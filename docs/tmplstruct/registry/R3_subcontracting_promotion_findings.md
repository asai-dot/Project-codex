# R3 最小実証 findings: subcontracting の L4 accepted 昇格は「2冊目独立接地」待ちで正しく止まる

> date: 2026-06-15 / author: 番頭(リモートClaude) / 文脈: registry shell v0.2 が「動く」ことの実証(R3最小)。
> **結論**: registry のゲートは正しく機能した。subcontracting は **L4=candidate のまま**（accepted に上がらない）。
> 不足は「独立な2冊目の解説への接地」であり、その**正確なアドレスは特定済み**。律速は本文OCR源（自炊 or 弁コム全文）であって、TOC ではない。

## 1. やったこと（OCRなし・DB照会のみ）
1冊目接地（`poc_grounded/saiitaku.knowledge.json`）= **業務委託契約書作成のポイント〈第2版〉**（近藤圭介／中央経済社／自炊済み）pp.75-78。
独立な2冊目を `biblio.toc_nodes`（弁コムTOC・552k行）から横断検索し、**著者も出版社も別**の候補を特定した。

### 独立2冊目の最有力（同型・同論点）
| 項目 | 値 |
|---|---|
| 書名 | **業務委託契約書の作成と審査の実務〔全訂版〕** |
| 著者 | 滝川宜信・弁護士法人しょうぶ法律事務所（1冊目=近藤圭介と別） |
| 出版社 | 民事法研究会（1冊目=中央経済社と別） |
| アドレス | `…全訂版〕_01:toc:246` / 印刷p187 |
| パス | 第3章 モノに関する業務委託契約書 > 第1節 製造委託基本契約書 > 5 …実務上の留意点 > **POINT⑨ 再委託の禁止** |
| 同型性 | 1冊目と同じ「製造委託基本契約 × 再委託」＝apples-to-apples |
| 他の再委託節 | 同書に計7か所（設備製造/OEM/M&A/構内作業/ソフト開発/AI開発）→ 接地の厚みは十分 |

他の独立候補（同じく弁コムTOCあり）: 契約書作成の実務と書式〔第2版〕(有斐閣)・下請法の法律相談(青林書院)・取引基本契約書の作成と審査の実務(滝川/民事法研究会＝1冊目とは別だが2冊目候補とは同著者)。

## 2. ブロッカー（owner 認識と一致）
独立2冊目候補は **`scanned=null / has_pdf=false`**＝**自炊PDFが環境内に無い**（TOCは弁コム由来）。
一方、自炊済み（`has_pdf=true`）の契約本（学陽書房・商事法務・ぎょうせい等）は **再委託のTOCアドレスを持たない**。
→ **「自炊済み(OCR可) ∧ 再委託のTOCあり ∧ 1冊目と独立」を満たす本が現状ゼロ**。
→ つまり2冊目接地には (a) 独立本の自炊、または (b) 弁コム全文OCR が必要。**綺麗なTOCはあるが本文が無い**＝owner指摘の状況そのもの。

## 3. これが実証したこと（registry が「動く」証拠）
- registry のゲート `G_SINGLE` / `G_L4_ACC` が、**独立源1のまま accepted へ上げることを正しく拒否**した。
- システムは「何が足りないか（独立2冊目）」と「どこから取るか（toc:246/p187）」を**正確に提示**できた。
- 接地を捏造して accepted にすることは `gate_grounding_citation_required` 違反＝やらない。
- ∴ **registry は設計どおり機能**：早すぎる昇格を止め、次に必要な入力を一点に絞り込む。これがR3で見たかった挙動。

## 4. registry の状態（変更なし・正しい）
- `subcontracting`: term_identity=candidate / l2_anchor=seed / **l4_design=candidate（据え置き）**。
- `n_independent=1` のまま。2冊目接地が入って初めて `n_independent=2`＋`source_independence_checked=true` となり accepted 候補になる。
- seed の `notes` に本findingsへの参照を追記（接地候補アドレスを記録）。

## 5. 昇格の正確な手順（OCR源が来たとき）
1. `業務委託契約書の作成と審査の実務〔全訂版〕` p187（toc:246）を point-OCR（1冊目と同じ proven path）。
2. `poc_grounded/saiitaku_2.knowledge.json` を grounded_from 付きで抽出（evidence_purpose=design_rationale）。
3. registry の subcontracting を更新: design_knowledge_ref に2件目追加 / design_knowledge_count=2 / n_independent=2 / source_independence_checked=true / no_unresolved_contradiction 確認 / applicable_scope 明示。
4. バリデータ通過後、GPT 再監査 → owner ratify で **l4_design_status=accepted**。

## 6. owner 判断（ゆっくりで可）
- (a) 独立2冊目（業務委託契約書の作成と審査の実務 等）を**自炊キューに載せる** → 載れば上記手順で accepted 1件成立（R3完了）。
- (b) 当面 candidate 据え置き（registry の挙動は実証済みなので急がない）。
- 本件は `SCAN_ORDER_honmaru3.md` に「再委託 accepted 用の独立2冊目」として1行追記する価値あり。
