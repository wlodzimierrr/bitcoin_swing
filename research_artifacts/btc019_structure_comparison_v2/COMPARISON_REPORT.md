# CROSS_PROVIDER_STRUCTURE_COMPARISON_V2

Namespace: `research_artifacts/btc019_structure_comparison_v2/`

This is a **research measurement**, not an approval. It answers one question:

> when two provider series disagree about a weekly swing, breakout or reclaim,
> is that a disagreement about BTC market structure, or only the fact that one
> provider did not publish the observation the detector needs to decide it?

It approves no provider or composite, opens no sealed sample, changes no frozen
threshold, gate, protocol or artifact, and changes no production strategy
semantics. BTC-019 remains **IN PROGRESS** and the production canonical
reference remains **UNRESOLVED**.

- Comparison contract: `CROSS_PROVIDER_STRUCTURE_COMPARISON_V2`
- Prior contract, still reproducing its own evidence: `CROSS_PROVIDER_STRUCTURE_COMPARISON_V1`
- Source detector: `BTC_PREDICTOR_WEEKLY_LEVELS_V1` (production `detect_weekly_swing_levels` / `detect_breakout_reclaim_levels`, unchanged)
- Machine-readable evidence: `comparison_report.json`
- Schema: `CROSS_PROVIDER_STRUCTURE_COMPARISON_V2_REPORT_V1`
- Sealed `BTC_REFERENCE_COMPOSITE_V2` sample opened: **no**
- Outcome: `RESEARCH_INCONCLUSIVE`

Every number recomputes from the two collected raw histories, whose recorded
SHA-256 digests are verified before the comparison reads them. No wall-clock
input enters the record: each sample's evaluation instant is its own latest
ingestion time.

## The contract

`build_canonical_market_bars` emits complete buckets only, so an hourly outage
removes a whole weekly session and the surviving series is legitimately
non-contiguous. `detect_weekly_swing_levels` takes its confirmation window by
row — `available_bars[index - 3 : index + 4]` — so on such a series the weeks
either side of an absent one are read as neighbours. The V1 comparison counted
the resulting difference as venue disagreement.

The V2 contract rests on one fact about that detector:

> when every calendar week of a candidate's confirmation window `T-3 .. T+3` is
> present in a series, those weeks occupy seven consecutive rows, so the row
> window and the calendar window are the same window and the detector's verdict
> at `T` is the calendar-correct verdict. When any of them is absent the row
> window spans a different calendar and the verdict is not a verdict about `T`.

Only the first case is comparable. The detector is not modified; a versioned
research adapter decides, per candidate, whether its output may be compared.

### Session identity

A weekly session is a canonical UTC Monday 00:00 bucket start. A series that is
not one identified provider's strictly increasing sequence of such sessions has
no calendar reading and is refused: a repeated week, an out-of-order week, an
off-cadence timestamp, a naive or non-UTC timestamp, a mixed provider identity,
a bar with no provider, a non-`1w` timeframe, an unknown detector version, a
policy-version mismatch and a tampered artifact digest all fail closed.

### Required calendar

| Candidate | Required weekly sessions |
| --- | --- |
| swing high / swing low at week `T` | `T-3 .. T+3`, the detector's own reach |
| breakout / reclaim from a swing at `T` | every week after `T` through the later of the two confirmations — or through the end of the shared calendar when either series never confirms, because "never" is a claim about every remaining week |

