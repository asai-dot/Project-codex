# 突合(同定)の重大ヒント: 出版日・版・ページ数・TOC項目【owner指摘 2026-06-15】

owner指摘: **出版日 / 版 / ページ数 / TOCの項目** が突合の重大なヒント。
ISBNを持たない弁コム・legal-library では、この4つが**事実上の“版の指紋”**になる。

## なぜ効くか（4信号の性質）

| 信号 | 突合での働き | 版の分離 |
|---|---|---|
| **出版日(pub_date, 年月日)** | 年より細かい。別の本が同一 pub_date を共有する確率は低く、同一書は各ソースで一致しやすい | 版ごとに pub_date が違う → **同名でも版を弁別** |
| **版(edition_statement, 第N版)** | 直接「どの版か」を言う。突合キーに**必須**（無いと別版を誤マージ） | 版の弁別そのもの（版を束ねない原則の番人） |
| **ページ数(page_count)** | 同一版はほぼ同ページ。強い弁別子（DD-LITID E3 fingerprint に既収載） | 版が違えば頁数が動く → 版差の検出 |
| **TOC項目(正規化見出し列＋level＋ページ範囲)** | **ISBNなし本の決め手**。弁コム/legallib は TOC 100%保有。見出し列＝版固有の指紋 | 改訂で章追加・頁シフト → TOC が乖離 ＝ **版差を最も鋭く検出** |

→ 4つは単独でなく**合わせて**「同一作品か」「同一版か」を同時に判定する。特に **pub_date＋edition＋page_count＋TOC** が揃えば、ISBN無しでも版レベルで確定に近づく。

## 既存設計との対応（DD-LITID-001 / lane plan B2）

- 既に在る: E3 `biblio_fingerprint_v1 = sha256(title+publisher+**year**+**page_count**+**edition_statement**+volume)`、E4 `toc_fingerprint_v1`（見出し列＋level列＋page列）。→ **page_count・edition・TOCは既に証拠化済み**。
- **強化提案（本ヒント反映）**:
  1. **`year` → `pub_date`（年月日）に細粒度化**（または pub_date を独立証拠として加点）。年同一でも月日差で別版を弁別できる。
  2. **TOC項目を no-ISBN 層の主証拠に格上げ**（E4 を E5 の補強でなく、弁コム/legallib では準・主キー級に）。lane plan B2 の読み（「詳細目次が同定の決め手」）と一致。
  3. TOC の **page範囲列**を版差検出に明示利用（見出し一致でも頁レンジがずれれば版差候補）。

## 監査反映 v0.2（お目付け役 `DESIGN_PASS_WITH_NOTES` 2026-06-16 / result Box 2287192002732）

「信号を足すほど false-match と false-split の両方が増える。足す前に独立性・粒度・許容差・confirm昇格規律を固定せよ」。must-fix 5件を反映:

1. **pub_date を単値にしない**: `pub_date_value` ＋ `pub_date_precision ∈ {year, year_month, full_date, unknown}` ＋ `pub_date_kind ∈ {publication, release, impression, database_recorded, unknown}`。比較は full 一致を硬条件にせず**粒度互換判定**（初版日 vs 重版日 vs 奥付日の混在で false-split を防ぐ）。
2. **TOC独立性**: `toc_provenance_family ∈ {publisher_official, vendor_redistribution, ocr, manual}` を導入。TOC一致は no-ISBN の主証拠にしてよいが、**独立性は family 単位で数える**（弁コム×legal-library の同一出版社TOC再配信を独立2本に数えない）。
3. **page_count を硬キーにしない**: `page_count_value` ＋ `page_count_basis`（NDL extent / 出版社 / 本文 / 索引込 / 電子 / PDF）＋ 許容差（初期 **±2〜5p または ~5% の soft match**）。範囲・「xx, 300p」形式は raw 保持。
4. **confirm昇格＝独立 evidence family 2本以上**（field数で数えない）。pub_date と edition が同一書誌レコード由来なら**1 family**。確定は (A) strong identifier(ISBN/NDL/official)1本＋補助1本、または (B) 独立 family 2本（例: publisher TOC ＋ NDL page_count／legal-library TOC ＋ NDL title/extent）。title-only は候補化禁止を継続。
5. **版分離 vs 刷違いを分ける**: 版差は `edition_statement / pub_date_kind / toc_delta / page_delta / title_delta` の**複合**で判定。刷・印刷だけの差は `same_edition_impression_variant`（過剰分割を防ぐ）。

should-fix: TOC類似閾値を raw label/normalized label/depth path/page range の複合で定義、部分一致の判定表（same_work_candidate/same_edition_candidate/review）、**proxyの34件edition_suspectedを gold mini set 化**、供給元別 page confidence。

next（監査指定）: ①本noteへ反映（本節）→ ②34件の手動分類 → ③**501本番前に independent evidence family counting を実装** → ④dry-run結果を再投函。

---

## 私の proxy で露呈した穴（このヒントが直す）
- 縮小版dry-run(`..._proxy_dryrun_result.md`)は **出版“年”だけ**で edition_suspected を 34件出した＝**粒度が粗い**。
- 本ヒントの **pub_date＋edition＋page_count＋TOC** を使えば、その34件を「真の別版」「同版の表記揺れ」「同名異本」に**正しく腑分け**できる（triage `edition_suspected` の解像度が上がる）。

## データ上の要対応（gap）
- **弁コム biblio raw に page_count が無い**（現状キー: 識別子＋TOCのみ）。page_count を突合に使うには**corpus層 or NDL から page_count を供給**する必要がある（NDL parser は `ndl_pages` を抽出済み＝NDL経由で補完可能）。
- pub_date: 弁コムは `publication_date`、蔵書/NDLは別フィールド → 年月日へ正規化規則を1本化。

## 反映先
- 同定(identity)レーン B2 / DD-LITID E3-E4: 上記「強化提案」を Mac側 fingerprint 実装に反映（owner→お目付け役ルート）。
- 本番501 dry-run（WO `2286268562080`）の edition_suspected 判定に pub_date/edition/page_count/TOC を使う旨を、ワーカー実行時の判定基準として追記可能。

## 投函記録（お目付け役 to_gpt/・2026-06-15）
- レビュー依頼: `20260615_DD-LITID-FP_matching_signal_strengthening_REVIEW_REQUEST.md`（Box `2287177276619`、status=queued）
- 現物: `20260615_DD-LITID-FP_matching_signals_note.md`（Box `2287161796030`、source_hash sha256:23f4666f…fb66）
- 結果待ち: `from_gpt/20260615_DD-LITID-FP_matching_signal_strengthening_RESULT.md`
