"""RBT-001 ``BUILD_HISTORICAL_REPLAY_INPUTS_V1`` (EPIC Y, non-certifying).

A backfill stamps every row it writes with one bulk ingestion time, and the
frozen BTC-180 engine reads ``OhlcvBar.ingested_at`` as live availability. A
dataset built the repository's own way therefore replays with no executable
decision. ``HISTORICAL_REPLAY_AVAILABILITY_V1`` (``RESEARCH_BACKTEST_POLICY_V2``
section 4) models availability instead, on derived copies, and never touches a
raw row.

These tests pin:

- the section 4 availability table, including its boundaries;
- the field each owner's point-in-time predicate reads, and that the replay
  copy carries the modelled value there and nowhere else;
- a point-in-time property checked through the owners' own predicates
  (BTC-180, BTC-040, ``features.flow``, ``data.derivatives``,
  ``features.positioning``) rather than a restatement of them;
- the checked-in control: a real-shaped Bitstamp backfill, produced by the
  real BTC-020 collector and Bitstamp adapter from canned API payloads, that
  the unchanged engine cannot trade, and the same bars through the builder,
  which it can;
- stop, fill and funding timing on replayed bars through the unchanged owners;
- the closed window enumeration, the holdout guard, the series rules, and a
  manifest that is byte-identical under reordering, hash seeds, another cwd and
  a fresh process.

Every fixture is synthetic, offline and dated inside the data window. Nothing
before 2020 or inside the holdout is read or collected.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import socket
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest

from btc_predictor.backtest import (
    ARM_ENTRY_ACTION,
    EXIT_ACTION,
    BacktestContext,
    BacktestIntent,
    BacktestResult,
    run_backtest,
)
from btc_predictor.config import load_strategy_config
from btc_predictor.data import (
    BITSTAMP_BTC_USD_SYMBOL,
    BITSTAMP_EXCHANGE,
    BITSTAMP_PROVIDER_ID,
    BitstampOhlcvProvider,
    DerivativesQualityConfig,
    EtfFlow,
    FundingRate,
    FuturesBasis,
    Liquidation,
    OhlcvBar,
    OhlcvCollectionRequest,
    OpenInterest,
    PerpVolume,
    aggregate_btc_derivatives_available_at,
    build_canonical_market_bars,
    collect_btc_ohlcv,
    validate_derivatives_quality,
)
from btc_predictor.data import ohlcv as ohlcv_owner
from btc_predictor.features import flow as flow_owner
from btc_predictor.features.flow import spot_perp_participation_from_rows
from btc_predictor.features.positioning import funding_health, open_interest_growth_health
from btc_predictor.research.us_equity_market_closures import load_closures
from btc_predictor.research_backtest import (
    BITFINEX_REPLAY_VENUE,
    BITSTAMP_REPLAY_VENUE,
    COINBASE_REPLAY_VENUE,
    DATA_WINDOW,
    ETF_FLOW_FAMILY,
    FUNDING_RATE_FAMILY,
    HOLDOUT_WINDOW,
    OPEN_INTEREST_FAMILY,
    PERP_VOLUME_FAMILY,
    PROHIBITED_WINDOW,
    REFERENCE_PRICE_FAMILY,
    REPLAY_AVAILABILITY_RULES,
    REPLAY_VENUES,
    REPLAY_WINDOWS,
    RESERVE_WINDOW,
    REVISION_HISTORY_UNAVAILABLE,
    SHARED_SNAPSHOT_FAMILIES,
    SHARED_VOLUME_FAMILY,
    SHARED_VOLUME_VENUE,
    EtfSourcePublicationTime,
    ReplayInputRefused,
    ReplayVenue,
    ReplayWindow,
    SharedReplaySnapshot,
    VenueReplayDataset,
    build_shared_replay_snapshot,
    build_venue_replay_dataset,
    canonical_decimal,
    etf_flow_scheduled_available_at,
    modelled_bar_available_at,
    modelled_etf_flow_available_at,
    modelled_funding_rate_available_at,
    modelled_open_interest_available_at,
    modelled_perp_volume_available_at,
    replay_market_bars_at,
    replay_record_content_sha256,
    replay_window_of,
    require_replay_window,
)
from btc_predictor.research_backtest import replay_inputs as replay
from btc_predictor.risk import calculate_initial_stop


ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_strategy_config()
METADATA = CONFIG.run_metadata()
NAV = "100000"
HOUR = timedelta(hours=1)
DAY = timedelta(days=1)
MICROSECOND = timedelta(microseconds=1)
# A backfill run in 2026, after the data window ends, stamps everything it writes.
BULK_INGESTED_AT = datetime(2026, 9, 28, 9, 15, tzinfo=UTC)
DECISION_EXECUTION_EVENTS = (
    "ENTRY_EXECUTION",
    "ADD_EXECUTION",
    "TRIM_EXECUTION",
    "TRAILING_STOP",
    "EXIT_EXECUTION",
)


def utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


# --- owner-record fixtures ----------------------------------------------------


def hourly_bar(
    timestamp: datetime,
    *,
    venue: ReplayVenue = BITSTAMP_REPLAY_VENUE,
    close: str = "60000",
    low: str | None = None,
    high: str | None = None,
    open_price: str | None = None,
    ingested_at: datetime = BULK_INGESTED_AT,
    timeframe: str = "1h",
) -> OhlcvBar:
    closing = Decimal(close)
    opening = Decimal(open_price) if open_price is not None else closing
    return OhlcvBar(
        timestamp=timestamp,
        exchange=venue.exchange,
        symbol=venue.symbol,
        timeframe=timeframe,
        open=opening,
        high=Decimal(high) if high is not None else max(opening, closing) + Decimal("80"),
        low=Decimal(low) if low is not None else min(opening, closing) - Decimal("80"),
        close=closing,
        volume=Decimal("4.25"),
        provider=venue.provider,
        ingested_at=ingested_at,
    )


def hourly_series(
    start: datetime,
    hours: int,
    *,
    venue: ReplayVenue = BITSTAMP_REPLAY_VENUE,
    missing: tuple[int, ...] | set[int] = (),
    ingested_at: datetime = BULK_INGESTED_AT,
) -> tuple[OhlcvBar, ...]:
    return tuple(
        hourly_bar(
            start + index * HOUR,
            venue=venue,
            close=str(60000 + 10 * index),
            ingested_at=ingested_at,
        )
        for index in range(hours)
        if index not in missing
    )


def etf_flow(
    fund: str,
    day: date,
    *,
    flow: str = "125.5",
    aum: str | None = "25000",
    provider: str = "fixture-etf",
    revision: str = "initial",
    available_at: datetime = BULK_INGESTED_AT,
    ingested_at: datetime = BULK_INGESTED_AT,
) -> EtfFlow:
    return EtfFlow(
        fund=fund,
        observation_date=day,
        flow_usd=Decimal(flow),
        aum_usd=Decimal(aum) if aum is not None else None,
        provider=provider,
        source="fixture-etf-source",
        revision=revision,
        available_at=available_at,
        ingested_at=ingested_at,
    )


def funding_rate(
    settled_at: datetime,
    *,
    interval: str = "8",
    rate: str = "0.0001",
    exchange: str = "binance",
    available_at: datetime = BULK_INGESTED_AT,
    ingested_at: datetime = BULK_INGESTED_AT,
) -> FundingRate:
    return FundingRate(
        observation_time=settled_at,
        exchange=exchange,
        symbol="BTCUSDT",
        instrument="BTCUSDT-PERP",
        funding_rate=Decimal(rate),
        funding_interval_hours=Decimal(interval),
        provider=exchange,
        source="fixture-derivatives",
        available_at=available_at,
        ingested_at=ingested_at,
    )


def open_interest(
    observed_at: datetime,
    *,
    value: str = "51000",
    exchange: str = "binance",
    available_at: datetime = BULK_INGESTED_AT,
    ingested_at: datetime = BULK_INGESTED_AT,
) -> OpenInterest:
    return OpenInterest(
        observation_time=observed_at,
        exchange=exchange,
        symbol="BTCUSDT",
        instrument="BTCUSDT-PERP",
        open_interest=Decimal(value),
        open_interest_unit="BTC",
        provider=exchange,
        source="fixture-derivatives",
        available_at=available_at,
        ingested_at=ingested_at,
    )


def perp_volume(
    start: datetime,
    *,
    timeframe: str = "1h",
    notional: str = "650000",
    exchange: str = "binance",
    available_at: datetime = BULK_INGESTED_AT,
    ingested_at: datetime = BULK_INGESTED_AT,
) -> PerpVolume:
    return PerpVolume(
        observation_time=start,
        exchange=exchange,
        symbol="BTCUSDT",
        timeframe=timeframe,
        volume=Decimal("10.5"),
        volume_unit="BTC",
        notional_usd=Decimal(notional),
        provider=exchange,
        source="fixture-derivatives",
        available_at=available_at,
        ingested_at=ingested_at,
    )


def shared(**families: Any) -> SharedReplaySnapshot:
    return build_shared_replay_snapshot(window=DATA_WINDOW, **families)


def venue_dataset(
    price_bars: tuple[OhlcvBar, ...],
    *,
    venue: ReplayVenue = BITSTAMP_REPLAY_VENUE,
    shared_snapshot: SharedReplaySnapshot | None = None,
) -> VenueReplayDataset:
    return build_venue_replay_dataset(
        venue=venue,
        window=DATA_WINDOW,
        price_bars=price_bars,
        shared_snapshot=shared_snapshot if shared_snapshot is not None else shared(),
    )


def assert_refused(reason: str, call: Any, *args: Any, **kwargs: Any) -> ReplayInputRefused:
    with pytest.raises(ReplayInputRefused) as caught:
        call(*args, **kwargs)
    assert caught.value.reason_code == reason, str(caught.value)
    assert str(caught.value).startswith(f"{reason}: ")
    return caught.value


def entries_of(snapshot: SharedReplaySnapshot, family: str) -> list[Any]:
    return [entry for entry in snapshot.availability if entry.family == family]


def replayed_pairs(
    snapshot: SharedReplaySnapshot,
    dataset: VenueReplayDataset,
) -> list[tuple[Any, Any]]:
    """Every replay copy with its manifest entry, family by family."""

    pairs = list(zip(dataset.price_bars, dataset.price_availability, strict=True))
    for rows, family in (
        (snapshot.volume_bars, SHARED_VOLUME_FAMILY),
        (snapshot.etf_flows, ETF_FLOW_FAMILY),
        (snapshot.funding_rates, FUNDING_RATE_FAMILY),
        (snapshot.open_interest, OPEN_INTEREST_FAMILY),
        (snapshot.perp_volumes, PERP_VOLUME_FAMILY),
    ):
        pairs.extend(zip(rows, entries_of(snapshot, family), strict=True))
    return pairs


# Policy section 4 restated from the raw fields: an oracle the builder never sees.
TIMEFRAME_LENGTH = {"1h": HOUR, "1d": DAY, "1w": 7 * DAY}


def utc_midnight(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def policy_observation_end(record: Any) -> datetime:
    if isinstance(record, OhlcvBar):
        return record.timestamp + HOUR
    if isinstance(record, EtfFlow):
        return utc_midnight(record.observation_date) + DAY
    if isinstance(record, PerpVolume):
        return record.observation_time + TIMEFRAME_LENGTH[record.timeframe]
    # A funding settlement and an open-interest snapshot end at their instant.
    return record.observation_time


def policy_availability(record: Any, supplied: dict[tuple[Any, ...], datetime]) -> datetime:
    if isinstance(record, EtfFlow):
        floor = utc_midnight(record.observation_date) + 2 * DAY
        published = supplied.get((record.fund, record.observation_date, record.provider, record.revision))
        return floor if published is None else max(floor, published)
    return policy_observation_end(record)


def record_key(record: Any) -> tuple[Any, ...]:
    """The owner identity a replay copy shares with its raw record."""

    if isinstance(record, OhlcvBar):
        return ("bar", record.exchange, record.timestamp)
    if isinstance(record, EtfFlow):
        return ("etf", record.fund, record.observation_date, record.provider, record.revision)
    series = record.timeframe if isinstance(record, PerpVolume) else record.instrument
    return (type(record).__name__, record.observation_time, record.exchange, record.symbol, series, record.provider)


def raw_index(inputs: dict[str, tuple[Any, ...]]) -> dict[tuple[Any, ...], Any]:
    return {
        record_key(record): record
        for name in ("price", "volume", "etf", "funding", "open_interest", "perp")
        for record in inputs[name]
    }


def supplied_times(inputs: dict[str, tuple[Any, ...]]) -> dict[tuple[Any, ...], datetime]:
    return {item.key(): item.published_at for item in inputs["publication"]}


# A mixed shared snapshot: gaps, several funds, a two-revision ETF history with
# supplied publication times, derivatives on their own cadences.
MIXED_START = utc(2024, 3, 4)


def mixed_inputs() -> dict[str, tuple[Any, ...]]:
    price = hourly_series(MIXED_START, 96, missing=(17, 40, 41))
    return {
        "price": price,
        "volume": price,
        "etf": (
            etf_flow("IBIT", date(2024, 3, 4)),
            etf_flow("IBIT", date(2024, 3, 5), flow="-40"),
            etf_flow("FBTC", date(2024, 3, 4), aum=None),
            etf_flow("FBTC", date(2024, 3, 5), flow="10", revision="r1"),
            etf_flow("FBTC", date(2024, 3, 5), flow="12", revision="r2"),
        ),
        "publication": (
            EtfSourcePublicationTime("FBTC", date(2024, 3, 5), "fixture-etf", "r1", utc(2024, 3, 5, 23, 40)),
            EtfSourcePublicationTime("FBTC", date(2024, 3, 5), "fixture-etf", "r2", utc(2024, 3, 8, 14, 5)),
        ),
        "funding": tuple(funding_rate(MIXED_START + 8 * k * HOUR) for k in range(1, 12) if k != 5),
        "open_interest": tuple(
            open_interest(MIXED_START + k * HOUR, value=str(51000 + k)) for k in range(96) if k % 7 != 3
        ),
        "perp": tuple(perp_volume(MIXED_START + k * HOUR) for k in range(96) if k not in (10, 11))
        + (
            perp_volume(MIXED_START, timeframe="1d"),
            perp_volume(MIXED_START + DAY, timeframe="1d"),
        ),
    }


def build_mixed(inputs: dict[str, tuple[Any, ...]]) -> tuple[SharedReplaySnapshot, VenueReplayDataset]:
    snapshot = build_shared_replay_snapshot(
        window=DATA_WINDOW,
        volume_bars=inputs["volume"],
        etf_flows=inputs["etf"],
        etf_source_publication_times=inputs["publication"],
        funding_rates=inputs["funding"],
        open_interest=inputs["open_interest"],
        perp_volumes=inputs["perp"],
    )
    dataset = build_venue_replay_dataset(
        venue=BITSTAMP_REPLAY_VENUE,
        window=DATA_WINDOW,
        price_bars=inputs["price"],
        shared_snapshot=snapshot,
    )
    return snapshot, dataset


def determinism_manifests() -> tuple[bytes, bytes]:
    """The venue and shared manifests of the mixed fixture (used in-process and fresh)."""

    snapshot, dataset = build_mixed(mixed_inputs())
    return dataset.manifest_bytes, snapshot.manifest_bytes


# --- a golden-style scripted strategy --------------------------------------------


def arm(context: BacktestContext, *, invalidation: Decimal) -> BacktestIntent:
    close = context.bar.close
    return BacktestIntent(
        action=ARM_ENTRY_ACTION,
        direction="long",
        entry_zone_lower=close * Decimal("0.97"),
        entry_zone_upper=close * Decimal("1.03"),
        initial_stop=calculate_initial_stop(
            invalidation_price=close * invalidation,
            buffer=Decimal("0"),
            direction="long",
            entry_price=close,
            config_metadata=METADATA,
        ),
        entry_conviction=Decimal("90"),
        source_id=f"rbt001:entry:{context.bar.timestamp.isoformat()}",
    )


class ScriptedStrategy:
    """Act on the planned decision bars only, as the BTC-224 golden scenarios do.

    An entry is armed only when flat and an exit only when a position is open,
    so a run whose entry never executes never queues a second intent.
    """

    def __init__(
        self,
        plan: dict[datetime, str],
        *,
        invalidation: Decimal = Decimal("0.9"),
    ) -> None:
        self.plan = dict(plan)
        self.invalidation = invalidation
        self.decisions: list[tuple[datetime, datetime]] = []

    def __call__(self, context: BacktestContext) -> BacktestIntent | None:
        action = self.plan.get(context.bar.timestamp)
        if action == ARM_ENTRY_ACTION and not context.position_open:
            self.decisions.append((context.bar.timestamp, context.as_of))
            return arm(context, invalidation=self.invalidation)
        if action == EXIT_ACTION and context.position_open:
            self.decisions.append((context.bar.timestamp, context.as_of))
            return BacktestIntent(
                action=EXIT_ACTION,
                exit_reason="RBT001_SCRIPTED_EXIT",
                source_id=f"rbt001:exit:{context.bar.timestamp.isoformat()}",
            )
        return None


def scripted_run(
    bars: tuple[OhlcvBar, ...],
    plan: dict[datetime, str],
    *,
    invalidation: Decimal = Decimal("0.9"),
    cost_profile: str | None = None,
) -> BacktestResult:
    return run_backtest(
        bars,
        strategy=ScriptedStrategy(plan, invalidation=invalidation),
        symbol=bars[0].symbol,
        starting_nav=NAV,
        strategy_config=CONFIG,
        cost_profile=cost_profile,
        strategy_id="rbt001:scripted",
    )


def executed_decisions(result: BacktestResult) -> list[Any]:
    return [
        event
        for event in result.events
        if event.event_type in DECISION_EXECUTION_EVENTS and event.status == "EXECUTED"
    ]


def events_of(result: BacktestResult, event_type: str, status: str | None = None) -> list[Any]:
    return [
        event
        for event in result.events
        if event.event_type == event_type and (status is None or event.status == status)
    ]


# --- policy identifiers, windows and venues -------------------------------------


def test_the_policy_identifiers_and_evidence_class_are_pinned() -> None:
    assert replay.RESEARCH_BACKTEST_POLICY_VERSION == "RESEARCH_BACKTEST_POLICY_V2"
    assert replay.REPLAY_AVAILABILITY_POLICY_VERSION == "HISTORICAL_REPLAY_AVAILABILITY_V1"
    assert replay.REPLAY_INPUTS_BUILDER_VERSION == "BUILD_HISTORICAL_REPLAY_INPUTS_V1"
    assert replay.RESEARCH_EVIDENCE_CLASS == "RESEARCH_BACKTEST_NON_CERTIFYING"
    assert replay.CANONICAL_REFERENCE_UNRESOLVED == "UNRESOLVED"
    assert replay.REVISION_HISTORY_UNAVAILABLE == "REVISION_HISTORY_UNAVAILABLE"
    # The holdout guard is shut at this commit; only RBT-008 may lift it.
    assert replay.HOLDOUT_OPENING_AUTHORIZED is False


@pytest.mark.parametrize(
    ("instant", "window"),
    [
        (datetime(2019, 12, 31, 23, 59, 59, 999999, tzinfo=UTC), PROHIBITED_WINDOW),
        (utc(2015, 7, 20, 21), PROHIBITED_WINDOW),
        (utc(2020, 1, 1), DATA_WINDOW),
        (utc(2024, 3, 4, 12), DATA_WINDOW),
        (utc(2025, 12, 31, 23), DATA_WINDOW),
        (datetime(2025, 12, 31, 23, 59, 59, 999999, tzinfo=UTC), DATA_WINDOW),
        (utc(2026, 1, 1), HOLDOUT_WINDOW),
        (utc(2026, 6, 30, 23), HOLDOUT_WINDOW),
        (utc(2026, 7, 1), RESERVE_WINDOW),
        (utc(2031, 1, 1), RESERVE_WINDOW),
    ],
)
def test_the_windows_are_a_closed_partition_of_time(instant: datetime, window: ReplayWindow) -> None:
    assert replay_window_of(instant) == window
    assert sum(candidate.contains(instant) for candidate in REPLAY_WINDOWS) == 1


def test_the_window_bounds_match_the_policy_labels() -> None:
    assert [window.window_id for window in REPLAY_WINDOWS] == [
        "PROHIBITED",
        "DATA",
        "HOLDOUT",
        "RESERVE",
    ]
    assert DATA_WINDOW.as_record() == {
        "window_id": "DATA",
        "start": "2020-01-01T00:00:00+00:00",
        "end_exclusive": "2026-01-01T00:00:00+00:00",
        "first_hour": "2020-01-01T00:00:00+00:00",
        "last_hour": "2025-12-31T23:00:00+00:00",
    }
    assert HOLDOUT_WINDOW.as_record()["first_hour"] == "2026-01-01T00:00:00+00:00"
    assert HOLDOUT_WINDOW.as_record()["last_hour"] == "2026-06-30T23:00:00+00:00"
    assert RESERVE_WINDOW.start == utc(2026, 7, 1) and RESERVE_WINDOW.end is None
    assert PROHIBITED_WINDOW.start is None and PROHIBITED_WINDOW.end == utc(2020, 1, 1)


def test_the_three_required_venues_carry_their_adapter_identities() -> None:
    assert [venue.as_record() for venue in REPLAY_VENUES] == [
        {
            "venue_id": "BITSTAMP",
            "exchange": "bitstamp",
            "symbol": "BTC/USD",
            "provider": "bitstamp",
            "api_instrument": "btcusd",
        },
        {
            "venue_id": "COINBASE",
            "exchange": "coinbase",
            "symbol": "BTC-USD",
            "provider": "coinbase",
            "api_instrument": "BTC-USD",
        },
        {
            "venue_id": "BITFINEX",
            "exchange": "bitfinex",
            "symbol": "BTC/USD",
            "provider": "bitfinex",
            "api_instrument": "tBTCUSD",
        },
    ]
    assert REPLAY_VENUES == (BITSTAMP_REPLAY_VENUE, COINBASE_REPLAY_VENUE, BITFINEX_REPLAY_VENUE)
    # Policy section 2: volume and spot participation use Bitstamp in every run.
    assert SHARED_VOLUME_VENUE == BITSTAMP_REPLAY_VENUE


# --- the policy section 4 availability table ------------------------------------


@pytest.mark.parametrize(
    ("timestamp", "raw_ingested_at"),
    [
        (utc(2020, 1, 1), BULK_INGESTED_AT),
        (utc(2024, 2, 29, 23), BULK_INGESTED_AT),
        (utc(2024, 12, 31, 23), utc(2025, 1, 1, 0, 3)),
        (utc(2025, 12, 31, 23), BULK_INGESTED_AT),
        # A raw time earlier than the close never pulls availability forward.
        (utc(2024, 3, 4, 10), utc(2024, 3, 4, 10, 20)),
    ],
)
def test_a_1h_price_bar_is_available_at_its_close_boundary(
    timestamp: datetime,
    raw_ingested_at: datetime,
) -> None:
    raw = hourly_bar(timestamp, ingested_at=raw_ingested_at)
    close = timestamp + HOUR

    assert modelled_bar_available_at(raw) == close
    dataset = venue_dataset((raw,))
    (copy,) = dataset.price_bars
    assert copy.ingested_at == close
    assert replace(copy, ingested_at=raw.ingested_at) == raw
    (record,) = dataset.manifest["price_series"]["records"]
    assert record["raw"] == {"ingested_at": raw_ingested_at.isoformat()}
    assert record["modelled_available_at"] == close.isoformat()
    assert record["observation_end"] == close.isoformat()


def test_a_bar_of_another_timeframe_is_not_a_replay_source() -> None:
    daily = hourly_bar(utc(2024, 3, 4), timeframe="1d")

    assert_refused("SOURCE_TIMEFRAME_REFUSED", modelled_bar_available_at, daily)
    assert_refused("SOURCE_TIMEFRAME_REFUSED", venue_dataset, (daily,))


FEBRUARY_2024 = hourly_series(utc(2024, 2, 1), (29 + 4) * 24)


@pytest.fixture(scope="module")
def february_replay() -> VenueReplayDataset:
    return venue_dataset(FEBRUARY_2024)


@pytest.mark.parametrize(
    ("timeframe", "bucket_start", "bucket_end"),
    [
        ("1d", utc(2024, 2, 20), utc(2024, 2, 21)),
        ("1d", utc(2024, 2, 29), utc(2024, 3, 1)),
        ("1w", utc(2024, 2, 26), utc(2024, 3, 4)),
        ("1mo", utc(2024, 2, 1), utc(2024, 3, 1)),
    ],
)
def test_a_derived_bar_takes_the_close_of_its_last_constituent_hour(
    february_replay: VenueReplayDataset,
    timeframe: str,
    bucket_start: datetime,
    bucket_end: datetime,
) -> None:
    def derived(decision_at: datetime) -> list[OhlcvBar]:
        return [
            bar
            for bar in february_replay.market_bars_at(decision_at, timeframes=(timeframe,))
            if bar.timestamp == bucket_start
        ]

    # Not yet complete one microsecond before its last hour closes.
    assert derived(bucket_end - MICROSECOND) == []
    (at_close,) = derived(bucket_end)
    (later,) = derived(bucket_end + 3 * DAY)
    last_hour = next(bar for bar in february_replay.price_bars if bar.timestamp == bucket_end - HOUR)
    assert at_close.ingested_at == last_hour.ingested_at == bucket_end
    assert later.ingested_at == bucket_end
    # BTC-040 derived it; only the availability field differs from the owner's bar.
    (owner_bar,) = [
        bar
        for bar in build_canonical_market_bars(
            february_replay.price_bars,
            data_available_at=bucket_end + 3 * DAY,
            timeframes=(timeframe,),
        )
        if bar.timestamp == bucket_start
    ]
    assert owner_bar.ingested_at == bucket_end + 3 * DAY
    assert replace(later, ingested_at=owner_bar.ingested_at) == owner_bar


def test_decision_instant_bars_from_the_raw_backfill_do_not_exist() -> None:
    decision_at = utc(2024, 3, 1)

    assert build_canonical_market_bars(FEBRUARY_2024, data_available_at=decision_at) == ()
    assert_refused(
        "NOT_A_REPLAY_BAR",
        replay_market_bars_at,
        FEBRUARY_2024,
        decision_at=decision_at,
        window=DATA_WINDOW,
    )


def replay_shaped(start: datetime, hours: int, *, exchange: str | None = None) -> tuple[OhlcvBar, ...]:
    """Bars that carry close-boundary availability but never passed the builder."""

    bars = tuple(
        hourly_bar(start + index * HOUR, ingested_at=start + (index + 1) * HOUR)
        for index in range(hours)
    )
    return bars if exchange is None else tuple(replace(bar, exchange=exchange, provider=exchange) for bar in bars)


@pytest.mark.parametrize(
    ("bars", "window", "reason"),
    [
        pytest.param(replay_shaped(utc(2019, 11, 1), 48), DATA_WINDOW, "PRE_2020_RECORD_REFUSED", id="pre-2020"),
        pytest.param(replay_shaped(utc(2026, 2, 2), 24), DATA_WINDOW, "HOLDOUT_RECORD_REFUSED", id="holdout-dated"),
        pytest.param(replay_shaped(utc(2026, 7, 6), 24), DATA_WINDOW, "RESERVE_RECORD_REFUSED", id="reserve-dated"),
        pytest.param(
            replay_shaped(utc(2024, 3, 4), 24, exchange="cross_venue_reference"),
            DATA_WINDOW,
            "UNKNOWN_REPLAY_VENUE",
            id="composite",
        ),
        pytest.param(
            replay_shaped(utc(2024, 3, 4), 24)
            + tuple(
                replace(bar, exchange="coinbase", symbol="BTC-USD", provider="coinbase")
                for bar in replay_shaped(utc(2024, 3, 5), 24)
            ),
            DATA_WINDOW,
            "MIXED_VENUE_SERIES_REFUSED",
            id="spliced-venues",
        ),
        pytest.param(replay_shaped(utc(2024, 3, 4), 24), HOLDOUT_WINDOW, "HOLDOUT_WINDOW_NOT_AUTHORIZED", id="holdout-window"),
    ],
)
def test_decision_instant_bars_hold_their_sources_to_the_replay_rules(
    bars: tuple[OhlcvBar, ...],
    window: ReplayWindow,
    reason: str,
) -> None:
    """Close-boundary availability alone does not make a bar a replay bar."""

    assert_refused(reason, replay_market_bars_at, bars, decision_at=utc(2026, 9, 1), window=window)


@pytest.mark.parametrize(
    ("hour", "changes", "reason"),
    [
        pytest.param(5, dict(volume=Decimal("-7")), "ENGINE_BAR_CONTRACT_REFUSED", id="negative-volume"),
        pytest.param(5, dict(low=Decimal("61000")), "ENGINE_BAR_CONTRACT_REFUSED", id="impossible-geometry"),
        pytest.param(5, dict(close=59999.5), "RECORD_TYPE_REFUSED", id="float-price"),
    ],
)
def test_decision_instant_bars_meet_the_venue_bar_contract(hour: int, changes: dict[str, Any], reason: str) -> None:
    bars = list(replay_shaped(utc(2024, 3, 4), 24))
    bars[hour] = replace(bars[hour], **changes)

    assert_refused(reason, replay_market_bars_at, tuple(bars), decision_at=utc(2024, 3, 5), window=DATA_WINDOW)
    assert_refused(
        "DUPLICATE_RECORD_REFUSED",
        replay_market_bars_at,
        (*replay_shaped(utc(2024, 3, 4), 24), replay_shaped(utc(2024, 3, 4), 24)[3]),
        decision_at=utc(2024, 3, 5),
        window=DATA_WINDOW,
    )


def test_a_gap_inside_a_bucket_is_preserved_rather_than_filled() -> None:
    gapped = hourly_series(utc(2024, 2, 5), 72, missing=(30,))
    dataset = venue_dataset(gapped)

    days = [bar.timestamp for bar in dataset.market_bars_at(utc(2024, 2, 8), timeframes=("1d",))]
    assert days == [utc(2024, 2, 5), utc(2024, 2, 7)]
    assert len(dataset.price_bars) == 71
    assert utc(2024, 2, 6, 6) not in {bar.timestamp for bar in dataset.price_bars}


@pytest.mark.parametrize(
    ("trading_date", "supplied", "expected", "labelled"),
    [
        (date(2024, 3, 4), None, utc(2024, 3, 6), True),
        # Friday T: calendar day T+2 is Sunday.
        (date(2024, 3, 8), None, utc(2024, 3, 10), True),
        (date(2024, 2, 28), None, utc(2024, 3, 1), True),
        (date(2024, 12, 31), None, utc(2025, 1, 2), True),
        (date(2025, 12, 31), None, utc(2026, 1, 2), True),
        # The source's own later publication or revision time wins.
        (date(2024, 3, 4), utc(2024, 3, 7, 14, 5), utc(2024, 3, 7, 14, 5), False),
        # T+2 00:00 is a floor: an earlier supplied time never advances it.
        (date(2024, 3, 4), utc(2024, 3, 4, 22, 30), utc(2024, 3, 6), False),
        (date(2024, 3, 4), utc(2024, 3, 6), utc(2024, 3, 6), False),
    ],
)
def test_an_etf_flow_is_available_at_t_plus_2_or_its_later_source_time(
    trading_date: date,
    supplied: datetime | None,
    expected: datetime,
    labelled: bool,
) -> None:
    raw = etf_flow("IBIT", trading_date)
    publications = (
        (EtfSourcePublicationTime("IBIT", trading_date, "fixture-etf", "initial", supplied),)
        if supplied is not None
        else ()
    )

    assert etf_flow_scheduled_available_at(trading_date) == datetime.combine(
        trading_date + 2 * DAY, datetime.min.time(), tzinfo=UTC
    )
    assert modelled_etf_flow_available_at(raw, source_published_at=supplied) == expected
    snapshot = shared(etf_flows=(raw,), etf_source_publication_times=publications)
    (copy,) = snapshot.etf_flows
    assert copy.available_at == expected
    # Only the field the flow owner reads changes; AUM and ingestion stay raw.
    assert replace(copy, available_at=raw.available_at) == raw
    (entry,) = snapshot.availability
    assert entry.modelled_available_at == expected
    assert entry.raw_available_at == raw.available_at
    assert entry.raw_ingested_at == raw.ingested_at
    assert entry.source_published_at == supplied
    assert entry.observation_end == datetime.combine(
        trading_date + DAY, datetime.min.time(), tzinfo=UTC
    )
    assert (REVISION_HISTORY_UNAVAILABLE in entry.labels) is labelled


@pytest.mark.parametrize(
    "raw_available_at",
    [utc(2024, 3, 4, 8, 2), BULK_INGESTED_AT],
)
def test_funding_settled_at_s_is_available_at_s(raw_available_at: datetime) -> None:
    raw = funding_rate(utc(2024, 3, 4, 8), available_at=raw_available_at)

    assert modelled_funding_rate_available_at(raw) == utc(2024, 3, 4, 8)
    snapshot = shared(funding_rates=(raw,))
    (copy,) = snapshot.funding_rates
    assert copy.available_at == utc(2024, 3, 4, 8)
    assert replace(copy, available_at=raw.available_at) == raw
    (entry,) = snapshot.availability
    assert dict(entry.raw_times) == {"available_at": raw_available_at, "ingested_at": BULK_INGESTED_AT}


def test_an_open_interest_snapshot_is_available_at_its_instant() -> None:
    raw = open_interest(utc(2024, 3, 4, 13))

    assert modelled_open_interest_available_at(raw) == utc(2024, 3, 4, 13)
    (copy,) = shared(open_interest=(raw,)).open_interest
    assert copy.available_at == utc(2024, 3, 4, 13)
    assert replace(copy, available_at=raw.available_at) == raw


@pytest.mark.parametrize(
    ("timeframe", "start", "end"),
    [
        ("1h", utc(2024, 3, 4, 13), utc(2024, 3, 4, 14)),
        ("1d", utc(2024, 3, 4), utc(2024, 3, 5)),
        ("1w", utc(2024, 3, 4), utc(2024, 3, 11)),
        ("1h", utc(2025, 12, 31, 23), utc(2026, 1, 1)),
    ],
)
def test_a_perp_volume_interval_is_available_at_its_end(
    timeframe: str,
    start: datetime,
    end: datetime,
) -> None:
    raw = perp_volume(start, timeframe=timeframe)

    assert modelled_perp_volume_available_at(raw) == end
    (copy,) = shared(perp_volumes=(raw,)).perp_volumes
    assert copy.available_at == end
    assert copy.observation_time == start
    assert replace(copy, available_at=raw.available_at) == raw


@pytest.mark.parametrize("timeframe", ["4h", "5m", "1y"])
def test_a_perp_volume_interval_the_owner_cannot_close_is_refused(timeframe: str) -> None:
    assert_refused(
        "UNSUPPORTED_OBSERVATION_INTERVAL",
        shared,
        perp_volumes=(perp_volume(utc(2024, 3, 4), timeframe=timeframe),),
    )


def test_the_availability_rules_render_the_policy_table() -> None:
    rules = {family: rule.as_record() for family, rule in REPLAY_AVAILABILITY_RULES.items()}

    assert rules[REFERENCE_PRICE_FAMILY]["modelled_availability"] == "BAR_CLOSE_BOUNDARY"
    assert rules[REFERENCE_PRICE_FAMILY]["availability_field"] == "ingested_at"
    assert rules[SHARED_VOLUME_FAMILY]["availability_field"] == "ingested_at"
    assert rules[ETF_FLOW_FAMILY]["availability_field"] == "available_at"
    assert rules[ETF_FLOW_FAMILY]["modelled_availability"] == (
        "T_PLUS_2_0000_UTC_OR_LATER_SOURCE_PUBLICATION"
    )
    assert rules[FUNDING_RATE_FAMILY]["modelled_availability"] == "SETTLEMENT_INSTANT"
    assert rules[OPEN_INTEREST_FAMILY]["observation_convention"] == "SNAPSHOT_INSTANT"
    assert rules[PERP_VOLUME_FAMILY]["observation_convention"] == "INTERVAL_START"
    assert rules[PERP_VOLUME_FAMILY]["modelled_availability"] == "INTERVAL_END"
    # The start reading is a surfaced assumption, not an owner fact.
    assert rules[PERP_VOLUME_FAMILY]["observation_convention_basis"].startswith("ASSUMED:")
    assert "RBT-003 must stamp interval starts" in rules[PERP_VOLUME_FAMILY]["observation_convention_basis"]
    assert set(rules) == {REFERENCE_PRICE_FAMILY, *SHARED_SNAPSHOT_FAMILIES}


def test_every_replay_copy_differs_from_its_raw_record_only_in_the_owner_read_field() -> None:
    inputs = mixed_inputs()
    snapshot, dataset = build_mixed(inputs)

    def by(records: tuple[Any, ...], key: Any) -> list[Any]:
        return sorted(records, key=key)

    raw_price = by(inputs["price"], lambda bar: bar.timestamp)
    assert [replace(copy, ingested_at=raw.ingested_at) for copy, raw in zip(dataset.price_bars, raw_price)] == raw_price
    raw_volume = by(inputs["volume"], lambda bar: bar.timestamp)
    assert [replace(copy, ingested_at=raw.ingested_at) for copy, raw in zip(snapshot.volume_bars, raw_volume)] == raw_volume
    raw_etf = by(inputs["etf"], lambda flow: (flow.fund, flow.observation_date, flow.provider, flow.revision))
    assert [replace(copy, available_at=raw.available_at) for copy, raw in zip(snapshot.etf_flows, raw_etf)] == raw_etf
    for replayed, raw_records in (
        (snapshot.funding_rates, inputs["funding"]),
        (snapshot.open_interest, inputs["open_interest"]),
    ):
        ordered = by(raw_records, lambda row: (row.observation_time, row.exchange, row.instrument))
        assert [replace(copy, available_at=raw.available_at) for copy, raw in zip(replayed, ordered)] == ordered
    raw_perp = by(inputs["perp"], lambda row: (row.observation_time, row.exchange, row.symbol, row.timeframe))
    assert [replace(copy, available_at=raw.available_at) for copy, raw in zip(snapshot.perp_volumes, raw_perp)] == raw_perp
    # Every ingestion field outside the bar families keeps its raw value.
    for record in (*snapshot.etf_flows, *snapshot.funding_rates, *snapshot.open_interest, *snapshot.perp_volumes):
        assert record.ingested_at == BULK_INGESTED_AT


def test_modelled_availability_is_never_earlier_than_the_observation_close_or_end() -> None:
    inputs = mixed_inputs()
    snapshot, dataset = build_mixed(inputs)
    raw = raw_index(inputs)
    supplied = supplied_times(inputs)

    for copy, entry in replayed_pairs(snapshot, dataset):
        record = raw[record_key(copy)]
        # The oracle reads only the raw record and the policy table.
        assert entry.observation_end == policy_observation_end(record)
        assert entry.modelled_available_at == policy_availability(record, supplied)
        assert entry.modelled_available_at >= policy_observation_end(record)
    ends = {
        entry.family: entry.modelled_available_at - entry.observation_end
        for entry in (*dataset.price_availability, *snapshot.availability)
        if entry.source_published_at is None
    }
    # Bars, funding, open interest and perp volume sit exactly at the end;
    # an ETF day is modelled one full UTC day after the day it describes.
    assert ends == {
        REFERENCE_PRICE_FAMILY: timedelta(0),
        SHARED_VOLUME_FAMILY: timedelta(0),
        FUNDING_RATE_FAMILY: timedelta(0),
        OPEN_INTEREST_FAMILY: timedelta(0),
        PERP_VOLUME_FAMILY: timedelta(0),
        ETF_FLOW_FAMILY: DAY,
    }


def test_every_record_without_revision_history_is_labelled_and_counted() -> None:
    snapshot, dataset = build_mixed(mixed_inputs())
    manifest = dataset.manifest
    families = snapshot.manifest["families"]

    labelled = [entry for entry in snapshot.availability if REVISION_HISTORY_UNAVAILABLE in entry.labels]
    # Only the two FBTC revisions carry source publication times.
    assert len(snapshot.availability) - len(labelled) == 2
    assert {
        family: families[family]["revision_history_unavailable_count"] for family in families
    } == {
        family: len([entry for entry in labelled if entry.family == family])
        for family in SHARED_SNAPSHOT_FAMILIES
    }
    assert families[ETF_FLOW_FAMILY]["revision_history_unavailable_count"] == 3
    assert snapshot.manifest["revision_history_unavailable_count"] == len(labelled)
    assert manifest["price_series"]["revision_history_unavailable_count"] == len(dataset.price_bars)
    assert manifest["revision_history_unavailable_count"] == len(dataset.price_bars) + len(labelled)


# --- point in time through the owners' own predicates ---------------------------


class VisibilityRecorder:
    def __init__(self) -> None:
        self.seen: list[tuple[datetime, datetime, tuple[datetime, ...]]] = []

    def __call__(self, context: BacktestContext) -> None:
        self.seen.append(
            (context.as_of, context.bar.timestamp, tuple(bar.timestamp for bar in context.bars))
        )
        return None


def random_inputs(rng: random.Random) -> dict[str, tuple[Any, ...]]:
    start = utc(2024, 3, 4) + rng.randrange(0, 20 * 24) * HOUR
    hours = rng.randrange(60, 110)
    missing = set(rng.sample(range(1, hours - 1), k=rng.randrange(0, 6)))
    price = hourly_series(start, hours, missing=missing)
    first_day = start.date()
    days = [first_day + offset * DAY for offset in range(hours // 24 + 1)]
    etf: list[EtfFlow] = []
    publications: list[EtfSourcePublicationTime] = []
    refused_groups: list[tuple[tuple[EtfFlow, ...], tuple[EtfSourcePublicationTime, ...]]] = []
    for fund in ("IBIT", "FBTC", "ARKB"):
        for day in days:
            roll = rng.random()
            if roll < 0.15:
                continue
            if roll < 0.55:
                # A dated history of two or three rows: labels drawn independently
                # of publication order, sometimes two providers, times on both
                # sides of the T+2 floor.
                rows, dated = [], []
                for label in rng.sample(REVISION_LABELS, k=rng.choice((2, 2, 3))):
                    provider = rng.choice(("fixture-etf", "fixture-etf-b"))
                    # Mostly before the T+2 floor (48h), so floor ties are common.
                    published = utc_midnight(day) + timedelta(minutes=rng.randrange(20 * 60, 60 * 60))
                    rows.append(
                        etf_flow(fund, day, flow=str(rng.randrange(-500, 500)), revision=label, provider=provider)
                    )
                    dated.append(EtfSourcePublicationTime(fund, day, provider, label, published))
                if owner_replays_in_publication_order(rows, dated):
                    etf.extend(rows)
                    publications.extend(dated)
                else:
                    refused_groups.append((tuple(rows), tuple(dated)))
                continue
            etf.append(etf_flow(fund, day, flow=str(rng.randrange(-500, 500))))
            if rng.random() < 0.3:
                publications.append(
                    EtfSourcePublicationTime(
                        fund,
                        day,
                        "fixture-etf",
                        "initial",
                        datetime.combine(day, datetime.min.time(), tzinfo=UTC)
                        + timedelta(minutes=rng.randrange(0, 5 * 24 * 60)),
                    )
                )
    first_settlement = datetime.combine(first_day, datetime.min.time(), tzinfo=UTC) + 8 * HOUR
    funding = tuple(
        funding_rate(
            first_settlement + 8 * k * HOUR,
            rate=str(Decimal(rng.randrange(-20, 40)) / Decimal(100000)),
            available_at=rng.choice(
                (BULK_INGESTED_AT, first_settlement + 8 * k * HOUR + timedelta(minutes=2))
            ),
        )
        for k in range(hours // 8)
        if rng.random() > 0.15
    )
    oi = tuple(
        open_interest(start + k * HOUR, value=str(50000 + rng.randrange(0, 900)))
        for k in range(hours)
        if rng.random() > 0.2
    )
    perp = tuple(
        perp_volume(start + k * HOUR, notional=str(600000 + rng.randrange(0, 90000)))
        for k in range(hours)
        if rng.random() > 0.2
    ) + tuple(
        perp_volume(datetime.combine(day, datetime.min.time(), tzinfo=UTC), timeframe="1d")
        for day in days[1:-1]
    )
    return {
        "price": price,
        "volume": price,
        "etf": tuple(etf),
        "publication": tuple(publications),
        "funding": funding,
        "open_interest": oi,
        "perp": perp,
        "refused_etf_groups": tuple(refused_groups),
    }


REVISION_LABELS = ("initial", "final", "corrected", "r1", "r2", "r3")
PROPERTY_SEEDS = (3, 17, 29, 101, 8675309)


def owner_replays_in_publication_order(
    rows: list[EtfFlow],
    dated: list[EtfSourcePublicationTime],
) -> bool:
    """Ask the real flow owner whether one fund-and-date history replays in publication order.

    Replay copies take the policy availability. The owner's choice is probed at
    every availability, one microsecond after it and between availabilities. At
    each probe it must be the latest-published row visible then. Equal
    publication instants have no later row, so they never replay.
    """

    supplied = {item.key(): item.published_at for item in dated}
    times = [supplied[(row.fund, row.observation_date, row.provider, row.revision)] for row in rows]
    if len(set(times)) != len(times):
        return False
    copies = [replace(row, available_at=policy_availability(row, supplied)) for row in rows]
    availabilities = sorted({copy.available_at for copy in copies})
    probes = {*availabilities, *(at + MICROSECOND for at in availabilities)}
    probes |= {early + (late - early) / 2 for early, late in zip(availabilities, availabilities[1:])}
    for probe in sorted(probes):
        visible = [(copy, at) for copy, at in zip(copies, times, strict=True) if copy.available_at <= probe]
        if not visible:
            continue
        chosen = flow_owner._latest_available_flows_by_fund_date(
            copies, as_of=probe, funds=(), end_date=None
        )[(rows[0].fund, rows[0].observation_date)]
        if chosen is not max(visible, key=lambda item: item[1])[0]:
            return False
    return True


def test_the_property_generator_produces_both_replayable_and_refused_histories() -> None:
    """Guard against a vacuous generator: floor ties occur both ways round."""

    admitted_ties = refused = 0
    for seed in PROPERTY_SEEDS:
        inputs = random_inputs(random.Random(seed))
        refused += len(inputs["refused_etf_groups"])
        supplied = supplied_times(inputs)
        floor_tied: dict[tuple[str, date], int] = {}
        for flow in inputs["etf"]:
            published = supplied.get((flow.fund, flow.observation_date, flow.provider, flow.revision))
            if published is not None and published <= utc_midnight(flow.observation_date) + 2 * DAY:
                floor_tied[(flow.fund, flow.observation_date)] = floor_tied.get((flow.fund, flow.observation_date), 0) + 1
        admitted_ties += sum(1 for count in floor_tied.values() if count > 1)
    assert refused >= 3
    assert admitted_ties >= 3


@pytest.mark.parametrize("seed", PROPERTY_SEEDS)
def test_no_replay_input_is_visible_before_its_modelled_availability(seed: int) -> None:
    """Every owner predicate sees a replay input exactly from its policy availability.

    The expected availability comes from the raw records and the policy table
    (the oracle above), never from the builder, so a builder that shifted both
    a replay field and its manifest entry would still fail here.
    """

    rng = random.Random(seed)
    inputs = random_inputs(rng)
    # Histories the owner would serve out of publication order are refused;
    # every other history, floor ties included, builds below.
    for rows, dated in inputs["refused_etf_groups"]:
        assert_refused(
            "ETF_REVISION_ORDER_UNAVAILABLE",
            shared,
            etf_flows=rows,
            etf_source_publication_times=dated,
        )
    snapshot, dataset = build_mixed(inputs)
    raw = raw_index(inputs)
    supplied = supplied_times(inputs)
    expected: dict[int, datetime] = {}
    for copy, entry in replayed_pairs(snapshot, dataset):
        oracle = policy_availability(raw[record_key(copy)], supplied)
        # The manifest claims the availability the policy table gives.
        assert entry.modelled_available_at == oracle
        expected[id(copy)] = oracle

    price_available = {bar.timestamp: expected[id(bar)] for bar in dataset.price_bars}
    derivatives = (*snapshot.funding_rates, *snapshot.open_interest, *snapshot.perp_volumes)
    first, last = dataset.price_bars[0].timestamp, dataset.price_bars[-1].timestamp
    boundaries = sorted(set(expected.values()))
    instants = [
        moment + delta
        for moment in rng.sample(boundaries, k=min(25, len(boundaries)))
        for delta in (timedelta(0), -MICROSECOND)
    ]
    instants += [
        first - DAY + timedelta(seconds=rng.randrange(0, int((last - first + 5 * DAY).total_seconds())))
        for _ in range(25)
    ]

    for decision_at in instants:
        # BTC-040's own 1h point-in-time predicate.
        for bar in dataset.price_bars:
            assert ohlcv_owner._source_bar_is_point_in_time_available(bar, decision_at, "1h") is (
                expected[id(bar)] <= decision_at
            )
        for derived in replay_market_bars_at(dataset.price_bars, decision_at=decision_at, window=DATA_WINDOW):
            bucket_end = ohlcv_owner.next_bar_timestamp(derived.timestamp, derived.timeframe)
            assert derived.ingested_at == bucket_end <= decision_at
            assert all(
                at <= decision_at
                for hour, at in price_available.items()
                if derived.timestamp <= hour < bucket_end
            )

        # features.flow keeps, per fund and date, the latest revision available.
        selected = flow_owner._latest_available_flows_by_fund_date(
            snapshot.etf_flows,
            as_of=decision_at,
            funds=(),
            end_date=None,
        )
        visible: dict[tuple[str, date], list[EtfFlow]] = {}
        for flow in snapshot.etf_flows:
            if expected[id(flow)] <= decision_at:
                visible.setdefault((flow.fund, flow.observation_date), []).append(flow)
        assert set(selected) == set(visible)
        for key, rows in visible.items():
            latest = max(
                rows,
                key=lambda flow: supplied.get(
                    (flow.fund, flow.observation_date, flow.provider, flow.revision),
                    datetime.min.replace(tzinfo=UTC),
                ),
            )
            assert selected[key] is latest

        # data.derivatives: every row the aggregate reads, and nothing later.
        aggregate = aggregate_btc_derivatives_available_at(list(derivatives), decision_at)
        assert aggregate.source_record_count == sum(
            1 for row in derivatives if expected[id(row)] <= decision_at
        )

        # features.positioning reads the latest settlement and snapshot available.
        settled = [row.observation_time for row in snapshot.funding_rates if expected[id(row)] <= decision_at]
        assert funding_health(snapshot.funding_rates, as_of=decision_at).observation_time == max(
            settled, default=decision_at
        )
        observed = [row.observation_time for row in snapshot.open_interest if expected[id(row)] <= decision_at]
        assert open_interest_growth_health(
            snapshot.open_interest,
            as_of=decision_at,
            open_interest_unit="BTC",
        ).observation_time == max(observed, default=decision_at)

        # features.flow spot participation reads bar ingested_at and perp available_at.
        participation = spot_perp_participation_from_rows(
            snapshot.volume_bars,
            snapshot.perp_volumes,
            as_of=decision_at,
        )
        assert participation.source_record_count == sum(
            1 for row in (*snapshot.volume_bars, *snapshot.perp_volumes) if expected[id(row)] <= decision_at
        )

    # BTC-180: each decision sees exactly the bars available at its instant.
    recorder = VisibilityRecorder()
    run_backtest(
        dataset.price_bars,
        strategy=recorder,
        symbol=BITSTAMP_REPLAY_VENUE.symbol,
        starting_nav=NAV,
        strategy_config=CONFIG,
    )
    assert len(recorder.seen) == len(dataset.price_bars)
    for as_of, bar_timestamp, visible_bars in recorder.seen:
        assert as_of == price_available[bar_timestamp] == bar_timestamp + HOUR
        assert set(visible_bars) == {
            timestamp for timestamp, at in price_available.items() if at <= as_of
        }


def test_the_raw_backfill_is_invisible_to_every_owner_inside_the_window() -> None:
    inputs = mixed_inputs()
    decision_at = MIXED_START + 5 * DAY

    assert build_canonical_market_bars(inputs["price"], data_available_at=decision_at) == ()
    assert flow_owner._latest_available_flows_by_fund_date(
        inputs["etf"], as_of=decision_at, funds=(), end_date=None
    ) == {}
    assert aggregate_btc_derivatives_available_at(
        [*inputs["funding"], *inputs["open_interest"], *inputs["perp"]],
        decision_at,
    ).source_record_count == 0
    assert spot_perp_participation_from_rows(
        inputs["volume"], inputs["perp"], as_of=decision_at
    ).source_record_count == 0
    snapshot, _ = build_mixed(inputs)
    assert aggregate_btc_derivatives_available_at(
        [*snapshot.funding_rates, *snapshot.open_interest, *snapshot.perp_volumes],
        decision_at,
    ).source_record_count == len(snapshot.funding_rates) + len(snapshot.open_interest) + len(
        snapshot.perp_volumes
    )


def test_a_revision_is_never_visible_before_its_supplied_publication() -> None:
    day = date(2024, 3, 5)
    flows = (
        etf_flow("FBTC", day, flow="10", revision="r1"),
        etf_flow("FBTC", day, flow="12", revision="r2"),
    )
    publications = (
        EtfSourcePublicationTime("FBTC", day, "fixture-etf", "r1", utc(2024, 3, 5, 23, 40)),
        EtfSourcePublicationTime("FBTC", day, "fixture-etf", "r2", utc(2024, 3, 8, 14, 5)),
    )
    snapshot = shared(etf_flows=flows, etf_source_publication_times=publications)

    def selected_flow(decision_at: datetime) -> Decimal | None:
        chosen = flow_owner._latest_available_flows_by_fund_date(
            snapshot.etf_flows, as_of=decision_at, funds=(), end_date=None
        )
        return chosen[("FBTC", day)].flow_usd if chosen else None

    assert selected_flow(utc(2024, 3, 7) - MICROSECOND) is None
    assert selected_flow(utc(2024, 3, 7)) == Decimal("10")
    assert selected_flow(utc(2024, 3, 8, 14, 5) - MICROSECOND) == Decimal("10")
    assert selected_flow(utc(2024, 3, 8, 14, 5)) == Decimal("12")


def owner_choice(snapshot: SharedReplaySnapshot, fund: str, day: date, decision_at: datetime) -> EtfFlow:
    return flow_owner._latest_available_flows_by_fund_date(
        snapshot.etf_flows, as_of=decision_at, funds=(), end_date=None
    )[(fund, day)]


@pytest.mark.parametrize(
    ("earlier", "later", "replayable"),
    [
        ("r1", "r2", True),
        ("2024-03-05T22:00Z", "2024-03-06T15:00Z", True),
        # 'initial' sorts above 'final', so the owner would keep the superseded row.
        ("initial", "final", False),
        ("initial", "corrected", False),
    ],
)
def test_revisions_tied_at_the_t_plus_2_floor_replay_only_in_publication_order(
    earlier: str,
    later: str,
    replayable: bool,
) -> None:
    """Both revisions are public before T+2, so the floor gives them one availability.

    The owner then breaks the tie by label. The replay is admitted only when that
    choice is the later publication; otherwise it would serve the superseded
    value at every decision instant, forever.
    """

    day = date(2024, 3, 5)
    flows = (
        etf_flow("FBTC", day, flow="10", revision=earlier),
        etf_flow("FBTC", day, flow="12", revision=later),
    )
    times = (
        EtfSourcePublicationTime("FBTC", day, "fixture-etf", earlier, utc(2024, 3, 5, 22)),
        EtfSourcePublicationTime("FBTC", day, "fixture-etf", later, utc(2024, 3, 6, 15)),
    )

    if not replayable:
        error = assert_refused(
            "ETF_REVISION_ORDER_UNAVAILABLE",
            shared,
            etf_flows=flows,
            etf_source_publication_times=times,
        )
        assert "breaks that tie by label" in str(error)
        return
    snapshot = shared(etf_flows=flows, etf_source_publication_times=times)
    for decision_at in (utc(2024, 3, 7), utc(2024, 3, 20), utc(2025, 6, 1)):
        assert owner_choice(snapshot, "FBTC", day, decision_at).flow_usd == Decimal("12")


def test_a_revision_published_after_the_floor_replays_at_its_own_time_whatever_its_label() -> None:
    day = date(2024, 3, 5)
    flows = (
        etf_flow("FBTC", day, flow="10", revision="initial"),
        etf_flow("FBTC", day, flow="12", revision="final"),
    )
    times = (
        EtfSourcePublicationTime("FBTC", day, "fixture-etf", "initial", utc(2024, 3, 5, 22)),
        EtfSourcePublicationTime("FBTC", day, "fixture-etf", "final", utc(2024, 3, 9, 15)),
    )
    snapshot = shared(etf_flows=flows, etf_source_publication_times=times)

    assert owner_choice(snapshot, "FBTC", day, utc(2024, 3, 7)).flow_usd == Decimal("10")
    assert owner_choice(snapshot, "FBTC", day, utc(2024, 3, 9, 15) - MICROSECOND).flow_usd == Decimal("10")
    assert owner_choice(snapshot, "FBTC", day, utc(2024, 3, 9, 15)).flow_usd == Decimal("12")


def test_rows_from_two_providers_for_one_fund_and_date_replay_only_in_publication_order() -> None:
    """The owner keys one row per fund and date across providers."""

    day = date(2024, 3, 5)
    first = etf_flow("IBIT", day, flow="10", provider="provider-a")
    second = etf_flow("IBIT", day, flow="11", provider="provider-b")

    assert_refused("ETF_REVISION_ORDER_UNAVAILABLE", shared, etf_flows=(first, second))
    # Both public before T+2: the owner would keep provider-b by name although
    # provider-a published later.
    assert_refused(
        "ETF_REVISION_ORDER_UNAVAILABLE",
        shared,
        etf_flows=(first, second),
        etf_source_publication_times=(
            EtfSourcePublicationTime("IBIT", day, "provider-a", "initial", utc(2024, 3, 6, 1)),
            EtfSourcePublicationTime("IBIT", day, "provider-b", "initial", utc(2024, 3, 5, 23)),
        ),
    )
    snapshot = shared(
        etf_flows=(first, second),
        etf_source_publication_times=(
            EtfSourcePublicationTime("IBIT", day, "provider-a", "initial", utc(2024, 3, 8)),
            EtfSourcePublicationTime("IBIT", day, "provider-b", "initial", utc(2024, 3, 5, 23)),
        ),
    )
    assert owner_choice(snapshot, "IBIT", day, utc(2024, 3, 7)).provider == "provider-b"
    assert owner_choice(snapshot, "IBIT", day, utc(2024, 3, 8)).provider == "provider-a"


def test_a_publication_time_before_its_trading_date_is_refused() -> None:
    """An impossible date (say a day/month swap) must not decide revision order or shed a label."""

    day = date(2024, 3, 5)
    flows = (
        etf_flow("FBTC", day, flow="10", revision="initial"),
        etf_flow("FBTC", day, flow="12", revision="final"),
    )
    error = assert_refused(
        "SOURCE_PUBLICATION_BEFORE_OBSERVATION",
        shared,
        etf_flows=flows,
        etf_source_publication_times=(
            EtfSourcePublicationTime("FBTC", day, "fixture-etf", "initial", utc(2024, 3, 5, 23, 40)),
            EtfSourcePublicationTime("FBTC", day, "fixture-etf", "final", utc(2024, 2, 5)),
        ),
    )
    assert "before its own trading date" in str(error)
    assert_refused(
        "SOURCE_PUBLICATION_BEFORE_OBSERVATION",
        shared,
        etf_flows=flows[:1],
        etf_source_publication_times=(
            EtfSourcePublicationTime(
                "FBTC", day, "fixture-etf", "initial", datetime(2024, 3, 4, 23, 59, 59, 999999, tzinfo=UTC)
            ),
        ),
    )
    # The trading date's first instant is admissible; the T+2 floor still holds.
    (copy,) = shared(
        etf_flows=flows[:1],
        etf_source_publication_times=(EtfSourcePublicationTime("FBTC", day, "fixture-etf", "initial", utc(2024, 3, 5)),),
    ).etf_flows
    assert copy.available_at == utc(2024, 3, 7)


def test_every_floor_tied_instant_is_checked_not_only_the_last() -> None:
    """At the floor the owner keeps 'initial' by label although 'final' is newer.

    A third revision published later makes the owner right again at its own
    instant, so a check of only the last instant would admit this history.
    """

    day = date(2024, 3, 5)
    flows = (
        etf_flow("FBTC", day, flow="10", revision="initial"),
        etf_flow("FBTC", day, flow="12", revision="final"),
        etf_flow("FBTC", day, flow="13", revision="r3"),
    )
    times = (
        EtfSourcePublicationTime("FBTC", day, "fixture-etf", "initial", utc(2024, 3, 5, 22)),
        EtfSourcePublicationTime("FBTC", day, "fixture-etf", "final", utc(2024, 3, 6, 6)),
        EtfSourcePublicationTime("FBTC", day, "fixture-etf", "r3", utc(2024, 3, 9, 12)),
    )

    assert_refused("ETF_REVISION_ORDER_UNAVAILABLE", shared, etf_flows=flows, etf_source_publication_times=times)
    assert not owner_replays_in_publication_order(list(flows), list(times))


@pytest.mark.parametrize("reverse", [False, True], ids=["r1-first", "r2-first"])
def test_revisions_published_at_one_instant_are_refused_in_any_input_order(reverse: bool) -> None:
    day = date(2024, 3, 5)
    flows = [etf_flow("FBTC", day, flow="10", revision="r1"), etf_flow("FBTC", day, flow="12", revision="r2")]
    times = [
        EtfSourcePublicationTime("FBTC", day, "fixture-etf", "r1", utc(2024, 3, 6, 6)),
        EtfSourcePublicationTime("FBTC", day, "fixture-etf", "r2", utc(2024, 3, 6, 6)),
    ]
    if reverse:
        flows.reverse()
        times.reverse()

    assert_refused(
        "ETF_REVISION_ORDER_UNAVAILABLE",
        shared,
        etf_flows=tuple(flows),
        etf_source_publication_times=tuple(times),
    )


# --- the checked-in control --------------------------------------------------------


CONTROL_START = utc(2024, 3, 4)
CONTROL_HOURS = 7 * 24
CONTROL_ENTRY_BAR = utc(2024, 3, 5, 23)
CONTROL_EXIT_BAR = utc(2024, 3, 8, 23)
CONTROL_PLAN = {CONTROL_ENTRY_BAR: ARM_ENTRY_ACTION, CONTROL_EXIT_BAR: EXIT_ACTION}
CONTROL_RAW_DIGEST = "sha256:3d7811e57cead59dfdc300e0dc1b636c701ff5a5e119ba22f9eb26cf30e8bae2"


def control_candles() -> dict[int, dict[str, str]]:
    """Bitstamp ``/api/v2/ohlc`` rows for one week of March 2024 (synthetic prices)."""

    candles: dict[int, dict[str, str]] = {}
    previous_close = 63000
    for index in range(CONTROL_HOURS):
        opened_at = int((CONTROL_START + index * HOUR).timestamp())
        close = previous_close + 20 * ((index * 37) % 11 - 5) + 15
        candles[opened_at] = {
            "timestamp": str(opened_at),
            "open": str(previous_close),
            "high": str(max(previous_close, close) + 35 + (index % 4) * 12),
            "low": str(min(previous_close, close) - 40 - (index % 3) * 9),
            "close": str(close),
            "volume": f"{11 + index % 9}.{(index * 53) % 100:02d}",
        }
        previous_close = close
    return candles


class CannedBitstampApi:
    """Answers the Bitstamp adapter's paged requests from canned rows, newest first."""

    def __init__(self, candles: dict[int, dict[str, str]]) -> None:
        self.candles = candles
        self.urls: list[str] = []

    def __call__(self, url: str) -> dict[str, Any]:
        self.urls.append(url)
        query = parse_qs(urlsplit(url).query)
        start, end = int(query["start"][0]), int(query["end"][0])
        rows = [row for opened, row in sorted(self.candles.items()) if start <= opened <= end]
        return {"data": {"pair": "BTC/USD", "ohlc": list(reversed(rows))}}


