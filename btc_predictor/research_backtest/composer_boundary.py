"""Census call boundary for the EPIC Y champion composers (policy V7 section 5A.6).

RBT-002 re-review finding E4 requires every decision owner function a composer
calls directly to be a census root, proven two ways. This module provides both
proofs; RBT-004 applies them to ``entry_composer`` and RBT-005 can reuse them.

- **Static, alias-resolving call census** (:func:`static_call_census`). The
  composer module's AST is read, and every call target is resolved in the
  module's live namespace, so an aliased import resolves to the real owner
  object. Each call is classified as a census root, a classified input source
  (``input_census.CLASSIFIED_INPUT_SOURCES``), an explicitly classified
  constructor, a type-bound serializer or accessor, a composer-local helper, a
  builtin or a standard-library call. Everything else is refused:
  - an owner function that is not a root;
  - a callable held in a local variable, container or subscript (callback or
    dict dispatch);
  - ``getattr``, ``functools.partial``, ``operator`` getters, ``eval``/``exec``
    and ``importlib`` dispatch;
  - an owner function or constructor used as a value rather than called.
- **Runtime direct-caller check** (:func:`trace_direct_calls`). A profiler
  records every ``btc_predictor`` function entered, and every owner dataclass
  constructed, directly from a frame of the composer file. Pure-Python
  standard-library frames between them are walked past, so ``dataclasses.replace``
  cannot hide a constructor. :func:`direct_call_violations` then requires each
  recorded call to be a root, an input source or an explicit allowance.

Allowances (each classified here and nowhere else):
- constructors of the composer-facing owner input types (their fields are
  classified in ``coverage.INPUT_TYPE_FIELD_CLASSIFICATIONS``) and the BTC-180
  ``BacktestIntent`` the backtest adapter returns;
- the type-bound evidence serializer ``as_record`` of an owner record (owner
  outputs still come from roots). The entry composer also reads a replay
  record's ``available_at`` and ``observation_time`` through it, exactly as the
  positioning owners' own inline point-in-time predicate does;
- the champion configuration's identity accessor ``StrategyConfig.run_metadata``
  and the engine's ``BacktestContext.position_open`` view.
"""

from __future__ import annotations

import ast
import builtins
import dataclasses
import functools
import inspect
import sys
import types
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from btc_predictor.research_backtest import input_census as census_owner

COMPOSER_BOUNDARY_VERSION = "COMPOSER_CENSUS_CALL_BOUNDARY_V1"

KIND_ROOT = "CENSUS_ROOT"
KIND_INPUT_SOURCE = "CLASSIFIED_INPUT_SOURCE"
KIND_CONSTRUCTOR = "CLASSIFIED_CONSTRUCTOR"
KIND_SERIALIZER = "TYPE_BOUND_SERIALIZER"
KIND_ACCESSOR = "CLASSIFIED_ACCESSOR"
KIND_LOCAL = "COMPOSER_LOCAL"
KIND_EPIC_Y = "EPIC_Y_NON_OWNER_HELPER"
KIND_BUILTIN = "BUILTIN"
KIND_STDLIB = "STANDARD_LIBRARY"
KIND_VALUE_METHOD = "VALUE_METHOD"

REFUSED_NOT_A_ROOT = "OWNER_FUNCTION_IS_NOT_A_CENSUS_ROOT"
REFUSED_CONSTRUCTOR = "UNCLASSIFIED_OWNER_CONSTRUCTOR"
REFUSED_DYNAMIC = "DYNAMIC_DISPATCH"
REFUSED_UNRESOLVED = "UNRESOLVED_CALLABLE"
REFUSED_VALUE_METHOD = "UNCLASSIFIED_METHOD_CALL"
REFUSED_OWNER_AS_VALUE = "OWNER_CALLABLE_USED_AS_A_VALUE"
REFUSED_FOREIGN = "UNCLASSIFIED_PACKAGE_CALLABLE"

