# BTC_REFERENCE_COMPOSITE_V4 Stage Correction

- Parent: `BTC_REFERENCE_COMPOSITE_V3` (`4232e886e7888b85833f778fcba6b2cb3eb5b7d802748aebf3b8adf19c5bf71a`)
- V4 hash: `670ff12dd3d63615e9ddb3be05d65505bab16b50e50c1fd9ad077a4923a3f501`
- Threshold changes: none
- Stage relocation: `live_shadow_days` only
- `live_shadow_days` threshold: `>= 90` (unchanged)
- Sealed sample collected/opened: no / no

## Gate ownership

| metric | role | threshold | direction | authoritative owner count | derivable | prospective | V4 stage |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| `atr_median_absolute_fractional_difference` | hard | `0.02` | `maximum` | 1 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `atr_p95_absolute_fractional_difference` | hard | `0.10` | `maximum` | 1 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `cross_market_confirmed_stop_preservation_rate` | hard | `1.0` | `minimum` | 0 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `daily_bucket_usable_rate` | hard | `0.995` | `minimum` | 1 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `deterministic_rerun_hash_match` | hard | `True` | `equal` | 0 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `gap_through_stop_consensus_agreement_rate` | hard | `0.99` | `minimum` | 0 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `historical_fallback_splice_count` | hard | `0` | `equal` | 1 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `isolated_venue_stop_suppression_rate` | hard | `0.95` | `minimum` | 0 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `live_shadow_days` | hard | `90` | `minimum` | 0 | false | true | `POST_CERTIFICATION_PROMOTION` |
| `mae_max_absolute_difference` | soft | `0.05` | `maximum` | 1 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `mae_median_absolute_difference` | hard | `0.0025` | `maximum` | 1 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `mae_p95_absolute_difference` | hard | `0.01` | `maximum` | 1 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `mfe_max_absolute_difference` | soft | `0.05` | `maximum` | 1 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `mfe_median_absolute_difference` | hard | `0.0025` | `maximum` | 1 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `mfe_p95_absolute_difference` | hard | `0.01` | `maximum` | 1 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `point_in_time_violation_count` | hard | `0` | `equal` | 1 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `provenance_complete_rate` | hard | `1.0` | `minimum` | 0 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `raw_observation_mutation_count` | hard | `0` | `equal` | 1 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `reference_degraded_rate` | soft | `0.020` | `maximum` | 1 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `reference_unavailable_rate` | hard | `0.005` | `maximum` | 1 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `reference_usable_rate` | hard | `0.995` | `minimum` | 1 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `regime_classification_disagreement_rate` | hard | `0.02` | `maximum` | 0 | false | false | `SEALED_HISTORICAL_VALIDATION` |
| `risk_size_p95_relative_difference` | hard | `0.10` | `maximum` | 0 | false | false | `SEALED_HISTORICAL_VALIDATION` |
| `setup_classification_disagreement_rate` | hard | `0.01` | `maximum` | 0 | false | false | `SEALED_HISTORICAL_VALIDATION` |
| `silent_incomplete_bucket_omission_count` | hard | `0` | `equal` | 1 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `stop_touch_disagreement_rate` | hard | `0.01` | `maximum` | 1 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `swing_level_disagreement_rate_above_0_50_atr` | hard | `0.05` | `maximum` | 1 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `trade_action_disagreement_rate` | hard | `0.01` | `maximum` | 0 | false | false | `SEALED_HISTORICAL_VALIDATION` |
| `trade_eligibility_disagreement_rate` | hard | `0.01` | `maximum` | 0 | false | false | `SEALED_HISTORICAL_VALIDATION` |
| `unrecorded_quality_state_count` | hard | `0` | `equal` | 1 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `validation_period_days` | hard | `1460` | `minimum` | 1 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `venue_disagreement_rate` | soft | `0.005` | `maximum` | 1 | true | false | `SEALED_HISTORICAL_VALIDATION` |
| `weekly_bucket_usable_rate` | hard | `0.990` | `minimum` | 1 | true | false | `SEALED_HISTORICAL_VALIDATION` |

## Certification disposition

The stage correction is deterministic and `live_shadow_days` is the sole prospective-only inherited gate. Executor certification remains fail-closed because the following Stage-A hard metrics have no executable measurement owner with a frozen input universe and denominator:

- `cross_market_confirmed_stop_preservation_rate`
- `deterministic_rerun_hash_match`
- `gap_through_stop_consensus_agreement_rate`
- `isolated_venue_stop_suppression_rate`
- `provenance_complete_rate`
- `regime_classification_disagreement_rate`
- `risk_size_p95_relative_difference`
- `setup_classification_disagreement_rate`
- `trade_action_disagreement_rate`
- `trade_eligibility_disagreement_rate`

Classification: `V4_EVIDENCE_PIPELINE_INCOMPLETE`
