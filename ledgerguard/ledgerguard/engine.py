"""Invoice validation, fault-detection evaluation, and release decision logic."""
from __future__ import annotations

from collections import defaultdict
from math import ceil

SEVERITY_WEIGHT = {"critical": 40, "high": 20, "medium": 8, "low": 2}
TRUTH_TO_RULE = {
    "duplicate_payment": "duplicate_reference",
    "unverified_beneficiary": "payee_verification",
    "po_amount_mismatch": "po_variance",
    "approval_chain_gap": "approval_policy",
    "currency_mismatch": "currency_consistency",
}


def _finding(invoice: dict, rule_id: str, severity: str, title: str, message: str,
             observed=None, expected=None) -> dict:
    return {
        "finding_id": f"FG-{invoice['invoice_id']}-{rule_id.upper()}",
        "invoice_id": invoice["invoice_id"], "vendor_id": invoice["vendor_id"],
        "rule_id": rule_id, "severity": severity, "title": title, "message": message,
        "observed": observed, "expected": expected, "status": "Open",
        "owner_team": {"duplicate_reference": "Payments", "payee_verification": "Risk & Identity",
                       "po_variance": "Procurement Ops", "approval_policy": "Finance Controls",
                       "currency_consistency": "Payments", "gateway_latency": "Platform",
                       "ledger_posting": "Ledger", "document_integrity": "Invoice API"}.get(rule_id, "Platform"),
        "risk_points": SEVERITY_WEIGHT[severity],
    }


def validate_invoice(invoice: dict) -> list[dict]:
    """Apply deterministic controls to one invoice; ground-truth labels are ignored."""
    findings = []
    amount = invoice.get("amount_cents")
    if not isinstance(amount, int) or amount <= 0:
        findings.append(_finding(invoice, "positive_amount", "critical", "Invalid invoice amount",
                                 "Invoice amount must be a positive integer number of cents.", amount, "> 0 cents"))
    if invoice.get("currency") != invoice.get("po_currency"):
        findings.append(_finding(invoice, "currency_consistency", "high", "Invoice and PO currencies differ",
                                 "Currency mismatch can cause a mispayment or reconciliation failure.",
                                 invoice.get("currency"), invoice.get("po_currency")))
    po_amount = invoice.get("po_amount_cents")
    if isinstance(amount, int) and isinstance(po_amount, int) and abs(amount - po_amount) > 100:
        findings.append(_finding(invoice, "po_variance", "high", "Invoice exceeds purchase order tolerance",
                                 "Amount variance is greater than the $1.00 control tolerance.", amount, po_amount))
    if invoice.get("payee_verified") is not True:
        findings.append(_finding(invoice, "payee_verification", "critical", "Beneficiary is not verified",
                                 "Payment is held until the bank beneficiary is verified.",
                                 invoice.get("payee_verified"), True))
    if isinstance(amount, int) and amount >= 1_000_000 and invoice.get("approval_count", 0) < 2:
        findings.append(_finding(invoice, "approval_policy", "high", "Approval chain below policy",
                                 "Invoices of $10,000 or more require two independent approvals.",
                                 invoice.get("approval_count"), 2))
    latency = invoice.get("api_latency_ms")
    if isinstance(latency, int) and latency > 450:
        findings.append(_finding(invoice, "gateway_latency", "medium", "Payment API exceeds latency SLO",
                                 "Gateway response exceeded the 450 ms per-request target.", latency, "<= 450 ms"))
    if not invoice.get("invoice_document_hash"):
        findings.append(_finding(invoice, "document_integrity", "medium", "Invoice document is missing",
                                 "A source document hash is required for the audit trail.", "missing", "sha256 digest"))
    if invoice.get("status") == "PENDING_LEDGER" or invoice.get("ledger_posted") is not True:
        findings.append(_finding(invoice, "ledger_posting", "high", "Payment is not posted to the ledger",
                                 "A captured payment has no confirmed ledger posting.",
                                 invoice.get("ledger_posted"), True))
    ledger_amount = invoice.get("ledger_amount_cents")
    if invoice.get("ledger_posted") and isinstance(amount, int) and ledger_amount != amount:
        findings.append(_finding(invoice, "ledger_amount", "critical", "Ledger amount differs from invoice",
                                 "Posted ledger amount does not reconcile to the approved invoice.",
                                 ledger_amount, amount))
    return findings


