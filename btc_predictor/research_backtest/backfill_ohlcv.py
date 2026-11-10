"""RBT-003 Part B: the Coinbase and Bitfinex hours RBT-002 found missing, re-requested (owner Part B ruling 15).

RBT-002's census of ``raw.btc_ohlcv`` found every in-window ``1h`` hour of
Bitstamp, and all but 11 Coinbase and 16 Bitfinex hours. Its acquisition plan
re-requests those hours through the existing adapters, and any hour still
missing stays a preserved gap. The dataset build freezes each venue's price
series, so this re-request comes before it (ruling 15).

This module reads exactly those hours through the unchanged BTC-020
``CoinbaseOhlcvProvider`` and ``BitfinexOhlcvProvider``. It replaces their JSON
requester with one that reads through the backfill fetcher, so every response
comes from the backfill transport's allowlisted hosts and is logged (URL,
instant, status, size and SHA-256, never a value). Before an adapter sees a
response, the requester refuses one that is not a JSON list of candle rows,
each starting with the integer epoch the adapter documents. It also refuses
any candle dated outside the data window: that is an exposure to record,
refused and never filtered (Part A's decision 1). The adapter itself keeps
only the requested hours and checks each candle. Every value it returns must
be one ``raw.btc_ohlcv``'s ``NUMERIC(38,18)`` columns hold exactly, so the row
persisted is the row read.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from btc_predictor.data.bitfinex import BitfinexOhlcvProvider
from btc_predictor.data.coinbase import CoinbaseOhlcvProvider
from btc_predictor.data.ohlcv import OhlcvProvider
from btc_predictor.research_backtest import replay_inputs as v1
from btc_predictor.research_backtest.backfill_kraken import fits_raw_numeric
from btc_predictor.research_backtest.backfill_sources import (
    BackfillRefused,
    Fetcher,
    from_epoch_milliseconds,
    iso,
    require_observation_in_window,
    require_request_span,
)

TIMEFRAME = "1h"
VALUE_FIELDS = ("open", "high", "low", "close", "volume")
_HOUR = timedelta(hours=1)
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)

JsonRequester = Callable[[str], Any]


def _hour(year: int, month: int, day: int, hour: int) -> datetime:
    return datetime(year, month, day, hour, tzinfo=UTC)


# RBT-002's census (2026-10-01), checked again read-only on 2026-11-10: every in-window grid hour
# each venue lacks, as runs of consecutive hours (first, last), both inclusive.
COINBASE_MISSING_RUNS = (
    (_hour(2020, 1, 30, 17), _hour(2020, 1, 30, 17)),
    (_hour(2020, 9, 4, 23), _hour(2020, 9, 4, 23)),
    (_hour(2020, 10, 20, 20), _hour(2020, 10, 20, 20)),
    (_hour(2023, 3, 4, 18), _hour(2023, 3, 4, 20)),
    (_hour(2025, 10, 25, 16), _hour(2025, 10, 25, 20)),
)
BITFINEX_MISSING_RUNS = (
    (_hour(2020, 2, 11, 11), _hour(2020, 2, 11, 12)),
    (_hour(2020, 8, 12, 21), _hour(2020, 8, 12, 21)),
    (_hour(2021, 6, 30, 8), _hour(2021, 6, 30, 9)),
    (_hour(2021, 10, 13, 14), _hour(2021, 10, 13, 16)),
    (_hour(2022, 10, 12, 8), _hour(2022, 10, 12, 11)),
    (_hour(2023, 3, 6, 10), _hour(2023, 3, 6, 11)),
    (_hour(2024, 5, 5, 10), _hour(2024, 5, 5, 11)),
)


def _epoch_seconds(value: Any, what: str) -> datetime:
    """Coinbase's candle time: an integer of epoch seconds (ten digits across the data window)."""

    text = str(value)
    if type(value) is not int or not text.isdigit() or len(text) != 10:
        raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"{what} is not an epoch in seconds")
    return _EPOCH + timedelta(seconds=value)


def _epoch_milliseconds(value: Any, what: str) -> datetime:
    """Bitfinex's candle ``MTS``: an integer of epoch milliseconds (thirteen digits)."""

    if type(value) is not int:
        raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"{what} is not an epoch in milliseconds")
    return from_epoch_milliseconds(value, what)


@dataclass(frozen=True)
class MissingHoursVenue:
    """One venue's missing hours and the BTC-020 adapter that reads them."""

    venue: v1.ReplayVenue
    runs: tuple[tuple[datetime, datetime], ...]
    adapter: Callable[[JsonRequester], OhlcvProvider]
    candle_instant: Callable[[Any, str], datetime]

    def hours(self) -> tuple[datetime, ...]:
        return tuple(hour for first, last in self.runs for hour in hours_between(first, last))


