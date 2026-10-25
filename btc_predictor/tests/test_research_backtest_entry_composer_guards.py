"""RBT-004: the policy V7 section 6A.9 zero-variance guards and the spec's uniform rules.

Each frozen positioning owner returns a *complete* z-score on an exactly
constant non-terminating history (Decimal mean/variance rounding). The composer
must refuse such a history with the owner's own reason code, pass on no health
score or z-score, and record positioning as structurally unevaluable. Each
owner gets the five required tests: constant history, current equal, current
different, point-in-time exclusion and non-constant pass-through. Synthetic
deterministic fixtures only.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from btc_predictor.data import FundingRate, FuturesBasis, OpenInterest
from btc_predictor.features import positioning as positioning_owner
from btc_predictor.features.rolling import rolling_percentile, rolling_zscore
from btc_predictor.quant import rolling as quant_rolling
from btc_predictor.research_backtest import completion_spec, composer_boundary, entry_composer
from btc_predictor.research_backtest.entry_composer import (
    AUTHORITY_SPEC_GUARD,
    OUTCOME_STRUCTURALLY_UNEVALUABLE,
    _uniform_percentile,
    _uniform_zscore,
    accounted_cause,
)
from btc_predictor.tests.rbt004_composer_fixtures import BULK_INGESTED_AT, CONFIG, DAY, HOUR, Scenario, utc

T = utc(2024, 4, 9)
DERIVATIVES_START = utc(2023, 6, 1)
# The OI fixture starts later so its exact integer series stays well inside the
# Decimal context: 3**(40 - k) * 4**k has at most 25 digits for k <= 40.
OI_START = utc(2023, 9, 15)
FUNDING_CONSTANT = Decimal(1) / Decimal(3) / Decimal(1000)
BASIS_CONSTANT = Decimal("0.015") * 365 / 90
OI_EXPONENT = 40
NON_TERMINATING = (Decimal("0.1"), Decimal(1) / Decimal(3), Decimal("0.015") * 365 / 90)
SPEC = json.loads((completion_spec.ARTIFACT_DIRECTORY / completion_spec.SPEC_FILENAME).read_text(encoding="utf-8"))
SPEC_GUARDS = {item["guard_id"]: item for item in SPEC["positioning_zero_variance_guards"]}


def _oi_constant_growth(index: int) -> Decimal:
    # OI(i) / OI(i - 7) == 4/3 exactly for every i, so every 7-day growth is
    # the same Decimal 0.333...; the owner's mean/variance rounding does the rest.
    week = index // 7
    return Decimal(3 ** (OI_EXPONENT - week) * 4**week)


def _funding_index(instant) -> int:
    return int((instant - DERIVATIVES_START) / timedelta(hours=8))


def _day_index(instant, start) -> int:
    return (instant - start).days


@dataclass(frozen=True)
class Guard:
    key: str
    owner: str
    guard_id: str
    code: str
    z_field: str
    z_feature: str
    health_feature: str
    start: Any
    index: Any
    constant: Any

    def scenario(self, value_at) -> Scenario:
        if self.key == "funding":
            return Scenario(funding_at=value_at)
        if self.key == "basis":
            return Scenario(basis_at=value_at)
        return Scenario(derivatives_start=OI_START, oi_at=value_at)

    def owner_result(self, inputs, instant):
        shared = inputs.dataset.shared_snapshot
        if self.key == "funding":
            return positioning_owner.funding_health(tuple(r for r in shared.funding_rates if r.available_at <= instant), as_of=instant)
        if self.key == "basis":
            return positioning_owner.futures_basis_health(tuple(r for r in inputs.futures_basis if r.available_at <= instant), as_of=instant)
        return positioning_owner.open_interest_growth_health(
            tuple(r for r in shared.open_interest if r.available_at <= instant), as_of=instant, open_interest_unit="USD"
        )

    def owner_history(self, inputs, instant) -> tuple[Decimal, ...]:
        """The owner's own prior history, rebuilt independently with its helpers."""

        result = self.owner_result(inputs, instant)
        shared = inputs.dataset.shared_snapshot
        if self.key == "funding":
            rows = [r for r in shared.funding_rates if r.available_at <= instant and r.observation_time <= instant]
            averages = positioning_owner._funding_averages_by_time(rows, average_window_days=result.average_window_days)
            return positioning_owner._funding_average_history(
                averages, observation_time=result.observation_time, zscore_window_days=result.zscore_window_days
            )
        if self.key == "basis":
            rows = [r for r in inputs.futures_basis if r.available_at <= instant and r.observation_time <= instant]
            averages = positioning_owner._futures_basis_averages_by_time(rows)
            return positioning_owner._futures_basis_history(
                averages, observation_time=result.observation_time, zscore_window_days=result.zscore_window_days
            )
        rows = [
            r for r in shared.open_interest if r.open_interest_unit == "USD" and r.available_at <= instant and r.observation_time <= instant
        ]
        growth = positioning_owner._open_interest_growth_by_time(
            positioning_owner._aggregate_open_interest_by_time(rows), growth_window_days=result.growth_window_days
        )
        return positioning_owner._oi_growth_history(growth, observation_time=result.observation_time, zscore_window_days=result.zscore_window_days)


