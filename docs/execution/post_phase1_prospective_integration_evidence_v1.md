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

**Status:** `IMPLEMENTATION COMPLETE / FAILED REPEAT INDEPENDENT EXACT-HASH xHIGH REVIEW`
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

### Authorization boundary at implementation

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

## POSTP1-002V2A-R1 — `REPEAT_INDEPENDENT_XHIGH_REVIEW_ETF_PUBLICATION_CALENDAR_AUTHORITY_V1`

**Status:** `COMPLETE / FAIL`
**Reviewed implementation:** `ab2bce5241e7372de3bbb70c938d08357054b615`
**Reviewed authority:** `b81c1702c65e1e042b7a2f948216305618fd21fabe2e629edc46376882b357af`
**Review result:** `FAIL — ETF CALENDAR SOURCE ORIGIN AUTHORITY INVALID`
**Execution classification:** `ETF_PUBLICATION_CALENDAR_AUTHORITY_REQUIRES_FIX`

### Bounded blocking findings

The corrected parser-derived schedule, PIT ordering, common-session rule and ETF
adapter passed review. Three source-authority defects remained. First, the
scientific acquisition constructor still accepted caller-supplied bytes, HTTP
status, final URL, redirect chain, headers and timestamps, so an approved URL
could label arbitrary look-alike bytes as official evidence. Second, the annual
parsers flattened page-wide cells and accepted plausible prefixes or generic
minimum row counts rather than proving complete traversal of one supported
calendar table and every early-close statement. Third, host/path/query matching
normalized non-canonical aliases, permitted explicit ports and did not validate
every redirect transition exactly. The authority remained non-certified and
unused; no downstream work or collection was authorized.

## POSTP1-001V2A-R2 — `CLOSE_ETF_CALENDAR_TRUSTED_ORIGIN_AND_PARSER_COMPLETENESS_V1`

**Status:** `IMPLEMENTATION COMPLETE / AWAITING FINAL INDEPENDENT EXACT-HASH xHIGH REVIEW`
**Dependency:** POSTP1-002V2A-R1 failure and its three bounded P1 findings
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Review model:** final independent xHigh review of the exact corrected calendar-authority hash
**Owner modules:** `btc_predictor/research/etf_publication_calendar.py`,
`btc_predictor/research/etf_calendar_semantics.py`
**Artifacts:** `prospective_evidence/etf_publication_calendar_authority_v1_r2/`
**Implementation commits:** `fcfeb937c0990bc87559d580c38061848fe6c579`
(trusted collector, parsers, tests and refreeze),
`02528bd6dc6c7512d8b114751d4b9032e7396f92` (compressed-fixture provenance completion)
and `7668d9a93ea841ad7fd33679eb46358b74549731` (authority binding of exact
format-reference fixture provenance), plus
`38ee8e14e786d74c5894a51699cf13f39c2e178d` (named material-rule hash-movement tests)

### Final corrected authority decision

Both failed authorities remain byte-preserved, non-authoritative, non-certified,
unused pre-data lineage: `a1ceb66b...7db0b9` and `b81c1702...b357af`. The final
corrected authority remains `ETF_PUBLICATION_CALENDAR_AUTHORITY_V1` and is
refrozen at:

```text
0524334396e529afbd057db25721b92c3074dd10205dd08be0946e512f99c855
```

It binds **12 material children** from one mechanical registry. The trusted
collector now selects an exact canonical profile URL, creates a standard
certificate- and hostname-verifying SSL context, performs and reads the HTTPS
GET itself, validates each observed redirect against an exact transition
registry, samples receipt time after reading the response, and directly creates
the acquisition record. Its production API accepts only a source-profile ID and
trusted receipt clock; no caller bytes, HTTP metadata, transport, session or
response object enter that API. Trusted acquisitions carry
`TRUSTED_HTTPS_COLLECTOR_V1`; parser fixtures carry
`TEST_FIXTURE_NON_AUTHORITATIVE` and fail scientific-store admission. This is a
trusted-process HTTPS boundary, not an offline cryptographic proof for detached
bytes.

Source identity uses exact raw canonical URL equality. Explicit ports,
credentials, fragments, path aliases, query aliases and any non-frozen redirect
hop refuse. The three source parsers capture table, section, row and cell
boundaries; select exactly one supported annual calendar table; traverse every
body row; enforce exact headers and the complete ordered semantic row census of
the retained source format; reject duplicate, missing, malformed or unknown
rows; and bind coverage only to the demonstrated years. NYSE additionally
requires every frozen early-close statement class and completely parses its
source-stated dates. A new year or changed census is unsupported until a
prospectively reviewed parser/source-format version is added.

The normalized-AST identity binds request construction, TLS transport,
redirects, response reading, receipt timing, acquisition construction and every
parser-completeness owner. Store admission replays trusted provenance, exact
profile identity, record digest, receipt timestamps, source parser and product
scope. The accepted PIT equality and future filtering, same-time conflict rule,
venue set, weekend/early-close/common-session rules and all ETF formula,
lookback, normalization, AUM, fund-completeness and revision semantics remain
unchanged.

### Authorization boundary

Classification is
`ETF_PUBLICATION_CALENDAR_AUTHORITY_V1_READY_FOR_FINAL_XHIGH_REVIEW`. This is the
final planned calendar-authority correction and authorizes only final independent
exact-hash xHigh review. It does not authorize POSTP1-001V2R1,
POSTP1-003R3, POSTP1-004 or collection. No prospective observation was
collected, no real Stage-B evaluation ran, BTC-019 sealed data was untouched and
Epic T was unchanged.

Validation used Python 3.12.14. The final trusted-origin/parser-completeness
suite passed 112 tests. The focused ETF/PIT/V1/V2 regression set passed 463
tests with 2 skips. The full suite passed 5,022 tests with 2 skips under
`-W error::RuntimeWarning`. Artifact restore/regeneration and
`python -m compileall btc_predictor` passed. Repository-wide
`git diff --check` continues to report only the pre-existing unrelated trailing
blank line in `prompts/review_epic.md`, which this ticket did not modify.

## POSTP1-002V2A-R2 — `FINAL_XHIGH_REVIEW_ETF_PUBLICATION_CALENDAR_AUTHORITY_V1`

**Status:** `COMPLETE / FAIL`
**Reviewed implementation:** `fcfeb937c0990bc87559d580c38061848fe6c579`,
`02528bd6dc6c7512d8b114751d4b9032e7396f92`,
`7668d9a93ea841ad7fd33679eb46358b74549731`, and
`38ee8e14e786d74c5894a51699cf13f39c2e178d`
**Review HEAD:** `8bebcc7c3349e22859c43743b6182a5659724dbd`
**Reviewed authority:** `0524334396e529afbd057db25721b92c3074dd10205dd08be0946e512f99c855`
**Review model:** GPT-5.6 Sol — Extra High (xHigh)
**Review result:** `FAIL — ETF CALENDAR TRUSTED ORIGIN BOUNDARY INVALID`
**Execution classification:** `ETF_PUBLICATION_CALENDAR_AUTHORITY_BLOCKED_BY_TRUSTED_ACQUISITION_BOUNDARY`

### Exact-hash and preserved-science result

Independent canonical-JSON regeneration reproduced the authority hash above.
All 12/12 material child hashes reproduce and equal their parent bindings. The
failed `a1ceb66b...7db0b9` and `b81c1702...b357af` directories remain unchanged,
non-authoritative, non-certified and unused with zero observations. Certified V1
`8915d991...fbfac7d7` and its 25 children and failed V2
`488251df...0ec0b6d` and its 21 children also reproduce unchanged.

The collector itself constructs its exact request, owns a certificate- and
hostname-verifying HTTPS context, forbids HTTP downgrade and caller transport
parameters, observes every exact redirect transition, reads the response and
then timestamps receipt. Exact raw URL matching, complete structured parser
traversal, fixture bindings, source-derived schedule replay, PIT filtering,
same-time conflict handling, the common-session reducer and the ETF adapter
passed review. The venue set, weekend/early-close rules and all ETF, Stage-B,
risk, stop and threshold science are unchanged.

### Blocking finding

One P1 trusted-origin defect remains. `CalendarEvidenceStore.put` publicly
admits any self-hashed acquisition mapping for which `_verify_source_snapshot`
can recompute fields and parser output. A hostile review constructed a complete
Nasdaq acquisition mapping from parser-valid official-looking fixture bytes,
the exact canonical URL, all required trusted collector/TLS/executable identity
fields and equal valid timestamps, computed its record SHA independently, and
successfully inserted it without executing the network collector. Rewriting a
fixture into that shape succeeds for the same reason. The store constructor also
rehydrates records through this identical route, so no immutable evidence
distinguishes trusted creation from caller-authored replay input. There is no
collector-only durable append path, non-forgeable persistence envelope or
separately frozen ingestion boundary inaccessible to scientific callers.

The required correction is an explicit architecture/authority decision that
creates an enforceable trusted persistence boundary and separately defines
rehydration evidence. Adding or checking another caller-computable JSON field or
self-hash is insufficient. This is not a uniquely mechanical review fix, so the
review changed no implementation or frozen artifact and created no review-fix
commit. The authority is not certified; POSTP1-001V2R1, POSTP1-003R3,
POSTP1-004 and collection remain blocked; BTC-019 and Epic T remain untouched.

Validation used Python 3.12.14. The focused calendar suite passed 112 tests; an
expanded ETF/PIT/V1/V2 relevant set passed 575 tests with 2 skips; and the full
suite passed 5,023 tests with 2 skips under `-W error::RuntimeWarning`. The two
skips are V2 composite owner-class cases that inherit component missing-history
behavior and do not cover this calendar authority. Artifact restoration,
independent fixture/census, URL/redirect, 64-state common-reducer and seven named
hash-movement probes, and `python -m compileall btc_predictor` passed.
Repository-wide `git diff --check` reports only the pre-existing user-owned
trailing blank line in `prompts/review_epic.md`, which this review left untouched.

## POSTP1-001V2B — `DEFINE_AND_FREEZE_TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1`

**Status:** `IMPLEMENTATION COMPLETE / FAILED INDEPENDENT EXACT-HASH xHIGH REVIEW`
**Dependency:** POSTP1-002V2A-R2 failure,
`ETF_PUBLICATION_CALENDAR_AUTHORITY_BLOCKED_BY_TRUSTED_ACQUISITION_BOUNDARY`
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Review model:** independent xHigh review of the exact trusted-acquisition authority hash
**Owner modules:** `btc_predictor/research/trusted_acquisition.py`,
`btc_predictor/research/trusted_acquisition_persistence.py`, and the bounded
integration points in `btc_predictor/research/etf_publication_calendar.py`
**Artifacts:** `prospective_evidence/trusted_acquisition_persistence_authority_v1/`
**Implementation commit:** `201769231c32faa03f3f3e49c328d022047a1be3`

### Authority decision

`TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1` freezes exactly one architecture
decision: scientific acquisition creation is verified collector execution plus
possession of the collector-only Ed25519 private key plus collector-only durable
PostgreSQL append; rehydration is authoritative-table read plus offline envelope
verification against the frozen public key. A self-hash, provenance string,
copied executable identity, official-looking response, or in-memory insertion
cannot prove creation origin.

The collector completes exact source-profile selection, verified HTTPS,
endpoint/redirect/HTTP validation, receipt timestamping and complete parser/
product-scope validation before building and signing the canonical acquisition
payload. The domain-separated canonical signed message binds the payload digest,
envelope schema, trusted-acquisition authority and signing-key ID. The immutable
envelope binds the signed payload, payload digest, key ID, Ed25519 signature and
outer content hash. Strict schema, digest, authority, algorithm, key-registry and
signature failure all refuse.

V1 freezes one active production verification key and its SHA-256 fingerprint.
Its matching private key is not in the repository or artifacts, has no default
or fallback, is loaded only by the collector from an explicitly configured
owner-protected external secret file, and must match the frozen public registry.
Tests use a distinct injected test-only key and registry; test signatures fail
production verification.

The production origin store is
`research.etf_calendar_trusted_acquisitions`. Migration 0025 revokes public
table privileges, gives `btc_calendar_collector_writer` only SELECT/INSERT and
gives `btc_predictor_scientific_reader` only SELECT; UPDATE/DELETE are explicitly
revoked. The writer API verifies a complete envelope then executes one
idempotent PostgreSQL INSERT in the caller transaction. Corrections are new
signed rows. `CalendarEvidenceStore` remains only a replay/test cache and admits
source acquisitions solely by verified signed envelope.

### Implementation notes and verification boundary

The frozen authority definition hash is:

```text
c3619b7a72d2ee04247139f47130b995e8ef00514c6e2a736435ba4f2a223554
```

It binds **8 material children** from one mechanical registry: the production
public-key registry, canonical signed-message contract, payload/envelope schema,
collector creation and secret-provisioning contract, PostgreSQL persistence and
privilege contract, creation/rehydration/failure contract, threat/security
boundary and normalized-AST executable-semantic manifest. The manifest binds
the message/digest/signature owners, collector signing and creation, replay-store
admission, PostgreSQL append and database rehydration. `cryptography==50.0.1`
is pinned and a deterministic test-only compatibility vector is frozen.

Hostile tests construct parser-valid official-looking source mappings with all
trusted strings, the current semantic identity and recomputed content hashes;
unsigned admission refuses. Random and test-key production signatures refuse.
Changing response bytes/digest, URL, redirects, venue/profile, `available_at`,
collector semantic identity or parser identity while recomputing all ordinary
hashes refuses. Signature and key substitutions refuse. A legitimate signed
envelope reloads in a fresh process, reproduces payload identity and supports
calendar source replay.

Ed25519 proves possession of the trusted collector key for the exact payload.
Together with the frozen verified-HTTPS collector and exclusive key/persistence
privileges this establishes the project's origin boundary; it does not claim an
independent third-party cryptographic TLS transcript. Collector-host or private-
key compromise remains outside this boundary and requires collection stop plus
a new reviewed authority/key-registry version.

Classification is
`TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1_READY_FOR_XHIGH_REVIEW`.
This certifies nothing by itself. The required order remains: independent review
of this exact hash; only after PASS, one bounded calendar integration/refreeze;
then independent calendar closure review; then POSTP1-001V2R1. No observations
were collected and no Stage-B evaluation ran. Calendar certification, V2R1,
POSTP1-003R3, POSTP1-004 and collection remain blocked; BTC-019 and Epic T are
unchanged.

Validation used Python 3.12.14. The hostile cryptographic/persistence suite
passed 23 tests; the focused calendar/cryptography/migration suite passed 159;
the expanded calendar, PIT, artifact, V1 and failed-V2 regression set passed
640 tests with 2 inherited composite skips; and the full suite passed 5,046
tests with those same 2 skips under `-W error::RuntimeWarning`. Artifact
regeneration/restoration, the production-public-key match check,
`python -m compileall btc_predictor`, and scoped diff checking passed. The
repository-wide diff check continues to report only the pre-existing unrelated
trailing blank line in `prompts/review_epic.md`, which this ticket did not
modify.

## POSTP1-002V2B — `INDEPENDENT_XHIGH_REVIEW_TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1`

**Status:** `COMPLETE / FAIL`
**Reviewed implementation:** `201769231c32faa03f3f3e49c328d022047a1be3`
**Documentation handoff:** `128119d2501144c5b49663f4cceddd008a7d7529`
**Reviewed authority:** `c3619b7a72d2ee04247139f47130b995e8ef00514c6e2a736435ba4f2a223554`
**Review model:** GPT-5.6 Sol — Extra High (xHigh)
**Review result:** `FAIL — TRUST REGISTRY INJECTION INVALID`
**Execution classification:** `TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_REQUIRES_FIX`

### Exact-hash, key and preserved-science result

Independent canonical-JSON regeneration reproduced the authority hash. All
8/8 material child hashes reproduce and equal the bindings in the parent. The
single active Ed25519 production public key decodes to 32 bytes and its frozen
fingerprint reproduces. A scan of tracked and untracked non-ignored project
files plus marker searches across Git history found no recognizable production
private-key material. The production private key was not available to the
reviewer, so possession and deployment matching were not independently
demonstrated.

The domain-separated message and payload digest bind the intended public
identities, public-key-only and random-signature forgery refuse under an
unmodified production registry, and payload tampering cannot be rescued by
ordinary hash recomputation. The failed calendar authority, certified V1 and
failed V2 hashes reproduce unchanged. No calendar, parser, PIT,
common-session, ETF, Stage-B, risk, stop or threshold science changed. No
observation was collected and no real Stage-B evaluation ran.

### Blocking findings

Four independent P1 boundaries fail.

1. Production trust roots are caller-replaceable. `verify_envelope`,
   `CalendarEvidenceStore`, `PostgresTrustedAcquisitionAppender` and
   `rehydrate_verified_envelopes` all accept arbitrary registries. A test key
   plus injected registry successfully produced normalized scientific calendar
   evidence, rehydrated an unmarked envelope and reached a PostgreSQL INSERT.
   More strongly, `PRODUCTION_KEY_REGISTRY` is a mutable dictionary captured by
   the default arguments; replacing it in place makes the default production
   verifier and store accept the test key. The production path therefore does
   not have a fixed frozen trust root.
2. The production creation/durability result is capability-injectable and can
   precede commit. `collect_official_calendar` accepts any signer and appender;
   a test signer plus fake appender returning the expected hash reports success
   without persistence. The PostgreSQL appender executes inside a caller-owned
   transaction and returns the envelope hash without commit or durable
   confirmation. A real PostgreSQL transaction contained the returned row and
   then rolled back to zero durable rows after reported success.
3. Executable binding is incomplete and is not enforced by production paths.
   Canonical serialization, public-key decoding and external private-key
   loading are not direct owners in the frozen executable manifest. Mutating
   public-key decoding or external key loading does not move the top authority
   on regeneration; a semantics-preserving source mutation of canonical
   serialization also does not move it. Although a verifier-body mutation moves
   the regenerated hash, production verification never compares runtime
   identity with the frozen artifact: a hostile permissive verifier admitted an
   invalid signature under the old artifact.
4. Fresh PostgreSQL deployment is not closed. Migration 0025 hard-codes two
   roles but neither repository migrations nor deployment documentation
   provision them. A disposable PostgreSQL 17.9 database failed migration at
   the GRANT because the roles did not exist. When the reviewer manually
   created isolated no-login roles, actual ACL probes did enforce collector
   SELECT/INSERT-only, reader SELECT-only, no role memberships, no schema
   CREATE and no PUBLIC table privileges. The table owner was the
   infrastructure superuser; the required non-owner/non-superuser application
   credential assumption is not documented.

Two additional P2 contract defects were reproduced. Strict Base64 verification
accepts an alternate non-canonical pad-bit encoding of the same 64-byte
signature, and Boolean `true` is accepted as envelope `schema_version = 1`.
The external-key loader refuses missing paths, directories, permissive modes,
RSA keys and wrong/test Ed25519 keys, but checks mode bits without checking
`st_uid` and no deployment authority documents the effective-UID assumption.

These are authority and deployment decisions, not uniquely mechanical review
fixes. The review therefore changed no implementation or frozen artifact and
created no review-fix commit. The trusted-persistence authority is not
certified; calendar integration/refreeze, V2R1, POSTP1-003R3, POSTP1-004 and
collection remain blocked. BTC-019 and Epic T remain untouched.

Validation used Python 3.12.14 with `cryptography 50.0.1`. The focused existing
suite passed 159 tests and the full suite passed 5,046 tests with 2 inherited
composite skips under `-W error::RuntimeWarning`. Independent hostile probes
covered registry substitution, fake capability injection, rollback durability,
fresh migration and actual role ACLs, strict encodings, owner checks, artifact
regeneration, child mutation and runtime semantic mutation. `python -m
compileall btc_predictor` passed. Repository-wide `git diff --check` reports
only the pre-existing user-owned trailing blank line in
`prompts/review_epic.md`, which this review left untouched.

## POSTP1-001V2B-R1 — `CLOSE_TRUSTED_ACQUISITION_PRODUCTION_BOUNDARIES_V1`

**Status:** `IMPLEMENTATION COMPLETE / FAILED REPEAT INDEPENDENT EXACT-HASH xHIGH REVIEW`
**Dependency:** POSTP1-002V2B failure,
`TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_REQUIRES_FIX`
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Review model:** repeat independent xHigh review of the exact corrected authority hash
**Artifacts:** `prospective_evidence/trusted_acquisition_persistence_authority_v1_r1/`
**Implementation commits:** `97927f2702aa524f1551b6f1b0c8f76d61efad12`,
final key-loader/refreeze hardening `f6240a3d2044311e4124fdad06ffcacafdb47eba`

