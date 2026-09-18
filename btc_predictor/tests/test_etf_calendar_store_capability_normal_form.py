"""POSTP1-001V2A-PAD1 closed store-capability architecture tests."""

from __future__ import annotations

import copy
import json
import os
import subprocess
from pathlib import Path

import pytest

from btc_predictor.research import etf_calendar_store_capability_normal_form as normal


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / normal.OUTPUT_NAMESPACE


def _audit(source: str, owners: tuple[str, ...] = ("owner",)) -> tuple[normal.StoreUse, ...]:
    return normal.audit_store_capability_normal_form(source, owners)


def test_parent_freezes_closed_grammar_and_review_only_authorization() -> None:
    decision = normal.store_capability_normal_form_definition()
    assert decision["program_ticket"] == "POSTP1-001V2A-PAD1"
    assert decision["proof_strategy"] == "CLOSED_SUPPORTED_STORE_CAPABILITY_GRAMMAR"
    assert decision["status"] == normal.STATUS
    assert decision["final_classification"] == (
        "ETF_CALENDAR_STORE_CAPABILITY_NORMAL_FORM_V1_READY_FOR_XHIGH_REVIEW"
    )
    assert decision["failed_parent_sha256"] == (
        "dc36ffe228b7a3bc6d9145042b4e301c8624c99a79d71a88b46fc268f1372c3e"
    )
    central = decision["central_decisions"]
    assert central["closed_supported_scientific_store_use_grammar"] is True
    assert central["models_arbitrary_python_dataflow"] is False
    assert central["every_certified_allowed_store_use_modeled"] is True
    assert central["every_non_certified_store_use_rejected"] is True
    assert central["bare_bound_method_extraction_permitted"] is False
    assert central["unsupported_use_masked_by_valid_route_permitted"] is False
    assert central["future_new_syntax_automatically_supported"] is False
    proof = normal.proof_order_and_completeness_definition()
    assert proof["decision_certifies_current_production_conformance"] is False
    assert "GENERATOR_CAPTURE" in proof["known_future_implementation_delta"]
    assert decision["authorization"] == {
        "independent_proof_architecture_xhigh_review_may_begin": True,
        "calendar_implementation_may_begin": False,
        "postp1_001v2r1_may_begin": False,
        "prospective_collection_may_begin": False,
    }
    children = normal._children()
    assert decision["material_child_count"] == len(normal._CHILD_ARTIFACTS) == 9
    assert decision["child_definition_sha256"] == {
        name: child["definition_sha256"] for name, child in children.items()
    }


def test_current_production_owner_census_remains_exactly_eleven() -> None:
    source = normal.CALENDAR_SOURCE.read_text(encoding="utf-8")
    assert normal.verify_replay_owner_census(source) == normal.FROZEN_REPLAY_OWNERS


@pytest.mark.parametrize("api", ["put", "get", "records", "envelopes"])
def test_direct_documented_store_calls_are_allowed(api: str) -> None:
    argument = "'x'" if api == "get" else "object()" if api == "put" else ""
    uses = _audit(
        f"def owner(store: CalendarEvidenceStore):\n    return store.{api}({argument})\n"
    )
    assert any(
        use.kind == "PERMITTED_DIRECT_STORE_API_CALL" and use.detail == api
        for use in uses
    )


def test_direct_undocumented_store_call_is_forbidden() -> None:
    source = "def owner(store: CalendarEvidenceStore):\n    return store.bad_method()\n"
    with pytest.raises(normal.NormalFormError, match="STORE_ATTRIBUTE_EXTRACTION"):
        _audit(source)


@pytest.mark.parametrize("attribute", ["records", "get", "put", "envelopes", "anything"])
def test_all_bare_store_attribute_extractions_are_forbidden(attribute: str) -> None:
    source = (
        "def owner(store: CalendarEvidenceStore):\n"
        f"    fn = store.{attribute}\n"
        "    return fn()\n"
    )
    with pytest.raises(normal.NormalFormError, match="STORE_ATTRIBUTE_EXTRACTION"):
        _audit(source)


