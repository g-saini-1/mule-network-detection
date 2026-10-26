# Stage 1: data understanding

**Status:** complete (`v0.1`). Data: AMLworld HI-Small, a synthetic dataset (see
[data/README.md](../data/README.md)).

## What was built

- **`make data`:** downloads HI-Small from Kaggle and validates it against expected file hashes,
  row counts and content checks (`data/README.md`, Validation).
- **[notebooks/01_eda.ipynb](../notebooks/01_eda.ipynb):** the exploratory analysis.
- **`make labels`:** tested account-level mule labels, with rules R1 to R7 documented in
  `data/README.md` (Account labels).

## Findings

- **Laundering is rare.** 5,177 of 5,078,345 payments (0.1019%) are laundering, so a model that
  flags nothing would be about 99.9% accurate. Evaluation therefore uses precision and recall at
  an alert budget, not accuracy.
- **The timeline has a trap.** Normal activity stops after 10 September; the 8 days after that
  hold 1,108 transactions, 59.12% of them laundering. They are not a realistic test period.
- **Some signals are too clean.** ACH carries 86.59% of laundering but 11.83% of transactions, and
  Wire, Reinvestment and all 72,170 cross-currency payments carry none. These are likely
  simulator artefacts rather than laundering behaviour.
- **Timestamps do not follow the money.** Within laundering schemes, a payment that passes money
  on is often timestamped before the payment that brought it in (five of the eight typologies).
- **1,003 of 515,088 accounts (0.1947%) are mules** under the final label.

## How the label was decided

The data flags payments, but the project scores accounts, so the label had to be built. It went
through three versions:

1. **Receives and sends laundering money** (1,003 mules).
2. **Strict: sends after its first receipt** (899 mules), after a review found 104 mules that
   never sent money after receiving it.
3. **Back to order ignored** (1,003 mules), after a second review showed the timestamps do not
   follow the money, so the strict rule mislabelled real middle accounts.

The final labels also record when each account became a mule and can be built as at any point in
time. An independent rebuild of the final labels matched with no differing rows. Reasoning for
each version: [docs/decisions.md](../docs/decisions.md).

## What this stage does not show

- **No model has been built,** so nothing here measures detection performance.
- **The data is synthetic,** with complete and certain labels that real banks never have, so
  results from later stages are likely to overstate real-world performance.

## What it means for Stage 2

- **The temporal split must not treat the days after 10 September as a realistic test period.**
- **Every account is scored at the same point in time,** mules and non-mules alike; labels built
  as at a cut-off make this possible.
- **Consider splitting by owner:** 637 of the 945 owners of a mule account also own non-mule
  accounts.
- **Positives are scarce:** as at 11 September 00:00, 795 accounts are mules, and the training and
  test periods have to share them.
