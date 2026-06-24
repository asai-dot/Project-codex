# P19: 未解決ロングテール SRU 網羅取得 + ローカルちゃん誌名同定

```yaml
artifact: P19_sru_tailfill_and_localchan
generated_at: 2026-06-25 JST
based_on: P17_local_agent_handoff_20260624.md / P18(v2) e0ea629
branch: claude/periodical-sru-tailfill  (claude/magazine-object-analysis-seg9cr の e0ea629 から派生)
gate: read-only検証 + authority CSV拡張のみ。DB投入/canonical promotion/accepted edge化/外部公開はHOLD。
push: 保留（並行する P18v2 エージェントと同一成果物のため、owner が整合方針を決めてから）
```

## 0. 背景（P17本命の前提崩れ）
P17 Task A は「NDL書誌バルク ~240万レコードが Mac 手元にある」前提だったが、実機探索の結果**そのバルクは存在しない**（最大でも `magazine_bib_NDL.jsonl`=407行、`ndl_serial_issn_overlay.csv`=479行）。P18(v2) は静的データ上限（423誌 resolved / 記事被覆95.2%）まで到達済み。
→ 残ロングテールを詰める唯一の道として、**未解決誌名を NDL SRU でライブ取得**した（CiNii/Portalは403、NDL SRUは可）。

## 1. SRU 網羅取得（518誌）
- 入力: P18v2 で `unresolved` の 518誌（`d1_journal_issn_authority_ALL_resolved.csv`）。
- 手法: NDL SRU `searchRetrieve` を誌名で叩き、記事レコードの `dcndl:publicationName` が照会誌名と
  **norm一致(exact)** したレコードの `dcterms:isPartOf .../issn/` を採用。
  norm = NFKC + 旧字マップ(獨→独, 應→応, 醫→医 等30字) + 併記分離(`= / : （ <`)。
- 誤マージ厳禁: publicationName の **exact一致のみ**採用。部分一致/複数ISSNは採用せずレビュー行へ。

### SRU 結果内訳（518誌）
| status | 誌数 | 扱い |
|--------|------|------|
| sru_unique（誌名exact一致→単一ISSN） | 12 | 決定的に解決・採用 |
| sru_ncid（ISSN無→単一NCID） | 11 | 決定的に解決・採用 |
| sru_review_substring / ambiguous | 77 | グレー→ローカルちゃん一次裁定（§2） |
| unresolved_confirmed（NDLにキー無し） | 418 | 紀要/廃刊/総称中心。実在キー無しを確認 |

### authority CSV への反映（決定的分のみ）
- 出力: `d1_journal_issn_authority_ALL_resolved_v2_sru.csv`
- P18v2 ベース(423 resolved)に SRU決定分を統合 → **442/931 resolved (47.5%)**、**記事被覆 288,655/302,130 = 95.5%**（+0.3pt）。
- 採用は sru_unique/sru_ncid の **exact一致決定分のみ**。advisory（§2）は未promote。

## 2. ローカルちゃん発注（誌名 same/different 一次裁定）
グレー残差77件を bounded タスク化し、`author_snd` と同型で発注。
- job: `journal_snd__20260625_051557`（qwen3:30b, batch3, schema制約）
- 前処理: 決定的に解けた分はコードで auto-confirm 済み、**候補数件付きのグレーのみ**投函。
- ベンチ: 実dispatch経路で5件 → 5/5正答・ハルシネーション0・sanity HEALTHY（総称→特定誌の過剰マージを none+uncertain に矯正済）。
- 本走: 77/77完了・sanity HEALTHY・ハルシネーション0・欠落0。

### advisory 内訳（要 owner ratify・正準直書きせず）
| class | 件数 | 意味 |
|-------|------|------|
| advisory_same_issn | 2 | 同一誌かつISSN有→ratifyで即解決 |
| advisory_same_noissn | 35 | 同一誌だがNDL候補にISSN無→NCID後追い候補 |
| none_unresolved | 40 | 同一候補なし（過剰マージを正しく拒否） |

**advisory_same_issn（ratify候補）:**
- 法律科学研究所年報 → 明治学院大学法律科学研究所年報（ISSN 2185-2278）
- 法学会雑誌(東京都立大学) → 東京都立大学法学会雑誌（ISSN 0389-8571）

詳細: `P19_localchan_journal_identity_advisory.csv`（pick/uncertain/reason/候補ISSN付き全77件）。

## 3. 成果物
- `d1_journal_issn_authority_ALL_resolved_v2_sru.csv` — SRU決定分統合版（442 resolved）
- `P19_localchan_journal_identity_advisory.csv` — ローカルちゃん advisory 全77件
- `sru_results_20260625.jsonl` — SRU生結果（provenance）

## 4. 次アクション（owner ratify 待ち）
1. **並行 P18v2 との整合**: 本ブランチは派生。owner が P18v2(magazine本線) と本SRU増分の統合方針を決定 → 私が push/マージ。
2. **advisory_same_issn 2件** を ratify → resolved へ promote（+2誌）。
3. **advisory_same_noissn 35件** の NCID 後追い要否判断（ISSN無のため被覆%には効かない・identity網には効く）。
4. unresolved_confirmed 418誌は実在キー無し → isbn_per_issue 化（書籍シリーズ）か恒久 unresolved 受容。

## 5. 制約（再掲）
- 全 advisory は助言。**正準DB直書き・identity自動マージ禁止**。`external_share_allowed`=false。
- 作業は隔離worktree（メイン共有ツリーは複数ワーカー稼働中のため不可侵）。
- model id は記載しない。
