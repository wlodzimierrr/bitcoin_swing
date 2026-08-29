from datetime import UTC, datetime, timedelta
from decimal import Decimal

from btc_predictor.data import OhlcvBar
from btc_predictor.research.reference_composite_empirical import (
    ATR_BOOTSTRAP_METHOD_VERSION,
    PRIMARY_METHOD_VERSION,
    _prior_daily_atr_by_hour,
    frozen_candidate_definition,
)


def provider_history(provider: str, *, start: datetime, days: int):
    exchange = "coinbase" if provider == "coinbase" else provider
    symbol = "BTC-USD" if provider == "coinbase" else "BTC/USD"
    return tuple(
        OhlcvBar(
            timestamp=start + timedelta(hours=offset),
            exchange=exchange,
            symbol=symbol,
            timeframe="1h",
            open=Decimal("100"),
            high=Decimal("102"),
            low=Decimal("98"),
            close=Decimal("101"),
            volume=Decimal("1"),
            provider=provider,
            ingested_at=start + timedelta(days=days + 1),
        )
        for offset in range(days * 24)
    )


def test_frozen_definition_keeps_research_and_execution_roles_separate() -> None:
    definition = frozen_candidate_definition()

    assert definition["status"] == "RESEARCH"
    assert definition["primary_candidate_method_version"] == PRIMARY_METHOD_VERSION
    assert definition["raw_source_mutation_allowed"] is False
    assert definition["historical_provider_splicing_allowed"] is False
    assert definition["price_source_policy_change_in_scope"] is False
    assert definition["recommended_future_policy_version_if_approved"] == (
        "PRICE_SOURCE_POLICY_V2"
    )
    assert definition["atr_definition"]["method_version"] == (
        ATR_BOOTSTRAP_METHOD_VERSION
    )
    assert definition["sensitivity_tolerance_atr_grid"] == [
        "0.05",
        "0.10",
        "0.15",
        "0.20",
        "0.30",
    ]


def test_atr_confirmation_uses_only_a_prior_completed_day() -> None:
    start = datetime(2020, 1, 1, tzinfo=UTC)
    histories = {
        provider: provider_history(provider, start=start, days=16)
        for provider in ("bitstamp", "coinbase", "bitfinex")
    }

    trailing = _prior_daily_atr_by_hour(histories)

    assert start + timedelta(days=13, hours=23) not in trailing
    assert trailing[start + timedelta(days=14)] == Decimal("4")
    assert trailing[start + timedelta(days=14, hours=23)] == Decimal("4")