### Bounded correction and frozen result

The failed `c3619b7a...223554` directory remains immutable, non-authoritative,
uncertified, unused, and superseded before any observation. R1 preserves the
Ed25519 algorithm, production key ID, public-key fingerprint and domain
separator, and refreezes `TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1` at:

```text
240985bf042bc6b9910e39f6c5e170dc22a0385d93ef2f17fecc21c0adee7bd0
```

Nine mechanically enumerated material children bind the immutable production
key authority; canonical signed-envelope encoding; production signing and
POSIX single-descriptor private-key loading; fixed-key verification and
rehydration; internally owned production collection; commit-confirmed
PostgreSQL persistence; deterministic role/bootstrap privileges; creation
versus replay; the threat boundary; and the normalized-AST runtime semantic
closure.

Production verification, `CalendarEvidenceStore`, persistence, rehydration and
collection accept no caller registry, alternate key, signer, appender or
connection. Test keys are confined to explicitly non-authoritative helpers and
fail every production admission path. The public registry is an immutable
mapping proxy over an unexposed frozen key. Authoritative persistence verifies
the production signature, owns INSERT and COMMIT, opens a distinct connection,
reconstructs and verifies the exact envelope, cross-checks denormalized
projections and returns only after equality. Commit or confirmation ambiguity
fails as `TRUSTED_ACQUISITION_COMMIT_UNCONFIRMED`; conflicts succeed only when
the already-persisted envelope is identical.

Every production boundary attests material runtime identity against the
persisted executable manifest, its parent binding and the frozen top identity.
Schema version is exact integer `1`; signature and public-key Base64 strictly
decode and canonically re-encode. The key loader requires POSIX, opens once with
required `O_NOFOLLOW`, validates a regular owner-only file owned by
`geteuid()`, and derives the frozen public key. Migration 0025 provisions
idempotent NOLOGIN, non-privileged group roles before GRANT, refuses unsafe
existing roles, revokes schema CREATE, and documents infrastructure ownership.

No calendar source/parser, PIT, common-session, ETF, Stage-B, risk, stop or
threshold science changed. No observation was collected and no Stage-B
evaluation ran. The failed calendar authority and failed V2 remain unchanged.
Calendar integration/refreeze, V2R1, POSTP1-003R3, POSTP1-004 and collection
remain blocked. Classification is
`TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1_READY_FOR_REPEAT_XHIGH_REVIEW`.

Focused correction validation passed 35 tests. The combined migration,
calendar, V1/V2 integrity, governance and trust regression set passed 412 tests
with 2 inherited composite skips using Python 3.12.14 and
`cryptography==50.0.1`. Artifact regeneration/restoration and runtime
attestation passed. Local PostgreSQL was not running and no database URL was
configured, so actual fresh-cluster ACL and committed-row visibility evidence
is deferred to repeat review; deterministic SQL and transaction fixtures pass.
Full-suite validation, compileall and diff checks are recorded in the final
implementation handoff: 5,058 tests passed with 2 inherited composite skips
under `-W error::RuntimeWarning`; compileall, artifact restoration, preserved-
hash checks and the scoped diff check passed. The repository-wide diff check
reports only the pre-existing user-owned trailing blank line in
`prompts/review_epic.md`, which this ticket left untouched.

## POSTP1-002V2B-R1 — `REPEAT_XHIGH_REVIEW_CORRECTED_TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1`

**Status:** `COMPLETE / FAIL`
**Reviewed implementation:** `97927f2702aa524f1551b6f1b0c8f76d61efad12`,
`f6240a3d2044311e4124fdad06ffcacafdb47eba`
**Reviewed HEAD:** `ed96eee973b1185f5fc9c50f47264575e9aa150d`
**Reviewed authority:** `240985bf042bc6b9910e39f6c5e170dc22a0385d93ef2f17fecc21c0adee7bd0`
**Review model:** GPT-5.6 Sol — Extra High (xHigh)
**Review result:** `FAIL — PRODUCTION VERIFICATION AUTHORITY INVALID`
**Execution classification:** `TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_REQUIRES_FIX`

Independent canonical-JSON regeneration reproduced the corrected parent and all
9/9 material child hashes; every child equals its parent binding. The Ed25519
production public-key fingerprint reproduced as
`8540303bf79b540bac83ef4dbf7315007c8ab7840fe017ee0b748177063443b9`.
The immutable supported registry API, fixed production signatures, strict schema
and Base64, single-descriptor POSIX key loading, sealed store, owned commit,
independent exact-envelope readback, projection checks, deterministic role SQL,
and preserved scientific lineage passed their focused checks.

Two P1 boundaries remain open. First, runtime attestation compares normalized
function ASTs with the persisted executable manifest but never compares the
effective `_PRODUCTION_VERIFICATION_KEY` or the other production-critical
runtime values with the parent-bound signing-key and signed-message contracts.
An isolated replacement of that effective key leaves attestation passing and
makes `verify_production_envelope` accept an envelope from the replacement key.
Second, production persistence opens `BTC_PREDICTOR_DATABASE_URL` and begins the
write without validating the connected identity's collector-writer membership,
non-owner status, or non-superuser status. It can therefore claim the frozen ACL
boundary while operating through an infrastructure-authority credential.

No PostgreSQL URL was configured and the local server did not respond, so fresh
migration, live role/ACL, and durable-visibility validation were not run:
`POSTGRES_RUNTIME_VALIDATION_ENVIRONMENT_UNAVAILABLE`. This absence does not
prevent the present fail verdict because both blocking defects reproduce from
the production code, but live PostgreSQL validation remains required after
correction before certification. The focused calendar/migration/trust suite
passed 171 tests. The full suite passed 5,058 tests with two inherited V2
composite-owner skips under `-W error::RuntimeWarning` using Python 3.12.14 and
`cryptography 50.0.1`; those skips do not exercise this authority. Compileall
passed. Repository-wide `git diff --check` reports only the pre-existing
user-owned trailing blank line in `prompts/review_epic.md`, which remained
untouched. No authority artifacts or implementation were changed and there is
no review-fix commit. Calendar integration/refreeze, V2R1, POSTP1-003R3,
POSTP1-004 and prospective collection remain blocked; BTC-019 and Epic T remain
untouched.

## POSTP1-001V2B-R2 — `CLOSE_TRUSTED_ACQUISITION_RUNTIME_MATERIAL_AND_DATABASE_IDENTITY_V1`

**Status:** `IMPLEMENTATION COMPLETE / FAILED FINAL INDEPENDENT EXACT-HASH xHIGH REVIEW`
**Dependency:** POSTP1-002V2B-R1 failure,
`TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_REQUIRES_FIX`
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Review model:** final independent xHigh review of the exact corrected authority hash
**Artifacts:** `prospective_evidence/trusted_acquisition_persistence_authority_v1_r2/`
**Implementation commit:** `c1edd5686516bae0634a561bd69c251359c36d98`
**Determinism regression commit:** `180ad8c1f14b165eedae60c32bf3270066ac8930`

### Final bounded correction and frozen result

The failed `240985bf...e7bd0` R1 directory remains immutable,
non-authoritative, uncertified, unused, and superseded before any observation.
R2 preserves Ed25519, key ID
`BTC_ETF_CALENDAR_COLLECTOR_ED25519_V1`, public-key fingerprint
`8540303b...3443b9`, and domain separator
`BTC_PREDICTOR_TRUSTED_ACQUISITION_ENVELOPE_V1` exactly. It refreezes the final
pre-data candidate at:

```text
bd55a3c0043c636f9e60db54e8f0d9fc72effd4e795b4518cad518608702c4fc
```

The nine-child mechanical census now binds two final corrections. First, every
production boundary uses one composed assertion requiring both the normalized-
AST executable identity and exact effective material values. Expected values
are read only from persisted signing-key and signed-message children after
their child digests, parent digest, child bindings, and exact frozen parent hash
verify. The live constants, effective `_PRODUCTION_VERIFICATION_KEY`, registry
keys/values and count must equal those artifacts exactly. Replacement of the
effective key with another valid Ed25519 key, registry replacement, or drift in
authority, envelope, domain, algorithm, key ID, key bytes, fingerprint,
authority version or status refuses before production evidence can verify.
Artifact resolution is package/repository-relative and independent of cwd.

Second, authoritative INSERT and independent confirmation each query their
actual PostgreSQL connection. The fixed NOLOGIN collector group must retain all
six non-privileged role attributes and no parent-role membership. `session_user`
or `current_user` must be its member; both must be non-superusers and non-owners
of the connected database, `research` schema and trusted table. Effective
`current_user` must have table SELECT/INSERT and schema USAGE, and must not have
UPDATE, DELETE or schema CREATE. Failure is distinct as
`TRUSTED_ACQUISITION_DATABASE_IDENTITY_INVALID` and occurs before INSERT. The
same configured collector login is intentionally used for confirmation, whose
independent connection is revalidated before SELECT.

### Verification evidence and safety

The hostile cryptographic/persistence suite passes 73 tests. A disposable
PostgreSQL 17 server passed a fresh complete migration chain through 0025 with
no role pre-creation, a safe-role idempotence migration, both group roles across
LOGIN/SUPERUSER/CREATEDB/CREATEROLE/REPLICATION/BYPASSRLS/foreign-membership
refusals, exact collector/reader/PUBLIC ACL checks, and real connected-identity
checks for normal collector, reader, unrelated, database owner, table owner,
schema owner, superuser, extra UPDATE, extra DELETE and schema CREATE logins.
Real commit plus independent readback, exact retry idempotence, conflicting
uniqueness, constraint failure and post-commit confirmation failure also pass
through the deterministic non-production signing boundary. Disposable
databases and roles were removed after validation.

The focused calendar/migration/trust regression set passes 209 tests with the
opt-in live test skipped. The final-tree full Python 3.12 suite passes 5,096
tests with three skips under `-W error::RuntimeWarning`; the additional third
skip is that same opt-in PostgreSQL test already exercised separately above.

The artifact regenerates byte-identically across input ordering, two
`PYTHONHASHSEED` values, alternate cwd, fresh processes and fresh artifact
directories. V1 `8915d991...fbfac7d7`, failed V2
`488251df...0ec0b6d`, failed calendar `05243343...f99c855`, and both failed
trusted-persistence directories remain unchanged. No calendar/parser/PIT,
common-session, ETF, Stage-B, risk, stop or threshold semantics changed. No
observation was collected and no Stage-B evaluation ran. The authority is not
certified; calendar integration/refreeze, V2R1, POSTP1-003R3, POSTP1-004 and
collection remain blocked. Classification is
`TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1_READY_FOR_FINAL_XHIGH_REVIEW`.

## POSTP1-002V2B-R2 — `FINAL_XHIGH_REVIEW_TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1`

**Status:** `COMPLETE / FAIL`
**Reviewed implementation:** `c1edd5686516bae0634a561bd69c251359c36d98`
**Determinism regression:** `180ad8c1f14b165eedae60c32bf3270066ac8930`
**Reviewed HEAD:** `8827aea0e3a1255c8a4ee9090392cb3848dfdde7`
**Documentation handoff:** `7be253e1e62353e085c80e38b889ba1e98e1ce13`
**Reviewed authority:** `bd55a3c0043c636f9e60db54e8f0d9fc72effd4e795b4518cad518608702c4fc`
**Review model:** GPT-5.6 Sol — Extra High (xHigh)
**Review result:** `FAIL — DATABASE IDENTITY AUTHORITY INVALID`
**Execution classification:** `TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_REQUIRES_FIX`

Independent canonical-JSON regeneration reproduced the R2 parent and all 9/9
material child hashes; all 9/9 children equal their parent bindings. The
production signing key and protocol values are loaded from independently
persisted, digest-verified, exact-parent-bound children, and replacement key,
registry and protocol values refuse. The real disposable PostgreSQL 17 test
passed independently, including fresh and safe-role migrations, all 14 unsafe
role cases, ACL and connected-identity matrices, commit/readback, transaction
and confirmation failures, idempotence, conflicts and cleanup.

One P1 boundary remains open. The executable manifest hashes the AST of the
database identity functions, but it does not bind the effective module-level
`COLLECTOR_ROLE` value (or the associated effective database authority
identifiers) as frozen runtime material. The material-value assertion covers
only signing-key and signed-message values. In an isolated regression,
replacing `COLLECTOR_ROLE` with `attacker_controlled_safe_group` left
`assert_frozen_production_authority()` passing, and the actual identity snapshot
then queried membership in that replacement role. A connection authorized by
an alternate safe group can therefore satisfy the production identity check
without authorization through the frozen `btc_calendar_collector_writer`
group. The correction must parent-bind the effective database authority values
and refuse such replacement before identity validation or INSERT. No automatic
R3 is created by this review.

The stale nonexistent implementation and determinism SHAs in the R2 handoff
were mechanically corrected to the actual commits above. This documentation-
only provenance repair did not move the scientific authority hash. The hostile
persistence/cryptographic suite passed 73 tests; the focused calendar,
migration and trust set passed 209 tests with the explicitly opt-in PostgreSQL
test skipped; that test separately passed against PostgreSQL 17; and the full
suite passed 5,096 tests with three explained skips under Python 3.12.14,
`cryptography 50.0.1` and `-W error::RuntimeWarning`. Compileall passed. The
authority remains uncertified; calendar integration/refreeze, V2R1,
POSTP1-003R3, POSTP1-004 and prospective collection remain blocked. BTC-019 and
Epic T remain untouched.

## POSTP1-001V2B-R3 — `BIND_TRUSTED_ACQUISITION_DATABASE_AUTHORITY_RUNTIME_IDENTIFIERS_V1`

**Status:** `DONE / PASSED FINAL INDEPENDENT EXACT-HASH xHIGH CLOSURE REVIEW`
**Dependency:** POSTP1-002V2B-R2 failure,
`TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_REQUIRES_FIX`
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Review model:** final independent xHigh closure review of the exact corrected authority hash
**Artifacts:** `prospective_evidence/trusted_acquisition_persistence_authority_v1_r3/`
**Implementation commit:** `c9c7771be532e5efbec1b79c776807d6ae3d0fa9`

### Final micro-correction and frozen result

The failed R2 authority `bd55a3c0...02c4fc` remains immutable,
non-authoritative, uncertified, unused, and superseded before any observation.
R3 preserves all accepted cryptographic, PostgreSQL identity, ACL, transaction,
commit/readback, projection and production-isolation behavior and refreezes the
nine-child authority at:

```text
02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772
```

The existing parent-bound PostgreSQL persistence child now freezes the exact
runtime collector role, authoritative schema, qualified table, SQLAlchemy table
schema/name/fullname, and deployment database-URL environment-key name. The URL
secret/value remains external and is not bound. The live material snapshot
compares these identifiers together with the accepted cryptographic/protocol
material after exact parent, child digest and parent-binding verification. The
identity query's short table name derives from the attested SQLAlchemy table
object instead of an independent literal. Runtime replacement of the role,
schema, qualified table, table object, or environment-key name refuses before
database use; write and independent confirmation recheck frozen material.

Deterministic regressions cover each database contract field, runtime scalar
and table-object replacement, child/top-hash movement, non-execution of the
identity query on central-attestation failure, and regeneration across child
ordering, hash seeds, cwd, processes and output directories. Disposable
PostgreSQL validation includes an independently safe alternate NOLOGIN group
and a login authorized only through it; replacing the runtime collector role
refuses on frozen material before opening a connection. The complete accepted
R2 migration, unsafe-role, ACL, identity, durability, failure, idempotence,
conflict and cleanup matrix remains covered.

Validation used Python 3.12.14 and `cryptography==50.0.1`. The focused hostile
cryptographic/persistence suite passed 91 tests; the broader calendar,
migration, trusted-persistence and V1/V2 integrity set passed 603 tests with
three explained skips; the opt-in disposable PostgreSQL 17 test separately
passed; and the full suite passed 5,114 tests with those same three skips under
`-W error::RuntimeWarning`. Artifact restoration, multi-process/hash-seed/cwd/
fresh-directory determinism, preserved-lineage checks, compileall and scoped
diff checking passed.

No calendar source/parser/PIT, common-session, ETF, Stage-B, risk, stop or
threshold semantics changed. No observation was collected and no real Stage-B
evaluation ran. The authority is not certified; calendar integration/refreeze,
V2R1, POSTP1-003R3, POSTP1-004 and collection remain blocked. Classification is
`TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1_READY_FOR_FINAL_CLOSURE_XHIGH_REVIEW`.
No POSTP1-001V2B-R4 may be created.

## POSTP1-002V2B-R3 — `FINAL_CLOSURE_XHIGH_REVIEW_TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1`

**Status:** `COMPLETE / PASS`
**Reviewed implementation:** `c9c7771be532e5efbec1b79c776807d6ae3d0fa9`
**Documentation handoff reviewed:** `2a1761408812daffabb73cc19ab093ab3589350f`
**Review closure commit:** `3522c89ad0807be942198b82e5d71248042e221a`
**Reviewed authority:** `02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772`
**Review model:** GPT-5.6 Sol — Extra High (xHigh)
**Review result:** `PASS`
**Execution classification:** `TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_CERTIFIED_FOR_CALENDAR_INTEGRATION`

Independent canonical-JSON regeneration reproduced the exact R3 parent and all
9/9 mechanically enumerated material children; all 9/9 child digests reproduce
and equal their parent bindings. The persisted R3 parent independently retains
the exact three failed predecessors `c3619b7a...223554`,
`240985bf...e7bd0`, and `bd55a3c0...02c4fc` as non-authoritative,
non-certified, zero-observation candidates superseded before use. Those
directories, the failed ETF calendar authority `05243343...f99c855`, certified
V1 `8915d991...fbfac7d7`, and failed V2 `488251df...0ec0b6d` are unchanged.

The parent-bound PostgreSQL child freezes the effective collector role, schema,
qualified table, SQLAlchemy table schema/name/fullname, and database-URL
environment-key name. Expected values come only through persisted exact-parent,
child-digest and parent-child-binding verification. Independent runtime
substitution of each scalar or table-object identity refuses at the composed
executable/material authority assertion before database identity evaluation or
connection use. Both write and independent confirmation recheck frozen material;
the actual identity query derives its short name from the attested table object.
Representative role, schema, table, table-object, membership, ownership,
required/forbidden privilege and configuration-key mutations move both the
owning child hash and top authority hash.

The preserved key/protocol, production-API isolation, strict encoding,
private-key file, durability, ACL, projection and executable-semantic boundaries
all pass. Disposable PostgreSQL 17.9 independently passed the alternate-safe-
group exact-authority refusal, fresh/idempotent migrations, unsafe-role, ACL,
connected-identity, commit/readback, transaction and confirmation failure,
idempotence, conflict and cleanup cases; cleanup probes found no leftover test
databases or roles.

The focused persistence suite passed 91 tests. The broader calendar, migration,
trusted-persistence and V1/V2 set passed 603 tests with three explained skips:
two composite cases inherit component behavior and the PostgreSQL case is
explicitly opt-in and was run separately. The full Python 3.12.14 suite passed
5,114 tests with the same three skips under `-W error::RuntimeWarning` using
`cryptography==50.0.1`; compileall and the reviewed-range diff check passed. The
repository-wide diff check reports only the pre-existing user-owned trailing
blank line in `prompts/review_epic.md`, which this review left untouched.

No finding exists and no review-fix commit was created. No calendar, PIT,
common-session, ETF, Stage-B, risk, stop or threshold science changed; no
prospective observation was collected and no real Stage-B evaluation ran.
`TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1` is closed absent a concrete later
integration defect. This PASS authorizes only bounded ETF-calendar
integration/refreeze against the exact certified hash. V2R1, POSTP1-003R3,
POSTP1-004 and prospective collection remain blocked; BTC-019 and Epic T remain
untouched.

## POSTP1-001V2A-I1 — `INTEGRATE_CERTIFIED_TRUSTED_PERSISTENCE_INTO_ETF_CALENDAR_AUTHORITY_V1`

**Status:** `IMPLEMENTATION COMPLETE / AWAITING INDEPENDENT EXACT-HASH xHIGH INTEGRATION CLOSURE REVIEW`
**Dependency:** POSTP1-002V2B-R3 PASS at certified trusted-persistence authority
`02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772`
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Required review:** POSTP1-002V2A-I1, independent exact-hash xHigh integration closure review
**Artifacts:** `prospective_evidence/etf_publication_calendar_authority_v1_i1/`
**Implementation commit:** `c040d2027abe8a7adb64be64a6450b6434bc6543`

### Integrated frozen result

