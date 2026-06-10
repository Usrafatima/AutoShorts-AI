"""
demo.py  —  Run the clip selector on sample data and show the result.

Usage:
    python demo.py
    python demo.py --clips 4 --duration 20
    python demo.py path/to/scored_segments.json

This lets the Clip Selection component be tested and demonstrated on its own,
without the rest of the pipeline being finished.
"""

import argparse
import json
import os

from selector import select_clips, clips_to_dicts

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser(description="Greedy non-overlapping clip selection demo")
    ap.add_argument("input", nargs="?", default=os.path.join(HERE, "sample_scored.json"),
                    help="Path to a scored-segments JSON file")
    ap.add_argument("--clips", type=int, default=3, help="Number of clips to select")
    ap.add_argument("--duration", type=float, default=30.0, help="Target clip duration (s)")
    ap.add_argument("--min", type=float, default=12.0, help="Minimum clip duration (s)")
    ap.add_argument("--max", type=float, default=60.0, help="Maximum clip duration (s)")
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as f:
        segments = json.load(f)

    total_span = max(s["end"] for s in segments) - min(s["start"] for s in segments)
    print(f"Loaded {len(segments)} scored segments spanning ~{total_span:.0f}s")
    print(f"Selecting {args.clips} clips, target {args.duration:.0f}s "
          f"(min {args.min:.0f}s, max {args.max:.0f}s)\n")

    clips = select_clips(
        segments,
        num_clips=args.clips,
        target_duration=args.duration,
        min_duration=args.min,
        max_duration=args.max,
    )

    if not clips:
        print("No clips could be selected from this input.")
        return

    for c in clips:
        dur = c.end - c.start
        print(f"  Clip {c.index}  [{c.start:6.1f}s -> {c.end:6.1f}s]  "
              f"{dur:4.1f}s  score={c.score:6.2f} (seed {c.seed_score})")
        print(f"           “{c.text[:70]}{'…' if len(c.text) > 70 else ''}”")

    # Simple ASCII timeline so the non-overlap is obvious in a screen recording.
    print("\nTimeline (each '#' is a selected clip, '.' is unused):")
    scale = max(1, int(total_span // 70) + 1)
    width = int(total_span / scale) + 1
    line = ["."] * width
    for c in clips:
        for x in range(int(c.start / scale), int(c.end / scale) + 1):
            if 0 <= x < width:
                line[x] = str(c.index)
    print("  " + "".join(line))

    print("\nJSON output (handed to the Renderer teammate):")
    print(json.dumps(clips_to_dicts(clips), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
