"""Builders for small hand-built transaction and account tables, shared by the test files."""

import pandas as pd

from mule_detection.source.load import TRANSACTION_HEADER

# One valid raw transaction row as text, in file column order, for loader and validation tests.
GOOD_ROW = [
    "2022/09/01 00:20",
    "010",
    "8000EBD30",
    "0010",
    "8000F5340",
    "3697.34",
    "US Dollar",
    "3697.34",
    "US Dollar",
    "Reinvestment",
    "0",
]

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


def raw_transactions_file(tmp_path, *rows):
    """A raw transactions file in `tmp_path`: the expected header, then the text rows given."""
    path = tmp_path / "trans.csv"
    lines = [",".join(TRANSACTION_HEADER), *(",".join(row) for row in rows)]
    path.write_text("\n".join(lines) + "\n")
    return path
