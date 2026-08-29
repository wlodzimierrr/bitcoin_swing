# BTC_REFERENCE_COMPOSITE_V1 Final Research Report

Decision: **RESEARCH_INCONCLUSIVE**

The study does not approve a canonical reference and does not alter
`PRICE_SOURCE_POLICY_V1`. `MEDIAN_OHLC_V1` passed 9 of 11 frozen gates but
missed the external degraded-frequency and swing-stability gates.

## 1. Files Changed

- Core methods: `btc_predictor/research/reference_composite.py`
- Empirical runner: `btc_predictor/research/reference_composite_empirical.py`
- Derived table: `btc_predictor/db/derived.py`
- Migration: `btc_predictor/db/migrations/versions/0019_create_btc_reference_composite.py`
- Tests: `test_reference_composite.py`, `test_reference_composite_empirical.py`, and migration tests
- Policy documentation: `README.md` and `docs/price_source_policy_v1.md`
- Evidence: this artifact directory

## 2. Candidate Methodologies

- Candidate A, `MEDIAN_OHLC_V1`: independent median of each OHLC field.
- Candidate B, `CONFIRMED_EXTREMES_V1`: median open/close plus two-venue-confirmed highs/lows.
- Candidate C, `CLIPPED_CENTER_V1`: median-centered, ATR-clipped residual mean for each field.

Candidate A was selected as the primary frozen candidate after development
research. Candidate B materially inflated ATR and Candidate C introduced
synthetic center movement without improving structural stability.

## 3. Exact Formulas

For provider field values `x_i` and prior completed 14-day daily ATR `A`:

- A: `x_ref = median(x_1, x_2, x_3)` for open, high, low, and close.
- B open/close: median. High uses the maximum only when the two highest highs
  differ by at most `0.15A`; otherwise it uses the median high. Low uses the
  minimum only when the two lowest lows differ by at most `0.15A`; otherwise it
  uses the median low.
- C: `x_ref = median(x) + mean(clip(x_i - median(x), -0.15A, +0.15A))`.

All aggregate candles are checked for positive values and valid OHLC ordering.

## 4. Missing-Provider Rules

- 3/3: `REFERENCE_OK` when all closes agree; `REFERENCE_DEGRADED` with
  `TWO_PROVIDER_CONSENSUS` when one close is outside the cluster.
- 2/3: degraded and usable only when closes are within 50 bps and high/low
  dispersion is no more than 0.30 prior ATR.
- 1/3 or 0/3: `REFERENCE_UNAVAILABLE`; no OHLC is published.
- No historical fallback or source splicing is allowed.

## 5. Disagreement Rules

Diagnostics persist close dispersion in bps and high, low, and range dispersion
in prior ATR units. Three-venue close dispersion above 50 bps is degraded when
any independent pair remains within 50 bps; without such a pair it becomes
`VENUE_DISAGREEMENT`. This preserved the genuine 17 August 2023 and March 2020
selloffs while exposing single-venue discontinuities.

## 6. Point-in-Time Rules

The decision time is fixed at bar close plus five minutes. Only inputs with
`input.available_at <= decision_time` are included. `available_at` on the
composite is the fixed decision time. ATR uses only the previous
completed UTC daily bar. Historical public API archives do not preserve actual
publication latency, so final candles are conservatively assumed available at
bar close; that limitation is explicit rather than reconstructed after the fact.

## 7. Development Period

The inspected development sample was `2023-01-01 00:00 UTC` through
`2025-12-31 23:00 UTC`: 26,304 expected hours and 26,292 three-venue common
hours. It was used for method design and debugging, never described as
out-of-sample evidence.

## 8. External Period

Definitions and gates were frozen under SHA-256
`dc5dd567165cc56aeda906ee147e8209a8cdc1105071d558e8529ed52d90f65f`
before collecting external data. December 2019 was ATR warmup only. The untouched
evaluation period was `2020-01-01 00:00 UTC` through `2022-12-31 23:00 UTC`,
covering 26,304 hours. No parameters were retuned after inspection.

The original frozen artifact is retained unchanged. A post-run metadata audit
corrected derived `available_at` from latest-input time to the fixed composite
decision time. Both reports were rerun and all research metrics were byte-for-byte
identical after excluding insertion counters; the correction is recorded in
`point_in_time_metadata_correction.json` and is not model retuning.

## 9-12. Six-Series External Results

Rates and differences are fractions; MFE/MAE and ATR columns are p95 absolute
differences from two-of-three venue consensus.

| Series | Coverage | Degraded | Swing disagree | Breakout | Reclaim | Stop disagree | MFE p95 | MAE p95 | ATR p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Bitstamp | 1.000000 | 0 | 0 | 0 | 0 | 0 | 0.001218 | 0.002287 | 0.039656 |
| Coinbase | 0.999886 | 0 | 0.062500 | 0.200000 | 0.250000 | 0.013072 | 0.002127 | 0.002329 | 0.017638 |
| Bitfinex | 0.999544 | 0 | 0.093750 | 0.200000 | 0.250000 | 0 | 0.004240 | 0.014026 | 0.042302 |
| Median OHLC | 0.999886 | 0.010873 | 0.121212 | 0.111111 | 0.250000 | 0 | 0 | 0 | 0.019464 |
| Confirmed extremes | 0.999886 | 0.010873 | 0.228571 | 0.111111 | 0.250000 | 0.013072 | 0.003016 | 0.005581 | 0.064985 |
| Clipped center | 0.999886 | 0.010873 | 0.176471 | 0.111111 | 0.250000 | 0 | 0.001362 | 0.002381 | 0.020138 |

