"""Tests for the Early Warning Center API (routers/alerts.py).

Two classes of regression are covered here:

1. Ordering. The list used to come back in SQLite insertion order, which put a
   stale MEDIUM warning above a newer CRITICAL one - the opposite of what an
   early-warning surface needs.
2. The resolve lifecycle. The "Resolved" tab was previously unreachable: nothing
   in the API could change an alert's status, so the tab only ever showed
   whatever the seed script happened to write.

Follows the same isolation approach as test_ai_analysis: throwaway SQLite files
so the developer's govrisk.db / auth.db are never touched.
"""

import os
import shutil
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROJECT_ID = "PRJ-TEST-EW"


def _patch_temp_dbs():
    """Point the module-level session factories at throwaway SQLite files."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import database
    import auth.database
    import models  # noqa: F401  (force model registration before create_all)
    import auth.models  # noqa: F401

    tmpdir = tempfile.mkdtemp(prefix="sankalp-alerts-test-")
    engine = create_engine(
        "sqlite:///" + os.path.join(tmpdir, "test.db"),
        connect_args={"check_same_thread": False},
    )
    auth_engine = create_engine(
        "sqlite:///" + os.path.join(tmpdir, "auth.db"),
        connect_args={"check_same_thread": False},
    )

    make = sessionmaker(autocommit=False, autoflush=False)
    make.configure(bind=engine)
    database.SessionLocal = make
    database.Base.metadata.create_all(bind=engine)

    make_auth = sessionmaker(autocommit=False, autoflush=False)
    make_auth.configure(bind=auth_engine)
    auth.database.AuthSessionLocal = make_auth
    auth.database.AuthBase.metadata.create_all(bind=auth_engine)

    return tmpdir


class AlertsApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from main import app

        cls._tmpdir = _patch_temp_dbs()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmpdir, ignore_errors=True)

    def setUp(self):
        from database import SessionLocal
        from models import Alert, Project

        # Per-test isolation: these tables are shared across the whole class.
        with SessionLocal() as db:
            db.query(Alert).filter(Alert.project_id == PROJECT_ID).delete()
            db.query(Project).filter(Project.id == PROJECT_ID).delete()
            db.commit()
            db.add(
                Project(
                    id=PROJECT_ID,
                    name="Early Warning Test Project",
                    ministry="MoRTH",
                    sector="Transport",
                    state="Odisha",
                    agency="NHAI",
                    original_cost=1000.0,
                    current_cost=1000.0,
                    expenditure=100.0,
                    physical_progress=0.0,
                    planned_progress=0.0,
                    start_date="2025-01-01",
                    expected_completion="2027-01-01",
                    predicted_completion="2027-01-01",
                    cost_overrun_probability=50.0,
                    delay_probability=50.0,
                    implementation_risk=50.0,
                    risk_score=50.0,
                    risk_level="MEDIUM",
                    milestones_total=10,
                    milestones_delayed=0,
                    lat=20.0,
                    lng=85.0,
                    risk_factors="[]",
                    recommendations="[]",
                )
            )
            db.commit()

    # ── helpers ──────────────────────────────────────────────────────────
    def _headers_for(self, role):
        """Register a throwaway user, promote it to `role`, return auth headers."""
        email = f"ew_{role}_{uuid.uuid4().hex[:8]}@sankalp.gov.in"
        r = self.client.post(
            "/api/auth/register",
            json={
                "fullName": "EW Test User",
                "email": email,
                "password": "testpass123",
                "department": "IT",
                "designation": "Testing",
            },
        )
        self.assertEqual(r.status_code, 201, r.text)

        from auth.database import AuthSessionLocal
        from auth.models import User

        with AuthSessionLocal() as db:
            user = db.query(User).filter(User.email == email).first()
            user.role = role
            # Registration now creates a pending-approval account; the
            # authorization dependency rejects unapproved users on every
            # request, so the test user must be approved explicitly.
            user.is_approved = True
            db.commit()

        return {"Authorization": f"Bearer {r.json()['accessToken']}"}

    def _add_alert(self, alert_id, severity, status="ACTIVE", detected="2025-01-01"):
        from database import SessionLocal
        from models import Alert

        with SessionLocal() as db:
            db.add(
                Alert(
                    id=alert_id,
                    project_id=PROJECT_ID,
                    type="Test Alert",
                    severity=severity,
                    description="desc",
                    detected_date=detected,
                    status=status,
                )
            )
            db.commit()

    # ── ordering ─────────────────────────────────────────────────────────
    def test_list_orders_unresolved_before_resolved(self):
        self._add_alert("A-RESOLVED-CRIT", "CRITICAL", status="RESOLVED")
        self._add_alert("A-ACTIVE-LOW", "LOW")

        r = self.client.get("/api/alerts", headers=self._headers_for("officer"))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual([a["id"] for a in r.json()], ["A-ACTIVE-LOW", "A-RESOLVED-CRIT"])

    def test_list_orders_by_severity_then_newest_first(self):
        self._add_alert("A-MED-OLD", "MEDIUM", detected="2025-01-01")
        self._add_alert("A-CRIT-OLD", "CRITICAL", detected="2025-01-01")
        self._add_alert("A-CRIT-NEW", "CRITICAL", detected="2025-09-01")
        self._add_alert("A-HIGH", "HIGH", detected="2025-05-01")

        r = self.client.get("/api/alerts", headers=self._headers_for("officer"))
        self.assertEqual(
            [a["id"] for a in r.json()],
            ["A-CRIT-NEW", "A-CRIT-OLD", "A-HIGH", "A-MED-OLD"],
        )

    def test_unrecognised_severity_sorts_last(self):
        self._add_alert("A-WEIRD", "catastrophic")
        self._add_alert("A-LOW", "LOW")

        r = self.client.get("/api/alerts", headers=self._headers_for("officer"))
        self.assertEqual([a["id"] for a in r.json()], ["A-LOW", "A-WEIRD"])

    def test_severity_comparison_is_case_insensitive(self):
        self._add_alert("A-lower", "critical")
        self._add_alert("A-upper", "MEDIUM")

        r = self.client.get("/api/alerts", headers=self._headers_for("officer"))
        self.assertEqual([a["id"] for a in r.json()], ["A-lower", "A-upper"])

    # ── resolve lifecycle ────────────────────────────────────────────────
    def test_officer_can_resolve_and_reopen(self):
        self._add_alert("A-1", "CRITICAL")
        headers = self._headers_for("officer")

        r = self.client.patch("/api/alerts/A-1", json={"status": "RESOLVED"}, headers=headers)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["status"], "RESOLVED")

        r = self.client.patch("/api/alerts/A-1", json={"status": "ACTIVE"}, headers=headers)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["status"], "ACTIVE")

    def test_resolving_keeps_severity(self):
        """Severity and status are independent: resolving must not rewrite how
        severe the warning was, otherwise the Resolved tab misfiles it."""
        self._add_alert("A-1", "CRITICAL")

        r = self.client.patch(
            "/api/alerts/A-1", json={"status": "RESOLVED"}, headers=self._headers_for("officer")
        )
        self.assertEqual(r.json()["severity"], "CRITICAL")
        self.assertEqual(r.json()["status"], "RESOLVED")

    def test_resolved_alert_sorts_below_active_ones(self):
        self._add_alert("A-CRIT", "CRITICAL")
        self._add_alert("A-MED", "MEDIUM")
        headers = self._headers_for("officer")

        self.client.patch("/api/alerts/A-CRIT", json={"status": "RESOLVED"}, headers=headers)

        r = self.client.get("/api/alerts", headers=headers)
        self.assertEqual([a["id"] for a in r.json()], ["A-MED", "A-CRIT"])

    def test_viewer_cannot_resolve(self):
        self._add_alert("A-1", "HIGH")

        r = self.client.patch(
            "/api/alerts/A-1", json={"status": "RESOLVED"}, headers=self._headers_for("viewer")
        )
        self.assertEqual(r.status_code, 403, r.text)

    def test_requires_authentication(self):
        self._add_alert("A-1", "HIGH")

        # The app's HTTPBearer dependency answers a missing Authorization
        # header with 403 "Not authenticated" on every protected route, so
        # that is the contract asserted here rather than 401.
        self.assertEqual(self.client.get("/api/alerts").status_code, 403)
        self.assertEqual(
            self.client.patch("/api/alerts/A-1", json={"status": "RESOLVED"}).status_code, 403
        )

    def test_unknown_status_is_rejected(self):
        """An unknown status would drop the alert out of every severity tab and
        make it unreachable, so it must be a 422 rather than a silent write."""
        self._add_alert("A-1", "HIGH")

        r = self.client.patch(
            "/api/alerts/A-1",
            json={"status": "ACKNOWLEDGED"},
            headers=self._headers_for("officer"),
        )
        self.assertEqual(r.status_code, 422, r.text)

    def test_missing_alert_returns_404(self):
        r = self.client.patch(
            "/api/alerts/NOPE",
            json={"status": "RESOLVED"},
            headers=self._headers_for("officer"),
        )
        self.assertEqual(r.status_code, 404)

    def test_status_change_is_audited(self):
        from auth.database import AuthSessionLocal
        from auth.models import AuditLog, User

        # Unique id: the audit log is shared across the whole test class, so a
        # bare count would pick up entries written by the other resolve tests.
        alert_id = f"A-AUDIT-{uuid.uuid4().hex[:8]}"
        self._add_alert(alert_id, "HIGH")

        r = self.client.patch(
            "/api/alerts/" + alert_id,
            json={"status": "RESOLVED"},
            headers=self._headers_for("admin"),
        )
        self.assertEqual(r.status_code, 200, r.text)

        with AuthSessionLocal() as db:
            entries = (
                db.query(AuditLog)
                .filter(
                    AuditLog.action == "ALERT_STATUS_CHANGED",
                    AuditLog.details.like(f"%{alert_id}%"),
                )
                .all()
            )
            self.assertEqual(len(entries), 1)
            self.assertIn("ACTIVE -> RESOLVED", entries[0].details)

            # The entry must be attributed to a real user, not left anonymous.
            actor = db.query(User).filter(User.user_id == entries[0].user_id).first()
            self.assertIsNotNone(actor, "audit entry is not attributed to a user")
            self.assertEqual(actor.role, "admin")


if __name__ == "__main__":
    unittest.main()
