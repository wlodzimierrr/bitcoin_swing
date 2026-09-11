# EPIC X — Prospective Integration Evidence

Workstream authority for the post-Phase-1 prospective evidence program. This
document controls EPIC X ticket status, dependencies and acceptance criteria.
It is **not** Phase-1 execution authority: [Structured Tickets
v2.6](bitcoin_swing_predictor_structured_tickets_v2_6.md) keeps that role and is
not modified by this workstream.

## Why this workstream exists

BTC-019 is historically terminal at
`BTC019_TERMINALLY_BLOCKED_BY_MISSING_INTEGRATION_EVIDENCE`. Its V5 assessment
(`95e43ee1...775a89`) found eight inherited hard gates that name a rate, a
threshold, a direction and an intent but no decision universe, no complete
point-in-time input corpus, no comparison reference and no denominator. The
evidence that would answer them never existed, and manufacturing it backwards —
after the thresholds were already known — is exactly what the V5 finding
refuses.

EPIC X does the only remaining honest thing: it creates that evidence
**prospectively**, under rules frozen before a single qualifying observation is
accumulated.

EPIC X is not `BTC_REFERENCE_COMPOSITE_V6`. It reopens nothing, moves no frozen
byte of V3, V4, V5 or certified V1, and changes no threshold, direction or hard
role. BTC-019 remains terminal and the sealed 2015-2019 sample remains **NOT
COLLECTED, NOT OPENED and NOT EVALUATED**. A future reference candidate may
consume this corpus only under a separately governed promotion protocol.

## Boundaries

- EPIC T is `CLOSED / PASS WITH NON-BLOCKING FINDINGS` and is not reopened or
  modified by this workstream.
- No EPIC X work authorizes opening the BTC-019 sealed sample, and a Stage-B
  PASS here creates no automatic dependency that would.
- Phase-1 deterministic implementation is `COMPLETE`; the production canonical
  reference remains `UNRESOLVED`. Neither statement is changed by this program.

## POSTP1-001 — `DESIGN_AND_FREEZE_PROSPECTIVE_INTEGRATION_CORPUS_V1`

**Status:** `FAILED INDEPENDENT xHIGH REVIEW / SUPERSEDED PRE-DATA BY POSTP1-001R`
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Review model:** independent xHigh review of the exact protocol hash
**Owner module:** `btc_predictor/research/prospective_integration_corpus.py`
**Artifacts:** `prospective_evidence/prospective_integration_corpus_v1/`

The first attempted `PROSPECTIVE_INTEGRATION_CORPUS_V1` freeze used protocol
hash:

```text
aaa05c7288971ecb60e331c750fa728db13a3f2046cd597ffe4957a2f3d37326
```

Independent review returned `FAIL — PROSPECTIVE PROTOCOL INVALID` /
`PROSPECTIVE_PROTOCOL_REQUIRES_FIX`. No collection began and no qualifying
observation exists. The hash and its children below remain failed lineage; they
are not valid collection authority and are not overwritten by the correction.

Bound child contracts:

| contract | hash |
| --- | --- |
| `data_schema_contract` | `4664d1d59bf48f4f6409200f72b2b7ee8c33141518974efe8badb9f9d0209315` |
| `decision_universe` | `1205ec050c2bd46aeb882752e1834cc94984d5ac6caae911d3e312faab348ec9` |
| `evidence_sufficiency` | `923eb68e3138edf00bc3feec31838dc29d8e5924a5c6b377897f021fee5423d3` |
| `input_snapshot_schema` | `37e58f99df18522c444625e6919308bedfe47d4e7e8970c565281e8381ff7be7` |
| `metric_evidence_contracts` | `a5d6ee1097772a322855ba919beae30ff5acbd8784a7a43bfe99538d7707b295` |
| `portfolio_track_contract` | `6b69af9ae9e9bb9c3b24cd622d0aa4f432207a032b4bcd94e1cdf25db21e3a2c` |
| `semantic_diff_from_v5_blockers` | `3b6f2576a9e930b40443dc615b080bda016084caed1aa6edba0e3902cd50d47e` |
| `stage_b_evaluation_contract` | `66b1b7d62900af235fc33b3f7e4dfbb529d23c67451bc66e3ef511359fbc2e5b` |
| `stop_event_taxonomy` | `a239328b56a9312844e20319b6e88f4c4faecfc1c295519bf53b4f05b924ab72` |

### The eight measurements

Threshold, direction, hard role and stated intent are imported verbatim from
`btc_predictor.research.reference_composite_v2.V2_APPROVAL_GATES` and
re-verified on every build. The protocol supplies only what the historical
record lacked.

| metric | universe | statistic | threshold | direction |
| --- | --- | --- | --- | --- |
| `cross_market_confirmed_stop_preservation_rate` | `CROSS_MARKET_CONFIRMED_STOP_EVENTS` | rate | `1.0` | minimum |
| `gap_through_stop_consensus_agreement_rate` | `GAP_THROUGH_STOP_EVENTS` | rate | `0.99` | minimum |
| `isolated_venue_stop_suppression_rate` | `ISOLATED_VENUE_STOP_EVENTS` | rate | `0.95` | minimum |
| `regime_classification_disagreement_rate` | `REGIME_EVALUABLE_DECISION_TIMES` | rate | `0.02` | maximum |
| `risk_size_p95_relative_difference` | `SIZING_EVALUABLE_DECISION_TIMES` | nearest-rank p95 | `0.10` | maximum |
| `setup_classification_disagreement_rate` | `SETUP_EVALUABLE_DECISION_TIMES` | rate | `0.01` | maximum |
| `trade_action_disagreement_rate` | `ACTION_EVALUABLE_DECISION_TIMES` | rate | `0.01` | maximum |
| `trade_eligibility_disagreement_rate` | `ELIGIBILITY_EVALUABLE_DECISION_TIMES` | rate | `0.01` | maximum |

### What the protocol freezes

- **Observation unit** `decision_time`, in UTC, at two cadences on the existing
  canonical sessions: `STOP_HOURLY` and `STRATEGY_DAILY`. Both decision instants
  are `bar close + 5 minutes`, the reference-composite owner's own
  `DEFAULT_DECISION_DELAY`, which the frozen V2 `point_in_time` block states for
  an hourly bar as `observation_time + 1 hour + 5 minutes`. Availability is the
  frozen Phase-1 rule `AVAILABLE_AT_LTE_DECISION_TIME_V1`.
- **Decision universes** as pure predicates over inputs and per-track state. No
  universe reads a comparison outcome, so a timestamp can never enter or leave a
  denominator because the two tracks happened to agree.
- **Input snapshot** binding the frozen BTC-048 feature contract's own price and
  non-price families to their existing PIT raw tables, each with source
  identity, raw field, `observation_time`, `available_at`, `ingested_at`,
  revision policy, units, normalization owner and PIT rule.
- **Two deterministic portfolio tracks** from one frozen flat initial state,
  sharing every exogenous input except the reference under test, diverging
  naturally and never resynchronized.
- **A mechanical stop-event taxonomy** replacing
  `reference_composite_empirical.KNOWN_DEVELOPMENT_EVENTS`. No timestamp is
  hand-selected.
- **Evidence sufficiency** split into a frozen evaluability minimum and a
  deliberately deferred certification minimum (see below).
