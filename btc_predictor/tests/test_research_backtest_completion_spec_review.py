"""Independent RBT-002A review regressions; synthetic contract witnesses only.

The composers do not exist yet. These exercise the frozen contract's exact
predicate and row-helper adaptation, not a claim of RBT-004 implementation.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import numpy as np
import pytest

from btc_predictor.features.rolling import rolling_percentile, rolling_zscore
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
