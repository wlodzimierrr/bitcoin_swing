# Champion Completion Spec V1

Policy identifier: `CHAMPION_COMPLETION_SPEC_V1`

Status: **FROZEN PRE-REGISTRATION DEFINITION (RBT-002A), awaiting the
independent xHigh review.** A narrow, versioned strategy policy for **EPIC Y
only**, made under
[`RESEARCH_BACKTEST_POLICY_V6`](research_backtest_policy_v6.md) section 6A.

| Item | Value |
| --- | --- |
| Research strategy identifier | `swing_v1.2+completion_v1` = `swing_v1.2` / `strategy_config_v2` / `default_phase1` plus this spec |
| Scope | EPIC Y research backtests only. Not `swing_v1.2` for advisory, paper, EPIC X or BTC-019 use; adopting it anywhere else needs that workstream's own decision (policy V6 section 6) |
| Machine-readable definition | `btc_predictor/research_backtest/completion_spec.py` (typed) → canonical sorted JSON `backtest_evidence/research_backtest_v1/champion_completion_spec_v1.json` |
| Definition SHA-256 | `d9f9b334abfba52b5f5af6a2eefe60616cec170568dbd7c5b310403cef7a80fd` (`champion_completion_spec_v1.json.sha256`) |
| Bound inventory | `rbt002_input_coverage_inventory_v1.json`, `108ab25b2240a76befc0f685cc684175e5207561d978bad099869fb0cc5efe3a` (reviewed under V5; kept by V6) |
| Evidence class | `RESEARCH_BACKTEST_NON_CERTIFYING`, canonical reference `UNRESOLVED` |

This document explains the definition. **The machine-readable definition is
authoritative**; where this summary is shorter, the JSON governs. Every rule,
citation and rationale is in the JSON, entry by entry.

## 1. What the spec is

The reviewed RBT-002 inventory marks 26 inputs of the champion's decision path
owner-less: 25 `OWNERLESS_UNDEFINED` inputs and `LEVEL_VOLUME_PERCENTILE`,
whose Rulebook 9.2 fallback row policy V6 section 6A.8 supersedes for this
champion. Without definitions, Trend, Flow, Volatility and Structure could never
be complete, so every decision would be structurally unevaluable. The spec
defines each of the 26 exactly once:

- **22 DEFINED**, **2 OMITTED** by written ruling (`MEASURED_MOVE_REFERENCE`,
  `CAPITULATION_EVENT`), **2 INERT** short-side inputs (`SHORT_TRIGGER`,
  `DISTRIBUTION_STATE`).
- `LIQUIDATION_PERCENTILE` is owner-less but certified (EPIC X, by reference);
  it is excluded and not redefined.

It adds **no executable formula** beyond the arithmetic it declares (section 7
below). The RBT-004/RBT-005 composers implement it by calling owner helpers.
It computes no score, signal, trade or outcome.

## 2. Uniform rules (section 6A.3)

**`UNIFORM_ZSCORE_V1`**, for every undefined z-score (the four trend and three
flow z-scores):

