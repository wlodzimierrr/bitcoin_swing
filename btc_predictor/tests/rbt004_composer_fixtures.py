"""Deterministic synthetic replay inputs for the RBT-004 entry-composer tests.

Every input passes through the reviewed RBT-001 builders
(``build_shared_replay_snapshot`` and ``build_venue_replay_dataset``), so each
record carries its policy V7 section 4 modelled availability. The families
RBT-001A has not built yet (futures basis, market cap, liquidation percentile)
are owner records whose availability fields carry the modelled availability.

Determinism: no randomness, clock, network or database. Every series is a
closed-form function of its index. Dates stay inside the data window
(2020-01-01 .. 2025-12-31), so nothing reads the prohibited window or the
holdout.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.data import EtfFlow, FundingRate, FuturesBasis, OhlcvBar, OpenInterest, PerpVolume
from btc_predictor.features.positioning import MarketCapObservation
from btc_predictor.research.us_equity_market_closures import load_closures
from btc_predictor.research_backtest import entry_composer
from btc_predictor.research_backtest.entry_composer import (
    EntryComposer,
    EntryComposerInputs,
    EtfFundLaunch,
    LiquidationPercentileObservation,
)
from btc_predictor.research_backtest.replay_inputs import (
    BITSTAMP_REPLAY_VENUE,
    DATA_WINDOW,
    ReplayVenue,
    build_shared_replay_snapshot,
    build_venue_replay_dataset,
)

CONFIG = load_strategy_config()
BULK_INGESTED_AT = datetime(2026, 9, 28, 9, 15, tzinfo=UTC)
HOUR = timedelta(hours=1)
DAY = timedelta(days=1)
CLOSURES = load_closures(date(2023, 1, 1), date(2026, 12, 31))


def utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=UTC)


def _q(value: float | Decimal, places: str = "0.01") -> Decimal:
    # An exact Decimal is kept as given (the zero-variance guard tests need
    # non-terminating constants); a float is quantized to the family's places.
    if isinstance(value, Decimal):
        return value
    return Decimal(repr(value)).quantize(Decimal(places))


def wave(index: float, period: float, phase: float = 0.0) -> float:
    return math.sin(2 * math.pi * (index + phase) / period)


# --- price and volume ---------------------------------------------------------------------


def hourly_bars(
    start: datetime,
    end: datetime,
    close_at: Callable[[int], float],
    *,
    venue: ReplayVenue = BITSTAMP_REPLAY_VENUE,
    spread: float = 0.002,
    volume_at: Callable[[int], float] | None = None,
    missing: Iterable[datetime] = (),
) -> tuple[OhlcvBar, ...]:
    """1h raw bars from ``start`` to ``end`` (exclusive); ``close_at(hour_index)``."""

    skip = set(missing)
    bars = []
    hours = int((end - start) / HOUR)
    previous = close_at(0)
    for index in range(hours):
        timestamp = start + index * HOUR
        close = close_at(index)
        if timestamp in skip:
            previous = close
            continue
        opening = previous
        high = max(opening, close) * (1 + spread)
        low = min(opening, close) * (1 - spread)
        volume = volume_at(index) if volume_at is not None else 4.0 + 1.5 * wave(index, 37) + 0.75 * wave(index, 11)
        bars.append(
            OhlcvBar(
                timestamp=timestamp,
                exchange=venue.exchange,
                symbol=venue.symbol,
                timeframe="1h",
                open=_q(opening),
                high=_q(high),
                low=_q(low),
                close=_q(close),
                volume=_q(volume, "0.0001"),
                provider=venue.provider,
                ingested_at=BULK_INGESTED_AT,
            )
        )
        previous = close
    return tuple(bars)


def trending_close(base: float = 30000.0, daily_drift: float = 0.0006, cycle_days: float = 47.0, cycle_amplitude: float = 0.07) -> Callable[[int], float]:
    """A deterministic market: drift, a slow swing cycle (weekly pivots) and small hourly noise."""

    def close_at(hour: int) -> float:
        day = hour / 24.0
        trend = base * math.exp(daily_drift * day)
        cycle = 1.0 + cycle_amplitude * wave(day, cycle_days) + 0.02 * wave(day, 9.0, 0.3)
        noise = 1.0 + 0.002 * wave(hour, 5.0) + 0.001 * wave(hour, 13.0, 0.7)
        return trend * cycle * noise

    return close_at


# --- shared non-price families ---------------------------------------------------------


def us_trading_days(first: date, last: date) -> list[date]:
    days = []
    day = first
    while day <= last:
        if day.weekday() < 5 and day not in CLOSURES:
            days.append(day)
        day += DAY
    return days


@dataclass(frozen=True)
class FundSpec:
    fund: str
    launch: date
    aum_base: float
    flow_scale: float


DEFAULT_FUNDS = (
    FundSpec("IBIT", date(2024, 1, 11), 2_000_000_000.0, 40_000_000.0),
    FundSpec("FBTC", date(2024, 1, 11), 1_500_000_000.0, 30_000_000.0),
    FundSpec("ARKB", date(2024, 2, 12), 400_000_000.0, 8_000_000.0),
)


def etf_flows(funds: Iterable[FundSpec], last: date, flow_at: Callable[[str, int], float] | None = None) -> tuple[EtfFlow, ...]:
    rows = []
    for spec in funds:
        for index, day in enumerate(us_trading_days(spec.launch, last)):
            flow = flow_at(spec.fund, index) if flow_at is not None else spec.flow_scale * (0.6 + wave(index, 23.0) + 0.4 * wave(index, 7.0, 0.2))
            aum = spec.aum_base * (1.0 + 0.004 * index)
            rows.append(
                EtfFlow(
                    fund=spec.fund,
                    observation_date=day,
                    flow_usd=_q(flow),
                    aum_usd=_q(aum),
                    provider="fixture-etf",
                    source="fixture-etf-source",
                    revision="final",
                    available_at=BULK_INGESTED_AT,
                    ingested_at=BULK_INGESTED_AT,
                )
            )
    return tuple(rows)


def fund_launches(funds: Iterable[FundSpec]) -> tuple[EtfFundLaunch, ...]:
    return tuple(EtfFundLaunch(spec.fund, spec.launch, "fixture: issuer prospectus first trading date") for spec in funds)


def funding_rates(start: datetime, end: datetime, rate_at: Callable[[int], float | Decimal] | None = None) -> tuple[FundingRate, ...]:
    rows = []
    instant = start
    index = 0
    while instant < end:
        rate = rate_at(index) if rate_at is not None else 0.0001 * (1.0 + 0.6 * wave(index, 31.0) + 0.2 * wave(index, 5.0))
        rows.append(
            FundingRate(
                observation_time=instant,
                exchange="binance",
                symbol="BTCUSDT",
                instrument="BTCUSDT-PERP",
                funding_rate=_q(rate, "0.00000001"),
                funding_interval_hours=Decimal("8"),
                provider="binance",
                source="fixture-derivatives",
                available_at=BULK_INGESTED_AT,
                ingested_at=BULK_INGESTED_AT,
            )
        )
        instant += timedelta(hours=8)
        index += 1
    return tuple(rows)


def open_interest(start: datetime, end: datetime, value_at: Callable[[int], float | Decimal] | None = None, *, unit: str = "USD") -> tuple[OpenInterest, ...]:
    rows = []
    instant = start
    index = 0
    while instant < end:
        value = value_at(index) if value_at is not None else 9_000_000_000.0 * (1.0 + 0.0007 * index) * (1.0 + 0.05 * wave(index, 17.0))
        rows.append(
            OpenInterest(
                observation_time=instant,
                exchange="binance",
                symbol="BTCUSDT",
                instrument="BTCUSDT-PERP",
                open_interest=_q(value),
                open_interest_unit=unit,
                provider="binance",
                source="fixture-derivatives",
                available_at=BULK_INGESTED_AT,
                ingested_at=BULK_INGESTED_AT,
            )
        )
        instant += DAY
        index += 1
    return tuple(rows)


def perp_volumes(start: datetime, end: datetime) -> tuple[PerpVolume, ...]:
    rows = []
    instant = start
    index = 0
    while instant < end:
        rows.append(
            PerpVolume(
                observation_time=instant,
                exchange="binance",
                symbol="BTCUSDT",
                timeframe="1h",
                volume=Decimal("10.5"),
                volume_unit="BTC",
                notional_usd=_q(650000.0 * (1.0 + 0.1 * wave(index, 19.0))),
                provider="binance",
                source="fixture-derivatives",
                available_at=BULK_INGESTED_AT,
                ingested_at=BULK_INGESTED_AT,
            )
        )
        instant += HOUR
        index += 1
    return tuple(rows)


# --- families with no replay builder yet (modelled availability on the record) --------------


def futures_basis(start: datetime, end: datetime, annualized_at: Callable[[int], float | Decimal] | None = None) -> tuple[FuturesBasis, ...]:
    rows = []
    instant = start
    index = 0
    while instant < end:
        annualized = annualized_at(index) if annualized_at is not None else 0.08 * (1.0 + 0.5 * wave(index, 29.0) + 0.1 * wave(index, 6.0))
        days_to_expiry = 60
        rows.append(
            FuturesBasis(
                observation_time=instant,
                exchange="binance",
                symbol="BTCUSD",
                instrument="BTCUSD-QUARTERLY",
                expiry=instant + timedelta(days=days_to_expiry),
                basis_rate=(
                    (annualized * days_to_expiry / 365).quantize(Decimal("0.00000001"))
                    if isinstance(annualized, Decimal)
                    else _q(annualized * days_to_expiry / 365.0, "0.00000001")
                ),
                annualized_basis_rate=_q(annualized, "0.00000001"),
                provider="binance",
                source="fixture-derivatives",
                available_at=instant,
                ingested_at=BULK_INGESTED_AT,
            )
        )
        instant += DAY
        index += 1
    return tuple(rows)


def market_caps(start: datetime, end: datetime, close_at_day: Callable[[int], float]) -> tuple[MarketCapObservation, ...]:
    rows = []
    instant = start
    index = 0
    while instant < end:
        rows.append(
            MarketCapObservation(
                observation_time=instant,
                market_cap_usd=_q(close_at_day(index) * 19_500_000.0),
                provider="fixture-marketcap",
                available_at=instant + 2 * DAY,
            )
        )
        instant += DAY
        index += 1
    return tuple(rows)


def liquidation_percentiles(first: date, last: date, value_at: Callable[[int], float] | None = None) -> tuple[LiquidationPercentileObservation, ...]:
    rows = []
    day = first
    index = 0
    while day <= last:
        value = value_at(index) if value_at is not None else 45.0 + 20.0 * wave(index, 13.0)
        rows.append(
            LiquidationPercentileObservation(
                observation_date=day,
                liquidation_percentile=_q(value),
                available_at=datetime(day.year, day.month, day.day, tzinfo=UTC) + DAY,
            )
        )
        day += DAY
        index += 1
    return tuple(rows)


# --- scenario ---------------------------------------------------------------------------------


@dataclass
class Scenario:
    """A synthetic market whose families can each be replaced before building."""

    start: datetime = field(default_factory=lambda: utc(2021, 6, 1))
    end: datetime = field(default_factory=lambda: utc(2024, 5, 1))
    close_at: Callable[[int], float] = field(default_factory=trending_close)
    venue: ReplayVenue = BITSTAMP_REPLAY_VENUE
    funds: tuple[FundSpec, ...] = DEFAULT_FUNDS
    flow_at: Callable[[str, int], float] | None = None
    funding_at: Callable[[int], float | Decimal] | None = None
    oi_at: Callable[[int], float | Decimal] | None = None
    basis_at: Callable[[int], float | Decimal] | None = None
    liquidation_at: Callable[[int], float] | None = None
    # Derivatives start later than prices: the frozen funding owner's averages
    # are quadratic in the visible rows, and 180 days of z-score history suffice.
    derivatives_start: datetime = field(default_factory=lambda: utc(2023, 6, 1))
    missing_hours: tuple[datetime, ...] = ()
    extra_flows: tuple[EtfFlow, ...] = ()
    extra_funding: tuple[FundingRate, ...] = ()
    extra_open_interest: tuple[OpenInterest, ...] = ()

    def build(self) -> EntryComposerInputs:
        price = hourly_bars(self.start, self.end, self.close_at, venue=self.venue, missing=self.missing_hours)
        volume = (
            price
            if self.venue == BITSTAMP_REPLAY_VENUE
            else hourly_bars(self.start, self.end, self.close_at, venue=BITSTAMP_REPLAY_VENUE)
        )
        last_day = (self.end - DAY).date()
        shared = build_shared_replay_snapshot(
            window=DATA_WINDOW,
            volume_bars=volume,
            etf_flows=(*etf_flows(self.funds, last_day, self.flow_at), *self.extra_flows),
            funding_rates=(*funding_rates(self.derivatives_start, self.end, self.funding_at), *self.extra_funding),
            open_interest=(*open_interest(self.derivatives_start, self.end, self.oi_at), *self.extra_open_interest),
            # hourly perp volume: the BTC-031 derivatives quality owner requires a fresh
            # perp_volume snapshot (required_snapshot_feeds) at every decision instant
            perp_volumes=perp_volumes(self.derivatives_start, self.end),
            etf_market_holidays=CLOSURES,
        )
        dataset = build_venue_replay_dataset(venue=self.venue, window=DATA_WINDOW, price_bars=price, shared_snapshot=shared)
        day_close = lambda index: self.close_at(index * 24)  # noqa: E731
        return EntryComposerInputs(
            dataset=dataset,
            futures_basis=futures_basis(self.derivatives_start, self.end, self.basis_at),
            market_caps=market_caps(self.start, self.end, day_close),
            liquidation_percentiles=liquidation_percentiles(self.start.date(), last_day, self.liquidation_at),
            etf_fund_launches=fund_launches(self.funds),
        )

    def composer(self) -> EntryComposer:
        return EntryComposer(self.build(), strategy_config=CONFIG)


def with_inputs(inputs: EntryComposerInputs, **changes: object) -> EntryComposerInputs:
    return replace(inputs, **changes)


@dataclass(frozen=True)
class OwnerCall:
    args: tuple[object, ...]
    kwargs: dict[str, object]
    result: object


@contextmanager
def recording(*names: str) -> Iterator[dict[str, list[OwnerCall]]]:
    """Record each named owner call the composer makes, delegating to the real owner.

    The composer imports its owners by name, so the recorder replaces the name in
    the composer module's namespace only; owner results are unchanged.
    """

    calls: dict[str, list[OwnerCall]] = {name: [] for name in names}
    with pytest.MonkeyPatch.context() as patch:
        for name in names:
            real = getattr(entry_composer, name)

            def wrapper(*args: object, _real: Callable[..., object] = real, _name: str = name, **kwargs: object) -> object:
                result = _real(*args, **kwargs)
                calls[_name].append(OwnerCall(args, kwargs, result))
                return result

            patch.setattr(entry_composer, name, wrapper)
        yield calls


def decide_consecutively(composer: EntryComposer, first: datetime, last: datetime) -> list[object]:
    """Decide and record every daily instant in ``[first, last]``; return the rows."""

    rows = []
    instant = first
    while instant <= last:
        decision = composer.decide(instant)
        composer.record(decision)
        rows.append(decision.row)
        instant += DAY
    return rows
