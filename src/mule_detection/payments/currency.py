"""Convert amounts to one base currency with rates inferred from the data (P6).

The method is in `docs/currency_conversion_guide.md`; the reasoning is in `docs/decisions.md`.
Tests in `tests/test_currency.py` are named by rule number.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import pandas as pd

__all__ = [
    "CurrencySettings",
    "check_conversion",
    "conversion_gaps",
    "convert_amounts",
    "exchange_rates",
]


@dataclass(frozen=True, slots=True)
class CurrencySettings:
    """P6 settings, read once from the `transaction_preparation` section of `configs/data.yaml`.

    Attributes:
        base_currency: Currency every amount is converted to.
        min_amount_paid: Smallest amount paid used to infer rates and to check them.
        tolerance: Largest relative gap allowed between converted paid and received amounts.
    """

    base_currency: str
    min_amount_paid: float
    tolerance: float

    @classmethod
    def from_config(cls, section: Mapping[str, Any]) -> "CurrencySettings":
        """Build the settings from the config section, converting each value to its type."""
        return cls(
            base_currency=str(section["base_currency"]),
            min_amount_paid=float(section["rate_min_amount_paid"]),
            tolerance=float(section["conversion_tolerance"]),
        )


def exchange_rates(tx: pd.DataFrame, base_currency: str, min_amount_paid: float) -> pd.Series:
    """P6: units of each currency per one unit of `base_currency`.

    The median implied rate of each currency's cross-currency payments with the base currency,
    in either direction, using only payments with `amount_paid >= min_amount_paid`. Returns a
    float Series indexed by currency name, with the base currency at 1.0.
    """
    payment_currency_str = tx["payment_currency"].astype(str)
    receiving_currency_str = tx["receiving_currency"].astype(str)

    base_currency_pmt = (payment_currency_str == base_currency) & (
        receiving_currency_str != base_currency
    )

    base_currency_rpt = (payment_currency_str != base_currency) & (
        receiving_currency_str == base_currency
    )

    base_currency_txn = (base_currency_pmt | base_currency_rpt) & (
        tx["amount_paid"] >= min_amount_paid
    )

    exchg_rate_rpt = (
        tx["amount_received"] / tx["amount_paid"]
    )  # includes rate where payment is made in base currency and all other rates

    exch_rate_rpt_pmt = exchg_rate_rpt.where(
        base_currency_pmt, other=tx["amount_paid"] / tx["amount_received"]
    )  # includes rates where txn is done with mixed currency
    exch_rate_useable = exch_rate_rpt_pmt[
        base_currency_txn
    ]  # rates for all txns where payment is made or received in base currency

    # Other currency in each payment
    other_currency = receiving_currency_str.where(base_currency_pmt, payment_currency_str)[
        base_currency_txn
    ]

    rates = exch_rate_useable.groupby(other_currency).median()
    rates[base_currency] = 1.0
    return rates.sort_index().rename_axis("currency").rename("rate")


def convert_amounts(tx: pd.DataFrame, rates: pd.Series) -> pd.DataFrame:
    """P6: `amount_paid_usd` and `amount_received_usd`, aligned to `tx.index`.

    Each amount is divided by its currency's rate from `exchange_rates`. Fails if a currency in
    `tx` has no rate.
    """
    pmt_rate = tx["payment_currency"].astype(str).map(rates)
    rpt_rate = tx["receiving_currency"].astype(str).map(rates)
    missing = set(tx.loc[pmt_rate.isna(), "payment_currency"].astype(str)) | set(
        tx.loc[rpt_rate.isna(), "receiving_currency"].astype(str)
    )
    if missing:
        raise ValueError(f"no exchange rate for currencies: {sorted(missing)}")
    return pd.DataFrame(
        {
            "amount_paid_usd": tx["amount_paid"] / pmt_rate,
            "amount_received_usd": tx["amount_received"] / rpt_rate,
        },
        index=tx.index,
    )


def conversion_gaps(prepared: pd.DataFrame, min_amount_paid: float) -> pd.Series:
    """P6: relative gap between converted paid and received amounts.

    Covers cross-currency payments with `amount_paid >= min_amount_paid` only. The gap is the
    absolute difference between the two converted amounts, as a share of the converted amount
    paid.
    """
    cross_currency = prepared["payment_currency"].astype(str) != prepared[
        "receiving_currency"
    ].astype(str)
    covered = cross_currency & (prepared["amount_paid"] >= min_amount_paid)
    paid = prepared.loc[covered, "amount_paid_usd"]
    received = prepared.loc[covered, "amount_received_usd"]
    return ((paid - received).abs() / paid).rename("conversion_gap")


def check_conversion(prepared: pd.DataFrame, min_amount_paid: float, tolerance: float) -> None:
    """P6: fail if any converted paid and received amounts differ by more than `tolerance`."""
    gaps = conversion_gaps(prepared, min_amount_paid)
    if (gaps > tolerance).any():
        raise ValueError(
            f"{int((gaps > tolerance).sum())} payments convert with a gap above {tolerance}; "
            f"largest {gaps.max():.6f}"
        )
