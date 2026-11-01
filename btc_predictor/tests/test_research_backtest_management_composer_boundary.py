"""RBT-005: the management composer's census call boundary (RBT-002 E4, policy V7 section 5A.6).

Every decision owner function the management composer calls directly must be a
census root, proven statically (the alias-resolving AST census) and at runtime
(a direct-caller profile over a composed replay, TRIM and EXIT decisions and the
pending ADD's risk re-check at its callback). Each refused dispatch form is introduced by mutation and must fail
both checks, as for the entry composer.
"""

from __future__ import annotations

import functools
import inspect
import sys
import textwrap
import types
from dataclasses import replace
from pathlib import Path

import pytest

from btc_predictor.portfolio import state_machine as state_machine_owner
from btc_predictor.research_backtest import composer_boundary as boundary
from btc_predictor.research_backtest import coverage, entry_composer, management_composer
from btc_predictor.risk import trailing as trailing_owner
from btc_predictor.tests.rbt005_management_fixtures import (
    HOUR,
    TRAIL_AT,
    Interventions,
    callback_context,
    engine_bars,
    higher_low_at,
    managed_run,
    management_market,
    natural_run,
    pending_trail_add,
    resolver_holding,
    utc,
)
from btc_predictor.tests.test_research_backtest_entry_composer_boundary import MANAGEMENT_CONSTRUCTORS

COMPOSER_FILE = management_composer.__file__
SOURCE = Path(COMPOSER_FILE).read_text(encoding="utf-8")
# Insertion points for the mutations: module imports, and a line of the Hold step.
IMPORT_ANCHOR = "from btc_predictor.signals.trim import trim_rules_from_results\n"
HOLD_ANCHOR = '        structure = self._structure_at("hold_structure", self.lifecycle.stop_price, "hold")\n'

EXPECTED_ROOTS = {
    "btc_predictor.features.add.calculate_add_score",
    "btc_predictor.features.add.risk_improvement_component_score",
    # the trim owner's prior flow when the prior instant had no decision bar (review F2)
    "btc_predictor.features.flow.calculate_flow_score",
    "btc_predictor.features.hold.calculate_hold_score",
    "btc_predictor.quant.comparisons.decision_greater_equal",
    "btc_predictor.quant.transforms.normal_cdf_score",
    "btc_predictor.risk.budget.calculate_risk_budget",
    "btc_predictor.risk.buffer.volatility_buffer_for_invalidation",
    "btc_predictor.risk.exposure.calculate_risk_at_stop",
    "btc_predictor.risk.sizing.initial_position_size_for_trade",
    "btc_predictor.risk.trailing.trail_stop_for_position",
    "btc_predictor.risk.tranches.next_tranche_for_position",
    "btc_predictor.signals.add_requirements.add_requirements_from_results",
    "btc_predictor.signals.data_quality.apply_data_quality_gate",
    "btc_predictor.signals.exit_rules.exit_rules_for_position",
    "btc_predictor.signals.trim.trim_rules_from_results",
}


@pytest.fixture(scope="module")
def census():
    return boundary.static_call_census(management_composer)


# --- static census -----------------------------------------------------------------------


def test_the_static_census_has_no_refusal(census):
    assert census.refusals == ()


def test_every_owner_the_composer_calls_is_a_census_root(census):
    assert census.roots_called == EXPECTED_ROOTS
    assert EXPECTED_ROOTS <= boundary.census_roots()
    # the management composer reads no replay input itself: the entry composition carries them
    assert census.input_sources_called == frozenset()


def test_its_constructors_are_the_classified_in_position_inputs(census):
    constructed = {call.target for call in census.calls if call.kind == boundary.KIND_CONSTRUCTOR}
    # FlowScoreInput: the flow owner's every-input-missing result for an absent prior flow (review F2)
    assert constructed == MANAGEMENT_CONSTRUCTORS | {"btc_predictor.backtest.engine.BacktestIntent", "btc_predictor.features.flow.FlowScoreInput"}
    for target in MANAGEMENT_CONSTRUCTORS:
        assert target in coverage.INPUT_TYPE_FIELD_CLASSIFICATIONS, target
    # together the two composers use every allowance
    entry_constructed = {call.target for call in boundary.static_call_census(entry_composer).calls if call.kind == boundary.KIND_CONSTRUCTOR}
    assert constructed | entry_constructed == set(boundary.ALLOWED_CONSTRUCTORS)


