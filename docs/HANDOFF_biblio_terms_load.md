# 引き継ぎ — biblio.terms 語彙シード投入（provisional）

Supabase static DB `nixfjmwxmgugiiuqfuym`（asai-dot's Project）への、e-Gov錨×辞書/JLTの
**リッチ用語カード554件**の provisional 投入。GPTレビューの梯子 candidate→machine-gated→**provisional**→canonical の
provisional 段階。canonical 昇格は浅井さんの承認待ち。

## いま入っている状態（2026-06-03）
- **ガバナンス証跡**（codex作法に整合・登録済）:
  - `control.source_snapshots` = `snapshot:golden-term-card:0053466a340b`
  - `control.ingest_jobs` = `ingest:biblio:golden-term-card-rich:20260603`（status=**partial** 8/554）
  - `control.releases` = `release:biblio-terms-golden-rich:20260603`（**approval_status=pending**、rollback_target記録済）
- **`biblio.terms`** に **パイロット8件**投入済（`source='golden_term_card_v1'`、全件 term_yomi、canonical_status=provisional）。
- 投入元の正本: repo `data/db_staging/biblio_terms_richcards_v1.jsonl`（554件・フルprovenance）。

## 残り546を入れて完了する（DB権限が要る＝owner/codex/ローカルで）
クラウドsandboxにDB接続情報が無いため、以下いずれかを**DB接続のある環境**で1回:

**(a) SQLファイル（最も簡単・転記誤りゼロ）**
```bash
psql "$SUPABASE_DB_URL" -f data/db_staging/load_biblio_terms_richcards_v1.sql
```
→ 冪等（ON CONFLICT）。完了で ingest_job が succeeded・rows_inserted=554 に。

**(b) ローダースクリプト**
```bash
export SUPABASE_DB_URL='postgresql://...:5432/postgres'   # service role / direct connection
python3 phases/load_biblio_terms.py data/db_staging/biblio_terms_richcards_v1.jsonl
```

## canonical へ昇格（浅井さんの承認ゲート）
provisional は検索・下流に使わない。昇格は release の承認:
```sql
UPDATE control.releases
SET approval_status='approved', approved_by='浅井', activated_at=now()
WHERE release_id='release:biblio-terms-golden-rich:20260603';
-- 併せて terms.raw の canonical_status を 'canonical' へ更新する運用（owner判断）
```
（「承認」と言ってもらえれば私がMCPで approval_status を更新します。）

## ロールバック（完全可逆）
```sql
DELETE FROM biblio.terms WHERE source='golden_term_card_v1';
-- 必要なら証跡も:
DELETE FROM control.releases  WHERE release_id='release:biblio-terms-golden-rich:20260603';
DELETE FROM control.ingest_jobs WHERE ingest_job_id='ingest:biblio:golden-term-card-rich:20260603';
DELETE FROM control.source_snapshots WHERE source_snapshot_id='snapshot:golden-term-card:0053466a340b';
```

## 測って分かった次の一手（書誌軸）
- 仕様の `alo_terms/alo_hubs` は実在せず、**実体は `biblio.terms`**（語彙の受け皿・空だった）。
- **蔵書（NDL/ISBN）は未投入**: `biblio.bib_records` 3,802 は全て bencom-library（NOBN_系、ISBN6件のみ）。
  `biblio.bib_toc` は 555,887（bencom TOC）ロード済。
- よって**§8の橋 `biblio.bib_terms`（書誌↔用語）を張るには、まず蔵書を `bib_records` に載せる**のが先決。
  これが書誌軸の次の第一歩（`docs/DESIGN_bibliographic_axis.md` §11 の measure と接続）。

## 参照
- 設計: `docs/DESIGN_bibliographic_axis.md`
- ゲート: `phases/gate_egov_anchors.py`（authority/extraction/canonical/review の分解）
- カード生成: `phases/assemble_term_card.py`