class RecordingConnection:
    def __init__(self) -> None:
        self.statements: list[Any] = []

    def execute(self, statement: Any) -> None:
        self.statements.append(statement)


def control_backfill() -> tuple[Any, RecordingConnection, CannedBitstampApi]:
    """Run the real BTC-020 collector over the canned API, as a 2026 backfill would."""

    api = CannedBitstampApi(control_candles())
    connection = RecordingConnection()
    result = collect_btc_ohlcv(
        BitstampOhlcvProvider(request_json=api),
        connection,
        OhlcvCollectionRequest(
            exchange=BITSTAMP_EXCHANGE,
            symbol=BITSTAMP_BTC_USD_SYMBOL,
            provider=BITSTAMP_PROVIDER_ID,
            start=CONTROL_START,
            end=CONTROL_START + (CONTROL_HOURS - 1) * HOUR,
        ),
        ingested_at=BULK_INGESTED_AT,
    )
    return result, connection, api


def bars_digest(bars: tuple[OhlcvBar, ...]) -> str:
    payload = [
        [
            bar.timestamp.isoformat(),
            bar.exchange,
            bar.symbol,
            bar.provider,
            str(bar.open),
            str(bar.high),
            str(bar.low),
            str(bar.close),
            str(bar.volume),
            bar.ingested_at.isoformat(),
        ]
        for bar in bars
    ]
    return "sha256:" + hashlib.sha256(
        json.dumps(payload, separators=(",", ":")).encode("ascii")
    ).hexdigest()


