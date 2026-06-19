# WORKER TASK PACKET — P0 silver dry-run（実データ実測）

> to: worker（Mac CC・単一書き手レーン） / from: 番頭(Claude) / owner: 浅井 / date: 2026-06-19
> gate: **read-only dry-run のみ**。DB write / DDL / 外部取得 / canonical mint は禁止（下記 FORBIDDEN）。
> 親: design/vocab_bottleneck/01_BOTTLENECK_RESOLUTION_PLAN_20260618.md（P0）
> tools: tools/silver_resolve/（silver_cite_id.py / silver_toc_section.py / schema_probe.py）— 本リポジトリに実装・検証済(19 tests OK)

## 0. ゴール（一行）

既取得データだけで silver-1（掲載位置→判例ID）と silver-2（TOC→論点section）の dry-run を回し、
**report 2本＋主要数字**を持ち帰る。これで claim_support 在庫(実測ゼロ)立ち上げの歩留まりが測れる。

## 1. 入力データ（既取得・read-only で参照のみ）

| 役割 | 既知の所在 | 期待スキーマ（schema_probe --expect） |
|---|---|---|
| lic 解説引用エッジ | `alo-ai/work/lic_edges_staging/edges_raw.jsonl`（55,978） | `lic` |
| 関係エッジ全体（派生元） | `build/periodical_lane_20260611/edges_20260611.jsonl`（287k・edge_type別） | — |
| hanrei_published_in 索引 | ↑から `edge_type=hanrei_published_in` を抽出（76,643） | `pub` |
| toc_row_reports_hanrei | ↑から `edge_type=toc_row_reports_hanrei` を抽出（7,039 strong） | `toc_edges` |
| TOC 階層 nodes | 新3源TOC の node 化分（toc_node/parent/heading） | `toc_nodes` |
| 評釈密度 | `hyoshaku.jsonl`（61,153） | `hyoshaku` |
| 判例 canonical（by_date用） | `project_d1law_hanrei_canonicalized`（192,998・court+date） | `canon` |

> edges_20260611.jsonl からの抽出は `jq -c 'select(.edge_type=="hanrei_published_in")'` 等で行う。

## 1.5 誌名正規化は既存資産を再利用（★再発明禁止）

誌名正規化と雑誌同定は **雑誌レーン (DD-PERIODICAL-001) が既に正本を持っている**。新規辞書を作らないこと。

| 既存資産（正本） | 所在 | 役割 |
|---|---|---|
| `periodical_edges_normalize.py` の `jnorm()`/`canon()`/`ALIAS` | `事務所内本棚DX化計画/scripts/`（build/periodical_lane 生成元） | 誌名正規化規則（NFKC＋空白除去＋lower＋別称統合）。`ALIAS` 例: 判時→判例時報 / 判タ→判例タイムズ / 金判・商事判例→金融・商事判例 / 金法→金融法務事情 / 商事法務→旬刊商事法務 |
| `journal_issn_map.jsonl` | `build/periodical_lane_20260611/` | journal_norm → ISSN（confirmed/confirmed_ndl）。雑誌同定レジストリ |
| `hanrei_published_in` の `issue_id` | edges_20260611.jsonl | `issn:{issn}#{通巻}` / `jp:{jnorm}#{号}` の**正準号キー**（既発行） |
| 関連: `ndl_normalize.py` / `cinii_opac_overlay.py` / `opac_ndl_overlay_analysis.py` | `scripts/` | NDL/OPAC/CiNii 側の正規化・同定 |

**silver-1 の `--norm-dict` は、上記から生成する（手書きしない）**:
- `periodical_edges_normalize.py` の `ALIAS` ＋ `journal_issn_map.jsonl` の journal_norm を書き出して `journal_norm.json` を作る。
- silver-1 の照合は **雑誌レーンと同じ正規化**に揃える。可能なら lic locator も同じ `canon()` で正規化し、
  `issue_id`（`issn:…#…` / `jp:…#…`）名前空間で `hanrei_published_in` に突合する（= 既存の号同定を流用、別系統の号キーを新設しない）。
- 整合性ゲート: silver-1 が作る判例側の号キーが `hanrei_published_in` の `issue_id` と一致すること（不一致なら正規化が雑誌レーンとずれている＝再発明の兆候）。

## 2. 手順