# Composer-facing owner input types (classified field by field in
# coverage.INPUT_TYPE_FIELD_CLASSIFICATIONS) and the engine intent: the only
# owner classes a composer may construct directly.
ALLOWED_CONSTRUCTORS: Mapping[str, str] = {
    "btc_predictor.features.trend.TrendScoreInput": "Rulebook 5.2 trend input, fields classified by the inventory",
    "btc_predictor.features.flow.FlowScoreInput": "Rulebook 6.2 flow input, fields classified by the inventory",
    "btc_predictor.features.positioning.PositioningScoreInput": "Rulebook 7.5 positioning input, fields classified",
    "btc_predictor.features.positioning.CrowdingFlagInput": "Rulebook 24 CROWDING input, fields classified",
    "btc_predictor.features.volatility.OrderlinessScoreInput": "Rulebook 8.1 orderliness input, fields classified",
    "btc_predictor.features.volatility.VolatilityScoreInput": "Rulebook 8 volatility input, fields classified",
    "btc_predictor.features.volatility.StressFlagInput": "Rulebook 24 STRESS input, fields classified",
    "btc_predictor.features.volatility.CapitulationFlagInput": "Rulebook 24 CAPITULATION input, fields classified",
    "btc_predictor.features.volatility.EuphoriaFlagInput": "Rulebook 24 EUPHORIA input, fields classified",
    "btc_predictor.features.regime.RegimeScoreInput": "Rulebook 10 core regime input, fields classified",
    "btc_predictor.features.regime.RegimeSmoothingInput": "Rulebook 10 smoothing input, fields classified",
    "btc_predictor.features.entry.EntryConvictionInput": "Rulebook 13 Entry Conviction input, fields classified",
    "btc_predictor.features.setup.BullTrendContinuationInput": "Rulebook 11 Setup A input, fields classified",
    "btc_predictor.features.setup.BullishResetInput": "Rulebook 11 Setup B input, fields classified",
    "btc_predictor.features.setup.CapitulationReversalInput": "Rulebook 11 Setup C input, fields classified",
    "btc_predictor.features.setup.BearishDistributionInput": "Rulebook 11 Setup D input (inert), fields classified",
    "btc_predictor.signals.hard_veto.HardVetoInput": "Rulebook 14 hard-veto input, fields classified",
    "btc_predictor.backtest.engine.BacktestIntent": "the BTC-180 decision record the backtest adapter returns",
}
ALLOWED_SERIALIZER_NAMES: frozenset[str] = frozenset({"as_record"})
ALLOWED_ACCESSORS: Mapping[str, str] = {
    "btc_predictor.config.strategy.StrategyConfig.run_metadata": "the champion configuration's identity metadata",
    "btc_predictor.backtest.engine.BacktestContext.position_open": "the engine's point-in-time position view",
}
# Methods of builtin and standard-library values (list, dict, set, str, tuple,
# Decimal, date, datetime) a composer may call; none reaches owner code.
ALLOWED_VALUE_METHODS: frozenset[str] = frozenset(
    {
        "append", "extend", "add", "update", "get", "items", "keys", "values", "setdefault", "pop", "sort",
        "index", "count", "copy", "join", "split", "startswith", "endswith", "lower", "upper", "strip",
        "format", "isoformat", "date", "replace", "astimezone", "total_seconds", "is_finite", "as_tuple",
        "weekday", "utcoffset", "encode", "decode", "time", "__init__",
    }
)
# Refused dynamic-dispatch builtins and standard-library callables.
_REFUSED_BUILTINS = frozenset({"getattr", "setattr", "delattr", "eval", "exec", "compile", "__import__", "globals", "locals", "vars"})
_REFUSED_STDLIB = frozenset(
    {
        "functools.partial", "functools.partialmethod", "operator.attrgetter", "operator.methodcaller",
        "operator.itemgetter", "importlib.import_module", "importlib.__import__",
    }
)


