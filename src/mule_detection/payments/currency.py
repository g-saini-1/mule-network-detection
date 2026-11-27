"""Convert amounts to one base currency with rates inferred from the data (P6).

The method is in `docs/currency_conversion_guide.md`; the reasoning is in `docs/decisions.md`.
Tests in `tests/test_currency.py` are named by rule number.
"""

import math
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

# The converted columns are named for this currency (`amount_paid_usd`, `amount_received_usd`).
_SUPPORTED_BASE_CURRENCY = "US Dollar"


@dataclass(frozen=True, slots=True)
class CurrencySettings:
    """P6 settings, read once from the `transaction_preparation` section of `configs/data.yaml`.

    Fails if the base currency is not US Dollar, the currency the converted columns are named
    for, if the minimum amount is not above 0, or if the tolerance is not a number of 0 or more.

    Attributes:
        base_currency: Currency every amount is converted to.
        min_amount_paid: Smallest amount paid used to infer rates and to check them.
        tolerance: Largest relative gap allowed between converted paid and received amounts.
    """

    base_currency: str
    min_amount_paid: float
    tolerance: float

    def __post_init__(self) -> None:
        """Fail on settings that would convert wrongly or let the checks pass silently."""
        if self.base_currency != _SUPPORTED_BASE_CURRENCY:
            raise ValueError(
                f"P6: base currency must be {_SUPPORTED_BASE_CURRENCY}, not {self.base_currency}; "
                "the converted columns are named for it"
            )
        if not self.min_amount_paid > 0:
            raise ValueError(f"P6: minimum amount paid must be above 0, not {self.min_amount_paid}")
        if not (math.isfinite(self.tolerance) and self.tolerance >= 0):
            raise ValueError(f"P6: tolerance must be a number of 0 or more, not {self.tolerance}")

    @classmethod
    def from_config(cls, section: Mapping[str, Any]) -> "CurrencySettings":
        """Build the settings from the config section, converting each value to its type."""
        return cls(
            base_currency=str(section["base_currency"]),
            min_amount_paid=float(section["rate_min_amount_paid"]),
            tolerance=float(section["conversion_tolerance"]),
        )


def exchange_rates(tx: pd.DataFrame, currency: CurrencySettings) -> pd.Series:
    """P6: units of each currency per one unit of the base currency.

    The median implied rate of each currency's cross-currency payments with the base currency,
    in either direction, using only payments with an amount paid of at least
    `currency.min_amount_paid`. Returns a float Series indexed by currency name, with the base
    currency at 1.0.
    """
    base = currency.base_currency
    paid_in = tx["payment_currency"].astype(str)
    received_in = tx["receiving_currency"].astype(str)

    base_paid = (paid_in == base) & (received_in != base)
    base_received = (paid_in != base) & (received_in == base)
    usable = (base_paid | base_received) & (tx["amount_paid"] >= currency.min_amount_paid)

    implied_rate = (tx["amount_received"] / tx["amount_paid"]).where(
        base_paid, other=tx["amount_paid"] / tx["amount_received"]
    )
    other_currency = received_in.where(base_paid, other=paid_in)

    rates = implied_rate[usable].groupby(other_currency[usable]).median()
    rates[base] = 1.0
    return rates.sort_index().rename_axis("currency").rename("rate")


def convert_amounts(tx: pd.DataFrame, rates: pd.Series) -> pd.DataFrame:
    """P6: `amount_paid_usd` and `amount_received_usd`, aligned to `tx.index`.

    Each amount is divided by its currency's rate from `exchange_rates`. Fails if a currency in
    `tx` has no rate.
    """
    paid_in = tx["payment_currency"].astype(str)
    received_in = tx["receiving_currency"].astype(str)
    paid_rate = paid_in.map(rates)
    received_rate = received_in.map(rates)
    missing = set(paid_in[paid_rate.isna()]) | set(received_in[received_rate.isna()])
    if missing:
        raise ValueError(f"P6: no exchange rate for currencies: {sorted(missing)}")
    return pd.DataFrame(
        {
            "amount_paid_usd": tx["amount_paid"] / paid_rate,
            "amount_received_usd": tx["amount_received"] / received_rate,
        },
        index=tx.index,
    )


def conversion_gaps(prepared: pd.DataFrame, currency: CurrencySettings) -> pd.Series:
    """P6: relative gap between converted paid and received amounts.

    Covers cross-currency payments with an amount paid of at least `currency.min_amount_paid`
    only. The gap is the absolute difference between the two converted amounts, as a share of
    the converted amount paid.
    """
    cross_currency = prepared["payment_currency"].astype(str) != prepared[
        "receiving_currency"
    ].astype(str)
    covered = cross_currency & (prepared["amount_paid"] >= currency.min_amount_paid)
    paid = prepared.loc[covered, "amount_paid_usd"]
    received = prepared.loc[covered, "amount_received_usd"]
    return ((paid - received).abs() / paid).rename("conversion_gap")


def check_conversion(prepared: pd.DataFrame, currency: CurrencySettings) -> None:
    """P6: fail unless every gap between converted paid and received amounts is within tolerance.

    Also fails if no payment is covered, since the rates would then go unchecked, and if any gap
    cannot be computed, e.g. from a missing amount received.
    """
    gaps = conversion_gaps(prepared, currency)
    if gaps.empty:
        raise ValueError(
            "P6: no cross-currency payment with an amount paid of at least "
            f"{currency.min_amount_paid} to check the rates against"
        )
    if gaps.isna().any():
        raise ValueError(
            f"P6: {int(gaps.isna().sum())} payments have a gap that cannot be computed"
        )
    above = gaps > currency.tolerance
    if above.any():
        raise ValueError(
            f"P6: {int(above.sum())} payments convert with a gap above {currency.tolerance}; "
            f"largest {gaps.max():.6f}"
        )
