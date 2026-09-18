"""POSTP1-001V2A-PAD1-R1 narrow corrected proof-architecture tests."""

from __future__ import annotations

import copy
import json
import os
import subprocess
from pathlib import Path

import pytest

from btc_predictor.research import etf_calendar_store_capability_normal_form_r1 as normal


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / normal.OUTPUT_NAMESPACE


def _audit(source: str, owners: tuple[str, ...] = ("owner",)) -> tuple[normal.StoreUse, ...]:
    return normal.audit_store_capability_normal_form(source, owners)


def test_parent_freezes_narrow_grammar_and_review_only_authorization() -> None:
    decision = normal.store_capability_normal_form_definition()
    assert decision["program_ticket"] == "POSTP1-001V2A-PAD1-R1"
    assert decision["proof_strategy"] == "DIRECT_IMMUTABLE_STORE_PARAMETER_NORMAL_FORM"
    assert decision["status"] == normal.STATUS
    assert decision["final_classification"] == (
        "ETF_CALENDAR_STORE_CAPABILITY_NORMAL_FORM_V1_READY_FOR_FINAL_XHIGH_REVIEW"
    )
    assert decision["failed_parent_sha256"] == normal.FAILED_PARENT_SHA256
    central = decision["central_decisions"]
    assert central["ordinary_explicitly_annotated_immutable_roots_only"] is True
    assert central["store_aliases_permitted"] is False
    assert central["store_variadics_permitted"] is False
    assert central["starred_store_forwarding_permitted"] is False
    assert central["root_rebinding_or_unbinding_permitted"] is False
    assert central["models_arbitrary_python_dataflow"] is False
    assert decision["authorization"] == {
        "independent_final_proof_architecture_xhigh_review_may_begin": True,
        "calendar_implementation_may_begin": False,
        "postp1_001v2r1_may_begin": False,
        "prospective_collection_may_begin": False,
    }
    assert decision["material_child_count"] == len(normal._CHILD_ARTIFACTS) == 10


def test_current_production_owner_census_is_exactly_eleven_ordinary_roots() -> None:
    source = normal.CALENDAR_SOURCE.read_text(encoding="utf-8")
    assert normal.verify_replay_owner_census(source) == normal.FROZEN_REPLAY_OWNERS
    assert len(normal.FROZEN_REPLAY_OWNERS) == 11


@pytest.mark.parametrize("api", ["put", "get", "records", "envelopes"])
def test_direct_documented_store_calls_pass(api: str) -> None:
    argument = "'x'" if api == "get" else "object()" if api == "put" else ""
    uses = _audit(f"def owner(store: CalendarEvidenceStore):\n    return store.{api}({argument})\n")
    assert [(use.kind, use.detail) for use in uses] == [
        ("PERMITTED_DIRECT_STORE_API_CALL", api)
    ]


@pytest.mark.parametrize(
    "signature",
    [
        "store: CalendarEvidenceStore, /",
        "store: CalendarEvidenceStore",
        "*, store: CalendarEvidenceStore",
    ],
)
def test_all_ordinary_annotated_parameter_kinds_pass(signature: str) -> None:
    _audit(f"def owner({signature}):\n    return store.records()\n")


def test_name_alone_does_not_create_store_authority() -> None:
    assert _audit("def owner(store):\n    return store.records()\n") == ()


@pytest.mark.parametrize(
    "call",
    [
        "enumerated_owner(store)",
        "enumerated_owner(object(), store)",
        "enumerated_owner(store=store)",
        "enumerated_owner(evidence_store=store)",
    ],
)
def test_direct_enumerated_owner_forwarding_passes(call: str) -> None:
    source = (
        "def owner(store: CalendarEvidenceStore):\n"
        f"    return {call}\n"
        "def enumerated_owner(store: CalendarEvidenceStore):\n"
        "    return store.records()\n"
    )
    uses = _audit(source, ("owner", "enumerated_owner"))
    assert any(use.kind == "PERMITTED_ENUMERATED_OWNER_FORWARD" for use in uses)