def test_valid_terminal_cannot_mask_undocumented_bound_method_extraction() -> None:
    source = """
def owner(store: CalendarEvidenceStore):
    good = store.records()
    bad_fn = store.some_undocumented_method
    return good, bad_fn()
"""
    with pytest.raises(normal.NormalFormError, match="STORE_ATTRIBUTE_EXTRACTION"):
        _audit(source)


def test_valid_terminal_cannot_mask_documented_bound_method_extraction() -> None:
    source = """
def owner(store: CalendarEvidenceStore):
    good = store.get('x')
    fn = store.records
    return good, fn()
"""
    with pytest.raises(normal.NormalFormError, match="STORE_ATTRIBUTE_EXTRACTION"):
        _audit(source)


def test_transparent_local_alias_is_allowed() -> None:
    uses = _audit(
        "def owner(store: CalendarEvidenceStore):\n"
        "    alias = store\n"
        "    return alias.records()\n"
    )
    assert {use.kind for use in uses} == {
        "PERMITTED_TRANSPARENT_ALIAS",
        "PERMITTED_DIRECT_STORE_API_CALL",
    }


@pytest.mark.parametrize(
    "statement",
    ["obj.alias = store", "container[0] = store"],
)
def test_object_and_subscript_storage_are_forbidden(statement: str) -> None:
    source = f"def owner(store: CalendarEvidenceStore):\n    {statement}\n"
    with pytest.raises(normal.NormalFormError, match="OBJECT_OR_SUBSCRIPT_STORAGE"):
        _audit(source)


def test_direct_enumerated_owner_forward_is_allowed() -> None:
    source = """
def owner(store: CalendarEvidenceStore):
    return enumerated_owner(store)
def enumerated_owner(store: CalendarEvidenceStore):
    return store.records()
"""
    uses = _audit(source, ("owner", "enumerated_owner"))
    assert any(
        use.kind == "PERMITTED_ENUMERATED_OWNER_FORWARD"
        and use.detail == "enumerated_owner"
        for use in uses
    )


def test_unknown_store_forward_is_forbidden() -> None:
    source = """
def arbitrary_helper(value):
    return value
def owner(store: CalendarEvidenceStore):
    return arbitrary_helper(store)
"""
    with pytest.raises(normal.NormalFormError, match="UNKNOWN_FORWARD"):
        _audit(source)


@pytest.mark.parametrize("statement", ["return store", "yield store"])
def test_direct_return_or_yield_is_forbidden(statement: str) -> None:
    source = f"def owner(store: CalendarEvidenceStore):\n    {statement}\n"
    with pytest.raises(normal.NormalFormError, match="RETURN_OR_YIELD"):
        _audit(source)


@pytest.mark.parametrize(
    "statement",
    [
        "return [store]",
        "mapping = {'s': store}",
        "pair = (store, object())",
        "values = {store}",
    ],
)
def test_new_container_packing_is_forbidden(statement: str) -> None:
    source = f"def owner(store: CalendarEvidenceStore):\n    {statement}\n"
    with pytest.raises(normal.NormalFormError, match="CONTAINER_ESCAPE"):
        _audit(source)


def test_nested_function_capture_is_forbidden() -> None:
    source = """
def owner(store: CalendarEvidenceStore):
    def inner():
        return store.records()
    return inner()
"""
    with pytest.raises(normal.NormalFormError, match="NESTED_SCOPE_CAPTURE"):
        _audit(source)


def test_lambda_capture_is_forbidden() -> None:
    source = """
def owner(store: CalendarEvidenceStore):
    fn = lambda: store.records()
    return fn()
"""
    with pytest.raises(normal.NormalFormError, match="NESTED_SCOPE_CAPTURE"):
        _audit(source)


def test_generator_closure_capture_is_forbidden() -> None:
    source = """
def owner(store: CalendarEvidenceStore):
    return tuple(store.get(key) for key in ('a', 'b'))
"""
    with pytest.raises(normal.NormalFormError, match="NESTED_SCOPE_CAPTURE"):
        _audit(source)


def test_nested_annotated_store_owner_is_forbidden_even_without_capture() -> None:
    source = """
def owner(store: CalendarEvidenceStore):
    def inner(other_store: CalendarEvidenceStore):
        return other_store.records()
    return store.records()
"""
    with pytest.raises(normal.NormalFormError, match="NESTED_SCOPE_CAPTURE"):
        _audit(source)


