"""Classify transfers by the accounts on each side (P4, P5).

The rules are in `docs/transaction_preparation_guide.md`; the reasoning is in
`docs/decisions.md`. Tests in `tests/test_transfers.py` are named by rule number.

- P4: payments from an account to itself are flagged `is_self_transfer`.
- P5: payments between two accounts at the same bank with the same owner are flagged
  `is_own_account_transfer`.
"""

import pandas as pd

__all__ = ["flag_own_account_transfers", "flag_self_transfers"]


def flag_self_transfers(tx: pd.DataFrame) -> pd.Series:
    """P4: True where sender and receiver are the same account (R1: bank ID plus account).

    Returns a bool Series aligned to `tx.index`.
    """
    return ((tx["from_bank"] == tx["to_bank"]) & (tx["from_account"] == tx["to_account"])).rename(
        "is_self_transfer"
    )


def flag_own_account_transfers(tx: pd.DataFrame, accounts: pd.DataFrame) -> pd.Series:
    """P5: True for different accounts at the same bank with the same owner.

    `accounts` is `load.load_accounts()`: one row per account, with `bank_id`,
    `account_number` and `entity_id`. Returns a bool Series aligned to `tx.index`.
    """
    tx1 = (
        tx.merge(
            accounts[["bank_id", "account_number", "entity_id"]],
            left_on=["from_bank", "from_account"],
            right_on=["bank_id", "account_number"],
            how="left",
        )
        .set_axis(tx.index)
        .rename(columns={"entity_id": "from_entity_id"})
    )
    tx2 = (
        tx1.merge(
            accounts[["bank_id", "account_number", "entity_id"]],
            left_on=["to_bank", "to_account"],
            right_on=["bank_id", "account_number"],
            how="left",
        )
        .set_axis(tx1.index)
        .rename(columns={"entity_id": "to_entity_id"})
    )

    return (
        (tx2["from_bank"] == tx2["to_bank"])
        & (tx2["from_account"] != tx2["to_account"])
        & (tx2["from_entity_id"] == tx2["to_entity_id"])
    ).rename("is_own_account_transfer")
