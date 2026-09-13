"""Tests for the whitelisted pandas tools and intent routing (PRD §6.9,
§7/Phase 7 tasks 2-3). Uses the real cached artifacts — these tools ARE the
anti-hallucination contract, so they must be tested against genuine data,
not a hand-built fixture that could hide a real schema mismatch.
"""

from __future__ import annotations

import pytest

from paimana import config
from paimana.assistant.retriever import route_by_rules, route_question
from paimana.assistant.tools import (
    TOOL_REGISTRY,
    alert_digest,
    backtest_summary,
    compare_sectors,
    delay_reason_breakdown,
    model_bakeoff_summary,
    portfolio_summary,
    project_detail,
    sector_risk_summary,
    state_risk_summary,
    top_risk_projects,
)


# --------------------------------------------------------------------------
# Tool registry structure
# --------------------------------------------------------------------------
def test_tool_registry_has_at_least_ten_tools():
    assert len(TOOL_REGISTRY) >= 10


def test_every_registered_tool_is_callable_and_has_a_description():
    for name, entry in TOOL_REGISTRY.items():
        assert callable(entry["fn"]), f"{name} is not callable"
        assert isinstance(entry["description"], str) and len(entry["description"]) > 10
        assert isinstance(entry["params"], list)


# --------------------------------------------------------------------------
# Individual tools — structural + plausibility checks against real data
# --------------------------------------------------------------------------
def test_portfolio_summary_matches_known_scale():
    result = portfolio_summary()
    assert result["n_projects"] == config.N_PROJECTS
    assert result["n_ongoing"] + result["n_completed"] == config.N_PROJECTS
    assert 0.0 <= result["share_at_risk"] <= 1.0
    assert set(result["risk_band_counts"]) <= {"Green", "Amber", "Red"}


def test_sector_risk_summary_single_sector():
    result = sector_risk_summary("Railways")
    assert result["sector"] == "Railways"
    assert result["n_projects"] > 0
    assert 0.0 <= result["mean_risk_score"] <= 100.0


def test_sector_risk_summary_all_sectors_ranked():
    result = sector_risk_summary(None)
    ranked = result["all_sectors_ranked_by_risk"]
    assert len(ranked) == config.N_SECTORS
    scores = [row["mean_risk_score"] for row in ranked]
    assert scores == sorted(scores, reverse=True)  # worst first


def test_sector_risk_summary_unknown_sector_raises():
    with pytest.raises(ValueError, match="Unknown sector"):
        sector_risk_summary("Not A Real Sector")


def test_state_risk_summary_single_state():
    result = state_risk_summary("Kerala")
    assert result["state"] == "Kerala"
    assert result["n_projects"] >= 0


def test_state_risk_summary_top_10_ranking():
    result = state_risk_summary(None)
    assert len(result["top_10_states_by_at_risk_count"]) <= 10


def test_state_risk_summary_unknown_state_raises():
    with pytest.raises(ValueError, match="Unknown state"):
        state_risk_summary("Atlantis")


def test_top_risk_projects_returns_requested_count_and_is_sorted():
    result = top_risk_projects(k=5)
    assert result["k"] == 5
    assert len(result["projects"]) == 5
    scores = [p["risk_score"] for p in result["projects"]]
    assert scores == sorted(scores, reverse=True)


def test_top_risk_projects_clips_k_to_sane_bounds():
    result = top_risk_projects(k=10000)
    assert result["k"] <= 100
    result_zero = top_risk_projects(k=0)
    assert result_zero["k"] >= 1


def test_project_detail_known_project():
    result = project_detail("PRJ-00001")
    assert result["project_id"] == "PRJ-00001"
    assert result["status"] in ("Ongoing", "Completed")
    assert "current_risk_score" in result or result["status"] == "Ongoing"


