# Solution architecture

**Status:** Draft, Stage 2

How this project's own detection system is put together: its main parts, how they are grouped
into bounded contexts, and how data moves from download to reported results.
[bank_detection_architecture.md](bank_detection_architecture.md) describes the generic bank
pipeline this mirrors and which parts AMLworld covers; this document describes only what the
project builds.

The views follow the C4 model, which describes software at increasing levels of zoom: system
context (the system and what sits around it), containers (the parts that run or store data on
their own) and components (the building blocks inside one container). The domain model follows
domain-driven design: the system is split into bounded contexts, each owning one part of the
domain and its terms. The data design is a layered data architecture, in which each layer is
built only from the layer before it.

## System context

The mule detection system takes in transaction data and scores accounts. At this point its only
external system is its data source.

| External system | Role |
|---|---|
| Kaggle | Source of the AMLworld HI-Small transactions, accounts and laundering patterns, downloaded by script |

Table 1. External systems the mule detection system depends on.

## Containers

| Container | Type | Technology | Responsibility |
|---|---|---|---|
| Mule detection application | Batch application | Python, run one job at a time | Ingests and prepares data, builds labels, scores accounts and evaluates the scores |
| Raw zone | Data store | Files as downloaded | Holds the source files unchanged |
| Interim zone | Data store | Parquet files | Holds prepared transactions |
| Processed zone | Data store | Parquet files | Holds account and transaction labels, the temporal split and scores |

Table 2. Containers of the mule detection system.

## Components

The mule detection application is made up of the components below. Each belongs to one bounded
context (Table 4), and the application's code is organised by context. A component's internal
design, where it has one, is in its own design document.

| Component | Responsibility | Design |
|---|---|---|
| Data ingestion and validation | Download the source files and check hashes, row counts and content | |
| Transaction preparation | Load typed transactions, apply the preparation rules and write prepared transactions | |
| Payment rules | Flag self-transfers and own-account transfers, and give both amounts in the base currency ([transaction_preparation_guide.md](transaction_preparation_guide.md), P4 to P6) | |
| Rules engine | Score accounts with explainable rules | [rules_engine_design.md](rules_engine_design.md) |
| Feature pipeline | Account, velocity and graph features | |
| ML model | Train and score the account model | |
| Ground truth | Build account labels from typed transactions, and transaction labels from typed transactions and the patterns file ([account_labelling_guide.md](account_labelling_guide.md), [transaction_labelling_guide.md](transaction_labelling_guide.md)) | |
| Evaluation harness | Temporal split, metrics at the alert budget, costs, thresholds and stability | [evaluation_harness_design.md](evaluation_harness_design.md) |

Table 3. Components of the mule detection application.

## Domain model

Each bounded context owns one part of the domain and its terms, and passes data to another
context only through the datasets in Table 6, or through source data's typed loader. All four contexts run inside the mule detection
application: they are boundaries of meaning and ownership within one container, not separate
deployments. The data stores are shared and organised by how refined the data is; each dataset
belongs to the context of the component that builds it (Table 6).

| Context | Responsibility | Components |
|---|---|---|
| Source data | Turns the source files into clean, typed records: validated, with a stable transaction ID, duplicates flagged and in time order. It is the anti-corruption layer that keeps the source's quirks out of the other contexts | Data ingestion and validation, transaction preparation |
| Payments | Holds the banking rules about payments, apart from how the source data records them: what kind of transfer each payment is, and its amounts in the base currency | Payment rules |
| Detection | Scores accounts from prepared transactions | Rules engine, feature pipeline, ML model |
| Ground truth and evaluation | Records what is known to be laundering, and measures detection against it | Ground truth, evaluation harness |

Table 4. Bounded contexts and the components in each.

![Figure 1. The bounded contexts of the mule detection system and the flows between them](figures/solution_pipeline.svg)

Figure 1. The bounded contexts and the flows between them.

Three rules govern how the contexts relate ([decisions.md](decisions.md), 2026-11-27):

- **Detection never reads ground truth.** No flow runs from ground truth to detection; only the
  evaluation harness reads the labels.
- **Source data uses payments, never the reverse.** Transaction preparation applies the payment
  rules, and the payment rules depend on no other context.
- **Detection takes only scoring times from evaluation.** The temporal split sets when each
  account is scored; the labels stay in evaluation.

The terms below have one meaning across every context.

