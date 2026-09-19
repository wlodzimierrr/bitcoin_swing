# ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1 — isolated one-shot scientific worker

- Ticket: `POSTP1-001V2A-PAD4`
- Decision hash: `cc1b325a656f5b0be046d46700a4fcb9ad7ad94bf9b3440acac164677b809e78`
- Failed parent: `b8f8b92d4e3c1c80c4226f7101e71f95d125bd48afbfcde72e489408f6b5b996` (never certified)
- Status: `FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_XHIGH_REVIEW`
- Classification: `ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_READY_FOR_XHIGH_REVIEW`
- Strategy: `CERTIFIED_SOURCE_PLUS_FROZEN_CPYTHON_PLUS_CLOSED_STORE_GRAMMAR_PLUS_COMPILED_ROOT_WITNESS_PLUS_ONE_SHOT_EXEC_ISOLATED_SCIENTIFIC_WORKER`
- Material children: 17
- Certified worker project source modules: 116
- Worker project source manifest digest: `674b006ae66b8aace3458cb870f898ecad33e1f23833436954d36749b3aadbb8`

## Why same-process identity was abandoned

`POSTP1-002V2A-PAD3` failed with `PROJECT IMPORT EXECUTION CLOSURE INCOMPLETE`.
A clean attestation of the eleven frozen replay owners plus the calendar
module's own functions, classes, values and imports left the complete
attestation digest unchanged while persistent mutation of
`_flow.FIVE_DAY_ETF_FLOW_WINDOW_DAYS`, `_flow.FIVE_DAY_ETF_FLOW_FEATURE_ID`,
`_flow.EtfFlowFeatureResult`, the `require_utc_datetime` re-export origin and
the dataclass-generated `ScientificEtfFlowResult.__init__` changed the
scientific answer.

Each previous decision answered a defect by enlarging the enumerated surface.
That is not a bounded completeness argument: the mutable execution surface
expands transitively through project-owned modules and generated runtime
objects, so the enumeration can always be one object short. This decision
therefore changes the boundary instead of the list:

> do not share mutable Python scientific execution state with the application
> process.

The following are explicitly abandoned as completeness proofs: recursive
same-process runtime object attestation, transitive mutable-object closure
across the repository, reflection blacklist completeness, and
generated-runtime-method enumeration. PAD3's measured closure of
7 classes, 25 functions, 14 imports, 15 values survives only as archived diagnostic evidence explaining why
PAD3 failed.

## The scientific worker

`ETF_CALENDAR_SCIENTIFIC_WORKER` is a fresh operating-system process created by
an exec-style launch of the exact frozen interpreter, with a fresh
`sys.modules`, fresh project imports and no inherited Python module object. A
fork-only inherited interpreter is `NOT_AN_AUTHORIZED_SCIENTIFIC_WORKER`.
One request enters, one fully materialized response leaves, and the process
exits. There is no worker pool, no reuse, no background thread and no async
continuation. Given the system's low-frequency design, performance is
subordinate to proof simplicity.

The worker starts under `-I -S -B`: environment-variable
Python configuration ignored, user site disabled, `sitecustomize`/
`usercustomize` not executed, uncontrolled current-directory import precedence
disabled and `sys.path` explicitly parent-controlled. The child receives a
frozen minimal environment, so parent environment drift after controller
startup cannot change the child scientific import environment, and there is no
dependency on ambient `PYTHONPATH`.

## Exact interpreter

- implementation: `cpython`
- version: `3.12.14 final/0`
- hexversion: `51121904`
- cache tag: `cpython-312`
- bytecode magic: `cb0d0d0a`

Any mismatch is `REFUSE_SCIENTIFIC_AUTHORITY`. Standard-library
implementation semantics rely on this exact interpreter identity as an explicit
architecture axiom; stdlib Python objects are never recursively attested.

## Certified source universe, not object closure

`ETF_CALENDAR_WORKER_PROJECT_SOURCE_MANIFEST_V1` is the recursive project import closure of
the scientific worker entrypoint, derived mechanically from static import
declarations and every ancestor package, binding each module's canonical name,
canonical source path and SHA-256. No project-owned module outside the manifest
may execute in the worker. The proof boundary is *certified source modules*,
not every runtime constant, function or class object reachable after import,
because under a fresh one-shot process every project-owned runtime object —
including a dataclass-generated `__init__` — is freshly constructed from the
certified source universe under the frozen interpreter.

Third-party dependencies are explicitly frozen. The artifact freezes the rule
and the derived distribution roots; each launch binds the exact distribution,
version, install location and installed `RECORD` manifest digest into the
request, and the worker verifies them without `importlib`. Arbitrary
`site-packages` state is never scientific authority.

## Capability boundary

No parent Python object crosses the boundary: no function, class, module
object, live `CalendarEvidenceStore`, pickled object or callable. Pickle,
cloudpickle, dill and marshal are forbidden scientific IPC. The worker performs
no network I/O, loads no production signing key and writes no authoritative
database evidence; result admission stays a controller responsibility.

## Preserved static authority

The compiled root-binding witness, the root-cell prohibition, the closed AST
store-use grammar, the exact eleven-owner census and graph and the direct
dependency-body requirement are preserved and freshly parent-bound under this
decision. The failed PAD2 and PAD3 parents are not certified. The owners remain
exactly:

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
(`put`, `get`, `records`, `envelopes`), cycles and unknown forwarding remain forbidden,
and `assert_trusted_persistence_dependency()` must still execute directly
inside each of the five required bodies. Process isolation does not legalize
wrappers.

## Current production

- reviewed calendar source: `49fa356e48426aaaea0be987930062f85058839f9efd73feb2d210b3b79c4145`
- root write/clear/delete findings: 0
- root-cell blocker: `common_etf_session_status:evidence_store`
- AST store grammar: `REFUSED_AT_THE_SAME_GENERATOR_CAPTURE`
- wrapper-installer removal required: True
- isolated worker implemented in production: False
- full conformance: `NO`

## Failed lineage

All of the following remain failed, non-certified, unused and at zero
observations:

- `0c237c1b217b1fd406ec3967309774293c01d3e27574b9f4a7d1b9a0e887b55d`
- `a7d2b08741080494cc4ca0269bf21e28e631c7f2e70887bcb0e1beb302534dd0`
- `dc36ffe228b7a3bc6d9145042b4e301c8624c99a79d71a88b46fc268f1372c3e`
- `9f6af1794e8b49dce38288b9f1b9710bffd04ba70303b5c380e8fb447ac86295`
- `7ef114fede9efebe594f0ecf119d097a1161119f448737d0df10afdf9468d17b`
- `b5ca36bfa9b96970b667cc44b10c5c5da7eb5ce7c57e5739601640d9b2a8abe9`
- `b8f8b92d4e3c1c80c4226f7101e71f95d125bd48afbfcde72e489408f6b5b996`

Failed calendar authority hashes are preserved unchanged, the certified
predecessor corpus protocol `8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7`
and the failed V2 `488251df7bc1b49f801caa0dc28eb5224836574b154db9e4a70d4be670ec0b6d`
are unchanged, and trusted persistence `02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772` remains
closed, certified and unchanged.

## Safety

Prospective observations remain 0. No real Stage-B evaluation ran. The calendar
authority is not certified, calendar implementation is blocked, POSTP1-001V2R1,
POSTP1-003R3 and POSTP1-004 are blocked, collection is not authorized, BTC-019
is untouched and Epic T is unchanged. This candidate authorizes only
`POSTP1-002V2A-PAD4_INDEPENDENT_EXACT_HASH_XHIGH_PROOF_ARCHITECTURE_REVIEW`.
