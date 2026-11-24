# Transaction preparation

**Status:** Draft, Stage 2.

The raw transactions file is not ready for detection rules:

- It has no transaction identifier.
- It is not in time order.
- It holds amounts in several currencies.
- It does not say which scheme a laundering payment belongs to.
- It does not mark duplicates, self-transfers or own-account transfers.

Preparation turns it into one prepared transactions file that the rules engine and later stages
read. The raw data is described in [data/README.md](../data/README.md), and the reasoning behind
each rule is in [decisions.md](decisions.md).

## Rules

**P1. Transaction ID.** Each transaction gets `transaction_id`, its zero-based row position in
the raw transactions file (header excluded), assigned before any reordering. The raw data has no
natural key ([data/README.md](../data/README.md), Structure).

**P2. Typed columns.** Columns are named and typed as `load_transactions()` returns them: parsed
timestamps, amounts as numbers, the laundering flag as 0 or 1, bank IDs without zero-padding, and
currencies and payment formats as categories. An account is a bank ID plus an account number
([account_labelling_guide.md](account_labelling_guide.md), R1), kept as two columns on each side.

**P3. Duplicates.** A transaction whose every column apart from `transaction_id` equals an
earlier transaction in file order is a duplicate, and `is_duplicate` is true for it. The first
copy is not flagged, and no row is dropped.
*Example:* if rows 10 and 11 are identical, row 11 is flagged and row 10 is not.

**P4. Self-transfers.** A transaction whose sender and receiver are the same account, with the
same bank ID and the same account number (R1), is a self-transfer, and `is_self_transfer` is true
for it. A payment between two different accounts is not a self-transfer, even when both accounts
are at the same bank or have the same owner (P5). No row is dropped; each detection rule states
whether it excludes self-transfers.

**P5. Own-account transfers.** A transaction between two different accounts at the same bank
with the same owner (the same `entity_id` in the accounts file) is an own-account transfer, and
`is_own_account_transfer` is true for it. A payment between accounts of the same owner at
different banks is not flagged, because a bank cannot see who owns an account at another bank. No
row is dropped; each detection rule states whether it excludes own-account transfers.
*Example:* a payment from bank 10, account X to bank 10, account Y is flagged if X and Y have the
same owner; a payment from bank 10, account X to bank 20, account Z is not, whoever owns Z.

**P6. Currency conversion.** Every amount is also given in US Dollar, the base currency set in
`configs/data.yaml`, as `amount_paid_usd` and `amount_received_usd`, by the method in
[currency_conversion_guide.md](currency_conversion_guide.md). Preparation fails if that method's
checks fail.

**P7. Time order.** Transactions are sorted by timestamp, with ties kept in `transaction_id`
order.

**P8. Scheme tags.** Each block in the patterns file is one scheme. Its `scheme_id` is the
block's position in the file, starting at 1, and its `typology` is the name on the block's
`BEGIN LAUNDERING ATTEMPT` line. Each row in a block is matched to the transaction with the same
raw text, which then takes the block's `scheme_id` and `typology`. Transactions in no block have
both empty. A laundering payment with an empty typology is one the patterns file does not cover,
not a normal payment. Preparation fails if a pattern row matches no transaction, matches more
than one, or matches a transaction whose laundering flag is 0.

**P9. Output checks.** Before the file is written, preparation fails unless the output matches
its declared schema (column names, types, empty values and value ranges), has the same number of
rows as the raw file, has the same number of laundering payments, and has the same total amount
paid per payment currency and amount received per receiving currency as the raw file, within
floating-point rounding.

## Columns

| Column | Meaning | Rule |
|---|---|---|
| `transaction_id` | Row position in the raw file | P1 |
| `timestamp` | Time of payment, to the minute | P2 |
| `from_bank`, `from_account` | Sender account | P2 |
| `to_bank`, `to_account` | Receiver account | P2 |
| `amount_paid`, `payment_currency` | Amount leaving, in the sender's currency | P2 |
| `amount_received`, `receiving_currency` | Amount arriving, in the receiver's currency | P2 |
| `payment_format` | e.g. ACH, Wire, Reinvestment | P2 |
| `is_laundering` | 1 if the payment is part of a laundering scheme | P2 |
| `is_duplicate` | True for a later copy of an earlier transaction | P3 |
| `is_self_transfer` | True if sender and receiver are the same account | P4 |
| `is_own_account_transfer` | True if sender and receiver are different accounts at the same bank with the same owner | P5 |
| `amount_paid_usd`, `amount_received_usd` | The two amounts in US Dollar | P6 |
| `scheme_id` | The patterns-file block the payment belongs to; empty if none | P8 |
| `typology` | The scheme's typology, e.g. Fan-in or Cycle; empty if none | P8 |

Table 1. Columns in `data/interim/transactions.parquet`.

`make prepare-data` builds the file, and
`mule_detection.data.prepare_transactions.load_prepared_transactions()` reads it.

`is_laundering`, `scheme_id` and `typology` are for evaluation only. The rules engine never reads
them ([solution_architecture.md](solution_architecture.md), Figure 3).
