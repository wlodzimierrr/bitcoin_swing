"""Synthetic provider responses for the RBT-003 Part A adapter tests.

Every response here is built in memory: no network, no database, no real-data
value. The shapes follow what RBT-002 recorded for each source (and, for the
unverified CoinGlass and Kraken chart endpoints, the documented examples), so
the tests show what the adapters accept and refuse, not that a live provider
answers this way.
"""

from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from btc_predictor.research_backtest import backfill_binance as binance
from btc_predictor.research_backtest.backfill_sources import Fetcher, RetrievalLog, TransportResponse, epoch_milliseconds


RETRIEVED_AT = datetime(2026, 11, 5, 10, 0, tzinfo=UTC)
HOUR = timedelta(hours=1)
DAY = timedelta(days=1)


def utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


class FakeTransport:
    """URL -> response; any other URL answers ``default_status`` with no body."""

    def __init__(self, responses: Mapping[str, TransportResponse] | None = None, *, default_status: int = 404) -> None:
        self.responses: dict[str, TransportResponse] = dict(responses or {})
        self.default_status = default_status
        self.calls: list[tuple[str, dict[str, str]]] = []

    def add(self, url: str, body: bytes, status: int = 200) -> None:
        self.responses[url] = TransportResponse(status, body)

    def __call__(self, url: str, headers: Mapping[str, str]) -> TransportResponse:
        self.calls.append((url, dict(headers)))
        return self.responses.get(url, TransportResponse(self.default_status, b""))

    @property
    def urls(self) -> list[str]:
        return [url for url, _ in self.calls]


def make_fetcher(transport: FakeTransport, **changes: Any) -> Fetcher:
    return Fetcher(transport, RetrievalLog(), lambda: RETRIEVED_AT, **changes)


# --- Binance archives ------------------------------------------------------------------------


def zip_bytes(name: str, rows: Iterable[Sequence[str]], *, extra: Mapping[str, str] | None = None) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0)), "".join(",".join(row) + "\n" for row in rows))
        for other, text in (extra or {}).items():
            archive.writestr(zipfile.ZipInfo(other, date_time=(2026, 1, 1, 0, 0, 0)), text)
    return buffer.getvalue()


def checksum(url: str, data: bytes) -> bytes:
    import hashlib

    return f"{hashlib.sha256(data).hexdigest()}  {url.rsplit('/', 1)[1]}\n".encode()


def add_archive(transport: FakeTransport, url: str, rows: Iterable[Sequence[str]], *, member: str | None = None) -> bytes:
    name = member or url.rsplit("/", 1)[1].replace(".zip", ".csv")
    data = zip_bytes(name, rows)
    transport.add(url, data)
    transport.add(f"{url}.CHECKSUM", checksum(url, data))
    return data


def ms(instant: datetime) -> str:
    return str(epoch_milliseconds(instant))


def funding_row(settled: datetime, rate: str = "0.0001", hours: str = "8") -> list[str]:
    return [ms(settled), hours, rate]


def metrics_row(instant: datetime, value: str = "1000000", symbol: str = "BTCUSDT") -> list[str]:
    return [instant.strftime("%Y-%m-%d %H:%M:%S"), symbol, "10", value, "1", "1", "1", "1"]


def kline_row(opened: datetime, close: Decimal | str, *, volume: str = "2", quote: str = "20000") -> list[str]:
    closed = opened + HOUR - timedelta(milliseconds=1)
    return [ms(opened), str(close), str(close), str(close), str(close), volume, ms(closed), quote, "5", "1", "1", "0"]


def hourly(start: datetime, end: datetime) -> list[datetime]:
    out, cursor = [], start
    while cursor < end:
        out.append(cursor)
        cursor += HOUR
    return out


def month_of(instant: datetime) -> date:
    return date(instant.year, instant.month, 1)


def add_contract(
    transport: FakeTransport,
    contract: str,
    first_open: datetime,
    last_open: datetime,
    close_at: Any = lambda t: Decimal("10010"),
) -> None:
    """A contract's monthly archives holding every hour from ``first_open`` to ``last_open``."""

    by_month: dict[date, list[list[str]]] = {}
    for opened in hourly(first_open, last_open + HOUR):
        by_month.setdefault(month_of(opened), []).append(kline_row(opened, close_at(opened)))
    for month, rows in by_month.items():
        add_archive(transport, binance.coinm_klines_archive_url(contract, month), rows)


