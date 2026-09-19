"""POSTP1-001V2A-PAD2 compiled binding-witness proof-architecture tests."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import types
from pathlib import Path

import pytest

from btc_predictor.research import etf_calendar_compiled_binding_witness as witness
from btc_predictor.research import etf_calendar_store_capability_normal_form_r1 as narrow


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / witness.OUTPUT_NAMESPACE
FROZEN_PYTHON = ROOT / ".venv312/bin/python"
OWNER = ("owner",)


def _owner(body: str, *, header: str = "def owner(store: CalendarEvidenceStore):") -> str:
    return f"{header}\n{body}"


def _witness(source: str, owners: tuple[str, ...] = OWNER) -> witness.CompiledBindingWitness:
    return witness.compiled_binding_witness(source, owners, "<candidate>")


def _findings(source: str, owners: tuple[str, ...] = OWNER) -> tuple[str, ...]:
    return tuple(row.kind for row in _witness(source, owners).findings)


def _refuses(source: str, owners: tuple[str, ...] = OWNER) -> None:
    with pytest.raises(witness.CompiledBindingWitnessError, match="compiled root binding forbidden"):
        witness.audit_compiled_binding_witness(source, owners, "<candidate>")


# ---------------------------------------------------------------------------
# Decision parent and frozen interpreter authority
# ---------------------------------------------------------------------------


def test_parent_freezes_the_compiled_binding_witness_and_review_only_authorization() -> None:
    decision = witness.compiled_binding_witness_v1_definition()
    assert decision["decision_version"] == "ETF_CALENDAR_COMPILED_BINDING_WITNESS_V1"
    assert decision["program_ticket"] == "POSTP1-001V2A-PAD2"
    assert decision["proof_strategy"] == (
        "CLOSED_AST_USE_GRAMMAR_PLUS_FROZEN_CPYTHON_BINDING_WITNESS"
    )
    assert decision["status"] == witness.STATUS
    assert decision["final_classification"] == (
        "ETF_CALENDAR_COMPILED_BINDING_WITNESS_V1_READY_FOR_XHIGH_REVIEW"
    )
    assert decision["failed_parent_sha256"] == (
        "7ef114fede9efebe594f0ecf119d097a1161119f448737d0df10afdf9468d17b"
    )
    central = decision["central_decisions"]
    assert central["hand_maintained_ast_binder_census_is_the_completeness_proof"] is False
    assert central["root_immutability_proven_against_exact_compiled_owner_code_object"] is True
    assert central["compiler_identity_is_scientific_proof_material"] is True
    assert central["type_statement_root_replacement_refused_before_graph_authority"] is True
    assert central["definition_time_named_expressions_refused_in_the_outer_owner"] is True
    assert central["nested_body_local_assignment_misclassified_as_outer_write"] is False
    assert central["store_aliases_permitted"] is False
    assert central["store_variadics_permitted"] is False
    assert central["starred_store_forwarding_permitted"] is False
    assert central["proves_arbitrary_python_semantics"] is False
    assert decision["authorization"] == {
        "independent_proof_architecture_xhigh_review_may_begin": True,
        "calendar_implementation_may_begin": False,
        "postp1_001v2r1_may_begin": False,
        "prospective_collection_may_begin": False,
    }
    assert decision["material_child_count"] == len(witness._CHILD_ARTIFACTS) == 11
    assert decision["proof_interpreter"] == dict(witness.PROOF_INTERPRETER_IDENTITY)


def test_frozen_proof_interpreter_is_the_exact_reviewed_cpython() -> None:
    identity = witness.verify_proof_interpreter_identity()
    assert identity["implementation_name"] == "cpython"
    assert (identity["version_major"], identity["version_minor"], identity["version_micro"]) == (
        3,
        12,
        14,
    )
    assert identity["magic_number_hex"] == "cb0d0d0a"
    assert identity["cache_tag"] == "cpython-312"
    assert identity == dict(witness.PROOF_INTERPRETER_IDENTITY)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("implementation_name", "pypy"),
        ("version_minor", 13),
        ("version_micro", 13),
        ("version_releaselevel", "candidate"),
        ("hexversion", 0x030D0000),
        ("cache_tag", "cpython-313"),
        ("magic_number_hex", "f30d0d0a"),
    ],
)
def test_interpreter_or_compiler_identity_mismatch_refuses_scientific_authority(
    field: str, value: object
) -> None:
    interposed = dict(witness.PROOF_INTERPRETER_IDENTITY)
    interposed[field] = value
    with pytest.raises(witness.CompiledBindingWitnessError, match="REFUSE_SCIENTIFIC_AUTHORITY"):
        witness.verify_proof_interpreter_identity(interposed)


def test_identity_shape_change_refuses() -> None:
    interposed = dict(witness.PROOF_INTERPRETER_IDENTITY)
    interposed.pop("magic_number_hex")
    with pytest.raises(witness.CompiledBindingWitnessError, match="shape mismatch"):
        witness.verify_proof_interpreter_identity(interposed)


def test_mismatched_interpreter_refuses_proof_authority_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(witness.PROOF_INTERPRETER_IDENTITY, "version_micro", 13)
    with pytest.raises(witness.CompiledBindingWitnessError, match="REFUSE_SCIENTIFIC_AUTHORITY"):
        witness.compiled_binding_witness_v1_definition()
    with pytest.raises(witness.CompiledBindingWitnessError, match="REFUSE_SCIENTIFIC_AUTHORITY"):
        witness.restore_artifacts(ARTIFACT_DIR)


# ---------------------------------------------------------------------------
# Opcode-policy integrity
# ---------------------------------------------------------------------------


def _opcode_stub(**overrides: object) -> types.SimpleNamespace:
    import opcode as real

    opname = list(real.opname)
    stub = types.SimpleNamespace(
        opname=opname,
        haslocal=list(real.haslocal),
        hasfree=list(real.hasfree),
        hasname=list(real.hasname),
    )
    for key, value in overrides.items():
        setattr(stub, key, value)
    return stub


def test_frozen_opcode_policy_matches_the_exact_interpreter_table() -> None:
    table = witness.verify_opcode_policy_integrity()
    assert set(table["named"]) == set(witness.ROOT_BINDING_OPCODE_POLICY)
    assert table["named"] == dict(sorted(witness.FROZEN_OPCODE_NUMBERS.items()))
    assert table["unnamed"] == [148]
    assert 148 not in set(__import__("opcode").opmap.values())
    assert len(__import__("opcode")._specialized_instructions) == (
        witness.FROZEN_SPECIALIZED_INSTRUCTION_COUNT
    )
    assert set(witness._opcodes_of_class("ROOT_WRITE")) == {
        "STORE_FAST",
        "STORE_FAST_MAYBE_NULL",
        "STORE_DEREF",
        "STORE_NAME",
        "STORE_GLOBAL",
    }
    assert set(witness._opcodes_of_class("ROOT_DELETE")) == {
        "DELETE_FAST",
        "DELETE_DEREF",
        "DELETE_NAME",
        "DELETE_GLOBAL",
    }
    assert witness._opcodes_of_class("ROOT_CLEAR") == ("LOAD_FAST_AND_CLEAR",)
    assert witness._opcodes_of_class("FRAME_ENTRY_CELL_ESTABLISHMENT") == ("MAKE_CELL",)


def test_unexpected_root_binding_opcode_requires_a_new_proof_architecture() -> None:
    import opcode as real

    opname = list(real.opname)
    free_slot = next(index for index, name in enumerate(opname) if name.startswith("<"))
    opname[free_slot] = "STORE_SOMETHING_NEW"
    stub = _opcode_stub(opname=opname, haslocal=[*real.haslocal, free_slot])
    with pytest.raises(
        witness.CompiledBindingWitnessError, match="REQUIRE_NEW_PROOF_ARCHITECTURE"
    ):
        witness.verify_opcode_policy_integrity(stub)


def test_absent_expected_opcode_requires_a_new_proof_architecture() -> None:
    import opcode as real

    stub = _opcode_stub(
        haslocal=[index for index in real.haslocal if real.opname[index] != "STORE_FAST"]
    )
    with pytest.raises(
        witness.CompiledBindingWitnessError, match="REQUIRE_NEW_PROOF_ARCHITECTURE"
    ):
        witness.verify_opcode_policy_integrity(stub)


def test_moved_opcode_number_requires_a_new_proof_architecture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(witness.FROZEN_OPCODE_NUMBERS, "STORE_FAST", 7)
    with pytest.raises(
        witness.CompiledBindingWitnessError, match="REQUIRE_NEW_PROOF_ARCHITECTURE"
    ):
        witness.verify_opcode_policy_integrity()


def test_changed_reserved_unnamed_opcode_set_requires_a_new_proof_architecture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(witness, "FROZEN_UNNAMED_NAME_GROUP_OPCODES", ())
    with pytest.raises(
        witness.CompiledBindingWitnessError, match="REQUIRE_NEW_PROOF_ARCHITECTURE"
    ):
        witness.verify_opcode_policy_integrity()


# ---------------------------------------------------------------------------
# Exact owner code-object identification
# ---------------------------------------------------------------------------


def test_exact_top_level_owner_code_object_is_identified() -> None:
    source = _owner("    return store.records()\n")
    identified = _witness(source).owners
    assert len(identified) == 1
    assert identified[0].owner == "owner"
    assert identified[0].qualname == "owner"
    assert identified[0].first_line == 1
    assert identified[0].parameters == ("store",)
    assert identified[0].roots == ("store",)


@pytest.mark.parametrize(
    ("label", "source", "expected_line"),
    [
        ("plain", "def owner(store: CalendarEvidenceStore):\n    return store.records()\n", 1),
        (
            "async",
            "async def owner(store: CalendarEvidenceStore):\n    return store.records()\n",
            1,
        ),
        (
            "pep695_generic",
            "def owner[T](store: CalendarEvidenceStore):\n    return store.records()\n",
            1,
        ),
    ],
)
def test_owner_identity_agrees_with_the_compiler_definition_line(
    label: str, source: str, expected_line: int
) -> None:
    identified = _witness(source).owners[0]
    assert identified.qualname == "owner", label
    assert identified.first_line == expected_line, label
    assert identified.roots == ("store",), label


@pytest.mark.parametrize(
    ("label", "source", "expected_line"),
    [
        (
            "decorated",
            "@deco\ndef owner(store: CalendarEvidenceStore):\n    return store.records()\n",
            1,
        ),
        (
            "stacked_decorators",
            "@a\n@b\ndef owner(store: CalendarEvidenceStore):\n    return store.records()\n",
            1,
        ),
        (
            "async_decorated",
            "@deco\nasync def owner(store: CalendarEvidenceStore):\n    return store.records()\n",
            1,
        ),
    ],
)
def test_decorator_definition_line_matches_the_compiler_but_owners_may_not_decorate(
    label: str, source: str, expected_line: int
) -> None:
    import ast as _ast

    node = next(
        child
        for child in _ast.parse(source).body
        if isinstance(child, (_ast.FunctionDef, _ast.AsyncFunctionDef))
    )
    assert witness.owner_definition_line(node) == expected_line, label
    module_code = witness.compile_reviewed_source(source, "<candidate>")
    identity = witness.identify_owner_code_object(
        module_code, "owner", expected_line, ("store",)
    )
    assert identity.first_line == expected_line, label
    assert "MODULE_OWNER_DECORATED" in _findings(source)
    _refuses(source)


def test_same_named_nested_function_is_never_substituted_for_the_owner() -> None:
    source = (
        "def owner(store: CalendarEvidenceStore):\n"
        "    def inner():\n"
        "        def owner(store):\n"
        "            return store\n"
        "        return owner\n"
        "    return store.records()\n"
    )
    identified = _witness(source).owners[0]
    assert identified.qualname == "owner"
    assert identified.first_line == 1


def test_duplicate_top_level_owner_definitions_refuse() -> None:
    source = (
        "def owner(store: CalendarEvidenceStore):\n"
        "    return store.records()\n"
        "def owner(store: CalendarEvidenceStore):\n"
        "    store = other\n"
        "    return store\n"
    )
    module_code = witness.compile_reviewed_source(source, "<candidate>")
    with pytest.raises(witness.CompiledBindingWitnessError, match="not exact"):
        witness.identify_owner_code_object(module_code, "owner", 1, ("store",))
    findings = witness.owner_name_identity_findings(
        module_code, {"owner": __import__("ast").parse(source).body[0]}
    )
    assert [row.kind for row in findings] == ["MODULE_OWNER_NAME_NOT_UNIQUELY_BOUND"]


def test_absent_frozen_owner_refuses() -> None:
    source = _owner("    return store.records()\n")
    with pytest.raises(witness.CompiledBindingWitnessError, match="absent from the reviewed source"):
        witness.compiled_binding_witness(source, ("owner", "missing_owner"), "<candidate>")


# ---------------------------------------------------------------------------
# The TypeAlias review defect
# ---------------------------------------------------------------------------


TYPE_ALIAS_OWNER = _owner("    type store = int\n    return store.records()\n")


def test_type_alias_root_replacement_refuses_through_the_compiled_witness() -> None:
    assert _findings(TYPE_ALIAS_OWNER) == ("OWNER_SCOPE_ROOT_WRITE",)
    assert _witness(TYPE_ALIAS_OWNER).findings[0].opname == "STORE_FAST"
    _refuses(TYPE_ALIAS_OWNER)


def test_type_alias_refusal_precedes_graph_authority() -> None:
    with pytest.raises(witness.CompiledBindingWitnessError, match="compiled root binding forbidden"):
        witness.audit_compiled_binding_witness_architecture(
            TYPE_ALIAS_OWNER, OWNER, "<candidate>"
        )


def test_the_source_ast_binding_visitor_is_not_the_proof_of_root_immutability() -> None:
    """The AST layer misses ``ast.TypeAlias``; the compiled witness still refuses."""

    assert witness.ast_binding_diagnostics(TYPE_ALIAS_OWNER, OWNER) == ()
    narrow.audit_store_capability_normal_form(TYPE_ALIAS_OWNER, OWNER)
    _refuses(TYPE_ALIAS_OWNER)
    inlined = _owner("    values = [1 for store in items]\n    return store.records()\n")
    assert witness.ast_binding_diagnostics(inlined, OWNER) == ()
    narrow.audit_store_capability_normal_form(inlined, OWNER)
    assert set(_findings(inlined)) == {
        "OWNER_SCOPE_ROOT_CLEAR",
        "OWNER_SCOPE_ROOT_WRITE",
    }
    _refuses(inlined)
    definition = witness.compiled_binding_witness_definition()
    assert definition["hand_maintained_ast_binder_census_is_the_proof"] is False
    assert definition["missing_ast_diagnostic_can_accept_a_compiled_root_write"] is False
    assert definition["ast_binding_visitor_role"] == [
        "DIAGNOSTICS",
        "EARLY_FAILURE",
        "HUMAN_READABLE_REASON_CODES",
        "REGRESSION_LOCALIZATION",
    ]


def test_layer_disagreement_never_chooses_the_permissive_result() -> None:
    with pytest.raises(witness.CompiledBindingWitnessError, match="regardless of the AST"):
        witness.reconcile_binding_layers(TYPE_ALIAS_OWNER, OWNER, "<candidate>")


# ---------------------------------------------------------------------------
# Definition-time assignment expressions in the enclosing owner
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "body"),
    [
        ("nested_function_default", "    def helper(x=(store := other)):\n        pass\n"),
        (
            "nested_async_function_default",
            "    async def helper(x=(store := other)):\n        pass\n",
        ),
        (
            "nested_function_decorator",
            "    @decorator(store := other)\n    def helper():\n        pass\n",
        ),
        ("lambda_default", "    helper = lambda x=(store := other): None\n"),
        (
            "class_base",
            "    class Helper(base_factory(store := other)):\n        pass\n",
        ),
        (
            "class_keyword",
            "    class Helper(Base, metaclass=(store := other)):\n        pass\n",
        ),
        (
            "class_decorator",
            "    @decorator(store := other)\n    class Helper:\n        pass\n",
        ),
    ],
)
def test_definition_time_named_expressions_refuse_in_the_outer_owner(
    label: str, body: str
) -> None:
    source = _owner(f"{body}    return store.records()\n")
    assert _findings(source) == ("OWNER_SCOPE_ROOT_WRITE",), label
    _refuses(source)


# ---------------------------------------------------------------------------
# Ordinary binder regressions, proven by compiled behaviour
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "header", "body"),
    [
        ("Assign", None, "    store = other\n"),
        ("AnnAssign", None, "    store: int = 1\n"),
        ("AugAssign", None, "    store += 1\n"),
        ("NamedExpr", None, "    (store := other)\n"),
        ("For", None, "    for store in items:\n        pass\n"),
        (
            "AsyncFor",
            "async def owner(store: CalendarEvidenceStore):",
            "    async for store in items:\n        pass\n",
        ),
        ("With", None, "    with cm() as store:\n        pass\n"),
        (
            "AsyncWith",
            "async def owner(store: CalendarEvidenceStore):",
            "    async with cm() as store:\n        pass\n",
        ),
        (
            "ExceptHandler",
            None,
            "    try:\n        pass\n    except Exception as store:\n        pass\n",
        ),
        ("MatchCapture", None, "    match value:\n        case store:\n            pass\n"),
        ("Import", None, "    import store\n"),
        ("ImportFrom", None, "    from module import member as store\n"),
        ("FunctionDefShadow", None, "    def store():\n        pass\n"),
        (
            "AsyncFunctionDefShadow",
            None,
            "    async def store():\n        pass\n",
        ),
        ("ClassDefShadow", None, "    class store:\n        pass\n"),
        ("Del", None, "    del store\n"),
        ("InlinedComprehensionTarget", None, "    values = [store for store in items]\n"),
    ],
)
def test_ordinary_rebinding_forms_refuse_through_the_compiled_witness(
    label: str, header: str | None, body: str
) -> None:
    kwargs = {} if header is None else {"header": header}
    source = _owner(f"{body}    return store.records()\n", **kwargs)
    kinds = set(_findings(source))
    assert kinds, label
    assert kinds <= {
        "OWNER_SCOPE_ROOT_WRITE",
        "OWNER_SCOPE_ROOT_DELETE",
        "OWNER_SCOPE_ROOT_CLEAR",
    }, label
    _refuses(source)


def test_delete_is_witnessed_as_a_root_delete() -> None:
    source = _owner("    del store\n    return store.records()\n")
    assert _findings(source) == ("OWNER_SCOPE_ROOT_DELETE",)
    assert _witness(source).findings[0].opname == "DELETE_FAST"


# ---------------------------------------------------------------------------
# Cell-variable roots and nested-body isolation
# ---------------------------------------------------------------------------


NONLOCAL_WRITE = _owner(
    "    def helper():\n"
    "        nonlocal store\n"
    "        store = other\n"
    "    helper()\n"
    "    return store.records()\n"
)
NONLOCAL_DELETE = _owner(
    "    def helper():\n"
    "        nonlocal store\n"
    "        del store\n"
    "    helper()\n"
    "    return store.records()\n"
)
GENERATOR_WALRUS = _owner("    return tuple((store := item) for item in items)\n")
NESTED_BODY_LOCAL = _owner(
    "    def helper():\n"
    "        store = other\n"
    "        return store\n"
    "    return store.records()\n"
)


def test_cell_variable_root_write_refuses_without_relying_on_store_fast() -> None:
    findings = _witness(NONLOCAL_WRITE).findings
    assert {row.kind for row in findings} == {
        "OWNER_ROOT_IS_CELL_VARIABLE",
        "OWNER_CELL_ROOT_WRITE",
    }
    deref = next(row for row in findings if row.kind == "OWNER_CELL_ROOT_WRITE")
    assert deref.opname == "STORE_DEREF"
    assert deref.scope.startswith("OWNER_CELL_CLOSURE:")
    _refuses(NONLOCAL_WRITE)


def test_cell_variable_root_delete_refuses() -> None:
    findings = _witness(NONLOCAL_DELETE).findings
    assert {row.kind for row in findings} == {
        "OWNER_ROOT_IS_CELL_VARIABLE",
        "OWNER_CELL_ROOT_DELETE",
    }
    assert next(
        row for row in findings if row.kind == "OWNER_CELL_ROOT_DELETE"
    ).opname == "DELETE_DEREF"
    _refuses(NONLOCAL_DELETE)


def test_generator_expression_assignment_expression_rebinds_the_owner_root() -> None:
    findings = _witness(GENERATOR_WALRUS).findings
    assert {row.kind for row in findings} == {
        "OWNER_ROOT_IS_CELL_VARIABLE",
        "OWNER_CELL_ROOT_WRITE",
    }
    _refuses(GENERATOR_WALRUS)


def test_deep_closure_root_write_refuses() -> None:
    source = _owner(
        "    def helper():\n"
        "        def inner():\n"
        "            nonlocal store\n"
        "            store = other\n"
        "        return inner\n"
        "    return store.records()\n"
    )
    assert {row.kind for row in _witness(source).findings} == {
        "OWNER_ROOT_IS_CELL_VARIABLE",
        "OWNER_CELL_ROOT_WRITE",
    }
    _refuses(source)


# ---------------------------------------------------------------------------
# The root is never a first-class closure cell
# ---------------------------------------------------------------------------


CLOSURE_CELL_WRITE = _owner(
    "    capture = lambda: store\n"
    "    capture.__closure__[0].cell_contents = other\n"
    "    return store.records()\n"
)
CLOSURE_CELL_DELETE = _owner(
    "    capture = lambda: store\n"
    "    del capture.__closure__[0].cell_contents\n"
    "    return store.records()\n"
)
CELL_PASSED_TO_HELPER = _owner(
    "    capture = lambda: store\n"
    "    def poke(cell):\n"
    "        cell.cell_contents = other\n"
    "    poke(capture.__closure__[0])\n"
    "    return store.records()\n"
)


@pytest.mark.parametrize(
    ("label", "source"),
    [
        ("cell_contents_write", CLOSURE_CELL_WRITE),
        ("cell_contents_delete", CLOSURE_CELL_DELETE),
        ("cell_handed_to_a_helper", CELL_PASSED_TO_HELPER),
    ],
)
def test_closure_cell_escape_refuses_structurally(label: str, source: str) -> None:
    """A cell object could rebind the root with no root-binding instruction."""

    findings = _witness(source).findings
    assert [row.kind for row in findings] == ["OWNER_ROOT_IS_CELL_VARIABLE"], label
    assert _witness(source).root_rebinding_findings == (), label
    _refuses(source)
    with pytest.raises(
        witness.CompiledBindingWitnessError, match="reflective authority escape"
    ):
        witness.audit_dynamic_execution_prohibition(source, OWNER, "<candidate>")


def test_any_capture_makes_the_root_a_cell_and_refuses() -> None:
    for body in (
        "    helper = lambda: store\n    return store.records()\n",
        "    def helper():\n        return store\n    return store.records()\n",
        "    return tuple(helper(store) for item in items)\n",
    ):
        source = _owner(body)
        assert [row.kind for row in _witness(source).findings] == [
            "OWNER_ROOT_IS_CELL_VARIABLE"
        ]
        _refuses(source)


@pytest.mark.parametrize(
    ("label", "body"),
    [
        ("ctypes_frame_writeback", "    import ctypes\n"),
        ("sys_getframe", "    frame = sys._getframe()\n"),
        ("frame_locals", "    holder.f_locals['store'] = other\n"),
        ("inspect_module", "    import inspect\n"),
        ("gc_referrers", "    import gc\n"),
        ("code_object", "    target = helper.__code__\n"),
        ("function_globals", "    target = helper.__globals__\n"),
        ("wrapper_unwrap", "    target = helper.__wrapped__\n"),
    ],
)
def test_reflective_authority_escapes_refuse_in_replay_owners(label: str, body: str) -> None:
    source = _owner(f"{body}    return store.records()\n")
    with pytest.raises(
        witness.CompiledBindingWitnessError, match="reflective authority escape"
    ):
        witness.audit_dynamic_execution_prohibition(source, OWNER, "<candidate>")


def test_class_body_attribute_of_the_same_name_is_not_an_owner_root_write() -> None:
    """A class body binds its own ``co_names`` entry, not the owner's cell."""

    source = _owner(
        "    class Helper:\n"
        "        store = 1\n"
        "        def method(self):\n"
        "            return store\n"
        "    return store.records()\n"
    )
    findings = _witness(source).findings
    assert [row.kind for row in findings] == ["OWNER_ROOT_IS_CELL_VARIABLE"]
    assert all(row.opname != "STORE_NAME" for row in findings)


