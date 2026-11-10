"""CoinGlass ETF flow and AUM adapter for RBT-003 (Part B, ruling 10; shapes UNVERIFIED).

RBT-002's rank-1 ETF source is the CoinGlass Hobbyist plan (USD 29 a month,
personal use): ``etf/bitcoin/flow-history`` gives each day's total and
per-ticker flows, and ``etf/bitcoin/history?ticker=`` gives a ticker's daily
history, whose ``net_assets`` is the fund's total net assets in USD. Owner
ruling 5 (2026-11-04) applies: the response shapes follow the provider's
documented examples (re-read in Part B's first step, 2026-11-05: the
``history`` record is ``assets_date``, ``btc_holdings``, ``market_date``,
``market_price``, ``name``, ``nav``, ``net_assets``, ``premium_discount``,
``shares_outstanding`` and ``ticker``), any unexpected field or shape refuses
the response, and the adapter stays UNVERIFIED until one live response of each
endpoint passes. Every declared field is type-checked, including those the
rows do not use (review F5): the envelope's ``msg``, when present, is a string;
a flow day's total ``flow_usd`` and ``price_usd`` are finite JSON numbers; a
ticker's ``flow_usd`` is a finite JSON number, ``null`` or absent; a fund day's
numbers are finite JSON numbers, its ``name`` a non-empty string and its
``ticker`` the requested one. A JSON number whose exponent no decimal can hold
refuses the response, whatever the caller's decimal context (re-review R14-1).
The first live responses (2026-11-09) omit the
envelope's ``msg`` and, on most of IBIT's days, a fund day's ``btc_holdings``:
owner Part B ruling 14 makes both optional, and each is checked when present.

**Holdout guard (owner Part B ruling 10, 2026-11-05).** Neither endpoint takes
a date bound, so every response holds the whole history, holdout, reserve and
(for a fund that predates 2020) the prohibited window included. The two URLs
carry no date and no other query than the ticker, and a response is read only
through :func:`backfill_projection.project_records`, which drops every record
dated outside the requested in-window days before any of its values is parsed
and counts what it dropped. The parsers accept only a projected response.

The source supplies no publication time and no vintages, so every row is
``FINAL_AS_RETRIEVED``: the replay builder applies the ``T+2 00:00`` floor and
``REVISION_HISTORY_UNAVAILABLE``. The API key travels only in the request
header; the retrieval log records URLs, never headers.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Context, Decimal, InvalidOperation, localcontext
from typing import Any
from urllib.parse import urlencode

from btc_predictor.data import EtfFlow
from btc_predictor.research_backtest.backfill_projection import ProjectedResponse, project_records, verified_body
from btc_predictor.research_backtest.backfill_sources import (
    LAST_DATA_DAY,
    BackfillRefused,
    Clock,
    Fetcher,
    RetrievalLog,
    Transport,
    epoch_milliseconds,
    from_epoch_milliseconds,
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
FLOW_DATE_KEYS = ("timestamp",)
FUND_DATE_KEYS = ("assets_date", "market_date")

_ENVELOPE_KEYS = frozenset({"code", "msg", "data"})
_OPTIONAL_ENVELOPE_KEYS = frozenset({"msg"})  # the live responses omit it (owner Part B ruling 14)
_FLOW_DAY_KEYS = frozenset({"timestamp", "flow_usd", "price_usd", "etf_flows"})
_FLOW_TICKER_KEYS = frozenset({"etf_ticker", "flow_usd"})
_FUND_DAY_KEYS = frozenset(
    {
        "assets_date", "btc_holdings", "market_date", "market_price", "name", "nav", "net_assets",
        "premium_discount", "shares_outstanding", "ticker",
    }
)
_OPTIONAL_FUND_DAY_KEYS = frozenset({"btc_holdings"})  # IBIT's live history mostly omits it (owner Part B ruling 14)
_FUND_NUMBERS = ("btc_holdings", "market_price", "nav", "premium_discount", "shares_outstanding")
# every JSON number is decoded in this context, so one whose exponent no decimal can hold refuses whatever the
# caller's traps, as Kraken's reader does (re-review R12-5); decoding is exact in any precision
_DECODING_CONTEXT = Context(traps=[InvalidOperation])
_TICKER = re.compile(r"[A-Z][A-Z0-9]{0,9}")
_API_KEY = re.compile(r"[!-~]{1,256}")  # visible ASCII only: no space, control byte or line break (review B6)


def coinglass_fetcher(transport: Transport, log: RetrievalLog, *, api_key: str, clock: Clock = utc_now) -> Fetcher:
    if not isinstance(api_key, str) or not _API_KEY.fullmatch(api_key):
        # the message never quotes the key (review B6)
        raise BackfillRefused("PROVIDER_RESPONSE_REFUSED", "a CoinGlass API key of visible ASCII characters is required")
    return Fetcher(transport, log, clock, headers={API_KEY_HEADER: api_key})


def fund_history_url(ticker: str) -> str:
    """The documented per-fund URL: its only query is the ticker (no date bound exists, ruling 10)."""

    if not isinstance(ticker, str) or not _TICKER.fullmatch(ticker):
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"{ticker!r} is not a fund ticker")
    return f"{FUND_HISTORY_URL}?{urlencode({'ticker': ticker})}"


def fund_of_history_url(url: Any) -> str:
    """The ticker a per-fund URL names: its only query."""

    match = re.fullmatch(re.escape(FUND_HISTORY_URL) + r"\?ticker=([A-Z][A-Z0-9]{0,9})", url) if isinstance(url, str) else None
    if match is None:
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", "a fund history URL without its ticker")
    return match.group(1)


def _refuse(message: str) -> Any:
    raise BackfillRefused("RESPONSE_SHAPE_REFUSED", message)


def _envelope(projection: Any, what: str, date_keys: tuple[str, ...]) -> list[Any]:
    # nothing is decoded before the bytes are proven a projection on the endpoint's own date members (review B2)
    body = verified_body(projection, date_keys=date_keys, what=what)
    try:
        with localcontext(_DECODING_CONTEXT):
            payload = json.loads(body, parse_float=Decimal)
    except (UnicodeDecodeError, ValueError):
        return _refuse(f"{what} is not JSON")
    except InvalidOperation:  # re-review R14-1: it raised, stopping the run, instead of refusing
        return _refuse(f"{what} holds a number no decimal can hold")
    if not isinstance(payload, dict) or not _ENVELOPE_KEYS - _OPTIONAL_ENVELOPE_KEYS <= set(payload) <= _ENVELOPE_KEYS:
        return _refuse(f"{what} is not exactly {sorted(_ENVELOPE_KEYS)}, msg optional")
    if payload["code"] != "0" or not isinstance(payload["data"], list):
        return _refuse(f"{what} reports code {payload['code']!r}")
    if "msg" in payload and not isinstance(payload["msg"], str):
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


def parse_flow_history(projection: ProjectedResponse) -> dict[tuple[str, date], Decimal]:
    """Per-ticker flows by ``(ticker, trading date)``; a ticker without a value has no entry."""

    first_day, last_day = getattr(projection, "first_day", None), getattr(projection, "last_day", None)
    flows: dict[tuple[str, date], Decimal] = {}
    days: set[date] = set()
    seen: set[tuple[str, date]] = set()
    for entry in _envelope(projection, "the flow history", FLOW_DATE_KEYS):
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


def parse_fund_history(projection: ProjectedResponse, *, ticker: str) -> dict[date, Decimal]:
    """One ticker's total net assets (USD) by trading date."""

    first_day, last_day = getattr(projection, "first_day", None), getattr(projection, "last_day", None)
    assets: dict[date, Decimal] = {}
    for entry in _envelope(projection, f"the {ticker} history", FUND_DATE_KEYS):
        if not isinstance(entry, dict) or not _FUND_DAY_KEYS - _OPTIONAL_FUND_DAY_KEYS <= set(entry) <= _FUND_DAY_KEYS:
            return _refuse(f"each {ticker} history day is exactly {sorted(_FUND_DAY_KEYS)}, btc_holdings optional")
        day = _trading_day(entry["assets_date"], f"a {ticker} assets date", first_day, last_day)
        _trading_day(entry["market_date"], f"a {ticker} market date", first_day, last_day)  # declared: checked (F5)
        if entry["ticker"] != ticker:
            return _refuse(f"a {ticker} history day names ticker {entry['ticker']!r}")
        if not isinstance(entry["name"], str) or not entry["name"].strip():
            return _refuse(f"a {ticker} history day has no fund name")
        for field in _FUND_NUMBERS:  # unused, but declared: checked (review F5)
            if field in entry or field not in _OPTIONAL_FUND_DAY_KEYS:  # btc_holdings only when present (ruling 14)
                _usd(entry[field], f"{ticker} {day} {field}")
        if day in assets:
            raise BackfillRefused("DUPLICATE_PROVIDER_RECORD", f"{ticker} assets for {day} appear twice")
        value = _usd(entry["net_assets"], f"{ticker} {day} net assets")
        if value < 0:
            return _refuse(f"{ticker} {day}: net assets must be >= 0")
        assets[day] = value
    return assets


