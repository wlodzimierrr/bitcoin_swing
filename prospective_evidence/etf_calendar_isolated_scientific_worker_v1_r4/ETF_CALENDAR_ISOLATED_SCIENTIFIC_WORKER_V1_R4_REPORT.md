# ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1 — POSTP1-001V2A-PAD4-R4

**Decision hash:** `ae25c2468972725a0ebd2f7742a532f3ec616c2e2cc8e94d93b3de46f86e65bc`
**Status:** `FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_FINAL_XHIGH_REVIEW`
**Final classification:** `ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_R4_READY_FOR_FINAL_XHIGH_REVIEW`
**Required review:** `POSTP1-002V2A-PAD4-R4_INDEPENDENT_EXACT_HASH_FINAL_XHIGH_PROOF_ARCHITECTURE_REVIEW`

## What this corrects

`POSTP1-002V2A-PAD4-R3` failed the `PAD4-R3` candidate
`1fd9a2f9d5e5318505a6c48241f243b358261c100f67c4bc5b2c43ac9bd8bad0` with:

```text
FAIL — CALLER-CREATED STATE CAN BECOME SCIENTIFIC AUTHORITY
```

Admission itself was correct. The failure happened *after* successful admission:
the closed flow stored its authority as a shallow copy whose `response` value was
the live protocol-parser mapping and whose `result` value was that mapping's own
nested `result` object, and handed both straight back. Mutating a returned
mapping therefore rewrote the authority-bearing state of an admitted,
affirmatively stamped execution, while the bound `result_digest` kept describing
what had actually been admitted.

This is a bounded return-state / authority-container correction. It is not a
bootstrap, process-isolation, bytecode, source-authority, third-party-authority
or worker-protocol correction, and it is not a `PAD5`.

## The frozen rule

```text
ONCE SCIENTIFIC ADMISSION SUCCEEDS, NO CALLER MUTATION MAY CHANGE THE
AUTHORITATIVE RESPONSE, RESULT OR AFFIRMATIVE EVIDENCE REPRESENTED BY THAT
ADMITTED EXECUTION.
```

Equivalently: what was admitted is what the authority permanently represents,
for the whole lifetime of the admitted execution.

## The authority-bearing storage

The authority stops being a Python container. These nine fields are the whole of
what an admitted execution represents, and every one of them holds `bytes`,
`str`, `bool` or `None`:

- `admitted`
- `affirmative_evidence_bytes`
- `affirmative_evidence_digest`
- `failure_reason`
- `request_digest`
- `response_bytes`
- `response_digest`
- `result_bytes`
- `result_digest`

There is therefore no nested mutable descendant to reach, and no read-only
wrapper is used: an outer `MappingProxyType` over a mutable graph would leave
every nested container writable and is explicitly **not** the mechanism. The
canonical serialisation is the already reviewed worker protocol
`etf_calendar_worker.protocol_r1.canonical_json_bytes` — no second canonical encoding was invented — and
`etf_calendar_worker.protocol_r1.parse_canonical_json` produces a fresh, fully detached object graph on
every mapping-like accessor call.

## The closed authoritative order

```text
1_RECEIVE_THE_TRUSTED_CONTROLLER_AUTHORITY_CONTEXT
2_VALIDATE_THE_REQUEST_AGAINST_THE_TRUSTED_AUTHORITY
3_PREVERIFY_THE_COMPLETE_BOOTSTRAP_SOURCE_SET
4_ALLOCATE_THE_FRESH_EMPTY_BYTECODE_CACHE_NAMESPACE
5_SPAWN_THE_EXACT_WORKER_AND_OBTAIN_THE_EXACT_EXECUTION_RESULT
6_VALIDATE_THE_RESPONSE_PROTOCOL_INSIDE_THE_SAME_CLOSED_FLOW
7_CANONICALIZE_THE_EXACT_VALIDATED_RESPONSE_AND_RESULT
8_VERIFY_AND_BIND_THE_EXACT_RESULT_DIGEST_TO_THOSE_CANONICAL_BYTES
9_PERFORM_SUCCESSFUL_SCIENTIFIC_ADMISSION_INSIDE_THAT_FLOW
10_STORE_THE_IMMUTABLE_CANONICAL_ADMITTED_SNAPSHOT_AS_AUTHORITATIVE_TRUTH
11_CONSTRUCT_AFFIRMATIVE_EVIDENCE_FROM_THAT_IMMUTABLE_AUTHORITATIVE_TRUTH
12_RETURN_THE_AUTHORITATIVE_EXECUTION
13_SERVE_CALLER_FACING_ACCESS_WITHOUT_EXPOSING_AUTHORITY_BY_MUTABLE_REFERENCE
```

