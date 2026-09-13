"""The LLM client and its deterministic fallback — PRD §6.9.

The anti-hallucination guarantee: the system prompt instructs the model to
narrate ONLY the verified JSON it is handed, never to compute, estimate, or
recall a number from its own training data. If Ollama is unreachable, slow,
or errors, a Jinja2 template renders the SAME underlying tool output
deterministically — the assistant screen can never hard-fail during a demo,
and the numbers a user sees are identical either way.

Model choice: Qwen2.5-7B-Instruct (Apache-2.0) — Llama models are rejected
project-wide as not OSI-approved (see LICENSES.md).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from jinja2 import Template

OLLAMA_MODEL = "qwen2.5:7b-instruct"
# Generous enough to absorb a cold model load (~45-80s measured directly
# during Phase 7 build — see HANDOFF.md), short enough that a genuinely
# unreachable Ollama fails fast into the fallback rather than hanging the UI.
OLLAMA_TIMEOUT_SECONDS = 90.0

SYSTEM_PROMPT = """You are the PARIKSHAN Project Intelligence Assistant for MoSPI's PAIMANA portal.

You will be given a JSON object of ALREADY-VERIFIED data computed by a trusted pandas
pipeline. Your ONLY job is to narrate these exact numbers in clear, concise prose for a
government official.

RULES (follow all of them):
1. NEVER invent, estimate, round differently, or compute a new number from the data —
   quote every figure exactly as given.
2. NEVER answer from your own general knowledge about India, infrastructure, or
   statistics — use ONLY the provided JSON.
3. If the JSON does not contain enough information to answer the question, say so
   plainly rather than guessing.
4. Keep your answer to 2-4 sentences unless the data is a list, in which case
   summarise briefly and mention there are more items if truncated.
5. This is SYNTHETIC data generated for methodology validation — do not claim it
   reflects real Indian infrastructure outcomes.
