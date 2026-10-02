"""Independent RBT-002 re-review evidence; known failures stay explicit."""
from __future__ import annotations

import ast
import importlib.util
import inspect
import sys
import textwrap
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from btc_predictor.data import FuturesBasis, OhlcvBar
from btc_predictor.features.positioning import futures_basis_health
from btc_predictor.features.structure import calculate_structure_score_from_clusters
from btc_predictor.levels.anchored_vwap import (
    CapitulationEvent, anchored_vwap_anchor_from_capitulation_event, calculate_anchored_vwap,
)
from btc_predictor.levels.clustering import cluster_price_levels
from btc_predictor.levels.strength import calculate_level_strength_from_cluster
from btc_predictor.research_backtest import coverage, input_census
from btc_predictor.risk import reward, trailing


def _compile_changed(function, change):
    tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
    change(tree)
    ast.fix_missing_locations(tree)
    ast.increment_lineno(tree, function.__code__.co_firstlineno - 1)
    namespace = dict(function.__globals__)
    exec(compile(tree, function.__code__.co_filename, "exec"), namespace)
    return namespace[function.__name__]


def test_capitulation_avwap_feeds_structure_even_when_optional():
    start = datetime(2024, 3, 4, tzinfo=UTC)
    as_of = start + timedelta(hours=2)
    price = Decimal("100")
    event = CapitulationEvent(start, start, price, "fixture", "BTC/USD", "fixture")
    bar = OhlcvBar(start, "fixture", "BTC/USD", "1h", price, price, price, price, Decimal("1"), "fixture", as_of)
    vwap = calculate_anchored_vwap(anchored_vwap_anchor_from_capitulation_event(event), (bar,), as_of=as_of)
    def level(value, kind):
        return {"feature_id": "WEEKLY_SWING_LEVEL", "level_type": kind, "price": str(value),
                "detected_at": start, "level_timestamp": start-timedelta(days=7), "timeframe": "1w",
                "exchange": "fixture", "symbol": "BTC/USD", "provider": "fixture"}
    levels = (level(100, "swing_low"), level(150, "swing_high"))
    results = []
    for extras in ((), (vwap,)):
        clusters = cluster_price_levels((*levels, *extras), reference_price=110, as_of=as_of)
        support = next(c for c in clusters.clusters if c.zone_type == "support")
        strength = calculate_level_strength_from_cluster(support, touch_count=5,
            reaction_magnitude_fraction=Decimal("0.05"), volume_percentile=Decimal("50"))
        structure = calculate_structure_score_from_clusters(clusters, entry_price=110, stop_price=95,
            level_strength_result=strength)
        assert strength.complete and structure.complete
        results.append((support.confluence_score, strength.score, structure.score))
    assert all(b > a for a, b in zip(*results))
    event_rows = [r for r in coverage.enumerate_input_surface() if r.classification.input_id == "CAPITULATION_EVENT"]
    assert len(event_rows) == 8
    assert all(r.classification.entry_components == ("structure",) for r in event_rows)
    blocker = next(b for b in coverage.derive_blockers(coverage.enumerate_input_surface()) if b["blocker_id"] == "BLK-AVWAP-EVENT-ANCHOR")
    assert blocker["entry_components"] == ["structure"]
    assert blocker["entry_conviction_structurally_incomplete_on_every_date"] is False


def test_inventory_names_the_current_policy():
    # RBT-002 R2: the inventory label tracks the governing policy, now V5.
    assert coverage.INVENTORY_POLICY_VERSION == "RESEARCH_BACKTEST_POLICY_V5"


def test_nested_trailing_helper_parameters_are_enumerated():
    c = input_census.discover_decision_path()
    helper = c.callables["btc_predictor.risk.trailing.calculate_trailing_stop.<locals>.held"]
    assert helper.parameter_names == ("reason", "candidate", "complete")