def test_class_body_nonlocal_write_is_still_an_owner_root_write() -> None:
    source = _owner(
        "    class Helper:\n"
        "        nonlocal store\n"
        "        store = 1\n"
        "    return store.records()\n"
    )
    assert "OWNER_CELL_ROOT_WRITE" in {row.kind for row in _witness(source).findings}
    _refuses(source)


# ---------------------------------------------------------------------------
# Module-level owner name identity
# ---------------------------------------------------------------------------


def _module_identity(source: str) -> list[str]:
    return [row.kind for row in _witness(source).module_identity_findings]


def test_decorated_replay_owner_definition_refuses() -> None:
    source = "@deco\ndef owner(store: CalendarEvidenceStore):\n    return store.records()\n"
    assert _module_identity(source) == ["MODULE_OWNER_DECORATED"]
    _refuses(source)


@pytest.mark.parametrize(
    ("label", "tail", "kind"),
    [
        ("plain_rebind", "owner = guard(owner)\n", "MODULE_OWNER_NAME_NOT_UNIQUELY_BOUND"),
        ("deletion", "del owner\n", "MODULE_OWNER_NAME_REBOUND"),
        ("globals_subscript", "globals()['owner'] = guard\n", "MODULE_NAMESPACE_REACH"),
        ("module_level_exec", "exec('def owner(store): return 1')\n", "MODULE_NAMESPACE_REACH"),
        ("code_object_swap", "owner.__code__ = impostor.__code__\n", "MODULE_FUNCTION_OBJECT_MUTATION"),
        ("defaults_swap", "owner.__defaults__ = (1,)\n", "MODULE_FUNCTION_OBJECT_MUTATION"),
        ("module_attribute_swap", "modules[__name__].owner = guard\n", "MODULE_OWNER_NAME_REBOUND"),
        ("setattr_swap", "setattr(here, 'owner', guard)\n", "MODULE_NAMESPACE_REACH"),
    ],
)
def test_module_level_owner_substitution_refuses(label: str, tail: str, kind: str) -> None:
    source = (
        "def owner(store: CalendarEvidenceStore):\n"
        "    return store.records()\n"
        f"{tail}"
    )
    assert kind in _module_identity(source), label
    _refuses(source)


