"""BTC-141: volatility buffer for structural stops."""

from decimal import Decimal

import pytest

from btc_predictor.risk import (
    ATR_BOUND,
    BUFFER_ATR_MULTIPLIER_GRID,
    BUFFER_BINDING_TERMS,
    BUFFER_PARAMETER_STATUS,
    DEFAULT_BUFFER_ATR_MULTIPLIER,
    DEFAULT_BUFFER_ATR_WINDOW_DAYS,
    LEVEL_NOISE_BOUND,
    VOLATILITY_BUFFER_FEATURE_ID,
    VOLATILITY_BUFFER_POLICY_VERSION,
    VOLATILITY_BUFFER_REASON_CODES,
    VolatilityBufferResult,
    atr_from_daily_bars,
    calculate_volatility_buffer,
    level_noise_from_zone,
    volatility_buffer_grid,
)


def test_metadata_is_stable() -> None:
    assert VOLATILITY_BUFFER_FEATURE_ID == "VOLATILITY_BUFFER"
    assert VOLATILITY_BUFFER_POLICY_VERSION == "VOLATILITY_BUFFER_V1"
    assert DEFAULT_BUFFER_ATR_MULTIPLIER == Decimal("0.30")
    assert DEFAULT_BUFFER_ATR_WINDOW_DAYS == 20
    assert BUFFER_ATR_MULTIPLIER_GRID == (
        Decimal("0.25"),
        Decimal("0.50"),
        Decimal("0.75"),
    )
    assert BUFFER_PARAMETER_STATUS == "PROVISIONAL_RESEARCH_CALIBRATABLE"
    assert BUFFER_BINDING_TERMS == (ATR_BOUND, LEVEL_NOISE_BOUND)


# --- max(0.3 * ATR, LevelNoiseEstimate) ---------------------------------


def test_default_buffer_is_three_tenths_of_atr() -> None:
    result = calculate_volatility_buffer(atr="1000")

    assert result.buffer == Decimal("300.00")
    assert result.atr_component == Decimal("300.00")
    assert result.complete is True
    assert result.binding_term == ATR_BOUND


def test_level_noise_wins_when_it_exceeds_the_atr_term() -> None:
    result = calculate_volatility_buffer(atr="1000", level_noise_estimate="500")

    assert result.buffer == Decimal("500")
    assert result.binding_term == LEVEL_NOISE_BOUND
    assert "VOLATILITY_BUFFER_LEVEL_NOISE_BOUND" in result.reason_codes


def test_atr_term_wins_when_it_exceeds_level_noise() -> None:
    result = calculate_volatility_buffer(atr="1000", level_noise_estimate="200")

    assert result.buffer == Decimal("300.00")
    assert result.binding_term == ATR_BOUND
    assert "VOLATILITY_BUFFER_ATR_BOUND" in result.reason_codes


def test_a_tie_resolves_to_the_atr_term_deterministically() -> None:
    result = calculate_volatility_buffer(atr="1000", level_noise_estimate="300")

    assert result.buffer == Decimal("300.00")
    assert result.binding_term == ATR_BOUND


def test_buffer_is_the_maximum_of_both_terms_across_a_sweep() -> None:
    for noise in range(0, 1000, 50):
        result = calculate_volatility_buffer(atr="1000", level_noise_estimate=noise)
        assert result.buffer == max(Decimal("300.00"), Decimal(noise))


# --- declared research grid ---------------------------------------------


def test_declared_atr_multiplier_grid_is_evaluated() -> None:
    grid = volatility_buffer_grid(atr="1000")

    assert set(grid) == {"0.25", "0.50", "0.75"}
    assert grid["0.25"].buffer == Decimal("250.00")
    assert grid["0.50"].buffer == Decimal("500.00")
    assert grid["0.75"].buffer == Decimal("750.00")
    for result in grid.values():
        assert result.complete is True


def test_grid_respects_level_noise_and_reports_the_binding_term() -> None:
    grid = volatility_buffer_grid(atr="1000", level_noise_estimate="400")

    # 0.25 * 1000 = 250 < 400, so noise binds at the tightest multiplier only.
    assert grid["0.25"].buffer == Decimal("400")
    assert grid["0.25"].binding_term == LEVEL_NOISE_BOUND
    assert grid["0.50"].buffer == Decimal("500.00")
    assert grid["0.50"].binding_term == ATR_BOUND
    assert grid["0.75"].binding_term == ATR_BOUND


def test_grid_does_not_select_a_winner() -> None:
    """BTC-141 reports the sweep; BTC-185 calibrates it."""

    grid = volatility_buffer_grid(atr="1000")
    buffers = [result.buffer for result in grid.values()]

    assert len(set(buffers)) == len(buffers)
    assert BUFFER_PARAMETER_STATUS == "PROVISIONAL_RESEARCH_CALIBRATABLE"


# --- missing data --------------------------------------------------------


def test_missing_atr_makes_the_buffer_incomplete_not_zero() -> None:
    result = calculate_volatility_buffer(atr=None, level_noise_estimate="500")

    # A stop must never be placed on a silently absent volatility term.
    assert result.complete is False
    assert result.buffer is None
    assert result.binding_term is None
    assert result.reason_codes == ("VOLATILITY_BUFFER_INPUT_MISSING",)


