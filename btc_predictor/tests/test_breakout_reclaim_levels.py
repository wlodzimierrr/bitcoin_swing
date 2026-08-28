from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.data import OhlcvBar
from btc_predictor.levels import (
    BREAKOUT_LEVEL_TYPE,
    BREAKOUT_RECLAIM_LEVEL_FEATURE_ID,
    BREAKOUT_RECLAIM_LEVEL_ROLES,
    BREAKOUT_RECLAIM_LEVEL_TYPES,
    BREAKOUT_RECLAIM_REASON_CODES,
    BREAKOUT_SUPPORT_ROLE,
    DEFAULT_BREAKOUT_CLOSE_BUFFER_FRACTION,
    DEFAULT_RECLAIM_CLOSE_BUFFER_FRACTION,
    MONTHLY_SWING_LEVEL_FEATURE_ID,
    RECLAIM_LEVEL_TYPE,
    RECLAIM_SUPPORT_ROLE,
    WEEKLY_SWING_LEVEL_FEATURE_ID,
    BreakoutReclaimLevel,
    MonthlySwingLevel,
    WeeklySwingLevel,
    detect_breakout_reclaim_levels,
)


def daily_bar(
    timestamp: datetime,
    *,
    high: str,
    low: str,
    close: str,
    ingested_at: datetime | None = None,
    timeframe: str = "1d",
    provider: str = "coinbase",
) -> OhlcvBar:
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe=timeframe,
        open=Decimal(close),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("100"),
        provider=provider,
        ingested_at=ingested_at or timestamp + timedelta(days=1),
    )


def weekly_swing_high(
    *,
    price: str = "120",
    detected_at: datetime = datetime(2026, 2, 23, tzinfo=UTC),
    provider: str = "coinbase",
) -> WeeklySwingLevel:
    return WeeklySwingLevel(
        feature_id=WEEKLY_SWING_LEVEL_FEATURE_ID,
        level_type="swing_high",
        level_timestamp=datetime(2026, 1, 26, tzinfo=UTC),
        detected_at=detected_at,
        price=Decimal(price),
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1w",
        provider=provider,
        left_bars=3,
        right_bars=3,
        source_bar_count=7,
    )


def monthly_swing_low(
    *,
    price: str = "80",
    detected_at: datetime = datetime(2026, 6, 1, tzinfo=UTC),
    provider: str = "coinbase",
) -> MonthlySwingLevel:
    return MonthlySwingLevel(
        feature_id=MONTHLY_SWING_LEVEL_FEATURE_ID,
        level_type="swing_low",
        level_timestamp=datetime(2026, 3, 1, tzinfo=UTC),
        detected_at=detected_at,
        price=Decimal(price),
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1mo",
        provider=provider,
        left_bars=2,
        right_bars=2,
        source_bar_count=5,
    )


def test_breakout_reclaim_metadata_is_stable() -> None:
    assert BREAKOUT_RECLAIM_LEVEL_FEATURE_ID == "BREAKOUT_RECLAIM_LEVEL"
    assert BREAKOUT_LEVEL_TYPE == "breakout"
    assert RECLAIM_LEVEL_TYPE == "reclaim"
    assert BREAKOUT_RECLAIM_LEVEL_TYPES == ("breakout", "reclaim")
    assert BREAKOUT_SUPPORT_ROLE == "support_after_breakout"
    assert RECLAIM_SUPPORT_ROLE == "reclaimed_support"
    assert BREAKOUT_RECLAIM_LEVEL_ROLES == (
        "support_after_breakout",
        "reclaimed_support",
    )
    assert DEFAULT_BREAKOUT_CLOSE_BUFFER_FRACTION == Decimal("0")
    assert DEFAULT_RECLAIM_CLOSE_BUFFER_FRACTION == Decimal("0")
    assert BREAKOUT_RECLAIM_REASON_CODES == (
        "BREAKOUT_RECLAIM_INPUT_MISSING",
        "BREAKOUT_CONFIRMED",
        "RECLAIM_CONFIRMED",
    )


