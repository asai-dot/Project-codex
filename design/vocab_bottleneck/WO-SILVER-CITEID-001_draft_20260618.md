# WO-SILVER-CITEID-001（草案）: 掲載位置 → 判例ID の silver 解決

> doc_kind: WORK ORDER 草案 / **設計のみ・実行承認ではない** / status: DRAFT（owner GO 未）
> author: Claude / date: 2026-06-18 / owner: 浅井
> 親: DD-DATAARCH-001 v0.2（build側②クレンジング/silver）/ DD-LRINDEX-001 v0.3（claim_support 二層）/ relationship_layer_status_20260617
> 優先度: **silver 順序 #1（最優先）** — 関係層を厚くする正しい順序の第1ステップ
> gate: 既存エッジ/索引の集計・突合のみ（read-only 派生）。**本番 write・canonical mint・外部取得は HOLD**。

## 0. 一行
lic 解説引用（tier B・判例ID未解決）の「掲載位置文字列」を、`hanrei_published_in` 索引（76,643）に照合して
**judgment-level の解説→判例エッジ**へ昇格する silver パイプラインを設計・dry-run する。

## 1. 入力（実在・measured）
- `lic cites_judgment_via_journal` 23,914（ユニーク掲載位置 12,169）/ `cites_judgment_by_date` 5,571。
- `hanrei_published_in`（判例→号: 誌＋号＋頁）索引 76,643。
- 判例 canonical 192,998（court+date+docket）。
- 掲載位置文字列の例: `journal_article:労働判例:1060:5`（誌名:号:頁）。

## 2. 出力（candidate のみ・本番 write なし）
- `silver_cite_resolution_candidates.jsonl`: 1 行 = 1 引用解決候補。
  必須フィールド: `lic_edge_id` / `source_locator_raw` / `normalized_journal` / `issue` / `page` /
  `resolved_hanrei_id` / `match_method`（issue_page_exact / issue_page_fallback / court_date）/
  `confidence` / `decision_status`(strong|review) / `evidence` / `honest_empty`(該当時: db_unbuilt|locator_unresolvable)。
- `silver_cite_resolution_report.md`: 歩留まり・未解決理由内訳・誌名正規化前後の比較。

## 3. 手順（dry-run / read-only）
1. **誌名正規化辞書**を起こす（観測された誌名表記ゆれ → canonical 誌名）。略称・旧称・全半角・スペースを吸収。
2. 掲載位置 → (誌, 号, 頁) パース。パース不能は `honest_empty=locator_unresolvable` で隔離（捨てない）。
3. `hanrei_published_in` 索引へ多段照合:
   - L1 issue+page exact（最強・`match_method=issue_page_exact`）
   - L2 誌名正規化後の号レベル fallback（頁ロス時・`issue_page_fallback`・confidence 減）
   - L3 court+date 経路（via_date 5,571 用・`court_date`）
4. 1 掲載位置 → 複数判例候補（同号同頁に複数判例）は**畳まず**全候補を `review` として保持（P4 信号保存）。
5. 歩留まり集計。基準値 = 概算 24%（5,849）。**誌名正規化＋号 fallback で向上を測る**のが本 WO の主眼。

## 4. 受入基準（dry-run 完了条件）
- exact / fallback / court_date 別の解決件数と confidence 分布が出ている。
- strong（issue_page_exact 由来）と review（fallback/court_date 由来）が混ざらず二層分離されている。
- 未解決の理由内訳（誌名正規化不能 / 索引欠落 / 頁不一致）が定量化されている。
- 同号同頁複数判例の曖昧ケースが review として保持され、自動確定されていない。

## 5. 本 WO で決めない / やらない（別ゲート）
- 解決候補の**本番 write・accepted 化**（owner review 後の別パケット）。
- treatment（肯定/否定/区別）の付与 → DD-CITE-TREATMENT（未起票）。
- 外部からの誌・判例の追加取得（D1 再取得は WO-D1HANREI-REFETCH-001）。

## 6. ゲート
- read-only（既存 jsonl/索引の集計・突合のみ）。candidate は staging 出力のみ・canonical graph へ書かない。
- low confidence は review queue。strong/reviewed のみが将来 claim_support 候補（DD-LRINDEX G4 / v0.6.1 緩和版に従う）。
