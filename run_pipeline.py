import os
import sys
import logging
import json
from pathlib import Path

# Pipeline imports - strictly using what's in the pipeline folder
from pipeline.transcriber import transcribe_video
from pipeline.Audio import analyze_audio
from pipeline.selcector import score_all_segments  # Scoring logic
from pipeline.selector import select_clips       # Window selection logic
from pipeline.effects import apply_effects_pipeline

# Import moviepy for rendering
try:
    from moviepy.video.io.VideoFileClip import VideoFileClip
except ImportError:
    logging.warning("moviepy not found. Rendering will be skipped.")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def render_shorts(video_path, selected_clips, transcript_data, output_dir):
    """
    Renders the selected Clip objects as 9:16 shorts.
    Ensures Audio is preserved even if effects fail.
    """
    if 'VideoFileClip' not in globals():
        logger.error("MoviePy is not installed. Skipping rendering.")
        return

    logger.info(f"Starting render for {len(selected_clips)} shorts with Enhanced Audio Fix...")
    
    try:
        # Load main video
        video = VideoFileClip(video_path)
        all_words = transcript_data.get('words', [])
        
        for clip in selected_clips:
            idx = clip.index
            start_t = clip.start
            end_t = clip.end
            
            logger.info(f"Processing Short {idx}: [{start_t}s - {end_t}s]")
            
            # 1. Extract subclip
            # We keep the audio of the subclip very carefully
            subclip = video.subclipped(start_t, end_t)
            original_audio = subclip.audio
            
            # 2. Apply 9:16 Center Crop
            w, h = subclip.size
            target_ratio = 9/16
            if w/h > target_ratio:
                new_w = h * target_ratio
                processed_subclip = subclip.cropped(x_center=w/2, width=new_w)
            else:
                new_h = w / target_ratio
                processed_subclip = subclip.cropped(y_center=h/2, height=new_h)
            
            # 3. Apply effects pipeline (Zoom + Captions)
            try:
                clip_words = [
                    {"word": w['word'], "start": w['start'] - start_t, "end": w['end'] - start_t} 
                    for w in all_words 
                    if w['start'] >= start_t and w['end'] <= end_t
                ]
                
                final_short = apply_effects_pipeline(
                    processed_subclip, 
                    word_timestamps=clip_words,
                    should_zoom=True
                )
                
                # RE-ATTACH AUDIO: Very important for MoviePy v2
                if original_audio is not None:
                    final_short = final_short.with_audio(original_audio)
                    
            except Exception as effect_error:
                logger.warning(f"Effects failed (likely font): {effect_error}. Using plain crop with Audio.")
                # Fallback also needs audio re-attached
                final_short = processed_subclip
                if original_audio is not None:
                    final_short = final_short.with_audio(original_audio)

            # 4. Export with High-Compatibility Audio Settings
            output_filename = os.path.join(output_dir, f"short_{idx}.mp4")
            logger.info(f"Writing video file: {output_filename}")
            
            final_short.write_videofile(
                output_filename, 
                codec="libx264", 
                audio_codec="aac", 
                audio=True,        # Must be True
                fps=24,
                logger=None,
                temp_audiofile=os.path.join(output_dir, f"temp_audio_{idx}.m4a"),
                remove_temp=True
            )
            
        video.close()
    except Exception as e:
        logger.error(f"Rendering failed: {str(e)}")

def run_pipeline(video_path, output_dir="shorts_output", num_shorts=15, model_size="base"):
    """
    Main orchestration function. Updated default shorts to 15.
    """
    try:
        if not os.path.exists(video_path):
            logger.error(f"Input video not found: {video_path}")
            return

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        logger.info(f"--- STAGE 1: Initializing Pipeline for {os.path.basename(video_path)} ---")
        
        # 2. Transcription
        logger.info("--- STAGE 2: Transcribing Video ---")
        transcript_data = transcribe_video(video_path, model_size=model_size, output_dir=output_dir)
        
        # 3. Audio Analysis
        logger.info("--- STAGE 3: Analyzing Audio Features ---")
        audio_features = analyze_audio(video_path, os.path.join(output_dir, "audio_features.json"))
        
        # 4. Scoring
        logger.info("--- STAGE 4: Scoring Transcript Segments ---")
        segments = transcript_data.get('segments', [])
        scored_segments = score_all_segments(segments)
        
        # Boost scores with volume spikes
        spikes = audio_features.get('volume_spikes', [])
        for seg in scored_segments:
            for spike in spikes:
                if seg['start'] <= spike['time'] <= seg['end']:
                    seg['score'] = seg.get('score', 0) + 2.0
                    break
        
        # 5. Selection
        logger.info(f"--- STAGE 5: Selecting Top {num_shorts} Viral Windows ---")
        selected_clips = select_clips(
            scored_segments, 
            num_clips=num_shorts,
            target_duration=30.0,
            min_duration=15.0,
            max_duration=60.0
        )
        
        if not selected_clips:
            logger.warning("No clips were selected for rendering.")
            return

        # 6. Rendering
        logger.info("--- STAGE 6: Rendering 9:16 Shorts with Audio Fix ---")
        render_shorts(video_path, selected_clips, transcript_data, output_dir)

        logger.info(f"--- STAGE 7: Pipeline Successful! Shorts saved in {output_dir} ---")

    except Exception as e:
        logger.error(f"Pipeline Error: {str(e)}")
        raise

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_pipeline.py <video_path> [output_dir] [num_shorts]")
    else:
        video_input = sys.argv[1]
        out_dir = sys.argv[2] if len(sys.argv) > 2 else "shorts_output"
        # Use 15 as default if not provided
        shorts_count = int(sys.argv[3]) if len(sys.argv) > 3 else 15
        run_pipeline(video_input, output_dir=out_dir, num_shorts=shorts_count)
