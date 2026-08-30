"""BTC-019 correctness and reproducibility audit regressions.

Each test group maps to one numbered item of the BTC-019 implementation audit:
point-in-time provenance, optional-provider isolation, revision selection,
isolated-wick materiality, trade-path truncation, percentile convention, empty
provider provenance, and structural level identity.
"""

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
    CROSS_VENUE_CONFIRMED,
    CROSS_VENUE_UNCONFIRMED,
    PRICE_SOURCE_POLICY_VERSION,
    REQUIRED_POLICY_PROVIDER_IDS,
    WICK_ANOMALY_ATR_THRESHOLD,
    WICK_ANOMALY_CANDIDATE,
    YFINANCE_PROVIDER_ID,
    CanonicalSourceDecision,
    ProviderAccessDiagnostic,
    TradePathProbe,
    compare_price_sources,
)
from btc_predictor.research.price_source_policy import (
    _bars_by_timestamp,
    _nearest_rank_percentile,
)
from btc_predictor.research.reference_composite import (
    DEFAULT_TWO_PROVIDER_RANGE_DISAGREEMENT_ATR,
)

from btc_predictor.tests.test_price_source_policy import (
    approved_decision,
    hourly_bar,
    hourly_series,
    required_provider_series,
)


WICK_HISTORY_HOURS = 17 * 24


def baseline_window(
    start: datetime,
    hour_count: int,
) -> tuple[datetime, datetime]:
    end = start + timedelta(hours=hour_count - 1)
    return end, end + timedelta(hours=1)


