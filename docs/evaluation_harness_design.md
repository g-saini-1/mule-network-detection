# Evaluation harness design

**Status:** Draft, Stage 2

The internal design of the evaluation harness, the component that measures detection against
the ground truth. Where it sits in the system, its inputs and its outputs are in
[solution_architecture.md](solution_architecture.md).

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