def test_detect_breakout_level_from_confirmed_swing_high() -> None:
    levels = detect_breakout_reclaim_levels(
        (weekly_swing_high(),),
        (
            daily_bar(datetime(2026, 2, 24, tzinfo=UTC), high="121", low="116", close="119"),
            daily_bar(datetime(2026, 2, 25, tzinfo=UTC), high="126", low="118", close="123"),
        ),
        as_of=datetime(2026, 2, 26, tzinfo=UTC),
    )

    assert len(levels) == 1
    assert levels[0].level_type == "breakout"
    assert levels[0].level_role == "support_after_breakout"
    assert levels[0].price == Decimal("120")
    assert levels[0].level_timestamp == datetime(2026, 2, 25, tzinfo=UTC)
    assert levels[0].confirmation_timestamp == datetime(2026, 2, 25, tzinfo=UTC)
    assert levels[0].detected_at == datetime(2026, 2, 26, tzinfo=UTC)
    assert levels[0].source_level_timestamp == datetime(2026, 1, 26, tzinfo=UTC)
    assert levels[0].source_level_detected_at == datetime(2026, 2, 23, tzinfo=UTC)
    assert levels[0].reason_codes == ("BREAKOUT_CONFIRMED",)


def test_detect_reclaim_level_from_confirmed_swing_low() -> None:
    levels = detect_breakout_reclaim_levels(
        (monthly_swing_low(),),
        (
            daily_bar(datetime(2026, 6, 2, tzinfo=UTC), high="84", low="78", close="82"),
        ),
        as_of=datetime(2026, 6, 3, tzinfo=UTC),
    )

    assert len(levels) == 1
    assert levels[0].level_type == "reclaim"
    assert levels[0].level_role == "reclaimed_support"
    assert levels[0].price == Decimal("80")
    assert levels[0].level_timestamp == datetime(2026, 6, 2, tzinfo=UTC)
    assert levels[0].detected_at == datetime(2026, 6, 3, tzinfo=UTC)
    assert levels[0].source_level_timestamp == datetime(2026, 3, 1, tzinfo=UTC)
    assert levels[0].source_level_detected_at == datetime(2026, 6, 1, tzinfo=UTC)
    assert levels[0].reason_codes == ("RECLAIM_CONFIRMED",)


def test_breakout_reclaim_waits_for_source_level_detection() -> None:
    levels = detect_breakout_reclaim_levels(
        (weekly_swing_high(detected_at=datetime(2026, 2, 27, tzinfo=UTC)),),
        (
            daily_bar(datetime(2026, 2, 25, tzinfo=UTC), high="126", low="118", close="123"),
        ),
        as_of=datetime(2026, 2, 26, tzinfo=UTC),
    )

    assert levels == ()


def test_breakout_reclaim_waits_for_confirmation_bar_close_and_ingestion() -> None:
    breakout_bar = daily_bar(
        datetime(2026, 2, 25, tzinfo=UTC),
        high="126",
        low="118",
        close="123",
        ingested_at=datetime(2026, 2, 27, tzinfo=UTC),
    )

    assert (
        detect_breakout_reclaim_levels(
            (weekly_swing_high(),),
            (breakout_bar,),
            as_of=datetime(2026, 2, 26, tzinfo=UTC),
        )
        == ()
    )

    levels = detect_breakout_reclaim_levels(
        (weekly_swing_high(),),
        (breakout_bar,),
        as_of=datetime(2026, 2, 27, tzinfo=UTC),
    )

    assert len(levels) == 1
    assert levels[0].detected_at == datetime(2026, 2, 27, tzinfo=UTC)


def test_breakout_reclaim_ignores_future_bars_and_other_series() -> None:
    levels = detect_breakout_reclaim_levels(
        (weekly_swing_high(), monthly_swing_low(provider="kraken")),
        (
            daily_bar(datetime(2026, 2, 25, tzinfo=UTC), high="126", low="118", close="123"),
            daily_bar(
                datetime(2026, 6, 2, tzinfo=UTC),
                high="84",
                low="78",
                close="82",
                provider="kraken",
            ),
        ),
        as_of=datetime(2026, 2, 26, tzinfo=UTC),
    )

    assert [(level.level_type, level.price) for level in levels] == [
        ("breakout", Decimal("120")),
    ]


def test_breakout_reclaim_uses_close_buffer_thresholds() -> None:
    source_level = weekly_swing_high(price="100")
    first_bar = daily_bar(
        datetime(2026, 2, 25, tzinfo=UTC),
        high="103",
        low="99",
        close="101",
    )
    second_bar = daily_bar(
        datetime(2026, 2, 26, tzinfo=UTC),
        high="104",
        low="100",
        close="102.5",
    )

    levels = detect_breakout_reclaim_levels(
        (source_level,),
        (first_bar, second_bar),
        as_of=datetime(2026, 2, 27, tzinfo=UTC),
        breakout_close_buffer_fraction=Decimal("0.02"),
    )

    assert len(levels) == 1
    assert levels[0].level_timestamp == datetime(2026, 2, 26, tzinfo=UTC)
    assert levels[0].confirming_close == Decimal("102.5")
    assert levels[0].close_buffer_fraction == Decimal("0.02")


