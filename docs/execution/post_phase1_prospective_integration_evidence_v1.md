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

**Status:** `COMPLETE / PASSED SIXTH INDEPENDENT xHIGH REVIEW`
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

The sixth independent review passed on this exact hash and made POSTP1-003
dependency-satisfied. POSTP1-003's later exact-hash review failed, so POSTP1-004
and collection remain blocked pending corrected sufficiency governance and its
review, followed by the POSTP1-004 implementation review. BTC-019 does not
reopen and Epic T remains closed.

### POSTP1-002R5 — sixth independent exact-hash xHigh review

**Status:** `COMPLETE / PASS`
**Dependency:** POSTP1-001R5 implementation commit
`428356665dff0985cf8b1c379f6f18bf6cc5bac1`
**Review target:** exact protocol hash
`8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7`
**Review model:** independent GPT-5.6 Sol — Extra High (xHigh)

The review independently reproduced the parent and all 25 mechanically
enumerated child hashes, verified all 25 parent bindings, replayed the complete
CoinGecko, clock, stream/CVD, runtime-metadata and liquidation evidence graphs,
and reran the P1-A through P1-D adversarial boundaries. It also verified zero
Stage-B threshold/direction/hard-role/intent changes, retained failed lineage,
no sufficiency-minimum selection, no collection, and no BTC-019 sealed access.
PASS makes POSTP1-003 dependency-satisfied; POSTP1-004 and collection remain
blocked by their later required reviews.

### POSTP1-002R5 review result

The sixth independent GPT-5.6 Sol xHigh review returned `PASS` /
`PROSPECTIVE_PROTOCOL_CERTIFIED_FOR_SUFFICIENCY_GOVERNANCE` for implementation
`428356665dff0985cf8b1c379f6f18bf6cc5bac1`, documentation handoff
`933f0bce363779d8b68a75895d157290e821240d`, and exact protocol hash
`8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7`.

Review fix `ab3b353e344465966da321af02b08f6fe28213f5` closed two uniquely
mechanical enforcement gaps without changing any frozen protocol semantics or
artifact hash:

- stream collector-health and epoch-establishment health must be PIT-valid,
  share the epoch's explicit monotonic domain and resolve inside the interval's
  clock evidence; clock/metadata Boolean schema fields now reject truthy
  non-Booleans;
- the CVD 21-hour and CoinGecko revision selectors must replay their persisted
  surface and complete transitive evidence graph through
  `SCIENTIFIC_EVIDENCE_RESOLVER_V1` before producing historical-owner inputs.

After the fix, deletion of any tested clock, epoch, liveness,
collector-health, metadata, completeness or source-event record refuses, as do
wrong-hour/provider/instrument/epoch/domain substitutions and rehashed
scientific surfaces. Exact CoinGecko bytes, request/date identity, the inclusive
45.000-second boundary, the 45.001-second refusal, append-only PIT revisions,
future-received event exclusion, the 24-hour liquidation census and the
incomplete-hour rehash attack all replay fail closed. Arbitrary non-UTF-8 bytes
round-trip through the tagged canonical content representation without
confusing the provider-byte digest with the canonical-record digest.

The review independently recomputed V3 `4232e886...bf71a`, certified V1
`8e6254e0...c7ffe7`, V4 `670ff12d...3f501`, V5 `95e43ee1...775a89`, the
prospective parent and all 25 children. All 25 children remain parent-bound and
all 25 semantic mutation probes moved both child and parent hashes. The five
failed predecessors remain explicitly non-authoritative and pre-data. Direct
comparison with `reference_composite_v2.V2_APPROVAL_GATES` found zero threshold,
direction, hard-role or metric-intent changes.

Validation passed 230 focused replayability tests, 2,352 selected
source/feature/PIT/lifecycle/paper/backtest/price-lineage/authority regressions,
and the complete 4,670-test Python 3.12.14 suite with `RuntimeWarning` promoted
to an error. Clean-directory artifact regeneration, hash-seed/CWD/fresh-process
reproduction and `compileall` pass. Scoped `git diff --check` passes; the
repository-wide command reports only the unrelated pre-existing trailing blank
line in `prompts/review_epic.md`, which this review did not modify.

No qualifying observation was collected, no persistent collection began, no
real Stage-B aggregate was evaluated, no sufficiency minimum was selected, and
the BTC-019 sealed sample was neither collected nor opened. PASS authorizes
only POSTP1-003 sufficiency governance; it does not authorize POSTP1-004 or
prospective collection.

## POSTP1-003 — `PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1`

**Status:** `COMPLETE / FAILED INDEPENDENT EXACT-HASH xHIGH REVIEW / REQUIRES PRE-DATA CORRECTION`
**Dependency:** POSTP1-002R5 PASS on certified corpus hash
`8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7`
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Review model:** independent xHigh review of the exact sufficiency-governance
hash
**Owner module:**
`btc_predictor/research/prospective_integration_evidence_sufficiency.py`
**Artifacts:**
`prospective_evidence/prospective_integration_evidence_sufficiency_governance_v1/`

### Scope and acceptance criteria

Freeze, before collection, the evidence-quantity rules and blind stopping point
for exactly the eight prospective Stage-B metrics. Threshold, direction, hard
role, intent, universe, numerator, denominator and exclusion semantics remain
owned by the certified corpus and immutable historical gates. A successful
implementation must bind the certified corpus hash, recover zero semantic gate
changes, select every minimum without observed outcomes, require complete slot
accounting, define one outcome-blind earliest cutoff and freeze the evaluation
corpus there. POSTP1-004, collection and BTC-019 remain unauthorized.

### POSTP1-003 implementation notes

Implementation commit `90a0252744f333e2168ad3904efbc1ec14c5693e` freezes
`PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1` at:

```text
3f51c4d9d8f14689b3f6c863e1731a6ef170b9764162b79bd56cc369af4ae2c7
```

- Eight mechanically enumerated semantic children are bound by the parent.
  Direct import from `reference_composite_v2.V2_APPROVAL_GATES` and the
  certified corpus produces zero threshold, direction, hard-role or
  metric-intent changes.
- The common finite-rate rule is the uncorrected two-sided 95% Wilson
  capability floor at `z = 1.959963984540054235631`. It derives minima of 381
  for `gap_through_stop_consensus_agreement_rate`, 73 for
  `isolated_venue_stop_suppression_rate`, 189 for
  `regime_classification_disagreement_rate`, and 381 for each of setup, action
  and eligibility disagreement. Every finite boundary is pinned at `n-1` and
  `n` through the repository Wilson owner.
- The inherited exact
  `cross_market_confirmed_stop_preservation_rate >= 1.0` boundary has no finite
  Wilson capability denominator: for every finite positive `n`,
  `WilsonLower(n,n) = n/(n+z^2) < 1`. The governance records that theorem
  instead of rounding it away and freezes the smallest positive denominator,
  1, under
  `EXACT_POINT_RATE_BOUNDARY_IDENTIFIABILITY_EXCEPTION_V1`. This is explicitly
  an estimator-definedness exception, not a confidence claim, and the inherited
  point-rate performance gate remains exactly `>= 1.0`.
- The non-binomial risk-size minimum is 20, the first sample size for which
  nearest-rank p95 selects rank 19 rather than the sample maximum and leaves one
  observed tail value above the selected order statistic. No distribution,
  interpolation or bootstrap rule is introduced.
- Coverage freezes 100% scheduled post-warmup slot accounting and zero
  unaccounted slots. There is no separate numerical evaluability/comparability
  floor: no frozen percentage applies to these universes, their exclusions are
  candidate-neutral, and each metric must independently reach its own minimum.
  The V3 structural-pair 0.50 floor stays scoped out. Calendar duration,
  distinct-day and distinct-week minima are `NONE`; Stage-C's 90-day live
  shadow is not imported. Day/week concentration remains a persisted
  diagnostic.
