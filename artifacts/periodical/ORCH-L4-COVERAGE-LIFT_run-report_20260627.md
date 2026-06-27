# ORCH-L4-COVERAGE-LIFT 実行報告（Worker Claude Code）

- order: `artifacts/periodical/ORCH-L4-COVERAGE-LIFT_order_20260626.md`
- 実行日: 2026-06-27
- 実行者: Worker Claude Code（記事接合再実行・誌調査）
- 検証ラベル: **deterministic self-verification completed / independent meaning audit pending（head 受入監査 → 必要なら GPT Pro）**
- read-only / dry-run 厳守: DB / Box / 外部公開 / canonical昇格 / accepted edge化 いずれもなし。authority CSV 増分と join dry-run の出力のみ。

---

## 0. 重要な前提変化（owner/head 要確認・1論点）

発注書の受入基準は **総記事 302,130 / 既存接合 299,957 / orphan 2,173** の宇宙で書かれている。
しかし現在の labeled 入力は **333,206 件**（`…/labeled_v0.2.1/article_meta_labeled.jsonl`, 2026-06-26 15:50 更新、
git `1cd8eb1 D1文献 長尾取得後の最終確定 333,206` に対応）に拡大している。
+31,076 件の **長尾(long-tail)取得分** が新規に入り、その大半が **authority 未登録の新規誌** で orphan 化している。

→ したがって「被覆 ≥ 99.6%」は **旧 302,130 宇宙での基準** であり、現在の 333,206 宇宙へそのまま適用すると
スコープ外の長尾誌（本ORCHの対象=旧2,173 orphan ではない）まで巻き込むため、**そのままでは満たせない**。
本報告は (a) 本ORCHが対象とした旧 orphan の解消結果 と (b) 現宇宙での全体数値 を分けて提示する。
**判断を仰ぐ点**: 長尾 32,114 orphan の解消は新規 authority 整備が必要で本ORCHの範囲外 → 後続ORCH起票が妥当か。

---

## 1. 数値（同一入力 333,206 件で比較・決定的再現可能）

| 指標 | TRUE baseline (旧code + authority v14) | v0.2 (本ORCH: 新code + authority v15) | 差分 |
|---|---:|---:|---:|
| joined | 299,596 | **301,092** | **+1,496** |
| orphan | 33,610 | 32,114 | −1,496 |
| coverage | 89.91% | 90.36% | +0.45pt |
| orphan: authority_unresolved | 32,557 | 32,114 | −443 |
| orphan: **tsuukan_unavailable** | 1,053 | **0** | **−1,053** |
| article_collision | 0 | **0** | 維持 |
| 百選(別冊ジュリスト) collision | 0 | **0** | 維持 |
| issue_id 混在 | 2 | 2 | 維持（後述・本ORCH起因ではない） |

- 受入検査（`tools/periodical/audit_article_join.py`）:
  `[PASS] article_collision=0` / `[PASS] bessatsu_jurist_collision=0` / `[PASS] orphan_all_classified` /
  `[FAIL] coverage>=95%`（90.36% — §0 の長尾拡大が原因。本ORCH変更による後退ではない）。
- issue_id 混在 2 件は `issn:1342-1301#4,#5`（日本国際経済法学会年報 / 経済法学会年報、ISSN共有）で
  **v0.1 から不変の既存 authority 課題**。本ORCHの変更（誌統合・split・isbn番号化）は新たな混在を **0 件** しか生んでいない。

## 2. 本ORCH対象（旧 2,173 orphan / 20誌）の解消結果

| 誌 | 旧orphan | 処理 | v0.2 結果 |
|---|---:|---|---|
| 月刊債権管理 | 682 | **NCID取得**(CiNii Books `AN10034403`=債権管理:月刊民事法情報号外/民事法情報センター)。誤マージISSN 1348-8953破棄 | joined 682 / orphan 0 |
| 民事法研究 | 367 | **isbn_per_issue 番号化**(季刊・民事法研究21〜=判タ増刊656〜) | joined 367 / orphan 0 |
| 法学セミナー別冊付録,p | 116 | **本誌統合**(ISSN 0439-3295, ym_terminal) | joined 116 / orphan 0 |
| TKC税研時報 | 103 | **NCID取得**(`AN1009402X`, vol-issue) | joined 103 / orphan 0 |
| 商法研究 | 77 | **isbn_per_issue 番号化**(有斐閣 商法研究24等) | joined 104 / orphan 0 |
| 商事法務 | 50 | **collision_split 分離**(掲載誌先頭で 旬刊/国際/資料版 商事法務へ振分) | orphan 0（実在誌へ吸収） |
| 建築関係法令の研究 | 44 | **NCID取得**(`BN03460454`) | joined 44 / orphan 0 |
| 現代刑事法 | 43 | **isbn_per_issue**(『植村立郎判事退官記念論文集…』book_key + 誌号フォールバック) | joined 48 / orphan 0 |
| 立命館大学法学部ニューズレター | 37 | **NCID取得**(`AN10486595`) | joined 37 / orphan 0 |
| 保安と外勤 | 30 | **NCID取得**(`AN0004113X`) | joined 30 / orphan 0 |
| 法学論集(駒沢大学) | 28 | **collision_split解除**(駒沢NCID基底 `AN00224683` direct) | joined 28 / orphan 0 |
| タイム | 25 | **collision_split**(判例タイムズ分のみ吸収。他=セキュリティ/富士タイムズ等は別誌で受容) | orphan 24（判タ分のみ解消） |
| 明治大学法科大学院ジェンダー法センター年報 | 21 | **NCID取得**(`AA1291592X`) | joined 21 / orphan 0 |
| 訟務月報 | 14 | **NCID取得**(`AN00327981` 法務省、ISSN無, vol-issue) | joined 14 / orphan 0 |
| 法学セミナー増刊,p | 7 | **本誌統合**(ISSN 0439-3295, ym_terminal) | joined 7 / orphan 0 |
| 永世中立 | 4 | NDL serial有/CiNii Books clean NCID無 → **受容(authority_unresolved)** | orphan 4 |
| 軍事民論 | 3 | **NCID取得**(`AN00020468`) | joined 3 / orphan 0 |
| 東洋法学会会報 | 2 | NDL/CiNii **該当なし → 受容**(記録) | orphan 2 |
| **判例研究** | 513 | **触らない原則厳守**。機関混在(金融判例研究=金融法務事情所収 等)につき `collision_split` に再分類し orphan 受容（join せず） | orphan 570 |
| **法学研究** | 7 | **触らない原則厳守**(4機関混在、既 collision_split) | orphan 7 |

