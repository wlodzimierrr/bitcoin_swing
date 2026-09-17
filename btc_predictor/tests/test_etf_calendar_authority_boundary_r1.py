"""POSTP1-001V2A-AD1-R1 corrected architecture-decision tests."""

from __future__ import annotations

import copy
import json
import os
import subprocess
from pathlib import Path

import pytest

from btc_predictor.research import etf_calendar_authority_boundary_r1 as boundary


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / boundary.OUTPUT_NAMESPACE
CALENDAR_SOURCE = boundary.CALENDAR_SOURCE.read_text(encoding="utf-8")


COMPLIANT_SOURCE = """
def assert_trusted_persistence_dependency():
    pass

class CalendarEvidenceStore:
    def __init__(self):
        self._records = {}
        self._envelopes = {}
    def put(self, record):
        assert_trusted_persistence_dependency()
        self._records['x'] = record
    def get(self, key):
        assert_trusted_persistence_dependency()
        return self._records[key]
    def records(self):
        assert_trusted_persistence_dependency()
        return tuple(self._records.values())
    def envelopes(self):
        assert_trusted_persistence_dependency()
        return tuple(self._envelopes.values())

def collect_official_calendar():
    assert_trusted_persistence_dependency()

def compliant_owner(store: CalendarEvidenceStore):
    return store.records()
"""


def test_corrected_parent_answers_central_questions_and_binds_every_child() -> None:
    decision = boundary.authority_boundary_definition()
    assert decision["decision_version"] == "ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1"
    assert decision["program_ticket"] == "POSTP1-001V2A-AD1-R1"
    assert decision["final_classification"] == (
        "ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1_READY_FOR_REPEAT_XHIGH_REVIEW"
    )
    central = decision["central_decisions"]
    assert central["trusted_production_python_process"] is True
    assert central["arbitrary_caller_private_state_mutation_in_scope"] is False
    assert central["project_owned_private_state_access_in_scope"] is True
    assert central["project_owned_private_state_access_permitted"] is False
    assert central["process_isolation_required_if_hostile_same_process_mutation_enters_scope"]
    children = boundary._children()
    assert decision["material_child_count"] == len(boundary._CHILD_ARTIFACTS) == 9
    assert decision["child_definition_sha256"] == {
        name: payload["definition_sha256"] for name, payload in children.items()
    }
    for payload in children.values():
        boundary._verify_definition_digest(payload)


def test_private_state_registry_and_future_extension_rule_are_parent_bound() -> None:
    child = boundary.private_state_boundary()
    assert child["authoritative_internal_state"] == ["_records", "_envelopes"]
    assert child["allowed_implementation_boundary"] == "CalendarEvidenceStore_METHOD_BODIES"
    assert child["direct_reads_outside_implementation"] == "FORBIDDEN"
    assert child["direct_writes_outside_implementation"] == "FORBIDDEN"
    assert "PARENT_HASH_CHANGE" in child["future_extension_rule"]
    assert child["underscore_naming_alone_is_the_boundary"] is False


def test_exact_replay_owner_registry_matches_mechanical_current_source_census() -> None:
    discovered = boundary.verify_replay_owner_census(CALENDAR_SOURCE)
    assert discovered == boundary.FROZEN_REPLAY_OWNERS
    assert "SCIENTIFIC_CALENDAR_AND_REPLAY_OWNERS_CONSUMING_CalendarEvidenceStore" not in (
        boundary.replay_owner_registry()["owners"]
    )
    boundary.audit_private_state_access(CALENDAR_SOURCE)
    boundary.audit_replay_owner_api_routes(CALENDAR_SOURCE)


@pytest.mark.parametrize(
    "owner",
    [
        "def bad_replay_owner(store: CalendarEvidenceStore):\n    return tuple(store._records.values())\n",
        "def bad_envelope_owner(store: CalendarEvidenceStore):\n    return tuple(store._envelopes.values())\n",
        "def bad_getattr_owner(store: CalendarEvidenceStore):\n    return getattr(store, '_records')\n",
        "def bad_setattr_owner(store: CalendarEvidenceStore):\n    setattr(store, '_envelopes', {})\n",
        "def bad_dict_owner(store: CalendarEvidenceStore):\n    return store.__dict__['_records']\n",
        "def bad_vars_owner(store: CalendarEvidenceStore):\n    return vars(store)['_envelopes']\n",
        "def bad_dict_get_owner(store: CalendarEvidenceStore):\n    return store.__dict__.get('_records')\n",
        "def bad_vars_get_owner(store: CalendarEvidenceStore):\n    return vars(store).get('_envelopes')\n",
    ],
)
def test_repository_owned_private_state_bypass_forms_refuse(owner: str) -> None:
    with pytest.raises(boundary.AuthorityBoundaryError, match="reserved authoritative"):
        boundary.audit_private_state_access(CALENDAR_SOURCE + "\n" + owner)


def test_unenumerated_new_owner_refuses_even_when_it_uses_guarded_api() -> None:
    mutated = CALENDAR_SOURCE + """

def new_replay_owner(store: CalendarEvidenceStore):
    return store.records()
"""
    with pytest.raises(boundary.AuthorityBoundaryError, match="census mismatch"):
        boundary.verify_replay_owner_census(mutated)


