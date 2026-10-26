"""Tests for the account-level mule labels, using small hand-built transaction sets."""

import pandas as pd

from mule_detection.data import load
from mule_detection.data.labels import LABEL_COLUMNS, build_account_labels

T1 = pd.Timestamp("2022-09-01 09:00")
T2 = pd.Timestamp("2022-09-01 12:00")
T3 = pd.Timestamp("2022-09-02 08:00")


def tx(*rows):
    """Rows of (timestamp, from_bank, from_account, to_bank, to_account, is_laundering)."""
    return pd.DataFrame(
        rows,
        columns=[
            "timestamp",
            "from_bank",
            "from_account",
            "to_bank",
            "to_account",
            "is_laundering",
        ],
    )


def label_of(labels, bank, account):
    row = labels[(labels["bank_id"] == bank) & (labels["account_number"] == account)]
    assert len(row) == 1, f"expected one row for {bank}:{account}, got {len(row)}"
    return row.iloc[0]


def test_pass_through_account_is_mule_and_its_neighbours_are_not():
    labels = build_account_labels(
        tx((T1, "1", "SRC", "2", "MULE", 1), (T2, "2", "MULE", "3", "DST", 1))
    )
    mule = label_of(labels, "2", "MULE")
    assert mule["is_mule"]
    assert (mule["laundering_received"], mule["laundering_sent"]) == (1, 1)
    assert not label_of(labels, "1", "SRC")["is_mule"]  # sends only
    assert not label_of(labels, "3", "DST")["is_mule"]  # receives only


def test_mule_since_is_first_laundering_transaction_in_either_direction():
    labels = build_account_labels(
        tx(
            (T1, "2", "MULE", "3", "DST", 1),
            (T2, "1", "SRC", "2", "MULE", 1),
            (T3, "2", "MULE", "3", "DST", 1),
        )
    )
    assert label_of(labels, "2", "MULE")["mule_since"] == T1


def test_normal_transactions_do_not_make_a_mule():
    labels = build_account_labels(tx((T1, "1", "A", "2", "B", 0), (T2, "2", "B", "3", "C", 0)))
    b = label_of(labels, "2", "B")
    assert not b["is_mule"]
    assert pd.isna(b["mule_since"])
    assert (b["laundering_received"], b["laundering_sent"]) == (0, 0)


def test_laundering_self_transfer_alone_does_not_make_a_mule():
    labels = build_account_labels(tx((T1, "1", "SELF", "1", "SELF", 1)))
    assert not label_of(labels, "1", "SELF")["is_mule"]


def test_self_transfer_does_not_supply_the_missing_direction():
    # Receives laundering money, then a laundering self-transfer: still receive-only.
    labels = build_account_labels(tx((T1, "1", "SRC", "2", "X", 1), (T2, "2", "X", "2", "X", 1)))
    assert not label_of(labels, "2", "X")["is_mule"]


def test_counting_self_transfers_changes_the_result():
    rows = (T1, "1", "SRC", "2", "X", 1), (T2, "2", "X", "2", "X", 1)
    assert label_of(build_account_labels(tx(*rows), ignore_self_transfers=False), "2", "X")[
        "is_mule"
    ]


def test_same_account_number_at_two_banks_is_two_accounts():
    labels = build_account_labels(tx((T1, "1", "SRC", "2", "Z", 1), (T2, "3", "Z", "4", "DST", 1)))
    assert not label_of(labels, "2", "Z")["is_mule"]  # receives only
    assert not label_of(labels, "3", "Z")["is_mule"]  # sends only


def test_every_transacting_account_gets_exactly_one_row():
    labels = build_account_labels(
        tx((T1, "1", "A", "2", "B", 0), (T2, "2", "B", "1", "A", 1), (T3, "1", "A", "1", "A", 0))
    )
    assert labels.columns.tolist() == LABEL_COLUMNS
    assert len(labels) == 2
    assert not labels.duplicated(["bank_id", "account_number"]).any()


def test_padded_bank_ids_are_the_same_account(tmp_path):
    # "010" and "0010" are both bank 10 once loaded, so this account receives and sends.
    rows = [
        [
            "2022/09/01 09:00",
            "001",
            "SRC",
            "010",
            "MULE",
            "5.00",
            "Euro",
            "5.00",
            "Euro",
            "ACH",
            "1",
        ],
        [
            "2022/09/01 12:00",
            "0010",
            "MULE",
            "003",
            "DST",
            "5.00",
            "Euro",
            "5.00",
            "Euro",
            "ACH",
            "1",
        ],
    ]
    path = tmp_path / "trans.csv"
    path.write_text(
        "\n".join([",".join(load.TRANSACTION_HEADER)] + [",".join(r) for r in rows]) + "\n"
    )
    labels = build_account_labels(load.load_transactions(path))
    assert label_of(labels, "10", "MULE")["is_mule"]
