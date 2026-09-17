# ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1

- Ticket: `POSTP1-001V2A-AD1`
- Decision hash: `0c237c1b217b1fd406ec3967309774293c01d3e27574b9f4a7d1b9a0e887b55d`
- Status: `FROZEN_PRE_DATA_AWAITING_INDEPENDENT_XHIGH_ARCHITECTURE_REVIEW`
- Classification: `ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1_READY_FOR_XHIGH_REVIEW`
- Material children: 7

## Decision

The production Python interpreter and process are part of the trusted computing
boundary. This is a scientific-correctness boundary, not a hostile-interpreter
isolation boundary. Arbitrary code execution, monkeypatching, module or class
mutation, private-state manipulation, debugger changes, and replacement of the
assertion inside that trusted process are outside this authority's threat model.

Every documented project-owned authoritative entrypoint must contain the exact
trusted-persistence dependency assertion directly in its reviewed body. The
repository may expose no wrapper original, raw/core owner, production alias,
alternate constructor, test helper, or caller-selected capability that bypasses
that assertion. Runtime decorator installation and `functools.wraps` authority
guards are forbidden. Store reads must assert at replay time, and production
collection must assert before HTTPS, private-key loading, signing, or persistence.

Controlled-startup implementation identity remains required to detect ordinary
repository/runtime drift. A startup self-check supplements, but never replaces,
the direct entrypoint checks. If a higher authority later requires resistance to
arbitrary mutation inside the trusted process, wrapper-level work must stop and
a separate process/service isolation architecture is required.

## Preserved scope and safety

Persisted calendar-parent, dependency-child, expected dependency hash/version,
and certified dependency mismatches still refuse. The certified dependency
`02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772` remains closed and unchanged. Source, parser,
PIT, common-session, ETF, Stage-B, risk, stop, and threshold semantics are
unchanged. All five failed calendar hashes remain non-authoritative,
non-certified, unused, and superseded before use.

No observation was collected and no real Stage-B evaluation ran. The calendar
is not certified. POSTP1-001V2R1, POSTP1-003R3, POSTP1-004, and collection stay
blocked; BTC-019 is untouched and Epic T is unchanged. This decision authorizes
only its independent xHigh architecture review.
