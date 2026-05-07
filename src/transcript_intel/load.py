"""Load JSON artifacts from each meeting folder under the dataset root."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from transcript_intel import config

import json

def iter_meeting_dirs() -> list[Path]:
    """Return sorted directories under dataset/, each expected to contain meeting JSON files."""
    root = config.DATASET_DIR
    if not root.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {root}")

    #where iterdir gives children of root
    dirs = [p for p in sorted(root.iterdir()) if p.is_dir()]
    return dirs


def load_json(path: Path) -> Any:
    """Load a JSON file."""
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_meeting_folder(meeting_dir: Path) -> dict[str, Any]:
    """
    Load meeting-info, transcript, summary for one meeting_id folder.

    TODO (you): merge ancillary files (events, speakers) if needed.
    """
    mid = meeting_dir.name
    out: dict[str, Any] = {"meeting_id": mid, "folder": str(meeting_dir)}

    for name, key in (
        ("meeting-info.json", "meeting_info"),
        ("transcript.json", "transcript"),
        ("summary.json", "summary"),
    ):
        path = meeting_dir / name
        if path.is_file():
            out[key] = load_json(path)
        else:
            out[key] = None

    return out
