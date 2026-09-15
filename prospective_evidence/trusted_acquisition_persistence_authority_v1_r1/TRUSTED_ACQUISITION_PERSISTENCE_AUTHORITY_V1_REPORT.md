# TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1

- Ticket: `POSTP1-001V2B-R1`
- Definition hash: `240985bf042bc6b9910e39f6c5e170dc22a0385d93ef2f17fecc21c0adee7bd0`
- Classification: `TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1_READY_FOR_REPEAT_XHIGH_REVIEW`
- Material children: 9

Verified collector execution now produces a canonical acquisition payload and an
Ed25519 signature. The production persistence owner reports success only after its
PostgreSQL commit and independent exact-envelope readback. Replay verifies the
immutable envelope against one frozen production public key and cross-checks every
denormalized projection.
Self-hashes and provenance strings are descriptive and cannot establish origin.

The signature proves possession of the collector key for the exact payload; this
does not claim an independent third-party cryptographic TLS transcript.

## Material child hashes

| child | definition hash |
| --- | --- |
| `collector_creation_contract` | `c5ab6dda5848b96cd6e5a67b00b8a02c1ab7f422e89b678b34fd47cc90c3e228` |
| `creation_rehydration_failure_contract` | `8a6cd8e689f597b6ca57ff21f65bef041d7497a1bbd532551ef415f44860dde5` |
| `executable_semantic_manifest` | `74eb3e8b576f91e7c2fd71e5b0979e1b5445b9357b7b22c3e4e7aa9a22ee7eda` |
| `postgres_persistence_privileges` | `21dae015269524c42bcb64f4d8cacb795dcc5afa95deaf1446ef824f322e3a81` |
| `postgres_role_bootstrap` | `66e2edfbfaae4f6f2d96333af53d95365e1c5ffc4abfd176db79baff913915e9` |
| `signed_message_contract` | `b324126346c2aebfbc0bf3cb29eae99ecf0d18b0c5fa07c3a588e3563020c96a` |
| `signed_payload_envelope_schema` | `86c44364d3d71638e5edb0fb46a2a4c321f098c4d30367306463ea24338a7371` |
| `signing_key_registry` | `dc7d09644b0503bb1c7e78c9e3cf43d66561032cbc35aacafa4caa7b5e55d189` |
| `threat_security_boundary` | `515f81f8bb7905f8a5c1020580ca069764b19322119dc22bfc7254b652cfb35e` |

## Safety

No prospective observations were collected. Calendar certification, V2R1,
POSTP1-003R3, POSTP1-004, and collection remain blocked pending review and the
explicit downstream sequence. BTC-019 and Epic T are unchanged.
