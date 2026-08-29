from datetime import UTC, datetime, timedelta
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

import pytest

from btc_predictor.data import (
    BITSTAMP_BTC_USD_SYMBOL,
    BITSTAMP_EXCHANGE,
    BITSTAMP_PROVIDER_ID,
    BitstampOhlcvProvider,
    BitstampOhlcvProviderError,
    OhlcvCollectionRequest,
    collect_btc_ohlcv,
)


def candle(timestamp: datetime, *, close: str = "100") -> dict[str, str]:
    return {
        "timestamp": str(int(timestamp.timestamp())),
        "open": "100",
        "high": "101",
        "low": "99",
        "close": close,
        "volume": "12.5",
    }


class RecordingRequester:
    def __init__(self, candles: dict[int, dict[str, str]]) -> None:
        self.candles = candles
        self.urls: list[str] = []

    def __call__(self, url: str):
        self.urls.append(url)
        query = parse_qs(urlsplit(url).query)
        start = int(query["start"][0])
        end = int(query["end"][0])
        rows = [row for timestamp, row in self.candles.items() if start <= timestamp <= end]
        return {"data": {"ohlc": list(reversed(rows))}}


class RecordingConnection:
    def __init__(self) -> None:
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)


def test_bitstamp_provider_pages_orders_and_integrates_with_collector() -> None:
    start = datetime(2023, 1, 1, tzinfo=UTC)
    timestamps = tuple(start + timedelta(hours=offset) for offset in range(5))
    requester = RecordingRequester(
        {int(timestamp.timestamp()): candle(timestamp) for timestamp in timestamps},
    )
    provider = BitstampOhlcvProvider(request_json=requester, page_limit=2)

    rows = provider.fetch_ohlcv(
        exchange=BITSTAMP_EXCHANGE,
        symbol=BITSTAMP_BTC_USD_SYMBOL,
        timeframe="1h",
        start=start,
        end=timestamps[-1],
    )

    assert len(requester.urls) == 3
    assert all("/ohlc/btcusd/?" in url for url in requester.urls)
    assert all(parse_qs(urlsplit(url).query)["step"] == ["3600"] for url in requester.urls)
    assert [row["timestamp"] for row in rows] == list(timestamps)
    assert rows[0]["close"] == Decimal("100")

    connection = RecordingConnection()
    result = collect_btc_ohlcv(
        provider,
        connection,
        OhlcvCollectionRequest(
            exchange=BITSTAMP_EXCHANGE,
            symbol=BITSTAMP_BTC_USD_SYMBOL,
            provider=BITSTAMP_PROVIDER_ID,
            start=start,
            end=timestamps[-1],
            derived_timeframes=(),
        ),
        ingested_at=timestamps[-1] + timedelta(hours=1),
    )

    assert len(result.raw_bars) == 5
    assert all(bar.provider == BITSTAMP_PROVIDER_ID for bar in result.raw_bars)
    assert result.missing_source_timestamps == ()
    assert len(connection.statements) == 1


def test_bitstamp_provider_rejects_conflicting_duplicates() -> None:
    timestamp = datetime(2023, 2, 1, tzinfo=UTC)
    provider = BitstampOhlcvProvider(
        request_json=lambda url: {
            "data": {"ohlc": [candle(timestamp), candle(timestamp, close="100.5")]},
        },
    )

    with pytest.raises(BitstampOhlcvProviderError, match="conflicting duplicate"):
        provider.fetch_ohlcv(
            exchange=BITSTAMP_EXCHANGE,
            symbol=BITSTAMP_BTC_USD_SYMBOL,
            timeframe="1h",
            start=timestamp,
            end=timestamp,
        )
