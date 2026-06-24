# DD-TOCADOPT-001 — 統一TOC採用ルール (Unified TOC Adoption Rule) v0.1 REQUEST

- 日付: 2026-06-15
- status: REQUEST (GPT 再監査 → owner ratify 待ち。design-only / 本番未反映)
- 起票理由: TOC に関する設計が **2 レーン・2 ポリシーに分裂**しており、同じ本に対して
  採用源が割れうる。源どうしの優劣ではなく **「本・ノード単位で最良の中身を合成して採用する」**
  という単一の採用ルールを明示し、TOC の議論を一本化する。
- 親/関連: DD-TOCATTACH-001 v0.3 (accepted, 本流の着脱式TOC機構) / DDLEGALLIBCONCORD v0.3.1
  (legallib 接合・phase0=GO/apply=HOLD) / toc_merge_policy v2 (commit 64cec12)。
- supersede 対象: `data/toc_merge_policy_legallib.json`(Fork1) と
  `app/data/toc_merge_policy.json`(v2) を **本DD合意後に 1 本へ統合**する。

---

## 0. 原則 (これが幹)

> **源どうしの勝ち負けを決めない。本ごと・ノードごとに「最も良い中身」を、出所を記録しながら
> 合成し、その良きものを採用する。源の優先順位ラダーは "同点決勝のタイブレーク" に格下げする。**

「良さ」の単位は **源ではなく本/ノード**。同一の本でも強みは源ごとに散る:
- 目次の深さ(粒度) … legallib / lionbolt の詳細TOCが強い
- ページ番号 … 源により有無が割れる
- 章執筆者 … ndl_partinfo が独自に持つ (809冊で唯一のTOC)
- 原本忠実度 … publisher の toc_pdf

したがって採用ルールは「どの源が偉いか」ではなく **「この本ではどの中身が最良か」** を解く。

---

## 1. 現状の分裂 (一本化の対象)

| 論点 | 本流: TOC-attach v2 | legallibjoin: Fork1 | 一本化方針 |
|---|---|---|---|
| ポリシーファイル | `app/data/toc_merge_policy.json` | `data/toc_merge_policy_legallib.json` | **1 本へ統合** |
| 源の母集団 | 12 源 (lionbolt/ndl_partinfo/zosho 含む) | 10 源 (lionbolt **欠落**) | **v2 の完全母集団を採用** |
| legallib vs toc_pdf | legallib > toc_pdf | **toc_pdf > legallib** (逆) | §4 でタイブレーク決定 (owner判断) |
| ndl 系 | `ndl_partinfo` (内容細目) | `ndl` (粗) | **ndl_partinfo を採用** |
| 粒度保護 | `granularity_guard`(最富源比20%) | なし | **採用** |
| 上書きゲート | (projection で基底選択) | `simple_only`(良い既存を壊さない) | **両方を Step2/3 へ吸収** |
| 版同定ゲート | (識別子前提) | **edition_identity (Phase0)** | **Step1 へ昇格・全源共通化** |

> 本DDは「v2 を幹に、legallibjoin の良い枝(simple_only・版同定・resolver突合)を接ぐ」。
> 50:50 ではなく、機構・母集団が成熟している v2 を土台にする。

---

## 2. 対象源 (統一母集団)

新3源 = **lionbolt(LION BOLT)** / **bengo4(弁コム)** / **legallib(legal-library)** に加え、
manual / ndl_partinfo / publisher / toc_pdf / openbd / books_or_jp / codex_ocr / zosho_bib_toc。

各源には `provenance_origin`(独立性判定用) と `page_basis`(print_page/pdf_page) を付与する
(Phase0 実測: legallib は両者併記・offset は本単位で 94.9% 単一 → pdf↔print は本単位 offset で機械変換可)。

---

## 3. 採用ルール本体 (5 ステップ)

各本(同一 manifestation クラスタ)に対し順に評価する。**全段 report-only で投影し、
production 反映は apply_guard 通過後のみ。**

### Step 1 — 同一性ゲート (混ぜてよい源だけに絞る)
同一の本と主張された源群から、**同一 edition/manifestation が確認できた源のみ**を合議対象にする。
- 判定 = `classify_edition_identity` 強化版 (Phase0 所見を反映):
  - **タイトルからの版番号抽出**を一次信号にする (`第7版`/`〔第4版〕`/`(第N版)`/`〈第N版〉`)。
    版番号が相違 → `suspected_different_manifestation` (別版・合議対象外)。
  - **核タイトル包含**で副題の有無を吸収 (片方が副題を含むだけなら同一)。
  - **年差±1 は許容**、版番号一致なら年差は重版扱い (誤検知防止)。
- Phase0 実測: 生の別版疑い 344件(16.5%)のうち **偽陽性 226 / 実質 118 / 確実な別版 26**。
  → このゲートを置かないと 226 件の同一本を誤って分離する。
- 未解決(同一性が確認できない)源は合議に入れず human_review。

### Step 2 — 基底選択 (一番リッチな中身を base に)
合議対象の中から本ごとに base TOC を選ぶ。**順位ではなく品質を一次基準**にする:
1. **粒度(深さ)** が最も豊富な源を base 候補に。
2. `granularity_guard`(最富源のノード数比 20% 未満の源で base を上書きしない)で
   **詳細TOC → 浅い章リストへの劣化を禁止**。
