"""RBT-003 Part B owner ruling 15: the missing Coinbase and Bitfinex hours, re-requested.

Synthetic candle APIs only: no network (every socket is refused), no database
(a recording connection), and the evidence store is a temporary git work tree.
"""

from __future__ import annotations

import contextlib
import json
import socket
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy.dialects import postgresql

from btc_predictor.data import coinbase as coinbase_module
from btc_predictor.data import bitfinex as bitfinex_module
from btc_predictor.data.ohlcv import OhlcvCollectionRequest
from btc_predictor.research_backtest import backfill_ohlcv as ohlcv
from btc_predictor.research_backtest import backfill_persistence as persistence
from btc_predictor.research_backtest import backfill_run as run
from btc_predictor.research_backtest import backfill_transport as transport_module
from btc_predictor.research_backtest import replay_inputs as v1
from btc_predictor.research_backtest.backfill_sources import BackfillRefused, TransportResponse
from btc_predictor.tests.rbt003_backfill_fixtures import RETRIEVED_AT, make_fetcher

REPOSITORY = Path(__file__).resolve().parents[2]
PERSISTED_AT = RETRIEVED_AT + timedelta(minutes=5)
H = timedelta(hours=1)


@pytest.fixture(autouse=True)
def no_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("a test opened a socket")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def refused(reason: str, call: Any, *args: Any, **kwargs: Any) -> BackfillRefused:
    with pytest.raises(BackfillRefused) as caught:
        call(*args, **kwargs)
    assert caught.value.reason_code == reason, str(caught.value)
    return caught.value


