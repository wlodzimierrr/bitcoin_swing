# ETF_CALENDAR_RUNTIME_OWNER_ATTESTATION_V1 — runtime owner attestation

- Ticket: `POSTP1-001V2A-PAD3`
- Decision hash: `b8f8b92d4e3c1c80c4226f7101e71f95d125bd48afbfcde72e489408f6b5b996`
- Failed parent: `b5ca36bfa9b96970b667cc44b10c5c5da7eb5ce7c57e5739601640d9b2a8abe9`
- Status: `FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_XHIGH_REVIEW`
- Classification: `ETF_CALENDAR_RUNTIME_OWNER_ATTESTATION_V1_READY_FOR_XHIGH_REVIEW`
- Strategy: `COMPILED_ROOT_WITNESS_PLUS_CLOSED_AST_STORE_USE_GRAMMAR_PLUS_RUNTIME_SCIENTIFIC_EXECUTION_EPOCH_ATTESTATION`
- Material children: 16

## Why the static owner-identity proof was replaced

`POSTP1-002V2A-PAD2` failed with `MODULE OWNER IDENTITY MODEL INCOMPLETE`.
Ordinary project-owned source using `sys.modules[__name__].__dict__["owner"] =
replacement` or `owner.__setattr__("__code__", replacement.__code__)` — and the
`object.__setattr__` and `type(owner).__setattr__` equivalents — passed the whole
static pipeline while replacing what the frozen owner executes. Enumerating more
reflection names is not a correction: the enumeration itself is the defect.

This decision freezes `STATIC_REFLECTION_BLACKLIST_IS_NOT_OWNER_IDENTITY_PROOF`
and sets `reflection_blacklist_complete = false`. The source-level reflection and
namespace checks survive only as diagnostics, defence in depth and coding-policy
enforcement. They are never scientific completeness authority again.

## What replaces it

Effective scientific owner identity is measured, not enumerated. Immediately
before and immediately after every authoritative calendar or replay computation,
each of the eleven frozen owners is read out of the loaded calendar module's own
`__dict__` — the namespace a call actually resolves through — and checked against
identity material derived by independently compiling the certified reviewed
source under frozen `cpython`
`3.12.14`
(magic `cb0d0d0a`, cache tag `cpython-312`).

The attested material is the binding's presence, its exact callable type, its
`__name__`, `__qualname__` and `__module__`, a deterministic recursive execution
fingerprint of its `__code__`, the identity of its `__globals__` and of its bound
builtins namespace, its closure contract, its `__defaults__` and `__kwdefaults__`
fingerprints and its wrapper state. The mutation syntax is irrelevant, because
none of this asks how the binding got there.

## The transitive execution closure

Attesting only the eleven entry bindings would measure who is called, not what
executes. An owner resolves other module-level names at call time, so a
persistent replacement of a reachable helper, result class, frozen constant or
imported dependency changes the scientific answer while every owner fingerprint
still matches byte for byte. The attested surface is therefore the transitive
execution closure, derived as a mechanical fixpoint over the module-level names
the certified owner code objects can actually load — seeded by the eleven owners
and by the `CalendarEvidenceStore` root type the owners declare, recursing into
nested code objects and reading instructions deoptimized. It is a derivation,
not a hand-maintained list, and a closure member missing from the frozen
expectation refuses.

Reachable functions carry the same identity contract as the owners. Reachable
classes are attested by exact metaclass, qualname, module, certified method code
fingerprints and method wrapper state, with an explicit census of any
uncertified function attribute. Reachable values are attested by a deterministic
deep typed fingerprint against the literal the reviewed source declares, and a
value that is not a reviewable literal refuses instead of being accepted.
Reachable project-owned imports are attested by `sys.modules` identity, origin
attribute identity and their own certified source digest, so drift in the
calendar semantics, flow or trusted-acquisition modules is refused too.
Interpreter-provided modules are attested by binding identity only; their
internals are not re-proved function by function, because the frozen proof
interpreter identity is already an explicit axiom of this architecture.

The module itself must also be the one callers reach: exactly a
`types.ModuleType`, the live `sys.modules` entry, the package attribute of the
same name, the only loaded instance of the certified source, and holding the
real builtins namespace. A loaded consumer that holds its own divergent binding
for a frozen owner name refuses as well.

Code identity is a fingerprint, not an object comparison: an independently
compiled equivalent code object is a different object, so
`function.__code__ is expected_code` would refuse honest sources. The fingerprint
covers the argument layout, flags, stack, name and variable tuples, the exception
table, the line table, the raw bytecode and a type-tagged canonical encoding of
the constant pool, recursing into every nested code object. `co_filename` is
excluded because it records where the text was read, and reviewed-source identity
is attested separately and exactly.

`__globals__` identity is required for its own reason: a
`types.FunctionType(expected_code, attacker_globals)` reconstruction matches the
code bytes exactly and would otherwise pass.

## The scientific execution epoch

One bounded unit encloses every authoritative computation: pre-execution
attestation, then the synchronous scientific computation in the very module
whose bindings were attested, then post-execution attestation, and only then
result admission or persistence. A pre-attestation mismatch is
`SCIENTIFIC_EXECUTION_NOT_AUTHORIZED` with no owner call, no partial result, no
persistence and no Stage-B evidence. A post-attestation that does not reproduce
the pre-attestation digest is `RESULT_REJECTED` / `DATA_QUALITY_FAIL`. There
is no persist-then-discover-mismatch path, and that is proven structurally over
this architecture's own source rather than asserted: the executor performs
exactly two attestations on the admitting path, the operation runs strictly
between them, and the admission call is unreachable until the post-attestation
refusal has not fired.

