# ETF_CALENDAR_COMPILED_BINDING_WITNESS_V1 — compiled binding witness

- Ticket: `POSTP1-001V2A-PAD2`
- Decision hash: `b5ca36bfa9b96970b667cc44b10c5c5da7eb5ce7c57e5739601640d9b2a8abe9`
- Failed parent: `7ef114fede9efebe594f0ecf119d097a1161119f448737d0df10afdf9468d17b`
- Status: `FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_XHIGH_REVIEW`
- Classification: `ETF_CALENDAR_COMPILED_BINDING_WITNESS_V1_READY_FOR_XHIGH_REVIEW`
- Strategy: `CLOSED_AST_USE_GRAMMAR_PLUS_FROZEN_CPYTHON_BINDING_WITNESS`
- Material children: 11

## Why the binder census was replaced

`POSTP1-002V2A-PAD1-R1` failed with `PYTHON 3.12 BINDING CENSUS INCOMPLETE`.
Manually enumerating AST binding constructs is not a bounded completeness
strategy, so this decision stops claiming it. The source AST binding visitor is
retained only for diagnostics, early failure, reason codes and regression
localization; a missing AST diagnostic can never make an actual compiled root
write scientifically acceptable.

## Two independent layers

The source layer keeps the narrow `DIRECT_IMMUTABLE_STORE_PARAMETER_NORMAL_FORM`
grammar: the only scientific root is an ordinary positional-only,
positional-or-keyword or keyword-only parameter explicitly annotated
`CalendarEvidenceStore`, usable only as the receiver of a direct `put`, `get`,
`records` or `envelopes` call or as a non-starred argument to an exact frozen
replay owner. Aliases, annotated store variadics, starred forwarding, local
construction, container derivation and nested annotated owners remain forbidden.

The compiled layer proves root immutability against the exact top-level code
object of each owner under frozen `cpython`
`3.12.14`
(magic `cb0d0d0a`, cache tag `cpython-312`).
The reviewed source is compiled, never executed and never imported, with
`dont_inherit=True` and `optimize=0`; cached
bytecode is not scientific authority. A runtime or compiler identity mismatch
refuses scientific authority instead of silently certifying another compiler.

## What the witness proves

A conforming root is an ordinary, uncaptured fast local. Structurally, the root
may never be a cell variable of its owner, because a cell is a first-class
object that any capturing function exposes through `__closure__`, and writing
`cell_contents` would rebind the root without emitting a single root-binding
instruction. The rule removes the entire cell-escape class by construction
rather than by enumerating escape attributes.

It is at least as strict as the source layer's unconditional nested-capture
prohibition, and in a few families it is strictly stricter: a bare `nonlocal`
declaration naming the root, a PEP 695 lazy type-alias or type-parameter scope
that reads the root, and a statically dead nested scope that still cells the
root are all accepted by the source grammar and refused here. That over-refusal
is deliberate and fail closed; the decision never claims the two layers accept
exactly the same sources.

On top of it, no instruction in an owner's own code object may write, clear or
delete the root after frame-entry parameter establishment, and, as defence in
depth, no nested code object holding the root as a free variable of the owner's
cell may `STORE_DEREF` or `DELETE_DEREF` it. A class body keeps the root in its
free variables while binding its own same-named `co_names` entry through
`STORE_NAME`; that is a different namespace and is never an owner-root write.
An ordinary assignment inside a nested function body binds that nested scope's
own local and is likewise not an outer-root write.

The module-level owner name must still denote the reviewed definition. Owners
may not be decorated, each owner name is bound exactly once in the module code
object, and anywhere in the reviewed module's whole code-object tree a later
rebinding or deletion of an owner name, a write to a live function object's
`__code__`, `__defaults__`, `__closure__`, `__globals__` or `__dict__`, and any
reach into the module namespace as a mutable mapping through `globals`, `vars`,
`locals`, `setattr`, `delattr`, `exec`, `eval`, `compile` or `__import__` all
refuse. Those checks run over every nested code object, so a substitution hidden
one call frame deep is refused too.

The frozen write/delete/clear opcode policy is checked mechanically against the
exact interpreter's opcode table, including its reserved unnamed slots and its
specialization table; an unclassified, moved or newly emittable root-binding
opcode refuses and requires a new proof architecture. Instructions are read
deoptimized, so a specialized opcode cannot hide a root write.

The witness proves exactly that, and nothing more. It does not claim to prove
arbitrary Python semantics, and frame-local mutation, debugger mutation and
arbitrary reflective namespace manipulation remain outside the trusted-process
threat model; the reflective-name and attribute prohibitions inside replay
owners are a conservative production rule, not a completeness claim. The AST
normal form proves permitted uses and the replay graph proves route closure.

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

The production census is exactly eleven. Compiled binding, dynamic-execution and
AST use audits all precede graph extraction; cycles are forbidden and every
owner path must terminate at a documented API.

## Current production

All eleven owners are binding-proof compatible: there is no root write, clear or
delete anywhere, and no dynamic or reflective authority escape. The single
compiled-layer root finding is the `common_etf_session_status`
generator-expression capture of `evidence_store`, which exposes that root as a
closure cell; the closed AST grammar refuses the same construct. Both layers
therefore refuse one and the same known use.

Separately, current production reaches its own module namespace through
`globals()` in five scopes. One of them installs the wrapper guard that the
frozen direct-body dependency rule already forbids; the other four dispatch
artifact builders by name and must become an explicit registry. The calendar
implementation ticket removes all five, and the implementation therefore remains
blocked.

## Preserved authority and safety

Failed proof-architecture lineage `0c237c1b217b1fd406ec3967309774293c01d3e27574b9f4a7d1b9a0e887b55d, a7d2b08741080494cc4ca0269bf21e28e631c7f2e70887bcb0e1beb302534dd0, dc36ffe228b7a3bc6d9145042b4e301c8624c99a79d71a88b46fc268f1372c3e, 9f6af1794e8b49dce38288b9f1b9710bffd04ba70303b5c380e8fb447ac86295, 7ef114fede9efebe594f0ecf119d097a1161119f448737d0df10afdf9468d17b`
remains immutable, non-certified, unused and at zero observations. Trusted
persistence `02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772` is closed and unchanged. The
trusted-process boundary, direct dependency-body rule, startup identity checks,
calendar science, failed calendar lineage, BTC-019 and Epic T are unchanged.

No observation was collected and no real Stage-B evaluation ran. Calendar
implementation, POSTP1-001V2R1, POSTP1-003R3, POSTP1-004 and collection remain
blocked. This candidate authorizes only `POSTP1-002V2A-PAD2_INDEPENDENT_EXACT_HASH_XHIGH_PROOF_ARCHITECTURE_REVIEW`.
