# Account labelling

The data flags individual payments, but the project scores accounts, so each account gets a
label built from its laundering payments. The reasoning behind the rules is recorded in
[decisions.md](decisions.md); the rules themselves are below. The data they are built from is
described in [data/README.md](../data/README.md).

## Rules

**R1. Account.** An account is a bank ID plus an account number.
*Example:* account number `80A7FD400` appears at bank 27755 and at bank 28248; these are two
different accounts. Eight account numbers in HI-Small appear at more than one bank.

**R2. Laundering payment.** A payment whose laundering flag is 1
([data/README.md](../data/README.md), How the laundering flag is set).
*Example:* on 10 September 09:59, account `10057:80C3B78E0` receives 1,870,505.26 yen in a
laundering payment.

**R3. Self-transfers.** A laundering payment from an account to itself is ignored, because it
neither receives money from nor passes money to anyone else.
*Example:* 11 laundering payments are self-transfers; ignoring them changes no label in
HI-Small.

**R4. Mule.** An account is a mule if it receives at least one laundering payment and sends at
least one laundering payment, in either order. Why order is ignored: `docs/decisions.md`
("Mule label returned to both directions, order ignored").
*Example:* `10057:80C3B78E0` receives on 10 September and sends on 11 September, so it is a mule.
`213952:806D47B10` is a middle account in a scatter-gather scheme, where money must arrive before
it is passed on, yet its send is timestamped 1 September 08:40 and its receipt 2 September 13:04;
it is also a mule.

**R5. Timing.** Each account records when it was first involved in laundering in each direction
and, for mules, when it first met R4: the later of its first laundering receipt and its first
laundering send.
*Example:* for `10057:80C3B78E0`, `first_laundering_at` is 10 September 09:59 and `mule_at` is
11 September 10:03. Between those two times the account had received laundering money but not
yet sent any.

**R6. Cut-off.** Labels built "as at" a point in time use only payments before it, so they show
what had happened by that point. Accounts whose first transaction is at or after the cut-off are
left out (R7).
*Example:* as at 11 September 00:00, `10057:80C3B78E0` is not yet a mule, and HI-Small has 795
mules among 515,078 accounts, instead of 1,003 among 515,088.

**R7. Population.** Every account that appears in at least one transaction (before the cut-off,
if one is used) gets a label.
*Example:* 515,088 accounts are labelled; the 3,493 accounts in the accounts file with no
transactions are not.

## Label columns

| Column | Meaning |
|---|---|
| `bank_id`, `account_number` | The account (R1) |
| `is_mule` | True if the account meets R4 |
| `mule_at` | When the account first met R4; empty for non-mules |
| `first_laundering_at` | First laundering payment in either direction; empty if none |
| `first_received_at`, `first_sent_at` | First laundering payment received and sent; empty if none |
| `laundering_received`, `laundering_sent` | Number of laundering payments received and sent |

Table 1. Columns in `data/processed/account_labels.parquet`.

## Accounts by laundering role

| Role | Accounts | Label |
|---|---|---|
| No laundering payments | 508,731 | Not mule |
| Send only | 2,373 | Not mule |
| Receive only | 2,981 | Not mule |
| Both directions, first receipt timestamped first | 862 | Mule |
| Both directions, first send timestamped first | 141 | Mule |

Table 2. Labelled accounts by role in laundering payments.

1,003 of 515,088 accounts (0.1947%) are mules. Their `mule_at` runs from 1 September 02:52 to
16 September 00:20, and 208 of them first meet R4 on or after 11 September, in the tail where
normal activity has stopped. The split by which direction is timestamped first is shown for
information only, since the timestamps do not reliably show the order money moved.

The roles describe where an account sits in the laundering flows, not facts the data records.
"Send only" accounts are likely where money enters a scheme. "Receive only" accounts are where a
scheme ends in the data, which could be a cash-out account or the criminal's own. Some
"both directions" accounts are not mules in the usual sense but the account where a scheme
starts and its money returns, e.g. the start of a cycle; the data cannot reliably tell these
apart from mules, so they are labelled mules.

## Building and exploring the labels

```bash
make labels     # build data/processed/account_labels.parquet from the raw transactions
```

In Python, `mule_detection.data.labels.load_labels()` reads the file with account keys as text
and timestamps as dates; `build_account_labels(transactions, as_at=...)` builds labels as at a
point in time. To browse the file, open it in VS Code with the Data Wrangler extension.