def test_reclaim_uses_low_through_level_and_close_above_buffer() -> None:
    source_level = monthly_swing_low(price="100")
    around_level = daily_bar(
        datetime(2026, 6, 2, tzinfo=UTC),
        high="102",
        low="99",
        close="100.5",
    )
    reclaim_bar = daily_bar(
        datetime(2026, 6, 3, tzinfo=UTC),
        high="104",
        low="99",
        close="102.5",
    )

    levels = detect_breakout_reclaim_levels(
        (source_level,),
        (around_level, reclaim_bar),
        as_of=datetime(2026, 6, 4, tzinfo=UTC),
        reclaim_close_buffer_fraction=Decimal("0.02"),
    )

    assert len(levels) == 1
    assert levels[0].level_timestamp == datetime(2026, 6, 3, tzinfo=UTC)
    assert levels[0].confirming_low == Decimal("99")
    assert levels[0].confirming_close == Decimal("102.5")


def test_breakout_reclaim_level_exposes_persistable_payload() -> None:
    level = BreakoutReclaimLevel(
        feature_id="BREAKOUT_RECLAIM_LEVEL",
        level_type="breakout",
        level_role="support_after_breakout",
        level_timestamp=datetime(2026, 2, 25, tzinfo=UTC),
        detected_at=datetime(2026, 2, 26, tzinfo=UTC),
        confirmation_timestamp=datetime(2026, 2, 25, tzinfo=UTC),
        price=Decimal("120"),
        source_level_feature_id="WEEKLY_SWING_LEVEL",
        source_level_type="swing_high",
        source_level_timestamp=datetime(2026, 1, 26, tzinfo=UTC),
        source_level_detected_at=datetime(2026, 2, 23, tzinfo=UTC),
        confirmation_timeframe="1d",
        exchange="coinbase",
        symbol="BTC-USD",
        provider="coinbase",
        close_buffer_fraction=Decimal("0.01"),
        confirming_close=Decimal("123"),
        confirming_low=Decimal("118"),
        source_bar_count=2,
        reason_codes=("BREAKOUT_CONFIRMED",),
    )

    assert level.as_record() == {
        "feature_id": "BREAKOUT_RECLAIM_LEVEL",
        "level_type": "breakout",
        "level_role": "support_after_breakout",
        "level_timestamp": "2026-02-25T00:00:00+00:00",
        "detected_at": "2026-02-26T00:00:00+00:00",
        "confirmation_timestamp": "2026-02-25T00:00:00+00:00",
        "price": "120",
        "source_level_feature_id": "WEEKLY_SWING_LEVEL",
        "source_level_type": "swing_high",
        "source_level_timestamp": "2026-01-26T00:00:00+00:00",
        "source_level_detected_at": "2026-02-23T00:00:00+00:00",
        "confirmation_timeframe": "1d",
        "exchange": "coinbase",
        "symbol": "BTC-USD",
        "provider": "coinbase",
        "close_buffer_fraction": "0.01",
        "confirming_close": "123",
        "confirming_low": "118",
        "source_bar_count": 2,
        "reason_codes": ["BREAKOUT_CONFIRMED"],
    }


def test_breakout_reclaim_detection_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="as_of must be timezone-aware UTC"):
        detect_breakout_reclaim_levels((), (), as_of=datetime(2026, 2, 26))

    with pytest.raises(ValueError, match="breakout_close_buffer_fraction"):
        detect_breakout_reclaim_levels(
            (),
            (),
            as_of=datetime(2026, 2, 26, tzinfo=UTC),
            breakout_close_buffer_fraction=Decimal("-0.01"),
        )

    with pytest.raises(ValueError, match="reclaim_close_buffer_fraction"):
        detect_breakout_reclaim_levels(
            (),
            (),
            as_of=datetime(2026, 2, 26, tzinfo=UTC),
            reclaim_close_buffer_fraction=Decimal("-0.01"),
        )

    with pytest.raises(ValueError, match="canonical bars"):
        detect_breakout_reclaim_levels(
            (weekly_swing_high(),),
            (
                daily_bar(
                    datetime(2026, 2, 25, tzinfo=UTC),
                    high="126",
                    low="118",
                    close="123",
                    timeframe="4h",
                ),
            ),
            as_of=datetime(2026, 2, 26, tzinfo=UTC),
        )
