"""Finished RBT-003 collections behind the existing collector protocols (Part A).

The ticket requires collection through the existing collectors and their
provider protocols, with no collector, schema or migration change. The
adapters read and verify whole archives first, so these wrappers hold a
finished collection and serve it to BTC-021's ``collect_btc_derivatives``
(:class:`DerivativesProvider`) and BTC-022's ``collect_etf_flows``
(:class:`EtfFlowProvider`), which persist it with their idempotent inserts.

The collectors stamp ``exchange``, ``symbol`` and ``provider`` from the request,
not from the row. A provider protocol call carries the exchange and symbol but
never the provider, so a wrapper alone cannot see a renamed provider (review
F2). Rows are therefore persisted only through :func:`persist_derivatives` and
:func:`persist_etf_flows`, which refuse, before the unchanged collector runs, a
request that does not name the rows' own exchange, symbol and provider or that
spans days outside the data window: a row is never renamed on its way into the
raw tables. Rows are served for ``[start, end)`` (ETF dates inclusive, as
BTC-022).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from btc_predictor.data import (
    DerivativesCollectionRequest,
    DerivativesCollectionResult,
    EtfFlow,
    EtfFlowCollectionRequest,
    EtfFlowCollectionResult,
    FundingRate,
    FuturesBasis,
    Liquidation,
    OpenInterest,
    PerpVolume,
    collect_btc_derivatives,
    collect_etf_flows,
)
from btc_predictor.research_backtest.backfill_sources import (
    DATA_WINDOW_START,
    LAST_DATA_DAY,
    BackfillRefused,
    require_request_span,
    require_utc,
)


def _identity(rows: Iterable[Any]) -> set[tuple[str, str, str]]:
    return {(row.exchange, row.symbol, row.provider) for row in rows}


@dataclass(frozen=True)
class RecordedDerivativesProvider:
    """One exchange, symbol and provider's finished rows as a ``DerivativesProvider``."""

    exchange: str
    symbol: str
    provider: str
    funding: tuple[FundingRate, ...] = ()
    open_interest_rows: tuple[OpenInterest, ...] = ()
    basis: tuple[FuturesBasis, ...] = ()
    liquidation_rows: tuple[Liquidation, ...] = ()
    perp_volume_rows: tuple[PerpVolume, ...] = ()

    def __post_init__(self) -> None:
        rows = (*self.funding, *self.open_interest_rows, *self.basis, *self.liquidation_rows, *self.perp_volume_rows)
        identities = _identity(rows)
        if identities - {(self.exchange, self.symbol, self.provider)}:
            raise BackfillRefused(
                "PROVIDER_REQUEST_MISMATCH",
                f"rows carry {sorted(identities)}, not only {(self.exchange, self.symbol, self.provider)}",
            )

    def collection_request(self, start: datetime, end: datetime, *, source: str = "provider") -> DerivativesCollectionRequest:
        """The collector request that persists these rows under their own names."""

        return DerivativesCollectionRequest(
            exchange=self.exchange, symbol=self.symbol, provider=self.provider, start=start, end=end, source=source
        )

    def _serve(self, rows: Sequence[Any], *, exchange: str, symbol: str, start: datetime, end: datetime) -> tuple[Any, ...]:
        if (exchange, symbol) != (self.exchange, self.symbol):
            raise BackfillRefused(
                "PROVIDER_REQUEST_MISMATCH", f"the request names {exchange}/{symbol}; these rows are {self.exchange}/{self.symbol}"
            )
        start, end = require_utc(start, "start"), require_utc(end, "end")
        return tuple(row for row in rows if start <= row.observation_time < end)

    def fetch_funding_rates(self, *, exchange: str, symbol: str, start: datetime, end: datetime, **_: Any) -> tuple[FundingRate, ...]:
        return self._serve(self.funding, exchange=exchange, symbol=symbol, start=start, end=end)

    def fetch_open_interest(self, *, exchange: str, symbol: str, start: datetime, end: datetime, **_: Any) -> tuple[OpenInterest, ...]:
        return self._serve(self.open_interest_rows, exchange=exchange, symbol=symbol, start=start, end=end)

    def fetch_futures_basis(self, *, exchange: str, symbol: str, start: datetime, end: datetime, **_: Any) -> tuple[FuturesBasis, ...]:
        return self._serve(self.basis, exchange=exchange, symbol=symbol, start=start, end=end)

    def fetch_liquidations(self, *, exchange: str, symbol: str, start: datetime, end: datetime, **_: Any) -> tuple[Liquidation, ...]:
        return self._serve(self.liquidation_rows, exchange=exchange, symbol=symbol, start=start, end=end)

    def fetch_perp_volume(self, *, exchange: str, symbol: str, start: datetime, end: datetime, **_: Any) -> tuple[PerpVolume, ...]:
        return self._serve(self.perp_volume_rows, exchange=exchange, symbol=symbol, start=start, end=end)


