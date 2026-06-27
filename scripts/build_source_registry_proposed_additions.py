#!/usr/bin/env python3
"""alo_source_registry の proposed additions 生成 (should_fix#1 の欠落10行充足)。

注意: 原本想定41行のうち再構成できたのは31行。残10行の *正確な原本内訳は不明*。
本スクリプトは原本を騙らず、実在する日本の判例/法情報ソースを
`recon_status: proposed_addition_pending_owner_confirm` として候補提示する。
owner / DDCASESOURCE 確認後に正式採用 (status を昇格)。

出口分類は DD-CASE-001 AC-3 と同一ポリシー:
  can_global_index = (confidentiality_default==open) and (redistribution==public)
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs" / "alo_source_registry_proposed_additions_20260620.jsonl"

# (source_system, category, confidentiality_default, redistribution, name)
PROPOSED = [
    ("kakyu-saibansho-hp", "official_court", "open", "public",
     "下級裁判所 裁判例(裁判所HP saibansho.go.jp)"),
    ("chizai-kosai-hp", "official_court", "open", "public",
     "知的財産高等裁判所HP 裁判例"),
    ("shomu-geppo", "official", "open", "restricted",
     "訟務月報(法務省。国の利害関係訴訟)"),
    ("lexdb-tkc", "commercial_caselaw", "open", "commercial_licensed",
     "LEX/DB インターネット(TKC)"),
    ("westlaw-japan", "commercial_caselaw", "open", "commercial_licensed",
     "Westlaw Japan"),
    ("hanrei-jiho", "commercial_lit", "open", "commercial_licensed",
     "判例時報(判例時報社)"),
    ("roudou-hanrei", "commercial_lit", "open", "commercial_licensed",
     "労働判例(産労総合研究所。労働事件 reporter)"),
    ("roukei-soku", "commercial_lit", "open", "commercial_licensed",
     "労働経済判例速報(経団連)"),
    ("kinyu-shoji-hanrei", "commercial_lit", "open", "commercial_licensed",
     "金融・商事判例(経済法令研究会)"),
    ("hanrei-chiho-jichi", "commercial_lit", "open", "commercial_licensed",
     "判例地方自治(ぎょうせい)"),
]


def main():
    rows = []
    for source, cat, conf, redist, name in PROPOSED:
        can_idx = (conf == "open" and redist == "public" and source != "jufu")
        rows.append({
            "source_system": source, "forum_type": "", "name": name,
            "category": cat, "jurisdiction": "",
            "confidentiality_default": conf, "redistribution": redist,
            "can_global_index": can_idx, "seed_source": "proposed_real_sources",
            "recon_status": "proposed_addition_pending_owner_confirm",
            "provenance": "candidate_not_original; real Japanese legal source",
        })
    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    n_idx = sum(1 for r in rows if r["can_global_index"])
    print(f"proposed_additions: {len(rows)} 行 "
          f"(official_public={sum(1 for r in rows if r['redistribution']=='public')}, "
          f"licensed/restricted={sum(1 for r in rows if r['redistribution']!='public')})")
    print(f"  can_global_index=True: {n_idx} (公的HPのみ) / 残りは licensed/restricted ゆえ false")
    print(f"  ※これらは原本10行の復元ではなく candidate。owner 確認で 31→最大41 へ。")
    print(f"出力: {OUT}")


if __name__ == "__main__":
    main()
