"""
selector.py — Clip Selection (greedy, non-overlapping)
"""

def select_clips(segments: list, num_clips: int = 3,
                 min_duration: float = 15.0,
                 max_duration: float = 60.0) -> list:
    """
    Select top N non-overlapping clips from scored segments.
    Returns list of (start, end, score) tuples.
    """
    sorted_segments = sorted(segments, key=lambda x: x.get("score", 0), reverse=True)
    selected = []

    for seg in sorted_segments:
        if len(selected) >= num_clips:
            break

        start = float(seg["start"])
        end = float(seg["end"])
        duration = end - start

        if duration < min_duration:
            center = (start + end) / 2
            start = max(0, center - min_duration / 2)
            end = start + min_duration

        if (end - start) > max_duration:
            continue

        overlap = False
        for s, e, _ in selected:
            if not (end <= s or start >= e):
                overlap = True
                break

        if not overlap:
            selected.append((round(start, 2), round(end, 2), seg.get("score", 0)))

    return selected