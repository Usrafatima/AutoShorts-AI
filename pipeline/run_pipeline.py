import json
import sys
sys.path.insert(0, 'pipeline')

from scorer import score_all_segments
from selector import select_clips

with open("pipeline/sample_scored.json") as f:
    segments = json.load(f)

print(f"Loaded {len(segments)} segments")
scored = score_all_segments(segments)
clips = select_clips(scored, num_clips=3)

print("\n===== BEST CLIPS =====")
for i, (start, end, score) in enumerate(clips):
    print(f"Clip {i+1}: {int(start//60)}m{int(start%60)}s → {int(end//60)}m{int(end%60)}s (score: {score})")