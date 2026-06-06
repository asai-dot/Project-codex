#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
case_deeplink.py — 判例の着地解決（deeplink.js の思想を判例に適用）

正規化済み判例 + 文脈（引用元の cid/viewer_page 等）から、着地先URLを
優先順（内部PD→裁判所HTML→ベンコムオンランプ）で解決する。

config/case_sources.json の各 source は `requires`（必要キー）と `url_template` を持つ。
必要キーが揃うものだけ着地候補になり、priority昇順で返す。
"""
import json
import re
from pathlib import Path

_CFG = Path(__file__).resolve().parents[1] / "config" / "case_sources.json"


def load_sources(path=None):
    data = json.loads(Path(path or _CFG).read_text(encoding="utf-8"))
    return sorted(data.get("sources", []), key=lambda s: s.get("priority", 99))


def _fill(template, vars):
    def repl(m):
        k = m.group(1)
        return str(vars[k]) if k in vars and vars[k] is not None else m.group(0)
    return re.sub(r"\{(\w+)\}", repl, template)


def _has(vars, key):
    if key.startswith("has_"):
        return bool(vars.get(key))
    return vars.get(key) not in (None, "", [])


def resolve_case(case, context=None, sources=None):
    """
    case    : normalize_citation() の出力（court_id / detail_variant / has_internal_pd 等を含み得る）
    context : 引用元の文脈（cid, viewer_page 等。オンランプ用）
    返り値  : 着地候補のリスト（優先順）。各要素 {source_id, label, tier, url, needs_auth}
    """
    sources = sources if sources is not None else load_sources()
    vars = dict(case or {})
    if context:
        vars.update(context)
    out = []
    for s in sources:
        req = s.get("requires", [])
        if not all(_has(vars, k) for k in req):
            continue
        url = _fill(s["url_template"], vars)
        if re.search(r"\{\w+\}", url):   # 未解決プレースホルダが残る→不可
            continue
        out.append({
            "source_id": s["id"], "label": s["label"], "tier": s.get("tier"),
            "url": url, "needs_auth": bool(s.get("needs_auth")),
            "priority": s.get("priority", 99),
        })
    return out


def best_landing(case, context=None, sources=None):
    """最優先の着地1件（無ければ None）。"""
    cands = resolve_case(case, context, sources)
    return cands[0] if cands else None
