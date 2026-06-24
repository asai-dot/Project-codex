# ORCH-ARTICLE-JOIN — Worker Claude Code 発注: 記事↔issue_id 接合 dry-run（L4）

```yaml
order: ORCH-ARTICLE-JOIN
from: Cloud Code Web (codex, head=雑誌オブジェクト)
to: Worker Claude Code （Mac access保持の実行担当。owner 2026-06-24 アサイン=A 並行発注）
authority: owner GO済(WO-PERIODICAL-OWNER-GO-REQUEST)。本発注は read-only dry-run。
gate: read-only。DB書込・canonical昇格・accepted edge化・外部公開は含まない(別GO)。生payload移動/削除なし。
priority: 最優先(DD-PERIODICAL-002_PROGRESS_REVIEW D3)。L3と並行。
```

## 前提条件（着手前に必ず反映）
1. **入力 authority は最新版**（現時点 v11 `d1_journal_issn_authority_ALL_resolved_v11.csv`。着手時の最新を使う）。
2. **D2適用**: 別冊ジュリスト(NCID BN01263667)の判例百選58誌は **isbn_per_issue として扱う**
   （PROGRESS_REVIEW D2確定）。`ncid:BN01263667#通巻` で接合しない。各百選版はISBN単位で号を立てる。

## 処理（記事↔issue_id 接合）
入力: `build/labeled_v0.2.1/article_meta_labeled.jsonl`(read-only) ＋ authority(最新).csv。
```python
# 各記事 r:
# 1. journal_canonical → authority で key解決 (issn/ncid/isbn or unresolved)
# 2. status==isbn_per_issue の誌(別冊ジュリスト含む) → issue_id = isbn:{掲載誌から抽出したISBN/書誌単位キー}
#    それ以外 → vol/issue_no/issue_year/issue_month を tsuukan規則(direct/formula/ndl_actual/ym_terminal)で
#    通巻 or YYYY-MM に変換 → issue_id = {key}#{通巻|YYYY-MM}
# 3. article_id = {issue_id}#a{seq_in_issue}  (号内順不明なら #p{page_start})
# 4. 接合不能は status=orphan＋理由(authority_unresolved / tsuukan_unavailable / meta_missing)を記録
```

## 出力スキーマ（この列で固定。私の検査スクリプトが前提にする）
`artifacts/periodical/article_join_dryrun_v0.1.csv`、ヘッダ:
```
article_id, issue_id, journal_canonical, key_type, key_value, tsuukan_or_ym,
pub_year, vol, issue_no, page_start, seq_in_issue, title, join_status, orphan_reason
```
- `join_status` ∈ {joined, orphan}
- `orphan_reason` ∈ {"", authority_unresolved, tsuukan_unavailable, meta_missing}
併せてサマリ `article_join_summary_v0.1.json`:
`{total, joined, orphan, coverage, orphan_by_reason{}, orphan_by_journal_top20[], collision_count}`

## 受入基準（私=head が独立検査。これを満たせばL4接合「認定」）
- **article_collision = 0**（同一 article_id に異なる title）。
- **接合被覆 ≥ 95%**（joined / 全302,130。orphan の大半が authority_unresolved 長尾なら可）。
- **別冊ジュリスト衝突 = 0**（百選58誌が isbn単位で分離、同一 issue_id 衝突なし）。
- orphan は理由分類済（authority_unresolved は許容、tsuukan_unavailable/meta_missing は要改善対象として報告）。

## 返却（ファイル名は衝突回避で日付付き。`P##`系は使わない）
1. `article_join_dryrun_v0.1.csv` ＋ `article_join_summary_v0.1.json` を push。
2. orphan 主因と誌別上位。tsuukan_unavailable の誌は L3 へフィードバック。

## 検査体制
head(codex)が `tools/periodical/audit_article_join.py`（本発注と同時に用意）で受入基準を独立再検査。
合格 → L4接合認定 → 初出(pacsigny)/OCR(L2)へ進む。不合格 → 主因を返して再実行。