@pytest.mark.parametrize(
    ("label", "helper"),
    [
        (
            "globals_one_frame_deep",
            "def _install():\n    globals()['owner'] = guard\n_install()\n",
        ),
        (
            "global_statement_rebind",
            "def _install():\n    global owner\n    owner = guard\n_install()\n",
        ),
        (
            "code_swap_one_frame_deep",
            "def _install():\n    owner.__code__ = impostor.__code__\n_install()\n",
        ),
        (
            "exec_one_frame_deep",
            "def _install():\n    exec('pass')\n_install()\n",
        ),
    ],
)
def test_module_substitution_hidden_in_a_helper_frame_refuses(
    label: str, helper: str
) -> None:
    """The module identity audit walks the whole module code-object tree."""

    source = (
        "def owner(store: CalendarEvidenceStore):\n"
        "    return store.records()\n"
        f"{helper}"
    )
    assert _module_identity(source), label
    _refuses(source)


@pytest.mark.parametrize(
    ("label", "body"),
    [
        ("bare_nonlocal", "    def inner():\n        nonlocal store\n"),
        ("dead_nested_scope", "    if False:\n        def inner():\n            nonlocal store\n"),
        ("pep695_lazy_type_alias", "    type Alias = store.records()\n"),
    ],
)
def test_structural_rule_is_strictly_stricter_than_the_source_grammar(
    label: str, body: str
) -> None:
    """Deliberate fail-closed over-refusal; the decision never claims parity."""

    source = _owner(f"{body}    return store.records()\n")
    assert [row.kind for row in _witness(source).findings] == [
        "OWNER_ROOT_IS_CELL_VARIABLE"
    ], label
    _refuses(source)
    narrow.audit_store_capability_normal_form(source, OWNER)
    definition = witness.compiled_binding_witness_definition()
    assert definition[
        "structural_rule_is_at_least_as_strict_as_the_source_nested_capture_prohibition"
    ] is True
    assert definition["structural_rule_may_refuse_sources_the_source_grammar_accepts"] is True


