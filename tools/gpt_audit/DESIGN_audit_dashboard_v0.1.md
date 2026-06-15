# DESIGN — 人とAIが一緒に見る監査ダッシュボード v0.1（設計メモ）

- date: 2026-06-15 JST
- status: **design memo only**（実装なし・Supabaseへの適用なし）
- author: Claude Code（番頭代行）
- basis: 本スレの実作業（`alo-gpt-audit` 実装＋実Box退避16件）と Owner 決定
- owner_decision (2026-06-15): 基盤 = **Supabase 連携（ライブ共有状態）** / 着手 = **設計メモ先行**
- 正本: GPT_PRO_AUDIT_LOOP_RULE v0.1 / LANE_DESIGN v0.3 / APPROVAL_RULE v0.1
- companion: `tools/gpt_audit/alo_gpt_audit.py`（状態生成エンジン）, `_GPT_AUDIT_BOARD.md`（現行軽量板）

---

## 0. 目的（なぜ作るか）

> 人と AI が**同じ画面を見ながら**監査を進める環境を作る。

現状、監査レーンの状態が **4 か所に分散**している：

| # | 状態の在処 | 性質 | 問題 |
|---|---|---|---|
| 1 | Box フォルダ位置（to_gpt / processed） | 物理的な正（SoT） | 機械可読だが一覧性が低い |
| 2 | `_GPT_AUDIT_BOARD.md` | 軽量・手動 | 人手更新。AI の自動反映と乖離する |
| 3 | `_AUDIT_LEDGER.jsonl` | 派生控え | 実質放置・古い |
| 4 | タグ / `00_QUEUE_CLEANUP_INDEX` | move 不能の代替策 | 「未済に見えない」だけで実体と乖離 |

この分散が「監査結果が返っても反映されない」「人が今何を見ればいいか分からない」の
根本原因。**1 つの再生成可能なライブ状態**へ畳む。

### 非目的（やらないこと）
- 監査の**判断自体**を自動化しない（PASS/accepted の決定は従来通り）。
- **守秘情報（実案件・依頼者データ）はダッシュボードに載せない**（§7）。設計・監査メタのみ。
- 既存の承認ゲート（accepted化・本番DB・SF・外部送信）を緩めない。ダッシュボードは
  「見える化」であって「承認のバイパス」ではない。

---

## 1. 全体像

```text
            ┌──────────────────────────────────────────────┐
   物理SoT  │ Box gpt_ometsuke/  (to_gpt / processed / from_gpt) │
            └───────────────┬──────────────────────────────┘
                            │ (1) ingest / reconcile
                            ▼
        ┌───────────────────────────────────────────┐
        │ alo-gpt-audit  (状態生成エンジン)            │
        │  status / action-queue / health → 正規化レコード │
        └───────────────┬───────────────────────────┘
                        │ (2) upsert（差分のみ）
                        ▼
        ┌───────────────────────────────────────────┐
        │ Supabase  (ライブ共有状態 = 単一ビュー)       │
        │  tables + views + RLS + Realtime            │
        └──────┬──────────────────────────┬─────────┘
        (3a) 人 │ Web UI（閲覧/owner決定）   │ (3b) AI（MCP で読み書き）
               ▼                            ▼
            浅井先生                      Claude / GPT Pro lane
```

- **物理 SoT は Box フォルダ位置のまま**（LANE_DESIGN の不変条項）。Supabase は
  「派生ライブビュー」。両者が食い違ったら **Box が勝つ**（reconcile で上書き）。
- 書き込み主体を分離：機械的な状態（loop_state 等）は AI/CLI、**owner 判断**は人が UI。

---

## 2. データモデル（案）

語彙は LANE_DESIGN v0.3 §A に従い **runtime/pipeline 状態**と **artifact lifecycle**
を別列に保つ（混同禁止）。