Bitstamp's zero external structural disagreement does not reverse BTC-019: the
previously inspected 2023-2025 period contains the decisive consensus stop miss
and isolated structural fragility. The two samples answer different questions.

## 13. Known BTC-019 Events

`MEDIAN_OHLC_V1` rejected the isolated Bitstamp high on 24 March 2023, retained
the confirmed 17 August 2023 selloff, rejected the isolated Bitfinex low on
5 December 2024, rejected the isolated Bitstamp low on 2 April 2025, and retained
the 10 October 2025 selloff. Event-centered MFE matched venue consensus in all
five cases. Event-centered MAE matched in four; the October case differed by
0.000108245 fraction while retaining the correct stop state.

## 14. Stop-Touch Sensitivity

Median OHLC had zero stop disagreements over 149 development probes and 153
external probes. On 10 October 2025 its low was 107,000, so it touched the
reviewed 107,270 stop; Bitstamp's 109,683 low did not. Confirmed extremes had two
external stop disagreements at the frozen 0.15 ATR setting.

## 15. Swing / Breakout / Reclaim Sensitivity

Median OHLC development disagreement rates were 3.23% for combined swings,
12.50% for breakouts, and 14.29% for reclaims. External rates were 12.12%,
11.11%, and 25.00%. The external combined-swing result exceeded the frozen
10% gate, with four timestamp disagreements across the event union.

## 16. MFE / MAE Sensitivity

Median OHLC external p95 MFE and MAE differences were both zero; maxima were
0.0003465 and 0.0027797. Development p95 MFE was zero and p95 MAE was
0.0001084. Candidate B was worse on both measures, while Candidate C remained
close but did not improve structural stability.

## 17. Degraded-Reference Frequency

Development had 84 degraded bars (0.3193%) and no missing median-reference bars.
External validation had 286 degraded bars (1.0873%), three disagreement bars,
and 26,301 usable bars (99.9886%). Coverage passed the 99.5% gate, but degraded
frequency exceeded the frozen 0.5% gate.

## 18. Parameter Robustness

The predeclared grid was 0.05, 0.10, 0.15, 0.20, and 0.30 prior ATR. All ten
Candidate B/C variants passed all five development known-event checks. External
Candidate C was stable across the grid at 17.65% swing disagreement and zero
stop disagreement. Candidate B ranged from 12.12% to 22.86% swing disagreement
and from zero to 1.307% stop disagreement, showing materially weaker robustness.

## 19. Manual Reviews

The five required BTC-019 divergence events and the 20 largest external
ATR-normalized range disagreements were reviewed. External reviews identified
isolated Bitstamp, Coinbase, and Bitfinex wicks, Bitfinex discontinuity/catch-up
bars, mixed-range disagreements, and the genuine March 2020 crash. Median OHLC
rejected isolated extremes while preserving the crash. Structured conclusions
are in `external_manual_review_assessments.json`.

## 20. Decision

**RESEARCH_INCONCLUSIVE.** Passed gates: external duration, coverage, ATR median,
ATR p95, stop sensitivity, all known isolated events, both known cross-market
moves, the October stop, and tolerance-grid known-event behavior. Failed gates:
external degraded frequency and combined-swing disagreement. Frozen thresholds
were not relaxed after seeing these results.

## 21. BTC-019 Impact

BTC-019 remains **IN PROGRESS**. Bitstamp remains appropriate as immutable
primary raw OHLCV, but remains rejected as the sole canonical structural
reference. No other venue is automatically promoted.

## 22. Policy Versioning

`PRICE_SOURCE_POLICY_V1` is unchanged and no production canonical reference is
set. Because V1's historical meaning is already persisted, any future approved
composite requires a separately reviewed `PRICE_SOURCE_POLICY_V2`; V1 must not
be mutated in place.

## 23. Tests and Database Verification

- Focused composite/migration suite: 38 passed.
- Full repository suite: 544 passed.
- PostgreSQL revision: `0019_reference_composite`.
- Runtime and research connection verification: passed.
- Rendered downgrade contains `DROP TABLE derived.btc_reference_composite`.
- PostgreSQL contains 157,824 development/external derived observations with
  immutable conflict-do-nothing semantics and full raw-observation IDs.

## 24. Remaining Limitations

- Historical APIs do not expose original provider publication latency.
- Consensus is a research majority rule, not objective trade-level ground truth.
- Only three USD spot venues were studied; no institutional benchmark was added.
- Manual reviews used hourly OHLC, not order-book or trade-level replay.
- The external degraded and swing gates failed; live shadow behavior is untested.
- The test environment used Python 3.11 while project metadata requires 3.12+.