GUARDS = {
    "funding": Guard(
        "funding", "funding_health", "FUNDING_HEALTH_ZERO_VARIANCE_GUARD_V1", "FUNDING_HEALTH_ZERO_VARIANCE",
        "funding_zscore", "FUNDING_ZSCORE_180D", "FUNDING_HEALTH", DERIVATIVES_START, _funding_index, lambda i: FUNDING_CONSTANT,
    ),
    "basis": Guard(
        "basis", "futures_basis_health", "FUTURES_BASIS_ZERO_VARIANCE_GUARD_V1", "FUTURES_BASIS_ZERO_VARIANCE",
        "annualized_basis_zscore", "FUTURES_BASIS_ZSCORE_180D", "FUTURES_BASIS_HEALTH", DERIVATIVES_START,
        lambda instant: _day_index(instant, DERIVATIVES_START), lambda i: BASIS_CONSTANT,
    ),
    "growth": Guard(
        "growth", "open_interest_growth_health", "OI_GROWTH_ZERO_VARIANCE_GUARD_V1", "OI_GROWTH_ZERO_VARIANCE",
        "oi_growth_zscore", "OI_GROWTH_ZSCORE_180D", "OI_GROWTH_HEALTH", OI_START,
        lambda instant: _day_index(instant, OI_START), _oi_constant_growth,
    ),
}
# The downstream inputs that must never carry a refused owner's health or z.
DOWNSTREAM = {
    "funding": {
        "calculate_positioning_score": ("funding_health",),
        "calculate_crowding_flag": ("funding_zscore",),
        "calculate_stress_flag": ("funding_zscore",),
        "calculate_euphoria_flag": ("funding_zscore",),
        "calculate_capitulation_flag": ("funding_zscore",),
    },
    "basis": {
        "calculate_positioning_score": ("basis_health",),
        "calculate_crowding_flag": ("basis_zscore",),
        "calculate_stress_flag": ("basis_zscore",),
        "calculate_euphoria_flag": ("basis_zscore",),
    },
    "growth": {"calculate_positioning_score": ("oi_health",)},
}
# the owner's current quantity: the value at its latest visible observation
CURRENT_FIELD = {"funding": "funding_7d_avg", "basis": "annualized_basis_rate_avg", "growth": "oi_growth"}
RECORDED = ("calculate_positioning_score", "calculate_crowding_flag", "calculate_stress_flag", "calculate_euphoria_flag", "calculate_capitulation_flag")


def _decide_recording(inputs, instants, names=RECORDED):
    """Decide at consecutive instants on one composer, recording owner inputs."""

    calls: dict[str, list[Any]] = {name: [] for name in names}
    with pytest.MonkeyPatch.context() as patch:
        for name in names:
            real = getattr(entry_composer, name)

            def wrapper(*args, _real=real, _name=name, **kwargs):
                calls[_name].append(args[0])
                return _real(*args, **kwargs)

            patch.setattr(entry_composer, name, wrapper)
        composer = entry_composer.EntryComposer(inputs, strategy_config=CONFIG)
        rows = []
        for instant in instants:
            decision = composer.decide(instant)
            composer.record(decision)
            rows.append(decision.row)
    return rows, calls


def _decide(inputs, instants):
    composer = entry_composer.EntryComposer(inputs, strategy_config=CONFIG)
    rows = []
    for instant in instants:
        decision = composer.decide(instant)
        composer.record(decision)
        rows.append(decision.row)
    return rows


# --- shared scenario runs (module scope: each decision costs seconds) ------------------


