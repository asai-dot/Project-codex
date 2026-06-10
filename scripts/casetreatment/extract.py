"""Treatment-candidate extraction.

Window strategy: the sentence containing the citation plus the following
sentence (treating-court commentary usually trails the citation, e.g.
「所論引用の判例は、事案を異にし本件に適切でない。」).

Confidence policy (citator lesson — algorithmic treatments are surfaced as
lower-confidence than editorial ones):
  - cue matched  -> that cue's confidence (medium ceiling in v0.1)
  - no cue       -> `cited`, low
All rows: assertion_status='candidate', claim_support_eligible=False.
"""
from __future__ import annotations

import dataclasses
import hashlib
import re
import unicodedata
from typing import List, Optional

from . import EXTRACTOR_VERSION
from .patterns import (CITATION_RE, DOCKET_RE, CUES, DEFAULT_TREATMENT,
                       STRONG_ONLY, PARTY_ARGUMENT_RE, ARGUMENT_SENSITIVE,
                       COURT_HAS_DISPO_RE)

_SENT_SPLIT = re.compile(r"(?<=。)")

SOURCE_TYPES = ("court", "scholar", "treatise", "practitioner",
                "legislative_drafter", "ministry_commentary",
                "legislative_record", "alo_internal")


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s or "")


@dataclasses.dataclass
class TreatmentCandidate:
    doc_id: str
    source_type: str                  # who is speaking (court / scholar / ...)
    citation_text: str                # the matched citation string
    court: str
    date_text: str
    reporter_text: Optional[str]
    docket_text: Optional[str]
    treatment_relation: str           # DD §2.6
    pattern_id: str
    cue_text: Optional[str]           # matched cue surface (None for default)
    quoted_text: str                  # evidence window (T5 quoted_text)
    span_start: int
    span_end: int
    confidence: str                   # low / medium  (v0.1 never emits high)
    assertion_status: str             # always 'candidate'
    claim_support_eligible: bool      # always False
    extractor_version: str
    dedup_key: str

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


def _sentences(text: str) -> List[tuple]:
    """Return [(start_offset, sentence), ...] preserving offsets."""
    out = []
    pos = 0
    for part in _SENT_SPLIT.split(text):
        if part:
            out.append((pos, part))
            pos += len(part)
    return out


def _window(sents: List[tuple], idx: int) -> tuple:
    """Citation sentence + following sentence."""
    start = sents[idx][0]
    end_idx = min(idx + 1, len(sents) - 1)
    end = sents[end_idx][0] + len(sents[end_idx][1])
    text = "".join(s for _, s in sents[idx:end_idx + 1])
    return start, end, text


def _dedup_key(doc_id: str, citation: str, treatment: str, span: tuple) -> str:
    base = f"{doc_id}|{citation}|{treatment}|{span[0]}:{span[1]}|{EXTRACTOR_VERSION}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


def extract_treatments(text: str, *, doc_id: str,
                       source_type: str = "court") -> List[TreatmentCandidate]:
    if source_type not in SOURCE_TYPES:
        raise ValueError(f"unknown source_type: {source_type}")
    text = nfc(text)
    sents = _sentences(text)
    candidates: List[TreatmentCandidate] = []
    for idx, (s_off, sent) in enumerate(sents):
        for m in CITATION_RE.finditer(sent):
            # precision guard: need a disposition (trailing or fused in the
            # abbreviated court token) or a reporter ref; bare court+date is
            # not a citation.
            if not (m.group("dispo") or m.group("reporter")
                    or COURT_HAS_DISPO_RE.search(m.group("court"))):
                continue
            w_start, w_end, w_text = _window(sents, idx)
            # classify: cues in the citation's own sentence outrank cues in
            # the following sentence (sentence-level unit per Zhang & Koppaka)
            pattern_id, treatment, conf = DEFAULT_TREATMENT
            cue_text = None
            for scope in (sent, w_text):
                for pid, cre, rel, c in CUES:
                    cm = cre.search(scope)
                    if cm:
                        pattern_id, treatment, conf = pid, rel, c
                        cue_text = cm.group(0)
                        break
                if cue_text is not None:
                    break
            # party-argument suppression: 「所論は…判例違反をいう」 narrates a
            # contention, not the court's treatment — downgrade to neutral.
            if (treatment in ARGUMENT_SENSITIVE
                    and PARTY_ARGUMENT_RE.search(w_text)):
                pattern_id = f"{pattern_id}+argued_party_suppressed"
                treatment, conf = "cited", "low"
                cue_text = None
            dm = DOCKET_RE.search(w_text)
            candidates.append(TreatmentCandidate(
                doc_id=doc_id,
                source_type=source_type,
                citation_text=m.group(0),
                court=m.group("court"),
                date_text=m.group("date"),
                reporter_text=m.group("reporter"),
                docket_text=dm.group(0) if dm else None,
                treatment_relation=treatment,
                pattern_id=pattern_id,
                cue_text=cue_text,
                quoted_text=w_text,
                span_start=w_start,
                span_end=w_end,
                confidence=conf,
                assertion_status="candidate",
                claim_support_eligible=False,
                extractor_version=EXTRACTOR_VERSION,
                dedup_key=_dedup_key(doc_id, m.group(0), treatment,
                                     (w_start, w_end)),
            ))
    # sanity: strong treatments require an explicit cue
    for c in candidates:
        if c.treatment_relation in STRONG_ONLY and c.cue_text is None:
            raise AssertionError(
                f"strong treatment {c.treatment_relation} without cue")
    return candidates
