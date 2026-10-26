import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analysis_core import resume_metrics, summarize_rows
from analyze import complete_lines


HEADER = [
    "rank_in_set",
    "recommendation_set_id",
    "clicked",
    "set_size",
    "algorithm-class",
    "request_received",
]


class SummarizeRowsTests(unittest.TestCase):
    def test_first_range_keeps_header_and_discards_partial_trailing_record(self):
        raw = b"header\tvalue\ncomplete\trow\npartial"
        rows, header = complete_lines(raw, first_window=True)
        self.assertEqual(header, ["header", "value"])
        self.assertEqual(list(rows), [["complete", "row"]])

    def test_later_range_discards_partial_boundary_records(self):
        raw = b"partial-start\ncomplete\trow\npartial-end"
        rows, header = complete_lines(raw, first_window=False)
        self.assertIsNone(header)
        self.assertEqual(list(rows), [["complete", "row"]])

    def test_rank_ctr_ratio_and_shares(self):
        rows = [
            ["1", "a", "2020-01-01", "3", "NULL", "2020-01-01 00:00:00"],
            ["2", "a", "NULL", "3", "NULL", "2020-01-01 00:00:00"],
            ["3", "a", "NULL", "3", "NULL", "2020-01-01 00:00:00"],
            ["1", "b", "NULL", "3", "NULL", "2020-01-02 00:00:00"],
            ["2", "b", "2020-01-02", "3", "NULL", "2020-01-02 00:00:00"],
            ["3", "b", "NULL", "3", "NULL", "2020-01-02 00:00:00"],
        ]
        result = summarize_rows(rows, HEADER)
        comparison = result["position_comparison"]
        self.assertEqual(result["sample"]["recommendation_rows"], 6)
        self.assertEqual(result["sample"]["recommendation_sets"], 2)
        self.assertEqual(comparison["rank_1_ctr"], 0.5)
        self.assertEqual(comparison["ranks_2_to_10_ctr"], 0.25)
        self.assertEqual(comparison["rank_1_ctr_ratio_vs_ranks_2_to_10"], 2.0)
        self.assertEqual(comparison["rank_1_share_of_clicks"], 0.5)
        self.assertTrue(result["quality_checks"]["all_sampled_algorithm_class_values_missing"])

    def test_malformed_and_out_of_range_rows_are_counted(self):
        rows = [["0", "bad-rank", "NULL", "3", "NULL", "2020-01-01"]]
        result = summarize_rows(rows, HEADER)
        self.assertEqual(result["quality_checks"]["rows_skipped"], 1)
        self.assertEqual(result["sample"]["recommendation_rows"], 0)

    def test_required_columns_are_checked(self):
        with self.assertRaisesRegex(ValueError, "Missing required columns"):
            summarize_rows([], ["rank_in_set"])

    def test_resume_metrics_use_aggregate_values(self):
        summary = summarize_rows(
            [["1", "a", "click", "1", "NULL", "2020-01-01"]], HEADER
        )
        values = resume_metrics(summary)
        self.assertEqual(values["impressions"], 1)
        self.assertEqual(values["rank_1_ctr_percent"], 100.0)


if __name__ == "__main__":
    unittest.main()
