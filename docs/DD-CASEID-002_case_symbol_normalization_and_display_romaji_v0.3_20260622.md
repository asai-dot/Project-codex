# DD-CASEID-002 — 事件符号の正規化と display romaji **v0.3 (再 MODIFY_REQUIRED patch)**

- v0.3 改訂: 2026-06-22 JST（番頭: Claude Code remote）。v0.2 は `superseded_by_v0.3`。
- 監査: v0.1 `MODIFY_REQUIRED`(Box 2299867559432) → v0.2 → **再監査 `DDCASEID_MODIFY_REQUIRED`**(Box 2301890416366, 2026-06-22)。
- closure packet: `DD-CASEID-002_v0.3_closure_packet_20260622.md`
- parent: `DD-CASEID-001`(accepted) / `31c` / `DD-CASE-001`(accepted)

> 再監査で **MF-1/MF-3 CLOSED**。本 v0.3 は **MF-4(BLOCKING)・MF-2・MF-5・P0-1・P0-2・P1-1** を閉じる。中核（かな/漢字 identity・unparsed→provisional）は不変。

---

## 1. 符号正規化 N1〜N5（v0.3 修正）

### 1.1 字形正規化（P0-1 仕様↔コード統一）
segment 正規化＝**NFKC を符号も含め全体に適用**（半角カタカナ `ﾜ`→`ワ` 等を畳み込む。identity-safe）＋全角数字半角化＋空白除去。`{符号}` は NFKC 後さらに NFC。
→ v0.2 までの「符号は NFC 保持（数字/括弧のみ NFKC）」表記は**誤り**。実装と一致させ「符号も NFKC（互換字畳み込み）」に統一。互換字 fixture（`(ﾜ)`→`ワ`）で ratify。

### 1.2 N1〜N5
| 段 | 規則 |
|---|---|
| N1 元号 | 元号観測時のみ `R/H/S/T/M`。**西暦→元号の逆引きはしない（MF-1, CLOSED）**。西暦のみ→`era_resolution_status=unresolved`→provisional |
| N2 数字 | 全角→半角（全 numeric）。**漢数字→算用は元号年のみ（P0-2）**。事件番号/枝番は算用前提、漢数字番号は `unresolved`（fail-closed） |
| N3 符号 | §1.1 の NFKC＋NFC で正準字形。ローマ字化しない |
| N4 区切り | delimiter registry（§2）で分割、`第/年/号/空白/中黒` 除去 |
| N5 枝番 | number と別 field。表示時のみ `-{枝}` |

## 2. 併合事件＝1:N docket（MF-4 closure）
`normalize_dockets(raw) -> [Docket...]`。

- **MF-4-1 後続も full parser を先に適用**。各 segment はまず `{元号}{年}({符号}){番号}` を試み、**era/year/symbol が省略された時のみ**直前 resolved から継承。明示値は継承で**上書きしない**。
  - 例: `令和3年(ワ)第1号、令和4年(ネ)第2号`→`[R3-ワ-1, R4-ネ-2]`（seg2 は自前 era で parsed）。`平成31年(行ケ)第10003号、令和元年(行ケ)第10004号`→`[H31-行ケ-10003, R1-行ケ-10004]`（元号跨ぎ）。
- **MF-4-2 component_basis**: 各 docket に `component_basis{era,year,symbol,number,branch ∈ observed|inherited|unresolved|absent}`・`parse_status{parsed|partial|unresolved}`・`review_status{not_required|review_required}`。継承で resolved した docket は `partial`＋`review_required`。
- **MF-4-3 raw span 保存**: `raw_segment`＋`raw_start/raw_end`（原文オフセット）と `normalized_segment` を別持ち。`raw[start:end]==raw_segment` を fixture で確認。
- **MF-4-4 delimiter registry**: `、 , ， ・ ; ； ／ / 改行 及び 並びに`。未知連結を含む segment は継承で繋がず **fail-closed（unresolved/review_required）**。
- **P1-1**: `is_primary`→**`is_display_primary`**（文字列先頭の表示上の代表。法的主事件性ではない。source 側の主事件指定は別途）。

## 3. display 2表（MF-2 closure・MF-3 維持）
- **`case_symbol_romanization`**（symbol_norm, romaji, romanization_scheme=`alo-display-v1`, scheme_version）: identity非使用・多対一。MF-3 CLOSED 維持。
- **`case_symbol_semantics`**（symbol_norm, forum_level, procedure_kind, case_category, **valid_from, valid_to, meaning_basis, source_ref, source_captured_at, source_hash, status**）:
  - **MF-2 訂正**（meaning_basis=`court_official_definition`）: 行サ=行政上告提起 / 行フ=行政許可抗告 / 行ケ=行政訴訟第一審 / 行ス=行政抗告提起。
  - **source 証跡列**を追加。ただし**公式 doc の version/hash 取得は本リモート不可（no web）→ `source_captured_at`/`source_hash` = `pending_capture`**。よって **confirmed を付与せず `pending_source_fixation`**（24件）。固定できない行を confirmed と偽らない（MF-2 閉鎖条件）。残 `review`（10件）。Mac CC/web で公式 doc を取得・hash 固定後に `confirmed` 昇格。
  - K7: `valid_from/valid_to` は空でなく `unknown` 又は日付（旧法 `ヰ` の valid_to=1947-05-02 は**排他上限**＝同日以降は別機関、を意味）。
  - `status ∈ {pending_source_fixation, review}` は分類・filter・case_type 推定に**供給しない**（confirmed 化まで）。

## 4. verification
- `scripts/case_number_norm.py` v0.3 ＋ `test_case_number_norm.py` = **全 green（exit 0）**。MF-1/MF-4-1..4/P0-1/P0-2/P1-1/同字異義/raw span を網羅。
- `build_case_symbol_tables.py`→2表、`check_case_symbol_tables.py` = **C1-C9 PASS**。
- 証跡（commit SHA/SHA256/実行ログ/fixture対応）は closure packet。
- **corpus-level・公式doc hash 固定は Mac CC/web で別途**（HOLD）。
- independent_meaning_audit = **再 re-audit 待ち**。owner_approval = HOLD。

## 5. GO/HOLD（監査準拠）
- GO: v0.3 patch（本書）・full-tail/component basis・raw span・official source 列・追加 fixture。
- HOLD: accept昇格 / 31c production / DDL / DB write / canonical mint / seed serving / romaji identity 利用 / multi-docket alias 本番確定。
