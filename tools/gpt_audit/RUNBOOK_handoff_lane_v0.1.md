# RUNBOOK — handoff lane 運用観測 (v0.1, non_mutating only, flag default off)

対象: `alo_gpt_audit.py handoff-validate` を使い、**DISPATCH packet** の受け渡しを
実レーンで観測する単一書き手。設計は `HANDOFF_OPERATIONAL_IMPL_DESIGN_v0.1`、
監査は `20260623_handoff_operational_impl_v0.1`（GPTPRO PASS_WITH_NOTES）。

> 大原則（不変）
> - 運用経路に出るのは **non_mutating レーンのみ**。mutating / paid / 機密 egress /
>   Box mutation / DB・DDL・canonical / 外部送信は **fail-closed で必ず block**。
> - feature flag `ALO_HANDOFF_LANE` は **既定 off**。off の間は完全 read-only。
> - 必ず **flag off で目視 → flag on + `--apply`** の順。単一書き手で実行。
> - blocked は route card を出さず、理由を台帳へ **append-only** 記録するだけ。

---

## 0. 前提（最新コードを pull）

```bash
cd ~/path/to/Project-codex
git fetch origin claude/gpt-codex-mcp-plugin-r4cleb
git checkout claude/gpt-codex-mcp-plugin-r4cleb
git pull origin claude/gpt-codex-mcp-plugin-r4cleb

cd tools/gpt_audit
python3 -m unittest discover -s tests          # 20 green を確認
(cd handoff_proto && python3 -m unittest test_handoff_proto)   # 15 green
```

---

## 1. レーン root を設定

```bash
export ALO_GPT_AUDIT_ROOT="$HOME/Library/CloudStorage/Box-Box/浅井/claude/handoffs/gpt_ometsuke"
ls "$ALO_GPT_AUDIT_ROOT"        # to_gpt / from_gpt / _AUDIT_LEDGER.jsonl 等
```

handoff lane の成果物は root 直下の `handoff_queue/`（card）と `_AUDIT_LEDGER.jsonl`
（blocked 記録）に出る。既存の監査ループ用 queue とは別ディレクトリで干渉しない。

---

## 2. DISPATCH packet を用意

最小スキーマ（`handoff_proto/README.md` / SCHEMA_APPENDIX v0.5 準拠）。JSON 単体か配列。

```jsonc
// dispatch_sample.json — non_mutating（dispatch される例）
{
  "packet_id": "DISP_20260623_001",
  "source_queue_item_id": "AQ_xxx",       // 任意: action-queue 由来の追跡 id
  "next_action_type": "doc_patch",
  "assignee": "worker_cc",
  "execution_role": "worker",
  "data_access_class": "internal",
  "objective": "README の節を追記",
  "side_effect_flags": []                  // 空 = non_mutating
}
```

mutating を試したい場合は `side_effect_flags: ["file_move"]` 等。**これは必ず block
される**（lease subsystem 未実装 → `lease_required_but_unavailable`）。

---

## 3. flag OFF で目視（read-only）

```bash
# flag を立てない = 既定。--apply を付けても一切書かない。
python3 alo_gpt_audit.py handoff-validate dispatch_sample.json --apply
```

期待出力（書き込みゼロ）:

```
handoff lane: DISABLED (default). ... running read-only.
  packet=DISP_20260623_001 dispatchable=True block_reason=None mutation=non_mutating ...
would create card: handoff_queue/DISP_20260623_001_DISPATCH_CARD.md (flag off / dry-run)
```

`dispatchable` と `mutation/egress/resource` の 3 軸を目視で確認する。
mutating パケットなら `BLOCKED -> no card; would append ledger (...)` になる。

---

## 4. flag ON + --apply（観測実行）

目視で問題なければ flag を立てて実行:

```bash
ALO_HANDOFF_LANE=1 python3 alo_gpt_audit.py handoff-validate dispatch_sample.json --apply
```

- dispatchable(non_mutating) → `handoff_queue/<packet_id>_DISPATCH_CARD.md` を生成（冪等）。
- blocked → **card は作らず**、`_AUDIT_LEDGER.jsonl` に
  `{"event":"handoff_blocked","block_reason":...}` を 1 行追記。

`--apply` 無し（flag on でも）は dry-run のまま。`ALO_HANDOFF_LANE=1` 単体では
read 経路に影響しない。

---

## 5. 観測ポイント

```bash
# 生成された card
ls "$ALO_GPT_AUDIT_ROOT/handoff_queue/"
cat "$ALO_GPT_AUDIT_ROOT/handoff_queue/DISP_20260623_001_DISPATCH_CARD.md"

# blocked 記録（append-only・最後の数件）
tail -n 5 "$ALO_GPT_AUDIT_ROOT/_AUDIT_LEDGER.jsonl"
```

観測で確認すること:
1. **non_mutating だけ** card 化されているか（mutating/paid/機密が漏れていないか）。
2. blocked の `block_reason` が想定どおりか（`lease_required_but_unavailable` /
   `resource_permit_unavailable` / `egress_forbidden` / `access_class_unknown` …）。
3. card と blocked のカウントが投入 packet 数と一致するか。

---

## 6. ロールバック / 無効化

- **即時停止**: flag を外すだけ（`unset ALO_HANDOFF_LANE`）。以後は read-only。
- card は単なる md。誤生成は削除してよい（冪等なので再実行で作り直せる）。
- 台帳は append-only。誤記録は**消さず**、後続の打ち消し記録か運用メモで対応。

---

## 7. やってはいけないこと（HOLD）

- mutating レーンを「とりあえず通す」目的で validator を書き換える / Env を真にする。
  → mutating 解禁は **lease subsystem を別 gate で設計 → 監査 → owner ratify** が必須
  （`LEASE_SUBSYSTEM_DESIGN_v0.1` 参照）。
- 複数マシンから同時 `--apply`。
- handoff lane の成果を accepted/canonical 化・本番 DB・SF 書戻し・外部送信へ繋ぐこと
  （すべて owner-gated・このレーンの範囲外）。
