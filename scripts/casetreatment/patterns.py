"""Citation regexes and treatment cue inventory for Japanese legal text.

Citation grammar (pragmatic subset, precision-first):
  - court head:   最高裁(判所) / 最大判 / 最判 / 最決 / 大審院 / 東京高裁 /
                  東京高判 / 大阪地判 / 〜家裁 / 〜簡裁 ...
  - era date:     (明治|大正|昭和|平成|令和)N年N月N日
  - bench:        大法廷 / 第[一二三]小法廷
  - disposition:  判決 / 決定
  - reporter:     民集/刑集/集民/集刑/裁判集/判時/判タ/金法/金判/労判 + 巻号頁
  - docket (事件番号): (昭和|平成|令和)N年(オ)第N号 etc.

Treatment cues map to DD-LAWSUBTRANS-001 §2.6 (citator union vocabulary).
Pattern policy: precision over recall; anything without a cue is `cited`
(neutral), mirroring how citators default to neutral analysis.
"""
from __future__ import annotations

import re

ERA = r"(?:明治|大正|昭和|平成|令和)"
NUM = r"[0-9０-９一二三四五六七八九十百元]+"

# Two court-token families (longest alternative first):
#  - full names, which need a trailing 判決/決定 (e.g. 最高裁…大法廷判決)
#  - abbreviations with the disposition fused in (最判/最大決/東京高判 …)
COURT = (
    r"(?:最高裁判所|最高裁|大審院"
    r"|[一-龥]{1,4}(?:高等|地方|家庭|簡易)裁判所"
    r"|[一-龥]{1,4}(?:高|地|家|簡)裁"
    r"|最大[判決]|最[判決]|大[判決]"
    r"|[一-龥]{1,4}(?:高|地|家|簡)[判決])"
)
BENCH = r"(?:大法廷|第[一二三]小法廷)?"
DISPO = r"(?:判決|決定)"
DATE = rf"{ERA}{NUM}年{NUM}月{NUM}日"

REPORTER = (
    rf"(?:民集|刑集|集民|集刑|裁判集(?:民事|刑事)?|判例時報|判時|判例タイムズ|判タ"
    rf"|金融法務事情|金法|金融・商事判例|金判|労働判例|労判)"
    rf"\s*{NUM}巻?\s*{NUM}?号?\s*{NUM}頁?"
)

DOCKET = rf"{ERA}{NUM}年[（(]([^）)]{{1,8}})[）)]第?{NUM}号"

# citation core: court + date, then optional bench/disposition and reporter.
# Precision guard (applied in extract.py): a match must carry a disposition —
# either trailing 判決/決定 or fused in the abbreviation — or a reporter ref;
# a bare "court + date" is too weak to count as a citation.
CITATION_RE = re.compile(
    rf"(?P<court>{COURT}){BENCH}(?P<date>{DATE}){BENCH}(?P<dispo>{DISPO})?"
    rf"(?:[・,、\s]*(?P<reporter>{REPORTER}))?"
)
DOCKET_RE = re.compile(DOCKET)
COURT_HAS_DISPO_RE = re.compile(r"[判決]$")

# ---------------------------------------------------------------------------
# Treatment cue inventory (pattern_id, regex, treatment_relation, confidence)
# Order matters: first match wins within a window; strongest cues first.
# Vocabulary = DD-LAWSUBTRANS-001 §2.6.
# ---------------------------------------------------------------------------
CUES = [
    # --- negative / displacing -------------------------------------------
    # 判例変更 requires the Grand Bench (裁判所法10条3号); procedural anchoring
    # to 大法廷 is recorded via the citation's bench, promotion is curator work.
    ("ovr_henko", re.compile(r"判例[はを]?[、\s]*変更|変更すべきものと|改められるべきで"
                             r"|判例.{0,12}変更する|抵触する限度で.{0,12}変更"),
     "overruled", "medium"),
    # --- statutory displacement (quarantined category) ---------------------
    ("sup_statute", re.compile(r"(?:法改正|改正法|現行法)の?(?:下|もと)では.{0,20}(?:妥当しない|維持(?:できない|し難い))|法改正により.{0,15}(?:失われ|前提を欠く)"),
     "superseded_by_statute", "medium"),
    # --- caution / qualifying ---------------------------------------------
    ("dist_jian", re.compile(r"事案を異に(?:し|する)|事例を異に(?:し|する)|前提を異に(?:し|する)"
                             r"|本件と(?:は)?事案を異に|本件に(?:は)?適切でない"),
     "distinguished", "medium"),
    ("dist_shushi", re.compile(r"趣旨を判示したものではな(?:い|く)"),
     "distinguished", "medium"),
    ("qst_souhan", re.compile(r"と相反する判断|判例と相反する|判例違反"),
     "called_into_doubt", "low"),
    ("lim_shatei", re.compile(r"射程(?:外|は.{0,20}及ばない)|限定的に解(?:す|する|される)べき"),
     "limited", "medium"),
    ("qst_gimon", re.compile(r"疑問(?:が(?:ある|残る)|なしとしない|を呈す)|疑義が(?:ある|残る)"),
     "questioned", "low"),
    ("crit_hihan", re.compile(r"批判(?:が(?:強い|ある)|されて)|妥当で(?:は)?ない|賛成(?:でき|し難)|支持(?:できない|し難い)"),
     "criticized", "low"),
    ("nfl_sai", re.compile(r"(?:採用|採ら|従う)(?:し難い|ない|べきでない)|これに(?:は)?従わない"),
     "not_applied", "low"),
    # --- positive -----------------------------------------------------------
    ("fol_doshi", re.compile(r"と同旨|の趣旨に(?:徴し|照らし|従い)|を踏襲|に従(?:い|って)判断"
                             r"|当裁判所の判例とするところ"),
     "followed", "medium"),
    ("app_motozuki", re.compile(r"(?:に|の)(?:基づき|のっとり)|を適用し"),
     "applied", "low"),
    ("rel_izkyo", re.compile(r"に依拠|を前提と(?:し|する)"),
     "relied_upon", "low"),
    # --- neutral ------------------------------------------------------------
    ("exp_setsumei", re.compile(r"を敷衍|を説明|を整理"),
     "explained", "low"),
    ("con_kento", re.compile(r"を検討|を考慮"),
     "considered", "low"),
    # `参照` / bare citation falls through to default `cited`.
]

DEFAULT_TREATMENT = ("cited_default", "cited", "low")

TREATMENT_DOMAIN = {
    "followed", "applied", "approved", "relied_upon",
    "cited", "considered", "explained",
    "distinguished", "limited", "questioned", "criticized", "called_into_doubt",
    "declined_to_extend", "followed_with_reservations", "not_applied",
    "overruled", "abrogated", "disapproved",
    "superseded_by_statute",
}

# Treatments that MUST NOT be emitted without an explicit cue match.
STRONG_ONLY = {"overruled", "abrogated", "disapproved", "superseded_by_statute"}

# Party-argument narration: a cue inside the summary of a party's contention
# (「所論は…という」「上告理由」「論旨は」) is ARGUMENT, not court treatment
# (Zhang & Koppaka / Sadeghian window discipline). Argument-borne cues for the
# 相反/変更 family are suppressed to neutral `cited`.
PARTY_ARGUMENT_RE = re.compile(r"所論は|上告(?:受理申立て)?理由|論旨は|上告人は.{0,12}主張")
ARGUMENT_SENSITIVE = {"called_into_doubt", "overruled", "superseded_by_statute"}
