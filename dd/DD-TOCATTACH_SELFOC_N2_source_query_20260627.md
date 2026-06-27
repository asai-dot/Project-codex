# DD-TOCATTACH ← N-2 source registration query: bookshelf_self TOC

- 作成日: 2026-06-27
- 種別: **owner への設計クエリ**。新設計ではない。
- 親: `dd/DD-LITID_TOC_RECONCILIATION_20260623.md` N-2 / 監査 PASS_WITH_NOTES binding note。
- 監査拘束（不変）: source 投入なし / DB write なし / canonical projection なし（HOLD）。

---

## 背景

`dd/DD-LITID_TOC_RECONCILIATION_20260623.md` N-2 で確認:

- **self-scan TOC**（Box `app/data/toc/`、folder 370441454337）は `toc_nodes` **未投入**。
- `toc_nodes` 現在の bencom corpus = 3,802冊 / 552,544ノード（source='unknown' 暫定）。
- 既存 DD-TOCADOPT v0.1 の source リスト: `manual / ndl_partinfo / publisher / toc_pdf / bengo4 / legallib`。
- **`bookshelf_self`（または `self_scan`）は既存 source リストに含まれない**。

→ RECONCILIATION 監査（result_file_id: 2303315073194）は明言:
> "新規source registration addendumを起票する"（既存registry に存在しない場合）

---

## クエリ（owner/設計確認）

1. **Q1: source class の有無**
   既存 DD-TOCATTACH/TOCADOPT のいずれかで `bookshelf_self` 相当（自炊/内製 scan scan TOC）を
   source class として計画済みか。
   - YES → 既存 source adapter / landing packet に合流。新規 DD 不要。
   - NO → 新規 source registration addendum を起票（→ §アクション）。

2. **Q2: provenance_origin 割当**
   self-scan TOC の `provenance_origin` を何と定義するか。
   候補: `self_scan` / `bookshelf_self_scan` / `asai_inhouse`
   - TOCATTACH v0.3 の vote 集計 (`votes_by_provenance_origin`) に影響するため owner 明示が必要。

3. **Q3: rights / access class**
   Box `app/data/toc/` = 自社管理スキャン。外部 TOC 購入・第三者配信ではないため
   rights レビュー（TOC取得状況報告 MODIFY_REQUIRED）の対象外と理解してよいか。
   - 確認目的。rights 問題ありの場合は ingest HOLD を延長。

---

## 新規 source registration に必要な先行確定項目（Q1=NO の場合）

| 項目 | 現在値 / 必要確定 |
|---|---|
| source_name | `bookshelf_self`（案） |
| provenance_origin | 要 owner 確定（Q2） |
| snapshot_id / content_hash | Box folder 370441454337 の listing hash（要計測） |
| record_count | 5,206ファイル（2026-06-22 観測） |
| toc_set_identity | `isbn_*.json` / `title_*.json`（parser 要確認） |
| parser_version | 未定（要実装） |
| reject / duplicate report | 未計測（read-only dry-run 後） |
| idempotency_key | 未定 |
| rights_class | 自社管理スキャン（要 Q3 確認） |
| ingest_gate | TOC content agreement dry-run（§4θ 較正）後 |

---

## アクション（Q1 回答待ち）

- [ ] Q1 回答受領後、既存合流 or 新規 addendum 起票を決定。
- [ ] Q2/Q3 owner 明示後、source registration draft 作成。
- [ ] self TOC JSON フォーマット（parser 設計）は dry-run 並行で調査可。
  → `artifacts/` に `selfTOC_format_sample.json`（1冊分・egress 禁止 = サンプル構造のみ）。
- [ ] 全件 ingest・canonical projection は θ 較正完了・owner 裁定後の別 gate。

---

## HOLD（不変）

- bookshelf_self TOC の `toc_nodes` 投入（production）。
- canonical projection への反映。
- DB write / embedding / API 露出。
- rights 未確認状態での大量出力・外部搬出。
