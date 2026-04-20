"""宽带退单稽核场景造数脚本 - 真实感强、分布合理"""
import pymysql, random, datetime, hashlib
from decimal import Decimal

DB = dict(host='127.0.0.1', port=3307, user='root', password='123456',
          db='bb_churn_audit', charset='utf8mb4')

def get_conn():
    c = pymysql.connect(**DB)
    c.cursor().execute("SET sql_mode=''")
    c.commit()
    return c

rng = random.Random(42)

def rdate(start='2024-10-01', end='2025-03-31'):
    s = datetime.datetime.strptime(start, '%Y-%m-%d')
    e = datetime.datetime.strptime(end, '%Y-%m-%d')
    return s + datetime.timedelta(seconds=rng.randint(0, int((e-s).total_seconds())))

def rid(prefix, n): return f"{prefix}{n:06d}"

# ── 根因配置（分布权重）──────────────────────────────────────────
ROOT_CAUSES = [
    # code, l1, l2, weight, churn_texts, phases
    ('施1','施工原因','入户线问题',      8,  ['入户线老化无法穿线','楼道管道堵塞无法布线','入户线路损坏需更换'], ['施工中','施工后']),
    ('施2','施工原因','施工受阻(物业/房东)', 9, ['物业不配合开门','房东不同意施工','物业要求缴纳施工费'], ['施工中']),
    ('施3','施工原因','智家人员问题',    10, ['工程师态度差客户投诉','工程师迟到超过2小时','工程师技术水平不足'], ['施工中','施工后']),
    ('施4','施工原因','无法攻克技术问题', 7, ['光衰超标无法达标','设备兼容性问题无法解决','FTTR组网复杂无法完成'], ['施工中']),
    ('用1','用户原因','用户不想装',      7,  ['客户说暂时不在本地','客户出差无法配合','客户说近期不需要'], ['受理后','派单后']),
    ('用2','用户原因','联系不上用户',    8,  ['多次拨打无人接听','用户电话关机','预约时间到达无人在家'], ['派单后','施工中']),
    ('用3','用户原因','已选友商',        6,  ['客户已办理移动宽带','客户选择联通套餐更便宜','客户说已经装好了'], ['受理后','派单后']),
    ('用4','用户原因','实名认证问题',    5,  ['身份证信息不符无法实名','客户证件过期','实名认证系统异常'], ['受理后']),
    ('用5','用户原因','支付/金融问题',   5,  ['安装费用问题协商未果','客户要求免费安装被拒','押金问题未解决'], ['受理后','派单后']),
    ('用6','用户原因','用户要求变更',    7,  ['客户要求更换套餐被拒','客户要求更改安装地址','客户要求升级产品'], ['受理后','派单后']),
    ('资1','资源原因','建设时间长',      6,  ['该区域宽带建设预计3个月后完成','小区光纤改造中预计60天','待装库积压等待时间过长'], ['受理后']),
    ('资2','资源原因','非无条件受理区域', 5, ['该地址不在无条件受理范围','偏远地区暂不提供服务','农村地区暂无覆盖'], ['受理后']),
    ('资3','资源原因','无资源覆盖',      5,  ['该地址无宽带资源覆盖','端口资源已满无法新增','OLT容量不足'], ['受理后','派单后']),
    ('资4','资源原因','待装无建设计划',  4,  ['该小区暂无建设计划','运营商暂不覆盖该区域','该地址无建设规划'], ['受理后']),
    ('资5','资源原因','资源不足/故障',   5,  ['光缆故障维修中','主干光缆容量不足','分纤箱端口全满'], ['派单后','施工中']),
    ('资6','资源原因','垄断小区',        4,  ['该小区为广电独家运营','物业签订独家协议不允许其他运营商','小区已被竞争对手垄断'], ['受理后']),
    ('业1','业务原因','资费疑问',        4,  ['客户对套餐资费有疑问未解决','客户认为价格偏高','客户要求优惠未获批准'], ['受理后']),
    ('业2','业务原因','办理条件限制',    4,  ['客户不满足办理条件','宽带账户欠费无法新装','客户信用评分不足'], ['受理后']),
    ('业3','业务原因','重复单',          3,  ['系统检测到重复工单','客户已有在途工单','同地址已有有效工单'], ['受理后']),
    ('业4','业务原因','未申请业务',      3,  ['客户表示未申请该业务','工单系统录入错误','渠道误操作创建工单'], ['受理后']),
    ('业5','业务原因','受理信息错误',    4,  ['地址信息录入错误','联系电话有误无法联系','客户姓名与证件不符'], ['受理后']),
    ('业6','业务原因','业务规则限制',    4,  ['该产品不支持该地址类型','套餐与地址类型不匹配','产品已停售'], ['受理后']),
    ('业7','业务原因','测试单',          3,  ['系统测试工单','渠道测试数据','内部测试单据'], ['受理后']),
    ('业8','业务原因','渠道权限不足',    4,  ['渠道权限不够无法受理','代理商无权限办理该产品','渠道级别不足'], ['受理后']),
]

