"""Aggregate-fidelity validation against the calibration anchors — PRD §4.4.

This is the build gate that keeps the synthetic generator honest: if the
generated portfolio's headline statistics drift too far from the documented
(and labelled-as-assumption) anchors, the build fails rather than silently
shipping an uncalibrated dataset.

Overrun-share and magnitude anchors are checked on the COMPLETED subset only
(is_censored == False) — that mirrors how such published figures are
actually computed (a project reports a realised overrun once it has a final
cost/date; an ongoing project reports an anticipated figure, a different and
softer signal this generator does not attempt to reproduce). See
docs/DATA_METHODOLOGY.md for the full scoping rationale.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from paimana import config


@dataclass(frozen=True)
class AnchorCheck:
    name: str
    anchor: float
    observed: float
    lower: float
    upper: float

    @property
    def passed(self) -> bool:
        return self.lower <= self.observed <= self.upper


def _tolerance_band(anchor: float, tolerance: float = config.ANCHOR_TOLERANCE) -> tuple[float, float]:
    return anchor * (1 - tolerance), anchor * (1 + tolerance)


def compute_fidelity_report(projects: pd.DataFrame) -> list[AnchorCheck]:
    """Compute every anchor check defined in PRD §4.4 against `projects`."""
    n_total = len(projects)
    completed = projects[projects["is_censored"] == False]  # noqa: E712
    n_completed = len(completed)

    share_censored = float((projects["is_censored"] == True).mean())  # noqa: E712
    share_cost_overrun = float((completed["y_cost_overrun"] == True).mean()) if n_completed else float("nan")  # noqa: E712
    share_time_overrun = float((completed["y_time_overrun"] == True).mean()) if n_completed else float("nan")  # noqa: E712
    aggregate_cost_overrun_pct = float(completed["cost_overrun_pct"].mean()) if n_completed else float("nan")

    checks = [
        AnchorCheck(
            "n_projects",
            config.ANCHOR_N_PROJECTS,
            float(n_total),
            *_tolerance_band(config.ANCHOR_N_PROJECTS, tolerance=0.0),
        ),
        AnchorCheck(
            "n_sectors",
            config.ANCHOR_N_SECTORS,
            float(projects["sector"].nunique()),
            *_tolerance_band(config.ANCHOR_N_SECTORS, tolerance=0.0),
        ),
        AnchorCheck(
            "share_censored_ongoing",
            config.ANCHOR_SHARE_ONGOING_CENSORED,
            share_censored,
            *_tolerance_band(config.ANCHOR_SHARE_ONGOING_CENSORED),
        ),
        AnchorCheck(
            "share_cost_overrun (completed subset)",
            config.ANCHOR_SHARE_COST_OVERRUN,
            share_cost_overrun,
            *_tolerance_band(config.ANCHOR_SHARE_COST_OVERRUN),
        ),
        AnchorCheck(
            "share_time_overrun (completed subset)",
            config.ANCHOR_SHARE_TIME_OVERRUN,
            share_time_overrun,
            *_tolerance_band(config.ANCHOR_SHARE_TIME_OVERRUN),
        ),
        AnchorCheck(
            "aggregate_cost_overrun_pct (completed subset)",
            config.ANCHOR_AGGREGATE_COST_OVERRUN_PCT,
            aggregate_cost_overrun_pct,
            *_tolerance_band(config.ANCHOR_AGGREGATE_COST_OVERRUN_PCT),
        ),
    ]
    return checks


def format_report(checks: list[AnchorCheck]) -> str:
    lines = [
        f"{'Anchor':45s} {'Target':>10s} {'Observed':>10s} {'Band':>22s} {'Status':>8s}",
        "-" * 100,
    ]
    for c in checks:
        status = "PASS" if c.passed else "FAIL"
        band = f"[{c.lower:.3f}, {c.upper:.3f}]"
        lines.append(f"{c.name:45s} {c.anchor:>10.3f} {c.observed:>10.3f} {band:>22s} {status:>8s}")
    return "\n".join(lines)


def assert_fidelity(projects: pd.DataFrame) -> None:
    """Raise AssertionError listing every failing anchor, or pass silently."""
    checks = compute_fidelity_report(projects)
    failures = [c for c in checks if not c.passed]
    if failures:
        raise AssertionError(
            "Synthetic data failed aggregate-fidelity validation (PRD §4.4):\n"
            + format_report(checks)
        )
