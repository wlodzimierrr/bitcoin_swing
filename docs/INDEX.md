# Documentation Index

Start with [AGENTS.md](../AGENTS.md), this index, and
[CURRENT_STATE.md](CURRENT_STATE.md). Detailed authority remains in the
documents mapped below.

## Current / Authoritative

| Document | Purpose | Authority | When to read |
| --- | --- | --- | --- |
| [Structured Tickets v2.6](execution/bitcoin_swing_predictor_structured_tickets_v2_6.md) | Phase-1 ticket status, dependencies, execution order, acceptance criteria, and implementation/review notes | Authoritative Phase-1 execution roadmap | Read the exact ticket block; inspect dependency blocks and V2 order only as needed |
| [Rulebook v1.2](strategy/bitcoin_swing_predictor_rulebook_v1_2.md) | Strategy semantics and mathematics for v1.2 | Authoritative except scopes explicitly superseded by newer narrow versioned policies | Read only sections relevant to the ticket's formulas and invariants |
| [PRICE_SOURCE_POLICY_V1](policies/price_source_policy_v1.md) | Versioned empirical price-source evidence and conclusion | Authoritative for its explicitly defined V1 price-source-policy scope; newer than provisional Rulebook source language | Read for canonical/reference-source, provenance, fallback, or price-data work |
| [EPIC X — Prospective Integration Evidence](execution/post_phase1_prospective_integration_evidence_v1.md) | Post-Phase-1 prospective integration-evidence workstream status, dependencies, and acceptance criteria | Authoritative for EPIC X only; not Phase-1 execution authority and not BTC-019 authority | Read when implementing or reviewing a POSTP1-xxx ticket |

## Prospective Evidence Artifacts

