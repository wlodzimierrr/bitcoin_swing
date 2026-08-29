from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.data import OhlcvBar
from btc_predictor.research import (
    BITFINEX_PROVIDER_ID,
    BITSTAMP_PROVIDER_ID,
    COINBASE_PROVIDER_ID,
    COIN_METRICS_COMMUNITY_PROVIDER_ID,
    CROSS_VENUE_UNCONFIRMED,
    DEFAULT_PRICE_SOURCE_POLICY,
    DIVERGENCE_TIER_DECISION,
    DIVERGENCE_TIER_PORTFOLIO,
    PRICE_SOURCE_POLICY_VERSION,
    REQUIRED_POLICY_PROVIDER_IDS,
    WICK_ANOMALY_CANDIDATE,
    YFINANCE_PROVIDER_ID,
    CanonicalSourceDecision,
    PriceSourceDivergenceReview,
    PriceSourceOhlcvSnapshot,
    ProviderAccessDiagnostic,
    TradePathProbe,
    compare_price_sources,
)


PROVIDER_SERIES = {
    BITSTAMP_PROVIDER_ID: ("bitstamp", "BTC/USD"),
    COINBASE_PROVIDER_ID: ("coinbase", "BTC-USD"),
    BITFINEX_PROVIDER_ID: ("bitfinex", "BTC/USD"),
    COIN_METRICS_COMMUNITY_PROVIDER_ID: ("coin_metrics_community", "BTC/USD"),
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


def required_provider_series(
    start: datetime,
    count: int,
) -> dict[str, tuple[OhlcvBar, ...]]:
    return {
        provider_id: hourly_series(provider_id, start, count)
        for provider_id in REQUIRED_POLICY_PROVIDER_IDS
    }


def approved_decision(decided_at: datetime) -> CanonicalSourceDecision:
    return CanonicalSourceDecision(
        policy_version=PRICE_SOURCE_POLICY_VERSION,
        provider_id=BITSTAMP_PROVIDER_ID,
        status="approved",
        decided_at=decided_at,
        reviewer="btc019-fixture",
        rationale="Deterministic fixture explicitly approves the candidate.",
    )


def test_v1_policy_persists_provider_roles_and_instrument_provenance() -> None:
    record = DEFAULT_PRICE_SOURCE_POLICY.as_record()
    instruments = {
        instrument["provider_id"]: instrument for instrument in record["instruments"]
    }

    assert record["version"] == PRICE_SOURCE_POLICY_VERSION
    assert record["canonical_candidate_provider_id"] == BITSTAMP_PROVIDER_ID
    assert record["canonical_candidate_status"] == "rejected"
    assert record["canonical_reference_provider_id"] is None
    assert record["primary_raw_ohlcv_provider_id"] == BITSTAMP_PROVIDER_ID
    assert record["required_validation_provider_ids"] == [
        BITSTAMP_PROVIDER_ID,
        COINBASE_PROVIDER_ID,
        BITFINEX_PROVIDER_ID,
    ]
    assert record["secondary_validation_provider_id"] == COINBASE_PROVIDER_ID
    assert record["additional_validation_provider_ids"] == [BITFINEX_PROVIDER_ID]
    assert record["institutional_reference_benchmark_provider_ids"] == [
        COIN_METRICS_COMMUNITY_PROVIDER_ID,
    ]
    assert record["noncanonical_sanity_check_provider_ids"] == [
        YFINANCE_PROVIDER_ID,
    ]
    assert instruments[BITSTAMP_PROVIDER_ID]["api_instrument"] == "btcusd"
    assert instruments[COINBASE_PROVIDER_ID]["api_instrument"] == "BTC-USD"
    assert instruments[BITFINEX_PROVIDER_ID]["api_instrument"] == "tBTCUSD"
    assert (
        instruments[COIN_METRICS_COMMUNITY_PROVIDER_ID]["api_instrument"]
        == "btc-usd"
    )
    assert instruments[BITSTAMP_PROVIDER_ID]["reference_price_role"]
    assert not instruments[BITSTAMP_PROVIDER_ID]["execution_venue"]
    assert instruments[BITFINEX_PROVIDER_ID]["required_for_v1_completion"]
    assert not instruments[COIN_METRICS_COMMUNITY_PROVIDER_ID][
        "required_for_v1_completion"
    ]
    assert not instruments[YFINANCE_PROVIDER_ID]["required_for_v1_completion"]


def test_policy_rejects_unknown_canonical_candidate_status() -> None:
    with pytest.raises(ValueError, match="canonical candidate status"):
        replace(
            DEFAULT_PRICE_SOURCE_POLICY,
            canonical_candidate_status="implicitly_validated",
        ).as_record()


def test_unapproved_candidate_cannot_be_recorded_as_canonical_reference() -> None:
    with pytest.raises(ValueError, match="cannot be the canonical reference"):
        replace(
            DEFAULT_PRICE_SOURCE_POLICY,
            canonical_reference_provider_id=BITSTAMP_PROVIDER_ID,
        ).as_record()


def test_policy_rejects_historical_fallback_splicing_in_v1() -> None:
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

    with pytest.raises(
        ValueError,
        match="unversioned historical fallback splicing is prohibited",
    ):
        replace(
            DEFAULT_PRICE_SOURCE_POLICY,
            instruments=changed_instruments,
        ).as_record()


def test_policy_required_providers_must_be_independent_venues() -> None:
    changed_instruments = tuple(
        replace(instrument, exchange="bitstamp")
        if instrument.provider_id == BITFINEX_PROVIDER_ID
        else instrument
        for instrument in DEFAULT_PRICE_SOURCE_POLICY.instruments
    )

    with pytest.raises(ValueError, match="independent venues"):
        replace(
            DEFAULT_PRICE_SOURCE_POLICY,
            instruments=changed_instruments,
        ).as_record()


def test_three_exchange_two_year_overlap_satisfies_decision_gate() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    hour_count = 2 * 365 * 24
    end = start + timedelta(hours=hour_count - 1)
    as_of = end + timedelta(hours=1)

    report = compare_price_sources(
        required_provider_series(start, hour_count),
        start=start,
        end=end,
        as_of=as_of,
        canonical_source_decision=approved_decision(as_of),
    )

    assert report.required_provider_ids == REQUIRED_POLICY_PROVIDER_IDS
    assert report.overlap_bar_count == hour_count
    assert report.overlap_years == Decimal("2")
    assert report.policy_decision_ready
    assert report.canonical_provider_approved
    assert report.reason_codes == ()
    profiles = {profile.provider_id: profile for profile in report.series_profiles}
    bitstamp_profile = profiles[BITSTAMP_PROVIDER_ID].as_record()
    assert bitstamp_profile["price_source_policy_version"] == (
        PRICE_SOURCE_POLICY_VERSION
    )
    assert bitstamp_profile["price_source_roles"] == [
        "reference_price",
        "primary_raw_ohlcv",
        "validation_provider",
    ]
    assert bitstamp_profile["fallback_used"] is False


def test_coin_metrics_entitlement_unavailable_does_not_fail_v1_gate() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = start + timedelta(hours=47)
    as_of = end + timedelta(hours=1)
    access = ProviderAccessDiagnostic(
        provider_id=COIN_METRICS_COMMUNITY_PROVIDER_ID,
        status="entitlement_unavailable",
        checked_at=as_of,
        details="Catalog advertises history but current credentials cannot retrieve it.",
        catalog_coverage_advertised=True,
        historical_retrieval_entitled=False,
    )

    report = compare_price_sources(
        required_provider_series(start, 48),
        start=start,
        end=end,
        as_of=as_of,
        minimum_overlap_years=0,
        provider_access_diagnostics=(access,),
        canonical_source_decision=approved_decision(as_of),
    )
    access_by_provider = {
        item.provider_id: item for item in report.provider_access_diagnostics
    }

    assert report.policy_decision_ready
    assert access_by_provider[COIN_METRICS_COMMUNITY_PROVIDER_ID] == access
    assert COIN_METRICS_COMMUNITY_PROVIDER_ID not in {
        profile.provider_id for profile in report.series_profiles
    }


def test_optional_coin_metrics_data_still_requires_valid_provenance_and_ohlc() -> None:
    start = datetime(2026, 2, 1, tzinfo=UTC)
    end = start + timedelta(hours=1)
    provider_bars = required_provider_series(start, 2)
    provider_bars[COIN_METRICS_COMMUNITY_PROVIDER_ID] = (
        hourly_bar(
            start,
            COIN_METRICS_COMMUNITY_PROVIDER_ID,
            high="98",
        ),
    )

    with pytest.raises(ValueError, match="impossible OHLC ordering"):
        compare_price_sources(
            provider_bars,
            start=start,
            end=end,
            as_of=end + timedelta(hours=1),
            minimum_overlap_years=0,
        )


def test_yfinance_short_history_does_not_shorten_required_overlap() -> None:
    start = datetime(2026, 3, 1, tzinfo=UTC)
    hour_count = 72
    end = start + timedelta(hours=hour_count - 1)
    as_of = end + timedelta(hours=1)
    provider_bars = required_provider_series(start, hour_count)
    provider_bars[YFINANCE_PROVIDER_ID] = hourly_series(
        YFINANCE_PROVIDER_ID,
        start + timedelta(hours=70),
        2,
    )

    report = compare_price_sources(
        provider_bars,
        start=start,
        end=end,
        as_of=as_of,
        minimum_overlap_years=0,
        canonical_source_decision=approved_decision(as_of),
    )

    assert report.overlap_bar_count == hour_count
    assert report.close_price_divergence.observation_count == (2 * hour_count) + 2
    assert report.policy_decision_ready


def test_comparison_reports_gaps_duplicates_and_missing_manual_review() -> None:
    start = datetime(2026, 4, 1, tzinfo=UTC)
    hour_count = 48
    provider_bars = required_provider_series(start, hour_count)
    bitfinex_bars = list(
        hourly_series(
            BITFINEX_PROVIDER_ID,
            start,
            hour_count,
            skip_offsets={10},
        ),
    )
    bitfinex_bars.append(
        hourly_bar(
            start + timedelta(hours=11),
            BITFINEX_PROVIDER_ID,
            ingested_at=start + timedelta(hours=12),
        ),
    )
    provider_bars[BITFINEX_PROVIDER_ID] = tuple(bitfinex_bars)
    coinbase_bars = list(provider_bars[COINBASE_PROVIDER_ID])
    coinbase_bars[20] = hourly_bar(
        start + timedelta(hours=20),
        COINBASE_PROVIDER_ID,
        high="108",
    )
    provider_bars[COINBASE_PROVIDER_ID] = tuple(coinbase_bars)
    end = start + timedelta(hours=hour_count - 1)
    as_of = end + timedelta(hours=1)

    report = compare_price_sources(
        provider_bars,
        start=start,
        end=end,
        as_of=as_of,
        minimum_overlap_years=0,
        top_event_count=1,
        canonical_source_decision=approved_decision(as_of),
    )
    profiles = {profile.provider_id: profile for profile in report.series_profiles}

    assert profiles[BITFINEX_PROVIDER_ID].missing_bar_count == 1
    assert profiles[BITFINEX_PROVIDER_ID].duplicate_bar_count == 1
    assert report.overlap_bar_count == hour_count - 1
    assert "PRICE_SOURCE_POLICY_MANUAL_REVIEW_MISSING" in report.reason_codes
    assert not report.policy_decision_ready


def test_wick_research_manual_review_and_divergence_tiers_are_persisted() -> None:
    start = datetime(2026, 5, 1, tzinfo=UTC)
    hour_count = 17 * 24
    event_offset = (15 * 24) + 10
    event_time = start + timedelta(hours=event_offset)
    provider_bars = required_provider_series(start, hour_count)
    bitfinex_bars = list(provider_bars[BITFINEX_PROVIDER_ID])
    bitfinex_bars[event_offset] = hourly_bar(
        event_time,
        BITFINEX_PROVIDER_ID,
        high="110",
        low="94",
        close="105",
    )
    provider_bars[BITFINEX_PROVIDER_ID] = tuple(bitfinex_bars)
    end = start + timedelta(hours=hour_count - 1)
    as_of = end + timedelta(hours=1)
    probe = TradePathProbe(
        entry_time=start + timedelta(days=15),
        exit_time=end,
        entry_price=Decimal("100"),
    )

    unreviewed = compare_price_sources(
        provider_bars,
        start=start,
        end=end,
        as_of=as_of,
        minimum_overlap_years=0,
        stop_levels=(Decimal("95"),),
        trade_path_probes=(probe,),
        top_event_count=1,
        canonical_source_decision=approved_decision(as_of),
    )
    wick_context = next(
        item
        for item in unreviewed.cross_venue_wick_diagnostics
        if item.timestamp == event_time and item.provider_id == BITFINEX_PROVIDER_ID
    )
    review = PriceSourceDivergenceReview(
        timestamp=event_time,
        provider_id=BITFINEX_PROVIDER_ID,
        metric="high",
        providers_involved=REQUIRED_POLICY_PROVIDER_IDS,
        canonical_candidate_ohlc=PriceSourceOhlcvSnapshot.from_bar(
            provider_bars[BITSTAMP_PROVIDER_ID][event_offset],
        ),
        validator_ohlc=PriceSourceOhlcvSnapshot.from_bar(
            provider_bars[BITFINEX_PROVIDER_ID][event_offset],
        ),
        cross_provider_median_high=wick_context.median_high,
        cross_provider_median_low=wick_context.median_low,
        cross_provider_median_close=wick_context.median_close,
        atr_normalized_divergence=wick_context.high_atr_divergence,
        event_classification="venue_specific_anomaly",
        swing_impact=False,
        breakout_impact=False,
        reclaim_impact=False,
        stop_touch_impact=True,
        mfe_impact=True,
        mae_impact=True,
        trade_outcome_impact=True,
        review_conclusion="Keep raw candle but do not redefine structure automatically.",
        review_notes="Deterministic isolated-wick fixture.",
        reviewed_at=as_of + timedelta(minutes=5),
    )

    with pytest.raises(ValueError, match="ATR-normalized divergence"):
        compare_price_sources(
            provider_bars,
            start=start,
            end=end,
            as_of=as_of,
            minimum_overlap_years=0,
            stop_levels=(Decimal("95"),),
            trade_path_probes=(probe,),
            manual_reviews=(
                replace(review, atr_normalized_divergence=Decimal("999")),
            ),
            top_event_count=1,
            canonical_source_decision=approved_decision(as_of),
        )

    report = compare_price_sources(
        provider_bars,
        start=start,
        end=end,
        as_of=as_of,
        minimum_overlap_years=0,
        stop_levels=(Decimal("95"),),
        trade_path_probes=(probe,),
        manual_reviews=(review,),
        top_event_count=1,
        canonical_source_decision=approved_decision(as_of),
    )
    tiers = {summary.tier: summary for summary in report.divergence_tiers}

    assert report.policy_decision_ready
    assert report.wick_high_atr_divergence.max_abs == Decimal("4.5")
    assert report.wick_low_atr_divergence.max_abs == Decimal("2.5")
    assert WICK_ANOMALY_CANDIDATE in wick_context.candidate_flags
    assert CROSS_VENUE_UNCONFIRMED in wick_context.candidate_flags
    assert report.stop_touch_difference_count == 1
    assert report.mfe_divergence.max_abs == Decimal("0.09")
    assert report.mae_divergence.max_abs == Decimal("0.05")
    assert [summary.tier for summary in report.divergence_tiers] == [4, 3, 2, 1]
    assert tiers[DIVERGENCE_TIER_PORTFOLIO].event_count > 0
    persisted = report.as_record()
    assert persisted["policy_version"] == PRICE_SOURCE_POLICY_VERSION
    assert persisted["manual_reviews"][0]["stop_touch_impact"]
    assert persisted["manual_reviews"][0]["reviewed_at"] == (
        as_of + timedelta(minutes=5)
    ).isoformat()


def weekly_pattern_series(
    provider_id: str,
    start: datetime,
    *,
    structured: bool,
) -> tuple[OhlcvBar, ...]:
    highs = [103, 104, 105, 110, 105, 104, 103, 116, 104, 103]
    lows = [97, 96, 95, 90, 95, 96, 97, 89, 96, 97]
    closes = [100, 100, 100, 100, 100, 100, 100, 115, 100, 100]
    if not structured:
        highs = [103] * len(highs)
        lows = [97] * len(lows)
        closes = [100] * len(closes)
    bars = []
    for week_index, (high, low, close) in enumerate(zip(highs, lows, closes)):
        for hour in range(7 * 24):
            timestamp = start + timedelta(weeks=week_index, hours=hour)
            bars.append(
                hourly_bar(
                    timestamp,
                    provider_id,
                    open_price="100",
                    high=str(high),
                    low=str(low),
                    close=str(close),
                ),
            )
    return tuple(bars)


def test_structure_breakout_and_reclaim_divergence_are_tier_three() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    provider_bars = {
        BITSTAMP_PROVIDER_ID: weekly_pattern_series(
            BITSTAMP_PROVIDER_ID,
            start,
            structured=True,
        ),
        COINBASE_PROVIDER_ID: weekly_pattern_series(
            COINBASE_PROVIDER_ID,
            start,
            structured=True,
        ),
        BITFINEX_PROVIDER_ID: weekly_pattern_series(
            BITFINEX_PROVIDER_ID,
            start,
            structured=False,
        ),
    }
    end = start + timedelta(weeks=10) - timedelta(hours=1)
    as_of = end + timedelta(hours=1)

    report = compare_price_sources(
        provider_bars,
        start=start,
        end=end,
        as_of=as_of,
        minimum_overlap_years=0,
        top_event_count=1,
        canonical_source_decision=approved_decision(as_of),
    )
    tier_three = next(
        summary
        for summary in report.divergence_tiers
        if summary.tier == DIVERGENCE_TIER_DECISION
    )

    assert report.swing_high_difference_count > 0
    assert report.swing_low_difference_count > 0
    assert report.breakout_difference_count > 0
    assert report.reclaim_difference_count > 0
    assert tier_three.category == "DECISION_DIVERGENCE"
    assert tier_three.event_count > 0


def test_required_provider_outage_fails_but_optional_access_does_not() -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    end = start + timedelta(hours=23)
    as_of = end + timedelta(hours=1)
    access = (
        ProviderAccessDiagnostic(
            provider_id=BITFINEX_PROVIDER_ID,
            status="provider_outage",
            checked_at=as_of,
            details="Bitfinex endpoint unavailable for requested window.",
        ),
        ProviderAccessDiagnostic(
            provider_id=COIN_METRICS_COMMUNITY_PROVIDER_ID,
            status="entitlement_unavailable",
            checked_at=as_of,
            details="Optional institutional history is not entitled.",
            catalog_coverage_advertised=True,
            historical_retrieval_entitled=False,
        ),
    )

    report = compare_price_sources(
        {
            BITSTAMP_PROVIDER_ID: hourly_series(BITSTAMP_PROVIDER_ID, start, 24),
            COINBASE_PROVIDER_ID: hourly_series(COINBASE_PROVIDER_ID, start, 24),
        },
        start=start,
        end=end,
        as_of=as_of,
        minimum_overlap_years=0,
        provider_access_diagnostics=access,
        canonical_source_decision=approved_decision(as_of),
    )

    assert "PRICE_SOURCE_POLICY_REQUIRED_PROVIDER_MISSING" in report.reason_codes
    assert not report.policy_decision_ready


def test_canonical_decision_and_manual_reviews_are_required_explicitly() -> None:
    start = datetime(2026, 7, 1, tzinfo=UTC)
    end = start + timedelta(hours=23)
    provider_bars = required_provider_series(start, 24)
    bitfinex = list(provider_bars[BITFINEX_PROVIDER_ID])
    bitfinex[5] = hourly_bar(
        start + timedelta(hours=5),
        BITFINEX_PROVIDER_ID,
        high="105",
    )
    provider_bars[BITFINEX_PROVIDER_ID] = tuple(bitfinex)

    report = compare_price_sources(
        provider_bars,
        start=start,
        end=end,
        as_of=end + timedelta(hours=1),
        minimum_overlap_years=0,
        top_event_count=1,
    )

    assert "PRICE_SOURCE_POLICY_MANUAL_REVIEW_MISSING" in report.reason_codes
    assert "PRICE_SOURCE_POLICY_CANONICAL_DECISION_MISSING" in report.reason_codes
    assert not report.policy_decision_ready


def test_trade_probe_stop_touch_is_point_in_time_and_persisted() -> None:
    start = datetime(2026, 8, 1, tzinfo=UTC)
    end = start + timedelta(hours=2)
    provider_bars = required_provider_series(start, 3)
    coinbase = list(provider_bars[COINBASE_PROVIDER_ID])
    coinbase[1] = hourly_bar(
        start + timedelta(hours=1),
        COINBASE_PROVIDER_ID,
        low="94",
    )
    provider_bars[COINBASE_PROVIDER_ID] = tuple(coinbase)
    probe = TradePathProbe(
        entry_time=start,
        exit_time=end,
        entry_price=Decimal("100"),
        stop_level=Decimal("95"),
    )

    report = compare_price_sources(
        provider_bars,
        start=start,
        end=end,
        as_of=end + timedelta(hours=1),
        minimum_overlap_years=0,
        trade_path_probes=(probe,),
        canonical_source_decision=approved_decision(end + timedelta(hours=1)),
    )

    assert report.stop_touch_difference_count == 1
    assert report.trade_path_probes[0].as_record()["stop_level"] == "95"
