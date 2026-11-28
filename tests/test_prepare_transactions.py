"""Tests for transaction preparation, using small hand-built transaction tables."""

import pandas as pd
import pandera.pandas as pa
import pytest
from builders import T1, T2, acc, as_loaded, frame, txn

from mule_detection.payments.currency import CurrencySettings
from mule_detection.source.prepare_transactions import (
    _flag_duplicates,
    _sort_by_time,
    prepare_transactions,
)

AUD = "Australian Dollar"
SETTINGS = CurrencySettings(base_currency="US Dollar", min_amount_paid=100.0, tolerance=0.005)

# --- P3 -------------------------------------------------------------------------------------------


def test_p3_only_the_later_copy_is_flagged():
    tx = frame(txn(), txn())
    assert _flag_duplicates(tx).tolist() == [False, True]

    tx = frame(txn(), txn(), txn())
    assert _flag_duplicates(tx).tolist() == [False, True, True]


def test_p3_rows_differing_in_one_column_are_not_duplicates():
    tx = frame(txn(), txn(amount_paid=500))
    assert _flag_duplicates(tx).tolist() == [False, False]


def test_p3_a_copy_is_flagged_even_with_rows_in_between():
    tx = frame(txn(), txn(amount_paid=500), txn())
    assert _flag_duplicates(tx).tolist() == [False, False, True]


def test_p3_transaction_id_is_ignored():
    tx = frame(txn(transaction_id=1), txn(transaction_id=2))
    assert _flag_duplicates(tx).tolist() == [False, True]


def test_p3_rows_differing_only_in_the_laundering_flag_are_duplicates():
    tx = frame(txn(is_laundering=0), txn(is_laundering=1))
    assert _flag_duplicates(tx).tolist() == [False, True]


def test_p3_columns_outside_the_source_columns_are_ignored():
    tx = frame(txn(extra="a"), txn(extra="b"))
    assert _flag_duplicates(tx).tolist() == [False, True]


# --- P7 -------------------------------------------------------------------------------------------


def test_p7_rows_are_sorted_by_timestamp():
    tx = frame(txn(transaction_id=0, timestamp=T2), txn(transaction_id=1, timestamp=T1))
    assert _sort_by_time(tx)["transaction_id"].tolist() == [1, 0]


def test_p7_ties_keep_transaction_id_order():
    tx = frame(txn(transaction_id=0, timestamp=T1), txn(transaction_id=1, timestamp=T1))
    assert _sort_by_time(tx)["transaction_id"].tolist() == [0, 1]


def test_p7_ties_are_sorted_by_transaction_id():
    tx = frame(txn(transaction_id=1, timestamp=T1), txn(transaction_id=0, timestamp=T1))
    assert _sort_by_time(tx)["transaction_id"].tolist() == [0, 1]


# --- pipeline -------------------------------------------------------------------------------------


def pipeline_input():
    """Three transactions in file order that the P7 sort reorders, with the accounts table.

    ID 0 is a US Dollar to Australian Dollar payment, so P6 has a rate to infer and check. IDs 1
    and 2 are identical self-transfers at an earlier time, so ID 2 is a duplicate. The sort
    moves ID 0 from first to last.
    """
    tx = frame(
        txn(transaction_id=0, timestamp=T2, amount_received=150.0, receiving_currency=AUD),
        txn(transaction_id=1, timestamp=T1, to_bank="10", to_account="A"),
        txn(transaction_id=2, timestamp=T1, to_bank="10", to_account="A"),
    )
    return as_loaded(tx), frame(acc())


def test_pipeline_keeps_each_row_with_its_own_flags_and_amounts():
    tx, accounts = pipeline_input()
    prepared = prepare_transactions(tx, accounts, currency=SETTINGS).transactions
    assert prepared["transaction_id"].tolist() == [1, 2, 0]  # the sort reordered the rows

    by_id = prepared.set_index("transaction_id")
    assert by_id.loc[1, ["is_self_transfer", "is_duplicate"]].tolist() == [True, False]
    assert by_id.loc[2, ["is_self_transfer", "is_duplicate"]].tolist() == [True, True]
    assert by_id.loc[0, ["is_self_transfer", "is_duplicate"]].tolist() == [False, False]
    assert by_id.loc[0, ["amount_paid_base", "amount_received_base"]].tolist() == pytest.approx(
        [100.0, 100.0]
    )


def test_pipeline_leaves_the_input_table_unchanged():
    tx, accounts = pipeline_input()
    before = tx.copy(deep=True)
    prepare_transactions(tx, accounts, currency=SETTINGS)
    pd.testing.assert_frame_equal(tx, before)


def test_pipeline_rejects_input_that_breaks_the_typed_transactions_contract():
    tx, accounts = pipeline_input()
    padded = tx.assign(from_bank="010")
    with pytest.raises(pa.errors.SchemaErrors, match="from_bank"):
        prepare_transactions(padded, accounts, currency=SETTINGS)