@pytest.fixture(scope="module")
def constant_runs():
    runs = {}
    for key, guard in GUARDS.items():
        inputs = guard.scenario(guard.constant).build()
        rows, calls = _decide_recording(inputs, [T])
        runs[key] = {"inputs": inputs, "row": rows[0], "calls": calls}
    return runs


@pytest.fixture(scope="module")
def differing_runs():
    runs = {}
    for key, guard in GUARDS.items():
        current = guard.index(T)
        bump = Decimal(5) / Decimal(4) if key == "growth" else Decimal(2)

        def value_at(index, _guard=guard, _current=current, _bump=bump):
            value = _guard.constant(index)
            return value * _bump if index == _current else value

        inputs = guard.scenario(value_at).build()
        runs[key] = {"inputs": inputs, "row": _decide(inputs, [T])[0]}
    return runs


@pytest.fixture(scope="module")
def baseline():
    inputs = Scenario().build()
    rows, calls = _decide_recording(inputs, [T])
    return {"inputs": inputs, "row": rows[0], "calls": calls}


# --- the owners themselves are wrong on these constants (the guard is load-bearing) -----------


@pytest.mark.parametrize("key", sorted(GUARDS))
def test_the_frozen_owner_returns_a_complete_z_on_the_constant_history(key, constant_runs):
    guard = GUARDS[key]
    inputs = constant_runs[key]["inputs"]
    result = guard.owner_result(inputs, T)
    history = guard.owner_history(inputs, T)
    assert result.complete and result.reason_codes == ()
    assert getattr(result, guard.z_field) is not None and result.health_score is not None
    assert len(history) == result.history_observation_count >= 30
    assert all(value == history[0] for value in history)


# --- required test 1: a constant history refuses ------------------------------------------


@pytest.mark.parametrize("key", sorted(GUARDS))
def test_a_constant_history_refuses_with_the_owners_own_code(key, constant_runs):
    guard = GUARDS[key]
    row = constant_runs[key]["row"]
    owner = guard.owner_result(constant_runs[key]["inputs"], T)
    assert [(r.guard_id, r.owner, r.reason_code) for r in row.guard_refusals] == [(guard.guard_id, guard.owner, guard.code)]
    refusal = row.guard_refusals[0]
    assert refusal.history_observation_count == owner.history_observation_count
    assert refusal.observation_time == owner.observation_time
    assert row.features[guard.z_feature] is None and row.features[guard.health_feature] is None
    assert row.outcome == OUTCOME_STRUCTURALLY_UNEVALUABLE
    assert "POSITIONING_INCOMPLETE" in row.reasons
    positioning = {item.component: item.causes for item in row.unevaluable}["positioning"]
    assert guard.code in positioning
    cause = accounted_cause(guard.code)
    assert cause is not None and cause.authority == AUTHORITY_SPEC_GUARD and cause.reference == guard.guard_id
    assert row.unaccounted == ()
    # the guard id and its code are the frozen spec's
    assert guard.code in SPEC_GUARDS[guard.guard_id]["clauses"]["6_refusal"]
    assert guard.code in json.dumps(SPEC_GUARDS[guard.guard_id]["required_tests"])


@pytest.mark.parametrize("key", sorted(GUARDS))
def test_a_refused_owner_reaches_no_downstream_input(key, constant_runs):
    calls = constant_runs[key]["calls"]
    row = constant_runs[key]["row"]
    for name, fields in DOWNSTREAM[key].items():
        assert len(calls[name]) == 1, name
        for field in fields:
            assert getattr(calls[name][0], field) is None, (name, field)
    # the two unaffected owners still pass their values through
    other = {"funding": "basis_health", "basis": "funding_health", "growth": "funding_health"}[key]
    assert getattr(calls["calculate_positioning_score"][0], other) is not None
    # every withheld field is attributed, per field, to the refusal (contract clause 7)
    owner_type = {
        "calculate_positioning_score": "PositioningScoreInput",
        "calculate_crowding_flag": "CrowdingFlagInput",
        "calculate_stress_flag": "StressFlagInput",
        "calculate_euphoria_flag": "EuphoriaFlagInput",
        "calculate_capitulation_flag": "CapitulationFlagInput",
    }
    expected = {f"{owner_type[name]}.{field}" for name, fields in DOWNSTREAM[key].items() for field in fields}
    (refusal,) = row.guard_refusals
    assert set(refusal.withheld_inputs) == expected
    assert refusal.as_record()["withheld_inputs"] == list(refusal.withheld_inputs)
    clause = SPEC_GUARDS[GUARDS[key].guard_id]["clauses"]["6_refusal"]
    for item in refusal.withheld_inputs:
        assert item in clause or key == "growth", item


