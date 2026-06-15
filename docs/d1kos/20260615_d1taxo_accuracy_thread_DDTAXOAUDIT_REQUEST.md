---
doc_id: 20260615_d1taxo_accuracy_thread_DDTAXOAUDIT_REQUEST
date_jst: 2026-06-15
requester: 番頭（Claude Head / Project-codex セッション）
target_reviewer: GPT お目付け役
result_label_vocab: [PASS, PASS_WITH_NOTES, NEEDS_MORE, REVISE, NO_GO]
scope: methodology + conclusions の read-only 監査。DB/canonical/raw への変更は本依頼の対象外（apply は HOLD 継続）。
related:
  - DD-D1TAXO-001 v0.3-draft（d1law_civil_selection_taxonomy_live_capture）
  - DD-D1TAXO-001_acceptance_package_20260615（§6 に別の設計監査依頼テンプレあり）
  - DD-D1TAXO-002 v0.1-draft（L1-L3 × alo_statutes crosswalk）
  - GitHub PR #22（asai-dot/Project-codex, branch claude/d1-case-law-taxonomy-8pf3d4）
---

# DDTAXOAUDIT 監査依頼 — D1-Law 体系目次 精度検収＆番頭セッション通し

## 0. 依頼趣旨

番頭セッションで、ワーカーちゃんの「D1-Law 民事セレクション 体系目次 ライブ取得（DD-D1TAXO-001）」の
**状況確認 → 精度検収（自動＋目視）→ 次工程WO発注** を独立に実施した。
この一連の**手法と結論**を通してレビューし、情報共有＆ブラッシュアップしたい。
（DD-D1TAXO-001 自体の設計監査は acceptance_package §6 に別途あり。本依頼は重複せず、
「検収のやり方」と「番頭の独立検証の正本反映」に焦点を当てる。）

## 1. 対象データ（事実）

- ②WEB側ライブ取得: 民事セレクション・**21法編 / 総ノード 55,074 / 最大深度 10 / 葉 41,311**
  （walker errors 0, progress 55,074==total）。例: 民法709条配下 6,876ノード。
- box_prior(2026-05-19, 判例trunk_inference 48,301) との突合: **recall 97.29%** / matched 33,411 /
  removed 929 / added 21,667 / live_precision 0.6067。
- 変換(v3): L4-L11 **49,733** → `alo_terms(jp_kos, scheme_id=d1law-taikei)`、L1-L3 **5,341** →
  `alo_statutes`候補(DD-D1TAXO-002)、`skos_broader` **38,910**、labels/extra 各 49,733。
- 実体はローカル alo-ai ＋ ローカル PostgreSQL。**クラウド Supabase 未投入。DBA apply は A1–A8 HOLD。**

## 2. 番頭がこのスレで実施したこと

1. **所在特定**: git空・Box/Supabase/handoff横断調査で D1KOS の正体（D1-Law Knowledge Organization System）と
   2系統（①判例から evidence / ②WEBから体系ナビ）を確定。
2. **ベースライン記録**: ①判例側D1KOS(2026-05-25: node 9,449 / evidence 57,315)を検収基準点として
   PR #22 にコミット。②WEB側(55,074)は別物＝骨格の拡張版と整理。
3. **A 内部整合（自動・全件 55,074）**: nodes.csv を全件検査 → key重複0 / orphan0 / level整合違反0 /
   child_count(宣言=実子数)一致 / is_leaf整合 / by_level==summary / NFC clean / 循環0 / 葉41,311一致。
   変換件数は**源CSVのレベル分布から独立再計算**し v3 manifest と全一致（`skos_broader 38,910 = level≥4`
   ＝「L4の親=L3(statutes)へは張らない」スキーム横断禁止の実装証明）。→ 全 green。
4. **B 実画面照合**: 21法編×5＝**105件の層化目視チェックリスト**（フルパス/件数/dtmid付）を生成・納品。
   owner の俯瞰 spot-check で「違和感なし・キレイ」。個別105行の○付けはしていない。
5. **C 次WO発注**: 唯一バイト検証できなかった `.jsonl` 実体を閉じる **WO-D1TAXO-002**
   （sha256/行数・term_uri一意&1:1・skos_broader dst実在&同scheme・値域・pref重複・源↔terms集合一致 の7項目、
   read-only）を Box to_worker へ投函。

## 3. 監査論点（各 5ラベル ＋ 根拠 ＋ ブラッシュアップ提案 で）

1. **精度検収フレーム（A内部整合＋B目視＋Cバイト検査）の十分性**。
   特に B を「105件（=55,074の0.19%）・各root均等5件の層化・個別○なしの俯瞰spot-check」で合格としたのは妥当か。
   サンプル件数/層化軸（root均等 vs 深度/サイズ比例）/合否基準の設計に改善余地は？
2. **box_prior を真値扱いしない判断**と、**precision 60.67% を誤り率と読まない解釈**（added 21,667 の大半は
   box_priorの未到達枝という説明）の妥当性。**removed 929件の仕分けを「任意」に留めた**判断は是か。
3. **ベースライン設計**（①判例側5/26 を基準点、②WEB側を別物扱い）と、空ブランチに PR #22 として
   検収証跡を置く運用の妥当性。
4. **WO-D1TAXO-002 の検査7項目**に過不足はないか。DBA apply（A1–A8）前ゲートとして十分か。追加すべき不変条件は？
5. **二重管理・反映経路**: 番頭が独立検証した内容（git PR #22）と、Box正本・DD-D1TAXO群・受入パッケージの
   整合をどう取るべきか。番頭の独立検証結果を正本（90_design_decisions / DD）へ反映する正しい経路は？

## 4. 参照アーティファクト

- GitHub PR #22（4コミット）:
  - `docs/d1kos/BASELINE_d1kos_20260525.md`
  - `docs/d1kos/ACCURACY_CHECK_DD-D1TAXO-001_A_internal.md`
  - `docs/d1kos/ACCURACY_SAMPLE_CHECK_DD-D1TAXO-001_105.md`（owner spot-check 合格記録入り）
  - `docs/d1kos/WO_d1taxo_jsonl_integrity_verify_20260615_2030.md`
- Box: DD-D1TAXO-001 v0.1/v0.2/v0.3・acceptance_package・DD-D1TAXO-002 v0.1、
  iteration の live_taxonomy / box_prior_join / v3 load 一式。

## 5. 期待アウトプット

- 各論点に 5ラベル＋根拠。
- 検収手法の**ブラッシュアップ提案**（サンプリング設計・追加不変条件・正本反映フロー）。
- 必要なら NEEDS_MORE で不足材料を具体指定。