@dataclass(frozen=True)
class RecordedEtfFlowProvider:
    """One provider's finished ETF rows as an ``EtfFlowProvider`` (dates inclusive, as BTC-022)."""

    provider: str
    flows: tuple[EtfFlow, ...]

    def __post_init__(self) -> None:
        providers = {flow.provider for flow in self.flows}
        if providers - {self.provider}:
            raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"rows carry providers {sorted(providers)}, not only {self.provider}")

    def collection_request(self, funds: Sequence[str], start: date, end: date, *, source: str, market_holidays: frozenset[date]) -> EtfFlowCollectionRequest:
        return EtfFlowCollectionRequest(
            funds=tuple(funds), provider=self.provider, source=source, start=start, end=end, market_holidays=market_holidays
        )

    def fetch_etf_flows(self, *, funds: Sequence[str], start: date, end: date) -> tuple[EtfFlow, ...]:
        wanted = set(funds)
        return tuple(flow for flow in self.flows if flow.fund in wanted and start <= flow.observation_date <= end)


def persist_derivatives(
    provider: RecordedDerivativesProvider,
    connection: Any,
    request: DerivativesCollectionRequest,
    *,
    ingested_at: datetime | None = None,
) -> DerivativesCollectionResult:
    """Persist a finished collection through BTC-021's collector under the rows' own names."""

    if not isinstance(provider, RecordedDerivativesProvider) or not isinstance(request, DerivativesCollectionRequest):
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", "persist a RecordedDerivativesProvider with a DerivativesCollectionRequest")
    named, own = (request.exchange, request.symbol, request.provider), (provider.exchange, provider.symbol, provider.provider)
    if named != own:
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"the request names {named}; these rows are {own}")
    require_request_span(request.start, request.end, "a persistence request")
    return collect_btc_derivatives(provider, connection, request, ingested_at=ingested_at)


def persist_etf_flows(
    provider: RecordedEtfFlowProvider,
    connection: Any,
    request: EtfFlowCollectionRequest,
    *,
    ingested_at: datetime | None = None,
) -> EtfFlowCollectionResult:
    """Persist finished ETF rows through BTC-022's collector under their own provider."""

    if not isinstance(provider, RecordedEtfFlowProvider) or not isinstance(request, EtfFlowCollectionRequest):
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", "persist a RecordedEtfFlowProvider with an EtfFlowCollectionRequest")
    if request.provider != provider.provider:
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"the request names provider {request.provider!r}; these rows are {provider.provider!r}")
    if not DATA_WINDOW_START.date() <= request.start <= request.end <= LAST_DATA_DAY:
        raise BackfillRefused("REQUEST_OUTSIDE_DATA_WINDOW", f"ETF days {request.start}..{request.end} are not inside the data window")
    return collect_etf_flows(provider, connection, request, ingested_at=ingested_at)