@pytest.mark.parametrize("key", ["funding", "basis"])
def test_a_refusal_leaves_the_hard_flags_failing_closed(key, constant_runs):
    row = constant_runs[key]["row"]
    crowding = row.flags["crowding"]
    assert crowding["complete"] is False and crowding["severe_crowding_state"] is None
    assert "CROWDING_INPUT_MISSING" in crowding["reason_codes"]
    # STRESS_NON_DISCRETIONARY_MISSING: a withheld STRESS input gives stress_flagged None
    assert row.flags["stress"]["mapped"] is None


# --- required test 2: a current value equal to the constant history ---------------------------


@pytest.mark.parametrize("key", sorted(GUARDS))
def test_a_current_value_equal_to_the_constant_history_refuses(key, constant_runs):
    guard = GUARDS[key]
    inputs = constant_runs[key]["inputs"]
    history = guard.owner_history(inputs, T)
    owner = guard.owner_result(inputs, T)
    current = getattr(owner, CURRENT_FIELD[key])
    assert current == history[0]
    assert [r.reason_code for r in constant_runs[key]["row"].guard_refusals] == [guard.code]


# --- required test 3: a current value different from the constant history ----------------------


@pytest.mark.parametrize("key", sorted(GUARDS))
def test_a_current_value_different_from_the_constant_history_refuses(key, differing_runs):
    guard = GUARDS[key]
    inputs = differing_runs[key]["inputs"]
    row = differing_runs[key]["row"]
    history = guard.owner_history(inputs, T)
    owner = guard.owner_result(inputs, T)
    current = getattr(owner, CURRENT_FIELD[key])
    assert all(value == history[0] for value in history)
    assert current != history[0]
    # the owner itself still reports a complete z for this instant
    assert owner.complete and getattr(owner, guard.z_field) is not None
    assert [r.reason_code for r in row.guard_refusals] == [guard.code]
    assert row.features[guard.z_feature] is None and row.features[guard.health_feature] is None
    assert row.unaccounted == ()


# --- required test 4: point-in-time exclusion ---------------------------------------------------


def _future_breaking_value(guard: Guard):
    # Constant up to and including T, non-constant after it.
    current = guard.index(T)

    def value_at(index):
        value = guard.constant(index)
        if index <= current:
            return value
        return value * (Decimal(1) + Decimal(index % 5 + 1) / Decimal(10))

    return value_at


def _late_rows(guard: Guard, inputs):
    """Rows observed before T but available only after it; they break constancy once visible."""

    late = T + HOUR
    if guard.key == "funding":
        rows = [
            FundingRate(
                observation_time=T - timedelta(hours=4) - DAY * offset,
                exchange="binance",
                symbol="BTCUSDT",
                instrument="BTCUSDT-PERP",
                funding_rate=FUNDING_CONSTANT * 3,
                funding_interval_hours=Decimal("8"),
                provider="binance",
                source="fixture-late-revision",
                available_at=late,
                ingested_at=BULK_INGESTED_AT,
            )
            for offset in (2, 9)
        ]
        shared = inputs.dataset.shared_snapshot
        dataset = replace(inputs.dataset, shared_snapshot=replace(shared, funding_rates=(*shared.funding_rates, *rows)))
        return replace(inputs, dataset=dataset)
    if guard.key == "basis":
        rows = [
            FuturesBasis(
                observation_time=T - timedelta(hours=12) - DAY * offset,
                exchange="binance",
                symbol="BTCUSD",
                instrument="BTCUSD-QUARTERLY",
                expiry=T + DAY * 60,
                basis_rate=Decimal("0.01"),
                annualized_basis_rate=BASIS_CONSTANT * 3,
                provider="binance",
                source="fixture-late-revision",
                available_at=late,
                ingested_at=BULK_INGESTED_AT,
            )
            for offset in (2, 9)
        ]
        return replace(inputs, futures_basis=(*inputs.futures_basis, *rows))
    shared = inputs.dataset.shared_snapshot
    rows = []
    for offset in (2, 9):
        observed = T - timedelta(hours=12) - DAY * offset
        rows.append(
            OpenInterest(
                observation_time=observed,
                exchange="binance",
                symbol="BTCUSDT",
                instrument="BTCUSDT-PERP",
                open_interest=Decimal(10**20),
                open_interest_unit="USD",
                provider="binance",
                source="fixture-late-revision",
                available_at=late,
                ingested_at=BULK_INGESTED_AT,
            )
        )
        # another unit, visible at T: the unit filter keeps it out of H
        rows.append(replace(rows[-1], open_interest_unit="BTC", open_interest=Decimal(17 + offset), available_at=observed))
    dataset = replace(inputs.dataset, shared_snapshot=replace(shared, open_interest=(*shared.open_interest, *rows)))
    return replace(inputs, dataset=dataset)