def test_clean_module_has_no_module_identity_findings() -> None:
    source = _owner("    return store.records()\n")
    assert _module_identity(source) == []


def test_conditional_module_level_owner_is_refused_by_the_structural_grammar() -> None:
    source = (
        "def owner(store: CalendarEvidenceStore):\n"
        "    return store.records()\n"
        "if flag:\n"
        "    def owner(store: CalendarEvidenceStore):\n"
        "        del store\n"
        "        return None\n"
    )
    with pytest.raises(witness.CompiledBindingWitnessError, match="not exact"):
        _witness(source)
    module_code = witness.compile_reviewed_source(source, "<candidate>")
    import ast as _ast

    findings = witness.owner_name_identity_findings(
        module_code, {"owner": _ast.parse(source).body[0]}
    )
    assert "MODULE_OWNER_NAME_NOT_UNIQUELY_BOUND" in [row.kind for row in findings]
    with pytest.raises(narrow.NormalFormError, match="nested_annotated_store_owner"):
        narrow.verify_replay_owner_census(source, OWNER)


def test_nested_body_local_assignment_is_not_an_outer_owner_write() -> None:
    """Negative control: the nested scope binds its own local, not the owner root."""

    result = _witness(NESTED_BODY_LOCAL)
    assert result.findings == ()
    assert result.root_immutable is True
    witness.audit_compiled_binding_witness(NESTED_BODY_LOCAL, OWNER, "<candidate>")
    # The independent source grammar still refuses the nested capability capture.
    with pytest.raises(narrow.NormalFormError, match="FORBIDDEN_NESTED_SCOPE_CAPTURE"):
        narrow.audit_store_capability_normal_form(NESTED_BODY_LOCAL, OWNER)


