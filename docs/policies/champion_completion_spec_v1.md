# Champion Completion Spec V1

Policy identifier: `CHAMPION_COMPLETION_SPEC_V1`

Status: **FROZEN PRE-REGISTRATION DEFINITION (RBT-002A), awaiting the
independent xHigh review.** A narrow, versioned strategy policy for **EPIC Y
only**, made under
[`RESEARCH_BACKTEST_POLICY_V7`](research_backtest_policy_v7.md) section 6A.

| Item | Value |
| --- | --- |
| Research strategy identifier | `swing_v1.2+completion_v1` = `swing_v1.2` / `strategy_config_v2` / `default_phase1` plus this spec |
| Scope | EPIC Y research backtests only. Not `swing_v1.2` for advisory, paper, EPIC X or BTC-019 use; adopting it anywhere else needs that workstream's own decision (policy V7 section 6) |
| Machine-readable definition | `btc_predictor/research_backtest/completion_spec.py` (typed) → canonical sorted JSON `backtest_evidence/research_backtest_v1/champion_completion_spec_v1.json` |
| Definition SHA-256 | `9819f84a6ec89f6c39dc1c5215edeae4898f91ebea30eccd5698ca11da65013f` (`champion_completion_spec_v1.json.sha256`) |
| Bound inventory | `rbt002_input_coverage_inventory_v1.json`, `108ab25b2240a76befc0f685cc684175e5207561d978bad099869fb0cc5efe3a` (reviewed under V5; kept by V7) |
| Evidence class | `RESEARCH_BACKTEST_NON_CERTIFYING`, canonical reference `UNRESOLVED` |

This document explains the definition. **The machine-readable definition is
authoritative**; where this summary is shorter, the JSON governs. Every rule,
citation and rationale is in the JSON, entry by entry.

## 1. What the spec is

The reviewed RBT-002 inventory marks 26 inputs of the champion's decision path
owner-less: 25 `OWNERLESS_UNDEFINED` inputs and `LEVEL_VOLUME_PERCENTILE`,
whose Rulebook 9.2 fallback row policy V7 section 6A.8 supersedes for this
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

**`UNIFORM_ZSCORE_V1`**, uniformly for the four Trend and three Flow inputs:

- x is the latest visible native owner observation D;
- H is the last **20 defined prior native observations**, current excluded,
  after PIT filtering; incomplete values are skipped and never filled;
- minimum 20; population SD (ddof 0), no per-input exceptions;
- exact original-value equality refuses a constant H before float conversion
  or calling the BTC-041 helper, whether x equals H or differs;
- otherwise call `rolling_zscore((*H, x), window=len(H), min_periods=20,
  sample=False)` and take the last result.

This adopts the existing Flow/CVD **20-observation/minimum-20 owner
convention** unchanged (flow.py `spot_perp_cvd_spread`, `_latest_zscore`).
Calendar span varies with native cadence and gaps; weekly values are never
repeated daily. This is explicit observation counting, with no time-based z
window.

**Review correction RBT002A-R4 (V7 section 6A.2).** The original 730-day/30
`NEW_PARAMETER` bypassed that applicable, feasible owner convention. The
180-day/30 positioning convention cannot fit 30 weekly observations (maximum
25); that valid observation did not authorize the lower-tier new window.
The original rejection of 20 observations because of cadence, recent change
or earlier availability is not permitted by source precedence. The original
26-entry calendar audit independently reproduced 2024-03-24. The corrected
rule moves the lower bound to 2024-03-10; no outcome informed the correction.

**`UNIFORM_PERCENTILE_V1`** remains unchanged: a daily quantity's prior
midrank `(less + 0.5 * equal) / n * 100` over `[D - 730 days, D)`, at least
365 defined observations, current excluded. Select history by observation
**time first**, then call `rolling_percentile((*H, x), window=len(H),
min_periods=365)`. Gaps never extend or shorten the time window silently.

## 3. The 26 entries