def hour(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


COINBASE_HOURS = [
    "2020-01-30 17:00", "2020-09-04 23:00", "2020-10-20 20:00", "2023-03-04 18:00", "2023-03-04 19:00", "2023-03-04 20:00",
    "2025-10-25 16:00", "2025-10-25 17:00", "2025-10-25 18:00", "2025-10-25 19:00", "2025-10-25 20:00",
]
BITFINEX_HOURS = [
    "2020-02-11 11:00", "2020-02-11 12:00", "2020-08-12 21:00", "2021-06-30 08:00", "2021-06-30 09:00", "2021-10-13 14:00",
    "2021-10-13 15:00", "2021-10-13 16:00", "2022-10-12 08:00", "2022-10-12 09:00", "2022-10-12 10:00", "2022-10-12 11:00",
    "2023-03-06 10:00", "2023-03-06 11:00", "2024-05-05 10:00", "2024-05-05 11:00",
]


# --- synthetic candle APIs -------------------------------------------------------------------------

PRICES = {"open": 9350.5, "high": 9400.25, "low": 9300.125, "close": 9380.75, "volume": 123.4567}


def coinbase_row(at: datetime, **changes: Any) -> list[Any]:
    values = {**PRICES, **changes}
    return [int(at.timestamp()), values["low"], values["high"], values["open"], values["close"], values["volume"]]


def bitfinex_row(at: datetime, **changes: Any) -> list[Any]:
    values = {**PRICES, **changes}
    return [int(at.timestamp()) * 1000, values["open"], values["close"], values["high"], values["low"], values["volume"]]


class CandleApi:
    """Answers each adapter's own URL with the candles it holds inside the requested span."""

    def __init__(self, unit: str, hours: Any = (), *, extra: list[list[Any]] | None = None, body: bytes | None = None, status: int = 200) -> None:
        self.unit = unit
        self.row = coinbase_row if unit == "coinbase" else bitfinex_row
        self.rows = {at: self.row(at) for at in hours}
        self.extra = extra or []
        self.body = body
        self.status = status
        self.urls: list[str] = []

    def span(self, url: str) -> tuple[datetime, datetime]:
        query = {key: values[0] for key, values in parse_qs(urlsplit(url).query).items()}
        if self.unit == "coinbase":
            return tuple(datetime.fromisoformat(query[key].replace("Z", "+00:00")) for key in ("start", "end"))  # type: ignore[return-value]
        return tuple(datetime.fromtimestamp(int(query[key]) / 1000, tz=UTC) for key in ("start", "end"))  # type: ignore[return-value]

    def __call__(self, url: str, headers: Any) -> TransportResponse:
        self.urls.append(url)
        if self.body is not None or self.status != 200:
            return TransportResponse(self.status, self.body or b"")
        start, end = self.span(url)
        rows = [row for at, row in sorted(self.rows.items()) if start <= at <= end] + self.extra
        return TransportResponse(200, json.dumps(rows).encode())


def all_hours(unit: str) -> tuple[datetime, ...]:
    return ohlcv.MISSING_HOURS_VENUES[unit].hours()


# --- the schedule ----------------------------------------------------------------------------------


def test_ruling_15_the_schedule_is_rbt002s_census_of_missing_hours() -> None:
    assert [at.strftime("%Y-%m-%d %H:%M") for at in all_hours("coinbase")] == COINBASE_HOURS
    assert [at.strftime("%Y-%m-%d %H:%M") for at in all_hours("bitfinex")] == BITFINEX_HOURS
    assert (len(ohlcv.COINBASE_MISSING_RUNS), len(ohlcv.BITFINEX_MISSING_RUNS)) == (5, 7)
    assert ohlcv.MISSING_HOURS_VENUES["coinbase"].venue is v1.COINBASE_REPLAY_VENUE
    assert ohlcv.MISSING_HOURS_VENUES["bitfinex"].venue is v1.BITFINEX_REPLAY_VENUE
    assert run.SOURCES["ohlcv-missing-hours"].units() == ("bitfinex", "coinbase")
    assert run.SOURCES["ohlcv-missing-hours"].table == "btc_ohlcv"
    for unit in ("coinbase", "bitfinex"):
        for first, last in ohlcv.MISSING_HOURS_VENUES[unit].runs:
            assert v1.DATA_WINDOW.start <= first <= last < v1.DATA_WINDOW.end
            assert (first.minute, first.second, last.minute, last.second) == (0, 0, 0, 0)


@pytest.mark.parametrize("unit", ["coinbase", "bitfinex"])
def test_each_run_is_one_adapter_request_inside_the_window(unit: str) -> None:
    api = CandleApi(unit, all_hours(unit))
    read = ohlcv.read_missing_hours(make_fetcher(api), unit)  # type: ignore[arg-type]
    runs = ohlcv.MISSING_HOURS_VENUES[unit].runs
    assert len(api.urls) == len(runs)
    host = "api.exchange.coinbase.com" if unit == "coinbase" else "api-pub.bitfinex.com"
    for url, (first, last) in zip(api.urls, runs):
        assert urlsplit(url).hostname == host
        start, end = api.span(url)
        assert start == first and last <= end < last + H  # Bitfinex asks to the run's last hour's final millisecond
        assert v1.DATA_WINDOW.start <= start and end < v1.DATA_WINDOW.end
    assert read.returned == read.requested == all_hours(unit) and read.still_missing == ()


@pytest.mark.parametrize("unit", ["coinbase", "bitfinex"])
def test_the_adapters_default_requester_is_never_used(unit: str, monkeypatch: pytest.MonkeyPatch) -> None:
    def no_default(url: str) -> Any:
        raise AssertionError("the BTC-020 adapter's own network requester was used")

    monkeypatch.setattr(coinbase_module, "_request_json", no_default)
    monkeypatch.setattr(bitfinex_module, "_request_json", no_default)
    api = CandleApi(unit, all_hours(unit))
    assert len(ohlcv.read_missing_hours(make_fetcher(api), unit).rows) == len(all_hours(unit))  # type: ignore[arg-type]


def test_the_module_opens_no_connection_and_injects_the_requester_everywhere() -> None:
    text = Path(ohlcv.__file__).read_text()
    for word in ("urlopen", "import socket", "http.client", "import requests", "import httpx", "urllib.request", "backfill_transport", "backfill_run"):
        assert word not in text, word
    assert text.count("OhlcvProvider(request_json=requester)") == 2


@pytest.mark.parametrize("unit", ["bitstamp", "kraken", "", None, "../coinbase"])
def test_an_unscheduled_venue_is_refused_before_any_request(unit: Any) -> None:
    api = CandleApi("coinbase")
    refused("PROVIDER_REQUEST_MISMATCH", ohlcv.read_missing_hours, make_fetcher(api), unit)  # type: ignore[arg-type]
    assert api.urls == []


# --- the run -----------------------------------------------------------------------------------------


class RecordingConnection:
    def __init__(self) -> None:
        self.statements: list[Any] = []

    def execute(self, statement: Any) -> None:
        self.statements.append(statement)


class Database:
    def __init__(self) -> None:
        self.connections: list[RecordingConnection] = []

    @contextlib.contextmanager
    def connect(self) -> Any:
        connection = RecordingConnection()
        self.connections.append(connection)
        yield connection


@pytest.fixture
def store(tmp_path: Path) -> run.EvidenceStore:
    root = tmp_path / "backtest_evidence"
    (root / ".git").mkdir(parents=True)
    return run.EvidenceStore(root, public_repository=REPOSITORY)


def context(api: Any, store: run.EvidenceStore, database: Database | None = None) -> run.RunContext:
    instants = iter([RETRIEVED_AT] * 1000)
    return run.RunContext(
        transport=api, store=store, clock=lambda: next(instants), connect=None if database is None else database.connect, out=lambda line: None
    )


def inserted(database: Database) -> list[dict[str, Any]]:
    rows = []
    for connection in database.connections:
        for statement in connection.statements:
            sql = str(statement.compile(dialect=postgresql.dialect()))
            assert sql.startswith("INSERT INTO raw.btc_ohlcv") and "ON CONFLICT" in sql and "DO NOTHING" in sql and "DO UPDATE" not in sql
            parameters = statement.compile(dialect=postgresql.dialect()).params
            count = sum(1 for key in parameters if key.startswith("timestamp"))
            for index in range(count):
                rows.append({name: parameters[f"{name}_m{index}"] for name in ("timestamp", "exchange", "symbol", "timeframe", "provider", "open", "volume", "ingested_at")})
    return rows


@pytest.mark.parametrize("unit", ["coinbase", "bitfinex"])
def test_a_unit_persists_the_returned_hours_through_btc020_and_lists_the_rest_as_missing(unit: str, store: run.EvidenceStore) -> None:
    hours = all_hours(unit)
    returned = hours[::2]
    api, database = CandleApi(unit, returned), Database()
    ctx = context(api, store, database)
    ctx.clock = lambda: PERSISTED_AT
    ctx.fetch_clock = None
    report = run.run_unit(ctx, "ohlcv-missing-hours", unit)
    assert report.status == "DONE", report.detail
    venue = ohlcv.MISSING_HOURS_VENUES[unit].venue
    done = store.done("ohlcv-missing-hours", unit)
    assert done is not None and done["persisted"] == {"btc_ohlcv": len(returned)}
    summary = json.loads((store.unit_dir("ohlcv-missing-hours", unit) / "summary.json").read_bytes())
    iso = lambda at: at.isoformat()  # noqa: E731
    assert summary == {
        "venue": venue.venue_id,
        "rows": len(returned),
        "requested_hours": [iso(at) for at in hours],
        "returned_hours": [iso(at) for at in returned],
        "still_missing_hours": [iso(at) for at in hours if at not in returned],
    }
    rows = inserted(database)
    assert [row["timestamp"] for row in rows] == list(returned)
    assert {(row["exchange"], row["symbol"], row["timeframe"], row["provider"]) for row in rows} == {(venue.exchange, venue.symbol, "1h", venue.provider)}
    assert {row["ingested_at"] for row in rows} == {PERSISTED_AT}  # owner review ruling 7: the persistence instant
    assert {row["open"] for row in rows} == {Decimal("9350.5")} and {row["volume"] for row in rows} == {Decimal("123.4567")}
    # value-free: no price or volume reaches a file or the progress line
    for path in store.unit_dir("ohlcv-missing-hours", unit).iterdir():
        assert b"9350" not in path.read_bytes() and b"123.45" not in path.read_bytes()
    assert "9350" not in report.detail
    # done: skipped without a request
    calls = len(api.urls)
    assert run.run_unit(context(api, store, database), "ohlcv-missing-hours", unit).status == "SKIPPED" and len(api.urls) == calls


def test_an_empty_answer_leaves_every_hour_a_preserved_gap(store: run.EvidenceStore) -> None:
    database = Database()
    report = run.run_unit(context(CandleApi("coinbase"), store, database), "ohlcv-missing-hours", "coinbase")
    assert report.status == "DONE", report.detail
    assert store.done("ohlcv-missing-hours", "coinbase")["persisted"] == {"btc_ohlcv": 0}
    summary = json.loads((store.unit_dir("ohlcv-missing-hours", "coinbase") / "summary.json").read_bytes())
    assert summary["rows"] == 0 and summary["returned_hours"] == [] and len(summary["still_missing_hours"]) == 11
    assert inserted(database) == []


def test_a_run_without_persistence_is_resumed_from_its_saved_read(store: run.EvidenceStore) -> None:
    api = CandleApi("bitfinex", all_hours("bitfinex"))
    assert run.run_unit(context(api, store), "ohlcv-missing-hours", "bitfinex").status == "DONE"
    assert store.done("ohlcv-missing-hours", "bitfinex")["persisted"] == {"not_persisted": 1}
    database = Database()
    report = run.run_unit(context(api, store, database), "ohlcv-missing-hours", "bitfinex")
    assert report.status == "DONE", report.detail
    assert store.done("ohlcv-missing-hours", "bitfinex")["persisted"] == {"btc_ohlcv": 16} and len(inserted(database)) == 16
    # a re-read that differs from the saved read refuses for reconciliation by hand
    other = Database()
    store_two = run.EvidenceStore(store.root, public_repository=REPOSITORY)
    assert run.run_unit(context(CandleApi("coinbase", all_hours("coinbase")), store_two), "ohlcv-missing-hours", "coinbase").status == "DONE"
    changed = run.run_unit(context(CandleApi("coinbase", all_hours("coinbase")[1:]), store_two, other), "ohlcv-missing-hours", "coinbase")
    assert changed.status == "REFUSED" and "re-read differs" in changed.detail and other.connections == []


@pytest.mark.parametrize(
    ("unit", "at"),
    [
        ("coinbase", "2026-01-01 00:00"),
        ("coinbase", "2019-12-31 23:00"),
        ("bitfinex", "2026-06-30 23:00"),
        ("bitfinex", "2019-12-01 00:00"),
    ],
)
def test_a_candle_outside_the_data_window_is_refused_not_filtered(unit: str, at: str, store: run.EvidenceStore) -> None:
    row = (coinbase_row if unit == "coinbase" else bitfinex_row)(hour(at))
    api, database = CandleApi(unit, all_hours(unit), extra=[row]), Database()
    report = run.run_unit(context(api, store, database), "ohlcv-missing-hours", unit)
    assert report.status == "REFUSED" and report.detail.startswith("OBSERVATION_OUTSIDE_DATA_WINDOW"), report.detail
    assert database.connections == [] and not store.has_directory("ohlcv-missing-hours", unit)
    assert len(api.urls) == 1  # refused at the first response, before the adapter read any value


@pytest.mark.parametrize("unit", ["coinbase", "bitfinex"])
def test_an_unrequested_in_window_candle_is_dropped_by_the_adapter(unit: str) -> None:
    first, _ = ohlcv.MISSING_HOURS_VENUES[unit].runs[0]
    row = (coinbase_row if unit == "coinbase" else bitfinex_row)(first - H)
    read = ohlcv.read_missing_hours(make_fetcher(CandleApi(unit, all_hours(unit), extra=[row])), unit)  # type: ignore[arg-type]
    assert first - H not in read.returned and read.returned == all_hours(unit)


def _deep(depth: int) -> bytes:
    return b"[" * depth + b"]" * depth


MALFORMED = [  # (label, body, the guard that refuses it)
    ("not json", b"<html>", "is not JSON"),
    ("NaN literal", b"[[1580403600, NaN, 1, 1, 1, 1]]", "is not JSON"),
    ("Infinity literal", b"[[1580403600, 9300, Infinity, 9350, 9380, 1]]", "is not JSON"),
    ("deep nesting", _deep(100_000), "is not JSON"),
    ("an object", b'{"message": "error"}', "is not a list of candles"),
    ("a row not a list", b"[1580403600]", "is not a list"),
    ("an empty row", b"[[]]", "is not a list"),
    ("time as a string", b'[["1580403600", 1, 2, 1, 1, 1]]', "is not an epoch in seconds"),
    ("time as a float", b"[[1580403600.0, 1, 2, 1, 1, 1]]", "is not an epoch in seconds"),
    ("time as a boolean", b"[[true, 1, 2, 1, 1, 1]]", "is not an epoch in seconds"),
    ("time in milliseconds", b"[[1580403600000, 1, 2, 1, 1, 1]]", "is not an epoch in seconds"),
    ("a huge integer", b"[[" + b"9" * 5000 + b", 1, 2, 1, 1, 1]]", "is not JSON"),
    ("a short row", b"[[1580403600, 1, 2, 1, 1]]", "the adapter refused the response"),
    ("impossible prices", b"[[1580403600, 9, 1, 5, 5, 1]]", "the adapter refused the response"),  # low above high
    ("a value as text", b'[[1580403600, "x", 2, 1, 1, 1]]', "the adapter refused the response"),
]


@pytest.mark.parametrize(("label", "body", "guard"), MALFORMED, ids=[label for label, _, _ in MALFORMED])
def test_a_malformed_coinbase_answer_refuses_without_raising(label: str, body: bytes, guard: str, store: run.EvidenceStore) -> None:
    database = Database()
    report = run.run_unit(context(CandleApi("coinbase", body=body), store, database), "ohlcv-missing-hours", "coinbase")
    assert report.status == "REFUSED" and report.detail.startswith("RESPONSE_SHAPE_REFUSED"), (label, report.detail)
    assert guard in report.detail, (label, report.detail)  # the guard meant for it, not a later one
    assert not any(character.isdigit() for character in report.detail.split(":", 1)[1])
    assert database.connections == [] and not store.has_directory("ohlcv-missing-hours", "coinbase")


@pytest.mark.parametrize(
    "body",
    [
        b"[[1581418800, 1, 2, 1, 1, 1]]",  # seconds, not milliseconds
        b'[["1581418800000", 1, 1, 2, 1, 1]]',
        b"[[1581418800000, 1, 1, 2, 1]]",
        b"[[1581418800000, 5, 5, 1, 9, 1]]",  # high below low
        b"[[1581418801000, 1, 1, 2, 1, 1]]",  # not on the hour
    ],
)
def test_a_malformed_bitfinex_answer_refuses_without_raising(body: bytes) -> None:
    refused("RESPONSE_SHAPE_REFUSED", ohlcv.read_missing_hours, make_fetcher(CandleApi("bitfinex", body=body)), "bitfinex")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "row",
    [
        "[1580403600, 9300, 9400, 9350, 9380, 1e-20]",  # more places than NUMERIC(38,18) keeps
        "[1580403600, 9300, 9400, 9350, 9380, 1.25e-19]",
        "[1580403600, 9300, 1e400, 9350, 9380, 1]",  # an exponent far beyond the column
        "[1580403600, 1e21, 1e21, 1e21, 1e21, 1]",  # 10^21 does not fit below 10^20
    ],
)
def test_a_value_raw_btc_ohlcv_cannot_hold_exactly_refuses(row: str) -> None:
    api = CandleApi("coinbase", body=f"[{row}]".encode())
    error = refused("RESPONSE_SHAPE_REFUSED", ohlcv.read_missing_hours, make_fetcher(api), "coinbase")  # type: ignore[arg-type]
    assert "holds exactly" in str(error), str(error)


