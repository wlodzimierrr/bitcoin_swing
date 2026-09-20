# ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1 — bootstrap-bound isolated one-shot scientific worker

- Ticket: `POSTP1-001V2A-PAD4-R2`
- Decision hash: `68e6bd074a027900b2f3dde3da0a31b6d1cb2f1b9fc6c563e9b45bdc70e52561`
- Corrected predecessor: `3415765f63a902e415e039ea71892087274541c1e8976a46d41c8f4afde37ebc` (failed, never certified, never overwritten)
- Status: `FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_XHIGH_REVIEW`
- Classification: `ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_R2_READY_FOR_FINAL_XHIGH_REVIEW`
- Strategy: `BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING_PLUS_CERTIFIED_SOURCE_AUTHORITY_PLUS_FROZEN_THIRD_PARTY_ARTIFACT_AUTHORITY_PLUS_FROZEN_CPYTHON_PLUS_FRESH_EMPTY_BYTECODE_CACHE_NAMESPACE_PLUS_CLOSED_STORE_GRAMMAR_PLUS_COMPILED_ROOT_WITNESS_PLUS_ONE_SHOT_EXEC_ISOLATED_SCIENTIFIC_WORKER_PLUS_TRUSTED_CONTROLLER_AUTHORITY_CONTEXT`
- Material children: 22
- Pre-I2 source fixture: 116 modules at `674b006ae66b8aace3458cb870f898ecad33e1f23833436954d36749b3aadbb8`
- Candidate worker source universe: 120 modules at `7ffbf15792d33e0cd387eb995d8d733c1fa1b98b2859153957c670f796a44e8e`
- Bootstrap source set: 4 files at `1811e04dac7a033de2c8e6620bf7d5aa227b94eebdf419657ecccf4d3fead411`
- Third-party authority digest: `23e4f1d89a503b43fc39ee0ae3516b742f6db72028224d78a9181be6726298a6`

## What this corrects, and what it does not

`POSTP1-002V2A-PAD4-R1` independently regenerated the exact `PAD4-R1` parent
`3415765f63a902e415e039ea71892087274541c1e8976a46d41c8f4afde37ebc`, reproduced 20/20 material children and 20/20 parent
bindings, and failed the candidate with `FAIL — WORKER BOOTSTRAP SOURCE NOT BOUND BEFORE EXECUTION`.

The blocking invariant was authority *ordering*, not isolation:

> Already-trusted code does not establish the certified identity of the worker
> bootstrap source before that source executes.

The controller allocated the fresh cache namespace, built the parent-bound
launch material and exec'd the entrypoint path directly. The frozen expected
manifest was compared against disk inside the worker, by the worker's own
protocol module, so every module that had to execute in order to reach that
comparison was outside it: the manifest check was the first thing the bootstrap
did, not the last thing the controller did. Two stable pre-launch drift probes
proved this was authoritative rather than merely undetected — entrypoint drift
and protocol drift each left the execution marker **PRESENT** and each had a
fabricated scientific result **ADMITTED**.

This is a bounded correction of that one ordering defect. It is deliberately
**not** a `PAD5`: no new proof-architecture family is created, the failed
`PAD4` namespace at `cc1b325a656f5b0be046d46700a4fcb9ad7ad94bf9b3440acac164677b809e78` and the failed `PAD4-R1` namespace
at `3415765f63a902e415e039ea71892087274541c1e8976a46d41c8f4afde37ebc` both keep their own untouched namespaces and both
remain failed, non-certified, unused, immutable, superseded before use and at
zero observations. Same-process runtime-object attestation is **not** reopened,
and `-X pycache_prefix` is **not** redesigned.

These portions were independently reproduced as valid by
`POSTP1-002V2A-PAD4-R1` and are carried forward intact rather than rebuilt:

- `BYTECODE_EXECUTION_BINDING_REPAIR_A`
- `CANONICAL_NON_EXECUTABLE_IPC`
- `CLOSED_STORE_GRAMMAR`
- `COMPILED_ROOT_WITNESS`
- `DIRECT_DEPENDENCY_BODY_RULE`
- `EXACT_ELEVEN_OWNER_GRAPH`
- `FRESH_EMPTY_PYCACHE_NAMESPACE`
- `FRESH_EXEC_ISOLATION`
- `FROZEN_SOURCE_AUTHORITY_FOR_ORDINARY_CERTIFIED_SOURCE_REPAIR_B`
- `ONE_REQUEST_ONE_PROCESS_LIFECYCLE`
- `RECORD_INSTALLED_CONTENT_VERIFICATION_BEFORE_DEPENDENCY_EXECUTION`
- `THIRD_PARTY_EXACT_VERSION_AND_ARTIFACT_AUTHORITY_REPAIR_D`
- `TRUSTED_CONTROLLER_AUTHORITY_CONTEXT_REPAIR_C`

## The complete pre-trust bootstrap source set

The review named two filenames in its P0 findings. The corrected set is derived
mechanically instead — the transitive *module-level* project-import closure of
the exec'd entrypoint plus every ancestor package — and it is wider than two
files, in this execution order:

