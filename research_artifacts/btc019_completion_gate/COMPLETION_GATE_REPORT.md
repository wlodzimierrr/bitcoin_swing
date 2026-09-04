# BTC-019 Completion-Gate Assessment

Namespace: `research_artifacts/btc019_completion_gate/`

This is a **non-approval** record. It answers one question:

> does the repository's evidence support an approved production canonical BTC
> reference under an explicit versioned policy today?

It does not. BTC-019 remains **IN PROGRESS**, the production canonical
reference remains **UNRESOLVED**, and no frozen artifact, policy, threshold, or
gate was changed to reach that conclusion.

- Outcome: `BLOCKED_BY_UNRESOLVED_CORRECTNESS_DEFECT`
- Sealed `BTC_REFERENCE_COMPOSITE_V2` sample opened: **no**
- Machine-readable evidence: `completion_gate_assessment.json`
- Schema: `BTC019_COMPLETION_GATE_ASSESSMENT_V1`

Every number below recomputes from the two collected raw histories, whose
recorded SHA-256 digests are verified before the assessment reads them, through
the authoritative owners. No wall-clock input enters the record: each sample's
evaluation instant is its own latest ingestion time.

## Candidate status

| Candidate | Status | Where it is recorded |
| --- | --- | --- |
| Bitstamp `btcusd` as sole canonical reference | `REJECTED` | `btc019/PRICE_SOURCE_POLICY_V1/canonical_source_decision.json` |
| Coinbase `BTC-USD` as sole canonical reference | never affirmatively evaluated | — |
| Bitfinex `tBTCUSD` as sole canonical reference | never affirmatively evaluated | — |
| `BTC_REFERENCE_COMPOSITE_V1` (`MEDIAN_OHLC_V1`) | `RESEARCH_INCONCLUSIVE` | `btc_reference_composite/BTC_REFERENCE_COMPOSITE_V1/final_decision.json` |
| `BTC_REFERENCE_COMPOSITE_V2` (`MEDIAN_OHLC_V2`) | `FROZEN_RESEARCH_PROTOCOL`, unvalidated | `btc_reference_composite/BTC_REFERENCE_COMPOSITE_V2/protocol_definition.json` |

Rejecting Bitstamp promotes nothing. No affirmative evidence exists for any
other single venue, and the only composite that was evaluated missed two of its
own predeclared external gates.

## Why the sealed V2 sample stays sealed

The frozen V2 protocol permits opening `2015-07-20T21:00Z .. 2019-11-30T23:00Z`
only through "a future dedicated validator bound to this definition hash". Three
independent conditions fail:

1. **No validator exists.** Nothing in the repository binds an evaluation to
   `bc312f3e6a6035e00a3cd80103aacdee7b5a02ae69732b7bbca5785a3dd6106a`.
   `guard_untouched_validation_sample` still refuses every overlapping window.
2. **The sample is not collected.** `data/` holds 2019-12-01..2022-12-31 and
   2023-01-01..2025-12-31 only.
3. **An unresolved implementation defect would invalidate the evaluation.**
   This is the blocking one, and it is measured below.

The sample can be opened once. Opening it against a structural comparison that
cannot distinguish venue disagreement from provider availability would spend
the repository's only pristine out-of-sample period on an uninterpretable
result.

## The defect: adjacent rows are read as adjacent sessions

`build_canonical_market_bars` emits complete buckets only, so an hourly provider
outage removes that whole daily and weekly session. The resulting series is
legitimately non-contiguous. `btc_predictor.features.rolling` — the BTC-041
owner — handles this: a range whose preceding session is absent is `None`. Two
BTC-019 paths do not.

### 1. Weekly structural detection reads its window by row

`detect_weekly_swing_levels` takes `available_bars[index - 3 : index + 4]` and
`detect_breakout_reclaim_levels` builds on its output. Neither requires the
window to be seven consecutive calendar weeks. Removing one week from an
otherwise contiguous series therefore confirms a swing high that the complete
series does not contain, because the bar that disqualified the candidate is the
bar that is gone.

That mechanism is reachable on the repository's own data:

| Sample | Provider | Omitted daily sessions | Omitted weekly sessions |
| --- | --- | ---: | ---: |
| 2023-01-01..2025-12-31 | bitstamp | 0 | 0 |
| 2023-01-01..2025-12-31 | coinbase | 2 | 2 |
| 2023-01-01..2025-12-31 | bitfinex | 2 | 2 |
| 2019-12-01..2022-12-31 | bitstamp | 0 | 0 |
| 2019-12-01..2022-12-31 | coinbase | 3 | 3 |
| 2019-12-01..2022-12-31 | bitfinex | 5 | 5 |

Reproducing BTC-019's own structural comparison against the Bitstamp baseline
gives 24 differences on the study sample — 4 swing highs, 7 swing lows,
4 breakouts and 9 reclaims, matching the corrected frozen
`comparison_report.json` exactly — and 16 more on the external sample.
**24 of those 40 differences sit inside the detector's own ±3-week confirmation
reach of a week one of the two compared series does not have.**

Two are unambiguous: Bitstamp holds a swing low at `2023-03-06` and another at
`2024-04-29`, and those are precisely the weeks Bitfinex omits. A venue cannot
disagree about the structure of a week it has no bar for.

The 2023-02-13 swing high — the "Bitstamp alone created one swing and its
breakout" clause of the frozen rejection rationale, confirmed as a breakout on
2023-03-13 — is in the same class: Coinbase omits 2023-02-27 and Bitfinex omits
2023-03-06, both inside that candidate's confirmation window.

The same mechanism explains BTC-019B's failed exact-timestamp swing gate. Its
four disagreements are two adjacent-week pairs, `2020-03-09`/`2020-03-16` and
`2021-04-05`/`2021-04-12`, around the two weekly buckets the composite omitted
for unresolved venue disagreement.

**Certification impact.** Six `BTC_REFERENCE_COMPOSITE_V2` approval gates are
computed from this comparison — `exact_timestamp_swing_disagreement_rate`,
`within_1_week_…`, `within_2_week_…`, `structural_state_disagreement_rate`,
`breakout_disagreement_rate` and `reclaim_disagreement_rate`, four of them hard.
On 2015-2019 venue history, provider outages are at least as frequent as the
five weeks Bitfinex already loses in 2020-2022, so those gates would measure
availability as much as reference quality.

**Owner.** `btc_predictor/levels/swing.py` is EPIC E's, not BTC-019's, and its
output feeds structure scores, stops and setups. Making it session-aware is a
strategy-semantics change that needs its own version, so it is proven and
pinned here rather than changed.

### 2. Three BTC-019 research helpers restate true range

`price_source_policy._atr_fraction_series`, `price_source_policy._atr_value_series`
and `btc019_empirical._baseline_atr_before` each rebuild
`max(h - l, |h - c_prev|, |l - c_prev|)` over `zip(ordered, ordered[1:])`, and
`price_source_policy._daily_returns` takes `close / previous close` the same way.
The EPIC E/E2 audit recorded this; the footprint is now measured:

| Sample | Provider | `_daily_returns` bridged | `_atr_*_series` bridged (each) |
| --- | --- | ---: | ---: |
| 2023-01-01..2025-12-31 | coinbase | 2 | 28 |
| 2023-01-01..2025-12-31 | bitfinex | 2 | 28 |
| 2019-12-01..2022-12-31 | coinbase | 3 | 42 |
| 2019-12-01..2022-12-31 | bitfinex | 5 | 70 |

348 published observations across the two samples cross an absent session that
the BTC-041 owner reports as undefined. Two of them are visible as ordinary
one-day moves of 0.3333% and 3.1573% (Coinbase) and -0.9897% and -1.0987%
(Bitfinex) that actually span two days.

`_baseline_atr_before` is not in that table because it is only ever called on
the Bitstamp baseline, which omits no session in either sample, so it
contaminates nothing today. Handed a series that does have an outage it
publishes anyway, which is pinned by test rather than assumed.

