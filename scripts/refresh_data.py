#!/usr/bin/env python3
"""自动把内置快照刷新到体彩最新开奖 —— 在能直连体彩的机器上运行（如本机）。

只改「数据」，绝不碰算法：
  index.html / public/index.html
    - JQC_SNAPSHOT           4 场进球最近开奖（推荐引擎的数据源）
    - ZFC_SNAPSHOT.recent    14 场胜负彩近期开奖（走势表用）
    - ZFC_SNAPSHOT.upcoming  当前在售期赛程 + 欧赔（14 场预测用；无在售期时置 null）
    - ZFC_SNAPSHOT.elo/.latest 沿历史比分滚动更新的球队实力分（配 latest 水位线一起推进）
  table.html / public/table.html            ROWS 追加新期（进球彩走势表）
  table-zfc.html / public/table-zfc.html    ROWS 追加新期（胜负彩走势表）

任何一路 fetch 失败即整体放弃、一个字节都不写（保证多文件一致）。
退出码：0 = 有更新已写入   3 = 已是最新、无改动   1 = 出错
用法：python3 scripts/refresh_data.py [--check]   （--check 只报告不落盘）
"""
import json, re, sys, os, datetime, urllib.request, urllib.error

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = '--check' in sys.argv
HDRS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17 Safari/605.1.15',
    'Referer': 'https://www.sporttery.cn/', 'Accept': 'application/json', 'Accept-Language': 'zh-CN,zh;q=0.9',
}
HIST = 'https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo={g}&provinceId=0&pageSize=30&isVerify=1&pageNo={p}'
UPCOMING = 'https://webapi.sporttery.cn/gateway/lottery/getFootBallMatchV1.qry?param=90,0&isFsl=1'
WPL = {'3': 'W', '1': 'P', '0': 'L'}
clean = lambda s: re.sub(r'\s+', '', str(s or ''))


def fnum(x):
    try:
        f = float(x)
        return f if f == f and f not in (float('inf'), float('-inf')) else None
    except (TypeError, ValueError):
        return None


def get(url):
    req = urllib.request.Request(url, headers=HDRS)
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.load(r)


def die(msg):
    print('✗ ' + msg, file=sys.stderr)
    sys.exit(1)


# ---------- 抓取（全部先抓，任何失败即放弃） ----------
try:
    jqc = get(HIST.format(g=94, p=1))
    zfc_pages = [get(HIST.format(g=90, p=p)) for p in (1, 2)]
    upcoming_raw = get(UPCOMING)
except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
    die('体彩接口不可达（此机可能无法直连 .cn）：%s' % e)

# ---------- 解析 JQC（8 位 0-3，3+ 记 3；含 * 或不足 8 位则跳过） ----------
jqc_rows = []
for it in (jqc.get('value', {}).get('list') or []):
    parts = str(it.get('lotteryDrawResult', '')).split()
    if len(parts) != 8 or any('*' in p for p in parts):
        continue
    d = ''.join('3' if p.startswith('3') else p for p in parts)
    if len(d) == 8 and all(c in '0123' for c in d):
        jqc_rows.append((str(it['lotteryDrawNum']).strip(), d))
if not jqc_rows:
    die('JQC 无有效开奖')
jqc_rows.sort(key=lambda x: int(x[0]))

# ---------- 解析 ZFC（14 场 W/P/L + 队名） ----------
zfc_rows, zfc_results = [], {}   # results: issue -> [[home,away,outcome]×14]
for z in zfc_pages:
    for it in (z.get('value', {}).get('list') or []):
        iss = str(it.get('lotteryDrawNum', '')).strip()
        parts = str(it.get('lotteryDrawResult', '')).split()
        if len(parts) != 14 or not all(x in ('0', '1', '3') for x in parts):
            continue
        wpl = ''.join(WPL[x] for x in parts)
        zfc_rows.append((iss, wpl))
        ml = it.get('matchList') or []
        if len(ml) == 14:
            zfc_results[iss] = [[clean(m.get('masterTeamName')), clean(m.get('guestTeamName')), WPL[parts[i]]]
                                for i, m in enumerate(ml)]
zfc_rows = sorted({iss: wpl for iss, wpl in zfc_rows}.items(), key=lambda x: int(x[0]))
if not zfc_rows:
    die('ZFC 无有效开奖')

# ---------- 解析 在售期 + 欧赔 ----------
sfc = (upcoming_raw.get('value') or {}).get('sfcMatch') or {}
upcoming = None
ml = sfc.get('matchList') or []
if ml:
    upcoming = {
        'issue': str(sfc.get('lotteryDrawNum', '')),
        'drawTime': str(sfc.get('estimateDrawTime', ''))[:10],
        'saleEnd': str(sfc.get('lotterySaleEndtime', ''))[:16],
        'matches': [{'no': m.get('matchNum'), 'h': clean(m.get('masterTeamName')), 'a': clean(m.get('guestTeamName')),
                     'oh': fnum(m.get('h')), 'od': fnum(m.get('d')), 'oa': fnum(m.get('a')),
                     'league': m.get('matchName') or ''} for m in ml],
    }

today = datetime.date.today().isoformat()
changed = []

# ================= index.html：JQC_SNAPSHOT + ZFC_SNAPSHOT =================
idx = open(os.path.join(REPO, 'index.html'), encoding='utf-8').read()
orig_idx = idx

