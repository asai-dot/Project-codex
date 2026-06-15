# DD-EDIDENT-001 — Edition / Manifestation Identity Gate 強化 v0.1 REQUEST

- 日付: 2026-06-15
- domain: SDB (書籍 identity 層 / DD-BOOK 家系の同定ゲート)
- status: **REQUEST** (design-only / 本番・共有モジュール未反映。GPT 再監査 → owner ratify 待ち)
- 起票理由: legallibjoin v0.3.1 Phase 0 実測で、現行 `classify_edition_identity` の
  「title 文字列が1つでも違えば別版 / 年が1つでも違えば別版」判定が **過検知**することが
  数値で確定した（生の別版疑い 344件=16.5% のうち **偽陽性 226 / 実質 118 / 確実な別版 26**）。
  この過検知は **同一本 226 件を誤って分離**し、接合・TOC 合議の母集団を痩せさせる。
  本DDは、過検知を ≈0 に抑えつつ確実な別版 26 を取りこぼさない **強化仕様**を、Phase 0 で
  実証済みのロジックに接地して確定する。
- 親/関連:
  - **DDLEGALLIBCONCORD v0.3.1** (legallib 接合・phase0=GO/apply=HOLD) … apply ゲートの edition 判定がこれに従属。
  - **DD-TOCADOPT-001 v0.1** (統一TOC採用ルール / 2026-06-15 REQUEST) … §3 Step1 同一性ゲート・§5 吸収マップ・§6② 実装順が **本DDを前提として参照**している。本DDはその「classify_edition_identity 強化」の実体仕様。
  - **DD-BOOK-001** (書籍 canonical schema, canonical) … 同定対象の schema。
- 一次証拠: `handoff/legallibjoin_v0.3.1_phase0_20260615/`
  (`source_inventory.md` 所見1-4 / `edition_identity_sample.jsonl` 全 2,082 対 / `known_conflict_golden.md`)。
  入力固定 = `inputs_sha256.txt`。
- 変更対象コード（合意・ratify 後に実装。**本DDでは触らない**）:
  - `scripts/edition_identity.py` … `classify_edition_identity` を v2 へ。
  - `scripts/_toc_text.py` … 共有 `normalize_title` の `_STRIP_RE` に3文字追加（**共有モジュール = 影響範囲 §7 で要確認**）。
- 性質: **report-only / design-only**。canonical・legallib・final_toc いずれも書き換えない。apply は HOLD 継続。

---

## 0. 原則

> **「title が違う / 年が違う」は別版の証拠ではない。別版の一次信号は《タイトルから抽出した版番号の相違》であり、
> 表記の装飾差・副題の有無・出版年の±1 ゆれは同一 manifestation の範囲内とみなす。**

過検知は安全側に見えて有害である。同一本を別版へ割ると、(a) TOC 合議の母集団が痩せ（DD-TOCADOPT-001 Step1）、
(b) human_review が偽陽性で溢れて owner 時間を食い、(c) 接合 recall が落ちる。
「保守的＝正しい」ではなく「**版番号という決定的信号がある層だけを別版とする**」が正解。

---

## 1. 問題（Phase 0 実測）

評価対象 = canonical ISBN 一致 **2,082 対**（resolver auto_accept/human_review 由来）。
現行ロジックの判定:

| 現行 reason | 件数 | 実態 |
|---|---:|---|
| resolved_same_manifestation | 1,738 | 同一（正） |
| suspected_different — title divergence | 319 | **大半が偽陽性**（下表） |
| suspected_different — year divergence | 25 | うち 14 は ±1 ノイズ |

title divergence 319 の層別（`title_diff_kind` 実測）:

| 層 | 件数 | 別版か |
|---|---:|---|
| cosmetic（全半角・`〔〕〈〉`括弧・読点差のみ） | 123 | ✗ 同一 |
| subtitle_difference（片方が副題を含む/欠く） | 87 | ✗ 同一本 |
| edition_marker_asymmetry（片方のみ版表記） | 53 | △ 要レビュー |
| edition_number_conflict（第7版 vs 第4版） | 26 | ✓ **真の別版** |
| genuine_title_diff（核タイトル相違） | 30 | △ 要レビュー |

**偽陽性（装飾/副題/年差±1）= 226。実質要レビュー = 118（5.7%）。うち確実な別版 = 26。**

---

## 2. 現状ロジック（`scripts/edition_identity.py` 抜粋）

```python
# 2) title が割れている → 別物の疑い。
if len(titles) > 1:
    return SUSPECTED_DIFFERENT, "title divergence"
# 4) 刊行年が割れている → 別版の疑い。
if len(years) > 1:
    return SUSPECTED_DIFFERENT, "year divergence"
```

`titles` は `normalize_title`（NFKC＋記号除去）後の集合。だが現行 `normalize_title` の `_STRIP_RE` は
`〔〕` `〈〉` `、`(読点) を落とさないため、`〔第4版〕` と `(第4版)` 等が別文字列となり cosmetic 123 件が割れる。
また「年が1つでも違えば別版」は出版年の表記ゆれ（print年/刊年/カタログ年）を別版と誤る。