def evaluate_invoices(invoices: list[dict], finding_statuses: dict[str, str] | None = None) -> dict:
    finding_statuses = finding_statuses or {}
    findings = [finding for invoice in invoices for finding in validate_invoice(invoice)]
    reference_groups = defaultdict(list)
    for invoice in invoices:
        reference_groups[invoice.get("payment_reference")].append(invoice)
    for reference, group in reference_groups.items():
        if reference and len(group) > 1:
            for invoice in group[1:]:
                findings.append(_finding(invoice, "duplicate_reference", "high", "Duplicate payment reference",
                                         "Payment reference appears on more than one invoice.", reference, "unique reference"))
    findings.sort(key=lambda f: (-SEVERITY_WEIGHT[f["severity"]], f["invoice_id"], f["rule_id"]))
    for finding in findings:
        finding["status"] = finding_statuses.get(finding["finding_id"], "Open")

    truth = [(invoice, defect) for invoice in invoices for defect in invoice.get("ground_truth_defects", [])]
    high_truth = [(invoice, defect) for invoice, defect in truth if defect["severity"] == "high"]
    detected_pairs = {(f["invoice_id"], f["rule_id"]) for f in findings}
    true_positives = sum((invoice["invoice_id"], TRUTH_TO_RULE.get(defect["category"], "__undetected__")) in detected_pairs
                         for invoice, defect in high_truth)
    recall = true_positives / len(high_truth) if high_truth else 1.0
    open_findings = [f for f in findings if f["status"] not in ("Resolved", "Accepted")]
    critical = [f for f in open_findings if f["severity"] == "critical"]
    high = [f for f in open_findings if f["severity"] == "high"]
    p95_latency = _percentile([i["api_latency_ms"] for i in invoices], .95)
    matched = sum(i.get("ledger_posted") is True and i.get("ledger_amount_cents") == i.get("amount_cents")
                  for i in invoices)
    reconciliation_pct = round(matched / len(invoices) * 100, 2) if invoices else 100.0
    detected_high = sum(f["severity"] in ("critical", "high") for f in findings)
    risk_points = sum(f["risk_points"] for f in open_findings)
    at_risk_ids = {f["invoice_id"] for f in open_findings if f["severity"] in ("critical", "high")}
    exposure_cents = sum(i["amount_cents"] for i in invoices if i["invoice_id"] in at_risk_ids)

    gates = [
        _gate("High-severity fault recall", recall >= .96, f"{true_positives}/{len(high_truth)} seeded high-severity defects detected (target ≥ 96%)", "benchmark", "quality"),
        _gate("Critical financial controls", len(critical) == 0, f"{len(critical)} open critical findings (target 0)", "metric:open_critical", "safety"),
        _gate("Payment reference uniqueness", not any(f["rule_id"] == "duplicate_reference" and f["status"] not in ("Resolved", "Accepted") for f in findings), "Duplicate payment references must be resolved before release.", "metric:duplicate_references", "integrity"),
        _gate("Invoice-to-ledger reconciliation", reconciliation_pct >= 99.5, f"{reconciliation_pct:.2f}% reconciled (target ≥ 99.50%)", "metric:reconciliation_pct", "integrity"),
        _gate("Payment API p95 latency", p95_latency <= 450, f"p95 {p95_latency} ms (target ≤ 450 ms)", "metric:p95_latency_ms", "reliability"),
        _gate("Audit document completeness", not any(f["rule_id"] == "document_integrity" and f["status"] not in ("Resolved", "Accepted") for f in findings), "Every invoice must have a source document hash.", "metric:missing_documents", "audit"),
    ]
    blocked = sum(g["status"] == "blocked" for g in gates)
    return {
        "scenario": "Synthetic supplier-payment release", "as_of": "2027-09-15",
        "invoice_count": len(invoices), "finding_count": len(findings), "open_findings": len(open_findings),
        "open_critical": len(critical), "open_high": len(high), "detected_high_severity": detected_high,
        "seeded_high_severity": len(high_truth), "true_positive_high_severity": true_positives,
        "high_severity_recall_pct": round(recall * 100, 2), "p95_latency_ms": p95_latency,
        "reconciliation_pct": reconciliation_pct, "open_risk_points": risk_points,
        "risk_score": min(100, round(risk_points / max(1, len(invoices)) * 100)),
        "at_risk_invoice_cents": exposure_cents, "gate_count": len(gates), "blocked_gates": blocked,
        "release_decision": "GO" if blocked == 0 else "NO-GO", "gates": gates,
        "findings": findings,
    }


def _gate(name: str, passed: bool, detail: str, source: str, category: str) -> dict:
    return {"name": name, "status": "passed" if passed else "blocked", "detail": detail,
            "source": source, "category": category}


def _percentile(values: list[int], p: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, ceil(p * len(ordered)) - 1))]


def build_report(assessment: dict) -> dict:
    findings = assessment["findings"]
    critical = [f for f in findings if f["severity"] == "critical" and f["status"] not in ("Resolved", "Accepted")]
    high = [f for f in findings if f["severity"] == "high" and f["status"] not in ("Resolved", "Accepted")]
    claims = [
        {"text": f"{assessment['invoice_count']:,} synthetic invoices were evaluated across payment, approval, and ledger controls.", "citations": ["metric:invoice_count"]},
        {"text": f"The validator detected {assessment['true_positive_high_severity']} of {assessment['seeded_high_severity']} seeded high-severity defects ({assessment['high_severity_recall_pct']:.2f}% recall).", "citations": ["benchmark:high_severity_recall_pct"]},
        {"text": f"{assessment['open_critical']} critical and {assessment['open_high']} high-severity findings remain open; current decision is {assessment['release_decision']}.", "citations": ["metric:open_critical", "metric:open_high", "metric:release_decision"]},
        {"text": f"Invoice-to-ledger match is {assessment['reconciliation_pct']:.2f}% and payment API p95 is {assessment['p95_latency_ms']} ms.", "citations": ["metric:reconciliation_pct", "metric:p95_latency_ms"]},
    ]
    actions = [{"priority": f["severity"].upper(), "title": f["title"], "invoice_id": f["invoice_id"],
                "owner_team": f["owner_team"], "next_step": f["message"],
                "citations": [f"finding:{f['finding_id']}", f"invoice:{f['invoice_id']}"]}
               for f in (critical + high)[:8]]
    return {"title": "Supplier payment release brief", "decision": assessment["release_decision"],
            "claims": claims, "actions": actions,
            "method": "Deterministic control evaluation against a fixed-seed synthetic invoice set; no generative model is used."}
