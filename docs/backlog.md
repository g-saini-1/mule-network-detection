# Backlog

Ideas and follow-ups parked outside the current stage. The scope document's own post-`v1.0`
items (GNN, simulated scam payments, BAF fairness audit, LI robustness check) are in
`scope_and_rationale.md` Section 3 and are not repeated here.

## Project tooling

- **Pre-commit hooks.** ruff, nbstripout, end-of-file and trailing-whitespace hooks, as listed in
  `scope_and_rationale.md` Section 6 (deferred; see `docs/decisions.md`, 2026-10-26).
- **Command sandbox for Claude Code.** Revisit when either trigger applies: running third-party
  code (e.g. the IBM Multi-GNN repository), or switching to a permission mode with fewer prompts.

## Publishing

- **Project site on GitHub Pages.** Generate the site from the repository's Markdown with a
  documentation site generator (e.g. MkDocs), rebuilt on every push, so there is no second copy
  to maintain. Open decisions: making the repository public, publishing now or at `v1.0`, and
  which documents appear on the site.
- **Portfolio.** A personal GitHub Pages hub with one card per project, project sites for depth,
  and LinkedIn posts and articles adapted from the project site, which stays the canonical copy.
- **"How this was built" in the README at `v1.0`.** A short paragraph on how Claude Code was used
  as an assistant under a written working agreement (plans approved before code, every number
  verified by running code, independent reviews at each stage), since the agreement itself is
  kept locally and not committed.
- **Results chart for the README at `v1.0`.** Recall at a fixed alert budget, compared across the
  rules baseline, ML and ML with graph features.

## Later stages

- **Stage 2: the tail after 10 September.** Normal activity stops after 10 September, and the
  remaining days are mostly laundering, so the temporal split must not use them as a realistic
  test period (see `data/README.md`, Key characteristics).
- **Stage 2: when accounts are scored.** Labels can be built as at any point in time
  (`data/README.md`, Account labels, R6). Decide one scoring time rule for every account, mules
  and non-mules alike; giving only mules a cut-off would let a model learn from how much history
  each class has rather than from behaviour.
- **Stage 2: split by owner.** 637 of the 945 entities that own a mule account also own non-mule
  accounts, so a split by account could put one owner on both sides; consider splitting by owner.
- **Stage 2 and 3: the transactions file is not in time order.** Sort by timestamp before any
  rolling-window or as-at computation.
- **Stage 3: simulator artefacts.** ACH, Wire, Reinvestment and cross-currency signals are cleaner
  than real behaviour is likely to be; compare model performance with and without payment format
  and currency features.
- **Stage 5: scheme-starting accounts in the mule label.** The label cannot separate mules from
  accounts where a scheme starts and its money returns (e.g. the start of a cycle), because
  AMLworld's timestamps do not follow the money. If an error analysis needs them, identify them
  from the patterns file's scheme structure rather than from timestamps.
- **Backlog GNN: IBM Multi-GNN on Apple Silicon.** The repository's `env.yml` requires CUDA. A
  CPU environment for macOS would use Python 3.10, PyTorch and PyTorch Geometric from pip, and the
  PyG extension wheels for the matching PyTorch version; untested.