def test_missing_level_noise_degenerates_to_the_atr_term() -> None:
    result = calculate_volatility_buffer(atr="1000")

    assert result.complete is True
    assert result.buffer == Decimal("300.00")
    assert result.level_noise_estimate is None
    assert "VOLATILITY_BUFFER_LEVEL_NOISE_UNAVAILABLE" in result.reason_codes


def test_zero_level_noise_is_permitted_and_never_binds() -> None:
    result = calculate_volatility_buffer(atr="1000", level_noise_estimate="0")

    assert result.buffer == Decimal("300.00")
    assert result.binding_term == ATR_BOUND


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"atr": "0"}, "atr must be positive"),
        ({"atr": "-5"}, "atr must be positive"),
        ({"atr": "1000", "level_noise_estimate": "-1"}, "must be non-negative"),
        ({"atr": "1000", "atr_multiplier": "-0.1"}, "must be non-negative"),
    ],
)
def test_invalid_inputs_fail_fast(kwargs, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        calculate_volatility_buffer(**kwargs)


def test_a_zero_multiplier_is_allowed_and_lets_level_noise_govern() -> None:
    result = calculate_volatility_buffer(
        atr="1000",
        level_noise_estimate="120",
        atr_multiplier="0",
    )

    assert result.buffer == Decimal("120")
    assert result.binding_term == LEVEL_NOISE_BOUND


# --- LevelNoiseEstimate interpretation -----------------------------------


def test_level_noise_from_zone_is_half_the_zone_width() -> None:
    assert level_noise_from_zone(lower_bound="95", upper_bound="97") == Decimal("1")
    assert level_noise_from_zone(lower_bound="100", upper_bound="100") == Decimal("0")


def test_level_noise_from_zone_composes_with_the_buffer() -> None:
    noise = level_noise_from_zone(lower_bound="9000", upper_bound="9600")
    result = calculate_volatility_buffer(atr="500", level_noise_estimate=noise)

    # Half of a 600-wide zone is 300, which exceeds 0.3 * 500 = 150.
    assert noise == Decimal("300")
    assert result.buffer == Decimal("300")
    assert result.binding_term == LEVEL_NOISE_BOUND


# --- ATR bridge to BTC-043 ----------------------------------------------


def test_atr_from_daily_bars_uses_the_shared_rolling_primitive() -> None:
    highs = [Decimal("101")] * 25
    lows = [Decimal("99")] * 25
    closes = [Decimal("100")] * 25

    atr = atr_from_daily_bars(highs, lows, closes, window=20)

    # Constant 2-wide bars give a true range of 2 throughout.
    assert atr == Decimal("2.0")


def test_atr_from_daily_bars_returns_none_while_warming_up() -> None:
    highs = [Decimal("101")] * 5
    lows = [Decimal("99")] * 5
    closes = [Decimal("100")] * 5

    # Warm-up must be None, never a partial-window number.
    assert atr_from_daily_bars(highs, lows, closes, window=20) is None


def test_atr_from_daily_bars_validates_its_inputs() -> None:
    with pytest.raises(ValueError, match="same length"):
        atr_from_daily_bars([1, 2], [1], [1], window=2)
    with pytest.raises(ValueError, match="window must be >= 1"):
        atr_from_daily_bars([1], [1], [1], window=0)


# --- determinism and persistence ----------------------------------------


def test_recomputation_is_deterministic() -> None:
    first = calculate_volatility_buffer(atr="1234.5", level_noise_estimate="410")
    second = calculate_volatility_buffer(atr="1234.5", level_noise_estimate="410")

    assert first.as_record() == second.as_record()


def test_record_is_persistable_with_both_terms() -> None:
    result = calculate_volatility_buffer(
        atr="1000",
        level_noise_estimate="500",
        config_metadata={"config_version": "strategy_config_v2"},
    )
    record = result.as_record()

    assert isinstance(result, VolatilityBufferResult)
    assert record["feature_id"] == "VOLATILITY_BUFFER"
    assert record["policy_version"] == "VOLATILITY_BUFFER_V1"
    assert record["buffer"] == "500"
    assert record["atr"] == "1000"
    assert record["atr_multiplier"] == "0.30"
    # Both terms stay reconstructable, not just the winner.
    assert record["atr_component"] == "300.00"
    assert record["level_noise_estimate"] == "500"
    assert record["binding_term"] == "LEVEL_NOISE"
    assert record["config_metadata"] == {"config_version": "strategy_config_v2"}
    assert record["complete"] is True


def test_reason_codes_are_drawn_from_the_declared_set() -> None:
    results = [
        calculate_volatility_buffer(atr="1000"),
        calculate_volatility_buffer(atr="1000", level_noise_estimate="500"),
        calculate_volatility_buffer(atr=None),
    ]

    for result in results:
        for code in result.reason_codes:
            assert code in VOLATILITY_BUFFER_REASON_CODES