MISSING_HOURS_VENUES: dict[str, MissingHoursVenue] = {
    "bitfinex": MissingHoursVenue(
        v1.BITFINEX_REPLAY_VENUE, BITFINEX_MISSING_RUNS, lambda requester: BitfinexOhlcvProvider(request_json=requester), _epoch_milliseconds
    ),
    "coinbase": MissingHoursVenue(
        v1.COINBASE_REPLAY_VENUE, COINBASE_MISSING_RUNS, lambda requester: CoinbaseOhlcvProvider(request_json=requester), _epoch_seconds
    ),
}


def hours_between(first: datetime, last: datetime) -> tuple[datetime, ...]:
    """Every hour from ``first`` to ``last``, both inclusive."""

    hours, hour = [], first
    while hour <= last:
        hours.append(hour)
        hour += _HOUR
    return tuple(hours)


def _no_constant(name: str) -> Any:
    raise ValueError(f"{name} is not a JSON number")


def bounded_requester(fetcher: Fetcher, candle_instant: Callable[[Any, str], datetime], what: str) -> JsonRequester:
    """The adapter's JSON requester, read through ``fetcher`` and bounded to the data window.

    The response must be a JSON list of candle rows, each a non-empty list
    whose first element is the integer epoch the venue documents. Every candle
    must lie inside the data window, or the response is refused (an exposure,
    never filtered). The rest of each row is the adapter's to check.
    """

    def request_json(url: str) -> Any:
        page = fetcher.fetch(url)
        try:
            payload = json.loads(page.body, parse_constant=_no_constant)
        except (UnicodeDecodeError, ValueError, RecursionError):
            raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"{what}: a response is not JSON") from None
        if not isinstance(payload, list):
            raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"{what}: a response is not a list of candles")
        for index, row in enumerate(payload):
            if not isinstance(row, list) or not row:
                raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"{what}: candle {index} is not a list")
            require_observation_in_window(candle_instant(row[0], f"{what}: candle {index}'s time"), f"{what}: a returned candle")
        return payload

    return request_json


@dataclass(frozen=True)
class MissingHoursRead:
    """What one venue's re-request returned: the adapter's rows for the requested hours only."""

    unit: str
    venue: v1.ReplayVenue
    runs: tuple[tuple[datetime, datetime], ...]
    rows: tuple[Mapping[str, Any], ...]
    requested: tuple[datetime, ...]
    returned: tuple[datetime, ...]

    @property
    def still_missing(self) -> tuple[datetime, ...]:
        returned = set(self.returned)
        return tuple(hour for hour in self.requested if hour not in returned)

    def summary(self) -> dict[str, Any]:
        """Value-free: the hours requested, returned and still missing, and the row count."""

        return {
            "venue": self.venue.venue_id,
            "rows": len(self.rows),
            "requested_hours": [iso(hour) for hour in self.requested],
            "returned_hours": [iso(hour) for hour in self.returned],
            "still_missing_hours": [iso(hour) for hour in self.still_missing],
        }


def read_missing_hours(fetcher: Fetcher, unit: str) -> MissingHoursRead:
    """Re-request one venue's missing hours (owner Part B ruling 15), one adapter call per run."""

    spec = MISSING_HOURS_VENUES.get(unit) if isinstance(unit, str) else None
    if spec is None:
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"no missing hours are scheduled for {unit!r}")
    provider = spec.adapter(bounded_requester(fetcher, spec.candle_instant, f"{spec.venue.venue_id} missing hours"))
    rows: list[Mapping[str, Any]] = []
    for first, last in spec.runs:
        require_request_span(first, last + _HOUR, f"{spec.venue.venue_id} missing hours")
        try:
            got = tuple(
                provider.fetch_ohlcv(
                    exchange=spec.venue.exchange, symbol=spec.venue.symbol, timeframe=TIMEFRAME, start=first, end=last
                )
            )
        except BackfillRefused:
            raise
        except (ValueError, RuntimeError, ArithmeticError) as error:  # the adapter's own refusal: its type only, never its text
            raise BackfillRefused(
                "RESPONSE_SHAPE_REFUSED", f"{spec.venue.venue_id} {iso(first)}: the adapter refused the response ({type(error).__name__})"
            ) from None
        wanted = set(hours_between(first, last))
        for row in got:
            if row.get("timestamp") not in wanted:  # unreachable: the adapter keeps the requested hours only
                raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"{spec.venue.venue_id} {iso(first)}: a candle outside the requested hours")
            for name in VALUE_FIELDS:
                if not fits_raw_numeric(row[name]):
                    raise BackfillRefused(
                        "RESPONSE_SHAPE_REFUSED",
                        f"{spec.venue.venue_id} {iso(row['timestamp'])}: its {name} is not a value raw.btc_ohlcv holds exactly",
                    )
        rows.extend(got)
    returned = tuple(sorted(row["timestamp"] for row in rows))
    if len(set(returned)) != len(returned):  # unreachable: the runs are disjoint and the adapter keys rows by hour
        raise BackfillRefused("DUPLICATE_PROVIDER_RECORD", f"{spec.venue.venue_id}: an hour was returned twice")
    return MissingHoursRead(unit, spec.venue, spec.runs, tuple(sorted(rows, key=lambda row: row["timestamp"])), spec.hours(), returned)
