# A2/A3 read-only 分析 — cohort-A 穴埋め対象と edition 正規化

- generated_at_jst: 2026-06-20
- source: Supabase `nixfjmwxmgugiiuqfuym` / `biblio.bib_records`（**SELECT のみ・DB無変更**）
- plan: FORWARD_ROADMAP v0.2 §4-3（A2前段）/ §4-4（A3前段）
- cohort: cohort-A_self_scan = `source='asai-bookshelf'`（6,524）

---

## A2-1. ISBN有 NDL無 = 421件（穴埋め一次対象）

| 指標 | 値 |
|---|---|
| 件数 | 421 |
| ISBN形式が妥当(978/979+13桁) | **421（100%）** |
| pub_year あり | 383（1966〜2026） |
| **2024年以降の新刊** | **53** |
| bib_id 形式 | isbn形 326 / manual 95 |

出版社上位: 有斐閣76 / ぎょうせい43 / 労働新聞社29 / 日本評論社23 / 第一法規22 / 青林書院17 / 金融財政事情研究会17 / 中央経済社13 / 法律文化社12 / 法曹会10。

**含意**
- 421件は ISBN が健全 → **NDLダンプ(F2索引)へのオフライン照合の一次対象**。多くはダンプで引けるはず。
- ただし **2024+ の53件は「ダンプ鮮度の抜け」候補**。ダンプ snapshot 日以降の新刊は no_hit になり得る
  → `no_hit_after_valid_isbn` のうち **新刊起因**を `pub_year >= dump_snapshot_year` で切り分ける（ライブAPI補完の対象）。
  これは v0.2 §8「鮮度バイアス」の実証データ。

## A2-2. ISBN無 NDL無 = 1,101件（難所の正体）

| 指標 | 値 | | 指標 | 値 |
|---|---|---|---|---|
| 件数 | 1,101 | | author(responsibility) | 408（37%） |
| title あり | 1,101（100%） | | pub_year あり | 904（82%） |
| publisher あり | 1,098（99.7%） | | ndc あり | 144（13%） |
| **bib_id=manual** | **1,101（100%）** | | series/volume/ncid | **0** |
| 加除式キーワード | 0 | | 年報/年鑑等シリーズ | 3 |
| 1990年より前 | 6 | | | |

**含意（重要な認識修正）**
- 難所の正体は **古書・加除式ではなく「ISBN未付与の手入力レコード」**（全件 manual、ISBN無）。
- ISBN waterfall は使えない → **title_norm + publisher_norm (+author) の書誌fingerprint で NDLダンプ照合する別レーン**が必要
  （DD-LITID-001 の no-ISBN 経路、第2独立証拠ルール適用）。
- title/publisher はほぼ揃う（fingerprint の素材はある）。author 37%・NDC 13% は補助に留まる。
- **誤統合リスクが高い層**（ISBNという強キーが無い）→ confirmed 化は特に慎重に。candidate 据置。

## A3. edition 値の棚卸し（cohort-A 全体、edition非空=424件）

| パターン | 件数 | 割合 | 扱い |
|---|---|--:|---|
| 「版」を含む | 310 | 73% | **版＝edition の本命**（第N版/改訂版 等） |
| 「刷」を含む | 51 | 12% | **刷＝印刷回次。edition ではない**（同一版の重版）→ 分離必須 |
| 改訂/新版/増補/補訂/全訂/訂 | 63 | 15% | 版の改訂表現。版として扱う（粒度は版） |
| 4桁年/日付様 | 59 | 14% | **日付が edition 欄に混入**（例 `2019/08/25`, `2019年10月`）→ 版でなく刊行日 |
| いずれも非該当 | 22 | 5% | 個別確認 |

（割合は重複あり。例: 「第2刷」は版数字＋刷の両方に該当しうる）

### 正規化ルール草案（DD-LITID-FP へ反映予定）

1. **版(edition_no)**: `第?N版` / 改訂語 → 版粒度のキー。N を整数抽出（一二三…も変換）。
2. **刷(printing_no)**: `第?N刷` → **edition と別フィールド**へ。版同定では**刷を無視**（同一版扱い）。
3. **日付(pub_date_in_edition)**: `YYYY[-/年]MM…` → edition でなく刊行日として退避。pub_year と突合。
4. **改訂表現**: 「改訂版/新版/増補版/全訂版/n訂版」は版の一種として正規化（序数化）。
5. **空(7.6%しか埋まっていない)**: 大半は edition 不明 → NDLダンプの版表示で補完を試みる（F2）。

→ **版 vs 刷の分離が最重要**（51件の刷混入を版として数えると別版に誤って割れる＝監査 must_fix #1 の実害源）。

## 次アクション（read-only・HOLD据置）

- 421: F2索引が出来次第オフライン照合。2024+ 53件は鮮度抜けとして別計上。
- 1,101: no-ISBN fingerprint レーンの照合設計（title+publisher+author、第2独立証拠）。
- A3: 上記正規化ルールを実装ツール（DD-LITID-FP）に落とし、edition/印刷/日付を3分割パースして再集計。

## no-write 保証
SELECT のみ。`biblio`/`bookdx`/canonical/Box 一切変更なし。出力は本 artifact のみ（append-only）。
