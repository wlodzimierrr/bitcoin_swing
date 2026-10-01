"""RBT-002 correction R1: the section 5A census is discovered, not hand-listed.

These tests pin:

- the hand-written roots (the only list), each resolvable and justified, and
  equal to the classified root call sites;
- that every owner-module definition the roots do not reach is listed with a
  reason, and every other part of ``btc_predictor`` is out of owner scope with
  a reason;
- the review's reproducers: an owner type (``AnchoredVwapAnchor``,
  ``OhlcvQualityConfig``, ``DerivativesQualityConfig``) replaced in memory by a
  clone with one extra defaulted field, or a reached helper that gains a
  parameter, fails the enumeration; ``select_reward_reference``'s internal
  ``major_timeframes`` default has a row;
- universally, that adding a field to any reached type or a parameter to any
  reached callable, reaching a new owner, or no longer reaching one fails;
- the static walk's semantics on in-scope fixture code (local imports,
  callbacks, dispatch tables, partials, members, protocols, annotations) and
  the call-site default-override analysis.

Every fixture is synthetic and offline; no database or network is touched.
"""

from __future__ import annotations

import dataclasses
import functools
import importlib
import pkgutil
import sys
import types
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol

import pytest

import btc_predictor
from btc_predictor.data import quality as quality_owner
from btc_predictor.features._scoring import decimal_bounded_linear
from btc_predictor.levels import anchored_vwap as anchored_vwap_owner
from btc_predictor.research_backtest import coverage, input_census, input_census_registry
from btc_predictor.research_backtest.coverage import InputSurfaceError
from btc_predictor.risk import reward as reward_owner


@functools.cache
def _census() -> input_census.DecisionPathCensus:
    return input_census.discover_decision_path()


def _replace_everywhere(monkeypatch: pytest.MonkeyPatch, original: Any, replacement: Any) -> int:
    """Rebind ``original`` to ``replacement`` in every loaded btc_predictor module."""

    replaced = 0
    for name, module in sorted(sys.modules.items()):
        if not name.startswith("btc_predictor") or module is None:
            continue
        for attribute, value in list(vars(module).items()):
            if value is original:
                monkeypatch.setattr(module, attribute, replacement)
                replaced += 1
    assert replaced, f"{original!r} is bound nowhere"
    return replaced


def _clone_with_extra_defaulted_field(owner: type) -> type:
    fields = [(item.name, item.type, item) for item in dataclasses.fields(owner)]
    clone = dataclasses.make_dataclass(
        owner.__name__,
        [*fields, ("new_owner_input", "Decimal | None", dataclasses.field(default=None))],
        frozen=True,
        module=owner.__module__,
    )
    clone.__qualname__ = owner.__qualname__
    return clone


# --- roots ------------------------------------------------------------------------------


def test_every_root_resolves_and_is_justified() -> None:
    roots = input_census.DECISION_PATH_ROOTS
    assert len({root.path for root in roots}) == len(roots)
    for root in roots:
        function = root.resolve()
        assert input_census.owner_path(function) == root.path
        assert root.justification.strip()
        assert root.area in input_census.ROOT_AREAS
    assert {root.area for root in roots} == set(input_census.ROOT_AREAS)


def test_the_classified_root_call_sites_are_exactly_the_roots() -> None:
    assert set(coverage.ROOT_PARAMETER_CLASSIFICATIONS) == {root.path for root in input_census.DECISION_PATH_ROOTS}


def test_a_missing_root_is_refused() -> None:
    root = input_census.DecisionPathRoot("btc_predictor.risk.reward", "no_such_owner", input_census.AREA_RISK_GEOMETRY, "x")
    with pytest.raises(input_census.CensusError) as raised:
        input_census.discover_decision_path((root,))
    assert raised.value.code == "ROOT_NOT_FOUND"


