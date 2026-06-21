"""Article alignment & delta classification.

World-standard shape (see scripts/lawdelta/README.md for citations):

- Phase A  anchor matching on article number (the stable identifier inside one
  law_id), like consolidation systems (Norma-System, legislation.gov.uk
  effects: affected provision is addressed by number).
- Phase B  rename detection over the unmatched remainder by content
  similarity with thresholds — the same heuristic family as git's rename
  detection (similarity index over candidate pairs, greedy best-first).
- Phase C  1-to-many / many-to-1 (split/join) via *asymmetric containment*,
  because symmetric ratios punish size mismatch.
- Leftovers are pure insertion / repeal.

The classifier observes text only. It never decides whether a change is
substantive — that is DD-LAWSUBTRANS-001 §4 gate `amendment_not_auto_substantive`.
"""
from __future__ import annotations

import difflib
from typing import Dict, List, Optional, Tuple

from .model import ArticleUnit, DeltaRecord
from . import DETECTOR_VERSION

# Thresholds (tunable; see README for rationale/prior art)
RENUMBER_SIM = 0.92      # near-identical content under a new number
RELOCATE_SIM = 0.60      # moved + edited (git default 0.5; legal domain 0.6-0.7)
SUBST_MIN = 0.50         # same-number pair below this is "broken" (diffcore-break;
                         # git's default rename floor — see README prior art)
CONTAIN_PART = 0.55      # a fragment counts as "contained" in a counterpart
SPLIT_COVERAGE = 0.60    # combined containment of old text inside new parts
LENGTH_RATIO_GATE = 0.30 # git-style size prefilter for candidate pairs
CAPTION_WEIGHT = 0.10    # 見出し is strong, cheap alignment evidence


def similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    sm = difflib.SequenceMatcher(None, a, b)
    if sm.real_quick_ratio() < RELOCATE_SIM:
        return sm.real_quick_ratio()
    if sm.quick_ratio() < RELOCATE_SIM:
        return sm.quick_ratio()
    return sm.ratio()


def pair_score(o: ArticleUnit, n: ArticleUnit) -> float:
    """Body similarity, blended with caption similarity when both have one."""
    body = similarity(o.sim_text, n.sim_text)
    if o.caption and n.caption:
        cap = similarity(o.caption, n.caption)
        return (1.0 - CAPTION_WEIGHT) * body + CAPTION_WEIGHT * cap
    return body


def _length_gate(a: str, b: str) -> bool:
    la, lb = len(a), len(b)
    if la == 0 or lb == 0:
        return la == lb
    return min(la, lb) / max(la, lb) >= LENGTH_RATIO_GATE


def _num_main(article_number: str) -> Optional[int]:
    head = article_number.split("-")[0]
    return int(head) if head.isdigit() else None


def containment(part: str, whole: str) -> float:
    """How much of `part` is covered by matching blocks inside `whole` (0..1)."""
    if not part:
        return 0.0
    sm = difflib.SequenceMatcher(None, part, whole)
    matched = sum(bl.size for bl in sm.get_matching_blocks())
    return matched / len(part)


def diff_opcodes(a: str, b: str, limit: int = 50) -> dict:
    """Compact difflib opcode summary (artifact form of diff_pointer)."""
    sm = difflib.SequenceMatcher(None, a, b)
    ops = [
        {"op": tag, "a": [i1, i2], "b": [j1, j2]}
        for tag, i1, i2, j1, j2 in sm.get_opcodes()
        if tag != "equal"
    ]
    truncated = len(ops) > limit
    return {"opcodes": ops[:limit], "truncated": truncated}


def _record(law_id: str, law_work_id: Optional[str], snapshot_id: str,
            from_rev: str, to_rev: str, path: str, kind: str,
            old: Optional[ArticleUnit], new: Optional[ArticleUnit],
            sim: Optional[float], counterparts: Optional[List[str]] = None,
            with_diff: bool = True) -> DeltaRecord:
    text_changed = (old.sim_text if old else "") != (new.sim_text if new else "")
    payload = None
    if with_diff and text_changed and old is not None and new is not None:
        payload = diff_opcodes(old.text, new.text)
    return DeltaRecord(
        law_id=law_id,
        law_work_id=law_work_id,
        article_path=path,
        from_law_revision_id=from_rev,
        to_law_revision_id=to_rev,
        delta_kind=kind,
        text_changed=text_changed,
        similarity=round(sim, 4) if sim is not None else None,
        counterpart_paths=counterparts or [],
        diff_payload=payload,
        old_payload_sha1=old.payload_sha1 if old else None,
        new_payload_sha1=new.payload_sha1 if new else None,
        detector_version=DETECTOR_VERSION,
        source_snapshot_id=snapshot_id,
    )


