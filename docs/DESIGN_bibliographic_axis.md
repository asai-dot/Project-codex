# 書誌軸 設計メモ — NDL錨 × bencom簡易TOC（語彙軸の型を移植）

> status: design (考えるための叩き台) / owner: 浅井 / drafted: 2026-06-03
> 前提: 既存ALO設計の**上に立つ**。再発見・再実装しない。
> 参照（Box docs/alo）: 32_literature_layer / DD-BOOK-001 accepted v1.0 / cc_handoff_ndl_canonical_v2 /
> DD-CINII-001 / 05_data_inventory・40_data_inventory / 30_law_layer・34_vocabulary_layer・35_link_layer。

## 0. 狙い
語彙軸で実証できた型——**権威錨 ＋ 多源衛星 ＋ 綺麗なキーでjoin ＋ suspect/canonical段階**——を
書誌軸にそのまま移す。書誌軸は語彙軸より既に作り込みが進んでいる（NDL正本enrich済、TOC構造化済、
schema accepted）ので、本メモの貢献は**新設計でなく「既存資産を語彙軸と同じ流儀で噛み合わせる」道筋**。

## 1. 語彙軸 → 書誌軸の写像（中核）
| 語彙軸（実証済） | 書誌軸（本設計） | 既存資産/仕様 |
|---|---|---|
| 権威錨＝e-Gov法定定義(authority_rank=100) | 権威錨＝**NDL書誌正本**（title/yomi/pages/NDLC/NDC10/bib_id…） | cc_handoff_ndl_canonical_v2（5,401 ISBN parse済）、DD-BOOK-001 |
| 綺麗なキー＝見出し語 | 綺麗なキー＝**ISBN**（無ければ NDL bib_id / jpno） | work_identifiers（ISBN/ISSN/DOI） |
| URI＝`egov:{law}:art:{n}` | URI＝**`alo:book:isbn:{ISBN}:toc:{seq}`**（既に bencom TOC が採用） | 32_literature §1.3, bencom toc json 実物で確認 |
| 衛星＝有斐閣/学陽/JLT gloss | 衛星＝**bencom簡易TOC・D1-Law(分類/事項索引)・OpenBD・奥付OCR** | toc/(21,600 file), D1-Law文献編449,677, colophon_extracted |
| 読みconsensus(多源多数決) | **フィールドconsensus**（title/著者読み/頁/出版者/日付 を多源で突合） | field_provenance（ndl@/openbd@/manual 既設計） |
| 怪しい箇所＝読み化け | 怪しい箇所＝**フィールド不一致**（NDL頁 vs 奥付OCR頁、title異表記、版差） | 同上 |
| 用語カード（Hub最終形） | **book card**（work node＝NDL錨＋TOC木＋著者＋識別子＋provenance＋suspect台帳） | alo_works/alo_toc/alo_persons |
| scheme別 alo_terms→alo_hubs | **alo_works＋work_identifiers＋fingerprints(entity_type='work')** | 32_literature §2 |

## 2. 既にあるもの / 本当の残作業（measure-then-build）
**ある**: NDL正本enrich（books.json 6,537、per-field provenance）、bencom簡易TOC（`alo:book:isbn:` URIで構造化、
~1万冊規模）、D1-Law文献編449,677、CiNii著者63万件（名寄せ待ち）、巻末索引（人手EL=confidence1.0）、
DD-BOOK-001 schema、TOC→chunk設計（content_function 12分類・locator/explainer原則）。
**残**: ①多源フィールドの**突合と不一致の炙り出し**（＝書誌版の「読み訂正」鉱脈）、②TOC木の**chunk/概念タグ付け**、
③**書誌↔語彙の接合**（巻末索引・事項索引→alo_terms→§8）、④D1-Law 449,677 と 蔵書/NDL の名寄せ。

