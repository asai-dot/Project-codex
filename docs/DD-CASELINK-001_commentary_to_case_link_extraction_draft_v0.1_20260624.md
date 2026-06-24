# DD-CASELINK-001 — 評釈→判例 リンク抽出 / role typing（本文から (判例, 役割) を取り出す）**draft v0.1**

- 起票: 2026-06-24 JST ／ 番頭: Claude Code (remote)
- lifecycle: **draft / candidate**（独立監査 未了 → DDCASE ゲート）
- domain: CASE（判例精度・意味層厚み付け／②③④横断）
- parent: `DD-CASE-001`(accepted v1.0, merge禁止/関係は edge) / `DD-CASEID-001`(accepted v1.0, fingerprints/external_ids)
- related: `DD-CASECORROB-001`(L2 annotation の供給元になる) / `DD-CASEBIND-001`(②ガード A/B/C/prov) / `DD-CASECITE-001`(引用検証ゲート) / `DD-CASEID-002`(符号正規化) / reality_check(D1-LIC resolved 5,475 / OPAC accepted edge 0)
- 実装(予定): `scripts/case_link_extract.py` / `scripts/test_case_link_extract.py`

> **目的**: 雑誌・文献の**本文**から該当判例を取り出し、評釈と判例を丁寧に繋いで**意味層を厚くする**。難所は「1記事:N判例（評釈と判例が 1:1 でない）」。これを**フラットなN本の同格エッジにせず、(判例, 役割) の型付きエッジ**として捕まえる。**識別(merge)はしない・自動リンクは masthead 由来のみ・本文由来は review-first。設計のみ・read-only。**

---

## 0. スコープと原則
- reality_check 厳守: **「LIC data_no を canonical case にしてはならない」「OPAC accepted edge 0」**。本 DD は**エッジ候補の生成と役割型付け**に限り、canonical 昇格・auto-merge はしない（CASE-001 AN-2: 関係は edge）。
- **抽出の価値はエッジ数でなく役割型**。1記事に判例が K 個出ても、K 本の同格 `mentions` を張ったら意味層はむしろ薄くなる。
- **精度優先(split-first)**: 誤った `annotates` は欠落より有害（利用者は「この評釈はX判例の解説」と信じる）。迷ったら review。

## 1. 決定① — 役割語彙（edge type）

1記事の複数判例は同格でない。本文採掘の各 mention を役割に分類する：

| 役割 | 典型シグナル | edge type | 既定信頼 |
|---|---|---|---|
| **評釈対象（主）** | masthead の表示判例 / 「本判決」「本件」共参照 | `annotates` | 高（masthead由来=自動可） |
| 同旨・参照（従） | 「同旨、最判平…」「参照、…」 | `cites_supporting` | review |
| 対比・反対（従） | 「これに対し」「反対、…」 | `cites_contrasting` | review |
| 背景・傍論言及（従） | 制度説明で一度きり登場 | `cites_incidental` | review |

- **未知 role は fail-closed**（候補から外し review へ）。
- `annotates` は原則 **1**。masthead が複数判例を表示する併合・同種まとめ評釈のみ N を許容（`annotates_multi` フラグで明示）。

## 2. 決定② — 記事タイプで条件分け（主検出の前提）

役割推定は記事ジャンルに条件づける。書誌 genre / タイトルパターンで安価に分類：

| 記事タイプ | 主(評釈対象)の有無 | 既定の扱い |
|---|---|---|
| **評釈 / 判例研究** | あり（masthead に表示判例） | masthead→`annotates`(主)、本文→`cites_*`(従) |
| 判例紹介 / 解説 | 弱い〜あり | masthead あれば主、無ければ全 `cites_*` |
| 論文 / 論説 | **なし**（テーマ横断で多数引用） | 1:1 復元しない。N本の `cites_*`。頻度・位置が突出すれば `central_case` ヒント |

- 1:1 を**無理に作らない**のが安全。論文は「中心判例」概念で代替し、`annotates` は付与しない。

## 3. 決定③ — 主検出シグナルの優先順位（高精度→低精度）

1. **書誌メタの表示判例**（masthead = 裁判所/日付/事件番号/出典）。D1-LIC crosswalk で構造化済みなら**決定的キー一致 = Tier A で自動リンク**。
2. **位置**: masthead 判例＝主、本文走り書き＝従。
3. **共参照**: 「本判決／本件／対象判決」は主を指す。
4. **頻度**: 主は全文反復、従は一度きり。