### 2.1 `audit_request`
| col | type | 例 / 備考 |
|---|---|---|
| request_id | text PK | `20260613_litid_O1_..._DDLITID` |
| topic | text | `litid` |
| gate | text | `DDLITID` |
| request_status | text | `queued/blocked/superseded/cancelled`（runtime, 非lifecycle） |
| lane_status | text | `active/answered_not_processed/missing_result/bad_label/processed` |
| box_file_id | text | Box item id |
| box_location | text | `to_gpt` / `to_gpt/processed` |
| result_expected_filename | text | 三点照合キー |
| source_hash | text | unresolved 検出 |
| created_at / updated_at | timestamptz | |

### 2.2 `audit_result`
| col | type | 備考 |
|---|---|---|
| result_id | text PK | result filename か box_file_id |
| request_id | text FK | |
| result_label | text | `<GATE>_<VERDICT>` |
| verdict | text | 正規化 5 値 |
| next_action_type | text | `ratify/patch/required_materials/reject/none` |
| ratify_required / requeue_expected | bool | |
| need_more_type | text | §E 細分 |
| blocking_before_ratify | jsonb | |
| missing_materials | jsonb | |
| owner_digest_5line | text | |
| claude_rethink_prompt | text | |
| reviewed_at | timestamptz | |

### 2.3 `audit_event`（= 台帳 `_AUDIT_LEDGER.jsonl` の正規化先, append-only）
| col | type | 備考 |
|---|---|---|
| event_id | bigint PK | |
| ts | timestamptz | |
| event | text | `close/route/reflect` |
| request_id | text | |
| loop_state | text | `returned/reflected/requeued/ratify_wait/closed` |
| reflected | bool | |
| actor | text | `cli/claude/gpt_pro/owner` |
| payload | jsonb | 監査証跡 |

→ `_AUDIT_LEDGER.jsonl` は **このテーブルの export 控え**として残す（可搬性・オフライン）。

### 2.4 `audit_hold`（= `_GPT_AUDIT_BOARD.md` §1 Holds を構造化）
| col | type | 例 |
|---|---|---|
| topic | text PK | `D1HAN` / `NEWSOURCES` |
| db_ddl / mcp / embedding / production | text | `HOLD` / `report-only` 等 |
| note | text | |
| updated_by / updated_at | | |

### 2.5 `owner_decision`（人が UI で書く唯一の必須テーブル）
| col | type | 備考 |
|---|---|---|
| decision_id | bigint PK | |
| topic / request_id | text | |
| kind | text | `ratify / hold_release / priority / reject_confirm` |
| decision | text | `approved/denied/deferred` |
| decided_by | text | `owner` |
| decided_at | timestamptz | |
| rationale | text | |

### 2.6 派生ビュー（VIEW / Realtime 購読対象）
- `v_action_queue` — `reflected=false AND loop_state<>'closed'`、緊急度順。**AI の To-Do**。
- `v_owner_inbox` — `next_action_type='ratify' OR kind='ambiguity_owner' OR hold pending`。**人の To-Do**。
- `v_lane_health` — lane_status 集計 / 未反映数 / queue サイズ（`health` 相当）。
- `v_holds` — 現在の HOLD 一覧（本番/DDL/MCP/外部の赤信号）。

---

## 3. 同期モデル（Box ↔ Supabase）

**一方向 ingest ＋ 限定 write-back** にして競合を避ける。

| 流れ | 方向 | 主体 | 内容 |
|---|---|---|---|
| ingest | Box → Supabase | CLI/AI | フォルダ走査→ `audit_request/result/event` を upsert（差分のみ） |
| owner決定 | UI → Supabase | 人 | `owner_decision` 追記 |
| 反映 | Supabase → Box | AI（要承認判定） | owner_decision を受けて patch/退避/ratify を実行し、結果を再 ingest |

**鉄則**：Supabase の行を編集しても Box は動かない。Box を動かすのは従来どおり
CLI/AI の物理操作だけ。Supabase は「指示・可視化」、Box は「実体」。reconcile で
不整合は Box 優先で解消。

---

## 4. 承認ゲートの DB 表現（APPROVAL_RULE を緩めない）

