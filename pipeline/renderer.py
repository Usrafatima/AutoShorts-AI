"""
renderer.py — AutoShorts-AI Renderer Module
Intern: Fajar Warriach
Branch: renderer/Fajar-Warriach

PIPELINE POSITION:
------------------
Video → Transcriber → Scorer → Selector → [RENDERER] → Output Shorts
                                                ↑
                                           YOU ARE HERE

HOW IT CONNECTS:
----------------
- Receives : video_path (str) + scored segments (list of dicts from scorer.py)
- Uses     : effects.py → apply_effects_pipeline() for zoom + word captions
- Outputs  : .mp4 files saved to shorts_output/ (matching app.py config)
- Called by: app.py (in the future, when /upload route is completed)
"""

import os
import logging
from pathlib import Path
from moviepy import VideoFileClip, CompositeVideoClip

# Import effects from the same pipeline package
from pipeline.effects import apply_effects_pipeline

# ─────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# CONFIGURATION
# Must match app.py OUTPUT_FOLDER = 'shorts_output'
# ─────────────────────────────────────────────────────────────
OUTPUT_FOLDER = "shorts_output"
TARGET_WIDTH   = 1080
TARGET_HEIGHT  = 1920


# ─────────────────────────────────────────────────────────────
# STEP 1: Crop horizontal video to vertical 9:16
# ─────────────────────────────────────────────────────────────

def crop_to_vertical(clip):
    """
    Crops a landscape video to portrait 9:16 format (1080x1920).

    How it works:
    - Takes the original height
    - Calculates what width gives 9:16 ratio
    - Crops from the horizontal center
    - Resizes to 1080x1920

    Example:
        1920x1080 input → crops to 608x1080 → resizes to 1080x1920
    """
    original_w = clip.w
    original_h = clip.h

    # If already vertical, skip cropping
    if original_h >= original_w:
        logger.info("  Video is already vertical — skipping crop.")
        return clip.resized((TARGET_WIDTH, TARGET_HEIGHT))

    # Calculate new width for 9:16
    new_w = int(original_h * 9 / 16)

    # Center crop horizontally
    x1 = (original_w - new_w) / 2
    x2 = x1 + new_w

    cropped = clip.cropped(x1=x1, y1=0, x2=x2, y2=original_h)
    resized  = cropped.resized((TARGET_WIDTH, TARGET_HEIGHT))

    return resized


# ─────────────────────────────────────────────────────────────
# STEP 2: Render a single short
# ─────────────────────────────────────────────────────────────