@pytest.mark.parametrize("call", ["enumerated_owner(*store)", "enumerated_owner(**store)"])
def test_starred_store_forwarding_refuses(call: str) -> None:
    source = (
        "def owner(store: CalendarEvidenceStore):\n"
        f"    return {call}\n"
        "def enumerated_owner(store: CalendarEvidenceStore):\n"
        "    return store.records()\n"
    )
    with pytest.raises(normal.NormalFormError, match="FORBIDDEN_STARRED_FORWARD"):
        _audit(source, ("owner", "enumerated_owner"))


@pytest.mark.parametrize(
    "source",
    [
        "def owner(*stores: CalendarEvidenceStore):\n    return None\n",
        "def owner(**stores: CalendarEvidenceStore):\n    return None\n",
    ],
)
def test_annotated_store_variadic_owner_definitions_refuse(source: str) -> None:
    with pytest.raises(normal.NormalFormError, match="annotated_store_variadic_parameter"):
        _audit(source)


@pytest.mark.parametrize(
    "body",
    [
        "alias = store\n    return alias.records()",
        "alias: CalendarEvidenceStore = store\n    return frozen_owner(alias)",
        "alias.records()\n    alias = store",
    ],
)
def test_all_store_aliases_refuse_without_propagation(body: str) -> None:
    with pytest.raises(normal.NormalFormError, match="FORBIDDEN_OTHER_STORE_USE"):
        _audit(f"def owner(store: CalendarEvidenceStore):\n    {body}\n")


@pytest.mark.parametrize(
    ("body", "detail"),
    [
        ("store = other", "Assign"),
        ("store: object = other", "AnnAssign"),
        ("store += other", "AugAssign"),
        ("(store := other)", "NamedExpr"),
        ("for store in rows:\n        pass", "For"),
        ("async for store in rows:\n        pass", "AsyncFor"),
        ("with context() as store:\n        pass", "With"),
        ("async with context() as store:\n        pass", "AsyncWith"),
        ("try:\n        pass\n    except Error as store:\n        pass", "ExceptHandler"),
        ("match value:\n        case store:\n            pass", "MatchCapture"),
        ("import thing as store", "Import"),
        ("from thing import value as store", "ImportFrom"),
        ("def store():\n        pass", "FunctionDef"),
        ("async def store():\n        pass", "AsyncFunctionDef"),
        ("class store:\n        pass", "ClassDef"),
        ("del store", "Del"),
    ],
)
def test_complete_same_scope_binding_census_refuses(body: str, detail: str) -> None:
    keyword = "async def" if body.startswith(("async for", "async with")) else "def"
    source = f"{keyword} owner(store: CalendarEvidenceStore):\n    {body}\n"
    uses = normal.classify_store_uses(source, ("owner",))
    assert any(
        use.kind == "FORBIDDEN_STORE_ROOT_REBIND_OR_UNBIND" and use.detail == detail
        for use in uses
    )
    with pytest.raises(normal.NormalFormError, match="FORBIDDEN_STORE_ROOT_REBIND_OR_UNBIND"):
        _audit(source)


def test_rebinding_refuses_before_false_documented_terminal_is_extracted() -> None:
    source = (
        "def owner(store: CalendarEvidenceStore):\n"
        "    store = object()\n"
        "    return store.records()\n"
    )
    with pytest.raises(normal.NormalFormError, match="FORBIDDEN_STORE_ROOT_REBIND_OR_UNBIND"):
        normal.extract_owner_edges(source, ("owner",))


