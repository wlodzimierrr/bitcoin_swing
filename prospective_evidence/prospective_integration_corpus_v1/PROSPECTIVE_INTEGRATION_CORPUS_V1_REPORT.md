# PROSPECTIVE_INTEGRATION_CORPUS_V1

- Program / ticket: `POSTP1-001R5` -- `EPIC X -- PROSPECTIVE INTEGRATION EVIDENCE`
- Status: `REPLAYABLE_PRE_DATA_PROTOCOL_AWAITING_SIXTH_XHIGH_REVIEW`
- Protocol hash: `8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7`
- Final classification: `PROSPECTIVE_INTEGRATION_CORPUS_READY_FOR_SIXTH_XHIGH_REVIEW`
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

- Attempt 1 (`POSTP1-001`) hash: `aaa05c7288971ecb60e331c750fa728db13a3f2046cd597ffe4957a2f3d37326`
  - Implementation commit: `b38f387f822da713aa06489e6643c9d6909de32a`
  - Review: `FAIL — PROSPECTIVE PROTOCOL INVALID` / `PROSPECTIVE_PROTOCOL_REQUIRES_FIX`
  - Retained as failed, non-authoritative, superseded before collection: `YES`
- Attempt 2 (`POSTP1-001R`) hash: `0d4f14370c2d17359fa3e5d36ce545f00e00da1a360a66ad3151a37d0cf45a9e`
  - Implementation commit: `8af223d708ee03b09bca6e43c204620aba44ecab`
  - Review: `FAIL — AMBIGUOUS FROZEN INPUT` / `PROSPECTIVE_PROTOCOL_BLOCKED_BY_AMBIGUOUS_FROZEN_INPUT`
  - Retained as failed, non-authoritative, superseded before collection: `YES`
- Attempt 3 (`POSTP1-001R2`) hash: `40e37067fdddee467ea6c8f0094a2498573e3ff379d35f0fdd5586af423c9862`
  - Implementation commit: `9b2f23acc793457b0e8683387d8382f06472fdd4`
  - Review: `FAIL — MARKET CAP SOURCE CONTRACT INVALID` / `PROSPECTIVE_PROTOCOL_REQUIRES_FIX`
  - Retained as failed, non-authoritative, superseded before collection: `YES`
- Attempt 4 (`POSTP1-001R3`) hash: `e60a951476afb41437347220e7ab043ed6261cc03489da379adfca915c9a7dca`
  - Implementation commit: `f54025690975047c9c859567303088a5059f342e`
  - Review: `FAIL — CORRECTED PROSPECTIVE PROTOCOL INVALID` / `PROSPECTIVE_PROTOCOL_REQUIRES_FIX`
  - Retained as failed, non-authoritative, superseded before collection: `YES`
- Attempt 5 (`POSTP1-001R4`) hash: `fd946a091d9e1944163a78d331c31c518de2f21a35707a32141443d05f9bedff`
  - Implementation commit: `b813365c39d0423babe17caeabf85e7b7473de09`
  - Review: `FAIL — CORRECTED PROSPECTIVE PROTOCOL INVALID` / `PROSPECTIVE_PROTOCOL_REQUIRES_FIX`
  - Retained as failed, non-authoritative, superseded before collection: `YES`

Version retained rather than incremented: All five prior definition hashes failed independent review before any collection epoch opened, so no persisted observation carries the superseded semantics. CHANGE_PROCEDURE binds PROSPECTIVE_INTEGRATION_CORPUS_V2 to a semantic change after collection starts, not to a pre-data correction, so the version is retained and the five failed definition hashes carry the lineage.

## New prospective pre-data acquisition governance

Phase-1 owns the feature transformations. It never owned a persisted source, cadence or feed-state contract for three of their raw inputs, so `POSTP1-001R5` freezes those acquisition semantics now, before collection, and declares them explicitly as new governance rather than inherited authority.

