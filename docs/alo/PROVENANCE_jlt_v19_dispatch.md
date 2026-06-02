# Provenance — JLT v19.0 dispatch coordination (codex mirror)

このフォルダの mirror は **Box が正本（SoT）**。本リポジトリ（Project-codex）は版管理用ミラー。
内容が食い違った場合は Box 側を真とする。

## 正本（Box, folder `docs/alo` = folder_id 372503394965）

| 役割 | ファイル名 | Box file_id | sha1 | size | created_at (UTC) |
|------|-----------|-------------|------|------|------------------|
| 親 order | `cc_order_jlt_v19_box_transport_20260601.md` | `2257628721136` | `c52327151e2527e6b54dbab4607eb9f53bf74436` | 6,179 B | 2026-06-01T12:23:27Z |
| dispatch v1 (gate のみ) | `cc_dispatch_jlt_v19_step0_20260601.md` | `2257948885398` | `7b970b2fa3661e6e2b21ab075e58501abaf0a14b` | 1,920 B | 2026-06-01T15:57:17Z |
| Step 0 報告 (v1, BLOCKED) | `cc_report_jlt_v19_step0_20260601.md` | `2258570269989` | `09b974d9e8d02bbf34abb0c3c9da5b6663174302` | 4,310 B | 2026-06-02T00:01:14Z |
| standup amendment 013 | `_ALO_STANDUP_20260601_amendment_013_claudecode_web_jlt_v19_step0_envmismatch.md` | `2258594590828` | `7a07457190b677df3d288a8e58d7a7a44726ed21` | 866 B | 2026-06-02T00:01:19Z |
| **dispatch v2 (機体ガード付き)** | `cc_dispatch_jlt_v19_step0_v2_20260602.md` | `2258787836914` | `6ab9826ac9def6d941f429063b73cf2bedfcb524` | 3,403 B | 2026-06-02T01:58:21Z |

- すべて `itemStatus: active`、作成者 `asai@asai-lo.com`。
- Box path: `すべてのファイル / 浅井 / claude / 事務所内本棚DX化計画 / docs / alo`。

## ループ記録（実在確認済み・幽霊参照なし。すべて Box API 直読みで検証）

1. **dispatch v1 発行 → 誤着弾。** windows 宛 dispatch が Linux web セッション（`claudecode_web`）に着弾。
   原因 = dispatch に実行機アサーションが無く、Box ファイルを読めた agent なら誰でも実行に入れる構造だった。
2. **web セッションは正しく折れた（合格挙動）。** golden 8点不在のため hash/size は算出不能。
   ここで値を**捏造せず**「測定不能を測定不能として申告」し、gate を維持して Step 1 を撃たず停止。
   → 親 order §1-1 の cp932 サイレント破損と同一クラスの事故を整合性の起点で自作するのを回避した。
3. **head による鍛え直し → dispatch v2 発行。** v1 の根本原因（宛先ガード不在）を潰すため、
   先頭に `Step -1 実行機アサーション`（`Test-Path 'H:\work\jlt_v19_dl\'` / hostname / OS / golden 8点実在）を追加。
   1つでも偽なら Step 0 に入らず1行報告で即停止。Step 0 には Windows 具体コマンド
   （`Get-FileHash -Algorithm SHA256` / `(Get-Item).Length`）と acquisition_log 既記録の優先転記を明記。

## ゴーサイン（v2。claude-code-windows へ。これ一言だけ）

> Box の `cc_dispatch_jlt_v19_step0_v2_20260602.md`（file_id 2258787836914）を読んで実行せよ。

- **v1（file_id 2257948885398）はもう撃たない**（v2 が supersede）。
- 発火タイミングは INC-2026-04-22-001 の backfill 完走後を推奨。Step 0 は read+hash+text のみで
  重 I/O 転送を含まないため割り込みでもほぼ競合しない。
- v2 は web/Mac に誤着弾しても Step -1 で機械的に即停止する（今回のように丁寧に折れるのを待たない）。

## 次工程（head 側）

1. claude-code-windows が v2 を実行 → Step -1 通過 → Step 0 報告（`cc_report_jlt_v19_step0_v2_*.md`）を docs/alo に upload + standup append。
2. head が Box から直読みして Step 1 経路を確定（0-1 の資格情報有無で boxsdk / Box Drive / 浅井さん手動 に分岐）。
3. 次 dispatch（Step 1 transport）を同様に Box へ格納。
