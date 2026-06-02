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

## 付随（golden 8点外・参考）

| file | bytes | sha256 |
|------|-------|--------|
| return_handoff_jlt_v19_dl_to_claudeai_20260601.md | 3,261 | `843652038a3f99de1b5d6fa35b17b717ddc495209915328e4dd99516ae09dc9c` |

## 次工程（Step 1 routing 待ち）

- 本基準値の確定で Step 0 の 0-2 / 0-3 は充足。
- 残るは 0-1（A-PC の Box 書込手段: boxsdk JWT/developer token の有無 / Box Drive 導入と同期フォルダ）。
  これで Step 1 transport の経路（boxsdk 直 / Box Drive / 浅井さん手動 Box web UI）が確定する。
- Step 1 は head の routing ＋ 浅井先生のゴー後にのみ実行（現時点 gate 維持、転送未着手）。
