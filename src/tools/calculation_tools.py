"""
社保明细精确计算模块

提供基于政策规则的精确社保计算功能
"""

import json
import logging
from decimal import Decimal, ROUND_HALF_UP, ROUND_UP
from typing import Any, Dict, List, Optional

logger = logging.getLogger("mcp_agent.tools.calculation")


def to_decimal(value: Any) -> Optional[Decimal]:
    """转换为 Decimal"""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    return Decimal(str(value))


def clamp(
    value: Decimal, min_value: Optional[Decimal], max_value: Optional[Decimal]
) -> Decimal:
    """确定缴纳基数"""
    if min_value is not None and value < min_value:
        return min_value
    elif max_value is not None and value > max_value:
        return max_value
    else:
        return value


def apply_rounding(amount: Decimal, rounding_mode: str) -> Decimal:
    if rounding_mode == "1":
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    elif rounding_mode == "2":
        return amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    elif rounding_mode == "3":
        return amount.quantize(Decimal("1"), rounding=ROUND_UP)
    else:
        return amount


def merge_account_policy(account_info: Dict, city_policy: List[Dict]) -> List[Dict]:
    account_policy = [p.copy() for p in city_policy]

    work_injury_ratio = account_info.get("work_injury_company_ratio")
    housing_fund_company_ratio = account_info.get("housing_fund_company_ratio")
    housing_fund_employee_ratio = account_info.get("housing_fund_employee_ratio")

    for p in account_policy:
        item_code = str(p.get("item_code", ""))

        if item_code == "1050" and work_injury_ratio is not None:
            p["company_ratio"] = work_injury_ratio
            p["employee_ratio"] = 0

        if item_code == "2010":
            if housing_fund_company_ratio is not None:
                p["company_ratio"] = housing_fund_company_ratio
            if housing_fund_employee_ratio is not None:
                p["employee_ratio"] = housing_fund_employee_ratio

        if item_code == "2020":
            if housing_fund_company_ratio is not None:
                p["company_ratio"] = housing_fund_company_ratio
            if housing_fund_employee_ratio is not None:
                p["employee_ratio"] = housing_fund_employee_ratio

    return account_policy


def generate_simulated_employees(
    policy: List[Dict], simulate_type: str
) -> List[Dict[str, Any]]:
    pension_policies = [p for p in policy if p.get("item_code") == "1010"]

    if not pension_policies:
        return []

    min_wage = min(
        p.get("min_radix", 0) or p.get("company_min_radix", 0)
        for p in pension_policies
        if p.get("min_radix") or p.get("company_min_radix")
    )
    max_wage = max(
        p.get("max_radix", 0) or p.get("company_max_radix", 0)
        for p in pension_policies
        if p.get("max_radix") or p.get("company_max_radix")
    )

    if min_wage == 0 or max_wage == 0:
        return []

    avg_wage = (min_wage + max_wage) / 2

    if simulate_type == "min":
        return [{"姓名": "社保下限", "证件号码": "SIMULATED-001", "申报工资": min_wage}]
    elif simulate_type == "max":
        return [{"姓名": "社保上限", "证件号码": "SIMULATED-002", "申报工资": max_wage}]
    elif simulate_type == "avg":
        return [{"姓名": "社保平均", "证件号码": "SIMULATED-003", "申报工资": avg_wage}]
    elif simulate_type == "synth":
        return [
            {"姓名": "社保下限", "证件号码": "SIMULATED-001", "申报工资": min_wage},
            {"姓名": "社保平均", "证件号码": "SIMULATED-002", "申报工资": avg_wage},
            {"姓名": "社保上限", "证件号码": "SIMULATED-003", "申报工资": max_wage},
        ]
    return []


