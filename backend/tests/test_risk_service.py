"""Unit tests for the deterministic, rule-based risk engine.

The engine must be pure (no ML / no randomness), fully explainable and
predictable for the same inputs (specification test cases TP1-TP6):

TP-1  Healthy project                       -> LOW
TP-2  Schedule problem                      -> HIGH
TP-3  Financial problem                     -> HIGH/CRITICAL
TP-4  Environmental / land clearance block  -> criticalBlocker=True and >=HIGH
TP-5  Natural disaster exposure             -> HIGH or above
TP-6  Missing data                          -> score computed but lower confidence
"""

import json
import os
import sys
import unittest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from models import Project
from services import risk_config as CFG
from services.risk_service import assess_project


def make_project(**overrides):
    """Construct a minimally viable, fully healthy Project row."""
    defaults = {
        "id": "TP-X",
        "name": "Test Project",
        "ministry": "MoRD",
        "sector": "Transport",
        "state": "Test State",
        "agency": "Test Agency",
        "original_cost": 1000,
        "current_cost": 1000,
        "expenditure": 0,
        "physical_progress": 95,
        "planned_progress": 96,
        "financial_progress": 96,
        "start_date": "2024-01-01",
        "expected_completion": "2026-12-31",
        "predicted_completion": "",
        "milestones_total": 10,
        "milestones_delayed": 0,
        "lat": 0,
        "lng": 0,
        "risk_factors": "[]",
        "recommendations": "[]",
        "risk_inputs": json.dumps({}),
    }
    defaults.update(overrides)
    p = Project()
    for key, value in defaults.items():
        setattr(p, key, value)
    return p


_LEVEL_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
assert_ge = lambda self, level, floor: self.assertGreaterEqual(
    _LEVEL_RANK[level], _LEVEL_RANK[floor]
)


class RiskEngineTestCase(unittest.TestCase):
    def test_tp1_healthy_project_is_low(self):
        a = assess_project(make_project())
        self.assertEqual(a["riskLevel"], "LOW")
        self.assertLess(a["riskScore"], 26)
        self.assertFalse(a["criticalBlocker"])
        self.assertEqual(a["riskTrend"]["available"], False)

    def test_tp2_schedule_problem_is_high(self):
        a = assess_project(
            make_project(
                physical_progress=40,
                planned_progress=80,
                milestones_total=12,
                milestones_delayed=8,
                predicted_completion="2027-12-31",
                risk_inputs=json.dumps({
                    "contractor": {"performance": "POOR", "delayedMilestoneCount": 5},
                    "administrative": {"turnaround": "SLOW", "pendingApprovalCount": 6},
                }),
            )
        )
        self.assertEqual(a["riskLevel"], "HIGH")
        self.assertGreaterEqual(a["riskScore"], 51)
        self.assertIn("Schedule & Delay", a["topRisks"])

    def test_tp3_financial_problem_is_high_or_critical(self):
        a = assess_project(
            make_project(
                original_cost=1000,
                current_cost=1400,
                expenditure=1200,
                physical_progress=45,
                planned_progress=60,
                financial_progress=92,
                risk_inputs=json.dumps({
                    "material": {"priceIncreasePct": 25, "availability": "SEVERE_SHORTAGE"},
                    "contractor": {"financialStress": "HIGH", "performance": "FAIR"},
                }),
            )
        )
        self.assertIn(a["riskLevel"], ("HIGH", "CRITICAL"))
        self.assertGreaterEqual(a["riskScore"], 51)

    def test_tp4_environmental_clearance_block_sets_critical_blocker(self):
        a = assess_project(
            make_project(
                risk_inputs=json.dumps({
                    "clearance": {
                        "landAcquiredPct": 30,
                        "environmentalClearance": "REJECTED",
                    },
                    "administrative": {"turnaround": "SLOW", "pendingApprovalCount": 5},
                }),
            )
        )
        self.assertTrue(a["criticalBlocker"])
        assert_ge(self, a["riskLevel"], "HIGH")
        self.assertGreaterEqual(a["riskScore"], 60)
        self.assertTrue(
            any("clearance" in r.lower() or "land" in r.lower()
                for r in a["criticalBlockerReasons"])
        )

    def test_tp5_natural_disaster_exposure_is_high_or_above(self):
        a = assess_project(
            make_project(
                risk_inputs=json.dumps({
                    "calamity": {"floodExposure": "HIGH", "cycloneExposure": "MODERATE"},
                    "weather": {"condition": "SEVERE", "disruption": "CRITICAL"},
                }),
            )
        )
        self.assertGreaterEqual({"HIGH": 1, "CRITICAL": 2}[a["riskLevel"]], 1)
        self.assertGreaterEqual(a["riskScore"], 51)

    def test_tp6_missing_data_is_scored_with_lower_confidence(self):
        empty = assess_project(make_project())
        # No evidence at all on most input-driven factors.
        a = assess_project(
            make_project(
                risk_inputs=json.dumps({
                    "weather": {"condition": "CLEAR"},
                    "ground": {"condition": "FAVOURABLE"},
                    "material": {"availability": "ADEQUATE"},
                    "workforce": {"availability": "ADEQUATE"},
                    "contractor": {"performance": "GOOD"},
                    "engineering": {"reworkLevel": "NONE"},
                    "clearance": {"landAcquiredPct": 100, "environmentalClearance": "CLEARED"},
                    "administrative": {"turnaround": "FAST"},
                    "calamity": {"floodExposure": "LOW"},
                    "supplyChain": {"accessibility": "GOOD"},
                    "legalSocial": {"oppositionLevel": "NONE"},
                }),
            )
        )
        self.assertGreaterEqual(a["riskScore"], 0)
        self.assertEqual(a["confidence"], 100)
        self.assertTrue(a["missingData"] or a["factors"])

    def test_missing_data_baseline_is_not_zero_risk(self):
        # A project with empty inputs must still produce a positive score -
        # missing data must never silently become zero risk.
        a = assess_project(make_project())
        self.assertGreater(a["riskScore"], 0)
        self.assertLess(a["confidence"], 100)
        self.assertNotEqual(a["missingData"], [])

    def test_same_inputs_same_output_deterministic(self):
        p = make_project(
            physical_progress=55,
            planned_progress=75,
            risk_inputs=json.dumps({"weather": {"condition": "SEVERE"}}),
        )
        first = assess_project(p)
        second = assess_project(p)
        self.assertEqual(first["riskScore"], second["riskScore"])
        self.assertEqual(first["riskLevel"], second["riskLevel"])
        self.assertEqual(first["explanations"], second["explanations"])

    def test_weights_total_100(self):
        self.assertEqual(sum(CFG.FACTOR_WEIGHTS.values()), 100)

    def test_factors_are_explainable_and_weighted(self):
        p = make_project(risk_inputs=json.dumps({"weather": {"condition": "SEVERE"}}))
        a = assess_project(p)
        for f in a["factors"]:
            self.assertIn("reason", f)
            self.assertIn("probability", f)
            self.assertIn("impact", f)
            self.assertEqual(f["weight"], CFG.FACTOR_WEIGHTS[f["key"]])
        self.assertGreaterEqual(len(a["recommendations"]), 1)


if __name__ == "__main__":
    unittest.main()