# DDTAXOAUDIT 監査結果 反映メモ（2026-06-16）

- 監査: `20260615_d1taxo_accuracy_thread_DDTAXOAUDIT`（Box from_gpt file_id 2287180763230）
- 判定: **DDTAXOAUDIT_PASS_WITH_NOTES**（GPT-5.5 Pro, reviewed 2026-06-16）
- methodology_accept_now: true_with_notes / **apply_now: false / canonical_promotion_now: false**
- final_gate: jsonl byte integrity ＋ sampling record before apply

## 結論（要点）

検収フレーム（A 内部整合 / B 実画面照合 / C JSONL byte検査WO）の三段構えは方法論として妥当。
ただし **apply・canonical acceptance の証拠としては不足**。各層が「何を証明し、何を証明しないか」を
明記し、サンプリングと正本反映を補強すること。

| 層 | 証明する | 証明しない |
|---|---|---|
| A 内部整合(全件) | 取得CSVの構造的整合（壊れていない） | 内容(意味)が正しいこと |
| B 105件目視 | 明らかな異常の不在(sanity) | 全件の内容精度 |
| C byte検査WO | JSONL実体のbyte整合 | 体系の意味的正しさ |

owner の「危ない気がする」の正体（監査が明示）= ①構造整合と意味精度の混同 ②spot-check言語が強すぎる
③box_prior差分の真値化リスク。→ 「合格」ではなく「次ゲートへ進める整合証跡」と弱める。本反映で B 表記を修正済み。

## 採用したノート（このコミットで反映）

- B の表記を `合格判定` → `spot_check_no_obvious_anomaly` に弱め、役割分担を明記（105チェックリスト冒頭）。
- box_prior 非真値・precision 60.67%=差分率（誤り率ではない）の解釈は妥当と確認。
- ①判例側 baseline と ②WEB側 拡張骨格の分離、PR #22 を evidence とする運用は妥当と確認。

## 要対応（apply / acceptance 前・owner ratify 対象）

1. **WO-D1TAXO-002 を完了**し、byte integrity 結果を Box(from_gpt/evidence) へ保存。
   - 追加不変条件（監査推奨）: source_version 単位で labels/relations が閉じる / relation src・dst が同scheme・同version /
     parentless term の reason=`parent_is_statute_layer` 記録 / raw_label vs clean_label・search_norm 区別 /
     enumerator 除去・分離の検査 / term→statute context edge の有無 / scheme_id・source_item_key・source_version の重複混在なし。
2. **B 105件を個別 ○/×/保留ログ**化（checked_by/at/result/note/path）。次サンプルは depth別・large subtree・
   added-only・removed-near・L4親無し・民法709条配下 を層化。
3. **removed 929 を全件 or 層化仕分け**（`box_prior_only / renamed / moved / removed_from_live / prior_false_positive`）。
   ※「任意」扱いは弱い、と指摘。regression 候補として扱う。
4. **added 21,667** のうち巨大枝・深層枝・709条配下を追加サンプル。
5. D1TAXOLOAD 指摘（L3/L4 切断・親無し 10,823・enumerator・外部 scheme/crosswalk）と接続。
6. **正本反映フロー**: PR #22=evidence、Box/DD/_AUDIT_LEDGER=SoT。
   - Box該当DDフォルダに検収サマリを hash付き保存 / acceptance package に `independent_verification_ref`(PR#22/commit/files) 列挙 /
     _AUDIT_LEDGER に `loop_state=returned/reflected`・`pr_number/commit_hash/file_hash/role` 登録 /
     90_design_decisions へは owner ratify 後に「受入れた設計判断」のみ append。

## ステータス

- methodology: PASS_WITH_NOTES（read-only 検収・次WO発注としては妥当）
- apply/canonical: **NO-GO**（HOLD 継続）。上記1〜6の補強と owner ratify 後に別ゲートで判断。
