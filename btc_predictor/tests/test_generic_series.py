from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.dialects import postgresql

from btc_predictor.data import (
    MACRO_SERIES_IDS,
    SUPPORTED_SERIES_TYPES,
    MacroDataCollectionRequest,
    build_generic_series_insert_ignore,
    collect_macro_data,
    expected_macro_observation_dates,
    latest_generic_series_available_at,
    latest_macro_series_available_at,
    missing_macro_observation_dates,
)
from btc_predictor.db import GENERIC_SERIES_PRIMARY_KEY, generic_series


class RecordingConnection:
    def __init__(self) -> None:
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)


class StaticMacroProvider:
    def __init__(self, rows):
        self.rows = rows
        self.calls = 0

    def fetch_macro_series(self, **kwargs):
        self.calls += 1
        assert kwargs["series_ids"] == MACRO_SERIES_IDS
        assert kwargs["start"] == datetime(2026, 8, 24, tzinfo=UTC)
        assert kwargs["end"] == datetime(2026, 8, 26, tzinfo=UTC)
        return self.rows


class FlakyMacroProvider(StaticMacroProvider):
    def fetch_macro_series(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary macro provider outage")
        return self.rows


def macro_request() -> MacroDataCollectionRequest:
    return MacroDataCollectionRequest(
        provider="fred",
        source="fred-api",
        start=datetime(2026, 8, 24, tzinfo=UTC),
        end=datetime(2026, 8, 26, tzinfo=UTC),
        max_attempts=2,
    )


def macro_rows():
    return (
        {
            "series_id": "VIX",
            "observation_time": datetime(2026, 8, 24, 1, tzinfo=timezone(timedelta(hours=1))),
            "value": "14.2",
            "available_at": datetime(2026, 8, 24, 22, tzinfo=UTC),
        },
        {
            "series_id": "DXY",
            "series_type": "market_proxy",
            "observation_time": datetime(2026, 8, 24, tzinfo=UTC),
            "value": Decimal("103.5"),
            "unit": "index_points",
            "revision": "v2",
            "available_at": datetime(2026, 8, 24, 22, tzinfo=UTC),
        },
        {
            "series_id": "NASDAQ_PROXY",
            "observation_time": datetime(2026, 8, 24, tzinfo=UTC),
            "value": "18000",
            "available_at": datetime(2026, 8, 24, 22, tzinfo=UTC),
        },
        {
            "series_id": "US_2Y_YIELD",
            "observation_time": datetime(2026, 8, 24, tzinfo=UTC),
            "value": "4.25",
            "available_at": datetime(2026, 8, 24, 22, tzinfo=UTC),
        },
        {
            "series_id": "REAL_YIELD_PROXY",
            "observation_time": datetime(2026, 8, 26, tzinfo=UTC),
            "value": "1.8",
            "available_at": datetime(2026, 8, 26, 22, tzinfo=UTC),
        },
    )


def test_generic_series_primary_key_preserves_historical_revisions() -> None:
    assert GENERIC_SERIES_PRIMARY_KEY == (
        "series_id",
        "observation_time",
        "provider",
        "revision",
        "available_at",
    )


def test_generic_series_supports_macro_liquidity_onchain_and_proxies() -> None:
    assert SUPPORTED_SERIES_TYPES == ("macro", "liquidity", "onchain", "market_proxy")
    for column_name in (
        "series_id",
        "series_type",
        "observation_time",
        "value",
        "unit",
        "provider",
        "revision",
        "available_at",
        "ingested_at",
    ):
        assert column_name in generic_series.c

    assert generic_series.c.observation_time.type.timezone is True
    assert generic_series.c.available_at.type.timezone is True
    assert generic_series.c.ingested_at.type.timezone is True


def test_macro_candidate_series_are_configured() -> None:
    assert MACRO_SERIES_IDS == (
        "VIX",
        "DXY",
        "NASDAQ_PROXY",
        "US_2Y_YIELD",
        "REAL_YIELD_PROXY",
    )


def test_latest_generic_series_query_filters_to_signal_time() -> None:
    query = latest_generic_series_available_at(datetime(2026, 8, 25, 16, tzinfo=UTC))
    compiled = str(query.compile(dialect=postgresql.dialect()))

    assert "available_at <= " in compiled
    assert "observation_time <= " in compiled
    assert "row_number() OVER" in compiled
    assert "PARTITION BY raw.generic_series.series_id" in compiled
    assert "revision_rank = " in compiled


def test_latest_generic_series_query_can_filter_series_ids_and_types() -> None:
    query = latest_generic_series_available_at(
        datetime(2026, 8, 25, 16, tzinfo=UTC),
        series_ids=("VIX", "DXY"),
        series_types=("macro", "market_proxy"),
    )
    compiled = str(query.compile(dialect=postgresql.dialect()))

    assert "series_id IN" in compiled
    assert "series_type IN" in compiled


def test_latest_generic_series_query_rejects_unsupported_series_type() -> None:
    with pytest.raises(ValueError, match="Unsupported series types"):
        latest_generic_series_available_at(
            datetime(2026, 8, 25, 16, tzinfo=UTC),
            series_types=("sentiment",),
        )


def test_latest_generic_series_query_requires_utc_signal_time() -> None:
    with pytest.raises(ValueError, match="UTC"):
        latest_generic_series_available_at(datetime(2026, 8, 25, 16))


def test_latest_macro_series_query_filters_to_candidate_series() -> None:
    query = latest_macro_series_available_at(datetime(2026, 8, 25, 16, tzinfo=UTC))
    compiled = str(query.compile(dialect=postgresql.dialect()))

    assert "series_id IN" in compiled
    assert "series_type IN" in compiled
    assert "available_at <= " in compiled
    assert "observation_time <= " in compiled


def test_collect_macro_data_loads_candidate_series_and_normalizes_provider_rows() -> None:
    provider = FlakyMacroProvider(macro_rows())
    connection = RecordingConnection()

    result = collect_macro_data(
        provider,
        connection,
        macro_request(),
        ingested_at=datetime(2026, 8, 27, 12, tzinfo=UTC),
    )

    assert provider.calls == 2
    assert result.provider_attempts == 2
    assert len(result.observations) == 5
    assert result.observations[0].series_id == "DXY"
    assert result.observations[0].revision == "v2"
    assert result.observations[0].value == Decimal("103.5")
    assert result.observations[1].series_id == "NASDAQ_PROXY"
    assert result.observations[2].series_id == "US_2Y_YIELD"
    assert result.observations[3].series_id == "VIX"
    assert result.observations[3].observation_time == datetime(2026, 8, 24, tzinfo=UTC)
    assert result.observations[4].series_id == "REAL_YIELD_PROXY"
    assert len(connection.statements) == 1


def test_generic_series_insert_ignore_is_idempotent_without_changing_existing_raw_records() -> None:
    result = collect_macro_data(
        StaticMacroProvider(macro_rows()),
        RecordingConnection(),
        macro_request(),
        ingested_at=datetime(2026, 8, 27, 12, tzinfo=UTC),
    )
    statement = build_generic_series_insert_ignore(result.observations)
    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "INSERT INTO raw.generic_series" in compiled
    assert "ON CONFLICT (series_id, observation_time, provider, revision, available_at) DO NOTHING" in compiled
    assert "DO UPDATE SET" not in compiled


def test_expected_macro_observation_dates_excludes_weekends_and_known_holidays() -> None:
    assert expected_macro_observation_dates(
        start=date(2026, 8, 21),
        end=date(2026, 8, 26),
        market_holidays={date(2026, 8, 24)},
    ) == (
        date(2026, 8, 21),
        date(2026, 8, 25),
        date(2026, 8, 26),
    )


def test_collect_macro_data_reports_missing_observation_dates_by_series() -> None:
    result = collect_macro_data(
        StaticMacroProvider(macro_rows()),
        RecordingConnection(),
        macro_request(),
        ingested_at=datetime(2026, 8, 27, 12, tzinfo=UTC),
    )

    assert result.missing_observation_dates["VIX"] == (
        date(2026, 8, 25),
        date(2026, 8, 26),
    )
    assert result.missing_observation_dates["REAL_YIELD_PROXY"] == (
        date(2026, 8, 24),
        date(2026, 8, 25),
    )


def test_missing_macro_observation_dates_handles_empty_provider_response_explicitly() -> None:
    assert missing_macro_observation_dates(
        (),
        series_ids=("VIX",),
        start=date(2026, 8, 24),
        end=date(2026, 8, 25),
    ) == {"VIX": (date(2026, 8, 24), date(2026, 8, 25))}


def test_collect_macro_data_rejects_unexpected_series() -> None:
    rows = (
        {
            "series_id": "UNREQUESTED",
            "observation_time": datetime(2026, 8, 24, tzinfo=UTC),
            "value": "1",
            "series_type": "macro",
            "unit": "index_points",
            "available_at": datetime(2026, 8, 24, 22, tzinfo=UTC),
        },
    )

    with pytest.raises(ValueError, match="unexpected macro series"):
        collect_macro_data(
            StaticMacroProvider(rows),
            RecordingConnection(),
            macro_request(),
            ingested_at=datetime(2026, 8, 27, 12, tzinfo=UTC),
        )


def test_macro_observations_reject_future_availability_state() -> None:
    rows = (
        {
            "series_id": "VIX",
            "observation_time": datetime(2026, 8, 25, 22, tzinfo=UTC),
            "value": "15",
            "available_at": datetime(2026, 8, 25, 21, tzinfo=UTC),
        },
    )

    with pytest.raises(ValueError, match="available_at"):
        collect_macro_data(
            StaticMacroProvider(rows),
            RecordingConnection(),
            macro_request(),
            ingested_at=datetime(2026, 8, 27, 12, tzinfo=UTC),
        )
