---
request_id: 20260618_DD-LITID-PLAN_4route_edition_resolution
decision_id: DD-LITID 配下 4ルート書籍 版同定パイプラインの全体計画（工程順序と最善手）
request_type: 設計監査 (DESIGN gate)
topic: 4-route (自所物理/裁断・LION BOLT・弁コム・legallib) book edition resolution against NDL
作成日: 2026-06-18
監査対象: dd/DD-LITID-PLAN_4route_edition_resolution_v0.1_20260618.md（本依頼に全文同梱・§3）
source_hash: sha256:be0c164821ba95f0f41149fc14074e3d84790d6cd828ca7a5b9ba81990f76aab
source_commit: 05b1259 (branch claude/book-identification-progress-7yjxpc)
親設計: DD-LITID-001 v0.2（fingerprints / E3 / E4）＋ DD-LITID-FP（4信号）＋ DD-LITID-001-ATTR（属性観測層）
result_expected_filename: 20260618_DD-LITID-PLAN_4route_edition_resolution_RESULT.md
status: queued
gate: DESIGN。**DDL/実装/backfill/本番突合/canonical promotion/serving確定は対象外。** 工程計画の可否のみ。
---

# GPT Pro お目付け役 監査依頼: 4ルート書籍 版同定パイプライン 全体計画

## 0. 独立監査の要請（迎合不要）

owner が「これは今後のポイントになる」と位置づけた、書籍同定の **全体工程計画** の監査。
起案は Claude（同 family の blind spot あり）。**結論ありきの追認は不要。** 計画の前提・順序・
load-bearing な依存を厳しく疑ってほしい。「方向でよい」だけの返答は要らない。

## 1. 趣旨（owner ゴール・変更不可）

実データで、自所が **物理本/裁断本** で持つデータと、**LION BOLT / 弁コム / legallib** 由来の
大きく4ルートの書籍を、(1) 版ごと区分管理、(2) NDL 等と突合、(3) 別の本は別・同じ本は同じと
カウントできる状態にする。今後の購入処理（定常運用）まで含めて、**最短・最正確・最小手戻り・高拡張**で。

## 2. 確定済み前提（枠）

- DD-LITID-001 v0.2 採用方向、版を束ねない（DDL-20260428-01）、fingerprints=identity SoT、
  title-only 禁止、独立証拠2つで confirm、raw 保全、append-only 観測。
- 本件は **工程計画（順序と最善手）の設計可否のみ**。実装/DDL/本番突合は対象外。

## 3. 提案要旨（対象 doc 全文は source_hash の現物。要点）

計画の核は **可逆性で工程を分ける**:
- 🔴 不可逆・安価（provenance/rights/medium/時刻の捕捉 ＋ raw 投入）＝今すぐ。
- 🟢 可逆（配点・閾値・TTL）＝本番分布で較正、proxy で決め打ちしない。
- 🟠 不可逆・高価（promote/canonical/serving/DDL/backfill）＝shadow 実証後にゲート開放。

データモデル: `holding（所有）→ edition(=NDL bibid 錨)→ work` ＋ `source_biblio_item`(4ルート生)
＋ authority(NDL/CiNii/KAKEN)。カウントは work/edition/holding/access の4種を分離定義。

マッチング: **NDL をハブ**にして 4×4 総当り(O(n²))を source→NDL(O(n))へ縮約。Waterfall
（ISBN完全一致→強書誌NDLクロスウォーク→無ISBNはTOC主証拠＋独立証拠2本）。ブロッキングで高速化。
同一出版社TOC再配信は `origin_publisher` で独立性判定（同origin=0.5/異origin=1.0証拠）。

フェーズ: 0 背骨確定 → 1 legallib/LION BOLT 含む全ルート＋NDL raw投入 → 2 正規化+fingerprint
→ 3 NDLハブ突合 shadow → 4 実分布較正+disputed腑分け → 5 promote+canonical+count → 6 定常運用（増分）。

## 4. 特に厳しく監査してほしい点（前提を疑え）

