# ModAppeal — Decentralized Community Moderation & Appeal Protocol

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

The app is a static, wallet-connected dashboard. It reads canonical `LATEST_FINAL` state and waits for finalized receipts for writes. The deployed contract address is recorded in `dist/app.js` after deployment.

## Safety model

- Policy text and its SHA-256 rules fingerprint are versioned on-chain.
- Moderation actions pin the policy version, content URL, and content fingerprint.
- Evidence URLs must be HTTPS, are deduplicated, and carry a committed SHA-256 fingerprint.
- Web content is treated as untrusted evidence; prompt instructions found in pages are ignored.
- Bond accounting is deterministic and happens only after validator classification.
