"""RBT-004: the composer's census call boundary (RBT-002 E4, policy V7 section 5A.6).

Every decision owner function the entry composer calls directly must be a
census root. This is proven statically (an alias-resolving AST census) and at
runtime (a direct-caller profile over fixture decisions), and each refused
dispatch form is introduced by mutation and must fail both checks.
"""

from __future__ import annotations

import functools
import inspect
import json
import sys
import textwrap
import types
from decimal import Decimal
from pathlib import Path

import pytest

from btc_predictor.backtest.engine import run_backtest
from btc_predictor.features import flow as flow_owner
from btc_predictor.research_backtest import composer_boundary as boundary
from btc_predictor.research_backtest import completion_spec, coverage, entry_composer, input_census
from btc_predictor.research_backtest.replay_inputs import replay_market_bars_at
from btc_predictor.tests.rbt004_composer_fixtures import CONFIG, DAY, HOUR, Scenario, trending_close, utc

COMPOSER_FILE = entry_composer.__file__
SOURCE = Path(COMPOSER_FILE).read_text(encoding="utf-8")
SPEC = json.loads((completion_spec.ARTIFACT_DIRECTORY / completion_spec.SPEC_FILENAME).read_text(encoding="utf-8"))
# Insertion points for the mutations: module imports, and the first line of a method body.
IMPORT_ANCHOR = "import bisect\n"
TREND_ANCHOR = "        m4 = four_week_momentum_from_daily_bars(self.daily)\n"


@pytest.fixture(scope="module")
def census():
    return boundary.static_call_census(entry_composer)


# --- static census -----------------------------------------------------------------------


def test_the_static_census_has_no_refusal(census):
    # a recording wrapper left in the composer namespace by another test would
    # masquerade as an owner call: name the leak before the census refuses it
    leaked = sorted(name for name, value in vars(entry_composer).items() if getattr(value, "__module__", "").startswith("btc_predictor.tests"))
    assert leaked == []
    assert census.refusals == ()
    assert census.module == entry_composer.__name__
    record = census.as_record()
    assert record["version"] == boundary.COMPOSER_BOUNDARY_VERSION and record["refusals"] == []


def test_every_directly_called_owner_function_is_a_census_root(census):
    roots = {root.path for root in input_census.DECISION_PATH_ROOTS}
    sources = {source.path for source in input_census.CLASSIFIED_INPUT_SOURCES}
    for call in census.calls:
        if call.kind == boundary.KIND_ROOT:
            assert call.target in roots, call
        elif call.kind == boundary.KIND_INPUT_SOURCE:
            assert call.target in sources, call
        elif call.kind == boundary.KIND_CONSTRUCTOR:
            assert call.target in boundary.ALLOWED_CONSTRUCTORS, call
        elif call.kind == boundary.KIND_EPIC_Y:
            assert call.target.startswith("btc_predictor.research_backtest."), call
        elif call.kind == boundary.KIND_ACCESSOR:
            assert call.target in boundary.ALLOWED_ACCESSORS, call
        else:
            assert not call.target.startswith("btc_predictor.") or call.kind == boundary.KIND_LOCAL, call
    # The census itself classifies every root's parameters (RBT-002 / Part A).
    assert census.roots_called <= roots


def test_the_called_spec_helpers_are_promoted_roots(census):
    promoted = set(SPEC["composer_roots_to_promote"])
    roots = {root.path for root in input_census.DECISION_PATH_ROOTS}
    assert len(promoted) == 14 and promoted <= roots
    # RBT-004 calls 12 of the 14; normal_cdf_score and decision_greater_equal
    # serve RBT-005's ADD/Hold inputs (ADD_MOMENTUM_SCORE, MOMENTUM_PERSISTENCE_SCORE,
    # FLOW_SUPPORTIVE_PREDICATE).
    assert promoted - census.roots_called == {
        "btc_predictor.quant.transforms.normal_cdf_score",
        "btc_predictor.quant.comparisons.decision_greater_equal",
    }
    # Every guard history helper is called, and every classified input source the spec names.
    guard_helpers = {helper["symbol"] for guard in SPEC["positioning_zero_variance_guards"] for helper in guard["history_helpers"]}
    assert guard_helpers <= census.roots_called
    assert census.input_sources_called == {
        "btc_predictor.research_backtest.replay_inputs.replay_market_bars_at",
        "btc_predictor.research.us_equity_market_closures.load_closures",
    }


def test_allowed_constructors_are_classified_input_types(census):
    constructed = {call.target for call in census.calls if call.kind == boundary.KIND_CONSTRUCTOR}
    classified = set(coverage.INPUT_TYPE_FIELD_CLASSIFICATIONS)
    # every allowance is used, and nothing else is constructed
    assert constructed == set(boundary.ALLOWED_CONSTRUCTORS)
    for target in boundary.ALLOWED_CONSTRUCTORS:
        if target != "btc_predictor.backtest.engine.BacktestIntent":
            assert target in classified, target


