"""Tests for currency conversion, using small hand-built transaction tables."""

import pandas as pd
import pytest
from builders import frame, txn

from mule_detection.payments.currency import (
    CurrencySettings,
    check_conversion,
    conversion_gaps,
    convert_amounts,
    exchange_rates,
)

AUD = "Australian Dollar"


def usd_to_aud(paid, received):
    """A payment made in US Dollar and received in Australian Dollar."""
    return txn(
        amount_paid=paid,
        payment_currency="US Dollar",
        amount_received=received,
        receiving_currency=AUD,
    )


# --- P6: settings ------------------------------------------------------------------------
def test_p6_settings_are_read_from_the_config_section_with_their_types():
    section = {
        "base_currency": "US Dollar",
        "rate_min_amount_paid": 100,
        "conversion_tolerance": "0.005",
    }
    assert CurrencySettings.from_config(section) == CurrencySettings("US Dollar", 100.0, 0.005)


# --- P6: rates ---------------------------------------------------------------------------
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


# --- P6: conversion ----------------------------------------------------------------------
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


# --- P6: conversion consistency check ----------------------------------------------------
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
