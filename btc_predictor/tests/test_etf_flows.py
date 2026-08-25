from datetime import UTC, datetime

import pytest
from sqlalchemy.dialects import postgresql

from btc_predictor.data import latest_etf_flows_available_at
from btc_predictor.db import ETF_FLOWS_PRIMARY_KEY, etf_flows


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
