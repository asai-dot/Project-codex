import csv
from collections import defaultdict

PREV='artifacts/periodical/hanrei_authority_fix_preview_v0.1.csv'
A='/Users/yuta/alo-ai/work/d1law_dl/_parsed_hanrei/判例_identity_keys_20260605.csv'
B='/Users/yuta/alo-ai/work/d1law_dl/_parsed_hanrei/判例_identity_keys_backfill6yr_20260617.csv'
OUT='artifacts/periodical/判例_identity_keys_vnext_candidate_20260701_PROPOSAL.csv'
CHG='artifacts/periodical/hanrei_apply_changelog_20260701.csv'

with open(PREV) as f:
    r=list(csv.reader(f)); ph=r[0]
prows=[dict(zip(ph,x)) for x in r[1:]]

auth=[]
for path in (A,B):
    with open(path, encoding='utf-8-sig') as f:
        rr=csv.reader(f); H=next(rr)
        for x in rr: auth.append(list(x))
ID=H.index('判例ID'); CK=H.index('court_key'); DT=H.index('date_key'); DK=H.index('docket_key'); IK=H.index('identity_key')
N=len(auth)
by_id=defaultdict(list); by_ik=defaultdict(list)
for i,x in enumerate(auth): by_id[x[ID]].append(i); by_ik[x[IK]].append(i)

changelog=[]  # object,op,key,detail,before_row,after_row,reason
def rowstr(x): return ' | '.join(x)

# ---------- REDERIVABLE: fix court_key + rebuild identity_key ----------
red=[x for x in prows if x['verdict']=='REDERIVABLE']
red_affected=set()
for x in red:
    mangled=x['key']; new=x['new_value']
    for i in range(N):
        if auth[i][CK]==mangled:
            before=list(auth[i])
            auth[i][CK]=new
            auth[i][IK]=new+'|'+auth[i][DT]+'|'+auth[i][DK]
            red_affected.add(i)
            changelog.append(['hanrei','REDERIVABLE',mangled,'court_key %s->%s; identity_key rebuilt'%(mangled,new),
                              rowstr(before),rowstr(auth[i]),x['evidence']])

# ---------- TRUE_DUP: union-find components from ORIGINAL grouping ----------
td=[x for x in prows if x['verdict']=='TRUE_DUP']
groups=[]
for x in td:
    idx = by_id[x['key']] if x['issue']=='DUP_HANREI_ID' else by_ik[x['key']]
    groups.append(idx)
parent={}
def find(a):
    parent.setdefault(a,a)
    while parent[a]!=a: parent[a]=parent[parent[a]]; a=parent[a]
    return a
for idx in groups:
    for j in idx[1:]:
        ra,rb=find(idx[0]),find(j)
        if ra!=rb: parent[ra]=rb
comp=defaultdict(list); allrows=set(i for idx in groups for i in idx)
for i in allrows: comp[find(i)].append(i)

# sanity: no dedup component row was also REDERIVABLE-modified in a conflicting way
overlap=allrows & red_affected
# survivor scoring: full docket, then correct (un-mangled longer) court, then min 判例ID, then min index
def has_ascii_digit(s): return any(c.isdigit() and ord(c)<128 for c in s)
def numid(s):
    try: return int(s)
    except: return 10**18
def score(i):
    x=auth[i]
    return (len(x[DK]), 0 if has_ascii_digit(x[CK]) else 1, len(x[CK]), -numid(x[ID]))
remove=set()
for root,members in comp.items():
    survivor=max(members, key=lambda i:(score(i), -i))
    for i in members:
        if i!=survivor:
            remove.add(i)
            changelog.append(['hanrei','TRUE_DUP(dedup remove)',auth[i][ID],
                              'merged into 判例ID=%s (survivor)'%auth[survivor][ID],
                              rowstr(auth[i]),'(removed; survivor='+rowstr(auth[survivor])+')',
                              'survivor rule: full-docket/correct-court/min-ID'])

final=[x for i,x in enumerate(auth) if i not in remove]

# ---------- write ----------
with open(OUT,'w',newline='') as f:
    w=csv.writer(f); w.writerow(H); w.writerows(final)
with open(CHG,'w',newline='') as f:
    w=csv.writer(f); w.writerow(['object','op','key','detail','before_row','after_row','reason']); w.writerows(changelog)

# ---------- regression ----------
mangled_keys=set(x['key'] for x in red)
def dupcount(rows,col,skip_empty=True):
    c=defaultdict(int)
    for x in rows:
        if skip_empty and x[col]=='': continue
        c[x[col]]+=1
    return sum(1 for v in c.values() if v>1)
id_dup_before=dupcount(auth,ID,skip_empty=False)
id_dup_after=dupcount(final,ID,skip_empty=False)
ik_dup_before=dupcount(auth,IK)
ik_dup_after=dupcount(final,IK)
court_mangle_after=sum(1 for x in final if x[CK] in mangled_keys)
print('=== HANREI candidate (PROPOSAL) ===')
print('input rows:',N,' removed:',len(remove),' candidate rows:',len(final))
print('  order expected: 211564 (assumes 1038 removals). ACTUAL distinct removals:',len(remove),'-> ',len(final))
print('REDERIVABLE rows fixed:',len(red_affected),' (15 court_keys)')
print('dedup components:',len(comp),' TRUE_DUP preview rows:',len(td))
print('判例ID dup before:',id_dup_before,' after:',id_dup_after,' (target 0)')
print('identity_key dup (non-empty) before:',ik_dup_before,' after:',ik_dup_after,' (should decrease)')
print('court-mangled court_key remaining in candidate:',court_mangle_after,' (target 0)')
print('REDERIVABLE∩dedup overlap rows:',len(overlap))
print('changelog rows:',len(changelog))
print('WROTE',OUT)
print('WROTE',CHG)
