from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.data import OhlcvBar
from btc_predictor.levels import (
    ANCHORED_VWAP_ANCHOR_TYPES,
    ANCHORED_VWAP_FEATURE_ID,
    ANCHORED_VWAP_PRICE_SOURCE_CLOSE,
    ANCHORED_VWAP_PRICE_SOURCE_HLC3,
    ANCHORED_VWAP_PRICE_SOURCES,
    ANCHORED_VWAP_REASON_CODES,
    ANCHOR_BREAKOUT,
    ANCHOR_CAPITULATION_EVENT,
    ANCHOR_MAJOR_SWING_HIGH,
    ANCHOR_MAJOR_SWING_LOW,
    BREAKOUT_LEVEL_TYPE,
    BREAKOUT_RECLAIM_LEVEL_FEATURE_ID,
    BREAKOUT_SUPPORT_ROLE,
    DEFAULT_ANCHORED_VWAP_PRICE_SOURCE,
    MONTHLY_SWING_LEVEL_FEATURE_ID,
    RECLAIM_LEVEL_TYPE,
    RECLAIM_SUPPORT_ROLE,
    WEEKLY_SWING_LEVEL_FEATURE_ID,
    AnchoredVwapAnchor,
    BreakoutReclaimLevel,
    CapitulationEvent,
    MonthlySwingLevel,
    WeeklySwingLevel,
    anchored_vwap_anchor_from_breakout_level,
    anchored_vwap_anchor_from_capitulation_event,
    anchored_vwap_anchor_from_swing_level,
    calculate_anchored_vwap,
    calculate_anchored_vwaps,
)


def daily_bar(
    timestamp: datetime,
    *,
    high: str,
    low: str,
    close: str,
    volume: str = "100",
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
        volume=Decimal(volume),
        provider=provider,
        ingested_at=ingested_at or timestamp + timedelta(days=1),
    )


def weekly_swing_low(
    *,
    detected_at: datetime = datetime(2026, 1, 26, tzinfo=UTC),
) -> WeeklySwingLevel:
    return WeeklySwingLevel(
        feature_id=WEEKLY_SWING_LEVEL_FEATURE_ID,
        level_type="swing_low",
        level_timestamp=datetime(2026, 1, 5, tzinfo=UTC),
        detected_at=detected_at,
        price=Decimal("90"),
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1w",
        provider="coinbase",
        left_bars=3,
        right_bars=3,
        source_bar_count=7,
    )


def monthly_swing_high() -> MonthlySwingLevel:
    return MonthlySwingLevel(
        feature_id=MONTHLY_SWING_LEVEL_FEATURE_ID,
        level_type="swing_high",
        level_timestamp=datetime(2026, 3, 1, tzinfo=UTC),
        detected_at=datetime(2026, 6, 1, tzinfo=UTC),
        price=Decimal("125"),
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1mo",
        provider="coinbase",
        left_bars=2,
        right_bars=2,
        source_bar_count=5,
    )


def breakout_level(*, level_type: str = BREAKOUT_LEVEL_TYPE) -> BreakoutReclaimLevel:
    return BreakoutReclaimLevel(
        feature_id=BREAKOUT_RECLAIM_LEVEL_FEATURE_ID,
        level_type=level_type,
        level_role=BREAKOUT_SUPPORT_ROLE
        if level_type == BREAKOUT_LEVEL_TYPE
        else RECLAIM_SUPPORT_ROLE,
        level_timestamp=datetime(2026, 2, 10, tzinfo=UTC),
        detected_at=datetime(2026, 2, 11, tzinfo=UTC),
        confirmation_timestamp=datetime(2026, 2, 10, tzinfo=UTC),
        price=Decimal("110"),
        source_level_feature_id=WEEKLY_SWING_LEVEL_FEATURE_ID,
        source_level_type="swing_high"
        if level_type == BREAKOUT_LEVEL_TYPE
        else "swing_low",
        source_level_timestamp=datetime(2026, 1, 5, tzinfo=UTC),
        source_level_detected_at=datetime(2026, 1, 26, tzinfo=UTC),
        confirmation_timeframe="1d",
        exchange="coinbase",
        symbol="BTC-USD",
        provider="coinbase",
        close_buffer_fraction=Decimal("0"),
        confirming_close=Decimal("112"),
        confirming_low=Decimal("108"),
        source_bar_count=10,
        reason_codes=("BREAKOUT_CONFIRMED",)
        if level_type == BREAKOUT_LEVEL_TYPE
        else ("RECLAIM_CONFIRMED",),
    )


