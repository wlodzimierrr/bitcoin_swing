from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.data import OhlcvBar
from btc_predictor.features._scoring import decimal_bounded_linear
from btc_predictor.features import (
    CAPITULATION_FLAG_EFFECTS,
    CAPITULATION_FLAG_FEATURE_ID,
    CAPITULATION_FLAG_REASON_CODES,
    DEFAULT_CAPITULATION_DOWNSIDE_RETURN_MIN,
    DEFAULT_CAPITULATION_FUNDING_ZSCORE_MAX,
    DEFAULT_CAPITULATION_LIQUIDATION_PERCENTILE_MIN,
    DEFAULT_CAPITULATION_RANGE_PERCENTILE_MIN,
    DEFAULT_CAPITULATION_VOLATILITY_PERCENTILE_MIN,
    DEFAULT_EUPHORIA_BASIS_ZSCORE_MIN,
    DEFAULT_EUPHORIA_FUNDING_ZSCORE_MIN,
    DEFAULT_EUPHORIA_OI_INTENSITY_PERCENTILE_MIN,
    DEFAULT_EUPHORIA_RANGE_PERCENTILE_MIN,
    DEFAULT_EUPHORIA_UPSIDE_RETURN_MIN,
    DEFAULT_EUPHORIA_VOLATILITY_PERCENTILE_MIN,
    DEFAULT_ORDERLINESS_DOWNSIDE_RETURN_MIN,
    DEFAULT_ORDERLINESS_LIQUIDATION_PERCENTILE_MAX,
    DEFAULT_ORDERLINESS_RANGE_PERCENTILE_MAX,
    COMPRESSION_SCORE_FEATURE_ID,
    COMPRESSION_SCORE_PARAMETER_STATUS,
    COMPRESSION_SCORE_V1_PARAMETERS,
    COMPRESSION_SCORE_VERSION,
    VOLATILITY_REGIME_PARAMETER_STATUS,
    VOLATILITY_REGIME_V1_PARAMETERS,
    VOLATILITY_REGIME_VERSION,
    VOLATILITY_SCORE_DIAGNOSTIC_IDS,
    DEFAULT_COMPRESSION_FULL_SCORE_RATIO,
    DEFAULT_COMPRESSION_ZERO_SCORE_RATIO,
    DEFAULT_ORDERLINESS_SCORE_DISORDERLY_MAX,
    DEFAULT_ORDERLINESS_SCORE_WEIGHTS,
    DEFAULT_VOLATILITY_REGIME_COMPRESSED_MAX,
    DEFAULT_VOLATILITY_REGIME_ELEVATED_MAX,
    DEFAULT_VOLATILITY_REGIME_NORMAL_MAX,
    DEFAULT_VOLATILITY_SCORE_WEIGHTS,
    VOLATILITY_REGIMES,
    VOLATILITY_SCORE_COMPONENT_IDS,
    VOLATILITY_SCORE_FEATURE_ID,
    VOLATILITY_SCORE_REASON_CODES,
    VolatilityScoreInput,
    VolatilityScoreResult,
    calculate_volatility_score,
    calculate_volatility_score_from_results,
    compression_score_from_ratio,
    DEFAULT_ORDERLINESS_VOLATILITY_PERCENTILE_MAX,
    DEFAULT_REALIZED_VOLATILITY_ANNUALIZATION_PERIODS,
    DEFAULT_STRESS_BASIS_ABS_ZSCORE_MIN,
    DEFAULT_STRESS_BLOCK_NEW_TRADES,
    DEFAULT_STRESS_DOWNSIDE_RETURN_MIN,
    DEFAULT_STRESS_FUNDING_ABS_ZSCORE_MIN,
    DEFAULT_STRESS_LIQUIDATION_PERCENTILE_MIN,
    DEFAULT_STRESS_MAX_EXPOSURE_MULTIPLIER,
    DEFAULT_STRESS_VOLATILITY_PERCENTILE_MIN,
    DEFAULT_VOLATILITY_PERCENTILE_MIN_OBSERVATIONS,
    DEFAULT_VOLATILITY_PERCENTILE_WINDOW_DAYS,
    EUPHORIA_FLAG_EFFECTS,
    EUPHORIA_FLAG_FEATURE_ID,
    EUPHORIA_FLAG_REASON_CODES,
    ORDERLINESS_SCORE_COMPONENT_IDS,
    ORDERLINESS_SCORE_FEATURE_ID,
    ORDERLINESS_SCORE_REASON_CODES,
    REALIZED_VOLATILITY_FEATURE_IDS,
    REALIZED_VOLATILITY_REASON_CODES,
    REALIZED_VOLATILITY_WINDOWS,
    RV_7_FEATURE_ID,
    RV_20_FEATURE_ID,
    RV_60_FEATURE_ID,
    STRESS_FLAG_EFFECTS,
    STRESS_FLAG_FEATURE_ID,
    STRESS_FLAG_REASON_CODES,
    VOLATILITY_COMPRESSION_RATIO_FEATURE_ID,
    VOLATILITY_COMPRESSION_RATIO_REASON_CODES,
    VOLATILITY_PERCENTILE_FEATURE_ID,
    VOLATILITY_PERCENTILE_REASON_CODES,
    CapitulationFlagInput,
    EuphoriaFlagInput,
    OrderlinessScoreInput,
    RealizedVolatilityResult,
    StressFlagInput,
    VolatilityCompressionRatioInput,
    calculate_capitulation_flag,
    calculate_euphoria_flag,
    calculate_orderliness_score,
    calculate_stress_flag,
    realized_volatility_from_daily_bars,
    rv_7_20_60_from_daily_bars,
    volatility_compression_ratio,
    volatility_compression_ratio_from_results,
    volatility_percentile,
)


def daily_bar(
    timestamp: datetime,
    *,
    close: str,
    ingested_at: datetime | None = None,
    timeframe: str = "1d",
) -> OhlcvBar:
    close_value = Decimal(close)
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC/USD",
        timeframe=timeframe,
        open=close_value,
        high=close_value,
        low=close_value,
        close=close_value,
        volume=Decimal("100"),
        provider="coinbase",
        ingested_at=ingested_at or timestamp + timedelta(minutes=5),
    )


def daily_bars(closes: tuple[str, ...]) -> tuple[OhlcvBar, ...]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return tuple(
        daily_bar(start + timedelta(days=index), close=close)
        for index, close in enumerate(closes)
    )


def rv_result(
    timestamp: datetime,
    *,
    feature_id: str = "RV_20",
    realized_volatility: str | None,
    complete: bool = True,
) -> RealizedVolatilityResult:
    return RealizedVolatilityResult(
        feature_id=feature_id,
        observation_time=timestamp,
        window_days=20,
        annualization_periods=365,
        realized_volatility=(
            Decimal(realized_volatility)
            if realized_volatility is not None
            else None
        ),
        return_count=20 if realized_volatility is not None else 0,
        source_bar_count=21 if realized_volatility is not None else 0,
        complete=complete,
        reason_codes=() if complete else ("REALIZED_VOLATILITY_INPUT_MISSING",),
    )


def compounding_daily_bars(
    *,
    count: int,
    returns: tuple[Decimal, ...] = (
        Decimal("0.01"),
        Decimal("-0.005"),
        Decimal("0.007"),
        Decimal("0"),
    ),
) -> tuple[OhlcvBar, ...]:
    closes = [Decimal("100")]
    for index in range(count - 1):
        closes.append(closes[-1] * (Decimal("1") + returns[index % len(returns)]))
    return daily_bars(tuple(str(close) for close in closes))


def test_realized_volatility_metadata_is_stable() -> None:
    assert RV_7_FEATURE_ID == "RV_7"
    assert RV_20_FEATURE_ID == "RV_20"
    assert RV_60_FEATURE_ID == "RV_60"
    assert REALIZED_VOLATILITY_WINDOWS == (7, 20, 60)
    assert REALIZED_VOLATILITY_FEATURE_IDS == {
        7: "RV_7",
        20: "RV_20",
        60: "RV_60",
    }
    assert DEFAULT_REALIZED_VOLATILITY_ANNUALIZATION_PERIODS == 365
    assert REALIZED_VOLATILITY_REASON_CODES == (
        "REALIZED_VOLATILITY_INPUT_MISSING",
        "REALIZED_VOLATILITY_INSUFFICIENT_HISTORY",
        "REALIZED_VOLATILITY_NON_POSITIVE_CLOSE",
    )


def test_volatility_compression_ratio_metadata_is_stable() -> None:
    assert VOLATILITY_COMPRESSION_RATIO_FEATURE_ID == "VOL_COMPRESSION_RATIO"
    assert VOLATILITY_COMPRESSION_RATIO_REASON_CODES == (
        "VOL_COMPRESSION_INPUT_MISSING",
        "VOL_COMPRESSION_ZERO_DENOMINATOR",
    )


def test_volatility_percentile_metadata_is_stable() -> None:
    assert VOLATILITY_PERCENTILE_FEATURE_ID == "VOL_PERCENTILE_2Y"
    assert DEFAULT_VOLATILITY_PERCENTILE_WINDOW_DAYS == 730
    assert DEFAULT_VOLATILITY_PERCENTILE_MIN_OBSERVATIONS == 365
    assert VOLATILITY_PERCENTILE_REASON_CODES == (
        "VOL_PERCENTILE_INPUT_MISSING",
        "VOL_PERCENTILE_INSUFFICIENT_HISTORY",
    )


def test_orderliness_score_metadata_is_stable() -> None:
    assert ORDERLINESS_SCORE_FEATURE_ID == "ORDERLINESS_SCORE"
    assert ORDERLINESS_SCORE_COMPONENT_IDS == (
        "extreme_range",
        "disorderly_downside",
        "liquidation_cascade",
        "volatility_spike",
    )
    assert DEFAULT_ORDERLINESS_SCORE_WEIGHTS == {
        "extreme_range": Decimal("0.25"),
        "disorderly_downside": Decimal("0.25"),
        "liquidation_cascade": Decimal("0.25"),
        "volatility_spike": Decimal("0.25"),
    }
    assert DEFAULT_ORDERLINESS_RANGE_PERCENTILE_MAX == Decimal("90")
    assert DEFAULT_ORDERLINESS_DOWNSIDE_RETURN_MIN == Decimal("-0.08")
    assert DEFAULT_ORDERLINESS_LIQUIDATION_PERCENTILE_MAX == Decimal("90")
    assert DEFAULT_ORDERLINESS_VOLATILITY_PERCENTILE_MAX == Decimal("90")
    assert ORDERLINESS_SCORE_REASON_CODES == (
        "ORDERLINESS_INPUT_MISSING",
        "ORDERLINESS_EXTREME_RANGE",
        "ORDERLINESS_DISORDERLY_DOWNSIDE",
        "ORDERLINESS_LIQUIDATION_CASCADE",
        "ORDERLINESS_VOLATILITY_SPIKE",
    )


