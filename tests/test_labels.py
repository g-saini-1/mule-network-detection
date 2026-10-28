"""Tests for the account-level mule labels, using small hand-built transaction sets."""

import pandas as pd
import pytest

from mule_detection.data import load
from mule_detection.data.labels import (
    LABEL_COLUMNS,
    build_account_labels,
    load_labels,
    role_counts,
)

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


# --- the mule rule ---------------------------------------------------------------------


def test_r4_receiving_and_sending_makes_a_mule_and_its_neighbours_are_not():
    labels = build_account_labels(
        tx((T1, "1", "SRC", "2", "MULE", 1), (T2, "2", "MULE", "3", "DST", 1))
    )
    mule = label_of(labels, "2", "MULE")
    assert mule["is_mule"]
    assert (mule["laundering_received"], mule["laundering_sent"]) == (1, 1)
    assert not label_of(labels, "1", "SRC")["is_mule"]  # sends only
    assert not label_of(labels, "3", "DST")["is_mule"]  # receives only


def test_r4_order_of_receipt_and_send_does_not_matter():
    # A send timestamped before the receipt still counts.
    labels = build_account_labels(tx((T1, "2", "X", "3", "DST", 1), (T2, "1", "SRC", "2", "X", 1)))
    x = label_of(labels, "2", "X")
    assert x["is_mule"]
    assert (x["first_sent_at"], x["first_received_at"]) == (T1, T2)


def test_r2_normal_transactions_do_not_make_a_mule():
    labels = build_account_labels(tx((T1, "1", "A", "2", "B", 0), (T2, "2", "B", "3", "C", 0)))
    b = label_of(labels, "2", "B")
    assert not b["is_mule"]
    assert pd.isna(b["mule_at"]) and pd.isna(b["first_laundering_at"])
    assert (b["laundering_received"], b["laundering_sent"]) == (0, 0)


# --- timing ----------------------------------------------------------------------------


def test_r5_mule_at_is_when_both_directions_have_happened():
    # Sends at T1, receives at T2, sends again at T3: a mule from T2.
    labels = build_account_labels(
        tx(
            (T1, "2", "X", "3", "DST", 1),
            (T2, "1", "SRC", "2", "X", 1),
            (T3, "2", "X", "3", "DST", 1),
        )
    )
    x = label_of(labels, "2", "X")
    assert x["mule_at"] == T2
    assert x["first_laundering_at"] == T1


def test_r5_receipt_and_send_in_the_same_minute_make_a_mule_at_that_minute():
    labels = build_account_labels(tx((T1, "1", "SRC", "2", "X", 1), (T1, "2", "X", "3", "DST", 1)))
    assert label_of(labels, "2", "X")["mule_at"] == T1


def test_r6_as_at_ignores_payments_from_that_time_onwards():
    rows = (T1, "1", "SRC", "2", "X", 1), (T3, "2", "X", "3", "DST", 1)
    before = build_account_labels(tx(*rows), as_at=T2)
    assert not label_of(before, "2", "X")["is_mule"]  # has only received so far
    assert label_of(before, "2", "X")["laundering_sent"] == 0
    after = build_account_labels(tx(*rows), as_at="2022-09-03")
    assert label_of(after, "2", "X")["mule_at"] == T3


def test_r6_as_at_excludes_payments_at_exactly_the_cut_off():
    rows = (T1, "1", "SRC", "2", "X", 1), (T2, "2", "X", "3", "DST", 1)
    assert not label_of(build_account_labels(tx(*rows), as_at=T2), "2", "X")["is_mule"]


def test_r7_as_at_leaves_out_accounts_that_first_appear_after_the_cut_off():
    labels = build_account_labels(
        tx((T1, "1", "A", "2", "B", 0), (T3, "3", "LATE", "2", "B", 0)), as_at=T2
    )
    assert set(labels["account_number"]) == {"A", "B"}


def test_row_order_does_not_change_the_labels():
    # X has two laundering sends, listed latest first, so file order and time order differ.
    rows = [
        (T3, "2", "X", "3", "DST", 1),
        (T1, "1", "SRC", "2", "X", 1),
        (T2, "2", "X", "4", "Y", 0),
        (T2, "4", "Y", "2", "X", 1),
        (T2, "2", "X", "5", "Z", 1),
    ]
    in_order = build_account_labels(tx(*rows))
    shuffled = build_account_labels(tx(*reversed(rows)))
    pd.testing.assert_frame_equal(in_order, shuffled)
    assert label_of(in_order, "2", "X")["first_sent_at"] == T2


# --- self-transfers and account identity -----------------------------------------------


