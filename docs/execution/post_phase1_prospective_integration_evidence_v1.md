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

**Status:** `IMPLEMENTED / AWAITING REPEAT INDEPENDENT xHIGH REVIEW`
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

## Next EPIC X tasks

| ticket | task | status |
| --- | --- | --- |
| POSTP1-002 | `FORMAL_XHIGH_REVIEW_PROSPECTIVE_INTEGRATION_CORPUS_V1` | COMPLETE / FAIL |
| POSTP1-001R | `CORRECT_AND_REFREEZE_PROSPECTIVE_INTEGRATION_CORPUS_V1` | IMPLEMENTED / AWAITING REPEAT REVIEW |
| POSTP1-002R | repeat independent xHigh review of corrected protocol hash | READY |
| POSTP1-003 | `PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1` | BLOCKED by POSTP1-002R PASS |
| POSTP1-004 | schema, collectors, CVD capture and decision snapshot implementation | BLOCKED by POSTP1-003 exact-hash independent review PASS |
