"""Rule-based call type from meeting title (separate from thematic categories)."""

from __future__ import annotations

import re

_RE_SUPPORT = re.compile(r"^Support\s+Case\s*#", re.I)
_RE_AEGIS_CUSTOMER = re.compile(r"^Aegis\s*/\s*", re.I)
_RE_INCIDENT = re.compile(
    r"(INCIDENT:|URGENT:|ESCALATION:|Detect\s+Outage|War\s+Room|Root\s+Cause|Remediation)",
    re.I,
)
_RE_INTERNAL = re.compile(
    r"(Weekly\s+Engineering|Team\s+-\s+Sprint|All\s+Hands|Comply\s+v2\s+-|"
    r"SOC\s+2|Product\s+Sync|Win/Loss|Competitive\s+Landscape)",
    re.I,
)


def infer_call_type(title: str | None) -> str:
    """
    Return one of: support | customer_external | internal_ops | incident_cross_function | unknown

    TODO (you): document edge cases; order of checks matters.
    """
    if not title:
        return "unknown"
    if _RE_SUPPORT.search(title):
        return "support"
    if _RE_INCIDENT.search(title):
        return "incident_cross_function"
    if _RE_INTERNAL.search(title):
        return "internal_ops"
    if _RE_AEGIS_CUSTOMER.search(title):
        return "customer_external"
    return "unknown"