Because the admission call is the only place that may persist, the operation is
frozen as pure with respect to durable state: `THE_OPERATION_IS_PURE_WITH_RESPECT_TO_DURABLE_STATE_AND_ALL_ADMISSION_PERSISTENCE_AND_PUBLICATION_HAPPENS_IN_ADMIT_AFTER_POST_ATTESTATION`. A
lazy or deferred result would run its body after the measured window closed, so
`THE_ADMITTED_RESULT_MUST_BE_FULLY_EVALUATED_INSIDE_THE_EPOCH` and a generator, coroutine or lazy iterator result is
refused. Every exit path, including an exception raised by the operation, sweeps
for drift, so a failing epoch can never leave a persistent substitution silently
in place.

Pre-attestation catches persistent substitution from before the operation,
import-time mutation and startup drift. Post-attestation catches persistent
mutation that happened during the operation. Startup attestation additionally
refuses a process that is already wrong and records the baseline the first
pre-attestation must reproduce; it never replaces either. Import-time behaviour
is itself determined by the certified sources whose digests are attested, so the
residual window is the interval between the end of import and the startup
attestation, which the frozen ordering rule closes by running startup
attestation as the process's first action.

Epochs are serialised — `ONE_CALENDAR_SCIENTIFIC_EXECUTION_EPOCH_AT_A_TIME_PER_PROCESS` — and a nested or reentrant
epoch refuses. The lock exists for deterministic execution and configuration
integrity, not for hostile same-process security, and it does not serialise an
epoch against ordinary non-epoch threads.

## The bounded guarantee and its explicit limit

Any substitution or mutation anywhere in the attested closure that is still in
effect at either attestation point refuses before any result is admitted. Any
mutation that is fully reverted between the two attestation instants is **not**
detected, whatever its cause — including benign concurrent patch-and-restore by
project-owned code in a non-epoch thread, not only a deliberate adversary. That
case is classified as arbitrary adversarial same-process mutation and is outside
the accepted trust model, which is unchanged by this decision: the production
Python process is trusted, project-owned scientific drift and misconfiguration
are in scope, and arbitrary debugger, memory and interpreter mutation is out of
scope. If resistance to the transient case ever becomes required the escalation
is **process isolation**, never more Python reflection filters.

## Preserved layers

The compiled root-binding witness is re-adopted in full and freshly parent-bound:
the frozen CPython 3.12.14 identity, the exact opcode policy checked against the
interpreter's own tables, the deoptimized instruction scan, `TypeAlias` and
definition-time mutation detection, nested-body scoping correctness and the
structural rule that a conforming root may never be a cell variable. The failed
PAD2 parent itself is not certified.

The closed AST store-use grammar is preserved unchanged: an ordinary explicit
store parameter only, with aliases, store variadics, starred forwarding, bound
methods, unknown forwarding, capability escapes, nested capture and private
authoritative state access all forbidden.

Static structure and runtime measurement are separate and both required. The
static graph proves the certified source structure; runtime attestation proves
the effective bindings correspond to it. Neither substitutes for the other.
Cycles remain forbidden, every owner path must terminate at `put`, `get`,
`records` or `envelopes`, and the census is exactly eleven frozen, eleven
source-discovered and eleven runtime-attested owners.

## Frozen replay owners

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

## Current production

No compiled root write, clear or delete exists in any owner. The single compiled
root finding remains the `common_etf_session_status` generator-expression
capture of `evidence_store`, which the closed AST grammar refuses
at the same construct, so the rewrite that was already required stays required.

All eleven effective runtime owner bindings attest cleanly. The transitive
execution closure does not: the `CalendarEvidenceStore` admission and read
methods are `functools.wraps` guards installed at import, so their certified
method fingerprints and wrapper state both refuse. Runtime measurement therefore
rediscovers the wrapper-installer blocker independently of any static rule.

Of the five module-namespace reaches, exactly one — `_install_exact_dependency_guards` —
writes the namespace, and the key it writes is not a replay owner. It must still
be removed, because the certified direct-body architecture forbids
wrapper-installed authority guards; that requirement is independent of owner
attestation. The other four are read-only artifact-builder dispatch lookups that
cannot change any effective owner binding, and this decision does not require
them to be rewritten for owner identity. Their determinism remains governed by
their existing artifact tests.

Current full calendar conformance is **NO** and the calendar implementation
remains blocked.

## Preserved authority and safety

Failed proof-architecture lineage `0c237c1b217b1fd406ec3967309774293c01d3e27574b9f4a7d1b9a0e887b55d, a7d2b08741080494cc4ca0269bf21e28e631c7f2e70887bcb0e1beb302534dd0, dc36ffe228b7a3bc6d9145042b4e301c8624c99a79d71a88b46fc268f1372c3e, 9f6af1794e8b49dce38288b9f1b9710bffd04ba70303b5c380e8fb447ac86295, 7ef114fede9efebe594f0ecf119d097a1161119f448737d0df10afdf9468d17b, b5ca36bfa9b96970b667cc44b10c5c5da7eb5ce7c57e5739601640d9b2a8abe9` remains immutable, non-certified,
unused and at zero observations. Trusted persistence
`02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772` is closed, certified and unchanged, and is not
re-reviewed here. The trusted-process boundary, the five direct dependency-body
requirements, calendar science, failed calendar lineage, BTC-019 and Epic T are
unchanged, and no ETF calendar production code was modified.

No observation was collected and no real Stage-B evaluation ran. Calendar
implementation, `POSTP1-001V2R1`, `POSTP1-003R3`, `POSTP1-004` and collection
remain blocked. This candidate authorizes only `POSTP1-002V2A-PAD3_INDEPENDENT_EXACT_HASH_XHIGH_PROOF_ARCHITECTURE_REVIEW`.
