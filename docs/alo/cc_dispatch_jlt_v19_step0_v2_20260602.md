# cc_dispatch: JLT v19.0 — Step 0 のみ実行（実行機ガード付き・v2）

- dispatch_id: cc_dispatch_jlt_v19_step0_v2_20260602
- 宛先: claude-code-windows（`H:\work\jlt_v19_dl\` を保持する Windows scrape 機 **のみ**）
- issued_by: claude.ai (head agent)
- 親 order: cc_order_jlt_v19_box_transport_20260601.md（Box file_id 2257628721136）
- supersedes: cc_dispatch_jlt_v19_step0_20260601（Box file_id 2257948885398）
  - 却下理由: 実行機アサーション不在のため、windows 宛 dispatch が Linux web セッション（claudecode_web）に誤着弾。
    当該 web セッションは hash/size を捏造せず BLOCKED 申告で正しく停止
    （報告 cc_report_jlt_v19_step0_20260601.md / standup amendment_013）。本 v2 で機体ガードを追加し再発を機械的に防ぐ。
- 発火条件: 浅井先生のゴーサイン。INC-2026-04-22-001 backfill との重 I/O 競合回避のタイミングは浅井先生判断。

---

## Step -1 — 実行機アサーション（最初に必ず実行。1つでも偽なら即停止・1行報告のみ）

1. `Test-Path 'H:\work\jlt_v19_dl\'` が **True** か。
2. 当機が Windows scrape 機か（`$env:COMPUTERNAME` と `[System.Environment]::OSVersion` を確認）。
3. golden 8点が `H:\work\jlt_v19_dl\` に実在するか（ファイル名・個数を `Get-ChildItem` で確認）。

- いずれか偽 → docs/alo へ「**当機は本 dispatch の宛先機ではない**（hostname=… / Test-Path=… / OS=…）」と1行報告して**即停止。Step 0 に入るな**。
- **hash/size を捏造して Step 0 を“完了”に見せかけるのは厳禁**（親 order §1-1 の cp932 サイレント破損と同一クラスの事故を整合性の起点で自作することになる）。v1 誤着弾時の web セッションの判断＝正。踏襲せよ。

---

## Step 0 — 環境申告（Step -1 を全通過した場合のみ）

### 0-1. Box 書込手段の有無（**当機について**）
- boxsdk JWT app / developer token が当機に在るか ―― **有無だけ。在処・トークン値は書くな**。
- Box Drive 導入の有無 / 同期対象フォルダ名。

### 0-2. 取得8点の取得時 SHA-256
- **まず `acquisition_log` に既記録があるか確認**し、あれば転記する（再計算ドリフト回避）。
- 未記録なら `Get-FileHash -Algorithm SHA256 <file>` で算出し、`acquisition_log` に追記。

### 0-3. 各ファイルの実バイトサイズ
- `(Get-Item <file>).Length` で8点分。PDF・XML が想定内かの確認用。

---

## 報告先（H: ローカルに留めるな。head が Box を直読みする）

- docs/alo（folder_id 372503394965）へ `cc_report_jlt_v19_step0_v2_<YYYYMMDD>.md` として Box upload（text-only で足りる）。
- standup（`_ALO_STANDUP` 当日ファイル）へ1行 pointer を amendment パターンで append（DD-COORD-001 §9）。

---

## gate / 安全

- Step 0 の完了 ＝ 報告 upload ＋ standup append まで。転送本体（Step 1 以降: フォルダ作成・byte 転送・upload）は **head の Step 1 routing 後にのみ**実行。
- 本 dispatch の範囲は read + hash + text report のみ。不可逆操作なし。
- 親 order に対する設計上の疑義があれば、Step 0 報告内に [query] として併記し、走り続けず止まること。