→ 旧 2,173 orphan のうち、**意図的保留(判例研究 570 / 法学研究 7)と少数受容(タイム24 / 永世中立4 / 東洋法学会会報2)= 計607** を除き、**約1,566件を解消**。tsuukan_unavailable は **0** に到達（基準4「≤300」を充足）。

## 3. 変更内容

### 3.1 authority 増分 `d1_journal_issn_authority_ALL_resolved_v15.csv`（v14→v15, 12行のみ変更, 既存解決行は不変）
生成: `tools/periodical/build_authority_v15.py`（再現可能・差分が自己文書化）。
- NCID 追記（NDL Search SRU + CiNii Books OpenSearch の serial 照合, 2026-06-27 調査）: 月刊債権管理 / TKC税研時報 / 訟務月報 / 立命館大学法学部ニューズレター / 保安と外勤 / 明治大学法科大学院ジェンダー法センター年報 / 建築関係法令の研究 / 軍事民論。
- status 是正: 法学論集(駒沢大学) `collision_split→ndl_unique` / 法学セミナー別冊付録,p・増刊,p `seed_bessatsu_jurist→seed_verified`。
- 誤マージ防止の再分類: 判例研究 `seed_isbn_per_issue→collision_split`（join せず、reason を tsuukan_unavailable→authority_unresolved へ正しく分類）。
- external_share は一切付与せず（owner gate 不変）。NCID は内部 join キーとして使用、canonical/外部公開昇格は別途 owner GO。

### 3.2 join dry-run 改修 `tools/periodical/run_article_join_dryrun.py`（追加のみ・既存接合不変）
1. **isbn_per_issue 番号フォールバック**: 『…』書誌が無い isbn/別冊系で、誌自身の号数を per-issue キー(`isbn:{誌}#{号}`)に採用。`book_key` がある既存接合は不変、orphan のみ救済（民事法研究/商法研究/現代刑事法）。
2. **SPLIT_MAP**: collision_split された canonical(商事法務/タイム)を掲載誌先頭表記で実在誌へ振分。振分先は authority 解決済のみ、既存マージは不変、orphan のみ救済。

決定的検証として TRUE baseline（git HEAD の旧コード + v14）と同一入力で比較し、上記改修が既存接合を後退させず（joined 単調増加 +1,496）、article_collision を 0 のまま維持することを確認済み。

## 4. 成果物
- `artifacts/periodical/d1_journal_issn_authority_ALL_resolved_v15.csv`（authority 増分）
- `artifacts/periodical/article_join_summary_v0.2.json`（dry-run サマリ）
- `artifacts/periodical/article_join_dryrun_v0.2.audit.json`（受入検査結果）
- `tools/periodical/build_authority_v15.py`（新規）, `tools/periodical/run_article_join_dryrun.py`（改修）
- `artifacts/periodical/ORCH-L4-COVERAGE-LIFT_run-report_20260627.md`（本報告）
- ※ `article_join_dryrun_v0.2.csv`（約79MB）は .gitignore 対象（v0.1同様）。Mac ローカル正本に存在。

## 5. head への申し送り（受入監査の観点・L1/L3/L7）
- 決定的基準は満たす: **article_collision=0 / 百選collision=0 / tsuukan_unavailable=0 / orphan全分類済 / 旧スコープ約1,566件解消**。
- 唯一の FAIL「coverage≥95(99.6)%」は **§0 のデータ拡大(302,130→333,206)が原因**で、本ORCH変更による後退ではない（同一入力比較で joined は +1,496）。基準値は旧宇宙のもの。
- 意味監査の論点（別 family 推奨）: NCID 同定の妥当性（特に 月刊債権管理=AN10034403 / 建築関係法令の研究=BN03460454 は複数候補から選択）、法学セミナー別冊付録/増刊の本誌 ym_terminal 統合の意味的妥当性。
- **後続提案(1入力で可)**: 長尾 32,114 orphan（企業会計1941 / Profession Journal1917 / 市民と法1852 …）は新規 authority 整備が必要。本ORCHのスコープ外。後続 ORCH-L4-LONGTAIL を起票するか否か、owner/head 判断を仰ぐ。