A session is `PRESENT`, `ABSENT` (an outage inside the series' own coverage),
`PENDING` (not yet closed or not yet ingested at the evaluation instant) or
`OUT_OF_COVERAGE` (before the series starts or after it ends). Only sessions the
series can speak for at the evaluation instant count as present, so appending
later history cannot change a comparison already made.

### Classification

| Comparability | Outcome | When |
| --- | --- | --- |
| `COMPARABLE` | `STRUCTURAL_AGREEMENT` | both detect, or neither does |
| `COMPARABLE` | `STRUCTURAL_DISAGREEMENT` | exactly one detects, or the two confirm in different weeks |
| `NOT_COMPARABLE_AVAILABILITY_GAP` | `NOT_COMPARABLE` | a required week is absent; the record names the series, or `both` |
| `NOT_COMPARABLE_CONFIRMATION_PENDING` | `NOT_COMPARABLE` | a required week had not arrived at the evaluation instant |
| `NOT_COMPARABLE_SERIES_COVERAGE` | `NOT_COMPARABLE` | a required week lies outside the collected span |
| `NOT_COMPARABLE_SOURCE_LEVEL` | `NOT_COMPARABLE` | the derived event's source swing is itself not comparable, or the two series do not share it |

### Pairwise, on a common calendar

Comparison is **pairwise on the weekly calendar the two compared series have in
common**. Each pair is canonicalised by sorted series id, so `compare(A, B)` and
`compare(B, A)` produce the identical record. No multi-provider consensus quorum
is computed: a quorum needs its own declared calendar basis before it can mean
anything, and the research question here is whether a two-series difference is
real.

### Denominators

Every rate names its denominator. `comparable_detected_event_union` counts the
candidates at least one series detected **and** both series could evaluate;
`all_detected_event_union` is the V1 denominator, kept beside it so the prior
measurement stays visible. Nothing is dropped silently: comparable and
not-comparable candidate counts always sum to the candidate universe, and
comparable and not-comparable event counts always sum to the raw detected
events.

## The V1 comparison still reproduces

The old contract is not retired, corrected or re-run under new rules. Executed
exactly as it stands, it reproduces the corrected frozen
`comparison_report.json` for the 2023-2025 sample — 4 swing highs, 7 swing lows,
4 breakouts, 9 reclaims — and both samples reproduce the counts recorded in
`BTC019_COMPLETION_GATE_ASSESSMENT_V1`: 24 and 16, 40 in total.

## What the 40 prior differences turn out to be

| Sample | Prior differences | Not comparable | Genuine disagreement |
| --- | ---: | ---: | ---: |
| 2023-01-01..2025-12-31 | 24 | 16 | 8 |
| 2019-12-01..2022-12-31 | 16 | 10 | 6 |
| **Total** | **40** | **26** | **14** |

None became an agreement. **26 of the 40 previously reported structural
disagreements are not evidence of disagreement at all.** Their reasons:

| Reason | Count |
| --- | ---: |
| `REQUIRED_SESSION_ABSENT_IN_ONE_SERIES` — a compared series has no bar for a week the detector needs | 13 |
| `SOURCE_LEVEL_NOT_COMPARABLE` — a derived breakout/reclaim whose source swing is itself blocked by an absent week | 10 |
| `SOURCE_LEVEL_NOT_SHARED` — a derived breakout/reclaim the two series do not both hold a source swing for | 3 |

The first twenty-three are availability. The last three are the downstream
shadow of a genuine upstream swing disagreement that is itself counted, and are
excluded because the pair has no shared source level to compare confirmations
on — not because a week is missing.

Omitted weekly sessions, recomputed:

| Sample | bitstamp | coinbase | bitfinex |
| --- | ---: | ---: | ---: |
| 2023-01-01..2025-12-31 | 0 | 2 | 2 |
| 2019-12-01..2022-12-31 | 0 | 3 | 5 |

### The named cases

- **`2023-03-06` and `2024-04-29`.** Bitstamp holds a swing low on each; those
  are the exact two weeks Bitfinex omits. Both are now
  `NOT_COMPARABLE_AVAILABILITY_GAP` with `availability_gap_side = bitfinex`.
- **`2023-02-13` and its `2023-03-13` breakout.** The "Bitstamp alone created
  one swing and its breakout" clause of the frozen rejection rationale. Coinbase
  omits `2023-02-27` and Bitfinex omits `2023-03-06`, both inside the swing's
  own confirmation window, so the swing is not comparable against either
  validator and the breakout inherits `SOURCE_LEVEL_NOT_COMPARABLE`.
- **BTC-019B's `2020-03-09`/`2020-03-16` and `2021-04-05`/`2021-04-12`.** The
  frozen BTC-019B record names the two weekly buckets the composite omitted for
  unresolved venue disagreement — `2020-03-09` and `2021-04-12` — and each of
  the four exact-timestamp disagreements has one of them inside its own `±3`
  confirmation window. All four are `NOT_COMPARABLE` under this contract; none
  survives as a disagreement.

### The contract is a filter, not an eraser

It moves events in both directions relative to the completion gate's coarse
`±3`-week adjacency heuristic. The `2025-09-01` reclaim, which Bitstamp confirms
on `2025-10-13` and Coinbase on `2025-10-06`, was flagged adjacent because
Coinbase omits `2025-10-20`; that week is not in the required confirmation
calendar `2025-09-08 .. 2025-10-13`, so it stands as a **genuine disagreement**.
Conversely four differences the heuristic called source-only — the `2023-06-12`
reclaim, the `2024-06-03` breakout, the `2023-08-14` reclaim and the
`2025-10-06` reclaim — are not comparable once the full confirmation calendar is
required.

### What survives

Of the 40 prior differences against the Bitstamp baseline, 14 remain genuine:
1 swing high, 5 swing lows, 8 reclaims and **no breakouts at all**. Counting
candidate sessions rather than V1 symmetric-difference elements, and across all
six pairwise comparisons rather than only the two baseline-anchored ones, the
genuine disagreements are 2 swing highs, 5 swing lows, 0 breakouts and 5
reclaims. Every one of them sits on a candidate where both compared series hold
the whole required calendar.

## Frozen V2 gate measurability

Six `BTC_REFERENCE_COMPOSITE_V2` approval gates are computed from cross-provider
weekly structural comparison; four of them, plus `breakout` and `reclaim`, are
hard. Their thresholds are read from the frozen protocol definition and are not
written, moved or reinterpreted here. Measuring them on raw provider pairs is a
**measurability probe**, not an approval evaluation of any candidate reference.

| Gate | Hard | Threshold | Defined on a comparable denominator | Verdict stable across denominators |
| --- | --- | --- | --- | --- |
| `exact_timestamp_swing_disagreement_rate` | no | 0.15 | 6/6 | 3/6 |
| `within_1_week_swing_disagreement_rate` | yes | 0.05 | 6/6 | 3/6 |
| `within_2_week_swing_disagreement_rate` | yes | 0.02 | 6/6 | 4/6 |
| `structural_state_disagreement_rate` | yes | 0.05 | 6/6 | 2/6 |
| `breakout_disagreement_rate` | yes | 0.05 | 6/6 | 0/6 |
| `reclaim_disagreement_rate` | yes | 0.05 | 6/6 | 5/6 |

**No affected gate is undefined**, and none is availability-dominated: across
the six pairwise comparisons 230 structural events are comparable against 83
that are not. The metrics are now measurements of venue disagreement rather than
of provider availability.

**But the frozen thresholds cannot be carried over unchanged in meaning.** The
frozen numbers were calibrated against BTC-019B's all-detected-event
denominator. Under this contract the denominator excludes events no series could
evaluate, and on 5 of the 6 gates — including 4 hard ones — the verdict against
the very same frozen number changes when the denominator changes. The most
extreme is `breakout_disagreement_rate`: every one of the six measurements fails
on the prior denominator and passes on the comparable one, because all 14
breakout disagreement candidates across both samples turn out to be
availability and none survives.

## Outcome

`RESEARCH_INCONCLUSIVE`, read off the rule predeclared in
`btc_predictor/research/cross_provider_structure_comparison.py` before the
samples were measured:

> `BLOCKED_BY_NEW_CORRECTNESS_DEFECT` when a collected artifact digest fails,
> the contract refuses its own inputs, or the V1 structural counts no longer
> reproduce; `NOT_READY_STRUCTURAL_GATES_STILL_INVALID` when any affected hard
> gate metric has no comparable denominator on a measured pair, or when
> not-comparable events outnumber comparable events in a pair's structural event
> universe; `RESEARCH_INCONCLUSIVE` when every affected hard gate is defined but
> a frozen threshold's verdict changes between the comparable and all-event
> denominators, so the frozen number cannot be applied to the revised
> denominator without changing its meaning; `READY_TO_BUILD_SEALED_VALIDATOR`
> otherwise.

The comparison defect is closed: availability gaps can no longer become
structural disagreements. What is not settled is which denominator the frozen
V2 structural gates are defined over. That was never written down, the two
readings disagree, and choosing one is a governance decision about a frozen
protocol — not something this measurement may decide, and certainly not
something to settle by adjusting a threshold.

## Smallest legitimate next step

1. **Declare the denominator, under its own version, bound to the frozen V2
   definition hash `bc312f3e…6106a`.** State whether each affected structural
   gate is evaluated over `comparable_detected_event_union` or
   `all_detected_event_union`, and how a not-comparable event is treated. No
   threshold moves; only the previously unstated denominator becomes explicit.
2. **Only then** build the hash-bound validator on top of this comparison
   contract, collect 2015-2019, and open the sealed sample once.

Step 1 must complete before step 2. The sealed sample can be opened once, and
opening it against gates whose denominator is undeclared would spend it on a
result no one can interpret.

## Preservation

Unchanged by this measurement, and verified by test:

- `PRICE_SOURCE_POLICY_V1` and `BITSTAMP = REJECTED`;
- `BTC_REFERENCE_COMPOSITE_V1` at `RESEARCH_INCONCLUSIVE`;
- BTC-019B at `MIXED`;
- the V2 protocol definition, its status, every gate, threshold and direction;
- `BTC019_COMPLETION_GATE_ASSESSMENT_V1`;
- `detect_weekly_swing_levels` and `detect_breakout_reclaim_levels`;
- both collected raw histories, matching their manifest digests;
- the sealed `2015-07-20 .. 2019-11-30` validation window, unopened and
  uncollected.
