# DD-CASELINK-001 — 評釈→判例 リンク抽出 / role typing（本文から判例を取り出し正典 edge に載せる）**draft v0.2**

- 起票: 2026-06-24 JST ／ 番頭: Claude Code (remote)
- 改訂: 2026-06-24 v0.2 — **v0.1 の独自役割語彙（annotates/cites_* 造語）を撤回し、正典 `35_link_layer` の `edge_type`/`assertion_mode` に全面 crosswalk**（自己ドリフトの是正）
- lifecycle: **draft / candidate**（独立監査 未了 → DDCASE ゲート）
- domain: CASE（判例精度・意味層厚み付け／リンクレイヤへの供給）
- parent: `35_link_layer`(alo_edges 正典・edge_type 10値/assertion_mode 4値) / `DD-CASE-001`(関係は edge・merge禁止) / `DD-CASEID-001`(fingerprints/external_ids)
- related: `33_magazine_layer`(OPAC判評→evaluates+applies の前例) / `32_literature_layer`(文献標題推定マッチ→evaluates strength=implicit) / `DD-CASECORROB-001`(L2 annotation 補強) / `DD-CASEBIND-001`(②ガード) / `DD-CASECITE-001`(引用検証ゲート) / `DD-CASEID-002`(符号正規化)
- 実装: `scripts/case_link_map.py`(mention→alo_edges 写像・決定的) / `scripts/test_case_link_map.py`(fixture) / `case_vocab.py`(link層語彙の正本ミラー) ／ 抽出器 `case_link_extract.py` は別途(citation-span 抽出は分離)

> **目的**: 雑誌・文献の**本文**から該当判例を取り出し、評釈と判例を丁寧に繋いで**意味層を厚くする**。難所は「1記事:N判例（評釈と判例が 1:1 でない）」。これを**フラットなN本の同格エッジにせず、正典 `alo_edges` の型付きエッジ（evaluates/review_chain/compares …）として載せる**。**新語彙を作らない・merge しない・自動エッジは構造由来(vendor_explicit)のみ・本文推定は strength=implicit で review-first・llm_inferred 直書き禁止（PoC DB制約）。設計のみ・read-only。**

---

## 0. スコープと原則
- **正典は `35_link_layer`**。本 DD は alo_edges への **candidate 供給**であり、新しい edge_type も新しい confidence 体系も作らない（`assertion_mode`/`weight`/`strength`/`alo_edge_evidence` を使う）。
- reality_check 厳守: **「LIC data_no を canonical case にしてはならない」「OPAC accepted edge 0」**。canonical 昇格・auto-merge はしない（CASE-001: 関係は edge）。
- **抽出の価値はエッジ数でなく役割（edge_type）と確信度（assertion_mode）**。1記事に判例が K 個出ても、K 本の同格エッジにしたら意味層はむしろ薄くなる。
- **精度優先(split-first)**: 誤った `evaluates`（＝この評釈はX判例の評価）は欠落より有害。構造由来のみ自動、本文推定は review。

## 1. 決定① — 正典 edge_type への crosswalk（**造語を撤回**）

`35_link_layer §2.2` が commentary→case 語彙を既に定義済み。本文の各 mention を**正典 edge_type に割り当てる**：

| 記事中の役割 | 正典 edge_type（既存） | stance（新 qualifier・§7決定） | 典型シグナル | 既定 assertion_mode |
|---|---|---|---|---|
| **評釈対象（主）** | `evaluates`（評価）／正式評釈は `review_chain` | —（評価そのもの） | masthead 表示判例 / 「本判決」「本件」共参照 | **vendor_explicit**（構造由来＝自動可） |
| 同旨・参照（従） | `compares`（比較） | `supporting` | 「同旨、…」「参照、…」 | vendor_implicit（strength=implicit）→ review |
| 対比・反対（従） | `compares`（比較） | `contrasting` | 「これに対し」「反対、…」 | vendor_implicit（strength=implicit）→ review |
| 背景・傍論言及（従） | `compares`／非エッジ化 | `neutral` | 制度説明で一度きり | vendor_implicit → review（弱 weight） |

- **stance 決定（owner 確定 2026-06-24）**: 同旨/反対は **新 edge_type を増やさず `alo_edges` に `stance` qualifier 列（`supporting`/`contrasting`/`neutral`）を足して保存**。edge_type は `compares` 据え置き、CHECK 制約は最小変更。`35_link_layer §11`「OPPOSES（通説 vs 反対説）」開項目とも整合（commentary→case では edge_type 増設でなく stance で表現）。**正典への列追加は §7 の順序＝DDCASE 監査通過後**。
- `evaluates` の主は原則 **1**。masthead が複数判例を表示する併合・同種まとめ評釈のみ N を許容。
- **未知シグナルは非エッジ化**（fail-closed、review へ）。新 edge_type は CHECK 制約変更を伴うため**勝手に増やさない**。

