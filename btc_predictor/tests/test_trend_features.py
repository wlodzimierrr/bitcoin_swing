from datetime import UTC, datetime, timedelta
from decimal import Decimal
from math import erf, sqrt

import pytest

from btc_predictor.data import OhlcvBar
from btc_predictor.features import (
    DEFAULT_TREND_SCORE_WEIGHTS,
    FIFTY_TWO_WEEK_HIGH_DISTANCE_FEATURE_ID,
    FIFTY_TWO_WEEK_HIGH_DISTANCE_LOOKBACK_WEEKS,
    TWENTY_WEEK_MA_DISTANCE_FEATURE_ID,
    TWENTY_WEEK_MA_DISTANCE_LOOKBACK_WEEKS,
    TREND_SCORE_COMPONENT_IDS,
    TREND_SCORE_FEATURE_ID,
    WEEKLY_STRUCTURE_FEATURE_ID,
    WEEKLY_STRUCTURE_LABELS,
    WEEKLY_STRUCTURE_SCORES,
    TrendScoreInput,
    calculate_trend_score,
    classify_weekly_structure,
    classify_weekly_structure_from_weekly_bars,
    fifty_two_week_high_distance,
    fifty_two_week_high_distance_from_weekly_bars,
    moving_average_distance,
    rolling_high_distance,
    twenty_week_ma_distance,
    twenty_week_ma_distance_from_weekly_bars,
)


def weekly_bar(
    timestamp: datetime,
    close: str,
    *,
    high: str | None = None,
    low: str | None = None,
) -> OhlcvBar:
    price = Decimal(close)
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1w",
        open=price,
        high=Decimal(high or close),
        low=Decimal(low or close),
        close=price,
        volume=Decimal("1"),
        provider="coinbase",
        ingested_at=datetime(2026, 8, 26, tzinfo=UTC),
    )


def test_twenty_week_ma_distance_metadata_is_stable() -> None:
    assert TWENTY_WEEK_MA_DISTANCE_FEATURE_ID == "MA_DISTANCE_20W"
    assert TWENTY_WEEK_MA_DISTANCE_LOOKBACK_WEEKS == 20


def test_weekly_structure_metadata_is_stable() -> None:
    assert WEEKLY_STRUCTURE_FEATURE_ID == "WEEKLY_STRUCTURE"
    assert WEEKLY_STRUCTURE_LABELS == ("HH_HL", "HL_ONLY", "MIXED", "LH_ONLY", "LH_LL")
    assert WEEKLY_STRUCTURE_SCORES == {
        "HH_HL": Decimal("1.0"),
        "HL_ONLY": Decimal("0.5"),
        "MIXED": Decimal("0.0"),
        "LH_ONLY": Decimal("-0.5"),
        "LH_LL": Decimal("-1.0"),
    }


def test_fifty_two_week_high_distance_metadata_is_stable() -> None:
    assert FIFTY_TWO_WEEK_HIGH_DISTANCE_FEATURE_ID == "HIGH_DISTANCE_52W"
    assert FIFTY_TWO_WEEK_HIGH_DISTANCE_LOOKBACK_WEEKS == 52


def test_trend_score_metadata_is_stable() -> None:
    assert TREND_SCORE_FEATURE_ID == "TREND_SCORE"
    assert TREND_SCORE_COMPONENT_IDS == ("Z_M4", "Z_M12", "Z_20W", "S_STRUCTURE", "Z_52H")
    assert DEFAULT_TREND_SCORE_WEIGHTS == {
        "Z_M4": Decimal("0.30"),
        "Z_M12": Decimal("0.30"),
        "Z_20W": Decimal("0.20"),
        "S_STRUCTURE": Decimal("0.15"),
        "Z_52H": Decimal("0.05"),
    }


