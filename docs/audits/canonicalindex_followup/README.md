# canonicalindex DDINDEXDISPO フォローアップ草案

GPT お目付け役 verdict `20260607_canonicalindex_v0.1_DDINDEXDISPO_RESULT.md`
（Box `2270473891101`, **DDINDEXDISPO_PASS_WITH_NOTES**, 2026-06-07 15:02 JST）に基づく **草案**。

> ⚠️ これは草案であり、**Box への書き込み・accepted 化（ratify）は未実施**。浅井先生の承認後に適用する。

## 採用方針（GPT verdict (二)）

`ALO_CANONICAL_INDEX_20260605` を延命せず、per-artifact 状態 SoT を design_decisions Generated Index に一本化する。
ただし「触らない」では止めず、以下2点を同時に行う:

1. index 側を **superseded / historical snapshot** として退役（**削除禁止**・full refresh も部分追記もしない）
2. accepted 済 `DD-STATUS-REGISTRY-001 v0.2` の §5.3 を inline 改変せず、**v0.2.1 narrow pointer patch** を新版で作る

## 適用手順（承認後）

| # | 操作 | 対象 | 種別 | 草案 |
|---|---|---|---|---|
| 1 | superseded marker を**先頭に prepend**（本文は不変） | `ALO_CANONICAL_INDEX_20260605.md` (Box `2266253855296`) | Box 編集（要承認） | `ALO_CANONICAL_INDEX_20260605_superseded_header.md` |
| 2 | v0.2.1 SoT pointer patch を**新規作成** | 新 `DD-STATUS-REGISTRY-001_v0.2.1_SOT_POINTER_PATCH.md` | Box 新規（要承認） | `DD-STATUS-REGISTRY-001_v0.2.1_SOT_POINTER_PATCH.md` |
| 3 | v0.2.1 を **ratify → accepted** | 同上 | 浅井先生判断 | — |
| 4 | 以後の per-artifact 状態 SoT を design_decisions Generated Index に固定 | 運用規約 | — | — |

GPT 制約の再掲: accepted v0.2 本文は触らない / index は full refresh・部分追記しない / index は削除せず historical として残す / v0.2.1 は本 DDINDEXDISPO_RESULT を independent audit として引用し、diff 確認後に owner ratify。

---

## 記録: queueaudit loop レビュー（報告のみ・未対応）

別途 `20260608_queueaudit_loop_GPTQUEUE_REVIEW_RESULT.md`（Box `2270920897721`, GPT-5.5 Pro, **GPTQUEUE_MODIFY_REQUIRED**）が返却済み。
本フォローアップの**対象外**（浅井先生の指示により報告のみ・実装着手しない）。要求概要のみ記録:

- `_AUDIT_LEDGER.jsonl` + action-queue の実体化（P0/blocking）
- `to_gpt/` 直下 `.processed.md` の物理退避 or 厳格除外（P1）
- from_gpt RESULT 群の `next_action_type` / `owner_digest_5line` / `claude_rethink_prompt` backfill
- dry-run/apply/idempotency ログ添付で再投函（別途 `GPTAUDITLOOP_IMPL` 起票）

※ 着手判断は保留。実装すると当初タスクの禁止事項（Box 移動・台帳化）と衝突するため、別途承認が要る。
