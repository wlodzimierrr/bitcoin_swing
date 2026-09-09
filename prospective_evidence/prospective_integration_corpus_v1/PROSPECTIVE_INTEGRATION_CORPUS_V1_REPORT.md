# PROSPECTIVE_INTEGRATION_CORPUS_V1

- Program / ticket: `POSTP1-001R` -- `EPIC X -- PROSPECTIVE INTEGRATION EVIDENCE`
- Status: `CORRECTED_PRE_DATA_PROTOCOL_AWAITING_REPEAT_XHIGH_REVIEW`
- Protocol hash: `0d4f14370c2d17359fa3e5d36ce545f00e00da1a360a66ad3151a37d0cf45a9e`
- Final classification: `CORRECTED_PROSPECTIVE_INTEGRATION_CORPUS_V1_READY_FOR_REPEAT_XHIGH_REVIEW`
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

## Failed lineage retained

- Failed protocol hash: `aaa05c7288971ecb60e331c750fa728db13a3f2046cd597ffe4957a2f3d37326`
- Failed implementation commit: `b38f387f822da713aa06489e6643c9d6909de32a`
- Review: `FAIL — PROSPECTIVE PROTOCOL INVALID` / `PROSPECTIVE_PROTOCOL_REQUIRES_FIX`
- Superseded before collection: `YES`

## Corrected ownership and input closure

- `raw.liquidations` is a required append-only PIT capture family.
- Every `INITIAL_FEATURE_NAMES` member is bound to its transitive raw input families and one prospective capture contract.
- CVD cadence is exact-hour UTC with the authoritative 20-period z-score window.
- Trade-action comparison owner: `TRADE_ACTION_COMPARISON_OWNER_V1`.
- Trade-eligibility permission owner: `TRADE_ELIGIBILITY_COMPOSITE_OWNER_V1`.
- Stop-event anchor: `CONTROL_REFERENCE_TRACK_ACTIVE_STOP`.
- Gap-through prior owner: `PREVIOUS_CONTIGUOUS_REQUIRED_PROVIDER_CONSENSUS_CLOSE_V1`; maximum gap: `3600s`.

## Frozen child contracts

- `data_schema_contract`: `ada2223829adbe804e27e437f04fc46472587c02f2833126b7c558ae57246dd2`
- `decision_universe`: `b8673d9a170585c62b8e3feec1d126c75c8aa9352238f260f235066649c16b39`
- `evidence_sufficiency`: `af424423723f377d22fdddd01e396de9a2323db0c9aa59defd57b78076cc5df9`
- `feature_input_coverage`: `7b049c0e49739d6e20370e2472c46134889d811f8f9b7a5b770cbc6f95c8ec31`
- `input_snapshot_schema`: `35c55f616e6ed567400d597a2c747dbb67335514417a07496288d0bf1f303116`
- `metric_evidence_contracts`: `98746db2d5d8d9a7d2d5846a83333ff356c6747f39949c2c0bdae38f799e3c98`
- `portfolio_track_contract`: `1560eee774049e7eb72180ccfc18477e919eaf127646e03e1405cdf161318623`
- `semantic_diff_from_v5_blockers`: `49b129afd07a08ddfbe6b4195e648b7ab28f712a3d2747739ec139ef7965673d`
- `stage_b_evaluation_contract`: `8be898a9f858a6d60fbd44bbce6effc4c4d2051f87aea39952805be5798240e2`
- `stop_event_taxonomy`: `ebd2d322db1994332844a6a597fcad7673b61632fb34f1361e758546af6e971e`
- `warmup_history`: `0f718a197d19ccebe9068a51f11b3dd12c4d874e3c97de129172ab7ff3068055`

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

Arithmetic evaluability is frozen here: a complete scheduled-slot census, complete PIT inputs, frozen warmup completion and both tracks' owner outputs. A zero denominator is `UNDEFINED_INSUFFICIENT_EVIDENCE` and never a PASS; this protocol chooses no certification minimum.

Per-metric certification minimums are deliberately not chosen here. Selecting a rate gate's minimum n is its own pre-data governance task in this repository, so all eight are marked `REPORTABLE_BUT_NOT_CERTIFIABLE_WITHOUT_SEPARATE_PRE_DATA_GOVERNANCE` and deferred to `PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1`. No calendar minimum is imported from Stage-C's `live_shadow_days >= 90`.

## Collection is not authorized

Lifecycle state is `FROZEN`. Entering `COLLECTING` requires `INDEPENDENT_XHIGH_CERTIFICATION_OF_THIS_EXACT_PROTOCOL_HASH_AND_INDEPENDENT_XHIGH_CERTIFICATION_OF_THE_EXACT_PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1_HASH_AND_INDEPENDENT_IMPLEMENTATION_REVIEW_OF_POSTP1_004_MUST_ALL_PASS`. The sealed BTC-019 sample stays NOT COLLECTED, NOT OPENED and NOT EVALUATED, and a Stage-B PASS here does not open it.

Final classification: `CORRECTED_PROSPECTIVE_INTEGRATION_CORPUS_V1_READY_FOR_REPEAT_XHIGH_REVIEW`
