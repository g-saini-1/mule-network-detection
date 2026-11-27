"""Load the raw HI-Small files into pandas with consistent column names and types.

The transactions file has two columns both named `Account` (sender, then receiver), so
columns are named by position rather than by header. Bank codes are zero-padded
inconsistently in the transactions file (e.g. `010` and `0010` are both bank 10), while the
accounts file stores them unpadded; `normalise_bank_id` maps both to the unpadded form.
"""

from pathlib import Path

import pandas as pd

from mule_detection.utils.config import load_config, repo_path

TRANSACTION_HEADER = [
    "Timestamp",
    "From Bank",
    "Account",
    "To Bank",
    "Account",
    "Amount Received",
    "Receiving Currency",
    "Amount Paid",
    "Payment Currency",
    "Payment Format",
    "Is Laundering",
]
TRANSACTION_COLUMNS = [
    "timestamp",
    "from_bank",
    "from_account",
    "to_bank",
    "to_account",
    "amount_received",
    "receiving_currency",
    "amount_paid",
    "payment_currency",
    "payment_format",
    "is_laundering",
]
ACCOUNT_HEADER = ["Bank Name", "Bank ID", "Account Number", "Entity ID", "Entity Name"]
ACCOUNT_COLUMNS = ["bank_name", "bank_id", "account_number", "entity_id", "entity_name"]

TIMESTAMP_FORMAT = "%Y/%m/%d %H:%M"


def raw_file(key: str) -> Path:
    """Absolute path of a configured raw file, e.g. `raw_file("transactions")`."""
    config = load_config("data")
    file_name: str = config["files"][key]
    return repo_path(config["paths"]["raw"]) / file_name


def read_header(path: Path) -> list[str]:
    """Return a CSV file's header row exactly as written, duplicates included."""
    with path.open() as fh:
        return fh.readline().rstrip("\r\n").split(",")


def normalise_bank_id(banks: pd.Series) -> pd.Series:
    """Strip zero-padding from bank codes, keeping them as strings (`"0010"` -> `"10"`)."""
    return banks.str.lstrip("0").replace("", "0")


def load_raw_transactions(path: Path | None = None) -> pd.DataFrame:
    """Transactions with every column as an unparsed string, named by position."""
    path = path or raw_file("transactions")
    return pd.read_csv(path, header=0, names=TRANSACTION_COLUMNS, dtype=str)


def load_raw_accounts(path: Path | None = None) -> pd.DataFrame:
    """Accounts with every column as an unparsed string."""
    path = path or raw_file("accounts")
    return pd.read_csv(path, header=0, names=ACCOUNT_COLUMNS, dtype=str)


def load_transactions(path: Path | None = None) -> pd.DataFrame:
    """Typed transactions: parsed timestamps, float amounts, 0/1 label, unpadded bank IDs."""
    df = load_raw_transactions(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format=TIMESTAMP_FORMAT)
    for col in ["amount_received", "amount_paid"]:
        df[col] = df[col].astype(float)
    df["is_laundering"] = df["is_laundering"].astype("int8")
    for col in ["from_bank", "to_bank"]:
        df[col] = normalise_bank_id(df[col])
    for col in ["receiving_currency", "payment_currency", "payment_format"]:
        df[col] = df[col].astype("category")
    return df


def load_accounts(path: Path | None = None) -> pd.DataFrame:
    """Typed accounts with unpadded bank IDs."""
    df = load_raw_accounts(path)
    df["bank_id"] = normalise_bank_id(df["bank_id"])
    return df


def load_pattern_lines(path: Path | None = None) -> list[str]:
    """Lines of the laundering patterns file, without line endings."""
    path = path or raw_file("patterns")
    return Path(path).read_text().splitlines()
