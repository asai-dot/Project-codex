# DICT-008 accept 記録ドラフト（owner 署名待ち）20260625

> doc_kind: accept 記録ドラフト（design-only / owner の OK で確定） / author: Claude / date: 2026-06-25 / owner: 浅井
> 親: 02_P1_DICT008_ACCEPT_READINESS / 11_P1_WAVE_URL_VERIFICATION
> 注: DICT-008 v0.2 本体は owner 側設計空間にあり本リポジトリ未収録。本書は accept の「枠」と
>     downstream 更新ドラフトを用意するもので、内容判断(A1/A2/A3)は owner が下す。

## 0. 一行

DICT-008 を candidate → accepted v1.0 にするための**記録の枠**。owner が A1/A2/A3 に OK を入れれば確定。
残ブロッカーは owner レビューのみ（Wave B は 11 で解消済）。

## 1. accept 判定（owner 記入欄）

| # | 判定項目 | owner 判定 | 備考 |
|---|---|---|---|
| A1 | DICT-008 v0.2 本体（Q1–Q4反映版）を accept してよいか | ☐ OK / ☐ NO / ☐ 戻す | Canonical Bedrock 戦略本体 |
| A2 | 34層 §4.1(bedrock-first) / §9(gate 2本) 改訂計画 | ☐ OK / ☐ 修正 | 下記 §3 にドラフト |
| A3 | DDL gate 改訂(gate群＋§2.3.1 昇格可rank集合)の影響範囲 | ☐ OK / ☐ 修正 | SQL は `tools/vocab_hub/sql/02_*` に生成済 |
| - | accept 確定日 / version | __________ / v1.0 | A1–A3 全 OK で記入 |

## 2. accept が解禁する作業（DICT-008 §6.2）— 全て accept 後

1. **doc_registry 登録**: DICT-008 を accepted v1.0 として登録（status/version/accept日）。
2. **34_vocabulary_layer 改訂**: §4.1 接続順=bedrock-first、§9 gate 2本追加（§3 ドラフト）。
3. **gate VIEW 追加**: `tools/vocab_hub/sql/02_vocab_hub_gates.sql`（生成済）を P2 DDL に同梱。
4. **PLAN-01 反映**: §3.4.5（既に整合 A4=済）。

## 3. 34層改訂ドラフト（A2 レビュー対象）

### §4.1 接続順（bedrock-first / 物理ゲート）
> specialty(rank≥103) は単独で canonical hub anchor になれない。bedrock(100–102) hub に attach のみ。
> = `gate_specialty_exact_match`（SQL生成済）で担保。

### §9 ゲート追加（2本＋入口品質1本）
> - `gate_canonical_promotion`: canonical hub anchor は昇格可 rank 集合(100/100a–100d/101/102/200自hub)のみ。
> - `gate_specialty_exact_match`: specialty 同士 exact_match を bedrock anchor なしに作らせない。
> - （P0品質監査由来の追加）`gate_quality_canonical`: needs_preprocessing 非空の hub は canonical 不可。
>   = 空定義/短定義/末尾切れ anchor の canonical 昇格を物理的に封じる（06/09 findings）。

## 4. §2.3.1 gate 条件改訂（A3 レビュー対象・SQL生成済）

`gate_canonical_promotion` を「昇格可 rank 集合」方式へ改訂（02_P1 §2 のとおり）。
実 DDL = `tools/vocab_hub/sql/02_vocab_hub_gates.sql`（未 apply、owner GO+監査後）。

## 5. accept と P2 の関係（owner 向け一言）

- accept = **設計の確定**。辞書を DB に積む（P2）とは別ゲート（owner GO＋GPT監査＋canary）。
- P2 の生成物（DDL/load-ready）は `tools/vocab_hub/sql/` ＋ `build_load_artifacts.py` に**DB非接続で用意済**。
- accept は DD-CRED-001 に依存しない（Q4 で scope 外確定済）。

## 6. ゲート

本書は記録ドラフト。accept 確定は owner の A1/A2/A3 記入による。DDL apply・DB load・doc_registry 実更新は
別ゲート（owner GO / GPT監査）。
