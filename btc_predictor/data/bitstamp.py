"""Bitstamp public 1h BTC/USD OHLCV provider."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, ClassVar
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from btc_predictor.data.ohlcv import require_utc_datetime


BITSTAMP_PROVIDER_ID = "bitstamp"
BITSTAMP_EXCHANGE = "bitstamp"
BITSTAMP_BTC_USD_SYMBOL = "BTC/USD"
BITSTAMP_BTC_USD_API_SYMBOL = "btcusd"
BITSTAMP_OHLC_BASE_URL = "https://www.bitstamp.net/api/v2/ohlc"
BITSTAMP_MAX_CANDLES_PER_REQUEST = 1_000
BITSTAMP_HOUR_SECONDS = 3_600

JsonRequester = Callable[[str], Any]


class BitstampOhlcvProviderError(RuntimeError):
    """Raised when a Bitstamp public candle response is invalid."""


def _request_json(url: str) -> Any:
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "btc-predictor/1.0"},
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


@dataclass(frozen=True)
class BitstampOhlcvProvider:
    """Fetch historical Bitstamp BTC/USD 1h candles in deterministic chunks."""

    provider_id: ClassVar[str] = BITSTAMP_PROVIDER_ID
    request_json: JsonRequester = _request_json
    base_url: str = BITSTAMP_OHLC_BASE_URL
    api_symbol: str = BITSTAMP_BTC_USD_API_SYMBOL
    page_limit: int = BITSTAMP_MAX_CANDLES_PER_REQUEST

    def __post_init__(self) -> None:
        if not 1 <= self.page_limit <= BITSTAMP_MAX_CANDLES_PER_REQUEST:
            raise ValueError(
                "page_limit must be between 1 and "
                f"{BITSTAMP_MAX_CANDLES_PER_REQUEST}",
            )
        if not self.base_url.strip():
            raise ValueError("base_url must be non-empty")
        if not self.api_symbol.strip():
            raise ValueError("api_symbol must be non-empty")

    def fetch_ohlcv(
        self,
        *,
        exchange: str,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> tuple[Mapping[str, Any], ...]:
        window_start = require_utc_datetime(start, "start")
        window_end = require_utc_datetime(end, "end")
        _validate_request(exchange, symbol, timeframe, window_start, window_end)

        rows_by_timestamp: dict[datetime, Mapping[str, Any]] = {}
        cursor_seconds = int(window_start.timestamp())
        end_seconds = int(window_end.timestamp())
        while cursor_seconds <= end_seconds:
            chunk_end_seconds = min(
                end_seconds,
                cursor_seconds + (self.page_limit - 1) * BITSTAMP_HOUR_SECONDS,
            )
            payload = self.request_json(
                self._request_url(
                    start_seconds=cursor_seconds,
                    end_seconds=chunk_end_seconds,
                ),
            )
            for row in _normalize_payload(payload):
                timestamp = row["timestamp"]
                if not window_start <= timestamp <= window_end:
                    continue
                _add_row(rows_by_timestamp, row)
            cursor_seconds = chunk_end_seconds + BITSTAMP_HOUR_SECONDS

        return tuple(
            rows_by_timestamp[timestamp]
            for timestamp in sorted(rows_by_timestamp)
        )

    def _request_url(self, *, start_seconds: int, end_seconds: int) -> str:
        query = urlencode(
            {
                "step": BITSTAMP_HOUR_SECONDS,
                "limit": self.page_limit,
                "start": start_seconds,
                "end": end_seconds,
                "exclude_current_candle": "true",
            },
        )
        return f"{self.base_url.rstrip('/')}/{self.api_symbol}/?{query}"


def _normalize_payload(payload: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(payload, dict):
        raise BitstampOhlcvProviderError("Bitstamp candle response must be an object")
    try:
        raw_rows = payload["data"]["ohlc"]
    except (KeyError, TypeError) as exc:
        raise BitstampOhlcvProviderError(
            "Bitstamp candle response is missing data.ohlc",
        ) from exc
    if not isinstance(raw_rows, list):
        raise BitstampOhlcvProviderError("Bitstamp data.ohlc must be a list")

    normalized = []
    for raw_row in raw_rows:
        if not isinstance(raw_row, dict):
            raise BitstampOhlcvProviderError("Bitstamp candle row must be an object")
        try:
            timestamp = datetime.fromtimestamp(int(raw_row["timestamp"]), tz=UTC)
            row = {
                "timestamp": timestamp,
                "open": Decimal(str(raw_row["open"])),
                "high": Decimal(str(raw_row["high"])),
                "low": Decimal(str(raw_row["low"])),
                "close": Decimal(str(raw_row["close"])),
                "volume": Decimal(str(raw_row["volume"])),
            }
        except (KeyError, TypeError, ValueError, ArithmeticError, OverflowError) as exc:
            raise BitstampOhlcvProviderError(
                "Bitstamp candle row contains invalid values",
            ) from exc
        _validate_row(row)
        normalized.append(row)
    return tuple(sorted(normalized, key=lambda row: row["timestamp"]))


def _validate_request(
    exchange: str,
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
) -> None:
    if end < start:
        raise ValueError("end must be >= start")
    if exchange != BITSTAMP_EXCHANGE:
        raise ValueError(f"exchange must be {BITSTAMP_EXCHANGE!r}")
    if symbol != BITSTAMP_BTC_USD_SYMBOL:
        raise ValueError(f"symbol must be {BITSTAMP_BTC_USD_SYMBOL!r}")
    if timeframe != "1h":
        raise ValueError("Bitstamp BTC/USD provider supports timeframe='1h'")
    _require_hour_boundary(start, "start")
    _require_hour_boundary(end, "end")


def _validate_row(row: Mapping[str, Any]) -> None:
    _require_hour_boundary(row["timestamp"], "Bitstamp candle timestamp")
    prices = (row["open"], row["high"], row["low"], row["close"])
    if any(value <= 0 for value in prices):
        raise BitstampOhlcvProviderError("Bitstamp OHLC values must be positive")
    if row["high"] < max(row["open"], row["close"]):
        raise BitstampOhlcvProviderError("Bitstamp candle has impossible OHLC ordering")
    if row["low"] > min(row["open"], row["close"]):
        raise BitstampOhlcvProviderError("Bitstamp candle has impossible OHLC ordering")
    if row["high"] < row["low"]:
        raise BitstampOhlcvProviderError("Bitstamp candle high must be >= low")
    if row["volume"] < 0:
        raise BitstampOhlcvProviderError("Bitstamp candle volume must be non-negative")


def _add_row(
    rows_by_timestamp: dict[datetime, Mapping[str, Any]],
    row: Mapping[str, Any],
) -> None:
    timestamp = row["timestamp"]
    existing = rows_by_timestamp.get(timestamp)
    if existing is not None and existing != row:
        raise BitstampOhlcvProviderError(
            f"conflicting duplicate Bitstamp candle at {timestamp.isoformat()}",
        )
    rows_by_timestamp.setdefault(timestamp, row)


def _require_hour_boundary(value: datetime, name: str) -> None:
    if value.minute or value.second or value.microsecond:
        raise ValueError(f"{name} must be aligned to an hourly UTC boundary")
