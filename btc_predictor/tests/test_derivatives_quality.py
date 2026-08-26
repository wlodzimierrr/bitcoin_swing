from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.data import (
    DERIVATIVES_QUALITY_REASON_CODES,
    FundingRate,
    IngestionAuditRecord,
    OpenInterest,
    PerpVolume,
    DerivativesQualityConfig,
    validate_derivatives_quality,
)


def funding_rate(
    observation_time: datetime,
    *,
    exchange: str = "binance",
    funding_rate_: str = "0.0001",
    provider: str = "binance",
) -> FundingRate:
    return FundingRate(
        observation_time=observation_time,
        exchange=exchange,
        symbol="BTCUSDT",
        instrument="BTCUSDT-PERP",
        funding_rate=Decimal(funding_rate_),
        funding_interval_hours=Decimal("8"),
        provider=provider,
        source="provider-api",
        available_at=observation_time + timedelta(minutes=1),
        ingested_at=datetime(2026, 8, 26, tzinfo=UTC),
    )


def open_interest(
    observation_time: datetime,
    *,
    exchange: str = "binance",
    amount: str = "1000",
    unit: str = "contracts",
    provider: str = "binance",
) -> OpenInterest:
    return OpenInterest(
        observation_time=observation_time,
        exchange=exchange,
        symbol="BTCUSDT",
        instrument="BTCUSDT-PERP",
        open_interest=Decimal(amount),
        open_interest_unit=unit,
        provider=provider,
        source="provider-api",
        available_at=observation_time + timedelta(minutes=1),
        ingested_at=datetime(2026, 8, 26, tzinfo=UTC),
    )


def perp_volume(
    observation_time: datetime,
    *,
    exchange: str = "binance",
    amount: str = "100",
    unit: str = "BTC",
    provider: str = "binance",
) -> PerpVolume:
    return PerpVolume(
        observation_time=observation_time,
        exchange=exchange,
        symbol="BTCUSDT",
        timeframe="1h",
        volume=Decimal(amount),
        volume_unit=unit,
        notional_usd=Decimal("10000000"),
        provider=provider,
        source="provider-api",
        available_at=observation_time + timedelta(minutes=1),
        ingested_at=datetime(2026, 8, 26, tzinfo=UTC),
    )


def audit_record(reason_codes: tuple[str, ...]) -> IngestionAuditRecord:
    return IngestionAuditRecord(
        job_run_id="derivatives-quality-20260826T000000Z",
        job_name="btc_derivatives_quality",
        feed_name="btc_derivatives",
        provider="binance",
        source="quality-checker",
        status="partial",
        started_at=datetime(2026, 8, 26, tzinfo=UTC),
        ended_at=datetime(2026, 8, 26, 0, 1, tzinfo=UTC),
        records_fetched=2,
        records_inserted=2,
        reason_codes=reason_codes,
    )


def no_snapshot_config(**overrides) -> DerivativesQualityConfig:
    values = {"required_snapshot_feeds": ()}
    values.update(overrides)
    return DerivativesQualityConfig(**values)


def test_derivatives_quality_reason_codes_are_stable() -> None:
    assert DERIVATIVES_QUALITY_REASON_CODES == (
        "STALE_FUNDING",
        "NEGATIVE_OPEN_INTEREST",
        "PROVIDER_DISCONTINUITY",
        "MISSING_EXCHANGE_SNAPSHOT",
        "UNIT_CHANGE",
    )


def test_derivatives_quality_detects_stale_funding() -> None:
    observed = datetime(2026, 8, 25, 0, tzinfo=UTC)

    report = validate_derivatives_quality(
        [funding_rate(observed)],
        as_of=observed + timedelta(hours=10),
        config=no_snapshot_config(),
    )

    assert report.is_valid is False
    assert report.reason_codes == ("STALE_FUNDING",)
    assert report.issues[0].timestamp == observed
    assert report.issues[0].details["max_staleness_seconds"] == 32400


def test_derivatives_quality_detects_negative_open_interest() -> None:
    observed = datetime(2026, 8, 25, 0, tzinfo=UTC)

    report = validate_derivatives_quality(
        [open_interest(observed, amount="-1")],
        as_of=observed + timedelta(hours=1),
        config=no_snapshot_config(),
    )

    assert report.reason_codes == ("NEGATIVE_OPEN_INTEREST",)
    assert report.issues[0].details["open_interest"] == "-1"


