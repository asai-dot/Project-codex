# WORKER_TASK_PACKET — tmplstruct docx 再抽出 v0.2.1（無料・クォータ0）

```yaml
task_id: WORKER_20260611_TMPLSTRUCT_DOCX_REEXTRACT_V021_001
created_at_jst: 2026-06-11
requested_by: Claude (番頭・リモート)
executor: claude-worker   # Mac CC
lifecycle: draft
role: worker_task
permission_tags:
 - docx-download-FORBIDDEN          # ★クォータ0：新規ダウンロード一切なし
 - no-production-db-write
 - no-DDL
 - no-SF-writeback
 - no-Box-delete
max_turns: 60
cost_cap_usd: 4
output_path: _claude_dispatch/from_worker/20260611_tmplstruct_docx_reextract_v021_RESULT.md
upload_target: Box handoffs/gpt_ometsuke/material_queue/20260611_docx_reextract_v0.2.1
stop_condition: one-pass-complete | needs_decision | blocked | max_turns
```

## 根拠

`docs/tmplstruct/VALIDATION_docx_batch1.md` の **PASS_WITH_NOTES**：21 件解析成功で復元方式は実証されたが、欠陥 **B / C / D** が定量化された。本パケットは既取得 docx だけで（**新規ダウンロードなし**）これらを潰す。欠陥 A（content-type）は本パケット対象外（次月枠の取得段で対応）、E（議事録 E2 挙動）は本バッチで挙動記録のみ。

## 対象（既取得 21 docx・新規取得なし）

ローカル: `~/alo-ai/work/legallib_dl/docx_batch1/` の `.docx`（21 件）：

```
1859 1988 2349 2354 2369 3249 3852 4119 4262 9338
9395 9400 9414 11318 11325 11327 14281 14490 14950 14970
15055
```

不正形式 6 件（4163/4166/4168/4323/4324/4937）と未取得 3 件は本パケット対象外。

## タスク（順に・bounded）

### 1. パーサ更新（`loaders/process_docx_batch1.py` を分岐コピー）

`loaders/process_docx_reextract_v021.py` を新設し、次の決定論的差分を入れる。挙動は **既存出力を上書きしない**ように `~/alo-ai/work/legallib_dl/docx_batch1_v0.2.1/<tid>.*` へ書き出す。

#### 1-A. slot ルール（欠陥 B 対策）
- slot 抽出から **`^（[^）]+）$` 単独段落** を除外。
- `第N条（…）` を含む段落のキャプション部は **fixed_spans 側のみ**で表現し、slot として再カウントしない。
- `blank_lined` の対象を以下に限定（OR）：
  - `[_＿]{2,}`（連続アンダースコア）
  - `[ 　]{4,}`（4 字以上の連続空白）
  - `〔[^〕]*〕` / `【[^】]*】` のうち **本文中に挿入された記入欄**（行頭でなく単独カッコ段落でないもの）
  - 「年　月　日」「￥　　　円」のような **記入枠を示す定型**
- 既存 kind（party/address/date/money/rate/authority/free_blank）は仕様維持。

#### 1-B. 英文契約（欠陥 C 対策）
- `extract_headings_full` の正規表現に追加：
  - `^\s*Article\s+(?P<num>[0-9]+|[IVXLC]+)(?:[\.\:　\s]|$)`
  - キャプションは Article 行の続き／同段落後半／次段落見出しから推定（最大 60 字）。
- `tables` 内に `Article N` セルがある場合も headings_full 候補にする。
- fixed_spans の `role` には `article` を統一使用。

#### 1-C. F1 差し戻し（欠陥 D 対策）
- 起動時に classification を読み込み、対象 tid のうち以下を満たすものは **B または E1 へ差し戻し**：
  - docx_clauses == 0 ∧ tables == 0 ∧ paragraphs <= 30 ∧ headings_full == 0
- 差し戻した tid は `_F1_REVERSALS.json` に `{tid, before: archetype/source_fidelity, after, evidence}` で記録。
- 該当が見込まれるのは **3852（雇用契約書）の 1 件**（他は欠陥C＝英文に該当するため除外）。

### 2. 再抽出実行

21 件に対し新パーサを実行し、`~/alo-ai/work/legallib_dl/docx_batch1_v0.2.1/` に：
- `<tid>.docx_struct.json`（headings_full / tables / slots / signature_block を再生成）
- `<tid>.restorable_profile.json`（profile_version を `restorable_profile_v0.2.1` に更新、parser_version を `docx_extract_v0.2.1_20260611` に更新）

