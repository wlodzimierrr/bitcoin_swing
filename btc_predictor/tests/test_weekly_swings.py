from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.data import OhlcvBar
from btc_predictor.levels import (
    DEFAULT_WEEKLY_SWING_LEFT_BARS,
    DEFAULT_WEEKLY_SWING_RIGHT_BARS,
    WEEKLY_SWING_HIGH,
    WEEKLY_SWING_LEVEL_FEATURE_ID,
    WEEKLY_SWING_LEVEL_TYPES,
    WEEKLY_SWING_LOW,
    WeeklySwingLevel,
    detect_weekly_swing_levels,
)


def weekly_bar(
    timestamp: datetime,
    *,
    high: str,
    low: str,
    ingested_at: datetime | None = None,
    timeframe: str = "1w",
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
        ingested_at=ingested_at or timestamp + timedelta(days=7),
    )


def weekly_bars(
    highs: tuple[str, ...],
    lows: tuple[str, ...],
    *,
    start: datetime = datetime(2026, 1, 5, tzinfo=UTC),
) -> tuple[OhlcvBar, ...]:
    return tuple(
        weekly_bar(start + timedelta(weeks=index), high=high, low=low)
        for index, (high, low) in enumerate(zip(highs, lows))
    )


def test_weekly_swing_metadata_is_stable() -> None:
    assert WEEKLY_SWING_LEVEL_FEATURE_ID == "WEEKLY_SWING_LEVEL"
    assert WEEKLY_SWING_HIGH == "swing_high"
    assert WEEKLY_SWING_LOW == "swing_low"
    assert WEEKLY_SWING_LEVEL_TYPES == ("swing_high", "swing_low")
    assert DEFAULT_WEEKLY_SWING_LEFT_BARS == 3
    assert DEFAULT_WEEKLY_SWING_RIGHT_BARS == 3


def test_detect_weekly_swing_levels_confirms_highs_and_lows_point_in_time() -> None:
    bars = weekly_bars(
        highs=("100", "105", "110", "120", "111", "108", "107"),
        lows=("90", "88", "85", "80", "86", "89", "91"),
    )

    levels = detect_weekly_swing_levels(
        tuple(reversed(bars)),
        as_of=datetime(2026, 2, 23, tzinfo=UTC),
        left_bars=3,
        right_bars=3,
    )

    assert [(level.level_type, level.price) for level in levels] == [
        ("swing_high", Decimal("120")),
        ("swing_low", Decimal("80")),
    ]
    assert all(level.level_timestamp == datetime(2026, 1, 26, tzinfo=UTC) for level in levels)
    assert all(level.detected_at == datetime(2026, 2, 23, tzinfo=UTC) for level in levels)
    assert all(level.detected_at > level.level_timestamp for level in levels)


def test_weekly_swing_detection_waits_for_confirmation_bars() -> None:
    bars = weekly_bars(
        highs=("100", "105", "110", "120", "111", "108", "107"),
        lows=("90", "88", "85", "80", "86", "89", "91"),
    )

    assert (
        detect_weekly_swing_levels(
            bars,
            as_of=datetime(2026, 2, 16, 23, 59, tzinfo=UTC),
            left_bars=3,
            right_bars=3,
        )
        == ()
    )

    assert detect_weekly_swing_levels(
        bars,
        as_of=datetime(2026, 2, 23, tzinfo=UTC),
        left_bars=3,
        right_bars=3,
    )


def test_weekly_swing_detection_ignores_late_ingested_confirmation_bar() -> None:
    bars = list(
        weekly_bars(
            highs=("100", "105", "110", "120", "111", "108", "107"),
            lows=("90", "88", "85", "80", "86", "89", "91"),
        )
    )
    bars[-1] = weekly_bar(
        datetime(2026, 2, 16, tzinfo=UTC),
        high="107",
        low="91",
        ingested_at=datetime(2026, 2, 24, tzinfo=UTC),
    )

    assert (
        detect_weekly_swing_levels(
            bars,
            as_of=datetime(2026, 2, 23, tzinfo=UTC),
            left_bars=3,
            right_bars=3,
        )
        == ()
    )

    levels = detect_weekly_swing_levels(
        bars,
        as_of=datetime(2026, 2, 24, tzinfo=UTC),
        left_bars=3,
        right_bars=3,
    )

    assert {level.detected_at for level in levels} == {
        datetime(2026, 2, 24, tzinfo=UTC),
    }