def test_each_root_area_from_the_review_is_covered() -> None:
    paths = {root.path for root in input_census.DECISION_PATH_ROOTS}
    for required in (
        "btc_predictor.features.entry.calculate_entry_conviction",
        "btc_predictor.features.regime.calculate_regime_smoothing",
        "btc_predictor.features.volatility.calculate_stress_flag",
        "btc_predictor.features.positioning.calculate_crowding_flag",
        "btc_predictor.signals.hard_veto.evaluate_hard_veto",
        "btc_predictor.signals.data_quality.apply_data_quality_gate",
        "btc_predictor.features.setup.detect_bull_trend_continuation",
        "btc_predictor.signals.reclaim.evaluate_reclaim_trigger",
        "btc_predictor.risk.invalidation.select_structural_invalidation",
        "btc_predictor.risk.reward.reward_risk_for_stop",
        "btc_predictor.risk.budget.calculate_risk_budget",
        "btc_predictor.portfolio.state_machine.apply_position_event",
        "btc_predictor.signals.exit_rules.exit_rules_for_position",
        "btc_predictor.levels.anchored_vwap.calculate_anchored_vwaps",
        "btc_predictor.levels.clustering.cluster_price_levels",
    ):
        assert required in paths


def test_every_root_has_runtime_trace_fixtures() -> None:
    """The runtime cross-check (test_research_backtest_census_trace_*) runs every root."""

    import btc_predictor.tests as tests_package

    names = sorted(
        info.name
        for info in pkgutil.iter_modules(tests_package.__path__)
        if info.name.startswith("test_research_backtest_census_trace_")
    )
    assert len(names) == 9
    fixtures: dict[str, Any] = {}
    for name in names:
        module = importlib.import_module(f"btc_predictor.tests.{name}")
        assert not set(module.FIXTURES) & set(fixtures)
        fixtures.update(module.FIXTURES)
    assert set(fixtures) == {root.path for root in input_census.DECISION_PATH_ROOTS}
    assert all(len(thunks) >= 1 for thunks in fixtures.values())


# --- the census and its pinned snapshot ---------------------------------------------------


def test_the_census_reaches_what_the_registry_omitted() -> None:
    census = _census()
    for path in (
        "btc_predictor.levels.anchored_vwap.AnchoredVwapAnchor",
        "btc_predictor.data.quality.OhlcvQualityConfig",
        "btc_predictor.data.quality.DerivativesQualityConfig",
        "btc_predictor.config.strategy.StrategyConfig",
    ):
        assert path in census.types
    assert len(census.types["btc_predictor.levels.anchored_vwap.AnchoredVwapAnchor"].fields) == 13
    assert len(census.types["btc_predictor.data.quality.OhlcvQualityConfig"].fields) == 4
    assert len(census.types["btc_predictor.data.quality.DerivativesQualityConfig"].fields) == 6
    assert "btc_predictor.risk.reward.select_reward_reference" in census.callables
    assert census.sourceless == ()


def test_the_census_is_deterministic() -> None:
    first, second = _census(), input_census.discover_decision_path()
    assert first.callables == second.callables
    assert first.types == second.types
    assert first.references == second.references
    assert first.call_sites == second.call_sites


def test_the_pinned_snapshot_equals_the_discovered_census_both_ways() -> None:
    census = _census()
    rows = coverage.enumerate_input_surface(census)
    assert set(input_census_registry.DISCOVERED_TYPES) | set(coverage.INPUT_TYPE_FIELD_CLASSIFICATIONS) == set(census.types)
    assert not set(input_census_registry.DISCOVERED_TYPES) & set(coverage.INPUT_TYPE_FIELD_CLASSIFICATIONS)
    internal = set(census.callables) - set(census.root_paths)
    assert set(input_census_registry.DISCOVERED_CALLABLES) == internal
    for path, (_, fields, _) in input_census_registry.DISCOVERED_TYPES.items():
        assert fields == census.types[path].fields
    for path, names in input_census_registry.DISCOVERED_CALLABLES.items():
        assert names == census.callables[path].parameter_names
    expected = sum(len(item.fields) for item in census.types.values()) + sum(
        len(item.parameters) for item in census.callables.values()
    )
    assert len(rows) == expected


