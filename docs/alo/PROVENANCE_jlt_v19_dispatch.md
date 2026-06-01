# Provenance — JLT v19.0 dispatch coordination (codex mirror)

このフォルダの2点は **Box が正本（SoT）**。本リポジトリ（Project-codex）は版管理用ミラー。
内容が食い違った場合は Box 側を真とする。

## 正本（Box, folder `docs/alo` = folder_id 372503394965）

| 役割 | ファイル名 | Box file_id | sha1 | size | created_at (UTC) |
|------|-----------|-------------|------|------|------------------|
| dispatch (Step 0 gated) | `cc_dispatch_jlt_v19_step0_20260601.md` | `2257948885398` | `7b970b2fa3661e6e2b21ab075e58501abaf0a14b` | 1,920 B | 2026-06-01T15:57:17Z |
| 親 order | `cc_order_jlt_v19_box_transport_20260601.md` | `2257628721136` | `c52327151e2527e6b54dbab4607eb9f53bf74436` | 6,179 B | 2026-06-01T12:23:27Z |

- 両ファイルとも `itemStatus: active`、作成者 `asai@asai-lo.com`。
- Box path: `すべてのファイル / 浅井 / claude / 事務所内本棚DX化計画 / docs / alo`。

## 検証（2026-06-01, head agent による Box 直読み）

- **実在確認済み・幽霊参照なし**: 上記2 file_id は Box API `get_file_details` で active 実在を確認。
- dispatch 本文は次の gate を内蔵することを確認:
  - **Step 0（環境申告）のみ実行し停止**。Step 1 以降（フォルダ作成・byte 転送・upload）は head の Step 1 routing 後にのみ実行。
  - 報告先は **docs/alo へ `cc_report_jlt_v19_step0_<YYYYMMDD>.md` upload ＋ standup へ1行 append**。
  - 本 dispatch の範囲は **read + hash + text report のみ。不可逆操作なし**。
- 親 order（file_id 2257628721136）の参照は dispatch 本文・本ミラーともに一致。

## ゴーサイン（claude-code-windows へ。これ一言だけ）

> Box の cc_dispatch_jlt_v19_step0_20260601.md（file_id 2257948885398）を読んで実行せよ。

- 発火タイミングは INC-2026-04-22-001 の backfill 完走後を推奨。ただし Step 0 は read+hash+text のみで
  重 I/O 転送を含まないため、割り込み実行でも backfill とほぼ競合しない。

## 次工程（head 側、本セッションの担当外）

1. claude-code-windows が Step 0 報告（`cc_report_jlt_v19_step0_*.md`）を docs/alo に upload。
2. head が Box から直読みして Step 1 経路を確定（資格情報の有無で boxsdk / Box Drive / 手動に分岐）。
3. 次 dispatch を同様に Box へ格納。
