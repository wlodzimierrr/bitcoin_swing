# PROSPECTIVE_INTEGRATION_CORPUS_V1

- Program / ticket: `POSTP1-001` -- `EPIC X -- PROSPECTIVE INTEGRATION EVIDENCE`
- Status: `FROZEN_PRE_DATA_PROTOCOL`
- Protocol hash: `aaa05c7288971ecb60e331c750fa728db13a3f2046cd597ffe4957a2f3d37326`
- Final classification: `PROSPECTIVE_INTEGRATION_CORPUS_V1_READY_FOR_XHIGH_REVIEW`
- Threshold changes: `0`
- Direction changes: `0`
- Hard-role changes: `0`
- Metric-intent changes: `0`
- Qualifying observations collected: no
- Real Stage-B outcomes evaluated: no
- BTC-019 reopened: no
- BTC-019 sealed sample collected / opened: no / no

## What this program is

BTC-019 is historically terminal at `BTC019_TERMINALLY_BLOCKED_BY_MISSING_INTEGRATION_EVIDENCE` and is not repaired here. This is a new post-Phase-1 prospective evidence program that creates, forward in time, the deterministic integration evidence that did not exist when BTC-019 terminated. It is not `BTC_REFERENCE_COMPOSITE_V6`: no frozen V3, V4, V5 or certified V1 byte moves, and no approval threshold, direction or hard role changes.

## Frozen child contracts

- `data_schema_contract`: `4664d1d59bf48f4f6409200f72b2b7ee8c33141518974efe8badb9f9d0209315`
- `decision_universe`: `1205ec050c2bd46aeb882752e1834cc94984d5ac6caae911d3e312faab348ec9`
- `evidence_sufficiency`: `923eb68e3138edf00bc3feec31838dc29d8e5924a5c6b377897f021fee5423d3`
- `input_snapshot_schema`: `37e58f99df18522c444625e6919308bedfe47d4e7e8970c565281e8381ff7be7`
- `metric_evidence_contracts`: `a5d6ee1097772a322855ba919beae30ff5acbd8784a7a43bfe99538d7707b295`
- `portfolio_track_contract`: `6b69af9ae9e9bb9c3b24cd622d0aa4f432207a032b4bcd94e1cdf25db21e3a2c`
- `semantic_diff_from_v5_blockers`: `3b6f2576a9e930b40443dc615b080bda016084caed1aa6edba0e3902cd50d47e`
- `stage_b_evaluation_contract`: `66b1b7d62900af235fc33b3f7e4dfbb529d23c67451bc66e3ef511359fbc2e5b`
- `stop_event_taxonomy`: `a239328b56a9312844e20319b6e88f4c4faecfc1c295519bf53b4f05b924ab72`

## The eight measurements

| metric | universe | statistic | threshold | direction |
| --- | --- | --- | --- | --- |
| `cross_market_confirmed_stop_preservation_rate` | `CROSS_MARKET_CONFIRMED_STOP_EVENTS` | rate | `1.0` | `minimum` |
| `gap_through_stop_consensus_agreement_rate` | `GAP_THROUGH_STOP_EVENTS` | rate | `0.99` | `minimum` |
| `isolated_venue_stop_suppression_rate` | `ISOLATED_VENUE_STOP_EVENTS` | rate | `0.95` | `minimum` |
| `regime_classification_disagreement_rate` | `REGIME_EVALUABLE_DECISION_TIMES` | rate | `0.02` | `maximum` |
| `risk_size_p95_relative_difference` | `SIZING_EVALUABLE_DECISION_TIMES` | nearest_rank_p95_of_the_absolute_relative_differences | `0.10` | `maximum` |
| `setup_classification_disagreement_rate` | `SETUP_EVALUABLE_DECISION_TIMES` | rate | `0.01` | `maximum` |
| `trade_action_disagreement_rate` | `ACTION_EVALUABLE_DECISION_TIMES` | rate | `0.01` | `maximum` |
| `trade_eligibility_disagreement_rate` | `ELIGIBILITY_EVALUABLE_DECISION_TIMES` | rate | `0.01` | `maximum` |

## Evidence sufficiency

Every metric's evaluability minimum is frozen here: a complete scheduled-slot census, both tracks valid, and a comparable denominator of at least one. A zero denominator is `UNDEFINED_INSUFFICIENT_EVIDENCE` and never a PASS.

Per-metric certification minimums are deliberately not chosen here. Selecting a rate gate's minimum n is its own pre-data governance task in this repository, so all eight are marked `REPORTABLE_BUT_NOT_CERTIFIABLE_WITHOUT_SEPARATE_PRE_DATA_GOVERNANCE` and deferred to `PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1`. No calendar minimum is imported from Stage-C's `live_shadow_days >= 90`.

## Collection is not authorized

Lifecycle state is `FROZEN`. Entering `COLLECTING` requires `INDEPENDENT_XHIGH_REVIEW_OF_THIS_EXACT_PROTOCOL_HASH_MUST_PASS_FIRST`. The sealed BTC-019 sample stays NOT COLLECTED, NOT OPENED and NOT EVALUATED, and a Stage-B PASS here does not open it.

Final classification: `PROSPECTIVE_INTEGRATION_CORPUS_V1_READY_FOR_XHIGH_REVIEW`
