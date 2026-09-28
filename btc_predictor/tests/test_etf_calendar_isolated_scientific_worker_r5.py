"""POSTP1-001V2A-PAD4-R5 exact-identity worker tests.

The decisive regression reproduces R4's unrelated non-subclass descriptor-reuse
P0 and proves that the same receiver is refused by R5 without executing its
equality, hash or other caller-controlled hooks.  The reviewed R4 immutable
snapshot and copy-isolation suite is also retained here against R5.

Everything the review reproduced as valid is re-proved here rather than assumed:
the closed one-operation authority flow and its construction authority, the four
bootstrap drift refusals, the reviewed ``PAD4-R2`` admission bypasses, Repairs
A/B/C/D, the compiled witness, the closed grammar, the eleven-owner graph and the
direct dependency-body rule.  The reviewed ``PAD4-R2`` fixtures — the certified
tree, the pre-launch drifted bootstrap trees, the forged bytecode and the
fabricated-result probe — and the ``PAD4-R3`` raw review harness are imported
rather than forked, so the preserved properties are re-proved with the same
material earlier reviews reproduced, driven through the *R5* closed flow.
"""

from __future__ import annotations

import gc
import inspect
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from weakref import ref

import pytest

from btc_predictor.features import flow as _flow
from btc_predictor.research import etf_calendar_isolated_scientific_worker_r1 as r1
from btc_predictor.research import etf_calendar_isolated_scientific_worker_r2 as r2
from btc_predictor.research import etf_calendar_isolated_scientific_worker_r3 as r3
from btc_predictor.research import etf_calendar_isolated_scientific_worker_r4 as r4
from btc_predictor.research import etf_calendar_isolated_scientific_worker_r5 as r5
from btc_predictor.tests import etf_calendar_raw_worker_harness_r3 as raw
from btc_predictor.tests import test_etf_calendar_isolated_scientific_worker_r2 as base
from etf_calendar_worker import protocol_r2 as protocol


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / r5.OUTPUT_NAMESPACE
R3_ARTIFACT_DIR = ROOT / r3.OUTPUT_NAMESPACE
R4_ARTIFACT_DIR = ROOT / r4.OUTPUT_NAMESPACE

ENTRYPOINT = base.ENTRYPOINT
PACKAGE_INITIALIZER = base.PACKAGE_INITIALIZER
REUSED_PROTOCOL = base.REUSED_PROTOCOL
WORKER_PROTOCOL = base.WORKER_PROTOCOL
BOOTSTRAP_SET = base.BOOTSTRAP_SET
ZERO_HASH = base.ZERO_HASH
DEADBEEF_HASH = base.DEADBEEF_HASH
FABRICATED_RESULT = base.FABRICATED_RESULT
HONEST_SESSION_STATE = base.HONEST_SESSION_STATE
SESSION_DAY = base.SESSION_DAY
DECISION_TIME = base.DECISION_TIME

DECISION = r5.isolated_scientific_worker_v1_r5_definition()
CANDIDATE_HASH = DECISION["definition_sha256"]

#: The trusted R5 context a reviewer or harness instantiates for this candidate.
CONTEXT = r5.candidate_review_authority_context(CANDIDATE_HASH)
LAUNCH = r5.worker_launch()
MANIFEST = r5.frozen_candidate_source_manifest()
BOOTSTRAP_MANIFEST = r5.frozen_bootstrap_source_manifest()

#: The reviewed failed ``PAD4-R3`` decision hash, used to build the *R3* trusted
#: context the mandatory return-state control drives.
R3_CANDIDATE_HASH = r5.FAILED_PAD4_R3_SHA256
R4_CANDIDATE_HASH = r5.FAILED_PAD4_R4_SHA256


def session_request(context=None, launch=None, **overrides) -> dict:
    return r5.build_scientific_request(
        CONTEXT if context is None else context,
        launch=LAUNCH if launch is None else launch,
        operation="common_etf_session_status",
        operation_inputs={"trade_date": SESSION_DAY.isoformat()},
        evidence_records=overrides.pop("evidence_records", base.SESSION_RECORDS),
        decision_time=DECISION_TIME.isoformat(),
        **overrides,
    )


def flow_request(context=None, launch=None, **overrides) -> dict:
    return r5.build_scientific_request(
        CONTEXT if context is None else context,
        launch=LAUNCH if launch is None else launch,
        operation="scientific_etf_flow_window",
        operation_inputs={
            "as_of": DECISION_TIME.isoformat(),
            "funds": list(base.FUNDS),
            "end_date": SESSION_DAY.isoformat(),
            "earliest_date": base.WINDOW_START.isoformat(),
            "window_days": 5,
            "etf_flows": base._encoded_flows(),
        },
        evidence_records=base.WINDOW_RECORDS,
        decision_time=DECISION_TIME.isoformat(),
        **overrides,
    )


SESSION_REQUEST = session_request()