def test_control_the_fixture_is_a_real_shaped_bulk_backfill() -> None:
    result, connection, api = control_backfill()
    raw = result.raw_bars

    assert bars_digest(raw) == CONTROL_RAW_DIGEST
    assert len(raw) == CONTROL_HOURS and result.missing_source_timestamps == ()
    assert {(bar.exchange, bar.symbol, bar.provider, bar.timeframe) for bar in raw} == {
        ("bitstamp", "BTC/USD", "bitstamp", "1h")
    }
    # One bulk ingestion time on every row, after the data it describes.
    assert {bar.ingested_at for bar in raw} == {BULK_INGESTED_AT}
    assert BULK_INGESTED_AT > raw[-1].timestamp + HOUR
    assert {bar.ingested_at for bar in result.derived_bars} == {BULK_INGESTED_AT}
    assert len(connection.statements) == 2
    assert api.urls and all("/btcusd/" in url for url in api.urls)


def test_control_the_bulk_backfill_replays_with_no_executable_decision() -> None:
    raw = control_backfill()[0].raw_bars
    strategy = ScriptedStrategy(CONTROL_PLAN)

    result = run_backtest(
        raw,
        strategy=strategy,
        symbol=BITSTAMP_BTC_USD_SYMBOL,
        starting_nav=NAV,
        strategy_config=CONFIG,
        strategy_id="rbt001:control",
    )

    # The plan's entry was decided, but only at the bulk ingestion instant.
    assert strategy.decisions == [(CONTROL_ENTRY_BAR, BULK_INGESTED_AT)]
    assert executed_decisions(result) == []
    assert result.trades == ()
    assert [event.status for event in events_of(result, "INTENT")] == ["QUEUED", "UNEXECUTED"]
    (unexecuted,) = events_of(result, "INTENT", "UNEXECUTED")
    assert unexecuted.reason_codes == ("DATASET_ENDED_BEFORE_ELIGIBLE_BAR",)
    assert "BACKTEST_INTENT_UNEXECUTED_END" in result.reason_codes
    # Nor does BTC-040 derive a single daily bar for the decision instant.
    assert build_canonical_market_bars(raw, data_available_at=CONTROL_ENTRY_BAR + HOUR) == ()