- `PROSPECTIVE_STAGE_B_SUFFICIENCY_MONITOR_V1` accepts only scheduler identity,
  time, certified universe membership and disposition fields. It has no target
  numerator, agreement bit, relative-difference value, aggregate or PASS/FAIL
  input. All eight metrics plus global accounting are required, the cutoff is
  the earliest qualifying `decision_time`, later evidence cannot move the
  frozen evaluation corpus, and an evaluated epoch cannot be extended after a
  FAIL to chase a PASS.
- Validation passed 39 focused synthetic tests, 997 prospective-corpus and
  reference-lineage tests, 831 selected feature/PIT/risk/stop/portfolio
  regressions, and the complete 4,709-test Python 3.12.14 suite with
  `RuntimeWarning` promoted to an error. Clean artifact regeneration,
  Decimal/hash-seed/CWD/fresh-process reproduction, all eight child mutation
  probes, `compileall` and scoped `git diff --check` pass.
- No prospective observation was collected, no persistent collector or schema
  was started, no real numerator or Stage-B result was inspected, and no
  BTC-019 sealed path was accessed. The classification is
  `PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1_READY_FOR_XHIGH_REVIEW`.
  POSTP1-004 and collection remain blocked pending independent review of this
  exact hash; BTC-019 remains terminal and Epic T remains closed.

### POSTP1-003 independent exact-hash review outcome

**Status:** `COMPLETE / FAIL`
**Result:** `FAIL — SUFFICIENCY GOVERNANCE INVALID`
**Classification:** `SUFFICIENCY_GOVERNANCE_REQUIRES_FIX`

The independent GPT-5.6 Sol xHigh review rejected exact hash
`3f51c4d9d8f14689b3f6c863e1731a6ef170b9764162b79bd56cc369af4ae2c7`.
The hash and arithmetic reproduce: all eight mechanically enumerated children
are parent-bound; certified corpus `8915d991...fbfac7d7` and all 25 of its
children reproduce; historical threshold, direction, hard-role and intent
changes are zero; the six finite Wilson boundaries are exactly
381/73/189/381/381/381; and nearest-rank p95 first becomes non-maximum at 20.
Those facts establish mathematical definedness, not scientific sufficiency.

The review found six release-blocking pre-data defects:

1. The exact-1.0 exception permits hard certification after one successful
   cross-market event. Its Wilson lower bound is only
   `0.2065493143772373879497053966633758`; estimator definedness does not support
   the inherited claim that a robust estimator preserves genuine shared tail
   moves. No finite Wilson solution at exactly 1.0 rules out that criterion; it
   does not logically select `n=1`. A separate outcome-independent
   evidence-strength rule must be governed without changing the 1.0 performance
   threshold.
2. The risk p95 rule at `n=20` proves only that rank 19 is not the sample
   maximum and leaves one observation above it. It freezes no precision,
   repeatability or distribution-free tail-evidence claim sufficient for the
   hard Stage-B certification statement. A stricter number cannot be invented
   in review; a corrected governance must predeclare the scientific criterion.
3. Complete accounting is not usable-coverage sufficiency. A synthetic prefix
   with 7,220 of 7,601 daily opportunities not evaluable (about 95% missing)
   still reached every minimum and certified. Candidate-neutral exclusions
   prevent outcome-selected labels but do not prevent source-health or regime
   selection bias. The corrected governance must freeze a defensible coverage
   claim or explicitly narrow what certification means.
4. Count-only stop-event evidence can be concentrated in one episode: a
   conforming synthetic corpus certified with the 381 gap events in 16 UTC days,
   73 isolated events in four days and the exact-boundary event in one day.
   Persisted concentration diagnostics do not make clustered observations
   independent Wilson evidence. A corrected rule must govern the evidence unit,
   dependence/episode handling or defensible spreading criterion without
   importing an arbitrary calendar duration.
5. The executable blind monitor trusts caller-supplied `universe_member` and
   `metric_disposition` surfaces. It accepts no authoritative evidence record,
   availability time or warmup proof from which to replay those fields, so a
   hostile projection can admit an ineligible observation, relabel an exclusion
   as evaluated, admit warmup evidence or backfill a post-cutoff revision. This
   contradicts the child contract's own replay requirement and the certified
   parent's append-only PIT boundary.
6. Cutoff immutability and same-epoch failure are not statefully enforceable.
   Re-running the function with a revised pre-cutoff disposition moved the
   accepted cutoff for the same epoch; the extension helper binds only two
   timestamps and a PASS/FAIL string, while arbitrary non-empty epoch IDs and
   arbitrary syntactically valid evaluation hashes are accepted. A failed epoch
   can therefore be presented as a new epoch without the required pre-outcome
   successor governance.

The result schema also needs to bind the certified corpus and temporal-policy
identity explicitly and the blind surface must not expose cross-track
disagreement through unrestricted reason codes. These are non-blocking beside
the six P1 findings but must be closed in the correction.

Validation passed 39 focused tests, 1,136 prospective-corpus/reference-lineage/
Wilson/authority tests, 869 selected feature/PIT/risk/stop/portfolio tests and
the complete 4,709-test Python 3.12.14 suite with `RuntimeWarning` promoted to
an error. Independent exact-rational boundary calculations, 8/8 and 25/25
artifact reproduction, low-coverage/concentration/authority/revision probes,
`compileall` and scoped `git diff --check` also pass. No prospective observation
was collected, no real Stage-B outcome was inspected, and BTC-019 and its sealed
sample remain untouched. These are semantic governance defects, not mechanical
review fixes, so the failed V1 hash is preserved and a corrected pre-data
governance definition with a new hash and independent review is required before
POSTP1-004.

## POSTP1-003R1 — `CORRECT_AND_REFREEZE_PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1`

**Status:** `COMPLETE / FAILED REPEAT INDEPENDENT EXACT-HASH xHIGH REVIEW / REQUIRES PRE-DATA CORRECTION`
**Dependency:** POSTP1-003 failed review on non-authoritative hash
`3f51c4d9d8f14689b3f6c863e1731a6ef170b9764162b79bd56cc369af4ae2c7`,
with certified parent corpus
`8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7`
remaining immutable
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Review model:** independent xHigh review of the exact corrected governance hash
**Owner module:**
`btc_predictor/research/prospective_integration_evidence_sufficiency.py`
**Artifacts:**
`prospective_evidence/prospective_integration_evidence_sufficiency_governance_v1/`

### Scope and acceptance criteria

Correct only POSTP1-003 review findings P1-01 through P1-06 and the associated
identity/reason-code P2 findings before collection. Preserve all eight
historical performance gates and every certified parent semantic. Separate the
historical performance denominator, raw sufficiency denominator and effective
dependence-unit count; impose outcome-independent common-rate, p95-tail,
coverage and natural evidence-unit requirements; make the blind monitor replay
content-addressed evidence rather than trust caller labels; and make the unique
initial epoch, first cutoff, frozen evidence manifest and terminal result
statefully enforceable. Retain the failed hash as non-authoritative pre-data
lineage. POSTP1-004 and collection require this exact corrected hash to pass
independent xHigh review first.

### POSTP1-003R1 implementation notes

Implementation commit `8540e80e58511818eaa2ce4d976470a405234a53` corrects and
refreezes `PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1` at:

```text
0ca7a2a8487e9c54b1b0f5ad07201ec39dfd20b328b5e09cb3b51b0de86c8242
```

- Failed predecessor `3f51c4d9...f4ae2c7` remains explicit with
  `authoritative = false`, failed review result, zero collected observations and
  `superseded_before_collection = true`. V1 is retained because that definition
  was never certified and no collection began.
