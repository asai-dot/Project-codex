# LIT_SOURCE_GAP_20260618 — 文献コーパス ソースギャップ現況固定

```yaml
doc_id: LIT-SOURCE-GAP-20260618
status: source_gap_record (現況固定 / 投入指示ではない)
created_at: 2026-06-18 JST
updated_at: 2026-06-18 JST (rev1: B2.2 の弁コムTOC差異を出所特定し『解決済み』に更新)
author: Claude (claude.ai head / 浅井さん指示) — WO-BIBREC-FPDRYRUN-RECFIX-20260618 タスクB2/B3
gate: READ_ONLY_STRICT (本記録は SELECT 実測 + Box新規作成のみ。DB mutation 0 / mint 0)
parent:
  - 02_LIT_PHASE0_IDENTITY_DRYRUN_20260617.md (Box 2291271231830, rev3)
  - 法律情報コーパス データインベントリ台帳 v1.1 (Box 2276950720705)
supabase_project: nixfjmwxmgugiiuqfuym  # asai-dot's Project
```

> **本ファイルの性格**: 4ソース設計（DATA_INVENTORY 台帳基準）と、Supabase に実投入されている2ソースの**ギャップを現況として固定する記録**。
> **投入の指示ではない**。lionbolt / legal-library の本投入・Box配置・mint は全て **owner ratify 待ちの HOLD**（WO §6 非対象）。

---

## B2.1 4ソース設計 vs 実投入（bib_records 2ソース）ギャップ表

| ソース | 設計上の役割 | 件数(設計/台帳) | 詳細TOC | Box配置 | Supabase投入 | 状態 |
|---|---|---:|---:|---|---|---|
| **asai-bookshelf**（実蔵書） | 事務所実蔵書（books.json系） | 6,524 | — | — | **投入済**（bib_records source=asai-bookshelf 6,524 / ISBN 5,397 / NDL enrich 5,002） | ✅ 稼働 |
| **bencom-library**（弁コムカタログ） | 弁護士コム書籍カタログ | 台帳 4,490 / DB投入 **3,802** | 台帳 709,029 / DB **552,544** | — | **部分投入**（bib_records source=bencom-library 3,802 / candidates 3,802。台帳 4,490 冊中 688 冊未ロード） | ⚠ 部分 |
| **lionbolt**（法律書カタログ） | 商用法律書カタログ | 22,844（TOC 4,433書 / 264,555項目） | 264,555（設計値） | **配置済** (LIONBOLT_法律書カタログ_20260610, folder 388659455439) | **未投入** | ⛔ HOLD |
| **legal-library** | 法律ライブラリ | 4,051（TOCノード 662,717） | 662,717（設計値） | **未配置**（ローカル `~/alo-ai/work/legallib_dl/` のみ） | **未投入** | ⛔ HOLD |

**実測の裏付け（2026-06-18, SET TRANSACTION READ ONLY）**:
- `biblio.bib_records.source` の distinct は **2値のみ** = `asai-bookshelf` / `bencom-library`。lionbolt / legal-library は source 列に存在しない。
- `raw` 走査: `lionbolt` 痕跡 **0件**。`raw ILIKE '%legal%lib%'` は **86件**で、**全86件が source=bencom-library 由来の別文脈ノイズ**（legal-library ソースではない）。
- → 4ソース設計のうち **2ソース（lionbolt / legal-library）は Supabase 完全未投入**。lionbolt は Box 配置済だが DB 未投入、legal-library は Box 未配置かつ DB 未投入。
- **弁コムも全数ではなく部分投入**: 台帳の弁コムカタログは 4,490 冊だが、DB の `bookdx.candidates` / `biblio.books` は **3,802 冊**（688 冊未ロード）。→ B2.2 参照。

## B2.2 詳細TOCノードの会計（fact#5 — 出所特定・解決済み）

設計（WO §1 fact#5）は「詳細TOC総ノード ≒ **1,636,301**（lionbolt 264,555 ＋ 弁コム 709,029 ＋ legal-library 662,717）」とする。本記録での DB 内実測との対照:

| ソース | 設計上のTOCノード（出所） | DB内ロード済み（実測） | 差異 |
|---|---:|---:|---|
| lionbolt | 264,555（台帳§2 `_separated/lionbolt/with_toc.jsonl`, 4,433書） | **0**（未投入） | 未投入につき DB 内不在 |
| 弁コム(bencom) | **709,029**（台帳§2 `_separated/bengo4/with_toc.jsonl`, **4,490書**） | **552,544**（`bib_toc` = `toc_nodes` = `candidates.total_toc` 合計, **3,802書**） | **−156,485 = 未ロード 688書ぶん** |
| legal-library | 662,717（台帳§2, 4,051書） | **0**（未配置・未投入） | 未投入につき DB 内不在 |
| **合計** | **1,636,301**（= 全カタログの設計目標値） | **552,544**（弁コム部分集合のみ） | 1,083,757 は未投入(lionbolt/legallib) + 弁コム688書未ロード |