"""

_FALLBACK_TEMPLATE = Template(
    "Based on verified portfolio data for **{{ tool_name }}**:\n\n"
    "{% for key, value in result.items() %}"
    "- **{{ key }}**: {{ value }}\n"
    "{% endfor %}\n"
    "_(Rendered by the deterministic fallback template — the local LLM was unavailable. "
    "These numbers are identical to what the LLM would have narrated.)_"
)


@dataclass
class AssistantResponse:
    answer: str
    tool_used: str
    tool_result: dict
    source: str  # "ollama" or "fallback"
    routing_method: str  # "rule" or "embedding"
    # True when a live Ollama narration was generated but REJECTED for
    # containing an unverified number, and the deterministic template was
    # substituted instead — found to be a real, live occurrence (not a
    # hypothetical) during Phase 7's mandatory UI check: the model
    # misattributed a portfolio-wide total to a single sector's breakdown
    # and stated an aggregate figure that didn't trace to `tool_result` at
    # all. `source` is still "fallback" in this case (the numbers on screen
    # ARE the deterministic ones), but this flag lets the UI be transparent
    # about WHY, rather than looking identical to "Ollama was unreachable."
    ollama_answer_rejected: bool = False


_FALLBACK_MAX_LIST_ITEMS = 5


def _flatten_for_template(result: dict, max_list_items: int = _FALLBACK_MAX_LIST_ITEMS) -> dict:
    """Keep the fallback template readable: truncate long lists/dicts
    rather than dumping a huge nested structure into the chat bubble."""
    flat = {}
    for key, value in result.items():
        if isinstance(value, list):
            shown = value[:max_list_items]
            suffix = f" (+{len(value) - max_list_items} more)" if len(value) > max_list_items else ""
            flat[key] = f"{shown}{suffix}"
        else:
            flat[key] = value
    return flat


def render_fallback(tool_name: str, tool_result: dict) -> str:
    """Deterministic, LLM-free narration of `tool_result` — used whenever
    Ollama is unavailable, slow, or errors. Renders the SAME numbers an
    LLM-narrated answer would, just without the prose polish."""
    return _FALLBACK_TEMPLATE.render(tool_name=tool_name, result=_flatten_for_template(tool_result))


def _call_ollama(question: str, tool_result: dict) -> str | None:
    """Returns the model's narration, or None if Ollama is unavailable,
    times out, or errors for any reason — callers must treat None as
    "use the fallback," never as an error to surface to the user."""
    try:
        import ollama

        client = ollama.Client(timeout=OLLAMA_TIMEOUT_SECONDS)
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Question: {question}\n\n"
                        f"Verified data (JSON):\n{json.dumps(tool_result, indent=2, default=str)}"
                    ),
                },
            ],
            options={"temperature": 0.1},
        )
        content = response["message"]["content"].strip()
        return content if content else None
    except Exception:
        # Deliberately broad: network errors, timeouts, missing model,
        # Ollama not running, malformed response — ALL of these must fall
        # through to the deterministic template, not crash the UI.
        return None


def answer_question(
    question: str, tool_name: str, tool_result: dict, routing_method: str
) -> AssistantResponse:
    """Narrate `tool_result` via Ollama if possible, else the fallback
    template. This is the single entry point `pages/5_Assistant.py` calls.

    Every live Ollama narration is checked with `verify_numeric_fidelity`
    before it's trusted — found to be necessary, not theoretical, during
    Phase 7's mandatory live-UI check: a real live call to Qwen2.5-7B
    answered "What is the riskiest sector?" with a fabricated portfolio
    total ("1,426 projects... 299 at risk") that appeared nowhere in the
    verified `tool_result`, alongside real numbers quoted correctly
    elsewhere in the same answer. `scripts/run_assistant_eval.py` and
    `tests/test_golden_questions.py` only sample the model's output on the
    runs they happen to make — they don't guarantee every future live call
    stays faithful, so this check runs on every single answer served to a
    user, not just in tests.
    """
    narration = _call_ollama(question, tool_result)
    if narration is not None:
        verified, _unverified = verify_numeric_fidelity(narration, tool_result, question=question)
        if verified:
            return AssistantResponse(
                answer=narration,
                tool_used=tool_name,
                tool_result=tool_result,
                source="ollama",
                routing_method=routing_method,
            )
        return AssistantResponse(
            answer=render_fallback(tool_name, tool_result),
            tool_used=tool_name,
            tool_result=tool_result,
            source="fallback",
            routing_method=routing_method,
            ollama_answer_rejected=True,
        )
    return AssistantResponse(
        answer=render_fallback(tool_name, tool_result),
        tool_used=tool_name,
        tool_result=tool_result,
        source="fallback",
        routing_method=routing_method,
    )


# --------------------------------------------------------------------------
# Numeric fidelity — the automated check behind PRD §7/Phase 7 task 6's
# golden test set: "every quoted figure matches pandas ground truth."
# --------------------------------------------------------------------------
_NUMBER_PATTERN = re.compile(r"-?\d[\d,]*\.?\d*")


def _extract_numbers(text: str) -> list[float]:
    """Every numeric literal in free text, commas stripped (so "1,981"
    reads as 1981.0)."""
    numbers = []
    for match in _NUMBER_PATTERN.findall(text):
        cleaned = match.replace(",", "")
        if cleaned not in ("", "-", "."):
            try:
                numbers.append(float(cleaned))
            except ValueError:
                continue
    return numbers


def _flatten_numbers(obj) -> set[float]:
    """Every numeric value anywhere in a nested dict/list, rounded to 2dp
    so a model's own reasonable rounding doesn't register as a mismatch.
    Also pulls numbers embedded in STRING fields (e.g. "PRJ-00367" or
    "Project 00367") — a model repeating an identifier's digits is not
    inventing a number, and should not be flagged as one. Also pulls
    numbers embedded in dict KEY names (e.g. "top_10_states_by_at_risk_count",
    "bootstrap_95pct_ci_ml_minus_conventional") — the fallback template
    renders `{{ key }}: {{ value }}` for every field, so a key's own digits
    end up in the answer text too, and they're part of the tool's verified
    output structure, not an invented figure."""
    numbers: set[float] = set()
    if isinstance(obj, bool):
        return numbers
    if isinstance(obj, int | float):
        numbers.add(round(float(obj), 2))
    elif isinstance(obj, str):
        numbers.update(_extract_numbers(obj))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            numbers.update(_extract_numbers(str(k)))
            numbers |= _flatten_numbers(v)
    elif isinstance(obj, list | tuple):
        for v in obj:
            numbers |= _flatten_numbers(v)
    return numbers


def _truncation_counts(obj) -> set[float]:
    """The "(+N more)" figures `_flatten_for_template` computes for any
    list longer than its `max_list_items` default — a real, derived number
    (`len(list) - max_list_items`), not one present verbatim anywhere in
    `tool_result`, so `_flatten_numbers` alone can't see it. Recurses the
    same way `_flatten_numbers` does so a truncated list nested inside a
    dict (the common case) is still caught."""
    counts: set[float] = set()
    if isinstance(obj, dict):
        for v in obj.values():
            counts |= _truncation_counts(v)
    elif isinstance(obj, list | tuple):
        remainder = len(obj) - _FALLBACK_MAX_LIST_ITEMS
        if remainder > 0:
            counts.add(float(remainder))
        for v in obj:
            counts |= _truncation_counts(v)
    return counts


def _ordinal_markers(obj) -> set[float]:
    """The 1, 2, 3, ... markers a real LLM naturally prefixes onto each item
    when narrating a list as prose ("1. Project X ... 2. Project Y ..."),
    found empirically via `scripts/run_assistant_eval.py` against the live
    Ollama model (the deterministic fallback never does this — it renders a
    raw Python list repr, so this case doesn't show up against
    `render_fallback`). An ordinal marker up to a list's own length is a
    formatting choice, not an invented data value, so it's allowed for
    every list found in `tool_result` regardless of nesting depth."""
    markers: set[float] = set()
    if isinstance(obj, dict):
        for v in obj.values():
            markers |= _ordinal_markers(v)
    elif isinstance(obj, list | tuple):
        markers |= {float(i) for i in range(1, len(obj) + 1)}
        for v in obj:
            markers |= _ordinal_markers(v)
    return markers


def verify_numeric_fidelity(
    answer_text: str, tool_result: dict, question: str = "", tolerance: float = 0.5
) -> tuple[bool, list[float]]:
    """True if every number mentioned in `answer_text` is within
    `tolerance` of some number present in `tool_result` (the verified
    source data) OR in `question` itself (a model may reasonably echo back
    a number the user asked with, e.g. "top 5", without that being a
    hallucination). Returns (all_verified, the specific numbers that
    couldn't be matched to anything) — the second value is what a failing
    test should show, not just a bare assertion.
    """
    answer_numbers = _extract_numbers(answer_text)
    source_numbers = _flatten_numbers(tool_result)
    # A fraction in the source data (e.g. share_at_risk=0.2953) is often
    # faithfully narrated as a percentage (29.53%) — a correct unit
    # conversion, not a hallucination — so both forms count as verified.
    # Absolute values are allowed too: a negative "time overrun" of -2.0
    # months is faithfully described as "2 months ahead of schedule," and a
    # hyphen inside an identifier string (e.g. "PRJ-00367") gets parsed by
    # `_extract_numbers` as a false minus sign — both are sign artifacts,
    # not hallucinated magnitudes.
    source_numbers = source_numbers | {abs(n) for n in source_numbers}
    allowed = (
        source_numbers
        | {round(n * 100, 2) for n in source_numbers}
        | {round(n / 100, 4) for n in source_numbers}
        | set(_extract_numbers(question))
        | _truncation_counts(tool_result)
        | _ordinal_markers(tool_result)
    )
    unverified = [n for n in answer_numbers if not any(abs(n - a) <= tolerance for a in allowed)]
    return len(unverified) == 0, unverified
