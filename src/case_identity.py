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

既存の判例参照資産への合わせ込み:
- 最高裁OPACパーサ `opac_parse.py` が `case_ref_text`（略記形『最大判昭44.11.26民集23-11-2150』『東京高判…』）を
  既に抽出済。OPAC/CiNii の case_citations は 17,259件、`opac_cinii_bib_docket_keys.docket_raw` に docket(事件番号)を保持。
- ただし**正本キーは未整備**（docket_raw は生文字列止まり）。本モジュールの `normalize_case_ref()` が
  この略記形を食って canonical_key / case_node_id を与える＝既存17,259件と bencom precedents を同じ正本に名寄せできる。
- D1KOS/OPAC-CiNii の `article_cites_case` レーンと規律一致（claim_scope=cites / pending_review / reject_not_same_case）。
"""
import re
import unicodedata

# 和暦 → 西暦: seireki = base + 年（元年=1）
ERA_BASE = {"明治": 1867, "大正": 1911, "昭和": 1925, "平成": 1988, "令和": 2018}
ERA_ABBR = {"明": "明治", "大": "大正", "昭": "昭和", "平": "平成", "令": "令和"}
# 判例集・雑誌の略記（OPAC/CiNii の case_ref に頻出）
REPORTER_RE = re.compile(r"(民集|刑集|集民|集刑|裁時|判時|判タ|家月|金法|金判|労判|訟月|行集|高刑集|下民集)\s*[\d‐–－・\-]+")

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
    """『昭和44年5月19日』『昭44.5.19』『平20・3・1』→ '1969-05-19' 等。失敗時 None。"""
    s = _nfkc(s)
    m = re.search(r"(明治|大正|昭和|平成|令和)\s*(元|\d+)\s*年\s*(\d+)\s*月\s*(\d+)\s*日", s)
    if m:
        era, y, mo, d = m.group(1), _parse_year_token(m.group(2)), int(m.group(3)), int(m.group(4))
        sy = to_seireki(era, y)
        return f"{sy:04d}-{mo:02d}-{d:02d}" if sy else None
    # 略記・点区切り: 昭44.5.19 / 平20・3・1 / 令1/5/1
    m = re.search(r"(明|大|昭|平|令)\s*(元|\d+)\s*[.・/]\s*(\d+)\s*[.・/]\s*(\d+)", s)
    if m:
        era = ERA_ABBR[m.group(1)]
        y, mo, d = _parse_year_token(m.group(2)), int(m.group(3)), int(m.group(4))
        sy = to_seireki(era, y)
        return f"{sy:04d}-{mo:02d}-{d:02d}" if sy else None
    return None


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


_ABBR_TYPE = {"高": "高等裁判所", "地": "地方裁判所", "家": "家庭裁判所", "簡": "簡易裁判所"}


def parse_court_abbrev(token):
    """略記の裁判所（『最大判』『東京高判』『大阪地決』『福岡家審』）→ parse_court と同形式。
    OPAC/CiNii の case_ref_text の形式。失敗時 None。"""
    t = _nfkc(token)
    if t.startswith("最"):
        bench = "大法廷" if "大" in t[:3] else ("小法廷" if "小" in t[:3] else None)
        return {"name": "最高裁判所", "level": "supreme", "detail_variant": 2,
                "court_slug": "saikosai", "bench": bench, "division": None}
    m = re.match(r"(.+?)([高地家簡])[判決審]", t)
    if m:
        return parse_court(m.group(1) + _ABBR_TYPE[m.group(2)])
    return None


# 略記の判例参照を1つ捕捉（court略記 + 日付。和暦はフル『昭和44年5月19日』も略記『昭44.11.26』も可）
CASE_REF_RE = re.compile(
    r"(最(?:大|小|第[一二三])?[判決]|[^\s\d、。，,]{2,5}?[高地家簡][判決審])"
    r"[\s,，、]*"
    r"((?:明治|大正|昭和|平成|令和|明|大|昭|平|令)\s*(?:元|\d+)\s*年?[\s.・/]*\d+\s*月?[\s.・/]*\d+\s*日?)"
)


def normalize_case_ref(text, hh_id=None, court_id=None):
    """OPAC/CiNii の case_ref_text（略記の判例参照）→ 正本レコード。
    例 『最大判昭44.11.26民集23-11-2150』『東京高判昭和44年5月19日』。
    事件番号が無い略記でも、court+判決日+判例集citation で正本キーを作る。"""
    t = _nfkc(text)
    m = CASE_REF_RE.search(t)
    if not m:
        return None
    court = parse_court_abbrev(m.group(1))
    judged_on = parse_date(m.group(2))
    rm = REPORTER_RE.search(t)
    reporter = rm.group(0).strip() if rm else None
    if not court or not judged_on:
        return None
    # 事件番号があれば優先、無ければ判例集citationを識別子に
    cn = parse_case_number(t)
    ident = cn["normalized"] if cn else (reporter or "na")
    canonical_key = f"{court['court_slug']}|{judged_on}|{ident}"
    return {
        "case_node_id": f"alo:case:{court['court_slug']}:{judged_on}:{ident}",
        "canonical_key": canonical_key,
        "court": court["name"], "court_slug": court["court_slug"], "court_level": court["level"],
        "detail_variant": court["detail_variant"], "bench": court["bench"], "division": None,
        "judged_on": judged_on, "case_number": cn, "case_number_text": cn["normalized"] if cn else None,
        "reporter": reporter, "ref_text": text.strip(), "hh_id": hh_id, "court_id": court_id,
    }


# 改良版・本文からの判例参照抽出（地名を保持＝opac_parse の抽出regex欠陥を上流回避）
# opac_parse は `高[裁判]` 始まりで地名(東京)を捨てていた。ここは place(漢字2-4)+(高|地|家|簡)+判決審 を保持。
EXTRACT_RE = re.compile(
    r"("
    r"最(?:大|小)?[判決]"                        # 最判/最決/最大判/最大決（最高裁は地名不要）
    r"|[一-龥]{2,4}(?:高|地|家|簡)(?:判|決|審)"    # 東京高判/大阪地判/福岡家審 …（地名を保持）
    r")"
    r"[\s,，、]*"
    r"((?:明治|大正|昭和|平成|令和|明|大|昭|平|令)\s*(?:元|\d+)\s*年?[\s.・/]*\d+\s*[月.・/]*\s*\d+\s*日?)"  # 判決日
    r"(\s*(?:民集|刑集|集民|集刑|裁時|判時|判タ|家月|金法|金判|労判|訟月|行集)\s*[\d‐–－・\-]+)?"           # 判例集citation(任意)
)


def extract_case_refs(text):
    """本文/記事テキストから判例参照を抽出（地名込み）。returns list[str]。
    opac_parse.py の case_ref_text が下級審の地名を落としていた問題を、raw_text からの再抽出で回避する。"""
    if not text:
        return []
    t = _nfkc(text)
    return [(m.group(1) + m.group(2) + (m.group(3) or "")).strip() for m in EXTRACT_RE.finditer(t)]


def normalize_text(text, **kw):
    """テキストから判例参照を抽出し、各々を正本レコードへ。returns list[record]。"""
    out = []
    for ref in extract_case_refs(text):
        rec = normalize_case_ref(ref, **kw)
        if rec:
            out.append(rec)
    return out


if __name__ == "__main__":
    import json, sys
