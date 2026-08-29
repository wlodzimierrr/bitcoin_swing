from datetime import UTC, datetime, timedelta
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

import pytest

from btc_predictor.data import (
    COINBASE_BTC_USD_SYMBOL,
    COINBASE_EXCHANGE,
    COINBASE_PROVIDER_ID,
    CoinbaseOhlcvProvider,
    CoinbaseOhlcvProviderError,
    OhlcvCollectionRequest,
    collect_btc_ohlcv,
)


def candle(timestamp: datetime, *, close: str = "100") -> list[object]:
    return [
        int(timestamp.timestamp()),
        "99",
        "101",
        "100",
        close,
        "12.5",
    ]


class RecordingRequester:
    def __init__(self, candles: dict[int, list[object]]) -> None:
        self.candles = candles
        self.urls: list[str] = []

    def __call__(self, url: str):
        self.urls.append(url)
        query = parse_qs(urlsplit(url).query)
        start = int(datetime.fromisoformat(query["start"][0].replace("Z", "+00:00")).timestamp())
        end = int(datetime.fromisoformat(query["end"][0].replace("Z", "+00:00")).timestamp())
        return list(
            reversed(
                [row for timestamp, row in self.candles.items() if start <= timestamp <= end],
            ),
        )


class RecordingConnection:
    def __init__(self) -> None:
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)


def test_coinbase_provider_pages_orders_and_integrates_with_collector() -> None:
    start = datetime(2023, 1, 1, tzinfo=UTC)
    timestamps = tuple(start + timedelta(hours=offset) for offset in range(5))
    requester = RecordingRequester(
        {int(timestamp.timestamp()): candle(timestamp) for timestamp in timestamps},
    )
    provider = CoinbaseOhlcvProvider(request_json=requester, page_limit=2)

    rows = provider.fetch_ohlcv(
        exchange=COINBASE_EXCHANGE,
        symbol=COINBASE_BTC_USD_SYMBOL,
        timeframe="1h",
        start=start,
        end=timestamps[-1],
    )

    assert len(requester.urls) == 3
    assert all("/BTC-USD/candles?" in url for url in requester.urls)
    assert all(
        parse_qs(urlsplit(url).query)["granularity"] == ["3600"]
        for url in requester.urls
    )
    assert [row["timestamp"] for row in rows] == list(timestamps)
    assert rows[0]["close"] == Decimal("100")

    connection = RecordingConnection()
    result = collect_btc_ohlcv(
        provider,
        connection,
        OhlcvCollectionRequest(
            exchange=COINBASE_EXCHANGE,
            symbol=COINBASE_BTC_USD_SYMBOL,
            provider=COINBASE_PROVIDER_ID,
            start=start,
            end=timestamps[-1],
            derived_timeframes=(),
        ),
        ingested_at=timestamps[-1] + timedelta(hours=1),
    )

    assert len(result.raw_bars) == 5
    assert all(bar.provider == COINBASE_PROVIDER_ID for bar in result.raw_bars)
    assert result.missing_source_timestamps == ()
    assert len(connection.statements) == 1


def test_coinbase_provider_rejects_conflicting_duplicates() -> None:
    timestamp = datetime(2023, 2, 1, tzinfo=UTC)
    provider = CoinbaseOhlcvProvider(
        request_json=lambda url: [candle(timestamp), candle(timestamp, close="100.5")],
    )

    with pytest.raises(CoinbaseOhlcvProviderError, match="conflicting duplicate"):
        provider.fetch_ohlcv(
            exchange=COINBASE_EXCHANGE,
            symbol=COINBASE_BTC_USD_SYMBOL,
            timeframe="1h",
            start=timestamp,
            end=timestamp,
        )
