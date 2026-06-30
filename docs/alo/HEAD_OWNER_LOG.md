# HEAD_OWNER_LOG — 航海日誌（Head↔Owner 決定ログ・単一の真実）

> 本ファイルは DD-ORCH-CONTINUITY-001 v0.3（RATIFIED 2026-06-30）の成果物。
> **継続性・意図・HOLD・owner pending の蒸留ログに限定**（設計判断正本ではない）。
> head は3トリガ（方針決定 / 発注・検収 / owner判断待ち発生）でのみ digest を5行追記し push。
> 代理 head BOOTSTRAP: ①本ファイル全文 ②`claude agents --json` ③`git log -15` ④`owner_pending: yes` を最優先。
> 正本参照: `origin/claude/magazine-object-analysis-seg9cr:docs/alo/HEAD_OWNER_LOG.md`（head infra 正本ブランチ）。ORCH は `required_log_commit / required_digest_id /
> required_standing_ids` を、worker RESULT は `read_log_commit / read_digest_id / read_standing_ids` を持つ。

---

## A. STANDING（恒久の決定・好み・禁止 / active 最大20・各3行以内）

- standing_id: HOS-001
  rule: 共有ブランチへ force push / -f 禁止（rebase 後に通常 push）
  applies_to: all branches | enforcement: global_required | status: active | last_confirmed: 2026-06-30 | owner_ratified: yes

- standing_id: HOS-002
  rule: external_share_allowed=false は不変（外部公開しない）
  applies_to: all data | enforcement: global_required | status: active | last_confirmed: 2026-06-30 | owner_ratified: yes

- standing_id: HOS-003
  rule: canonical 昇格・DB投入・accepted edge化・外部公開・生payload取込は owner(asai) GO 必須
  applies_to: all threads | enforcement: global_required | status: active | last_confirmed: 2026-06-30 | owner_ratified: yes

- standing_id: HOS-004
  rule: ローカルちゃん(ローカルLLM)へは必ず処理可能サイズにチャンク分割してから発注
  applies_to: local dispatch | enforcement: task_scoped | status: active | last_confirmed: 2026-06-30 | owner_ratified: yes

- standing_id: HOS-005
  rule: 常駐デーモンを増やさない（コスト過大）。storm対策は wake_worker の起動時 cap ゲートで足りる
  applies_to: orchestration | enforcement: global_required | status: active | last_confirmed: 2026-06-30 | owner_ratified: yes

- standing_id: HOS-006
  rule: DD 監査は Box gpt_ometsuke/to_gpt 経由。PASS_WITH_NOTES 以上 → owner ratify → accepted → main commit → 実装
  applies_to: design audits | enforcement: task_scoped | status: active | last_confirmed: 2026-06-30 | owner_ratified: yes

- standing_id: HOS-007
  rule: ループは EXIT-A(成功)/B(収穫逓減)/C(完了)/D(緊急停止)で必ず止める。各発注書冒頭にどの EXIT か明示
  applies_to: orchestration loops | enforcement: task_scoped | status: active | last_confirmed: 2026-06-30 | owner_ratified: yes

---

## B. SESSION DIGESTS（新しい順・直近~30件 / 1件5行）

- digest_id: HOL-20260630-019
  trigger: handoff_review
  summary: owner指摘『名のある判例50倍あるやろ』が正鵠→court正規化バグ(末尾判/決)発見・修正。L5被覆激増(マップ199→1575/edge34→66/unresolved807→323)
  reason: normalize_courtが東京地判→東京地に正規化せず下級審全不一致(court_miss3653→558)。GPT監査は旧数字をhold→v0.2で再投函。code=worktree-casename-dict c4aa073
  related_orch: DD-L5-DISAMBIGUATION v0.2 | related_commit: (本コミット, code=c4aa073) | owner_pending: yes(GPT v0.2監査帰り便)