def test_value_methods_and_accessors_are_bounded(census):
    methods = {call.target for call in census.calls if call.kind == boundary.KIND_VALUE_METHOD}
    assert {name.removeprefix("<value>.") for name in methods} <= boundary.ALLOWED_VALUE_METHODS
    accessors = {call.target for call in census.calls if call.kind == boundary.KIND_ACCESSOR}
    assert accessors == {"btc_predictor.config.strategy.StrategyConfig.run_metadata"}
    epic_y = {call.target for call in census.calls if call.kind == boundary.KIND_EPIC_Y}
    assert {
        "btc_predictor.research_backtest.entry_composer.structure_score_at",
        "btc_predictor.research_backtest.entry_composer.latest_higher_low",
        "btc_predictor.research_backtest.entry_composer.EntryComposer.step",
    } <= epic_y


# --- runtime direct-caller check -----------------------------------------------------------


@pytest.fixture(scope="module")
def traced():
    """A composed replay (ARM_ENTRY, HOLD, TRAIL), TRIM and EXIT decisions, and the ADD at its callback.

    The replay's only intervention is the entry composer's higher-low result, so
    nothing stands between the management composer and its owners; the add is
    evaluated in full (blocked by its own score). The pending ADD's callback,
    with its risk re-check (owner review ruling 4), is traced on the resolver
    from the trail-and-add replay's state, built outside the trace.
    """

    natural = natural_run()  # built outside the trace
    pending = pending_trail_add()
    resolver = resolver_holding(pending)
    callback = callback_context(pending.moved)
    market = management_market(end=utc(2024, 4, 6))
    inputs = market.build()

    def setup(interventions: Interventions) -> None:
        higher_low_at(interventions, inputs, {TRAIL_AT})

    traces, decisions = {}, {}
    run, traces["replay"] = boundary.trace_direct_calls(
        lambda: managed_run(
            market, engine_end=utc(2024, 4, 2, 3), setup=setup, capture=False,
            bars=lambda built: engine_bars(built, utc(2024, 3, 30, 23), utc(2024, 4, 2, 3)),
        ),
        COMPOSER_FILE,
    )
    decisions["replay"] = run
    trim_at = utc(2024, 4, 3)
    decisions["trim"], traces["trim"] = boundary.trace_direct_calls(lambda: natural.redecide(trim_at), COMPOSER_FILE)
    bear = replace(natural.captured[trim_at].decision.composition.regime_classification, regime="BEAR")
    decisions["exit"], traces["exit"] = boundary.trace_direct_calls(lambda: natural.redecide(trim_at, regime_classification=bear), COMPOSER_FILE)
    item = natural.captured[trim_at]
    decisions["no_prior_flow"], traces["no_prior_flow"] = boundary.trace_direct_calls(
        lambda: management_composer.ManagementComposer(natural.champion.entry).decide(
            item.decision, lifecycle=item.lifecycle, nav=item.nav, armed=item.armed, prior_flow=None
        ),
        COMPOSER_FILE,
    )
    decisions["add"], traces["add"] = boundary.trace_direct_calls(lambda: resolver._resolve_pending(callback, TRAIL_AT + HOUR), COMPOSER_FILE)
    decisions["add_followups"] = resolver.add_followups
    return traces, decisions


def test_the_traced_paths_cover_every_management_outcome(traced):
    _, decisions = traced
    replay = decisions["replay"]
    outcomes = {row.outcome for row in replay.champion.ledger}
    assert {"HOLD", "TRAIL"} <= outcomes
    trail = next(row for row in replay.champion.ledger if row.outcome == "TRAIL")
    assert trail.add["evaluated"] is True and trail.add["reasons"] == ["ADD_REQUIREMENTS_ADD_SCORE_BELOW_MINIMUM"]
    assert decisions["trim"].row.outcome == "TRIM" and decisions["exit"].row.outcome == "EXIT"
    assert decisions["no_prior_flow"].row.owner_reason_codes["trim_prior_flow_unavailable"]["complete"] is False
    (followup,) = decisions["add_followups"]
    assert decisions["add"].action == "ADD" and followup.risk_recheck["within_maximum"] is True
    assert followup.unaccounted == ()
    for row in (*replay.champion.ledger, decisions["trim"].row, decisions["exit"].row, decisions["no_prior_flow"].row):
        assert row.unaccounted == ()


def test_runtime_direct_calls_are_roots_sources_or_allowances(traced):
    traces, _ = traced
    for label, calls in traces.items():
        assert boundary.direct_call_violations(calls) == (), label


