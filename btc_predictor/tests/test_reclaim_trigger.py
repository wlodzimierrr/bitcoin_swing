from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.data import OhlcvBar
from btc_predictor.levels import (
    BREAKOUT_RECLAIM_LEVEL_FEATURE_ID,
    MONTHLY_SWING_LEVEL_FEATURE_ID,
    BreakoutReclaimLevel,
    MonthlySwingLevel,
    detect_breakout_reclaim_levels,
)
from btc_predictor.signals import (
    DEFAULT_RECLAIM_CLOSE_BUFFER_FRACTION,
    DEFAULT_RECLAIM_CONFIRMATION_BARS,
    DEFAULT_RECLAIM_HOLD_BUFFER_FRACTION,
    RECLAIM_TRIGGER_FEATURE_ID,
    RECLAIM_TRIGGER_REASON_CODES,
    RECLAIM_TRIGGER_TYPE,
    evaluate_reclaim_trigger,
)


RECLAIM_TIME = datetime(2026, 6, 2, tzinfo=UTC)
RECLAIM_DETECTED_AT = datetime(2026, 6, 3, tzinfo=UTC)


def reclaim_level(*, detected_at: datetime = RECLAIM_DETECTED_AT) -> BreakoutReclaimLevel:
    return BreakoutReclaimLevel(
        feature_id=BREAKOUT_RECLAIM_LEVEL_FEATURE_ID,
        level_type="reclaim",
        level_role="reclaimed_support",
        level_timestamp=RECLAIM_TIME,
        detected_at=detected_at,
        confirmation_timestamp=RECLAIM_TIME,
        price=Decimal("100"),
        source_level_feature_id=MONTHLY_SWING_LEVEL_FEATURE_ID,
        source_level_type="swing_low",
        source_level_timestamp=datetime(2026, 3, 1, tzinfo=UTC),
        source_level_detected_at=datetime(2026, 6, 1, tzinfo=UTC),
        confirmation_timeframe="1d",
        exchange="coinbase",
        symbol="BTC-USD",
        provider="coinbase",
        close_buffer_fraction=Decimal("0"),
        confirming_close=Decimal("101"),
        confirming_low=Decimal("99"),
        source_bar_count=1,
        reason_codes=("RECLAIM_CONFIRMED",),
    )


def daily_bar(
    timestamp: datetime,
    *,
    low: str = "100",
    close: str = "102",
    ingested_at: datetime | None = None,
    provider: str = "coinbase",
    timeframe: str = "1d",
) -> OhlcvBar:
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe=timeframe,
        open=Decimal("101"),
        high=max(Decimal("103"), Decimal(close), Decimal(low)),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("100"),
        provider=provider,
        ingested_at=ingested_at or timestamp + timedelta(days=1),
    )


def test_reclaim_trigger_metadata_is_stable() -> None:
    assert RECLAIM_TRIGGER_FEATURE_ID == "ENTRY_TRIGGER_RECLAIM"
    assert RECLAIM_TRIGGER_TYPE == "RECLAIM"
    assert DEFAULT_RECLAIM_CONFIRMATION_BARS == 1
    assert DEFAULT_RECLAIM_HOLD_BUFFER_FRACTION == Decimal("0")
    assert DEFAULT_RECLAIM_CLOSE_BUFFER_FRACTION == Decimal("0")
    assert RECLAIM_TRIGGER_REASON_CODES == (
        "RECLAIM_TRIGGER_CONFIRMATION_PENDING",
        "RECLAIM_TRIGGER_LEVEL_NOT_HELD",
        "RECLAIM_TRIGGER_CLOSE_NOT_CONFIRMED",
        "RECLAIM_TRIGGER_CONFIRMED",
    )


