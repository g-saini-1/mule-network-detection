"""Tests for currency conversion, using small hand-built transaction tables."""

import pandas as pd
import pytest
from builders import as_loaded, frame, txn

from mule_detection.payments.currency import (
    CurrencySettings,
    check_conversion,
    conversion_gaps,
    convert_amounts,
    exchange_rates,
)

AUD = "Australian Dollar"
SETTINGS = CurrencySettings(base_currency="US Dollar", min_amount_paid=100.0, tolerance=0.005)


def usd_to_aud(paid, received):
    """A payment made in US Dollar and received in Australian Dollar."""
    return txn(
        amount_paid=paid,
        payment_currency="US Dollar",
        amount_received=received,
        receiving_currency=AUD,
    )


# --- P6: settings ---------------------------------------------------------------------------------


def test_p6_settings_are_read_from_the_config_section_with_their_types():
    section = {
        "base_currency": "US Dollar",
        "rate_min_amount_paid": 100,
        "conversion_tolerance": "0.005",
    }
    assert CurrencySettings.from_config(section) == CurrencySettings("US Dollar", 100.0, 0.005)


def test_p6_a_base_currency_other_than_us_dollar_fails():
    with pytest.raises(ValueError, match="must be US Dollar"):
        CurrencySettings(base_currency="Euro", min_amount_paid=100.0, tolerance=0.005)


@pytest.mark.parametrize("min_amount_paid", [0.0, -1.0, float("nan")])
def test_p6_a_minimum_amount_not_above_zero_fails(min_amount_paid):
    with pytest.raises(ValueError, match="minimum amount paid must be above 0"):
        CurrencySettings(
            base_currency="US Dollar", min_amount_paid=min_amount_paid, tolerance=0.005
        )


@pytest.mark.parametrize("tolerance", [-0.001, float("nan"), float("inf")])
def test_p6_a_tolerance_that_is_not_a_number_of_zero_or_more_fails(tolerance):
    with pytest.raises(ValueError, match="tolerance must be a number of 0 or more"):
        CurrencySettings(base_currency="US Dollar", min_amount_paid=100.0, tolerance=tolerance)


# --- P6: rates ------------------------------------------------------------------------------------


def test_p6_rate_is_units_received_per_base_unit_paid():
    rates = exchange_rates(frame(usd_to_aud(100.0, 150.0)), SETTINGS)
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
    assert exchange_rates(tx, SETTINGS)[AUD] == 1.5


def test_p6_rate_is_the_median_not_the_mean():
    tx = frame(usd_to_aud(100.0, 140.0), usd_to_aud(100.0, 150.0), usd_to_aud(100.0, 990.0))
    assert exchange_rates(tx, SETTINGS)[AUD] == 1.5


def test_p6_base_currency_rate_is_one():
    rates = exchange_rates(frame(usd_to_aud(100.0, 150.0)), SETTINGS)
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
    rates = exchange_rates(tx, SETTINGS)
    assert rates.to_dict() == {AUD: 1.5, "US Dollar": 1.0}


def test_p6_payments_in_both_directions_feed_one_median():
    tx = frame(
        usd_to_aud(100.0, 140.0),  # rate 1.4
        txn(
            amount_paid=160.0,
            payment_currency=AUD,
            amount_received=100.0,
            receiving_currency="US Dollar",
        ),  # rate 1.6
        usd_to_aud(100.0, 150.0),  # rate 1.5
    )
    assert exchange_rates(tx, SETTINGS)[AUD] == pytest.approx(1.5)


# --- P6: conversion -------------------------------------------------------------------------------


RATES = pd.Series({AUD: 1.5, "US Dollar": 1.0})


def test_p6_amounts_are_divided_by_their_currency_rate():
    converted = convert_amounts(frame(usd_to_aud(100.0, 150.0)), RATES)
    assert converted["amount_paid_base"].tolist() == [100.0]
    assert converted["amount_received_base"].tolist() == [100.0]


def test_p6_converted_amounts_keep_the_row_labels_of_tx():
    tx = frame(usd_to_aud(100.0, 150.0)).set_axis([99])
    assert convert_amounts(tx, RATES).index.tolist() == [99]


def test_p6_a_currency_without_a_rate_fails():
    tx = frame(txn(payment_currency="Yen", receiving_currency="Yen"))
    with pytest.raises(ValueError, match="Yen"):
        convert_amounts(tx, RATES)


def test_p6_a_payment_between_two_non_base_currencies_converts_each_side_by_its_own_rate():
    rates = pd.Series({AUD: 1.5, "Euro": 0.85, "US Dollar": 1.0})
    tx = frame(
        txn(
            amount_paid=85.0, payment_currency="Euro", amount_received=150.0, receiving_currency=AUD
        )
    )
    converted = convert_amounts(tx, rates)
    assert converted["amount_paid_base"].tolist() == pytest.approx([100.0])
    assert converted["amount_received_base"].tolist() == pytest.approx([100.0])


def test_p6_rates_and_conversion_work_on_currencies_typed_as_categories():
    tx = frame(
        usd_to_aud(100.0, 150.0),
        txn(
            amount_paid=300.0,
            payment_currency=AUD,
            amount_received=200.0,
            receiving_currency="US Dollar",
        ),
    )
    rates = exchange_rates(as_loaded(tx), SETTINGS)
    assert rates.to_dict() == exchange_rates(tx, SETTINGS).to_dict()
    assert convert_amounts(as_loaded(tx), rates).equals(convert_amounts(tx, rates))


# --- P6: conversion consistency check -------------------------------------------------------------


def prepared(*rows):
    """Transactions with converted amounts, as `check_conversion` sees them."""
    tx = frame(*rows)
    return tx.join(convert_amounts(tx, RATES))


def test_p6_gap_is_the_difference_as_a_share_of_the_amount_paid():
    gaps = conversion_gaps(prepared(usd_to_aud(100.0, 153.0)), SETTINGS)
    assert gaps.tolist() == pytest.approx([0.02])


def test_p6_gaps_cover_only_cross_currency_payments_of_the_minimum_or_more():
    gaps = conversion_gaps(
        prepared(usd_to_aud(100.0, 150.0), usd_to_aud(99.0, 150.0), txn(amount_received=50.0)),
        SETTINGS,
    )
    assert gaps.index.tolist() == [0]


def test_p6_check_fails_when_a_gap_is_above_the_tolerance():
    with pytest.raises(ValueError, match="1 payments"):
        check_conversion(prepared(usd_to_aud(100.0, 153.0)), SETTINGS)


def test_p6_check_passes_when_every_gap_is_within_the_tolerance():
    check_conversion(prepared(usd_to_aud(100.0, 150.3)), SETTINGS)


def test_p6_check_fails_when_no_payment_is_covered():
    with pytest.raises(ValueError, match="no cross-currency payment"):
        check_conversion(prepared(txn(), usd_to_aud(99.0, 150.0)), SETTINGS)


def test_p6_check_fails_when_a_gap_cannot_be_computed():
    with pytest.raises(ValueError, match="cannot be computed"):
        check_conversion(prepared(usd_to_aud(100.0, float("nan"))), SETTINGS)
