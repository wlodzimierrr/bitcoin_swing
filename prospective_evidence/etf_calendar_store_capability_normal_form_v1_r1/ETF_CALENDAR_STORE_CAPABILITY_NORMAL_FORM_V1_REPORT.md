# ETF_CALENDAR_STORE_CAPABILITY_NORMAL_FORM_V1 — corrected candidate

- Ticket: `POSTP1-001V2A-PAD1-R1`
- Decision hash: `7ef114fede9efebe594f0ecf119d097a1161119f448737d0df10afdf9468d17b`
- Failed parent: `9f6af1794e8b49dce38288b9f1b9710bffd04ba70303b5c380e8fb447ac86295`
- Status: `FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_XHIGH_REVIEW`
- Classification: `ETF_CALENDAR_STORE_CAPABILITY_NORMAL_FORM_V1_READY_FOR_FINAL_XHIGH_REVIEW`
- Material children: 10

## Direct immutable parameter normal form

The only scientific store root is an ordinary function parameter explicitly
annotated `CalendarEvidenceStore`. It has one binding: its parameter binding.
Aliases, annotated store variadics, local construction, nested annotated owners,
rebindings, deletion, and starred forwarding are forbidden. No naming heuristic,
reaching-definition analysis, SSA construction, generic capability propagation,
or arbitrary Python dataflow proof is used.

An immutable root may only receive a direct `put`, `get`, `records`, or
`envelopes` call, or be passed as an ordinary positional or named keyword
argument to one of the exact frozen replay owners. Every other root occurrence
and every later same-scope binding event fails closed.

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

The production census is exactly eleven. Binding and use audits precede graph
extraction; cycles are forbidden and every owner path must terminate at a
documented API. Current production is not certified: the known
`common_etf_session_status` generator-expression capture remains refused and is
reserved for the later calendar implementation ticket after review PASS.

## Preserved authority and safety

Failed parent `9f6af1794e8b49dce38288b9f1b9710bffd04ba70303b5c380e8fb447ac86295` remains immutable, non-certified, unused,
and at zero observations. Trusted persistence `02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772` is
closed and unchanged. The trusted-process boundary, direct dependency-body rule,
startup identity checks, calendar science, failed calendar lineage, BTC-019 and
Epic T are unchanged.

No observation was collected and no real Stage-B evaluation ran. Calendar
implementation, POSTP1-001V2R1, POSTP1-003R3, POSTP1-004 and collection remain
blocked. This candidate authorizes only `POSTP1-002V2A-PAD1-R1_INDEPENDENT_EXACT_HASH_XHIGH_PROOF_ARCHITECTURE_REVIEW`.
