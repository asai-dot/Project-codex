# DD-CASEID-002 v0.2 closure packet（MF-5 証跡固定）

監査 `DDCASEID_MODIFY_REQUIRED`（Box 2299867559432）の MUST FIX 5点 closure と、再現可能な検証証跡。

## 1. 監査対象の固定（MF-5）
- repo: `asai-dot/Project-codex`
- branch: `claude/precedent-object-progress-gwb47u`
- **commit SHA: `4c2867624861e7cce3a96cc459fba7f8ecae16d5`**

| file | SHA256 |
|---|---|
| scripts/case_number_norm.py | `84a0b873e987f1ca18e61dae5f92c5e608740c36fadee148a8e7692ca828a54f` |
| scripts/test_case_number_norm.py | `ebdcbe5539534e21629472846834245f1109b90ecd2ebe97c2cb060a51809466` |
| scripts/build_case_symbol_tables.py | `c105bb9d1c148af5c91fb1a31a5f7b26b0f0e51e647b73c3863b84da2d39049f` |
| scripts/check_case_symbol_tables.py | `d6e34a0bc290e743b0c24717c1ec20c2d2b545074100875b824f5aa785538107` |
| app/data/case_identity/case_symbol_romanization.csv | `080237d66bfdc8801205d4eee153e4e98c8ed98636e5b9a20faba9ea9a0df3bd` |
| app/data/case_identity/case_symbol_semantics.csv | `2167e13d724475efb84525e648b3ef2401b27e7a1fa0af6cc2003ab3f081d9e3` |
| docs/DD-CASEID-002_..._v0.2_20260621.md | `0c7db1f9df267b876471fe3bf3dee6f08bdabd4f9d7b1239a1f2560f15aa8d87` |

## 2. 実行ログ（再現コマンド付）
```
$ python3 scripts/test_case_number_norm.py
RESULT: PASS (17 fixtures + MF-1/MF-4/同字異義 green)   # exit 0

$ python3 scripts/check_case_symbol_tables.py
romanization=34 semantics=34 confirmed=24 review=10
romaji collisions (display許容): {'wa': ['ワ', 'わ']}
RESULT: PASS (2表健全; MF-2訂正反映; romaji衝突は設計上許容)   # exit 0
```

## 3. N規則 ↔ fixture 対応（MF-5）
| 規則 | fixture tag | 入力例 → 期待 |
|---|---|---|
| N1 元号 | N1, N1元年 | `令和元年(ワ)第1号`→`R1-ワ-1` |
| N2 数字 | N2全角/N2漢数字/N2先頭ゼロ | `令和3年(ワ)第007号`→`R3-ワ-7` |
| N3 符号保持 | N3 | `令和4年(行ウ)第5号`→`R4-行ウ-5` |
| N4 区切り | N4 | `  令和5年 (ネ) 第 45 号 `→`R5-ネ-45` |
| N5 枝番 | N5 | `令和3年(ワ)第123号の2`→`R3-ワ-123-2` |
| MF-1 西暦逆引き禁止 | MF1 / N1元号年保持 | `2019(行ケ)10003`→unresolved/None；`平成31(行ケ)10003`→`H31-行ケ-10003`（西暦化しない） |
| MF-4 多docket | MF4 | `令和3年(ワ)第1号、第2号`→`[R3-ワ-1(primary), R3-ワ-2]` |
| 同字異義 | 同字異義 | `R3-ワ-1 ≠ R3-わ-1` |
| 未解析 | 未解析 | `事件番号不明`→None（provisional） |

## 4. MUST FIX closure 一覧
| MF | 指摘 | closure |
|---|---|---|
| MF-1 | 西暦→元号逆引き禁止 | 元号観測時のみ正規化。西暦のみ→`era_resolution_status=unresolved`→None→provisional。決定日推測なし。fixture `MF1` green |
| MF-2 | seed 法的意味が公式定義と不一致 | 行サ/行フ/行ケ訂正＋行ス追加。`source_basis`/`forum_level`/`valid_from`/`valid_to`/`status`付与。review行は分類非供給。checker C7 で検証 |
| MF-3 | romaji表と意味表の混在 | `case_symbol_romanization`＋`case_symbol_semantics`へ分離。romaji=identity非使用・多対一。checker C5/C6 |
| MF-4 | 先頭docketのみ採用 | `normalize_dockets` 1:N（is_primary/ordinal/source_span、era/symbol継承）。fixture `MF4` green |
| MF-5 | 証跡未固定 | 本packet（commit SHA・SHA256・実行ログ・N↔fixture対応）。§1.3/NFKC表記訂正 |

## 5. 残（HOLD）
- corpus-level 回帰（NII100%/D1 99.94%・norm差分・collision増減・multi-docket回収率・era unresolved率）= Mac CC 実データ。
- review10件の公式典拠確定。
- accept / 31c production / DDL / DB write / canonical mint / seed serving = **re-audit まで HOLD**。
