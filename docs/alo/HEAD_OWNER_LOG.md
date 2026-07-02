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

- digest_id: HOL-20260702-008
  trigger: 検収・canonical反映
  summary: 2大authority canonical昇格完了(owner GO). 判例212,602→211,988(dedup614+court化け15復元) / journal 931→924(NORMALIZE341+MERGE7+税理ISSN)
  reason: workerが発注書の算術ミス(1038=DUP_HANREI/IDENTITY二重計上)を停止・訂正=614削除が正(残identity_key重複6=DISTINCT held完全一致で裏取り). 236実判決の過削除を回避. 元d1law2ファイル/v14保全=rollback可
  related_orch: ORCH-AUTHORITY-APPLY | related_commit: journal v15=b741d2a(casename) / 判例dedup=d1law_dl/判例_identity_keys_dedup_canonical_20260702.csv(gitでなくファイル) | owner_pending: consumer配線(L5等)をv15/dedupへ=producer次段

- digest_id: HOL-20260701-007
  trigger: 発注・検収
  summary: 2大join根authorityのQA→WO化→段1投下完了。判例(ORCH hanrei)+journal(ORCH journal)。journal記事加重カバレッジ=ISSN77.3%+NCID19.9%=97.2%(行44.6%無ISSNは誤解)
  reason: 判例authority修正候補1063/journal370。両WOとも段1=read-only dry-run投下・段2実反映はowner GO。watcher未常駐なら手動wake_worker(要/login)。手戻り少・全join土台
  related_orch: ORCH-HANREI-AUTHORITY-FIX / ORCH-JOURNAL-AUTHORITY-FIX | related_commit: WO fbc09d0, data 09318b0 | owner_pending: watcher起動 or 手動launch, 段2 GO

- digest_id: HOL-20260701-006
  trigger: handoff_review
  summary: 判例authority整合性QA(read-only)=高レバ低手戻りタスク発見。212602行に修正候補1063(dup ID600/dup identity444/bad date4/court化け15)
  reason: 全判決joinとL5の根。court化け(四日市→4日市)は評釈とのcourt_miss一因=authority修正でL5被覆も改善。決定論的確定誤りのみ。修正は判例pipeline owner GO
  related_orch: 判例authority QA | related_commit: (本コミット, data=39783df) | owner_pending: yes(判例pipelineへの修正反映可否)

- digest_id: HOL-20260701-005
  trigger: policy_decision
  summary: 通称衝突33の分離を二段設計(L5_collision_separation): 段1=formal事件名subject差でread-only分離12/段2=同subjectは当事者署名(owner権威)要21
  reason: 武富士(租税/不法行為)等は法分野で分離、日産自動車(労働×3)等は当事者でしか分けられず判決本文/curated索引=owner領域。LITIGATION-001はGPT監査中
  related_orch: L5_collision_separation v0.1 | related_commit: (本コミット) | owner_pending: yes(段2の当事者署名権威取込)

- digest_id: HOL-20260701-004
  trigger: policy_decision
  summary: L5主鍵の1:N構造化を設計(DD-L5-LITIGATION-001): 通称→事件(litigation)→判決の二層。機械精査でCONFLICT77を審級昇順で判別
  reason: 通称→判例は1:1でなく1:N(訴訟チェーン)。litigation_chain44(機械確定)/通称衝突33(held)。flat mapの誤りを解く。code=worktree-casename-dict 1cf849a
  related_orch: DD-L5-LITIGATION-001 | related_commit: (本コミット, data=1cf849a) | owner_pending: yes(GPT監査 or 次設計)

- digest_id: HOL-20260701-003
  trigger: handoff_review
  summary: GPT監査2件帰り: L5 v0.3=DESIGN_PASS_WITH_NOTES(7点CLOSED)、PERIODICAL-003 v0.1=MODIFY_REQUIRED→v0.2再投函
  reason: PERIODICAL-003核心指摘=target正でもedge意味誤り(評釈対象でなく引用/脚注)のfalse link。MF-1 edge role gate等5点反映。L5はreview packet化がGO(DB投入HOLD)
  related_orch: DD-PERIODICAL-003 v0.2 / DD-L5 v0.3 | related_commit: (本コミット) | owner_pending: yes(PERIODICAL-003 v0.2帰り便 / L5 review packet)

- digest_id: HOL-20260701-002
  trigger: handoff_review
  summary: L5-DISAMBIGUATION v0.3 GPT=DESIGN_PASS_WITH_NOTES。Must-Fix7点全CLOSED。T1 23/map T1+T2 615がreview packet候補
  reason: 'accepted edge'表示はDB前に避ける(edge_candidate_tier/edge_status二軸)。T3 922自動accepted禁止。DB load/canonical昇格はHOLD
  related_orch: DD-L5-DISAMBIGUATION v0.3 | related_commit: 結果file_id 2318727879847 | owner_pending: yes(owner review packet→ratify→DB投入)

- digest_id: HOL-20260701-001
  trigger: policy_decision
  summary: head本務に回帰=OCR抽出精度監査規格をDD化(DD-PERIODICAL-003)。誤OCR=edge_falselinkを号ISSN衝突検査の一般化で封じる
  reason: 私の判例百選縛り→ad-hoc OCR(HIGH-HOLD踏越)を是正。OCR-conf閾値/named reject code/低conf held/tieringを規格化(read-only)
  related_orch: DD-PERIODICAL-003 | related_commit: (本コミット) | owner_pending: yes(GPT監査 or owner ratify)

- digest_id: HOL-20260630-020
  trigger: handoff_review
  summary: GPT Pro L5監査=DESIGN_MODIFY_REQUIRED→Must-Fix7点反映でv0.3(status弱体化/court空欄除外/generic guard/edge証跡/owner-review/map tiering/canonical設計)。再投函
  reason: 『=1→当事者別名』『≥2→確定』が過強の指摘が正鵠。confirmed8のみ・edge T1=23/map T1+T2=615に正直化。canonical target=判例IDでCASENAMEはalias。code=worktree-casename-dict a4a64aa
  related_orch: DD-L5-DISAMBIGUATION v0.3 | related_commit: (本コミット, code=a4a64aa) | owner_pending: yes(GPT v0.3再監査)

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
