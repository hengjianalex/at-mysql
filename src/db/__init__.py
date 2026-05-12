"""
公共查询模块

提供 SQL 执行等公共查询函数，供 MCP Server 和 scripts 共用
"""

from .queries import execute_query, execute_query_raw, get_default_server_id

__all__ = [
    "execute_query",
    "execute_query_raw",
    "get_default_server_id",
]
