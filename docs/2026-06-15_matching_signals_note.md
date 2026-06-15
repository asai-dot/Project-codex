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

## 私の proxy で露呈した穴（このヒントが直す）
- 縮小版dry-run(`..._proxy_dryrun_result.md`)は **出版“年”だけ**で edition_suspected を 34件出した＝**粒度が粗い**。
- 本ヒントの **pub_date＋edition＋page_count＋TOC** を使えば、その34件を「真の別版」「同版の表記揺れ」「同名異本」に**正しく腑分け**できる（triage `edition_suspected` の解像度が上がる）。

## データ上の要対応（gap）
- **弁コム biblio raw に page_count が無い**（現状キー: 識別子＋TOCのみ）。page_count を突合に使うには**corpus層 or NDL から page_count を供給**する必要がある（NDL parser は `ndl_pages` を抽出済み＝NDL経由で補完可能）。
- pub_date: 弁コムは `publication_date`、蔵書/NDLは別フィールド → 年月日へ正規化規則を1本化。

## 反映先
- 同定(identity)レーン B2 / DD-LITID E3-E4: 上記「強化提案」を Mac側 fingerprint 実装に反映（owner→お目付け役ルート）。
- 本番501 dry-run（WO `2286268562080`）の edition_suspected 判定に pub_date/edition/page_count/TOC を使う旨を、ワーカー実行時の判定基準として追記可能。
