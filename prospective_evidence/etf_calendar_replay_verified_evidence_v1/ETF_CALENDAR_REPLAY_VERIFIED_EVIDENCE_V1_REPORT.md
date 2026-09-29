# ETF_CALENDAR_REPLAY_VERIFIED_EVIDENCE_V1 — POSTP1-001V2A-PAD5

**Decision hash:** `546759848b27fc09af7701b6b40712838c5fc9eb1d8500df62a3e2e02df3f483`
**Status:** `FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_XHIGH_REVIEW`
**Final classification:** `ETF_CALENDAR_REPLAY_VERIFIED_EVIDENCE_V1_READY_FOR_XHIGH_REVIEW`
**Required review:** `POSTP1-002V2A-PAD5 — INDEPENDENT EXACT-HASH xHIGH PROOF-ARCHITECTURE REVIEW`

## What this replaces

`POSTP1-002V2A-PAD4-R5` failed the exact-identity `PAD4-R5` candidate
`b4168dc9c757f3cdbdeed48e9a91cc35eb921728adb5d38d0d5b76fd2ef861c7` with:

```text
COMPLETE / FAIL — CLOSURE-OWNED REGISTRY OBJECT-GRAPH BOUNDARY INVALID; SAME-FAMILY ESCALATION AUTOMATIC
```

That was the fourth failure in one family — fabricate, mutate, impersonate,
recover — and the pre-committed rule escalated automatically to a new
proof-architecture decision, `DECIDE_ETF_CALENDAR_PROOF_ARCHITECTURE_AFTER_PAD4_R5_V1`. No `PAD4-R6` was created.

The shared root cause is that any object reachable in a CPython process can be
enumerated and mutated by other code in that process. No arrangement of
in-process Python state can make "only the exact controller-owned object
resolves authority" true while uncertified caller code shares the interpreter.

## The frozen invariant

```text
NO_IN_PROCESS_OBJECT_CARRIES_SCIENTIFIC_AUTHORITY__CALENDAR_EVIDENCE_IS_ADMISSIBLE_IF_AND_ONLY_IF_A_STANDALONE_VERIFIER_PROCESS_EXECUTING_ONLY_CERTIFIED_SOURCE_AT_AN_EXACT_REVIEWED_COMMIT_VERIFIES_THE_RECORDED_REQUEST_AGAINST_THE_FROZEN_TRUSTED_AUTHORITY_CONTEXT_VERIFIES_EVERY_INPUT_EVIDENCE_RECORD_UNDER_THE_CERTIFIED_TRUSTED_PERSISTENCE_AUTHORITY_RE_EXECUTES_THE_CERTIFIED_FRESH_EXEC_WORKER_ON_THE_EXACT_RECORDED_REQUEST_BYTES_AND_FINDS_THE_FROZEN_DETERMINISTIC_PROJECTION_OF_THE_RESPONSE_BYTE_IDENTICAL_TO_THE_RECORDED_ONE
```

Authority is a property of bytes, not of an object. It is anchored in the exact
reviewed commit the verifier runs from; the verifier recording its own source
manifest digest is audit metadata and defence in depth, and is **not**
authority.

## The verification order

```text
1_READ_THE_EVIDENCE_ITEM_AS_FILES_AND_CHECK_THE_FROZEN_LAYOUT
2_PARSE_THE_RECORDED_REQUEST_AS_EXACT_SELF_RESERIALIZING_CANONICAL_BYTES
3_VALIDATE_THE_RECORDED_REQUEST_AGAINST_THE_FROZEN_REQUEST_SCHEMA
4_COMPARE_EVERY_AUTHORITY_BOUND_REQUEST_FIELD_WITH_THE_FROZEN_CONTEXT
5_VERIFY_THAT_THIS_INTERPRETER_IS_THE_FROZEN_PROOF_INTERPRETER
6_VERIFY_THAT_THIS_IS_THE_RECORDED_ENVIRONMENT
7_VERIFY_EVERY_INPUT_ENVELOPE_UNDER_THE_CERTIFIED_TRUSTED_PERSISTENCE_PATH
8_REQUIRE_THE_RECORDED_EVIDENCE_RECORDS_AND_VERIFIED_PAYLOADS_TO_AGREE
9_BIND_THE_COMPLETE_BOOTSTRAP_SOURCE_SET_BEFORE_ANY_PROCESS_EXISTS
10_RE_EXECUTE_THE_CERTIFIED_WORKER_ON_THE_EXACT_RECORDED_REQUEST_BYTES
11_COMPARE_THE_FROZEN_PROJECTION_OF_BOTH_RESPONSES_BYTE_FOR_BYTE
12_WRITE_ONE_CANONICAL_DIGEST_BOUND_RECORD_WHETHER_ACCEPTED_OR_REJECTED
```

