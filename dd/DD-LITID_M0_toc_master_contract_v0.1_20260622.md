# DD-LITID M0 — 文献オブジェクト TOC マスター契約 v0.1（golden/silver/bronze ＋ 最精度選択）

- 作成日: 2026-06-22
- 位置づけ: 文献オブジェクトの **L3内容層（TOC）→ L5マスター層** をつなぐ設計契約。
  実測前提 = `artifacts/TOC_two_corpora_inventory_20260622.md`（2コーパス棚卸し）。
- 上位設計: DD-LITID v0.4 / D0（決定・証拠契約）/ Q（評価ゲート）。本契約は **D0の枠組みをTOCに適用**したもの。
- 監査拘束（不変）: candidate≠confirmed / coverage≠correctness / silent mutation禁止 / external_egress=prohibited。
  **本契約は設計のみ。ingest実行・DB write・embedding生成・promote・外部公開は HOLD（別gate）。**

---

## 0. 何を解く契約か（棚卸しからの3事実）

| 事実（実測） | 含意 |
|---|---|
| TOCは3表現: bencom `toc_nodes`(階層)＝`bib_toc`(flat) 同一corpus、self-scan Box(5,206/≈776,999) は別corpus・DB未投入 | canonical一本化 ＋ self取込が要る |
| bencom: TOC完備(552,544・空0・page0)だが ISBN6/NDL0。self: ISBN5,397/NDL5,002 だがTOCはBox | 識別子が**相補的** |
| title一致1,509（うち self が ISBN+NDL 持ち 810） | **同一版に複数TOC**が生じる＝最精度選択が必要。810は bencom同定の貸与候補 |

→ 本契約は **(A)TOCのcanonical定義 (B)出所source語彙 (C)品質status階層 (D)複数TOC時の最精度選択 (E)非循環ガバナンス** を定義する。

---

## 1. TOC マスターの層（L3→L5）

```
L3-raw    各源のTOC（bencom DB既存 / self-scan Box JSON / 将来 ndl_toc / ocr_colophon）
            = 不変・出所つき。捨てない。
L3-canon  canonical TOC ノード = biblio.toc_nodes（階層・path・page・embedding枠を持つ）
            bib_toc(flat) は L3-canon からの派生ビュー扱い（新規 truth にしない）
L4-select 同一 edition に複数TOCがある時の primary/alternate 選択（§4 スコア）
            alternate も retain（最精度選択は破壊しない）
L5-master accepted_toc_state: status=golden/silver かつ Q-gate 通過のみ（本段 HOLD）
```

- **edition 単位**: TOCは「holding」でなく「edition_manifestation」に束ねる（DD-LITID の decision_type に従う）。
  同一editionの self-TOC と bencom-TOC は **同一 edition_key 配下の複数 evidence**。

---

## 2. `toc_source` 語彙（出所・実測ベース）

| toc_source | 意味 | 現状件数 | origin_family（D0連携） |
|---|---|---|---|
| `bencom_import` | 弁コム由来TOC（DB既存） | 552,544ノード/3,802冊 | bencom_provider |
| `bookshelf_self` | 自炊/自所 TOC（Box app/data/toc・未投入） | ≈776,999/5,206冊 | self_scan |
| `ndl_toc` | NDL目次（将来・補完） | 0 | NDL |
| `ocr_colophon` | OCR抽出（将来・残差専用） | 0 | colophon |

- **独立性ルール（D0踏襲）**: 同一 `origin_family` のTOCは独立証拠に数えない。
  `bencom_import` と `bookshelf_self` は **別 origin_family ＝独立2証拠になりうる**（これが1,509の価値）。

## 3. `toc_status` 階層（golden / silver / bronze）

