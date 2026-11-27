"""Tests for transaction preparation, using small hand-built transaction tables."""

import pandas as pd
import pytest

from mule_detection.data.prepare_transactions import (
    check_conversion,
    conversion_gaps,
    convert_amounts,
    exchange_rates,
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


# --- P6 ----------------------------------------------------------------------------------
AUD = "Australian Dollar"


def usd_to_aud(paid, received):
    """A payment made in US Dollar and received in Australian Dollar."""
    return txn(
        amount_paid=paid,
        payment_currency="US Dollar",
        amount_received=received,
        receiving_currency=AUD,
    )


def test_p6_rate_is_units_received_per_base_unit_paid():
    rates = exchange_rates(frame(usd_to_aud(100.0, 150.0)), "US Dollar", 100)
    assert rates[AUD] == 1.5


def test_p6_rate_is_inverted_when_the_base_currency_is_received():
    tx = frame(
        txn(
            amount_paid=300.0,
            payment_currency=AUD,
            amount_received=200.0,
            receiving_currency="US Dollar",
        )
    )
    assert exchange_rates(tx, "US Dollar", 100)[AUD] == 1.5


def test_p6_rate_is_the_median_not_the_mean():
    tx = frame(usd_to_aud(100.0, 140.0), usd_to_aud(100.0, 150.0), usd_to_aud(100.0, 990.0))
    assert exchange_rates(tx, "US Dollar", 100)[AUD] == 1.5


def test_p6_base_currency_rate_is_one():
    rates = exchange_rates(frame(usd_to_aud(100.0, 150.0)), "US Dollar", 100)
    assert rates["US Dollar"] == 1.0


def test_p6_small_same_currency_and_non_base_payments_are_ignored():
    tx = frame(
        usd_to_aud(100.0, 150.0),
        usd_to_aud(99.0, 990.0),  # amount paid under the minimum
        txn(),  # US Dollar to US Dollar
        txn(
            amount_paid=100.0,
            payment_currency="Euro",
            amount_received=500.0,
            receiving_currency=AUD,
        ),  # no US Dollar side
    )
    rates = exchange_rates(tx, "US Dollar", 100)
    assert rates.to_dict() == {AUD: 1.5, "US Dollar": 1.0}


RATES = pd.Series({AUD: 1.5, "US Dollar": 1.0})


def test_p6_amounts_are_divided_by_their_currency_rate():
    converted = convert_amounts(frame(usd_to_aud(100.0, 150.0)), RATES)
    assert converted["amount_paid_usd"].tolist() == [100.0]
    assert converted["amount_received_usd"].tolist() == [100.0]


def test_p6_converted_amounts_keep_the_row_labels_of_tx():
    tx = frame(usd_to_aud(100.0, 150.0)).set_axis([99])
    assert convert_amounts(tx, RATES).index.tolist() == [99]


def test_p6_a_currency_without_a_rate_fails():
    tx = frame(txn(payment_currency="Yen", receiving_currency="Yen"))
    with pytest.raises(ValueError, match="Yen"):
        convert_amounts(tx, RATES)


def prepared(*rows):
    """Transactions with converted amounts, as `check_conversion` sees them."""
    tx = frame(*rows)
    return tx.join(convert_amounts(tx, RATES))


def test_p6_gap_is_the_difference_as_a_share_of_the_amount_paid():
    gaps = conversion_gaps(prepared(usd_to_aud(100.0, 153.0)), 100)
    assert gaps.tolist() == pytest.approx([0.02])


def test_p6_gaps_cover_only_cross_currency_payments_of_the_minimum_or_more():
    gaps = conversion_gaps(
        prepared(usd_to_aud(100.0, 150.0), usd_to_aud(99.0, 150.0), txn(amount_received=50.0)),
        100,
    )
    assert gaps.index.tolist() == [0]


def test_p6_check_fails_when_a_gap_is_above_the_tolerance():
    with pytest.raises(ValueError, match="1 payments"):
        check_conversion(prepared(usd_to_aud(100.0, 153.0)), 100, 0.005)


def test_p6_check_passes_when_every_gap_is_within_the_tolerance():
    check_conversion(prepared(usd_to_aud(100.0, 150.3)), 100, 0.005)


# --- P7----------------------------------------------------------------------------------
def test_p7_out_of_time_order():
    tx = frame(txn(transaction_id=0, timestamp=T2), txn(transaction_id=1, timestamp=T1))
    assert sort_by_time(tx)["transaction_id"].tolist() == [1, 0]


def test_p7_ties_already_in_time_order():
    tx = frame(txn(transaction_id=0, timestamp=T1), txn(transaction_id=1, timestamp=T1))
    assert sort_by_time(tx)["transaction_id"].tolist() == [0, 1]


def test_p7_ties_out_of_time_order():
    tx = frame(txn(transaction_id=1, timestamp=T1), txn(transaction_id=0, timestamp=T1))
    assert sort_by_time(tx)["transaction_id"].tolist() == [0, 1]
