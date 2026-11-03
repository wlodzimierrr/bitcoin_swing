"""Deterministic synthetic fixtures for the RBT-001A extended replay builder.

Every value is synthetic: no database, no network and no real-data value. The
records mimic what RBT-003's adapters will persist (Binance COIN-M quarterly
basis at hour closes with a contract listing evidence file whose calendar is
synthetic, Kraken Futures ``PI_XBTUSD`` per-side hourly liquidation
aggregates with their hour evidence, and a Coin Metrics market-cap evidence
file), each carrying one bulk ingestion time, as a backfill would.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal, localcontext
from functools import lru_cache

from btc_predictor.data import FuturesBasis, Liquidation, OpenInterest
from btc_predictor.research import prospective_integration_corpus as epic_x
from btc_predictor.research.us_equity_market_closures import COVERAGE_END, COVERAGE_START, load_closures
from btc_predictor.research_backtest import replay_inputs as v1
from btc_predictor.research_backtest import replay_inputs_v2 as v2

HOUR = timedelta(hours=1)
DAY = timedelta(days=1)
MICROSECOND = timedelta(microseconds=1)
BULK_INGESTED_AT = datetime(2026, 9, 28, 9, 15, tzinfo=UTC)
BASIS_PROVIDER = "binance_coinm_klines_fixture"
LIQUIDATION_PROVIDER = "kraken_futures_rest_history_fixture"
RETRIEVED_AT = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)
OBSERVED = epic_x.FEED_STATUS_OBSERVED_WITH_EVENTS
ZERO = epic_x.FEED_STATUS_OBSERVED_ZERO_EVENTS
UNAVAILABLE = epic_x.FEED_STATUS_SOURCE_UNAVAILABLE


def utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=UTC)


def midnight(day: date) -> datetime:
    return datetime.combine(day, time(0), tzinfo=UTC)


def digest(*parts: object) -> str:
    return hashlib.sha256("|".join(str(part) for part in parts).encode()).hexdigest()


@lru_cache(maxsize=1)
def closure_holidays() -> frozenset[date]:
    return load_closures(COVERAGE_START, COVERAGE_END)


def shared_snapshot(**families: object) -> v1.SharedReplaySnapshot:
    """A V1 shared snapshot built with the closure table, as V2 requires."""

    return v1.build_shared_replay_snapshot(window=v1.DATA_WINDOW, etf_market_holidays=closure_holidays(), **families)


# --- futures basis ----------------------------------------------------------------------


def last_friday(year: int, month: int) -> date:
    day = date(year + (month == 12), month % 12 + 1, 1) - DAY
    while day.weekday() != 4:
        day -= DAY
    return day


def quarterly_expiry(year: int, month: int) -> datetime:
    """Binance COIN-M quarterlies deliver at 08:00 UTC on the quarter month's last Friday."""

    return datetime.combine(last_friday(year, month), time(8), tzinfo=UTC)


def annualized(basis_rate: Decimal, t: datetime, expiry: datetime) -> Decimal:
    """The contract's annualisation, computed independently of the builder."""

    seconds = Decimal(int((expiry - t).total_seconds()))
    with localcontext() as context:
        context.prec = 60
        return (basis_rate * Decimal(365 * 24 * 3600) / seconds).quantize(Decimal("1e-18"), rounding=ROUND_HALF_UP)


def basis_row(
    t: datetime,
    expiry: datetime,
    basis_rate: Decimal = Decimal("0.012345678901234567"),
    **changes: object,
) -> FuturesBasis:
    fields: dict[str, object] = {
        "observation_time": t,
        "exchange": v2.FUTURES_BASIS_EXCHANGE,
        "symbol": v2.FUTURES_BASIS_SYMBOL,
        "instrument": instrument(expiry),
        "expiry": expiry,
        "basis_rate": basis_rate,
        "provider": BASIS_PROVIDER,
        "source": "fixture-coinm-klines",
        "available_at": BULK_INGESTED_AT,
        "ingested_at": BULK_INGESTED_AT,
    }
    fields.update(changes)
    if "annualized_basis_rate" not in fields:
        fields["annualized_basis_rate"] = annualized(fields["basis_rate"], t, expiry)  # type: ignore[arg-type]
    return FuturesBasis(**fields)  # type: ignore[arg-type]