def test_anchored_vwap_metadata_is_stable() -> None:
    assert ANCHORED_VWAP_FEATURE_ID == "ANCHORED_VWAP"
    assert ANCHOR_MAJOR_SWING_LOW == "major_swing_low"
    assert ANCHOR_MAJOR_SWING_HIGH == "major_swing_high"
    assert ANCHOR_BREAKOUT == "breakout"
    assert ANCHOR_CAPITULATION_EVENT == "capitulation_event"
    assert ANCHORED_VWAP_ANCHOR_TYPES == (
        "major_swing_low",
        "major_swing_high",
        "breakout",
        "capitulation_event",
    )
    assert ANCHORED_VWAP_PRICE_SOURCE_HLC3 == "hlc3"
    assert ANCHORED_VWAP_PRICE_SOURCE_CLOSE == "close"
    assert ANCHORED_VWAP_PRICE_SOURCES == ("hlc3", "close")
    assert DEFAULT_ANCHORED_VWAP_PRICE_SOURCE == "hlc3"
    assert ANCHORED_VWAP_REASON_CODES == (
        "ANCHORED_VWAP_ANCHOR_NOT_DETECTED",
        "ANCHORED_VWAP_INSUFFICIENT_BARS",
        "ANCHORED_VWAP_ZERO_VOLUME",
        "ANCHORED_VWAP_COMPLETE",
    )


def test_creates_anchors_from_supported_sources() -> None:
    swing_low_anchor = anchored_vwap_anchor_from_swing_level(weekly_swing_low())
    swing_high_anchor = anchored_vwap_anchor_from_swing_level(monthly_swing_high())
    breakout_anchor = anchored_vwap_anchor_from_breakout_level(breakout_level())
    capitulation_anchor = anchored_vwap_anchor_from_capitulation_event(
        CapitulationEvent(
            event_timestamp=datetime(2026, 4, 1, tzinfo=UTC),
            detected_at=datetime(2026, 4, 1, 1, tzinfo=UTC),
            price=Decimal("80"),
            exchange="coinbase",
            symbol="BTC-USD",
            provider="coinbase",
            reason_codes=("CAPITULATION_DOWNSIDE_SPIKE",),
        )
    )

    assert swing_low_anchor.anchor_type == "major_swing_low"
    assert swing_low_anchor.anchor_timestamp == datetime(2026, 1, 5, tzinfo=UTC)
    assert swing_low_anchor.source_feature_id == WEEKLY_SWING_LEVEL_FEATURE_ID
    assert swing_low_anchor.source_timeframe == "1w"
    assert swing_high_anchor.anchor_type == "major_swing_high"
    assert swing_high_anchor.source_feature_id == MONTHLY_SWING_LEVEL_FEATURE_ID
    assert breakout_anchor.anchor_type == "breakout"
    assert breakout_anchor.anchor_timestamp == datetime(2026, 2, 10, tzinfo=UTC)
    assert breakout_anchor.source_feature_id == BREAKOUT_RECLAIM_LEVEL_FEATURE_ID
    assert capitulation_anchor.anchor_type == "capitulation_event"
    assert capitulation_anchor.reason_codes == ("CAPITULATION_DOWNSIDE_SPIKE",)


def test_breakout_anchor_rejects_reclaim_level() -> None:
    with pytest.raises(ValueError, match="breakout anchors require a breakout"):
        anchored_vwap_anchor_from_breakout_level(
            breakout_level(level_type=RECLAIM_LEVEL_TYPE),
        )