## 3. ゴールデン書誌レコード（錨）
ISBNを綺麗なキーに、各フィールドを**最権威ソースで確定＋出所を field_provenance に刻む**（既設計を踏襲）。
権威順（暫定・要確認）: **NDL > OpenBD > D1-Law文献編 > 奥付OCR > 手入力**（手入力の棚位置/自炊状態は別orthogonal）。
- 出力1行＝1 work：`{isbn, ndl_bib_id, title, title_yomi, creators[], creators_yomi[], publisher, date, pages,
  ndlc, ndc10, price, has_index, identifiers[], field_provenance{field:source@date}, suspect_fields[]}`。
- 「派生物を正本扱いしない」: 奥付OCRやSheet viewは衛星。SoT=books.json（DD-BOOK-001 §M-2-4）。

## 4. 多源トライアンギュレーション ＝ 書誌版「怪しい箇所/クレンジング」
語彙軸の最高歩留まりは**読み**だった。書誌軸の同型の鉱脈は以下。**生は非改変・訂正は提案層(auto_apply=false)**。
| 対象 | 多源 | 不一致の意味 | 裁定 |
|---|---|---|---|
| **著者読み** creators_yomi | NDL / 奥付 | 読み化け or 別人 | 読みは語彙軸の `reading_adjudicate` 流儀（NFKC＋カナ→かな＋多数決）が**そのまま再利用可** |
| **書名** title | NDL / OpenBD / 手入力 / 奥付OCR | 異表記・副題有無・OCR誤り | 正規化（NFKC・全角半角）後に差分。版/副題差は「誤りでない」（学陽≒有斐閣の教訓＝版差を誤判定しない） |
| **頁** pages | NDL / 奥付OCR / OpenBD | OCR誤り or 版差 | 物理facts突合（語彙軸の条見出し突合と同型＝特定factで鋭く当てる） |
| **出版者/日付** | NDL / D1-Law / OpenBD | 表記ゆれ・改版 | 表記ゆれは正規化、改版は版として保持（temporal） |
| **ISBN↔書誌** | 蔵書 / D1-Law / NDL | 同定ミス | fingerprints(entity_type='work')で同一性解決 |
方法知見の移植: **精密(ISBN厳密一致) と 再現(書名+著者ファジー) の併用**／**権威は万能でない**（NDL欠落12件の実例）。

## 5. bencom 簡易TOC ＝ 衛星enrichment（最重要・綺麗）
実物確認: `toc/isbn_{ISBN}.json` は配列、各ノード `{l, p, t, toc_node_id:"alo:book:isbn:{ISBN}:toc:{NNN}",
depth, parent_toc_node_id, toc_path_id:"c03-s02-p01", page_start, toc_source:"bencom", toc_status:"simple"}`。
- **既にALO URI・親子・頁付き** ＝ 32_literature の文献JSON.toc / alo_toc にほぼそのまま載る。
- 価値: ①**chunk locator**（葉TOC=1チャンク、page_startで奥付/本文に解決）、②**自己完結のためのTOCパスprepend**素材、
  ③「書式」「Column」「Q&A」等の content_function ヒント（t の接頭辞）、④**概念タグの貼り先**（§8）。
- 規模: `toc/`(370441454337) に isbn_*/title_* で~1万冊。`title_*` はISBN無し本（NDL bib_id/内部idで解決要）。

## 6. golden book card（用語カードの対・最終形）
語彙軸 `golden_term_cards_high.jsonl` の書誌版。1冊=1ノード:
```
【書名】 ISBN / NDL bib_id        ← 綺麗なキー
◆[錨] NDL書誌正本 (authority)  title_yomi・著者・出版者・日付・頁・NDLC・NDC10  field_provenance付き
・著者: {name, name_yomi(多源一致?), CiNii CRID}            ← alo_persons（名寄せ）
・目次: bencom簡易TOC木（depth/page/locator）                ← chunk化の単位
・分類/事項索引: D1-Law categories[], subject_index[]        ← §8で alo_terms へ
・suspect: [{field:pages, ndl:312, colophon:308, status:provisional}]  ← §4の炙り出し
```
- 錨単独ノード（TOC無し）も可＝語彙軸の「錨単独2,288」と同じく、書誌のみでも有効ノード。
- リッチノード＝NDL錨＋TOC＋著者CRID＋事項索引が揃い、相互検証が回る（NDL頁↔奥付頁 等）。