class SpawnRecorder:
    """Record every worker process the R5 controller actually creates."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.calls: list[list[str]] = []
        original = subprocess.run

        def recording_run(argv, *args, **kwargs):
            self.calls.append([str(part) for part in argv])
            return original(argv, *args, **kwargs)

        monkeypatch.setattr(r5.subprocess, "run", recording_run)

    @property
    def worker_spawns(self) -> list[list[str]]:
        return [
            argv
            for argv in self.calls
            if any(part.endswith(ENTRYPOINT) for part in argv)
        ]


def _run(request: dict, launch=None, context=None, **kwargs):
    return r5.run_isolated_scientific_request(
        CONTEXT if context is None else context,
        request,
        LAUNCH if launch is None else launch,
        **kwargs,
    )


def _snapshot(execution) -> dict:
    """Everything an admitted execution represents, as comparable material."""

    return {
        "admitted": execution.admitted,
        "failure_reason": execution.failure_reason,
        "request_digest": execution.request_digest,
        "result": execution.result,
        "response": execution.response,
        "scientific_evidence": execution.scientific_evidence,
        "proof": execution.authoritative_snapshot_proof(),
    }


def _mutable_ids(payload, found=None) -> set[int]:
    """Every mutable container reachable from a returned convenience value."""

    if found is None:
        found = set()
    if isinstance(payload, dict):
        found.add(id(payload))
        for value in payload.values():
            _mutable_ids(value, found)
    elif isinstance(payload, list):
        found.add(id(payload))
        for value in payload:
            _mutable_ids(value, found)
    return found


@pytest.fixture(scope="module")
def admitted_session():
    """One admitted session execution, shared deliberately.

    Sharing is the point: if any mutation a test performs could reach authority,
    a later test reading this same execution would see it.  Every mutation test
    below also asserts the invariant immediately, so a leak fails loudly here
    rather than silently somewhere else.
    """

    execution = _run(SESSION_REQUEST)
    assert execution.admitted is True, execution.failure_reason
    return execution


@pytest.fixture(scope="module")
def admitted_flow():
    """One admitted flow execution — nested mappings and nested sequences."""

    execution = _run(flow_request())
    assert execution.admitted is True, execution.failure_reason
    return execution


# ---------------------------------------------------------------------------
# Decision integrity
# ---------------------------------------------------------------------------


def test_decision_scope_status_and_strategy_are_frozen() -> None:
    assert DECISION["decision_version"] == "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1"
    assert DECISION["program_ticket"] == "POSTP1-001V2A-PAD4-R5"
    assert DECISION["status"] == (
        "FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_FINAL_XHIGH_REVIEW"
    )
    assert DECISION["final_classification"] == (
        "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_R5_READY_FOR_FINAL_XHIGH_REVIEW"
    )
    assert DECISION["pre_data"] is True
    assert DECISION["required_review"].startswith("POSTP1-002V2A-PAD4-R5")
    assert DECISION["proof_strategy"].startswith(
        "EXACT_IDENTITY_SAFE_AUTHORITY_BINDING_PLUS_"
    )
    assert DECISION["correction_of"] == r5.FAILED_PAD4_R4_SHA256
    assert DECISION["correction_is_a_new_architecture_family"] is False
    assert DECISION["correction_scope"] == (
        "BOUNDED_EXACT_EXECUTION_IDENTITY_BINDING"
    )
    assert DECISION["authorization"] == {
        "independent_proof_architecture_xhigh_review_may_begin": True,
        "calendar_implementation_may_begin": False,
        "postp1_001v2a_i2_may_begin": False,
        "postp1_001v2r1_may_begin": False,
        "prospective_collection_may_begin": False,
    }


def test_material_children_are_mechanical_bound_and_digest_valid() -> None:
    children = r5._children()
    assert len(children) == 34
    assert DECISION["material_child_count"] == 34
    assert DECISION["material_child_enumeration"] == (
        "MECHANICALLY_ENUMERATED_FROM_ONE_REGISTRY"
    )
    assert sorted(DECISION["child_definition_sha256"]) == sorted(children)
    assert sorted(f"{name}.json" for name in children) == sorted(
        name for name, _ in r5._CHILD_ARTIFACTS
    )
    for name, child in children.items():
        r5._verify_definition_digest(child)
        assert DECISION["child_definition_sha256"][name] == child["definition_sha256"]


def test_the_four_new_children_own_the_exact_identity_correction() -> None:
    registry = dict(r5._CHILD_ARTIFACTS)
    new = [
        "authoritative_execution_identity_rule",
        "identity_safe_snapshot_binding_rule",
        "authority_receiver_validation_rule",
        "construction_identity_audit_rule",
    ]
    for name in new:
        assert f"{name}.json" in registry
        assert name not in R4_PERSISTED_CHILD_HASHES, f"{name} must be new in R5"
    identity = r5.authoritative_execution_identity_rule()
    assert identity["authority_lookup_uses_exact_identity"] is True
    assert identity["receiver_equality_is_authority"] is False
    assert identity["p0_a_unearned_resolution_closed"] is True
    assert identity["p0_b_relay_closed"] is False


R3_PERSISTED_CHILD_HASHES = {
    path.name.removesuffix(".json"): json.loads(path.read_text("ascii"))[
        "definition_sha256"
    ]
    for path in sorted(R3_ARTIFACT_DIR.glob("*.json"))
    if path.name != r3.DEFINITION_FILENAME
}

R4_PERSISTED_CHILD_HASHES = {
    path.name.removesuffix(".json"): json.loads(path.read_text("ascii"))[
        "definition_sha256"
    ]
    for path in sorted(R4_ARTIFACT_DIR.glob("*.json"))
    if path.name != r4.DEFINITION_FILENAME
}


def test_preserved_children_are_byte_identical_to_the_reviewed_pad4_r4() -> None:
    assert len(R4_PERSISTED_CHILD_HASHES) == 30
    carried = sorted(
        name
        for name, digest in DECISION["child_definition_sha256"].items()
        if R4_PERSISTED_CHILD_HASHES.get(name) == digest
    )
    assert carried == sorted(r5.VERBATIM_PAD4_R4_CHILDREN)
    assert len(carried) == 22
    assert DECISION["verbatim_pad4_r4_children"] == list(
        r5.VERBATIM_PAD4_R4_CHILDREN
    )
    changed = sorted(
        name
        for name in DECISION["child_definition_sha256"]
        if name in R4_PERSISTED_CHILD_HASHES and name not in carried
    )
    assert changed == [
        "affirmative_evidence_snapshot_rule",
        "authoritative_scientific_execution_boundary",
        "caller_visible_copy_isolation_rule",
        "canonical_admitted_snapshot_rule",
        "controller_authority_context_rule",
        "proof_order_and_completeness_definition",
        "science_lineage_and_safety",
        "scientific_evidence_authority_rule",
    ]


def test_the_r3_and_r2_byte_identical_provenance_is_still_preserved() -> None:
    """Mechanically, against the persisted ``PAD4-R3`` namespace itself."""

    assert len(R3_PERSISTED_CHILD_HASHES) == 25
    carried = sorted(
        name
        for name, digest in DECISION["child_definition_sha256"].items()
        if R3_PERSISTED_CHILD_HASHES.get(name) == digest
    )
    assert set(r5.VERBATIM_PAD4_R3_CHILDREN) <= set(carried)
    assert len(carried) == 20
    assert DECISION["verbatim_pad4_r3_children"] == list(
        r5.VERBATIM_PAD4_R3_CHILDREN
    )
    # the sixteen that reached PAD4-R3 byte-identically from PAD4-R2 keep that
    # provenance here as well
    for name in r5.VERBATIM_PAD4_R2_CHILDREN:
        assert name in carried, name
    assert len(r5.VERBATIM_PAD4_R2_CHILDREN) == 16


def test_no_material_child_claims_immutability_the_implementation_lacks() -> None:
    """Material-child consistency, which the completed review made in-scope.

    Every child that asserts the authority is immutable is checked against the
    live container rather than trusted: the storage really holds no mutable
    container, the accessors really return detached decodes, and the mechanical
    return-state audit embedded in the isolation child really is closed.
    """

    isolation = r5.caller_visible_copy_isolation_rule()
    snapshot = r5.canonical_admitted_snapshot_rule()
    evidence = r5.affirmative_evidence_snapshot_rule()
    digest = r5.result_digest_lifetime_binding_rule()
    assert isolation["return_state_audit"]["closed"] is True
    assert isolation["return_state_audit"]["findings"] == []
    assert isolation["caller_visible_mutable_result_is_authority_storage"] is False
    assert isolation["caller_visible_mutable_response_is_authority_storage"] is False
    assert isolation["caller_visible_mutable_evidence_is_authority_storage"] is False
    assert isolation["nested_mutable_alias_can_change_authority"] is False
    assert isolation["mapping_proxy_outer_wrapper_is_the_mechanism"] is False
    assert isolation["shallow_copy_is_the_mechanism"] is False
    assert isolation["deep_copy_of_a_mutable_graph_is_the_mechanism"] is False
    assert isolation["a_class_member_returns_the_authority_storage"] is False
    assert isolation["class_surface_is_a_verified_enumeration_not_an_allow_list"] is (
        True
    )
    assert isolation["authority_storage_reader_is_closure_local_and_not_a_member"] is (
        True
    )
    # honest about the reflection carve-out rather than overclaiming, and checked
    # against the live objects rather than re-asserted against itself
    assert isolation["reflective_recovery_of_the_storage_is_claimed_impossible"] is (
        False
    )
    assert isolation["authority_storage_reachable_through_a_declared_member"] is False
    assert isolation["authority_storage_reachable_through_closure_cells"] is True
    assert isolation["reflectively_recovered_snapshot_is_immutable"] is True
    assert isolation["reflectively_recovered_binding_container_is_mutable"] is True
    execution = _run(SESSION_REQUEST)
    assert execution.admitted is True, execution.failure_reason
    reader = inspect.getclosurevars(
        vars(r5.AuthoritativeScientificExecution)["admitted"].fget
    ).nonlocals[r5.AUTHORITY_STORAGE_READER]
    container = inspect.getclosurevars(reader).nonlocals[r5.AUTHORITY_STORAGE_NAME]
    # the binding container really is mutable, exactly as the child discloses ...
    assert hasattr(container, "__setitem__")
    assert not isinstance(container, tuple)
    # ... and every value it holds really is an immutable snapshot
    entry = container[id(execution)]
    assert entry.witness() is execution
    stored = entry.snapshot
    assert isinstance(stored, r5.FrozenAuthoritySnapshot)
    assert isinstance(stored, tuple)
    for member in r5.MUTATING_CONTAINER_MEMBERS:
        assert not hasattr(stored, member), member
    rule = r5.authoritative_return_state_rule()
    assert rule["authority_snapshot_has_a_mutating_api"] is False
    assert rule["authority_snapshot_is_an_immutable_tuple"] is True
    assert rule["a_class_member_hands_the_authority_storage_to_a_caller"] is False
    assert rule["a_refusal_can_be_promoted_to_an_admitted_execution"] is False
    assert snapshot["authority_snapshot_type"] == "FrozenAuthoritySnapshot"
    assert snapshot["authority_binding_container_is_mutable"] is True
    assert snapshot["authority_binding_container_carries_authority_content"] is False
    assert snapshot[
        "authority_binding_container_resolves_keys_by_equality_not_identity"
    ] is False
    assert snapshot["receiver_is_a_mapping_key"] is False
    assert snapshot["bare_id_bucket_is_authority"] is False
    assert snapshot["subclassing_the_authoritative_execution_is_refused"] is True
    assert snapshot["immutability_gate_is_the_only_write_path_into_authority"] is True
    assert snapshot["immutability_gate_refusals_are_mechanically_exercised"] is True
    assert digest["a_refusal_can_be_given_an_admitted_result_digest"] is False
    assert digest["snapshot_proof_reports_unbound_digests_as_unbound"] is True
    assert snapshot["authority_snapshot_holds_a_mutable_container"] is False
    assert snapshot["authority_snapshot_holds_a_nested_mutable_descendant"] is False
    assert snapshot["second_canonical_encoding_introduced"] is False
    assert snapshot["canonicalization_is_the_reviewed_worker_protocol"] is True
    assert snapshot["frozen_authority_fields"] == list(r5.FROZEN_AUTHORITY_FIELDS)
    assert evidence["evidence_is_stored_as_immutable_canonical_bytes"] is True
    assert evidence["evidence_constructed_from_caller_facing_copies"] is False
    assert digest["result_digest_binds_exact_frozen_result_snapshot"] is True
    assert digest["digest_is_recomputed_from_a_caller_visible_object"] is False
    assert digest["digest_is_recomputed_on_read_to_match_live_state"] is False


def test_central_decisions_bind_the_return_state_anchors() -> None:
    central = DECISION["central_decisions"]
    assert central["authority_lookup_uses_exact_identity"] is True
    assert central["receiver_equality_is_authority"] is False
    assert central["receiver_hash_equivalence_is_authority"] is False
    assert central["identity_safe_lookup_is_load_bearing"] is True
    assert central["exact_type_guard_is_load_bearing"] is False
    assert central["relay_residual_closed"] is False
    assert central["admitted_authority_uses_immutable_canonical_snapshot"] is True
    assert central["caller_visible_mutable_result_is_authority_storage"] is False
    assert central["caller_visible_mutable_response_is_authority_storage"] is False
    assert central["caller_visible_mutable_evidence_is_authority_storage"] is False
    assert central["nested_mutable_alias_can_change_authority"] is False
    assert central["result_digest_binds_exact_frozen_result_snapshot"] is True
    assert central["post_admission_mutation_can_redefine_authority"] is False
    assert central["authority_is_recomputed_from_caller_mutated_live_state"] is False
    assert central["outer_only_read_only_wrapper_is_sufficient"] is False
    assert central["closed_r3_authority_flow_preserved"] is True
    assert central["bootstrap_architecture_reopened"] is False
    assert central["worker_protocol_reopened"] is False
    assert central["authority_is_repaired_on_read"] is False
    assert central["authority_bearing_mutable_mapping_retained_internally"] is False
    assert central["admission_decision_procedure_changed_by_this_decision"] is False
    assert central["construction_authority_weakened_by_this_decision"] is False
    assert central["second_canonical_encoding_introduced_by_this_decision"] is False
    assert central["worker_package_changed_by_this_decision"] is False
    assert central["i2_calendar_production_work_performed"] is False


def test_the_reviewed_r4_central_decisions_are_carried_forward() -> None:
    """Nothing the reviewed ``PAD4-R4`` parent decided is silently dropped."""

    r3_central = r4.isolated_scientific_worker_v1_r4_definition()["central_decisions"]
    central = DECISION["central_decisions"]
    missing = sorted(set(r3_central) - set(central))
    assert missing == []
    disagreeing = sorted(
        name for name, value in r3_central.items() if central[name] != value
    )
    assert disagreeing == []


def test_preserved_portions_and_the_not_reopened_scope_are_explicit() -> None:
    preserved = set(DECISION["preserved_valid_portions"])
    assert set(r4.PRESERVED_VALID_PORTIONS) <= preserved
    assert {
        "AUTHORITATIVE_SCIENTIFIC_EXECUTION_CLOSURE",
        "CAPABILITY_OWNED_CONSTRUCTION_AUTHORITY",
        "CLOSED_ONE_OPERATION_AUTHORITY_FLOW",
        "SCIENTIFIC_ADMISSION_DECISION_PROCEDURE",
    } <= preserved
    not_reopened = set(DECISION["not_reopened"])
    assert set(r4.NOT_REOPENED) <= not_reopened
    assert {
        "AUTHORITATIVE_EXECUTION_CONSTRUCTION_AUTHORITY",
        "CLOSED_CONTROLLER_AUTHORITY_FLOW",
        "PROCESS_ISOLATION_ARCHITECTURE",
        "SCIENTIFIC_ADMISSION_DECISION_PROCEDURE",
        "THIRD_PARTY_RECORD_AND_CONTENT_AUTHORITY",
        "WORKER_PROTOCOL",
    } <= not_reopened
    assert DECISION["confirmed_not_a_defect"] == list(r4.CONFIRMED_NOT_A_DEFECT)
    assert DECISION["closed_reviewed_bypasses"] == list(r3.CLOSED_REVIEWED_BYPASSES)
    assert DECISION["closed_reviewed_return_state_mutations"] == list(
        r5.CLOSED_REVIEWED_RETURN_STATE_MUTATIONS
    )


def test_the_whole_failed_lineage_is_preserved_immutably() -> None:
    lineage = r5.science_lineage_and_safety()
    hashes = [
        row["definition_sha256"] for row in lineage["failed_architecture_lineage"]
    ]
    # the accumulated lineage is every failed predecessor, with PAD4 through
    # the newly failed PAD4-R4 occupying the final five entries
    assert hashes == list(r5.FAILED_ARCHITECTURE_LINEAGE)
    assert hashes[:-1] == list(r4.FAILED_ARCHITECTURE_LINEAGE)
    assert hashes[-5:] == [
        r5.FAILED_PAD4_SHA256,
        r5.FAILED_PAD4_R1_SHA256,
        r5.FAILED_PAD4_R2_SHA256,
        r5.FAILED_PAD4_R3_SHA256,
        r5.FAILED_PAD4_R4_SHA256,
    ]
    assert len(set(hashes)) == len(hashes)
    for row in lineage["failed_architecture_lineage"]:
        assert row["certified"] is False
        assert row["failed"] is True
        assert row["used"] is False
        assert row["prospective_observations"] == 0
        assert row["immutable"] is True
    predecessor = lineage["corrected_predecessor"]
    assert predecessor["definition_sha256"] == (
        "ae25c2468972725a0ebd2f7742a532f3ec616c2e2cc8e94d93b3de46f86e65bc"
    )
    assert predecessor["implementation_commit"] == (
        "90fcf88a7be65bd43cefeb0eb766cccde766d6ae"
    )
    assert predecessor["decision_record_commit"] == (
        "1d6cfdb16361c9c25eadccf4977fd39cf335eaa0"
    )
    assert predecessor["review"] == "POSTP1-002V2A-PAD4-R4"
    assert predecessor["review_result"] == (
        "FAIL — AUTHORITATIVE EXECUTION CONSTRUCTION BOUNDARY INVALID"
    )
    assert predecessor["execution_classification"] == (
        "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_R4_REQUIRES_FIX"
    )
    assert predecessor["material_children"] == 30
    assert predecessor["artifacts_overwritten_by_this_correction"] is False
    assert predecessor["namespace_mutated_by_this_correction"] is False
    assert predecessor["prospective_observations"] == 0
    assert DECISION["failed_pad4_r3_certified"] is False
    assert DECISION["failed_pad4_r3_artifacts_overwritten"] is False
    assert DECISION["failed_pad4_r3_namespace_mutated"] is False


def test_the_failed_r4_namespace_still_reproduces_untouched() -> None:
    """R5 must not have disturbed the immutable failed ``PAD4-R4`` evidence."""

    persisted = r4.restore_artifacts(R4_ARTIFACT_DIR)
    assert persisted["definition_sha256"] == r5.FAILED_PAD4_R4_SHA256
    assert persisted["material_child_count"] == 30
    assert persisted["status"] == (
        "FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_FINAL_XHIGH_REVIEW"
    )


def test_trusted_persistence_authority_is_unchanged_and_not_re_reviewed() -> None:
    lineage = r5.science_lineage_and_safety()
    assert lineage["trusted_persistence_authority"] == {
        "definition_sha256": r5.CERTIFIED_DEPENDENCY_SHA256,
        "status": "CLOSED_CERTIFIED_UNCHANGED",
        "re_reviewed_by_this_decision": False,
    }
    assert DECISION["certified_dependency_sha256"] == r5.CERTIFIED_DEPENDENCY_SHA256


def test_write_and_restore_artifacts_round_trip(tmp_path: Path) -> None:
    decision = r5.write_artifacts(tmp_path / "out")
    assert decision == DECISION
    assert r5.restore_artifacts(tmp_path / "out") == DECISION


def test_persisted_namespace_reproduces_exactly() -> None:
    assert r5.restore_artifacts(ARTIFACT_DIR) == DECISION


def test_restore_refuses_a_mutated_child(tmp_path: Path) -> None:
    r5.write_artifacts(tmp_path / "out")
    target = tmp_path / "out" / "authoritative_return_state_rule.json"
    payload = json.loads(target.read_text("ascii"))
    payload["post_admission_mutation_can_redefine_authority"] = True
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", "ascii")
    with pytest.raises(r5.IsolatedScientificWorkerR5Error):
        r5.restore_artifacts(tmp_path / "out")


def test_restore_refuses_a_mutated_report(tmp_path: Path) -> None:
    r5.write_artifacts(tmp_path / "out")
    target = tmp_path / "out" / r5.REPORT_FILENAME
    target.write_text(target.read_text("utf-8") + "\ndrift\n", "utf-8")
    with pytest.raises(r5.IsolatedScientificWorkerR5Error):
        r5.restore_artifacts(tmp_path / "out")


def test_child_order_variation_does_not_change_the_parent() -> None:
    reversed_registry = tuple(reversed(r5._CHILD_ARTIFACTS))
    assert r5.isolated_scientific_worker_v1_r5_definition(reversed_registry) == DECISION


def test_candidate_hash_is_not_embedded_in_its_own_certified_source() -> None:
    source = (ROOT / r5.CONTROLLER_RELATIVE_PATH).read_text("utf-8")
    assert CANDIDATE_HASH not in source
    assert DECISION["central_decisions"]["candidate_parent_hash_self_embedded"] is False


MATERIAL_MUTATIONS = [
    # -- the R5 correction, one entry per frozen decision POSTP1-001V2A-PAD4-R5
    #    is required to be sensitive to
    ("authoritative_execution_identity_rule", "authority_lookup_uses_exact_identity"),
    ("authoritative_execution_identity_rule", "receiver_equality_is_authority"),
    ("identity_safe_snapshot_binding_rule",
     "receiver_keyed_mapping_is_authority_registry"),
    ("identity_safe_snapshot_binding_rule", "weakref_keyed_mapping_is_identity_safe"),
    ("identity_safe_snapshot_binding_rule", "bare_id_bucket_is_authority"),
    ("identity_safe_snapshot_binding_rule", "live_witness_identity_check_required"),
    ("identity_safe_snapshot_binding_rule", "receiver_none_rejected"),
    ("identity_safe_snapshot_binding_rule", "conditional_cleanup_required"),
    ("identity_safe_snapshot_binding_rule",
     "receiver_controlled_hash_eq_executes_in_authority_lookup"),
    ("authority_receiver_validation_rule", "exact_type_guard_required"),
    ("authority_receiver_validation_rule", "exact_type_guard_is_load_bearing"),
    ("authoritative_scientific_execution_boundary", "authority_reader_count"),
    ("authoritative_scientific_execution_boundary", "authority_bind_count"),
    ("identity_safe_snapshot_binding_rule", "lookup_cache_permitted"),
    ("authoritative_execution_identity_rule", "p0_b_relay_closed"),
    ("authoritative_return_state_rule",
     "admitted_authority_uses_immutable_canonical_snapshot"),
    ("authoritative_return_state_rule",
     "post_admission_mutation_can_redefine_authority"),
    ("authoritative_return_state_rule",
     "authority_is_recomputed_from_caller_mutated_live_state"),
    ("authoritative_return_state_rule", "outer_only_read_only_wrapper_is_sufficient"),
    ("authoritative_return_state_rule", "rule"),
    ("caller_visible_copy_isolation_rule",
     "caller_visible_mutable_result_is_authority_storage"),
    ("caller_visible_copy_isolation_rule",
     "caller_visible_mutable_response_is_authority_storage"),
    ("caller_visible_copy_isolation_rule",
     "caller_visible_mutable_evidence_is_authority_storage"),
    ("caller_visible_copy_isolation_rule",
     "nested_mutable_alias_can_change_authority"),
    ("caller_visible_copy_isolation_rule", "return_state_audit"),
    ("caller_visible_copy_isolation_rule", "accessor_mechanism"),
    ("caller_visible_copy_isolation_rule", "a_class_member_returns_the_authority_storage"),
    ("canonical_admitted_snapshot_rule", "frozen_authority_fields"),
    ("canonical_admitted_snapshot_rule", "authority_snapshot_has_a_mutating_api"),
    ("canonical_admitted_snapshot_rule",
     "authority_binding_container_resolves_keys_by_equality_not_identity"),
    ("canonical_admitted_snapshot_rule",
     "subclassing_the_authoritative_execution_is_refused"),
    ("canonical_admitted_snapshot_rule",
     "immutability_gate_is_the_only_write_path_into_authority"),
    ("canonical_admitted_snapshot_rule", "preserved_canonical_rejections"),
    ("authoritative_return_state_rule",
     "a_refusal_can_be_promoted_to_an_admitted_execution"),
    ("authoritative_return_state_rule",
     "authority_snapshot_is_an_immutable_tuple"),
    ("authoritative_scientific_execution_boundary",
     "no_class_member_returns_authority_storage"),
    ("canonical_admitted_snapshot_rule",
     "authority_snapshot_holds_a_mutable_container"),
    ("canonical_admitted_snapshot_rule", "canonical_encoder"),
    ("result_digest_lifetime_binding_rule",
     "result_digest_binds_exact_frozen_result_snapshot"),
    ("result_digest_lifetime_binding_rule",
     "digest_is_recomputed_on_read_to_match_live_state"),
    ("affirmative_evidence_snapshot_rule",
     "evidence_is_stored_as_immutable_canonical_bytes"),
    ("affirmative_evidence_snapshot_rule", "affirmative_authority_marker"),
    ("authoritative_scientific_execution_boundary",
     "closed_r3_authority_flow_preserved"),
    ("authoritative_scientific_execution_boundary",
     "post_admission_representation_is_immutable"),
    ("authoritative_scientific_execution_boundary", "authoritative_execution_order"),
    ("authoritative_scientific_execution_boundary", "frozen_authority_fields"),
    ("authoritative_scientific_execution_boundary", "api_closure_audit"),
    ("authoritative_scientific_execution_boundary", "direct_worker_launch_census"),
    ("scientific_evidence_authority_rule",
     "affirmative_scientific_evidence_is_stored_as_immutable_canonical_bytes"),
    # -- the R3 correction, preserved and still sensitive
    ("admission_provenance_rule", "bootstrap_preverification_required_before_spawn"),
    ("admission_provenance_rule",
     "unverified_worker_outcome_scientifically_admissible"),
    ("admission_provenance_rule", "caller_constructed_outcome_is_authority"),
    ("admission_provenance_rule", "caller_constructed_admission_state_is_authority"),
    ("scientific_evidence_authority_rule",
     "affirmative_scientific_evidence_created_only_inside_authoritative_path"),
    ("authoritative_scientific_execution_boundary",
     "caller_may_construct_the_authoritative_execution"),
    ("authoritative_scientific_execution_boundary",
     "leading_underscore_is_authority_boundary"),
    ("controller_result_admission_rule",
     "admission_requires_the_same_authoritative_controller_execution"),
    # -- preserved portions that must stay sensitive
    ("bootstrap_pre_execution_source_binding_rule", "bootstrap_mismatch_spawns_worker"),
    ("bootstrap_source_set", "bootstrap_manifest_digest"),
    ("bytecode_execution_binding_rule",
     "cached_bytecode_may_override_certified_source"),
    ("bytecode_execution_binding_rule", "fresh_cache_namespace_per_worker"),
    ("project_source_manifest_binding_rule",
     "runtime_source_manifest_rederivation_permitted"),
    ("third_party_installed_content_attestation_rule",
     "record_declared_installed_file_hashes_must_be_verified"),
    ("compiled_root_binding_witness_rule", "root_cell_prohibition_is_structural"),
    ("compiled_root_binding_witness_rule", "root_may_be_a_cell_variable_of_the_owner"),
    ("store_root_and_direct_use_grammar",
     "root_may_be_a_cell_variable_of_a_conforming_owner"),
    ("direct_body_dependency_rule", "required_direct_bodies"),
    ("direct_body_dependency_rule", "exact_dependency_assertion"),
    ("replay_owner_graph_rule", "contract_version"),
    ("controller_authority_context_rule", "request_is_authority_root"),
    ("proof_order_and_completeness_definition", "controller_admission_order"),
]


@pytest.mark.parametrize("child,field", MATERIAL_MUTATIONS)
def test_material_mutation_moves_both_child_and_parent_hashes(
    child: str, field: str
) -> None:
    builders = dict(r5._CHILD_ARTIFACTS)
    original = builders[f"{child}.json"]()
    assert field in original, sorted(original)

    def mutated() -> dict:
        payload = {
            name: value
            for name, value in original.items()
            if name != "definition_sha256"
        }
        payload[field] = "MATERIAL_MUTATION_PROBE"
        return r5._definition(payload)

    registry = tuple(
        (name, mutated if name == f"{child}.json" else builder)
        for name, builder in r5._CHILD_ARTIFACTS
    )
    assert mutated()["definition_sha256"] != original["definition_sha256"]
    assert (
        r5.isolated_scientific_worker_v1_r5_definition(registry)["definition_sha256"]
        != CANDIDATE_HASH
    )


@pytest.mark.parametrize("seed", ["0", "1", "8675309"])
def test_definition_is_deterministic_across_hash_seeds(
    seed: str, tmp_path: Path
) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "from btc_predictor.research import "
            "etf_calendar_isolated_scientific_worker_r5 as r5;"
            "print(r5.isolated_scientific_worker_v1_r5_definition()"
            "['definition_sha256'])",
        ],
        capture_output=True,
        check=True,
        cwd=str(tmp_path),
        env={**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(ROOT)},
    )
    assert completed.stdout.decode().strip() == CANDIDATE_HASH


def test_a_diagnostic_re_export_does_not_move_the_parent_hash() -> None:
    """Section 51: the parent must be a function of the frozen source.

    The launch census names every inherited helper that creates a process, and it
    keys each row on the resolved callable rather than on the module attribute
    pointing at it, so adding a second name for an already declared non-worker
    helper cannot move the hash for a non-material reason.
    """

    module = sys.modules[r5.__name__]
    setattr(module, "a_diagnostic_alias", r5.interpreter_base_sys_path)
    try:
        census = r5.audit_direct_worker_launch_census()
        assert census["closed"] is True, census["findings"]
        assert census["production_reachable_inherited_launch_sites"] == [
            {
                "callable": "interpreter_base_sys_path",
                "defining_module": "etf_calendar_isolated_scientific_worker_r1",
                "primitive": "subprocess.run",
                "qualname": "interpreter_base_sys_path",
            }
        ]
        assert (
            r5.isolated_scientific_worker_v1_r5_definition()["definition_sha256"]
            == CANDIDATE_HASH
        )
    finally:
        delattr(module, "a_diagnostic_alias")
    assert r5.isolated_scientific_worker_v1_r5_definition() == DECISION


def test_artifacts_reproduce_from_an_alternate_working_directory(
    tmp_path: Path,
) -> None:
    output = tmp_path / "fresh"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "btc_predictor.research.etf_calendar_isolated_scientific_worker_r5",
            str(output),
        ],
        capture_output=True,
        check=True,
        cwd=str(tmp_path),
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    assert completed.stdout.decode().strip() == CANDIDATE_HASH
    assert r5.restore_artifacts(output) == DECISION
    for filename in sorted(p.name for p in ARTIFACT_DIR.iterdir()):
        assert (output / filename).read_bytes() == (ARTIFACT_DIR / filename).read_bytes()


# ---------------------------------------------------------------------------
# Mechanical API closure, return-state audit and launch census
# ---------------------------------------------------------------------------


def test_the_scientific_api_closure_audit_is_closed() -> None:
    audit = r5.audit_scientific_api_closure()
    assert audit["closed"] is True, audit["findings"]
    assert audit["findings"] == []
    assert audit["module_accessible_authority_bearing_operations"] == 1
    assert audit["authoritative_production_operation"] == (
        "run_isolated_scientific_request"
    )
    assert len(audit["production_launch_sites"]) == 1
    assert audit["production_launch_sites"][0]["scope"] == [
        r5.AUTHORITY_OWNING_FACTORY,
        "_execute_exact_worker",
    ]
    assert len(audit["authoritative_execution_construction_sites"]) == 1
    assert audit["authoritative_execution_construction_sites"][0]["scope"] == [
        r5.AUTHORITY_OWNING_FACTORY,
        "run_isolated_scientific_request",
    ]
    assert audit["authoritative_execution_undeclared_construction_sites"] == []
    # the return-state audit's own refusal probes are declared rather than hidden
    # behind indirection that the AST census could not see
    assert audit["authoritative_execution_declared_refusal_probe_scopes"] == [
        ["audit_authoritative_execution_identity"],
        ["audit_authoritative_return_state"]
    ]
    assert audit["authoritative_execution_refusal_probe_sites"] == [
        {"scope": ["audit_authoritative_execution_identity"]},
        {"scope": ["audit_authoritative_return_state"]},
        {"scope": ["audit_authoritative_return_state"]},
    ]
    assert len(audit["affirmative_marker_construction_sites"]) == 1
    assert audit["affirmative_marker_construction_sites"][0]["scope"] == [
        r5.AUTHORITY_OWNING_FACTORY,
        "_affirmative_scientific_evidence",
    ]
    assert audit["affirmative_marker_undeclared_sites"] == []
    assert audit["authority_owning_factory_is_module_accessible"] is False
    assert audit["forbidden_authority_names_defined"] == []
    assert audit["forbidden_authority_names_reexported"] == []
    assert audit["module_attributes_bound_to_failed_lineage"] == []
    # the identity comparisons above are only meaningful where the lineage module
    # defines the name, so the audit records that coverage instead of leaving an
    # empty result indistinguishable from an inapplicable check
    coverage = audit["forbidden_authority_name_lineage_coverage"]
    assert coverage["etf_calendar_isolated_scientific_worker_r2"] == sorted(
        r5.FORBIDDEN_PRODUCTION_AUTHORITY_NAMES
    )
    assert coverage["etf_calendar_isolated_scientific_worker_r3"] == []
    assert coverage["etf_calendar_isolated_scientific_worker_r4"] == []
    for name in r5.FORBIDDEN_PRODUCTION_AUTHORITY_NAMES:
        assert hasattr(r2, name)
        assert not hasattr(r3, name)
    assert all(audit["affirmative_marker_free_modules"].values())
    assert sorted(audit["affirmative_marker_free_modules"]) == sorted(
        [*r5.FAILED_LINEAGE_CONTROLLER_MODULES, r5.RAW_REVIEW_HARNESS_RELATIVE_PATH]
    )
    assert r3.CONTROLLER_RELATIVE_PATH in audit["affirmative_marker_free_modules"]
    assert audit["authority_owned_steps"] == [
        "_affirmative_scientific_evidence",
        "_bind",
        "_execute_exact_worker",
        "_frozen",
        "_validate_and_admit",
        "run_isolated_scientific_request",
    ]
    # exactly one of the owned steps is module-accessible: the one operation
    for step in audit["authority_owned_steps"]:
        assert hasattr(r5, step) is (step == "run_isolated_scientific_request"), step


def test_the_authoritative_return_state_audit_is_closed() -> None:
    """The R5 correction's own mechanical audit, structural and behavioural."""

    audit = r5.audit_authoritative_return_state()
    assert audit["closed"] is True, audit["findings"]
    assert audit["findings"] == []
    # (1) one bind, one read and conditional callback cleanup are the only uses
    assert audit["authority_storage_references"] == [
        {"scope": [r5.AUTHORITY_OWNING_FACTORY], "context": "Store"},
        {
            "scope": [r5.AUTHORITY_OWNING_FACTORY, r5.AUTHORITY_STORAGE_BINDER],
            "context": "Load",
        },
        {
            "scope": [r5.AUTHORITY_OWNING_FACTORY, r5.AUTHORITY_STORAGE_READER],
            "context": "Load",
        },
        {
            "scope": [
                r5.AUTHORITY_OWNING_FACTORY,
                r5.AUTHORITY_STORAGE_BINDER,
                r5.AUTHORITY_STORAGE_CLEANUP,
            ],
            "context": "Load",
        },
        {
            "scope": [
                r5.AUTHORITY_OWNING_FACTORY,
                r5.AUTHORITY_STORAGE_BINDER,
                r5.AUTHORITY_STORAGE_CLEANUP,
            ],
            "context": "Load",
        },
    ]
    assert audit["authority_storage_references"] == (
        audit["declared_authority_storage_references"]
    )
    assert audit["authority_storage_write_sites"] == [
        {
            "scope": [
                r5.AUTHORITY_OWNING_FACTORY,
                r5.AUTHORITY_STORAGE_BINDER,
            ],
            "value": "NAME",
        }
    ]
    assert audit["authority_storage_reader_scopes"] == [[r5.AUTHORITY_OWNING_FACTORY]]
    assert audit["construction_site_material_fields"] == sorted(
        r5.FROZEN_AUTHORITY_FIELDS
    )
    # (2) the immutability gate is actually exercised, not merely named
    assert audit["authority_immutability_gate"] == "verify_frozen_authority_snapshot"
    assert audit["authority_immutability_gate_probes"] == {
        "COMPLETE_IMMUTABLE_SNAPSHOT": "ACCEPTED_AS_FROZEN_SNAPSHOT",
        "EXTRA_FIELD": "REFUSED",
        "MISSING_FIELD": "REFUSED",
        "MUTABLE_BYTEARRAY_VALUE": "REFUSED",
        "MUTABLE_MAPPING_VALUE": "REFUSED",
        "MUTABLE_SEQUENCE_VALUE": "REFUSED",
        "MUTABLE_SET_VALUE": "REFUSED",
        "NOT_A_MAPPING": "REFUSED",
    }
    # (2b) construction authority is probed behaviourally, not only the gate
    assert audit["construction_authority_probes"] == {
        "DIRECT_CONSTRUCTION": "REFUSED",
        "FORGED_CAPABILITY": "REFUSED",
        "NEW_BYPASS_MAPPING_ACCESSOR": "REFUSED",
        "NEW_BYPASS_SCALAR_ACCESSOR": "REFUSED",
        "NEW_BYPASS_SNAPSHOT_PROOF": "REFUSED",
        "SUBCLASS": "REFUSED",
    }
    assert audit["subclassing_the_authoritative_execution_is_refused"] is True
    assert audit[
        "authority_storage_binding_is_resolved_by_equality_not_identity"
    ] is False
    assert audit["construction_identity_audit"]["closed"] is True
    # (3) the stored snapshot type is genuinely immutable
    assert audit["frozen_authority_snapshot_type"] == {
        "name": "FrozenAuthoritySnapshot",
        "is_tuple_subclass": True,
        "fields": list(r5.FROZEN_AUTHORITY_FIELDS),
        "mutating_members_present": [],
        "has_instance_dictionary": False,
    }
    # (4) the live class surface is a verified enumeration, not an allow-list
    assert audit["live_class_members"] == sorted(r5.AUTHORITATIVE_EXECUTION_MATERIAL)
    assert audit["returning_class_members"] == sorted(
        (*r5.AUTHORITATIVE_EXECUTION_MATERIAL, *r5.DECLARED_NON_MATERIAL_MEMBERS)
    )
    for name in r5.MUTABLE_CONVENIENCE_ACCESSORS:
        assert audit["material_member_return_mechanisms"][name] == [
            "protocol.parse_canonical_json"
        ]
    for name in r5.IMMUTABLE_CONVENIENCE_ACCESSORS:
        assert audit["material_member_return_mechanisms"][name] == ["ATTRIBUTE"]
    assert audit["material_member_return_mechanisms"][
        "authoritative_snapshot_proof"
    ] == ["DICT"]
    # every accessor reads the frozen field it is declared to read
    for name, field in r5.ACCESSOR_FROZEN_FIELDS.items():
        assert audit["material_member_frozen_field_reads"][name] == [field]
    # (5) and (6)
    assert audit["prohibited_mechanism_sites"] == []
    assert audit["declared_slots"] == ["__weakref__"]
    assert audit["container_has_instance_dictionary"] is False
    assert all(
        row["is_read_only_property"]
        for row in audit["caller_facing_accessor_descriptors"].values()
    )


