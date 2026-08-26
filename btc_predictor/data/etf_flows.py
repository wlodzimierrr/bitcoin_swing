"""ETF flow collection and point-in-time helpers."""

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
from btc_predictor.db.raw import ETF_FLOWS_PRIMARY_KEY, etf_flows


@dataclass(frozen=True)
class EtfFlow:
    fund: str
    observation_date: date
    flow_usd: Decimal
    aum_usd: Decimal | None
    provider: str
    source: str
    revision: str
    available_at: datetime
    ingested_at: datetime

    def as_record(self) -> dict[str, Any]:
        return {
            "fund": self.fund,
            "observation_date": self.observation_date,
            "flow_usd": self.flow_usd,
            "aum_usd": self.aum_usd,
            "provider": self.provider,
            "source": self.source,
            "revision": self.revision,
            "available_at": require_utc_datetime(self.available_at, "available_at"),
            "ingested_at": require_utc_datetime(self.ingested_at, "ingested_at"),
        }


EtfFlowRow = EtfFlow | Mapping[str, Any]


class EtfFlowProvider(Protocol):
    """Provider boundary for ETF flow data clients."""

    def fetch_etf_flows(
        self,
        *,
        funds: Sequence[str],
        start: date,
        end: date,
    ) -> Iterable[EtfFlowRow]:
        ...


@dataclass(frozen=True)
class EtfFlowCollectionRequest:
    funds: tuple[str, ...]
    provider: str
    source: str
    start: date
    end: date
    market_holidays: frozenset[date] = frozenset()
    max_attempts: int = 3
    retry_backoff_seconds: float = 0

    def __post_init__(self) -> None:
        if not self.funds:
            raise ValueError("funds must contain at least one ETF identifier")
        if self.end < self.start:
            raise ValueError("end must be >= start")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds must be >= 0")


@dataclass(frozen=True)
class EtfFlowCollectionResult:
    flows: tuple[EtfFlow, ...]
    missing_publication_dates: Mapping[str, tuple[date, ...]]
    provider_attempts: int


class EtfFlowCollectionError(RuntimeError):
    """Raised when an ETF flow provider cannot satisfy a collection request."""


def collect_etf_flows(
    provider: EtfFlowProvider,
    connection: Any,
    request: EtfFlowCollectionRequest,
    *,
    ingested_at: datetime | None = None,
) -> EtfFlowCollectionResult:
    """Fetch daily ETF flows, persist raw revisions, and report publication gaps."""

    ingestion_time = require_utc_datetime(ingested_at or datetime.now(UTC), "ingested_at")
    rows, attempts = _fetch_with_retry(provider, request)
    flows = _normalize_provider_rows(rows, request=request, ingested_at=ingestion_time)
    missing_publication_dates = missing_etf_publication_dates(
        flows,
        funds=request.funds,
        start=request.start,
        end=request.end,
        market_holidays=request.market_holidays,
    )

    if flows:
        connection.execute(build_etf_flows_insert_ignore(flows))

    return EtfFlowCollectionResult(
        flows=flows,
        missing_publication_dates=missing_publication_dates,
        provider_attempts=attempts,
    )


def build_etf_flows_insert_ignore(flows: Sequence[EtfFlow]):
    """Build an idempotent insert that preserves existing ETF flow revisions."""

    if not flows:
        raise ValueError("flows must contain at least one ETF flow record")

    statement = insert(etf_flows).values([flow.as_record() for flow in flows])
    return statement.on_conflict_do_nothing(index_elements=list(ETF_FLOWS_PRIMARY_KEY))


def expected_etf_publication_dates(
    *,
    start: date,
    end: date,
    market_holidays: Iterable[date] = (),
) -> tuple[date, ...]:
    """Return expected ETF publication dates, excluding weekends and known holidays."""

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


def missing_etf_publication_dates(
    flows: Sequence[EtfFlow],
    *,
    funds: Sequence[str],
    start: date,
    end: date,
    market_holidays: Iterable[date] = (),
) -> dict[str, tuple[date, ...]]:
    """Return expected ETF flow publication dates missing by fund."""

    expected = expected_etf_publication_dates(
        start=start,
        end=end,
        market_holidays=market_holidays,
    )
    observed_by_fund = {fund: set() for fund in funds}
    for flow in flows:
        if flow.fund in observed_by_fund:
            observed_by_fund[flow.fund].add(flow.observation_date)

    return {
        fund: tuple(publication_date for publication_date in expected if publication_date not in observed)
        for fund, observed in observed_by_fund.items()
    }