@dataclass(frozen=True)
class EtfFlowCollectionRead:
    flows: tuple[EtfFlow, ...]
    tickers_seen: tuple[str, ...]
    missing_aum: tuple[tuple[str, date], ...]
    projections: tuple[ProjectedResponse, ...]  # the flow history first, then each fund's, in request order


def read_etf_flows(
    fetcher: Fetcher, funds: Sequence[str] | None, first_day: date, last_day: date
) -> EtfFlowCollectionRead:
    """The funds' flows with the same day's net assets (``None`` when absent).

    ``funds=None`` reads every ticker the projected flow history names, the
    collection Part B makes: policy V7's fund universe is chosen per decision
    at replay, not here. Every response is projected to
    ``[max(first_day, 2024-01-11), last_day]`` before it is parsed (owner Part B
    ruling 10); the full response is not kept.
    """

    first_day = max(first_day, FIRST_ETF_FLOW_DAY)
    if not first_day <= last_day <= LAST_DATA_DAY:  # before any request: no response is fetched for days outside
        raise BackfillRefused("REQUEST_OUTSIDE_DATA_WINDOW", f"ETF days {first_day}..{last_day} are not inside the data window")
    if funds is not None and (not funds or len(set(funds)) != len(funds)):
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", "name each fund once")
    urls = {ticker: fund_history_url(ticker) for ticker in funds or ()}  # every named ticker is checked before any request
    flow = project_records(
        fetcher.fetch(FLOW_HISTORY_URL), date_keys=FLOW_DATE_KEYS, first_day=first_day, last_day=last_day,
        what="the flow history",
    )
    flows = parse_flow_history(flow)
    if funds is None:
        funds = tuple(sorted({ticker for ticker, _ in flows}))
        urls = {ticker: fund_history_url(ticker) for ticker in funds}
    histories: dict[str, tuple[ProjectedResponse, Mapping[date, Decimal]]] = {}
    for ticker in funds:
        history = project_records(
            fetcher.fetch(urls[ticker]), date_keys=FUND_DATE_KEYS, first_day=first_day, last_day=last_day,
            what=f"the {ticker} history",
        )
        histories[ticker] = (history, parse_fund_history(history, ticker=ticker))
    return _collection(flow, flows, histories)


