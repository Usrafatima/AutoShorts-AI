import os
import json
import subprocess
import numpy as np
import librosa

def extract_audio(video_path: str, audio_path: str) -> str:
    """
    Extracts audio from a video file and saves it in WAV format (16kHz, Mono).
    Uses FFmpeg via subprocess to ensure robustness on Windows/Linux.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(audio_path)), exist_ok=True)

    # Run FFmpeg command to extract 16kHz mono WAV
    command = [
        'ffmpeg',
        '-y',                 # Overwrite output files without asking
        '-i', video_path,     # Input video file
        '-vn',                # Disable video stream
        '-acodec', 'pcm_s16le', # Codec PCM 16-bit
        '-ar', '16000',       # Sample rate 16000 Hz
        '-ac', '1',           # Mono channel
        audio_path
    ]

    try:
        # Run command capturing stdout and stderr
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return audio_path
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8', errors='ignore')
        raise RuntimeError(f"FFmpeg audio extraction failed: {error_msg}")

def load_audio(audio_path: str) -> tuple[np.ndarray, float]:
    """
    Loads WAV/MP3 audio file using Librosa.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    y, sr = librosa.load(audio_path, sr=None)
    return y, sr

def calculate_rms_energy(y: np.ndarray, frame_length: int = 2048, hop_length: int = 512) -> np.ndarray:
    """
    Calculates Root Mean Square (RMS) energy values for the audio signal per frame.
    """
    if len(y) == 0:
        return np.array([])
    
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)
    return rms[0]

def detect_pauses_and_silence(
    y: np.ndarray, 
    sr: float, 
    silence_threshold_db: float = 40.0, 
    min_pause_duration: float = 1.5
) -> tuple[list[dict], list[dict]]:
    """
    Identifies silent regions and long pauses (duration > min_pause_duration).
    silence_threshold_db is the threshold (in dB) below the peak reference to consider as silence.
    Returns:
       tuple: (silent_regions, pauses)
    """
    if len(y) == 0:
        return [], []

    silent_regions = []
    pauses = []
    total_duration = float(len(y) / sr)

    # Check if the signal is essentially completely silent (peak absolute amplitude < 1e-4)
    if np.max(np.abs(y)) < 1e-4:
        silent_regions.append({"start": 0.0, "end": total_duration})
    else:
        # Detect non-silent intervals (librosa returns samples)
        non_silent_intervals = librosa.effects.split(y, top_db=silence_threshold_db)
        
        if len(non_silent_intervals) == 0:
            # The entire audio file is silent
            silent_regions.append({"start": 0.0, "end": total_duration})
        else:
            # Check if there is silence at the very beginning
            first_start = float(non_silent_intervals[0][0] / sr)
            if first_start > 0.05:  # ignore extremely tiny noise gate triggers
                silent_regions.append({"start": 0.0, "end": first_start})

            # Check silence between non-silent segments
            for i in range(len(non_silent_intervals) - 1):
                start_silence = float(non_silent_intervals[i][1] / sr)
                end_silence = float(non_silent_intervals[i+1][0] / sr)
                if end_silence > start_silence:
                    silent_regions.append({"start": start_silence, "end": end_silence})

            # Check if there is silence at the end
            last_end = float(non_silent_intervals[-1][1] / sr)
            if total_duration - last_end > 0.05:
                silent_regions.append({"start": last_end, "end": total_duration})

    # Filter pauses based on duration
    for region in silent_regions:
        duration = float(region["end"] - region["start"])
        if duration >= min_pause_duration:
            pauses.append({
                "start": round(float(region["start"]), 2),
                "end": round(float(region["end"]), 2)
            })

    # Format silences rounded to 2 decimal places
    formatted_silences = [
        {"start": round(float(r["start"]), 2), "end": round(float(r["end"]), 2)} 
        for r in silent_regions
    ]

    return formatted_silences, pauses

def detect_volume_spikes(
    rms: np.ndarray, 
    sr: float, 
    hop_length: int = 512, 
    threshold_multiplier: float = 2.0, 
    min_distance_sec: float = 2.0
) -> list[dict]:
    """
    Identifies moments (timestamps) where the volume significantly exceeds average levels.
    Uses mean + multiplier * std of RMS energy to identify peaks.
    """
    if len(rms) == 0:
        return []

    mean_rms = np.mean(rms)
    std_rms = np.std(rms)
    
    # Calculate threshold for spike
    threshold = mean_rms + threshold_multiplier * std_rms
    
    # Find indices where rms exceeds the threshold
    spike_indices = np.where(rms > threshold)[0]
    
    spikes = []
    last_spike_time = -min_distance_sec

    for idx in spike_indices:
        time = idx * hop_length / sr
        if time - last_spike_time >= min_distance_sec:
            spikes.append({
                "time": round(float(time), 2)
            })
            last_spike_time = time

    return spikes

