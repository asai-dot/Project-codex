# WO-HANREI-AUTHORITY-FIX v0.1 — 判例 authority 整合性修正（dry-run先行・実反映は owner GO）

- wo_id: WO-HANREI-AUTHORITY-FIX-V01-20260701
- from: head (CC) / to: 判例 pipeline producer (Mac・d1law_dl)
- priority: 中（全判決join と L5 の根・低手戻り）
- 入力(read-only): `hanrei_authority_corrections_v0.1.csv`（head 生成・1,063件・code 39783df）
  ＋ 判例 authority `判例_identity_keys_{20260605,backfill6yr_20260617}.csv`（212,602行）
- result_to: 判例 pipeline の from_producer / RPT_hanrei_authority_fix_v01_<日時>

## 背景
head の read-only 決定論QAで判例authority(全判決join・L5主鍵の根)に確定誤り1,063件:
DUP_HANREI_ID 600 / DUP_IDENTITY_KEY 444 / BAD_DATE 4 / COURT_KEY_MANGLED 15。
court化け(四日市→4日市)は評釈との court_miss 一因＝直すと L5 被覆も改善。

## scope（producer がやること・段階的）

### 段1: dry-run 検証（read-only・owner GO 前に実施可）
1. 修正候補1,063件を judgmentデータと突合し、各 recommend の妥当性を検証:
   - DUP_HANREI_ID/DUP_IDENTITY_KEY: 2行が**真の同一判決**か（全列一致 or 軽微差）を判定。真重複→統合候補、別判決→identity_key 精緻化候補に分類。
   - BAD_DATE: 判決年月日(漢字)から date_key を再導出（昭和38.2.29 等は原本確認フラグ）。
   - COURT_KEY_MANGLED: 裁判所名フルから court_key を再導出（先頭漢数字復元）。回帰: 復元後 court_key が他の正規 court_key と衝突しないか。
2. **preview diff**（before/after）と件数・影響行を RPT に出す。**この段は authority 本体に書かない**。

### 段2: 実反映（owner GO 必須・HOLD）
- 段1 preview を owner が承認 → authority へ append-only/補正適用（raw保全・旧値保持）。
- court_key 再導出は L5 court 突合の再生成も誘発（被覆改善の確認）。

## 受入基準（段1）
- 1,063件すべてに verdict（真重複/別判決/再導出可/原本確認要）が付く。
- COURT_KEY_MANGLED 15件は全て裁判所名フルから一意復元でき、衝突0。
- preview diff が件数・サンプル・high-risk(別判決疑いの重複統合等)を含む（DD-L5 v0.3 binding 同様の packet 規律）。

## 安全（厳守）
- 段1は **read-only / dry-run**。judgment本体・当事者名の生payloadは出力しない（識別キーのみ）。
- 段2(実反映)・canonical昇格・DB投入・外部公開は **owner GO**。raw保全・append-only。
- 迷ったら needs_decision で head へ戻す。

## head 受入検査
- 段1 RPT を head が検査（verdict網羅・court復元衝突0・high-risk明示）。必要なら GPT 監査へ。
- 段2 後、判決join と L5 court_miss の改善を head が回帰監査。
