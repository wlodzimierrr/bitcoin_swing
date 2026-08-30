from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.data import FundingRate, FuturesBasis, OpenInterest
from btc_predictor.features import (
    CROWDING_FLAG_EFFECTS,
    CROWDING_FLAG_FEATURE_ID,
    CROWDING_FLAG_REASON_CODES,
    DEFAULT_CROWDING_BASIS_ZSCORE_MIN,
    DEFAULT_CROWDING_ENTRY_QUALITY_PENALTY,
    DEFAULT_CROWDING_FUNDING_ZSCORE_MIN,
    DEFAULT_CROWDING_OI_INTENSITY_PERCENTILE_MIN,
    DEFAULT_FUNDING_AVERAGE_WINDOW_DAYS,
    DEFAULT_FUNDING_HEALTH_PREFERRED_ZSCORE,
    DEFAULT_FUNDING_HEALTH_ZSCORE_WIDTH,
    DEFAULT_FUNDING_MIN_ZSCORE_OBSERVATIONS,
    DEFAULT_FUNDING_ZSCORE_WINDOW_DAYS,
    DEFAULT_FUTURES_BASIS_HEALTH_PREFERRED_ZSCORE,
    DEFAULT_FUTURES_BASIS_HEALTH_ZSCORE_WIDTH,
    DEFAULT_FUTURES_BASIS_MIN_ZSCORE_OBSERVATIONS,
    DEFAULT_FUTURES_BASIS_ZSCORE_WINDOW_DAYS,
    DEFAULT_OI_GROWTH_HEALTH_PREFERRED_ZSCORE,
    DEFAULT_OI_GROWTH_HEALTH_ZSCORE_WIDTH,
    DEFAULT_OI_GROWTH_MIN_ZSCORE_OBSERVATIONS,
    DEFAULT_OI_GROWTH_WINDOW_DAYS,
    DEFAULT_OI_GROWTH_ZSCORE_WINDOW_DAYS,
    DEFAULT_OI_INTENSITY_MIN_PERCENTILE_OBSERVATIONS,
    DEFAULT_OI_INTENSITY_PERCENTILE_WINDOW_DAYS,
    DEFAULT_POSITIONING_SCORE_WEIGHTS,
    FUNDING_7D_AVG_FEATURE_ID,
    FUNDING_HEALTH_FEATURE_ID,
    FUNDING_HEALTH_REASON_CODES,
    FUNDING_ZSCORE_FEATURE_ID,
    FUTURES_BASIS_AVG_FEATURE_ID,
    FUTURES_BASIS_HEALTH_FEATURE_ID,
    FUTURES_BASIS_HEALTH_REASON_CODES,
    FUTURES_BASIS_ZSCORE_FEATURE_ID,
    OI_GROWTH_FEATURE_ID,
    OI_GROWTH_HEALTH_FEATURE_ID,
    OI_GROWTH_HEALTH_REASON_CODES,
    OI_GROWTH_ZSCORE_FEATURE_ID,
    OI_INTENSITY_FEATURE_ID,
    OI_INTENSITY_PERCENTILE_FEATURE_ID,
    OI_INTENSITY_REASON_CODES,
    POSITIONING_SCORE_COMPONENT_IDS,
    POSITIONING_SCORE_FEATURE_ID,
    POSITIONING_SCORE_REASON_CODES,
    CrowdingFlagInput,
    MarketCapObservation,
    PositioningScoreInput,
    calculate_crowding_flag,
    calculate_positioning_score,
    futures_basis_health,
    funding_health,
    open_interest_growth_health,
    open_interest_intensity,
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


def futures_basis(
    observation_time: datetime,
    *,
    basis_rate: str,
    annualized_basis_rate: str,
    available_at: datetime | None = None,
    exchange: str = "binance",
) -> FuturesBasis:
    return FuturesBasis(
        observation_time=observation_time,
        exchange=exchange,
        symbol="BTCUSDT",
        instrument="BTCUSDT-QUARTERLY",
        expiry=observation_time + timedelta(days=90),
        basis_rate=Decimal(basis_rate),
        annualized_basis_rate=Decimal(annualized_basis_rate),
        provider=exchange,
        source=f"{exchange}-api",
        available_at=available_at or observation_time + timedelta(minutes=1),
        ingested_at=observation_time + timedelta(minutes=2),
    )


def daily_futures_basis(
    values: tuple[tuple[str, str], ...],
) -> tuple[FuturesBasis, ...]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return tuple(
        futures_basis(
            start + timedelta(days=index),
            basis_rate=basis_rate,
            annualized_basis_rate=annualized_basis_rate,
        )
        for index, (basis_rate, annualized_basis_rate) in enumerate(values)
    )


def open_interest(
    observation_time: datetime,
    *,
    open_interest_value: str,
    available_at: datetime | None = None,
    exchange: str = "binance",
    unit: str = "USD",
) -> OpenInterest:
    return OpenInterest(
        observation_time=observation_time,
        exchange=exchange,
        symbol="BTCUSDT",
        instrument="BTCUSDT-PERP",
        open_interest=Decimal(open_interest_value),
        open_interest_unit=unit,
        provider=exchange,
        source=f"{exchange}-api",
        available_at=available_at or observation_time + timedelta(minutes=1),
        ingested_at=observation_time + timedelta(minutes=2),
    )


def daily_open_interest(values: tuple[str, ...], *, unit: str = "USD") -> tuple[OpenInterest, ...]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return tuple(
        open_interest(start + timedelta(days=index), open_interest_value=value, unit=unit)
        for index, value in enumerate(values)
    )


def market_cap(
    observation_time: datetime,
    *,
    market_cap_usd: str,
    available_at: datetime | None = None,
    provider: str = "coinmetrics",
) -> MarketCapObservation:
    return MarketCapObservation(
        observation_time=observation_time,
        market_cap_usd=Decimal(market_cap_usd),
        provider=provider,
        available_at=available_at or observation_time + timedelta(minutes=1),
    )


def daily_market_caps(values: tuple[str, ...]) -> tuple[MarketCapObservation, ...]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return tuple(
        market_cap(start + timedelta(days=index), market_cap_usd=value)
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


def test_futures_basis_health_metadata_is_stable() -> None:
    assert FUTURES_BASIS_HEALTH_FEATURE_ID == "FUTURES_BASIS_HEALTH"
    assert FUTURES_BASIS_AVG_FEATURE_ID == "FUTURES_BASIS_AVG"
    assert FUTURES_BASIS_ZSCORE_FEATURE_ID == "FUTURES_BASIS_ZSCORE_180D"
    assert DEFAULT_FUTURES_BASIS_ZSCORE_WINDOW_DAYS == 180
    assert DEFAULT_FUTURES_BASIS_MIN_ZSCORE_OBSERVATIONS == 30
    assert DEFAULT_FUTURES_BASIS_HEALTH_PREFERRED_ZSCORE == Decimal("0.25")
    assert DEFAULT_FUTURES_BASIS_HEALTH_ZSCORE_WIDTH == Decimal("1.25")
    assert FUTURES_BASIS_HEALTH_REASON_CODES == (
        "FUTURES_BASIS_INPUT_MISSING",
        "FUTURES_BASIS_INSUFFICIENT_HISTORY",
        "FUTURES_BASIS_ZERO_VARIANCE",
    )


def test_open_interest_growth_health_metadata_is_stable() -> None:
    assert OI_GROWTH_HEALTH_FEATURE_ID == "OI_GROWTH_HEALTH"
    assert OI_GROWTH_FEATURE_ID == "OI_GROWTH_7D"
    assert OI_GROWTH_ZSCORE_FEATURE_ID == "OI_GROWTH_ZSCORE_180D"
    assert DEFAULT_OI_GROWTH_WINDOW_DAYS == 7
    assert DEFAULT_OI_GROWTH_ZSCORE_WINDOW_DAYS == 180
    assert DEFAULT_OI_GROWTH_MIN_ZSCORE_OBSERVATIONS == 30
    assert DEFAULT_OI_GROWTH_HEALTH_PREFERRED_ZSCORE == Decimal("0.25")
    assert DEFAULT_OI_GROWTH_HEALTH_ZSCORE_WIDTH == Decimal("1.25")
    assert OI_GROWTH_HEALTH_REASON_CODES == (
        "OI_GROWTH_INPUT_MISSING",
        "OI_GROWTH_PRIOR_INPUT_MISSING",
        "OI_GROWTH_INSUFFICIENT_HISTORY",
        "OI_GROWTH_ZERO_VARIANCE",
    )


def test_open_interest_intensity_metadata_is_stable() -> None:
    assert OI_INTENSITY_FEATURE_ID == "OI_INTENSITY"
    assert OI_INTENSITY_PERCENTILE_FEATURE_ID == "OI_INTENSITY_PERCENTILE_180D"
    assert DEFAULT_OI_INTENSITY_PERCENTILE_WINDOW_DAYS == 180
    assert DEFAULT_OI_INTENSITY_MIN_PERCENTILE_OBSERVATIONS == 30
    assert OI_INTENSITY_REASON_CODES == (
        "OI_INTENSITY_OI_INPUT_MISSING",
        "OI_INTENSITY_MARKET_CAP_INPUT_MISSING",
        "OI_INTENSITY_INSUFFICIENT_HISTORY",
    )


def test_positioning_score_metadata_is_stable() -> None:
    assert POSITIONING_SCORE_FEATURE_ID == "POSITIONING_SCORE"
    assert POSITIONING_SCORE_COMPONENT_IDS == (
        "funding_health",
        "oi_health",
        "basis_health",
        "leverage_health",
    )
    assert DEFAULT_POSITIONING_SCORE_WEIGHTS == {
        "funding_health": Decimal("0.35"),
        "oi_health": Decimal("0.30"),
        "basis_health": Decimal("0.20"),
        "leverage_health": Decimal("0.15"),
    }
    assert POSITIONING_SCORE_REASON_CODES == ("POSITIONING_SCORE_INPUT_MISSING",)


def test_crowding_flag_metadata_is_stable() -> None:
    assert CROWDING_FLAG_FEATURE_ID == "CROWDING"
    assert CROWDING_FLAG_EFFECTS == (
        "NO_ADD",
        "REDUCE_ENTRY_QUALITY",
        "OPTIONAL_TIGHTER_PROFIT_PROTECTION",
    )
    assert DEFAULT_CROWDING_FUNDING_ZSCORE_MIN == Decimal("2")
    assert DEFAULT_CROWDING_BASIS_ZSCORE_MIN == Decimal("2")
    assert DEFAULT_CROWDING_OI_INTENSITY_PERCENTILE_MIN == Decimal("90")
    assert DEFAULT_CROWDING_ENTRY_QUALITY_PENALTY == Decimal("10")
    assert CROWDING_FLAG_REASON_CODES == (
        "CROWDING_FUNDING_EXCESS",
        "CROWDING_BASIS_EXCESS",
        "CROWDING_LEVERAGE_EXCESS",
        "CROWDING_INPUT_MISSING",
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


def test_futures_basis_health_uses_annualized_basis_rolling_zscore() -> None:
    rows = daily_futures_basis(
        (
            ("0.001", "0.01"),
            ("0.002", "0.02"),
            ("0.003", "0.03"),
            ("0.004", "0.04"),
            ("0.005", "0.05"),
            ("0.006", "0.06"),
            ("0.007", "0.07"),
            ("0.008", "0.08"),
            ("0.009", "0.09"),
            ("0.010", "0.10"),
        )
    )

    result = futures_basis_health(
        tuple(reversed(rows)),
        as_of=datetime(2026, 1, 10, 1, tzinfo=UTC),
        min_zscore_observations=3,
    )

    assert result.complete is True
    assert result.feature_id == "FUTURES_BASIS_HEALTH"
    assert result.observation_time == datetime(2026, 1, 10, tzinfo=UTC)
    assert result.zscore_window_days == 180
    assert result.basis_rate_avg == Decimal("0.010")
    assert result.annualized_basis_rate_avg == Decimal("0.10")
    assert result.annualized_basis_zscore is not None
    assert result.annualized_basis_zscore.quantize(Decimal("0.000001")) == Decimal("1.936492")
    assert result.health_score is not None
    assert result.health_score.quantize(Decimal("0.001")) == Decimal("40.246")
    assert result.history_observation_count == 9
    assert result.source_record_count == 10
    assert result.reason_codes == ()


def test_open_interest_growth_health_uses_rolling_normalized_growth() -> None:
    rows = daily_open_interest(
        ("100", "105", "110", "118", "125", "133", "140", "148", "160", "175", "190", "210")
    )

    result = open_interest_growth_health(
        tuple(reversed(rows)),
        as_of=datetime(2026, 1, 12, 1, tzinfo=UTC),
        open_interest_unit="USD",
        min_zscore_observations=4,
    )

    assert result.complete is True
    assert result.feature_id == "OI_GROWTH_HEALTH"
    assert result.observation_time == datetime(2026, 1, 12, tzinfo=UTC)
    assert result.open_interest_unit == "USD"
    assert result.growth_window_days == 7
    assert result.zscore_window_days == 180
    assert result.aggregate_open_interest == Decimal("210")
    assert result.prior_open_interest == Decimal("125")
    assert result.oi_growth == Decimal("0.68")
    assert result.oi_growth_zscore is not None
    assert result.oi_growth_zscore.quantize(Decimal("0.000001")) == Decimal("2.469899")
    assert result.health_score is not None
    assert result.health_score.quantize(Decimal("0.001")) == Decimal("20.661")
    assert result.history_observation_count == 4
    assert result.source_record_count == 12
    assert result.reason_codes == ()


def test_open_interest_intensity_uses_rolling_percentile() -> None:
    rows = daily_open_interest(("100", "120", "80", "110", "90", "105"))
    caps = daily_market_caps(("1000", "1000", "1000", "1000", "1000", "1000"))

    result = open_interest_intensity(
        tuple(reversed(rows)),
        tuple(reversed(caps)),
        as_of=datetime(2026, 1, 6, 1, tzinfo=UTC),
        open_interest_unit="USD",
        min_percentile_observations=5,
    )

    assert result.complete is True
    assert result.feature_id == "OI_INTENSITY"
    assert result.observation_time == datetime(2026, 1, 6, tzinfo=UTC)
    assert result.open_interest_unit == "USD"
    assert result.percentile_window_days == 180
    assert result.aggregate_open_interest == Decimal("105")
    assert result.market_cap_usd == Decimal("1000")
    assert result.oi_intensity == Decimal("0.105")
    assert result.oi_intensity_percentile == Decimal("60.0")
    assert result.health_score == Decimal("40.0")
    assert result.history_observation_count == 5
    assert result.open_interest_record_count == 6
    assert result.market_cap_record_count == 6
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


def test_futures_basis_health_filters_unavailable_future_rows() -> None:
    rows = daily_futures_basis(
        (
            ("0.001", "0.01"),
            ("0.002", "0.02"),
            ("0.003", "0.03"),
            ("0.004", "0.04"),
            ("0.005", "0.05"),
            ("0.006", "0.06"),
            ("0.007", "0.07"),
            ("0.008", "0.08"),
            ("0.009", "0.09"),
            ("0.010", "0.10"),
        )
    )
    unavailable_revision = futures_basis(
        datetime(2026, 1, 10, tzinfo=UTC),
        basis_rate="1.00",
        annualized_basis_rate="1.00",
        available_at=datetime(2026, 1, 11, tzinfo=UTC),
        exchange="okx",
    )

    baseline = futures_basis_health(
        rows,
        as_of=datetime(2026, 1, 10, 1, tzinfo=UTC),
        min_zscore_observations=3,
    ).as_record()
    with_future = futures_basis_health(
        (*rows, unavailable_revision),
        as_of=datetime(2026, 1, 10, 1, tzinfo=UTC),
        min_zscore_observations=3,
    ).as_record()

    assert with_future == baseline


def test_open_interest_growth_health_filters_unavailable_future_rows() -> None:
    rows = daily_open_interest(
        ("100", "105", "110", "118", "125", "133", "140", "148", "160", "175", "190", "210")
    )
    unavailable_revision = open_interest(
        datetime(2026, 1, 12, tzinfo=UTC),
        open_interest_value="9999",
        available_at=datetime(2026, 1, 13, tzinfo=UTC),
        exchange="okx",
    )

    baseline = open_interest_growth_health(
        rows,
        as_of=datetime(2026, 1, 12, 1, tzinfo=UTC),
        open_interest_unit="USD",
        min_zscore_observations=4,
    ).as_record()
    with_future = open_interest_growth_health(
        (*rows, unavailable_revision),
        as_of=datetime(2026, 1, 12, 1, tzinfo=UTC),
        open_interest_unit="USD",
        min_zscore_observations=4,
    ).as_record()

    assert with_future == baseline


def test_open_interest_intensity_filters_unavailable_future_rows() -> None:
    rows = daily_open_interest(("100", "120", "80", "110", "90", "105"))
    caps = daily_market_caps(("1000", "1000", "1000", "1000", "1000", "1000"))
    unavailable_oi = open_interest(
        datetime(2026, 1, 6, tzinfo=UTC),
        open_interest_value="9999",
        available_at=datetime(2026, 1, 7, tzinfo=UTC),
        exchange="okx",
    )
    unavailable_cap = market_cap(
        datetime(2026, 1, 6, tzinfo=UTC),
        market_cap_usd="1",
        available_at=datetime(2026, 1, 7, tzinfo=UTC),
        provider="late-provider",
    )

    baseline = open_interest_intensity(
        rows,
        caps,
        as_of=datetime(2026, 1, 6, 1, tzinfo=UTC),
        open_interest_unit="USD",
        min_percentile_observations=5,
    ).as_record()
    with_future = open_interest_intensity(
        (*rows, unavailable_oi),
        (*caps, unavailable_cap),
        as_of=datetime(2026, 1, 6, 1, tzinfo=UTC),
        open_interest_unit="USD",
        min_percentile_observations=5,
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


def test_futures_basis_health_averages_multiple_exchange_rows_per_timestamp() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    rows = (
        futures_basis(start, basis_rate="0.001", annualized_basis_rate="0.01"),
        futures_basis(
            start + timedelta(days=1),
            basis_rate="0.002",
            annualized_basis_rate="0.02",
        ),
        futures_basis(
            start + timedelta(days=2),
            basis_rate="0.003",
            annualized_basis_rate="0.03",
        ),
        futures_basis(
            start + timedelta(days=2),
            basis_rate="0.009",
            annualized_basis_rate="0.09",
            exchange="okx",
        ),
    )

    result = futures_basis_health(
        rows,
        as_of=start + timedelta(days=2, hours=1),
        min_zscore_observations=2,
    )

    assert result.basis_rate_avg == Decimal("0.006")
    assert result.annualized_basis_rate_avg == Decimal("0.06")
    assert result.source_record_count == 4
    assert result.history_observation_count == 2


def test_open_interest_growth_health_aggregates_multiple_exchanges_and_filters_units() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    rows = (
        open_interest(start, open_interest_value="100"),
        open_interest(start, open_interest_value="50", exchange="okx"),
        open_interest(start, open_interest_value="999", exchange="bybit", unit="contracts"),
        open_interest(start + timedelta(days=1), open_interest_value="165"),
        open_interest(start + timedelta(days=1), open_interest_value="15", exchange="okx"),
    )

    result = open_interest_growth_health(
        rows,
        as_of=start + timedelta(days=1, hours=1),
        open_interest_unit="USD",
        growth_window_days=1,
        min_zscore_observations=1,
    )

    assert result.aggregate_open_interest == Decimal("180")
    assert result.prior_open_interest == Decimal("150")
    assert result.oi_growth == Decimal("0.2")
    assert result.source_record_count == 4


def test_open_interest_intensity_aggregates_exchanges_and_filters_units() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    rows = (
        open_interest(start, open_interest_value="100"),
        open_interest(start, open_interest_value="50", exchange="okx"),
        open_interest(start, open_interest_value="999", exchange="bybit", unit="contracts"),
        open_interest(start + timedelta(days=1), open_interest_value="300"),
    )
    caps = (
        market_cap(start, market_cap_usd="1000"),
        market_cap(start, market_cap_usd="2000", provider="second-provider"),
        market_cap(start + timedelta(days=1), market_cap_usd="1500"),
    )

    result = open_interest_intensity(
        rows,
        caps,
        as_of=start + timedelta(days=1, hours=1),
        open_interest_unit="USD",
        percentile_window_days=10,
        min_percentile_observations=1,
    )

    assert result.complete is True
    assert result.aggregate_open_interest == Decimal("300")
    assert result.market_cap_usd == Decimal("1500")
    assert result.oi_intensity == Decimal("0.2")
    assert result.oi_intensity_percentile == Decimal("100")
    assert result.open_interest_record_count == 3
    assert result.market_cap_record_count == 3


def test_funding_health_reports_missing_input_without_zero_fill() -> None:
    result = funding_health((), as_of=datetime(2026, 1, 10, tzinfo=UTC))

    assert result.complete is False
    assert result.funding_7d_avg is None
    assert result.funding_zscore is None
    assert result.health_score is None
    assert result.reason_codes == ("FUNDING_RATE_INPUT_MISSING",)


def test_futures_basis_health_reports_missing_input_without_zero_fill() -> None:
    result = futures_basis_health((), as_of=datetime(2026, 1, 10, tzinfo=UTC))

    assert result.complete is False
    assert result.basis_rate_avg is None
    assert result.annualized_basis_rate_avg is None
    assert result.annualized_basis_zscore is None
    assert result.health_score is None
    assert result.reason_codes == ("FUTURES_BASIS_INPUT_MISSING",)


def test_open_interest_growth_health_reports_missing_input_without_zero_fill() -> None:
    result = open_interest_growth_health(
        (),
        as_of=datetime(2026, 1, 10, tzinfo=UTC),
        open_interest_unit="USD",
    )

    assert result.complete is False
    assert result.aggregate_open_interest is None
    assert result.prior_open_interest is None
    assert result.oi_growth is None
    assert result.health_score is None
    assert result.reason_codes == ("OI_GROWTH_INPUT_MISSING",)


def test_open_interest_intensity_reports_missing_inputs_without_zero_fill() -> None:
    result = open_interest_intensity(
        (),
        (),
        as_of=datetime(2026, 1, 10, tzinfo=UTC),
        open_interest_unit="USD",
    )

    assert result.complete is False
    assert result.aggregate_open_interest is None
    assert result.market_cap_usd is None
    assert result.oi_intensity is None
    assert result.health_score is None
    assert result.reason_codes == (
        "OI_INTENSITY_OI_INPUT_MISSING",
        "OI_INTENSITY_MARKET_CAP_INPUT_MISSING",
    )


def test_open_interest_intensity_reports_missing_market_cap() -> None:
    rows = daily_open_interest(("100", "120"))

    result = open_interest_intensity(
        rows,
        (),
        as_of=datetime(2026, 1, 2, 1, tzinfo=UTC),
        open_interest_unit="USD",
    )

    assert result.complete is False
    assert result.aggregate_open_interest == Decimal("120")
    assert result.market_cap_usd is None
    assert result.oi_intensity is None
    assert result.reason_codes == ("OI_INTENSITY_MARKET_CAP_INPUT_MISSING",)


def test_open_interest_growth_health_reports_missing_prior_input() -> None:
    rows = daily_open_interest(("100", "110"))

    result = open_interest_growth_health(
        rows,
        as_of=datetime(2026, 1, 2, 1, tzinfo=UTC),
        open_interest_unit="USD",
        min_zscore_observations=1,
    )

    assert result.complete is False
    assert result.aggregate_open_interest == Decimal("110")
    assert result.prior_open_interest is None
    assert result.oi_growth is None
    assert result.reason_codes == ("OI_GROWTH_PRIOR_INPUT_MISSING",)


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


def test_futures_basis_health_reports_insufficient_history() -> None:
    rows = daily_futures_basis((("0.001", "0.01"), ("0.002", "0.02")))

    result = futures_basis_health(
        rows,
        as_of=datetime(2026, 1, 2, 1, tzinfo=UTC),
        min_zscore_observations=3,
    )

    assert result.complete is False
    assert result.annualized_basis_rate_avg == Decimal("0.02")
    assert result.annualized_basis_zscore is None
    assert result.health_score is None
    assert result.history_observation_count == 1
    assert result.reason_codes == ("FUTURES_BASIS_INSUFFICIENT_HISTORY",)


def test_open_interest_growth_health_reports_insufficient_history() -> None:
    rows = daily_open_interest(
        ("100", "105", "110", "118", "125", "133", "140", "148", "160")
    )

    result = open_interest_growth_health(
        rows,
        as_of=datetime(2026, 1, 9, 1, tzinfo=UTC),
        open_interest_unit="USD",
        min_zscore_observations=3,
    )

    assert result.complete is False
    assert result.aggregate_open_interest == Decimal("160")
    assert result.prior_open_interest == Decimal("105")
    assert result.oi_growth == Decimal("0.523809523809523809523809524")
    assert result.oi_growth_zscore is None
    assert result.health_score is None
    assert result.history_observation_count == 1
    assert result.reason_codes == ("OI_GROWTH_INSUFFICIENT_HISTORY",)


def test_open_interest_intensity_reports_insufficient_history() -> None:
    rows = daily_open_interest(("100", "120"))
    caps = daily_market_caps(("1000", "1000"))

    result = open_interest_intensity(
        rows,
        caps,
        as_of=datetime(2026, 1, 2, 1, tzinfo=UTC),
        open_interest_unit="USD",
        min_percentile_observations=2,
    )

    assert result.complete is False
    assert result.oi_intensity == Decimal("0.12")
    assert result.oi_intensity_percentile is None
    assert result.health_score is None
    assert result.history_observation_count == 1
    assert result.reason_codes == ("OI_INTENSITY_INSUFFICIENT_HISTORY",)


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


def test_futures_basis_health_reports_zero_variance_history() -> None:
    rows = daily_futures_basis(
        (("0.001", "0.01"), ("0.001", "0.01"), ("0.001", "0.01"), ("0.001", "0.01"))
    )

    result = futures_basis_health(
        rows,
        as_of=datetime(2026, 1, 4, 1, tzinfo=UTC),
        min_zscore_observations=3,
    )

    assert result.complete is False
    assert result.annualized_basis_rate_avg == Decimal("0.01")
    assert result.annualized_basis_zscore is None
    assert result.health_score is None
    assert result.reason_codes == ("FUTURES_BASIS_ZERO_VARIANCE",)


def test_open_interest_growth_health_reports_zero_variance_history() -> None:
    rows = daily_open_interest(
        ("100", "100", "100", "100", "100", "100", "100", "100", "100", "100", "100")
    )

    result = open_interest_growth_health(
        rows,
        as_of=datetime(2026, 1, 11, 1, tzinfo=UTC),
        open_interest_unit="USD",
        growth_window_days=1,
        min_zscore_observations=3,
    )

    assert result.complete is False
    assert result.oi_growth is not None
    assert result.oi_growth_zscore is None
    assert result.health_score is None
    assert result.reason_codes == ("OI_GROWTH_ZERO_VARIANCE",)


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


def test_futures_basis_health_exposes_persistable_payload() -> None:
    rows = daily_futures_basis(
        (
            ("0.001", "0.01"),
            ("0.002", "0.02"),
            ("0.003", "0.03"),
            ("0.004", "0.04"),
            ("0.005", "0.05"),
            ("0.006", "0.06"),
            ("0.007", "0.07"),
            ("0.008", "0.08"),
            ("0.009", "0.09"),
            ("0.010", "0.10"),
        )
    )

    result = futures_basis_health(
        rows,
        as_of=datetime(2026, 1, 10, 1, tzinfo=UTC),
        min_zscore_observations=3,
    )

    record = result.as_record()
    assert record["feature_id"] == "FUTURES_BASIS_HEALTH"
    assert record["observation_time"] == "2026-01-10T00:00:00+00:00"
    assert record["average_feature_id"] == "FUTURES_BASIS_AVG"
    assert record["zscore_feature_id"] == "FUTURES_BASIS_ZSCORE_180D"
    assert record["zscore_window_days"] == 180
    assert record["min_zscore_observations"] == 3
    assert record["preferred_basis_zscore"] == "0.25"
    assert record["basis_zscore_width"] == "1.25"
    assert record["basis_rate_avg"] == "0.010"
    assert record["annualized_basis_rate_avg"] == "0.10"
    assert record["annualized_basis_zscore"] == str(result.annualized_basis_zscore)
    assert record["health_score"] == str(result.health_score)
    assert record["history_observation_count"] == 9
    assert record["source_record_count"] == 10
    assert record["complete"] is True
    assert record["reason_codes"] == []


def test_open_interest_growth_health_exposes_persistable_payload() -> None:
    rows = daily_open_interest(
        ("100", "105", "110", "118", "125", "133", "140", "148", "160", "175", "190", "210")
    )

    result = open_interest_growth_health(
        rows,
        as_of=datetime(2026, 1, 12, 1, tzinfo=UTC),
        open_interest_unit="USD",
        min_zscore_observations=4,
    )

    record = result.as_record()
    assert record["feature_id"] == "OI_GROWTH_HEALTH"
    assert record["observation_time"] == "2026-01-12T00:00:00+00:00"
    assert record["growth_feature_id"] == "OI_GROWTH_7D"
    assert record["zscore_feature_id"] == "OI_GROWTH_ZSCORE_180D"
    assert record["open_interest_unit"] == "USD"
    assert record["growth_window_days"] == 7
    assert record["zscore_window_days"] == 180
    assert record["min_zscore_observations"] == 4
    assert record["preferred_growth_zscore"] == "0.25"
    assert record["growth_zscore_width"] == "1.25"
    assert record["aggregate_open_interest"] == "210"
    assert record["prior_open_interest"] == "125"
    assert record["oi_growth"] == "0.68"
    assert record["oi_growth_zscore"] == str(result.oi_growth_zscore)
    assert record["health_score"] == str(result.health_score)
    assert record["history_observation_count"] == 4
    assert record["source_record_count"] == 12
    assert record["complete"] is True
    assert record["reason_codes"] == []


def test_open_interest_intensity_exposes_persistable_payload() -> None:
    rows = daily_open_interest(("100", "120", "80", "110", "90", "105"))
    caps = daily_market_caps(("1000", "1000", "1000", "1000", "1000", "1000"))

    result = open_interest_intensity(
        rows,
        caps,
        as_of=datetime(2026, 1, 6, 1, tzinfo=UTC),
        open_interest_unit="USD",
        min_percentile_observations=5,
    )

    record = result.as_record()
    assert record["feature_id"] == "OI_INTENSITY"
    assert record["observation_time"] == "2026-01-06T00:00:00+00:00"
    assert record["percentile_feature_id"] == "OI_INTENSITY_PERCENTILE_180D"
    assert record["open_interest_unit"] == "USD"
    assert record["percentile_window_days"] == 180
    assert record["min_percentile_observations"] == 5
    assert record["aggregate_open_interest"] == "105"
    assert record["market_cap_usd"] == "1000"
    assert record["oi_intensity"] == "0.105"
    assert record["oi_intensity_percentile"] == "60.0"
    assert record["health_score"] == "40.0"
    assert record["history_observation_count"] == 5
    assert record["open_interest_record_count"] == 6
    assert record["market_cap_record_count"] == 6
    assert record["complete"] is True
    assert record["reason_codes"] == []


def test_calculate_positioning_score_uses_rulebook_weights() -> None:
    result = calculate_positioning_score(
        PositioningScoreInput(
            funding_health=Decimal("80"),
            oi_health=Decimal("70"),
            basis_health=Decimal("60"),
            leverage_health=Decimal("40"),
        ),
    )

    assert result.complete is True
    assert result.feature_id == "POSITIONING_SCORE"
    assert result.score == Decimal("67.00")
    assert result.interpretation == "TRADE_SUPPORTIVE"
    assert result.reason_code == "POSITIONING_SCORE_TRADE_SUPPORTIVE"
    assert result.weights == {
        "funding_health": Decimal("0.35"),
        "oi_health": Decimal("0.30"),
        "basis_health": Decimal("0.20"),
        "leverage_health": Decimal("0.15"),
    }
    assert result.contributions == {
        "funding_health": Decimal("28.00"),
        "oi_health": Decimal("21.00"),
        "basis_health": Decimal("12.00"),
        "leverage_health": Decimal("6.00"),
    }
    assert result.reason_codes == ()


def test_calculate_positioning_score_interprets_rulebook_thresholds() -> None:
    add_supportive = calculate_positioning_score(
        PositioningScoreInput(
            funding_health=Decimal("70"),
            oi_health=Decimal("70"),
            basis_health=Decimal("70"),
            leverage_health=Decimal("70"),
        ),
    )
    weak = calculate_positioning_score(
        PositioningScoreInput(
            funding_health=Decimal("40"),
            oi_health=Decimal("40"),
            basis_health=Decimal("40"),
            leverage_health=Decimal("40"),
        ),
    )
    stressed = calculate_positioning_score(
        PositioningScoreInput(
            funding_health=Decimal("39"),
            oi_health=Decimal("39"),
            basis_health=Decimal("39"),
            leverage_health=Decimal("39"),
        ),
    )

    assert add_supportive.interpretation == "ADD_SUPPORTIVE"
    assert weak.interpretation == "WEAK_POSITIONING"
    assert stressed.interpretation == "STRESSED_POSITIONING"


def test_calculate_positioning_score_does_not_fill_missing_inputs() -> None:
    result = calculate_positioning_score(
        PositioningScoreInput(
            funding_health=Decimal("80"),
            oi_health=None,
            basis_health=Decimal("60"),
            leverage_health=Decimal("40"),
        ),
    )

    assert result.complete is False
    assert result.score is None
    assert result.interpretation is None
    assert result.reason_code is None
    assert result.contributions == {
        "funding_health": Decimal("28.00"),
        "oi_health": None,
        "basis_health": Decimal("12.00"),
        "leverage_health": Decimal("6.00"),
    }
    assert result.reason_codes == ("POSITIONING_SCORE_INPUT_MISSING",)


def test_calculate_positioning_score_exposes_persistable_payload() -> None:
    result = calculate_positioning_score(
        PositioningScoreInput(
            funding_health=Decimal("80"),
            oi_health=Decimal("70"),
            basis_health=Decimal("60"),
            leverage_health=Decimal("40"),
        ),
        config_metadata={
            "config_version": "strategy_config_v2",
            "strategy_version": "swing_v1.2",
            "parameter_set_id": "default_phase1",
        },
    )

    record = result.as_record()
    assert record["feature_id"] == "POSITIONING_SCORE"
    assert record["score"] == "67.00"
    assert record["interpretation"] == "TRADE_SUPPORTIVE"
    assert record["reason_code"] == "POSITIONING_SCORE_TRADE_SUPPORTIVE"
    assert record["inputs"] == {
        "funding_health": "80",
        "oi_health": "70",
        "basis_health": "60",
        "leverage_health": "40",
    }
    assert record["weights"] == {
        "funding_health": "0.35",
        "oi_health": "0.30",
        "basis_health": "0.20",
        "leverage_health": "0.15",
    }
    assert record["contributions"] == {
        "funding_health": "28.00",
        "oi_health": "21.00",
        "basis_health": "12.00",
        "leverage_health": "6.00",
    }
    assert record["config_metadata"] == {
        "config_version": "strategy_config_v2",
        "strategy_version": "swing_v1.2",
        "parameter_set_id": "default_phase1",
    }
    assert record["complete"] is True
    assert record["reason_codes"] == []


def test_calculate_positioning_score_uses_weights_from_versioned_strategy_config() -> None:
    config = load_strategy_config()

    result = calculate_positioning_score(
        PositioningScoreInput(
            funding_health=Decimal("80"),
            oi_health=Decimal("70"),
            basis_health=Decimal("60"),
            leverage_health=Decimal("40"),
        ),
        weights=config.scoring_weights.positioning,
        config_metadata=config.run_metadata(),
    )

    assert result.score == Decimal("67.00")
    assert result.weights == {
        "funding_health": Decimal("0.35"),
        "oi_health": Decimal("0.3"),
        "basis_health": Decimal("0.2"),
        "leverage_health": Decimal("0.15"),
    }
    assert result.config_metadata == {
        "config_version": "strategy_config_v2",
        "strategy_version": "swing_v1.2",
        "parameter_set_id": "default_phase1",
    }


def test_calculate_crowding_flag_triggers_from_excess_inputs() -> None:
    result = calculate_crowding_flag(
        CrowdingFlagInput(
            funding_zscore=Decimal("2.1"),
            basis_zscore=Decimal("1.5"),
            oi_intensity_percentile=Decimal("95"),
        ),
    )

    assert result.complete is True
    assert result.feature_id == "CROWDING"
    assert result.flagged is True
    assert result.effects == CROWDING_FLAG_EFFECTS
    assert result.entry_quality_penalty == Decimal("10")
    assert result.reason_codes == (
        "CROWDING_FUNDING_EXCESS",
        "CROWDING_LEVERAGE_EXCESS",
    )


def test_calculate_crowding_flag_stays_clear_for_normal_inputs() -> None:
    result = calculate_crowding_flag(
        CrowdingFlagInput(
            funding_zscore=Decimal("1.9"),
            basis_zscore=Decimal("1.5"),
            oi_intensity_percentile=Decimal("89.9"),
        ),
    )

    assert result.complete is True
    assert result.flagged is False
    assert result.effects == ()
    assert result.entry_quality_penalty == Decimal("0")
    assert result.reason_codes == ()


def test_calculate_crowding_flag_does_not_clear_missing_inputs_silently() -> None:
    result = calculate_crowding_flag(
        CrowdingFlagInput(
            funding_zscore=None,
            basis_zscore=Decimal("2.5"),
            oi_intensity_percentile=None,
        ),
    )

    assert result.complete is False
    assert result.flagged is True
    assert result.effects == CROWDING_FLAG_EFFECTS
    assert result.reason_codes == (
        "CROWDING_INPUT_MISSING",
        "CROWDING_BASIS_EXCESS",
    )


def test_calculate_crowding_flag_uses_versioned_strategy_config() -> None:
    config = load_strategy_config()
    crowding_config = config.positioning_flags.crowding

    result = calculate_crowding_flag(
        CrowdingFlagInput(
            funding_zscore=Decimal("2.1"),
            basis_zscore=Decimal("1.5"),
            oi_intensity_percentile=Decimal("95"),
        ),
        funding_zscore_min=crowding_config.funding_zscore_min,
        basis_zscore_min=crowding_config.basis_zscore_min,
        oi_intensity_percentile_min=crowding_config.oi_intensity_percentile_min,
        entry_quality_penalty=crowding_config.entry_quality_penalty,
        config_metadata=config.run_metadata(),
    )

    assert result.flagged is True
    assert result.funding_zscore_min == Decimal("2.0")
    assert result.basis_zscore_min == Decimal("2.0")
    assert result.oi_intensity_percentile_min == Decimal("90.0")
    assert result.entry_quality_penalty == Decimal("10.0")
    assert result.config_metadata == {
        "config_version": "strategy_config_v2",
        "strategy_version": "swing_v1.2",
        "parameter_set_id": "default_phase1",
    }


def test_calculate_crowding_flag_exposes_persistable_payload() -> None:
    result = calculate_crowding_flag(
        CrowdingFlagInput(
            funding_zscore=Decimal("2.1"),
            basis_zscore=Decimal("1.5"),
            oi_intensity_percentile=Decimal("95"),
        ),
        config_metadata={
            "config_version": "strategy_config_v2",
            "strategy_version": "swing_v1.2",
            "parameter_set_id": "default_phase1",
        },
    )

    record = result.as_record()
    assert record["feature_id"] == "CROWDING"
    assert record["flagged"] is True
    assert record["effects"] == [
        "NO_ADD",
        "REDUCE_ENTRY_QUALITY",
        "OPTIONAL_TIGHTER_PROFIT_PROTECTION",
    ]
    assert record["entry_quality_penalty"] == "10"
    assert record["funding_zscore_min"] == "2"
    assert record["basis_zscore_min"] == "2"
    assert record["oi_intensity_percentile_min"] == "90"
    assert record["inputs"] == {
        "funding_zscore": "2.1",
        "basis_zscore": "1.5",
        "oi_intensity_percentile": "95",
    }
    assert record["config_metadata"] == {
        "config_version": "strategy_config_v2",
        "strategy_version": "swing_v1.2",
        "parameter_set_id": "default_phase1",
    }
    assert record["complete"] is True
    assert record["reason_codes"] == [
        "CROWDING_FUNDING_EXCESS",
        "CROWDING_LEVERAGE_EXCESS",
    ]


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


def test_futures_basis_health_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="as_of must be timezone-aware UTC"):
        futures_basis_health((), as_of=datetime(2026, 1, 10))

    with pytest.raises(ValueError, match="zscore_window_days"):
        futures_basis_health(
            (),
            as_of=datetime(2026, 1, 10, tzinfo=UTC),
            zscore_window_days=0,
        )

    with pytest.raises(ValueError, match="basis_zscore_width"):
        futures_basis_health(
            (),
            as_of=datetime(2026, 1, 10, tzinfo=UTC),
            basis_zscore_width=Decimal("0"),
        )


def test_open_interest_growth_health_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="as_of must be timezone-aware UTC"):
        open_interest_growth_health((), as_of=datetime(2026, 1, 10), open_interest_unit="USD")

    with pytest.raises(ValueError, match="open_interest_unit"):
        open_interest_growth_health(
            (),
            as_of=datetime(2026, 1, 10, tzinfo=UTC),
            open_interest_unit="",
        )

    with pytest.raises(ValueError, match="growth_window_days"):
        open_interest_growth_health(
            (),
            as_of=datetime(2026, 1, 10, tzinfo=UTC),
            open_interest_unit="USD",
            growth_window_days=0,
        )

    with pytest.raises(ValueError, match="growth_zscore_width"):
        open_interest_growth_health(
            (),
            as_of=datetime(2026, 1, 10, tzinfo=UTC),
            open_interest_unit="USD",
            growth_zscore_width=Decimal("0"),
        )


def test_open_interest_intensity_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="as_of must be timezone-aware UTC"):
        open_interest_intensity((), (), as_of=datetime(2026, 1, 10), open_interest_unit="USD")

    with pytest.raises(ValueError, match="open_interest_unit"):
        open_interest_intensity(
            (),
            (),
            as_of=datetime(2026, 1, 10, tzinfo=UTC),
            open_interest_unit="",
        )

    with pytest.raises(ValueError, match="percentile_window_days"):
        open_interest_intensity(
            (),
            (),
            as_of=datetime(2026, 1, 10, tzinfo=UTC),
            open_interest_unit="USD",
            percentile_window_days=0,
        )

    with pytest.raises(ValueError, match="market_cap_usd"):
        open_interest_intensity(
            (),
            (
                market_cap(
                    datetime(2026, 1, 10, tzinfo=UTC),
                    market_cap_usd="0",
                ),
            ),
            as_of=datetime(2026, 1, 10, tzinfo=UTC),
            open_interest_unit="USD",
        )


def test_calculate_positioning_score_rejects_invalid_weights() -> None:
    with pytest.raises(ValueError, match="positioning"):
        calculate_positioning_score(
            PositioningScoreInput(
                funding_health=Decimal("80"),
                oi_health=Decimal("70"),
                basis_health=Decimal("60"),
                leverage_health=Decimal("40"),
            ),
            weights={
                "funding_health": 0.35,
                "oi_health": 0.30,
                "basis_health": 0.20,
            },
        )

    with pytest.raises(ValueError, match="sum to 1"):
        calculate_positioning_score(
            PositioningScoreInput(
                funding_health=Decimal("80"),
                oi_health=Decimal("70"),
                basis_health=Decimal("60"),
                leverage_health=Decimal("40"),
            ),
            weights={
                "funding_health": 0.35,
                "oi_health": 0.30,
                "basis_health": 0.20,
                "leverage_health": 0.10,
            },
        )


def test_calculate_positioning_score_rejects_out_of_range_inputs() -> None:
    with pytest.raises(ValueError, match="funding_health"):
        calculate_positioning_score(
            PositioningScoreInput(
                funding_health=Decimal("101"),
                oi_health=Decimal("70"),
                basis_health=Decimal("60"),
                leverage_health=Decimal("40"),
            ),
        )


def test_calculate_crowding_flag_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="funding_zscore_min"):
        calculate_crowding_flag(
            CrowdingFlagInput(
                funding_zscore=Decimal("1"),
                basis_zscore=Decimal("1"),
                oi_intensity_percentile=Decimal("50"),
            ),
            funding_zscore_min=Decimal("-1"),
        )

    with pytest.raises(ValueError, match="oi_intensity_percentile"):
        calculate_crowding_flag(
            CrowdingFlagInput(
                funding_zscore=Decimal("1"),
                basis_zscore=Decimal("1"),
                oi_intensity_percentile=Decimal("101"),
            ),
        )

    with pytest.raises(ValueError, match="entry_quality_penalty"):
        calculate_crowding_flag(
            CrowdingFlagInput(
                funding_zscore=Decimal("1"),
                basis_zscore=Decimal("1"),
                oi_intensity_percentile=Decimal("50"),
            ),
            entry_quality_penalty=Decimal("101"),
        )