def test_every_unreached_owner_definition_is_left_out_with_a_reason() -> None:
    unreached = input_census.unreached_owner_definitions(_census())
    assert set(unreached) == set(input_census.LEFT_OUT_OWNER_DEFINITIONS)
    assert all(reason.strip() for reason in input_census.LEFT_OUT_OWNER_DEFINITIONS.values())
    # the generic rolling helpers stay candidates for the completion spec, not inputs
    assert "btc_predictor.features.rolling.rolling_zscore" in input_census.LEFT_OUT_OWNER_DEFINITIONS


def test_every_part_of_the_package_is_owner_scope_or_out_of_scope_with_a_reason() -> None:
    top_level = {f"btc_predictor.{info.name}" for info in pkgutil.iter_modules(btc_predictor.__path__)}
    in_scope = set(input_census.DECISION_PATH_OWNER_PACKAGES)
    assert top_level == in_scope | set(input_census.OUTSIDE_OWNER_SCOPE)
    assert not in_scope & set(input_census.OUTSIDE_OWNER_SCOPE)
    for module in input_census.DECISION_PATH_OWNER_MODULES:
        importlib.import_module(module)


# --- the review's reproducers (fail on the original registry, pass on the census) ------------


@pytest.mark.parametrize(
    "owner",
    [
        anchored_vwap_owner.AnchoredVwapAnchor,
        quality_owner.OhlcvQualityConfig,
        quality_owner.DerivativesQualityConfig,
    ],
    ids=lambda owner: owner.__name__,
)
def test_an_omitted_owner_type_gaining_a_defaulted_field_fails_the_census(monkeypatch: pytest.MonkeyPatch, owner: type) -> None:
    _replace_everywhere(monkeypatch, owner, _clone_with_extra_defaulted_field(owner))
    with pytest.raises(InputSurfaceError) as raised:
        coverage.enumerate_input_surface()
    assert raised.value.code == "UNCLASSIFIED_FIELD"
    assert "new_owner_input" in str(raised.value)
    assert f"{owner.__module__}.{owner.__qualname__}" in str(raised.value)


def test_select_reward_reference_major_timeframes_default_has_a_row() -> None:
    row = next(
        row
        for row in coverage.enumerate_input_surface()
        if row.owner == "btc_predictor.risk.reward.select_reward_reference" and row.name == "major_timeframes"
    )
    assert row.classification.kind == coverage.KIND_CONFIG
    assert row.category == coverage.CATEGORY_OWNER_DEFAULT
    assert row.default == input_census.canonical_default(reward_owner.MAJOR_REWARD_TIMEFRAMES) == "('1w', '1mo')"
    assert row.default_override == input_census.DEFAULT_FIXED


def _grown_level_references(levels: Sequence[Any], *, reference_type: str, priority: int, new_owner_input: Any = None) -> list[Any]:
    return []


def _grown_missing_period_issues(bars: Sequence[Any], *, start: datetime, end: datetime, timeframe: str, new_owner_input: Any = None) -> tuple[Any, ...]:
    return ()


def _grown_gaussian_health(values: Any, *, preferred: float = 0.0, width: float = 1.0, maximum: float = 100.0, nan_policy: str = "raise", new_owner_input: Any = None) -> Any:
    return None


@pytest.mark.parametrize(
    "original, grown",
    [
        ("btc_predictor.risk.reward._level_references", _grown_level_references),
        ("btc_predictor.data.quality._missing_period_issues", _grown_missing_period_issues),
        ("btc_predictor.quant.transforms.gaussian_health", _grown_gaussian_health),
    ],
    ids=["reward-helper", "quality-helper", "quant-helper"],
)
def test_a_reached_helper_gaining_a_parameter_fails_the_census(monkeypatch: pytest.MonkeyPatch, original: str, grown: Any) -> None:
    module_name, name = original.rsplit(".", 1)
    function = getattr(importlib.import_module(module_name), name)
    replacement = types.FunctionType(grown.__code__, grown.__globals__, name, grown.__defaults__, grown.__closure__)
    replacement.__kwdefaults__ = grown.__kwdefaults__
    replacement.__module__ = function.__module__
    replacement.__qualname__ = function.__qualname__
    replacement.__annotations__ = dict(grown.__annotations__)
    _replace_everywhere(monkeypatch, function, replacement)
    with pytest.raises(InputSurfaceError) as raised:
        coverage.enumerate_input_surface()
    assert raised.value.code == "UNCLASSIFIED_PARAMETER"
    assert "new_owner_input" in str(raised.value)


