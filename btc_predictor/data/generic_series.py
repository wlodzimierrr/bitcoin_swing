"""Generic point-in-time series helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from time import sleep
from typing import Any, Protocol

from sqlalchemy import Select, func, select
from sqlalchemy.dialects.postgresql import insert

from btc_predictor.data.ohlcv import normalize_utc_datetime, require_utc_datetime
from btc_predictor.db.raw import GENERIC_SERIES_PRIMARY_KEY, generic_series


SUPPORTED_SERIES_TYPES = ("macro", "liquidity", "onchain", "market_proxy")


@dataclass(frozen=True)
class SeriesDefinition:
    series_id: str
    series_type: str
    unit: str
    description: str


MACRO_SERIES_DEFINITIONS = {
    "VIX": SeriesDefinition(
        series_id="VIX",
        series_type="macro",
        unit="index_points",
        description="Cboe volatility index or provider-equivalent volatility proxy.",
    ),
    "DXY": SeriesDefinition(
        series_id="DXY",
        series_type="market_proxy",
        unit="index_points",
        description="US dollar index or provider-equivalent dollar strength proxy.",
    ),
    "NASDAQ_PROXY": SeriesDefinition(
        series_id="NASDAQ_PROXY",
        series_type="market_proxy",
        unit="index_points",
        description="Nasdaq index, ETF, or provider-equivalent risk-asset proxy.",
    ),
    "US_2Y_YIELD": SeriesDefinition(
        series_id="US_2Y_YIELD",
        series_type="macro",
        unit="percent",
        description="US 2-year treasury yield or provider-equivalent rate proxy.",
    ),
    "REAL_YIELD_PROXY": SeriesDefinition(
        series_id="REAL_YIELD_PROXY",
        series_type="macro",
        unit="percent",
        description="Real-yield series or provider-equivalent inflation-adjusted rate proxy.",
    ),
}
MACRO_SERIES_IDS = tuple(MACRO_SERIES_DEFINITIONS)

ONCHAIN_SERIES_DEFINITIONS = {
    "SOPR": SeriesDefinition(
        series_id="SOPR",
        series_type="onchain",
        unit="ratio",
        description="Spent output profit ratio or provider-equivalent profitability metric.",
    ),
    "MVRV": SeriesDefinition(
        series_id="MVRV",
        series_type="onchain",
        unit="ratio",
        description="Market-value-to-realized-value ratio or provider-equivalent valuation metric.",
    ),
    "REALIZED_PL": SeriesDefinition(
        series_id="REALIZED_PL",
        series_type="onchain",
        unit="usd",
        description="Realized profit/loss series reported in USD.",
    ),
    "STH_REALIZED_PRICE": SeriesDefinition(
        series_id="STH_REALIZED_PRICE",
        series_type="onchain",
        unit="usd",
        description="Short-term holder realized price reported in USD.",
    ),
    "EXCHANGE_FLOWS": SeriesDefinition(
        series_id="EXCHANGE_FLOWS",
        series_type="onchain",
        unit="btc",
        description="Net exchange flow or provider-equivalent exchange-flow metric reported in BTC.",
    ),
}
ONCHAIN_SERIES_IDS = tuple(ONCHAIN_SERIES_DEFINITIONS)


@dataclass(frozen=True)
class GenericSeriesObservation:
    series_id: str
    series_type: str
    observation_time: datetime
    value: Decimal
    unit: str
    provider: str
    source: str
    revision: str
    available_at: datetime
    ingested_at: datetime

    def as_record(self) -> dict[str, Any]:
        _validate_series_type(self.series_type)
        _validate_availability(self.observation_time, self.available_at)
        return {
            "series_id": self.series_id,
            "series_type": self.series_type,
            "observation_time": require_utc_datetime(self.observation_time, "observation_time"),
            "value": self.value,
            "unit": self.unit,
            "provider": self.provider,
            "source": self.source,
            "revision": self.revision,
            "available_at": require_utc_datetime(self.available_at, "available_at"),
            "ingested_at": require_utc_datetime(self.ingested_at, "ingested_at"),
        }


GenericSeriesRow = GenericSeriesObservation | Mapping[str, Any]


class MacroDataProvider(Protocol):
    """Provider boundary for macro and market-proxy series clients."""

    def fetch_macro_series(
        self,
        *,
        series_ids: Sequence[str],
        start: datetime,
        end: datetime,
    ) -> Iterable[GenericSeriesRow]:
        ...


class OnchainDataProvider(Protocol):
    """Provider boundary for on-chain metric clients."""

    def fetch_onchain_series(
        self,
        *,
        series_ids: Sequence[str],
        start: datetime,
        end: datetime,
    ) -> Iterable[GenericSeriesRow]:
        ...


@dataclass(frozen=True)
class MacroDataCollectionRequest:
    provider: str
    source: str
    start: datetime
    end: datetime
    series_ids: tuple[str, ...] = MACRO_SERIES_IDS
    series_definitions: Mapping[str, SeriesDefinition] | None = None
    market_holidays: frozenset[date] = frozenset()
    max_attempts: int = 3
    retry_backoff_seconds: float = 0

    def __post_init__(self) -> None:
        require_utc_datetime(self.start, "start")
        require_utc_datetime(self.end, "end")
        if self.end < self.start:
            raise ValueError("end must be >= start")
        if not self.series_ids:
            raise ValueError("series_ids must contain at least one series")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds must be >= 0")

    @property
    def definitions(self) -> Mapping[str, SeriesDefinition]:
        return self.series_definitions or MACRO_SERIES_DEFINITIONS


@dataclass(frozen=True)
class MacroDataCollectionResult:
    observations: tuple[GenericSeriesObservation, ...]
    missing_observation_dates: Mapping[str, tuple[date, ...]]
    provider_attempts: int


class MacroDataCollectionError(RuntimeError):
    """Raised when a macro data provider cannot satisfy a collection request."""


@dataclass(frozen=True)
class OnchainDataCollectionRequest:
    provider: str
    source: str
    start: datetime
    end: datetime
    series_ids: tuple[str, ...] = ONCHAIN_SERIES_IDS
    series_definitions: Mapping[str, SeriesDefinition] | None = None
    max_attempts: int = 3
    retry_backoff_seconds: float = 0

    def __post_init__(self) -> None:
        require_utc_datetime(self.start, "start")
        require_utc_datetime(self.end, "end")
        if self.end < self.start:
            raise ValueError("end must be >= start")
        if not self.series_ids:
            raise ValueError("series_ids must contain at least one series")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds must be >= 0")

    @property
    def definitions(self) -> Mapping[str, SeriesDefinition]:
        return self.series_definitions or ONCHAIN_SERIES_DEFINITIONS


@dataclass(frozen=True)
class OnchainDataCollectionResult:
    observations: tuple[GenericSeriesObservation, ...]
    missing_observation_dates: Mapping[str, tuple[date, ...]]
    provider_attempts: int


class OnchainDataCollectionError(RuntimeError):
    """Raised when an on-chain data provider cannot satisfy a collection request."""


def collect_macro_data(
    provider: MacroDataProvider,
    connection: Any,
    request: MacroDataCollectionRequest,
    *,
    ingested_at: datetime | None = None,
) -> MacroDataCollectionResult:
    """Fetch macro series, persist raw revisions, and report missing expected dates."""

    ingestion_time = require_utc_datetime(ingested_at or datetime.now(UTC), "ingested_at")
    rows, attempts = _fetch_with_retry(provider, request)
    observations = _normalize_provider_rows(rows, request=request, ingested_at=ingestion_time)
    missing_observation_dates = missing_macro_observation_dates(
        observations,
        series_ids=request.series_ids,
        start=request.start.date(),
        end=request.end.date(),
        market_holidays=request.market_holidays,
    )

    if observations:
        connection.execute(build_generic_series_insert_ignore(observations))

    return MacroDataCollectionResult(
        observations=observations,
        missing_observation_dates=missing_observation_dates,
        provider_attempts=attempts,
    )


def collect_onchain_data(
    provider: OnchainDataProvider,
    connection: Any,
    request: OnchainDataCollectionRequest,
    *,
    ingested_at: datetime | None = None,
) -> OnchainDataCollectionResult:
    """Fetch on-chain series, persist raw revisions, and report missing calendar dates."""

    ingestion_time = require_utc_datetime(ingested_at or datetime.now(UTC), "ingested_at")
    rows, attempts = _fetch_onchain_with_retry(provider, request)
    observations = _normalize_provider_rows(rows, request=request, ingested_at=ingestion_time)
    missing_observation_dates = missing_onchain_observation_dates(
        observations,
        series_ids=request.series_ids,
        start=request.start.date(),
        end=request.end.date(),
    )

    if observations:
        connection.execute(build_generic_series_insert_ignore(observations))

    return OnchainDataCollectionResult(
        observations=observations,
        missing_observation_dates=missing_observation_dates,
        provider_attempts=attempts,
    )


def build_generic_series_insert_ignore(observations: Sequence[GenericSeriesObservation]):
    """Build an idempotent insert that preserves existing generic-series revisions."""

    if not observations:
        raise ValueError("observations must contain at least one generic-series record")

    statement = insert(generic_series).values([observation.as_record() for observation in observations])
    return statement.on_conflict_do_nothing(index_elements=list(GENERIC_SERIES_PRIMARY_KEY))


def expected_macro_observation_dates(
    *,
    start: date,
    end: date,
    market_holidays: Iterable[date] = (),
) -> tuple[date, ...]:
    """Return expected macro observation dates, excluding weekends and known holidays."""

    if end < start:
        raise ValueError("end must be >= start")

    holidays = set(market_holidays)
    current = start
    expected = []
    while current <= end:
        if current.weekday() < 5 and current not in holidays:
            expected.append(current)
        current += timedelta(days=1)
    return tuple(expected)


def missing_macro_observation_dates(
    observations: Sequence[GenericSeriesObservation],
    *,
    series_ids: Sequence[str],
    start: date,
    end: date,
    market_holidays: Iterable[date] = (),
) -> dict[str, tuple[date, ...]]:
    """Return expected macro observation dates missing by series."""

    expected = expected_macro_observation_dates(
        start=start,
        end=end,
        market_holidays=market_holidays,
    )
    observed_by_series = {series_id: set() for series_id in series_ids}
    for observation in observations:
        if observation.series_id in observed_by_series:
            observed_by_series[observation.series_id].add(observation.observation_time.date())

    return {
        series_id: tuple(observation_date for observation_date in expected if observation_date not in observed)
        for series_id, observed in observed_by_series.items()
    }


def expected_onchain_observation_dates(
    *,
    start: date,
    end: date,
) -> tuple[date, ...]:
    """Return expected on-chain observation dates for a continuous daily market."""

    if end < start:
        raise ValueError("end must be >= start")

    current = start
    expected = []
    while current <= end:
        expected.append(current)
        current += timedelta(days=1)
    return tuple(expected)


def missing_onchain_observation_dates(
    observations: Sequence[GenericSeriesObservation],
    *,
    series_ids: Sequence[str],
    start: date,
    end: date,
) -> dict[str, tuple[date, ...]]:
    """Return expected on-chain observation dates missing by series."""

    expected = expected_onchain_observation_dates(start=start, end=end)
    observed_by_series = {series_id: set() for series_id in series_ids}
    for observation in observations:
        if observation.series_id in observed_by_series:
            observed_by_series[observation.series_id].add(observation.observation_time.date())

    return {
        series_id: tuple(observation_date for observation_date in expected if observation_date not in observed)
        for series_id, observed in observed_by_series.items()
    }


def latest_generic_series_available_at(
    signal_time: datetime,
    *,
    series_ids: Sequence[str] | None = None,
    series_types: Sequence[str] | None = None,
) -> Select:
    """Select latest generic-series revisions available at a signal timestamp."""

    signal_time = require_utc_datetime(signal_time, "signal_time")
    ranked_revisions = (
        select(
            generic_series,
            func.row_number()
            .over(
                partition_by=(
                    generic_series.c.series_id,
                    generic_series.c.observation_time,
                    generic_series.c.provider,
                ),
                order_by=(
                    generic_series.c.available_at.desc(),
                    generic_series.c.revision.desc(),
                ),
            )
            .label("revision_rank"),
        )
        .where(generic_series.c.available_at <= signal_time)
        .where(generic_series.c.observation_time <= signal_time)
    )

    if series_ids is not None:
        ranked_revisions = ranked_revisions.where(generic_series.c.series_id.in_(series_ids))

    if series_types is not None:
        unsupported = sorted(set(series_types) - set(SUPPORTED_SERIES_TYPES))
        if unsupported:
            raise ValueError(f"Unsupported series types: {', '.join(unsupported)}")
        ranked_revisions = ranked_revisions.where(generic_series.c.series_type.in_(series_types))

    subquery = ranked_revisions.subquery()
    return select(subquery).where(subquery.c.revision_rank == 1)


def latest_macro_series_available_at(signal_time: datetime) -> Select:
    """Select latest configured macro candidate series available at signal time."""

    return latest_generic_series_available_at(
        signal_time,
        series_ids=MACRO_SERIES_IDS,
        series_types=("macro", "market_proxy"),
    )


def latest_onchain_series_available_at(signal_time: datetime) -> Select:
    """Select latest configured on-chain candidate series available at signal time."""

    return latest_generic_series_available_at(
        signal_time,
        series_ids=ONCHAIN_SERIES_IDS,
        series_types=("onchain",),
    )


def _fetch_with_retry(
    provider: MacroDataProvider,
    request: MacroDataCollectionRequest,
) -> tuple[tuple[GenericSeriesRow, ...], int]:
    attempts = 0
    while attempts < request.max_attempts:
        attempts += 1
        try:
            return (
                tuple(
                    provider.fetch_macro_series(
                        series_ids=request.series_ids,
                        start=request.start,
                        end=request.end,
                    )
                ),
                attempts,
            )
        except Exception as exc:
            if attempts >= request.max_attempts:
                raise MacroDataCollectionError("Macro data provider failed after retry attempts") from exc
            if request.retry_backoff_seconds:
                sleep(request.retry_backoff_seconds)
    raise MacroDataCollectionError("Macro data provider failed without returning data")


def _fetch_onchain_with_retry(
    provider: OnchainDataProvider,
    request: OnchainDataCollectionRequest,
) -> tuple[tuple[GenericSeriesRow, ...], int]:
    attempts = 0
    while attempts < request.max_attempts:
        attempts += 1
        try:
            return (
                tuple(
                    provider.fetch_onchain_series(
                        series_ids=request.series_ids,
                        start=request.start,
                        end=request.end,
                    )
                ),
                attempts,
            )
        except Exception as exc:
            if attempts >= request.max_attempts:
                raise OnchainDataCollectionError("On-chain data provider failed after retry attempts") from exc
            if request.retry_backoff_seconds:
                sleep(request.retry_backoff_seconds)
    raise OnchainDataCollectionError("On-chain data provider failed without returning data")


def _normalize_provider_rows(
    rows: Iterable[GenericSeriesRow],
    *,
    request: MacroDataCollectionRequest | OnchainDataCollectionRequest,
    ingested_at: datetime,
) -> tuple[GenericSeriesObservation, ...]:
    observations = []
    seen_keys = set()
    for row in rows:
        observation = _coerce_provider_row(row, request=request, ingested_at=ingested_at)
        key = tuple(observation.as_record().items())
        if key in seen_keys:
            raise ValueError("Duplicate generic-series provider record")
        seen_keys.add(key)
        observations.append(observation)
    return tuple(sorted(observations, key=lambda item: (item.observation_time, item.series_id, item.revision)))


def _coerce_provider_row(
    row: GenericSeriesRow,
    *,
    request: MacroDataCollectionRequest | OnchainDataCollectionRequest,
    ingested_at: datetime,
) -> GenericSeriesObservation:
    if isinstance(row, GenericSeriesObservation):
        source = row.as_record()
    else:
        source = dict(row)

    series_id = str(source["series_id"])
    if series_id not in request.series_ids:
        raise ValueError(f"Provider returned unexpected series: {series_id}")

    definition = request.definitions.get(series_id)
    series_type = str(source.get("series_type", definition.series_type if definition else ""))
    unit = str(source.get("unit", definition.unit if definition else ""))
    if not series_type or not unit:
        raise ValueError(f"Series {series_id} requires series_type and unit")

    return GenericSeriesObservation(
        series_id=series_id,
        series_type=series_type,
        observation_time=normalize_utc_datetime(source["observation_time"], "observation_time"),
        value=_decimal(source["value"]),
        unit=unit,
        provider=request.provider,
        source=str(source.get("source", request.source)),
        revision=str(source.get("revision", "initial")),
        available_at=normalize_utc_datetime(source["available_at"], "available_at"),
        ingested_at=ingested_at,
    )


def _validate_series_type(series_type: str) -> None:
    if series_type not in SUPPORTED_SERIES_TYPES:
        raise ValueError(f"Unsupported series type: {series_type}")


def _validate_availability(observation_time: datetime, available_at: datetime) -> None:
    observation_time = require_utc_datetime(observation_time, "observation_time")
    available_at = require_utc_datetime(available_at, "available_at")
    if available_at < observation_time:
        raise ValueError("available_at must be >= observation_time")


def _decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))
