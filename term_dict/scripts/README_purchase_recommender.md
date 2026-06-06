# 購入レコメンド（アイデアD / Fork 3）— `purchase_recommender.py`

未所蔵で**詳細TOC**を持つ書籍（`defer_new` 群 ≈ 616 冊）を、事務所の**現業テーマ
との関連度**でランキングして購入候補を提案するスタンドアロン・ツール。あわせて
**「すでに持っている本を2度買わない」ための重複アラート**を出力する。

`gap_recommender.py`（辞書ギャップ推薦）と同じ流儀で、Box 同期されたローカル
データを直読みする。**接合不要・単体成立**。

---

## 1. 何を解くか

| | |
|---|---|
| 入力A | **所蔵カタログ** `app/data/books.json`（事務所SoT, 約6,400冊） |
| 入力B | **候補プール** `archive/data_imports/bencom_clean.json`（弁護士ドットコムライブラリー掲載書, TOC付き 約3,800冊） |
| 入力C | `term_dict/analysis/book_coverage_by_domain.json`（候補TOCをterm_dictへ照合した `primary_domain` / `total_toc`） |
| 入力D | `term_dict/analysis/bencom_tag_domain_mapping.json`（tag→`domain_l1`） |
| 出力 | Top-N 購入提案（txt / json / csv）＋ 2度買い防止アラート（json） |

`defer_new` =「**未所蔵**（所蔵カタログに無い）× **詳細TOC有り**（TOCノード数 ≥
`min_toc_nodes`）」の候補集合。明示リスト
`term_dict/analysis/defer_new_ids.json` があればそれを優先採用し、無ければ
上記条件で動的に算出する。

---

## 2. スコアリング（番頭目検で上位＝現業テーマとなるよう設計）

### ① 所蔵の主題分布 × 候補のTOC主題

- **所蔵の主題分布** `demand_share[domain]`
  所蔵カタログ各冊の `genre`（`classify_genre` / `NDC_GENRE_MAP` 由来）を
  term_dict の `domain_l1` 軸へ写像（`GENRE_TO_DOMAIN`）。`genre` が無い冊は
  `ndc` を補助に使う（`NDC_PREFIX_TO_DOMAIN`）。ドメイン別の所蔵冊数を正規化
  したものが「現業テーマの強さ」。

- **候補の主題プロファイル** `profile[domain]`
  `book_coverage_by_domain.json` の `primary_domain` と `domain_hits`
  （= `{domain: TOCヒット数}` の実フィールド）、および `tags`→`domain_l1`
  写像から合成し、合計1へ正規化。`unclassified` / `unknown` は除外。

  > 実データ注記: term_dict 照合は疎で（`matched_toc` が小さく、約3,800冊中
  > 1,907冊が `primary_domain=unclassified`）、`domain_hits` だけでは信号が弱い
  > 候補が多い。このため `tags`→`domain` フォールバックが実務上は効く。
  > 候補側の実ドメイン軸は
  > `commercial / civil / administrative / labor / procedure / criminal / ip / tax`
  > （所蔵 `genre` の写像先と一致するよう `GENRE_TO_DOMAIN` を設計済み）。

- **関連度**
  ```
  relevance = Σ_domain ( demand_share[domain] ** weight_power ) * profile[domain]
  ```
  - `weight_power = 1.0`（既定）… **現業テーマ整合**。所蔵が厚いドメインの
    候補ほど高得点（＝「もっと強みを伸ばす」推薦）。
  - `weight_power < 1.0` … 分布が平坦化し、**空白補完(gap-fill)寄り**に振れる。
    薄いドメインの候補の相対評価が上がる（1本のノブで両論を切替）。

### ② 旗艦級（コンメンタール・大系等）への重み

```
flagship_weight = 1 + flagship_alpha * log1p(toc_nodes)
              （×1.25 if 書名/シリーズに旗艦キーワード or toc_nodes>=200）
```
高ノード数＝基幹書（引きやすく長く使う）ほど優遇。`FLAGSHIP_KEYWORDS` =
コンメンタール / 大系 / 注釈 / 注解 / 講座 / 体系 / 全書 / 争点 …。

### 最終スコア

```
raw_score   = relevance * flagship_weight
score(0-100)= 100 * raw_score / max(raw_score)   # 表示用に正規化
```
主題が取れない候補（プロファイル空）は番頭目検の精度を守るため除外する。

---

## 3. 2度買い防止アラート