- **Post-hoc contamination prohibitions**, with any semantic change requiring
  `PROSPECTIVE_INTEGRATION_CORPUS_V2` and a new collection epoch.

### Recorded findings

1. **Certification sufficiency is deferred, not chosen.** Selecting a rate
   gate's minimum denominator is its own pre-data governance task in this
   repository — that is what
   `BTC_REFERENCE_COMPOSITE_V3_STRUCTURAL_THRESHOLD_CALIBRATION_V1` and the
   convergence review that followed it established. `PER_PAIR_WILSON_UPPER_BOUND_V1`
   is frozen for the V3 structural gate family and controls only that scope.
   All eight metrics are therefore marked
   `REPORTABLE_BUT_NOT_CERTIFIABLE_WITHOUT_SEPARATE_PRE_DATA_GOVERNANCE` and
   deferred to `PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1`. No
   Stage-B certification is reachable from this protocol alone.
2. **`CVD_SPREAD` has no persisted PIT source.**
   `btc_predictor.features.flow.CvdObservation` is a feature-layer boundary with
   no raw table and no collector, so one of the 33 frozen features cannot be
   reproduced from anything the repository persists today. The corpus declares
   the capture contract and marks it
   `REQUIRES_NEW_COLLECTOR_IN_FIRST_COLLECTION_TICKET`; it neither fabricates
   the series nor drops the feature from the champion.
3. **The reference identities are not named here.** No production candidate
   legitimately exists, so the corpus stays candidate-neutral and the
   `CONTROL_REFERENCE` / `CANDIDATE_REFERENCE` identities are supplied later by a
   separately frozen `PROSPECTIVE_INTEGRATION_EVALUATION_CONTRACT_V1`.
4. **The schema is a contract, not a migration.** Implementing the migration now
   would make a collection target exist before the freeze has been reviewed, so
   it belongs to the first collection ticket.
5. **The artifacts cannot live under `research_artifacts/`.** The frozen V5
   terminal assessment hashes an inventory of every JSON file under `data/` and
   `research_artifacts/`, so persisting a single new JSON artifact in either
   tree moves the V5 protocol hash away from `95e43ee1...775a89`. Measured
   directly: writing these ten artifacts under `research_artifacts/` recomputed
   V5 to `c67fd3a4...456c9d`. V5 is immutable authority and BTC-019 is terminal,
   so this program persists its own evidence under `prospective_evidence/`,
   outside that historical census, and a regression pins V5's recomputation to
   its frozen value. The V5 terminal classification and its
   `reproducible_integration_corpus_exists = false` finding are unaffected
   either way: none of these artifacts contains a mapping carrying all fourteen
   required corpus fields.

## POSTP1-001R — `CORRECT_AND_REFREEZE_PROSPECTIVE_INTEGRATION_CORPUS_V1`

**Status:** `FAILED REPEAT INDEPENDENT xHIGH REVIEW / SUPERSEDED PRE-DATA BY POSTP1-001R2`
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Review model:** repeat independent xHigh review of the exact corrected hash
**Owner module:** `btc_predictor/research/prospective_integration_corpus.py`
**Artifacts:** `prospective_evidence/prospective_integration_corpus_v1/`

Because no collection began and the failed hash never passed certification,
the corrected protocol remains `PROSPECTIVE_INTEGRATION_CORPUS_V1`. It is
refrozen at status `CORRECTED_PRE_DATA_PROTOCOL_AWAITING_REPEAT_XHIGH_REVIEW`
with definition hash:

```text
0d4f14370c2d17359fa3e5d36ce545f00e00da1a360a66ad3151a37d0cf45a9e
```

Corrected bound child contracts:

| contract | hash |
| --- | --- |
| `data_schema_contract` | `ada2223829adbe804e27e437f04fc46472587c02f2833126b7c558ae57246dd2` |
| `decision_universe` | `b8673d9a170585c62b8e3feec1d126c75c8aa9352238f260f235066649c16b39` |
| `evidence_sufficiency` | `af424423723f377d22fdddd01e396de9a2323db0c9aa59defd57b78076cc5df9` |
| `feature_input_coverage` | `7b049c0e49739d6e20370e2472c46134889d811f8f9b7a5b770cbc6f95c8ec31` |
| `input_snapshot_schema` | `35c55f616e6ed567400d597a2c747dbb67335514417a07496288d0bf1f303116` |
| `metric_evidence_contracts` | `98746db2d5d8d9a7d2d5846a83333ff356c6747f39949c2c0bdae38f799e3c98` |
| `portfolio_track_contract` | `1560eee774049e7eb72180ccfc18477e919eaf127646e03e1405cdf161318623` |
| `semantic_diff_from_v5_blockers` | `49b129afd07a08ddfbe6b4195e648b7ab28f712a3d2747739ec139ef7965673d` |
| `stage_b_evaluation_contract` | `8be898a9f858a6d60fbd44bbce6effc4c4d2051f87aea39952805be5798240e2` |
| `stop_event_taxonomy` | `ebd2d322db1994332844a6a597fcad7673b61632fb34f1361e758546af6e971e` |
| `warmup_history` | `0f718a197d19ccebe9068a51f11b3dd12c4d874e3c97de129172ab7ff3068055` |

The correction is bounded to the POSTP1-002 blocking findings. It adds
`raw.liquidations`; mechanically closes every `INITIAL_FEATURE_NAMES` input;
freezes CVD to the existing exact-hour cadence; binds action and eligibility to
decision-producing composites; makes isolated-venue evidence fully observable;
freezes gap-through to the immediately preceding contiguous hourly raw-provider
consensus close with a one-hour maximum gap; anchors all stop-event universes to
the control track's active stop; and binds every feature's owner-derived warmup.
It also requires the separately reviewed POSTP1-003 sufficiency governance hash
and the reviewed POSTP1-004 implementation before collection. POSTP1-001R
selects no sufficiency minimum.

### POSTP1-001R implementation notes

- The failed definition hash `aaa05c72...d37326`, its implementation commit,
  and its failed review classification remain inside the corrected definition's
  lineage. No failed artifact is presented as certified authority.
- The corrected input-coverage artifact proves all 33 frozen features close
  mechanically over nine required raw/PIT families. Missing data is never
  zero-filled, defaulted, or reconstructed from future information.
- The action contract compares the ordered decision/lifecycle/execution action
  envelope and retains source event identity. The eligibility contract composes
  setup, conviction, regime/context, R/R, hard-veto, data-quality, no-chase,
  lifecycle, risk-capacity, and reference-availability outputs into new-entry
  permission; neither reporting presentation nor a conviction bucket owns the
  scientific comparison.
- Focused correction validation is 104 tests. Two relevant regression passes
  cover 2,699 price/PIT/feature-lineage tests and 1,713 decision/risk/lifecycle/
  paper/backtest/reporting tests; overlaps are intentional. The complete suite
  passes 4,544 tests with Python 3.12.14 and `RuntimeWarning` as an error.
- No qualifying observation was collected, no real Stage-B aggregate was
  evaluated, and no BTC-019 sealed path was accessed. Collection remains
  unauthorized under this corrected implementation.

### Frozen future workflow