**Parity where no session is absent.** On every window with no omitted session
the helpers agree with the BTC-041 owner's true range to the digit; Bitstamp,
which omits nothing, has zero bridged observations in either sample. The
duplication is therefore only reproducing history incorrectly where a provider
had an outage, not computing a different formula.

**Scope.** These helpers produce the frozen BTC-019 artifacts. Correcting them
in place would break byte reproduction of evidence this ticket is required to
preserve, so they are left as they are and pinned. Any future BTC-019 canonical
selection must read the BTC-041 owner or carry parity evidence before its
result can support an approval.

## What the defect does not overturn

The frozen `BITSTAMP = REJECTED` decision stands. Its rationale rests on four
pillars and only the first two are adjacency-exposed:

1. Bitstamp alone created one swing and its breakout — Tier 3, exposed.
2. Both validators created a swing/reclaim sequence Bitstamp did not — Tier 3, exposed.
3. Both validators touched a `107270` stop Bitstamp missed on 10 October 2025 —
   Tier 4, a price-level comparison on synchronized hourly bars, **not exposed**.
4. Maximum MFE/MAE sensitivities of 2.433 and 4.605 percentage points —
   Tier 4 hourly path probes, **not exposed**.

Pillar 3 is independently corroborated outside this research path: BTC-224's
golden scenario places its 10 October 2025 stop at 107,623.70, between Coinbase's
pinned 107,000 low and Bitstamp's 109,683. Tier 1 price divergence, the
cross-venue wick diagnostics and the 82 manual reviews all normalize by ATR
taken from the Bitstamp baseline, which omits no session, so they are unaffected
too.

Rejecting a single venue therefore remains sound. Approving one — or approving a
composite — does not, because approval is exactly the direction that depends on
the structural evidence.

## Point-in-time and historical availability

The V2 provenance schema already separates `observation_time`, `decision_time`
and `available_at`, includes a provider only when
`provider.available_at <= composite decision_time`, and refuses a late provider
rather than waiting. That contract is sound but unexercised, because no approved
canonical path exists.

BTC-019 owns none of the Phase-1 historical-availability finding. Both
`derive_ohlcv_bars` and `build_canonical_market_bars` stamp one `ingested_at`
across a whole backfill, so a dataset built the repository's own way carries no
meaningful per-bar live availability. That boundary belongs to BTC-020 and
BTC-180. An approved canonical reference would have to supply per-bar
availability, but there is no canonical path here to supply it from, so nothing
in BTC-019 can be credited against that finding.

## Smallest legitimate next research step

Not "collect 2015-2019". In order:

1. **Make weekly structural comparison session-aware, under its own version.**
   Either give `detect_weekly_swing_levels` an explicit calendar-contiguity
   contract, or have the price-source comparator restrict every cross-provider
   structural comparison to weeks all compared series actually hold. The second
   is narrower and changes no production strategy semantics.
2. **Re-measure structural disagreement on the already-inspected 2019-2022 and
   2023-2025 samples** with that comparison, to establish how much of the 24
   adjacent differences was availability. This needs no new data and cannot
   contaminate the sealed sample.
3. **Only then** decide whether V2's structural gates are measurable, build the
   validator bound to the frozen definition hash, collect 2015-2019, and open
   the sample once.

Steps 1 and 2 must complete before step 3. Tuning anything after the sealed
outcomes are visible would void the protocol.

## Certification status

Phase-1 champion certification remains blocked. The V2 quant-refactor completion
gate's first line — "BTC-019 production canonical reference is explicitly
approved and versioned" — is unmet, and this assessment does not weaken, move or
reinterpret any gate in order to change that.

## Preservation

Unchanged by this assessment, and verified by test:

- `PRICE_SOURCE_POLICY_V1` document and artifacts, and `BITSTAMP = REJECTED`;
- `BTC_REFERENCE_COMPOSITE_V1` at `RESEARCH_INCONCLUSIVE`;
- BTC-019B at `MIXED`;
- the V2 protocol definition, recomputing to `bc312f3e…6106a`;
- both collected raw histories, matching their manifest digests;
- every threshold, gate, comparison definition and degraded-reference limit.
