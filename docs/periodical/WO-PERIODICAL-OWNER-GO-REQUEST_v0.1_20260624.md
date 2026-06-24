# WO-PERIODICAL-OWNER-GO-REQUEST: 雑誌オブジェクト 記事・本文層の着手承認（exact owner GO 文言）

```yaml
doc: WO-PERIODICAL-OWNER-GO-REQUEST
for: DD-PERIODICAL-002 (記事・本文層)
date: 2026-06-24 JST
owner: asai@asai-lo.com
protocol: AI_READY Wave51/Wave58 OWNER_GO_PHRASE_MATRIX 準拠（行為/対象/検証/ロールバック/権限範囲を明記）
rule: 各GOは独立。承認は「GO-n 承認」と返すだけでよい。無記載は不承認＝設計のみ継続。
```

下表の GO は**リスク昇順**。GO-1 は ready・低リスク（即着手推奨）、GO-3/4/5 は HIGH-HOLD レーンで生payload/OCR/外部メタに触れるため要明示承認。

---

## GO-0 ── locator 行抽出（REFERENCE_ONLY・実質承認不要）
- **行為**: ローカルちゃんが `docs/alo/AI_READY_DATA_LOCATOR_INDEX_LATEST.tsv` + `QUERY_CHEATSHEET` から雑誌関連レーン(`pacsigny`/`scan_data`/`legal_thought`/D1/periodical)の `locator_id`/`primary_location`/`read_first`/`currentness`/`safety_note` のみ抽出。
- **対象**: 上記2索引のメタ行のみ。**生payload・rawファイルは開かない**。
- **検証**: 出力はパス文字列とフラグのみ（中身ゼロ）。
- **ロールバック**: 出力破棄で原状（read-only）。
- **権限範囲**: REFERENCE_ONLY_NO_ACTION。→ atlas規定上ほぼ自動。**「GO-0 承認」で即実行**。

## GO-1 ── L1×L3 記事↔issue_id 接合 dry-run（D1レーン・read-only・最高レバレッジ）
- **行為**: Mac-local の D1 labeled(`article_meta_labeled.jsonl`)を read-only で走査し、各記事を確定済み issue_id へ接合した**候補マップ(CSV)**を生成。article_id 規約 `{issue_id}#a{seq}` を付与。
- **対象**: D1 labeled（read-only） + 確定済み authority v4。**書込なし**。
- **検証**: `article_orphan`(号未解決)/`article_collision`(同id重複) を回帰検査、0件を確認。被覆率報告。
- **ロールバック**: 候補CSV削除で原状。DB/canonical 不変。
- **権限範囲**: LOCAL_READONLY_DRYRUN。canonical昇格・DB投入・edge化は**含まない**（別GO）。

## GO-2 ── 初出スキーマ(article_first_pub) 設計dry-run（メタのみ・本文なし）
- **行為**: D1メタ範囲で初出/再録の**候補判定ロジック**を設計・小規模試走（同一標題+著者の異誌出現を初出候補に）。
- **対象**: D1メタ（read-only）。pacsigny本体には**まだ触れない**。
- **検証**: `firstpub_conflict`(複数初出主張) 検査。サンプル目視用に20件出力。
- **ロールバック**: 出力破棄。
- **権限範囲**: LOCAL_READONLY_DRYRUN。

---
（以下 HIGH-HOLD。生payload/OCR/外部メタに触れるため要明示）

## GO-3 ── `pacsigny` 初出メタ抽出（HIGH-HOLD）
- **行為**: SIGNY論考レーンから初出メタを抽出し article_first_pub を実体化。
- **対象**: `pacsigny` レーン生メタ（locator read_first 経由）。
- **検証**: firstpub_conflict=0、provenance記録。 **ロールバック**: 抽出物 quarantine→破棄。
- **権限範囲**: HIGH-HOLD解除。**provider/license 批准も要**（atlas: PROVIDER_OR_LICENSE_RATIFICATION）。

## GO-4 ── `scan_data` 取込＋OCR（HIGH-HOLD・L0-L2）
- **行為**: DVD/生スキャン(金融・商事判例/金融法務事情等)を L1分割→OCR→L2本文化。OCR conf 保持。
- **対象**: Box `scan_data` レーン生画像。 **検証**: 分割境界の目視抜取、OCR conf 分布、誤分割検査。
- **ロールバック**: 派生物 quarantine→破棄。原盤不変（非破壊）。
- **権限範囲**: HIGH-HOLD解除＋license批准。本文の外部公開は**別途**（external_share=false不変）。

## GO-5 ── `legal_thought` 取込（HIGH-HOLD）
- **行為**: 法学論考レーンを L4/L5 補助メタとして取込。 **対象**: `legal_thought` レーン。
- **検証**: edge_falselink 検査。 **ロールバック**: quarantine→破棄。 **権限範囲**: HIGH-HOLD解除。

---
## 推奨
**GO-0 + GO-1 を先に**（どちらも read-only、リスクほぼ無し、L1×L3接合という土台が即進む）。
初出・OCRの本丸(GO-3/4)は license/provider 批准が絡むので、GO-1 の dry-run 結果を見てから判断で十分。
私(head)は GO の有無に関わらず設計・監査規格化は進める。承認は「GO-n 承認」で。
