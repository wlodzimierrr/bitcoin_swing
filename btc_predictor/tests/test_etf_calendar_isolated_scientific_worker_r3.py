"""POSTP1-001V2A-PAD4-R3 authority-closed isolated scientific worker tests.

``POSTP1-002V2A-PAD4-R2`` failed ``PAD4-R2`` with
``FAIL — AUTHORITATIVE LAUNCH / ADMISSION BYPASS``.  The decisive regressions in
this module are the four bypass reproductions: each one first proves, as a
*control*, that the reviewed bypass really works at the raw layer, and then
proves that nothing it produces can enter R3 scientific admission or obtain
affirmative R3 scientific authority evidence.

The reviewed ``PAD4-R2`` fixtures — the certified tree, the pre-launch drifted
bootstrap trees, the forged bytecode and the fabricated-result probe — are
imported rather than forked, so the preserved properties are re-proved with the
same material the review reproduced, driven through the *R3* closed flow.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from btc_predictor.features import flow as _flow
from btc_predictor.research import etf_calendar_isolated_scientific_worker_r1 as r1
from btc_predictor.research import etf_calendar_isolated_scientific_worker_r2 as r2
from btc_predictor.research import etf_calendar_isolated_scientific_worker_r3 as r3
from btc_predictor.tests import etf_calendar_raw_worker_harness_r3 as raw
from btc_predictor.tests import test_etf_calendar_isolated_scientific_worker_r2 as base
from etf_calendar_worker import protocol_r2 as protocol


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / r3.OUTPUT_NAMESPACE
R2_ARTIFACT_DIR = ROOT / r2.OUTPUT_NAMESPACE

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

DECISION = r3.isolated_scientific_worker_v1_r3_definition()
CANDIDATE_HASH = DECISION["definition_sha256"]

#: The trusted R3 context a reviewer or harness instantiates for this candidate.
CONTEXT = r3.candidate_review_authority_context(CANDIDATE_HASH)
LAUNCH = r3.worker_launch()
MANIFEST = r3.frozen_candidate_source_manifest()
BOOTSTRAP_MANIFEST = r3.frozen_bootstrap_source_manifest()


def session_request(context=None, launch=None, **overrides) -> dict:
    return r3.build_scientific_request(
        CONTEXT if context is None else context,
        launch=LAUNCH if launch is None else launch,
        operation="common_etf_session_status",
        operation_inputs={"trade_date": SESSION_DAY.isoformat()},
        evidence_records=overrides.pop("evidence_records", base.SESSION_RECORDS),
        decision_time=DECISION_TIME.isoformat(),
        **overrides,
    )


def flow_request(context=None, launch=None, **overrides) -> dict:
    return r3.build_scientific_request(
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
    """Record every worker process the R3 controller actually creates."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.calls: list[list[str]] = []
        original = subprocess.run

        def recording_run(argv, *args, **kwargs):
            self.calls.append([str(part) for part in argv])
            return original(argv, *args, **kwargs)

        monkeypatch.setattr(r3.subprocess, "run", recording_run)

    @property
    def worker_spawns(self) -> list[list[str]]:
        return [
            argv
            for argv in self.calls
            if any(part.endswith(ENTRYPOINT) for part in argv)
        ]