def test_reclaim_trigger_confirms_first_closed_follow_up_bar() -> None:
    config = load_strategy_config()
    result = evaluate_reclaim_trigger(
        reclaim_level(),
        (daily_bar(RECLAIM_DETECTED_AT),),
        as_of=datetime(2026, 6, 4, tzinfo=UTC),
        config_metadata=config.run_metadata(),
    )

    assert result.triggered is True
    assert result.complete is True
    assert result.confirmation_timestamp == RECLAIM_DETECTED_AT
    assert result.detected_at == datetime(2026, 6, 4, tzinfo=UTC)
    assert result.reason_codes == ("RECLAIM_TRIGGER_CONFIRMED",)
    assert result.source_bar_count == 1
    assert result.as_record() == {
        "feature_id": "ENTRY_TRIGGER_RECLAIM",
        "trigger_type": "RECLAIM",
        "evaluated_at": "2026-06-04T00:00:00+00:00",
        "triggered": True,
        "complete": True,
        "reason_code": "RECLAIM_TRIGGER_CONFIRMED",
        "source_reclaim_level": reclaim_level().as_record(),
        "confirmation_bars_required": 1,
        "hold_buffer_fraction": "0",
        "close_buffer_fraction": "0",
        "hold_threshold": "100",
        "close_threshold": "100",
        "confirmation_bar_timestamps": ["2026-06-03T00:00:00+00:00"],
        "confirmation_lows": ["100"],
        "confirmation_closes": ["102"],
        "confirmation_timestamp": "2026-06-03T00:00:00+00:00",
        "detected_at": "2026-06-04T00:00:00+00:00",
        "source_bar_count": 1,
        "config_metadata": config.run_metadata(),
        "reason_codes": ["RECLAIM_TRIGGER_CONFIRMED"],
    }


def test_reclaim_trigger_waits_for_bar_close_and_ingestion() -> None:
    follow_up = daily_bar(
        RECLAIM_DETECTED_AT,
        ingested_at=datetime(2026, 6, 5, tzinfo=UTC),
    )

    pending_before_close = evaluate_reclaim_trigger(
        reclaim_level(),
        (follow_up,),
        as_of=datetime(2026, 6, 3, 12, tzinfo=UTC),
    )
    pending_before_ingestion = evaluate_reclaim_trigger(
        reclaim_level(),
        (follow_up,),
        as_of=datetime(2026, 6, 4, tzinfo=UTC),
    )

    for result in (pending_before_close, pending_before_ingestion):
        assert result.triggered is False
        assert result.complete is False
        assert result.source_bar_count == 0
        assert result.reason_codes == ("RECLAIM_TRIGGER_CONFIRMATION_PENDING",)
        assert result.confirmation_bar_timestamps == ()
        assert result.detected_at is None


@pytest.mark.parametrize(
    ("low", "close", "expected_reasons"),
    [
        ("99", "102", ("RECLAIM_TRIGGER_LEVEL_NOT_HELD",)),
        ("100", "100", ("RECLAIM_TRIGGER_CLOSE_NOT_CONFIRMED",)),
        (
            "99",
            "100",
            (
                "RECLAIM_TRIGGER_LEVEL_NOT_HELD",
                "RECLAIM_TRIGGER_CLOSE_NOT_CONFIRMED",
            ),
        ),
    ],
)
def test_reclaim_trigger_reports_failed_confirmation_rules(
    low: str,
    close: str,
    expected_reasons: tuple[str, ...],
) -> None:
    result = evaluate_reclaim_trigger(
        reclaim_level(),
        (daily_bar(RECLAIM_DETECTED_AT, low=low, close=close),),
        as_of=datetime(2026, 6, 4, tzinfo=UTC),
    )

    assert result.triggered is False
    assert result.complete is True
    assert result.reason_codes == expected_reasons
    assert result.confirmation_timestamp is None
    assert result.detected_at is None


def test_reclaim_trigger_applies_configured_buffers_across_required_bars() -> None:
    result = evaluate_reclaim_trigger(
        reclaim_level(),
        (
            daily_bar(RECLAIM_DETECTED_AT, low="99", close="102.1"),
            daily_bar(RECLAIM_DETECTED_AT + timedelta(days=1), low="99.5", close="103"),
        ),
        as_of=datetime(2026, 6, 5, tzinfo=UTC),
        confirmation_bars=2,
        hold_buffer_fraction=Decimal("0.01"),
        close_buffer_fraction=Decimal("0.02"),
    )

    assert result.triggered is True
    assert result.hold_threshold == Decimal("99.00")
    assert result.close_threshold == Decimal("102.00")
    assert result.confirmation_bar_timestamps == (
        RECLAIM_DETECTED_AT,
        RECLAIM_DETECTED_AT + timedelta(days=1),
    )