def test_project_detail_completed_project_has_actuals():
    completed = top_risk_projects(k=1)  # any project; check via portfolio scan instead
    from paimana.data.loader import load_processed_projects

    projects = load_processed_projects()
    a_completed_id = projects[projects["is_censored"] == False].iloc[0]["project_id"]  # noqa: E712
    result = project_detail(a_completed_id)
    assert result["status"] == "Completed"
    assert "actual_final_cost_cr" in result
    assert "actual_cost_overrun_pct" in result
    del completed


def test_project_detail_unknown_id_raises():
    with pytest.raises(ValueError, match="Unknown project_id"):
        project_detail("PRJ-99999")


def test_alert_digest_filters_by_severity():
    result = alert_digest(severity="Critical", limit=5)
    assert result["severity_filter"] == "Critical"
    for alert in result["alerts"]:
        assert alert["severity"] == "Critical"


def test_alert_digest_unknown_severity_raises():
    with pytest.raises(ValueError, match="Unknown severity"):
        alert_digest(severity="Apocalyptic")


def test_compare_sectors_returns_both():
    result = compare_sectors("Railways", "Textiles")
    assert result["sector_a"]["sector"] == "Railways"
    assert result["sector_b"]["sector"] == "Textiles"


def test_model_bakeoff_summary_overall():
    result = model_bakeoff_summary(None)
    assert "headline" in result
    assert "best_ml" in result
    assert len(result["targets"]) == 5


def test_model_bakeoff_summary_one_target():
    result = model_bakeoff_summary("y_severe")
    assert result["target"] == "y_severe"
    assert isinstance(result["significant"], bool)
    assert len(result["bootstrap_95pct_ci_ml_minus_conventional"]) == 2


def test_model_bakeoff_summary_unknown_target_raises():
    with pytest.raises(ValueError, match="Unknown target"):
        model_bakeoff_summary("not_a_real_target")


def test_backtest_summary_recall_is_a_fraction():
    result = backtest_summary()
    assert 0.0 <= result["recall_at_min_lead_quarters"] <= 1.0
    assert result["n_flagged_by_any_signal"] <= result["n_eventually_severe_projects"]


def test_delay_reason_breakdown_covers_all_reasons():
    result = delay_reason_breakdown()
    assert len(result["active_reason_counts"]) == len(config.DELAY_REASONS)
    counts = list(result["active_reason_counts"].values())
    assert counts == sorted(counts, reverse=True)


# --------------------------------------------------------------------------
# Rule-based routing (deterministic — no ML dependency)
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("question", "expected_tool"),
    [
        ("How many projects are at risk?", "portfolio_summary"),
        ("What is the riskiest sector?", "sector_risk_summary"),
        ("Which state has the most at-risk projects?", "state_risk_summary"),
        ("Show me PRJ-00123", "project_detail"),
        ("What are the top 10 riskiest projects?", "top_risk_projects"),
        ("Show me critical alerts", "alert_digest"),
        ("Compare Railways and Power sectors", "compare_sectors"),
        ("Did ML beat conventional statistics?", "model_bakeoff_summary"),
        ("How early would we catch severe overruns?", "backtest_summary"),
        ("What are the most common delay reasons?", "delay_reason_breakdown"),
    ],
)
def test_rule_routing_matches_expected_tool(question, expected_tool):
    result = route_by_rules(question)
    assert result is not None, f"no rule matched: {question!r}"
    assert result[0] == expected_tool


def test_rule_routing_extracts_project_id_correctly():
    result = route_by_rules("Tell me about prj-00456 please")
    assert result == ("project_detail", {"project_id": "PRJ-00456"})


def test_rule_routing_extracts_k_for_top_projects():
    result = route_by_rules("Show me the top 25 riskiest projects")
    assert result[0] == "top_risk_projects"
    assert result[1]["k"] == 25


def test_route_question_always_returns_a_valid_tool_name():
    for question in [
        "How many projects are at risk?",
        "asdkjflkasjdf random nonsense text",
        "",
    ]:
        tool_name, kwargs, method = route_question(question)
        assert tool_name in TOOL_REGISTRY
        assert method in ("rule", "narrative_search", "embedding", "default_fallback")
        assert isinstance(kwargs, dict)
