# ISBN→NDL read-only ドライラン計画 v0.3

- 作成日: 2026-06-19（v0.2 を改訂・一本化）
- 改訂理由: 2監査 RESULT を畳み込み。
  - `20260619_ISBN_NDL_DRYRUN_PLAN_v0.2_RESULT`（**DESIGN_PASS_WITH_NOTES / read-only は出力スキーマ3点を埋めれば GO**）
  - `20260619_DB-OBSERVED-SNAPSHOT_litid_RESULT`（**VALID_WITH_NOTES / 前提更新可・既存NDL品質QA等を追加**）
- 対象: DD-LITID-PLAN 4ルート版同定のうち **ISBN持ちルート**（self_scan / LION BOLT / legallib）
- ゲート: read-only dry-run のみ GO（§5/§10 の出力要件充足後）。**実装/DB書込/backfill/promote/serving/embedding は HOLD。**
- 前提契約: INGEST_SPEC v0.2, DD-LITID-001 v0.2（fingerprints/2独立証拠）
- 実測前提: `artifacts/DB_OBSERVED_SNAPSHOT_litid_20260619.md`（bib_records 投入済は self/own のみ。LION/legallib 未投入）

## 0. v0.2 からの変更点（2監査 notes の反映）

| 出典 | note | v0.3 反映 |
|---|---|---|
| v0.2監査 must_fix-1 | 全出力行に必須列 | §5：`link_status`/`route_cohort`/`evidence_family`/`write_authorization=false` を必須化 |
| v0.2監査 must_fix-2 | candidate と confirmed の分離 | §6：サマリで分離。confirmed は独立証拠充足を実行するまで **0** |
| v0.2監査 must_fix-3 | cohort-A 率は self_scan 限定 | §5/§6：レポートテンプレに外挿不可を明記 |
| v0.2監査 should_fix | preexisting vs new / evidence_origin enum / collapse key / review bucket | §5, §3-bis |
| snapshot must_fix-1 | 既存NDL有4,976の版粒度QA | §9-Phase0 ＋ §8 |
| snapshot must_fix-2 | present と verified の分離 | §3：`ndl_bib_id_present` / `ndl_bib_id_verified` |
| snapshot must_fix-3 | 1,101件の内訳推定 | §9-Phase2 ＋ §6 |
| snapshot must_fix-4 | medium 775 は existing_unconfirmed | §4-bis |
| snapshot must_fix-5 | 自所分布を後合流へ外挿しない | §1-bis（v0.2 既出を強化） |

## 1. スコープと非スコープ

- IN: ISBN正規化 → NDL bibid 解決 → **候補**分類 → 例外レーン仕分け → QAサンプル抽出 → 既存NDL品質QA。**全て read-only**。
- OUT（HOLD据置）: edition/work/canonical 書込, promote, DDL, backfill, serving, embedding, 外部公開。
- OUT（別レーン）: bengo4 no-ISBN（`bengo4_noisbn_shadow`）。ただし**既存リンク775件の遡及検証**は §4-bis で本計画の read-only QA 対象に含む。
- OUT（別ゲート）: 記事/論文層（authority.publication）。DD-PERIODICAL へ参照リンクのみ残す。

### 1-bis. route cohort（外挿禁止）

| cohort | ルート | 現況（実測） | 扱い |
|---|---|---|---|
| **cohort-A** | self_scan（asai-bookshelf） | bib_records 投入済 6,524 | 先行ドライラン（**self_scan 限定の較正**） |
| cohort-A' | LION BOLT | **未投入** | 着地後に新規 baseline profile を作る（cohort-A 閾値を継承しない） |
| **cohort-B** | legallib | **未着** | 着地後に別分布として再測定、合算は再計算 |

- 各行に `route_cohort` 必須。**cohort-A の率/閾値を LION/legallib へ外挿しない**（設計文＋出力レポート両方に明記）。

## 2. 入力

