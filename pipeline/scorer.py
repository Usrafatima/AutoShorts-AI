
import json
from collections import Counter
from typing import Dict, Any

from keybert import KeyBERT
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


FILLER_WORDS = {
    "um", "uh", "like", "you know", "so", "basically",
    "actually", "literally", "right", "okay",
}

STOP_WORDS = {
    "the", "and", "you", "your", "that", "this",
    "with", "have", "from", "they", "them",
    "when", "what", "will", "would", "could",
    "should", "can", "for", "are", "was",
    "were", "been", "into", "about", "than",
    "then", "their", "there", "here"
}


class TranscriptScorer:

    def __init__(self):
        self.kw_model = KeyBERT()
        self.sentiment_analyzer = SentimentIntensityAnalyzer()

    # -------------------------
    # MAIN ENTRY
    # -------------------------

    
    def score(self, transcript: Dict[str, Any]):

        words = transcript.get("words", [])
        segments = transcript.get("segments", [])

        word_list = [
            w["word"].lower()
            for w in words
            if isinstance(w, dict) and w.get("word")
        ]

        filler_count = self._filler_count(word_list)

        pause_score, pause_bonus = self._pause_score(segments)

        #  NEW VIRAL METRICS
        hook = self._hook_strength(segments)
        emotion = self._emotional_intensity(word_list)
        curiosity = self._curiosity_density(word_list)
        retention = self._retention_prediction(
            hook, emotion, curiosity,
            pause_bonus, pause_score
        )

        return {
            "overall_score": self._overall_score(word_list, segments, filler_count, pause_score, pause_bonus),

            "keyword_score": self._keyword_score(word_list),
            "clarity_score": self._clarity_score(word_list, filler_count),
            "pace_score": self._pace_score(segments),
            "pause_score": pause_score,
            "pause_bonus": pause_bonus,

            "sentence_structure_score": self._sentence_structure_score(segments),
            "sentence_energy_score": self._sentence_energy_score(segments),

            "repetition_score": self._repetition_score(word_list),

            "hook_strength": hook,
            "emotional_intensity": emotion,
            "curiosity_density": curiosity,
            "retention_prediction": retention,

            "sentiment_score": self._sentiment_score(word_list),

            "filler_count": filler_count,
            "top_keywords": self._top_keywords_keybert(word_list),
        }

    # -------------------------
    # OVERALL SCORE
    # -------------------------
    def _overall_score(self, words, segments, filler_count, pause_score, pause_bonus):

        clarity = self._clarity_score(words, filler_count)
        keyword = self._keyword_score(words)
        pace = self._pace_score(segments)
        sentence = self._sentence_structure_score(segments)
        energy = self._sentence_energy_score(segments)
        repetition = self._repetition_score(words)

        sentiment = self._sentiment_score(words)

        
        score = (
    clarity * 0.14 +
    keyword * 0.10 +
    pace * 0.08 +
    sentence * 0.08 +
    energy * 0.08 +
    pause_score * 0.08 +
    repetition * 0.08 +
    pause_bonus * 0.10 +
    self._hook_strength(segments) * 0.08 +
    self._emotional_intensity(words) * 0.08 +
    self._curiosity_density(words) * 0.08 +
    sentiment * 0.10
)
        

        return round(min(max(score, 0), 100), 2)

    # -------------------------
    # KEYWORD SCORE
    # -------------------------
    def _keyword_score(self, words):
        clean = [
            w for w in words
            if w not in FILLER_WORDS
            and w not in STOP_WORDS
            and len(w) > 2
        ]

        if not clean:
            return 0

        return round((len(set(clean)) / len(clean)) * 100, 2)

    # -------------------------
    # CLARITY
    # -------------------------
    def _clarity_score(self, words, filler_count):
        return round((1 - filler_count / len(words)) * 100, 2) if words else 0

    # -------------------------
    # PACING
    # -------------------------
    def _pace_score(self, segments):
        if not segments:
            return 0

        durations = [
            seg["end"] - seg["start"]
            for seg in segments
            if "start" in seg and "end" in seg
        ]

        avg = sum(durations) / len(durations)

        if 2 <= avg <= 6:
            return 90
        if 1 <= avg < 2 or 6 < avg <= 8:
            return 70
        return 50

    # -------------------------
    # PAUSE SCORE + BONUS
    # -------------------------
    def _pause_score(self, segments):
        if not segments or len(segments) < 2:
            return 70, 0

        pauses = []

        for i in range(1, len(segments)):
            gap = segments[i]["start"] - segments[i - 1]["end"]
            if gap > 0:
                pauses.append(gap)

        if not pauses:
            return 90, 0

        avg = sum(pauses) / len(pauses)

        base = 90 if avg <= 0.5 else 70 if avg <= 1.5 else 50

        good = sum(1 for p in pauses if 0.4 <= p <= 1.0)
        bonus = (good / len(pauses)) * 100

        return base, round(min(bonus, 100), 2)

    # -------------------------
    # SENTENCE STRUCTURE
    # -------------------------
    def _sentence_structure_score(self, segments):
        lengths = [len(seg.get("text", "").split()) for seg in segments if seg.get("text")]
        if not lengths:
            return 0

        avg = sum(lengths) / len(lengths)
        return 90 if 8 <= avg <= 20 else 70 if 5 <= avg < 8 or avg <= 30 else 50

    # -------------------------
    # ENERGY
    # -------------------------
    def _sentence_energy_score(self, segments):
        words = [len(seg.get("text", "").split()) for seg in segments if seg.get("text")]
        if not words:
            return 0

        avg = sum(words) / len(words)
        return 90 if 10 <= avg <= 18 else 70 if 7 <= avg < 10 or avg <= 25 else 50

    # -------------------------
    # REPETITION
    # -------------------------
    def _repetition_score(self, words):
        clean = [
            w for w in words
            if w not in FILLER_WORDS and w not in STOP_WORDS and len(w) > 2
        ]

        if len(clean) < 5:
            return 50

        freq = Counter(clean)

        total = len(clean)
        unique = len(freq)

        diversity = unique / total
        pressure = sum((c / total) ** 2 for c in freq.values())

        return round(((diversity * 0.6) + ((1 - pressure) * 0.4)) * 100, 2)

    # -------------------------
    # FILLER COUNT
    # -------------------------
    def _filler_count(self, words):
        return sum(1 for w in words if w in FILLER_WORDS)

    # -------------------------
    #  HOOK STRENGTH (FIRST 3 SECONDS)
    # -------------------------
    def _hook_strength(self, segments):
        if not segments:
            return 50

        first = segments[0].get("text", "").lower()
        if not first:
            return 50

        strong_words = {"why", "how", "what", "imagine", "stop", "you", "now", "secret", "hack"}
        score = sum(1 for w in strong_words if w in first)

        length_bonus = min(len(first.split()) / 10 * 100, 50)

        return round(min(50 + score * 15 + length_bonus, 100), 2)

    # -------------------------
    #   EMOTIONAL INTENSITY
    # -------------------------
    def _emotional_intensity(self, words):

        if not words:
           return 0

        text = " ".join(words)

        scores = self.sentiment_analyzer.polarity_scores(text)

        pos = scores["pos"]
        neg = scores["neg"]

        intensity = (pos + neg) * 100

        return round(min(intensity, 100), 2)

    
    # -------------------------
     # SENTIMENT SCORE
     # -------------------------
    def _sentiment_score(self, words):

        if not words:
          return 50

        text = " ".join(words)

        scores = self.sentiment_analyzer.polarity_scores(text)

        compound = scores["compound"]

        # Normalize to a realistic range
        score = 50 + (compound * 30)

        return round(max(0, min(score, 100)), 2)

    # -------------------------
    #  CURIOSITY DENSITY
    # -------------------------
    def _curiosity_density(self, words):
        question_words = {"why", "how", "what", "when", "where"}

        if not words:
            return 0

        score = sum(1 for w in words if w in question_words)
        return round(min((score / max(len(words), 1)) * 500, 100), 2)

    # -------------------------
    # RETENTION PREDICTION
    # -------------------------
    def _retention_prediction(self, hook, emotion, curiosity, pause_bonus, pause_score):
        return round(
            (hook * 0.30 +
             emotion * 0.20 +
             curiosity * 0.20 +
             pause_bonus * 0.15 +
             pause_score * 0.15),
            2
        )

    # -------------------------
    # TOP KEYWORDS
    # -------------------------
  
    def _top_keywords_keybert(self, words):

        if not words:
          return []

        text = " ".join(words)

        keywords = self.kw_model.extract_keywords(
        text,
        keyphrase_ngram_range=(1, 2),
        stop_words="english",
        top_n=10
    )

        return [kw[0] for kw in keywords]


# -------------------------
# RUNNER
# -------------------------
if __name__ == "__main__":

    with open("pipeline/uploads/video_transcript.json", "r", encoding="utf-8") as f:
        transcript = json.load(f)

    scorer = TranscriptScorer()
    results = scorer.score(transcript)

    print("\n=== VIRAL SCORING RESULTS ===")
    for k, v in results.items():
        print(f"{k:25}: {v}")

    