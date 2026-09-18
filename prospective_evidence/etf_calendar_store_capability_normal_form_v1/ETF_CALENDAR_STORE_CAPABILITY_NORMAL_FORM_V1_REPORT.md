# ETF_CALENDAR_STORE_CAPABILITY_NORMAL_FORM_V1

- Ticket: `POSTP1-001V2A-PAD1`
- Decision hash: `9f6af1794e8b49dce38288b9f1b9710bffd04ba70303b5c380e8fb447ac86295`
- Status: `FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_XHIGH_REVIEW`
- Classification: `ETF_CALENDAR_STORE_CAPABILITY_NORMAL_FORM_V1_READY_FOR_XHIGH_REVIEW`
- Material children: 9

## Closed proof architecture

Scientific authority is proven by restricting repository-owned production code
to a closed, mechanically auditable store-capability grammar. Every recognized
store-bearing use must be a direct documented API call, direct enumerated-owner
forward, transparent local alias, or frozen variadic derivation. Every other
use is refused. Completeness does not mean understanding every Python program.

Bare extraction of documented or undocumented bound methods is forbidden.
Return/yield, arbitrary container packing, object/subscript storage, unknown
forwarding, nested capture, and dynamic access are forbidden. A future syntax
outside this normal form fails until an explicit reviewed authority change.
This architecture decision does not certify current production conformance;
the later implementation must rewrite the existing generator-expression store
capture in `common_etf_session_status` without changing calendar semantics.

## Proof order and replay graph

The capability normal-form audit runs before owner reconciliation or graph
extraction. The accepted graph retains these eleven frozen owners:

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

Only direct documented store terminals and direct enumerated-owner edges enter
the graph. Cycles are forbidden and every owner path must terminate at `put`,
`get`, `records`, or `envelopes`.

## Preserved boundary and safety

The production Python process remains trusted; hostile same-process arbitrary
mutation remains out of scope, and process isolation remains required if that
threat enters scope. Project-owned scientific bypasses remain forbidden. The
failed architecture parent `dc36ffe228b7a3bc6d9145042b4e301c8624c99a79d71a88b46fc268f1372c3e` and its two
predecessors remain failed, non-certified, unused, and at zero observations.
Trusted persistence `02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772` remains closed and
unchanged. Calendar science and failed calendar lineage are unchanged.

No observation was collected and no Stage-B evaluation ran. Calendar
implementation, POSTP1-001V2R1, POSTP1-003R3, POSTP1-004, and collection remain
blocked. BTC-019 is untouched and Epic T is unchanged. This decision authorizes
only POSTP1-002V2A-PAD1 independent exact-hash xHigh proof-architecture review.
