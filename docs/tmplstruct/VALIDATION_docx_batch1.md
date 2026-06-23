# VALIDATION — docx batch1 検収（番頭・restorable_profile 実証ゲート）

- **対象**: ワーカー docx_batch1（Box `material_queue/20260608_docx_batch1`、ローカル `~/alo-ai/work/legallib_dl/docx_batch1/`）。
- **入力**: 取得30件のうち **有効 21 件**（`.docx_struct.json` + `.restorable_profile.json` 生成済）、**不正形式 6 件**（`_BAD_DOCX.json` 記録、`themeManager+xml` 5 件＋relationship error 1 件）、未取得 3 件。
- **方法**: 21件の `restorable_profile`/`docx_struct` を読み、3249 を理想例に据えて `_OCR_VS_DOCX.md` の集計と整合させた上で、slot/見出し/言語/形状ごとに失敗パタンを抽出。
- **結論**: **VALIDATION PASS_WITH_NOTES**。restorable_profile スキーマと「OCR=triage / docx=忠実復元」の設計は実証成功。事務所スキャンPDFへ横展開する前に **欠陥 5（A〜E）を確定論で潰す**。うち A はクォータ直撃で次バッチ前に必須、B/C/D は **既取得 21 docx で無料再抽出**（v0.2.1）で完結する。

## 1. 定量結果

| 指標 | 値 | 評価 |
|---|---|---|
| docx 取得 | 30/30 | ◎ クォータ消費は ratify 内（ただし 6 件が無効ファイル=欠陥A） |
| 解析成功 | **21/30**（70%） | △ ファイル品質ゲートが必要（欠陥A） |
| 全件 docx 条数 合計 | **338**（21件） | ◎ OCR 合計 335 と一致水準 |
| **見出しキャプション回収** | **119**（OCRが落としていた見出し文） | ◎ docx 復元の最大価値が定量化 |
| restorable_profile_ok | 21/21 | ◎ スキーマ充填エラーなし |
| signature_block 検出 | 3249 等で `YES`（実例確認） | ◎ ㊞・押印枠込みで取得（個別件で網羅性検証は次工程） |
| 監査メタ (hash/version/canonical_image_ref) | 21/21 | ◎ profile_version=`restorable_profile_v0.2`／parser=`docx_extract_v0.1_20260608` |

**OCR↔docx の核心**：OCR が条見出しキャプションを全欠落させていた件で、docx が **119 個** のキャプションを完全回収。就業規則 OCR50→**docx76（+26 条＝34% 見落とし）** など、OCR では到達不能な忠実復元が docx で初めて可能になることを実測で確証。

## 2. 理想例＝3249 新設合併契約書（横展開の根拠）

`3249.restorable_profile.json` を引用：

- **fixed_spans 17 件**：「第１条（合併の方法）」「第２条（新設会社の目的等）」…「第17条（協議解決）」を **全条キャプション込み**で回収（OCR は番号のみで全 17 キャプション欠落していた箇所）。
- **slots 30 件**（blank_lined 26 / address 1 / money 3）。
- **signature_block: YES**（㊞含む末尾署名枠を検出）。
- **meta** に sha256 / parser_version / profile_version / canonical_image_ref を完備 → そのまま再生成・再監査可能。

この一件が証明したこと：**restorable_profile v0.2 スキーマは（少なくとも条文型契約 archetype A に対して）実 docx から忠実復元できる器**。事務所スキャンPDF横展開の前提が立った。

## 3. 件別評価（21 有効・抜粋）

