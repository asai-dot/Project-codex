import csv
from collections import defaultdict

V14='artifacts/periodical/d1_journal_issn_authority_ALL_resolved_v14.csv'
OUT='artifacts/periodical/d1_journal_issn_authority_ALL_resolved_v15_candidate.csv'
CHG='artifacts/periodical/journal_apply_changelog_20260701.csv'
NORM='artifacts/periodical/journal_authority_norm_preview_v0.1.csv'

with open(V14) as f:
    r=csv.reader(f); H=next(r); rows=[list(x) for x in r]
COL={c:i for i,c in enumerate(H)}
JC,AC,KT,KV,ST,SR,NT=COL['journal_canonical'],COL['article_count'],COL['key_type'],COL['key_value'],COL['status'],COL['source'],COL['note']
idx_by_name={x[JC]:i for i,x in enumerate(rows)}
assert len(idx_by_name)==len(rows), 'v14 has duplicate names'

with open(NORM) as f:
    nr=list(csv.reader(f)); nh=nr[0]
recs=[dict(zip(nh,x)) for x in nr[1:]]
normalize=[x for x in recs if x['verdict']=='NORMALIZE']
merge=[x for x in recs if x['verdict']=='MERGE_TO_EXISTING']

def rowstr(x): return ' | '.join(x)
changelog=[]  # object,op,key,field,before,after,reason,before_row,after_row

# --- 1. NORMALIZE (rename in place) ---
for m in normalize:
    src=m['canonical_group']; new=m['normalized_name']
    i=idx_by_name[src]
    before=list(rows[i])
    assert new not in idx_by_name, 'NORMALIZE target collides: '+new
    rows[i][JC]=new
    changelog.append(['journal','NORMALIZE',src,'journal_canonical',src,new,m['evidence'],rowstr(before),rowstr(rows[i])])
    # update index to keep collision detection valid for later ops
    del idx_by_name[src]; idx_by_name[new]=i

# --- 2. MERGE_TO_EXISTING (remove source, add ac to target, note) ---
remove_idx=set()
for m in merge:
    src=m['canonical_group']; tgt=m['merge_target']
    si=idx_by_name[src]; ti=idx_by_name[tgt]
    src_before=list(rows[si]); tgt_before=list(rows[ti])
    src_ac=int(rows[si][AC]); tgt_ac=int(rows[ti][AC])
    rows[ti][AC]=str(tgt_ac+src_ac)
    note=rows[ti][NT]
    add=f"merged<-{src}(ac={src_ac}) apply_20260701"
    rows[ti][NT]=(note+' | '+add) if note else add
    remove_idx.add(si)
    changelog.append(['journal','MERGE_TO_EXISTING(source removed)',src,'row',rowstr(src_before),'(removed)',m['evidence'],rowstr(src_before),'(removed)'])
    changelog.append(['journal','MERGE_TO_EXISTING(target updated)',tgt,'article_count/note',f"ac={tgt_ac}",f"ac={tgt_ac+src_ac}",m['evidence'],rowstr(tgt_before),rowstr(rows[ti])])

# --- 3. ISSN_RESOLVED 税理 ---
i=idx_by_name['税理']
before=list(rows[i])
assert rows[i][KT]=='ncid', '税理 unexpected key_type '+rows[i][KT]
rows[i][KT]='issn'; rows[i][KV]='0514-2512'; rows[i][SR]='ndl_sru:apply_20260701'
changelog.append(['journal','ISSN_RESOLVED','税理','key_type/key_value/source','ncid/AN00080095/seed:head_verified','issn/0514-2512/ndl_sru:apply_20260701','NDL SRU 0514-2512 (jissn proposal ISSN_RESOLVED)',rowstr(before),rowstr(rows[i])])

# --- write candidate ---
final=[x for i,x in enumerate(rows) if i not in remove_idx]
assert len(final)==931-7, f'row count {len(final)} != 924'
names=[x[JC] for x in final]
assert len(set(names))==len(names), 'duplicate journal_canonical in candidate'
with open(OUT,'w',newline='') as f:
    w=csv.writer(f); w.writerow(H); w.writerows(final)
with open(CHG,'w',newline='') as f:
    w=csv.writer(f); w.writerow(['object','op','key','field','before','after','reason','before_row','after_row'])
    w.writerows(changelog)

# --- regression ---
def issn_dupcount(rr):
    m=defaultdict(set)
    for x in rr:
        if x[KT]=='issn' and x[KV]: m[x[KV]].add(x[JC])
    return sum(1 for v in m.values() if len(v)>1), m
before_dup,_=issn_dupcount(rows if False else [list(x) for x in csv.reader(open(V14))][1:])
after_dup,after_m=issn_dupcount(final)
print('candidate rows:',len(final),'(expect 924)')
print('unique names:',len(set(names)))
print('changes: NORMALIZE',len(normalize),'MERGE',len(merge),'ISSN_RESOLVED 1  total',len(normalize)+len(merge)+1)
print('changelog rows:',len(changelog))
print('dup-ISSN before:',before_dup,'after:',after_dup,'(must be non-increase)')
print('0514-2512 users after:',sorted(after_m.get('0514-2512',[])))
print('WROTE',OUT,'and',CHG)