def test_calculate_trend_score_applies_rulebook_formula_and_cdf() -> None:
    inputs = TrendScoreInput(
        z_m4=Decimal("1"),
        z_m12=Decimal("0.5"),
        z_20w=Decimal("-0.25"),
        structure_score=Decimal("1"),
        z_52h=Decimal("-0.5"),
    )

    result = calculate_trend_score(inputs)
    expected_score = Decimal(str(100 * (0.5 * (1.0 + erf(float(Decimal("0.525")) / sqrt(2.0))))))

    assert result.raw_score == Decimal("0.525")
    assert result.score == expected_score
    assert Decimal("0") <= result.score <= Decimal("100")
    assert result.interpretation == "BULLISH"
    assert result.contributions == {
        "Z_M4": Decimal("0.30"),
        "Z_M12": Decimal("0.150"),
        "Z_20W": Decimal("-0.050"),
        "S_STRUCTURE": Decimal("0.15"),
        "Z_52H": Decimal("-0.025"),
    }


def test_calculate_trend_score_exposes_persistable_explanation_payload() -> None:
    inputs = TrendScoreInput(
        z_m4=Decimal("0"),
        z_m12=Decimal("0"),
        z_20w=Decimal("0"),
        structure_score=Decimal("0"),
        z_52h=Decimal("0"),
    )

    result = calculate_trend_score(inputs)

    assert result.reason_code == "TREND_SCORE_MIXED"
    assert result.as_record() == {
        "feature_id": "TREND_SCORE",
        "raw_score": "0.00",
        "score": "50.0",
        "interpretation": "MIXED",
        "reason_code": "TREND_SCORE_MIXED",
        "inputs": {
            "Z_M4": "0",
            "Z_M12": "0",
            "Z_20W": "0",
            "S_STRUCTURE": "0",
            "Z_52H": "0",
        },
        "weights": {
            "Z_M4": "0.30",
            "Z_M12": "0.30",
            "Z_20W": "0.20",
            "S_STRUCTURE": "0.15",
            "Z_52H": "0.05",
        },
        "contributions": {
            "Z_M4": "0.00",
            "Z_M12": "0.00",
            "Z_20W": "0.00",
            "S_STRUCTURE": "0.00",
            "Z_52H": "0.00",
        },
    }


def test_calculate_trend_score_is_deterministic_for_historical_recompute() -> None:
    inputs = TrendScoreInput(
        z_m4=Decimal("-1.25"),
        z_m12=Decimal("-0.75"),
        z_20w=Decimal("-0.5"),
        structure_score=Decimal("-1.0"),
        z_52h=Decimal("-0.25"),
    )

    first = calculate_trend_score(inputs).as_record()
    second = calculate_trend_score(inputs).as_record()

    assert first == second
    recomputed_inputs = TrendScoreInput(
        z_m4=Decimal(first["inputs"]["Z_M4"]),
        z_m12=Decimal(first["inputs"]["Z_M12"]),
        z_20w=Decimal(first["inputs"]["Z_20W"]),
        structure_score=Decimal(first["inputs"]["S_STRUCTURE"]),
        z_52h=Decimal(first["inputs"]["Z_52H"]),
    )
    recomputed_weights = {
        component_id: Decimal(value)
        for component_id, value in first["weights"].items()
    }
    assert calculate_trend_score(recomputed_inputs, weights=recomputed_weights).as_record() == first


def test_calculate_trend_score_interprets_score_bands() -> None:
    assert calculate_trend_score(
        TrendScoreInput(
            z_m4=Decimal("3"),
            z_m12=Decimal("3"),
            z_20w=Decimal("3"),
            structure_score=Decimal("1"),
            z_52h=Decimal("3"),
        )
    ).interpretation == "STRONG_BULLISH"
    assert calculate_trend_score(
        TrendScoreInput(
            z_m4=Decimal("-3"),
            z_m12=Decimal("-3"),
            z_20w=Decimal("-3"),
            structure_score=Decimal("-1"),
            z_52h=Decimal("-3"),
        )
    ).interpretation == "STRONG_BEARISH"


