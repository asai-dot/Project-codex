# VALIDATION — docx batch1 復元方式の実証（番頭ゲート）

- **対象**: `material_queue/20260608_docx_batch1`（月30枠で取得・27DL/21解析OK/6不正形式）。
- **判定**: **復元方式 VALIDATED（PASS_WITH_NOTES）**。restorable_profile は本筋で機能。スケール前に下記5欠陥を修正。

## 1. 実証された核心（◎）
- **条見出しキャプションの回収**: 3249新設合併契約書で**全17条をキャプション込み**で fixed_spans 化（第1条（合併の方法）…）。OCRは番号のみ・キャプション全欠落だった → **docx忠実復元の価値を実証**。batch全体で**119キャプション回収**。
- **OCRの条数誤りを露呈**: 就業規則 OCR50 vs docx**76**（OCRが34%=26条見落とし）／文書管理規程+7／監査役会規則+7／従業員持株会規約+8。「OCR平均回収99.1%」は相殺による誤った安心で、**実体はdocxが大幅に多く拾う**＝"OCR=triage / docx=忠実復元"を数値で確証。
- **signature_block＋監査メタ**: date/parties(name/address/㊞)検出、hash・version・canonical_image_ref・validation_status=candidate 完備 → 再生成可能＋監査可能。**事務所PDF横展開の器として妥当**。

## 2. スケール前に直す欠陥
- **A. ダウンロード信頼性（重大・クォータ直撃）**: 6/30が `application/vnd...themeManager+xml`＝Word以外が落ちて解析不能（4163,4166,4168,4323,4324,4937）。希少な月30枠を無駄打ち。**修正: 取得直後に zip/content-type 検証 → 不正なら budget にカウントせず再取得 or 別エクスポート経路。** 次バッチ前の必須対応。
- **B. slot抽出精度（高）**: 括弧見出し（合併の方法）等を `blank_lined` slot に誤抽出（3249で約22偽slot、fixed_spansと重複）。**修正: fixed_spans/条キャプションに含まれる括弧は slot から除外。slot は party-def「（以下「○」という）」/ ○〇下線空欄 /〔〕【】/ money・date・rate パターンに限定。** slots_extracted の数値（就業規則108等）は現状過大。
- **C. 英文/翻訳契約（高）**: 11318/11325/11327（Consignment/Basic Purchase/JV 日本語訳）が docx_clauses=0。`第N条`のみ対応で **Article型・表組の条文を拾えず**。**修正: Article \d+ / Section / 表内条文 を条見出しに追加検出。** 英文契約テンプレは高価値。
- **D. F1過剰救済（中）**: 雇用契約書(3852)は docx でも0条・1slot＝**1枚記入フォーム**（条文契約でない）。**修正: F1救済は暫定とし、docx真値で0条なら B/E1（フォーム）へ確定差し戻し。** 3852は B/E1 へ。4163は不正形式で判定保留。
- **E. 議事録（軽）**: 14281/14490 は docx1条＝E2挙動。archetypeはAだが復元上は E2_minutes として扱う。

## 3. 次工程
1. **無料の再抽出（B/C/D）**: 既取得の21 docx を改良抽出器で再処理 → restorable_profile 再生成（slot精度・英文条文・F1差し戻し）。クォータ0。
2. **A の修正後**、次月枠で 6不正形式の再取得＋第2バッチ。
3. **restorable_profile を v0.3 として確定**（スキーマは据置、生成器を改善）。
4. **事務所スキャンPDF横展開**は production rollout＝**GPT再監査ゲート**（v0.2 NOTE5/最終）を通してから。

## 4. クォータ会計
- 本月: 27DL消費（21有効＋6不正形式）。**6件＝枠の無駄打ち**＝欠陥Aの実害。次月枠は A修正後に。