@pytest.fixture(scope="module")
def pit_runs():
    runs = {}
    for key, guard in GUARDS.items():
        future = guard.scenario(_future_breaking_value(guard)).build()
        late = _late_rows(guard, guard.scenario(guard.constant).build())
        runs[key] = {
            "future": future,
            "future_rows": _decide(future, [T, T + 3 * DAY]),
            "late": late,
            "late_rows": _decide(late, [T, T + DAY]),
        }
    return runs


@pytest.mark.parametrize("key", sorted(GUARDS))
def test_rows_observed_after_t_never_join_the_history(key, pit_runs):
    guard = GUARDS[key]
    at_t, later = pit_runs[key]["future_rows"]
    assert [r.reason_code for r in at_t.guard_refusals] == [guard.code]
    assert at_t.features[guard.z_feature] is None
    # Once those rows are visible the history is no longer constant: the owner's
    # own z passes through unchanged (the exclusion above is not vacuous).
    owner = guard.owner_result(pit_runs[key]["future"], T + 3 * DAY)
    assert later.guard_refusals == ()
    assert later.features[guard.z_feature] == getattr(owner, guard.z_field) is not None
    assert later.features[guard.health_feature] == owner.health_score


@pytest.mark.parametrize("key", sorted(GUARDS))
def test_rows_available_after_t_never_join_the_history(key, pit_runs):
    guard = GUARDS[key]
    at_t, next_day = pit_runs[key]["late_rows"]
    assert [r.reason_code for r in at_t.guard_refusals] == [guard.code]
    assert at_t.features[guard.z_feature] is None and at_t.features[guard.health_feature] is None
    late = pit_runs[key]["late"]
    if key == "growth":
        # A visible row of another unit never joins H, and the late USD rows
        # make H non-constant once available.
        assert any(r.open_interest_unit == "BTC" and r.available_at <= T for r in late.dataset.shared_snapshot.open_interest)
    owner = guard.owner_result(late, T + DAY)
    assert not all(value == guard.owner_history(late, T + DAY)[0] for value in guard.owner_history(late, T + DAY))
    assert next_day.guard_refusals == ()
    assert next_day.features[guard.z_feature] == getattr(owner, guard.z_field) is not None


# --- required test 5: non-constant histories pass through unchanged -----------------------------


@pytest.mark.parametrize("key", sorted(GUARDS))
def test_a_non_constant_history_passes_the_owner_through_unchanged(key, baseline):
    guard = GUARDS[key]
    row = baseline["row"]
    owner = guard.owner_result(baseline["inputs"], T)
    assert owner.complete
    assert row.guard_refusals == ()
    assert row.features[guard.z_feature] == getattr(owner, guard.z_field)
    assert row.features[guard.health_feature] == owner.health_score
    field = {"funding": "funding_health", "basis": "basis_health", "growth": "oi_health"}[key]
    assert getattr(baseline["calls"]["calculate_positioning_score"][0], field) == owner.health_score


@pytest.fixture(scope="module")
def tiny_runs():
    runs = {}
    for key, guard in GUARDS.items():
        target = guard.index(T - 10 * DAY)
        bump = Decimal(1) if key == "growth" else Decimal("1e-20")

        def value_at(index, _guard=guard, _target=target, _bump=bump):
            value = _guard.constant(index)
            return value + _bump if index == _target else value

        inputs = guard.scenario(value_at).build()
        runs[key] = {"inputs": inputs, "row": _decide(inputs, [T])[0]}
    return runs


@pytest.mark.parametrize("key", sorted(GUARDS))
def test_the_guard_uses_exact_equality_with_no_tolerance(key, tiny_runs):
    guard = GUARDS[key]
    inputs = tiny_runs[key]["inputs"]
    row = tiny_runs[key]["row"]
    history = guard.owner_history(inputs, T)
    distinct = set(history)
    assert len(distinct) > 1
    spread = max(distinct) - min(distinct)
    assert spread < Decimal("1e-15") * max(abs(value) for value in distinct)
    owner = guard.owner_result(inputs, T)
    assert row.guard_refusals == ()
    assert row.features[guard.z_feature] == getattr(owner, guard.z_field) is not None
    assert row.features[guard.health_feature] == owner.health_score


