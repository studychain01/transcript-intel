"""Deterministic meeting classification (no LLM dependency)."""

from __future__ import annotations

import re
from typing import Any

from transcript_intel.taxonomy import OTHERS_LABEL, normalize_category_label

# Primary routing from high-frequency title shapes (~100 calls):
# Support Case, Detect/incident, Comply (before Aegis), Aegis / …, else Others.

_RE_SUPPORT = re.compile(r"^support\s+case\s*#", re.I)
_RE_INCIDENT = re.compile(
    r"(incident:|urgent:|escalation:|detect\s+outage|war\s+room|post-incident|root\s+cause|remediation|outage)",
    re.I,
)
_RE_AEGIS_ACCOUNT = re.compile(r"^aegis\s*/\s*", re.I)
_RE_COMPLY = re.compile(r"\bcomply\b", re.I)


def _clean_topics(topics: Any) -> list[str]:
    if not isinstance(topics, list):
        return []
    out: list[str] = []
    for t in topics:
        s = str(t).strip()
        if s and s not in out:
            out.append(s)
    return out


def _primary_from_title(title: str) -> tuple[str, str]:
    """Return (primary_category, reason)."""
    if _RE_SUPPORT.search(title):
        return ("Support case", "title matched support-case pattern")
    if _RE_INCIDENT.search(title):
        return ("Detect outage", "title matched incident/outage pattern")
    if _RE_COMPLY.search(title):
        return ("Comply", "title matched Comply product / program pattern")
    if _RE_AEGIS_ACCOUNT.search(title):
        return ("Aegis", "title matched account-call prefix (Aegis / ...)")
    return (
        OTHERS_LABEL,
        "title did not match high-volume title patterns (see summary topics for detail)",
    )


def classify_meeting_rules(row: dict[str, Any]) -> dict[str, Any]:
    """
    Rule-first meeting classification:
    - primary category from title patterns
    - secondary categories from provided summary topics (free-form)
    """
    title = str(row.get("title") or "").strip()
    primary_raw, _ = _primary_from_title(title)
    primary = normalize_category_label(primary_raw)
    topics = _clean_topics(row.get("provided_topics"))

    return {
        "primary_category": primary,
        "secondary_categories": topics,
        "subthemes": topics[:5],
        "evidence_quotes": [],
        "llm_skipped": False,
    }
