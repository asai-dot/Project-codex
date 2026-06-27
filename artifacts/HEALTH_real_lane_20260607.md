# 監査レーン health report — 実レーン観測スナップショット

- generated_at_jst: 2026-06-07
- source: Box `gpt_ometsuke/` (folder_id 387373370306) の読み取り観測
- method: read-only (このレポートは Box を一切変更していない)
- tool: `alo-gpt-audit` の status / health ロジックを実観測値に適用

> 注: `alo-gpt-audit` は Box Drive 同期パスを root に取る fs ツール。本レポートは
> Box API 経由の観測値を同ロジックで集計した「実レーンの現況」である。Box への
> 退避・relocate は **未実施** (承認不要処理だが、実 Box への書込は別途 `--apply`
> 実行が必要)。

---

## サマリ

| 指標 | 値 |
|---|---|
| to_gpt 直下 active REQUEST (`*_REQUEST.md`) | 2 |
| └ うち answered_not_processed (要 close) | 0 |
| └ うち missing_result (GPT 未回答 / 待ち) | 2 |
| └ うち bad_label | 0 |
| 旧式 `*_REQUEST.processed.md` (要 relocate) | 2 |
| to_gpt/processed/ の REQUEST | 15 |
| from_gpt/ の RESULT | 18 |
| _AUDIT_LEDGER.jsonl | 存在 (4356 bytes) |

## to_gpt 直下 active REQUEST 内訳

| request_id | gate | lane_status | 理由 |
|---|---|---|---|
| 20260607_lawtime_v0.2_DDLAWTIME | DDLAWTIME | missing_result | from_gpt に v0.2 RESULT 未着 (あるのは v0.1) |
| 20260607_toclegalref_v0.2_DDTOCLEGALREF | DDTOCLEGALREF | missing_result | from_gpt に v0.2 RESULT 未着 (あるのは v0.1) |

→ 2 件とも **GPT Pro の回答待ち**。ルール「to_gpt 直下は未回答だけ」に**適合**。

## 旧式その場退避 (relocate 推奨)

`to_gpt/processed/` サブフォルダへ移すべきだが、旧式の「その場 `.processed.md`
リネーム」で残っている 2 件。RESULT は受領済み。

| ファイル | 対応 RESULT |
|---|---|
| 20260607_codexprogress_v0.2_DDPROGRESS_REQUEST.processed.md | 20260607_codexprogress_v0.2_DDPROGRESS_RESULT.md ✓ |
| 20260607_legaldb_v0.5.1_DESIGN_REQUEST.processed.md | 20260607_legaldb_v0.5.1_DESIGN_RESULT.md ✓ |

## route queue サイズ (実 Box)

| queue | 件数 | 中身 |
|---|---|---|
| approval_queue | 0 | — |
| patch_queue | 1 | PATCH_CARD__20260607_codexprogress_v0.2_DDPROGRESS.md |
| material_queue | 0 | — |
| rejected_queue | 0 | — |
| ledger/ (補助 doc) | 2 | ROUTE_PLAN, RECONCILE note |

## health 判定: GREEN-ish (軽微 2 点)

- ✅ to_gpt 直下に answered_not_processed なし (帰り便は捌けている)
- ✅ bad_label なし
- ✅ to_gpt 直下 active は未回答 2 件のみ = ルール適合
- ⚠️ 旧式 `*_REQUEST.processed.md` が 2 件 → `to_gpt/processed/` へ relocate 推奨
- ⚠️ 未着 RESULT 2 件 (lawtime v0.2 / toclegalref v0.2) は GPT Pro 投函待ち

## 推奨アクション (すべて承認不要)

1. `alo-gpt-audit close-all --apply` を Box Drive 同期 root で実行し、今後 RESULT 着
   の REQUEST を `to_gpt/processed/` へ自動退避させる。
2. 旧式 `*_REQUEST.processed.md` 2 件を `to_gpt/processed/` へ relocate (one-off)。
3. lawtime v0.2 / toclegalref v0.2 は GPT Pro 監査投函を待つ (Owner の「監査を回して」
   で投函済み、回答待ち)。

## 承認が必要 (このツールは実行しない)

- DD accepted/canonical 化、Generated Index backfill、本番 DB 投入、SF 書戻し、外部送信。
