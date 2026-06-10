import os
from moviepy.video.io.VideoFileClip import VideoFileClip # New v2 way
# Import the pipeline master runner you just built
from pipeline.effects import apply_effects_pipeline



# Create the folder automatically if it's not there
os.makedirs("uploads", exist_ok=True)
os.makedirs("shorts_output", exist_ok=True)

def run_local_effects_test():
    print("🚀 Starting Effects Module Test...")
    
    # 1. Path setup (Use a small 10-15 second video clip for testing)
    # Put a test video in your uploads/ folder as mentioned in your docs
    video_path = "uploads/test_input.mp4" 
    output_dir = "shorts_output"
    output_path = os.path.join(output_dir, "test_short_with_effects.mp4")
    
    if not os.path.exists(video_path):
        print(f"❌ Error: Please place a sample video at '{video_path}' to run the test.")
        return

    os.makedirs(output_dir, exist_ok=True)

    # 2. Mocking Whisper timestamps (Simulating what transcriber.py will give you)
    # This lets you test your word highlights immediately without waiting for AI transcription
    mock_word_timestamps = [
        {"word": "Welcome", "start": 0.5, "end": 1.0},
        {"word": "to", "start": 1.0, "end": 1.3},
        {"word": "AutoShorts", "start": 1.3, "end": 2.0},
        {"word": "AI", "start": 2.0, "end": 2.5},
        {"word": "local", "start": 3.0, "end": 3.6},
        {"word": "video", "start": 3.6, "end": 4.1},
        {"word": "editor.", "start": 4.1, "end": 4.8}
    ]

    print(f"🎬 Loading test video: {video_path}")
    video_clip = VideoFileClip(video_path)
    
    # Optional: Trim down to 5-10 seconds so the test render finishes in seconds
    test_clip = video_clip.subclipped(0, min(10, video_clip.duration))

    print("✨ Applying zoom and animated word captions...")
    # 3. Call your pipeline module
    final_clip = apply_effects_pipeline(test_clip, mock_word_timestamps, should_zoom=True)

    print(f"⏳ Rendering test output to: {output_path} (Using CPU threads)...")
    # 4. Render using standard CPU processing
    final_clip.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        threads=4,  # Adjust based on your CPU threads
        logger="bar" # Shows progress bar in terminal
    )
    
    # Close clips to free up system resources
    test_clip.close()
    video_clip.close()
    final_clip.close()
    print("✅ Test complete! Check 'shorts_output/test_short_with_effects.mp4' to verify visual zoom and captions.")

if __name__ == "__main__":
    run_local_effects_test()