def run_report(
    provider_bars: dict[str, tuple[OhlcvBar, ...]],
    *,
    start: datetime,
    end: datetime,
    as_of: datetime,
    **kwargs: object,
):
    return compare_price_sources(
        provider_bars,
        start=start,
        end=end,
        as_of=as_of,
        minimum_overlap_years=0,
        canonical_source_decision=approved_decision(as_of),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Item 1 - point-in-time provenance must respect as_of
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("offset_minutes", [-60, 0])
def test_decision_recorded_at_or_before_as_of_is_accepted(
    offset_minutes: int,
) -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    end, as_of = baseline_window(start, 72)
    provider_bars = required_provider_series(start, 72)
    decision = CanonicalSourceDecision(
        policy_version=PRICE_SOURCE_POLICY_VERSION,
        provider_id=BITSTAMP_PROVIDER_ID,
        status="approved",
        decided_at=as_of + timedelta(minutes=offset_minutes),
        reviewer="btc019-audit",
        rationale="Decision recorded at or before the historical as_of.",
    )

    report = compare_price_sources(
        provider_bars,
        start=start,
        end=end,
        as_of=as_of,
        minimum_overlap_years=0,
        canonical_source_decision=decision,
    )

    assert report.policy_decision_ready


def test_decision_recorded_after_as_of_is_rejected() -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    end, as_of = baseline_window(start, 72)
    provider_bars = required_provider_series(start, 72)
    decision = CanonicalSourceDecision(
        policy_version=PRICE_SOURCE_POLICY_VERSION,
        provider_id=BITSTAMP_PROVIDER_ID,
        status="approved",
        decided_at=as_of + timedelta(microseconds=1),
        reviewer="btc019-audit",
        rationale="Decision recorded after the historical as_of.",
    )

    with pytest.raises(ValueError, match="decided_at is after as_of"):
        compare_price_sources(
            provider_bars,
            start=start,
            end=end,
            as_of=as_of,
            minimum_overlap_years=0,
            canonical_source_decision=decision,
        )


@pytest.mark.parametrize("offset_minutes", [-60, 0])
def test_access_diagnostic_at_or_before_as_of_is_accepted(
    offset_minutes: int,
) -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    end, as_of = baseline_window(start, 72)
    provider_bars = required_provider_series(start, 72)
    diagnostic = ProviderAccessDiagnostic(
        provider_id=COIN_METRICS_COMMUNITY_PROVIDER_ID,
        status="entitlement_unavailable",
        checked_at=as_of + timedelta(minutes=offset_minutes),
        details="Entitlement checked at or before the historical as_of.",
    )

    report = run_report(
        provider_bars,
        start=start,
        end=end,
        as_of=as_of,
        provider_access_diagnostics=(diagnostic,),
    )

    assert report.policy_decision_ready


def test_access_diagnostic_after_as_of_is_rejected() -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    end, as_of = baseline_window(start, 72)
    provider_bars = required_provider_series(start, 72)
    diagnostic = ProviderAccessDiagnostic(
        provider_id=COIN_METRICS_COMMUNITY_PROVIDER_ID,
        status="entitlement_unavailable",
        checked_at=as_of + timedelta(microseconds=1),
        details="Entitlement checked after the historical as_of.",
    )

    with pytest.raises(ValueError, match="checked_at .* is after as_of"):
        run_report(
            provider_bars,
            start=start,
            end=end,
            as_of=as_of,
            provider_access_diagnostics=(diagnostic,),
        )


def wick_fixture() -> tuple[dict[str, tuple[OhlcvBar, ...]], datetime, datetime, datetime, int]:
    start = datetime(2026, 5, 1, tzinfo=UTC)
    event_offset = (15 * 24) + 10
    provider_bars = required_provider_series(start, WICK_HISTORY_HOURS)
    bitfinex_bars = list(provider_bars[BITFINEX_PROVIDER_ID])
    bitfinex_bars[event_offset] = hourly_bar(
        start + timedelta(hours=event_offset),
        BITFINEX_PROVIDER_ID,
        high="110",
        low="94",
        close="105",
    )
    provider_bars[BITFINEX_PROVIDER_ID] = tuple(bitfinex_bars)
    end, as_of = baseline_window(start, WICK_HISTORY_HOURS)
    return provider_bars, start, end, as_of, event_offset


def test_manual_review_after_as_of_is_rejected() -> None:
    from btc_predictor.tests.test_price_source_policy import (
        PriceSourceDivergenceReview,
        PriceSourceOhlcvSnapshot,
    )

    provider_bars, start, end, as_of, event_offset = wick_fixture()
    event_time = start + timedelta(hours=event_offset)
    unreviewed = run_report(
        provider_bars,
        start=start,
        end=end,
        as_of=as_of,
        top_event_count=1,
    )
    context = next(
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
        cross_provider_median_high=context.median_high,
        cross_provider_median_low=context.median_low,
        cross_provider_median_close=context.median_close,
        atr_normalized_divergence=context.high_atr_divergence,
        event_classification="venue_specific_anomaly",
        swing_impact=False,
        breakout_impact=False,
        reclaim_impact=False,
        stop_touch_impact=False,
        mfe_impact=False,
        mae_impact=False,
        trade_outcome_impact=False,
        review_conclusion="Audit fixture review.",
        review_notes="Audit fixture review notes.",
        reviewed_at=as_of,
    )

    accepted = run_report(
        provider_bars,
        start=start,
        end=end,
        as_of=as_of,
        manual_reviews=(review,),
        top_event_count=1,
    )
    assert accepted.policy_decision_ready

    earlier = run_report(
        provider_bars,
        start=start,
        end=end,
        as_of=as_of,
        manual_reviews=(replace(review, reviewed_at=as_of - timedelta(hours=1)),),
        top_event_count=1,
    )
    assert earlier.policy_decision_ready

    with pytest.raises(ValueError, match="reviewed_at .* is after as_of"):
        run_report(
            provider_bars,
            start=start,
            end=end,
            as_of=as_of,
            manual_reviews=(
                replace(review, reviewed_at=as_of + timedelta(microseconds=1)),
            ),
            top_event_count=1,
        )


# ---------------------------------------------------------------------------
# Item 2 - optional providers must not move a V1 gate
# ---------------------------------------------------------------------------


def decision_driving_fingerprint(report) -> dict[str, object]:
    """Every V1 approval- and readiness-driving output of the comparison."""

    return {
        "policy_decision_ready": report.policy_decision_ready,
        "reason_codes": report.reason_codes,
        "overlap_bar_count": report.overlap_bar_count,
        "close": report.close_price_divergence.as_record(),
        "high": report.high_price_divergence.as_record(),
        "low": report.low_price_divergence.as_record(),
        "wick": report.extreme_wick_divergence.as_record(),
        "daily_return": report.daily_return_divergence.as_record(),
        "atr": report.atr_divergence.as_record(),
        "wick_high_atr": report.wick_high_atr_divergence.as_record(),
        "wick_low_atr": report.wick_low_atr_divergence.as_record(),
        "swing_high": report.swing_high_difference_count,
        "swing_low": report.swing_low_difference_count,
        "swing_level": report.swing_level_difference_count,
        "breakout": report.breakout_difference_count,
        "reclaim": report.reclaim_difference_count,
        "stop_touch": report.stop_touch_difference_count,
        "mfe": report.mfe_divergence.as_record(),
        "mae": report.mae_divergence.as_record(),
        "tiers": tuple(summary.as_record()["event_count"] for summary in report.divergence_tiers),
        "top_events": tuple(
            event.as_record() for event in report.top_divergence_events
        ),
        "wick_diagnostics": tuple(
            diagnostic.as_record()
            for diagnostic in report.cross_venue_wick_diagnostics
        ),
    }


def extreme_optional_series(
    provider_id: str,
    start: datetime,
    count: int,
) -> tuple[OhlcvBar, ...]:
    """A deliberately extreme optional series that must change no V1 metric."""

    return tuple(
        hourly_bar(
            start + timedelta(hours=offset),
            provider_id,
            open_price="9000",
            high="99999",
            low="1",
            close="9000",
        )
        for offset in range(count)
    )


@pytest.mark.parametrize(
    "optional_provider_id",
    [YFINANCE_PROVIDER_ID, COIN_METRICS_COMMUNITY_PROVIDER_ID],
)
def test_extreme_optional_provider_changes_no_v1_decision_metric(
    optional_provider_id: str,
) -> None:
    provider_bars, start, end, as_of, _ = wick_fixture()
    probe = TradePathProbe(
        entry_time=start + timedelta(days=15),
        exit_time=end,
        entry_price=Decimal("100"),
        stop_level=Decimal("95"),
    )
    kwargs = {
        "stop_levels": (Decimal("95"),),
        "trade_path_probes": (probe,),
        "top_event_count": 5,
    }

    without_optional = run_report(
        dict(provider_bars),
        start=start,
        end=end,
        as_of=as_of,
        **kwargs,
    )
    contaminated = dict(provider_bars)
    contaminated[optional_provider_id] = extreme_optional_series(
        optional_provider_id,
        start,
        WICK_HISTORY_HOURS,
    )
    with_optional = run_report(
        contaminated,
        start=start,
        end=end,
        as_of=as_of,
        **kwargs,
    )

    assert decision_driving_fingerprint(with_optional) == (
        decision_driving_fingerprint(without_optional)
    )
    # The optional provider stays auditable even though it drives nothing.
    profiles = {
        profile.provider_id: profile for profile in with_optional.series_profiles
    }
    assert optional_provider_id in profiles
    assert profiles[optional_provider_id].bar_count == WICK_HISTORY_HOURS
    assert optional_provider_id not in with_optional.required_provider_ids


# ---------------------------------------------------------------------------
# Item 3 - revision selection must pick the latest revision known at as_of
# ---------------------------------------------------------------------------


def test_latest_revision_known_at_as_of_wins() -> None:
    timestamp = datetime(2026, 7, 1, 10, tzinfo=UTC)
    first = hourly_bar(
        timestamp,
        BITSTAMP_PROVIDER_ID,
        close="100",
        high="101",
        ingested_at=timestamp + timedelta(minutes=5),
    )
    revised = hourly_bar(
        timestamp,
        BITSTAMP_PROVIDER_ID,
        close="102",
        high="103",
        ingested_at=timestamp + timedelta(minutes=20),
    )

    selected = _bars_by_timestamp((first, revised))[timestamp]
    assert selected.close == Decimal("102")
    # Input ordering must not change the winner.
    assert _bars_by_timestamp((revised, first))[timestamp].close == Decimal("102")


def test_as_of_selects_the_revision_known_at_that_time() -> None:
    start = datetime(2026, 7, 1, tzinfo=UTC)
    hour_count = 72
    end = start + timedelta(hours=hour_count - 1)
    revised_timestamp = start + timedelta(hours=10)
    provider_bars = required_provider_series(start, hour_count)
    bitstamp = list(provider_bars[BITSTAMP_PROVIDER_ID])
    bitstamp.append(
        hourly_bar(
            revised_timestamp,
            BITSTAMP_PROVIDER_ID,
            open_price="100",
            high="106",
            low="99",
            close="105",
            ingested_at=revised_timestamp + timedelta(minutes=20),
        ),
    )
    provider_bars[BITSTAMP_PROVIDER_ID] = tuple(bitstamp)

    early_as_of = end + timedelta(hours=1)
    early = run_report(
        provider_bars,
        start=start,
        end=end,
        as_of=early_as_of,
    )
    # Both revisions are visible well after the window, so the later one wins.
    assert early.close_price_divergence.max_abs > Decimal("0")

    # Restricting to the first revision's ingestion time hides the revision.
    only_first = {
        provider_id: tuple(
            bar
            for bar in bars
            if bar.ingested_at <= revised_timestamp + timedelta(minutes=6)
        )
        for provider_id, bars in provider_bars.items()
    }
    unrevised = run_report(
        only_first,
        start=start,
        end=end,
        as_of=early_as_of,
    )
    assert unrevised.close_price_divergence.max_abs == Decimal("0")


def test_identical_duplicate_bars_collapse_deterministically() -> None:
    timestamp = datetime(2026, 7, 1, 10, tzinfo=UTC)
    bar = hourly_bar(
        timestamp,
        BITSTAMP_PROVIDER_ID,
        ingested_at=timestamp + timedelta(minutes=5),
    )

    resolved = _bars_by_timestamp((bar, replace(bar)))
    assert len(resolved) == 1
    assert resolved[timestamp].close == bar.close


def test_conflicting_duplicate_bars_with_equal_ingested_at_are_rejected() -> None:
    timestamp = datetime(2026, 7, 1, 10, tzinfo=UTC)
    ingested_at = timestamp + timedelta(minutes=5)
    first = hourly_bar(
        timestamp,
        BITSTAMP_PROVIDER_ID,
        close="100",
        ingested_at=ingested_at,
    )
    conflicting = hourly_bar(
        timestamp,
        BITSTAMP_PROVIDER_ID,
        close="100.5",
        ingested_at=ingested_at,
    )

    with pytest.raises(ValueError, match="conflicting duplicate bars"):
        _bars_by_timestamp((first, conflicting))
    with pytest.raises(ValueError, match="conflicting duplicate bars"):
        _bars_by_timestamp((conflicting, first))


# ---------------------------------------------------------------------------
# Item 4 - isolated-wick classification needs ATR materiality
# ---------------------------------------------------------------------------


def wick_flags_for(
    *,
    bitfinex_high: str,
    bitfinex_low: str,
    coinbase_high: str | None = None,
    hours: int = WICK_HISTORY_HOURS,
) -> dict[str, tuple[str, ...]]:
    start = datetime(2026, 8, 1, tzinfo=UTC)
    event_offset = min((15 * 24) + 10, hours - 5)
    event_time = start + timedelta(hours=event_offset)
    provider_bars = required_provider_series(start, hours)
    bitfinex_bars = list(provider_bars[BITFINEX_PROVIDER_ID])
    bitfinex_bars[event_offset] = hourly_bar(
        event_time,
        BITFINEX_PROVIDER_ID,
        high=bitfinex_high,
        low=bitfinex_low,
    )
    provider_bars[BITFINEX_PROVIDER_ID] = tuple(bitfinex_bars)
    if coinbase_high is not None:
        coinbase_bars = list(provider_bars[COINBASE_PROVIDER_ID])
        coinbase_bars[event_offset] = hourly_bar(
            event_time,
            COINBASE_PROVIDER_ID,
            high=coinbase_high,
        )
        provider_bars[COINBASE_PROVIDER_ID] = tuple(coinbase_bars)
    end, as_of = baseline_window(start, hours)

    report = run_report(
        provider_bars,
        start=start,
        end=end,
        as_of=as_of,
        # Retain every diagnostic so the assertion sees all three providers at
        # the event hour rather than only the highest-divergence rows.
        top_event_count=3 * hours,
    )
    return {
        diagnostic.provider_id: diagnostic.candidate_flags
        for diagnostic in report.cross_venue_wick_diagnostics
        if diagnostic.timestamp == event_time
    }


def test_tiny_ordinary_dispersion_is_not_a_wick_anomaly() -> None:
    # Baseline ATR is 2.00, so 0.30 ATR is 0.60 price units. A unique high that
    # is 0.10 above consensus is ordinary independent-venue dispersion.
    flags = wick_flags_for(bitfinex_high="101.10", bitfinex_low="99")

    assert flags.get(BITFINEX_PROVIDER_ID, ()) == ()
    assert all(WICK_ANOMALY_CANDIDATE not in value for value in flags.values())


def test_materially_extreme_single_venue_is_isolated_and_unconfirmed() -> None:
    flags = wick_flags_for(bitfinex_high="110", bitfinex_low="99")

    assert flags[BITFINEX_PROVIDER_ID] == (
        WICK_ANOMALY_CANDIDATE,
        CROSS_VENUE_UNCONFIRMED,
    )
    assert flags[BITSTAMP_PROVIDER_ID] == ()
    assert flags[COINBASE_PROVIDER_ID] == ()


def test_material_move_corroborated_across_venues_is_confirmed() -> None:
    flags = wick_flags_for(
        bitfinex_high="110",
        bitfinex_low="99",
        coinbase_high="110",
    )

    assert flags[BITFINEX_PROVIDER_ID] == (CROSS_VENUE_CONFIRMED,)
    assert flags[COINBASE_PROVIDER_ID] == (CROSS_VENUE_CONFIRMED,)
    assert WICK_ANOMALY_CANDIDATE not in flags[BITFINEX_PROVIDER_ID]
    assert flags[BITSTAMP_PROVIDER_ID] == ()


def test_wick_classification_without_prior_atr_asserts_nothing() -> None:
    # Only three days of history: the 14-day ATR window never completes, so
    # materiality cannot be judged and no flag may be asserted either way.
    flags = wick_flags_for(bitfinex_high="110", bitfinex_low="94", hours=72)

    assert flags
    for value in flags.values():
        assert value == ()


def test_wick_threshold_is_pinned_to_the_frozen_range_disagreement_threshold() -> None:
    assert WICK_ANOMALY_ATR_THRESHOLD == DEFAULT_TWO_PROVIDER_RANGE_DISAGREEMENT_ATR
    assert WICK_ANOMALY_ATR_THRESHOLD == Decimal("0.30")


# ---------------------------------------------------------------------------
# Item 5 - trade-path probes must not be silently truncated
# ---------------------------------------------------------------------------


def test_probe_spanning_the_whole_window_is_accepted() -> None:
    start = datetime(2026, 9, 1, tzinfo=UTC)
    hour_count = 72
    end, as_of = baseline_window(start, hour_count)
    provider_bars = required_provider_series(start, hour_count)
    probe = TradePathProbe(
        entry_time=start,
        exit_time=end,
        entry_price=Decimal("100"),
        stop_level=Decimal("95"),
    )

    report = run_report(
        provider_bars,
        start=start,
        end=end,
        as_of=as_of,
        trade_path_probes=(probe,),
    )

    assert report.trade_path_probes == (probe,)


def test_probe_entering_before_the_window_is_rejected() -> None:
    start = datetime(2026, 9, 1, tzinfo=UTC)
    hour_count = 72
    end, as_of = baseline_window(start, hour_count)
    provider_bars = required_provider_series(start, hour_count)
    probe = TradePathProbe(
        entry_time=start - timedelta(hours=1),
        exit_time=end,
        entry_price=Decimal("100"),
    )

    with pytest.raises(ValueError, match="must lie inside the comparison window"):
        run_report(
            provider_bars,
            start=start,
            end=end,
            as_of=as_of,
            trade_path_probes=(probe,),
        )


def test_probe_exiting_after_the_window_is_rejected() -> None:
    start = datetime(2026, 9, 1, tzinfo=UTC)
    hour_count = 72
    end, as_of = baseline_window(start, hour_count)
    provider_bars = required_provider_series(start, hour_count)
    probe = TradePathProbe(
        entry_time=start,
        exit_time=end + timedelta(hours=1),
        entry_price=Decimal("100"),
    )

    with pytest.raises(ValueError, match="must lie inside the comparison window"):
        run_report(
            provider_bars,
            start=start,
            end=end,
            as_of=as_of,
            trade_path_probes=(probe,),
        )


def test_missing_bars_inside_a_valid_probe_remain_visible_as_gaps() -> None:
    """A provider gap inside a probe is preserved, not filled or hidden.

    BTC-019 deliberately measures what each provider's own history would have
    told a decision maker, so a gap legitimately changes that provider's MFE.
    The gap must remain reconstructable from the series profile.
    """

    start = datetime(2026, 9, 1, tzinfo=UTC)
    hour_count = 72
    end, as_of = baseline_window(start, hour_count)
    provider_bars = required_provider_series(start, hour_count)
    coinbase = list(provider_bars[COINBASE_PROVIDER_ID])
    coinbase[30] = hourly_bar(
        start + timedelta(hours=30),
        COINBASE_PROVIDER_ID,
        high="120",
        low="99",
    )
    provider_bars[COINBASE_PROVIDER_ID] = tuple(coinbase)
    gapped = dict(provider_bars)
    gapped[BITFINEX_PROVIDER_ID] = hourly_series(
        BITFINEX_PROVIDER_ID,
        start,
        hour_count,
        skip_offsets={30},
    )
    probe = TradePathProbe(
        entry_time=start,
        exit_time=end,
        entry_price=Decimal("100"),
    )

    report = run_report(
        gapped,
        start=start,
        end=end,
        as_of=as_of,
        trade_path_probes=(probe,),
    )
    profiles = {profile.provider_id: profile for profile in report.series_profiles}

    assert profiles[BITFINEX_PROVIDER_ID].missing_bar_count == 1
    assert report.mfe_divergence.observation_count == 2


# ---------------------------------------------------------------------------
# Item 6 - percentile convention is nearest-rank and exact in Decimal
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("size", "expected_index"),
    [(1, 0), (2, 1), (10, 9), (20, 18), (100, 94)],
)
def test_p95_uses_nearest_rank_indexing(size: int, expected_index: int) -> None:
    ordered = [Decimal(value) for value in range(size)]

    assert _nearest_rank_percentile(ordered, Decimal("0.95")) == Decimal(
        expected_index,
    )