候補（既定: bencom 全体。任意の買い物リストも可）を所蔵カタログへ突き合わせ、
以下のいずれかが一致したものを「購入不要（所蔵済み）」として列挙する。

- `isbn`（13桁正規化）一致
- `bencomId` 一致（所蔵レコードは bencom 由来IDを保持している）
- 正規化タイトル一致

Top-N 提案表でも、別版/類似タイトルを所蔵していそうな候補には `dup_alert`
注記を付ける（ハード除外はしない＝別版購入の判断は人へ）。

---

## 4. 使い方

stdlib のみ。依存パッケージ無し。

```bash
# 実データ（Box同期）に対して全出力を生成
python purchase_recommender.py \
    --base "C:/Users/Asai/Box/浅井/claude/事務所内本棚DX化計画" \
    --top-n 100

# ベースは環境変数でも指定可
export BOOKDX_BASE="/path/to/事務所内本棚DX化計画"
python purchase_recommender.py --print          # 標準出力にレポート

# 空白補完寄りで再ランキング
python purchase_recommender.py --weight-power 0.3

# 詳細TOCの閾値を調整（defer_new の母数が変わる）
python purchase_recommender.py --min-toc-nodes 60
```

主なオプション:

| オプション | 既定 | 説明 |
|---|---|---|
| `--base` | Box 同期パス | 計画フォルダのルート |
| `--top-n` | 100 | 提案件数 |
| `--min-toc-nodes` | 40 | `defer_new` 判定の詳細TOC下限 |
| `--weight-power` | 1.0 | 1.0=現業整合 / <1.0=空白補完 |
| `--flagship-alpha` | 0.20 | 旗艦重みの強さ |
| `--present-only` | off | 所蔵分布を物理/スキャン所持本のみで集計 |
| `--print` | off | ファイル出力せず標準出力 |

出力先（`term_dict/output/`）:
`purchase_recommendations.{txt,json,csv}` と `purchase_dedup_alert.json`。

### ライブラリとして

```python
from purchase_recommender import PurchaseRecommender
pr = PurchaseRecommender(base=..., weight_power=1.0)
pr.load()
recs   = pr.recommend(top_n=50)        # list[Recommendation]
alerts = pr.dedup_alert()              # list[DedupHit]
dist   = pr.demand_summary()           # 所蔵の主題分布
```

---

## 5. 検収（acceptance）

> 上位提案が現業テーマと合致（番頭目検でヒット率）。

1. `python purchase_recommender.py --print` で Top-N と「所蔵の主題分布」を出す。
2. 番頭（中森さん等）が上位20〜30件を目検し、「今の案件で実際に引きたい本か」を
   ○×。ヒット率を記録。
3. 外れが多いドメインがあれば `GENRE_TO_DOMAIN` / `bencom_tag_domain_mapping`
   の写像を補正、または `weight_power` を調整して再実行。
4. 旗艦級の出方が強すぎ/弱すぎる場合は `--flagship-alpha` で調整。

> `GENRE_TO_DOMAIN` は2系統の語彙の和集合をカバー: `booklib.py` の
> `GENRE_RULES`（キーワード分類「〜実務/〜法務」）と
> `app/data/ndc_genre_mapping.json`（NDCバックフィル「民法/刑法/民事訴訟法」等。
> 2026-05-13 backfill で所蔵に付与）。レポート冒頭に **未写像 genre** を出すので、
> 写像漏れがあればそこを見て `GENRE_TO_DOMAIN` に追記すればよい。

---

## 6. テスト

Box/実データ無しで動く合成テストを同梱。

```bash
python tests/test_purchase_recommender.py     # もしくは: pytest tests/
```

検証内容: 所蔵主題分布の生成（genre/ndc）、`defer_new` 選定、現業テーマ整合
ランキング、旗艦重み、`weight_power` による gap-fill シフト、2度買いアラート
（ISBN/bencomId/タイトル一致・任意の買い物リスト）。

---

## 7. 想定スキーマ（参照）

**所蔵 `books.json`**（`booklib.py` 由来）: `id, isbn, title, author, publisher,
genre(str|list), ndc, status{physical,cut,scanned}, hasToc, bencomId, shelfLabel, …`

**候補 `bencom_clean.json`**: `id, isbn, title, author, publisher, tags(list),
toc(list[{t, children?}]), bencomUrl, …`

ローダはフィールド欠落・表記揺れに寛容（ISBN正規化、TOCの入れ子キー
`children/c/sub/items/nodes`、`genre` の str/list 両対応など）。