- All eight gates are mechanically re-imported with zero threshold, direction,
  hard-role or metric-intent changes. The cross-market performance gate remains
  exactly `>= 1.0`; its separate common 95% / 1%-error evidence reference
  derives `n=381`, with 380 failing and 381 passing. The other six finite Wilson
  minima remain 381/73/189/381/381/381.
- Nearest-rank p95 remains unchanged. Exact rational binomial arithmetic derives
  93 as the first sample size with at least 95% probability of at least two
  population-tail hits: `n=92` gives
  `0.94786359706832297071275334555109578761521757634568497087748121876263472445581796`
  and `n=93` gives
  `0.95002420475738346021474735105078010632665901011874667478706307816526427641530659`.
- Each metric requires authoritative replay coverage `>= 0.99` by exact integer
  comparison, 100% scheduled-slot accounting and zero unaccounted slots.
  Legitimately replayed `NOT_IN_UNIVERSE` and `NOT_COMPARABLE` count as coverage;
  unavailable, invalid, late, unreplayable, reference-unavailable and warmup-
  incomplete evidence does not.
- Stop metrics count one unit per replayed control-position/active-stop lifecycle
  episode using the parent lifecycle hash chain and `active_stop_identity`.
  Daily decision metrics and risk sizing use the certified canonical UTC slot.
  Repeated rows do not inflate unit counts. There is no separate arbitrary
  calendar minimum and Stage-C's 90 days are not imported.
- The scientific API accepts only slot, content SHA and persisted epoch-
  authorization identity. It replays warmup, PIT, universe, disposition and
  dependence identity, exposes only coarse outcome-blind categories and refuses
  projection mismatches or outcome-sensitive categories.
- A real recomputing evaluation-contract SHA is required before the first
  qualifying observation. The stateful reference registry permits one
  `INITIAL_STAGE_B_EVALUATION_EPOCH`, persists the first cutoff and exact
  content-addressed evidence manifest, returns that immutable cutoff after later
  revisions, and makes PASS or FAIL terminal. Random epoch IDs and automatic
  successors are refused. POSTP1-004 must enforce this transactionally and
  persistently.
- Thirteen material children are mechanically enumerated and parent-bound.
  Required 381/93/0.99/dependence/blind-authority/epoch/cutoff mutation probes
  move their child and the top-level hash. The certified parent remains exactly
  `8915d991...fbfac7d7` with all 25 children unchanged.
- Validation passed 65 focused corrected-governance tests, 1,167 selected
  corpus/Wilson/PIT/warmup/reference/risk/stop/lifecycle regressions, and the
  complete 4,735-test Python 3.12.14 suite with `RuntimeWarning` promoted to an
  error. Artifact regeneration, hash-seed/CWD/fresh-process reproduction,
  `compileall` and scoped diff checks pass.
- No prospective observation was collected, no real Stage-B evaluation or
  numerator was inspected, BTC-019 stayed terminal and its sealed sample stayed
  untouched, and Epic T was not modified. Final classification is
  `PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1_READY_FOR_REPEAT_XHIGH_REVIEW`.
  POSTP1-004 and collection remain unauthorized pending independent review of
  this exact corrected hash.

### POSTP1-003R1 repeat independent exact-hash review outcome

**Status:** `COMPLETE / FAIL`
**Result:** `FAIL — CORRECTED SUFFICIENCY GOVERNANCE INVALID`
**Classification:** `SUFFICIENCY_GOVERNANCE_REQUIRES_FIX`

The independent GPT-5.6 Sol xHigh repeat review rejected corrected exact hash
`0ca7a2a8487e9c54b1b0f5ad07201ec39dfd20b328b5e09cb3b51b0de86c8242`.
The hash, all 13 mechanically enumerated child hashes and all parent bindings
reproduce. Certified corpus `8915d991...fbfac7d7` and all 25 children are
unchanged, the failed predecessor remains explicit non-authoritative pre-data
lineage, and direct comparison with `reference_composite_v2.V2_APPROVAL_GATES`
finds zero threshold, direction, hard-role or metric-intent changes.

The common-rate epsilon is mechanically and scientifically defensible at
`0.01`; the exact-1.0 gate remains a performance threshold of exactly `1.0`,
while 380 all-success units fail and 381 pass its separate common 95% Wilson
evidence-strength reference of `0.99`. The six finite Wilson minima remain
381/73/189/381/381/381. Exact rational p95-tail arithmetic gives
`P(n=92)=0.94786359706832297071275334555109578761521757634568497087748121876263472445581796`
and
`P(n=93)=0.95002420475738346021474735105078010632665901011874667478706307816526427641530659`;
93 distinct natural sizing opportunities is a defensible limited repeated-tail
exposure rule, not a population p95 confidence interval. Exact per-metric 0.99
coverage and complete prefix accounting also reject the synthetic 5%-coverage
case. These policies do not prove missing-at-random sampling or temporal
stationarity, but those limitations are accurately outside their narrow claims.

The review found three release-blocking defects and one associated P2 identity
defect:

1. **P1 — dependence-unit governance invalid.** The stop-unit hash includes
   both the root control-position episode and `active_stop_identity`, while the
   certified parent defines that stop identity as the active stop plus its
   transition/source identity. Three ordinary trailing-stop transitions in one
   still-open position therefore produce three distinct sufficiency units. The
   existing test explicitly expects this inflation. Hash distinctness does not
   make stop updates inside one economic position independent; 381 updates can
   satisfy a 381-unit rule without 381 independent position/risk episodes.
2. **P1 — blind evidence authority invalid.** `BlindEvidenceResolver` resolves
   a blind envelope and a newly authored
   `PROSPECTIVE_STAGE_B_BLIND_SOURCE_EVIDENCE_V1` summary, but that summary
   carries caller-populated warmup, PIT, universe, comparability and dependence
   facts and no transitive references to the certified decision, source,
   portfolio, stop or risk evidence that owns them. Changing a summary's
   `universe_member`, recomputing both content hashes and matching the declared
   projection is accepted. This violates the certified parent's rule that
   scientific surface records are not authorities.
3. **P1 — evaluation-cutoff governance invalid.** The public registry
   `freeze_cutoff` path verifies only the manifest-list digest. It does not
   verify the cutoff record hash, schema, required policy/epoch bindings,
   recomputed earliest counts or the cited evidence records. A two-field fake
   cutoff carrying an arbitrary `record_sha256` was accepted and a terminal
   PASS was then bound to that fake hash. Persisting a result also does not
   replay the frozen manifest, so later integrity invalidation of cited evidence
   is neither detected nor failed closed.
4. **P2 — evaluation-contract identity under-specified.** Epoch authorization
   verifies only that a supplied mapping's digest reproduces. An empty mapping
   plus its correct digest is accepted as an evaluation contract, leaving no
   candidate/control identity or required evaluation-contract schema behind the
   hash that the cutoff and terminal result bind.

These are scientific authority and state-contract defects, not uniquely
mechanical review fixes. Correcting the stop dependence unit or authoritative
blind graph changes hash-bound semantics, while correcting cutoff and
evaluation-contract validation must move their bound children. The failed R1
hash is therefore retained unchanged and non-authoritative. A bounded pre-data
successor governance correction with a new exact hash and another independent
review is required; no certified-parent semantic change has yet been shown
necessary.

Validation passed 65 focused R1 tests, 1,922 independently selected prospective-
corpus/Wilson/PIT/warmup/reference/risk/stop/lifecycle/portfolio regressions and
the complete 4,735-test Python 3.12.14 suite with `RuntimeWarning` promoted to an
error. Independent hash reconstruction reproduced 13/13 governance and 25/25
parent children; exact-rational arithmetic, clean-directory regeneration,
Decimal/hash-seed/CWD/fresh-process determinism, `compileall` and scoped diff
checks pass. Repository-wide `git diff --check` reports only the unrelated
pre-existing trailing blank line in `prompts/review_epic.md`, which this review
did not modify.

