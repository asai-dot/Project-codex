#!/usr/bin/env python3
"""test_jufu_intake.py — jufu 取込境界の検証 (DD-CASEID-005)。"""
import sys
from jufu_intake import allow_jufu_use, classify_jufu_observation, GLOBAL_SINKS


def run() -> int:
    fails = []

    def check(name, cond):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")
        if not cond:
            fails.append(name)

    # identity evidence は常に許可(出口ではない)
    check("identity_evidence 許可(global)", allow_jufu_use("identity_evidence", scope="global"))
    check("identity_evidence 許可(matter)", allow_jufu_use("identity_evidence", scope="matter"))

    # global では出口5点すべて不可
    check("global 出口5点すべて拒否",
          all(not allow_jufu_use(s, scope="global") for s in GLOBAL_SINKS))

    # embedding は matter でも(認可者でも)不可(RP-04)
    check("embedding は matter認可でも拒否",
          not allow_jufu_use("embedding", scope="matter",
                             requester_matters={"M-1"}, matter_id="M-1"))

    # matter 内・認可者: display/mcp_serve は許可
    check("matter認可者 display 許可",
          allow_jufu_use("display", scope="matter", requester_matters={"M-1"}, matter_id="M-1"))
    check("matter認可者 mcp_serve 許可",
          allow_jufu_use("mcp_serve", scope="matter", requester_matters={"M-1"}, matter_id="M-1"))

    # matter 内でも export/claim_support/global_index は不可(matter 外へ出す用途)
    check("matter内でも export 拒否",
          not allow_jufu_use("export", scope="matter", requester_matters={"M-1"}, matter_id="M-1"))
    check("matter内でも claim_support 拒否",
          not allow_jufu_use("claim_support", scope="matter", requester_matters={"M-1"}, matter_id="M-1"))

    # 未認可 matter は閲覧も不可
    check("未認可matter は mcp_serve 拒否",
          not allow_jufu_use("mcp_serve", scope="matter", requester_matters=None, matter_id="M-1"))
    check("別matter認可は拒否",
          not allow_jufu_use("mcp_serve", scope="matter", requester_matters={"M-9"}, matter_id="M-1"))

    # 取込分類
    c = classify_jufu_observation({"observation_id": "j1"})
    check("分類: identity_evidence_only / can_global_index False",
          c["role"] == "identity_evidence_only" and c["can_global_index"] is False
          and c["matter_link_required"] is True and c["confidentiality_class"] == "lawyer_client_confidential")

    print()
    if fails:
        print(f"RESULT: FAIL ({len(fails)}): {fails}")
        return 1
    print("RESULT: PASS (jufu: identity evidence可・global出口全拒否・matter内は認可閲覧のみ green)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