## Deterministic comparison projection

The projection is a **closed inclusion list** of
32 named response fields. It is
never "everything except". `RUN_LOCAL` is empty — measured, not assumed, by
re-executing the same recorded request in separate processes with different
bytecode-cache namespaces, different working directories and different
`PYTHONHASHSEED` values.

- `authority_context_origin` — IN_PROJECTION_AUTHORITY: echoed from the recorded request, so it is a pure function of the request bytes
- `bootstrap_defence_in_depth_verification` — IN_PROJECTION_AUTHORITY: the worker's restatement of the bootstrap binding; drift of any bootstrap source changes it
- `bytecode_cache_binding` — IN_PROJECTION_AUTHORITY: the preserved Repair A verdict; a cache namespace that is not fresh and empty changes it
- `calendar_authority_sha256` — IN_PROJECTION_AUTHORITY: authority-bound, compared against the frozen trusted context before execution and again after
- `calendar_authority_version` — IN_PROJECTION_AUTHORITY: authority-bound frozen constant
- `decision_time` — IN_PROJECTION_AUTHORITY: echoed from the recorded request; it is the decision time the request names, never a clock read at run time
- `evidence_admission_mode` — IN_PROJECTION_AUTHORITY: echoed from the recorded request
- `failure_reason` — IN_PROJECTION_AUTHORITY: the worker's own verdict; a refusal that re-derives as a success, or the reverse, must not compare equal
- `interpreter_flags` — IN_PROJECTION_AUTHORITY: fixed by the frozen launch contract, so a changed launch flag is a rejection rather than a silent difference
- `interpreter_identity` — IN_PROJECTION_AUTHORITY: authority-bound; this is the field that makes an interpreter-identity mismatch a rejection
- `loaded_project_modules` — IN_PROJECTION_AUTHORITY: the count of certified project modules the worker actually imported; source drift changes it
- `one_request_one_process` — IN_PROJECTION_AUTHORITY: the preserved one-shot declaration
- `operation` — IN_PROJECTION_AUTHORITY: echoed from the recorded request
- `post_execution_source_verification` — IN_PROJECTION_AUTHORITY: the preserved post-execution source verdict
- `project_source_manifest_digest` — IN_PROJECTION_AUTHORITY: authority-bound; certified worker source drift changes it
- `project_source_manifest_role` — IN_PROJECTION_AUTHORITY: authority-bound frozen constant
- `request_digest` — IN_PROJECTION_AUTHORITY: the digest of the exact canonical request bytes the worker received, so it is a pure function of those bytes
- `request_schema_version` — IN_PROJECTION_AUTHORITY: echoed from the recorded request
- `response_schema_version` — IN_PROJECTION_AUTHORITY: frozen worker protocol constant
- `result` — IN_PROJECTION_AUTHORITY: the full scientific result. The projection carries the whole result object, not a summary of it
- `result_digest` — IN_PROJECTION_AUTHORITY: the digest the worker bound to its result
- `status` — IN_PROJECTION_AUTHORITY: the worker's SUCCESS or REFUSED verdict
- `sys_path_digest` — IN_PROJECTION_AUTHORITY: a digest of the recorded request's sys_path, so it is a pure function of the request bytes
- `third_party_authority_digest` — IN_PROJECTION_AUTHORITY: authority-bound frozen reviewed registry digest
- `third_party_installed_content_verification` — IN_PROJECTION_AUTHORITY: the preserved Repair D verdict
- `third_party_observed_content_manifest_digest` — IN_PROJECTION_AUTHORITY: measured from the installed third-party content. It is environment-derived, which is exactly why it is projected: installed-content drift then rejects instead of passing
- `trusted_persistence_authority_sha256` — IN_PROJECTION_AUTHORITY: authority-bound certified trusted-persistence hash
- `worker_authority_sha256` — IN_PROJECTION_AUTHORITY: authority-bound proof-architecture identity
- `worker_authority_ticket` — IN_PROJECTION_AUTHORITY: authority-bound frozen worker protocol ticket
- `worker_authority_version` — IN_PROJECTION_AUTHORITY: authority-bound frozen constant
- `worker_bootstrap_manifest_digest` — IN_PROJECTION_AUTHORITY: authority-bound; any bootstrap source drift changes it
- `worker_entrypoint_module` — IN_PROJECTION_AUTHORITY: authority-bound frozen constant

