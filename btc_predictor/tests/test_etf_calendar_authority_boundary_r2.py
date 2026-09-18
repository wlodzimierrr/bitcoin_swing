"""POSTP1-001V2A-AD1-R2 universal replay-route architecture tests."""

from __future__ import annotations

import copy
import json
import os
import subprocess
from pathlib import Path

import pytest

from btc_predictor.research import etf_calendar_authority_boundary_r2 as boundary


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


def test_parent_binds_corrected_universal_model_and_preserves_boundary() -> None:
    decision = boundary.authority_boundary_definition()
    assert decision["program_ticket"] == "POSTP1-001V2A-AD1-R2"
    assert decision["status"] == (
        "FROZEN_PRE_DATA_AWAITING_INDEPENDENT_XHIGH_ARCHITECTURE_REVIEW"
    )
    assert decision["final_classification"] == (
        "ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1_READY_FOR_FINAL_XHIGH_ARCHITECTURE_REVIEW"
    )
    central = decision["central_decisions"]
    assert central["all_store_dependent_edges_classified"] is True
    assert central["owner_route_compliance_is_universal"] is True
    assert central["owner_cycles_permitted"] is False
    assert central["annotated_variadic_store_consumers_discovered"] is True
    assert central["trusted_production_python_process"] is True
    assert central["arbitrary_caller_private_state_mutation_in_scope"] is False
    children = boundary._children()
    assert decision["material_child_count"] == len(boundary._CHILD_ARTIFACTS) == 10
    assert decision["child_definition_sha256"] == {
        name: child["definition_sha256"] for name, child in children.items()
    }


def test_exact_production_owner_census_and_universal_routes_pass() -> None:
    assert boundary.verify_replay_owner_census(CALENDAR_SOURCE) == (
        boundary.FROZEN_REPLAY_OWNERS
    )
    edges = boundary.audit_replay_owner_api_routes(CALENDAR_SOURCE)
    assert edges
    assert {edge.kind for edge in edges} <= {
        "DOCUMENTED_STORE_API_TERMINAL",
        "ENUMERATED_REPLAY_OWNER_EDGE",
    }
    assert tuple(sorted(edges)) == edges


def test_documented_and_undocumented_mixed_routes_refuse() -> None:
    source = """
def owner(store: CalendarEvidenceStore):
    good = store.records()
    bad = store.some_undocumented_method()
    return good, bad
"""
    with pytest.raises(boundary.AuthorityBoundaryError, match="UNDOCUMENTED"):
        boundary.audit_replay_owner_api_routes(source, ("owner",))


def test_branch_with_undocumented_route_refuses_conservatively() -> None:
    source = """
def owner(store: CalendarEvidenceStore, condition):
    if condition:
        return store.records()
    return store.some_undocumented_method()
"""
    with pytest.raises(boundary.AuthorityBoundaryError, match="UNDOCUMENTED"):
        boundary.audit_replay_owner_api_routes(source, ("owner",))


def test_multiple_documented_routes_pass() -> None:
    source = """
def owner(store: CalendarEvidenceStore):
    a = store.get('x')
    b = store.records()
    return a, b
"""
    edges = boundary.audit_replay_owner_api_routes(source, ("owner",))
    assert [edge.target for edge in edges] == ["get", "records"]


@pytest.mark.parametrize(
    ("source", "owners"),
    [
        (
            """
def owner_a(store: CalendarEvidenceStore):
    return owner_b(store)
def owner_b(store: CalendarEvidenceStore):
    return owner_a(store)
""",
            ("owner_a", "owner_b"),
        ),
        (
            """
def owner_a(store: CalendarEvidenceStore):
    return owner_b(store)
def owner_b(store: CalendarEvidenceStore):
    owner_a(store)
    return store.records()
""",
            ("owner_a", "owner_b"),
        ),
        (
            """
def owner(store: CalendarEvidenceStore):
    owner(store)
    return store.records()
""",
            ("owner",),
        ),
    ],
)
def test_all_owner_cycles_refuse_even_with_documented_exit(
    source: str, owners: tuple[str, ...]
) -> None:
    with pytest.raises(boundary.AuthorityBoundaryError, match="cycle forbidden"):
        boundary.audit_replay_owner_api_routes(source, owners)


