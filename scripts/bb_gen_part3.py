def insert_base_data(cur):
    for p in PRODUCTS:
        cur.execute("INSERT IGNORE INTO bb_product VALUES(%s,%s,%s,%s,'在售','住宅')", p)
    for c in CHANNELS:
        cur.execute("INSERT IGNORE INTO bb_channel VALUES(%s,%s,%s,%s,%s)", c)
    print("Base data inserted")

def gen_addresses(cur, n=300):
    rows = []
    for i in range(n):
        aid = f"ADDR{i+1:05d}"
        comm = rng.choice(COMMUNITIES)
        name, res_status, hist_rate, is_mono, has_plan, prop_coop = comm
        addr = gen_address(name)
        is_uncond = 1 if res_status != '无资源' else 0
        open_days = 0 if is_uncond else rng.randint(30, 180)
        rows.append((aid, addr, name, '房间', is_uncond, open_days,
                     res_status, hist_rate, is_mono, has_plan, prop_coop))
    cur.executemany("INSERT IGNORE INTO bb_address VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", rows)
    print(f"Inserted {n} addresses")
    return [r[0] for r in rows]

def gen_customers(cur, n=500):
    rows = []
    for i in range(n):
        cid = f"CUST{i+1:06d}"
        level = weighted_choice(['普通','银卡','金卡','钻石'],[60,25,12,3])
        age = rng.randint(0, 120)
        complaints = rng.choices([0,1,2,3,4,5],[50,25,12,7,4,2])[0]
        churns_cnt = rng.choices([0,1,2],[70,22,8])[0]
        blacklist = 1 if complaints >= 4 else 0
        credit = rng.randint(550, 950)
        rows.append((cid, gen_name(), gen_phone(), level, age,
                     complaints, churns_cnt, blacklist, 1, credit))
    cur.executemany("INSERT IGNORE INTO bb_customer VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", rows)
    print(f"Inserted {n} customers")
    return [r[0] for r in rows]

def gen_engineers(cur):
    rows = []
    for i, e in enumerate(ENGINEER_NAMES):
        eid = f"ENG{i+1:04d}"
        name, level, emp, team, churn_r, ontime_r, optical_r = e
        monthly = rng.randint(30, 120)
        complaints = rng.randint(0, max(1, int(churn_r * 20)))
        skills = rng.choice(['FTTH,FTTR','FTTH','FTTH,FTTB','FTTH,FTTR,FTTB','全类型'])
        rows.append((eid, name, level, emp, team, skills,
                     churn_r, ontime_r, optical_r, monthly, complaints))
    cur.executemany("INSERT IGNORE INTO bb_engineer VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", rows)
    print(f"Inserted {len(rows)} engineers")
    return [f"ENG{i+1:04d}" for i in range(len(ENGINEER_NAMES))]
