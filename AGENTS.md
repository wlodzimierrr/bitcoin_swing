# Repository Agent Contract

This repository is the complete project memory for implementation and review.
Fresh sessions must recover context from the repository, not from prior chats.

## Authority by Question

### Strategy Semantics / Mathematics

1. A newer narrow versioned policy controls only its explicitly defined scope.
2. [Rulebook v1.2](docs/strategy/bitcoin_swing_predictor_rulebook_v1_2.md)
3. Ticket Implementation Notes may clarify the implemented contract only when
   they do not contradict the authorities above.

A newer narrow versioned policy may supersede an older provisional Rulebook
statement only for that policy's explicitly defined scope.

### Phase-1 Ticket Execution

1. [Structured Tickets v2.6](docs/execution/bitcoin_swing_predictor_structured_tickets_v2_6.md)
   controls status, dependencies, acceptance criteria, execution order, and
   implementation/review requirements.
2. [CURRENT_STATE.md](docs/CURRENT_STATE.md) is only a compact handoff and must
   agree with the execution roadmap.

### Price-Source Policy

1. [PRICE_SOURCE_POLICY_V1](docs/policies/price_source_policy_v1.md) and later
   explicitly versioned source policies control their stated scopes.
2. Rulebook provisional source language is historical/provisional context.

### Future Development

[Post-Phase-1 roadmap](docs/roadmaps/bitcoin_swing_predictor_post_phase1_roadmap_v1.md)
controls Phase 1.5+ planning, not current Phase-1 execution.

### Historical Documents

Documents under `docs/archive/` are provenance only. Never use them to
determine current execution, dependencies, status, or strategy semantics.

## Mandatory Startup Procedure

Before implementing or reviewing a ticket:

1. Read `AGENTS.md`.
2. Read `docs/INDEX.md`.
3. Read `docs/CURRENT_STATE.md`.
4. Locate the exact ticket in the authoritative execution roadmap.
5. Read that complete ticket block.
6. Inspect direct dependencies.
7. Read only relevant Rulebook sections.
8. Read applicable narrow policy documents.
9. Inspect the existing implementation.
10. Inspect existing tests.
11. Verify prerequisites from repository evidence.

**DO NOT IMPLEMENT FROM TICKET WORDING ALONE.**

**DO NOT RELY ON PREVIOUS CHAT CONTEXT.**

## Context-Efficiency Rule

Fresh sessions must use targeted repository reads. Do not load the entire
Structured Tickets document merely to implement or review one ticket.

1. Search for the exact ticket identifier.
2. Read that complete ticket block.
3. Read direct dependency blocks only when needed.
4. Read V2 execution-order sections only when scheduling or dependency
   selection is relevant.

Do not load the entire Rulebook by default. Read only sections referenced by
the ticket, formulas/invariants used by the ticket, sections needed for a
discovered cross-cutting issue, and applicable narrow policy documents.

Do not read archived documents unless historical provenance is specifically
needed. Prefer search plus bounded line/range reads. Expand context only when
implementation or review evidence requires additional cross-cutting context.

## Conflict Rule

If documentation appears inconsistent:

1. Identify the type of question being answered.
2. Apply the authority-by-question hierarchy.
3. Prefer a newer, narrower, explicitly authoritative versioned policy within
   its stated scope.
4. Preserve historical documents rather than rewriting history.
5. Do not invent missing strategy semantics.
6. Do not silently resolve material strategy ambiguity.
7. Surface unresolved material ambiguity in the final ticket report.

## Implementation Rules

- Implement one substantial ticket per task; do not combine unrelated
  correctness-critical tickets.
- Preserve public behavior unless the ticket intentionally changes it.
- Engineering, vectorization, and refactoring must not alter strategy semantics
  without explicit strategy/config/policy versioning.
- Preserve point-in-time correctness and never silently convert missing
  numerical values to zero.
- Add deterministic tests for mathematical and lifecycle invariants.
- Inspect existing parity/reference implementations before replacing behavior.
- Use authoritative owner modules instead of duplicating formulas.
- Run focused tests, relevant regressions, and parity/invariant tests where
  applicable.
- Comply with ticket-specific implementation and review model requirements.
- Do not weaken existing tests merely to make new code pass.

## Definition of Done

A ticket is `DONE` only when:

- acceptance criteria are satisfied;
- focused and relevant regression tests pass;
- parity/invariant tests pass where applicable;
- required independent review passes and blocking findings are fixed;
- Implementation Notes are current;
- `CURRENT_STATE.md` is updated when project state changed; and
- no known correctness-critical ambiguity remains unresolved.

A required independent review is part of closure. Passing the first
implementation commit and tests does not finally close that ticket.

## State Updates

Work that materially changes project state must update the applicable
`CURRENT_STATE.md` fields: date, frontier, recent completion, in-progress or
blocked work, next ticket, test baseline, relevant commit, and unresolved
decisions. `CURRENT_STATE.md` must not become a duplicate ticket ledger.

## End-of-Ticket Report

Every implementation report must state: Ticket, Status, Implementation commit,
Files changed, Behavior implemented, Tests added/changed, Commands/tests run,
Results, Acceptance criteria verification, Design decisions, Documentation
updated, Remaining risks/ambiguities, and Recommended next
dependency-satisfied ticket.

Review agents must report a distinct review-fix commit when fixes are needed.
If no genuine defect exists, do not create a meaningless commit.