def test_runtime_and_static_roots_agree(traced, census):
    traces, _ = traced
    functions = {call.path for calls in traces.values() for call in calls if call.kind == "FUNCTION"}
    serializers = {path for path in functions if path.rsplit(".", 1)[-1] in boundary.ALLOWED_SERIALIZER_NAMES}
    epic_y = {path for path in functions if path.startswith("btc_predictor.research_backtest.")}
    accessors = functions & set(boundary.ALLOWED_ACCESSORS)
    # every traced owner function is statically visible, and every static root is exercised
    assert functions - serializers - epic_y - accessors <= census.roots_called
    assert census.roots_called - functions == set()
    constructors = {call.path for calls in traces.values() for call in calls if call.kind == "CONSTRUCTOR"}
    assert constructors == MANAGEMENT_CONSTRUCTORS | {"btc_predictor.backtest.engine.BacktestIntent", "btc_predictor.features.flow.FlowScoreInput"}


# --- mutation regressions: static ----------------------------------------------------------


def _mutant(tmp_path: Path, *, imports: str = "", body: str = "") -> types.ModuleType:
    """The composer's own source with extra imports and lines in ``_hold``, loaded as a module."""

    assert IMPORT_ANCHOR in SOURCE and HOLD_ANCHOR in SOURCE
    source = SOURCE.replace(IMPORT_ANCHOR, IMPORT_ANCHOR + imports, 1)
    source = source.replace(HOLD_ANCHOR, textwrap.indent(body, " " * 8) + HOLD_ANCHOR, 1)
    path = tmp_path / "management_composer_mutant.py"
    path.write_text(source, encoding="utf-8")
    name = "btc_predictor.research_backtest.management_composer_mutant"
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
    "direct non-root owner function": (
        "from btc_predictor.risk.trailing import used_trailing_structure_ids\n",
        "used_trailing_structure_ids(self.lifecycle)\n",
        {(boundary.REFUSED_NOT_A_ROOT, "btc_predictor.risk.trailing.used_trailing_structure_ids")},
    ),
    "aliased non-root owner function": (
        "from btc_predictor.portfolio.state_machine import position_is_profitable_at_price as harmless_name\n",
        "harmless_name(direction='long', average_entry_price=self.price, current_price=self.price)\n",
        {(boundary.REFUSED_NOT_A_ROOT, "btc_predictor.portfolio.state_machine.position_is_profitable_at_price")},
    ),
    "module attribute call of a helper": (
        "from btc_predictor.risk import trailing as trailing_module\n",
        "trailing_module.stop_advance_count(self.lifecycle)\n",
        {(boundary.REFUSED_NOT_A_ROOT, "btc_predictor.risk.trailing.stop_advance_count")},
    ),
    "getattr dispatch": (
        "from btc_predictor.risk import trailing as trailing_module\n",
        "getattr(trailing_module, 'stop_advance_count')(self.lifecycle)\n",
        {(boundary.REFUSED_DYNAMIC, "builtins.getattr")},
    ),
    "dict dispatch of a root": (
        "",
        "{'hold': calculate_hold_score}['hold'](None, strategy_config=self.config)\n",
        {(boundary.REFUSED_OWNER_AS_VALUE, "btc_predictor.features.hold.calculate_hold_score")},
    ),
    "local alias of a root": (
        "",
        "scorer = calculate_hold_score\nscorer(None, strategy_config=self.config)\n",
        {(boundary.REFUSED_OWNER_AS_VALUE, "btc_predictor.features.hold.calculate_hold_score"), (boundary.REFUSED_UNRESOLVED, "scorer")},
    ),
    "unclassified owner constructor": (
        "from btc_predictor.signals.trim import TrimRuleInput\n",
        "TrimRuleInput(position_open=True, hold_score=None, euphoria_active=None, crowding_active=None, current_flow_score=None, prior_flow_score=None)\n",
        {(boundary.REFUSED_CONSTRUCTOR, "btc_predictor.signals.trim.TrimRuleInput")},
    ),
    "function-local import": (
        "",
        "from btc_predictor.risk.trailing import stop_advance_count\nstop_advance_count(self.lifecycle)\n",
        {(boundary.REFUSED_LOCAL_IMPORT, "btc_predictor.risk.trailing.stop_advance_count")},
    ),
    "trusted name rebound through __dict__": (
        "from btc_predictor.risk import trailing as trailing_module\n",
        "self.__dict__['_keep'] = trailing_module.__dict__['stop_advance_count']\n",
        {(boundary.REFUSED_DUNDER_ATTRIBUTE, "self.__dict__")},
    ),
}


@pytest.mark.parametrize("name", sorted(STATIC_MUTATIONS))
def test_a_new_dispatch_form_fails_the_static_census(name, tmp_path):
    imports, body, expected = STATIC_MUTATIONS[name]
    refusals = boundary.static_call_census(_mutant(tmp_path, imports=imports, body=body)).refusals
    found = {(refusal.reason, refusal.target) for refusal in refusals}
    assert expected <= found, (name, found)