def test_stress_flag_metadata_is_stable() -> None:
    assert STRESS_FLAG_FEATURE_ID == "STRESS"
    assert STRESS_FLAG_EFFECTS == (
        "NO_ADD",
        "REDUCE_MAX_EXPOSURE",
        "OPTIONALLY_BLOCK_NEW_TRADES",
    )
    assert DEFAULT_STRESS_VOLATILITY_PERCENTILE_MIN == Decimal("95")
    assert DEFAULT_STRESS_LIQUIDATION_PERCENTILE_MIN == Decimal("95")
    assert DEFAULT_STRESS_DOWNSIDE_RETURN_MIN == Decimal("-0.10")
    assert DEFAULT_STRESS_FUNDING_ABS_ZSCORE_MIN == Decimal("3")
    assert DEFAULT_STRESS_BASIS_ABS_ZSCORE_MIN == Decimal("3")
    assert DEFAULT_STRESS_MAX_EXPOSURE_MULTIPLIER == Decimal("0.50")
    assert DEFAULT_STRESS_BLOCK_NEW_TRADES is False
    assert STRESS_FLAG_REASON_CODES == (
        "STRESS_INPUT_MISSING",
        "STRESS_EXTREME_VOLATILITY",
        "STRESS_LIQUIDATION_CASCADE",
        "STRESS_DISORDERLY_DOWNSIDE",
        "STRESS_ABNORMAL_FUNDING",
        "STRESS_ABNORMAL_BASIS",
        "STRESS_SYSTEMIC_MARKET_SHOCK",
    )


def test_capitulation_flag_metadata_is_stable() -> None:
    assert CAPITULATION_FLAG_FEATURE_ID == "CAPITULATION"
    assert CAPITULATION_FLAG_EFFECTS == (
        "REQUIRE_REVERSAL_CONFIRMATION",
        "NO_ADD_UNTIL_CONFIRMATION",
    )
    assert DEFAULT_CAPITULATION_RANGE_PERCENTILE_MIN == Decimal("95")
    assert DEFAULT_CAPITULATION_DOWNSIDE_RETURN_MIN == Decimal("-0.12")
    assert DEFAULT_CAPITULATION_LIQUIDATION_PERCENTILE_MIN == Decimal("95")
    assert DEFAULT_CAPITULATION_VOLATILITY_PERCENTILE_MIN == Decimal("95")
    assert DEFAULT_CAPITULATION_FUNDING_ZSCORE_MAX == Decimal("-2")
    assert CAPITULATION_FLAG_REASON_CODES == (
        "CAPITULATION_INPUT_MISSING",
        "CAPITULATION_DISORDERLY_DOWNSIDE",
        "CAPITULATION_EXTREME_RANGE",
        "CAPITULATION_LIQUIDATION_CASCADE",
        "CAPITULATION_VOLATILITY_SPIKE",
        "CAPITULATION_NEGATIVE_FUNDING_FLUSH",
        "CAPITULATION_SYSTEMIC_MARKET_SHOCK",
        "CAPITULATION_CONFIRMATION_MISSING",
    )


def test_euphoria_flag_metadata_is_stable() -> None:
    assert EUPHORIA_FLAG_FEATURE_ID == "EUPHORIA"
    assert EUPHORIA_FLAG_EFFECTS == (
        "NO_ADD",
        "REDUCE_ENTRY_QUALITY",
        "TIGHTEN_PROFIT_PROTECTION",
    )
    assert DEFAULT_EUPHORIA_RANGE_PERCENTILE_MIN == Decimal("95")
    assert DEFAULT_EUPHORIA_UPSIDE_RETURN_MIN == Decimal("0.12")
    assert DEFAULT_EUPHORIA_FUNDING_ZSCORE_MIN == Decimal("2")
    assert DEFAULT_EUPHORIA_BASIS_ZSCORE_MIN == Decimal("2")
    assert DEFAULT_EUPHORIA_OI_INTENSITY_PERCENTILE_MIN == Decimal("95")
    assert DEFAULT_EUPHORIA_VOLATILITY_PERCENTILE_MIN == Decimal("95")
    assert EUPHORIA_FLAG_REASON_CODES == (
        "EUPHORIA_INPUT_MISSING",
        "EUPHORIA_UPSIDE_EXTENSION",
        "EUPHORIA_EXTREME_RANGE",
        "EUPHORIA_FUNDING_OVERHEATED",
        "EUPHORIA_BASIS_OVERHEATED",
        "EUPHORIA_OI_INTENSITY_EXTREME",
        "EUPHORIA_VOLATILITY_SPIKE",
        "EUPHORIA_SYSTEMIC_MARKET_EUPHORIA",
        "EUPHORIA_CONFIRMATION_MISSING",
    )


def test_realized_volatility_uses_close_to_close_returns() -> None:
    rows = daily_bars(("100", "110", "99", "108.9"))

    result = realized_volatility_from_daily_bars(
        tuple(reversed(rows)),
        as_of=datetime(2026, 1, 4, 1, tzinfo=UTC),
        window_days=3,
        annualization_periods=1,
    )

    assert result.complete is True
    assert result.feature_id == "RV_3"
    assert result.observation_time == datetime(2026, 1, 4, tzinfo=UTC)
    assert result.window_days == 3
    assert result.annualization_periods == 1
    assert result.realized_volatility is not None
    assert result.realized_volatility.quantize(Decimal("0.000001")) == Decimal("0.094281")
    assert result.return_count == 3
    assert result.source_bar_count == 4
    assert result.reason_codes == ()


def test_rv_7_20_60_from_daily_bars_returns_default_windows() -> None:
    rows = compounding_daily_bars(count=62)

    results = rv_7_20_60_from_daily_bars(
        tuple(reversed(rows)),
        as_of=datetime(2026, 3, 3, 1, tzinfo=UTC),
    )

    assert tuple(result.feature_id for result in results) == ("RV_7", "RV_20", "RV_60")
    assert tuple(result.window_days for result in results) == (7, 20, 60)
    assert tuple(result.return_count for result in results) == (7, 20, 60)
    assert all(result.complete for result in results)
    assert all(result.realized_volatility is not None for result in results)


def test_volatility_compression_ratio_uses_rv7_over_rv60() -> None:
    result = volatility_compression_ratio(
        VolatilityCompressionRatioInput(
            rv_7=Decimal("0.25"),
            rv_60=Decimal("0.50"),
        )
    )

    assert result.complete is True
    assert result.feature_id == "VOL_COMPRESSION_RATIO"
    assert result.numerator_feature_id == "RV_7"
    assert result.denominator_feature_id == "RV_60"
    assert result.compression_ratio == Decimal("0.5")
    assert result.inputs.as_record() == {"rv_7": "0.25", "rv_60": "0.50"}
    assert result.reason_codes == ()


def test_volatility_compression_ratio_from_results_uses_persisted_rvs() -> None:
    results = rv_7_20_60_from_daily_bars(
        compounding_daily_bars(count=62),
        as_of=datetime(2026, 3, 3, 1, tzinfo=UTC),
    )

    result = volatility_compression_ratio_from_results(results)

    assert result.complete is True
    assert result.compression_ratio is not None
    assert result.inputs.rv_7 == results[0].realized_volatility
    assert result.inputs.rv_60 == results[2].realized_volatility


def test_volatility_compression_ratio_reports_missing_inputs_without_zero_fill() -> None:
    result = volatility_compression_ratio(
        VolatilityCompressionRatioInput(
            rv_7=None,
            rv_60=Decimal("0.50"),
        )
    )

    assert result.complete is False
    assert result.compression_ratio is None
    assert result.reason_codes == ("VOL_COMPRESSION_INPUT_MISSING",)


def test_volatility_compression_ratio_reports_zero_denominator() -> None:
    result = volatility_compression_ratio(
        VolatilityCompressionRatioInput(
            rv_7=Decimal("0.25"),
            rv_60=Decimal("0"),
        )
    )

    assert result.complete is False
    assert result.compression_ratio is None
    assert result.reason_codes == ("VOL_COMPRESSION_ZERO_DENOMINATOR",)


def test_volatility_compression_ratio_exposes_persistable_payload() -> None:
    result = volatility_compression_ratio(
        VolatilityCompressionRatioInput(
            rv_7=Decimal("0.25"),
            rv_60=Decimal("0.50"),
        )
    )

    record = result.as_record()
    assert record == {
        "feature_id": "VOL_COMPRESSION_RATIO",
        "numerator_feature_id": "RV_7",
        "denominator_feature_id": "RV_60",
        "compression_ratio": "0.5",
        "inputs": {"rv_7": "0.25", "rv_60": "0.50"},
        "complete": True,
        "reason_codes": [],
    }


def test_volatility_percentile_uses_rv20_against_prior_history() -> None:
    results = (
        rv_result(datetime(2026, 1, 1, tzinfo=UTC), realized_volatility="0.10"),
        rv_result(datetime(2026, 1, 2, tzinfo=UTC), realized_volatility="0.20"),
        rv_result(datetime(2026, 1, 3, tzinfo=UTC), realized_volatility="0.30"),
        rv_result(datetime(2026, 1, 4, tzinfo=UTC), realized_volatility="0.20"),
    )

    result = volatility_percentile(
        results,
        as_of=datetime(2026, 1, 4, 1, tzinfo=UTC),
        percentile_window_days=10,
        min_percentile_observations=3,
    )

    assert result.complete is True
    assert result.feature_id == "VOL_PERCENTILE_2Y"
    assert result.observation_time == datetime(2026, 1, 4, tzinfo=UTC)
    assert result.source_feature_id == "RV_20"
    assert result.realized_volatility == Decimal("0.20")
    assert result.volatility_percentile == Decimal("50.0")
    assert result.history_observation_count == 3
    assert result.source_result_count == 4
    assert result.reason_codes == ()


