"""Primary taxonomy: short title-aligned labels from `classify_rules.py`."""

from __future__ import annotations

# Short primaries for charts (match recurring title shapes in the dataset).
OTHERS_LABEL = "Others"
TAXONOMY: tuple[str, ...] = (
    "Support case",
    "Detect outage",
    "Comply",
    "Aegis",
    OTHERS_LABEL,
)


def normalize_category_label(label: str | None) -> str:
    """
    Map a label onto the canonical spelling from TAXONOMY.

    Uses case-insensitive exact match, then substring match against non-Others buckets.
    """
    if not label or not str(label).strip():
        return OTHERS_LABEL
    s = str(label).strip()
    low = s.lower()
    if low in ("other", "others", "other / unclear (needs review)"):
        return OTHERS_LABEL
    for canon in TAXONOMY:
        if low == canon.lower():
            return canon
    for canon in sorted(TAXONOMY, key=len, reverse=True):
        if canon == OTHERS_LABEL:
            continue
        c = canon.lower()
        if c in low or low in c:
            return canon
    return OTHERS_LABEL