def test_control_the_replay_builder_restores_executed_decisions() -> None:
    raw = control_backfill()[0].raw_bars
    before = [bar.as_record() for bar in raw]
    snapshot = build_shared_replay_snapshot(window=DATA_WINDOW, volume_bars=raw)
    dataset = build_venue_replay_dataset(
        venue=BITSTAMP_REPLAY_VENUE,
        window=DATA_WINDOW,
        price_bars=raw,
        shared_snapshot=snapshot,
    )
    strategy = ScriptedStrategy(CONTROL_PLAN)

    result = run_backtest(
        dataset.price_bars,
        strategy=strategy,
        symbol=BITSTAMP_BTC_USD_SYMBOL,
        starting_nav=NAV,
        strategy_config=CONFIG,
        strategy_id="rbt001:control",
    )

    # Both decisions are taken at their daily decision instants and execute on
    # the next bar through the unchanged BTC-161 and BTC-163 owners.
    assert strategy.decisions == [
        (CONTROL_ENTRY_BAR, utc(2024, 3, 6)),
        (CONTROL_EXIT_BAR, utc(2024, 3, 9)),
    ]
    executed = executed_decisions(result)
    assert [(event.event_type, event.occurred_at) for event in executed] == [
        ("ENTRY_EXECUTION", utc(2024, 3, 6, 1)),
        ("EXIT_EXECUTION", utc(2024, 3, 9, 1)),
    ]
    assert len(result.trades) == 1 and result.trades[0].closed
    assert "BACKTEST_INTENT_UNEXECUTED_END" not in result.reason_codes
    # The daily bars the champion reads now exist at the decision instant.
    assert [bar.timestamp for bar in dataset.market_bars_at(utc(2024, 3, 6), timeframes=("1d",))] == [
        utc(2024, 3, 4),
        utc(2024, 3, 5),
    ]
    # The raw backfill is untouched and the manifest keeps both timestamps.
    assert [bar.as_record() for bar in raw] == before
    records = dataset.manifest["price_series"]["records"]
    assert {record["raw"]["ingested_at"] for record in records} == {BULK_INGESTED_AT.isoformat()}
    assert [record["modelled_available_at"] for record in records] == [
        (CONTROL_START + (index + 1) * HOUR).isoformat() for index in range(CONTROL_HOURS)
    ]
    assert dataset.manifest["price_series"]["gap_count"] == 0