# 证据定义：code, name, type, 适用根因codes, content模板
EVIDENCE_DEF = [
    ('E1',  'nlp',  '工程师陈述原因',       ['施1','施2','施3','施4'], ['工程师反映入户线老化','工程师说物业不配合','工程师表示技术难度大']),
    ('E2',  'nlp',  '工程师技术困难陈述',   ['施4','施1'],             ['工程师反映光衰超标','工程师说设备不兼容','工程师表示无法完成施工']),
    ('E3',  'nlp',  '工程师资源限制陈述',   ['资3','资5','资1'],       ['工程师反映端口不足','工程师说光缆故障','工程师表示资源紧张']),
    ('E4',  'nlp',  '用户选择友商',         ['用3'],                   ['用户说已办移动宽带','用户表示选择联通','用户已签约其他运营商']),
    ('E5',  'nlp',  '用户主动取消意愿',     ['用1','用6'],             ['用户说暂时不需要','用户要求取消工单','用户表示近期不装']),
    ('E6',  'nlp',  '用户投诉工程师',       ['施3'],                   ['用户投诉工程师态度差','用户反映工程师迟到','用户对服务不满意']),
    ('E7',  'nlp',  '用户价格异议',         ['业1','用5'],             ['用户认为价格太贵','用户要求优惠','用户对资费有疑问']),
    ('E8',  'nlp',  '用户需求变更意愿',     ['用6'],                   ['用户要求更换套餐','用户想更改地址','用户要求升级产品']),
    ('E9',  'nlp',  '物业/房东阻碍陈述',    ['施2'],                   ['物业不同意施工','房东拒绝开门','物业要求额外费用']),
    ('E10', 'nlp',  '资源不足陈述',         ['资3','资5'],             ['该地址无端口资源','光缆容量已满','OLT资源不足']),
    ('E11', 'nlp',  '地址覆盖问题陈述',     ['资2','资4'],             ['该地址不在覆盖范围','偏远地区无法覆盖','暂无建设计划']),
    ('E12', 'nlp',  '业务办理障碍陈述',     ['业2','业5','业6'],       ['客户不满足办理条件','信息录入有误','产品不适用该地址']),
    ('E13', 'nlp',  '重复单/测试单识别',    ['业3','业7'],             ['系统检测重复工单','内部测试数据','渠道误操作']),
    ('E14', 'nlp',  '客户情绪愤怒',         ['施3','用1'],             ['客户情绪激动','客户强烈不满','客户要求立即取消']),
    ('E15', 'nlp',  '客户情绪焦虑',         ['用2','施3'],             ['客户表现焦虑','客户多次催促','客户情绪不稳定']),
    ('E16', 'nlp',  '客户满意度低',         ['施3','施4'],             ['客户对服务评价差','客户表示非常失望','客户拒绝再次预约']),
    ('E17', 'nlp',  '渠道问题陈述',         ['业4','业8'],             ['渠道权限不足','代理商操作失误','渠道录入错误']),
    ('E18', 'nlp',  '多次改约记录',         ['用2','施3'],             ['多次改约','预约多次未到','反复改变时间']),
    ('E19', 'nlp',  '实名认证问题陈述',     ['用4'],                   ['身份证信息不符','证件过期无法认证','实名认证失败']),
    ('E20', 'nlp',  '支付问题陈述',         ['用5'],                   ['安装费用争议','押金问题未解决','客户拒绝支付']),
    ('E21', 'nlp',  '垄断小区识别',         ['资6'],                   ['小区已被竞争对手垄断','物业签独家协议','广电独家运营']),
    ('E22', 'nlp',  '回访确认施工问题',     ['施1','施2','施3','施4'], ['回访确认工程师问题','回访核实施工受阻','回访证实技术困难']),
    ('E23', 'nlp',  '回访确认用户原因',     ['用1','用3','用6'],       ['回访确认用户主动取消','回访核实已选友商','回访证实需求变更']),
    ('E24', 'nlp',  '回访核实资源问题',     ['资1','资2','资3'],       ['回访确认资源不足','回访核实无覆盖','回访证实建设时间长']),
    ('E25', 'nlp',  '回访核实业务问题',     ['业1','业2','业5'],       ['回访确认资费疑问','回访核实办理条件','回访证实信息错误']),
    ('E26', 'nlp',  '营销挽回通话内容',     ['用1','用3'],             ['营销挽回用户失败','用户拒绝重新预约','用户坚持取消']),
    ('E27', 'rule', '派单延迟>24h',         ['施3','用2'],             ['派单延迟>24h']),
    ('E28', 'rule', '工程师近90日退单率高', ['施3'],                   ['工程师退单率>15%']),
    ('E29', 'rule', '多次改约(≥2次)',       ['用2','施3'],             ['改约次数≥2次']),
    ('E30', 'rule', '光衰超标',             ['施1','施4'],             ['光衰值超过阈值']),
    ('E31', 'rule', '测速不达标',           ['施4','施1'],             ['测速低于套餐标称速率80%']),
    ('E32', 'rule', '待装库积压>30天',      ['资1','资4'],             ['待装库积压超30天']),
    ('E33', 'rule', '地址历史退单率高',     ['资3','资6','施2'],       ['该地址历史退单率>20%']),
    ('E34', 'rule', '工单受理后72h未派单',  ['业5','业4'],             ['受理后72小时未派单']),
    ('E35', 'rule', '实际资源核查不足',     ['资3','资5'],             ['现场核查资源不足']),
    ('E36', 'rule', '竞争对手通话频次高',   ['用3'],                   ['7日内竞品通话≥2次']),
    ('E37', 'rule', '回访补全信息',         ['用4','业5'],             ['回访补全实名信息']),
]

