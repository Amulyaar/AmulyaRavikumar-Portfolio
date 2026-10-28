"""FastAPI/PostgreSQL smoke tests; skipped by stdlib-only local runs without dependencies."""
import os
import tempfile
import unittest

try:
    from fastapi.testclient import TestClient
    from ledgerguard import api
    from ledgerguard.storage import SnapshotStore
    API_DEPS_AVAILABLE = True
except Exception:
    API_DEPS_AVAILABLE = False


@unittest.skipUnless(API_DEPS_AVAILABLE, "install the project dependencies to run API integration tests")
class ApiIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = None
        # In CI, keep the configured PostgreSQL store so these smoke tests
        # exercise the same database option used in the workflow. Use isolated
        # SQLite only for a local API run without DATABASE_URL.
        if not os.getenv("DATABASE_URL", "").startswith("postgresql"):
            cls.temp = tempfile.TemporaryDirectory()
            api.store = SnapshotStore(f"sqlite:///{cls.temp.name}/api-test.db")
        cls.client = TestClient(api.app)

    @classmethod
    def tearDownClass(cls):
        if cls.temp:
            cls.temp.cleanup()

    def test_health_endpoint(self):
        self.assertEqual(self.client.get("/api/health").json()["status"], "ok")

    def test_overview_returns_release_kpis_and_gate_decision(self):
        result = self.client.get("/api/overview").json()
        self.assertEqual(result["invoice_count"], 1000)
        self.assertEqual(result["release_decision"], "NO-GO")
        self.assertEqual(result["high_severity_recall_pct"], 96.0)

    def test_findings_endpoint_filters_and_searches(self):
        result = self.client.get("/api/findings?severity=critical&limit=5").json()
        self.assertLessEqual(len(result["items"]), 5)
        self.assertGreater(result["total"], 0)
        self.assertTrue(all(row["severity"] == "critical" for row in result["items"]))

    def test_invoice_detail_includes_ordered_source_events(self):
        result = self.client.get("/api/invoices/INV-2027-0001").json()
        self.assertEqual(len(result["invoice"]["events"]), 4)
        self.assertEqual(result["invoice"]["events"][0]["sequence"], 1)

    def test_status_update_persists_across_requests(self):
        finding = self.client.get("/api/findings?limit=1").json()["items"][0]
        response = self.client.patch(f"/api/findings/{finding['finding_id']}/status", json={"status": "Investigating"})
        self.assertEqual(response.status_code, 200)
        refreshed = self.client.get("/api/findings?search={}".format(finding["finding_id"])).json()["items"][0]
        self.assertEqual(refreshed["status"], "Investigating")

    def test_csv_export_has_header_and_findings(self):
        response = self.client.get("/api/export/findings.csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn("finding_id,invoice_id", response.text)

    def test_report_and_evidence_reference_resolve(self):
        report = self.client.get("/api/report").json()
        reference = report["claims"][0]["citations"][0]
        result = self.client.get("/api/evidence/" + reference.replace(":", "%3A"))
        self.assertEqual(result.status_code, 200)

    def test_dashboard_static_page_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("LedgerGuard", response.text)


if __name__ == "__main__":
    unittest.main()
