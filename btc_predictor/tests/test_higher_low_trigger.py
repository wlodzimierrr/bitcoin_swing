from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.data import OhlcvBar
from btc_predictor.levels import (
    WEEKLY_SWING_LEVEL_FEATURE_ID,
    WeeklySwingLevel,
    detect_weekly_swing_levels,
)
from btc_predictor.signals import (
    DEFAULT_HIGHER_LOW_BUFFER_FRACTION,
    DEFAULT_HIGHER_LOW_LEFT_BARS,
    DEFAULT_HIGHER_LOW_MAX_BREAKOUT_BARS,
    DEFAULT_HIGHER_LOW_MAX_PATTERN_BARS,
    DEFAULT_HIGHER_LOW_PIVOT_BREAK_BUFFER_FRACTION,
    DEFAULT_HIGHER_LOW_PIVOT_LEFT_BARS,
    DEFAULT_HIGHER_LOW_PIVOT_RIGHT_BARS,
    DEFAULT_HIGHER_LOW_RIGHT_BARS,
    HIGHER_LOW_TRIGGER_FEATURE_ID,
    HIGHER_LOW_TRIGGER_REASON_CODES,
    HIGHER_LOW_TRIGGER_TYPE,
    evaluate_higher_low_trigger,
)


WEEK_START = datetime(2026, 1, 5, tzinfo=UTC)
SOURCE_DETECTED_AT = datetime(2026, 2, 2, tzinfo=UTC)
ANCHOR_TIME = datetime(2026, 1, 7, tzinfo=UTC)


def source_low(
    *,
    level_type: str = "swing_low",
    detected_at: datetime = SOURCE_DETECTED_AT,
) -> WeeklySwingLevel:
    return WeeklySwingLevel(
        feature_id=WEEKLY_SWING_LEVEL_FEATURE_ID,
        level_type=level_type,
        level_timestamp=WEEK_START,
        detected_at=detected_at,
        price=Decimal("80"),
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1w",
        provider="coinbase",
        left_bars=3,
        right_bars=3,
        source_bar_count=7,
    )


def daily_bar(
    timestamp: datetime,
    *,
    high: str,
    low: str,
    close: str | None = None,
    ingested_at: datetime | None = None,
    provider: str = "coinbase",
    timeframe: str = "1d",
) -> OhlcvBar:
    close_value = Decimal(close or high)
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe=timeframe,
        open=close_value,
        high=Decimal(high),
        low=Decimal(low),
        close=close_value,
        volume=Decimal("100"),
        provider=provider,
        ingested_at=ingested_at or timestamp + timedelta(days=1),
    )


def confirmed_pattern(*, higher_low: str = "85") -> tuple[OhlcvBar, ...]:
    return (
        daily_bar(ANCHOR_TIME, high="84", low="80", close="82"),
        daily_bar(ANCHOR_TIME + timedelta(days=1), high="85", low="82"),
        daily_bar(ANCHOR_TIME + timedelta(days=2), high="90", low="84"),
        daily_bar(ANCHOR_TIME + timedelta(days=3), high="100", low="90"),
        daily_bar(ANCHOR_TIME + timedelta(days=4), high="96", low="88"),
        daily_bar(ANCHOR_TIME + timedelta(days=5), high="94", low=higher_low),
        daily_bar(ANCHOR_TIME + timedelta(days=6), high="95", low="87"),
        daily_bar(ANCHOR_TIME + timedelta(days=7), high="97", low="89"),
    )


def breakout_bar(
    *,
    day_offset: int = 8,
    high: str = "103",
    low: str = "90",
    close: str = "101",
) -> OhlcvBar:
    return daily_bar(
        ANCHOR_TIME + timedelta(days=day_offset),
        high=high,
        low=low,
        close=close,
    )


