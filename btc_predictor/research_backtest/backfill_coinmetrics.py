"""Coin Metrics Community market-cap adapter for RBT-003 (Part A, offline).

The source is RBT-002's rank-1 market cap, Coin Metrics Community
``CapMrktCurUSD`` at ``1d`` (CC BY-NC 4.0, final values only). Its daily value
for UTC day D is the end-of-day close stamped at D's ``00:00`` (RBT-002 pin
``MARKET_CAP_END_OF_DAY``). The adapter asks for exactly the data-window days
``2020-01-01`` .. ``2025-12-31``, refuses any returned row outside them, and
writes RBT-001A's hash-bound ``BTC_MARKET_CAP_EVIDENCE_V1`` file through the
replay builder's own :func:`replay_inputs_v2.market_cap_evidence_bytes`; the
builder applies the ``D+1 00:00`` stamp and the ``D+2 00:00`` availability.

The timeseries response shape follows the provider's documented form; any
unexpected field refuses the response, and Part B confirms it on one live
in-window page.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlencode

from btc_predictor.research_backtest import replay_inputs_v2 as v2
from btc_predictor.research_backtest.backfill_sources import (
    DATA_WINDOW_START,
    LAST_DATA_DAY,
    BackfillRefused,
    Fetcher,
    sha256_hex,
)


COINMETRICS_TIMESERIES_URL = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
COINMETRICS_SOURCE = "community-api.coinmetrics.io v4 timeseries asset-metrics btc CapMrktCurUSD 1d"
COINMETRICS_LICENCE = "CC BY-NC 4.0 (Coin Metrics Community Data)"
PAGE_SIZE = 10_000
MAX_PAGES = 10
_DAY_STAMP = re.compile(r"(\d{4}-\d{2}-\d{2})T00:00:00\.000000000Z")
_PAGE_KEYS = frozenset({"data", "next_page_token", "next_page_url"})
_ROW_KEYS = frozenset({"asset", "time", v2.MARKET_CAP_METRIC})


def timeseries_url(first_day: date, last_day: date) -> str:
    if not DATA_WINDOW_START.date() <= first_day <= last_day <= LAST_DATA_DAY:
        raise BackfillRefused("REQUEST_OUTSIDE_DATA_WINDOW", f"market cap days {first_day}..{last_day} are not inside the data window")
    query = {
        "assets": v2.MARKET_CAP_ASSET,
        "metrics": v2.MARKET_CAP_METRIC,
        "frequency": v2.MARKET_CAP_FREQUENCY,
        "start_time": first_day.isoformat(),
        "end_time": last_day.isoformat(),
        "end_inclusive": "true",
        "page_size": PAGE_SIZE,
    }
    return f"{COINMETRICS_TIMESERIES_URL}?{urlencode(query)}"


def _refuse(message: str) -> Any:
    raise BackfillRefused("RESPONSE_SHAPE_REFUSED", message)


def parse_timeseries_page(data: bytes, *, first_day: date, last_day: date) -> tuple[tuple[tuple[date, Decimal], ...], str | None]:
    """One page's ``(day, market cap)`` rows and the next page's URL, if any."""

    try:
        payload = json.loads(data)
    except (UnicodeDecodeError, ValueError):
        return _refuse("a market-cap page is not JSON")
    if not isinstance(payload, dict) or "data" not in payload or not set(payload) <= _PAGE_KEYS:
        return _refuse(f"a market-cap page has keys {sorted(payload) if isinstance(payload, dict) else payload!r}")
    next_url = payload.get("next_page_url")
    if next_url is not None and (not isinstance(next_url, str) or not next_url.startswith(f"{COINMETRICS_TIMESERIES_URL}?")):
        return _refuse("the next page is not a Coin Metrics timeseries URL")
    if not isinstance(payload["data"], list):
        return _refuse("data must be a list")
    rows = []
    for item in payload["data"]:
        if not isinstance(item, dict) or set(item) != _ROW_KEYS or item["asset"] != v2.MARKET_CAP_ASSET:
            return _refuse(f"each row is exactly {sorted(_ROW_KEYS)} for asset {v2.MARKET_CAP_ASSET}")
        match = _DAY_STAMP.fullmatch(str(item["time"]))
        if match is None:
            return _refuse(f"row time {item['time']!r} is not a day's 00:00 stamp")
        day = date.fromisoformat(match.group(1))
        if not DATA_WINDOW_START.date() <= day <= LAST_DATA_DAY:
            raise BackfillRefused("OBSERVATION_OUTSIDE_DATA_WINDOW", f"market cap for {day} lies outside the data window")
        if not first_day <= day <= last_day:
            return _refuse(f"market cap for {day} is outside the requested days {first_day}..{last_day}")
        value = item[v2.MARKET_CAP_METRIC]
        try:
            number = Decimal(value) if isinstance(value, str) else None
        except InvalidOperation:
            number = None
        if number is None or not number.is_finite() or number <= 0:
            return _refuse(f"market cap for {day} must be a positive decimal string, not {value!r}")
        rows.append((day, number))
    return tuple(rows), next_url


@dataclass(frozen=True)
class MarketCapCollection:
    rows: tuple[tuple[date, Decimal], ...]
    missing_days: tuple[date, ...]
    evidence_bytes: bytes

    @property
    def evidence_sha256(self) -> str:
        return sha256_hex(self.evidence_bytes)

    def evidence(self) -> v2.MarketCapEvidence:
        return v2.parse_market_cap_evidence(self.evidence_bytes, expected_sha256=self.evidence_sha256)


def read_market_caps(fetcher: Fetcher, first_day: date, last_day: date) -> MarketCapCollection:
    """Every requested day's value, the days the source does not cover, and the evidence file."""

    url: str | None = timeseries_url(first_day, last_day)
    rows: list[tuple[date, Decimal]] = []
    digests: list[str] = []
    retrieved: list[datetime] = []
    for _ in range(MAX_PAGES):
        if url is None:
            break
        page = fetcher.fetch(url)
        digests.append(page.sha256)
        retrieved.append(page.retrieved_at)
        page_rows, url = parse_timeseries_page(page.body, first_day=first_day, last_day=last_day)
        rows.extend(page_rows)
    else:
        if url is not None:
            raise BackfillRefused("CONTINUATION_CHAIN_REFUSED", f"market cap: more than {MAX_PAGES} pages")
    rows.sort()
    if any(later[0] == earlier[0] for earlier, later in zip(rows, rows[1:])):
        raise BackfillRefused("DUPLICATE_PROVIDER_RECORD", "a market-cap day appears twice")
    if not rows:
        return _refuse(f"no market cap was returned for {first_day}..{last_day}")
    present = {day for day, _ in rows}
    span = (last_day - first_day).days + 1
    missing = tuple(day for day in (first_day + timedelta(days=offset) for offset in range(span)) if day not in present)
    evidence = v2.market_cap_evidence_bytes(
        source=COINMETRICS_SOURCE,
        licence=COINMETRICS_LICENCE,
        retrieved_at=max(retrieved),
        response_sha256=digests,
        rows=rows,
    )
    return MarketCapCollection(tuple(rows), missing, evidence)


def missing_day_records(days: Sequence[date]) -> list[str]:
    return [day.isoformat() for day in days]