EVIDENCE_MAP = {e[0]: e for e in EVIDENCE_DEF}

def weighted_choice(items, weights):
    total = sum(weights)
    r = rng.uniform(0, total)
    for item, w in zip(items, weights):
        r -= w
        if r <= 0:
            return item
    return items[-1]

def gen_phone():
    prefixes = ['138','139','136','137','150','151','152','158','159','186','187','188','189','176','177','178']
    return rng.choice(prefixes) + ''.join([str(rng.randint(0,9)) for _ in range(8)])

def gen_name():
    surnames = '王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许邓冯韩曹曾彭萧蔡潘田董袁于余叶蒋盛钱'
    names2 = '伟芳娜秀英敏静丽强磊军洋勇艳杰娟涛明超霞秋香云莉诚志华建国平东文博'
    return rng.choice(surnames) + rng.choice(names2) + (rng.choice(names2) if rng.random() > 0.4 else '')

def gen_address(community):
    buildings = rng.randint(1, 30)
    units = rng.randint(1, 6)
    rooms = rng.randint(101, 2506)
    return f"{community}{buildings}栋{units}单元{rooms}室"

# ── 静态基础数据 ─────────────────────────────────────────────────

PRODUCTS = [
    ('P001','FTTH','电信宽带100M套餐',100),
    ('P002','FTTH','电信宽带200M套餐',200),
    ('P003','FTTH','电信宽带500M套餐',500),
    ('P004','FTTH','电信宽带1000M套餐',1000),
    ('P005','FTTR','全屋WiFi200M套餐',200),
    ('P006','FTTR','全屋WiFi500M套餐',500),
    ('P007','FTTB','楼道宽带100M',100),
    ('P008','ComboAPON','融合套餐200M',200),
    ('P009','ComboAPON','融合套餐500M',500),
    ('P010','FTTH','电信宽带300M套餐',300),
]

CHANNELS = [
    ('CH001','营业厅自营','自营厅',0.08,1),
    ('CH002','网上营业厅','网络渠道',0.12,1),
    ('CH003','电话营销中心','电话营销',0.15,1),
    ('CH004','代理商A','代理商',0.18,0),
    ('CH005','代理商B','代理商',0.20,0),
    ('CH006','上门营销','上门营销',0.22,0),
    ('CH007','微信公众号','网络渠道',0.10,1),
    ('CH008','第三方平台','网络渠道',0.14,0),
    ('CH009','社区推广','上门营销',0.19,0),
    ('CH010','企业客户部','自营厅',0.07,1),
]

