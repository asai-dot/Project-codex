# ORCH-L4-COVERAGE-LIFT — L4記事接合 被覆引き上げ（orphan上位20誌）

```yaml
order: ORCH-L4-COVERAGE-LIFT
from: Cloud Code Web (codex, head)
to: Mac Cloud Code（誌解決スキル保持・記事接合再実行可能な実行担当）
priority: 高（手戻り少・精度効率最高・後段L5の対象を増やす）
read-only: 既存 article_id は不変、新規が乗るだけ。
ref: article_join_summary_v0.1.json / article_join_dryrun_v0.1.audit.json / DD-PERIODICAL-002
scope: orphan上位20誌（owner指示 2026-06-26）
```

## 背景
L4記事接合(99.28%)の orphan 2,173件のうち **1,123件 = tsuukan_unavailable**（通巻算出不能）。
1,050件の authority_unresolved（NDL未収録・廃刊極小誌）は受容済だが、tsuukan_unavailable は
**通巻規則(tsuukan_crosswalk / formula / isbn_per_issue) と表記揺れ統合 を増やすだけで解消**できる。
authority は触らない＝既存99.28%を壊さず、上に積むだけ。

## 標的: orphan 上位20誌（全 2,193件 = orphan 全体の 100% 弱）
| # | 誌 | orphan | 1次調査(head) | 推奨処理 |
|---|---|---:|---|---|
| 1 | **判例研究** | 513 | collision_split（4機関混在: 北大/早大/民事法情報C/関学） | **触らない**＝orphan受容（誤マージリスク>>得） |
| 2 | **民事法研究** | 367 | 判例タイムズ増刊号(No.656〜)シリーズ書籍 | **isbn_per_issue へ**（authority 確認の上） |
| 3 | **法学セミナー別冊付録,p** | 116 | 法学セミナー本体の別冊付録（スペース無し変種） | **法学セミナー(ISSN 0439-3295)と統合**（銀行法務=銀行法務21パターン） |
| 4 | **TKC税研時報** | 103 | TKC発行・NCID取得未完(P25保留) | NDL/CiNii再調査 → ndl_unique or 認定保留 |
| 5 | **商法研究** | 77 | 増刊・所収「p」形式 | **isbn_per_issue へ** |
| 6 | **商事法務** | 50 | 「国際商事法務」と「旬刊商事法務」混在の可能性 | **collision_split で分離**（誤マージ防止） |
| 7 | **建築関係法令の研究** | 44 | 既知の誤マッチ要因（建築雑誌と区別） | NDL再調査 → ISSN/NCID取得か未解決受容 |
| 8 | **現代刑事法** | 43 | 1994創刊・月刊・休刊（後継=刑事法ジャーナル AA12066555） | **NDL で現代刑事法のISSN/NCID取得→direct通巻** |
| 9 | **立命館大学法学部ニューズレター** | 37 | 立命館発行の学内NL | NDL検索 → ISSN/NCID 取得か受容 |
| 10 | **保安と外勤** | 30 | 警察系雑誌の可能性 | NDL/CiNii 検索 → ISSN/NCID |
| 11 | **法学論集(駒沢大学)** | 28 | 駒沢大学法学論集 | NDL: ISSN/NCID取得 → direct通巻 |
| 12 | **タイム** | 25 | 複数誌混在の可能性（Time誌系/他） | **collision_split で分離** |
| 13 | **明治大学法科大学院ジェンダー法センター年報** | 21 | 年刊紀要 | NDL: ISSN/NCID → direct通巻 or ym_terminal |
| 14 | **訟務月報** | 14 | 法務省 訟務月報（月刊・公的刊行物） | NDL: ISSN/NCID → direct通巻 |
| 15 | **法学セミナー増刊,p** | 7 | 法学セミナー(0439-3295)増刊の表記揺れ | **法学セミナーと統合** or seed_bessatsu |
| 16 | **法学研究** | 7 | 既知の collision_split（4機関混在） | **触らない**＝orphan受容 |
| 17 | **永世中立** | 4 | 極小・特殊誌 | 検索可なら取得、不可なら受容 |
| 18 | **軍事民論** | 3 | 極小・特殊誌 | 検索可なら取得、不可なら受容 |
| 19 | **東洋法学会会報** | 2 | 学会会報 | NDL検索（東洋法学=ISSN 0564-0245 別誌との混同確認） |
| 20 | **(orphan_by_journal top20 末尾)** | 残 | summary.json 参照 | 個別対応 |

**実質対象**: 上記20 − {判例研究513・法学研究7（collision_split受容）} = **1,673件を引き上げ対象**。

## 受入基準（再実行後）
1. **tsuukan_unavailable ≤ 300**（73%以上削減）。
2. **接合被覆 ≥ 99.6%**（299,957 → 301,000+）。
3. **article_collision = 0** 維持（採番衝突を新たに作らない）。
4. **百選 issue_id 衝突 = 0** 維持（D2のisbn化を新規追加に巻き込まない）。
5. authority_unresolved は据置可（長尾受容）。

## 並行（Cloud Web=head が即やる軽い片付け）
- **別冊ジュリスト D2 反映**: authority v14 で BN01263667 の58誌は seed_bessatsu_jurist のまま。
  isbn_per_issue へ書き換え（接合層で既に解消済だが authority も整合させる）。コミット1本。
- 上記の調査結果(現代刑事法のISSN/NCID等)が出たら都度反映。

## 後段
被覆引き上げ後 → ★分類完走待ち → 全量分類監査 → L5(判例評釈→判例リンク) 発注。
順番に下流へ波及するので、L4を厚くしてから L5 に行く方が手戻りない。

## 明示的に「やらない」こと（手戻り回避）
- **判例研究 513 / 法学研究 7** は触らない（collision_split は機関混在で誤マージリスク高、orphan受容のまま）。
- authority unresolved 1,050件は受容（月刊債権管理682含む。NDL未収録・廃刊極小誌）。
- v14 と v2_sru/v3_ratified 系の統合は本ORCHのスコープ外（記事接合への即影響なし、別途）。

## 実行
1. `git pull --rebase`（force-push禁止厳守）。
2. 各誌を NDL/CiNii で調査 → authority に追記 / isbn化 / 表記揺れ統合。
3. tsuukan_crosswalk か isbn_per_issue を整備（既存 crosswalk スキーマに沿う）。
4. `tools/periodical/run_article_join_dryrun.py` を再実行し新 summary を出力。
5. head監査 `tools/periodical/audit_article_join.py` を回し受入基準PASSを確認。
6. PASSなら commit→push、不合格なら主因報告。
