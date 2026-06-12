"""
selector.py  —  Clip Selection (greedy, non-overlapping)
=========================================================

Owner: Clip Selection role.

This module is the bridge between two teammates:

    Scoring Logic  ──►  [ Clip Selection ]  ──►  Renderer
    (gives scored        (this module)           (cuts the chosen
     segments)                                    time windows)

Given a list of *scored segments* (each with a start time, end time and a
"how interesting is this" score), it decides which moments of the video become
shorts. It does this by:

  1. Growing a clip *window* around each high-scoring segment until the window
     reaches the target duration — snapping to segment boundaries so a sentence
     is never cut in half.
  2. Greedily selecting the highest-scoring windows that do NOT overlap each
     other, until we have N clips.
  3. Applying a light repetition penalty so we don't pick several clips that all
     rely on the same hook keyword (keeps the set varied).

It is dependency-free and framework-free: it accepts plain dicts OR objects,
so it works no matter how the Scoring teammate structures their output.

------------------------------------------------------------------------------
INPUT CONTRACT  (one item per scored segment, in chronological order)
------------------------------------------------------------------------------
Each segment must expose:
    start : float   seconds
    end   : float   seconds   (end > start)
    score : float   higher = more interesting
Optional:
    text     : str
    keywords : list[str]      hook words that drove the score (for variety)

Accepts either dicts ({"start": .., "end": .., "score": ..}) or any object with
those attributes.

------------------------------------------------------------------------------
OUTPUT
------------------------------------------------------------------------------
A list of `Clip` objects, in chronological order:
    index   : 1-based position in the final video order
    start   : float   clip window start (seconds)
    end     : float   clip window end (seconds)
    score   : float   the window's total score
    seed_score : float  score of the segment that triggered this clip
    text    : str     concatenated text of the segment(s) in the window
    segment_indices : list[int]  which input segments fall in this window
"""

from __future__ import annotations

from dataclasses import dataclass, field


# --------------------------------------------------------------------------- #
# Normalised internal representation
# --------------------------------------------------------------------------- #
@dataclass
class _Seg:
    start: float
    end: float
    score: float
    text: str = ""
    keywords: list = field(default_factory=list)


@dataclass
class Clip:
    index: int
    start: float
    end: float
    score: float
    seed_score: float
    text: str
    segment_indices: list


def _get(seg, name, default=None):
    """Read a field from either a dict or an object."""
    if isinstance(seg, dict):
        return seg.get(name, default)
    return getattr(seg, name, default)


def _normalise(segments) -> list:
    """Coerce arbitrary input into a chronological list of _Seg."""
    out = []
    for s in segments:
        start = float(_get(s, "start"))
        end = float(_get(s, "end"))
        if end <= start:
            # Skip zero / negative length segments — they can't form a window.
            continue
        out.append(
            _Seg(
                start=start,
                end=end,
                score=float(_get(s, "score", 0.0)),
                text=(_get(s, "text", "") or "").strip(),
                keywords=list(_get(s, "keywords", []) or []),
            )
        )
    out.sort(key=lambda x: x.start)
    return out


