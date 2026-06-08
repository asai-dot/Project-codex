# WORKER_TASK_PACKET — tmplstruct: 解剖用 .docx 30件 取得＆構造抽出

```yaml
task_id: WORKER_20260608_TMPLSTRUCT_SAMPLE30_001
created_at_jst: 2026-06-08
requested_by: Claude (浅井先生担当・リモートセッション / 番頭)
executor: claude-worker   # Mac CC worker（~/alo-ai/work/legallib_dl/ と リーガルライブラリー 認証セッション・月30 .docx枠を持つ唯一の実行者）
lifecycle: draft
role: worker_task
permission_tags:
 - no-production-db-write   # Supabase 投入はしない（本タスクは取得＆抽出のみ）
 - no-DDL
 - no-SF-writeback
 - no-Box-delete
 - docx-download-AUTHORIZED-budget-30   # ★リーガルライブラリーからの .docx エクスポートを 30件まで明示許可（owner ratify 済の枠）
max_turns: 60
cost_cap_usd: 5
output_path: _claude_dispatch/from_worker/20260608_tmplstruct_sample30_RESULT.md
stop_condition: one-pass-complete | needs_decision | blocked | budget_exhausted | max_turns
```

## 背景（なぜこの30件か）
GPT お目付け監査が `DESIGN_MODIFY_REQUIRED`（`from_gpt/20260608_tmplstruct_v0.1_DESIGN_RESULT.md`）。
核心: **書式テンプレを「読む文献」として outline 化していたのが誤り。type 別 `structure_profile` を実物 .docx から逆算せよ。**
盲目設計を避けるため、月30枠で **設計判断が分かれる類型に層化した30件** を取得し、実構造を抽出する。
選定は番頭が決定論アルゴリズムで固定（worker は選ばない＝恣意性ゼロ）。worker は「取得＋構造抽出＋アップロード＋報告」のみ。

## 0. 前提資産（実行前に存在確認）
- カタログ: `~/alo-ai/work/legallib_dl/templates.json`（無ければ `app/data/templates.json`）
- 選定スクリプト: 本リポジトリ `loaders/select_template_sample.py`（このブランチを pull）
- .docx 取得経路: worker が既に使っている **リーガルライブラリーの .docx エクスポート**（月30枠）。本パケットは 30件まで authorize。
- アップロード先: Box `handoffs/gpt_ometsuke/material_queue`（folder_id `387887802362`・現在空）

## 1. タスク（順に実行・bounded）
1. **bind & inspect**（DB非接触）:
   `python3 loaders/select_template_sample.py --catalog <catalog> --inspect`
   - `unresolved fields` が出たら `select_template_sample.py` の該当 `*_KEYS` 先頭に実キー名を追記（最小差分）。判断は §6 形式で記録。
2. **選定（決定論）**:
   `python3 loaders/select_template_sample.py --catalog <catalog> --out docs/tmplstruct/SAMPLE30_manifest`
   - `SAMPLE30_manifest.json/.md`（30件・stratum別）を生成。`total_selected != 30` の警告が出たら **stop=needs_decision** で報告（corpus不足の可能性）。
3. **.docx 取得（budget=30・authorize済）**:
   - manifest の各 `source_url`（無ければ `id`）から **リーガルライブラリーの .docx を 30件取得**。
   - **30件で必ず打ち切る**。途中で月枠が尽きたら取得済分で `budget_exhausted` 報告。
   - 取得は `~/alo-ai/work/legallib_dl/sample30/<id>.docx` に保存。
4. **構造抽出（解釈しない・事実のみ）**: 各 .docx について以下を機械抽出して `<id>.struct.json` に：
   - `paragraphs`: [{text, style_name, outline_level, numbering(ilvl/numId), is_bold_heading_like}]
   - `tables`: 表の有無・行列数・各セル先頭テキスト（差込枠の検出用）
   - `fields_or_placeholders`: 〔　〕／（　）／下線空欄／「甲」「乙」「年 月 日」等の差込候補トークンと出現位置
   - `headings_detected`: スタイル/ナンバリングから見た見出し候補（条・項・号の階層）
   - `counts`: 段落数・表数・推定差込スロット数・定型文字比率
   - ※ structure_profile の設計判断（outline採用/slot化）は **番頭が後で行う**。worker は生事実のみ。
5. **アップロード**: `material_queue`(387887802362) に **30件の .docx＋各 .struct.json＋SAMPLE30_manifest.json** を置く。
6. **報告**: §7 schema で `output_path` に。Box `CODEX/handoff/` にもコピー（実シークレット・認証情報は貼らない）。

## 4. Allowed operations
- read: templates.json / 本ブランチの `loaders/` / 取得した .docx（自分が保存したもの）
- fetch: リーガルライブラリー .docx エクスポート **30件まで**（本パケットの authorize 範囲）
- write: `~/alo-ai/work/legallib_dl/sample30/`（workdir内）・Box `material_queue` へ upload・`output_path` へ report
- run: 上記 deterministic スクリプト・docx 構造抽出（python-docx 等）

## 5. Forbidden operations
- Supabase / 本番DB への書き込み・DDL、SF 書戻し、Box ファイル削除
- 31件目以降の .docx 取得（**budget 厳守**）
- structure_profile の設計確定・templates.json 本体の改変（解釈は番頭の領分）
- 認証情報・トークン・他人のホームディレクトリの読取り
- 守秘: 実案件データ・依頼者個人情報を含む書式は除外（manifest段階で除外し needs_decision 報告）

## 7. Required output schema
```yaml
result: success | partial | needs_decision | blocked | budget_exhausted | failed
confidence: high | medium | low
catalog_used: <path> / records: <n>
field_binding: { id: ..., title: ..., formType: ..., source_url: ... }  # inspect結果＋追記したキー
stratum_distribution_full_corpus: { contract: , other: , court_filing: , notice: , registry: , notarial: }
selected: 30  # or 実数＋不足理由
downloaded: <n>/30   # budget 消費
uploaded_to_box_material_queue: [ <file names> ]
per_template:        # 30件ぶん（または取得できた分）
 - id: ...
   stratum: ...
   title: ...
   formType_current: ...
   structure_facts:
     paragraphs: <n>
     tables: <n>
     placeholders_detected: <n>
     headings_levels: <e.g. 条/項/号 or none>
     looks_like: free_text | clause_headed | slot_form | table_form   # 観察のみ（設計判断ではない）
decision_log:        # §6 形式（観測/選択肢/採択/理由）
 - ...
needs_decision: [ ... ]
next_safe_action: 番頭が material_queue を読み structure_profile v0.2 を逆算
```

## 注記（routing）
- 本パケットは reference/draft。**owner が worker を起動して初めて実行**される（人は選定・DLを手作業しない＝worker が私の選定アルゴリズムを実行する）。
- 完了後、番頭(リモートClaude)が Box `material_queue` の .docx＋struct.json を読み、**type別 structure_profile v0.2** を逆算して `to_gpt` に再投函する。
```
```