- digest_id: HOL-20260630-018
  trigger: handoff_review
  summary: L5群(過併合判定/edge化34/通称マップ141)を1本のDD-L5-DISAMBIGUATIONにまとめGPT Pro独立監査へ投函(to_gpt queued)
  reason: owner指示。source_hash fd16988…。判定/edgeのfalse linkage/被覆拡大/L5主鍵昇格可否を5点監査依頼
  related_orch: DD-L5-DISAMBIGUATION | related_commit: (本コミット) | owner_pending: yes(GPT再監査の帰り便→反映)

- digest_id: HOL-20260630-017
  trigger: handoff_review
  summary: L5 edge化34件(owner GO・file artifact)＋通称↔正式名マップ141ペア導出(判例DB)。単発199バケット=609評釈が確定接続候補
  reason: edge化はDB投入せずcanonical file(可逆)・本番投入は投入先確定後canary→batch。マップは判例百選不在のため判例DB直接導出。code=worktree-casename-dict 385649f/fae6097
  related_orch: L5 edge化+通称マップ | related_commit: (本コミット, code=385649f/fae6097) | owner_pending: yes(edge本番DB投入の投入先・マップ被覆拡大の反復)

- digest_id: HOL-20260630-016
  trigger: handoff_review
  summary: L5照合 第二段(read-only確定提案): SPLIT候補247のvariant(正式事件名)→判例ID 高精度照合24件確定
  reason: ハマキョウレックス→28262467/レペタ→27803181 等。形式名一致のみ高精度採用。通称単独は候補docket併記。code=worktree-casename-dict 76c1d0b
  related_orch: L5-disambiguation stage2 | related_commit: (本コミット, code=76c1d0b) | owner_pending: yes(被覆拡大は通称↔正式名マップ・edge化はT2 owner GO)

- digest_id: HOL-20260630-015
  trigger: handoff_review
  summary: L5判例DB照合パイロット(read-only): CASENAME過併合1124を判例_identity_keys(212,604行事件番号)で照合
  reason: SPLIT_confirmed246(>=2事件番号=真の別事件)/MERGE71(当事者別名)/unresolved807。判例権威で真偽機械確定を実証。code=worktree-casename-dict 2fd173b
  related_orch: L5-disambiguation(判例DB照合) | related_commit: (本コミット, code=2fd173b) | owner_pending: yes(二段目=名称→事件番号確定・edge化要承認)

- digest_id: HOL-20260630-014
  trigger: handoff_review
  summary: GO順3実装(owner GO): CASENAME v0.2(過併合flag1124,a0fa2ca)/NDL v0.2(機関分割除外111→105,c0709e3)/ISSUE本採用+field_fragment flag38(346b731)
  reason: CASENAMEは文字列で確実分割不能ゆえAUTHOR同様フラグ化(誤分割回避)。NDLは機関分割除外。ISSUEクリーン本採用。HOL-011/012/013解消
  related_orch: CASENAME/NDL/ISSUE v0.2 | related_commit: (本コミット, code=a0fa2ca/c0709e3/346b731) | owner_pending: no

- digest_id: HOL-20260630-013
  trigger: handoff_review
  summary: ISSUE-FEATURE(特集号メタ8582号)をhead検証 → PASS(高精度)。junk title0.4%・97.1%が単発特集
  reason: 汎用ラベル混入0・恒例年次特集は正当・曖昧と低confidenceを自己フラグ。SERIES/AUTHOR同様クリーン
  related_orch: ORCH-ISSUE-FEATURE | related_commit: 4ca0ffa | owner_pending: no(GO済→HOL-014)

- digest_id: HOL-20260630-012
  trigger: handoff_review
  summary: CASENAME-DICT(L5主鍵)をhead検証 → PASS_WITH_NOTES。(court,date)キーで同日別事件を過併合
  reason: ハマキョウレックス+長澤運輸/新国立劇場+INAX 等が同日同裁判所ゆえ1事件に誤併合。v0.2で固有名stem分割を推奨
  related_orch: ORCH-CASENAME-DICT | related_commit: (本コミット) | owner_pending: yes(v0.2 着手可否)

