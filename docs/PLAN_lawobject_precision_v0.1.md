# PLAN — 法令オブジェクト「精度に効く手」v0.1（後から効く順）

- 作成: 2026-06-22 / owner: 浅井 / head: Project-codex (claude-code remote)
- 位置づけ: production 工程表 [`PLAN_DD-LAWSUBTRANS-001_production_v0.1.md`](PLAN_DD-LAWSUBTRANS-001_production_v0.1.md)
  （P0 lawtime → P1 DDL → P2 ingest → P3 較正 → P4 curation → P5 MCP）とは**別カット**。
  あちらは「production apply まで配管を通す」工程。本書は **「法令オブジェクトの精度（precision/recall）
  を上げる手」を、複利で後から効く順に並べた**もの。両者は直交し、地盤レバー（L1/L2）は production
  工程のどのフェーズよりも先に着手できる。
- 一言で: **いま致命的なのは「精度を上げる手」が無いことではなく、「精度を測る物差し」と「精度を守る柵」が
  無いこと**。測れて・守れて初めて、閾値較正もパターン追加も ML 層も“効いた”と証明できる。

---

## 0. 現況の精度的評価（なぜ地盤から始めるか）

| 事実 | 精度上の含意 |
|---|---|
| producer 5層は実装完・unit test 715行 GREEN | ロジックは動く。**だが採点されていない** |
| 閾値が fixture 値（lawdelta `SUBST_MIN=0.50` / `RENUMBER_SIM=0.92` / `RELOCATE_SIM`、cue 確度上限 medium） | **勘の値**。実データでの P/R 未測定 |
| 入力は demo 合成データのみ（民法改正4項目） | producer は**実 e-Gov XML も実判例テキストも一度も通していない** |
| CI（`.github/workflows/ci.yml`）は購買レコメンド＋Supabase の2本だけ | **producer の 715行テストも自己 gate も CI 不在**＝回帰の床が無い |
| assembler のグルーピングは条 root の v0.1 ヒューリスティック（`art:415:para:1 → art:415`） | dispute の成否＝同定精度に直結。**誤 dispute / 見逃しが測れていない** |

→ 結論: **測れる化（L1）と守れる化（L2）を最初に置く**。これらは外部依存ゼロ・今すぐ着手でき、
以後のあらゆる較正・拡充の前提（複利の元本）になる。

---

## 1. レバー一覧（後から効く順）

| # | レバー | 効き方 | 依存 | 工数 | 期待効果 | 着手可否 |
|---|---|---|---|---|---|---|
| **L1** | 測れる化：ゴールド評価セット＋評価ハーネス | 🟢 複利（元本） | なし（実データは段階的） | 中 | 全較正の前提。P/R を pattern_id 単位で可視化 | **今すぐ**（雛形は空ラベルでも動く） |
| **L2** | 守れる化：CI に producer テスト＋"非 accepted/非 claim_support" gate | 🟢 複利（床） | なし | 小 | 回帰防止。過信 assertion 流出を恒久封鎖 | **今すぐ** |
| **L3** | 素材：real-lane（e-Gov 実 XML・実判例テキスト） | 🟢 複利（土） | 環境/調達 | 中 | L1 のラベル母集団。実分布で初めて精度が現実値に | 権限・調達次第 |
| **L4** | 同定の地盤：article_path 正規化＋lawtime resolved view 接続（article crosswalk） | 🟡 構造的 | lawtime 側 apply に一部依存 | 中 | dispute の join key を正す＝誤 dispute/見逃しの根を断つ | 設計は先行可 |
| L5 | 項・号粒度（条→`art:X:para:n:item:m`） | 🔵 局所 | L1 | 中 | どの規定が変わったかの分解能↑ | L1 後 |
| L6 | stance 射影の精緻化（過剰 dispute 削減） | 🔵 局所 | L1 | 小 | 「新設だが法理継続」等の誤 dispute を削る | L1 後 |
| L7 | cue 拡充 → ML/LLM recall 層 | 🔵 局所 | L1/L3 | 大 | recall↑。**ルール＋ゴールドの上に載せる** | L1/L3 後 |

着手順（推奨）: **L1+L2 を同時 → L3 の段取り → L4 → （L5/L6/L7 はゴールドセット完成後）**。

---

## 2. L1 — 測れる化：ゴールド評価セット＋評価ハーネス 🟢

### 何が問題か
閾値も cue 確度も実測根拠なし。**「閾値を 0.50→0.55 にしたら精度が上がった/下がった」を言える基盤が無い**。
これが無い限り、L5–L7 を含む後続の改善はすべて“感想”にしかならない。

