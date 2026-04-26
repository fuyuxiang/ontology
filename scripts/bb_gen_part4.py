def gen_orders_and_churns(cur, cust_ids, addr_ids, eng_ids, n_orders=1200):
    orders, churns, dispatches = [], [], []
    eng_calls, cb_calls, mkt_calls = [], [], []
    comp_calls, pending_rows, demands = [], [], []
    evidences, trails = [], []
    cause_weights = [c[3] for c in ROOT_CAUSES]
    counters = {k:1 for k in ['order','churn','disp','ec','cb','mk','cc','pp','ud','ev','tr']}

    def nid(prefix):
        v = counters[prefix]; counters[prefix] += 1; return v

    for _ in range(n_orders):
        oid = f"WO2025{nid('order'):05d}"
        cust_id = rng.choice(cust_ids)
        eng_id  = rng.choice(eng_ids)
        addr_id = rng.choice(addr_ids)
        prod    = rng.choice(PRODUCTS)
        chan    = rng.choice(CHANNELS)
        accept_t = rdate('2024-10-01','2025-03-15')
        biz_type = weighted_choice(['新装','移装','改装','迁移'],[70,15,10,5])
        is_churn = rng.random() < 0.55
        status = '已退单' if is_churn else weighted_choice(['已完工','施工中','已派单'],[80,12,8])
        finish_t = speed = optical = sat = None
        if status == '已完工':
            finish_t = accept_t + datetime.timedelta(hours=rng.randint(4,72))
            speed = round(prod[3] * rng.uniform(0.75, 1.05), 1)
            optical = round(rng.uniform(-28, -15), 1)
            sat = rng.choices([1,2,3,4,5],[3,5,12,40,40])[0]
        addr_str = gen_address(rng.choice(COMMUNITIES)[0])
        orders.append((oid, cust_id, eng_id, accept_t, status, biz_type,
                       prod[1], prod[0], prod[2], chan[0], addr_id, addr_str,
                       finish_t, speed, optical, sat))
        if not is_churn:
            continue

        cause = weighted_choice(ROOT_CAUSES, cause_weights)
        c_code, c_l1, c_l2, _, texts, phases = cause
        churn_phase = rng.choice(phases)
        churn_t = accept_t + datetime.timedelta(hours=rng.randint(2, 96))
        reason_text = rng.choice(texts)

        if rng.random() < 0.60:
            conf = round(rng.uniform(0.85, 0.98), 4)
            audit_status = '已归档'
            archive_t = churn_t + datetime.timedelta(hours=rng.randint(1,6))
            manual_status = None
        elif rng.random() < 0.65:
            conf = round(rng.uniform(0.50, 0.84), 4)
            audit_status = '人工审核中'
            archive_t = None
            manual_status = rng.choice(['待审核','审核中'])
        else:
            conf = round(rng.uniform(0.30, 0.55), 4)
            audit_status = '待补全回访'
            archive_t = None
            manual_status = None

        sec_label = c_l2 if rng.random() > 0.3 else None
        triggered = {'施工原因':'培训整改','用户原因':'挽回外呼','资源原因':'资源修复','业务原因':'流程优化'}.get(c_l1,'')
        churn_id = f"TD2025{nid('churn'):05d}"
        churns.append((churn_id, oid, churn_t, churn_phase, reason_text,
                       c_l1, c_l2, audit_status,
                       churn_t + datetime.timedelta(minutes=5) if audit_status != '待稽核' else None,
                       None, None, c_code, c_l1, c_l2, conf, sec_label,
                       f"证据链：{c_l2}，置信度{conf}", f"推理路径：{c_l1}到{c_l2}",
                       triggered, manual_status, None, archive_t,
                       1 if c_l1 == '用户原因' and conf >= 0.85 else 0))

        # 派单
        appt_t = accept_t + datetime.timedelta(hours=rng.randint(4, 48))
        is_late = c_code == '施3' or rng.random() < 0.15
        late_min = rng.randint(30, 180) if is_late else rng.randint(-10, 20)
        actual_t = appt_t + datetime.timedelta(minutes=max(0, late_min))
        reschedule = rng.choices([0,1,2,3],[60,25,12,3])[0]
        if c_code == '用2': reschedule = rng.randint(1,3)
        exc_type = '工程师迟到' if late_min > 30 else ('爽约' if reschedule >= 2 else None)
        dispatches.append((f"DP{nid('disp'):06d}", oid, eng_id, appt_t, actual_t,
                           churn_t, rng.randint(10,120), max(0,late_min),
                           '已退单', exc_type, reschedule))

        # 工程师外呼
        for _ in range(rng.choices([1,2,3],[50,35,15])[0]):
            ct = accept_t + datetime.timedelta(hours=rng.randint(1,48))
            connected = rng.random() < (0.5 if c_code == '用2' else 0.85)
            dur = rng.randint(30,300) if connected else 0
            sentiment = '正常'
            asr = ''
            if c_code == '施3' and connected:
                sentiment = rng.choice(['焦虑','愤怒','正常'])
                asr = rng.choice(['工程师说无法完成施工','工程师反映物业不配合','客户情绪激动要求取消'])
            elif c_code in ('用1','用3') and connected:
                asr = rng.choice(['用户说暂时不需要了','用户表示已选择其他运营商','用户要求取消工单'])
            eng_calls.append((f"EC{nid('ec'):06d}", oid, ct,
                              ct + datetime.timedelta(seconds=dur),
                              '接通' if connected else rng.choice(['未接','占线']),
                              1 if connected and dur > 60 else 0, dur, asr, sentiment))

        # 回访外呼（E22-E26命中来源）
        needs_cb = c_l1 in ('用户原因','资源原因','业务原因') or conf < 0.85
        if needs_cb:
            cb_t = churn_t + datetime.timedelta(hours=rng.randint(2,24))
            connected = rng.random() < 0.72
            dur = rng.randint(60,360) if connected else 0
            if connected:
                cb_result = '已核实'
                verified_cause = c_l2
                asr_cb = f'回访确认：{reason_text}'
            else:
                cb_result = '无法联系'
                verified_cause = None
                asr_cb = ''
            cb_calls.append((f"CB{nid('cb'):06d}", oid, c_l1,
                             cb_t, cb_t + datetime.timedelta(seconds=dur),
                             '接通' if connected else rng.choice(['未接','空号']),
                             dur, asr_cb, cb_result, verified_cause))

        # 竞品通话
        if c_code == '用3' or rng.random() < 0.08:
            for _ in range(rng.randint(1,4)):
                comp_t = accept_t - datetime.timedelta(days=rng.randint(0,7))
                comp_calls.append((f"CC{nid('cc'):06d}", cust_id, gen_phone(),
                                   gen_phone(), comp_t,
                                   rng.choice(['移动','联通','广电']),
                                   rng.randint(30,300), rng.randint(1,5)))

        # 营销挽回
        if c_l1 == '用户原因' and rng.random() < 0.6:
            mkt_t = churn_t + datetime.timedelta(hours=rng.randint(4,48))
            connected = rng.random() < 0.65
            dur = rng.randint(60,240) if connected else 0
            result = weighted_choice(['挽回成功','挽回失败','用户拒绝'],[20,50,30]) if connected else '无法联系'
            mkt_calls.append((f"MK{nid('mk'):06d}", oid, cust_id,
                              mkt_t, mkt_t + datetime.timedelta(seconds=dur),
                              '接通' if connected else '未接',
                              f'营销挽回：{result}', result))

        # 待装库
        if c_l1 == '资源原因':
            entry_t = accept_t - datetime.timedelta(days=rng.randint(0,30))
            resolve_date = datetime.date.today() + datetime.timedelta(days=rng.randint(30,180))
            reason_map = {'资1':'建设中','资2':'待规划','资3':'无资源','资4':'待规划','资5':'资源冲突','资6':'无资源'}
            pending_rows.append((f"PP{nid('pp'):06d}", addr_id, oid, entry_t,
                                 reason_map.get(c_code,'无资源'),
                                 rng.randint(5,80), rng.randint(10,120), rng.randint(0,5), resolve_date))

        # 用户需求
        if c_l1 == '用户原因' and rng.random() < 0.5:
            dem_type = {'用3':'竞品对比','用5':'价格敏感','用6':'速率需求'}.get(c_code,'其他')
            demands.append((f"UD{nid('ud'):06d}", cust_id, oid, dem_type,
                            '已流失', rng.choice(['低','中','高']), '工单系统', churn_t))

        # 证据（核心：适用证据高命中，噪声证据低命中）
        applicable = [e for e in EVIDENCE_DEF if c_code in e[3]]
        not_applicable = [e for e in EVIDENCE_DEF if c_code not in e[3]]
        for ev in applicable:
            hit = 1 if rng.random() < 0.78 else 0
            ev_conf = round(rng.uniform(0.55, 0.92) if hit else rng.uniform(0.05, 0.35), 4)
            content = rng.choice(ev[4]) if ev[4] else ev[1]
            src = 'engineer_call' if ev[1] == 'nlp' else 'dispatch_record'
            evidences.append((f"EV{nid('ev'):07d}", churn_id, ev[0], ev[1],
                              src, oid, content, content, hit, ev_conf,
                              churn_t + datetime.timedelta(minutes=rng.randint(5,60))))
        for ev in rng.sample(not_applicable, min(5, len(not_applicable))):
            hit = 1 if rng.random() < 0.12 else 0
            ev_conf = round(rng.uniform(0.05, 0.30) if not hit else rng.uniform(0.30, 0.55), 4)
            content = rng.choice(ev[4]) if ev[4] else ev[1]
            evidences.append((f"EV{nid('ev'):07d}", churn_id, ev[0], ev[1],
                              'system', oid, content, content, hit, ev_conf,
                              churn_t + datetime.timedelta(minutes=rng.randint(5,60))))

        # 审计轨迹
        trails.append((f"TR{nid('tr'):07d}", churn_id, '接受稽核', 'SYS001', '系统',
                       churn_t + datetime.timedelta(minutes=5), '待稽核', '推理中', '系统自动触发'))
        if audit_status == '已归档':
            trails.append((f"TR{nid('tr'):07d}", churn_id, '自动归档', 'SYS001', '系统',
                           archive_t, '推理中', '已归档', f'置信度{conf}>=0.85自动归档'))
        elif audit_status == '人工审核中':
            trails.append((f"TR{nid('tr'):07d}", churn_id, '转人工审核', 'SYS001', '系统',
                           churn_t + datetime.timedelta(hours=1), '推理中', '人工审核中',
                           f'置信度{conf}<0.85转人工'))

    def batch_insert(sql, rows, batch=500):
        for i in range(0, len(rows), batch):
            cur.executemany(sql, rows[i:i+batch])

    batch_insert("INSERT IGNORE INTO bb_install_order VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", orders)
    print(f"Orders: {len(orders)}")
    batch_insert("INSERT IGNORE INTO bb_install_churn VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", churns)
    print(f"Churns: {len(churns)}")
    batch_insert("INSERT IGNORE INTO bb_dispatch_record VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", dispatches)
    print(f"Dispatches: {len(dispatches)}")
    batch_insert("INSERT IGNORE INTO bb_engineer_call VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)", eng_calls)
    print(f"Engineer calls: {len(eng_calls)}")
    batch_insert("INSERT IGNORE INTO bb_callback_call VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", cb_calls)
    print(f"Callback calls: {len(cb_calls)}")
    batch_insert("INSERT IGNORE INTO bb_marketing_call VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", mkt_calls)
    print(f"Marketing calls: {len(mkt_calls)}")
    batch_insert("INSERT IGNORE INTO bb_competitor_call VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", comp_calls)
    print(f"Competitor calls: {len(comp_calls)}")
    if pending_rows:
        batch_insert("INSERT IGNORE INTO bb_pending_pool VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)", pending_rows)
        print(f"Pending pool: {len(pending_rows)}")
    if demands:
        batch_insert("INSERT IGNORE INTO bb_user_demand VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", demands)
        print(f"User demands: {len(demands)}")
    batch_insert("INSERT IGNORE INTO bb_evidence VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", evidences)
    print(f"Evidences: {len(evidences)}")
    batch_insert("INSERT IGNORE INTO bb_audit_trail VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)", trails)
    print(f"Audit trails: {len(trails)}")


def main():
    c = get_conn()
    cur = c.cursor()
    insert_base_data(cur)
    addr_ids = gen_addresses(cur, 300)
    cust_ids = gen_customers(cur, 500)
    eng_ids  = gen_engineers(cur)
    c.commit()
    gen_orders_and_churns(cur, cust_ids, addr_ids, eng_ids, n_orders=1200)
    c.commit()
    c.close()
    print("\n数据生成完成")

if __name__ == '__main__':
    main()