def test_specialized_bytecode_cannot_hide_a_root_write_from_the_scan() -> None:
    """The scan is deoptimized, so quickening never changes its result."""

    source = _owner("    store = other\n    return store.records()\n")
    before = _findings(source)
    code = witness.compile_reviewed_source(source, "<candidate>")
    owner_code = next(
        child for child in witness._all_code_objects(code) if child.co_qualname == "owner"
    )
    warm = types.FunctionType(owner_code, {"other": 1})
    for _ in range(3000):
        try:
            warm(None)
        except Exception:  # pragma: no cover - value semantics are irrelevant here
            break
    assert _findings(source) == before == ("OWNER_SCOPE_ROOT_WRITE",)


def test_nested_scope_that_owns_its_own_binding_is_not_an_outer_root_write() -> None:
    source = _owner(
        "    def helper():\n"
        "        store = 1\n"
        "        def inner():\n"
        "            nonlocal store\n"
        "            store = 2\n"
        "        return inner\n"
        "    return store.records()\n"
    )
    assert _witness(source).findings == ()


def test_lambda_parameter_named_like_the_root_is_not_an_outer_root_write() -> None:
    source = _owner("    helper = lambda store: store\n    return store.records()\n")
    assert _witness(source).findings == ()


def test_generator_expression_capture_is_binding_compatible_but_exposes_a_cell() -> None:
    source = _owner("    return tuple(helper(store) for item in items)\n")
    result = _witness(source)
    assert result.root_rebinding_findings == ()
    assert [row.kind for row in result.root_capture_findings] == [
        "OWNER_ROOT_IS_CELL_VARIABLE"
    ]
    assert result.owners[0].cell_roots == ("store",)