> ✅ **解決（2026-06-18, owner と確認）**: fact#5 の 709,029 と DB 実測 552,544 の差は **データ破損やロードバグではなく、「ソース全体 vs ロード済み部分集合」の区別**。
>
> **出所特定**: 709,029 は **データインベントリ台帳 v1.1 §2** の行「弁コム | toc | **4,490(709,029項目)** | `_separated/bengo4/with_toc.jsonl`」＝**弁コム全カタログ 4,490 冊ぶんのソース側TOCノード数**。fact#5 の lionbolt 264,555・legal-library 662,717 も同様に台帳§2の各 `_separated/*` 全カタログ件数であり、いずれも**ソース（取り込み前）の設計目標値**。
>
> **DB側の実体（自己整合を確認）**:
> - `bib_toc` 552,544 は **100% 弁コム由来**（`bib_records.source` で内訳: bencom 552,544 / asai 0 / 孤児 0）。`toc_nodes` 552,544 / 3,802 書、`candidates.total_toc` 合計も **ぴったり 552,544**。DB 内のどこにも 709,029 は存在しない。
> - `bookdx.load_run` = `in_db_sql/0.1`（2026-06-11, Box 無しの in-DB projection）。candidates(total_toc 既に 552,544)→ bib_toc/toc_nodes へ射影しただけ。709,029 はこのパイプラインに登場しない。
>
> **差 156,485 ノードの内訳**: 弁コムカタログ **4,490 冊**のうち DB に candidate 化されたのは **3,802 冊**で、**688 冊が未ロード**。未ロード 688 冊が 156,485 ノード（**平均 227.4 ノード/冊**）を持つ。ロード済み 3,802 冊は平均 145.3 ノード/冊（= DB 実測 avg と一致）、台帳全体 4,490 冊は平均 157.9 ノード/冊。
> → **間引かれた 688 冊はむしろ TOC が多い本**。よって「TOC が薄い本を落とした」ではない。
>
> **残る open item（DB では確定不能）**: 688 冊が candidate 化されなかった**選別理由**は本DBからは確定できない（落ちた 688 冊は DB に存在せず、判定は ソース jsonl `_separated/bengo4/with_toc.jsonl` ＋ candidate 生成ローダ＝Mac `~/alo-ai/work/bengo4_dl/` 側にある）。DB 側で言えるのは「ロード済み 3,802 冊/552,544 ノードで自己整合、未ロード 688 冊は TOC-rich」まで。理由の特定はソース/ローダ確認に委ねる。
>
> 1,636,301（約164万ノード）の総コーパス像は **2ソース未投入＋弁コム688書未ロードを前提とした設計目標値**であって、現時点の DB 実体（弁コム 3,802書 / 552,544ノードのみ）ではない。

## B3 bib_records 行数の決着（「行数過剰」memo の原因確定）

**結論: `bib_records` 10,326 行は異常ではない。**

```
10,326 = 6,524 (asai-bookshelf / 実蔵書) + 3,802 (bencom-library / 弁コムカタログ)
       = 2ソース縦積みの当然の和
```

- 「`bib_records` 行数過剰（10,326 > 6,528）＝異常」という認識は **誤り**。
  - 6,528 は **asai-bookshelf 単独（≒ books.json）** の数であって、`bib_records` 全体の上限ではない。
  - `bib_records` は asai-bookshelf と bencom-library の **2ソースを縦積みするテーブル**なので、6,524 + 3,802 = 10,326 が正しい母数。上限超えではない。
- memo「行数過剰の重複調査未着手」は **ここで原因確定し決着**する。原因＝2ソース縦積みの誤読（単一ソース上限と比較していた）。
- 残る実作業は「行数過剰の是正」ではなく、**asai × bencom の dedup（= DD-LITID identity 解決）**に吸収される:
  - asai 内 ISBN 重複は **ゼロ**（distinct_isbn 5,397 = with_isbn 5,397）。
  - ダブりは **asai × bencom の title+publisher 重なり**に局在（弁コム→holding 1,761 / 無ISBN holding→弁コム 784, fact#6）。
  - read-only dry-run（同WO タスクA / `a1`–`a3`）の見積り: fan-out 4,370行のうち二重ロード候補 1,696グループ（うち跨ぎ 1,639）、版違い候補 335グループ。identity_status 見積り = resolved ≈ 8,637 / candidate(merge) ≈ 777 / split_required 20グループ(127行)。distinct full-fp 9,497（推定ユニーク item 上限）、exact 重複行 829 が圧縮可能。
  - これらの dedup/収斂は biblio_item mint を伴うため **owner ratify 待ちの HOLD**。本記録では 1 件も mint しない。

> 補足（B2.2 と整合）: 弁コム側の「母数」は DB 上 3,802 冊（未ロード 688 冊を除く）。asai × bencom dedup の見積り（A1–A3）はこの 3,802 冊ベースであり、688 冊が将来ロードされれば再見積りが要る。

---

## 投入HOLD（WO §6 非対象・owner ratify 判断待ち）

以下は本記録の対象外。現況固定のみで、実行指示ではない:
- lionbolt / legal-library の本投入（DDL / backfill）
- legal-library の Box 配置（未配置の解消）
- 弁コム未ロード 688 冊の追加投入
- biblio_item の正準 mint（O1案B `alo:lit:item:{UUIDv7}`）
- 詳細TOC（設計総計約164万ノード）の実務活用（逆引き索引／網羅性チェッカー／合成カリキュラム／思考地図）の実装

## 参照・再現性

- 実測は全て `SET TRANSACTION READ ONLY;` 下の SELECT（`current_setting('transaction_read_only')='on'` 確認）。DB mutation 0 / mint 0 / DDL 0。
- 成果物（Box `_inventory` 388953248767 ミラー / リポジトリ `artifacts/fp_dryrun_20260618/`）:
  `a1_fanout_breakdown.json` / `a2_collision_compressed.json` / `a3_identity_status_estimate.json` / `SESSION_LOG_readonly_proof.json` / `SHA256SUMS.txt`。
- 関連: Phase0 記録 rev3（Box 2291271231830）, データインベントリ台帳 v1.1（Box 2276950720705 §2）。
