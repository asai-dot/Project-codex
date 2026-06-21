# DD-CASEID-002 — 事件符号の正規化と display romaji（識別はかな/漢字・romajiは表示専用）**v0.2 (MODIFY_REQUIRED patch)**

- 起票: 2026-06-20 ／ **v0.2 改訂: 2026-06-21 JST**（番頭: Claude Code remote）
- lifecycle: draft v0.1 → **v0.2 patch**（監査 `DDCASEID_MODIFY_REQUIRED` 2026-06-21 の MUST FIX 5点反映）→ **re-audit 待ち**
- 監査: `20260620_caseid_v0.1_DDCASEID002_RESULT.md`（Box 2299867559432）。v0.1 は `superseded_by_v0.2`。
- parent: `DD-CASEID-001`(accepted v1.0) / `31c_case_number_norm_spec.md` / `DD-CASE-001`(accepted v1.0)

> 監査が ADOPT した中核は維持：(1) `case_number_norm` は かな/漢字保持・romaji を identity/dedup/FK に使わない、(2) 解析不能は `norm=null`＋provisional（推測・最近傍丸めしない）。v0.2 は MUST FIX 5点（MF-1 西暦逆引き禁止 / MF-2 公式定義訂正 / MF-3 表分離 / MF-4 多docket / MF-5 証跡固定）を反映。

---

## 0. スコープ
DD-CASEID-001 確定（正準は かな/漢字）の下で、(1) 符号正規化 N1〜N5、(2) display romaji と手続意味の**分離2表**を実装粒度に落とす。

## 1. 決定

### 1.1 符号正規化規則 N1〜N5（→ `case_number_norm`）
正準形 `{ERA}{year}-{符号}-{number}[-{枝}]` を決定的に生成（参照実装 `scripts/case_number_norm.py`）。

| 段 | 規則 | 実装 | 例 |
|---|---|---|---|
| N1 元号 | **元号が観測できる入力のみ** `R/H/S/T/M` へ。**西暦→元号の自動逆引きはしない（MF-1）** | 元号トークン必須。`元`=1 | 令和3→`R3` |
| N2 数字 | 全角→半角・漢数字→算用・先頭ゼロ除去 | NFKC＋漢数字変換 | `０１２`/`十二`→`12`/`7` |
| N3 符号 | 符号は**かな/漢字の正準字形**(NFC)で保持。ローマ字化しない | `unicodedata.normalize("NFC", sym)` | `ワ`→`ワ` |
| N4 区切り | `第`/`年`/`号`/空白(全角含)/中黒 を除去し再構成 | NFKC後 `\s+` 除去＋正規表現 | `令和3年(ワ)第123号`→`R3-ワ-123` |
| N5 枝番 | 枝番は number と**別 field**に保持し、表示時のみ `-{枝}` 直列化（SHOULD-FIX#1） | `branch` field | `123の2`→`R3-ワ-123-2` |

- **MF-1 元号解決**: `era_resolution_status ∈ {resolved, unresolved}`。西暦のみ/元号不明は `unresolved`→`norm=null`→provisional。決定日から推測しない。変換時は `resolution_basis`＋evidence observation ID を残す（実装は production/31c）。
  - 根拠例（監査提示）: `平成31(行ケ)10003` は令和元年判決、`平成31(ネ)10034` も令和元年判決 → 西暦2019から H31/R1 を一意決定できない。
- **N3 字形正規化**: NFKC は数字/カッコの半角化に用い、**符号字形は NFC で保持**（v0.1 の「NFC＋異体統合表 §1.3」表記は誤り。異体統合表は将来別表、本DDに §1.3 は無い）。

### 1.2 併合事件＝1:N docket 観測（MF-4）
一判断は複数 docket を持ちうる。先頭だけ採らない。

- `normalize_dockets(raw) -> [Docket...]`。各 Docket は `norm / symbol / number / branch / is_primary / ordinal / source_span / era_resolution_status`。
- 後続 docket は区切り（`、・,`）分割で回収し、era/year（必要なら symbol）を先頭から**継承**。全 docket を個別正規化。
- canonical URI は代表（`is_primary`）番号で生成してよいが、**残りは alias/fingerprint として必ず解決可能**に保つ（raw 文字列に閉じ込めない）。
- 例: `令和3年(ワ)第1号、第2号`→`[R3-ワ-1(primary), R3-ワ-2]`／`令和3年(ワ)第1号・(ネ)第9号`→`[R3-ワ-1, R3-ネ-9]`。