3. **ページ被覆率**が高い源を優先。
4. 上記が同点のときだけ §4 の優先ラダーでタイブレーク。
- legallibjoin の `simple_only` はここに吸収: 既存 base が "simple(浅い)" のときのみ
  詳細源で base を張り替え、良い既存 base は壊さない。

### Step 3 — ノード補完 (base に無い良さを足す)
base に欠けるノード/ページ/章執筆者を他源から **append_missing_only** で補う。
- ページ: `page_numbers_prefer = with_pages` (持っている源から充当、本単位 offset で print/pdf 整合)。
- 章執筆者: ndl_partinfo contents 型から付与。
- **補完した各ノードに provenance(出所源)を記録**。

### Step 4 — 保護と合議 (壊さない・割れたら止める)
- `protected_sources = {manual, ndl_partinfo, publisher, toc_pdf}` は自動上書き不可。
- ノード単位 `votes_by_provenance`: 独立 3 源以上が一致 → consensus 採用。
- 源が割れて consensus が立たない / PDF が ground truth 資格を満たさない → human_review
  (`authority_resolver`: pdf_primary は qualified+版解決+page_basis整合のときのみ)。

### Step 5 — 記録 (なぜこの中身かを追える)
sticky な toc_node_id (DD-TOCATTACH v0.3) を維持し、採用結果は 3 層分離
(snapshot 不変 / attachment 着脱 / canonical 投影) で投影する。本ルールは投影層の採用関数を定義する。

---

## 4. 統一優先ラダー (タイブレーク専用)

Step2-4 が同点のときだけ使う。v2 を基準に 1 本化:

```
manual > ndl_partinfo > publisher > toc_pdf > legallib > lionbolt
       > openbd > books_or_jp > bencom > codex_ocr > zosho_bib_toc > unknown
```

確認/解消した点:
- **lionbolt を明示追加** (Fork1 の欠落を解消)。
- **ndl → ndl_partinfo** に統一。
- **legallib vs toc_pdf**: 下記 OQ-1 の owner 判断を要する。上記たたき台は
  「publisher 自身の PDF 目次 (toc_pdf) は第三者抽出 (legallib) より原本忠実」として
  **toc_pdf > legallib** を採用 (= Fork1 側に寄せた)。**v2 は逆順**だったため要裁定。
  ※ 本DDの新原則では Step2 の粒度優先が先に効くので、この順序は「両者が同粒度のとき」
    にしか発火せず、実務影響は限定的 (Phase0 で legallib 詳細TOC は toc_pdf より深いことが多い)。

---

## 5. legallibjoin の吸収マップ

| legallibjoin 資産 | 統一ルールでの居場所 |
|---|---|
| `edition_identity` (版同定 4 ラベル) | Step1 同一性ゲート (全源共通化・版番号抽出を追加) |
| Phase0 `phase0_inventory.py` 所見 | Step1 の閾値較正根拠 (装飾差/副題/年±1 除外) |
| `resolver_decisions.jsonl` (book_id→ISBN) | Step1 のクラスタ形成入力。auto_accept 偽陽性12件・defer_new取りこぼし58件は human_review へ差し戻し |
| `simple_only` overwrite gate | Step2 の base 張替え条件 |
| `authority_resolver` (consensus/pdf_primary) | Step4 合議 |
| Fork1 policy ファイル | 本DD合意後に統合 policy へ畳んで廃止 |

---

## 6. 適用範囲 / HOLD

- 本DDは **採用ルールの定義のみ**。canonical 投影・production apply・policy ファイル上書きは
  **HOLD 継続** (DD-TOCATTACH v0.3 と DDLEGALLIBCONCORD の HOLD を踏襲)。
- 本DD合意後の実装順: ①統合 policy ファイル生成(2本→1本、検証=既存 projection dry-run の
  完全再現) → ②`classify_edition_identity` 強化(版番号抽出/核包含/年トレランス) →
  ③統一採用関数で全クラスタ report-only 投影 → ④owner ratify → 初めて apply 検討。

---

## 7. Open Questions (owner 判断事項)

- **OQ-1**: タイブレーク順 `toc_pdf` vs `legallib` はどちらを上にするか
  (たたき台=toc_pdf>legallib。原則上は粒度優先で影響限定だが明示が必要)。
- **OQ-2**: `granularity_guard` 閾値 20% を全源共通でよいか、源ごとに変えるか。
- **OQ-3**: bengo4(弁コム) と legallib は重複が多い (B4↔LLB 2,052組≒弁コムの46%)。
  同一本で両者がある場合の base 既定を粒度優先のみで決めてよいか。
- **OQ-4**: Fork1 policy を即廃止してよいか、移行期間を置くか。

---

## 8. 検収基準 (合意後の実装が満たすべきこと)

1. 統合 policy 1 本で、既存 `tocattach_projection_dryrun`(631クラスタ/116,727ノード) を
   **完全再現** (投影 sha 入力順非依存一致・基底源分布不変)。
2. Step1 が Phase0 の **確実な別版 26 件を合議から除外**し、偽陽性 226 件は同一として通す。
3. 詳細TOC → 浅い章リストの **劣化 0** (granularity_guard 実効)。
4. 全採用ノードに provenance が付き、source が割れたノードは human_review に落ちる。
5. canonical / 各源スナップショットへの **書き込み 0** (report-only)。

---

> 本DDの狙いは「legallib vs lionbolt vs 弁コム のどれが優秀か」という問いを **消す**こと。
> 問いを「この本ではどの中身が最良で、それをどう合成して採用するか」に置き換え、
> TOC の設計議論を 1 つの採用ルールへ収束させる。
