"""Builders for small hand-built transaction and account tables, shared by the test files."""

import pandas as pd

from mule_detection.source.load import TRANSACTION_COLUMNS, TRANSACTION_HEADER

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


def as_loaded(tx):
    """`tx` typed as `load_transactions` returns it (P1, P2).

    Currencies and payment formats become categories and the laundering flag an 8-bit integer.
    If `tx` has `transaction_id`, it becomes the first column, followed by the source columns;
    any other column is kept, after them.
    """
    typed = tx.astype(
        {
            "payment_currency": "category",
            "receiving_currency": "category",
            "payment_format": "category",
            "is_laundering": "int8",
        }
    )
    if "transaction_id" in typed.columns:
        leading = ["transaction_id", *TRANSACTION_COLUMNS]
        typed = typed[leading + [c for c in typed.columns if c not in leading]]
    return typed


def raw_transactions_file(tmp_path, *rows):
    """A raw transactions file in `tmp_path`: the expected header, then the text rows given."""
    path = tmp_path / "trans.csv"
    lines = [",".join(TRANSACTION_HEADER), *(",".join(row) for row in rows)]
    path.write_text("\n".join(lines) + "\n")
    return path


# The output columns in order, as the preparation guide (Table 1) lists them.
GUIDE_COLUMNS = [
    "transaction_id",
    "timestamp",
    "from_bank",
    "from_account",
    "to_bank",
    "to_account",
    "amount_paid",
    "payment_currency",
    "amount_received",
    "receiving_currency",
    "payment_format",
    "is_duplicate",
    "is_self_transfer",
    "is_own_account_transfer",
    "amount_paid_base",
    "amount_received_base",
]


# Two transactions in time order, with IDs 0 and 1: the default rows of `prepared` and `raw_text`.
DEFAULT_ROWS = (txn(transaction_id=0), txn(transaction_id=1, timestamp=T2))


def prepared(*rows):
    """Prepared transactions from typed rows: no laundering flag, flags false, base amounts 100.

    `DEFAULT_ROWS` if no rows are given.
    """
    rows = rows or DEFAULT_ROWS
    added = {
        "is_duplicate": False,
        "is_self_transfer": False,
        "is_own_account_transfer": False,
        "amount_paid_base": 100.0,
        "amount_received_base": 100.0,
    }
    return as_loaded(frame(*rows)).assign(**added)[GUIDE_COLUMNS]


def raw_text(*rows):
    """Raw transactions from rows, every column as text, for P8 tests; `DEFAULT_ROWS` if none.

    Only the amounts and currencies, the columns P8 compares, are in the raw file's form; e.g.
    timestamps and bank IDs are not. Raw rows have no `transaction_id`: a row's ID is its
    position, so any `transaction_id` in the rows given is dropped.
    """
    rows = rows or DEFAULT_ROWS
    return frame(*rows)[TRANSACTION_COLUMNS].astype(str)
