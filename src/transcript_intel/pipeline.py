"""End-to-end run: ingest → enrich → write outputs/meetings.parquet."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

from transcript_intel import config
from transcript_intel.call_type import infer_call_type
from transcript_intel.classify_rules import classify_meeting_rules
from transcript_intel.load import iter_meeting_dirs, load_meeting_folder
from transcript_intel.normalize import build_transcript_text, meeting_row_skeleton
from transcript_intel.sentiment_agg import (
    label_from_proportions,
    sentiment_proportions,
    speaker_sentiment_breakdown,
)


# Columns you will extend as Parts 1–3 mature
_MEETINGS_COLUMNS = [
    "meeting_id",
    "title",
    "start_time",
    "duration_min",
    "call_type",
    "transcript_text",
    "provided_summary",
    "provided_topics",
    "provided_overall_sentiment",
    "provided_sentiment_score",
    "pct_positive",
    "pct_neutral",
    "pct_negative",
    "utterance_count",
    "speaker_count",
    "speaker_sentiment",
    "aggregated_label",
    "primary_category",
    "secondary_categories",
    "subthemes",
    "evidence_quotes",
]


def build_rows() -> list[dict]:
    meeting_dirs = iter_meeting_dirs()
    total = len(meeting_dirs)
    print(f"[pipeline] Processing {total} meeting folders...")
    rows: list[dict] = []
    started = time.perf_counter()
    for idx, d in enumerate(meeting_dirs, start=1):
        raw = load_meeting_folder(d)
        base = meeting_row_skeleton(raw)
        title = base.get("title")
        tr = raw.get("transcript")

        props = sentiment_proportions(tr)
        speaker_stats = speaker_sentiment_breakdown(tr)
        cls = classify_meeting_rules(base)
        if idx == 1 or idx % 5 == 0 or idx == total:
            print(
                f"[pipeline] [{idx}/{total}] {base.get('meeting_id')} "
                f"category={cls.get('primary_category')}"
            )

        row = {
            **base,
            "call_type": infer_call_type(title),
            "pct_positive": props["pct_positive"],
            "pct_neutral": props["pct_neutral"],
            "pct_negative": props["pct_negative"],
            "utterance_count": int(props["n"]),
            "speaker_count": len(speaker_stats),
            "speaker_sentiment": speaker_stats,
            "aggregated_label": label_from_proportions(props),
            "primary_category": cls.get("primary_category"),
            "secondary_categories": cls.get("secondary_categories") or [],
            "subthemes": cls.get("subthemes") or [],
            "evidence_quotes": cls.get("evidence_quotes") or [],
        }
        rows.append(row)
    elapsed = time.perf_counter() - started
    print(f"[pipeline] Built {len(rows)} rows in {elapsed:.1f}s")
    return rows


def run_pipeline(*, output_path: Path | None = None) -> Path:
    """Create output dirs, build meetings table, write Parquet (+ optional CSV)."""
    run_started = time.perf_counter()
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    config.LLM_LOGS_DIR.mkdir(parents=True, exist_ok=True)

    rows = build_rows()
    df = pd.DataFrame(rows)

    # Ensure column order (missing columns become NaN)
    for col in _MEETINGS_COLUMNS:
        if col not in df.columns:
            df[col] = None
    df = df[[c for c in _MEETINGS_COLUMNS if c in df.columns]]

    out = output_path or (config.OUTPUT_DIR / "meetings.parquet")
    df.to_parquet(out, index=False)
    # CSV: stringify list/dict cells for Excel-friendly review

    df_csv = df.copy()
    for col in df_csv.columns:
        sample = df_csv[col].dropna().head(1)
        if len(sample) and isinstance(sample.iloc[0], (list, dict)):
            df_csv[col] = df_csv[col].apply(
                lambda x: json.dumps(x, ensure_ascii=False)
                if isinstance(x, (list, dict))
                else x
            )
    df_csv.to_csv(config.OUTPUT_DIR / "meetings.csv", index=False)
    print(f"[pipeline] Wrote parquet: {out}")
    print(f"[pipeline] Wrote csv: {config.OUTPUT_DIR / 'meetings.csv'}")
    print(f"[pipeline] Total runtime: {time.perf_counter() - run_started:.1f}s")
    return out


def main() -> None:
    path = run_pipeline()
    print(f"Wrote {path} and {config.OUTPUT_DIR / 'meetings.csv'}")


if __name__ == "__main__":
    main()