The three failed calendar candidates `a1ceb66b...7db0b9`,
`b81c1702...b357af`, and `05243343...f99c855` remain immutable,
non-authoritative, non-certified, zero-observation candidates superseded before
use. The integrated successor preserves all accepted source profiles, exact
URLs, TLS and redirect policy, parser format censuses, annual coverage,
early-close, PIT, common-session and ETF feature semantics and refreezes the
13-child authority at:

```text
b499c6a4d1a8a6c25c6b108279831f26508742de97bdbcd57c7bee58e584e076
```

The new material `trusted_acquisition_persistence_dependency` child binds the
exact certified scientific dependency hash, required certification status,
production signed-envelope admission, rehydration/replay handoff and refusal
semantics. It explicitly makes unsigned/self-hashed snapshots, provenance
strings and non-production envelopes non-authoritative. Ed25519 keys,
PostgreSQL identities and privileges, private-key loading and transaction
durability remain delegated to the certified trusted-persistence authority and
are not duplicated by the calendar.

The existing production admission chain remains
`CalendarEvidenceStore.put -> verify_production_envelope ->
assert_frozen_production_authority`; the calendar dependency assertion also
verifies the persisted calendar parent/child binding and exact certified
runtime owner identity. Dependency mutation moves both the owning child and
top hash. Runtime trusted-authority replacement refuses before a signed
acquisition can become calendar evidence. Test-only envelopes remain usable
only through the explicitly non-authoritative replay boundary; fresh-process
replay requires no signing private key.

Focused calendar and trusted-persistence integration tests pass (209 tests).
The broader calendar, migration, trusted-persistence, ETF and V1/V2 integrity
set passes 625 tests with three explained skips. Deterministic
regressions cover child-order changes, multiple hash seeds, alternate cwd,
fresh processes and output directories, exact dependency mutation, calendar
and runtime dependency mismatch, direct unsigned/self-hashed refusal,
non-production-envelope refusal, and source-to-schedule-to-venue replay. The
full suite passes 5,120 tests with the same three skips; compileall and scoped
diff checks pass under Python 3.12.14. The
repository-wide diff check continues to report only the pre-existing
user-owned trailing blank line in `prompts/review_epic.md`, which this ticket
left untouched.

No prospective observation was collected and no real Stage-B evaluation ran.
This implementation does not certify the calendar authority and authorizes
only POSTP1-002V2A-I1. POSTP1-001V2R1, POSTP1-003R3, POSTP1-004, collection,
BTC-019 and Epic T remain blocked or untouched as applicable. Classification
is `ETF_PUBLICATION_CALENDAR_AUTHORITY_V1_READY_FOR_FINAL_INTEGRATION_XHIGH_REVIEW`.

## POSTP1-002V2A-I1 — `FINAL_INTEGRATION_XHIGH_REVIEW_ETF_PUBLICATION_CALENDAR_AUTHORITY_V1`

**Status:** `COMPLETE / FAIL`
**Reviewed implementation:** `c040d2027abe8a7adb64be64a6450b6434bc6543`
**Documentation handoff reviewed:** `bd103553a891db70eb648372e556bc21338bd3b4`
**Reviewed authority:** `b499c6a4d1a8a6c25c6b108279831f26508742de97bdbcd57c7bee58e584e076`
**Review model:** GPT-5.6 Sol — Extra High (xHigh)
**Review result:** `FAIL — CALENDAR DEPENDENCY CALL-SITE CLOSURE INVALID`
**Execution classification:** `ETF_PUBLICATION_CALENDAR_AUTHORITY_REQUIRES_FIX`

Independent canonical-JSON regeneration reproduced the exact parent and all
13/13 mechanically enumerated material children; every child digest reproduces
and equals its parent binding. The certified trusted-persistence authority
`02f96203...1a12772` independently reproduces with all 9/9 children and remains
closed and unchanged. The calendar dependency child contains the required exact
authority identity, certification status, signed-envelope requirement, replay
handoff and failure semantics. Each requested dependency-field mutation moves
both the child and parent hashes. Eleven of the twelve shared R2 children are
identical; only the integration-aware executable manifest moved, and the new
dependency child was added. Failed calendar lineage, certified V1 and failed V2
reproduce unchanged.

One P1 integration defect blocks certification. The standalone
`assert_trusted_persistence_dependency()` correctly rejects calendar parent,
dependency child, expected dependency version/hash, live dependency identity
and central frozen-authority mismatches, but no authoritative admission path
calls it. `CalendarEvidenceStore.put()` calls only
`verify_production_envelope()`. Consequently, when that verifier successfully
validates evidence under the installed persistence authority, calendar runtime
expected-hash/version replacement, persisted calendar-parent replacement, or
persisted dependency-child replacement is not inspected and the evidence is
admitted. A hypothetical later otherwise-valid persistence authority would be
accepted without first detecting that it differs from the exact dependency
frozen by this calendar. The executable manifest hashes both functions but does
not make the missing call edge true. The required correction is mechanical:
every authoritative calendar acquisition/replay admission must execute the
exact calendar dependency assertion before source evidence becomes scientific
calendar evidence, with regressions for every mismatch class. Any correction
changes the integration executable manifest and parent hash and therefore needs
a new independent exact-hash review; this review did not alter or refreeze the
candidate.

All preserved source-profile, parser/census, PIT, common-session and ETF-science
children are hash-identical to R2, and their regressions pass. Unsigned,
self-hashed and non-production evidence remains refused; test-only replay stays
explicitly non-authoritative. The focused calendar/trusted-persistence suite
passed 209 tests. The independently reconstructed broader calendar, migration,
trusted-persistence, ETF and V1/V2 set passed 619 tests with three explained
skips: two V2 composites inherit component behavior and the disposable
PostgreSQL test is explicitly opt-in. The full suite passed 5,120 tests with
the same three skips under Python 3.12.14 and `-W error::RuntimeWarning`;
compileall passed. Repository-wide `git diff --check` reports only the
pre-existing user-owned trailing blank line in `prompts/review_epic.md`, which
this review left untouched.

No prospective observation was collected and no real Stage-B evaluation ran.
The calendar remains uncertified. POSTP1-001V2R1, POSTP1-003R3, POSTP1-004 and
collection remain blocked; BTC-019 and Epic T remain untouched. The certified
trusted-persistence authority is not reopened because the defect is solely in
the calendar's admission call-site composition.

## POSTP1-001V2A-I1-R1 — `CLOSE_ETF_CALENDAR_EXACT_DEPENDENCY_CALL_SITE_V1`

**Status:** `IMPLEMENTATION COMPLETE / AWAITING INDEPENDENT EXACT-HASH xHIGH CALL-SITE CLOSURE REVIEW`
**Dependency:** POSTP1-002V2A-I1 failure,
`ETF_PUBLICATION_CALENDAR_AUTHORITY_REQUIRES_FIX`
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Required review:** independent exact-hash xHigh call-site closure review
**Artifacts:** `prospective_evidence/etf_publication_calendar_authority_v1_i1_r1/`
**Implementation commit:** `8a2b41480eebd7aff31a2f087d8bf5a41360c3bc`

### Bounded correction and frozen result

The failed I1 authority `b499c6a4...e584e076` remains immutable,
non-authoritative, non-certified, unused, and superseded before any prospective
observation. The corrected successor preserves the exact certified
trusted-persistence dependency `02f96203...1a12772` and refreezes the 13-child
calendar authority at:

```text
901f572e03781030906cd6fe72a73ec5804f9ffbdefe6a8a944c067f7fd9853f
```

An explicit dependency-guard composition layer now executes
`assert_trusted_persistence_dependency()` before effective entry to
`CalendarEvidenceStore.put`, `get`, `records`, `envelopes`, and
`collect_official_calendar`. Admission therefore checks the exact calendar
parent, dependency child and binding, expected dependency version/hash,
effective dependency identity and certified central production authority
before envelope verification or any store mutation. Existing admitted records
cannot be returned or scientifically replayed after a dependency mismatch, and
production collection refuses before HTTPS, private-key loading, signing or
persistence. The explicitly non-authoritative test-only collector remains
outside this production guard.

The composition layer preserves the already-certified trusted-persistence
runtime identity: its artifacts and implementation are unchanged, and its
central frozen production assertion still reproduces exactly. The calendar's
integration-aware executable manifest binds the assertion, guard, all five
guard installations, authoritative boundary owners and envelope/source
handoff. Removing any one installation in isolation moves both the executable
manifest and calendar parent.

All twelve shared scientific children are byte-identical to failed I1,
including source profiles, HTTPS/TLS/redirect contract, acquisition schema,
parser registry and census, normalized schedule, venue session, PIT,
common-session, ETF adapter, semantic diff, and the exact trusted-persistence
dependency. Only the executable integration manifest and parent moved. Failed
calendar lineage, certified V1 and failed V2 reproduce unchanged.

Deterministic hostile regressions cover expected dependency hash/version,
calendar parent, rehashed persisted dependency-child and effective persistence
identity mismatches; every admission refuses with zero mutation. A populated
store refuses `get`, `records`, venue status, calendar-window and scientific ETF
replay after mismatch. Production collection proves HTTPS, signer and appender
are not invoked. Unsigned, self-hashed/provenance-only and non-production
evidence remains refused, while the exact production envelope is admissible
only when the calendar dependency passes. Child-order reversal, multiple hash
seeds, alternate cwd, fresh process and fresh output directory reproduce the
exact parent and artifacts.

Validation used Python 3.12.14 and `cryptography==50.0.1`. The focused
calendar/trusted-persistence suite passed 222 tests. The broader calendar,
migration, trusted-persistence, ETF and V1/V2 integrity set passed 632 tests
with three explained skips: two V2 composites inherit component behavior and
the disposable PostgreSQL test is explicitly opt-in. The full suite passed
5,133 tests with the same three skips under `-W error::RuntimeWarning`;
compileall, artifact restoration, central trusted-persistence reproduction and
scoped diff checking passed. Repository-wide `git diff --check` reports only
the pre-existing user-owned trailing blank line in `prompts/review_epic.md`,
which this ticket left untouched. PostgreSQL certification was not rerun because
the certified implementation and boundary are unchanged.

No prospective observation was collected and no real Stage-B evaluation ran.
The calendar remains uncertified pending review. POSTP1-001V2R1,
POSTP1-003R3, POSTP1-004 and collection remain blocked; BTC-019 and Epic T
remain untouched. Classification is
`ETF_PUBLICATION_CALENDAR_AUTHORITY_V1_READY_FOR_FINAL_CALL_SITE_CLOSURE_XHIGH_REVIEW`.

## POSTP1-002V2A-I1-R1 — `FINAL_CALL_SITE_CLOSURE_XHIGH_REVIEW_ETF_PUBLICATION_CALENDAR_AUTHORITY_V1`

**Status:** `COMPLETE / FAIL`
**Reviewed implementation:** `8a2b41480eebd7aff31a2f087d8bf5a41360c3bc`
**Documentation handoff reviewed:** `e7e3fad131a25569f0fabe7bda10dd28ac551c91`
**Reviewed authority:** `901f572e03781030906cd6fe72a73ec5804f9ffbdefe6a8a944c067f7fd9853f`
**Review model:** GPT-5.6 Sol — Extra High (xHigh)
**Review result:** `FAIL — CALL-SITE GUARD BYPASS INVALID`
**Execution classification:** `ETF_PUBLICATION_CALENDAR_AUTHORITY_REQUIRES_ARCHITECTURE_DECISION`

Independent canonical-JSON regeneration reproduced the exact parent and all
13/13 mechanically enumerated material children; every child digest reproduces
and equals its parent binding. The certified trusted-persistence authority
`02f96203...1a12772` independently reproduces and remains closed and unchanged.
All twelve scientific children shared with failed I1 are byte-identical; only
the executable integration manifest and calendar parent moved. Failed calendar
lineage, certified V1 and failed V2 reproduce unchanged. Normal guarded store
admission/read/replay and production collection refuse every tested exact-
dependency mismatch before mutation, return or external side effects.

One P1 composition defect blocks certification. `_exact_dependency_guard()`
uses `functools.wraps`, which exposes each unguarded owner through `__wrapped__`.
With the calendar dependency deliberately mismatched, direct original `get`,
`records`, and `envelopes` return an already-populated scientific store; direct
original `put` admits an otherwise verified envelope; and direct original
collection proceeds to production private-key loading. Rebinding any one of the
five effective boundaries to its exposed original leaves both the trusted-
persistence executable hash and calendar parent hash unchanged. Frozen runtime
attestation therefore passes while original read boundaries remain usable.
Removing one installation at runtime has the same undetected behavior. Calling
the installer again only nests another wrapper and increases exposed-wrapper
depth; it does not close the original path.

The source manifest binds the guard and installation source text but does not
attest effective callable identity or the material assertion-to-owner call edge.
Consequently, the normal call sites are closed but authoritative behavior
remains reachable without `assert_trusted_persistence_dependency()`. This is
the review's requested hard-failure condition. No implementation, frozen
artifact, trusted-persistence code or scientific semantics were changed, and no
review-fix commit was created. A further correction requires an explicit
architecture decision; this review does not automatically create another
calendar ticket.

The focused suite passed 222 tests with the opt-in disposable PostgreSQL test
skipped. The broader calendar, migration, trusted-persistence, ETF and V1/V2
set passed 632 tests with three explained skips. The full Python 3.12.14 suite
passed 5,133 tests with the same three skips under
`-W error::RuntimeWarning`; the 13 post-commit authority cases passed,
compileall and reviewed-range diff checks passed. Repository-wide
`git diff --check` continues to report only the pre-existing user-owned trailing
blank line in `prompts/review_epic.md`, which this review left untouched.

No prospective observation was collected and no real Stage-B evaluation ran.
The calendar remains uncertified. POSTP1-001V2R1, POSTP1-003R3, POSTP1-004 and
collection remain blocked; BTC-019 and Epic T remain untouched. The certified
trusted-persistence authority is not reopened.

## POSTP1-001V2A-AD1 — `DEFINE_ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1`

**Status:** `IMPLEMENTATION COMPLETE / FAILED INDEPENDENT xHIGH ARCHITECTURE REVIEW`
**Dependency:** POSTP1-002V2A-I1-R1 failure,
`ETF_CALENDAR_AUTHORITY_REQUIRES_ARCHITECTURE_DECISION`
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Required review:** one independent exact-hash xHigh architecture review
**Artifacts:** `prospective_evidence/etf_calendar_in_process_authority_boundary_v1/`
**Decision commit:** `28c9d985ffd08a8f65089b6648bb7e8b03fcf5fc`
**Decision hash:** `0c237c1b217b1fd406ec3967309774293c01d3e27574b9f4a7d1b9a0e887b55d`

### Decision objective and authority

This architecture-only ticket resolves the failed call-site review's threat-
boundary ambiguity without implementing another calendar correction. The
production Python interpreter and process are part of the trusted computing
boundary. The calendar authority is a scientific-correctness authority, not a
hostile-interpreter isolation mechanism. It must defend against project-owned
supported bypasses, configuration and implementation error, persisted-artifact
drift, dependency drift, and accidental acceptance of unsupported public or
test APIs. It does not claim resistance to arbitrary code execution,
monkeypatching, module-global or class-dictionary reassignment, private-state
manipulation, debugger modification, or replacement of the assertion inside
the already-trusted process.

Only documented production entrypoints are authoritative callable surfaces.
For the ETF calendar they include `CalendarEvidenceStore.put`, `get`,
`records`, `envelopes`, `collect_official_calendar`, and scientific calendar or
replay owners consuming `CalendarEvidenceStore`. Explicit private and test-only
helpers are non-authoritative and must be unmistakably classified, rejected by
production persistence/store boundaries, and never exposed as production
aliases.

### Required future enforcement architecture

Every authoritative production entrypoint body must directly execute
`assert_trusted_persistence_dependency()`. Runtime decorator installation,
`functools.wraps` authority guards, exposed `__wrapped__` originals, raw or
original owner attributes, unguarded production cores, alternate aliases or
constructors, production-accepted test helpers, and caller-selected verification
or persistence capabilities are forbidden. Factored helpers may not establish
or return authoritative scientific behavior independently of an already-proven
authority context. Small duplicated boundary assertions are preferred over an
unguarded DRY core.

Read boundaries must assert at replay time: admission-time verification alone
does not make existing evidence scientifically usable after dependency drift.
The production collector body must assert before HTTPS, private-key loading,
signing, or persistence. A controlled startup self-check must validate the
calendar parent, dependency child, exact certified dependency, and executable
manifest, but does not replace any direct entrypoint check.

A mechanical AST production-surface audit must prove that no wrapper/decorator
guard, `__wrapped__` bypass, unguarded production alias/core, or missing direct
entrypoint assertion exists. Direct-call regressions must cover all five named
entrypoints and scientific replay owners. Controlled-startup repository/runtime
identity detects ordinary reviewed code drift; it does not claim hostile
post-load mutation resistance.

If any higher authority later requires arbitrary same-process mutation
resistance, work must stop with
`ETF_CALENDAR_AUTHORITY_REQUIRES_PROCESS_ISOLATION_ARCHITECTURE`. A separate
trusted process or service with narrow IPC and independently controlled state is
then required; no decorator, metaclass, source-hash, or other wrapper-level
workaround is acceptable.

### Drift, science, lineage, and safety

Calendar-parent, dependency-child, expected dependency hash/version, certified
trusted-persistence authority, and supported-production-API bypass mismatches
remain hard refusals. The certified dependency remains closed and unchanged at
`02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772`.
Source profiles, URLs, TLS, redirects, parsers, coverage, early closes, PIT,
common-session semantics, ETF formulas/revisions, Stage-B metrics, risk, stops,
and thresholds are unchanged.

Failed calendar hashes `a1ceb66b...7db0b9`, `b81c1702...b357af`,
`05243343...f99c855`, `b499c6a4...e584e076`, and `901f572e...fd9853f`
remain non-authoritative, non-certified, unused, zero-observation, and
superseded before use. The seven material child decisions and parent reproduce
deterministically from one registry; focused integrity and tamper tests pass
7/7. The combined architecture-decision and unchanged ETF calendar regression
suite passes 138/138; compileall and exact persisted-artifact restoration pass.

No observation was collected and no real Stage-B evaluation ran. The calendar
is not certified. POSTP1-001V2R1, POSTP1-003R3, POSTP1-004, and collection stay
blocked; BTC-019 is untouched and Epic T is unchanged. This ticket authorizes
only independent xHigh architecture review. Another calendar implementation is
forbidden until that review passes. Final classification is
`ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1_READY_FOR_XHIGH_REVIEW`.

### Independent architecture review result

POSTP1-002V2A-AD1 failed this exact candidate with
`PROJECT-OWNED BYPASS MODEL INCOMPLETE`. Caller-driven arbitrary private-state
manipulation was correctly outside scope, but repository-owned production and
scientific code was not explicitly forbidden from directly accessing
`CalendarEvidenceStore` authoritative internals. The scientific replay-owner
surface was also a category placeholder rather than a closed, mechanically
reconciled census. The namespace and hash above remain immutable,
non-certified, unused, and at zero observations.

## POSTP1-001V2A-AD1-R1 — `COMPLETE_ETF_CALENDAR_PROJECT_OWNED_BYPASS_MODEL_V1`

**Status:** `IMPLEMENTATION COMPLETE / FAILED INDEPENDENT EXACT-HASH xHIGH ARCHITECTURE RE-REVIEW`
**Dependency:** POSTP1-002V2A-AD1 failure,
`ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1_REQUIRES_FIX`
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Required review:** one independent exact-hash xHigh architecture re-review
**Artifacts:** `prospective_evidence/etf_calendar_in_process_authority_boundary_v1_r1/`
**Decision commit:** `e09534f611dc5043fbc8099c80106adba899a42c`
**Decision hash:** `a7d2b08741080494cc4ca0269bf21e28e631c7f2e70887bcb0e1beb302534dd0`

### Corrected decision objective and authority

This architecture-only correction preserves the trusted-process boundary and
distinguishes arbitrary caller manipulation from repository-owned bypasses.
External code with arbitrary Python execution that mutates private fields,
class dictionaries, module globals, or debugger state remains outside the
scientific-authority threat model. Repository-owned production/scientific code
that reads or writes authoritative store internals outside the implementation
of `CalendarEvidenceStore` is in scope and forbidden.

The parent binds `_records` and `_envelopes` as the complete current registry of
implementation-private authoritative state. Store methods may access their own
state; code outside that boundary must use `put`, `get`, `records`, or
`envelopes`. Adding authoritative internal storage requires registry review and
must move both the owning child and parent hashes.

