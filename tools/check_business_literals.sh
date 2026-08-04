#!/usr/bin/env bash
# 检查平台代码里是否混入了具体业务字面量。
# 平台层（backend/app、frontend/src）应保持业务中立，业务数据必须来自 DB / 用户前端录入。
# 命中即视为分层泄漏，CI 应 fail。

set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# 具体业务字面量黑名单：MNP / 宽带 / 联通电信 / 特定业务对象名 / 特定业务表名 / 特定业务口径术语
PATTERN='MobileSubscriber|PortabilityQuery|UserContract|UserArrears|ComplaintWorkOrder|MonthlyBilling|VoiceCallRecord|ConvergencePackage|RetentionRecord|InstallChurn|InstallOrder|DispatchRecord|EngineerCall|BroadbandChurnOrder|VoiceAuditRecord|ConstructionRecord|AuditRule|MnpQueryRecord|AlertResult|EnterpriseCustomer|NetworkDevice|FaultOrder|RootCauseResult|CbssSubscriber|bb_install|bb_audit|bb_customer|bb_engineer|bb_dispatch|bb_callback|bb_competitor|bb_logic_hit|bb_root_cause|bb_evidence|dwd_d_cus|dwa_v_d_cus|bb_audit_db|TELECOM_SCENARIOS|TELECOM_KNOWLEDGE|TELECOM_DOMAIN_KNOWLEDGE|_MNP_ENTITIES|_ENTITY_ALIAS|_SCENE_LAYER_MAP|_BB_CONN_NAME|_case_users_cache|broadband_audit|list_mnp_case_users|execute_mnp_flow|携号转网|宽带退单|专属坐席|自动外呼|短信触达|合约到期|竞品活动|政企根因|联通|电信业务|折损因子|退单根因|FTTR续约'

# 白名单：本脚本自身 / 说明文档 / 一次性迁移脚本
EXCLUDE='tools/check_business_literals\.sh|/__pycache__/|\.pyc$|/dist/|/node_modules/|\.md$|/uploads/|/workspace/'

SCAN_DIRS=(
  "$ROOT/backend/app"
  "$ROOT/frontend/src"
)

hits=0
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

for d in "${SCAN_DIRS[@]}"; do
  [ -d "$d" ] || continue
  grep -REn --binary-files=without-match "$PATTERN" "$d" 2>/dev/null \
    | grep -Ev "$EXCLUDE" >> "$tmp" || true
done

count=$(wc -l < "$tmp" | tr -d ' ')
if [ "$count" -gt 0 ]; then
  echo "❌ 平台代码里发现业务字面量（分层泄漏），共 $count 处："
  echo "-----------------------------------------------------------"
  cat "$tmp"
  echo "-----------------------------------------------------------"
  echo "规则：backend/app 和 frontend/src 不允许出现具体业务名/表名/业务术语。"
  echo "业务数据必须由用户在前端界面录入，存 DB。"
  exit 1
fi

echo "✅ 平台代码业务中立检查通过"