- field-profile ゲート通過済みの raw。manifest_gate PASS が前提。
- ISBN は `normalize_isbn` で正規化（`-`/空白除去 → 13化）。
- ISBN欠落は対象外 → §6 で no-ISBN 別計上。
- 各行に raw input row id と route-local id を保持。

## 3. NDL 解決手順（waterfall, read-only）

各 ISBN について:
1. **ISBN完全一致**で NDL bibid を引く（既存 resolver/キャッシュを読むだけ）。
2. ヒット件数で分岐:
   - `candidate_single_bibid`: bibid 1件 → **候補 evidence のみ**（版確定でない）。
   - `multi_bibid`: 複数 bibid → 例外レーン。
   - `no_hit`: 0件 → §4 のバケット。
3. 候補が出ても **§3-bis の2独立証拠を満たすまで confirm しない**。confirmed は実際に確認を実行した場合のみ。

**present と verified の分離（snapshot must_fix-2）:**
- `ndl_bib_id_present` = DB に既に値がある（cohort-A の4,976件等）。
- `ndl_bib_id_verified` = 本ドライランで版粒度QA を通過した。
- 既存値は `preexisting_candidate` として取り込む。**present を verified と読み替えない。**

### 3-bis. 「2独立証拠」の定義

- 独立 = **異なるソース系（evidence_family / origin_family）**。
  enum: `NDL` / `publisher` / `colophon_ocr` / `legallib_provider` / `LION_catalog` / `self_scan_metadata` / `manual_review`。
- **同一 NDL レコード内の複数フィールド（出版年＋版表示等）は1証拠。**
- legallib/LION/出版社由来メタは別ルートでも同origin なら独立でない → `same_origin_collapse_key` で1証拠に畳む。
- 後段 confirm では content_hash / source_url / capture_method の併用を追加（取得可能な場合）。

## 4. 例外レーン

| レーン | 条件 |
|---|---|
| `multi_bibid` | 1 ISBN → 複数 bibid |
| `no_hit_after_valid_isbn` | 妥当ISBNでヒット0（NDL未収載の本命） |
| `no_hit_low_confidence_isbn` | 低信頼ISBNでヒット0（再OCR候補） |
| `isbn_source_untrusted` | ISBN出所不信 |
| `looseleaf_or_supplement_series` | 加除式・追録・シリーズ |
| `isbn_invalid` | チェックサム不正 |
| `isbn_reused_or_suspicious` | ISBN再利用/重複疑い |
| `metadata_conflict` | ISBN一致だが title/publisher/year 著しく不一致 |

### 4-bis. 既存リンクの遡及検証（snapshot must_fix-4）

- `bookdx.holding_bencom_link` の medium 775件は **`existing_unconfirmed`** として扱う。
- これらは「これから作る」ものではなく**既存の単証拠寄りリンク**。**confirmed 化禁止**、promotion HOLD。
- confirm 条件 = `title_norm + publisher_norm + 独立証拠（別 evidence_family）`。read-only では sample precision を測るのみ。

## 5. 出力（read-only アーティファクトのみ）

- `dryrun_isbn_ndl_<cohort>_<date>.jsonl`: 1行に以下を**必須**:
  `{raw_row_id, route_local_id, route_cohort, isbn13, link_status, ndl_bib_id_present, ndl_bib_id_verified, bibid(s), exception_lane, evidence_family, same_origin_collapse_key, review_sample_bucket, write_authorization=false}`。
  - `link_status` ∈ {`candidate_single_bibid`, `multi_bibid`, `no_hit_*`, `existing_unconfirmed`, `confirmed`}。
  - `preexisting_ndl_bib_id` と `new_candidate_ndl_bib_id` を区別（preload を発見と偽装しない）。
- `dryrun_isbn_ndl_summary_<date>.md`: **cohort別**。candidate/multi/no_hit を **confirmed と分離**。
  **confirmed は独立証拠確認を実行するまで 0。** 冒頭に「cohort-A 率は self_scan 限定・外挿不可」を明記。