- `PROSPECTIVE_CVD_ACQUISITION_V1`: the historical owner `btc_predictor.features.flow.spot_perp_cvd_spread` specifies **no cadence** -- it accepts arbitrary common timestamps and is observation-count based, requiring `20 prior common observations`. The `1h` acquisition cadence is selected here by new pre-data governance over exact Kraken `BTC/USD` spot and `PI_XBTUSD` perpetual trade feeds. Every complete hour is reconstructed from one uninterrupted acknowledged subscription epoch, collector-owned ping/pong liveness, renewed same-domain clock health, collector-health counters, runtime PI_XBTUSD metadata and exact event/received-at censuses; nothing is stitched across reconnects and no event received after finalization can enter the closed revision. The selector requires the current and 20 prior contiguous UTC hours before the observation-count owner; no Stage-B outcome was inspected.
- `PROSPECTIVE_BTC_MARKET_CAP_ACQUISITION_V1`: no repository producer emits `market_cap_usd` today, and the unqualified `raw.generic_series` family is not a source contract. One exact series identity is frozen: `BTC_MARKET_CAP_USD` / `market_cap` / `usd` from provider `coingecko` `https://api.coingecko.com/api/v3/coins/bitcoin/history` on `raw.generic_series` at `1d`. Fixed 00:45/00:50/00:55 UTC polling serializes `date=YYYY-MM-DD`, binds each exact response BYTEA and byte digest to its exact request attempt, mechanically enforces the inclusive 45-second monotonic timeout, represents timeout/transport failures without fake response fields, validates exact `bitcoin` / `btc` identity and a finite positive `market_data.market_cap.usd`, records clock-valid response completion locally, requeries day-1 through day-3, requires the exact scheduled date and selects one latest PIT revision per timestamp.
- `PROSPECTIVE_LIQUIDATION_CAPTURE_V1`: the existing aggregate `btc_predictor.data.derivatives.aggregate_btc_derivatives_available_at` collapses a missing feed and an observed zero-event feed to the same numeric zero. The prospective capture layer uses only Kraken Futures `PI_XBTUSD` liquidation-typed trade events and reuses the same epoch/liveness/health evidence as CVD. An observed zero requires one fully replayed exact hour. The daily reducer resolves each cited completeness record and its transitive graph, so a rehashed surface cannot override incomplete evidence; a daily value requires the exact 24-hour UTC census with no missing or duplicate identity, over `['INVALID', 'LATE', 'OBSERVED_WITH_EVENTS', 'OBSERVED_ZERO_EVENTS', 'SOURCE_UNAVAILABLE']`.
- `PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_V1`: no executable owner produces `liquidation_percentile`, so one is frozen here over a `730`-day half-open trailing window with `365` minimum prior observations and the repository's own `MIDRANK_PERCENTILE_OF_PRIOR_WINDOW_V1` convention.
- `PROSPECTIVE_CLOCK_INTEGRITY_V1`: scientific local wall timestamps require an auditable synchronized OS/NTP/chrony health record with absolute offset and uncertainty each no greater than one second. Health is polled every 30 seconds, may be no older than 40 seconds and may have no renewal gap above 40 seconds. Durations and liveness deadlines use one explicit host/process/start/boot monotonic domain; a larger than one-second wall/monotonic divergence invalidates the affected evidence.

## Warmup is a rule, not a constant

- `VOL_PERCENTILE_2Y` trailing window span: `730` days, `half-open [observation_time - window, observation_time)`.
- Minimum prior observations: `365`.
- Upstream initialization: each RV_20 result needs 21 contiguous daily closes (20 daily returns).
- First evaluable with contiguous daily observations: `386` sessions (`385` elapsed calendar days).
- `750 calendar days` is **not** retained as a scientific minimum; contiguous-history numbers are retained only as `PLANNING_ESTIMATE_NOT_EVALUABILITY_AUTHORITY`.

## Corrected ownership and input closure

- `raw.liquidations` is a required append-only PIT capture family.
- Every `INITIAL_FEATURE_NAMES` member is bound to its transitive raw input families and one prospective capture contract.
- `OI_INTENSITY` and `OI_INTENSITY_PERCENTILE_180D` name the frozen market-cap source contract, never an unqualified generic-series family.
- Trade-action comparison owner: `TRADE_ACTION_COMPARISON_OWNER_V1`.
- Trade-eligibility permission owner: `TRADE_ELIGIBILITY_COMPOSITE_OWNER_V1`.
- Stop-event anchor: `CONTROL_REFERENCE_TRACK_ACTIVE_STOP`.
- Gap-through prior owner: `PREVIOUS_CONTIGUOUS_REQUIRED_PROVIDER_CONSENSUS_CLOSE_V1`; maximum gap: `3600s`.

