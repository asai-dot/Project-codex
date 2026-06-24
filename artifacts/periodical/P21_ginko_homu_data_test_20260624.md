# P21: ローカルちゃん発注 — 銀行法務 vs 銀行法務21 を実記事データで判定

```yaml
artifact: P21_ginko_homu_data_test
generated_at: 2026-06-24 JST
reason: owner指摘「記事の中身を突き合わせれば同じ雑誌か別雑誌か分かる。3000件のヒントがある」
blocker: クラウドVMには誌レベル集計(件数)しか無い。記事レベル(巻号/年/タイトル)はMac側 article_meta_labeled.jsonl のみ。
        Supabase issue_stage(2847行)にも銀行法務は0件。→ この判定はデータが在るローカルちゃんでしか実行できない。
gate: read-only分析のみ。
```

## 1. 問い
D1文献編で `journal_canonical` が「銀行法務」(3,827記事) と「銀行法務21」(3,000記事) に分裂。
同一シリアル(ISSN 1341-1179)か、別物か。**件数差(3,827>3,000)の正体は何か。**

## 2. 書誌事実（確定済み・前提）
- 手形研究(ISSN 0494-9692, 経済法令研究会, vol1=1957 〜 vol38=1994) → **1995年に改題** → 銀行法務21(ISSN 1341-1179, vol39=通巻501〜)
- NDL/CiNiiの継続前誌は「手形研究」。**独立した「銀行法務」誌は書誌上存在しない。**
- よって「銀行法務」ラベルは (a)「銀行法務21」の"21"省略表記 か (b) 手形研究era混入 のいずれか。データで判別する。

## 3. ローカルちゃんが実行する判定（article_meta_labeled.jsonl）
2バケツの pub_year / vol(巻) 分布を出す。擬似コード:
```python
import json, collections
buckets={'銀行法務':collections.Counter(),'銀行法務21':collections.Counter()}
volrange=collections.defaultdict(list)
for line in open('build/labeled_v0.2.1/article_meta_labeled.jsonl'):
    r=json.loads(line); j=r.get('journal_canonical')
    if j in buckets:
        y=r.get('pub_year') or r.get('issue_year') or r.get('year')
        v=r.get('vol') or r.get('volume')
        buckets[j][y]+=1
        if v: volrange[j].append(str(v))
for j,c in buckets.items():
    yrs=[int(y) for y in c if str(y).isdigit()]
    print(j, 'n=',sum(c.values()), 'year',min(yrs,default='-'),'..',max(yrs,default='-'),
          'vol', sorted(set(volrange[j]))[:5],'..',sorted(set(volrange[j]))[-3:])
# 年ヒストグラム(1990-2000の境界を重点表示)も出す
```

## 4. 判定ルール（結論の出し方）
| 観測 | 結論 | 是正アクション |
|---|---|---|
| 「銀行法務」が全て **1995+ / vol39+** | 銀行法務21の"21"省略表記＝**同一シリアル** | 銀行法務→1341-1179へ統合確定。issue_id衝突無し(通巻連続) |
| 「銀行法務」に **1994以前 / vol≤38** が含まれる | その分は **手形研究**(0494-9692) | 年(<=1994)で分割: ≤1994→0494-9692, ≥1995→1341-1179 |
| 「銀行法務」と「銀行法務21」の **巻号が同年で重複** | 同一号の二重ラベル | 同一キーに正規化(重複排除) |

件数差(3,827>3,000)の最有力仮説: 「銀行法務」バケツに **改題前(手形研究era/1994以前)+省略表記** が混在し、「銀行法務21」は明示"21"表記のみ。→ 年分布を見れば一発。

## 5. 判定結果（2026-06-25 ローカルちゃんがMac記事データで実検証 → 確定）
**結論: 銀行法務 = 銀行法務21 の同一誌（ISSN 1341-1179）。統合確定。**
- 「銀行法務」3,827件の内訳（article_meta実検証）:
  - **3,728件(97.4%)** = 銀行法務21各号の記事。掲載誌文字列「銀行法務２１70-3」(スペース無し)をD1抽出が `銀行法務` と切った**表記揺れ**。
  - 99件 = 「銀行法務21 別冊N」書籍シリーズ。
- 件数差(3,827>3,000)の正体 = **掲載誌文字列のスペース有無による抽出差**（別誌でも年代差でもない）。
- クラウド側の事前仮説「pre-1995/手形研究era混入」は**外れ**。記事は全て改題後。
- → v4.csv の「銀行法務」を **seed_verified ISSN 1341-1179** に格上げ（source=d1_article_data_test）。held解除。
- ISSN衝突回帰検査(P19手法)再実行: 1341-1179 は data-verified の正しいマージ。残9衝突は全て同一誌の表記揺れで別誌マージ0件。被覆 95.38% 維持。
- 軽微フォロー: 99件の別冊シリーズは将来 isbn_per_issue 化可能（実用上は同一ISSNで可）。

## 6. 分担の教訓（重複解消の実証）
本件は「解決=Mac / 監査=クラウド」分担が機能した例:
- クラウドは記事データを持たず書誌推論しかできず、結論を誤りかけた（held止まり）。
- **記事レベルの突き合わせ(3,000+のヒント)はMac側でしか不可能**＝ローカルちゃんの専管。
- クラウドの価値は衝突検出・検証seed override・統合後の回帰監査に集中すべき（誌の二重解決はしない）。