### Exact replay-owner closure and static audit

The placeholder owner category is removed. The frozen eleven-owner registry is
`derive_normalized_schedule_from_official_source`,
`venue_session_calendar_record`, `_verify_schedule`,
`_verify_schedule_record`, `validate_normalized_schedule_against_source`,
`_verify_venue_row`, `venue_session_status`, `common_etf_session_status`,
`expected_etf_publication_dates`, `derive_etf_window_calendar`, and
`scientific_etf_flow_window`. Python AST discovery mechanically reconciles the
registry against annotated store parameters, documented store calls, reserved
internal-state access, and transitive owner calls forwarding a store argument.
Missing and stale owners refuse.

The entire production calendar module, excluding only the implementation
bodies of `CalendarEvidenceStore`, is structurally audited for dotted private
access, literal `getattr`/`setattr`, and literal `__dict__`/`vars` forms. Every
enumerated owner must terminate in a documented store API directly or through
another compliant enumerated owner. The corrected static-audit contract also
retains the direct executable AST-call requirement for the five authoritative
boundary bodies and prohibits runtime wrappers, `functools.wraps`,
`__wrapped__`, and unguarded production aliases/cores. Higher-level owners need
not duplicate a dependency assertion when every evidence route terminates in a
directly asserting store read surface.

The nine material children and parent reproduce under child-order variation,
three `PYTHONHASHSEED` values, alternate working directory, fresh process, and
fresh output directories. Regressions refuse `_records`, `_envelopes`, literal
dynamic private access, unenumerated owners, and stale registry entries while a
compliant enumerated store-API consumer passes.

No production calendar implementation changed. The failed architecture remains
immutable and non-certified. The certified trusted-persistence dependency is
closed and unchanged. Source/parser, PIT/common-session, ETF, Stage-B, risk,
stop, and threshold semantics are unchanged. No observation was collected and
no real Stage-B evaluation ran. Calendar implementation, POSTP1-001V2R1,
POSTP1-003R3, POSTP1-004, and collection remain blocked; BTC-019 and Epic T are
untouched. Final classification is
`ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1_READY_FOR_REPEAT_XHIGH_REVIEW`.

### Independent architecture re-review result

POSTP1-002V2A-AD1-R1 independently reproduced the exact parent
`a7d2b087...534dd0`, all nine material children and the current 11/11 replay-
owner census, but failed the candidate with
`TRANSITIVE REPLAY CLOSURE INVALID`. The fixed-point route audit proves only
that an owner has at least one documented-store path. It accepts a mixed owner
cycle when one member also has a documented exit, and it accepts an owner that
has both a documented call and an alternate undocumented store-method route.
Therefore it does not prove the frozen universal invariant that every evidence
route terminates at `put`, `get`, `records`, or `envelopes` and that no owner
cycle can evade such termination.

The re-review also found that annotated variadic parameters are omitted from
the mechanical owner-discovery parameter census. A new top-level
`*stores: CalendarEvidenceStore` consumer using `stores[0].records()` leaves
the discovered and frozen sets unchanged and passes the complete static audit,
contrary to the frozen annotation-discovery rule and new-consumer drift
requirement. The exact candidate remains immutable, non-certified, unused and
at zero observations. No review fix or production change was made. A bounded
architecture correction is required before any calendar implementation; V2R1,
POSTP1-003R3, POSTP1-004 and collection remain blocked. The focused corrected-
architecture suite passed 22 tests; the full Python 3.12.14 suite passed 5,162
tests with three explained skips under `-W error::RuntimeWarning`. Compileall
and the reviewed documentation diff check also passed.

## POSTP1-001V2A-AD1-R2 — `ENFORCE_ETF_CALENDAR_UNIVERSAL_REPLAY_ROUTE_CLOSURE_V1`

**Status:** `IMPLEMENTATION COMPLETE / AWAITING INDEPENDENT EXACT-HASH FINAL xHIGH ARCHITECTURE REVIEW`
**Dependency:** POSTP1-002V2A-AD1-R1 failure,
`ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1_REQUIRES_FIX`
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Required review:** one independent exact-hash final xHigh architecture review
**Artifacts:** `prospective_evidence/etf_calendar_in_process_authority_boundary_v1_r2/`
**Decision commit:** `5d9bf9de9f90c48650a6d087df85cc1ac2349a75`
**Decision hash:** `dc36ffe228b7a3bc6d9145042b4e301c8624c99a79d71a88b46fc268f1372c3e`

### Bounded corrected decision objective and authority

This architecture-only correction fixes the two POSTP1-002V2A-AD1-R1 review
defects without changing the accepted trusted-process or private-state model.
The failed R1 boundary at `a7d2b087...534dd0` remains immutable,
non-certified, unused, and at zero observations. The certified trusted-
persistence authority remains closed and unchanged at
`02f96203...1a12772`. No production calendar implementation or scientific
semantics changed.

The corrected proof uses one `StoreBearingExpressions` model for owner
discovery, route extraction, forwarding detection, and undocumented-method
detection. It includes ordinary parameters and aliases; annotated `*args`
elements and `**kwargs` values; indexed variadic references; loop variables;
and mechanically resolvable starred forwarding. The unchanged production
source still reconciles exactly to the frozen eleven-owner registry.

### Universal route graph and closure

Every mechanically known store-dependent edge is emitted with stable owner,
line, column, kind, and target identity and is classified as exactly one of
`DOCUMENTED_STORE_API_TERMINAL`, `ENUMERATED_REPLAY_OWNER_EDGE`,
`FORBIDDEN_UNDOCUMENTED_STORE_METHOD`,
`FORBIDDEN_UNENUMERATED_STORE_FORWARD`, or
`FORBIDDEN_PRIVATE_STATE_ROUTE`. Only `put`, `get`, `records`, and `envelopes`
are documented store terminals. Any forbidden edge refuses the audit.

The owner-only graph must be acyclic; self-loops and all multi-owner cycles
refuse even when a cycle member also has a documented exit. After cycle
rejection, every owner must have a store-dependent edge and every owner-edge
path must recursively terminate at a documented store API. This is universal
closure: one valid route cannot excuse an undocumented method, unknown
forward, private-state route, or cyclic route.

The ten material children include a new replay-route-model contract plus
corrected owner-registry, transitive-rule, static-audit, and safety contracts.
Independent mutations of the universal quantifier, cycle rule, undocumented-
method rule, variadic-parameter rule, indexed-reference rule, and terminal-
path rule move the owning child and parent hashes. The parent and all children
reproduce under child-order reversal, three `PYTHONHASHSEED` values, alternate
working directory, fresh process, and fresh output directory.

The focused R2 suite passes 40/40. The combined R1/R2 architecture, original
boundary, and unchanged calendar regression suite passes 200/200. The full
Python 3.12.14 suite passes 5,202 tests with three explained skips under
`-W error::RuntimeWarning`; compileall, exact persisted-artifact restoration,
and the scoped implementation/documentation diff check pass. The repository-
wide diff check reports only the pre-existing user-owned trailing blank line in
`prompts/review_epic.md`, which this ticket leaves untouched as required. No
observation was collected and no Stage-B evaluation ran. Calendar
implementation, POSTP1-001V2R1, POSTP1-003R3, POSTP1-004, and collection stay
blocked; BTC-019 is untouched and Epic T is unchanged. Final classification is
`ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1_READY_FOR_FINAL_XHIGH_ARCHITECTURE_REVIEW`.

Successful implementation authorizes only POSTP1-002V2A-AD1-R2 independent
exact-hash final xHigh architecture review. Only that review passing may
authorize one final ETF calendar implementation/refreeze.

### Independent final architecture review result

POSTP1-002V2A-AD1-R2 independently reproduced exact parent
`dc36ffe2...f1372c3e`, all ten material children and their parent bindings, the
11/11 production replay-owner census, the acyclic actual owner graph, both
failed architecture lineages and certified trusted-persistence dependency.
The direct undocumented-method, branch-conservative, unknown-forward, cycle,
variadic, private-state, direct-body, material-mutation and determinism probes
passed.

The candidate nevertheless failed with
`FAIL — UNIVERSAL EDGE CLASSIFICATION INCOMPLETE`. An ordinary bound-method
extraction such as `bad_fn = store.some_undocumented_method` emits no edge and
does not preserve a store-method capability. Therefore an owner that also calls
`store.records()` passes because only the good terminal is visible. A
documented bound-method alias is likewise silently omitted when another direct
terminal exists. This is ordinary repository-owned behavior, not hostile
obfuscation, and falsifies the frozen claim that every mechanically known
store-dependent edge is classified.

The exact candidate remains immutable, non-certified, unused and at zero
observations. No review fix or production change was made. Per the final-review
hard stopping rule, do not create POSTP1-001V2A-AD1-R3; an explicit proof-
architecture decision is required. Calendar implementation/refreeze,
POSTP1-001V2R1, POSTP1-003R3, POSTP1-004 and collection remain blocked; BTC-019
and Epic T remain untouched. The focused R2 suite passed 40 tests, the combined
architecture/calendar regression passed 200 tests, and the full Python 3.12.14
suite passed 5,202 tests with three explained skips under
`-W error::RuntimeWarning`. Compileall and diff checks passed.

## POSTP1-001V2A-PAD1 — `DEFINE_ETF_CALENDAR_STORE_CAPABILITY_NORMAL_FORM_V1`

**Status:** `IMPLEMENTATION COMPLETE / FAILED INDEPENDENT EXACT-HASH xHIGH PROOF-ARCHITECTURE REVIEW`
**Dependency:** POSTP1-002V2A-AD1-R2 failure,
`ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1_REQUIRES_PROOF_ARCHITECTURE_DECISION`
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Required review:** POSTP1-002V2A-PAD1, one independent exact-hash xHigh
proof-architecture review
**Artifacts:** `prospective_evidence/etf_calendar_store_capability_normal_form_v1/`
**Decision commit:** `2cc1ce600355483d5f7567e5294d59fcb934e999`
**Decision hash:** `9f6af1794e8b49dce38288b9f1b9710bffd04ba70303b5c380e8fb447ac86295`

### Decision objective and closed proof strategy

This proof-architecture decision supersedes the failed open-ended route-model
strategy without modifying any failed artifact or production calendar code.
Scientific authority is proven by restricting repository-owned scientific code
to a closed mechanically auditable store-capability grammar. The proof models
every certified allowed store use and refuses every recognized use outside the
grammar; it does not claim to understand every valid Python program and has no
obligation to learn a future syntax automatically.

Store-bearing roots and derivations are limited to directly annotated
`CalendarEvidenceStore` parameters, simple local-name aliases, annotated
`*args` elements, annotated `**kwargs` values, direct indexed extraction,
direct variadic iteration targets, and simple aliases of those derived values.
The only permitted uses are direct calls to `put`, `get`, `records`, or
`envelopes`; direct forwarding to the exact frozen owner registry; transparent
local aliases; and the frozen variadic derivations. Every use receives exactly
one stable permitted or forbidden classification.

Bare extraction of a documented or undocumented bound method is forbidden,
including when another valid terminal exists. Return/yield of a store,
arbitrary list/tuple/dict/set packing, object/subscript storage, unknown
forwarding, nested function/lambda/generator capture, dynamic attribute access,
and all other unsupported uses are refused. The proof does not propagate bound-
method capabilities because extraction itself is outside the certified coding
surface.

### Preserved graph, boundary and implementation separation

Only after the normal-form audit passes may proof reconcile the eleven frozen
replay owners, extract direct documented terminal and enumerated-owner edges,
reject cycles, and prove every owner path terminates at a documented store API.
The trusted production-process boundary, project-owned bypass prohibition,
private `_records`/`_envelopes` boundary, five direct-body dependency
requirements and controlled startup self-check remain unchanged. If hostile
same-process resistance later enters scope, process isolation remains required.

This decision does not certify current production conformance. The current
`common_etf_session_status` generator expression captures `evidence_store`, a
syntax deliberately forbidden by the new grammar; a later implementation may
rewrite it only after proof-architecture review PASS and must preserve its
science and behavior. That later ticket must also implement the certified
normal-form audit, remove wrapper-installed guards, insert direct assertions in
the five required production bodies, perform controlled startup verification,
and refreeze the calendar authority. This ticket performs none of those steps.

### Evidence, safety and authorization

The nine material children bind the trusted-process reference, store-bearing
grammar, permitted and forbidden uses, replay graph, variadics, direct-body
dependency rule, proof order/completeness, and science/lineage/safety. The
focused decision suite passed 56 tests. The combined PAD1, original/R1/R2
architecture and unchanged calendar regression set passed 256 tests. Exact
artifact restoration, material mutation sensitivity, child-order reversal,
three `PYTHONHASHSEED` values, alternate cwd, fresh process/output, compileall
and diff checks passed under Python 3.12.14.

All three failed architecture hashes and all five failed calendar hashes remain
immutable, failed, non-certified, unused and at zero observations. Certified
trusted persistence `02f96203...1a12772`, certified prospective V1
`8915d991...fbfac7d7`, failed V2 `488251df...0ec0b6d`, and all calendar science
remain unchanged. No observation was collected and no Stage-B evaluation ran.
Calendar implementation/refreeze, POSTP1-001V2R1, POSTP1-003R3, POSTP1-004 and
collection remain blocked; BTC-019 is untouched and Epic T is unchanged.

Final classification is
`ETF_CALENDAR_STORE_CAPABILITY_NORMAL_FORM_V1_READY_FOR_XHIGH_REVIEW`.
Successful implementation authorizes only POSTP1-002V2A-PAD1 independent
exact-hash xHigh proof-architecture review. Review PASS would authorize defining
one calendar implementation/refreeze ticket, not implementation, V2R1 or
collection directly.

### Independent proof-architecture review result

POSTP1-002V2A-PAD1 independently reproduced exact parent
`9f6af179...7ac86295`, all nine material children and their parent bindings,
the exact eleven-owner production census, all failed lineages, and certified
trusted-persistence dependency `02f96203...1a12772`. The candidate correctly
defines a finite grammar rather than claiming arbitrary Python analysis,
refuses bare bound-method extraction and the current
`common_etf_session_status` generator capture, and freezes that production
delta without claiming current conformance. The explicitly listed return,
yield, container, storage, nested-capture, dynamic-access and unknown-forward
refusals, plus direct APIs, bounded variadics, cycles, material mutation
sensitivity and determinism, otherwise behaved as specified.

The candidate nevertheless failed with
`FAIL — CLOSED GRAMMAR COMPLETENESS INVALID`. Three ordinary syntactic classes
violate the frozen fail-closed boundary. First, a directly annotated ordinary
store parameter is accepted in `enumerated_owner(*store)` and
`enumerated_owner(**store)`, although starred forwarding is frozen only for the
annotated variadic containers. Second, a nested function with an annotated
`CalendarEvidenceStore` parameter is completely invisible when its top-level
outer function has no store-bearing root. Third, roots and aliases are derived
flow-insensitively and binding contexts are not audited: an annotated root or
transparent alias can be rebound before a documented call, and an alias can be
used before its later assignment, while the call is still classified as a
permitted store terminal. The replay graph can therefore prove a terminal that
does not consume the passed evidence capability.

These are closed-grammar completeness defects, not requests to understand
arbitrary Python dataflow. The exact candidate remains immutable,
non-certified, unused and at zero observations. No review fix, artifact change
or production change was made because the review may not expand the analyzer
or rewrite the calendar implementation. A bounded corrected proof architecture
and its own independent review are required before calendar implementation/
refreeze. POSTP1-001V2R1, POSTP1-003R3, POSTP1-004 and collection remain
blocked; BTC-019 and Epic T remain untouched. The focused PAD1 suite passed 56
tests, the combined architecture/calendar regression passed 256 tests, and the
prior full-suite baseline remains 5,202 passed with three explained skips.
Nine representative material mutations, fresh-process/hash-seed, alternate-
cwd/output, child-order, compileall and diff checks passed.

## POSTP1-001V2A-PAD1-R1 — `NARROW_ETF_CALENDAR_STORE_CAPABILITY_NORMAL_FORM_V1`

**Status:** `IMPLEMENTATION COMPLETE / FAILED INDEPENDENT EXACT-HASH FINAL xHIGH REVIEW`
**Dependency:** POSTP1-002V2A-PAD1 failure,
`ETF_CALENDAR_STORE_CAPABILITY_NORMAL_FORM_V1_REQUIRES_FIX`
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Required review:** POSTP1-002V2A-PAD1-R1, one independent exact-hash final
xHigh proof-architecture review
**Artifacts:** `prospective_evidence/etf_calendar_store_capability_normal_form_v1_r1/`
**Decision commit:** `22ba8194e591a5f76091abd3f7ceb8508abc7a19`
**Decision hash:** `7ef114fede9efebe594f0ecf119d097a1161119f448737d0df10afdf9468d17b`

### Narrow corrected architecture

The corrected candidate retains decision version
`ETF_CALENDAR_STORE_CAPABILITY_NORMAL_FORM_V1` in a new immutable R1 namespace
and leaves failed parent `9f6af179...7ac86295` unchanged, non-certified, unused
and at zero observations. It resolves exactly the three P1 review findings by
narrowing the grammar to `DIRECT_IMMUTABLE_STORE_PARAMETER_NORMAL_FORM`.

The only supported store-bearing root is a positional-only, ordinary
positional/keyword or keyword-only function parameter explicitly annotated
`CalendarEvidenceStore`. Names do not confer authority. Aliases, annotated
store `*args`/`**kwargs`, local store construction, container derivation,
nested annotated owners and starred store forwarding are forbidden. A root may
only be the receiver of a direct `put`, `get`, `records` or `envelopes` call,
or an ordinary positional/named keyword argument to an exact frozen replay
owner.

Each root has only its parameter binding. Before use or graph analysis, the
executable audit refuses same-scope `Assign`, `AnnAssign`, `AugAssign`,
`NamedExpr`, `For`, `AsyncFor`, `With`, `AsyncWith`, `ExceptHandler`, match
capture, `Import`, `ImportFrom`, `FunctionDef`, `AsyncFunctionDef`, `ClassDef`
and `Del` binding/unbinding events. A module-wide pass independently refuses
all nested annotated owners, including under rootless outer functions. This
closed syntax requires no alias propagation, reaching-definition analysis,
SSA construction or arbitrary control-flow proof.

Only after structural, binding and use audits pass does the analyzer reconcile
the exact eleven ordinary annotated production owners, extract direct terminal
and enumerated-owner edges, reject cycles and prove terminal paths. Current
production is deliberately refused at the known
`common_etf_session_status` generator-expression capture; no production or
scientific code changed.

### Evidence and authorization

Ten mechanically enumerated material children bind the trusted-process
boundary, root grammar, binding discipline, permitted uses, forbidden escapes,
nested-owner prohibition, replay graph, direct-body dependency rule, proof
order/completeness and science/lineage/safety. The focused R1 suite passed 81
tests. The combined R1/PAD1/original-R1-R2 architecture and unchanged calendar
regression set passed 337 tests. Three `PYTHONHASHSEED` values, alternate cwd,
fresh output, reversed child order, artifact restoration and representative
material mutations passed. Python 3.12 compileall and diff checks passed.

Trusted persistence `02f96203...1a12772`, the trusted-process boundary, five
direct dependency-body requirements, startup identity checks, calendar science
and all prior lineages remain unchanged. No observations were collected and no
real Stage-B evaluation ran. Calendar implementation/refreeze,
POSTP1-001V2R1, POSTP1-003R3, POSTP1-004 and collection remain blocked;
BTC-019 is untouched and Epic T is unchanged.

Final classification is
`ETF_CALENDAR_STORE_CAPABILITY_NORMAL_FORM_V1_READY_FOR_FINAL_XHIGH_REVIEW`.
Successful implementation authorizes only POSTP1-002V2A-PAD1-R1 independent
exact-hash final xHigh review. Only review PASS may authorize one final ETF
calendar implementation/refreeze ticket.

### Independent final proof-architecture review result

POSTP1-002V2A-PAD1-R1 independently reproduced exact parent
`7ef114fe...8d17b`, all ten material children and their parent bindings, the
exact eleven-owner production census, all preserved failed lineages and
certified trusted-persistence dependency `02f96203...1a12772`. All ten requested
material mutations moved both the owning child and parent hashes. Fresh-process
hash-seed, alternate-cwd/output, child-order, artifact-restoration, compileall
and diff checks passed. Direct immutable roots, alias/variadic/starred-forward
refusals, nested annotated-owner discovery, closed direct uses, graph cycles and
termination otherwise behaved as specified. Current production remains refused
only at the known `common_etf_session_status` generator capture and continues to
need no alias, variadic or rebinding support.