def calculate_precise_detail(
    employee: Dict[str, Any],
    policy: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """精确计算单员工的社保明细"""
    declare_salary = Decimal(str(employee.get("申报工资", 0)))
    result = {
        "姓名": employee.get("姓名"),
        "证件号码": employee.get("证件号码"),
        "申报工资": float(declare_salary),
    }

    item_code_map = {
        "1010": "养老",
        "1020": "医疗",
        "1030": "生育",
        "1040": "失业",
        "1050": "工伤",
        "1060": "大额医疗",
        "1070": "长期护理",
        "1080": "补充医疗",
        "2010": "公积金",
        "2020": "补充公积金",
    }
    fund_types = ["公积金", "补充公积金"]

    summary_by_item_code = {}

    for p in policy:
        insurance_name = str(p.get("insurance_name", ""))
        insurance_type = str(p.get("insurance_type", ""))
        insurance_payment_type = str(p.get("insurance_payment_type", ""))
        item_code = str(p.get("item_code", ""))
        
        min_radix = to_decimal(p.get("employee_min_radix")) or to_decimal(
            p.get("min_radix")
        )
        max_radix = to_decimal(p.get("employee_max_radix")) or to_decimal(
            p.get("max_radix")
        )
        company_min = to_decimal(p.get("company_min_radix")) or to_decimal(
            p.get("min_radix")
        )
        company_max = to_decimal(p.get("company_max_radix")) or to_decimal(
            p.get("max_radix")
        )

        # 获取比例
        if insurance_type == "2":  # 公积金
            company_ratio = float(p.get("company_ratio", 0) or 0)
            employee_ratio = float(p.get("employee_ratio", 0) or 0)
        else:  # 社保
            company_ratio = float(
                p.get("company_ratio", 0) or p.get("company_approval_ratio", 0) or 0
            )
            employee_ratio = float(
                p.get("employee_ratio", 0) or p.get("employee_approval_ratio", 0) or 0
            )

        # 固定金额补贴（部分险种如大额医疗用固定金额）
        company_pay = float(p.get("company_pay_amount", 0) or 0)
        employee_pay = float(p.get("employee_pay_amount", 0) or 0)

        # 允许上下限为None（无限制）
        if not min_radix:
            continue

        base = clamp(declare_salary, min_radix, max_radix)
        company_base = clamp(declare_salary, company_min, company_max)

        # 计算金额
        rounding_mode = str(p.get("rounding_mode", "1"))
        if insurance_payment_type == "2":
            company_amount = Decimal(str(company_pay))
            employee_amount = Decimal(str(employee_pay))
        else:
            company_amount = apply_rounding(
                company_base * Decimal(str(company_ratio)) / 100, rounding_mode
            )
            employee_amount = apply_rounding(
                base * Decimal(str(employee_ratio)) / 100, rounding_mode
            )

        # 分类处理
        if insurance_name in fund_types:
            type_name = "补充公积金" if "补充" in insurance_name else "公积金"
            result[f"{type_name}基数"] = float(base)
            result[f"企业{type_name}比例"] = company_ratio
            result[f"个人{type_name}比例"] = employee_ratio
            result[f"{type_name}公司"] = float(company_amount)
            result[f"{type_name}个人"] = float(employee_amount)
            if item_code not in summary_by_item_code:
                summary_by_item_code[item_code] = {
                    "公司": float(company_amount),
                    "个人": float(employee_amount),
                }

        elif item_code in item_code_map:
            type_name = item_code_map[item_code]
            result[f"{type_name}基数"] = float(base)
            result[f"企业{type_name}比例"] = company_ratio
            result[f"个人{type_name}比例"] = employee_ratio
            result[f"{type_name}公司"] = float(company_amount)
            result[f"{type_name}个人"] = float(employee_amount)
            if item_code not in summary_by_item_code:
                summary_by_item_code[item_code] = {
                    "公司": float(company_amount),
                    "个人": float(employee_amount),
                }

    # 计算合计（按 item_code 去重）
    social_company_total = 0
    social_employee_total = 0
    fund_company_total = 0
    fund_employee_total = 0

    for item_code, amounts in summary_by_item_code.items():
        if item_code in ["1010", "1020", "1030", "1040", "1050", "1060", "1070", "1080"]:
            social_company_total += amounts["公司"]
            social_employee_total += amounts["个人"]
        elif item_code in ["2010", "2020"]:
            fund_company_total += amounts["公司"]
            fund_employee_total += amounts["个人"]

    result["社保公司合计"] = social_company_total
    result["社保个人合计"] = social_employee_total
    result["公积金公司合计"] = fund_company_total
    result["公积金个人合计"] = fund_employee_total
    result["企业合计"] = social_company_total + fund_company_total
    result["个人合计"] = social_employee_total + fund_employee_total

    return result


def social_details_calculate(city_name: str, account_name: Optional[str] = None, simulate_type: str = "synth") -> str:
    """
    城市社保明成本明细测算，计算指定城市、社保账户(可选）的社保明细。
    """
    try:
        # 1. 获取账户信息
        from .data_reader import get_account_info, get_policy_by_city

        account_info = get_account_info(city_name=city_name, account_name=account_name or "")
        if not account_info:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"未找到账户 {account_name} 的信息",
                    "account_name": account_name,
                },
                ensure_ascii=False,
            )

        city_name = account_info.get("city_policy_name", "")
        if not city_name:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"未找到账户 {account_name} 对应的城市信息",
                    "account_name": account_name,
                },
                ensure_ascii=False,
            )

        # 2. 获取城市政策
        policy = get_policy_by_city(city_name=city_name, city_id=0)
        if not policy:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"未找到城市 {city_name} 的社保政策",
                    "city_name": city_name,
                },
                ensure_ascii=False,
            )

        # 3. 合并账户比例到城市政策
        account_policy = merge_account_policy(account_info, policy)

        # 4. 生成模拟员工
        employees = generate_simulated_employees(account_policy, simulate_type)

        # 5. 计算明细
        data = []
        for emp in employees:
            detail = calculate_precise_detail(emp, account_policy)
            data.append(detail)

        # 6. 构建汇总
        summary = {"模拟人数": len(data)}
        if len(data) >= 3:
            summary["企业合计_下限"] = data[0].get("企业合计", 0)
            summary["个人合计_下限"] = data[0].get("个人合计", 0)
            summary["企业合计_平均"] = data[1].get("企业合计", 0)
            summary["个人合计_平均"] = data[1].get("个人合计", 0)
            summary["企业合计_上限"] = data[2].get("企业合计", 0)
            summary["个人合计_上限"] = data[2].get("个人合计", 0)

        return json.dumps(
            {
                "status": "success",
                "account_name": account_name,
                "city_name": city_name,
                "simulate_type": simulate_type,
                "data": data,
                "summary": summary,
            },
            ensure_ascii=False,
        )

    except Exception as e:
        logger.error(f"社保计算失败: {e}")
        return json.dumps(
            {"status": "error", "message": f"计算失败: {str(e)}"}, ensure_ascii=False
        )


__all__ = [
    "merge_account_policy",
    "generate_simulated_employees",
    "calculate_precise_detail",
    "social_details_calculate",
]
