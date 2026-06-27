# DD-CASEID-002 v0.3 closure packet（再 MODIFY_REQUIRED 対応・MF-5 証跡固定）

再監査 `DDCASEID_MODIFY_REQUIRED`（Box 2301890416366, 2026-06-22）の MF-4(BLOCKING)/MF-2/MF-5/P0-1/P0-2/P1-1 closure と再現証跡。

## 1. 監査対象の固定
- repo: `asai-dot/Project-codex` / branch: `claude/precedent-object-progress-gwb47u`
- **commit SHA: `989dc4ca98062af232c5a7b727d4e9c4d7e51dc9`**

| file | SHA256 |
|---|---|
| scripts/case_number_norm.py | `c9200312717578b391e0eeb7109803e4b82b0393b5dc2b4dd1bdb88d4a9bf846` |
| scripts/test_case_number_norm.py | `aea2d889fe7fe432a47812219c2d75e4b36b3ec242d785d19ea1eed97f1555c2` |
| app/data/case_identity/case_symbol_romanization.csv | `080237d66bfdc8801205d4eee153e4e98c8ed98636e5b9a20faba9ea9a0df3bd` |
| app/data/case_identity/case_symbol_semantics.csv | `da7df47b6882d79a43e9433ba9c7a625b9f4f5a6f7b6228a109b9a19dd216ef8` |
| docs/DD-CASEID-002_..._v0.3_20260622.md | `8a9bab4daf151e78e34ec6a150a9a5d5904d7f2c38826a594aba777cb3d34209` |

## 2. 実行ログ
```
$ python3 scripts/test_case_number_norm.py
RESULT: PASS (16 fixtures + MF-1/MF-4-1..4/P0-1/P0-2/P1-1/同字異義 green)   # exit 0

$ python3 scripts/check_case_symbol_tables.py
romanization=34 semantics=34 status={'pending_source_fixation': 24, 'review': 10}
RESULT: PASS (2表健全; MF-2訂正反映; source未固定はpending明示; romaji衝突は許容)   # exit 0
```

## 3. 再監査 closeout
| 項目 | 前回 | v0.3 |
|---|---|---|
| MF-1 西暦逆引き禁止 | CLOSED | 維持（fixture MF1） |
| MF-3 表分離 | CLOSED | 維持 |
| **MF-4-1** 後続full解析 | PARTIAL/BLOCKING | **CLOSED**: 各 segment full parser 先行、省略時のみ継承、明示値上書きせず。fixture `MF41`（同era別year・元号跨ぎ） |
| **MF-4-2** component provenance | 欠落 | **CLOSED**: `component_basis`(observed/inherited/unresolved/absent)・`parse_status`・`review_status`。fixture `MF42` |
| **MF-4-3** raw span | 不正 | **CLOSED**: `raw_segment`+`raw_start/raw_end`+`normalized_segment`。fixture `MF43`（`raw[s:e]==raw_segment`） |
| **MF-4-4** delimiter coverage | 狭い | **CLOSED**: registry（、,，・;；／/改行/及び/並びに）。未知連結 fail-closed。fixture `MF44` |
| **MF-2** 公式source固定 | PARTIAL | **PARTIAL→明示**: 訂正反映＋`source_ref/captured_at/hash/valid_from/valid_to` 列追加。hash 取得は no-web ゆえ `pending_capture`、confirmed 付与せず `pending_source_fixation`。**doc hash 固定は Mac CC/web 委譲**（corpus 同様） |
| **MF-5** fixture 不足 | PARTIAL | **CLOSED**: 後続full/元号跨ぎ/継承basis/未知delimiter/raw span/互換字/漢数字番号 を追加 |
| **P0-1** NFKC範囲 | 矛盾 | **CLOSED**: 符号も NFKC（互換字畳み込み）と明示、仕様↔コード一致。fixture `P01`(ﾜ→ワ) |
| **P0-2** 漢数字範囲 | 不明 | **CLOSED**: 元号年のみ。漢数字事件番号は unresolved。fixture `P02` |
| **P1-1** primary 命名 | 誤誘導 | **CLOSED**: `is_display_primary` |

## 4. N規則・MF ↔ fixture 対応
| 観点 | fixture tag |
|---|---|
| N1/N1元年/N2全角/N2漢数字(年)/N2先頭ゼロ/N3/N4/N5 | 同名 tag |
| MF-1 西暦→unresolved | MF1 |
| MF-4-1 後続full(同era別year/元号跨ぎ) | MF41 |
| MF-4-2 component basis(継承/明示) | MF42 |
| MF-4-3 raw span offset | MF43 |
| MF-4-4 未知tail fail-closed | MF44 |
| P0-1 互換字 ﾜ→ワ | P01 |
| P0-2 漢数字番号→None | P02 |
| P1-1 is_display_primary | P11 |
| 同字異義 民事ワ≠刑事わ | 同字異義 |

## 5. 残（明示 HOLD）
- **公式 doc の version/hash 固定**（MF-2 完全閉鎖）= Mac CC/web（no-web のため本リモート不可）。固定後に `pending_source_fixation`→`confirmed` 昇格。
- corpus-level 回帰（NII100%/D1 99.94%・norm差分・collision・multi-docket回収率・era unresolved率）= Mac CC 実データ。
- accept / 31c production / DDL / DB write / canonical mint / seed serving = re-audit 通過＋owner ratify まで HOLD。