# --- universal drift checks on the census itself ----------------------------------------------


def _with_callable(census: input_census.DecisionPathCensus, path: str, record: Any) -> input_census.DecisionPathCensus:
    return dataclasses.replace(census, callables={**census.callables, path: record})


def test_any_reached_callable_gaining_a_parameter_fails_the_census() -> None:
    census = _census()
    extra = input_census.CensusParameter("new_owner_input", "KEYWORD_ONLY", None, True, "None")
    for path, record in census.callables.items():
        grown = dataclasses.replace(record, parameters=(*record.parameters, extra))
        with pytest.raises(InputSurfaceError) as raised:
            coverage._require_classified_census(_with_callable(census, path, grown))
        assert raised.value.code == "UNCLASSIFIED_PARAMETER", path


def test_any_reached_type_gaining_a_field_fails_the_census() -> None:
    census = _census()
    for path, record in census.types.items():
        if record.kind == input_census.TYPE_CLASS:
            continue
        grown = dataclasses.replace(record, fields=(*record.fields, "new_owner_input"))
        with pytest.raises(InputSurfaceError) as raised:
            coverage._require_classified_census(dataclasses.replace(census, types={**census.types, path: grown}))
        assert raised.value.code == "UNCLASSIFIED_FIELD", path


def test_a_newly_reached_owner_fails_and_an_owner_no_longer_reached_is_stale() -> None:
    census = _census()
    template = next(iter(census.callables.values()))
    new = dataclasses.replace(template, path="btc_predictor.risk.reward._new_owner_helper")
    with pytest.raises(InputSurfaceError) as raised:
        coverage._require_classified_census(_with_callable(census, new.path, new))
    assert raised.value.code == "UNCLASSIFIED_CALLABLE"
    type_template = census.types["btc_predictor.risk.reward.RewardReference"]
    new_type = dataclasses.replace(type_template, path="btc_predictor.risk.reward.NewOwnerRecord")
    with pytest.raises(InputSurfaceError) as raised:
        coverage._require_classified_census(dataclasses.replace(census, types={**census.types, new_type.path: new_type}))
    assert raised.value.code == "UNCLASSIFIED_OWNER_TYPE"
    gone = "btc_predictor.risk.reward._level_references"
    with pytest.raises(InputSurfaceError) as raised:
        coverage._require_classified_census(
            dataclasses.replace(census, callables={k: v for k, v in census.callables.items() if k != gone})
        )
    assert raised.value.code == "STALE_CLASSIFICATION"
    reordered = dataclasses.replace(
        census.callables[gone], parameters=tuple(reversed(census.callables[gone].parameters))
    )
    with pytest.raises(InputSurfaceError) as raised:
        coverage._require_classified_census(_with_callable(census, gone, reordered))
    assert raised.value.code == "SIGNATURE_ORDER_CHANGED"


# --- composer-facing findings of the corrected census -------------------------------------------


def test_the_capitulation_event_anchor_is_a_new_owner_less_input() -> None:
    rows = coverage.enumerate_input_surface(_census())
    event = [row for row in rows if row.classification.input_id == "CAPITULATION_EVENT"]
    assert {row.owner for row in event} == {
        "btc_predictor.levels.anchored_vwap.CapitulationEvent",
        "btc_predictor.levels.anchored_vwap.anchored_vwap_anchor_from_capitulation_event",
    }
    assert all(row.classification.kind == coverage.KIND_OWNERLESS_UNDEFINED for row in event)
    assert all(row.classification.entry_components == () for row in event)
    blocker = next(item for item in coverage.derive_blockers(rows) if item["blocker_id"] == "BLK-AVWAP-EVENT-ANCHOR")
    assert blocker["entry_conviction_structurally_incomplete_on_every_date"] is False
    # no owner constructs the event
    assert not [site for site in _census().call_sites if site.callee == "btc_predictor.levels.anchored_vwap.CapitulationEvent"]


