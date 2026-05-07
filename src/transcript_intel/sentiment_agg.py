"""Aggregate utterance-level sentiment from transcript.json into call-level metrics."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from transcript_intel.normalize import utterances_list


def sentiment_proportions(transcript_doc: dict[str, Any] | None) -> dict[str, float]:
    """
    Count sentimentType per sentence → fractions positive / neutral / negative.

    TODO (you): handle unexpected labels; very short calls.
    """
    utt = utterances_list(transcript_doc)
    if not utt:
        return {"pct_positive": 0.0, "pct_neutral": 0.0, "pct_negative": 0.0, "n": 0}

    counts = {"positive": 0, "neutral": 0, "negative": 0, "other": 0}
    for row in utt:
        st = (row.get("sentimentType") or "").lower()
        if st in counts:
            counts[st] += 1
        else:
            counts["other"] += 1

    n = len(utt)
    return {
        "pct_positive": counts["positive"] / n,
        "pct_neutral": counts["neutral"] / n,
        "pct_negative": counts["negative"] / n,
        "n": n,
    }


def label_from_proportions(p: dict[str, float]) -> str:
    """
    Map pct_* proportions to a compact sentiment label.

    Expected keys: pct_positive, pct_neutral, pct_negative, n (optional).
    """
    n = int(p.get("n", 0) or 0)
    if n == 0:
        return "no_signal"
    if n < 5:
        return "low_signal"

    pos = float(p.get("pct_positive", 0.0) or 0.0)
    neu = float(p.get("pct_neutral", 0.0) or 0.0)
    neg = float(p.get("pct_negative", 0.0) or 0.0)

    # Dominant classes for strong signals.
    if neg >= 0.60:
        return "very_negative"
    if pos >= 0.60:
        return "very_positive"
    if neu >= 0.70:
        return "mostly_neutral"

    # Leaning classes for moderate dominance.
    if neg >= 0.45 and neg > pos:
        return "negative_leaning"
    if pos >= 0.45 and pos > neg:
        return "positive_leaning"

    # Close positive/negative with low neutrality indicates tension/polarization.
    if abs(pos - neg) <= 0.10 and neu <= 0.40:
        return "polarized"

    return "mixed"


def speaker_sentiment_breakdown(
    transcript_doc: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """
    Build sentiment stats for every speaker in a call.

    Notes:
    - Adds `n_utterances` and `turn_share` so low-volume speakers can be
      interpreted with proper confidence.
    """
    utt = utterances_list(transcript_doc)
    if not utt:
        return []

    by_speaker: dict[str, dict[str, int]] = defaultdict(
        lambda: {"positive": 0, "neutral": 0, "negative": 0, "other": 0, "n": 0}
    )

    for row in utt:
        raw_name = row.get("speaker_name")
        speaker = str(raw_name).strip() if raw_name is not None else ""
        if not speaker:
            sid = row.get("speaker_id")
            speaker = f"speaker_{sid}" if sid is not None else "unknown"

        st = str(row.get("sentimentType") or "").lower().strip()
        if st not in {"positive", "neutral", "negative"}:
            st = "other"

        by_speaker[speaker][st] += 1
        by_speaker[speaker]["n"] += 1

    total_utterances = len(utt)
    out: list[dict[str, Any]] = []
    for speaker, c in by_speaker.items():
        n = c["n"]
        if n == 0:
            continue
        dominant = max(["positive", "neutral", "negative"], key=lambda k: c[k])
        out.append(
            {
                "speaker_name": speaker,
                "n_utterances": n,
                "turn_share": n / total_utterances,
                "pct_positive": c["positive"] / n,
                "pct_neutral": c["neutral"] / n,
                "pct_negative": c["negative"] / n,
                "dominant_sentiment": dominant,
                "is_sparse": n < 3,
            }
        )

    out.sort(key=lambda r: r["n_utterances"], reverse=True)
    return out
