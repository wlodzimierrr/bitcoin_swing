from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.data import OhlcvBar
from btc_predictor.levels import (
    BREAKOUT_RECLAIM_LEVEL_FEATURE_ID,
    WEEKLY_SWING_LEVEL_FEATURE_ID,
    BreakoutReclaimLevel,
    WeeklySwingLevel,
    detect_breakout_reclaim_levels,
)
from btc_predictor.signals import (
    BREAKOUT_RETEST_TRIGGER_FEATURE_ID,
    BREAKOUT_RETEST_TRIGGER_REASON_CODES,
    BREAKOUT_RETEST_TRIGGER_TYPE,
    DEFAULT_BREAKOUT_RETEST_CONTINUATION_BUFFER_ATR,
    DEFAULT_BREAKOUT_RETEST_DISTANCE_ATR_MAX,
    DEFAULT_BREAKOUT_RETEST_MAX_CONTINUATION_BARS,
    DEFAULT_BREAKOUT_RETEST_MAX_RETEST_BARS,
    DEFAULT_BREAKOUT_RETEST_SUPPORT_BREACH_ATR_MAX,
    evaluate_breakout_retest_trigger,
)


BREAKOUT_TIME = datetime(2026, 6, 2, tzinfo=UTC)
BREAKOUT_DETECTED_AT = datetime(2026, 6, 3, tzinfo=UTC)


def breakout_level(
    *,
    detected_at: datetime = BREAKOUT_DETECTED_AT,
) -> BreakoutReclaimLevel:
    return BreakoutReclaimLevel(
        feature_id=BREAKOUT_RECLAIM_LEVEL_FEATURE_ID,
        level_type="breakout",
        level_role="support_after_breakout",
        level_timestamp=BREAKOUT_TIME,
        detected_at=detected_at,
        confirmation_timestamp=BREAKOUT_TIME,
        price=Decimal("100"),
        source_level_feature_id=WEEKLY_SWING_LEVEL_FEATURE_ID,
        source_level_type="swing_high",
        source_level_timestamp=datetime(2026, 5, 4, tzinfo=UTC),
        source_level_detected_at=datetime(2026, 6, 1, tzinfo=UTC),
        confirmation_timeframe="1d",
        exchange="coinbase",
        symbol="BTC-USD",
        provider="coinbase",
        close_buffer_fraction=Decimal("0"),
        confirming_close=Decimal("106"),
        confirming_low=Decimal("99"),
        source_bar_count=1,
        reason_codes=("BREAKOUT_CONFIRMED",),
    )


