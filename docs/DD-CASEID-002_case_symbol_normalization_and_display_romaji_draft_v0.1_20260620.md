# DD-CASEID-002 — 事件符号の正規化と display romaji 表（識別はかな/漢字・romajiは表示専用）**draft v0.1**

- 起票: 2026-06-20 JST ／ 番頭: Claude Code (remote)
- lifecycle: **draft / candidate**（GPT Pro 独立監査 未了 → DDCASEID ゲート）
- domain: CASEID（判例ID確定 / 符号正規化）。**DD-CASEID-001 の下位DD**（accepted v1.0 §5 follow-up で予告）
- parent: `DD-CASEID-001`(accepted v1.0) / `31c_case_number_norm_spec.md`(符号正規化 実装仕様) / `31_case_layer.md`
- related: `DD-CASE-001`(accepted v1.0／case_type・node schema 供給) / `DD-CASEID-003`(forum registry)

> **確定前提（DD-CASEID-001 で accept 済・本DDは覆さない）**: `case_number_norm` は事件符号を**かな/漢字のまま保持**する正準形 `{ERA}{year}-{符号}-{number}`。**ローマ字化しない**。ローマ字を identity / dedup キーにすることは §2 で却下済（同字異義・長い裾で対応表不完全→dedup破壊）。本DDの romaji は **display/検索補助 専用**で、正準キーには一切用いない。

---

## 0. スコープ

DD-CASEID-001 が「正準は かな/漢字」を確定した上で、残る2点を実装粒度に落とす：

1. **符号正規化**（normalization）: 生の事件番号文字列 → `case_number_norm` を決定的に生成する規則（全角/半角・元号・符号異体・区切り）。解析率は実測済（NII 100.00%(65,853/65,855) / D1 99.94%(68,099/68,141)、DD-CASEID-001 §4）。本DDはその**規則を明文化**し、未解析の裾（NII 2件 / D1 42件）の扱いを定める。
2. **display romaji 表**（表示専用）: 事件符号（かな/漢字）→ romaji の対応表。UI 表示・ローマ字検索・URL slug 補助に使う。**identity ではない**。

## 1. 決定

### 1.1 符号正規化規則（→ `case_number_norm`）
正準形 `{ERA}{year}-{符号}-{number}`（DD-CASEID-001 §1.3）を生成する決定的変換：

| 段 | 規則 | 例 |
|---|---|---|
| N1 元号 | 元号は正準コードへ（令和=R / 平成=H / 昭和=S / 大正=T / 明治=M）。西暦混在は元号へ逆引き（境界年は重複期間表で確定） | 令和3年→`R3` |
| N2 数字 | 全角数字→半角。漢数字（十二→12）も算用へ。先頭ゼロ除去 | `０１２`→`12` |
| N3 符号 | 事件符号は**かな/漢字の正準字形**へ（NFC＋異体統合表 §1.3）。ローマ字化しない | `ワ`(全角カナ)を正準カナへ |
| N4 区切り | `第`/`号`/空白/中黒を除去、`{ERA}{year}-{符号}-{number}` に再構成 | `令和3年(ワ)第123号`→`R3-ワ-123` |
| N5 枝番 | 枝番（の2 等）は number 末尾に `-枝` で保持（分離しない） | `123の2`→`123-2` |

- **決定性**: 同一入力→同一 norm（DD-CASEID-001 の `fn_generate_case_uri_v2` が前提とする不変条件）。
- **未解析の裾**（N3で符号が異体辞書に無い等）: **`norm=null` のまま provisional 採番**（DD-CASEID-001 §1.5、case_key不変）。捨てない・推測しない。`resolution_log` に `unparsed_symbol` で記録し人手確定へ。

### 1.2 display romaji 表
- スキーマ: `symbol`(かな/漢字, 正準字形) / `romaji` / `instance`(審級・手続) / `category`(民事/刑事/行政/家事/…) / `meaning` / `status`(confirmed/review)。
- **用途限定**: 表示・ローマ字入力検索・slug 補助のみ。**dedup・FK・自然キーに使わない**（AC＝DD-CASEID-001 §2 rejected の維持）。
- **多対一を許容**: 異なる符号が同じ romaji に落ちてよい（display では衝突可、identity では別物）。逆引き（romaji→symbol）は**候補集合**を返す（一意でない）。
- seed: `case_symbol_display_romaji_seed.csv`（本DD同梱、コア符号。status=review は人手確定待ち）。

## 2. why / alternatives_rejected
- **why 表示romaji を別に持つ**: 正準は かな/漢字だが、UI のローマ字検索・英字環境・slug にはローマ字が要る。これを正準キーに混ぜると DD-CASEID-001 §2 の dedup 破壊が再発するため、**表示専用の片方向表**として隔離する。
- **rejected**: romaji を norm に含める（却下＝CASEID-001 §2）。romaji 逆引きを一意キー化（同字異義で衝突＝却下、候補集合に留める）。未解析符号を最近傍 romaji に丸める（誤同定リスク＝却下、provisional へ）。

## 3. downstream_effect
- 新規 DB write なし（**設計確定のみ**、DD-CASE-001 AC-6 / DD-CASEID-001 AN-5 の HOLD 継承）。
- `case_observation` 取込時に N1〜N5 を適用し norm を埋める（実装は 31c）。romaji 表は display 層でのみ join。
- forum_registry_seed（CASEID-003）と独立（符号は forum 非依存）。

## 4. verification（昇格条件・現状）
- deterministic_self_verification = **fixture-level done / corpus-level pending**:
  - `case_number_norm.py`（N1〜N5 参照実装）＋ `test_case_number_norm.py` = **16/16 fixtures green（exit 0）**。N1元号・N2全角/漢数字/先頭ゼロ・N3符号保持・N4空白除去・N5枝番・同字異義(民事ワ≠刑事わ)・未解析→None を網羅。
  - `check_case_symbol_romaji_seed.py` = PASS（symbol一意・romaji衝突 wa を許容報告）。
  - **corpus-level**（NII 100.00% / D1 99.94% の回帰再現）は Mac CC 実データで別途（本リモートにデータ無）。
- independent_meaning_audit = **未了**（本draftを DDCASEID ゲートへ）。
- owner_approval = **未了**。

## 5. follow-up
- romaji seed の `status=review` 符号（異体・旧法・知財審決取消 行ケ 等）を人手確定。
- 元号境界年（改元年の重複）確定表を 31c と共有。
- 未解析裾（NII2/D1 42）の実サンプルを `CASE_HUMAN_REVIEW_SAMPLE_FRAME`（DD-CASEID-001 §5）へ。