def test_volatility_percentile_filters_source_feature_and_future_results() -> None:
    results = (
        rv_result(datetime(2026, 1, 1, tzinfo=UTC), realized_volatility="0.10"),
        rv_result(datetime(2026, 1, 2, tzinfo=UTC), realized_volatility="0.20"),
        rv_result(datetime(2026, 1, 3, tzinfo=UTC), realized_volatility="0.30"),
        rv_result(
            datetime(2026, 1, 3, tzinfo=UTC),
            feature_id="RV_7",
            realized_volatility="9.00",
        ),
        rv_result(datetime(2026, 1, 4, tzinfo=UTC), realized_volatility="0.40"),
        rv_result(datetime(2026, 1, 5, tzinfo=UTC), realized_volatility="0.00"),
    )

    result = volatility_percentile(
        results,
        as_of=datetime(2026, 1, 4, 1, tzinfo=UTC),
        percentile_window_days=10,
        min_percentile_observations=3,
    )

    assert result.volatility_percentile == Decimal("100")
    assert result.history_observation_count == 3
    assert result.source_result_count == 4


def test_volatility_percentile_reports_missing_input_without_zero_fill() -> None:
    result = volatility_percentile(
        (),
        as_of=datetime(2026, 1, 4, tzinfo=UTC),
        percentile_window_days=10,
        min_percentile_observations=3,
    )

    assert result.complete is False
    assert result.observation_time == datetime(2026, 1, 4, tzinfo=UTC)
    assert result.realized_volatility is None
    assert result.volatility_percentile is None
    assert result.history_observation_count == 0
    assert result.source_result_count == 0
    assert result.reason_codes == ("VOL_PERCENTILE_INPUT_MISSING",)


def test_volatility_percentile_reports_insufficient_history() -> None:
    results = (
        rv_result(datetime(2026, 1, 1, tzinfo=UTC), realized_volatility="0.10"),
        rv_result(datetime(2026, 1, 2, tzinfo=UTC), realized_volatility="0.20"),
    )

    result = volatility_percentile(
        results,
        as_of=datetime(2026, 1, 2, 1, tzinfo=UTC),
        percentile_window_days=10,
        min_percentile_observations=2,
    )

    assert result.complete is False
    assert result.realized_volatility == Decimal("0.20")
    assert result.volatility_percentile is None
    assert result.history_observation_count == 1
    assert result.reason_codes == ("VOL_PERCENTILE_INSUFFICIENT_HISTORY",)


def test_volatility_percentile_exposes_persistable_payload() -> None:
    results = (
        rv_result(datetime(2026, 1, 1, tzinfo=UTC), realized_volatility="0.10"),
        rv_result(datetime(2026, 1, 2, tzinfo=UTC), realized_volatility="0.20"),
        rv_result(datetime(2026, 1, 3, tzinfo=UTC), realized_volatility="0.30"),
        rv_result(datetime(2026, 1, 4, tzinfo=UTC), realized_volatility="0.20"),
    )

    record = volatility_percentile(
        results,
        as_of=datetime(2026, 1, 4, 1, tzinfo=UTC),
        percentile_window_days=10,
        min_percentile_observations=3,
    ).as_record()

    assert record == {
        "feature_id": "VOL_PERCENTILE_2Y",
        "observation_time": "2026-01-04T00:00:00+00:00",
        "source_feature_id": "RV_20",
        "percentile_window_days": 10,
        "min_percentile_observations": 3,
        "realized_volatility": "0.20",
        "volatility_percentile": "50.0",
        "history_observation_count": 3,
        "source_result_count": 4,
        "complete": True,
        "reason_codes": [],
    }


def test_orderliness_score_is_100_when_market_is_orderly() -> None:
    result = calculate_orderliness_score(
        OrderlinessScoreInput(
            range_percentile=Decimal("55"),
            downside_return=Decimal("-0.02"),
            liquidation_percentile=Decimal("40"),
            volatility_percentile=Decimal("55"),
        )
    )

    assert result.complete is True
    assert result.feature_id == "ORDERLINESS_SCORE"
    assert result.score == Decimal("100")
    assert result.interpretation == "ORDERLY"
    assert result.penalties == {
        "extreme_range": Decimal("0"),
        "disorderly_downside": Decimal("0"),
        "liquidation_cascade": Decimal("0"),
        "volatility_spike": Decimal("0"),
    }
    assert result.reason_codes == ()


def test_orderliness_score_penalizes_extreme_ranges_and_disorderly_downside() -> None:
    result = calculate_orderliness_score(
        OrderlinessScoreInput(
            range_percentile=Decimal("95"),
            downside_return=Decimal("-0.10"),
            liquidation_percentile=Decimal("50"),
            volatility_percentile=Decimal("60"),
        )
    )

    assert result.complete is True
    assert result.score == Decimal("50.00")
    assert result.interpretation == "DISORDERLY"
    assert result.penalties["extreme_range"] == Decimal("25.00")
    assert result.penalties["disorderly_downside"] == Decimal("25.00")
    assert result.reason_codes == (
        "ORDERLINESS_EXTREME_RANGE",
        "ORDERLINESS_DISORDERLY_DOWNSIDE",
    )


def test_orderliness_score_penalizes_liquidation_cascades_and_volatility_spikes() -> None:
    result = calculate_orderliness_score(
        OrderlinessScoreInput(
            range_percentile=Decimal("50"),
            downside_return=Decimal("0.01"),
            liquidation_percentile=Decimal("91"),
            volatility_percentile=Decimal("92"),
        )
    )

    assert result.complete is True
    assert result.score == Decimal("50.00")
    assert result.interpretation == "DISORDERLY"
    assert result.reason_codes == (
        "ORDERLINESS_LIQUIDATION_CASCADE",
        "ORDERLINESS_VOLATILITY_SPIKE",
    )


def test_orderliness_score_uses_custom_weights_and_thresholds() -> None:
    result = calculate_orderliness_score(
        OrderlinessScoreInput(
            range_percentile=Decimal("85"),
            downside_return=Decimal("-0.061"),
            liquidation_percentile=Decimal("75"),
            volatility_percentile=Decimal("82"),
        ),
        weights={
            "extreme_range": Decimal("0.10"),
            "disorderly_downside": Decimal("0.20"),
            "liquidation_cascade": Decimal("0.30"),
            "volatility_spike": Decimal("0.40"),
        },
        range_percentile_max=Decimal("80"),
        downside_return_min=Decimal("-0.06"),
        liquidation_percentile_max=Decimal("80"),
        volatility_percentile_max=Decimal("80"),
        config_metadata={"config_version": "strategy_config_v2"},
    )

    assert result.score == Decimal("30.00")
    assert result.interpretation == "STRESSED"
    assert result.penalties == {
        "extreme_range": Decimal("10.00"),
        "disorderly_downside": Decimal("20.00"),
        "liquidation_cascade": Decimal("0"),
        "volatility_spike": Decimal("40.00"),
    }
    assert result.thresholds == {
        "range_percentile_max": Decimal("80"),
        "downside_return_min": Decimal("-0.06"),
        "liquidation_percentile_max": Decimal("80"),
        "volatility_percentile_max": Decimal("80"),
    }
    assert result.config_metadata == {"config_version": "strategy_config_v2"}


def test_orderliness_score_reports_missing_inputs_without_zero_fill() -> None:
    result = calculate_orderliness_score(
        OrderlinessScoreInput(
            range_percentile=None,
            downside_return=Decimal("-0.02"),
            liquidation_percentile=Decimal("40"),
            volatility_percentile=Decimal("55"),
        )
    )

    assert result.complete is False
    assert result.score is None
    assert result.interpretation is None
    assert result.penalties["extreme_range"] is None
    assert result.reason_codes == ("ORDERLINESS_INPUT_MISSING",)


def test_orderliness_score_exposes_persistable_payload() -> None:
    result = calculate_orderliness_score(
        OrderlinessScoreInput(
            range_percentile=Decimal("95"),
            downside_return=Decimal("-0.10"),
            liquidation_percentile=Decimal("50"),
            volatility_percentile=Decimal("60"),
        ),
        config_metadata={"parameter_set_id": "default_phase1"},
    )

    assert result.as_record() == {
        "feature_id": "ORDERLINESS_SCORE",
        "score": "50.00",
        "interpretation": "DISORDERLY",
        "inputs": {
            "range_percentile": "95",
            "downside_return": "-0.10",
            "liquidation_percentile": "50",
            "volatility_percentile": "60",
        },
        "weights": {
            "extreme_range": "0.25",
            "disorderly_downside": "0.25",
            "liquidation_cascade": "0.25",
            "volatility_spike": "0.25",
        },
        "thresholds": {
            "range_percentile_max": "90",
            "downside_return_min": "-0.08",
            "liquidation_percentile_max": "90",
            "volatility_percentile_max": "90",
        },
        "penalties": {
            "extreme_range": "25.00",
            "disorderly_downside": "25.00",
            "liquidation_cascade": "0",
            "volatility_spike": "0",
        },
        "config_metadata": {"parameter_set_id": "default_phase1"},
        "complete": True,
        "reason_codes": [
            "ORDERLINESS_EXTREME_RANGE",
            "ORDERLINESS_DISORDERLY_DOWNSIDE",
        ],
    }


def test_stress_flag_is_clear_when_inputs_are_below_thresholds() -> None:
    result = calculate_stress_flag(
        StressFlagInput(
            volatility_percentile=Decimal("70"),
            liquidation_percentile=Decimal("65"),
            downside_return=Decimal("-0.03"),
            funding_zscore=Decimal("0.8"),
            basis_zscore=Decimal("-1.0"),
            systemic_shock=False,
        )
    )

    assert result.complete is True
    assert result.flagged is False
    assert result.effects == ()
    assert result.max_exposure_multiplier == Decimal("1")
    assert result.block_new_trades is False
    assert result.reason_codes == ()


def test_stress_flag_triggers_for_volatility_liquidations_and_downside() -> None:
    result = calculate_stress_flag(
        StressFlagInput(
            volatility_percentile=Decimal("96"),
            liquidation_percentile=Decimal("98"),
            downside_return=Decimal("-0.12"),
            funding_zscore=Decimal("0"),
            basis_zscore=Decimal("0"),
            systemic_shock=False,
        ),
        block_new_trades=True,
    )

    assert result.complete is True
    assert result.flagged is True
    assert result.effects == STRESS_FLAG_EFFECTS
    assert result.max_exposure_multiplier == Decimal("0.50")
    assert result.block_new_trades is True
    assert result.reason_codes == (
        "STRESS_EXTREME_VOLATILITY",
        "STRESS_LIQUIDATION_CASCADE",
        "STRESS_DISORDERLY_DOWNSIDE",
    )


