"""POSTP1-001V2A-PAD4-R5 exact execution identity regressions."""

from __future__ import annotations

import gc
import inspect
import platform
from pathlib import Path
from weakref import ref as weakref_ref

import pytest

from btc_predictor.research import etf_calendar_isolated_scientific_worker_r4 as r4
from btc_predictor.research import etf_calendar_isolated_scientific_worker_r5 as r5
from btc_predictor.tests import test_etf_calendar_isolated_scientific_worker_r2 as base


ROOT = Path(__file__).resolve().parents[2]
DECISION = r5.isolated_scientific_worker_v1_r5_definition()
CANDIDATE_HASH = DECISION["definition_sha256"]
CONTEXT = r5.candidate_review_authority_context(CANDIDATE_HASH)
LAUNCH = r5.worker_launch()

SESSION_REQUEST = r5.build_scientific_request(
    CONTEXT,
    launch=LAUNCH,
    operation="common_etf_session_status",
    operation_inputs={"trade_date": base.SESSION_DAY.isoformat()},
    evidence_records=base.SESSION_RECORDS,
    decision_time=base.DECISION_TIME.isoformat(),
)

R4_CONTEXT = r4.candidate_review_authority_context(r5.FAILED_PAD4_R4_SHA256)
R4_REQUEST = r4.build_scientific_request(
    R4_CONTEXT,
    launch=r4.worker_launch(),
    operation="common_etf_session_status",
    operation_inputs={"trade_date": base.SESSION_DAY.isoformat()},
    evidence_records=base.SESSION_RECORDS,
    decision_time=base.DECISION_TIME.isoformat(),
)


def _run():
    execution = r5.run_isolated_scientific_request(CONTEXT, SESSION_REQUEST, LAUNCH)
    assert execution.admitted is True, execution.failure_reason
    return execution


@pytest.fixture(scope="module")
def admitted():
    return _run()


def test_decision_is_the_bounded_r5_successor_only() -> None:
    assert DECISION["program_ticket"] == "POSTP1-001V2A-PAD4-R5"
    assert DECISION["correction_of"] == r5.FAILED_PAD4_R4_SHA256
    assert DECISION["correction_scope"] == (
        "BOUNDED_AUTHORITATIVE_EXECUTION_EXACT_IDENTITY_BINDING"
    )
    assert DECISION["required_review"].startswith("POSTP1-002V2A-PAD4-R5")
    assert DECISION["authorization"] == {
        "independent_proof_architecture_xhigh_review_may_begin": True,
        "calendar_implementation_may_begin": False,
        "postp1_001v2a_i2_may_begin": False,
        "postp1_001v2r1_may_begin": False,
        "prospective_collection_may_begin": False,
    }
    assert DECISION["central_decisions"]["relay_residual_closed"] is False


def test_proof_interpreter_identity_assumptions_are_reconfirmed_exclusively_here() -> None:
    probe = r5.probe_proof_interpreter_identity_assumptions()
    assert platform.python_implementation() == "CPython"
    assert platform.python_version() == "3.12.14"
    assert probe["is_frozen_proof_interpreter"] is True
    assert probe["weakref_equality_can_follow_referent_equality"] is True
    assert probe["weakref_hash_can_follow_referent_hash"] is True
    assert probe["callbackless_weakref_is_interned"] is True
    assert probe["callback_weakrefs_are_not_interned"] is True
    assert probe["weakref_callback_fires_after_collection"] is True
    assert probe["first_weakref_hash_after_referent_death_is_refused"] is True
    assert probe["previously_computed_weakref_hash_survives_referent_death"] is True
    assert probe["type_builtin_ignores_spoofed___class___property"] is True
    assert probe["identifier_reuse_observed_after_collection"] is True


def test_identity_binding_audit_is_behaviorally_computed_and_closed() -> None:
    audit = r5.audit_authoritative_return_state()
    assert audit["closed"] is True, audit["findings"]
    assert audit["authority_reader_registry_fetch_count"] == 1
    assert audit["authority_reader_live_witness_identity_compare_count"] == 1
    assert audit["authority_receiver_exact_type_guard_count"] == 1
    assert audit["single_capability_gated_bind"] is True
    assert audit["conditional_cleanup_is_witness_specific"] is True
    assert audit["authority_storage_binding_is_resolved_by_identity_not_equality"] is True
    assert audit["authority_storage_binding_is_resolved_by_equality_not_identity"] is False
    assert audit["exact_type_guard_is_load_bearing"] is False
    assert audit["live_witness_identity_compare_is_load_bearing"] is True
    assert audit["object_identity___eq___preserved"] is True
    assert audit["object_identity___hash___preserved"] is True
    behavior = audit["behavioral_identity_safety_probe"]
    assert behavior["exact_owner_resolves"] is True
    assert behavior["foreign_equal_hash_equivalent_receiver_refused"] is True
    assert behavior["stale_identifier_bucket_refused_by_live_witness_identity"] is True
    assert behavior["newer_entry_survives_stale_cleanup"] is True
    assert behavior["receiver_controlled_eq_calls"] == 0
    assert behavior["receiver_controlled_hash_calls"] == 0
    assert behavior["receiver_controlled_class_calls"] == 0


