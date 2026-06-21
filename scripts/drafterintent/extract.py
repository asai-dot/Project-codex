"""Extract drafter-intent substantive-change candidates + evidence.

For each statute reference whose sentence (±1 following sentence) carries a
drafter-claim cue, emit:
  - one T5 evidence pointer (the quoted commentary span), and
  - one T2 substantive_change_assertion CANDIDATE referencing it.

Window discipline mirrors casetreatment: cues in the reference's own sentence
outrank cues in the next sentence. A bare reference with no cue yields nothing
(no fabricated change_type).
"""
from __future__ import annotations

import dataclasses
import hashlib
import re
import unicodedata
from typing import List, Optional

from . import PRODUCER_VERSION
from .patterns import (ARTICLE_RE, article_path, revision_side, CUES,
                       infer_source_type, SOURCE_TIER, CHANGE_TYPE_DOMAIN)

_SENT_SPLIT = re.compile(r"(?<=。)")


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s or "")


def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


@dataclasses.dataclass
class Evidence:
    """T5 alo_law_interpretive_evidence row (candidate form)."""
    evidence_key: str
    source_type: str
    source_tier: int
    source_uri: Optional[str]
    source_record_key: str
    locator: Optional[str]
    source_span_hash: str
    quoted_text: str
    parser_version: str

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class SubstantiveAssertion:
    """T2 alo_law_substantive_change_assertion row (candidate form)."""
    assertion_key: str
    law_work_id: Optional[str]
    law_name: Optional[str]
    article_path: str
    revision_side: str                 # before/after/current/unknown (hint)
    change_type: str
    temporal_reach: str
    asserted_by_source_type: str
    source_tier: int
    evidence_key: str                  # -> Evidence.evidence_key
    confidence: str                    # low/medium (never high from rules)
    confirmatory: bool                 # 確認的(=declares existing) per drafter
    pattern_id: str
    cue_text: str
    assertion_status: str              # always 'candidate'
    claim_support_eligible: bool       # always False
    producer_version: str

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


def _sentences(text: str) -> List[tuple]:
    out, pos = [], 0
    for part in _SENT_SPLIT.split(text):
        if part:
            out.append((pos, part))
            pos += len(part)
    return out


def _window(sents: List[tuple], idx: int) -> tuple:
    start = sents[idx][0]
    end_idx = min(idx + 1, len(sents) - 1)
    end = sents[end_idx][0] + len(sents[end_idx][1])
    return start, end, "".join(s for _, s in sents[idx:end_idx + 1])


def extract_drafter_intent(text: str, *, doc_id: str,
                           source_type_hint: Optional[str] = None,
                           law_work_id: Optional[str] = None,
                           locator: Optional[str] = None,
                           source_uri: Optional[str] = None):
    """Return (evidences, assertions)."""
    text = nfc(text)
    source_type = infer_source_type(source_type_hint)
    tier = SOURCE_TIER[source_type]
    sents = _sentences(text)
    evidences: List[Evidence] = []
    assertions: List[SubstantiveAssertion] = []
    seen_ev: dict = {}

    for idx, (s_off, sent) in enumerate(sents):
        for m in ARTICLE_RE.finditer(sent):
            path = article_path(m)
            if path is None:
                continue
            w_start, w_end, w_text = _window(sents, idx)
            # cue: same sentence first, then next sentence
            hit = None
            for scope in (sent, w_text):
                for pid, cre, ctype, conf, confirm in CUES:
                    cm = cre.search(scope)
                    if cm:
                        hit = (pid, ctype, conf, confirm, cm.group(0))
                        break
                if hit:
                    break
            if hit is None:
                continue  # bare mention -> no fabricated change_type
            pid, ctype, conf, confirm, cue_text = hit

            span_hash = _sha1(w_text)
            ev_key = _sha1(f"{doc_id}|{path}|{w_start}:{w_end}|{PRODUCER_VERSION}")
            if ev_key not in seen_ev:
                ev = Evidence(
                    evidence_key=ev_key,
                    source_type=source_type,
                    source_tier=tier,
                    source_uri=source_uri,
                    source_record_key=doc_id,
                    locator=locator,
                    source_span_hash=span_hash,
                    quoted_text=w_text,
                    parser_version=PRODUCER_VERSION,
                )
                evidences.append(ev)
                seen_ev[ev_key] = ev

            a_key = _sha1(f"{ev_key}|{path}|{ctype}|{pid}")
            assertions.append(SubstantiveAssertion(
                assertion_key=a_key,
                law_work_id=law_work_id,
                law_name=(m.group("lawname") or None),
                article_path=path,
                revision_side=revision_side(
                    (m.group("marker") or "") + (m.group("lawname") or "")),
                change_type=ctype,
                temporal_reach="unknown",
                asserted_by_source_type=source_type,
                source_tier=tier,
                evidence_key=ev_key,
                confidence=conf,
                confirmatory=confirm,
                pattern_id=pid,
                cue_text=cue_text,
                assertion_status="candidate",
                claim_support_eligible=False,
                producer_version=PRODUCER_VERSION,
            ))

    # invariants
    for a in assertions:
        assert a.change_type in CHANGE_TYPE_DOMAIN, a.change_type
        assert a.assertion_status == "candidate"
        assert a.claim_support_eligible is False
        assert a.source_tier == 2
    return evidences, assertions