def test_higher_low_trigger_metadata_is_stable() -> None:
    assert HIGHER_LOW_TRIGGER_FEATURE_ID == "ENTRY_TRIGGER_HIGHER_LOW"
    assert HIGHER_LOW_TRIGGER_TYPE == "HIGHER_LOW"
    assert DEFAULT_HIGHER_LOW_PIVOT_LEFT_BARS == 2
    assert DEFAULT_HIGHER_LOW_PIVOT_RIGHT_BARS == 2
    assert DEFAULT_HIGHER_LOW_LEFT_BARS == 2
    assert DEFAULT_HIGHER_LOW_RIGHT_BARS == 2
    assert DEFAULT_HIGHER_LOW_MAX_PATTERN_BARS == 30
    assert DEFAULT_HIGHER_LOW_MAX_BREAKOUT_BARS == 10
    assert DEFAULT_HIGHER_LOW_BUFFER_FRACTION == Decimal("0")
    assert DEFAULT_HIGHER_LOW_PIVOT_BREAK_BUFFER_FRACTION == Decimal("0")
    assert HIGHER_LOW_TRIGGER_REASON_CODES == (
        "HIGHER_LOW_SOURCE_BAR_MISSING",
        "HIGHER_LOW_PIVOT_PENDING",
        "HIGHER_LOW_PIVOT_NOT_FOUND",
        "HIGHER_LOW_PULLBACK_PENDING",
        "HIGHER_LOW_PULLBACK_NOT_FOUND",
        "HIGHER_LOW_NOT_ABOVE_SOURCE",
        "HIGHER_LOW_BREAK_PENDING",
        "HIGHER_LOW_INVALIDATED",
        "HIGHER_LOW_BREAK_NOT_CONFIRMED",
        "HIGHER_LOW_CONFIRMED",
    )


def test_higher_low_confirms_only_when_source_level_is_known() -> None:
    config = load_strategy_config()
    bars = (*confirmed_pattern(), breakout_bar())

    result = evaluate_higher_low_trigger(
        source_low(),
        tuple(reversed(bars)),
        as_of=SOURCE_DETECTED_AT,
        config_metadata=config.run_metadata(),
    )

    assert result.triggered is True
    assert result.complete is True
    assert result.source_low_bar_timestamp == ANCHOR_TIME
    assert result.pivot_timestamp == ANCHOR_TIME + timedelta(days=3)
    assert result.pivot_detected_at == ANCHOR_TIME + timedelta(days=6)
    assert result.pivot_high == Decimal("100")
    assert result.higher_low_timestamp == ANCHOR_TIME + timedelta(days=5)
    assert result.higher_low_detected_at == ANCHOR_TIME + timedelta(days=8)
    assert result.higher_low_price == Decimal("85")
    assert result.confirmation_timestamp == ANCHOR_TIME + timedelta(days=8)
    assert result.confirmation_close == Decimal("101")
    assert result.detected_at == SOURCE_DETECTED_AT
    assert result.reason_codes == ("HIGHER_LOW_CONFIRMED",)
    record = result.as_record()
    assert record["source_swing_low"] == source_low().as_record()
    assert record["higher_low_threshold"] == "80"
    assert record["pivot_break_threshold"] == "100"
    assert record["config_metadata"] == config.run_metadata()


def test_higher_low_rejects_evaluation_before_btc_090_detection() -> None:
    with pytest.raises(ValueError, match="available by as_of"):
        evaluate_higher_low_trigger(
            source_low(),
            (*confirmed_pattern(), breakout_bar()),
            as_of=datetime(2026, 1, 20, tzinfo=UTC),
        )


def test_higher_low_reports_missing_source_daily_bar() -> None:
    bars = tuple(
        daily_bar(
            ANCHOR_TIME + timedelta(days=index),
            high=str(90 + index),
            low=str(81 + index),
        )
        for index in range(5)
    )

    result = evaluate_higher_low_trigger(
        source_low(),
        bars,
        as_of=SOURCE_DETECTED_AT,
    )

    assert result.complete is False
    assert result.triggered is False
    assert result.reason_codes == ("HIGHER_LOW_SOURCE_BAR_MISSING",)
    assert result.source_low_bar_timestamp is None
    assert result.evaluated_bar_timestamps == ()


def test_higher_low_uses_last_matching_low_in_source_week() -> None:
    first = daily_bar(ANCHOR_TIME, high="84", low="80", close="82")
    last = daily_bar(ANCHOR_TIME + timedelta(days=2), high="85", low="80", close="83")

    result = evaluate_higher_low_trigger(
        source_low(),
        (first, last),
        as_of=SOURCE_DETECTED_AT,
    )

    assert result.source_low_bar_timestamp == last.timestamp
    assert result.reason_codes == ("HIGHER_LOW_PIVOT_PENDING",)


def test_higher_low_pivot_search_is_pending_then_expires() -> None:
    anchor = daily_bar(ANCHOR_TIME, high="84", low="80", close="82")
    rising = tuple(
        daily_bar(
            ANCHOR_TIME + timedelta(days=index + 1),
            high=str(85 + index),
            low=str(82 + index),
        )
        for index in range(11)
    )

    pending = evaluate_higher_low_trigger(
        source_low(),
        (anchor, *rising[:10]),
        as_of=SOURCE_DETECTED_AT,
        max_pattern_bars=11,
    )
    expired = evaluate_higher_low_trigger(
        source_low(),
        (anchor, *rising),
        as_of=SOURCE_DETECTED_AT,
        max_pattern_bars=11,
    )

    assert pending.complete is False
    assert pending.reason_codes == ("HIGHER_LOW_PIVOT_PENDING",)
    assert expired.complete is True
    assert expired.reason_codes == ("HIGHER_LOW_PIVOT_NOT_FOUND",)