def daily_bar(
    timestamp: datetime,
    *,
    low: str,
    high: str,
    close: str,
    ingested_at: datetime | None = None,
    provider: str = "coinbase",
    timeframe: str = "1d",
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


def test_breakout_retest_metadata_is_stable() -> None:
    assert BREAKOUT_RETEST_TRIGGER_FEATURE_ID == "ENTRY_TRIGGER_BREAKOUT_RETEST"
    assert BREAKOUT_RETEST_TRIGGER_TYPE == "BREAKOUT_RETEST"
    assert DEFAULT_BREAKOUT_RETEST_MAX_RETEST_BARS == 5
    assert DEFAULT_BREAKOUT_RETEST_MAX_CONTINUATION_BARS == 3
    assert DEFAULT_BREAKOUT_RETEST_DISTANCE_ATR_MAX == Decimal("0.50")
    assert DEFAULT_BREAKOUT_RETEST_SUPPORT_BREACH_ATR_MAX == Decimal("0.25")
    assert DEFAULT_BREAKOUT_RETEST_CONTINUATION_BUFFER_ATR == Decimal("0")
    assert BREAKOUT_RETEST_TRIGGER_REASON_CODES == (
        "BREAKOUT_RETEST_ATR_MISSING",
        "BREAKOUT_RETEST_PENDING",
        "BREAKOUT_RETEST_NOT_FOUND",
        "BREAKOUT_RETEST_SUPPORT_FAILED",
        "BREAKOUT_RETEST_CONTINUATION_PENDING",
        "BREAKOUT_RETEST_CONTINUATION_NOT_CONFIRMED",
        "BREAKOUT_RETEST_CONFIRMED",
    )


def test_breakout_retest_reports_missing_atr_without_scanning_bars() -> None:
    result = evaluate_breakout_retest_trigger(
        breakout_level(),
        (
            daily_bar(
                BREAKOUT_DETECTED_AT,
                low="102",
                high="104",
                close="103",
            ),
        ),
        as_of=datetime(2026, 6, 4, tzinfo=UTC),
    )

    assert result.triggered is False
    assert result.complete is False
    assert result.reason_codes == ("BREAKOUT_RETEST_ATR_MISSING",)
    assert result.atr is None
    assert result.retest_zone_upper is None
    assert result.evaluated_bar_timestamps == ()
    assert result.source_bar_count == 1


def test_breakout_retest_confirms_retest_then_continuation() -> None:
    config = load_strategy_config()
    retest = daily_bar(
        BREAKOUT_DETECTED_AT,
        low="102",
        high="104",
        close="103",
    )
    continuation = daily_bar(
        BREAKOUT_DETECTED_AT + timedelta(days=1),
        low="101",
        high="106",
        close="105",
    )

    result = evaluate_breakout_retest_trigger(
        breakout_level(),
        (continuation, retest),
        as_of=datetime(2026, 6, 5, tzinfo=UTC),
        atr=Decimal("10"),
        atr_available_at=BREAKOUT_DETECTED_AT,
        config_metadata=config.run_metadata(),
    )

    assert result.triggered is True
    assert result.complete is True
    assert result.retest_timestamp == BREAKOUT_DETECTED_AT
    assert result.retest_detected_at == datetime(2026, 6, 4, tzinfo=UTC)
    assert result.retest_distance_atr == Decimal("0.2")
    assert result.continuation_threshold == Decimal("104")
    assert result.confirmation_timestamp == BREAKOUT_DETECTED_AT + timedelta(days=1)
    assert result.detected_at == datetime(2026, 6, 5, tzinfo=UTC)
    assert result.reason_codes == ("BREAKOUT_RETEST_CONFIRMED",)
    record = result.as_record()
    assert record["source_breakout_level"] == breakout_level().as_record()
    assert record["atr"] == "10"
    assert record["atr_available_at"] == "2026-06-03T00:00:00+00:00"
    assert record["retest_zone_upper"] == "105.00"
    assert record["support_floor"] == "97.50"
    assert record["evaluated_bar_timestamps"] == [
        "2026-06-03T00:00:00+00:00",
        "2026-06-04T00:00:00+00:00",
    ]
    assert record["config_metadata"] == config.run_metadata()


def test_breakout_retest_waits_for_closed_and_ingested_bars() -> None:
    late = daily_bar(
        BREAKOUT_DETECTED_AT,
        low="102",
        high="104",
        close="103",
        ingested_at=datetime(2026, 6, 5, tzinfo=UTC),
    )

    before_close = evaluate_breakout_retest_trigger(
        breakout_level(),
        (late,),
        as_of=datetime(2026, 6, 3, 12, tzinfo=UTC),
        atr="10",
        atr_available_at=BREAKOUT_DETECTED_AT,
    )
    before_ingestion = evaluate_breakout_retest_trigger(
        breakout_level(),
        (late,),
        as_of=datetime(2026, 6, 4, tzinfo=UTC),
        atr="10",
        atr_available_at=BREAKOUT_DETECTED_AT,
    )

    for result in (before_close, before_ingestion):
        assert result.complete is False
        assert result.reason_codes == ("BREAKOUT_RETEST_PENDING",)
        assert result.source_bar_count == 0
        assert result.evaluated_bar_timestamps == ()


def test_breakout_retest_expires_when_retest_window_is_exhausted() -> None:
    bars = tuple(
        daily_bar(
            BREAKOUT_DETECTED_AT + timedelta(days=index),
            low="106",
            high="110",
            close="108",
        )
        for index in range(5)
    )

    pending = evaluate_breakout_retest_trigger(
        breakout_level(),
        bars[:4],
        as_of=datetime(2026, 6, 7, tzinfo=UTC),
        atr="10",
        atr_available_at=BREAKOUT_DETECTED_AT,
    )
    expired = evaluate_breakout_retest_trigger(
        breakout_level(),
        bars,
        as_of=datetime(2026, 6, 8, tzinfo=UTC),
        atr="10",
        atr_available_at=BREAKOUT_DETECTED_AT,
    )

    assert pending.complete is False
    assert pending.reason_codes == ("BREAKOUT_RETEST_PENDING",)
    assert expired.complete is True
    assert expired.triggered is False
    assert expired.reason_codes == ("BREAKOUT_RETEST_NOT_FOUND",)
    assert len(expired.evaluated_bar_timestamps) == 5


@pytest.mark.parametrize(
    ("low", "close"),
    [("97", "101"), ("99", "99")],
)
def test_breakout_retest_fails_when_contact_does_not_hold_support(
    low: str,
    close: str,
) -> None:
    result = evaluate_breakout_retest_trigger(
        breakout_level(),
        (
            daily_bar(
                BREAKOUT_DETECTED_AT,
                low=low,
                high="104",
                close=close,
            ),
        ),
        as_of=datetime(2026, 6, 4, tzinfo=UTC),
        atr="10",
        atr_available_at=BREAKOUT_DETECTED_AT,
    )

    assert result.complete is True
    assert result.triggered is False
    assert result.reason_codes == ("BREAKOUT_RETEST_SUPPORT_FAILED",)
    assert result.retest_timestamp is None


def test_breakout_retest_continuation_window_is_strict_and_bounded() -> None:
    retest = daily_bar(
        BREAKOUT_DETECTED_AT,
        low="100",
        high="104",
        close="102",
    )
    non_confirming = tuple(
        daily_bar(
            BREAKOUT_DETECTED_AT + timedelta(days=index),
            low="100",
            high="105",
            close="104",
        )
        for index in range(1, 4)
    )

    pending = evaluate_breakout_retest_trigger(
        breakout_level(),
        (retest, *non_confirming[:2]),
        as_of=datetime(2026, 6, 6, tzinfo=UTC),
        atr="10",
        atr_available_at=BREAKOUT_DETECTED_AT,
    )
    failed = evaluate_breakout_retest_trigger(
        breakout_level(),
        (retest, *non_confirming),
        as_of=datetime(2026, 6, 7, tzinfo=UTC),
        atr="10",
        atr_available_at=BREAKOUT_DETECTED_AT,
    )

    assert pending.complete is False
    assert pending.reason_codes == ("BREAKOUT_RETEST_CONTINUATION_PENDING",)
    assert failed.complete is True
    assert failed.triggered is False
    assert failed.reason_codes == (
        "BREAKOUT_RETEST_CONTINUATION_NOT_CONFIRMED",
    )


def test_breakout_retest_fails_if_support_breaks_during_continuation() -> None:
    result = evaluate_breakout_retest_trigger(
        breakout_level(),
        (
            daily_bar(
                BREAKOUT_DETECTED_AT,
                low="101",
                high="104",
                close="102",
            ),
            daily_bar(
                BREAKOUT_DETECTED_AT + timedelta(days=1),
                low="97",
                high="106",
                close="105",
            ),
        ),
        as_of=datetime(2026, 6, 5, tzinfo=UTC),
        atr="10",
        atr_available_at=BREAKOUT_DETECTED_AT,
    )

    assert result.complete is True
    assert result.triggered is False
    assert result.retest_timestamp == BREAKOUT_DETECTED_AT
    assert result.reason_codes == ("BREAKOUT_RETEST_SUPPORT_FAILED",)


def test_breakout_retest_applies_atr_distance_and_continuation_buffers() -> None:
    retest = daily_bar(
        BREAKOUT_DETECTED_AT,
        low="104.9",
        high="106",
        close="105",
    )
    exact_boundary = daily_bar(
        BREAKOUT_DETECTED_AT + timedelta(days=1),
        low="101",
        high="109",
        close="108",
    )
    confirmed = daily_bar(
        BREAKOUT_DETECTED_AT + timedelta(days=2),
        low="101",
        high="110",
        close="108.1",
    )

    result = evaluate_breakout_retest_trigger(
        breakout_level(),
        (retest, exact_boundary, confirmed),
        as_of=datetime(2026, 6, 6, tzinfo=UTC),
        atr="10",
        atr_available_at=BREAKOUT_DETECTED_AT,
        continuation_buffer_atr="0.2",
    )

    assert result.triggered is True
    assert result.retest_distance_atr == pytest.approx(Decimal("0.49"))
    assert result.continuation_threshold == Decimal("108.0")
    assert result.confirmation_timestamp == BREAKOUT_DETECTED_AT + timedelta(days=2)


def test_breakout_retest_filters_series_and_future_appends_deterministically() -> None:
    retest = daily_bar(
        BREAKOUT_DETECTED_AT,
        low="102",
        high="104",
        close="103",
    )
    unrelated = daily_bar(
        BREAKOUT_DETECTED_AT,
        low="100",
        high="110",
        close="109",
        provider="bitstamp",
    )
    prior = daily_bar(
        BREAKOUT_TIME,
        low="99",
        high="110",
        close="108",
    )
    future = daily_bar(
        BREAKOUT_DETECTED_AT + timedelta(days=10),
        low="100",
        high="110",
        close="109",
    )

    base = evaluate_breakout_retest_trigger(
        breakout_level(),
        (retest, unrelated, prior),
        as_of=datetime(2026, 6, 4, tzinfo=UTC),
        atr="10",
        atr_available_at=BREAKOUT_DETECTED_AT,
    )
    appended = evaluate_breakout_retest_trigger(
        breakout_level(),
        (future, prior, unrelated, retest),
        as_of=datetime(2026, 6, 4, tzinfo=UTC),
        atr="10",
        atr_available_at=BREAKOUT_DETECTED_AT,
    )

    assert base.as_record() == appended.as_record()


def test_breakout_retest_rejects_invalid_inputs() -> None:
    reclaim = BreakoutReclaimLevel(
        **{
            **breakout_level().__dict__,
            "level_type": "reclaim",
            "level_role": "reclaimed_support",
            "reason_codes": ("RECLAIM_CONFIRMED",),
        }
    )
    as_of = datetime(2026, 6, 4, tzinfo=UTC)

    with pytest.raises(ValueError, match="level_type breakout"):
        evaluate_breakout_retest_trigger(reclaim, (), as_of=as_of)
    with pytest.raises(ValueError, match="available by as_of"):
        evaluate_breakout_retest_trigger(
            breakout_level(detected_at=datetime(2026, 6, 5, tzinfo=UTC)),
            (),
            as_of=as_of,
        )
    with pytest.raises(ValueError, match="supplied together"):
        evaluate_breakout_retest_trigger(
            breakout_level(),
            (),
            as_of=as_of,
            atr="10",
        )
    with pytest.raises(ValueError, match="breakout detection time"):
        evaluate_breakout_retest_trigger(
            breakout_level(),
            (),
            as_of=as_of,
            atr="10",
            atr_available_at=datetime(2026, 6, 4, tzinfo=UTC),
        )
    with pytest.raises(ValueError, match="must be <="):
        evaluate_breakout_retest_trigger(
            breakout_level(),
            (),
            as_of=as_of,
            atr="10",
            atr_available_at=BREAKOUT_DETECTED_AT,
            retest_distance_atr_max="0.25",
            support_breach_atr_max="0.5",
        )
    duplicate = daily_bar(
        BREAKOUT_DETECTED_AT,
        low="102",
        high="104",
        close="103",
    )
    with pytest.raises(ValueError, match="must not contain duplicates"):
        evaluate_breakout_retest_trigger(
            breakout_level(),
            (duplicate, duplicate),
            as_of=as_of,
        )


def test_breakout_retest_integrates_with_btc_092_output() -> None:
    source = WeeklySwingLevel(
        feature_id=WEEKLY_SWING_LEVEL_FEATURE_ID,
        level_type="swing_high",
        level_timestamp=datetime(2026, 5, 4, tzinfo=UTC),
        detected_at=datetime(2026, 6, 1, tzinfo=UTC),
        price=Decimal("100"),
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1w",
        provider="coinbase",
        left_bars=3,
        right_bars=3,
        source_bar_count=7,
    )
    breakout_bar = daily_bar(
        BREAKOUT_TIME,
        low="99",
        high="108",
        close="106",
    )
    levels = detect_breakout_reclaim_levels(
        (source,),
        (breakout_bar,),
        as_of=BREAKOUT_DETECTED_AT,
    )
    retest = daily_bar(
        BREAKOUT_DETECTED_AT,
        low="102",
        high="104",
        close="103",
    )
    continuation = daily_bar(
        BREAKOUT_DETECTED_AT + timedelta(days=1),
        low="101",
        high="106",
        close="105",
    )

    result = evaluate_breakout_retest_trigger(
        levels[0],
        (breakout_bar, retest, continuation),
        as_of=datetime(2026, 6, 5, tzinfo=UTC),
        atr="10",
        atr_available_at=BREAKOUT_DETECTED_AT,
    )

    assert result.triggered is True
    assert result.source_breakout_level is levels[0]
    assert result.reason_codes == ("BREAKOUT_RETEST_CONFIRMED",)
