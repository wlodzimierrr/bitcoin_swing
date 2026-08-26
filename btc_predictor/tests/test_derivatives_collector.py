from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.dialects import postgresql

from btc_predictor.data import (
    DERIVATIVES_FEEDS,
    DerivativesCollectionRequest,
    FundingRate,
    FuturesBasis,
    Liquidation,
    OpenInterest,
    PerpVolume,
    aggregate_btc_derivatives_available_at,
    build_derivatives_insert_ignore,
    collect_btc_derivatives,
    latest_derivatives_available_at,
)


class RecordingConnection:
    def __init__(self) -> None:
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)


class StaticDerivativesProvider:
    def __init__(self, rows_by_feed):
        self.rows_by_feed = rows_by_feed
        self.calls = {feed_name: 0 for feed_name in DERIVATIVES_FEEDS}

    def fetch_funding_rates(self, **kwargs):
        return self._fetch("funding_rates", kwargs)

    def fetch_open_interest(self, **kwargs):
        return self._fetch("open_interest", kwargs)

    def fetch_futures_basis(self, **kwargs):
        return self._fetch("futures_basis", kwargs)

    def fetch_liquidations(self, **kwargs):
        return self._fetch("liquidations", kwargs)

    def fetch_perp_volume(self, **kwargs):
        return self._fetch("perp_volume", kwargs)

    def _fetch(self, feed_name: str, kwargs):
        self.calls[feed_name] += 1
        assert kwargs["exchange"] == "binance"
        assert kwargs["symbol"] == "BTCUSDT"
        assert kwargs["instrument"] == "BTCUSDT-PERP"
        assert kwargs["timeframe"] == "1h"
        return self.rows_by_feed[feed_name]


class FlakyFundingProvider(StaticDerivativesProvider):
    def fetch_funding_rates(self, **kwargs):
        self.calls["funding_rates"] += 1
        if self.calls["funding_rates"] == 1:
            raise RuntimeError("temporary funding outage")
        assert kwargs["timeframe"] == "1h"
        return self.rows_by_feed["funding_rates"]


def derivatives_request() -> DerivativesCollectionRequest:
    return DerivativesCollectionRequest(
        exchange="binance",
        symbol="BTCUSDT",
        provider="binance",
        instrument="BTCUSDT-PERP",
        source="binance-api",
        start=datetime(2026, 8, 25, tzinfo=UTC),
        end=datetime(2026, 8, 25, 1, tzinfo=UTC),
    )


def rows_by_feed(observation_time: datetime | None = None):
    observed = observation_time or datetime(2026, 8, 25, tzinfo=UTC)
    available = datetime(2026, 8, 25, 1, tzinfo=UTC)
    return {
        "funding_rates": (
            {
                "observation_time": observed,
                "funding_rate": "0.0001",
                "funding_interval_hours": "8",
                "available_at": available,
            },
        ),
        "open_interest": (
            {
                "observation_time": observed,
                "open_interest": "12345.5",
                "open_interest_unit": "contracts",
                "available_at": available,
            },
        ),
        "futures_basis": (
            {
                "observation_time": observed,
                "expiry": datetime(2026, 9, 25, tzinfo=UTC),
                "basis_rate": "0.02",
                "annualized_basis_rate": "0.18",
                "available_at": available,
            },
        ),
        "liquidations": (
            {
                "observation_time": observed,
                "side": "long",
                "quantity": "3",
                "quantity_unit": "BTC",
                "notional_usd": "300000",
                "available_at": available,
            },
            {
                "observation_time": observed,
                "side": "short",
                "quantity": "2",
                "quantity_unit": "BTC",
                "notional_usd": "200000",
                "available_at": available,
            },
        ),
        "perp_volume": (
            {
                "observation_time": observed,
                "volume": "50",
                "volume_unit": "BTC",
                "notional_usd": "5000000",
                "available_at": available,
            },
        ),
    }


def test_collect_btc_derivatives_normalizes_all_raw_feeds_and_retries() -> None:
    one_hour_east = timezone(timedelta(hours=1))
    shifted_observation_time = datetime(2026, 8, 25, 1, tzinfo=one_hour_east)
    provider = FlakyFundingProvider(rows_by_feed(shifted_observation_time))
    connection = RecordingConnection()

    result = collect_btc_derivatives(
        provider,
        connection,
        derivatives_request(),
        ingested_at=datetime(2026, 8, 25, 2, tzinfo=UTC),
    )

    assert result.provider_attempts["funding_rates"] == 2
    assert result.provider_attempts["open_interest"] == 1
    assert result.funding_rates[0].observation_time == datetime(2026, 8, 25, tzinfo=UTC)
    assert result.funding_rates[0].funding_rate == Decimal("0.0001")
    assert result.open_interest[0].open_interest == Decimal("12345.5")
    assert result.futures_basis[0].annualized_basis_rate == Decimal("0.18")
    assert result.liquidations[0].timeframe == "1h"
    assert result.perp_volume[0].volume_unit == "BTC"
    assert len(connection.statements) == 5