```text
POSTP1-001R CORRECTED PROTOCOL
  -> REPEAT INDEPENDENT XHIGH REVIEW OF THE EXACT CORRECTED HASH
  -> POSTP1-003 SUFFICIENCY GOVERNANCE
  -> INDEPENDENT XHIGH REVIEW OF THE EXACT SUFFICIENCY HASH
  -> POSTP1-004 SCHEMA + COLLECTORS + DECISION SNAPSHOT IMPLEMENTATION
  -> INDEPENDENT IMPLEMENTATION REVIEW
  -> COLLECTION AUTHORIZATION
  -> PROSPECTIVE COLLECTION AND WARMUP CAPTURE
  -> EVIDENCE-SUFFICIENCY CHECK
  -> STAGE-B EVALUATION
  -> IF PASS: candidate/reference research may proceed under a separately
     authorized protocol
  -> formal post-certification live-shadow gate when applicable
```

Collection requires all three reviews above. It is **not** authorized by
POSTP1-001R, and warmup capture is not an exception.

### POSTP1-002R outcome

The repeat independent xHigh review of `0d4f1437...f45a9e` returned
`FAIL — AMBIGUOUS FROZEN INPUT` /
`PROSPECTIVE_PROTOCOL_BLOCKED_BY_AMBIGUOUS_FROZEN_INPUT` on four findings:

- **P1-A** the CVD acquisition cadence was falsely claimed to be inherited from,
  and uniquely implied by, the Phase-1 feature owner;
- **P1-B** `OI_INTENSITY`'s `market_cap_usd` had no real prospective source
  contract, only the unqualified `raw.generic_series` family;
- **P1-C** liquidation missing-versus-empty semantics were unsupported by the
  named aggregate owner; and
- **P2** the 750-day warmup was not the exact owner-derived minimum.

No collection began under `0d4f1437...f45a9e` and no qualifying observation
exists. It is retained as failed lineage alongside `aaa05c72...d37326`.

## POSTP1-001R2 — `FREEZE_MISSING_PROSPECTIVE_INPUT_SEMANTICS_AND_REFREEZE_CORPUS_V1`

**Status:** `FAILED THIRD INDEPENDENT xHIGH REVIEW / REQUIRES PRE-DATA CORRECTION`
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Review model:** third independent xHigh review of the exact corrected hash
**Owner module:** `btc_predictor/research/prospective_integration_corpus.py`
**Artifacts:** `prospective_evidence/prospective_integration_corpus_v1/`

The protocol remains `PROSPECTIVE_INTEGRATION_CORPUS_V1`: neither failed hash
was certified, no collection epoch opened and no persisted observation carries
the superseded semantics, and this document's own change procedure binds
`PROSPECTIVE_INTEGRATION_CORPUS_V2` to a semantic change *after* collection
starts. The immutable implementation artifact retains its pre-review status
`CORRECTED_PRE_DATA_PROTOCOL_AWAITING_THIRD_XHIGH_REVIEW` and definition hash;
the failed review record in this ticket does not rewrite either:

```text
40e37067fdddee467ea6c8f0094a2498573e3ff379d35f0fdd5586af423c9862
```

Corrected bound child contracts:

| contract | hash |
| --- | --- |
| `data_schema_contract` | `90dea1ba5336f0fc5b74d83ccef88dc22d69f29e874e442ae0a151a7c092ee25` |
| `decision_universe` | `b78abe4e34dfdcd097523dc80548bc452c4a5eb787fda4ea82ba47784a36c3ce` |
| `evidence_sufficiency` | `af424423723f377d22fdddd01e396de9a2323db0c9aa59defd57b78076cc5df9` |
| `feature_input_coverage` | `7fca47cbc1872d8e17801b37b704b09284597dbc875f14b5f7e6571a2f65f517` |
| `input_snapshot_schema` | `4ac2a60b2909228ac4a818aea98700caf2ca2b6488c6605f74a5ebd808f65534` |
| `metric_evidence_contracts` | `98746db2d5d8d9a7d2d5846a83333ff356c6747f39949c2c0bdae38f799e3c98` |
| `portfolio_track_contract` | `92887cc240c77ebcea24eb5e9b521fda84f036f33e1d033eea663587cd5360f4` |
| `prospective_btc_market_cap_acquisition` | `fe0fe85532233e767a33ff1a4649cd72a5049746559d0be799aca3d88d50e817` |
| `prospective_cvd_acquisition` | `c485a4c36e2d4ddaf443955760ad9073e7b9e640a5307367399e5af25ffa8b76` |
| `prospective_liquidation_capture` | `23212f669cb0f7308a19df2498781f0747a43974f8bbdac39a9ceb23943f16c8` |
| `prospective_liquidation_percentile_adapter` | `849f7843066930418822dfc0f15e238897d65bc148a9882548b9decce8e75d79` |
| `semantic_diff_from_v5_blockers` | `49b129afd07a08ddfbe6b4195e648b7ab28f712a3d2747739ec139ef7965673d` |
| `stage_b_evaluation_contract` | `3df077ec947c7350393aaa1e7ff73dbabcf7e8829b0b56adfbcc207c12edf98c` |
| `stop_event_taxonomy` | `ebd2d322db1994332844a6a597fcad7673b61632fb34f1361e758546af6e971e` |
| `warmup_history` | `71af8a1a0fe31e60d0be3bd37292a73f174b8112b731eb619d41ad26d1de50ac` |

### The governance distinction this correction rests on

Phase-1 owns **feature semantics** — `spot_perp_cvd_spread`,
`open_interest_intensity` and `calculate_orderliness_score` keep their formulas,
windows and reason codes untouched. For three of their raw inputs Phase-1 never
owned **acquisition semantics**: which source produces a raw observation, on
what cadence, with what timestamp, availability and revision meaning. Because
this corpus has not begun collection, POSTP1-001R2 freezes those missing
acquisition semantics now. Every new rule is declared explicitly as
`NEW_PROSPECTIVE_PRE_DATA_ACQUISITION_GOVERNANCE`, carries
`historically_inherited = false`, is hash-bound by the parent protocol, and was
selected without inspecting any Stage-B outcome. Nothing newly authored is
presented as historically implicit.

### P1-A — CVD acquisition

`PROSPECTIVE_CVD_ACQUISITION_V1` (`c485a4c3...f8b76`). The previous claim that an
exact UTC hourly cadence was uniquely implied by `spot_perp_cvd_spread` was
false: the owner intersects the available spot and perp `observation_time` sets,
applies no grid, spacing or interval test, and is observation-count based. The
corpus now persists `historical_feature_owner_specifies_cadence = false` and
`historical_feature_owner_specifies_window = 20 prior common observations`, and
records that unit tests exercising hourly fixtures are not cadence authority.

`1h` is selected **prospectively** against eight predeclared criteria, with `4h`
and `1d` assessed and rejected on record. It is the finest interval that closes
natively in the sources the repository already integrates, it coincides with the
`STOP_HOURLY` decision grid and with every `STRATEGY_DAILY` session opening, it
needs no aggregation and therefore admits no partial-bucket lookahead, it needs
no arbitrary phase origin to replay, and it keeps the frozen
20-prior-observation window from becoming the corpus's binding warmup. The
contract freezes the spot and perpetual market universes, provider identity,
cadence, timestamp alignment, calculation interval, aggregation method, the
`cvd_usd` interval-delta definition, the buy/sell classification owner,
`observation_time` / `available_at` / `ingested_at`, revision, missing-interval
and duplicate semantics, units and the PIT rule. `CVD_SPREAD` initialization is
20 prior aligned hourly common observations plus 1 current. Any change to
cadence, provider, market universe, classification or aggregation requires
`PROSPECTIVE_CVD_ACQUISITION_V2` and a new epoch; no observation is resampled.

