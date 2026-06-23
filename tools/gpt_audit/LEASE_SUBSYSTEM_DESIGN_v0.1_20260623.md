# LEASE_SUBSYSTEM_DESIGN v0.1 — mutating レーン解禁の最小設計

- status: **draft (未ratify・未実装)** — 監査 gate 用
- date: 2026-06-23
- 上位: `HANDOFF_SCHEMA_APPENDIX_v0.5` §4.4（mutating ∧ no lease → block）,
  `HANDOFF_OPERATIONAL_IMPL_DESIGN_v0.1`（non_mutating レーン運用中）
- 目的: 現在 fail-closed で全 block している **mutating レーン**を、**lease（占有
  権）**という最小の安全機構付きで初めて解禁する。external 解禁ではない。

---

## 0. 現状（解禁前）

`validator.validate_dispatch` は §4.4 で:

```
mutation == "mutating" and not env.lease_subsystem_available → block("lease_required_but_unavailable")
```

`Env.lease_subsystem_available` は既定 `False`。運用ツール
（`alo_gpt_audit.handoff_validate_packet`）は `HandoffEnv()` を素で渡すため、
mutating は**例外なく block**。これは安全だが mutating は一切進まない。

**問題**: 現 gate は「subsystem が在るか」の boolean のみ。仮に True にしても
「誰が・何を・いつまで占有しているか」を検証しないため、二重書き込み・期限切れ占有・
他人のリースでの mutate を防げない。解禁にはリース実体の検証が要る。

---

## 1. lease とは（定義）

ある **mutation target**（例: 1 ファイルパス / 1 レコード ID / 1 queue item）に対する
**時間制限つき・単一書き手の占有権**。append-only に発行・解放される。

lease record（最小フィールド）:

| field | 意味 |
|---|---|
| `lease_id` | 一意 id |
| `target_key` | 占有対象の正規化キー（path / record id 等） |
| `holder` | 占有者（assignee + machine の単一書き手識別） |
| `granted_at` / `expires_at` | JST ISO。期限必須（無期限禁止） |
| `scope` | 許す mutation の種類（例: `file_move`, `metadata_set`） |
| `state` | `active` / `released` / `expired` |

保存: 既存台帳と同じ append-only JSONL（`_LEASE_LEDGER.jsonl`）。発行/解放はレコード
追記で表現（mutate-in-place しない）。これは「監査の帰り便」と同じ承認不要事務に収まる。

---

## 2. dispatch packet 拡張

mutating packet は **`lease_ref`** を必須にする:

```jsonc
{
  "next_action_type": "file_move",
  "side_effect_flags": ["file_move"],
  "lease_ref": {
    "lease_id": "LS_20260623_001",
    "target_key": "to_gpt/X_REQUEST.md",
    "scope": "file_move"
  }
}
```

`lease_ref` 無しの mutating は従来どおり block。

---

## 3. validator 拡張（§4.4 を置換、単一実装）

`Env.lease_subsystem_available` に加え、有効リースを参照する関数 `lease_lookup`
（`Callable[[str], LeaseRecord | None]`）を `Env` に追加。新しい mutating gate:

```
if mutation == "mutating":
    if not env.lease_subsystem_available:        → block("lease_required_but_unavailable")  # 既存
    ref = packet.get("lease_ref")
    if not ref:                                  → block("lease_ref_missing")
    rec = env.lease_lookup(ref["lease_id"])
    if rec is None:                              → block("lease_not_found")
    if rec.state != "active":                    → block("lease_inactive")
    if now > rec.expires_at:                     → block("lease_expired")
    if rec.target_key != ref["target_key"]:      → block("lease_target_mismatch")
    if ref["scope"] not in rec.scope:            → block("lease_scope_mismatch")
    if rec.holder != packet.assignee+machine:    → block("lease_holder_mismatch")
    # すべて通れば mutating dispatchable
```

**全 block 理由は fail-closed**（不明・欠落は通さない側へ）。検証は
`handoff_proto/validator.py` の単一実装に追加し、運用ツールは import するだけ
（operational v0.1 の must_fix #3 を継続）。

---

## 4. 運用ツール側

- 新コマンド `handoff-lease`（`grant` / `release` / `list`）。発行・解放は append-only。
- `handoff-validate` は flag on のとき `Env` に lease subsystem を結線して mutating を
  検証。**flag は引き続き既定 off**（must_fix #4 継続）。
- mutating dispatch card は `handoff_queue/` に出すが、**実 mutate は実行しない**。
  card は「占有確認済み・実行可」の証跡で、実行は別レーン（worker）に委ねる。

---

## 5. スコープ境界（この設計で解禁する / しない）

**解禁する**: ローカル / Box 内の **mutating（file_move・metadata_set 等）**を、
有効リース下で **dispatch 可** と判定すること。

**解禁しない（HOLD 継続）**: paid/quota call、confidential egress、外部送信、本番
DB・DDL、accepted/canonical 化、SF 書戻し、自動実行（card→実 mutate の自動連結）。
リース取得後の**実 mutate 実行**自体も本設計の範囲外（別 gate）。

---

## 6. テスト計画（実装時）

prototype に追加:
- mutating ∧ lease_ref 無し → `lease_ref_missing`
- 期限切れ / state≠active → `lease_expired` / `lease_inactive`
- target / scope / holder 不一致 → 各 mismatch block
- 全条件 OK → dispatchable（唯一の許可ケース）
- lease subsystem 不在（flag off 相当）→ 既存 `lease_required_but_unavailable`
body に追加:
- `handoff-lease grant/release` の append-only 冪等性
- flag off で lease 検証経路に入っても書き込みゼロ

---

## 7. owner への問い（decision_requested）

1. mutation target の `target_key` 正規化（path 基準で十分か / record id も要るか）。
2. lease 既定 TTL（例 30 分）と上限。
3. 単一書き手の `holder` 同定方法（assignee + machine id でよいか）。
4. 「card まで（dispatch 可判定まで）」で v0.1 を切り、実 mutate 実行は次 gate でよいか。
