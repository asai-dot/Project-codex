# JLT v19.0 — Step 0 取得時ハッシュ基準値（head 記録）

- 出所: claude-code-windows（execution_host: **A-PC / Windows 10.0.19045.7184 (Win10 Pro)**）が
  dispatch `cc_dispatch_jlt_v19_step0_v2_20260602` を実行し、`H:\work\jlt_v19_dl\` で算出。
- 報告: `cc_report_jlt_v19_step0_v2_20260602.md`（path B = H: ローカル保全＋セッション返し）/
  `_acquisition_log_20260526.md` に append。
- 算出: GNU coreutils `sha256sum`（SHA-256 は実装非依存）。timestamp: 2026-06-02 22:05 JST。
- 位置づけ: **landing 前の取得時基準値**。Step 2 で Box から再 DL した landing 後ハッシュと全件一致して初めて格納完了。
- 注意: 原 scrape は 2026-05-26。acquisition_log に取得時ハッシュ未記録だったため本基準値は 06-02 初回算出
  （dispatch 0-2 の「未記録なら今算出」規定どおり）。5/26→6/2 間の無破損を前提とする点だけ記録に残す。

## golden 8点（取得時基準値）

| # | file | bytes | sha256 |
|---|------|-------|--------|
| 1 | jlt_dict_v19.0.xml | 1,109,506 | `c831d22eddc0b2eb41b6c5e0f53faf43c5f3269c4e8c7edac771d5cd8211f748` |
| 2 | jlt_dict_v19.0_utf8.csv | 557,638 | `3a2b06121f675241fe0ad00f2e77524198871e7ed45a4f305de49b0454fb8b97` |
| 3 | jlt_dict_v19.0_sjis.csv | 449,610 | `048c05cc07c499e72794ec439502727aa61cb49d1e13489800ecd77003e1a31c` |
| 4 | jlt_dict_v19.0.pdf | 2,669,002 | `56925a2547b23d1fab230e6713b4721ee22500a9283acfb259c4c520d3e36a2f` |
| 5 | jlt_law.dtd | 13,839 | `14eaad2d2f6a30b6502440c2e29f985975a537247c592d06b3f765bd2f0ddebb` |
| 6 | jlt_dict.dtd | 753 | `0732938d854ae7111c9d5854c1d76e90c21f235c8c09f78ba24d7959eafdf3c2` |
| 7 | _snapshot_download_page_20260526.html | 18,176 | `9d67831105cac74307bf372ac409d9be5eca91025d0c2952839616186644cfa9` |
| 8 | _snapshot_dtd_page_20260526.html | 12,242 | `faa899cc32f955b05f5c726e93a7ba008b003758f2b97b6f00b88614ba10cf0a` |

合計: 8点 / 4,831,266 bytes。CSV(SJIS) #3 は SJIS バイト列が価値 → 後工程でも再エンコード禁止。

## golden 8点（SHA-1 = Box ネイティブ digest・着地照合用）

claude-code-windows が Step 1 着手時に算出（acquisition_log に append 済）。Box は landed file の digest を SHA-1 で返すため、
源↔着地の byte-exact 判定はこの sha1 一致で十分（任意で sha256 二重確認）。

| # | file | bytes | sha1 |
|---|------|-------|------|
| 1 | jlt_dict_v19.0.xml | 1,109,506 | `260aa7b173d44de2adbfec83e85ccd985060352c` |
| 2 | jlt_dict_v19.0_utf8.csv | 557,638 | `a5784d7c0cfafce1d2712102a245ee5660603caa` |
| 3 | jlt_dict_v19.0_sjis.csv | 449,610 | `e5789b861edb474e7c7ec290ffe8c946330e8ec5` |
| 4 | jlt_dict_v19.0.pdf | 2,669,002 | `5103b9f8a4e29d2e76ccdf03be9abdf1ee5aba01` |
| 5 | jlt_law.dtd | 13,839 | `946123bad374a5d4e53c79836d376a66275b7065` |
| 6 | jlt_dict.dtd | 753 | `6e3d300e8c0d4a402de2cffd33a04a240e3d9a4f` |
| 7 | _snapshot_download_page_20260526.html | 18,176 | `8ae7d7c292cfa3e722c4f799df19eef912cd7fba` |
| 8 | _snapshot_dtd_page_20260526.html | 12,242 | `0f94020ed31bc1022f05c09208848904f1d5f837` |

## 付随（golden 8点外・参考）

| file | bytes | sha256 |
|------|-------|--------|
| return_handoff_jlt_v19_dl_to_claudeai_20260601.md | 3,261 | `843652038a3f99de1b5d6fa35b17b717ddc495209915328e4dd99516ae09dc9c` |

## Step 1 試行結果（2026-06-02）= BLOCKED（能力欠如・破損回避で正しく停止）

claude-code-windows が Step 1（byte-exact 着地）に着手 → **STATUS=BLOCKED / reason=no_byte_exact_binary_upload_capability**。
何も upload せず source 無改変。報告: Box `cc_report_jlt_v19_step1_BLOCKED_20260602.md`(file_id 2259859268401) /
ローカル `return_jlt_v19_step1_BLOCKED_20260602.md`。standup: amendment(file_id 2259905800786, cloud 中継)。

- Step -1 PASS（A-PC が正しい宛先機）。BLOCK は機違いでなく**転送能力の欠如**。
- 当機 Box MCP は text-only（`upload_file`/`upload_file_version`）、binary 用 `get_upload_url` 未提供
  → PDF・SJIS CSV を text upload すると確実破損 → 不実行（親 order の鉄則）。
- Box Drive: 対象 docs/alo は `syncState=not_synced` → Drive 経路も不可。
- cloud(head) 側 MCP も同様に text-only。**MCP 経由では誰も byte-exact バイナリ着地ができない。**

### 未解決（head 決定待ち）— Step 1 着地経路の確定

- 0-1 補足: A-PC の boxsdk 資格は「未確認」（credential scan 回避のため）。報告中に `C:\Users\Asai\.claude\keys` 言及あり＝鍵存在の可能性。
- ⚠️ **着地先の訂正**: 試行報告は target を docs/alo と誤記。正典は **05＿語彙レイヤー(folder_id 370003701279)** 配下 `jlt_v19_0`（親 order §1-2）。正式 Step 1 dispatch で修正する。
- 経路の二択（親 order §3）:
  1. **boxsdk あり** → A-PC が python で 370003701279 へ直 upload＋sha1 照合を自走（最有力・自動）。
  2. **無し** → 浅井先生が Box web UI で `jlt_v19_0` 作成＋8点 D&D → windows が sha1 全件照合で LANDED_VERIFIED。
- Step 1 は head routing（正しい着地先）＋ 浅井先生のゴー後にのみ実行。現時点 gate 維持・転送未着手。

## Step 1 試行②（boxsdk 経路, 2026-06-02 22:57 JST）= BLOCKED reason=boxsdk_auth_or_perm

正式 dispatch `cc_dispatch_jlt_v19_step1_boxsdk_20260602`（Box id 2259921555626）を浅井先生のゴーで実行。
Step -1 PASS（COMPUTERNAME=DESKTOP-UH5QM00 / H:\work\jlt_v19_dl\ あり / golden 8点サイズ全件一致）。
Step 0 boxsdk プリフライトで停止 ── **A-PC に使える非対話 Box 資格が無い**ことが判明：

- `.box_token`（H:\work\box_manifest\）は 2026-05-12 付で**期限切れ**（"Developer token has expired"）。Box dev token は60分失効。
- `BOX_DEVELOPER_TOKEN` 環境変数: 未設定。
- `C:\Users\Asai\.claude\keys` の .json は **GCP サービスアカウント**（Box JWT ではない）。かつ 6/2 13:05 の ACL 強化で読取不可。
- `BOX_CLIENT_SECRET` はあるが `BOX_CLIENT_ID`/enterprise_id が無く CCG 認証を組めない。
- MCP binary は禁止（text-only で破損）→ フォールバック無し。

結果: upload ゼロ・source 無改変・v18 不可触・トークン値非出力。報告 `cc_report_jlt_v19_step1_BLOCKED_boxsdk_auth_20260602.md`(Box id 2259915126581) / standup amendment(id 2259901711164)。

### 残る経路（2択・浅井先生の選択待ち）

1. **新しい Box developer token を発行**（Box dev console → 既存 app → Configuration → Generate Developer Token, 60分有効）→ `H:\work\box_manifest\.box_token` に保存 or `BOX_DEVELOPER_TOKEN` に設定 → windows が dispatch を再実行し、folder 作成＋8点 upload＋sha1 全件照合まで自走（最速・自動）。
2. **浅井先生が手動 upload**（Box web で 370003701279 配下に `jlt_v19_0` 作成＋8点を D&D, SJIS は raw bytes＝再エンコードなし）→ windows が sha1 全件照合で LANDED_VERIFIED 判定。
- （恒久策）CCG/JWT 資格（client_id+secret+enterprise_id か Box JWT config）の整備。