### 作るもの
1. **ゴールドセットの様式**（`tests/gold/` に JSONL）
   - `lawdelta`: 既知改正ペアの条文ごとに正解 `delta_kind`（＋ counterpart）。例: 2017 債権法改正。
     検証器に公式新旧対照表・名大「改め文」16 パターンを使う。
   - `drafterintent`: 逐条解説/一問一答の抜粋スパンごとに正解 `change_type` と source_type。
   - `casetreatment`: 判決の評価窓ごとに正解 `treatment_relation`（と当事者抑制すべき箇所）。
   - `assembler`: 入力 assertion 群に対し dispute が成立すべきか（target 単位の正解ラベル）。
2. **評価ハーネス**（`scripts/eval/`、stdlib のみ・空ラベルでも動く）
   - 入力: gold JSONL ＋ producer の出力 JSONL。
   - 出力: **pattern_id / delta_kind / treatment 単位の precision・recall・confusion**（Paxton 流 per-label 公開）。
   - `--gold` 未指定や 0 件でも「母数0」で正常終了（CI に常駐させても落ちない）。
   - 出力は `out/eval_<run>_summary.json` ＋ Markdown。

### 着手の現実解（実データ前でも価値が出る）
- まず **demo fixture を“仮ゴールド”として配線**し、ハーネスが P/R を吐く配管を完成させる。
- 実ラベルは L3 と同期して充填（最初は債権法改正の数十条＋判決10数件で十分に効く）。

### 出口
ハーネスが pattern_id 単位 P/R を出す → 以後の閾値・cue 変更は**この数字で採否**（版管理）。

---

## 3. L2 — 守れる化：CI に producer テスト＋恒久 gate 🟢

### 何が問題か
`ci.yml` は法令オブジェクトを一切見ていない。**分類ロジックが静かに壊れても、producer がうっかり
`accepted`/`claim_support_eligible=true` を吐いても、誰も気づかない。** 安全弁（DD §10.1-6）が
設計には在るが CI には無い。

### 作るもの（`.github/workflows/ci.yml` に追加）
1. **producer 5モジュールの unit test を CI に載せる**
   ```yaml
   - name: Run law-object producer tests (stdlib only, no DB)
     run: |
       python tests/test_lawdelta.py
       python tests/test_drafterintent.py
       python tests/test_casetreatment.py
       python tests/test_assembler.py
       python tests/test_mcprender.py
   ```
2. **恒久 gate（snapshot/契約テスト）を新規追加**（`tests/test_producer_invariants.py`）
   - すべての producer summary で `db_writes == 0`。
   - drafter/casetreatment 出力の全行 `assertion_status == 'candidate'`、`claim_support_eligible == false`。
   - assembler 出力に `current_status == 'accepted'` や `claim_support_eligible == true` が**一切無い**。
   - mcprender 出力に断定フレーズ（「現在も有効です」等）が無い・disputed は両論・`unknown` を根拠に使わない。
   - lawdelta 出力に実質フィールド（`change_type` 等 `FORBIDDEN_SUBSTANTIVE_FIELDS`）が混入しない。
3. **評価ハーネス（L1）を CI に常駐**（ゴールド0件でも緑、充填後は閾値割れで赤）。

### なぜ後から効くか
今日の精度の数字は上げない。だが**今後の全編集を永続的に守る**＝精度が静かに劣化する経路を塞ぐ。
最も安く、最も長く効く。DD §10.1 の宿題 5・6 をそのまま CI gate 化するもの。

### 出口
PR が producer テスト＋不変 gate を必ず通る。回帰は CI で赤くなる。

---

## 4. L3 — 素材：real-lane の確保 🟢

### 何が問題か
全部 demo 合成。**実分布を一度も見ていない**ので、精度数字は現状フィクション。

### 段取り（コードでなく権限・調達中心）
- **e-Gov 実 XML**: 本リモート環境は e-Gov API が許可リスト外（403）。
  代替: 既存 `alo-kg/raw/egov_revisions/`（取得済 revisions）を入力に lawdelta を実走（PLAN 示唆6）。
- **実判例テキスト**: D1-Law 契約 355 件で開始 → 法務省 民事判決 DB（2026 年度運用開始）で拡張。
- **実逐条解説/一問一答**: PDF/書籍の L0 raw 化（既存 bib/TOC レーン接続。本書スコープ外だが前提）。

### 出口
L1 ゴールドセットに実ラベルを充填できる状態。最初は「債権法改正の数十条＋判決十数件」で十分。

### 進捗（2026-06-23, real-lane 実証 ✅ — サンドボックスで実行）
e-Gov API は 403 だが **GitHub clone は通る**ことを使い、**実 e-Gov 標準 XML で lawdelta を実走できた**:
- 実民法 XML 2 版を GitHub から取得（`japanese_law_xml_schema` のテスト XML=2023-06-14 / `gitlaw-jp`
  の current=2025-10-01 施行）。**XML 本体はリポジトリに入れない**（外部データ）。
- 結果: 1164 条パース（枝番・削除 shell 含む）→ diff 1167 行（**substitution14/insertion4/repeal2/join1
  = 21 条の実改正**）、**全 gate pass**。＝producer が fixture でなく**実データで動く**ことを実証。
