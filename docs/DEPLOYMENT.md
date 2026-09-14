# Deployment record

The source-visible contract is `contracts/mod_appeal.py`. Deploy it in GenLayer Studio on Studionet using the built-in wallet. After the deployment receipt is finalized, record the contract and deployment transaction in `deploy/deployment.json`, then update `CONTRACT_ADDRESS` in `dist/app.js`.

The browser app uses:

- network: `studionet`
- chain ID: `61999`
- RPC: `https://studio.genlayer.com/api`
- finalized reads: `TransactionHashVariant.LATEST_FINAL`
- writes: `writeContract()` followed by `TransactionStatus.FINALIZED`

The contract intentionally requires a 30-second minimum appeal window. For a smoke test, create a community, publish policy version 1, register a moderator, record an action, open an appeal with a short deadline, commit evidence from both sides, wait for the deadline, adjudicate, finalize, and claim the resulting credit.
