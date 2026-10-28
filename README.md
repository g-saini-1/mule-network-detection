# Money mule detection

Detecting money mule accounts (bank accounts that receive and pass on illicit funds, e.g. scam
proceeds) in bank transfer networks, using AMLworld, IBM's synthetic dataset of bank
transactions with known laundering.

**Status:** self-directed learning project. Stage 1 (data understanding) is complete; Stage 2
(rules baseline) is next. Results come from synthetic data and are illustrative only, not claims
of production performance.

![A bank's mule detection pipeline, marked by what this project's data covers and which stage builds each part](docs/figures/detection_pipeline.svg)

Figure 1. A typical bank mule-detection pipeline, marked by what the AMLworld dataset covers.
Stage tags (S2 to S5) mark the parts this project builds; dashed boxes have no equivalent in the
dataset.

**How banks detect mule accounts, and what this dataset can and can't show:**
[the full walkthrough](docs/bank_detection_architecture.md) covers the detection pipeline, what
AMLworld stands in for, and why one bank sees only part of a laundering chain.

## Stages

| Stage | Focus | Status | Report |
|---|---|---|---|
| 1 | Data understanding | Complete (`v0.1`) | [reports/stage1_data_understanding.md](reports/stage1_data_understanding.md) |
| 2 | Rules baseline | Not started | *Pending* |
| 3 | Machine learning model | Not started | *Pending* |
| 4 | Graph features | Not started | *Pending* |
| 5 | Validation and business case | Not started | *Pending* |

Table 1. Project stages.

## Data

AMLworld is a synthetic dataset from IBM Research
([Altman et al., NeurIPS 2023](https://arxiv.org/abs/2306.16424)) in which every laundering
payment is known. That makes it useful for learning, and means results here are likely to
overstate real-world performance. The project uses the HI-Small version, downloaded from Kaggle
by script; no data is committed to this repository. Files, structure, validation results,
account labels and limitations are described in [data/README.md](data/README.md).

## Setup

Requires [uv](https://docs.astral.sh/uv/) and a Kaggle API token saved at
`~/.kaggle/access_token` (outside the repository).

```bash
make setup          # create .venv with Python 3.12 and install dependencies
make data           # download HI-Small into data/raw (about 510 MB), then validate it
make labels         # build the account-level mule labels
make test           # run the test suite
make check          # format check, lint, type check and tests (what CI runs)
```

Contributors install the pre-commit hooks once per clone with `uv run pre-commit install`.

The exploratory analysis is in [notebooks/01_eda.ipynb](notebooks/01_eda.ipynb); run it with the
`.venv` interpreter after `make data`.

## Documentation

| Document | Contents |
|---|---|
| [docs/bank_detection_architecture.md](docs/bank_detection_architecture.md) | How a bank detects mule accounts, and what the dataset covers (start here) |
| [scope_and_rationale.md](scope_and_rationale.md) | Rationale, stage plan and evaluation approach, fixed at the start |
| [data/README.md](data/README.md) | Dataset source, structure, validation, account labels and limitations |
| [docs/decisions.md](docs/decisions.md) | Data and modelling decisions, with the options considered and why |
| [docs/domain_primer.md](docs/domain_primer.md) | Fraud, scams, money laundering and mules explained |
| [docs/development.md](docs/development.md) | Coding, testing and reproducibility standards |

Table 2. Project documentation.

## Licence

The code and documentation are released under the [MIT License](LICENSE). The data is not part
of this repository: AMLworld is published by IBM on Kaggle under the Community Data License
Agreement - Sharing - Version 1.0 (see [data/README.md](data/README.md)).
