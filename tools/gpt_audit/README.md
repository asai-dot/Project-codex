# tools/gpt_audit — CONSUMED ビュー (v0.3 監査レーンへの追加)

GPT お目付け役監査レーンは Box の **v0.3 設計**が正本
(`GPT_PRO_AUDIT_LANE_DESIGN_v0.3` / `_AUDIT_LEDGER.jsonl` / `_ACTION_QUEUE.md` / `alo-gpt-audit`)。
ここに置くのは、その v0.3 に**唯一足りなかった派生ビュー**だけ。

> GPT が試作した `GPT_OMETSUEKE_QUEUE_PROTOCOL_v0.2` は、調査の結果 v0.3 とほぼ同一概念だった。
> v0.2 で唯一 v0.3 に無かったのが **CONSUMED (採用判断を 1 ファイルで追う) の発想**。
> よって v0.2 を新規実装せず、その発想だけを v0.3 台帳の派生ビューとして取り込む。

## ファイル

| ファイル | 役割 |
|---|---|
| `consumed_view.py` | `_AUDIT_LEDGER.jsonl` → `handoffs/gpt_ometsuke/CONSUMED.md` を生成する派生ビュー |
| `_AUDIT_LEDGER.snapshot.jsonl` | Box 正本台帳の CONSUMED 関連フィールドのミラー (2026-06-08)。既定入力 |
| `test_consumed_view.py` | 単体テスト |

## 使い方

```bash
# 既定 (スナップショット) から生成
python3 tools/gpt_audit/consumed_view.py build

# 本番: Box 同期の _AUDIT_LEDGER.jsonl を指す
python3 tools/gpt_audit/consumed_view.py build --ledger /path/to/_AUDIT_LEDGER.jsonl

# 生成物と台帳の一致を検証 (CI)
python3 tools/gpt_audit/consumed_view.py check

python3 tools/gpt_audit/test_consumed_view.py
```

## 何をするビューか

v0.3 台帳の `next_action_type` / `loop_state` / `reflected` を読み替えて、
「GPT RESULT を Claude が読んだか・採用/不採用・反映したか」を 1 画面に集約する。
**未反映 (`reflected:false`) を最上段**に出し、「読んだのに反映していない」を可視化する。
新しい状態語彙や別の台帳は作らない。closed 判定など状態管理は v0.3 のまま。
