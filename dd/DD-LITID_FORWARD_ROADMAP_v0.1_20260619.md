# DD-LITID 書籍同定 フォワード・ロードマップ v0.1

- 作成日: 2026-06-19
- 位置づけ: これまでの **実測（DB snapshot）＋ Phase 0 QA ＋ 2監査 RESULT** を踏まえた、4ルート書籍同定の今後方針。
- 上位設計: DD-LITID-PLAN v0.1（DESIGN_PASS_WITH_NOTES）/ DD-LITID-001 v0.2 / DD-LITID-FP / INGEST_SPEC v0.2。
- ゲート原則（不変）: 可逆=安価は先行、不可逆=高価（promote/canonical/DDL/serving）は shadow 実証後。
  **本ロードマップは計画。実装/DDL/backfill/promote は引き続き HOLD。**

## 0. 確定した現実（根拠つき）

| 事実 | 根拠 |
|---|---|
| bib_records に実在するのは **self/own(asai-bookshelf 6,524) と bencom(3,802) のみ**。LION BOLT/legallib 未投入 | DB snapshot 20260619 |
| self/own は ISBN↔NDL が **厳密1:1・衝突0**、だが `edition`7.6%/`volume`0% で **版正誤は内部判定不能** | Phase 0 QA |
| 弁コム突合は **既存1,737件**（high 962 / medium 775=単証拠寄り） | snapshot |
| ISBN provenance 不一致 **6件**（bib_id↔isbn） | Phase 0 QA |
| **NDL外部照合は本実行環境から不可**（outbound不可）。要 NDLアクセス可能 runner | Phase 0 実行時に判明 |

監査からの拘束: **candidate≠confirmed / coverage≠correctness / cohort外挿禁止 / medium775=existing_unconfirmed / 全promote HOLD**。

## 1. クリティカルパスの真因

版同定の品質は **NDL/奥付の外部照合**に律速される（内部フィールドが空のため）。
→ 最初に解くべきは設計ではなく **「NDLにアクセスできる実行環境(runner)の確定」**。ここが開かないと
cohort-A の version-granularity 精度が測れず、実装ゲートの閾値も埋まらない。**§6 が owner 決定事項。**

## 2. ワークストリーム（並走可能な単位）

### WS-A 自所(cohort-A) 版同定 — 主戦場
- A0 ✅ Phase 0 in-DB QA + 層化サンプル91（完了）
- A1 ⛳ サンプル91を **NDL/奥付で外部照合** → `ndl_bib_id_verified` 充填 → **版粒度精度**を算出（要 runner, §6）
- A2 穴埋め: **ISBN有NDL無 421** の NDL照会 / **ISBN無NDL無 1,101** の内訳分類・難所queue化
- A3 **edition 正規化**（版 vs 刷, 改訂/n訂, 日付表記, 年刊/シリーズ）→ DD-LITID-FP に反映
- A4 provenance 6件の原本確認（正ISBN確定）

### WS-B 弁コム no-ISBN shadow（既存1,737の遡及検証）
- B1 **medium 775 を existing_unconfirmed として遡及検証**（title_norm+publisher_norm + 第2独立証拠=TOC/fingerprint）
- B2 high 962 の sample precision 抜き取り
- 全件 candidate 据置・promote 禁止

### WS-C 未投入ルートの取り込み
- C1 **LION BOLT** raw intake → field-profile/manifest ゲート → cohort-A' 合流
- C2 **legallib** フル → cohort-B
- cohort別に再計測、**cohort-A閾値を継承しない**

### WS-D NDLハブ + マッチング基盤（DD-LITID-PLAN 中核・設計のみ先行）
- waterfall / blocking / 独立性(origin_family, same_origin_collapse_key) を A1/B1 の実測で較正
- shadow 実証前に promote しない

### WS-E identity/edition モデル promote — **HOLD**
- shadow 精度が §5 閾値を満たして初めてゲート。DDL/canonical/count/serving はここ。

## 3. 依存と順序

```
§6 runner決定 ──▶ WS-A1(版粒度精度) ─┐
                                      ├─▶ WS-D較正 ─▶ 閾値充足 ─▶ WS-E(promote, 要監査)
WS-B1(775遡及) ───────────────────────┘
WS-A2/A3/A4 (runner非依存の範囲は先行可)
WS-C1/C2 (raw着地待ち。着地後 cohort別計測)
```
- **runner非依存で今すぐ進む分**: A2の対象リスト抽出（421/1,101の属性集計）, A3のedition表記の棚卸し, B のサンプル設計, A4の6件特定（済）。
- **runner依存**: A1の実照合, A2のNDL実照会。

## 4. 直近スプリント（read-only のみ・HOLD据置）

1. §6 runner を owner 決定（最優先・ブロッカー）。
2. A2前段: 421件リスト＋1,101件の属性分布（title/publisher/author/year/scan有無）を read-only 集計。
3. A3前段: cohort-A の `edition` 全値を棚卸しし、版/刷/改訂/シリーズの正規化ルール草案。
4. B 設計: 775 medium の遡及検証サンプル設計（第2独立証拠の取得元定義）。

## 5. 実装ゲート閾値（種類を先に固定・値は実測較正）

version-granularity 精度 / candidate_single 妥当率 / multi-bibid 曖昧率 / no_hit(valid ISBN)率 /
low-confidence ISBN率 / metadata_conflict率 / **false-confirmation 率** / medium775 の precision /
manual-review yield。**これらが閾値を満たすまで WS-E は開けない。**

## 6. owner 決定事項（ブロッカー）

**NDL外部照合の runner をどうするか。** 候補:
- (a) Mac/owner ローカルで NDL Search API を叩く（既存 resolver/キャッシュ resue）。
- (b) ネット許可された実行環境を別途用意。
- (c) 既存 `colophon_ndl_results.json` 等キャッシュの範囲だけで先行し、不足は明示限定。

推奨: **(a) または (c) で A1 を先行**。(b) は範囲が広がるなら別途。

## 7. スコープ境界（再確認）

- 記事/論文層（authority.publication, D1-Law 文献/bunken）は **DD-PERIODICAL 別ゲート**。本ロードマップ外（参照リンクのみ）。
- bengo4 no-ISBN の新規生成は本線外。ただし**既存1,737の遡及検証(WS-B)は本線**。
- 不可逆処理（promote/canonical/DDL/serving/embedding/外部公開）は全 WS で HOLD。

## 8. 未確定・リスク

- runner 未決だと A1 が進まず全体が律速（§6）。
- edition 表記の多様性（A3）が想定以上なら正規化コスト増。
- LION BOLT/legallib の実メタ形状未確認（C着地まで cohort-B の前提は仮）。
- 独立性判定が origin だけで足りるか（content_hash/source_url 併用要否）。