@pytest.mark.parametrize(
    ("body", "detail"),
    [
        ("local: CalendarEvidenceStore = other", "annotated_local_store_binding"),
        ("local = CalendarEvidenceStore()", "local_store_construction"),
        ("local = module.CalendarEvidenceStore()", "local_store_construction"),
    ],
)
def test_local_store_capability_construction_refuses(body: str, detail: str) -> None:
    source = f"def outer():\n    {body}\n"
    with pytest.raises(normal.NormalFormError, match=detail):
        normal.audit_store_capability_normal_form(source, ())


@pytest.mark.parametrize(
    "source",
    [
        "def outer():\n"
        "    def inner(store: CalendarEvidenceStore):\n"
        "        return store.records()\n"
        "    return inner\n",
        "def outer(store: CalendarEvidenceStore):\n"
        "    def inner(other: CalendarEvidenceStore):\n"
        "        return other.records()\n"
        "    return store.records()\n",
    ],
)
def test_rootless_and_rooted_nested_annotated_owners_refuse(source: str) -> None:
    with pytest.raises(normal.NormalFormError, match="nested_annotated_store_owner"):
        normal.audit_store_capability_normal_form(source, ("outer",))


@pytest.mark.parametrize(
    "body",
    [
        "def inner():\n        return store.records()\n    return inner()",
        "fn = lambda: store.records()\n    return fn()",
        "return tuple(store.get(key) for key in keys)",
        "return [store.get(key) for key in keys]",
        "return {store.get(key) for key in keys}",
        "return {key: store.get(key) for key in keys}",
    ],
)
def test_nested_callable_and_comprehension_capture_refuses(body: str) -> None:
    with pytest.raises(normal.NormalFormError, match="FORBIDDEN_NESTED_SCOPE_CAPTURE"):
        _audit(f"def owner(store: CalendarEvidenceStore):\n    {body}\n")


@pytest.mark.parametrize("attribute", ["records", "bad_method"])
def test_bound_method_extraction_refuses(attribute: str) -> None:
    source = f"def owner(store: CalendarEvidenceStore):\n    fn = store.{attribute}\n    return fn()\n"
    with pytest.raises(normal.NormalFormError, match="STORE_ATTRIBUTE_EXTRACTION"):
        _audit(source)


@pytest.mark.parametrize(
    ("body", "category"),
    [
        ("return unknown_helper(store)", "UNKNOWN_FORWARD"),
        ("return store", "RETURN_OR_YIELD"),
        ("yield store", "RETURN_OR_YIELD"),
        ("return [store]", "CONTAINER_ESCAPE"),
        ("return (store,)", "CONTAINER_ESCAPE"),
        ("return {'store': store}", "CONTAINER_ESCAPE"),
        ("return {store}", "CONTAINER_ESCAPE"),
        ("obj.value = store", "OBJECT_OR_SUBSCRIPT_STORAGE"),
        ("values[0] = store", "OBJECT_OR_SUBSCRIPT_STORAGE"),
        ("return getattr(store, 'records')", "DYNAMIC_ACCESS"),
        ("setattr(store, 'x', 1)", "DYNAMIC_ACCESS"),
        ("return vars(store)", "DYNAMIC_ACCESS"),
        ("return store.__dict__", "DYNAMIC_ACCESS"),
        ("return store._records", "STORE_ATTRIBUTE_EXTRACTION"),
        ("return store._envelopes", "STORE_ATTRIBUTE_EXTRACTION"),
    ],
)
def test_existing_capability_escape_rules_remain_refused(body: str, category: str) -> None:
    with pytest.raises(normal.NormalFormError, match=category):
        _audit(f"def owner(store: CalendarEvidenceStore):\n    {body}\n")


def test_each_root_load_receives_exactly_one_classification() -> None:
    source = (
        "def owner(store: CalendarEvidenceStore):\n"
        "    store.records()\n"
        "    return another_owner(evidence_store=store)\n"
        "def another_owner(store: CalendarEvidenceStore):\n"
        "    return store.records()\n"
    )
    uses = normal.classify_store_uses(source, ("owner", "another_owner"))
    assert len(uses) == 3
    assert len({(use.owner, use.lineno, use.col_offset) for use in uses}) == len(uses)
    assert all(use.kind in normal.UseKind.__args__ for use in uses)