def add_index(transport: FakeTransport, first_open: datetime, last_open: datetime, close_at: Any = lambda t: Decimal("10000")) -> None:
    by_month: dict[date, list[list[str]]] = {}
    for opened in hourly(first_open, last_open + HOUR):
        by_month.setdefault(month_of(opened), []).append(kline_row(opened, close_at(opened)))
    for month, rows in by_month.items():
        add_archive(transport, binance.coinm_index_archive_url(month), rows)


def s3_listing(names: Iterable[str], *, prefix: str = binance.COINM_KLINES_PREFIX, marker: str | None = None) -> bytes:
    prefixes = "".join(f"<CommonPrefixes><Prefix>{prefix}{name}/</Prefix></CommonPrefixes>" for name in names)
    truncated = "true" if marker else "false"
    next_marker = f"<NextMarker>{marker}</NextMarker>" if marker else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        f"<Name>data.binance.vision</Name><Prefix>{prefix}</Prefix><Delimiter>/</Delimiter>"
        f"<IsTruncated>{truncated}</IsTruncated>{next_marker}{prefixes}</ListBucketResult>"
    ).encode()


# --- Kraken ----------------------------------------------------------------------------------


def execution(uid: str, at: datetime, quantity: Any = "100", *, order_type: str = "Limit", direction: str = "Buy") -> dict[str, Any]:
    return {
        "uid": f"element-{uid}",
        "timestamp": epoch_milliseconds(at),
        "event": {
            "Execution": {
                "execution": {
                    "uid": uid,
                    "timestamp": epoch_milliseconds(at),
                    "price": "30000",
                    "quantity": quantity,
                    "usdValue": "0",
                    "markPrice": "30000",
                    "limitFilled": False,
                    "takerOrder": {"uid": f"taker-{uid}", "orderType": order_type, "direction": direction},
                    "makerOrder": {"uid": f"maker-{uid}", "orderType": "Limit", "direction": "Sell" if direction == "Buy" else "Buy"},
                }
            }
        },
    }


def execution_page(elements: Sequence[Mapping[str, Any]], token: str | None = None) -> bytes:
    payload: dict[str, Any] = {"elements": list(elements), "len": len(elements)}
    if token is not None:
        payload["continuationToken"] = token
    return json.dumps(payload, separators=(",", ":")).encode()


def series_body(
    points: Mapping[datetime, Any], *, more: bool = False, errors: Sequence[Any] = (), quoted: bool = True
) -> bytes:
    """Kraken's hourly liquidation-volume chart; values are JSON strings, as the live series spells them."""

    hours = sorted(points)
    stamps = ",".join(str(int(hour.timestamp())) for hour in hours)
    values = ",".join((f'"{points[hour]}"' if quoted else str(points[hour])) for hour in hours)
    tail = "true" if more else "false"
    return (
        '{"result":{"timestamp":[%s],"data":[%s],"more":%s},"errors":%s}'
        % (stamps, values, tail, json.dumps(list(errors), separators=(",", ":")))
    ).encode()


# --- Coin Metrics and CoinGlass --------------------------------------------------------------


def coinmetrics_page(
    rows: Iterable[tuple[date, str]],
    *,
    next_url: str | None = None,
    token: str | None = "token",
    extra: Mapping[str, Any] | None = None,
) -> bytes:
    payload: dict[str, Any] = {
        "data": [
            {"asset": "btc", "time": f"{day.isoformat()}T00:00:00.000000000Z", "CapMrktCurUSD": value, **(extra or {})}
            for day, value in rows
        ]
    }
    if next_url is not None:
        payload["next_page_url"] = next_url
        if token is not None:
            payload["next_page_token"] = token
    return json.dumps(payload).encode()


def coinglass_flow_page(days: Mapping[date, Mapping[str, Any]], *, code: str = "0") -> bytes:
    data = [
        {
            "timestamp": epoch_milliseconds(datetime(day.year, day.month, day.day, tzinfo=UTC)),
            "flow_usd": 0,
            "price_usd": 45000,
            "etf_flows": [{"etf_ticker": ticker, "flow_usd": flow} for ticker, flow in flows.items()],
        }
        for day, flows in sorted(days.items())
    ]
    return json.dumps({"code": code, "msg": "success", "data": data}).encode()


def coinglass_fund_page(assets: Mapping[date, Any]) -> bytes:
    data = [
        {
            "assets_date": epoch_milliseconds(datetime(day.year, day.month, day.day, tzinfo=UTC)),
            "btc_holdings": 1000,
            "net_assets_usd": value,
        }
        for day, value in sorted(assets.items())
    ]
    return json.dumps({"code": "0", "msg": "success", "data": data}).encode()