def test_value_methods_and_accessors_are_bounded(census):
    methods = {call.target for call in census.calls if call.kind == boundary.KIND_VALUE_METHOD}
    assert {name.removeprefix("<value>.") for name in methods} <= boundary.ALLOWED_VALUE_METHODS
    accessors = {call.target for call in census.calls if call.kind == boundary.KIND_ACCESSOR}
    assert accessors == {"btc_predictor.config.strategy.StrategyConfig.run_metadata"}


# --- runtime direct-caller check -----------------------------------------------------------


def _armed_scenario():
    # A deterministic market in which Setup A arms an entry (found by an offline
    # scan of trending_close parameters; the outcome is asserted, not assumed).
    return Scenario(end=utc(2024, 4, 15), close_at=trending_close(daily_drift=0.0003, cycle_days=80.0, cycle_amplitude=0.07))


@pytest.fixture(scope="module")
def traced():
    """Composer decisions on every outcome path, each traced for direct calls."""

    traces = {}
    rows = {}

    default = Scenario().composer()
    for label, instant in (("warm_up", utc(2023, 6, 1)), ("no_trade", utc(2024, 4, 9))):
        decision, calls = boundary.trace_direct_calls(lambda instant=instant: default.decide(instant), COMPOSER_FILE)
        default.record(decision)
        traces[label], rows[label] = calls, decision.row

    armed = _armed_scenario().composer()
    day = utc(2024, 3, 25)
    while day < utc(2024, 3, 31):
        armed.record(armed.decide(day))
        day += DAY
    decision, calls = boundary.trace_direct_calls(lambda: armed.decide(utc(2024, 3, 31)), COMPOSER_FILE)
    traces["arm_entry"], rows["arm_entry"] = calls, decision.row

    constant = Scenario(funding_at=lambda index: Decimal(1) / 3 / 1000).composer()
    decision, calls = boundary.trace_direct_calls(lambda: constant.decide(utc(2024, 4, 9)), COMPOSER_FILE)
    traces["guard_refusal"], rows["guard_refusal"] = calls, decision.row

    # The backtest adapter, through the BTC-180 engine (positions, accessors).
    engine_inputs = Scenario().build()
    adapter = entry_composer.EntryComposer(engine_inputs, strategy_config=CONFIG)
    bars = tuple(bar for bar in engine_inputs.dataset.price_bars if utc(2024, 4, 9) - 2 * HOUR <= bar.timestamp < utc(2024, 4, 10))
    _, calls = boundary.trace_direct_calls(lambda: run_backtest(bars, strategy=adapter, strategy_config=CONFIG, symbol=bars[0].symbol), COMPOSER_FILE)
    traces["engine"], rows["engine"] = calls, adapter.ledger[-1]
    return traces, rows


def test_the_traced_paths_cover_every_outcome(traced):
    _, rows = traced
    assert rows["warm_up"].outcome == entry_composer.OUTCOME_STRUCTURALLY_UNEVALUABLE
    assert rows["no_trade"].outcome == entry_composer.OUTCOME_NO_TRADE
    assert rows["arm_entry"].outcome == entry_composer.OUTCOME_ARM_ENTRY
    assert rows["guard_refusal"].guard_refusals
    for row in rows.values():
        assert row.unaccounted == ()


def test_runtime_direct_calls_are_roots_sources_or_allowances(traced):
    traces, _ = traced
    for label, calls in traces.items():
        assert boundary.direct_call_violations(calls) == (), label


def test_runtime_and_static_roots_agree(traced, census):
    traces, _ = traced
    functions = {call.path for calls in traces.values() for call in calls if call.kind == "FUNCTION"}
    static = census.roots_called | census.input_sources_called
    # Every traced owner function is statically visible (the owner records'
    # own as_record serializers aside), and every static root is exercised.
    serializers = {path for path in functions if path.rsplit(".", 1)[-1] in boundary.ALLOWED_SERIALIZER_NAMES}
    epic_y = {path for path in functions if path.startswith("btc_predictor.research_backtest.")}
    accessors = functions & set(boundary.ALLOWED_ACCESSORS)
    assert functions - serializers - epic_y - accessors <= static
    unexercised = census.roots_called - functions
    assert unexercised <= {"btc_predictor.signals.reclaim.evaluate_reclaim_trigger"}, unexercised
    constructors = {call.path for calls in traces.values() for call in calls if call.kind == "CONSTRUCTOR"}
    assert constructors <= set(boundary.ALLOWED_CONSTRUCTORS)
    assert "btc_predictor.backtest.engine.BacktestIntent" in constructors