def test_derivatives_quality_detects_provider_discontinuities() -> None:
    start = datetime(2026, 8, 25, 0, tzinfo=UTC)

    report = validate_derivatives_quality(
        [
            perp_volume(start),
            perp_volume(start + timedelta(hours=5)),
        ],
        as_of=start + timedelta(hours=5, minutes=30),
        config=no_snapshot_config(max_provider_gap=timedelta(hours=3)),
    )

    assert report.reason_codes == ("PROVIDER_DISCONTINUITY",)
    assert report.issues[0].details["gap_seconds"] == 18000
    assert report.issues[0].details["max_gap_seconds"] == 10800


def test_derivatives_quality_detects_missing_exchange_snapshots() -> None:
    observed = datetime(2026, 8, 25, 0, tzinfo=UTC)

    report = validate_derivatives_quality(
        [
            funding_rate(observed, exchange="binance"),
            funding_rate(observed, exchange="bybit", provider="bybit"),
            open_interest(observed, exchange="binance"),
            perp_volume(observed, exchange="binance"),
        ],
        as_of=observed + timedelta(hours=1),
        config=DerivativesQualityConfig(expected_exchanges=("binance", "bybit")),
    )

    assert report.reason_codes == ("MISSING_EXCHANGE_SNAPSHOT",)
    assert [(issue.details["exchange"], issue.details["feed"]) for issue in report.issues] == [
        ("bybit", "open_interest"),
        ("bybit", "perp_volume"),
    ]


def test_derivatives_quality_detects_unit_changes() -> None:
    start = datetime(2026, 8, 25, 0, tzinfo=UTC)

    report = validate_derivatives_quality(
        [
            open_interest(start, unit="contracts"),
            open_interest(start + timedelta(hours=1), unit="USD"),
        ],
        as_of=start + timedelta(hours=1, minutes=30),
        config=no_snapshot_config(),
    )

    assert report.reason_codes == ("UNIT_CHANGE",)
    assert report.issues[0].details["previous_unit"] == "contracts"
    assert report.issues[0].details["unit"] == "USD"


def test_derivatives_quality_is_deterministic_for_unsorted_input() -> None:
    start = datetime(2026, 8, 25, 0, tzinfo=UTC)
    rows = (
        perp_volume(start + timedelta(hours=4)),
        open_interest(start, amount="-1"),
        perp_volume(start),
    )

    first = validate_derivatives_quality(
        rows,
        as_of=start + timedelta(hours=4, minutes=30),
        config=no_snapshot_config(max_provider_gap=timedelta(hours=2)),
    )
    second = validate_derivatives_quality(
        tuple(reversed(rows)),
        as_of=start + timedelta(hours=4, minutes=30),
        config=no_snapshot_config(max_provider_gap=timedelta(hours=2)),
    )

    assert first.issues == second.issues
    assert first.reason_codes == ("NEGATIVE_OPEN_INTEREST", "PROVIDER_DISCONTINUITY")


def test_derivatives_quality_rejects_invalid_config() -> None:
    with pytest.raises(ValueError, match="max_provider_gap"):
        DerivativesQualityConfig(required_snapshot_feeds=(), max_provider_gap=timedelta(0))


def test_derivatives_quality_requires_utc_as_of() -> None:
    observed = datetime(2026, 8, 25, 0, tzinfo=UTC)

    with pytest.raises(ValueError, match="as_of must be timezone-aware UTC"):
        validate_derivatives_quality(
            [funding_rate(observed)],
            as_of=datetime(2026, 8, 25, 1),
            config=no_snapshot_config(),
        )


def test_derivatives_quality_reason_codes_can_be_persisted_to_ingestion_audit() -> None:
    observed = datetime(2026, 8, 25, 0, tzinfo=UTC)
    report = validate_derivatives_quality(
        [open_interest(observed, amount="-1")],
        as_of=observed + timedelta(hours=1),
        config=no_snapshot_config(),
    )

    record = audit_record(report.reason_codes).as_record()

    assert record["reason_codes"] == ["NEGATIVE_OPEN_INTEREST"]