**Environment-local request fields:** `project_root`, `sys_path`, `third_party_environment`.
The frozen choice is `VERIFY_IN_THE_RECORDED_ENVIRONMENT`; no relocation rule is
frozen and request bytes are never rewritten.

## Verifier

- Entry: `btc_predictor.research.etf_calendar_evidence_verifier`
- Launch: `-I -S -B` plus `-X pycache_prefix`
- Source manifest: 119 modules at
  `37f69095b0c576097fcf3bc5d88508398e6134507ddd363852f050fb9f9cf140`
- Interface: 5 command-line strings and the
  canonical JSON documents they name. No callback, plugin, pickle, class, module
  or caller object can cross.

## Reject-on-sight

- `ACCEPTING_EVIDENCE_BY_DIGEST_COMPARISON_ALONE_WITHOUT_RE_EXECUTION`
- `ANY_DOMAIN_TEXT_THAT_EXCLUDES_INTROSPECTION_ROUTES_TO_MAKE_A_CLAIM_TRUE`
- `ANY_IN_PROCESS_OBJECT_REGISTRY_CAPABILITY_CLOSURE_OR_TYPE_GATE_AS_AUTHORITY`
- `A_COMPARISON_PROJECTION_DEFINED_BY_EXCLUSION`
- `THE_PRODUCER_OR_WORKER_ATTESTING_ITS_OWN_AUTHORITY`
- `THE_VERIFIER_IMPORTING_A_MODULE_OUTSIDE_THE_CERTIFIED_CLOSURE`
- `THE_VERIFIER_RUNNING_INSIDE_THE_PRODUCERS_PROCESS`

## Children carried forward byte-identically from `PAD4-R5` (15)

- `bootstrap_source_set`
- `bytecode_execution_binding_rule`
- `compiled_root_binding_witness_rule`
- `direct_body_dependency_rule`
- `dynamic_import_and_execution_prohibition`
- `pre_i2_project_source_manifest_fixture`
- `project_source_manifest_binding_rule`
- `proof_interpreter_identity`
- `replay_owner_graph_rule`
- `scientific_request_protocol`
- `scientific_response_protocol`
- `store_root_and_direct_use_grammar`
- `third_party_installed_content_attestation_rule`
- `third_party_semantic_authority`
- `worker_io_and_capability_boundary`

## Children re-issued because the reviewed payload asserted in-process closure (5)

- `bootstrap_pre_execution_source_binding_rule`
- `replay_verified_admission_rule`
- `trusted_authority_context_rule`
- `trusted_process_and_isolation_boundary`
- `worker_launch_contract`

## New children (11)

- `canonical_encoding_rule`
- `comparison_projection_definition`
- `consumer_admission_rule`
- `evidence_item_layout_rule`
- `non_authoritative_producer_rule`
- `proof_order_and_completeness_definition`
- `replay_verified_evidence_boundary`
- `science_lineage_and_safety`
- `verification_record_contract`
- `verifier_interface_boundary`
- `verifier_source_manifest`

## Retired `R5` identity children — failed lineage, not copied here (11)

- `affirmative_evidence_snapshot_rule`
- `authoritative_execution_identity_rule`
- `authoritative_return_state_rule`
- `authoritative_scientific_execution_boundary`
- `authority_receiver_validation_rule`
- `caller_visible_copy_isolation_rule`
- `canonical_admitted_snapshot_rule`
- `construction_identity_audit_rule`
- `identity_safe_snapshot_binding_rule`
- `result_digest_lifetime_binding_rule`
- `scientific_evidence_authority_rule`

## Worker bootstrap source set

Unchanged and not forked.

