# ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1

- Ticket: `POSTP1-001V2A-AD1-R1`
- Decision hash: `a7d2b08741080494cc4ca0269bf21e28e631c7f2e70887bcb0e1beb302534dd0`
- Status: `FROZEN_PRE_DATA_AWAITING_INDEPENDENT_XHIGH_ARCHITECTURE_REVIEW`
- Classification: `ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1_READY_FOR_REPEAT_XHIGH_REVIEW`
- Material children: 9

## Threat boundary and project-owned bypasses

The production Python interpreter/process remains trusted. Arbitrary external
caller manipulation of private fields, class dictionaries, module globals,
debugger state, or equivalent interpreter internals is outside the scientific-
authority threat model. Repository-owned production/scientific code that reads
or writes authoritative store internals outside `CalendarEvidenceStore` is in
scope and forbidden. If hostile same-process mutation later enters scope, work
must stop for process isolation; no wrapper, metaclass, descriptor, frozen-
object, or source-hash workaround may substitute for that boundary.

The implementation-private authoritative fields are exactly `_records` and
`_envelopes`. Store methods may access their own state. Every other production
owner must use `put`, `get`, `records`, or `envelopes`. A future authoritative
state field requires registry review and a new child and parent hash.

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

The production module is mechanically parsed with Python AST. The discovered
owner set must equal this registry with no missing or stale names. The entire
production module, excluding `CalendarEvidenceStore` method bodies, is audited
for dotted, literal `getattr`/`setattr`, `__dict__`, and `vars` access to the
reserved internals. Each owner must reach a documented store surface directly
or through another compliant enumerated owner.

The five authoritative boundary bodies remain required to contain a direct
executable AST call to `assert_trusted_persistence_dependency`. Runtime guards,
`functools.wraps`, `__wrapped__`, unguarded production owners, and aliases remain
forbidden. Controlled startup checks the calendar parent, dependency child,
exact trusted-persistence dependency, and executable manifest, but never
replaces direct body checks.

## Preserved scope and safety

The failed architecture `0c237c1b217b1fd406ec3967309774293c01d3e27574b9f4a7d1b9a0e887b55d` remains non-certified,
failed, superseded before use, and at zero observations. The certified trusted-
persistence dependency `02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772` remains closed and
unchanged. Source/parser, PIT/common-session, ETF, Stage-B, risk, stop, and
threshold semantics are unchanged.

No observation was collected and no real Stage-B evaluation ran. The calendar
is not certified. Calendar implementation, POSTP1-001V2R1, POSTP1-003R3,
POSTP1-004, and collection remain blocked; BTC-019 is untouched and Epic T is
unchanged. This correction authorizes only independent exact-hash xHigh
architecture re-review.
