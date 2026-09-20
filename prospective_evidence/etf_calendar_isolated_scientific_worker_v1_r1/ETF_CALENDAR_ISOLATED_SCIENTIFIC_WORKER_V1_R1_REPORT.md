# ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1 — corrected isolated one-shot scientific worker

- Ticket: `POSTP1-001V2A-PAD4-R1`
- Decision hash: `3415765f63a902e415e039ea71892087274541c1e8976a46d41c8f4afde37ebc`
- Corrected predecessor: `cc1b325a656f5b0be046d46700a4fcb9ad7ad94bf9b3440acac164677b809e78` (failed, never certified, never overwritten)
- Status: `FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_XHIGH_REVIEW`
- Classification: `ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_R1_READY_FOR_FINAL_XHIGH_REVIEW`
- Strategy: `CERTIFIED_SOURCE_AUTHORITY_PLUS_FROZEN_THIRD_PARTY_ARTIFACT_AUTHORITY_PLUS_FROZEN_CPYTHON_PLUS_FRESH_EMPTY_BYTECODE_CACHE_NAMESPACE_PLUS_CLOSED_STORE_GRAMMAR_PLUS_COMPILED_ROOT_WITNESS_PLUS_ONE_SHOT_EXEC_ISOLATED_SCIENTIFIC_WORKER_PLUS_TRUSTED_CONTROLLER_AUTHORITY_CONTEXT`
- Material children: 20
- Pre-I2 source fixture: 116 modules at `674b006ae66b8aace3458cb870f898ecad33e1f23833436954d36749b3aadbb8`
- Candidate worker source universe: 119 modules at `c6a71401a3d240c3196be0ef51a3fd14b93e44022baeaacfafe1112b7aa89332`
- Third-party authority digest: `23e4f1d89a503b43fc39ee0ae3516b742f6db72028224d78a9181be6726298a6`

## What this corrects, and what it does not

`POSTP1-002V2A-PAD4` independently reproduced the `PAD4` parent and found the
fresh-exec process-isolation boundary **sound**. It failed the candidate with
`FAIL — EXECUTED BYTECODE NOT BOUND TO CERTIFIED SOURCE` plus three further release-critical
authority-anchoring defects. This ticket is a bounded correction of exactly
those four findings:

1. **Executed bytecode was not bound to certified source.** `-B`
   suppresses bytecode *writes* only; nothing suppressed or validated bytecode
   *reads*. A forged timestamp-valid `__pycache__/flow.cpython-312.pyc`
   executed while the certified `.py` bytes were unchanged, and the controller
   admitted `FORGED_BYTECODE_ID`. The repair is structural: every worker runs
   under `-X pycache_prefix=<fresh empty per-worker directory>`, the
   namespace is controller-created, verified empty before launch and removed
   afterwards, and the worker refuses unless `sys.pycache_prefix` is exactly
   the declared namespace, `sys.dont_write_bytecode` is `True` and the
   namespace is empty. Adjacent `__pycache__` directories are then never
   consulted at all, for certified project source and for installed
   third-party source alike, and every loaded module's `__cached__` path must
   lie inside the namespace.
2. **Certified source authority was not frozen.** Request construction derived
   the manifest from live disk and verified the worker against that same newly
   derived manifest, so drift existing *before* request construction
   self-certified. Authority construction and runtime are now two distinct
   operations: derivation from reviewed source happens only at authority
   construction or refreeze, and runtime consumes an already-frozen expected
   manifest.
3. **Controller authority binding was invalid.** The decision hash was a
   request/response echo, so `0000...0000` and `deadbeef...deadbeef` were both
   admitted with real scientific results. Every material authority identity is
   now compared against a trusted `ScientificWorkerAuthorityContext` that a
   request cannot construct, a response cannot construct, live disk cannot
   silently replace and the installed environment cannot silently replace.
4. **Third-party installed content and semantics were not attested.**
   Verification hashed only `RECORD`, and the declared version was compared to
   nothing. The reviewed semantic and artifact registry is now frozen, and
   every installed file byte the reviewed `RECORD` declares a hash for is
   verified before any dependency code executes.