def latest_etf_flows_available_at(signal_time: datetime) -> Select:
    """Select latest ETF flow revisions available at a signal timestamp."""

    signal_time = require_utc_datetime(signal_time, "signal_time")
    ranked_revisions = (
        select(
            etf_flows,
            func.row_number()
            .over(
                partition_by=(
                    etf_flows.c.fund,
                    etf_flows.c.observation_date,
                    etf_flows.c.provider,
                ),
                order_by=(
                    etf_flows.c.available_at.desc(),
                    etf_flows.c.revision.desc(),
                ),
            )
            .label("revision_rank"),
        )
        .where(etf_flows.c.available_at <= signal_time)
        .subquery()
    )

    return select(ranked_revisions).where(ranked_revisions.c.revision_rank == 1)


def _fetch_with_retry(
    provider: EtfFlowProvider,
    request: EtfFlowCollectionRequest,
) -> tuple[tuple[EtfFlowRow, ...], int]:
    attempts = 0
    while attempts < request.max_attempts:
        attempts += 1
        try:
            return (
                tuple(
                    provider.fetch_etf_flows(
                        funds=request.funds,
                        start=request.start,
                        end=request.end,
                    )
                ),
                attempts,
            )
        except Exception as exc:
            if attempts >= request.max_attempts:
                raise EtfFlowCollectionError("ETF flow provider failed after retry attempts") from exc
            if request.retry_backoff_seconds:
                sleep(request.retry_backoff_seconds)
    raise EtfFlowCollectionError("ETF flow provider failed without returning data")


def _normalize_provider_rows(
    rows: Iterable[EtfFlowRow],
    *,
    request: EtfFlowCollectionRequest,
    ingested_at: datetime,
) -> tuple[EtfFlow, ...]:
    flows = []
    seen_keys = set()
    for row in rows:
        flow = _coerce_provider_row(row, request=request, ingested_at=ingested_at)
        key = tuple(flow.as_record().items())
        if key in seen_keys:
            raise ValueError("Duplicate ETF flow provider record")
        seen_keys.add(key)
        flows.append(flow)
    return tuple(sorted(flows, key=lambda flow: (flow.observation_date, flow.fund, flow.revision)))


def _coerce_provider_row(
    row: EtfFlowRow,
    *,
    request: EtfFlowCollectionRequest,
    ingested_at: datetime,
) -> EtfFlow:
    if isinstance(row, EtfFlow):
        source = row.as_record()
    else:
        source = dict(row)

    available_at = normalize_utc_datetime(source["available_at"], "available_at")
    return EtfFlow(
        fund=str(source["fund"]),
        observation_date=_coerce_date(source["observation_date"]),
        flow_usd=_monetary_usd(source, "flow"),
        aum_usd=_optional_monetary_usd(source, "aum"),
        provider=request.provider,
        source=str(source.get("source", request.source)),
        revision=str(source.get("revision", "initial")),
        available_at=available_at,
        ingested_at=ingested_at,
    )


def _coerce_date(value: Any) -> date:
    if isinstance(value, datetime):
        return normalize_utc_datetime(value, "observation_date").date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _monetary_usd(source: Mapping[str, Any], field_name: str) -> Decimal:
    explicit_key = f"{field_name}_usd"
    if explicit_key in source:
        return _decimal(source[explicit_key])

    unit = str(source.get(f"{field_name}_unit", "USD")).upper()
    if unit != "USD":
        raise ValueError(f"{field_name} must be denominated in USD")
    return _decimal(source[field_name])


def _optional_monetary_usd(source: Mapping[str, Any], field_name: str) -> Decimal | None:
    explicit_key = f"{field_name}_usd"
    if explicit_key in source and source[explicit_key] is not None:
        return _decimal(source[explicit_key])
    if field_name in source and source[field_name] is not None:
        unit = str(source.get(f"{field_name}_unit", "USD")).upper()
        if unit != "USD":
            raise ValueError(f"{field_name} must be denominated in USD")
        return _decimal(source[field_name])
    return None


def _decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))