- digest_id: HOL-20260630-011
  trigger: handoff_review
  summary: NDL-RECONCILE を head 直接検証 → PASS_WITH_NOTES。承継144件・per-row高精度だがクラスタ6件機関誤併合
  reason: 同一大学の別部局誌を1承継チェーンに誤結合(明治学院/静岡大等26誌)。v0.2で推移結合制限を推奨
  related_orch: ORCH-NDL-RECONCILE | related_commit: (本コミット) | owner_pending: yes(v0.2 着手可否)

- digest_id: HOL-20260630-010
  trigger: handoff_review
  summary: AUTHOR-CLUSTER 本採用＋is_ambiguousフラグ実装(owner GO)。author_index_v0.2で≤2字809件にtrue付与
  reason: 同名異人の誤用防止フラグ。code=worktree-author-cluster 2570418。保守設計(fuzzy無効)維持
  related_orch: ORCH-AUTHOR-CLUSTER v0.2 | related_commit: (本コミット, code=2570418) | owner_pending: no

- digest_id: HOL-20260630-009
  trigger: handoff_review
  summary: AUTHOR-CLUSTER を head 直接検証 → PASS(高精度)。旧字統合214件正しい/誤併合は≤2字名0.90%に限局
  reason: fuzzy無効の保守設計は妥当(別人誤マージ回避)。推奨=≤2字809clusterにis_ambiguousフラグ。SERIES同様クリーン
  related_orch: ORCH-AUTHOR-CLUSTER | related_commit: 88079c2 | owner_pending: no(GO済→HOL-010)

- digest_id: HOL-20260630-008
  trigger: handoff_review
  summary: CITATION-EXTRACT v0.2 実装(owner GO)。保険法ファミリー辞書追加で部分文字列FP修正→保険法833→489(-344)正タグ昇格
  reason: 誤タグを正タグに昇格=精度・被覆同時改善。code は wt-cite-extract dd84c6e、判例側は不変
  related_orch: ORCH-CITATION-EXTRACT v0.2 | related_commit: (本コミット, code=dd84c6e) | owner_pending: no

- digest_id: HOL-20260630-007
  trigger: handoff_review
  summary: CITATION-EXTRACT を head 直接検証。判例引用=PASS(和暦↔西暦整合100%/79936行)、法令引用=PASS_WITH_NOTES
  reason: 法令に部分文字列FP(保険法タグの64%が労災/健康保険法=別法令)。v0.2で保険法ファミリー辞書追加を推奨
  related_orch: ORCH-CITATION-EXTRACT | related_commit: 0aa0379 | owner_pending: no(GO済→HOL-008)

- digest_id: HOL-20260630-006
  trigger: handoff_review
  summary: owner GO で SERIES-DETECT v0.1 本採用＋detect_series.py を patch(junk系列除外)→v0.2再生成 10243→10174(-69)
  reason: 偽候補69件を生成パッチで恒久除去(demote+再発防止を同時達成)。実データ再生成で-69完全一致を検証
  related_orch: ORCH-ACCEPT-SERIES-DETECT_v0.2 | related_commit: (本コミット) | owner_pending: no

- digest_id: HOL-20260630-005
  trigger: handoff_review
  summary: SERIES-VALIDATE を head 直接 read-only 検証 → 精度99.33%(60目視59/60)・偽候補69件。PASS(本採用推奨)
  reason: 既存の静的データ(10,243系列)を非破壊で精度確定＝手戻りゼロの精度向上。owner GO で本採用＋偽候補demote
  related_orch: ORCH-SERIES-VALIDATE | related_commit: 0892ffa | owner_pending: no(2026-06-30 GO済→HOL-006)

