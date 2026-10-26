# Decisions

Non-trivial modelling, data and project decisions, in the order they were made. Each entry
follows the template in `scope_and_rationale.md` Section 6, with a colon in the heading in place
of the template's dash.

## 2026-10-24: Strip zero-padding from bank IDs

- **Context:** The transactions file pads bank codes inconsistently: `010` and `0010` both appear
  for bank 10. As written there are 30,528 bank codes; without padding, 30,470. The accounts file
  stores bank IDs unpadded, and no account appears under two different paddings.
- **Options considered:** keep codes as written; strip the padding and keep them as text; convert
  them to integers.
- **Decision and rationale:** Strip the padding and keep bank IDs as text
  (`load.normalise_bank_id`). This matches the accounts file and makes bank-level grouping
  correct, which Stage 4's partial-view test depends on. Account identity is unaffected either
  way. Text avoids any integer handling of identifiers.

## 2026-10-24: Name transaction columns by position

- **Context:** The transactions file header names two columns `Account` (sender, then receiver).
- **Options considered:** use pandas' automatic renaming (`Account`, `Account.1`); assign names by
  position after checking the header.
- **Decision and rationale:** Assign snake_case names by position (`from_account`, `to_account`,
  and so on). Validation first checks that the header matches the expected names in the expected
  order, and fails otherwise, so a reordered file cannot be silently mislabelled.

## 2026-10-24: Treat zero or negative amounts as a validation failure

- **Context:** A transfer amount should always be positive. The smallest amount in HI-Small is
  0.000001.
- **Options considered:** report zero or negative amounts as a warning; fail validation.
- **Decision and rationale:** Fail validation. The check never triggers on HI-Small, but it
  guards against a corrupted or changed download feeding later stages.

## 2026-10-26: Rename `make validate` to `make validate-data`

- **Context:** Stage 5 adds model validation, so a bare `validate` target would become ambiguous.
  `scope_and_rationale.md` Section 6 lists `validate` among the planned Makefile targets.
- **Options considered:** keep `validate`; rename now; rename when Stage 5 starts.
- **Decision and rationale:** Rename now to `validate-data`, while few files refer to it, and
  have `make data` run it after every download so unchecked data is never used. Later validation
  targets get their own specific names. This departs from the scope document's target list.

## 2026-10-26: Account-level mule label: receive and forward

- **Context:** The data flags individual payments, but the project scores accounts, so the
  payment flag has to become an account label. The EDA counted three candidates among the
  515,088 accounts that appear in at least one transaction: any involvement (6,357 accounts),
  receive and forward (1,003) and receiving side (3,984).
- **Options considered:** any involvement; receive and forward; receiving side.
- **Decision and rationale:** Receive and forward. An account is a mule if it both receives and
  sends at least one laundering transaction. This matches the project's definition of a mule
  account as one that receives and passes on illicit funds, and leaves out accounts that only
  send (likely sources) or only receive (likely end points). The cost is fewer positive examples,
  and some real mules whose onward payments are not flagged will be labelled negative. Details:
  - Laundering self-transfers are ignored when deciding whether an account receives and sends.
    On HI-Small this changes no labels (1,003 mules either way).
  - `mule_since` is the time of the account's first laundering transaction. Stage 3's leakage
    tests use it: features may only use information from before it.
  - Every account in at least one transaction is labelled; the 3,493 accounts that never transact
    are not scored.
  - Built by `make labels` into `data/processed/account_labels.parquet`
    (`src/mule_detection/data/labels.py`, tested in `tests/test_labels.py`).

## 2026-10-26: Keep the learning log outside this repository

- **Context:** `scope_and_rationale.md` Section 6 lists `docs/learning_log.md`, one entry per
  stage.
- **Options considered:** keep it in the repository; keep it locally but git-ignored; move it to a
  separate private journal repository; keep it in a notes tool.
- **Decision and rationale:** A separate private journal repository covering all projects. The
  log's value is to the owner, as a record of what was learned and a source of material for
  interviews and posts, rather than to readers of this repository; a private repository keeps
  working notes out of public view and still backs them up. `docs/learning_log.md` was removed.
  This departs from the scope document's repository structure.

## 2026-10-26: Defer pre-commit hooks

- **Context:** `scope_and_rationale.md` Section 7 lists pre-commit with ruff, nbstripout,
  end-of-file and trailing-whitespace hooks; the scaffold's `.pre-commit-config.yaml` was empty.
- **Options considered:** set up pre-commit now; defer it.
- **Decision and rationale:** Defer, and remove the empty file. `nbstripout` is installed directly
  as a git filter, which covers the rule that matters most (no notebook outputs in commits), and
  `make lint` runs ruff. Pre-commit is parked in `docs/backlog.md`.