def compute_deltas(old_units: List[ArticleUnit], new_units: List[ArticleUnit],
                   *, law_id: str, from_rev: str, to_rev: str,
                   snapshot_id: str, law_work_id: Optional[str] = None
                   ) -> List[DeltaRecord]:
    old_by = {u.article_path: u for u in old_units}
    new_by = {u.article_path: u for u in new_units}
    records: List[DeltaRecord] = []

    def rec(path, kind, o, n, sim, counterparts=None, with_diff=True):
        return _record(law_id, law_work_id, snapshot_id, from_rev, to_rev,
                       path, kind, o, n, sim, counterparts, with_diff)

    # ---- Phase A: anchor on article number --------------------------------
    # Same-number pairs whose similarity falls below SUBST_MIN are "broken"
    # back into the pools (git diffcore-break), so a coincidental number
    # reuse does not mask a renumber/split/join elsewhere.
    subst_pairs: List[Tuple[float, ArticleUnit, ArticleUnit]] = []
    broken_pairs: Dict[str, Tuple[float, ArticleUnit, ArticleUnit]] = {}
    pool_old: List[ArticleUnit] = []
    pool_new: List[ArticleUnit] = []
    seen_old, seen_new = set(), set()
    for path, o in old_by.items():
        n = new_by.get(path)
        if n is None:
            continue
        seen_old.add(path)
        seen_new.add(path)
        if o.deleted and n.deleted:
            records.append(rec(path, "no_change", o, n, 1.0))
        elif not o.deleted and n.deleted:
            # 「第X条 削除」 shell: number persists, content repealed
            records.append(rec(path, "repeal", o, n, None))
        elif o.deleted and not n.deleted:
            # number reused for new content
            records.append(rec(path, "insertion", o, n, None))
        elif o.sim_text == n.sim_text:
            records.append(rec(path, "no_change", o, n, 1.0, with_diff=False))
        else:
            s = pair_score(o, n)
            if s >= SUBST_MIN:
                subst_pairs.append((s, o, n))
            else:
                broken_pairs[path] = (s, o, n)
                pool_old.append(o)
                pool_new.append(n)
    pool_old += [o for p, o in old_by.items()
                 if p not in seen_old and not o.deleted]
    pool_new += [n for p, n in new_by.items()
                 if p not in seen_new and not n.deleted]

    def greedy(pairs_min: float, pairs_max: Optional[float]) -> List[Tuple[float, ArticleUnit, ArticleUnit]]:
        """git diffcore-rename: scored candidates, greedy best-first."""
        nonlocal pool_old, pool_new
        cands: List[Tuple[float, ArticleUnit, ArticleUnit]] = []
        for o in pool_old:
            for n in pool_new:
                if not _length_gate(o.sim_text, n.sim_text):
                    continue
                s = pair_score(o, n)
                if s >= pairs_min and (pairs_max is None or s < pairs_max):
                    cands.append((s, o, n))
        cands.sort(key=lambda t: (-t[0], t[1].article_path))
        used_o, used_n, out = set(), set(), []
        for s, o, n in cands:
            if o.article_path in used_o or n.article_path in used_n:
                continue
            used_o.add(o.article_path)
            used_n.add(n.article_path)
            out.append((s, o, n))
        pool_old = [o for o in pool_old if o.article_path not in used_o]
        pool_new = [n for n in pool_new if n.article_path not in used_n]
        return out

    # ---- Phase B1: high-confidence renames (near-identical content) -------
    moved_pairs = greedy(RENUMBER_SIM, None)

    # ---- Phase C: split / join on the remainder (before relocate, because a
    # moderate whole-vs-part similarity would otherwise win as relocate) ----
    consumed_new: set = set()
    still_old: List[ArticleUnit] = []
    for o in sorted(pool_old, key=lambda u: u.article_path):
        parts = [n for n in pool_new
                 if n.article_path not in consumed_new
                 and containment(n.sim_text, o.sim_text) >= CONTAIN_PART]
        coverage = containment(o.sim_text,
                               "".join(p.sim_text for p in parts)) if parts else 0.0
        if len(parts) >= 2 and coverage >= SPLIT_COVERAGE:
            consumed_new.update(p.article_path for p in parts)
            records.append(rec(o.article_path, "split", o, None,
                               round(coverage, 4),
                               counterparts=sorted(p.article_path for p in parts),
                               with_diff=False))
        else:
            still_old.append(o)
    pool_old = still_old
    pool_new = [n for n in pool_new if n.article_path not in consumed_new]

    consumed_old: set = set()
    still_new: List[ArticleUnit] = []
    for n in sorted(pool_new, key=lambda u: u.article_path):
        sources = [o for o in pool_old
                   if o.article_path not in consumed_old
                   and containment(o.sim_text, n.sim_text) >= CONTAIN_PART]
        coverage = containment(n.sim_text,
                               "".join(s.sim_text for s in sources)) if sources else 0.0
        if len(sources) >= 2 and coverage >= SPLIT_COVERAGE:
            consumed_old.update(s_.article_path for s_ in sources)
            records.append(rec(n.article_path, "join", None, n,
                               round(coverage, 4),
                               counterparts=sorted(s.article_path for s in sources),
                               with_diff=False))
        else:
            still_new.append(n)
    pool_old = [o for o in pool_old if o.article_path not in consumed_old]
    pool_new = still_new

    # ---- Phase B2: moved + edited (relocate grade) -------------------------
    moved_pairs += greedy(RELOCATE_SIM, RENUMBER_SIM)

    # ---- join/split absorption post-pass -----------------------------------
    # A leftover old article absorbed into a same-number rewrite is a join
    # (e.g. 第424条 merged into 第423条); the symmetric case is a split.
    absorbed_old: set = set()
    absorbed_new: set = set()
    final_subst: List[Tuple[float, ArticleUnit, ArticleUnit]] = []
    for s, o, n in subst_pairs:
        joins = [x for x in pool_old
                 if x.article_path not in absorbed_old
                 and containment(x.sim_text, n.sim_text) >= CONTAIN_PART]
        splits = [x for x in pool_new
                  if x.article_path not in absorbed_new
                  and containment(x.sim_text, o.sim_text) >= CONTAIN_PART]
        if joins and containment(n.sim_text,
                                 o.sim_text + "".join(x.sim_text for x in joins)
                                 ) >= SPLIT_COVERAGE:
            absorbed_old.update(x.article_path for x in joins)
            records.append(rec(n.article_path, "join", o, n, s,
                               counterparts=sorted([o.article_path]
                                                   + [x.article_path for x in joins]),
                               with_diff=False))
        elif splits and containment(o.sim_text,
                                    n.sim_text + "".join(x.sim_text for x in splits)
                                    ) >= SPLIT_COVERAGE:
            absorbed_new.update(x.article_path for x in splits)
            records.append(rec(o.article_path, "split", o, n, s,
                               counterparts=sorted([n.article_path]
                                                   + [x.article_path for x in splits]),
                               with_diff=False))
        else:
            final_subst.append((s, o, n))
    pool_old = [o for o in pool_old if o.article_path not in absorbed_old]
    pool_new = [n for n in pool_new if n.article_path not in absorbed_new]
    for s, o, n in final_subst:
        records.append(rec(o.article_path, "substitution", o, n, s))

    # ---- renumber vs relocate: near-identical content OR membership in a
    # coherent block shift (繰上げ/繰下げ: >=2 pairs, same numeric offset) ---
    offsets: Dict[int, int] = {}
    for s, o, n in moved_pairs:
        om, nm = _num_main(o.article_number), _num_main(n.article_number)
        if om is not None and nm is not None:
            offsets[nm - om] = offsets.get(nm - om, 0) + 1
    for s, o, n in moved_pairs:
        om, nm = _num_main(o.article_number), _num_main(n.article_number)
        in_block_shift = (om is not None and nm is not None
                          and offsets.get(nm - om, 0) >= 2)
        kind = "renumber" if (s >= RENUMBER_SIM or in_block_shift) else "relocate"
        records.append(rec(o.article_path, kind, o, n, s,
                           counterparts=[n.article_path]))

    # ---- broken-pair fallback: a same-number pair that found no better
    # partner anywhere is still a heavy in-place rewrite, not repeal+insert.
    left_old = {o.article_path for o in pool_old}
    left_new = {n.article_path for n in pool_new}
    for path, (s, o, n) in broken_pairs.items():
        if path in left_old and path in left_new:
            records.append(rec(path, "substitution", o, n, s))
            left_old.discard(path)
            left_new.discard(path)
    pool_old = [o for o in pool_old if o.article_path in left_old]
    pool_new = [n for n in pool_new if n.article_path in left_new]

    # ---- Leftovers: pure repeal / insertion --------------------------------
    for o in pool_old:
        records.append(rec(o.article_path, "repeal", o, None, None,
                           with_diff=False))
    for n in pool_new:
        records.append(rec(n.article_path, "insertion", None, n, None,
                           with_diff=False))

    records.sort(key=lambda r: (r.article_path, r.delta_kind))
    return records