def test_clean_owner_passes_the_binding_witness() -> None:
    source = _owner("    return store.records()\n")
    assert witness.audit_compiled_binding_witness(source, OWNER, "<candidate>").root_immutable


# ---------------------------------------------------------------------------
# Source / compiled identity
# ---------------------------------------------------------------------------


def test_witness_binds_the_exact_reviewed_source() -> None:
    source = _owner("    return store.records()\n")
    produced = _witness(source)
    assert produced.source_sha256 == witness.source_sha256(source)
    witness.verify_witness_binds_source(produced, source)


def test_detached_witness_from_another_source_refuses() -> None:
    source_a = _owner("    return store.records()\n")
    source_b = _owner("    return store.envelopes()\n")
    produced = _witness(source_a)
    with pytest.raises(
        witness.CompiledBindingWitnessError, match="does not certify this source"
    ):
        witness.verify_witness_binds_source(produced, source_b)


def test_witness_from_another_compiler_identity_refuses() -> None:
    source = _owner("    return store.records()\n")
    produced = _witness(source)
    interposed = dict(produced.interpreter_identity)
    interposed["magic_number_hex"] = "f30d0d0a"
    detached = witness.CompiledBindingWitness(
        decision_version=produced.decision_version,
        source_sha256=produced.source_sha256,
        filename=produced.filename,
        interpreter_identity=tuple(sorted(interposed.items())),
        owners=produced.owners,
        findings=produced.findings,
    )
    with pytest.raises(
        witness.CompiledBindingWitnessError, match="not produced by the frozen proof interpreter"
    ):
        witness.verify_witness_binds_source(detached, source)


def test_compile_settings_are_frozen_and_never_execute_the_source() -> None:
    identity = witness.proof_interpreter_identity()["compile_settings"]
    assert identity == {
        "mode": "exec",
        "flags": 0,
        "dont_inherit": True,
        "optimize": 0,
        "executes_reviewed_source": False,
        "imports_reviewed_source": False,
        "performs_https_signing_persistence_or_collection": False,
    }
    assert witness.proof_interpreter_identity()["cached_pyc_is_scientific_authority"] is False
    code = witness.compile_reviewed_source(
        "SENTINEL = 1 / 0\n", "<never-executed>"
    )
    assert isinstance(code, types.CodeType)


# ---------------------------------------------------------------------------
# Dynamic execution prohibition
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["exec", "eval", "compile", "__import__", "globals", "locals"])
def test_dynamic_execution_in_a_replay_owner_refuses(name: str) -> None:
    source = _owner(f"    {name}('x')\n    return store.records()\n")
    with pytest.raises(witness.CompiledBindingWitnessError, match="dynamic code execution"):
        witness.audit_dynamic_execution_prohibition(source, OWNER, "<candidate>")


def test_dynamic_execution_hidden_in_a_nested_scope_refuses() -> None:
    source = _owner(
        "    def helper():\n        return exec('x')\n    return store.records()\n"
    )
    with pytest.raises(witness.CompiledBindingWitnessError, match="dynamic code execution"):
        witness.audit_dynamic_execution_prohibition(source, OWNER, "<candidate>")


def test_dynamic_prohibition_leaves_the_hostile_threat_model_out_of_scope() -> None:
    rule = witness.dynamic_execution_prohibition()
    assert rule["project_supported_dynamic_store_authority_synthesis"] == "FORBIDDEN"
    assert rule["arbitrary_hostile_same_process_mutation_in_threat_model"] is False
    assert rule["attempts_to_prove_arbitrary_dynamic_python_mutation"] is False
    assert rule["escalation_if_hostile_resistance_becomes_required"] == "PROCESS_ISOLATION"


# ---------------------------------------------------------------------------
# The preserved closed AST grammar
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("body", "category"),
    [
        ("alias = store\n    return alias.records()", "store_alias_or_assignment"),
        ("return store.records", "STORE_ATTRIBUTE_EXTRACTION"),
        ("return unknown_owner(store)", "UNKNOWN_FORWARD"),
        ("return store", "RETURN_OR_YIELD"),
        ("return [store]", "CONTAINER_ESCAPE"),
        ("holder.store = store\n    return store.records()", "OBJECT_OR_SUBSCRIPT_STORAGE"),
        ("return getattr(store, 'records')()", "DYNAMIC_ACCESS"),
        ("return store._records", "STORE_ATTRIBUTE_EXTRACTION"),
        ("return store._envelopes", "STORE_ATTRIBUTE_EXTRACTION"),
    ],
)
def test_existing_capability_escape_rules_remain_refused(body: str, category: str) -> None:
    with pytest.raises(narrow.NormalFormError, match=category):
        narrow.audit_store_capability_normal_form(_owner(f"    {body}\n"), OWNER)


@pytest.mark.parametrize(
    "source",
    [
        "def owner(*stores: CalendarEvidenceStore):\n    return None\n",
        "def owner(**stores: CalendarEvidenceStore):\n    return None\n",
    ],
)
def test_annotated_store_variadics_remain_forbidden(source: str) -> None:
    with pytest.raises(narrow.NormalFormError, match="annotated_store_variadic_parameter"):
        narrow.audit_store_capability_normal_form(source, OWNER)


@pytest.mark.parametrize("call", ["enumerated(*store)", "enumerated(**store)"])
def test_starred_store_forwarding_remains_forbidden(call: str) -> None:
    source = (
        f"def owner(store: CalendarEvidenceStore):\n    return {call}\n"
        "def enumerated(store: CalendarEvidenceStore):\n    return store.records()\n"
    )
    with pytest.raises(narrow.NormalFormError, match="FORBIDDEN_STARRED_FORWARD"):
        narrow.audit_store_capability_normal_form(source, ("owner", "enumerated"))


def test_nested_annotated_owner_remains_refused() -> None:
    source = (
        "def outer():\n"
        "    def owner(store: CalendarEvidenceStore):\n"
        "        return store.records()\n"
        "    return owner\n"
    )
    with pytest.raises(narrow.NormalFormError, match="nested_annotated_store_owner"):
        narrow.verify_replay_owner_census(source, ())


@pytest.mark.parametrize("api", ["put", "get", "records", "envelopes"])
def test_direct_documented_store_api_use_still_passes(api: str) -> None:
    argument = "'x'" if api == "get" else "object()" if api == "put" else ""
    uses = narrow.audit_store_capability_normal_form(
        _owner(f"    return store.{api}({argument})\n"), OWNER
    )
    assert [use.kind for use in uses] == ["PERMITTED_DIRECT_STORE_API_CALL"]


