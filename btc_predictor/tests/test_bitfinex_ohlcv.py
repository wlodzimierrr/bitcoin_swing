from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

import pytest

from btc_predictor.data import (
    BITFINEX_BTC_USD_SYMBOL,
    BITFINEX_EXCHANGE,
    BITFINEX_PROVIDER_ID,
    BitfinexOhlcvProvider,
    BitfinexOhlcvProviderError,
    OhlcvCollectionRequest,
    collect_btc_ohlcv,
)


def candle(timestamp: datetime, *, close: str = "100") -> list[object]:
    return [
        int(timestamp.timestamp() * 1000),
        "100",
        close,
        "101",
        "99",
        "12.5",
    ]


class RecordingRequester:
    def __init__(
        self,
        candles_by_timestamp: dict[int, list[object]],
        *,
        duplicate_timestamp: int | None = None,
    ) -> None:
        self.candles_by_timestamp = candles_by_timestamp
        self.duplicate_timestamp = duplicate_timestamp
        self.urls: list[str] = []

    def __call__(self, url: str):
        self.urls.append(url)
        query = parse_qs(urlsplit(url).query)
        start_ms = int(query["start"][0])
        end_ms = int(query["end"][0])
        rows = [
            row
            for timestamp, row in self.candles_by_timestamp.items()
            if start_ms <= timestamp <= end_ms
        ]
        if (
            self.duplicate_timestamp is not None
            and start_ms <= self.duplicate_timestamp <= end_ms
        ):
            rows.append(self.candles_by_timestamp[self.duplicate_timestamp])
        return list(reversed(rows))


class RecordingConnection:
    def __init__(self) -> None:
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)


def test_bitfinex_provider_pages_and_orders_hourly_history() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    timestamps = tuple(start + timedelta(hours=offset) for offset in range(5))
    requester = RecordingRequester(
        {
            int(timestamp.timestamp() * 1000): candle(timestamp)
            for timestamp in timestamps
        },
        duplicate_timestamp=int(timestamps[1].timestamp() * 1000),
    )
    provider = BitfinexOhlcvProvider(request_json=requester, page_limit=2)

    rows = provider.fetch_ohlcv(
        exchange=BITFINEX_EXCHANGE,
        symbol=BITFINEX_BTC_USD_SYMBOL,
        timeframe="1h",
        start=start,
        end=timestamps[-1],
    )

    assert len(requester.urls) == 3
    assert all("/candles/trade:1h:tBTCUSD/hist?" in url for url in requester.urls)
    assert all(parse_qs(urlsplit(url).query)["sort"] == ["1"] for url in requester.urls)
    request_windows = [
        (
            int(parse_qs(urlsplit(url).query)["start"][0]),
            int(parse_qs(urlsplit(url).query)["end"][0]),
        )
        for url in requester.urls
    ]
    assert all(end_ms > start_ms for start_ms, end_ms in request_windows)
    assert [row["timestamp"] for row in rows] == list(timestamps)
    assert all(row["timestamp"].tzinfo is UTC for row in rows)
    assert rows[0]["close"] == Decimal("100")


def test_bitfinex_provider_integrates_with_collector_gap_and_provenance() -> None:
    start = datetime(2024, 2, 1, tzinfo=UTC)
    end = start + timedelta(hours=3)
    requester = RecordingRequester(
        {
            int(timestamp.timestamp() * 1000): candle(timestamp)
            for timestamp in (
                start,
                start + timedelta(hours=1),
                start + timedelta(hours=3),
            )
        },
    )
    provider = BitfinexOhlcvProvider(request_json=requester, page_limit=2)
    connection = RecordingConnection()
    request = OhlcvCollectionRequest(
        exchange=BITFINEX_EXCHANGE,
        symbol=BITFINEX_BTC_USD_SYMBOL,
        provider=BITFINEX_PROVIDER_ID,
        start=start,
        end=end,
        derived_timeframes=(),
    )

    result = collect_btc_ohlcv(
        provider,
        connection,
        request,
        ingested_at=end + timedelta(hours=1),
    )

    assert result.missing_source_timestamps == (start + timedelta(hours=2),)
    assert [bar.timestamp for bar in result.raw_bars] == [
        start,
        start + timedelta(hours=1),
        start + timedelta(hours=3),
    ]
    assert all(bar.provider == BITFINEX_PROVIDER_ID for bar in result.raw_bars)
    assert all(bar.exchange == BITFINEX_EXCHANGE for bar in result.raw_bars)
    assert all(bar.symbol == BITFINEX_BTC_USD_SYMBOL for bar in result.raw_bars)
    assert len(connection.statements) == 1


