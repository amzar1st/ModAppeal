# ModAppeal — Decentralized Community Moderation & Appeal Protocol

- Live dashboard: https://modappeal.amzar1st96.chatgpt.site
- Studionet contract: https://explorer-studio.genlayer.com/address/0x5f4d4256736DC7B9288F4c02796c6A4c1b4B47c2
- Deployment transaction: https://explorer-studio.genlayer.com/tx/0x0b25ce86ed02f6c461622d55a0f1dea0c9c3b4cf5d4708ca348980619876e528

ModAppeal makes moderation appeals auditable without giving one administrator the final word. A community commits an immutable policy version, records the moderation action against that version, and lets the affected subject submit an appeal bond. Both parties can commit HTTPS evidence and counter-evidence. GenLayer validators independently inspect the same public sources and must agree on one categorical outcome:

- `VIOLATION_CONFIRMED`
- `ACTION_OVERTURNED`
- `PARTIAL_VIOLATION`
- `INSUFFICIENT_EVIDENCE`

The contract keeps validator reasoning separate from settlement. After consensus, deterministic contract code moves the appeal to `ADJUDICATED`, then `FINALIZED`, and exposes the recorded appellant or community-owner credit through `claim_bond()`.

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

The final deployment passed the entire production workflow on Studionet: community and immutable policy creation, moderator registration, action recording, a 1 GEN bonded appeal, evidence from both sides, validator adjudication, finalization, and bond claim. Validators independently fetched the SHA-256-pinned content and both evidence files. All three hashes were `VERIFIED`; the finalized verdict was `ACTION_OVERTURNED` at 100 confidence, and the appellant reclaimed the full bond.

- Case: `case-final-20260922`
- Adjudication transaction: https://explorer-studio.genlayer.com/tx/0xeab6ca73e51559b0d15b786f126e40393694445085f4fc460972ac35b0a41253
- Finalization transaction: https://explorer-studio.genlayer.com/tx/0xbd34baca35ab53319d4aabc6798ffb20d4c24d205c4e75d68d52722a4de755b6
- Bond claim transaction: https://explorer-studio.genlayer.com/tx/0x002624f942e68d8d081fd675b9f734adfdb7d729df0004c96dbef70bd214a8bb
- Machine-readable record: `deploy/live-test.json`

## Safety model

- Policy text and its SHA-256 rules fingerprint are versioned on-chain.
- Moderation actions pin the policy version, content URL, and content fingerprint.
- Evidence URLs must be HTTPS, are deduplicated, and carry a committed SHA-256 fingerprint.
- Validators adjudicate only the exact bytes whose SHA-256 fingerprints match the on-chain commitments.
- Web content is treated as untrusted evidence; prompt instructions found in pages are ignored.
- Bond accounting is deterministic and happens only after validator classification.