---

## 3. 強化仕様（Phase 0 で実証済み・`phase0_inventory.py` のロジックを正式モジュールへ昇格）

> 下記 §3.1〜§3.4 は Phase 0 の診断器 `phase0_inventory.py`（`edition_signature` /
> `_core_title` / `title_diff_kind` / `is_real_suspect`）として **実 2,082 対で動作実証済み**。
> 本DDはそれを診断専用から `edition_identity.py` の本番判定へ移すことを定義する。

### 3.1 共有 `normalize_title` の穴埋め（cosmetic 123 件を解消）

`scripts/_toc_text.py` の `_STRIP_RE` に **`〔` `〕` `〈` `〉` `、`** を追加する。

```python
# before
_STRIP_RE = re.compile(r"[\s　・･:：,_\-\(\)\[\]【】「」『』“”\"'./&＆ー―−‐‑‒–—]+")
# after（〔〕〈〉、を追加）
_STRIP_RE = re.compile(r"[\s　・･:：,，、_\-\(\)\[\]【】「」『』〔〕〈〉（）“”\"'./&＆ー―−‐‑‒–—]+")
```

- 効果: `〔第4版〕`↔`(第4版)`、`A、B`↔`AB` 等の cosmetic 差が同一化。
- ⚠ **共有モジュール**（接合・突合・トリアージで使用）。§7 の後方互換チェックを満たすこと。

### 3.2 版番号抽出 `edition_signature(title) -> str`（別版の一次信号）

NFKC 後のタイトルから版番号を抽出して正規化シグネチャ（`v7` 等 / 版表記なしは `''`）を返す。

```python
_ED_NUM_RE   = re.compile(r"[第\(\[〔〈【]?\s*(\d+|[〇一二三四五六七八九十]+)\s*版")
_ED_LABEL_RE = re.compile(r"(改訂|新訂|全訂|増補|補訂|新版|初版)")
# 例: "第7版"->"v7"  "〔第4版〕"->"v4"  "(第3版)"->"v3"  "初版"->"v1"  "改訂版"->"rev"  なし->""
```

漢数字は `_kanji_to_int`（十進対応: 十N / N十 / N十M）で数値化。

### 3.3 核タイトル包含（副題の有無を吸収）

```python
def _core_title(t):  # 版表記と記号を除いた核（副題込み・小文字）
    s = NFKC(t).lower(); s = _ED_NUM_RE.sub("", s); s = _ED_LABEL_RE.sub("", s)
    return _CORE_STRIP.sub("", s)
```

片方の核が他方の核を**包含**するなら副題差にすぎず同一本（`subtitle_difference`）。

### 3.4 `classify_edition_identity` v2 の判定順序（title/year 段を差し替え）

現行 §2 の素朴な `len(titles)>1 → 別版` / `len(years)>1 → 別版` を、次の層別へ置換する
（ISBN 複数・edition/volume ラベル相違・page_count 大差の段は現行どおり残す）:

1. **版番号衝突**: `edition_signature(a) ≠ edition_signature(b)` で両方非空 → `suspected_different`（reason=`edition_number_conflict`）= **確実な別版**。
2. **核一致**: 核タイトルが一致 →
   - 版マーカ非対称（片方のみ版表記）→ `suspected_different`（reason=`edition_marker_asymmetry`, 要レビュー）。
   - それ以外（装飾差のみ）→ `resolved_same`。
3. **核包含**: 片方の核が他方を包含 → `subtitle_difference` → `resolved_same`。
4. **核相違**: 上記いずれでもない → `suspected_different`（reason=`genuine_title_diff`, 要レビュー）。
5. **年差トレランス**: title が同一化された後、年だけ違う場合は
   - 版番号一致 → 重版とみなし `resolved_same`。
   - 版番号不明かつ **年差 ≤ 1** → `resolved_same`（出版年表記ゆれ）。
   - 年差 ≥ 2 → `suspected_different`（reason=`year divergence`, 要レビュー）。

> 4ラベル（`resolved_same` / `suspected_different` / `insufficient` / `manual`）と
> `APPLY_OK_STATUS = {resolved_same, manual}` は**不変**（GPT Q2 準拠）。本DDは
> `suspected_different` の発火条件を精緻化するだけで、apply 許可集合は広げない。

---

## 4. 周辺: resolver 差し戻し（Phase 0 所見4・所見3／別ワークでも可）

edition gate 本体とは独立だが、同じ Phase 0 証拠から確定した resolver 入力の修正:

- **defer_new の取りこぼし 58 件**: bucket=defer_new（canonical 不在として create 予定）だが
  canonical に同一 ISBN が存在 → `human_review` へ差し戻す。
- **auto_accept 偽陽性 12 件**: 装飾/副題/年±1 を除いた実質要レビュー → apply 時に edition gate が物理拒否。

> これは `resolver_decisions` 側の bucket 再判定であり、edition_identity.py の変更ではない。
> owner 判断で本DDに含めても、resolver の micro-DD として切り出してもよい（§8 OQ-3）。

---

## 5. ダウンストリーム接続（本DDが供給する先）