@pytest.fixture(scope="module")
def owner_refusal_runs():
    # A terminating constant: the owner's own zero-variance refusal fires.
    inputs = Scenario(funding_at=lambda index: Decimal("0.0001")).build()
    return {"inputs": inputs, "rows": _decide(inputs, [utc(2023, 6, 1), T])}


def test_the_guard_never_relabels_an_owner_refusal(owner_refusal_runs):
    warm_up, constant = owner_refusal_runs["rows"]
    owner = GUARDS["funding"].owner_result(owner_refusal_runs["inputs"], T)
    assert owner.funding_zscore is None and owner.reason_codes == ("FUNDING_HEALTH_ZERO_VARIANCE",)
    # clause 2: R stands unchanged and the guard does nothing
    assert constant.guard_refusals == () and warm_up.guard_refusals == ()
    assert constant.owner_reason_codes["funding_health"]["reason_codes"] == ["FUNDING_HEALTH_ZERO_VARIANCE"]
    assert "FUNDING_HEALTH_ZERO_VARIANCE" in {item.component: item.causes for item in constant.unevaluable}["positioning"]
    assert "FUNDING_HEALTH_INSUFFICIENT_HISTORY" in {item.component: item.causes for item in warm_up.unevaluable}["positioning"]
    assert constant.unaccounted == () and warm_up.unaccounted == ()


def test_the_guard_never_restates_the_owners_z_score():
    tree = ast.parse(Path(entry_composer.__file__).read_text(encoding="utf-8"))
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    names |= {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    names |= {alias.asname or alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) for alias in node.names}
    assert not {"_zscore", "_average", "sqrt", "stdev", "pstdev", "variance", "mean", "fsum"} & names
    roots = composer_boundary.static_call_census(entry_composer).roots_called
    assert "btc_predictor.features.positioning._zscore" not in roots
    # the guard reads history only through the spec's own helpers, all census roots
    helpers = {helper["symbol"] for item in SPEC_GUARDS.values() for helper in item["history_helpers"]}
    assert len(helpers) == 10 and helpers <= roots  # three owners and their seven history helpers


# --- the guard also runs on the Setup B prior-instant histories ---------------------------------


@pytest.fixture(scope="module")
def history_guard_run():
    # Funding is constant up to T - 2 days and varies afterwards, so the guard
    # refuses at the earlier instants of Setup B's 7-day history but not at T.
    switch = _funding_index(T - 2 * DAY)

    def funding_at(index):
        if index <= switch:
            return FUNDING_CONSTANT
        return FUNDING_CONSTANT * (Decimal(1) + Decimal(index % 7) / Decimal(10))

    inputs = Scenario(funding_at=funding_at).build()
    rows, calls = _decide_recording(inputs, [T], names=("detect_bullish_reset",))
    return {"inputs": inputs, "row": rows[0], "calls": calls}


def test_setup_b_health_history_applies_the_guard_at_each_prior_instant(history_guard_run):
    guard = GUARDS["funding"]
    inputs = history_guard_run["inputs"]
    row = history_guard_run["row"]
    assert row.guard_refusals == ()
    (reset_input,) = history_guard_run["calls"]["detect_bullish_reset"]
    lookback = int(CONFIG.setup_requirements.bullish_reset["funding_health_improving_days"])
    history = reset_input.funding_health_history
    assert len(history) == lookback + 1
    expected = []
    for days_back in range(lookback, -1, -1):
        instant = T - days_back * DAY
        owner = guard.owner_result(inputs, instant)
        prior = guard.owner_history(inputs, instant)
        refused = owner.funding_zscore is not None and all(value == prior[0] for value in prior)
        expected.append(None if refused else owner.health_score)
    assert tuple(history) == tuple(expected)
    assert None in expected and expected[-1] is not None


# --- UNIFORM_ZSCORE_V1 (spec uniform rule application contract) -------------------------------


