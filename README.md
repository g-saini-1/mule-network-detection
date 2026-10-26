# Money mule detection

Detecting money mule accounts (bank accounts that receive and pass on illicit funds, e.g. scam
proceeds) in bank transfer networks, using synthetic public data.

**Status:** self-directed learning project, Stage 1 (data understanding) in progress. Results
come from synthetic data and are illustrative only, not claims of production performance.

## Stages

| Stage | Focus | Status |
|---|---|---|
| 1 | Data understanding | In progress |
| 2 | Rules baseline | Not started |
| 3 | Machine learning model | Not started |
| 4 | Graph features | Not started |
| 5 | Validation and business case | Not started |

Table 1. Project stages.

## Data

IBM's synthetic AMLworld dataset (HI-Small), downloaded from Kaggle by script. No data is
committed to this repository. Files, structure, validation results and limitations are described
in [data/README.md](data/README.md).

## Setup

Requires [uv](https://docs.astral.sh/uv/) and a Kaggle API token saved at
`~/.kaggle/access_token` (outside the repository).

```bash
make setup          # create .venv with Python 3.12 and install dependencies
make data           # download HI-Small into data/raw (about 510 MB), then validate it
make test           # run the test suite
```

The exploratory analysis is in [notebooks/01_eda.ipynb](notebooks/01_eda.ipynb); run it with the
`.venv` interpreter after `make data`.

## Documentation

| Document | Contents |
|---|---|
| [scope_and_rationale.md](scope_and_rationale.md) | Rationale, stage plan and evaluation approach, fixed at the start |
| [data/README.md](data/README.md) | Dataset source, structure, validation and limitations |
| [docs/domain_primer.md](docs/domain_primer.md) | Fraud, scams, money laundering and mules explained |
| [docs/bank_detection_architecture.md](docs/bank_detection_architecture.md) | How a bank detects mule accounts, and what the dataset covers |

Table 2. Project documentation.