def test_bitfinex_provider_rejects_conflicting_duplicates_and_bad_requests() -> None:
    start = datetime(2024, 3, 1, tzinfo=UTC)
    duplicate_ms = int(start.timestamp() * 1000)

    def conflicting_response(url: str):
        return [candle(start), candle(start, close="100.5")]

    provider = BitfinexOhlcvProvider(request_json=conflicting_response)
    with pytest.raises(BitfinexOhlcvProviderError, match="conflicting duplicate"):
        provider.fetch_ohlcv(
            exchange=BITFINEX_EXCHANGE,
            symbol=BITFINEX_BTC_USD_SYMBOL,
            timeframe="1h",
            start=start,
            end=start,
        )

    assert duplicate_ms == candle(start)[0]
    with pytest.raises(ValueError, match="timeframe='1h'"):
        provider.fetch_ohlcv(
            exchange=BITFINEX_EXCHANGE,
            symbol=BITFINEX_BTC_USD_SYMBOL,
            timeframe="1d",
            start=start,
            end=start,
        )
    with pytest.raises(ValueError, match="must be UTC"):
        provider.fetch_ohlcv(
            exchange=BITFINEX_EXCHANGE,
            symbol=BITFINEX_BTC_USD_SYMBOL,
            timeframe="1h",
            start=start.astimezone(timezone(timedelta(hours=1))),
            end=start.astimezone(timezone(timedelta(hours=1))),
        )


def test_bitfinex_provider_rejects_misaligned_candles_and_provenance_relabeling() -> None:
    start = datetime(2024, 4, 1, tzinfo=UTC)
    misaligned = start + timedelta(minutes=30)
    provider = BitfinexOhlcvProvider(request_json=lambda url: [candle(misaligned)])

    with pytest.raises(BitfinexOhlcvProviderError, match="hourly UTC boundary"):
        provider.fetch_ohlcv(
            exchange=BITFINEX_EXCHANGE,
            symbol=BITFINEX_BTC_USD_SYMBOL,
            timeframe="1h",
            start=start,
            end=start,
        )

    with pytest.raises(ValueError, match="declared provider_id"):
        collect_btc_ohlcv(
            BitfinexOhlcvProvider(request_json=lambda url: []),
            RecordingConnection(),
            OhlcvCollectionRequest(
                exchange=BITFINEX_EXCHANGE,
                symbol=BITFINEX_BTC_USD_SYMBOL,
                provider="not_bitfinex",
                start=start,
                end=start,
                derived_timeframes=(),
            ),
            ingested_at=start + timedelta(hours=1),
        )


def test_bitfinex_provider_supports_a_single_candle_window() -> None:
    timestamp = datetime(2024, 5, 1, tzinfo=UTC)
    requester = RecordingRequester(
        {int(timestamp.timestamp() * 1000): candle(timestamp)},
    )

    rows = BitfinexOhlcvProvider(request_json=requester).fetch_ohlcv(
        exchange=BITFINEX_EXCHANGE,
        symbol=BITFINEX_BTC_USD_SYMBOL,
        timeframe="1h",
        start=timestamp,
        end=timestamp,
    )
    query = parse_qs(urlsplit(requester.urls[0]).query)

    assert len(rows) == 1
    assert int(query["end"][0]) - int(query["start"][0]) == 3_599_999
