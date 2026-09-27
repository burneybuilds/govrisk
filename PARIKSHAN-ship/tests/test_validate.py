"""Tests for the aggregate-fidelity validation gate (PRD §4.4)."""

from __future__ import annotations

from paimana import config
from paimana.data.generator import generate_synthetic_panel
from paimana.data.validate import assert_fidelity, compute_fidelity_report, format_report


def test_structural_anchors_always_pass_at_full_scale():
    generated = generate_synthetic_panel(n_projects=config.N_PROJECTS, seed=config.RANDOM_SEED)
    checks = compute_fidelity_report(generated.projects)
    structural = {c.name: c for c in checks if c.name in ("n_projects", "n_sectors")}
    assert structural["n_projects"].passed
    assert structural["n_sectors"].passed


def test_format_report_is_human_readable():
    generated = generate_synthetic_panel(n_projects=200, seed=config.RANDOM_SEED)
    checks = compute_fidelity_report(generated.projects)
    report = format_report(checks)
    assert "n_projects" in report
    assert "PASS" in report or "FAIL" in report


def test_full_scale_default_generation_passes_all_anchors():
    """The canonical Phase 1 deliverable: at the real portfolio scale with
    the production seed, every documented anchor must be within tolerance.
    This is the test the generator's tuning constants are calibrated against.
    """
    generated = generate_synthetic_panel(n_projects=config.N_PROJECTS, seed=config.RANDOM_SEED)
    assert_fidelity(generated.projects)  # raises with a full report on any failure
