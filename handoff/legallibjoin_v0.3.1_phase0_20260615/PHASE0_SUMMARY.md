# legallibjoin v0.3.1 Phase 0 — 実データ inventory 結果 (2026-06-15)

> **report-only**: canonical (`app/data/books.json`) も legallib も **一切書き換えていない**。
> final_toc 未生成 / production apply 未実施 (DDLEGALLIBCONCORD: phase0=GO / apply=HOLD を維持)。
> 生成: `scripts/phase0_inventory.py`（stdlib のみ・決定的・`--out` 指定先のみ書込）。

## 実行
```
python3 scripts/phase0_inventory.py \
  --legallib-dir ~/alo-ai/work/legallib_dl \
  --resolver     ~/alo-ai/work/legallib_dl/resolver_decisions.jsonl \
  --canonical    ~/ALOBookDX/事務所内本棚DX化計画/app/data/books.json \
  --out          handoff/legallibjoin_v0.3.1_phase0_20260615
```
入力の sha256 は `inputs_sha256.txt`（legallib_dir は *.json 4,052 件の順序非依存フィンガープリント）。

## 規模
- legallib 詳細TOC: **4,052 ファイル** (book 2,760 / journal 422 / material 214 / pubcom 655 / 他)
  — book の TOC 総ノード **623,891**。
- canonical 書誌: **7,728 レコード** (ISBN 付与 5,535)。
- resolver 突合: **2,760 判定** (auto_accept 1,839 / human_review 305 / defer_new 616)。
- edition identity 評価 (canonical ISBN 一致): **2,082 対**。

## 成果物 (Phase 0 発注書 6 点 + GPT 指定 dry-run evidence)
| ファイル | 内容 | GPT evidence |
|---|---|---|
| `source_inventory.md` | ソース別 inventory + edition identity 診断(所見1-4) | ① source inventory |
| `parser_success_histogram.csv` | content_type × node数バケット | ② parser histogram |
| `page_basis_profile.md` | pdf/print 両持ち率・offset 本単位一貫性 | (page_basis profile) |
| `edition_identity_sample.jsonl` | classify_edition_identity 全 2,082 対の判定 | ③ conflict seed 母集団 |
| `known_conflict_golden.md` | 既知 conflict 10冊 golden (危険順) | ③ known conflict 10冊 |
| `inputs_sha256.txt` | 入力ハッシュ (再現性) | ④/⑤ の入力固定 |

> ④ all_nodes_accounted_for 照合 と ⑤ apply_guard 物理拒否ログ は、本 Phase 0 で判明した
> **接合キー(ISBN付与=resolver依存)** と **edition gate 入力(下記 golden)** を使って
> `concordance_pipeline.py` で生成する次段（Phase A dry-run）の入力が確定した。

## 主要所見（= 閾値調整に直結する Phase 0 の本体）

1. **legallib はネイティブ ISBN を持たない** → ISBN は resolver の title/publisher/year 突合で
   後付け。接合キーの素性は **resolver 品質に従属**。canonical 書誌に **頁数欄なし**
   (page_count 照合は legallib 側のみ)。

2. **edition identity の生 344 件 (16.5%) 別版疑いは過検知**。層別すると:
   - 偽陽性 **226 件** = title 装飾差 (cosmetic 123: 全半角・`〔〕〈〉`・読点) + 副題差 (87)
     + 年差±1 ノイズ / 版番号一致の重版。**別版ではない**。
   - 真に要レビュー **118 件 (5.7%)**。うち **確実な別版 (版番号衝突) = 26 件**。
   - 信頼できる別版信号は **タイトルから抽出した版番号の相違**。現行
     `classify_edition_identity` の「title 文字列一致 / 年が1つでも違えば別版」では過検知する。

3. **共有 `normalize_title` の穴**: NFKC はするが `〔〕` `〈〉` `、`(読点) を strip しない。
   これだけで cosmetic 123 件が別版誤判定 → `_STRIP_RE` へ3文字追加で解消（共有モジュール
   変更のため本 PR スコープ外＝別 DD で実施）。

4. **resolver 偽陽性**: auto_accept 1,839 件中 108 件が別版疑い → 装飾/副題/年ノイズ除外後の
   **実質要レビュー 12 件 (0.7%)**。これらは production apply で edition gate が物理拒否すべき
   対象（HOLD 維持の根拠）。`known_conflict_golden.md` は **この危険ケース優先**で 10冊選定。

5. **resolver recall ギャップ**: bucket=defer_new (canonical 不在として create 予定) のうち
   **58 件は canonical に同一 ISBN が存在** → human_review へ差し戻すべき取りこぼし候補。

6. **page_basis は機械変換可能**: book TOC ノードの 95% が pdf_page/print_page 両持ち。
   offset(=前付け頁数) は **2,670冊中 94.9% で完全単一・95.5% で 90%以上単一**（平均占有率
   0.979）。横断で offset が 133 種に散るのは本ごとに前付け頁数が違うためで同一本内のブレ
   ではない。→ **page tolerance は本単位 offset 補正後に評価すべき**（生 pdf_page 差での
   別版判定は前付け差を誤検知する）。残り 5% の pdf-only は章見出し等の構造ノード。

## apply 解禁ゲートへの提言（HOLD のまま、次段の条件）
- 別 DD で `classify_edition_identity` を **版番号抽出 + 核タイトル包含 + 年差±1許容 +
  版番号一致時の年差無視** へ強化（過検知 226 → ≈0、真の別版 118 を取りこぼさない）。
- `normalize_title` に `〔〕〈〉、` を追加。
- resolver defer_new の 58 件と auto_accept 偽陽性 12 件を human_review へ。
- 上記反映後に `concordance_pipeline.py` で all_nodes_accounted_for 照合 + apply_guard 拒否
  ログ (evidence ④⑤) を golden 10冊込みで生成 → owner ratify → 初めて apply 検討。

## 検証 / テスト
- `tests/test_phase0_inventory.py` 追加（版判定ロジックを実例で凍結）。
- 関連テスト 33 件 PASS（phase0 / v031_authority / v031_gates / concordance / concordance_pipeline）。
- 既知: `tests/test_pipeline.py` 9件が `tmp` fixture 未定義で ERROR。**Phase 0 と無関係**
  (pipeline dashboard 用・本作業前から存在・conftest.py 不在の環境差)。
