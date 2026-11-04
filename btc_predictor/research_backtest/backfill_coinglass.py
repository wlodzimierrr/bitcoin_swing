"""CoinGlass ETF flow and AUM adapter for RBT-003 (Part A, offline, UNVERIFIED).

RBT-002's rank-1 ETF source is the CoinGlass Hobbyist plan (USD 29 a month,
personal use): ``etf/bitcoin/flow-history`` gives each day's total and
per-ticker flows, and ``etf/bitcoin/history`` gives a ticker's net-assets
history (RBT-002 recorded ``assets_date``, ``btc_holdings`` and net assets).
Nothing is purchased and no key exists, so owner ruling 5 (2026-11-04) applies:
the response shapes follow the documented examples as RBT-002 recorded them,
any unexpected field or shape refuses the response, and the adapter stays
UNVERIFIED until Part B checks one live in-window response of each endpoint.
``net_assets_usd`` is this adapter's reading of "net assets"; Part B confirms
the name. Every declared field is type-checked, including those the rows do
not use (review F5): the envelope's ``msg`` is a string; a flow day's total
``flow_usd`` and ``price_usd`` and a fund day's ``btc_holdings`` are finite JSON
numbers; a ticker's ``flow_usd`` is a finite JSON number, ``null`` or absent.

**Holdout guard.** CoinGlass serves history to the present, so an unbounded
request would return 2026 rows, which policy V7 section 3 forbids collecting.
No request is built without :class:`DateBoundParameters`, the documented
query parameters that end the response on 2025-12-31; Part B supplies them
from the provider's documentation, not from a data response. A returned row
outside the data window is still refused, never filtered.

The source supplies no publication time and no vintages, so every row is
``FINAL_AS_RETRIEVED``: the replay builder applies the ``T+2 00:00`` floor and
``REVISION_HISTORY_UNAVAILABLE``. The API key travels only in the request
header; the retrieval log records URLs, never headers.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

from btc_predictor.data import EtfFlow
from btc_predictor.research_backtest.backfill_sources import (
    DATA_WINDOW_START,
    LAST_DATA_DAY,
    BackfillRefused,
    Clock,
    Fetcher,
    RetrievalLog,
    Transport,
    epoch_milliseconds,
    from_epoch_milliseconds,
    midnight,
    require_observation_in_window,
    utc_now,
)


COINGLASS_BASE_URL = "https://open-api-v4.coinglass.com"
FLOW_HISTORY_URL = f"{COINGLASS_BASE_URL}/api/etf/bitcoin/flow-history"
FUND_HISTORY_URL = f"{COINGLASS_BASE_URL}/api/etf/bitcoin/history"
COINGLASS_PROVIDER = "coinglass"
COINGLASS_LICENCE = "CoinGlass Hobbyist plan: personal use; no publication or redistribution"
API_KEY_HEADER = "CG-API-KEY"
ETF_REVISION = "FINAL_AS_RETRIEVED"
FIRST_ETF_FLOW_DAY = date(2024, 1, 11)  # US spot bitcoin ETFs began trading (policy V7 section 3)

_ENVELOPE_KEYS = frozenset({"code", "msg", "data"})
_FLOW_DAY_KEYS = frozenset({"timestamp", "flow_usd", "price_usd", "etf_flows"})
_FLOW_TICKER_KEYS = frozenset({"etf_ticker", "flow_usd"})
_FUND_DAY_KEYS = frozenset({"assets_date", "btc_holdings", "net_assets_usd"})


@dataclass(frozen=True)
class DateBoundParameters:
    """The documented query parameters that bound a response to a day range.

    ``unit`` is ``"ms"`` (epoch milliseconds of the day's 00:00 and of the last
    day's end) or ``"date"`` (ISO dates, the end inclusive).
    """

    start: str
    end: str
    unit: str

    def __post_init__(self) -> None:
        if not self.start.strip() or not self.end.strip() or self.start == self.end:
            raise BackfillRefused("REQUEST_OUTSIDE_DATA_WINDOW", "date-bound parameters need two distinct names")
        if self.unit not in ("ms", "date"):
            raise BackfillRefused("REQUEST_OUTSIDE_DATA_WINDOW", f"unknown date-bound unit {self.unit!r}")

    def query(self, first_day: date, last_day: date) -> dict[str, Any]:
        if not DATA_WINDOW_START.date() <= first_day <= last_day <= LAST_DATA_DAY:
            raise BackfillRefused("REQUEST_OUTSIDE_DATA_WINDOW", f"ETF days {first_day}..{last_day} are not inside the data window")
        if self.unit == "date":
            return {self.start: first_day.isoformat(), self.end: last_day.isoformat()}
        last_instant = midnight(last_day) + timedelta(days=1) - timedelta(milliseconds=1)
        return {self.start: epoch_milliseconds(midnight(first_day)), self.end: epoch_milliseconds(last_instant)}


def coinglass_fetcher(transport: Transport, log: RetrievalLog, *, api_key: str, clock: Clock = utc_now) -> Fetcher:
    if not api_key or api_key != api_key.strip():
        raise BackfillRefused("PROVIDER_RESPONSE_REFUSED", "a CoinGlass API key is required")
    return Fetcher(transport, log, clock, headers={API_KEY_HEADER: api_key})


def flow_history_url(bounds: DateBoundParameters | None, first_day: date, last_day: date) -> str:
    if bounds is None:
        raise BackfillRefused(
            "REQUEST_OUTSIDE_DATA_WINDOW", "no documented date bound: an unbounded ETF request would return holdout rows"
        )
    return f"{FLOW_HISTORY_URL}?{urlencode(bounds.query(first_day, last_day))}"


def fund_history_url(bounds: DateBoundParameters | None, ticker: str, first_day: date, last_day: date) -> str:
    if bounds is None:
        raise BackfillRefused(
            "REQUEST_OUTSIDE_DATA_WINDOW", "no documented date bound: an unbounded ETF request would return holdout rows"
        )
    return f"{FUND_HISTORY_URL}?{urlencode({'ticker': ticker, **bounds.query(first_day, last_day)})}"


def _refuse(message: str) -> Any:
    raise BackfillRefused("RESPONSE_SHAPE_REFUSED", message)


def _envelope(data: bytes, what: str) -> list[Any]:
    try:
        payload = json.loads(data, parse_float=Decimal)
    except (UnicodeDecodeError, ValueError):
        return _refuse(f"{what} is not JSON")
    if not isinstance(payload, dict) or set(payload) != _ENVELOPE_KEYS:
        return _refuse(f"{what} is not exactly {sorted(_ENVELOPE_KEYS)}")
    if payload["code"] != "0" or not isinstance(payload["data"], list):
        return _refuse(f"{what} reports code {payload['code']!r}")
    if not isinstance(payload["msg"], str):
        return _refuse(f"{what}: msg {payload['msg']!r} is not a string")
    return payload["data"]


def _usd(value: Any, what: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
        return _refuse(f"{what} {value!r} is not a JSON number")
    number = Decimal(value)
    if not number.is_finite():
        return _refuse(f"{what} {value!r} is not finite")
    return number


def _trading_day(stamp: Any, what: str, first_day: date, last_day: date) -> date:
    instant = require_observation_in_window(from_epoch_milliseconds(stamp, what), what)
    if (instant.hour, instant.minute, instant.second, instant.microsecond) != (0, 0, 0, 0):
        return _refuse(f"{what} {instant.isoformat()} is not a UTC day stamp")
    if not first_day <= instant.date() <= last_day:
        return _refuse(f"{what} {instant.date()} is outside the requested days {first_day}..{last_day}")
    return instant.date()


def parse_flow_history(data: bytes, *, first_day: date, last_day: date) -> dict[tuple[str, date], Decimal]:
    """Per-ticker flows by ``(ticker, trading date)``; a ticker without a value has no entry."""

    flows: dict[tuple[str, date], Decimal] = {}
    days: set[date] = set()
    seen: set[tuple[str, date]] = set()
    for entry in _envelope(data, "the flow history"):
        if not isinstance(entry, dict) or set(entry) != _FLOW_DAY_KEYS or not isinstance(entry["etf_flows"], list):
            return _refuse(f"each flow day is exactly {sorted(_FLOW_DAY_KEYS)}")
        day = _trading_day(entry["timestamp"], "a flow day", first_day, last_day)
        if day in days:
            raise BackfillRefused("DUPLICATE_PROVIDER_RECORD", f"flow day {day} appears twice")
        days.add(day)
        _usd(entry["flow_usd"], f"the {day} total flow_usd")  # unused, but declared: checked (review F5)
        _usd(entry["price_usd"], f"the {day} price_usd")
        for item in entry["etf_flows"]:
            if not isinstance(item, dict) or "etf_ticker" not in item or not set(item) <= _FLOW_TICKER_KEYS:
                return _refuse(f"each ticker flow is within {sorted(_FLOW_TICKER_KEYS)} and names its ticker")
            ticker = item["etf_ticker"]
            if not isinstance(ticker, str) or not ticker or ticker != ticker.strip():
                return _refuse(f"ticker {ticker!r} is not a fund identifier")
            if (ticker, day) in seen:  # with or without a value
                raise BackfillRefused("DUPLICATE_PROVIDER_RECORD", f"{ticker} {day} appears twice")
            seen.add((ticker, day))
            if item.get("flow_usd") is not None:
                flows[(ticker, day)] = _usd(item["flow_usd"], f"{ticker} {day} flow_usd")
    return flows


def parse_fund_history(data: bytes, *, ticker: str, first_day: date, last_day: date) -> dict[date, Decimal]:
    """One ticker's net assets by trading date."""

    assets: dict[date, Decimal] = {}
    for entry in _envelope(data, f"the {ticker} history"):
        if not isinstance(entry, dict) or set(entry) != _FUND_DAY_KEYS:
            return _refuse(f"each {ticker} history day is exactly {sorted(_FUND_DAY_KEYS)}")
        day = _trading_day(entry["assets_date"], f"a {ticker} assets date", first_day, last_day)
        _usd(entry["btc_holdings"], f"{ticker} {day} btc_holdings")  # unused, but declared: checked (review F5)
        if day in assets:
            raise BackfillRefused("DUPLICATE_PROVIDER_RECORD", f"{ticker} assets for {day} appear twice")
        value = _usd(entry["net_assets_usd"], f"{ticker} {day} net assets")
        if value < 0:
            return _refuse(f"{ticker} {day}: net assets must be >= 0")
        assets[day] = value
    return assets


@dataclass(frozen=True)
class EtfFlowCollectionRead:
    flows: tuple[EtfFlow, ...]
    tickers_seen: tuple[str, ...]
    missing_aum: tuple[tuple[str, date], ...]


def read_etf_flows(
    fetcher: Fetcher,
    funds: Sequence[str],
    first_day: date,
    last_day: date,
    *,
    bounds: DateBoundParameters | None,
) -> EtfFlowCollectionRead:
    """The requested funds' flows with the same day's net assets (``None`` when absent)."""

    first_day = max(first_day, FIRST_ETF_FLOW_DAY)
    if not funds or len(set(funds)) != len(funds):
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", "name each fund once")
    page = fetcher.fetch(flow_history_url(bounds, first_day, last_day))
    flows = parse_flow_history(page.body, first_day=first_day, last_day=last_day)
    histories: dict[str, tuple[Mapping[date, Decimal], datetime]] = {}
    for ticker in funds:
        history = fetcher.fetch(fund_history_url(bounds, ticker, first_day, last_day))
        histories[ticker] = (
            parse_fund_history(history.body, ticker=ticker, first_day=first_day, last_day=last_day),
            history.retrieved_at,
        )
    rows: list[EtfFlow] = []
    missing: list[tuple[str, date]] = []
    for (ticker, day), flow in sorted(flows.items(), key=lambda item: (item[0][1], item[0][0])):
        if ticker not in histories:
            continue
        assets, retrieved_at = histories[ticker]
        aum = assets.get(day)
        if aum is None:
            missing.append((ticker, day))
        rows.append(
            EtfFlow(
                fund=ticker,
                observation_date=day,
                flow_usd=flow,
                aum_usd=aum,
                provider=COINGLASS_PROVIDER,
                source=FLOW_HISTORY_URL,
                revision=ETF_REVISION,
                available_at=max(page.retrieved_at, retrieved_at),
                ingested_at=max(page.retrieved_at, retrieved_at),
            )
        )
    tickers = tuple(sorted({ticker for ticker, _ in flows}))
    return EtfFlowCollectionRead(tuple(rows), tickers, tuple(missing))


def utc_day_stamp(day: date) -> int:
    """A trading date as the epoch-millisecond 00:00 UTC stamp the responses carry."""

    return epoch_milliseconds(datetime(day.year, day.month, day.day, tzinfo=UTC))