# --- stops, fills and funding on replayed bars -------------------------------------


STOP_START = utc(2024, 5, 6, 10)


def stop_bars(*, touched_on: int, ingested_delay: timedelta | None = None) -> tuple[OhlcvBar, ...]:
    """Ten flat hourly bars; ``touched_on`` trades through a 59,700 stop."""

    bars = []
    for index in range(10):
        timestamp = STOP_START + index * HOUR
        low = "59600" if index == touched_on else "59920"
        ingested_at = (
            BULK_INGESTED_AT if ingested_delay is None else timestamp + HOUR + ingested_delay
        )
        bars.append(hourly_bar(timestamp, low=low, high="60080", ingested_at=ingested_at))
    return tuple(bars)


STOP_PLAN = {STOP_START + 2 * HOUR: ARM_ENTRY_ACTION}
STOP_INVALIDATION = Decimal("0.995")


def test_a_replayed_stop_touch_resolves_at_its_bar_close_and_is_not_refused() -> None:
    dataset = venue_dataset(stop_bars(touched_on=5))

    result = scripted_run(dataset.price_bars, STOP_PLAN, invalidation=STOP_INVALIDATION)

    (entry,) = events_of(result, "ENTRY_EXECUTION", "EXECUTED")
    assert entry.occurred_at == STOP_START + 4 * HOUR
    assert entry.evidence["intent"]["decision_at"] == (STOP_START + 3 * HOUR).isoformat()
    resting = events_of(result, "STOP_EXECUTION", "RESTING")
    assert [event.occurred_at for event in resting] == [STOP_START + 4 * HOUR, STOP_START + 5 * HOUR]
    (stop,) = events_of(result, "STOP_EXECUTION", "EXECUTED")
    assert stop.occurred_at == STOP_START + 6 * HOUR
    assert stop.evidence["resolved_at"] == (STOP_START + 6 * HOUR).isoformat()
    assert "STOP_TOUCHED" in stop.reason_codes and "STOP_FILL_AT_STOP_PRICE" in stop.reason_codes
    assert result.stopped_out == 1
    (trade,) = result.trades
    assert trade.closed and trade.exit_reason == "STRUCTURAL_STOP"


