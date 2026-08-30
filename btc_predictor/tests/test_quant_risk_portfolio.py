from decimal import Decimal

import numpy as np
import pytest

from btc_predictor.quant import (
    POSITION_SIDES,
    NumericInputError,
    capital_at_risk,
    gross_exposure,
    max_allowed_notional,
    net_exposure,
    position_notional,
    realized_pnl,
    reward_risk_ratio,
    risk_at_stop,
    risk_contribution_by_tranche,
    risk_improvement,
    stop_distance,
    unrealized_pnl,
    weighted_average_entry,
)


def test_position_side_contract_is_explicit() -> None:
    assert POSITION_SIDES == ("long", "short")


def test_stop_distance_handles_long_short_and_profitable_stops() -> None:
    assert stop_distance(100, 90, side="long") == pytest.approx(0.1)
    assert stop_distance(100, 110, side="short") == pytest.approx(0.1)
    np.testing.assert_array_equal(
        stop_distance([100, 100], [90, 105], side="long"),
        [0.1, 0],
    )
    np.testing.assert_array_equal(
        stop_distance([100, 100], [95, 110], side="short"),
        [0, 0.1],
    )


def test_reward_risk_ratio_supports_long_short_and_invalid_geometry() -> None:
    assert reward_risk_ratio(100, 90, 125, side="long") == 2.5
    assert reward_risk_ratio(100, 110, 75, side="short") == 2.5
    result = reward_risk_ratio(
        [100, 100, 100],
        [90, 100, 90],
        [120, 120, 95],
        side="long",
    )

    assert result[0] == 2
    assert np.isnan(result[1])
    assert np.isnan(result[2])


def test_reward_risk_ratio_matches_existing_structure_decimal_formula() -> None:
    cases = (
        ("100", "90", "125"),
        ("100", "85", "130"),
        ("97500", "91250", "112345"),
    )

    for entry_text, stop_text, target_text in cases:
        entry = Decimal(entry_text)
        stop = Decimal(stop_text)
        target = Decimal(target_text)
        expected = (target - entry) / (entry - stop)
        result = reward_risk_ratio(
            float(entry),
            float(stop),
            float(target),
            side="long",
        )
        assert result == pytest.approx(float(expected), rel=1e-12, abs=1e-12)


def test_position_notional_and_capital_at_risk_support_scalar_expansion() -> None:
    assert position_notional(0.05, 100_000) == 5_000
    np.testing.assert_array_equal(
        position_notional([0.05, 0.10], 100_000),
        [5_000, 10_000],
    )
    assert capital_at_risk(100_000, 0.005) == 500
    np.testing.assert_array_equal(
        capital_at_risk([100_000, 200_000], 0.005),
        [500, 1_000],
    )


def test_long_risk_at_stop_matches_rulebook_notional_formula() -> None:
    notionals = np.asarray([5_000, 3_000, 2_000])
    entries = np.asarray([100_000, 110_000, 120_000])
    stop = 105_000
    expected = np.asarray(
        [
            0,
            3_000 * (110_000 - stop) / 110_000,
            2_000 * (120_000 - stop) / 120_000,
        ]
    )

    contributions = risk_contribution_by_tranche(
        notionals,
        entries,
        stop,
        side="long",
    )

    np.testing.assert_allclose(contributions, expected)
    assert risk_at_stop(notionals, entries, stop, side="long") == pytest.approx(
        expected.sum()
    )
    assert np.all(contributions >= 0)


def test_short_risk_at_stop_is_symmetric_and_never_negative() -> None:
    notionals = [5_000, 3_000, 2_000]
    entries = [100_000, 90_000, 80_000]
    stop = 95_000
    expected = [0, 3_000 * 5_000 / 90_000, 2_000 * 15_000 / 80_000]

    contributions = risk_contribution_by_tranche(
        notionals,
        entries,
        stop,
        side="short",
    )

    np.testing.assert_allclose(contributions, expected)
    assert risk_at_stop(notionals, entries, stop, side="short") == pytest.approx(
        sum(expected)
    )
    assert np.all(contributions >= 0)


def test_quantity_and_notional_risk_formulas_are_equivalent() -> None:
    quantities = np.asarray([0.05, 0.025, 0.01])
    entries = np.asarray([100_000, 110_000, 120_000])
    stop = 90_000
    notionals = position_notional(quantities, entries)
    quantity_risk = np.sum(quantities * np.maximum(entries - stop, 0))

    assert risk_at_stop(notionals, entries, stop, side="long") == pytest.approx(
        quantity_risk
    )


