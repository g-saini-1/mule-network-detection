"""Tests for the transfer flags, using small hand-built transaction tables."""

import pytest
from builders import acc, frame, txn

from mule_detection.payments.transfers import flag_own_account_transfers, flag_self_transfers

# --- P4 -------------------------------------------------------------------------------------------


def test_p4_only_same_bank_and_same_account_is_a_self_transfer():
    tx = frame(txn(to_bank="10", to_account="A"), txn(), txn(to_account="A"), txn(to_bank="10"))
    assert flag_self_transfers(tx).tolist() == [True, False, False, False]


# --- P5 -------------------------------------------------------------------------------------------


def test_p5_same_entity_different_banks_is_not_own_account_transfer():
    tx = frame(txn())
    accs = frame(
        acc(bank_id="10", account_number="A", entity_id="E1"),
        acc(bank_id="20", account_number="B", entity_id="E1"),
    )
    assert flag_own_account_transfers(tx, accs).tolist() == [False]


def test_p5_same_entity_same_bank_is_own_account_transfer():
    tx = frame(txn(to_bank="10"))
    accs = frame(
        acc(bank_id="10", account_number="A", entity_id="E1"),
        acc(bank_id="10", account_number="B", entity_id="E1"),
    )
    assert flag_own_account_transfers(tx, accs).tolist() == [True]


def test_p5_different_entity_same_bank_is_not_own_account_transfer():
    tx = frame(txn(to_bank="10"))
    accs = frame(
        acc(bank_id="10", account_number="A", entity_id="E1"),
        acc(bank_id="10", account_number="B", entity_id="E2"),
    )
    assert flag_own_account_transfers(tx, accs).tolist() == [False]


def test_p5_unknown_entity_same_bank_is_not_own_account_transfer():
    tx = frame(txn(to_bank="10", to_account="Z"))
    accs = frame(acc(bank_id="10", account_number="A", entity_id="E1"))
    assert flag_own_account_transfers(tx, accs).tolist() == [False]


def test_p5_same_entity_same_bank_same_account_is_not_own_account_transfer():
    tx = frame(txn(to_bank="10", to_account="A"))
    accs = frame(acc(bank_id="10", account_number="A", entity_id="E1"))
    assert flag_own_account_transfers(tx, accs).tolist() == [False]


def test_p5_result_keeps_the_row_labels_of_tx():
    tx = frame(txn(to_bank="10", to_account="A")).set_axis([99])
    accs = frame(acc(bank_id="10", account_number="A", entity_id="E1"))
    assert flag_own_account_transfers(tx, accs).index.tolist() == [99]


def test_p5_both_sides_unknown_at_the_same_bank_is_not_own_account_transfer():
    tx = frame(txn(from_account="Y", to_bank="10", to_account="Z"))
    accs = frame(acc(bank_id="10", account_number="A", entity_id="E1"))
    assert flag_own_account_transfers(tx, accs).tolist() == [False]


def test_p5_an_account_listed_twice_fails():
    tx = frame(txn(to_bank="10"))
    accs = frame(
        acc(bank_id="10", account_number="A", entity_id="E1"),
        acc(bank_id="10", account_number="A", entity_id="E2"),
    )
    with pytest.raises(ValueError, match="more than once"):
        flag_own_account_transfers(tx, accs)
