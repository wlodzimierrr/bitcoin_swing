from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.data import OhlcvBar
from btc_predictor.features import (
    TWENTY_WEEK_MA_DISTANCE_FEATURE_ID,
    TWENTY_WEEK_MA_DISTANCE_LOOKBACK_WEEKS,
    WEEKLY_STRUCTURE_FEATURE_ID,
    WEEKLY_STRUCTURE_LABELS,
    WEEKLY_STRUCTURE_SCORES,
    classify_weekly_structure,
    classify_weekly_structure_from_weekly_bars,
    moving_average_distance,
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
