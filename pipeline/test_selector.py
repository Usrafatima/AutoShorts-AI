"""
test_selector.py  —  Tests for the clip-selection module.

Run either way:
    python test_selector.py        # plain, no dependencies
    pytest test_selector.py        # if pytest is installed
"""

from selector import select_clips, Clip


def seg(start, end, score, text="", keywords=None):
    return {"start": start, "end": end, "score": score,
            "text": text, "keywords": keywords or []}


def _no_overlap(clips, min_gap=0.0):
    s = sorted(clips, key=lambda c: c.start)
    return all(s[i].end <= s[i + 1].start + 1e-9 for i in range(len(s) - 1))


# --------------------------------------------------------------------------- #
def test_basic_selection_count_and_order():
    segs = [seg(i * 6, i * 6 + 5, score=10 - i, text=f"s{i}") for i in range(10)]
    clips = select_clips(segs, num_clips=3, target_duration=10, min_duration=8)
    assert len(clips) == 3
    # chronological order + 1-based indices
    assert [c.index for c in clips] == [1, 2, 3]
    assert all(clips[i].start <= clips[i + 1].start for i in range(len(clips) - 1))
    print("test_basic_selection_count_and_order OK")


def test_non_overlapping():
    segs = [seg(i * 5, i * 5 + 4, score=(i % 3) + 1) for i in range(20)]
    clips = select_clips(segs, num_clips=5, target_duration=12, min_duration=8)
    assert _no_overlap(clips), "clips overlap!"
    print("test_non_overlapping OK")


def test_picks_highest_score_first():
    # one clearly best segment surrounded by dull ones
    segs = [seg(0, 5, 1), seg(5, 10, 1), seg(10, 15, 99, text="BEST"),
            seg(15, 20, 1), seg(20, 25, 1)]
    clips = select_clips(segs, num_clips=1, target_duration=6, min_duration=4)
    assert len(clips) == 1
    assert "BEST" in clips[0].text, "did not centre on the best segment"
    print("test_picks_highest_score_first OK")


def test_min_duration_filter():
    # tiny segments that can't reach min_duration when isolated
    segs = [seg(0, 2, 5), seg(50, 52, 5), seg(100, 102, 5)]
    clips = select_clips(segs, num_clips=3, target_duration=30, min_duration=10)
    # none can grow (huge gaps, single short segments) -> filtered out
    assert clips == [] or all((c.end - c.start) >= 10 for c in clips)
    print("test_min_duration_filter OK")


def test_max_duration_cap():
    segs = [seg(i * 10, i * 10 + 9, score=5) for i in range(10)]
    clips = select_clips(segs, num_clips=1, target_duration=200,
                         min_duration=10, max_duration=40)
    assert len(clips) == 1
    assert (clips[0].end - clips[0].start) <= 40 + 1e-6
    print("test_max_duration_cap OK")


def test_fewer_segments_than_requested():
    segs = [seg(0, 10, 5, text="only one")]
    clips = select_clips(segs, num_clips=5, target_duration=8, min_duration=5)
    assert len(clips) <= 1
    print("test_fewer_segments_than_requested OK")


def test_empty_input():
    assert select_clips([], num_clips=3) == []
    assert select_clips(None or [], num_clips=3) == []
    print("test_empty_input OK")


def test_zero_length_segments_ignored():
    segs = [seg(0, 0, 100), seg(5, 5, 100), seg(10, 22, 5, text="real")]
    clips = select_clips(segs, num_clips=2, target_duration=10, min_duration=5)
    assert all(c.end > c.start for c in clips)
    print("test_zero_length_segments_ignored OK")


def test_accepts_objects_not_just_dicts():
    class S:
        def __init__(self, start, end, score):
            self.start, self.end, self.score = start, end, score
            self.text, self.keywords = "obj", []
    segs = [S(i * 6, i * 6 + 5, 10 - i) for i in range(6)]
    clips = select_clips(segs, num_clips=2, target_duration=10, min_duration=8)
    assert len(clips) == 2 and isinstance(clips[0], Clip)
    print("test_accepts_objects_not_just_dicts OK")


def test_repetition_penalty_promotes_variety():
    # Many high-score segments all using the same keyword, plus a couple with a
    # different keyword. With the penalty, the varied ones should get a look in.
    segs = []
    for i in range(8):
        segs.append(seg(i * 8, i * 8 + 7, score=9, text=f"money {i}", keywords=["money"]))
    segs.append(seg(70, 77, score=8.5, text="success story", keywords=["success"]))
    segs.append(seg(80, 87, score=8.4, text="growth tip", keywords=["growth"]))
    clips = select_clips(segs, num_clips=3, target_duration=7, min_duration=5,
                         repetition_limit=1)
    kws = " ".join(c.text for c in clips)
    assert ("success" in kws or "growth" in kws), "repetition penalty had no effect"
    print("test_repetition_penalty_promotes_variety OK")


def test_min_gap_enforced():
    segs = [seg(i * 6, i * 6 + 5, score=10 - i) for i in range(10)]
    clips = select_clips(segs, num_clips=3, target_duration=6, min_duration=4,
                         min_gap=5.0)
    s = sorted(clips, key=lambda c: c.start)
    for i in range(len(s) - 1):
        assert s[i + 1].start - s[i].end >= 5.0 - 1e-6, "min_gap violated"
    print("test_min_gap_enforced OK")


ALL = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    for t in ALL:
        t()
    print(f"\nAll {len(ALL)} tests passed.")
