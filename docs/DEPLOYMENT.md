# Deployment record

## Live Studionet deployment

- Contract: `0x1Bc7cB40DB3781E835Ba23fF7E3a76698dF71d13`
- Explorer: https://explorer-studio.genlayer.com/address/0x1Bc7cB40DB3781E835Ba23fF7E3a76698dF71d13
- Deployment transaction: https://explorer-studio.genlayer.com/tx/0x215d3b46b03dfcdd696058082461ef872e491192a064191d78acfb846337cc03
- Status: `FINALIZED`

The source-visible contract is `contracts/mod_appeal.py`. The live address and deployment transaction are recorded in `deploy/deployment.json`, and the same address is pinned in `dist/app.js`.

The browser app uses:

- network: `studionet`
- chain ID: `61999`
- RPC: `https://studio.genlayer.com/api`
- finalized reads: `TransactionHashVariant.LATEST_FINAL`
- writes: `writeContract()` followed by `TransactionStatus.FINALIZED`

The contract intentionally requires a 30-second minimum appeal window. For a smoke test, create a community, publish policy version 1, register a moderator, record an action, open an appeal with a short deadline, commit evidence from both sides, wait for the deadline, adjudicate, finalize, and claim the resulting credit.

## Verified adversarial workflow

On 2026-09-24, case `case-malicious-20260924` completed the full workflow against this deployment. The disputed content returned `VERIFIED`, while an intentionally false appellant commitment returned `MISMATCH` and was excluded from the validator record. Validator consensus returned `ACTION_OVERTURNED` with confidence 92. Despite that verdict, fault-aware settlement applied `APPELLANT_INVALID_EVIDENCE_FORFEITURE`: the appellant credit was 0 and the community claimed the full 1 GEN bond. Final protocol counters were one community, one policy, one case, one appeal, one adjudication, one finalization, zero active appeals, 1 GEN paid, and zero remaining contract balance.

The contract reserves six evidence slots independently for each side. Invalid or unavailable appellant evidence forfeits the appeal bond; invalid moderator evidence or moderator-committed disputed content refunds it; faults by both parties split it. A clean `INSUFFICIENT_EVIDENCE` result still follows the normal appellant refund rule.

Every transaction hash and the final read-state snapshot are preserved in `deploy/live-test.json`.
