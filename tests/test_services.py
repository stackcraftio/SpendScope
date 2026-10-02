import io

import pandas as pd
import pytest

from spendscope.services import (
    categorise_transaction,
    clean_transactions,
    detect_recurring,
)


def test_categorise_transaction():
    assert categorise_transaction("TESCO STORES", -42.50) == "Groceries"
    assert categorise_transaction("ACME PAYROLL", 2500.00) == "Income"
    assert categorise_transaction("NETFLIX", -10.99) == "Entertainment"
    assert categorise_transaction("UNKNOWN MERCHANT", -12.00) == "Other"


def test_clean_transactions():
    raw = b"""date,description,amount
2026-01-01,ACME PAYROLL,2000
2026-01-02,TESCO STORES,-50.25
not-a-date,BROKEN,-10
"""
    df = clean_transactions(io.BytesIO(raw))

    assert list(df.columns) == [
        "date",
        "description",
        "amount",
        "category",
        "normalized_merchant",
    ]
    assert len(df) == 2
    assert set(df["category"]) == {"Income", "Groceries"}


def test_clean_transactions_requires_columns():
    raw = b"""date,description
2026-01-01,TEST
"""
    with pytest.raises(ValueError):
        clean_transactions(io.BytesIO(raw))


def test_recurring_monthly_detection():
    df = pd.DataFrame([
        {"date": "2026-01-05", "description": "NETFLIX", "amount": -10.99, "category": "Entertainment", "normalized_merchant": "netflix"},
        {"date": "2026-02-05", "description": "NETFLIX", "amount": -10.99, "category": "Entertainment", "normalized_merchant": "netflix"},
        {"date": "2026-03-05", "description": "NETFLIX", "amount": -10.99, "category": "Entertainment", "normalized_merchant": "netflix"},
    ])

    recurring = detect_recurring(df)

    assert len(recurring) == 1
    assert recurring[0]["cadence"] == "Monthly"
    assert recurring[0]["merchant"] == "NETFLIX"
