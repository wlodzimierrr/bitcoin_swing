from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.data import OhlcvBar
from btc_predictor.research import (
    BITSTAMP_PROVIDER_ID,
    COINBASE_PROVIDER_ID,
    COIN_METRICS_COMMUNITY_PROVIDER_ID,
    DEFAULT_PRICE_SOURCE_POLICY,
    PRICE_SOURCE_POLICY_VERSION,
    YFINANCE_PROVIDER_ID,
    PriceSourceDivergenceReview,
    TradePathProbe,
    compare_price_sources,
)


PROVIDER_SERIES = {
    COIN_METRICS_COMMUNITY_PROVIDER_ID: ("coin_metrics_community", "BTC/USD"),
    BITSTAMP_PROVIDER_ID: ("bitstamp", "BTC/USD"),
    COINBASE_PROVIDER_ID: ("coinbase", "BTC-USD"),
    YFINANCE_PROVIDER_ID: ("yfinance", "BTC-USD"),
}


def hourly_bar(
    timestamp: datetime,
    provider_id: str,
    *,
    open_price: str = "100",
    high: str = "101",
    low: str = "99",
    close: str = "100",
    ingested_at: datetime | None = None,
    timeframe: str = "1h",
) -> OhlcvBar:
    exchange, symbol = PROVIDER_SERIES[provider_id]
    return OhlcvBar(
        timestamp=timestamp,
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("1"),
        provider=provider_id,
        ingested_at=ingested_at or timestamp + timedelta(minutes=1),
    )


def hourly_series(
    provider_id: str,
    start: datetime,
    count: int,
    *,
    skip_offsets: set[int] | None = None,
) -> tuple[OhlcvBar, ...]:
    skipped = skip_offsets or set()
    return tuple(
        hourly_bar(start + timedelta(hours=offset), provider_id)
        for offset in range(count)
        if offset not in skipped
    )


def core_provider_series(
    start: datetime,
    count: int,
) -> dict[str, tuple[OhlcvBar, ...]]:
    return {
        provider_id: hourly_series(provider_id, start, count)
        for provider_id in (
            COIN_METRICS_COMMUNITY_PROVIDER_ID,
            BITSTAMP_PROVIDER_ID,
            COINBASE_PROVIDER_ID,
        )
    }


def test_default_policy_persists_provider_roles_and_instrument_provenance() -> None:
    record = DEFAULT_PRICE_SOURCE_POLICY.as_record()
    instruments = {
        instrument["provider_id"]: instrument for instrument in record["instruments"]
    }

    assert record["version"] == PRICE_SOURCE_POLICY_VERSION
    assert (
        record["canonical_reference_provider_id"]
        == COIN_METRICS_COMMUNITY_PROVIDER_ID
    )
    assert record["primary_raw_ohlcv_provider_id"] == BITSTAMP_PROVIDER_ID
    assert (
        record["secondary_validation_fallback_provider_id"]
        == COINBASE_PROVIDER_ID
    )
    assert record["noncanonical_sanity_check_provider_id"] == YFINANCE_PROVIDER_ID
    assert instruments[COIN_METRICS_COMMUNITY_PROVIDER_ID]["symbol"] == "BTC/USD"
    assert (
        instruments[COIN_METRICS_COMMUNITY_PROVIDER_ID]["api_instrument"]
        == "btc-usd"
    )
    assert instruments[BITSTAMP_PROVIDER_ID]["symbol"] == "BTC/USD"
    assert instruments[BITSTAMP_PROVIDER_ID]["api_instrument"] == "btcusd"
    assert instruments[COINBASE_PROVIDER_ID]["symbol"] == "BTC-USD"
    assert instruments[YFINANCE_PROVIDER_ID]["symbol"] == "BTC-USD"
    assert "next_page_url" in instruments[COIN_METRICS_COMMUNITY_PROVIDER_ID][
        "api_practicality"
    ]
    assert "1000 candles" in instruments[BITSTAMP_PROVIDER_ID]["api_practicality"]
    assert "300 candles" in instruments[COINBASE_PROVIDER_ID]["api_practicality"]
    assert "60-day" in instruments[YFINANCE_PROVIDER_ID]["access_constraints"]
    assert "do not provide exchange volume" in instruments[
        COIN_METRICS_COMMUNITY_PROVIDER_ID
    ]["data_semantics"]
    assert instruments[COIN_METRICS_COMMUNITY_PROVIDER_ID]["reference_price_role"]
    assert not instruments[COIN_METRICS_COMMUNITY_PROVIDER_ID]["execution_venue"]
    assert all(
        not instrument["fallback_splicing_allowed"]
        for instrument in instruments.values()
    )
    assert "prohibited" in record["historical_fallback_splicing_rule"].lower()


