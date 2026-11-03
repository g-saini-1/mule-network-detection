# Solution architecture

**Status:** Draft, Stage 2

How this project's own detection system is put together: its main parts, the rules engine inside
it, and how data moves from download to reported results.
[bank_detection_architecture.md](bank_detection_architecture.md) describes the generic bank
pipeline this mirrors and which parts AMLworld covers; this document describes only what the
project builds.

The views follow the C4 model, which describes software at increasing levels of zoom: system
context (the system and what sits around it), containers (the parts that run or store data on
their own) and components (the building blocks inside one container). The data design is a
layered data architecture, in which each layer is built only from the layer before it.

## System context

The mule detection system takes in transaction data and scores accounts. At this point its only
external system is its data source.

| External system | Role |
|---|---|
| Kaggle | Source of the AMLworld HI-Small transactions, accounts and laundering patterns, downloaded by script |

Table 1. External systems the mule detection system depends on.

## Containers

| Container | Type | Technology | Responsibility | Stage |
|---|---|---|---|---|
| Mule detection application | Batch application | Python, run one job at a time | Ingests and prepares data, builds labels, scores accounts and evaluates the scores | 1 to 5 |
| Raw zone | Data store | Files as downloaded | Holds the source files unchanged | 1 |
| Interim zone | Data store | Parquet files | Holds prepared transactions | 2 |
| Processed zone | Data store | Parquet files | Holds account labels, the temporal split and scores | 1, 2 |

Table 2. Containers of the mule detection system.

## Components

The mule detection application is made up of the components below; the application's code is
organised the same way.

| Component | Responsibility | Stage |
|---|---|---|
| Data ingestion and validation | Download the source files and check hashes, row counts and content | 1 |
| Data preparation | Load typed data, build account labels and write prepared transactions | 1, 2 |
| Rules engine | Score accounts with explainable rules | 2 |
| Feature pipeline | Account, velocity and graph features | 3, 4 |
| ML model | Train and score the account model | 3 |
| Evaluation harness | Temporal split, metrics at the alert budget, costs, thresholds and stability | 2 to 5 |

Table 3. Components of the mule detection application.

## Detection pipeline

