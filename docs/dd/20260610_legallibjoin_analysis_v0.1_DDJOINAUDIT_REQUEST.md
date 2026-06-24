---
request_id: 20260610_legallibjoin_analysis_v0.1_DDJOINAUDIT
topic: legallibjoin_analysis
gate: DDJOINAUDIT
version: v0.1
source_hash: sha256:8d76d59cf4052687958c1e90f0e5abcfdfaa8078ecc3a78c375029c9e8c0e330
git_commit: c8bb186
git_branch: claude/legallib-integration-design-Jgrtf
git_pr: https://github.com/asai-dot/Project-codex/pull/5
supersedes: null
result_expected_filename: 20260610_legallibjoin_analysis_v0.1_DDJOINAUDIT_RESULT.md
status: queued
---

# GPT Pro お目付け役 監査依頼: web Claude の「ドライラン結果の分析と次の一手」が安全か (DDJOINAUDIT)

- gate: **DDJOINAUDIT** / topic: legallibjoin_analysis / 起票: 2026-06-10 / 番頭: web CC
- RESULT 先頭行: `DDJOINAUDIT_PASS` / `DDJOINAUDIT_PASS_WITH_NOTES` / `DDJOINAUDIT_MODIFY_REQUIRED` / `DDJOINAUDIT_FAIL` / `DDJOINAUDIT_NEED_MORE`
- **これはコード監査ではなく、web Claude の判断・分析・推奨手順が安全か/過信か/危険な前提を含むかのメタ監査**。owner が「web の言い分が危ない気がする。判断がつかない」と感じたため第三者裁定を求める。

## 0. owner の懸念（これを最優先で見てほしい）
owner 所感: 「web Claude の分析、なんか危ないことを言っている気がする。本適用に進めてよいのか判断がつかない」。
→ **web Claude の安全判断に、過信・見落とし・危険な暗黙前提がないか**を地に足の付いた事実で検証してほしい。特に「overwrite_simple を自動書き込み候補に入れている」点が安全か。

## 1. 前提事情（システム）
- 目的: legallib の詳細目次(TOC)を本番蔵書 canonical (`app/data/toc/isbn_*.json`) に接合。
- 確定ポリシー(owner ratify 済): **simple-only ゲート**（既存が `toc_status==simple` のみ、かつ非保護ソース、かつ非構造(F3構造ガード)のときだけ昇格上書き）/ 人手・NDL・出版社・PDF目次・**構造あり**は絶対上書きしない / book_id↔ISBN 誤マージ0 / provenance 付与。
- **ドライラン** = 本番に書かず、各書籍を create / overwrite_simple / route_human_review / skip_idempotent / blocked_* / defer_staging に振り分けるだけ。
- **本適用** = 人手承認した ISBN のみ `apply --commit` で実書き込み。
- **overwrite_simple の意味 = 既存 simple TOC を legallib TOC で全置換 (マージではない)**。

## 2. 観測データ
- 合成デモ(6件): overwrite_simple 1 / create 1 / route_human_review 2 / blocked_missing 1 / defer 1。invariant_violations 0。L300(manual)は正しく保護。
- 実全数(2,760件, ただし v0.2/構造ガード前): overwrite_simple **1525** / create 215 / route_human_review 309 / defer 616 / blocked_bad_isbn 95。invariant_violations 0。
- 既知: overwrite_simple は legallib への全置換。`render_proposed_diff` で enrich(旧⊆新, 安全) と replace(旧の一部が新に無い, 要確認) を仕分け可能。デモの overwrite 例は「replace」(旧タイトルが新に無い) だった。

## 3. web Claude の分析と推奨（←これを監査対象に）
web は次のように述べた（要旨・原文趣旨）:
1. 「デモ結果は合成のカバレッジ・スモークで、実データ品質や分布の証拠ではない。invariant 0 もフィクスチャに罠を仕込んだから検出できた面がある（ややトートロジー）」。
2. 「実全数比率は v0.2(構造ガード)前なので、再実行すると overwrite が review に流れて減るはず。旧数字は最終値の予測に使えない」。
3. 「**overwrite_simple は全置換で、legallib が既存より良い保証はない。デモでも replace(旧情報喪失)だった。overwrite候補は render_proposed_diff で enrich/replace に仕分けて人手レビューすべき。盲目適用は禁物**」。
4. 「F3 構造ガードを足したが根本は toc_status ラベル精度。安全側に倒したのでレビュー増で受ける」。
5. 「create vs missing は実 books.json 突合が要（web では近似）」。
6. 推奨手順: **実全数を v0.2 で再実行 → render_proposed_diff で replace 候補抽出 → そこを重点レビュー → 承認 ISBN のみ apply**。
7. 「『緑=出荷OK』ではなく『緑=危険経路は塞がれた。中身の良し悪しは人が見る段階』」。

## 4. 特に裁定してほしい点
1. **overwrite_simple を“自動書き込み候補”に置くこと自体が危険ではないか**。create(純新規=破壊なし)だけ自動、**既存を全置換する overwrite は status に関わらず全件 human_review に回す**べきでは? web の「diff レビュー前提で overwrite を候補に残す」判断は妥当か、過信か。
2. **全置換 vs マージ**: 既存 simple TOC を legallib で全置換する設計は、既存にしか無い情報(独自ページ番号・別表記)を捨てうる。マージ(既存温存+legallib追加)を検討すべきか、全置換で良いか。
3. web の分析の各主張(§3)に**事実誤認・過信・危険な暗黙前提**がないか。特に「invariant 0 はトートロジー気味」という自己評価は正しい謙抑か、それとも検収の意味を過小評価しているか。
4. owner が「危ない」と感じた直感の正体は何か（言語化してほしい）。
5. 本適用に進む前の **gate 条件**（これを満たすまで apply 禁止、というチェックリスト）。

## 5. 返却様式 (PROTOCOL準拠)
- 書き戻し: `from_gpt/20260610_legallibjoin_analysis_v0.1_DDJOINAUDIT_RESULT.md`
- **先頭行 = `DDJOINAUDIT_<LABEL>`**。以降、§4 各点に「判断/根拠/推奨」＋確度＋反証条件。owner 懸念(§0)への直接回答を必ず含めること。

## 6. 監査対象
- PR #5 / commit `c8bb186`。`scripts/legallib_join_policy.py`(decide_join_action/is_structurally_rich) / `legallib_join_dryrun.py` / `handoff/legallib_dryrun_20260608/SAMPLE_DRYRUN_REPORT.md`。
- 既決: DDJOIN v0.1→v0.2 (MODIFY_REQUIRED→accepted), DDPROGRESS accepted。

## 7. 守秘
設計・件数・状態語彙レベルのみ。実依頼者データなし。
