# tmplstruct — 法律書式テンプレ「再復元可能な構造化」立て直し

## なぜ（業務上の意味）
- 法律書式テンプレ **3,806件** を、文献ではなく「再利用する作成物の型」として構造化し直す。
- この第一歩は **30件（≒全体の1%）の .docx を取得して実構造を抽出**し、「スキャン画像から**再復元可能な構造データ**を取り出せるか」を検証すること。
- 検証が通れば、**事務所内のスキャンPDF書式**にも同じパイプラインを適用でき、**組織オブジェクト（Salesforce）の拡充が極めて容易**になる。→ 業務効率化に直結。

## 監査の結論（立て直しの軸）
`from_gpt/20260608_tmplstruct_v0.1_DESIGN_RESULT.md` = **DESIGN_MODIFY_REQUIRED**
- outline を中心に据えない。
- 画像=正本／OCR=検索補助／分類(formType)=入口／構造化=**類型別 structure_profile**。
- 契約書だけ条項見出し。申立・通知・登記系は **slot 抽出**。
- 契約839件は全清書せず、月30枠で**上位から段階投資**。

## ループ（誰が何を）
1. **番頭(リモートClaude)**: 解剖対象30件を決定論アルゴリズムで層化選定（`loaders/select_template_sample.py`）＋ ワーカー実行パケット作成（`WORKER_TASK_PACKET_tmplstruct_sample30.md`）。← 人は選定・DLを手作業しない。
2. **ワーカー(Mac CC)**: パケットを実行 → リーガルライブラリーから30件.docx取得（budget厳守）→ 構造を**事実として**抽出（解釈しない）→ Box `material_queue` へアップロード＋報告。
3. **番頭**: `material_queue` の .docx＋struct.json を読み、**type別 structure_profile v0.2**（＝再復元単位＝定型span＋差込slot＋繰返group）を逆算 → `to_gpt` に再投函 → GPT再監査。

## 現在地（2026-06-10）— rollout gate 判定
`from_gpt/20260611_tmplstruct_v0.3_ROLLOUT_RESULT.md` = **ROLLOUT_MODIFY_REQUIRED**。rollout を3段階に分離：
- **Design/profile = PASS**（v0.3 schema・fixed_spans/paragraphs 分離は採用）
- **Docx pipeline = PASS_WITH_CONDITIONS**（下記 P0×4 を閉じてから batch2）
- **Office scanned PDF = HOLD**（事務所PDFは shadow-run を別ゲートで通してから production）

**batch2 前に閉じる P0×4（いずれもクォータ0）**: ①content-type/zip 検証フェッチャ ②classify v0.3.1 無料再分類 ③deduped docx_queue ④independent validator 実装＋全profile実行（F-1 空虚ゲート置換）。

## 成果物
- `loaders/select_template_sample.py` — 層化30件サンプラー（read-only・決定論・inspect→bind）
- `structure_profile_v0.3.1.md` — rollout closeout 確定設計（監査反映・meta/anchor・Phase A/B/C）
- `VALIDATOR_restorable_profile_spec.md` — F-1 独立ゲート仕様（G1〜G7）
- `WORKER_TASK_PACKET_tmplstruct_closeout_v0_3_1.md` — P0×4 closeout パケット（クォータ0）
- `WORKER_TASK_PACKET_tmplstruct_sample30.md` — ワーカー実行パケット（取得＋抽出＋アップロード＋報告）
- （ワーカー実行後）`SAMPLE30_manifest.json` ＋ 30×`<id>.docx`/`<id>.struct.json` → Box `material_queue`
