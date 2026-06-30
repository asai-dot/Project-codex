# L5 通称衝突 分離設計 v0.1 — DD-L5-LITIGATION-001 §6 held(通称衝突) の解法

- 起案: head (Claude Code) / 2026-07-01 / 種別: DESIGN（read-only。当事者署名取込・canonical は owner GO）
- 親: `DD-L5-LITIGATION-001`（通称→事件→判決 二層）の **held=通称衝突33** を分離する解法。
- 契機: LITIGATION 分析で「同通称→複数 litigation」が **subject差で機械分離可 vs 当事者署名要** に二分されると実証。

---

## 0. 一行要約

通称衝突（日産自動車事件＝別個3事件 等）は二段で分ける: **(段1) formal事件名の法分野(subject)が割れるものは read-only で分離**、
**(段2) 同分野で割れないものは当事者署名(判決本文/curated索引＝owner権威)が必須**。read-only は段1まで、段2は owner GO。

## 1. 実データ（read-only・本セッション分析）

衝突33通称の分離可能性（formal事件名の subject 分類）:

| 分離手段 | 件数 | 例 |
|---|---|---|
| **段1: subject差（read-only可）** | **12** | 武富士事件(租税/不法行為) / 高山労基署長事件(労働/行政) / 国立大学法人賃下げ訴訟(行政/労働) / オリエンタルモーター(不法行為/労働) |
| 段2: 同subject→当事者署名要 | 11 | 日産自動車事件(労働×3) / 離婚訴訟(家事×2) / マンナ運輸(労働×2) / みちのく銀行(労働×2) |
| 段2: subject不明→当事者署名要 | 10 | 共有物分割訴訟 / 固有必要的共同訴訟（他/他）|

※ 段1の一部（国賠事件 等、ほぼ同subject）は実質段2。**確実な段1は法分野が明確に割れる ~6-8 件**（過大評価しない）。

## 2. 二段分離設計

### 段1（read-only・head 可）— subject 照合
- litigation 候補の各 judgment を **formal事件名の法分野**（労働/独禁/租税/知財/会社/不法行為/行政/家事/倒産/刑事）に分類。
- 衝突通称が **≥2 の明確に異なる法分野** を含む → 各 litigation を法分野で分離。
- 評釈article は **掲載誌＋タイトル主題**（労働判例→労働 litigation、商事法務→会社 等）で対応 litigation に割当。
- tier: 法分野が一意に割れる＝T2 candidate。割れ方が弱い＝held。

### 段2（owner 権威要）— 当事者署名
- 同分野の衝突（日産自動車×3労働、離婚×2家事）は **subject では分けられない**。唯一の分離子 = **当事者(原告/被告)**。
- 当事者署名の入手元（**いずれも owner GO**）:
  1. **判決本文の当事者欄**（hanrei/ body・HIGH-HOLD・OCR-conf gate=PERIODICAL-003 を通す）。
  2. **curated 事件通称索引**（判例百選/重要判例解説の通称↔当事者・owner 提供）。
  3. 評釈本文の当事者言及（本文層・DD-PERIODICAL-002・owner GO）。
- 段2は read-only string では届かない＝**owner 領域**（追加権威の取込判断）。

## 3. 出力 / tiering

- `l5_collision_separation_v0.1.csv`: 33通称 × subjects × separation_verdict。
- T2(段1分離可) → review queue へ昇格候補（owner 確認）。
- held(段2) → **owner 権威待ち queue**（当事者署名が来るまで held・silent に流さない＝PERIODICAL-003 §5 整合）。

## 4. 求める判定（GPT 監査用・任意）

1. 二段（subject→当事者署名）分離は妥当か。段1 subject 照合の誤分離リスクは。
2. 段2 を owner 権威（判決本文当事者/curated索引）に委ねる切り分けは正しいか。read-only で更にできることは。

## 5. HOLD

当事者署名（判決本文/curated索引）の取込 / litigation 分離の canonical 化 / edge accepted は owner GO。
本設計は **read-only（段1 subject 分離 ＋ 段2 の権威要件定義）まで**。