def test_calculates_hlc3_anchored_vwap_from_point_in_time_bars() -> None:
    anchor = anchored_vwap_anchor_from_swing_level(
        weekly_swing_low(detected_at=datetime(2026, 1, 6, tzinfo=UTC)),
    )

    result = calculate_anchored_vwap(
        anchor,
        (
            daily_bar(datetime(2026, 1, 4, tzinfo=UTC), high="99", low="90", close="96"),
            daily_bar(
                datetime(2026, 1, 5, tzinfo=UTC),
                high="12",
                low="9",
                close="9",
                volume="2",
            ),
            daily_bar(
                datetime(2026, 1, 6, tzinfo=UTC),
                high="21",
                low="19",
                close="20",
                volume="3",
            ),
            daily_bar(
                datetime(2026, 1, 7, tzinfo=UTC),
                high="33",
                low="30",
                close="33",
                volume="5",
            ),
        ),
        as_of=datetime(2026, 1, 7, tzinfo=UTC),
    )

    assert result.complete is True
    assert result.vwap == Decimal("16")
    assert result.bar_count == 2
    assert result.volume_sum == Decimal("5")
    assert result.price_volume_sum == Decimal("80")
    assert result.source_timeframe == "1d"
    assert result.reason_codes == ("ANCHORED_VWAP_COMPLETE",)


def test_can_calculate_vwap_from_close_price_source() -> None:
    anchor = anchored_vwap_anchor_from_breakout_level(breakout_level())

    result = calculate_anchored_vwap(
        anchor,
        (
            daily_bar(
                datetime(2026, 2, 10, tzinfo=UTC),
                high="120",
                low="110",
                close="112",
                volume="2",
            ),
            daily_bar(
                datetime(2026, 2, 11, tzinfo=UTC),
                high="130",
                low="120",
                close="126",
                volume="3",
            ),
        ),
        as_of=datetime(2026, 2, 12, tzinfo=UTC),
        price_source="close",
    )

    assert result.vwap == Decimal("120.4")
    assert result.price_source == "close"


def test_waits_for_anchor_detection_time() -> None:
    result = calculate_anchored_vwap(
        anchored_vwap_anchor_from_swing_level(weekly_swing_low()),
        (
            daily_bar(datetime(2026, 1, 5, tzinfo=UTC), high="12", low="9", close="9"),
        ),
        as_of=datetime(2026, 1, 20, tzinfo=UTC),
    )

    assert result.complete is False
    assert result.vwap is None
    assert result.bar_count == 0
    assert result.reason_codes == ("ANCHORED_VWAP_ANCHOR_NOT_DETECTED",)


def test_excludes_late_ingested_and_future_bars() -> None:
    anchor = anchored_vwap_anchor_from_swing_level(
        weekly_swing_low(detected_at=datetime(2026, 1, 6, tzinfo=UTC)),
    )

    result = calculate_anchored_vwap(
        anchor,
        (
            daily_bar(
                datetime(2026, 1, 5, tzinfo=UTC),
                high="12",
                low="9",
                close="9",
                volume="2",
            ),
            daily_bar(
                datetime(2026, 1, 6, tzinfo=UTC),
                high="21",
                low="19",
                close="20",
                volume="3",
                ingested_at=datetime(2026, 1, 8, tzinfo=UTC),
            ),
            daily_bar(
                datetime(2026, 1, 7, tzinfo=UTC),
                high="33",
                low="30",
                close="33",
                volume="5",
            ),
        ),
        as_of=datetime(2026, 1, 7, tzinfo=UTC),
    )

    assert result.complete is True
    assert result.vwap == Decimal("10")
    assert result.bar_count == 1


def test_reports_missing_or_zero_volume_inputs_explicitly() -> None:
    anchor = anchored_vwap_anchor_from_swing_level(weekly_swing_low())

    missing = calculate_anchored_vwap(
        anchor,
        (),
        as_of=datetime(2026, 1, 27, tzinfo=UTC),
    )
    zero_volume = calculate_anchored_vwap(
        anchor,
        (
            daily_bar(
                datetime(2026, 1, 5, tzinfo=UTC),
                high="12",
                low="9",
                close="9",
                volume="0",
            ),
        ),
        as_of=datetime(2026, 1, 27, tzinfo=UTC),
    )

    assert missing.complete is False
    assert missing.reason_codes == ("ANCHORED_VWAP_INSUFFICIENT_BARS",)
    assert zero_volume.complete is False
    assert zero_volume.bar_count == 1
    assert zero_volume.reason_codes == ("ANCHORED_VWAP_ZERO_VOLUME",)