The candidate nevertheless failed with
`FAIL — PYTHON 3.12 BINDING CENSUS INCOMPLETE`. The executable binding visitor
does not handle `ast.TypeAlias`, so `type store = int` can replace an annotated
root and a later `store.records()` is accepted as a documented terminal. The
visitor also suppresses nested function and lambda bodies without separately
visiting their enclosing-scope defaults and decorators, and records a nested
class name without visiting its bases, keywords or decorators. Consequently,
assignment expressions in each of those definition-time contexts can rebind
the owner root while the later false terminal is accepted. These are direct
Python 3.12 binding contexts inside the frozen immutable-root claim, not a
request for reaching-definition, SSA or general control-flow analysis.

The exact candidate remains immutable, non-certified, unused and at zero
observations. No review fix, proof artifact change or production change was
made. Do not automatically create POSTP1-001V2A-PAD1-R2; the missing binder and
enclosing-scope contexts require an explicit proof-architecture decision.
Calendar implementation/refreeze, POSTP1-001V2R1, POSTP1-003R3, POSTP1-004 and
collection remain blocked; BTC-019 and Epic T remain untouched. The focused R1
suite passed 81 tests and the combined architecture/calendar regression passed
337 tests. The prior full-suite baseline remains 5,202 passed with three
explained skips because no production behavior changed.

## POSTP1-001V2A-PAD2 — `DEFINE_ETF_CALENDAR_COMPILED_BINDING_WITNESS_V1`

**Status:** `IMPLEMENTATION COMPLETE / FAILED INDEPENDENT EXACT-HASH xHIGH PROOF-ARCHITECTURE REVIEW`
**Dependency:** POSTP1-002V2A-PAD1-R1 failure,
`ETF_CALENDAR_PROOF_ARCHITECTURE_REQUIRES_NEW_DECISION`
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Required review:** POSTP1-002V2A-PAD2, one independent exact-hash xHigh
proof-architecture review
**Artifacts:** `prospective_evidence/etf_calendar_compiled_binding_witness_v1/`
**Decision commit:** `a83dcf4c5b4a5a34c251434e1488ec2b1d0cb072`
**Decision hash:** `b5ca36bfa9b96970b667cc44b10c5c5da7eb5ce7c57e5739601640d9b2a8abe9`

### New proof architecture

This is an explicit new proof-architecture decision, not a PAD1 revision. The
failed `ETF_CALENDAR_STORE_CAPABILITY_NORMAL_FORM_V1` candidates
`9f6af179...7ac86295` and `7ef114fe...8d17b` are untouched, non-certified,
unused and at zero observations, and no PAD1-R2 was created.

The narrow PAD1-R1 coding grammar is retained in full: the only scientific root
is an ordinary positional-only, positional-or-keyword or keyword-only parameter
explicitly annotated `CalendarEvidenceStore`; aliases, annotated store
variadics, starred forwarding, local construction, container derivation and
nested annotated owners stay forbidden; a root may only receive a direct `put`,
`get`, `records` or `envelopes` call or be a non-starred argument to an exact
frozen replay owner. What is removed is the failed claim that a hand-maintained
census of `ast` binding nodes is the proof of root immutability. The source
binding visitor is demoted to diagnostics, early failure, reason codes and
regression localization, and the frozen material states explicitly that a
missing AST diagnostic can never make an actual compiled root write acceptable.

Root immutability is now proven as `CLOSED_AST_USE_GRAMMAR_PLUS_FROZEN_CPYTHON_BINDING_WITNESS`
against the exact compiled code object of each replay owner under frozen CPython
`3.12.14` (`magic cb0d0d0a`, `cache_tag cpython-312`, `hexversion 0x030C0EF0`).
Any runtime or compiler identity mismatch refuses scientific authority. The
reviewed source is compiled with `dont_inherit=True, optimize=0` and never
imported or executed; cached bytecode is never trusted. The frozen 29-name
root-binding opcode policy is checked mechanically against the interpreter's own
`haslocal | hasfree | hasname` tables, their opcode numbers, the single reserved
unnamed slot `148`, and the 64-entry specialization table; anything unexpected
requires a new proof architecture rather than a guess. Instructions are read
deoptimized, so quickening cannot hide a root write.

Each owner is identified by exactly one code object with `co_qualname` equal to
the top-level name, `co_firstlineno` equal to the compiler's definition line
(the first decorator line when decorated) and the root in its declared-parameter
slice, so a same-named nested function can never be substituted. The module-level
owner name must still denote that definition: owners may not be decorated, each
owner name is bound exactly once in the module code object, and, anywhere in the
module's whole code-object tree, a later rebinding or deletion of an owner name,
a write to a live function object's `__code__`/`__defaults__`/`__closure__`/
`__globals__`/`__dict__`, and any reach into the module namespace through
`globals`, `vars`, `locals`, `setattr`, `delattr`, `exec`, `eval`, `compile` or
`__import__` all refuse. Those checks descend into nested code objects, so a
substitution hidden one call frame deep is refused too.

The primary binding rule is structural: a conforming root may never be a cell
variable of its owner. A cell is a first-class object that any capturing
function exposes through `__closure__`, so writing `cell_contents` would rebind
the root without emitting a single root-binding instruction; forbidding the cell
removes that entire escape class by construction instead of by enumerating
escape attributes. The rule is at least as strict as the source grammar's
unconditional nested-capture prohibition and, in three known families — a bare
`nonlocal` declaration naming the root, a PEP 695 lazy type-alias or
type-parameter scope reading the root, and a statically dead nested scope that
still cells the root — strictly stricter; that over-refusal is deliberate and
fail closed, and the decision does not claim the two layers accept the same
sources. On top of
it, no instruction in the owner's own code object may write, clear or delete the
root after frame-entry parameter establishment, and, as defence in depth, no
nested code object holding the root as a free variable of the owner's cell may
`STORE_DEREF` or `DELETE_DEREF` it; a class body's same-named `STORE_NAME` is a
different namespace and is never an owner-root write, and a nested function
body's own local assignment is not an outer-root write. `exec`, `eval`,
`compile`, `__import__`, `getattr`/`setattr`/`delattr`, `globals`/`locals`/`vars`,
`ctypes`, `gc`, `inspect`, `sys` and the frame/cell reflection attribute surface
are forbidden inside replay owners as a conservative production rule, explicitly
not as a completeness claim; frame-local mutation, debugger mutation and
arbitrary reflective namespace manipulation remain outside the trusted-process
threat model.

The frozen proof order verifies compiler identity, compiles without executing,
identifies the exact owner code objects, discovers annotated roots, runs the
binding witness, rejects any root write, and only then runs the closed AST use
grammar, the eleven-owner census, edge extraction, cycle rejection, termination
and the direct-body/startup contracts. There is no graph authority before the
binding witness, and a disagreement between the AST and compiled layers always
fails closed. The architecture claims exactly three separate guarantees — the
compiled witness proves the root is not rebound or deleted, the AST normal form
proves permitted uses, the graph proves replay-route closure — and never that
bytecode proves arbitrary program semantics. The witness carries the reviewed
source hash, so a witness generated from other source cannot certify the module.

### Evidence and authorization

Eleven mechanically enumerated material children bind the trusted-process
boundary, proof-interpreter identity, root/direct-use grammar, compiled binding
witness, owner code-object identity, dynamic-execution prohibition, nested-owner
and capability-escape rules, replay graph, direct-body dependency rule, proof
order/completeness and science/lineage/safety. Two adversarial probing rounds
against the frozen interpreter found and closed seven real defects: the
`__closure__`/`cell_contents` cell escape, `ctypes`/`settrace` frame write-back,
module-level owner-name substitution by decorator or `globals()`, the same
substitution hidden one call frame deep, module-level `exec`, a live
`owner.__code__` swap, and class-body `STORE_NAME` misread as an owner-cell
write; the false "localsplus name tuples are disjoint" premise was corrected as
well. The second round independently reconfirmed the opcode-table integrity and
that a deoptimized scan is stable under quickening.

Current production is binding-proof compatible: none of the eleven owners
contains a root write, clear or delete, and none reaches a dynamic or reflective
authority escape. The single compiled-layer finding is the known
`common_etf_session_status` generator-expression capture of `evidence_store`,
which exposes that root as a closure cell; the closed AST grammar refuses the
same construct, so both layers refuse one and the same known use and the
calendar implementation stays blocked on the rewrite that was already required.
Production additionally reaches its own module namespace through `globals()` in
five scopes: `_install_exact_dependency_guards`, which installs the wrapper
guard the frozen direct-body dependency rule already forbids, and
`_semantic_ast_sha256`, `_children`, `write_artifacts` and `restore_artifacts`,
which dispatch artifact builders by name and must become an explicit registry.
The exact five are frozen in the decision and verified mechanically. Both the
cell-capture refusal and the module-namespace findings are deliberate, reported
strengthenings of the expected result, which anticipated the compiled layer
passing current production silently.

Trusted persistence `02f96203...1a12772`, the trusted-process boundary, the five
direct dependency-body requirements, startup identity checks, calendar science
and all prior lineages are unchanged. No observation was collected and no real
Stage-B evaluation ran.

Final classification is
`ETF_CALENDAR_COMPILED_BINDING_WITNESS_V1_READY_FOR_XHIGH_REVIEW`. Successful
implementation authorizes only POSTP1-002V2A-PAD2 independent exact-hash xHigh
proof-architecture review. Only that review PASS may authorize the final ETF
calendar implementation/refreeze ticket.

### Independent proof-architecture review result

POSTP1-002V2A-PAD2 independently reproduced exact parent
`b5ca36bf...b2a8abe9`, all eleven material children and their parent bindings,
the certified trusted-persistence dependency `02f96203...1a12772`, the exact
CPython 3.12.14 identity, all 29 named name-referencing opcodes, reserved slot
148 and the 64-entry specialization table. Deoptimized inspection exposed a
quickened root mutation as base `STORE_FAST`. `TypeAlias`, all reviewed
definition-time assignment expressions, ordinary binders, detached witnesses,
owner-code collisions, root cells, dynamic execution, cycles and non-terminating
graph routes refused as required. The exact eleven-owner production census has
zero root write/clear/delete findings, the one expected
`common_etf_session_status` cell capture and exactly five `globals()` namespace
findings. All twelve requested material mutations moved both the owning child
and parent hashes; artifact reproduction, child-order, three hash seeds,
alternate cwd and fresh output also passed.

The candidate nevertheless failed with
`FAIL — MODULE OWNER IDENTITY MODEL INCOMPLETE`. The whole-module identity scan
at `owner_name_identity_findings` recognizes direct owner-name stores/deletes,
direct `STORE_ATTR`/`DELETE_ATTR` writes and a finite list of namespace-reach
names. Ordinary project-owned source using either
`sys.modules[__name__].__dict__["owner"] = replacement` or
`owner.__setattr__("__code__", replacement.__code__)` produces none of those
recognized forms. Both sources pass the complete PAD2 compiled, dynamic, AST,
census and graph pipeline, while isolated execution confirms that each replaces
what the reviewed owner executes. `object.__setattr__` and
`type(owner).__setattr__` equivalents evade it too. Thus the module-owner
guarantee depends on an incomplete, open-ended enumeration of Python namespace
and function-mutation syntax even though the compiled root-binding witness
itself is coherent and bounded.

The exact candidate remains immutable, non-certified, unused and at zero
observations. No review fix, proof artifact change or production change was
made; adding more reflection names would not close the architectural defect.
Do not automatically create POSTP1-001V2A-PAD2-R1 or start I2. An explicit
bounded proof-architecture decision is required. Calendar
implementation/refreeze, POSTP1-001V2R1, POSTP1-003R3, POSTP1-004 and collection
remain blocked; trusted persistence, BTC-019 and Epic T remain unchanged. The
focused PAD2 suite passed 155 tests and the combined architecture/calendar/
trusted-persistence regression passed 583 tests. The prior full-suite baseline
remains 5,202 passed with three explained skips because production behavior did
not change.

## POSTP1-001V2A-PAD3 — `DEFINE_ETF_CALENDAR_RUNTIME_OWNER_ATTESTATION_V1`

**Status:** `IMPLEMENTATION COMPLETE / FAILED INDEPENDENT EXACT-HASH xHIGH PROOF-ARCHITECTURE REVIEW`
**Dependency:** POSTP1-002V2A-PAD2 failure,
`ETF_CALENDAR_PROOF_ARCHITECTURE_REQUIRES_NEW_DECISION`
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Required review:** POSTP1-002V2A-PAD3, one independent exact-hash xHigh
proof-architecture review
**Artifacts:** `prospective_evidence/etf_calendar_runtime_owner_attestation_v1/`
**Decision commit:** `385dd8ed32b0537ac3c97fe7c35d3e3e49c49ca9`
**Decision hash:** `b8f8b92d4e3c1c80c4226f7101e71f95d125bd48afbfcde72e489408f6b5b996`

### New proof architecture

This is an explicit new proof-architecture decision, not a PAD2 revision. No
`POSTP1-001V2A-PAD2-R1` was created, the failed
`ETF_CALENDAR_COMPILED_BINDING_WITNESS_V1` parent `b5ca36bf...b2a8abe9` is
untouched and is never certified here, and the whole failed lineage
`0c237c1b...887b55d`, `a7d2b087...534dd0`, `dc36ffe2...f1372c3e`,
`9f6af179...7ac86295`, `7ef114fe...8d17b` and `b5ca36bf...b2a8abe9` remains
immutable, non-certified, unused and at zero observations.

Exactly one failed component is replaced.
`STATIC_COMPLETE_MODULE_OWNER_IDENTITY_PROOF` becomes
`CONTROLLED_RUNTIME_OWNER_ATTESTATION`, and the decision freezes
`STATIC_REFLECTION_BLACKLIST_IS_NOT_OWNER_IDENTITY_PROOF` with
`reflection_blacklist_complete = false`. A list such as `globals`, `locals`,
`vars`, `setattr`, `delattr`, `sys.modules`, `object.__setattr__` and
`type.__setattr__` is no longer claimed to enumerate every way Python can
replace a module binding or change what a function executes. Those source
checks survive only as diagnostics, defence in depth and coding-policy
enforcement, never as scientific completeness authority.

Everything that independently survived PAD2 review is preserved and freshly
parent-bound: the frozen CPython 3.12.14 identity and exact opcode policy
checked against the interpreter's own tables, the deoptimized instruction scan,
`TypeAlias` and definition-time mutation detection, exact owner code-object
identification, nested-body scoping correctness, the structural rule that a
conforming root may never be a cell variable, the closed AST store-use grammar,
the exact eleven-owner census and graph, the direct dependency-body requirement
and the trusted-process boundary.

### Measured runtime identity

Effective scientific owner identity is measured, not enumerated. Immediately
before and immediately after every authoritative calendar or replay
computation, each frozen owner is read out of the loaded calendar module's own
`__dict__` and checked against material derived by independently compiling the
certified reviewed source under the frozen interpreter: the binding's presence,
its exact `types.FunctionType` type, its `__name__`, `__qualname__` and
`__module__`, a deterministic recursive execution fingerprint of its `__code__`,
the identity of its `__globals__` and of its bound builtins namespace, its
closure contract, its `__defaults__` and `__kwdefaults__` fingerprints and its
wrapper state. Code identity is a fingerprint rather than an object comparison,
because independently compiled equivalent code objects are not the same object;
the fingerprint covers argument layout, flags, stack, name and variable tuples,
the exception and line tables, the raw bytecode and a type-tagged canonical
encoding of the constant pool, recursing into nested code objects, and excludes
only `co_filename`, whose reviewed-source identity is attested separately and
exactly. `__globals__` identity is required for its own reason: a
`types.FunctionType(expected_code, foreign_globals)` reconstruction matches the
code bytes exactly and would otherwise pass.

Adversarial regression proves that module-dictionary replacement,
`owner.__setattr__("__code__", ...)`, `object.__setattr__`,
`type(owner).__setattr__`, same-code foreign globals, `__defaults__` and
`__kwdefaults__` mutation, and partial, wrapper, callable-object and
bound-method substitution are all refused without any of those syntactic forms
appearing in a blacklist.

### Transitive execution closure

Independent adversarial probing of the owner-only design found, and reproduced
against the implementation, that attesting only the eleven entry bindings
measures who is called and not what executes: substituting a private helper such
as `_parse_date`, a frozen constant such as `CANONICAL_VENUES`, a result
dataclass, the error type or a dependency-module function changes the scientific
answer while all eleven owner fingerprints still match byte for byte. An
executed end-to-end demonstration turned an honest `2025-01-04/CLOSED`
resolution into `2025-01-05/CLOSED` with a conforming owner attestation.

The attested surface is therefore the transitive execution closure, derived as a
mechanical fixpoint over the module-level names the certified owner code objects
can actually load, seeded by the eleven owners and by the declared
`CalendarEvidenceStore` root type, recursing into nested code objects and reading
instructions deoptimized. It is a derivation, not a hand-maintained list, and a
closure member missing from the frozen expectation refuses. For current
production it is 25 functions, 7 classes, 15 values and 14 imported bindings.
Reachable functions carry the full identity contract; reachable classes are
attested by exact metaclass, qualname, module, certified method code
fingerprints with their descriptor kinds, method wrapper state and an
uncertified-attribute census; reachable values by a deterministic deep typed
fingerprint against the literal the reviewed source declares, with a
non-literal value refusing; project-owned imports by `sys.modules` identity,
origin-attribute identity, their own certified source digest and the full
identity contract over every top-level function of the defining module, with
re-export chains followed. Interpreter-provided modules are attested by binding
identity only, because the frozen proof interpreter identity is already an
explicit axiom of this architecture and is not re-proved function by function.

The module itself must also be the one callers reach: exactly a
`types.ModuleType`, the live `sys.modules` entry, the package attribute of the
same name, the only loaded instance of the certified source, and holding the real
builtins namespace; a loaded consumer holding its own divergent binding for a
frozen owner name refuses too.

### Scientific execution epoch

`CALENDAR_SCIENTIFIC_EXECUTION_EPOCH` encloses every authoritative computation:
pre-execution attestation, then the synchronous computation in the very module
whose bindings were attested, then post-execution attestation, and only then
admission or persistence. A pre-attestation mismatch is
`SCIENTIFIC_EXECUTION_NOT_AUTHORIZED` with no owner call, no partial result, no
persistence and no Stage-B evidence; a post-attestation that does not reproduce
the pre-attestation digest is `RESULT_REJECTED` / `DATA_QUALITY_FAIL`. The
ordering is proven structurally over the architecture's own source rather than
asserted. The operation is frozen as pure with respect to durable state so that
all persistence happens in the admission call after post-attestation; a lazy or
deferred result is refused because its body would run after the measured window
closed; and every exit path, including an exception raised by the operation,
sweeps for persistent drift. Startup attestation additionally refuses a process
that is already wrong, records the baseline the first pre-attestation must
reproduce, and never replaces per-epoch attestation. Epochs are serialised one
at a time per process and a nested or reentrant epoch refuses; the lock is for
deterministic execution and configuration integrity, not hostile same-process
security.

### Bounded guarantee and explicit limit

Any substitution or mutation anywhere in the attested closure that is still in
effect at either attestation point refuses before any result is admitted. Any
mutation fully reverted between the two attestation instants is explicitly not
detected, whatever its cause, including benign concurrent patch-and-restore by
project-owned code in a non-epoch thread. That case is classified as arbitrary
adversarial same-process mutation, outside the accepted trust model, which is
unchanged: the production Python process is trusted, project-owned scientific
drift and misconfiguration are in scope, and arbitrary debugger, memory and
interpreter mutation is out of scope. If resistance to the transient case ever
becomes required the escalation is process isolation, never more Python
reflection filters. The threat model is not silently strengthened.

### Evidence and authorization

Sixteen mechanically enumerated material children, built from one explicit
registry of builder callables rather than by module-namespace dispatch, bind the
trusted-process boundary, proof-interpreter identity, compiled root-binding
witness, store root and direct-use grammar, runtime owner identity contract,
transitive execution closure rule, owner code fingerprint definition, scientific
execution epoch rule, pre/post attestation rule, attestation evidence schema,
replay owner graph rule, direct-body dependency rule, static reflection policy
demotion, module-namespace reach classification, proof order/completeness and
science/lineage/safety.