@pytest.mark.parametrize(
    "expression",
    [
        "getattr(store, 'records')",
        "setattr(store, 'x', 1)",
        "vars(store)",
        "store.__dict__",
    ],
)
def test_dynamic_store_access_is_forbidden(expression: str) -> None:
    source = f"def owner(store: CalendarEvidenceStore):\n    return {expression}\n"
    with pytest.raises(normal.NormalFormError, match="DYNAMIC_ACCESS"):
        _audit(source)


@pytest.mark.parametrize(
    "source",
    [
        "def owner(*stores: CalendarEvidenceStore):\n"
        "    return stores[0].records()\n",
        "def owner(**stores: CalendarEvidenceStore):\n"
        "    return stores['primary'].records()\n",
        "def owner(*stores: CalendarEvidenceStore):\n"
        "    alias = stores[0]\n"
        "    return alias.records()\n",
        "def owner(*stores: CalendarEvidenceStore):\n"
        "    for store in stores:\n"
        "        store.records()\n",
        "def owner(**stores: CalendarEvidenceStore):\n"
        "    for store in stores.values():\n"
        "        store.records()\n",
    ],
)
def test_frozen_variadic_derivation_and_direct_use_are_allowed(source: str) -> None:
    uses = _audit(source)
    assert any(use.kind == "PERMITTED_VARIADIC_DERIVATION" for use in uses)
    assert any(use.kind == "PERMITTED_DIRECT_STORE_API_CALL" for use in uses)


@pytest.mark.parametrize(
    ("source", "owners"),
    [
        (
            "def owner(*stores: CalendarEvidenceStore):\n"
            "    return enumerated_owner(stores[0])\n"
            "def enumerated_owner(store: CalendarEvidenceStore):\n"
            "    return store.records()\n",
            ("owner", "enumerated_owner"),
        ),
        (
            "def owner(*stores: CalendarEvidenceStore):\n"
            "    return enumerated_owner(*stores)\n"
            "def enumerated_owner(store: CalendarEvidenceStore):\n"
            "    return store.records()\n",
            ("owner", "enumerated_owner"),
        ),
        (
            "def owner(**stores: CalendarEvidenceStore):\n"
            "    return enumerated_owner(**stores)\n"
            "def enumerated_owner(store: CalendarEvidenceStore):\n"
            "    return store.records()\n",
            ("owner", "enumerated_owner"),
        ),
    ],
)
def test_bounded_variadic_owner_forwarding_is_allowed(
    source: str, owners: tuple[str, ...]
) -> None:
    uses = _audit(source, owners)
    assert any(use.kind == "PERMITTED_ENUMERATED_OWNER_FORWARD" for use in uses)


def test_variadic_bound_method_extraction_is_forbidden() -> None:
    source = "def owner(*stores: CalendarEvidenceStore):\n    fn = stores[0].records\n"
    with pytest.raises(normal.NormalFormError, match="STORE_ATTRIBUTE_EXTRACTION"):
        _audit(source)


def test_variadic_container_escape_is_forbidden() -> None:
    source = "def owner(*stores: CalendarEvidenceStore):\n    return [stores[0]]\n"
    with pytest.raises(normal.NormalFormError, match="CONTAINER_ESCAPE"):
        _audit(source)


def test_usage_sites_receive_exactly_one_frozen_classification() -> None:
    source = """
def owner(store: CalendarEvidenceStore):
    alias = store
    return alias.records()
"""
    uses = normal.classify_store_uses(source, ("owner",))
    assert len(uses) == 2
    assert all(use.kind in normal.UseKind.__args__ for use in uses)
    assert len({(use.owner, use.lineno, use.col_offset) for use in uses}) == len(uses)


def test_normal_form_precedes_acyclic_terminating_owner_graph() -> None:
    source = """
def owner_a(store: CalendarEvidenceStore):
    return owner_b(store)
def owner_b(store: CalendarEvidenceStore):
    return store.records()
"""
    edges = normal.audit_replay_owner_graph(source, ("owner_a", "owner_b"))
    assert {edge.kind for edge in edges} == {
        "DOCUMENTED_STORE_API_TERMINAL",
        "ENUMERATED_REPLAY_OWNER_EDGE",
    }


