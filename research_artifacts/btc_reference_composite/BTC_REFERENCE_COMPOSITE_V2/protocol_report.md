# BTC_REFERENCE_COMPOSITE_V2 Frozen Validation Protocol

## State

- Status: `FROZEN_RESEARCH_PROTOCOL`
- Definition SHA-256: `bc312f3e6a6035e00a3cd80103aacdee7b5a02ae69732b7bbca5785a3dd6106a`
- Research only: `true`
- External validation performed: `false`
- Production promotion authorized: `false`
- BTC-019: `IN PROGRESS`

## Formula

`MEDIAN_OHLC_V2` independently takes the median available provider open, high,
low, and close. Composite volume is not defined.

## Quality Semantics

- Three providers with full close agreement: publish `REFERENCE_OK`.
- Three providers with full close agreement but material high, low, or range
  dispersion: publish `VENUE_DISAGREEMENT`.
- Three providers with two-provider close consensus: publish `REFERENCE_DEGRADED`.
- Three providers without close consensus: publish `VENUE_DISAGREEMENT` with
  `reference_price_available=true`.
- Two agreeing providers with prior ATR and range checks passing: publish
  `REFERENCE_DEGRADED`.
- Two providers failing agreement checks: `REFERENCE_UNAVAILABLE`.
- One or zero providers: `REFERENCE_UNAVAILABLE`.

Reference availability and strategy entry permission are separate contracts.
This protocol does not choose final entry/add behavior.

## Higher Timeframes

Daily and weekly records always persist expected, observed, missing, degraded,
venue-disagreement, and unavailable counts. Complete warned buckets publish
OHLC with warning state. Incomplete buckets persist null OHLC with
`bucket_complete=false`, `bucket_usable=false`, and `REFERENCE_UNAVAILABLE`.
Partial-bucket OHLC is not approved, and silent omission is prohibited.

## Validation

- Hard gates: 34
- Diagnostic gates: 5
- Primary ATR materiality threshold: `0.50 ATR`
- Full ATR grid: `0.10, 0.20, 0.30, 0.50, 1.00 ATR`
- Required comparison series: Bitstamp, Coinbase, Bitfinex, historical
  `MEDIAN_OHLC_V1`, and `BTC_REFERENCE_COMPOSITE_V2`.
- Production promotion additionally requires at least 90 days of live shadow.

## Sealed Sample

- Start: `2015-07-20T21:00:00+00:00`
- End: `2019-11-30T23:00:00+00:00`
- `BOUNDARY_VERIFIED`
- `BULK_COMPLETENESS_UNMEASURED`
- `OUTCOMES_UNINSPECTED`
- `DO_NOT_OPEN_UNTIL_V2_VALIDATION`

BTC-019C does not bulk collect, inspect, or validate this period. A future
dedicated validator bound to this definition hash is required to open it.

## Governance

V1, BTC-019B, and `PRICE_SOURCE_POLICY_V1` remain unchanged. Material V2
methodology changes require `BTC_REFERENCE_COMPOSITE_V3` or a later explicit
version. Normal Phase-1 development may resume after this freeze.
