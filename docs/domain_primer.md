# Domain primer

Suggested sources: the IBM AMLworld paper (arXiv 2306.16424), AUSTRAC and FATF publications on money mules, and the NASC *Targeting Scams* reports.

## Key terms

**Fraud:** Stealing money without the victim's consent, e.g. through hacking or identity theft.

**Scam:** Tricking a victim to willingly send money.

**Mule:** A person who receives and moves illicit money on behalf of criminals, knowingly or not.

**Mule account:** An account used to receive or move illegal or stolen money.

**Money laundering:** Hiding the illegal source of the money to make it clean.

## The laundering cycle
1. **Placement: getting the money into the financial system**
- The proceeds first land in an account the criminal can use. The money is stolen using illegal methods like fraud or scams.
- This is where the money is most exposed to tracing or recalling. Criminals try to move the money within minutes or hours of receiving it.
- Mule signal: a dormant or new account suddenly receiving one or more incoming payments from people it has no history with.
2. **Layering: hiding the trail**
- The process of moving stolen money from victim to criminal network. The money is split and passed through many accounts with the aim to break the link between the money and the original crime.
- This is where mule networks do most of the work, using common mule typologies like fan-in and fan-out, with recruited or complicit mules.
- Mule signal: high velocity, near zero balances most of the time and short chains of transfers between connected accounts.
3. **Integration: clean the stolen money for use**
- The process to clean the stolen money for use by criminals looking legitimate. It's mostly outside what a bank's transfer data can see.
- By this stage the money is several steps away from the original crime and hard to tie back to it.
- Detection relies more on investigation than on transaction monitoring.

## Detecting mules
1. **Onboarding data and controls**
- Checks when account is opened: KYC, device and IP checks
- Multiple mule accounts may open in short period of time.
2. **Rules engines**
- Automated transaction monitoring systems (TMS)
3. **Behavioural profiling**
- Check for behavioural anomalies. Score accounts or transactions on behavioural features
like velocity, balance patterns, counterparties.
4. **Alerts and triage**
- Alerts go into a case management queue for analyst investigation
5. **Suspicious matter reporting**
- If the activity is concluded as suspicious, the bank files a Suspicious Matter Report (SMR) to AUSTRAC.

For the full detection pipeline and how the AMLworld data maps onto it, see [bank_detection_architecture.md](bank_detection_architecture.md).

## Model performance metrics
Accuracy is not a useful metric on its own for rare events. It measures every prediction equally. Correct prediction of non-mule and mule accounts are treated equally. In this project's data, mules make up 0.1947% of accounts (1,003 of 515,088). If the model predicted the majority of non-mule accounts accurately then the accuracy can be very high but it's not very useful for mule detection. The bank cares about the accurate detection of the small share of mule accounts.

1. **Precision:** Out of the alerts that were identified, how many were real. A measure of quality of identification.

*True positives as a percentage of all alerts (true positives + false positives)*

2. **Recall:** Out of all the mules out there, how many were caught. A measure of quantity of identification.

*True positives as a percentage of all mules (true positives + false negatives)*