![Figure 1. This project's detection pipeline, marked by what is built and which stage builds each part](figures/solution_pipeline.svg)

Figure 1. The mule detection system's pipeline from source data to evaluation, marked by what is
built so far and the stage that builds each part.

## Data architecture

![Figure 2. The project's data layers and the lineage between them](figures/data_layers.svg)

Figure 2. Arrows show lineage: the datasets each one is built from.

Four principles shape the layers:

- **Immutable raw zone.** Files stay as downloaded and are checked against their expected file
  hashes and row counts ([data/README.md](../data/README.md), Validation).
- **Rebuildable derived layers.** Every interim and processed dataset is rebuilt by script from
  earlier layers and never edited by hand, so the derived layers can be deleted and rebuilt
  without loss.
- **Schemas at layer boundaries.** From Stage 2, data passed between stages is checked against a
  declared schema ([DEVELOPMENT.md](../DEVELOPMENT.md), Data).
- **Only aggregates are committed.** No data file enters the repository
  ([scope_and_rationale.md](../scope_and_rationale.md) Section 4); reports hold summary results.

The raw datasets, their entities and the relationships between them are described in
data/README.md, with an entity relationship diagram under Structure.

| Dataset | Zone | Contents | Built by | Used by |
|---|---|---|---|---|
| Transactions, accounts and patterns | Raw | Source files as downloaded | Data ingestion and validation | Data preparation |
| Download manifest | Raw | Record of each download | Data ingestion and validation | Data ingestion and validation |
| Prepared transactions | Interim | The transactions with proper data types, sorted by time, and each laundering payment tagged with its scheme's typology | Data preparation, Stage 2 | Rules engine, feature pipeline |
| Account labels | Processed | One row per account: whether it is a mule, and when it was first involved in laundering | Data preparation | Evaluation harness |
| Temporal split | Processed | Each account's period (train, validation or test) and its scoring time | Evaluation harness, Stage 2 | Rules engine, ML model, evaluation harness |
| Rule scores | Processed | For each account and period: the rules that fired, the values that triggered them, and the account's rank against the alert budget | Rules engine, Stage 2 | Evaluation harness |

Table 4. Datasets: what each holds, which component builds it and which use it.

## Rules engine design

![Figure 3. Internal design of the rules engine, with its inputs and outputs](figures/rules_engine_design.svg)

Figure 3. The parts follow a typical transaction monitoring design, trimmed to what AMLworld
supports. Account labels are never an input: only the evaluation harness reads them.

| Part | Responsibility | Project equivalent |
|---|---|---|
| Run controller | Sets the scoring time and lookback windows for a run | Scoring times from the temporal split |
| Window aggregation | Computes per-account values over each window, from transactions before the scoring time | Pure rule functions that take an `as_at` time ([DEVELOPMENT.md](../DEVELOPMENT.md), Code) |
| Population filter | Restricts each rule to the accounts it is meant for | e.g. account age from the first observed transaction, since AMLworld has no opening date |
| Rule evaluator | Applies thresholds and AND/OR logic, and keeps the values that triggered each hit | 3 to 5 account-level rules, with parameters in `configs/*.yaml` |
| Alert consolidation | Merges several rule hits on one account into one alert | One row per account per period |
| Prioritisation | Ranks alerts and cuts the queue at the alert budget K | A ranking rule, to be decided in Stage 2 |
| Run record | Records what produced each alert, so any result can be reproduced | Config and git tag in Stage 2; a run manifest from Stage 3 (DEVELOPMENT.md, Reproducibility) |

Table 5. Parts of the rules engine and their project equivalents.

Alert suppression and case management are left out: AMLworld has no alert or investigation
history for them to act on
([bank_detection_architecture.md](bank_detection_architecture.md), Table 1). Whether rules are
written in Python or as SQL run with DuckDB is open ([backlog.md](backlog.md), Later stages); the
parts are the same either way.

## Evaluation and backtesting

The evaluation harness plays the part of the backtesting environment a bank uses to test rule
changes on past data before they go live.

- **Point-in-time correctness.** Each period of the temporal split has a scoring time. Rules and
  features see only transactions before it, the same cut-off the labels use
  ([account_labelling_guide.md](account_labelling_guide.md), R6), and the label for that period
  comes from an outcome window after it.
- **Tuning and testing kept apart.** Rule thresholds and model settings are chosen on the train
  and validation periods. The test period is scored once, for the stage's reported result.
- **Champion and challenger.** Every detector writes scores in the same shape, so each stage's
  challenger is compared with the previous stage's champion on the same unit, label, split and
  alert budget ([scope_and_rationale.md](../scope_and_rationale.md) Section 5).

The open choices that fix the split, e.g. the tail after 10 September, one scoring time rule for
every account and splitting by owner, are in [backlog.md](backlog.md) (Later stages).

## Cross-cutting concerns

| Concern | How it is handled | Where it is set out |
|---|---|---|
| Configuration | Values live in `configs/*.yaml`, read with `load_config()` and resolved with `repo_path()` | [DEVELOPMENT.md](../DEVELOPMENT.md), Code |
| Reproducibility | File hashes and row counts, a release tag per stage, and a run manifest from Stage 3 | DEVELOPMENT.md, Reproducibility |
| Quality | `make check` runs a format check, lint, type checks and tests, locally and in CI | DEVELOPMENT.md, Checks and tooling |
| Data security and licence | No data or credentials committed; credentials stay at `~/.kaggle/access_token` | [scope_and_rationale.md](../scope_and_rationale.md) Section 4 |
| Change control | A branch per stage, reviews before merge, and a decision log | [WORKFLOW.md](../WORKFLOW.md) |

Table 6. Cross-cutting concerns and where each is set out.

## Architecture decisions

[decisions.md](decisions.md) is the project's decision log, in the style of architecture decision
records: each entry gives the context, the options considered and the rationale. This document
shows the resulting design and links to entries rather than restating them.