def test_percentiles_stay_exact_in_decimal_without_binary_float_error() -> None:
    ordered = [Decimal("0.1"), Decimal("0.2"), Decimal("0.3")]

    # 0.95 * 3 = 2.85 -> ceil 3 -> index 2.
    assert _nearest_rank_percentile(ordered, Decimal("0.95")) == Decimal("0.3")
    # 0.90 * 10 = 9 exactly; nearest rank must not round up to index 9.
    decade = [Decimal(value) for value in range(10)]
    assert _nearest_rank_percentile(decade, Decimal("0.90")) == Decimal(8)


# ---------------------------------------------------------------------------
# Item 7 - provenance survives an empty provider series
# ---------------------------------------------------------------------------


def test_available_provider_with_zero_bars_keeps_instrument_provenance() -> None:
    start = datetime(2026, 10, 1, tzinfo=UTC)
    hour_count = 72
    end, as_of = baseline_window(start, hour_count)
    provider_bars = required_provider_series(start, hour_count)
    provider_bars[COIN_METRICS_COMMUNITY_PROVIDER_ID] = ()
    diagnostic = ProviderAccessDiagnostic(
        provider_id=COIN_METRICS_COMMUNITY_PROVIDER_ID,
        status="available",
        checked_at=as_of,
        details="Provider reachable but returned no candles for this window.",
        catalog_coverage_advertised=True,
        historical_retrieval_entitled=True,
    )

    report = run_report(
        provider_bars,
        start=start,
        end=end,
        as_of=as_of,
        provider_access_diagnostics=(diagnostic,),
    )
    profiles = {profile.provider_id: profile for profile in report.series_profiles}
    empty = profiles[COIN_METRICS_COMMUNITY_PROVIDER_ID]

    assert empty.bar_count == 0
    assert empty.exchange == "coin_metrics_community"
    assert empty.symbol == "BTC/USD"
    assert empty.timeframe == "1h"
    record = empty.as_record()
    assert record["exchange"] == "coin_metrics_community"
    assert record["symbol"] == "BTC/USD"


