"""Data model for lawdelta."""
from __future__ import annotations

import dataclasses
import hashlib
import unicodedata
from typing import Optional


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s or "")


def normalize_for_similarity(s: str) -> str:
    """Normalization used ONLY for similarity/equality comparison.

    NFC + strip all whitespace. Raw text is preserved elsewhere for hashing
    and evidence (No Destructive Import / Raw First).
    """
    s = nfc(s)
    return "".join(s.split())


def sha1_text(s: str) -> str:
    return hashlib.sha1(nfc(s).encode("utf-8")).hexdigest()


# 「削除」 shell bodies as they appear in e-Gov consolidated texts.
_DELETED_BODIES = {"削除", "削除。"}


@dataclasses.dataclass
class ArticleUnit:
    """One article (条) of one consolidated revision.

    article_path follows the egov URI tail used by 30_law_layer / DD-LAWTIME:
    ``art:709`` / ``art:415`` ; branch numbers (枝番, e-Gov Num="709_2")
    are hyphenated: ``art:709-2``.
    """

    article_path: str
    article_number: str               # "709", "709-2"
    caption: str = ""                 # （不法行為による損害賠償） etc.
    text: str = ""                    # paragraphs/items concatenated, raw
    deleted: bool = False             # Delete="true" or 「削除」 shell
    order_index: int = 0              # document order, used for relocate hints

    def __post_init__(self) -> None:
        self.text = nfc(self.text)
        self.caption = nfc(self.caption)
        if not self.deleted and normalize_for_similarity(self.text) in _DELETED_BODIES:
            self.deleted = True

    @property
    def sim_text(self) -> str:
        return normalize_for_similarity(self.text)

    @property
    def payload_sha1(self) -> str:
        return sha1_text(self.text)


@dataclasses.dataclass
class DeltaRecord:
    """One row of the T1 ``alo_law_textual_delta`` output contract (JSONL).

    Pure textual observation. MUST NOT carry substantive judgement fields.
    """

    law_id: str
    law_work_id: Optional[str]
    article_path: str
    from_law_revision_id: str
    to_law_revision_id: str
    delta_kind: str                   # ck_delta_kind domain
    text_changed: bool
    similarity: Optional[float]
    counterpart_paths: list           # split/join/renumber counterparts
    diff_payload: Optional[dict]      # opcodes summary (inline artifact form)
    old_payload_sha1: Optional[str]
    new_payload_sha1: Optional[str]
    detector_version: str
    source_snapshot_id: str

    DELTA_KIND_DOMAIN = (
        "substitution", "insertion", "repeal", "renumber",
        "relocate", "split", "join", "no_change", "unknown",
    )

    def to_dict(self) -> dict:
        d = dataclasses.asdict(self)
        d.pop("DELTA_KIND_DOMAIN", None)
        return d