def test_store_alias_is_discovered_and_store_method_may_access_only_own_state() -> None:
    aliased = CALENDAR_SOURCE + """

def aliased_replay_owner(store: CalendarEvidenceStore):
    alias = store
    return alias.records()
"""
    assert "aliased_replay_owner" in boundary.discover_replay_owners(aliased)

    cross_store = COMPLIANT_SOURCE.replace(
        "    def get(self, key):\n",
        "    def bad_cross_store(self, other):\n"
        "        return other._records\n"
        "    def get(self, key):\n",
    )
    with pytest.raises(boundary.AuthorityBoundaryError, match="reserved authoritative"):
        boundary.audit_private_state_access(cross_store)


def test_stale_registry_refuses() -> None:
    stale = (*boundary.FROZEN_REPLAY_OWNERS, "owner_that_no_longer_exists")
    with pytest.raises(boundary.AuthorityBoundaryError, match="census mismatch"):
        boundary.verify_replay_owner_census(CALENDAR_SOURCE, stale)


def test_compliant_enumerated_owner_and_complete_static_fixture_pass() -> None:
    boundary.audit_static_production_surface(COMPLIANT_SOURCE, ("compliant_owner",))


def test_static_audit_requires_structural_direct_calls_and_rejects_runtime_wrapping() -> None:
    text_only = COMPLIANT_SOURCE.replace(
        "        assert_trusted_persistence_dependency()\n        self._records['x'] = record",
        "        'assert_trusted_persistence_dependency()'\n        self._records['x'] = record",
    )
    with pytest.raises(boundary.AuthorityBoundaryError, match="ast.Call missing"):
        boundary.audit_static_production_surface(text_only, ("compliant_owner",))

    wrapped = COMPLIANT_SOURCE + "\nCalendarEvidenceStore.get = guard(CalendarEvidenceStore.get)\n"
    with pytest.raises(boundary.AuthorityBoundaryError, match="rebinding forbidden"):
        boundary.audit_static_production_surface(wrapped, ("compliant_owner",))


def test_transitive_owner_must_terminate_in_documented_store_api() -> None:
    no_route = COMPLIANT_SOURCE.replace(
        "    return store.records()", "    return tuple()"
    )
    with pytest.raises(boundary.AuthorityBoundaryError, match="no route"):
        boundary.audit_replay_owner_api_routes(no_route, ("compliant_owner",))


def test_failed_lineage_science_and_authorization_remain_bounded() -> None:
    safety = boundary.drift_science_and_safety()
    assert safety["failed_architecture"]["definition_sha256"] == (
        "0c237c1b217b1fd406ec3967309774293c01d3e27574b9f4a7d1b9a0e887b55d"
    )
    assert safety["failed_architecture"]["failed_independent_review"] is True
    assert safety["certified_dependency"]["definition_sha256"] == (
        "02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772"
    )
    assert safety["certified_dependency"]["changed"] is False
    assert set(safety["preserved_science"].values()) == {"UNCHANGED"}
    assert safety["safety"]["prospective_observations"] == 0
    assert safety["safety"]["collection_authorized"] is False
    assert boundary.authority_boundary_definition()["authorization"] == {
        "independent_architecture_xhigh_rereview_may_begin": True,
        "calendar_implementation_may_begin": False,
        "postp1_001v2r1_may_begin": False,
        "prospective_collection_may_begin": False,
    }


def test_artifacts_reproduce_tampering_refuses_and_child_order_is_invariant(
    tmp_path: Path,
) -> None:
    persisted = boundary.restore_artifacts(ARTIFACT_DIR)
    assert persisted == boundary.authority_boundary_definition()

    normal = tmp_path / "normal"
    reversed_dir = tmp_path / "reversed"
    first = boundary.write_artifacts(normal)
    second = boundary.write_artifacts(reversed_dir, reversed(boundary._CHILD_ARTIFACTS))
    assert first == second
    assert {
        path.name: path.read_bytes() for path in normal.iterdir()
    } == {
        path.name: path.read_bytes() for path in reversed_dir.iterdir()
    }

    child_path = normal / "private_state_boundary.json"
    child = json.loads(child_path.read_text(encoding="ascii"))
    child["authoritative_internal_state"].append("_new_authoritative_state")
    child_path.write_text(json.dumps(child, indent=2, sort_keys=True) + "\n", encoding="ascii")
    with pytest.raises(boundary.AuthorityBoundaryError, match="does not reproduce"):
        boundary.restore_artifacts(normal)

    parent = copy.deepcopy(persisted)
    parent["authorization"]["prospective_collection_may_begin"] = True
    with pytest.raises(boundary.AuthorityBoundaryError, match="does not reproduce"):
        boundary.verify_authority_boundary_definition(parent)


@pytest.mark.parametrize("seed", ["0", "1", "8675309"])
def test_fresh_process_hashseed_and_alternate_cwd_reproduce(
    tmp_path: Path, seed: str
) -> None:
    output = tmp_path / f"seed-{seed}"
    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = seed
    environment["PYTHONPATH"] = str(ROOT)
    completed = subprocess.run(
        [
            str(ROOT / ".venv312/bin/python"),
            "-m",
            "btc_predictor.research.etf_calendar_authority_boundary_r1",
            str(output),
        ],
        cwd=tmp_path,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == boundary.authority_boundary_definition()[
        "definition_sha256"
    ]
    assert boundary.restore_artifacts(output) == boundary.authority_boundary_definition()