Current production is unchanged and no ETF calendar production code was
modified. It reports zero compiled root writes, clears or deletes; the single
root-cell finding remains `common_etf_session_status:evidence_store`; the closed
AST grammar refuses at the same generator capture; and all eleven effective
runtime owner bindings attest cleanly. The transitive closure does not: the
`CalendarEvidenceStore` admission and read methods are `functools.wraps` guards
installed at import, so runtime measurement independently rediscovers the
wrapper-installer blocker that the certified direct-body architecture already
forbids. Of the five module-namespace reaches, exactly one —
`_install_exact_dependency_guards` — writes, and the key it writes is not a
replay owner; the other four are read-only artifact-builder dispatch lookups
that cannot change any effective owner binding, established both by mechanical
AST classification and by measuring the owner attestation digest across artifact
generation, so this decision does not require them to be rewritten for owner
identity. Full calendar conformance is `NO` and the implementation stays
blocked.

Trusted persistence `02f96203...1a12772` is closed, certified, unchanged and not
re-reviewed. Calendar science, failed calendar lineage, BTC-019 and Epic T are
unchanged. No observation was collected and no real Stage-B evaluation ran.

Final classification is
`ETF_CALENDAR_RUNTIME_OWNER_ATTESTATION_V1_READY_FOR_XHIGH_REVIEW`. Successful
implementation authorizes only POSTP1-002V2A-PAD3 independent exact-hash xHigh
proof-architecture review. Only that review PASS may authorize the final ETF
calendar implementation/refreeze ticket, which must then rewrite the
`common_etf_session_status` generator capture, remove the wrapper-installed
guards, insert the five direct dependency assertions, implement startup and
per-epoch pre/post attestation, persist execution attestation evidence and
preserve the exact eleven-owner graph and the calendar science before an
independent exact-hash calendar closure review.

### Scope note

The transitive execution closure is broader than the literal PAD3 owner-set
wording, which specifies exactly eleven attested owners. That census is
preserved exactly — eleven frozen, eleven source-discovered, eleven
runtime-attested — and the closure is an additional mechanically derived tier.
It was added because independent adversarial verification reproduced, against
the implementation, that the eleven-owner surface alone admits a wrong
scientific result under ordinary project-owned drift, which is the same class of
defect that failed PAD2. Reviewers should treat the closure tier as the material
scope extension of this decision.

### Independent proof-architecture review result

POSTP1-002V2A-PAD3 independently reproduced exact parent
`b8f8b92d...f6b5b996`, all sixteen material children and their parent bindings,
failed PAD2 parent `b5ca36bf...b2a8abe9`, certified trusted-persistence dependency
`02f96203...1a12772`, the exact CPython 3.12.14 identity, and closure expectation
digest `d41b47db...e7b7`. The current mechanically derived calendar-module closure
is exactly 25 functions, 7 classes, 15 values and 14 imports; its intra-module
fixpoint, nested-code scan, code/value fingerprints, eleven-owner identity
contract, route checks, epoch sequencing, lazy-result refusal, current-production
blockers, material binding and determinism otherwise reproduced. The focused
suite passed 148 tests, the combined PAD3/PAD2/PAD1-R1/PAD1 suite passed 440, and
the calendar/ETF/trusted-persistence regression passed 741 with the one explained
PostgreSQL opt-in skip.

The candidate nevertheless failed with
`FAIL — PROJECT IMPORT EXECUTION CLOSURE INCOMPLETE`. A project-owned import is
attested by module route/source identity and by the runtime identity of its
top-level functions, but the derivation does not recurse through the globals
those functions and the calendar owner read. After a clean conforming
attestation, changing only `_flow.FIVE_DAY_ETF_FLOW_WINDOW_DAYS` or
`_flow.FIVE_DAY_ETF_FLOW_FEATURE_ID` leaves the complete attestation digest
unchanged. The feature-ID mutation changes the end-to-end scientific result from
`ETF_FLOW_5D` to `WRONG`, and the epoch admits it with equal pre/post digests.
Mutating a `_flow` constant during the operation is likewise admitted; the same
persistent mutation on an exception path escapes the drift sweep. Replacing
`_flow.EtfFlowFeatureResult` and substituting both the package re-export and
calendar binding of `require_utc_datetime` also pass unchanged while effective
runtime behavior changes.

A separate blocking class-closure defect was reproduced. The class attestor
records names and wrapper states for dataclass-generated functions but does not
fingerprint or reject them. Replacing `ScientificEtfFlowResult.__init__` leaves
the full attestation digest unchanged, changes an end-to-end result from
`NOT_EVALUABLE` to `WRONG`, and is admitted by the epoch. Adding an uncertified
method also leaves the class conforming despite the frozen refusal code.

The exact PAD3 candidate remains immutable, non-certified, unused and at zero
observations. No review fix, proof artifact change or production change was
made. Do not automatically create POSTP1-001V2A-PAD3-R1 and do not start I2;
the incomplete cross-module/class closure requires an explicit new bounded
proof-architecture decision. Calendar implementation/refreeze,
POSTP1-001V2R1, POSTP1-003R3, POSTP1-004 and collection remain blocked;
trusted persistence, failed PAD2 lineage, BTC-019 and Epic T remain unchanged.

## POSTP1-001V2A-PAD4 — `DEFINE_ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1`

**Status:** `IMPLEMENTATION COMPLETE / FAILED INDEPENDENT EXACT-HASH xHIGH PROOF-ARCHITECTURE REVIEW`
**Dependency:** POSTP1-002V2A-PAD3 failure,
`ETF_CALENDAR_PROOF_ARCHITECTURE_REQUIRES_NEW_DECISION`
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Required review:** POSTP1-002V2A-PAD4, one independent exact-hash xHigh
proof-architecture review
**Artifacts:** `prospective_evidence/etf_calendar_isolated_scientific_worker_v1/`
**Decision commit:** `02df82c2516ebcc50a592e5466fd15a61dcee481`
**Decision hash:** `cc1b325a656f5b0be046d46700a4fcb9ad7ad94bf9b3440acac164677b809e78`

### New proof architecture

This is an explicit new proof-architecture decision, not a PAD3 revision. No
`POSTP1-001V2A-PAD3-R1` was created, the failed
`ETF_CALENDAR_RUNTIME_OWNER_ATTESTATION_V1` parent `b8f8b92d...f6b5b996` is
untouched and is never certified here, and the whole failed lineage
`0c237c1b...887b55d`, `a7d2b087...534dd0`, `dc36ffe2...f1372c3e`,
`9f6af179...7ac86295`, `7ef114fe...8d17b`, `b5ca36bf...b2a8abe9` and
`b8f8b92d...f6b5b996` remains immutable, non-certified, unused and at zero
observations.

PAD3 proved that a clean attestation of the eleven owners plus the calendar
module's own functions, classes, values and imports is insufficient: persistent
mutation of `_flow.FIVE_DAY_ETF_FLOW_WINDOW_DAYS`,
`_flow.FIVE_DAY_ETF_FLOW_FEATURE_ID`, `_flow.EtfFlowFeatureResult`, the
`require_utc_datetime` re-export origin or the dataclass-generated
`ScientificEtfFlowResult.__init__` changes the science while the attested
surface is unchanged. Every earlier decision answered a defect by enlarging the
enumerated surface, and the mutable execution surface expands transitively, so
the enumeration can always be one object short.

PAD4 therefore changes the boundary rather than the list: **do not share mutable
Python scientific execution state with the application process**, rather than
attempt to enumerate every mutable object capable of affecting execution.
Recursive same-process runtime object attestation, transitive mutable-object
closure across the repository, reflection blacklist completeness and
generated-runtime-method enumeration are explicitly abandoned as completeness
proofs. PAD3's measured 25-function, 7-class, 15-value, 14-import runtime
closure is demoted to archived diagnostic evidence explaining why PAD3 failed.

### The isolated scientific worker

`ETF_CALENDAR_SCIENTIFIC_WORKER` is a fresh operating-system process created by
an exec-style launch of the exact frozen CPython 3.12.14 interpreter under
`-I -S -B`: fresh interpreter, fresh `sys.modules`, fresh project imports, no
inherited Python module object, environment-variable Python configuration
ignored, user site disabled, `sitecustomize`/`usercustomize` not executed,
uncontrolled current-directory import precedence disabled and `sys.path`
explicitly parent-controlled with no dependency on ambient `PYTHONPATH`. The
child receives a frozen minimal environment, so parent environment drift after
controller startup cannot reach it. A fork-only inherited interpreter is
`NOT_AN_AUTHORIZED_SCIENTIFIC_WORKER`. One canonical request enters on stdin,
exactly one fully materialized canonical response leaves on stdout, and the
process exits; there is no worker pool, no reuse, no background thread, no async
continuation and no lazy result. A wrong interpreter refuses with
`REFUSE_SCIENTIFIC_AUTHORITY` before any project import runs.

### Certified source universe, not object closure

`ETF_CALENDAR_WORKER_PROJECT_SOURCE_MANIFEST_V1` is the recursive project import
closure of the worker entrypoint, derived mechanically from static import
declarations — nested function-level declarations included — plus every ancestor
package, binding each module's canonical name, canonical source path and
SHA-256. For current production it is exactly 116 modules at manifest digest
`674b006a...3aadbb8`. No project-owned module outside the manifest may execute
in the worker. The proof boundary is certified source modules, not every runtime
object reachable after import, because under a fresh one-shot process every
project-owned runtime object — including a dataclass-generated `__init__` — is
freshly constructed from certified source under the frozen interpreter. A source
change that alters a generated class changes the manifest and requires refreeze.

Every non-stdlib dependency is explicitly frozen. The artifact freezes the rule
and the mechanically derived distribution roots (`alembic`, `cryptography`,
`numpy`, `scipy`, `sqlalchemy`); each launch binds the exact distribution,
version, install location and installed `RECORD` hash-manifest digest into the
request and the response, and the worker verifies them without `importlib`.
Install locations and wheel digests are deliberately launch-bound rather than
artifact-bound, because binding machine-specific environment material into the
decision would make the frozen decision hash unreproducible for an independent
reviewer.

The closed worker-coding rule is scoped to the two repository-owned
authoritative worker modules, `etf_calendar_scientific_worker_entry.py` and
`etf_calendar_worker_protocol.py`. They may not use `exec`, `eval`, `compile`,
`__import__`, `importlib`, `runpy`, `marshal`, `pickle`, `cloudpickle`, `dill`,
`ctypes`, `subprocess`, `multiprocessing`, network or database client modules,
or process-spawning `os` capabilities. Production calendar source remains
governed by the compiled root witness and the closed AST store grammar, not by
this rule, and this rule makes no claim to enumerate hostile Python techniques.

### Protocol and admission

`ETF_CALENDAR_SCIENTIFIC_WORKER_REQUEST_V1` is canonical JSON: schema-validated,
unknown fields refused, NaN/Infinity refused, timestamps canonical UTC with a
round-trip check, decimals canonical strings, and the received bytes must
re-serialize to themselves, which is the enforceable form of the no-pickle rule.
No function, class, module object, live `CalendarEvidenceStore`, pickled object
or callable crosses the boundary; the worker reconstructs a read-only evidence
view from canonical validated data. `ETF_CALENDAR_SCIENTIFIC_WORKER_RESPONSE_V1`
carries the worker, calendar, trusted-persistence, interpreter, entrypoint,
protocol, source-manifest and dependency-manifest identities, the request digest
echo, the operation, the fully materialized result and its digest, the
post-execution verification verdict and the one-request-one-process flag, with
no memory addresses. The controller admits a result only after every binding
reproduces and the process terminated cleanly; timeout, crash, protocol error,
extra stdout or any mismatch is `RESULT_NOT_ADMITTED` / `DATA_QUALITY_FAIL` with
no silent retry on a different authority path. The decision hash itself is
controller-bound by echo comparison, because the decision artifact is
deliberately outside the worker's certified source universe.

### Preserved authority and current production

The compiled root-binding witness, the root-cell prohibition, the closed AST
store-use grammar, the exact eleven-owner census and graph, the documented
`put`/`get`/`records`/`envelopes` terminals and the direct dependency-body
requirement are preserved and freshly parent-bound. Process isolation does not
redefine the owner graph and does not legalize wrappers. No ETF calendar
production code was modified: current production still reports zero compiled
root writes, clears or deletes, the single `common_etf_session_status`
generator capture, the same closed-grammar refusal, the five wrapper-installed
dependency guards and no isolated worker, so full conformance is `NO` and the
implementation stays blocked.

### Executed adversarial evidence

Sixteen adversarial regressions execute real worker processes. Parent-process
mutation of the `_flow` window constant, the `_flow` feature ID, the imported
`EtfFlowFeatureResult` class, the dataclass-generated
`ScientificEtfFlowResult.__init__`, the `require_utc_datetime` package
re-export, `sys.modules` and `builtins.sum` each demonstrably corrupts the
parent's own evaluation — the principal regression turns an honest
`ETF_FLOW_5D` into `WRONG`, and the generated-method regression turns
`EVALUABLE` into `WRONG` — while the isolated worker returns the certified
result unchanged, with no generated-method fingerprinting anywhere. A real
`os.fork()` child is shown to inherit the parent mutation that exec does not.
On-disk certified source mutation, a shadowing wrong project origin, an
unexpected project module, a tampered dependency `RECORD`, a leaked `PYTHON*`
environment, a signing-key environment variable, a drifted declared `sys.path`,
a second request in one process, a worker scientific exception, a real timeout
and extra stdout all fail closed.

### Recorded limits

The trusted process model is explicit: the worker is trusted once its certified
source and environment admission passes, and hostile debugger attachment,
operating-system memory injection, kernel compromise and a modification
perfectly racing file verification are out of scope. No operating-system-level
network sandbox is claimed; the no-network, no-signing-key and no-database
guarantees rest on the frozen read-only operation registry, the frozen minimal
child environment and the static closed worker-source prohibition. The current
package re-export graph makes the certified universe 116 modules wide and
includes `btc_predictor.db` and HTTPS-capable calendar collection modules even
though no frozen operation reaches them; the direct-import reduction that
narrows this is explicitly deferred to the final calendar implementation ticket.
The prototype non-authoritative evidence admission mode installs an
already-verified acquisition snapshot directly, because the authoritative
production-signed envelope replay path needs a production signing capability the
worker must never hold; the authoritative mode uses only documented store APIs.

Trusted persistence `02f96203...1a12772` is closed, certified, unchanged and not
re-reviewed. Calendar science, failed calendar lineage, BTC-019 and Epic T are
unchanged. No observation was collected and no real Stage-B evaluation ran.

Final classification is
`ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_READY_FOR_XHIGH_REVIEW`. Successful
implementation authorizes only POSTP1-002V2A-PAD4 independent exact-hash xHigh
proof-architecture review. Only that review PASS may authorize POSTP1-001V2A-I2,
the final ETF calendar implementation/refreeze, which must then rewrite the
`common_etf_session_status` generator capture, remove the wrapper-installed
guards, insert the five direct dependency assertions, implement the one-shot
isolated scientific worker with its canonical request/response protocol and
controller result admission, preserve the exact eleven-owner graph and the
calendar science, and refreeze `ETF_PUBLICATION_CALENDAR_AUTHORITY_V1` before an
independent exact-hash calendar closure review. Only that closure PASS may
unblock POSTP1-001V2R1.

### Independent proof-architecture review result

POSTP1-002V2A-PAD4 independently reproduced exact parent
`cc1b325a...7b809e78`, all 17 material children mechanically enumerated from the
single builder registry, 17/17 child reproduction and 17/17 parent binding, the
frozen CPython 3.12.14 identity (`hexversion` 51121904, `cache_tag`
`cpython-312`, magic `cb0d0d0a`), the failed PAD3 parent `b8f8b92d...f6b5b996`,
the whole failed proof and calendar lineage, certified trusted-persistence
dependency `02f96203...1a12772`, the recursive 116-module project import closure
at digest `674b006a...3aadbb8` re-derived from an independent implementation,
the five non-stdlib distribution roots, the preserved compiled root-binding
witness, root-cell prohibition, closed AST store grammar, exact 11/11 owner
census and graph, the direct dependency-body rule and every unchanged
current-production blocker. All fifteen requested material mutations moved both
the owning child hash and the parent hash, and the parent reproduced under three
`PYTHONHASHSEED` values, reversed child order, an alternate working directory
and a fresh output directory that is byte-identical to the persisted namespace.
The focused PAD4 suite passed 77, the combined PAD4/PAD3/PAD2/PAD1-R1/PAD1 suite
passed 517, and the wider calendar, ETF, trusted-persistence and V1/V2 corpus
regression passed 1,279 with the three explained skips. `compileall` and
`git diff --check` are clean.

**The isolation boundary itself is sound and is not the defect.** Real
exec-launched worker processes were driven for every isolation probe. Parent
mutation of `_flow.FIVE_DAY_ETF_FLOW_FEATURE_ID`,
`_flow.FIVE_DAY_ETF_FLOW_WINDOW_DAYS`, the generated
`ScientificEtfFlowResult.__init__`, the `require_utc_datetime` re-export,
`sys.modules` and `builtins.sorted` each demonstrably corrupted the parent's own
evaluation while the worker returned the certified result unchanged; the
principal feature-ID probe reproduced parent `WRONG` against worker
`ETF_FLOW_5D`. A real `os.fork()` child inherited the mutation that exec does
not. `-I -S -B`, the frozen `LC_ALL`/`LANG`/`TZ` child environment, disabled user
site, unexecuted `sitecustomize`/`usercustomize`, ignored ambient `PYTHONPATH`,
parent-bound `sys.path`, the frozen three-operation registry, canonical
non-executable IPC, lazy-result refusal, one-request-one-process, result-digest
binding, timeout, crash, signal, extra-stdout and typed-exception handling, the
signing-key and `PYTHON*` environment refusals and the wrong-dependency-origin
refusal all failed closed.

The candidate nevertheless failed with
`FAIL — EXECUTED BYTECODE NOT BOUND TO CERTIFIED SOURCE`, plus three further
independent release-critical authority-anchoring defects.

1. **Executed bytecode is not bound to the certified `.py` source.** `-B` only
   suppresses bytecode *writes*; nothing suppresses or validates cached
   bytecode *reads*. A `__pycache__/flow.cpython-312.pyc` was forged under the
   frozen interpreter carrying different executable code while its timestamp
   invalidation header still matched the certified source. With the certified
   `btc_predictor/features/flow.py` bytes unchanged, its origin path unchanged
   and the request manifest digest exactly `674b006a...3aadbb8`, the real worker
   executed the forged bytecode and the controller admitted
   `feature_id: FORGED_BYTECODE_ID`. No `sys.pycache_prefix` isolation,
   hash-based invalidation requirement, `__cached__` check or `__pycache__`
   absence check exists anywhere in the architecture.
2. **`FAIL — CERTIFIED SOURCE AUTHORITY NOT FROZEN.`** `build_scientific_request`
   re-derives the manifest from live disk and
   `verify_project_source_manifest` only compares disk against that
   caller-supplied manifest. Mutating a certified project source file *before*
   request construction produced a new self-consistent digest
   (`36ccbc82...`, and `37b7ffa2...` for the semantic variant) that was
   admitted; the semantic variant admitted a drifted
   `feature_id: WRONG_DRIFTED_ID` in place of `ETF_FLOW_5D`. Post-request drift
   is correctly refused, so the frozen authority binds nothing before request
   time.
3. **`FAIL — CONTROLLER AUTHORITY BINDING INVALID.`** The worker echoes
   `payload["worker_authority_sha256"]` and `admit_worker_result` compares that
   echo with the same request value. `cc1b325a...7b809e78` appears in no
   executable file in the repository. Requests declaring
   `0000...0000` and `deadbeef...deadbeef` were both admitted with a real
   scientific result. `controller_result_admission_rule.json` materially claims
   `worker_authority_hash_is_controller_bound` and lists
   `worker_authority_identity` and `worker_source_manifest_identity` under
   `validated_before_admission`; echo comparison establishes neither.
4. **`FAIL — THIRD-PARTY INSTALLED CONTENT NOT ATTESTED` and
   `FAIL — THIRD-PARTY DEPENDENCY AUTHORITY NOT FROZEN.`**
   `verify_third_party_manifest` hashes only the `RECORD` file and never checks
   any installed file against the per-file hashes `RECORD` declares. With
   `RECORD` bytes unchanged and one executable installed dependency file
   modified, the tampered dependency code executed inside the worker and the
   result was admitted. Separately, the declared `version` is never compared to
   anything: a manifest declaring `99.99.99-FORGED` for all five distributions
   was admitted, so no reviewed semantic dependency authority exists.

