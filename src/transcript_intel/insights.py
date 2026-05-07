"""Part 3: account timelines, feature-gap risk, action-item owners — implement here."""

from __future__ import annotations

from typing import Any


def parse_account_from_title(title: str | None) -> str | None:
    """
    Extract a coarse account name from titles like 'Aegis / Acme Corp - Renewal'.

    TODO (you): regex + manual exceptions for Support Case # lines.
    """
    return None


def account_timeline_rows(meetings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """TODO (you): group by account, sort by start_time, emit timeline events."""
    return []


def feature_gap_risk_scores(meetings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    TODO (you): combine keyMoments types, primary_category, sentiment aggregates.

    meetings rows should include summary_blob or pre-extracted key_moment flags.
    """
    return []


def parse_action_items(summary: dict[str, Any] | None) -> list[dict[str, str]]:
    """TODO (you): split actionItems strings into {owner, task}."""
    return []


def owner_load_histogram(meetings: list[dict[str, Any]]) -> dict[str, int]:
    """TODO (you): count tasks per owner across meetings."""
    return {}