主の確定は (1) を最優先（構造由来=高精度）。(2)〜(4) は (1) を欠く/補強するときの従シグナル。

## 4. 決定④ — 抽出パイプライン（既存基盤への接続）

本文採掘の判例文字列は**部分引用が常態**（事件番号なし・「最判平成X年Y月Z日」だけ、OCR 揺れ）。よって：

```
記事 → (a)記事タイプ分類
     → (b)masthead 解析 → 対象判例候補【構造化・高精度】
     → (c)本文 citation-span 抽出 → 引用文字列リスト
     → (d)各文字列を case_number_norm + 符号正規化(CASEID-002)
     → (e)bind guard で canonical 解決:
            ・完全キー一致(masthead系) → Tier A → 自動リンク
            ・部分一致(本文系)         → Tier C → review レーン（fuzzy_review_candidates）
     → (f)role 分類（§1・§3シグナル）
     → (g)cite_gate で「引用が実在・解決可能か」検証 → 通過後にエッジを信頼
     → (h)typed edge 候補を corroborate L2/L3 へ供給
```

- **自動リンクは (e) Tier A（masthead由来）のみ**。本文由来は全て Tier C → review。先日実装した `fuzzy=C` 経路がここの安全弁。
- 出力は **corroborate の L2(`literature_about_case`) / L3(`case_cites_case`) の供給元**。CASELINK が (判例, 役割) を作り、CORROB が独立源一致で confidence を付ける、という分担。

## 5. why / alternatives_rejected
- **why 役割型付け**: 1記事:N判例を同格 `mentions` で潰すと、評釈対象と単なる参照が混ざり意味層が薄くなる＋誤った `annotates` を生む。役割を一級市民にする。
- **why masthead のみ自動**: 本文採掘は部分引用・OCR で本質的にノイジー。決定的キー(masthead)だけ Tier A、本文は review-first にして false link を防ぐ。
- **rejected**: 本文 mention を全部 accepted edge に直昇格（OPAC accepted 0・review-first＝却下）。論文の多数引用から無理に 1:1 評釈対象を選ぶ（誤 `annotates` 量産＝却下、`central_case` ヒントに留める）。抽出文字列を canonical key 化（reality_check 禁止＝却下）。LLM 一発で role 付与し検証なし（cite_gate 未通過の信頼は禁止＝却下）。

## 6. precision target（案・owner 判断）
- `annotates`（評釈対象）= **最高精度要求**（誤リンクが最も有害）。masthead 構造由来のみ自動、それ以外 review。
- `cites_*`（参照系）= 中。cite_gate 通過を必須、未解決は review。
- 計測は `DD-CASEEVAL` 系に link 用の gold（記事→(判例,役割)）を足して、`annotates_precision` / `cites_precision` を別建てで測る。

## 7. verification（予定）
- deterministic_self_verification: `test_case_link_extract.py` で fixture 記事（評釈1主＋従2 / 論文N / 併合 annotates_multi）を流し、role 分類・masthead=A・本文=C review・未知 role fail-closed・**merge 不発生**を確認。
- corpus-level = **Mac CC**: D1-LIC 5,475 を「本文に他判例引用を含む」観点で再走査し、masthead 対象以外の本文 mention を Tier C review として抽出。`annotates` 精度を実 gold で測る。
- independent_meaning_audit = 未了（DDCASE ゲート）。owner_approval = 未了。

## 8. follow-up / open questions
- 記事タイプ分布（評釈 vs 解説 vs 論文）を LIC 4誌で実測 → 条件分けの閾値確定（owner 提案: 設計前に分布を見る選択肢あり）。
- citation-span 抽出器の実体（規則ベース＋符号正規化 vs 統計）。本 DD は**役割モデルと結線**を確定し、抽出器実装は分離。
- `central_case`（論文の中心判例）を正式 edge type に昇格するか、ヒント止めか。
- masthead が複数対象（`annotates_multi`）のとき、各対象を独立 Tier A とするか、グループ評釈として束ねるか。
- 逆向き 1判例:N評釈（landmark に評釈集中）は**歓迎方向**＝多源 annotation corroboration として CORROB L2 で confidence 加点。