The exact PAD4 candidate remains immutable, non-certified, unused and at zero
observations. No review fix, proof-artifact change or production change was
made, because authority anchoring itself is incomplete and section 65 forbids
patching it inside review. The fresh-exec process-isolation concept is **not**
rejected and same-process runtime-object attestation must **not** be reopened: a
`POSTP1-001V2A-PAD4-R1` that preserves this isolation boundary and repairs
executed-code binding, frozen source anchoring, controller authority anchoring
and third-party content attestation is the indicated path. A successor must also
resolve explicitly whether the exact 116-module manifest child is scientific
authority, because it is embedded in the parent hash and the I2-mandated
`common_etf_session_status` rewrite will necessarily move it. Calendar
implementation/refreeze, POSTP1-001V2R1, POSTP1-003R3, POSTP1-004 and collection
remain blocked; trusted persistence, calendar science, failed proof and calendar
lineage, BTC-019 and Epic T remain unchanged.

## POSTP1-001V2A-PAD4-R1 — `REPAIR_ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_AUTHORITY_ANCHORS_V1`

**Status:** `IMPLEMENTATION COMPLETE / FAILED INDEPENDENT EXACT-HASH FINAL
xHIGH PROOF-ARCHITECTURE REVIEW`
**Dependency:** POSTP1-002V2A-PAD4 failure,
`ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_REQUIRES_FIX`
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Required review:** POSTP1-002V2A-PAD4-R1, one independent exact-hash final
xHigh proof-architecture review
**Artifacts:** `prospective_evidence/etf_calendar_isolated_scientific_worker_v1_r1/`
**Decision commit:** `37f0db2b12c86b5809d213ae3bdda77a46cc82c2`
**Decision hash:** `3415765f63a902e415e039ea71892087274541c1e8976a46d41c8f4afde37ebc`

### A bounded correction, not a new architecture family

This is a correction of PAD4. No `POSTP1-001V2A-PAD5` was created, the failed
PAD4 parent `cc1b325a...7b809e78` keeps its own untouched namespace and remains
failed, non-certified, unused, immutable, superseded before use and at zero
observations, and the whole failed lineage `0c237c1b...887b55d`,
`a7d2b087...534dd0`, `dc36ffe2...f1372c3e`, `9f6af179...7ac86295`,
`7ef114fe...8d17b`, `b5ca36bf...b2a8abe9`, `b8f8b92d...f6b5b996` and
`cc1b325a...7b809e78` is preserved unchanged. Same-process runtime-owner
attestation, transitive mutable-object closure, reflection-blacklist
completeness and generated-method enumeration are explicitly **not** reopened.

POSTP1-002V2A-PAD4 found the fresh-exec process-isolation boundary **sound**,
so the proven closed input boundary is preserved verbatim: a fresh exec'd
CPython 3.12.14 worker under `-I -S -B`, one request per process, no parent
Python object sharing, canonical JSON IPC, no pickle/cloudpickle/dill/marshal
IPC, lazy-result refusal, controller result admission, fork-only refusal and
parent monkeypatch isolation. The corrected proof strategy is
`CERTIFIED_SOURCE_AUTHORITY + FROZEN_THIRD_PARTY_ARTIFACT_AUTHORITY +
FROZEN_CPYTHON + FRESH_EMPTY_BYTECODE_CACHE_NAMESPACE + CLOSED_STORE_GRAMMAR +
COMPILED_ROOT_WITNESS + ONE_SHOT_EXEC_ISOLATED_SCIENTIFIC_WORKER +
TRUSTED_CONTROLLER_AUTHORITY_CONTEXT`, frozen across 20 mechanically enumerated
parent-bound children.

### Repair A — executed bytecode is bound to certified source

`-B` suppresses bytecode *writes* only; nothing suppressed or validated
bytecode *reads*, so a forged timestamp-valid
`__pycache__/flow.cpython-312.pyc` executed while the certified `.py` bytes,
origin and manifest digest were all unchanged. Every worker now additionally
runs under `-X pycache_prefix=<fresh empty per-worker directory>`. The
namespace is controller-created, proven empty before launch, never shared with
any repository or `site-packages` `__pycache__`, never reused between workers,
never selected from the scientific request and removed after the worker exits.
Before it imports even the certified protocol module the entrypoint refuses
unless `sys.pycache_prefix` is exactly the declared namespace,
`sys.dont_write_bytecode` is `True` and the namespace is empty; the protocol
module re-verifies the same property as the owning authority, and every loaded
certified and reviewed-dependency module's `__cached__` must lie inside the
namespace. The exact `__file__`/`__spec__.origin` source-path checks are
preserved, because a *sourceless* `flow/__init__.pyc` package shadow is not
covered by a cache namespace at all. The cache path is operational launch
material and is deliberately not scientific identity evidence.

### Repair B — frozen certified source authority

Authority construction and runtime are now two distinct operations. Mechanical
derivation — the reviewed recursive static import closure, nested declarations
followed, ancestor packages included — is used only for authority construction,
refreeze, review and consistency checking. Runtime consumes an already-frozen
expected manifest and compares module, relative path, SHA-256 and manifest
digest exactly; unknown, missing, additional or altered entries refuse. The
request builder has no manifest parameter, so source drift that exists before
request construction leaves the request bound to the frozen expected values and
the worker refuses the drifted disk instead of self-certifying.

The exact 116-module universe at `674b006a...3aadbb8` is frozen as
`ETF_CALENDAR_WORKER_PRE_I2_SOURCE_MANIFEST_FIXTURE_V1` with role
`PRE_I2_CONFORMANCE_FIXTURE_AND_PROVENANCE`: an architecture conformance test
vector, provenance and a pre-I2 source-drift regression anchor. It is
explicitly **not** the future production scientific source authority, and it is
embedded as literal material so it stays immutable when I2 changes source. The
candidate worker universe is 119 modules at `c6a71401...7aa89332`, adding the
three corrected worker-owned modules. POSTP1-001V2A-I2 **must** derive the
exact final worker project-source manifest after all its source changes are
complete and parent-bind that exact manifest to
`ETF_PUBLICATION_CALENDAR_AUTHORITY_V1`. I2 may perform the anticipated
direct-import reduction provided the calendar science, the outputs and the
replay-owner graph are unchanged and the manifest is mechanically re-derived;
the proof-architecture hash does not change merely because the production
manifest narrows.

### Repair C — the trusted controller authority context

PAD4 admitted a result when the worker echoed `worker_authority_sha256` back to
the request. `ScientificWorkerAuthorityContext` now holds the trusted expected
proof-architecture identity, source manifest and digest, third-party
semantic/artifact authority, frozen interpreter identity, calendar authority
identity and trusted-persistence identity. A request cannot construct it, a
response cannot construct it, live disk cannot silently replace it and the
installed environment cannot silently replace it. `build_scientific_request`
takes the context and copies the authority fields from it; there is no raw
`decision_sha256` parameter. Admission requires request equals context **and**
response equals context **and** response cross-binds to the request: caller,
request and worker agreeing with each other is necessary but never sufficient.

The candidate parent hash cannot be materially embedded inside itself and no
cryptographic self-hash fixed point is attempted. The architecture uses a
two-stage boundary: the reviewer or harness instantiates the context with the
recomputed parent hash, which comes from the trusted review context and never
from the scientific request. `production_authority_context_from_calendar_authority`
refuses today with `PRODUCTION_AUTHORITY_CONTEXT_NOT_YET_BOUND_BY_POSTP1_001V2A_I2`,
because the production context must be derived from the final calendar
authority, never from the request, the current filesystem, the ambient
environment or a caller-selected SHA.

### Repair D — third-party semantic and installed-content authority

The exact reviewed registry is frozen: `alembic` 1.19.1, `cryptography` 50.0.1,
`numpy` 2.5.2, `scipy` 1.18.1 and `SQLAlchemy` 2.0.52, each with its canonical
distribution name, expected root module, reviewed `RECORD` SHA-256, normalized
`RECORD` content-manifest digest and row counts. Distribution, version,
reviewed artifact identity and root-module mapping are parent-bound; absolute
install location and `RECORD` path stay launch-bound, so semantic authority is
portable while installation material is not. An observed version that differs
from the reviewed version refuses, and a same-version but different unreviewed
artifact refuses because the reviewed `RECORD` identity is parent-bound.

Before any scientific project import, the worker parses each reviewed `RECORD`
with bounded deterministic CSV parsing, refuses an unreviewed hash algorithm
rather than skipping it, resolves each row safely — absolute paths, Windows
separators, `.` segments and interior traversal refuse, leading parent segments
are permitted only for console-script rows that stay inside the installation
environment — and verifies every declared file's bytes and size, including
compiled extension and shared-library rows. The only reviewed unhashed-row
exceptions are the distribution's own `RECORD`, whose exact bytes are
parent-bound, and install-generated `__pycache__` bytecode, which is
structurally unreachable under the enforced fresh cache namespace; any other
unhashed installed file refuses. This ordering is why the corrected protocol
lives in `etf_calendar_worker` rather than under `btc_predictor`: importing
`btc_predictor` executes `numpy`, `scipy`, `sqlalchemy` and `alembic` through
its re-export graph, so a protocol module inside the application package could
only attest dependencies after they had already run.

### Executed adversarial evidence

The focused suite passed 100 tests driving real exec'd worker processes, the
combined PAD4-R1/PAD4/PAD3/PAD2/PAD1-R1/PAD1 proof-architecture suite passed
617, and the wider calendar, ETF, trusted-persistence and V1/V2 corpus
regression passed 1,453 with the three explained skips. A
side-by-side probe reproduced the PAD4 defect exactly — `-I -S -B` alone
executes a forged `.pyc` as `FORGED_BYTECODE_ID` — and the same tree returned
`CERTIFIED` under a fresh cache namespace. A real worker over a forged
repository `__pycache__/flow.cpython-312.pyc`, with `flow.py` byte-identical to
the certified source, returned `ETF_FLOW_5D`. A forged
`alembic/__pycache__/__init__.cpython-312.pyc` never executed its marker. A
pre-populated namespace refused before the certified protocol module was
imported, a sourceless `flow/__init__.pyc` shadow refused on the origin check,
and a `.pyc`-only project module could not satisfy the frozen manifest.
Pre-request drift of `flow.py`, of both corrected worker modules and of both
reviewed PAD4 worker modules all refused while the request stayed bound to the
frozen digest. `0000...0000` and `deadbeef...deadbeef` were refused with the
worker echoing them consistently, and a context expecting a different hash
refused an otherwise correct request. A `99.99.99-FORGED` version, a
same-version different-artifact `RECORD` and a tampered installed
`alembic/__init__.py` with unchanged `RECORD` all refused before the altered
code executed, proven by an absent execution marker. Parent mutation of
`_flow.FIVE_DAY_ETF_FLOW_FEATURE_ID`, of the generated
`ScientificEtfFlowResult.__init__` and of `sys.modules` each left the worker
result certified, and a real `os.fork()` child still inherits what exec does
not.

### Recorded limits

Hostile filesystem race resistance is explicitly **not** claimed: a malicious
modification perfectly racing verification or use is outside the accepted
trusted-operating-system boundary, and the requirement is deterministic project
and deployment integrity, not hostile kernel defence. No operating-system-level
network sandbox is claimed and none was added; the no-network, no-signing-key
and no-database guarantees still rest on the frozen read-only operation
registry, the frozen minimal child environment and the static closed
worker-source prohibition. The dynamic-import claim is scoped precisely:
authoritative worker entry/protocol dynamic project execution is forbidden and
statically audited, the certified universe is mechanically derived from static
import declarations, an unexpected loaded project module refuses, and the
per-module dynamic-construct scan of the current certified universe is recorded
as a verified current-source fact rather than an eternal universal claim.

### Preserved authority and current production

The compiled root-binding witness, the root-cell prohibition, the closed AST
store-use grammar, the exact eleven-owner census and graph, the documented
`put`/`get`/`records`/`envelopes` terminals and the direct dependency-body
requirement are preserved and freshly parent-bound. No ETF calendar production
code was modified: current production still reports zero compiled root writes,
clears or deletes, the single `common_etf_session_status` generator capture, the
same closed-grammar refusal, the five wrapper-installed dependency guards and no
isolated worker, so full conformance is `NO` and the implementation stays
blocked. Trusted persistence `02f96203...1a12772` is closed, certified,
unchanged and not re-reviewed. Calendar science, failed calendar lineage,
BTC-019 and Epic T are unchanged. No observation was collected and no real
Stage-B evaluation ran.

Final classification is
`ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_R1_READY_FOR_FINAL_XHIGH_REVIEW`.
Successful implementation authorizes only POSTP1-002V2A-PAD4-R1. Only that
review PASS may authorize POSTP1-001V2A-I2, which must then bind the exact
certified PAD4-R1 hash into the final calendar authority, rewrite the
`common_etf_session_status` generator capture, remove the wrapper-installed
guards, insert the five direct dependency assertions, derive and
calendar-parent-bind the final post-I2 project source manifest, instantiate the
production controller authority context from those certified values, integrate
the one-shot worker, preserve the exact eleven-owner graph and the calendar
science, and refreeze `ETF_PUBLICATION_CALENDAR_AUTHORITY_V1` before an
independent exact-hash calendar closure review. Only that closure PASS may
unblock POSTP1-001V2R1.

## POSTP1-002V2A-PAD4-R1 — `FINAL_XHIGH_PROOF_ARCHITECTURE_REVIEW_ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_R1`

**Status:** `COMPLETE / FAIL`
**Reviewed ticket:** POSTP1-001V2A-PAD4-R1
**Reviewed decision commit:** `37f0db2b12c86b5809d213ae3bdda77a46cc82c2`
**Reviewed authority:** `3415765f63a902e415e039ea71892087274541c1e8976a46d41c8f4afde37ebc`
**Review model:** independent exact-hash final xHigh proof-architecture review
of the exact corrected worker hash
**Review result:** `FAIL — WORKER BOOTSTRAP SOURCE NOT BOUND BEFORE EXECUTION`
**Execution classification:** `ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_R1_REQUIRES_FIX`

Independent canonical-JSON regeneration reproduced the exact candidate parent
`3415765f63a902e415e039ea71892087274541c1e8976a46d41c8f4afde37ebc`. All 20
material children mechanically enumerated from the single builder registry
reproduce: 20/20 child reproduction and 20/20 parent binding.

### Independently reproduced valid portions

These portions were independently reproduced and are preserved. A successor
must not reopen, rebuild or renegotiate them.

- **Fresh-exec isolation — VALID.** The one-shot exec'd worker boundary that
  POSTP1-002V2A-PAD4 already found sound reproduces again and remains the
  proven closed input boundary.
- **Repair A — bytecode binding — VALID.** The fresh, controller-created,
  empty per-worker `-X pycache_prefix` namespace closes the PAD4 forged-`.pyc`
  defect.
- **Repair C — trusted controller authority — VALID FOR ITS STATED SCOPE**,
  but unable to close bootstrap ordering because worker-visible authority
  fields are derivable from the supplied request. Within its stated scope
  `ScientificWorkerAuthorityContext` is genuine trusted material that a
  request, a response, live disk and the installed environment cannot
  construct or silently replace, and admission does require request equals
  context and response equals context and response cross-binds to request.
  What it does not do is hand already-executing bootstrap code an authority
  that code could not have reconstructed from its own input.
- **Repair D — third-party semantic/content authority — VALID.** The exact
  reviewed five-distribution semantic registry and the per-file
  installed-content verification against the parent-bound `RECORD` identity
  hold.
- **Repair B — frozen source authority — VALID FOR ORDINARY CERTIFIED SOURCE,
  INCOMPLETE FOR THE PRE-TRUST BOOTSTRAP SOURCES.** Runtime consumption of an
  already-frozen expected manifest, with no request manifest parameter and no
  runtime re-derivation, is correct for every certified project module the
  verifier is in a position to check. It does not reach the modules that must
  already have run in order for that verifier to exist.

### Blocking invariant

Already-trusted code does not establish the certified identity of the worker
bootstrap source before that source executes.

The controller allocates the fresh cache namespace, builds the parent-bound
launch material and execs the entrypoint path directly. The frozen expected
manifest is compared against disk inside the worker, by the worker's own
protocol module. Every module that must execute to reach that comparison is
therefore outside it: the manifest check is the first thing the bootstrap
does, not the last thing the controller does. The already-trusted side of the
boundary never hashes the bootstrap files it is about to run.

### Bootstrap package surface

- `etf_calendar_worker/entry_r1.py`
- `etf_calendar_worker/__init__.py`
- `etf_calendar_worker/protocol_r1.py`

This set executes before the normal scientific verifier is trustworthy. The
package `__init__.py` is on the surface because importing the protocol module
executes it first; it is not covered by the `worker_entrypoint_sha256` and
`worker_protocol_sha256` fields, and those two fields are in any case verified
by code that has already run.

### Stable pre-launch bootstrap drift

Two stable pre-launch drift probes were executed against the exact frozen
candidate. In each case the drift was introduced before launch and left in
place across the whole request.

- **Entrypoint drift:** marker **PRESENT**, fabricated scientific result
  **ADMITTED**.
- **Protocol drift:** marker **PRESENT**, fabricated scientific result
  **ADMITTED**.

The execution marker proves the drifted bootstrap module really ran, and the
controller then admitted a fabricated scientific result. Pre-launch bootstrap
drift is therefore not merely undetected; it is authoritative. This is the
precise ordering complement of the POSTP1-002V2A-PAD4 pre-request source-drift
finding that Repair B otherwise closes: Repair B moved the certified-source
authority ahead of request construction, but the bootstrap source is ahead of
Repair B.

### Consequences

The exact PAD4-R1 candidate remains immutable, non-certified, unused and at
zero observations. No review fix, proof-artifact change, production change,
calendar-science change or candidate-authority change was made, because
authority ordering itself is incomplete and a review may not patch the
authority it is reviewing. The isolated-worker proof-architecture family is
**not** rejected, same-process runtime-object attestation must **not** be
reopened, and the validated isolation, bytecode and third-party repairs must
be carried forward intact.

Calendar implementation/refreeze (POSTP1-001V2A-I2), POSTP1-001V2R1,
POSTP1-003R3 and POSTP1-004 remain **BLOCKED**. Collection is **NOT
AUTHORIZED** and observations remain **0**. No prospective observation was
collected and no real Stage-B evaluation ran. Certified trusted persistence
`02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772` is
**CLOSED / CERTIFIED / UNCHANGED** and was not reopened. Calendar science, the
failed proof and calendar lineage, the untouched failed PAD4 namespace at
`cc1b325a...7b809e78`, BTC-019 (**UNTOUCHED**, sealed sample unopened) and
Epic T (**UNCHANGED**) are all unaffected.

### Indicated successor

`POSTP1-001V2A-PAD4-R2` — a bounded correction that pre-verifies the complete
worker bootstrap source set in already-trusted controller code before
subprocess execution, while preserving the validated PAD4-R1 isolation,
bytecode and third-party repairs.

This is a bounded correction of PAD4-R1 and is deliberately **not** a PAD5: no
new proof-architecture family is authorized and the R1 namespace stays
immutable and preserved alongside the failed PAD4 namespace. Successful
POSTP1-001V2A-PAD4-R2 implementation authorizes only its own independent
exact-hash review; only that review's PASS may authorize POSTP1-001V2A-I2.

### Documentation-only correction made by this review

This review also independently identified one documentation-only defect:
`CURRENT_STATE.md` recorded the combined
PAD4-R1/PAD4/PAD3/PAD2/PAD1-R1/PAD1 proof-architecture suite as **615** where
the measured count is **617**, which this record corrects. No unrelated
historical test count was altered, and no wider or full test rerun was
required for this documentation-only review record.

## POSTP1-001V2A-PAD4-R2 — `BIND_ETF_CALENDAR_WORKER_BOOTSTRAP_SOURCE_BEFORE_EXECUTION_V1`

**Status:** `IMPLEMENTATION COMPLETE / AWAITING INDEPENDENT EXACT-HASH FINAL
xHIGH PROOF-ARCHITECTURE REVIEW`
**Dependency:** POSTP1-002V2A-PAD4-R1 failure,
`ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_R1_REQUIRES_FIX`
**Implementation model:** GPT-5.6 Sol — Extra High (xHigh)
**Required review:** POSTP1-002V2A-PAD4-R2, one independent exact-hash final
xHigh proof-architecture review
**Artifacts:** `prospective_evidence/etf_calendar_isolated_scientific_worker_v1_r2/`
**Decision commit:** `d6b5565a7006eec323e990d906e3a1240a2ee807`
**Decision hash:** `68e6bd074a027900b2f3dde3da0a31b6d1cb2f1b9fc6c563e9b45bdc70e52561`

