---
request_id: DDLAWREF_v0.1_20260623
topic: 法令間「接続軸」（委任チェーン・条文間参照・行政解釈レイヤ）設計の監査
gate: DDLAWREF
status: queued
result_expected_filename: DDLAWREF_v0.1_20260623_RESULT.md
target_mode: design
source_hash: sha1:9742d91be2e86addd9ad1815ed58e3bb9221fdc7
review_scope:
  - docs/dd/DD-LAWREF-001_delegation_crossref_v0.1_notes.md （本体・被監査対象。source_hash で版固定）
  - docs/status/20260623_reallane_minpo_articlepath_findings.md （実民法 real-lane 知見・§8.5 改め文真実源）
  - scripts/articlepath/ （L4 同定の地盤：3表記→正準 article_path・数値ソート・crosswalk）
  - scripts/amendparse/ （改め文→delta_kind 機械写像＝gold の公式真実源）
regression_anchors:
  - DD-LAWTIME-001 形式軸との境界（接続軸は形式 edge、評価は持ち込まない）
  - DD-LAWSUBTRANS-001 形式/実質の分離原則（委任の「限界・趣旨」評価は assertion 側へ）
  - ALO データ編成指針：alo_edges(35_link_layer) への接続軸の引き取り、append-only / 出典付き
  - 「事実を自動確定しない・unknown を根拠にしない・推測で埋めない」家風
decision_requested: PASS / PASS_WITH_NOTES / MODIFY_REQUIRED（design accept 可否。production は別ゲート）
---

# REQUEST DDLAWREF_v0.1_20260623 — 法令間「接続軸」設計の監査

## 0. 一行
法令オブジェクトに、形式軸(DD-LAWTIME)・実質軸(DD-LAWSUBTRANS)に次ぐ**第三軸＝接続軸**
（法律→政令→省令の委任チェーン／条文間参照／行政解釈レイヤ）を新設する設計ノート
`DD-LAWREF-001 v0.1`（status: draft notes）の **design accept 可否**を問う。

## 1. 背景（なぜ別軸か・一次情報で確定済み）
- 実務家の問題提起「e-Gov は政令・省令に繋がらない」を一次情報で精密化：e-Gov は政令・省令・規則の
  **全文 XML は持つ**（2015/16〜, API v2）。欠けているのは**テキストではなく「接続」**＝①委任チェーン
  ②条文間参照グラフ ③告示・通達。これは**デジタル庁が「法令ID=法令単位・条項単位IDは未整備・今後の
  課題」と公式に明言**（ANLP2024 / デジタル庁2025-06、ノート §1 に URL）。
- 委任チェーンを構造化提供する公開 OSS は**存在しない**（狙い撃ち再調査済）。

## 2. 監査してほしい設計判断
1. **第三軸の切り出し**は妥当か。接続軸を `alo_edges` の関係種（`delegates_to`/`references`/`reads_as`/
   `implements`/`authority_basis`）として持ち、いずれも**形式事実 edge**（官報/XML 由来）に限り、
   委任の限界・趣旨の**評価は DD-SUBTRANS の assertion へ**回す——この形式/実質の線引きは正しいか。
2. **OSS 戦略（ゼロイチ回避）**：参照抽出の本体を **Lawtext**、略称名寄せ等を部品流用、委任 typing と
   限界評価のみ自前。なお当初「`analysis_law_reference` が参照抽出器」としたのを **src 精読で訂正**
   （実体は略称辞書ビルダー）。この look-before-adopt の修正と最終配置は妥当か。
3. **改め文を delta_kind の公式真実源**とし、text-diff(lawdelta) を代替に降格（findings §8.5,
   `scripts/amendparse` 実装）。gold は**改め文/新旧対照表から機械生成・人手は spot 監査のみ**。この
   真実源の優先順位は妥当か。
4. **同定の地盤(L4)**：3表記（e-Gov Num / house / 漢数字）を単一正準 article_path に集約し、版間
   crosswalk は**確度付き assertion**として持つ（実データが誤 join 740→774 を炙り出した）。
   版間同一性を事実断定しない設計は妥当か。

## 3. 既知の不確実点（ノート §7 に明示済・隠していない）
- e-Gov API v2 OAS 全文・OASIS 逐語定義の一部は環境 403 で未取得。
- `analysis_law_reference` の機能は Cargo 依存＋src 精読で確定（略称辞書）、README は無い。
- デジタル庁ハッカソン作品の repo/作者は未特定。`jstatutree` 実在未確認。
- 改め文パーサ v0.1 は合成改め文でのみ検証（実改正の改め文は e-Gov allowlist 待ち）。

## 4. 求める判定
- `target_mode: design` の accept 可否（PASS / PASS_WITH_NOTES / MODIFY_REQUIRED）。
- production（alo_edges DDL・gate・実改め文での gold 較正）は **別ゲート**で、本 REQUEST の対象外。
- blocking note があれば、§2 の 4 判断のどれに対するものかを明示願いたい。

> 投函手順: 本ファイルを Box の `gpt_ometsuke/to_gpt/` 直下に置けば active REQUEST になる。
> `python3 tools/gpt_audit/alo_gpt_audit.py lint` で T2 キー検証可。RESULT は
> `from_gpt/DDLAWREF_v0.1_20260623_RESULT.md`。
