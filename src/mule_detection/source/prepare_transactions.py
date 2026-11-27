"""Prepare the raw transactions for detection rules.

The rules are in `docs/transaction_preparation_guide.md`; the reasoning is in
`docs/decisions.md`. Tests in `tests/test_prepare_transactions.py` are named by rule number.

- P1 and P2: `load.load_transactions` assigns `transaction_id` and types the columns.
- P3: later copies of an earlier transaction are flagged `is_duplicate`.
- P4 and P5: transfer flags, from `mule_detection.payments.transfers`.
- P6: amounts in the base currency, from `mule_detection.payments.currency`.
- P7: transactions are sorted by timestamp, ties in `transaction_id` order.
- P8: the output is checked before it is written.

The output holds no ground truth (T1 to T3, `docs/transaction_labelling_guide.md`). The rule
functions are pure; files and config are read only in `main()`.
Run with `python -m mule_detection.source.prepare_transactions`.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from mule_detection.payments.currency import (
    CurrencySettings,
    check_conversion,
    conversion_gaps,
    convert_amounts,
    exchange_rates,
)
from mule_detection.payments.transfers import flag_own_account_transfers, flag_self_transfers
from mule_detection.source import load
from mule_detection.utils.config import load_config, repo_path

__all__ = [
    "PREPARED_COLUMNS",
    "PreparedTransactions",
    "load_prepared_transactions",
    "main",
    "prepare_transactions",
]

logger = logging.getLogger(__name__)

PREPARED_COLUMNS = [
    "transaction_id",
    "timestamp",
    "from_bank",
    "from_account",
    "to_bank",
    "to_account",
    "amount_paid",
    "payment_currency",
    "amount_received",
    "receiving_currency",
    "payment_format",
    "is_duplicate",
    "is_self_transfer",
    "is_own_account_transfer",
    "amount_paid_usd",
    "amount_received_usd",
]


@dataclass(frozen=True, slots=True, eq=False)
class PreparedTransactions:
    """Result of `prepare_transactions` (P3 to P7).

    Not compared with `==`, because comparing DataFrames that way is ambiguous.

    Attributes:
        transactions: The prepared transactions, with the columns in `PREPARED_COLUMNS`.
        rates: The P6 rates used, in units per one unit of the base currency.
    """

    transactions: pd.DataFrame
    rates: pd.Series


# --- P3: duplicates -------------------------------------------------------------------------------

_DUPLICATE_COLUMNS = [c for c in load.TRANSACTION_COLUMNS if c != "is_laundering"]


def _flag_duplicates(tx: pd.DataFrame) -> pd.Series:
    """P3: True for a row whose source columns, laundering flag aside, equal an earlier row's.

    The first copy is False. Returns a bool Series aligned to `tx.index`.
    """
    return tx[_DUPLICATE_COLUMNS].duplicated().rename("is_duplicate")


# --- P7: time order -------------------------------------------------------------------------------


def _sort_by_time(tx: pd.DataFrame) -> pd.DataFrame:
    """P7: `tx` sorted by `timestamp`, with ties in `transaction_id` order."""
    return tx.sort_values(by=["timestamp", "transaction_id"], ascending=True)


# --- P8: output checks ----------------------------------------------------------------------------


def _check_output(prepared: pd.DataFrame, raw: pd.DataFrame) -> None:
    """P8: fail unless `prepared` matches its schema and reconciles with `raw`.

    `raw` is `load.load_raw_transactions()`, all text. Checks row count and total amounts paid
    and received per currency, within floating-point rounding.
    """
    raise NotImplementedError("P8 is not written yet")


# --- pipeline -------------------------------------------------------------------------------------


def prepare_transactions(
    tx: pd.DataFrame, accounts: pd.DataFrame, *, currency: CurrencySettings
) -> PreparedTransactions:
    """Apply P3 to P7 to transactions from `load.load_transactions` (P1, P2)."""
    prepared = tx.copy()
    logger.info("P3 to P5: flagging duplicates, self-transfers and own-account transfers")
    prepared["is_duplicate"] = _flag_duplicates(prepared)
    prepared["is_self_transfer"] = flag_self_transfers(prepared)
    prepared["is_own_account_transfer"] = flag_own_account_transfers(prepared, accounts)
    logger.info("P6: converting amounts to %s", currency.base_currency)
    rates = exchange_rates(prepared, currency)
    prepared = prepared.join(convert_amounts(prepared, rates))
    check_conversion(prepared, currency)
    logger.info("P7: sorting by time")
    prepared = _sort_by_time(prepared)
    return PreparedTransactions(prepared[PREPARED_COLUMNS].reset_index(drop=True), rates)


def _run_summary(prepared: pd.DataFrame, rates: pd.Series, currency: CurrencySettings) -> str:
    """Figures from a run, printed by `main()` for the Stage 2 report."""
    self_transfers = prepared[prepared["is_self_transfer"]]
    gaps = conversion_gaps(prepared, currency)
    return "\n".join(
        [
            f"rows: {len(prepared):,}",
            f"P3 duplicates flagged: {int(prepared['is_duplicate'].sum()):,}",
            f"P4 self-transfers flagged: {len(self_transfers):,}, by payment format:",
            self_transfers["payment_format"].value_counts().to_string(),
            f"P5 own-account transfers flagged: {int(prepared['is_own_account_transfer'].sum()):,}",
            "P6 units per base currency:",
            rates.sort_index().to_string(),
            f"P6 largest conversion gap ({len(gaps):,} payments): {gaps.max():.6f}",
        ]
    )


def _prepared_path() -> Path:
    """Absolute path of the prepared transactions file."""
    return repo_path(load_config("data")["paths"]["prepared_transactions"])


def load_prepared_transactions(path: Path | None = None) -> pd.DataFrame:
    """Read the prepared transactions, checking every expected column is present.

    Returns the transactions only, not a `PreparedTransactions`: the P6 rates are not saved.
    """
    prepared = pd.read_parquet(path or _prepared_path())
    missing = set(PREPARED_COLUMNS) - set(prepared.columns)
    if missing:
        raise ValueError(f"prepared transactions file is missing columns: {sorted(missing)}")
    return prepared


def main() -> None:
    """Command-line entry point: prepare, check, save and summarise the transactions.

    The one place errors are handled: a failure in configuration, preparation or the P8 check
    is logged once and ends the run with exit code 1, before anything is saved.
    """
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s: %(message)s"
    )
    try:
        currency = CurrencySettings.from_config(load_config("data")["transaction_preparation"])
        result = prepare_transactions(
            load.load_transactions(), load.load_accounts(), currency=currency
        )
        logger.info("P8: checking the output")
        _check_output(result.transactions, load.load_raw_transactions())
    except Exception:
        logger.exception("transaction preparation failed")
        raise SystemExit(1) from None

    # path = _prepared_path()
    # path.parent.mkdir(parents=True, exist_ok=True)
    # result.transactions.to_parquet(path, index=False)
    print(_run_summary(result.transactions, result.rates, currency))
    # print(f"saved to {path}")


if __name__ == "__main__":
    main()
