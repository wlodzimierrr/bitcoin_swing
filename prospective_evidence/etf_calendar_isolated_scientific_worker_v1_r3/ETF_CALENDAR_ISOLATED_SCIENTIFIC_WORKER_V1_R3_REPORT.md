# ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1 — POSTP1-001V2A-PAD4-R3

**Decision hash:** `1fd9a2f9d5e5318505a6c48241f243b358261c100f67c4bc5b2c43ac9bd8bad0`
**Status:** `FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_FINAL_XHIGH_REVIEW`
**Final classification:** `ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_R3_READY_FOR_FINAL_XHIGH_REVIEW`
**Required review:** `POSTP1-002V2A-PAD4-R3_INDEPENDENT_EXACT_HASH_FINAL_XHIGH_PROOF_ARCHITECTURE_REVIEW`

## What this corrects

`POSTP1-002V2A-PAD4-R2` failed the `PAD4-R2` candidate
`68e6bd074a027900b2f3dde3da0a31b6d1cb2f1b9fc6c563e9b45bdc70e52561` with:

```text
FAIL — AUTHORITATIVE LAUNCH / ADMISSION BYPASS
```

Scientific admission neither required nor authenticated the trusted-controller
bootstrap pre-verification that its evidence claimed occurred. Three
independent reproducers each obtained an admitted fabricated scientific result:
the private raw spawn helper on a drifted bootstrap tree; a caller-fabricated
PASS `bootstrap_pre_verification` mapping, after which the evidence falsely
attested `ALREADY_TRUSTED_CONTROLLER_CODE`; and a hand-built
`WorkerProcessOutcome` with no subprocess ever created, using only public
names.

## The frozen rule

```text
NO OUTCOME CREATED WITHOUT SUCCESSFUL TRUSTED-CONTROLLER BOOTSTRAP
PREVERIFICATION MAY ENTER SCIENTIFIC ADMISSION OR PRODUCE AFFIRMATIVE
SCIENTIFIC AUTHORITY EVIDENCE.
```

The correction is structural. The generic composition of a caller-constructible
outcome, a generic admission function and a generic evidence function is gone
from the production scientific API. `admit_worker_result`,
`scientific_response_evidence`, `run_scientific_worker`, `WorkerProcessOutcome`,
`AdmissionOutcome` and the raw spawn helper do not exist in the production
controller. Their logic is folded inside one closed operation.

## The closed authoritative order

```text
1_RECEIVE_THE_TRUSTED_CONTROLLER_AUTHORITY_CONTEXT
2_VALIDATE_THE_REQUEST_AGAINST_THE_TRUSTED_AUTHORITY
3_PREVERIFY_THE_COMPLETE_BOOTSTRAP_SOURCE_SET
4_ALLOCATE_THE_FRESH_EMPTY_BYTECODE_CACHE_NAMESPACE
5_SPAWN_THE_EXACT_WORKER
6_OBTAIN_THE_EXACT_WORKER_EXECUTION_RESULT
7_VALIDATE_THE_RESPONSE_INSIDE_THE_SAME_CLOSED_FLOW
8_PERFORM_SCIENTIFIC_ADMISSION_INSIDE_THAT_FLOW
9_CONSTRUCT_AFFIRMATIVE_SCIENTIFIC_EVIDENCE_INSIDE_THAT_FLOW
10_RETURN_THE_FINAL_ADMITTED_RESULT_AND_EVIDENCE
```

The raw / test path may reproduce unverified worker behaviour, cannot enter
scientific admission, and cannot construct affirmative scientific evidence.

## Closed reviewed bypasses

- `CALLER_BUILT_ADMISSION_STATE_INTO_AFFIRMATIVE_EVIDENCE`
- `CALLER_FABRICATED_PASS_BOOTSTRAP_PRE_VERIFICATION_MAPPING`
- `HAND_BUILT_WORKER_PROCESS_OUTCOME_WITH_NO_SUBPROCESS`
- `RAW_UNVERIFIED_SPAWN_HELPER_INTO_GENERIC_ADMISSION`

