"""
MCP Server 主程序 (FastMCP 方式)

提供 MySQL 查询的 MCP 工具，数据清洗、丰富、分析
"""

import logging
import sys
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
import pandas as pd

from mcp.server.fastmcp import FastMCP

from .core import path_manager, get_config, db_manager
from .tools import (
    execute_sql, list_tables as list_tables_impl, get_table_schema as get_schema_impl,
    read_table as read_table_impl, get_server_info,
    cache_data as cache_data_impl,
    enrich_derived_features,
    mask_sensitive_data as mask_sensitive_data_impl
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mcp_agent_server")

mcp = FastMCP("mcp-mysql-excel")

@mcp.tool()
async def get_current_datetime() -> str:
    """
    获取当前日期和时间。

    返回：
        - current_date: 当前日期，格式为 YYYY-MM-DD（如：2026-03-29）
        - current_datetime: 当前日期时间，格式为 YYYY-MM-DDTHH:MM:SS（如：2025-01-01T00:00:00）

    用途：
        - 在构建 OData 查询时提供当前日期作为基准
        - 支持相对时间计算（如"上个季度末"、"去年10月"）
        - 用于 asOfDate 参数的默认值
    """
    now = datetime.now()
    current_date = now.strftime('%Y-%m-%d')
    current_datetime = now.strftime('%Y-%m-%dT%H:%M:%S')

    return json.dumps({
        "current_date": current_date,
        "current_datetime": current_datetime
    }, ensure_ascii=False, indent=2)

@mcp.tool()
async def analyze_cached_data(
    operation: str,
    group_by: Optional[str] = None,
    target_col: Optional[str] = None
) -> str:
    """
    对上一步 MySQL_OB 或 MySQL_Yifei 查询到的缓存数据执行 Pandas 分析。

    Args:
        operation: 执行的操作。可选值:
            - 'status': 查看当前缓存状态（数据条数、可用字段）
            - 'count': 统计各分组的数量
            - 'sum': 求和
            - 'mean': 求均值
            - 'describe': 数据概览
            - 'value_counts': 频数统计
        group_by: 分组字段名
        target_col: 计算的目标字段名（对于 sum/mean 是必须的）

    Returns:
        分析结果
    """
    # 直接导入并使用底层实现
    from .tools.data_tools import CACHED_DF
    import numpy as np
    
    if CACHED_DF is None or CACHED_DF.empty:
        return json.dumps({
            "status": "error",
            "message": "当前内存中没有已缓存的数据。请先调用 MySQL_OB 或 MySQL_Yifei 查询数据。"
        }, ensure_ascii=False)

    try:
        if operation == 'status':
            return json.dumps({
                "status": "success",
                "cached": True,
                "count": len(CACHED_DF),
                "columns": list(CACHED_DF.columns)
            }, ensure_ascii=False)

        elif operation == 'describe':
            result = CACHED_DF.describe(include='all')
            res = result.to_csv()

        elif operation == 'value_counts' and group_by:
            if group_by not in CACHED_DF.columns:
                return json.dumps({
                    "status": "error",
                    "message": f"字段 '{group_by}' 不存在于数据中。可用字段：{list(CACHED_DF.columns)}"
                }, ensure_ascii=False)
            res = CACHED_DF[group_by].value_counts().reset_index().to_csv(index=False)

        elif operation == 'count' and group_by:
            if group_by not in CACHED_DF.columns:
                return json.dumps({
                    "status": "error",
                    "message": f"字段 '{group_by}' 不存在于数据中。可用字段：{list(CACHED_DF.columns)}"
                }, ensure_ascii=False)
            res = CACHED_DF.groupby(group_by).size().reset_index(name='count').to_csv(index=False)

        elif operation in ['sum', 'mean'] and group_by and target_col:
            if group_by not in CACHED_DF.columns:
                return json.dumps({
                    "status": "error",
                    "message": f"分组字段 '{group_by}' 不存在于数据中。可用字段：{list(CACHED_DF.columns)}"
                }, ensure_ascii=False)
            if target_col not in CACHED_DF.columns:
                return json.dumps({
                    "status": "error",
                    "message": f"目标字段 '{target_col}' 不存在于数据中。可用字段：{list(CACHED_DF.columns)}"
                }, ensure_ascii=False)

            CACHED_DF[target_col] = pd.to_numeric(CACHED_DF[target_col], errors='coerce')
            if operation == 'sum':
                res = CACHED_DF.groupby(group_by)[target_col].sum().reset_index().to_csv(index=False)
            else:
                res = CACHED_DF.groupby(group_by)[target_col].mean().reset_index().to_csv(index=False)

        else:
            return json.dumps({
                "status": "error",
                "message": f"未知的操作类型 '{operation}' 或参数缺失。对于 sum/mean 需要同时指定 group_by 和 target_col。"
            }, ensure_ascii=False)

        return json.dumps({
            "status": "success",
            "operation": operation,
            "data_count": len(CACHED_DF),
            "result": res
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"数据分析执行异常：{e}")
        return json.dumps({
            "status": "error",
            "message": f"分析执行异常：{str(e)}"
        }, ensure_ascii=False)


@mcp.tool()
async def MySQL_OB(
    query: str,
    max_rows: int = 10000
) -> str:
    """
    执行SQL查询语句（使用YUNYAN_OB服务器）。

    支持 SELECT、SHOW、DESCRIBE 等查询操作。
    查询结果会自动缓存，供后续 analyze_cached_data 分析使用。

    Args:
        query: SQL查询语句
        max_rows: 最大返回行数，默认10000
    """
    result = execute_sql(query=query, server_id="YUNYAN_OB", max_rows=max_rows)

    try:
        result_dict = json.loads(result)
        
        if result_dict.get("status") != "success":
            return result
        
        data = result_dict.get("data")
        if not data:
            return result
        
        df = pd.DataFrame(data)
        
        df = enrich_derived_features(df)
        enriched_data = df.fillna("").to_dict(orient='records')
        
        cache_data_impl(enriched_data)
        
        df_masked = mask_sensitive_data_impl(df.copy())
        masked_records = df_masked.fillna("").to_dict(orient='records')
        
        count = len(masked_records)
        
        if count <= 50:
            return json.dumps({
                "mode": "detail",
                "count": count,
                "data": masked_records
            }, indent=2, ensure_ascii=False)
        
        return json.dumps({
            "mode": "analysis_portrait",
            "total_records_captured": count,
            "available_columns": list(df.columns),
            "data_sample_head1": df_masked.fillna("").head(1).to_dict(orient='records'),
            "instruction": "数据已缓存。你可以使用 available_columns 中的字段调用 'analyze_cached_data' 进行聚合统计。"
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.warning(f"处理逻辑异常，执行降级脱敏输出: {e}")
        try:
            result_dict = json.loads(result)
            data = result_dict.get("data", [])
            cache_data_impl(data)
            
            df_fallback = pd.DataFrame(data)
            df_fallback_masked = mask_sensitive_data_impl(df_fallback)
            masked_data = df_fallback_masked.fillna("").to_dict(orient='records')
            
            if len(masked_data) <= 50:
                return json.dumps({
                    "mode": "detail",
                    "count": len(masked_data),
                    "data": masked_data
                }, ensure_ascii=False, indent=2)
            else:
                return json.dumps({
                    "mode": "analysis_portrait",
                    "total_records_captured": len(masked_data),
                    "data_sample_head1": masked_data[:1],
                    "instruction": "数据已缓存（部分处理失败）。"
                }, ensure_ascii=False, indent=2)
        except:
            return result


@mcp.tool()
async def MySQL_Yifei(
    query: str,
    max_rows: int = 10000
) -> str:
    """
    执行SQL查询语句（使用YIFEI服务器）。

    支持 SELECT、SHOW、DESCRIBE 等查询操作。
    查询结果会自动缓存，供后续 analyze_cached_data 分析使用。

    Args:
        query: SQL查询语句
        max_rows: 最大返回行数，默认10000
    """
    result = execute_sql(query=query, server_id="YIFEI", max_rows=max_rows)

    try:
        result_dict = json.loads(result)
        
        if result_dict.get("status") != "success":
            return result
        
        data = result_dict.get("data")
        if not data:
            return result
        
        df = pd.DataFrame(data)
        
        df = enrich_derived_features(df)
        enriched_data = df.fillna("").to_dict(orient='records')
        
        cache_data_impl(enriched_data)
        
        df_masked = mask_sensitive_data_impl(df.copy())
        masked_records = df_masked.fillna("").to_dict(orient='records')
        
        count = len(masked_records)
        
        if count <= 50:
            return json.dumps({
                "mode": "detail",
                "count": count,
                "data": masked_records
            }, indent=2, ensure_ascii=False)
        
        return json.dumps({
            "mode": "analysis_portrait",
            "total_records_captured": count,
            "available_columns": list(df.columns),
            "data_sample_head1": df_masked.fillna("").head(1).to_dict(orient='records'),
            "instruction": "数据已缓存。你可以使用 available_columns 中的字段调用 'analyze_cached_data' 进行聚合统计。"
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.warning(f"处理逻辑异常，执行降级脱敏输出: {e}")
        try:
            result_dict = json.loads(result)
            data = result_dict.get("data", [])
            cache_data_impl(data)
            
            df_fallback = pd.DataFrame(data)
            df_fallback_masked = mask_sensitive_data_impl(df_fallback)
            masked_data = df_fallback_masked.fillna("").to_dict(orient='records')
            
            if len(masked_data) <= 50:
                return json.dumps({
                    "mode": "detail",
                    "count": len(masked_data),
                    "data": masked_data
                }, ensure_ascii=False, indent=2)
            else:
                return json.dumps({
                    "mode": "analysis_portrait",
                    "total_records_captured": len(masked_data),
                    "data_sample_head1": masked_data[:1],
                    "instruction": "数据已缓存（部分处理失败）。"
                }, ensure_ascii=False, indent=2)
        except:
            return result


@mcp.tool()
async def list_tables(server_id: Optional[str] = None) -> str:
    """
    列出 MySQL 服务器中的所有表。

    Args:
        server_id: MySQL 服务器 ID（可选）
    """
    return list_tables_impl(server_id=server_id)


@mcp.tool()
async def get_table_schema(
    table: str,
    server_id: Optional[str] = None
) -> str:
    """
    获取指定表的结构信息（字段名、类型等）。

    Args:
        table: 表名
        server_id: MySQL 服务器 ID（可选）
    """
    return get_schema_impl(table=table, server_id=server_id)


@mcp.tool()
async def read_table(
    table: str,
    server_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> str:
    """
    读取表中的数据，支持分页。

    Args:
        table: 表名
        server_id: MySQL 服务器 ID（可选）
        limit: 最大返回行数，默认 100
        offset: 跳过行数，默认 0
    """
    return read_table_impl(table=table, server_id=server_id, limit=limit, offset=offset)




@mcp.resource("mysql://{server_id}/{database}/{table}")
async def get_table_resource(server_id: str, database: str, table: str) -> str:
    """
    通过URI访问数据库表资源。

    URI格式: mysql://{server_id}/{database}/{table}

    Args:
        server_id: 服务器ID
        database: 数据库名
        table: 表名
    """
    import json

    try:
        schema = db_manager.get_table_schema(table, server_id)
        data = db_manager.get_table_data(table, server_id, limit=100)

        return json.dumps({
            "server_id": server_id,
            "database": database,
            "table": table,
            "schema": schema,
            "data": data,
            "count": len(data)
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"读取资源失败: {e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, ensure_ascii=False)


def main():
    """主入口"""
    config = get_config()

    print(f"MCP MySQL Excel Server (FastMCP) 启动中...", file=sys.stderr)
    print(f"项目目录: {path_manager.project_root}", file=sys.stderr)
    print(f"输出目录: {path_manager.output_dir}", file=sys.stderr)

    if not config.list_servers():
        print("警告: 未配置任何MySQL服务器，请检查 config/databases.json", file=sys.stderr)

    mcp.run()


if __name__ == "__main__":
    main()
