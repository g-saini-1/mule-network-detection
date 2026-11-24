"""Tests for transaction preparation, using small hand-built transaction tables."""

import pandas as pd

from mule_detection.data.prepare_transactions import (
    flag_duplicates,
    flag_own_account_transfers,
    flag_self_transfers,
    sort_by_time,
    transaction_ids,
)

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
    """A transactions table from rows, in the order given."""
    return pd.DataFrame(list(rows))


# --- P1 ----------------------------------------------------------------------------------
def test_p1_transaction_id_is_the_row_position_in_file_order():
    tx = frame(txn(from_account="A"), txn(from_account="B"), txn(from_account="C"))
    assert transaction_ids(tx).tolist() == [0, 1, 2]


# --- P3 ----------------------------------------------------------------------------------
def test_p3_only_the_later_copy_is_flagged():
    tx = frame(txn(), txn())
    assert flag_duplicates(tx).tolist() == [False, True]

    tx = frame(txn(), txn(), txn())
    assert flag_duplicates(tx).tolist() == [False, True, True]


def test_p3_rows_differing_in_one_column_are_not_duplicates():
    tx = frame(txn(), txn(amount_paid=500))
    assert flag_duplicates(tx).tolist() == [False, False]


def test_p3_a_copy_is_flagged_even_with_rows_in_between():
    tx = frame(txn(), txn(amount_paid=500), txn())
    assert flag_duplicates(tx).tolist() == [False, False, True]


def test_p3_transaction_id_is_ignored():
    tx = frame(txn(transaction_id=1), txn(transaction_id=2))
    assert flag_duplicates(tx).tolist() == [False, True]


# --- P4 ----------------------------------------------------------------------------------
def test_p4_only_same_bank_and_same_account_is_a_self_transfer():
    tx = frame(txn(to_bank="10", to_account="A"), txn(), txn(to_account="A"), txn(to_bank="10"))
    assert flag_self_transfers(tx).tolist() == [True, False, False, False]


# --- P5 ----------------------------------------------------------------------------------
def test_p5_same_entity_different_banks_is_not_own_account_transfer():
    tx = frame(txn())
    accs = frame(
        acc(bank_id="10", account_number="A", entity_id="E1"),
        acc(bank_id="20", account_number="B", entity_id="E1"),
    )
    assert flag_own_account_transfers(tx, accs).tolist() == [False]


def test_p5_same_entity_same_bank_is_own_account_transfer():
    tx = frame(txn(to_bank="10"))
    accs = frame(
        acc(bank_id="10", account_number="A", entity_id="E1"),
        acc(bank_id="10", account_number="B", entity_id="E1"),
    )
    assert flag_own_account_transfers(tx, accs).tolist() == [True]


def test_p5_different_entity_same_bank_is_not_own_account_transfer():
    tx = frame(txn(to_bank="10"))
    accs = frame(
        acc(bank_id="10", account_number="A", entity_id="E1"),
        acc(bank_id="10", account_number="B", entity_id="E2"),
    )
    assert flag_own_account_transfers(tx, accs).tolist() == [False]


def test_p5_unknown_entity_same_bank_is_not_own_account_transfer():
    tx = frame(txn(to_bank="10", to_account="Z"))
    accs = frame(acc(bank_id="10", account_number="A", entity_id="E1"))
    assert flag_own_account_transfers(tx, accs).tolist() == [False]


def test_p5_same_entity_same_bank_same_account_is_not_own_account_transfer():
    tx = frame(txn(to_bank="10", to_account="A"))
    accs = frame(acc(bank_id="10", account_number="A", entity_id="E1"))
    assert flag_own_account_transfers(tx, accs).tolist() == [False]


def test_p5_result_keeps_the_row_labels_of_tx():
    tx = frame(txn(to_bank="10", to_account="A")).set_axis([99])
    accs = frame(acc(bank_id="10", account_number="A", entity_id="E1"))
    assert flag_own_account_transfers(tx, accs).index.tolist() == [99]


def test_p7_out_of_time_order():
    tx = frame(txn(transaction_id=0, timestamp=T2), txn(transaction_id=1, timestamp=T1))
    assert sort_by_time(tx)["transaction_id"].tolist() == [1, 0]


def test_p7_ties_already_in_time_order():
    tx = frame(txn(transaction_id=0, timestamp=T1), txn(transaction_id=1, timestamp=T1))
    assert sort_by_time(tx)["transaction_id"].tolist() == [0, 1]


def test_p7_ties_out_of_time_order():
    tx = frame(txn(transaction_id=1, timestamp=T1), txn(transaction_id=0, timestamp=T1))
    assert sort_by_time(tx)["transaction_id"].tolist() == [0, 1]
