"""Independent RBT-001 review regressions; all market facts are synthetic."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.data import EtfFlow, FundingRate, OhlcvBar
from btc_predictor.features.flow import _latest_available_flows_by_fund_date
from btc_predictor.research_backtest import (
    BITSTAMP_REPLAY_VENUE, DATA_WINDOW, ETF_FLOW_FAMILY,
    REVISION_HISTORY_UNAVAILABLE, EtfSourcePublicationTime, ReplayInputRefused,
    build_shared_replay_snapshot, build_venue_replay_dataset,
)


RAW_TIME = datetime(2026, 9, 28, 9, 15, tzinfo=UTC)
HOUR = timedelta(hours=1)


def final_flow() -> EtfFlow:
    return EtfFlow(
        fund="IBIT", observation_date=date(2024, 3, 28),
        flow_usd=Decimal("321"), aum_usd=Decimal("12345"),
        provider="final-only-source", source="synthetic-final-only-export",
        revision="final", available_at=RAW_TIME, ingested_at=RAW_TIME,
    )


def publication(flow: EtfFlow, when: datetime, **kwargs) -> EtfSourcePublicationTime:
    return EtfSourcePublicationTime(
        flow.fund, flow.observation_date, flow.provider, flow.revision, when, **kwargs,
    )


def test_final_only_etf_with_a_real_publication_time_still_lacks_revision_history():
    """A source's final revision timestamp does not supply its missing earlier values."""
    raw = final_flow()
    published = datetime(2024, 4, 2, 16, 30, tzinfo=UTC)
    snapshot = build_shared_replay_snapshot(
        window=DATA_WINDOW, etf_flows=(raw,),
        etf_source_publication_times=(publication(raw, published),),
    )
    (entry,) = snapshot.availability
    assert entry.source_published_at == published
    assert entry.modelled_available_at == published
    assert REVISION_HISTORY_UNAVAILABLE in entry.labels
    assert snapshot.manifest["families"][ETF_FLOW_FAMILY]["revision_history_unavailable_count"] == 1
    assert raw.ingested_at == raw.available_at == RAW_TIME


def test_revision_history_assertion_is_separate_from_publication_timing():
    raw = final_flow()
    when = datetime(2024, 4, 2, 16, 30, tzinfo=UTC)
    def snapshot(available):
        return build_shared_replay_snapshot(
            window=DATA_WINDOW, etf_flows=(raw,),
            etf_source_publication_times=(publication(raw, when, revision_history_available=available),),
        )
    unknown, supplied = snapshot(False), snapshot(True)
    assert unknown.etf_flows == supplied.etf_flows
    assert unknown.availability[0].labels == (REVISION_HISTORY_UNAVAILABLE,)
    assert supplied.availability[0].labels == ()
    assert unknown.manifest_sha256 != supplied.manifest_sha256
    assert supplied.manifest["families"][ETF_FLOW_FAMILY]["revision_history_unavailable_count"] == 0


@pytest.mark.parametrize("invalid", [None, "yes", 1])
def test_revision_history_assertion_requires_a_boolean(invalid):
    raw = final_flow()
    with pytest.raises(ReplayInputRefused, match="RECORD_TYPE_REFUSED"):
        build_shared_replay_snapshot(
            window=DATA_WINDOW, etf_flows=(raw,),
            etf_source_publication_times=(publication(raw, datetime(2024, 4, 2, tzinfo=UTC),
                                                      revision_history_available=invalid),),
        )


def test_cross_month_week_refuses_a_missing_hour_and_waits_for_sunday_close():
    start = datetime(2024, 12, 30, tzinfo=UTC)
    end = datetime(2025, 1, 6, tzinfo=UTC)
    venue = BITSTAMP_REPLAY_VENUE
    raw = tuple(OhlcvBar(
        timestamp=start + i * HOUR, exchange=venue.exchange, symbol=venue.symbol,
        provider=venue.provider, timeframe="1h", ingested_at=RAW_TIME,
        open=Decimal("100"), high=Decimal("102"), low=Decimal("98"),
        close=Decimal("101"), volume=Decimal("2"),
    ) for i in range(168))
    shared = build_shared_replay_snapshot(window=DATA_WINDOW)
    def dataset(bars):
        return build_venue_replay_dataset(
            venue=venue, window=DATA_WINDOW, price_bars=bars, shared_snapshot=shared,
        )
    complete = dataset(raw)
    assert complete.market_bars_at(end - timedelta(microseconds=1), timeframes=("1w",)) == ()
    (weekly,) = complete.market_bars_at(end, timeframes=("1w",))
    assert weekly.timestamp == start and weekly.ingested_at == end
    assert weekly.volume == Decimal("336")
    assert dataset(raw[:73] + raw[74:]).market_bars_at(end + HOUR, timeframes=("1w",)) == ()


def test_three_revisions_with_reversed_labels_and_late_supplied_time():
    raw = final_flow()
    flows = tuple(replace(raw, revision=label, flow_usd=Decimal(value))
                  for label, value in (("z-original", "10"), ("a-final", "20"), ("0-correction", "30")))
    times = (datetime(2024, 3, 29, 12, tzinfo=UTC),
             datetime(2024, 3, 31, 8, tzinfo=UTC),
             datetime(2024, 4, 2, 16, 30, tzinfo=UTC))
    snapshot = build_shared_replay_snapshot(
        window=DATA_WINDOW, etf_flows=tuple(reversed(flows)),
        etf_source_publication_times=tuple(publication(row, when) for row, when in zip(flows, times)),
    )
    for instant, expected in ((datetime(2024, 3, 30, tzinfo=UTC), "10"),
                              (times[1] - timedelta(microseconds=1), "10"),
                              (times[1], "20"),
                              (times[2] - timedelta(microseconds=1), "20"),
                              (times[2], "30"), (times[2] + timedelta(days=300), "30")):
        selected = _latest_available_flows_by_fund_date(
            snapshot.etf_flows, as_of=instant, funds=(), end_date=None,
        )[(raw.fund, raw.observation_date)]
        assert selected.flow_usd == Decimal(expected)


def test_first_wholly_in_window_funding_period_is_admitted_at_its_boundary():
    start = datetime(2020, 1, 1, tzinfo=UTC)
    raw = FundingRate(
        observation_time=start + timedelta(minutes=15),
        exchange="synthetic", symbol="BTCUSDT", instrument="BTCUSDT-PERP",
        funding_rate=Decimal(".0001"), funding_interval_hours=Decimal(".25"),
        provider="synthetic", source="synthetic", available_at=RAW_TIME,
        ingested_at=RAW_TIME,
    )
    accepted = build_shared_replay_snapshot(window=DATA_WINDOW, funding_rates=(raw,))
    assert accepted.funding_rates[0].available_at == raw.observation_time
    # More than one clock tick before the boundary puts represented accrual in 2019.
    with pytest.raises(ReplayInputRefused, match="PRE_2020_RECORD_REFUSED"):
        build_shared_replay_snapshot(window=DATA_WINDOW, funding_rates=(
            replace(raw, observation_time=raw.observation_time - timedelta(microseconds=2)),
        ))