Affirmative evidence is constructed *from* the frozen snapshot, and the admitted
execution is already frozen when it first becomes caller-visible. There is no
window in which mutable admitted state is exposed and frozen afterwards.

## Closed reviewed return-state mutations

- `CALLER_MUTATED_RETURNED_RESPONSE_MAPPING_CHANGED_ADMITTED_AUTHORITY`
- `CALLER_MUTATED_RETURNED_RESULT_MAPPING_CHANGED_ADMITTED_AUTHORITY`
- `LIVE_AUTHORITATIVE_STATE_STOPPED_MATCHING_THE_BOUND_RESULT_DIGEST`
- `RETURNED_RESPONSE_AND_RETURNED_RESULT_SHARED_MUTABLE_DESCENDANTS`

## Authority mechanism

Capability ownership and closed control flow, preserved exactly from the reviewed
`PAD4-R3`, plus immutable canonical snapshot storage. Not naming, not a field
value, not a dataclass identity, not a secret, not a signature, and not a
defensive copy bolted onto an accessor. `authoritative_snapshot_proof()`
reproduces the bound digests from the frozen bytes alone.

## Preserved valid portions

- `AUTHORITATIVE_SCIENTIFIC_EXECUTION_CLOSURE`
- `BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING_ON_THE_AUTHORITATIVE_PATH`
- `BYTECODE_EXECUTION_BINDING_REPAIR_A`
- `CANONICAL_NON_EXECUTABLE_IPC`
- `CAPABILITY_OWNED_CONSTRUCTION_AUTHORITY`
- `CLOSED_ONE_OPERATION_AUTHORITY_FLOW`
- `CLOSED_STORE_GRAMMAR`
- `COMPILED_ROOT_WITNESS`
- `DIRECT_DEPENDENCY_BODY_RULE`
- `EXACT_ELEVEN_OWNER_GRAPH`
- `FOUR_MEMBER_BOOTSTRAP_SOURCE_SET`
- `FRESH_EMPTY_PYCACHE_NAMESPACE`
- `FRESH_EXEC_ISOLATION`
- `FROZEN_SOURCE_AUTHORITY_REPAIR_B`
- `ONE_REQUEST_ONE_PROCESS_LIFECYCLE`
- `RECORD_INSTALLED_CONTENT_VERIFICATION_BEFORE_DEPENDENCY_EXECUTION`
- `SCIENTIFIC_ADMISSION_DECISION_PROCEDURE`
- `THIRD_PARTY_EXACT_VERSION_AND_ARTIFACT_AUTHORITY_REPAIR_D`
- `TRUSTED_CONTROLLER_AUTHORITY_CONTEXT_REPAIR_C`

## Children carried forward byte-identically from `PAD4-R3`

- `admission_provenance_rule`
- `bootstrap_pre_execution_source_binding_rule`
- `bootstrap_source_set`
- `bytecode_execution_binding_rule`
- `compiled_root_binding_witness_rule`
- `controller_result_admission_rule`
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
- `trusted_process_and_isolation_boundary`
- `worker_io_and_capability_boundary`
- `worker_launch_contract`

## Worker bootstrap source set

Unchanged from the reviewed `PAD4-R2` set carried through `PAD4-R3`, because this
correction is entirely parent-side and post-admission.

1. `etf_calendar_worker/__init__.py`
2. `etf_calendar_worker/entry_r2.py`
3. `etf_calendar_worker/protocol_r1.py`
4. `etf_calendar_worker/protocol_r2.py`

**Bootstrap manifest digest:** `1811e04dac7a033de2c8e6620bf7d5aa227b94eebdf419657ecccf4d3fead411`

## Source authority

- PRE-I2 conformance fixture: 116 modules
  at `674b006ae66b8aace3458cb870f898ecad33e1f23833436954d36749b3aadbb8`
  (role `PRE_I2_CONFORMANCE_FIXTURE_AND_PROVENANCE`)
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

## Failed architecture lineage — immutable, non-certified, unused

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

Trusted persistence `02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772` is closed, certified,
unchanged and not re-reviewed by this decision.

## Material children (30)

