from alo_gpt_audit.classify import build_action_queue, label_suffix
from alo_gpt_audit.lane import scan


def _by_id(items):
    return {i.request_id: i for i in items}


def test_label_suffix_resolution():
    assert label_suffix("DDSTATUS", "DDSTATUS_PASS_WITH_NOTES") == "PASS_WITH_NOTES"
    assert label_suffix("DDCASESOURCE", "DDCASESOURCE_NEED_MORE") == "NEED_MORE"
    # gate 不明でも接尾辞で解決
    assert label_suffix(None, "G0_PASS") == "PASS"


def test_action_queue_derives_next_action(design_lane_root):
    lane = scan(design_lane_root)
    items = _by_id(build_action_queue(lane))

    # MODIFY_REQUIRED -> patch / requeue
    sr = items["20260605_statusregistry_v0.1_DDSTATUS"]
    assert sr.next_action_type == "patch"
    assert sr.requeue_expected is True
    assert sr.ratify_required is False

    # PASS_WITH_NOTES -> ratify, blocking notes 抽出
    ch = items["20260605_claudehead_v1.1_DDCLAUDEHEAD"]
    assert ch.next_action_type == "ratify"
    assert ch.ratify_required is True
    assert any("hand/capacity" in b for b in ch.blocking_notes)
    assert any("fallback" in b for b in ch.blocking_notes)

    # NEED_MORE -> required_materials, need_more_type/missing 抽出
    qj = items["20260605_quasijudicial_v0.4_DDCASESOURCE"]
    assert qj.next_action_type == "required_materials"
    assert qj.need_more_type == "material_absent"
    assert len(qj.missing_materials) == 2

    # legaldb MODIFY_REQUIRED
    ld = items["20260606_legaldb_v0.5_DESIGN"]
    assert ld.next_action_type == "patch"


def test_action_queue_covers_processed_results(lane_root):
    # 退避済み (processed_done) の RESULT も反映キューに出る = 「赤入れで止まる」を防ぐ
    lane = scan(lane_root)
    items = build_action_queue(lane)
    statuses = {i.request_id: i.lane_status for i in items}
    # claudehead は processed 済みだが RESULT があるので消化対象として出続ける
    assert statuses["20260605_claudehead_v1.1_DDCLAUDEHEAD"] == "processed_done"
    # quasijudicial は未退避 (answered_not_processed)
    assert statuses["20260605_quasijudicial_v0.4_DDCASESOURCE"] == "answered_not_processed"