- `qa_sample_<cohort>_<date>.jsonl`: §8 のサンプル設計。
- いずれも artifacts/ への append-only のみ。**canonical へは書かない。**

## 6. 計測指標

cohort別に: ISBN被覆率 / `candidate_single_bibid率` / `multi_bibid率` / `no_hit`各バケット率 / `isbn_invalid率` /
no-ISBN比率 / multi_bibid QA精度 / route別 disagreement rate /
**既存NDLの version-granularity 精度（QAサンプル）** / 1,101件の内訳分布 / 775件 medium の sample precision。

## 7. 受け入れ基準（ドライランの合否 ≠ 本実装許可）

- ✅ cohort別分布が出る。multi_bibid/no_hit/既存NDL-QA のサンプルが揃う。
- ✅ 「candidate 支配的か / 加除式・改訂で no_hit・multi が無視できない水準か」への定量回答。
- ⛔ promote/DDL/backfill の許可を含まない。

### 7-bis. 実装ゲート移行の閾値（種類のみ先に固定・値は cohort-A 較正）

valid ISBN rate / candidate_single rate / multi-bibid ambiguity rate / no_hit(valid ISBN) rate /
low-confidence ISBN rate / source-untrusted rate / metadata_conflict rate /
**false-confirmation sample rate** / manual-review yield。

## 8. QAサンプル設計

- ランダム ＋ 層化（route_cohort × {invalid ISBN, no_hit各バケット, multi_bibid, looseleaf, 高価値法律シリーズ, metadata_conflict}）。
- **既存NDL有4,976件の版粒度QA（snapshot 推奨）**:
  ```
  100件 = random50 + edition/巻次あり20 + publisher表記ゆれ10 + 汎用/短title10 + 古書/旧版疑い10
  確認項目: ISBN13完全一致 / title・publisher一致 / edition・volume・year齟齬 / 複数候補時の選択根拠
  ```
- `review_sample_bucket` で candidate_single / multi_bibid / valid-isbn-no-hit / low-confidence ISBN / metadata_conflict を網羅。

## 9. 実行フェーズ（snapshot 推奨を採用・全て read-only）

- **Phase 0**: read-only観測確定 ＋ **既存NDL有4,976件の版粒度QAサンプル**（§8）。
- **Phase 1**: cohort-A の **ISBN有NDL無 421件**の NDL 照会 dry-run（候補数分布）。
- **Phase 2**: **ISBN無NDL無 1,101件**の内訳分類（title/publisher/author/year/scan有無、古書・加除式・非売品の疑い）と難所 queue 化。
- **Phase 3**: bencom **medium 775件**の遡及 confirm sample precision（`existing_unconfirmed`、promotion HOLD）。
- **Phase 4**: LION BOLT / legallib が DB 着地後に**別分布**として再測定（cohort-A 閾値を継承しない）。
- 補助: ISBN無NDL有 26件の由来確認（過去 resolver 品質の手掛かり）/ holdings の cut・has_toc=0 が「未投入」か「真に無」かの切り分け。

## 10. runbook の no-write 保証

- canonical 化なし / count 表生成なし / promote なし / backfill なし / source(raw)改変なし / DDL なし。
- 出力は artifacts/ への append-only のみ。NDL へは read-only アクセスのみ。
- **post-run check**: DB テーブル / Box source / canonical レコードが一切変更されていないことを確認。

## 11. open questions

- legallib/LION メタが NDL/出版社由来の場合の独立性（origin + content_hash 併用で足りるか）。
- 加除式検出が title 語だけで足りるか（publisher/series heuristic 要否）。
- multi_bibid QA の実装ゲート開放に要する最小サンプルサイズ。

## 12. 次手

1. 本 v0.3 で read-only 実行（**Phase 0**）に着手可。出力スキーマ（§5）を実装ツール側に反映してから走らせる。
2. Phase 0 結果（既存NDL品質QA）を監査レーンへ → 実装ゲート判断材料に。
3. LION BOLT / legallib は着地後に cohort-A' / B として合流。
