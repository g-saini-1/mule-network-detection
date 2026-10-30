# CLAUDE.md

Guidance for Claude Code in this repository. Writing style (no em-dashes, British spelling, no
second person, etc.) comes from the parent `CLAUDE.md` and isn't repeated here.

## Project

A self-directed learning project that detects money mule accounts (accounts that receive and pass
on illicit funds, e.g. scam proceeds) in bank transfer networks. It uses synthetic public data
(IBM AMLworld HI-Small), not production or real customer data. The owner is new to the
financial-crime domain, so domain concepts get plain-language explanations. The rationale, stage
plan and evaluation approach are in `scope_and_rationale.md`.

## Never

- **Never commit data, credentials or notebook outputs.** `data/` is git-ignored apart from
  `.gitkeep` and `data/README.md`; Kaggle credentials stay in `~/.kaggle/access_token`.
- **Never put personal email addresses or local machine paths in committed files.** The
  repository is public (github.com/g-saini-1/mule-network-detection, MIT licence).
- **Never edit `scope_and_rationale.md`.** It is the frozen upfront plan and only the owner edits
  it. Results, choices made along the way and scope changes go in `reports/` and
  `docs/decisions.md`.
- **Never write a number that wasn't produced by running the code.** If a figure can't be
  verified, say so instead of writing a placeholder.
- **Never create placeholder or empty files.** Create each module, test, config, notebook and
  report when its stage starts, following the layout under Architecture.

## Current state

- **Stage 1 (data understanding) is closed:** merged to `main` and tagged `v0.1`. Next is Stage 2
  (rules baseline), starting with concepts before code; Stage 2 notes are in `docs/backlog.md`.
- **Labels:** load with `mule_detection.data.labels.load_labels()`. Rules R1 to R7 are in
  `data/README.md` ("Account labels"). Payment order is ignored because AMLworld's timestamps
  within a scheme don't follow the money, so don't build rules on payment order without checking
  this first.
- **Environment:** `uv` with Python 3.12, virtual environment in `.venv`. Only Stage 1
  dependencies are installed so far.

## Commands

```bash
make setup          # install dependencies (uv sync)
make data           # download the HI-Small files into data/raw (skipping unchanged files), then validate
make validate-data  # run validation checks on the raw files only
make labels         # build account-level mule labels into data/processed/account_labels.parquet
make test           # run the test suite
make lint           # ruff check on src and tests
make format         # ruff format src and tests in place
make typecheck      # mypy on src
make check          # format check, lint, type check and tests (what CI runs)
```

- **Definition of done for code:** `make check` passes before handing over. Coding and testing
  standards are in `DEVELOPMENT.md`.
- **Planned targets:** `make rules`, `make train`, `make graph`, `make evaluate`. Add each here
  only once the Makefile wires it up.
- **Run a notebook from the terminal**, keeping the repository copy free of outputs:
  `uv run jupyter nbconvert --to notebook --execute notebooks/01_eda.ipynb --output-dir <dir>`.

## Architecture

- **Staged pipeline:** Stage 1 (data understanding), Stage 2 (rules baseline), Stage 3 (ML
  model), Stage 4 (graph features), Stage 5 (validation and business case, `v1.0`). Each stage's
  "learn", "build" and "done when" are set in `scope_and_rationale.md` Section 3; code implements
  only what that section commits to. Backlog items (GNN, simulated scam payments, BAF fairness
  audit, LI robustness check) wait until after `v1.0`.
- **One unit, one label, one split:** scoring is at account level, the label comes from Stage 1,
  and the temporal train/validation/test split is fixed in Stage 2 and reused unchanged, so each
  stage's lift over the previous one is a fair comparison.
- **Installed package:** `src/mule_detection/`, imported normally (e.g.
  `from mule_detection.data import load`). Target submodules: `data/` (download, load, validate,
  labels), `rules/`, `features/` (account, velocity, graph), `models/` (train, predict),
  `evaluation/` (metrics, costs, thresholds, stability), `utils/` (config).
- **Config, not code:** paths, split dates, rule thresholds and cost assumptions live in
  `configs/*.yaml`, read with `mule_detection.utils.config.load_config()` and resolved with
  `repo_path()`.
- **Data access:** datasets are downloaded only through `src/mule_detection/data/download.py`.
- **Notebooks** follow the stages: `01_eda`, `02_rules_baseline`, `03_ml_model`,
  `04_graph_features`, `05_validation`.
- **Reports:** each stage adds `reports/stageN_<name>.md` (contents set in `WORKFLOW.md`), linked
  from the README's stage table.
  `model_card.md` and `business_case.md` are written in Stage 5 from actual run output.

## Where information lives

| Document | Owns |
|---|---|
| `scope_and_rationale.md` | Upfront plan: rationale, stage objectives, evaluation approach (frozen) |
| `data/README.md` | Data facts and figures, label rules R1 to R7, validation results, limitations |
| `docs/decisions.md` | Why each decision was made, with options considered; history kept as written |
| `docs/backlog.md` | Parked ideas and open questions for later stages |
| `WORKFLOW.md` | The steps each stage follows, from branch to release tag |
| `DEVELOPMENT.md` | Coding, testing, data and reproducibility standards |
| `reports/stageN_*.md` | What each stage found and what it means next; links for detail |
| `README.md` | Project summary, status and navigation |
| Code docstrings and test names | Cite rule numbers; don't restate reasoning |

Table 1. Which document owns each kind of information.

`docs/domain_primer.md` is the owner's domain explainer; leave its content to the owner.
`docs/bank_detection_architecture.md` shows a typical bank detection pipeline and what AMLworld
covers.

## How to work

Each stage follows the steps in `WORKFLOW.md`, imported below so it loads in every session:

@WORKFLOW.md

On top of it:

1. **One stage at a time**, and only the stage asked for.
2. **Plan, then wait.** State the plan and the files to change, then wait for explicit
   confirmation. Never propose and execute in the same turn.
3. **Suggest, don't decide.** For each assumption, suggest a `docs/decisions.md` entry (template
   at the top of that file) for the owner to confirm.

## Personas

Work in one of six personas, named when it matters (e.g. "As validator: ..."). The owner can ask
for one directly. Honesty rules and the working rules above apply in every persona.

| Persona | Covers |
|---|---|
| Domain educator | AML and mule concepts, typologies, how banks detect mules |
| Financial crime practitioner | Bank fraud and AML practice: scenario tuning and coverage, alert capacity, operational metrics, governance |
| Data scientist | EDA, splits, features, leakage, models, graph features, cost and alert-budget analysis |
| Engineer | Data pipeline, package and tests, git commands for the owner, credentials and permissions |
| Independent validator | Challenges claims, leakage and synthetic-data artefacts |
| Communicator | README, data and model documentation, decisions log, later LinkedIn content |

Table 2. Personas used in this project.

- **The domain educator explains from public sources** (AUSTRAC, FATF, NASC, the IBM AMLworld
  paper). It isn't a compliance authority, and its explanations aren't claims of domain expertise.
- **The financial crime practitioner reviews from public sources** (AUSTRAC, FATF, NASC, APRA,
  model risk guidance). It approximates a practitioner's view and doesn't replace one.
- **The practitioner and validator stay separate from the builder.** Self-review leans towards
  agreement, so their end-of-stage reviews (`WORKFLOW.md`) offer a fresh-context review when the
  owner wants stronger independence.