No prospective observation was collected, no persistent collection began, no
real Stage-B numerator or result was inspected, and BTC-019, its sealed sample
and Epic T remain untouched. POSTP1-004 and collection remain blocked.

## POSTP1-003R2 — `CLOSE_SUFFICIENCY_EVIDENCE_AUTHORITY_AND_EPOCH_ENFORCEMENT_V1`

**Status:** `COMPLETE / FAILED FINAL INDEPENDENT EXACT-HASH xHIGH REVIEW / NON-AUTHORITATIVE`
**Dependency:** POSTP1-003R1 failed repeat review on non-authoritative hash
`0ca7a2a8487e9c54b1b0f5ad07201ec39dfd20b328b5e09cb3b51b0de86c8242`,
with failed implementation `8540e80e58511818eaa2ce4d976470a405234a53` and
review documentation `1342ff9eca04d254bf17566dcc80b5796310af92`; certified parent corpus
`8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7`
remains immutable
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Review model:** independent xHigh review of the exact corrected governance hash
**Owner module:**
`btc_predictor/research/prospective_integration_evidence_sufficiency.py`
**Artifacts:**
`prospective_evidence/prospective_integration_evidence_sufficiency_governance_v1/`

### Scope and acceptance criteria

Apply only the bounded pre-data corrections required by POSTP1-003R1 findings:
count every stop metric at the root control-position lifecycle episode rather
than by active-stop revision; replace caller-authored blind conclusions with a
full transitive replay of certified-parent evidence; require a strict,
scientifically identified Stage-B evaluation contract before the initial epoch;
and derive, validate, freeze and terminally revalidate the earliest cutoff and
its exact evidence manifest. Hash-bind the blind source/replay schemas,
evaluation-contract schema and cutoff replay-validation semantics. Preserve the
certified parent, all historical performance gates, the already-defended
statistical minima and exact 0.99 coverage rule. Retain both failed predecessor
hashes as non-authoritative pre-data lineage. Do not collect observations,
authorize POSTP1-004, inspect a real Stage-B numerator, reopen BTC-019 or touch
Epic T.

Acceptance requires deterministic hostile tests proving that ordinary stop
moves cannot manufacture independent units; self-rehashed blind summaries and
cross-identity substitutions cannot override certified-parent replay; empty,
under-schema or mismatched evaluation contracts cannot authorize an epoch;
caller-supplied, fabricated, early or late cutoffs cannot be frozen; frozen
evidence deletion or substitution prevents a terminal result; PASS and FAIL are
both terminal; and later evidence cannot move the first valid cutoff. The
corrected exact hash must pass a final independent xHigh review before this
ticket is DONE or POSTP1-004 becomes dependency-satisfied.

### POSTP1-003R2 implementation notes

Implementation commit `d476a16e4d87656bac39b1a925004901a19b9374`
closes the bounded findings and refreezes
`PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1` at:

```text
0c0c0f96bc68afee0cbecc285546e0721e6fc621b09354af079adffd5863c64e
```

- Failed hashes `3f51c4d9...f4ae2c7` and `0ca7a2a8...e86c8242` remain
  explicit with `authoritative = false`, zero collected observations and
  `superseded_before_collection = true`. No failed definition was rewritten.
- Stop sufficiency identity is now one content-addressed root control-position
  lifecycle episode. The complete certified control state/action chain and
  current active-stop membership are replayed, but `active_stop_identity` is
  excluded from the dependence-unit hash. Stop revisions in one open position
  remain one unit; exit/re-entry creates a new root episode.
- The monitor accepts only slot, certified-parent manifest hash and persisted
  epoch-authorization hash. Strict content-addressed manifests transitively
  resolve warmup, PIT/source/quality, decision universe, comparability, paired
  risk outputs and complete stop lifecycle/classifier inputs. Coarse blind
  categories and dependence units are freshly derived; blind projections and
  scientific surface records are never authorities.
- The evaluation contract has an exact hash-bound schema containing candidate
  and control reference identities, certified corpus, sufficiency governance,
  parent Stage-B contract, creation time and its own hash. Empty, unknown-field,
  same-identity, cross-corpus, cross-governance and late contracts are refused.
- Cutoff derivation is a pure replay over identity-only manifest rows. The
  registry rejects caller-supplied cutoff/progress/manifest data, freezes only
  a fully recomputed earliest qualifying prefix, and revalidates the strict
  cutoff, manifest, evidence graph, epoch and evaluation contract before either
  terminal PASS or terminal FAIL. Deletion, substitution, fabricated records,
  early/late cutoffs, second results and epoch retries fail closed; later
  evidence cannot move the frozen cutoff.
- Eighteen material children are mechanically enumerated. New hash-bound
  children define blind-category mapping, the certified blind-parent manifest,
  blind replay derivation, evaluation-contract schema and cutoff replay
  validation. Every material child is top-bound; the certified parent remains
  exactly `8915d991...fbfac7d7` with all 25 children unchanged.
- Historical gate parity remains zero for threshold, direction, hard role and
  metric intent. The exact common-rate science remains epsilon `0.01`, evidence
  reference `0.99`, confidence `0.95`; raw/distinct minima remain
  `381/381/73/189/93/381/381/381`; and exact authoritative replay coverage
  remains `0.99`. The common-rate, p95-tail, coverage and statistical-derivation
  child bytes are unchanged from R1.
- Validation passed 95 focused corrected-governance tests, 1,661 selected
  corpus/Wilson/PIT/warmup/reference/risk/stop/lifecycle regressions, and the
  complete 4,765-test Python 3.12.14 suite with `RuntimeWarning` promoted to an
  error. Artifact restoration exactly reproduces 18/18 child bindings and the
  top hash; `compileall` and scoped diff checks pass.
- No prospective observation was collected, no real Stage-B evaluation or
  numerator was inspected, BTC-019 stayed terminal and sealed, Epic T was not
  modified, and POSTP1-004 remains unauthorized. The implementation
  classification is
  `PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1_READY_FOR_FINAL_XHIGH_REVIEW`.

### POSTP1-003R2 final independent exact-hash review outcome

**Status:** `COMPLETE / FAIL`
**Result:** `FAIL — BLIND PARENT REPLAY INVALID`
**Classification:** `SUFFICIENCY_GOVERNANCE_REQUIRES_FIX`

The final review found that governance-authored parent-input, warmup and metric
records still supplied scientific conclusions instead of replaying the actual
certified-parent graph. It also found that materially scientific executable
replay and cutoff-validation behavior was not bound into the governance hash,
and that candidate/control string identities were not canonically enforced.
Hash `0c0c0f96bc68afee0cbecc285546e0721e6fc621b09354af079adffd5863c64e`
is therefore retained as failed, non-authoritative pre-data lineage with no
prospective observations collected and `superseded_before_collection = true`.
POSTP1-004 and collection remain unauthorized.

## POSTP1-003R3 — `CLOSE_CERTIFIED_PARENT_REPLAY_AND_EXECUTABLE_SEMANTIC_BINDING_V1`

**Status:** `BLOCKED / CERTIFIED PARENT CHANGE REQUIRED`
**Dependency:** POSTP1-003R2 failed final review on non-authoritative hash
`0c0c0f96bc68afee0cbecc285546e0721e6fc621b09354af079adffd5863c64e`;
certified parent corpus
`8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7`
was audited unchanged
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Required classification:** `SUFFICIENCY_GOVERNANCE_REQUIRES_CERTIFIED_CORPUS_CHANGE`