## Authority mechanism

Capability ownership and closed control flow — not naming, not a field value,
not a dataclass identity, not a secret and not a signature. The affirmative
authority marker is constructed at exactly one site, inside the closure-local
evidence constructor, and the mechanical API-closure audit proves it.

## Preserved valid portions

- `BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING_ON_THE_AUTHORITATIVE_PATH`
- `BYTECODE_EXECUTION_BINDING_REPAIR_A`
- `CANONICAL_NON_EXECUTABLE_IPC`
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
- `THIRD_PARTY_EXACT_VERSION_AND_ARTIFACT_AUTHORITY_REPAIR_D`
- `TRUSTED_CONTROLLER_AUTHORITY_CONTEXT_REPAIR_C`

## Children carried forward byte-identically from `PAD4-R2`

- `bootstrap_pre_execution_source_binding_rule`
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

## Worker bootstrap source set

Unchanged from the reviewed `PAD4-R2` set, because this correction is local to
the controller admission surface.

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

Trusted persistence `02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772` is closed, certified,
unchanged and not re-reviewed by this decision.

## Material children (25)

- `admission_provenance_rule` — `38054897ccc264964b14e433fcb8fe1dfaa937a4c20df958b9b69a3ec97cf376`
- `authoritative_scientific_execution_boundary` — `80ff4ed62504682376d7bd14e92d9d20cb6839710657bfaf89b2dcfe9ed1992b`
- `bootstrap_pre_execution_source_binding_rule` — `4249d9c36003b26dac0bcf006db8d65a3b7a7c2406ae28b1b6623062e5372b69`
- `bootstrap_source_set` — `8c700f4dee49e5d46a2e51183517dc51b2f12670d57b7573002c50102fc9c3f9`
- `bytecode_execution_binding_rule` — `6078ed5454af4d1f2270bfddc9dfa17bfdd534ed233e01dda97bc3bc52ecb386`
- `compiled_root_binding_witness_rule` — `1f6849435345a9da4f4261c6a1b1aa1c749d36bb53fd0ef9197e75f615f3876f`
- `controller_authority_context_rule` — `6ac89d7552136afe89be255d4ae4aef0e3acc73fc59e3145eec43f85475c8eaf`
- `controller_result_admission_rule` — `98ae369af8aab472f4aa1de2bdedd6d8c086f28a2c5260c37da127bc3ac4abb0`
- `direct_body_dependency_rule` — `3fb36786521c581c972e94840d98f8f3a26e7587ac219053389c1c985f111e56`
- `dynamic_import_and_execution_prohibition` — `02126ea85f95c222d477b1fb89b780362194c81fa6adebd6d94ad3d3c2d9ccd1`
- `pre_i2_project_source_manifest_fixture` — `d92490b871277e6891949dce6a1fa690df6becb1a0a6f32a9b9359870f633cd2`
- `project_source_manifest_binding_rule` — `22d46bb74df195b2b3ea3349f393bc2edab404d34cb689ffb874951be5a41537`
- `proof_interpreter_identity` — `db93ec338968393c8242900b21eb2a1210a34498765693266fbfdc80344d8bcc`
- `proof_order_and_completeness_definition` — `95bb657e535f9011dc4bef8c40bf020f54302420cfbad3d4243ca61f4b56e8fd`
- `replay_owner_graph_rule` — `b296a93418bfc075a9dfc76e4dc236bdb721a36b2cfc99f2636b049d72bbc49b`
- `science_lineage_and_safety` — `0ee8c99af9ecfece3d2bfedde578374524ca67973b674c0886af5c35a0835add`
- `scientific_evidence_authority_rule` — `3c6fb44b3f4b142ca7f453e093736fc6d25c6a0fbf696bd35fce3f88f93c608e`
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

Successful implementation authorizes only `POSTP1-002V2A-PAD4-R3`. It does
**not** authorize `POSTP1-001V2A-I2`, `POSTP1-001V2R1`, `POSTP1-003R3`,
`POSTP1-004` or any prospective collection.
