"""Tests for the typed transactions contract, using small hand-built transaction tables."""

import pytest
from builders import GOOD_ROW, as_loaded, frame, raw_transactions_file, txn
from contract_checks import broken_rules

from mule_detection.source import load
from mule_detection.source.typed_transactions_contract import TypedTransactionsContract as Typed


def typed(**changes):
    """Two valid typed transactions, the first with the given columns changed."""
    return as_loaded(frame(txn(transaction_id=0, **changes), txn(transaction_id=1)))


def test_p2_valid_typed_transactions_meet_the_contract():
    assert broken_rules(Typed, typed()) == set()


def test_p2_the_loader_output_meets_the_contract(tmp_path):
    tx = load.load_transactions(raw_transactions_file(tmp_path, GOOD_ROW))
    assert broken_rules(Typed, tx) == set()


@pytest.mark.parametrize(
    ("tx", "expected"),
    [
        pytest.param(
            typed().drop(columns="payment_format"),
            {("payment_format", "column_in_dataframe")},
            id="missing column",
        ),
        pytest.param(typed().assign(extra=1), {("extra", "column_in_schema")}, id="extra column"),
        pytest.param(
            typed()[["timestamp", "transaction_id", *load.TRANSACTION_COLUMNS[1:]]],
            {("timestamp", "column_ordered"), ("transaction_id", "column_ordered")},
            id="columns out of order",
        ),
        pytest.param(
            typed().astype({"amount_paid": "float32"}), {("amount_paid", "dtype")}, id="wrong type"
        ),
        pytest.param(
            typed().astype({"timestamp": str}), {("timestamp", "dtype")}, id="timestamp as text"
        ),
        pytest.param(
            typed().astype({"payment_currency": str}),
            {("payment_currency", "dtype")},
            id="currency not a category",
        ),
        pytest.param(
            typed(from_account=None), {("from_account", "not_nullable")}, id="empty value"
        ),
        pytest.param(
            typed(from_account=""), {("from_account", "str_length")}, id="empty account text"
        ),
        pytest.param(
            typed(from_bank="010"), {("from_bank", "str_matches")}, id="zero-padded bank ID"
        ),
        pytest.param(
            typed(from_bank="10\n"), {("from_bank", "str_matches")}, id="bank ID with newline"
        ),
        pytest.param(
            typed(amount_paid=0.0), {("amount_paid", "greater_than")}, id="amount of zero"
        ),
        pytest.param(
            typed(amount_paid=float("inf")),
            {("amount_paid", "amounts must be finite")},
            id="infinite amount",
        ),
        pytest.param(
            typed(is_laundering=2), {("is_laundering", "isin")}, id="laundering flag not 0 or 1"
        ),
        pytest.param(
            as_loaded(frame(txn(transaction_id=-1), txn(transaction_id=1))),
            {("transaction_id", "greater_than_or_equal_to")},
            id="negative transaction ID",
        ),
        pytest.param(
            as_loaded(frame(txn(transaction_id=0), txn(transaction_id=0))),
            {("transaction_id", "field_uniqueness")},
            id="repeated transaction ID",
        ),
    ],
)
def test_p2_typed_transactions_that_break_the_contract_are_rejected(tx, expected):
    assert broken_rules(Typed, tx) == expected
