# US_EQUITY_MARKET_CLOSURE_TABLE_V1

Frozen by `POSTP1-001V2A-T1`, authorized by the PAD5 owner scoping decision
`DECIDE_ETF_CALENDAR_SCOPE_AFTER_PAD5_V1`.

**Status:** `FROZEN_AWAITING_INDEPENDENT_EXACT_HASH_XHIGH_TICKET_REVIEW`
**Required review:** `POSTP1-002V2A-T1` — an independent exact-hash xHigh
**ticket** review. This is not a proof-architecture review.

## What this is

A static, hash-bound table of every full-day closure of the three US equity
venues that list the US spot bitcoin ETF universe. It owns the
`market_holidays` input of the Phase-1 ETF flow owner, which is the single
`POSTP1-002V2` blocking finding every retired ETF-calendar candidate was trying
to close.

Its authority is the exact-hash review of the table itself, exactly as for any
other frozen constant in this repository. There is no runtime acquisition, no
worker, no verifier and no origin authority. The citations and the stored source
bytes are audit aids: they let a reviewer re-hash the retrieved documents
offline and re-derive every row.

## Hashes

| Item | SHA-256 |
| --- | --- |
| Definition (canonical JSON digest) | `2292388e4a91c1617275ac20ed9d6b45e4b9678525c020e1ccc6fc36a01d1710` |
| `us_equity_market_closure_table_v1_definition.json` (file bytes) | `0692e778a8a20e87cfa9b7c40b0d1af37b201e870d448d683ee467b7124456fe` |
| `closure_table.json` (file bytes) | `4a7a5a25d19ead02619e83af6dd99574372450a08d1daac17973947911ee241d` |
| `source_index.json` (file bytes) | `f939b1d70da2f0543e19c73dcba96471c39735a369c159d4ead1041d7b38ebd3` |

`definition_sha256` is the canonical-JSON digest of its own document with the
field excluded. The `*_file_sha256` values the definition binds, and the loader's
frozen constants, are SHA-256 over the checked-in file bytes.

## Coverage

`2023-01-01` through `2026-12-31`, all three venues sourced for every year.

The start is a full year before the first US spot bitcoin ETF flows on
2024-01-11, so every trailing flow window that can contain a flow record lies
inside coverage.

The ticket target was 2028 and coverage stops at 2026. The acceptance criterion
is "the last year for which all listing venues have officially published a
holiday schedule at freeze time", and at freeze time (2026-09-29) only NYSE had
published beyond 2026:

- **NYSE** publishes 2026, 2027 and 2028 on its live hours-and-calendars page.
- **Nasdaq** publishes 2026. Its trading-calendar page links per-year calendars
  for 2021-2026 only, and the `nasdaqtrader.com` per-year calendar URL has no
  2027 document.
- **Cboe** publishes 2026. Its US equities holiday CSV serves the current year
  only and ignores a `year` query parameter.

2027 and 2028 are therefore outside coverage and the loader refuses them rather
than implying that any date in them was open.

## Rows

41 rows, every one a Monday-to-Friday date.

| Year | Total | Scheduled holiday | Unscheduled closure |
| --- | --- | --- | --- |
| 2023 | 10 | 10 | 0 |
| 2024 | 10 | 10 | 0 |
| 2025 | 11 | 10 | 1 |
| 2026 | 10 | 10 | 0 |

The single unscheduled closure is `2025-01-09`, the National Day of Mourning for
former President Jimmy Carter. Each venue confirms it from its own publication:
Cboe carries it on its 2025 equities holiday schedule, Nasdaq published Equity
Trader Alert #2024-86, and the NYSE closure notice names NYSE Arca Equities
explicitly.

**Venue disagreements: none.** All three venues agree on all 41 dates. An
independent rule-based holiday computation reproduces all 40 scheduled holidays,
as a cross-check that never replaces the sources.

## Early closes

Out of scope, and the rationale is frozen in the definition. Trading occurs on
an early-close day, the venues publish early closes separately from full-day
closures, and ETF flow records exist for them. Treating one as a closure would
remove a real publication date from the trailing window and change feature
values.

## Amendment rule

An unlisted closure fails closed through the flow owner. The owner counts the
unlisted date as a publication date, finds no flow record, and returns
`ETF_FLOW_INPUT_MISSING`. That is never a zero and never a fabricated value.

Corrections are new frozen versions (`US_EQUITY_MARKET_CLOSURE_TABLE_V2`, and so
on), reviewed by exact hash before any consumer relies on the amended date.
Evidence produced under V1 keeps V1 semantics. This table is never edited in
place.

## Loader

`btc_predictor/research/us_equity_market_closures.py` exposes
`load_closures(start, end) -> frozenset[date]`. On every call it re-reads and
re-verifies the definition and table bytes against their frozen hashes, checks
that the definition still binds the table and source-index hashes, validates
every row, then returns the closures inside the requested range.

It refuses, with `ClosureTableError`:

- a range not wholly inside coverage — an uncovered date is never implied open;
- a range containing a `VENUE_DISAGREEMENT` date;
- a range whose declared disagreement summary does not match its rows;
- an inverted range, or a `start`/`end` that is not exactly a `datetime.date`;
- any byte-level change to the definition or the table.

It imports only `__future__`, `collections.abc`, `datetime`, `hashlib`, `json`,
`pathlib` and `typing`. It imports nothing from the closed ETF-calendar
proof-architecture lineage.

## Consumers

Consumers pass the loaded set to the existing `market_holidays` parameter of
`btc_predictor.features.flow.etf_flow_window`. Wiring a consumer belongs to that
consumer's ticket; this ticket changed no consumer.

- **EPIC X:** `POSTP1-001V2R1` freezes a new corpus hash with this table as the
  `market_holidays` owner. Blocked until `POSTP1-002V2A-T1` passes.
- **EPIC Y:** `RESEARCH_BACKTEST_POLICY_V2` section 5 requires this table, loaded
  and hash-verified by its owner module. RBT-006 only after that review passes.

## Standing

Pre-data. Zero observations. Authorizes only `POSTP1-002V2A-T1`. It authorizes
no collection, no `POSTP1-001V2R1` freeze and no RBT-006 freeze. BTC-019 remains
untouched and its sealed sample unopened.