def _run(request: dict, launch=None, context=None, **kwargs):
    return r3.run_isolated_scientific_request(
        CONTEXT if context is None else context,
        request,
        LAUNCH if launch is None else launch,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Decision integrity
# ---------------------------------------------------------------------------


def test_decision_scope_status_and_strategy_are_frozen() -> None:
    assert DECISION["decision_version"] == "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1"
    assert DECISION["program_ticket"] == "POSTP1-001V2A-PAD4-R3"
    assert DECISION["pre_data"] is True
    assert DECISION["status"] == (
        "FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_FINAL_XHIGH_REVIEW"
    )
    assert DECISION["final_classification"] == (
        "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_R3_READY_FOR_FINAL_XHIGH_REVIEW"
    )
    assert DECISION["correction_of"] == r3.FAILED_PAD4_R2_SHA256
    assert DECISION["correction_is_a_new_architecture_family"] is False
    assert DECISION["required_review"].startswith("POSTP1-002V2A-PAD4-R3")
    assert DECISION["authorization"] == {
        "independent_proof_architecture_xhigh_review_may_begin": True,
        "calendar_implementation_may_begin": False,
        "postp1_001v2a_i2_may_begin": False,
        "postp1_001v2r1_may_begin": False,
        "prospective_collection_may_begin": False,
    }


def test_material_children_are_mechanical_bound_and_digest_valid() -> None:
    children = r3._children()
    assert len(children) == 25
    assert DECISION["material_child_count"] == 25
    assert DECISION["material_child_enumeration"] == (
        "MECHANICALLY_ENUMERATED_FROM_ONE_REGISTRY"
    )
    assert set(DECISION["child_definition_sha256"]) == set(children)
    for name, child in children.items():
        assert DECISION["child_definition_sha256"][name] == child["definition_sha256"]
        r3._verify_definition_digest(child)
    assert len({name for name, _ in r3._CHILD_ARTIFACTS}) == 25


def test_the_three_new_children_own_the_correction() -> None:
    children = r3._children()
    for name in (
        "authoritative_scientific_execution_boundary",
        "admission_provenance_rule",
        "scientific_evidence_authority_rule",
    ):
        assert name in children
        assert name not in r3.VERBATIM_PAD4_R2_CHILDREN
        assert not (R2_ARTIFACT_DIR / f"{name}.json").exists()


def test_preserved_children_are_byte_identical_to_the_reviewed_pad4_r2() -> None:
    """The preservation claim is mechanical, not rhetorical."""

    children = r3._children()
    assert len(r3.VERBATIM_PAD4_R2_CHILDREN) == 16
    for name in r3.VERBATIM_PAD4_R2_CHILDREN:
        persisted = json.loads((R2_ARTIFACT_DIR / f"{name}.json").read_text("ascii"))
        assert children[name] == persisted, name


def test_central_decisions_bind_the_admission_closure_anchors() -> None:
    decisions = DECISION["central_decisions"]
    assert decisions["bootstrap_preverification_required_before_spawn"] is True
    assert decisions["unverified_worker_outcome_scientifically_admissible"] is False
    assert decisions["generic_raw_outcome_to_scientific_admission_supported"] is False
    assert (
        decisions["scientific_admission_requires_same_authoritative_controller_"
                  "execution"]
        is True
    )
    assert decisions["caller_fabricated_preverification_mapping_is_authority"] is False
    assert decisions["caller_constructed_outcome_is_authority"] is False
    assert decisions["caller_constructed_admission_state_is_authority"] is False
    assert decisions["worker_can_mint_controller_admission_provenance"] is False
    assert (
        decisions["affirmative_scientific_evidence_created_only_inside_"
                  "authoritative_path"]
        is True
    )
    assert decisions["leading_underscore_is_authority_boundary"] is False
    assert decisions["authoritative_scientific_execution_is_closed_end_to_end"] is True
    assert decisions["fresh_exec_required"] is True
    assert decisions["fresh_empty_pycache_namespace_required"] is True
    assert decisions["runtime_source_manifest_rederivation_permitted"] is False
    assert decisions["trusted_controller_authority_context_required"] is True
    assert decisions["third_party_installed_file_verification_required"] is True
    assert decisions["runtime_object_closure_is_completeness_proof"] is False
    assert decisions["bootstrap_preverification_mapping_is_diagnostic_not_authority"] is True
    assert decisions["raw_unverified_spawn_in_production_authority_surface"] is False
    assert decisions["worker_visible_shared_secret_introduced"] is False
    assert decisions["cryptographic_ceremony_introduced_by_this_decision"] is False


def test_preserved_portions_and_the_not_reopened_scope_are_explicit() -> None:
    preserved = set(DECISION["preserved_valid_portions"])
    for name in (
        "BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING_ON_THE_AUTHORITATIVE_PATH",
        "BYTECODE_EXECUTION_BINDING_REPAIR_A",
        "CLOSED_STORE_GRAMMAR",
        "COMPILED_ROOT_WITNESS",
        "DIRECT_DEPENDENCY_BODY_RULE",
        "EXACT_ELEVEN_OWNER_GRAPH",
        "FOUR_MEMBER_BOOTSTRAP_SOURCE_SET",
        "FRESH_EXEC_ISOLATION",
        "FROZEN_SOURCE_AUTHORITY_REPAIR_B",
        "THIRD_PARTY_EXACT_VERSION_AND_ARTIFACT_AUTHORITY_REPAIR_D",
        "TRUSTED_CONTROLLER_AUTHORITY_CONTEXT_REPAIR_C",
    ):
        assert name in preserved, name
    not_reopened = set(DECISION["not_reopened"])
    for name in (
        "BOOTSTRAP_SOURCE_DERIVATION",
        "FRESH_PYCACHE_ARCHITECTURE",
        "PROCESS_ISOLATION_ARCHITECTURE",
        "THIRD_PARTY_RECORD_AND_CONTENT_AUTHORITY",
    ):
        assert name in not_reopened, name
    assert DECISION["confirmed_not_a_defect"] == [
        "CANDIDATE_REVIEW_AUTHORITY_CONTEXT_ACCEPTS_A_WELL_FORMED_CANDIDATE_SHA"
    ]


def test_the_whole_failed_lineage_is_preserved_immutably() -> None:
    lineage = r3.science_lineage_and_safety()["failed_architecture_lineage"]
    shas = {row["definition_sha256"] for row in lineage}
    for failed in (
        r3.FAILED_PAD4_SHA256,
        r3.FAILED_PAD4_R1_SHA256,
        r3.FAILED_PAD4_R2_SHA256,
    ):
        assert failed in shas
    for row in lineage:
        assert row["certified"] is False
        assert row["failed"] is True
        assert row["used"] is False
        assert row["prospective_observations"] == 0
        assert row["immutable"] is True
    assert DECISION["failed_pad4_r2_artifacts_overwritten"] is False
    assert DECISION["failed_pad4_r2_namespace_mutated"] is False
    persisted = json.loads(
        (R2_ARTIFACT_DIR / r2.DEFINITION_FILENAME).read_text("ascii")
    )
    assert persisted["definition_sha256"] == r3.FAILED_PAD4_R2_SHA256
    r2.restore_artifacts(R2_ARTIFACT_DIR)


def test_trusted_persistence_authority_is_unchanged_and_not_re_reviewed() -> None:
    lineage = r3.science_lineage_and_safety()
    assert lineage["trusted_persistence_authority"] == {
        "definition_sha256": (
            "02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772"
        ),
        "status": "CLOSED_CERTIFIED_UNCHANGED",
        "re_reviewed_by_this_decision": False,
    }
    assert DECISION["certified_dependency_sha256"] == (
        "02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772"
    )


def test_write_and_restore_artifacts_round_trip(tmp_path: Path) -> None:
    decision = r3.write_artifacts(tmp_path / "out")
    assert decision == DECISION
    assert r3.restore_artifacts(tmp_path / "out") == DECISION


def test_persisted_namespace_reproduces_exactly() -> None:
    assert r3.restore_artifacts(ARTIFACT_DIR) == DECISION


def test_restore_refuses_a_mutated_child(tmp_path: Path) -> None:
    r3.write_artifacts(tmp_path / "out")
    target = tmp_path / "out" / "admission_provenance_rule.json"
    payload = json.loads(target.read_text("ascii"))
    payload["provenance_is_a_value"] = True
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", "ascii")
    with pytest.raises(r3.IsolatedScientificWorkerR3Error):
        r3.restore_artifacts(tmp_path / "out")


def test_restore_refuses_a_mutated_report(tmp_path: Path) -> None:
    r3.write_artifacts(tmp_path / "out")
    target = tmp_path / "out" / r3.REPORT_FILENAME
    target.write_text(target.read_text("utf-8") + "\ndrift\n", "utf-8")
    with pytest.raises(r3.IsolatedScientificWorkerR3Error):
        r3.restore_artifacts(tmp_path / "out")


def test_child_order_variation_does_not_change_the_parent() -> None:
    reversed_registry = tuple(reversed(r3._CHILD_ARTIFACTS))
    assert r3.isolated_scientific_worker_v1_r3_definition(reversed_registry) == DECISION


def test_candidate_hash_is_not_embedded_in_its_own_certified_source() -> None:
    source = (ROOT / r3.CONTROLLER_RELATIVE_PATH).read_text("utf-8")
    assert CANDIDATE_HASH not in source
    assert DECISION["central_decisions"]["candidate_parent_hash_self_embedded"] is False


MATERIAL_MUTATIONS = [
    # -- the R3 correction, one entry per frozen decision POSTP1-001V2A-PAD4-R3
    #    is required to be sensitive to
    ("admission_provenance_rule",
     "unverified_worker_outcome_scientifically_admissible"),
    ("authoritative_scientific_execution_boundary", "closed_authority_path"),
    ("authoritative_scientific_execution_boundary",
     "authoritative_execution_order"),
    ("admission_provenance_rule", "caller_constructed_outcome_is_authority"),
    ("admission_provenance_rule", "caller_constructed_admission_state_is_authority"),
    ("scientific_evidence_authority_rule",
     "affirmative_scientific_evidence_created_only_inside_authoritative_path"),
    ("admission_provenance_rule", "worker_can_mint_controller_admission_provenance"),
    ("admission_provenance_rule", "bootstrap_preverification_required_before_spawn"),
    ("admission_provenance_rule",
     "bootstrap_preverification_mapping_is_diagnostic_not_authority"),
    ("authoritative_scientific_execution_boundary",
     "caller_may_construct_the_authoritative_execution"),
    ("authoritative_scientific_execution_boundary",
     "leading_underscore_is_authority_boundary"),
    ("authoritative_scientific_execution_boundary",
     "raw_unverified_spawn_in_production_authority_surface"),
    ("authoritative_scientific_execution_boundary", "api_closure_audit"),
    ("authoritative_scientific_execution_boundary", "direct_worker_launch_census"),
    ("scientific_evidence_authority_rule",
     "caller_built_admission_state_can_mint_evidence"),
    ("controller_result_admission_rule",
     "admission_requires_the_same_authoritative_controller_execution"),
    # -- preserved portions that must stay sensitive
    ("bytecode_execution_binding_rule",
     "cached_bytecode_may_override_certified_source"),
    ("bytecode_execution_binding_rule", "fresh_cache_namespace_per_worker"),
    ("project_source_manifest_binding_rule",
     "runtime_source_manifest_rederivation_permitted"),
    ("third_party_installed_content_attestation_rule",
     "record_declared_installed_file_hashes_must_be_verified"),
    ("compiled_root_binding_witness_rule", "root_may_be_a_cell_variable_of_the_owner"),
    ("compiled_root_binding_witness_rule", "root_cell_prohibition_is_structural"),
    ("store_root_and_direct_use_grammar",
     "root_may_be_a_cell_variable_of_a_conforming_owner"),
    ("direct_body_dependency_rule", "required_direct_bodies"),
    ("direct_body_dependency_rule", "exact_dependency_assertion"),
    ("replay_owner_graph_rule", "contract_version"),
    ("bootstrap_pre_execution_source_binding_rule", "bootstrap_mismatch_spawns_worker"),
    ("bootstrap_source_set", "bootstrap_manifest_digest"),
    ("controller_authority_context_rule", "request_is_authority_root"),
    ("proof_order_and_completeness_definition", "controller_admission_order"),
]


@pytest.mark.parametrize("child,field", MATERIAL_MUTATIONS)
def test_material_mutation_moves_both_child_and_parent_hashes(
    child: str, field: str
) -> None:
    builders = dict(r3._CHILD_ARTIFACTS)
    original = builders[f"{child}.json"]()
    assert field in original, sorted(original)

    def mutated() -> dict:
        payload = {
            name: value
            for name, value in original.items()
            if name != "definition_sha256"
        }
        payload[field] = "MATERIAL_MUTATION_PROBE"
        return r3._definition(payload)

    registry = tuple(
        (name, mutated if name == f"{child}.json" else builder)
        for name, builder in r3._CHILD_ARTIFACTS
    )
    assert mutated()["definition_sha256"] != original["definition_sha256"]
    assert (
        r3.isolated_scientific_worker_v1_r3_definition(registry)["definition_sha256"]
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
            "etf_calendar_isolated_scientific_worker_r3 as r3;"
            "print(r3.isolated_scientific_worker_v1_r3_definition()"
            "['definition_sha256'])",
        ],
        capture_output=True,
        check=True,
        cwd=str(tmp_path),
        env={**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(ROOT)},
    )
    assert completed.stdout.decode().strip() == CANDIDATE_HASH