def test_the_construction_identity_audit_is_live_surface_complete() -> None:
    audit = r5.audit_authoritative_execution_identity()
    assert audit["closed"] is True, audit["findings"]
    assert audit["findings"] == []
    expected = sorted(
        [
            "__repr__",
            "admitted",
            "authoritative_snapshot_proof",
            "failure_reason",
            "request_digest",
            "response",
            "result",
            "scientific_evidence",
        ]
    )
    assert audit["authority_bearing_members"] == expected
    assert audit["authority_bearing_properties"] == sorted(
        ["admitted", "failure_reason", "request_digest", "response", "result",
         "scientific_evidence"]
    )
    assert [row["member"] for row in audit["snapshot_lookup_sites"]] == expected
    assert audit["authority_reader_count"] == 1
    assert audit["authority_bind_count"] == 1
    assert len(audit["authority_bind_insertions"]) == 1
    assert len(audit["authority_bind_snapshot_gate_calls"]) == 1
    assert audit["authority_bind_capability_tests"] == [
        "capability is not _capability"
    ]
    assert audit["registry_fetch_count_in_authority_reader"] == 1
    assert audit["receiver_keyed_mapping"] is False
    assert audit["weakref_keyed_authority_mapping"] is False
    assert audit["bare_id_is_authority"] is False
    assert audit["authority_lookup_uses_exact_identity"] is True
    assert audit["final_authority_predicate"] == "live_witness is receiver"
    assert audit["receiver_none_rejected"] is True
    assert audit["exact_type_guard"] == "type(receiver) is canonical class"
    assert audit["exact_type_guard_is_load_bearing"] is False
    assert audit["identity_comparison_is_load_bearing"] is True
    assert audit["receiver_controlled_operations_in_lookup"] == []
    assert audit["receiver_controlled_hash_or_equality_executed"] is False
    assert audit["receiver_controlled_code_executed"] == []
    assert audit["authoritative_execution_eq_is_object_eq"] is True
    assert audit["authoritative_execution_hash_is_object_hash"] is True
    assert set(audit["exact_owner_outcomes"].values()) == {"AUTHORITY_AVAILABLE"}
    assert set(audit["descriptor_reuse_outcomes"].values()) == {"REFUSED"}
    assert set(audit["spoofed_class_outcomes"].values()) == {"REFUSED"}
    assert set(audit["receiver_controlled_code_outcomes"].values()) == {"REFUSED"}
    assert set(audit["exact_class_unowned_outcomes"].values()) == {"REFUSED"}
    assert audit["direct_construction"] == "REFUSED"
    assert audit["unsupported_subclass"] == "REFUSED"
    assert audit["identity_refusal_message_is_uniform"] is True
    assert audit["stale_cleanup_preserved_newer_entry"] is True
    assert audit["same_bucket_different_live_witness"] == "REFUSED"
    assert audit["exact_owner_still_resolves_after_collision_probe"] is True
    assert audit["dead_execution_collected"] is True
    assert audit["dead_execution_bucket_removed"] is True
    assert audit["concurrency"] == "NOT_SUPPORTED_OUTSIDE_CURRENT_CONTRACT"


def test_no_class_member_hands_out_the_authority_storage(admitted_session) -> None:
    """The class the caller receives exposes only its declared material.

    ``PAD4-R3`` exposed a ``_owned()`` method that returned the live storage, and
    a leading underscore is explicitly not a boundary in this architecture.  R5's
    single storage read is a closure-local function, so the class has no member
    that hands the snapshot out at all.
    """

    members = sorted(
        name
        for name in vars(r5.AuthoritativeScientificExecution)
        if not (name.startswith("__") and name.endswith("__"))
    )
    assert members == sorted(r5.AUTHORITATIVE_EXECUTION_MATERIAL)
    assert "_owned" not in members
    assert not hasattr(admitted_session, "_owned")
    assert not hasattr(admitted_session, r5.AUTHORITY_STORAGE_NAME)
    assert not hasattr(admitted_session, r5.AUTHORITY_STORAGE_READER)
    # and nothing a member returns is the storage: every returned value is either
    # an immutable scalar or a freshly decoded, detached structure
    for name in r5.IMMUTABLE_CONVENIENCE_ACCESSORS:
        assert isinstance(
            getattr(admitted_session, name), r5.IMMUTABLE_AUTHORITY_VALUE_TYPES
        )
    for name in r5.MUTABLE_CONVENIENCE_ACCESSORS:
        first = getattr(admitted_session, name)
        second = getattr(admitted_session, name)
        assert first == second and first is not second
    proof = admitted_session.authoritative_snapshot_proof()
    assert proof["authority_snapshot_type"] == "FrozenAuthoritySnapshot"
    assert proof["authority_snapshot_is_immutable"] is True
    assert proof["bound_digests_reproduce"] is True
    assert proof["result_digest_is_bound"] is True
    assert proof["unbound_digest_names"] == []


def test_the_frozen_authority_snapshot_has_no_mutating_api() -> None:
    """Freezing only the members of a mutable container is not sufficient."""

    assert issubclass(r5.FrozenAuthoritySnapshot, tuple)
    assert r5.FrozenAuthoritySnapshot._fields == r5.FROZEN_AUTHORITY_FIELDS
    assert "__dict__" not in vars(r5.FrozenAuthoritySnapshot)
    for member in r5.MUTATING_CONTAINER_MEMBERS:
        assert not hasattr(r5.FrozenAuthoritySnapshot, member), member
    snapshot = r5.verify_frozen_authority_snapshot(
        {
            "admitted": False,
            "affirmative_evidence_bytes": b"null",
            "affirmative_evidence_digest": "",
            "failure_reason": None,
            "request_digest": "",
            "response_bytes": b"null",
            "response_digest": "",
            "result_bytes": b"null",
            "result_digest": None,
        }
    )
    assert isinstance(snapshot, r5.FrozenAuthoritySnapshot)
    with pytest.raises(TypeError):
        snapshot[0] = True  # type: ignore[index]
    with pytest.raises(AttributeError):
        object.__setattr__(snapshot, "admitted", True)
    # _replace makes a new snapshot; it cannot change this one
    assert snapshot._replace(admitted=True).admitted is True
    assert snapshot.admitted is False


def test_the_immutability_gate_refuses_mutable_and_malformed_material() -> None:
    """The gate is module-level precisely so its refusals can be exercised."""

    accepted = {
        "admitted": True,
        "affirmative_evidence_bytes": b"null",
        "affirmative_evidence_digest": "a" * 64,
        "failure_reason": None,
        "request_digest": "b" * 64,
        "response_bytes": b"null",
        "response_digest": "c" * 64,
        "result_bytes": b"null",
        "result_digest": "d" * 64,
    }
    assert isinstance(
        r5.verify_frozen_authority_snapshot(accepted), r5.FrozenAuthoritySnapshot
    )
    refused = [
        {**accepted, "result_bytes": {"state": "MUTABLE"}},
        {**accepted, "result_bytes": ["MUTABLE"]},
        {**accepted, "result_bytes": bytearray(b"null")},
        {**accepted, "response_digest": {"MUTABLE"}},
        {**accepted, "injected": "EXTRA"},
        {name: value for name, value in accepted.items() if name != "admitted"},
        ["not", "a", "mapping"],
        None,
    ]
    for material in refused:
        with pytest.raises(r5.AuthoritativeExecutionConstructionError):
            r5.verify_frozen_authority_snapshot(material)

    # a mapping whose __getitem__ answers differently on a second read cannot be
    # validated on an immutable value and then built from a mutable one
    class Shifting(dict):
        def __init__(self, base):
            super().__init__(base)
            self.reads = 0

        def __getitem__(self, key):
            if key == "result_bytes":
                self.reads += 1
                return b"null" if self.reads == 1 else {"state": "MUTABLE"}
            return super().__getitem__(key)

    produced = r5.verify_frozen_authority_snapshot(Shifting(accepted))
    assert all(
        isinstance(value, r5.IMMUTABLE_AUTHORITY_VALUE_TYPES) for value in produced
    )
    assert isinstance(produced.result_bytes, bytes)
    # the gate is inert: producing a snapshot grants no authority
    snapshot = r5.verify_frozen_authority_snapshot(accepted)
    with pytest.raises(r5.AuthoritativeExecutionConstructionError):
        r5.AuthoritativeScientificExecution(object(), snapshot._asdict())


def test_the_refused_copy_and_wrapper_mechanisms_are_absent_from_the_closure() -> None:
    """A shallow copy, a deep copy of a mutable graph and an outer proxy are out.

    The refused mechanisms are *named* in the controller, as the audited
    prohibition list and in the comments explaining why each one is refused; what
    must be absent is any actual use of them.
    """

    source = (ROOT / r5.CONTROLLER_RELATIVE_PATH).read_text("utf-8")
    for forbidden in (
        "import copy",
        "from copy import",
        "MappingProxyType(",
        "copy.copy(",
        "copy.deepcopy(",
        "copy.replace(",
        "json.loads(json.dumps",
    ):
        assert forbidden not in source, forbidden
    audit = r5.audit_authoritative_return_state()
    assert audit["prohibited_authority_copy_mechanisms"] == [
        "MappingProxyType",
        "copy.copy",
        "copy.deepcopy",
        "copy.replace",
        "json.dumps",
        "json.loads",
        "types.MappingProxyType",
    ]
    assert audit["prohibited_mechanism_sites"] == []


@pytest.mark.parametrize("name", r5.FORBIDDEN_PRODUCTION_AUTHORITY_NAMES)
def test_the_reviewed_authority_escalation_names_do_not_exist(name: str) -> None:
    """The ``PAD4-R2`` composition surface stays removed, not merely renamed."""

    assert not hasattr(r5, name), name
    assert not hasattr(r3, name), name
    assert hasattr(r2, name), f"{name} must still exist in the preserved R2 module"


def test_no_module_attribute_is_bound_to_a_failed_lineage_authority_name() -> None:
    forbidden = [
        getattr(module, name)
        for module in (r2,)
        for name in r5.FORBIDDEN_PRODUCTION_AUTHORITY_NAMES
        if hasattr(module, name)
    ]
    assert len(forbidden) == len(r5.FORBIDDEN_PRODUCTION_AUTHORITY_NAMES)
    for name in dir(r5):
        value = getattr(r5, name)
        assert not any(value is banned for banned in forbidden), name


