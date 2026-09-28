# ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1 — POSTP1-001V2A-PAD4-R5

**Decision hash:** `b4168dc9c757f3cdbdeed48e9a91cc35eb921728adb5d38d0d5b76fd2ef861c7`
**Status:** `FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_FINAL_XHIGH_REVIEW`
**Final classification:** `ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_R5_READY_FOR_FINAL_XHIGH_REVIEW`
**Required review:** `POSTP1-002V2A-PAD4-R5_INDEPENDENT_EXACT_HASH_FINAL_XHIGH_PROOF_ARCHITECTURE_REVIEW`

## What this corrects

`POSTP1-002V2A-PAD4-R4` failed the immutable-snapshot `PAD4-R4` candidate
`ae25c2468972725a0ebd2f7742a532f3ec616c2e2cc8e94d93b3de46f86e65bc` with:

```text
FAIL — AUTHORITATIVE EXECUTION CONSTRUCTION BOUNDARY INVALID
```

A distinct unrelated caller-defined object could reuse the public authority
descriptors and equality/hash behaviour matching a legitimate execution. R4's
equality-keyed `WeakKeyDictionary` then resolved the legitimate immutable
snapshot for the foreign receiver. The snapshot representation and copy
isolation passed review; this is a bounded exact-identity correction, not PAD5.

## The frozen rule

```text
FOR ORDINARY PROJECT-OWNED CALLER CODE AND CALLER-DEFINED ORDINARY PYTHON
OBJECTS — NO CLOSURE-CELL RECOVERY, NO PRIVATE-NAME REFLECTION, NO MODULE
MUTATION — ONLY THE EXACT CONTROLLER-OWNED AUTHORITATIVE EXECUTION IDENTITY MAY
RESOLVE THE FROZEN ADMITTED AUTHORITY BOUND TO THAT EXECUTION.
```

Operatively, the frozen snapshot resolves only when the weak live witness is the
receiver by Python `is`, and only while that exact object is alive.

## Identity-safe binding

- Registry: closure-owned `dict[int, entry]`; the receiver is not a key.
- Bucket: `id(receiver)`, used only as a non-authoritative index.
- Entry: weak live witness plus the reviewed `FrozenAuthoritySnapshot`.
- Final predicate: `live_witness is receiver`.
- Type guard: `type(receiver) is AuthoritativeScientificExecution`, required
  non-load-bearing defence in depth.
- Reader/bind count: 1 / 1. Lookup cache: none.
- Cleanup: delete only if the current entry is the callback's exact entry.
- Receiver-controlled hash, equality, class, getattr, bool and repr are never
  invoked by lookup.

