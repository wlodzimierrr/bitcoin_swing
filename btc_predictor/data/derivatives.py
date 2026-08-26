"""Derivatives data collection and point-in-time aggregation helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from time import sleep
from typing import Any, Protocol

from sqlalchemy import Select, select
from sqlalchemy.dialects.postgresql import insert

from btc_predictor.data.ohlcv import normalize_utc_datetime, require_utc_datetime
from btc_predictor.db.raw import (
    FUNDING_RATES_PRIMARY_KEY,
    FUTURES_BASIS_PRIMARY_KEY,
    LIQUIDATIONS_PRIMARY_KEY,
    OPEN_INTEREST_PRIMARY_KEY,
    PERP_VOLUME_PRIMARY_KEY,
    funding_rates,
    futures_basis,
    liquidations,
    open_interest,
    perp_volume,
)


DERIVATIVES_FEEDS = (
    "funding_rates",
    "open_interest",
    "futures_basis",
    "liquidations",
    "perp_volume",
)


@dataclass(frozen=True)
class FundingRate:
    observation_time: datetime
    exchange: str
    symbol: str
    instrument: str
    funding_rate: Decimal
    funding_interval_hours: Decimal
    provider: str
    source: str
    available_at: datetime
    ingested_at: datetime

    def as_record(self) -> dict[str, Any]:
        _validate_availability(self.observation_time, self.available_at)
        return {
            "observation_time": require_utc_datetime(self.observation_time, "observation_time"),
            "exchange": self.exchange,
            "symbol": self.symbol,
            "instrument": self.instrument,
            "funding_rate": self.funding_rate,
            "funding_interval_hours": self.funding_interval_hours,
            "provider": self.provider,
            "source": self.source,
            "available_at": require_utc_datetime(self.available_at, "available_at"),
            "ingested_at": require_utc_datetime(self.ingested_at, "ingested_at"),
        }


@dataclass(frozen=True)
class OpenInterest:
    observation_time: datetime
    exchange: str
    symbol: str
    instrument: str
    open_interest: Decimal
    open_interest_unit: str
    provider: str
    source: str
    available_at: datetime
    ingested_at: datetime

    def as_record(self) -> dict[str, Any]:
        _validate_availability(self.observation_time, self.available_at)
        return {
            "observation_time": require_utc_datetime(self.observation_time, "observation_time"),
            "exchange": self.exchange,
            "symbol": self.symbol,
            "instrument": self.instrument,
            "open_interest": self.open_interest,
            "open_interest_unit": self.open_interest_unit,
            "provider": self.provider,
            "source": self.source,
            "available_at": require_utc_datetime(self.available_at, "available_at"),
            "ingested_at": require_utc_datetime(self.ingested_at, "ingested_at"),
        }


@dataclass(frozen=True)
class FuturesBasis:
    observation_time: datetime
    exchange: str
    symbol: str
    instrument: str
    expiry: datetime
    basis_rate: Decimal
    annualized_basis_rate: Decimal
    provider: str
    source: str
    available_at: datetime
    ingested_at: datetime

    def as_record(self) -> dict[str, Any]:
        _validate_availability(self.observation_time, self.available_at)
        return {
            "observation_time": require_utc_datetime(self.observation_time, "observation_time"),
            "exchange": self.exchange,
            "symbol": self.symbol,
            "instrument": self.instrument,
            "expiry": require_utc_datetime(self.expiry, "expiry"),
            "basis_rate": self.basis_rate,
            "annualized_basis_rate": self.annualized_basis_rate,
            "provider": self.provider,
            "source": self.source,
            "available_at": require_utc_datetime(self.available_at, "available_at"),
            "ingested_at": require_utc_datetime(self.ingested_at, "ingested_at"),
        }


@dataclass(frozen=True)
class Liquidation:
    observation_time: datetime
    exchange: str
    symbol: str
    timeframe: str
    side: str
    quantity: Decimal
    quantity_unit: str
    notional_usd: Decimal | None
    provider: str
    source: str
    available_at: datetime
    ingested_at: datetime

    def as_record(self) -> dict[str, Any]:
        _validate_availability(self.observation_time, self.available_at)
        return {
            "observation_time": require_utc_datetime(self.observation_time, "observation_time"),
            "exchange": self.exchange,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "side": self.side,
            "quantity": self.quantity,
            "quantity_unit": self.quantity_unit,
            "notional_usd": self.notional_usd,
            "provider": self.provider,
            "source": self.source,
            "available_at": require_utc_datetime(self.available_at, "available_at"),
            "ingested_at": require_utc_datetime(self.ingested_at, "ingested_at"),
        }


@dataclass(frozen=True)
class PerpVolume:
    observation_time: datetime
    exchange: str
    symbol: str
    timeframe: str
    volume: Decimal
    volume_unit: str
    notional_usd: Decimal | None
    provider: str
    source: str
    available_at: datetime
    ingested_at: datetime

    def as_record(self) -> dict[str, Any]:
        _validate_availability(self.observation_time, self.available_at)
        return {
            "observation_time": require_utc_datetime(self.observation_time, "observation_time"),
            "exchange": self.exchange,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "volume": self.volume,
            "volume_unit": self.volume_unit,
            "notional_usd": self.notional_usd,
            "provider": self.provider,
            "source": self.source,
            "available_at": require_utc_datetime(self.available_at, "available_at"),
            "ingested_at": require_utc_datetime(self.ingested_at, "ingested_at"),
        }


DerivativesRow = (
    FundingRate
    | OpenInterest
    | FuturesBasis
    | Liquidation
    | PerpVolume
    | Mapping[str, Any]
)


class DerivativesProvider(Protocol):
    """Provider boundary for exchange-specific derivatives clients."""

    def fetch_funding_rates(self, **kwargs: Any) -> Iterable[DerivativesRow]:
        ...

    def fetch_open_interest(self, **kwargs: Any) -> Iterable[DerivativesRow]:
        ...

    def fetch_futures_basis(self, **kwargs: Any) -> Iterable[DerivativesRow]:
        ...

    def fetch_liquidations(self, **kwargs: Any) -> Iterable[DerivativesRow]:
        ...

    def fetch_perp_volume(self, **kwargs: Any) -> Iterable[DerivativesRow]:
        ...


@dataclass(frozen=True)
class DerivativesCollectionRequest:
    exchange: str
    symbol: str
    provider: str
    start: datetime
    end: datetime
    instrument: str = "BTC-PERP"
    source: str = "provider"
    timeframe: str = "1h"
    max_attempts: int = 3
    retry_backoff_seconds: float = 0

    def __post_init__(self) -> None:
        require_utc_datetime(self.start, "start")
        require_utc_datetime(self.end, "end")
        if self.end < self.start:
            raise ValueError("end must be >= start")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds must be >= 0")


@dataclass(frozen=True)
class DerivativesCollectionResult:
    funding_rates: tuple[FundingRate, ...]
    open_interest: tuple[OpenInterest, ...]
    futures_basis: tuple[FuturesBasis, ...]
    liquidations: tuple[Liquidation, ...]
    perp_volume: tuple[PerpVolume, ...]
    provider_attempts: dict[str, int]

    @property
    def records(self) -> tuple[FundingRate | OpenInterest | FuturesBasis | Liquidation | PerpVolume, ...]:
        return (
            *self.funding_rates,
            *self.open_interest,
            *self.futures_basis,
            *self.liquidations,
            *self.perp_volume,
        )


@dataclass(frozen=True)
class BtcDerivativesAggregate:
    signal_time: datetime
    funding_rate_avg: Decimal | None
    open_interest_by_unit: Mapping[str, Decimal]
    futures_basis_rate_avg: Decimal | None
    annualized_basis_rate_avg: Decimal | None
    long_liquidations_usd: Decimal
    short_liquidations_usd: Decimal
    perp_volume_usd: Decimal
    source_record_count: int


class DerivativesCollectionError(RuntimeError):
    """Raised when a derivatives provider cannot satisfy a collection request."""


def collect_btc_derivatives(
    provider: DerivativesProvider,
    connection: Any,
    request: DerivativesCollectionRequest,
    *,
    ingested_at: datetime | None = None,
) -> DerivativesCollectionResult:
    """Fetch all BTC derivatives feeds and persist normalized raw records."""

    ingestion_time = require_utc_datetime(ingested_at or datetime.now(UTC), "ingested_at")
    attempts: dict[str, int] = {}
    funding = _fetch_normalized(provider, request, "funding_rates", ingestion_time, FundingRate)
    attempts["funding_rates"] = funding[1]
    oi = _fetch_normalized(provider, request, "open_interest", ingestion_time, OpenInterest)
    attempts["open_interest"] = oi[1]
    basis = _fetch_normalized(provider, request, "futures_basis", ingestion_time, FuturesBasis)
    attempts["futures_basis"] = basis[1]
    liq = _fetch_normalized(provider, request, "liquidations", ingestion_time, Liquidation)
    attempts["liquidations"] = liq[1]
    volume = _fetch_normalized(provider, request, "perp_volume", ingestion_time, PerpVolume)
    attempts["perp_volume"] = volume[1]

    result = DerivativesCollectionResult(
        funding_rates=funding[0],
        open_interest=oi[0],
        futures_basis=basis[0],
        liquidations=liq[0],
        perp_volume=volume[0],
        provider_attempts=attempts,
    )

    for statement in build_derivatives_insert_ignore(result):
        connection.execute(statement)

    return result


def build_derivatives_insert_ignore(result: DerivativesCollectionResult) -> tuple[Any, ...]:
    """Build idempotent inserts that preserve existing raw derivatives records."""

    statements = []
    if result.funding_rates:
        statements.append(
            _insert_ignore(funding_rates, FUNDING_RATES_PRIMARY_KEY, result.funding_rates)
        )
    if result.open_interest:
        statements.append(
            _insert_ignore(open_interest, OPEN_INTEREST_PRIMARY_KEY, result.open_interest)
        )
    if result.futures_basis:
        statements.append(
            _insert_ignore(futures_basis, FUTURES_BASIS_PRIMARY_KEY, result.futures_basis)
        )
    if result.liquidations:
        statements.append(
            _insert_ignore(liquidations, LIQUIDATIONS_PRIMARY_KEY, result.liquidations)
        )
    if result.perp_volume:
        statements.append(
            _insert_ignore(perp_volume, PERP_VOLUME_PRIMARY_KEY, result.perp_volume)
        )
    return tuple(statements)


def latest_derivatives_available_at(signal_time: datetime) -> dict[str, Select]:
    """Build point-in-time raw derivative feed queries for a signal timestamp."""

    signal_time = require_utc_datetime(signal_time, "signal_time")
    tables = {
        "funding_rates": funding_rates,
        "open_interest": open_interest,
        "futures_basis": futures_basis,
        "liquidations": liquidations,
        "perp_volume": perp_volume,
    }
    return {
        name: select(table).where(
            table.c.available_at <= signal_time,
            table.c.observation_time <= signal_time,
        )
        for name, table in tables.items()
    }


def aggregate_btc_derivatives_available_at(
    rows: Sequence[FundingRate | OpenInterest | FuturesBasis | Liquidation | PerpVolume],
    signal_time: datetime,
) -> BtcDerivativesAggregate:
    """Aggregate BTC derivative rows available at a signal timestamp."""

    signal_time = require_utc_datetime(signal_time, "signal_time")
    available_rows = tuple(
        row for row in rows if row.available_at <= signal_time and row.observation_time <= signal_time
    )
    funding = [row.funding_rate for row in available_rows if isinstance(row, FundingRate)]
    basis = [row for row in available_rows if isinstance(row, FuturesBasis)]
    oi_by_unit: dict[str, Decimal] = {}
    long_liquidations_usd = Decimal("0")
    short_liquidations_usd = Decimal("0")
    perp_volume_usd = Decimal("0")

    for row in available_rows:
        if isinstance(row, OpenInterest):
            oi_by_unit[row.open_interest_unit] = (
                oi_by_unit.get(row.open_interest_unit, Decimal("0")) + row.open_interest
            )
        elif isinstance(row, Liquidation) and row.notional_usd is not None:
            if row.side == "long":
                long_liquidations_usd += row.notional_usd
            elif row.side == "short":
                short_liquidations_usd += row.notional_usd
        elif isinstance(row, PerpVolume) and row.notional_usd is not None:
            perp_volume_usd += row.notional_usd

    return BtcDerivativesAggregate(
        signal_time=signal_time,
        funding_rate_avg=_average(funding),
        open_interest_by_unit=oi_by_unit,
        futures_basis_rate_avg=_average([row.basis_rate for row in basis]),
        annualized_basis_rate_avg=_average([row.annualized_basis_rate for row in basis]),
        long_liquidations_usd=long_liquidations_usd,
        short_liquidations_usd=short_liquidations_usd,
        perp_volume_usd=perp_volume_usd,
        source_record_count=len(available_rows),
    )


def _fetch_normalized(
    provider: DerivativesProvider,
    request: DerivativesCollectionRequest,
    feed_name: str,
    ingested_at: datetime,
    record_type: type[FundingRate] | type[OpenInterest] | type[FuturesBasis] | type[Liquidation] | type[PerpVolume],
):
    rows, attempts = _fetch_with_retry(provider, request, feed_name)
    normalized = tuple(
        _coerce_derivatives_row(row, request=request, ingested_at=ingested_at, record_type=record_type)
        for row in rows
    )
    _validate_unique_records(normalized)
    return normalized, attempts


def _fetch_with_retry(
    provider: DerivativesProvider,
    request: DerivativesCollectionRequest,
    feed_name: str,
) -> tuple[tuple[DerivativesRow, ...], int]:
    method = getattr(provider, f"fetch_{feed_name}")
    attempts = 0
    while attempts < request.max_attempts:
        attempts += 1
        try:
            return (
                tuple(
                    method(
                        exchange=request.exchange,
                        symbol=request.symbol,
                        instrument=request.instrument,
                        timeframe=request.timeframe,
                        start=request.start,
                        end=request.end,
                    )
                ),
                attempts,
            )
        except Exception as exc:
            if attempts >= request.max_attempts:
                raise DerivativesCollectionError(
                    f"Derivatives provider failed for {feed_name} after retry attempts"
                ) from exc
            if request.retry_backoff_seconds:
                sleep(request.retry_backoff_seconds)
    raise DerivativesCollectionError(f"Derivatives provider failed for {feed_name} without returning data")


def _coerce_derivatives_row(
    row: DerivativesRow,
    *,
    request: DerivativesCollectionRequest,
    ingested_at: datetime,
    record_type: type[FundingRate] | type[OpenInterest] | type[FuturesBasis] | type[Liquidation] | type[PerpVolume],
):
    if isinstance(row, record_type):
        source = row.as_record()
    else:
        source = dict(row)

    common = {
        "observation_time": normalize_utc_datetime(source["observation_time"], "observation_time"),
        "exchange": request.exchange,
        "symbol": request.symbol,
        "provider": request.provider,
        "source": str(source.get("source", request.source)),
        "available_at": normalize_utc_datetime(source["available_at"], "available_at"),
        "ingested_at": ingested_at,
    }

    if record_type is FundingRate:
        record = FundingRate(
            instrument=str(source.get("instrument", request.instrument)),
            funding_rate=_decimal(source["funding_rate"]),
            funding_interval_hours=_decimal(source["funding_interval_hours"]),
            **common,
        )
    elif record_type is OpenInterest:
        record = OpenInterest(
            instrument=str(source.get("instrument", request.instrument)),
            open_interest=_decimal(source["open_interest"]),
            open_interest_unit=str(source["open_interest_unit"]),
            **common,
        )
    elif record_type is FuturesBasis:
        record = FuturesBasis(
            instrument=str(source.get("instrument", request.instrument)),
            expiry=normalize_utc_datetime(source["expiry"], "expiry"),
            basis_rate=_decimal(source["basis_rate"]),
            annualized_basis_rate=_decimal(source["annualized_basis_rate"]),
            **common,
        )
    elif record_type is Liquidation:
        record = Liquidation(
            timeframe=str(source.get("timeframe", request.timeframe)),
            side=str(source["side"]),
            quantity=_decimal(source["quantity"]),
            quantity_unit=str(source["quantity_unit"]),
            notional_usd=_optional_decimal(source.get("notional_usd")),
            **common,
        )
    elif record_type is PerpVolume:
        record = PerpVolume(
            timeframe=str(source.get("timeframe", request.timeframe)),
            volume=_decimal(source["volume"]),
            volume_unit=str(source["volume_unit"]),
            notional_usd=_optional_decimal(source.get("notional_usd")),
            **common,
        )
    else:
        raise TypeError(f"Unsupported derivatives record type: {record_type!r}")

    record.as_record()
    return record


def _insert_ignore(table: Any, primary_key: Sequence[str], rows: Sequence[Any]):
    statement = insert(table).values([row.as_record() for row in rows])
    return statement.on_conflict_do_nothing(index_elements=list(primary_key))


def _validate_availability(observation_time: datetime, available_at: datetime) -> None:
    observation_time = require_utc_datetime(observation_time, "observation_time")
    available_at = require_utc_datetime(available_at, "available_at")
    if available_at < observation_time:
        raise ValueError("available_at must be >= observation_time")


def _validate_unique_records(rows: Sequence[Any]) -> None:
    seen = set()
    for row in rows:
        key = tuple(row.as_record().items())
        if key in seen:
            raise ValueError("Duplicate derivatives provider record")
        seen.add(key)


def _decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _optional_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return _decimal(value)


def _average(values: Sequence[Decimal]) -> Decimal | None:
    if not values:
        return None
    return sum(values, Decimal("0")) / Decimal(len(values))