COMMUNITIES = [
    ('阳光花园','充足',0.06,0,1,'良好'),
    ('碧桂园','充足',0.05,0,1,'良好'),
    ('万科城市花园','充足',0.07,0,1,'良好'),
    ('恒大名都','充足',0.08,0,1,'一般'),
    ('保利花园','充足',0.06,0,1,'良好'),
    ('龙湖天街','充足',0.09,0,1,'良好'),
    ('中海国际','充足',0.07,0,1,'良好'),
    ('绿地中央广场','紧张',0.12,0,1,'一般'),
    ('华润橡树湾','紧张',0.11,0,1,'一般'),
    ('金地格林','紧张',0.13,0,1,'困难'),
    ('远洋天地','不足',0.18,0,1,'困难'),
    ('富力城','不足',0.20,0,1,'困难'),
    ('雅居乐','无资源',0.35,0,0,'困难'),
    ('城郊新村','无资源',0.40,1,0,'困难'),
    ('工业园区宿舍','紧张',0.15,0,1,'一般'),
    ('老城区改造小区','不足',0.25,0,0,'困难'),
    ('新开发区A区','充足',0.04,0,1,'良好'),
    ('新开发区B区','充足',0.05,0,1,'良好'),
    ('学府名苑','充足',0.06,0,1,'良好'),
    ('滨江豪庭','充足',0.08,0,1,'良好'),
    ('广电独家小区','充足',0.45,1,1,'良好'),  # 垄断小区
    ('联通独家小区','充足',0.42,1,1,'良好'),  # 垄断小区
]

ENGINEER_NAMES = [
    ('张伟','高级','自有','装维一班',0.06,0.92,0.95),
    ('李强','中级','自有','装维一班',0.09,0.88,0.91),
    ('王磊','中级','外包','装维二班',0.12,0.85,0.88),
    ('刘洋','初级','外包','装维二班',0.18,0.78,0.82),
    ('陈军','高级','自有','装维三班',0.05,0.94,0.96),
    ('杨帆','中级','智家','智家团队',0.14,0.82,0.85),
    ('赵鑫','初级','智家','智家团队',0.22,0.72,0.78),
    ('吴涛','专家','自有','装维一班',0.04,0.96,0.98),
    ('周杰','中级','外包','装维三班',0.16,0.80,0.83),
    ('徐明','初级','外包','装维二班',0.25,0.68,0.75),
    ('孙浩','高级','自有','装维三班',0.07,0.91,0.93),
    ('马超','中级','智家','智家团队',0.13,0.84,0.87),
    ('朱峰','初级','外包','装维一班',0.20,0.75,0.80),
    ('胡斌','中级','自有','装维二班',0.10,0.87,0.90),
    ('郭亮','高级','自有','装维三班',0.06,0.93,0.95),
    ('何勇','初级','智家','智家团队',0.28,0.65,0.72),
    ('高峰','中级','外包','装维一班',0.15,0.81,0.84),
    ('林涛','专家','自有','装维二班',0.03,0.97,0.99),
    ('罗刚','中级','外包','装维三班',0.17,0.79,0.82),
    ('郑华','初级','外包','装维一班',0.23,0.70,0.76),
]