def test_reclaim_trigger_uses_first_confirmation_window_without_later_rescue() -> None:
    failed_first = daily_bar(RECLAIM_DETECTED_AT, low="98", close="101")
    successful_later = daily_bar(
        RECLAIM_DETECTED_AT + timedelta(days=1),
        low="100",
        close="103",
    )

    result = evaluate_reclaim_trigger(
        reclaim_level(),
        (successful_later, failed_first),
        as_of=datetime(2026, 6, 5, tzinfo=UTC),
    )

    assert result.triggered is False
    assert result.complete is True
    assert result.confirmation_bar_timestamps == (RECLAIM_DETECTED_AT,)
    assert result.reason_codes == ("RECLAIM_TRIGGER_LEVEL_NOT_HELD",)
    assert result.source_bar_count == 2


def test_reclaim_trigger_filters_series_and_preserves_past_output() -> None:
    valid = daily_bar(RECLAIM_DETECTED_AT)
    unrelated = daily_bar(RECLAIM_DETECTED_AT, provider="bitstamp")
    prior = daily_bar(RECLAIM_TIME)
    future = daily_bar(RECLAIM_DETECTED_AT + timedelta(days=10))

    base = evaluate_reclaim_trigger(
        reclaim_level(),
        (valid, unrelated, prior),
        as_of=datetime(2026, 6, 4, tzinfo=UTC),
    )
    appended = evaluate_reclaim_trigger(
        reclaim_level(),
        (future, prior, unrelated, valid),
        as_of=datetime(2026, 6, 4, tzinfo=UTC),
    )

    assert base.as_record() == appended.as_record()


def test_reclaim_trigger_rejects_invalid_inputs() -> None:
    breakout = BreakoutReclaimLevel(
        **{
            **reclaim_level().__dict__,
            "level_type": "breakout",
            "level_role": "support_after_breakout",
            "reason_codes": ("BREAKOUT_CONFIRMED",),
        }
    )

    with pytest.raises(ValueError, match="level_type reclaim"):
        evaluate_reclaim_trigger(
            breakout,
            (),
            as_of=datetime(2026, 6, 4, tzinfo=UTC),
        )
    with pytest.raises(ValueError, match="available by as_of"):
        evaluate_reclaim_trigger(
            reclaim_level(detected_at=datetime(2026, 6, 5, tzinfo=UTC)),
            (),
            as_of=datetime(2026, 6, 4, tzinfo=UTC),
        )
    with pytest.raises(ValueError, match="positive integer"):
        evaluate_reclaim_trigger(
            reclaim_level(),
            (),
            as_of=datetime(2026, 6, 4, tzinfo=UTC),
            confirmation_bars=0,
        )
    with pytest.raises(ValueError, match="between 0 and 1"):
        evaluate_reclaim_trigger(
            reclaim_level(),
            (),
            as_of=datetime(2026, 6, 4, tzinfo=UTC),
            hold_buffer_fraction=Decimal("1.1"),
        )
    duplicate = daily_bar(RECLAIM_DETECTED_AT)
    with pytest.raises(ValueError, match="must not contain duplicates"):
        evaluate_reclaim_trigger(
            reclaim_level(),
            (duplicate, duplicate),
            as_of=datetime(2026, 6, 4, tzinfo=UTC),
        )


def test_reclaim_trigger_integrates_with_btc_092_output() -> None:
    source = MonthlySwingLevel(
        feature_id=MONTHLY_SWING_LEVEL_FEATURE_ID,
        level_type="swing_low",
        level_timestamp=datetime(2026, 3, 1, tzinfo=UTC),
        detected_at=datetime(2026, 6, 1, tzinfo=UTC),
        price=Decimal("100"),
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1mo",
        provider="coinbase",
        left_bars=2,
        right_bars=2,
        source_bar_count=5,
    )
    reclaim_bar = daily_bar(RECLAIM_TIME, low="99", close="101")
    levels = detect_breakout_reclaim_levels(
        (source,),
        (reclaim_bar,),
        as_of=RECLAIM_DETECTED_AT,
    )

    result = evaluate_reclaim_trigger(
        levels[0],
        (reclaim_bar, daily_bar(RECLAIM_DETECTED_AT, low="100", close="102")),
        as_of=datetime(2026, 6, 4, tzinfo=UTC),
    )

    assert result.triggered is True
    assert result.source_reclaim_level is levels[0]
    assert result.reason_codes == ("RECLAIM_TRIGGER_CONFIRMED",)
