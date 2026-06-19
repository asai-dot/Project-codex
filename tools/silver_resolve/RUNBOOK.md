# RUNBOOK — silver_resolve を実データで回す (P0 dry-run)

> 対象: 単一書き手 (Mac CC) / Box Drive 同期パスを入力に取る / **read-only dry-run のみ**
> 計画: design/vocab_bottleneck/01_BOTTLENECK_RESOLUTION_PLAN_20260618.md の P0
> 採用済み推奨: D1=賃料不払解除 canary / D2=strong-only / D3=外部取得保留 / D4=yes

## 0. 原則

- 本ツールは **既存 JSONL/索引の集計・突合のみ**。DB write / 外部取得 / canonical mint を一切行わない。
- 出力は candidate staging (JSONL) と report (md) だけ。staging への write・accepted 化は **P1 (owner ゲート)** で別途。
- 数字を見てから D1 (着手単位の確定) と D2 (閾値) を最終決定してよい。

## 1. 入力データの所在 (Box 同期側・既取得)

| 役割 | 既知の所在 (relationship_layer_status_20260617 より) |
|---|---|
| lic 解説引用エッジ | `alo-ai/work/lic_edges_staging/edges_raw.jsonl` (55,978) |
| 関係エッジ全体 | `build/periodical_lane_20260611/edges_20260611.jsonl` (287k, edge_type 別) |
| hanrei_published_in 索引 | periodical lane 集計 (判例→号 76,643) |
| 評釈密度 | `hyoshaku.jsonl` (61,153) |
| 判例 canonical | `project_d1law_hanrei_canonicalized` (192,998) |
| toc_row_reports_hanrei | periodical edges (`edge_type=toc_row_reports_hanrei`, 7,039 strong) |
| TOC 階層 | 文献TOC nodes (新3源TOC 1.64M の node 化分) |

> 実フィールド名が本ツールの期待スキーマと違っても、**変換スクリプトは不要**。
> まず `schema_probe.py` で点検 → 出力された field-map 雛形を埋めて `--field-map` に渡すだけ。
>
> ```bash
> # 各入力のフィールドと期待スキーマの充足/欠落を点検し, field-map 雛形を得る
> python3 tools/silver_resolve/schema_probe.py --jsonl <lic_edges.jsonl>  --expect lic
> python3 tools/silver_resolve/schema_probe.py --jsonl <pub_index.jsonl>  --expect pub
> python3 tools/silver_resolve/schema_probe.py --jsonl <toc_nodes.jsonl>  --expect toc_nodes
> ```
>
> 欠落キーがあれば `field_map.json`（例: `{"source_locator":"cite_str","hanrei_id":"case_id"}`）を作り、
> 下記コマンドに `--field-map field_map.json` を足す。`toc_nodes` に `kind` が無ければ silver-2 に `--infer-kind`
> を付ける（判例を report する node=row, 他=heading と推定）。

## 2. silver-1: 掲載位置 → 判例ID

```bash
python3 tools/silver_resolve/silver_cite_id.py \
  --lic-edges   <lic_edges.jsonl> \
  --pub-index   <hanrei_published_in.jsonl> \
  --canon-index <hanrei_canonical.jsonl> \   # by_date 経路用 (任意)
  --norm-dict   <journal_norm.json> \         # 誌名正規化辞書 (任意・反復改善)
  --field-map   field_map.json \              # フィールド名が違う場合 (任意)
  --out         out/silver1_$(date +%Y%m%d)
```

出力: `silver_cite_resolution_candidates.jsonl` / `silver_cite_resolution_report.md`。

**見るべき数字** (report):
- 解決済 % (基準値 概算 24%)。誌名正規化辞書を足して **向上幅**を測る (これが silver-1 の主眼)。
- strong 件数 = issue_page_exact 単一 = **P1 で staging write 候補**になる集合。
- 未解決理由内訳 (`locator_unresolvable` / `db_unbuilt`) → 正規化辞書 or 号fallback の改善対象。

**反復改善ループ**: report の未解決・多候補を見て `--norm-dict` に表記ゆれを追記 → 再実行 → 歩留まり比較。

## 3. silver-2: TOC → 論点section

```bash
python3 tools/silver_resolve/silver_toc_section.py \
  --toc-nodes <toc_nodes.jsonl> \
  --toc-edges <toc_row_reports_hanrei.jsonl> \
  --hyoshaku  <hyoshaku.jsonl> \   # 重要度 (任意)
  --field-map field_map.json \     # フィールド名が違う場合 (任意)
  --infer-kind \                   # toc_nodes に kind が無い場合 (任意)
  --out       out/silver2_$(date +%Y%m%d)
```

出力: `silver_toc_section_candidates.jsonl` / `silver_issue_cooccurrence_candidates.jsonl` / `silver_toc_section_report.md`。

**見るべき数字** (report):
- `naive_book_pairs` (同一書籍全結合 weight-1・無意味) vs `section_pairs` (論点section 単位・意味あり)。
  前者は実データで約 89,358 ペアになるはず。後者への**置換**が silver-2 の成果。
- 論点section サイズ分布 / 共起 weight 分布。
- trace_absent (評釈密度ゼロ section) の割合。

> 注意: TOC nodes に `kind` (heading/row) が無い場合は `--infer-kind` を付ける
> (判例を report する node = row、他 = heading と自動推定)。事前変換は不要。

## 4. canary (D1 採用: 賃料不払解除)

全件前に、まず賃料不払解除の評釈付 882 件相当だけに絞った lic/toc サブセットで両ツールを回し、
report の妥当性 (strong の中身・論点section の見出しが論点になっているか) を目視確認 → 問題なければ batch。

## 5. やってはいけないこと (HOLD)

- candidate JSONL を DB / canonical graph へ投入する (P1 owner ゲート・別パケット)。
- D1 や外部サービスからの取得 (X1 #16 / X2 D1再取得 = owner GO・別 WO)。
- 論点section を accepted 論点として下流に流す (DD-LRINDEX v0.4 GPT確認パス前)。

## 6. テスト / デモ

```bash
python3 -m unittest discover -s tools/silver_resolve/tests -v   # 14 tests
python3 tools/silver_resolve/demo_run.py                        # artifacts/DEMO_silver_*.md
```