# review D1: a JSON fraction is decoded as the decimal it spells, never through a binary float
FIRST_CANDLE = {"coinbase": "[[1580403600, 9300, 9400, 9350, 9380, {}]]", "bitfinex": "[[1581418800000, 9350, 9380, 9400, 9300, {}]]"}
EXACT_VOLUMES = [
    "0.123456789012345678",  # eighteen places: a float keeps seventeen significant digits
    "99999999999999999999.999999999999999999",  # the largest value NUMERIC(38,18) holds: a float rounds it to 10^20
    "12345678901234567890.123456789012345678",
    "123.4567",
]
INEXACT_VOLUMES = [  # (numeral, the guard that refuses it)
    ("0.1234567890123456789", "holds exactly"),  # nineteen places: a float rounded it to a value that fits
    ("1e-324", "holds exactly"),  # a float underflowed it to zero, persisted as a zero volume
    ("100000000000000000000.000000000000000001", "holds exactly"),
    ("1e+1000000000000000000", "no decimal can hold"),  # beyond any decimal: refused, never raised (as R14-1)
]


@pytest.mark.parametrize("unit", ["coinbase", "bitfinex"])
@pytest.mark.parametrize("numeral", EXACT_VOLUMES)
def test_a_fraction_is_persisted_exactly_as_the_venue_spelled_it(unit: str, numeral: str, store: run.EvidenceStore) -> None:
    database = Database()
    api = CandleApi(unit, body=FIRST_CANDLE[unit].format(numeral).encode())
    report = run.run_unit(context(api, store, database), "ohlcv-missing-hours", unit)
    assert report.status == "DONE", report.detail
    (row,) = inserted(database)
    assert row["timestamp"] == all_hours(unit)[0] and str(row["volume"]) == numeral and row["volume"] == Decimal(numeral)
    assert row["open"] == Decimal("9350")