# ---------------------------------------------------------------------------
# Item 8 - structural level identity
# ---------------------------------------------------------------------------


def test_swing_identity_is_timestamp_based_and_price_distance_is_separate() -> None:
    """Swing identity is deliberately the structural week, not the exact price.

    Two venues that mark the same swing week a few dollars apart made the same
    structural decision. The magnitude of that price difference is measured
    separately by the ATR-normalized level metrics owned by BTC-019B and the
    frozen V2 ``swing_level_disagreement_rate_above_0_50_atr`` gate.
    """

    from btc_predictor.levels import WEEKLY_SWING_HIGH
    from btc_predictor.research.price_source_policy import (
        _typed_level_difference_count,
    )

    class Level:
        def __init__(self, level_type: str, timestamp: datetime, price: str) -> None:
            self.level_type = level_type
            self.level_timestamp = timestamp
            self.price = Decimal(price)

    week = datetime(2026, 1, 5, tzinfo=UTC)
    other_week = datetime(2026, 1, 12, tzinfo=UTC)

    same_timestamp_same_price = _typed_level_difference_count(
        {
            BITSTAMP_PROVIDER_ID: [Level(WEEKLY_SWING_HIGH, week, "100")],
            COINBASE_PROVIDER_ID: [Level(WEEKLY_SWING_HIGH, week, "100")],
        },
        baseline_provider_id=BITSTAMP_PROVIDER_ID,
        level_type=WEEKLY_SWING_HIGH,
        timestamp_field="level_timestamp",
    )
    same_timestamp_other_price = _typed_level_difference_count(
        {
            BITSTAMP_PROVIDER_ID: [Level(WEEKLY_SWING_HIGH, week, "100")],
            COINBASE_PROVIDER_ID: [Level(WEEKLY_SWING_HIGH, week, "100.25")],
        },
        baseline_provider_id=BITSTAMP_PROVIDER_ID,
        level_type=WEEKLY_SWING_HIGH,
        timestamp_field="level_timestamp",
    )
    different_timestamp = _typed_level_difference_count(
        {
            BITSTAMP_PROVIDER_ID: [Level(WEEKLY_SWING_HIGH, week, "100")],
            COINBASE_PROVIDER_ID: [Level(WEEKLY_SWING_HIGH, other_week, "100")],
        },
        baseline_provider_id=BITSTAMP_PROVIDER_ID,
        level_type=WEEKLY_SWING_HIGH,
        timestamp_field="level_timestamp",
    )

    assert same_timestamp_same_price == 0
    assert same_timestamp_other_price == 0
    assert different_timestamp == 2