### Parent-completeness audit and stopping-rule result

The mandatory pre-adapter audit established that genuine transitive replay
cannot be implemented from the immutable certified parent without inventing a
new governance authority:

- `prospective_decision_observation` persists
  `warmup_history_complete` as a Boolean, while no frozen content-addressed
  slot input-manifest schema enumerates the complete owner-specific history and
  transitive raw-record references from which every warmup predicate can be
  rerun. The generic `prospective_source_input_snapshot.payload` row and a
  derived record's singular `input_snapshot_sha256` do not define that closure
  or make omitted qualifying/adverse history detectable.
- `prospective_portfolio_state` binds only `prior_state_sha256`; it does not
  bind the content-addressed predecessor record or the transition/action record
  that produced the resulting state. `prospective_trade_action` binds its prior
  state but not the resulting state. Consequently the exact root opening
  transition and complete active-stop lifecycle membership cannot be uniquely
  traversed and validated from parent-bound references alone.
- The R2-only `CERTIFIED_PARENT_INPUT_EVIDENCE_V1` and related warmup/metric
  records fill these gaps with asserted `quality_state`, initialization and
  other conclusions. Rehashing or replacing those governance records is not a
  replay of certified evidence and cannot repair the missing parent closure.

The ticket's hard stopping rule therefore applies. No R3 governance artifact,
executable-semantic manifest or new governance hash was issued. The accepted
381/381/73/189/93/381/381/381 minima, exact 0.99 coverage rule, Wilson inputs,
stop dependence-unit policy and historical Stage-B gates remain unchanged.
All three failed governance hashes remain non-authoritative, superseded before
collection and associated with zero collected prospective observations. No
real Stage-B numerator or result was inspected, BTC-019 and its sealed sample
were untouched, Epic T was not modified, and POSTP1-004 and collection remain
unauthorized. A new certified-corpus authority decision is required; this
ticket does not propose POSTP1-003R4.

## POSTP1-001V2 — `DEFINE_AND_FREEZE_PROSPECTIVE_INTEGRATION_CORPUS_V2_REPLAY_CLOSURE`

**Status:** `IMPLEMENTATION COMPLETE / FAILED INDEPENDENT EXACT-HASH xHIGH REVIEW`
**Dependencies:** POSTP1-002R5 PASS on certified corpus hash
`8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7`, and the
POSTP1-003R3 parent-completeness audit result
`SUFFICIENCY_GOVERNANCE_REQUIRES_CERTIFIED_CORPUS_CHANGE`
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Review model:** independent xHigh review of the exact successor corpus hash
**Owner modules:** `btc_predictor/research/prospective_integration_corpus_v2.py`,
reusing `btc_predictor/research/prospective_integration_corpus.py` and
`btc_predictor/research/prospective_source_integrity.py` unchanged
**Artifacts:** `prospective_evidence/prospective_integration_corpus_v2/`

### Authority decision

`PROSPECTIVE_INTEGRATION_CORPUS_V1` remains immutable historical **certified**
lineage. It is not modified in place, its hash does not move, its 25 child
hashes do not move, and it is not called invalid for anything its six reviews
accepted. It is a new category — certified, authoritative when frozen, and
superseded before collection — not a failed predecessor, and the five genuinely
failed pre-data hashes above keep their own separate lineage.

V1's single limitation is narrow and named:

```text
REPLAY PROVENANCE INCOMPLETE FOR THE NEW SUFFICIENCY-AUTHORITY REQUIREMENT
```

`PROSPECTIVE_INTEGRATION_CORPUS_V2` is the pre-data successor intended to become
collection authority **after** independent certification. Until that review
passes, V1 is not marked a replaced collection authority; after it passes,
documentation may classify V1 as
`SUPERSEDED_PRE_COLLECTION_BY_REPLAY_COMPLETE_V2` while retaining every
historical certification fact.

The version increments despite the frozen `CHANGE_PROCEDURE` binding a successor
to a post-collection semantic change, because POSTP1-003R3 established that
genuine transitive replay needs a new certified-parent **authority**, not a
pre-data correction of the same one. Zero qualifying prospective observations
exist under V1, so no collection epoch is disturbed and no observation is
migrated or fabricated.

### Scope and acceptance criteria

V2 changes only the certified-parent evidence and provenance architecture
required for deterministic transitive replay. The following are unchanged and
re-verified against their own owners on every build: provider and source
identities, CoinGecko and Kraken acquisition semantics, clock integrity, stream
completeness, the CVD and liquidation definitions, the 33 `INITIAL_FEATURE_NAMES`
scientific definitions, decision cadences, the PIT rule, warmup scientific
predicates, regime/setup definitions, the stop-event taxonomy, portfolio
economic semantics, trade-action, trade-eligibility and risk-sizing semantics,
and every Stage-B metric definition, threshold, direction, hard role and intent.
`semantic_diff_v1_to_v2` recomputes all nine change families from the certified
parent's own gate authority, metric contracts, warmup rows and feature coverage
and refuses the build on any non-zero count. BTC-019 stays terminal, its sealed
sample stays uncollected and unopened, Epic T is not modified, and the frozen
V3, certified V1 validator, V4 and V5 hashes are bound and unchanged.

The acceptance criteria are replay closure, not description:

1. every owner-specific warmup result is regenerated from exact persisted
   history rather than a Boolean;
2. an omitted qualifying or adverse observation cannot hide inside a
   self-hashed manifest;
3. every resulting portfolio state proves its exact predecessor record and the
   transition that produced it;
4. the root opening transition and active-stop membership are traversal
   results, not governance surrogates;
5. all eight Stage-B universe, comparability and denominator facts are
   replayable from V2 parent evidence; and
6. no trading, source, metric, threshold, risk or stop-event science moves.

### POSTP1-001V2 implementation notes

Implementation commit `40993038ac81cca9f2a4c2f03b971b3bc99f82c3` freezes
`PROSPECTIVE_INTEGRATION_CORPUS_V2` at:

```text
488251df7bc1b49f801caa0dc28eb5224836574b154db9e4a70d4be670ec0b6d
```

- **21 material children**, mechanically enumerated from one artifact/builder
  registry. `inherited_v1_child_bindings` binds all 25 certified V1 children by
  hash: 14 reused unchanged, 9 extended by a new V2 child, 2 superseded for
  replay closure with V1 retained immutable.
- **`PROSPECTIVE_OWNER_HISTORY_MANIFEST_V2`** persists, per owner per slot, the
  owner identity and contract hash, the slot and decision time, the series
  identity and required cadence, the window semantics, the exact ordered
  qualifying *and adverse* observation record SHAs, the PIT selection semantics,
  and its own digest. A generic `input_snapshot_sha256` never established that
  closure, which is the audit's first finding.
- **Completeness is a second, independent derivation.** `expected_owner_evidence`
  recomputes the expected reference set from the evidence store alone and never
  reads the manifest it is checking, so an omitted qualifying observation, an
  omitted adverse one, a substituted record, a wrong date, cadence or source, or
  a future-available revision all fail the comparison and refuse.
- **The owner census is heterogeneous by construction.** All 33 frozen features
  land in exactly one of twelve owner classes, each class carrying its own
  frozen predicate shape and each row carrying its own owner-derived parameters,
  read from the owner modules on every build. No generic count rule replaces a
  scientific predicate.
- **Warmup is demoted.** `warmup_history_complete` leaves the V2 decision record
  entirely and survives only as `cached_projections.warmup_history_state`, a
  non-authoritative cache. Authoritative warmup is obtained by resolving each
  owner's history manifest, resolving every referenced record, running that
  owner's own evaluability predicate and combining them under the frozen
  decision-evaluability contract. A cached value that disagrees refuses in
  either direction.