## 2. 決定② — 確信度は `assertion_mode` で表現（独自 Tier を作らない）

v0.1 の「Tier A/C」は正典の `assertion_mode` に写す：

| 由来 | assertion_mode | strength | 扱い | v0.1 の呼称（廃止） |
|---|---|---|---|---|
| masthead / crosswalk（構造化済み） | `vendor_explicit` | — | **自動エッジ可** | Tier A |
| 本文採掘（部分引用・OCR 揺れ） | `vendor_implicit` | `implicit` | **review-first** | Tier C |
| LLM 推論 | `llm_inferred` | — | **PoC 禁止（DB制約）** | — |

- `vendor_implicit`/`strength=implicit` は `32_literature_layer §6`「文献標題推定マッチ→evaluates (strength=implicit)」と同じ扱い＝既存の安全レーン。
- **エッジには必ず `alo_edge_evidence`**（role=support/quote/source_field, ordinal）。本文 span を quote 根拠に、masthead を source_field 根拠に。`35_link_layer` Gate-5「根拠なし edge 禁止」を満たす。

## 3. 決定③ — 記事タイプで条件分け（主検出の前提）

| 記事タイプ | 主(評釈対象) | 既定の扱い |
|---|---|---|
| **評釈 / 判例研究** | あり（masthead 表示判例） | masthead→`evaluates`(vendor_explicit) / 本文→`compares`(vendor_implicit) |
| 判例紹介 / 解説 | 弱い〜あり | masthead あれば `evaluates`、無ければ全 `compares`(implicit) |
| 論文 / 論説 | **なし**（テーマ横断で多数引用） | 1:1 を作らない。N本 `compares`(implicit)。頻度突出は `central_case` ヒント止め |

- 論文の多数引用から無理に主を選ばない（誤 `evaluates` を量産しない）。

## 4. 決定④ — 主検出シグナルの優先順位（高精度→低精度）
1. **書誌メタの表示判例**（masthead = 裁判所/日付/事件番号/出典）→ 構造的キー一致 → `evaluates` を **vendor_explicit** で。
2. **位置**（masthead=主 / 本文=従）。
3. **共参照**（「本判決/本件/対象判決」＝主）。
4. **頻度**（主は反復 / 従は一度）。

(1) を最優先。(2)〜(4) は (1) を欠く/補強する従シグナル。

## 5. 決定⑤ — 抽出パイプライン（既存基盤への接続）

本文の判例文字列は**部分引用が常態**（事件番号なし・OCR 揺れ）：

```
記事 → (a)記事タイプ分類
     → (b)masthead 解析 → 対象判例【構造化・高精度】
     → (c)本文 citation-span 抽出 → 引用文字列リスト
     → (d)case_number_norm + 符号正規化(CASEID-002)
     → (e)bind guard で canonical case 解決:
            ・構造キー一致(masthead) → vendor_explicit エッジ
            ・部分一致(本文)         → vendor_implicit/strength=implicit → review（fuzzy_review_candidates）
     → (f)edge_type 割当（§1 crosswalk）＋ assertion_mode（§2）
     → (g)cite_gate で引用が実在・解決可能か検証 → 通過後にエッジ確定
     → (h)alo_edges + alo_edge_evidence へ candidate 投入（DD-CASECORROB が独立源一致で weight/confidence 補強）
```

- **自動確定は (e) vendor_explicit のみ**。本文由来は全て strength=implicit → review。先日実装した `fuzzy_review_candidates` がこの review レーンの実体。
- LLM は **候補提示まで**（assertion_mode を llm_inferred にしない＝DB制約遵守）。エッジ化は vendor_explicit/vendor_implicit/human のみ。

## 6. 正典整合（self-consistency・このDD固有の必須節）
- edge_type は `35_link_layer §2.2` の10値のみ使用（`evaluates`/`review_chain`/`compares`）。**新 edge_type を本 DD で増設しない**。
- assertion_mode は §2.3 の4値、`llm_inferred` は PoC 禁止（§2.3 DB制約）。
- 根拠は §3 `alo_edge_evidence`（Gate-5）。time は §2.4（valid_from/valid_to、commentary→case は時点必須でない edge_type なら NULL 可）。
- 1記事:N は §6「OPAC判評→evaluates+applies」と同型（前例あり）。逆向き 1判例:N評釈は歓迎＝多源 annotation corroboration（CORROB L2）。

