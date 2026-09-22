# Deployment record

## Live Studionet deployment

- Contract: `0x5f4d4256736DC7B9288F4c02796c6A4c1b4B47c2`
- Explorer: https://explorer-studio.genlayer.com/address/0x5f4d4256736DC7B9288F4c02796c6A4c1b4B47c2
- Deployment transaction: https://explorer-studio.genlayer.com/tx/0x0b25ce86ed02f6c461622d55a0f1dea0c9c3b4cf5d4708ca348980619876e528
- Status: `FINALIZED`

The source-visible contract is `contracts/mod_appeal.py`. The live address and deployment transaction are recorded in `deploy/deployment.json`, and the same address is pinned in `dist/app.js`.

The browser app uses:

- network: `studionet`
- chain ID: `61999`
- RPC: `https://studio.genlayer.com/api`
- finalized reads: `TransactionHashVariant.LATEST_FINAL`
- writes: `writeContract()` followed by `TransactionStatus.FINALIZED`

The contract intentionally requires a 30-second minimum appeal window. For a smoke test, create a community, publish policy version 1, register a moderator, record an action, open an appeal with a short deadline, commit evidence from both sides, wait for the deadline, adjudicate, finalize, and claim the resulting credit.

## Verified live workflow

On 2026-09-22, case `case-final-20260922` completed the full workflow against this deployment. The disputed content and both evidence sources returned `VERIFIED` SHA-256 status. Validator consensus returned `ACTION_OVERTURNED` with confidence 100, finalization credited the 1 GEN bond to the appellant, and `claim_bond` paid it in full. The final protocol counters were one community, one policy, one case, one appeal, one adjudication, one finalization, zero active appeals, and zero remaining contract balance.

Every transaction hash and the final read-state snapshot are preserved in `deploy/live-test.json`.
