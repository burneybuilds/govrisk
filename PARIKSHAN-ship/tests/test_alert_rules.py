"""Tests for the early-warning alert engine (PRD §6.8) — hand-built
fixtures proving each rule fires exactly when it should, edge-triggering
suppresses repeat alerts, severity ranking picks the worst trigger, and
SHAP reason codes only ever attach to a project's true latest snapshot.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from paimana import config
from paimana.risk.alerts import RULE_IDS, build_alerts, compute_rule_triggers

# Neutral defaults: none of these values trigger any rule on their own.
_NEUTRAL_ROW: dict = {
    "velocity_ratio": 1.0,
    "progress_gap_pp": 0.0,
    "stalled_quarters": 0,
    "risk_score": 10.0,
    "elapsed_frac": 0.3,
    "physical_progress_pct": 40.0,
    "n_reasons_active": 0,
    "revisions_to_date": 0,
    "pred_cost_overrun_pct": 5.0,
}


def _make_panel(project_id: str, overrides: list[dict]) -> pd.DataFrame:
    """One row per quarter for `project_id`, each starting from
    `_NEUTRAL_ROW` and overridden by the corresponding dict in `overrides`
    (quarter 0, 1, 2, ... in order)."""
    base_date = date(2020, 1, 1)
    rows = []
    for i, override in enumerate(overrides):
        row = {**_NEUTRAL_ROW, **override}
        row["project_id"] = project_id
        row["as_of_date"] = pd.Timestamp(base_date + timedelta(days=91 * i))
        for reason in config.DELAY_REASONS:
            row.setdefault(f"reason_{reason}", False)
        rows.append(row)
    return pd.DataFrame(rows)


def _fired_rules_by_quarter(df: pd.DataFrame, project_id: str) -> list[list[str]]:
    triggers = compute_rule_triggers(df)
    triggers = triggers[triggers["project_id"] == project_id].sort_values("as_of_date")
    return [[r for r in RULE_IDS if row[r]] for _, row in triggers.iterrows()]


# --------------------------------------------------------------------------
# EW-01: velocity_ratio < 0.5 for 2 CONSECUTIVE quarters
# --------------------------------------------------------------------------
def test_ew01_requires_two_consecutive_low_velocity_quarters():
    df = _make_panel(
        "P1",
        [
            {"velocity_ratio": 0.6},  # not low
            {"velocity_ratio": 0.4},  # low, but only 1st low quarter
            {"velocity_ratio": 0.3},  # low, and prev was also low -> fires
            {"velocity_ratio": 0.6},  # recovered
        ],
    )
    fired = _fired_rules_by_quarter(df, "P1")
    assert "EW-01" not in fired[0]
    assert "EW-01" not in fired[1]
    assert "EW-01" in fired[2]
    assert "EW-01" not in fired[3]


# --------------------------------------------------------------------------
# EW-02: progress_gap_pp > 20
# --------------------------------------------------------------------------
def test_ew02_fires_exactly_above_threshold():
    df = _make_panel(
        "P1",
        [
            {"progress_gap_pp": config.EW_PROGRESS_GAP_THRESHOLD_PP},  # boundary: not > threshold
            {"progress_gap_pp": config.EW_PROGRESS_GAP_THRESHOLD_PP + 0.1},  # just above
        ],
    )
    fired = _fired_rules_by_quarter(df, "P1")
    assert "EW-02" not in fired[0]
    assert "EW-02" in fired[1]


# --------------------------------------------------------------------------
# EW-03: stalled_quarters >= 3
# --------------------------------------------------------------------------
def test_ew03_fires_at_threshold():
    df = _make_panel(
        "P1",
        [
            {"stalled_quarters": config.EW_STALLED_QUARTERS_THRESHOLD - 1},
            {"stalled_quarters": config.EW_STALLED_QUARTERS_THRESHOLD},
        ],
    )
    fired = _fired_rules_by_quarter(df, "P1")
    assert "EW-03" not in fired[0]
    assert "EW-03" in fired[1]


# --------------------------------------------------------------------------
# EW-04: risk_score >= 70 AND risen >= 15 points in 2 quarters
# --------------------------------------------------------------------------
def test_ew04_requires_both_high_score_and_a_rise():
    df = _make_panel(
        "P1",
        [
            {"risk_score": 50.0},
            {"risk_score": 72.0},  # high, but 2q-ago is missing (NaN) -> no rise computed, must not fire
            {"risk_score": 90.0},  # high AND risen 90-50=40 >= 15 over 2 quarters -> fires
            {"risk_score": 92.0},  # still high, but rise 92-72=20... check exact semantics below
        ],
    )
    fired = _fired_rules_by_quarter(df, "P1")
    assert "EW-04" not in fired[0]
    assert "EW-04" not in fired[1]  # no valid 2-quarters-ago comparison yet
    assert "EW-04" in fired[2]


def test_ew04_does_not_fire_when_high_but_flat():
    df = _make_panel(
        "P1",
        [
            {"risk_score": 80.0},
            {"risk_score": 80.0},
            {"risk_score": 80.0},  # high but flat -> no rise -> must not fire
        ],
    )
    fired = _fired_rules_by_quarter(df, "P1")
    assert "EW-04" not in fired[2]


# --------------------------------------------------------------------------
# EW-05: elapsed_frac > 0.8 AND physical_progress_pct < 60
# --------------------------------------------------------------------------
def test_ew05_requires_both_conditions():
    df = _make_panel(
        "P1",
        [
            {"elapsed_frac": 0.9, "physical_progress_pct": 70.0},  # late but progressed enough
            {"elapsed_frac": 0.5, "physical_progress_pct": 30.0},  # behind but not late yet
            {"elapsed_frac": 0.9, "physical_progress_pct": 30.0},  # both -> fires
        ],
    )
    fired = _fired_rules_by_quarter(df, "P1")
    assert "EW-05" not in fired[0]
    assert "EW-05" not in fired[1]
    assert "EW-05" in fired[2]


# --------------------------------------------------------------------------
# EW-06: 3+ delay reasons active simultaneously
# --------------------------------------------------------------------------
def test_ew06_fires_at_threshold():
    df = _make_panel(
        "P1",
        [
            {"n_reasons_active": config.EW_MANY_REASONS_THRESHOLD - 1},
            {"n_reasons_active": config.EW_MANY_REASONS_THRESHOLD},
        ],
    )
    fired = _fired_rules_by_quarter(df, "P1")
    assert "EW-06" not in fired[0]
    assert "EW-06" in fired[1]


# --------------------------------------------------------------------------
# EW-07: 2+ prior revisions AND rising predicted overrun
# --------------------------------------------------------------------------
def test_ew07_requires_revisions_and_rising_prediction():
    df = _make_panel(
        "P1",
        [
            {"revisions_to_date": 1, "pred_cost_overrun_pct": 10.0},  # not enough revisions
            {"revisions_to_date": 2, "pred_cost_overrun_pct": 8.0},  # enough revisions, but falling
            {"revisions_to_date": 2, "pred_cost_overrun_pct": 15.0},  # enough AND rising -> fires
        ],
    )
    fired = _fired_rules_by_quarter(df, "P1")
    assert "EW-07" not in fired[0]
    assert "EW-07" not in fired[1]
    assert "EW-07" in fired[2]


# --------------------------------------------------------------------------
# MODEL-01: risk_score >= 70 (Red band)
# --------------------------------------------------------------------------
def test_model01_fires_at_red_band_threshold():
    df = _make_panel(
        "P1",
        [
            {"risk_score": config.EW_RISK_SCORE_RED_THRESHOLD - 1},
            {"risk_score": config.EW_RISK_SCORE_RED_THRESHOLD},
        ],
    )
    fired = _fired_rules_by_quarter(df, "P1")
    assert "MODEL-01" not in fired[0]
    assert "MODEL-01" in fired[1]


# --------------------------------------------------------------------------
# Edge-triggering: a persistent condition alerts ONCE, not every quarter
# --------------------------------------------------------------------------
def test_alert_fires_once_on_rising_edge_not_every_persisting_quarter():
    df = _make_panel(
        "P1",
        [
            {"progress_gap_pp": 25.0},  # onset -> alert
            {"progress_gap_pp": 25.0},  # still true -> NO new alert
            {"progress_gap_pp": 25.0},  # still true -> NO new alert
            {"progress_gap_pp": 5.0},  # resolved
            {"progress_gap_pp": 25.0},  # re-onset -> alert again
        ],
    )
    alerts = build_alerts(df)
    p1_alerts = alerts[alerts["project_id"] == "P1"].sort_values("as_of_date")
    assert len(p1_alerts) == 2  # onset and re-onset only, not the 2 persisting quarters


# --------------------------------------------------------------------------
# Severity ranking: multiple simultaneous triggers collapse to ONE alert
# at the highest severity, listing every triggered rule
# --------------------------------------------------------------------------
def test_multiple_simultaneous_triggers_collapse_to_highest_severity():
    df = _make_panel(
        "P1",
        [
            # EW-06 (Medium) and EW-03 (Critical) both fire this quarter.
            {"n_reasons_active": 3, "stalled_quarters": 3},
        ],
    )
    alerts = build_alerts(df)
    assert len(alerts) == 1
    row = alerts.iloc[0]
    assert row["severity"] == "Critical"
    assert set(row["triggered_rules"]) >= {"EW-03", "EW-06"}


# --------------------------------------------------------------------------
# SHAP reason codes: only the row that IS the project's true latest
# snapshot may carry them (PRD §7/Phase 5 — the temporal-correctness fix)
# --------------------------------------------------------------------------
def test_reason_codes_only_attach_to_the_true_latest_snapshot():
    df = _make_panel(
        "P1",
        [
            {"progress_gap_pp": 25.0},  # historical alert (not the latest quarter)
            {"progress_gap_pp": 5.0},
            {"progress_gap_pp": 25.0},  # this IS the latest quarter -> gets codes
        ],
    )
    shap_codes = {"P1": [{"feature": "num__progress_gap_pp", "shap_value": 0.4}]}
    alerts = build_alerts(df, shap_reason_codes=shap_codes).sort_values("as_of_date")

    assert alerts.iloc[0]["reason_codes"] is None  # historical alert: no codes
    assert alerts.iloc[-1]["reason_codes"] == shap_codes["P1"]  # latest snapshot: has codes


def test_recommended_action_falls_back_to_active_delay_reason_without_shap():
    from paimana.risk.alerts import REASON_ACTIONS

    df = _make_panel("P1", [{"n_reasons_active": 3, "reason_land_acquisition": True}])
    alerts = build_alerts(df)  # no SHAP codes supplied at all
    assert alerts.iloc[0]["recommended_action"] == REASON_ACTIONS["land_acquisition"]


def test_recommended_action_default_when_no_driver_identifiable():
    df = _make_panel("P1", [{"n_reasons_active": 3}])  # EW-06 fires, no active reason flags set
    alerts = build_alerts(df)
    assert alerts.iloc[0]["recommended_action"] != ""


# --------------------------------------------------------------------------
# No trigger anywhere -> empty, well-formed alerts table
# --------------------------------------------------------------------------
def test_build_alerts_returns_empty_dataframe_with_correct_columns_when_nothing_fires():
    df = _make_panel("P1", [{}, {}, {}])  # all neutral
    alerts = build_alerts(df)
    assert len(alerts) == 0
    assert "severity" in alerts.columns
    assert "recommended_action" in alerts.columns


@pytest.mark.parametrize("rule_id", RULE_IDS)
def test_every_rule_id_has_a_severity_and_description(rule_id):
    from paimana.risk.alerts import RULE_DESCRIPTIONS, RULE_SEVERITY

    assert rule_id in RULE_SEVERITY
    assert rule_id in RULE_DESCRIPTIONS
    assert RULE_SEVERITY[rule_id] in {"Medium", "High", "Critical"}
