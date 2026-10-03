"""Independent RBT-002A review regressions; synthetic contract witnesses only.

The composers do not exist yet. These exercise the frozen contract's exact
predicate and row-helper adaptation, not a claim of RBT-004 implementation.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import numpy as np
import pytest

from btc_predictor.features.rolling import rolling_percentile, rolling_zscore
from btc_predictor.features import positioning
from btc_predictor.quant import rolling as quant_rolling
from btc_predictor.research_backtest import completion_spec as spec


def _contract_z(history, current, helper=rolling_zscore):
    contract = dict(spec.UNIFORM_ZSCORE.application_contract)
    assert "BEFORE float conversion" in contract["constant_history_refusal"]
    assert "without calling the helper" in contract["constant_history_refusal"]
    assert "window=len(H)" in contract["owner_call"]
    if current is None or len(history) < spec.UNIFORM_ZSCORE_MIN_OBSERVATIONS:
        return None
    predicate = contract["constant_history_predicate"]
    # Execute the frozen predicate over original Decimals, without a mean or
    # variance calculation. The exact text is independently pinned below.
    assert predicate == "all(h == H[0] for h in H)"
    if eval(predicate, {"__builtins__": {"all": all}, "H": history}):
        return None
    return helper(
        [*history, current], window=len(history),
        min_periods=spec.UNIFORM_ZSCORE_MIN_OBSERVATIONS, sample=False,
    )[-1]


@pytest.mark.parametrize("value", [Decimal("0.1"), Decimal(1) / 3, Decimal("0.015") * 365 / 90])
@pytest.mark.parametrize("same_current", [True, False])
@pytest.mark.parametrize("accumulator", [np.longdouble, np.float64])
def test_exact_refusal_precedes_the_owner_at_full_window(value, same_current, accumulator, monkeypatch):
    monkeypatch.setattr(quant_rolling.np, "longdouble", accumulator)
    history = [value] * 730
    current = value if same_current else value + 1

    def forbidden_helper(*args, **kwargs):
        pytest.fail("exactly constant history reached the numerical helper")

    assert _contract_z(history, current, forbidden_helper) is None


def test_the_64_bit_owner_counterexample_is_real(monkeypatch):
    monkeypatch.setattr(quant_rolling.np, "longdouble", np.float64)
    value = Decimal(1) / 3
    history = [value] * 730
    # The existing frozen owner, unedited, does not supply the promised exact
    # refusal on this supported accumulator width.
    assert rolling_zscore([*history, value], window=730, min_periods=30)[-1] == -1
    assert _contract_z(history, value) is None


def test_nonconstant_history_uses_the_owner_without_a_tolerance():
    history = [Decimal(index % 11) / 3 for index in range(730)]
    current = Decimal("2.25")
    expected = rolling_zscore([*history, current], window=730, min_periods=30, sample=False)[-1]
    assert _contract_z(history, current) == expected
    # An arbitrarily small exact difference must still reach the owner.
    close = [Decimal("0.1")] * 729 + [Decimal("0.1000000000000000000000000001")]
    calls = []

    def witness(values, **kwargs):
        calls.append((values, kwargs))
        return (Decimal("17"),)

    assert _contract_z(close, current, witness) == Decimal("17")
    assert len(calls) == 1


def test_time_selected_history_maps_to_row_count_without_backfilling_gaps():
    current_time = datetime(2025, 1, 1, tzinfo=UTC)
    lower = current_time - timedelta(days=730)
    points = [(current_time - timedelta(days=i), Decimal(i % 13)) for i in range(800)]
    # A gap removes observations; it never moves the lower time boundary.
    points = [(time, value) for time, value in points if time.day % 5]
    points += [(lower, Decimal("42")), (current_time + timedelta(days=1), Decimal("999"))]
    history = [value for time, value in sorted(points) if lower <= time < current_time]
    assert len(history) < 730
    assert Decimal("999") not in history
    calls = []

    def witness(values, **kwargs):
        calls.append((values, kwargs))
        return (Decimal("17"),)

    assert _contract_z(history, Decimal("4"), witness) == Decimal("17")
    assert calls[0][0] == [*history, Decimal("4")]
    assert calls[0][1] == {"window": len(history), "min_periods": 30, "sample": False}
    contract = dict(spec.UNIFORM_PERCENTILE.application_contract)
    assert "window=len(H)" in contract["owner_call"]
    assert "never extend the time window" in contract["history_selection"]
    expected = (sum(h < 4 for h in history) + .5 * sum(h == 4 for h in history)) / len(history) * 100
    actual = rolling_percentile([*history, Decimal(4)], window=len(history), min_periods=365)[-1]
    assert float(actual) == pytest.approx(expected)


@pytest.mark.parametrize(
    "guard,owner,reason,helpers",
    [
        ("FUTURES_BASIS_ZERO_VARIANCE_GUARD_V1", "futures_basis_health", "FUTURES_BASIS_ZERO_VARIANCE",
         {"_futures_basis_averages_by_time", "_futures_basis_history"}),
        ("FUNDING_HEALTH_ZERO_VARIANCE_GUARD_V1", "funding_health", "FUNDING_HEALTH_ZERO_VARIANCE",
         {"_funding_averages_by_time", "_funding_average_history"}),
        ("OI_GROWTH_ZERO_VARIANCE_GUARD_V1", "open_interest_growth_health", "OI_GROWTH_ZERO_VARIANCE",
         {"_aggregate_open_interest_by_time", "_open_interest_growth_by_time", "_oi_growth_history"}),
    ],
)
def test_v7_guard_contract_is_owner_specific(guard, owner, reason, helpers):
    records = {item.guard_id: item.as_record() for item in spec.POSITIONING_GUARDS}
    record = records[guard]
    promoted = {item["symbol"].rsplit(".", 1)[-1] for item in record["history_helpers"] if item["census"] == "PROMOTE_TO_CENSUS_ROOT"}
    assert promoted == helpers
    assert all(callable(getattr(positioning, name)) for name in helpers)
    assert f"{owner}(rows, as_of=t)" in record["clauses"]["1_owner_result"]
    assert reason in record["clauses"]["6_refusal"]
    assert "no health score" in record["clauses"]["6_refusal"]
    assert "no z-score" in record["clauses"]["6_refusal"]
    assert "STRUCTURALLY_UNEVALUABLE" in record["clauses"]["7_structural_unevaluability"]
    assert "Decimal ==" in record["clauses"]["5_equality"]
    assert "whether or not" in record["clauses"]["5_equality"]
    assert "available_at" in record["clauses"]["3_visible_rows"]
    assert "observation_time" in record["clauses"]["3_visible_rows"]
    assert len(record["required_tests"]) == 5
    assert "equal" in record["required_tests"][1]
    assert "different" in record["required_tests"][2]
    assert "point-in-time" in record["required_tests"][3]
    assert "non-constant" in record["required_tests"][4]


def test_v7_guard_roots_and_accepted_overlap_are_frozen():
    record = spec.spec_definition()
    assert record["policy"] == "RESEARCH_BACKTEST_POLICY_V7"
    assert len(record["positioning_zero_variance_guards"]) == 3
    assert len(record["composer_roots_to_promote"]) == 14
    limitations = {item["limitation_id"]: item["statement"] for item in record["named_limitations"]}
    assert "Guarded limitation" in limitations["E1_CLASS_FUNDING_AND_OI_GROWTH"]
    overlap = limitations["MOMENTUM_PERSISTENCE_OVERLAP"]
    assert "ACCEPTED unchanged" in overlap
    assert "RBT-006" in overlap and "RBT-007" in overlap
    assert "SENSITIVITY_ONLY_NOT_SELECTION" in overlap
    assert "never on holdout" in overlap
    assert "ACCEPTED" in record["surfaced_for_review"][0]
    assert "GUARDED" in record["surfaced_for_review"][1]