def test_r3_laundering_self_transfer_alone_does_not_make_a_mule():
    labels = build_account_labels(tx((T1, "1", "SELF", "1", "SELF", 1)))
    assert not label_of(labels, "1", "SELF")["is_mule"]


def test_r3_self_transfer_does_not_count_as_passing_money_on():
    labels = build_account_labels(tx((T1, "1", "SRC", "2", "X", 1), (T2, "2", "X", "2", "X", 1)))
    assert not label_of(labels, "2", "X")["is_mule"]


def test_r3_self_transfer_does_not_count_as_a_receipt():
    labels = build_account_labels(tx((T1, "2", "X", "2", "X", 1), (T2, "2", "X", "3", "DST", 1)))
    x = label_of(labels, "2", "X")
    assert not x["is_mule"]
    assert pd.isna(x["first_received_at"])


def test_r1_same_account_number_at_another_bank_is_not_a_self_transfer():
    # 1:Z pays 2:Z: a real payment between two accounts, so 2:Z receives and then sends.
    labels = build_account_labels(tx((T1, "1", "Z", "2", "Z", 1), (T2, "2", "Z", "3", "DST", 1)))
    assert label_of(labels, "2", "Z")["is_mule"]
    assert label_of(labels, "1", "Z")["first_sent_at"] == T1


def test_r3_counting_self_transfers_changes_the_result():
    rows = (T1, "1", "SRC", "2", "X", 1), (T2, "2", "X", "2", "X", 1)
    labels = build_account_labels(tx(*rows), ignore_self_transfers=False)
    assert label_of(labels, "2", "X")["is_mule"]


def test_r1_same_account_number_at_two_banks_is_two_accounts():
    labels = build_account_labels(tx((T1, "1", "SRC", "2", "Z", 1), (T2, "3", "Z", "4", "DST", 1)))
    assert not label_of(labels, "2", "Z")["is_mule"]  # receives only
    assert not label_of(labels, "3", "Z")["is_mule"]  # sends only


def test_r1_padded_bank_ids_are_rejected():
    with pytest.raises(ValueError, match="zero-padded"):
        build_account_labels(tx((T1, "010", "A", "2", "B", 0)))


def test_r1_padded_bank_ids_are_the_same_account_once_loaded(tmp_path):
    # "010" and "0010" are both bank 10 once loaded, so this account receives and sends.
    header = ",".join(load.TRANSACTION_HEADER)
    rows = [
        "2022/09/01 09:00,001,SRC,010,MULE,5.00,Euro,5.00,Euro,ACH,1",
        "2022/09/01 12:00,0010,MULE,003,DST,5.00,Euro,5.00,Euro,ACH,1",
    ]
    path = tmp_path / "trans.csv"
    path.write_text("\n".join([header, *rows]) + "\n")
    labels = build_account_labels(load.load_transactions(path))
    assert label_of(labels, "10", "MULE")["is_mule"]


# --- output ----------------------------------------------------------------------------


def test_r7_every_transacting_account_gets_exactly_one_row():
    labels = build_account_labels(
        tx((T1, "1", "A", "2", "B", 0), (T2, "2", "B", "1", "A", 1), (T3, "1", "A", "1", "A", 0))
    )
    assert labels.columns.tolist() == LABEL_COLUMNS
    assert len(labels) == 2
    assert not labels.duplicated(["bank_id", "account_number"]).any()


def test_role_counts_cover_every_account_once():
    labels = build_account_labels(
        tx(
            (T1, "1", "SRC", "2", "MULE", 1),
            (T2, "2", "MULE", "3", "DST", 1),
            (T1, "4", "S", "5", "Y", 1),
            (T2, "5", "Y", "4", "S", 1),
            (T1, "6", "A", "7", "B", 0),
        )
    )
    counts = role_counts(labels)
    assert counts.sum() == len(labels)
    assert counts["both directions (mule), receipt timestamped first"] == 2  # MULE and Y
    assert counts["both directions (mule), send timestamped first"] == 1  # S


def test_load_labels_keeps_digit_account_numbers_as_text(tmp_path):
    labels = build_account_labels(
        tx((T1, "1", "800737690", "2", "000123", 1), (T2, "2", "000123", "3", "DST", 1))
    )
    path = tmp_path / "labels.parquet"
    labels.to_parquet(path, index=False)
    loaded = load_labels(path)
    assert label_of(loaded, "2", "000123")["is_mule"]
    assert loaded["account_number"].tolist() == labels["account_number"].tolist()
    assert loaded["mule_at"].dtype.kind == "M"
