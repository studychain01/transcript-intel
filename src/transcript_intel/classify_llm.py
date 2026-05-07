"""Constrained LLM classification via LangChain + OpenAI structured output (Pydantic)."""

from __future__ import annotations

import json
import os
import time
from typing import Any

from pydantic import BaseModel, Field

from transcript_intel import config
from transcript_intel.taxonomy import OTHERS_LABEL, TAXONOMY, normalize_category_label


class ClassificationLLMOutput(BaseModel):
    """Returned directly by the model when using structured output."""

    primary_category: str
    secondary_categories: list[str] = Field(default_factory=list)
    subthemes: list[str] = Field(default_factory=list)
    evidence_quotes: list[str] = Field(default_factory=list)


_SYSTEM_PROMPT = """You classify B2B call transcripts into a fixed list of business themes.
Rules:
- primary_category MUST be exactly one string from the allowed taxonomy list.
- secondary_categories: zero or more FREE-FORM labels (short phrases) for extra specificity.
- subthemes: 2-5 short phrases capturing specifics (e.g. "SSO failures", "renewal pricing").
- evidence_quotes: 1-3 short verbatim quotes from the transcript excerpt (not from the summary alone)."""


def _user_payload(
    *,
    title: str | None,
    transcript_excerpt: str,
    provided_summary: str | None,
    provided_topics: list[str] | None,
) -> str:
    topics = ", ".join(provided_topics or [])
    return (
        "Allowed taxonomy (primary must be one of these exact labels):\n"
        f"{json.dumps(list(TAXONOMY), ensure_ascii=False, indent=2)}\n\n"
        f"meeting_title: {title or ''}\n"
        f"provided_summary (hint only): {provided_summary or ''}\n"
        f"provided_topics (hint only): {topics}\n\n"
        f"transcript_excerpt:\n{transcript_excerpt}\n"
    )


def _validate_and_normalize(parsed: dict[str, Any]) -> dict[str, Any]:
    primary_raw = parsed.get("primary_category")
    prim = normalize_category_label(
        primary_raw if isinstance(primary_raw, str) else None
    )

    secondaries_raw = parsed.get("secondary_categories") or []
    if not isinstance(secondaries_raw, list):
        secondaries_raw = []
    secondaries: list[str] = []
    for item in secondaries_raw:
        if not isinstance(item, str):
            continue
        cleaned = item.strip()
        if cleaned and cleaned not in secondaries:
            secondaries.append(cleaned[:80])

    subthemes = parsed.get("subthemes") or []
    if isinstance(subthemes, list):
        subthemes = [str(s).strip() for s in subthemes if str(s).strip()][:8]
    else:
        subthemes = []

    quotes = parsed.get("evidence_quotes") or []
    if isinstance(quotes, list):
        quotes = [str(q).strip() for q in quotes if str(q).strip()][:5]
    else:
        quotes = []

    return {
        "primary_category": prim,
        "secondary_categories": secondaries,
        "subthemes": subthemes,
        "evidence_quotes": quotes,
        "llm_skipped": False,
    }


def _log_llm(meeting_id: str | None, payload: dict[str, Any]) -> None:
    try:
        config.LLM_LOGS_DIR.mkdir(parents=True, exist_ok=True)
        mid = meeting_id or "unknown"
        path = config.LLM_LOGS_DIR / f"{mid}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def _invoke_with_retries(chain: Any, user_text: str, row: dict[str, Any]) -> dict[str, Any]:
    last_err: str | None = None
    last_dump = ""
    model = config.OPENAI_MODEL

    for attempt in range(config.LLM_MAX_RETRIES):
        try:
            raw_out = chain.invoke({"user_text": user_text})
            if isinstance(raw_out, dict):
                parsed = raw_out
                last_dump = json.dumps(parsed, ensure_ascii=False)
            else:
                parsed_obj: ClassificationLLMOutput = raw_out  # type: ignore[assignment]
                parsed = parsed_obj.model_dump()
                last_dump = parsed_obj.model_dump_json(ensure_ascii=False)
            out = _validate_and_normalize(parsed)
            _log_llm(
                row.get("meeting_id"),
                {
                    "provider": "openai",
                    "model": model,
                    "attempt": attempt + 1,
                    "response_parsed": json.loads(last_dump),
                    "normalized": {k: v for k, v in out.items() if k != "evidence_quotes"},
                },
            )
            time.sleep(config.LLM_SLEEP_SEC)
            return out
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
            time.sleep(config.LLM_SLEEP_SEC * (attempt + 1))

    fallback = {
        "primary_category": OTHERS_LABEL,
        "secondary_categories": [],
        "subthemes": [],
        "evidence_quotes": [],
        "llm_skipped": True,
    }
    _log_llm(
        row.get("meeting_id"),
        {"provider": "openai", "error": last_err, "last_response_json": last_dump},
    )
    return fallback


def _classify_openai(row: dict[str, Any]) -> dict[str, Any]:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    title = row.get("title")
    excerpt = (row.get("transcript_text") or "")[: config.MAX_TRANSCRIPT_CHARS]
    summary = row.get("provided_summary")
    topics = row.get("provided_topics")
    if topics is not None and not isinstance(topics, list):
        topics = None

    user_text = _user_payload(
        title=title,
        transcript_excerpt=excerpt,
        provided_summary=summary,
        provided_topics=topics,
    )

    llm = ChatOpenAI(model=config.OPENAI_MODEL, temperature=0.1)
    structured = llm.with_structured_output(ClassificationLLMOutput)
    prompt = ChatPromptTemplate.from_messages(
        [("system", _SYSTEM_PROMPT), ("human", "{user_text}")]
    )
    chain = prompt | structured

    return _invoke_with_retries(chain, user_text, row)


def build_classification_prompt(
    *,
    title: str | None,
    transcript_excerpt: str,
    provided_summary: str | None,
    provided_topics: list[str] | None,
) -> str:
    """Debug helper: user message body sent to the model."""
    return _user_payload(
        title=title,
        transcript_excerpt=transcript_excerpt[: config.MAX_TRANSCRIPT_CHARS],
        provided_summary=provided_summary,
        provided_topics=provided_topics,
    )


def classify_meeting_llm(row: dict[str, Any]) -> dict[str, Any]:
    """
    Return primary_category, secondary_categories, subthemes, evidence_quotes,
    llm_skipped. Requires OPENAI_API_KEY.
    """
    if not os.environ.get("OPENAI_API_KEY"):
        return {
            "primary_category": OTHERS_LABEL,
            "secondary_categories": [],
            "subthemes": [],
            "evidence_quotes": [],
            "llm_skipped": True,
        }

    try:
        return _classify_openai(row)
    except ImportError:
        return {
            "primary_category": OTHERS_LABEL,
            "secondary_categories": [],
            "subthemes": [],
            "evidence_quotes": [],
            "llm_skipped": True,
        }
