from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.data import FundingRate
from btc_predictor.features import (
    DEFAULT_FUNDING_AVERAGE_WINDOW_DAYS,
    DEFAULT_FUNDING_HEALTH_PREFERRED_ZSCORE,
    DEFAULT_FUNDING_HEALTH_ZSCORE_WIDTH,
    DEFAULT_FUNDING_MIN_ZSCORE_OBSERVATIONS,
    DEFAULT_FUNDING_ZSCORE_WINDOW_DAYS,
    FUNDING_7D_AVG_FEATURE_ID,
    FUNDING_HEALTH_FEATURE_ID,
    FUNDING_HEALTH_REASON_CODES,
    FUNDING_ZSCORE_FEATURE_ID,
    funding_health,
)


def funding_rate(
    observation_time: datetime,
    *,
    funding_rate_value: str,
    available_at: datetime | None = None,
    exchange: str = "binance",
) -> FundingRate:
    return FundingRate(
        observation_time=observation_time,
        exchange=exchange,
        symbol="BTCUSDT",
        instrument="BTCUSDT-PERP",
        funding_rate=Decimal(funding_rate_value),
        funding_interval_hours=Decimal("8"),
        provider=exchange,
        source=f"{exchange}-api",
        available_at=available_at or observation_time + timedelta(minutes=1),
        ingested_at=observation_time + timedelta(minutes=2),
    )


def daily_funding_rates(values: tuple[str, ...]) -> tuple[FundingRate, ...]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return tuple(
        funding_rate(start + timedelta(days=index), funding_rate_value=value)
        for index, value in enumerate(values)
    )


def test_funding_health_metadata_is_stable() -> None:
    assert FUNDING_HEALTH_FEATURE_ID == "FUNDING_HEALTH"
    assert FUNDING_7D_AVG_FEATURE_ID == "FUNDING_7D_AVG"
    assert FUNDING_ZSCORE_FEATURE_ID == "FUNDING_ZSCORE_180D"
    assert DEFAULT_FUNDING_AVERAGE_WINDOW_DAYS == 7
    assert DEFAULT_FUNDING_ZSCORE_WINDOW_DAYS == 180
    assert DEFAULT_FUNDING_MIN_ZSCORE_OBSERVATIONS == 30
    assert DEFAULT_FUNDING_HEALTH_PREFERRED_ZSCORE == Decimal("0.25")
    assert DEFAULT_FUNDING_HEALTH_ZSCORE_WIDTH == Decimal("1.25")
    assert FUNDING_HEALTH_REASON_CODES == (
        "FUNDING_RATE_INPUT_MISSING",
        "FUNDING_HEALTH_INSUFFICIENT_HISTORY",
        "FUNDING_HEALTH_ZERO_VARIANCE",
    )


def test_funding_health_uses_seven_day_average_and_rolling_zscore() -> None:
    rows = daily_funding_rates(
        ("0.01", "0.02", "0.03", "0.04", "0.05", "0.06", "0.07", "0.08", "0.09", "0.10")
    )

    result = funding_health(
        tuple(reversed(rows)),
        as_of=datetime(2026, 1, 10, 1, tzinfo=UTC),
        min_zscore_observations=3,
    )

    assert result.complete is True
    assert result.feature_id == "FUNDING_HEALTH"
    assert result.observation_time == datetime(2026, 1, 10, tzinfo=UTC)
    assert result.average_window_days == 7
    assert result.zscore_window_days == 180
    assert result.funding_7d_avg == Decimal("0.07")
    assert result.funding_zscore is not None
    assert result.funding_zscore.quantize(Decimal("0.000001")) == Decimal("2.480154")
    assert result.health_score is not None
    assert result.health_score.quantize(Decimal("0.001")) == Decimal("20.361")
    assert result.average_window_record_count == 7
    assert result.history_observation_count == 9
    assert result.source_record_count == 10
    assert result.reason_codes == ()


def test_funding_health_filters_unavailable_future_rows() -> None:
    rows = daily_funding_rates(
        ("0.01", "0.02", "0.03", "0.04", "0.05", "0.06", "0.07", "0.08", "0.09", "0.10")
    )
    unavailable_revision = funding_rate(
        datetime(2026, 1, 10, tzinfo=UTC),
        funding_rate_value="1.00",
        available_at=datetime(2026, 1, 11, tzinfo=UTC),
        exchange="okx",
    )

    baseline = funding_health(
        rows,
        as_of=datetime(2026, 1, 10, 1, tzinfo=UTC),
        min_zscore_observations=3,
    ).as_record()
    with_future = funding_health(
        (*rows, unavailable_revision),
        as_of=datetime(2026, 1, 10, 1, tzinfo=UTC),
        min_zscore_observations=3,
    ).as_record()

    assert with_future == baseline


