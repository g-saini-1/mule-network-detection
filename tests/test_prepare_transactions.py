"""Tests for transaction preparation, using small hand-built transaction tables."""

from builders import T1, T2, frame, txn

from mule_detection.source.prepare_transactions import flag_duplicates, sort_by_time


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


# --- P7 ----------------------------------------------------------------------------------
def test_p7_out_of_time_order():
    tx = frame(txn(transaction_id=0, timestamp=T2), txn(transaction_id=1, timestamp=T1))
    assert sort_by_time(tx)["transaction_id"].tolist() == [1, 0]


def test_p7_ties_already_in_time_order():
    tx = frame(txn(transaction_id=0, timestamp=T1), txn(transaction_id=1, timestamp=T1))
    assert sort_by_time(tx)["transaction_id"].tolist() == [0, 1]


def test_p7_ties_out_of_time_order():
    tx = frame(txn(transaction_id=1, timestamp=T1), txn(transaction_id=0, timestamp=T1))
    assert sort_by_time(tx)["transaction_id"].tolist() == [0, 1]