def test_calculate_trend_score_rejects_invalid_weights() -> None:
    inputs = TrendScoreInput(
        z_m4=Decimal("0"),
        z_m12=Decimal("0"),
        z_20w=Decimal("0"),
        structure_score=Decimal("0"),
        z_52h=Decimal("0"),
    )

    with pytest.raises(ValueError, match="exactly match"):
        calculate_trend_score(inputs, weights={"Z_M4": 1})

    with pytest.raises(ValueError, match="non-negative"):
        calculate_trend_score(
            inputs,
            weights={
                "Z_M4": Decimal("-1"),
                "Z_M12": Decimal("0"),
                "Z_20W": Decimal("0"),
                "S_STRUCTURE": Decimal("0"),
                "Z_52H": Decimal("0"),
            },
        )


def test_twenty_week_ma_distance_calculates_price_minus_ma_over_ma() -> None:
    prices = [Decimal("100")] * 19 + [Decimal("120")]

    distance = twenty_week_ma_distance(prices)

    assert distance[:19] == (None,) * 19
    assert distance[19] == Decimal("0.1881188118811881188118811881")


def test_moving_average_distance_supports_custom_windows() -> None:
    assert moving_average_distance([10, 20, 30], window=2) == (
        None,
        Decimal("0.3333333333333333333333333333"),
        Decimal("0.2"),
    )


def test_twenty_week_ma_distance_returns_none_when_ma_is_zero() -> None:
    prices = [Decimal("0")] * 20

    assert twenty_week_ma_distance(prices)[19] is None


def test_twenty_week_ma_distance_uses_only_past_and_current_prices() -> None:
    prices = [Decimal("100")] * 19 + [Decimal("120"), Decimal("1000000")]

    assert twenty_week_ma_distance(prices)[:-1] == twenty_week_ma_distance(prices[:-1])


def test_twenty_week_ma_distance_from_weekly_bars_uses_timestamp_order() -> None:
    start = datetime(2026, 1, 5, tzinfo=UTC)
    bars = tuple(
        weekly_bar(start + timedelta(weeks=offset), "100")
        for offset in range(19)
    ) + (weekly_bar(start + timedelta(weeks=19), "120"),)

    assert twenty_week_ma_distance_from_weekly_bars(tuple(reversed(bars)))[19] == Decimal(
        "0.1881188118811881188118811881"
    )


def test_twenty_week_ma_distance_from_weekly_bars_rejects_non_weekly_bars() -> None:
    daily = OhlcvBar(**{**weekly_bar(datetime(2026, 1, 5, tzinfo=UTC), "100").as_record(), "timeframe": "1d"})

    with pytest.raises(ValueError, match="requires 1w bars"):
        twenty_week_ma_distance_from_weekly_bars([daily])


def test_twenty_week_ma_distance_rejects_invalid_windows() -> None:
    with pytest.raises(ValueError, match="window"):
        twenty_week_ma_distance([1, 2, 3], window=0)


def test_fifty_two_week_high_distance_calculates_price_minus_high_over_high() -> None:
    prices = [Decimal("100")] * 51 + [Decimal("90")]
    highs = [Decimal("100")] * 51 + [Decimal("110")]

    distance = fifty_two_week_high_distance(prices, highs)

    assert distance[:51] == (None,) * 51
    assert distance[51] == Decimal("-0.1818181818181818181818181818")


def test_rolling_high_distance_supports_custom_windows() -> None:
    assert rolling_high_distance([10, 20, 15], [11, 22, 18], window=2) == (
        None,
        Decimal("-0.09090909090909090909090909091"),
        Decimal("-0.3181818181818181818181818182"),
    )


def test_fifty_two_week_high_distance_defaults_to_price_series_highs() -> None:
    prices = [Decimal("100")] * 51 + [Decimal("120")]

    assert fifty_two_week_high_distance(prices)[51] == Decimal("0")


def test_fifty_two_week_high_distance_returns_none_when_trailing_high_is_zero() -> None:
    prices = [Decimal("0")] * 52

    assert fifty_two_week_high_distance(prices)[51] is None


def test_fifty_two_week_high_distance_uses_only_past_and_current_values() -> None:
    prices = [Decimal("100")] * 51 + [Decimal("90"), Decimal("1000000")]
    highs = [Decimal("100")] * 51 + [Decimal("110"), Decimal("1000000")]

    assert fifty_two_week_high_distance(prices, highs)[:-1] == fifty_two_week_high_distance(
        prices[:-1],
        highs[:-1],
    )


