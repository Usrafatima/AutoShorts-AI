import json
import sys
sys.path.insert(0, 'pipeline')

from faster_whisper import WhisperModel
from scorer import score_all_segments

def select_clips(segments, num_clips=3, min_duration=15.0, max_duration=60.0):
    sorted_segments = sorted(segments, key=lambda x: x.get("score", 0), reverse=True)
    selected = []
    for seg in sorted_segments:
        if len(selected) >= num_clips:
            break
        start = float(seg["start"])
        end = float(seg["end"])
        if (end - start) < min_duration:
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

# ===== YOUR VIDEO PATH =====
VIDEO_PATH = "C:/Users/ABC/Desktop/test_video.mp4"
# ===========================

print("Loading Whisper model...")
model = WhisperModel("tiny", device="cpu", compute_type="int8")

print("Transcribing video...")
segments, info = model.transcribe(VIDEO_PATH, word_timestamps=True)

segment_list = []
for seg in segments:
    words = [{"word": w.word, "start": w.start, "end": w.end} for w in seg.words]
    segment_list.append({
        "text": seg.text,
        "start": seg.start,
        "end": seg.end,
        "words": words
    })

print(f"Found {len(segment_list)} segments")
scored = score_all_segments(segment_list)
clips = select_clips(scored, num_clips=3)

print("\n===== BEST CLIPS FROM YOUR VIDEO =====")
for i, (start, end, score) in enumerate(clips):
    print(f"Clip {i+1}: {int(start//60)}m{int(start%60)}s → {int(end//60)}m{int(end%60)}s (score: {score})")