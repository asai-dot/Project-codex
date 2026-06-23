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
  python scripts/egov_fetch.py --law-id 417AC0000000086 --article 199 --paragraph 1 \
      --raw-dir pipeline/egov_raw --out pipeline/egov_raw/kaishaho_199_1.anchors.json
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

# e-Gov 法令API。v1 lawdata は 法令標準XML(<DataRoot>…<LawFullText><Law>)を直接返すため、
# ElementTree でそのまま各号を抽出できる(v2 /law_data は構造化 JSON で別パーサが要る)。read-only(GET)のみ。
EGOV_API = "https://laws.e-gov.go.jp/api/1/lawdata/{law_id}"
SOURCE_LABEL = "e-Gov 法令API v1 (lawdata)"
LAYER = "L0_observation"  # 生 anchor。床として accepted ではない(HOLD)。


def build_url(law_id: str) -> str:
    return EGOV_API.format(law_id=law_id)


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


_PAREN = re.compile(r"[（(][^（）()]*[）)]")


def derive_alias(text: str, *, max_len: int = 24) -> str | None:
    """号本文から短縮名 alias 候補を機械生成（last-mile 正規化・authoring ではない）。

    各号は「<短い名称>（<定義・読替>）」型が多い。**定義括弧を剥いた残り**が短ければ、書式の
    短語と突合できる alias 候補になる(例「募集株式の数（種類株式…）」→「募集株式の数」)。
    括弧の無い条件節型(例「金銭以外の財産を…ときは、…」)は短縮できないので None(=curation 対象)。
    名称(raw)は一切変えない。aliases に候補を足すだけ。
    """
    prev, s = None, text
    while prev != s:                 # 入れ子括弧も剥く
        prev, s = s, _PAREN.sub("", s)
    s = s.strip("、。 　　")
    return s if (s and s != text and len(s) <= max_len) else None


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
                    "名称": body,          # 生の号本文(raw・不変)。
                    "text": body,
                    # 定義括弧を剥いた短縮名を alias 候補に(機械正規化)。残りは owner curation。
                    "aliases": [a] if (a := derive_alias(body)) else [],
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


def run_targets(targets: list[dict], *, raw_dir: Path, out_dir: Path,
                fetch_fn=fetch_raw) -> list[dict]:
    """対象リストを一括 read-only 取得 → raw 保存 + anchor JSON 出力。

    targets: [{"law_id","article"?,"paragraph"?,"out"?,"url"?}, ...]
    fetch_fn は live 取得関数（テスト時はオフライン注入可）。許可された outbound 環境で回す想定。
    返り値: 各対象の {law_id, n_anchors, raw, out}。
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    for t in targets:
        law_id = t["law_id"]
        raw = fetch_fn(law_id, url=t.get("url"))
        raw_path = save_raw(raw, raw_dir, law_id)
        anchors = parse_items(extract_law_xml(raw), law_id=law_id,
                              article=t.get("article"), paragraph=t.get("paragraph"))
        out_name = t.get("out") or f"{law_id}_a{t.get('article','')}_p{t.get('paragraph','')}.anchors.json"
        out_path = out_dir / out_name
        out_path.write_text(json.dumps(
            {"layer": LAYER, "source": SOURCE_LABEL,
             "_comment": "条文各号の生 anchor(read-only)。procedure 紐付け/floor accepted化は HOLD。",
             "items": anchors}, ensure_ascii=False, indent=2), encoding="utf-8")
        results.append({"law_id": law_id, "n_anchors": len(anchors),
                        "raw": str(raw_path), "out": str(out_path)})
    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="e-Gov 条文各号の read-only 取得 / anchor 抽出")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--law-id", help="e-Gov 法令ID (例 会社法=417AC0000000086)。online 取得")
    src.add_argument("--from-file", help="取得済み/fixture の法令XML を parse (offline)")
    src.add_argument("--targets", help="対象リスト JSON で一括 read-only 取得 (許可環境で)")
    ap.add_argument("--url", help="取得URLを明示上書き (版差対応・read-only)")
    ap.add_argument("--article", help="条番号で絞り込み (例 199)")
    ap.add_argument("--paragraph", help="項番号で絞り込み (例 1)")
    ap.add_argument("--raw-dir", help="raw 保存先 (例 pipeline/egov_raw)")
    ap.add_argument("--out", help="anchor JSON の出力先。未指定なら標準出力に要約")
    args = ap.parse_args(argv)

    if args.targets:
        spec = json.loads(Path(args.targets).read_text(encoding="utf-8"))
        targets = spec if isinstance(spec, list) else spec.get("targets", [])
        raw_dir = Path(args.raw_dir) if args.raw_dir else Path(args.targets).resolve().parent
        out_dir = Path(args.out) if args.out else raw_dir
        res = run_targets(targets, raw_dir=raw_dir, out_dir=out_dir)
        for r in res:
            print(f"  {r['law_id']}: 各号 {r['n_anchors']}件 → {r['out']} (raw {r['raw']})")
        print(f"完了: {len(res)}件取得 (read-only / L0 observation)")
        return 0

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