def test_anchored_vwap_record_is_reconstructable() -> None:
    anchor = anchored_vwap_anchor_from_swing_level(weekly_swing_low())
    result = calculate_anchored_vwap(
        anchor,
        (
            daily_bar(
                datetime(2026, 1, 5, tzinfo=UTC),
                high="12",
                low="9",
                close="9",
                volume="2",
            ),
        ),
        as_of=datetime(2026, 1, 27, tzinfo=UTC),
    )

    assert result.as_record() == {
        "feature_id": "ANCHORED_VWAP",
        "anchor": {
            "anchor_type": "major_swing_low",
            "anchor_timestamp": "2026-01-05T00:00:00+00:00",
            "detected_at": "2026-01-26T00:00:00+00:00",
            "price": "90",
            "exchange": "coinbase",
            "symbol": "BTC-USD",
            "provider": "coinbase",
            "source_feature_id": "WEEKLY_SWING_LEVEL",
            "source_type": "swing_low",
            "source_timestamp": "2026-01-05T00:00:00+00:00",
            "source_detected_at": "2026-01-26T00:00:00+00:00",
            "source_timeframe": "1w",
            "reason_codes": [],
        },
        "anchor_type": "major_swing_low",
        "anchor_timestamp": "2026-01-05T00:00:00+00:00",
        "anchor_detected_at": "2026-01-26T00:00:00+00:00",
        "anchor_price": "90",
        "source_feature_id": "WEEKLY_SWING_LEVEL",
        "source_type": "swing_low",
        "source_timestamp": "2026-01-05T00:00:00+00:00",
        "source_detected_at": "2026-01-26T00:00:00+00:00",
        "source_timeframe": "1d",
        "exchange": "coinbase",
        "symbol": "BTC-USD",
        "provider": "coinbase",
        "as_of": "2026-01-27T00:00:00+00:00",
        "price_source": "hlc3",
        "vwap": "10",
        "bar_count": 1,
        "volume_sum": "2",
        "price_volume_sum": "20",
        "complete": True,
        "reason_codes": ["ANCHORED_VWAP_COMPLETE"],
    }


def test_calculates_many_anchored_vwaps_deterministically() -> None:
    results = calculate_anchored_vwaps(
        (
            anchored_vwap_anchor_from_breakout_level(breakout_level()),
            anchored_vwap_anchor_from_swing_level(weekly_swing_low()),
        ),
        (
            daily_bar(datetime(2026, 1, 5, tzinfo=UTC), high="12", low="9", close="9"),
            daily_bar(datetime(2026, 2, 10, tzinfo=UTC), high="120", low="110", close="112"),
        ),
        as_of=datetime(2026, 2, 12, tzinfo=UTC),
    )

    assert [result.anchor.anchor_type for result in results] == [
        "major_swing_low",
        "breakout",
    ]


def test_invalid_inputs_fail_fast() -> None:
    anchor = anchored_vwap_anchor_from_swing_level(weekly_swing_low())

    with pytest.raises(ValueError, match="as_of must be timezone-aware UTC"):
        calculate_anchored_vwap(anchor, (), as_of=datetime(2026, 1, 27))

    with pytest.raises(ValueError, match="price_source"):
        calculate_anchored_vwap(
            anchor,
            (),
            as_of=datetime(2026, 1, 27, tzinfo=UTC),
            price_source="ohlc4",
        )

    with pytest.raises(ValueError, match="bar volume"):
        calculate_anchored_vwap(
            anchor,
            (
                daily_bar(
                    datetime(2026, 1, 5, tzinfo=UTC),
                    high="12",
                    low="9",
                    close="9",
                    volume="-1",
                ),
            ),
            as_of=datetime(2026, 1, 27, tzinfo=UTC),
        )

    invalid_anchor = AnchoredVwapAnchor(
        anchor_type="unsupported",
        anchor_timestamp=datetime(2026, 1, 5, tzinfo=UTC),
        detected_at=datetime(2026, 1, 6, tzinfo=UTC),
        price=Decimal("90"),
        exchange="coinbase",
        symbol="BTC-USD",
        provider="coinbase",
        source_feature_id=WEEKLY_SWING_LEVEL_FEATURE_ID,
        source_type="swing_low",
        source_timestamp=datetime(2026, 1, 5, tzinfo=UTC),
        source_detected_at=datetime(2026, 1, 6, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="anchor_type"):
        calculate_anchored_vwap(
            invalid_anchor,
            (),
            as_of=datetime(2026, 1, 27, tzinfo=UTC),
        )
