# ModAppeal — Decentralized Community Moderation & Appeal Protocol

- Live dashboard: https://modappeal.amzar1st96.chatgpt.site
- Studionet contract: https://explorer-studio.genlayer.com/address/0x1Bc7cB40DB3781E835Ba23fF7E3a76698dF71d13
- Deployment transaction: https://explorer-studio.genlayer.com/tx/0x215d3b46b03dfcdd696058082461ef872e491192a064191d78acfb846337cc03

ModAppeal makes moderation appeals auditable without giving one administrator the final word. A community commits an immutable policy version, records the moderation action against that version, and lets the affected subject submit an appeal bond. Both parties can commit HTTPS evidence and counter-evidence. GenLayer validators independently inspect the same public sources and must agree on one categorical outcome:

- `VIOLATION_CONFIRMED`
- `ACTION_OVERTURNED`
- `PARTIAL_VIOLATION`
- `INSUFFICIENT_EVIDENCE`

The contract keeps validator reasoning separate from settlement. Unavailable sources and mismatched commitments are excluded from the validator record and attributed to the party that submitted them. Deterministic contract code then moves the appeal to `ADJUDICATED`, then `FINALIZED`, and exposes the recorded appellant or community-owner credit through `claim_bond()`.

## Contract workflow

`create_community` → `publish_policy` → `register_moderator` → `record_action` → `open_appeal` → `submit_evidence` / `submit_counter_evidence` → `adjudicate` → `finalize` → `claim_bond`

Public reads include `get_case`, `get_result`, `get_case_evidence`, `get_policy`, `get_protocol_stats`, and the case/community indexes.

## Run the local checks

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
node tests/test_frontend.mjs
```

The app is a static, wallet-connected dashboard. It reads canonical `LATEST_FINAL` state and waits for finalized receipts for writes. The Studionet address is pinned in `dist/app.js` and recorded in `deploy/deployment.json`.

## Live end-to-end proof

The v1.1 deployment passed an adversarial production workflow on Studionet. The appellant submitted a deliberately mismatched SHA-256 evidence commitment, then validators independently evaluated only the verified disputed content. Consensus returned `ACTION_OVERTURNED` at 92 confidence, but the contract attributed one invalid item to the appellant and applied `APPELLANT_INVALID_EVIDENCE_FORFEITURE`. The appellant received 0; the community received and claimed the entire 1 GEN bond. The final contract balance is 0.

- Case: `case-malicious-20260924`
- Malicious commitment transaction: https://explorer-studio.genlayer.com/tx/0xa7ec0e855c8209c34404ca63eb21a6cd66432907d636ad4c3ff789adb7fa4703
- Adjudication transaction: https://explorer-studio.genlayer.com/tx/0x05bd42914ec94d60a55c057e0d35c4ece4f8d770babb135e14fbbc068f519f90
- Finalization transaction: https://explorer-studio.genlayer.com/tx/0x478e1882e23b1f3927c99809b90052426c1ad1908797863e576fc1a6f09b13b7
- Bond claim transaction: https://explorer-studio.genlayer.com/tx/0xb89af82170bf4c7e6319ad2caa831ceae98ed4a3c03ee5360a5f82bcf798758d
- Machine-readable record: `deploy/live-test.json`

## Safety model

- Policy text and its SHA-256 rules fingerprint are versioned on-chain.
- Moderation actions pin the policy version, content URL, and content fingerprint.
- Evidence URLs must be HTTPS, are deduplicated, and carry a committed SHA-256 fingerprint.
- Validators adjudicate only the exact bytes whose SHA-256 fingerprints match the on-chain commitments.
- Each party has six independently reserved evidence slots, so neither side can crowd out the other.
- `MISMATCH` and `UNAVAILABLE` submissions are attributed to their submitter instead of poisoning the whole case.
- An appellant evidence fault forfeits the bond to the community; a moderator/content fault refunds it to the appellant; faults by both sides split it.
- Web content is treated as untrusted evidence; prompt instructions found in pages are ignored.
- Bond accounting is deterministic and happens only after validator classification.

The 20-test behavioral suite covers malicious hash commitments, source fetch failures on either side, evidence-capacity crowd-out, disputed-content failures, dual-role claims, and every resulting bond allocation.
