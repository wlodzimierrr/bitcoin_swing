from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.data import (
    OHLCV_QUALITY_REASON_CODES,
    IngestionAuditRecord,
    OhlcvBar,
    OhlcvQualityConfig,
    validate_ohlcv_quality,
)


def hourly_bar(
    timestamp: datetime,
    *,
    open_: str = "100",
    high: str = "110",
    low: str = "90",
    close: str = "105",
    volume: str = "10",
    provider: str = "coinbase",
) -> OhlcvBar:
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1h",
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal(volume),
        provider=provider,
        ingested_at=datetime(2026, 8, 26, tzinfo=UTC),
    )


def audit_record(reason_codes: tuple[str, ...]) -> IngestionAuditRecord:
    return IngestionAuditRecord(
        job_run_id="ohlcv-quality-20260826T000000Z",
        job_name="btc_ohlcv_quality",
        feed_name="btc_ohlcv",
        provider="coinbase",
        source="quality-checker",
        status="partial",
        started_at=datetime(2026, 8, 26, tzinfo=UTC),
        ended_at=datetime(2026, 8, 26, 0, 1, tzinfo=UTC),
        records_fetched=2,
        records_inserted=2,
        reason_codes=reason_codes,
    )


def test_ohlcv_quality_reason_codes_are_stable() -> None:
    assert OHLCV_QUALITY_REASON_CODES == (
        "DUPLICATE_BAR",
        "IMPOSSIBLE_OHLC",
        "MISSING_PERIOD",
        "STALE_DATA",
        "EXTREME_MALFORMED_VALUE",
    )


def test_ohlcv_quality_detects_duplicate_bars() -> None:
    timestamp = datetime(2026, 8, 26, tzinfo=UTC)

    report = validate_ohlcv_quality(
        [hourly_bar(timestamp), hourly_bar(timestamp)],
        start=timestamp,
        end=timestamp,
        timeframe="1h",
        as_of=timestamp + timedelta(hours=1),
    )

    assert report.is_valid is False
    assert report.reason_codes == ("DUPLICATE_BAR",)
    assert report.issues[0].details["key"] == (
        timestamp,
        "coinbase",
        "BTC-USD",
        "1h",
        "coinbase",
    )


def test_ohlcv_quality_detects_impossible_ohlc() -> None:
    timestamp = datetime(2026, 8, 26, tzinfo=UTC)

    report = validate_ohlcv_quality(
        [hourly_bar(timestamp, high="100", low="90", close="105", volume="-1")],
        start=timestamp,
        end=timestamp,
        timeframe="1h",
        as_of=timestamp + timedelta(hours=1),
    )

    assert report.reason_codes == ("IMPOSSIBLE_OHLC",)
    assert report.issues[0].details == {
        "bad_prices": False,
        "bad_ohlc_order": True,
        "bad_volume": True,
    }


def test_ohlcv_quality_detects_missing_periods() -> None:
    start = datetime(2026, 8, 26, 0, tzinfo=UTC)
    end = datetime(2026, 8, 26, 2, tzinfo=UTC)

    report = validate_ohlcv_quality(
        [hourly_bar(start), hourly_bar(end)],
        start=start,
        end=end,
        timeframe="1h",
        as_of=end + timedelta(minutes=30),
    )

    assert report.reason_codes == ("MISSING_PERIOD",)
    assert report.issues[0].timestamp == datetime(2026, 8, 26, 1, tzinfo=UTC)


def test_ohlcv_quality_detects_stale_data() -> None:
    latest = datetime(2026, 8, 26, 0, tzinfo=UTC)

    report = validate_ohlcv_quality(
        [hourly_bar(latest)],
        start=latest,
        end=latest,
        timeframe="1h",
        as_of=latest + timedelta(hours=3),
    )

    assert report.reason_codes == ("STALE_DATA",)
    assert report.issues[0].details["max_staleness_seconds"] == 7200


def test_ohlcv_quality_detects_extreme_malformed_values() -> None:
    start = datetime(2026, 8, 26, 0, tzinfo=UTC)

    report = validate_ohlcv_quality(
        [
            hourly_bar(start, close="100"),
            hourly_bar(start + timedelta(hours=1), open_="180", high="185", low="175", close="180"),
        ],
        start=start,
        end=start + timedelta(hours=1),
        timeframe="1h",
        as_of=start + timedelta(hours=1, minutes=30),
        config=OhlcvQualityConfig(max_close_change_fraction=Decimal("0.25")),
    )

    assert report.reason_codes == ("EXTREME_MALFORMED_VALUE",)
    assert report.issues[0].timestamp == start + timedelta(hours=1)
    assert report.issues[0].details["close_change_fraction"] == "0.8"


def test_ohlcv_quality_is_deterministic_for_unsorted_input() -> None:
    start = datetime(2026, 8, 26, 0, tzinfo=UTC)
    bars = (
        hourly_bar(start + timedelta(hours=2), provider="kraken"),
        hourly_bar(start, provider="coinbase"),
        hourly_bar(start + timedelta(hours=2), provider="coinbase"),
    )

    first = validate_ohlcv_quality(
        bars,
        start=start,
        end=start + timedelta(hours=2),
        timeframe="1h",
        as_of=start + timedelta(hours=2, minutes=30),
    )
    second = validate_ohlcv_quality(
        tuple(reversed(bars)),
        start=start,
        end=start + timedelta(hours=2),
        timeframe="1h",
        as_of=start + timedelta(hours=2, minutes=30),
    )

    assert first.issues == second.issues
    assert first.reason_codes == ("MISSING_PERIOD",)


def test_ohlcv_quality_rejects_invalid_config() -> None:
    with pytest.raises(ValueError, match="max_close_change_fraction"):
        OhlcvQualityConfig(max_close_change_fraction=Decimal("0"))


def test_ohlcv_quality_requires_utc_cutoffs() -> None:
    timestamp = datetime(2026, 8, 26, tzinfo=UTC)

    with pytest.raises(ValueError, match="start must be timezone-aware UTC"):
        validate_ohlcv_quality(
            [hourly_bar(timestamp)],
            start=datetime(2026, 8, 26),
            end=timestamp,
            timeframe="1h",
            as_of=timestamp,
        )


def test_ohlcv_quality_reason_codes_can_be_persisted_to_ingestion_audit() -> None:
    start = datetime(2026, 8, 26, 0, tzinfo=UTC)
    report = validate_ohlcv_quality(
        [hourly_bar(start), hourly_bar(start + timedelta(hours=2))],
        start=start,
        end=start + timedelta(hours=2),
        timeframe="1h",
        as_of=start + timedelta(hours=2, minutes=30),
    )

    record = audit_record(report.reason_codes).as_record()

    assert record["reason_codes"] == ["MISSING_PERIOD"]
