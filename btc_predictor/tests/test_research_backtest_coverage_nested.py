"""RBT-002 correction R2 (policy V5 section 5A.1, 5A.5 and 5A.7).

These tests pin:

- discovery of every nested, local and private callable defined inside a
  reached callable, with its qualified name, parameters, defaults and call
  sites, cross-checked against an independent walk of the live code objects;
- each one's ``OWNER_INTERNAL``/``EXTERNAL`` classification from its call-site
  AST, on the real owners (the trailing ``held`` helper among them) and on
  synthetic fixture owners exercising every rule;
- that an external nested callable is refused until each of its parameters
  is classified, and a changed classification is refused;
- the tracer without exemption: an executed nested frame is covered only by
  its own static record, and a live signature differing from the static
  census is reported;
- that every local function and lambda gaining a live parameter is refused;
- the census's stated limits and measured coverage in the inventory.

Every fixture is synthetic and offline; no database or network is touched.
"""

from __future__ import annotations

import ast
import dataclasses
import functools
import importlib.util
import inspect
import json
import sys
import textwrap
import types
from pathlib import Path
from typing import Any

import pytest

from btc_predictor.research_backtest import coverage, input_census, input_census_registry
from btc_predictor.research_backtest.coverage import InputSurfaceError
from btc_predictor.tests import test_research_backtest_census_trace_g9_hold_add_trail_trim_exit as trailing_fixtures

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / coverage.ARTIFACT_DIRECTORY / coverage.INVENTORY_FILENAME
REPORT = ROOT / coverage.ARTIFACT_DIRECTORY / coverage.INVENTORY_REPORT_FILENAME
HELD = "btc_predictor.risk.trailing.calculate_trailing_stop.<locals>.held"
UNALLOCATED = "btc_predictor.risk.tranches.next_tranche_for_position.<locals>.unallocated"
FIXTURE_MODULE = "btc_predictor.rbt002_r2_nested_fixture"
FIXTURE_ROOT = f"{FIXTURE_MODULE}.nested_root"


@functools.cache
def _census() -> input_census.DecisionPathCensus:
    return input_census.discover_decision_path()


def _live_function(path: str) -> types.FunctionType:
    parts = path.split(".")
    index = next(i for i in range(len(parts), 0, -1) if ".".join(parts[:i]) in sys.modules)
    owner: Any = sys.modules[".".join(parts[:index])]
    for part in parts[index:]:
        owner = inspect.getattr_static(owner, part)
        if isinstance(owner, (staticmethod, classmethod)):
            owner = owner.__func__
        if isinstance(owner, property):
            owner = owner.fget
    return owner


def _nested_code(code: types.CodeType) -> list[types.CodeType]:
    found = []
    for constant in code.co_consts:
        if isinstance(constant, types.CodeType):
            found.append(constant)
            found.extend(_nested_code(constant))
    return found


# --- the real owners ------------------------------------------------------------------------


def test_every_nested_code_object_of_every_reached_callable_is_discovered() -> None:
    census = _census()
    live = []
    for path in census.callables:
        if path in census.nested:
            continue
        function = _live_function(path)
        module = function.__globals__["__name__"]
        live += [
            (module, code.co_qualname, input_census.code_source(code), input_census.code_column(code))
            for code in _nested_code(function.__code__)
        ]
    assert len(live) == len(set(live)) == len(census.nested) == 230
    assert set(live) == {record.code_key for record in census.nested.values()}


def test_the_nested_census_classifies_all_230_callables_as_owner_internal() -> None:
    census = _census()
    summary = census.summary()
    assert summary["callables"] == 882
    assert summary["nested_callables"] == 230
    assert summary["nested_callables_by_role"] == {
        input_census.ROLE_GENERATOR_EXPRESSION: 188,
        input_census.ROLE_LAMBDA: 40,
        input_census.ROLE_NESTED_FUNCTION: 2,
    }
    assert summary["nested_callables_by_classification"] == {input_census.NESTED_OWNER_INTERNAL: 230}
    assert summary["nested_callables_by_basis"] == {
        input_census.BASIS_DIRECT_CALLS: 2,
        input_census.BASIS_GENERATOR: 188,
        input_census.BASIS_BUILTIN_KEY: 40,
    }
    assert {path for path, record in census.nested.items() if record.role == input_census.ROLE_NESTED_FUNCTION} == {
        HELD,
        UNALLOCATED,
    }
    # every builtin key callback is applied by sorted, min or max to values the owner passes
    for record in census.nested.values():
        assert record.enclosing in census.callables
        assert record.call_sites, record.path
        if record.role == input_census.ROLE_LAMBDA:
            (site,) = record.call_sites
            assert site.form == input_census.FORM_BUILTIN_KEY and site.callee in ("sorted", "min", "max")
    assert input_census_registry.DISCOVERED_NESTED_CALLABLES == {
        path: (record.classification, record.basis) for path, record in census.nested.items()
    }
    assert coverage.EXTERNAL_NESTED_PARAMETER_CLASSIFICATIONS == {}