- 成果物: 手順 [`scripts/lawdelta/REALLANE.md`](../scripts/lawdelta/REALLANE.md) ＋ **候補 gold ワークリスト**
  `tests/gold/lawdelta_minpo_20230614_20251001.candidate.jsonl`（21 条・producer 予測・`verified:false`）。
- **残: 新旧対照表での人手検証**（asai）→ `delta_kind` 記入＝real gold 化 → `scripts.eval --min-f1` で
  pattern 単位 P/R 較正。＝L1 の物差しに**実データの一発目**が乗る一歩手前。

---

## 5. L4 — 同定の地盤：article_path 正規化＋lawtime 接続 🟡

### 何が問題か
dispute は「**同じ条文に主張が集まるか**」で決まる。いまの同定は:
- `article_path` は e-Gov URI tail の素のまま、`law_work_id` は NULL 可、
- assembler のグルーピングは `art:415:para:1 → art:415` の **v0.1 ヒューリスティック**。

→ ゆるいと **誤 dispute（別物を同一視）／見逃し（同一物を別グループ化）** が直接出る。
全 assertion の identity を支える根なので、ここがブレると L1 の数字も信用できない。

### 作るもの
- **article_path 正規化器**（漢数字・枝番・項号の正準化、`drafterintent/extract.py` の正規化と統一）。
- **article crosswalk**: 改正前後で条番号が動く（繰下げ・split/join）場合の旧↔新 path 対応表。
  lawdelta の `delta_kind=renumber/relocate/split/join` 出力を crosswalk の素にできる。
- **lawtime resolved view 接続**: `law_work_id`/revision を lawtime の resolved view で解決し、
  grouping を「正準 work × 正準 article」に固定（DD gate 9/10/13 の前提）。

### 依存
lawtime v0.2.3 apply（production PLAN P0）に一部依存。ただし**正規化器と crosswalk の設計・単体実装は
lawtime 非依存で先行可**。

### 出口
assembler のグルーピングが正準 path ベースになり、誤 dispute/見逃しが L1 で測れて下がる。

> **接続軸との共有地盤**: L4 の article-level 正準 URI ＋ crosswalk は、法令間の委任チェーン・
> 参照グラフ（[`DD-LAWREF-001`](dd/DD-LAWREF-001_delegation_crossref_v0.1_notes.md) の接続軸）を
> 張るための前提でもある。「e-Gov は政令・省令の**テキストは持つが接続が無い**」という実務家の
> 問題提起（同ノート §1 で一次情報により精密化）に応えるには、まず L4 の同定地盤が要る。

---

## 6. L5–L7 — 局所改善（ゴールドセット完成後）🔵

- **L5 項・号粒度**: lawdelta/assembler を `art:X:para:n:item:m` まで分解。どの規定が変わったかの分解能↑。
- **L6 stance 射影の精緻化**: 現状「粗い二項対立」で「新設だが旧法理は継続」等が過剰 dispute に出る
  （安全側の over-surface）。L1 で誤 dispute 率を測りながら、両立ケースを dispute から外す。
- **L7 cue 拡充 → ML/LLM recall 層**: ルール先行（LEXA 実証: 手作りパターン > ML 基線）。
  recall を上げる ML/LLM はゴールドセット（L1）と実データ（L3）が揃ってから、**ルールの上に**載せる。
  載せる前後で P/R を必ず比較（precision を割らないことを gate 化）。

---

## 7. 依存と順序

```
L2(CI床) ─┐
          ├─► （今すぐ・並行）
L1(物差し)─┘        │
                    ├─► L3(実素材) ─► L1にラベル充填 ─► L5/L6/L7(較正・拡充)
                    └─► L4(同定地盤, lawtime apply 後に接続)
```

- **第一手**: L1 ＋ L2 を同時（外部依存ゼロ・今すぐ実装可能）。
- L3 は権限/調達の段取りを並行で起こす。
- L4 は正規化器/crosswalk を先行実装し、lawtime apply 後に view 接続。
- L5/L6/L7 は L1 のゴールドセットが回り始めてから（数字で採否できる状態で）着手。

## 8. 第一手の具体（すぐ着手分）

1. `.github/workflows/ci.yml` に producer 5テスト＋評価ハーネス step を追加（L2-1, L2-3）。
2. `tests/test_producer_invariants.py` 新規（L2-2: db_writes=0 / candidate 固定 /
   claim_support 非産出 / 断定フレーズ無し / 実質フィールド非混入）。
3. `scripts/eval/`（L1: gold JSONL × producer 出力 → pattern_id 単位 P/R、空ラベルでも緑）。
4. `tests/gold/` の様式定義＋ demo fixture を仮ゴールドとして配線（実ラベルは L3 と同期充填）。

> 本書は精度レバーの**順序合意**のための計画。実装は合意後、第一手（§8）から着手する。