def test_owner_outputs_have_producers_and_internal_parameters_have_callers() -> None:
    census = _census()
    rows = coverage.enumerate_input_surface(census)
    for row in rows:
        if row.category == input_census_registry.TYPE_OWNER_OUTPUT:
            assert row.classification.kind == coverage.KIND_DERIVED
            assert coverage._type_producers(row.owner, census), row.owner
        if row.category == coverage.CATEGORY_INTERNAL_PARAMETER:
            assert row.owner not in census.root_paths
            assert row.classification.kind == coverage.KIND_OWNER_INTERNAL
        if row.category == coverage.CATEGORY_OWNER_DEFAULT:
            assert census.default_override(row.owner, row.name)[0] == input_census.DEFAULT_FIXED


# --- static walk semantics on in-scope fixture code ----------------------------------------------

_FIXTURE_MODULE = "btc_predictor.census_fixture"


@dataclasses.dataclass(frozen=True)
class _FixtureNested:
    count: int


@dataclasses.dataclass(frozen=True)
class _FixtureRecord:
    value: Decimal
    nested: _FixtureNested | None = None

    def compute(self) -> Any:
        return _fixture_method_helper()

    @property
    def doubled(self) -> Decimal:
        return self.value * 2


class _FixtureView(Protocol):
    price: Decimal
    detected_at: datetime


def _fixture_method_helper() -> int:
    return 1


def _fixture_fixed(x: int, *, k: int = 1) -> int:
    return x + k


def _fixture_keyword(x: int, k: int = 1) -> int:
    return x + k


def _fixture_positional(x: int, k: int = 1) -> int:
    return x + k


def _fixture_starred(x: int, k: int = 1) -> int:
    return x + k


def _fixture_callback(item: int, k: int = 1) -> int:
    return item + k


def _fixture_dispatched(value: int) -> int:
    return value


def _fixture_partial_target(a: int, b: int) -> int:
    return a + b


_FIXTURE_DISPATCH = {"a": _fixture_dispatched}
_FIXTURE_PARTIAL = functools.partial(_fixture_partial_target, 1)


def _fixture_root(record: "_FixtureRecord", view: "_FixtureView", *, mode: str = "a") -> Any:
    from btc_predictor.features._scoring import decimal_bounded_linear as local_import

    args = (1,)
    local: "_FixtureNested | None" = None
    return (
        _fixture_fixed(1),
        _fixture_keyword(1, k=2),
        _fixture_positional(1, 2),
        _fixture_starred(*args),
        sorted([1], key=_fixture_callback),
        _FIXTURE_DISPATCH[mode](1),
        _FIXTURE_PARTIAL(2),
        local_import,
        local,
    )


@pytest.fixture()
def fixture_census(monkeypatch: pytest.MonkeyPatch) -> input_census.DecisionPathCensus:
    module = types.ModuleType(_FIXTURE_MODULE)
    for value in (
        _FixtureNested, _FixtureRecord, _FixtureView, _fixture_method_helper, _fixture_fixed, _fixture_keyword,
        _fixture_positional, _fixture_starred, _fixture_callback, _fixture_dispatched, _fixture_partial_target,
        _fixture_root,
    ):
        monkeypatch.setattr(value, "__module__", _FIXTURE_MODULE)
        setattr(module, value.__name__, value)
    for member in (_FixtureRecord.compute, _FixtureRecord.doubled.fget):
        monkeypatch.setattr(member, "__module__", _FIXTURE_MODULE)
    monkeypatch.setitem(sys.modules, _FIXTURE_MODULE, module)
    root = input_census.DecisionPathRoot(_FIXTURE_MODULE, "_fixture_root", input_census.AREA_RISK_GEOMETRY, "fixture")
    return input_census.discover_decision_path((root,))


