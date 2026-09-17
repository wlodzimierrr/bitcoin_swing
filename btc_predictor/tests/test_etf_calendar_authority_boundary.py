"""POSTP1-001V2A-AD1 frozen architecture-decision tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from btc_predictor.research import etf_calendar_authority_boundary as boundary


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / boundary.OUTPUT_NAMESPACE


def test_frozen_decision_answers_central_questions() -> None:
    decision = boundary.authority_boundary_definition()
    assert decision["decision_version"] == "ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1"
    assert decision["program_ticket"] == "POSTP1-001V2A-AD1"
    assert decision["final_classification"] == (
        "ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1_READY_FOR_XHIGH_REVIEW"
    )
    assert decision["central_decisions"] == {
        "trusted_production_python_process": True,
        "arbitrary_in_process_monkeypatch_resistance_required": False,
        "project_owned_production_bypasses_permitted": False,
        "direct_entrypoint_body_enforcement_required": True,
        "dynamic_wrapper_installation_permitted": False,
        "functools_wraps_authority_guards_permitted": False,
        "exposed_unguarded_production_owners_permitted": False,
        "process_isolation_required_if_arbitrary_same_process_mutation_enters_scope": True,
    }


def test_parent_mechanically_binds_every_child() -> None:
    decision, children = boundary.authority_boundary_definition(), boundary._children()
    assert decision["material_child_count"] == len(boundary._CHILD_ARTIFACTS) == 7
    assert decision["child_definition_sha256"] == {
        name: payload["definition_sha256"] for name, payload in children.items()
    }
    for payload in children.values():
        boundary._verify_definition_digest(payload)
    boundary.verify_authority_boundary_definition(decision)


def test_runtime_mutation_scope_and_process_isolation_escalation_are_explicit() -> None:
    threat = boundary.runtime_mutation_threat_model()
    assert len(threat["mutations"]) == 6
    assert set(threat["mutations"].values()) == {
        "OUTSIDE_SCIENTIFIC_AUTHORITY_THREAT_MODEL"
    }
    assert threat["escalation"]["classification"] == (
        "ETF_CALENDAR_AUTHORITY_REQUIRES_PROCESS_ISOLATION_ARCHITECTURE"
    )
    assert threat["escalation"]["wrapper_metaclass_or_hash_workaround_permitted"] is False


def test_direct_bodies_replay_collection_and_static_audit_are_frozen() -> None:
    direct = boundary.direct_body_enforcement()
    audit = boundary.static_surface_audit()
    bypass = boundary.project_owned_bypass_prohibition()
    required = {
        "CalendarEvidenceStore.put",
        "CalendarEvidenceStore.get",
        "CalendarEvidenceStore.records",
        "CalendarEvidenceStore.envelopes",
        "collect_official_calendar",
    }
    assert set(direct["required_direct_bodies"]) == required
    assert direct["startup_self_check_required"] is True
    assert direct["startup_self_check_replaces_per_entrypoint_checks"] is False
    assert audit["mechanical_ast_audit_required"] is True
    assert bypass["project_owned_production_bypasses_permitted"] is False
    assert "FUNCTOOLS_WRAPS_AUTHORITY_GUARDS" in bypass["forbidden"]


def test_drift_refusal_failed_lineage_preserved_science_and_safety_are_frozen() -> None:
    contract = boundary.drift_science_and_safety()
    assert all(contract["hard_refusal"].values())
    assert contract["certified_dependency"]["definition_sha256"] == (
        "02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772"
    )
    assert contract["certified_dependency"]["changed"] is False
    assert set(contract["preserved_science"].values()) == {"UNCHANGED"}
    assert [row["definition_sha256"] for row in contract["failed_calendar_lineage"]] == list(
        boundary.FAILED_CALENDAR_LINEAGE
    )
    assert all(
        not row["authoritative"] and not row["certified"]
        and row["prospective_observations"] == 0 and row["superseded_before_use"]
        for row in contract["failed_calendar_lineage"]
    )
    assert contract["safety"]["prospective_observations"] == 0
    assert contract["safety"]["collection_authorized"] is False


def test_decision_authorizes_review_only() -> None:
    authorization = boundary.authority_boundary_definition()["authorization"]
    assert authorization == {
        "independent_architecture_xhigh_review_may_begin": True,
        "another_calendar_implementation_may_begin": False,
        "calendar_implementation_requires_architecture_review_pass": True,
        "postp1_001v2r1_may_begin": False,
        "prospective_collection_may_begin": False,
    }


def test_persisted_artifacts_reproduce_and_tampering_refuses(tmp_path: Path) -> None:
    persisted = boundary.restore_artifacts(ARTIFACT_DIR)
    assert persisted == boundary.authority_boundary_definition()

    copied = tmp_path / "decision"
    boundary.write_artifacts(copied)
    path = copied / "trusted_computing_boundary.json"
    child = json.loads(path.read_text(encoding="ascii"))
    child["arbitrary_same_process_mutation_resistance_required"] = True
    path.write_text(json.dumps(child, indent=2, sort_keys=True) + "\n", encoding="ascii")
    with pytest.raises(boundary.AuthorityBoundaryError, match="does not reproduce"):
        boundary.restore_artifacts(copied)

    parent = copy.deepcopy(persisted)
    parent["authorization"]["prospective_collection_may_begin"] = True
    with pytest.raises(boundary.AuthorityBoundaryError, match="does not reproduce"):
        boundary.verify_authority_boundary_definition(parent)
