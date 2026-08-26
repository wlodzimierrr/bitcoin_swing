from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.dialects import postgresql

from btc_predictor.data import (
    EtfFlowCollectionRequest,
    build_etf_flows_insert_ignore,
    collect_etf_flows,
    expected_etf_publication_dates,
    latest_etf_flows_available_at,
    missing_etf_publication_dates,
)
from btc_predictor.db import ETF_FLOWS_PRIMARY_KEY, etf_flows


class RecordingConnection:
    def __init__(self) -> None:
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)


class StaticEtfFlowProvider:
    def __init__(self, rows):
        self.rows = rows
        self.calls = 0

    def fetch_etf_flows(self, **kwargs):
        self.calls += 1
        assert kwargs["funds"] == ("IBIT", "FBTC")
        assert kwargs["start"] == date(2026, 8, 24)
        assert kwargs["end"] == date(2026, 8, 26)
        return self.rows


class FlakyEtfFlowProvider(StaticEtfFlowProvider):
    def fetch_etf_flows(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary ETF provider outage")
        return self.rows


def etf_request() -> EtfFlowCollectionRequest:
    return EtfFlowCollectionRequest(
        funds=("IBIT", "FBTC"),
        provider="farside",
        source="farside-dashboard",
        start=date(2026, 8, 24),
        end=date(2026, 8, 26),
        max_attempts=2,
    )


def etf_rows():
    return (
        {
            "fund": "IBIT",
            "observation_date": date(2026, 8, 24),
            "flow": "125000000",
            "flow_unit": "USD",
            "aum": "89000000000",
            "aum_unit": "USD",
            "available_at": datetime(2026, 8, 25, 1, tzinfo=timezone(timedelta(hours=1))),
        },
        {
            "fund": "FBTC",
            "observation_date": "2026-08-24",
            "flow_usd": "-10000000",
            "aum_usd": None,
            "revision": "v2",
            "available_at": datetime(2026, 8, 25, tzinfo=UTC),
        },
        {
            "fund": "IBIT",
            "observation_date": date(2026, 8, 26),
            "flow_usd": "25000000",
            "aum_usd": "89500000000",
            "available_at": datetime(2026, 8, 27, tzinfo=UTC),
        },
    )


def test_etf_flow_primary_key_represents_historical_revisions() -> None:
    assert ETF_FLOWS_PRIMARY_KEY == (
        "fund",
        "observation_date",
        "provider",
        "revision",
        "available_at",
    )


def test_etf_flow_table_preserves_required_source_fields() -> None:
    for column_name in (
        "fund",
        "observation_date",
        "flow_usd",
        "aum_usd",
        "source",
        "available_at",
    ):
        assert column_name in etf_flows.c

    assert etf_flows.c.aum_usd.nullable is True
    assert etf_flows.c.available_at.type.timezone is True
    assert etf_flows.c.ingested_at.type.timezone is True


def test_latest_etf_flows_query_filters_to_signal_time() -> None:
    query = latest_etf_flows_available_at(datetime(2026, 8, 25, 16, tzinfo=UTC))
    compiled = str(query.compile(dialect=postgresql.dialect()))

    assert "available_at <= " in compiled
    assert "row_number() OVER" in compiled
    assert "PARTITION BY raw.etf_flows.fund" in compiled
    assert "revision_rank = " in compiled


def test_latest_etf_flows_query_requires_utc_signal_time() -> None:
    with pytest.raises(ValueError, match="UTC"):
        latest_etf_flows_available_at(datetime(2026, 8, 25, 16))


def test_collect_etf_flows_loads_daily_flows_and_normalizes_aum() -> None:
    provider = FlakyEtfFlowProvider(etf_rows())
    connection = RecordingConnection()

    result = collect_etf_flows(
        provider,
        connection,
        etf_request(),
        ingested_at=datetime(2026, 8, 27, 12, tzinfo=UTC),
    )

    assert provider.calls == 2
    assert result.provider_attempts == 2
    assert len(result.flows) == 3
    assert result.flows[0].fund == "FBTC"
    assert result.flows[0].flow_usd == Decimal("-10000000")
    assert result.flows[0].aum_usd is None
    assert result.flows[0].revision == "v2"
    assert result.flows[1].fund == "IBIT"
    assert result.flows[1].flow_usd == Decimal("125000000")
    assert result.flows[1].aum_usd == Decimal("89000000000")
    assert result.flows[1].available_at == datetime(2026, 8, 25, tzinfo=UTC)
    assert len(connection.statements) == 1


def test_etf_flow_insert_ignore_is_idempotent_without_changing_existing_raw_records() -> None:
    result = collect_etf_flows(
        StaticEtfFlowProvider(etf_rows()),
        RecordingConnection(),
        etf_request(),
        ingested_at=datetime(2026, 8, 27, 12, tzinfo=UTC),
    )
    statement = build_etf_flows_insert_ignore(result.flows)
    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "INSERT INTO raw.etf_flows" in compiled
    assert "ON CONFLICT (fund, observation_date, provider, revision, available_at) DO NOTHING" in compiled
    assert "DO UPDATE SET" not in compiled


def test_expected_etf_publication_dates_excludes_weekends_and_known_holidays() -> None:
    assert expected_etf_publication_dates(
        start=date(2026, 8, 21),
        end=date(2026, 8, 26),
        market_holidays={date(2026, 8, 24)},
    ) == (
        date(2026, 8, 21),
        date(2026, 8, 25),
        date(2026, 8, 26),
    )


def test_collect_etf_flows_reports_missing_publication_days_by_fund() -> None:
    result = collect_etf_flows(
        StaticEtfFlowProvider(etf_rows()),
        RecordingConnection(),
        etf_request(),
        ingested_at=datetime(2026, 8, 27, 12, tzinfo=UTC),
    )

    assert result.missing_publication_dates == {
        "IBIT": (date(2026, 8, 25),),
        "FBTC": (date(2026, 8, 25), date(2026, 8, 26)),
    }


def test_missing_etf_publication_dates_handles_empty_provider_response_explicitly() -> None:
    assert missing_etf_publication_dates(
        (),
        funds=("IBIT",),
        start=date(2026, 8, 24),
        end=date(2026, 8, 25),
    ) == {"IBIT": (date(2026, 8, 24), date(2026, 8, 25))}


def test_collect_etf_flows_rejects_non_usd_money_without_silent_conversion() -> None:
    rows = (
        {
            "fund": "IBIT",
            "observation_date": date(2026, 8, 24),
            "flow": "100",
            "flow_unit": "EUR",
            "available_at": datetime(2026, 8, 25, tzinfo=UTC),
        },
    )

    with pytest.raises(ValueError, match="USD"):
        collect_etf_flows(
            StaticEtfFlowProvider(rows),
            RecordingConnection(),
            etf_request(),
            ingested_at=datetime(2026, 8, 27, 12, tzinfo=UTC),
        )