def test_stress_flag_triggers_for_abnormal_funding_basis_and_systemic_shock() -> None:
    result = calculate_stress_flag(
        StressFlagInput(
            volatility_percentile=Decimal("50"),
            liquidation_percentile=Decimal("50"),
            downside_return=Decimal("0.01"),
            funding_zscore=Decimal("-3.2"),
            basis_zscore=Decimal("3.1"),
            systemic_shock=True,
        )
    )

    assert result.flagged is True
    assert result.reason_codes == (
        "STRESS_ABNORMAL_FUNDING",
        "STRESS_ABNORMAL_BASIS",
        "STRESS_SYSTEMIC_MARKET_SHOCK",
    )


def test_stress_flag_uses_custom_thresholds_and_config_metadata() -> None:
    result = calculate_stress_flag(
        StressFlagInput(
            volatility_percentile=Decimal("91"),
            liquidation_percentile=Decimal("75"),
            downside_return=Decimal("-0.07"),
            funding_zscore=Decimal("2.1"),
            basis_zscore=Decimal("1.0"),
            systemic_shock=False,
        ),
        volatility_percentile_min=Decimal("90"),
        liquidation_percentile_min=Decimal("80"),
        downside_return_min=Decimal("-0.06"),
        funding_abs_zscore_min=Decimal("2"),
        basis_abs_zscore_min=Decimal("2"),
        max_exposure_multiplier=Decimal("0.25"),
        config_metadata={"parameter_set_id": "default_phase1"},
    )

    assert result.flagged is True
    assert result.max_exposure_multiplier == Decimal("0.25")
    assert result.thresholds == {
        "volatility_percentile_min": Decimal("90"),
        "liquidation_percentile_min": Decimal("80"),
        "downside_return_min": Decimal("-0.06"),
        "funding_abs_zscore_min": Decimal("2"),
        "basis_abs_zscore_min": Decimal("2"),
    }
    assert result.config_metadata == {"parameter_set_id": "default_phase1"}
    assert result.reason_codes == (
        "STRESS_EXTREME_VOLATILITY",
        "STRESS_DISORDERLY_DOWNSIDE",
        "STRESS_ABNORMAL_FUNDING",
    )


def test_stress_flag_reports_missing_inputs_without_treating_them_as_normal() -> None:
    result = calculate_stress_flag(
        StressFlagInput(
            volatility_percentile=None,
            liquidation_percentile=Decimal("50"),
            downside_return=Decimal("-0.03"),
            funding_zscore=Decimal("0"),
            basis_zscore=Decimal("0"),
            systemic_shock=False,
        )
    )

    assert result.complete is False
    assert result.flagged is False
    assert result.effects == ()
    assert result.max_exposure_multiplier == Decimal("1")
    assert result.reason_codes == ("STRESS_INPUT_MISSING",)


def test_stress_flag_can_report_present_trigger_with_missing_secondary_input() -> None:
    result = calculate_stress_flag(
        StressFlagInput(
            volatility_percentile=Decimal("99"),
            liquidation_percentile=None,
            downside_return=Decimal("-0.03"),
            funding_zscore=Decimal("0"),
            basis_zscore=Decimal("0"),
            systemic_shock=False,
        )
    )

    assert result.complete is False
    assert result.flagged is True
    assert result.effects == STRESS_FLAG_EFFECTS
    assert result.reason_codes == (
        "STRESS_INPUT_MISSING",
        "STRESS_EXTREME_VOLATILITY",
    )


def test_stress_flag_exposes_persistable_payload() -> None:
    result = calculate_stress_flag(
        StressFlagInput(
            volatility_percentile=Decimal("96"),
            liquidation_percentile=Decimal("98"),
            downside_return=Decimal("-0.12"),
            funding_zscore=Decimal("-3.5"),
            basis_zscore=Decimal("0"),
            systemic_shock=False,
        ),
        block_new_trades=True,
        config_metadata={"config_version": "strategy_config_v2"},
    )

    assert result.as_record() == {
        "feature_id": "STRESS",
        "flagged": True,
        "effects": [
            "NO_ADD",
            "REDUCE_MAX_EXPOSURE",
            "OPTIONALLY_BLOCK_NEW_TRADES",
        ],
        "max_exposure_multiplier": "0.50",
        "block_new_trades": True,
        "inputs": {
            "volatility_percentile": "96",
            "liquidation_percentile": "98",
            "downside_return": "-0.12",
            "funding_zscore": "-3.5",
            "basis_zscore": "0",
            "systemic_shock": False,
        },
        "thresholds": {
            "volatility_percentile_min": "95",
            "liquidation_percentile_min": "95",
            "downside_return_min": "-0.10",
            "funding_abs_zscore_min": "3",
            "basis_abs_zscore_min": "3",
        },
        "config_metadata": {"config_version": "strategy_config_v2"},
        "complete": True,
        "reason_codes": [
            "STRESS_EXTREME_VOLATILITY",
            "STRESS_LIQUIDATION_CASCADE",
            "STRESS_DISORDERLY_DOWNSIDE",
            "STRESS_ABNORMAL_FUNDING",
        ],
    }


def test_capitulation_flag_is_clear_when_inputs_are_below_thresholds() -> None:
    result = calculate_capitulation_flag(
        CapitulationFlagInput(
            range_percentile=Decimal("70"),
            downside_return=Decimal("-0.04"),
            liquidation_percentile=Decimal("65"),
            volatility_percentile=Decimal("70"),
            funding_zscore=Decimal("-0.5"),
            systemic_shock=False,
        )
    )

    assert result.complete is True
    assert result.flagged is False
    assert result.effects == ()
    assert result.reason_codes == ()


def test_capitulation_flag_requires_downside_plus_confirmation() -> None:
    result = calculate_capitulation_flag(
        CapitulationFlagInput(
            range_percentile=Decimal("96"),
            downside_return=Decimal("-0.12"),
            liquidation_percentile=Decimal("98"),
            volatility_percentile=Decimal("96"),
            funding_zscore=Decimal("-2.5"),
            systemic_shock=False,
        )
    )

    assert result.complete is True
    assert result.flagged is True
    assert result.effects == CAPITULATION_FLAG_EFFECTS
    assert result.reason_codes == (
        "CAPITULATION_DISORDERLY_DOWNSIDE",
        "CAPITULATION_EXTREME_RANGE",
        "CAPITULATION_LIQUIDATION_CASCADE",
        "CAPITULATION_VOLATILITY_SPIKE",
        "CAPITULATION_NEGATIVE_FUNDING_FLUSH",
    )


def test_capitulation_flag_reports_missing_confirmation() -> None:
    result = calculate_capitulation_flag(
        CapitulationFlagInput(
            range_percentile=Decimal("80"),
            downside_return=Decimal("-0.13"),
            liquidation_percentile=Decimal("70"),
            volatility_percentile=Decimal("75"),
            funding_zscore=Decimal("-1.0"),
            systemic_shock=False,
        )
    )

    assert result.complete is True
    assert result.flagged is False
    assert result.effects == ()
    assert result.reason_codes == (
        "CAPITULATION_DISORDERLY_DOWNSIDE",
        "CAPITULATION_CONFIRMATION_MISSING",
    )


def test_capitulation_flag_allows_systemic_shock_to_flag_directly() -> None:
    result = calculate_capitulation_flag(
        CapitulationFlagInput(
            range_percentile=Decimal("50"),
            downside_return=Decimal("-0.02"),
            liquidation_percentile=Decimal("50"),
            volatility_percentile=Decimal("50"),
            funding_zscore=Decimal("0"),
            systemic_shock=True,
        )
    )

    assert result.flagged is True
    assert result.reason_codes == ("CAPITULATION_SYSTEMIC_MARKET_SHOCK",)


def test_capitulation_flag_reports_missing_inputs_without_zero_fill() -> None:
    result = calculate_capitulation_flag(
        CapitulationFlagInput(
            range_percentile=None,
            downside_return=Decimal("-0.13"),
            liquidation_percentile=Decimal("96"),
            volatility_percentile=Decimal("50"),
            funding_zscore=Decimal("-1"),
            systemic_shock=False,
        )
    )

    assert result.complete is False
    assert result.flagged is True
    assert result.reason_codes == (
        "CAPITULATION_INPUT_MISSING",
        "CAPITULATION_DISORDERLY_DOWNSIDE",
        "CAPITULATION_LIQUIDATION_CASCADE",
    )


def test_capitulation_flag_uses_custom_thresholds_and_config_metadata() -> None:
    result = calculate_capitulation_flag(
        CapitulationFlagInput(
            range_percentile=Decimal("91"),
            downside_return=Decimal("-0.09"),
            liquidation_percentile=Decimal("88"),
            volatility_percentile=Decimal("80"),
            funding_zscore=Decimal("-1.6"),
            systemic_shock=False,
        ),
        range_percentile_min=Decimal("90"),
        downside_return_min=Decimal("-0.08"),
        liquidation_percentile_min=Decimal("90"),
        volatility_percentile_min=Decimal("90"),
        funding_zscore_max=Decimal("-1.5"),
        config_metadata={"parameter_set_id": "default_phase1"},
    )

    assert result.flagged is True
    assert result.thresholds == {
        "range_percentile_min": Decimal("90"),
        "downside_return_min": Decimal("-0.08"),
        "liquidation_percentile_min": Decimal("90"),
        "volatility_percentile_min": Decimal("90"),
        "funding_zscore_max": Decimal("-1.5"),
    }
    assert result.config_metadata == {"parameter_set_id": "default_phase1"}
    assert result.reason_codes == (
        "CAPITULATION_DISORDERLY_DOWNSIDE",
        "CAPITULATION_EXTREME_RANGE",
        "CAPITULATION_NEGATIVE_FUNDING_FLUSH",
    )


