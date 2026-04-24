"""
数据库连接模块

提供基于服务器ID的连接池管理
"""

import logging
from typing import Optional, Dict, List, Any
from contextlib import contextmanager

from mysql.connector import pooling, Error

from .config_loader import get_config, ServerConfig

logger = logging.getLogger("mcp_agent.db")


class DBConnectionPool:
    """数据库连接池管理器"""

    _pools: Dict[str, pooling.MySQLConnectionPool] = {}

    @classmethod
    def get_pool(cls, server_config: ServerConfig) -> pooling.MySQLConnectionPool:
        """获取或创建连接池"""
        pool_name = f"pool_{server_config.id}"

        if pool_name not in cls._pools:
            try:
                cls._pools[pool_name] = pooling.MySQLConnectionPool(
                    pool_name=pool_name,
                    pool_size=5,
                    pool_reset_session=True,
                    **server_config.to_dict()
                )
                logger.info(f"为服务器 {server_config.id} 创建连接池")
            except Error as e:
                logger.error(f"创建连接池失败 {server_config.id}: {e}")
                raise

        return cls._pools[pool_name]

    @classmethod
    @contextmanager
    def get_connection(cls, server_config: ServerConfig):
        """从池中获取连接"""
        pool = cls.get_pool(server_config)
        conn = None
        try:
            conn = pool.get_connection()
            yield conn
        except Error as e:
            logger.error(f"获取连接失败: {e}")
            raise
        finally:
            if conn:
                conn.close()

    @classmethod
    def close_all(cls):
        """关闭所有连接池"""
        cls._pools.clear()
        logger.info("所有连接池已关闭")


class DBManager:
    """数据库管理器"""

    def __init__(self):
        self.config_loader = get_config()

    def execute_query(
        self,
        query: str,
        server_id: Optional[str] = None,
        params: tuple = None,
        max_rows: int = 1000
    ) -> List[Dict[str, Any]]:
        """执行查询并返回字典列表"""
        server = self.config_loader.get_server(server_id)

        with DBConnectionPool.get_connection(server) as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)

            if cursor.description is None:
                return [{"rows_affected": cursor.rowcount}]

            results = cursor.fetchmany(max_rows)
            return results

    def get_tables(self, server_id: Optional[str] = None) -> List[str]:
        """获取所有表名"""
        server = self.config_loader.get_server(server_id)

        with DBConnectionPool.get_connection(server) as conn:
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            return tables

    def get_table_schema(
        self,
        table: str,
        server_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取表结构"""
        server = self.config_loader.get_server(server_id)

        with DBConnectionPool.get_connection(server) as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(f"DESCRIBE `{table}`")
            return cursor.fetchall()

    def get_table_data(
        self,
        table: str,
        server_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取表数据"""
        server = self.config_loader.get_server(server_id)

        with DBConnectionPool.get_connection(server) as conn:
            cursor = conn.cursor(dictionary=True)
            query = f"SELECT * FROM `{table}` LIMIT %s OFFSET %s"
            cursor.execute(query, (limit, offset))
            return cursor.fetchall()


db_manager = DBManager()
