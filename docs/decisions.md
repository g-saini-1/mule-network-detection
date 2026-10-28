# Decisions

Non-trivial modelling, data and project decisions, in the order they were made. Each entry uses
this template:

```
## <date>: <decision>
- Context:
- Options considered:
- Decision and rationale:
```

Section references in older entries mean the scope document as it was when the entry was
written; git history keeps those versions.

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
  The scope document's repository structure listed `validate` among the planned Makefile targets.
- **Options considered:** keep `validate`; rename now; rename when Stage 5 starts.
- **Decision and rationale:** Rename now to `validate-data`, while few files refer to it, and
  have `make data` run it after every download so unchecked data is never used. Later validation
  targets get their own specific names. This departs from the scope document's target list.

## 2026-10-26: Account-level mule label: receive and forward

*Superseded by "Mule label refined to receive, then pass on" below.*

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

## 2026-10-26: Defer pre-commit hooks

- **Context:** `scope_and_rationale.md` Section 6 lists pre-commit with ruff, nbstripout,
  end-of-file and trailing-whitespace hooks; the scaffold's `.pre-commit-config.yaml` was empty.
- **Options considered:** set up pre-commit now; defer it.
- **Decision and rationale:** Defer, and remove the empty file. `nbstripout` is installed directly
  as a git filter, which covers the rule that matters most (no notebook outputs in commits), and
  `make lint` runs ruff. Pre-commit is parked in `docs/backlog.md`.

## 2026-10-26: Mule label refined to receive, then pass on

*Superseded by "Mule label returned to both directions, order ignored" below. Its reading of the
104 "send first" accounts as organisers assumed that timestamps follow the money, which a
follow-up review showed they do not; its statement that only the 50 accounts where a cycle
starts and ends fail the rule was also inaccurate (only 40 of the 50 send the first payment in
their cycle). The context below also misdescribes the 104: they are the accounts with no
laundering send after their first receipt, not all accounts that sent first (141 mules sent
first, and some of those sent again after receiving). References to R4 and R6 below mean those
rules as worded at the time; R4 now states the order-ignored rule.*

- **Context:** An independent validator review found two problems with the first label. It
  ignored the order of payments: 104 of its 1,003 mules sent laundering money before ever
  receiving any, behaving like the start of a scheme whose money comes back (e.g. where a cycle
  begins and ends) rather than a mule passing money on. And it was built from all 18 days with
  one timestamp per account, so it could not say whether an account was a mule as at an earlier
  point in time: using only payments before 11 September, 795 accounts had both received and
  sent, against 1,003 using all the data.
- **Options considered:** keep the first rule and document the 104 accounts; require a
  laundering send after the first laundering receipt (strict); label the whole receiving side
  (3,984 accounts), which is closer to the broad way banks label mules from confirmed cases but
  also counts end-point accounts the data cannot classify.
- **Decision and rationale:** Strict. An account is a mule if it sends a laundering payment
  after its first laundering receipt (`data/README.md`, Account labels, R4), giving 899 mules of
  515,088 accounts. This matches the project's definition of a mule and keeps one behaviour
  under one label. It does not stop cycle-type schemes being detected: of the 271 accounts in
  the 54 cycle schemes, 221 meet the strict rule and only the 50 where a cycle starts and ends
  do not. The labels now also record `mule_at`, `first_laundering_at`, `first_received_at` and
  `first_sent_at`, so the 104 organiser-like accounts stay identifiable, and can be built as at
  any point in time (R6). How later stages score accounts over time is left to Stage 2.

## 2026-10-26: Mule label returned to both directions, order ignored

- **Context:** A follow-up validator review found that AMLworld does not timestamp the payments
  within a laundering scheme in the order the money moves. In the patterns file, accounts send
  before they receive within their own scheme in five of the eight typologies (counted as
  account and scheme pairs: 65 in cycle schemes, 43 in scatter-gather, 23 in gather-scatter, 15
  in stack, 3 in random). In scatter-gather schemes the middle accounts must receive before
  passing money on, yet e.g. `213952:806D47B10` sends on 1 September 08:40 and receives on
  2 September 13:04 in the same scheme. The strict rule therefore labelled some real middle accounts as non-mules because of
  a simulator artefact rather than behaviour.
- **Options considered:** keep the strict rule and describe it as "order as timestamped",
  accepting known label errors; return to the order-ignored rule.
- **Decision and rationale:** Return to the order-ignored rule: an account is a mule if it
  receives and sends at least one laundering payment, in either order (`data/README.md`, Account
  labels, R4), giving 1,003 mules of 515,088 accounts. A rule should not depend on a signal the
  data cannot support. The cost is that some accounts where a scheme starts and its money
  returns (e.g. the start of a cycle) are labelled mules; the data cannot reliably tell them
  apart, and counting them is closer to the broad way banks label mules from confirmed cases.
  The timing columns and `as_at` cut-off are kept; `mule_at` is now the later of the account's
  first laundering receipt and first laundering send. As at 11 September 00:00 there are 795
  mules, and 208 mules first meet the rule on or after 11 September. Rules R1 to R3, R6 and R7
  (`data/README.md`, Account labels) carry over unchanged from the earlier label entries.
