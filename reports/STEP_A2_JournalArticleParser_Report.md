# STEP A2 / Fork 4 報告 — 論文 entity 抽出 + 法令リンク

- 宛先: 番頭 (Mac CC)
- 発信: ワーカー (claude / headless, remote container)
- 日付: 2026-06-06
- 上位指示: `cc_instruction_legallib_journal_article_parser_20260605.md` (v1.1) +
  Fork 4「論文 entity ＆ 法令リンク（アイデア B・F）」
- ブランチ: `claude/journal-article-legal-linking-UaBnp`

---

## 0. サマリ

Fork 4 の 3 ステップ（① article parser スイープ、② 著者正規化、③ 条文・判例参照→
e-gov リンク）を **実行可能パイプライン**として実装し、テスト 38 件 + fixture E2E で
検証した。検収 3 項目はいずれも fixture 上で成立を確認:

| 検収項目 | 結果 |
|---|---|
| parse_rate ≥ 80%（hard） | **PASS** (fixture 全体 0.9167) |
| 著者横断検索が成立 | **PASS**（表記揺れ吸収・雑誌横断ヒット確認） |
| 法令リンクのサンプル目検 | **PASS**（条 URI 解決・e-gov 突合・confidence 付与） |

---

## 1. 重要な前提 / データ可用性（番頭判断を要する点）

本タスクは **remote 実行コンテナ**で動いており、STEP A 成果物の
**422 号分の元 JSON (`~/alo-ai/work/legallib_dl/*.json`) は当環境に存在しない**
（番頭 Mac ローカル資産）。Box / Drive も探索したが当該フォルダは未発見。

→ 方針: 元データが来たら**そのまま全 422 号に流せる**パイプラインを実装し、
**指示書記載の実例（法学セミナー No.49 / `305760`）＋エッジケース合成 fixture**で
E2E 検証した。**全 422 号の本番スイープは、番頭環境（または `legallib_dl` を
mount したコンテナ）で `scripts/run_article_parser.py --src <dir> --out out` を
実行すれば完了する。** parser ロジックは指示書 §3 の確定 reference に準拠。

- 観測: 元 422 JSON が当環境に無い。
- 選択肢: A=パイプライン実装＋fixture 検証で handoff / B=データ取得まで blocked 報告。
- 採択: **A**。
- 理由: parser 仕様は指示書で確定済。実行系を完成させ fixture で gate を満たせば、
  本番スイープは番頭側で 1 コマンド。blocked で止めるより前進量が大きい。

---

## 2. 成果物

### 2.1 実装（src/codex/）
- `article_parser.py` … 指示書 §3 の `parse_article` を忠実実装 + TOC 平坦化
  （flat / nested 両対応、label/page キーの揺れ吸収）。
- `author_normalize.py` … ② 著者正規化（NFKC・敬称除去・所属注記除去・役割語分離・
  内部空白除去 → `author_key`）。
- `egov_index.py` … `data/egov/*.jsonl`（154 法令）から法令名→law_id /
  (law_id, 条)→uri 索引を構築。同名複数 law_id は `ambiguous` フラグ。
- `legal_links.py` … ③ 条文参照→e-gov URI、判例参照→引用グラフ node、confidence 付与。
- `jp_numerals.py` … 漢数字（位取り/桁並べ）・全角数字 → int、枝番「の」対応。

### 2.2 スクリプト（scripts/）
- `run_article_parser.py` … §4.1/4.4/4.5 の 3 ファイルを出力（冪等順序・sha1 表示）。
- `run_legal_links.py` … `legal_links.jsonl` + `legal_links_summary.csv`。
- `author_search.py` … 著者横断検索（検収用）。

