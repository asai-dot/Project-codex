# cc_dispatch: JLT v19.0 — Step 0 のみ実行（gate 付き）

- dispatch_id: cc_dispatch_jlt_v19_step0_20260601
- 宛先: claude-code-windows（H:\work\jlt_v19_dl\ を持つ機。標準命名でも可）
- issued_by: claude.ai (head agent)
- 親 order: cc_order_jlt_v19_box_transport_20260601.md（Box file_id 2257628721136）
- 発火条件: 浅井先生のゴーサインで実行。INC-2026-04-22-001 の backfill 進行中は重 I/O 競合回避のため後回し可（タイミングは浅井先生判断）。

---

## 指示（この通りに動け）

1. Box の親 order（file_id **2257628721136**）を読め。
2. **Step 0（環境申告）だけを実行し、そこで止まれ。**
   Step 1 以降（フォルダ作成・byte 転送・upload）は走らせるな。head の経路確定（Step 1 routing）を待て。
3. Step 0 で出すもの:
   - Box API 資格情報（boxsdk JWT / developer token）が当機に在るか ―― **有無だけ。在処・トークン値は書くな**
   - Box Drive 導入の有無 / 同期対象フォルダ名
   - H:\work\jlt_v19_dl\ の8点の取得時 SHA-256（acquisition_log 未記録なら今算出して追記）
   - 8点の実バイトサイズ

## 報告先（H: ローカルのみに留めるな。head が Box を直読みする）

- docs/alo（folder_id 372503394965）へ `cc_report_jlt_v19_step0_<YYYYMMDD>.md` として Box upload（text-only で足りる内容）
- standup（_ALO_STANDUP の当日ファイル）へ1行 pointer を amendment パターンで append

## gate / 安全

- Step 0 の完了 ＝ 報告 upload ＋ standup append まで。転送本体は head の Step 1 routing 後にのみ実行。
- 本 dispatch の範囲は read + hash + text report のみ。不可逆操作なし。
- 親 order に対する設計上の疑義があれば、Step 0 報告内に [query] として併記し、走り続けず止まること。
