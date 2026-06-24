# P2 STEP A 訂正記録: 投入先を asai-dot's Project に修正 20260625

> doc_kind: 実施記録（DDL apply 済・訂正あり） / author: Claude / date: 2026-06-25 / owner: 浅井
> 親: 13_P2_STEPA_SCHEMA_DEPLOY_RECORD（初版・誤投入） / owner GO（AskUserQuestion 2026-06-25）

## 0. 訂正内容（重要）

初版(13)で **schema を alo-connect (`vlsunmqpjhzbhipiehzs`) に誤投入**した。
alo-connect は**久保さんが使う動的DB**で vocab の投入先ではない。owner 指摘で判明。
（接続が password authentication failed だったのも、owner の使う asai-dot's Project の
パスワードを別プロジェクト alo-connect に当てていたのが原因だった。）

owner GO（AskUserQuestion）で下記2点を実施:

| 操作 | 対象 | 結果 |
|---|---|---|
| 誤投入の撤去（drop 7テーブル+gate, 全0行） | alo-connect `vlsunmqpjhzbhipiehzs` | ✅ 元の空に復旧（list_tables=[]） |
| schema＋gate 再展開 | **asai-dot's Project `nixfjmwxmgugiiuqfuym`** | ✅ success |

## 1. 正しい投入先（確定）

**asai-dot's Project** `nixfjmwxmgugiiuqfuym` (ap-northeast-1, pg17)。
- 7テーブル + gate 3本 + fn_run_all_gates() apply 済。
- `select * from fn_run_all_gates();` → 全 gate violation_count=**0**（空DBで正常）。
- direct host: `db.nixfjmwxmgugiiuqfuym.supabase.co` / pooler user: `postgres.nixfjmwxmgugiiuqfuym`。
- loader 既定値もこのプロジェクトに更新済（vocab_load_to_supabase.py）。

## 2. STEP C データ load（Mac側・正しいプロジェクトへ）

`~/vocab-wt` から（pooler は前回 `aws-1-ap-northeast-1.pooler.supabase.com` が正解だった）:
```
python3 tools/vocab_hub/vocab_load_to_supabase.py --pooler --pooler-host aws-1-ap-northeast-1.pooler.supabase.com
```
パスワードは **asai-dot's Project の DB パスワード**（owner が普段使っている方）。canary→batch。

## 3. ⚠ RLS（owner 判断・asai-dot's Project でも同様）

新展開した7テーブルも RLS 無効。Supabase advisory(critical)。remediation SQL は 13 §5 と同じ。
owner 判断（内部専用なら保留可 / 有効化＋policy）。

## 4. 教訓

- **プロジェクト ID を owner に明示確認してから DDL/DB を触る**（alo_ 接頭辞や「空」だけで投入先を推測しない）。
- 撤去は owner GO（AskUserQuestion）取得後に実施。alo-connect は原状回復済。

## 5. ゲート

alo-connect 撤去・asai-dot's Project 展開とも owner GO で実施。RLS・データ load・canonical 昇格は別ゲート。
