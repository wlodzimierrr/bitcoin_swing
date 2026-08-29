"""Bitfinex public 1h BTC/USD OHLCV provider."""

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


BITFINEX_PROVIDER_ID = "bitfinex"
BITFINEX_EXCHANGE = "bitfinex"
BITFINEX_BTC_USD_SYMBOL = "BTC/USD"
BITFINEX_BTC_USD_API_SYMBOL = "tBTCUSD"
BITFINEX_CANDLES_BASE_URL = "https://api-pub.bitfinex.com/v2"
BITFINEX_MAX_CANDLES_PER_REQUEST = 10_000
BITFINEX_HOUR_MILLISECONDS = 3_600_000

JsonRequester = Callable[[str], Any]


class BitfinexOhlcvProviderError(RuntimeError):
    """Raised when the Bitfinex public candle response is invalid."""


def _request_json(url: str) -> Any:
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "btc-predictor/1.0"},
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


@dataclass(frozen=True)
class BitfinexOhlcvProvider:
    """Fetch historical Bitfinex BTC/USD 1h candles in deterministic chunks."""

    provider_id: ClassVar[str] = BITFINEX_PROVIDER_ID
    request_json: JsonRequester = _request_json
    base_url: str = BITFINEX_CANDLES_BASE_URL
    api_symbol: str = BITFINEX_BTC_USD_API_SYMBOL
    page_limit: int = BITFINEX_MAX_CANDLES_PER_REQUEST

    def __post_init__(self) -> None:
        if not 1 <= self.page_limit <= BITFINEX_MAX_CANDLES_PER_REQUEST:
            raise ValueError(
                "page_limit must be between 1 and "
                f"{BITFINEX_MAX_CANDLES_PER_REQUEST}",
            )
        if not self.base_url.strip():
            raise ValueError("base_url must be non-empty")
        if not self.api_symbol.startswith("t"):
            raise ValueError("Bitfinex trading-pair api_symbol must start with 't'")

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
        if window_end < window_start:
            raise ValueError("end must be >= start")
        if exchange != BITFINEX_EXCHANGE:
            raise ValueError(f"exchange must be {BITFINEX_EXCHANGE!r}")
        if symbol != BITFINEX_BTC_USD_SYMBOL:
            raise ValueError(f"symbol must be {BITFINEX_BTC_USD_SYMBOL!r}")
        if timeframe != "1h":
            raise ValueError("Bitfinex BTC/USD provider supports timeframe='1h'")
        _require_hour_boundary(window_start, "start")
        _require_hour_boundary(window_end, "end")

        start_ms = _unix_milliseconds(window_start)
        end_ms = _unix_milliseconds(window_end)
        rows_by_timestamp: dict[datetime, Mapping[str, Any]] = {}
        cursor_ms = start_ms
        while cursor_ms <= end_ms:
            chunk_end_ms = min(
                end_ms,
                cursor_ms + (self.page_limit - 1) * BITFINEX_HOUR_MILLISECONDS,
            )
            payload = self.request_json(
                self._request_url(
                    start_ms=cursor_ms,
                    end_ms=chunk_end_ms + BITFINEX_HOUR_MILLISECONDS - 1,
                ),
            )
            for row in _normalize_payload(payload):
                timestamp = row["timestamp"]
                if not window_start <= timestamp <= window_end:
                    continue
                existing = rows_by_timestamp.get(timestamp)
                if existing is not None and existing != row:
                    raise BitfinexOhlcvProviderError(
                        "conflicting duplicate Bitfinex candle at "
                        f"{timestamp.isoformat()}",
                    )
                rows_by_timestamp.setdefault(timestamp, row)
            cursor_ms = chunk_end_ms + BITFINEX_HOUR_MILLISECONDS

        return tuple(
            rows_by_timestamp[timestamp]
            for timestamp in sorted(rows_by_timestamp)
        )

    def _request_url(self, *, start_ms: int, end_ms: int) -> str:
        query = urlencode(
            {
                "start": start_ms,
                "end": end_ms,
                "limit": self.page_limit,
                "sort": 1,
            },
        )
        return (
            f"{self.base_url.rstrip('/')}/candles/"
            f"trade:1h:{self.api_symbol}/hist?{query}"
        )


def _normalize_payload(payload: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(payload, list):
        raise BitfinexOhlcvProviderError("Bitfinex candle response must be a list")
    normalized = []
    for raw_row in payload:
        if not isinstance(raw_row, list) or len(raw_row) < 6:
            raise BitfinexOhlcvProviderError(
                "Bitfinex candle row must contain MTS/O/C/H/L/V",
            )
        try:
            timestamp = datetime.fromtimestamp(int(raw_row[0]) / 1000, tz=UTC)
        except (TypeError, ValueError, ArithmeticError, OverflowError) as exc:
            raise BitfinexOhlcvProviderError(
                "Bitfinex candle timestamp is invalid",
            ) from exc
        if timestamp.minute or timestamp.second or timestamp.microsecond:
            raise BitfinexOhlcvProviderError(
                "Bitfinex candle timestamp must be aligned to an hourly UTC boundary",
            )
        try:
            row = {
                "timestamp": timestamp,
                "open": Decimal(str(raw_row[1])),
                "close": Decimal(str(raw_row[2])),
                "high": Decimal(str(raw_row[3])),
                "low": Decimal(str(raw_row[4])),
                "volume": Decimal(str(raw_row[5])),
            }
        except (TypeError, ValueError, ArithmeticError) as exc:
            raise BitfinexOhlcvProviderError(
                "Bitfinex candle row contains invalid values",
            ) from exc
        _validate_row(row)
        normalized.append(row)
    return tuple(sorted(normalized, key=lambda row: row["timestamp"]))


def _validate_row(row: Mapping[str, Any]) -> None:
    open_price = row["open"]
    close_price = row["close"]
    high = row["high"]
    low = row["low"]
    volume = row["volume"]
    if any(value <= 0 for value in (open_price, close_price, high, low)):
        raise BitfinexOhlcvProviderError("Bitfinex OHLC values must be positive")
    if high < max(open_price, close_price) or low > min(open_price, close_price):
        raise BitfinexOhlcvProviderError("Bitfinex candle has impossible OHLC ordering")
    if high < low:
        raise BitfinexOhlcvProviderError("Bitfinex candle high must be >= low")
    if volume < 0:
        raise BitfinexOhlcvProviderError("Bitfinex candle volume must be non-negative")


def _unix_milliseconds(value: datetime) -> int:
    return int(require_utc_datetime(value, "timestamp").timestamp() * 1000)


def _require_hour_boundary(value: datetime, name: str) -> None:
    if value.minute or value.second or value.microsecond:
        raise ValueError(f"{name} must be aligned to an hourly UTC boundary")
