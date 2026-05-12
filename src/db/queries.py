"""
公共查询模块

提供 SQL 执行等公共查询函数，供 MCP Server 和 scripts 共用
"""

import logging
import sys
import os
from typing import Optional, List, Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.db_connection import db_manager
from core.config_loader import get_config

logger = logging.getLogger("mcp_agent.db.queries")


def execute_query(
    query: str,
    server_id: Optional[str] = None,
    max_rows: int = 1000,
    params: Optional[tuple] = None,
) -> List[Dict[str, Any]]:
    """
    执行 SQL 查询并返回字典列表

    Args:
        query: SQL 查询语句
        server_id: 服务器 ID（可选）
        max_rows: 最大返回行数
        params: 查询参数元组

    Returns:
        查询结果字典列表
    """
    return db_manager.execute_query(query, server_id, max_rows=max_rows, params=params)


def execute_query_raw(
    query: str, server_id: Optional[str] = None, max_rows: int = 1000
) -> Optional[List[Dict[str, Any]]]:
    """
    执行 SQL 查询并返回原始结果（无异常包装）

    Args:
        query: SQL 查询语句
        server_id: 服务器 ID（可选）
        max_rows: 最大返回行数

    Returns:
        查询结果字典列表，失败时返回 None
    """
    try:
        return db_manager.execute_query(query, server_id, max_rows=max_rows)
    except Exception as e:
        logger.error(f"SQL 执行失败: {e}")
        return None


def get_default_server_id() -> str:
    """获取默认服务器 ID"""
    return get_config().get_default_server_id()
