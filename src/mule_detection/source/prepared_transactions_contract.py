"""Data contract for prepared transactions, the output of transaction preparation (P8).

Produced by `prepare_transactions` (P3 to P7) and consumed by detection, e.g. the rules engine.
Declared here; P8 will check it before the file is written, and no check on reading exists yet.
It holds no ground truth (T1 to T3, `docs/transaction_labelling_guide.md`): the laundering flag
is not among its columns, and no other column is allowed. Contracts are described in
DEVELOPMENT.md ("Data"); tests are in `tests/test_prepared_transactions_contract.py`.
"""

import numpy as np
import pandas as pd
import pandera.pandas as pa
from pandera.typing import DataFrame, Series

from mule_detection.source.load import UNPADDED_BANK_ID

__all__ = ["PreparedTransactionsContract"]


class PreparedTransactionsContract(pa.DataFrameModel):
    """Exactly these columns, in this order, with no empty values, in time order (P7).

    `timestamp` must be a time-zone-naive datetime; its unit (e.g. microseconds) is not
    constrained.
    """

    transaction_id: Series[int] = pa.Field(ge=0, unique=True)
    timestamp: Series[pd.Timestamp]
    from_bank: Series[str] = pa.Field(str_matches=UNPADDED_BANK_ID)
    from_account: Series[str] = pa.Field(str_length={"min_value": 1})
    to_bank: Series[str] = pa.Field(str_matches=UNPADDED_BANK_ID)
    to_account: Series[str] = pa.Field(str_length={"min_value": 1})
    amount_paid: Series[float] = pa.Field(gt=0)
    payment_currency: Series[pd.CategoricalDtype]
    amount_received: Series[float] = pa.Field(gt=0)
    receiving_currency: Series[pd.CategoricalDtype]
    payment_format: Series[pd.CategoricalDtype]
    is_duplicate: Series[bool]
    is_self_transfer: Series[bool]
    is_own_account_transfer: Series[bool]
    amount_paid_base: Series[float] = pa.Field(gt=0)
    amount_received_base: Series[float] = pa.Field(gt=0)

    class Config:
        """Reject missing and extra columns, and columns out of order."""

        strict = True
        ordered = True

    @pa.check(
        "amount_paid",
        "amount_received",
        "amount_paid_base",
        "amount_received_base",
        error="amounts must be finite",
    )
    @classmethod
    def amounts_are_finite(cls, amounts: "pd.Series[float]") -> "pd.Series[bool]":
        """Reject infinite amounts, which the rule above 0 lets through."""
        return amounts.abs() < np.inf

    @pa.dataframe_check(error="rows are not sorted by timestamp, with ties by transaction_id (P7)")
    @classmethod
    def in_time_order(cls, prepared: DataFrame["PreparedTransactionsContract"]) -> bool:
        """P7: each row is later than the one before, or at the same time with a higher ID."""
        timestamp, transaction_id = prepared["timestamp"], prepared["transaction_id"]
        later = timestamp > timestamp.shift()
        tie_in_id_order = (timestamp == timestamp.shift()) & (
            transaction_id > transaction_id.shift()
        )
        in_order = later | tie_in_id_order
        return bool(in_order.iloc[1:].all())
