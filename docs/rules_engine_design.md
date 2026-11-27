# Rules engine design

**Status:** Draft, Stage 2

The internal design of the rules engine, the detection component that scores accounts with
explainable rules. Where it sits in the system, its inputs and its outputs are in
[solution_architecture.md](solution_architecture.md).

![Figure 1. Internal design of the rules engine, with its inputs and outputs](figures/rules_engine_design.svg)

Figure 1. The parts follow a typical transaction monitoring design, trimmed to what AMLworld
supports. Account labels are never an input: only the evaluation harness reads them.

| Part | Responsibility | Project equivalent |
|---|---|---|
| Run controller | Sets the scoring time and lookback windows for a run | Scoring times from the temporal split |
| Window aggregation | Computes per-account values over each window, from transactions before the scoring time | Pure rule functions that take an `as_at` time ([DEVELOPMENT.md](../DEVELOPMENT.md), Code) |
| Population filter | Restricts each rule to the accounts it is meant for | e.g. account age from the first observed transaction, since AMLworld has no opening date |
| Rule evaluator | Applies thresholds and AND/OR logic, and keeps the values that triggered each hit | 3 to 5 account-level rules, with parameters in `configs/*.yaml` |
| Alert consolidation | Merges several rule hits on one account into one alert | One row per account per period |
| Prioritisation | Ranks alerts and cuts the queue at the alert budget K | A ranking rule, to be decided in Stage 2 |
| Run record | Records what produced each alert, so any result can be reproduced | To be confirmed |

Table 1. Parts of the rules engine and their project equivalents.

Alert suppression and case management are left out: AMLworld has no alert or investigation
history for them to act on
([bank_detection_architecture.md](bank_detection_architecture.md), Table 1). Whether rules are
written in Python or as SQL run with DuckDB is open ([backlog.md](backlog.md), Later stages); the
parts are the same either way.
