"""Data contract for typed transactions, the input to transaction preparation.

Produced by `load.load_transactions` (P1, P2) and relied on by preparation, whose payment rules
(P4 to P6) depend on it, e.g. P5 matches no account if bank IDs are zero-padded. Checked when
`prepare_transactions` starts. Contracts are described in DEVELOPMENT.md ("Data"); tests are in
`tests/test_typed_transactions_contract.py`.
"""

import numpy as np
import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from mule_detection.source.load import UNPADDED_BANK_ID

__all__ = ["TypedTransactionsContract"]


class TypedTransactionsContract(pa.DataFrameModel):
    """Exactly these columns, in this order, with no empty values (P1, P2).

    `timestamp` must be a time-zone-naive datetime; its unit (e.g. microseconds) is not
    constrained.
    """

    transaction_id: Series[int] = pa.Field(ge=0, unique=True)
    timestamp: Series[pd.Timestamp]
    from_bank: Series[str] = pa.Field(str_matches=UNPADDED_BANK_ID)
    from_account: Series[str] = pa.Field(str_length={"min_value": 1})
    to_bank: Series[str] = pa.Field(str_matches=UNPADDED_BANK_ID)
    to_account: Series[str] = pa.Field(str_length={"min_value": 1})
    amount_received: Series[float] = pa.Field(gt=0)
    receiving_currency: Series[pd.CategoricalDtype]
    amount_paid: Series[float] = pa.Field(gt=0)
    payment_currency: Series[pd.CategoricalDtype]
    payment_format: Series[pd.CategoricalDtype]
    is_laundering: Series[np.int8] = pa.Field(isin=[0, 1])

    class Config:
        """Reject missing and extra columns, and columns out of order."""

        strict = True
        ordered = True

    @pa.check("amount_received", "amount_paid", error="amounts must be finite")
    @classmethod
    def amounts_are_finite(cls, amounts: "pd.Series[float]") -> "pd.Series[bool]":
        """Reject infinite amounts, which the rule above 0 lets through."""
        return amounts.abs() < np.inf
