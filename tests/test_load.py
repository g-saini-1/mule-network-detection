"""Tests for the raw-data loaders, using small hand-built files."""

import pandas as pd
import pytest
from builders import GOOD_ROW, raw_transactions_file

from mule_detection.source import load

# --- raw loaders ----------------------------------------------------------------------------------


def test_load_raw_transactions_names_duplicate_account_columns_by_position(tmp_path):
    path = raw_transactions_file(tmp_path, GOOD_ROW)
    df = load.load_raw_transactions(path)
    assert df.columns.tolist() == load.TRANSACTION_COLUMNS
    assert df.loc[0, "from_account"] == "8000EBD30"
    assert df.loc[0, "to_account"] == "8000F5340"
    assert df.loc[0, "from_bank"] == "010"  # leading zero kept as text
    assert load.read_header(path) == load.TRANSACTION_HEADER


def test_load_raw_transactions_reads_only_the_columns_asked_for_in_file_order(tmp_path):
    received_differs = [*GOOD_ROW[:5], "50.00", "Euro", *GOOD_ROW[7:]]
    path = raw_transactions_file(tmp_path, received_differs)
    df = load.load_raw_transactions(path, columns=["payment_currency", "amount_paid"])
    assert df.columns.tolist() == ["amount_paid", "payment_currency"]
    assert df.to_dict("records") == [{"amount_paid": "3697.34", "payment_currency": "US Dollar"}]


# --- P1 -------------------------------------------------------------------------------------------


def test_p1_transaction_id_is_the_row_position_in_file_order():
    tx = pd.DataFrame({"from_account": ["A", "B", "C"]})
    assert load._transaction_ids(tx).tolist() == [0, 1, 2]


def test_p1_load_transactions_puts_transaction_id_first(tmp_path):
    df = load.load_transactions(raw_transactions_file(tmp_path, GOOD_ROW, GOOD_ROW))
    assert df.columns[0] == "transaction_id"
    assert df["transaction_id"].tolist() == [0, 1]


# --- P2 -------------------------------------------------------------------------------------------


def test_p2_bank_ids_lose_padding_but_keep_zero():
    banks = pd.Series(["010", "0010", "10", "03208", "0", "000"])
    assert load.normalise_bank_id(banks).tolist() == ["10", "10", "10", "3208", "0", "0"]


def test_p2_columns_are_parsed_to_their_types(tmp_path):
    df = load.load_transactions(raw_transactions_file(tmp_path, GOOD_ROW))
    assert df.loc[0, "timestamp"] == pd.Timestamp("2022-09-01 00:20")
    assert df.loc[0, "amount_paid"] == pytest.approx(3697.34)
    assert df.loc[0, "is_laundering"] == 0
    assert (df.loc[0, "from_bank"], df.loc[0, "to_bank"]) == ("10", "10")