@pytest.mark.parametrize("unit", ["coinbase", "bitfinex"])
@pytest.mark.parametrize(("numeral", "guard"), INEXACT_VOLUMES)
def test_a_fraction_the_column_cannot_hold_is_refused_never_rounded(unit: str, numeral: str, guard: str, store: run.EvidenceStore) -> None:
    database = Database()
    api = CandleApi(unit, body=FIRST_CANDLE[unit].format(numeral).encode())
    report = run.run_unit(context(api, store, database), "ohlcv-missing-hours", unit)
    assert report.status == "REFUSED" and report.detail.startswith("RESPONSE_SHAPE_REFUSED"), report.detail
    assert guard in report.detail, report.detail
    assert database.connections == [] and not store.has_directory("ohlcv-missing-hours", unit)


def test_decoding_is_exact_whatever_the_callers_decimal_context() -> None:
    import decimal

    api = CandleApi("coinbase", body=FIRST_CANDLE["coinbase"].format("0.123456789012345678").encode())
    with decimal.localcontext(decimal.Context(prec=3, traps=[])):
        read = ohlcv.read_missing_hours(make_fetcher(api), "coinbase")  # type: ignore[arg-type]
        api_huge = CandleApi("coinbase", body=FIRST_CANDLE["coinbase"].format("1e+1000000000000000000").encode())
        error = refused("RESPONSE_SHAPE_REFUSED", ohlcv.read_missing_hours, make_fetcher(api_huge), "coinbase")  # type: ignore[arg-type]
    assert str(read.rows[0]["volume"]) == "0.123456789012345678" and "no decimal can hold" in str(error)