def test_funding_health_averages_multiple_exchange_rows_per_timestamp() -> None:
    rows = (
        funding_rate(datetime(2026, 1, 1, tzinfo=UTC), funding_rate_value="0.01"),
        funding_rate(datetime(2026, 1, 1, tzinfo=UTC), funding_rate_value="0.03", exchange="okx"),
    )

    result = funding_health(
        rows,
        as_of=datetime(2026, 1, 1, 1, tzinfo=UTC),
        average_window_days=1,
        min_zscore_observations=1,
    )

    assert result.funding_7d_avg == Decimal("0.02")
    assert result.average_window_record_count == 2
    assert result.source_record_count == 2


def test_funding_health_reports_missing_input_without_zero_fill() -> None:
    result = funding_health((), as_of=datetime(2026, 1, 10, tzinfo=UTC))

    assert result.complete is False
    assert result.funding_7d_avg is None
    assert result.funding_zscore is None
    assert result.health_score is None
    assert result.reason_codes == ("FUNDING_RATE_INPUT_MISSING",)


def test_funding_health_reports_insufficient_history() -> None:
    rows = daily_funding_rates(("0.01", "0.02"))

    result = funding_health(
        rows,
        as_of=datetime(2026, 1, 2, 1, tzinfo=UTC),
        min_zscore_observations=3,
    )

    assert result.complete is False
    assert result.funding_7d_avg == Decimal("0.015")
    assert result.funding_zscore is None
    assert result.health_score is None
    assert result.history_observation_count == 1
    assert result.reason_codes == ("FUNDING_HEALTH_INSUFFICIENT_HISTORY",)


def test_funding_health_reports_zero_variance_history() -> None:
    rows = daily_funding_rates(("0.01", "0.01", "0.01", "0.01"))

    result = funding_health(
        rows,
        as_of=datetime(2026, 1, 4, 1, tzinfo=UTC),
        min_zscore_observations=3,
    )

    assert result.complete is False
    assert result.funding_7d_avg == Decimal("0.01")
    assert result.funding_zscore is None
    assert result.health_score is None
    assert result.reason_codes == ("FUNDING_HEALTH_ZERO_VARIANCE",)


def test_funding_health_exposes_persistable_payload() -> None:
    rows = daily_funding_rates(
        ("0.01", "0.02", "0.03", "0.04", "0.05", "0.06", "0.07", "0.08", "0.09", "0.10")
    )

    result = funding_health(
        rows,
        as_of=datetime(2026, 1, 10, 1, tzinfo=UTC),
        min_zscore_observations=3,
    )

    record = result.as_record()
    assert record["feature_id"] == "FUNDING_HEALTH"
    assert record["observation_time"] == "2026-01-10T00:00:00+00:00"
    assert record["average_feature_id"] == "FUNDING_7D_AVG"
    assert record["zscore_feature_id"] == "FUNDING_ZSCORE_180D"
    assert record["average_window_days"] == 7
    assert record["zscore_window_days"] == 180
    assert record["min_zscore_observations"] == 3
    assert record["preferred_zscore"] == "0.25"
    assert record["zscore_width"] == "1.25"
    assert record["funding_7d_avg"] == "0.07"
    assert record["funding_zscore"] == str(result.funding_zscore)
    assert record["health_score"] == str(result.health_score)
    assert record["average_window_record_count"] == 7
    assert record["history_observation_count"] == 9
    assert record["source_record_count"] == 10
    assert record["complete"] is True
    assert record["reason_codes"] == []


def test_funding_health_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="as_of must be timezone-aware UTC"):
        funding_health((), as_of=datetime(2026, 1, 10))

    with pytest.raises(ValueError, match="average_window_days"):
        funding_health((), as_of=datetime(2026, 1, 10, tzinfo=UTC), average_window_days=0)

    with pytest.raises(ValueError, match="zscore_width"):
        funding_health(
            (),
            as_of=datetime(2026, 1, 10, tzinfo=UTC),
            zscore_width=Decimal("0"),
        )