The load-bearing boundary is exact live identity, not the type guard. Identifier
reuse cannot rebind old authority and stale cleanup cannot remove a newer entry.

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
10_BIND_THE_IMMUTABLE_SNAPSHOT_TO_THE_EXACT_EXECUTION_IDENTITY
11_CONSTRUCT_AFFIRMATIVE_EVIDENCE_FROM_THAT_IMMUTABLE_AUTHORITATIVE_TRUTH
12_RETURN_THE_AUTHORITATIVE_EXECUTION
13_SERVE_CALLER_FACING_ACCESS_WITHOUT_EXPOSING_AUTHORITY_BY_MUTABLE_REFERENCE
```

R4's immutable snapshot, canonical bytes, bound digests and fresh detached
decodes remain unchanged. The exact controller-owned execution continues to
resolve all authority-bearing accessors.

## Preserved valid portions

- `AUTHORITATIVE_SCIENTIFIC_EXECUTION_CLOSURE`
- `BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING_ON_THE_AUTHORITATIVE_PATH`
- `BYTECODE_EXECUTION_BINDING_REPAIR_A`
- `CALLER_VISIBLE_COPY_ISOLATION`
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
- `FROZEN_AUTHORITY_SNAPSHOT`
- `FROZEN_SOURCE_AUTHORITY_REPAIR_B`
- `ONE_REQUEST_ONE_PROCESS_LIFECYCLE`
- `RECORD_INSTALLED_CONTENT_VERIFICATION_BEFORE_DEPENDENCY_EXECUTION`
- `RESULT_DIGEST_LIFETIME_BINDING`
- `SCIENTIFIC_ADMISSION_DECISION_PROCEDURE`
- `THIRD_PARTY_EXACT_VERSION_AND_ARTIFACT_AUTHORITY_REPAIR_D`
- `TRUSTED_CONTROLLER_AUTHORITY_CONTEXT_REPAIR_C`

## Children carried forward byte-identically from `PAD4-R4`

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
- `authoritative_return_state_rule`
- `result_digest_lifetime_binding_rule`

## Worker bootstrap source set

Unchanged from the reviewed four-file set because this correction is parent-side.

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
- `ae25c2468972725a0ebd2f7742a532f3ec616c2e2cc8e94d93b3de46f86e65bc`

Trusted persistence `02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772` is closed, certified,
unchanged and not re-reviewed by this decision.

## Open residual and scope

Relay through a legitimately held execution remains **OPEN / NOT CLAIMED
CLOSED**. Closure-cell recovery, private-name reflection, module mutation and
arbitrary hostile control of the trusted process remain outside the frozen
domain. Concurrency is **NOT SUPPORTED / OUTSIDE CURRENT CONTRACT**. If the R5
review fails in the same caller-created-authority family, a new architecture
decision is automatic; no PAD4-R6 is automatically created.

## Material children (34)

- `admission_provenance_rule` — `38054897ccc264964b14e433fcb8fe1dfaa937a4c20df958b9b69a3ec97cf376`
- `affirmative_evidence_snapshot_rule` — `6ba9e091d2670f93ee6bc0e8e3a9c9b0e9e5ef2be2eabd6ea19053205627ceb9`
- `authoritative_execution_identity_rule` — `4d0cfa40e30905b781f820a45f3bd6c74ba1016c5aac37824e2710b38acf2f1e`
- `authoritative_return_state_rule` — `62157bf2a5a716a31c1bbf49ad7b7dfeb8db899a2e1196508edd508798f1fe97`
- `authoritative_scientific_execution_boundary` — `959be72f614fb8691d277efed254b44919548da7de113d01c5b2528eaf1398fe`
- `authority_receiver_validation_rule` — `5236af8cb19cb00d8dc21b5b18d8b9a242ee839e3271380047b620a6dae0526f`
- `bootstrap_pre_execution_source_binding_rule` — `4249d9c36003b26dac0bcf006db8d65a3b7a7c2406ae28b1b6623062e5372b69`
- `bootstrap_source_set` — `8c700f4dee49e5d46a2e51183517dc51b2f12670d57b7573002c50102fc9c3f9`
- `bytecode_execution_binding_rule` — `6078ed5454af4d1f2270bfddc9dfa17bfdd534ed233e01dda97bc3bc52ecb386`
- `caller_visible_copy_isolation_rule` — `99f1053ba6aebde05df88af8845fd770c515274410313b1c3fa1be06996119d1`
- `canonical_admitted_snapshot_rule` — `93a34e3b9f7bc9cfdf95d8a5d67f9a70a5a5eac697494a6a1c7301f676bf007c`
- `compiled_root_binding_witness_rule` — `1f6849435345a9da4f4261c6a1b1aa1c749d36bb53fd0ef9197e75f615f3876f`
- `construction_identity_audit_rule` — `cc8e6548441ad84f763ec5dc6a47d5d9072a77fcf7053f75817b2661c1b607a5`
- `controller_authority_context_rule` — `709373868615fbb02c5b26a1618644c2a73a68daebc2f63922cc36c9574218e4`
- `controller_result_admission_rule` — `98ae369af8aab472f4aa1de2bdedd6d8c086f28a2c5260c37da127bc3ac4abb0`
- `direct_body_dependency_rule` — `3fb36786521c581c972e94840d98f8f3a26e7587ac219053389c1c985f111e56`
- `dynamic_import_and_execution_prohibition` — `02126ea85f95c222d477b1fb89b780362194c81fa6adebd6d94ad3d3c2d9ccd1`
- `identity_safe_snapshot_binding_rule` — `cd6d9b262ae29a1b24722fa2bd07782fb471e9363c9f9c23689535b1c2c118c7`
- `pre_i2_project_source_manifest_fixture` — `d92490b871277e6891949dce6a1fa690df6becb1a0a6f32a9b9359870f633cd2`
- `project_source_manifest_binding_rule` — `22d46bb74df195b2b3ea3349f393bc2edab404d34cb689ffb874951be5a41537`
- `proof_interpreter_identity` — `db93ec338968393c8242900b21eb2a1210a34498765693266fbfdc80344d8bcc`
- `proof_order_and_completeness_definition` — `221f275c3eb275bf287c005087d375dc79c5cd6b31a337f9428b4b88520cd29c`
- `replay_owner_graph_rule` — `b296a93418bfc075a9dfc76e4dc236bdb721a36b2cfc99f2636b049d72bbc49b`
- `result_digest_lifetime_binding_rule` — `5af3139f1e01b5f4b45f64af63f7a29ec2f6e896f5f24304992ee870b56bfe08`
- `science_lineage_and_safety` — `4c13b1236d3018f1585087f4e31e34d8f3f701b3026d3c0729a51aa911394989`
- `scientific_evidence_authority_rule` — `c79a8b117e818dac0ccfdad962ec0762bc7769712f8f2ac8f019b827704e6d17`
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

Successful implementation authorizes only `POSTP1-002V2A-PAD4-R5`. It does
**not** authorize `POSTP1-001V2A-I2`, `POSTP1-001V2R1`, `POSTP1-003R3`,
`POSTP1-004` or any prospective collection.
