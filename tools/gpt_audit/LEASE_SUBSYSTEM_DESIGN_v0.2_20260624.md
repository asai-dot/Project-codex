# LEASE_SUBSYSTEM_DESIGN v0.2 — mutating レーン解禁の最小設計

- status: **draft (未ratify・未実装)** — 監査 gate 用（v0.1 MODIFY_REQUIRED への patch）
- date: 2026-06-24
- 前段: `LEASE_SUBSYSTEM_DESIGN_v0.1`（result 2304096222240, **MODIFY_REQUIRED**,
  v0.2 patch GO / 実 mutate HOLD）
- 上位: `HANDOFF_SCHEMA_APPENDIX_v0.5` §4.4（mutating ∧ no lease → block）,
  `HANDOFF_OPERATIONAL_IMPL_DESIGN_v0.1`（non_mutating レーン運用中・flag 既定 off）
- 目的: fail-closed で全 block 中の **mutating レーン**を、**lease（占有権）**付きで
  **dispatch 可判定まで**解禁する。実 mutate 実行・external は範囲外（別 gate）。

## v0.1 → v0.2 差分（must_fix 対応表）

| # | v0.1 の穴 | v0.2 の手当て | 反映節 |
|---|---|---|---|
| 1 | grant/release 自体が書込みなのに「承認不要事務」扱いが甘い | ledger 書込み安全境界を固定（path/create_new/append-only/hash chain） | §1.1 |
| 2 | target_key が path 文字列のみで抜け道 | `canonical_target_key`（stable id 優先 / path は正規化必須） | §1.2 |
| 3 | holder=assignee+machine で弱い | holder = assignee + machine_id + runner_id/session_id の合成 | §1.3 |
| 4 | TTL 未定義（無期限可） | 既定 15–30 分 / 上限 2h / 無期限禁止 / 延長は新発行 | §1.4 |
| 5 | scope 単一文字列・prefix 一致で緩い | scope は set 正規化・完全一致のみ（prefix 禁止） | §1.5 |
| 6 | 二重 active 発行の検出なし | 同一 (canonical_target_key, scope) で active 複数 → 全 block | §3 gate G8 |

---

## 0. 現状（解禁前）

`validator.validate_dispatch` は §4.4 で:

```
mutation == "mutating" and not env.lease_subsystem_available → block("lease_required_but_unavailable")
```

`Env.lease_subsystem_available` 既定 `False`、運用ツールは素の `HandoffEnv()` を渡すため
mutating は例外なく block。安全だが一切進まない。boolean しか見ないため「誰が・何を・
いつまで」を検証できない。解禁にはリース実体検証が要る。

---

## 1. lease record（v0.2 定義）

ある **mutation target** に対する **時間制限つき・単一書き手の占有権**。append-only に
発行・解放する。

| field | 意味 |
|---|---|
| `lease_id` | 一意 id（発行時刻 + counter, 衝突時 block） |
| `canonical_target_key` | §1.2 で正規化した占有対象キー |
| `holder` | §1.3 の合成識別子 |
| `granted_at` / `expires_at` | JST ISO8601。`expires_at` 必須・無期限禁止（§1.4） |
| `scope` | §1.5 の正規化 scope set |
| `state` | `active` / `released` / `expired` |
| `prev_hash` / `record_hash` | §1.1 の hash chain |

### 1.1 ledger 書込みの安全境界（must_fix #1）

- ledger は単一固定 path の append-only JSONL（`gpt_audit/handoff_proto/_LEASE_LEDGER.jsonl`）。
  path は設定で固定し、実行時に外から差し替え不可。
- 書込みは **追記のみ**。既存レコードの mutate-in-place・truncate・上書きを一切禁止。
- ファイル作成は **create-new（no-overwrite）**。既存ファイルへの再 create は失敗させる。
- 各レコードに `prev_hash`（直前レコードの `record_hash`）と自身の `record_hash`
  （正規化 JSON の sha256）を持たせ **hash chain** を成す。検証時にチェーン不整合
  （prev_hash 断絶・record_hash 不一致）を検出したら **全 block**（`lease_ledger_tampered`）。
- grant/release はこのチェーンへの 1 追記で表現。これにより「監査の帰り便」と同じ
  承認不要事務に収まる根拠（不可改ざん・単一 path・追記限定）を満たす。

### 1.2 canonical_target_key（must_fix #2）

占有対象は**安定 ID を最優先**でキー化する。

- Box object は `box:file:{file_id}` / `box:folder:{folder_id}`（path でなく stable id）。
- ローカル path しか無い場合は `path:{normalized}` とし、正規化は必須:
  realpath 解決（symlink 展開）→ Unicode **NFC** → OS 規約に応じた case 畳み込み →
  trailing slash 除去 → 区切り正規化。正規化に失敗・曖昧な場合は **block**
  （`target_key_unnormalizable`）。
- packet 側 `lease_ref.target_key` も同じ正規化を通してから比較する（正規化前の生文字列
  一致は不可）。

### 1.3 holder 合成識別（must_fix #3）

`holder = {assignee, machine_id, runner_id|session_id}` の合成。3 要素すべてを記録し、
検証は合成キー全体の一致で行う（部分一致は不可）。いずれか欠落は **block**
（`holder_underspecified`）。

### 1.4 TTL（must_fix #4）

- `expires_at` は必須。**無期限禁止**。
- 既定 TTL **15–30 分**（運用既定 30 分）、**上限 2 時間**。上限超過の grant は block
  （`lease_ttl_exceeds_max`）。
- **延長は禁止**。継続が要る場合は **新 lease 発行**（旧 lease は release または自然
  expire）。in-place な expires_at 更新は §1.1 で構造的に不可。

### 1.5 scope 正規化（must_fix #5）

