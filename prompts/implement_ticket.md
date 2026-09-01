# Implement a Ticket

## Input

Ticket ID: `BTC-XXX`

The repository is the complete project memory.

Do not request or rely on previous chat history. Resolve all available context
from repository documentation and code before asking the user for information.

## Startup Sequence

1. Read `AGENTS.md` in full.
2. Read `docs/INDEX.md` in full.
3. Read `docs/CURRENT_STATE.md` in full.
4. Search for the exact `BTC-XXX` heading.
5. Read only that complete ticket block.
6. Read direct dependency ticket blocks as needed.
7. Read only relevant Rulebook sections.
8. Read applicable narrow policy documents.
9. Inspect the current implementation.
10. Inspect existing tests.
11. Verify prerequisites from repository evidence.

Do not dump the entire execution roadmap or Rulebook into context. Use targeted
search and bounded reads. Do not preload archived documents. Expand context
only when implementation evidence requires cross-cutting material.

**DO NOT IMPLEMENT FROM TICKET WORDING ALONE.**

## Workflow

```text
Verify dependencies
    -> establish exact contract
    -> inspect existing owners/parity implementations
    -> implement ticket scope only
    -> add/update deterministic tests
    -> run focused tests
    -> run relevant regressions
    -> run parity/invariant tests
    -> verify every acceptance criterion
    -> update ticket Implementation Notes
    -> update CURRENT_STATE only if project state changed
    -> commit appropriately if repository workflow calls for it
    -> final report
```

Respect the ticket's implementation and review model requirements. Preserve
public behavior, point-in-time semantics, provenance, and deterministic replay
unless the authoritative contract explicitly changes them.

## Prohibitions

- Do not invent strategy rules.
- Do not rely on previous chat history.
- Do not perform unrelated refactors.
- Do not duplicate formulas owned by authoritative modules.
- Do not weaken tests merely to make implementation pass.
- Do not silently resolve material strategy ambiguity.
- Do not mark `DONE` while acceptance criteria fail.
- Do not mark fully `DONE` if required independent review remains outstanding.
- Do not silently modify strategy/config semantics without versioning.
- Do not silently convert missing numerical values to zero.

## Final Report

Report Ticket, Status, Implementation commit, Files changed, Behavior
implemented, Tests added/changed, Commands/tests run, Results, Acceptance
criteria verification, Design decisions, Documentation updated, Remaining
risks/ambiguities, and Recommended next dependency-satisfied ticket.
