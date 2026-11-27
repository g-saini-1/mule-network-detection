"""Builders for small hand-built transaction and account tables, shared by the test files."""

import pandas as pd

T1 = pd.Timestamp("2022-09-01 09:00")
T2 = pd.Timestamp("2022-09-01 12:00")

DEFAULT_TXN = {
    "timestamp": T1,
    "from_bank": "10",
    "from_account": "A",
    "to_bank": "20",
    "to_account": "B",
    "amount_received": 100.0,
    "receiving_currency": "US Dollar",
    "amount_paid": 100.0,
    "payment_currency": "US Dollar",
    "payment_format": "ACH",
    "is_laundering": 0,
}

DEFAULT_ACCOUNT = {
    "bank_name": "My Bank",
    "bank_id": "10",
    "account_number": "A",
    "entity_id": "E1",
    "entity_name": "Entity 1",
}


def txn(**changes):
    """One transaction: the default row with the given columns changed."""
    return {**DEFAULT_TXN, **changes}


def acc(**changes):
    """One account: the default row with the given columns changed."""
    return {**DEFAULT_ACCOUNT, **changes}


def frame(*rows):
    """A table from rows, in the order given."""
    return pd.DataFrame(list(rows))
