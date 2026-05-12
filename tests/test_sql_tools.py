"""
sql_tools 模块回归测试
"""

import pytest
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestSqlToolsImport:
    """模块导入测试"""

    def test_import_sql_tools(self):
        """测试 sql_tools 模块可导入"""
        from tools import sql_tools

        assert sql_tools is not None

    def test_import_execute_sql(self):
        """测试 execute_sql 函数可导入"""
        from tools.sql_tools import execute_sql

        assert callable(execute_sql)

    def test_import_list_tables(self):
        """测试 list_tables 函数可导入"""
        from tools.sql_tools import list_tables

        assert callable(list_tables)


class TestExecuteSql:
    """execute_sql 函数测试"""

    def test_execute_sql_returns_json(self):
        """测试 execute_sql 返回 JSON 字符串"""
        from tools.sql_tools import execute_sql

        result = execute_sql(
            "SELECT 1 as id, 'test' as name", server_id="YIFEI", max_rows=1
        )
        # 验证是有效的 JSON
        data = json.loads(result)
        assert "status" in data

    def test_execute_sql_with_params(self):
        """测试 execute_sql 支持 params 参数"""
        from tools.sql_tools import execute_sql

        result = execute_sql(
            "SELECT %s as id, %s as name", server_id="YIFEI", params=("1", "test")
        )
        data = json.loads(result)
        assert data["status"] == "success"

    def test_execute_sql_empty_result(self):
        """测试 execute_sql 空结果返回"""
        from tools.sql_tools import execute_sql

        result = execute_sql("SELECT * FROM nonexistent_table_xyz", server_id="YIFEI")
        data = json.loads(result)
        assert "status" in data


class TestConvertToJsonSerializable:
    """convert_to_json_serializable 函数测试"""

    def test_convert_list(self):
        """测试列表转换"""
        from tools.sql_tools import convert_to_json_serializable

        result = convert_to_json_serializable([1, 2, 3])
        assert result == [1, 2, 3]

    def test_convert_dict(self):
        """测试字典转换"""
        from tools.sql_tools import convert_to_json_serializable

        result = convert_to_json_serializable({"key": "value"})
        assert result == {"key": "value"}