def test_policy_rejects_historical_fallback_splicing_in_v1() -> None:
    coinbase = next(
        instrument
        for instrument in DEFAULT_PRICE_SOURCE_POLICY.instruments
        if instrument.provider_id == COINBASE_PROVIDER_ID
    )
    changed_instruments = tuple(
        replace(
            instrument,
            fallback_splicing_allowed=True,
            historical_fallback_policy_version="PRICE_SOURCE_POLICY_V2",
        )
        if instrument.provider_id == COINBASE_PROVIDER_ID
        else instrument
        for instrument in DEFAULT_PRICE_SOURCE_POLICY.instruments
    )
    assert not coinbase.fallback_splicing_allowed

    with pytest.raises(
        ValueError,
        match="unversioned historical fallback splicing is prohibited",
    ):
        replace(
            DEFAULT_PRICE_SOURCE_POLICY,
            instruments=changed_instruments,
        ).as_record()


def test_two_year_synchronized_overlap_satisfies_decision_gate() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    hour_count = 2 * 365 * 24
    end = start + timedelta(hours=hour_count - 1)

    report = compare_price_sources(
        core_provider_series(start, hour_count),
        start=start,
        end=end,
        as_of=end + timedelta(hours=1),
    )

    assert report.overlap_bar_count == hour_count
    assert report.overlap_years == Decimal("2")
    assert report.policy_decision_ready
    assert report.reason_codes == ()


def test_comparison_measures_divergence_sensitivity_and_manual_review() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    hour_count = 16 * 24
    event_offset = 30
    event_time = start + timedelta(hours=event_offset)
    provider_bars = core_provider_series(start, hour_count)
    bitstamp_bars = list(provider_bars[BITSTAMP_PROVIDER_ID])
    bitstamp_bars[event_offset] = hourly_bar(
        event_time,
        BITSTAMP_PROVIDER_ID,
        high="110",
        low="94",
        close="105",
    )
    provider_bars[BITSTAMP_PROVIDER_ID] = tuple(bitstamp_bars)
    provider_bars[YFINANCE_PROVIDER_ID] = hourly_series(
        YFINANCE_PROVIDER_ID,
        start + timedelta(hours=hour_count - 2),
        2,
    )
    review = PriceSourceDivergenceReview(
        timestamp=event_time,
        provider_id=BITSTAMP_PROVIDER_ID,
        metric="high",
        disposition="isolated_exchange_wick",
        notes="Synthetic isolated-wick case reviewed for deterministic coverage.",
    )
    end = start + timedelta(hours=hour_count - 1)

    report = compare_price_sources(
        provider_bars,
        start=start,
        end=end,
        as_of=end + timedelta(hours=1),
        minimum_overlap_years=0,
        stop_levels=(Decimal("95"),),
        trade_path_probes=(
            TradePathProbe(
                entry_time=start + timedelta(hours=24),
                exit_time=end,
                entry_price=Decimal("100"),
            ),
        ),
        manual_reviews=(review,),
        top_event_count=1,
    )

    assert report.overlap_bar_count == hour_count
    assert report.close_price_divergence.observation_count == (2 * hour_count) + 2
    assert report.high_price_divergence.max_abs == Decimal("9") / Decimal("101")
    assert report.low_price_divergence.max_abs == Decimal("5") / Decimal("99")
    assert report.extreme_wick_divergence.max_abs is not None
    assert report.daily_return_divergence.observation_count > 0
    assert report.atr_divergence.observation_count > 0
    assert report.stop_touch_difference_count == 1
    assert report.mfe_mae_difference.observation_count > 0
    assert report.top_divergence_events[0].metric == "high"
    assert report.manual_reviews == (review,)
    assert report.policy_decision_ready
    persisted = report.as_record()
    assert persisted["as_of"] == (end + timedelta(hours=1)).isoformat()
    assert persisted["stop_levels"] == ["95"]
    assert persisted["trade_path_probes"][0]["direction"] == "long"
    assert persisted["top_event_count"] == 1