@pytest.mark.parametrize("status", [404, 429, 500])
def test_an_answer_other_than_200_refuses(status: int) -> None:
    refused("PROVIDER_RESPONSE_REFUSED", ohlcv.read_missing_hours, make_fetcher(CandleApi("bitfinex", status=status)), "bitfinex")  # type: ignore[arg-type]


# --- persistence ---------------------------------------------------------------------------------


def recorded(unit: str = "coinbase", rows: tuple[Any, ...] = ()) -> persistence.RecordedOhlcvProvider:
    venue = ohlcv.MISSING_HOURS_VENUES[unit].venue
    return persistence.RecordedOhlcvProvider(venue.exchange, venue.symbol, venue.provider, rows=rows)


def test_the_recorded_provider_serves_inclusive_hours_of_its_own_venue_only() -> None:
    hours = all_hours("coinbase")
    rows = tuple({"timestamp": at, "open": 1} for at in hours)
    provider = recorded(rows=rows)
    served = provider.fetch_ohlcv(exchange="coinbase", symbol="BTC-USD", timeframe="1h", start=hours[3], end=hours[5])
    assert [row["timestamp"] for row in served] == list(hours[3:6])
    refused("PROVIDER_REQUEST_MISMATCH", provider.fetch_ohlcv, exchange="bitfinex", symbol="BTC-USD", timeframe="1h", start=hours[0], end=hours[0])
    refused("PROVIDER_REQUEST_MISMATCH", provider.fetch_ohlcv, exchange="coinbase", symbol="BTC-USD", timeframe="1d", start=hours[0], end=hours[0])
    request = provider.collection_request(hours[0], hours[0])
    assert (request.exchange, request.symbol, request.provider, request.derived_timeframes) == ("coinbase", "BTC-USD", "coinbase", ())
    assert provider.provider_id == "coinbase"