| status | 定義 | 判定条件（初期） | 現状該当 |
|---|---|---|---|
| `golden` | 検証済み・正本 | 人手裁定 verified、**または** 異origin独立2源のTOCが内容一致(≥θ) | 0（未着手） |
| `silver` | 構造健全・単一源・未検証 | 単一source・page/title完備・depth健全・空率<ε | **bencom 現状がここ**（page0/title0） |
| `bronze` | 機械抽出のみ・要検証 | OCR等・構造不全・空率高・page非単調 | 将来 ocr_colophon |
| `unknown` | 未分類（現DB初期値） | 上記未判定 | 全件（移行対象） |

> owner確認: 「silver = bencom現状（単一源・構造健全・未検証）」で合意でよいか。
> golden昇格は **(i)人手 or (ii)self×bencom独立2TOC一致** の二経路。(ii)が自動golden化の本命。

## 4. 最精度選択規則（同一editionに複数TOC・G4）

同一 edition_key に複数 `toc_source` のTOCがある時、**primary を選ぶが alternate を捨てない**。

```text
toc_quality_score（source単位・edition単位で算出）:
  + node_count            ノード数（情報量）
  + depth_coverage        depth≥2 比率（階層の濃さ）
  + page_monotonicity     print_page の単調増加率（健全性）
  + nonempty_rate         空title率の逆数
  - dup_rate              同一(title,page)重複率
  （重みは1,509較正で freeze。本段は型のみ）

primary = argmax(score)、他は alternate として retain。
両source score 拮抗かつ内容一致(≥θ) → status 候補 golden（独立2証拠）。
両source 内容不一致(<θ) → confusion bucket: same_work_diff_edition / 別版疑い → manual_review。
```

- **不一致は捨て情報でなく信号**: 別版・改訂・合冊の検出器（Q3 buckets へ流す）。

## 5. ガバナンス（D0踏襲・append-only）

- TOC選択・status昇格は **decision_event** で記録（行更新でなく追記）。
  `subject_ref=edition_key, decision_type=toc_primary|toc_status, event_type=candidate|verified|...`。
- **非循環（Q1）**: candidate生成に使った source を同一subjectの正解にしない。
  self×bencom一致で golden化する時、両者は別origin_familyなので非循環が成立（◎）。
- **gold seed = 1,509**（うち self が ISBN+NDL の 810 を最優先）。これを Q評価の正解集合の起点に。

## 6. self TOC 取込（ingest）契約 — CONDITIONAL（owner確認後）

```text
方向: Box app/data/toc（read-only export）→ staging（isolated）→ toc_nodes(source=bookshelf_self)
不変条件:
  - source manifest/hash/parser version 保持
  - canonical/DB本体を直接書き換えない（staging経由・再生成可能）
  - reject/error/dup レポート同時生成
  - Box source を変更しない / 外部egressなし
  - edition_key への束ね前に DD-LITID 同定candidateを通す（holdingに直貼りしない）
```

## 7. OCR の位置づけ（残差専用・確定）

- bencom TOC が既に **silver**（page/title完備）で 3,802冊揃う以上、**OCRは全件前提でない**。
- OCR投下先 = **G7残差**（同定貸与で埋まらない bencom）＋ 版/刷曖昧例 ＋ self未TOC（6,524−5,206≈1,318冊）。
- 611 PDF（pdf_inventory）→ 難所専用に限定。`toc_source=ocr_colophon`/`status=bronze` で入り、検証で昇格。

## 8. HOLD（本契約が止めるもの）

- self TOC の実 ingest / DB write / toc_nodes への source・status backfill
- embedding 生成（0→生成）
- accepted_toc_state への昇格 / golden 自動確定の実行
- bib_toc の廃止（派生ビュー化は別タスク）
- 上記はいずれも本契約承認＋Q-gate 後の別 gate。

## 9. 次段
- M1: 1,509較正 — self×bencom TOC内容一致スコアθの決定（最精度選択・golden経路の閾値）。
- Q接続: 不一致buckets を Q3 へ、θ判定を Q4 数値計画へ。
- owner確認事項: §3 silver定義 / §6 ingest方向 / §7 OCR残差化。