def analyze_audio(
    video_path: str, 
    output_json_path: str,
    temp_wav_path: str = None,
    silence_threshold_db: float = 40.0,
    min_pause_duration: float = 1.5,
    spike_threshold_multiplier: float = 2.0
) -> dict:
    """
    Main function to run the full audio analysis pipeline:
    1. Extract audio from video.
    2. Load audio with Librosa.
    3. Calculate RMS energy.
    4. Detect silence and pauses.
    5. Detect volume spikes.
    6. Generate feature JSON.
    """
    if temp_wav_path is None:
        import uuid
        temp_wav_path = f"temp_extracted_{uuid.uuid4().hex}.wav"

    try:
        # Step 1: Extract audio
        print(f"Extracting audio from {video_path}...")
        extract_audio(video_path, temp_wav_path)

        # Step 2: Load audio
        print(f"Loading audio from {temp_wav_path}...")
        y, sr = load_audio(temp_wav_path)

        # Step 3: Calculate RMS
        print("Calculating RMS energy...")
        rms = calculate_rms_energy(y)

        # Calculate metrics
        avg_energy = float(np.mean(rms)) if len(rms) > 0 else 0.0
        max_energy = float(np.max(rms)) if len(rms) > 0 else 0.0

        # Step 4: Detect pauses and silence
        print("Detecting silence and pauses...")
        silence_regions, pauses = detect_pauses_and_silence(
            y, sr, 
            silence_threshold_db=silence_threshold_db, 
            min_pause_duration=min_pause_duration
        )

        # Step 5: Detect volume spikes
        print("Detecting volume spikes...")
        spikes = detect_volume_spikes(
            rms, sr, 
            threshold_multiplier=spike_threshold_multiplier
        )

        # Step 6: Generate JSON
        audio_features = {
            "avg_energy": round(avg_energy, 4),
            "max_energy": round(max_energy, 4),
            "silence_segments": silence_regions,
            "pauses": pauses,
            "volume_spikes": spikes
        }

        # Save JSON output
        os.makedirs(os.path.dirname(os.path.abspath(output_json_path)), exist_ok=True)
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(audio_features, f, indent=4)

        print(f"Audio features successfully saved to {output_json_path}")
        return audio_features

    finally:
        # Clean up temporary WAV file if it exists
        if os.path.exists(temp_wav_path):
            try:
                os.remove(temp_wav_path)
                print("Temporary WAV file cleaned up.")
            except Exception as e:
                print(f"Warning: Could not remove temporary WAV file {temp_wav_path}: {e}")