def test_higher_low_pullback_search_is_pending_then_expires() -> None:
    anchor = daily_bar(ANCHOR_TIME, high="84", low="80", close="82")
    pattern = (
        daily_bar(ANCHOR_TIME + timedelta(days=1), high="85", low="82"),
        daily_bar(ANCHOR_TIME + timedelta(days=2), high="90", low="84"),
        daily_bar(ANCHOR_TIME + timedelta(days=3), high="100", low="90"),
        daily_bar(ANCHOR_TIME + timedelta(days=4), high="96", low="89"),
        daily_bar(ANCHOR_TIME + timedelta(days=5), high="95", low="88"),
        daily_bar(ANCHOR_TIME + timedelta(days=6), high="94", low="87"),
        daily_bar(ANCHOR_TIME + timedelta(days=7), high="93", low="86"),
        daily_bar(ANCHOR_TIME + timedelta(days=8), high="92", low="85"),
        daily_bar(ANCHOR_TIME + timedelta(days=9), high="91", low="84"),
        daily_bar(ANCHOR_TIME + timedelta(days=10), high="90", low="83"),
        daily_bar(ANCHOR_TIME + timedelta(days=11), high="89", low="82"),
    )

    pending = evaluate_higher_low_trigger(
        source_low(),
        (anchor, *pattern[:10]),
        as_of=SOURCE_DETECTED_AT,
        max_pattern_bars=11,
    )
    expired = evaluate_higher_low_trigger(
        source_low(),
        (anchor, *pattern),
        as_of=SOURCE_DETECTED_AT,
        max_pattern_bars=11,
    )

    assert pending.reason_codes == ("HIGHER_LOW_PULLBACK_PENDING",)
    assert expired.complete is True
    assert expired.reason_codes == ("HIGHER_LOW_PULLBACK_NOT_FOUND",)


def test_higher_low_must_be_strictly_above_source_threshold() -> None:
    result = evaluate_higher_low_trigger(
        source_low(),
        confirmed_pattern(higher_low="80"),
        as_of=SOURCE_DETECTED_AT,
    )

    assert result.complete is True
    assert result.triggered is False
    assert result.higher_low_price == Decimal("80")
    assert result.reason_codes == ("HIGHER_LOW_NOT_ABOVE_SOURCE",)


def test_higher_low_break_window_is_strict_and_bounded() -> None:
    exact_closes = tuple(
        breakout_bar(day_offset=8 + index, high="102", low="86", close="100")
        for index in range(3)
    )

    pending = evaluate_higher_low_trigger(
        source_low(),
        (*confirmed_pattern(), *exact_closes[:2]),
        as_of=SOURCE_DETECTED_AT,
        max_breakout_bars=3,
    )
    expired = evaluate_higher_low_trigger(
        source_low(),
        (*confirmed_pattern(), *exact_closes),
        as_of=SOURCE_DETECTED_AT,
        max_breakout_bars=3,
    )

    assert pending.complete is False
    assert pending.reason_codes == ("HIGHER_LOW_BREAK_PENDING",)
    assert expired.complete is True
    assert expired.reason_codes == ("HIGHER_LOW_BREAK_NOT_CONFIRMED",)


def test_higher_low_is_invalidated_before_pivot_break() -> None:
    result = evaluate_higher_low_trigger(
        source_low(),
        (
            *confirmed_pattern(),
            breakout_bar(low="84", close="101"),
        ),
        as_of=SOURCE_DETECTED_AT,
    )

    assert result.complete is True
    assert result.triggered is False
    assert result.reason_codes == ("HIGHER_LOW_INVALIDATED",)
    assert result.confirmation_timestamp is None


def test_higher_low_applies_source_and_pivot_break_buffers() -> None:
    exact = breakout_bar(high="103", low="86", close="102")
    confirmed = breakout_bar(day_offset=9, high="104", low="86", close="102.1")

    result = evaluate_higher_low_trigger(
        source_low(),
        (*confirmed_pattern(), exact, confirmed),
        as_of=SOURCE_DETECTED_AT,
        higher_low_buffer_fraction="0.05",
        pivot_break_buffer_fraction="0.02",
    )

    assert result.triggered is True
    assert result.higher_low_threshold == Decimal("84.00")
    assert result.pivot_break_threshold == Decimal("102.00")
    assert result.confirmation_timestamp == confirmed.timestamp


