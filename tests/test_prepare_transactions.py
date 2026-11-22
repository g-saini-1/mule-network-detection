"""Tests for transaction preparation, using small hand-built transaction tables."""

import pandas as pd

from mule_detection.data.prepare_transactions import (
    flag_duplicates,
    flag_self_transfers,
    transaction_ids,
)

T1 = pd.Timestamp("2022-09-01 09:00")
T2 = pd.Timestamp("2022-09-01 12:00")

DEFAULT_ROW = {
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


def row(**changes):
    """One transaction: the default row with the given columns changed."""
    return {**DEFAULT_ROW, **changes}


def frame(*rows):
    """A transactions table from rows built with `row()`, in the order given."""
    return pd.DataFrame(list(rows))


# --- P1 ----------------------------------------------------------------------------------


def test_p1_transaction_id_is_the_row_position_in_file_order():
    tx = frame(row(from_account="A"), row(from_account="B"), row(from_account="C"))
    assert transaction_ids(tx).tolist() == [0, 1, 2]


def test_p3_only_the_later_copy_is_flagged():
    tx = frame(row(), row())
    assert flag_duplicates(tx).tolist() == [False, True]

    tx = frame(row(), row(), row())
    assert flag_duplicates(tx).tolist() == [False, True, True]


def test_p3_rows_differing_in_one_column_are_not_duplicates():
    tx = frame(row(), row(amount_paid=500))
    assert flag_duplicates(tx).tolist() == [False, False]


def test_p3_a_copy_is_flagged_even_with_rows_in_between():
    tx = frame(row(), row(amount_paid=500), row())
    assert flag_duplicates(tx).tolist() == [False, False, True]


def test_p3_transaction_id_is_ignored():
    tx = frame(row(transaction_id=1), row(transaction_id=2))
    assert flag_duplicates(tx).tolist() == [False, True]


def test_p4_only_same_bank_and_same_account_is_a_self_transfer():
    tx = frame(row(to_bank="10", to_account="A"), row(), row(to_account="A"), row(to_bank="10"))
    assert flag_self_transfers(tx).tolist() == [True, False, False, False]
