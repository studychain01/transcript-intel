"""Normalize raw JSON into flat fields for the canonical meetings table."""

from __future__ import annotations

from typing import Any


def utterances_list(transcript_doc: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Return transcript.data utterances or []."""
    if not transcript_doc or "data" not in transcript_doc:
        return []
    data = transcript_doc["data"]
    return data if isinstance(data, list) else []


def build_transcript_text(
    transcript_doc: dict[str, Any] | None,
    *,
    max_chars: int | None = None,
) -> str:
    """
    Concatenate utterance sentences into one string.

    TODO (you): optional max_chars truncation for LLM prompts (add ellipsis if cut).
    """
    utt = utterances_list(transcript_doc)
    parts: list[str] = []
    for row in utt:
        s = row.get("sentence") or row.get("text") or ""
        if s:
            parts.append(str(s))
    text = "\n".join(parts)
    if max_chars is not None and len(text) > max_chars:
        return text[:max_chars]
    return text


def meeting_row_skeleton(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Map one load_meeting_folder() result to a flat row (fill logic in your pipeline).

    Extend this dict as you add Part 1–3 columns.
    """
    info = raw.get("meeting_info") or {}
    summary = raw.get("summary") or {}
    tr = raw.get("transcript")

    return {
        "meeting_id": raw.get("meeting_id"),
        "title": info.get("title"),
        "start_time": info.get("startTime"),
        "duration_min": info.get("duration"),
        "transcript_text": build_transcript_text(tr),
        "provided_summary": summary.get("summary"),
        "provided_topics": summary.get("topics"),
        "provided_overall_sentiment": summary.get("overallSentiment"),
        "provided_sentiment_score": summary.get("sentimentScore"),
    }
