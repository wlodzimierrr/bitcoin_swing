"""Coinbase Exchange public 1h BTC-USD OHLCV provider."""

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


COINBASE_PROVIDER_ID = "coinbase"
COINBASE_EXCHANGE = "coinbase"
COINBASE_BTC_USD_SYMBOL = "BTC-USD"
COINBASE_BTC_USD_API_SYMBOL = "BTC-USD"
COINBASE_CANDLES_BASE_URL = "https://api.exchange.coinbase.com/products"
COINBASE_MAX_CANDLES_PER_REQUEST = 300
COINBASE_HOUR_SECONDS = 3_600

JsonRequester = Callable[[str], Any]


class CoinbaseOhlcvProviderError(RuntimeError):
    """Raised when a Coinbase Exchange candle response is invalid."""


def _request_json(url: str) -> Any:
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "btc-predictor/1.0"},
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


@dataclass(frozen=True)
class CoinbaseOhlcvProvider:
    """Fetch historical Coinbase BTC-USD 1h candles in deterministic chunks."""

    provider_id: ClassVar[str] = COINBASE_PROVIDER_ID
    request_json: JsonRequester = _request_json
    base_url: str = COINBASE_CANDLES_BASE_URL
    api_symbol: str = COINBASE_BTC_USD_API_SYMBOL
    page_limit: int = COINBASE_MAX_CANDLES_PER_REQUEST

    def __post_init__(self) -> None:
        if not 1 <= self.page_limit <= COINBASE_MAX_CANDLES_PER_REQUEST:
            raise ValueError(
                "page_limit must be between 1 and "
                f"{COINBASE_MAX_CANDLES_PER_REQUEST}",
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
                cursor_seconds + (self.page_limit - 1) * COINBASE_HOUR_SECONDS,
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
            cursor_seconds = chunk_end_seconds + COINBASE_HOUR_SECONDS

        return tuple(
            rows_by_timestamp[timestamp]
            for timestamp in sorted(rows_by_timestamp)
        )

    def _request_url(self, *, start_seconds: int, end_seconds: int) -> str:
        query = urlencode(
            {
                "granularity": COINBASE_HOUR_SECONDS,
                "start": _iso_utc(start_seconds),
                "end": _iso_utc(end_seconds),
            },
        )
        return f"{self.base_url.rstrip('/')}/{self.api_symbol}/candles?{query}"


def _normalize_payload(payload: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(payload, list):
        raise CoinbaseOhlcvProviderError("Coinbase candle response must be a list")
    normalized = []
    for raw_row in payload:
        if not isinstance(raw_row, list) or len(raw_row) < 6:
            raise CoinbaseOhlcvProviderError(
                "Coinbase candle row must contain time/low/high/open/close/volume",
            )
        try:
            timestamp = datetime.fromtimestamp(int(raw_row[0]), tz=UTC)
            row = {
                "timestamp": timestamp,
                "low": Decimal(str(raw_row[1])),
                "high": Decimal(str(raw_row[2])),
                "open": Decimal(str(raw_row[3])),
                "close": Decimal(str(raw_row[4])),
                "volume": Decimal(str(raw_row[5])),
            }
        except (TypeError, ValueError, ArithmeticError, OverflowError) as exc:
            raise CoinbaseOhlcvProviderError(
                "Coinbase candle row contains invalid values",
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
    if exchange != COINBASE_EXCHANGE:
        raise ValueError(f"exchange must be {COINBASE_EXCHANGE!r}")
    if symbol != COINBASE_BTC_USD_SYMBOL:
        raise ValueError(f"symbol must be {COINBASE_BTC_USD_SYMBOL!r}")
    if timeframe != "1h":
        raise ValueError("Coinbase BTC-USD provider supports timeframe='1h'")
    _require_hour_boundary(start, "start")
    _require_hour_boundary(end, "end")


def _validate_row(row: Mapping[str, Any]) -> None:
    _require_hour_boundary(row["timestamp"], "Coinbase candle timestamp")
    prices = (row["open"], row["high"], row["low"], row["close"])
    if any(value <= 0 for value in prices):
        raise CoinbaseOhlcvProviderError("Coinbase OHLC values must be positive")
    if row["high"] < max(row["open"], row["close"]):
        raise CoinbaseOhlcvProviderError("Coinbase candle has impossible OHLC ordering")
    if row["low"] > min(row["open"], row["close"]):
        raise CoinbaseOhlcvProviderError("Coinbase candle has impossible OHLC ordering")
    if row["high"] < row["low"]:
        raise CoinbaseOhlcvProviderError("Coinbase candle high must be >= low")
    if row["volume"] < 0:
        raise CoinbaseOhlcvProviderError("Coinbase candle volume must be non-negative")


def _add_row(
    rows_by_timestamp: dict[datetime, Mapping[str, Any]],
    row: Mapping[str, Any],
) -> None:
    timestamp = row["timestamp"]
    existing = rows_by_timestamp.get(timestamp)
    if existing is not None and existing != row:
        raise CoinbaseOhlcvProviderError(
            f"conflicting duplicate Coinbase candle at {timestamp.isoformat()}",
        )
    rows_by_timestamp.setdefault(timestamp, row)


def _iso_utc(timestamp_seconds: int) -> str:
    return datetime.fromtimestamp(timestamp_seconds, tz=UTC).strftime(
        "%Y-%m-%dT%H:%M:%SZ",
    )


def _require_hour_boundary(value: datetime, name: str) -> None:
    if value.minute or value.second or value.microsecond:
        raise ValueError(f"{name} must be aligned to an hourly UTC boundary")
