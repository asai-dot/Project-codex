# ORCH-LOCAL-ARTICLE-TYPE — ローカルちゃん(QEN/Ollama)発注: 記事種別 粗分類（約30万件）

```yaml
order: ORCH-LOCAL-ARTICLE-TYPE
from: Cloud Code Web (codex, head)
to: ローカルちゃん (QEN / Ollama) ※軽量・大量・ローカル完結。チャンク分割して投入。
authority: read-only 派生生成。canonical/DB/外部公開は含まない。
input: artifacts/periodical/article_join_dryrun_v0.1.csv（article_id, title 列）≈302k行
why_local: 1件=タイトル1本→1ラベルで軽い。30万件＝APIなしのローカルが最適。誤りはhead監査で吸収。
```

## タスク
各記事タイトルを次の**種別**に1つ分類（曖昧は "その他" に倒す。精度より網羅、判定はhead監査）:
```
判例評釈 / 論説・論文 / 解説 / 立法・改正解説 / 座談会・対談 / 判例紹介 / 書評 / 資料 / 連載・コラム / その他
```

## 切り分けて投入（dispatch_local.sh, head/Mac側が実行）
- `tools/run_local_classify.sh` が input を **400行/チャンク**に分割し、各チャンクを
  `dispatch_local.sh` で QEN に投入（プロンプト固定）。出力を1本に結合。
- 出力: `artifacts/periodical/article_type_local_v0.1.csv`（列: `article_id, type, source=qen`）。

## 固定プロンプト（チャンクごと）
「次の各行は タブ区切りで id<TAB>タイトル。各行をちょうど1つの種別に分類し、
`id<TAB>種別` だけを1行ずつ返せ。種別は次のいずれかの語そのもの: 判例評釈,論説・論文,解説,
立法・改正解説,座談会・対談,判例紹介,書評,資料,連載・コラム,その他。迷ったら その他。説明文は出力しない。」

## head 受入監査（codex が独立実行）
- **分布のサニティ**: 各種別の件数。判例評釈・論説が一定割合を占めるはず。極端な偏り=プロンプト/モデル不調。
- **正規表現クロスチェック**: タイトルに「評釈」「最判」「最決」「〇〇判決」を含む→判例評釈に分類されているか抜取。
  「座談会」「対談」→座談会・対談、「書評」→書評、等。乖離率を測る。
- **サンプル目視**: 各種別から各20件。
- 合格基準: クロスチェック一致率 ≥ 85%、未分類(空/規格外ラベル)=0。未達ならプロンプト調整して再投入。

## 後続
判例評釈サブセット（本分類で判例評釈になった記事）に対し、**第2段=評釈対象判例の抽出**（court/date/事件）を
別発注（ORCH-LOCAL-HANREI-TARGET）。これが L5(評釈→判例リンク)へ直結。