| 消費側 | 使い方 |
|---|---|
| DD-TOCADOPT-001 §3 Step1（同一性ゲート） | 合議に入れる源を「同一 manifestation 確認済み」に絞る判定に v2 を使用。全源共通化。 |
| DD-TOCADOPT-001 §6② 実装順 | 「②classify_edition_identity 強化」の実体が本DD。 |
| DDLEGALLIBCONCORD apply gate | `is_apply_allowed_identity` の入力。`suspected_different`（版衝突26＋実質要レビュー）を物理拒否。 |
| concordance_pipeline.py（次段 evidence ④⑤） | 強化後の判定で all_nodes_accounted_for 照合 / apply_guard 拒否ログを生成。 |

---

## 6. 検収基準（実装が満たすべき・**測定可能**）

1. `edition_identity_sample.jsonl` の同一入力 2,082 対に v2 を適用し:
   - **確実な別版 `edition_number_conflict` 26 件**を `suspected_different` のまま保持（取りこぼし 0）。
   - **偽陽性 226 件（cosmetic 123 + subtitle 87 + year±1 14 + …）を `resolved_same` へ回収**（過検知 ≈0）。
   - 実質要レビュー 118 → `suspected_different`（edition_marker_asymmetry 53 / genuine_title_diff 30 / 版衝突 26 / 年差≧2 等）。
2. 4ラベル集合・`APPLY_OK_STATUS` 不変。`is_apply_allowed_identity` の真偽が広がっていない。
3. `normalize_title` 変更後、**既存の projection / 突合 dry-run が回帰しない**（§7）。
4. 既存テスト（phase0 / v031_authority / v031_gates / concordance / concordance_pipeline 計 33 件）PASS 維持＋
   v2 判定を凍結する新テスト（版衝突・cosmetic・subtitle・年±1 の各代表例）追加。
5. canonical / 各源スナップショットへの**書き込み 0**（report-only）。

---

## 7. 影響範囲 / 後方互換（共有モジュール変更の唯一の risk）

`normalize_title` は接合・突合・トリアージ・TOC title_set/jaccard が共有する。`_STRIP_RE` 拡張は
「より多くの記号を落とす＝より多くが一致する」方向のみで、**新たに不一致を生むことはない**が、
title 集合の Jaccard が上振れする箇所がありうる。実装時は:

- 変更前後で既存 projection dry-run（DD-TOCADOPT-001 §8.1 の 631クラスタ/116,727ノード）の
  **基底源分布が不変**であることを確認してからマージ。
- 影響が出る場合は edition_identity 専用の `normalize_title_strict` を切り出し、共有モジュールは据え置く案を OQ-2 とする。

---

## 8. Open Questions（owner 判断）

- **OQ-1**: `edition_marker_asymmetry`（片方のみ版表記、53件）の既定。`suspected_different`（要レビュー）か、
  核一致なら `resolved_same` に倒すか。たたき台 = **要レビュー**（版が片方にしか無いのは別刷りの可能性）。
- **OQ-2**: `_STRIP_RE` 拡張を**共有モジュールに入れる**か、edition_identity 専用の strict 版に分けるか（§7）。
  たたき台 = 共有に入れる（cosmetic は接合全体でも同一化が望ましい）。要 dry-run 確認。
- **OQ-3**: §4 の resolver 差し戻し（58＋12）を本DDに含めるか、resolver micro-DD に切るか。
- **OQ-4**: 年差トレランスは ±1 でよいか（判例集の巻号前後年・重版年で実証）。±2 まで許すと別版を拾う恐れ。
  たたき台 = **±1**。
- **OQ-5**: `改訂/新版/増補`系（`_ED_LABEL_RE`）の扱い。版番号なしで `rev` シグネチャ同士は同一視するか別版扱いか。
  たたき台 = `rev` 同士は核一致なら同一、`v1`(初版) と `rev` は版マーカ非対称として要レビュー。

---

## 9. HOLD / 実装順（合意後）

1. owner ratify（本DD）＋ GPT 再監査（意味監査は別 family）。
2. `_toc_text.py` `_STRIP_RE` 拡張 → §7 後方互換 dry-run → 既存 projection 再現確認。
3. `edition_identity.py` を v2 へ（§3.2-3.4）＋新テスト。
4. §6 の 2,082 対回帰で「別版26保持・偽陽性226回収」を数値確認。
5. （resolver 差し戻し採用時）defer_new 58 / auto_accept 12 を human_review へ再判定。
6. これらを入力に `concordance_pipeline.py` で evidence ④⑤（all_nodes_accounted_for / apply_guard 拒否ログ）を
   golden 10冊込みで生成 → owner ratify → **初めて apply 検討**（apply は本DD完了後も HOLD のまま別ゲート）。

---

> 本DDは「過検知を安全と取り違えない」ための一点突破。版番号という決定的信号を一次に据えることで、
> 同一本 226 件の誤分離を消し、確実な別版 26 件だけを止める。Phase 0 で既に動いたロジックの昇格であり、
> 新規発明ではない（L2: 動かしてから設計を確定した）。