def test_arbitrary_tranche_count_matches_independent_python_oracle() -> None:
    generator = np.random.Generator(np.random.PCG64(47))
    entries = generator.uniform(80_000, 120_000, size=257)
    notionals = generator.uniform(100, 10_000, size=257)
    stop = 95_000.0
    expected = sum(
        notional * max((entry - stop) / entry, 0)
        for notional, entry in zip(notionals, entries)
    )

    result = risk_at_stop(notionals, entries, stop, side="long")

    assert result == pytest.approx(expected, rel=1e-12, abs=1e-12)


def test_risk_improvement_uses_total_portfolio_risk_before_clipping() -> None:
    assert risk_improvement([500, 500, 200], [300, 600, 200]) == 100
    assert risk_improvement(500, 300) == 200
    assert risk_improvement(300, 500) == 0
    assert risk_improvement([100, 100], [0, 300]) == 0
    np.testing.assert_array_equal(
        risk_improvement(
            [[500, 500, 200], [100, 100, 100]],
            [[300, 600, 200], [0, 300, 100]],
        ),
        [100, 0],
    )


def test_max_allowed_notional_reproduces_rulebook_position_sizing() -> None:
    assert max_allowed_notional(100_000, 0.005, 0.10) == pytest.approx(5_000)
    np.testing.assert_allclose(
        max_allowed_notional(100_000, [0.0035, 0.005, 0.006], 0.10),
        [3_500, 5_000, 6_000],
    )


def test_weighted_average_entry_supports_arbitrary_tranches() -> None:
    assert weighted_average_entry([100, 110, 90], [1, 2, 1]) == 102.5
    assert weighted_average_entry(100, 2) == 100


def test_unrealized_and_realized_pnl_are_signed_for_long_and_short_positions() -> None:
    np.testing.assert_array_equal(
        unrealized_pnl([100, 100], [110, 90], 2, side="long"),
        [20, -20],
    )
    np.testing.assert_array_equal(
        unrealized_pnl([100, 100], [110, 90], 2, side="short"),
        [-20, 20],
    )
    assert realized_pnl(100, 125, 0.5, side="long") == 12.5
    assert realized_pnl(100, 75, 0.5, side="short") == 12.5


def test_gross_and_net_exposure_handle_mixed_directions() -> None:
    notionals = [10_000, 4_000, 2_500]
    sides = ["long", "short", "long"]

    assert gross_exposure(notionals) == 16_500
    assert net_exposure(notionals, sides) == 8_500
    assert net_exposure(notionals, "short") == -16_500


def test_portfolio_matrices_return_one_aggregate_per_observation_row() -> None:
    notionals = np.asarray([[1_000, 2_000], [3_000, 4_000]], dtype=np.float64)
    entries = np.asarray([[100, 100], [100, 100]], dtype=np.float64)
    entry_prices = np.asarray([[100, 110], [200, 220]], dtype=np.float64)
    quantities = np.ones((2, 2), dtype=np.float64)
    sides = [["long", "short"], ["long", "short"]]

    np.testing.assert_array_equal(
        risk_at_stop(notionals, entries, 90, side="long"),
        [300, 700],
    )
    np.testing.assert_array_equal(gross_exposure(notionals), [3_000, 7_000])
    np.testing.assert_array_equal(net_exposure(notionals, sides), [-1_000, -1_000])
    np.testing.assert_array_equal(
        weighted_average_entry(entry_prices, quantities),
        [105, 210],
    )


def test_matrix_aggregates_match_independent_single_portfolio_calls() -> None:
    notionals = np.asarray([[1_000, 2_000], [3_000, 4_000]], dtype=np.float64)
    entries = np.asarray([[100, 110], [120, 130]], dtype=np.float64)
    quantities = np.asarray([[1, 2], [3, 4]], dtype=np.float64)
    sides = np.asarray([["long", "short"], ["short", "long"]], dtype=object)

    np.testing.assert_array_equal(
        risk_at_stop(notionals, entries, 90, side="long"),
        [
            risk_at_stop(row_n, row_e, 90, side="long")
            for row_n, row_e in zip(notionals, entries)
        ],
    )
    np.testing.assert_array_equal(
        gross_exposure(notionals),
        [gross_exposure(row) for row in notionals],
    )
    np.testing.assert_array_equal(
        net_exposure(notionals, sides),
        [net_exposure(row, row_sides) for row, row_sides in zip(notionals, sides)],
    )
    np.testing.assert_array_equal(
        weighted_average_entry(entries, quantities),
        [weighted_average_entry(row, row_q) for row, row_q in zip(entries, quantities)],
    )


