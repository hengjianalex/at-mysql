"""
SQL工具模块

提供SQL执行、表查询等工具函数
"""

import json
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any

from ..core.db_connection import db_manager
from ..core.config_loader import get_config

logger = logging.getLogger("mcp_agent.tools.sql")


class DateTimeEncoder(json.JSONEncoder):
    """JSON编码器，支持datetime、date和Decimal类型"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def convert_to_json_serializable(data: Any) -> Any:
    """递归转换数据为JSON可序列化格式"""
    if isinstance(data, list):
        return [convert_to_json_serializable(item) for item in data]
    elif isinstance(data, dict):
        return {key: convert_to_json_serializable(value) for key, value in data.items()}
    elif isinstance(data, datetime):
        return data.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(data, date):
        return data.strftime('%Y-%m-%d')
    elif isinstance(data, Decimal):
        return float(data)
    else:
        return data


def execute_sql(
    query: str,
    server_id: Optional[str] = None,
    max_rows: int = 1000
) -> str:
    """
    执行SQL查询并返回JSON结果

    Args:
        query: SQL查询语句
        server_id: 服务器ID（可选）
        max_rows: 最大返回行数

    Returns:
        JSON格式的查询结果
    """
    try:
        results = db_manager.execute_query(query, server_id, max_rows=max_rows)

        if not results:
            return json.dumps({
                "status": "success",
                "count": 0,
                "data": []
            }, ensure_ascii=False)

        return json.dumps({
            "status": "success",
            "server_id": server_id or get_config().get_default_server_id(),
            "count": len(results),
            "data": convert_to_json_serializable(results)
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"SQL执行失败: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, ensure_ascii=False)


def list_tables(server_id: Optional[str] = None) -> str:
    """
    列出所有表

    Args:
        server_id: 服务器ID（可选）

    Returns:
        JSON格式的表列表
    """
    try:
        tables = db_manager.get_tables(server_id)

        return json.dumps({
            "status": "success",
            "server_id": server_id or get_config().get_default_server_id(),
            "count": len(tables),
            "tables": tables
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"获取表列表失败: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, ensure_ascii=False)


def get_table_schema(
    table: str,
    server_id: Optional[str] = None
) -> str:
    """
    获取表结构

    Args:
        table: 表名
        server_id: 服务器ID（可选）

    Returns:
        JSON格式的表结构
    """
    try:
        schema = db_manager.get_table_schema(table, server_id)

        return json.dumps({
            "status": "success",
            "server_id": server_id or get_config().get_default_server_id(),
            "table": table,
            "schema": schema
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"获取表结构失败: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, ensure_ascii=False)


def read_table(
    table: str,
    server_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> str:
    """
    读取表数据

    Args:
        table: 表名
        server_id: 服务器ID（可选）
        limit: 最大返回行数
        offset: 跳过行数

    Returns:
        JSON格式的表数据
    """
    try:
        data = db_manager.get_table_data(table, server_id, limit, offset)

        return json.dumps({
            "status": "success",
            "server_id": server_id or get_config().get_default_server_id(),
            "table": table,
            "count": len(data),
            "limit": limit,
            "offset": offset,
            "data": convert_to_json_serializable(data)
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"读取表数据失败: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, ensure_ascii=False)


def get_server_info() -> str:
    """
    获取服务器信息列表

    Returns:
        JSON格式的服务器列表
    """
    try:
        config = get_config()
        servers = config.list_servers()
        default = config.get_default_server_id()

        return json.dumps({
            "status": "success",
            "servers": servers,
            "default_server": default
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"获取服务器信息失败: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, ensure_ascii=False)