## 7. 正典(Box設計資料)への反映 ← owner 指摘「設計資料の修正がいるんちゃうか」への回答
v0.2 で語彙を正典に合わせた結果、正典側の改修は **最小限**で済む。**反映順序（owner 確定 2026-06-24）＝本 DD が DDCASE 監査を通過してから、下記をまとめて正典へ適用**（監査前は Box 正典を編集しない＝設計正典の単一書き手を保つ）。queue:

1. **`35_link_layer §2.1/§2.2` に `stance` qualifier 列を追加**: `alo_edges.stance text NULL CHECK (stance IN ('supporting','contrasting','neutral'))`。`compares`（commentary→case）の同旨/反対を保存。edge_type は増やさない。§11「OPPOSES」開項目もこの stance で解決方針に更新。
2. **`35_link_layer §6 エッジ生成パターン`に1行追加**: 「雑誌/文献**本文**採掘 → `evaluates`／`compares`(+stance)（strength=implicit, DD-CASELINK-001）」。現状は「文献**標題**推定マッチ」のみで、**本文採掘**の生成元が未記載。
3. **`33_magazine_layer §4`（OPAC判評）と本 DD の境界注記**: OPAC由来(書誌レベル)と本文採掘(記事内 span)の二経路がともに `evaluates` を生むことを明示。

> 順序: **(a) 本 DD を正典語彙に整合（済・v0.2）→ (b) DDCASE 監査通過 → (c) 上記1〜3を正典へまとめて反映**。ドリフトを足さず、設計正典の単一書き手（owner）を保つ。

> つまり「設計資料の大改修」ではなく、**(a) 本 DD を正典語彙に合わせる（済・v0.2）→ (b) 正典に本文採掘経路の1行と同旨/反対の開項目を足す**、の順。ドリフトを足さずに意味層を厚くできる。

## 8. verification
- deterministic_self_verification = **fixture-level done**: `test_case_link_map.py` green（評釈1主＋同旨＋反対 / 正式評釈→review_chain / 論文→主なし＋central_case_hint / 未解決→edge無しreview / 未知→fail-closed）。確認項目: (i) **1記事:N が同格に潰れない**(edge_type/stance で分化)、(ii) masthead=vendor_explicit→auto・本文=vendor_implicit(strength=implicit)→review、(iii) emit 値域 ⊆ 正典(`COMMENTARY_TO_CASE_EDGE_TYPES ⊆ LINK_EDGE_TYPES`)、(iv) **llm_inferred 不発生**、(v) **merge 不発生**(route は auto/review/drop のみ)。
- consistency_gate = **恒久化済**: `test_case_consistency.py` に「`case_link_map` の edge_type/assertion_mode/stance ⊆ `case_vocab`(=35_link_layer ミラー)」を追加。**PASS**。本文採掘語彙のドリフトを CI で停止。
- corpus-level = **Mac CC**: D1-LIC 5,475 を本文採掘し、masthead 対象以外の本文 mention を vendor_implicit review として抽出。`evaluates` 精度を実 gold で測る。citation-span 抽出器(`case_link_extract.py`)実装はここで合流。
- independent_meaning_audit = 未了（DDCASE ゲート）。owner_approval = 未了。

### 8.1 写像決定表（`case_link_map.map_mention` の実装則）
| article_type | source | role | resolved | → edge_type | stance | assertion_mode | route |
|---|---|---|---|---|---|---|---|
| commentary/note | masthead | primary | deterministic | `evaluates`(正式評釈は`review_chain`) | — | vendor_explicit | **auto** |
| commentary/note | body | supporting | det/fuzzy | `compares` | supporting | vendor_implicit(implicit) | review |
| commentary/note | body | contrasting | det/fuzzy | `compares` | contrasting | vendor_implicit(implicit) | review |
| commentary/note | body | incidental | det/fuzzy | `compares`(弱weight) | neutral | vendor_implicit(implicit) | review |
| **article(論文)** | * | primary | * | `compares`(降格) + `central_case_hint` | neutral | (由来通り) | review |
| * | * | * | **None(未解決)** | — | — | — | review |
| **未知** article_type/source/role | — | — | — | — | — | — | **drop**(fail-closed) |

## 9. follow-up / open questions
- §7-2 の同旨/反対 を保存するか（edge_type 追加 vs `stance` qualifier vs 非保存）＝**owner 設計判断**。
- 記事タイプ分布（評釈/解説/論文）を LIC4誌で実測 → 条件分け閾値（owner 提案: 設計前に分布を見る選択肢）。
- citation-span 抽出器の実体（規則ベース＋符号正規化 vs 統計）。本 DD は edge へのマッピングを確定し、抽出器実装は分離。
- `central_case`（論文の中心判例）を正式 edge_type に昇格するか、ヒント止めか（§11 と連動）。
