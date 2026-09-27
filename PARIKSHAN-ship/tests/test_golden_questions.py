"""The golden question set — PRD §7/Phase 7 task 6.

8 canonical questions, each asserting the routed tool is correct AND that
every number in the rendered answer traces back to the verified tool
output (`verify_numeric_fidelity`). Tests exercise the DETERMINISTIC
fallback template specifically — not a live Ollama call — so this suite
is fast, has no external dependency, and is exactly as meaningful: the
fallback renders the identical numbers a real LLM narration would, and
PRD §7/Phase 7's explicit anti-hallucination requirement is about the
NUMBERS, not the prose style. `scripts/run_assistant_eval.py` separately
exercises the real Ollama path for the same 8 questions as a live check.
"""

from __future__ import annotations

import pytest

from paimana.assistant.llm import render_fallback, verify_numeric_fidelity
from paimana.assistant.retriever import route_question
from paimana.assistant.tools import TOOL_REGISTRY

GOLDEN_QUESTIONS: list[tuple[str, str]] = [
    ("How many projects are in the portfolio and how many are at risk?", "portfolio_summary"),
    ("What is the riskiest sector?", "sector_risk_summary"),
    ("Which state has the most at-risk projects?", "state_risk_summary"),
    ("Show me PRJ-00001", "project_detail"),
    ("What are the top 5 riskiest projects?", "top_risk_projects"),
    ("Show me the current critical alerts", "alert_digest"),
    ("Did ML significantly beat conventional statistics for severe overruns?", "model_bakeoff_summary"),
    ("How early would we have caught eventual severe overruns?", "backtest_summary"),
]


def _run_golden_question(question: str) -> tuple[str, dict, bool, list[float]]:
    """Route, call the tool, render via the fallback, and check fidelity.
    Returns (tool_name, tool_result, verified, unverified_numbers)."""
    tool_name, kwargs, _method = route_question(question)
    kwargs_clean = {k: v for k, v in kwargs.items() if v is not None}
    tool_result = TOOL_REGISTRY[tool_name]["fn"](**kwargs_clean)
    answer = render_fallback(tool_name, tool_result)
    verified, unverified = verify_numeric_fidelity(answer, tool_result, question=question)
    return tool_name, tool_result, verified, unverified


@pytest.mark.parametrize(("question", "expected_tool"), GOLDEN_QUESTIONS)
def test_golden_question_routes_correctly(question, expected_tool):
    tool_name, _kwargs, _method = route_question(question)
    assert tool_name == expected_tool, f"{question!r} routed to {tool_name!r}, expected {expected_tool!r}"


@pytest.mark.parametrize(("question", "expected_tool"), GOLDEN_QUESTIONS)
def test_golden_question_answer_is_numerically_faithful(question, expected_tool):
    tool_name, tool_result, verified, unverified = _run_golden_question(question)
    assert tool_name == expected_tool
    assert verified, (
        f"{question!r}: unverified numbers in fallback answer: {unverified} (source: {tool_result})"
    )


def test_all_eight_golden_questions_pass_together():
    """A single aggregate check matching the PRD's literal framing: "8
    canonical questions ... automated assertion that every quoted figure
    matches pandas ground truth." Prints a summary so a failure is
    immediately legible without re-running with -v.
    """
    assert len(GOLDEN_QUESTIONS) == 8
    results = []
    for question, expected_tool in GOLDEN_QUESTIONS:
        tool_name, _tool_result, verified, unverified = _run_golden_question(question)
        results.append((question, tool_name == expected_tool, verified, unverified))

    for question, routed_ok, verified, unverified in results:
        status = "PASS" if (routed_ok and verified) else "FAIL"
        print(f"[{status}] {question!r}")
        print(f"    routed_ok={routed_ok}, verified={verified}, unverified={unverified}")

    assert all(routed_ok and verified for _, routed_ok, verified, _ in results)


# --------------------------------------------------------------------------
# verify_numeric_fidelity itself — the mechanism the golden set depends on
# --------------------------------------------------------------------------
def test_verify_numeric_fidelity_catches_a_real_hallucination():
    tool_result = {"n_projects": 1981, "n_at_risk": 585}
    hallucinated_answer = "There are 1981 projects, with 2500 of them at serious risk."
    verified, unverified = verify_numeric_fidelity(hallucinated_answer, tool_result)
    assert not verified
    assert 2500.0 in unverified


def test_verify_numeric_fidelity_allows_percentage_conversion():
    tool_result = {"share_at_risk": 0.2953}
    answer = "About 29.53% of projects are at risk."
    verified, _unverified = verify_numeric_fidelity(answer, tool_result)
    assert verified


def test_verify_numeric_fidelity_allows_absolute_value_of_negative_source():
    tool_result = {"actual_time_overrun_months": -2.0}
    answer = "The project finished 2 months ahead of schedule."
    verified, _unverified = verify_numeric_fidelity(answer, tool_result)
    assert verified


def test_verify_numeric_fidelity_allows_numbers_embedded_in_identifiers():
    tool_result = {"project_id": "PRJ-00367", "risk_score": 0.9}
    answer = "Project 00367 has a risk score of 0.9."
    verified, _unverified = verify_numeric_fidelity(answer, tool_result)
    assert verified


def test_verify_numeric_fidelity_allows_numbers_echoed_from_the_question():
    tool_result = {"k": 5, "projects": []}
    answer = "Here are the top 5 projects you asked about."
    verified, _unverified = verify_numeric_fidelity(
        answer, tool_result, question="What are the top 5 riskiest projects?"
    )
    assert verified