def test_the_direct_worker_launch_census_is_closed() -> None:
    census = r5.audit_direct_worker_launch_census()
    assert census["closed"] is True, census["findings"]
    assert census["production_scientific_authority_launch_sites"] == 1
    assert census["certified_worker_source_launch_sites"] == 0
    assert census["undeclared_production_reachable_launch_sites"] == []
    # 125 surveyed by PAD4-R3, plus the now-superseded PAD4-R3 controller itself
    assert census["surveyed_path_count"] == 127
    harness = [
        site
        for site in census["sites"]
        if site["classification"] == "TEST_AND_REVIEW_HARNESS_ONLY"
    ]
    assert [site["scope"] for site in harness] == [["raw_unverified_worker_execution"]]
    superseded = {
        site["path"]
        for site in census["sites"]
        if site["classification"] == "SUPERSEDED_FAILED_LINEAGE_NOT_R5_AUTHORITY"
    }
    assert r3.CONTROLLER_RELATIVE_PATH in superseded
    assert census["declared_non_worker_launch_sites"] == ["interpreter_base_sys_path"]
    assert [
        site["callable"] for site in census["production_reachable_inherited_launch_sites"]
    ] == ["interpreter_base_sys_path"]


def test_the_raw_harness_is_outside_the_certified_worker_source_universe() -> None:
    paths = {entry.path for entry in MANIFEST}
    assert r5.RAW_REVIEW_HARNESS_RELATIVE_PATH not in paths
    assert r5.CONTROLLER_RELATIVE_PATH not in paths
    assert r3.CONTROLLER_RELATIVE_PATH not in paths
    assert (ROOT / r5.RAW_REVIEW_HARNESS_RELATIVE_PATH).is_file()
    # the harness is reused byte-identically from PAD4-R3: it is not authority
    assert r5.RAW_REVIEW_HARNESS_RELATIVE_PATH == r3.RAW_REVIEW_HARNESS_RELATIVE_PATH


# ---------------------------------------------------------------------------
# Preserved construction authority — unchanged from the reviewed PAD4-R3
# ---------------------------------------------------------------------------


def test_the_authoritative_execution_cannot_be_constructed_by_a_caller() -> None:
    with pytest.raises(r5.AuthoritativeExecutionConstructionError):
        r5.AuthoritativeScientificExecution()
    with pytest.raises(r5.AuthoritativeExecutionConstructionError):
        r5.AuthoritativeScientificExecution(object(), {"admitted": True})
    with pytest.raises(r5.AuthoritativeExecutionConstructionError):
        r5.AuthoritativeScientificExecution(
            capability=object(),
            material={"admitted": True, "affirmative_evidence_bytes": b"{}"},
        )
    # nor by offering a complete, correctly shaped, wholly immutable snapshot
    with pytest.raises(r5.AuthoritativeExecutionConstructionError):
        r5.AuthoritativeScientificExecution(
            object(),
            {name: b"" for name in r5.FROZEN_AUTHORITY_FIELDS},
        )


def test_the_authority_owning_factory_cannot_build_a_second_boundary() -> None:
    """A second boundary would be a second authority-bearing operation."""

    assert not hasattr(r5, r5.AUTHORITY_OWNING_FACTORY)
    assert r5.AUTHORITY_OWNING_FACTORY not in vars(r5)
    source = (ROOT / r5.CONTROLLER_RELATIVE_PATH).read_text("utf-8")
    assert f"del {r5.AUTHORITY_OWNING_FACTORY}" in source
    boundary_names = sorted(
        name
        for name, value in vars(r5).items()
        if callable(value)
        and getattr(value, "__module__", None) == r5.__name__
        and "boundary" in name
    )
    # every surviving "boundary" name is a frozen child-contract builder: it takes
    # no argument, returns a JSON contract, and can construct nothing
    assert boundary_names == ["authoritative_scientific_execution_boundary"]
    registry = {name for name, _ in r5._CHILD_ARTIFACTS}
    for name in boundary_names:
        assert f"{name}.json" in registry, name
        assert isinstance(getattr(r5, name)(), dict)


def test_no_module_callable_can_produce_an_authoritative_execution() -> None:
    """Census the live module: nothing but the one operation returns the type."""

    import inspect

    producers = []
    for name, value in vars(r5).items():
        if not callable(value) or isinstance(value, type):
            continue
        if getattr(value, "__module__", None) != r5.__name__:
            continue
        annotation = inspect.signature(value).return_annotation
        if "AuthoritativeScientificExecution" in str(annotation):
            producers.append(name)
    assert producers == ["run_isolated_scientific_request"]


def _assert_every_accessor_refuses(execution) -> None:
    """No caller-facing material at all, including the snapshot proof."""

    for attribute in r5.MUTABLE_CONVENIENCE_ACCESSORS + (
        r5.IMMUTABLE_CONVENIENCE_ACCESSORS
    ):
        with pytest.raises(r5.AuthoritativeExecutionConstructionError):
            getattr(execution, attribute)
    with pytest.raises(r5.AuthoritativeExecutionConstructionError):
        execution.authoritative_snapshot_proof()
    with pytest.raises(r5.AuthoritativeExecutionConstructionError):
        repr(execution)


def test_a_new_bypassed_execution_carries_no_material_and_refuses() -> None:
    """``__new__`` around ``__init__`` yields an object with nothing in it."""

    forged = r5.AuthoritativeScientificExecution.__new__(
        r5.AuthoritativeScientificExecution
    )
    _assert_every_accessor_refuses(forged)


def test_a_subclass_cannot_manufacture_authoritative_material() -> None:
    """Subclassing is refused outright, which is stronger than ``PAD4-R3``."""

    with pytest.raises(r5.AuthoritativeExecutionConstructionError):

        class Forged(r5.AuthoritativeScientificExecution):
            def __init__(self) -> None:  # deliberately does not call super()
                pass

    with pytest.raises(r5.AuthoritativeExecutionConstructionError):
        type("Forged2", (r5.AuthoritativeScientificExecution,), {"__slots__": ()})
    audit = r5.audit_authoritative_return_state()
    assert audit["construction_authority_probes"]["SUBCLASS"] == "REFUSED"
    assert audit["subclassing_the_authoritative_execution_is_refused"] is True


def test_r4_unrelated_descriptor_reuse_p0_reproduces_and_r5_refuses(
    admitted_session,
) -> None:
    """The checked-in exact review P0 fails against R4 and passes against R5."""

    r4_context = r4.candidate_review_authority_context(R4_CANDIDATE_HASH)
    r4_request = r4.build_scientific_request(
        r4_context,
        launch=LAUNCH,
        operation="common_etf_session_status",
        operation_inputs={"trade_date": SESSION_DAY.isoformat()},
        evidence_records=base.SESSION_RECORDS,
        decision_time=DECISION_TIME.isoformat(),
    )
    r4_execution = r4.run_isolated_scientific_request(r4_context, r4_request, LAUNCH)
    assert r4_execution.admitted is True, r4_execution.failure_reason

    r4_calls: list[str] = []

    def r4_hash(self) -> int:
        r4_calls.append("__hash__")
        return hash(r4_execution)

    def r4_eq(self, other: object) -> bool:
        r4_calls.append("__eq__")
        return other is r4_execution

    r4_namespace = {
        name: vars(r4.AuthoritativeScientificExecution)[name]
        for name in r4.audit_authoritative_return_state()["returning_class_members"]
    }
    r4_namespace.update(
        {"__slots__": ("__weakref__",), "__hash__": r4_hash, "__eq__": r4_eq}
    )
    R4Unrelated = type("R4UnrelatedDescriptorReuse", (), r4_namespace)
    r4_foreign = R4Unrelated()
    assert not isinstance(r4_foreign, r4.AuthoritativeScientificExecution)
    assert r4_foreign.admitted is True
    assert r4_foreign.result == r4_execution.result
    assert r4_foreign.authoritative_snapshot_proof() == (
        r4_execution.authoritative_snapshot_proof()
    )
    assert r4.AUTHORITATIVE_SCIENTIFIC_AUTHORITY in repr(r4_foreign.scientific_evidence)
    assert r4_calls == ["__hash__", "__eq__"] * 4

    r5_calls: list[str] = []
    target_hash = hash(admitted_session)

    def r5_hash(self) -> int:
        r5_calls.append("__hash__")
        return target_hash

    def r5_eq(self, other: object) -> bool:
        r5_calls.append("__eq__")
        return other is admitted_session

    identity = r5.audit_authoritative_execution_identity()
    r5_namespace = {
        name: vars(r5.AuthoritativeScientificExecution)[name]
        for name in identity["authority_bearing_members"]
    }
    r5_namespace.update(
        {"__slots__": ("__weakref__",), "__hash__": r5_hash, "__eq__": r5_eq}
    )
    R5Unrelated = type("R5UnrelatedDescriptorReuse", (), r5_namespace)
    r5_foreign = R5Unrelated()
    assert not isinstance(r5_foreign, r5.AuthoritativeScientificExecution)
    for name in identity["authority_bearing_members"]:
        descriptor = vars(r5.AuthoritativeScientificExecution)[name]
        with pytest.raises(r5.AuthoritativeExecutionConstructionError):
            value = getattr(r5_foreign, name)
            if not isinstance(descriptor, property):
                value()
    assert r5_calls == []
    assert admitted_session.admitted is True


def test_every_unbound_authority_member_refuses_a_foreign_receiver() -> None:
    identity = r5.audit_authoritative_execution_identity()

    class Foreign:
        @property
        def __class__(self):
            raise AssertionError("__class__ must not execute")

        def __hash__(self):
            raise AssertionError("__hash__ must not execute")

        def __eq__(self, other):
            raise AssertionError("__eq__ must not execute")

        def __getattr__(self, name):
            raise AssertionError("__getattr__ must not execute")

        def __bool__(self):
            raise AssertionError("__bool__ must not execute")

        def __repr__(self):
            raise AssertionError("__repr__ must not execute")

    foreign = Foreign()
    for name in identity["authority_bearing_members"]:
        descriptor = vars(r5.AuthoritativeScientificExecution)[name]
        with pytest.raises(r5.AuthoritativeExecutionConstructionError):
            if isinstance(descriptor, property):
                descriptor.fget(foreign)
            else:
                descriptor(foreign)


def test_spoofed_class_property_cannot_defeat_the_type_slot_guard() -> None:
    class SpoofedClass:
        @property
        def __class__(self):
            return r5.AuthoritativeScientificExecution

    foreign = SpoofedClass()
    assert foreign.__class__ is r5.AuthoritativeScientificExecution
    assert type(foreign) is SpoofedClass
    identity = r5.audit_authoritative_execution_identity()
    for name in identity["authority_bearing_members"]:
        descriptor = vars(r5.AuthoritativeScientificExecution)[name]
        with pytest.raises(r5.AuthoritativeExecutionConstructionError):
            if isinstance(descriptor, property):
                descriptor.fget(foreign)
            else:
                descriptor(foreign)


def _identity_registry():
    reader = inspect.getclosurevars(
        vars(r5.AuthoritativeScientificExecution)["admitted"].fget
    ).nonlocals[r5.AUTHORITY_STORAGE_READER]
    return inspect.getclosurevars(reader).nonlocals[r5.AUTHORITY_STORAGE_NAME]


def test_dead_cleanup_collision_and_identifier_reuse_are_identity_safe(
    admitted_session,
) -> None:
    registry = _identity_registry()
    doomed = _run(SESSION_REQUEST)
    doomed_bucket = id(doomed)
    doomed_witness = ref(doomed)
    assert doomed_bucket in registry
    del doomed
    gc.collect()
    assert doomed_witness() is None
    assert doomed_bucket not in registry
    assert admitted_session.admitted is True

    bucket = id(admitted_session)
    old_entry = registry[bucket]
    other = object.__new__(r5.AuthoritativeScientificExecution)
    newer_entry = type(old_entry)(ref(other), old_entry.snapshot)
    registry[bucket] = newer_entry
    old_entry.witness.__callback__(old_entry.witness)
    assert registry[bucket] is newer_entry
    with pytest.raises(r5.AuthoritativeExecutionConstructionError):
        admitted_session.admitted
    registry[bucket] = old_entry
    assert admitted_session.admitted is True


def test_the_authoritative_execution_exposes_no_material_setter() -> None:
    forged = r5.AuthoritativeScientificExecution.__new__(
        r5.AuthoritativeScientificExecution
    )
    with pytest.raises(AttributeError):
        forged.admitted = True  # type: ignore[misc]
    with pytest.raises(AttributeError):
        forged._fields = {"admitted": True}  # type: ignore[attr-defined]


def test_an_admitted_execution_refuses_accessor_reassignment(admitted_session) -> None:
    """An admitted execution's representation cannot be replaced either."""

    with pytest.raises(AttributeError):
        admitted_session.result = {"state": "REASSIGNED"}  # type: ignore[misc]
    with pytest.raises(AttributeError):
        admitted_session.scientific_evidence = {}  # type: ignore[misc]
    with pytest.raises(AttributeError):
        del admitted_session.response  # type: ignore[misc]
    assert admitted_session.result["state"] == HONEST_SESSION_STATE


def test_the_flow_refuses_a_superseded_or_absent_trusted_context() -> None:
    r3_context = r3.candidate_review_authority_context(CANDIDATE_HASH)
    assert not isinstance(r3_context, r5.ScientificWorkerAuthorityContext)
    with pytest.raises(r5.IsolatedScientificWorkerR5Error):
        r5.run_isolated_scientific_request(r3_context, SESSION_REQUEST, LAUNCH)
    r2_context = r2.candidate_review_authority_context(CANDIDATE_HASH)
    with pytest.raises(r5.IsolatedScientificWorkerR5Error):
        r5.run_isolated_scientific_request(r2_context, SESSION_REQUEST, LAUNCH)
    with pytest.raises(r5.IsolatedScientificWorkerR5Error):
        r5.run_isolated_scientific_request(None, SESSION_REQUEST, LAUNCH)
    with pytest.raises(r5.IsolatedScientificWorkerR5Error):
        r5.run_isolated_scientific_request(CONTEXT, SESSION_REQUEST, object())
    with pytest.raises(r5.IsolatedScientificWorkerR5Error):
        r5.run_isolated_scientific_request(CONTEXT, object(), LAUNCH)


def test_the_flow_refuses_a_drifted_request_without_spawning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = SpawnRecorder(monkeypatch)
    drifted = dict(SESSION_REQUEST)
    drifted["worker_authority_sha256"] = ZERO_HASH
    with pytest.raises(r5.IsolatedScientificWorkerR5Error) as refusal:
        _run(drifted)
    assert "REQUEST_AUTHORITY_MISMATCH" in str(refusal.value)
    assert recorder.worker_spawns == []


# ---------------------------------------------------------------------------
# THE MANDATORY RETURN-STATE CONTROL — the reviewed PAD4-R3 defect itself
# ---------------------------------------------------------------------------


def test_the_reviewed_r3_return_state_defect_reproduces_as_a_control() -> None:
    """CONTROL: against the preserved frozen ``PAD4-R3`` controller, it works.

    A correction that cannot reproduce the old failure as a *control* has proved
    nothing.  This drives the untouched ``PAD4-R3`` closed flow, admits an honest
    result, then performs exactly the mutation
    ``POSTP1-002V2A-PAD4-R3`` described — and shows the admitted, affirmatively
    authoritative execution really does come to represent caller-created state
    that no longer matches its own bound result digest.
    """

    r3_context = r3.candidate_review_authority_context(R3_CANDIDATE_HASH)
    r3_request = r3.build_scientific_request(
        r3_context,
        launch=LAUNCH,
        operation="common_etf_session_status",
        operation_inputs={"trade_date": SESSION_DAY.isoformat()},
        evidence_records=base.SESSION_RECORDS,
        decision_time=DECISION_TIME.isoformat(),
    )
    r3_execution = r3.run_isolated_scientific_request(r3_context, r3_request, LAUNCH)
    assert r3_execution.admitted is True, r3_execution.failure_reason
    bound = r3_execution.scientific_evidence["result_digest"]
    assert protocol.result_digest(r3_execution.result) == bound
    assert r3_execution.result["state"] == HONEST_SESSION_STATE

    # the exact reviewed defect: caller mutation of the returned result mapping
    r3_execution.result["state"] = "CALLER_CREATED_STATE"
    r3_execution.result["injected"] = {"nested": ["caller", "created"]}

    assert r3_execution.admitted is True
    assert r3_execution.result["state"] == "CALLER_CREATED_STATE"
    assert "injected" in r3_execution.result
    assert protocol.result_digest(r3_execution.result) != bound
    assert r3_execution.scientific_evidence["result_digest"] == bound
    assert r3_execution.scientific_evidence["admitted"] is True
    assert r3_execution.scientific_evidence["scientific_authority"] == (
        r3.AUTHORITATIVE_SCIENTIFIC_AUTHORITY
    )
    # and the returned response shares the same mutable descendants
    r3_execution.response["result"]["state"] = "VIA_RESPONSE"
    assert r3_execution.result["state"] == "VIA_RESPONSE"

    # the same semantic mutation against R5 changes nothing at all
    execution = _run(SESSION_REQUEST)
    assert execution.admitted is True, execution.failure_reason
    before = _snapshot(execution)
    result = execution.result
    result["state"] = "CALLER_CREATED_STATE"
    result["injected"] = {"nested": ["caller", "created"]}
    response = execution.response
    response["result"]["state"] = "VIA_RESPONSE"
    assert _snapshot(execution) == before
    assert execution.result["state"] == HONEST_SESSION_STATE
    assert "injected" not in execution.result
    assert protocol.result_digest(execution.result) == (
        execution.scientific_evidence["result_digest"]
    )


# ---------------------------------------------------------------------------
# Mandatory return-state regressions against R5
# ---------------------------------------------------------------------------


def test_top_level_result_mutation_is_isolated(admitted_session) -> None:
    before = _snapshot(admitted_session)
    bound = admitted_session.authoritative_snapshot_proof()["bound_result_digest"]

    result = admitted_session.result
    result["state"] = "CALLER_CREATED_STATE"
    result["trade_date"] = "1970-01-01"
    result["injected_top_level"] = True
    del result["reason_codes"]

    assert result["state"] == "CALLER_CREATED_STATE"
    assert admitted_session.result["state"] == HONEST_SESSION_STATE
    assert "injected_top_level" not in admitted_session.result
    assert "reason_codes" in admitted_session.result
    assert admitted_session.admitted is True
    assert admitted_session.authoritative_snapshot_proof()["bound_result_digest"] == bound
    assert _snapshot(admitted_session) == before


def test_nested_mapping_mutation_is_isolated(admitted_flow) -> None:
    before = _snapshot(admitted_flow)
    result = admitted_flow.result
    assert isinstance(result["calendar"], dict)
    assert isinstance(result["feature"], dict)

    result["calendar"]["state"] = "NESTED_CALLER_CREATED_STATE"
    result["calendar"]["injected"] = {"deeper": {"still": "mutable"}}
    result["feature"]["feature_id"] = "NESTED_MUTATED_ID"
    result["feature"]["flow_sum_usd"] = "0"

    assert _snapshot(admitted_flow) == before
    assert admitted_flow.result["feature"]["feature_id"] == (
        _flow.FIVE_DAY_ETF_FLOW_FEATURE_ID
    )
    assert "injected" not in admitted_flow.result["calendar"]