- **`PROSPECTIVE_SLOT_EVIDENCE_MANIFEST_V2`** binds one immutable
  content-addressed commitment per scientific decision slot and carries
  references only; seven conclusion field names are refused by schema. The
  manifest is explicitly not sufficient authority: replay independently verifies
  existence, validation, identity, cadence, window, completeness, substitution
  and PIT before anything rests on it.
- **The portfolio graph is content-addressed and acyclic.** A transition binds
  its exact prior state record and its exact decision/action evidence and never
  names its result; a resulting state binds both its `prior_state_record_sha256`
  and its `producing_transition_record_sha256`. Identity therefore flows strictly
  backwards to one explicit `GENESIS` per track whose predecessor and producing
  transition are both null, and no later state may use a null for either.
- **The replay owner re-runs the existing semantics.** `replay_portfolio_state`
  restores the prior lifecycle through the authoritative public
  `restore_position_lifecycle`, applies each bound event through
  `apply_position_event`, applies each bound account operation through the
  `PaperAccount` owner's own methods, recomputes NAV by invoking
  `PaperAccount.nav`, and requires exact equality with the persisted state. No
  economic meaning is authored and no private helper is called.
- **Root lifecycle and active-stop membership are traversals.**
  `derive_root_opening_transition` walks the verified chain back to the `ENTER`
  that opened the current position; `derive_active_stop` returns the active stop,
  its installing transition and the advance count; and the active-stop identity
  is derived from the graph, so an asserted `active_stop_identity` establishes
  nothing. A stop-event record whose control state was stamped after the observed
  bar formed is refused.
- **The paired sizing opportunity is proved, not asserted.** A V2 risk record
  carries every input `INITIAL_POSITION_SIZE_V1` consumes — NAV and the risk
  fraction included, which the certified parent's typed projection omitted — so
  the owner is re-run rather than read back, and `trade_permitted` is a strict
  Boolean. `prove_paired_sizing_opportunity` requires exactly one record per
  reference role at one slot, distinct identities, distinct tracks, both
  permitted, both complete and both notionals strictly positive.
- **Closure is mechanical.** The metric matrix reports **8/8** Stage-B metrics
  replayable with their universe, comparability and denominator predicates; the
  feature matrix reports **33/33**. Both refuse the build below full coverage.
- **The replay architecture is itself hash-bound.** Eleven executable replay
  owners are frozen with their identity, contract hash, selection semantics,
  required evidence schemas and `REFUSE` failure semantics, so a scientifically
  material selection rule does not live only in code. A later
  executable-semantic manifest may additionally bind concrete runtime code.
- **Three boundaries are declared rather than hidden**: the ETF publication
  calendar's unowned `market_holidays` default, the canonical-bar derivation
  cutoff that makes a daily or weekly bar's very existence PIT evidence, and
  same-timestamp revision resolution, which only the ETF owner performs today.
- **Four certified-parent feature-owner labels do not resolve to a real symbol.**
  V2 records both the parent's label and the resolving symbol — which is the
  parent's own evaluability owner in every case, so the predicate measured does
  not move — and verifies the latter imports. The correction lives in a new V2
  child; the certified V1 child is untouched.
- **Numerical context is pinned.** None of the owners V2 invokes pins a Decimal
  context, so a persisted tranche quantity, average entry, available cash or
  position notional follows `getcontext().prec`. V2 runs every owner invocation
  inside the interpreter default those owners already run under, which moves no
  byte any existing caller produces and makes persisted V2 evidence invariant to
  the ambient context.
- **The acceptance demonstration is a construction.** A synthetic graph of 767
  records and 33 owner-history manifests derives every required blind fact from
  parent evidence alone, inventing no `quality_state`, warmup, universe or
  comparability Boolean, no control root SHA, no active-stop membership and no
  sizing-opportunity Boolean.

### POSTP1-001V2 frozen dependency order

```text
PROSPECTIVE_INTEGRATION_CORPUS_V2 frozen
  -> INDEPENDENT EXACT-HASH xHIGH REVIEW OF THE V2 HASH
  -> SUFFICIENCY GOVERNANCE REISSUED AGAINST THE V2 PARENT (POSTP1-003R3)
  -> INDEPENDENT EXACT-HASH REVIEW OF THAT GOVERNANCE
  -> POSTP1-004 IMPLEMENTATION
  -> INDEPENDENT REVIEW OF POSTP1-004
  -> PROSPECTIVE COLLECTION AUTHORIZED
```

No sufficiency-governance hash is issued by this ticket and all three failed
governance hashes remain non-authoritative. POSTP1-003R3 stays blocked until the
V2 review passes and must then bind the V2 parent, perform true owner-level
replay, bind executable semantics and enforce canonical candidate/control
identity, using the accepted 381 / 93 / 0.99 rules unchanged. POSTP1-004 and
collection remain unauthorized, BTC-019 does not reopen and Epic T remains
closed.

## POSTP1-002V2 — `INDEPENDENT_XHIGH_REVIEW_PROSPECTIVE_INTEGRATION_CORPUS_V2_REPLAY_CLOSURE`

**Status:** `COMPLETE / FAIL`
**Reviewed implementation:** `40993038ac81cca9f2a4c2f03b971b3bc99f82c3`
**Reviewed candidate:** `488251df7bc1b49f801caa0dc28eb5224836574b154db9e4a70d4be670ec0b6d`
**Review model:** GPT-5.6 Sol — Extra High (xHigh)
**Review result:** `FAIL — PROSPECTIVE INTEGRATION CORPUS V2 INVALID`
**Execution classification:** `PROSPECTIVE_CORPUS_V2_BLOCKED_BY_MISSING_EXISTING_OWNER_AUTHORITY`

### Exact-hash and lineage result

Independent regeneration reproduced the V2 hash above, all 21 mechanically
enumerated child definitions and their parent bindings. Mutating each child
moved both its child hash and the V2 top hash in 21/21 cases. Certified V1
reproduced unchanged at
`8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7`
with all 25 children and artifact restoration unchanged. V3, the certified V1
validator, V4 and V5 also retain their frozen hashes. No prospective evidence
was collected, no real Stage-B evaluation ran, BTC-019 sealed data was not
opened and Epic T was not modified.

### Blocking findings

1. `market_holidays` has no existing certified owner even though it changes the
   ETF publication window, expected observations, missingness and feature
   values. Persisting the rows selected under the empty-set default does not
   make that new scientific calendar choice inherited authority. The required
   fail-closed classification is therefore
   `PROSPECTIVE_CORPUS_V2_BLOCKED_BY_MISSING_EXISTING_OWNER_AUTHORITY`.
2. The owner-history selector does not inherit V1's latest-available revision
   rule. It selects the greatest integer revision, so two PIT-valid revisions
   whose revision-number and `available_at` order differ select a different
   record from the certified source owners.
3. Source quality is not transitively replayed. An asserted qualifying status
   with no underlying V1 acquisition/completeness evidence is accepted as
   evaluable; source-acquisition references in a slot are only resolved for
   existence.
4. The advertised 8/8 metric closure is declarative. No executable metric
   replay owner derives universe, comparability and denominator membership.
   Arbitrary regime/setup/action/eligibility outputs pass slot replay, stop
   classification is caller supplied rather than rerun, and a paired sizing
   opportunity can pass with no bound reference, portfolio or scientific input
   records.
5. The semantic-diff validator does not fail on all material owner drift. A
   synthetic mutation of the authoritative ETF five-day lookback to six is
   accepted while `feature_formula_changes` remains zero.

These are scientific-authority and replay-architecture defects, not uniquely
mechanical review fixes. The review therefore made no implementation change and
created no review-fix commit. V2 is not certified, V1 remains the immutable
certified pre-collection authority, POSTP1-003R3 remains blocked, and
POSTP1-004 and collection remain unauthorized.

