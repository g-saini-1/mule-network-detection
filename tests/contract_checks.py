"""A helper for data contract tests: which rules a table breaks, shared by the test files."""

import re

import pandera.pandas as pa

# Checks pandera reports against the whole table, naming the column in the failure case.
_COLUMN_SET_CHECKS = {"column_in_dataframe", "column_in_schema", "column_ordered"}


def broken_rules(contract, tx):
    """The (column, check) pairs `contract` reports for `tx`; empty if `tx` meets it.

    Built-in checks lose their arguments, e.g. `greater_than(0)` becomes `greater_than`. A check
    on the column set is reported against the column it names; a check on the whole table
    against the contract's name; a custom check by its error message.
    """
    try:
        contract.validate(tx, lazy=True)
    except pa.errors.SchemaErrors as error:
        rules = set()
        cases = error.failure_cases[["column", "check", "failure_case"]]
        for column, check, failure_case in cases.itertuples(index=False):
            name = re.sub(r"\(.*\)$", "", check) if re.match(r"^\w+\(", check) else check
            rules.add((failure_case if name in _COLUMN_SET_CHECKS else column, name))
        return rules
    return set()
