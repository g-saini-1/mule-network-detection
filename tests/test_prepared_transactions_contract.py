"""Tests for the prepared transactions contract, using small hand-built transaction tables."""

import pytest
from builders import T1, T2, prepared, txn
from contract_checks import broken_rules

from mule_detection.source.prepared_transactions_contract import (
    PreparedTransactionsContract as Prepared,
)


def test_p8_valid_prepared_transactions_in_the_guide_column_order_meet_the_contract():
    assert broken_rules(Prepared, prepared()) == set()


@pytest.mark.parametrize(
    ("tx", "expected"),
    [
        pytest.param(
            prepared().drop(columns="amount_paid_base"),
            {("amount_paid_base", "column_in_dataframe")},
            id="missing column",
        ),
        pytest.param(
            prepared().assign(is_laundering=0),
            {("is_laundering", "column_in_schema")},
            id="extra column",
        ),
        pytest.param(
            prepared().astype({"is_duplicate": int}), {("is_duplicate", "dtype")}, id="wrong type"
        ),
        pytest.param(
            prepared().assign(amount_received_base=float("nan")),
            {("amount_received_base", "not_nullable")},
            id="empty value",
        ),
        pytest.param(
            prepared(txn(transaction_id=0, to_bank="020")),
            {("to_bank", "str_matches")},
            id="zero-padded bank ID",
        ),
        pytest.param(
            prepared().assign(amount_paid_base=0.0),
            {("amount_paid_base", "greater_than")},
            id="amount of zero",
        ),
        pytest.param(
            prepared().assign(amount_received_base=float("inf")),
            {("amount_received_base", "amounts must be finite")},
            id="infinite amount",
        ),
        pytest.param(
            prepared(txn(transaction_id=0, timestamp=T1), txn(transaction_id=0, timestamp=T2)),
            {("transaction_id", "field_uniqueness")},
            id="repeated transaction ID",
        ),
    ],
)
def test_p8_prepared_transactions_that_break_the_contract_are_rejected(tx, expected):
    assert broken_rules(Prepared, tx) == expected


TIME_ORDER = "rows are not sorted by timestamp, with ties by transaction_id (P7)"


@pytest.mark.parametrize(
    "rows",
    [
        pytest.param(
            (txn(transaction_id=0, timestamp=T2), txn(transaction_id=1, timestamp=T1)),
            id="later time first",
        ),
        pytest.param(
            (txn(transaction_id=1, timestamp=T1), txn(transaction_id=0, timestamp=T1)),
            id="tie with higher ID first",
        ),
    ],
)
def test_p7_prepared_transactions_out_of_time_order_are_rejected(rows):
    assert broken_rules(Prepared, prepared(*rows)) == {("PreparedTransactionsContract", TIME_ORDER)}
