# BTC_REFERENCE_COMPOSITE_V3_VALIDATOR_V2

The executing successor to the certified
`BTC_REFERENCE_COMPOSITE_V3_VALIDATOR_V1`. It is derived from the parent contract at
build time and differs from it by exactly one verdict-affecting field --
`sealed_execution_authorized`, false -> true -- plus the execution-control
artifacts that make that authorization one-shot.

## Binding

- Bound protocol hash: `4232e886e7888b85833f778fcba6b2cb3eb5b7d802748aebf3b8adf19c5bf71a`
- Parent validator: `BTC_REFERENCE_COMPOSITE_V3_VALIDATOR_V1`
- Parent validator hash: `8e6254e0354c04de077bf482ccb6852bfe4299f138d3c97f1ba33859bfc7ffe7`
- Executing validator hash: `e21e6ad8e8a40e4ee0763d7f3176efc168dacc0701f8e1199ae8a25ee5f9d784`
- Parent certification: `VALIDATOR_CERTIFIED_FOR_SEALED_EXECUTION_PREPARATION`

## Semantic delta

`SEALED_EXECUTION_AUTHORIZATION_ONLY_V1`

Changed:

- `output_schema.fields`
- `output_schema.record_schema_version`
- `sealed_sample.collection_authorized`
- `sealed_sample.opening_authorized`
- `sealed_sample.sealed_execution_authorized`
- `sealed_sample.sealed_execution_rule`
- `validator_schema_version`
- `validator_version`

Added:

- `parent_validator`
- `sealed_execution_control`
- `sealed_sample.execution_states`
- `sealed_sample.one_shot_execution`
- `sealed_sample.reuse_after_finalized_run`
- `sealed_sample_contract`
- `semantic_delta`

Removed: 0

Every other field of the certified parent is byte-identical.

## One-shot execution

```text
NOT_PREPARED -> PREPARED -> COLLECTED_FROZEN -> EXECUTION_STARTED -> FINALIZED
```

- `NOT_PREPARED` -> `PREPARED` via `prepare_sealed_execution`
- `PREPARED` -> `COLLECTED_FROZEN` via `record_frozen_collection_manifest`
- `COLLECTED_FROZEN` -> `EXECUTION_STARTED` via `begin_sealed_execution`
- `EXECUTION_STARTED` -> `FINALIZED` via `execute_sealed_validation`

The sealed sample is opened exactly once. A second sealed result for the same frozen V3 definition hash, the same executing validator hash and the same sealed sample identity is REFUSE, whether it is requested in the same process or after a restart. The execution state is durable, never process-local: it is read from the authorization record before every transition, no transition may move backwards or repeat, and FINALIZED is terminal. A finalized run can be re-read but never re-run, and its result digest is immutable.

## Sealed sample

- Window: `2015-07-20T21:00:00+00:00` .. `2019-11-30T23:00:00+00:00`
- Bar interval: `1h`, timezone `UTC`
- Providers: `bitfinex`, `bitstamp`, `coinbase`
- Manifest schema: `BTC019_V3_SEALED_SAMPLE_MANIFEST_V1`
- Result schema: `BTC019_V3_SEALED_VALIDATION_RESULT_V1`
- Collected: no
- Opened: no

## Collection sequence

1. collect raw provider data
2. write immutable raw files
3. compute per-file SHA-256
4. create the collection manifest
5. freeze the manifest and record its digest on the authorization record
6. only then construct the candidate and any derived evidence

## Terminal outcomes

### `PASS`

The candidate is approved under the frozen BTC_REFERENCE_COMPOSITE_V3 protocol. PRICE_SOURCE_POLICY_V2 may then be written and BTC-019 may close successfully.

### `FAIL`

The candidate is rejected under the frozen protocol. V3 may not be retuned using the sealed sample.

### `UNDEFINED_INSUFFICIENT_EVIDENCE`

The candidate is not approved and the canonical production reference remains unresolved. V3 may not be retuned using the sealed sample.

All three verdicts are valid terminal research outcomes of the one-shot run. Nothing in this contract promises that BTC-019 passes. After the sealed sample is opened there is no post-sealed tuning: no threshold, gate, denominator, window or pair universe may be changed in response to what the sealed sample showed, and no second sample may be collected to improve an outcome.
