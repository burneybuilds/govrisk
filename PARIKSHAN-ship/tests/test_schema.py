"""Structural tests for the CUF data contract (PRD §5)."""

from __future__ import annotations

from paimana import config
from paimana.data import schema


def test_column_lists_have_no_duplicates_within_themselves():
    assert len(schema.STATIC_COLUMNS) == len(set(schema.STATIC_COLUMNS))
    assert len(schema.SNAPSHOT_COLUMNS) == len(set(schema.SNAPSHOT_COLUMNS))
    assert len(schema.TARGET_COLUMNS) == len(set(schema.TARGET_COLUMNS))


def test_static_and_snapshot_columns_are_disjoint():
    assert set(schema.STATIC_COLUMNS).isdisjoint(schema.SNAPSHOT_COLUMNS)


def test_static_and_target_columns_are_disjoint():
    assert set(schema.STATIC_COLUMNS).isdisjoint(schema.TARGET_COLUMNS)


def test_all_panel_columns_is_the_union():
    expected = set(schema.STATIC_COLUMNS) | set(schema.SNAPSHOT_COLUMNS) | set(schema.TARGET_COLUMNS)
    assert set(schema.ALL_PANEL_COLUMNS) == expected


def test_reason_columns_match_config_delay_reasons():
    reason_cols = [c for c in schema.SNAPSHOT_COLUMNS if c.startswith("reason_")]
    assert len(reason_cols) == len(config.DELAY_REASONS)
    for reason in config.DELAY_REASONS:
        assert f"reason_{reason}" in reason_cols


def test_enums_match_config_lists():
    assert len(schema.Sector) == len(config.SECTORS)
    assert len(schema.FundingMode) == len(config.FUNDING_MODES)
    assert len(schema.AgencyType) == len(config.AGENCY_TYPES)
    assert len(schema.CostBand) == len(config.COST_BANDS)
    assert len(schema.DelayReason) == len(config.DELAY_REASONS)


def test_snapshot_key_columns_are_subset_of_snapshot_or_static():
    for key_col in schema.SNAPSHOT_KEY_COLUMNS:
        assert key_col in schema.STATIC_COLUMNS or key_col in schema.SNAPSHOT_COLUMNS