## Frozen child contracts

Material child count (mechanically enumerated): `25`

- `coingecko_market_cap_request_attempt`: `4ea71f2461ac9d4a279c757ee349be4df76679e070e0a896e3e53ca9f0175fc6`
- `coingecko_market_cap_response_validation`: `1cda159214ab5b2045790a5fa3c1ca7e3ba0d51d41456be4c5bc5d5e75f67eee`
- `cvd_interval_completeness`: `b26bd859c30648b182d06e669177b1c440e7329de18c135be429f41c3c6cc906`
- `data_schema_contract`: `0c29908f121c9060d47c5153aa938feed48f73a69268d323e9e72b9affcbf66d`
- `decision_universe`: `b78abe4e34dfdcd097523dc80548bc452c4a5eb787fda4ea82ba47784a36c3ce`
- `evidence_sufficiency`: `af424423723f377d22fdddd01e396de9a2323db0c9aa59defd57b78076cc5df9`
- `feature_input_coverage`: `73d5909cb47d4cd63efc9e743a706448c8e609e65593f4474d183e759513f580`
- `input_snapshot_schema`: `c90999c6a73574fed161297eefc17ff55f2bdf068b79e5d55d6785f8fd25c69c`
- `kraken_futures_instrument_metadata_validation`: `efeb5be0164582370aea0cefc4c5be8802de80ee551bb77e763c6c713e84ee6e`
- `liquidation_interval_completeness`: `346214ec2b6c6dd7cf5b31b76134d85756d2a1a7aaa7e7006199c8a2c0ff2522`
- `liquidation_utc_day_census`: `7180ad6cb78f2abe03308618ab369e94509bb20c3f4bb8b7ac9535abb190a4a2`
- `metric_evidence_contracts`: `98746db2d5d8d9a7d2d5846a83333ff356c6747f39949c2c0bdae38f799e3c98`
- `portfolio_track_contract`: `92887cc240c77ebcea24eb5e9b521fda84f036f33e1d033eea663587cd5360f4`
- `prospective_btc_market_cap_acquisition`: `76738c92292058c557a9828d3b1d8c2e88fee591b2ef37096f01c163a590a798`
- `prospective_clock_integrity`: `be449ebd62b7bcc8cf90ea8c9b38d3fb06f382ff16cc19a5cb04ff9697823ef2`
- `prospective_cvd_acquisition`: `65ff928b3eaed7eba7db9f5ebd7f0a0c06e79648218dc851ca993960b896390f`
- `prospective_liquidation_capture`: `d4268aa2833b8f386777729ae69c9625895b477733c1a62866ea896d141798c8`
- `prospective_liquidation_percentile_adapter`: `606e3930d32f13550b86c6db918782274bd1758a5548dea147771eb766b215b7`
- `scientific_evidence_resolver`: `ea8ce4f3c79638b322a3c9c354ed38f8b2f2689b5dc79c1538aa2b9b9e41ac1e`
- `semantic_diff_from_v5_blockers`: `49b129afd07a08ddfbe6b4195e648b7ab28f712a3d2747739ec139ef7965673d`
- `source_stream_epoch`: `b8e35f3bc14252334d1a651c3a6e28cb1685cfcfb4e415ab5b9e8f73bb6434e5`
- `stage_b_evaluation_contract`: `a98c161de21ecb31467fbd73c80f606e2999bd1843429976147ec46d299212f0`
- `stop_event_taxonomy`: `ebd2d322db1994332844a6a597fcad7673b61632fb34f1361e758546af6e971e`
- `stream_liveness_policy`: `efe9402aa3721234cfe7d05791d3735b817d96130dc359acc50d102d2c0f80a5`
- `warmup_history`: `71af8a1a0fe31e60d0be3bd37292a73f174b8112b731eb619d41ad26d1de50ac`

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

Final classification: `PROSPECTIVE_INTEGRATION_CORPUS_READY_FOR_SIXTH_XHIGH_REVIEW`
