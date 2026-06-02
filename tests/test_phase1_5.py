#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic tests for phase1_5_parse_md.py and cross_reference_web.py.

Runs offline (no network, no Box, no real md). Uses a synthetic md fixture that
models the structures called out in the handoff: ## / ### headwords, non-entry
headings (kana, numbered section, structural), page markers, an index page to be
dropped, a truncated definition, and an OCR citation-concat error.

Usage: python3 tests/test_phase1_5.py
"""
import json
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARSE = os.path.join(REPO, "phases", "phase1_5_parse_md.py")
XREF = os.path.join(REPO, "phases", "cross_reference_web.py")

SAMPLE_MD = """<!-- page:001 -->
## あ
（五十音見出し。非エントリ）

## 1．用語の選定
本辞典の用語選定方針。非エントリ節。

## 凡例
記号の説明。非エントリ構造見出し。

## 勘案（かんあん）
いろいろの事情を考え合わせること。地方自治法施行令150に例がある。

<!-- page:002 -->
### 売渡し
売買行為の一種。地方自治法施行令167の3に規定。

### きんこ
<!-- page:189 -->
昭和38年政令306号による。予算決算及び会計令5710も参照。

<!-- page:815 -->
## 渡船（とせん）
索引ページ(p815以降)由来の見出し。語名は通常だがページ規則で除外されるべき。
"""

PASS = 0
FAIL = 0


def check(desc, cond):
    global PASS, FAIL
    if cond:
        print(f"PASS: {desc}")
        PASS += 1
    else:
        print(f"FAIL: {desc}")
        FAIL += 1


def main():
    with tempfile.TemporaryDirectory() as d:
        md = os.path.join(d, "sample.md")
        out = os.path.join(d, "all_entries.jsonl")
        with open(md, "w", encoding="utf-8") as fh:
            fh.write(SAMPLE_MD)

        # expected disabled (small fixture) -> rc 0 unless io error
        r = subprocess.run([sys.executable, PARSE, md, out, "--expected", "0"],
                           capture_output=True, text=True)
        print(r.stderr)
        check("parser exit 0", r.returncode == 0)

        entries = [json.loads(x) for x in open(out, encoding="utf-8") if x.strip()]
        hws = [e["headword"] for e in entries]

        check("3 real entries kept (勘案/売渡し/きんこ)", len(entries) == 3)
        check("kana heading 'あ' excluded", "あ" not in hws)
        check("numbered section excluded", "1．用語の選定" not in hws)
        check("structural '凡例' excluded", "凡例" not in hws)
        check("index page entry dropped by page rule (>=815)",
              "渡船" not in hws and "dropped(index>=p)     : 1" in r.stderr)
        check("reading split: 勘案/かんあん",
              any(e["headword"] == "勘案" and e["reading"] == "かんあん" for e in entries))
        check("source_page assigned (勘案=1)",
              any(e["headword"] == "勘案" and e["source_page"] == 1 for e in entries))
        check("売渡し on page 2",
              any(e["headword"] == "売渡し" and e["source_page"] == 2 for e in entries))
        # きんこ: short definition + next has no next -> not flagged truncated here,
        # but definition should be captured across the inner page marker
        kinko = next(e for e in entries if e["headword"] == "きんこ")
        check("きんこ definition captured", "政令306号" in kinko["definition"])

        # cross-reference: corrected semantics — all citations are LINK candidates;
        # only 4+digit runs are collapse suspects; 3-digit (政令306号) is NOT an error.
        corr = os.path.join(d, "xref.jsonl")
        r2 = subprocess.run([sys.executable, XREF, out, corr],
                            capture_output=True, text=True)
        print(r2.stderr)
        check("xref exit 0", r2.returncode == 0)
        findings = [json.loads(x) for x in open(corr, encoding="utf-8") if x.strip()]
        susp = [s for c in findings for s in c["collapse_suspects"]]
        links = [l for c in findings for l in c["citation_link_candidates"]]
        check("3-digit 令306 is NOT a collapse suspect (regression for the 129-myth)",
              not any("306" in s["num"] for s in susp))
        check("4-digit 令5710 IS a collapse suspect",
              any(s["num"] == "5710" for s in susp))
        check("citations surfaced as LINK candidates (令306/施行令167…)",
              len(links) >= 2)
        check("nothing is marked auto_fix",
              all(s.get("auto_fix") is False for s in susp))

    print(f"\n=== test summary: {PASS} passed, {FAIL} failed ===")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