### 2.3 fixture に対する生成サンプル（out/, 再生成可能）
| ファイル | sha1 |
|---|---|
| `out/articles_extracted.jsonl` | `101c90dbd51515d9de78500ff058a85164299a97` |
| `out/articles_extracted_summary.csv` | `9b85431c2c59ace5ea235f3823554073ffeb86d1` |
| `out/articles_unknown_sample.csv` | `3c935b606991546d99b94335e6a6ce5cf8ef8046` |
| `out/legal_links.jsonl` | `cb76c9f8aa8f738452d36c15c69917aae430b2fb` |

e-gov ソース（git 履歴から `data/egov/` に復元）:
| ファイル | sha1 |
|---|---|
| `data/egov/egov_statutory_definitions_ALL.jsonl` (18,099 行) | `b7d22bbb060b79ff5537121fb3096d507dcfa1a7` |
| `data/egov/egov_statutory_definitions_ALL_high.jsonl` (5,874 行) | `9c2851129feff121997c68cb7ac65e4f0c2d154b` |

---

## 3. ① article parser — fixture 集計

fixture: `fixtures/legallib_dl/`（journal 4 + book 1）。book は content_type で正しく除外。

| journal | total | article | section | other | unknown | parse_rate |
|---|---|---|---|---|---|---|
| 305760（法セミ No.49・実例） | 8 | 6 | 1 | 1 | 0 | 1.0000 |
| 305761（民法・会社法判例特集） | 10 | 8 | 1 | 1 | 0 | 1.0000 |
| 305762（連載・対談特集） | 11 | 5 | 3 | 1 | 2 | 0.7143 |
| 305763_nested（ネスト TOC） | 4 | 3 | 1 | 0 | 0 | 1.0000 |
| **合計** | **33** | **22** | **6** | **3** | **2** | **0.9167** |

- **hard gate (≥0.80): PASS**, soft target (≥0.90): PASS。
- unknown 2 件はいずれも 305762 の「資料編」配下の異常データ（`あ` / `山田太郎` =
  著者のみ・全角空白なし）。指示書 §3.2-8「空タイトル/著者のみ→unknown」の想定通り。

---

## 4. ② 著者横断検索（検収）

`author_search.py` は articles から正規化キーで逆引き索引を構築:
- distinct authors（正規化後）: 24、author-article links: 27
- **雑誌横断著者: 2 名**（宇賀克也＝305761/305763、大橋洋一＝305761/305763）

検証例:
- 表記揺れクエリ `"山口 厚"`（半角空白入り）→ key `山口厚` に正規化し 305761 をヒット。
- `"宇賀克也"` → 2 雑誌（ジュリスト / 判例タイムズ）を横断ヒット。
- `対談　…　司会・神田秀樹・藤田友敬` の `司会` は role として分離（検索キーから除外）、
  神田秀樹/藤田友敬のみが著者キー化。

→ **著者横断検索 成立。**

---

## 5. ③ 条文・判例リンク（引用グラフの芽 / サンプル目検）

`legal_links.jsonl`: 法令参照 19 + 判例参照 3 = 22 link。

**条 URI が解決した例（高 confidence）:**
- 民法第七百九条 → `egov:129AC0000000089:art:709`
- 会社法423条 → `egov:417AC0000000086:art:423` ✓e-gov 定義突合
- 刑法第百九十九条 → `egov:140AC0000000045:art:199`
- 所得税法56条 → `egov:340AC0000000033:art:56`
- 行政手続法第十四条 → `egov:405AC0000000088:art:14`（最長一致で「行政」等の短名を回避）
- 都市計画法第二十九条 → `egov:343AC0000000100:art:29` ✓e-gov 定義突合

**判例参照（引用グラフ node, 法令へは繋がない）:**
- 最判平成20年1月28日 / 最大判昭和60年3月27日 / 東京地判令和2年9月30日
  （court/era/cite_key を正規化）

**confidence 設計（目検フィルタ用）:**
- high = 条番号を伴う（6 件）／ medium = 語境界が立つ素抽出／
  low = 短法令名が漢字に埋もれた素抽出。
