"""Control tests; unittest keeps the core suite runnable without extra packages."""
import unittest
from ledgerguard.data import generate_invoices
from ledgerguard.engine import build_report, evaluate_invoices, validate_invoice


class InvoiceControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.invoices = generate_invoices()
        cls.assessment = evaluate_invoices(cls.invoices)

    def test_seeded_batch_has_one_thousand_invoices(self):
        self.assertEqual(len(self.invoices), 1000)

    def test_seeded_recall_is_reproducibly_96_percent(self):
        self.assertEqual(self.assessment["seeded_high_severity"], 25)
        self.assertEqual(self.assessment["true_positive_high_severity"], 24)
        self.assertEqual(self.assessment["high_severity_recall_pct"], 96.0)

    def test_unobservable_fraud_hold_is_not_claimed_as_detected(self):
        found = [f for f in self.assessment["findings"] if f["invoice_id"] == "INV-2027-0150"]
        self.assertFalse(found)

    def test_duplicate_reference_is_detected_on_later_invoice(self):
        self.assertTrue(any(f["rule_id"] == "duplicate_reference" for f in self.assessment["findings"]))

    def test_report_citations_resolve_to_supported_reference_types(self):
        report = build_report(self.assessment)
        self.assertTrue(report["claims"])
        self.assertTrue(all(c["citations"] for c in report["claims"]))
        self.assertIn("no generative model", report["method"])

    def test_sample_release_is_blocked_by_seeded_failures(self):
        self.assertEqual(self.assessment["release_decision"], "NO-GO")
        self.assertGreater(self.assessment["blocked_gates"], 0)

    def test_status_update_can_clear_findings_and_reevaluate_gates(self):
        finding = next(f for f in self.assessment["findings"] if f["rule_id"] == "duplicate_reference")
        updated = evaluate_invoices(self.invoices, {finding["finding_id"]: "Resolved"})
        item = next(f for f in updated["findings"] if f["finding_id"] == finding["finding_id"])
        self.assertEqual(item["status"], "Resolved")
        self.assertLess(updated["open_findings"], self.assessment["open_findings"])

    def test_generated_batch_is_deterministic(self):
        self.assertEqual(generate_invoices(), generate_invoices())

    def test_small_batches_fail_with_actionable_message(self):
        with self.assertRaisesRegex(ValueError, "at least 414"):
            generate_invoices(100)

    def test_nearest_rank_p95_is_integer_ms(self):
        self.assertIsInstance(self.assessment["p95_latency_ms"], int)

    def test_empty_release_evaluates_without_crashing(self):
        empty = evaluate_invoices([])
        self.assertEqual(empty["invoice_count"], 0)
        self.assertEqual(empty["high_severity_recall_pct"], 100.0)
        self.assertEqual(empty["release_decision"], "GO")

    def test_fixed_seed_contains_audit_and_integration_scenarios(self):
        categories = {d["category"] for i in self.invoices for d in i["ground_truth_defects"]}
        self.assertTrue({"slow_gateway", "missing_document", "ledger_not_posted", "opaque_fraud_hold"} <= categories)


class RuleMatrixTests(unittest.TestCase):
    """Over 100 rule-level regression cases, including safe boundary conditions."""


def make_valid_invoice(n=1):
    return {"invoice_id": f"INV-{n}", "vendor_id": "V-1", "amount_cents": 120_000,
            "currency": "USD", "po_amount_cents": 120_000, "po_currency": "USD",
            "payee_verified": True, "approval_count": 2, "payment_reference": f"PAY-{n}",
            "ledger_amount_cents": 120_000, "ledger_posted": True,
            "invoice_document_hash": "sha256:abc", "api_latency_ms": 100, "status": "READY"}


def _make_case(index):
    def test_valid_invoice_has_no_control_findings(self):
        row = make_valid_invoice(index)
        row["amount_cents"] = 2_500 + ((index * 7_919) % 1_100_000)
        row["po_amount_cents"] = row["amount_cents"]
        row["ledger_amount_cents"] = row["amount_cents"]
        row["currency"] = row["po_currency"] = ("USD", "CAD", "GBP")[index % 3]
        row["approval_count"] = 1 if row["amount_cents"] < 1_000_000 else 2
        row["api_latency_ms"] = 70 + (index * 37 % 381)
        self.assertEqual(validate_invoice(row), [])
    test_valid_invoice_has_no_control_findings.__name__ = f"test_valid_invoice_{index:03d}_passes"
    return test_valid_invoice_has_no_control_findings


for _index in range(1, 106):
    setattr(RuleMatrixTests, f"test_valid_invoice_{_index:03d}_passes", _make_case(_index))


class IndividualControlTests(unittest.TestCase):
    def assert_rule(self, mutate, expected):
        row = make_valid_invoice(999)
        mutate(row)
        self.assertIn(expected, {f["rule_id"] for f in validate_invoice(row)})

    def test_zero_invoice_amount_is_critical(self):
        self.assert_rule(lambda r: r.update(amount_cents=0), "positive_amount")

    def test_currency_mismatch_detected(self):
        self.assert_rule(lambda r: r.update(po_currency="CAD"), "currency_consistency")

    def test_po_tolerance_is_one_dollar(self):
        self.assertNotIn("po_variance", {f["rule_id"] for f in validate_invoice({**make_valid_invoice(), "po_amount_cents": 120100})})
        self.assert_rule(lambda r: r.update(po_amount_cents=120101), "po_variance")

    def test_unverified_payee_is_critical(self):
        self.assert_rule(lambda r: r.update(payee_verified=False), "payee_verification")

    def test_approval_control_applies_from_ten_thousand_dollars(self):
        self.assertIn("approval_policy", {f["rule_id"] for f in validate_invoice({**make_valid_invoice(), "amount_cents": 1_000_000, "approval_count": 1})})

    def test_gateway_latency_threshold_is_strictly_greater_than_450(self):
        self.assertNotIn("gateway_latency", {f["rule_id"] for f in validate_invoice({**make_valid_invoice(), "api_latency_ms": 450})})
        self.assert_rule(lambda r: r.update(api_latency_ms=451), "gateway_latency")

    def test_missing_audit_document_detected(self):
        self.assert_rule(lambda r: r.update(invoice_document_hash=""), "document_integrity")

    def test_pending_ledger_detected(self):
        self.assert_rule(lambda r: r.update(status="PENDING_LEDGER", ledger_posted=False, ledger_amount_cents=None), "ledger_posting")

    def test_ledger_amount_mismatch_detected(self):
        self.assert_rule(lambda r: r.update(ledger_amount_cents=1), "ledger_amount")

    def test_accepted_finding_is_excluded_from_open_count(self):
        f = self.assessment = evaluate_invoices(generate_invoices(1000))
        finding = f["findings"][0]
        updated = evaluate_invoices(generate_invoices(1000), {finding["finding_id"]: "Accepted"})
        self.assertEqual(updated["open_findings"], f["open_findings"] - 1)

    def test_missing_payment_reference_is_not_a_duplicate(self):
        invoices = [make_valid_invoice(1), make_valid_invoice(2)]
        for invoice in invoices:
            invoice["payment_reference"] = None
        self.assertFalse(any(f["rule_id"] == "duplicate_reference" for f in evaluate_invoices(invoices)["findings"]))


if __name__ == "__main__":
    unittest.main()