1. **NDL ハブ仮説の妥当性（最重要）**: NDL bibid は本当に edition 粒度の錨になるか。
   同一 ISBN で複数 bibid／版違いが 1 bibid に潰れる事象は。法律実務書・**加除式・頻繁改訂本**で
   NDL カバレッジが薄い場合、ハブが穴だらけになり O(n) 縮約が崩れて無 ISBN 直接突合が主役化し、
   計画前提（速さ・正確さ）が壊れないか。NDL 非収載率の見積りと fallback 設計は十分か。
2. **可逆性二分法の罠**: 「閾値は可逆」と言うが、shadow で較正→promote 後に閾値を変えると
   既存 confirm リンクが遡及的に揺れる。本当に可逆か。閾値変更時の再評価コスト・リンク安定性・
   confirm 済みの不変性保証はどう設計すべきか。
3. **raw 投入ノーリスク主張の穴**: append-only でも、スクレイプ時点でしか取れない TOC/権利状態/
   出所がある（弁コム/legallib）。Phase 0（🔴メタ列確定）より先に Phase 1（投入）に入ると
   「メタ取り損ね確定」になる。Phase 0→1 の順序は本当に間に合うか、投入と捕捉設計の同時性をどう担保するか。
4. **holding ↔ edition 着地の残差**: 自所裁断 PDF の版が奥付欠落・改訂未記載で決まらない場合の扱い。
   edition 未確定 holding をどう保持し、後で着地させるか（unresolved holding の設計）。
5. **work-rollup 遅延 vs カウント欲求の衝突**: work を confirmed まで作らないと「同じ本は同じ」カウントが
   初期に出ない。candidate work で暫定カウントを見せると誤統合を数える。カウント提供時期と
   暫定/確定の二重表示をどう規律するか。
6. **「持っている」の定義揺れ**: 弁コム/legallib は所有でなくアクセス権。owner ゴールの「うちが持つデータ」に
   オンライン購読を含めるか。holding(所有) と access(閲覧可) の分離はゴール解釈として正しいか、過剰分割か。
7. **独立性判定の実現可能性（循環依存）**: 計画の誤統合抑止は「同一供給元再配信を検出できる」前提に乗る。
   弁コム/legallib が `origin_publisher` を提供しない場合 `independence_flag` 計算不能で名目倒れ。
   この依存は循環でないか。代替の独立性推定（content_hash 一致・抽出器/URL pattern 等）で足りるか。
8. **過剰/過小設計**: 4カウント分離・属性観測層・NDLハブ・可逆性三分の全部を初手で持つのは過剰でないか。
   逆に MVP に削るならどこを残しどこを後回すか。DD-PERIODICAL（雑誌/記事）・著者名寄せと
   同一基盤に乗るか別物に割れるか。

## 5. 期待する判定

`DESIGN_PASS` / `DESIGN_PASS_WITH_NOTES` / `MODIFY_REQUIRED` / `HOLD`

## 6. 返答フォーマット

```text
status:
verdict_summary:
accepted_now:
- 可逆性による工程分離:
- データモデル(holding/edition/work/source/authority):
- NDLハブ + waterfall + blocking:
- フェーズ順序(0..6):
adversarial_findings:
- NDLハブ仮説の妥当性:
- 可逆性二分法の罠:
- raw投入ノーリスク主張の穴:
- holding↔edition残差:
- work-rollup遅延vsカウント:
- 「持っている」定義揺れ:
- 独立性判定の循環依存:
- 過剰/過小設計:
must_fix:
should_fix:
open_questions:
recommended_next_steps:
final_gate:
```

## 7. 監査上の注意

DDL/実装/backfill/本番突合/canonical promotion/serving確定/embedding/外部公開は本件で許可しない。
工程計画の設計可否のみ。

## 8. banto 自己申告

- owner が承認した全体計画を Claude が DD 化。新正本は作らず DD-LITID-001/FP/ATTR の上に工程を載せる位置づけ。
- 親 DD-LITID-001 v0.2 の正確な列名/ゲート名への厳密マッピングと、LION BOLT/legallib の実メタ形状確認は
  未実施（§9 既知の未確定）。監査所見と合わせ Phase 0 で確定予定。
- 根拠データ: biblio 現況 = asai 蔵書(NDC5,503/NDLC5,020)＋弁コム3,802 のみ投入、legallib/LION BOLT 未投入。
  proxy dry-run（蔵書↔弁コム 1,470書名一致/厚化847/出版社差2.7%/年差2.3%/ungrounded0、read-only）。