def test_breakouts_sharing_a_confirmation_week_are_not_collapsed() -> None:
    """Breakout detection emits one level per source swing level.

    Several distinct breakouts can therefore confirm in the same week, and
    identity must keep them apart instead of silently merging them into one.
    """

    from btc_predictor.levels import BREAKOUT_LEVEL_TYPE
    from btc_predictor.research.price_source_policy import (
        _typed_level_difference_count,
    )

    class Level:
        def __init__(
            self,
            confirmation: datetime,
            source: datetime,
            price: str,
        ) -> None:
            self.level_type = BREAKOUT_LEVEL_TYPE
            self.confirmation_timestamp = confirmation
            self.source_level_timestamp = source
            self.price = Decimal(price)

    confirmation = datetime(2026, 2, 2, tzinfo=UTC)
    first_source = datetime(2026, 1, 5, tzinfo=UTC)
    second_source = datetime(2026, 1, 19, tzinfo=UTC)

    difference = _typed_level_difference_count(
        {
            BITSTAMP_PROVIDER_ID: [
                Level(confirmation, first_source, "100"),
                Level(confirmation, second_source, "120"),
            ],
            COINBASE_PROVIDER_ID: [Level(confirmation, first_source, "100")],
        },
        baseline_provider_id=BITSTAMP_PROVIDER_ID,
        level_type=BREAKOUT_LEVEL_TYPE,
        timestamp_field="confirmation_timestamp",
        identity_fields=("source_level_timestamp",),
    )

    # Confirmation timestamp alone would have reported zero disagreement.
    assert difference == 1
