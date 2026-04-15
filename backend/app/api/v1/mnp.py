"""
携号转网数据查询 API — 从 MySQL 数据源查询真实业务数据
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.datasource import DataSource
from app.services.datasource_utils import execute_readonly_sql, get_connection

router = APIRouter(prefix="/mnp", tags=["mnp"])

MNP_DS_NAME = "携号转网数据源"


def _get_mnp_ds(db: Session) -> DataSource:
    ds = db.query(DataSource).filter(DataSource.type == "mysql").first()
    if not ds:
        raise HTTPException(404, "未找到携号转网 MySQL 数据源")
    return ds


@router.get("/stats")
def get_mnp_stats(db: Session = Depends(get_db)):
    """携转预警统计概览"""
    ds = _get_mnp_ds(db)

    # 总用户数
    r = execute_readonly_sql(ds, "SELECT COUNT(*) FROM dwa_v_d_cus_cb_user_info")
    total_users = r["rows"][0][0] if r.get("rows") else 0

    # 携转查询用户数
    r = execute_readonly_sql(ds, "SELECT COUNT(DISTINCT device_number) FROM dwd_d_cus_np_turn_query_user")
    query_users = r["rows"][0][0] if r.get("rows") else 0

    # 维挽记录数
    r = execute_readonly_sql(ds, "SELECT COUNT(*) FROM dwd_d_cus_qk_turn_maintain")
    maintain_total = r["rows"][0][0] if r.get("rows") else 0

    # 维挽成功数
    r = execute_readonly_sql(ds, "SELECT COUNT(*) FROM dwd_d_cus_qk_turn_maintain WHERE is_success_maintain = '1'")
    maintain_success = r["rows"][0][0] if r.get("rows") else 0

    # 客服工单数
    r = execute_readonly_sql(ds, "SELECT COUNT(*) FROM dwd_d_evt_kf_order_main")
    complaint_total = r["rows"][0][0] if r.get("rows") else 0

    # 欠费用户数
    r = execute_readonly_sql(ds, "SELECT COUNT(*) FROM dwd_m_mrt_al_chl_owe WHERE arrear_fee > 0")
    owe_users = r["rows"][0][0] if r.get("rows") else 0

    return {
        "total_users": total_users,
        "query_users": query_users,
        "maintain_total": maintain_total,
        "maintain_success": maintain_success,
        "maintain_rate": round(maintain_success / maintain_total * 100, 1) if maintain_total else 0,
        "complaint_total": complaint_total,
        "owe_users": owe_users,
    }


@router.get("/risk-users")
def get_risk_users(db: Session = Depends(get_db)):
    """风险用户列表 — 关联用户信息+携转查询+费用+维挽"""
    ds = _get_mnp_ds(db)
    sql = """
        SELECT
            u.user_id,
            u.device_number,
            u.area_id,
            u.user_status,
            u.innet_months,
            u.is_5g,
            u.pay_mode,
            COALESCE(c.total_fee, 0) as arpu,
            COALESCE(owe.arrear_fee, 0) as arrear_fee,
            q.query_time,
            q.query_channel,
            q.limit_remark,
            q.out_tag
        FROM dwa_v_d_cus_cb_user_info u
        LEFT JOIN dwa_v_m_cus_cb_sing_charge c ON u.user_id = c.user_id
        LEFT JOIN dwd_m_mrt_al_chl_owe owe ON u.user_id = owe.subs_id
        INNER JOIN dwd_d_cus_np_turn_query_user q ON u.user_id = q.user_id
        ORDER BY q.query_time DESC
        LIMIT 100
    """
    return execute_readonly_sql(ds, sql, limit=100)


@router.get("/risk-users/{user_id}")
def get_risk_user_detail(user_id: str, db: Session = Depends(get_db)):
    """单个用户的完整画像"""
    ds = _get_mnp_ds(db)

    # 基本信息
    r = execute_readonly_sql(ds, f"SELECT * FROM dwa_v_d_cus_cb_user_info WHERE user_id = '{user_id}' LIMIT 1")
    user_info = dict(zip(r["columns"], r["rows"][0])) if r.get("rows") else {}

    # 费用
    r = execute_readonly_sql(ds, f"SELECT * FROM dwa_v_m_cus_cb_sing_charge WHERE user_id = '{user_id}' LIMIT 1")
    charge = dict(zip(r["columns"], r["rows"][0])) if r.get("rows") else {}

    # 合约活动
    r = execute_readonly_sql(ds, f"SELECT * FROM dwa_v_d_cus_cb_act_info WHERE user_id = '{user_id}'")
    contracts = [dict(zip(r["columns"], row)) for row in r.get("rows", [])]

    # 携转查询记录
    r = execute_readonly_sql(ds, f"SELECT * FROM dwd_d_cus_np_turn_query_user WHERE user_id = '{user_id}'")
    queries = [dict(zip(r["columns"], row)) for row in r.get("rows", [])]

    # 维挽记录
    device = user_info.get("device_number", "")
    r = execute_readonly_sql(ds, f"SELECT * FROM dwd_d_cus_qk_turn_maintain WHERE device_number = '{device}'")
    maintains = [dict(zip(r["columns"], row)) for row in r.get("rows", [])]

    # 客服工单
    r = execute_readonly_sql(ds, f"SELECT * FROM dwd_d_evt_kf_order_main WHERE device_number = '{device}'")
    complaints = [dict(zip(r["columns"], row)) for row in r.get("rows", [])]

    # 通话记录统计
    r = execute_readonly_sql(ds, f"""
        SELECT COUNT(*) as call_count,
               COALESCE(SUM(call_duration), 0) as total_duration,
               SUM(CASE WHEN oppose_dealer_type != 1 THEN 1 ELSE 0 END) as cross_carrier_calls
        FROM dwd_d_use_cb_f_voice WHERE user_id = '{user_id}'
    """)
    voice = dict(zip(r["columns"], r["rows"][0])) if r.get("rows") else {}

    # 欠费
    r = execute_readonly_sql(ds, f"SELECT * FROM dwd_m_mrt_al_chl_owe WHERE subs_id = '{user_id}' LIMIT 1")
    owe = dict(zip(r["columns"], r["rows"][0])) if r.get("rows") else {}

    return {
        "user_info": user_info,
        "charge": charge,
        "contracts": contracts,
        "queries": queries,
        "maintains": maintains,
        "complaints": complaints,
        "voice_stats": voice,
        "owe": owe,
    }


@router.get("/maintain-stats")
def get_maintain_stats(db: Session = Depends(get_db)):
    """维挽统计 — 按转网原因和维挽结果分组"""
    ds = _get_mnp_ds(db)

    # 按转网原因分组
    r = execute_readonly_sql(ds, """
        SELECT turn_reason, COUNT(*) as cnt,
               SUM(CASE WHEN is_success_maintain = '1' THEN 1 ELSE 0 END) as success_cnt
        FROM dwd_d_cus_qk_turn_maintain
        GROUP BY turn_reason
        ORDER BY cnt DESC
    """)
    by_reason = [dict(zip(r["columns"], row)) for row in r.get("rows", [])]

    # 按产品分组
    r = execute_readonly_sql(ds, """
        SELECT product_name, COUNT(*) as cnt,
               SUM(CASE WHEN is_success_maintain = '1' THEN 1 ELSE 0 END) as success_cnt
        FROM dwd_d_cus_qk_turn_maintain
        GROUP BY product_name
        ORDER BY cnt DESC
    """)
    by_product = [dict(zip(r["columns"], row)) for row in r.get("rows", [])]

    return {"by_reason": by_reason, "by_product": by_product}
