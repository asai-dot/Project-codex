"""e-Gov 法令API 各号取得 — 条文各号を law/article/item anchor として read-only 取得 (stdlib のみ).

設計思想: docs/dd_doctrine.md §5（記載事項の床）の **top-down 正準リスト** を、
e-Gov 法令データから機械取得する。`requirement_floor.py --canonical` の入力源。

GPT お目付け (20260619 DDPROGRESS_PASS_WITH_NOTES §5/§4) の指示:
  「`requirement_floor` 用の e-Gov 各号取得は、law/article/item anchor として再利用可能であり
    read-only なら並行着手可。ただし、未確定 procedure ID への canonical mapping、floor accepted化、
    DB write は HOLD。」

⇒ 本ツールの境界（厳守）:
  - **read-only**: HTTP GET のみ。DB write もファイル正本化もしない。
  - **L0 observation**: 取り出すのは raw な item anchor（条/項/号 + 本文）。procedure へ紐付けない。
  - **floor accepted化しない**: ここで出るのは「条文各号の生 anchor」。法定の床への昇格は
    requirement_floor の N書式収束 + owner ratify を経る別工程（HOLD）。

巨人の肩(dd_doctrine): 法令構造そのもの(各号の区切り)は e-Gov 正本を **consume** する。
我々は last-mile（anchor 正規化・raw 保存・床ツールへの受け渡し）だけを担う。

使い方:
  # offline: 取得済み/fixture の法令XMLから各号 anchor を抽出（本 session はこちら）
  python scripts/egov_fetch.py --from-file law.xml --article 199 --paragraph 1
  # online: e-Gov から read-only 取得し raw 保存（要・outbound 許可の実行環境）
  python scripts/egov_fetch.py --law-id 405AC0000000086 --article 199 --paragraph 1 \
      --raw-dir pipeline/egov_raw --out pipeline/egov_raw/kaishaho_199_1.anchors.json
"""

from __future__ import annotations

import argparse
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

# e-Gov 法令API v2 の法令データ取得。read-only(GET) のみに使う。
EGOV_API_V2 = "https://laws.e-gov.go.jp/api/2/law_data/{law_id}"
SOURCE_LABEL = "e-Gov 法令API"
LAYER = "L0_observation"  # 生 anchor。床として accepted ではない(HOLD)。


def build_url(law_id: str) -> str:
    return EGOV_API_V2.format(law_id=law_id)


