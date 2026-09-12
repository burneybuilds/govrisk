"""Provider-agnostic LLM client.

Reads AI_PROVIDER / AI_API_KEY / AI_MODEL / AI_API_BASE from environment
configuration. Supports OpenAI-compatible chat-completions endpoints
(OpenAI, OpenRouter, Azure OpenAI, any base URL) and Anthropic Messages.

Guarantees:
- never raises on provider failure (returns None instead)
- bounded timeout + bounded retries (never an infinite loop)
- structured JSON output parsed and validated by Pydantic
- API keys are never logged or exposed
"""

import json
import re
import urllib.request
import urllib.error

from config import (
    AI_API_BASE,
    AI_API_KEY,
    AI_MAX_RETRIES,
    AI_MODEL,
    AI_PROVIDER,
    AI_TIMEOUT_SECONDS,
    ai_logger,
    is_llm_available,
)
from ai.schemas import UpdateAnalysisResult


def _extract_json(text: str):
    """Parse a JSON object from a model reply, tolerating code fences."""
    if not text:
        return None
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    # Greedy match of the outermost {...}
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    blob = cleaned[start : end + 1]
    try:
        data = json.loads(blob)
        return data if isinstance(data, dict) else None
    except (ValueError, TypeError):
        return None


def _invoke_provider(messages: list) -> str:
    """Low-level HTTP call. Returns raw reply text or raises.

    Overridden in tests by monkeypatching this module attribute.
    """
    if not is_llm_available():
        raise RuntimeError("AI_PROVIDER or AI_API_KEY not configured")

    if AI_PROVIDER in ("anthropic", "claude"):
        return _call_anthropic(messages)
    return _call_openai_compatible(messages)


def _call_openai_compatible(messages: list) -> str:
    base = AI_API_BASE or "https://api.openai.com/v1"
    url = base.rstrip("/") + "/chat/completions"
    payload = json.dumps(
        {
            "model": AI_MODEL,
            "messages": messages,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AI_API_KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=AI_TIMEOUT_SECONDS) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["choices"][0]["message"]["content"]


def _call_anthropic(messages: list) -> str:
    base = AI_API_BASE or "https://api.anthropic.com"
    url = base.rstrip("/") + "/v1/messages"
    system = messages[0]["content"] if messages and messages[0]["role"] == "system" else ""
    rest = [m for m in messages if m["role"] != "system"]
    payload = json.dumps(
        {
            "model": AI_MODEL,
            "max_tokens": 1000,
            "temperature": 0.2,
            "system": system,
            "messages": [{"role": m["role"], "content": m["content"]} for m in rest],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": AI_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=AI_TIMEOUT_SECONDS) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return "".join(block.get("text", "") for block in body.get("content", []))


def _call_with_retry(messages: list, attempts_remaining=None) -> str:
    """Bounded retry that re-raises only when attempts are exhausted."""
    attempts_remaining = AI_MAX_RETRIES if attempts_remaining is None else attempts_remaining
    try:
        return _invoke_provider(messages)
    except urllib.error.HTTPError as exc:
        status = exc.code
        # Retry only transient failures (429 too many requests, 5xx), never 4xx.
        if status in (429, 500, 502, 503, 504) and attempts_remaining > 0:
            return _call_with_retry(messages, attempts_remaining - 1)
        raise
    except urllib.error.URLError:
        raise
    except (TimeoutError, OSError) as exc:
        if attempts_remaining > 0:
            return _call_with_retry(messages, attempts_remaining - 1)
        raise


def analyze_update(update_id, update_type, created_at, content) -> UpdateAnalysisResult:
    """Analyze one project update with the LLM.

    Returns a validated UpdateAnalysisResult, or a neutral
    `risk_detected=False` result if the provider is unavailable/fails.
    Never raises.
    """
    from ai.prompts import build_analyze_messages

    if not is_llm_available():
        ai_logger.info("llm unavailable - update analysis skipped (provider not set)")
        return UpdateAnalysisResult(risk_detected=False, risk_category="OTHER")

    try:
        raw = _call_with_retry(
            build_analyze_messages(update_id, update_type, created_at, content)
        )
        data = _extract_json(raw)
        result = UpdateAnalysisResult(**data)
        ai_logger.info("llm update analysis ok update=%s risk=%s", update_id, result.risk_category)
        return result
    except Exception as exc:  # noqa: BLE001 - must never surface
        ai_logger.warning("llm update analysis failed update=%s err=%s", update_id, type(exc).__name__)
        return UpdateAnalysisResult(risk_detected=False, risk_category="OTHER")


def explain_project(deterministic: str, history: str) -> dict:
    """Generate a grounded explanation. Returns {} on failure/unavailable."""
    from ai.prompts import build_explain_messages

    if not is_llm_available():
        return {}
    try:
        raw = _call_with_retry(build_explain_messages(deterministic, history))
        data = _extract_json(raw) or {}
        return {
            "summary": str(data.get("summary", "")).strip(),
            "predicted_events": _as_list(data.get("predicted_events")),
            "ai_evidence": _as_list(data.get("ai_evidence")),
        }
    except Exception as exc:  # noqa: BLE001
        ai_logger.warning("llm explanation failed err=%s", type(exc).__name__)
        return {}


def _as_list(value) -> list:
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def health() -> dict:
    return {
        "available": is_llm_available(),
        "provider": AI_PROVIDER if is_llm_available() else "",
        "model": AI_MODEL if is_llm_available() else "",
        "fallback_enabled": True,
    }