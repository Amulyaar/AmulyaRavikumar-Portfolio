"""Fixed-seed invoice fixtures for repeatable release simulations."""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone


def generate_invoices(count: int = 1000, seed: int = 2027) -> list[dict]:
    if count < 414:
        raise ValueError("The default fault-injection plan requires at least 414 invoices")
    rng = random.Random(seed)
    anchor = datetime(2027, 9, 15, 12, tzinfo=timezone.utc)
    currencies = ["USD", "CAD", "GBP"]
    invoices = []
    for n in range(1, count + 1):
        invoice_id = f"INV-2027-{n:04d}"
        amount = rng.randint(2_500, 2_500_000)
        currency = rng.choice(currencies)
        created = anchor - timedelta(minutes=rng.randint(0, 60 * 24 * 30))
        invoices.append({
            "invoice_id": invoice_id,
            "vendor_id": f"V-{rng.randint(1, 90):04d}",
            "invoice_number": f"{rng.randint(10_000, 99_999)}-{n:04d}",
            "amount_cents": amount,
            "currency": currency,
            "po_amount_cents": amount,
            "po_currency": currency,
            "payee_verified": True,
            "approval_count": 2,
            "payment_reference": f"PAY-{invoice_id}",
            "ledger_amount_cents": amount,
            "ledger_posted": True,
            "invoice_document_hash": f"sha256:{rng.getrandbits(128):032x}",
            "api_latency_ms": rng.randint(70, 290),
            "created_at": created.isoformat(),
            "due_date": (created.date() + timedelta(days=rng.randint(15, 45))).isoformat(),
            "status": "READY",
            "fraud_hold": False,
            "ground_truth_defects": [],
        })

    # High-severity seeded defects. The validator detects 24/25; the opaque hold
    # defect is intentionally not represented by a machine-visible signal.
    cases = [
        *((n, "duplicate_payment") for n in range(100, 106)),
        *((n, "unverified_beneficiary") for n in range(110, 115)),
        *((n, "po_amount_mismatch") for n in range(120, 125)),
        *((n, "approval_chain_gap") for n in range(130, 135)),
        *((n, "currency_mismatch") for n in range(140, 143)),
        (150, "opaque_fraud_hold"),
    ]
    for n, category in cases:
        invoice = invoices[n - 1]
        invoice["ground_truth_defects"].append({"id": f"GT-H-{n:04d}", "category": category, "severity": "high"})
        if category == "duplicate_payment":
            invoice["payment_reference"] = invoices[n - 2]["payment_reference"]
        elif category == "unverified_beneficiary":
            invoice["payee_verified"] = False
        elif category == "po_amount_mismatch":
            invoice["po_amount_cents"] += 5_000
        elif category == "approval_chain_gap":
            invoice["approval_count"] = 0
        elif category == "currency_mismatch":
            invoice["po_currency"] = "EUR" if invoice["currency"] != "EUR" else "USD"
        elif category == "opaque_fraud_hold":
            invoice["fraud_hold"] = True

    # Additional medium-severity integration conditions exercise SLO and
    # completeness gates without changing the high-severity recall denominator.
    for n in range(200, 280):
        invoice = invoices[n - 1]
        invoice["api_latency_ms"] = rng.randint(480, 900)
        invoice["ground_truth_defects"].append({"id": f"GT-M-{n:04d}", "category": "slow_gateway", "severity": "medium"})
    for n in range(300, 320):
        invoice = invoices[n - 1]
        invoice["invoice_document_hash"] = ""
        invoice["ground_truth_defects"].append({"id": f"GT-M-{n:04d}", "category": "missing_document", "severity": "medium"})
    for n in range(400, 415):
        invoice = invoices[n - 1]
        invoice["ledger_posted"] = False
        invoice["ledger_amount_cents"] = None
        invoice["status"] = "PENDING_LEDGER"
        invoice["ground_truth_defects"].append({"id": f"GT-M-{n:04d}", "category": "ledger_not_posted", "severity": "medium"})

    # A small time-ordered event stream per invoice. Sequence errors are
    # represented as an observed integration defect, not a fabricated metric.
    for invoice in invoices:
        created = datetime.fromisoformat(invoice["created_at"])
        invoice["events"] = [
            {"sequence": 1, "event": "invoice.received", "at": created.isoformat(), "service": "Invoice API"},
            {"sequence": 2, "event": "invoice.approved", "at": (created + timedelta(seconds=8)).isoformat(), "service": "Approval service"},
            {"sequence": 3, "event": "payment.authorized", "at": (created + timedelta(seconds=19)).isoformat(), "service": "Payment gateway"},
            {"sequence": 4, "event": "ledger.posted" if invoice["ledger_posted"] else "ledger.pending",
             "at": (created + timedelta(seconds=31)).isoformat(), "service": "Ledger"},
        ]
    return invoices
