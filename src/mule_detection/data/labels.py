"""Account-level mule labels (receive and forward).

An account is identified by (bank_id, account_number), with bank IDs unpadded. Every account
that appears in at least one transaction gets a label. An account is a mule if it both receives
and sends at least one laundering transaction. Laundering self-transfers (same sender and
receiver account) are ignored when deciding this, since one such payment would otherwise count
as both receiving and sending. `mule_since` is the time of the account's first laundering
transaction, ignoring self-transfers, and is empty for non-mules. See `docs/decisions.md`.

Run with `python -m mule_detection.data.labels`.
"""

from pathlib import Path

import pandas as pd

from mule_detection.data import load
from mule_detection.utils.config import load_config, repo_path

KEY = ["bank_id", "account_number"]
LABEL_COLUMNS = KEY + ["is_mule", "mule_since", "laundering_received", "laundering_sent"]


def _side(tx: pd.DataFrame, bank: str, account: str) -> pd.DataFrame:
    return tx[[bank, account]].set_axis(KEY, axis=1)


def build_account_labels(tx: pd.DataFrame, ignore_self_transfers: bool = True) -> pd.DataFrame:
    """One row per transacting account with its mule label.

    `tx` needs `timestamp`, `from_bank`, `from_account`, `to_bank`, `to_account` and
    `is_laundering`, with bank IDs already unpadded (as returned by `load.load_transactions`).
    `ignore_self_transfers=False` exists only to measure the rule's effect.
    """
    accounts = pd.concat(
        [_side(tx, "from_bank", "from_account"), _side(tx, "to_bank", "to_account")]
    ).drop_duplicates()

    laundering = tx[tx["is_laundering"] == 1]
    if ignore_self_transfers:
        is_self = (laundering["from_bank"] == laundering["to_bank"]) & (
            laundering["from_account"] == laundering["to_account"]
        )
        laundering = laundering[~is_self]

    sent = (
        laundering.assign(**_side(laundering, "from_bank", "from_account"))
        .groupby(KEY)["timestamp"]
        .agg(laundering_sent="size", first_sent="min")
        .reset_index()
    )
    received = (
        laundering.assign(**_side(laundering, "to_bank", "to_account"))
        .groupby(KEY)["timestamp"]
        .agg(laundering_received="size", first_received="min")
        .reset_index()
    )

    labels = accounts.merge(sent, on=KEY, how="left").merge(received, on=KEY, how="left")
    for col in ["laundering_sent", "laundering_received"]:
        labels[col] = labels[col].fillna(0).astype("int64")
    labels["is_mule"] = (labels["laundering_received"] > 0) & (labels["laundering_sent"] > 0)
    first = labels[["first_sent", "first_received"]].min(axis=1)
    labels["mule_since"] = first.where(labels["is_mule"])

    return labels[LABEL_COLUMNS].sort_values(KEY).reset_index(drop=True)


def labels_path() -> Path:
    """Absolute path of the saved labels file."""
    return repo_path(load_config("data")["paths"]["labels"])


def main() -> None:
    tx = load.load_transactions()
    labels = build_account_labels(tx)
    path = labels_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    labels.to_parquet(path, index=False)

    with_self = int(build_account_labels(tx, ignore_self_transfers=False)["is_mule"].sum())
    mules = labels[labels["is_mule"]]
    print(f"accounts labelled: {len(labels):,}")
    print(f"mule accounts: {len(mules):,} ({100 * len(mules) / len(labels):.4f}%)")
    print(f"mules if laundering self-transfers counted: {with_self:,}")
    print(f"mule_since range: {mules['mule_since'].min()} to {mules['mule_since'].max()}")
    print(f"saved to {path}")


if __name__ == "__main__":
    main()
