"""床チェックの横断有効性スイープ (stdlib のみ・オフライン).

複数手続について、会社法の条文各号(=記載事項の床)を取得済み XML から抽出し、床チェックの
機械的有効性を測る:
  - n各号   : 抽出できた法定記載事項の数(構造抽出が効くか)
  - recall  : 各号を1つずつ落として『欠落』として検出できた割合(検出が効くか)
  - 要alias : 名称が長く(括弧/条件節)短縮 alias が機械生成できない号の数
              = 実務書面の口語表現と素では当たらず、curation(別名整備)が要る号(募集株式199①で実証)

実prose の照合精度そのものは alias curation 後に決まる(本スイープは抽出+検出の機構と、curation 必要量
を測る)。実 prose での合否は examples/(文例33型 等)で別途確認済み。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from egov_fetch import parse_items  # noqa: E402
from requirement_floor import check_against_statute  # noqa: E402

XML = (ROOT / "pipeline" / "egov_raw" / "417AC0000000086.xml").read_text(encoding="utf-8")

TARGETS = [
    ("27", None, "定款の絶対的記載事項(設立)"),
    ("199", "1", "募集株式の募集事項"),
    ("238", "1", "募集新株予約権の募集事項"),
    ("676", None, "募集社債に関する事項"),
    ("749", "1", "吸収合併契約(存続株式会社)"),
    ("763", "1", "新設分割計画"),
    ("768", "1", "株式交換契約(完全親会社)"),
    ("773", "1", "株式移転計画"),
    ("911", "3", "設立の登記事項"),
    ("744", "1", "組織変更計画(持分→株式)"),
]


def sweep_one(art: str, para: str | None, label: str) -> dict:
    items = parse_items(XML, article=art, paragraph=para)
    canon = [{"号": it["号"], "名称": it["名称"], "aliases": it["aliases"]} for it in items]
    n = len(canon)
    # detection recall: 各号を1つずつ落として、その号が欠落検出されるか。
    caught = 0
    for i in range(n):
        draft = "／".join(c["名称"] for j, c in enumerate(canon) if j != i)
        miss = {m["号"] for m in check_against_statute(draft, canon)["missing"]}
        if canon[i]["号"] in miss:
            caught += 1
    # 要alias: 長名称かつ短縮 alias 無し → 実prose照合に curation が要る号。
    need = sum(1 for c in canon if not c["aliases"] and len(c["名称"]) > 14)
    return {"label": label, "art": art, "para": para, "n": n,
            "recall": caught / n if n else 0.0, "need_alias": need}


def main() -> int:
    rows = [sweep_one(*t) for t in TARGETS]
    print(f"{'条':>5} {'各号':>3} {'検出recall':>9} {'要alias':>7}  手続")
    tot_n = tot_caught = tot_need = 0
    for r in rows:
        c = f"{r['art']}{('①②③④⑤⑥'[int(r['para'])-1]) if r['para'] else ''}"
        print(f"{c:>5} {r['n']:>3} {r['recall']*100:>7.0f}% {r['need_alias']:>5}/{r['n']:<2} {r['label']}")
        tot_n += r["n"]; tot_caught += round(r["recall"] * r["n"]); tot_need += r["need_alias"]
    print(f"\n合計 {len(rows)}手続 / 各号 {tot_n} / 検出 {tot_caught}/{tot_n}"
          f"({tot_caught/tot_n*100:.0f}%) / 要alias {tot_need}/{tot_n}({tot_need/tot_n*100:.0f}%)")
    print("読み方: 検出=機械的に欠落を撃てる割合(高いほど良) / 要alias=実prose照合に別名整備が要る号(curation 対象)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
