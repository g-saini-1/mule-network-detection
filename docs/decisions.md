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

## 2026-10-28: Adopt automated code-quality checks

- **Context:** Before Stage 2 adds rule and feature code, the only automated checks were ruff's
  default lint rules and the test suite. The 2026-10-26 entry deferred pre-commit hooks;
  `scope_and_rationale.md` Section 6 lists pytest, ruff, pre-commit and nbstripout as the dev
  tools. `pyproject.toml` allowed Python 3.11 while `.python-version` pins 3.12.
- **Options considered:** keep the current checks; add pre-commit, a wider ruff rule set, a type
  checker and CI now; add them later as needed. Type checker: mypy or pyright. Data schemas:
  `pandera` or hand-written column checks. Leakage tests: hand-picked examples only, or
  property-based tests with `hypothesis` as well.
- **Decision and rationale:** Add them now, before Stage 2, so new code starts under the
  standards rather than being brought up to them afterwards. This reverses the 2026-10-26
  deferral of pre-commit. Choices, set out in `docs/development.md`:
  - a wider ruff rule set and `ruff format`;
  - mypy on `src/`, chosen over pyright because it runs from the uv environment with no Node.js
    dependency and has mature pandas stubs (`pandas-stubs`); this adds mypy to the dev tools in
    `scope_and_rationale.md` Section 6;
  - pre-commit, with ruff and nbstripout run from the uv environment so `uv.lock` sets their
    versions;
  - GitHub Actions running `make check`;
  - Python 3.12 only, departing from the "3.11+" in `scope_and_rationale.md` Section 6; the
    project has only ever run on 3.12, and testing one version keeps CI simple.

  `pandera` (schemas at stage boundaries) and `hypothesis` (property-based leakage tests) are
  adopted from Stage 2, when the code they check is written. `pandera` checks a frame against a
  declared schema in one call, where hand-written checks would be repeated in every stage, and
  `hypothesis` tests the leakage rule over many generated cases rather than a few chosen ones.

## 2026-11-02: Keep `docs/` flat, with a naming convention

- **Context:** Adding `docs/solution_architecture.md` brings `docs/` to five documents and five
  figures. `docs/decisions.md` and `docs/backlog.md` are linked from many files, e.g.
  `scope_and_rationale.md`, which is frozen, and the Stage 1 report tagged in `v0.1`.
- **Options considered:** keep `docs/` flat with a naming convention; add sub-folders by document
  type now (e.g. `docs/explanation/`); add sub-folders by subject (e.g. `docs/architecture/`).
- **Decision and rationale:** Keep it flat, with the naming convention in `CLAUDE.md` ("Where
  information lives"). Sub-folders holding one or two files each would make documents harder to
  find, and moving the two most-linked files would break links that cannot all be fixed. The
  README's documentation table groups documents by type (explanation, plan and records,
  reference, how-to), loosely following the Diátaxis framework, so it serves as the index without
  a separate one. Revisit when the GitHub Pages site in `docs/backlog.md` is built, or if `docs/`
  grows past about ten documents; the README groups would then become the sub-folders.

## 2026-11-03: Move account labels into their own document

- **Context:** The account label rules R1 to R7, the label columns and the label counts sat in
  `data/README.md` ("Account labels") because labels were built in Stage 1, alongside data
  understanding. They define the target every later stage scores against, not a fact about the
  raw data.
- **Options considered:** keep them in `data/README.md`; move them to their own document in
  `docs/`.
- **Decision and rationale:** Move them to `docs/account_labelling_guide.md`, unchanged apart from
  headings, cross-links and table numbers (Tables 8 and 9 become Tables 1 and 2), and leave a
  pointer in `data/README.md`. References in earlier entries to "`data/README.md`, Account labels" now mean
  `docs/account_labelling_guide.md`; those entries are kept as written.

## 2026-11-19: Keep duplicate transactions and flag them

- **Context:** 9 transaction rows are exact copies of an earlier row (`data/README.md`, Table 7).
  None is laundering, a self-transfer or in the patterns file.
- **Options considered:** keep them unflagged; keep them with a flag; drop them.
- **Decision and rationale:** Keep them, with an `is_duplicate` flag on the later copies. No
  payment that might be real is deleted, the labels and rules see the same rows, and any rule can
  still exclude the flagged rows.

## 2026-11-19: Keep self-transfers and flag them

- **Context:** 591,212 transactions have the same sender and receiver account, 481,056 of them
  Reinvestment. Label rule R3 ignores laundering self-transfers, but the rules engine is a separate
  detector.
- **Options considered:** keep them unflagged; keep them with a flag; drop them.
- **Decision and rationale:** Keep them, with an `is_self_transfer` flag. Each rule's
  specification states whether it excludes them. A self-transfer neither receives money from nor
  passes money to anyone else, so pass-through rules exclude them; counting them would push money
  in and money out towards each other.

## 2026-11-19: Convert amounts to US Dollar with rates inferred from the data

- **Context:** Amounts are in 15 currencies, and 664 of 1,003 mules use more than one. The
  dataset has no exchange rates, but each cross-currency payment implies one.