def test_weekly_swing_detection_excludes_future_unconfirmed_candidates() -> None:
    bars = weekly_bars(
        highs=("100", "105", "110", "120", "111", "108", "107", "140"),
        lows=("90", "88", "85", "80", "86", "89", "91", "70"),
    )

    levels = detect_weekly_swing_levels(
        bars,
        as_of=datetime(2026, 3, 2, tzinfo=UTC),
        left_bars=3,
        right_bars=3,
    )

    assert [(level.level_timestamp, level.price) for level in levels] == [
        (datetime(2026, 1, 26, tzinfo=UTC), Decimal("120")),
        (datetime(2026, 1, 26, tzinfo=UTC), Decimal("80")),
    ]


def test_weekly_swing_detection_requires_strict_extremes() -> None:
    bars = weekly_bars(
        highs=("100", "105", "120", "120", "111"),
        lows=("90", "88", "80", "80", "86"),
    )

    assert (
        detect_weekly_swing_levels(
            bars,
            as_of=datetime(2026, 2, 9, tzinfo=UTC),
            left_bars=2,
            right_bars=2,
        )
        == ()
    )


def test_weekly_swing_level_exposes_persistable_payload() -> None:
    level = WeeklySwingLevel(
        feature_id="WEEKLY_SWING_LEVEL",
        level_type="swing_high",
        level_timestamp=datetime(2026, 1, 26, tzinfo=UTC),
        detected_at=datetime(2026, 2, 23, tzinfo=UTC),
        price=Decimal("120"),
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1w",
        provider="coinbase",
        left_bars=3,
        right_bars=3,
        source_bar_count=7,
    )

    assert level.as_record() == {
        "feature_id": "WEEKLY_SWING_LEVEL",
        "level_type": "swing_high",
        "level_timestamp": "2026-01-26T00:00:00+00:00",
        "detected_at": "2026-02-23T00:00:00+00:00",
        "price": "120",
        "exchange": "coinbase",
        "symbol": "BTC-USD",
        "timeframe": "1w",
        "provider": "coinbase",
        "left_bars": 3,
        "right_bars": 3,
        "source_bar_count": 7,
    }


def test_weekly_swing_detection_rejects_invalid_inputs() -> None:
    bars = weekly_bars(
        highs=("100", "105", "110", "120", "111"),
        lows=("90", "88", "85", "80", "86"),
    )

    with pytest.raises(ValueError, match="as_of must be timezone-aware UTC"):
        detect_weekly_swing_levels(bars, as_of=datetime(2026, 2, 9))

    with pytest.raises(ValueError, match="left_bars"):
        detect_weekly_swing_levels(
            bars,
            as_of=datetime(2026, 2, 9, tzinfo=UTC),
            left_bars=0,
        )

    with pytest.raises(ValueError, match="right_bars"):
        detect_weekly_swing_levels(
            bars,
            as_of=datetime(2026, 2, 9, tzinfo=UTC),
            right_bars=0,
        )

    with pytest.raises(ValueError, match="canonical 1w bars"):
        detect_weekly_swing_levels(
            (
                weekly_bar(
                    datetime(2026, 1, 5, tzinfo=UTC),
                    high="100",
                    low="90",
                    timeframe="1d",
                ),
            ),
            as_of=datetime(2026, 2, 9, tzinfo=UTC),
        )

    with pytest.raises(ValueError, match="one exchange/symbol/provider/timeframe"):
        detect_weekly_swing_levels(
            (
                weekly_bar(datetime(2026, 1, 5, tzinfo=UTC), high="100", low="90"),
                weekly_bar(
                    datetime(2026, 1, 12, tzinfo=UTC),
                    high="105",
                    low="88",
                    provider="kraken",
                ),
            ),
            as_of=datetime(2026, 2, 9, tzinfo=UTC),
        )
