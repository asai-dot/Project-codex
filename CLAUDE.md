# CLAUDE.md — 番頭(Claude)の運用メモ

Claude Code が毎セッション読む正本メモ。ここに書いたルールは次回以降も効く。

## 【重要】GPT お目付け監査レーンの自動化ルール

### 眼目：監査は「記録が残ること」が設計。REQUEST→RESULT→反映 が**実装ログ**になる
**記録が残らない監査は無意味。** REQUEST（何を・どの版で監査に出したか）／RESULT（GPTの判定）／
反映（受けて何をしたか）の連鎖が、そのまま**設計判断と実装の正本ログ**になる。だから「回す」の
ゴールは"GPTに見せる"ことでなく、**この一連が台帳に永続すること**。一過性で消えたら設計が消える。

### 1セット（起票→投函→回収→反映→記録 まで）
1. **REQUEST 作成**（front-matter付き: `request_id` / `gate` / `version` / `source_hash` /
   `git_branch` / `git_pr` / `result_expected_filename` / `status: queued`）。git `docs/dd/` に記録。
2. **Box `gpt_ometsuke/to_gpt/` に投函**（lane の正規キュー）。← **git に置くだけでは GPT に届かない**。
3. GPT お目付け処理 → `gpt_ometsuke/from_gpt/` に `..._RESULT.md`
   （先頭行ラベル `*_PASS` / `*_PASS_WITH_NOTES` / `*_MODIFY_REQUIRED` / `*_FAIL` / `*_NEED_MORE`）。
   **RESULT は git にも回収して残す**（実装ログの一部）。
4. **反映**：RESULT の next_action を実装/対応し、**台帳 `_AUDIT_LEDGER` に記録**（`request_id` /
   `result_label` / `next_action_type` / `reflected` 等）。三点照合（to_gpt/from_gpt/processed）。
   処理済 REQUEST は `to_gpt/processed/` へ退避。**監査結果≠正本化**（反映キューで「赤入れで止まる」事故を防ぐ）。

> 事故事例（覚えておく）: 20260611 ddoctrine の REQUEST を git(PR #15)に置いただけで Box
> `to_gpt/` に未投函 → GPT に届かず、キュー掃き取りで「未処理リクエストなし」と出た。
> **投函しない＝記録(実装ログ)が始まらない**。「投函したつもり」で git 止まり、を繰り返さない。

### 約束事
- **本番 Box への投函・退避・移動は owner の運用領域**。勝手に正本を移動/削除しない。
  投函は owner の明示指示 or 承認の範囲で行い、**やった事実を報告**する。
- **起動は owner**：GPT Pro に「お目付け、キュー（or PR）を見て」で回る。番頭から GPT は起動できない。
- Box パス: `浅井/claude/handoffs/gpt_ometsuke/{to_gpt, to_gpt/processed, from_gpt}`。
- 関連ワークストリーム: `audit-lane-implementation` / `gpt-pro-audit-loop` / `gpt-queue-audit`
  （alo-gpt-audit CLI: status / close / action-queue 等）。

## 巨人の肩・分業（→ docs/dd_doctrine.md が正本）
- 我々の領分は last-mile（整列・三点測量・差分注記・抜け漏れ検出・足場検索）。
  汎用（法令構造・委任グラフ＝法務省/e-Gov、綺麗TOC＝bencom/legallib）は consume・追随。
- authoring（法・手続・解釈の創作）はしない。判断・監査は owner。