def test_nested_sequence_mutation_is_isolated(admitted_flow, admitted_session) -> None:
    before_flow = _snapshot(admitted_flow)
    before_session = _snapshot(admitted_session)

    result = admitted_flow.result
    dates = result["calendar"]["expected_dates"]
    assert isinstance(dates, list) and len(dates) == 5
    dates.append("1970-01-01")
    dates.extend(["1970-01-02", "1970-01-03"])
    dates[0] = "1970-01-04"
    result["feature"]["funds"].clear()
    result["reason_codes"].append("INJECTED_REASON_CODE")

    # a nested sequence of nested sequences, mutated at the leaf
    session_result = admitted_session.result
    venue_states = session_result["venue_states"]
    assert isinstance(venue_states, list) and isinstance(venue_states[0], list)
    venue_states[0][1] = "CLOSED_BY_THE_CALLER"
    venue_states.append(["INJECTED_VENUE", "INJECTED_STATE"])

    assert _snapshot(admitted_flow) == before_flow
    assert _snapshot(admitted_session) == before_session
    assert len(admitted_flow.result["calendar"]["expected_dates"]) == 5
    assert admitted_flow.result["feature"]["funds"] == (
        before_flow["result"]["feature"]["funds"]
    )
    assert admitted_flow.result["feature"]["funds"] != []
    assert admitted_session.result["venue_states"][0][1] != "CLOSED_BY_THE_CALLER"
    assert len(admitted_session.result["venue_states"]) == 3


def test_response_mutation_is_isolated(admitted_session) -> None:
    before = _snapshot(admitted_session)
    response = admitted_session.response
    assert response is not None

    response["status"] = "TAMPERED"
    response["result"]["state"] = "VIA_RESPONSE"
    response["result_digest"] = "0" * 64
    response["injected"] = ["caller", "created"]

    assert admitted_session.response["status"] == protocol.SUCCESS
    assert admitted_session.response["result"]["state"] == HONEST_SESSION_STATE
    assert admitted_session.result["state"] == HONEST_SESSION_STATE
    assert "injected" not in admitted_session.response
    assert _snapshot(admitted_session) == before


def test_evidence_mutation_is_isolated(admitted_session) -> None:
    before = _snapshot(admitted_session)
    evidence = admitted_session.scientific_evidence

    evidence["admitted"] = False
    evidence["scientific_authority"] = "TAMPERED"
    evidence["result_digest"] = "0" * 64
    evidence["bootstrap_pre_execution_source_binding"][
        "performed_by_this_authoritative_execution"
    ] = False
    evidence["trusted_authority_context"]["authority_context_version"] = "TAMPERED"

    fresh = admitted_session.scientific_evidence
    assert fresh["admitted"] is True
    assert fresh["scientific_authority"] == r5.AUTHORITATIVE_SCIENTIFIC_AUTHORITY
    assert fresh["bootstrap_pre_execution_source_binding"][
        "performed_by_this_authoritative_execution"
    ] is True
    assert fresh["trusted_authority_context"]["authority_context_version"] == (
            "ETF_CALENDAR_SCIENTIFIC_WORKER_AUTHORITY_CONTEXT_V1_R5"
    )
    assert admitted_session.admitted is True
    assert _snapshot(admitted_session) == before


def test_cross_accessor_values_are_equal_but_share_no_mutable_descendant(
    admitted_session,
) -> None:
    first = admitted_session.result
    second = admitted_session.result
    assert first == second
    assert first is not second
    assert _mutable_ids(first) & _mutable_ids(second) == set()

    first["state"] = "MUTATED_FIRST_COPY"
    first["venue_states"][0][0] = "MUTATED_NESTED"
    assert second["state"] == HONEST_SESSION_STATE
    assert second["venue_states"][0][0] != "MUTATED_NESTED"
    assert admitted_session.result["state"] == HONEST_SESSION_STATE

    # the same holds for the response and the evidence
    for accessor in ("response", "scientific_evidence"):
        one = getattr(admitted_session, accessor)
        two = getattr(admitted_session, accessor)
        assert one == two and one is not two
        assert _mutable_ids(one) & _mutable_ids(two) == set()


def test_the_response_and_the_result_share_no_mutable_descendant(
    admitted_session,
) -> None:
    """The reviewed defect made these the same nested object."""

    response = admitted_session.response
    result = admitted_session.result
    assert response["result"] == result
    assert response["result"] is not result
    assert _mutable_ids(response) & _mutable_ids(result) == set()

    result["state"] = "VIA_RESULT"
    assert response["result"]["state"] == HONEST_SESSION_STATE
    response["result"]["state"] = "VIA_RESPONSE"
    assert result["state"] == "VIA_RESULT"
    assert admitted_session.result["state"] == HONEST_SESSION_STATE

    evidence = admitted_session.scientific_evidence
    assert _mutable_ids(evidence) & _mutable_ids(result) == set()
    assert _mutable_ids(evidence) & _mutable_ids(response) == set()


def test_temporary_protocol_parser_state_is_not_retained_by_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The parsed worker response exists before the freeze; authority keeps none.

    The mapping captured here is the very object ``_validate_and_admit`` worked
    with.  Mutating it, and then discarding it entirely, must leave the returned
    authoritative execution exactly as admitted.
    """

    captured: list[dict] = []
    original = protocol.validate_response

    def recording(payload):
        parsed = original(payload)
        captured.append(parsed)
        return parsed

    monkeypatch.setattr(r5.protocol, "validate_response", recording)
    execution = _run(SESSION_REQUEST)
    monkeypatch.undo()

    assert execution.admitted is True, execution.failure_reason
    assert len(captured) == 1
    parser_state = captured[0]
    assert parser_state["result"]["state"] == HONEST_SESSION_STATE
    before = _snapshot(execution)

    parser_state["status"] = "TAMPERED"
    parser_state["result"]["state"] = "VIA_PARSER_STATE"
    parser_state["result"]["venue_states"][0][0] = "VIA_PARSER_STATE"
    assert _snapshot(execution) == before

    parser_state.clear()
    captured.clear()
    del parser_state
    gc.collect()
    assert _snapshot(execution) == before
    assert execution.result["state"] == HONEST_SESSION_STATE


def test_a_discarded_caller_request_object_is_not_retained_by_authority() -> None:
    request = session_request()
    execution = _run(request)
    assert execution.admitted is True, execution.failure_reason
    before = _snapshot(execution)

    request["operation"] = "TAMPERED"
    request["sys_path"].append("/injected/path")
    request.clear()
    gc.collect()

    assert _snapshot(execution) == before
    assert execution.response["operation"] == "common_etf_session_status"
    assert execution.scientific_evidence["operation"] == "common_etf_session_status"


def test_the_bound_digests_reproduce_from_the_frozen_snapshot_alone(
    admitted_session, admitted_flow
) -> None:
    """SHA-256 over the canonical bytes the authority stores *is* the bound digest."""

    for execution in (admitted_session, admitted_flow):
        proof = execution.authoritative_snapshot_proof()
        assert proof["admitted"] is True
        assert proof["authoritative_return_state"] == (
            "ETF_CALENDAR_AUTHORITATIVE_ADMITTED_RETURN_STATE_V1_R4"
        )
        assert proof["result_digest_recomputed_from_frozen_bytes"] == (
            proof["bound_result_digest"]
        )
        assert proof["response_digest_recomputed_from_frozen_bytes"] == (
            proof["bound_response_digest"]
        )
        assert proof["affirmative_evidence_digest_recomputed_from_frozen_bytes"] == (
            proof["bound_affirmative_evidence_digest"]
        )
        assert proof["authority_snapshot_holds_a_mutable_container"] is False
        assert sorted(proof["authority_snapshot_field_types"]) == sorted(
            r5.FROZEN_AUTHORITY_FIELDS
        )
        assert set(proof["authority_snapshot_field_types"].values()) <= {
            "NoneType",
            "bool",
            "bytes",
            "str",
        }
        # the same digest the worker bound and the evidence reports
        assert proof["bound_result_digest"] == (
            execution.response["result_digest"]
        )
        assert proof["bound_result_digest"] == (
            execution.scientific_evidence["result_digest"]
        )
        assert proof["bound_result_digest"] == protocol.result_digest(execution.result)
        assert proof["bound_response_digest"] == (
            execution.scientific_evidence["admitted_response_digest"]
        )


def test_the_digest_is_not_recomputed_from_caller_mutated_live_state(
    admitted_session,
) -> None:
    """No repair on read: mutation cannot move the digest in either direction."""

    before = admitted_session.authoritative_snapshot_proof()
    mutated = admitted_session.result
    mutated["state"] = "CALLER_CREATED_STATE"
    assert protocol.result_digest(mutated) != before["bound_result_digest"]
    after = admitted_session.authoritative_snapshot_proof()
    assert after == before
    assert after["result_digest_recomputed_from_frozen_bytes"] == (
        before["bound_result_digest"]
    )


def test_repeated_reads_after_caller_mutation_return_the_admitted_state(
    admitted_session,
) -> None:
    baseline = _snapshot(admitted_session)
    for round_index in range(4):
        result = admitted_session.result
        response = admitted_session.response
        evidence = admitted_session.scientific_evidence
        result["state"] = f"ROUND_{round_index}"
        response["status"] = f"ROUND_{round_index}"
        evidence["admitted"] = False
        assert _snapshot(admitted_session) == baseline
    assert _snapshot(admitted_session) == baseline
    assert admitted_session.result["state"] == HONEST_SESSION_STATE


def test_authority_is_stable_across_garbage_collection_and_later_requests(
    admitted_session,
) -> None:
    """Lifetime stability: nothing later may rewrite an earlier authority."""

    baseline = _snapshot(admitted_session)
    admitted_session.result["state"] = "MUTATED_BEFORE_GC"
    gc.collect()
    assert _snapshot(admitted_session) == baseline

    later = _run(flow_request())
    assert later.admitted is True, later.failure_reason
    assert _snapshot(admitted_session) == baseline
    later.result["calendar"]["state"] = "MUTATED_LATER"
    assert _snapshot(admitted_session) == baseline

    gc.collect()
    assert _snapshot(admitted_session) == baseline
    assert admitted_session.result["state"] == HONEST_SESSION_STATE


def test_sequential_requests_have_independent_return_state() -> None:
    """Two legitimate requests: A cannot affect B and B cannot affect A."""

    a = _run(SESSION_REQUEST)
    b = _run(flow_request())
    assert a.admitted is True, a.failure_reason
    assert b.admitted is True, b.failure_reason
    before_a, before_b = _snapshot(a), _snapshot(b)
    assert before_a["proof"]["bound_result_digest"] != (
        before_b["proof"]["bound_result_digest"]
    )
    assert _mutable_ids(a.result) & _mutable_ids(b.result) == set()

    a_result = a.result
    a_result["state"] = "MUTATED_A"
    a.response["status"] = "MUTATED_A"
    a.scientific_evidence["admitted"] = False
    assert _snapshot(a) == before_a
    assert _snapshot(b) == before_b

    b_result = b.result
    b_result["calendar"]["state"] = "MUTATED_B"
    b.response["result"]["feature"]["feature_id"] = "MUTATED_B"
    assert _snapshot(b) == before_b
    assert _snapshot(a) == before_a

    # a third request afterwards rewrites neither
    c = _run(SESSION_REQUEST)
    assert c.admitted is True, c.failure_reason
    assert _snapshot(a) == before_a
    assert _snapshot(b) == before_b
    assert c.authoritative_snapshot_proof()["bound_result_digest"] == (
        before_a["proof"]["bound_result_digest"]
    )


def test_a_refusal_cannot_be_promoted_to_an_admitted_execution() -> None:
    """The escalation an authority stored in a mutable container would allow.

    With authority in a ``dict``, anything holding the mapping could copy an
    admitted snapshot over a refusal's and obtain a fully self-consistent
    affirmatively-admitted execution, with ``authoritative_snapshot_proof()``
    reporting every digest as matching.  An immutable ``tuple`` snapshot has no
    operation that could do it, and this drives the strongest available route —
    reflective recovery of the closure-private store from the returned object
    itself, which is outside the stated threat model but must still be read-only.
    """

    refused = _run(SESSION_REQUEST, launch=replace(LAUNCH, timeout_seconds=0))
    admitted = _run(SESSION_REQUEST)
    assert refused.admitted is False and refused.failure_reason == "WORKER_TIMEOUT"
    assert admitted.admitted is True, admitted.failure_reason
    before = _snapshot(refused)

    reader = inspect.getclosurevars(
        vars(r5.AuthoritativeScientificExecution)["admitted"].fget
    ).nonlocals[r5.AUTHORITY_STORAGE_READER]
    store = inspect.getclosurevars(reader).nonlocals[r5.AUTHORITY_STORAGE_NAME]
    frozen_refusal = store[id(refused)].snapshot
    frozen_admitted = store[id(admitted)].snapshot
    assert isinstance(frozen_refusal, r5.FrozenAuthoritySnapshot)
    assert isinstance(frozen_admitted, r5.FrozenAuthoritySnapshot)
    for attempt in (
        lambda: frozen_refusal.update(frozen_admitted._asdict()),
        lambda: frozen_refusal.__setitem__(0, True),
        lambda: object.__setattr__(frozen_refusal, "admitted", True),
        lambda: object.__setattr__(frozen_refusal, "result_bytes", b"null"),
    ):
        with pytest.raises((AttributeError, TypeError)):
            attempt()

    assert refused.admitted is False
    assert refused.failure_reason == "WORKER_TIMEOUT"
    assert refused.authoritative_snapshot_proof()["bound_result_digest"] is None
    assert _snapshot(refused) == before
    assert refused.scientific_evidence["admitted"] is False
    assert admitted.result["state"] == HONEST_SESSION_STATE


def test_a_refusal_also_represents_an_immutable_canonical_snapshot() -> None:
    """The freeze is not limited to the admitted branch."""

    launch = replace(LAUNCH, timeout_seconds=0)
    execution = _run(SESSION_REQUEST, launch=launch)
    assert execution.admitted is False
    assert execution.failure_reason == "WORKER_TIMEOUT"
    before = _snapshot(execution)
    proof = execution.authoritative_snapshot_proof()
    assert proof["admitted"] is False
    assert proof["bound_result_digest"] is None
    # a refusal binds no result digest, so the accessor reports it as unbound
    # rather than comparing it against the digest of the canonical "no result"
    # snapshot, which would read as a mismatch on every refusal
    assert proof["result_digest_is_bound"] is False
    assert proof["unbound_digest_names"] == ["result"]
    assert proof["bound_digest_names"] == ["affirmative_evidence", "response"]
    assert proof["bound_digests_reproduce"] is True
    assert proof["authority_snapshot_holds_a_mutable_container"] is False
    assert execution.result is None
    assert execution.response is None

    evidence = execution.scientific_evidence
    evidence["admitted"] = True
    evidence["scientific_authority"] = "TAMPERED"
    assert execution.scientific_evidence["admitted"] is False
    assert _snapshot(execution) == before


def test_the_immutability_gate_is_the_only_write_path_into_authority() -> None:
    """Why the store in ``__init__`` is a complete freeze, not a copy.

    The proof is a chain: the mechanical audit establishes that the closure-private
    storage is referenced at exactly three declared places and that the one write
    site writes the gate's return value; the gate admits only
    ``IMMUTABLE_AUTHORITY_VALUE_TYPES`` and is exercised for each refusal; and the
    value it returns is an immutable ``tuple`` subclass, so there is nothing to
    mutate in place even for a route that recovers the storage reflectively.
    """

    audit = r5.audit_authoritative_return_state()
    assert audit["authority_storage_write_sites"] == [
        {
            "scope": [
                r5.AUTHORITY_OWNING_FACTORY,
                r5.AUTHORITY_STORAGE_BINDER,
            ],
            "value": "NAME",
        }
    ]
    assert len(audit["authority_storage_references"]) == 5
    # exactly the four types the nine frozen fields hold, so the gate is no looser
    # than the child contract that describes it
    assert r5.IMMUTABLE_AUTHORITY_VALUE_TYPES == (bool, bytes, str, type(None))
    assert r5.canonical_admitted_snapshot_rule()["authority_snapshot_value_types"] == (
        sorted(t.__name__ for t in r5.IMMUTABLE_AUTHORITY_VALUE_TYPES)
    )
    for mutable in ({}, [], set(), bytearray(b"x"), ("a", "tuple"), object(), 0, 1.5):
        assert not isinstance(mutable, r5.IMMUTABLE_AUTHORITY_VALUE_TYPES)
    for immutable in (True, False, b"", "", None):
        assert isinstance(immutable, r5.IMMUTABLE_AUTHORITY_VALUE_TYPES)
    # a caller cannot reach the one write site: the capability check comes first,
    # even for a complete and wholly immutable candidate snapshot
    with pytest.raises(r5.AuthoritativeExecutionConstructionError):
        r5.AuthoritativeScientificExecution(
            object(), {name: b"" for name in r5.FROZEN_AUTHORITY_FIELDS}
        )


# ---------------------------------------------------------------------------
# Preserved bypass regression 1 — raw unverified spawn -> fabricated response
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "relative,marker_name,expected",
    [
        (ENTRYPOINT, "r5-entrypoint-fabrication", "ENTRYPOINT_BOOTSTRAP_EXECUTED"),
        (REUSED_PROTOCOL, "r5-reused-fabrication", "PROTOCOL_BOOTSTRAP_EXECUTED"),
        (WORKER_PROTOCOL, "r5-worker-fabrication", "PROTOCOL_BOOTSTRAP_EXECUTED"),
    ],
)
def test_raw_unverified_spawn_fabrication_reproduces_as_a_control(
    relative: str, marker_name: str, expected: str, tmp_path: Path
) -> None:
    """CONTROL: unguarded, the drifted bootstrap really executes and fabricates."""

    marker = tmp_path / marker_name
    root = base.drifted_bootstrap_tree(tmp_path / "tree", relative, marker)
    launch = r5.worker_launch(project_root=root)
    request = session_request(launch=launch)

    outcome = raw.raw_unverified_worker_execution(request, launch)
    assert marker.exists(), outcome.stderr.decode()
    assert marker.read_text("ascii") == expected
    assert outcome.exit_status == 0
    fabricated = json.loads(outcome.stdout.decode())
    assert fabricated["status"] == protocol.SUCCESS
    assert fabricated["result"] == FABRICATED_RESULT
    assert fabricated["result"]["state"] != HONEST_SESSION_STATE

    # CONTROL: the reviewed PAD4-R2 surface really did admit exactly this.
    r2_context = r2.candidate_review_authority_context(CANDIDATE_HASH)
    r2_request = r2.build_scientific_request(
        r2_context,
        launch=launch,
        operation="common_etf_session_status",
        operation_inputs={"trade_date": SESSION_DAY.isoformat()},
        evidence_records=base.SESSION_RECORDS,
        decision_time=DECISION_TIME.isoformat(),
    )
    r2_outcome = r2._spawn_unverified_worker_process(r2_request, launch)
    r2_admission = r2.admit_worker_result(r2_context, r2_request, r2_outcome)
    assert r2_admission.admitted is True, "the reviewed bypass must reproduce"
    assert r2_admission.result == FABRICATED_RESULT


@pytest.mark.parametrize(
    "relative,marker_name",
    [
        (ENTRYPOINT, "r5-entrypoint-closed"),
        (PACKAGE_INITIALIZER, "r5-package-closed"),
        (REUSED_PROTOCOL, "r5-reused-closed"),
        (WORKER_PROTOCOL, "r5-worker-closed"),
    ],
)
def test_raw_fabricated_response_cannot_enter_r5_authority(
    relative: str, marker_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same fabrication, offered to R5: REFUSED, and never even spawned."""

    marker = tmp_path / marker_name
    root = base.drifted_bootstrap_tree(tmp_path / "tree", relative, marker)
    launch = r5.worker_launch(project_root=root)
    request = session_request(launch=launch)
    recorder = SpawnRecorder(monkeypatch)

    with pytest.raises(r5.BootstrapSourcePreVerificationError) as refusal:
        r5.run_isolated_scientific_request(CONTEXT, request, launch)

    assert refusal.value.reason == "WORKER_BOOTSTRAP_SOURCE_SHA_MISMATCH"
    assert refusal.value.detail.startswith(f"{relative}: expected ")
    assert recorder.worker_spawns == []
    assert not marker.exists()

    # and there is no second route: the raw outcome has nowhere to go.
    outcome = raw.raw_unverified_worker_execution(request, launch)
    assert marker.exists() or relative == PACKAGE_INITIALIZER
    assert outcome.scientifically_admissible is False
    assert outcome.scientific_authority == r5.NON_AUTHORITATIVE_SCIENTIFIC_AUTHORITY
    with pytest.raises(r5.AuthoritativeExecutionConstructionError):
        r5.AuthoritativeScientificExecution(outcome, {"admitted": True})
    with pytest.raises(r5.IsolatedScientificWorkerR5Error):
        r5.run_isolated_scientific_request(CONTEXT, request, outcome)


