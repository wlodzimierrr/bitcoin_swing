# TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1

- Ticket: `POSTP1-001V2B-R1`
- Definition hash: `c412c1b80cef220220cdccd3c031e6694aa53451ef7ab63ac7ab9180e3e6857b`
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
| `collector_creation_contract` | `55b51df63ba11ff9f76a9fd9002130e21a7c1be8fd53977b2b437b242f574ed9` |
| `creation_rehydration_failure_contract` | `8a6cd8e689f597b6ca57ff21f65bef041d7497a1bbd532551ef415f44860dde5` |
| `executable_semantic_manifest` | `fd997cd70c2b2ec73b114a4c5f8c25326ae750292652fb0f9a1fbec8a3e56cbf` |
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