if __name__ == "__main__":
    import sys
    
    print("=== Step 1: Verify Dependencies ===")
    try:
        import numpy as np
        import librosa
        print(f"numpy: {np.__version__}")
        print(f"librosa: {librosa.__version__}")
        # Verify FFmpeg
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print("FFmpeg is available in system PATH.")
    except Exception as e:
        print(f"Dependency check failed: {e}")
        sys.exit(1)

    # Use paths relative to this script so it runs correctly from any working directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Check multiple possible locations/names for sample.mp4
    video_file = os.path.join(base_dir, "sample.mp4")
    if not os.path.exists(video_file):
        if os.path.exists(os.path.join(base_dir, "sample.mp4.mp4")):
            video_file = os.path.join(base_dir, "sample.mp4.mp4")
        elif os.path.exists(os.path.join(os.path.dirname(base_dir), "sample.mp4")):
            video_file = os.path.join(os.path.dirname(base_dir), "sample.mp4")
            
    temp_wav = os.path.join(base_dir, "temp_extracted_audio.wav")
    output_json = os.path.join(base_dir, "audio_features.json")

    print("\n=== Step 5: Validate Audio Extraction ===")
    if os.path.exists(temp_wav):
        os.remove(temp_wav)
    try:
        extracted_path = extract_audio(video_file, temp_wav)
        if os.path.exists(temp_wav):
            print(f"SUCCESS: WAV file successfully created at: {temp_wav}")
        else:
            print(f"FAILED: WAV file was not created.")
    except Exception as e:
        print(f"Audio Extraction failed: {e}")

    print("\n=== Step 6: Validate Audio Loading ===")
    y, sr = None, None
    try:
        y, sr = load_audio(temp_wav)
        print(f"SUCCESS: Loaded audio signal with shape {y.shape} and sample rate {sr}")
    except Exception as e:
        print(f"Audio Loading failed: {e}")

    print("\n=== Step 7: Validate RMS Energy Detection ===")
    rms = None
    if y is not None:
        try:
            rms = calculate_rms_energy(y)
            avg_energy = float(np.mean(rms)) if len(rms) > 0 else 0.0
            max_energy = float(np.max(rms)) if len(rms) > 0 else 0.0
            print(f"RMS Energy values generated. Count: {len(rms)}")
            print(f"Average Energy: {avg_energy:.4f}")
            print(f"Maximum Energy: {max_energy:.4f}")
            if avg_energy > 0 and max_energy > 0:
                print("SUCCESS: Average and maximum energy are greater than 0.")
            else:
                print("FAILED: Average and/or maximum energy not greater than 0.")
        except Exception as e:
            print(f"RMS Calculation failed: {e}")
    else:
        print("SKIPPED: Audio signal y not loaded.")

    print("\n=== Step 8 & 9: Validate Silence and Pause Detection ===")
    if y is not None and sr is not None:
        try:
            silence_regions, pauses = detect_pauses_and_silence(y, sr, min_pause_duration=1.5)
            print(f"Silence regions detected: {silence_regions}")
            print(f"Pauses detected (duration >= 1.5s): {pauses}")
            print("SUCCESS: Silence and pauses detected successfully.")
        except Exception as e:
            print(f"Silence/Pause Detection failed: {e}")
    else:
        print("SKIPPED: Audio signal y or sr not loaded.")

    print("\n=== Step 10: Validate Volume Spike Detection ===")
    if rms is not None and sr is not None:
        try:
            spikes = detect_volume_spikes(rms, sr)
            print(f"Volume spikes detected: {spikes}")
            print("SUCCESS: Volume spikes detected successfully.")
        except Exception as e:
            print(f"Volume Spike Detection failed: {e}")
    else:
        print("SKIPPED: RMS energy or sample rate not available.")

    print("\n=== Step 4 & 11: Execute Pipeline and Generate JSON Output ===")
    if os.path.exists(output_json):
        os.remove(output_json)
    try:
        result = analyze_audio(video_path=video_file, output_json_path=output_json, temp_wav_path=temp_wav)
        print(f"Result returned: {json.dumps(result, indent=2)}")
        if os.path.exists(output_json):
            print(f"SUCCESS: JSON file generated at {output_json}")
        else:
            print("FAILED: JSON file was not generated.")
    except Exception as e:
        print(f"Pipeline execution failed: {e}")

    print("\n=== Step 12: Error Handling ===")
    # Missing video file
    print("Testing missing video file:")
    try:
        analyze_audio("non_existent_video.mp4", "features.json")
        print("FAILED: Did not raise error for missing file.")
    except FileNotFoundError as e:
        print(f"SUCCESS: Correctly raised FileNotFoundError: {e}")
    except Exception as e:
        print(f"FAILED: Raised unexpected error: {e}")

    # Corrupted video file
    print("Testing corrupted video file:")
    corrupt_file = "corrupted_test.mp4"
    with open(corrupt_file, "w") as f:
        f.write("corrupted content")
    try:
        analyze_audio(corrupt_file, "features.json")
        print("FAILED: Did not raise error for corrupted file.")
    except Exception as e:
        print(f"SUCCESS: Correctly raised error for corrupted file: {e}")
    finally:
        if os.path.exists(corrupt_file):
            os.remove(corrupt_file)

    # Silent audio file test
    print("Testing silent audio file:")
    import soundfile as sf
    silent_wav = "silent_test.wav"
    try:
        # Generate 5 seconds of silence at 16kHz
        sf.write(silent_wav, np.zeros(16000 * 5), 16000)
        y_silent, sr_silent = load_audio(silent_wav)
        rms_silent = calculate_rms_energy(y_silent)
        avg_silent = float(np.mean(rms_silent)) if len(rms_silent) > 0 else 0.0
        silence_regions, pauses = detect_pauses_and_silence(y_silent, sr_silent, min_pause_duration=1.5)
        print(f"Silent audio - Average energy: {avg_silent}")
        print(f"Silent audio - Silence regions: {silence_regions}")
        print(f"Silent audio - Pauses: {pauses}")
        if len(pauses) > 0 and pauses[0]["end"] - pauses[0]["start"] >= 4.9:
            print("SUCCESS: Silent audio file correctly detected as silent.")
        else:
            print("FAILED: Silent audio file did not return expected silence segments.")
    except Exception as e:
        print(f"FAILED: Silent audio file test raised exception: {e}")
    finally:
        if os.path.exists(silent_wav):
            os.remove(silent_wav)

    # Clean up test outputs
    if os.path.exists(temp_wav):
        os.remove(temp_wav)