def test_the_walk_follows_every_reference_form(fixture_census: input_census.DecisionPathCensus) -> None:
    callables, census_types = set(fixture_census.callables), set(fixture_census.types)
    prefix = _FIXTURE_MODULE + "."
    for name in (
        "_fixture_fixed", "_fixture_keyword", "_fixture_positional", "_fixture_starred", "_fixture_callback",
        "_fixture_dispatched", "_fixture_partial_target", "_FixtureRecord.compute", "_FixtureRecord.doubled",
        "_fixture_method_helper",
    ):
        assert prefix + name in callables, name
    assert input_census.owner_path(decimal_bounded_linear) in callables
    assert {prefix + "_FixtureRecord", prefix + "_FixtureNested", prefix + "_FixtureView"} <= census_types
    assert fixture_census.types[prefix + "_FixtureView"].kind == input_census.TYPE_PROTOCOL
    assert fixture_census.types[prefix + "_FixtureView"].fields == ("price", "detected_at")
    assert fixture_census.callables[prefix + "_FixtureRecord.compute"].parameters == ()
    assert fixture_census.callables[prefix + "_FixtureRecord.doubled"].role == input_census.ROLE_PROPERTY


def test_the_default_override_analysis(fixture_census: input_census.DecisionPathCensus) -> None:
    prefix = _FIXTURE_MODULE + "."
    verdict = {name: fixture_census.default_override(prefix + name, "k")[0] for name in (
        "_fixture_fixed", "_fixture_keyword", "_fixture_positional", "_fixture_starred", "_fixture_callback")}
    assert verdict == {
        "_fixture_fixed": input_census.DEFAULT_FIXED,
        "_fixture_keyword": input_census.DEFAULT_OVERRIDDEN,
        "_fixture_positional": input_census.DEFAULT_OVERRIDDEN,
        "_fixture_starred": input_census.DEFAULT_UNRESOLVED,
        "_fixture_callback": input_census.DEFAULT_UNRESOLVED,
    }
    assert fixture_census.default_override(prefix + "_fixture_root", "mode")[0] == input_census.DEFAULT_COMPOSER_SUPPLIED


def test_two_different_objects_under_one_owner_path_are_refused(
    fixture_census: input_census.DecisionPathCensus, monkeypatch: pytest.MonkeyPatch
) -> None:
    # An owner replaced in only some of the modules that bind it would make the
    # census silently pick one; the walk refuses instead.
    monkeypatch.setattr(_fixture_keyword, "__qualname__", "_fixture_fixed")
    root = input_census.DecisionPathRoot(_FIXTURE_MODULE, "_fixture_root", input_census.AREA_RISK_GEOMETRY, "fixture")
    with pytest.raises(input_census.CensusError) as raised:
        input_census.discover_decision_path((root,))
    assert raised.value.code == "CONFLICTING_OWNER_OBJECTS"


def test_an_owner_name_bound_to_code_outside_the_package_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    namespace: dict[str, Any] = {}
    exec("def _fixture_fixed(x, *, k=1):\n    return x + k\n", namespace)  # noqa: S102 - synthetic foreign code
    foreign = namespace["_fixture_fixed"]
    foreign.__module__ = _FIXTURE_MODULE
    module = types.ModuleType(_FIXTURE_MODULE)
    monkeypatch.setattr(_fixture_root, "__module__", _FIXTURE_MODULE)
    module._fixture_root = _fixture_root
    monkeypatch.setitem(sys.modules, _FIXTURE_MODULE, module)
    monkeypatch.setitem(globals(), "_fixture_fixed", foreign)
    root = input_census.DecisionPathRoot(_FIXTURE_MODULE, "_fixture_root", input_census.AREA_RISK_GEOMETRY, "fixture")
    with pytest.raises(input_census.CensusError) as raised:
        input_census.discover_decision_path((root,))
    assert raised.value.code == "FOREIGN_OWNER_CODE"


def test_canonical_defaults_are_order_free_and_id_free() -> None:
    assert input_census.canonical_default(frozenset({"b", "a"})) == "frozenset({'a', 'b'})"
    assert input_census.canonical_default(("1w",)) == "('1w',)"
    assert input_census.canonical_default(Decimal("0.30")) == "Decimal('0.30')"
    assert input_census.canonical_default(_fixture_fixed) == input_census.owner_path(_fixture_fixed)
    assert "0x" not in input_census.canonical_default(object())
