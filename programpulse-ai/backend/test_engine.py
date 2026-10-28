import csv
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from engine import Store


class ProgramPulseEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "test.db")

    def tearDown(self):
        self.tmp.cleanup()

    def test_seed_is_five_hundred_tasks_and_repeatable(self):
        self.assertEqual(len(self.store.rows("SELECT id FROM tasks")), 500)
        self.assertEqual(len(self.store.rows("SELECT predecessor_id FROM dependencies")), self.store.overview()["metrics"]["dependency_edges"])
        with tempfile.TemporaryDirectory() as other_dir:
            other = Store(Path(other_dir) / "other.db")
            self.assertEqual(self.store.rows("SELECT id,title,status,progress FROM tasks ORDER BY id"),
                             other.rows("SELECT id,title,status,progress FROM tasks ORDER BY id"))

    def test_dependency_graph_is_acyclic_and_critical_path_resolves(self):
        graph = self.store.dependency_analysis()
        pos = {task_id: i for i, task_id in enumerate(graph["critical_path"])}
        self.assertGreater(graph["edge_count"], 500)
        self.assertGreater(len(graph["critical_path"]), 1)
        self.assertEqual(len(pos), len(graph["critical_path"]))
        edge_set = {(edge["source"], edge["target"]) for edge in graph["edges"]}
        self.assertTrue(all((a, b) in edge_set for a, b in zip(graph["critical_path"], graph["critical_path"][1:])))
        for edge in graph["edges"]:
            self.assertLess(int(edge["source"][2:]), int(edge["target"][2:]))

    def test_status_report_claims_have_resolvable_citations(self):
        report = self.store.status_report()
        self.assertEqual(report["health"], "Red")
        self.assertGreaterEqual(len(report["actions"]), 3)
        refs = {ref for claim in report["claims"] for ref in claim["citations"]}
        refs.update(ref for action in report["actions"] for ref in action["citations"])
        self.assertTrue(all(self.store.evidence(ref) is not None for ref in refs))
        self.assertIn("R-001", report["markdown"])

    def test_csv_export_contains_full_register(self):
        rows = list(csv.DictReader(self.store.tasks_csv().splitlines()))
        self.assertEqual(len(rows), 500)
        self.assertEqual(rows[0]["id"], "T-0001")

    def test_report_tracks_raid_resolution(self):
        with self.store.connect() as conn:
            conn.execute("UPDATE raid SET status='Resolved' WHERE id IN ('R-001','R-002')")
        report = self.store.status_report()
        self.assertEqual(self.store.overview()["metrics"]["critical_raid"], 0)
        self.assertTrue(any("No critical RAID items" in claim["text"] for claim in report["claims"]))


if __name__ == "__main__":
    unittest.main()