1. `etf_calendar_worker/__init__.py`
2. `etf_calendar_worker/entry_r2.py`
3. `etf_calendar_worker/protocol_r1.py`
4. `etf_calendar_worker/protocol_r2.py`

**Bootstrap manifest digest:** `1811e04dac7a033de2c8e6620bf7d5aa227b94eebdf419657ecccf4d3fead411`

## Source authority

- PRE-I2 conformance fixture: 116 modules
  at `674b006ae66b8aace3458cb870f898ecad33e1f23833436954d36749b3aadbb8`
- Candidate worker source universe:
  120 modules at
  `7ffbf15792d33e0cd387eb995d8d733c1fa1b98b2859153957c670f796a44e8e`
- Third-party authority digest: `23e4f1d89a503b43fc39ee0ae3516b742f6db72028224d78a9181be6726298a6`

## Preserved eleven replay owners

- `derive_normalized_schedule_from_official_source`
- `venue_session_calendar_record`
- `_verify_schedule`
- `_verify_schedule_record`
- `validate_normalized_schedule_against_source`
- `_verify_venue_row`
- `venue_session_status`
- `common_etf_session_status`
- `expected_etf_publication_dates`
- `derive_etf_window_calendar`
- `scientific_etf_flow_window`

## Failed architecture lineage — immutable, non-certified, unused (13)

- `0c237c1b217b1fd406ec3967309774293c01d3e27574b9f4a7d1b9a0e887b55d`
- `a7d2b08741080494cc4ca0269bf21e28e631c7f2e70887bcb0e1beb302534dd0`
- `dc36ffe228b7a3bc6d9145042b4e301c8624c99a79d71a88b46fc268f1372c3e`
- `9f6af1794e8b49dce38288b9f1b9710bffd04ba70303b5c380e8fb447ac86295`
- `7ef114fede9efebe594f0ecf119d097a1161119f448737d0df10afdf9468d17b`
- `b5ca36bfa9b96970b667cc44b10c5c5da7eb5ce7c57e5739601640d9b2a8abe9`
- `b8f8b92d4e3c1c80c4226f7101e71f95d125bd48afbfcde72e489408f6b5b996`
- `cc1b325a656f5b0be046d46700a4fcb9ad7ad94bf9b3440acac164677b809e78`
- `3415765f63a902e415e039ea71892087274541c1e8976a46d41c8f4afde37ebc`
- `68e6bd074a027900b2f3dde3da0a31b6d1cb2f1b9fc6c563e9b45bdc70e52561`
- `1fd9a2f9d5e5318505a6c48241f243b358261c100f67c4bc5b2c43ac9bd8bad0`
- `ae25c2468972725a0ebd2f7742a532f3ec616c2e2cc8e94d93b3de46f86e65bc`
- `b4168dc9c757f3cdbdeed48e9a91cc35eb921728adb5d38d0d5b76fd2ef861c7`

Trusted persistence `02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772` is closed, certified,
unchanged and not re-reviewed by this decision.

## Accepted costs

Verification re-executes the worker once per evidence item. Integrity is
guaranteed; availability is not. A hostile producer can make evidence be
**rejected**; it cannot make evidence be **accepted**. Rejections are counted
and recorded, never silently dropped.

## Material children (31)