# —— JQC_SNAPSHOT（重建整条字面量；仅用最近 30 期）——
m = re.search(r'const JQC_SNAPSHOT=\{.*?\};', idx)
if not m:
    die('未找到 JQC_SNAPSHOT')
cur_jqc_latest = (re.search(r'latest:"(\d+)"', m.group(0)) or [None, None])[1]
jqc_latest = jqc_rows[-1][0]
snap = 'const JQC_SNAPSHOT={asOf:"%s",latest:"%s",results:[%s]};' % (
    today, jqc_latest, ','.join('{"issue":"%s","d":"%s"}' % (i, d) for i, d in reversed(jqc_rows)))
if m.group(0) != snap:
    idx = idx[:m.start()] + snap + idx[m.end():]
    if cur_jqc_latest != jqc_latest:
        changed.append('JQC 快照 %s→%s' % (cur_jqc_latest, jqc_latest))
    else:
        changed.append('JQC 快照数据刷新（latest 仍 %s）' % jqc_latest)

# —— ZFC_SNAPSHOT（JSON 往返，安全）——
mz = re.search(r'const ZFC_SNAPSHOT = (\{.*\});', idx)
if not mz:
    die('未找到 ZFC_SNAPSHOT')
zobj = json.loads(mz.group(1))

# recent：并入新期（升序去重）
have_recent = {r[0] for r in zobj['recent']}
add_recent = [[i, w] for i, w in zfc_rows if i not in have_recent]
if add_recent:
    zobj['recent'] = sorted(zobj['recent'] + add_recent, key=lambda x: int(x[0]))
    changed.append('ZFC recent +%d 期 →%s' % (len(add_recent), zobj['recent'][-1][0]))

# Elo：从 latest 水位线往后，用带队名的结果滚动更新；latest 与 elo 一起推进（二者必须一致）
cfg = zobj['eloConfig']
H, K, base = cfg['H'], cfg['K'], cfg['base']
R = dict(zobj['elo'])
prev_latest = int(zobj['latest'])
roll = sorted((int(i) for i in zfc_results if int(i) > prev_latest))
for iss in roll:
    for h, a, o in zfc_results[str(iss)]:
        rh = R.get(h, base); ra = R.get(a, base)
        eh = 1.0 / (1.0 + 10 ** (-((rh + H) - ra) / 400.0))
        sh = 1.0 if o == 'W' else 0.5 if o == 'P' else 0.0
        R[h] = round(rh + K * (sh - eh)); R[a] = round(ra - K * (sh - eh))
if roll:
    zobj['elo'] = R
    zobj['latest'] = str(roll[-1])
    changed.append('ZFC Elo 滚动 %d→%s' % (prev_latest, roll[-1]))

# upcoming：以接口为准（无在售期即 null）
if json.dumps(zobj.get('upcoming'), sort_keys=True, ensure_ascii=False) != json.dumps(upcoming, sort_keys=True, ensure_ascii=False):
    zobj['upcoming'] = upcoming
    changed.append('ZFC 在售期 →%s' % (upcoming['issue'] if upcoming else '无(null)'))
zobj['asOf'] = today

new_zfc = 'const ZFC_SNAPSHOT = ' + json.dumps(zobj, ensure_ascii=False, separators=(',', ':')) + ';'
idx = idx[:mz.start()] + new_zfc + idx[mz.end():]

# ================= table.html / table-zfc.html：ROWS 追加 =================
def append_rows(path, pattern, rows, label):
    t = open(os.path.join(REPO, path), encoding='utf-8').read()
    mt = re.search(r'const ROWS=\[(.*?)\];', t, re.S)
    if not mt:
        die('%s 未找到 ROWS' % path)
    have = {i for i, _ in re.findall(pattern, mt.group(1))}
    add = [r for r in rows if r[0] not in have]
    if not add:
        return t, None
    ins = ',' + ','.join('["%s","%s"]' % r for r in add)
    t = t[:mt.end() - 2] + ins + t[mt.end() - 2:]
    return t, '%s ROWS +%d →%s' % (label, len(add), add[-1][0])

tbl, c1 = append_rows('table.html', r'\["(\d+)","([0-3]{8})"\]', jqc_rows, 'table')
tblz, c2 = append_rows('table-zfc.html', r'\["(\d+)","([WPL]{14})"\]', zfc_rows, 'table-zfc')
if c1: changed.append(c1)
if c2: changed.append(c2)

# ================= 落盘 =================
if not changed:
    print('已是最新，无改动。JQC latest=%s  ZFC recent latest=%s' % (jqc_latest, zfc_rows[-1][0]))
    sys.exit(3)

print(('[--check] 将' if CHECK else '已') + '更新：')
for c in changed:
    print('  ·', c)

if CHECK:
    sys.exit(0)

writes = {'index.html': idx, 'table.html': tbl, 'table-zfc.html': tblz}
for name, content in writes.items():
    if content is None:
        continue
    open(os.path.join(REPO, name), 'w', encoding='utf-8').write(content)
    open(os.path.join(REPO, 'public', name), 'w', encoding='utf-8').write(content)
print('已写入根目录 + public/ 镜像。')
sys.exit(0)
