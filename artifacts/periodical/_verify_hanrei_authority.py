import csv, unicodedata, re, sys, json, calendar
from collections import defaultdict, Counter

CORR = "/Users/yuta/Project-codex/.claude/worktrees/casename-dict/artifacts/periodical/hanrei_authority_corrections_v0.1.csv"
AUTH = ["/Users/yuta/alo-ai/work/d1law_dl/_parsed_hanrei/判例_identity_keys_20260605.csv",
        "/Users/yuta/alo-ai/work/d1law_dl/_parsed_hanrei/判例_identity_keys_backfill6yr_20260617.csv"]
OUT_PREVIEW = "/Users/yuta/Project-codex/.claude/worktrees/wk-hanrei/artifacts/periodical/hanrei_authority_fix_preview_v0.1.csv"
OUT_SUMMARY = "/Users/yuta/Project-codex/.claude/worktrees/wk-hanrei/artifacts/periodical/_summary.json"

COLS = ['判例ID','court_key','date_key','docket_key','identity_key','裁判所名','判決年月日','事件番号','事件名']

rows = []
by_hid = defaultdict(list)
by_ident = defaultdict(list)
courtkey_to_names = defaultdict(set)
for path in AUTH:
    with open(path, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            rows.append(row)
            by_hid[row['判例ID']].append(row)
            by_ident[row['identity_key']].append(row)
            courtkey_to_names[row['court_key']].add(row['裁判所名'])
print("authority rows:", len(rows), file=sys.stderr)

def nfkc(s): return unicodedata.normalize('NFKC', s or '')
def norm(s):
    # 軽微差(空白/表記ゆれ)吸収: NFKC化 + 区切り/装飾字(第・号)除去
    s = nfkc(s)
    s = re.sub(r'[\s　／/・,、\.]', '', s)
    s = s.replace('第', '').replace('号', '')
    return s

# 判決の同一性を分ける識別列(判例ID/identity_key はキーそのものなので除外)
DISCRIM = ['court_key','裁判所名','date_key','判決年月日','docket_key','事件番号','事件名']

def is_subset_chain(vals):
    """True if, among normalized non-empty values, the longest contains every other
    (consolidation: shared lead docket, extra consolidated numbers appended)."""
    nv = [norm(v) for v in vals if norm(v)]
    if len(nv) < 2:
        return False
    longest = max(nv, key=len)
    return all(v in longest for v in nv)

def compare_rows(group, issue):
    distinct = []; seen = set()
    for row in group:
        sig = tuple(row[c] for c in COLS)
        if sig not in seen:
            seen.add(sig); distinct.append(row)
    n_raw = len(group); n_distinct = len(distinct)
    if n_distinct == 1:
        return "TRUE_DUP", f"{n_raw}行が全列完全一致(純重複登録)"
    # 識別列(DISCRIM)のみで実質差を判定。判例ID/identity_key の差は同一判決の想定内。
    diff_cols = [c for c in DISCRIM if len({r[c] for r in distinct}) > 1]
    subst_cols = [c for c in diff_cols if len({norm(r[c]) for r in distinct}) > 1]
    key_diff = [c for c in ['事件名','事件番号','docket_key','裁判所名','判決年月日','date_key','court_key','判例ID']
                if len({r[c] for r in distinct}) > 1]
    ev_parts = [f"{c}=[{' || '.join(sorted({r[c] for r in distinct}))}]" for c in key_diff]
    ev = f"{n_distinct}別行; " + " ; ".join(ev_parts)
    if not subst_cols:
        return "TRUE_DUP", f"差異列={','.join(diff_cols) or '判例ID/identity のみ'} 正規化後一致(空白/表記ゆれ); " + ev
    # WO の DISTINCT トリガ = 事件名/事件番号/当事者が実質的に異なる（別判決）。
    name_diff = '事件名' in subst_cols
    docket_diff = ('docket_key' in subst_cols) or ('事件番号' in subst_cols)
    if name_diff:
        # 事件名が実質差 = 別判決。DUP_HANREI_ID→判例ID誤再利用疑い / DUP_IDENTITY_KEY→identity_key精緻化(統合禁止)
        return "DISTINCT", ev
    if docket_diff:
        subset = is_subset_chain([r['docket_key'] for r in distinct])
        if subset:
            # 併合事件: lead 一致・番号追加のみ。同一判決。full docket 採用推奨。
            return "TRUE_DUP", "docketが被併合(lead一致・full docket採用推奨); " + ev
        return "NEEDS_DECISION", "docketが非包含・事件名は同一(要head確認); " + ev
    # 残差 = court_key/date/裁判所名 のみの実質差。同一判例ID/identity → 同一判決の field不整合。
    if issue == 'DUP_HANREI_ID':
        return "TRUE_DUP", "同一判例ID・field不整合(支部粒度/化け等)→正しい値採用要; " + ev
    return "TRUE_DUP", "同一identity・field不整合→統合可; " + ev

ERA = {'明治':1868,'大正':1912,'昭和':1926,'平成':1989,'令和':2019}
def parse_wareki(s):
    s0 = nfkc(s)
    m = re.match(r'(明治|大正|昭和|平成|令和)(\d+)年(\d+)月(\d+)日', s0)
    if not m:
        return None, "日欠落(年月のみ or 解析不可)"
    era, y, mo, d = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
    year = ERA[era] + y - 1
    try:
        maxd = calendar.monthrange(year, mo)[1]
    except Exception:
        return None, f"月不正 mo={mo}"
    if not (1 <= mo <= 12 and 1 <= d <= maxd):
        return None, f"存在しない日 {year}-{mo:02d}-{d:02d}(当月最終日={maxd})"
    return f"{year:04d}{mo:02d}{d:02d}", "一意導出"

ARA2KAN = {'1':'一','2':'二','3':'三','4':'四','5':'五','6':'六','7':'七','8':'八','9':'九','0':'〇'}
def restore_court_key(mangled):
    if mangled and mangled[0] in ARA2KAN:
        return ARA2KAN[mangled[0]] + mangled[1:]
    return mangled

out = []
with open(CORR, encoding='utf-8', newline='') as f:
    for c in csv.DictReader(f):
        issue = c['issue']; key = c['key']
        verdict=""; new_val=""; evidence=""
        if issue in ('DUP_HANREI_ID','BAD_DATE'):
            grp = by_hid.get(key, [])
        elif issue == 'DUP_IDENTITY_KEY':
            grp = by_ident.get(key, [])
        else:
            grp = None
        if issue == 'DUP_HANREI_ID':
            if not grp: verdict="NEEDS_DECISION"; evidence="authorityに該当判例IDなし"
            else: verdict, evidence = compare_rows(grp, issue)
        elif issue == 'DUP_IDENTITY_KEY':
            if not grp: verdict="NEEDS_DECISION"; evidence="authorityに該当identity_keyなし"
            else: verdict, evidence = compare_rows(grp, issue)
        elif issue == 'BAD_DATE':
            if not grp: verdict="NEEDS_DECISION"; evidence="authorityに該当判例IDなし"
            else:
                wareki = grp[0]['判決年月日']
                newdk, why = parse_wareki(wareki)
                if newdk: verdict="REDERIVABLE"; new_val=newdk; evidence=f"判決年月日='{wareki}'→date_key={newdk} ({why})"
                else: verdict="SOURCE_CHECK"; evidence=f"判決年月日='{wareki}' {why} 原本確認要"
        elif issue == 'COURT_KEY_MANGLED':
            restored = restore_court_key(key)
            existing = courtkey_to_names.get(restored, set())
            mangled_names = courtkey_to_names.get(key, set())
            other = existing - mangled_names
            if not existing:
                verdict="REDERIVABLE"; new_val=restored; evidence=f"{key}→{restored} 既存court_keyに未存在(衝突0)"
            elif other:
                verdict="CONFLICT"; new_val=restored; evidence=f"{key}→{restored} 既存に別裁判所名{sorted(other)}(衝突)"
            else:
                verdict="REDERIVABLE"; new_val=restored; evidence=f"{key}→{restored} 既存も同一裁判所名{sorted(existing)}(衝突0・一部行が正)"
        else:
            verdict="NEEDS_DECISION"; evidence=f"未知issue {issue}"
        out.append({**c, 'verdict':verdict, 'new_value':new_val, 'evidence':evidence})

with open(OUT_PREVIEW, 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['issue','key','detail','recommend','sample','verdict','new_value','evidence'])
    w.writeheader()
    for o in out: w.writerow(o)

vc = Counter(o['verdict'] for o in out)
by_issue = defaultdict(Counter)
for o in out: by_issue[o['issue']][o['verdict']]+=1
print("TOTAL", len(out), file=sys.stderr)
print("VERDICTS", dict(vc), file=sys.stderr)
for iss, cc in by_issue.items(): print(iss, dict(cc), file=sys.stderr)
with open(OUT_SUMMARY,'w') as f:
    json.dump({'total':len(out),'verdicts':dict(vc),
               'by_issue':{k:dict(v) for k,v in by_issue.items()},
               'high_risk':[o for o in out if o['verdict'] in ('DISTINCT','SOURCE_CHECK','CONFLICT','NEEDS_DECISION')]},
              f, ensure_ascii=False, indent=1)