def fetch_raw(law_id: str, *, timeout: int = 30, url: str | None = None) -> bytes:
    """e-Gov から法令データを read-only 取得して生バイトを返す（GET のみ）。"""
    target = url or build_url(law_id)
    req = urllib.request.Request(target, headers={"User-Agent": "project-codex/egov_fetch (read-only)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (固定の e-Gov ドメイン)
        return resp.read()


def extract_law_xml(raw: bytes) -> str:
    """応答(XML 直 or JSON 包み)から法令標準XML 文字列を取り出す。

    e-Gov の版差(JSON 包み / XML 直) を吸収。JSON なら中の '<Law'/'<Article' を含む文字列を拾う。
    """
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            return text

        def _find(o: object) -> str | None:
            if isinstance(o, str):
                return o if ("<Law" in o or "<Article" in o) else None
            if isinstance(o, dict):
                for v in o.values():
                    if (hit := _find(v)) is not None:
                        return hit
            if isinstance(o, list):
                for v in o:
                    if (hit := _find(v)) is not None:
                        return hit
            return None

        return _find(obj) or text
    return text


def _text(el: ET.Element | None) -> str:
    """要素配下の全テキストを連結（タグ無視・空白圧縮）。"""
    if el is None:
        return ""
    return "".join(el.itertext()).strip()


def _law_num(root: ET.Element) -> str:
    ln = root.find(".//LawNum")
    return _text(ln) if ln is not None else (root.attrib.get("Num", ""))


def parse_items(xml_text: str, *, law_id: str = "", article: str | None = None,
                paragraph: str | None = None) -> list[dict]:
    """法令標準XML から各号(Item)を anchor として抽出。

    article/paragraph を与えると Num 属性で絞り込む。返すのは床ではなく **生 anchor**(L0)。
    requirement_floor が consume する形 (id/名称/号/aliases) に raw text を載せる。
    """
    root = ET.fromstring(xml_text)
    law_num = _law_num(root)
    key = law_id or law_num or "unknown_law"
    retrieved = datetime.now(timezone.utc).isoformat(timespec="seconds")

    anchors: list[dict] = []
    for art in root.iter("Article"):
        anum = art.attrib.get("Num", "")
        if article is not None and str(anum) != str(article):
            continue
        art_caption = _text(art.find("ArticleCaption"))
        for para in art.iter("Paragraph"):
            pnum = para.attrib.get("Num", "")
            if paragraph is not None and str(pnum) != str(paragraph):
                continue
            for item in para.iter("Item"):
                inum = item.attrib.get("Num", "")
                go = _text(item.find("ItemTitle"))
                body = _text(item.find("ItemSentence"))
                anchors.append({
                    "id": f"{key}/a{anum}/p{pnum}/i{inum}",
                    "law_id": law_id, "law_num": law_num,
                    "article": anum, "paragraph": pnum, "号": go,
                    "anchor": f"{(_text(root.find('.//LawTitle')) or key)}{anum}条"
                              + (f"{pnum}項" if pnum else "") + f"{go}号",
                    "article_caption": art_caption,
                    "名称": body,          # 生の号本文。短縮名/aliases は owner curation(別工程)。
                    "text": body,
                    "aliases": [],
                    "source": SOURCE_LABEL, "retrieved_at": retrieved,
                    "layer": LAYER, "status": "observed",
                })
    return anchors


def save_raw(raw: bytes, raw_dir: Path, law_id: str) -> Path:
    """取得した生バイトをそのまま保存（raw 保存。改変しない）。"""
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{law_id or 'law'}.xml"
    path.write_bytes(raw)
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="e-Gov 条文各号の read-only 取得 / anchor 抽出")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--law-id", help="e-Gov 法令ID (例 会社法=405AC0000000086)。online 取得")
    src.add_argument("--from-file", help="取得済み/fixture の法令XML を parse (offline)")
    ap.add_argument("--url", help="取得URLを明示上書き (版差対応・read-only)")
    ap.add_argument("--article", help="条番号で絞り込み (例 199)")
    ap.add_argument("--paragraph", help="項番号で絞り込み (例 1)")
    ap.add_argument("--raw-dir", help="online 取得時の raw 保存先 (例 pipeline/egov_raw)")
    ap.add_argument("--out", help="anchor JSON の出力先。未指定なら標準出力に要約")
    args = ap.parse_args(argv)

    if args.from_file:
        raw = Path(args.from_file).read_bytes()
        law_id = ""
    else:
        raw = fetch_raw(args.law_id, url=args.url)
        law_id = args.law_id
        if args.raw_dir:
            saved = save_raw(raw, Path(args.raw_dir), law_id)
            print(f"raw 保存: {saved} ({len(raw)} bytes)")

    xml_text = extract_law_xml(raw)
    anchors = parse_items(xml_text, law_id=law_id, article=args.article, paragraph=args.paragraph)

    print(f"各号 anchor {len(anchors)}件 (L0 observation / 床ではない)"
          + (f" @ {args.article}条{args.paragraph or ''}項" if args.article else ""))
    for a in anchors:
        print(f"    [{a['号']}号] {a['名称'][:48]}  <{a['id']}>")

    if args.out:
        payload = {"layer": LAYER, "source": SOURCE_LABEL,
                   "_comment": "条文各号の生 anchor(read-only)。procedure 紐付け/floor accepted化は HOLD。",
                   "items": anchors}
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"anchor JSON 出力: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