1. `etf_calendar_worker/__init__.py`
2. `etf_calendar_worker/protocol_r1.py`
3. `etf_calendar_worker/protocol_r2.py`
4. `etf_calendar_worker/entry_r2.py`

`etf_calendar_worker/__init__.py` is a member because importing the protocol
executes the package initializer first, and `PAD4-R1` covered it by neither
`worker_entrypoint_sha256` nor `worker_protocol_sha256`.
`etf_calendar_worker/protocol_r1.py` is a member because the reviewed `PAD4-R1`
protocol implementation is *reused rather than forked*, so it executes during
bootstrap too. Every member is also an ordinary member of the certified source
manifest with the identical path and SHA-256; the bootstrap manifest is not a
second, weaker source of truth.

Three closure properties are proven mechanically, and together they are what
makes a finite set a complete one: no bootstrap module declares a module-level
project import outside the set; no bootstrap module declares a module-level
import outside the standard library, so no third-party code can run before the
reviewed installed-content attestation; and every deferred, function-scoped
project import declared by a bootstrap module is an ordinary certified manifest
member that Repair B already covers. The closed worker-coding rule is enforced
over the whole set rather than over two filenames.

## Trusted controller pre-execution binding

```
NO_PROJECT_OWNED_WORKER_BOOTSTRAP_SOURCE_MAY_EXECUTE_UNTIL_ALREADY_TRUSTED_CONTROLLER_CODE_HAS_ESTABLISHED_ITS_EXPECTED_PATH_AND_SOURCE_SHA_AGAINST_THE_TRUSTED_SCIENTIFIC_WORKER_AUTHORITY_CONTEXT
```

Before a worker process can exist, already-trusted controller code receives the
trusted `ScientificWorkerAuthorityContext`, takes the expected bootstrap
manifest from it, resolves each expected source beneath the certified project
root, reads the exact bytes, computes SHA-256, compares path and SHA against the
trusted expected authority, and refuses immediately on any mismatch. Only after
every bootstrap source passes does it allocate the fresh empty bytecode-cache
namespace and exec the frozen interpreter.

    bootstrap mismatch -> the subprocess is NEVER spawned.

Per source the binding checks the expected relative path, the resolved expected
project root, the absence of any alternate source candidate, the absence of a
sourceless bytecode replacement, regular certified-source file semantics, the
absence of an earlier `sys.path` entry that would shadow the worker package,
and the exact SHA-256. Module name alone is never identity.

`run_scientific_worker(authority_context, request, launch)` is the only
supported scientific launch path and the context is a required positional
argument, so bootstrap pre-verification is unavoidable.
`_spawn_unverified_worker_process` remains as a **private, non-authoritative**
raw helper; scientific admission never uses it, and it exists so the reviewed
`PAD4-R1` defect can be reproduced deliberately under test.

## No bootstrap self-certification

```
bootstrap_self_verification_is_authority            = false
entrypoint_self_verification_is_authority           = false
protocol_self_verification_is_authority             = false
package_initializer_self_verification_is_authority  = false
```

The in-worker bootstrap checks are retained as
`DEFENCE_IN_DEPTH_NEVER_PRIMARY_BOOTSTRAP_AUTHORITY`. No worker-visible shared secret
was invented as a substitute for correct pre-exec ordering.

## Frozen proof order

```
TRUSTED CONTROLLER
1  load the trusted authority context
2  establish the expected bootstrap source set
3  resolve, read and hash every bootstrap source
4  compare every path and SHA with the trusted authority
5  any mismatch -> STOP, no subprocess
6  allocate the fresh pycache namespace
7  exec the exact frozen interpreter

WORKER
8  verify interpreter and cache startup
9  parse the canonical request
10 defence-in-depth source checks
11 verify the third-party environment before dependency code
12 establish certified project imports
13 execute exactly one scientific operation
14 refuse a lazy result
15 post-verify
16 emit the canonical result
17 exit

CONTROLLER
18 verify process success
19 verify request == trusted context
20 verify response == trusted context
21 verify response == request
22 verify the result digest
23 admit
```

No bootstrap project source executes before step 4 succeeds.

## Preserved Repair A — executed bytecode is bound to certified source

Every worker still runs under `-I -S -B` plus
`-X pycache_prefix=<fresh empty per-worker directory>`. The namespace
is controller-created, proven empty before launch, never shared with any
repository or `site-packages` `__pycache__`, never reused between workers, never
selected from the scientific request and removed after the worker exits. A
forged repository `.pyc` is not executed, a forged third-party `.pyc` is not
executed, a pre-populated "fresh" namespace refuses and a sourceless scientific
module shadow refuses. The `-X pycache_prefix` design is unchanged.

## Preserved Repair C — the trusted controller authority context

