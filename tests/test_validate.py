"""Tests for the validation checks, using small hand-built inputs."""

import pandas as pd
import pytest
from builders import GOOD_ROW

from mule_detection.source import load
from mule_detection.source.validate import (
    _check_accounts,
    _check_expected,
    _check_patterns,
    _check_transactions,
)


def transactions(*rows: list[str]) -> pd.DataFrame:
    return pd.DataFrame(list(rows), columns=load.TRANSACTION_COLUMNS, dtype=str)


def row(**changes: str | None) -> list[str]:
    values = dict(zip(load.TRANSACTION_COLUMNS, GOOD_ROW, strict=True))
    values.update(changes)
    return list(values.values())


def accounts(*rows: list[str]) -> pd.DataFrame:
    return pd.DataFrame(list(rows), columns=load.ACCOUNT_COLUMNS, dtype=str)


# --- transactions ---------------------------------------------------------------------------------


def test_clean_transactions_pass():
    report = _check_transactions(
        transactions(row(), row(is_laundering="1")), load.TRANSACTION_HEADER
    )
    assert report.passed, report.errors
    assert report.info["rows"] == 2


def test_unexpected_header_fails():
    header = [*load.TRANSACTION_HEADER[:-1], "Label"]
    assert not _check_transactions(transactions(row()), header).passed


@pytest.mark.parametrize(
    "changes",
    [
        {"amount_paid": None},
        {"timestamp": "01/09/2022 00:20"},
        {"amount_received": "abc"},
        {"amount_paid": "0"},
        {"amount_received": "-5.00"},
        {"is_laundering": "2"},
        {"from_bank": "B10"},
    ],
    ids=["missing", "bad-timestamp", "non-numeric", "zero", "negative", "bad-label", "bank"],
)
def test_bad_value_fails(changes):
    report = _check_transactions(transactions(row(), row(**changes)), load.TRANSACTION_HEADER)
    assert not report.passed


def test_info_counts_duplicates_self_transfers_and_padding():
    self_transfer = row(to_bank="010", to_account="8000EBD30")
    report = _check_transactions(transactions(row(), row(), self_transfer), load.TRANSACTION_HEADER)
    assert report.passed
    assert report.info["duplicate_rows"] == 1
    assert report.info["self_transfers"] == 1
    assert report.info["bank_codes_as_written"] == 2  # "010" and "0010"
    assert report.info["bank_codes_unpadded"] == 1


# --- accounts -------------------------------------------------------------------------------------


ACCOUNT_A = ["Bank #10", "10", "8000EBD30", "E1", "Corporation #1"]
ACCOUNT_B = ["Bank #10", "10", "8000F5340", "E2", "Corporation #2"]
ACCOUNT_C = ["Bank #3", "3", "8000EBD30", "E3", "Corporation #3"]  # same number, other bank


def test_clean_accounts_pass_and_padding_matches_unpadded_bank_id():
    report = _check_accounts(
        accounts(ACCOUNT_A, ACCOUNT_B, ACCOUNT_C), load.ACCOUNT_HEADER, transactions(row())
    )
    assert report.passed, report.errors
    assert report.info["transacting_accounts"] == 2
    assert report.info["accounts_without_transactions"] == 1


def test_duplicate_account_key_fails():
    assert not _check_accounts(accounts(ACCOUNT_A, ACCOUNT_A), load.ACCOUNT_HEADER).passed


def test_transacting_account_missing_from_accounts_file_fails():
    report = _check_accounts(accounts(ACCOUNT_A), load.ACCOUNT_HEADER, transactions(row()))
    assert not report.passed


# --- patterns -------------------------------------------------------------------------------------


PATTERN_TXN = ",".join([*GOOD_ROW[:-1], "1"])


def test_clean_patterns_pass_and_count_typologies():
    lines = [
        "BEGIN LAUNDERING ATTEMPT - FAN-OUT:  Max 16-degree Fan-Out",
        PATTERN_TXN,
        "END LAUNDERING ATTEMPT - FAN-OUT",
        "",
        "BEGIN LAUNDERING ATTEMPT - CYCLE:  Max 5 hops",
        PATTERN_TXN,
        "END LAUNDERING ATTEMPT - CYCLE",
    ]
    report = _check_patterns(lines)
    assert report.passed, report.errors
    assert report.info["attempts_by_typology"] == {"CYCLE": 1, "FAN-OUT": 1}


@pytest.mark.parametrize(
    "lines",
    [
        ["BEGIN LAUNDERING ATTEMPT - CYCLE", PATTERN_TXN],
        ["END LAUNDERING ATTEMPT - CYCLE"],
        [PATTERN_TXN],
        ["BEGIN LAUNDERING ATTEMPT - CYCLE", ",".join(GOOD_ROW), "END LAUNDERING ATTEMPT"],
        ["BEGIN LAUNDERING ATTEMPT - CYCLE", "a,b,c", "END LAUNDERING ATTEMPT"],
    ],
    ids=["unclosed", "unmatched-end", "outside-block", "label-0", "field-count"],
)
def test_malformed_patterns_fail(lines):
    assert not _check_patterns(lines).passed


# --- expected file contents -----------------------------------------------------------------------


EXPECTED = {"sha256": "abc123", "rows": 10}


def test_matching_hash_and_rows_pass():
    assert _check_expected("f.csv", "abc123", 10, EXPECTED).passed


def test_changed_hash_fails():
    report = _check_expected("f.csv", "def456", 10, EXPECTED)
    assert not report.passed
    assert "SHA-256" in report.errors[0]


def test_changed_row_count_fails():
    report = _check_expected("f.csv", "abc123", 9, EXPECTED)
    assert not report.passed
    assert "rows" in report.errors[0]


def test_row_count_is_optional():
    assert _check_expected("patterns.txt", "abc123", None, {"sha256": "abc123"}).passed
