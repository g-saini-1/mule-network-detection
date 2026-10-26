# How a bank detects mule accounts, and what AMLworld covers

A generic picture of how a bank turns payments into mule alerts and decisions, and which parts of
it the IBM AMLworld data used in this project actually stands in for. Terms such as mule
account, the laundering cycle and suspicious matter reports are defined in
[domain_primer.md](domain_primer.md).

The architecture is a simplified, typical layout drawn from public descriptions of bank fraud
and financial-crime operations. It is not any specific bank's system, and it is not compliance
guidance.

## The detection pipeline

Data flows left to right, from raw sources to a decision on an account. The loop along the
bottom is what makes the system learn: confirmed outcomes become the labels that future rules
and models are tuned on.

![Figure 1. A bank's mule detection pipeline, marked by what AMLworld covers](figures/detection_pipeline.svg)

Figure 1. Only three boxes have AMLworld equivalents: payments, accounts and owners, and
confirmed labels. The project builds the middle of the pipeline (features, graph, rules, ML,
validation) from them; everything about investigation and intervention is outside the data.

## How the pipeline works

1. **Data sources.** Payments are the core feed, joined to who owns each account (identity
   checks, or KYC), how customers log in (devices and IP addresses), and what outsiders report:
   scam victims, other banks asking for money back, and law enforcement.
2. **Data platform.** Entity resolution works out which accounts, people and devices belong
   together. A feature store keeps behaviour summaries per account, e.g. money in and out over
   the last 24 hours. A graph store records who pays whom.
3. **Detection.** Rules catch known patterns and are easy to explain. Models score accounts on
   behaviour. Graph analytics looks at an account's neighbours, e.g. whether it receives from
   many unrelated senders. Some checks run as a payment happens so it can be held; most mule
   scoring runs daily per account.
4. **Alerts and cases.** Scores become a ranked queue cut off at what the team can investigate
   each day, the alert budget. Analysts review each case.
5. **Outcomes.** An account can be restricted or closed, money can be recalled, and a suspicious
   matter report can go to AUSTRAC. A confirmed outcome becomes a label.
6. **Governance.** An independent validation team reviews models before use and monitors them
   after, separate from the team that built them.

## Where AMLworld resembles a bank

AMLworld provides the raw material at the two ends of the pipeline, payments in and labels out,
and nothing in between. Details of each file are in [data/README.md](../data/README.md).

| Bank component | AMLworld equivalent | Main difference |
|---|---|---|
| Payments | Transactions file: each payment's time, accounts, amount, currency and format | Covers every bank at once, over 18 days, with no channel detail beyond a payment format |
| Accounts and owners | Accounts file: each account's bank and owner (entity) | Owners have only a simulated type (e.g. Corporation); there is no identity, age, income or opening date |
| Confirmed labels | `is_laundering` flag on each payment | Complete, immediate and certain, unlike real labels (data/README.md, Table 4) |
| Case and typology knowledge | Patterns file: laundering schemes by typology | A partial answer key; in a bank this knowledge sits in case files and intelligence reports, and covers only what was caught |
| Transaction graph | Buildable from the transactions file | Shows the whole network across banks; a bank sees only its own side (Figure 2) |
| Everything else | None | No devices, external intelligence, alerts, investigations or interventions |

Table 1. Bank pipeline components and their AMLworld equivalents.

## The biggest difference: what one bank can see

AMLworld shows payments between all banks. A real bank sees its own customers' accounts in
full, and for a payment to or from another bank only the counterparty's account number.
Payments between two other banks are invisible to it.

![Figure 2. One laundering chain seen in AMLworld and from a single bank](figures/one_bank_view.svg)

Figure 2. The red chain A1 → B1 → B2 → A2 is one laundering scheme. In AMLworld every hop is
visible. Bank A sees money leave A1 for B1 and arrive at A2 from B2, but not the hop inside
Bank B, so the chain looks like two unrelated payments.

This is why Stage 4 has a partial-view test: graph features are rebuilt using only what one bank
could see, to measure how much of the full-view lift survives.

## What this means for the project

- **The project rebuilds the detection layer, not the bank.** Stages 2 to 4 build the rules,
  features, ML and graph boxes in Figure 1; Stage 5 plays the validation box and prices the
  alert budget.
- **Results describe the middle of the pipeline under ideal inputs.** Perfect labels and a full
  network view make detection easier than in a bank, so results are likely to overstate what a
  bank would achieve.
- **The missing boxes are where real banks get much of their signal.** Devices, identity checks
  and external reports are absent, so the project cannot say how much they would add.
