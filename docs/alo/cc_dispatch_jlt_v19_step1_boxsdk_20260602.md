# cc_dispatch: JLT v19.0 — Step 1（Box byte-exact 着地・boxsdk 経路）

- dispatch_id: cc_dispatch_jlt_v19_step1_boxsdk_20260602
- 宛先: claude-code-windows（A-PC / `H:\work\jlt_v19_dl\` を持つ scrape 機 **のみ**）
- issued_by: claude.ai (head agent) / 起草: claudecode_web（Project-codex）
- 親 order: cc_order_jlt_v19_box_transport_20260601（Box file_id 2257628721136）
- 先行: cc_dispatch_jlt_v19_step0_v2_20260602（Step 0 完了・基準値確定）/ Step 1 初回試行は MCP binary 不可で BLOCKED（cc_report_jlt_v19_step1_BLOCKED_20260602.md, id 2259859268401）
- reversibility: **W2**（Box フォルダ作成＋ファイル upload。正典への書込。delete で可逆だが要検証）
- 発火条件: **浅井先生の明示ゴー**。INC-2026-04-22-001 backfill の I/O 窓と重ねない。
- 本ファイルは Box 未読でも単体で走る自己完結版。**read-only ではない（着地書込を伴う）。**

---

## 0. 前回 BLOCKED の是正点（必ず踏襲）

1. **着地先の訂正**: 正典は **`05＿語彙レイヤー`(folder_id 370003701279)** 配下に新規 `jlt_v19_0`。
   ❌ docs/alo ではない（前回試行の docs/alo は誤り。docs/alo は報告専用、データを置かない＝親 order §1-2）。
2. **転送手段の確定**: **boxsdk（Python）で byte-exact 直 upload**。
   ❌ Box MCP の `upload_file`/`upload_file_version` は text-only。PDF/SJIS CSV を上げると確実破損。**MCP でバイナリを上げるな。**
3. A-PC に Box 資格あり（`C:\Users\Asai\.claude\keys` 実在を確認済）→ boxsdk 認証に使う。

## 着地先（head 実地確認済・幽霊参照なし）

- 親: `05＿語彙レイヤー` id **370003701279**、path `ALO共有フォルダ/ALOナレッジデータベース関連フォルダ（外部共有）/05＿語彙レイヤー`、`canUpload=true`、所有=asai。
- 既存物: `dict_v18_xml.xml`（id 2173956474824, 1,088,385 B, sha1 `2b065c11aa6cbe95ead32eec17395b93ac3d797a`）= **v18。絶対に触るな。**

---

## Step -1 — 実行機アサーション（最初に必ず。1つでも偽なら BLOCK・1行報告のみ）

```powershell
Test-Path 'H:\work\jlt_v19_dl\'
$env:COMPUTERNAME
Get-ChildItem 'H:\work\jlt_v19_dl\' -File | Select-Object Name, Length
```
- `H:\work\jlt_v19_dl\` 存在 ∧ golden 8点サイズが `_acquisition_log_20260526.md` 基準と全件一致 ∧ 自機 Windows、を満たすこと。
- 偽 → `STATUS=BLOCKED reason=not_target_machine` を返して終了。upload しない。

## Step 0 — boxsdk プリフライト（書込前の能力確認。失敗したら BLOCK→手動経路へ）

1. `pip show boxsdk`（未導入なら `pip install boxsdk` 可。venv 推奨）。
2. `C:\Users\Asai\.claude\keys` 配下の Box 資格で boxsdk 認証（JWT config(.json) / developer token を自動判定）。
   **トークン値・鍵の中身は絶対にログ/報告に出すな**（有無と認証成否だけ）。
3. 認証ユーザを取得し、`370003701279` に対する書込可否を確認（フォルダ取得 or 軽い権限確認）。
4. いずれか失敗 → `STATUS=BLOCKED reason=boxsdk_auth_or_perm` を返して終了（→ 浅井先生手動 upload 経路に切替）。

## Step 1 — 着地（boxsdk のみ。MCP binary 禁止）

1. `370003701279` 配下に `jlt_v19_0` を作成 → 生成 folder_id を控える。
   - 既に `jlt_v19_0` が在る場合は**重複作成せず STOP し報告**（部分着地/重複回避）。
2. golden 8点を boxsdk で byte-exact upload（>20MB は chunked、本件は最大2.6MB なので通常 upload で可）。
   - **SJIS CSV は raw bytes のまま。再エンコード厳禁。** v18 は touch しない。

## Step 2 — 着地検証（全8件・必須。1件でも不一致なら STOP）

各ファイル:
- 着地 size == 基準 size（下表）。
- **sha1 byte-exact 照合**: ローカル source の sha1 == Box が返す landed file の sha1（Box ネイティブ digest=SHA-1）。
- （推奨）二重確認: landed を再 download → sha256 が基準と一致。
- 判定: 8点すべて (size OK ∧ sha1 一致) で **LANDED_VERIFIED**。
- 1件でも不一致: 当該 upload を削除（部分着地を残さない）→ `STATUS=BLOCKED reason=hash_mismatch file=<name>` を観測値 vs 基準値つきで報告。**盲目的再 upload 禁止。**

### 基準値（canonical はローカル `_acquisition_log_20260526.md`。下表は cross-check）

| # | file | bytes | sha1 | sha256 |
|---|------|-------|------|--------|
| 1 | jlt_dict_v19.0.xml | 1109506 | 260aa7b173d44de2adbfec83e85ccd985060352c | c831d22eddc0b2eb41b6c5e0f53faf43c5f3269c4e8c7edac771d5cd8211f748 |
| 2 | jlt_dict_v19.0_utf8.csv | 557638 | a5784d7c0cfafce1d2712102a245ee5660603caa | 3a2b06121f675241fe0ad00f2e77524198871e7ed45a4f305de49b0454fb8b97 |
| 3 | jlt_dict_v19.0_sjis.csv | 449610 | e5789b861edb474e7c7ec290ffe8c946330e8ec5 | 048c05cc07c499e72794ec439502727aa61cb49d1e13489800ecd77003e1a31c |
| 4 | jlt_dict_v19.0.pdf | 2669002 | 5103b9f8a4e29d2e76ccdf03be9abdf1ee5aba01 | 56925a2547b23d1fab230e6713b4721ee22500a9283acfb259c4c520d3e36a2f |
| 5 | jlt_law.dtd | 13839 | 946123bad374a5d4e53c79836d376a66275b7065 | 14eaad2d2f6a30b6502440c2e29f985975a537247c592d06b3f765bd2f0ddebb |
| 6 | jlt_dict.dtd | 753 | 6e3d300e8c0d4a402de2cffd33a04a240e3d9a4f | 0732938d854ae7111c9d5854c1d76e90c21f235c8c09f78ba24d7959eafdf3c2 |
| 7 | _snapshot_download_page_20260526.html | 18176 | 8ae7d7c292cfa3e722c4f799df19eef912cd7fba | 9d67831105cac74307bf372ac409d9be5eca91025d0c2952839616186644cfa9 |
| 8 | _snapshot_dtd_page_20260526.html | 12242 | 0f94020ed31bc1022f05c09208848904f1d5f837 | faa899cc32f955b05f5c726e93a7ba008b003758f2b97b6f00b88614ba10cf0a |

## Step 3 — 記録＆完了報告

- `_acquisition_log_20260526.md` に landing セクションを append-only 追記: 各 file の landed file_id / landed sha1 / size / match=OK / landed_at(JST)、および `jlt_v19_0` の folder_id。
- 報告 `cc_report_jlt_v19_step1_<RESULT>_<YYYYMMDD>.md` を docs/alo（folder_id 372503394965）へ upload（text、MCP で可）。
- standup（`_ALO_STANDUP_<当日>.md`）へ1行 append。**amendment ファイル方式で可**（新規 `_ALO_STANDUP_<当日>_amendment_<topic>.md` を upload_file。本体を rewrite しなくてよい＝clobber 回避）。1行だけ書いて深掘りするな。
- return（cloud が次工程で拾う）: `jlt_v19_0` folder_id ／ 8点の landed file_id 一覧（特に `jlt_dict_v19.0_utf8.csv` の file_id＝権威リスト構築の入力）／ 検証結果（size/sha1 全件 OK の明示）。
- BLOCKED 時: 理由・該当ファイル・観測値 vs 基準値を返す。直さず止める。

## 不変条件

- `H:\work\jlt_v19_dl\` の source は削除・改変しない（着地検証 PASS までローカル golden 保持）。
- v18（dict_v18_xml.xml）は触らない。
- 完了基準は rc=0 ではなく **LANDED_VERIFIED（size ∧ sha1 全件一致）**。
- 鍵・トークンの値はいかなる出力にも出さない。