def test_the_trailing_held_helper_is_owner_internal_from_its_six_call_sites() -> None:
    census = _census()
    record = census.nested[HELD]
    assert record.qualname == "calculate_trailing_stop.<locals>.held"
    assert record.enclosing == "btc_predictor.risk.trailing.calculate_trailing_stop"
    assert record.role == input_census.ROLE_NESTED_FUNCTION
    assert record.classification == input_census.NESTED_OWNER_INTERNAL
    assert record.basis == input_census.BASIS_DIRECT_CALLS
    parameters = census.callables[HELD].parameters
    assert [(item.name, item.kind, item.has_default, item.default) for item in parameters] == [
        ("reason", "POSITIONAL_OR_KEYWORD", False, None),
        ("candidate", "KEYWORD_ONLY", True, "None"),
        ("complete", "KEYWORD_ONLY", True, "True"),
    ]
    assert len(record.call_sites) == 6
    assert all(site.form == input_census.FORM_DIRECT_CALL for site in record.call_sites)
    assert {(item.slot, item.basis) for site in record.call_sites for item in site.arguments} == {
        ("0", input_census.ARGUMENT_LITERAL),
        ("candidate", input_census.ARGUMENT_SCOPE_NAME),
        ("complete", input_census.ARGUMENT_LITERAL),
    }
    for name in ("candidate", "complete"):
        assert census.default_override(HELD, name) == (input_census.DEFAULT_OVERRIDDEN, (record.enclosing,))
    rows = [row for row in coverage.enumerate_input_surface(census) if row.owner == HELD]
    assert [row.name for row in rows] == ["candidate", "complete", "reason"]
    for row in rows:
        assert row.surface == coverage.SURFACE_NESTED_PARAMETER
        assert row.category == coverage.CATEGORY_NESTED_INTERNAL
        assert row.classification.kind == coverage.KIND_OWNER_INTERNAL
        assert row.classification.producing_owner == record.enclosing
        assert row.reached_from == record.enclosing
    unallocated = census.nested[UNALLOCATED]
    assert unallocated.basis == input_census.BASIS_DIRECT_CALLS and len(unallocated.call_sites) == 2
    assert census.callables[UNALLOCATED].parameter_names == ("reason",)


def test_executed_trailing_frames_match_their_own_nested_record() -> None:
    census = _census()
    executing = 0
    for thunk in trailing_fixtures.FIXTURES["btc_predictor.risk.trailing.trail_stop_for_position"]:
        _, traced = input_census.trace_owner_calls(thunk)
        assert input_census.uncovered_traced(census, traced) == {"functions": [], "dataclasses": []}
        executed = {code.key for code in traced.code if code.qualname.endswith("<locals>.held")}
        if not executed:
            continue  # the advancing fixture returns without the helper
        executing += 1
        assert executed == {census.nested[HELD].code_key}
        # without its own record the helper is reported, although its owner is in the census
        without = dataclasses.replace(
            census,
            callables={k: v for k, v in census.callables.items() if k != HELD},
            nested={k: v for k, v in census.nested.items() if k != HELD},
        )
        assert "btc_predictor.risk.trailing.calculate_trailing_stop" in without.callables
        uncovered = input_census.uncovered_traced(without, traced)["functions"]
        assert HELD in uncovered
        assert any(item.startswith(HELD + " at btc_predictor/risk/trailing.py:272") for item in uncovered)
    assert executing == 2


# --- synthetic fixture owners: every classification rule -----------------------------------------


