
- Why accuracy misleads on rare events, and what precision, recall and "alerts per day" mean to an operations team.
- Suggested sources: the IBM AMLworld paper (arXiv 2306.16424), AUSTRAC and FATF publications on money mules, and the NASC *Targeting Scams* reports.

**Fraud:** Stealing through hacking, identity theft.

**Scam:** Tricking a victim to willingly send money.

**Mule:** Middle steps used to move and clean the illicit funds.

**Mule account:** An account used to receive or move illegal or stolen money.

**Money Laundering:** Hiding the illegal source of the money to make it clean.

# The laundering cycle
1. **Placement: getting the money into the financial system**
- The proceeds first land in an account the criminal can use. The money is stolen using illegal methods like fraud or scams.
- This is where the money is most exposed to tracing or recalling. Criminals try to move the money within in minutes or hours of receiving it.
- Mule signal: a dormant or new account suddenly recieving one or more incoming payments from people it has no history with.
2. **Layering: hiding the trail**
- The process of moving stolen money from victim to criminal network. The money is split and passed through many accounts with the aim to break the link between the money and the original crime.
- This is where mule networks do most of the work using common mule typologies like fan-in, fan-out, recruited vs complicit mules.
- Mule signal: high velocity, near zerio balances most of the time and shor chains of transfers between connected accounts.
3. **Ingegration: clean the stolen money for use**
- The process to clean the stolen money for use by criminals looking legitimate. It's mostly outside what a bank's transfer data can see.
- By this stage the money is several steps away from the original crime and hard to tie back to it.
- Detection relies more on investigation than on transaction monitoring. 

# Detecting mules
1. **Onboarding data and controls**
- Checks when account is opened: KYC, device and IP checks
- Multiple mule accounts may open in short period of time.
2. **Rules engines**
- Automated transaction monitoring systems (TMS)
3. **Behavioural profiling**
- Check for behavioural anomalies. Score accounts or transaction on behavioural features
like velocity, balance patterns, counterparties.
3. **Alerts and triage**
- Alerts goes into a case management queue for analyst investigation
4. **Suspicious matter reporting**
- If the acitivity is concluded as suspicious, the bank files a Suspicious Matter Report (SMR) to AUSTRAC.

For the full detection pipeline and how the AMLworld data maps onto it, see [bank_detection_architecture.md](bank_detection_architecture.md).

# Model performance metrics
 Accuracy is not a useful metric as it measures accuracy of the prediction. It measure every prediction equally. Correct prediction of non-mule and mule-accounts are treated equally. Mules make up about 1% of all account. If the model predicted predicted majority of non-mule accounts accurately then the accuracy can be very high but it's not very useful for mule detection. The bank cares about the accurate detetection of the 1% of mule accounts.

1. **Precision:** Out of the alerts that were identified, how many were real. A measure of quality of identification.

*True positive as a percentagle of all positives (true positive + false positive)*

2. **Recall:** Out of all the mules out there, how many were caught. A measure of quantity of identification.

*True positive as a percentagle of all mules (true positive + false negative)*