| Namespace | Purpose | Provenance boundary |
| --- | --- | --- |
| [`prospective_evidence/prospective_integration_corpus_v1/`](../prospective_evidence/prospective_integration_corpus_v1/) | Hash-bound corrected `PROSPECTIVE_INTEGRATION_CORPUS_V1` protocol and child contracts | Immutable certified lineage; collection authority remains unchanged until V2 passes review; post-Phase-1 prospective evidence only; deliberately outside the immutable V5 historical JSON census |
| [`prospective_evidence/prospective_integration_corpus_v2/`](../prospective_evidence/prospective_integration_corpus_v2/) | Hash-bound `PROSPECTIVE_INTEGRATION_CORPUS_V2` replay-closure parent and child contracts | Frozen pre-data successor awaiting independent exact-hash xHigh review; authorizes no collection; deliberately outside the immutable V5 historical JSON census |
| [`prospective_evidence/etf_publication_calendar_authority_v1/`](../prospective_evidence/etf_publication_calendar_authority_v1/) | Hash-bound `ETF_PUBLICATION_CALENDAR_AUTHORITY_V1` definition and material child contracts | Frozen pre-data missing-authority completion that failed independent exact-hash xHigh review; not certified and authorizes no collection or V2 correction |
| [`prospective_evidence/etf_publication_calendar_authority_v1_r1/`](../prospective_evidence/etf_publication_calendar_authority_v1_r1/) | Failed corrected hash-bound `ETF_PUBLICATION_CALENDAR_AUTHORITY_V1` source-derived definition and material child contracts | Frozen pre-data failed lineage rejected for caller-asserted HTTP origin, incomplete annual traversal, and permissive URL/redirect identity; immutable, non-authoritative, and unused |
| [`prospective_evidence/etf_publication_calendar_authority_v1_r2/`](../prospective_evidence/etf_publication_calendar_authority_v1_r2/) | Final corrected hash-bound `ETF_PUBLICATION_CALENDAR_AUTHORITY_V1` trusted-origin and parser-completeness definition | Frozen pre-data failed lineage rejected because caller-manufactured self-hashed trusted acquisitions can enter the public scientific store; blocked pending an explicit trusted-persistence architecture/authority decision; authorizes no V2 correction or collection |
| [`prospective_evidence/etf_publication_calendar_authority_v1_i1/`](../prospective_evidence/etf_publication_calendar_authority_v1_i1/) | Failed integrated hash-bound `ETF_PUBLICATION_CALENDAR_AUTHORITY_V1` delegating origin to the certified trusted-persistence authority | Frozen pre-data candidate at `b499c6a4...e584e076` that failed independent exact-hash xHigh integration closure review because authoritative calendar admission does not execute the exact dependency assertion; not certified and authorizes no V2 correction or collection |
| [`prospective_evidence/etf_publication_calendar_authority_v1_i1_r1/`](../prospective_evidence/etf_publication_calendar_authority_v1_i1_r1/) | Failed call-site-closed hash-bound `ETF_PUBLICATION_CALENDAR_AUTHORITY_V1` successor retaining the exact certified trusted-persistence dependency | Frozen pre-data candidate at `901f572e...fd9853f` rejected because wrapper originals and runtime rebinding bypass the exact dependency assertion without effective-call-edge drift detection; immutable, non-authoritative, and authorizes no V2 correction or collection |
| [`prospective_evidence/etf_calendar_in_process_authority_boundary_v1/`](../prospective_evidence/etf_calendar_in_process_authority_boundary_v1/) | Failed hash-bound `ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1` architecture decision | Immutable failed pre-data boundary at `0c237c1b...887b55d`, rejected because the project-owned private-state bypass model and exact replay-owner census were incomplete; non-certified and unused |
| [`prospective_evidence/etf_calendar_in_process_authority_boundary_v1_r1/`](../prospective_evidence/etf_calendar_in_process_authority_boundary_v1_r1/) | Failed corrected hash-bound `ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1` project-owned bypass architecture | Immutable pre-data boundary at `a7d2b087...534dd0` that failed independent exact-hash xHigh architecture re-review because replay-route closure is existential rather than universal and annotated variadic store consumers evade the census; non-certified, unused, and authorizes no calendar implementation, V2 correction, or collection |
| [`prospective_evidence/etf_calendar_in_process_authority_boundary_v1_r2/`](../prospective_evidence/etf_calendar_in_process_authority_boundary_v1_r2/) | Failed universal-route corrected hash-bound `ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1` architecture | Immutable pre-data candidate at `dc36ffe2...f1372c3e` that failed independent exact-hash final xHigh architecture review because an ordinary bound-method alias can hide an undocumented store route behind another valid terminal edge; non-certified, unused, and blocked pending an explicit proof-architecture decision; authorizes no calendar implementation, V2 correction, or collection |
| [`prospective_evidence/etf_calendar_store_capability_normal_form_v1/`](../prospective_evidence/etf_calendar_store_capability_normal_form_v1/) | Failed hash-bound `ETF_CALENDAR_STORE_CAPABILITY_NORMAL_FORM_V1` closed proof architecture | Immutable pre-data candidate at `9f6af179...7ac86295` that failed independent exact-hash xHigh review because direct non-variadic starred forwarding is accepted, nested annotated store owners can be invisible, and flow-insensitive/rebindable store names can manufacture permitted uses and false graph terminals; non-certified, unused, and authorizes no calendar implementation, V2 correction, or collection |
| [`prospective_evidence/etf_calendar_store_capability_normal_form_v1_r1/`](../prospective_evidence/etf_calendar_store_capability_normal_form_v1_r1/) | Failed narrow corrected hash-bound `ETF_CALENDAR_STORE_CAPABILITY_NORMAL_FORM_V1` direct immutable-parameter proof architecture | Immutable pre-data candidate at `7ef114fe...8d17b` that failed independent exact-hash final xHigh review because the Python 3.12 binding census omits `TypeAlias` and enclosing-scope assignment expressions in nested function defaults/decorators, lambda defaults and class headers/decorators; non-certified, unused, and authorizes no calendar implementation, V2 correction, or collection |
| [`prospective_evidence/etf_calendar_compiled_binding_witness_v1/`](../prospective_evidence/etf_calendar_compiled_binding_witness_v1/) | Failed hash-bound `ETF_CALENDAR_COMPILED_BINDING_WITNESS_V1` proof architecture: the closed AST store-use grammar plus a frozen CPython 3.12.14 compiled root-binding witness | Immutable pre-data candidate at `b5ca36bf...b2a8abe9` that failed independent exact-hash xHigh proof-architecture review because ordinary module-dictionary and function `__setattr__` substitutions evade the claimed module-owner identity proof; the compiled root-binding layer is sound, but the owner-identity layer depends on an incomplete reflection/module-mutation blacklist; non-certified, unused, and authorizes no calendar implementation, V2 correction, or collection |
| [`prospective_evidence/etf_calendar_runtime_owner_attestation_v1/`](../prospective_evidence/etf_calendar_runtime_owner_attestation_v1/) | Hash-bound `ETF_CALENDAR_RUNTIME_OWNER_ATTESTATION_V1` proof architecture: the preserved compiled root-binding witness and closed AST store-use grammar plus measured pre/post runtime attestation of the eleven frozen replay owners and their mechanically derived transitive execution closure | Frozen pre-data candidate at `b8f8b92d...f6b5b996` awaiting POSTP1-002V2A-PAD3, its independent exact-hash xHigh proof-architecture review; the static reflection blacklist is explicitly demoted and is no longer completeness authority; not certified and authorizes no calendar implementation, V2 correction or collection |
| [`prospective_evidence/trusted_acquisition_persistence_authority_v1/`](../prospective_evidence/trusted_acquisition_persistence_authority_v1/) | Failed hash-bound `TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1` signature, key, replay, and PostgreSQL append boundary | Immutable failed pre-data lineage rejected for replaceable trust roots, pre-commit success, incomplete runtime binding, and missing role provisioning; non-authoritative and unused |
| [`prospective_evidence/trusted_acquisition_persistence_authority_v1_r1/`](../prospective_evidence/trusted_acquisition_persistence_authority_v1_r1/) | Corrected hash-bound `TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1` fixed trust-root, commit-confirmation, runtime-attestation, key-file and PostgreSQL bootstrap boundary | Frozen pre-data R1 candidate that failed repeat independent exact-hash xHigh review on runtime key-value attestation and connected-database identity enforcement; non-authoritative and authorizes no calendar integration/collection |
| [`prospective_evidence/trusted_acquisition_persistence_authority_v1_r2/`](../prospective_evidence/trusted_acquisition_persistence_authority_v1_r2/) | Final corrected hash-bound `TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1` runtime-material and connected-database-identity boundary | Frozen pre-data R2 candidate at `bd55a3c0...02c4fc` that failed final independent exact-hash xHigh review because the effective collector-role identity is not parent-bound runtime material; uncertified and authorizes no calendar integration/collection |
| [`prospective_evidence/trusted_acquisition_persistence_authority_v1_r3/`](../prospective_evidence/trusted_acquisition_persistence_authority_v1_r3/) | Final micro-corrected hash-bound `TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1` database-authority runtime-material boundary | Certified frozen pre-data authority at `02f96203...1a12772`; final independent exact-hash xHigh closure review passed and authorizes only bounded ETF-calendar integration/refreeze, not collection |

