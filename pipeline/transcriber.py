"""
AutoShorts AI — Transcription Lead Module
"""

import os
import json
import subprocess
import logging
from pathlib import Path
from typing import Optional

from faster_whisper import WhisperModel

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SUPPORTED_MODELS = ("tiny", "base", "small", "medium", "large-v2")


class Transcriber:

    def __init__(self, model_size="base", device="cpu", compute_type="int8", language=None):
        if model_size not in SUPPORTED_MODELS:
            raise ValueError(f"model_size must be one of {SUPPORTED_MODELS}")
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self._model = None

    def transcribe(self, video_path, output_dir=None, keep_wav=False):
        video_path = Path(video_path).resolve()
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        output_dir = Path(output_dir) if output_dir else video_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)

        wav_path = output_dir / (video_path.stem + "_audio.wav")
        json_path = output_dir / (video_path.stem + "_transcript.json")

        logger.info(f"Extracting audio from: {video_path.name}")
        self._extract_audio(video_path, wav_path)

        logger.info(f"Loading Whisper model: '{self.model_size}'")
        model = self._load_model()

        logger.info("Transcribing... (takes a few minutes on CPU)")
        result = self._run_transcription(model, str(wav_path))

        result["video_path"] = str(video_path)
        self._save_transcript(result, json_path)
        logger.info(f"Transcript saved → {json_path}")

        if not keep_wav and wav_path.exists():
            wav_path.unlink()

        return result

    def _load_model(self):
        if self._model is None:
            self._model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
        return self._model

    def _extract_audio(self, video_path, wav_path):
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            str(wav_path),
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed:\n{result.stderr.decode('utf-8', errors='replace')}")

    def _run_transcription(self, model, audio_path):
        segments_iter, info = model.transcribe(
            audio_path,
            language=self.language,
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        segments = []
        all_words = []
        full_text_parts = []

        for seg in list(segments_iter):
            seg_words = []
            if seg.words:
                for w in seg.words:
                    word_entry = {
                        "word": w.word.strip(),
                        "start": round(w.start, 3),
                        "end": round(w.end, 3),
                        "probability": round(w.probability, 4),
                    }
                    seg_words.append(word_entry)
                    all_words.append(word_entry)

            segments.append({
                "id": seg.id,
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "text": seg.text.strip(),
                "words": seg_words,
            })
            full_text_parts.append(seg.text.strip())

        return {
            "language": info.language,
            "language_probability": round(info.language_probability, 4),
            "duration": round(segments[-1]["end"] if segments else 0.0, 3),
            "full_text": " ".join(full_text_parts),
            "segments": segments,
            "words": all_words,
        }

    @staticmethod
    def _save_transcript(data, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def transcribe_video(video_path, model_size="base", output_dir=None, language=None, keep_wav=False):
    t = Transcriber(model_size=model_size, language=language)
    return t.transcribe(video_path, output_dir=output_dir, keep_wav=keep_wav)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("video")
    parser.add_argument("--model", default="base", choices=SUPPORTED_MODELS)
    parser.add_argument("--language", default=None)
    parser.add_argument("--keep-wav", action="store_true")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    result = transcribe_video(args.video, args.model, args.output_dir, args.language, args.keep_wav)
    print(f"\nLanguage : {result['language']}")
    print(f"Duration : {result['duration']}s")
    print(f"Segments : {len(result['segments'])}")
    print(f"Words    : {len(result['words'])}")
    print(f"\n{result['full_text'][:300]}...")