def test_capitulation_flag_exposes_persistable_payload() -> None:
    result = calculate_capitulation_flag(
        CapitulationFlagInput(
            range_percentile=Decimal("96"),
            downside_return=Decimal("-0.14"),
            liquidation_percentile=Decimal("98"),
            volatility_percentile=Decimal("97"),
            funding_zscore=Decimal("-2.3"),
            systemic_shock=False,
        ),
        config_metadata={"config_version": "strategy_config_v2"},
    )

    assert result.as_record() == {
        "feature_id": "CAPITULATION",
        "flagged": True,
        "effects": [
            "REQUIRE_REVERSAL_CONFIRMATION",
            "NO_ADD_UNTIL_CONFIRMATION",
        ],
        "inputs": {
            "range_percentile": "96",
            "downside_return": "-0.14",
            "liquidation_percentile": "98",
            "volatility_percentile": "97",
            "funding_zscore": "-2.3",
            "systemic_shock": False,
        },
        "thresholds": {
            "range_percentile_min": "95",
            "downside_return_min": "-0.12",
            "liquidation_percentile_min": "95",
            "volatility_percentile_min": "95",
            "funding_zscore_max": "-2",
        },
        "config_metadata": {"config_version": "strategy_config_v2"},
        "complete": True,
        "reason_codes": [
            "CAPITULATION_DISORDERLY_DOWNSIDE",
            "CAPITULATION_EXTREME_RANGE",
            "CAPITULATION_LIQUIDATION_CASCADE",
            "CAPITULATION_VOLATILITY_SPIKE",
            "CAPITULATION_NEGATIVE_FUNDING_FLUSH",
        ],
    }


def test_euphoria_flag_is_clear_when_inputs_are_below_thresholds() -> None:
    result = calculate_euphoria_flag(
        EuphoriaFlagInput(
            range_percentile=Decimal("70"),
            upside_return=Decimal("0.04"),
            funding_zscore=Decimal("0.5"),
            basis_zscore=Decimal("0.7"),
            oi_intensity_percentile=Decimal("70"),
            volatility_percentile=Decimal("65"),
            systemic_euphoria=False,
        )
    )

    assert result.complete is True
    assert result.flagged is False
    assert result.effects == ()
    assert result.reason_codes == ()


def test_euphoria_flag_requires_upside_plus_confirmation() -> None:
    result = calculate_euphoria_flag(
        EuphoriaFlagInput(
            range_percentile=Decimal("96"),
            upside_return=Decimal("0.12"),
            funding_zscore=Decimal("2.2"),
            basis_zscore=Decimal("2.1"),
            oi_intensity_percentile=Decimal("98"),
            volatility_percentile=Decimal("96"),
            systemic_euphoria=False,
        )
    )

    assert result.complete is True
    assert result.flagged is True
    assert result.effects == EUPHORIA_FLAG_EFFECTS
    assert result.reason_codes == (
        "EUPHORIA_UPSIDE_EXTENSION",
        "EUPHORIA_EXTREME_RANGE",
        "EUPHORIA_FUNDING_OVERHEATED",
        "EUPHORIA_BASIS_OVERHEATED",
        "EUPHORIA_OI_INTENSITY_EXTREME",
        "EUPHORIA_VOLATILITY_SPIKE",
    )


def test_euphoria_flag_reports_missing_confirmation() -> None:
    result = calculate_euphoria_flag(
        EuphoriaFlagInput(
            range_percentile=Decimal("80"),
            upside_return=Decimal("0.13"),
            funding_zscore=Decimal("1"),
            basis_zscore=Decimal("1"),
            oi_intensity_percentile=Decimal("70"),
            volatility_percentile=Decimal("75"),
            systemic_euphoria=False,
        )
    )

    assert result.complete is True
    assert result.flagged is False
    assert result.effects == ()
    assert result.reason_codes == (
        "EUPHORIA_UPSIDE_EXTENSION",
        "EUPHORIA_CONFIRMATION_MISSING",
    )


def test_euphoria_flag_allows_systemic_euphoria_to_flag_directly() -> None:
    result = calculate_euphoria_flag(
        EuphoriaFlagInput(
            range_percentile=Decimal("50"),
            upside_return=Decimal("0.02"),
            funding_zscore=Decimal("0"),
            basis_zscore=Decimal("0"),
            oi_intensity_percentile=Decimal("50"),
            volatility_percentile=Decimal("50"),
            systemic_euphoria=True,
        )
    )

    assert result.flagged is True
    assert result.reason_codes == ("EUPHORIA_SYSTEMIC_MARKET_EUPHORIA",)


def test_euphoria_flag_reports_missing_inputs_without_zero_fill() -> None:
    result = calculate_euphoria_flag(
        EuphoriaFlagInput(
            range_percentile=None,
            upside_return=Decimal("0.13"),
            funding_zscore=Decimal("2.1"),
            basis_zscore=Decimal("1"),
            oi_intensity_percentile=Decimal("80"),
            volatility_percentile=Decimal("70"),
            systemic_euphoria=False,
        )
    )

    assert result.complete is False
    assert result.flagged is True
    assert result.reason_codes == (
        "EUPHORIA_INPUT_MISSING",
        "EUPHORIA_UPSIDE_EXTENSION",
        "EUPHORIA_FUNDING_OVERHEATED",
    )


def test_euphoria_flag_uses_custom_thresholds_and_config_metadata() -> None:
    result = calculate_euphoria_flag(
        EuphoriaFlagInput(
            range_percentile=Decimal("91"),
            upside_return=Decimal("0.09"),
            funding_zscore=Decimal("1.6"),
            basis_zscore=Decimal("1.4"),
            oi_intensity_percentile=Decimal("88"),
            volatility_percentile=Decimal("80"),
            systemic_euphoria=False,
        ),
        range_percentile_min=Decimal("90"),
        upside_return_min=Decimal("0.08"),
        funding_zscore_min=Decimal("1.5"),
        basis_zscore_min=Decimal("2"),
        oi_intensity_percentile_min=Decimal("90"),
        volatility_percentile_min=Decimal("90"),
        config_metadata={"parameter_set_id": "default_phase1"},
    )

    assert result.flagged is True
    assert result.thresholds == {
        "range_percentile_min": Decimal("90"),
        "upside_return_min": Decimal("0.08"),
        "funding_zscore_min": Decimal("1.5"),
        "basis_zscore_min": Decimal("2"),
        "oi_intensity_percentile_min": Decimal("90"),
        "volatility_percentile_min": Decimal("90"),
    }
    assert result.config_metadata == {"parameter_set_id": "default_phase1"}
    assert result.reason_codes == (
        "EUPHORIA_UPSIDE_EXTENSION",
        "EUPHORIA_EXTREME_RANGE",
        "EUPHORIA_FUNDING_OVERHEATED",
    )


def test_euphoria_flag_exposes_persistable_payload() -> None:
    result = calculate_euphoria_flag(
        EuphoriaFlagInput(
            range_percentile=Decimal("96"),
            upside_return=Decimal("0.14"),
            funding_zscore=Decimal("2.3"),
            basis_zscore=Decimal("2.2"),
            oi_intensity_percentile=Decimal("97"),
            volatility_percentile=Decimal("96"),
            systemic_euphoria=False,
        ),
        config_metadata={"config_version": "strategy_config_v2"},
    )

    assert result.as_record() == {
        "feature_id": "EUPHORIA",
        "flagged": True,
        "effects": [
            "NO_ADD",
            "REDUCE_ENTRY_QUALITY",
            "TIGHTEN_PROFIT_PROTECTION",
        ],
        "inputs": {
            "range_percentile": "96",
            "upside_return": "0.14",
            "funding_zscore": "2.3",
            "basis_zscore": "2.2",
            "oi_intensity_percentile": "97",
            "volatility_percentile": "96",
            "systemic_euphoria": False,
        },
        "thresholds": {
            "range_percentile_min": "95",
            "upside_return_min": "0.12",
            "funding_zscore_min": "2",
            "basis_zscore_min": "2",
            "oi_intensity_percentile_min": "95",
            "volatility_percentile_min": "95",
        },
        "config_metadata": {"config_version": "strategy_config_v2"},
        "complete": True,
        "reason_codes": [
            "EUPHORIA_UPSIDE_EXTENSION",
            "EUPHORIA_EXTREME_RANGE",
            "EUPHORIA_FUNDING_OVERHEATED",
            "EUPHORIA_BASIS_OVERHEATED",
            "EUPHORIA_OI_INTENSITY_EXTREME",
            "EUPHORIA_VOLATILITY_SPIKE",
        ],
    }


def test_realized_volatility_filters_unavailable_future_bars() -> None:
    rows = daily_bars(("100", "110", "99", "108.9"))
    future_revision = daily_bar(
        datetime(2026, 1, 4, tzinfo=UTC),
        close="999",
        ingested_at=datetime(2026, 1, 5, tzinfo=UTC),
    )

    baseline = realized_volatility_from_daily_bars(
        rows,
        as_of=datetime(2026, 1, 4, 1, tzinfo=UTC),
        window_days=3,
        annualization_periods=1,
    ).as_record()
    with_future = realized_volatility_from_daily_bars(
        (*rows, future_revision),
        as_of=datetime(2026, 1, 4, 1, tzinfo=UTC),
        window_days=3,
        annualization_periods=1,
    ).as_record()

    assert with_future == baseline


def test_realized_volatility_reports_missing_input_without_zero_fill() -> None:
    result = realized_volatility_from_daily_bars(
        (),
        as_of=datetime(2026, 1, 4, tzinfo=UTC),
        window_days=3,
    )

    assert result.complete is False
    assert result.realized_volatility is None
    assert result.return_count == 0
    assert result.source_bar_count == 0
    assert result.reason_codes == ("REALIZED_VOLATILITY_INPUT_MISSING",)


def test_realized_volatility_reports_insufficient_history() -> None:
    result = realized_volatility_from_daily_bars(
        daily_bars(("100", "110", "99")),
        as_of=datetime(2026, 1, 3, 1, tzinfo=UTC),
        window_days=3,
    )

    assert result.complete is False
    assert result.realized_volatility is None
    assert result.return_count == 0
    assert result.source_bar_count == 3
    assert result.reason_codes == ("REALIZED_VOLATILITY_INSUFFICIENT_HISTORY",)


def test_realized_volatility_reports_non_positive_close() -> None:
    result = realized_volatility_from_daily_bars(
        daily_bars(("100", "110", "0", "108.9")),
        as_of=datetime(2026, 1, 4, 1, tzinfo=UTC),
        window_days=3,
    )

    assert result.complete is False
    assert result.realized_volatility is None
    assert result.return_count == 0
    assert result.reason_codes == ("REALIZED_VOLATILITY_NON_POSITIVE_CLOSE",)