- `scope` は列挙の **set**（例 `["file_move"]` / `["metadata_set","file_move"]`）。
- 許可値は固定 enum（`file_move`, `metadata_set`, …）。enum 外は block（`scope_unknown`）。
- 照合は **set membership の完全一致のみ**。**prefix 一致は禁止**（`file_*` 等の前方一致で
  広がる経路を塞ぐ）。`ref.scope` が `rec.scope` の要素として完全一致しなければ
  `lease_scope_mismatch`。

---

## 2. dispatch packet 拡張

mutating packet は `lease_ref` を必須にする:

```jsonc
{
  "next_action_type": "file_move",
  "side_effect_flags": ["file_move"],
  "lease_ref": {
    "lease_id": "LS_20260624_001",
    "target_key": "box:file:2303989218514",   // §1.2 で正規化済み
    "scope": "file_move"                        // §1.5 の enum 値
  }
}
```

`lease_ref` 無しの mutating は従来どおり block。

---

## 3. validator 拡張（§4.4 を置換・単一実装）

`Env` に `lease_subsystem_available`（既存 bool）、`lease_lookup`
（`Callable[[str], LeaseRecord | None]`）、`active_leases_for`
（`Callable[[str, str], list[LeaseRecord]]`; canonical_target_key+scope で active 列挙）、
`now`（注入時刻）を追加。新 gate（fail-closed・不明は通さない）:

```
if mutation == "mutating":
  G0  if not env.lease_subsystem_available:          → block("lease_required_but_unavailable")
  G1  ref = packet.get("lease_ref"); if not ref:     → block("lease_ref_missing")
  G2  ckey = canonicalize(ref["target_key"])
      if ckey is None:                               → block("target_key_unnormalizable")
  G3  rec = env.lease_lookup(ref["lease_id"])
      if rec is None:                                → block("lease_not_found")
  G4  if not ledger_chain_ok(rec):                   → block("lease_ledger_tampered")  # §1.1
  G5  if rec.state != "active":                       → block("lease_inactive")
  G6  if env.now > rec.expires_at:                    → block("lease_expired")
  G7  if rec.canonical_target_key != ckey:            → block("lease_target_mismatch")
  G8  scope = normalize_scope(ref["scope"])
      if scope is None:                               → block("scope_unknown")
      if scope not in rec.scope:                       → block("lease_scope_mismatch")  # 完全一致のみ
  G9  if rec.holder != compose_holder(packet):        → block("lease_holder_mismatch")
      if any(part missing in rec.holder):             → block("holder_underspecified")
  G10 actives = env.active_leases_for(ckey, scope)    # §3 二重発行検出 (must_fix #6)
      if len(actives) > 1:                            → block("lease_double_active")
      if len(actives) == 1 and actives[0].lease_id != rec.lease_id:
                                                       → block("lease_double_active")
      # ここまで通れば mutating dispatchable（唯一の許可ケース）
```

検証は `handoff_proto/validator.py` の **単一実装**に追加し、運用ツールは import のみ
（operational v0.1 must_fix #3 を継続）。

---

## 4. 運用ツール側

- 新コマンド `handoff-lease`（`grant` / `release` / `list`）。発行・解放は §1.1 の
  append-only + hash chain で追記。`grant` は同一 (canonical_target_key, scope) に active が
  既に在れば失敗（二重 active を作らせない；G10 と二重防御）。
- `handoff-validate` は flag on のとき `Env` に lease subsystem を結線して mutating を検証。
  **flag は引き続き既定 off**（operational must_fix #4 継続）。
- mutating dispatch card は `handoff_queue/` に出すが **実 mutate は実行しない**。card は
  「占有確認済み・実行可」の証跡で、実行は別レーン（worker）に委ねる。

---

## 5. スコープ境界（解禁する / しない）

**解禁する**: ローカル / Box 内 mutating（file_move・metadata_set 等）を、有効リース下で
**dispatch 可** と判定すること（card 生成まで）。

**解禁しない（HOLD 継続）**: paid/quota call、confidential egress、外部送信、本番 DB・DDL、
accepted/canonical 化、SF 書戻し、自動実行（card→実 mutate の自動連結）。リース取得後の
**実 mutate 実行**自体も本設計の範囲外（別 gate）。

---

## 6. テスト計画（実装時）

prototype（validator）:
- mutating ∧ lease_ref 無し → `lease_ref_missing`
- 正規化不能 target → `target_key_unnormalizable`
- not_found / chain 改ざん → `lease_not_found` / `lease_ledger_tampered`
- state≠active / 期限切れ → `lease_inactive` / `lease_expired`
- target / scope(enum外・prefix) / holder(欠落含む) 不一致 → 各 block
- 同一 (target,scope) に active 2 件 → `lease_double_active`
- 全条件 OK ∧ active 1 件一致 → dispatchable（唯一の許可）
- subsystem 不在（flag off 相当）→ `lease_required_but_unavailable`

body（handoff-lease）:
- grant/release の append-only 冪等性・hash chain 連結
- 同一 (target,scope) 二重 grant の拒否
- TTL 上限超過 grant の拒否 / 無期限拒否
- flag off で lease 検証経路に入っても書き込みゼロ

---

## 7. owner への問い（残論点）

1. `canonical_target_key` の stable id 優先順位: Box は file_id/folder_id 固定で良いか。
   ローカルは realpath ベースで十分か（mount 跨ぎの同一性は範囲外で良いか）。
2. holder の `runner_id` と `session_id` はどちらを正とするか（両方記録・照合は session_id 優先で可か）。
3. 既定 TTL は 30 分・上限 2h で確定して良いか。
4. v0.1 同様、v0.2 も「dispatch 可判定まで」で切り、実 mutate は次 gate で良いか（再確認）。
