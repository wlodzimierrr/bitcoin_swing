from datetime import UTC, datetime

import pytest
from sqlalchemy.dialects import postgresql

from btc_predictor.data import (
    SUPPORTED_SERIES_TYPES,
    latest_generic_series_available_at,
)
from btc_predictor.db import GENERIC_SERIES_PRIMARY_KEY, generic_series


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


def test_latest_generic_series_query_filters_to_signal_time() -> None:
    query = latest_generic_series_available_at(datetime(2026, 8, 25, 16, tzinfo=UTC))
    compiled = str(query.compile(dialect=postgresql.dialect()))

    assert "available_at <= " in compiled
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