| Term | Meaning | Set out in |
|---|---|---|
| Account | A bank ID plus an account number | [account_labelling_guide.md](account_labelling_guide.md), R1 |
| Entity | The owner of one or more accounts | [transaction_preparation_guide.md](transaction_preparation_guide.md), P5 |
| Transaction | One record in the source transactions file, identified by its transaction ID | P1 |
| Payment | The movement of money a transaction records: from a sending account to a receiving account, in a payment currency and a receiving currency | [data/README.md](../data/README.md), Transactions |
| Self-transfer | A payment from an account to itself | P4 |
| Own-account transfer | A payment between two accounts of the same entity at the same bank | P5 |
| Base currency | The one currency every amount is also given in | [currency_conversion_guide.md](currency_conversion_guide.md) |
| Laundering payment | A payment whose transaction has a laundering flag of 1 | R2 |
| Mule | An account that receives at least one laundering payment and sends at least one | R4 |
| Scheme | One laundering attempt in the patterns file | [transaction_labelling_guide.md](transaction_labelling_guide.md), T2 |
| Typology | The pattern a scheme follows, e.g. fan-in or cycle | T2 |
| Scoring time | The time an account is scored at; detection sees only transactions before it | [evaluation_harness_design.md](evaluation_harness_design.md) |
| Alert budget | The fixed number of alerts, K, at which the alert queue is cut | [scope_and_rationale.md](../scope_and_rationale.md) Section 5 |

Table 5. Domain terms and where each is set out.

## Data architecture

![Figure 2. The project's data layers and the lineage between them](figures/data_layers.svg)

Figure 2. Arrows show lineage: the datasets each one is built from.

Four principles shape the layers:

- **Immutable raw zone.** Files stay as downloaded and are checked against their expected file
  hashes and row counts ([data/README.md](../data/README.md), Validation).
- **Rebuildable derived layers.** Every interim and processed dataset is rebuilt by script from
  earlier layers and never edited by hand, so the derived layers can be deleted and rebuilt
  without loss.
- **Data contracts between contexts.** Each dataset passed from one bounded context to another
  is checked against its data contract: its schema and quality rules
  ([DEVELOPMENT.md](../DEVELOPMENT.md), Data).
- **Only aggregates are committed.** No data file enters the repository
  ([scope_and_rationale.md](../scope_and_rationale.md) Section 4); reports hold summary results.

The raw datasets, their entities and the relationships between them are described in
data/README.md, with an entity relationship diagram under Structure.

| Dataset | Zone | Contents | Built by | Used by |
|---|---|---|---|---|
| Transactions, accounts and patterns | Raw | Source files as downloaded | Data ingestion and validation | Transaction preparation, ground truth |
| Download manifest | Raw | Record of each download | Data ingestion and validation | Data ingestion and validation |
| Prepared transactions | Interim | Transactions standardised for detection ([transaction_preparation_guide.md](transaction_preparation_guide.md)) | Transaction preparation | Rules engine, feature pipeline |
| Account labels | Processed | One row per account: whether it is a mule, and when it was first involved in laundering | Ground truth | Evaluation harness |
| Transaction labels | Processed | One row per transaction: whether it is laundering, and its scheme and typology where known ([transaction_labelling_guide.md](transaction_labelling_guide.md)) | Ground truth | Evaluation harness |
| Temporal split | Processed | Each account's period (train, validation or test) and its scoring time | Evaluation harness | Rules engine, ML model, evaluation harness |
| Rule scores | Processed | For each account and period: the rules that fired, the values that triggered them, and the account's rank against the alert budget | Rules engine | Evaluation harness |

Table 6. Datasets: what each holds, which component builds it and which use it.

## Cross-cutting concerns

| Concern | How it is handled | Where it is set out |
|---|---|---|
| Configuration | Values live in `configs/*.yaml`, read with `load_config()` and resolved with `repo_path()` | [DEVELOPMENT.md](../DEVELOPMENT.md), Code |
| Reproducibility | File hashes and row counts, and a release tag per stage | [data/README.md](../data/README.md), Validation |
| Quality | `make check` runs a format check, lint, type checks and tests, locally and in CI | DEVELOPMENT.md, Checks and tooling |
| Currency | Amounts are kept as recorded and also given in one base currency; rule thresholds state their currency | [currency_conversion_guide.md](currency_conversion_guide.md) |
| Data security and licence | No data or credentials committed; credentials stay at `~/.kaggle/access_token` | [scope_and_rationale.md](../scope_and_rationale.md) Section 4 |
| Change control | A branch per stage, reviews before merge, and a decision log | [WORKFLOW.md](../WORKFLOW.md) |

Table 7. Cross-cutting concerns and where each is set out.

## Architecture decisions

[decisions.md](decisions.md) is the project's decision log, in the style of architecture decision
records: each entry gives the context, the options considered and the rationale. This document
shows the resulting design and links to entries rather than restating them.