## POSTP1-001V2A — `DEFINE_AND_FREEZE_ETF_PUBLICATION_CALENDAR_AUTHORITY_V1`

**Status:** `IMPLEMENTATION COMPLETE / FAILED INDEPENDENT EXACT-HASH xHIGH REVIEW`
**Dependency:** POSTP1-002V2 finding 1,
`PROSPECTIVE_CORPUS_V2_BLOCKED_BY_MISSING_EXISTING_OWNER_AUTHORITY`
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Review model:** independent xHigh review of the exact calendar-authority hash
**Owner module:** `btc_predictor/research/etf_publication_calendar.py`
**Artifacts:** `prospective_evidence/etf_publication_calendar_authority_v1/`

### Authority decision

`ETF_PUBLICATION_CALENDAR_AUTHORITY_V1` freezes exactly one previously unowned
scientific input: whether a U.S. equity trade date is an expected spot-Bitcoin-
ETF publication date. The canonical common-session venue set is the immutable
intersection of `NYSE_ARCA`, `NASDAQ` and `CBOE_BZX`; regular and early-close
sessions count as open, a full closure at any venue makes an otherwise resolved
date not expected, weekends are independently closed, and missing or unresolved
conflicting official evidence fails closed.

Only exact persisted snapshots from the frozen NYSE/NYSE Arca, Nasdaq Trader and
Cboe U.S. equities official source classes may support calendar rows. Every
snapshot binds its exact bytes and digest; the deterministic normalized schedule
binds both the raw-source and normalized-content digests; each venue/date row
replays from that schedule. Calendar revisions are append-only and selected at
decision time by latest PIT-valid `available_at`; same-time incompatible latest
states are unresolved and future notices do not leak backward.

The scientific adapter derives the existing `market_holidays` input as resolved
weekday common-session closures, then invokes the unchanged 5-day or 20-day ETF
flow owner. An expected date with a missing fund row remains
`ETF_FLOW_INPUT_MISSING`; a closed date is not expected; an unresolved date
makes the feature not evaluable and the low-level owner is not invoked. The
low-level compatibility argument remains unchanged. No flow formula, lookback,
normalization, fund-completeness, AUM, revision-ordering or source-quality
semantics are changed by this ticket.

### POSTP1-001V2A implementation notes

Implementation commit `596b407bd50d7754c4fcaf7b1681858582a02913` freezes
the authority below. (The abbreviated commit printed by Git is `596b407`.)

The frozen authority definition hash is:

```text
a1ceb66bc0f6b90066d3da123447ae6e7dd983047adf363790336bfb557db0b9
```

It binds **8 material children**, mechanically enumerated from the single
artifact/builder registry: the venue authority registry, venue-session record
schema, common-session rule, PIT/revision rule, official-source snapshot
contract, calendar extraction contract, ETF feature adapter contract and the
authority-completion semantic diff. Every child mutation moves the parent hash.

Non-persistent source verification on 2026-09-13 confirmed that the official
NYSE page covers NYSE Arca regular hours, full closures and scheduled early
closes; Nasdaq Trader's official U.S. equities calendar distinguishes closed
days from 1:00 p.m. early closes; and Cboe's official U.S. equities page covers
BZX regular hours, closures and early closes while its official update notices
support extraordinary revisions. No mutable web page or hard-coded 2026 sanity
date was made scientific authority.

The authority is frozen pre-data but is not certified. It produced no
prospective observation, did not change or rehash the failed V2 candidate
`488251df...0ec0b6d`, and did not resume POSTP1-003R3, authorize POSTP1-004 or
collection, reopen BTC-019, access its sealed data or modify Epic T. Only an
independent exact-hash xHigh PASS may authorize `POSTP1-001V2R1`; V2R1 itself
must then address all seven bounded POSTP1-002V2 findings together.

## POSTP1-002V2A — `INDEPENDENT_XHIGH_REVIEW_ETF_PUBLICATION_CALENDAR_AUTHORITY_V1`

**Status:** `COMPLETE / FAIL`
**Reviewed implementation:** `596b407bd50d7754c4fcaf7b1681858582a02913`
**Reviewed authority:** `a1ceb66bc0f6b90066d3da123447ae6e7dd983047adf363790336bfb557db0b9`
**Review model:** GPT-5.6 Sol — Extra High (xHigh)
**Review result:** `FAIL — ETF CALENDAR SOURCE DERIVATION INVALID`
**Execution classification:** `ETF_PUBLICATION_CALENDAR_AUTHORITY_REQUIRES_FIX`

### Exact-hash and source-scope result

Independent canonical-JSON regeneration reproduced the authority hash above.
The artifact directory contains exactly eight material JSON children; all 8/8
child hashes reproduce, all 8/8 equal the parent bindings, and mutating one
material field in each child moves both that child and the parent hash. The
frozen venue set is exactly `NYSE_ARCA`, `NASDAQ`, `CBOE_BZX`. Current official
NYSE, Nasdaq Trader and Cboe pages independently confirm that the named source
classes apply to NYSE Arca Equities, U.S. equities and Cboe BZX U.S. Equities,
respectively, and distinguish full closures from scheduled early closes.

The existing common-session, weekend, early-close, adapter and latest-valid-
`available_at` behavior passes its focused synthetic tests. The 5-day and
20-day lookbacks, ETF normalization, AUM, fund completeness, FlowAccel and ETF
flow revision semantics remain unchanged. The exact-byte source digest and
content-addressed record linkage also recompute. Those properties do not close
the source-derivation boundary below.

### Blocking findings

1. `normalized_schedule_record` accepts caller-authored `coverage_start`,
   `coverage_end`, `default_weekday_status` and `exceptions`. Neither it nor
   `_verify_schedule` parses the exact persisted official bytes or independently
   validates the normalized rows against them. With one unchanged source
   snapshot, hostile review successfully inserted a false closure and a false
   early close, omitted a source-stated holiday and early close so both became
   `OPEN_REGULAR`, submitted an empty exception map, and extended source-claimed
   2026 coverage through 2028. Every forged schedule and venue row rehashed and
   replayed successfully. The extraction child binds only raw and normalized
   digests; it freezes no supported source format/version, deterministic parser,
   coverage derivation or source-to-row validator. Provenance and self-hashing
   therefore substitute for extraction, and material source-derived semantics
   are absent from the authority hash tree.
2. Source/venue identity is caller-relabelable. The snapshot constructor accepts
   arbitrary nonempty bytes and document identity, then assigns the selected
   venue's registry identity solely from caller-supplied `venue_id`.
   `_verify_source_snapshot` recomputes bytes and checks that assigned registry
   string, but proves neither document origin nor product scope. Exact bytes
   labelled as an NYSE Arca document were accepted as a Nasdaq snapshot.
3. PIT availability is not scientifically established. Any caller-chosen
   `available_at <= acquired_at` is accepted without immutable evidence for an
   earlier availability instant, so a snapshot acquired in 2026 was accepted
   with `available_at` in 2020. `published_at` is persisted but has no frozen
   validation or ordering relationship and cannot repair that backdating.
4. Invalid future evidence leaks backward. `venue_session_status` marks any
   matching schema-invalid row as unresolved before applying its
   `available_at <= decision_time` eligibility test. Adding a content-addressed
   malformed row available after the decision changed an otherwise resolved
   earlier state to `UNRESOLVED`, contradicting the frozen no-future-leak rule.

These are scientific-authority decisions, not uniquely determined mechanical
review fixes. The review changed no implementation or authority artifact and
created no review-fix commit. The authority remains non-certified; the failed
V2 hash is unchanged; POSTP1-001V2R1, POSTP1-003R3, POSTP1-004 and prospective
collection remain blocked; BTC-019 and Epic T remain untouched.