def test_acyclic_owner_chain_terminating_at_store_api_passes() -> None:
    source = """
def owner_a(store: CalendarEvidenceStore):
    return owner_b(store)
def owner_b(store: CalendarEvidenceStore):
    return store.records()
"""
    edges = boundary.audit_replay_owner_api_routes(source, ("owner_a", "owner_b"))
    assert {edge.kind for edge in edges} == {
        "ENUMERATED_REPLAY_OWNER_EDGE",
        "DOCUMENTED_STORE_API_TERMINAL",
    }


def test_store_forward_to_unenumerated_function_refuses() -> None:
    source = """
def unknown_helper(value):
    return value
def owner(store: CalendarEvidenceStore):
    return unknown_helper(store)
"""
    with pytest.raises(boundary.AuthorityBoundaryError, match="UNENUMERATED"):
        boundary.audit_replay_owner_api_routes(source, ("owner",))


@pytest.mark.parametrize(
    ("function", "expected_target"),
    [
        (
            "def owner(*stores: CalendarEvidenceStore):\n"
            "    return stores[0].records()\n",
            "records",
        ),
        (
            "def owner(**stores: CalendarEvidenceStore):\n"
            "    return stores['primary'].records()\n",
            "records",
        ),
        (
            "def owner(*stores: CalendarEvidenceStore):\n"
            "    primary = stores[0]\n"
            "    return primary.records()\n",
            "records",
        ),
        (
            "def owner(**stores: CalendarEvidenceStore):\n"
            "    primary = stores['primary']\n"
            "    return primary.records()\n",
            "records",
        ),
        (
            "def owner(*stores: CalendarEvidenceStore):\n"
            "    for store in stores:\n"
            "        store.records()\n",
            "records",
        ),
        (
            "def owner(**stores: CalendarEvidenceStore):\n"
            "    for store in stores.values():\n"
            "        store.records()\n",
            "records",
        ),
    ],
)
def test_variadic_index_alias_and_iteration_are_discovered_and_audited(
    function: str, expected_target: str
) -> None:
    assert boundary.discover_replay_owners(function) == ("owner",)
    edges = boundary.audit_replay_owner_api_routes(function, ("owner",))
    assert any(edge.target == expected_target for edge in edges)


@pytest.mark.parametrize(
    "source",
    [
        """
def owner(*stores: CalendarEvidenceStore):
    return another_owner(stores[0])
def another_owner(store: CalendarEvidenceStore):
    return store.records()
""",
        """
def owner(*stores: CalendarEvidenceStore):
    return another_owner(*stores)
def another_owner(store: CalendarEvidenceStore):
    return store.records()
""",
        """
def owner(**stores: CalendarEvidenceStore):
    return another_owner(**stores)
def another_owner(store: CalendarEvidenceStore):
    return store.records()
""",
    ],
)
def test_variadic_forwarding_is_an_owner_edge(source: str) -> None:
    edges = boundary.audit_replay_owner_api_routes(
        source, ("owner", "another_owner")
    )
    assert any(
        edge.owner == "owner"
        and edge.kind == "ENUMERATED_REPLAY_OWNER_EDGE"
        and edge.target == "another_owner"
        for edge in edges
    )


def test_variadic_undocumented_method_refuses() -> None:
    source = """
def bad(*stores: CalendarEvidenceStore):
    stores[0].undocumented_method()
"""
    with pytest.raises(boundary.AuthorityBoundaryError, match="UNDOCUMENTED"):
        boundary.audit_replay_owner_api_routes(source, ("bad",))


@pytest.mark.parametrize(
    "function",
    [
        "def new_owner(*stores: CalendarEvidenceStore):\n"
        "    return stores[0].records()\n",
        "def new_owner(**stores: CalendarEvidenceStore):\n"
        "    return stores['primary'].records()\n",
    ],
)
def test_unregistered_variadic_owner_fails_production_census(function: str) -> None:
    with pytest.raises(boundary.AuthorityBoundaryError, match="census mismatch"):
        boundary.verify_replay_owner_census(CALENDAR_SOURCE + "\n" + function)