@pytest.mark.parametrize(
    "delay",
    [MICROSECOND, timedelta(seconds=1), timedelta(minutes=5)],
    ids=["1us", "1s", "5min-epic-x"],
)
def test_the_same_series_with_any_ingestion_delay_is_refused_by_btc162(delay: timedelta) -> None:
    """Why policy section 4 models bars at their close, not EPIC X's close + 5 minutes.

    Any positive delay stamps the ENTER after the next bar's start, so BTC-162
    refuses that bar and the whole run aborts.
    """

    delayed = stop_bars(touched_on=5, ingested_delay=delay)

    with pytest.raises(ValueError, match="first eligible bar"):
        scripted_run(delayed, STOP_PLAN, invalidation=STOP_INVALIDATION)


def test_an_entry_bracket_touched_on_its_fill_bar_resolves_at_that_bar_close() -> None:
    dataset = venue_dataset(stop_bars(touched_on=3))

    result = scripted_run(dataset.price_bars, STOP_PLAN, invalidation=STOP_INVALIDATION)

    (entry,) = events_of(result, "ENTRY_EXECUTION", "EXECUTED")
    (stop,) = events_of(result, "STOP_EXECUTION", "EXECUTED")
    assert entry.occurred_at == stop.occurred_at == STOP_START + 4 * HOUR
    assert result.stopped_out == 1


def test_an_entry_fill_and_funding_run_through_the_unchanged_owners_on_replayed_bars() -> None:
    dataset = venue_dataset(stop_bars(touched_on=-1))
    plan = {STOP_START + 2 * HOUR: ARM_ENTRY_ACTION, STOP_START + 6 * HOUR: EXIT_ACTION}

    result = scripted_run(dataset.price_bars, plan, invalidation=STOP_INVALIDATION, cost_profile="stress")

    (entry,) = events_of(result, "ENTRY_EXECUTION", "EXECUTED")
    assert entry.evidence["resolved_at"] == (STOP_START + 4 * HOUR).isoformat()
    assert entry.evidence["execution_bar"]["ingested_at"] == (STOP_START + 4 * HOUR).isoformat()
    funding = events_of(result, "FUNDING", "APPLIED")
    # Carry is charged on every bar held entering it: bars 4..7, the exit bar included.
    assert [event.occurred_at for event in funding] == [STOP_START + (index + 1) * HOUR for index in range(4, 8)]
    for event in funding:
        assert event.evidence["observed_at"] == event.occurred_at.isoformat()
        assert event.evidence["effective_at"] == (event.occurred_at - MICROSECOND).isoformat()
    (exit_event,) = events_of(result, "EXIT_EXECUTION", "EXECUTED")
    assert exit_event.occurred_at == STOP_START + 8 * HOUR
    (trade,) = result.trades
    assert trade.closed and len(trade.funding_events) == 4 and trade.funding > 0


def test_a_gap_at_the_first_eligible_bar_expires_the_intent_rather_than_filling() -> None:
    gapped = tuple(bar for bar in stop_bars(touched_on=-1) if bar.timestamp != STOP_START + 3 * HOUR)
    dataset = venue_dataset(gapped)

    result = scripted_run(dataset.price_bars, STOP_PLAN, invalidation=STOP_INVALIDATION)

    assert executed_decisions(result) == []
    (expired,) = events_of(result, "INTENT", "EXPIRED")
    assert expired.reason_codes == ("FIRST_ELIGIBLE_BAR_MISSING",)
    assert dataset.manifest["price_series"]["missing_slot_count"] == 1


# --- refusals ------------------------------------------------------------------------


VALID_BAR = hourly_bar(utc(2024, 3, 4))


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(lambda: venue_dataset((hourly_bar(utc(2019, 12, 31, 23)), VALID_BAR)), id="price-bar"),
        pytest.param(lambda: shared(volume_bars=(hourly_bar(utc(2019, 12, 31, 23)), VALID_BAR)), id="volume-bar"),
        pytest.param(lambda: shared(etf_flows=(etf_flow("IBIT", date(2019, 12, 31)),)), id="etf-flow"),
        pytest.param(lambda: shared(funding_rates=(funding_rate(utc(2019, 12, 31, 16)),)), id="funding"),
        # Settled on the boundary, but it prices the 2019 period before it.
        pytest.param(lambda: shared(funding_rates=(funding_rate(utc(2020, 1, 1)),)), id="funding-accrued-in-2019"),
        pytest.param(lambda: shared(open_interest=(open_interest(utc(2019, 12, 31, 23, 59)),)), id="open-interest"),
        pytest.param(lambda: shared(perp_volumes=(perp_volume(utc(2019, 12, 31, 23)),)), id="perp-1h"),
        pytest.param(lambda: shared(perp_volumes=(perp_volume(utc(2019, 12, 31), timeframe="1d"),)), id="perp-1d"),
        pytest.param(lambda: shared(perp_volumes=(perp_volume(utc(2019, 12, 30), timeframe="1w"),)), id="perp-1w"),
    ],
)
def test_a_record_observed_before_2020_is_refused(build: Any) -> None:
    assert_refused("PRE_2020_RECORD_REFUSED", build)


def test_the_first_admissible_record_of_each_family_starts_on_2020_01_01() -> None:
    snapshot = shared(
        volume_bars=(hourly_bar(utc(2020, 1, 1)),),
        etf_flows=(etf_flow("IBIT", date(2020, 1, 1)),),
        funding_rates=(funding_rate(utc(2020, 1, 1, 8)),),
        open_interest=(open_interest(utc(2020, 1, 1)),),
        perp_volumes=(perp_volume(utc(2020, 1, 1)),),
    )

    assert len(snapshot.availability) == 5
    assert venue_dataset((hourly_bar(utc(2020, 1, 1)),), shared_snapshot=snapshot).price_bars


def test_a_refused_record_fails_the_whole_build_rather_than_being_dropped() -> None:
    good = hourly_series(utc(2024, 3, 4), 24)

    assert_refused("PRE_2020_RECORD_REFUSED", venue_dataset, (*good, hourly_bar(utc(2019, 12, 31, 23))))
    assert_refused(
        "PRE_2020_RECORD_REFUSED",
        shared,
        funding_rates=(funding_rate(utc(2024, 3, 4, 8)), funding_rate(utc(2019, 6, 1, 8))),
    )


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(lambda: venue_dataset((VALID_BAR, hourly_bar(utc(2026, 1, 1)))), id="price-bar"),
        pytest.param(lambda: shared(volume_bars=(hourly_bar(utc(2026, 6, 30, 23)),)), id="volume-bar"),
        pytest.param(lambda: shared(etf_flows=(etf_flow("IBIT", date(2026, 1, 2)),)), id="etf-flow"),
        pytest.param(lambda: shared(funding_rates=(funding_rate(utc(2026, 1, 1)),)), id="funding"),
        pytest.param(lambda: shared(open_interest=(open_interest(utc(2026, 3, 1)),)), id="open-interest"),
        # A weekly interval opened in 2025 that closes inside the holdout.
        pytest.param(lambda: shared(perp_volumes=(perp_volume(utc(2025, 12, 29), timeframe="1w"),)), id="perp-1w-straddle"),
    ],
)
def test_a_record_observed_in_the_holdout_is_refused(build: Any) -> None:
    assert_refused("HOLDOUT_RECORD_REFUSED", build)


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(lambda: venue_dataset((VALID_BAR, hourly_bar(utc(2026, 7, 1)))), id="price-bar"),
        pytest.param(lambda: shared(etf_flows=(etf_flow("IBIT", date(2027, 1, 4)),)), id="etf-flow"),
        pytest.param(lambda: shared(open_interest=(open_interest(utc(2030, 1, 1)),)), id="open-interest"),
    ],
)
def test_a_record_observed_in_the_reserve_is_refused(build: Any) -> None:
    assert_refused("RESERVE_RECORD_REFUSED", build)


def test_the_last_data_window_hour_is_admitted_even_though_it_closes_in_the_holdout() -> None:
    dataset = venue_dataset((hourly_bar(utc(2025, 12, 31, 23)),))

    assert dataset.price_bars[0].ingested_at == utc(2026, 1, 1)
    assert shared(etf_flows=(etf_flow("IBIT", date(2025, 12, 31)),)).etf_flows[0].available_at == utc(2026, 1, 2)


def test_the_holdout_window_is_shut_by_its_guard() -> None:
    error = assert_refused("HOLDOUT_WINDOW_NOT_AUTHORIZED", require_replay_window, HOLDOUT_WINDOW)
    assert "RBT-008" in str(error)
    assert_refused("HOLDOUT_WINDOW_NOT_AUTHORIZED", build_shared_replay_snapshot, window=HOLDOUT_WINDOW)
    assert_refused(
        "HOLDOUT_WINDOW_NOT_AUTHORIZED",
        build_venue_replay_dataset,
        venue=BITSTAMP_REPLAY_VENUE,
        window=HOLDOUT_WINDOW,
        price_bars=(VALID_BAR,),
        shared_snapshot=shared(),
    )


def test_the_reserve_and_prohibited_windows_are_never_replayed() -> None:
    assert_refused("RESERVE_WINDOW_REFUSED", build_shared_replay_snapshot, window=RESERVE_WINDOW)
    assert_refused("PROHIBITED_WINDOW_REFUSED", build_shared_replay_snapshot, window=PROHIBITED_WINDOW)
    assert_refused(
        "RESERVE_WINDOW_REFUSED",
        build_venue_replay_dataset,
        venue=BITSTAMP_REPLAY_VENUE,
        window=RESERVE_WINDOW,
        price_bars=(VALID_BAR,),
        shared_snapshot=shared(),
    )


@pytest.mark.parametrize(
    "window",
    [
        ReplayWindow("DATA", utc(2019, 1, 1), utc(2026, 1, 1)),
        ReplayWindow("DATA", utc(2020, 1, 1), utc(2026, 7, 1)),
        ReplayWindow("EVALUATION", utc(2024, 1, 11), utc(2026, 1, 1)),
        "DATA",
    ],
)
def test_a_window_outside_the_enumeration_is_refused(window: Any) -> None:
    assert_refused("UNKNOWN_REPLAY_WINDOW", build_shared_replay_snapshot, window=window)


def test_lifting_the_holdout_guard_would_open_nothing_but_the_holdout(monkeypatch: pytest.MonkeyPatch) -> None:
    """The constant is the one switch RBT-008 flips, in its own reviewed commit.

    Flipped here in-process only, it lets a holdout replay be requested but still
    refuses the reserve and everything before 2020, and a data-window replay
    still refuses holdout records. No holdout-dated record is built.
    """

    monkeypatch.setattr(replay, "HOLDOUT_OPENING_AUTHORIZED", True)

    assert require_replay_window(HOLDOUT_WINDOW) == HOLDOUT_WINDOW
    assert_refused(
        "RESERVE_RECORD_REFUSED",
        build_shared_replay_snapshot,
        window=HOLDOUT_WINDOW,
        open_interest=(open_interest(utc(2026, 7, 1)),),
    )
    assert_refused(
        "PRE_2020_RECORD_REFUSED",
        build_shared_replay_snapshot,
        window=HOLDOUT_WINDOW,
        open_interest=(open_interest(utc(2019, 12, 31, 23)),),
    )
    assert_refused("RESERVE_WINDOW_REFUSED", require_replay_window, RESERVE_WINDOW)
    assert_refused(
        "HOLDOUT_RECORD_REFUSED",
        shared,
        open_interest=(open_interest(utc(2026, 3, 1)),),
    )


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        (dict(exchange="coinbase", symbol="BTC-USD", provider="coinbase"), "MIXED_VENUE_SERIES_REFUSED"),
        (dict(provider="bitstamp-backfill"), "MIXED_VENUE_SERIES_REFUSED"),
        (dict(symbol="BTC/USDT"), "MIXED_VENUE_SERIES_REFUSED"),
        (dict(exchange="bitstamp-archive"), "MIXED_VENUE_SERIES_REFUSED"),
    ],
)
def test_a_mixed_venue_price_series_is_refused(changes: dict[str, str], reason: str) -> None:
    series = hourly_series(utc(2024, 3, 4), 6)
    spliced = (*series[:3], replace(series[3], **changes), *series[4:])

    assert_refused(reason, venue_dataset, spliced)