# --- mutation regressions: runtime ------------------------------------------------------------


@pytest.fixture(scope="module")
def hold_run():
    natural = natural_run()
    item = natural.captured[utc(2024, 4, 1)]
    return management_composer._ManagementRun(
        management_composer.ManagementComposer(natural.champion.entry), item.decision,
        lifecycle=item.lifecycle, nav=item.nav, armed=item.armed, prior_flow=item.prior_flow,
    )


def _swapped_hold(body: str, extra: dict) -> types.FunctionType:
    """``_ManagementRun._hold`` recompiled with ``body`` first, under the composer's own file name."""

    source = textwrap.dedent(inspect.getsource(management_composer._ManagementRun._hold))
    anchor = HOLD_ANCHOR.removeprefix("    ")
    assert anchor in source
    source = source.replace(anchor, textwrap.indent(body, " " * 4) + anchor, 1)
    namespace = {**vars(management_composer), **extra}
    exec(compile(source, COMPOSER_FILE, "exec"), namespace)
    return namespace["_hold"]


def test_the_runtime_check_passes_the_unmutated_method(hold_run):
    _, calls = boundary.trace_direct_calls(hold_run._hold, COMPOSER_FILE)
    assert calls and boundary.direct_call_violations(calls) == ()


RUNTIME_MUTATIONS = {
    "direct non-root owner function": ("used_trailing_structure_ids(self.lifecycle)\n", {"used_trailing_structure_ids": trailing_owner.used_trailing_structure_ids}),
    "aliased non-root owner function": ("harmless_name(self.lifecycle)\n", {"harmless_name": trailing_owner.used_trailing_structure_ids}),
    "getattr dispatch": ("getattr(trailing_module, 'used_trailing_structure_ids')(self.lifecycle)\n", {"trailing_module": trailing_owner}),
    "dict dispatch": ("{'f': used_trailing_structure_ids}['f'](self.lifecycle)\n", {"used_trailing_structure_ids": trailing_owner.used_trailing_structure_ids}),
    "functools.partial dispatch": ("functools.partial(used_trailing_structure_ids, self.lifecycle)()\n", {"used_trailing_structure_ids": trailing_owner.used_trailing_structure_ids, "functools": functools}),
    "callback": ("list(map(lambda item: used_trailing_structure_ids(item), [self.lifecycle]))\n", {"used_trailing_structure_ids": trailing_owner.used_trailing_structure_ids}),
}


@pytest.mark.parametrize("name", sorted(RUNTIME_MUTATIONS))
def test_a_new_direct_helper_call_fails_the_runtime_check(name, hold_run, monkeypatch):
    body, extra = RUNTIME_MUTATIONS[name]
    monkeypatch.setattr(management_composer._ManagementRun, "_hold", _swapped_hold(body, extra))
    _, calls = boundary.trace_direct_calls(hold_run._hold, COMPOSER_FILE)
    assert "FUNCTION btc_predictor.risk.trailing.used_trailing_structure_ids" in boundary.direct_call_violations(calls), name


def test_an_unclassified_constructor_fails_the_runtime_check(hold_run, monkeypatch):
    from btc_predictor.signals.trim import TrimRuleInput

    body = "TrimRuleInput(position_open=True, hold_score=None, euphoria_active=None, crowding_active=None, current_flow_score=None, prior_flow_score=None)\n"
    monkeypatch.setattr(management_composer._ManagementRun, "_hold", _swapped_hold(body, {"TrimRuleInput": TrimRuleInput}))
    _, calls = boundary.trace_direct_calls(hold_run._hold, COMPOSER_FILE)
    assert "CONSTRUCTOR btc_predictor.signals.trim.TrimRuleInput" in boundary.direct_call_violations(calls)


def test_a_state_machine_helper_called_directly_fails_the_runtime_check(hold_run, monkeypatch):
    body = "position_is_profitable_at_price(direction='long', average_entry_price=self.price, current_price=self.price)\n"
    extra = {"position_is_profitable_at_price": state_machine_owner.position_is_profitable_at_price}
    monkeypatch.setattr(management_composer._ManagementRun, "_hold", _swapped_hold(body, extra))
    _, calls = boundary.trace_direct_calls(hold_run._hold, COMPOSER_FILE)
    assert "FUNCTION btc_predictor.portfolio.state_machine.position_is_profitable_at_price" in boundary.direct_call_violations(calls)