def basis_rows(start: datetime, end: datetime, rate_at: Callable[[int], Decimal] | None = None) -> tuple[FuturesBasis, ...]:
    """Hourly rows for every quarterly the fixture listing shows listed at each hour."""

    rows = []
    instant = start
    index = 0
    while instant < end:
        for expiry in listed_quarterlies(instant):
            rate = rate_at(index) if rate_at is not None else Decimal("0.01") + Decimal(index % 37) / Decimal(10_000)
            rows.append(basis_row(instant, expiry, rate.quantize(Decimal("1e-18"))))
        instant += HOUR
        index += 1
    return tuple(rows)


def listed_quarterlies(t: datetime) -> tuple[datetime, ...]:
    """The deliveries of the fixture listing's contracts listed at ``t`` (current and next quarter)."""

    return tuple(contract.delivery_at for contract in listing_contracts() if contract.listed_at(t))


def instrument(expiry: datetime) -> str:
    return f"BTCUSD_{expiry:%y%m%d}"


@lru_cache(maxsize=1)
def listing_contracts() -> tuple[v2.FuturesBasisContractListing, ...]:
    """A synthetic listing: every quarterly from 2019 to 2027, each first trading
    when the quarterly two deliveries earlier delivers (so two are listed at a time).

    The builder takes identity, listing and delivery only from evidence like this
    (owner review ruling 4); the calendar here is the fixture's, not a rule.
    """

    deliveries = [quarterly_expiry(year, month) for year in range(2018, 2028) for month in (3, 6, 9, 12)]
    return tuple(
        v2.FuturesBasisContractListing(instrument(delivery), deliveries[index - 2], delivery)
        for index, delivery in enumerate(deliveries)
        if index >= 2
    )


def basis_listing_bytes(contracts: Iterable[v2.FuturesBasisContractListing] | None = None, **changes: object) -> bytes:
    fields: dict[str, object] = {
        "source": "https://data.binance.vision/?prefix=data/futures/cm/monthly/klines/",
        "licence": "Binance public market data",
        "retrieved_at": RETRIEVED_AT,
        "response_sha256": [digest("binance-vision", "cm-klines", 1)],
        "contracts": tuple(listing_contracts() if contracts is None else contracts),
    }
    fields.update(changes)
    return v2.futures_basis_listing_evidence_bytes(**fields)  # type: ignore[arg-type]


def basis_listing_evidence(contracts: Iterable[v2.FuturesBasisContractListing] | None = None) -> v2.FuturesBasisListingEvidence:
    data = basis_listing_bytes(contracts)
    return v2.parse_futures_basis_listing_evidence(data, expected_sha256=hashlib.sha256(data).hexdigest())


@lru_cache(maxsize=1)
def default_listing_evidence() -> v2.FuturesBasisListingEvidence:
    return basis_listing_evidence()


# --- market cap ---------------------------------------------------------------------------


def market_cap_rows(first: date, last: date) -> tuple[tuple[date, Decimal], ...]:
    rows = []
    day = first
    index = 0
    while day <= last:
        rows.append((day, Decimal(600_000_000_000 + 3_000_000_000 * (index % 23))))
        day += DAY
        index += 1
    return tuple(rows)


def market_cap_bytes(rows: Iterable[tuple[date, Decimal]], **changes: object) -> bytes:
    fields: dict[str, object] = {
        "source": "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=btc&metrics=CapMrktCurUSD",
        "licence": "CC BY-NC 4.0",
        "retrieved_at": RETRIEVED_AT,
        "response_sha256": [digest("coinmetrics", "page", 1)],
        "rows": tuple(rows),
    }
    fields.update(changes)
    return v2.market_cap_evidence_bytes(**fields)  # type: ignore[arg-type]