def test_new_nested_live_input_is_refused(monkeypatch):
    def change(tree):
        helper = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "held")
        helper.args.kwonlyargs.append(ast.arg(arg="independent_new_input"))
        helper.args.kw_defaults.append(ast.Constant(True))
        argument = next(n for n in ast.walk(helper) if isinstance(n, ast.keyword) and n.arg == "complete")
        argument.value = ast.BoolOp(ast.And(), [argument.value, ast.Name("independent_new_input", ast.Load())])
    replacement = _compile_changed(trailing.calculate_trailing_stop, change)
    before = input_census.discover_decision_path()
    monkeypatch.setattr(trailing.calculate_trailing_stop, "__code__", replacement.__code__)
    c = input_census.discover_decision_path()
    _, traced = input_census.trace_owner_calls(lambda: trailing.calculate_trailing_stop(direction="long", previous_stop=90, structure_price=None, buffer=None))
    assert any(p.endswith(".<locals>.held") for p in traced.functions)
    # R2 fix: the census now discovers the executed helper's new input, and
    # the tracer checks that frame against its own static record instead of
    # exempting it through calculate_trailing_stop. (Before R2 the census and
    # tracer both stayed silent and the surface was unchanged.)
    helper = "btc_predictor.risk.trailing.calculate_trailing_stop.<locals>.held"
    assert c.callables[helper].parameter_names == ("reason", "candidate", "complete", "independent_new_input")
    assert input_census.uncovered_traced(c, traced) == {"functions": [], "dataclasses": []}
    stale = input_census.uncovered_traced(before, traced)["functions"]
    assert [item for item in stale if item.startswith(helper) and "independent_new_input" in item]
    with pytest.raises(coverage.InputSurfaceError, match="UNCLASSIFIED_PARAMETER.*independent_new_input"):
        coverage.enumerate_input_surface(c)
    with pytest.raises(coverage.InputSurfaceError, match="UNCLASSIFIED_PARAMETER"):
        coverage.enumerate_input_surface()


def test_live_top_level_parameter_mutation_is_refused(monkeypatch):
    def change(tree):
        tree.body[0].args.kwonlyargs.append(ast.arg(arg="independent_new_input"))
        tree.body[0].args.kw_defaults.append(ast.Constant(None))
    replacement = _compile_changed(reward._level_references, change)
    monkeypatch.setattr(reward._level_references, "__code__", replacement.__code__)
    monkeypatch.setattr(reward._level_references, "__kwdefaults__", replacement.__kwdefaults__)
    with pytest.raises(coverage.InputSurfaceError, match="UNCLASSIFIED_PARAMETER.*independent_new_input"):
        coverage.enumerate_input_surface()


@pytest.mark.xfail(strict=True, reason="P2 frozen Phase-1 owner defect: constant non-terminating basis must refuse zero variance")
def test_nonterminating_constant_basis_refuses_zero_variance():
    start = datetime(2023, 3, 1, tzinfo=UTC)
    basis = Decimal("0.015")
    annualized = basis * Decimal(365) / Decimal(90)
    rows = tuple(FuturesBasis(observation_time=start+timedelta(days=i), exchange="fixture", symbol="BTC",
        instrument="fixture-quarterly", expiry=start+timedelta(days=i+90), basis_rate=basis,
        annualized_basis_rate=annualized, provider="fixture", source="synthetic",
        available_at=start+timedelta(days=i, minutes=1), ingested_at=start+timedelta(days=i, minutes=2)) for i in range(60))
    assert len({r.annualized_basis_rate for r in rows}) == 1
    result = futures_basis_health(rows, as_of=start+timedelta(days=60))
    assert not result.complete and result.annualized_basis_zscore is None
    assert "FUTURES_BASIS_ZERO_VARIANCE" in result.reason_codes


@pytest.mark.parametrize("root,target,static", [
    ("enclosing_local_root", "hidden_callback", False),
    ("protocol_root", "HiddenImplementation.compute", False),
    ("dict_root", "hidden_callback", True),
    ("getattr_root", "hidden_callback", False),
    ("post_init_root", "Config", True),
    ("property_root", "hidden_callback", True),
])
def test_independent_adversarial_owners(root, target, static, monkeypatch):
    name = "btc_predictor.rbt002_review_fixture"
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name("rbt002_rereview_fixture_owners.py"))
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    module.MODULE = module
    thunk = {"enclosing_local_root": lambda: module.enclosing_local_root(module.hidden_callback),
             "protocol_root": lambda: module.protocol_root(module.HiddenImplementation()),
             "dict_root": lambda: module.dict_root("chosen"),
             "getattr_root": lambda: module.getattr_root("hidden_callback"),
             "post_init_root": module.post_init_root,
             "property_root": lambda: module.property_root(module.PublicRecord())}[root]
    census = input_census.discover_decision_path((input_census.DecisionPathRoot(name, root, input_census.AREA_LIFECYCLE, "independent fixture"),))
    _, traced = input_census.trace_owner_calls(thunk)
    path = name + "." + target
    assert (path in census.callables or path in census.types) is static
    assert path in traced.functions or path in traced.dataclasses
    assert bool(any(input_census.uncovered_traced(census, traced).values())) is (not static)
