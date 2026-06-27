# ORCH-L4-COVERAGE-LIFT — L4記事接合 被覆引き上げ（tsuukan_unavailable 1,123件の解消）

```yaml
order: ORCH-L4-COVERAGE-LIFT
from: Cloud Code Web (codex, head)
to: Mac Cloud Code（誌解決スキル保持・記事接合再実行可能な実行担当）
priority: 高（手戻り少・精度効率最高・後段L5の対象を増やす）
read-only: 既存 article_id は不変、新規が乗るだけ。
ref: article_join_summary_v0.1.json / article_join_dryrun_v0.1.audit.json / DD-PERIODICAL-002
```

## 背景
L4記事接合(99.28%)の orphan 2,173件のうち **1,123件 = tsuukan_unavailable**（通巻算出不能）。
1,050件の authority_unresolved（NDL未収録・廃刊極小誌）は受容済だが、tsuukan_unavailable は
**通巻規則(tsuukan_crosswalk / formula / isbn_per_issue) を増やすだけで解消**できる。
authority は触らない＝既存99.28%を壊さず、上に積むだけ。

## 標的誌（orphan 上位5、計 ≈ 1,076件＝tsuukan_unavailable の 96%）
| 誌 | orphan | 1次調査(head) | 推奨処理 |
|---|---:|---|---|
| **判例研究** | 513 | 既知の collision_split(4機関混在: 北大/早大/民事法情報センター/関学等) | collision_split のまま orphan受容。改善対象から除外（誤マージリスクの方が大）|
| **民事法研究** | 367 | **判例タイムズ増刊号 No.656〜のシリーズ書籍**（独立誌でなく増刊号） | 既に authority で seed_bessatsu_jurist 扱いの可能性。要確認→ **isbn_per_issue へ寄せる** |
| **法学セミナー別冊付録,p** | 116 | 法学セミナー本体の別冊付録（誌名抽出のスペース無し変種） | **法学セミナー(ISSN 0439-3295)と統合**（銀行法務=銀行法務21 と同じ表記揺れパターン）|
| **TKC税研時報** | 103 | TKC発行 (NCID取得 P25で試みたが要再調査) | NDL/CiNii追加調査 → ndl_unique or 認定保留 |
| **現代刑事法** | 43 | **1994創刊・月刊・休刊（後継=刑事法ジャーナル 2005-, NCID AA12066555）** | NDL で 現代刑事法のISSN/NCIDを取得→ direct通巻 で接合 |
| 商法研究 | 77 | 増刊系の可能性 | 民事法研究と同パターンか要確認 |
| **計** | ≈1,219 | | |

## 受入基準（再実行後）
1. article_join 再実行で **tsuukan_unavailable ≤ 300**（73%以上削減）。
2. 接合被覆 ≥ **99.6%**（299,957 → 301,000+）。
3. **article_collision = 0** 維持（採番衝突を新たに作らない）。
4. **百選 issue_id 衝突 = 0** 維持（D2のisbn化を新規追加に巻き込まない）。

## 並行（Cloud Web=head が即やる軽い片付け）
- **別冊ジュリスト D2 反映**: authority v14 で BN01263667 の58誌は seed_bessatsu_jurist のまま。
  isbn_per_issue へ書き換え（接合層で既に解消済だが authority も整合させる）。コミット1本。
- 上記の調査結果(現代刑事法のISSN/NCID等)が出たら都度反映。

## 後段
被覆引き上げ後 → ★分類完走待ち → 全量分類監査 → L5(判例評釈→判例リンク) 発注。
順番に下流へ波及するので、L4を厚くしてから L5 に行く方が手戻りない。

## 明示的に「やらない」こと（手戻り回避）
- 判例研究 513件は **触らない**（collision_split は機関混在で誤マージリスク高、orphan受容のまま）。
- authority unresolved 1,050件は受容（月刊債権管理682含む。NDL未収録・廃刊極小誌）。
- v14 と v2_sru/v3_ratified 系の統合は本ORCHのスコープ外（記事接合への即影響なし、別途）。