Admission still requires request equals context **and** response equals context
**and** response cross-binds to the request. `0000...0000` and
`deadbeef...deadbeef` still refuse. The review's secondary candidate — that
`candidate_review_authority_context` accepts any well-formed SHA — was
independently reproduced and reclassified as **not a defect**: constraining the
constructor to one literal value is exactly the self-hash fixed point this
architecture refuses, the hash's trust comes from the caller being the trusted
review or controller context, and the production context is derived from the
final calendar authority instead. `production_authority_context_from_calendar_authority`
still refuses with `PRODUCTION_AUTHORITY_CONTEXT_NOT_YET_BOUND_BY_POSTP1_001V2A_I2`, and it now also
requires the final authority to bind the exact bootstrap manifest.

## Preserved Repair D — third-party semantic and installed-content authority

The exact reviewed registry is unchanged:

- `alembic` `1.19.1` roots `alembic` RECORD `ebbb23640b1d2a9c5554db547f0af8ce79c36320e268ed25a376851e3c40dbe7` content `86960035cb916589bea1fe28cf60646154484567b8b53f1247390699ad50a6f9`
- `cryptography` `50.0.1` roots `cryptography` RECORD `e77cb6a30c87bdac2ee2ec0819a509ca45f660bd263f41da1f21ac3b48f2fb8b` content `68c3a09f5bad49e0c7a0dfa968536d85f873e5022f34e00a9f636929f1e32d59`
- `numpy` `2.5.2` roots `numpy` RECORD `7cde927bec887ea8c7a9be3d1e5c6719e504b4e11e29bddc66ed328f64dd9faa` content `cb22b41061e85436627479fe57d26d119da169035a0cac36380b84c26c3014c3`
- `scipy` `1.18.1` roots `scipy` RECORD `d376f6be3fce626b65090112b4498ae3221a25f6c8cb8d5fe46dd9f31d324858` content `c103a8d760286c146a96259969b44d6d4694c12f152d66e6e19b5829d459cd84`
- `sqlalchemy` `2.0.52` roots `sqlalchemy` RECORD `c386ba92b9d4998a846119301af8e71e13c741826ad4e6ad9103bde4b390a5b9` content `0a236c13e7c0de3426b0d4611965a03801c241bbd2feab0a23fc65d1bcf13807`

Installed bytes are still verified against `RECORD` before any dependency
executes, a tampered dependency's marker stays absent, and a `99.99.99-FORGED`
version still refuses. The review's secondary P3 candidate about
`worker_protocol_placement_reason` was independently reproduced — importing the
top-level `btc_predictor` namespace alone executes none of the four
distributions, while importing `btc_predictor.research`, which every frozen
operation requires, executes all four — and corrected as a mechanical
documentation wording change that alters no proof architecture.

## Preserved static authority

Compiled root-binding witness, root-cell prohibition, closed AST store-use
grammar, the exact eleven-owner census and the documented `put`, `get`, `records`, `envelopes`
terminals are preserved and freshly parent-bound.

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

## Failed architecture lineage, preserved and never certified

- `0c237c1b217b1fd406ec3967309774293c01d3e27574b9f4a7d1b9a0e887b55d`
- `a7d2b08741080494cc4ca0269bf21e28e631c7f2e70887bcb0e1beb302534dd0`
- `dc36ffe228b7a3bc6d9145042b4e301c8624c99a79d71a88b46fc268f1372c3e`
- `9f6af1794e8b49dce38288b9f1b9710bffd04ba70303b5c380e8fb447ac86295`
- `7ef114fede9efebe594f0ecf119d097a1161119f448737d0df10afdf9468d17b`
- `b5ca36bfa9b96970b667cc44b10c5c5da7eb5ce7c57e5739601640d9b2a8abe9`
- `b8f8b92d4e3c1c80c4226f7101e71f95d125bd48afbfcde72e489408f6b5b996`
- `cc1b325a656f5b0be046d46700a4fcb9ad7ad94bf9b3440acac164677b809e78`
- `3415765f63a902e415e039ea71892087274541c1e8976a46d41c8f4afde37ebc`

## Current production and authorization

No ETF calendar production code was modified. Current production still reports
compiled root write, clear or delete findings
`0`, the single
`common_etf_session_status` generator capture, the five
wrapper-installed dependency guards and no isolated worker, so full conformance
is `NO` and calendar
implementation stays `BLOCKED`.

The frozen proof interpreter is
`cpython 3.12.14`
with cache tag `cpython-312` and magic
`cb0d0d0a`.

Successful implementation authorizes only `POSTP1-002V2A-PAD4-R2_INDEPENDENT_EXACT_HASH_XHIGH_PROOF_ARCHITECTURE_REVIEW`. Only that review
PASS may authorize `POSTP1-001V2A-I2`, which must then bind the certified
`PAD4-R2` hash into the final calendar authority, derive and
calendar-parent-bind both the final post-I2 project source manifest **and** the
final post-I2 bootstrap source set, and refreeze
`ETF_PUBLICATION_CALENDAR_AUTHORITY_V1` before an independent exact-hash
calendar closure review. Collection remains **NOT AUTHORIZED** and prospective
observations remain **0**.