| tid | title | OCR_条 | docx_条 | キャプ回収 | slots | 判定 |
|---|---|---:|---:|---:|---:|---|
| 3249 | 新設合併契約書 | 17 | 17 | 17 | 30 | **理想例**：全条キャプション復元・署名検出 |
| 2369 | 持株会規約 | 17 | 25 | 22 | 28 | ◎ docx が +8 条と全キャプション回収 |
| 4262 | 就業規則 | 50 | **76** | 0 | 108 | ◎ OCR の **26 条見落とし**を docx で完全補填／一方 slot 105/108 が `blank_lined`＝欠陥B |
| 9395 | 給与規程 | 34 | 29 | 29 | 31 | ◎ キャプション全回収（OCR は数えすぎ 34→真値 29） |
| 9400 | 退職金規程 | 14 | 15 | 12 | 16 | ◎ 表 1・キャプ 12/15 |
| 9414 | 在宅勤務規程 | 21 | 22 | 21 | 27 | ◎ ほぼ完全回収 |
| 2354 | 情報管理規程 | 18 | 23 | 18 | 41 | ◎ +5 条、18 キャプ回収 |
| 11318 | Consignment Agreement | 10 | **0** | 0 | 6 | **欠陥C**：`Article N` 28 段落あり／`第N条` 0 ＝ regex が英文を拾えない |
| 11325 | Basic Purchase Agreement | 5 | **0** | 0 | 4 | **欠陥C**：`Article N` 27 段落あり |
| 11327 | Joint Venture Agreement | 8 | **0** | 0 | 11 | **欠陥C**：`Article N` 42 段落あり |
| 3852 | 雇用契約書 | 0 | **0** | 0 | 1 | **欠陥D**：docx 18 段落・0 表＝1 枚記入フォーム＝**F1 救済は誤りで B/E1 へ差し戻し** |
| 14281 | 株主総会議事録 | 5 | 1 | 0 | 6 | **欠陥E**：`第N号議案` 15 hit／`第N条` 1 ＝議案見出しは E2 挙動として別扱い |
| 14490 | 取締役会議事録記載例 | 5 | 1 | 0 | 6 | 同上（議案 5 hit） |
| 14970 | 和解契約書 | 7 | 2 | 0 | 7 | 要 OCR 比較（段落 numbering 拾い漏れの疑い・次バッチ精査） |
| 15055 | サブリース | 24 | 17 | 0 | 19 | OCR が数えすぎ／キャプ回収 0＝形式チェック必要 |
| 1859 | 定款 | 37 | 29 | 0 | 34 | OCR 数値勝ち／キャプ 0＝段落構造を要再確認 |

（残 5 件＝1988/2349/4119/9338/14950 は概ね正常、`_per_template.json` 参照）

## 4. 欠陥（次の工程で潰す）

### A. ダウンロード信頼性 — **重大／クォータ直撃**
- 30 件中 **6 件が Word 以外**＝ `themeManager+xml`（4163・4166・4323・4324・4937）または relationship 欠落（4168）。
- 月 30 の希少枠を **6 件分無駄打ち**（消費 30＝有効 21＋bad 6＋未取得 3）。
- **直し**：取得段で `Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document` を必須検証、不一致なら **エクスポート再リクエスト**＋それでも失敗なら `_BAD_DOCX` へ落とし、**budget から控除しない**運用。
- **適用タイミング**：**次月枠（batch2）取得前のフェッチャ修正必須**。本月内に修正だけ完了して次月初回ですぐ回す。

### B. slot 精度 — 高（無料再抽出で潰せる）
- 3249 の blank_lined slot 26 件のうち **11 件が見出しキャプション**の二重抽出（「（合併の方法）」「（新設会社の目的等）」…）。fixed_spans の `第N条（…）` と重複。
- 4262 就業規則は **108 slots 中 105 が blank_lined**＝同じ caption 取り込み問題が大規模に発火。
- **直し（v0.2.1）**：
  - slot 抽出ルールから `^（[^）]+）$` 単独段落を除外（fixed_spans に既に含まれる）。
  - `第N条（…）` 行内のカッコ部はキャプションとして fixed_spans 側のみへ寄せ、slot 側で再カウントしない。
  - blank_lined の真の対象＝**下線/連続スペース/〔　〕/【　】/_ など「記入欄を示す記号」を含む段落**に限定。