def test_net_exposure_uses_stable_summation_for_nearly_hedged_positions() -> None:
    assert net_exposure([1e16, 1, 1e16], ["long", "long", "short"]) == 1


def test_empty_portfolio_behavior_is_explicit() -> None:
    assert risk_at_stop([], [], 100, side="long") == 0
    assert risk_contribution_by_tranche([], [], 100, side="long").shape == (0,)
    assert gross_exposure([]) == 0
    assert net_exposure([], []) == 0
    assert np.isnan(weighted_average_entry([], []))
    assert risk_at_stop(np.empty((0, 2)), np.empty((0, 2)), 100, side="long").shape == (
        0,
    )
    np.testing.assert_array_equal(gross_exposure(np.empty((2, 0))), [0, 0])
    assert np.all(np.isnan(weighted_average_entry(np.empty((2, 0)), np.empty((2, 0)))))


def test_nan_requires_explicit_propagation_and_is_never_zero_filled() -> None:
    with pytest.raises(NumericInputError, match="NaN"):
        risk_at_stop([5_000, np.nan], [100, 110], 90, side="long")
    with pytest.raises(NumericInputError, match="NaN"):
        unrealized_pnl([100, np.nan], 110, 1, side="long")

    risk = risk_at_stop(
        [5_000, np.nan],
        [100, 110],
        90,
        side="long",
        nan_policy="propagate",
    )
    pnl = unrealized_pnl(
        [100, np.nan],
        110,
        1,
        side="long",
        nan_policy="propagate",
    )

    assert np.isnan(risk)
    assert pnl[0] == 10
    assert np.isnan(pnl[1])


@pytest.mark.parametrize(
    "call,match",
    [
        (lambda: stop_distance(100, 90, side="flat"), "side"),
        (lambda: stop_distance(0, 90, side="long"), "entry_prices"),
        (lambda: position_notional(-1, 100), "quantities"),
        (lambda: position_notional(1, 0), "prices"),
        (lambda: capital_at_risk(100, 1.1), "between 0 and 1"),
        (lambda: risk_at_stop([-1], [100], 90, side="long"), "notionals"),
        (lambda: risk_improvement(-1, 0), "current_risk"),
        (lambda: max_allowed_notional(100_000, 0.01, 0), "stop_distance"),
        (lambda: gross_exposure([-1]), "notionals"),
        (lambda: net_exposure([100, 200], ["long"]), "sides"),
        (lambda: net_exposure([100], ["flat"]), "side"),
    ],
)
def test_invalid_risk_and_portfolio_inputs_fail_fast(call, match) -> None:
    with pytest.raises(NumericInputError, match=match):
        call()


def test_array_shape_mismatches_do_not_broadcast() -> None:
    with pytest.raises(NumericInputError, match="identical shapes"):
        risk_contribution_by_tranche([1, 2], [[100, 110]], 90, side="long")
    with pytest.raises(NumericInputError, match="identical shapes"):
        realized_pnl([100, 110], [[120, 130]], 1, side="long")
    with pytest.raises(NumericInputError, match="scalars, vectors, or matrices"):
        position_notional(np.ones((1, 1, 1)), 100)


@pytest.mark.parametrize(
    "call",
    [
        lambda: position_notional(1e308, 1e308),
        lambda: gross_exposure([1e308, 1e308]),
        lambda: max_allowed_notional(1e308, 1.0, 1e-308),
        lambda: risk_at_stop([1e308, 1e308], [100, 100], 1, side="long"),
        lambda: unrealized_pnl(1e308, 1e-308, 1e308, side="long"),
    ],
)
def test_finite_inputs_cannot_silently_overflow_to_infinity(call) -> None:
    with pytest.raises(NumericInputError, match="finite float64 range|infinite"):
        call()


def test_repeated_risk_and_portfolio_calculations_are_deterministic() -> None:
    first_risk = risk_contribution_by_tranche(
        [5_000, 3_000],
        [100, 110],
        90,
        side="long",
    )
    second_risk = risk_contribution_by_tranche(
        [5_000, 3_000],
        [100, 110],
        90,
        side="long",
    )

    np.testing.assert_array_equal(first_risk, second_risk)
    assert weighted_average_entry([100, 110], [1, 2]) == weighted_average_entry(
        [100, 110], [1, 2]
    )
