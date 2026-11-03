# Test strategy

**Status:** Draft, Stage 2

How the mule detection system is tested. Test levels follow the C4 views in
[solution_architecture.md](solution_architecture.md); the conventions for writing tests (file
layout, naming, markers) are in [DEVELOPMENT.md](../DEVELOPMENT.md) ("Tests").

## Purpose and scope

The strategy covers the mule detection application and its data stores. Non-functional testing,
e.g. performance and security testing, is out of scope: the system runs offline, in batch, on
synthetic public data.

## Principles

- **Shift-left.** Tests are written with or before the code. Static checks (formatting, lint,
  types) and schema checks catch defects before tests run, and the fastest checks run first.
- **Test pyramid.** Most tests are fast unit tests at code level; each level above has fewer,
  slower tests.
- **Risk-based focus.** Most testing effort goes where failure would cost most: the account
  labels, leakage across the scoring time, and the temporal split.
- **Traceable.** Every test names the rule or risk it covers.

## Test levels

![Figure 1. Test pyramid: test levels by C4 view, with the test types and test data at each level](figures/test_pyramid.svg)

Figure 1. The test pyramid for the mule detection system, marked by what is built so far and the
stage that starts each level.

| C4 level | Test level | What it checks | Test data | Share | From |
|---|---|---|---|---|---|
| Code | Unit | One function, e.g. a label rule or a rule condition | Hand-built frames | Most | Stage 1 |
| Component | Component | One component end to end, e.g. the rules engine on fixture tables | Fixture tables | Fewer | Stage 2 |
| Container | Integration | The application reading and writing the data zones, with schemas checked at each boundary | Fixture dataset | Few | Stage 2 |
| Context | End-to-end | The whole pipeline, from ingested files to evaluation output | Fixture dataset | Very few | *Pending* |

Table 1. Test levels by C4 view.

## Test types

| Type | What it checks | From |
|---|---|---|
| Functional | Each rule behaves as specified, e.g. label rules R1 to R7 | Stage 1 |
| Data validation | Downloaded files match their expected hashes, row counts and content | Stage 1 |
| Static analysis | Formatting, lint and types | Stage 1 |
| Regression | Every test runs on every change | Stage 1 |
| Schema | Data passed between stages, to the standard in [DEVELOPMENT.md](../DEVELOPMENT.md) ("Data") | Stage 2 |
| Leakage and point-in-time | Payments at or after the scoring time never change a feature or rule value, checked with property-based tests | Stage 2 |
| Machine learning | Data, model and infrastructure tests, following Google's ML Test Score rubric | Stage 3 |

Table 2. Test types and the stage each starts in.

## Test data

- **Hand-built frames** for unit tests: the few rows each test needs, never the downloaded data.
- **Fixture tables** for component tests: small tables shaped for the component under test.
- **A fixture dataset** for integration and end-to-end tests: small enough to run in CI. Its
  design is *Pending*.
- **The downloaded data** only in tests marked `data` ([DEVELOPMENT.md](../DEVELOPMENT.md),
  "Tests"). None exist so far.

## Quality gates

| Gate | When | Checks |
|---|---|---|
| Pre-commit | Every commit | Formatting, lint, notebook outputs stripped, large files and private keys |
| `make check` | Before code is handed over | Format check, lint, types and tests |
| CI | Every pull request and push to `main` | `make check`, without tests marked `data` |

Table 3. Quality gates, from fastest to slowest feedback.

The tools behind each check are listed in DEVELOPMENT.md ("Checks and tooling").