def test_classified_serializers_accessors_and_epic_y_helpers_are_allowed():
    allowed = [
        boundary.DirectCall("FUNCTION", "btc_predictor.risk.stop.InitialStopResult.as_record"),
        boundary.DirectCall("FUNCTION", "btc_predictor.config.strategy.StrategyConfig.run_metadata"),
        boundary.DirectCall("FUNCTION", "btc_predictor.backtest.engine.BacktestContext.position_open"),
        boundary.DirectCall("FUNCTION", "btc_predictor.research_backtest.replay_inputs.replay_market_bars_at"),
        boundary.DirectCall("FUNCTION", "btc_predictor.research_backtest.replay_inputs.canonical_json_bytes"),
        boundary.DirectCall("CONSTRUCTOR", "btc_predictor.signals.hard_veto.HardVetoInput"),
    ]
    assert boundary.direct_call_violations(allowed) == ()
    refused = [
        boundary.DirectCall("FUNCTION", "btc_predictor.features.positioning._zscore"),
        boundary.DirectCall("CONSTRUCTOR", "btc_predictor.data.derivatives.FundingRate"),
    ]
    assert boundary.direct_call_violations(refused) == (
        "CONSTRUCTOR btc_predictor.data.derivatives.FundingRate",
        "FUNCTION btc_predictor.features.positioning._zscore",
    )


# --- mutation regressions: static ----------------------------------------------------------


def _mutant(tmp_path: Path, *, imports: str = "", body: str = "") -> types.ModuleType:
    """The composer's own source with extra imports and lines in ``_trend``, loaded as a module."""

    assert IMPORT_ANCHOR in SOURCE and TREND_ANCHOR in SOURCE
    source = SOURCE.replace(IMPORT_ANCHOR, IMPORT_ANCHOR + imports, 1)
    source = source.replace(TREND_ANCHOR, textwrap.indent(body, " " * 8) + TREND_ANCHOR, 1)
    path = tmp_path / "entry_composer_mutant.py"
    path.write_text(source, encoding="utf-8")
    name = "btc_predictor.research_backtest.entry_composer_mutant"
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    try:
        exec(compile(source, str(path), "exec"), module.__dict__)
    finally:
        del sys.modules[name]
    return module


def test_the_mutant_loader_alone_introduces_no_refusal(tmp_path):
    assert boundary.static_call_census(_mutant(tmp_path)).refusals == ()


STATIC_MUTATIONS = {
    "direct internal helper": (
        "from btc_predictor.features.flow import _trailing_publication_dates\n",
        "_trailing_publication_dates(self.t.date(), window_days=5, market_holidays=())\n",
        {(boundary.REFUSED_NOT_A_ROOT, "btc_predictor.features.flow._trailing_publication_dates")},
    ),
    "aliased internal helper": (
        "from btc_predictor.features.positioning import _zscore as harmless_name\n",
        "harmless_name(Decimal(1), (Decimal(1), Decimal(2)))\n",
        {(boundary.REFUSED_NOT_A_ROOT, "btc_predictor.features.positioning._zscore")},
    ),
    "module attribute call of a helper": (
        "from btc_predictor.features import positioning as positioning_module\n",
        "positioning_module._average((Decimal(1),))\n",
        {(boundary.REFUSED_NOT_A_ROOT, "btc_predictor.features.positioning._average")},
    ),
    "getattr dispatch": (
        "from btc_predictor.features import positioning as positioning_module\n",
        "getattr(positioning_module, 'funding_health')((), as_of=self.t)\n",
        {(boundary.REFUSED_DYNAMIC, "builtins.getattr")},
    ),
    "dict dispatch": (
        "",
        "{'health': funding_health}['health']((), as_of=self.t)\n",
        {(boundary.REFUSED_OWNER_AS_VALUE, "btc_predictor.features.positioning.funding_health")},
    ),
    "functools.partial dispatch": (
        "import functools\n",
        "functools.partial(funding_health, ())(as_of=self.t)\n",
        {(boundary.REFUSED_DYNAMIC, "functools.partial"), (boundary.REFUSED_OWNER_AS_VALUE, "btc_predictor.features.positioning.funding_health")},
    ),
    "callback value": (
        "",
        "sorted((), key=funding_health)\n",
        {(boundary.REFUSED_OWNER_AS_VALUE, "btc_predictor.features.positioning.funding_health")},
    ),
    "local alias variable": (
        "",
        "handler = funding_health\nhandler((), as_of=self.t)\n",
        {(boundary.REFUSED_OWNER_AS_VALUE, "btc_predictor.features.positioning.funding_health"), (boundary.REFUSED_UNRESOLVED, "handler")},
    ),
    "unclassified owner constructor": (
        "",
        "MarketCapObservation(observation_time=self.t, market_cap_usd=Decimal(1), provider='x', available_at=self.t)\n",
        {(boundary.REFUSED_CONSTRUCTOR, "btc_predictor.features.positioning.MarketCapObservation")},
    ),
    "importlib dispatch": (
        "import importlib\n",
        "importlib.import_module('btc_predictor.features.flow')\n",
        {(boundary.REFUSED_DYNAMIC, "importlib.import_module")},
    ),
}