def market_cap_evidence(first: date, last: date) -> v2.MarketCapEvidence:
    data = market_cap_bytes(market_cap_rows(first, last))
    return v2.parse_market_cap_evidence(data, expected_sha256=hashlib.sha256(data).hexdigest())


def open_interest(start: datetime, end: datetime) -> tuple[OpenInterest, ...]:
    rows = []
    instant = start
    index = 0
    while instant < end:
        rows.append(
            OpenInterest(
                observation_time=instant,
                exchange="binance",
                symbol="BTCUSDT",
                instrument="BTC-PERP",
                open_interest=Decimal(9_000_000_000 + 10_000_000 * (index % 17)),
                open_interest_unit="USD",
                provider="binance_um_metrics_fixture",
                source="fixture-metrics",
                available_at=BULK_INGESTED_AT,
                ingested_at=BULK_INGESTED_AT,
            )
        )
        instant += HOUR
        index += 1
    return tuple(rows)


# --- liquidations -----------------------------------------------------------------------


def liquidation_row(hour: datetime, side: str, notional: Decimal | None, **changes: object) -> Liquidation:
    fields: dict[str, object] = {
        "observation_time": hour,
        "exchange": v2.LIQUIDATION_EXCHANGE,
        "symbol": v2.LIQUIDATION_SYMBOL,
        "timeframe": v2.LIQUIDATION_TIMEFRAME,
        "side": side,
        "quantity": notional if notional is not None else Decimal("1"),
        "quantity_unit": "contracts",
        "notional_usd": notional,
        "provider": LIQUIDATION_PROVIDER,
        "source": "fixture-kraken-executions",
        "available_at": BULK_INGESTED_AT,
        "ingested_at": BULK_INGESTED_AT,
    }
    fields.update(changes)
    return Liquidation(**fields)  # type: ignore[arg-type]


def hour_evidence(hour: datetime, status: str = OBSERVED, corroboration: str | None = None) -> v2.LiquidationHourEvidence:
    if corroboration is None:
        corroboration = v2.CORROBORATION_NOT_APPLICABLE if status == UNAVAILABLE else v2.CORROBORATION_AGREES
    return v2.LiquidationHourEvidence(hour, status, corroboration, digest("kraken", hour.isoformat(), status))


@dataclass(frozen=True)
class LiquidationHistory:
    rows: tuple[Liquidation, ...]
    hours: tuple[v2.LiquidationHourEvidence, ...]
    first: date
    last: date


def liquidation_history(
    first: date,
    last: date,
    *,
    notional_at: Callable[[int, str], Decimal] | None = None,
    unavailable_hours: Iterable[datetime] = (),
    missing_hours: Iterable[datetime] = (),
    zero_days: Iterable[date] = (),
) -> LiquidationHistory:
    """Hour evidence and per-side rows for every hour of ``[first, last]``.

    By default every hour is observed with a deterministic long and short
    notional; ``zero_days`` are fully observed with no liquidation, listed hours
    are unavailable (no rows) or have no evidence at all.
    """

    unavailable = set(unavailable_hours)
    missing = set(missing_hours)
    zero = set(zero_days)
    rows: list[Liquidation] = []
    hours: list[v2.LiquidationHourEvidence] = []
    instant = midnight(first)
    end = midnight(last) + DAY
    index = 0
    while instant < end:
        if instant in missing:
            pass
        elif instant in unavailable:
            hours.append(hour_evidence(instant, UNAVAILABLE))
        elif instant.date() in zero:
            hours.append(hour_evidence(instant, ZERO))
        else:
            hours.append(hour_evidence(instant, OBSERVED))
            for side in v2.LIQUIDATION_SIDES:
                value = notional_at(index, side) if notional_at is not None else default_notional(index, side)
                rows.append(liquidation_row(instant, side, value))
        instant += HOUR
        index += 1
    return LiquidationHistory(tuple(rows), tuple(hours), first, last)


def default_notional(index: int, side: str) -> Decimal:
    # a slowly drifting, non-monotonic hourly series with ties
    base = 1_000 + 37 * ((index * 7919) % 101) + (index // 24) % 53
    return Decimal(base * (3 if side == "long" else 2))
