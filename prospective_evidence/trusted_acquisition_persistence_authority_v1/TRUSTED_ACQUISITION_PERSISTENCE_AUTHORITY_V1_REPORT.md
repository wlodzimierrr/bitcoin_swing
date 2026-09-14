# TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1

- Ticket: `POSTP1-001V2B`
- Definition hash: `c3619b7a72d2ee04247139f47130b995e8ef00514c6e2a736435ba4f2a223554`
- Classification: `TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1_READY_FOR_XHIGH_REVIEW`
- Material children: 8

Verified collector execution now produces a canonical acquisition payload, an
Ed25519 signature, and a collector-only PostgreSQL append. Replay loads the
immutable envelope and verifies it offline against one frozen production public key.
Self-hashes and provenance strings are descriptive and cannot establish origin.

The signature proves possession of the collector key for the exact payload; this
does not claim an independent third-party cryptographic TLS transcript.

## Material child hashes

| child | definition hash |
| --- | --- |
| `collector_creation_contract` | `47d169718282fb5f0be914e0fff0e69330f23e9ba487bb732ddc7b5d22661d5a` |
| `creation_rehydration_failure_contract` | `9922dd9cdb24359514001c9c9b5e2eda211f3fc07b5a40015f12077d3269e6e0` |
| `executable_semantic_manifest` | `70fc50f85aeaf2550c99272b1151ae1328b0a1bce854960ef3a1783442ef818a` |
| `postgres_persistence_privileges` | `73abce685f072ce62589ef49974aaabac759fa1b4cafb474fbfc5d6466088c72` |
| `signed_message_contract` | `b324126346c2aebfbc0bf3cb29eae99ecf0d18b0c5fa07c3a588e3563020c96a` |
| `signed_payload_envelope_schema` | `dc49e64e035c93c81b118f8a65bb8e9eafbf538b07dd11504fa68cf0dfbe2ce5` |
| `signing_key_registry` | `398d289d1b61314a249ba28193384897406790dee0a90d1d41e0d7e7772bcbd3` |
| `threat_security_boundary` | `515f81f8bb7905f8a5c1020580ca069764b19322119dc22bfc7254b652cfb35e` |

## Safety

No prospective observations were collected. Calendar certification, V2R1,
POSTP1-003R3, POSTP1-004, and collection remain blocked pending review and the
explicit downstream sequence. BTC-019 and Epic T are unchanged.
