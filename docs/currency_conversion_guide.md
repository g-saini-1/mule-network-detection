# Currency conversion

**Status:** Draft, Stage 2.

The transaction amounts are converted to one currency. This guide explains why and how it is done, and
the limits of the approach. The decision, with the options considered, is in
[decisions.md](decisions.md) (2026-11-19).

## Two currencies in one payment

A payment can leave the sender's account in one currency and arrive in the receiver's account in
another, with the bank converting between them at its own rate when the payment is made. This
applies within one bank as well as between banks, because two accounts at the same bank can be
held in different currencies.

AMLworld records each payment's amount paid and payment currency separately from its amount
received and receiving currency (Altman et al., 2023). The paper does not state how the simulator
sets exchange rates.

## How amounts are handled

1. **The original amounts are kept.** The amounts and currencies as recorded stay unchanged,
   because they are what actually moved.
2. **Every amount is also expressed in one base currency.** Detection rules add up and compare
   amounts across payments, e.g. money received against money sent by one account. Those sums are
   only meaningful in a single unit.
3. **Rates come from the data.** A bank would use the rate it recorded for each payment.
   AMLworld supplies no rates, so one fixed rate per currency is inferred from the payments
   themselves. This relies on the simulator's rates being fixed, which the conversion consistency
   check below tests on every run.

## Method

The base currency, the minimum amount and the tolerance below are set in a configuration file.

- **Rates.** Each currency's rate is its number of units per US Dollar: the median of the rates
  implied by cross-currency payments between that currency and US Dollar, in either direction,
  using only payments with an amount paid of 100 or more. A payment's implied rate is its amount
  received divided by its amount paid, inverted when US Dollar is the receiving currency. Rates
  are computed from the data on every run, not entered by hand.
- **Conversion.** `amount_paid_usd` is the amount paid divided by the payment currency's rate,
  and `amount_received_usd` the amount received divided by the receiving currency's rate. Each
  side uses its own currency's rate, so a payment between two other currencies, e.g. Euro to
  Australian Dollar, is converted like any other.

### Checks

Two checks test whether the data fits the method's assumptions. Preparation stops at the first
failed check and does not write its output; the error names what failed. A failure points to a
change in the data, not a fault to work around.

| Check | Fails when | Likely causes in the data | Response |
|---|---|---|---|
| Missing rate | A currency in the data has no rate | A new currency, or one with no US Dollar payment of 100 or more | Decide how the currency is handled (e.g. a rate through a third currency, or leaving its payments out), with a decisions.md entry |
| Conversion consistency | On any cross-currency payment with an amount paid of 100 or more, the gap between the converted amount paid and the converted amount received, as a share of the converted amount paid, is above the tolerance | Rates that change over time, or fees or spreads in the amounts | Find the pattern in the failing payments (e.g. which currency pairs, which dates), then revise the method (e.g. rates by period), with a decisions.md entry. The tolerance is not raised just to pass the check |

Table 1. Checks on the conversion and the response to each failure.

The consistency check covers every currency pair, not only pairs with US Dollar, so it tests
whether the inferred rates hold across all of them.

## Base currency

A bank would normally use its home currency, e.g. Australian Dollar for an Australian bank. This
project uses US Dollar, the most used currency in the data. The converted columns are named for
it, so preparation fails if another base currency is set.

With fixed rates, changing the base multiplies every converted amount by the same factor. Ratios
and rankings between amounts do not change, e.g. money sent as a share of money received, but a
fixed threshold does, so a rule threshold needs its currency stated.

## Implications for detection

This section is the project's reasoning, not a documented typology.

- A pass-through rule compares the money an account receives with the money it sends. When the
  two are in different currencies, the raw amounts cannot be compared, but the converted amounts
  can.
- Conversion does not hide a change of currency. The original currencies stay available to any
  rule that needs them.

## Limitations

- The rates are inferred from the data, not published rates.
- The rates are inferred from the whole period, so amounts in earlier periods are converted with
  rates learned partly from later payments ([decisions.md](decisions.md), 2026-11-27).
- The data has no exchange fees, spreads or rate changes over time. In real payments these would
  widen the gap between converted paid and received amounts, and the check's tolerance would
  need review.

## References

Altman, E., Blanuša, J., von Niederhäusern, L., Egressy, B., Anghel, A. and Atasu, K. (2023).
Realistic Synthetic Financial Transactions for Anti-Money Laundering Models. *NeurIPS 2023
Datasets and Benchmarks Track*. <https://arxiv.org/abs/2306.16424>
