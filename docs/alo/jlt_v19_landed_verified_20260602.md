# JLT v19.0 — LANDED_VERIFIED（着地完了マニフェスト）

- 状態: **LANDED_VERIFIED**（2026-06-02 JST）
- 経路: claude-code-windows（DESKTOP-UH5QM00 / A-PC）が boxsdk(box_sdk_gen) で byte-exact upload。新規 developer token で認証（user 16564603310 = asai）。
- 着地先: `05＿語彙レイヤー`(370003701279) 配下の新規 **`jlt_v19_0`（folder_id 386440014344）**。
- head 独立検証: claudecode_web が Box API 直読みで8点の size ∧ sha1 を基準値と全件突合 → **全一致**。totalCount=8（孤児・部分着地なし）。

## 着地8点（Box 実値＝取得時基準値、全件一致）

| # | file | bytes | sha1 | landed file_id |
|---|------|-------|------|----------------|
| 1 | jlt_dict_v19.0.xml | 1,109,506 | `260aa7b173d44de2adbfec83e85ccd985060352c` | 2259910321725 |
| 2 | jlt_dict_v19.0_utf8.csv | 557,638 | `a5784d7c0cfafce1d2712102a245ee5660603caa` | 2259902010075 |
| 3 | jlt_dict_v19.0_sjis.csv | 449,610 | `e5789b861edb474e7c7ec290ffe8c946330e8ec5` | 2259988448871 |
| 4 | jlt_dict_v19.0.pdf | 2,669,002 | `5103b9f8a4e29d2e76ccdf03be9abdf1ee5aba01` | 2259989540509 |
| 5 | jlt_law.dtd | 13,839 | `946123bad374a5d4e53c79836d376a66275b7065` | 2259939455302 |
| 6 | jlt_dict.dtd | 753 | `6e3d300e8c0d4a402de2cffd33a04a240e3d9a4f` | 2259955410012 |
| 7 | _snapshot_download_page_20260526.html | 18,176 | `8ae7d7c292cfa3e722c4f799df19eef912cd7fba` | 2259933129358 |
| 8 | _snapshot_dtd_page_20260526.html | 12,242 | `0f94020ed31bc1022f05c09208848904f1d5f837` | 2259993203444 |

- **権威リスト構築の入力**: `jlt_dict_v19.0_utf8.csv`（file_id **2259902010075**）。
- SJIS CSV(#3) は raw bytes で byte-exact 着地（cp932 再エンコード破損を回避）。

## 不変条件（遵守確認）

- v18 `dict_v18_xml.xml`（370003701279 直下, sha1 2b065c11…）= **無改変**。
- ローカル source `H:\work\jlt_v19_dl\` = 無改変（upload 前後で size+sha1 再検証）。
- クラッシュ初回の部分フォルダ(386442812947, 中身=xml のみ)は clean run 前に削除 → 孤児ゼロ。最終正典は 386440014344 のみ。
- token/key の値はいかなる出力にも非掲載。

## 記録（Box・ローカル・codex の三重）

- Box 報告: `cc_report_jlt_v19_step1_LANDED_VERIFIED_20260602.md`（file_id 2259924654125, docs/alo）。
- standup: amendment `_ALO_STANDUP_20260602_amendment_jlt_v19_step1_landed_verified.md`（file_id 2259914836782）。
- ローカル: `_acquisition_log_20260526.md` に landing セクション append。

## 次工程（本タスク範囲外・cloud 側）

- `jlt_dict_v19.0_utf8.csv`(2259902010075) のヘッダ確認 → 見出し語の権威リスト生成（決定的）→ 有斐閣⟷学陽 2辞書相互突合のスカフォルド。
