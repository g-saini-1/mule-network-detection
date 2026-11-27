# Transaction labelling

**Status:** Draft, Stage 2.

Transaction labels hold what is known about each payment's part in laundering: its laundering
flag and, where the patterns file covers it, its scheme and typology. They are kept apart from the
prepared transactions so that detection never reads them; only the evaluation harness does
([decisions.md](decisions.md), 2026-11-27). Each transaction is identified by its
`transaction_id` ([transaction_preparation_guide.md](transaction_preparation_guide.md), P1). The
raw data is described in [data/README.md](../data/README.md).

## Rules

**T1. Laundering flag.** Each transaction's `is_laundering` is its laundering flag in the raw
file, 0 or 1 ([data/README.md](../data/README.md), How the laundering flag is set).

**T2. Scheme tags.** Each block in the patterns file is one scheme. Its `scheme_id` is the
block's position in the file, starting at 1, and its `typology` is the name on the block's
`BEGIN LAUNDERING ATTEMPT` line. Each row in a block is matched to the transaction with the same
raw text, which then takes the block's `scheme_id` and `typology`. Transactions in no block have
both empty. A laundering payment with an empty typology is one the patterns file does not cover,
not a normal payment. Labelling fails if a pattern row matches no transaction, matches more than
one, or matches a transaction whose laundering flag is 0.

**T3. Output checks.** Before the file is written, labelling fails unless it has one row for each
transaction in the raw file and the same number of laundering payments as the raw file.

## Columns

| Column | Meaning | Rule |
|---|---|---|
| `transaction_id` | Row position in the raw file | P1 |
| `is_laundering` | 1 if the payment is part of a laundering scheme | T1 |
| `scheme_id` | The patterns-file block the payment belongs to; empty if none | T2 |
| `typology` | The scheme's typology, e.g. Fan-in or Cycle; empty if none | T2 |

Table 1. Columns in `data/processed/transaction_labels.parquet`.
