# Review a Ticket Independently

## Input

Ticket ID: `BTC-XXX`

Implementation commit: optional; discover it from repository history if
omitted.

This is an independent correctness review. The repository is the complete
project memory.

Do not rely on the implementation chat's reasoning. Do not assume the
implementation is correct. Do not rewrite correct working code without
evidence.

## Startup Sequence

1. Read `AGENTS.md`.
2. Read `docs/INDEX.md`.
3. Read `docs/CURRENT_STATE.md`.
4. Locate the exact ticket block.
5. Read its acceptance criteria and direct dependencies.
6. Read relevant Rulebook sections only.
7. Read applicable narrow policies.
8. Inspect the implementation diff and current implementation.
9. Inspect tests.
10. Inspect upstream/downstream contracts actually used by the implementation.

Do not preload the full roadmap or Rulebook. Use targeted searches and bounded
reads. Do not preload archived documents. Expand context only when review
evidence requires it.

## Review Philosophy

Do not limit review to existing tests. Existing tests can encode the same
misunderstanding as the implementation. Derive high-risk invariants
independently from the ticket, Rulebook, applicable policies, upstream and
downstream contracts, persistence/replay requirements, and actual behavior.

Evaluate only relevant categories: mathematical assumptions, unit semantics,
point-in-time semantics, look-ahead leakage, same-bar/event ordering, edge
cases, NaN/infinity behavior, risk invariants, long/short symmetry, state
transitions, fill assumptions, portfolio accounting, batch/single parity,
configuration provenance, persistence/replay integrity, reproducibility,
tamper resistance, duplicate economic effects, test coverage, behavior outside
scope, and dependency drift.

Do not force irrelevant boilerplate findings.

## Findings and Result

Use severities:

```text
P0 Critical
P1 High
P2 Medium
P3 Low
NOT_A_DEFECT
```

Every real finding must include severity, file/location, current behavior,
expected behavior, why it matters, recommended correction, and the missing or
regression test.

The review result must be one of:

```text
PASS
PASS WITH NON-BLOCKING FINDINGS
FAIL — RELEASE BLOCKING
```

## Review-Fix Procedure

If no genuine defect exists, do not create a meaningless commit. If defects
exist:

1. Make the smallest correct fix.
2. Add independent regressions.
3. Run focused tests.
4. Run relevant regressions.
5. Run the full suite where appropriate.
6. Create a distinct review-fix commit.
7. Update ticket Implementation Notes.
8. Update `CURRENT_STATE.md` if state, baseline, or frontier changed.

After fixes and passing tests, the final result may become `PASS`. Do not perform
unrelated redesign.

## Final Report

Report exactly these items, briefly:

```text
Ticket
Reviewed implementation commit
Review result
Findings
Review-fix commit, if any
Focused tests
Full test result
Documentation updated
Remaining limitations
Can ticket remain DONE?
Recommended next dependency-satisfied ticket
```
