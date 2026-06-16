# WO-D1TAXO-C-VERIFY — D1TAXO v3 JSONL 整合検証（統合版・ワーカー指示）2026-06-16

呼び名（トリガ）: 「D1TAXO 検証やって」
担当: ワーカーちゃん（ローカル alo-ai。実 JSONL アクセス可）
発注: 番頭 / owner: 浅井（承認済）
種別: **検証のみ（read-only / DB未投入 / ファイル非改変。apply は HOLD 継続）**
統合元: WO-D1TAXO-002（7項目）＋ ADDENDUM（8–14）＋ fp照合リファレンス。本書1本で完結。

## 対象（`app/data/pacsigny/iteration/`）

- `d1law_taikei_alo_terms_load_20260615_v3_alo_terms.jsonl`（49,733）
- `..._v3_alo_term_labels.jsonl`（49,733）
- `..._v3_alo_term_relations.jsonl`（38,910）
- `..._v3_alo_d1law_taikei_extra.jsonl`（49,733）
- `..._v3_statutes_candidates.jsonl`（5,341）
- `..._v3_manifest.json`（sha256/rows）／源 `d1law_live_taxonomy_20260612_nodes.jsonl`（55,074）

## STEP 1 — fp 照合（byte等価。これが本丸・1コマンド）

連結仕様: NFC・昇順・末尾改行。term/statute は `term_uri\n`、edge は `src\tskos_broader\tdst\n`。

```python
import json, hashlib, unicodedata
def fp(lines):
    h=hashlib.sha256()
    for s in sorted(lines): h.update((unicodedata.normalize("NFC",s)+"\n").encode())
    return h.hexdigest()
T=[json.loads(l)["term_uri"] for l in open("..._v3_alo_terms.jsonl")]
S=[json.loads(l)["term_uri"] for l in open("..._v3_statutes_candidates.jsonl")]
R=[f'{json.loads(l)["src_term_uri"]}\tskos_broader\t{json.loads(l)["dst_term_uri"]}' for l in open("..._v3_alo_term_relations.jsonl")]
print(fp(T), fp(R), fp(S))
```

期待値（源側＝あるべき値。一致すれば byte等価で C クローズ）:
```
fp_terms     = 23bade6c355b04390eaaf7553dfac3ec5df3eb25fde7e89667f162512404f4cc
fp_edges     = d3e22bc6c28e783d678b6ec801dbc0a539c2f03cd27746e30348ebfdcabbe1ab
fp_statutes  = eb389a4935916b5961447924fcaa0b608d7ba7297ff8f9ccdd687392aa31b73e
```

## STEP 2 — 不変条件（14項目）

1. 各 JSONL の sha256/行数 == manifest（terms49,733/labels49,733/relations38,910/extra49,733/statutes5,341、terms+statutes==55,074）
2. `term_uri` 重複0。labels/extra が terms と 1:1（orphan0）
3. relations: src/dst が terms に実在（dst orphan0）・`rel_type=skos_broader` のみ・自己参照0・サイクル0・**dst が statute(L1-3) でない**
4. `status` に `canonical` 混入0（許容 active/deprecated/merged/review_dismissed）・`term_tier∈{1,2}`
5. labels: pref/ja が term毎1件・`normalized_text==NFC(label_text)`
6. statutes_candidates.term_uri が terms と排他
7. 源 nodes.jsonl の L4-11(level≥3) 集合 == terms の source_item_key 集合（取りこぼし/混入0）／L1-3 == statutes
8. labels/relations が `source_version` 単位で閉じる（混在参照なし）
9. relation の src/dst が同一 scheme・同一 source_version
10. parentless term（level3=10,823）に `reason=parent_is_statute_layer` 記録
11. `raw_label` と `clean_label`/`search_norm` を区別保持（原表記が消えていない）
12. enumerator（L4-11 ナンバリング記号）の除去/分離有無を検査（name 統合ならフラグ）
13. term→statute の context edge/table 有無（L4→L3 を skos_broader で張らない代替接続が設計どおりか）
14. `scheme_id`/`source_item_key`/`source_version` の重複・混在なし

## 成果物（`from_worker/`）

- `VERIFY_d1taxo_v3_jsonl_integrity_<date>.md`（STEP1 fp 3値の一致可否 ＋ 14項目 PASS/件数表）
- `..._result.json`（機械可読・artifact。narrative完了では受理されない＝DD-D1TAXO-RDB-006準拠）
- NG は該当 term_uri/edge を最大50件添付

## DoD

- fp 3値一致 ＋ 14項目 PASS（or NG一覧）。read-only 厳守。apply は HOLD 継続。