### STEP A. スキーマ点検（各入力で1回）
```bash
python3 tools/silver_resolve/schema_probe.py --jsonl <lic_edges>  --expect lic
python3 tools/silver_resolve/schema_probe.py --jsonl <pub_index>  --expect pub
python3 tools/silver_resolve/schema_probe.py --jsonl <toc_nodes>  --expect toc_nodes
python3 tools/silver_resolve/schema_probe.py --jsonl <toc_edges>  --expect toc_edges
```
- 欠落キーが出たら、雛形を埋めて `field_map.json`（例 `{"source_locator":"cite_str","hanrei_id":"case_id"}`）を作る。
- `toc_nodes` に `kind` が無ければ STEP C で `--infer-kind` を付ける（手書き変換は不要）。

### STEP B. canary（小さく検証してから全量）
1. lic を先頭 2,000 行に絞って silver-1 を回し、strong の中身が妥当か目視（誌名・号・頁が正しく判例に対応するか）。
2. silver-2 は **賃貸借/解除** 周辺の book に絞って回し、論点section 見出しが「論点タイトル」になっているか、
   賃貸借/解除で既知の **659判例** 規模の harvest が再現する方向か目視（厳密一致は不要・桁感）。
3. 妥当なら STEP C で全量。おかしければ field_map / 正規化辞書を直して再実行（STEP D）。

### STEP C. 全量 dry-run
```bash
# silver-1: 掲載位置→判例ID
python3 tools/silver_resolve/silver_cite_id.py \
  --lic-edges <lic_edges> --pub-index <pub_index> \
  --canon-index <hanrei_canonical> \
  --norm-dict journal_norm.json \   # §1.5 で既存 ALIAS＋journal_issn_map から生成（手書きしない）
  [--field-map field_map.json] \
  --out out/silver1_20260619

# silver-2: TOC→論点section
python3 tools/silver_resolve/silver_toc_section.py \
  --toc-nodes <toc_nodes> --toc-edges <toc_edges> --hyoshaku <hyoshaku.jsonl> \
  [--field-map field_map.json] [--infer-kind] \
  --out out/silver2_20260619
```

### STEP D. 歩留まり改善ループ（silver-1）
- report の `未解決理由`（locator_unresolvable / db_unbuilt）と多候補を見て、誌名表記ゆれを拾う。
- 新しい別称は **`periodical_edges_normalize.py` の `ALIAS`（雑誌レーン正本）へ還元する形で追記**し、そこから
  `journal_norm.json` を再生成する（silver-1 ローカルに別辞書を増殖させない＝雑誌レーンと単一の正規化を保つ）。
- 再実行し、**解決% の向上幅**（基準 概算24%）を記録。2〜3反復で頭打ちまで。

## 3. 持ち帰るもの（return）

1. `out/silver1_20260619/silver_cite_resolution_report.md` の中身。
2. `out/silver2_20260619/silver_toc_section_report.md` の中身。
3. 主要数字を3行で:
   - silver-1: 解決%（正規化前→後）/ **strong 件数** / 主な未解決理由。
   - silver-2: `naive_book_pairs`（≒89,358想定）→ `section_pairs`（意味あり）の置換規模 / 論点section 数。
   - 異常・スキーマ不一致・想定外があればその旨。
4. candidate JSONL は **out/ に置いたまま**（DB へ入れない）。パスだけ報告。

## 4. ACCEPTANCE（完了条件）

- report 2本が生成され、上記3行サマリが揃っている。
- silver-1 の strong が `issue_page_exact 単一` のみであること（report の二層分離欄で確認）。
- silver-2 が同一書籍 weight-1 全結合を論点section内共起へ置換できていること（naive vs section の対比が出ている）。

## 5. FORBIDDEN（このパケットの射程外・やったら逸脱）

- candidate の DB / canonical graph への write（= P1・owner ゲート・別パケット）。
- 外部サービス取得（#16 D1文献編事項索引 / D1再取得 = owner GO・別 WO）。
- 論点section を accepted 論点として下流へ流す（DD-LRINDEX-001 v0.4 GPT確認パス前）。
- DDL / production mapping / MCP publication / embedding 生成。

## 6. ESCALATION

- 入力ファイルが見つからない / スキーマが大きく異なり field_map で吸収できない → 番頭へ差し戻し（推測で代替しない）。
- strong が極端に少ない（誌名正規化しても解決%が伸びない）→ report を添えて番頭へ。閾値・正規化方針を再設計。