@pytest.mark.parametrize(
    "changes",
    [
        {"exchange": "bitstamp"},
        {"symbol": "BTC/USD"},
        {"provider": "bitstamp"},
        {"derived_timeframes": ("1d",)},
        {"start": hour("2019-12-31 23:00"), "end": hour("2019-12-31 23:00")},
        {"start": hour("2025-12-31 23:00"), "end": hour("2026-01-01 00:00")},
    ],
)
def test_persist_ohlcv_refuses_a_renamed_derived_or_outside_request(changes: dict[str, Any]) -> None:
    at = all_hours("coinbase")[0]
    fields = {"exchange": "coinbase", "symbol": "BTC-USD", "provider": "coinbase", "start": at, "end": at, "derived_timeframes": (), **changes}
    request = OhlcvCollectionRequest(**fields)
    connection = RecordingConnection()
    reason = "REQUEST_OUTSIDE_DATA_WINDOW" if "start" in changes else "PROVIDER_REQUEST_MISMATCH"
    refused(reason, persistence.persist_ohlcv, recorded(), connection, request, ingested_at=PERSISTED_AT)
    assert connection.statements == []
    refused("PROVIDER_REQUEST_MISMATCH", persistence.persist_ohlcv, object(), connection, request)


def test_the_last_in_window_hour_may_be_persisted() -> None:
    last = hour("2025-12-31 23:00")
    provider = recorded(rows=({"timestamp": last, "open": Decimal(1), "high": Decimal(2), "low": Decimal(1), "close": Decimal(1), "volume": Decimal(0)},))
    connection = RecordingConnection()
    result = persistence.persist_ohlcv(provider, connection, provider.collection_request(last, last), ingested_at=PERSISTED_AT)
    assert len(result.raw_bars) == 1 and result.derived_bars == () and len(connection.statements) == 1