@pytest.mark.parametrize("value", NON_TERMINATING)
@pytest.mark.parametrize("same_current", [True, False])
@pytest.mark.parametrize("accumulator", [np.longdouble, np.float64])
@pytest.mark.parametrize("size", [20, 730])
def test_uniform_zscore_refuses_a_constant_history_before_the_helper(value, same_current, accumulator, size, monkeypatch):
    monkeypatch.setattr(quant_rolling.np, "longdouble", accumulator)

    def forbidden(*args, **kwargs):
        pytest.fail("an exactly constant history reached the numerical helper")

    monkeypatch.setattr(entry_composer, "rolling_zscore", forbidden)
    current = value if same_current else value * 2
    assert _uniform_zscore((*[value] * size, current), input_id="TREND_Z_M4") == (None, "TREND_Z_M4_ZERO_VARIANCE")


def test_the_64_bit_accumulator_counterexample_is_refused(monkeypatch):
    monkeypatch.setattr(quant_rolling.np, "longdouble", np.float64)
    value = Decimal(1) / 3
    assert rolling_zscore([*[value] * 730, value], window=730, min_periods=30)[-1] == -1
    assert _uniform_zscore((*[value] * 730, value), input_id="FLOW_Z_FLOW_ACCEL") == (None, "FLOW_Z_FLOW_ACCEL_ZERO_VARIANCE")


def _recording_zscore(monkeypatch):
    calls = []
    real = entry_composer.rolling_zscore

    def wrapper(values, **kwargs):
        calls.append((tuple(values), kwargs))
        return real(values, **kwargs)

    monkeypatch.setattr(entry_composer, "rolling_zscore", wrapper)
    return calls


def test_uniform_zscore_uses_the_last_20_defined_prior_observations(monkeypatch):
    calls = _recording_zscore(monkeypatch)
    prior = [Decimal(index % 7) / 3 for index in range(40)]
    # an older outlier beyond the last 20 defined observations changes nothing
    with_outlier = [Decimal(10**6), *prior]
    gapped = []
    for index, value in enumerate(prior):
        gapped.append(value)
        if index % 3 == 0:
            gapped.append(None)
    current = Decimal("2.5")
    z, cause = _uniform_zscore((*prior, current), input_id="TREND_Z_M12")
    assert cause is None
    assert _uniform_zscore((*with_outlier, current), input_id="TREND_Z_M12") == (z, None)
    assert _uniform_zscore((*gapped, current), input_id="TREND_Z_M12") == (z, None)
    assert z == rolling_zscore((*prior[-20:], current), window=20, min_periods=20, sample=False)[-1]
    for values, kwargs in calls:
        assert values == (*prior[-20:], current)
        assert kwargs == {"window": 20, "min_periods": completion_spec.UNIFORM_ZSCORE_MIN_OBSERVATIONS, "sample": False}
    # a population z computed independently on the same 20 values
    mean = sum(prior[-20:]) / 20
    sd = (sum((value - mean) ** 2 for value in prior[-20:]) / 20).sqrt()
    assert abs(Decimal(repr(float(z))) - (current - mean) / sd) < Decimal("1e-9")


