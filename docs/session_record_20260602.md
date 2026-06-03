# 辞書クリーニング・セッション記録 — 2026-06-02（v2 全体版）

`DISPATCH-HEADLESS-MIGRATE-001` 起点。JLT v19.0 着地 → 学陽 Phase1.5 → 3点測量 →
多型OCRミス検出（読み／引用／本文）→ 読み訂正適用、までの確定記録。
実装は repo `asai-dot/Project-codex` ブランチ `claude/gakuyo-headless-migrate-AuGAM`（PR #2）。
**生データ非改変・訂正は台帳/提案層（auto_apply=false）**。

## 1. 基盤データ
| 資産 | 実体 | 状態 |
|---|---|---|
| JLT v19.0 正典 | Box `05＿語彙レイヤー/jlt_v19_0`(386440014344) golden8 | byte-exact 着地・8/8 sha1検証 |
| JLT 権威見出し語 | repo `data/jlt/` 3,869 | term-set sha256 51d767a0… |
| 学陽 all_entries | repo `data/gakuyo/` 2,684 | byte-exact md→phase1_5（収録2,603+1.9%） |
| 有斐閣 all_entries | Box `dict_ocr/all_entries.jsonl`(2185088113728) 13,344 | 既存・構造化済（読み99%） |

## 2. 3点測量（JLT×学陽×有斐閣）
union 15,654 / **3源一致 core 922** / 学陽のみ564 / 有斐閣のみ10,159。
`phases/triangulate_terms.py`、`docs/triangulation_survey_20260602.md`。

## 3. 多型OCRミス検出 — 結果
| 型 | 信号 | 成果 |
|---|---|---|
| **読み化け** | 読み × JLT権威 ＋ 多数決(5源) | **確定訂正 44件**（有斐閣中心）→ §4 |
| 引用誤字(A1) | 引用句 × e-Gov本文 | 7法令で実証。**学陽≒有斐閣**（§5） |
| 引用収縮 | 令+4桁 | 学陽3件確定（令9921/5710/2210） |
| 見出し語化け | ed≤1 × 定義類似 | 低収量＝負 |
| C2 文字perplexity | trigram surprisal | **負**（語境界に埋没） |

## 4. 読み訂正（本日の最高歩留まり・5ソース多数決）
ソース: JLT(権威100%) / 有斐閣(99%) / 学陽(2%) / **法律用語がわかる辞書**(EX-word抽出2,694) /
**法律用語IME辞書**(Togi Lab、1,510)。
- **確定訂正 計44件**（台帳 `data/readings/reading_corrections_ledger_20260602.jsonl`）。
  有斐閣33パッチ＋学陽4適用済＋多数決追加。例: 機関訴訟そうしょう→そしょう、被疑者ひきぎしゃ→ひぎしゃ、
  過誤納かごうのう→かごのう、親等いっしんとう→しんとう。
- **JLTが少数派＝誤りの2件**発見（保健所ほけんじょ・商事会社がいしゃ＝有斐閣が正）。JLTも万能でない。
- 連濁系の残39件は2源のみで未決。学陽truncation6件はartifact。
- `phases/reading_triangulate.py` / `reading_adjudicate.py`。

## 5. A1（引用×e-Gov）と「学陽≒有斐閣」結論
- 7法令（民法/会社法/刑訴/地自/国公/国税/民訴。law_id は a2b＋依存グラフ合成索引で解決、
  各 law_title を実ファイル検証＝地方自治法=322AC0000000067 自己確認）。
- 学陽: 144帰属引用→97 verbatim clean、候補は送り仮名/版差中心。
- 有斐閣: blob照合で実誤り **信義誠実「従わ」→民法1②「行わ」(従→行)** を検出。略語帰属(法令略語tsv)で
  精密化＝58帰属/33clean/候補3（版差・ルビ・境界＝非OCR、偽陽性除去）。
- **結論（head観測の裏取り）**: 学陽≒有斐閣。引用本文の実OCR誤りは両者**少数・同水準**。
  当初「学陽は綺麗」は方法バイアス（学陽=厳密帰属法／有斐閣=広いblob法）。apples-to-apples で
  学陽もblob法なら同数19候補・同偽陽性。**同系統OCRなら誤り率は近い**。
- 運用知見: 精密(略語帰属)=偽陽性0だが出典非隣接を取りこぼす／再現(blob)=拾うが偽陽性。**両者併用**。
- 被覆: 合成索引で law_id 解決=引用の27%。長尾73%は e-Gov 未取得＝フル走はローカルが効率的。

## 6. 発見した資産・空振り
- **法律用語がわかる辞書 第2版**（Box `decrypted/法律用語辞書.txt`、EX-word抽出）: 見出し語+読み2,694対
  クリーン（定義は暗号化で不可）→ `data/wakaru/`。
- **法律用語IME辞書**（Togi Lab「法律用語辞書 IME版」、浅井提供、1,510対）→ `data/legal_ime/`。再配布許諾は要確認。
- **法令略語表**（有斐閣 `dict_ocr/law_abbreviations.tsv` 約340）= A1の引用帰属に使用。
- **空振り**: BKUP.TXT/JSIBKRS.* = ジャストシステムのバックアップツール（辞書データでない）。
  有斐閣公式ATOK辞書=販売終了。EX-word法律用語辞書の**定義**は暗号化（復号は別タスク）。

## 7. ツール（repo `phases/`）
phase1_5_parse_md / build_jlt_authority / triangulate_terms / garble_localize /
reading_triangulate / reading_adjudicate / cross_reference_web / quote_check_egov /
perplexity_scan(負). 索引 `data/egov/gakuyo_law_index.json`。

## 8. 残課題・次手
- 連濁 review 残39（より高被覆の読みソースが要る）。
- 有斐閣33読み訂正の canonical 適用（owner手順、verify2件=図画/競売 要確認）。
- A1 全158法令ローカル一括＋長尾 e-Gov 取得。
- EX-word「法律用語がわかる辞書」定義の復号（第3の定義辞書化）。
- 掃除: Box `docs/alo` の `_TMP_*`（egov/有斐閣 読取コピー多数）は削除可。

## 9. 設計原則（貫徹）
suspect/台帳層・自動修正なし／「派生物を正本扱いしない」(review_queue 129件の轍)／measure-then-build／
権威は万能でない（JLT少数派2件）。