def test_r4_descriptor_reuse_defect_reproduces_and_r5_refuses(admitted) -> None:
    """Checked-in R4-fails/R5-passes control for the independent review."""

    r4_execution = r4.run_isolated_scientific_request(
        R4_CONTEXT, R4_REQUEST, r4.worker_launch()
    )
    assert r4_execution.admitted is True, r4_execution.failure_reason

    r4_admitted = vars(r4.AuthoritativeScientificExecution)["admitted"]
    r4_proof = vars(r4.AuthoritativeScientificExecution)[
        "authoritative_snapshot_proof"
    ]
    target_hash = hash(r4_execution)

    class R4Foreign:
        admitted = r4_admitted
        authoritative_snapshot_proof = r4_proof

        def __hash__(self) -> int:
            return target_hash

        def __eq__(self, other: object) -> bool:
            return True

    foreign_r4 = R4Foreign()
    assert foreign_r4 is not r4_execution
    assert foreign_r4.admitted is True
    assert foreign_r4.authoritative_snapshot_proof()["admitted"] is True

    calls = {"hash": 0, "eq": 0, "class": 0}
    r5_admitted = vars(r5.AuthoritativeScientificExecution)["admitted"]
    r5_proof = vars(r5.AuthoritativeScientificExecution)[
        "authoritative_snapshot_proof"
    ]

    class R5Foreign:
        admitted = r5_admitted
        authoritative_snapshot_proof = r5_proof

        @property
        def __class__(self):
            calls["class"] += 1
            return r5.AuthoritativeScientificExecution

        def __hash__(self) -> int:
            calls["hash"] += 1
            return hash(admitted)

        def __eq__(self, other: object) -> bool:
            calls["eq"] += 1
            return True

    foreign_r5 = R5Foreign()
    with pytest.raises(r5.AuthoritativeExecutionConstructionError):
        _ = foreign_r5.admitted
    with pytest.raises(r5.AuthoritativeExecutionConstructionError):
        foreign_r5.authoritative_snapshot_proof()
    assert calls == {"hash": 0, "eq": 0, "class": 0}


def test_every_live_authority_property_refuses_a_foreign_receiver(admitted) -> None:
    calls = {"hash": 0, "eq": 0, "class": 0}

    class Foreign:
        @property
        def __class__(self):
            calls["class"] += 1
            return r5.AuthoritativeScientificExecution

        def __hash__(self) -> int:
            calls["hash"] += 1
            return hash(admitted)

        def __eq__(self, other: object) -> bool:
            calls["eq"] += 1
            return True

    foreign = Foreign()
    for name, descriptor in vars(r5.AuthoritativeScientificExecution).items():
        if isinstance(descriptor, property):
            with pytest.raises(r5.AuthoritativeExecutionConstructionError):
                descriptor.fget(foreign)
    with pytest.raises(r5.AuthoritativeExecutionConstructionError):
        vars(r5.AuthoritativeScientificExecution)["authoritative_snapshot_proof"](
            foreign
        )
    with pytest.raises(r5.AuthoritativeExecutionConstructionError):
        vars(r5.AuthoritativeScientificExecution)["__repr__"](foreign)
    assert calls == {"hash": 0, "eq": 0, "class": 0}


def test_exact_owner_continues_to_resolve_every_authority_surface(admitted) -> None:
    assert admitted.admitted is True
    assert admitted.failure_reason is None
    assert isinstance(admitted.request_digest, str)
    assert isinstance(admitted.result, dict)
    assert isinstance(admitted.response, dict)
    assert admitted.scientific_evidence["admitted"] is True
    proof = admitted.authoritative_snapshot_proof()
    assert proof["admitted"] is True
    assert proof["bound_digests_reproduce"] is True
    assert "admitted=True" in repr(admitted)


