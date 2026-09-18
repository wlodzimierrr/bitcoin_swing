# ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1

- Ticket: `POSTP1-001V2A-AD1-R2`
- Decision hash: `dc36ffe228b7a3bc6d9145042b4e301c8624c99a79d71a88b46fc268f1372c3e`
- Status: `FROZEN_PRE_DATA_AWAITING_INDEPENDENT_XHIGH_ARCHITECTURE_REVIEW`
- Classification: `ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1_READY_FOR_FINAL_XHIGH_ARCHITECTURE_REVIEW`
- Material children: 10

## Universal replay-route proof

Every syntactic store-dependent edge is classified as a documented terminal,
an enumerated owner edge, or a forbidden undocumented method, unenumerated
forward, or private-state route. Forbidden edges refuse the audit. The owner
graph must be acyclic, every owner must have a store-dependent edge, and every
owner path must terminate at `put`, `get`, `records`, or `envelopes`. One valid
route never excuses another invalid route.

Annotated `*args: CalendarEvidenceStore` elements and
`**kwargs: CalendarEvidenceStore` values are store-bearing. Indexed references,
ordinary aliases, iteration targets, and resolvable starred forwarding share
the same mechanical model used by discovery and validation.

## Frozen replay-owner census

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

The discovered production set equals the eleven-owner registry. No production
calendar code changed.

## Preserved boundary and safety

The production Python process remains trusted. Arbitrary caller mutation stays
out of scope; repository-owned access to `_records` or `_envelopes` remains
forbidden. If hostile same-process mutation enters scope, process isolation is
required. The five direct-body dependency assertions, wrapper prohibitions,
and startup self-check remain required.

Failed architectures `0c237c1b217b1fd406ec3967309774293c01d3e27574b9f4a7d1b9a0e887b55d` and
`a7d2b08741080494cc4ca0269bf21e28e631c7f2e70887bcb0e1beb302534dd0` remain immutable, non-certified, unused, and
at zero observations. Trusted persistence `02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772` is
closed and unchanged. Source/parser, PIT/common-session, ETF, Stage-B, risk,
stop, and threshold semantics are unchanged.

No observation was collected and no Stage-B evaluation ran. Calendar
implementation, POSTP1-001V2R1, POSTP1-003R3, POSTP1-004, and collection remain
blocked. BTC-019 is untouched and Epic T is unchanged. This correction
authorizes only independent exact-hash xHigh final architecture review.
