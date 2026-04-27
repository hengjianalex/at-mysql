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
    """应用进位规则"""
    if rounding_mode == "1":
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    elif rounding_mode == "2":
        return amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    elif rounding_mode == "3":
        return amount.quantize(Decimal("1"), rounding=ROUND_UP)
    else:
        return amount


def generate_simulated_employees(
    policy: List[Dict], simulate_type: str
) -> List[Dict[str, Any]]:
    """根据模拟类型生成虚拟员工数据"""
    min_wage = min(
        p.get("min_radix", 0) or p.get("company_min_radix", 0)
        for p in policy
        if p.get("min_radix") or p.get("company_min_radix")
    )
    max_wage = max(
        p.get("max_radix", 0) or p.get("company_max_radix", 0)
        for p in policy
        if p.get("max_radix") or p.get("company_max_radix")
    )
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
    separated_radix: bool = False,
) -> Dict[str, Any]:
    """精确计算单员工的社保明细"""
    declare_salary = Decimal(str(employee.get("申报工资", 0)))
    result = {
        "姓名": employee.get("姓名"),
        "证件号码": employee.get("证件号码"),
        "申报工资": float(declare_salary),
    }

    # 险种分类标识
    # 养老类险种（合并）
    pension_types = [
        "养老保险",
        "养老保险(深户)",
        "养老保险(非深户)",
        "养老保险（深户）",
        "养老保险（非深户）",
    ]
    # 医疗类险种（合并）
    medical_types = [
        "医疗保险(含生育)",
        "医疗保险（含生育）",
        "医疗保险（一档）",
        "医疗保险（二档）",
        "医疗保险",
        "补充医疗（地方附加）",
        "大额医疗补助",
        "大额医疗费用补助",
        "医疗保险(一档)",
        "医疗保险(二档)",
        "医疗保险（一档）",
        "医疗保险（二档）",
    ]
    # 公积金类险种（分开显示）
    fund_types = ["公积金", "补充公积金"]
    # 其他险种（直接映射）
    other_map = {
        "失业保险": "失业",
        "工伤保险": "工伤",
        "生育保险": "生育",
    }

    # 用于累积医疗险种数据
    medical_company_ratio = 0.0
    medical_employee_ratio = 0.0
    medical_company_amount = Decimal("0")
    medical_employee_amount = Decimal("0")
    medical_base = None
    medical_has_data = False

    # 用于累积养老险种数据（取最后一个有数据的）
    pension_base = None
    pension_company_ratio = 0.0
    pension_employee_ratio = 0.0
    pension_company_amount = Decimal("0")
    pension_employee_amount = Decimal("0")
    pension_has_data = False

    for p in policy:
        insurance_name = str(p.get("insurance_name", ""))
        insurance_type = str(p.get("insurance_type", ""))

        # 判断基数上下限
        if separated_radix:
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
        else:
            min_radix = to_decimal(p.get("min_radix"))
            max_radix = to_decimal(p.get("max_radix"))
            company_min = min_radix
            company_max = max_radix

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
        # 如果有固定金额，使用固定金额
        if company_pay > 0 or employee_pay > 0:
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
        if insurance_name in pension_types:
            # 养老类：取有数据的（深圳优先取非深户）
            if insurance_name == "养老保险(非深户)" and pension_has_data:
                continue
            pension_base = base
            pension_company_ratio = company_ratio
            pension_employee_ratio = employee_ratio
            pension_company_amount = company_amount
            pension_employee_amount = employee_amount
            pension_has_data = True

        elif insurance_name in medical_types:
            # 深圳医疗：只取二档
            if "一档" in insurance_name and medical_has_data:
                continue  # 已有二档，跳过一档
            # 医疗类：累加
            medical_company_ratio += company_ratio
            medical_employee_ratio += employee_ratio
            medical_company_amount += company_amount
            medical_employee_amount += employee_amount
            if medical_base is None:
                medical_base = base
            medical_has_data = True

        elif insurance_name in fund_types:
            # 公积金类：分开显示
            type_name = "补充公积金" if "补充" in insurance_name else "公积金"
            result[f"{type_name}基数"] = float(base)
            result[f"企业{type_name}比例"] = company_ratio
            result[f"个人{type_name}比例"] = employee_ratio
            result[f"{type_name}公司"] = float(company_amount)
            result[f"{type_name}个人"] = float(employee_amount)

        elif insurance_name in other_map:
            # 其他险种：直接映射
            type_name = other_map[insurance_name]
            result[f"{type_name}基数"] = float(base)
            result[f"企业{type_name}比例"] = company_ratio
            result[f"个人{type_name}比例"] = employee_ratio
            result[f"{type_name}公司"] = float(company_amount)
            result[f"{type_name}个人"] = float(employee_amount)

    # 写入养老险种结果
    if pension_has_data:
        result["养老基数"] = float(pension_base)
        result["企业养老比例"] = pension_company_ratio
        result["个人养老比例"] = pension_employee_ratio
        result["养老公司"] = float(pension_company_amount)
        result["养老个人"] = float(pension_employee_amount)

    # 写入医疗险种结果
    if medical_has_data:
        result["医疗基数"] = float(medical_base)
        result["企业医疗比例"] = medical_company_ratio
        result["个人医疗比例"] = medical_employee_ratio
        result["医疗公司"] = float(medical_company_amount)
        result["医疗个人"] = float(medical_employee_amount)

    # 计算合计
    result["社保公司合计"] = (
        result.get("养老公司", 0)
        + result.get("医疗公司", 0)
        + result.get("失业公司", 0)
        + result.get("工伤公司", 0)
        + result.get("生育公司", 0)
    )
    result["社保个人合计"] = (
        result.get("养老个人", 0)
        + result.get("医疗个人", 0)
        + result.get("失业个人", 0)
        + result.get("工伤个人", 0)
        + result.get("生育个人", 0)
    )
    result["公积金公司合计"] = result.get("公积金公司", 0) + result.get(
        "补充公积金公司", 0
    )
    result["公积金个人合计"] = result.get("公积金个人", 0) + result.get(
        "补充公积金个人", 0
    )
    result["企业合计"] = result.get("社保公司合计", 0) + result.get("公积金公司合计", 0)
    result["个人合计"] = result.get("社保个人合计", 0) + result.get("公积金个人合计", 0)

    return result


def social_security_calculate(
    account_name: str, simulate_type: str = "synth", separated_radix: bool = False
) -> str:
    """
    社保明细精确计算

    Args:
        account_name: 社保账户名称
        simulate_type: 模拟类型 (min/max/avg/synth)
        separated_radix: 是否分基数

    Returns:
        JSON 格式的计算结果
    """
    try:
        # 1. 获取账户信息
        from .data_reader import get_account_info, get_policy_by_city

        account_info = get_account_info(account_name=account_name)
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

        # 3. 生成模拟员工
        employees = generate_simulated_employees(policy, simulate_type)

        # 4. 计算明细
        data = []
        for emp in employees:
            detail = calculate_precise_detail(emp, policy, separated_radix)
            data.append(detail)

        # 5. 构建汇总
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
                "separated_radix": separated_radix,
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
    "generate_simulated_employees",
    "calculate_precise_detail",
    "social_security_calculate",
]