# ---------------------------------------------------------------------------
# Proof order, graph and current production
# ---------------------------------------------------------------------------


def test_frozen_proof_order_runs_the_binding_witness_before_graph_authority() -> None:
    order = witness.PROOF_ORDER
    assert order[0] == "VERIFY_FROZEN_CPYTHON_COMPILER_IDENTITY"
    assert order.index("RUN_COMPILED_BINDING_WITNESS_FOR_EVERY_ROOT") < order.index(
        "RUN_CLOSED_AST_STORE_USE_GRAMMAR"
    )
    assert order.index("REJECT_ANY_ROOT_WRITE_CLEAR_OR_DELETE") < order.index(
        "EXTRACT_DIRECT_API_AND_ENUMERATED_OWNER_EDGES"
    )
    assert order[-1] == "VERIFY_DIRECT_DEPENDENCY_BODY_AND_STARTUP_CONTRACTS"
    assert len(order) == 13


def test_conforming_two_owner_source_passes_the_whole_frozen_proof_order() -> None:
    source = (
        "def owner_a(store: CalendarEvidenceStore):\n"
        "    return owner_b(store)\n"
        "def owner_b(store: CalendarEvidenceStore):\n"
        "    return store.records()\n"
    )
    result = witness.audit_compiled_binding_witness_architecture(
        source, ("owner_a", "owner_b"), "<candidate>"
    )
    assert result["root_mutations"] == 0
    assert result["census"] == ["owner_a", "owner_b"]
    assert result["edges"] == 2
    assert result["layer_reconciliation"]["authoritative_layer"] == "COMPILED_BINDING_WITNESS"


def test_owner_cycles_and_non_terminating_paths_remain_refused() -> None:
    cyclic = (
        "def owner_a(store: CalendarEvidenceStore):\n"
        "    return owner_b(store)\n"
        "def owner_b(store: CalendarEvidenceStore):\n"
        "    return owner_a(store)\n"
    )
    with pytest.raises(narrow.NormalFormError, match="cycle forbidden"):
        witness.audit_compiled_binding_witness_architecture(
            cyclic, ("owner_a", "owner_b"), "<candidate>"
        )


def test_current_production_owner_census_is_exactly_eleven() -> None:
    source = witness.CALENDAR_SOURCE.read_text(encoding="utf-8")
    assert narrow.verify_replay_owner_census(source) == witness.FROZEN_REPLAY_OWNERS
    assert len(witness.FROZEN_REPLAY_OWNERS) == 11
    produced = witness.compiled_binding_witness(source)
    assert len(produced.owners) == 11
    assert sorted(row.owner for row in produced.owners) == sorted(witness.FROZEN_REPLAY_OWNERS)


def test_current_production_has_no_root_rebinding_anywhere() -> None:
    source = witness.CALENDAR_SOURCE.read_text(encoding="utf-8")
    produced = witness.compiled_binding_witness(source)
    assert produced.root_rebinding_findings == ()
    witness.verify_witness_binds_source(produced, source)
    witness.audit_dynamic_execution_prohibition(source)
    captured = {row.owner: row.cell_roots for row in produced.owners}
    assert captured["common_etf_session_status"] == ("evidence_store",)
    assert all(
        roots == () for owner, roots in captured.items()
        if owner != "common_etf_session_status"
    )


def test_current_production_compiled_refusal_is_the_single_known_generator_capture() -> None:
    source = witness.CALENDAR_SOURCE.read_text(encoding="utf-8")
    produced = witness.compiled_binding_witness(source)
    assert [
        (row.owner, row.root, row.kind) for row in produced.root_capture_findings
    ] == [("common_etf_session_status", "evidence_store", "OWNER_ROOT_IS_CELL_VARIABLE")]
    assert [row.root for row in produced.module_identity_findings] == ["globals"] * 5
    assert {row.kind for row in produced.module_identity_findings} == {
        "MODULE_NAMESPACE_REACH"
    }
    with pytest.raises(witness.CompiledBindingWitnessError, match="compiled root binding forbidden"):
        witness.audit_compiled_binding_witness(source)


def test_current_production_is_still_refused_by_the_closed_ast_grammar() -> None:
    source = witness.CALENDAR_SOURCE.read_text(encoding="utf-8")
    with pytest.raises(narrow.NormalFormError, match="FORBIDDEN_NESTED_SCOPE_CAPTURE"):
        narrow.audit_store_capability_normal_form(source)
    assert witness.verify_current_production_expected_result(source) == {
        "compiled_binding_witness": "BINDING_PROOF_COMPATIBLE",
        "unexpected_root_rebinding": "NONE",
        "root_write_clear_or_delete_findings": 0,
        "ast_direct_use_grammar": "REFUSED",
        "expected_generator_blocker": True,
        "blocking_owner": "common_etf_session_status",
        "blocking_root": "evidence_store",
        "both_layers_refuse_the_same_single_construct": True,
        "module_namespace_reach_sites": [
            "<module>:_children:globals",
            "<module>:_install_exact_dependency_guards:globals",
            "<module>:_semantic_ast_sha256:globals",
            "<module>:restore_artifacts:globals",
            "<module>:write_artifacts:globals",
        ],
    }


def test_direct_body_and_startup_contracts_are_preserved() -> None:
    rule = witness.direct_body_dependency_rule()
    assert rule["required_direct_bodies"] == [
        "CalendarEvidenceStore.put",
        "CalendarEvidenceStore.get",
        "CalendarEvidenceStore.records",
        "CalendarEvidenceStore.envelopes",
        "collect_official_calendar",
    ]
    assert rule["exact_dependency_assertion"] == "assert_trusted_persistence_dependency"
    assert rule["wrapper_installed_guards_permitted"] is False
    assert rule["startup_check_replaces_five_direct_checks"] is False
    assert "FROZEN_PROOF_INTERPRETER_IDENTITY" in rule["startup_self_check"]


def test_three_guarantees_stay_separate() -> None:
    definition = witness.proof_order_and_completeness_definition()
    assert definition["separate_guarantees"] == {
        "compiled_binding_witness": "FROZEN_ROOT_IS_NOT_REBOUND_OR_DELETED",
        "ast_normal_form": "PERMITTED_STORE_USES_ONLY",
        "replay_owner_graph": "REPLAY_ROUTE_CLOSURE",
    }
    assert definition["bytecode_proves_all_program_semantics"] is False
    assert definition[
        "manually_maintained_ast_node_list_frozen_as_complete_python_312_binding_set"
    ] is False
    assert definition["current_production_expected_result"]["calendar_implementation"] == "BLOCKED"


