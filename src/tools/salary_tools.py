"""
薪资计算器模块

提供薪资计算和Excel导出功能
"""

import json
import logging
from typing import Optional, List, Dict, Any

from .data_reader import get_account_bill_data, get_employee_info
from .excel_writer import write_to_excel

logger = logging.getLogger("mcp_agent.tools.salary")


def _calculate_salary(
    employee: Dict[str, Any], bill_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """计算单个员工的薪资"""
    emp_name = employee.get("姓名")

    matching_bills = [b for b in bill_data if b.get("姓名") == emp_name]

    result = {
        "姓名": emp_name,
        "身份证号": employee.get("身份证号"),
    }

    if matching_bills:
        bill = matching_bills[0]
        result["基本工资"] = bill.get("养老基数", 0)
        result["养老企业"] = bill.get("养老公司", 0)
        result["医疗企业"] = bill.get("医疗公司", 0)
        result["失业企业"] = bill.get("失业公司", 0)
        result["工伤企业"] = bill.get("工伤公司", 0)
        result["生育企业"] = bill.get("生育公司", 0)
        result["公积金企业"] = bill.get("公积金公司", 0)
        result["社保公司合计"] = bill.get("社保公司合计", 0)
        result["公积金公司合计"] = bill.get("公积金公司合计", 0)

        result["养老个人"] = bill.get("养老个人", 0)
        result["医疗个人"] = bill.get("医疗个人", 0)
        result["失业个人"] = bill.get("失业个人", 0)
        result["公积金个人"] = bill.get("公积金个人", 0)
        result["社保个人合计"] = bill.get("社保个人合计", 0)
        result["公积金个人合计"] = bill.get("公积金个人合计", 0)
    else:
        result["基本工资"] = 0
        result["养老企业"] = 0
        result["医疗企业"] = 0
        result["失业企业"] = 0
        result["工伤企业"] = 0
        result["生育企业"] = 0
        result["公积金企业"] = 0
        result["社保公司合计"] = 0
        result["公积金公司合计"] = 0
        result["养老个人"] = 0
        result["医疗个人"] = 0
        result["失业个人"] = 0
        result["公积金个人"] = 0
        result["社保个人合计"] = 0
        result["公积金个人合计"] = 0

    result["岗位津贴"] = 0
    result["绩效"] = 0
    result["加班费"] = 0
    result["个税"] = 0

    result["应发工资"] = (
        result.get("基本工资")
        or 0 + result.get("岗位津贴")
        or 0 + result.get("绩效")
        or 0 + result.get("加班费")
        or 0
    )

    result["实发工资"] = (
        result["应发工资"]
        - result.get("社保个人合计", 0)
        - result.get("公积金个人合计", 0)
        - result.get("个税", 0)
    )

    return result


def salary_calculator(
    company_name: str,
    cost_time: str,
    output_file: Optional[str] = None,
    template: str = "薪资模板.xlsx",
) -> str:
    """
    薪资计算器

    Args:
        company_name: 客户名称
        cost_time: 月份 (YYYY-MM)
        output_file: 输出文件路径
        template: 模板文件名

    Returns:
        JSON结果 + Excel文件
    """
    try:
        bill_data = get_account_bill_data(company_name, cost_time)
        if not bill_data:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"未找到 {company_name} 在 {cost_time} 的账单数据",
                },
                ensure_ascii=False,
            )

        employees = get_employee_info(company_name)
        if not employees:
            return json.dumps(
                {"status": "error", "message": f"未找到 {company_name} 的员工信息"},
                ensure_ascii=False,
            )

        results = []
        for emp in employees:
            salary = _calculate_salary(emp, bill_data)
            results.append(salary)

        if output_file:
            field_mapping = {
                "姓名": "姓名",
                "身份证号": "身份证号",
                "基本工资": "基本工资",
                "岗位津贴": "岗位津贴",
                "绩效": "绩效",
                "加班费": "加班费",
                "社保公司合计": "社保公司合计",
                "公积金公司合计": "公积金公司合计",
                "个税": "个税",
                "实发工资": "实发工资",
            }

            default_values = {
                "序号": 1,
                "基本工资": 0,
                "岗位津贴": 0,
                "绩效": 0,
                "加班费": 0,
                "社保公司合计": 0,
                "公积金公司合计": 0,
                "个税": 0,
                "实发工资": 0,
            }

            result = write_to_excel(
                results, template, field_mapping, default_values, output_file
            )

            return result
        else:
            return json.dumps(
                {"status": "success", "data": results, "count": len(results)},
                ensure_ascii=False,
            )

    except Exception as e:
        logger.error(f"薪资计算失败：{e}")
        return json.dumps(
            {"status": "error", "message": f"计算失败：{str(e)}"}, ensure_ascii=False
        )


__all__ = [
    "salary_calculator",
]