def test_artifacts_reproduce_from_an_alternate_working_directory(
    tmp_path: Path,
) -> None:
    output = tmp_path / "fresh"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "btc_predictor.research.etf_calendar_isolated_scientific_worker_r3",
            str(output),
        ],
        capture_output=True,
        check=True,
        cwd=str(tmp_path),
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    assert completed.stdout.decode().strip() == CANDIDATE_HASH
    assert r3.restore_artifacts(output) == DECISION
    for filename in sorted(p.name for p in ARTIFACT_DIR.iterdir()):
        assert (output / filename).read_bytes() == (ARTIFACT_DIR / filename).read_bytes()


# ---------------------------------------------------------------------------
# Mechanical API closure — the supported-API census
# ---------------------------------------------------------------------------


def test_the_scientific_api_closure_audit_is_closed() -> None:
    audit = r3.audit_scientific_api_closure()
    assert audit["closed"] is True, audit["findings"]
    assert audit["findings"] == []
    assert audit["module_accessible_authority_bearing_operations"] == 1
    assert audit["authoritative_production_operation"] == (
        "run_isolated_scientific_request"
    )
    assert len(audit["production_launch_sites"]) == 1
    assert audit["production_launch_sites"][0]["scope"] == [
        r3.AUTHORITY_OWNING_FACTORY,
        "_execute_exact_worker",
    ]
    assert len(audit["authoritative_execution_construction_sites"]) == 1
    assert audit["authoritative_execution_construction_sites"][0]["scope"] == [
        r3.AUTHORITY_OWNING_FACTORY,
        "run_isolated_scientific_request",
    ]
    assert len(audit["affirmative_marker_construction_sites"]) == 1
    assert audit["affirmative_marker_undeclared_sites"] == []
    assert audit["authority_owning_factory_is_module_accessible"] is False
    assert audit["forbidden_authority_names_defined"] == []
    assert audit["forbidden_authority_names_reexported"] == []
    assert audit["module_attributes_bound_to_failed_lineage"] == []
    assert all(audit["affirmative_marker_free_modules"].values())


@pytest.mark.parametrize("name", r3.FORBIDDEN_PRODUCTION_AUTHORITY_NAMES)
def test_the_reviewed_authority_escalation_names_do_not_exist(name: str) -> None:
    """The ``PAD4-R2`` composition surface is removed, not merely renamed."""

    assert not hasattr(r3, name), name
    assert hasattr(r2, name), f"{name} must still exist in the preserved R2 module"


def test_no_module_attribute_is_bound_to_a_failed_lineage_authority_name() -> None:
    forbidden = [
        getattr(module, name)
        for module in (r2,)
        for name in r3.FORBIDDEN_PRODUCTION_AUTHORITY_NAMES
        if hasattr(module, name)
    ]
    assert len(forbidden) == len(r3.FORBIDDEN_PRODUCTION_AUTHORITY_NAMES)
    for name in dir(r3):
        value = getattr(r3, name)
        assert not any(value is banned for banned in forbidden), name


def test_the_direct_worker_launch_census_is_closed() -> None:
    census = r3.audit_direct_worker_launch_census()
    assert census["closed"] is True, census["findings"]
    assert census["production_scientific_authority_launch_sites"] == 1
    assert census["certified_worker_source_launch_sites"] == 0
    assert census["undeclared_production_reachable_launch_sites"] == []
    assert census["surveyed_path_count"] == 125
    harness = [
        site
        for site in census["sites"]
        if site["classification"] == "TEST_AND_REVIEW_HARNESS_ONLY"
    ]
    assert [site["scope"] for site in harness] == [["raw_unverified_worker_execution"]]
    assert census["declared_non_worker_launch_sites"] == ["interpreter_base_sys_path"]
    assert [
        site["callable"] for site in census["production_reachable_inherited_launch_sites"]
    ] == ["interpreter_base_sys_path"]


