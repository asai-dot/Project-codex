# ORCH-L4-COVERAGE-LIFT — L4記事接合 被覆引き上げ（全orphan 当たれるだけ全部）

```yaml
order: ORCH-L4-COVERAGE-LIFT
from: Cloud Code Web (codex, head)
to: Worker Claude Code（記事接合再実行・誌調査の実行担当）
priority: 高
read-only: 既存 article_id は不変、新規が乗るだけ。authority に追加するだけで既存status不変。
ref: article_join_summary_v0.1.json / article_join_dryrun_v0.1.audit.json / DD-PERIODICAL-002
scope: owner指示 2026-06-26「20と言わず全部やれ」→ orphan 2,173件 全件を対象
```

## 背景
L4記事接合(99.28%)の orphan 2,173件:
- **tsuukan_unavailable 1,123件**（通巻算出不能）= 主戦場。通巻規則/isbn化/表記揺れ統合で構造的に解消可能。
- **authority_unresolved 1,050件**（authorityで未解決）= NDL/CiNiiで再当たり、取れたら接合可。取れなければ受容。
本ORCHは「authority無傷で既存99.28%を壊さず、上に積むだけ」。

## スコープ（全件）
**orphan 全2,173件**を以下のフローで一巡する。誌単位で機械的にループ。

**触らない原則（誤マージ防止・厳守）**:
- **判例研究**(513) / **法学研究**(7) = collision_split で機関混在。これらは触らず orphan受容。
  → 1,653件 が実質処理対象。

## ワーカーCCがやること（誌単位ループ）
```
for 誌 in (article_join_summary_v0.1.json の orphan_by_journal 全件; collision_split除く):
  1. authority の現状確認(status/key)。
  2. NDL/CiNii で誌名検索:
     - 単一ISSN/NCID取得 → authority に追記(seed_verified or ndl_unique)→ tsuukan_crosswalk 確認
     - 通巻が直接利用可 → tsuukan_rule=direct
     - 年月のみ → tsuukan_rule=ym_terminal
     - 増刊/書籍シリーズ → isbn_per_issue
     - 本誌の表記揺れ(別冊付録/増刊の語尾差等) → 本誌へ統合
     - 取得不能 → authority_unresolved のまま受容(記録)
  3. 通巻算出規則 (formula/crosswalk) が必要なら最小限の追記。
```
1次調査(head)で次手が判明している誌（必ずこの推奨処理を採る）:
| 誌 | orphan | 推奨処理 |
|---|---:|---|
| 民事法研究 | 367 | **isbn_per_issue**（判タ増刊No.656〜シリーズ） |
| 法学セミナー別冊付録,p | 116 | **法学セミナー本体(ISSN 0439-3295)へ統合**（表記揺れ・銀行法務パターン） |
| 法学セミナー増刊,p | 7 | **法学セミナー本体へ統合**（同上） |
| 商法研究 | 77 | **isbn_per_issue**（所収p形式） |
| 商事法務 | 50 | **collision_split**（国際商事 vs 旬刊商事 混在の疑い→分離） |
| タイム | 25 | **collision_split**（複数誌混在の疑い→分離） |
| 現代刑事法 | 43 | **NDLで自誌ISSN/NCID取得→direct通巻**（1994創刊・休刊、後継=刑事法ジャーナルAA12066555は別誌） |
| 訟務月報 | 14 | **NDL: ISSN/NCID取得→direct通巻**（法務省公的刊行物） |
| その他17件以下の細切れ含む全件 | 残 | NDL/CiNii検索 → 取れれば取り込み、取れなければ受容 |

## 受入基準（再実行後）
1. **接合被覆 ≥ 99.6%**（299,957 → 301,000+）。
2. **article_collision = 0** 維持。
3. **百選 issue_id 衝突 = 0** 維持（D2のisbn化を新規追加で巻き込まない）。
4. tsuukan_unavailable は ≤ 300 まで削減。
5. authority_unresolved は誌レベルで再調査済の証拠（探したが取れなかった記録）を残す。

## 実行手順
1. `cd /Users/yuta/Project-codex/.claude/worktrees/...`（適切なworktreeで実行、無ければ作成）。
   ※全量分類が `.claude/worktrees/classify-full` で背景実行中。GPU/CPUを奪わないよう注意。
2. `git pull --rebase`（**force-push禁止厳守**）。
3. 上記ループを誌単位で実施 → authority v15(または末尾増分)を出力。
4. `tools/periodical/run_article_join_dryrun.py` を再実行 → 新 article_join_dryrun_v0.2.csv / summary_v0.2.json。
5. `tools/periodical/audit_article_join.py` で受入検査 → PASS確認。
6. commit→push（force-push禁止、`git pull --rebase` 後に通常push）。

## 並行（Cloud Web=head 側）
- 別冊ジュリスト D2 反映（authority v14のBN01263667 58誌を isbn_per_issue 化）。コミット1本。
- ワーカー出力の受入監査を即実行し報告。

## 明示的に「やらない」こと（手戻り回避）
- **判例研究 513 / 法学研究 7** は触らない。
- v14 と v2_sru/v3_ratified 系の統合は本ORCHのスコープ外。
- 全量分類(classify-full)が走っている間はOllama/GPU負荷を増やさない（軽いNDL/CiNii検索のみで進める）。
