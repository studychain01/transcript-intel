"""Paths and defaults. Override with env vars in CI or local runs."""

from __future__ import annotations

import os
from pathlib import Path

# interview-assignment/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

DATASET_DIR = Path(
    os.environ.get("TRANSCRIPT_INTEL_DATASET", _PROJECT_ROOT / "dataset")
)
OUTPUT_DIR = Path(
    os.environ.get("TRANSCRIPT_INTEL_OUTPUT", _PROJECT_ROOT / "outputs")
)
FIGURES_DIR = OUTPUT_DIR / "figures"
LLM_LOGS_DIR = OUTPUT_DIR / "llm_logs"

# Optional: cap transcript text passed to the LLM (chars)
MAX_TRANSCRIPT_CHARS = int(os.environ.get("TRANSCRIPT_MAX_CHARS", "24000"))

# LLM classification (LangChain + structured output — see classify_llm.py)
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
LLM_MAX_RETRIES = int(os.environ.get("LLM_MAX_RETRIES", "3"))
LLM_SLEEP_SEC = float(os.environ.get("LLM_SLEEP_SEC", "0.15"))
