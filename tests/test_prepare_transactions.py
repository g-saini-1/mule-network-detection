"""Tests for transaction preparation, using small hand-built transaction tables."""

import re

import pandas as pd
import pandera.pandas as pa
import pytest
from builders import T1, T2, acc, as_loaded, frame, prepared, raw_text, txn

from mule_detection.payments.currency import CurrencySettings
from mule_detection.source import load
from mule_detection.source.prepare_transactions import (
    _check_output,
    _flag_duplicates,
    _publish,
    _sort_by_time,
    load_prepared_transactions,
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


# --- P8 -------------------------------------------------------------------------------------------


def test_p8_pipeline_output_meets_its_contract_and_matches_the_raw_file():
    tx, accounts = pipeline_input()
    output = prepare_transactions(tx, accounts, currency=SETTINGS).transactions
    _check_output(output, tx[load.TRANSACTION_COLUMNS].astype(str))


def test_p8_output_that_breaks_its_contract_fails():
    with pytest.raises(pa.errors.SchemaErrors, match="is_laundering"):
        _check_output(prepared().assign(is_laundering=0), raw_text())


def test_p8_rows_are_matched_to_the_raw_file_by_transaction_id_not_position():
    # In time order, ID 1 comes first; its raw row is the second.
    output = prepared(
        txn(transaction_id=1, timestamp=T1, amount_paid=200.0),
        txn(transaction_id=0, timestamp=T2, amount_paid=100.0),
    )
    raw_rows = raw_text(txn(amount_paid=100.0), txn(amount_paid=200.0))
    _check_output(output, raw_rows)


@pytest.mark.parametrize(
    ("output", "raw_rows", "message"),
    [
        pytest.param(
            prepared(txn(transaction_id=0)),
            raw_text(),
            "found 1 row for 2 rows, e.g. no row at position 1",
            id="a raw row with no prepared row",
        ),
        pytest.param(
            prepared(),
            raw_text(txn()),
            "found 2 rows for 1 row, e.g. ID 1 at position 1",
            id="a prepared row with no raw row",
        ),
        pytest.param(
            prepared(txn(transaction_id=0), txn(transaction_id=2, timestamp=T2)),
            raw_text(),
            "found 2 rows for 2 rows, e.g. ID 2 at position 1",
            id="an ID outside the raw rows",
        ),
    ],
)
def test_p8_output_without_exactly_one_row_per_raw_row_fails(output, raw_rows, message):
    with pytest.raises(ValueError, match=re.escape(message)):
        _check_output(output, raw_rows)


@pytest.mark.parametrize(
    ("column", "raw_value"),
    [
        pytest.param("amount_paid", "101.0", id="amount paid"),
        pytest.param("payment_currency", "Euro", id="payment currency"),
        pytest.param("amount_received", "101.0", id="amount received"),
        pytest.param("receiving_currency", "Euro", id="receiving currency"),
    ],
)
def test_p8_a_value_different_from_the_raw_file_fails(column, raw_value):
    raw_rows = raw_text()
    raw_rows.loc[1, column] = raw_value
    message = f"P8: {column} differs from the raw file in 1 row, e.g. transaction 1"
    with pytest.raises(ValueError, match=re.escape(message)):
        _check_output(prepared(), raw_rows)


# --- saving and reading the prepared file ---------------------------------------------------------


def test_published_file_reads_back_unchanged_and_meets_the_contract(tmp_path):
    path = tmp_path / "transactions.parquet"
    _publish(prepared(), path)
    pd.testing.assert_frame_equal(load_prepared_transactions(path), prepared())


def test_a_failed_publish_leaves_the_previous_file_and_no_temporary_file(tmp_path):
    path = tmp_path / "transactions.parquet"
    _publish(prepared(), path)
    with pytest.raises(pa.errors.SchemaErrors, match="is_laundering"):
        _publish(prepared().assign(is_laundering=0), path)
    pd.testing.assert_frame_equal(load_prepared_transactions(path), prepared())
    assert sorted(p.name for p in tmp_path.iterdir()) == ["transactions.parquet"]


def test_reading_a_file_that_breaks_the_contract_fails(tmp_path):
    path = tmp_path / "transactions.parquet"
    prepared().assign(is_laundering=0).to_parquet(path, index=False)
    with pytest.raises(pa.errors.SchemaErrors, match="is_laundering"):
        load_prepared_transactions(path)