### C. 英文契約 — 高（無料再抽出で潰せる）
- 11318/11325/11327（Consignment / Basic Purchase / JV 日本語訳）：docx 条数 0、しかし `Article N` 段落が **28 / 27 / 42 件**存在。`第N条` 正規表現が `Article N` を拾えていないだけ。
- **直し（v0.2.1）**：抽出 regex に `^Article\s+([0-9]+|[IVXLC]+)(?:\.|\s)` を追加。表組（11318 は tables=1）も headings_full 候補として走査。

### D. F1 過剰救済 — 中（無料差し戻し）
- 3852 雇用契約書：docx でも 18 段落・0 表・0 条見出し＝**1 枚記入フォーム**。OCR の 0 条は誤分類ではなく真値。
- **直し**：classification を **B（短文slot）または E1（フォーム）へ差し戻し**、`source_fidelity` から `docx_required` を外す。F1 ルール本体は維持（他 11 件は条文型契約として残す）。

### E. 議事録系 — 軽（subtype E2 挙動の確認）
- 14281/14490：`第N号議案` 15/5 hit、`第N条` 1。**fixed_spans に「議案」role を追加**するだけで議事録復元が成立する見込み（structure_profile v0.2 の §3.4 と整合）。
- 本バッチでは「E2 として期待挙動と一致」を記録するに留め、次バッチで明示処理を追加。

## 5. 復元方式 v0.3 への昇格条件

以下を満たしたら `structure_profile_v0.3.md` を確定して **事務所スキャンPDF横展開ゲート（GPT 再監査）** に進める：

1. **B/C/D の v0.2.1 再抽出**（無料・クォータ 0）が完了し、就業規則 4262 の slot 比率が `blank_lined ≤ 70%`、英文 3 件の `Article` 検出が `OCR_条数 ±2` に収まる。
2. **A 修正**（content-type ゲート＋再リクエスト）がフェッチャに入り、次バッチで `_BAD_DOCX = 0` を目標値として宣言。
3. v0.3 草案に **3249 を実物 worked example**、4262 を **slot 抽出の挙動仕様**として組み込む。

## 6. 検収観点（ワーカー §7 schema）への回答

| 観点 | 結果 |
|---|---|
| `result` | `success`（欠陥 5 件を申し送り。下記 next_safe_action） |
| `downloaded` | 30/30（うち 6 件＝欠陥A により実質有効 21） |
| `docx_quota_used` | **30/30 完全消費**（A 修正前のため 6 件は無駄打ち） |
| `per_template` | `_per_template.json` 採用、本書 §3 で抜粋 |
| `ocr_vs_docx_summary` | avg_clause_recovery = 99.1%（21件）／captions_recovered = 119 ／ notes = 欠陥B/C/Eで真値が見えにくい件あり |
| `uploaded` | Box `material_queue/20260608_docx_batch1`（worker 投函済） |
| `needs_decision` | 3852 を B/E1 へ差し戻すこと（owner 確認 1 点） |
| `next_safe_action` | **v0.2.1 再抽出パケット（無料・クォータ0）→ A 修正→次月枠 batch2** |

## 7. ステータス

設計監査 PASS → 全件分類 → v0.3.1 → owner ratify → **docx 実証 VALIDATED (PASS_WITH_NOTES)** → 次工程：

- 直ちに：[`WORKER_TASK_PACKET_tmplstruct_docx_reextract_v0.2.1.md`](./WORKER_TASK_PACKET_tmplstruct_docx_reextract_v0.2.1.md) を起票・実行（B/C/D 無料修正・既取得 21 docx ベース）。
- 並行：欠陥 A のフェッチャ修正（取得段の content-type 検証）。
- 次月：batch2 取得（A 修正後）→ restorable_profile v0.3 確定 → **事務所スキャンPDF横展開は production rollout のため GPT 再監査ゲート**を通過させる。