## 7. 段階・guard（既存原則の踏襲）
- provisional→canonical: フィールドが多源一致 or NDL確定で canonical、不一致は suspect_fields に残し provisional。
- `hub_status` / `__unresolved__` / fingerprints は語彙軸と同じ枠。
- **guard `literature_not_in_evidence`**（32_literature §1.2）厳守＝書誌チャンクは locator/explainer であり
  CaseBundle の evidence に直接入れない（「教科書がそう言ってる」で走らせない）。書誌軸は supporting_analysis 供給。

## 8. ★二軸の接合点 ＝ 巻末索引・事項索引（書誌↔語彙）— ここが本丸の payoff
語彙軸（e-Gov錨5,874・カード3,063）と書誌軸が**噛み合う場所**:
- **巻末索引**（32_literature §7）＝著者が人手で行ったEL（confidence=1.0）。索引語→`alo_term_labels`正規化一致→
  `alo_entity_links`。一致無は `__unresolved__` に scheme_only term 自動生成→doc_support_count≥50 で hub 昇格。
- **事項索引/分類**（D1-Law subject_index）→ `alo_edges`（語彙レイヤTier2）。
- これで「**この法律概念（語彙錨）を解説している本のこの章（書誌TOC locator）**」が programmatic に引ける。
  ＝浅井さん原案「ゴールデンデータ同士をぶっ刺す」の実体。語彙軸の法定定義↔書誌のTOC/索引が相互に錨を増やす。
- 副産物: 複数本の索引共起で**未登録term**が浮上（語彙軸の錨追補）、比較法書は cross-scheme リンクを自然生成
  （32_literature §11）。

## 9. スキーマ対応（既存）
| カード要素 | 既存テーブル |
|---|---|
| 錨（NDL書誌） | `alo_works`（Canonical）＋ `field_provenance` |
| 識別子 ISBN/ISSN/DOI | `work_identifiers` ＋ `fingerprints(entity_type='work')` |
| 著者（CRID名寄せ） | `alo_persons`（crid）＋ DD-CINII-001 突合 |
| 目次木（bencom） | 文献JSON.toc / `alo_toc_meta` / `alo_toc_chunk_map` |
| 事項索引→概念 | `alo_edges`（subject_index, Tier2）／巻末索引→`alo_entity_links` |
| 章チャンク | `alo_chunk`(+meta/generation/override) ＝ chunkメタ仕様v0.2.1 |
| カード自体 | work node（fingerprintsで横断同一性） |

## 10. 設計判断・要確認（浅井判断）
1. **フィールド権威順**: NDL>OpenBD>D1-Law>奥付OCR>手入力 で妥当か（語彙軸の authority_rank に相当）。
2. **スコープ第一弾**: まず**蔵書6,537冊**（NDL錨＋bencom TOC が既に濃い）で book card を実証 → 後で D1-Law 449,677 へ拡張、でよいか。
3. **版差の扱い**: title/頁の不一致を「OCR誤り」と「版差」に分ける基準（語彙軸＝版差を誤判定しない教訓）。
4. **書誌↔語彙の接続を今やるか**: §8（巻末索引→alo_terms）は二軸が揃って初めて価値。語彙軸が一段落した今が好機か。
5. **DB投入の境界**: books.json は本番稼働中。Supabase化/書き戻しは破壊的になり得る（cc_handoff の backup必須・§M-1順序固定を厳守）。設計と分離して慎重に。

## 11. 次の小さな一歩（measure first・非破壊）
語彙軸と同じく「**まず測る**」: 蔵書ISBNについて **NDL正本 × 奥付OCR × OpenBD × 手入力** のフィールド突合を1バッチ走らせ、
**不一致フィールドの分布**（title/著者読み/頁/出版者/日付）を出す。これで「書誌版の太い鉱脈」がどれか（語彙軸の"読み"に当たるもの）を
データで決めてから build する。読みは語彙軸の `reading_adjudicate.py` がそのまま使える見込み。
（このバッチはクラウドからでも、NDL parsed と bencom と books.json を Box から取れば回せる。実装はGPTレビュー後に。）
