---
request_id: 20260610_legallibjoin_v0.1_DDJOIN
topic: legallibjoin
gate: DDJOIN
version: v0.1
source_hash: sha256:8c340e6878d7ba56b60aa4931cad5655a565254982b0e59e65377a448d2fc91f
git_commit: f2752065ef188e14e8c25463d4ce58fae7bd17cb
git_branch: claude/legallib-integration-design-Jgrtf
git_pr: https://github.com/asai-dot/Project-codex/pull/5
supersedes: null
result_expected_filename: 20260610_legallibjoin_v0.1_DDJOIN_RESULT.md
status: queued
---

# GPT Pro お目付け役 監査依頼: legallib 接合ポリシー 2論点 (DDJOIN)

- gate: **DDJOIN** / topic: legallibjoin / version: v0.1 / 起票: 2026-06-10 / 番頭: web CC
- RESULT 先頭行: `DDJOIN_PASS` / `DDJOIN_PASS_WITH_NOTES` / `DDJOIN_MODIFY_REQUIRED` / `DDJOIN_FAIL` / `DDJOIN_NEED_MORE`
- requested_verdict: 下記 **F2 / F3 の方針**を確定したい。各論点に「採否＋必須修正」を。

## 趣旨（なぜ別family監査か）
legallib 詳細TOC を本番ブックJSON(canonical, `app/data/toc/isbn_*.json`) へ接合する設計
(PR #5)。実データのサンプル/全数ドライランで判明した**2つの方針論点**を、同 family Claude の
盲点回避のため GPT に裁定してほしい。実装バグ(converter のネスト未対応 / U+2028 / resolver
schema 吸収)は web 側で既に修正済。本件は**規範判断**のみ。

接合の確定ゲート (既決): **「人手/NDL/出版社/PDF目次 = 非simple/保護ソースは legallib で
絶対に上書きしない。既存が `toc_status=="simple"` のみのとき昇格上書き可」**。誤マージ0
(book_id↔ISBN missing/ambiguous/bad を全 block)。これは維持前提。

---

## 論点 F2: 「canonical 対象なし」を auto_accept+空ISBN で表すか、bucket=defer_new に寄せるか

- **観測**: resolver サンプルで `bucket=auto_accept` かつ `isbn=""` の行が4件あり、意図は
  「canonical 対象なし → defer」。だが `blocked_bad_isbn` 期待の2件も**入力形状が完全に同一**
  (auto_accept, isbn="")。接合ツールは両者を区別できず**全て blocked_bad_isbn**。
- **論点**: auto_accept は「解決済ISBNを持つ」不変条件とすべきか。「対象なし」は
  `bucket=defer_new` で表現する規約に統一すべきか。
- **選択肢**:
  - (A) **resolver 規約を統一**: auto_accept ⇒ 有効ISBN必須。対象なしは defer_new。
    (ツール現状のまま。resolver 出力側を直す)
  - (B) **ツールを寄せる**: auto_accept+空ISBN → `defer_staging` 扱い (malformed-present な
    ISBN のみ blocked_bad_isbn)。
- **番頭推奨**: (A)。auto_accept の意味を「適用先が確定」に保つ方が誤接合に強い。ただし
  resolver 実装が空ISBN auto_accept を出し続けるなら (B) の救済も要るか。

## 論点 F3 (重要): simple-only ゲートは `toc_status` ラベルに依存する — その信頼性

- **観測**: 既存 toc `9784641046429` は **bencom・104ノード・3階層ネスト＋ページ番号付き**の
  リッチな目次。だが全ノード `toc_status="simple"`。simple-only ゲートは「全 simple かつ
  非保護ソース(bencom は非保護)」→ **overwrite_simple** と判定。
- **問題**: `toc_status=="simple"` が**実態(深い構造/ページ有り)とズレている**と、本来
  保護したい既存TOCを legallib で上書きしてしまう。ゲートはラベルの正確性に全依存。
- **選択肢**:
  - (A) **上流のラベリング是正**: 構造深さ>1 or ページ有り の既存TOCは非simple に正す
    (供給側=openbd/bencom 取り込み時の status 付与を直す)。
  - (B) **ゲートに構造ガードを追加**: `toc_status` に加え「既存に depth>1 のノードがある or
    page_start を持つなら保護扱い」を AND で課す (ラベル不正に対する安全弁)。
  - (C) **bencom を保護ソースに格上げ** (PROTECTED_SOURCES に追加)。
- **番頭推奨**: (B)+(A)。(B) は実装容易でラベル不正に頑健(誤って上書きしない方向に倒す)、
  (A) は根本是正。(C) は乱暴(bencom にもフラット低品質はある)。
- **トレードオフ**: (B) は「legallib の方が実際リッチでも、既存が構造ありなら一旦 human_review」
  となり overwrite 候補が減る (安全側だがレビュー件数増)。許容可か。

## 確認してほしい点
1. F2 の (A)/(B) いずれが ALO 規約として正しいか。auto_accept の不変条件をどう定義すべきか。
2. F3 で simple-only ゲートを `toc_status` 単独依存のままにするリスク評価。(B) 構造ガード追加の
   是非。overwrite 候補減 (レビュー増) を許容すべきか。
3. 見落としている第3の論点 (例: legallib 自身の品質をどう信頼するか、同一書籍に複数版TOCが
   来た場合) があれば指摘。
4. accept 可否＋ v0.2 で閉じるべき必須修正。

## 返却様式 (PROTOCOL準拠)
- 書き戻し先: `from_gpt/20260610_legallibjoin_v0.1_DDJOIN_RESULT.md`
- **先頭行 = `DDJOIN_<LABEL>`**。以降 F2/F3 各々に「判断 / 根拠 / 推奨修正」、各に確度＋反証条件。

## 監査対象 (GitHub コネクタで読めます)
- PR #5 / commit `f275206`
- ゲート: `scripts/legallib_join_policy.py` (decide_join_action / PROTECTED_SOURCES / simple-only)
- 誤マージ: `scripts/legallib_join_dryrun.py` (detect_mismerge)
- 実データ所見: `handoff/legallib_dryrun_20260608/SAMPLE_DRYRUN_REPORT.md` (§2 F2/F3, §6 全数突合)
- 照合アンカー: DD-STATUS-REGISTRY (lifecycle軸) / codexgov (quality_status一軸)

## 守秘
設計・状態語彙・スキーマ名・件数レベルのみ。実依頼者データなし。