- **既知の偽陽性**: 305760 の「特別刑法」中の「刑法」が 7 件素抽出される
  （`特別刑法` は category で `刑法`=刑法典への引用ではない）。これらは
  **confidence=low** に落としており、目検/下流で除外可能。

---

## 6. 実装判断ログ（§9 フォーマット）

```
- 観測: SECTION_LIKE_PATTERN が「資料編/総論/各論/参考資料」を含むが、
        指示書 reference では SECTION_HEADER_KEYWORDS prefix gating により到達不能で、
        これら bare 見出しが unknown に落ちて parse_rate を不当に下げる。
- 選択肢: A=reference 完全踏襲（資料編→unknown） / B=全角空白を持たない bare 見出しに限り
          SECTION_LIKE_PATTERN 単独で section_header 判定。
- 採択: B。
- 理由: これらの語は指示書が明示的に「section 見出し」として列挙しており、unknown 化は
        意図に反する。著者付きタイトルは必ず全角空白を持つため、ZSP 無し限定なら
        article を誤って section にしない。parse_rate も改善。
```

```
- 観測: 判例引用の地名 prefix `[^\s　、。]{0,6}?` がひらがなを巻き込み、
        「をめぐる東京地判…」を court="をめぐる東京地" と誤抽出。
- 選択肢: A=lazy 量化のまま / B=地名 prefix を漢字 `[一-龥々〇]{1,5}` に限定。
- 採択: B。
- 理由: 日本の裁判所地名は漢字。ひらがな境界で停止し正しく「東京地判」を得る。
```

```
- 観測: 法令名の素抽出は複合語誤検出を生む（「特別刑法」→「刑法」）。
- 選択肢: A=素抽出を全部採用 / B=confidence を付け low に落とす / C=stopword 辞書で除去。
- 採択: B。
- 理由: 網羅性（recall）を保ちつつ目検・下流で precision 制御可能。C は語彙の
        whack-a-mole になり保守困難。条番号付き(high)を最優先シグナルにできる。
```

```
- 観測: 元 JSON の TOC 構造（flat list / nested children / label キー名）が不明。
- 選択肢: A=単一構造を仮定 / B=複数構造を吸収する平坦化を実装。
- 採択: B（iter_toc_nodes が dict/list/nested、label/title/text/name、
        print_page/pdf_page/page を吸収）。
- 理由: 実データ未取得のため構造ゆれに頑健な方が本番スイープの失敗リスクが低い。
```

---

## 7. L1 self-verify（§5 対応状況）

1. 取得率: journal 単位 fail なし（例外時も kind=unknown で entry 出力する実装）。— OK
2. parse_rate hard/soft gate: fixture で 0.9167（both PASS）。**本番は要全 422 スイープ。**
3. 冪等性: 出力順 journal_book_id→ordinal 固定。同一入力で同一 sha1 を再現確認。— OK
4. 構造: 各行に必須 key、kind は 4 種のみ（test で担保）。— OK
5. sha1: §2.3 に記載。— OK
6. サンプル目検: parse_rate<95% は 305762 のみ。unknown=資料編配下の著者のみ行と確認。— OK

---

## 8. 番頭への質問 / 次アクション

1. **本番 422 号スイープ**: `legallib_dl` を当コンテナに供給するか、番頭環境で
   `run_article_parser.py` を実行するか。前者なら本リポジトリのパイプラインで即完了。
2. **法令リンクの confidence しきい値**: 下流投入は high のみ / high+medium のどちら採用か。
3. **判例 node の正規化深度**: 現状 court/era/年月日 文字列まで。事件番号・出典
   （民集/判時 等）まで抽出して引用グラフのキーにするかは別タスク化を提案。
4. **著者 entity の名寄せ**: 現状は表記正規化キーのみ。同姓同名分離 / 別表記統合
   （CiNii author id 等の外部 ID 突合）は Fork 続行タスクとして要否判断を仰ぐ。