def test_every_venue_series_must_be_that_venue_and_the_engine_agrees() -> None:
    coinbase = hourly_series(utc(2024, 3, 4), 6, venue=COINBASE_REPLAY_VENUE)
    bitstamp = hourly_series(utc(2024, 3, 4, 6), 6)

    assert_refused("MIXED_VENUE_SERIES_REFUSED", venue_dataset, coinbase)
    assert venue_dataset(coinbase, venue=COINBASE_REPLAY_VENUE).price_bars
    assert_refused("SHARED_VOLUME_SOURCE_REFUSED", shared, volume_bars=coinbase)
    unknown = ReplayVenue("KRAKEN", "kraken", "BTC/USD", "kraken", "XBTUSD")
    assert_refused("UNKNOWN_REPLAY_VENUE", venue_dataset, bitstamp, venue=unknown)
    # The frozen engine already refuses provider splicing on its own.
    spliced = tuple(
        replace(bar, symbol=BITSTAMP_REPLAY_VENUE.symbol) for bar in coinbase
    ) + bitstamp
    with pytest.raises(ValueError, match="provider splicing"):
        run_backtest(spliced, strategy=lambda _: None, symbol="BTC/USD", starting_nav=NAV, strategy_config=CONFIG)


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(lambda: venue_dataset((VALID_BAR, VALID_BAR)), id="price-bar"),
        pytest.param(lambda: shared(volume_bars=(VALID_BAR, replace(VALID_BAR, close=Decimal("60001")))), id="volume-bar"),
        pytest.param(
            lambda: shared(
                etf_flows=(
                    etf_flow("IBIT", date(2024, 3, 4)),
                    etf_flow("IBIT", date(2024, 3, 4), available_at=utc(2026, 9, 29)),
                )
            ),
            id="etf-revision",
        ),
        pytest.param(lambda: shared(funding_rates=(funding_rate(utc(2024, 3, 4, 8)),) * 2), id="funding"),
        pytest.param(lambda: shared(open_interest=(open_interest(utc(2024, 3, 4, 8)), open_interest(utc(2024, 3, 4, 8), value="1"))), id="open-interest"),
        pytest.param(lambda: shared(perp_volumes=(perp_volume(utc(2024, 3, 4, 8)),) * 2), id="perp-volume"),
    ],
)
def test_a_duplicate_record_is_refused(build: Any) -> None:
    assert_refused("DUPLICATE_RECORD_REFUSED", build)


def test_etf_revisions_without_publication_times_cannot_be_ordered() -> None:
    day = date(2024, 3, 5)
    revisions = (etf_flow("FBTC", day, revision="r1"), etf_flow("FBTC", day, revision="r2"))
    one_time = (EtfSourcePublicationTime("FBTC", day, "fixture-etf", "r2", utc(2024, 3, 8)),)

    assert_refused("ETF_REVISION_ORDER_UNAVAILABLE", shared, etf_flows=revisions)
    assert_refused(
        "ETF_REVISION_ORDER_UNAVAILABLE",
        shared,
        etf_flows=revisions,
        etf_source_publication_times=one_time,
    )
    # Two revisions published at one instant: neither is the later one.
    assert_refused(
        "ETF_REVISION_ORDER_UNAVAILABLE",
        shared,
        etf_flows=revisions,
        etf_source_publication_times=(
            EtfSourcePublicationTime("FBTC", day, "fixture-etf", "r1", utc(2024, 3, 8)),
            EtfSourcePublicationTime("FBTC", day, "fixture-etf", "r2", utc(2024, 3, 8)),
        ),
    )
    assert_refused(
        "UNMATCHED_SOURCE_PUBLICATION_TIME",
        shared,
        etf_flows=revisions[:1],
        etf_source_publication_times=one_time,
    )
    assert_refused(
        "DUPLICATE_SOURCE_PUBLICATION_TIME",
        shared,
        etf_flows=revisions[1:],
        etf_source_publication_times=one_time * 2,
    )


@pytest.mark.parametrize(
    ("family", "record"),
    [
        (
            "funding_rates",
            FuturesBasis(
                observation_time=utc(2024, 3, 4, 8),
                exchange="deribit",
                symbol="BTC",
                instrument="BTC-29MAR24",
                expiry=utc(2024, 3, 29, 8),
                basis_rate=Decimal("0.01"),
                annualized_basis_rate=Decimal("0.15"),
                provider="deribit",
                source="fixture",
                available_at=BULK_INGESTED_AT,
                ingested_at=BULK_INGESTED_AT,
            ),
        ),
        (
            "perp_volumes",
            Liquidation(
                observation_time=utc(2024, 3, 4, 8),
                exchange="binance",
                symbol="BTCUSDT",
                timeframe="1h",
                side="long",
                quantity=Decimal("2"),
                quantity_unit="BTC",
                notional_usd=Decimal("120000"),
                provider="binance",
                source="fixture",
                available_at=BULK_INGESTED_AT,
                ingested_at=BULK_INGESTED_AT,
            ),
        ),
        ("volume_bars", {"timestamp": utc(2024, 3, 4)}),
        ("open_interest", funding_rate(utc(2024, 3, 4, 8))),
    ],
)
def test_a_record_the_policy_table_does_not_model_is_refused(family: str, record: Any) -> None:
    """Policy section 4 defines no availability for futures basis or liquidations."""

    assert_refused("RECORD_TYPE_REFUSED", shared, **{family: (record,)})


def test_a_naive_or_offset_timestamp_is_refused() -> None:
    naive = replace(VALID_BAR, timestamp=datetime(2024, 3, 4))
    offset = replace(VALID_BAR, timestamp=datetime.fromisoformat("2024-03-04T01:00:00+01:00"))

    assert_refused("NON_UTC_TIMESTAMP_REFUSED", venue_dataset, (naive,))
    assert_refused("NON_UTC_TIMESTAMP_REFUSED", venue_dataset, (offset,))
    assert_refused(
        "NON_UTC_TIMESTAMP_REFUSED",
        shared,
        funding_rates=(funding_rate(datetime(2024, 3, 4, 8)),),
    )


@pytest.mark.parametrize(
    ("family", "record"),
    [
        ("open_interest", replace(open_interest(utc(2024, 3, 4, 8)), open_interest=None)),
        ("open_interest", replace(open_interest(utc(2024, 3, 4, 8)), open_interest="51000")),
        ("funding_rates", replace(funding_rate(utc(2024, 3, 4, 8)), funding_rate=None)),
        ("perp_volumes", replace(perp_volume(utc(2024, 3, 4, 8)), volume=None)),
        ("etf_flows", replace(etf_flow("IBIT", date(2024, 3, 4)), flow_usd=None)),
        ("volume_bars", replace(VALID_BAR, volume=4.25)),
        ("etf_flows", replace(etf_flow("IBIT", date(2024, 3, 4)), flow_usd=Decimal("Infinity"))),
    ],
)
def test_an_owner_number_that_is_missing_or_not_a_finite_decimal_is_refused(family: str, record: Any) -> None:
    """Never zero-filled and never hashed as null: refused before any summary runs."""

    assert_refused("RECORD_TYPE_REFUSED", shared, **{family: (record,)})


def test_optional_owner_numbers_may_be_absent() -> None:
    snapshot = shared(
        etf_flows=(etf_flow("IBIT", date(2024, 3, 4), aum=None),),
        perp_volumes=(replace(perp_volume(utc(2024, 3, 4, 8)), notional_usd=None),),
    )

    assert snapshot.etf_flows[0].aum_usd is None
    assert snapshot.perp_volumes[0].notional_usd is None


def test_contrived_inputs_still_fail_with_a_declared_reason() -> None:
    # A funding interval reaching back past year 1, and one past timedelta's range.
    assert_refused(
        "PRE_2020_RECORD_REFUSED",
        shared,
        funding_rates=(funding_rate(utc(2024, 3, 4, 8), interval="1E8"),),
    )
    assert_refused(
        "UNSUPPORTED_OBSERVATION_INTERVAL",
        shared,
        funding_rates=(funding_rate(utc(2024, 3, 4, 8), interval="1E12"),),
    )
    # The far future is the reserve, refused before any interval arithmetic.
    assert_refused("RESERVE_RECORD_REFUSED", venue_dataset, (hourly_bar(datetime(9999, 12, 31, 23, tzinfo=UTC)),))
    assert_refused(
        "RESERVE_RECORD_REFUSED",
        shared,
        perp_volumes=(perp_volume(datetime(9999, 12, 31, 23, tzinfo=UTC)),),
    )
    assert_refused("RESERVE_RECORD_REFUSED", shared, etf_flows=(etf_flow("IBIT", date(9999, 12, 31)),))
    assert_refused("RECORD_TYPE_REFUSED", shared, etf_market_holidays=5)


def test_a_monthly_series_without_an_owner_grid_reports_its_gaps_as_not_evaluated() -> None:
    """Anchored on the 29th, the owner's month step fails at the next short February."""

    snapshot = shared(
        perp_volumes=(
            perp_volume(utc(2024, 1, 29), timeframe="1mo"),
            perp_volume(utc(2025, 3, 29), timeframe="1mo"),
        )
    )
    section = snapshot.manifest["families"][PERP_VOLUME_FAMILY]

    assert section["gap_count"] is None
    assert section["gap_not_evaluated_reasons"] == ["OWNER_GRID_UNDEFINED"]


def test_a_raw_record_its_owner_refuses_is_refused() -> None:
    early = funding_rate(utc(2024, 3, 4, 8), available_at=utc(2024, 3, 4, 7))

    assert_refused("OWNER_RECORD_REFUSED", shared, funding_rates=(early,))


def test_a_series_that_breaks_the_engine_bar_contract_is_refused() -> None:
    impossible = hourly_bar(utc(2024, 3, 4), low="61000", high="60100")
    off_boundary = replace(VALID_BAR, timestamp=utc(2024, 3, 4, 10, 30))

    assert_refused("ENGINE_BAR_CONTRACT_REFUSED", venue_dataset, (impossible,))
    assert_refused("ENGINE_BAR_CONTRACT_REFUSED", venue_dataset, (off_boundary,))
    assert_refused("EMPTY_PRICE_SERIES_REFUSED", venue_dataset, ())


def test_a_venue_dataset_needs_a_shared_snapshot_of_its_own_window() -> None:
    foreign = replace(shared(), window=HOLDOUT_WINDOW)

    assert_refused(
        "SHARED_SNAPSHOT_WINDOW_MISMATCH",
        build_venue_replay_dataset,
        venue=BITSTAMP_REPLAY_VENUE,
        window=DATA_WINDOW,
        price_bars=(VALID_BAR,),
        shared_snapshot=foreign,
    )


def test_a_build_leaves_every_raw_record_unchanged() -> None:
    inputs = mixed_inputs()
    before = {
        name: [record.as_record() for record in records]
        for name, records in inputs.items()
        if name != "publication"
    }
    identities = {name: [id(record) for record in records] for name, records in inputs.items()}

    snapshot, dataset = build_mixed(inputs)

    assert {
        name: [record.as_record() for record in records]
        for name, records in inputs.items()
        if name != "publication"
    } == before
    assert {name: [id(record) for record in records] for name, records in inputs.items()} == identities
    assert {bar.ingested_at for bar in inputs["price"]} == {BULK_INGESTED_AT}
    raw_ids = {id(record) for records in inputs.values() for record in records}
    replayed = (
        *dataset.price_bars,
        *snapshot.volume_bars,
        *snapshot.etf_flows,
        *snapshot.funding_rates,
        *snapshot.open_interest,
        *snapshot.perp_volumes,
    )
    assert not raw_ids & {id(record) for record in replayed}