を生成。`.docx` 自体はコピーしない（既存 batch1 を正本とする）。

### 3. 差分集計（B/C/D の効果を定量化）

`~/alo-ai/work/legallib_dl/docx_batch1_v0.2.1/_REEXTRACT_DIFF.md` に：

| tid | title | v0.2 条数 | **v0.2.1 条数** | v0.2 slots | **v0.2.1 slots** | v0.2.1 blank_lined 比率 | 改善判定 |

行ごとに改善コメント（欠陥 B/C/D のどれが効いたか）。

そして全体サマリ：

```
- captions_recovered v0.2 -> v0.2.1: 119 -> ?
- 英文 3 件 (11318/11325/11327) 条数: 0/0/0 -> ?/?/?
- 4262 就業規則 blank_lined 比率: 105/108 = 97% -> ?
- F1 reversals: [3852]（または empty）
```

### 4. ゲート判定（受入基準）

下記をすべて満たしたら `result: success`、いずれか欠ければ `partial` で番頭へ差し戻し：

- 英文 3 件で **`Article` 条数 ≥ OCR 条数の 90%**（11318→9+, 11325→4+, 11327→7+）
- 4262 の **blank_lined 比率 ≤ 70%**
- 3249 の **slots ≤ 22**（v0.2 の 30 から減）かつ **fixed_spans 17 維持**
- 3852 の **F1 reversal が記録されている**
- 21 件すべて `restorable_profile_ok: true` を維持

### 5. アップロード

Box `material_queue/20260611_docx_reextract_v0.2.1/` に 21×(`.docx_struct.json` + `.restorable_profile.json`) ＋ `_REEXTRACT_DIFF.md` ＋ `_F1_REVERSALS.json` ＋ `_README.md`。

### 6. 報告

`output_path` ＋ Box `CODEX/handoff/` に §8 schema。

## Allowed / Forbidden

- **Allowed**: 既取得 21 docx の再解析、新パーサ作成（`process_docx_reextract_v021.py`）、Box upload、report。
- **Forbidden**:
  - **新規 .docx ダウンロード（クォータ 0／違反即停止）**
  - 既存 `docx_batch1/` 配下の **上書き**（必ず `docx_batch1_v0.2.1/` 側へ）
  - templates.json / classification jsonl の **改変**（F1 差し戻しは別ファイルに記録するだけ）
  - 本番 DB 書込 / DDL / SF / Box 削除

## 7. 既知の留意点

- `themeManager+xml` 等の **不正形式 6 件は本パケット対象外**。次月枠の取得時に content-type 検証で再取得（番頭側パケットを別途起票）。
- 議事録（14281/14490）は E2 挙動として **本バッチでは挙動記録のみ**（`第N号議案` を fixed_spans の role=`gian` で書ければ書く、強制ではない）。
- 9395/15055/1859 のように OCR 数値が docx を上回るケースは、本パケット範囲外の段落 numbering 拾い漏れの可能性あり。差分集計で記録するに留め、次バッチで判断。

## 8. Required output schema

```yaml
result: success | partial | needs_decision | blocked | failed
parser_version: docx_extract_v0.2.1_20260611
profile_version: restorable_profile_v0.2.1
processed: 21/21
per_template:
  - { tid, title, v02_clauses, v021_clauses, v02_slots, v021_slots, v021_blank_lined_ratio, gate_pass }
gate_summary:
  english_articles_pass: true|false   # 11318/11325/11327 ≥ OCR×0.9
  ruleset_4262_slot_ratio: <ratio>    # ≤ 0.70
  ideal_3249_slots: <n>               # ≤ 22 ∧ fixed_spans == 17
  f1_reversals: [3852]                # 期待値
  all_profile_ok: true|false
captions_recovered_v021: <n>
uploaded: [ ... ]
needs_decision: [ ... ]
next_safe_action: 番頭が _REEXTRACT_DIFF.md をレビュー → restorable_profile を v0.3 として確定 → 事務所スキャンPDF横展開ゲート(GPT再監査)へ起票
```

## 完了後

番頭(リモート Claude)が `_REEXTRACT_DIFF.md` と 21 件の v0.2.1 profile を読み、ゲート基準達成を確認 → **`structure_profile_v0.3.md` を確定** → GPT 再監査ゲートを通して **事務所スキャンPDF横展開**へ。
並行：欠陥 A（content-type 検証付き取得）パケットを別途起票し、次月枠 batch2 取得の前提として完了させる。