# --- the transport ---------------------------------------------------------------------------------


class Reply:
    def __init__(self, url: str) -> None:
        self.url, self.status = url, 200

    def read(self) -> bytes:
        return b"[]"

    def __enter__(self) -> Reply:
        return self

    def __exit__(self, *args: Any) -> None:
        return None


@pytest.mark.parametrize(
    "url",
    [
        "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=3600&start=2020-01-30T17%3A00%3A00Z&end=2020-01-30T17%3A00%3A00Z",
        "https://api-pub.bitfinex.com/v2/candles/trade:1h:tBTCUSD/hist?start=1581418800000&end=1581425999999&limit=10000&sort=1",
    ],
)
def test_the_transport_allows_the_two_candle_hosts(url: str) -> None:
    opened: list[str] = []

    def opener(request: Any, timeout: float) -> Reply:
        opened.append(request.full_url)
        return Reply(request.full_url)

    transport = transport_module.UrllibTransport(opener=opener, sleep=lambda seconds: None)
    assert transport(url, {}) == TransportResponse(200, b"[]") and opened == [url]


@pytest.mark.parametrize(
    "url",
    [
        "http://api.exchange.coinbase.com/products/BTC-USD/candles",
        "https://api.pro.coinbase.com/products/BTC-USD/candles",
        "https://api.bitfinex.com/v2/candles/trade:1h:tBTCUSD/hist",
        "https://api-pub.bitfinex.com:8443/v2/candles/trade:1h:tBTCUSD/hist",
        "https://www.bitstamp.net/api/v2/ohlc/btcusd/",
    ],
)
def test_the_transport_still_refuses_every_other_host(url: str) -> None:
    def opener(request: Any, timeout: float) -> Reply:
        raise AssertionError("connected")

    refused("PROVIDER_REQUEST_MISMATCH", transport_module.UrllibTransport(opener=opener, sleep=lambda seconds: None), url, {})
    assert transport_module.ALLOWED_HOSTS >= {"api.exchange.coinbase.com", "api-pub.bitfinex.com"} and len(transport_module.ALLOWED_HOSTS) == 8


@pytest.mark.parametrize(
    "run_",
    [(hour("2025-12-31 23:00"), hour("2026-01-01 00:00")), (hour("2019-12-31 23:00"), hour("2020-01-01 00:00"))],
    ids=["into-the-holdout", "from-the-prohibited-window"],
)
def test_a_run_reaching_outside_the_data_window_is_refused_before_any_request(run_: tuple[datetime, datetime], monkeypatch: pytest.MonkeyPatch) -> None:
    spec = ohlcv.MISSING_HOURS_VENUES["coinbase"]
    monkeypatch.setitem(ohlcv.MISSING_HOURS_VENUES, "coinbase", ohlcv.MissingHoursVenue(spec.venue, (run_,), spec.adapter, spec.candle_instant))
    api = CandleApi("coinbase", all_hours("coinbase"))
    refused("REQUEST_OUTSIDE_DATA_WINDOW", ohlcv.read_missing_hours, make_fetcher(api), "coinbase")  # type: ignore[arg-type]
    assert api.urls == []
