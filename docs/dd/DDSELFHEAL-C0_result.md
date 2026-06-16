DDSELFHEAL_C0_PASS_WITH_NOTES

request_id: DDSELFHEAL-C0
reviewed_at_jst: 2026-06-16
gate: implementation_review + roadmap_advice
scope: DDSELFHEAL Phase C0 dry-run implementation
physical_write: HOLD / repair_write: HOLD / production_apply: HOLD / rdb_write: HOLD

(from_gpt/DDSELFHEAL-C0_result.md Box 2287692839804 の控え。反映状況は
20260616_DDSELFHEAL-C0_PASS_WITH_NOTES.md を参照。)

## verdict
C0 は DDSELFHEAL の主要 must_fix を report-only/dry-run として満たす。
SCAN→分類→repair plan→gate→decision_log chain は正しい骨格、writes_executed=0 が正しい境界。
C0 継続可。C1 write 解禁は ledger/idempotency/signoff package が整うまで不可。
最初の C1 write 候補は BodyShaRecompute (quarantine/offset ではない)。

## implementation review
1. 派生 vs raw mutation: 物理的に強制されるなら可。print_page/title_norm/source_sha256/
   quarantine_reason は派生 projection 可だが raw snapshot に書き戻さない。別 namespace/view 推奨。
   book 様 object に置くなら derived_from/repairer_version/projection_version/created_at/rollback proof を持つこと。
2. QuarantineOrphan 2ソース閾値: 概ね妥当。ただし多巻物/部分TOC/付録前付後付/既知 sparse 源は例外に。
   quarantine は quarantine_only (破壊的削除でない)。
3. OffsetPageConvert 閾値: conf=1.0+validated+anchors>=2 は C0/C1 で安全。法的ページ参照ゆえ厳しめに。
   最初の write 解禁 phase は anchors>=3 検討。anchors>=2 は dry-run/低リスク派生 projection のみ。
4. manifest 追加 (C1 前): pre/post_health, health_delta, apply_eligibility before/after,
   idempotency proof hash, no-op second-run proof, reviewer/owner signoff or whitelist id,
   rollback verification, affected object count, defect reason_code distribution, quarantine ledger pointer。

## must_fix status
class5=OK / raw非mutation=OK(別namespace前提) / identity保護=OK / health-eligibility分離=OK /
quarantine KPI=PARTIAL(age/escape/recurrence ledger は C1 quarantine write 前に必須) /
regression taxonomy=PARTIAL(C1 前に必須) / manifest schema=C0はOK・C1は不足 / semantic隔離=OK。

## roadmap advice
優先順位: (1) T2 DD-EDIDENT ratify 最優先 (edition identity は殆どの repair/apply gate の土台) →
(2) T1 DD-TOCADOPT 統合 corpus → (3) T3 C1 write 解禁は最後。共有 edition identity と統合 corpus が
安定する前に write 解禁しない。
C1 最小条件: golden 10→30以上 (sparse/multi-volume/page-offset/orphan/no-TOC/conflict 網羅) /
4 repairer が idempotency+no-op テスト通過 / quarantine write なら ledger / repair class ごとの
owner whitelist / manifest に pre-post health + rollback proof。
最初の write 解禁=BodyShaRecompute。第2=NormalizeTitleRegen(derived namespace 限定)。
Offset/Quarantine は golden 拡大まで保留。
並行レーン: DD-EDIDENT=共有 identity / DD-TOCADOPT=node・corpus 証拠 / DDSELFHEAL=report・gate・repair。
各レーンが edition identity や health score を再発明しない。
quarantine ledger: quarantine 状態変更前に必須。BodyShaRecompute が report-only quarantine のままなら後でよい。
撤退条件: repair plan の大半が human/quarantine で clean_set 増えない / false quarantine 率高い /
health 上がるのに apply_eligibility 上がらない / manifest が手動レビューより高コスト /
決定的 repair が常習的に semantic 例外要 / owner が dashboard から clean/quarantine 理由を理解できない。

## release boundary
今 許可: C0 dry-run 継続 / golden 拡張 / manifest 項目追加 / quarantine ledger 設計 /
C1 BodyShaRecompute candidate packet 準備。
HOLD: 全 repair write / production apply / RDB write / semantic repair / identity・canonical mutation /
ledger 無し quarantine 状態変更。

## final
DDSELFHEAL_C0_PASS_WITH_NOTES. C0 は順調。EDIDENT → TOCADOPT 統合 corpus → C1 の順で。
最初の C1 write は BodyShaRecompute、golden 拡張 + manifest 追加 + owner whitelist 後にのみ。
