# TOC RECONCILIATION — 既存TOC統合アーキテクチャとの突合（M0撤回）

- 作成: 2026-06-23
- 経緯: 文献オブジェクト棚卸し後に **TOCマスター契約 M0 v0.1** を起草したが、`from_gpt` 監査済みの
  **成熟した先行TOC統合設計（DD-TOCATTACH / DD-TOCADOPT / DD-TOCNODES）が既存**と判明。M0は再発明のため撤回。
- 本書 = 既存設計の所在・対応表・M0からの差分救済（=本当に新規の貢献）・前進方針。
- 出典: Box `from_gpt/` の各監査RESULT現物（file_id併記）。

## 1. 既存TOC統合アーキテクチャ（監査済み・一部本番適用済み）

| 層/設計 | 内容 | 監査ラベル | file_id |
|---|---|---|---|
| **DD-TOCNODES** | `bib_toc`(552,544) → `toc_nodes` 移行。**2026-06-12 本番適用済**。行数保存・親整合・node_id重複0確認 | `PRODUCTION_APPLY_PASS_WITH_NOTES` | 2286012501212 |
| **DD-TOCATTACH-001 v0.3** | 三層: snapshot(不変観測)/attachment(状態)/canonical projection(導出)。sticky node_id・crosswalk・granularity guard・provenance group votes | `PASS_WITH_NOTES` | 2278438348115 |
| **DD-TOCADOPT-001 v0.1** | 採用ルール: 「源の順位」→「本/ノード単位で最良中身」。edition identity / append_missing_only / votes_by_provenance / 実装7ゲート | `PASS_WITH_NOTES` | 2286066609478 |
| **TOC取得状況報告** | 収集データの権利/規約レビュー層（LIC本文・TOC大量抽出の扱い） | `MODIFY_REQUIRED`(rights) | 2276845856986 |

### 重要な既知事実（私が「発見」したが既知だったもの）
- `toc_source='unknown'` は **意図的な暫定値**（DDTOCNODES N2: provenance取得分だけ後続で昇格。unknownをsource confidenceに使わない）。→ 私のG1は既知。
- `toc_nodes` と `bib_toc` の二重 = **移行の互換維持**（`v_bib_toc_compat` view、旧表は安全のため未削除）。→ 私のG6は既知。
- canonical一本化・最精度選択 = TOCATTACH(canonical projection)＋TOCADOPT(best-content-per-node)で**設計済み**。→ 私のG4は既存。

## 2. M0 契約 ⇄ 既存設計（重複マップ＝撤回理由）

| M0 v0.1 の節 | 既存の対応 | 判定 |
|---|---|---|
| §1 canonical一本化(toc_nodes) | TOCNODES移行済 + TOCATTACH canonical projection | **重複・撤回** |
| §2 toc_source語彙 / origin_family | TOCATTACH provenance group / DDTOCNODES unknown昇格 | **重複・撤回** |
| §3 golden/silver/bronze | TOCADOPT votes_by_provenance + protected_sources（枠組み相当） | **重複・撤回**(語彙は供給可) |
| §4 最精度選択スコア | TOCADOPT best-content-per-node + granularity_guard(20%) | **重複・撤回** |
| §5 append-only governance | TOCATTACH snapshot不変 + sticky id（D0と整合済） | **重複・撤回** |
| §6 self TOC ingest | （未カバーの可能性＝§3で救済） | 一部新規 |
| §7 OCR残差化 | （明示されていない＝§3で救済） | 一部新規 |

→ **M0 v0.1 は撤回**（`dd/` から削除、git履歴に残置）。to_gpt の M0 REVIEW_REQUEST は**取り下げ**（未レビュー）。

## 3. 救済＝本当に新規の貢献（既存に無い／既存が待っているもの）

棚卸しの中で、既存設計と重複せず**前進に効く**のは次の3点のみ。

### N-1【最重要】1,509 self×bencom 一致 = 既存設計が待つ「cross-source gold」
- TOCATTACH v0.3 は明言: **"Keep automatic crosswalk limited to same-source swaps until cross-source gold evidence exists"**
  （異源 rebasing は cross-source gold が出るまで review-first で HOLD）。
- 私の棚卸し: **self(asai-bookshelf)×bencom のタイトル一致 1,509。うち810は self側が ISBN+NDL 保持**。
- これは**異源（self_scan ≠ bencom_provider）の独立ペア**＝TOCATTACHが解禁条件にしている cross-source gold の**候補そのもの**。
- → 貢献: 1,509(優先810)を **TOCADOPT/TOCATTACH の cross-source gold 候補**として供給。

### N-2 bookshelf_self TOC(≈777k/5,206ファイル) が canonical 未投入
- `toc_nodes` は bencom 3,802冊(552,544)のみ。Box `app/data/toc`(folder 370441454337)の self TOC は**toc_nodesに未投入**。
- 既存TOCADOPTの源リスト（manual/ndl_partinfo/publisher/toc_pdf/bengo4/legallib）に **bookshelf_self が含まれるか要確認**。
- → owner/設計確認: bookshelf_self を canonical の一源として TOCATTACH snapshot に取り込む計画があるか（未計画なら新規source登録）。

### N-3 全量スケール差
- 既存 dry-run = tocattach_projection_dryrun **116,727ノード/631クラスタ**（部分集合）。
- 実在は bencom 552,544 + self ≈777,999。**全量適用時のスケール挙動は未検証**。

## 4. 前進方針（M0に代えて）

1. **M0撤回**・本reconcileをPRに記録。
2. **N-1を成果物化**: 1,509ペア（810優先）を `artifacts/` に cross-source gold **候補**リストとして出力（read-only・candidate≠confirmed）。TOCATTACH/TOCADOPTのcross-source gold gateへ供給。
3. **N-2/N-3を owner/設計クエリ化**: bookshelf_self の canonical 取込計画の有無、全量スケール検証の要否。
4. TOC棚卸し artifact（`TOC_two_corpora_inventory_20260622.md`）は**測定値として保持**するが、構造論点は既存設計に帰属する旨を追記。

## 5. 監査拘束（不変・既存と同一）
- candidate≠confirmed / cross-source rebasing は gold 確定まで HOLD（TOCATTACH準拠）。
- toc_source unknown を confidence に使わない（DDTOCNODES N2）。
- production projection / embedding refresh / API露出 / 旧表削除 は別ゲート HOLD。
- 有償DB本文・TOC大量再配布は権利レビュー前 HOLD（TOC取得状況報告）。
