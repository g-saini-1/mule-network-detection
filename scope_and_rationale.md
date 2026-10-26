# Money mule detection: scope and rationale

> **Purpose:** Defines the scope, rationale and staged plan for a self-directed learning project on money mule detection in banking.
>
> **Working title:** Money Mule Detection · **Repository:** `mule-network-detection`

---

## 1. Project summary

This project detects **money mule accounts**: bank accounts that receive and pass on illicit funds, e.g. scam proceeds. The approach builds up in stages, from a simple rules baseline, to a machine learning model, to graph (network) features, and finally to validation and a business case.

---

## 2. Rationale

### Why money mules
- Scams are one of the largest financial-crime losses in Australia. The National Anti-Scam Centre's [*Targeting Scams Report 2025*](https://www.nasc.gov.au/system/files/targeting-scams-report-2025.pdf) reported $2.18B in combined losses across 481,523 reports in 2025.
- In a scam, the victim authorises the payment, so classic fraud rules often miss it. Banks increasingly detect scam and fraud proceeds on the receiving side, by identifying the mule accounts that collect and move the money.
- Mule detection is a core capability in bank fraud and financial-crime teams. It is relevant to the Scams Prevention Framework, which requires banks to detect and disrupt scams, and to the industry's Scam-Safe Accord, under which banks share scam intelligence, e.g. through the Australian Financial Crimes Exchange.

### Why this design
- **Account-level scoring:** banks flag accounts, not single payments, so every stage scores accounts with the same label and temporal split.
- **Benchmarked progression:** rules baseline, then ML, then ML with graph features. Each step's added value is measured fairly against the previous one.
- **Cost-based evaluation:** thresholds come from configurable alert and loss costs, with sensitivity analysis, because the cost assumptions are illustrative.
- **Honest validation:** synthetic AML data is generated from network patterns, so graph-feature lift is likely to overstate what a real bank would see. A single-bank partial view of the network is tested to approximate what one real bank can see.

### Scope boundary
The data covers laundering and mule behaviour in general, not scam proceeds specifically. Scams are the motivating context; the project's claim is **mule account detection**.

---

## 3. Stage plan

Suggested timeboxes assume part-time effort and are guides, not deadlines.

### Stage 1: Data understanding · ~1–2 weeks · `v0.1`
**Learn:** dataset structure, label construction, class imbalance, time coverage.

**Build:**
- A download script and data validation checks.
- An EDA notebook covering transaction volumes, the illicit rate, time span, payment formats, and examples of laundering patterns.
- An **account-level label definition** (which accounts count as mules), documented and tested.

**Done when:** `data/README.md` describes the data, its time span and its limitations, and the label definition is logged in `docs/decisions.md`.

### Stage 2: Rules baseline · ~1–2 weeks · `v0.2`
**Learn:** how rules engines work, alert budgets, precision and recall at a fixed number of alerts.

**Build:** 3–5 simple, explainable account-level rules (for example, high pass-through within 48 hours of first activity), plus a temporal train/validation/test split used by every later stage.

**Done when:** the rules are evaluated on the test period at a fixed alert budget, and the results table is in the README.

### Stage 3: Machine learning model · ~2–3 weeks · `v0.3`
**Learn:** feature engineering over time windows, data leakage, gradient boosting, calibration, cost-based thresholds, SHAP.

**Build:**
- Account-level transaction and velocity features, with leakage tests.
- A LightGBM model compared against the Stage 2 rules on the same split.
- A cost function with sensitivity analysis across cost ratios.
- SHAP explanations for the top drivers and example alerts.

**Done when:** the ML vs rules comparison is reported at the same alert budget, with the threshold choice justified by cost.

### Stage 4: Graph features · ~2–3 weeks · `v0.4`
**Learn:** network basics (nodes, edges, degree, components, PageRank, communities), and why network context reveals mules.

**Build:**
- A transaction network and account-level graph features.
- Lift measured against Stage 3 on the same unit, label and split.
- A **partial-view test**, using only the accounts one bank could see, to show how lift changes with limited visibility.

**Done when:** the full-view and partial-view lift are both reported, with the synthetic-data caveat stated.

### Stage 5: Validation and business case · ~1–2 weeks · `v1.0`
**Learn:** model risk basics, stability, error analysis, and translating model output into business terms.

**Build:**
- Calibration, threshold sensitivity, and stability across time periods (as far as the data's time span allows).
- Error analysis: what the model misses and what it wrongly flags.
- `reports/model_card.md` and a one-page `reports/business_case.md`.
- A final README written for hiring managers.

**Done when:** a non-technical reader can understand what was built, what it would mean for a bank, and its limitations.

### Backlog (only after `v1.0`)
- Graph neural network (PyTorch Geometric) vs engineered graph features.
- Simulated victim-side scam payments injected into the data.
- Fairness audit on the BAF dataset (account-opening fraud with controlled bias).
- Robustness check on the lower-illicit-rate (LI) datasets.

### Out of scope
Real customer data, production deployment, real-time systems, and claims of real-world performance.

---

## 4. Data

| Dataset | Use | Source | Licence / conditions |
|---|---|---|---|
| IBM Transactions for AML (AMLworld), **HI-Small** | Primary dataset, Stages 1–5 | Kaggle: `ealtman2019/ibm-transactions-for-anti-money-laundering-aml` | Community Data License Agreement - Sharing - Version 1.0 (as listed on Kaggle) |
| IBM AML, LI datasets | Backlog robustness check | Same as above | Same as above |
| Bank Account Fraud (BAF) suite | Backlog fairness module | Kaggle: `sgpjesus/bank-account-fraud-dataset-neurips-2022` | CC BY-NC-ND 4.0: non-commercial; no redistribution of modified copies |
| NASC *Targeting Scams* reports | Context only (aggregate figures) | scamwatch.gov.au / nasc.gov.au | Public reports |

**Data rules:**
- Never commit raw or processed data. Download through scripts only, and keep `data/` git-ignored apart from `.gitkeep` and `README.md`.
- Kaggle credentials stay outside the repo.
- Record dataset versions and file hashes in `data/README.md`.

**Known limitations:**
- The data is synthetic, and laundering is generated from network patterns, so results are likely to overstate real-world performance.
- It covers laundering in general, not scam-specific behaviour or the victim-side signals banks hold internally.

---

## 5. Evaluation approach

- **Unit:** account level, in every stage.
- **Split:** temporal (earlier periods for training, later periods for testing), fixed in Stage 2 and reused in every later stage.
- **Primary metrics:** recall and precision at a fixed alert budget, PR-AUC, and expected cost.
- **Cost assumptions:** stored in `configs/costs.yaml`, with sensitivity analysis rather than a single figure.
- **Secondary metrics:** accuracy and ROC-AUC, reported with a note on why they mislead for rare events.

---

## 6. Tooling and conventions

- **Python:** 3.11+, with `uv` for environments (fall back to `venv` + `pip` if needed).
- **Core:** pandas or polars, numpy, scikit-learn, lightgbm, networkx, shap, matplotlib, pyyaml, kaggle.
- **Dev:** pytest, ruff, pre-commit, nbstripout.
- **Backlog only:** torch, torch-geometric (optional dependency group `graph-ml`).
- **Reproducibility:** fixed seeds and all paths in config.
- **Git:** one branch per stage (`stage-1-data`, `stage-2-rules`, …), Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`), and a merge to `main` plus a release tag at the end of each stage.