- digest_id: HOL-20260630-004
  trigger: handoff_review
  summary: 本セッションの作業記録 DD を作成（docs/alo/SESSION-RECORD_DD-ORCH-CONTINUITY-001_20260630.md）＋ Box handoffs に記録
  reason: head が1枚読めば storm鎮圧〜航海日誌一気通貫の全容と現在地を継げるように（owner 指示）
  related_orch: DD-ORCH-CONTINUITY-001 | related_commit: (本コミット) | owner_pending: no

- digest_id: HOL-20260630-003
  trigger: handoff_review
  summary: ORCH検収ゲートを実行スクリプト化（tools/head_owner_log_gate.py）。7 reject code + alias lint を機械判定
  reason: protocol のチェック表を完全自動化（owner GO）。自己検証9ケース全 PASS
  related_orch: DD-ORCH-CONTINUITY-001 v0.3 | related_commit: be6eb2c | owner_pending: no

- digest_id: HOL-20260630-002
  trigger: handoff_review
  summary: head が data limit で停止 → 代理 head が git+監査レーン+claude agents から状態復元（F1 を実演）
  reason: HEAD_OWNER_LOG 未実装だったため手動フォールバックで復旧。本 seed 作成の直接動機
  related_orch: (なし) | related_commit: 80fdc47 | owner_pending: no

- digest_id: HOL-20260630-001
  trigger: handoff_review
  summary: DD-ORCH-CONTINUITY-001 v0.3 が GPT Pro で DESIGN_PASS_WITH_NOTES → owner ratify → 実装GO
  reason: v0.2 の祖先方向バグ＋field統一＋enforcement scope を v0.3 で閉鎖
  related_orch: RATIFY_DD-ORCH-CONTINUITY-001_v0.3_20260630.md | related_commit: 80fdc47 | owner_pending: no

- digest_id: HOL-20260629-002
  trigger: policy_decision
  summary: head 交代継続＋ワーカー意図伝播のため航海日誌(HEAD_OWNER_LOG)を起票（F1/F2 解消）
  reason: 意図・経緯が head 会話にしか宿らず limit で揮発する問題
  related_orch: DD-ORCH-CONTINUITY-001 | related_commit: - | owner_pending: no

- digest_id: HOL-20260629-001
  trigger: policy_decision
  summary: worker storm 対策は wake_worker の cap ゲートのみ採用、reap デーモンは塩漬け
  reason: 常駐はコスト過大（owner 決定）
  related_orch: - | related_commit: 08aa69e | owner_pending: no

- digest_id: HOL-20260628-001
  trigger: policy_decision
  summary: ALO-MODEL-ROUTER v0.1 — 実行権限ルーターを ALO 基底に固定（雑誌スレで先行運用）
  reason: 実行権限を一元化（正本 alo_ai_router/）
  related_orch: ALO-MODEL-ROUTER | related_commit: dde3708 | owner_pending: no

- digest_id: HOL-20260627-003
  trigger: policy_decision
  summary: storm 3度目事故（login即死＋消費push失敗ループ）→ worker_watch にトリガ内容 SHA1 lock 導入
  reason: 同一内容トリガは二度起動しない＝push 失敗でも storm にならない
  related_orch: - | related_commit: 5630fca | owner_pending: no

- digest_id: HOL-20260627-002
  trigger: policy_decision
  summary: 止め時を明文化（EXIT-A 成功 / B 収穫逓減 / C 完了 / D 緊急停止）でループ無限化防止
  reason: 再発注ループが永遠に回る事故の防止（HOS-007 の根拠）
  related_orch: - | related_commit: 8398f5b | owner_pending: no

- digest_id: HOL-20260627-001
  trigger: handoff_review
  summary: ORCH-L4-COVERAGE-LIFT 完了 — orphan 誌接合救済 +1,496 / tsuukan_unavailable 0化
  reason: L4 接合被覆 99.28% → 99.6%+ 引き上げ（受入検査 PASS）
  related_orch: ORCH-L4-COVERAGE-LIFT | related_commit: 7f50299 | owner_pending: no

---

## C. archive_index（30件超過時に退避した digest の薄い索引）

- （まだ archive なし）