Same-process runtime-owner attestation, transitive mutable-object closure,
reflection-blacklist completeness and generated-method enumeration are **not**
reopened. This is a correction of `PAD4`, not a new architecture family, and no
`PAD5` exists.

## Preserved closed-input isolation boundary

The proven boundary is unchanged and still required: a fresh exec'd CPython
3.12.14 worker under `-I -S -B`, one request per
process, no parent Python object sharing, canonical JSON IPC, no
pickle/cloudpickle/dill/marshal IPC, lazy-result refusal, controller result
admission, fork-only refusal and parent monkeypatch isolation.

## Exact interpreter

- implementation: `cpython`
- version: `3.12.14 final/0`
- hexversion: `51121904`
- cache tag: `cpython-312`
- bytecode magic: `cb0d0d0a`

## Source authority and the pre-I2 fixture

`ETF_CALENDAR_WORKER_PRE_I2_SOURCE_MANIFEST_FIXTURE_V1` freezes the exact reviewed current source universe —
116 modules at
`674b006ae66b8aace3458cb870f898ecad33e1f23833436954d36749b3aadbb8` — as literal material, so
it stays immutable when `POSTP1-001V2A-I2` later rewrites
`etf_publication_calendar.py`. Its role is an architecture conformance test
vector, provenance and a pre-I2 source-drift regression anchor. It is
explicitly **not** the future production scientific source authority.

`POSTP1-001V2A-I2` must derive the exact final worker project-source manifest
*after* all its source changes are complete and parent-bind that exact manifest
and digest to `ETF_PUBLICATION_CALENDAR_AUTHORITY_V1`. I2 may perform the
anticipated direct-import reduction, provided the calendar science, the
outputs and the replay-owner graph are unchanged and the manifest is
mechanically re-derived. This proof-architecture hash does not change merely
because the eventual production source manifest becomes narrower.

## Reviewed third-party authority

- `alembic` `1.19.1` roots `alembic` RECORD `ebbb23640b1d2a9c5554db547f0af8ce79c36320e268ed25a376851e3c40dbe7` content `86960035cb916589bea1fe28cf60646154484567b8b53f1247390699ad50a6f9`
- `cryptography` `50.0.1` roots `cryptography` RECORD `e77cb6a30c87bdac2ee2ec0819a509ca45f660bd263f41da1f21ac3b48f2fb8b` content `68c3a09f5bad49e0c7a0dfa968536d85f873e5022f34e00a9f636929f1e32d59`
- `numpy` `2.5.2` roots `numpy` RECORD `7cde927bec887ea8c7a9be3d1e5c6719e504b4e11e29bddc66ed328f64dd9faa` content `cb22b41061e85436627479fe57d26d119da169035a0cac36380b84c26c3014c3`
- `scipy` `1.18.1` roots `scipy` RECORD `d376f6be3fce626b65090112b4498ae3221a25f6c8cb8d5fe46dd9f31d324858` content `c103a8d760286c146a96259969b44d6d4694c12f152d66e6e19b5829d459cd84`
- `sqlalchemy` `2.0.52` roots `sqlalchemy` RECORD `c386ba92b9d4998a846119301af8e71e13c741826ad4e6ad9103bde4b390a5b9` content `0a236c13e7c0de3426b0d4611965a03801c241bbd2feab0a23fc65d1bcf13807`

An observed version that differs from the frozen reviewed version refuses. A
same-version but different unreviewed artifact refuses, because the reviewed
`RECORD` artifact digest and normalized content-manifest digest are both
parent-bound. Absolute install locations and `RECORD` paths remain launch
material, never scientific authority.

## Authority context and the self-hash boundary

The candidate parent hash cannot be materially embedded inside itself, and no
cryptographic self-hash fixed point is attempted. The architecture uses a
two-stage boundary: while this candidate is under review the reviewer or the
test harness instantiates the trusted context with the *recomputed* parent
hash, which comes from the trusted review context and never from the scientific
request. After a review PASS, `POSTP1-001V2A-I2` binds the exact certified
`PAD4-R1` hash into the final calendar authority, where no self-reference
exists because the proof-architecture hash is already certified before the
final `ETF_PUBLICATION_CALENDAR_AUTHORITY_V1` hash is created. Until I2 does
so, `production_authority_context_from_calendar_authority` refuses with
`PRODUCTION_AUTHORITY_CONTEXT_NOT_YET_BOUND_BY_POSTP1_001V2A_I2`.