# ---------------------------------------------------------------------------
# Preserved bypass regression 2 — fabricated PASS preverification mapping
# ---------------------------------------------------------------------------


FABRICATED_PRE_VERIFICATION = {
    "rule": r5.BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING_RULE,
    "verified_by": "ALREADY_TRUSTED_CONTROLLER_CODE",
    "verified_before_subprocess_creation": True,
    "bootstrap_source_count": 4,
    "bootstrap_manifest_digest": (
        "1811e04dac7a033de2c8e6620bf7d5aa227b94eebdf419657ecccf4d3fead411"
    ),
    "checks": list(r5.BOOTSTRAP_PRE_VERIFICATION_CHECKS),
}


def test_a_fabricated_preverification_mapping_is_never_authority(
    tmp_path: Path,
) -> None:
    """A caller-fabricated PASS mapping changes nothing, anywhere."""

    root = base.certified_tree(tmp_path / "tree")
    launch = r5.worker_launch(project_root=root)
    request = session_request(launch=launch)

    outcome = raw.raw_unverified_worker_execution(
        request, launch, bootstrap_pre_verification=FABRICATED_PRE_VERIFICATION
    )
    assert outcome.bootstrap_pre_verification == FABRICATED_PRE_VERIFICATION
    assert outcome.scientifically_admissible is False

    diagnostic = raw.raw_execution_diagnostic(outcome)
    binding = diagnostic["bootstrap_pre_execution_source_binding"]
    assert diagnostic["admitted"] is False
    assert diagnostic["scientific_authority"] == (
        r5.NON_AUTHORITATIVE_SCIENTIFIC_AUTHORITY
    )
    assert binding["performed_by_a_trusted_controller"] is False
    assert binding["caller_supplied_mapping_is_diagnostic_not_authority"] is True
    assert "verified_by" not in binding
    assert "ALREADY_TRUSTED_CONTROLLER_CODE" not in json.dumps(diagnostic)
    assert r5.AUTHORITATIVE_SCIENTIFIC_AUTHORITY not in json.dumps(diagnostic)

    # the fabricated mapping produces exactly the same verdict as no mapping
    without = raw.raw_execution_diagnostic(
        replace(outcome, bootstrap_pre_verification=None)
    )
    assert {k: v for k, v in diagnostic.items() if k != (
        "bootstrap_pre_execution_source_binding")} == {
        k: v for k, v in without.items() if k != (
            "bootstrap_pre_execution_source_binding")
    }

    # and it cannot create an admission or affirmative evidence
    with pytest.raises(r5.AuthoritativeExecutionConstructionError):
        r5.AuthoritativeScientificExecution(
            FABRICATED_PRE_VERIFICATION, {"admitted": True}
        )
    assert r5.admission_provenance_rule()[
        "caller_fabricated_preverification_mapping_is_authority"
    ] is False


# ---------------------------------------------------------------------------
# Preserved bypass regression 3 — hand-built worker outcome, no controller run
# ---------------------------------------------------------------------------


def test_a_hand_built_outcome_with_every_field_correct_is_not_admitted(
    tmp_path: Path,
) -> None:
    """The reviewed ``PAD4-R2`` reproducer #3 still has nowhere to go under R5."""

    root = base.certified_tree(tmp_path / "tree")
    launch = r5.worker_launch(project_root=root)
    request = session_request(launch=launch)
    outcome = raw.raw_unverified_worker_execution(request, launch)

    parsed = json.loads(outcome.stdout.decode())
    assert outcome.exit_status == 0 and outcome.timed_out is False
    assert parsed["status"] == protocol.SUCCESS
    assert parsed["result_digest"] == protocol.result_digest(parsed["result"])
    assert parsed["request_digest"] == outcome.request_digest
    assert r5.verify_response_against_authority_context(CONTEXT, parsed) == ()
    assert r5.verify_request_against_authority_context(CONTEXT, request) == ()

    # CONTROL: the reviewed PAD4-R2 surface admits exactly this.
    r2_context = r2.candidate_review_authority_context(CANDIDATE_HASH)
    r2_request = r2.build_scientific_request(
        r2_context,
        launch=launch,
        operation="common_etf_session_status",
        operation_inputs={"trade_date": SESSION_DAY.isoformat()},
        evidence_records=base.SESSION_RECORDS,
        decision_time=DECISION_TIME.isoformat(),
    )
    r2_bytes = raw.raw_unverified_worker_execution(r2_request, launch)
    hand_built = r2.WorkerProcessOutcome(
        exit_status=0,
        timed_out=False,
        stdout=r2_bytes.stdout,
        stderr=b"",
        request_digest=protocol.digest_bytes(
            protocol.canonical_json_bytes(r2_request)
        ),
        bootstrap_pre_verification=None,
    )
    r2_admission = r2.admit_worker_result(r2_context, r2_request, hand_built)
    assert r2_admission.admitted is True, r2_admission.failure_reason
    assert hand_built.bootstrap_pre_verification is None

    # R5: there is nothing to hand it to, and nothing to compose it with.
    assert not hasattr(r5, "admit_worker_result")
    assert not hasattr(r5, "WorkerProcessOutcome")
    with pytest.raises(r5.AuthoritativeExecutionConstructionError):
        r5.AuthoritativeScientificExecution(hand_built, {"admitted": True})
    with pytest.raises(r5.IsolatedScientificWorkerR5Error):
        r5.run_isolated_scientific_request(CONTEXT, request, hand_built)
    assert raw.raw_execution_diagnostic(outcome)["admitted"] is False


# ---------------------------------------------------------------------------
# Preserved bypass regression 4 — hand-built admission state -> evidence
# ---------------------------------------------------------------------------


def test_caller_built_admission_state_cannot_mint_affirmative_evidence(
    tmp_path: Path,
) -> None:
    """No project-owned R5 callable turns caller state into affirmative evidence."""

    root = base.certified_tree(tmp_path / "tree")
    launch = r5.worker_launch(project_root=root)
    request = session_request(launch=launch)
    outcome = raw.raw_unverified_worker_execution(request, launch)
    parsed = json.loads(outcome.stdout.decode())

    fabricated_state = {
        "admitted": True,
        "failure_reason": None,
        "request_digest": outcome.request_digest,
        "response_bytes": protocol.canonical_json_bytes(parsed),
        "response_digest": protocol.digest_payload(parsed),
        "result_bytes": protocol.canonical_json_bytes(parsed["result"]),
        "result_digest": parsed["result_digest"],
        "affirmative_evidence_bytes": protocol.canonical_json_bytes(
            {
                "scientific_authority": r5.AUTHORITATIVE_SCIENTIFIC_AUTHORITY,
                "admitted": True,
            }
        ),
        "affirmative_evidence_digest": "0" * 64,
    }
    assert sorted(fabricated_state) == sorted(r5.FROZEN_AUTHORITY_FIELDS)
    with pytest.raises(r5.AuthoritativeExecutionConstructionError):
        r5.AuthoritativeScientificExecution(object(), fabricated_state)

    # no module-accessible evidence constructor and no module-accessible write
    # into authority storage exists.  The immutability gate *is* module-level, on
    # purpose, so its refusals can be exercised — but it is inert: it validates a
    # mapping and returns a snapshot that grants nothing.
    assert not hasattr(r5, "scientific_response_evidence")
    assert not hasattr(r5, "AdmissionOutcome")
    assert not hasattr(r5, r5.AUTHORITY_STORAGE_NAME)
    assert not hasattr(r5, r5.AUTHORITY_STORAGE_READER)
    assert hasattr(r5, r5.AUTHORITY_SNAPSHOT_GUARD)
    assert r5.authoritative_scientific_execution_boundary()[
        "module_accessible_authority_storage_write_exists"
    ] is False
    evidence_callables = [
        name
        for name in dir(r5)
        if callable(getattr(r5, name)) and "evidence" in name and "rule" not in name
    ]
    assert evidence_callables == []
    assert r5.scientific_evidence_authority_rule()[
        "caller_built_admission_state_can_mint_evidence"
    ] is False


def test_superseded_lineage_evidence_is_not_r5_authority(tmp_path: Path) -> None:
    """Laundering the R5 hash through a failed lineage surface fails."""

    root = base.certified_tree(tmp_path / "tree")
    launch = r5.worker_launch(project_root=root)
    r2_context = r2.candidate_review_authority_context(CANDIDATE_HASH)
    r2_request = r2.build_scientific_request(
        r2_context,
        launch=launch,
        operation="common_etf_session_status",
        operation_inputs={"trade_date": SESSION_DAY.isoformat()},
        evidence_records=base.SESSION_RECORDS,
        decision_time=DECISION_TIME.isoformat(),
    )
    laundered = r2.admit_worker_result(
        r2_context,
        r2_request,
        r2.WorkerProcessOutcome(
            exit_status=0,
            timed_out=False,
            stdout=b"{}\n",
            stderr=b"",
            request_digest="0" * 64,
            bootstrap_pre_verification=FABRICATED_PRE_VERIFICATION,
        ),
    )
    evidence = r2.scientific_response_evidence(r2_context, laundered)
    assert evidence.get("scientific_authority") is None
    assert r5.AUTHORITATIVE_SCIENTIFIC_AUTHORITY not in json.dumps(evidence)
    assert r3.AUTHORITATIVE_SCIENTIFIC_AUTHORITY not in json.dumps(evidence)
    assert evidence["admitted"] is False
    # the R3 marker is a different string, so admitted R3 evidence — mutated or
    # not — can never be mistaken for affirmative R5 authority
    assert r5.AUTHORITATIVE_SCIENTIFIC_AUTHORITY != (
        r3.AUTHORITATIVE_SCIENTIFIC_AUTHORITY
    )
    assert r5.affirmative_evidence_snapshot_rule()[
        "mutated_r4_evidence_can_be_mistaken_for_r5_authority"
    ] is False


# ---------------------------------------------------------------------------
# Preserved worker-fabrication regression
# ---------------------------------------------------------------------------


def test_a_worker_that_copies_every_request_authority_field_cannot_be_admitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The worker can copy everything it can see, and it is still not enough."""

    marker = tmp_path / "r5-worker-copies-everything"
    root = base.drifted_bootstrap_tree(tmp_path / "tree", ENTRYPOINT, marker)
    launch = r5.worker_launch(project_root=root)
    request = session_request(launch=launch)

    outcome = raw.raw_unverified_worker_execution(request, launch)
    fabricated = json.loads(outcome.stdout.decode())
    assert marker.exists()
    assert r5.verify_response_against_authority_context(CONTEXT, fabricated) == ()
    assert fabricated["result_digest"] == protocol.result_digest(fabricated["result"])
    assert fabricated["bootstrap_defence_in_depth_verification"] == "PASS"
    assert fabricated["result"] == FABRICATED_RESULT

    recorder = SpawnRecorder(monkeypatch)
    with pytest.raises(r5.BootstrapSourcePreVerificationError):
        r5.run_isolated_scientific_request(CONTEXT, request, launch)
    assert recorder.worker_spawns == []
    assert raw.raw_execution_diagnostic(outcome)["admitted"] is False
    assert r5.admission_provenance_rule()[
        "worker_copied_request_authority_is_sufficient_for_admission"
    ] is False


# ---------------------------------------------------------------------------
# Positive authoritative regression and evidence truth
# ---------------------------------------------------------------------------


def test_the_clean_authoritative_path_is_admitted(tmp_path: Path) -> None:
    root = base.certified_tree(tmp_path / "tree")
    launch = r5.worker_launch(project_root=root)
    execution = _run(session_request(launch=launch), launch=launch)

    assert isinstance(execution, r5.AuthoritativeScientificExecution)
    assert execution.admitted is True, execution.failure_reason
    assert execution.failure_reason is None
    assert execution.result["state"] == HONEST_SESSION_STATE
    assert execution.response["bootstrap_defence_in_depth_verification"] == "PASS"
    assert execution.response["worker_bootstrap_manifest_digest"] == (
        CONTEXT.worker_bootstrap_manifest_digest
    )

    evidence = execution.scientific_evidence
    assert evidence["scientific_authority"] == r5.AUTHORITATIVE_SCIENTIFIC_AUTHORITY
    assert evidence["admitted"] is True
    assert evidence["authoritative_execution_is_closed_end_to_end"] is True
    assert evidence["admitted_authority_is_an_immutable_canonical_snapshot"] is True
    assert evidence["caller_visible_values_are_detached_decodes"] is True
    assert evidence["authoritative_return_state"] == (
        "ETF_CALENDAR_AUTHORITATIVE_ADMITTED_RETURN_STATE_V1_R4"
    )
    assert evidence["proof_architecture_program_ticket"] == "POSTP1-001V2A-PAD4-R5"
    binding = evidence["bootstrap_pre_execution_source_binding"]
    assert binding["verified_by"] == "ALREADY_TRUSTED_CONTROLLER_CODE"
    assert binding["verified_before_subprocess_creation"] is True
    assert binding["performed_by_this_authoritative_execution"] is True
    assert binding["bootstrap_source_count"] == 4
    assert binding["bootstrap_manifest_digest"] == (
        "1811e04dac7a033de2c8e6620bf7d5aa227b94eebdf419657ecccf4d3fead411"
    )
    assert evidence["trusted_authority_context"]["authority_context_version"] == (
            "ETF_CALENDAR_SCIENTIFIC_WORKER_AUTHORITY_CONTEXT_V1_R5"
    )
    assert evidence["trusted_authority_context"][
        "proof_architecture_program_ticket"
    ] == "POSTP1-001V2A-PAD4-R5"


def test_the_repository_tree_admits_an_honest_result(admitted_session) -> None:
    assert admitted_session.admitted is True, admitted_session.failure_reason
    assert admitted_session.result["state"] == HONEST_SESSION_STATE
    assert admitted_session.scientific_evidence["admitted"] is True


def test_the_flow_operation_matches_the_parent_computation(admitted_flow) -> None:
    assert admitted_flow.admitted is True, admitted_flow.failure_reason
    assert admitted_flow.result["feature"]["feature_id"] == (
        _flow.FIVE_DAY_ETF_FLOW_FEATURE_ID
    )
    assert admitted_flow.result["feature"]["window_days"] == (
        _flow.FIVE_DAY_ETF_FLOW_WINDOW_DAYS
    )


def test_every_non_authoritative_execution_tells_the_truth(tmp_path: Path) -> None:
    """Evidence truth: a raw execution may never claim what did not happen."""

    root = base.certified_tree(tmp_path / "tree")
    launch = r5.worker_launch(project_root=root)
    request = session_request(launch=launch)
    for mapping in (None, FABRICATED_PRE_VERIFICATION):
        outcome = raw.raw_unverified_worker_execution(
            request, launch, bootstrap_pre_verification=mapping
        )
        diagnostic = raw.raw_execution_diagnostic(outcome)
        rendered = json.dumps(diagnostic)
        assert diagnostic["admitted"] is False
        assert diagnostic["scientific_authority"] == (
            r5.NON_AUTHORITATIVE_SCIENTIFIC_AUTHORITY
        )
        assert diagnostic["authoritative_execution_is_closed_end_to_end"] is False
        assert "ALREADY_TRUSTED_CONTROLLER_CODE" not in rendered
        assert r5.AUTHORITATIVE_SCIENTIFIC_AUTHORITY not in rendered
        assert diagnostic["result"] is None
        assert diagnostic["result_digest"] is None


def test_the_raw_diagnostic_refuses_authoritative_material(admitted_session) -> None:
    with pytest.raises(TypeError):
        raw.raw_execution_diagnostic(admitted_session)
    with pytest.raises(TypeError):
        raw.raw_execution_diagnostic({"admitted": True})


def test_a_worker_failure_is_never_admitted_and_evidence_says_so() -> None:
    """Preserved failure admission, now frozen in the returned authority."""

    launch = replace(LAUNCH, timeout_seconds=0)
    execution = _run(SESSION_REQUEST, launch=launch)
    assert execution.admitted is False
    assert execution.failure_reason == "WORKER_TIMEOUT"
    evidence = execution.scientific_evidence
    assert evidence["admitted"] is False
    assert evidence["process_timed_out"] is True
    assert evidence["result_digest"] is None
    # the binding is still truthful: preverification really did run first
    assert evidence["bootstrap_pre_execution_source_binding"][
        "performed_by_this_authoritative_execution"
    ] is True


def _worker_refusal(request: dict, launch=None, context=None, **kwargs) -> dict:
    """The worker's own refusal payload, obtained through the closed flow."""

    execution = _run(request, launch=launch, context=context, **kwargs)
    assert execution.admitted is False
    assert execution.failure_reason.startswith(
        ("WORKER_REFUSED:", "WORKER_EXIT_STATUS_")
    )
    response = execution.response
    assert response is not None, execution.failure_reason
    assert response["status"] == "REFUSED"
    assert response["result"] is None
    assert response["result_digest"] is None
    return response


