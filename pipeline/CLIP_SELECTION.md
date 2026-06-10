# Clip Selection

My part of AutoShorts: deciding **which** moments of a video become shorts.

```
Scoring Logic  ──►  [ Clip Selection ]  ──►  Renderer
(scored segments)    (this component)        (cuts the chosen windows)
```

## What it does

It takes the scored segments produced by the Scoring teammate and returns up to
`N` **non-overlapping** clip windows, chosen with a **greedy, highest-score-first**
algorithm. Each clip is grown to a target duration around a high-scoring
"seed" segment, snapping to segment boundaries so a sentence is never cut in half.

## The algorithm

1. **Normalise & sort** the input segments chronologically (accepts dicts or
   objects; zero-length segments are dropped).
2. **Rank seeds** by score, highest first (ties broken by earlier start, so the
   output is deterministic).
3. For each seed, in order:
   - **Grow a window** outward from the seed toward `target_duration`, extending
     to whichever neighbouring segment keeps the seed roughly centred. Growth
     stops at `max_duration` and never crosses into an already-selected window.
   - **Reject** the window if it is shorter than `min_duration`.
   - **Repetition penalty:** skip the seed if its hook keywords are already used
     `repetition_limit` times across chosen clips (keeps the set varied) — unless
     candidates are scarce.
   - Otherwise **select** it and mark its time range (plus an optional `min_gap`)
     as used.
4. Stop once `N` clips are selected; return them in **chronological order** with
   fresh 1-based indices.

Greedy non-overlapping selection is the right fit here: clips are short relative
to the video, exact optimality isn't needed, and "take the best remaining slot
that still fits" is fast (O(n²) worst case on segment count, trivial in practice)
and easy to reason about.

## Interface contract

### Input — list of scored segments (chronological)
| Field | Type | Required | Notes |
|---|---|---|---|
| `start` | float | yes | seconds |
| `end` | float | yes | seconds, `> start` |
| `score` | float | yes | higher = more interesting |
| `text` | str | no | used only for previews |
| `keywords` | list[str] | no | drives the repetition penalty |

Dicts **or** objects with these attributes both work, so I'm not coupled to the
Scoring teammate's exact data type.

### Output — list of `Clip`
| Field | Meaning |
|---|---|
| `index` | 1-based order in the final video |
| `start`, `end` | clip window (seconds) — what the Renderer cuts |
| `score` | total score of segments in the window |
| `seed_score` | score of the segment that triggered the clip |
| `text` | concatenated segment text (preview) |
| `segment_indices` | which input segments fall inside the window |

Use `clips_to_dicts(clips)` to get plain dicts for JSON / handoff.

## Parameters

| Param | Default | Purpose |
|---|---|---|
| `num_clips` | 3 | how many shorts to produce |
| `target_duration` | 30.0 | desired clip length (s) |
| `min_duration` | 12.0 | reject shorter windows |
| `max_duration` | 60.0 | hard cap |
| `min_gap` | 0.0 | min spacing between clips (s) |
| `repetition_limit` | 2 | keyword reuse allowed before skipping for variety |

## How to run / demo

```bash
python demo.py                       # uses sample_scored.json
python demo.py --clips 4 --duration 20
python test_selector.py              # 11 tests, no dependencies needed
```

The demo prints the selected clips, an ASCII timeline (so the non-overlap is
obvious on a screen recording), and the JSON that goes to the Renderer.

## Integration

This file is `pipeline/selector.py` in the shared repo. The Integration teammate
calls:

```python
from pipeline.selector import select_clips
clips = select_clips(scored_segments, num_clips=n, target_duration=d)
```

## Tests

`test_selector.py` covers: correct count & ordering, non-overlap, picking the
highest score, `min`/`max` duration handling, `min_gap`, empty input, zero-length
segments, dict-vs-object input, and the repetition penalty. All 11 pass.