def insert_base_data(cur):
    # products
    for p in PRODUCTS:
        cur.execute("INSERT IGNORE INTO bb_product VALUES(%s,%s,%s,%s,'在售','住宅')", p)
    # channels
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
    cur.executemany("""INSERT IGNORE INTO bb_address VALUES
        (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", rows)
    print(f"Inserted {n} addresses")
    return [r[0] for r in rows]

def gen_customers(cur, n=500):
    rows = []
    for i in range(n):
        cid = f"CUST{i+1:06d}"
        level = weighted_choice(['普通','银卡','金卡','钻石'],[60,25,12,3])
        age = rng.randint(0, 120)
        complaints = rng.choices([0,1,2,3,4,5],[50,25,12,7,4,2])[0]
        churns = rng.choices([0,1,2],[70,22,8])[0]
        blacklist = 1 if complaints >= 4 else 0
        credit = rng.randint(550, 950)
        rows.append((cid, gen_name(), gen_phone(), level, age,
                     complaints, churns, blacklist, 1, credit))
    cur.executemany("""INSERT IGNORE INTO bb_customer VALUES
        (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", rows)
    print(f"Inserted {n} customers")
    return [r[0] for r in rows]

def gen_engineers(cur):
    rows = []
    for i, e in enumerate(ENGINEER_NAMES):
        eid = f"ENG{i+1:04d}"
        name, level, emp, team, churn_r, ontime_r, optical_r = e
        monthly = rng.randint(30, 120)
        complaints = rng.randint(0, int(churn_r * 20))
        skills = rng.choice(['FTTH,FTTR','FTTH','FTTH,FTTB','FTTH,FTTR,FTTB','全类型'])
        rows.append((eid, name, level, emp, team, skills,
                     churn_r, ontime_r, optical_r, monthly, complaints))
    cur.executemany("""INSERT IGNORE INTO bb_engineer VALUES
        (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", rows)
    print(f"Inserted {len(rows)} engineers")
    return [f"ENG{i+1:04d}" for i in range(len(ENGINEER_NAMES))]


PRODUCTS = [
    ('P001','FTTH','电信宽带100M套餐',100),
    ('P002','FTTH','电信宽带200M套餐',200),
    ('P003','FTTH','电信宽带500M套餐',500),
    ('P004','FTTH','电信宽带1000M套餐',1000),
    ('P005','FTTR','全屋WiFi200M套餐',200),
    ('P006','FTTR','全屋WiFi500M套餐',500),
    ('P007','FTTB','楼道宽带100M',100),
    ('P008','ComboAPON','融合套餐200M',200),
    ('P009','ComboAPON','融合套餐500M',500),
    ('P010','FTTH','电信宽带300M套餐',300),
]

CHANNELS = [
    ('CH001','营业厅自营','自营厅',0.08,1),
    ('CH002','网上营业厅','网络渠道',0.12,1),
    ('CH003','电话营销中心','电话营销',0.15,1),
    ('CH004','代理商A','代理商',0.18,0),
    ('CH005','代理商B','代理商',0.20,0),
    ('CH006','上门营销','上门营销',0.22,0),
    ('CH007','微信公众号','网络渠道',0.10,1),
    ('CH008','第三方平台','网络渠道',0.14,0),
    ('CH009','社区推广','上门营销',0.19,0),
    ('CH010','企业客户部','自营厅',0.07,1),
]

COMMUNITIES = [
    ('阳光花园','充足',0.06,0,1,'良好'),
    ('碧桂园','充足',0.05,0,1,'良好'),
    ('万科城市花园','充足',0.07,0,1,'良好'),
    ('恒大名都','充足',0.08,0,1,'一般'),
    ('保利花园','充足',0.06,0,1,'良好'),
    ('龙湖天街','充足',0.09,0,1,'良好'),
    ('中海国际','充足',0.07,0,1,'良好'),
    ('绿地中央广场','紧张',0.12,0,1,'一般'),
    ('华润橡树湾','紧张',0.11,0,1,'一般'),
    ('金地格林','紧张',0.13,0,1,'困难'),
    ('远洋天地','不足',0.18,0,1,'困难'),
    ('富力城','不足',0.20,0,1,'困难'),
    ('雅居乐','无资源',0.35,0,0,'困难'),
    ('城郊新村','无资源',0.40,1,0,'困难'),
    ('工业园区宿舍','紧张',0.15,0,1,'一般'),
    ('老城区改造小区','不足',0.25,0,0,'困难'),
    ('新开发区A区','充足',0.04,0,1,'良好'),
    ('新开发区B区','充足',0.05,0,1,'良好'),
    ('学府名苑','充足',0.06,0,1,'良好'),
    ('滨江豪庭','充足',0.08,0,1,'良好'),
    ('广电独家小区','充足',0.45,1,1,'良好'),
    ('联通独家小区','充足',0.42,1,1,'良好'),
]

ENGINEER_NAMES = [
    ('张伟','高级','自有','装维一班',0.06,0.92,0.95),
    ('李强','中级','自有','装维一班',0.09,0.88,0.91),
    ('王磊','中级','外包','装维二班',0.12,0.85,0.88),
    ('刘洋','初级','外包','装维二班',0.18,0.78,0.82),
    ('陈军','高级','自有','装维三班',0.05,0.94,0.96),
    ('杨帆','中级','智家','智家团队',0.14,0.82,0.85),
    ('赵鑫','初级','智家','智家团队',0.22,0.72,0.78),
    ('吴涛','专家','自有','装维一班',0.04,0.96,0.98),
    ('周杰','中级','外包','装维三班',0.16,0.80,0.83),
    ('徐明','初级','外包','装维二班',0.25,0.68,0.75),
    ('孙浩','高级','自有','装维三班',0.07,0.91,0.93),
    ('马超','中级','智家','智家团队',0.13,0.84,0.87),
    ('朱峰','初级','外包','装维一班',0.20,0.75,0.80),
    ('胡斌','中级','自有','装维二班',0.10,0.87,0.90),
    ('郭亮','高级','自有','装维三班',0.06,0.93,0.95),
    ('何勇','初级','智家','智家团队',0.28,0.65,0.72),
    ('高峰','中级','外包','装维一班',0.15,0.81,0.84),
    ('林涛','专家','自有','装维二班',0.03,0.97,0.99),
    ('罗刚','中级','外包','装维三班',0.17,0.79,0.82),
    ('郑华','初级','外包','装维一班',0.23,0.70,0.76),
]

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