@pytest.mark.parametrize(
    "owner",
    [
        "def bad(store: CalendarEvidenceStore):\n    return store._records\n",
        "def bad(store: CalendarEvidenceStore):\n    return store._envelopes\n",
        "def bad(store: CalendarEvidenceStore):\n    return getattr(store, '_records')\n",
        "def bad(store: CalendarEvidenceStore):\n    setattr(store, '_envelopes', {})\n",
        "def bad(store: CalendarEvidenceStore):\n    return store.__dict__['_records']\n",
        "def bad(store: CalendarEvidenceStore):\n    return vars(store).get('_envelopes')\n",
    ],
)
def test_preserved_private_state_bypass_regressions_refuse(owner: str) -> None:
    with pytest.raises(boundary.AuthorityBoundaryError, match="reserved authoritative"):
        boundary.audit_private_state_access(CALENDAR_SOURCE + "\n" + owner)


def test_complete_static_fixture_preserves_direct_body_requirements() -> None:
    boundary.audit_static_production_surface(COMPLIANT_SOURCE, ("compliant_owner",))
    missing = COMPLIANT_SOURCE.replace(
        "        assert_trusted_persistence_dependency()\n        self._records['x'] = record",
        "        self._records['x'] = record",
    )
    with pytest.raises(boundary.AuthorityBoundaryError, match="ast.Call missing"):
        boundary.audit_static_production_surface(missing, ("compliant_owner",))


@pytest.mark.parametrize(
    ("builder", "field"),
    [
        ("transitive_replay_rule", "owner_compliance_quantifier"),
        ("transitive_replay_rule", "owner_graph_must_be_acyclic"),
        ("replay_route_model", "undocumented_store_methods_permitted"),
        ("replay_owner_registry", "discovery_rules"),
        ("replay_route_model", "store_bearing_expressions"),
        ("transitive_replay_rule", "rules"),
    ],
)
def test_material_route_mutations_move_owning_child_and_parent_hash(
    builder: str, field: str
) -> None:
    original_child = getattr(boundary, builder)()
    mutated_payload = copy.deepcopy(original_child)
    mutated_payload.pop("definition_sha256")
    value = mutated_payload[field]
    if isinstance(value, list):
        value.append("MUTATED")
    elif isinstance(value, bool):
        mutated_payload[field] = not value
    else:
        mutated_payload[field] = "MUTATED"
    mutated_child = boundary._definition(mutated_payload)
    assert mutated_child["definition_sha256"] != original_child["definition_sha256"]

    original_parent = boundary.authority_boundary_definition()
    parent_payload = copy.deepcopy(original_parent)
    parent_payload.pop("definition_sha256")
    parent_payload["child_definition_sha256"][builder] = mutated_child[
        "definition_sha256"
    ]
    mutated_parent = boundary._definition(parent_payload)
    assert mutated_parent["definition_sha256"] != original_parent["definition_sha256"]


def test_failed_lineages_science_and_authorization_remain_bounded() -> None:
    safety = boundary.drift_science_and_safety()
    hashes = {row["definition_sha256"] for row in safety["failed_architectures"]}
    assert hashes == {
        boundary.FAILED_ARCHITECTURE_SHA256,
        boundary.FAILED_R1_ARCHITECTURE_SHA256,
    }
    assert all(
        row["failed"] and not row["certified"] and not row["used"]
        for row in safety["failed_architectures"]
    )
    assert safety["certified_dependency"]["changed"] is False
    assert set(safety["preserved_science"].values()) == {"UNCHANGED"}
    assert safety["safety"]["prospective_observations"] == 0
    assert safety["safety"]["collection_authorized"] is False
    assert boundary.authority_boundary_definition()["authorization"] == {
        "independent_architecture_xhigh_final_review_may_begin": True,
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
    second = boundary.write_artifacts(
        reversed_dir, tuple(reversed(boundary._CHILD_ARTIFACTS))
    )
    assert first == second
    assert {path.name: path.read_bytes() for path in normal.iterdir()} == {
        path.name: path.read_bytes() for path in reversed_dir.iterdir()
    }
    child_path = normal / "replay_route_model.json"
    child = json.loads(child_path.read_text(encoding="ascii"))
    child["edge_kinds"].pop()
    child_path.write_text(
        json.dumps(child, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    with pytest.raises(boundary.AuthorityBoundaryError, match="does not reproduce"):
        boundary.restore_artifacts(normal)


@pytest.mark.parametrize("seed", ["0", "1", "8675309"])
def test_fresh_process_hashseed_alternate_cwd_and_output_reproduce(
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
            "btc_predictor.research.etf_calendar_authority_boundary_r2",
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
