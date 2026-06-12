"""
scorer.py — Clip Scoring Logic
"""

def score_segment(segment: dict) -> float:
    """
    Score a transcript segment based on multiple signals.
    """
    score = 0.0
    text = segment.get("text", "")
    words = segment.get("words", [])

    # 1. Hook keyword matching
    hook_keywords = [
        "secret", "truth", "mistake", "never", "always",
        "best", "worst", "amazing", "shocking", "why",
        "how", "what", "top", "free", "easy"
    ]
    for keyword in hook_keywords:
        if keyword.lower() in text.lower():
            score += 2.0

    # 2. Sentence length filter (8-30 words preferred)
    word_count = len(text.split())
    if 8 <= word_count <= 30:
        score += 3.0
    elif word_count < 8:
        score -= 1.0

    # 3. Sentence energy score
    score += text.count("!") * 1.5
    score += text.count("?") * 1.5
    capital_words = sum(1 for w in text.split() if w.isupper() and len(w) > 1)
    score += capital_words * 1.0

    # 4. Pause detection (pauses > 1.5s boost score)
    if len(words) >= 2:
        for i in range(1, len(words)):
            gap = words[i]["start"] - words[i - 1]["end"]
            if gap > 1.5:
                score += 2.0

    return round(score, 2)


def score_all_segments(segments: list) -> list:
    """Score all segments and return sorted by score."""
    scored = []
    for seg in segments:
        seg["score"] = score_segment(seg)
        scored.append(seg)
    return sorted(scored, key=lambda x: x["score"], reverse=True)