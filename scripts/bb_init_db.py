"""建表 + 造数脚本：宽带退单稽核场景"""
import pymysql, random, datetime, uuid
from decimal import Decimal

DB = dict(host='127.0.0.1', port=3307, user='root', password='123456',
          db='bb_churn_audit', charset='utf8mb4')

def conn():
    c = pymysql.connect(**DB)
    c.cursor().execute("SET sql_mode=''")
    c.commit()
    return c

def create_tables(cur):
    sqls = [
    """CREATE TABLE IF NOT EXISTS bb_product (
      product_id VARCHAR(20) PRIMARY KEY,
      product_type VARCHAR(20) NOT NULL,
      product_name VARCHAR(100) NOT NULL,
      speed_mbps INT NOT NULL,
      product_status VARCHAR(10) DEFAULT '在售',
      applicable_address_type VARCHAR(50)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS bb_channel (
      channel_id VARCHAR(20) PRIMARY KEY,
      channel_name VARCHAR(50) NOT NULL,
      channel_type VARCHAR(20) NOT NULL,
      hist_churn_rate DECIMAL(5,4),
      is_self_operated TINYINT(1) DEFAULT 0
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS bb_customer (
      customer_id VARCHAR(20) PRIMARY KEY,
      customer_name VARCHAR(50) NOT NULL,
      contact_phone VARCHAR(20) NOT NULL,
      customer_level VARCHAR(10) DEFAULT '普通',
      network_age INT,
      hist_complaint_count INT DEFAULT 0,
      hist_churn_count INT DEFAULT 0,
      is_blacklist TINYINT(1) DEFAULT 0,
      id_verified TINYINT(1) DEFAULT 1,
      credit_score INT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS bb_engineer (
      engineer_id VARCHAR(20) PRIMARY KEY,
      engineer_name VARCHAR(30) NOT NULL,
      tech_level VARCHAR(10) NOT NULL,
      employment_type VARCHAR(10) NOT NULL,
      team_name VARCHAR(50),
      skill_tags VARCHAR(200),
      churn_rate_90d DECIMAL(5,4),
      on_time_rate_90d DECIMAL(5,4),
      optical_qualify_rate DECIMAL(5,4),
      monthly_order_count INT DEFAULT 0,
      complaint_count_90d INT DEFAULT 0
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS bb_address (
      address_id VARCHAR(20) PRIMARY KEY,
      standard_address_name VARCHAR(300) NOT NULL,
      community_name VARCHAR(100),
      address_level VARCHAR(10) DEFAULT '房间',
      is_unconditional_accept TINYINT(1) DEFAULT 1,
      open_time_limit_days INT DEFAULT 0,
      resource_status VARCHAR(10) DEFAULT '充足',
      hist_churn_rate DECIMAL(5,4),
      is_monopoly TINYINT(1) DEFAULT 0,
      has_build_plan TINYINT(1) DEFAULT 1,
      property_cooperation VARCHAR(10) DEFAULT '良好'
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS bb_install_order (
      order_no VARCHAR(30) PRIMARY KEY,
      cust_id VARCHAR(20) NOT NULL,
      engineer_id VARCHAR(20),
      accept_time DATETIME NOT NULL,
      order_status VARCHAR(20) NOT NULL,
      biz_type VARCHAR(10) NOT NULL,
      product_type VARCHAR(20) NOT NULL,
      product_id VARCHAR(20),
      product_name VARCHAR(100),
      channel_id VARCHAR(20),
      install_address_id VARCHAR(20),
      install_address VARCHAR(300),
      finish_time DATETIME,
      speed_test_result DECIMAL(6,1),
      optical_power_db DECIMAL(5,1),
      satisfaction_score INT,
      KEY idx_cust (cust_id),
      KEY idx_engineer (engineer_id),
      KEY idx_accept_time (accept_time)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS bb_install_churn (
      churn_id VARCHAR(30) PRIMARY KEY,
      related_order_no VARCHAR(30) NOT NULL,
      churn_time DATETIME NOT NULL,
      churn_phase VARCHAR(20) NOT NULL,
      churn_reason_text VARCHAR(500),
      churn_category_l1 VARCHAR(20),
      churn_category_l2 VARCHAR(50),
      audit_status VARCHAR(20) DEFAULT '待稽核',
      audit_start_time DATETIME,
      escalate_time DATETIME,
      escalate_reason VARCHAR(100),
      root_cause_code VARCHAR(10),
      root_cause_level_one VARCHAR(20),
      root_cause_level_two VARCHAR(50),
      root_cause_confidence DECIMAL(5,4),
      secondary_cause_label VARCHAR(50),
      evidence_chain_summary TEXT,
      reasoning_path_snapshot TEXT,
      triggered_action_type VARCHAR(30),
      manual_review_status VARCHAR(20),
      manual_override_label VARCHAR(50),
      archive_time DATETIME,
      callback_verified TINYINT(1) DEFAULT 0,
      KEY idx_order (related_order_no),
      KEY idx_status (audit_status),
      KEY idx_churn_time (churn_time)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS bb_dispatch_record (
      dispatch_id VARCHAR(30) PRIMARY KEY,
      related_order_no VARCHAR(30) NOT NULL,
      related_engineer_id VARCHAR(20),
      appointment_time DATETIME,
      actual_arrival_time DATETIME,
      finish_time DATETIME,
      wait_duration_minutes INT,
      late_duration_minutes INT,
      dispatch_status VARCHAR(20) NOT NULL,
      exception_type VARCHAR(50),
      reschedule_count INT DEFAULT 0,
      KEY idx_order (related_order_no)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS bb_pending_pool (
      record_id VARCHAR(30) PRIMARY KEY,
      related_address_id VARCHAR(20),
      order_no VARCHAR(30),
      entry_time DATETIME,
      pending_reason VARCHAR(20) NOT NULL,
      current_backlog_count INT DEFAULT 0,
      backlog_duration_days INT DEFAULT 0,
      hist_backlog_frequency INT DEFAULT 0,
      estimated_resolve_date DATE,
      KEY idx_address (related_address_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS bb_competitor_call (
      call_id VARCHAR(30) PRIMARY KEY,
      customer_id VARCHAR(20),
      customer_phone VARCHAR(20),
      called_phone VARCHAR(20),
      call_time DATETIME,
      competitor_type VARCHAR(10) NOT NULL,
      duration_seconds INT,
      call_count_7d INT DEFAULT 1,
      KEY idx_customer (customer_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS bb_engineer_call (
      call_id VARCHAR(30) PRIMARY KEY,
      related_order_no VARCHAR(30),
      call_start_time DATETIME,
      call_end_time DATETIME,
      connect_status VARCHAR(10) NOT NULL,
      is_effective_cop TINYINT(1) DEFAULT 0,
      duration_seconds INT DEFAULT 0,
      asr_text TEXT,
      sentiment VARCHAR(10) DEFAULT '正常',
      KEY idx_order (related_order_no)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS bb_callback_call (
      call_id VARCHAR(30) PRIMARY KEY,
      related_order_no VARCHAR(30),
      trigger_hypothesis VARCHAR(50),
      call_start_time DATETIME,
      call_end_time DATETIME,
      connect_status VARCHAR(10) NOT NULL,
      duration_seconds INT DEFAULT 0,
      asr_text TEXT,
      callback_result VARCHAR(20),
      verified_cause VARCHAR(50),
      KEY idx_order (related_order_no)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS bb_marketing_call (
      call_id VARCHAR(30) PRIMARY KEY,
      related_order_no VARCHAR(30),
      related_customer_id VARCHAR(20),
      call_start_time DATETIME,
      call_end_time DATETIME,
      connect_status VARCHAR(10) NOT NULL,
      asr_text TEXT,
      marketing_result VARCHAR(20),
      KEY idx_order (related_order_no)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS bb_user_demand (
      demand_id VARCHAR(30) PRIMARY KEY,
      related_customer_id VARCHAR(20),
      related_order_no VARCHAR(30),
      demand_type VARCHAR(20) NOT NULL,
      demand_status VARCHAR(10) DEFAULT '活跃',
      demand_intensity VARCHAR(5) DEFAULT '中',
      discovery_source VARCHAR(50),
      last_contact_time DATETIME,
      KEY idx_customer (related_customer_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS bb_evidence (
      evidence_id VARCHAR(30) PRIMARY KEY,
      churn_id VARCHAR(30) NOT NULL,
      evidence_code VARCHAR(10) NOT NULL,
      evidence_type VARCHAR(10) NOT NULL,
      source_type VARCHAR(30),
      source_id VARCHAR(30),
      content VARCHAR(200),
      raw_text TEXT,
      hit TINYINT(1) DEFAULT 0,
      confidence DECIMAL(5,4),
      extracted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      KEY idx_churn (churn_id),
      KEY idx_code (evidence_code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS bb_audit_trail (
      trail_id VARCHAR(30) PRIMARY KEY,
      churn_id VARCHAR(30) NOT NULL,
      action_type VARCHAR(50),
      operator_id VARCHAR(20),
      operator_role VARCHAR(30),
      action_time DATETIME DEFAULT CURRENT_TIMESTAMP,
      before_status VARCHAR(30),
      after_status VARCHAR(30),
      remark TEXT,
      KEY idx_churn (churn_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    ]
    for sql in sqls:
        cur.execute(f"DROP TABLE IF EXISTS {sql.split('EXISTS ')[1].split(' ')[0]}")
        cur.execute(sql)
    print(f"Created {len(sqls)} tables")

if __name__ == '__main__':
    c = conn()
    cur = c.cursor()
    create_tables(cur)
    c.commit()
    c.close()
    print("Tables created successfully")