@pytest.mark.parametrize("name", sorted(STATIC_MUTATIONS))
def test_a_new_dispatch_form_fails_the_static_census(name, tmp_path):
    imports, body, expected = STATIC_MUTATIONS[name]
    refusals = boundary.static_call_census(_mutant(tmp_path, imports=imports, body=body)).refusals
    found = {(refusal.reason, refusal.target) for refusal in refusals}
    assert expected <= found, (name, found)
    assert refusals, name


# --- mutation regressions: runtime ------------------------------------------------------------


@pytest.fixture(scope="module")
def trend_run():
    composer = Scenario().composer()
    instant = utc(2024, 4, 9)
    run = entry_composer._DecisionRun(composer, instant, position_open=False)
    canonical = replay_market_bars_at(composer._visible_hourly(instant), decision_at=instant, window=composer._window)
    run.daily = tuple(bar for bar in canonical if bar.timeframe == "1d")
    run.weekly = tuple(bar for bar in canonical if bar.timeframe == "1w")
    return run


def _swapped_trend(body: str, extra: dict) -> types.FunctionType:
    """``_DecisionRun._trend`` recompiled with ``body`` first, under the composer's own file name."""

    source = textwrap.dedent(inspect.getsource(entry_composer._DecisionRun._trend))
    anchor = TREND_ANCHOR.removeprefix("    ")
    assert anchor in source
    source = source.replace(anchor, textwrap.indent(body, " " * 4) + anchor, 1)
    namespace = {**vars(entry_composer), **extra}
    exec(compile(source, COMPOSER_FILE, "exec"), namespace)
    return namespace["_trend"]


def test_the_runtime_check_passes_the_unmutated_method(trend_run):
    _, calls = boundary.trace_direct_calls(trend_run._trend, COMPOSER_FILE)
    assert calls and boundary.direct_call_violations(calls) == ()


RUNTIME_MUTATIONS = {
    "direct internal helper": ("_trailing_publication_dates(self.t.date(), window_days=5, market_holidays=())\n", {"_trailing_publication_dates": flow_owner._trailing_publication_dates}),
    "aliased internal helper": ("harmless_name(self.t.date(), window_days=5, market_holidays=())\n", {"harmless_name": flow_owner._trailing_publication_dates}),
    "getattr dispatch": ("getattr(flow_module, '_trailing_publication_dates')(self.t.date(), window_days=5, market_holidays=())\n", {"flow_module": flow_owner}),
    "dict dispatch": ("{'f': _trailing_publication_dates}['f'](self.t.date(), window_days=5, market_holidays=())\n", {"_trailing_publication_dates": flow_owner._trailing_publication_dates}),
    "functools.partial dispatch": ("functools.partial(_trailing_publication_dates, self.t.date())(window_days=5, market_holidays=())\n", {"_trailing_publication_dates": flow_owner._trailing_publication_dates, "functools": functools}),
    "callback": ("list(map(lambda day: _trailing_publication_dates(day, window_days=5, market_holidays=()), [self.t.date()]))\n", {"_trailing_publication_dates": flow_owner._trailing_publication_dates}),
}


@pytest.mark.parametrize("name", sorted(RUNTIME_MUTATIONS))
def test_a_new_direct_helper_call_fails_the_runtime_check(name, trend_run, monkeypatch):
    body, extra = RUNTIME_MUTATIONS[name]
    monkeypatch.setattr(entry_composer._DecisionRun, "_trend", _swapped_trend(body, extra))
    _, calls = boundary.trace_direct_calls(trend_run._trend, COMPOSER_FILE)
    assert "FUNCTION btc_predictor.features.flow._trailing_publication_dates" in boundary.direct_call_violations(calls), name


def test_an_unclassified_constructor_fails_the_runtime_check(trend_run, monkeypatch):
    from btc_predictor.features.positioning import MarketCapObservation

    body = "MarketCapObservation(observation_time=self.t, market_cap_usd=Decimal(1), provider='x', available_at=self.t)\n"
    monkeypatch.setattr(entry_composer._DecisionRun, "_trend", _swapped_trend(body, {"MarketCapObservation": MarketCapObservation}))
    _, calls = boundary.trace_direct_calls(trend_run._trend, COMPOSER_FILE)
    assert "CONSTRUCTOR btc_predictor.features.positioning.MarketCapObservation" in boundary.direct_call_violations(calls)
