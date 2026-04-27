"""
社保账单和政策下载模块

提供：
- account_bill_download: 社保账单下载
- policy_download: 社保政策查询下载
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from openpyxl import Workbook
from openpyxl.styles import Font

from ..core.path_manager import path_manager
from .data_reader import get_account_bill_data, get_policy_by_city
from .excel_writer import write_to_excel

logger = logging.getLogger("mcp_agent.tools.bill_download")

# 账单字段映射（按模板表头顺序）
BILL_FIELD_MAPPING = {
    "姓名": "姓名",
    "户籍性质": "户籍性质",
    "证件号码": "证件号码",
    "社保缴纳单位": "社保缴纳单位",
    "公积金缴纳单位": "公积金缴纳单位",
    "养老基数": "养老基数",
    "医疗基数": "医疗基数",
    "失业基数": "失业基数",
    "工伤基数": "工伤基数",
    "生育基数": "生育基数",
    "公积金基数": "公积金基数",
    "养老个人": "养老个人",
    "补差养老个人": "补差养老个人",
    "医疗个人": "医疗个人",
    "补差医疗个人": "补差医疗个人",
    "失业个人": "失业个人",
    "补差失业个人": "补差失业个人",
    "公积金个人": "公积金个人",
    "补差公积金个人": "补差公积金个人",
    "养老公司": "养老公司",
    "补差养老公司": "补差养老公司",
    "医疗公司": "医疗公司",
    "补差医疗公司": "补差医疗公司",
    "失业公司": "失业公司",
    "补差失业公司": "补差失业公司",
    "工伤公司": "工伤公司",
    "补差工伤公司": "补差工伤公司",
    "生育公司": "生育公司",
    "补差生育公司": "补差生育公司",
    "公积金公司": "公积金公司",
    "补差公积金公司": "补差公积金公司",
    "服务费": "服务费",
    "工本费": "工本费",
    "档案管理费": "档案管理费",
    "滞纳金（社保）": "滞纳金（社保）",
    "工会费": "工会费",
    "一次性备注": "一次性备注",
    "系统调整备注": "系统调整备注",
    "唯一号": "唯一号",
}

BILL_DEFAULT_VALUES = {
    "序号": "sequence",
    "补差养老个人": 0,
    "补差医疗个人": 0,
    "补差失业个人": 0,
    "补差公积金个人": 0,
    "补差养老公司": 0,
    "补差医疗公司": 0,
    "补差失业公司": 0,
    "补差工伤公司": 0,
    "补差生育公司": 0,
    "补差公积金公司": 0,
    "服务费": 0,
    "工本费": 0,
    "档案管理费": 0,
    "滞纳金（社保）": 0,
    "工会费": 0,
    "一次性备注": "",
    "系统调整备注": "",
    "唯一号": "",
    "养老收费模式": "托收",
    "养老支付方向": 1,
    "疗收费模式": "托收",
    "医疗支付方向": 1,
    "失业收费模式": "托收",
    "失业支付方向": 1,
    "工伤收费模式": "托收",
    "工伤支付方向": 1,
    "生育收费模式": "托收",
    "生育支付方向": 1,
    "公积金收费模式": "托收",
    "公积金支付方向": 1,
    "委托服务费（社保公积金）": 0,
    "增值税": 0,
    "企业缴费": 0,
    "个人缴费": 0,
    "补缴企业合计": 0,
    "补缴个人合计": 0,
    "单立户托收合计": 0,
}

# 政策字段映射
POLICY_FIELD_MAPPING = {
    "city_name_his": "缴纳地名称",
    "city_name": "城市名称",
    "insurance_name": "类型描述",
    "ins_name": "社保类型",
    "min_employee_radix": "个人基数下限",
    "max_employee_radix": "个人基数上限",
    "employee_ratio": "个人缴费比例（%）",
    "rounding_mode": "个人取整规则",
    "employee_pay_amount": "个人附加金额",
    "min_company_radix": "公司基数下限",
    "max_company_radix": "公司基数上限",
    "company_ratio": "公司缴费比例（%）",
    "company_rounding": "公司取整规则",
    "company_pay_amount": "公司附加金额",
    "declare_rule": "每月操作截点--社保",
    "expiration_day": "每月操作截点--公积金",
}


def _update_sheet_header(ws, cost_time: str):
    """更新sheet头部信息"""
    ws["A1"] = f"账单年月：{cost_time}"


def account_bill_download(company_name: str, cost_time: Optional[str] = None) -> str:
    """下载社保账单明细Excel"""
    if cost_time is None:
        cost_time = datetime.now().strftime("%Y-%m")

    try:
        if not company_name or not cost_time:
            return json.dumps(
                {
                    "status": "error",
                    "message": "参数 company_name 和 cost_time 不能为空",
                },
                ensure_ascii=False,
            )

        # 调用data_reader获取数据
        results = get_account_bill_data(company_name, cost_time)

        if not results:
            return json.dumps(
                {
                    "status": "success",
                    "message": "未查询到数据",
                    "company_name": company_name,
                    "cost_time": cost_time,
                    "data_count": 0,
                },
                ensure_ascii=False,
            )

        if len(results) > 199:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"数据行数{len(results)}超过199行限制",
                    "company_name": company_name,
                    "cost_time": cost_time,
                    "data_count": len(results),
                },
                ensure_ascii=False,
            )

        output_dir = path_manager.output_dir
        template_file = output_dir / "FA独立户账单模版-客户版本.xlsx"
        output_file = str(template_file)

        if not template_file.exists():
            return json.dumps(
                {"status": "error", "message": f"模板文件不存在: {template_file}"},
                ensure_ascii=False,
            )

        result = write_to_excel(
            results,
            output_file,
            BILL_FIELD_MAPPING,
            BILL_DEFAULT_VALUES,
            output_file,
            sheet_name="账单明细",
            header_value=f"账单年月：{cost_time}",
        )

        return result

    except Exception as e:
        logger.error(f"账单下载失败: {e}")
        return json.dumps(
            {"status": "error", "message": f"账单下载失败: {str(e)}"},
            ensure_ascii=False,
        )


def policy_download(
    city_name: str = "上海",
    query_date: Optional[str] = None,
    output_file: Optional[str] = None,
) -> str:
    """
    下载社保政策到Excel（Sheet: 基数比例总表）
    """
    if query_date is None:
        query_date = datetime.now().strftime("%Y-%m")

    if output_file is None:
        output_dir = path_manager.output_dir
        output_file = str(output_dir / "FA独立户账单模版-客户版本.xlsx")

    try:
        start_date = query_date + "-01"
        results = get_policy_by_city(
            city_name=city_name, city_id=0, start_date=start_date
        )
        if not results:
            return json.dumps(
                {
                    "status": "success",
                    "message": "未查询到政策数据",
                    "city_name": city_name,
                    "data_count": 0,
                },
                ensure_ascii=False,
            )

        for r in results:
            r["city_name_his"] = r["city_name"]
            r["ins_name"] = r["insurance_name"]
            r["company_rounding"] = r["rounding_mode"]
            r["declare_rule"] = ""
            r["expiration_day"] = ""

        result = write_to_excel(
            results,
            output_file,
            POLICY_FIELD_MAPPING,
            {},
            output_file,
            sheet_name="基数比例总表",
            header_value=f"账单年月：{query_date}",
        )

        return result

    except Exception as e:
        logger.error(f"政策下载失败: {e}")
        return json.dumps(
            {"status": "error", "message": f"政策下载失败: {str(e)}"},
            ensure_ascii=False,
        )


if __name__ == "__main__":
    print(account_bill_download(company_name="三好", cost_time="2026-03"))