def test_higher_low_filters_unavailable_series_and_future_appends() -> None:
    bars = (*confirmed_pattern(), breakout_bar())
    unrelated = daily_bar(
        ANCHOR_TIME + timedelta(days=8),
        high="110",
        low="90",
        provider="bitstamp",
    )
    future = breakout_bar(day_offset=60, high="120", low="90", close="119")

    base = evaluate_higher_low_trigger(
        source_low(),
        bars,
        as_of=SOURCE_DETECTED_AT,
    )
    appended = evaluate_higher_low_trigger(
        source_low(),
        (future, unrelated, *reversed(bars)),
        as_of=SOURCE_DETECTED_AT,
    )

    assert base.as_record() == appended.as_record()


def test_higher_low_waits_for_bar_close_and_ingestion() -> None:
    late_breakout = daily_bar(
        ANCHOR_TIME + timedelta(days=8),
        high="103",
        low="90",
        close="101",
        ingested_at=SOURCE_DETECTED_AT + timedelta(days=1),
    )

    result = evaluate_higher_low_trigger(
        source_low(),
        (*confirmed_pattern(), late_breakout),
        as_of=SOURCE_DETECTED_AT,
    )

    assert result.complete is False
    assert result.reason_codes == ("HIGHER_LOW_BREAK_PENDING",)
    assert result.confirmation_timestamp is None


def test_higher_low_rejects_invalid_inputs() -> None:
    as_of = SOURCE_DETECTED_AT
    with pytest.raises(ValueError, match="level_type swing_low"):
        evaluate_higher_low_trigger(source_low(level_type="swing_high"), (), as_of=as_of)
    with pytest.raises(ValueError, match="confirmation windows"):
        evaluate_higher_low_trigger(
            source_low(),
            (),
            as_of=as_of,
            max_pattern_bars=5,
        )
    with pytest.raises(ValueError, match="between 0 and 1"):
        evaluate_higher_low_trigger(
            source_low(),
            (),
            as_of=as_of,
            higher_low_buffer_fraction="1.1",
        )
    non_daily = daily_bar(
        ANCHOR_TIME,
        high="84",
        low="80",
        timeframe="1w",
    )
    with pytest.raises(ValueError, match="canonical 1d"):
        evaluate_higher_low_trigger(source_low(), (non_daily,), as_of=as_of)
    duplicate = daily_bar(ANCHOR_TIME, high="84", low="80")
    with pytest.raises(ValueError, match="must not contain duplicates"):
        evaluate_higher_low_trigger(
            source_low(),
            (duplicate, duplicate),
            as_of=as_of,
        )


def test_higher_low_integrates_with_btc_090_weekly_swing() -> None:
    weekly_bars = tuple(
        OhlcvBar(
            timestamp=datetime(2026, 1, 5, tzinfo=UTC) + timedelta(weeks=index),
            exchange="coinbase",
            symbol="BTC-USD",
            timeframe="1w",
            open=Decimal(low),
            high=Decimal(high),
            low=Decimal(low),
            close=Decimal(high),
            volume=Decimal("100"),
            provider="coinbase",
            ingested_at=(
                datetime(2026, 1, 5, tzinfo=UTC)
                + timedelta(weeks=index + 1)
            ),
        )
        for index, (high, low) in enumerate(
            zip(
                ("100", "105", "110", "120", "111", "108", "107"),
                ("90", "88", "85", "80", "86", "89", "91"),
            )
        )
    )
    levels = detect_weekly_swing_levels(
        weekly_bars,
        as_of=datetime(2026, 2, 23, tzinfo=UTC),
    )
    detected_low = next(level for level in levels if level.level_type == "swing_low")
    day_zero = detected_low.level_timestamp + timedelta(days=2)
    daily = (
        daily_bar(day_zero, high="84", low="80", close="82"),
        daily_bar(day_zero + timedelta(days=1), high="85", low="82"),
        daily_bar(day_zero + timedelta(days=2), high="90", low="84"),
        daily_bar(day_zero + timedelta(days=3), high="100", low="90"),
        daily_bar(day_zero + timedelta(days=4), high="96", low="88"),
        daily_bar(day_zero + timedelta(days=5), high="94", low="85"),
        daily_bar(day_zero + timedelta(days=6), high="95", low="87"),
        daily_bar(day_zero + timedelta(days=7), high="97", low="89"),
        daily_bar(day_zero + timedelta(days=8), high="103", low="90", close="101"),
    )

    result = evaluate_higher_low_trigger(
        detected_low,
        daily,
        as_of=datetime(2026, 2, 23, tzinfo=UTC),
    )

    assert result.triggered is True
    assert result.source_swing_low is detected_low
    assert result.detected_at == detected_low.detected_at