def test_the_raw_harness_is_outside_the_certified_worker_source_universe() -> None:
    paths = {entry.path for entry in MANIFEST}
    assert r3.RAW_REVIEW_HARNESS_RELATIVE_PATH not in paths
    assert r3.CONTROLLER_RELATIVE_PATH not in paths
    assert (ROOT / r3.RAW_REVIEW_HARNESS_RELATIVE_PATH).is_file()


# ---------------------------------------------------------------------------
# The authoritative execution boundary itself
# ---------------------------------------------------------------------------


def test_the_authoritative_execution_cannot_be_constructed_by_a_caller() -> None:
    with pytest.raises(r3.AuthoritativeExecutionConstructionError):
        r3.AuthoritativeScientificExecution()
    with pytest.raises(r3.AuthoritativeExecutionConstructionError):
        r3.AuthoritativeScientificExecution(object(), {"admitted": True})
    with pytest.raises(r3.AuthoritativeExecutionConstructionError):
        r3.AuthoritativeScientificExecution(
            capability=object(),
            material={"admitted": True, "scientific_evidence": {}},
        )


def test_the_authority_owning_factory_cannot_build_a_second_boundary() -> None:
    """A second boundary would be a second authority-bearing operation.

    It would carry its own capability and its own class, so it could mint
    objects that look authoritative but fail ``isinstance`` against the
    canonical type.  The factory is therefore used once and removed from the
    module namespace.
    """

    assert not hasattr(r3, r3.AUTHORITY_OWNING_FACTORY)
    assert r3.AUTHORITY_OWNING_FACTORY not in vars(r3)
    source = (ROOT / r3.CONTROLLER_RELATIVE_PATH).read_text("utf-8")
    assert f"del {r3.AUTHORITY_OWNING_FACTORY}" in source
    boundary_names = sorted(
        name
        for name, value in vars(r3).items()
        if callable(value)
        and getattr(value, "__module__", None) == r3.__name__
        and "boundary" in name
    )
    # every surviving "boundary" name is a frozen child-contract builder: it
    # takes no argument, returns a JSON contract, and can construct nothing
    assert boundary_names == [
        "authoritative_scientific_execution_boundary",
        "trusted_process_and_isolation_boundary",
    ]
    registry = {name for name, _ in r3._CHILD_ARTIFACTS}
    for name in boundary_names:
        assert f"{name}.json" in registry, name
        assert isinstance(getattr(r3, name)(), dict)


def test_no_module_callable_can_produce_an_authoritative_execution() -> None:
    """Census the live module: nothing but the one operation returns the type."""

    import inspect

    producers = []
    for name, value in vars(r3).items():
        if not callable(value) or isinstance(value, type):
            continue
        if getattr(value, "__module__", None) != r3.__name__:
            continue
        annotation = inspect.signature(value).return_annotation
        if "AuthoritativeScientificExecution" in str(annotation):
            producers.append(name)
    assert producers == ["run_isolated_scientific_request"]


def test_a_new_bypassed_execution_carries_no_material_and_refuses() -> None:
    """``__new__`` around ``__init__`` yields an object with nothing in it."""

    forged = r3.AuthoritativeScientificExecution.__new__(
        r3.AuthoritativeScientificExecution
    )
    for attribute in r3.AUTHORITATIVE_EXECUTION_MATERIAL:
        with pytest.raises(r3.AuthoritativeExecutionConstructionError):
            getattr(forged, attribute)


def test_a_subclass_cannot_manufacture_authoritative_material() -> None:
    class Forged(r3.AuthoritativeScientificExecution):
        def __init__(self) -> None:  # deliberately does not call super()
            pass

    forged = Forged()
    for attribute in r3.AUTHORITATIVE_EXECUTION_MATERIAL:
        with pytest.raises(r3.AuthoritativeExecutionConstructionError):
            getattr(forged, attribute)


def test_the_authoritative_execution_exposes_no_material_setter() -> None:
    forged = r3.AuthoritativeScientificExecution.__new__(
        r3.AuthoritativeScientificExecution
    )
    with pytest.raises(AttributeError):
        forged.admitted = True  # type: ignore[misc]
    with pytest.raises(AttributeError):
        forged._fields = {"admitted": True}  # type: ignore[attr-defined]


def test_the_flow_refuses_a_superseded_or_absent_trusted_context() -> None:
    r2_context = r2.candidate_review_authority_context(CANDIDATE_HASH)
    assert not isinstance(r2_context, r3.ScientificWorkerAuthorityContext)
    with pytest.raises(r3.IsolatedScientificWorkerR3Error):
        r3.run_isolated_scientific_request(r2_context, SESSION_REQUEST, LAUNCH)
    with pytest.raises(r3.IsolatedScientificWorkerR3Error):
        r3.run_isolated_scientific_request(None, SESSION_REQUEST, LAUNCH)
    with pytest.raises(r3.IsolatedScientificWorkerR3Error):
        r3.run_isolated_scientific_request(CONTEXT, SESSION_REQUEST, object())


def test_the_flow_refuses_a_drifted_request_without_spawning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = SpawnRecorder(monkeypatch)
    drifted = dict(SESSION_REQUEST)
    drifted["worker_authority_sha256"] = ZERO_HASH
    with pytest.raises(r3.IsolatedScientificWorkerR3Error) as refusal:
        _run(drifted)
    assert "REQUEST_AUTHORITY_MISMATCH" in str(refusal.value)
    assert recorder.worker_spawns == []