class ComposerBoundaryError(ValueError):
    """The composer's call boundary cannot be established."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def census_roots() -> frozenset[str]:
    return frozenset(root.path for root in census_owner.DECISION_PATH_ROOTS)


def input_sources() -> frozenset[str]:
    return frozenset(source.path for source in census_owner.CLASSIFIED_INPUT_SOURCES)


@dataclass(frozen=True)
class StaticCall:
    line: int
    expression: str
    kind: str
    target: str


@dataclass(frozen=True)
class StaticRefusal:
    line: int
    expression: str
    reason: str
    target: str


@dataclass(frozen=True)
class StaticCallCensus:
    module: str
    calls: tuple[StaticCall, ...]
    refusals: tuple[StaticRefusal, ...]

    @property
    def roots_called(self) -> frozenset[str]:
        return frozenset(call.target for call in self.calls if call.kind == KIND_ROOT)

    @property
    def input_sources_called(self) -> frozenset[str]:
        return frozenset(call.target for call in self.calls if call.kind == KIND_INPUT_SOURCE)

    def as_record(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "version": COMPOSER_BOUNDARY_VERSION,
            "calls": [dataclasses.asdict(call) for call in self.calls],
            "refusals": [dataclasses.asdict(refusal) for refusal in self.refusals],
        }


def _path(obj: Any) -> str:
    return f"{getattr(obj, '__module__', '?')}.{getattr(obj, '__qualname__', getattr(obj, '__name__', '?'))}"


def _is_stdlib_module(name: str) -> bool:
    root = name.split(".", 1)[0]
    return root in sys.stdlib_module_names or root == "builtins"


def _in_package(name: str) -> bool:
    return name == "btc_predictor" or name.startswith("btc_predictor.")


def _is_epic_y(name: str) -> bool:
    return name == "btc_predictor.research_backtest" or name.startswith("btc_predictor.research_backtest.")


def _resolve(node: ast.AST, namespace: Mapping[str, Any]) -> Any:
    """The object a Name/Attribute chain names, or None when it is not static."""

    if isinstance(node, ast.Name):
        if node.id in namespace:
            return namespace[node.id]
        return getattr(builtins, node.id, None)
    if isinstance(node, ast.Attribute):
        base = _resolve(node.value, namespace)
        if base is None or not isinstance(base, (types.ModuleType, type)):
            return None
        try:
            value = inspect.getattr_static(base, node.attr)
        except AttributeError:
            return None
        if isinstance(value, (staticmethod, classmethod)):
            return value.__func__
        return value
    return None


def _module_local_callables(tree: ast.AST) -> tuple[frozenset[str], frozenset[str]]:
    functions: set[str] = set()
    methods: set[str] = set()
    for node in tree.body if isinstance(tree, ast.Module) else ():
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.add(node.name)
        elif isinstance(node, ast.ClassDef):
            functions.add(node.name)
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.add(item.name)
    return frozenset(functions), frozenset(methods)


def _classify_object(obj: Any, module_name: str) -> tuple[str | None, str, str]:
    """(accepted kind or None, refusal reason, target path) for a resolved callee."""

    if isinstance(obj, property):
        obj = obj.fget
    if isinstance(obj, functools.partial):
        return None, REFUSED_DYNAMIC, "functools.partial"
    target = _path(obj)
    owner_module = getattr(obj, "__module__", "") or ""
    objclass = getattr(obj, "__objclass__", None)
    if not owner_module and isinstance(objclass, type):
        # a builtin/standard-library method descriptor, such as datetime.combine
        owner_module = objclass.__module__
        target = f"{owner_module}.{objclass.__qualname__}.{getattr(obj, '__name__', '?')}"
    if isinstance(obj, types.BuiltinFunctionType) and owner_module == "builtins":
        if obj.__name__ in _REFUSED_BUILTINS:
            return None, REFUSED_DYNAMIC, f"builtins.{obj.__name__}"
        return KIND_BUILTIN, "", f"builtins.{obj.__name__}"
    if isinstance(obj, type) and owner_module == "builtins":
        return KIND_BUILTIN, "", f"builtins.{obj.__name__}"
    if f"{owner_module}.{getattr(obj, '__name__', '')}" in _REFUSED_STDLIB or target in _REFUSED_STDLIB:
        return None, REFUSED_DYNAMIC, target
    if owner_module == module_name:
        return KIND_LOCAL, "", target
    if target in input_sources():
        return KIND_INPUT_SOURCE, "", target
    if _in_package(owner_module):
        if _is_epic_y(owner_module):
            return KIND_EPIC_Y, "", target
        if isinstance(obj, type):
            if target in ALLOWED_CONSTRUCTORS:
                return KIND_CONSTRUCTOR, "", target
            return None, REFUSED_CONSTRUCTOR, target
        if target in census_roots():
            return KIND_ROOT, "", target
        if target in ALLOWED_ACCESSORS:
            return KIND_ACCESSOR, "", target
        if census_owner.in_scope_module(owner_module):
            return None, REFUSED_NOT_A_ROOT, target
        return None, REFUSED_FOREIGN, target
    if _is_stdlib_module(owner_module) or owner_module in ("decimal", "_decimal", "datetime", "_datetime"):
        return KIND_STDLIB, "", target
    return None, REFUSED_FOREIGN, target


def static_call_census(module: types.ModuleType) -> StaticCallCensus:
    """Classify every call in ``module`` and refuse any unresolved dispatch."""

    source = Path(module.__file__).read_text(encoding="utf-8")  # type: ignore[arg-type]
    tree = ast.parse(source)
    namespace = vars(module)
    local_functions, local_methods = _module_local_callables(tree)
    calls: list[StaticCall] = []
    refusals: list[StaticRefusal] = []
    call_funcs: set[int] = set()

    def text(node: ast.AST) -> str:
        return ast.unparse(node)[:160]

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        call_funcs.add(id(func))
        expression = text(func)
        if isinstance(func, ast.Name):
            if func.id in local_functions and func.id in namespace:
                kind, reason, target = _classify_object(namespace[func.id], module.__name__)
            elif func.id in namespace or hasattr(builtins, func.id):
                kind, reason, target = _classify_object(_resolve(func, namespace), module.__name__)
            else:
                kind, reason, target = None, REFUSED_UNRESOLVED, func.id
        elif isinstance(func, ast.Attribute):
            resolved = _resolve(func, namespace)
            if resolved is not None:
                kind, reason, target = _classify_object(resolved, module.__name__)
            elif func.attr in local_methods:
                kind, reason, target = KIND_LOCAL, "", f"<composer>.{func.attr}"
            elif func.attr in ALLOWED_SERIALIZER_NAMES:
                kind, reason, target = KIND_SERIALIZER, "", f"<record>.{func.attr}"
            elif func.attr == "run_metadata":
                kind, reason, target = KIND_ACCESSOR, "", "btc_predictor.config.strategy.StrategyConfig.run_metadata"
            elif func.attr in ALLOWED_VALUE_METHODS:
                kind, reason, target = KIND_VALUE_METHOD, "", f"<value>.{func.attr}"
            else:
                kind, reason, target = None, REFUSED_VALUE_METHOD, f"<value>.{func.attr}"
        else:
            kind, reason, target = None, REFUSED_DYNAMIC, expression
        if kind is None:
            refusals.append(StaticRefusal(node.lineno, expression, reason, target))
        else:
            calls.append(StaticCall(node.lineno, expression, kind, target))

    # An owner callable or classified constructor named anywhere except as a
    # call's function is a value (a callback, a dispatch-table entry, a partial
    # argument): refused, because the call site would not show its arguments.
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Name, ast.Attribute)) or id(node) in call_funcs:
            continue
        if not isinstance(getattr(node, "ctx", None), ast.Load):
            continue
        if isinstance(node, ast.Attribute) and isinstance(node.value, (ast.Name, ast.Attribute)) and id(node.value) in call_funcs:
            continue
        obj = _resolve(node, namespace)
        if obj is None or isinstance(obj, types.ModuleType):
            continue
        owner_module = getattr(obj, "__module__", "") or ""
        if not (_in_package(owner_module) and census_owner.in_scope_module(owner_module)):
            continue
        if isinstance(obj, (types.FunctionType, staticmethod, classmethod, functools.partial)):
            refusals.append(StaticRefusal(node.lineno, text(node), REFUSED_OWNER_AS_VALUE, _path(obj)))
    return StaticCallCensus(
        module=module.__name__,
        calls=tuple(sorted(calls, key=lambda call: (call.line, call.expression))),
        refusals=tuple(sorted(refusals, key=lambda refusal: (refusal.line, refusal.expression))),
    )


# --- runtime direct-caller check ------------------------------------------------------


@dataclass(frozen=True)
class DirectCall:
    kind: str  # "FUNCTION" or "CONSTRUCTOR"
    path: str


@functools.lru_cache(maxsize=None)
def _resolved_file(filename: str) -> str:
    return str(Path(filename).resolve()) if filename.endswith(".py") else filename


def _is_stdlib_file(filename: str) -> bool:
    if not filename.endswith(".py"):
        return False
    resolved = Path(_resolved_file(filename))
    return not census_owner._is_package_source(str(resolved)) and "site-packages" not in resolved.parts


def _direct_caller(frame: types.FrameType) -> types.FrameType | None:
    """The first caller frame that is not a pure-Python standard-library frame."""

    caller = frame.f_back
    while caller is not None and _is_stdlib_file(caller.f_code.co_filename):
        caller = caller.f_back
    return caller


def trace_direct_calls(thunk: Callable[[], Any], caller_file: str | Path) -> tuple[Any, frozenset[DirectCall]]:
    """Run ``thunk`` and record the package calls made directly from ``caller_file``."""

    target = _resolved_file(str(Path(caller_file)))
    found: set[DirectCall] = set()

    def profile(frame: types.FrameType, event: str, arg: Any) -> None:
        if event != "call":
            return
        caller = _direct_caller(frame)
        if caller is None or _resolved_file(caller.f_code.co_filename) != target:
            return
        code = frame.f_code
        if code.co_name == "__init__":
            instance = frame.f_locals.get("self")
            if instance is not None and dataclasses.is_dataclass(instance) and census_owner.in_scope_module(type(instance).__module__):
                found.add(DirectCall("CONSTRUCTOR", census_owner.owner_path(type(instance))))
                return
        if not census_owner._is_package_source(code.co_filename):
            return
        module = frame.f_globals.get("__name__")
        if isinstance(module, str) and _in_package(module) and _resolved_file(code.co_filename) != target:
            found.add(DirectCall("FUNCTION", f"{module}.{code.co_qualname}"))

    previous = sys.getprofile()
    sys.setprofile(profile)
    try:
        result = thunk()
    finally:
        sys.setprofile(previous)
    return result, frozenset(found)


def direct_call_violations(calls: Iterable[DirectCall]) -> tuple[str, ...]:
    """Every recorded direct call that is not a root, input source or allowance."""

    roots = census_roots()
    sources = input_sources()
    violations = []
    for call in sorted(calls, key=lambda item: (item.kind, item.path)):
        if call.kind == "CONSTRUCTOR":
            if call.path not in ALLOWED_CONSTRUCTORS:
                violations.append(f"CONSTRUCTOR {call.path}")
            continue
        module_part = call.path
        if _is_epic_y(module_part.rsplit(".", 1)[0]) or module_part.startswith("btc_predictor.research_backtest."):
            continue
        if call.path in roots or call.path in sources or call.path in ALLOWED_ACCESSORS:
            continue
        if call.path.rsplit(".", 1)[-1] in ALLOWED_SERIALIZER_NAMES:
            continue
        violations.append(f"FUNCTION {call.path}")
    return tuple(violations)