## Future Planning

| Document | Purpose | Authority | When to read |
| --- | --- | --- | --- |
| [Post-Phase-1 roadmap](roadmaps/bitcoin_swing_predictor_post_phase1_roadmap_v1.md) | Phase 1.5+ and post-Phase-1 planning | Future planning only; not current Phase-1 execution authority | Read when planning work beyond the current Phase-1 roadmap |

## Historical

| Document | Purpose | Authority | When to read |
| --- | --- | --- | --- |
| [Project Roadmap & Tickets v1](archive/bitcoin_swing_predictor_project_tickets_v1.md) | Original planning provenance | Historical only; never current dependency, status, execution, or strategy authority | Read only for explicit historical research |
| [Structured Tickets v1](archive/bitcoin_swing_predictor_project_tickets_structured_v1.md) | Original compact ticket provenance | Historical only; never current dependency, status, execution, or strategy authority | Read only for explicit historical research |

## Minimal Context for a Fresh Ticket Session

For normal ticket implementation or review, load only:

1. `/AGENTS.md`
2. `/docs/INDEX.md`
3. `/docs/CURRENT_STATE.md`
4. the exact `BTC-XXX` ticket block
5. direct dependency blocks when needed
6. relevant Rulebook sections
7. applicable narrow policy documents
8. related implementation and tests

Do not preload archived documents. Do not preload the full execution roadmap.
Do not preload the full Rulebook. Expand context only when evidence requires it.
