# DD-D1TAXO レビュー戻り 確認（2026-06-19 head 整理）

## ① d1taxo pre-apply（short 版・2026-06-17, file 2291346963984）
verdict: **DDD1TAXO_PREAPPLY_CONDITIONAL_GO**

- **Canary preparation は GO**。ただし **actual canary は owner lift ＋ must-fix closure が前提**。
- **canary 前 must-fix は MF-1 だけではない（4件）**:
  1. **normalizer_version review**
  2. **gate version discipline**（`OR REPLACE` 禁止・version 張り直し）
  3. **G23 term_ids の array-type guard**（= 既知の MF-1）
  4. **pending edges を canonical / claim-support から除外**
- HOLD: production write / DDL apply / backfill / embedding / canonical promotion / claim-support / broad batch。

→ head 対応: WO-CODEX-MF1 は #3(G23) と #4(pending除外) を含むが、**#1 normalizer_version / #2 gate version discipline を明示追加**して
  canary lease の must-fix closure に4件すべてを入れる。

## ② ANALYSIS d1taxo 15×16 case-pivot（pass2・2026-06-19, file 2294715758198）
verdict: **SOUND_WITH_NOTES**（independent meaning audit / report-only）

- 収束モデルは妥当: **#15 top-down taxonomy（D1TAXO）** と **#16 bottom-up literature pointillism** は、
  **case オブジェクト＋source非依存の concept layer を介して収束**させる（直接溶接しない）。owner の
  「fully linked → converges through cases」修正は適切。
- **over-claim 是正（重要）**:
  - 43% multi-classification は「多法体系所属」の証明ではない。
  - 複数誌掲載は publication multiplicity であって subject/taxonomy multiplicity ではない。
  - **#16 大分類33 を hidden backbone にしない**（candidate seed vocabulary 止まり・多源裏取り要）。
- データ根拠あり・read-only 開始可: case-pivot join inventory / strong `article_annotates_hanrei`（strong=5,009 cases / 6,948 articles）
  bridge inventory / multi-classification 分布 / source非依存 concept seed 抽出（mint なし）。
- 統合前の穴: #15node×#16cat の実 case_id/source_id join 重なり率 / 機械的タグ由来の multi-class 比率 /
  article_annotates_hanrei の case_id 解決率 / 真に複数法域に属す単一 case 例 / 掲載多重=主題多重 の偽陽性率。
- HOLD: DDL/DB write / integration / concept backbone minting / canonical promotion / claim-support / vendor KOS の backbone 昇格。

## head 判断・次

- **canary は「prep GO・実行は owner lift＋must-fix 4件 closure 後」**。MF-1 だけでなく normalizer_version /
  gate version discipline / pending除外 を closure 条件に含める。canary 1313 scratch packet（worker提出）は
  この4件を満たす形で Mode B exec lease に進める。
- **15×16 case-pivot は report-only で並行可**（mint/integration/canonical は HOLD）。D1TAXO(#15) と文献(#16) を
  「cases を軸に収束」させる方針を SoT 設計の前提に据える。over-claim 3点は文面ガードとして固定。
- HOLD 継続: production DDL apply / canonical / claim-support / embedding / broad batch / backbone minting。