### P1-B — BTC market cap

`PROSPECTIVE_BTC_MARKET_CAP_ACQUISITION_V1` (`fe0fe855...50e817`).
`existing_market_cap_producer = NONE`: `MarketCapObservation` is constructed only
inside a feature test, and `raw.generic_series` declares no market-cap series in
either its supported series types or its series definitions. The unqualified
generic-series family is not a source contract and is no longer accepted as one.

One exact identity is frozen on the repository's own point-in-time scalar-series
table: `series_id = BTC_MARKET_CAP_USD`, `series_type = market_cap`,
`unit = usd`, provider `coingecko`, daily observations on the exact UTC day start,
with the existing `NEW_REVISION_ROW_PER_RESTATEMENT` convention. `market_cap =
price x circulating supply` is considered and rejected: it is owned by no
repository authority, it needs a second supply contract, and it would make an
exogenous feature input depend on the reference identity under test, which
`SHARED_EXOGENOUS_INPUT_RULE` forbids. The contract also records the owner's own
exact-`observation_time` intersection rule, so the prospective open-interest
capture consumed by `OI_INTENSITY` must present its aggregate on the same daily
grid. POSTP1-004 must verify the named provider against the frozen semantics
before collection and fail closed — reissuing as
`PROSPECTIVE_BTC_MARKET_CAP_ACQUISITION_V2` — rather than adapting the contract
to whatever the provider publishes.

### P1-C — liquidation feed state and normalization

`PROSPECTIVE_LIQUIDATION_CAPTURE_V1` (`23212f66...3f16c8`) and
`PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_V1` (`849f7843...e75d79`).
`aggregate_btc_derivatives_available_at` initialises both liquidation notionals
to `Decimal("0")` and exposes no feed-state field, so a missing feed and an
observed feed with zero events are byte-identical zeros;
`existing_aggregate_distinguishes_missing_from_empty = false` is persisted and
the existing owner is not modified. The prospective capture layer persists
`feed_status`, `event_count` and the notional pair independently, in the new
append-only `research.prospective_liquidation_feed_state` table, over the
vocabulary `OBSERVED_WITH_EVENTS`, `OBSERVED_ZERO_EVENTS`, `SOURCE_UNAVAILABLE`,
`LATE`, `INVALID`. The first two are observations — `OBSERVED_ZERO_EVENTS`
legitimately carries 0 USD before normalization — and the last three make the
required input missing and the decision not evaluable. A replay reproduces the
distinction from storage and may never re-derive `feed_status` from a zero value.

No executable owner produces `liquidation_percentile`, so one is frozen before
data. It sums both observed sides, runs on one observation per fully observed
canonical UTC day, and inherits the repository's single existing percentile
convention — the midrank of a prior-only half-open window, implemented
identically in the volatility and positioning owners — with the 730-day window
and 365 minimum prior observations of `volatility_percentile`, the only
percentile already co-consumed by `calculate_orderliness_score`. The adapter
adds no new binding warmup and `calculate_orderliness_score` is unchanged.

### P2 — warmup

`750 calendar days` is withdrawn as the exact owner-derived warmup. It added a
730-day *eligible trailing window* to a 20-day upstream window as if both were
required populated histories, then used the sum as an elapsed-time evaluability
test. Three quantities are now frozen separately for all 33 features:

| quantity | meaning |
| --- | --- |
| `rolling_window_span` | the eligible trailing window an owner searches |
| `minimum_observation_count` | qualifying observations required inside it |
| `minimum_contiguous_history_to_first_evaluable` | a `PLANNING_ESTIMATE_NOT_EVALUABILITY_AUTHORITY` value only |

For `VOL_PERCENTILE_2Y` the owner-derived values are a 730-day half-open
`[t - 730d, t)` window, 365 prior `RV_20` observations inside it, and an upstream
requirement of 21 contiguous daily closes per `RV_20`. With contiguous daily
observations it therefore first defines at **386 contiguous daily sessions**
(385 elapsed calendar days), pinned by a synthetic fixture against the
production owner. Evaluability is the owner's rule — enough qualifying
observations inside the applicable trailing window and every upstream
initialization satisfied — never `elapsed_days >= a hardcoded longest warmup`.
Composites inherit their components' predicates and invent no window.

### POSTP1-001R2 implementation notes

- Both failed definition hashes, their implementation commits and their failed
  review classifications remain inside the corrected definition's lineage as
  explicitly non-authoritative pre-data history. Neither opened a collection
  epoch.
- The corrected input-coverage artifact proves all 33 frozen features close
  mechanically, `OI_INTENSITY` and `OI_INTENSITY_PERCENTILE_180D` now naming the
  frozen market-cap source contract rather than a generic family.
- Everything the repeat review passed is preserved unchanged: the stop-event
  taxonomy and its `NOT_CLASSIFIABLE` / gap-through / one-hour-contiguity rules,
  the control-reference stop anchor, `TRADE_ACTION_COMPARISON_OWNER_V1`,
  `TRADE_ELIGIBILITY_COMPOSITE_OWNER_V1`, and the risk-size definition
  (`position_notional`, `abs(candidate - control) / control`, nearest-rank p95).
- The accepted consequence of a divergence-preserving design is that after
  portfolio divergence, action and eligibility disagreement may persist across
  many subsequent slots. That is expected sensitivity evidence and is never a
  reason to outcome-filter a denominator; no universe predicate reads a
  comparison outcome.
- POSTP1-001R2 selects no sufficiency minimum and authorizes no collection.

### POSTP1-002R2 outcome

The third independent xHigh review of `40e37067...c9862` returned
`FAIL — MARKET CAP SOURCE CONTRACT INVALID` /
`PROSPECTIVE_PROTOCOL_REQUIRES_FIX`. The hash and all fifteen child hashes
recompute exactly, both predecessor hashes remain explicit non-authoritative
pre-data lineage, and direct comparison with `V2_APPROVAL_GATES` finds zero
threshold, direction, hard-role or metric-intent changes. The stop, action,
eligibility, risk-size, warmup and sufficiency-sequencing contracts also retain
their reviewed behavior. Three acquisition blockers nevertheless prevent
certification:

- **P1-A — the frozen CoinGecko daily market-cap observation is unavailable at
  the decision that requires it.** The corpus schedules a daily decision at bar
  close plus five minutes and forbids OI-intensity from using an earlier
  market-cap day. CoinGecko documents its 00:00 UTC daily point as available at
  00:35 on the following UTC day, thirty minutes after that decision. See the
  official [`/coins/{id}/market_chart/range` documentation](https://docs.coingecko.com/reference/coins-id-market-chart-range)
  and [`/coins/{id}/history` documentation](https://docs.coingecko.com/reference/coins-id-history).
  CoinGecko also documents same-day and next-day historical market caps as
  provisional, with scheduled restatements through day + 2 and no API finality
  field; see its [historical-market-cap revision policy](https://support.coingecko.com/hc/en-us/articles/61976309053337-Why-do-historical-market-cap-values-change-shortly-after-a-date-then-settle).
  The frozen rule that `available_at` is the instant the provider first
  published the point is not obtainable from the payload, and the protocol
  freezes no polling/retrieval schedule capable of producing a deterministic
  substitute. Satisfying the source would require a new observation/decision,
  staleness or acquisition rule, not a uniquely mechanical review fix.
- **P1-B — the CVD source and gap contract is not complete.** The spot venue
  list is concrete, but the perpetual venue/instrument universe and the actual
  spot/perpetual provider identities are deferred to a future collection epoch,
  so changing them cannot move this protocol hash. More importantly, the
  contract says a missing common timestamp contributes no observation to the
  count-based window. The production owner has no grid or spacing check, and a
  synthetic 22-hour sequence with the interior 20:00 spot observation missing
  still produces a complete feature at 21:00 from 21 non-contiguous common
  observations. The prospective grid therefore is not enforced before the
  historical owner as this freeze requires.
- **P1-C — liquidation coverage cannot distinguish a complete expected feed
  from partial provider/instrument coverage.** The new status vocabulary
  correctly keeps `OBSERVED_ZERO_EVENTS` separate from unavailable, late and
  invalid states, but the capture contract freezes neither an actual provider
  nor an expected instrument universe. Persisting a provider, instrument,
  `event_count` and source-record digest on an observed row cannot prove that
  every expected feed was present for the interval. A partial feed can
  therefore be labelled affirmatively observed and converted to numeric
  notional without a hash-bound coverage census.

No review fix was made because each blocker requires a new, explicit pre-data
acquisition decision and a newly frozen hash. POSTP1-003 may not begin. No
qualifying observation was collected, no real Stage-B aggregate was evaluated,
no BTC-019 sealed path was accessed, and collection remains unauthorized.

## POSTP1-001R3 — `CORRECT_SOURCE_COVERAGE_AND_REFREEZE_CORPUS_V1`

**Status:** `COMPLETE / FAILED FOURTH INDEPENDENT xHIGH REVIEW / SUPERSEDED PRE-DATA BY POSTP1-001R4`
**Dependencies:** POSTP1-001R2 implementation and POSTP1-002R2 failed review
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Review model:** fourth independent xHigh review of the exact corrected hash
**Owner module:** `btc_predictor/research/prospective_integration_corpus.py`
**Artifacts:** `prospective_evidence/prospective_integration_corpus_v1/`

### Scope

Correct only the three POSTP1-002R2 acquisition blockers before any collection:

1. freeze a CoinGecko polling, availability, revision-selection and decision-
   binding rule that consumes only a named observation known to have been
   retrieved before the decision, without treating provider publication time as
   observable and without falling back beyond the exact expected source date;
2. freeze concrete spot/perpetual CVD providers and instruments and enforce the
   exact contiguous 21-hour prospective grid before the historical observation-
   count feature owner; and
3. freeze one complete liquidation provider/instrument census whose affirmative
   coverage predicate separates an observed zero-event interval from a partial
   or absent feed.

The correction may add deterministic reference selectors/classifiers needed to
make these contracts executable, but it must not implement the POSTP1-004
network collectors, migrations or decision-snapshot pipeline. It may not alter
Phase-1 feature formulas, V2 Stage-B gates, stop/action/eligibility/risk
semantics, sufficiency minima, BTC-019, V3, certified V1, V4, V5 or EPIC T.

### Acceptance criteria

- CoinGecko's official 00:35 UTC daily availability and documented day + 2
  restatements are represented honestly. Collection uses a fixed post-cache
  polling schedule; `available_at` is the locally observable successful-response
  completion instant, never an inferred provider publication instant.
- A deterministic decision rule names exactly one required market-cap
  observation date. It is the newest date from the latest completed scheduled
  poll cycle, and absence of that exact date is not replaced by an older value.
- An executable PIT selector passes at most one latest-available market-cap
  revision per observation time to `open_interest_intensity`; historical
  revisions are never averaged together.
- CVD uses exact, hash-bound exchange-native public sources, spot instrument and
  perpetual instrument. Units, source identifiers, event timestamps, taker-side
  meaning, event inclusion and interval completion evidence are explicit.
- The CVD adapter accepts exactly the current hour and its 20 immediately prior
  UTC hours for both market types. An interior gap remains non-evaluable until
  it has aged out of that contiguous window; later observations cannot compress
  it away.
- Liquidation capture binds one expected provider/instrument universe and a
  complete-interval predicate. Disconnects, sequence gaps, heartbeat gaps,
  invalid events, late finalization and unexpected source identities cannot be
  labelled `OBSERVED_ZERO_EVENTS`.
- Synthetic tests pin market-cap decision boundaries and revision selection,
  CVD provider/grid behavior, complete/partial/zero liquidation states, child-
  and top-level hash movement, gate parity and historical authority immutability.
- The third failed hash remains explicit non-authoritative lineage. No
  qualifying observation is collected, no real Stage-B aggregate is evaluated,
  and collection remains unauthorized pending the fourth review, POSTP1-003 and
  POSTP1-004 reviews.

### POSTP1-001R3 implementation notes

Implementation commit `f54025690975047c9c859567303088a5059f342e`
refreezes `PROSPECTIVE_INTEGRATION_CORPUS_V1` at:

```text
e60a951476afb41437347220e7ab043ed6261cc03489da379adfca915c9a7dca
```

- Market cap is the exact CoinGecko `/coins/bitcoin/history` response field
  `market_data.market_cap.usd`. A UTC cycle polls at 00:45, 00:50 and 00:55,
  ends at 00:56, and requeries poll-day minus 1, 2 and 3. `available_at` is the
  locally observed successful-response completion instant. Before 00:56 a
  decision uses the prior cycle; afterwards it uses the current cycle. The
  required observation is exactly poll-day minus 1, with no older fallback.
  `ProspectiveMarketCapObservation` retains the exact series, provider, source,
  revision and response digest; the PIT selector emits only the latest
  available revision per timestamp to the historical owner, preventing its
  duplicate-timestamp average from blending revisions.
- CVD is frozen to Kraken spot WebSocket v2 `BTC/USD` and Kraken Futures
  WebSocket v1 `PI_XBTUSD`, a verified tradeable 1 USD inverse perpetual.
  Provider taker side owns the sign; event timestamps, included futures trade
  types, exact-hour bucketing, source IDs and completion evidence are explicit.
  `ProspectiveCvdAggregateObservation` retains provider, instrument, revision
  and a completion-evidence digest. Its selector passes exactly one latest
  revision for both markets over the current hour plus the 20 immediately prior
  hours; an incomplete or missing interior hour remains missing.
- Liquidation capture uses only liquidation-typed events from the same Kraken
  Futures `PI_XBTUSD` feed. Sell maps to long liquidation, buy to short, and
  notional is quantity times the 1 USD contract size. The executable interval
  classifier requires pre-start acknowledgement, continuous WebSocket and
  heartbeat coverage through close, no sequence gap or invalid/conflicting
  event, a consistent unique-UID census and timely local finalization.
  `OBSERVED_ZERO_EVENTS` is therefore possible only for a complete empty
  census; partial, late and invalid evidence carries null notionals.
- All three failed hashes remain non-authoritative, pre-data lineage. Phase-1
  feature formulas, all 39 V2 gates, stop/action/eligibility/risk contracts,
  sufficiency sequencing, V3, certified V1, V4, V5 and EPIC T are unchanged.
  Collection remains unauthorized and no qualifying observation or real
  Stage-B outcome was produced.
- Validation: 160 focused tests, 1,283 selected source/feature/authority
  regressions and the complete 4,600-test Python 3.12.14 suite pass with
  `RuntimeWarning` promoted to an error. `compileall`, scoped diff checks,
  artifact restore/reproduction, 15-child binding, V2 gate parity and direct
  immutable V3/certified-V1/V4/V5 recomputation all pass.

### POSTP1-002R3 review outcome

**Status:** `COMPLETE / FAIL`
**Result:** `FAIL — CORRECTED PROSPECTIVE PROTOCOL INVALID`
**Classification:** `PROSPECTIVE_PROTOCOL_REQUIRES_FIX`

The fourth independent xHigh review rejected exact hash
`e60a951476afb41437347220e7ab043ed6261cc03489da379adfca915c9a7dca`
on four P1 acquisition-integrity findings:

1. CoinGecko request/response observation identity was not reproducibly bound;
2. Kraken spot/perpetual CVD stream completeness was not mechanically
   reproducible;
3. Kraken liquidation zero/completeness and the daily 24-hour census were not
   mechanically reproducible; and
4. scientifically material locally observed timestamps lacked governed local-
   clock integrity.

The review passed the existing source/instrument/event semantics, liquidation
direction and notional, contiguous CVD selector, percentile adapter, 33-feature
coverage, Stage-B parity and previously frozen stop/action/eligibility/risk/
warmup semantics. No observation was collected under the failed hash.

## POSTP1-001R4 — `HARDEN_PROSPECTIVE_SOURCE_COMPLETENESS_AND_REFREEZE_CORPUS_V1`

**Status:** `COMPLETE / FAILED FIFTH INDEPENDENT xHIGH REVIEW / SUPERSEDED PRE-DATA BY POSTP1-001R5`
**Dependencies:** POSTP1-001R3 implementation and POSTP1-002R3 failed review
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Review model:** fifth independent xHigh review of the exact corrected hash
**Owner modules:** `btc_predictor/research/prospective_integration_corpus.py`,
`btc_predictor/research/prospective_source_integrity.py`
**Artifacts:** `prospective_evidence/prospective_integration_corpus_v1/`

### Scope and acceptance criteria

Correct only the four POSTP1-002R3 findings before collection:

- bind every CoinGecko observation to one immutable `YYYY-MM-DD` request,
  exact response bytes, exact case-sensitive `bitcoin`/`btc` identity, positive
  finite USD payload, acquisition hash and usable request/response clock
  evidence; derive `observation_time` solely from that requested date;
- derive Kraken hourly completeness from one uninterrupted, pre-start
  acknowledged `SOURCE_STREAM_EPOCH_V1`, collector-owned monotonic ping/pong
  liveness, collector-health counters, clock integrity and an exact event
  census; never stitch epochs or assume undocumented cross-reconnect sequence
  continuity;
- derive liquidation zero/positive states from that same Futures evidence and
  admit a daily value only from the exact 24 expected UTC hourly identities,
  with every hour complete and no duplicate identity; and
- bind scientific local timestamps to `PROSPECTIVE_CLOCK_INTEGRITY_V1`, with
  synchronized UTC offset and uncertainty each at most one second and a
  monotonic/wall cross-check for material clock steps.

The correction must preserve all passed R3 protocol areas, all eight Stage-B
gate values and intent, Phase-1 formulas, BTC-019 terminality and immutable V3,
certified V1, V4 and V5 hashes. It must implement neither persistent collection
nor sufficiency governance and must authorize no collection.

### POSTP1-001R4 implementation notes

Implementation commit `b813365c39d0423babe17caeabf85e7b7473de09`
refreezes `PROSPECTIVE_INTEGRATION_CORPUS_V1` at:

```text
fd946a091d9e1944163a78d331c31c518de2f21a35707a32141443d05f9bedff
```

- Four failed hashes are retained with `authoritative = false`,
  `qualifying_observations_collected = false` and
  `superseded_before_collection = true`, including R3 hash
  `e60a9514...a7dca` and implementation `f5402569...f342e`.
- `CoinGeckoMarketCapRequest` persists the exact serialized query, scheduled and
  actual timing, HTTP status, request/response digests, collector/acquisition
  identity and clock bindings. `COINGECKO_MARKET_CAP_RESPONSE_VALIDATION_V1`
  rejects wrong or duplicate identity/schema fields and nonpositive/nonfinite
  USD values. `ProspectiveMarketCapObservation` independently revalidates the
  bound response and exposes no caller-supplied observation-time/value/provider
  constructor path.
- `SOURCE_STREAM_EPOCH_V1` defines exact start/end rules and reconnect as a new
  epoch. `STREAM_LIVENESS_POLICY_V1` freezes 30-second collector pings, a
  10-second pong timeout and 40-second maximum liveness gap on monotonic time.
  Kraken spot `trade_id` remains an event identity, while Futures `seq` is
  scoped to one subscription epoch with no undocumented cross-reconnect rule.
- `CVD_INTERVAL_COMPLETENESS_V1` reconstructs both legs from their epoch,
  liveness, health, clock and sorted/deduplicated event objects. The 21-hour
  selector admits only exact complete common hours and cannot substitute an
  older hour or a second epoch.
- `LIQUIDATION_INTERVAL_COMPLETENESS_V1` reuses the Futures completeness owner.
  Only a complete empty census produces `OBSERVED_ZERO_EVENTS`; partial,
  late or invalid evidence produces no numeric value.
  `LIQUIDATION_UTC_DAY_CENSUS_V1` requires exactly 24 ordinary UTC hours,
  rejects duplicates and deterministically sums complete hours in a fixed
  Decimal context. The accepted percentile adapter is unchanged.
- Seven new hash-bound child artifacts cover clock integrity, stream epoch,
  stream liveness, CoinGecko response validation, CVD completeness,
  liquidation interval completeness and liquidation daily census. The parent
  now binds 22 child definitions, and the schema exposes the underlying
  request, response, clock, epoch, liveness, health, event and census records.
- Validation: 196 focused tests, 1,838 selected source/feature/PIT/lifecycle/
  backtest/authority regressions, and the complete 4,636-test Python 3.12.14
  suite pass with `RuntimeWarning` promoted to an error. Artifact restoration,
  `compileall`, scoped `git diff --check`, all eight gate-parity checks and
  immutable V3/certified-V1/V4/V5 recomputation pass.
- No persistent collector, migration, qualifying observation, real Stage-B
  aggregate or sufficiency minimum was created. BTC-019 and its sealed sample
  remain untouched. Classification is
  `PROSPECTIVE_INTEGRATION_CORPUS_READY_FOR_FIFTH_XHIGH_REVIEW`.

### POSTP1-002R4 review outcome

**Status:** `COMPLETE / FAIL`
**Result:** `FAIL — CORRECTED PROSPECTIVE PROTOCOL INVALID`
**Classification:** `PROSPECTIVE_PROTOCOL_REQUIRES_FIX`

The fifth independent xHigh review rejected exact hash
`fd946a091d9e1944163a78d331c31c518de2f21a35707a32141443d05f9bedff`
on four P1 pre-data source-integrity findings:

1. CoinGecko validation hashes exact response bytes in memory but the frozen
   schema persists neither those bytes nor the clock-interval record needed to
   replay validation. The executable validator also admits a response taking
   longer than the frozen 45-second timeout, and the schema has no unambiguous
   representation for the required timeout-attempt audit rows.
2. Clock intervals do not require the same collector host and process at both
   ends, and the frozen protocol specifies no health-renewal cadence or maximum
   clock-record age. The persistence contract retains only hashes for material
   interval evidence and cannot independently reconstruct the cross-check.
3. Stream liveness does not cross-check the wall interval duration against its
   monotonic interval. Source events are not required to have arrived by
   finalization or decision time, and the schema does not persist enough of the
   epoch, interval, health and clock evidence to reproduce completeness. Frozen
   Kraken metadata also has no runtime revalidation/fail-closed rule.
4. The liquidation daily reducer validates only each hourly record's surface
   fields and self-digest; it does not resolve and revalidate the cited
   completeness evidence. An incomplete hour can therefore be relabelled as
   `OBSERVED_ZERO_EVENTS`, rehashed and admitted to a `COMPLETE` daily zero.

Independent adversarial probes demonstrated materially different conforming
collector outcomes and a missing-evidence-to-favourable-evidence path. The
review nevertheless reproduced the parent hash and all 22 child hashes,
confirmed all 22 parent bindings and four failed predecessor lineage rows,
verified zero changes to the eight Stage-B gates, and passed the previously
accepted warmup, stop/action/eligibility/risk, 33-feature coverage, decimal,
ordering and hash determinism areas. Validation passed 196 focused tests,
3,346 selected source/feature/PIT/lifecycle/backtest/authority regressions and
the complete 4,636-test Python 3.12.14 suite with `RuntimeWarning` promoted to
an error. No qualifying observation was collected, no persistent collection
started, no real Stage-B aggregate was evaluated, and BTC-019 and its sealed
sample remained untouched. POSTP1-003, POSTP1-004 and collection remain
unauthorized pending a corrected successor protocol and its independent review.

## POSTP1-001R5 — `MAKE_PROSPECTIVE_SOURCE_EVIDENCE_REPLAYABLE_AND_REFREEZE_CORPUS_V1`

**Status:** `COMPLETE / AWAITING SIXTH INDEPENDENT xHIGH REVIEW`
**Dependencies:** POSTP1-001R4 implementation and POSTP1-002R4 failed review
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Review model:** sixth independent xHigh review of the exact corrected hash
**Owner modules:** `btc_predictor/research/prospective_integration_corpus.py`,
`btc_predictor/research/prospective_source_integrity.py`
**Artifacts:** `prospective_evidence/prospective_integration_corpus_v1/`

### Scope and acceptance criteria

Correct only the four POSTP1-002R4 P1 findings before collection, under one new
governing principle: **scientific surface records are not authorities**. Every
derived or surface row must resolve its complete immutable evidence graph —
resolve the referenced evidence, recompute its digest, validate its full
semantics, verify cross-record identity, and only then derive the scientific
value or status. A `record_sha256`, `completion_evidence_sha256`,
`request_sha256` or `response_sha256` is an identity and integrity check and
never a replacement for the referenced evidence.

- P1-A: make CoinGecko provenance replayable. Every scheduled attempt is a
  first-class persistable record regardless of outcome; the 45-second HTTP
  timeout is enforced mechanically from monotonic elapsed time; timeout and
  other non-success attempts are representable without fabricated response
  fields; exact raw response bytes are persisted and reverified on replay.
- P1-B: bind clock evidence to one explicit monotonic domain, freeze a clock
  health renewal and freshness contract pre-data, and persist every material
  clock record rather than only its hash.
- P1-C: cross-bind wall and monotonic interval coverage, bound source-event
  `received_at` by interval finalization and decision time, persist the full
  epoch, liveness, collector-health, event and metadata evidence graph, and
  fail closed on PI_XBTUSD runtime metadata drift.
- P1-D: resolve and independently revalidate the cited hourly completeness
  evidence in the liquidation daily reducer instead of trusting a
  caller-rehashable hourly surface row.

The correction must preserve all passed R4 protocol areas, all eight Stage-B
gate values and intent, the 33-feature inventory, warmup/evaluability, the stop
and action/eligibility/risk owners, Phase-1 formulas, BTC-019 terminality and
the immutable V3, certified V1, V4 and V5 hashes. It must implement neither
persistent collection nor sufficiency governance and must authorize no
collection.

### POSTP1-001R5 implementation notes

Implementation commit `428356665dff0985cf8b1c379f6f18bf6cc5bac1`
refreezes `PROSPECTIVE_INTEGRATION_CORPUS_V1` at:

```text
8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7
```

- Five failed hashes are retained with `authoritative = false`,
  `qualifying_observations_collected = false` and
  `superseded_before_collection = true`, including R4 hash `fd946a09...bedff`,
  implementation `b813365c...b7473de09` and review `c61b16cb...39f2ef5f1`.
- `COINGECKO_MARKET_CAP_REQUEST_ATTEMPT_V1` makes every scheduled attempt
  persistable over the outcome vocabulary `SUCCESS`, `TIMEOUT`, `HTTP_ERROR`,
  `TRANSPORT_ERROR`, `INVALID_RESPONSE`, `CLOCK_INVALID` and `CYCLE_CUTOFF`.
  `http_status`, `raw_response_bytes`, `response_sha256` and the market-cap
  value are nullable or absent per outcome, so a timeout row needs no
  fabricated status, empty body or zero value. Scientific success requires a
  mechanically derived `monotonic_elapsed_seconds <= 45`: 45.000 is admitted
  and 45.001 is not, and the 00:56 cycle cutoff remains a separate independent
  bound. Exact response bytes are persisted as `BYTEA`, and replay reverifies
  `sha256(raw_response_bytes) == response_sha256`, reparses the bytes,
  rechecks `id == bitcoin` and `symbol == btc`, requires a finite positive
  USD value, and derives `observation_time` from the persisted validated
  requested date, so a response reattached to `D+1` is refused.
- `PROSPECTIVE_CLOCK_INTEGRITY_V1` now carries a monotonic domain identity of
  `collector_host_id`, `collector_process_id`, `process_start_identity` and
  `boot_id`. Two anchors used for one duration must share that identity, so
  cross-host or cross-process subtraction refuses. Elapsed time is recomputed
  from the anchors rather than trusted from a caller field. Wall and monotonic
  elapsed must agree within one second, so a 3600-second wall hour backed by 20
  monotonic seconds refuses. Health polling is frozen at 30 seconds with a
  maximum record age of 40 seconds and a maximum renewal gap of 40 seconds,
  aligned with the existing 30-second stream-liveness cadence; a one-hour
  interval needs valid same-domain observations covering the whole interval and
  its finalization path.
- `KRAKEN_FUTURES_INSTRUMENT_METADATA_VALIDATION_V1` freezes `symbol`
  `PI_XBTUSD`, `type` `futures_inverse`, `underlying` `rr_xbtusd`,
  `contractSize` 1 USD and `tradeable` true, validated no more than five
  minutes before each exact UTC hour and revalidated at or after interval close
  but no later than, and no more than five minutes before, finalization. Any
  material drift makes the hour
  `INVALID / REQUIRED_INPUT_MISSING`, with no silent contract-size recompute
  and no instrument substitution.
- Source events persist both provider `event_time` and clock-validated local
  `received_at`. An interval finalized at `F` admits only `received_at <= F`,
  and decision-time use additionally requires the aggregate `available_at <= D`.
  Revisions are append-only: a late event produces a new revision with a later
  `available_at` and can never rewrite a closed one, so replay of an earlier
  decision keeps using the earlier revision.
- `SCIENTIFIC_EVIDENCE_RESOLVER_V1` freezes the transitive replay order — load
  the exact persisted record, recompute the digest, validate schema and
  version, resolve every material reference, re-run the owner predicate, verify
  cross-record interval, provider, instrument, epoch and clock identity, and
  compare every surface field with the replay-derived field. Missing,
  substituted or digest-only evidence refuses. The liquidation hourly row
  therefore derives `feed_status`, `event_count` and notionals from evidence, so
  a correctly rehashed `OBSERVED_ZERO_EVENTS` surface row over an incomplete
  hour cannot enter a daily zero, and `LIQUIDATION_UTC_DAY_CENSUS_V1` repeats
  the same transitive replay for all 24 exact expected UTC hours.
- The schema now freezes
  `research.prospective_scientific_evidence_record` as the exact
  content-addressed authority for every material normalized evidence object.
  It persists canonical payload bytes, record kind and schema version; the
  typed evidence tables are query/index projections only. Surface CVD and
  market-cap observations carry explicit schema versions and are reconstructed
  in full during replay, so a correctly rehashed row with an invalid revision
  or ingestion timestamp is refused.
- Three new hash-bound child artifacts cover the CoinGecko request attempt,
  the Kraken Futures runtime metadata validation and the scientific evidence
  resolver. The parent mechanically enumerates and binds 25 child definitions;
  the count is derived rather than asserted, and no R4 child-count prose
  survives.
- The accepted percentile adapter is unchanged: a 730-day prior eligible
  window, at least 365 prior valid complete daily observations and midrank,
  with an incomplete day treated as missing and never as zero. The 21-hour CVD
  contiguity rule is unchanged and every hour is now independently replayable.
- Validation passed 220 focused tests, 3,800 selected source/feature/PIT/
  lifecycle/backtest/authority regressions and the complete 4,660-test Python
  3.12.14 suite with `RuntimeWarning` promoted to an error. Artifact
  regeneration, all 25 parent bindings, `compileall` and scoped
  `git diff --check` also pass.
- No persistent collector, migration, qualifying observation, real Stage-B
  aggregate or sufficiency minimum was created. BTC-019 and its sealed sample
  remain untouched. Classification is
  `PROSPECTIVE_INTEGRATION_CORPUS_READY_FOR_SIXTH_XHIGH_REVIEW`.

### POSTP1-001R5 frozen dependency order

```text
POSTP1-001R5 CORRECTED PROTOCOL 8915d991...fbfac7d7
  -> SIXTH INDEPENDENT EXACT-HASH XHIGH REVIEW (POSTP1-002R5)
  -> POSTP1-003 SUFFICIENCY GOVERNANCE
  -> INDEPENDENT XHIGH REVIEW OF THE EXACT SUFFICIENCY HASH
  -> POSTP1-004 COLLECTOR/SCHEMA IMPLEMENTATION
  -> INDEPENDENT POSTP1-004 IMPLEMENTATION REVIEW
  -> PROSPECTIVE COLLECTION
```

Collection remains unauthorized. POSTP1-003 may not begin until the sixth
independent review passes on this exact hash, POSTP1-004 stays transitively
blocked, BTC-019 does not reopen, and Epic T remains closed. This is the final
planned source-provenance correction pass; a further failure is a candidate for
`PROSPECTIVE_PROTOCOL_TERMINALLY_BLOCKED_BY_SOURCE_INTEGRITY` rather than
another correction microticket.

### POSTP1-002R5 — sixth independent exact-hash xHigh review

**Status:** `READY / NOT STARTED`
**Dependency:** POSTP1-001R5 implementation commit
`428356665dff0985cf8b1c379f6f18bf6cc5bac1`
**Review target:** exact protocol hash
`8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7`
**Review model:** independent GPT-5.6 Sol — Extra High (xHigh)

The review must independently reproduce the parent and all 25 mechanically
enumerated child hashes, verify all 25 parent bindings, replay the complete
CoinGecko, clock, stream/CVD, runtime-metadata and liquidation evidence graphs,
and rerun the P1-A through P1-D adversarial boundaries. It must also verify
zero Stage-B threshold/direction/hard-role/intent changes, retained failed
lineage, no sufficiency-minimum selection, no collection, and no BTC-019 sealed
access. PASS makes POSTP1-003 dependency-satisfied; review failure leaves
POSTP1-003, POSTP1-004 and collection blocked and must use one of the bounded
terminal/incomplete source-integrity classifications rather than silently
authoring another correction task.

## Next EPIC X tasks

| ticket | task | status |
| --- | --- | --- |
| POSTP1-002 | `FORMAL_XHIGH_REVIEW_PROSPECTIVE_INTEGRATION_CORPUS_V1` | COMPLETE / FAIL |
| POSTP1-001R | `CORRECT_AND_REFREEZE_PROSPECTIVE_INTEGRATION_CORPUS_V1` | COMPLETE / FAILED REPEAT REVIEW |
| POSTP1-002R | repeat independent xHigh review of `0d4f1437...f45a9e` | COMPLETE / FAIL |
| POSTP1-001R2 | `FREEZE_MISSING_PROSPECTIVE_INPUT_SEMANTICS_AND_REFREEZE_CORPUS_V1` | COMPLETE / FAILED THIRD REVIEW |
| POSTP1-002R2 | third independent xHigh review of `40e37067...c9862` | COMPLETE / FAIL |
| POSTP1-001R3 | `CORRECT_SOURCE_COVERAGE_AND_REFREEZE_CORPUS_V1` | COMPLETE / FAILED FOURTH REVIEW |
| POSTP1-002R3 | fourth independent xHigh review of `e60a9514...a7dca` | COMPLETE / FAIL |
| POSTP1-001R4 | `HARDEN_PROSPECTIVE_SOURCE_COMPLETENESS_AND_REFREEZE_CORPUS_V1` | COMPLETE / FAILED FIFTH REVIEW |
| POSTP1-002R4 | fifth independent xHigh review of `fd946a09...bedff` | COMPLETE / FAIL |
| POSTP1-001R5 | `MAKE_PROSPECTIVE_SOURCE_EVIDENCE_REPLAYABLE_AND_REFREEZE_CORPUS_V1` | COMPLETE / AWAITING SIXTH REVIEW |
| POSTP1-002R5 | sixth independent xHigh review of `8915d991...fbfac7d7` | READY; not started |
| POSTP1-003 | `PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1` | BLOCKED by POSTP1-002R5 exact-hash review PASS |
| POSTP1-004 | schema, collectors, CVD/market-cap/liquidation capture and decision snapshot implementation | BLOCKED by POSTP1-003 exact-hash independent review PASS |