def test_realized_volatility_exposes_persistable_payload() -> None:
    result = realized_volatility_from_daily_bars(
        daily_bars(("100", "110", "99", "108.9")),
        as_of=datetime(2026, 1, 4, 1, tzinfo=UTC),
        window_days=3,
        annualization_periods=1,
    )

    record = result.as_record()
    assert record["feature_id"] == "RV_3"
    assert record["observation_time"] == "2026-01-04T00:00:00+00:00"
    assert record["window_days"] == 3
    assert record["annualization_periods"] == 1
    assert record["realized_volatility"] == str(result.realized_volatility)
    assert record["return_count"] == 3
    assert record["source_bar_count"] == 4
    assert record["complete"] is True
    assert record["reason_codes"] == []


def test_realized_volatility_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="as_of must be timezone-aware UTC"):
        realized_volatility_from_daily_bars((), as_of=datetime(2026, 1, 4), window_days=3)

    with pytest.raises(ValueError, match="window_days"):
        realized_volatility_from_daily_bars(
            (),
            as_of=datetime(2026, 1, 4, tzinfo=UTC),
            window_days=0,
        )

    with pytest.raises(ValueError, match="annualization_periods"):
        realized_volatility_from_daily_bars(
            (),
            as_of=datetime(2026, 1, 4, tzinfo=UTC),
            window_days=3,
            annualization_periods=0,
        )

    with pytest.raises(ValueError, match="canonical 1d bars"):
        realized_volatility_from_daily_bars(
            (daily_bar(datetime(2026, 1, 1, tzinfo=UTC), close="100", timeframe="1h"),),
            as_of=datetime(2026, 1, 4, tzinfo=UTC),
            window_days=3,
        )


def test_volatility_compression_ratio_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="rv_7"):
        volatility_compression_ratio(
            VolatilityCompressionRatioInput(
                rv_7=Decimal("-0.01"),
                rv_60=Decimal("0.50"),
            )
        )

    with pytest.raises(ValueError, match="rv_60"):
        volatility_compression_ratio(
            VolatilityCompressionRatioInput(
                rv_7=Decimal("0.25"),
                rv_60=Decimal("-0.50"),
            )
        )


def test_volatility_percentile_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="as_of must be timezone-aware UTC"):
        volatility_percentile((), as_of=datetime(2026, 1, 4))

    with pytest.raises(ValueError, match="source_feature_id"):
        volatility_percentile(
            (),
            as_of=datetime(2026, 1, 4, tzinfo=UTC),
            source_feature_id=" ",
        )

    with pytest.raises(ValueError, match="percentile_window_days"):
        volatility_percentile(
            (),
            as_of=datetime(2026, 1, 4, tzinfo=UTC),
            percentile_window_days=0,
        )

    with pytest.raises(ValueError, match="min_percentile_observations"):
        volatility_percentile(
            (),
            as_of=datetime(2026, 1, 4, tzinfo=UTC),
            min_percentile_observations=0,
        )

    with pytest.raises(ValueError, match="min_percentile_observations"):
        volatility_percentile(
            (),
            as_of=datetime(2026, 1, 4, tzinfo=UTC),
            percentile_window_days=2,
            min_percentile_observations=3,
        )

    with pytest.raises(ValueError, match="realized_volatility"):
        volatility_percentile(
            (
                rv_result(datetime(2026, 1, 1, tzinfo=UTC), realized_volatility="-0.10"),
                rv_result(datetime(2026, 1, 2, tzinfo=UTC), realized_volatility="0.20"),
            ),
            as_of=datetime(2026, 1, 2, 1, tzinfo=UTC),
            percentile_window_days=10,
            min_percentile_observations=1,
        )


def test_orderliness_score_rejects_invalid_inputs() -> None:
    valid_input = OrderlinessScoreInput(
        range_percentile=Decimal("50"),
        downside_return=Decimal("-0.02"),
        liquidation_percentile=Decimal("50"),
        volatility_percentile=Decimal("50"),
    )

    with pytest.raises(ValueError, match="range_percentile"):
        calculate_orderliness_score(
            OrderlinessScoreInput(
                range_percentile=Decimal("101"),
                downside_return=Decimal("-0.02"),
                liquidation_percentile=Decimal("50"),
                volatility_percentile=Decimal("50"),
            )
        )

    with pytest.raises(ValueError, match="liquidation_percentile"):
        calculate_orderliness_score(
            OrderlinessScoreInput(
                range_percentile=Decimal("50"),
                downside_return=Decimal("-0.02"),
                liquidation_percentile=Decimal("-1"),
                volatility_percentile=Decimal("50"),
            )
        )

    with pytest.raises(ValueError, match="volatility_percentile"):
        calculate_orderliness_score(
            OrderlinessScoreInput(
                range_percentile=Decimal("50"),
                downside_return=Decimal("-0.02"),
                liquidation_percentile=Decimal("50"),
                volatility_percentile=Decimal("101"),
            )
        )

    with pytest.raises(ValueError, match="weights"):
        calculate_orderliness_score(valid_input, weights={"extreme_range": Decimal("1")})

    with pytest.raises(ValueError, match="weights"):
        calculate_orderliness_score(
            valid_input,
            weights={
                "extreme_range": Decimal("0.20"),
                "disorderly_downside": Decimal("0.20"),
                "liquidation_cascade": Decimal("0.20"),
                "volatility_spike": Decimal("0.20"),
            },
        )

    with pytest.raises(ValueError, match="downside_return_min"):
        calculate_orderliness_score(valid_input, downside_return_min=Decimal("0"))


def test_stress_flag_rejects_invalid_inputs() -> None:
    valid_input = StressFlagInput(
        volatility_percentile=Decimal("50"),
        liquidation_percentile=Decimal("50"),
        downside_return=Decimal("-0.03"),
        funding_zscore=Decimal("0"),
        basis_zscore=Decimal("0"),
        systemic_shock=False,
    )

    with pytest.raises(ValueError, match="volatility_percentile"):
        calculate_stress_flag(
            StressFlagInput(
                volatility_percentile=Decimal("101"),
                liquidation_percentile=Decimal("50"),
                downside_return=Decimal("-0.03"),
                funding_zscore=Decimal("0"),
                basis_zscore=Decimal("0"),
                systemic_shock=False,
            )
        )


def test_capitulation_flag_rejects_invalid_inputs() -> None:
    valid_input = CapitulationFlagInput(
        range_percentile=Decimal("50"),
        downside_return=Decimal("-0.03"),
        liquidation_percentile=Decimal("50"),
        volatility_percentile=Decimal("50"),
        funding_zscore=Decimal("0"),
        systemic_shock=False,
    )

    with pytest.raises(ValueError, match="range_percentile"):
        calculate_capitulation_flag(
            CapitulationFlagInput(
                range_percentile=Decimal("101"),
                downside_return=Decimal("-0.03"),
                liquidation_percentile=Decimal("50"),
                volatility_percentile=Decimal("50"),
                funding_zscore=Decimal("0"),
                systemic_shock=False,
            )
        )


def test_euphoria_flag_rejects_invalid_inputs() -> None:
    valid_input = EuphoriaFlagInput(
        range_percentile=Decimal("50"),
        upside_return=Decimal("0.03"),
        funding_zscore=Decimal("0"),
        basis_zscore=Decimal("0"),
        oi_intensity_percentile=Decimal("50"),
        volatility_percentile=Decimal("50"),
        systemic_euphoria=False,
    )

    with pytest.raises(ValueError, match="range_percentile"):
        calculate_euphoria_flag(
            EuphoriaFlagInput(
                range_percentile=Decimal("101"),
                upside_return=Decimal("0.03"),
                funding_zscore=Decimal("0"),
                basis_zscore=Decimal("0"),
                oi_intensity_percentile=Decimal("50"),
                volatility_percentile=Decimal("50"),
                systemic_euphoria=False,
            )
        )

    with pytest.raises(ValueError, match="oi_intensity_percentile"):
        calculate_euphoria_flag(
            EuphoriaFlagInput(
                range_percentile=Decimal("50"),
                upside_return=Decimal("0.03"),
                funding_zscore=Decimal("0"),
                basis_zscore=Decimal("0"),
                oi_intensity_percentile=Decimal("-1"),
                volatility_percentile=Decimal("50"),
                systemic_euphoria=False,
            )
        )

    with pytest.raises(ValueError, match="volatility_percentile"):
        calculate_euphoria_flag(
            EuphoriaFlagInput(
                range_percentile=Decimal("50"),
                upside_return=Decimal("0.03"),
                funding_zscore=Decimal("0"),
                basis_zscore=Decimal("0"),
                oi_intensity_percentile=Decimal("50"),
                volatility_percentile=Decimal("101"),
                systemic_euphoria=False,
            )
        )

    with pytest.raises(ValueError, match="upside_return_min"):
        calculate_euphoria_flag(valid_input, upside_return_min=Decimal("0"))

    with pytest.raises(ValueError, match="funding_zscore_min"):
        calculate_euphoria_flag(valid_input, funding_zscore_min=Decimal("-1"))

    with pytest.raises(ValueError, match="basis_zscore_min"):
        calculate_euphoria_flag(valid_input, basis_zscore_min=Decimal("-1"))

    with pytest.raises(ValueError, match="systemic_euphoria"):
        calculate_euphoria_flag(
            EuphoriaFlagInput(
                range_percentile=Decimal("50"),
                upside_return=Decimal("0.03"),
                funding_zscore=Decimal("0"),
                basis_zscore=Decimal("0"),
                oi_intensity_percentile=Decimal("50"),
                volatility_percentile=Decimal("50"),
                systemic_euphoria="yes",  # type: ignore[arg-type]
            )
        )

    with pytest.raises(ValueError, match="liquidation_percentile"):
        calculate_capitulation_flag(
            CapitulationFlagInput(
                range_percentile=Decimal("50"),
                downside_return=Decimal("-0.03"),
                liquidation_percentile=Decimal("-1"),
                volatility_percentile=Decimal("50"),
                funding_zscore=Decimal("0"),
                systemic_shock=False,
            )
        )

    with pytest.raises(ValueError, match="volatility_percentile"):
        calculate_capitulation_flag(
            CapitulationFlagInput(
                range_percentile=Decimal("50"),
                downside_return=Decimal("-0.03"),
                liquidation_percentile=Decimal("50"),
                volatility_percentile=Decimal("101"),
                funding_zscore=Decimal("0"),
                systemic_shock=False,
            )
        )

    with pytest.raises(ValueError, match="downside_return_min"):
        calculate_capitulation_flag(valid_input, downside_return_min=Decimal("0"))

    with pytest.raises(ValueError, match="funding_zscore_max"):
        calculate_capitulation_flag(valid_input, funding_zscore_max=Decimal("0"))

    with pytest.raises(ValueError, match="systemic_shock"):
        calculate_capitulation_flag(
            CapitulationFlagInput(
                range_percentile=Decimal("50"),
                downside_return=Decimal("-0.03"),
                liquidation_percentile=Decimal("50"),
                volatility_percentile=Decimal("50"),
                funding_zscore=Decimal("0"),
                systemic_shock="yes",  # type: ignore[arg-type]
            )
        )

    with pytest.raises(ValueError, match="liquidation_percentile"):
        calculate_stress_flag(
            StressFlagInput(
                volatility_percentile=Decimal("50"),
                liquidation_percentile=Decimal("-1"),
                downside_return=Decimal("-0.03"),
                funding_zscore=Decimal("0"),
                basis_zscore=Decimal("0"),
                systemic_shock=False,
            )
        )

    with pytest.raises(ValueError, match="downside_return_min"):
        calculate_stress_flag(valid_input, downside_return_min=Decimal("0"))

    with pytest.raises(ValueError, match="funding_abs_zscore_min"):
        calculate_stress_flag(valid_input, funding_abs_zscore_min=Decimal("-1"))

    with pytest.raises(ValueError, match="basis_abs_zscore_min"):
        calculate_stress_flag(valid_input, basis_abs_zscore_min=Decimal("-1"))

    with pytest.raises(ValueError, match="max_exposure_multiplier"):
        calculate_stress_flag(valid_input, max_exposure_multiplier=Decimal("1.1"))

    with pytest.raises(ValueError, match="block_new_trades"):
        calculate_stress_flag(valid_input, block_new_trades="yes")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="systemic_shock"):
        calculate_stress_flag(
            StressFlagInput(
                volatility_percentile=Decimal("50"),
                liquidation_percentile=Decimal("50"),
                downside_return=Decimal("-0.03"),
                funding_zscore=Decimal("0"),
                basis_zscore=Decimal("0"),
                systemic_shock="yes",  # type: ignore[arg-type]
            )
        )