# ---------------------------------------------------------------------------
# Mandatory bypass regression 1 — raw unverified spawn -> fabricated response
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "relative,marker_name,expected",
    [
        (ENTRYPOINT, "r3-entrypoint-fabrication", "ENTRYPOINT_BOOTSTRAP_EXECUTED"),
        (REUSED_PROTOCOL, "r3-reused-fabrication", "PROTOCOL_BOOTSTRAP_EXECUTED"),
        (WORKER_PROTOCOL, "r3-worker-fabrication", "PROTOCOL_BOOTSTRAP_EXECUTED"),
    ],
)
def test_raw_unverified_spawn_fabrication_reproduces_as_a_control(
    relative: str, marker_name: str, expected: str, tmp_path: Path
) -> None:
    """CONTROL: unguarded, the drifted bootstrap really executes and fabricates.

    This is the reviewed ``PAD4-R2`` bypass reproduced deliberately in
    test-only code.  It must genuinely succeed at the raw process layer, or the
    closure proof below would be proving nothing.
    """

    marker = tmp_path / marker_name
    root = base.drifted_bootstrap_tree(tmp_path / "tree", relative, marker)
    launch = r3.worker_launch(project_root=root)
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
        (ENTRYPOINT, "r3-entrypoint-closed"),
        (PACKAGE_INITIALIZER, "r3-package-closed"),
        (REUSED_PROTOCOL, "r3-reused-closed"),
        (WORKER_PROTOCOL, "r3-worker-closed"),
    ],
)
def test_raw_fabricated_response_cannot_enter_r3_authority(
    relative: str, marker_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same fabrication, offered to R3: REFUSED, and never even spawned."""

    marker = tmp_path / marker_name
    root = base.drifted_bootstrap_tree(tmp_path / "tree", relative, marker)
    launch = r3.worker_launch(project_root=root)
    request = session_request(launch=launch)
    recorder = SpawnRecorder(monkeypatch)

    with pytest.raises(r3.BootstrapSourcePreVerificationError) as refusal:
        r3.run_isolated_scientific_request(CONTEXT, request, launch)

    assert refusal.value.reason == "WORKER_BOOTSTRAP_SOURCE_SHA_MISMATCH"
    assert refusal.value.detail.startswith(f"{relative}: expected ")
    assert recorder.worker_spawns == []
    assert not marker.exists()

    # and there is no second route: the raw outcome has nowhere to go.
    outcome = raw.raw_unverified_worker_execution(request, launch)
    assert marker.exists() or relative == PACKAGE_INITIALIZER
    assert outcome.scientifically_admissible is False
    assert outcome.scientific_authority == r3.NON_AUTHORITATIVE_SCIENTIFIC_AUTHORITY
    with pytest.raises(r3.AuthoritativeExecutionConstructionError):
        r3.AuthoritativeScientificExecution(outcome, {"admitted": True})
    with pytest.raises(r3.IsolatedScientificWorkerR3Error):
        r3.run_isolated_scientific_request(CONTEXT, request, outcome)


# ---------------------------------------------------------------------------
# Mandatory bypass regression 2 — fabricated PASS preverification mapping
# ---------------------------------------------------------------------------


FABRICATED_PRE_VERIFICATION = {
    "rule": r3.BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING_RULE,
    "verified_by": "ALREADY_TRUSTED_CONTROLLER_CODE",
    "verified_before_subprocess_creation": True,
    "bootstrap_source_count": 4,
    "bootstrap_manifest_digest": (
        "1811e04dac7a033de2c8e6620bf7d5aa227b94eebdf419657ecccf4d3fead411"
    ),
    "checks": list(r3.BOOTSTRAP_PRE_VERIFICATION_CHECKS),
}


def test_a_fabricated_preverification_mapping_is_never_authority(
    tmp_path: Path,
) -> None:
    """A caller-fabricated PASS mapping changes nothing, anywhere."""

    root = base.certified_tree(tmp_path / "tree")
    launch = r3.worker_launch(project_root=root)
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
        r3.NON_AUTHORITATIVE_SCIENTIFIC_AUTHORITY
    )
    assert binding["performed_by_a_trusted_controller"] is False
    assert binding["caller_supplied_mapping_is_diagnostic_not_authority"] is True
    assert "verified_by" not in binding
    assert "ALREADY_TRUSTED_CONTROLLER_CODE" not in json.dumps(diagnostic)

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
    with pytest.raises(r3.AuthoritativeExecutionConstructionError):
        r3.AuthoritativeScientificExecution(
            FABRICATED_PRE_VERIFICATION, {"admitted": True}
        )
    assert r3.admission_provenance_rule()[
        "caller_fabricated_preverification_mapping_is_authority"
    ] is False


# ---------------------------------------------------------------------------
# Mandatory bypass regression 3 — hand-built worker outcome, no controller run
# ---------------------------------------------------------------------------


def test_a_hand_built_outcome_with_every_field_correct_is_not_admitted(
    tmp_path: Path,
) -> None:
    """The strongest form of the reviewed reproducer #3.

    The outcome is not merely well formed — it is a *genuine* successful worker
    execution against the clean certified tree: exit 0, not timed out, correct
    request digest, a valid canonical success response, every request-visible
    authority field correct and a correct result digest.  The only thing it
    lacks is having been produced by the closed authoritative controller
    operation.  The reviewed ``PAD4-R2`` surface admits it; R3 has no route.
    """

    root = base.certified_tree(tmp_path / "tree")
    launch = r3.worker_launch(project_root=root)
    request = session_request(launch=launch)
    outcome = raw.raw_unverified_worker_execution(request, launch)

    parsed = json.loads(outcome.stdout.decode())
    assert outcome.exit_status == 0 and outcome.timed_out is False
    assert parsed["status"] == protocol.SUCCESS
    assert parsed["result_digest"] == protocol.result_digest(parsed["result"])
    assert parsed["request_digest"] == outcome.request_digest
    assert r3.verify_response_against_authority_context(CONTEXT, parsed) == ()
    assert r3.verify_request_against_authority_context(CONTEXT, request) == ()

    # CONTROL: the reviewed PAD4-R2 surface admits exactly this, from a
    # hand-built outcome, with no subprocess created by the admission call and
    # with bootstrap_pre_verification left None.
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

    # R3: there is nothing to hand it to.
    assert not hasattr(r3, "admit_worker_result")
    assert not hasattr(r3, "WorkerProcessOutcome")
    with pytest.raises(r3.AuthoritativeExecutionConstructionError):
        r3.AuthoritativeScientificExecution(hand_built, {"admitted": True})
    with pytest.raises(r3.IsolatedScientificWorkerR3Error):
        r3.run_isolated_scientific_request(CONTEXT, request, hand_built)
    assert raw.raw_execution_diagnostic(outcome)["admitted"] is False


# ---------------------------------------------------------------------------
# Mandatory bypass regression 4 — hand-built admission state -> evidence
# ---------------------------------------------------------------------------


def test_caller_built_admission_state_cannot_mint_affirmative_evidence(
    tmp_path: Path,
) -> None:
    """No project-owned R3 callable turns caller state into affirmative evidence."""

    root = base.certified_tree(tmp_path / "tree")
    launch = r3.worker_launch(project_root=root)
    request = session_request(launch=launch)
    outcome = raw.raw_unverified_worker_execution(request, launch)
    parsed = json.loads(outcome.stdout.decode())

    fabricated_state = {
        "admitted": True,
        "failure_reason": None,
        "response": parsed,
        "result": parsed["result"],
        "request_digest": outcome.request_digest,
        "scientific_evidence": {
            "scientific_authority": r3.AUTHORITATIVE_SCIENTIFIC_AUTHORITY,
            "admitted": True,
        },
    }
    with pytest.raises(r3.AuthoritativeExecutionConstructionError):
        r3.AuthoritativeScientificExecution(object(), fabricated_state)

    # no module-accessible evidence constructor exists to hand it to
    assert not hasattr(r3, "scientific_response_evidence")
    assert not hasattr(r3, "AdmissionOutcome")
    evidence_callables = [
        name
        for name in dir(r3)
        if callable(getattr(r3, name)) and "evidence" in name and "rule" not in name
    ]
    assert evidence_callables == []
    assert r3.scientific_evidence_authority_rule()[
        "caller_built_admission_state_can_mint_evidence"
    ] is False


def test_superseded_lineage_evidence_is_not_r3_authority(tmp_path: Path) -> None:
    """Laundering the R3 hash through the failed ``PAD4-R2`` surface fails.

    A caller may still call the preserved, failed, non-certified ``PAD4-R2``
    evidence builder.  What it produces can never carry the affirmative R3
    authority marker, so it cannot be mistaken for an R3 scientific execution.
    """

    root = base.certified_tree(tmp_path / "tree")
    launch = r3.worker_launch(project_root=root)
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
    assert r3.AUTHORITATIVE_SCIENTIFIC_AUTHORITY not in json.dumps(evidence)
    assert evidence["admitted"] is False


# ---------------------------------------------------------------------------
# Mandatory worker-fabrication regression
# ---------------------------------------------------------------------------


def test_a_worker_that_copies_every_request_authority_field_cannot_be_admitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The worker can copy everything it can see, and it is still not enough.

    The drifted entrypoint forgery copies every request-visible authority field
    into a canonical success response and computes a correct result digest, so
    it produces exactly the payload admission validates.  The controller-side
    condition it cannot manufacture is that *this* process was created by the
    closed authoritative operation after that operation pre-verified the
    bootstrap source — which is not data, and not observable from inside.
    """

    marker = tmp_path / "worker-copies-everything"
    root = base.drifted_bootstrap_tree(tmp_path / "tree", ENTRYPOINT, marker)
    launch = r3.worker_launch(project_root=root)
    request = session_request(launch=launch)

    outcome = raw.raw_unverified_worker_execution(request, launch)
    fabricated = json.loads(outcome.stdout.decode())
    assert marker.exists()
    assert r3.verify_response_against_authority_context(CONTEXT, fabricated) == ()
    assert fabricated["result_digest"] == protocol.result_digest(fabricated["result"])
    assert fabricated["bootstrap_defence_in_depth_verification"] == "PASS"
    assert fabricated["result"] == FABRICATED_RESULT

    recorder = SpawnRecorder(monkeypatch)
    with pytest.raises(r3.BootstrapSourcePreVerificationError):
        r3.run_isolated_scientific_request(CONTEXT, request, launch)
    assert recorder.worker_spawns == []
    assert raw.raw_execution_diagnostic(outcome)["admitted"] is False
    assert r3.admission_provenance_rule()[
        "worker_copied_request_authority_is_sufficient_for_admission"
    ] is False


# ---------------------------------------------------------------------------
# Positive authoritative regression and evidence truth
# ---------------------------------------------------------------------------


def test_the_clean_authoritative_path_is_admitted(tmp_path: Path) -> None:
    root = base.certified_tree(tmp_path / "tree")
    launch = r3.worker_launch(project_root=root)
    execution = _run(session_request(launch=launch), launch=launch)

    assert isinstance(execution, r3.AuthoritativeScientificExecution)
    assert execution.admitted is True, execution.failure_reason
    assert execution.failure_reason is None
    assert execution.result["state"] == HONEST_SESSION_STATE
    assert execution.response["bootstrap_defence_in_depth_verification"] == "PASS"
    assert execution.response["worker_bootstrap_manifest_digest"] == (
        CONTEXT.worker_bootstrap_manifest_digest
    )

    evidence = execution.scientific_evidence
    assert evidence["scientific_authority"] == r3.AUTHORITATIVE_SCIENTIFIC_AUTHORITY
    assert evidence["admitted"] is True
    assert evidence["authoritative_execution_is_closed_end_to_end"] is True
    assert evidence["proof_architecture_program_ticket"] == "POSTP1-001V2A-PAD4-R3"
    binding = evidence["bootstrap_pre_execution_source_binding"]
    assert binding["verified_by"] == "ALREADY_TRUSTED_CONTROLLER_CODE"
    assert binding["verified_before_subprocess_creation"] is True
    assert binding["performed_by_this_authoritative_execution"] is True
    assert binding["bootstrap_source_count"] == 4
    assert binding["bootstrap_manifest_digest"] == (
        "1811e04dac7a033de2c8e6620bf7d5aa227b94eebdf419657ecccf4d3fead411"
    )
    assert evidence["trusted_authority_context"]["authority_context_version"] == (
        "ETF_CALENDAR_SCIENTIFIC_WORKER_AUTHORITY_CONTEXT_V1_R3"
    )


def test_the_repository_tree_admits_an_honest_result() -> None:
    execution = _run(SESSION_REQUEST)
    assert execution.admitted is True, execution.failure_reason
    assert execution.result["state"] == HONEST_SESSION_STATE
    assert execution.scientific_evidence["admitted"] is True


def test_the_flow_operation_matches_the_parent_computation() -> None:
    execution = _run(flow_request())
    assert execution.admitted is True, execution.failure_reason
    assert execution.result["feature"]["feature_id"] == (
        _flow.FIVE_DAY_ETF_FLOW_FEATURE_ID
    )
    assert execution.result["feature"]["window_days"] == (
        _flow.FIVE_DAY_ETF_FLOW_WINDOW_DAYS
    )


def test_the_returned_evidence_is_a_copy_that_cannot_be_mutated_in_place() -> None:
    execution = _run(SESSION_REQUEST)
    first = execution.scientific_evidence
    first["admitted"] = False
    first["scientific_authority"] = "TAMPERED"
    second = execution.scientific_evidence
    assert second["admitted"] is True
    assert second["scientific_authority"] == r3.AUTHORITATIVE_SCIENTIFIC_AUTHORITY


def test_every_non_authoritative_execution_tells_the_truth(tmp_path: Path) -> None:
    """Evidence truth: a raw execution may never claim what did not happen."""

    root = base.certified_tree(tmp_path / "tree")
    launch = r3.worker_launch(project_root=root)
    request = session_request(launch=launch)
    for mapping in (None, FABRICATED_PRE_VERIFICATION):
        outcome = raw.raw_unverified_worker_execution(
            request, launch, bootstrap_pre_verification=mapping
        )
        diagnostic = raw.raw_execution_diagnostic(outcome)
        rendered = json.dumps(diagnostic)
        assert diagnostic["admitted"] is False
        assert diagnostic["scientific_authority"] == (
            r3.NON_AUTHORITATIVE_SCIENTIFIC_AUTHORITY
        )
        assert diagnostic["authoritative_execution_is_closed_end_to_end"] is False
        assert "ALREADY_TRUSTED_CONTROLLER_CODE" not in rendered
        assert r3.AUTHORITATIVE_SCIENTIFIC_AUTHORITY not in rendered
        assert diagnostic["result"] is None
        assert diagnostic["result_digest"] is None


def test_the_raw_diagnostic_refuses_authoritative_material(tmp_path: Path) -> None:
    execution = _run(SESSION_REQUEST)
    with pytest.raises(TypeError):
        raw.raw_execution_diagnostic(execution)
    with pytest.raises(TypeError):
        raw.raw_execution_diagnostic({"admitted": True})


def test_a_worker_failure_is_never_admitted_and_evidence_says_so() -> None:
    """Preserved failure admission, now reported through the closed flow."""

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
    namespace = r3.allocate_worker_pycache_namespace(tmp_path / "cache")
    argv = LAUNCH.argv_for(namespace)
    assert argv[1:4] == ("-I", "-S", "-B")
    assert argv[4] == "-X"
    assert argv[5] == f"pycache_prefix={namespace}"
    assert LAUNCH.mechanism == r3.EXEC_LAUNCH
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
    launch = r3.worker_launch(project_root=root)
    execution = _run(flow_request(launch=launch), launch=launch)
    assert execution.admitted is True, execution.failure_reason
    assert execution.result["feature"]["feature_id"] == (
        _flow.FIVE_DAY_ETF_FLOW_FEATURE_ID
    )
    assert execution.result["feature"]["feature_id"] != "FORGED_BYTECODE_ID"


def test_forged_bootstrap_pyc_is_not_executed(tmp_path: Path) -> None:
    root = base.certified_tree(tmp_path / "tree")
    marker = tmp_path / "r3-forged-bootstrap-pyc"
    base.forge_pyc(
        root / WORKER_PROTOCOL,
        root / "etf_calendar_worker/__pycache__/protocol_r2.cpython-312.pyc",
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('X')\n",
    )
    launch = r3.worker_launch(project_root=root)
    execution = _run(session_request(launch=launch), launch=launch)
    assert execution.admitted is True, execution.failure_reason
    assert not marker.exists()


def test_a_pre_populated_cache_namespace_refuses(tmp_path: Path) -> None:
    poisoned = tmp_path / "poisoned"
    poisoned.mkdir()
    (poisoned / "stale.pyc").write_bytes(b"\x00")
    with pytest.raises(r1.IsolatedScientificWorkerR1Error, match="is not fresh"):
        r3.create_fresh_pycache_namespace(poisoned)
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
    launch = r3.worker_launch(project_root=root)
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
    launch = r3.worker_launch(project_root=root)
    request = session_request(launch=launch)
    assert request["project_source_manifest_digest"] == (
        CONTEXT.project_source_manifest_digest
    )
    assert r3.verify_request_against_authority_context(CONTEXT, request) == ()
    assert _worker_refusal(request, launch=launch)["failure_reason"] == (
        "CERTIFIED_SOURCE_SHA_MISMATCH"
    )


def test_runtime_never_rederives_the_source_manifest() -> None:
    import inspect

    parameters = set(inspect.signature(r3.build_scientific_request).parameters)
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
# Preserved Repair C — trusted controller authority context
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("wrong", [ZERO_HASH, DEADBEEF_HASH])
def test_a_wrong_self_consistent_decision_hash_is_not_admitted(wrong: str) -> None:
    context = r3.candidate_review_authority_context(wrong)
    request = session_request(context=context)
    assert request["worker_authority_sha256"] == wrong
    execution = _run(request, context=context)
    assert execution.admitted is True, execution.failure_reason
    # the worker echoes it consistently, so the trusted context is what refuses
    assert r3.verify_response_against_authority_context(CONTEXT, execution.response) == (
        ("worker_authority_sha256",)
    )
    with pytest.raises(r3.IsolatedScientificWorkerR3Error):
        _run(request)


def test_the_three_way_authority_agreement_is_enforced() -> None:
    execution = _run(SESSION_REQUEST)
    assert r3.verify_request_against_authority_context(CONTEXT, SESSION_REQUEST) == ()
    assert r3.verify_response_against_authority_context(CONTEXT, execution.response) == ()
    assert execution.response["request_digest"] == execution.request_digest
    assert execution.admitted is True


def test_the_authority_context_cannot_be_built_from_a_request_or_response() -> None:
    with pytest.raises(TypeError):
        r3.ScientificWorkerAuthorityContext(**SESSION_REQUEST)
    with pytest.raises(r2.IsolatedScientificWorkerR2Error):
        r3.candidate_review_authority_context("not-a-sha")


def test_a_context_bound_to_a_different_worker_protocol_ticket_refuses() -> None:
    with pytest.raises(r2.IsolatedScientificWorkerR2Error):
        r3.ScientificWorkerAuthorityContext(
            origin=CONTEXT.origin,
            proof_architecture_version=CONTEXT.proof_architecture_version,
            proof_architecture_ticket="POSTP1-001V2A-PAD4-R3",
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


def test_the_candidate_context_hash_boundary_is_reproduced_and_not_reopened() -> None:
    """The review confirmed this is NOT a defect; behaviour is unchanged."""

    arbitrary = r3.candidate_review_authority_context("a" * 64)
    assert arbitrary.proof_architecture_sha256 == "a" * 64
    rule = r3.controller_authority_context_rule()
    assert rule["candidate_review_authority_context_reopened"] is False
    assert rule["candidate_review_authority_context_review_finding"] == (
        "CONFIRMED_NOT_A_DEFECT_BY_POSTP1_002V2A_PAD4_R2"
    )
    source = (ROOT / r3.CONTROLLER_RELATIVE_PATH).read_text("utf-8")
    assert "os.environ" not in source
    assert "getenv" not in source


def test_the_production_authority_context_is_still_blocked() -> None:
    with pytest.raises(
        r2.IsolatedScientificWorkerR2Error, match=r3.PRODUCTION_CONTEXT_NOT_YET_BOUND
    ):
        r3.production_authority_context_from_calendar_authority({})
    assert DECISION["authorization"]["postp1_001v2a_i2_may_begin"] is False


# ---------------------------------------------------------------------------
# Preserved Repair D — third-party semantic and installed-content authority
# ---------------------------------------------------------------------------


def test_the_reviewed_third_party_registry_is_unchanged() -> None:
    rows = {
        entry.distribution: entry.version for entry in r3.frozen_third_party_authority()
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
        for entry in r3.frozen_third_party_authority()
        if entry.distribution == "alembic"
    )
    observation = r3.observe_installed_distributions((authority,))[0]
    target = Path(observation.location) / "alembic/__init__.py"
    record = Path(observation.record_path)
    marker = tmp_path / "r3-tampered-dependency-executed"
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

    monkeypatch.setattr(builtins, "R3_PARENT_BUILTIN_PROBE", "PRESENT", raising=False)
    assert getattr(builtins, "R3_PARENT_BUILTIN_PROBE") == "PRESENT"
    execution = _run(SESSION_REQUEST)
    assert execution.admitted is True, execution.failure_reason
    assert "R3_PARENT_BUILTIN_PROBE" not in json.dumps(execution.scientific_evidence)


# ---------------------------------------------------------------------------
# Preserved static calendar authority and production status
# ---------------------------------------------------------------------------


def test_preserved_compiled_witness_grammar_and_owner_graph() -> None:
    witness_rule = r3.compiled_root_binding_witness_rule()
    grammar = r3.store_root_and_direct_use_grammar()
    graph = r3.replay_owner_graph_rule()
    bodies = r3.direct_body_dependency_rule()
    assert witness_rule == r2.compiled_root_binding_witness_rule()
    assert grammar == r2.store_root_and_direct_use_grammar()
    assert graph == r2.replay_owner_graph_rule()
    assert bodies == r2.direct_body_dependency_rule()
    assert len(r3.FROZEN_REPLAY_OWNERS) == 11
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
    assert production == r2.isolated_scientific_worker_v1_r2_definition()[
        "current_production_expected_result"
    ]
    assert DECISION["central_decisions"]["calendar_production_code_changed"] is False
    assert DECISION["central_decisions"]["calendar_science_changed"] is False


def test_the_pre_i2_fixture_role_is_unchanged_and_i2_still_owns_the_manifests() -> None:
    assert DECISION["pre_i2_project_source_module_count"] == 116
    assert DECISION["pre_i2_project_source_manifest_digest"] == (
        "674b006ae66b8aace3458cb870f898ecad33e1f23833436954d36749b3aadbb8"
    )
    assert DECISION["pre_i2_project_source_manifest_role"] == r3.PRE_I2_FIXTURE_ROLE
    assert DECISION["central_decisions"]["pre_i2_116_module_manifest_role"] == (
        "CONFORMANCE_FIXTURE_NOT_FINAL_PRODUCTION_AUTHORITY"
    )
    assert DECISION["central_decisions"][
        "final_i2_source_manifest_must_be_calendar_parent_bound"
    ] is True


def test_the_bootstrap_set_and_candidate_universe_are_mechanically_derived() -> None:
    completeness = r3.verify_frozen_bootstrap_set_is_complete()
    assert completeness["bootstrap_source_count"] == 4
    assert completeness["bootstrap_manifest_digest"] == (
        "1811e04dac7a033de2c8e6620bf7d5aa227b94eebdf419657ecccf4d3fead411"
    )
    assert completeness["bootstrap_source_set"] == list(BOOTSTRAP_SET[:0]) + sorted(
        BOOTSTRAP_SET
    )
    assert DECISION["worker_bootstrap_manifest_digest"] == (
        completeness["bootstrap_manifest_digest"]
    )
    assert DECISION["candidate_worker_source_module_count"] == 120
    assert DECISION["central_decisions"][
        "bootstrap_source_set_changed_by_this_decision"
    ] is False
    audit = r3.audit_authoritative_worker_source()
    assert audit["closed"] is True, audit["findings"]


def test_the_frozen_proof_order_is_the_closed_authoritative_order() -> None:
    order = r3.proof_order_and_completeness_definition()
    assert order["controller_or_review_order"][0].endswith(
        "RECEIVE_THE_TRUSTED_CONTROLLER_AUTHORITY_CONTEXT"
    )
    assert order["controller_or_review_order"][2].endswith(
        "PREVERIFY_THE_COMPLETE_BOOTSTRAP_SOURCE_SET"
    )
    assert order["controller_admission_order"][-1].endswith(
        "RETURN_THE_FINAL_ADMITTED_RESULT_AND_EVIDENCE"
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


def test_no_executable_ipc_and_no_worker_visible_secret() -> None:
    source = (ROOT / r3.CONTROLLER_RELATIVE_PATH).read_text("utf-8")
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
    boundary = r3.authoritative_scientific_execution_boundary()
    assert boundary["worker_computable_mac_key_introduced"] is False
    assert boundary["cryptographic_ceremony_introduced"] is False
    assert boundary["authority_mechanism"] == (
        "CLOSED_CONTROL_FLOW_AND_CAPABILITY_OWNERSHIP"
    )


def test_safety_posture_is_unchanged() -> None:
    lineage = r3.science_lineage_and_safety()
    assert lineage["preserved_science"] == {
        "calendar_normalization_early_closes_pit_common_session_rules": "UNCHANGED",
        "etf_formulas_and_revision_semantics": "UNCHANGED",
        "etf_calendar_production_code_changed_by_this_decision": False,
        "parser_science": "UNCHANGED",
        "source_urls_profiles_tls_redirects": "UNCHANGED",
        "stage_b_metrics_risk_stops_thresholds": "UNCHANGED",
    }
    assert DECISION["authorization"]["prospective_collection_may_begin"] is False
    assert DECISION["authorization"]["calendar_implementation_may_begin"] is False


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


def test_the_lazy_result_refusal_is_reused_unchanged() -> None:
    from etf_calendar_worker import protocol_r1 as owner

    assert r3.worker_io_and_capability_boundary() == (
        r2.worker_io_and_capability_boundary()
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


# ---------------------------------------------------------------------------
# Preserved failure admission, driven through the closed flow
# ---------------------------------------------------------------------------


def _completed(stdout: bytes, returncode: int = 0):
    """A crafted worker process result, injected at the process boundary.

    This patches ``subprocess.run`` — the operating-system boundary — rather
    than any project API, because R3 deliberately offers no API that accepts a
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
        r3.subprocess, "run", lambda *a, **k: _completed(stdout, returncode)
    )
    execution = _run(SESSION_REQUEST)
    assert execution.admitted is False
    assert execution.failure_reason.startswith(expected), execution.failure_reason
    assert execution.result is None
    evidence = execution.scientific_evidence
    assert evidence["admitted"] is False
    assert evidence["result_digest"] is None


def test_oversized_worker_output_is_never_admitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oversized = b"x" * (protocol.MAX_RESPONSE_BYTES + 1) + b"\n"
    monkeypatch.setattr(r3.subprocess, "run", lambda *a, **k: _completed(oversized))
    execution = _run(SESSION_REQUEST)
    assert execution.admitted is False
    assert execution.failure_reason == "WORKER_OUTPUT_EXCEEDS_THE_FROZEN_LIMIT"


def test_a_tampered_result_digest_is_never_admitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An honest response whose result is swapped afterwards must refuse."""

    honest = _run(SESSION_REQUEST)
    assert honest.admitted is True, honest.failure_reason
    payload = dict(honest.response)
    payload["result"] = dict(payload["result"])
    payload["result"]["state"] = "TAMPERED_AFTER_THE_FACT"
    stdout = protocol.canonical_json_bytes(payload) + b"\n"

    monkeypatch.setattr(r3.subprocess, "run", lambda *a, **k: _completed(stdout))
    execution = _run(SESSION_REQUEST)
    assert execution.admitted is False
    assert execution.failure_reason == "WORKER_RESULT_DIGEST_MISMATCH"
    assert execution.result is None
    assert execution.scientific_evidence["admitted"] is False
