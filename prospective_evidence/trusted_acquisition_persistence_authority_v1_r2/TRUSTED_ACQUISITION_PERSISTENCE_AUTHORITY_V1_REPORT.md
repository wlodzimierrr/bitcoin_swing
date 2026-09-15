# TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1

- Ticket: `POSTP1-001V2B-R2`
- Definition hash: `bd55a3c0043c636f9e60db54e8f0d9fc72effd4e795b4518cad518608702c4fc`
- Classification: `TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1_READY_FOR_FINAL_XHIGH_REVIEW`
- Material children: 9

Verified collector execution now produces a canonical acquisition payload and an
Ed25519 signature. The production persistence owner reports success only after its
PostgreSQL commit and independent exact-envelope readback. Replay verifies the
immutable envelope against one frozen production public key and cross-checks every
denormalized projection.
The central runtime assertion also compares every effective production key/message
value with persisted parent-bound child artifacts. Both the write and confirmation
connections prove their actual session/current users, collector membership,
non-owner/non-superuser state, and exact effective table/schema privileges.
Self-hashes and provenance strings are descriptive and cannot establish origin.

The signature proves possession of the collector key for the exact payload; this
does not claim an independent third-party cryptographic TLS transcript.

## Material child hashes

| child | definition hash |
| --- | --- |
| `collector_creation_contract` | `c5ab6dda5848b96cd6e5a67b00b8a02c1ab7f422e89b678b34fd47cc90c3e228` |
| `creation_rehydration_failure_contract` | `cb7873976cc6450fd95c8d6c02e3352fca2088871ed675940f9b623f614064ea` |
| `executable_semantic_manifest` | `720f36ef254f0f803210763c6ba18b9a0c6de03fd17449d068ad81bc19cbce2e` |
| `postgres_persistence_privileges` | `75f19e3ba7ce60ff7132c96b7abbb7a4f6d097e28e0a7f4ba02275b4caa378ea` |
| `postgres_role_bootstrap` | `abb2c96fe279a9c7b83a8787fb01e6200897a94bfca2cd4dae860b88a2921ec9` |
| `signed_message_contract` | `b324126346c2aebfbc0bf3cb29eae99ecf0d18b0c5fa07c3a588e3563020c96a` |
| `signed_payload_envelope_schema` | `86c44364d3d71638e5edb0fb46a2a4c321f098c4d30367306463ea24338a7371` |
| `signing_key_registry` | `dc7d09644b0503bb1c7e78c9e3cf43d66561032cbc35aacafa4caa7b5e55d189` |
| `threat_security_boundary` | `515f81f8bb7905f8a5c1020580ca069764b19322119dc22bfc7254b652cfb35e` |

## Safety

No prospective observations were collected. Calendar certification, V2R1,
POSTP1-003R3, POSTP1-004, and collection remain blocked pending review and the
explicit downstream sequence. Disposable PostgreSQL 17 runtime validation passed;
this candidate is ready only for final xHigh review. BTC-019 and Epic T are unchanged.
