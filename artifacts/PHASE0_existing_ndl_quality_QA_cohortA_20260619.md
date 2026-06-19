# Phase 0 — 既存NDL 版粒度QA（read-only）cohort-A self_scan

- generated_at_jst: 2026-06-19
- source: Supabase `nixfjmwxmgugiiuqfuym` / `biblio.bib_records`（**SELECT のみ・DB無変更**）
- plan: ISBN_NDL_DRYRUN_PLAN v0.3 §9-Phase0 / §8（既存NDL品質QA）
- cohort: **cohort-A_self_scan** = `source='asai-bookshelf'` かつ ISBN・ndl_bib_id 両方あり = **4,976件**
- 監査根拠: snapshot RESULT（VALID_WITH_NOTES, must_fix「既存NDL品質QA」「present≠verified」）、
  dryrun v0.2 RESULT（candidate≠confirmed）
- 重要: 本QAは **read-only**。`ndl_bib_id` は全て **`preexisting_candidate`（= present, verified ではない）**。
  promote/confirm/DDL/書込なし。

---

## 1. in-DB 整合性シグナル（NDL外部照合なしで測れる範囲）

| シグナル | 結果 | 解釈 |
|---|---|---|
| 同一 `ndl_bib_id` → 複数の異なるISBN | **0** | 別ISBNが同一bibidに潰れている形跡なし（版潰しの明示痕跡なし） |
| 同一 ISBN → 複数の異なる `ndl_bib_id` | **0** | ISBN↔NDL は **厳密に 1:1**。stored multi_bibid なし |
| `edition` 保有 | 376 / 4,976（**7.6%**） | 版を区別する内部フィールドがほぼ無い |
| `volume` 保有 | **0** | 巻次フィールド未投入 |
| ISBN が13桁(978/979)形式でない | **0** | ISBN形式は健全 |
| `ndl_bib_id` 数値のみ | 4,976（100%） | 形式は一貫（桁は2種：9桁系と12桁ゼロ詰め系） |

### 1-bis. 整合性の限界（coverage ≠ correctness）

ISBN↔NDL が 1:1 で衝突ゼロは **consistency** が良いことを示すだけで、**版粒度の正しさ(correctness) は証明しない**。
`edition` が7.6%・`volume` が0% である以上、「1つのISBNが実際には複数刷/版を含む」場合に
**DB内部からは版の取り違えを検出できない**。＝監査指摘どおり、正誤判定には **NDL/奥付の外部照合が必須**（§3）。

## 2. ISBN provenance 異常（identity 取り違えの芽）

`bib_id`（`alo:book:isbn:<13桁>` 形式 4,427件）に埋め込まれたISBNと `isbn` 列が食い違うもの **6件**。
identity キーと書誌ISBNの不一致＝dedup/同定のハザード。要 provenance 確認（再OCR/原本照合）。

| bib_id 埋め込み | isbn列 | ndl_bib_id | title |
|---|---|---|---|
| 9784785717174 | 9784785717179 | 000010663263 | 新下請法マニュアル |
| 9784896285847 | 9784896285840 | 000010679439 | ここがポイント!改正特商法・割販法 |
| 9784788203995 | 9784788203990 | 000003641403 | 民事意思能力と裁判判断の基準 |
| 9784474019467 | 9784474019461 | 000008047125 | 新会社法対策セミナー DVD |
| 9784474018427 | 9784474018426 | 000007442751 | 法律事務所事務職員マニュアル |
| 9784887134616 | 9784887134614 | 000003691840 | 資料で読み解く国際法 |

（注: いずれも末尾チェックデジット1桁違い。どちらが正かは外部照合で確定。）

## 3. 層化QAサンプル（外部照合用・未検証）

- 成果物: `artifacts/qa_sample_cohortA_20260619.jsonl`（**91行**、md5順で再現可能）。
- 各行スキーマ（v0.3 §5）: `review_sample_bucket, route_cohort, bib_id, isbn13, isbn_checkdigit_ok,
  ndl_bib_id_present, ndl_bib_id_verified(=null), link_status(=preexisting_candidate),
  title, publisher, edition, volume, pub_year, ndc, evidence_family, write_authorization(=false)`。
- バケット構成: random 50 / edition_present 20 / generic_short_title 10 / old_pubyear_suspect 10 /
  **publisher_variant 1**（`株式会社` 表記が cohort-A に少なく、目標10に未達 → §5 既知の穴）。
- サンプル内チェックデジット: 91件すべて妥当。bib_id↔isbn不一致は1件（資料で読み解く国際法、§2に含む）。
- **検証フィールド `ndl_bib_id_verified` は全て null。** 次工程（NDL/奥付照合）で埋める。

### 観測された難所の実例（サンプルより）

- 「民事判例」が **別ISBN・別bibid・別年**で複数存在 → 年刊/シリーズ（`looseleaf_or_supplement_series` 相当）。
- `edition` 値の表記ゆれ：`第2版` / `第1刷` / `改訂版` / `三訂版` / `10訂版` / `2019/08/25` / `2019年10月` 等が混在
  → 版表記の正規化が後段で必要（版 vs 刷の区別含む）。

## 4. この Phase 0 が答えたこと / まだ答えていないこと

- ✅ 答えた: cohort-A の ISBN↔NDL は構造的に 1:1・衝突なし。ISBN形式は健全。版識別の内部フィールドは実質欠落。
  identity provenance の異常は 6件に限局。
- ⛔ まだ: 「`ndl_bib_id` が指す bibid が実際に手元の版と一致するか」。これは **外部照合（NDL Search / 奥付OCR）**
  でしか判定できない。本Phaseは候補と検証対象の固定まで。

## 5. 次工程（すべて read-only、HOLD据置）

1. サンプル91件を **NDL/奥付で外部照合** → `ndl_bib_id_verified` を埋め、version-granularity 精度を算出
   （NDLアクセス可能な runner = Mac/owner 側、または resolver キャッシュ経由）。
2. publisher_variant バケットを別条件で補充し10件化（§3の穴）。
3. Phase 1: cohort-A の **ISBN有NDL無 421件** の NDL 照会 dry-run。
4. Phase 2: **ISBN無NDL無 1,101件** の内訳分類。
5. provenance mismatch 6件の原本確認（どちらのISBNが正か）。

## 6. no-write 保証

本Phaseは `biblio` / `bookdx` / canonical / Box source を一切変更していない（SELECTのみ）。
出力は `artifacts/` への append-only 2点（本レポート ＋ qa_sample JSONL）のみ。
promote / confirm / backfill / DDL は HOLD。