### 1.3 display 2表（MF-3：romaji と意味を分離）
1表に混在させず分離する：

- **`case_symbol_romanization`**（`symbol_norm, romaji, romanization_scheme, scheme_version`）: 表示専用・**identity非使用**・多対一許容。`romanization_scheme=alo-display-v1`（標準ローマ字でなくALO表示規約・版管理。SHOULD-FIX#2）。逆引きは候補集合（単独で case bind しない）。URL slug は romaji 単独をルートにせず `case_key` 等の不変anchorを併記。
- **`case_symbol_semantics`**（`symbol_norm, forum_level, procedure_kind, case_category, valid_from, valid_to, source_basis, status`）: forum・時期依存の法的意味を複合スコープで解決。`status=review` 行は**意味分類・検索filter・case_type推定に供給しない**（MF-2 閉鎖条件）。

**MF-2 公式定義訂正**（裁判所「符号の説明」着地、`source_basis=court_official`）:

| symbol | v0.1 (誤) | v0.2 (訂正) |
|---|---|---|
| `行サ` | 行政 抗告 | **高裁 行政上告提起**（`gyosei_jokoku_teiki`） |
| `行フ` | 行政 雑 | **最高裁 行政許可抗告**（`gyosei_kyoka_kokoku`） |
| `行ケ` | 知財審決取消に限定 | **高裁 行政訴訟事件(第一審)**（知財審決取消は主要例だが定義全体でない） |
| `行ス` | （無し） | **高裁 行政抗告提起**（新規・行サと峻別） |

執行系・家事ロ・人事訴訟タ・少年・旧法符号は公式典拠着地まで `status=review` 据置。少年事件の非公開性は**符号辞書でなく case observation/content の出口ACLで強制**（SHOULD-FIX#4／AC-3）。

## 2. why / alternatives_rejected
- romaji を正準キー化（REJECT＝CASEID-001 §2）。
- **西暦→元号の自動逆引き（REJECT AS WRITTEN, MF-1）**：受理時元号年と判決日元号が一致しない例があり一意に閉じない。
- **先頭docketのみ正規化（REJECT AS IDENTITY MODEL, MF-4）**：第二以降を別名/観測キーとして名寄せ・検索できなくなる。
- 未解析符号の最近傍丸め（REJECT＝誤同定）。

## 3. downstream_effect
- 新規 DB write なし（**設計確定のみ**、AC-6 / AN-5 HOLD 継承）。
- 取込時に N1〜N5＋docket 1:N を適用。romanization は display 層 join、semantics は forum＋時期で解決。

## 4. verification（MF-5：再現可能に固定）
- `scripts/case_number_norm.py` v0.2 ＋ `scripts/test_case_number_norm.py` = **fixtures 全 green（exit 0）**。N1〜N5＋MF-1（西暦→unresolved）＋MF-4（多docket）＋同字異義（民事ワ≠刑事わ）を網羅。N規則↔fixture 対応は test 冒頭 MAPPING。
- `scripts/build_case_symbol_tables.py` → `case_symbol_romanization.csv` / `case_symbol_semantics.csv`（各34行, confirmed24/review10）。`scripts/check_case_symbol_tables.py` = **PASS**（C1-C7：symbol一意・romaji衝突許容報告・status値域・wa併存・2表参照健全・review行はcourt_official詐称せず・MF-2訂正反映）。
- **証跡固定**: commit SHA / branch / file SHA256 は closure packet `DD-CASEID-002_v0.2_closure_packet_20260621.md` に記載。
- **corpus-level（NII100%/D1 99.94%回帰・norm差分・collision増減・multi-docket回収率・era unresolved率）は Mac CC 実データで別途**（SHOULD-FIX#5）。
- independent_meaning_audit = **re-audit 待ち**（v0.1=MODIFY_REQUIRED）。owner_approval = HOLD until re-audit。

## 5. follow-up / SHOULD-FIX
- SF#1 number/branch を内部別field（実装済）。SF#2 romanization_scheme 版管理（実装済 alo-display-v1）。SF#3 元号年・番号の構文範囲チェック（範囲外は推測せず review）。SF#4 少年非公開は出口ACLで強制。SF#5 corpus 回帰指標。
- review10件（執行系・家事ロ・人事訴訟・少年・旧法・ツ・ミ）の公式典拠確定。