## Accepted limits

No operating-system-level network sandbox is claimed and none is added here.
Hostile filesystem race resistance is explicitly not claimed: a malicious
modification perfectly racing verification or use is outside the accepted
trusted-operating-system boundary. The requirement is deterministic project and
deployment integrity, not hostile kernel defence. The dynamic-import claim is
scoped precisely: authoritative worker entry/protocol dynamic project execution
is forbidden and statically audited, the certified source universe is
mechanically derived from static import declarations, and an unexpected loaded
project module refuses. There is no universal claim that every certified module
is free of every dynamic import mechanism.

## Preserved static authority

The compiled root-binding witness, the root-cell prohibition, the closed AST
store-use grammar, the exact eleven-owner census and graph and the direct
dependency-body requirement are preserved and freshly parent-bound. The failed
PAD2, PAD3 and PAD4 parents are not certified. The owners remain exactly:

- `derive_normalized_schedule_from_official_source`
- `venue_session_calendar_record`
- `_verify_schedule`
- `_verify_schedule_record`
- `validate_normalized_schedule_against_source`
- `_verify_venue_row`
- `venue_session_status`
- `common_etf_session_status`
- `expected_etf_publication_dates`
- `derive_etf_window_calendar`
- `scientific_etf_flow_window`

Every owner path still terminates at a documented store API
(`put`, `get`, `records`, `envelopes`), cycles and unknown forwarding remain forbidden, and
`assert_trusted_persistence_dependency()` must still execute directly inside
each of the five required bodies. Process isolation does not legalize wrappers.

## Current production

- reviewed calendar source: `49fa356e48426aaaea0be987930062f85058839f9efd73feb2d210b3b79c4145`
- root write/clear/delete findings: 0
- root-cell blocker: `common_etf_session_status:evidence_store`
- AST store grammar: `REFUSED_AT_THE_SAME_GENERATOR_CAPTURE`
- wrapper-installer removal required: True
- corrected worker integrated in production: False
- full conformance: `NO`

## Failed lineage

All of the following remain failed, non-certified, unused, immutable and at
zero observations:

- `0c237c1b217b1fd406ec3967309774293c01d3e27574b9f4a7d1b9a0e887b55d`
- `a7d2b08741080494cc4ca0269bf21e28e631c7f2e70887bcb0e1beb302534dd0`
- `dc36ffe228b7a3bc6d9145042b4e301c8624c99a79d71a88b46fc268f1372c3e`
- `9f6af1794e8b49dce38288b9f1b9710bffd04ba70303b5c380e8fb447ac86295`
- `7ef114fede9efebe594f0ecf119d097a1161119f448737d0df10afdf9468d17b`
- `b5ca36bfa9b96970b667cc44b10c5c5da7eb5ce7c57e5739601640d9b2a8abe9`
- `b8f8b92d4e3c1c80c4226f7101e71f95d125bd48afbfcde72e489408f6b5b996`
- `cc1b325a656f5b0be046d46700a4fcb9ad7ad94bf9b3440acac164677b809e78`

Failed calendar authority hashes are preserved unchanged, the certified
predecessor corpus protocol
`8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7` and the
failed V2 `488251df7bc1b49f801caa0dc28eb5224836574b154db9e4a70d4be670ec0b6d`
are unchanged, and trusted persistence `02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772` remains
closed, certified and unchanged.

## Safety

Prospective observations remain 0. No real Stage-B evaluation ran. The calendar
authority is not certified, calendar implementation is blocked,
POSTP1-001V2A-I2, POSTP1-001V2R1, POSTP1-003R3 and POSTP1-004 are blocked,
collection is not authorized, BTC-019 is untouched and Epic T is unchanged.
This candidate authorizes only `POSTP1-002V2A-PAD4-R1_INDEPENDENT_EXACT_HASH_XHIGH_PROOF_ARCHITECTURE_REVIEW`.