def test_comparison_reports_gaps_duplicates_and_missing_manual_review() -> None:
    start = datetime(2026, 2, 1, tzinfo=UTC)
    hour_count = 48
    provider_bars = core_provider_series(start, hour_count)
    bitstamp_bars = list(
        hourly_series(
            BITSTAMP_PROVIDER_ID,
            start,
            hour_count,
            skip_offsets={10},
        )
    )
    bitstamp_bars.append(
        hourly_bar(
            start + timedelta(hours=11),
            BITSTAMP_PROVIDER_ID,
            high="120",
            ingested_at=start + timedelta(hours=12),
        )
    )
    provider_bars[BITSTAMP_PROVIDER_ID] = tuple(bitstamp_bars)
    coinbase_bars = list(provider_bars[COINBASE_PROVIDER_ID])
    coinbase_bars[20] = hourly_bar(
        start + timedelta(hours=20),
        COINBASE_PROVIDER_ID,
        high="108",
    )
    provider_bars[COINBASE_PROVIDER_ID] = tuple(coinbase_bars)
    end = start + timedelta(hours=hour_count - 1)

    report = compare_price_sources(
        provider_bars,
        start=start,
        end=end,
        as_of=end + timedelta(hours=1),
        minimum_overlap_years=2,
        top_event_count=1,
    )
    profiles = {profile.provider_id: profile for profile in report.series_profiles}

    assert profiles[BITSTAMP_PROVIDER_ID].missing_bar_count == 1
    assert profiles[BITSTAMP_PROVIDER_ID].duplicate_bar_count == 1
    assert report.overlap_bar_count == hour_count - 1
    assert "PRICE_SOURCE_POLICY_OVERLAP_TOO_SHORT" in report.reason_codes
    assert "PRICE_SOURCE_POLICY_MANUAL_REVIEW_MISSING" in report.reason_codes
    assert not report.policy_decision_ready


def test_comparison_fails_safe_when_canonical_provider_is_absent() -> None:
    start = datetime(2026, 3, 1, tzinfo=UTC)
    end = start + timedelta(hours=23)

    report = compare_price_sources(
        {
            BITSTAMP_PROVIDER_ID: hourly_series(BITSTAMP_PROVIDER_ID, start, 24),
            COINBASE_PROVIDER_ID: hourly_series(COINBASE_PROVIDER_ID, start, 24),
        },
        start=start,
        end=end,
        as_of=end + timedelta(hours=1),
        minimum_overlap_years=0,
    )

    assert "PRICE_SOURCE_POLICY_REQUIRED_PROVIDER_MISSING" in report.reason_codes
    assert report.close_price_divergence.observation_count == 0
    assert report.top_divergence_events == ()
    assert not report.policy_decision_ready


def test_comparison_rejects_wrong_provider_provenance_and_timeframe() -> None:
    start = datetime(2026, 4, 1, tzinfo=UTC)
    end = start + timedelta(hours=1)

    with pytest.raises(ValueError, match="key must match"):
        compare_price_sources(
            {BITSTAMP_PROVIDER_ID: hourly_series(COINBASE_PROVIDER_ID, start, 2)},
            start=start,
            end=end,
            as_of=end + timedelta(hours=1),
            minimum_overlap_years=0,
        )

    with pytest.raises(ValueError, match="requires 1h bars"):
        compare_price_sources(
            {
                COIN_METRICS_COMMUNITY_PROVIDER_ID: (
                    hourly_bar(
                        start,
                        COIN_METRICS_COMMUNITY_PROVIDER_ID,
                        timeframe="1d",
                    ),
                ),
            },
            start=start,
            end=end,
            as_of=end + timedelta(hours=1),
            minimum_overlap_years=0,
        )

    wrong_symbol_bar = replace(
        hourly_bar(start, BITSTAMP_PROVIDER_ID),
        symbol="BTC-USD",
    )
    with pytest.raises(ValueError, match="symbol must match policy provenance"):
        compare_price_sources(
            {BITSTAMP_PROVIDER_ID: (wrong_symbol_bar,)},
            start=start,
            end=end,
            as_of=end + timedelta(hours=1),
            minimum_overlap_years=0,
        )