def etf_flows_from_projections(flow: ProjectedResponse, histories: Sequence[ProjectedResponse]) -> EtfFlowCollectionRead:
    """The ``funds=None`` read rebuilt from its projections alone; nothing is requested (review B3).

    A resumed collection unit's rows must be the prepared read's, retrieval
    instants included: an ETF row's key holds ``available_at``. ``flow`` must
    be the flow history's projection and ``histories`` exactly one per ticker
    the flow history names, in the read's (sorted) order. Every projection is
    proven before it is decoded (review B2).
    """

    if getattr(flow, "url", None) != FLOW_HISTORY_URL:
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", "the first projection is not the flow history's")
    flows = parse_flow_history(flow)
    tickers = tuple(fund_of_history_url(getattr(history, "url", None)) for history in histories)
    if tickers != tuple(sorted({ticker for ticker, _ in flows})):
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", "the fund histories are not exactly the flow history's funds, in order")
    parsed = {ticker: (history, parse_fund_history(history, ticker=ticker)) for ticker, history in zip(tickers, histories)}
    return _collection(flow, flows, parsed)


def _collection(
    flow: ProjectedResponse,
    flows: Mapping[tuple[str, date], Decimal],
    histories: Mapping[str, tuple[ProjectedResponse, Mapping[date, Decimal]]],
) -> EtfFlowCollectionRead:
    """The rows of a parsed flow history and its funds' histories: one path for a live read and a rebuilt one."""

    rows: list[EtfFlow] = []
    missing: list[tuple[str, date]] = []
    for (ticker, day), value in sorted(flows.items(), key=lambda item: (item[0][1], item[0][0])):
        if ticker not in histories:
            continue
        history, assets = histories[ticker]
        retrieved_at = history.retrieved_at
        aum = assets.get(day)
        if aum is None:
            missing.append((ticker, day))
        rows.append(
            EtfFlow(
                fund=ticker,
                observation_date=day,
                flow_usd=value,
                aum_usd=aum,
                provider=COINGLASS_PROVIDER,
                source=FLOW_HISTORY_URL,
                revision=ETF_REVISION,
                available_at=max(flow.retrieved_at, retrieved_at),
                ingested_at=max(flow.retrieved_at, retrieved_at),
            )
        )
    tickers = tuple(sorted({ticker for ticker, _ in flows}))
    projections = (flow, *(history for history, _ in histories.values()))
    return EtfFlowCollectionRead(tuple(rows), tickers, tuple(missing), projections)


def utc_day_stamp(day: date) -> int:
    """A trading date as the epoch-millisecond 00:00 UTC stamp the responses carry."""

    return epoch_milliseconds(datetime(day.year, day.month, day.day, tzinfo=UTC))