- **Options considered:** compare amounts within each currency only; use published September 2022
  rates; infer rates from cross-currency payments.
- **Decision and rationale:** Infer one fixed rate per currency to US Dollar: the median rate of
  its direct pair with US Dollar, from payments of 100 or more. The simulator's rates are fixed,
  every currency has a direct pair with US Dollar, and converted paid and received amounts agree
  within 0.48% on those payments. US Dollar is the base because it is the most used currency; every
  currency has a direct pair with every other, so any base would work.

## 2026-11-19: Tag laundering payments with their scheme's typology

- **Context:** The Stage 2 plan commits to the rules and the temporal split only. A typology
  coverage matrix (`docs/backlog.md`) needs each laundering payment linked to its scheme's
  typology.
- **Options considered:** tag in data preparation now; tag later, when the coverage matrix is
  built.
- **Decision and rationale:** Tag in data preparation now, adding a scheme ID and a typology to
  each laundering payment found in the patterns file. It costs one extra step and keeps the
  prepared transactions as the single source for later stages. The tags are for evaluation only;
  the rules engine never reads them.

## 2026-11-20: Flag own-account transfers within a bank only

- **Context:** Pass-through rules can mistake an owner moving money between their own accounts
  for a mule. AMLworld links owners across all banks, but a real bank knows the owners of its own
  accounts only.
- **Options considered:** no flag; flag same-owner transfers at any bank; flag them within the
  same bank only.
- **Decision and rationale:** Flag them within the same bank only (`is_own_account_transfer`), so
  preparation uses only what a bank could know.

## 2026-11-27: Keep ground truth out of prepared transactions

- **Context:** Prepared transactions were to carry three columns for evaluation only:
  `is_laundering`, `scheme_id` and `typology`. Only a naming convention would keep them away from
  the rules engine. The solution architecture treats detection and ground truth as separate
  bounded contexts.
- **Options considered:** keep the columns in prepared transactions, marked evaluation only; move
  them to a separate transaction labels dataset keyed by `transaction_id`.
- **Decision and rationale:** Move them to a separate transaction labels dataset in the processed
  zone, built with the account labels by `make labels`. Detection's input then holds no ground
  truth, so these columns cannot leak into the rules. This supersedes the 2026-11-19 entry's point
  that prepared transactions are the single source for later stages; the typology coverage matrix
  joins the two datasets on `transaction_id`. Scheme tagging moves from the preparation rules to
  the transaction labelling rules, and the preparation rules are renumbered P1 to P8.

## 2026-11-27: Organise the package by bounded context

- **Context:** The solution architecture splits the system into bounded contexts (source data,
  payments, detection, and ground truth and evaluation), and detection must never read ground
  truth. The package was organised by technical layer, with source loading, payment rules and
  label building all under `data/`.
- **Options considered:** keep `data/` and split it into modules; one package per bounded
  context.
- **Decision and rationale:** One package per bounded context: `source/`, `payments/`,
  `detection/` and `evaluation/`, with `utils/` shared. Each context's boundary is then visible
  in the code, and the rule that detection never imports evaluation can be tested. Moving now
  costs less than later, when the rules engine adds modules. This replaces the `data/` layout
  planned in CLAUDE.md ("Architecture").

## 2026-11-27: Let source import payments, never the reverse

- **Context:** Transaction preparation in `source/` applies the payments rules (P4 to P6), so
  `source` imports `payments`. No rule said which way imports between the two may go, and an
  import in each direction would create a cycle.
- **Options considered:** allow `source` to import `payments` and never the reverse; move the
  preparation pipeline out of `source/` into a separate orchestration module.
- **Decision and rationale:** Allow `source` to import `payments`, and never the reverse. It keeps
  the agreed layout, and the payments rules stay pure functions on any transactions table. Moving
  the pipeline out of `source/` can be reconsidered when `detection/` adds a second pipeline. An
  import-boundary test covering this rule and "detection never imports evaluation" is added when
  `detection/` is created.

## 2026-11-27: Leave the laundering flag out of the duplicate comparison

- **Context:** P3 compared every column apart from `transaction_id`, so the laundering flag
  decided whether a row was a duplicate. Preparation is meant to use only what a bank could know
  (2026-11-20), and the flag is ground truth.
- **Options considered:** compare every column; compare a fixed list of source columns without
  the laundering flag.
- **Decision and rationale:** Compare a fixed list of source columns without the laundering flag,
  so a detection input never depends on ground truth and the result does not change with which
  columns happen to exist. On HI-Small the choice makes no difference: 9 rows are duplicates
  either way.

## 2026-11-27: Fail if the base currency is not US Dollar

- **Context:** The base currency is set in config, but the converted columns are named
  `amount_paid_usd` and `amount_received_usd`. Another base would silently mislabel them.
- **Options considered:** fail if the base is not US Dollar; rename the columns to a neutral
  name, e.g. `amount_paid_base`.
- **Decision and rationale:** Fail if the base is not US Dollar. The project uses US Dollar
  throughout and the currency conversion guide is written for it; a neutral name can follow if
  another base is ever needed.

## 2026-11-27: Infer exchange rates from the whole period for now