def test_fifty_two_week_high_distance_from_weekly_bars_uses_timestamp_order() -> None:
    start = datetime(2026, 1, 5, tzinfo=UTC)
    bars = tuple(
        weekly_bar(start + timedelta(weeks=offset), "100", high="100")
        for offset in range(51)
    ) + (weekly_bar(start + timedelta(weeks=51), "90", high="110"),)

    assert fifty_two_week_high_distance_from_weekly_bars(tuple(reversed(bars)))[51] == Decimal(
        "-0.1818181818181818181818181818"
    )


def test_fifty_two_week_high_distance_from_weekly_bars_rejects_non_weekly_bars() -> None:
    daily = OhlcvBar(**{**weekly_bar(datetime(2026, 1, 5, tzinfo=UTC), "100").as_record(), "timeframe": "1d"})

    with pytest.raises(ValueError, match="requires 1w bars"):
        fifty_two_week_high_distance_from_weekly_bars([daily])


def test_fifty_two_week_high_distance_rejects_mismatched_inputs() -> None:
    with pytest.raises(ValueError, match="same length"):
        fifty_two_week_high_distance([1, 2], [1])


def test_fifty_two_week_high_distance_rejects_invalid_windows() -> None:
    with pytest.raises(ValueError, match="window"):
        fifty_two_week_high_distance([1, 2, 3], window=0)


def test_classify_weekly_structure_covers_all_rulebook_labels() -> None:
    classifications = classify_weekly_structure(
        highs=[100, 110, 105, 108, 106, 100],
        lows=[90, 95, 96, 90, 90, 88],
    )

    assert classifications[0] is None
    assert [(item.label, item.raw_score) for item in classifications[1:]] == [
        ("HH_HL", Decimal("1.0")),
        ("HL_ONLY", Decimal("0.5")),
        ("MIXED", Decimal("0.0")),
        ("LH_ONLY", Decimal("-0.5")),
        ("LH_LL", Decimal("-1.0")),
    ]


def test_weekly_structure_reason_codes_are_stable_for_persistence() -> None:
    classification = classify_weekly_structure(
        highs=[100, 110],
        lows=[90, 95],
    )[1]

    assert classification is not None
    assert classification.reason_code == "WEEKLY_STRUCTURE_HH_HL"


def test_classify_weekly_structure_from_weekly_bars_uses_timestamp_order() -> None:
    start = datetime(2026, 1, 5, tzinfo=UTC)
    bars = (
        weekly_bar(start, "95", high="100", low="90"),
        weekly_bar(start + timedelta(weeks=1), "105", high="110", low="95"),
    )

    classification = classify_weekly_structure_from_weekly_bars(tuple(reversed(bars)))[1]

    assert classification is not None
    assert classification.label == "HH_HL"
    assert classification.raw_score == Decimal("1.0")


def test_classify_weekly_structure_uses_only_current_and_prior_week() -> None:
    highs = [100, 110, 1_000_000]
    lows = [90, 95, 1]

    assert classify_weekly_structure(highs, lows)[:-1] == classify_weekly_structure(
        highs[:-1],
        lows[:-1],
    )


def test_classify_weekly_structure_rejects_mismatched_inputs() -> None:
    with pytest.raises(ValueError, match="same length"):
        classify_weekly_structure(highs=[100], lows=[90, 95])


def test_classify_weekly_structure_rejects_impossible_weekly_ranges() -> None:
    with pytest.raises(ValueError, match="weekly high"):
        classify_weekly_structure(highs=[100], lows=[101])


def test_classify_weekly_structure_from_weekly_bars_rejects_non_weekly_bars() -> None:
    daily = OhlcvBar(**{**weekly_bar(datetime(2026, 1, 5, tzinfo=UTC), "100").as_record(), "timeframe": "1d"})

    with pytest.raises(ValueError, match="requires 1w bars"):
        classify_weekly_structure_from_weekly_bars([daily])
