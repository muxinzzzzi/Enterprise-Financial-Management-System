"""PDF依赖检查工具。"""
from __future__ import annotations

import logging
import platform
import os
from typing import Dict, List

logger = logging.getLogger(__name__)


def check_reportlab() -> Dict[str, any]:
    """检查reportlab是否安装。
    
    Returns:
        Dict: 检查结果
    """
    result = {
        "installed": False,
        "version": None,
        "error": None,
    }
    
    try:
        import reportlab
        result["installed"] = True
        result["version"] = getattr(reportlab, "__version__", "unknown")
        logger.info(f"reportlab已安装，版本: {result['version']}")
    except ImportError as e:
        result["error"] = str(e)
        logger.warning(f"reportlab未安装: {e}")
    
    return result


def check_weasyprint() -> Dict[str, any]:
    """检查weasyprint是否安装及其依赖。
    
    Returns:
        Dict: 检查结果
    """
    result = {
        "installed": False,
        "version": None,
        "dependencies_ok": False,
        "error": None,
        "dependency_errors": [],
    }
    
    try:
        import weasyprint
        result["installed"] = True
        result["version"] = getattr(weasyprint, "__version__", "unknown")
        logger.info(f"weasyprint已安装，版本: {result['version']}")
        
        # 检查依赖
        try:
            from weasyprint import HTML
            # 尝试创建一个简单的HTML对象来测试依赖
            test_html = HTML(string="<html><body>Test</body></html>")
            result["dependencies_ok"] = True
            logger.info("weasyprint依赖检查通过")
        except Exception as e:
            result["dependency_errors"].append(str(e))
            logger.warning(f"weasyprint依赖检查失败: {e}")
            
    except ImportError as e:
        result["error"] = str(e)
        logger.warning(f"weasyprint未安装: {e}")
    
    return result


def check_chinese_fonts() -> Dict[str, any]:
    """检查中文字体是否可用。
    
    Returns:
        Dict: 检查结果
    """
    result = {
        "fonts_found": [],
        "fonts_available": [],
        "error": None,
    }
    
    try:
        system = platform.system()
        font_paths = []
        
        if system == "Windows":
            windows_font_dir = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
            font_paths = [
                ("SimSun", os.path.join(windows_font_dir, 'simsun.ttc')),
                ("SimHei", os.path.join(windows_font_dir, 'simhei.ttf')),
                ("Microsoft YaHei", os.path.join(windows_font_dir, 'msyh.ttc')),
                ("KaiTi", os.path.join(windows_font_dir, 'simkai.ttf')),
            ]
        elif system == "Darwin":  # macOS
            font_paths = [
                ("STHeiti", '/System/Library/Fonts/STHeiti Light.ttc'),
                ("PingFang", '/System/Library/Fonts/PingFang.ttc'),
                ("Arial Unicode", '/Library/Fonts/Arial Unicode.ttf'),
            ]
        elif system == "Linux":
            font_paths = [
                ("WenQuanYi Micro Hei", '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'),
                ("WenQuanYi Zen Hei", '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'),
                ("AR PL UMing", '/usr/share/fonts/truetype/arphic/uming.ttc'),
            ]
        
        for font_name, font_path in font_paths:
            result["fonts_found"].append(font_name)
            if os.path.exists(font_path):
                result["fonts_available"].append({
                    "name": font_name,
                    "path": font_path,
                })
                logger.info(f"找到中文字体: {font_name} -> {font_path}")
        
        if not result["fonts_available"]:
            logger.warning("未找到可用的中文字体")
            
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"检查中文字体时发生错误: {e}")
    
    return result


def check_pdf_dependencies() -> Dict[str, any]:
    """检查所有PDF生成依赖。
    
    Returns:
        Dict: 完整的检查结果
    """
    logger.info("开始检查PDF生成依赖...")
    
    result = {
        "reportlab": check_reportlab(),
        "weasyprint": check_weasyprint(),
        "chinese_fonts": check_chinese_fonts(),
        "system": platform.system(),
        "can_generate_pdf": False,
    }
    
    # 判断是否可以生成PDF
    result["can_generate_pdf"] = (
        result["reportlab"]["installed"] or 
        (result["weasyprint"]["installed"] and result["weasyprint"]["dependencies_ok"])
    )
    
    if result["can_generate_pdf"]:
        logger.info("PDF生成依赖检查通过，可以生成PDF")
    else:
        logger.error("PDF生成依赖检查失败，无法生成PDF")
    
    return result


def print_diagnostic_report() -> None:
    """打印诊断报告。"""
    result = check_pdf_dependencies()
    
    print("=" * 60)
    print("PDF生成依赖诊断报告")
    print("=" * 60)
    print(f"\n系统: {result['system']}")
    
    print("\n1. reportlab检查:")
    if result["reportlab"]["installed"]:
        print(f"   ✓ 已安装，版本: {result['reportlab']['version']}")
    else:
        print(f"   ✗ 未安装: {result['reportlab']['error']}")
    
    print("\n2. weasyprint检查:")
    if result["weasyprint"]["installed"]:
        print(f"   ✓ 已安装，版本: {result['weasyprint']['version']}")
        if result["weasyprint"]["dependencies_ok"]:
            print("   ✓ 依赖检查通过")
        else:
            print(f"   ✗ 依赖检查失败: {result['weasyprint']['dependency_errors']}")
    else:
        print(f"   ✗ 未安装: {result['weasyprint']['error']}")
    
    print("\n3. 中文字体检查:")
    if result["chinese_fonts"]["fonts_available"]:
        print(f"   ✓ 找到 {len(result['chinese_fonts']['fonts_available'])} 个可用字体:")
        for font in result["chinese_fonts"]["fonts_available"]:
            print(f"      - {font['name']}: {font['path']}")
    else:
        print("   ✗ 未找到可用的中文字体")
        print(f"   已检查的字体: {', '.join(result['chinese_fonts']['fonts_found'])}")
    
    print("\n4. 总体状态:")
    if result["can_generate_pdf"]:
        print("   ✓ 可以生成PDF")
        if not result["chinese_fonts"]["fonts_available"]:
            print("   ⚠ 警告: 未找到中文字体，PDF中的中文可能显示为方块")
    else:
        print("   ✗ 无法生成PDF")
        print("   建议: 安装reportlab或weasyprint库")
    
    print("=" * 60)


if __name__ == "__main__":
    # 设置日志级别
    logging.basicConfig(level=logging.INFO)
    print_diagnostic_report()

