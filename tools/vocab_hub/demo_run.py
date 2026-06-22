#!/usr/bin/env python3
"""語彙Hub構築 dry-run デモ: synthetic 辞書ゴールドで回し artifacts/ へ report.
実データ(Box: 有斐閣 staging v3 / 学陽 v0.2)へ向ける手順は RUNBOOK.md.
"""
import json
import tempfile
from pathlib import Path

import build_hub_dryrun as bh

REPO = Path(__file__).resolve().parents[2]
ARTIFACTS = REPO / "artifacts"


def main() -> int:
    ARTIFACTS.mkdir(exist_ok=True)
    terms = [
        # 占有: 有斐閣+学陽 同義 -> exact merge
        {"term_id": "y_senyu", "scheme_id": "yuhikaku", "authority_rank": 101,
         "normalized_pref": "占有", "reading": "せんゆう", "definition": "物を事実上支配すること", "term_tier": 1},
        {"term_id": "h_senyu", "scheme_id": "hourei", "authority_rank": 102,
         "normalized_pref": "占有", "reading": "せんゆう", "definition": "物を事実上支配する状態", "term_tier": 1},
        # 債権: e-Gov anchor
        {"term_id": "e_saiken", "scheme_id": "egov", "authority_rank": 100,
         "normalized_pref": "債権", "reading": "さいけん", "definition": "特定人に給付を請求する権利", "term_tier": 1},
        {"term_id": "y_saiken", "scheme_id": "yuhikaku", "authority_rank": 101,
         "normalized_pref": "債権", "reading": "さいけん", "definition": "特定人に給付を請求しうる権利", "term_tier": 1},
        # 遺言: reading 違い -> 別hub
        {"term_id": "y_yuigon", "scheme_id": "yuhikaku", "authority_rank": 101,
         "normalized_pref": "遺言", "reading": "ゆいごん", "definition": "一般的な言い残し", "term_tier": 1},
        {"term_id": "y_igon", "scheme_id": "yuhikaku", "authority_rank": 101,
         "normalized_pref": "遺言", "reading": "いごん", "definition": "民法上の死後の意思表示の方式", "term_tier": 1},
        # 社員: 同key低重なり -> homograph_split
        {"term_id": "y_shain", "scheme_id": "yuhikaku", "authority_rank": 101,
         "normalized_pref": "社員", "reading": "しゃいん", "definition": "会社法上の構成員たる地位", "term_tier": 1},
        {"term_id": "h_shain", "scheme_id": "hourei", "authority_rank": 102,
         "normalized_pref": "社員", "reading": "しゃいん", "definition": "労働者一般を指す日常語", "term_tier": 1},
        # 持分: 専門辞典(103) attach
        {"term_id": "y_mochibun", "scheme_id": "yuhikaku", "authority_rank": 101,
         "normalized_pref": "持分", "reading": "もちぶん", "definition": "権利の量的部分", "term_tier": 1},
        {"term_id": "f_mochibun", "scheme_id": "fudosan", "authority_rank": 103,
         "normalized_pref": "持分", "reading": "もちぶん", "definition": "共有不動産の所有割合", "term_tier": 1},
    ]
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        with (d / "terms.jsonl").open("w", encoding="utf-8") as fh:
            for t in terms:
                fh.write(json.dumps(t, ensure_ascii=False) + "\n")
        bh.main(["--terms", str(d / "terms.jsonl"), "--out", str(d / "out")])
        (ARTIFACTS / "DEMO_vocab_hub_build_report.md").write_text(
            (d / "out" / "hub_build_report.md").read_text(encoding="utf-8"), encoding="utf-8")
    print(f"[demo] report -> {ARTIFACTS}/DEMO_vocab_hub_build_report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
