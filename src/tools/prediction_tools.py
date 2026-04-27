"""
社保预测模块

提供社保成本预测功能，返回JSON数组供LLM分析
"""

import json
import logging
from typing import Optional, List, Dict, Any

from .data_reader import (
    get_policy_by_city,
    get_employee_info,
    get_account_info,
)

logger = logging.getLogger("mcp_agent.tools.prediction")


def _calculate_cost(
    customer_name: str,
    account_name: str,
    employee: Dict[str, Any], 
    policy: List[Dict[str, Any]], 
    increase_rate: float = 0
) -> Dict[str, Any]:
    """计算单个员工的社保成本"""
    result = {
        "客户名称": customer_name,
        "账户名称": account_name,
        "姓名": employee.get("姓名"),
        "身份证号": employee.get("身份证号"),
        "申报工资": employee.get("申报工资", 0),
    }

    base = float(employee.get("申报工资", 0))
    if increase_rate > 0:
        base = base * (1 + increase_rate)

    for p in policy:
        social_type = p.get("险种类型", "")
        company_ratio = float(p.get("企业比例") or 0)
        employee_ratio = float(p.get("个人比例") or 0)

        company_amount = round(base * company_ratio, 2)
        employee_amount = round(base * employee_ratio, 2)

        if social_type == "养老":
            result["养老企业"] = company_amount
            result["养老个人"] = employee_amount
        elif social_type == "医疗":
            result["医疗企业"] = company_amount
            result["医疗个人"] = employee_amount
        elif social_type == "失业":
            result["失业企业"] = company_amount
            result["失业个人"] = employee_amount
        elif social_type == "工伤":
            result["工伤企业"] = company_amount
            result["工伤个人"] = 0
        elif social_type == "生育":
            result["生育企业"] = company_amount
            result["生育个人"] = 0
        elif social_type == "公积金":
            result["公积金企业"] = company_amount
            result["公积金个人"] = employee_amount

    result["社保企业合计"] = sum(
        [
            result.get("养老企业", 0),
            result.get("医疗企业", 0),
            result.get("失业企业", 0),
            result.get("工伤企业", 0),
            result.get("生育企业", 0),
        ]
    )
    result["社保个人合计"] = sum(
        [
            result.get("养老个人", 0),
            result.get("医疗个人", 0),
            result.get("失业个人", 0),
        ]
    )
    result["公积金合计"] = result.get("公积金企业", 0) + result.get("公积金个人", 0)

    return result


def social_security_predict(
    customer_name: Optional[str] = None,
    account_name: Optional[str] = None,
    merchant_name: Optional[str] = None,
    city_name: Optional[str] = None,
    increase_rate: float = 0,
) -> str:
    """
    社保成本预测

    Args:
        customer_name: 客户名称
        account_name: 社保账户名称
        merchant_name: 服务商名称
        city_name: 城市名称
        increase_rate: 涨幅比例（默认 0）

    Returns:
        JSON 数组（供 LLM 分析）
    """
    try:
        if not customer_name and not account_name and not city_name:
            return json.dumps(
                {
                    "status": "error",
                    "message": "请提供 customer_name 或 account_name 或 city_name",
                },
                ensure_ascii=False,
            )

        results = []
        employees = []
        policy = []

        if account_name:
            employees = get_employee_info(account_name=account_name)
            if employees:
                city = employees[0].get("城市", "")
                policy = get_policy_by_city(city_name=city) if city else []

        elif customer_name:
            employees = get_employee_info(company_name=customer_name)
            if employees:
                city = employees[0].get("城市", "")
                policy = get_policy_by_city(city_name=city) if city else []

        elif city_name:
            account_info = get_account_info(
                city_name=city_name,
                account_name=account_name,
            )
            if account_info:
                account_name_result = account_info.get("account_name", "")
                employees = get_employee_info(account_name=account_name_result)
                if employees:
                    city = employees[0].get("城市", "")
                    policy = get_policy_by_city(city_name=city) if city else []

            if not policy:
                policy = get_policy_by_city(city_name=city_name)

        if not policy:
            return json.dumps(
                {"status": "error", "message": "未找到社保政策"},
                ensure_ascii=False,
            )

        if not employees:
            wages = [
                min(
                    p.get("企业最低基数", 0) or 0
                    for p in policy
                    if p.get("企业最低基数")
                ),
                (
                    min(
                        p.get("企业最低基数", 0) or 0
                        for p in policy
                        if p.get("企业最低基数")
                    )
                    + max(
                        p.get("企业最高基数", 0) or 0
                        for p in policy
                        if p.get("企业最高基数")
                    )
                )
                / 2,
                max(
                    p.get("企业最高基数", 0) or 0
                    for p in policy
                    if p.get("企业最高基数")
                ),
            ]

            for i, wage in enumerate(wages):
                emp = {
                    "姓名": ["下限", "中间", "上限"][i],
                    "身份证号": f"虚拟-{i + 1}",
                    "申报工资": wage,
                }
                result = _calculate_cost(
                    customer_name=customer_name or "",
                    account_name=account_name or "",
                    employee=emp,
                    policy=policy,
                    increase_rate=increase_rate,
                )
                result["类型"] = ["最低基数", "中间基数", "最高基数"][i]
                results.append(result)
        else:
            for emp in employees:
                result = _calculate_cost(
                    customer_name=customer_name or "",
                    account_name=account_name or "",
                    employee=emp,
                    policy=policy,
                    increase_rate=increase_rate,
                )
                results.append(result)

        return json.dumps(
            {"status": "success", "data": results, "count": len(results)},
            ensure_ascii=False,
        )

    except Exception as e:
        logger.error(f"社保预测失败：{e}")
        return json.dumps(
            {"status": "error", "message": f"预测失败：{str(e)}"}, ensure_ascii=False
        )



__all__ = [
    "social_security_predict",
]
