from datetime import UTC, datetime
from decimal import Decimal

import pytest

from btc_predictor.data import OhlcvBar, next_bar_timestamp
from btc_predictor.levels import (
    DEFAULT_MONTHLY_SWING_LEFT_BARS,
    DEFAULT_MONTHLY_SWING_RIGHT_BARS,
    MONTHLY_SWING_HIGH,
    MONTHLY_SWING_LEVEL_FEATURE_ID,
    MONTHLY_SWING_LEVEL_TYPES,
    MONTHLY_SWING_LOW,
    MonthlySwingLevel,
    detect_monthly_swing_levels,
)


def month_start(year: int, month: int) -> datetime:
    return datetime(year, month, 1, tzinfo=UTC)


def monthly_bar(
    timestamp: datetime,
    *,
    high: str,
    low: str,
    ingested_at: datetime | None = None,
    timeframe: str = "1mo",
    provider: str = "coinbase",
) -> OhlcvBar:
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe=timeframe,
        open=Decimal(low),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(high),
        volume=Decimal("100"),
        provider=provider,
        ingested_at=ingested_at or next_bar_timestamp(timestamp, "1mo"),
    )


def monthly_bars(
    highs: tuple[str, ...],
    lows: tuple[str, ...],
    *,
    start: datetime = month_start(2026, 1),
) -> tuple[OhlcvBar, ...]:
    timestamp = start
    bars = []
    for high, low in zip(highs, lows):
        bars.append(monthly_bar(timestamp, high=high, low=low))
        timestamp = next_bar_timestamp(timestamp, "1mo")
    return tuple(bars)


def test_monthly_swing_metadata_is_stable() -> None:
    assert MONTHLY_SWING_LEVEL_FEATURE_ID == "MONTHLY_SWING_LEVEL"
    assert MONTHLY_SWING_HIGH == "swing_high"
    assert MONTHLY_SWING_LOW == "swing_low"
    assert MONTHLY_SWING_LEVEL_TYPES == ("swing_high", "swing_low")
    assert DEFAULT_MONTHLY_SWING_LEFT_BARS == 2
    assert DEFAULT_MONTHLY_SWING_RIGHT_BARS == 2


def test_detect_monthly_swing_levels_confirms_highs_and_lows_point_in_time() -> None:
    bars = monthly_bars(
        highs=("100", "110", "130", "115", "112"),
        lows=("90", "84", "70", "82", "88"),
    )

    levels = detect_monthly_swing_levels(
        tuple(reversed(bars)),
        as_of=month_start(2026, 6),
        left_bars=2,
        right_bars=2,
    )

    assert [(level.level_type, level.price) for level in levels] == [
        ("swing_high", Decimal("130")),
        ("swing_low", Decimal("70")),
    ]
    assert all(level.level_timestamp == month_start(2026, 3) for level in levels)
    assert all(level.detected_at == month_start(2026, 6) for level in levels)
    assert all(level.detected_at > level.level_timestamp for level in levels)


def test_monthly_swing_detection_waits_for_confirmation_months() -> None:
    bars = monthly_bars(
        highs=("100", "110", "130", "115", "112"),
        lows=("90", "84", "70", "82", "88"),
    )

    assert (
        detect_monthly_swing_levels(
            bars,
            as_of=datetime(2026, 5, 31, 23, 59, tzinfo=UTC),
            left_bars=2,
            right_bars=2,
        )
        == ()
    )

    assert detect_monthly_swing_levels(
        bars,
        as_of=month_start(2026, 6),
        left_bars=2,
        right_bars=2,
    )