- `admission_provenance_rule` — `38054897ccc264964b14e433fcb8fe1dfaa937a4c20df958b9b69a3ec97cf376`
- `affirmative_evidence_snapshot_rule` — `0b8ad16e2de4803b3cdafc16d7915adeb73cbce6c97433a6c04e7215f76ff60d`
- `authoritative_return_state_rule` — `62157bf2a5a716a31c1bbf49ad7b7dfeb8db899a2e1196508edd508798f1fe97`
- `authoritative_scientific_execution_boundary` — `d4fe4ac788d3f6a8b3272dd3784b2c2f85d225db077a656a0457841d93805f1b`
- `bootstrap_pre_execution_source_binding_rule` — `4249d9c36003b26dac0bcf006db8d65a3b7a7c2406ae28b1b6623062e5372b69`
- `bootstrap_source_set` — `8c700f4dee49e5d46a2e51183517dc51b2f12670d57b7573002c50102fc9c3f9`
- `bytecode_execution_binding_rule` — `6078ed5454af4d1f2270bfddc9dfa17bfdd534ed233e01dda97bc3bc52ecb386`
- `caller_visible_copy_isolation_rule` — `ffb49ced14c499dc5f56ecf9676e5ac9518fcc386f0e351c8903edc879b9b3d4`
- `canonical_admitted_snapshot_rule` — `5415cfe7ebe802aebb67bf20e2fa56bf77224892b37442a0db8f56423a7de5c5`
- `compiled_root_binding_witness_rule` — `1f6849435345a9da4f4261c6a1b1aa1c749d36bb53fd0ef9197e75f615f3876f`
- `controller_authority_context_rule` — `2622b8de1cd27d12f97983c8904275a34f98958fa875e697f0100df6f3ab43cb`
- `controller_result_admission_rule` — `98ae369af8aab472f4aa1de2bdedd6d8c086f28a2c5260c37da127bc3ac4abb0`
- `direct_body_dependency_rule` — `3fb36786521c581c972e94840d98f8f3a26e7587ac219053389c1c985f111e56`
- `dynamic_import_and_execution_prohibition` — `02126ea85f95c222d477b1fb89b780362194c81fa6adebd6d94ad3d3c2d9ccd1`
- `pre_i2_project_source_manifest_fixture` — `d92490b871277e6891949dce6a1fa690df6becb1a0a6f32a9b9359870f633cd2`
- `project_source_manifest_binding_rule` — `22d46bb74df195b2b3ea3349f393bc2edab404d34cb689ffb874951be5a41537`
- `proof_interpreter_identity` — `db93ec338968393c8242900b21eb2a1210a34498765693266fbfdc80344d8bcc`
- `proof_order_and_completeness_definition` — `555b778448972d4a991e8d273c4cdeeb23a25e054b81e0b8e118e14fe129f5c2`
- `replay_owner_graph_rule` — `b296a93418bfc075a9dfc76e4dc236bdb721a36b2cfc99f2636b049d72bbc49b`
- `result_digest_lifetime_binding_rule` — `5af3139f1e01b5f4b45f64af63f7a29ec2f6e896f5f24304992ee870b56bfe08`
- `science_lineage_and_safety` — `831dc6f5193689883fb49e93e70f6649a04c9bc3c9fec72d46cf30487e37edb0`
- `scientific_evidence_authority_rule` — `86aa85da0817e2b4bb769a8fa6eb8a2641060fd1ae52c3c419235485468ec33d`
- `scientific_request_protocol` — `791ccfa43aff42df06263b01ba5c8da26002a95a80f6b882601c690c07de3ae5`
- `scientific_response_protocol` — `61ce3a8694f4671eb3682af3985c140fd530cd73065e57ee25ae37055ae7571f`
- `store_root_and_direct_use_grammar` — `fbbd247a1a96b017f32b5532a4e539219b6d4459b76c91609411f7bf1791164b`
- `third_party_installed_content_attestation_rule` — `5abf011588f4affbb36c4f4163b0cf773c1ec68a71e8c368d6d05803ea1d1c2a`
- `third_party_semantic_authority` — `0e12dd87239de921de998421b1f3b9123552f74be9a4cfb6456f41224a1bb065`
- `trusted_process_and_isolation_boundary` — `b6d194ad820897ed699a6489a08017ee47382fe5027e2f1d3754251660170465`
- `worker_io_and_capability_boundary` — `cd39d3437481967ebf3be43025040d538e033c703d326c039a83213b05575cab`
- `worker_launch_contract` — `94566e79129e2b170f4b61aeed41cee9104bd5691eeaa394b8803d8d436df7ad`

## Safety

Observations remain **0**. No real Stage-B evaluation ran. The ETF calendar is
**not** certified, no calendar production code changed, collection is **NOT
AUTHORIZED**, `BTC-019` is untouched with its sealed sample unopened, and Epic T
is unchanged.

Successful implementation authorizes only `POSTP1-002V2A-PAD4-R4`. It does
**not** authorize `POSTP1-001V2A-I2`, `POSTP1-001V2R1`, `POSTP1-003R3`,
`POSTP1-004` or any prospective collection.
