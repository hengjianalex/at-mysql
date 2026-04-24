"""
数据清洗工具模块

提供数据清洗、格式转换、敏感信息脱敏等功能
"""

import json
import logging
from typing import Any, List, Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("mcp_agent.tools.data")

CACHED_DF: Optional[pd.DataFrame] = None

def cache_data(data: List[Dict]) -> str:
    """
    将数据缓存到内存中，供后续分析使用

    Args:
        data: 数据记录列表

    Returns:
        缓存状态
    """
    global CACHED_DF

    try:
        if not data:
            CACHED_DF = None
            return json.dumps({
                "status": "success",
                "message": "缓存已清空"
            }, ensure_ascii=False)

        CACHED_DF = pd.DataFrame(data)
        return json.dumps({
            "status": "success",
            "message": f"已缓存 {len(CACHED_DF)} 条数据",
            "columns": list(CACHED_DF.columns),
            "count": len(CACHED_DF)
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"数据缓存失败：{e}")
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, ensure_ascii=False)


def analyze_cached_data(
    operation: str,
    group_by: Optional[str] = None,
    target_col: Optional[str] = None
) -> str:
    """
    对缓存的数据执行 Pandas 分析

    Args:
        operation: 执行的操作。可选值：'count' (计数), 'sum' (求和), 'mean' (均值), 'describe' (概览), 'value_counts' (频数统计)
        group_by: 分组字段名
        target_col: 计算的目标字段名（对于 sum/mean 是必须的）

    Returns:
        分析结果
    """
    global CACHED_DF

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


def enrich_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    数据富化引擎：从身份证号自动衍生年龄、性别、出生日期等特征
    
    数据源：
    - id_number: 18 位身份证号 -> 提取出生日期、年龄、性别

    Args:
        df: DataFrame 包含原始数据的 DataFrame

    Returns:
        富化后的 DataFrame
    """
    if df.empty:
        return df

    now = pd.Timestamp.now()

    # 处理身份证号 -> 提取出生日期、年龄、性别
    if 'id_number' in df.columns:
        def extract_birth_date(id_num):
            """从身份证号提取出生日期（第 7-14 位）"""
            if pd.isna(id_num) or len(str(id_num)) < 14:
                return None
            try:
                birth_str = str(id_num)[6:14]
                return pd.to_datetime(birth_str, format='%Y%m%d', errors='coerce')
            except:
                return None

        def calculate_age(birth_date):
            """计算年龄（保留 1 位小数）"""
            if pd.isna(birth_date):
                return None
            return np.round((now - birth_date).days / 365.25, 1)

        def extract_gender(id_num):
            """从身份证号第 17 位判断性别：奇数=男，偶数=女"""
            if pd.isna(id_num) or len(str(id_num)) < 17:
                return None
            try:
                gender_digit = str(id_num)[16]
                if gender_digit.isdigit():
                    return '男' if int(gender_digit) % 2 == 1 else '女'
                return None
            except:
                return None

        df['birth_date_from_id'] = df['id_number'].apply(extract_birth_date)
        df['age'] = df['birth_date_from_id'].apply(calculate_age)
        df['gender'] = df['id_number'].apply(extract_gender)
    
    return df

def mask_sensitive_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    根据业务规则对敏感字段进行脱敏
    """
    if df.empty: return df
    
    # 字段归类
    names = ['emp_name', 'full_name', 'user_point_name', 'recruiter_name']
    ids = ['id_number']
    mobiles = ['mobile', 'phone']
    companies = ['customer_name', 'account_name', 'social_security_entity', 
                 'merchant_name', 'social_account_name', 'agent_name']

    for col in df.columns:
        if col in names:
            df[col] = df[col].apply(lambda x: str(x)[0] + "*" + str(x)[2:] if pd.notna(x) and len(str(x)) > 1 else x)
        elif col in ids:
            df[col] = df[col].apply(lambda x: str(x)[:6] + "*" * 11 + str(x)[-1:] if pd.notna(x) and len(str(x)) >= 15 else x)
        elif col in mobiles:
            df[col] = df[col].apply(lambda x: str(x)[:3] + "****" + str(x)[-4:] if pd.notna(x) and len(str(x)) >= 11 else x)
        elif col in companies:
            df[col] = df[col].apply(lambda x: ("*" * 6 + str(x)[6:] if len(str(x)) > 6 else "****" + str(x)[4:]) if pd.notna(x) else x)
    return df
