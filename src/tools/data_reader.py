"""
数据读取层模块

提供SQL查询、数据封装等通用数据获取功能
"""

import json
import logging
from typing import Optional, List, Dict, Any

from ..core.db_connection import db_manager

logger = logging.getLogger("mcp_agent.tools.data_reader")


def get_account_bill_data(company_name: str, cost_time: str) -> List[Dict[str, Any]]:
    """
    从SQL查询社保账单明细

    Args:
        company_name: 客户名称
        cost_time: 账单月份 (YYYY-MM)

    Returns:
        账单数据列表
    """
    if not company_name or not cost_time:
        return []

    try:
        query = """
        WITH acc AS (
            SELECT acc.id, tc.id AS customer_id, acc.account_name, acc.account_type, acc.code AS account_code, acc.uscc_code,
                   acc.agent_id, acc.city_id, acc.account_district
            FROM soi_account acc
            INNER JOIN hro_customer tc ON tc.id = acc.apply_id AND acc.account_type = '1'
            WHERE tc.name LIKE CONCAT('%%', %s, '%%')
            UNION
            SELECT acc.id, rel.customer_id, acc.account_name, acc.account_type, acc.code AS account_code, acc.uscc_code,
                   acc.agent_id, acc.city_id, acc.account_district
            FROM soi_acc_merchant_rel AS rel
            INNER JOIN soi_account acc ON rel.account_id = acc.id AND acc.account_type = '2'
            INNER JOIN hro_customer tc ON tc.id = rel.customer_id
            WHERE tc.name LIKE CONCAT('%%', %s, '%%')
        ),
        tt AS (
            SELECT insured_id,
            calc_id,
            cost_type AS ref_cost_type,
            dd.start_time,
            dd.cost_month,
            DATE_FORMAT(bill.start_time, '%%Y-%%m') AS bill_month,
            item_code,
            acc.customer_id,
            acc.account_name,
            ROUND(IFNULL(company_base, 0.00), 6) company_base,
            ROUND(IFNULL(employee_base, 0.00), 6) employee_base,
            ROUND(IFNULL(company_ratio, 0) / 100, 6) company_ratio,
            ROUND(IFNULL(employee_ratio, 0) / 100, 6) employee_ratio,
            ROUND(IFNULL(company_amount, 0.00), 6) company_amount,
            ROUND(IFNULL(employee_amount, 0.00), 6) employee_amount
            FROM soi_acc_bill AS bill
            INNER JOIN soi_acc_bill_detail AS dd ON bill.id = dd.calc_id
            INNER JOIN acc ON dd.account_id = acc.id
            WHERE bill.start_time >= %s
            AND bill.send_status = '1'
        ),
        inst AS (
            SELECT account_id, insured_id, MIN(start_time) AS start_time, MAX(no_cost_time) AS no_cost_time
            FROM soi_insured_insurance
            GROUP BY account_id, insured_id
        ),
        wrt AS (
            SELECT DISTINCT insured_id, start_time, ref_cost_type
            FROM tt
            WHERE ref_cost_type IN ('1', '2', '3', '4', '5')
        ),
        wt AS (
            SELECT tt.*,
            IFNULL(
                CASE WHEN (tt.ref_cost_type = '7') THEN wrt.ref_cost_type ELSE tt.ref_cost_type END,
                '7'
            ) AS cost_type
            FROM tt
            LEFT JOIN wrt ON tt.insured_id = wrt.insured_id AND tt.start_time = wrt.start_time
        ),
        wtt AS (
            SELECT insured_id,
            calc_id,
            cost_type AS bill_cost_type,
            ref_cost_type,
            bill_month,
            start_time,
            DATE_FORMAT(start_time, '%%Y-%%m') AS cost_month,
            customer_id,
            account_name,
            SUM(CASE WHEN item_code = '1010' THEN company_base ELSE 0 END) AS company_base_1010,
            SUM(CASE WHEN item_code = '1020' THEN company_base ELSE 0 END) AS company_base_1020,
            SUM(CASE WHEN item_code = '1030' THEN company_base ELSE 0 END) AS company_base_1030,
            SUM(CASE WHEN item_code = '1040' THEN company_base ELSE 0 END) AS company_base_1040,
            SUM(CASE WHEN item_code = '1050' THEN company_base ELSE 0 END) AS company_base_1050,
            SUM(CASE WHEN item_code = '1060' THEN company_base ELSE 0 END) AS company_base_1060,
            SUM(CASE WHEN item_code = '1070' THEN company_base ELSE 0 END) AS company_base_1070,
            SUM(CASE WHEN item_code = '1080' THEN company_base ELSE 0 END) AS company_base_1080,
            SUM(CASE WHEN item_code = '2010' THEN company_base ELSE 0 END) AS company_base_2010,
            SUM(CASE WHEN item_code = '2020' THEN company_base ELSE 0 END) AS company_base_2020,
            SUM(CASE WHEN item_code = '1010' THEN employee_base ELSE 0 END) AS employee_base_1010,
            SUM(CASE WHEN item_code = '1020' THEN employee_base ELSE 0 END) AS employee_base_1020,
            SUM(CASE WHEN item_code = '1030' THEN employee_base ELSE 0 END) AS employee_base_1030,
            SUM(CASE WHEN item_code = '1040' THEN employee_base ELSE 0 END) AS employee_base_1040,
            SUM(CASE WHEN item_code = '1050' THEN employee_base ELSE 0 END) AS employee_base_1050,
            SUM(CASE WHEN item_code = '1060' THEN employee_base ELSE 0 END) AS employee_base_1060,
            SUM(CASE WHEN item_code = '1070' THEN employee_base ELSE 0 END) AS employee_base_1070,
            SUM(CASE WHEN item_code = '1080' THEN employee_base ELSE 0 END) AS employee_base_1080,
            SUM(CASE WHEN item_code = '2010' THEN employee_base ELSE 0 END) AS employee_base_2010,
            SUM(CASE WHEN item_code = '2020' THEN employee_base ELSE 0 END) AS employee_base_2020,
            SUM(CASE WHEN item_code = '1010' THEN company_ratio ELSE 0 END) AS company_ratio_1010,
            SUM(CASE WHEN item_code = '1020' THEN company_ratio ELSE 0 END) AS company_ratio_1020,
            SUM(CASE WHEN item_code = '1030' THEN company_ratio ELSE 0 END) AS company_ratio_1030,
            SUM(CASE WHEN item_code = '1040' THEN company_ratio ELSE 0 END) AS company_ratio_1040,
            SUM(CASE WHEN item_code = '1050' THEN company_ratio ELSE 0 END) AS company_ratio_1050,
            SUM(CASE WHEN item_code = '1060' THEN company_ratio ELSE 0 END) AS company_ratio_1060,
            SUM(CASE WHEN item_code = '1070' THEN company_ratio ELSE 0 END) AS company_ratio_1070,
            SUM(CASE WHEN item_code = '1080' THEN company_ratio ELSE 0 END) AS company_ratio_1080,
            SUM(CASE WHEN item_code = '2010' THEN company_ratio ELSE 0 END) AS company_ratio_2010,
            SUM(CASE WHEN item_code = '2020' THEN company_ratio ELSE 0 END) AS company_ratio_2020,
            SUM(CASE WHEN item_code = '1010' THEN employee_ratio ELSE 0 END) AS employee_ratio_1010,
            SUM(CASE WHEN item_code = '1020' THEN employee_ratio ELSE 0 END) AS employee_ratio_1020,
            SUM(CASE WHEN item_code = '1030' THEN employee_ratio ELSE 0 END) AS employee_ratio_1030,
            SUM(CASE WHEN item_code = '1040' THEN employee_ratio ELSE 0 END) AS employee_ratio_1040,
            SUM(CASE WHEN item_code = '1050' THEN employee_ratio ELSE 0 END) AS employee_ratio_1050,
            SUM(CASE WHEN item_code = '1060' THEN employee_ratio ELSE 0 END) AS employee_ratio_1060,
            SUM(CASE WHEN item_code = '1070' THEN employee_ratio ELSE 0 END) AS employee_ratio_1070,
            SUM(CASE WHEN item_code = '1080' THEN employee_ratio ELSE 0 END) AS employee_ratio_1080,
            SUM(CASE WHEN item_code = '2010' THEN employee_ratio ELSE 0 END) AS employee_ratio_2010,
            SUM(CASE WHEN item_code = '2020' THEN employee_ratio ELSE 0 END) AS employee_ratio_2020,
            SUM(CASE WHEN item_code = '1010' THEN company_amount ELSE 0 END) AS company_amount_1010,
            SUM(CASE WHEN item_code = '1020' THEN company_amount ELSE 0 END) AS company_amount_1020,
            SUM(CASE WHEN item_code = '1030' THEN company_amount ELSE 0 END) AS company_amount_1030,
            SUM(CASE WHEN item_code = '1040' THEN company_amount ELSE 0 END) AS company_amount_1040,
            SUM(CASE WHEN item_code = '1050' THEN company_amount ELSE 0 END) AS company_amount_1050,
            SUM(CASE WHEN item_code = '1060' THEN company_amount ELSE 0 END) AS company_amount_1060,
            SUM(CASE WHEN item_code = '1070' THEN company_amount ELSE 0 END) AS company_amount_1070,
            SUM(CASE WHEN item_code = '1080' THEN company_amount ELSE 0 END) AS company_amount_1080,
            SUM(CASE WHEN item_code = '2010' THEN company_amount ELSE 0 END) AS company_amount_2010,
            SUM(CASE WHEN item_code = '2020' THEN company_amount ELSE 0 END) AS company_amount_2020,
            SUM(CASE WHEN item_code = '3000' THEN company_amount ELSE 0 END) AS company_amount_3000,
            SUM(CASE WHEN item_code = '1010' THEN employee_amount ELSE 0 END) AS employee_amount_1010,
            SUM(CASE WHEN item_code = '1020' THEN employee_amount ELSE 0 END) AS employee_amount_1020,
            SUM(CASE WHEN item_code = '1030' THEN employee_amount ELSE 0 END) AS employee_amount_1030,
            SUM(CASE WHEN item_code = '1040' THEN employee_amount ELSE 0 END) AS employee_amount_1040,
            SUM(CASE WHEN item_code = '1050' THEN employee_amount ELSE 0 END) AS employee_amount_1050,
            SUM(CASE WHEN item_code = '1060' THEN employee_amount ELSE 0 END) AS employee_amount_1060,
            SUM(CASE WHEN item_code = '1070' THEN employee_amount ELSE 0 END) AS employee_amount_1070,
            SUM(CASE WHEN item_code = '1080' THEN employee_amount ELSE 0 END) AS employee_amount_1080,
            SUM(CASE WHEN item_code = '2010' THEN employee_amount ELSE 0 END) AS employee_amount_2010,
            SUM(CASE WHEN item_code = '2020' THEN employee_amount ELSE 0 END) AS employee_amount_2020,
            SUM(CASE WHEN item_code = '3000' THEN employee_amount ELSE 0 END) AS employee_amount_3000
            FROM wt
            GROUP BY insured_id, calc_id, cost_type, bill_month, start_time, customer_id, account_name, ref_cost_type
        ),
        wlt AS (
            SELECT wtt.*,
            company_amount_1010 + company_amount_1020 + company_amount_1030 + company_amount_1040 +
            company_amount_1050 + company_amount_1060 + company_amount_1070 + company_amount_1080 +
            company_amount_3000 AS company_10_total,
            company_amount_2010 + company_amount_2020 AS company_20_total,
            employee_amount_1010 + employee_amount_1020 + employee_amount_1030 + employee_amount_1040 +
            employee_amount_1050 + employee_amount_1060 + employee_amount_1070 + employee_amount_1080 +
            employee_amount_3000 AS employee_10_total,
            employee_amount_2010 + employee_amount_2020 AS employee_20_total
            FROM wtt
        ),
        wtr AS (
            SELECT emp.emp_name AS '姓名',
            emp.id_type AS '户籍性质',
            emp.id_number AS '证件号码',
            acc.account_name AS '社保缴纳单位',
            acc.account_name AS '公积金缴纳单位',
            city.city_name AS '城市',
            DATE_FORMAT(inst.start_time, '%%Y-%%m') AS '入职日期',
            DATE_FORMAT(inst.no_cost_time, '%%Y-%%m') AS '离职日期',
            wlt.bill_month AS '账单年月',
            wlt.cost_month AS '服务年月',
            wlt.company_base_1010 AS '养老基数',
            wlt.company_base_1020 AS '医疗基数',
            wlt.company_base_1030 AS '失业基数',
            wlt.company_base_1040 AS '工伤基数',
            wlt.company_base_1050 AS '生育基数',
            wlt.company_base_2010 AS '公积金基数',
            wlt.employee_base_1010 AS '个人养老基数',
            wlt.employee_base_1020 AS '个人医疗基数',
            wlt.employee_base_1030 AS '个人失业基数',
            wlt.employee_base_2010 AS '个人公积金基数',
            wlt.company_ratio_1010 AS '企业养老比例',
            wlt.company_ratio_1020 AS '企业医疗比例',
            wlt.company_ratio_1030 AS '企业失业比例',
            wlt.company_ratio_2010 AS '企业公积金比例',
            wlt.employee_ratio_1010 AS '个人养老比例',
            wlt.employee_ratio_1020 AS '个人医疗比例',
            wlt.employee_ratio_1030 AS '个人失业比例',
            wlt.employee_ratio_2010 AS '个人公积金比例',
            wlt.company_amount_1010 AS '养老公司',
            wlt.company_amount_1020 AS '医疗公司',
            wlt.company_amount_1030 AS '失业公司',
            wlt.company_amount_1040 AS '工伤公司',
            wlt.company_amount_1050 AS '生育公司',
            wlt.company_amount_2010 AS '公积金公司',
            wlt.company_amount_3000 AS '公积金补缴公司',
            wlt.employee_amount_1010 AS '养老个人',
            wlt.employee_amount_1020 AS '医疗个人',
            wlt.employee_amount_1030 AS '失业个人',
            wlt.employee_amount_2010 AS '公积金个人',
            wlt.employee_amount_3000 AS '公积金补缴个人',
            wlt.company_10_total AS '社保公司合计',
            wlt.company_20_total AS '公积金公司合计',
            wlt.employee_10_total AS '社保个人合计',
            wlt.employee_20_total AS '公积金个人合计',
            wlt.customer_id,
            ind.account_id,
            wlt.bill_cost_type,
            wlt.cost_month
            FROM wlt
            LEFT JOIN soi_insured_info AS ind ON wlt.insured_id = ind.id
            LEFT JOIN inst ON wlt.insured_id = inst.insured_id AND ind.account_id = inst.account_id
            LEFT JOIN hro_customer AS cc ON ind.customer_id = cc.id
            LEFT JOIN hro_emp_info AS emp ON ind.emp_id = emp.id
            LEFT JOIN hro_merchant AS mer ON ind.merchant_id = mer.id
            LEFT JOIN hro_agent AS agent ON ind.agent_id = agent.id
            LEFT JOIN soi_account AS acc ON ind.account_id = acc.id
            LEFT JOIN hro_soi_city AS city ON acc.city_id = city.id
            WHERE wlt.insured_id IS NOT NULL
            AND cc.name LIKE CONCAT('%%', %s, '%%')
        )
        SELECT 姓名, 户籍性质, 证件号码, 社保缴纳单位, 公积金缴纳单位, 城市, 入职日期, 离职日期,
               账单年月, 服务年月, 养老基数, 医疗基数, 失业基数, 工伤基数, 生育基数, 公积金基数,
               个人养老基数, 个人医疗基数, 个人失业基数, 个人公积金基数,
               企业养老比例, 企业医疗比例, 企业失业比例, 企业公积金比例,
               个人养老比例, 个人医疗比例, 个人失业比例, 个人公积金比例,
               养老公司, 医疗公司, 失业公司, 工伤公司, 生育公司, 公积金公司, 公积金补缴公司,
               养老个人, 医疗个人, 失业个人, 公积金个人, 公积金补缴个人,
               社保公司合计, 公积金公司合计, 社保个人合计, 公积金个人合计
        FROM wtr
        ORDER BY customer_id, account_id, bill_cost_type DESC, cost_month DESC
        """

        params = (company_name, company_name, f"{cost_time}-01", company_name)
        results = db_manager.execute_query(
            query, server_id="YIFEI", params=params, max_rows=50000
        )
        return results or []

    except Exception as e:
        logger.error(f"查询社保账单数据失败：{e}")
        return []


