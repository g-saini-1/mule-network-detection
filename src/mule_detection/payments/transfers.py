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
    `account_number` and `entity_id`. Fails if an account appears in it more than once. Returns
    a bool Series aligned to `tx.index`.
    """
    if accounts.duplicated(["bank_id", "account_number"]).any():
        raise ValueError(
            "P5: an account (bank ID plus account number) appears more than once in accounts"
        )
    from_owner = _owner_of(tx, "from_bank", "from_account", accounts)
    to_owner = _owner_of(tx, "to_bank", "to_account", accounts)
    return (
        (tx["from_bank"] == tx["to_bank"])
        & (tx["from_account"] != tx["to_account"])
        & from_owner.eq(to_owner)
    ).rename("is_own_account_transfer")


def _owner_of(tx: pd.DataFrame, bank: str, account: str, accounts: pd.DataFrame) -> pd.Series:
    """P5: the owner (`entity_id`) of the account in columns `bank` and `account` of each row.

    `accounts` must list each account once, so the merge keeps one row per transaction. Empty
    where the account is not in `accounts`. Returns a Series aligned to `tx.index`.
    """
    side = tx[[bank, account]].merge(
        accounts[["bank_id", "account_number", "entity_id"]],
        left_on=[bank, account],
        right_on=["bank_id", "account_number"],
        how="left",
    )
    return side["entity_id"].set_axis(tx.index)