| 操作 | 承認 | DB での扱い |
|---|---|---|
| RESULT保存 / processed退避 / event追記 / queue更新 | 不要 | AI/CLI が直接 upsert 可 |
| accepted/canonical 化 | **必要** | `owner_decision(kind=ratify, approved)` が無いと lifecycle 列を進められない（RLS/トリガで強制） |
| index backfill / 本番DB / SF / 外部送信 | **必要** | `audit_hold` が `HOLD` の間は対応アクションを UI/AI 双方でブロック |

→ ダッシュボードは「赤信号（HOLD / ratify未）」を**機械的に可視化・強制**する層になる。

---

## 5. RLS / 権限（人とAIの書き分け）

- `owner` ロール：全テーブル read、`owner_decision` write、`audit_hold` write。
- `agent`（AI/MCP）ロール：`audit_request/result/event` upsert、全 view read、
  **`owner_decision` は read only**（人の判断を AI が捏造できない）。
- lifecycle 昇格列は **トリガで `owner_decision` 必須**にし、agent からの直接更新を拒否。

---

## 6. 段階導入（phased）

| Phase | 内容 | リスク | 価値 |
|---|---|---|---|
| **P0** ミラー（read-only） | ingest のみ。Supabase は Box の鏡。UI は閲覧専用。 | 低（Box 不変） | 分散解消・一覧性 |
| **P1** owner_inbox | `owner_decision` を UI で受ける。AI はそれを読んで Box 反映。 | 中（権限設計） | 人の判断が構造化される |
| **P2** write-back 自動化 | owner決定→AI が patch/退避/ratify準備まで自動化。 | 中 | ループが UI で回る |
| **P3** Realtime 協働 | 同一画面を人/AI が同時に見て更新（Realtime購読）。 | — | 当初ビジョン達成 |

各 Phase は前 Phase が安定してから。P0 は Box を一切変えないので安全に始められる。

---

## 7. セキュリティ / 守秘（最重要）

- ダッシュボードに載せるのは **設計・監査メタデータのみ**（request_id, label, verdict,
  next_action, hold 等）。**実案件・依頼者・本文の機微は載せない**。
- RESULT 本文は載せず **Box への参照（file_id / link）だけ**を持つ（本文は Box で読む）。
- Supabase の anon/public 公開は不可。`agent`/`owner` ロールと RLS で閉じる。
- これは `_GPT_AUDIT_BOARD.md` の `data_separation` / confidential 原則の継承。

---

## 8. 既存資産との関係

- `alo-gpt-audit` CLI は**捨てない**。むしろ Supabase ingest の**生成エンジン**になる
  （`status`/`action-queue`/`health` の出力 = upsert ペイロード）。`--emit json` を足す
  程度の拡張で接続できる。
- `_GPT_AUDIT_BOARD.md` は P0〜P1 の間、**人間向けの可読控え**として併存。最終的に
  `v_holds` / `v_owner_inbox` がそれを置換。
- Box フォルダ位置は **永続的に SoT**。Supabase はいつ落ちても Box から再構築できる。

---

## 9. Owner に決めてほしいこと（次フェーズの入口）

1. Supabase は**専用プロジェクト**を新設するか、既存（dynamic/static DB）と分けるか。
   → 守秘の観点では **監査メタ専用プロジェクト分離**を推奨。
2. UI は何で出すか（Supabase Studio で十分か / 最小 Web か）。P0 は Studio 閲覧で可。
3. `agent` ロールの書込範囲（P0 は ingest のみ＝最小から）。

---

## 10. 結論

> 物理 SoT は Box フォルダのまま。その上に **Supabase をライブ派生ビュー**として載せ、
> **人は owner_decision を、AI は状態を**書く。承認ゲートと守秘は DB の RLS/トリガで
> 機械的に強制する。`alo-gpt-audit` を ingest エンジンに、`_GPT_AUDIT_BOARD.md` を
> 移行期の可読控えにして、P0 ミラー（Box 不変）から安全に始める。

本メモは設計のみ。実装・Supabase 適用は次の Owner ゴーで着手する。