### A bounded ordering correction, not a new architecture family

No `POSTP1-001V2A-PAD5` was created. The failed `PAD4` parent
`cc1b325a...7b809e78` and the failed `PAD4-R1` parent `3415765f...fde37ebc`
both keep their own untouched namespaces and both remain failed, non-certified,
unused, immutable, superseded before use and at zero observations; the whole
failed lineage `0c237c1b...887b55d`, `a7d2b087...534dd0`,
`dc36ffe2...f1372c3e`, `9f6af179...7ac86295`, `7ef114fe...8d17b`,
`b5ca36bf...b2a8abe9`, `b8f8b92d...f6b5b996`, `cc1b325a...7b809e78` and
`3415765f...fde37ebc` is preserved unchanged. Same-process runtime-owner
attestation is explicitly **not** reopened, and the `-X pycache_prefix` launch
design is explicitly **not** redesigned.

The five portions `POSTP1-002V2A-PAD4-R1` independently reproduced as valid are
carried forward intact rather than rebuilt: fresh-exec isolation, the Repair A
fresh empty per-worker bytecode-cache namespace, the Repair C trusted
controller authority context within its stated scope, the Repair D third-party
semantic and installed-content authority, and the Repair B frozen source
authority for ordinary certified source. The corrected proof strategy is
`BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING + CERTIFIED_SOURCE_AUTHORITY +
FROZEN_THIRD_PARTY_ARTIFACT_AUTHORITY + FROZEN_CPYTHON +
FRESH_EMPTY_BYTECODE_CACHE_NAMESPACE + CLOSED_STORE_GRAMMAR +
COMPILED_ROOT_WITNESS + ONE_SHOT_EXEC_ISOLATED_SCIENTIFIC_WORKER +
TRUSTED_CONTROLLER_AUTHORITY_CONTEXT`, frozen across 22 mechanically enumerated
parent-bound children.

### The exact failed invariant

```text
NO PROJECT-OWNED WORKER BOOTSTRAP SOURCE MAY EXECUTE UNTIL ALREADY-TRUSTED
CONTROLLER CODE HAS ESTABLISHED ITS EXPECTED PATH AND SOURCE SHA AGAINST THE
TRUSTED ScientificWorkerAuthorityContext.
```

`PAD4-R1` compared the frozen expected manifest against disk *inside the
worker, by the worker's own protocol module*, so every module that had to
execute to reach that comparison was outside it. This is an authority-ordering
defect; fresh-process isolation itself remains valid.

### The complete pre-trust bootstrap source set

The set is derived mechanically — the transitive static project-import closure
of the exec'd entrypoint restricted to the authoritative worker package, plus
every ancestor package — and it is deliberately wider than the two filenames
the review named. In execution order it is
`etf_calendar_worker/__init__.py`, `etf_calendar_worker/protocol_r1.py`,
`etf_calendar_worker/protocol_r2.py` and `etf_calendar_worker/entry_r2.py`,
four files at `1811e04d...ead411`. The package initializer is a member because
importing the protocol executes it first and neither `worker_entrypoint_sha256`
nor `worker_protocol_sha256` covered it. The reviewed `PAD4-R1` protocol
implementation is reused rather than forked, so `protocol_r1.py` executes
during bootstrap and is pre-verified with the rest of the set; every reviewed
verification routine is therefore inherited unchanged instead of restated.
Every member is also an ordinary member of the certified 120-module source
manifest with the identical path and SHA-256, so the bootstrap manifest is not
a second, weaker source of truth.

Completeness is proven rather than asserted, by four mechanical properties: no
bootstrap module declares a module-level project import outside the set; no
bootstrap module declares a module-level import outside the standard library,
so no third-party code can run before the reviewed installed-content
attestation; every deferred, function-scoped certified import declared by a
bootstrap module is an ordinary certified manifest member that Repair B covers;
and every deferred loader in the entrypoint is called strictly after the
bootstrap, certified-source and third-party verifiers, enforced by AST
statement order rather than by comment. Moving `_load_calendar` above
`verify_project_source_manifest` refuses. The closed worker-coding rule is now
scoped to the whole bootstrap set instead of two filenames.

### Trusted controller pre-execution binding

`run_scientific_worker(authority_context, request, launch)` is the only
supported scientific launch path and the trusted context is a required
positional argument, so pre-verification is unavoidable. Before any process
exists the controller receives the trusted context, takes the expected
bootstrap manifest from it, resolves each source beneath the certified project
root, reads the exact bytes, computes SHA-256, compares path and SHA, and
raises `BootstrapSourcePreVerificationError` on any mismatch — before the fresh
cache namespace is allocated and before `subprocess.run` is reached. Per source
it checks the expected relative path, the resolved expected project root, the
absence of any alternate source candidate, the absence of a sourceless bytecode
replacement, regular certified-source file semantics, the absence of an earlier
`sys.path` entry that would shadow the worker package, and the exact SHA-256.
Module name alone is never identity. `_spawn_unverified_worker_process` remains
as a private, non-authoritative raw helper that scientific admission never
uses.

The request and response schemas move to `..._V1_R2`: the two ad-hoc
`worker_entrypoint_sha256` and `worker_protocol_sha256` fields are replaced by
the complete `worker_bootstrap_manifest` and its digest, which is
authority-bound on both the request and the response. In-worker bootstrap
checks remain as declared defence in depth:
`bootstrap_self_verification_is_authority`,
`entrypoint_self_verification_is_authority`,
`protocol_self_verification_is_authority` and
`package_initializer_self_verification_is_authority` are all `false`, and no
worker-visible shared secret was invented as a substitute for correct pre-exec
ordering.

### Executed adversarial evidence

The focused suite passed 89 tests driving real exec'd worker processes. Stable
pre-launch drift of each of the four bootstrap sources, introduced before
launch and left in place across the whole request, was driven through the
ordinary authoritative controller path: in every case the subprocess was
**never spawned**, the execution marker was **ABSENT**, no response was emitted
and nothing was admitted, and no cache namespace was even allocated. The
reproduction control proves the drift is real and that self-verification cannot
be authority: through the private non-authoritative helper the same trees
execute their markers, and the drifted entrypoint, `protocol_r1.py` and
`protocol_r2.py` each have a fabricated scientific result **ADMITTED**, because
a drifted protocol module owns the worker's own `file_sha256` and canonical
serializer and makes the in-worker restatement report itself certified. The
clean positive control pre-verifies, launches and admits the honest result.

A missing bootstrap source, a sourceless `protocol_r2.pyc` replacement, a
competing `etf_calendar_worker.py` module shadow, an alternate worker package
earlier on `sys.path`, a wrong entrypoint path and a symlinked bootstrap source
all refuse before launch. The preserved regressions still hold: a forged
repository `__pycache__/flow.cpython-312.pyc` is not executed, a forged
`etf_calendar_worker/__pycache__/protocol_r2.cpython-312.pyc` marker stays
absent, a pre-populated cache namespace refuses, a sourceless `flow/__init__.pyc`
shadow refuses on the origin check, ordinary pre-request certified-source drift
refuses, `0000...0000` and `deadbeef...deadbeef` are refused with the worker
echoing them consistently, a `99.99.99-FORGED` version refuses, a tampered
installed `alembic/__init__.py` with unchanged `RECORD` refuses with its marker
absent, and parent mutation of `_flow.FIVE_DAY_ETF_FLOW_FEATURE_ID` and of
`sys.modules` leave the worker result unaffected. The shared `.venv312`
mutation regression is serialized and restores under `finally`.

### Secondary review findings, reproduced and reclassified

Neither secondary candidate was accepted uninspected. That
`candidate_review_authority_context` accepts any well-formed SHA was
independently reproduced and **reclassified as not a defect**: constraining the
constructor to one literal value is exactly the self-hash fixed point this
architecture refuses, the hash's trust comes from the caller being the trusted
review or controller context, and the production context is derived from the
final calendar authority instead. The reason is frozen in
`controller_authority_context_rule` and behaviour is unchanged. The
`worker_protocol_placement_reason` wording was reproduced mechanically —
importing the top-level `btc_predictor` namespace alone executes none of the
four reviewed distributions, while importing `btc_predictor.research`, which
every frozen operation requires, executes all four — and corrected as a
documentation wording change that alters no proof architecture.

### Preserved authority and current production

The 116-module manifest keeps its
`PRE_I2_CONFORMANCE_FIXTURE_AND_PROVENANCE` role at `674b006a...3aadbb8` and is
still not production authority; the candidate worker universe is 120 modules.
The compiled root-binding witness, the root-cell prohibition, the closed AST
store-use grammar, the exact eleven-owner census and graph, the documented
`put`/`get`/`records`/`envelopes` terminals and the direct dependency-body
requirement are preserved and freshly parent-bound. No ETF calendar production
code was modified: `etf_publication_calendar.py`, the calendar science, the
`CalendarEvidenceStore` production implementation, the
`common_etf_session_status` generator capture, the wrapper guards and the five
direct dependency bodies are unchanged and remain I2 work, so full conformance
is `NO` and the implementation stays blocked. Trusted persistence
`02f96203...1a12772` is closed, certified, unchanged and not re-reviewed.
Calendar science, the failed lineage, BTC-019 and Epic T are unchanged. No
observation was collected and no real Stage-B evaluation ran.

Final classification is
`ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_R2_READY_FOR_FINAL_XHIGH_REVIEW`.
Successful implementation authorizes only POSTP1-002V2A-PAD4-R2. Only that
review PASS may authorize POSTP1-001V2A-I2, which must then bind the certified
`PAD4-R2` hash into the final calendar authority, rewrite the
`common_etf_session_status` generator capture, remove the wrapper-installed
guards, insert the five direct dependency assertions, derive and
calendar-parent-bind both the final post-I2 project source manifest **and** the
final post-I2 bootstrap source set, instantiate the production controller
authority context from those certified values, integrate the one-shot worker,
preserve the exact eleven-owner graph and the calendar science, and refreeze
`ETF_PUBLICATION_CALENDAR_AUTHORITY_V1` before an independent exact-hash
calendar closure review. Only that closure PASS may unblock POSTP1-001V2R1.

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
| POSTP1-001V2A-R1 | source-derived correction/refreeze of `ETF_PUBLICATION_CALENDAR_AUTHORITY_V1` at `b81c1702...b357af` | IMPLEMENTATION COMPLETE / FAILED REPEAT INDEPENDENT EXACT-HASH xHIGH REVIEW |
| POSTP1-002V2A-R1 | repeat independent exact-hash review of `b81c1702...b357af` | COMPLETE / FAIL — ETF CALENDAR SOURCE ORIGIN AUTHORITY INVALID |
| POSTP1-001V2A-R2 | final trusted-origin/parser-completeness correction at `05243343...f99c855` | IMPLEMENTATION COMPLETE / FAILED FINAL INDEPENDENT EXACT-HASH xHIGH REVIEW |
| POSTP1-002V2A-R2 | final independent exact-hash review of `05243343...f99c855` | COMPLETE / FAIL — TRUSTED ORIGIN BOUNDARY INVALID; EXPLICIT ARCHITECTURE/AUTHORITY DECISION REQUIRED |
| POSTP1-001V2B | freeze Ed25519 signed-envelope and collector-only PostgreSQL persistence authority at `c3619b7a...223554` | IMPLEMENTATION COMPLETE / FAILED INDEPENDENT EXACT-HASH xHIGH REVIEW |
| POSTP1-002V2B | independent exact-hash xHigh review of `c3619b7a...223554` | COMPLETE / FAIL — TRUST REGISTRY INJECTION INVALID; DURABILITY, EXECUTABLE-BINDING AND ROLE-PROVISIONING BOUNDARIES ALSO INVALID |
| POSTP1-001V2B-R1 | bounded correction/refreeze at `240985bf...e7bd0` | IMPLEMENTATION COMPLETE / FAILED REPEAT INDEPENDENT EXACT-HASH xHIGH REVIEW |
| POSTP1-002V2B-R1 | repeat independent exact-hash xHigh review of `240985bf...e7bd0` | COMPLETE / FAIL — PRODUCTION VERIFICATION AUTHORITY INVALID; DATABASE IDENTITY BOUNDARY ALSO INVALID |
| POSTP1-001V2B-R2 | final bounded runtime-material/database-identity correction at `bd55a3c0...02c4fc` | IMPLEMENTATION COMPLETE / FAILED FINAL INDEPENDENT EXACT-HASH xHIGH REVIEW |
| POSTP1-002V2B-R2 | final independent exact-hash xHigh review of `bd55a3c0...02c4fc` | COMPLETE / FAIL — DATABASE IDENTITY AUTHORITY INVALID |
| POSTP1-001V2B-R3 | final database-authority runtime-identifier binding at `02f96203...1a12772` | DONE / PASSED FINAL INDEPENDENT EXACT-HASH xHIGH CLOSURE REVIEW |
| POSTP1-002V2B-R3 | final independent exact-hash xHigh closure review of `02f96203...1a12772` | COMPLETE / PASS |
| POSTP1-001V2A-I1 | bind the calendar authority to certified trusted-persistence hash `02f96203...1a12772` and refreeze at `b499c6a4...e584e076` | IMPLEMENTATION COMPLETE / FAILED INDEPENDENT EXACT-HASH xHIGH INTEGRATION CLOSURE REVIEW |
| POSTP1-002V2A-I1 | independent exact-hash xHigh integration closure review of `b499c6a4...e584e076` | COMPLETE / FAIL — CALENDAR DEPENDENCY CALL-SITE CLOSURE INVALID |
| POSTP1-001V2A-I1-R1 | close every authoritative calendar exact-dependency call site and refreeze at `901f572e...fd9853f` | IMPLEMENTATION COMPLETE / FAILED INDEPENDENT EXACT-HASH xHIGH CALL-SITE CLOSURE REVIEW |
| POSTP1-002V2A-I1-R1 | independent exact-hash xHigh call-site closure review of `901f572e...fd9853f` | COMPLETE / FAIL — CALL-SITE GUARD BYPASS INVALID; EXPLICIT ARCHITECTURE DECISION REQUIRED |
| POSTP1-001V2A-AD1 | define and freeze the trusted-process scientific authority boundary at `0c237c1b...887b55d` | IMPLEMENTATION COMPLETE / FAILED INDEPENDENT xHIGH ARCHITECTURE REVIEW |
| POSTP1-002V2A-AD1 | independent exact-hash xHigh architecture review of `0c237c1b...887b55d` | COMPLETE / FAIL — PROJECT-OWNED BYPASS MODEL INCOMPLETE |
| POSTP1-001V2A-AD1-R1 | complete the project-owned private-state bypass model and exact replay-owner census at `a7d2b087...534dd0` | IMPLEMENTATION COMPLETE / FAILED INDEPENDENT EXACT-HASH xHIGH ARCHITECTURE RE-REVIEW |
| POSTP1-002V2A-AD1-R1 | independent exact-hash xHigh architecture re-review of `a7d2b087...534dd0` | COMPLETE / FAIL — TRANSITIVE REPLAY CLOSURE INVALID; BOUNDED ARCHITECTURE CORRECTION REQUIRED |
| POSTP1-001V2A-AD1-R2 | enforce universal replay-route closure and variadic owner discovery at `dc36ffe2...f1372c3e` | IMPLEMENTATION COMPLETE / FAILED INDEPENDENT EXACT-HASH FINAL xHIGH ARCHITECTURE REVIEW |
| POSTP1-002V2A-AD1-R2 | independent exact-hash final xHigh architecture review of `dc36ffe2...f1372c3e` | COMPLETE / FAIL — UNIVERSAL EDGE CLASSIFICATION INCOMPLETE; EXPLICIT PROOF-ARCHITECTURE DECISION REQUIRED |
| POSTP1-001V2A-PAD1 | define and freeze the closed `ETF_CALENDAR_STORE_CAPABILITY_NORMAL_FORM_V1` proof architecture at `9f6af179...7ac86295` | IMPLEMENTATION COMPLETE / FAILED INDEPENDENT EXACT-HASH xHIGH PROOF-ARCHITECTURE REVIEW |
| POSTP1-002V2A-PAD1 | independent exact-hash xHigh proof-architecture review of `9f6af179...7ac86295` | COMPLETE / FAIL — CLOSED GRAMMAR COMPLETENESS INVALID; CORRECTED PROOF ARCHITECTURE REQUIRED |
| POSTP1-001V2A-PAD1-R1 | narrow the corrected direct immutable-parameter proof architecture at `7ef114fe...8d17b` | IMPLEMENTATION COMPLETE / FAILED INDEPENDENT EXACT-HASH FINAL xHIGH REVIEW |
| POSTP1-002V2A-PAD1-R1 | independent exact-hash final xHigh proof-architecture review of `7ef114fe...8d17b` | COMPLETE / FAIL — PYTHON 3.12 BINDING CENSUS INCOMPLETE; EXPLICIT PROOF-ARCHITECTURE DECISION REQUIRED |
| POSTP1-001V2A-PAD2 | define and freeze the new `ETF_CALENDAR_COMPILED_BINDING_WITNESS_V1` proof architecture at `b5ca36bf...b2a8abe9` | IMPLEMENTATION COMPLETE / FAILED INDEPENDENT EXACT-HASH xHIGH PROOF-ARCHITECTURE REVIEW |
| POSTP1-002V2A-PAD2 | independent exact-hash xHigh proof-architecture review of `b5ca36bf...b2a8abe9` | COMPLETE / FAIL — MODULE OWNER IDENTITY MODEL INCOMPLETE; EXPLICIT BOUNDED PROOF-ARCHITECTURE DECISION REQUIRED |
| POSTP1-001V2A-PAD3 | define and freeze the new `ETF_CALENDAR_RUNTIME_OWNER_ATTESTATION_V1` proof architecture at `b8f8b92d...f6b5b996` | IMPLEMENTATION COMPLETE / FAILED INDEPENDENT EXACT-HASH xHIGH PROOF-ARCHITECTURE REVIEW |
| POSTP1-002V2A-PAD3 | independent exact-hash xHigh proof-architecture review of `b8f8b92d...f6b5b996` | COMPLETE / FAIL — PROJECT IMPORT EXECUTION CLOSURE INCOMPLETE; EXPLICIT PROOF-ARCHITECTURE DECISION REQUIRED |
| POSTP1-001V2A-PAD4 | define and freeze the new `ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1` proof architecture at `cc1b325a...7b809e78` | IMPLEMENTATION COMPLETE / FAILED INDEPENDENT EXACT-HASH xHIGH PROOF-ARCHITECTURE REVIEW |
| POSTP1-002V2A-PAD4 | independent exact-hash xHigh proof-architecture review of `cc1b325a...7b809e78` | COMPLETE / FAIL — EXECUTED BYTECODE NOT BOUND TO CERTIFIED SOURCE; SOURCE, CONTROLLER-AUTHORITY AND THIRD-PARTY ANCHORING ALSO INVALID; ISOLATION BOUNDARY SOUND |
| POSTP1-001V2A-PAD4-R1 | bounded correction of the four POSTP1-002V2A-PAD4 authority-anchoring findings, refrozen at `3415765f...fde37ebc` | IMPLEMENTATION COMPLETE / FAILED INDEPENDENT EXACT-HASH FINAL xHIGH PROOF-ARCHITECTURE REVIEW |
| POSTP1-002V2A-PAD4-R1 | independent exact-hash final xHigh proof-architecture review of `3415765f...fde37ebc` | COMPLETE / FAIL — WORKER BOOTSTRAP SOURCE NOT BOUND BEFORE EXECUTION; FRESH-EXEC ISOLATION, BYTECODE BINDING AND THIRD-PARTY AUTHORITY VALID |
| POSTP1-001V2A-PAD4-R2 | bounded correction that pre-verifies the complete four-file worker bootstrap source set in already-trusted controller code before subprocess execution, refrozen at `68e6bd07...e52561` | IMPLEMENTATION COMPLETE / AWAITING INDEPENDENT EXACT-HASH FINAL xHIGH PROOF-ARCHITECTURE REVIEW |
| POSTP1-002V2A-PAD4-R2 | independent exact-hash final xHigh proof-architecture review of `68e6bd07...e52561` | NOT STARTED / DEPENDENCY-SATISFIED |
| POSTP1-001V2R1 | bounded correction of all seven POSTP1-002V2 findings against the certified calendar authority | BLOCKED pending certification of an enforceable ETF calendar authority |
| POSTP1-004 | schema, collectors, CVD/market-cap/liquidation capture and decision snapshot implementation | BLOCKED pending the POSTP1-001V2 exact-hash review, reissued sufficiency governance against the V2 parent and its own review |