def test_owner_cycle_is_forbidden_after_normal_form_passes() -> None:
    source = """
def owner_a(store: CalendarEvidenceStore):
    return owner_b(store)
def owner_b(store: CalendarEvidenceStore):
    return owner_a(store)
"""
    with pytest.raises(normal.NormalFormError, match="cycle forbidden"):
        normal.audit_replay_owner_graph(source, ("owner_a", "owner_b"))


@pytest.mark.parametrize(
    ("builder", "field"),
    [
        ("store_bearing_value_grammar", "supported_roots_and_derivations"),
        ("permitted_store_use_normal_form", "permitted_categories"),
        ("forbidden_capability_escape_rules", "forbidden_categories"),
        ("proof_order_and_completeness_definition", "proof_order"),
        ("proof_order_and_completeness_definition", "models_all_possible_python_programs"),
    ],
)
def test_material_mutations_move_child_and_parent_hash(builder: str, field: str) -> None:
    original_child = getattr(normal, builder)()
    payload = copy.deepcopy(original_child)
    payload.pop("definition_sha256")
    if isinstance(payload[field], list):
        payload[field].append("MUTATED")
    else:
        payload[field] = not payload[field]
    mutated_child = normal._definition(payload)
    assert mutated_child["definition_sha256"] != original_child["definition_sha256"]

    original_parent = normal.store_capability_normal_form_definition()
    parent_payload = copy.deepcopy(original_parent)
    parent_payload.pop("definition_sha256")
    parent_payload["child_definition_sha256"][builder] = mutated_child[
        "definition_sha256"
    ]
    assert normal._definition(parent_payload)["definition_sha256"] != original_parent[
        "definition_sha256"
    ]


def test_lineage_science_and_safety_are_preserved() -> None:
    safety = normal.science_lineage_and_safety()
    assert {row["definition_sha256"] for row in safety["failed_architecture_lineage"]} == set(
        normal.FAILED_ARCHITECTURE_LINEAGE
    )
    assert all(
        row["failed"] and not row["certified"] and not row["used"]
        for row in safety["failed_architecture_lineage"]
    )
    assert safety["certified_dependency"]["changed"] is False
    assert set(safety["preserved_science"].values()) == {"UNCHANGED"}
    assert safety["safety"]["prospective_observations"] == 0
    assert safety["safety"]["collection_authorized"] is False
    escapes = normal.forbidden_capability_escape_rules()
    assert escapes["implementation_private_authoritative_state"] == [
        "_records",
        "_envelopes",
    ]
    assert escapes[
        "repository_owned_access_outside_CalendarEvidenceStore_permitted"
    ] is False


def test_artifacts_reproduce_child_order_is_invariant_and_tampering_refuses(
    tmp_path: Path,
) -> None:
    assert normal.restore_artifacts(ARTIFACT_DIR) == normal.store_capability_normal_form_definition()
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first = normal.write_artifacts(first_dir)
    second = normal.write_artifacts(second_dir, tuple(reversed(normal._CHILD_ARTIFACTS)))
    assert first == second
    assert {path.name: path.read_bytes() for path in first_dir.iterdir()} == {
        path.name: path.read_bytes() for path in second_dir.iterdir()
    }
    child_path = first_dir / "forbidden_capability_escape_rules.json"
    child = json.loads(child_path.read_text(encoding="ascii"))
    child["forbidden_categories"].pop()
    child_path.write_text(json.dumps(child, indent=2, sort_keys=True) + "\n", encoding="ascii")
    with pytest.raises(normal.NormalFormError, match="does not reproduce"):
        normal.restore_artifacts(first_dir)


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
            "btc_predictor.research.etf_calendar_store_capability_normal_form",
            str(output),
        ],
        cwd=tmp_path,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == normal.store_capability_normal_form_definition()[
        "definition_sha256"
    ]
    assert normal.restore_artifacts(output) == normal.store_capability_normal_form_definition()