# ---------------------------------------------------------------------------
# Preserved Repair A — executed bytecode binding
# ---------------------------------------------------------------------------


def test_worker_launch_uses_exec_isolation_and_a_fresh_pycache_namespace(
    tmp_path: Path,
) -> None:
    namespace = r5.allocate_worker_pycache_namespace(tmp_path / "cache")
    argv = LAUNCH.argv_for(namespace)
    assert argv[1:4] == ("-I", "-S", "-B")
    assert argv[4] == "-X"
    assert argv[5] == f"pycache_prefix={namespace}"
    assert LAUNCH.mechanism == r5.EXEC_LAUNCH
    assert not any(namespace.rglob("*.pyc"))


def test_forged_repository_pyc_is_not_executed_by_a_real_worker(
    tmp_path: Path,
) -> None:
    root = base.certified_tree(tmp_path / "tree")
    flow_source = root / "btc_predictor/features/flow.py"
    forged = flow_source.read_text("utf-8").replace(
        f'FIVE_DAY_ETF_FLOW_FEATURE_ID = "{_flow.FIVE_DAY_ETF_FLOW_FEATURE_ID}"',
        'FIVE_DAY_ETF_FLOW_FEATURE_ID = "FORGED_BYTECODE_ID"',
    )
    assert "FORGED_BYTECODE_ID" in forged
    base.forge_pyc(
        flow_source,
        root / "btc_predictor/features/__pycache__/flow.cpython-312.pyc",
        forged,
    )
    launch = r5.worker_launch(project_root=root)
    execution = _run(flow_request(launch=launch), launch=launch)
    assert execution.admitted is True, execution.failure_reason
    assert execution.result["feature"]["feature_id"] == (
        _flow.FIVE_DAY_ETF_FLOW_FEATURE_ID
    )
    assert execution.result["feature"]["feature_id"] != "FORGED_BYTECODE_ID"


def test_forged_bootstrap_pyc_is_not_executed(tmp_path: Path) -> None:
    root = base.certified_tree(tmp_path / "tree")
    marker = tmp_path / "r5-forged-bootstrap-pyc"
    base.forge_pyc(
        root / WORKER_PROTOCOL,
        root / "etf_calendar_worker/__pycache__/protocol_r2.cpython-312.pyc",
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('X')\n",
    )
    launch = r5.worker_launch(project_root=root)
    execution = _run(session_request(launch=launch), launch=launch)
    assert execution.admitted is True, execution.failure_reason
    assert not marker.exists()


def test_a_pre_populated_cache_namespace_refuses(tmp_path: Path) -> None:
    poisoned = tmp_path / "poisoned"
    poisoned.mkdir()
    (poisoned / "stale.pyc").write_bytes(b"\x00")
    with pytest.raises(r1.IsolatedScientificWorkerR1Error, match="is not fresh"):
        r5.create_fresh_pycache_namespace(poisoned)
    execution = _run(SESSION_REQUEST, pycache_namespace=poisoned)
    assert execution.admitted is False
    assert execution.failure_reason == "WORKER_EXIT_STATUS_6"
    assert execution.scientific_evidence["admitted"] is False


def test_a_sourceless_project_module_origin_refuses(tmp_path: Path) -> None:
    root = base.certified_tree(tmp_path / "tree")
    flow_source = root / "btc_predictor/features/flow.py"
    certified_bytes = flow_source.read_bytes()
    shadow = root / "btc_predictor/features/flow"
    shadow.mkdir()
    base.forge_pyc(
        flow_source,
        shadow / "__init__.pyc",
        flow_source.read_text("utf-8").replace(
            'FIVE_DAY_ETF_FLOW_FEATURE_ID = "ETF_FLOW_5D"',
            'FIVE_DAY_ETF_FLOW_FEATURE_ID = "SOURCELESS_BYTECODE_ID"',
        ),
    )
    assert flow_source.read_bytes() == certified_bytes
    launch = r5.worker_launch(project_root=root)
    assert _worker_refusal(session_request(launch=launch), launch=launch)[
        "failure_reason"
    ] == "WRONG_PROJECT_MODULE_ORIGIN"


# ---------------------------------------------------------------------------
# Preserved Repair B — frozen source authority
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "relative",
    [
        "btc_predictor/features/flow.py",
        "btc_predictor/research/etf_calendar_scientific_worker_entry.py",
        "btc_predictor/research/etf_calendar_worker_protocol.py",
    ],
)
def test_pre_request_source_drift_cannot_redefine_scientific_authority(
    relative: str, tmp_path: Path
) -> None:
    root = base.certified_tree(tmp_path / "tree", mutate=relative)
    launch = r5.worker_launch(project_root=root)
    request = session_request(launch=launch)
    assert request["project_source_manifest_digest"] == (
        CONTEXT.project_source_manifest_digest
    )
    assert r5.verify_request_against_authority_context(CONTEXT, request) == ()
    assert _worker_refusal(request, launch=launch)["failure_reason"] == (
        "CERTIFIED_SOURCE_SHA_MISMATCH"
    )


def test_runtime_never_rederives_the_source_manifest() -> None:
    import inspect

    parameters = set(inspect.signature(r5.build_scientific_request).parameters)
    assert parameters == {
        "authority_context",
        "launch",
        "operation",
        "operation_inputs",
        "evidence_records",
        "decision_time",
        "evidence_admission_mode",
    }
    assert "decision_sha256" not in parameters
    assert "project_source_manifest" not in parameters
    assert DECISION["central_decisions"][
        "runtime_source_manifest_rederivation_permitted"
    ] is False


# ---------------------------------------------------------------------------
# Preserved Repair C — trusted controller authority context, R5 identity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("wrong", [ZERO_HASH, DEADBEEF_HASH])
def test_a_wrong_self_consistent_decision_hash_is_not_admitted(wrong: str) -> None:
    context = r5.candidate_review_authority_context(wrong)
    request = session_request(context=context)
    assert request["worker_authority_sha256"] == wrong
    execution = _run(request, context=context)
    assert execution.admitted is True, execution.failure_reason
    # the worker echoes it consistently, so the trusted context is what refuses
    assert r5.verify_response_against_authority_context(CONTEXT, execution.response) == (
        ("worker_authority_sha256",)
    )
    with pytest.raises(r5.IsolatedScientificWorkerR5Error):
        _run(request)


def test_the_three_way_authority_agreement_holds_through_the_returned_lifetime(
    admitted_session,
) -> None:
    """Repair C, extended: the agreement cannot be broken by caller mutation."""

    assert r5.verify_request_against_authority_context(CONTEXT, SESSION_REQUEST) == ()
    assert r5.verify_response_against_authority_context(
        CONTEXT, admitted_session.response
    ) == ()
    assert admitted_session.response["request_digest"] == (
        admitted_session.request_digest
    )
    assert admitted_session.admitted is True

    mutated = admitted_session.response
    mutated["worker_authority_sha256"] = ZERO_HASH
    mutated["calendar_authority_sha256"] = ZERO_HASH
    assert r5.verify_response_against_authority_context(CONTEXT, mutated) != ()
    # the authority itself still agrees with the trusted context
    assert r5.verify_response_against_authority_context(
        CONTEXT, admitted_session.response
    ) == ()
    assert r5.controller_authority_context_rule()[
        "three_way_agreement_valid_through_returned_authority_lifetime"
    ] is True
    assert r5.controller_authority_context_rule()[
        "caller_mutation_can_break_the_three_way_agreement"
    ] is False


def test_the_authority_context_cannot_be_built_from_a_request_or_response() -> None:
    with pytest.raises(TypeError):
        r5.ScientificWorkerAuthorityContext(**SESSION_REQUEST)
    with pytest.raises(r2.IsolatedScientificWorkerR2Error):
        r5.candidate_review_authority_context("not-a-sha")


def test_a_context_bound_to_a_different_worker_protocol_ticket_refuses() -> None:
    # the reviewed PAD4-R2 ticket check fires first, exactly as it did under R3
    with pytest.raises(r2.IsolatedScientificWorkerR2Error):
        r5.ScientificWorkerAuthorityContext(
            origin=CONTEXT.origin,
            proof_architecture_version=CONTEXT.proof_architecture_version,
            proof_architecture_ticket="POSTP1-001V2A-PAD4-R5",
            proof_architecture_sha256=CONTEXT.proof_architecture_sha256,
            interpreter_identity=dict(CONTEXT.interpreter_identity),
            project_source_manifest=CONTEXT.project_source_manifest,
            project_source_manifest_role=CONTEXT.project_source_manifest_role,
            worker_bootstrap_manifest=CONTEXT.worker_bootstrap_manifest,
            required_project_modules=CONTEXT.required_project_modules,
            third_party_authority=CONTEXT.third_party_authority,
            calendar_authority_version=CONTEXT.calendar_authority_version,
            calendar_authority_sha256=CONTEXT.calendar_authority_sha256,
            trusted_persistence_authority_sha256=(
                CONTEXT.trusted_persistence_authority_sha256
            ),
        )
    assert CONTEXT.proof_architecture_ticket == "POSTP1-001V2A-PAD4-R2"
    assert r5.WORKER_PROTOCOL_AUTHORITY_TICKET == "POSTP1-001V2A-PAD4-R2"


def test_the_candidate_context_hash_boundary_is_reproduced_and_not_reopened() -> None:
    """Earlier review confirmed this is NOT a defect; behaviour is unchanged."""

    arbitrary = r5.candidate_review_authority_context("a" * 64)
    assert arbitrary.proof_architecture_sha256 == "a" * 64
    rule = r5.controller_authority_context_rule()
    assert rule["candidate_review_authority_context_reopened"] is False
    assert rule["candidate_review_authority_context_review_finding"] == (
        "CONFIRMED_NOT_A_DEFECT_BY_POSTP1_002V2A_PAD4_R2"
    )
    source = (ROOT / r5.CONTROLLER_RELATIVE_PATH).read_text("utf-8")
    assert "os.environ" not in source
    assert "getenv" not in source


def test_the_production_authority_context_is_still_blocked() -> None:
    with pytest.raises(
        r2.IsolatedScientificWorkerR2Error, match=r5.PRODUCTION_CONTEXT_NOT_YET_BOUND
    ):
        r5.production_authority_context_from_calendar_authority({})
    assert DECISION["authorization"]["postp1_001v2a_i2_may_begin"] is False


# ---------------------------------------------------------------------------
# Preserved Repair D — third-party semantic and installed-content authority
# ---------------------------------------------------------------------------


def test_the_reviewed_third_party_registry_is_unchanged() -> None:
    rows = {
        entry.distribution: entry.version for entry in r5.frozen_third_party_authority()
    }
    assert rows == {
        "alembic": "1.19.1",
        "cryptography": "50.0.1",
        "numpy": "2.5.2",
        "scipy": "1.18.1",
        "sqlalchemy": "2.0.52",
    }
    assert DECISION["third_party_authority_digest"] == (
        "23e4f1d89a503b43fc39ee0ae3516b742f6db72028224d78a9181be6726298a6"
    )


def test_a_tampered_installed_dependency_never_executes(tmp_path: Path) -> None:
    """Shared ``.venv312`` mutation, serialized here and restored under finally."""

    base._assert_reviewed_dependency_state("alembic")
    authority = next(
        entry
        for entry in r5.frozen_third_party_authority()
        if entry.distribution == "alembic"
    )
    observation = r5.observe_installed_distributions((authority,))[0]
    target = Path(observation.location) / "alembic/__init__.py"
    record = Path(observation.record_path)
    marker = tmp_path / "r5-tampered-dependency-executed"
    original_target = target.read_bytes()
    original_record = record.read_bytes()
    try:
        target.write_text(
            target.read_text("utf-8")
            + "\nimport pathlib as _p\n"
            + f"_p.Path({str(marker)!r}).write_text('executed')\n",
            encoding="utf-8",
        )
        assert record.read_bytes() == original_record
        response = _worker_refusal(SESSION_REQUEST)
        assert response["failure_reason"] == (
            protocol.NON_CERTIFIED_DEPENDENCY_ENVIRONMENT
        )
        assert response["third_party_installed_content_verification"] == "NOT_REACHED"
        assert not marker.exists()
    finally:
        target.write_bytes(original_target)
        record.write_bytes(original_record)
    assert target.read_bytes() == original_target
    base._assert_reviewed_dependency_state("alembic")


# ---------------------------------------------------------------------------
# Preserved fresh-exec process isolation
# ---------------------------------------------------------------------------


def test_parent_mutation_does_not_reach_the_exec_d_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_flow, "FIVE_DAY_ETF_FLOW_FEATURE_ID", "PARENT_MUTATED_ID")
    monkeypatch.setattr(_flow, "FIVE_DAY_ETF_FLOW_WINDOW_DAYS", 999)
    assert _flow.FIVE_DAY_ETF_FLOW_FEATURE_ID == "PARENT_MUTATED_ID"
    execution = _run(flow_request())
    assert execution.admitted is True, execution.failure_reason
    assert execution.result["feature"]["feature_id"] != "PARENT_MUTATED_ID"
    assert execution.result["feature"]["window_days"] != 999


def test_parent_sys_modules_substitution_does_not_reach_the_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import types

    shim = types.ModuleType("btc_predictor.features.flow")
    shim.FIVE_DAY_ETF_FLOW_FEATURE_ID = "SUBSTITUTED_ID"
    monkeypatch.setitem(sys.modules, "btc_predictor.features.flow", shim)
    execution = _run(flow_request())
    assert execution.admitted is True, execution.failure_reason
    assert execution.result["feature"]["feature_id"] != "SUBSTITUTED_ID"


def test_parent_builtins_mutation_does_not_reach_the_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import builtins

    monkeypatch.setattr(builtins, "R4_PARENT_BUILTIN_PROBE", "PRESENT", raising=False)
    assert getattr(builtins, "R4_PARENT_BUILTIN_PROBE") == "PRESENT"
    execution = _run(SESSION_REQUEST)
    assert execution.admitted is True, execution.failure_reason
    assert "R4_PARENT_BUILTIN_PROBE" not in json.dumps(execution.scientific_evidence)