def test_derivatives_insert_ignore_is_idempotent_without_changing_existing_raw_records() -> None:
    result = collect_btc_derivatives(
        StaticDerivativesProvider(rows_by_feed()),
        RecordingConnection(),
        derivatives_request(),
        ingested_at=datetime(2026, 8, 25, 2, tzinfo=UTC),
    )

    statements = build_derivatives_insert_ignore(result)
    compiled = [str(statement.compile(dialect=postgresql.dialect())) for statement in statements]

    assert len(compiled) == 5
    assert all("DO NOTHING" in sql for sql in compiled)
    assert all("DO UPDATE SET" not in sql for sql in compiled)
    assert any("INSERT INTO raw.funding_rates" in sql for sql in compiled)
    assert any("INSERT INTO raw.open_interest" in sql for sql in compiled)
    assert any("INSERT INTO raw.futures_basis" in sql for sql in compiled)
    assert any("INSERT INTO raw.liquidations" in sql for sql in compiled)
    assert any("INSERT INTO raw.perp_volume" in sql for sql in compiled)


def test_latest_derivatives_available_at_filters_future_observations_and_availability() -> None:
    queries = latest_derivatives_available_at(datetime(2026, 8, 25, 1, tzinfo=UTC))

    assert tuple(queries) == DERIVATIVES_FEEDS
    for query in queries.values():
        compiled = str(query.compile(dialect=postgresql.dialect()))
        assert "available_at <= " in compiled
        assert "observation_time <= " in compiled


def test_aggregate_btc_derivatives_view_excludes_future_unavailable_rows() -> None:
    result = collect_btc_derivatives(
        StaticDerivativesProvider(rows_by_feed()),
        RecordingConnection(),
        derivatives_request(),
        ingested_at=datetime(2026, 8, 25, 2, tzinfo=UTC),
    )
    future_available_funding = FundingRate(
        observation_time=datetime(2026, 8, 25, tzinfo=UTC),
        exchange="binance",
        symbol="BTCUSDT",
        instrument="BTCUSDT-PERP",
        funding_rate=Decimal("0.05"),
        funding_interval_hours=Decimal("8"),
        provider="binance",
        source="binance-api",
        available_at=datetime(2026, 8, 26, tzinfo=UTC),
        ingested_at=datetime(2026, 8, 25, 2, tzinfo=UTC),
    )
    future_observation_volume = PerpVolume(
        observation_time=datetime(2026, 8, 26, tzinfo=UTC),
        exchange="binance",
        symbol="BTCUSDT",
        timeframe="1h",
        volume=Decimal("999"),
        volume_unit="BTC",
        notional_usd=Decimal("999000000"),
        provider="binance",
        source="binance-api",
        available_at=datetime(2026, 8, 26, tzinfo=UTC),
        ingested_at=datetime(2026, 8, 25, 2, tzinfo=UTC),
    )

    aggregate = aggregate_btc_derivatives_available_at(
        (*result.records, future_available_funding, future_observation_volume),
        datetime(2026, 8, 25, 1, tzinfo=UTC),
    )

    assert aggregate.funding_rate_avg == Decimal("0.0001")
    assert aggregate.open_interest_by_unit == {"contracts": Decimal("12345.5")}
    assert aggregate.futures_basis_rate_avg == Decimal("0.02")
    assert aggregate.annualized_basis_rate_avg == Decimal("0.18")
    assert aggregate.long_liquidations_usd == Decimal("300000")
    assert aggregate.short_liquidations_usd == Decimal("200000")
    assert aggregate.perp_volume_usd == Decimal("5000000")
    assert aggregate.source_record_count == 6


def test_derivatives_records_reject_availability_before_observation_time() -> None:
    with pytest.raises(ValueError, match="available_at"):
        FundingRate(
            observation_time=datetime(2026, 8, 25, 1, tzinfo=UTC),
            exchange="binance",
            symbol="BTCUSDT",
            instrument="BTCUSDT-PERP",
            funding_rate=Decimal("0.0001"),
            funding_interval_hours=Decimal("8"),
            provider="binance",
            source="binance-api",
            available_at=datetime(2026, 8, 25, tzinfo=UTC),
            ingested_at=datetime(2026, 8, 25, 2, tzinfo=UTC),
        ).as_record()
