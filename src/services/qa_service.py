"""智能问答服务 - 基于LLM和数据库的自由问答。"""
from __future__ import annotations

import logging
import re
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from functools import lru_cache
from sqlalchemy import text
from sqlalchemy.orm import Session

from llm_client import LLMClient

logger = logging.getLogger(__name__)


class QAService:
    """智能问答服务。"""
    
    # SQL安全白名单
    ALLOWED_TABLES = {"documents", "ledger_entries", "reconciliations"}
    FORBIDDEN_KEYWORDS = {
        "insert", "update", "delete", "drop", "create", "alter", "truncate",
        "pragma", "attach", "detach", "information_schema", "pg_catalog",
        "union", "exec", "execute"
    }
    
    # 最大返回行数
    MAX_ROWS = 200
    DEFAULT_LIMIT = 20
    
    # 查询超时（秒）
    QUERY_TIMEOUT = 10
    
    def __init__(self, db: Session, llm_client: LLMClient):
        """初始化问答服务。
        
        Args:
            db: 数据库会话
            llm_client: LLM客户端
        """
        self.db = db
        self.llm_client = llm_client
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._cache_ttl = 30  # 缓存30秒
    
    def ask(
        self, 
        question: str, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """处理用户问题。
        
        Args:
            question: 用户问题
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            limit: 返回行数限制（可选）
            
        Returns:
            Dict: 包含answer_md, evidence, followups的响应
        """
        logger.info(f"收到问题: {question}")
        
        # 检查缓存
        cache_key = self._make_cache_key(question, start_date, end_date)
        cached = self._get_from_cache(cache_key)
        if cached:
            logger.info("从缓存返回结果")
            return cached
        
        try:
            # Step A: 使用LLM生成查询计划
            query_plan = self._generate_query_plan(question, start_date, end_date, limit)
            
            if query_plan.get("task") == "need_more":
                # 需要更多信息
                return {
                    "answer_md": "抱歉，我需要更多信息才能回答您的问题。\n\n" + 
                                "\n".join(f"- {q}" for q in query_plan.get("questions", [])),
                    "evidence": None,
                    "followups": query_plan.get("questions", [])
                }
            
            # Step B: 验证SQL安全性
            sql = query_plan.get("sql", "")
            params = query_plan.get("params", {})
            raw_limit = query_plan.get("limit")
            query_limit = raw_limit if isinstance(raw_limit, int) and raw_limit > 0 else (limit or self.DEFAULT_LIMIT)
            
            if not self._validate_sql(sql):
                logger.warning(f"SQL验证失败: {sql}")
                return {
                    "answer_md": "抱歉，无法生成安全的查询来回答您的问题。请尝试换一种方式提问。",
                    "evidence": None,
                    "followups": None
                }
            
            # 强制添加LIMIT
            sql = self._enforce_limit(sql, min(query_limit, self.MAX_ROWS))
            
            # Step C: 执行SQL查询
            rows, columns = self._execute_query(sql, params)
            
            # 创建紧凑的上下文并生成最终答案
            answer_md = self._generate_answer(question, sql, params, rows, columns, start_date, end_date, query_limit)
            
            # 准备证据
            evidence = {
                "sql": sql,
                "params": params,
                "rows_preview": rows[:20] if rows else [],  # 只返回前20行作为预览
                "total_rows": len(rows),
                "columns": columns
            }
            
            # 生成后续问题建议
            followups = self._generate_followups(question, rows)
            
            result = {
                "answer_md": answer_md,
                "evidence": evidence,
                "followups": followups
            }
            
            # 缓存结果
            self._put_to_cache(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.exception(f"处理问题时发生错误: {e}")
            return {
                "answer_md": f"抱歉，处理您的问题时发生错误：{str(e)}",
                "evidence": None,
                "followups": None
            }
    
    def _generate_query_plan(
        self, 
        question: str, 
        start_date: Optional[str],
        end_date: Optional[str],
        limit: Optional[int]
    ) -> Dict[str, Any]:
        """使用LLM生成查询计划。
        
        Args:
            question: 用户问题
            start_date: 开始日期
            end_date: 结束日期
            limit: 行数限制
            
        Returns:
            Dict: 查询计划JSON
        """
        # 构建提示词
        date_info = ""
        if start_date and end_date:
            date_info = f"用户指定的日期范围：{start_date} 到 {end_date}"
        elif not start_date and not end_date:
            # 默认最近30天
            default_start = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            default_end = datetime.now().strftime('%Y-%m-%d')
            date_info = f"默认日期范围（最近30天）：{default_start} 到 {default_end}"
            start_date = default_start
            end_date = default_end
        
        prompt = f"""你是一个SQL查询生成助手。根据用户问题生成安全的SQL查询计划。

数据库表结构：
- documents表：包含发票数据
  列：id, user_id, file_name, file_path, vendor, amount, tax_amount, currency, category, status, created_at

约束条件：
1. 只能使用SELECT语句，禁止INSERT/UPDATE/DELETE/DDL
2. 只能查询documents表
3. 不要选择大型字段（如raw_result等JSON/BLOB字段）
4. 必须包含LIMIT子句（非聚合查询默认20条）
5. 如果用户问"全部/所有"，仍需限制条数并说明"仅展示前N条"
6. {date_info}
7. 使用参数化查询，将值放在params中
8. 日期字段使用created_at（不是invoice_date）

用户问题：{question}

请生成JSON格式的查询计划（不要包含任何其他文字）：
{{
  "task": "sql",
  "sql": "SELECT id, vendor, amount, category, status, created_at FROM documents WHERE created_at >= :start_date AND created_at <= :end_date LIMIT :limit",
  "params": {{"start_date": "{start_date}", "end_date": "{end_date}", "limit": {limit or self.DEFAULT_LIMIT}}},
  "explain": "简短说明",
  "limit": {limit or self.DEFAULT_LIMIT}
}}

如果无法通过SQL回答，返回：
{{
  "task": "need_more",
  "questions": ["需要澄清的问题1", "需要澄清的问题2"]
}}

只返回JSON，不要包含其他内容。"""
        
        try:
            messages = [{"role": "system", "content": prompt}]
            response = self.llm_client.chat(messages)
            logger.debug(f"LLM查询计划响应: {response}")
            
            # 提取JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                query_plan = json.loads(json_match.group())
                return query_plan
            else:
                logger.warning("LLM响应中未找到有效的JSON")
                return {"task": "need_more", "questions": ["请提供更具体的问题"]}
                
        except Exception as e:
            logger.exception(f"生成查询计划失败: {e}")
            return {"task": "need_more", "questions": ["抱歉，无法理解您的问题，请换一种方式提问"]}
    
    def _validate_sql(self, sql: str) -> bool:
        """验证SQL安全性。
        
        Args:
            sql: SQL语句
            
        Returns:
            bool: 是否安全
        """
        if not sql or not sql.strip():
            return False
        
        sql_lower = sql.lower().strip()
        
        # 必须以SELECT开头
        if not sql_lower.startswith("select"):
            logger.warning("SQL不是以SELECT开头")
            return False
        
        # 检查禁止的关键字
        for keyword in self.FORBIDDEN_KEYWORDS:
            if re.search(fr"\b{keyword}\b", sql_lower):
                logger.warning(f"SQL包含禁止的关键字: {keyword}")
                return False
        
        # 检查是否只查询允许的表
        # 简单的表名检查（可以改进）
        from_match = re.search(r'from\s+(\w+)', sql_lower)
        if from_match:
            table_name = from_match.group(1)
            if table_name not in self.ALLOWED_TABLES:
                logger.warning(f"SQL查询了不允许的表: {table_name}")
                return False
        
        # 检查是否包含分号（防止多语句）
        if ';' in sql:
            logger.warning("SQL包含分号")
            return False
        
        return True
    
    def _enforce_limit(self, sql: str, limit: int) -> str:
        """强制添加或修改LIMIT子句。
        
        Args:
            sql: SQL语句
            limit: 限制行数
            
        Returns:
            str: 修改后的SQL
        """
        sql_lower = sql.lower().strip()
        
        # 如果已有LIMIT，替换它
        if 'limit' in sql_lower:
            # 使用正则替换LIMIT值
            sql = re.sub(r'limit\s+\d+', f'LIMIT {limit}', sql, flags=re.IGNORECASE)
        else:
            # 添加LIMIT
            sql = sql.rstrip(';') + f' LIMIT {limit}'
        
        return sql
    
    def _execute_query(self, sql: str, params: Dict[str, Any]) -> tuple[List[Dict], List[str]]:
        """执行SQL查询。
        
        Args:
            sql: SQL语句
            params: 参数
            
        Returns:
            tuple: (行数据列表, 列名列表)
        """
        try:
            logger.debug(f"执行SQL: {sql}, 参数: {params}")
            
            # 执行查询（带超时）
            result = self.db.execute(text(sql), params)
            
            # 获取列名
            columns = list(result.keys()) if result.keys() else []
            
            # 获取所有行
            rows = []
            for row in result:
                row_dict = dict(zip(columns, row))
                # 转换日期类型为字符串
                for key, value in row_dict.items():
                    if isinstance(value, (datetime, )):
                        row_dict[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                rows.append(row_dict)
            
            logger.info(f"查询返回 {len(rows)} 行数据")
            return rows, columns
            
        except Exception as e:
            logger.exception(f"执行查询失败: {e}")
            raise
    
    def _generate_answer(
        self,
        question: str,
        sql: str,
        params: Dict[str, Any],
        rows: List[Dict],
        columns: List[str],
        start_date: Optional[str],
        end_date: Optional[str],
        limit: int
    ) -> str:
        """使用LLM生成最终答案。
        
        Args:
            question: 用户问题
            sql: 执行的SQL
            params: SQL参数
            rows: 查询结果
            columns: 列名
            start_date: 开始日期
            end_date: 结束日期
            limit: 限制行数
            
        Returns:
            str: Markdown格式的答案
        """
        # 准备紧凑的上下文
        rows_preview = rows[:20] if rows else []
        
        # 构建提示词
        prompt = f"""根据以下查询结果回答用户问题。

用户问题：{question}

执行的SQL：{sql}
参数：{json.dumps(params, ensure_ascii=False)}

查询结果（共{len(rows)}行，显示前{len(rows_preview)}行）：
列名：{', '.join(columns)}

数据：
{json.dumps(rows_preview, ensure_ascii=False, indent=2)}

要求：
1. 用Markdown格式回答
2. 必须引用查询结果中的具体数字
3. 如果有多行数据，包含一个简洁的Markdown表格（最多显示10行）
4. 在答案末尾说明"数据口径/范围"（日期范围：{start_date} 到 {end_date}，限制：前{limit}条）
5. 保持简洁，不要编造数据
6. 如果结果为空，说明未找到符合条件的数据

请生成答案："""
        
        try:
            messages = [{"role": "system", "content": prompt}]
            answer = self.llm_client.chat(messages)
            return answer
        except Exception as e:
            logger.exception(f"生成答案失败: {e}")
            # 回退到简单格式
            if not rows:
                return f"未找到符合条件的数据。\n\n**数据范围**：{start_date} 到 {end_date}"
            
            # 生成简单的表格
            answer = f"查询到 {len(rows)} 条记录（显示前{min(len(rows), 10)}条）：\n\n"
            
            if rows_preview:
                # 创建Markdown表格
                answer += "| " + " | ".join(columns) + " |\n"
                answer += "| " + " | ".join(["---"] * len(columns)) + " |\n"
                
                for row in rows_preview[:10]:
                    answer += "| " + " | ".join(str(row.get(col, "")) for col in columns) + " |\n"
            
            answer += f"\n**数据范围**：{start_date} 到 {end_date}，限制：前{limit}条"
            
            return answer
    
    def _generate_followups(self, question: str, rows: List[Dict]) -> Optional[List[str]]:
        """生成后续问题建议。
        
        Args:
            question: 原问题
            rows: 查询结果
            
        Returns:
            Optional[List[str]]: 后续问题列表
        """
        if not rows:
            return None
        
        # 简单的后续问题生成逻辑
        followups = []
        
        # 根据查询结果提供建议
        if len(rows) > 0:
            # 检查是否有金额字段
            if any('amount' in str(k).lower() for k in rows[0].keys()):
                followups.append("这些发票的总金额是多少？")
            
            # 检查是否有供应商字段
            if any('vendor' in str(k).lower() for k in rows[0].keys()):
                followups.append("按供应商分组统计金额")
            
            # 检查是否有类别字段
            if any('category' in str(k).lower() for k in rows[0].keys()):
                followups.append("按类别分组统计")
        
        return followups[:3] if followups else None
    
    def _make_cache_key(self, question: str, start_date: Optional[str], end_date: Optional[str]) -> str:
        """生成缓存键。
        
        Args:
            question: 问题
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            str: 缓存键
        """
        return f"{question}|{start_date}|{end_date}"
    
    def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """从缓存获取结果。
        
        Args:
            key: 缓存键
            
        Returns:
            Optional[Dict]: 缓存的结果，如果过期或不存在返回None
        """
        if key in self._cache:
            result, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return result
            else:
                # 过期，删除
                del self._cache[key]
        return None
    
    def _put_to_cache(self, key: str, result: Dict[str, Any]) -> None:
        """将结果放入缓存。
        
        Args:
            key: 缓存键
            result: 结果
        """
        self._cache[key] = (result, time.time())
        
        # 简单的缓存清理：如果缓存超过100项，清除最旧的一半
        if len(self._cache) > 100:
            sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
            for old_key, _ in sorted_items[:50]:
                del self._cache[old_key]


__all__ = ["QAService"]

