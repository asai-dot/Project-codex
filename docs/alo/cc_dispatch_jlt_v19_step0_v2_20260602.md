# cc_dispatch: JLT v19.0 — Step 0 のみ実行（claude-code-windows 手渡し・自己完結版）

- dispatch_id: cc_dispatch_jlt_v19_step0_v2_20260602（etag1: windows 手渡し用に自己完結化）
- 宛先: claude-code-windows（`H:\work\jlt_v19_dl\` を保持する Windows scrape 機 **のみ**）
- issued_by: claude.ai (head agent)
- 親 order: cc_order_jlt_v19_box_transport_20260601.md（Box file_id 2257628721136）
  ※要点は本文 §A に内包。**Box を読めなくても本ファイル単体で Step 0 を実行できる。**
- supersedes: cc_dispatch_jlt_v19_step0_20260601（Box file_id 2257948885398）
  - 却下理由: 実行機アサーション不在で windows 宛 dispatch が Linux web セッション（claudecode_web）に誤着弾。
    当該セッションは hash/size を捏造せず BLOCKED 申告で正しく停止（報告 cc_report_jlt_v19_step0_20260601.md / standup amendment_013）。
- 発火条件: 浅井先生のゴーサイン。INC-2026-04-22-001 backfill との重 I/O 競合回避のタイミングは浅井先生判断。

---

## この指示文の使い方（最初に読む）

- **このファイル1枚を Claude Code Windows に渡せば実行できる。** 親 order を Box から取りに行く必要はない（必要な要点は §A）。
- 本 dispatch の範囲は **Step 0（環境申告）のみ**。やるのは read + hash + text report **だけ**。
  フォルダ作成・byte 転送・upload などの**不可逆操作・転送は一切するな**（それは head の Step 1 routing 後）。

---

## §A. 背景（親 order の要点・Step 0 を正しく行う最小限）

- 目的: `H:\work\jlt_v19_dl\` の JLT v19.0 golden 8点を、後工程で Box 正典
  （05＿語彙レイヤー folder_id 370003701279 配下に新規 `jlt_v19_0`）へ **byte-exact** 格納する。本 Step 0 はその前段の環境申告のみ。
- 整合性の核: **取得時 SHA-256 == landing 後 SHA-256 の全件一致**で初めて「格納完了」。
  だから Step 0 で確定する**取得時 hash が後工程の基準値**になる。
- **禁止: 値の捏造。** 測れない／無い物は「無い」と書く。捏造は cp932 サイレント破損級の事故を基準値に仕込む行為。
- 8点（参考）: 辞書XML / CSV(UTF-8) / CSV(SJIS) / PDF / Law DTD / Dict DTD / dtdページHTML snapshot（＋ acquisition_log）。
  ※CSV(SJIS) は SJIS バイト列であること自体が価値。後工程でも再エンコード禁止（Step 0 では触らない）。

---

## Step -1 — 実行機アサーション（最初に必ず実行。1つでも偽なら即停止・1行報告のみ）

PowerShell:
```powershell
Test-Path 'H:\work\jlt_v19_dl\'
$env:COMPUTERNAME
[System.Environment]::OSVersion.VersionString
Get-ChildItem 'H:\work\jlt_v19_dl\' -File | Select-Object Name, Length
```
- `Test-Path` が False ／ Windows でない ／ golden 8点が無い のいずれか →
  「**当機は本 dispatch の宛先機ではない**（hostname=… / Test-Path=… / OS=…）」と1行だけ報告して**即停止。Step 0 に入るな。**
- hash/size を捏造して Step 0 を“完了”に見せかけるのは厳禁（§A 参照）。

---

## Step 0 — 環境申告（Step -1 を全通過した場合のみ）

### 0-1. Box 書込手段の有無（**当機について**。有無だけ。在処・トークン値は書くな）
- boxsdk JWT app / developer token が当機に在るか。
- Box Drive 導入の有無 / 同期対象フォルダ名。

### 0-2. 取得8点の取得時 SHA-256
- **まず `acquisition_log` に既記録があるか確認**し、あればそれを転記（再計算ドリフト回避）。
- 未記録なら算出して `acquisition_log` に追記:
```powershell
Get-ChildItem 'H:\work\jlt_v19_dl\' -File | ForEach-Object {
  [pscustomobject]@{
    Name   = $_.Name
    Bytes  = $_.Length
    SHA256 = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
  }
} | Format-Table -AutoSize
```

### 0-3. 各ファイルの実バイトサイズ
- 上の `Bytes`（= `(Get-Item <file>).Length`）で8点分。PDF・XML が想定内かの確認用。

---

## 報告先（Box 書込可否で2系統に分岐）

- **A) Box 書込手段あり**（0-1 が「有」）→
  docs/alo（folder_id 372503394965）へ `cc_report_jlt_v19_step0_v2_<YYYYMMDD>.md` を upload ＋
  当日の `_ALO_STANDUP` ファイルへ amendment パターンで1行 append（DD-COORD-001 §9）。
- **B) Box 書込手段なし**（0-1 が「無」。← 想定本命）→
  1) ローカルに `H:\work\jlt_v19_dl\cc_report_jlt_v19_step0_v2_<YYYYMMDD>.md` として保存し、
  2) **同レポート全文をこのセッションの出力にも貼れ**（浅井先生 / head が Box へ中継する）。
- どちらでも **Step 1 以降は実行しない**。

---

## gate / 安全

- Step 0 の完了 ＝ 報告（A: upload ／ B: ローカル保存＋全文出力）まで。転送本体は **head の Step 1 routing 後にのみ**実行。
- 本 dispatch の範囲は read + hash + text report のみ。不可逆操作なし。
- §A / 本指示への設計上の疑義は、報告内に [query] として併記し、走り続けず止まること。
