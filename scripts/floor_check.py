"""記載事項の床チェック — 書面ドラフトを条文各号と突合し、法定の抜け漏れを撃つ (stdlib のみ).

実利: 募集株式発行の議事録などのドラフトを、e-Gov 由来の『記載事項の床』(会社法199①各号 等)と
機械照合し、**落とすと無効/却下になる法定記載事項の欠落**を致命傷として検出する。
条件付の号(現物出資 等)は、その語が本文に出た時だけ必須にする(無条件チェックリストにしない)。

使い方:
  python scripts/floor_check.py --canonical pipeline/floor/kaishaho_199_1.canonical.json \
      --draft path/to/議事録.txt
  # .docx 等はテキストに落としてから渡す(本ツールは stdlib のみ・テキスト入力)。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from requirement_floor import check_against_statute


def _load_canonical(path: Path) -> list[dict]:
    d = json.loads(path.read_text(encoding="utf-8"))
    return d if isinstance(d, list) else d.get("items", [])


def run(draft_text: str, canonical: list[dict]) -> dict:
    return check_against_statute(draft_text, canonical)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="記載事項の床チェック(書面ドラフト × 条文各号)")
    ap.add_argument("--canonical", required=True, help="床 JSON (e-Gov 由来 + alias)")
    ap.add_argument("--draft", required=True, help="ドラフト本文(.txt)")
    args = ap.parse_args(argv)

    canonical = _load_canonical(Path(args.canonical))
    res = run(Path(args.draft).read_text(encoding="utf-8"), canonical)

    print(f"=== 記載事項の床チェック: {Path(args.draft).name} ===")
    for r in res["rows"]:
        if not r["required"]:
            mark = "・(条件付・非該当)"
        elif r["present"]:
            mark = "✅ 記載あり"
        else:
            mark = "❌ 欠落"
        cond = "[条件付]" if r["conditional"] else ""
        print(f"  {r['号']}号 {cond} {r['名称']}: {mark}")
    print()
    if res["ok"]:
        print("✅ 法定記載事項(該当する各号)を満たしています。")
    else:
        for r in res["missing"]:
            print(f"❌ 致命傷: {r['号']}号「{r['名称']}」が欠落 — 会社法199条1項{r['号']}号(落とすと無効/却下リスク)")
    return 1 if not res["ok"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