def test_direct_new_subclass_and_exact_class_nonowned_construction_refuse() -> None:
    with pytest.raises(r5.AuthoritativeExecutionConstructionError):
        r5.AuthoritativeScientificExecution()

    forged = r5.AuthoritativeScientificExecution.__new__(
        r5.AuthoritativeScientificExecution
    )
    for name in ("admitted", "result", "response", "scientific_evidence"):
        with pytest.raises(r5.AuthoritativeExecutionConstructionError):
            getattr(forged, name)
    with pytest.raises(r5.AuthoritativeExecutionConstructionError):
        forged.authoritative_snapshot_proof()
    with pytest.raises(r5.AuthoritativeExecutionConstructionError):
        repr(forged)

    with pytest.raises(r5.AuthoritativeExecutionConstructionError):
        type("Unsupported", (r5.AuthoritativeScientificExecution,), {"__slots__": ()})


def test_failed_reinitialization_cannot_disturb_a_real_owner(admitted) -> None:
    before = admitted.authoritative_snapshot_proof()
    with pytest.raises(r5.AuthoritativeExecutionConstructionError):
        r5.AuthoritativeScientificExecution.__init__(admitted)
    assert admitted.authoritative_snapshot_proof() == before


def test_registry_does_not_retain_execution_strongly() -> None:
    execution = _run()
    witness = weakref_ref(execution)
    assert witness() is execution
    del execution
    gc.collect()
    assert witness() is None


def test_concurrently_live_exact_owners_are_independent() -> None:
    left = _run()
    right = _run()
    assert left is not right
    left_result = left.result
    left_result["caller_mutation"] = True
    assert "caller_mutation" not in left.result
    assert "caller_mutation" not in right.result
    assert left.authoritative_snapshot_proof()["bound_digests_reproduce"] is True
    assert right.authoritative_snapshot_proof()["bound_digests_reproduce"] is True


def test_authoritative_class_keeps_object_identity_eq_and_hash() -> None:
    cls = r5.AuthoritativeScientificExecution
    assert cls.__eq__ is object.__eq__
    assert cls.__hash__ is object.__hash__


def test_source_contains_no_rejected_binding_design() -> None:
    source = (ROOT / r5.CONTROLLER_RELATIVE_PATH).read_text("utf-8")
    factory = source[
        source.index("def _build_authoritative_scientific_execution_boundary"):
        source.index("del _build_authoritative_scientific_execution_boundary")
    ]
    assert "WeakKeyDictionary(" not in factory
    assert "_material[self]" not in factory
    assert "_material[receiver]" not in factory
    assert "hash(receiver)" not in factory
    assert "receiver.__class__" not in factory
    assert "isinstance(receiver" not in factory
    reader = factory[factory.index("    def _frozen("):factory.index("    class AuthoritativeScientificExecution")]
    assert reader.count("_material.get(bucket)") == 1
    assert "if type(receiver) is not AuthoritativeScientificExecution:" in reader
    assert "if live_witness is receiver:" in reader


def test_required_r5_material_contracts_are_bound() -> None:
    children = r5._children()
    required = {
        "authoritative_execution_identity_rule",
        "identity_safe_snapshot_binding_rule",
        "authority_receiver_validation_rule",
        "construction_identity_audit_rule",
    }
    assert required <= set(children)
    assert DECISION["material_child_count"] == len(children)
    for name in required:
        r5._verify_definition_digest(children[name])


def test_unchanged_r4_children_are_byte_identical_by_definition() -> None:
    r4_children = r4._children()
    r5_children = r5._children()
    for name in r5.VERBATIM_PAD4_R4_CHILDREN:
        assert r5_children[name] == r4_children[name], name


def test_r4_namespace_and_controller_are_not_mutated_by_r5() -> None:
    assert r5.FAILED_PAD4_R4_SHA256 == (
        "ae25c2468972725a0ebd2f7742a532f3ec616c2e2cc8e94d93b3de46f86e65bc"
    )
    assert r5.science_lineage_and_safety()["corrected_predecessor"][
        "definition_sha256"
    ] == r5.FAILED_PAD4_R4_SHA256
    assert r5.science_lineage_and_safety()["corrected_predecessor"][
        "namespace_mutated_by_this_correction"
    ] is False


def test_relay_is_explicitly_left_open() -> None:
    assert r5.authoritative_execution_identity_rule()["relay_residual_closed"] is False
    assert r5.authoritative_scientific_execution_boundary()[
        "relay_residual_closed"
    ] is False
    assert r5.proof_order_and_completeness_definition()[
        "relay_residual_closed"
    ] is False


def test_only_one_public_producer_returns_the_authoritative_type() -> None:
    producers = []
    for name, value in vars(r5).items():
        if not inspect.isfunction(value):
            continue
        annotation = inspect.signature(value).return_annotation
        if "AuthoritativeScientificExecution" in str(annotation):
            producers.append(name)
    assert producers == ["run_isolated_scientific_request"]