- current value x: the owner's value of the quantity at its latest observation
  D visible at the decision instant t (the owners' latest-available convention);
- history H: the owner's values at the prior observations D' of the quantity's
  **native series** (daily bar, weekly bar or US publication day) with
  `D - 730 days <= D' < D`; incomplete values are skipped, never filled;
- minimum 30 prior observations; population standard deviation (ddof 0);
  the current observation is never in H;
- an exactly constant H refuses (zero variance), so the refusal never depends
  on float or Decimal rounding;
- computed by the BTC-041 `features.rolling.rolling_zscore`.

**`UNIFORM_PERCENTILE_V1`**, for every undefined percentile (range and level
volume): the midrank `(less + 0.5 * equal) / n * 100` of a quantity observed once
per UTC day against its prior observations in `[D - 730 days, D)`, at least 365
of them, current excluded, computed by the BTC-041 `rolling_percentile`. This is
`volatility_percentile`'s convention unchanged.

No exceptions: the Rulebook distinguishes no input's normalisation.

**Why 730 days for z-scores (a `NEW_PARAMETER`).** The policy-named positioning
convention is 180 days with 30 observations. On native series that convention
cannot be met by the two weekly trend quantities: `[D - 180 days, D)` holds at
most 25 prior weekly observations. With it, `TREND_Z_20W` and `TREND_Z_52H`
would never be complete and the evaluation window would be empty on every
venue. The spec keeps the positioning minimum (30), population SD, prior-window
exclusion and zero-variance refusal. It takes the window from the Rulebook's
only other normalisation window (section 8.1, `Percentile(RV_20, 2yr)`, the
volatility owner's 730 days). This starts later than lowering the minimum,
which also governs the binding flow warm-up, so it trades less (section 6A.5).

Two other conventions were considered and rejected (recorded in the JSON as
`rejected_alternatives`):

- The flow owner's 20-observation count window (minimum 20). It is the window
  of the participation/CVD z-scores and EPIC X's certified CVD window. A
  20-row window over overlapping 5/20-day sums or 28/84-day returns measures
  recent change rather than "trailing historical data" (Rulebook 5.1). It
  spans 20 days or 20 weeks depending on cadence. It would also start the flow
  z-scores earlier (2024-03-10 instead of 2024-03-24), which trades more.
- Sampling each quantity at every daily decision instant. It would weight each
  weekly value about seven times and each weekend-straddling ETF day three
  times, and would trade more.

## 3. The 26 entries

| Input | Disposition | Governing class | Rule (summary) |
| --- | --- | --- | --- |
| `TREND_Z_M4`, `TREND_Z_M12`, `TREND_Z_20W`, `TREND_Z_52H` | DEFINED | NEW_PARAMETER (via the z window) | `UNIFORM_ZSCORE_V1` over the owner's `MOMENTUM_4W`, `MOMENTUM_12W`, `MA_DISTANCE_20W`, `HIGH_DISTANCE_52W` series |
| `FLOW_Z_ETF_NORM_5D`, `FLOW_Z_ETF_NORM_20D`, `FLOW_Z_FLOW_ACCEL` | DEFINED | NEW_PARAMETER (via the z window) | `UNIFORM_ZSCORE_V1` over ETFNorm_5, ETFNorm_20, FlowAccel per US publication day; history values with `end_date=D'`, the per-window fund universe and the closure table; one anchor date D |
| `RANGE_PERCENTILE` | DEFINED | NEW_PARAMETER | `UNIFORM_PERCENTILE_V1` of `TR(d) / close(d - 1 day)` (BTC-041 true range over the prior close); one value to Orderliness, CAPITULATION and EUPHORIA |
| `DOWNSIDE_RETURN` | DEFINED | NEW_PARAMETER | `R_7 = P_t / P_(t-7) - 1` (signed) via `price_momentum_from_daily_bars(lookback_periods=7)`; one value to Orderliness, STRESS, CAPITULATION |
| `UPSIDE_RETURN` | DEFINED | NEW_PARAMETER | the same `R_7` to EUPHORIA |
| `LEVEL_REACTION_MAGNITUDE` | DEFINED | NEW_PARAMETER | min over the cluster's swing members of the net move from the pivot to the close of the swing owner's last confirming bar, as a fraction of price (the owner's unit) |
| `LEVEL_VOLUME_PERCENTILE` | DEFINED | NEW_PARAMETER | min over the cluster's swing members of `UNIFORM_PERCENTILE_V1` of the member's pivot-bar Bitstamp volume against the same-length trailing Bitstamp volume observed at each prior UTC day (section 4) |
| `CAPITULATION_EVENT` | OMITTED | POLICY_RULING | no event anchor is built (AVWAP optional, Rulebook 9.2/9.4; no owner yields an event) |
| `SEVERE_CROWDING_STATE` | DEFINED | CONFIG | `CROWDING.flagged if CROWDING.complete else None` (policy V6 section 6A.5; trim owner's convention) |
| `MOMENTUM_PERSISTENCE_SCORE` | DEFINED | NEW_PARAMETER | `100 * Phi(TREND_Z_M12)` (overlap with Trend disclosed, section 6) |
| `ADD_MOMENTUM_SCORE` | DEFINED | NEW_PARAMETER | `100 * Phi(TREND_Z_M4)` (Add holds no Trend) |
| `NEW_STRUCTURE_SCORE` | DEFINED | NEW_PARAMETER | the Structure owner's score at the add's reference price under the raised trailing stop |
| `NEW_STRUCTURAL_CONFIRMATION` | DEFINED | NEW_PARAMETER | the trailing owner advanced on a HIGHER_LOW formed after the last accepted ENTER/ADD (RBT-005's producer, shared with the trail; the structure's own bar timestamp; BTC-122 mapping pinned) |
| `REGIME_SUPPORTIVE_PREDICATE` | DEFINED | CONFIG | smoothed regime classification BULL or STRONG_BULL (≥ 65) |
| `FLOW_SUPPORTIVE_PREDICATE` | DEFINED | RULEBOOK | FlowScore ≥ 60 (Rulebook 6.2 'Supportive'), not the owner's label |
| `REGIME_INVALIDATION_PREDICATE` | DEFINED | NEW_PARAMETER | smoothed classification Mild Bear or below (< 45), and the entry classification was not |
| `DATA_RISK_EXIT_PREDICATE` | DEFINED | OWNER_CONVENTION | False (Rulebook 24: DATA_QUALITY_FAIL blocks new trades and adds only) |
| `CORRECTION_FROM_LOCAL_HIGH` | DEFINED | NEW_PARAMETER | `-HIGH_DISTANCE_52W` (local high read as the trailing 52-week high) |
| `DISTRIBUTION_STATE`, `SHORT_TRIGGER` | INERT | POLICY_RULING | `None` (long-only, section 6A.6; the engine refuses shorts) |
| `MEASURED_MOVE_REFERENCE` | OMITTED | POLICY_RULING | `measured_move=None`; omitting tier 4 provably trades less |

The governing class is the lowest-precedence section 6A.2 tier any element of
the entry needs. Each element carries its own class and exact citation in the
JSON. There are **17 `NEW_PARAMETER` elements**, each with its one-line
rationale in the JSON `new_parameters` list.

## 4. Level volume (section 6A.8)

- **Source.** Bitstamp raw `1h` volume, in all three venue runs: RBT-001's
  shared `SHARED_RAW_VOLUME_1H` snapshot (`build_shared_replay_snapshot`), each
  hour used only once it is available (`modelled_bar_available_at <= t`).
- **Quantity**, defined once from level-record fields:
  - in scope are the cluster's `WEEKLY_SWING_LEVEL` / `MONTHLY_SWING_LEVEL`
    members;
  - member m's span is its pivot bar
    `[level_timestamp, next_bar_timestamp(level_timestamp, timeframe))`, of
    length L;
  - `Q_L(d)` is the Bitstamp volume summed over `[d - L, d)`, defined only when
    every hour is present.
- **Normalisation.** `p(m)` is `UNIFORM_PERCENTILE_V1` of `Q_L(e)` at the pivot
  close e, against `Q_L` at each prior UTC day in `[e - 730 days, e)`. The cluster
  value is the minimum over in-scope members. It is `None` when there is no swing
  member or when any member is `None` (strict).
- **What it does not do.** No price-level detection and no volume-profile
  binning. Weights stay at 0.20 each.
- **Point in time.** Every hour used ends before the member's detection.
- **Computed warm-up** (all venues):
  - a weekly pivot qualifies from the bar closing **2021-01-11** (369
    comparators); its earliest detection is **2021-02-01**;
  - a monthly pivot qualifies from January 2021; its earliest detection is
    **2021-04-01**;
  - earlier pivots never get a percentile. A cluster holding one stays
    incomplete, a declared cause. This is data-dependent, so it is reported as a
    lower bound.

## 5. Futures-basis zero variance (E1, section 6A.9)

**The limitation.** The frozen `futures_basis_health` owner returns a complete
score for an exactly constant non-terminating history. It does so because of
Decimal rounding in its `_average`.

**The contract RBT-004 must implement**, as guard
`FUTURES_BASIS_ZERO_VARIANCE_GUARD_V1`:

1. Take the owner result R at t.
2. If R has no z-score, R stands.
3. Otherwise apply the owner's own two-field visibility predicate to the rows.
   Rebuild the history H with the owner helpers `_futures_basis_averages_by_time`
   and `_futures_basis_history`, both promoted to census roots. Cross-check H
   against `R.history_observation_count` and `R.observation_time`.
4. If every element of H is exactly equal under Decimal `==` (whether or not the
   current value equals it), refuse with `FUTURES_BASIS_ZERO_VARIANCE`. Pass no
   health score or z-score to any of positioning, CROWDING, STRESS or EUPHORIA.
   Record positioning as `STRUCTURALLY_UNEVALUABLE`.
5. Otherwise pass R through unchanged.

**Required tests:**
- a constant history;
- a current value equal to it;
- a current value different from it;
- point-in-time exclusion of later rows;
- unchanged results on non-constant histories.

**Prohibited:** restating the z-score, any placeholder or tolerance, and an
owner edit.

## 6. Named limitations and items surfaced for review

**Limitations.** The JSON `named_limitations` lists all 13 in full:
- E1 itself;
- the same Decimal z-score class in `funding_health` and
  `open_interest_growth_health`, which section 6A.9 does not cover;
- the momentum-persistence overlap;
- the reaction unit (a price fraction, against the Rulebook's ATR);
- the frozen level-strength tables;
- the flow-owner label bands;
- row-based owner lookbacks;
- severe crowding collapsing ordinary CROWDING into the veto;
- pre-warm-up pivots;
- the STRESS mapping when a non-discretionary input is missing;
- add and reduce rules that no owner consumes;
- level families RBT-004 may cluster (volume-profile or AVWAP-only support
  clusters leave both level inputs `None`);
- one add instant per confirmed structure.

Row-based lookbacks carry a reporting obligation: RBT-006/RBT-007 report, per
venue, how many decision instants have such a lookback spanning an omitted bar.

**Surfaced, not silently resolved (AGENTS.md):**
1. **`MOMENTUM_PERSISTENCE_SCORE` overlaps Trend.** Z_M12 reaches Hold inside
   Trend (Hold weight 0.2666667 on `100 * Phi(... + 0.30 Z_M12 + ...)`) and
   directly (Hold weight 0.1333333). Rulebook 4.1/32.17 allow this only when
   the overlap is explicit, quantified, versioned *and validated*. This spec
   supplies the first three. No overlap-free owner output exists; a distinct
   persistence measure would be a new indicator. The owner decides whether to
   accept it.
2. **The E1 class in funding and OI-growth z-scores.** Should the section 6A.9
   guard extend to them?
3. **The `REGIME_INVALIDATION_PREDICATE` band.** Section 6A.5 is not monotone
   for exits.
4. **`CORRECTION_FROM_LOCAL_HIGH`** reads 'local high' as the trailing 52-week
   high, at weekly resolution.
5. **The z-score window of 730 days** (section 2), with the rejected
   alternatives.
6. **The return horizon of 7 daily bars.** Section 6A.5 is not monotone across
   consumers: a longer horizon fires Orderliness, STRESS and EUPHORIA more
   (fewer trades and adds) but also CAPITULATION, which enables Setup C.
7. **The range quantity** (true range over the prior close rather than raw true
   range). Neither is owner-fixed, and section 6A.5 is not monotone.
8. **Level families.** If RBT-004 clusters volume-profile or AVWAP members, a
   support cluster without a swing member leaves Structure incomplete.
9. **`NEW_STRUCTURAL_CONFIRMATION`** depends on RBT-005's trailing-structure
   producer, which it shares with the trail; each structure offers one add
   instant.

Item 1 is a closure precondition: RBT-002A is not DONE until the owner rules
on it.

## 7. Declared arithmetic (section 6A.7)

The only arithmetic the composers add to owner calls is listed in the JSON
`declared_arithmetic`:
- history selection by observation-time window;
- an exact-equality test;
- `TR / prior close`;
- a sign flip;
- the reaction ratio;
- an hourly volume sum;
- a minimum over members;
- band membership;
- the flow-score threshold test (`decision_greater_equal(FlowScore, 60)`);
- a timestamp comparison.

RBT-004/RBT-005's "no new formulas" criterion admits exactly these.

## 8. Composer obligations

**Census roots RBT-004/RBT-005 must promote** before calling them (section
5A.6):
- `features.rolling.rolling_zscore`
- `features.rolling.rolling_percentile`
- `features.rolling.true_ranges`
- `features.momentum.price_momentum_from_daily_bars`
- `quant.transforms.normal_cdf_score`
- `quant.comparisons.decision_greater_equal`
- `features.positioning._futures_basis_averages_by_time`
- `features.positioning._futures_basis_history`
- `data.ohlcv.next_bar_timestamp`

**Input sources to classify:**
- `research_backtest.replay_inputs.replay_market_bars_at` (wraps BTC-040
  `build_canonical_market_bars`; the composer never calls the latter directly)
- `research_backtest.replay_inputs.build_shared_replay_snapshot` (Bitstamp 1h
  volume)
- `research.us_equity_market_closures.load_closures`

**Accounted causes.** Every entry lists the accounted causes its `None` maps to
for the runtime completeness guard.

## 9. Warm-up and the evaluation start

Warm-up is computed from the bound inventory's coverage facts only, using
RBT-002's own simulation primitives (`compute_warm_up`).

On **all three venues**, the earliest instant at which every Entry Conviction
component and the core regime are complete is **no earlier than 2024-03-24**.
That is 43 days after the inventory's lower bound of 2024-02-10.

- **Binding entries:** `FLOW_Z_ETF_NORM_20D` and `FLOW_Z_FLOW_ACCEL`, which
  need 30 prior publication days after ETFNorm_20's first value.
- **Core regime:** complete from that date.
- **Entry Conviction:** a data-dependent lower bound, because whether the
  selected support cluster holds a pre-warm-up pivot depends on prices, which
  this pre-registration does not read.

This is an availability fact (policy V6 section 6A.8), not a stop.

Other components:

| Component | Earliest complete |
| --- | --- |
| Trend | Bitstamp 2021-08-02; Coinbase and Bitfinex 2021-08-23 |
| Volatility | 2022-05-29 (liquidations) |
| Positioning | 2020-10-02 |
| Structure | 2021-02-01 (lower bound) |

## 10. Pre-registration (section 6A.1)

**Data consulted:**
- the bound inventory's availability and coverage facts;
- owner code;
- configuration;
- Rulebook v1.2, policy V6 and the EPIC Y track;
- synthetic fixtures, in tests only.

**Not done:** no database connection, no market value read, and no score,
signal, trade or performance figure computed or inspected. Holdout NOT
COLLECTED; BTC-019 sealed sample unopened.

## 11. Change control

Until the independent RBT-002A review passes, review fixes may revise this V1
definition, and each revision carries a new digest. After that PASS, any change
to a rule, element, citation or warm-up fact changes the definition digest and
needs a new spec version (`CHAMPION_COMPLETION_SPEC_V2`). That version must be
recorded before the run it affects (policy V6 sections 6 and 11). The spec
cannot be re-derived after any EPIC Y outcome exists.
