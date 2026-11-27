"""Prepare the raw transactions for detection rules.

The rules are in `docs/transaction_preparation_guide.md`; the reasoning is in
`docs/decisions.md`. Tests in `tests/test_prepare_transactions.py` are named by rule number.

- P1 and P2: `load.load_transactions` assigns `transaction_id` and types the columns.
- P3: later copies of an earlier transaction are flagged `is_duplicate`.
- P4 and P5: transfer flags, from `mule_detection.payments.transfers`.
- P6: amounts in the base currency, from `mule_detection.payments.currency`.
- P7: transactions are sorted by timestamp, ties in `transaction_id` order.
- P8: laundering payments in the patterns file get their `scheme_id` and `typology`.
- P9: the output is checked before it is written.

The rule functions are pure; files and config are read only in `main()`.
Run with `python -m mule_detection.source.prepare_transactions`.
"""

import logging
from pathlib import Path
from typing import NamedTuple

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
    "is_laundering",
    "is_duplicate",
    "is_self_transfer",
    "is_own_account_transfer",
    "amount_paid_usd",
    "amount_received_usd",
    "scheme_id",
    "typology",
]
# Read only by the evaluation harness, never by the rules engine.
EVALUATION_ONLY_COLUMNS = ["is_laundering", "scheme_id", "typology"]


class Prepared(NamedTuple):
    """Result of `prepare_transactions`: the prepared transactions and the P6 rates used."""

    transactions: pd.DataFrame
    rates: pd.Series


# --- P3: duplicates ------------------------------------------------------------------


def flag_duplicates(tx: pd.DataFrame) -> pd.Series:
    """P3: True for a row whose every column apart from `transaction_id` equals an earlier row.

    The first copy is False. Returns a bool Series aligned to `tx.index`.
    """
    return tx.drop(columns=["transaction_id"], errors="ignore").duplicated().rename("is_duplicate")


# --- P7: time order ------------------------------------------------------------------


def sort_by_time(tx: pd.DataFrame) -> pd.DataFrame:
    """P7: `tx` sorted by `timestamp`, with ties in `transaction_id` order."""
    return tx.sort_values(by=["timestamp", "transaction_id"], ascending=True)


# --- P8: scheme tags -----------------------------------------------------------------


def parse_patterns(lines: list[str]) -> pd.DataFrame:
    """P8: one row per transaction line in the patterns file.

    Columns: `raw_line` (the line's text), `scheme_id` (block position, from 1) and
    `typology` (the name on the block's BEGIN line).
    """
    raise NotImplementedError("P8 parsing is not written yet")


def tag_schemes(tx: pd.DataFrame, raw_lines: pd.Series, patterns: pd.DataFrame) -> pd.DataFrame:
    """P8: `scheme_id` and `typology` for each row of `tx`, empty where in no scheme.

    `raw_lines` holds each transaction's raw text, indexed by `transaction_id`. Fails if a
    pattern row matches no transaction, more than one, or a non-laundering payment.
    """
    raise NotImplementedError("P8 tagging is not written yet")


# --- P9: output checks ---------------------------------------------------------------


def check_output(prepared: pd.DataFrame, raw: pd.DataFrame) -> None:
    """P9: fail unless `prepared` matches its schema and reconciles with `raw`.

    `raw` is `load.load_raw_transactions()`, all text. Checks row count, laundering count,
    and total amounts paid and received per currency, within floating-point rounding.
    """
    raise NotImplementedError("P9 is not written yet")


# --- pipeline ------------------------------------------------------------------------


def prepare_transactions(
    tx: pd.DataFrame,
    raw_lines: pd.Series,
    accounts: pd.DataFrame,
    pattern_lines: list[str],
    *,
    currency: CurrencySettings,
) -> Prepared:
    """Apply P3 to P8 to transactions from `load.load_transactions` (P1, P2).

    Schemes are tagged (P8) before sorting (P7), while rows are still in file order.
    """
    prepared = tx.copy()
    logger.info("P3 to P5: flagging duplicates, self-transfers and own-account transfers")
    prepared["is_duplicate"] = flag_duplicates(prepared)
    prepared["is_self_transfer"] = flag_self_transfers(prepared)
    prepared["is_own_account_transfer"] = flag_own_account_transfers(prepared, accounts)
    logger.info("P6: converting amounts to %s", currency.base_currency)
    rates = exchange_rates(prepared, currency.base_currency, currency.min_amount_paid)
    prepared = prepared.join(convert_amounts(prepared, rates))
    check_conversion(prepared, currency.min_amount_paid, currency.tolerance)
    logger.info("P8: tagging schemes")
    prepared = prepared.join(tag_schemes(prepared, raw_lines, parse_patterns(pattern_lines)))
    logger.info("P7: sorting by time")
    prepared = sort_by_time(prepared)
    return Prepared(prepared[PREPARED_COLUMNS].reset_index(drop=True), rates)


def run_summary(prepared: pd.DataFrame, rates: pd.Series, min_amount_paid: float) -> str:
    """Figures from a run, printed by `main()` for the Stage 2 report."""
    laundering = prepared[prepared["is_laundering"] == 1]
    self_transfers = prepared[prepared["is_self_transfer"]]
    gaps = conversion_gaps(prepared, min_amount_paid)
    typology = laundering["typology"].fillna("(not in patterns file)").value_counts()
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
            "P8 laundering payments by typology:",
            typology.to_string(),
        ]
    )


def raw_lines() -> pd.Series:
    """Each raw transaction line's text, indexed by row position (P1)."""
    lines = load.raw_file("transactions").read_text().splitlines()[1:]
    return pd.Series(lines, name="raw_line")


def prepared_path() -> Path:
    """Absolute path of the prepared transactions file."""
    return repo_path(load_config("data")["paths"]["prepared_transactions"])


def load_prepared_transactions(path: Path | None = None) -> pd.DataFrame:
    """Read the prepared transactions, checking every expected column is present."""
    prepared = pd.read_parquet(path or prepared_path())
    missing = set(PREPARED_COLUMNS) - set(prepared.columns)
    if missing:
        raise ValueError(f"prepared transactions file is missing columns: {sorted(missing)}")
    return prepared


def main() -> None:
    """Command-line entry point: prepare, check, save and summarise the transactions."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s: %(message)s"
    )
    currency = CurrencySettings.from_config(load_config("data")["transaction_preparation"])

    try:
        prepared, rates = prepare_transactions(
            load.load_transactions(),
            raw_lines(),
            load.load_accounts(),
            load.load_pattern_lines(),
            currency=currency,
        )
    except NotImplementedError:
        logger.error("Feature is not implemented yet.")
        raise
    except Exception:
        logger.exception("An unexpected error occurred during preparation.")
        raise

    logger.info("P9: checking the output")
    check_output(prepared, load.load_raw_transactions())

    # path = prepared_path()
    # path.parent.mkdir(parents=True, exist_ok=True)
    # prepared.to_parquet(path, index=False)
    print(run_summary(prepared, rates, currency.min_amount_paid))
    # print(f"saved to {path}")


if __name__ == "__main__":
    main()
