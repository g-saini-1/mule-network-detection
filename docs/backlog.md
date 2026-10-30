# Backlog

Ideas and follow-ups parked outside the current stage. The scope document's own post-`v1.0`
items (GNN, simulated scam payments, BAF fairness audit, LI robustness check) are in
`scope_and_rationale.md` Section 3 and are not repeated here.

## Project tooling

- **`make docs-check` at the start of Stage 2.** A script for the mechanical documentation checks:
  links and section anchors resolve, file paths and `make` targets exist, house-style patterns
  (em-dashes, "include", common American spellings), personal email addresses and local paths,
  and placeholder words such as TODO or TBD.
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
- **Stage 2: write the rules in SQL.** Express each rule as a SQL query over the transactions, run
  from Python (e.g. with DuckDB), so the rules read like the detection scenarios bank monitoring
  teams write and tune. Needs a `docs/decisions.md` entry (tooling choice, new dependency) and
  tests that run each query on small fixture tables.
- **Stage 2: typology coverage matrix.** For each typology in the patterns file
  (`data/README.md`, Table 6), the share of its mule accounts each rule flags at the alert budget;
  uncovered typologies are the detection gaps. Needs a decision on attributing accounts to
  typologies: 38.01% of laundering transactions sit in no scheme (`data/README.md`, Patterns), so
  the matrix needs a "no typology" row, and one account can sit in schemes of several typologies.
- **Stage 2 and 3: the transactions file is not in time order.** Sort by timestamp before any
  rolling-window or as-at computation.
- **Stage 2 and 3: which label timestamp marks the leakage cut-off.** The first label version
  named one timestamp for leakage tests (`mule_since`, the first laundering payment). The final
  labels have both `mule_at` and `first_laundering_at`, and no decision yet says which one
  features must precede.
- **Stage 3: simulator artefacts.** ACH, Wire, Reinvestment and cross-currency signals are cleaner
  than real behaviour is likely to be; compare model performance with and without payment format
  and currency features.
- **Stage 3: add the model to the coverage matrix,** on the same split, alert budget and typology
  attribution as Stage 2, to show which gaps the model closes.
- **Stage 4: add ML with graph features to the coverage matrix,** for both the full and the
  partial view, to show which typologies network context helps with and how much of that survives
  when one bank sees only part of the network.
- **Stage 5: detection effectiveness report.** A one-page report generated from the code: for each
  detection approach (rules, ML, ML with graph features), alert volume at the budget, precision,
  recall, the false positive ratio (false positives per true mule) and the final coverage matrix.
  Section 3 commits Stage 5 to `model_card.md` and `business_case.md` only, so a
  `docs/decisions.md` entry should settle whether this is a separate report or a section of the
  business case.
- **Stage 5: scheme-starting accounts in the mule label.** The label cannot separate mules from
  accounts where a scheme starts and its money returns (e.g. the start of a cycle), because
  AMLworld's timestamps do not follow the money. If an error analysis needs them, identify them
  from the patterns file's scheme structure rather than from timestamps.
- **Backlog GNN: IBM Multi-GNN on Apple Silicon.** The repository's `env.yml` requires CUDA. A
  CPU environment for macOS would use Python 3.10, PyTorch and PyTorch Geometric from pip, and the
  PyG extension wheels for the matching PyTorch version; untested.
