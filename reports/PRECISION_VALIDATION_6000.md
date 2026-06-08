# 精度検証 — TOC法令リンク 10×スケール（6,000ノード）

- 日付: 2026-06-08 / 関連: DD-TOCLEGALREF-001 v0.2 (ratified design) / PR #8
- 目的: GPT お目付け役 A3 note（medium 昇格は gold set で sampled precision を測れ）に応え、
  前回の 600 ノード検証を**一桁拡大（6,000ノード）**して tier 別精度を実測する。
- 結論: **段階設計（high=初期投入 / medium=隔離 / low=除外）は実データで妥当**。
  high precision = 1.000、medium = 0.906（0.95 未達）、low = 0.615。

## 1. 方法（再現可能・書込みなし）

1. `biblio.bib_toc`（552,544行）から決定的サンプル 6,000 行を抽出
   （`order by md5(bib_id||'#'||ordinal) limit 6000`）。
2. 抽出器が発火し得るノードのみ SQL superset prefilter で選別（**リンクは無損失**）:
   154 法令名のいずれか、または元号トークン（平成|令和|昭和|大正|明治）を含む行。
   → 6,000 中 **213 ノード**（164 冊, 2010–2025）が eligible。残り 5,787 は法令名・元号を
   一切含まず、抽出器の出力は構造上ゼロ。
3. 既存パイプライン（`legal_links.py` → `alo_edges` producer v0.2）を適用。
   → statute link **152**（high 33 / medium 106 / low 13）、case candidate 22、low 除外後の
   export edge 139（initial 33 / quarantine 106）。**12 gate 全 PASS**。
4. 全 152 statute link を**目視判定**（ノード本文と突合し、真の条文/法令参照か誤検出かを判定）。
   判定結果は `out_real6k/precision_validation_6000.csv`。

## 2. 結果（tier 別 precision）

| tier | n | 正 | precision | 95% CI (Wilson) | 設計上の扱い | 判定 |
|---|---|---|---|---|---|---|
| **high**（条番号あり） | 33 | 33 | **1.000** | [0.896, 1.000] | initial backfill | ✅ 0.98 auto閾値超 |
| **medium**（裸の法令名） | 106 | 96 | **0.906** | [0.835, 0.948] | quarantine | ✅ 0.95 **未達を実証** |
| **low**（短名の埋没） | 13 | 8 | 0.615 | [0.355, 0.823] | 除外 | ✅ 除外が妥当 |
| export（high+medium） | 139 | 129 | 0.928 | [0.873, 0.960] | — | — |

- **high 33/33**: すべて `第○条` を伴う真の条文参照（例: 刑法97条/会社法828条1項/民法958条の3/
  医療法46条の3）。`egov=0` は当該条文の定義文未ロードの意味で、参照の正誤とは無関係。
- **medium 0.906 < 0.95**: GPT が設定した production 閾値を**実データで下回り、medium 隔離の
  判断が正しかったことを裏づけ**。

## 3. 誤検出（FP）の機序 — medium 10件 + low 5件

| パターン | 件数 | 例 |
|---|---|---|
| 「…法人/法制」等への部分一致 | 7 | 医療**法人**→医療法（×6）、都市計画**法制**→都市計画法 |
| 複合語への埋没 | 4 | モニター**商法**、海**商法**、民**商法**、国際**民事訴訟法** |
| 外国法の文脈 | 4 | ブラジル民法／ドイツ法人税法 第8a条 等を日本 egov 法令に誤接続 |

→ **medium 昇格の具体策**: (a) 法令名直後の `人|制|院` 等への負の先読み、(b) 直前漢字で別複合語を
形成する場合の除外、(c) 外国国名近接の文脈除外。これらを入れれば medium は 0.95 を越える見込み
（FP 15件中 ~11件が機械的に除去可能）。production promotion の precision gate 実装時の TODO。

## 4. ratified design への含意

- **high の初期 backfill は安全**（precision 1.000, n=33; ただし n を増やした追検証を推奨）。
- **medium は据え置きが正しい**。上記 (a)(b)(c) の FP ガードを実装し、gold set を 300+ に拡大して
  再測定 → 0.95 到達を確認してから production candidate export に格上げ。
- low は引き続き除外。
- 本検証は read-only。DB 書込みなし。

## 5. 成果物（本PR / out_real6k/）
`real_nodes_6000_eligible.jsonl`(213) / `legal_links_nodes.jsonl`(174 links) /
`alo_edges_export.jsonl`(139) / `alo_edges_export_summary.json`(all_gates_pass=true) /
`precision_validation_6000.csv`(152 link の目視判定一覧)。