def test_parent_class_and_re_export_mutation_do_not_reach_the_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mutating a parent class body and a package re-export changes nothing."""

    import types

    from btc_predictor.research import etf_publication_calendar as parent_cal

    original_init = parent_cal.ScientificEtfFlowResult.__init__

    def corrupted_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        object.__setattr__(self, "feature_id", "PARENT_CLASS_MUTATED_ID")

    monkeypatch.setattr(
        parent_cal.ScientificEtfFlowResult, "__init__", corrupted_init, raising=True
    )
    shim = types.ModuleType("btc_predictor.features.flow")
    shim.FIVE_DAY_ETF_FLOW_FEATURE_ID = "REEXPORT_MUTATED_ID"
    import btc_predictor.features as features_package

    monkeypatch.setattr(features_package, "flow", shim, raising=False)
    assert features_package.flow.FIVE_DAY_ETF_FLOW_FEATURE_ID == "REEXPORT_MUTATED_ID"

    execution = _run(flow_request())
    assert execution.admitted is True, execution.failure_reason
    rendered = json.dumps(execution.result)
    assert "PARENT_CLASS_MUTATED_ID" not in rendered
    assert "REEXPORT_MUTATED_ID" not in rendered
    assert execution.result["feature"]["feature_id"] == (
        _flow.FIVE_DAY_ETF_FLOW_FEATURE_ID
    )


# ---------------------------------------------------------------------------
# Preserved static calendar authority and production status
# ---------------------------------------------------------------------------


def test_preserved_compiled_witness_grammar_and_owner_graph() -> None:
    witness_rule = r5.compiled_root_binding_witness_rule()
    grammar = r5.store_root_and_direct_use_grammar()
    graph = r5.replay_owner_graph_rule()
    bodies = r5.direct_body_dependency_rule()
    assert witness_rule == r2.compiled_root_binding_witness_rule()
    assert grammar == r2.store_root_and_direct_use_grammar()
    assert graph == r2.replay_owner_graph_rule()
    assert bodies == r2.direct_body_dependency_rule()
    assert witness_rule == r3.compiled_root_binding_witness_rule()
    assert grammar == r3.store_root_and_direct_use_grammar()
    assert graph == r3.replay_owner_graph_rule()
    assert bodies == r3.direct_body_dependency_rule()
    assert len(r5.FROZEN_REPLAY_OWNERS) == 11
    assert DECISION["central_decisions"]["compiled_root_witness_preserved"] is True
    assert DECISION["central_decisions"][
        "root_may_be_a_cell_variable_of_a_conforming_owner"
    ] is False
    assert DECISION["central_decisions"]["exact_eleven_owner_graph_preserved"] is True
    assert DECISION["central_decisions"]["direct_body_dependency_checks_preserved"] is (
        True
    )


def test_production_remains_blocked_and_calendar_source_is_untouched() -> None:
    production = DECISION["current_production_expected_result"]
    assert production == r3.isolated_scientific_worker_v1_r3_definition()[
        "current_production_expected_result"
    ]
    assert DECISION["central_decisions"]["calendar_production_code_changed"] is False
    assert DECISION["central_decisions"]["calendar_science_changed"] is False
    assert DECISION["central_decisions"]["i2_calendar_production_work_performed"] is (
        False
    )
    assert DECISION["central_decisions"]["wrapper_installed_guards_permitted"] is False


def test_the_pre_i2_fixture_role_is_unchanged_and_i2_still_owns_the_manifests() -> None:
    assert DECISION["pre_i2_project_source_module_count"] == 116
    assert DECISION["pre_i2_project_source_manifest_digest"] == (
        "674b006ae66b8aace3458cb870f898ecad33e1f23833436954d36749b3aadbb8"
    )
    assert DECISION["pre_i2_project_source_manifest_role"] == r5.PRE_I2_FIXTURE_ROLE
    assert DECISION["central_decisions"]["pre_i2_116_module_manifest_role"] == (
        "CONFORMANCE_FIXTURE_NOT_FINAL_PRODUCTION_AUTHORITY"
    )
    assert DECISION["central_decisions"][
        "final_i2_source_manifest_must_be_calendar_parent_bound"
    ] is True


def test_the_bootstrap_set_and_candidate_universe_are_mechanically_derived() -> None:
    completeness = r5.verify_frozen_bootstrap_set_is_complete()
    assert completeness["bootstrap_source_count"] == 4
    assert completeness["bootstrap_manifest_digest"] == (
        "1811e04dac7a033de2c8e6620bf7d5aa227b94eebdf419657ecccf4d3fead411"
    )
    assert completeness["bootstrap_source_set"] == sorted(BOOTSTRAP_SET)
    assert DECISION["worker_bootstrap_manifest_digest"] == (
        completeness["bootstrap_manifest_digest"]
    )
    assert DECISION["candidate_worker_source_module_count"] == 120
    assert DECISION["candidate_worker_source_manifest_digest"] == (
        "7ffbf15792d33e0cd387eb995d8d733c1fa1b98b2859153957c670f796a44e8e"
    )
    assert DECISION["central_decisions"][
        "bootstrap_source_set_changed_by_this_decision"
    ] is False
    assert DECISION["central_decisions"]["worker_package_changed_by_this_decision"] is (
        False
    )
    audit = r5.audit_authoritative_worker_source()
    assert audit["closed"] is True, audit["findings"]


def test_the_worker_package_is_byte_identical_to_the_reviewed_bootstrap_set() -> None:
    """The defect is parent-side, so the worker package must not have moved."""

    for entry in BOOTSTRAP_MANIFEST:
        assert protocol.file_sha256(ROOT / entry.path) == entry.sha256, entry.path
    assert protocol.bootstrap_manifest_digest(BOOTSTRAP_MANIFEST) == (
        "1811e04dac7a033de2c8e6620bf7d5aa227b94eebdf419657ecccf4d3fead411"
    )
    assert r5.WORKER_BOOTSTRAP_SOURCE_SET == r3.WORKER_BOOTSTRAP_SOURCE_SET
    assert protocol.WORKER_AUTHORITY_TICKET == "POSTP1-001V2A-PAD4-R2"


def test_the_frozen_proof_order_is_the_closed_authoritative_order() -> None:
    order = r5.proof_order_and_completeness_definition()
    assert len(r5.AUTHORITATIVE_EXECUTION_ORDER) == 13
    assert order["controller_or_review_order"] == list(
        r5.AUTHORITATIVE_EXECUTION_ORDER[:5]
    )
    assert order["controller_admission_order"] == list(
        r5.AUTHORITATIVE_EXECUTION_ORDER[5:]
    )
    assert order["controller_or_review_order"][0].endswith(
        "RECEIVE_THE_TRUSTED_CONTROLLER_AUTHORITY_CONTEXT"
    )
    assert order["controller_or_review_order"][2].endswith(
        "PREVERIFY_THE_COMPLETE_BOOTSTRAP_SOURCE_SET"
    )
    assert order["controller_admission_order"][1].endswith(
        "CANONICALIZE_THE_EXACT_VALIDATED_RESPONSE_AND_RESULT"
    )
    assert order["controller_admission_order"][2].endswith(
        "VERIFY_AND_BIND_THE_EXACT_RESULT_DIGEST_TO_THOSE_CANONICAL_BYTES"
    )
    assert order["controller_admission_order"][3].endswith(
        "PERFORM_SUCCESSFUL_SCIENTIFIC_ADMISSION_INSIDE_THAT_FLOW"
    )
    assert order["controller_admission_order"][4].endswith(
        "BIND_THE_IMMUTABLE_SNAPSHOT_TO_THE_EXACT_EXECUTION_IDENTITY"
    )
    assert order["controller_admission_order"][5].endswith(
        "CONSTRUCT_AFFIRMATIVE_EVIDENCE_FROM_THAT_IMMUTABLE_AUTHORITATIVE_TRUTH"
    )
    assert order["controller_admission_order"][-1].endswith(
        "SERVE_CALLER_FACING_ACCESS_WITHOUT_EXPOSING_AUTHORITY_BY_MUTABLE_REFERENCE"
    )
    assert order["raw_or_test_path_order"] == [
        "A_MAY_REPRODUCE_UNVERIFIED_WORKER_BEHAVIOUR",
        "B_CANNOT_ENTER_SCIENTIFIC_ADMISSION",
        "C_CANNOT_CONSTRUCT_AFFIRMATIVE_SCIENTIFIC_EVIDENCE",
    ]
    assert order["every_authority_bearing_step_is_owned_by_one_closed_operation"] is (
        True
    )
    assert order["no_bootstrap_project_source_executes_before_step_4_succeeds"] is True
    assert order["admitted_authority_is_frozen_before_it_becomes_caller_visible"] is (
        True
    )
    assert order["caller_facing_access_is_a_fresh_decode_of_frozen_bytes"] is True
    assert order["post_admission_mutation_can_redefine_authority"] is False
    required = order["required_adversarial_regressions"]
    for name in (
        "AFFIRMATIVE_EVIDENCE_MUTATION_IS_ISOLATED",
        "BOUND_RESULT_DIGEST_REPRODUCES_FROM_THE_FROZEN_SNAPSHOT",
        "CALLER_MUTATED_NESTED_MAPPING_CANNOT_CHANGE_AUTHORITY",
        "CALLER_MUTATED_NESTED_SEQUENCE_CANNOT_CHANGE_AUTHORITY",
        "CALLER_MUTATED_RESPONSE_CANNOT_CHANGE_AUTHORITY",
        "CALLER_MUTATED_RESULT_CANNOT_CHANGE_AUTHORITY",
        "CROSS_ACCESSOR_VALUES_SHARE_NO_MUTABLE_DESCENDANT",
        "DISCARDED_TEMPORARY_PARSER_STATE_CANNOT_CHANGE_AUTHORITY",
        "REPEATED_READS_RETURN_THE_ORIGINAL_ADMITTED_STATE",
        "SEQUENTIAL_REQUESTS_HAVE_INDEPENDENT_RETURN_STATE",
        "THE_REVIEWED_R3_RETURN_STATE_DEFECT_REPRODUCES_AS_A_CONTROL",
        "A_REFUSAL_CANNOT_BE_PROMOTED_TO_AN_ADMITTED_EXECUTION",
        "A_SUBCLASS_CANNOT_SPOOF_EQUALITY_TO_INHERIT_ADMITTED_AUTHORITY",
        "NO_CLASS_MEMBER_HANDS_OUT_THE_AUTHORITY_STORAGE",
        "SUPERSEDED_LINEAGE_EVIDENCE_IS_NOT_R4_AUTHORITY",
        "THE_FROZEN_AUTHORITY_SNAPSHOT_HAS_NO_MUTATING_API",
        "THE_IMMUTABILITY_GATE_REFUSES_MUTABLE_AND_MALFORMED_MATERIAL",
    ):
        assert name in required, name
    assert set(
        r3.proof_order_and_completeness_definition()[
            "required_adversarial_regressions"
        ]
    ) <= set(required)
    # inherited entries are R3-framed and are read against PAD4-R3; each such
    # property has an R5-framed counterpart in this parent's own list
    assert order["inherited_adversarial_regressions_are_read_against_their_own_parent"]
    assert "SUPERSEDED_LINEAGE_EVIDENCE_IS_NOT_R3_AUTHORITY" in required
    assert "SUPERSEDED_LINEAGE_EVIDENCE_IS_NOT_R4_AUTHORITY" in required


def test_the_affirmative_evidence_fields_the_child_names_all_exist(
    admitted_session,
) -> None:
    """Material-child truthfulness: the named evidence fields are really there."""

    evidence = admitted_session.scientific_evidence
    child = r5.affirmative_evidence_snapshot_rule()
    for field in child["evidence_fields_derived_from_controller_owned_authority"]:
        assert field in evidence, field
    assert evidence["scientific_authority"] == child["affirmative_authority_marker"]
    assert child["evidence_construction_sites"] == 1
    assert child["evidence_constructed_from_live_parser_state"] is False
    assert child["evidence_construction_happens_after_the_snapshot_is_frozen"] is True
    # the evidence's own digest is bound, and reproduces from the frozen bytes
    proof = admitted_session.authoritative_snapshot_proof()
    assert proof["bound_affirmative_evidence_digest"] == (
        proof["affirmative_evidence_digest_recomputed_from_frozen_bytes"]
    )


def test_no_executable_ipc_and_no_worker_visible_secret() -> None:
    source = (ROOT / r5.CONTROLLER_RELATIVE_PATH).read_text("utf-8")
    for forbidden in ("pickle", "cloudpickle", "dill", "marshal"):
        assert f"import {forbidden}" not in source
    for forbidden in ("hmac", "secrets"):
        assert f"import {forbidden}" not in source
    assert DECISION["central_decisions"]["pickle_ipc_permitted"] is False
    assert DECISION["central_decisions"]["worker_visible_shared_secret_introduced"] is (
        False
    )
    assert DECISION["central_decisions"][
        "cryptographic_ceremony_introduced_by_this_decision"
    ] is False
    boundary = r5.authoritative_scientific_execution_boundary()
    assert boundary["worker_computable_mac_key_introduced"] is False
    assert boundary["cryptographic_ceremony_introduced"] is False
    assert boundary["authority_mechanism"] == (
        "IDENTITY_SAFE_LIVE_WEAK_WITNESS_BINDING_PLUS_CLOSED_CONTROL_FLOW_AND_"
        "CAPABILITY_OWNERSHIP_PLUS_IMMUTABLE_CANONICAL_SNAPSHOT_STORAGE"
    )
    assert boundary["closed_r3_authority_flow_preserved"] is True
    assert boundary["construction_authority_weakened_by_this_decision"] is False


def test_the_r5_boundary_child_carries_the_reviewed_r4_key_set() -> None:
    """Nothing the reviewed boundary contract stated is silently dropped."""

    r3_boundary = r4.authoritative_scientific_execution_boundary()
    boundary = r5.authoritative_scientific_execution_boundary()
    missing = sorted(set(r3_boundary) - set(boundary))
    assert missing == []
    added = set(boundary) - set(r3_boundary)
    assert {
        "authority_lookup_uses_exact_identity",
        "receiver_equality_is_authority",
        "receiver_hash_equivalence_is_authority",
        "live_witness_identity_check_required",
        "exact_type_guard_required",
        "identity_safe_lookup_is_load_bearing",
        "construction_identity_audit",
        "relay_residual_closed",
        "threat_model_domain",
    } <= added
    unchanged = sorted(
        name
        for name in r3_boundary
        if name != "definition_sha256" and boundary[name] == r3_boundary[name]
    )
    # the reviewed negatives that are the authority boundary stay exactly as they
    # were reviewed
    for name in (
        "caller_may_construct_the_authoritative_execution",
        "class_naming_is_authority",
        "construction_bypass_yields_unowned_object_that_refuses",
        "cryptographic_ceremony_introduced",
        "field_values_are_authority",
        "generic_admission_function_exists",
        "generic_evidence_function_exists",
        "generic_raw_outcome_type_exists_in_production",
        "isinstance_of_a_public_dataclass_is_authority",
        "leading_underscore_is_authority_boundary",
        "raw_unverified_spawn_in_production_authority_surface",
        "raw_unverified_spawn_location",
        "worker_computable_mac_key_introduced",
        "worker_visible_secret_introduced",
    ):
        assert name in unchanged, name


def test_safety_posture_is_unchanged() -> None:
    lineage = r5.science_lineage_and_safety()
    assert lineage["preserved_science"] == {
        "calendar_normalization_early_closes_pit_common_session_rules": "UNCHANGED",
        "etf_formulas_and_revision_semantics": "UNCHANGED",
        "etf_calendar_production_code_changed_by_this_decision": False,
        "parser_science": "UNCHANGED",
        "source_urls_profiles_tls_redirects": "UNCHANGED",
        "stage_b_metrics_risk_stops_thresholds": "UNCHANGED",
    }
    assert lineage["preserved_science"] == (
        r3.science_lineage_and_safety()["preserved_science"]
    )
    assert DECISION["authorization"]["prospective_collection_may_begin"] is False
    assert DECISION["authorization"]["calendar_implementation_may_begin"] is False
    assert DECISION["authorization"]["postp1_001v2r1_may_begin"] is False
    assert DECISION["authorization"][
        "independent_proof_architecture_xhigh_review_may_begin"
    ] is True


def test_the_lazy_result_refusal_is_reused_unchanged() -> None:
    from etf_calendar_worker import protocol_r1 as owner

    assert r5.worker_io_and_capability_boundary() == (
        r3.worker_io_and_capability_boundary()
    )
    assert DECISION["central_decisions"]["lazy_result_permitted"] is False
    assert set(owner.LAZY_RESULT_KINDS) >= {
        "ASYNC_GENERATOR",
        "AWAITABLE",
        "CALLABLE",
        "COROUTINE",
        "GENERATOR",
        "ITERATOR",
        "MEMORYVIEW",
    }
    for value in ((x for x in (1,)), iter([1]), memoryview(b"x"), len):
        with pytest.raises(
            protocol.ScientificWorkerProtocolError,
            match="LAZY_SCIENTIFIC_RESULT_REFUSED",
        ):
            owner.refuse_lazy_result(value)


def test_the_preserved_canonical_rejections_name_real_protocol_reasons() -> None:
    """Every named rejection must be greppable in the reused protocol itself."""

    from etf_calendar_worker import protocol_r1 as owner

    protocol_source = "".join(
        (ROOT / relative).read_text("utf-8")
        for relative in (
            "etf_calendar_worker/protocol_r1.py",
            "etf_calendar_worker/protocol_r2.py",
        )
    )
    for reason in r5.PRESERVED_CANONICAL_REJECTIONS:
        assert f'"{reason}"' in protocol_source, reason
    assert r5.PRESERVED_TIMESTAMP_REJECTION in protocol_source
    for reason in r5.REQUEST_TRANSPORT_ONLY_CANONICAL_REJECTIONS:
        assert reason in r5.PRESERVED_CANONICAL_REJECTIONS
        # scope-qualified honestly: it is the request transport's re-serialisation
        # equality check, and the worker applies it to the request
        assert reason in (ROOT / "etf_calendar_worker/protocol_r1.py").read_text("utf-8")
    child = r5.canonical_admitted_snapshot_rule()
    assert child["preserved_canonical_rejections_are_exact_protocol_reasons"] is True
    assert child["response_side_re_serialization_equality_check_claimed"] is False
    assert child["preserved_canonical_rejections"] == list(
        r5.PRESERVED_CANONICAL_REJECTIONS
    )
    assert owner.canonical_json_bytes is protocol.canonical_json_bytes


def test_the_preserved_canonical_rejections_are_the_reused_protocol_rules() -> None:
    """R5 introduces no second canonicalisation, so none of these is weakened."""

    assert r5.CANONICAL_AUTHORITY_ENCODER == (
        "etf_calendar_worker.protocol_r1.canonical_json_bytes"
    )
    for payload in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(protocol.ScientificWorkerProtocolError):
            protocol.canonical_json_bytes({"value": payload})
    for raw_bytes in (b"NaN", b"Infinity", b"-Infinity"):
        with pytest.raises(protocol.ScientificWorkerProtocolError):
            protocol.parse_canonical_json(raw_bytes)
    with pytest.raises(protocol.ScientificWorkerProtocolError):
        protocol.parse_canonical_json(b'{"a":1}{"b":2}')
    with pytest.raises(protocol.ScientificWorkerProtocolError):
        protocol.validate_response({"unknown": 1})
    assert protocol.canonical_json_bytes({"b": 1, "a": 2}) == b'{"a":2,"b":1}'
    assert protocol.canonical_json_bytes(None) == b"null"
    assert protocol.parse_canonical_json(b"null") is None


# ---------------------------------------------------------------------------
# Preserved failure admission, driven through the closed flow
# ---------------------------------------------------------------------------


def _completed(stdout: bytes, returncode: int = 0):
    """A crafted worker process result, injected at the process boundary.

    This patches ``subprocess.run`` — the operating-system boundary — rather than
    any project API, because R5 deliberately offers no API that accepts a
    caller-built outcome.  It is the only way left to drive the admission
    branches, and it proves they still refuse.
    """

    class _Result:
        def __init__(self) -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = b""

    return _Result()


@pytest.mark.parametrize(
    "stdout,returncode,expected",
    [
        (b"", 1, "WORKER_EXIT_STATUS_1"),
        (b"", -9, "WORKER_EXIT_STATUS_-9"),
        (b'{"a": 1}\nextra\n', 0, "WORKER_STDOUT_IS_NOT_EXACTLY_ONE_PROTOCOL_PAYLOAD"),
        (b"not canonical json\n", 0, "WORKER_PROTOCOL_ERROR"),
        (b"{}\n", 0, "WORKER_PROTOCOL_ERROR"),
    ],
)
def test_worker_failure_modes_are_never_admitted(
    stdout: bytes,
    returncode: int,
    expected: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        r5.subprocess, "run", lambda *a, **k: _completed(stdout, returncode)
    )
    execution = _run(SESSION_REQUEST)
    assert execution.admitted is False
    assert execution.failure_reason.startswith(expected), execution.failure_reason
    assert execution.result is None
    evidence = execution.scientific_evidence
    assert evidence["admitted"] is False
    assert evidence["result_digest"] is None
    assert execution.authoritative_snapshot_proof()["bound_result_digest"] is None


def test_oversized_worker_output_is_never_admitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oversized = b"x" * (protocol.MAX_RESPONSE_BYTES + 1) + b"\n"
    monkeypatch.setattr(r5.subprocess, "run", lambda *a, **k: _completed(oversized))
    execution = _run(SESSION_REQUEST)
    assert execution.admitted is False
    assert execution.failure_reason == "WORKER_OUTPUT_EXCEEDS_THE_FROZEN_LIMIT"


def test_a_tampered_result_digest_is_never_admitted(
    admitted_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An honest response whose result is swapped afterwards must refuse.

    The payload is built from ``admitted_session.response`` — already a detached
    decode — so tampering with it cannot disturb the admitted execution it came
    from, which is asserted here too.
    """

    before = _snapshot(admitted_session)
    payload = admitted_session.response
    payload["result"]["state"] = "TAMPERED_AFTER_THE_FACT"
    stdout = protocol.canonical_json_bytes(payload) + b"\n"
    assert _snapshot(admitted_session) == before

    monkeypatch.setattr(r5.subprocess, "run", lambda *a, **k: _completed(stdout))
    execution = _run(SESSION_REQUEST)
    assert execution.admitted is False
    assert execution.failure_reason == "WORKER_RESULT_DIGEST_MISMATCH"
    assert execution.result is None
    assert execution.scientific_evidence["admitted"] is False
    assert _snapshot(admitted_session) == before