@pytest.fixture()
def fixture_module(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(FIXTURE_MODULE, Path(__file__).with_name("rbt002_r2_nested_fixture_owners.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, FIXTURE_MODULE, module)
    spec.loader.exec_module(module)
    return module


def _fixture_census() -> input_census.DecisionPathCensus:
    root = input_census.DecisionPathRoot(FIXTURE_MODULE, "nested_root", input_census.AREA_LIFECYCLE, "R2 fixture")
    return input_census.discover_decision_path((root,))


def test_nested_callables_are_classified_from_their_call_sites(fixture_module: types.ModuleType) -> None:
    census = _fixture_census()
    local = FIXTURE_ROOT + ".<locals>."
    verdicts = {path[len(local) :]: (record.classification, record.basis) for path, record in census.nested.items()}
    internal, external = input_census.NESTED_OWNER_INTERNAL, input_census.NESTED_EXTERNAL
    assert verdicts == {
        "internal": (internal, input_census.BASIS_DIRECT_CALLS),
        "computed": (external, input_census.BASIS_COMPUTED_ARGUMENT),
        "escapes": (external, input_census.BASIS_ESCAPES),
        "unpacked": (external, input_census.BASIS_UNPACKED_ARGUMENT),
        "decorated": (external, input_census.BASIS_DECORATED),
        "rebound": (external, input_census.BASIS_REBOUND),
        "wrapper": (internal, input_census.BASIS_DIRECT_CALLS),
        "wrapper.<locals>.<lambda>#1": (internal, input_census.BASIS_BUILTIN_KEY),
        "Local": (external, input_census.BASIS_LOCAL_CLASS),
        "Local.method": (external, input_census.BASIS_LOCAL_CLASS),
        "<lambda>#1": (internal, input_census.BASIS_DIRECT_CALLS),  # assigned, called with a literal
        "<lambda>#2": (internal, input_census.BASIS_BUILTIN_KEY),  # key= of builtin sorted
        "<lambda>#3": (external, input_census.BASIS_ESCAPES),  # key= of a package function
        "<genexpr>#1": (internal, input_census.BASIS_GENERATOR),
        "<genexpr>#2": (internal, input_census.BASIS_GENERATOR),  # inside an inlined list comprehension
    }
    record = census.nested[local + "internal"]
    assert [site.line for site in record.call_sites] == sorted(site.line for site in record.call_sites)
    assert [[(item.slot, item.basis) for item in site.arguments] for site in record.call_sites] == [
        [("0", input_census.ARGUMENT_LITERAL)],
        [("0", input_census.ARGUMENT_LITERAL), ("flag", input_census.ARGUMENT_LITERAL)],
        [("0", input_census.ARGUMENT_LITERAL), ("flag", input_census.ARGUMENT_SCOPE_NAME)],
    ]
    assert census.callables[local + "internal"].parameter_names == ("reason", "flag")
    assert census.callables[local + "unpacked"].parameters[0].kind == "VAR_POSITIONAL"
    assert census.callables[local + "<genexpr>#1"].parameter_names == (".0",)
    assert census.default_override(local + "internal", "flag")[0] == input_census.DEFAULT_OVERRIDDEN
    # an external callable's default is never fixed, even though its one direct call omits it
    assert [site.callee for site in census.nested[local + "computed"].call_sites] == ["computed"]
    assert census.default_override(local + "computed", "scale")[0] == input_census.DEFAULT_UNRESOLVED


def test_executed_nested_frames_are_checked_without_an_ancestor_exemption(fixture_module: types.ModuleType) -> None:
    census = _fixture_census()
    _, traced = input_census.trace_owner_calls(lambda: fixture_module.nested_root([3, 1, 2], lambda f: f(5)))
    executed = {f"{code.module}.{code.qualname}" for code in traced.code}
    assert FIXTURE_ROOT + ".<locals>.internal" in executed
    assert FIXTURE_ROOT + ".<locals>.wrapper.<locals>.<lambda>" in executed
    assert input_census.uncovered_traced(census, traced) == {"functions": [], "dataclasses": []}
    for name in ("internal", "<genexpr>#2", "wrapper.<locals>.<lambda>#1", "Local.method"):
        path = f"{FIXTURE_ROOT}.<locals>.{name}"
        without = dataclasses.replace(
            census,
            callables={k: v for k, v in census.callables.items() if k != path},
            nested={k: v for k, v in census.nested.items() if k != path},
        )
        uncovered = input_census.uncovered_traced(without, traced)["functions"]
        assert any(item.startswith(path.split("#")[0] + " at ") for item in uncovered), name
        # the path-only trace (functions without code identity) is not exempted either
        if "#" not in name:
            plain = input_census.TracedCalls(traced.functions, traced.dataclasses)
            assert input_census.uncovered_traced(without, plain)["functions"] == [path]


# --- refusals ---------------------------------------------------------------------------------------


def _with_nested(census: input_census.DecisionPathCensus, record: input_census.NestedCallable) -> input_census.DecisionPathCensus:
    return dataclasses.replace(census, nested={**census.nested, record.path: record})


def test_a_changed_nested_classification_is_refused() -> None:
    census = _census()
    changed = dataclasses.replace(census.nested[HELD], classification=input_census.NESTED_EXTERNAL, basis=input_census.BASIS_ESCAPES)
    with pytest.raises(InputSurfaceError) as raised:
        coverage._require_classified_census(_with_nested(census, changed))
    assert raised.value.code == "NESTED_CLASSIFICATION_CHANGED"


def test_a_new_nested_callable_is_refused() -> None:
    census = _census()
    path = "btc_predictor.risk.trailing.calculate_trailing_stop.<locals>.new_helper"
    record = dataclasses.replace(census.nested[HELD], path=path)
    grown = dataclasses.replace(
        _with_nested(census, record), callables={**census.callables, path: dataclasses.replace(census.callables[HELD], path=path)}
    )
    with pytest.raises(InputSurfaceError) as raised:
        coverage._require_classified_census(grown)
    assert raised.value.code == "UNCLASSIFIED_CALLABLE"


def test_an_external_nested_callable_needs_every_parameter_classified(monkeypatch: pytest.MonkeyPatch) -> None:
    census = _census()
    template = next(row.classification for row in coverage.enumerate_input_surface(census) if row.owner == HELD)
    external = dataclasses.replace(census.nested[HELD], classification=input_census.NESTED_EXTERNAL, basis=input_census.BASIS_ESCAPES)
    reviewed = {**input_census_registry.DISCOVERED_NESTED_CALLABLES, HELD: (input_census.NESTED_EXTERNAL, input_census.BASIS_ESCAPES)}
    monkeypatch.setattr(input_census_registry, "DISCOVERED_NESTED_CALLABLES", reviewed)
    mutated = _with_nested(census, external)
    with pytest.raises(InputSurfaceError) as raised:
        coverage._require_classified_census(mutated)
    assert raised.value.code == "UNCLASSIFIED_PARAMETER"
    assert "reason" in str(raised.value)
    partial = {"reason": template, "candidate": template}
    monkeypatch.setattr(coverage, "EXTERNAL_NESTED_PARAMETER_CLASSIFICATIONS", {HELD: partial})
    with pytest.raises(InputSurfaceError) as raised:
        coverage._require_classified_census(mutated)
    assert raised.value.code == "UNCLASSIFIED_PARAMETER" and "complete" in str(raised.value)
    monkeypatch.setattr(coverage, "EXTERNAL_NESTED_PARAMETER_CLASSIFICATIONS", {HELD: {**partial, "complete": template}})
    rows = [row for row in coverage.enumerate_input_surface(mutated) if row.owner == HELD]
    assert {row.category for row in rows} == {coverage.CATEGORY_NESTED_EXTERNAL}
    monkeypatch.setattr(coverage, "EXTERNAL_NESTED_PARAMETER_CLASSIFICATIONS", {HELD: {**partial, "complete": template}, UNALLOCATED: {}})
    with pytest.raises(InputSurfaceError) as raised:
        coverage._require_classified_census(mutated)
    assert raised.value.code == "STALE_CLASSIFICATION"


def _with_new_parameter(function: types.FunctionType, record: input_census.NestedCallable) -> types.CodeType:
    """Recompile ``function`` with one nested def or lambda gaining a used keyword-only parameter."""

    tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
    ast.increment_lineno(tree, function.__code__.co_firstlineno - 1)
    line = int(record.source.rsplit(":", 1)[1])
    if record.role == input_census.ROLE_NESTED_FUNCTION:
        node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == record.qualname.rsplit(".", 1)[1])
    else:
        node = next(
            n for n in ast.walk(tree)
            if isinstance(n, ast.Lambda)
            and n.lineno == line
            and (n.lineno, n.col_offset) <= (line, record.column) < (n.end_lineno, n.end_col_offset)
        )
    node.args.kwonlyargs.append(ast.arg(arg="independent_new_input"))
    node.args.kw_defaults.append(ast.Constant(None))
    ast.fix_missing_locations(tree)
    namespace = dict(function.__globals__)
    exec(compile(tree, function.__code__.co_filename, "exec"), namespace)  # noqa: S102 - owner source, recompiled in memory
    return namespace[function.__name__].__code__


def test_every_local_function_and_lambda_gaining_a_live_parameter_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    census = _census()
    mutable = [record for record in census.nested.values() if record.role in (input_census.ROLE_NESTED_FUNCTION, input_census.ROLE_LAMBDA)]
    assert len(mutable) == 42
    for record in mutable:
        function = _live_function(record.enclosing)
        assert input_census.owner_path(function) == record.enclosing and "." not in function.__qualname__
        with monkeypatch.context() as patch:
            patch.setattr(function, "__code__", _with_new_parameter(function, record))
            module, qualname = record.enclosing.rsplit(".", 1)
            root = input_census.DecisionPathRoot(module, qualname, input_census.AREA_LIFECYCLE, "R2 live mutation")
            mutated = input_census.discover_decision_path((root,))
            assert mutated.callables[record.path].parameter_names[-1] == "independent_new_input", record.path
            # the live code no longer matches its source, so it fails closed as external
            assert mutated.nested[record.path].basis == input_census.BASIS_LIVE_CODE_DIFFERS
            with pytest.raises(InputSurfaceError) as raised:
                coverage._require_exact_names(
                    record.path,
                    mutated.callables[record.path].parameter_names,
                    input_census_registry.DISCOVERED_CALLABLES[record.path],
                    unclassified="UNCLASSIFIED_PARAMETER",
                )
            assert raised.value.code == "UNCLASSIFIED_PARAMETER" and "independent_new_input" in str(raised.value)
    # end to end through the full enumeration, for a local function and a lambda
    for path in (UNALLOCATED, "btc_predictor.risk.reward.select_reward_reference.<locals>.<lambda>#1"):
        record = census.nested[path]
        function = _live_function(record.enclosing)
        with monkeypatch.context() as patch:
            patch.setattr(function, "__code__", _with_new_parameter(function, record))
            with pytest.raises(InputSurfaceError, match="UNCLASSIFIED_PARAMETER.*independent_new_input"):
                coverage.enumerate_input_surface()


# --- stated limits ------------------------------------------------------------------------------------


def test_the_census_states_its_limits_with_measured_coverage() -> None:
    limits = input_census.census_limits()
    assert [item["limit"] for item in limits["known_limits"]] == [
        "ENCLOSING_LOCAL_CALLBACKS",
        "UNNAMED_PROTOCOL_IMPLEMENTATIONS",
        "DYNAMIC_GETATTR_DISPATCH",
        "UNEXECUTED_BRANCHES",
    ]
    assert "static discovery plus the runtime trace" in limits["claim"] and "no exemption" in limits["claim"]
    assert "section 5A.6" in limits["backstop"] and "RBT-004, RBT-005 and RBT-006" in limits["backstop"]
    runs = {run["run"]: run for run in limits["measured_coverage"]["runs"]}
    assert set(runs) == {"fixture runs", "owner tests"}
    for run in runs.values():
        for name in ("reached_lines", "reached_branches", "module_lines", "module_branches"):
            measured = run[name]
            assert 0 < measured["covered"] <= measured["total"]
            assert measured["percent"] == f"{100 * measured['covered'] / measured['total']:.2f}"
    inventory = json.loads(INVENTORY.read_bytes())
    assert inventory["policy"] == "RESEARCH_BACKTEST_POLICY_V5"
    assert inventory["input_surface"]["census"]["limits"] == json.loads(json.dumps(limits))
    nested = {item["path"]: item for item in inventory["input_surface"]["census"]["nested_callables"]}
    assert len(nested) == 230 and nested[HELD]["basis"] == input_census.BASIS_DIRECT_CALLS
    assert [item["name"] for item in nested[HELD]["parameters"]] == ["reason", "candidate", "complete"]
    report = REPORT.read_text(encoding="utf-8")
    assert "## Census limits (policy V5 section 5A.5)" in report
    assert all(item["limit"] in report for item in limits["known_limits"])
