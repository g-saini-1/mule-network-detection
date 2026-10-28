"""Validation checks for the raw HI-Small files.

Each check function takes unparsed (all-string) data and returns a `ValidationReport`:
`errors` lists hard failures that would make later stages wrong, and `info` holds
descriptive counts worth knowing but not failing on (e.g. duplicate rows). `validate_all`
first confirms each file matches the hash and row count expected in `configs/data.yaml`, then
runs the content checks, and raises `ValidationError` if any file has errors.

Run with `python -m mule_detection.data.validate`.
"""

import json
import re
from dataclasses import dataclass, field

import pandas as pd

from mule_detection.data import load
from mule_detection.data.download import sha256
from mule_detection.utils.config import load_config

PATTERN_BEGIN = re.compile(r"^BEGIN LAUNDERING ATTEMPT - ([A-Z-]+)")
PATTERN_END = "END LAUNDERING ATTEMPT"


class ValidationError(Exception):
    """Raised when one or more raw files fail a hard check."""


@dataclass
class ValidationReport:
    """Hard failures (`errors`) and descriptive counts (`info`) from one check."""

    errors: list[str] = field(default_factory=list)
    info: dict = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """True if the check found no hard failures."""
        return not self.errors


def check_expected(
    name: str, actual_sha256: str, actual_rows: int | None, expected: dict
) -> ValidationReport:
    """Compare a file's hash, and its row count when one is expected, with the config."""
    report = ValidationReport()
    if actual_sha256 != expected["sha256"]:
        report.errors.append(
            f"{name}: SHA-256 {actual_sha256} does not match expected {expected['sha256']}"
        )
    if "rows" in expected and actual_rows != expected["rows"]:
        report.errors.append(f"{name}: {actual_rows} rows, expected {expected['rows']}")
    report.info = {"sha256": actual_sha256, "rows": actual_rows}
    return report


def check_transactions(raw: pd.DataFrame, header: list[str]) -> ValidationReport:
    """Schema, completeness, timestamp, amount, label and bank-code checks."""
    report = ValidationReport()
    if header != load.TRANSACTION_HEADER:
        report.errors.append(f"unexpected header: {header}")

    nulls = raw.isna().sum()
    for col, n in nulls[nulls > 0].items():
        report.errors.append(f"{col}: {n} missing values")

    ts = pd.to_datetime(raw["timestamp"], format=load.TIMESTAMP_FORMAT, errors="coerce")
    bad_ts = int((ts.isna() & raw["timestamp"].notna()).sum())
    if bad_ts:
        report.errors.append(f"timestamp: {bad_ts} values don't match {load.TIMESTAMP_FORMAT}")

    for col in ["amount_received", "amount_paid"]:
        amounts = pd.to_numeric(raw[col], errors="coerce")
        bad = int((amounts.isna() & raw[col].notna()).sum())
        if bad:
            report.errors.append(f"{col}: {bad} non-numeric values")
        non_positive = int((amounts <= 0).sum())
        if non_positive:
            report.errors.append(f"{col}: {non_positive} values are zero or negative")

    bad_labels = int((~raw["is_laundering"].isin(["0", "1"])).sum())
    if bad_labels:
        report.errors.append(f"is_laundering: {bad_labels} values not 0 or 1")

    for col in ["from_bank", "to_bank"]:
        bad = int((~raw[col].fillna("").str.fullmatch(r"\d+")).sum())
        if bad:
            report.errors.append(f"{col}: {bad} bank codes are not all digits")

    self_transfer = (raw["from_bank"] == raw["to_bank"]) & (
        raw["from_account"] == raw["to_account"]
    )
    padded = pd.concat([raw["from_bank"], raw["to_bank"]]).dropna().drop_duplicates()
    report.info = {
        "rows": len(raw),
        "duplicate_rows": int(raw.duplicated().sum()),
        "timestamp_min": str(ts.min()),
        "timestamp_max": str(ts.max()),
        "self_transfers": int(self_transfer.sum()),
        "bank_codes_as_written": int(padded.nunique()),
        "bank_codes_unpadded": int(load.normalise_bank_id(padded).nunique()),
    }
    return report