# ---------------------------------------------------------------------------
# Lineage, safety, mutation sensitivity and determinism
# ---------------------------------------------------------------------------


def test_failed_and_calendar_lineages_are_preserved_unchanged() -> None:
    safety = witness.science_lineage_and_safety()
    assert [row["definition_sha256"] for row in safety["failed_architecture_lineage"]] == [
        "0c237c1b217b1fd406ec3967309774293c01d3e27574b9f4a7d1b9a0e887b55d",
        "a7d2b08741080494cc4ca0269bf21e28e631c7f2e70887bcb0e1beb302534dd0",
        "dc36ffe228b7a3bc6d9145042b4e301c8624c99a79d71a88b46fc268f1372c3e",
        "9f6af1794e8b49dce38288b9f1b9710bffd04ba70303b5c380e8fb447ac86295",
        "7ef114fede9efebe594f0ecf119d097a1161119f448737d0df10afdf9468d17b",
    ]
    assert all(
        row["failed"]
        and not row["certified"]
        and not row["used"]
        and row["prospective_observations"] == 0
        and row["superseded_before_use"]
        for row in safety["failed_architecture_lineage"]
    )
    assert safety["failed_calendar_lineage"] == [
        "a1ceb66bc0f6b90066d3da123447ae6e7dd983047adf363790336bfb557db0b9",
        "b81c1702c65e1e042b7a2f948216305618fd21fabe2e629edc46376882b357af",
        "0524334396e529afbd057db25721b92c3074dd10205dd08be0946e512f99c855",
        "b499c6a4d1a8a6c25c6b108279831f26508742de97bdbcd57c7bee58e584e076",
        "901f572e03781030906cd6fe72a73ec5804f9ffbdefe6a8a944c067f7fd9853f",
    ]
    assert safety["preserved_hashes"] == {
        "certified_prospective_v1": (
            "8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7"
        ),
        "failed_prospective_v2": (
            "488251df7bc1b49f801caa0dc28eb5224836574b154db9e4a70d4be670ec0b6d"
        ),
    }
    assert safety["certified_dependency"]["definition_sha256"] == (
        "02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772"
    )
    assert safety["certified_dependency"]["changed"] is False
    assert set(safety["preserved_science"].values()) == {"UNCHANGED"}
    assert safety["safety"]["prospective_observations"] == 0
    assert safety["safety"]["real_stage_b_evaluation"] is False
    assert safety["safety"]["collection_authorized"] is False
    assert safety["safety"]["calendar_certified"] is False
    assert safety["safety"]["btc019"] == "UNTOUCHED"
    assert safety["safety"]["epic_t"] == "UNCHANGED"
    assert safety["safety"]["trusted_persistence"] == "CLOSED_UNCHANGED"


def test_failed_pad1_artifacts_are_not_mutated() -> None:
    failed_dir = ROOT / narrow.OUTPUT_NAMESPACE
    assert narrow.restore_artifacts(failed_dir)["definition_sha256"] == (
        "7ef114fede9efebe594f0ecf119d097a1161119f448737d0df10afdf9468d17b"
    )
    assert ARTIFACT_DIR != failed_dir


@pytest.mark.parametrize(
    ("builder", "field"),
    [
        ("compiled_binding_witness_definition", "root_write_opcodes"),
        ("compiled_binding_witness_definition", "root_delete_opcodes"),
        ("compiled_binding_witness_definition", "root_target_rule"),
        ("proof_interpreter_identity", "frozen_identity"),
        ("owner_code_object_identity_rule", "identity_components"),
        ("dynamic_execution_prohibition", "forbidden_names_in_replay_owners"),
        ("store_root_and_direct_use_grammar", "transparent_aliases_permitted"),
        ("nested_owner_and_capability_escape_rule", "rootless_outer_can_hide_nested_owner"),
        ("replay_owner_graph_rule", "cycles_permitted"),
        ("proof_order_and_completeness_definition", "proof_order"),
        ("direct_body_dependency_rule", "startup_self_check"),
        ("trusted_process_boundary_reference", "failed_boundary_lineage"),
        ("science_lineage_and_safety", "failed_calendar_lineage"),
    ],
)
def test_material_mutations_move_child_and_parent_hash(builder: str, field: str) -> None:
    original_child = getattr(witness, builder)()
    payload = copy.deepcopy(original_child)
    payload.pop("definition_sha256")
    value = payload[field]
    if isinstance(value, list):
        value.append("MUTATED")
    elif isinstance(value, dict):
        value["MUTATED"] = True
    elif isinstance(value, bool):
        payload[field] = not value
    else:
        payload[field] = f"{value}_MUTATED"
    mutated_child = witness._definition(payload)
    assert mutated_child["definition_sha256"] != original_child["definition_sha256"]
    parent = witness.compiled_binding_witness_v1_definition()
    parent_payload = copy.deepcopy(parent)
    parent_payload.pop("definition_sha256")
    parent_payload["child_definition_sha256"][builder] = mutated_child["definition_sha256"]
    assert witness._definition(parent_payload)["definition_sha256"] != parent["definition_sha256"]


def test_artifacts_reproduce_under_child_order_and_tampering_refuses(tmp_path: Path) -> None:
    assert witness.restore_artifacts(ARTIFACT_DIR) == (
        witness.compiled_binding_witness_v1_definition()
    )
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first = witness.write_artifacts(first_dir)
    second = witness.write_artifacts(second_dir, tuple(reversed(witness._CHILD_ARTIFACTS)))
    assert first == second
    assert {path.name: path.read_bytes() for path in first_dir.iterdir()} == {
        path.name: path.read_bytes() for path in second_dir.iterdir()
    }
    child_path = first_dir / "compiled_binding_witness_definition.json"
    child = json.loads(child_path.read_text(encoding="ascii"))
    child["root_write_opcodes"] = []
    child_path.write_text(json.dumps(child, indent=2, sort_keys=True) + "\n", encoding="ascii")
    with pytest.raises(witness.CompiledBindingWitnessError, match="does not reproduce"):
        witness.restore_artifacts(first_dir)


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
            str(FROZEN_PYTHON),
            "-m",
            "btc_predictor.research.etf_calendar_compiled_binding_witness",
            str(output),
        ],
        cwd=tmp_path,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    expected = witness.compiled_binding_witness_v1_definition()
    assert completed.stdout.strip() == expected["definition_sha256"]
    assert witness.restore_artifacts(output) == expected