## POSTP1-001V2A-R1 — `CORRECT_AND_REFREEZE_ETF_PUBLICATION_CALENDAR_SOURCE_DERIVATION_V1`

**Status:** `IMPLEMENTATION COMPLETE / AWAITING REPEAT INDEPENDENT EXACT-HASH xHIGH REVIEW`
**Dependency:** POSTP1-002V2A review failure and its four bounded P1 findings
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Review model:** independent xHigh review of the exact corrected calendar-authority hash
**Owner modules:** `btc_predictor/research/etf_publication_calendar.py`,
`btc_predictor/research/etf_calendar_semantics.py`
**Artifacts:** `prospective_evidence/etf_publication_calendar_authority_v1_r1/`
**Implementation commit:** `ab2bce5241e7372de3bbb70c938d08357054b615`

### Corrected authority decision

The failed authority `a1ceb66bc0f6b90066d3da123447ae6e7dd983047adf363790336bfb557db0b9`
remains preserved in its original directory as non-authoritative, non-certified,
unused pre-data lineage. The corrected authority remains versioned
`ETF_PUBLICATION_CALENDAR_AUTHORITY_V1` and is refrozen at:

```text
b81c1702c65e1e042b7a2f948216305618fd21fabe2e629edc46376882b357af
```

It binds **10 material children**, mechanically enumerated from one registry:
the official source-profile registry, HTTP acquisition schema, source-parser
registry, source-derived normalized-schedule contract, venue-session row
contract, PIT/revision contract, common-session contract, ETF adapter contract,
authority-completion semantic diff and executable-semantic manifest.

Scientific evidence now begins with a validated HTTPS GET acquisition envelope.
The request/final URL resolves exactly one frozen NYSE Arca, Nasdaq or Cboe BZX
profile, and venue/source authority derive from that resolution rather than a
caller field. The envelope binds exact response bytes and SHA-256, HTTP identity,
response receipt/acquisition time and parser/executable identity. Source-specific
parsers validate product scope and supported official format, then derive exact
annual coverage, closures, early closes and the source-supported regular-weekday
default. Caller-authored coverage and exception maps cannot enter the scientific
path. Schedule and venue-row validators rerun the acquisition/profile/parser
chain and require exact equality, so omissions, inventions, relabels and coverage
extensions refuse even after downstream rehashing.

Scientific `available_at` is structurally fixed to
`response_received_at == acquired_at`; `published_at` is optional informational
provenance and cannot own PIT eligibility. Strict append-only store admission
rejects unknown kinds, schema/digest/timestamp defects and invalid parent links.
Queries select exact venue/date evidence, filter `available_at <= decision_time`,
then resolve/replay the latest eligible evidence; a malformed or conflicting
future row therefore cannot affect an earlier result. Same-time incompatible
eligible schedules remain unresolved.

Exact compressed official response fixtures and acquisition provenance for all
three source formats are retained under
`btc_predictor/tests/fixtures/etf_calendar/`. Parser tests cover normal weekdays,
full closures, early closes, annual coverage, product scope, cross-venue relabels,
truncation, malformed dates and unknown labels. The executable semantic manifest
binds normalized AST identity for profile/acquisition handling, all three parsers,
normalization and venue replay, PIT selection, common reduction and the ETF
adapter. Runtime identity mismatch refuses scientific replay; isolated extractor,
early-close and PIT mutations move the executable child and corrected top hash.

The accepted venue set, intersection/weekend/full-closure/early-close/unresolved
rules and all ETF flow formula, 5/20-day lookback, normalization, AUM,
fund-completeness, FlowAccel and flow-revision semantics are unchanged. The
failed V2 remains exactly `488251df7bc1b49f801caa0dc28eb5224836574b154db9e4a70d4be670ec0b6d`.
No prospective observation was collected, no real Stage-B evaluation ran,
BTC-019 sealed data was untouched, and Epic T was unchanged.

### Authorization boundary

The implementation classification is
`ETF_PUBLICATION_CALENDAR_AUTHORITY_V1_READY_FOR_REPEAT_XHIGH_REVIEW`. It
authorizes only repeat independent exact-hash xHigh review. POSTP1-001V2R1,
POSTP1-003R3, POSTP1-004 and prospective collection remain blocked. Only a PASS
on the corrected exact hash may unlock POSTP1-001V2R1.

Validation used Python 3.12.14. The corrected exact-source/hostile suite passed
62 tests; the focused ETF/calendar/V1/V2 regression set passed 488 tests with 2
skips; and the full suite passed 4,973 tests with 2 skips under
`-W error::RuntimeWarning`. `python -m compileall btc_predictor` and scoped
`git diff --check` passed. The repository-wide diff check reports only the
pre-existing unrelated trailing blank line in `prompts/review_epic.md`, which
this ticket did not modify.

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
| POSTP1-001R5 | `MAKE_PROSPECTIVE_SOURCE_EVIDENCE_REPLAYABLE_AND_REFREEZE_CORPUS_V1` | COMPLETE / PASSED SIXTH REVIEW |
| POSTP1-002R5 | sixth independent xHigh review of `8915d991...fbfac7d7` | COMPLETE / PASS |
| POSTP1-003 | `PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1` | COMPLETE / FAILED INDEPENDENT EXACT-HASH xHIGH REVIEW |
| POSTP1-003R1 | corrected/refrozen sufficiency governance `0ca7a2a8...e86c8242` | COMPLETE / FAILED REPEAT INDEPENDENT EXACT-HASH xHIGH REVIEW |
| POSTP1-003R2 | bounded authority/epoch correction `0c0c0f96...5863c64e` | COMPLETE / FAILED FINAL INDEPENDENT EXACT-HASH xHIGH REVIEW |
| POSTP1-003R3 | certified-parent replay and executable-semantic binding audit | BLOCKED / AWAITING THE POSTP1-001V2 REVIEW PASS BEFORE IT MAY BE REISSUED AGAINST THE V2 PARENT |
| POSTP1-001V2 | `DEFINE_AND_FREEZE_PROSPECTIVE_INTEGRATION_CORPUS_V2_REPLAY_CLOSURE` | IMPLEMENTATION COMPLETE / FAILED INDEPENDENT EXACT-HASH xHIGH REVIEW |
| POSTP1-002V2 | independent exact-hash xHigh review of `488251df...0ec0b6d` | COMPLETE / FAIL — V2 INVALID / MISSING EXISTING OWNER AUTHORITY |
| POSTP1-001V2A | `DEFINE_AND_FREEZE_ETF_PUBLICATION_CALENDAR_AUTHORITY_V1` | IMPLEMENTATION COMPLETE / FAILED INDEPENDENT EXACT-HASH xHIGH REVIEW |
| POSTP1-002V2A | independent exact-hash xHigh review of `a1ceb66b...7db0b9` | COMPLETE / FAIL — ETF CALENDAR SOURCE DERIVATION INVALID |
| POSTP1-001V2A-R1 | source-derived correction/refreeze of `ETF_PUBLICATION_CALENDAR_AUTHORITY_V1` at `b81c1702...b357af` | IMPLEMENTATION COMPLETE / AWAITING REPEAT INDEPENDENT EXACT-HASH xHIGH REVIEW |
| POSTP1-001V2R1 | bounded correction of all seven POSTP1-002V2 findings against the certified calendar authority | BLOCKED pending POSTP1-001V2A exact-hash review PASS |
| POSTP1-004 | schema, collectors, CVD/market-cap/liquidation capture and decision snapshot implementation | BLOCKED pending the POSTP1-001V2 exact-hash review, reissued sufficiency governance against the V2 parent and its own review |
