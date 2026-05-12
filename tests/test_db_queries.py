"""
db.queries 模块测试
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestDbQueriesImport:
    """模块导入测试"""

    def test_import_queries_module(self):
        """测试 queries 模块可导入"""
        from db import queries

        assert queries is not None

    def test_import_execute_query(self):
        """测试 execute_query 函数可导入"""
        from db.queries import execute_query

        assert callable(execute_query)

    def test_import_execute_query_raw(self):
        """测试 execute_query_raw 函数可导入"""
        from db.queries import execute_query_raw

        assert callable(execute_query_raw)

    def test_import_get_default_server_id(self):
        """测试 get_default_server_id 函数可导入"""
        from db.queries import get_default_server_id

        assert callable(get_default_server_id)


class TestExecuteQuery:
    """execute_query 函数测试"""

    def test_execute_query_returns_list(self):
        """测试 execute_query 返回字典列表"""
        from db.queries import execute_query

        result = execute_query(
            "SELECT 1 as id, 'test' as name", server_id="YIFEI", max_rows=1
        )
        assert isinstance(result, list)


class TestExecuteQueryRaw:
    """execute_query_raw 函数测试"""

    def test_execute_query_raw_returns_list_or_none(self):
        """测试 execute_query_raw 返回列表或 None"""
        from db.queries import execute_query_raw

        result = execute_query_raw("SELECT 1", server_id="YIFEI")
        assert result is None or isinstance(result, list)


class TestGetDefaultServerId:
    """get_default_server_id 函数测试"""

    def test_get_default_server_id_returns_str(self):
        """测试 get_default_server_id 返回字符串"""
        from db.queries import get_default_server_id

        result = get_default_server_id()
        assert isinstance(result, str)
