#!/usr/bin/env python3
"""批量上传本地票据图片到系统：上传指定文件夹全部图片，并从数据集每个子文件夹随机抽样上传。"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Iterable, List

import requests


def is_image(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".pdf"}


def upload_file(session: requests.Session, base_url: str, file_path: Path, user_id: str | None = None) -> None:
    meta = json.dumps({"source_path": str(file_path)})
    data = {"meta": meta}
    if user_id:
        data["user_id"] = user_id
    with file_path.open("rb") as fp:
        files = {"file": (file_path.name, fp, "application/octet-stream")}
        resp = session.post(f"{base_url}/api/v1/reconciliations/upload", data=data, files=files, timeout=120)
    resp.raise_for_status()
    payload = resp.json()
    if not payload.get("success"):
        raise RuntimeError(payload.get("error") or f"upload failed for {file_path}")


def collect_all_images(root: Path) -> List[Path]:
    if not root.exists():
        return []
    return [p for p in root.rglob("*") if is_image(p)]


def collect_samples_per_subdir(root: Path, sample_size: int) -> List[Path]:
    picked: List[Path] = []
    if not root.exists():
        return picked
    for sub in sorted([p for p in root.iterdir() if p.is_dir()]):
        files = [p for p in sub.iterdir() if is_image(p)]
        if not files:
            continue
        random.shuffle(files)
        picked.extend(files[: sample_size if sample_size > 0 else len(files)])
    return picked


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="批量上传票据图片到系统")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000", help="服务地址，默认 http://127.0.0.1:5000")
    parser.add_argument("--ticket-dir", type=Path, default=Path("/Users/muxin/Desktop/对账系统/票据"), help="本地票据目录，全部上传")
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path("/Users/muxin/Desktop/对账系统/InvoiceDatasets-master/dataset/images"),
        help="数据集根目录（含多个子目录，每个随机抽样上传）",
    )
    parser.add_argument("--sample-per-folder", type=int, default=5, help="每个子目录抽取数量，默认 5")
    parser.add_argument("--email", help="登录邮箱，可选")
    parser.add_argument("--password", help="登录密码，可选")
    parser.add_argument("--user-id", help="上传时附带的 user_id，可选")
    parser.add_argument("--dry-run", action="store_true", help="仅打印将要上传的文件，不真正上传")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    session = requests.Session()
    base_url = args.base_url.rstrip("/")

    if args.email and args.password:
        resp = session.post(f"{base_url}/api/v1/auth/login", json={"email": args.email, "password": args.password}, timeout=30)
        try:
            data = resp.json()
        except Exception:
            data = {}
        if not resp.ok or not data.get("success"):
            print(f"登录失败: {data.get('error') if isinstance(data, dict) else resp.text}", file=sys.stderr)
            return 1

    ticket_files = collect_all_images(args.ticket_dir)
    dataset_files = collect_samples_per_subdir(args.dataset_dir, args.sample_per_folder)
    all_files: List[Path] = ticket_files + dataset_files

    if not all_files:
        print("未找到可上传的文件，检查路径或后缀(.jpg/.jpeg/.png/.pdf)", file=sys.stderr)
        return 1

    print(f"即将上传 {len(all_files)} 个文件，其中票据目录 {len(ticket_files)} 个，数据集抽样 {len(dataset_files)} 个。")

    if args.dry_run:
        for p in all_files:
            print(p)
        return 0

    success = 0
    for idx, file_path in enumerate(all_files, 1):
        try:
            upload_file(session, base_url, file_path, user_id=args.user_id)
            success += 1
            print(f"[{idx}/{len(all_files)}] 上传成功: {file_path}")
        except Exception as exc:
            print(f"[{idx}/{len(all_files)}] 上传失败: {file_path} -> {exc}", file=sys.stderr)

    print(f"完成：成功 {success} / 总计 {len(all_files)}")
    return 0 if success == len(all_files) else 1


if __name__ == "__main__":
    raise SystemExit(main())