def test_uniform_zscore_needs_20_defined_prior_observations(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("a short or missing series reached the numerical helper")

    monkeypatch.setattr(entry_composer, "rolling_zscore", forbidden)
    nineteen = [Decimal(index) for index in range(19)]
    spread = [value for index in range(19) for value in (Decimal(index), None)]
    assert _uniform_zscore((*nineteen, Decimal(3)), input_id="TREND_Z_20W") == (None, "TREND_Z_20W_INSUFFICIENT_HISTORY")
    assert _uniform_zscore((*spread, Decimal(3)), input_id="TREND_Z_20W") == (None, "TREND_Z_20W_INSUFFICIENT_HISTORY")
    assert _uniform_zscore((*nineteen, Decimal(1), None), input_id="TREND_Z_20W") == (None, "TREND_Z_20W_INPUT_MISSING")
    assert _uniform_zscore((), input_id="TREND_Z_20W") == (None, "TREND_Z_20W_INPUT_MISSING")


def test_uniform_zscore_counts_twenty_defined_values_across_gaps():
    values = []
    for index in range(20):
        values.extend((Decimal(index % 5) / 7, None, None))
    current = Decimal("0.9")
    z, cause = _uniform_zscore((*values, current), input_id="TREND_Z_52H")
    defined = [value for value in values if value is not None]
    assert cause is None and len(defined) == 20
    assert z == rolling_zscore((*defined, current), window=20, min_periods=20, sample=False)[-1]


@pytest.mark.parametrize("difference", [Decimal("1e-27"), Decimal("1e-12")])
def test_uniform_zscore_passes_an_exact_tiny_difference(difference, monkeypatch):
    # The spec refuses only an exactly constant history; any exact difference
    # reaches the helper, whose own result is then used unchanged.
    calls = _recording_zscore(monkeypatch)
    history = (*[Decimal("0.1")] * 19, Decimal("0.1") + difference)
    current = Decimal("0.1")
    value, cause = _uniform_zscore((*history, current), input_id="FLOW_Z_ETF_NORM_5D")
    assert len(calls) == 1
    helper = rolling_zscore((*history, current), window=20, min_periods=20, sample=False)[-1]
    if helper is None:
        # float conversion inside the helper erased the difference: its own refusal
        assert (value, cause) == (None, "FLOW_Z_ETF_NORM_5D_ZERO_VARIANCE")
    else:
        assert (value, cause) == (helper, None)
    assert (helper is None) == (difference == Decimal("1e-27"))


# --- UNIFORM_PERCENTILE_V1 ----------------------------------------------------------------------


def _daily(start, count, value_at):
    return [(start + DAY * index, value_at(index)) for index in range(count)]


def test_uniform_percentile_selects_history_by_time(monkeypatch):
    start = utc(2021, 1, 1)
    observations = _daily(start, 800, lambda index: Decimal(index % 37) / 11)
    now, current = observations[-1]
    window_start = now - timedelta(days=completion_spec.UNIFORM_PERCENTILE_WINDOW_DAYS)
    expected_history = [value for moment, value in observations[:-1] if window_start <= moment < now]
    assert len(expected_history) == 730
    calls = []
    real = entry_composer.rolling_percentile

    def wrapper(values, **kwargs):
        calls.append((tuple(values), kwargs))
        return real(values, **kwargs)

    monkeypatch.setattr(entry_composer, "rolling_percentile", wrapper)
    value, cause = _uniform_percentile(observations, input_id="RANGE_PERCENTILE")
    assert cause is None
    assert calls == [((*expected_history, current), {"window": 730, "min_periods": completion_spec.UNIFORM_PERCENTILE_MIN_OBSERVATIONS})]
    assert value == rolling_percentile((*expected_history, current), window=730, min_periods=365)[-1]


def test_uniform_percentile_window_boundaries():
    now = utc(2023, 6, 1)
    window_start = now - timedelta(days=730)
    base = [(window_start + DAY * (index + 1), Decimal(index % 13)) for index in range(400)]
    at_start = (window_start, Decimal(1000))
    before = (window_start - timedelta(seconds=1), Decimal(-1000))
    current = Decimal(6)
    with_start, _ = _uniform_percentile([*base, at_start, (now, current)], input_id="RANGE_PERCENTILE")
    without, _ = _uniform_percentile([*base, (now, current)], input_id="RANGE_PERCENTILE")
    with_before, _ = _uniform_percentile([before, *base, (now, current)], input_id="RANGE_PERCENTILE")
    assert with_start != without  # an observation exactly at D - 730 days is included
    assert with_before == without  # one a second earlier is excluded
    # the current observation never joins its own history
    assert _uniform_percentile([*base, (now, current)], input_id="RANGE_PERCENTILE") == (without, None)


def test_uniform_percentile_minimum_history_and_missing_values():
    now = utc(2023, 6, 1)
    history = [(now - DAY * (index + 1), Decimal(index)) for index in range(364)]
    assert _uniform_percentile([*history, (now, Decimal(1))], input_id="RANGE_PERCENTILE") == (None, "RANGE_PERCENTILE_INSUFFICIENT_HISTORY")
    padded = [*history, *((now - DAY * (400 + index), None) for index in range(10))]
    assert _uniform_percentile([*padded, (now, Decimal(1))], input_id="RANGE_PERCENTILE") == (None, "RANGE_PERCENTILE_INSUFFICIENT_HISTORY")
    gaps = [(moment, None if index % 2 else value) for index, (moment, value) in enumerate(history + [(now - DAY * 365, Decimal(7))])]
    assert _uniform_percentile([*gaps, (now, Decimal(1))], input_id="RANGE_PERCENTILE")[1] == "RANGE_PERCENTILE_INSUFFICIENT_HISTORY"
    full = [*history, (now - DAY * 365, Decimal(7))]
    value, cause = _uniform_percentile([*full, (now, Decimal(1))], input_id="RANGE_PERCENTILE")
    assert cause is None and value is not None
    assert _uniform_percentile([*full, (now, None)], input_id="RANGE_PERCENTILE") == (None, "RANGE_PERCENTILE_INPUT_MISSING")
