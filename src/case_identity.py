#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
case_identity.py — 判例の同定（正規化＋正本キー）

ベンコム引用判例リンク等から採取した判例引用（裁判所名・和暦判決日・事件番号）を、
case_spine 名寄せ用の正本キーに正規化する。判例レーンの心臓部。

入力例（コンメンタール民訴III p.43 の引用判例）:
  court="東京高等裁判所", date="昭和44年5月19日", caseno="昭和41年（ネ）第2780号"
出力:
  {court_slug, court_level, detail_variant, judged_on, case_number{...},
   canonical_key, case_node_id}

依存なし（stdlibのみ）。alo-kg(Python) と地続きに使える。

既存ALO資産との関係（重要）:
- 判例の**正本キーはALOにまだ無い**（裁判所マスタ・事件番号の素材はあるが未正規化）。本モジュールがその正本キーを提供する。
- 事務所自身の係属事件は leala `JurisdictionCourt`（`leala__CaseNo__c`=事件番号 / `leala__CourtName__c`=裁判所＋部）に
  構造化済。これを本モジュールで正規化すれば、**事務所の事件＝内部PD判決文**を判例グラフに接続できる（着地①の供給源）。
- 部・係（例「民事部3B」）は判例の同定（裁判所＋判決日＋事件番号）に含めず division として分離保持。
"""
import re
import unicodedata

# 和暦 → 西暦: seireki = base + 年（元年=1）
ERA_BASE = {"明治": 1867, "大正": 1911, "昭和": 1925, "平成": 1988, "令和": 2018}

# 裁判所 → (level, courts.go.jp detail variant, 固定slug, 種別romaji接尾辞)
# detail2=最高裁 / detail4=下級審(高裁・地裁・家裁) / detail7=知財高裁（variantは要最終確認）
COURT_RULES = [
    ("知的財産高等裁判所", "ip_high", 7, "chizai-koto", None),
    ("最高裁判所", "supreme", 2, "saikosai", None),
    ("高等裁判所", "high", 4, None, "koto"),     # slug は地名(romaji)+種別
    ("地方裁判所", "district", 4, None, "chiho"),
    ("家庭裁判所", "family", 4, None, "katei"),
    ("簡易裁判所", "summary", 4, None, "kani"),
]

ZEN2HAN = str.maketrans("０１２３４５６７８９", "0123456789")


def _nfkc(s):
    return unicodedata.normalize("NFKC", s or "").strip()


def to_seireki(era, year):
    base = ERA_BASE.get(era)
    if base is None:
        return None
    return base + int(year)


def _parse_year_token(tok):
    """『元』→1, 『２３』→23 など。"""
    tok = tok.translate(ZEN2HAN).strip()
    if tok in ("元", "元年"):
        return 1
    m = re.search(r"\d+", tok)
    return int(m.group()) if m else None


def parse_date(s):
    """『昭和44年5月19日』→ '1969-05-19'。失敗時 None。"""
    s = _nfkc(s)
    m = re.search(r"(明治|大正|昭和|平成|令和)\s*(元|\d+)\s*年\s*(\d+)\s*月\s*(\d+)\s*日", s)
    if not m:
        return None
    era, y, mo, d = m.group(1), _parse_year_token(m.group(2)), int(m.group(3)), int(m.group(4))
    sy = to_seireki(era, y)
    if sy is None:
        return None
    return f"{sy:04d}-{mo:02d}-{d:02d}"


def parse_case_number(s):
    """『昭和41年（ネ）第2780号』→ 構造化。"""
    s = _nfkc(s)
    # 全角括弧→半角はNFKCで済むが符号ゆれに両対応
    m = re.search(r"(明治|大正|昭和|平成|令和)?\s*(元|\d+)\s*年\s*[（(]\s*([^）)]+?)\s*[）)]\s*第?\s*(\d+)\s*号", s)
    if not m:
        return None
    era = m.group(1) or ""
    year = _parse_year_token(m.group(2))
    mark = m.group(3).strip()
    number = int(m.group(4))
    seireki = to_seireki(era, year) if era else None
    normalized = f"{era}{year}（{mark}）{number}号" if era else f"{year}（{mark}）{number}号"
    return {
        "era": era, "year": year, "seireki_year": seireki,
        "mark": mark, "number": number, "normalized": normalized,
    }


def parse_court(s):
    """裁判所名 → {name, level, detail_variant, court_slug, bench, division}。
    『奈良地方裁判所　民事部３B』のような部・係（leala係属事件の形式）にも対応。
    部・係は court_slug/正本キーには入れない（判例の同定は 裁判所＋判決日＋事件番号）。"""
    raw = _nfkc(s)
    bench = None
    bm = re.search(r"(大法廷|第[一二三]小法廷)", raw)
    if bm:
        bench = bm.group(1)
    name = re.sub(r"(大法廷|第[一二三]小法廷|判決|決定|命令)", "", raw).strip()
    for needle, level, variant, slug, type_ro in COURT_RULES:
        idx = name.find(needle)
        if idx >= 0:
            place = name[:idx].strip()                       # 地名（needleの前）
            division = name[idx + len(needle):].strip() or None  # 部・係・支部（needleの後）
            court_name = (place + needle).strip()
            if slug is None:
                slug = _place_slug(place) + "-" + type_ro    # 例 nara-chiho
            return {"name": court_name, "level": level, "detail_variant": variant,
                    "court_slug": slug, "bench": bench, "division": division}
    return {"name": name, "level": "unknown", "detail_variant": 4,
            "court_slug": _place_slug(name), "bench": bench, "division": None}


_PLACE_ROMAJI = {
    "東京": "tokyo", "大阪": "osaka", "名古屋": "nagoya", "広島": "hiroshima",
    "福岡": "fukuoka", "仙台": "sendai", "札幌": "sapporo", "高松": "takamatsu",
    "京都": "kyoto", "神戸": "kobe", "横浜": "yokohama", "千葉": "chiba",
    "さいたま": "saitama", "奈良": "nara", "大津": "otsu", "金沢": "kanazawa",
    "那覇": "naha", "高松": "takamatsu", "松山": "matsuyama",
}


_PLACE_ROMAJI_LEGACY_REMOVED = True


def _place_slug(place):
    place = place.strip()
    for jp, ro in _PLACE_ROMAJI.items():
        if place.startswith(jp):
            return ro
    # マップ外はそのまま（内部キーなので日本語可）
    return place or "unknown"


def normalize_citation(court, date, caseno, title=None, hh_id=None, court_id=None):
    """採取した1引用を正本レコードに正規化する。"""
    c = parse_court(court) if court else {"court_slug": "unknown", "level": "unknown", "detail_variant": 4, "name": "", "bench": None, "division": None}
    judged_on = parse_date(date) if date else None
    cn = parse_case_number(caseno) if caseno else None
    caseno_norm = cn["normalized"] if cn else (_nfkc(caseno) if caseno else "")
    canonical_key = f"{c['court_slug']}|{judged_on or ''}|{caseno_norm}"
    case_node_id = f"alo:case:{c['court_slug']}:{judged_on or 'na'}:{caseno_norm or 'na'}"
    return {
        "case_node_id": case_node_id,
        "canonical_key": canonical_key,
        "court": c["name"], "court_slug": c["court_slug"], "court_level": c["level"],
        "detail_variant": c["detail_variant"], "bench": c["bench"], "division": c.get("division"),
        "judged_on": judged_on,
        "case_number": cn, "case_number_text": caseno_norm,
        "title": _nfkc(title) if title else None,
        "hh_id": hh_id,          # 判例秘書ID（L+8桁）参考キー
        "court_id": court_id,    # 裁判所 detail?id=（ALO既存メタデータから付与）
    }


if __name__ == "__main__":
    import json, sys
    # デモ: 標準入力に「court | date | caseno」を渡す
    for line in sys.stdin:
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            print(json.dumps(normalize_citation(*parts[:3]), ensure_ascii=False))