def test_volatility_score_metadata_is_stable() -> None:
    assert VOLATILITY_SCORE_FEATURE_ID == "VOLATILITY_SCORE"
    assert COMPRESSION_SCORE_FEATURE_ID == "COMPRESSION_SCORE"
    assert VOLATILITY_SCORE_COMPONENT_IDS == ("compression", "orderliness")
    assert DEFAULT_VOLATILITY_SCORE_WEIGHTS == {
        "compression": Decimal("0.5"),
        "orderliness": Decimal("0.5"),
    }
    assert DEFAULT_COMPRESSION_FULL_SCORE_RATIO == Decimal("0.70")
    assert DEFAULT_COMPRESSION_ZERO_SCORE_RATIO == Decimal("1.30")
    assert DEFAULT_VOLATILITY_REGIME_COMPRESSED_MAX == Decimal("25")
    assert DEFAULT_VOLATILITY_REGIME_NORMAL_MAX == Decimal("75")
    assert DEFAULT_VOLATILITY_REGIME_ELEVATED_MAX == Decimal("95")
    assert DEFAULT_ORDERLINESS_SCORE_DISORDERLY_MAX == Decimal("60")
    assert VOLATILITY_REGIMES == ("COMPRESSED", "NORMAL", "ELEVATED", "STRESSED")
    assert VOLATILITY_SCORE_REASON_CODES == (
        "VOLATILITY_SCORE_INPUT_MISSING",
        "VOLATILITY_SCORE_COMPLETE",
        "VOLATILITY_COMPRESSED",
        "VOLATILITY_EXPANDING",
        "VOLATILITY_DISORDERLY",
        "VOLATILITY_REGIME_UNKNOWN",
    )


@pytest.mark.parametrize(
    ("ratio", "expected"),
    [
        ("0.50", Decimal("100")),
        ("0.70", Decimal("100")),
        ("0.85", Decimal("75")),
        ("1.00", Decimal("50")),
        ("1.15", Decimal("25")),
        ("1.30", Decimal("0")),
        ("2.00", Decimal("0")),
    ],
)
def test_compression_score_is_a_clamped_linear_ramp(
    ratio: str,
    expected: Decimal,
) -> None:
    assert compression_score_from_ratio(Decimal(ratio)) == expected


def test_compression_score_is_neutral_at_the_rulebook_boundary() -> None:
    # The rulebook prefers RV7 / RV60 < 1, so an exactly neutral ratio must
    # score at the midpoint rather than favouring either side.
    assert compression_score_from_ratio(Decimal("1")) == Decimal("50")


def test_compression_score_returns_none_without_a_ratio() -> None:
    assert compression_score_from_ratio(None) is None


def test_compression_score_rejects_inverted_thresholds() -> None:
    with pytest.raises(ValueError, match="less than zero_score_ratio"):
        compression_score_from_ratio(
            Decimal("1"),
            full_score_ratio=Decimal("1.30"),
            zero_score_ratio=Decimal("0.70"),
        )


def test_volatility_score_is_the_even_compression_orderliness_composite() -> None:
    result = calculate_volatility_score(
        VolatilityScoreInput(
            compression_ratio=Decimal("1.00"),
            orderliness_score=Decimal("80"),
            volatility_percentile=Decimal("50"),
        ),
    )

    # 0.5 * 50 + 0.5 * 80
    assert result.score == Decimal("65.0")
    assert result.compression_score == Decimal("50")
    assert result.contributions["compression"] == Decimal("25.0")
    assert result.contributions["orderliness"] == Decimal("40.0")
    assert result.interpretation == "ACCEPTABLE"
    assert result.volatility_regime == "NORMAL"
    assert result.complete
    assert "VOLATILITY_SCORE_COMPLETE" in result.reason_codes


def test_volatility_score_is_100_when_compressed_and_orderly() -> None:
    result = calculate_volatility_score(
        VolatilityScoreInput(
            compression_ratio=Decimal("0.60"),
            orderliness_score=Decimal("100"),
            volatility_percentile=Decimal("10"),
        ),
    )

    assert result.score == Decimal("100.0")
    assert result.interpretation == "FAVORABLE"
    assert result.volatility_regime == "COMPRESSED"
    assert "VOLATILITY_COMPRESSED" in result.reason_codes


def test_volatility_score_flags_expanding_and_disorderly_volatility() -> None:
    result = calculate_volatility_score(
        VolatilityScoreInput(
            compression_ratio=Decimal("1.60"),
            orderliness_score=Decimal("25"),
            volatility_percentile=Decimal("97"),
        ),
    )

    assert result.score == Decimal("12.5")
    assert result.compression_score == Decimal("0")
    assert result.interpretation == "UNFAVORABLE"
    assert result.volatility_regime == "STRESSED"
    assert "VOLATILITY_EXPANDING" in result.reason_codes
    assert "VOLATILITY_DISORDERLY" in result.reason_codes


@pytest.mark.parametrize(
    ("percentile", "regime"),
    [
        ("0", "COMPRESSED"),
        ("25", "COMPRESSED"),
        ("25.01", "NORMAL"),
        ("75", "NORMAL"),
        ("75.01", "ELEVATED"),
        ("95", "ELEVATED"),
        ("95.01", "STRESSED"),
        ("100", "STRESSED"),
    ],
)
def test_volatility_regime_bands_are_inclusive_at_their_upper_bound(
    percentile: str,
    regime: str,
) -> None:
    result = calculate_volatility_score(
        VolatilityScoreInput(
            compression_ratio=Decimal("1"),
            orderliness_score=Decimal("50"),
            volatility_percentile=Decimal(percentile),
        ),
    )

    assert result.volatility_regime == regime
    assert result.volatility_regime in VOLATILITY_REGIMES


def test_volatility_score_regime_is_unknown_without_a_percentile() -> None:
    result = calculate_volatility_score(
        VolatilityScoreInput(
            compression_ratio=Decimal("1"),
            orderliness_score=Decimal("50"),
        ),
    )

    # The percentile only classifies the regime; it must not block the score.
    assert result.score == Decimal("50.0")
    assert result.complete
    assert result.volatility_regime is None
    assert "VOLATILITY_REGIME_UNKNOWN" in result.reason_codes


@pytest.mark.parametrize(
    ("compression_ratio", "orderliness_score"),
    [(None, Decimal("80")), (Decimal("1"), None), (None, None)],
)
def test_volatility_score_is_incomplete_when_a_component_is_missing(
    compression_ratio: Decimal | None,
    orderliness_score: Decimal | None,
) -> None:
    result = calculate_volatility_score(
        VolatilityScoreInput(
            compression_ratio=compression_ratio,
            orderliness_score=orderliness_score,
        ),
    )

    # Missing components are never silently scored as zero.
    assert result.score is None
    assert not result.complete
    assert result.interpretation is None
    assert "VOLATILITY_SCORE_INPUT_MISSING" in result.reason_codes


def test_volatility_score_uses_custom_weights_and_thresholds() -> None:
    result = calculate_volatility_score(
        VolatilityScoreInput(
            compression_ratio=Decimal("1.00"),
            orderliness_score=Decimal("80"),
            volatility_percentile=Decimal("50"),
        ),
        weights={"compression": Decimal("0.25"), "orderliness": Decimal("0.75")},
        full_score_ratio=Decimal("0.90"),
        zero_score_ratio=Decimal("1.10"),
    )

    # Ratio 1.00 sits midway between 0.90 and 1.10, so compression is still 50.
    assert result.compression_score == Decimal("50")
    assert result.score == Decimal("72.50")
    assert result.weights == {
        "compression": Decimal("0.25"),
        "orderliness": Decimal("0.75"),
    }
    assert result.thresholds["compression_full_score_ratio"] == Decimal("0.90")