def check_accounts(
    raw: pd.DataFrame, header: list[str], transactions: pd.DataFrame | None = None
) -> ValidationReport:
    """Schema, completeness and key-uniqueness checks for the accounts file.

    If `transactions` (raw, all-string) is given, also checks that every account seen there is
    present in the accounts file.
    """
    report = ValidationReport()
    if header != load.ACCOUNT_HEADER:
        report.errors.append(f"unexpected header: {header}")

    nulls = raw.isna().sum()
    for col, n in nulls[nulls > 0].items():
        report.errors.append(f"{col}: {n} missing values")

    keys = pd.DataFrame(
        {"bank": load.normalise_bank_id(raw["bank_id"]), "account": raw["account_number"]}
    )
    duplicate_keys = int(keys.duplicated().sum())
    if duplicate_keys:
        report.errors.append(f"{duplicate_keys} duplicate (bank_id, account_number) keys")

    report.info = {"rows": len(raw)}

    if transactions is not None:
        seen = pd.concat(
            [
                pd.DataFrame({"bank": transactions[b], "account": transactions[a]})
                for b, a in [("from_bank", "from_account"), ("to_bank", "to_account")]
            ]
        )
        seen["bank"] = load.normalise_bank_id(seen["bank"])
        seen = seen.drop_duplicates()
        merged = seen.merge(keys.drop_duplicates(), how="left", indicator=True)
        missing = int((merged["_merge"] == "left_only").sum())
        if missing:
            report.errors.append(f"{missing} transacting accounts missing from accounts file")
        report.info["transacting_accounts"] = len(seen)
        report.info["accounts_without_transactions"] = len(raw) - (len(seen) - missing)
    return report


def check_patterns(lines: list[str]) -> ValidationReport:
    """Structure checks for the laundering patterns file.

    BEGIN/END blocks are balanced and not nested, and every transaction line inside a block has
    the transaction file's field count and a laundering label of 1.
    """
    report = ValidationReport()
    n_fields = len(load.TRANSACTION_HEADER)
    typologies: dict[str, int] = {}
    current = None

    for i, line in enumerate(lines, start=1):
        begin = PATTERN_BEGIN.match(line)
        if begin:
            if current is not None:
                report.errors.append(f"line {i}: BEGIN inside an unclosed block")
            current = begin.group(1)
            typologies[current] = typologies.get(current, 0) + 1
        elif line.startswith(PATTERN_END):
            if current is None:
                report.errors.append(f"line {i}: END without a matching BEGIN")
            current = None
        elif line.strip():
            if current is None:
                report.errors.append(f"line {i}: transaction outside a block")
            fields = line.split(",")
            if len(fields) != n_fields:
                report.errors.append(f"line {i}: {len(fields)} fields, expected {n_fields}")
            elif fields[-1] != "1":
                report.errors.append(f"line {i}: laundering label is {fields[-1]!r}, not '1'")

    if current is not None:
        report.errors.append("file ends inside an unclosed block")

    report.info = {
        "attempts": sum(typologies.values()),
        "attempts_by_typology": dict(sorted(typologies.items())),
    }
    return report


def validate_all() -> dict[str, ValidationReport]:
    """Run every check on the configured raw files; raise if any hard check fails."""
    config = load_config("data")
    transactions = load.load_raw_transactions()
    accounts = load.load_raw_accounts()
    rows = {"transactions": len(transactions), "accounts": len(accounts), "patterns": None}
    reports = {}
    for key, file_name in config["files"].items():
        reports[f"{key} file"] = check_expected(
            file_name, sha256(load.raw_file(key)), rows[key], config["expected"][file_name]
        )
    reports |= {
        "transactions": check_transactions(
            transactions, load.read_header(load.raw_file("transactions"))
        ),
        "accounts": check_accounts(
            accounts, load.read_header(load.raw_file("accounts")), transactions
        ),
        "patterns": check_patterns(load.load_pattern_lines()),
    }
    failures = {name: r.errors for name, r in reports.items() if not r.passed}
    if failures:
        raise ValidationError(json.dumps(failures, indent=2))
    return reports


def main() -> None:
    """Command-line entry point: validate and print each file's summary."""
    reports = validate_all()
    for name, report in reports.items():
        print(f"{name}: passed")
        print(json.dumps(report.info, indent=2))


if __name__ == "__main__":
    main()