def test_known_current_production_generator_capture_remains_refused() -> None:
    source = normal.CALENDAR_SOURCE.read_text(encoding="utf-8")
    with pytest.raises(normal.NormalFormError, match="FORBIDDEN_NESTED_SCOPE_CAPTURE"):
        normal.audit_store_capability_normal_form(source)


def test_acyclic_terminating_graph_passes_after_audits() -> None:
    source = (
        "def owner_a(store: CalendarEvidenceStore):\n"
        "    return owner_b(store)\n"
        "def owner_b(store: CalendarEvidenceStore):\n"
        "    return store.records()\n"
    )
    edges = normal.audit_replay_owner_graph(source, ("owner_a", "owner_b"))
    assert {edge.kind for edge in edges} == {
        "DOCUMENTED_STORE_API_TERMINAL",
        "ENUMERATED_REPLAY_OWNER_EDGE",
    }


def test_owner_cycle_refuses() -> None:
    source = (
        "def owner_a(store: CalendarEvidenceStore):\n"
        "    return owner_b(store)\n"
        "def owner_b(store: CalendarEvidenceStore):\n"
        "    return owner_a(store)\n"
    )
    with pytest.raises(normal.NormalFormError, match="cycle forbidden"):
        normal.audit_replay_owner_graph(source, ("owner_a", "owner_b"))


@pytest.mark.parametrize(
    ("builder", "field"),
    [
        ("store_root_grammar", "transparent_aliases_permitted"),
        ("store_binding_discipline", "forbidden_same_scope_binding_or_unbinding_forms"),
        ("permitted_direct_store_use", "starred_forwarding"),
        ("nested_owner_prohibition", "rootless_outer_can_hide_nested_owner"),
        ("proof_order_and_completeness_definition", "proof_order"),
        ("replay_owner_graph_rule", "cycles_permitted"),
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
    parent = normal.store_capability_normal_form_definition()
    parent_payload = copy.deepcopy(parent)
    parent_payload.pop("definition_sha256")
    parent_payload["child_definition_sha256"][builder] = mutated_child["definition_sha256"]
    assert normal._definition(parent_payload)["definition_sha256"] != parent["definition_sha256"]


def test_lineage_science_and_safety_are_preserved() -> None:
    safety = normal.science_lineage_and_safety()
    assert [row["definition_sha256"] for row in safety["failed_architecture_lineage"]] == list(
        normal.FAILED_ARCHITECTURE_LINEAGE
    )
    assert all(
        row["failed"] and not row["certified"] and not row["used"]
        for row in safety["failed_architecture_lineage"]
    )
    assert safety["certified_dependency"]["definition_sha256"] == normal.CERTIFIED_DEPENDENCY_SHA256
    assert safety["certified_dependency"]["changed"] is False
    assert set(safety["preserved_science"].values()) == {"UNCHANGED"}
    assert safety["safety"]["prospective_observations"] == 0
    assert safety["safety"]["collection_authorized"] is False


def test_artifacts_reproduce_child_order_and_tampering_refuses(tmp_path: Path) -> None:
    assert normal.restore_artifacts(ARTIFACT_DIR) == normal.store_capability_normal_form_definition()
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first = normal.write_artifacts(first_dir)
    second = normal.write_artifacts(second_dir, tuple(reversed(normal._CHILD_ARTIFACTS)))
    assert first == second
    assert {path.name: path.read_bytes() for path in first_dir.iterdir()} == {
        path.name: path.read_bytes() for path in second_dir.iterdir()
    }
    child_path = first_dir / "store_binding_discipline.json"
    child = json.loads(child_path.read_text(encoding="ascii"))
    child["root_is_immutable"] = False
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
            "btc_predictor.research.etf_calendar_store_capability_normal_form_r1",
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