| Input | Disposition | Governing class | Rule (summary) |
| --- | --- | --- | --- |
| `TREND_Z_M4`, `TREND_Z_M12`, `TREND_Z_20W`, `TREND_Z_52H` | DEFINED | OWNER_CONVENTION (existing 20/20 z rule) | `UNIFORM_ZSCORE_V1` over the owner's `MOMENTUM_4W`, `MOMENTUM_12W`, `MA_DISTANCE_20W`, `HIGH_DISTANCE_52W` series |
| `FLOW_Z_ETF_NORM_5D`, `FLOW_Z_ETF_NORM_20D`, `FLOW_Z_FLOW_ACCEL` | DEFINED | OWNER_CONVENTION (existing 20/20 z rule) | `UNIFORM_ZSCORE_V1` over ETFNorm_5, ETFNorm_20, FlowAccel per US publication day; history values with `end_date=D'`, the per-window fund universe and the closure table; one anchor date D |
| `RANGE_PERCENTILE` | DEFINED | NEW_PARAMETER | `UNIFORM_PERCENTILE_V1` of `TR(d) / close(d - 1 day)` (BTC-041 true range over the prior close); one value to Orderliness, CAPITULATION and EUPHORIA |
| `DOWNSIDE_RETURN` | DEFINED | NEW_PARAMETER | `R_7 = P_t / P_(t-7) - 1` (signed) via `price_momentum_from_daily_bars(lookback_periods=7)`; one value to Orderliness, STRESS, CAPITULATION |
| `UPSIDE_RETURN` | DEFINED | NEW_PARAMETER | the same `R_7` to EUPHORIA |
| `LEVEL_REACTION_MAGNITUDE` | DEFINED | NEW_PARAMETER | min over the cluster's swing members of the net move from the pivot to the close of the swing owner's last confirming bar, as a fraction of price (the owner's unit) |
| `LEVEL_VOLUME_PERCENTILE` | DEFINED | NEW_PARAMETER | min over the cluster's swing members of `UNIFORM_PERCENTILE_V1` of the member's pivot-bar Bitstamp volume against the same-length trailing Bitstamp volume observed at each prior UTC day (section 4) |
| `CAPITULATION_EVENT` | OMITTED | POLICY_RULING | no event anchor is built (AVWAP optional, Rulebook 9.2/9.4; no owner yields an event) |
| `SEVERE_CROWDING_STATE` | DEFINED | CONFIG | `CROWDING.flagged if CROWDING.complete else None` (policy V7 section 6A.5; trim owner's convention) |
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
JSON. There are **16 `NEW_PARAMETER` elements**, each with its one-line
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

## 5. Positioning zero variance (E1 class, V7 section 6A.9)

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


The funding and OI-growth contracts follow the same five stages and carry
five required tests per owner, with no tolerance or restated z-score:

| Owner / refusal reason | Its own prior-history construction |
| --- | --- |
| `funding_health` / `FUNDING_HEALTH_ZERO_VARIANCE` | `_funding_averages_by_time(rows_t, average_window_days=R.average_window_days)` then `_funding_average_history(..., observation_time=R.observation_time, zscore_window_days=R.zscore_window_days)` |
| `open_interest_growth_health` / `OI_GROWTH_ZERO_VARIANCE` | Filter `rows_t` by `R.open_interest_unit`; `_aggregate_open_interest_by_time`, `_open_interest_growth_by_time(..., growth_window_days=R.growth_window_days)`, then `_oi_growth_history(..., observation_time=R.observation_time, zscore_window_days=R.zscore_window_days)` |

Both visibility timestamps must be at or before t. History count and latest
observation are cross-checked against R. Exact constant history refuses
whether the current value equals it or differs. No health or z-score is
passed on; structural unevaluability is recorded with that owner's reason.
Funding suppression also covers CAPITULATION's funding leg. Original owner
refusals stand; nonconstant owner results pass unchanged. All five additional
history helpers become classified census roots before RBT-004 calls them.

## 6. Named limitations and items surfaced for review

**Limitations.** The JSON `named_limitations` lists all 13 in full:
- E1 itself;
- the same Decimal z-score class in `funding_health` and
  `open_interest_growth_health`, both guarded under V7 section 6A.9;
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

**Owner-ruled (2026-10-03, V7):**
1. **Momentum Persistence: ACCEPTED unchanged** (V7 section 6A.10). The
   definition remains `100 * Phi(TREND_Z_M12)`. RBT-006 freezes the required
   ablation without that term and with proportional renormalization of the
   other four weights; RBT-007 reports action-band disagreements and a full
   variant replay, evaluation window only, per venue at base costs,
   `SENSITIVITY_ONLY_NOT_SELECTION`, never on holdout (V7 section 8).
2. **Funding and OI-growth E1 class: GUARDED** (V7 section 6A.9). All three
   guards are frozen in `positioning_zero_variance_guards`; the original basis
   contract is also retained as `e1_guard`.

**Items for independent review:**
3. **The `REGIME_INVALIDATION_PREDICATE` band.** Section 6A.5 is not monotone
   for exits.
4. **`CORRECTION_FROM_LOCAL_HIGH`** reads 'local high' as the trailing 52-week
   high, at weekly resolution.
5. **Source precedence: CORRECTED** by adopting the existing 20/20 owner
   convention uniformly; the 730/30 bypass is removed (section 2).
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

Items 1–2 are settled owner rulings; independent review must confirm V7 conformance before closure.

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
- `features.positioning._funding_averages_by_time`
- `features.positioning._funding_average_history`
- `features.positioning._aggregate_open_interest_by_time`
- `features.positioning._open_interest_growth_by_time`
- `features.positioning._oi_growth_history`

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
component and the core regime are complete is **no earlier than 2024-03-10**.
That is 29 days after the inventory's lower bound of 2024-02-10.

- **Binding entries:** `FLOW_Z_ETF_NORM_20D` and `FLOW_Z_FLOW_ACCEL`, which
  need 20 prior publication days after ETFNorm_20's first value.
- **Core regime:** complete from that date.
- **Entry Conviction:** a data-dependent lower bound, because whether the
  selected support cluster holds a pre-warm-up pivot depends on prices, which
  this pre-registration does not read.

This is an availability fact (policy V7 section 6A.8), not a stop.

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
- Rulebook v1.2, policy V7 and the EPIC Y track;
- synthetic fixtures, in tests only.

**Not done:** no database connection, no market value read, and no score,
signal, trade or performance figure computed or inspected. Holdout NOT
COLLECTED; BTC-019 sealed sample unopened.

## 11. Change control

Until the independent RBT-002A review passes, review fixes may revise this V1
definition, and each revision carries a new digest. After that PASS, any change
to a rule, element, citation or warm-up fact changes the definition digest and
needs a new spec version (`CHAMPION_COMPLETION_SPEC_V2`). That version must be
recorded before the run it affects (policy V7 sections 6 and 11). The spec
cannot be re-derived after any EPIC Y outcome exists.