# --------------------------------------------------------------------------- #
# The greedy non-overlapping selection
# --------------------------------------------------------------------------- #
def select_clips(
    segments,
    num_clips: int = 3,
    target_duration: float = 30.0,
    min_duration: float = 12.0,
    max_duration: float = 60.0,
    min_gap: float = 0.0,
    repetition_limit: int = 2,
) -> list:
    """
    Select up to `num_clips` non-overlapping clip windows.

    Parameters
    ----------
    segments         : scored segments (chronological). See INPUT CONTRACT.
    num_clips        : how many shorts to produce (1-10 typically).
    target_duration  : desired clip length in seconds; windows grow toward this.
    min_duration     : reject windows shorter than this.
    max_duration     : hard cap on clip length.
    min_gap          : minimum spacing (s) required between two selected clips.
    repetition_limit : skip a clip if its hook keywords are already used this
                       many times across selected clips (variety control).

    Returns
    -------
    list[Clip] in chronological order. May be shorter than `num_clips` if the
    input doesn't contain enough non-overlapping material.
    """
    segs = _normalise(segments)
    if not segs or num_clips <= 0:
        return []

    n = len(segs)

    # Rank seeds by score (highest first). Ties broken by earlier start so the
    # result is deterministic.
    seed_order = sorted(range(n), key=lambda i: (-segs[i].score, segs[i].start))

    used_ranges: list[tuple] = []      # selected [start, end] windows
    used_keywords: dict = {}
    selected: list[dict] = []

    def overlaps(a_start: float, a_end: float) -> bool:
        for s, e in used_ranges:
            # treat clips closer than min_gap as overlapping
            if not (a_end + min_gap <= s or a_start - min_gap >= e):
                return True
        return False

    def grow_window(seed_idx: int):
        """
        Grow [lo, hi] outward from the seed segment until ~target_duration,
        never crossing into an already-selected range and snapping to segment
        boundaries. Returns (start, end, indices) or None if blocked.
        """
        lo = hi = seed_idx
        start, end = segs[seed_idx].start, segs[seed_idx].end

        # If the seed itself sits inside a used range, it's unusable.
        if overlaps(start, end):
            return None

        while (end - start) < target_duration:
            can_left = lo > 0 and not overlaps(segs[lo - 1].start, end)
            can_right = hi < n - 1 and not overlaps(start, segs[hi + 1].end)

            if not can_left and not can_right:
                break

            # Prefer the side that keeps the seed roughly centred; if only one
            # side is available, take it.
            grow_right_first = (hi - seed_idx) <= (seed_idx - lo)
            if can_right and (grow_right_first or not can_left):
                nxt_end = segs[hi + 1].end
                if (nxt_end - start) > max_duration:
                    break
                hi += 1
                end = nxt_end
            elif can_left:
                nxt_start = segs[lo - 1].start
                if (end - nxt_start) > max_duration:
                    break
                lo -= 1
                start = nxt_start
            else:
                break

        return start, end, list(range(lo, hi + 1))

    for seed_idx in seed_order:
        if len(selected) >= num_clips:
            break

        seed = segs[seed_idx]

        # Repetition penalty: if this seed's keywords are already well covered,
        # skip it for variety — unless candidates are scarce.
        if seed.keywords:
            repeats = sum(used_keywords.get(k, 0) for k in seed.keywords)
            if repeats >= repetition_limit and len(seed_order) > num_clips * 2:
                continue

        grown = grow_window(seed_idx)
        if grown is None:
            continue
        start, end, idxs = grown

        duration = end - start
        if duration < min_duration:
            continue
        if duration > max_duration:
            end = start + max_duration
            idxs = [i for i in idxs if segs[i].start < end]

        window_score = round(sum(segs[i].score for i in idxs), 3)
        text = " ".join(segs[i].text for i in idxs if segs[i].text).strip()

        used_ranges.append((start, end))
        for k in seed.keywords:
            used_keywords[k] = used_keywords.get(k, 0) + 1

        selected.append({
            "start": round(start, 3),
            "end": round(end, 3),
            "score": window_score,
            "seed_score": seed.score,
            "text": text,
            "segment_indices": idxs,
        })

    # Return in chronological order with fresh 1-based indices.
    selected.sort(key=lambda c: c["start"])
    return [
        Clip(index=i, **c) for i, c in enumerate(selected, start=1)
    ]


def clips_to_dicts(clips: list) -> list:
    """Convenience: serialise Clip objects to plain dicts (e.g. for JSON)."""
    return [
        {
            "index": c.index,
            "start": c.start,
            "end": c.end,
            "score": c.score,
            "seed_score": c.seed_score,
            "text": c.text,
            "segment_indices": c.segment_indices,
        }
        for c in clips
    ]
