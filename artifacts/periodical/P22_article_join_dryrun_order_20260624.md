# P22: ローカルちゃん発注 — GO-0 + GO-1（記事↔issue_id 接合 dry-run）

```yaml
artifact: P22_article_join_dryrun
generated_at: 2026-06-24 JST
authority: owner GO 2026-06-24 全GO承認(WO-PERIODICAL-OWNER-GO-REQUEST)。本発注はGO-0/GO-1のみ着手(read-only)。
gate: read-only/dry-run。DB書込・canonical昇格・edge化・外部公開は含まない(別GO)。生payload移動/削除なし。
ref: DD-PERIODICAL-002 (L1×L3接合), WO-PERIODICAL-OWNER-GO-REQUEST
```

## GO-0: locator 行抽出（REFERENCE_ONLY）
`docs/alo/AI_READY_DATA_LOCATOR_INDEX_LATEST.tsv` ＋ `AI_READY_DATA_LOCATOR_QUERY_CHEATSHEET_20260623.tsv` から、
雑誌オブジェクト関連レーンの**メタ行のみ**抽出（生payloadは開かない）。対象 lookup:
`pacsigny` / `scan_data` / `legal_thought` / D1文献編 / periodical。
返す列: `locator_id` / `primary_location` / `read_first` / `currentness` / `safety_note`(HOLD状態)。
→ DD-002 §3 の各レーン実体とHOLD状態を確定するため。

## GO-1: 記事↔issue_id 接合 dry-run（D1, read-only）
入力: `build/labeled_v0.2.1/article_meta_labeled.jsonl`(read-only) ＋ 確定 authority `d1_journal_issn_authority_ALL_resolved_v4.csv`。
処理（擬似コード）:
```python
# 1. 各記事 r の journal_canonical → authority で key(issn/ncid) 解決
# 2. r の vol/issue_no/issue_year/issue_month → tsuukan規則(direct/formula/ndl_actual/ym_terminal)で通巻 or YYYY-MM
# 3. issue_id = {key}#{tsuukan}  (ym_terminalは {key}#{YYYY-MM})
# 4. article_id = {issue_id}#a{seq_in_issue}  (号内順不明なら #p{page_start})
# 5. 候補CSV出力: article_id, issue_id, journal_canonical, key, tsuukan, pub_year, title, seq/page
```
出力: `artifacts/periodical/article_join_dryrun_v0.1.csv`（候補マップ。DB書込なし）。

**回帰検査（必須・0件を確認）:**
- `article_orphan`: issue_id 未解決(authority unresolved or 通巻算出不能)の記事数と誌別内訳。
- `article_collision`: 同一 article_id に異なる title/著者（=採番衝突）。
- 被覆率: 接合できた記事 / 全302,130件。誌別の orphan 上位を報告。

## 期待アウトプット（P23として返す）
1. GO-0 の locator 行（雑誌関連レーンのパス＋HOLD状態）。
2. article_join_dryrun_v0.1.csv の被覆率・orphan/collision 件数サマリ。
3. orphan の主因分類（authority unresolved / 通巻規則欠落 / メタ欠損）→ 次の精度改善対象。

## 着手していno事（権利確認待ち）
GO-3(pacsigny初出)・GO-4(scan_data OCR)・GO-5(legal_thought) は破壊性GOは下りているが
**LICENSE_CONFIRM_PENDING**（自所保有/ライセンス済の owner 明示確認待ち）。確認後に別発注。

## 分担
producer=ローカルちゃん(D1/索引はMacローカル)。監査=codex(head): 返却後に article_collision/orphan の
回帰検査を独立再実行し、接合精度を裏取り。誌の二重解決はしない。
