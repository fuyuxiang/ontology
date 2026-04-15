"""
测试场景5v2.json中的实体、属性、关系能否通过数据管道获取真实数据
数据来源: 系统数据管道API (非直连数据库)
"""
import json
import sys
import requests

API_BASE = "http://127.0.0.1:8001/api/v1"

# 数据源ID映射 (从系统数据管道获取)
DS_MAP = {
    "ds_cbss_user": "fe36ce97-19d1-48e4-8118-d8921b3cba0d",
    "ds_mnp_query": "ab5309ff-ea3f-48af-a804-e56f16a5282a",
    "ds_cbss_activity": "23857f9d-b7bb-423a-879c-4ca99c22d9aa",
    "ds_billing": "142d2b37-d8a4-44d2-85c9-333e8c64bcd9",
    "ds_arrears": "ff848ce3-4065-4e06-acc1-e5ab0225d831",
    "ds_voice_detail": "c04aa14f-7a72-4246-9cd8-4f8621feb81b",
    "ds_service_order": "adce4115-8dda-4439-b62e-663e3c3afdd7",
    "ds_retention": "92206800-0f13-438d-a787-23da44ff3477",
    "ds_convergence": "dcd24cc8-4f65-4c84-a5fc-7e1ac41cd5e9",
}


def test_entity_data(schema_path: str):
    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)

    results = []
    total = 0
    passed = 0
    failed = 0

    print(f"\n{'='*70}")
    print("场景5v2.json 实体-属性-数据管道 验证测试")
    print(f"{'='*70}\n")

    for obj in schema.get("object_types", []):
        ds_ref = obj.get("datasource_ref")
        if not ds_ref or ds_ref not in DS_MAP:
            print(f"[SKIP] {obj['name']} - 无数据源映射(tier{obj['tier']})")
            continue

        total += 1
        ds_id = DS_MAP[ds_ref]
        entity_name = obj["name"]
        display_name = obj.get("display_name", "")
        props = [p["name"] for p in obj.get("properties", [])]

        print(f"[TEST] {entity_name} ({display_name})")
        print(f"  数据源: {ds_ref} -> {ds_id}")
        print(f"  期望属性: {props}")

        # 通过数据管道API获取数据
        try:
            # 检查数据源是否启用
            ds_resp = requests.get(f"{API_BASE}/datasources/{ds_id}", timeout=10)
            if ds_resp.status_code != 200:
                print(f"  [FAIL] 数据源不存在: {ds_resp.status_code}")
                failed += 1
                results.append({"entity": entity_name, "status": "FAIL", "reason": "数据源不存在"})
                continue

            ds_info = ds_resp.json()
            if not ds_info.get("enabled"):
                print(f"  [FAIL] 数据源未启用(管道关闭)")
                failed += 1
                results.append({"entity": entity_name, "status": "FAIL", "reason": "数据源管道未启用"})
                continue

            # 通过管道预览数据
            preview_resp = requests.get(f"{API_BASE}/datasources/{ds_id}/preview", timeout=15)
            if preview_resp.status_code != 200:
                print(f"  [FAIL] 数据预览失败: {preview_resp.status_code} {preview_resp.text[:100]}")
                failed += 1
                results.append({"entity": entity_name, "status": "FAIL", "reason": f"预览失败: {preview_resp.status_code}"})
                continue

            data = preview_resp.json()
            db_columns = data.get("columns", [])
            rows = data.get("rows", [])

            # 验证属性字段是否都在数据库列中
            missing = [p for p in props if p not in db_columns]
            if missing:
                print(f"  [FAIL] 缺失字段: {missing}")
                print(f"  数据库列: {db_columns}")
                failed += 1
                results.append({"entity": entity_name, "status": "FAIL", "reason": f"缺失字段: {missing}"})
            elif len(rows) == 0:
                print(f"  [FAIL] 无数据记录")
                failed += 1
                results.append({"entity": entity_name, "status": "FAIL", "reason": "无数据记录"})
            else:
                print(f"  [PASS] 字段全部匹配, 数据行数: {len(rows)}+")
                # 打印第一行数据作为样例
                if rows:
                    sample = dict(zip(db_columns, rows[0]))
                    sample_str = ", ".join(f"{k}={v}" for k, v in sample.items() if k in props[:5])
                    print(f"  样例: {sample_str}")
                passed += 1
                results.append({"entity": entity_name, "status": "PASS", "rows": len(rows)})

        except requests.exceptions.ConnectionError:
            print(f"  [FAIL] 无法连接后端API")
            failed += 1
            results.append({"entity": entity_name, "status": "FAIL", "reason": "API连接失败"})
        except Exception as e:
            print(f"  [FAIL] 异常: {e}")
            failed += 1
            results.append({"entity": entity_name, "status": "FAIL", "reason": str(e)})

        print()

    # ── 验证关系 ──
    print(f"\n{'='*70}")
    print("关系验证 (检查关联实体是否都已导入系统)")
    print(f"{'='*70}\n")

    entities_resp = requests.get(f"{API_BASE}/entities", timeout=10)
    system_entities = {e["name"]: e["id"] for e in entities_resp.json()} if entities_resp.status_code == 200 else {}

    for link in schema.get("link_types", []):
        src = link["source_type"]
        tgt = link["target_type"]
        if src in system_entities and tgt in system_entities:
            print(f"  [PASS] {src} --[{link['name']}]--> {tgt}")
        else:
            missing_e = []
            if src not in system_entities:
                missing_e.append(src)
            if tgt not in system_entities:
                missing_e.append(tgt)
            print(f"  [WARN] {src} --[{link['name']}]--> {tgt} (实体未找到: {missing_e})")

    # ── 汇总 ──
    print(f"\n{'='*70}")
    print(f"测试结果汇总: 总计 {total} 个实体, 通过 {passed}, 失败 {failed}")
    print(f"{'='*70}")

    return failed == 0


if __name__ == "__main__":
    schema_path = sys.argv[1] if len(sys.argv) > 1 else "../场景5v2.json"
    success = test_entity_data(schema_path)
    sys.exit(0 if success else 1)