def get_policy_by_city(
    city_name: str, city_id: Optional[int] = None, start_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    按城市查询社保政策

    Args:
        city_name: 城市名称
        city_id: 城市ID
        start_date: 查询开始日期 (YYYY-MM-DD, 默认当前日期)
    Returns:
        政策列表：养老/医疗/失业/工伤/生育/公积金 比例
    """
    if not city_name:
        return []

    try:
        query = """
            SELECT 
                city.city_name, 
                city.id AS city_id,
                insc.code AS insurance_code, 
                insc.name AS insurance_name, 
                insc.code AS item_code,
                insc.payment_type as insurance_payment_type,
                his.adjust_serial, 
                his.start_time, 
                his.min_radix, 
                his.max_radix, 
                his.min_company_radix AS company_min_radix, 
                his.max_company_radix AS company_max_radix, 
                his.min_employee_radix AS employee_min_radix, 
                his.max_employee_radix AS employee_max_radix, 
                his.company_ratio, 
                his.employee_ratio, 
                his.company_pay_amount, 
                his.employee_pay_amount,
                his.rounding_mode,
                his.is_same_ratio
            FROM (
                SELECT his.*, 
                        ROW_NUMBER() OVER (PARTITION BY his.insurance_id ORDER BY his.adjust_serial DESC) AS rn
                FROM soi_city_insurance_his his
                WHERE 1=1
        """

        # 2. 处理 {period_condition} 逻辑
        # 如果提供了 start_date，则使用参数化查询；否则默认使用数据库当前日期
        if start_date:
            query += " AND his.start_time <= %s"
        else:
            query += " AND his.start_time <= CURRENT_DATE"

        # 3. 拼接中间关联部分
        query += """
            ) AS his
            INNER JOIN soi_city_insurance AS insc ON his.insurance_id = insc.id 
            INNER JOIN soi_city_policy AS policy ON insc.policy_id = policy.id 
            INNER JOIN hro_soi_city AS city ON policy.city_ids = CONCAT(city.id)
            WHERE his.rn = 1
        """

        # 4. 处理 {conditions} 逻辑 (城市过滤)
        if city_id:
            query += " AND city.id = %s"
            params = (city_id,)
        else:
            query += " AND (city.city_name LIKE CONCAT('%%', %s, '%%') OR policy.name LIKE CONCAT('%%', %s, '%%'))"
            params = (city_name, city_name)
        if start_date:
            params = (start_date,) + params

        # 6. 加上排序
        query += " ORDER BY insc.code"

        results = db_manager.execute_query(
            query, server_id="YIFEI", params=params, max_rows=100
        )
        return results or []

    except Exception as e:
        logger.error(f"查询城市政策失败：{e}")
        return []


def get_employee_info(
    company_name: Optional[str] = None, account_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    查询员工基本信息

    Args:
        company_name: 客户名称（可选）
        account_name: 账户名称（可选）

    Returns:
        员工信息列表：姓名、身份证、申报工资等
    """
    try:
        conditions = []
        params = []

        if company_name:
            conditions.append("tc.name LIKE CONCAT('%%', %s, '%%')")
            params.append(company_name)

        if account_name:
            conditions.append("acc.account_name LIKE CONCAT('%%', %s, '%%')")
            params.append(account_name)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
        SELECT 
            emp.emp_name AS 姓名,
            emp.id_number AS 身份证号,
            emp.id_type AS 户籍性质,
            emp.phone_number AS 手机号,
            acc.account_name AS 账户名称,
            city.city_name AS 城市,
            DATE_FORMAT(inst.start_time, '%%Y-%%m') AS 入职月份,
            inst.no_cost_time AS 离职月份
        FROM soi_insured_info AS ind
        LEFT JOIN hro_customer AS tc ON ind.customer_id = tc.id
        LEFT JOIN hro_emp_info AS emp ON ind.emp_id = emp.id
        LEFT JOIN soi_account AS acc ON ind.account_id = acc.id
        LEFT JOIN hro_soi_city AS city ON acc.city_id = city.id
        LEFT JOIN (
            SELECT account_id, insured_id, MIN(start_time) AS start_time, MAX(no_cost_time) AS no_cost_time
            FROM soi_insured_insurance
            GROUP BY account_id, insured_id
        ) AS inst ON ind.account_id = inst.account_id AND ind.id = inst.insured_id
        WHERE {where_clause}
        ORDER BY tc.name, emp.emp_name
        """

        results = db_manager.execute_query(
            query, server_id="YIFEI", params=tuple(params), max_rows=1000
        )
        return results or []

    except Exception as e:
        logger.error(f"查询员工信息失败：{e}")
        return []


def get_account_info(
    city_name: str,
    account_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    根据城市查询所有该城市社保账户的信息
    根据社保账户查询社保账户基本信息，社保政策补充信息（工伤比例，公积金公司和个人比例），服务人数等信息

    Args:
        city_name: 城市名称（用于筛选政策城市）
        account_name: 账户名称（可选）
    Returns:
        账户信息字典或 None
    """
    try:
        base_query = """
        SELECT 
            acc.id AS account_id, 
            acc.account_name, 
            acc.apply_id AS customer_id, 
            acc.agent_id, 
            acc.city_id, 
            cc.name AS customer_name, 
            agent.name AS agent_name 
        FROM soi_account AS acc 
        LEFT JOIN hro_customer AS cc ON acc.apply_id = cc.id AND cc.status = '1' 
        LEFT JOIN hro_agent AS agent ON acc.agent_id = agent.id AND agent.status = '1' 
        WHERE 1=1
        """
        params = []

        if account_name:
            base_query += " AND acc.account_name LIKE CONCAT('%%', %s, '%%')"
            params.append(account_name)

        query = f"""
        WITH base AS ( 
            {base_query}
        ), 
        t_work_injury AS ( 
            SELECT account_id, policy_id, company_approval_ratio AS work_injury_company_ratio 
            FROM soi_acc_insurance WHERE item_code = '1050' 
        ), 
        t_housing_fund AS ( 
            SELECT account_id, policy_id, company_ratios AS housing_fund_company_ratio, employee_ratios AS housing_fund_employee_ratio 
            FROM soi_acc_insurance WHERE item_code = '2010' 
        ), 
        t_city_policy AS ( 
            SELECT id, name, city_ids FROM soi_city_policy WHERE status = '1' 
        ), 
        t_insured_count AS ( 
            SELECT account_id, COUNT(*) AS insured_count 
            FROM soi_insured_info 
            GROUP BY account_id 
        ) 
        SELECT 
            b.account_id, b.account_name, b.customer_name, b.agent_name, ic.insured_count, 
            tw.policy_id AS work_injury_policy_id, tw.work_injury_company_ratio, 
            th.policy_id AS housing_fund_policy_id, th.housing_fund_company_ratio, th.housing_fund_employee_ratio, 
            cp.name AS city_policy_name 
        FROM base AS b 
        LEFT JOIN t_work_injury tw ON b.account_id = tw.account_id 
        LEFT JOIN t_housing_fund th ON b.account_id = th.account_id 
        LEFT JOIN t_city_policy cp ON CAST(b.city_id AS CHAR) = cp.city_ids COLLATE utf8mb4_general_ci
        LEFT JOIN t_insured_count ic ON b.account_id = ic.account_id 
        WHERE 1=1 
        """

        if city_name:
            query += " AND cp.name LIKE CONCAT('%%', %s, '%%')"
            params.append(city_name)

        query += " ORDER BY b.account_id DESC LIMIT 1"

        results = db_manager.execute_query(
            query, server_id="YIFEI", params=tuple(params), max_rows=1
        )
        
        if results:
            return results[0]
        return None

    except Exception as e:
        logger.error(f"查询账户信息失败：{e}")
        return None


__all__ = [
    "get_account_bill_data",
    "get_policy_by_city",
    "get_employee_info",
    "get_account_info",
]
