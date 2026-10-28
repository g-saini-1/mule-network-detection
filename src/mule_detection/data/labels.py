"""Account-level mule labels: an account that both receives and sends laundering money.

The rules R1 to R7, with examples, are in `data/README.md` ("Account labels"); the reasoning
is in `docs/decisions.md`. Tests in `tests/test_labels.py` are named by rule number.

- R1: an account is (bank_id, account_number), with bank IDs unpadded.
- R2: a laundering payment has `is_laundering == 1`.
- R3: laundering self-transfers are ignored.
- R4: a mule receives and sends at least one laundering payment, in either order.
- R5: `mule_at` is the later of the first receipt and the first send; `first_*` columns record
  first involvement.
- R6: with `as_at`, only payments strictly before that time are used.
- R7: every account in at least one transaction (before `as_at`, if given) gets a label.

Run with `python -m mule_detection.data.labels`.
"""

from pathlib import Path

import pandas as pd

from mule_detection.data import load
from mule_detection.utils.config import load_config, repo_path

KEY = ["bank_id", "account_number"]
LABEL_COLUMNS = KEY + [
    "is_mule",
    "mule_at",
    "first_laundering_at",
    "first_received_at",
    "first_sent_at",
    "laundering_received",
    "laundering_sent",
]


def _side(tx: pd.DataFrame, bank: str, account: str) -> pd.DataFrame:
    return tx[[bank, account]].set_axis(KEY, axis=1)


def _check_unpadded(tx: pd.DataFrame) -> None:
    banks = pd.concat([tx["from_bank"], tx["to_bank"]])
    padded = banks[banks.str.match(r"0\d")]
    if len(padded):
        raise ValueError(
            f"{len(padded)} bank IDs are still zero-padded (e.g. {padded.iloc[0]!r}); "
            "load transactions with load.load_transactions"
        )


def build_account_labels(
    tx: pd.DataFrame, as_at=None, ignore_self_transfers: bool = True
) -> pd.DataFrame:
    """One row per transacting account with its mule label and laundering timeline.

    `tx` needs `timestamp`, `from_bank`, `from_account`, `to_bank`, `to_account` and
    `is_laundering`, with bank IDs unpadded (as returned by `load.load_transactions`).
    `ignore_self_transfers=False` exists only to measure the rule's effect.
    """
    _check_unpadded(tx)
    if as_at is not None:
        tx = tx[tx["timestamp"] < pd.Timestamp(as_at)]

    accounts = pd.concat(
        [_side(tx, "from_bank", "from_account"), _side(tx, "to_bank", "to_account")]
    ).drop_duplicates()

    laundering = tx[tx["is_laundering"] == 1]
    if ignore_self_transfers:
        is_self = (laundering["from_bank"] == laundering["to_bank"]) & (
            laundering["from_account"] == laundering["to_account"]
        )
        laundering = laundering[~is_self]

    sends = _side(laundering, "from_bank", "from_account").assign(timestamp=laundering["timestamp"])
    receipts = _side(laundering, "to_bank", "to_account").assign(timestamp=laundering["timestamp"])
    sent = sends.groupby(KEY)["timestamp"].agg(laundering_sent="size", first_sent_at="min")
    received = receipts.groupby(KEY)["timestamp"].agg(
        laundering_received="size", first_received_at="min"
    )

    labels = accounts.merge(sent.reset_index(), on=KEY, how="left").merge(
        received.reset_index(), on=KEY, how="left"
    )
    for col in ["laundering_sent", "laundering_received"]:
        labels[col] = labels[col].fillna(0).astype("int64")
    labels["is_mule"] = (labels["laundering_received"] > 0) & (labels["laundering_sent"] > 0)
    firsts = labels[["first_sent_at", "first_received_at"]]
    labels["mule_at"] = firsts.max(axis=1).where(labels["is_mule"])
    labels["first_laundering_at"] = firsts.min(axis=1)

    return labels[LABEL_COLUMNS].sort_values(KEY).reset_index(drop=True)


def role_counts(labels: pd.DataFrame) -> pd.Series:
    """Accounts by laundering role, as described in data/README.md."""
    received = labels["laundering_received"] > 0
    sent = labels["laundering_sent"] > 0
    receipt_first = labels["first_received_at"] <= labels["first_sent_at"]
    return pd.Series(
        {
            "no laundering payments": int((~received & ~sent).sum()),
            "send only": int((sent & ~received).sum()),
            "receive only": int((received & ~sent).sum()),
            "both directions (mule), receipt timestamped first": int(
                (labels["is_mule"] & receipt_first).sum()
            ),
            "both directions (mule), send timestamped first": int(
                (labels["is_mule"] & ~receipt_first).sum()
            ),
        }
    )


def labels_path() -> Path:
    """Absolute path of the saved labels file."""
    return repo_path(load_config("data")["paths"]["labels"])


def load_labels(path: Path | None = None) -> pd.DataFrame:
    """Read the saved labels, keeping account keys as text and timestamps as datetimes."""
    labels = pd.read_parquet(path or labels_path())
    missing = set(LABEL_COLUMNS) - set(labels.columns)
    if missing:
        raise ValueError(f"labels file is missing columns: {sorted(missing)}")
    return labels.astype({"bank_id": "string", "account_number": "string"})


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
    print(f"mule_at range: {mules['mule_at'].min()} to {mules['mule_at'].max()}")
    print("accounts by laundering role:")
    print(role_counts(labels).to_string())
    print(f"saved to {path}")


if __name__ == "__main__":
    main()