def test_volatility_score_rejects_unknown_or_missing_weights() -> None:
    inputs = VolatilityScoreInput(
        compression_ratio=Decimal("1"),
        orderliness_score=Decimal("50"),
    )
    with pytest.raises(ValueError, match="missing components"):
        calculate_volatility_score(inputs, weights={"compression": Decimal("1")})
    with pytest.raises(ValueError, match="unknown volatility score weights"):
        calculate_volatility_score(
            inputs,
            weights={
                "compression": Decimal("0.5"),
                "orderliness": Decimal("0.5"),
                "regime": Decimal("0.5"),
            },
        )


def test_volatility_score_rejects_non_monotonic_regime_bounds() -> None:
    with pytest.raises(ValueError, match="non-decreasing"):
        calculate_volatility_score(
            VolatilityScoreInput(
                compression_ratio=Decimal("1"),
                orderliness_score=Decimal("50"),
                volatility_percentile=Decimal("50"),
            ),
            compressed_percentile_max=Decimal("80"),
            normal_percentile_max=Decimal("40"),
        )


def test_volatility_score_record_is_persistable_and_deterministic() -> None:
    inputs = VolatilityScoreInput(
        compression_ratio=Decimal("0.85"),
        orderliness_score=Decimal("90"),
        volatility_percentile=Decimal("30"),
    )
    first = calculate_volatility_score(inputs, config_metadata={"config": "v1.2"})
    second = calculate_volatility_score(inputs, config_metadata={"config": "v1.2"})

    assert isinstance(first, VolatilityScoreResult)
    assert first.as_record() == second.as_record()
    record = first.as_record()
    assert record["feature_id"] == "VOLATILITY_SCORE"
    assert record["score"] == "82.5"
    assert record["compression_score"] == "75"
    assert record["volatility_regime"] == "NORMAL"
    assert record["weights"] == {"compression": "0.5", "orderliness": "0.5"}
    assert record["config_metadata"] == {"config": "v1.2"}
    assert record["contributions"] == {
        "compression": "37.5",
        "orderliness": "45.0",
    }
    assert record["thresholds"]["compression_full_score_ratio"] == "0.70"
    assert "VOLATILITY_SCORE_COMPLETE" in record["reason_codes"]


def test_volatility_score_from_upstream_feature_results() -> None:
    compression = volatility_compression_ratio(
        VolatilityCompressionRatioInput(rv_7=Decimal("0.40"), rv_60=Decimal("0.40")),
    )
    orderliness = calculate_orderliness_score(
        OrderlinessScoreInput(
            range_percentile=Decimal("50"),
            downside_return=Decimal("-0.01"),
            liquidation_percentile=Decimal("50"),
            volatility_percentile=Decimal("50"),
        ),
    )

    result = calculate_volatility_score_from_results(compression, orderliness)

    assert compression.compression_ratio == Decimal("1")
    assert orderliness.score == Decimal("100.00")
    # 0.5 * 50 + 0.5 * 100
    assert result.score == Decimal("75.000")
    assert result.inputs.compression_ratio == Decimal("1")
    assert result.inputs.orderliness_score == Decimal("100.00")
    assert result.volatility_regime is None


def test_compression_score_parameters_are_versioned_and_marked_provisional() -> None:
    assert COMPRESSION_SCORE_VERSION == "COMPRESSION_SCORE_V1"
    assert COMPRESSION_SCORE_V1_PARAMETERS == {
        "full_compression_ratio": Decimal("0.70"),
        "neutral_ratio": Decimal("1.00"),
        "zero_compression_ratio": Decimal("1.30"),
    }
    # The ramp endpoints are a deterministic Phase-1 choice, not an empirically
    # validated calibration; BTC-185 may vary them.
    assert COMPRESSION_SCORE_PARAMETER_STATUS == "PROVISIONAL_RESEARCH_CALIBRATABLE"


def test_declared_neutral_ratio_cannot_drift_from_the_ramp_endpoints() -> None:
    parameters = COMPRESSION_SCORE_V1_PARAMETERS
    neutral = parameters["neutral_ratio"]

    # The declared neutral ratio must actually be the ramp's midpoint, so the
    # three parameters can never be edited out of agreement with each other.
    assert neutral == (
        parameters["full_compression_ratio"] + parameters["zero_compression_ratio"]
    ) / 2
    assert compression_score_from_ratio(neutral) == Decimal("50")


@pytest.mark.parametrize(
    ("ratio", "expected"),
    [
        ("0.00", Decimal("100")),
        ("0.699999", Decimal("100")),
        ("0.70", Decimal("100")),
        ("1.00", Decimal("50")),
        ("1.30", Decimal("0")),
        ("1.300001", Decimal("0")),
        ("99", Decimal("0")),
    ],
)
def test_compression_score_exact_boundaries_and_clamping(
    ratio: str,
    expected: Decimal,
) -> None:
    assert compression_score_from_ratio(Decimal(ratio)) == expected


def test_compression_score_is_bounded_0_to_100_across_the_domain() -> None:
    for hundredths in range(0, 301, 1):
        score = compression_score_from_ratio(Decimal(hundredths) / Decimal("100"))
        assert Decimal("0") <= score <= Decimal("100")


def test_decimal_bounded_linear_matches_quant_bounded_linear() -> None:
    """The Decimal ramp must agree with the BTC-044 float64 primitive."""

    from btc_predictor.quant.transforms import bounded_linear

    for hundredths in range(0, 201):
        ratio = Decimal(hundredths) / Decimal("100")
        exact = decimal_bounded_linear(
            ratio,
            input_minimum=Decimal("0.70"),
            input_maximum=Decimal("1.30"),
            output_at_minimum=Decimal("100"),
            output_at_maximum=Decimal("0"),
        )
        # bounded_linear maps low->low, so invert to compare the same ramp.
        quant_penalty = bounded_linear(
            float(ratio),
            input_minimum=0.70,
            input_maximum=1.30,
            output_minimum=0.0,
            output_maximum=100.0,
        )
        assert abs(float(exact) - (100.0 - quant_penalty)) < 1e-9


def test_volatility_regime_thresholds_are_versioned() -> None:
    assert VOLATILITY_REGIME_VERSION == "VOLATILITY_REGIME_V1"
    assert VOLATILITY_REGIME_V1_PARAMETERS == {
        "compressed_percentile_max": Decimal("25"),
        "normal_percentile_max": Decimal("75"),
        "elevated_percentile_max": Decimal("95"),
    }
    assert VOLATILITY_REGIME_PARAMETER_STATUS == "PROVISIONAL_RESEARCH_CALIBRATABLE"
    # The stressed boundary reuses the already-authoritative stress threshold.
    assert (
        VOLATILITY_REGIME_V1_PARAMETERS["elevated_percentile_max"]
        == DEFAULT_STRESS_VOLATILITY_PERCENTILE_MIN
    )


def test_case_a_low_compression_with_mid_percentile_is_not_stressed() -> None:
    """Weak compression must not manufacture a STRESSED regime."""

    result = calculate_volatility_score(
        VolatilityScoreInput(
            compression_ratio=Decimal("1.25"),
            orderliness_score=Decimal("90"),
            volatility_percentile=Decimal("45"),
        ),
    )

    assert result.compression_score == Decimal("8.333333333333333333333333333")
    assert result.compression_score < Decimal("20")
    assert result.volatility_regime == "NORMAL"
    assert result.complete is True


def test_case_b_full_compression_with_stress_percentile_is_stressed() -> None:
    """Full compression and a stressed regime are a valid combination."""

    result = calculate_volatility_score(
        VolatilityScoreInput(
            compression_ratio=Decimal("0.65"),
            orderliness_score=Decimal("90"),
            volatility_percentile=Decimal("97"),
        ),
    )

    assert result.compression_score == Decimal("100")
    assert result.volatility_regime == "STRESSED"
    assert result.complete is True


def test_regime_does_not_change_the_score_for_a_fixed_component_pair() -> None:
    """Regime is context; it must contribute no weight to the composite."""

    scores = {
        percentile: calculate_volatility_score(
            VolatilityScoreInput(
                compression_ratio=Decimal("1.00"),
                orderliness_score=Decimal("80"),
                volatility_percentile=Decimal(percentile),
            ),
        )
        for percentile in ("5", "45", "85", "99")
    }
    regimes = {result.volatility_regime for result in scores.values()}

    assert regimes == {"COMPRESSED", "NORMAL", "ELEVATED", "STRESSED"}
    assert {result.score for result in scores.values()} == {Decimal("65.0")}


def test_volatility_score_has_exactly_two_weighted_components() -> None:
    result = calculate_volatility_score(
        VolatilityScoreInput(
            compression_ratio=Decimal("1.00"),
            orderliness_score=Decimal("80"),
            volatility_percentile=Decimal("45"),
        ),
    )
    record = result.as_record()

    assert VOLATILITY_SCORE_COMPONENT_IDS == ("compression", "orderliness")
    assert set(record["weights"]) == {"compression", "orderliness"}
    assert set(record["contributions"]) == {"compression", "orderliness"}
    # Context must be reachable but must never look like a weighted component.
    assert set(record["diagnostics"]) == set(VOLATILITY_SCORE_DIAGNOSTIC_IDS)
    assert "volatility_percentile" not in record["contributions"]
    assert "volatility_regime" not in record["contributions"]
    assert "compression_ratio" not in record["contributions"]
    assert record["compression_score_version"] == "COMPRESSION_SCORE_V1"
    assert record["volatility_regime_version"] == "VOLATILITY_REGIME_V1"


def test_missing_regime_context_is_not_a_missing_weighted_component() -> None:
    complete_without_regime = calculate_volatility_score(
        VolatilityScoreInput(
            compression_ratio=Decimal("1.00"),
            orderliness_score=Decimal("80"),
        ),
    )
    incomplete = calculate_volatility_score(
        VolatilityScoreInput(
            compression_ratio=None,
            orderliness_score=Decimal("80"),
            volatility_percentile=Decimal("45"),
        ),
    )

    assert complete_without_regime.complete is True
    assert complete_without_regime.score == Decimal("65.0")
    assert "VOLATILITY_REGIME_UNKNOWN" in complete_without_regime.reason_codes
    assert "VOLATILITY_SCORE_INPUT_MISSING" not in (
        complete_without_regime.reason_codes
    )

    assert incomplete.complete is False
    assert incomplete.score is None
    assert "VOLATILITY_SCORE_INPUT_MISSING" in incomplete.reason_codes
    # The two conditions must never be conflated by a downstream consumer.
    assert "VOLATILITY_REGIME_UNKNOWN" not in incomplete.reason_codes