def render_clip(video_path, segment, output_filename, apply_effects=True):
    """
    Renders one short from a scored segment.

    Args:
        video_path      : path to source video (from uploads/ folder)
        segment         : dict from scorer.py, must have:
                            - "start" : float  (seconds)
                            - "end"   : float  (seconds)
                            - "text"  : str    (transcript text)
                            - "words" : list   (word-level timestamps)
                            - "score" : float  (from scorer.py)
        output_filename : e.g. "short_1.mp4"
        apply_effects   : True = add zoom + word captions (from effects.py)

    Returns:
        output_path (str) if successful, None if failed
    """
    start = segment.get("start")
    end   = segment.get("end")
    words = segment.get("words", [])
    score = segment.get("score", 0)

    logger.info(f"\n{'='*55}")
    logger.info(f"Rendering : {output_filename}")
    logger.info(f"Segment   : {start}s → {end}s  (score: {score})")
    logger.info(f"{'='*55}")

    # ── Validate inputs ──────────────────────────────────────
    if not os.path.exists(video_path):
        logger.error(f"Video not found: {video_path}")
        return None

    if start is None or end is None:
        logger.error("Segment missing start/end time.")
        return None

    if start >= end:
        logger.error(f"start ({start}) must be less than end ({end}).")
        return None

    # ── Prepare output path ──────────────────────────────────
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)

    try:
        # STEP 1: Load full video
        logger.info("  [1/4] Loading video...")
        full_video = VideoFileClip(video_path)

        # STEP 2: Trim to segment timestamps
        logger.info(f"  [2/4] Trimming {start}s → {end}s...")
        trimmed = full_video.subclipped(start, end)

        # STEP 3: Crop to vertical 9:16
        logger.info("  [3/4] Cropping to 9:16 vertical format...")
        vertical = crop_to_vertical(trimmed)

        # STEP 4: Apply effects (zoom + word captions) from effects.py
        if apply_effects and words:
            logger.info("  [4/4] Applying zoom + word captions...")

            # Adjust word timestamps to be relative to clip start
            relative_words = []
            for w in words:
                relative_words.append({
                    "word" : w["word"],
                    "start": round(w["start"] - start, 3),
                    "end"  : round(w["end"]   - start, 3),
                })

            # Call effects pipeline (defined in effects.py)
            vertical = apply_effects_pipeline(
                video_clip      = vertical,
                word_timestamps = relative_words,
                should_zoom     = True
            )
        else:
            logger.info("  [4/4] Skipping effects (no word timestamps or disabled).")

        # STEP 5: Export final .mp4
        logger.info(f"  [5/5] Exporting → {output_path}")
        vertical.write_videofile(
            output_path,
            codec       = "libx264",
            audio_codec = "aac",
            fps         = 30,
            logger      = None       # suppress moviepy verbose logs
        )

        # Clean up memory
        full_video.close()

        logger.info(f"  ✅ Saved: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"  Rendering failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# STEP 3: Render multiple clips (batch mode)
# ─────────────────────────────────────────────────────────────

def render_shorts(video_path, scored_segments, max_clips=5, apply_effects=True):
    """
    Renders multiple shorts from the top-scored segments.

    This is the MAIN function called by app.py or the pipeline.

    Args:
        video_path      : path to source video
        scored_segments : list of dicts from scorer.py → score_all_segments()
                          Each dict has: start, end, text, words, score
        max_clips       : how many shorts to render (default: top 5)
        apply_effects   : whether to apply zoom + captions

    Returns:
        List of successfully rendered output file paths

    Example usage:
        from pipeline.transcriber import transcribe_video
        from pipeline.scorer      import score_all_segments
        from pipeline.renderer    import render_shorts

        transcript = transcribe_video("video.mp4")
        scored     = score_all_segments(transcript["segments"])
        outputs    = render_shorts("video.mp4", scored, max_clips=3)
    """
    logger.info(f"\nBatch render: top {max_clips} clips from '{video_path}'")

    # Take only top N scored segments
    top_segments = scored_segments[:max_clips]

    if not top_segments:
        logger.warning("No segments to render.")
        return []

    successful = []

    for i, segment in enumerate(top_segments, start=1):
        output_filename = f"short_{i}.mp4"
        result = render_clip(
            video_path      = video_path,
            segment         = segment,
            output_filename = output_filename,
            apply_effects   = apply_effects
        )
        if result:
            successful.append(result)

    # Summary
    logger.info(f"\n{'='*55}")
    logger.info(f"Done: {len(successful)}/{len(top_segments)} shorts rendered.")
    logger.info(f"Output folder: ./{OUTPUT_FOLDER}/")
    logger.info(f"{'='*55}\n")

    return successful


# ─────────────────────────────────────────────────────────────
# STEP 4: Adapter — connect selector.py output to renderer
# ─────────────────────────────────────────────────────────────

def render_from_selection(video_path, scored_segments, selected_clips, apply_effects=True):
    """
    Bridges selector.py's output format to render_clip()'s expected format.

    Args:
        video_path       : path to source video
        scored_segments  : full list of dicts from scorer.py
                            (each has start, end, score, text, and
                             optionally "words" if available)
        selected_clips   : list of (start, end, score) tuples from
                            selector.py -> select_clips()
        apply_effects    : whether to apply zoom + captions

    Returns:
        List of successfully rendered output file paths

    Example usage:
        from pipeline.scorer   import score_all_segments
        from pipeline.selector import select_clips
        from pipeline.renderer import render_from_selection

        scored   = score_all_segments(segments)
        selected = select_clips(scored, num_clips=3)
        outputs  = render_from_selection("video.mp4", scored, selected)
    """
    logger.info(f"\nMatching {len(selected_clips)} selected clips to scored segments...")

    successful = []

    for i, (start, end, score) in enumerate(selected_clips, start=1):
        # Find the original segment that overlaps this selected clip
        matched_segment = None
        for seg in scored_segments:
            seg_start = float(seg.get("start", 0))
            seg_end = float(seg.get("end", 0))
            # Check for overlap between selected clip and original segment
            if not (end <= seg_start or start >= seg_end):
                matched_segment = seg
                break

        if matched_segment is None:
            logger.warning(f"  No matching segment found for clip {i} ({start}s-{end}s) — skipping.")
            continue

        # Build the dict render_clip() expects
        segment_for_render = {
            "start": start,
            "end": end,
            "text": matched_segment.get("text", ""),
            "words": matched_segment.get("words", []),
            "score": score,
        }

        output_filename = f"short_{i}.mp4"
        result = render_clip(
            video_path=video_path,
            segment=segment_for_render,
            output_filename=output_filename,
            apply_effects=apply_effects
        )
        if result:
            successful.append(result)

    logger.info(f"\n{'='*55}")
    logger.info(f"Done: {len(successful)}/{len(selected_clips)} shorts rendered.")
    logger.info(f"Output folder: ./{OUTPUT_FOLDER}/")
    logger.info(f"{'='*55}\n")

    return successful


# ─────────────────────────────────────────────────────────────
# DEMO / TEST
# Run: python pipeline/renderer.py
# Place a video named test_video.mp4 in the project root first
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from pipeline.transcriber import transcribe_video
    from pipeline.scorer      import score_all_segments

    TEST_VIDEO = "test_video.mp4"

    if not os.path.exists(TEST_VIDEO):
        print(f"\n[DEMO] No test video found.")
        print(f"[DEMO] Place a video named 'test_video.mp4' in the project root.")
        print(f"[DEMO] Then run: python pipeline/renderer.py\n")
    else:
        print(f"\n[DEMO] Running full pipeline on: {TEST_VIDEO}")

        # Step 1: Transcribe
        print("[DEMO] Step 1: Transcribing...")
        transcript = transcribe_video(TEST_VIDEO)

        # Step 2: Score segments
        print("[DEMO] Step 2: Scoring segments...")
        scored = score_all_segments(transcript["segments"])

        # Step 3: Render top 3 shorts
        print("[DEMO] Step 3: Rendering top 3 shorts...")
        outputs = render_shorts(TEST_VIDEO, scored, max_clips=3)

        print(f"\n[DEMO] Rendered files:")
        for f in outputs:
            print(f"  → {f}")