- **Context:** P6 infers rates from payments across the whole period, the test period as well,
  so amounts in earlier periods are converted with rates learned partly from later
  payments. While the simulator's rates are fixed, as the conversion consistency check tests,
  the effect is small, but it departs from point-in-time correctness.
- **Options considered:** keep whole-period rates and record the departure; infer rates from the
  train period only.
- **Decision and rationale:** Keep whole-period rates for now and record the departure in the
  currency conversion guide (Limitations). Revisit when the temporal split is built, when rates
  from the train period alone become possible.

## 2026-11-28: Use pandera for data contract checks

- **Context:** DEVELOPMENT.md ("Data") sets data contracts between contexts. The 2026-10-28
  decision adopted `pandera` after comparing it only with hand-written checks. Prepared
  transactions are written to Parquet, and whether the rules engine uses pandas or DuckDB is
  open ([backlog.md](backlog.md), Later stages).
- **Options considered:** pandera; hand-written pandas checks; Great Expectations; Pydantic;
  Soda Core; Frictionless Table Schema; the Data Contract CLI (Open Data Contract Standard).
- **Decision and rationale:** Use pandera, declaring each contract's schema as a
  `DataFrameModel`, for the checks made on pandas tables: the input to preparation and the
  prepared transactions before they are written to Parquet. It validates a whole table in one
  call, can report every failure at once, and runs inside pytest and `make check`. It supports
  pandas 3 from version 0.30.0; the installed 0.36.0 validated pandas 3.1 tables in a check on
  2026-11-28. Great Expectations and Soda Core are built for monitored pipelines and
  warehouses, Pydantic validates row by row, which is slow for millions of rows, and
  Frictionless and the Data Contract CLI add a separate YAML specification. Parquet keeps
  column names and storage types but not the contract's rules. How consumers check the
  contract when reading is left open, to be decided with the pandas or DuckDB choice for the
  rules engine.

## 2026-11-28: Name converted amounts for the base currency

- **Context:** The 2026-11-27 entry kept the converted columns as `amount_paid_usd` and
  `amount_received_usd` and failed on any other base currency. Names tied to one currency would
  have to change if the base ever changed.
- **Options considered:** keep the `_usd` names; rename to `amount_paid_base` and
  `amount_received_base` and keep US Dollar as the only allowed base; rename and allow any base.
- **Decision and rationale:** Rename to `amount_paid_base` and `amount_received_base`, and keep
  failing on any base other than US Dollar, now because it is the only base the method has been
  checked with. This supersedes the 2026-11-27 entry's choice of names; allowing another base
  would be a separate decision, with the checks re-run on it. No prepared file had been written,
  so no stored data changed.

## 2026-11-28: Reconcile prepared transactions with the raw file row by row

- **Context:** P8 was first built to compare the total amount paid and received per currency
  with the raw file, within a relative tolerance. Preparation never changes the amounts, so any difference points
  to a fault, e.g. rows dropped, duplicated or misaligned. Totals cannot catch faults that offset
  each other, e.g. two amounts swapped, and the tolerance allowed about 696 US Dollar of
  difference in the US Dollar total paid (10⁻⁹ of about 696 billion).
- **Options considered:** keep the totals with a tighter tolerance; compare each prepared row's
  amounts and currencies with its raw transaction by `transaction_id`; both.
- **Decision and rationale:** Compare row by row, exactly, with `transaction_id` required to run
  from 0 to one less than the number of raw rows. It catches everything the totals catch and
  offsetting faults as well, and needs no tolerance. On the real data the comparison itself,
  after the raw file is read, took 2.13 s against 1.72 s for the totals. Keeping the totals as
  well would add no protection, since matching rows imply matching totals.

## 2026-11-28: Write, audit, then publish the prepared transactions file

- **Context:** `make prepare-data` publishes prepared transactions, the first dataset passed
  between contexts with a data contract. A write that fails part way would leave a half-written
  file, and a failed run must not replace a good one.
  Writing to Parquet and reading back could also change a column's type without P8, which
  checks the table in memory, noticing.
- **Options considered:** write straight to the target; write to a temporary file and rename it
  (atomic write); write, audit the written file, then publish by renaming; success marker files
  or versioned outputs (e.g. Delta Lake, Apache Iceberg); lineage metadata in the file.
- **Decision and rationale:** Write, audit, publish: write to a temporary file beside the
  target, read it back and check it against the prepared transactions contract, then rename it
  onto the target, which is atomic on one file system. On the real data the audit took 0.44 to
  0.46 s (read back about 0.13 s, contract about 0.31 s) against about 1.1 s for the write.
  Success markers and versioned outputs are built for folders of many files written by many
  jobs; one file written by one job does not need them. Lineage metadata was not adopted. The
  written file is not forced to disk (`fsync`), so a power cut, unlike a failed run, could leave
  it cut short; the derived layers are rebuildable and the check on reading would reject such a
  file. `load_prepared_transactions` checks the full contract on reading, in pandas, which settles
  the consumer's check for pandas readers; for DuckDB it stays open (2026-11-28, "Use pandera for
  data contract checks").