- `bootstrap_pre_execution_source_binding_rule` — `a2ad7cbe0c2fea20ce5dc41244ee89a7fa28d2b854b1453859c8da9796c87d4c`
- `bootstrap_source_set` — `8c700f4dee49e5d46a2e51183517dc51b2f12670d57b7573002c50102fc9c3f9`
- `bytecode_execution_binding_rule` — `6078ed5454af4d1f2270bfddc9dfa17bfdd534ed233e01dda97bc3bc52ecb386`
- `canonical_encoding_rule` — `18c47e468075b1e18df376512fa2b8e81bdb3d25a143296b1a858c3d00bc3f49`
- `comparison_projection_definition` — `d2ab9af9af4d320f915f313715f510d3ed7e00ebda8f87165b974963627aa293`
- `compiled_root_binding_witness_rule` — `1f6849435345a9da4f4261c6a1b1aa1c749d36bb53fd0ef9197e75f615f3876f`
- `consumer_admission_rule` — `0929c1872caba4f9f8edbdbf89d80e7c6b625d1fdd48089543d3cdcaf9a615be`
- `direct_body_dependency_rule` — `3fb36786521c581c972e94840d98f8f3a26e7587ac219053389c1c985f111e56`
- `dynamic_import_and_execution_prohibition` — `02126ea85f95c222d477b1fb89b780362194c81fa6adebd6d94ad3d3c2d9ccd1`
- `evidence_item_layout_rule` — `7c9554f34899b7799b470a61dc084e2776447c14c7010c4ed15e198d9de5759f`
- `non_authoritative_producer_rule` — `74d0c04c91e18d669291179a63b4b80aa3fed49928a152faff19bacfb72cf87d`
- `pre_i2_project_source_manifest_fixture` — `d92490b871277e6891949dce6a1fa690df6becb1a0a6f32a9b9359870f633cd2`
- `project_source_manifest_binding_rule` — `22d46bb74df195b2b3ea3349f393bc2edab404d34cb689ffb874951be5a41537`
- `proof_interpreter_identity` — `db93ec338968393c8242900b21eb2a1210a34498765693266fbfdc80344d8bcc`
- `proof_order_and_completeness_definition` — `f18a17f8e725e60da87f888106ea1ffa3b7fbe094a66023c19df68d5dab40bb1`
- `replay_owner_graph_rule` — `b296a93418bfc075a9dfc76e4dc236bdb721a36b2cfc99f2636b049d72bbc49b`
- `replay_verified_admission_rule` — `4b2b0c760a2b9cf636bc66d7c0baa3ed3a71eee64bcdc5f080da5e7b251c895f`
- `replay_verified_evidence_boundary` — `f248f07ec9a68be5da1e3e40ef140fbf1217650969fab4f3e5a5c69374228651`
- `science_lineage_and_safety` — `b4ae22afcccab7100d60ae7a3a699ffac185cf67dd08cabbae4cbae0ec5db7e4`
- `scientific_request_protocol` — `791ccfa43aff42df06263b01ba5c8da26002a95a80f6b882601c690c07de3ae5`
- `scientific_response_protocol` — `61ce3a8694f4671eb3682af3985c140fd530cd73065e57ee25ae37055ae7571f`
- `store_root_and_direct_use_grammar` — `fbbd247a1a96b017f32b5532a4e539219b6d4459b76c91609411f7bf1791164b`
- `third_party_installed_content_attestation_rule` — `5abf011588f4affbb36c4f4163b0cf773c1ec68a71e8c368d6d05803ea1d1c2a`
- `third_party_semantic_authority` — `0e12dd87239de921de998421b1f3b9123552f74be9a4cfb6456f41224a1bb065`
- `trusted_authority_context_rule` — `951fa5af48af8e9999846674449e5b463a25624736584afff6fb0e64d24a3e60`
- `trusted_process_and_isolation_boundary` — `1eb78c8d1b7634a517ca18a3c61a9e9f72b68b4b88e84bec93e1cf3bc3b2acae`
- `verification_record_contract` — `53ca373a98bb18e3e2285ee033b86dafc134fbcac28a493f25874346b79b8237`
- `verifier_interface_boundary` — `f088244cbd5dccc1b71cb8fe0af889bf2b277bb9b3dd7feac3d9fe66ee955ebb`
- `verifier_source_manifest` — `fd684b9febb3f763bafce068d8d9406af209d092514bf143630546adad6dd5ab`
- `worker_io_and_capability_boundary` — `cd39d3437481967ebf3be43025040d538e033c703d326c039a83213b05575cab`
- `worker_launch_contract` — `44d15e0c1c1b845b38f082cb90dbf2090fb3d2c4cf026c4c8369e53050df2972`

## Safety

Observations remain **0**. No real Stage-B evaluation ran. The ETF calendar is
**not** certified, no calendar production code changed, collection is **NOT
AUTHORIZED**, `BTC-019` is untouched with its sealed sample unopened, Epic T is
unchanged and EPIC Y is unchanged.

Successful implementation authorizes only `POSTP1-002V2A-PAD5`. It does **not**
authorize `POSTP1-001V2A-I2`, `POSTP1-001V2R1`, `POSTP1-003R3`, `POSTP1-004` or
any prospective collection.