def test_monthly_swing_detection_ignores_late_ingested_confirmation_bar() -> None:
    bars = list(
        monthly_bars(
            highs=("100", "110", "130", "115", "112"),
            lows=("90", "84", "70", "82", "88"),
        )
    )
    bars[-1] = monthly_bar(
        month_start(2026, 5),
        high="112",
        low="88",
        ingested_at=datetime(2026, 6, 2, tzinfo=UTC),
    )

    assert (
        detect_monthly_swing_levels(
            bars,
            as_of=month_start(2026, 6),
            left_bars=2,
            right_bars=2,
        )
        == ()
    )

    levels = detect_monthly_swing_levels(
        bars,
        as_of=datetime(2026, 6, 2, tzinfo=UTC),
        left_bars=2,
        right_bars=2,
    )

    assert {level.detected_at for level in levels} == {
        datetime(2026, 6, 2, tzinfo=UTC),
    }


def test_monthly_swing_detection_excludes_future_unconfirmed_candidates() -> None:
    bars = monthly_bars(
        highs=("100", "110", "130", "115", "112", "150"),
        lows=("90", "84", "70", "82", "88", "60"),
    )

    levels = detect_monthly_swing_levels(
        bars,
        as_of=month_start(2026, 7),
        left_bars=2,
        right_bars=2,
    )

    assert [(level.level_timestamp, level.price) for level in levels] == [
        (month_start(2026, 3), Decimal("130")),
        (month_start(2026, 3), Decimal("70")),
    ]


def test_monthly_swing_detection_requires_strict_extremes() -> None:
    bars = monthly_bars(
        highs=("100", "130", "130", "115", "112"),
        lows=("90", "70", "70", "82", "88"),
    )

    assert (
        detect_monthly_swing_levels(
            bars,
            as_of=month_start(2026, 6),
            left_bars=2,
            right_bars=2,
        )
        == ()
    )


def test_monthly_swing_level_exposes_persistable_payload() -> None:
    level = MonthlySwingLevel(
        feature_id="MONTHLY_SWING_LEVEL",
        level_type="swing_high",
        level_timestamp=month_start(2026, 3),
        detected_at=month_start(2026, 6),
        price=Decimal("130"),
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1mo",
        provider="coinbase",
        left_bars=2,
        right_bars=2,
        source_bar_count=5,
    )

    assert level.as_record() == {
        "feature_id": "MONTHLY_SWING_LEVEL",
        "level_type": "swing_high",
        "level_timestamp": "2026-03-01T00:00:00+00:00",
        "detected_at": "2026-06-01T00:00:00+00:00",
        "price": "130",
        "exchange": "coinbase",
        "symbol": "BTC-USD",
        "timeframe": "1mo",
        "provider": "coinbase",
        "left_bars": 2,
        "right_bars": 2,
        "source_bar_count": 5,
    }


def test_monthly_swing_detection_rejects_invalid_inputs() -> None:
    bars = monthly_bars(
        highs=("100", "110", "130", "115", "112"),
        lows=("90", "84", "70", "82", "88"),
    )

    with pytest.raises(ValueError, match="as_of must be timezone-aware UTC"):
        detect_monthly_swing_levels(bars, as_of=datetime(2026, 6, 1))

    with pytest.raises(ValueError, match="left_bars"):
        detect_monthly_swing_levels(
            bars,
            as_of=month_start(2026, 6),
            left_bars=0,
        )

    with pytest.raises(ValueError, match="right_bars"):
        detect_monthly_swing_levels(
            bars,
            as_of=month_start(2026, 6),
            right_bars=0,
        )

    with pytest.raises(ValueError, match="canonical 1mo bars"):
        detect_monthly_swing_levels(
            (
                monthly_bar(
                    month_start(2026, 1),
                    high="100",
                    low="90",
                    timeframe="1w",
                ),
            ),
            as_of=month_start(2026, 6),
        )

    with pytest.raises(ValueError, match="one exchange/symbol/provider/timeframe"):
        detect_monthly_swing_levels(
            (
                monthly_bar(month_start(2026, 1), high="100", low="90"),
                monthly_bar(
                    month_start(2026, 2),
                    high="110",
                    low="84",
                    provider="kraken",
                ),
            ),
            as_of=month_start(2026, 6),
        )
