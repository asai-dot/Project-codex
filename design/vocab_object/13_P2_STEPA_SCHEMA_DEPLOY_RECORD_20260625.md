# P2 STEP A 実施記録: 語彙ハブ schema を alo-connect に展開 20260625

> doc_kind: 実施記録（DDL apply 済） / author: Claude / date: 2026-06-25 / owner: 浅井
> 親: 03_P2_VOCAB_SCHEMA_DEPLOY_PLAN / 12_DICT008_ACCEPT_RECORD_DRAFT
> 前提: owner GO（2026-06-25）＋ GPT独立監査 PASS_WITH_FIXES（全 finding 対応済）

## 0. 実施内容（STEP A のみ）

Supabase プロジェクト **alo-connect (`vlsunmqpjhzbhipiehzs`, ap-northeast-1, pg17)** に
語彙ハブ schema＋物理ゲートを apply。**データ load(STEP C)は未実施**（別ゲート・Mac側）。

| migration | 内容 | 結果 |
|---|---|---|
| `vocab_hub_schema_p2` | 7テーブル（alo_concept_schemes/terms/term_labels/hubs/hub_memberships/term_relations/entity_links）+ index | ✅ success |
| `vocab_hub_gates_p2` | gate 3本（canonical_promotion/quality_canonical/specialty_exact_match）+ fn_run_all_gates() | ✅ success |

## 1. 検証

- 7テーブル作成確認（全 0 行）。
- `select * from fn_run_all_gates();` → 全 gate violation_count=**0**（空DBで正常）。
- 監査(GPT独立) PASS_WITH_FIXES の blocker/major を load ビルダ側で全対応（FK整合・列射影・dst解決・scheme限定・gate拡張）。

## 2. ⚠ 未対応のセキュリティ事項（owner 判断要）

**RLS(Row Level Security)が全7テーブルで無効**。Supabase advisory(critical):
> anon キーで誰でも全行を read/write 可能。

→ **owner 判断事項**。RLS を有効化するとポリシー無しでは全アクセス遮断されるため、自動適用しない。
方針候補: ①このDBは内部専用で anon キー非公開ならリスク限定 ②有効化＋read-only ポリシー付与。
remediation SQL は本記録 §5 に保存（適用は owner GO）。

## 3. 未実施（STEP B/C：別ゲート・Mac側）

- **STEP C データ load**: defrag済 15,942 terms / hubs / memberships / alias(403) を canary→batch。
  load 生成物は Mac の `~/vocab_load/`（`build_load_artifacts.py` で生成）。**ローダはこのコンテナから
  Mac データに届かない**ため、load は Mac 上の loader スクリプト + Supabase 接続で実施する。
- canary: 高頻度語＋genuine 3＋xref alias＋needs_preprocessing を投入 → fn_run_all_gates()=0 確認 → batch。

## 4. ゲート

STEP A(schema DDL)のみ owner GO＋監査で実施。RLS・データ load・canonical 昇格は各々別ゲート。

## 5. RLS remediation SQL（保存・未適用）

```sql
ALTER TABLE public.alo_concept_schemes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alo_terms ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alo_term_labels ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alo_hubs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alo_hub_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alo_term_relations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alo_entity_links ENABLE ROW LEVEL SECURITY;
-- ↑ 有効化後は read ポリシー等を別途付与しないと全アクセス遮断になる点に注意.
```
