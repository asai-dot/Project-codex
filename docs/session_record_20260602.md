# 辞書クリーニング・セッション記録 — 2026-06-02

dispatch `DISPATCH-HEADLESS-MIGRATE-001` から始まり、JLT v19.0 着地 → 学陽 Phase1.5 →
3点測量 → 多型OCRミス検出 → 読み訂正適用、までの確定記録。実装は repo
`asai-dot/Project-codex` ブランチ `claude/gakuyo-headless-migrate-AuGAM`（PR #2）。
生データ非改変・訂正は提案/台帳層。

## 1. 基盤データ（確定）
| 資産 | 実体 | 状態 |
|---|---|---|
| JLT v19.0 正典 | Box `05＿語彙レイヤー/jlt_v19_0` golden 8 | **byte-exact 着地・8/8 sha1検証済** |
| JLT 権威見出し語 | repo `data/jlt/` 3,869語 | term-set sha256 `51d767a0…` |
| 学陽 all_entries | repo `data/gakuyo/gakuyo_all_entries.jsonl` 2,684 | byte-exact md→`phase1_5_parse_md.py`（実md2回校正、収録2,603と+1.9%） |
| 有斐閣 all_entries | Box `dict_ocr/all_entries.jsonl` 13,344行 | 既存・構造化済（読み99%） |

## 2. 3点測量（JLT × 学陽 × 有斐閣）
- 在不在: union 15,654、**3源一致 core 922**、学陽のみ564、有斐閣のみ10,159 ほか。
- ツール `phases/triangulate_terms.py`、被覆/成果 `data/triangulation/`、`docs/triangulation_survey_20260602.md`。
- ※第3脚は実体＝有斐閣（指示の「三省堂」は構造化データ無し＝要OCR）。

## 3. 多型OCRミス検出（方法taxonomy: `docs/suspicious_spot_methods.md`）
| 型 | 信号 | 結果 |
|---|---|---|
| **読み化け** | 読み×JLT権威＋多数決 | **37件 確定訂正**（有斐閣33/学陽4）→ §4 |
| 引用誤字 | 引用句×e-Gov本文(A1) | 民法/会社法/刑訴で実証、被覆28%上限。候補: 不法/刑訴378 等 |
| 引用収縮 | 令+4桁 | 学陽3件確定（令9921/5710/2210） |
| 見出し語化け | ed≤1×定義類似 | 低収量（別語/表記ゆれ）＝負 |
| **C2 文字perplexity** | trigram surprisal | **負の結果**（語境界に埋もれる）＝記録し無駄打ち回避 |

## 4. 読み訂正・適用（本日の主成果）
- 台帳 `data/readings/reading_corrections_ledger_20260602.jsonl`（37件、監査可能）。
- **有斐閣33＝パッチ**（canonical `all_entries.jsonl` に owner 適用。verify 2件=図画/競売 は保留）。
- **学陽4＝repo へ in-place 適用済**（`reading_orig`保存・git復帰可）。
- 連濁系48件は `*_review.jsonl` に保留（3票目で決着可）。学陽 truncation 6件は artifact。

## 5. ツール一覧（repo `phases/`）
`phase1_5_parse_md.py`（学陽抽出）/ `build_jlt_authority.py` / `triangulate_terms.py` /
`garble_localize.py` / `reading_triangulate.py` / `reading_adjudicate.py` /
`cross_reference_web.py`（引用抽出・収縮）/ `quote_check_egov.py`（A1）/ `perplexity_scan.py`（C2・負）。
索引 `data/egov/gakuyo_law_index.json`（学陽1,330法令→a2b law_id 78解決＝引用28%）。

## 6. 残課題・次手
- (b) 岡口辞書（無料・ハンド取得）→ review 48件を3票多数決で決着。有斐閣公式ATOK辞書は販売終了。
- (c) A1 を全158法令でローカル一括（cloudは法令ごとI/O重）／長尾72%は e-Gov 未取得＝要取得。
- (d') 有斐閣33読み訂正の canonical 適用（owner 手順）。
- C2 真形は MeCab＋法律語彙のOOV（当環境は MeCab 無し）。

## 7. 掃除メモ
Box `docs/alo` の読取用派生コピー `_TMP_*`（yuhikaku/minpou/kaishaho/keiso）は削除可。