def test_the_builder_needs_no_network_or_database(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_: Any, **__: Any) -> None:
        raise AssertionError("the replay builder opened a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)

    snapshot, dataset = build_mixed(mixed_inputs())
    assert dataset.manifest_sha256 and snapshot.manifest_sha256


# --- gaps ------------------------------------------------------------------------------


def test_bar_gaps_are_preserved_and_counted_per_series() -> None:
    series = hourly_series(utc(2024, 3, 4), 48, missing=(5, 6, 7, 20, 47))
    snapshot = shared(volume_bars=series)
    dataset = venue_dataset(series, shared_snapshot=snapshot)

    price = dataset.manifest["price_series"]
    assert len(dataset.price_bars) == price["record_count"] == 43
    assert price["gap_count"] == 2 and price["missing_slot_count"] == 4
    assert price["series"][0]["gaps"]["spans"] == [
        {"first_missing": utc(2024, 3, 4, 5).isoformat(), "last_missing": utc(2024, 3, 4, 7).isoformat(), "missing_slots": 3},
        {"first_missing": utc(2024, 3, 4, 20).isoformat(), "last_missing": utc(2024, 3, 4, 20).isoformat(), "missing_slots": 1},
    ]
    # A trailing absence is the series end, not an internal gap.
    assert price["series"][0]["last_observation"] == utc(2024, 3, 5, 22).isoformat()
    volume = snapshot.manifest["families"][SHARED_VOLUME_FAMILY]
    assert (volume["gap_count"], volume["missing_slot_count"]) == (2, 4)


def test_etf_publication_gaps_count_against_the_supplied_closure_table() -> None:
    days = [date(2024, 2, 12) + offset * DAY for offset in range(12)]
    publication_days = [day for day in days if day.weekday() < 5 and day != date(2024, 2, 19)]
    flows = tuple(etf_flow("IBIT", day) for day in publication_days if day != date(2024, 2, 21))
    closures = load_closures(date(2024, 1, 1), date(2024, 12, 31))
    assert date(2024, 2, 19) in closures

    counted = shared(etf_flows=flows, etf_market_holidays=closures).manifest
    section = counted["families"][ETF_FLOW_FAMILY]
    assert (section["gap_count"], section["missing_slot_count"]) == (1, 1)
    assert section["series"][0]["gaps"]["spans"] == [
        {"first_missing": "2024-02-21", "last_missing": "2024-02-21", "missing_slots": 1}
    ]
    assert counted["etf_market_holidays"] == sorted(day.isoformat() for day in closures)

    uncounted = shared(etf_flows=flows).manifest
    section = uncounted["families"][ETF_FLOW_FAMILY]
    assert section["gap_count"] is None and section["missing_slot_count"] is None
    assert section["series"][0]["gaps"]["not_evaluated_reason"] == "ETF_MARKET_HOLIDAYS_NOT_SUPPLIED"
    assert section["gap_not_evaluated_reasons"] == ["ETF_MARKET_HOLIDAYS_NOT_SUPPLIED"]
    assert uncounted["etf_market_holidays"] is None


def test_derivative_gaps_are_the_data_quality_owners_discontinuities() -> None:
    start = utc(2024, 3, 4)
    snapshot = shared(
        funding_rates=(
            *(funding_rate(start + 8 * k * HOUR) for k in range(1, 10) if k not in (4, 5)),
            # A settlement stamped 5 ms late is inside the owner's tolerance.
            *(
                funding_rate(
                    start + 8 * k * HOUR + (timedelta(milliseconds=5) if k == 3 else timedelta(0)),
                    exchange="bybit",
                )
                for k in range(1, 10)
            ),
        ),
        open_interest=(
            # A 2h jump is inside the owner's 3h provider-gap threshold; 4h is not.
            *(open_interest(start + k * HOUR) for k in range(12) if k != 4),
            *(open_interest(start + k * HOUR, exchange="bybit") for k in range(12) if k not in (4, 5, 6)),
        ),
        perp_volumes=tuple(perp_volume(start + k * HOUR) for k in range(10) if k not in (2, 3)),
    )
    families = snapshot.manifest["families"]

    funding = {item["identity"]["exchange"]: item["gaps"] for item in families[FUNDING_RATE_FAMILY]["series"]}
    assert funding["binance"]["method"] == "DATA_QUALITY_PROVIDER_DISCONTINUITY"
    assert funding["binance"]["spans"] == [
        {
            "previous_observation": (start + 24 * HOUR).isoformat(),
            "next_observation": (start + 48 * HOUR).isoformat(),
            "gap_seconds": 86400,
            "max_gap_seconds": 9 * 3600,
        }
    ]
    assert funding["bybit"]["gap_count"] == 0
    assert families[FUNDING_RATE_FAMILY]["gap_count"] == 1
    assert families[FUNDING_RATE_FAMILY]["missing_slot_count"] is None
    interest = {item["identity"]["exchange"]: item["gaps"] for item in families[OPEN_INTEREST_FAMILY]["series"]}
    assert interest["binance"]["gap_count"] == 0
    assert interest["bybit"]["spans"] == [
        {
            "previous_observation": (start + 3 * HOUR).isoformat(),
            "next_observation": (start + 7 * HOUR).isoformat(),
            "gap_seconds": 4 * 3600,
            "max_gap_seconds": 3 * 3600,
        }
    ]
    # Exactly the discontinuities the owner reports for the same rows.
    report = validate_derivatives_quality(
        [*snapshot.funding_rates, *snapshot.open_interest],
        as_of=start + 3 * DAY,
        config=DerivativesQualityConfig(),
    )
    assert sum(issue.reason_code == "PROVIDER_DISCONTINUITY" for issue in report.issues) == (
        families[FUNDING_RATE_FAMILY]["gap_count"] + families[OPEN_INTEREST_FAMILY]["gap_count"]
    )
    # Perpetual volume declares a timeframe, so it is counted on the bar grid.
    perp = families[PERP_VOLUME_FAMILY]
    assert (perp["gap_count"], perp["missing_slot_count"]) == (1, 2)


def test_an_absent_family_reports_no_gap_count_rather_than_zero() -> None:
    snapshot = shared(funding_rates=(funding_rate(utc(2024, 3, 4, 8)),))
    families = snapshot.manifest["families"]

    for family in (SHARED_VOLUME_FAMILY, ETF_FLOW_FAMILY, OPEN_INTEREST_FAMILY, PERP_VOLUME_FAMILY):
        section = families[family]
        assert section["record_count"] == 0
        assert section["gap_count"] is None and section["missing_slot_count"] is None
        assert section["gap_not_evaluated_reasons"] == ["FAMILY_HAS_NO_RECORDS"]
    assert families[FUNDING_RATE_FAMILY]["gap_count"] == 0
    assert families[FUNDING_RATE_FAMILY]["gap_not_evaluated_reasons"] == []
    venue = venue_dataset((VALID_BAR,), shared_snapshot=snapshot).manifest
    assert venue["shared_snapshot"]["families"][ETF_FLOW_FAMILY]["gap_count"] is None
    assert venue["shared_snapshot"]["families"][ETF_FLOW_FAMILY]["gap_not_evaluated_reasons"] == [
        "FAMILY_HAS_NO_RECORDS"
    ]


# --- the manifest ------------------------------------------------------------------------


def independently_canonical(document: bytes) -> bytes:
    """Sorted keys, no insignificant whitespace, ASCII: re-encoded here, not by the builder."""

    return json.dumps(
        json.loads(document.decode("ascii")),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def test_the_manifest_holds_policies_venue_window_digests_and_both_timestamps() -> None:
    inputs = mixed_inputs()
    snapshot, dataset = build_mixed(inputs)
    manifest = dataset.manifest
    raw = raw_index(inputs)
    supplied = supplied_times(inputs)

    for document in (manifest, snapshot.manifest):
        assert document["policy"] == "RESEARCH_BACKTEST_POLICY_V2"
        assert document["availability_policy"] == "HISTORICAL_REPLAY_AVAILABILITY_V1"
        assert document["builder_version"] == "BUILD_HISTORICAL_REPLAY_INPUTS_V1"
        assert document["evidence_class"] == "RESEARCH_BACKTEST_NON_CERTIFYING"
        assert document["canonical_reference"] == "UNRESOLVED"
        assert document["window"] == DATA_WINDOW.as_record()
        # The guard's state is not dataset content (see the RBT-008 flip test).
        assert "holdout_opening_authorized" not in document
    assert manifest["manifest_version"] == "HISTORICAL_REPLAY_DATASET_MANIFEST_V1"
    assert snapshot.manifest["manifest_version"] == "HISTORICAL_REPLAY_SHARED_SNAPSHOT_MANIFEST_V1"
    assert manifest["venue"] == BITSTAMP_REPLAY_VENUE.as_record()
    assert manifest["derived_market_bars"]["modelled_availability"] == "LAST_CONSTITUENT_HOUR_CLOSE_BOUNDARY"
    assert manifest["shared_snapshot"]["manifest_sha256"] == snapshot.manifest_sha256

    # Every input of every family: its owner's content digest, every raw time
    # field beside the modelled availability, checked against the raw record.
    sections = {REFERENCE_PRICE_FAMILY: manifest["price_series"], **snapshot.manifest["families"]}
    by_family: dict[str, list[tuple[Any, Any]]] = {}
    for copy, entry in replayed_pairs(snapshot, dataset):
        by_family.setdefault(entry.family, []).append((copy, entry))
    assert set(by_family) == set(sections)
    for family, pairs in by_family.items():
        section = sections[family]
        assert section["records"] == [entry.as_record() for _, entry in pairs]
        assert section["record_count"] == len(pairs)
        assert section["records_sha256"] == hashlib.sha256(
            independently_canonical(json.dumps(section["records"]).encode("ascii"))
        ).hexdigest()
        for (copy, entry), record in zip(pairs, section["records"], strict=True):
            source = raw[record_key(copy)]
            assert record["content_sha256"] == replay_record_content_sha256(family, source.as_record())
            expected_raw = {"ingested_at": source.ingested_at.isoformat()}
            if not isinstance(source, OhlcvBar):
                expected_raw["available_at"] = source.available_at.isoformat()
            assert record["raw"] == expected_raw
            assert set(record["raw"]) == set(REPLAY_AVAILABILITY_RULES[family].raw_time_fields)
            assert record["modelled_available_at"] == policy_availability(source, supplied).isoformat()

    for bytes_, digest in (
        (dataset.manifest_bytes, dataset.manifest_sha256),
        (snapshot.manifest_bytes, snapshot.manifest_sha256),
    ):
        assert hashlib.sha256(bytes_).hexdigest() == digest
        assert independently_canonical(bytes_) == bytes_


def test_every_raw_value_reaches_the_content_and_manifest_digests() -> None:
    """Change any one value of any one raw record and exactly that record's digest moves."""

    inputs = mixed_inputs()
    snapshot, dataset = build_mixed(inputs)
    before = {entry.content_sha256 for _, entry in replayed_pairs(snapshot, dataset)}
    mutations = {
        "price": ("close", Decimal("60003.5")),
        "volume": ("volume", Decimal("9.75")),
        "etf": ("flow_usd", Decimal("126.5")),
        "funding": ("funding_rate", Decimal("0.0002")),
        "open_interest": ("open_interest", Decimal("52000")),
        "perp": ("notional_usd", Decimal("650001")),
    }
    for name, (field_name, value) in mutations.items():
        changed = dict(inputs)
        records = list(changed[name])
        records[3] = replace(records[3], **{field_name: value})
        changed[name] = tuple(records)
        if name == "price":
            changed["volume"] = inputs["volume"]
        if name == "volume":
            changed["price"] = inputs["price"]
        mutated_snapshot, mutated_dataset = build_mixed(changed)
        after = {entry.content_sha256 for _, entry in replayed_pairs(mutated_snapshot, mutated_dataset)}
        assert len(after - before) == 1, name
        if name == "price":
            assert mutated_dataset.manifest_bytes != dataset.manifest_bytes
            assert mutated_snapshot.manifest_bytes == snapshot.manifest_bytes
        else:
            assert mutated_snapshot.manifest_sha256 != snapshot.manifest_sha256
            assert mutated_dataset.manifest_sha256 != dataset.manifest_sha256
    # A raw timestamp is content too: a different bulk ingestion time is a
    # different raw record, even though its modelled availability is unchanged.
    restamped = dict(inputs)
    restamped["price"] = tuple(replace(bar, ingested_at=utc(2026, 9, 29)) for bar in inputs["price"])
    _, restamped_dataset = build_mixed(restamped)
    assert [bar.ingested_at for bar in restamped_dataset.price_bars] == [bar.ingested_at for bar in dataset.price_bars]
    assert restamped_dataset.manifest_sha256 != dataset.manifest_sha256


def numeric_column(record: Any) -> Any:
    """The same record as a NUMERIC(38,18) / NUMERIC(10,4) read-back renders it."""

    changes = {}
    for name, value in vars(record).items():
        if isinstance(value, Decimal):
            scale = Decimal("1E-4") if name == "funding_interval_hours" else Decimal("1E-18")
            changes[name] = value.quantize(scale)
    return replace(record, **changes)


def test_record_digests_address_numbers_by_value_not_by_scale() -> None:
    inputs = mixed_inputs()
    read_back = {
        name: records if name == "publication" else tuple(numeric_column(record) for record in records)
        for name, records in inputs.items()
    }
    assert str(read_back["price"][0].close) != str(inputs["price"][0].close)
    assert str(read_back["funding"][0].funding_interval_hours) == "8.0000"

    snapshot, dataset = build_mixed(inputs)
    read_back_snapshot, read_back_dataset = build_mixed(read_back)

    assert read_back_snapshot.manifest_bytes == snapshot.manifest_bytes
    assert read_back_dataset.manifest_bytes == dataset.manifest_bytes
    assert canonical_decimal(Decimal("29374.500000000000000000")) == "29374.5"
    assert canonical_decimal(Decimal("1.00000000000E-7")) == "0.0000001"
    assert canonical_decimal(Decimal("-0.000")) == "0"
    # Exact digits, never context rounding: 39 significant digits survive.
    assert canonical_decimal(Decimal("123456789012345678901.123456789012345678")) == (
        "123456789012345678901.123456789012345678"
    )
    assert_refused("RECORD_TYPE_REFUSED", canonical_decimal, Decimal("NaN"))


def test_flipping_the_holdout_guard_leaves_data_manifests_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    """RBT-008 flips the guard in its own commit; the frozen DATA datasets must not move."""

    before = determinism_manifests()
    monkeypatch.setattr(replay, "HOLDOUT_OPENING_AUTHORIZED", True)

    assert determinism_manifests() == before


def test_the_manifest_property_is_a_detached_copy() -> None:
    dataset = venue_dataset(hourly_series(utc(2024, 3, 4), 3))
    copy = dataset.manifest
    copy["price_series"]["records"].clear()
    copy["evidence_class"] = "CERTIFIED"

    assert dataset.manifest["evidence_class"] == "RESEARCH_BACKTEST_NON_CERTIFYING"
    assert len(dataset.manifest["price_series"]["records"]) == 3
    assert hashlib.sha256(dataset.manifest_bytes).hexdigest() == dataset.manifest_sha256


def test_the_non_price_inputs_form_one_snapshot_shared_by_all_three_venues() -> None:
    inputs = mixed_inputs()
    snapshot, _ = build_mixed(inputs)
    rebuilt, _ = build_mixed(mixed_inputs())
    assert rebuilt.manifest_bytes == snapshot.manifest_bytes

    manifests = {}
    for venue in REPLAY_VENUES:
        series = hourly_series(MIXED_START, 96, venue=venue, missing=(17, 40, 41))
        dataset = build_venue_replay_dataset(
            venue=venue,
            window=DATA_WINDOW,
            price_bars=series,
            shared_snapshot=snapshot,
        )
        manifests[venue.venue_id] = dataset.manifest
    assert {manifest["shared_snapshot"]["manifest_sha256"] for manifest in manifests.values()} == {
        snapshot.manifest_sha256
    }
    # Only the reference price varies between the three runs.
    stripped = [
        {key: value for key, value in manifest.items() if key not in ("venue", "price_series")}
        for manifest in manifests.values()
    ]
    assert stripped[0] == stripped[1] == stripped[2]
    assert len({json.dumps(manifest["price_series"], sort_keys=True) for manifest in manifests.values()}) == 3


# --- determinism ---------------------------------------------------------------------------


@pytest.mark.parametrize("seed", [0, 1, 8675309, 20240304])
def test_the_manifests_are_byte_identical_under_input_reordering(seed: int) -> None:
    expected_venue, expected_shared = determinism_manifests()
    rng = random.Random(seed)
    shuffled = {}
    for name, records in mixed_inputs().items():
        items = list(records)
        rng.shuffle(items)
        shuffled[name] = tuple(items)

    snapshot, dataset = build_mixed(shuffled)

    assert dataset.manifest_bytes == expected_venue
    assert snapshot.manifest_bytes == expected_shared


def test_the_manifests_are_byte_identical_in_fresh_processes_hash_seeds_and_another_cwd(
    tmp_path: Path,
) -> None:
    expected_venue, expected_shared = determinism_manifests()
    script = """
import sys
from pathlib import Path
from btc_predictor.tests.test_research_backtest_replay_inputs import determinism_manifests
venue, shared = determinism_manifests()
out = Path(sys.argv[1])
(out / "venue.json").write_bytes(venue)
(out / "shared.json").write_bytes(shared)
"""
    for seed in ("0", "1", "8675309"):
        cwd = tmp_path / f"cwd-{seed}"
        output = tmp_path / f"out-{seed}"
        cwd.mkdir()
        output.mkdir()
        subprocess.run(
            [sys.executable, "-c", script, str(output)],
            cwd=cwd,
            env=dict(os.environ, PYTHONHASHSEED=seed, PYTHONPATH=str(ROOT)),
            check=True,
            capture_output=True,
            text=True,
        )
        assert (output / "venue.json").read_bytes() == expected_venue
        assert (output / "shared.json").read_bytes() == expected_shared
