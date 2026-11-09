"""RBT-003 Part B: the network transport and the resumable collection run, offline.

The transport is exercised through an injected opener and the run through
fake transports, a temporary private store and a recording connection: no test
opens a socket, touches a database or reads a real response.
"""

from __future__ import annotations

import contextlib
import gzip
import io
import json
import socket
import urllib.error
import urllib.request
import urllib.response
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from email.message import Message
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.dialects import postgresql

from btc_predictor.research_backtest import backfill_binance as binance
from btc_predictor.research_backtest import backfill_coinglass as coinglass
from btc_predictor.research_backtest import backfill_coinmetrics as coinmetrics
from btc_predictor.research_backtest import backfill_kraken as kraken
from btc_predictor.research_backtest import backfill_persistence as persistence
from btc_predictor.research_backtest import backfill_projection as projection
from btc_predictor.research_backtest import backfill_run as run
from btc_predictor.research_backtest import backfill_sources as sources
from btc_predictor.research_backtest import backfill_transport as transport_module
from btc_predictor.research_backtest.backfill_sources import BackfillRefused
from btc_predictor.tests import rbt003_backfill_fixtures as fx
from btc_predictor.tests.rbt003_backfill_fixtures import RETRIEVED_AT, FakeTransport, utc


REPOSITORY = Path(__file__).resolve().parents[2]
ADAPTERS = (sources, binance, kraken, coinmetrics, coinglass, projection, persistence)


@pytest.fixture(autouse=True)
def no_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("an RBT-003 Part B test opened a socket")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def refused(reason: str, call: Any, *args: Any, **kwargs: Any) -> BackfillRefused:
    with pytest.raises(BackfillRefused) as caught:
        call(*args, **kwargs)
    assert caught.value.reason_code == reason, str(caught.value)
    return caught.value


# --- the transport -----------------------------------------------------------------------------


class Reply:
    def __init__(self, status: int, body: bytes) -> None:
        self.status, self.body = status, body

    def __enter__(self) -> Reply:
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def http_error(url: str, code: int, body: bytes = b"", retry_after: str | None = None) -> urllib.error.HTTPError:
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return urllib.error.HTTPError(url, code, "status", headers, io.BytesIO(body))


class Opener:
    """Answers each call from a script of replies or exceptions, recording every request."""

    def __init__(self, *script: Any) -> None:
        self.script = list(script)
        self.requests: list[Any] = []

    def __call__(self, request: Any, timeout: float) -> Any:
        self.requests.append(request)
        step = self.script.pop(0)
        if isinstance(step, BaseException):
            raise step
        return step


def make_transport(opener: Opener, sleeps: list[float] | None = None, **kwargs: Any) -> transport_module.UrllibTransport:
    record = sleeps if sleeps is not None else []
    return transport_module.UrllibTransport(opener=opener, sleep=record.append, **kwargs)


URL = "https://data.binance.vision/data/futures/um/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-2020-02.zip"


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/data",
        "http://data.binance.vision/data/x.zip",
        "https://data.binance.vision:8443/data/x.zip",
        "https://user@data.binance.vision/data/x.zip",
        "https://data.binance.vision.example.com/x",
        "ftp://data.binance.vision/x",
    ],
)
def test_the_transport_refuses_any_other_host_before_connecting(url: str) -> None:
    opener = Opener()
    refused("PROVIDER_REQUEST_MISMATCH", make_transport(opener), url, {})
    assert opener.requests == []


def test_the_transport_returns_the_response_and_sends_the_headers() -> None:
    opener = Opener(Reply(200, b"archive"))
    sleeps: list[float] = []
    response = make_transport(opener, sleeps, pause_seconds=0.5)(URL, {"CG-API-KEY": "secret"})
    assert (response.status, response.body) == (200, b"archive") and sleeps == [0.5]
    request = opener.requests[0]
    assert request.get_method() == "GET" and request.full_url == URL
    assert request.get_header("Cg-api-key") == "secret" and request.get_header("User-agent") == transport_module.USER_AGENT


def test_a_404_is_returned_unchanged_without_a_retry() -> None:
    opener = Opener(http_error(URL, 404, b"missing"))
    response = make_transport(opener)(URL, {})
    assert (response.status, response.body) == (404, b"missing") and len(opener.requests) == 1


def test_transient_failures_are_retried_with_a_growing_pause_and_retry_after_is_honoured() -> None:
    opener = Opener(
        urllib.error.URLError("reset"), http_error(URL, 503), http_error(URL, 429, retry_after="7"), TimeoutError(), Reply(200, b"ok")
    )
    sleeps: list[float] = []
    transport = make_transport(opener, sleeps, pause_seconds=0.1, backoff_seconds=1.0)
    response = transport(URL, {})
    assert (response.status, response.body) == (200, b"ok")
    assert sleeps == [0.1, 1.0, 2.0, 7.0, 8.0] and (transport.requests, transport.retries) == (5, 4)


def test_a_retried_status_on_the_last_attempt_is_returned_for_the_fetcher_to_refuse() -> None:
    opener = Opener(*(http_error(URL, 503) for _ in range(3)))
    response = make_transport(opener, attempts=3)(URL, {})
    assert response.status == 503
    fetcher = sources.Fetcher(make_transport(Opener(*(http_error(URL, 503) for _ in range(3))), attempts=3), sources.RetrievalLog(), lambda: RETRIEVED_AT)
    refused("PROVIDER_RESPONSE_REFUSED", fetcher.fetch, URL)


def test_a_url_that_never_answers_raises_without_any_header_in_the_message() -> None:
    opener = Opener(*(urllib.error.URLError("down") for _ in range(2)))
    with pytest.raises(transport_module.TransportFailed) as caught:
        make_transport(opener, attempts=2)(URL, {"CG-API-KEY": "secret-key"})
    assert "secret-key" not in str(caught.value) and "URLError" in str(caught.value)


def test_a_long_retry_after_is_capped() -> None:
    opener = Opener(http_error(URL, 429, retry_after="100000"), Reply(200, b"ok"))
    sleeps: list[float] = []
    make_transport(opener, sleeps, pause_seconds=0)(URL, {})
    assert sleeps == [0, transport_module.MAX_RETRY_AFTER_SECONDS]


class FakeHttps(urllib.request.HTTPSHandler):
    """Answers inside urllib's real handler chain (redirect handling included) and opens no socket."""

    handler_order = 100  # ahead of the default HTTP and HTTPS handlers, which would open a socket

    def __init__(self, replies: dict[str, tuple[int, dict[str, str], bytes]]) -> None:
        super().__init__()
        self.replies = replies
        self.requests: list[tuple[str, dict[str, str]]] = []

    def https_open(self, request: Any) -> Any:
        self.requests.append((request.full_url, dict(request.header_items())))
        status, headers, body = self.replies[request.full_url]
        message = Message()
        for name, value in headers.items():
            message[name] = value
        response = urllib.response.addinfourl(io.BytesIO(body), message, request.full_url, status)
        response.msg = "fake"
        return response

    http_open = https_open


CG_URL = coinglass.FLOW_HISTORY_URL
JANUARY_2026 = "https://data.binance.vision/data/futures/um/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-2026-01.zip"


@pytest.mark.parametrize("code", [301, 302, 303, 307, 308])
@pytest.mark.parametrize(
    ("url", "target"),
    [
        (CG_URL, "https://outside.invalid/collect"),  # another host, with the key
        (CG_URL, "http://open-api-v4.coinglass.com/api/etf/bitcoin/flow-history"),  # plain HTTP, with the key
        (URL, JANUARY_2026),  # a bounded February 2020 archive sent to the holdout
    ],
)
def test_review_b1_a_redirect_is_returned_never_followed(code: int, url: str, target: str) -> None:
    handler = FakeHttps({url: (code, {"Location": target}, b"moved"), target: (200, {}, b"777000099")})
    transport = transport_module.UrllibTransport(opener=transport_module.build_opener(handler), sleep=lambda seconds: None)
    response = transport(url, {"CG-API-KEY": "secret-key"})
    assert response.status == code and b"777000099" not in response.body
    assert [requested for requested, _ in handler.requests] == [url]  # the target was never requested
    fetcher = sources.Fetcher(
        transport_module.UrllibTransport(opener=transport_module.build_opener(FakeHttps(handler.replies)), sleep=lambda seconds: None),
        sources.RetrievalLog(), lambda: RETRIEVED_AT, headers={"CG-API-KEY": "secret-key"},
    )
    caught = refused("PROVIDER_RESPONSE_REFUSED", fetcher.fetch, url)
    assert target not in str(caught) and "secret-key" not in str(caught)


def test_review_b1_the_default_opener_refuses_redirects_and_a_redirected_response_refuses() -> None:
    director = transport_module.UrllibTransport().opener.__self__
    redirecting = [handler for handler in director.handlers if isinstance(handler, urllib.request.HTTPRedirectHandler)]
    assert len(redirecting) == 1 and isinstance(redirecting[0], transport_module.RefuseRedirects)
    # an injected opener that did follow a redirect: its response is refused, its body never read
    reply = Reply(200, b"777000098")
    reply.url = JANUARY_2026
    reply.read = None  # reading would raise
    opener = Opener(reply)
    caught = refused("PROVIDER_RESPONSE_REFUSED", make_transport(opener), URL, {})
    assert "2026" not in str(caught) and len(opener.requests) == 1
    plain = Reply(200, b"archive")
    plain.url = URL
    assert make_transport(Opener(plain))(URL, {}).body == b"archive"


@pytest.mark.parametrize(
    "headers",
    [
        {"CG-API-KEY": "synthetic-secret\ncontinued"},
        {"CG-API-KEY": "synthetic-secret\r\nX-Injected: 1"},
        {"CG-API-KEY": "synthetic-secret\x00"},
        {"CG-API-KEY": " synthetic-secret"},
        {"CG-API-KEY": "synthetic-secret "},
        {"CG-API-KEY": "synthetic-s\u00e9cret"},
        {"CG-API-KEY": ""},
        {"CG API KEY": "synthetic-secret"},
        {"CG-API-KEY\n": "synthetic-secret"},
    ],
)
def test_review_b6_a_header_http_does_not_allow_refuses_before_urllib_without_being_quoted(headers: dict[str, str]) -> None:
    opener = Opener()
    caught = refused("PROVIDER_REQUEST_MISMATCH", make_transport(opener), URL, headers)
    assert opener.requests == [] and "synthetic" not in str(caught)


def test_review_b6_an_unexpected_error_leaves_its_type_only_and_is_not_retried() -> None:
    opener = Opener(ValueError("Invalid header value b'synthetic-secret'"))
    with pytest.raises(transport_module.TransportFailed) as caught:
        make_transport(opener)(URL, {})
    assert "synthetic-secret" not in str(caught.value) and "ValueError" in str(caught.value)
    assert caught.value.__cause__ is None and caught.value.__suppress_context__ and len(opener.requests) == 1


def test_only_the_transport_module_may_open_a_connection() -> None:
    banned = ("urlopen", "import socket", "http.client", "import requests", "import httpx", "urllib.request")
    for module in (*ADAPTERS, run):
        text = Path(module.__file__).read_text()
        for word in banned:
            assert word not in text, (module.__name__, word)
    for module in ADAPTERS:
        text = Path(module.__file__).read_text()
        assert "backfill_transport" not in text and "backfill_run" not in text, module.__name__
    assert "urllib.request" in Path(transport_module.__file__).read_text()


# --- the evidence store ------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path: Path) -> run.EvidenceStore:
    root = tmp_path / "backtest_evidence"
    (root / ".git").mkdir(parents=True)
    return run.EvidenceStore(root, public_repository=REPOSITORY)


def test_ruling_9_the_store_must_be_a_git_work_tree_outside_the_public_repository(tmp_path: Path) -> None:
    refused("PROVIDER_REQUEST_MISMATCH", run.EvidenceStore, REPOSITORY / "backtest_evidence", public_repository=REPOSITORY)
    refused("PROVIDER_REQUEST_MISMATCH", run.EvidenceStore, REPOSITORY, public_repository=REPOSITORY)
    refused("PROVIDER_REQUEST_MISMATCH", run.EvidenceStore, REPOSITORY.parent, public_repository=REPOSITORY)
    refused("PROVIDER_REQUEST_MISMATCH", run.EvidenceStore, tmp_path / "no-git", public_repository=REPOSITORY)
    # a git work tree inside, or around, a public repository is refused for that reason alone
    public = tmp_path / "public"
    for root in (public / "evidence", public, tmp_path):
        (root / ".git").mkdir(parents=True, exist_ok=True)
        refused("PROVIDER_REQUEST_MISMATCH", run.EvidenceStore, root, public_repository=public)
    (tmp_path / "private" / ".git").mkdir(parents=True)
    assert run.EvidenceStore(tmp_path / "private", public_repository=public).base == tmp_path / "private" / run.STORE_LAYOUT


def test_a_unit_whose_files_changed_is_not_done(store: run.EvidenceStore) -> None:
    # every completed unit binds its summary and retrieval log (review B4)
    store.write("s", "u", {"a.json": b"1", "summary.json": b"{}", "retrievals.json": b"[]"}, completed_at=RETRIEVED_AT, persisted={})
    assert store.done("s", "u") is not None
    (store.unit_dir("s", "u") / "a.json").write_bytes(b"2")
    assert store.done("s", "u") is None
    refused("PROVIDER_REQUEST_MISMATCH", store.write, "s", "u", {"../x": b"1"}, completed_at=RETRIEVED_AT, persisted={})


def outside_tree(tmp_path: Path) -> Path:
    public = tmp_path / "public-tree"
    public.mkdir()
    return public


@pytest.mark.parametrize("linked", ["layout", "source", "unit"])
def test_review_b5_a_linked_directory_below_the_root_is_refused_and_nothing_lands_outside(
    store: run.EvidenceStore, tmp_path: Path, linked: str
) -> None:
    public = outside_tree(tmp_path)
    target = {"layout": store.root / "research_backtest_v1", "source": store.base / "binance-funding", "unit": store.base / "binance-funding" / "2020-02"}[linked]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(public, target_is_directory=True)
    refused("PROVIDER_REQUEST_MISMATCH", store.write, "binance-funding", "2020-02", {"summary.json": b"777000020"}, completed_at=RETRIEVED_AT, persisted={})
    refused("PROVIDER_REQUEST_MISMATCH", store.done, "binance-funding", "2020-02")
    transport = funding_world()
    report_ = run.run_unit(context(transport, store, Database()), "binance-funding", "2020-02")
    assert report_.status == "REFUSED" and transport.calls == []  # refused before any request
    assert list(public.rglob("*")) == []


def test_review_b5_a_linked_file_is_never_written_through_or_trusted(store: run.EvidenceStore, tmp_path: Path) -> None:
    public = outside_tree(tmp_path)
    outside = public / "outside.json"
    outside.write_bytes(b"public")
    directory = store.unit_dir("binance-funding", "2020-02")
    directory.mkdir(parents=True)
    (directory / "summary.json").symlink_to(outside)
    refused("PROVIDER_REQUEST_MISMATCH", store.write, "binance-funding", "2020-02", {"summary.json": b"777000021"}, completed_at=RETRIEVED_AT, persisted={})
    (directory / "summary.json").unlink()
    # a planted partial link is removed, never followed
    (directory / "summary.json.partial").symlink_to(outside)
    store.write("binance-funding", "2020-02", {"summary.json": b"777000022", "retrievals.json": b"[]"}, completed_at=RETRIEVED_AT, persisted={})
    assert outside.read_bytes() == b"public" and not (directory / "summary.json").is_symlink()
    assert (directory / "summary.json").read_bytes() == b"777000022" and store.done("binance-funding", "2020-02") is not None
    # a bound file replaced by a link to identical bytes is not trusted
    outside.write_bytes(b"777000022")
    (directory / "summary.json").unlink()
    (directory / "summary.json").symlink_to(outside)
    refused("PROVIDER_REQUEST_MISMATCH", store.done, "binance-funding", "2020-02")
    (directory / "summary.json").unlink()
    (directory / "summary.json").write_bytes(b"777000022")
    (directory / "DONE.json").rename(public / "DONE.json")
    (directory / "DONE.json").symlink_to(public / "DONE.json")
    refused("PROVIDER_REQUEST_MISMATCH", store.done, "binance-funding", "2020-02")


@pytest.mark.parametrize("name", ["../x", "x/y", "", ".", "..", "A", "-x", "x" * 41, None])
def test_review_b5_a_source_or_unit_must_be_a_plain_store_name(store: run.EvidenceStore, name: Any) -> None:
    refused("PROVIDER_REQUEST_MISMATCH", store.unit_dir, name, "all")
    refused("PROVIDER_REQUEST_MISMATCH", store.unit_dir, "binance-funding", name)


@pytest.mark.parametrize("name", ["../x.json", "a/b.json", "", ".", "..", ".hidden", "DONE.json"])
def test_review_b5_a_unit_file_must_be_a_plain_file_name(store: run.EvidenceStore, name: str) -> None:
    refused("PROVIDER_REQUEST_MISMATCH", store.write, "binance-funding", "2020-02", {name: b"1"}, completed_at=RETRIEVED_AT, persisted={})


# --- the run -----------------------------------------------------------------------------------


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


def context(transport: Any, store: run.EvidenceStore, database: Database | None = None, **kwargs: Any) -> run.RunContext:
    lines: list[str] = []
    ctx = run.RunContext(
        transport=transport, store=store, clock=lambda: RETRIEVED_AT,
        connect=None if database is None else database.connect, out=lines.append, **kwargs,
    )
    return ctx


def funding_world() -> FakeTransport:
    transport = FakeTransport()
    rows = [fx.funding_row(utc(2020, 2, day, hour), rate="0.000777000006") for day in (1, 2) for hour in (0, 8, 16)]
    fx.add_archive(transport, binance.funding_archive_url(date(2020, 2, 1)), rows)
    return transport


def unit_files(store: run.EvidenceStore, source: str, unit: str) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in store.unit_dir(source, unit).iterdir()}


def test_a_funding_unit_is_read_persisted_recorded_and_then_skipped(store: run.EvidenceStore) -> None:
    transport, database = funding_world(), Database()
    report = run.run_unit(context(transport, store, database), "binance-funding", "2020-02")
    assert report.status == "DONE", report.detail
    files = unit_files(store, "binance-funding", "2020-02")
    assert sorted(files) == ["DONE.json", "retrievals.json", "summary.json"]
    done = json.loads(files["DONE.json"])
    assert done["persisted"] == {"funding_rates": 6} and set(done["files"]) == {"retrievals.json", "summary.json"}
    assert json.loads(files["summary.json"]) == {"rows": 6, "excluded": []}
    retrievals = json.loads(files["retrievals.json"])
    assert [item["status"] for item in retrievals] == [200, 200] and all(set(item) == {"url", "retrieved_at", "status", "size", "sha256"} for item in retrievals)
    # value-free: no rate reaches a progress line, a summary or the retrieval log
    assert all(b"777000006" not in data for data in files.values()) and "777000006" not in report.detail
    assert len(database.connections) == 1 and len(database.connections[0].statements) == 1
    # resumed: a done unit is skipped without a request
    calls = len(transport.calls)
    assert run.run_unit(context(transport, store, database), "binance-funding", "2020-02").status == "SKIPPED"
    assert len(transport.calls) == calls


def test_a_unit_read_without_persistence_is_read_again_by_a_persisting_run(store: run.EvidenceStore) -> None:
    transport = funding_world()
    assert run.run_unit(context(transport, store), "binance-funding", "2020-02").status == "DONE"
    assert store.done("binance-funding", "2020-02")["persisted"] == {"not_persisted": 1}
    assert run.run_unit(context(transport, store), "binance-funding", "2020-02").status == "SKIPPED"
    database = Database()
    assert run.run_unit(context(transport, store, database), "binance-funding", "2020-02").status == "DONE"
    assert store.done("binance-funding", "2020-02")["persisted"] == {"funding_rates": 6}


def test_a_refused_unit_writes_nothing_and_its_message_masks_every_digit(store: run.EvidenceStore) -> None:
    transport = FakeTransport(default_status=500)
    report = run.run_unit(context(transport, store, Database()), "binance-funding", "2020-02")
    assert report.status == "REFUSED" and report.detail.startswith("PROVIDER_RESPONSE_REFUSED")
    assert not any(character.isdigit() for character in report.detail.split(":", 1)[1])
    assert store.done("binance-funding", "2020-02") is None and not (store.unit_dir("binance-funding", "2020-02") / "DONE.json").exists()


def test_the_run_stops_at_a_refusal_and_honours_its_limit(store: run.EvidenceStore) -> None:
    ctx = context(FakeTransport(default_status=500), store)
    reports = run.run(ctx, ["binance-funding"])
    assert [report.status for report in reports] == ["REFUSED"]
    reports = run.run(context(funding_world(), store), ["binance-funding"], limit=1, stop_on_refusal=False)
    assert len(reports) == 1
    refused("PROVIDER_REQUEST_MISMATCH", run.run, ctx, ["nonsense"])


def test_the_units_follow_rbt002s_spans() -> None:
    assert run.SOURCES["binance-funding"].units()[0] == "2020-01" and run.SOURCES["binance-funding"].units()[-1] == "2025-12"
    assert run.SOURCES["binance-open-interest"].units()[0] == "2020-09"
    days = run.SOURCES["kraken-liquidations"].units()
    assert (days[0], days[-1], len(days)) == ("2021-05-27", "2025-12-31", (date(2025, 12, 31) - date(2021, 5, 27)).days + 1)
    assert all(len(run.SOURCES[name].units()) == 1 for name in ("binance-basis", "kraken-incidents", "coinmetrics-market-cap", "coinglass-etf"))


@pytest.mark.parametrize(
    ("source", "unit"),
    [
        ("kraken-liquidations", "2021-05-26"),  # before the execution log's depth
        ("kraken-liquidations", "2026-01-01"),
        ("binance-open-interest", "2020-08"),  # before the metrics archive's depth
        ("binance-funding", "2019-12"),
        ("binance-funding", "2026-01"),
        ("binance-funding", "2020-1"),
        ("binance-funding", "../2020-01"),
        ("binance-basis", "2020-01"),
        ("coinglass-etf", "2024-01"),
        ("nonsense", "all"),
    ],
)
def test_review_b8_a_unit_its_source_does_not_schedule_is_refused_before_any_request(store: run.EvidenceStore, source: str, unit: str) -> None:
    transport = FakeTransport()
    report_ = run.run_unit(context(transport, store, Database(), allow_coinglass=True, coinglass_key="key-123"), source, unit)
    assert report_.status == "REFUSED" and report_.detail.startswith("PROVIDER_REQUEST_MISMATCH"), report_.detail
    assert transport.calls == [] and not store.base.exists()


def done_marker(store: run.EvidenceStore, source: str, unit: str) -> dict[str, Any]:
    return json.loads((store.unit_dir(source, unit) / "DONE.json").read_bytes())


def rewrite_marker(store: run.EvidenceStore, source: str, unit: str, marker: Any) -> None:
    (store.unit_dir(source, unit) / "DONE.json").write_bytes(json.dumps(marker).encode())


def test_review_b4_a_copied_unit_is_not_skipped(store: run.EvidenceStore) -> None:
    transport, database = funding_world(), Database()
    assert run.run_unit(context(transport, store, database), "binance-funding", "2020-02").status == "DONE"
    store.unit_dir("binance-funding", "2020-03").mkdir()
    for path in store.unit_dir("binance-funding", "2020-02").iterdir():
        (store.unit_dir("binance-funding", "2020-03") / path.name).write_bytes(path.read_bytes())
    calls = len(transport.calls)
    report_ = run.run_unit(context(transport, store, database), "binance-funding", "2020-03")
    assert report_.status == "REFUSED" and "reconcile" in report_.detail and len(transport.calls) == calls
    assert store.done("binance-funding", "2020-03") is None


def test_review_b4_an_unpersisted_marker_edited_to_look_persisted_is_not_skipped(store: run.EvidenceStore) -> None:
    transport = funding_world()
    assert run.run_unit(context(transport, store), "binance-funding", "2020-02").status == "DONE"
    marker = done_marker(store, "binance-funding", "2020-02")
    assert marker["persisted"] == {"not_persisted": 1}
    for persisted in ({}, {"funding_rates": 5}, {"funding_rates": 6, "open_interest": 1}, {"etf_flows": 6}):
        rewrite_marker(store, "binance-funding", "2020-02", marker | {"persisted": persisted})
        calls = len(transport.calls)
        report_ = run.run_unit(context(transport, store, Database()), "binance-funding", "2020-02")
        assert report_.status == "REFUSED" and len(transport.calls) == calls, persisted
    rewrite_marker(store, "binance-funding", "2020-02", marker | {"persisted": {"funding_rates": 6}})
    assert run.run_unit(context(transport, store, Database()), "binance-funding", "2020-02").status == "SKIPPED"


def test_review_b4_a_source_that_persists_nothing_records_nothing_and_binds_its_evidence(store: run.EvidenceStore) -> None:
    transport = FakeTransport()
    transport.add(run.TARDIS_EXCHANGE_URL, tardis_body())
    assert run.run_unit(context(transport, store), "kraken-incidents", "all").status == "DONE"
    marker = done_marker(store, "kraken-incidents", "all")
    rewrite_marker(store, "kraken-incidents", "all", marker | {"persisted": {"liquidations": 0}})
    assert run.run_unit(context(transport, store), "kraken-incidents", "all").status == "REFUSED"
    rewrite_marker(store, "kraken-incidents", "all", marker)
    assert run.run_unit(context(transport, store), "kraken-incidents", "all").status == "SKIPPED"
    # a market-cap marker that does not bind the evidence file is refused
    directory = store.unit_dir("coinmetrics-market-cap", "all")
    store.write("coinmetrics-market-cap", "all", {"summary.json": b"{}", "retrievals.json": b"[]"}, completed_at=RETRIEVED_AT, persisted={})
    report_ = run.run_unit(context(transport, store), "coinmetrics-market-cap", "all")
    assert report_.status == "REFUSED" and "evidence" in report_.detail and directory.exists()


MARKER_EDITS = [
    ("run_version", "RBT003_PART_B_COLLECTION_RUN_V0"),
    ("source", "binance-open-interest"),
    ("unit", "2020-03"),
    ("completed_at", "2026-11-05T10:00:00"),
    ("completed_at", "not an instant"),
    ("persisted", {"funding_rates": True}),
    ("persisted", {"funding_rates": -6}),
    ("persisted", {"Funding Rates": 6}),
    ("persisted", []),
    ("files", {}),
    ("files", "summary.json"),
]


@pytest.mark.parametrize(("key", "value"), MARKER_EDITS)
def test_review_b4_a_marker_must_name_its_version_source_unit_and_valid_records(store: run.EvidenceStore, key: str, value: Any) -> None:
    transport, database = funding_world(), Database()
    assert run.run_unit(context(transport, store, database), "binance-funding", "2020-02").status == "DONE"
    rewrite_marker(store, "binance-funding", "2020-02", done_marker(store, "binance-funding", "2020-02") | {key: value})
    assert store.done("binance-funding", "2020-02") is None
    calls = len(transport.calls)
    assert run.run_unit(context(transport, store, database), "binance-funding", "2020-02").status == "REFUSED"
    assert len(transport.calls) == calls


def test_review_b4_a_marker_must_bind_the_summary_and_log_under_plain_names(store: run.EvidenceStore, tmp_path: Path) -> None:
    transport, database = funding_world(), Database()
    assert run.run_unit(context(transport, store, database), "binance-funding", "2020-02").status == "DONE"
    marker = done_marker(store, "binance-funding", "2020-02")
    outside = tmp_path / "outside.json"
    outside.write_bytes(b"{}")
    for files in (
        {"summary.json": marker["files"]["summary.json"]},  # no retrieval log
        marker["files"] | {"../../../../../outside.json": sources.sha256_hex(b"{}")},
        marker["files"] | {"DONE.json": marker["files"]["summary.json"]},
        marker["files"] | {"summary.json": marker["files"]["summary.json"].upper()},
    ):
        rewrite_marker(store, "binance-funding", "2020-02", marker | {"files": files})
        assert store.done("binance-funding", "2020-02") is None, files
    for extra in ({"note": 1}, None):
        bad = dict(marker)
        if extra is None:
            del bad["completed_at"]
        else:
            bad |= extra
        rewrite_marker(store, "binance-funding", "2020-02", bad)
        assert store.done("binance-funding", "2020-02") is None
    (store.unit_dir("binance-funding", "2020-02") / "DONE.json").write_bytes(b"{not json")
    assert store.done("binance-funding", "2020-02") is None
    assert run.run_unit(context(transport, store, database), "binance-funding", "2020-02").status == "REFUSED"


def test_review_b4_a_changed_bound_file_refuses_the_unit_instead_of_reading_it_again(store: run.EvidenceStore) -> None:
    transport, database = funding_world(), Database()
    assert run.run_unit(context(transport, store, database), "binance-funding", "2020-02").status == "DONE"
    (store.unit_dir("binance-funding", "2020-02") / "summary.json").write_bytes(b'{"rows":6,"excluded":[]} ')
    calls = len(transport.calls)
    report_ = run.run_unit(context(transport, store, database), "binance-funding", "2020-02")
    assert report_.status == "REFUSED" and len(transport.calls) == calls


class AdvancingClock:
    def __init__(self, start: datetime = RETRIEVED_AT) -> None:
        self.now = start

    def __call__(self) -> datetime:
        self.now += timedelta(seconds=1)
        return self.now


LATER = RETRIEVED_AT + timedelta(hours=1)


def advancing_context(transport: Any, store: run.EvidenceStore, database: Database | None = None, *, start: datetime = RETRIEVED_AT, **kwargs: Any) -> run.RunContext:
    return run.RunContext(
        transport=transport, store=store, clock=AdvancingClock(start),
        connect=None if database is None else database.connect, out=lambda line: None, **kwargs,
    )


def available_at(database: Database) -> list[tuple[str, Any]]:
    values = []
    for connection in database.connections:
        for statement in connection.statements:
            params = statement.compile(dialect=postgresql.dialect()).params
            values.extend(sorted((name, value) for name, value in params.items() if name.startswith("available_at")))
    return values


def interrupted_after_commit(*args: Any, **kwargs: Any) -> None:
    raise RuntimeError("interrupted after the commit")


def run_interrupted(store: run.EvidenceStore, ctx: run.RunContext, source: str, unit: str) -> None:
    store.complete = interrupted_after_commit  # type: ignore[method-assign]
    try:
        with pytest.raises(RuntimeError):
            run.run_unit(ctx, source, unit)
    finally:
        del store.complete


def prepared_files(store: run.EvidenceStore, source: str, unit: str) -> dict[str, bytes]:
    files = unit_files(store, source, unit)
    assert "DONE.json" not in files
    return {name: data for name, data in files.items() if name != "PREPARED.json"}


def coinglass_run_world() -> FakeTransport:
    first, second = date(2024, 1, 11), date(2024, 2, 1)
    transport = FakeTransport()
    days = {first: {"IBIT": 5, "GBTC": -7}, second: {"IBIT": 6}, date(2026, 1, 5): {"IBIT": 777000001}}
    transport.add(coinglass.FLOW_HISTORY_URL, fx.coinglass_flow_page(days))
    transport.add(coinglass.fund_history_url("IBIT"), fx.coinglass_fund_page({first: 9, second: 10, date(2026, 1, 5): 777000002}))
    transport.add(coinglass.fund_history_url("GBTC"), fx.coinglass_fund_page({date(2019, 6, 3): 777000003, first: 11}, ticker="GBTC"))
    return transport


def test_review_b3_an_etf_unit_interrupted_after_its_commit_resumes_from_its_projections(store: run.EvidenceStore) -> None:
    keyed = {"allow_coinglass": True, "coinglass_key": "key-123"}
    database = Database()
    run_interrupted(store, advancing_context(coinglass_run_world(), store, database, **keyed), "coinglass-etf", "all")
    committed = available_at(database)
    assert committed and store.done("coinglass-etf", "all") is None
    assert set(store.prepared("coinglass-etf", "all")[0]) == {"run_version", "source", "unit", "files"}  # no persistence claim (BR1)
    before = prepared_files(store, "coinglass-etf", "all")
    later, database_again = FakeTransport(), Database()  # serves nothing: a fresh read would be refused
    report_ = run.run_unit(advancing_context(later, store, database_again, start=LATER, **keyed), "coinglass-etf", "all")
    assert report_.status == "DONE", report_.detail
    assert later.calls == [] and available_at(database_again) == committed  # the same keys: insert-or-ignore adds nothing
    after = unit_files(store, "coinglass-etf", "all")
    assert {name: data for name, data in after.items() if name != "DONE.json"} == before and "PREPARED.json" not in after
    assert json.loads(after["DONE.json"])["persisted"]["etf_flows"] == 3


def test_review_b3_a_derivative_unit_interrupted_after_its_commit_is_read_again_with_its_instants(store: run.EvidenceStore) -> None:
    database = Database()
    run_interrupted(store, advancing_context(funding_world(), store, database), "binance-funding", "2020-02")
    committed = available_at(database)
    before = prepared_files(store, "binance-funding", "2020-02")
    transport, database_again = funding_world(), Database()
    report_ = run.run_unit(advancing_context(transport, store, database_again, start=LATER), "binance-funding", "2020-02")
    assert report_.status == "DONE", report_.detail
    assert len(transport.calls) == 2 and available_at(database_again) == committed
    after = unit_files(store, "binance-funding", "2020-02")
    assert {name: data for name, data in after.items() if name != "DONE.json"} == before


def test_review_b3_a_changed_response_or_a_no_persist_run_never_completes_a_persisting_runs_unit(store: run.EvidenceStore) -> None:
    run_interrupted(store, advancing_context(funding_world(), store, Database()), "binance-funding", "2020-02")
    changed = FakeTransport()
    rows = [fx.funding_row(utc(2020, 2, day, hour), rate="0.000777000007") for day in (1, 2) for hour in (0, 8, 16)]
    fx.add_archive(changed, binance.funding_archive_url(date(2020, 2, 1)), rows)
    database = Database()
    report_ = run.run_unit(advancing_context(changed, store, database, start=LATER), "binance-funding", "2020-02")
    assert report_.status == "REFUSED" and "reconcile" in report_.detail and database.connections == []
    transport = funding_world()
    report_ = run.run_unit(advancing_context(transport, store, None, start=LATER), "binance-funding", "2020-02")
    assert report_.status == "REFUSED" and transport.calls == []
    assert store.prepared("binance-funding", "2020-02") is not None and store.done("binance-funding", "2020-02") is None


def test_review_br1_a_unit_prepared_without_persistence_is_resumed_never_read_afresh(store: run.EvidenceStore) -> None:
    # owner BR1 decision: a prepared unit may be persisted whichever run prepared it (B3 had it read afresh)
    run_interrupted(store, advancing_context(funding_world(), store, None), "binance-funding", "2020-02")
    before = prepared_files(store, "binance-funding", "2020-02")
    transport = funding_world()
    report_ = run.run_unit(advancing_context(transport, store, None, start=LATER), "binance-funding", "2020-02")
    assert report_.status == "REFUSED" and "reconcile" not in report_.detail and transport.calls == []
    database = Database()
    report_ = run.run_unit(advancing_context(funding_world(), store, database, start=LATER), "binance-funding", "2020-02")
    assert report_.status == "DONE", report_.detail
    assert available_at(database) and all(value < LATER for _, value in available_at(database))  # the prepared read's instants
    assert {name: data for name, data in unit_files(store, "binance-funding", "2020-02").items() if name != "DONE.json"} == before


def test_review_b3_a_prepared_marker_that_does_not_verify_is_refused(store: run.EvidenceStore) -> None:
    run_interrupted(store, advancing_context(funding_world(), store, Database()), "binance-funding", "2020-02")
    (store.unit_dir("binance-funding", "2020-02") / "summary.json").write_bytes(b"{}")
    transport = funding_world()
    report_ = run.run_unit(advancing_context(transport, store, Database(), start=LATER), "binance-funding", "2020-02")
    assert report_.status == "REFUSED" and "PREPARED" in report_.detail and transport.calls == []


def test_review_b3_a_coinglass_rebuild_must_reproduce_every_exposure_record(store: run.EvidenceStore) -> None:
    keyed = {"allow_coinglass": True, "coinglass_key": "key-123"}
    run_interrupted(store, advancing_context(coinglass_run_world(), store, Database(), **keyed), "coinglass-etf", "all")
    files = prepared_files(store, "coinglass-etf", "all")
    ctx = advancing_context(FakeTransport(), store, Database(), **keyed)
    assert run.coinglass_resume(ctx, "all", files).summary == json.loads(files["summary.json"])
    summary = json.loads(files["summary.json"])
    # what the bytes prove: the rule, their digest and size, the count kept, the date members and the days
    # (the record's own instants and the full response's digest are bound by PREPARED.json's digest of the summary)
    for index, edit in (
        (1, {"rule": "OTHER"}), (1, {"projected_sha256": "0" * 64}), (1, {"projected_size": 1}), (1, {"kept": 3}),
        (1, {"date_keys": ["assets_date"]}), (1, {"first_day": "2024-01-12"}), (1, {"retrieved_at": "yesterday"}),
        (2, {"last_day": "2024-01-31"}),  # IBIT keeps 2024-02-01
    ):
        edited = json.loads(files["summary.json"])
        edited["projections"][index] |= edit
        with pytest.raises(BackfillRefused):
            run.coinglass_resume(ctx, "all", files | {"summary.json": json.dumps(edited).encode()})
    for drop in ("history_IBIT.projected.json", "flow_history.projected.json"):
        refused("PROVIDER_REQUEST_MISMATCH", run.coinglass_resume, ctx, "all", {k: v for k, v in files.items() if k != drop})
    one_fund = dict(summary, projections=summary["projections"][:2])
    refused("PROVIDER_REQUEST_MISMATCH", run.coinglass_resume, ctx, "all", files | {"summary.json": json.dumps(one_fund).encode()})
    refused("PROVIDER_REQUEST_MISMATCH", run.coinglass_resume, advancing_context(FakeTransport(), store), "all", files)  # the gate


# --- review BR1: no marker's claim sends a unit that may be persisted to a fresh read ----------------


KEYED = {"allow_coinglass": True, "coinglass_key": "key-123"}


def changed_coinglass_world() -> FakeTransport:
    transport = coinglass_run_world()
    transport.add(coinglass.FLOW_HISTORY_URL, fx.coinglass_flow_page({date(2024, 1, 11): {"IBIT": 999}}))
    return transport


def insert_params(database: Database) -> list[dict[str, Any]]:
    """Every persisted parameter but the persistence instant: the rows, their values and their keys."""

    return [
        {name: value for name, value in statement.compile(dialect=postgresql.dialect()).params.items() if not name.startswith("ingested_at")}
        for connection in database.connections
        for statement in connection.statements
    ]


@pytest.mark.parametrize("persisting", [True, False])
def test_review_br1_a_prepared_marker_edited_to_claim_no_persistence_does_not_verify(store: run.EvidenceStore, persisting: bool) -> None:
    # the re-review's reproducer: an ETF unit interrupted after its commit, its marker then edited to claim no persistence
    run_interrupted(store, advancing_context(coinglass_run_world(), store, Database(), **KEYED), "coinglass-etf", "all")
    marker = store.unit_dir("coinglass-etf", "all") / "PREPARED.json"
    record = json.loads(marker.read_bytes())
    marker.write_bytes(sources.canonical_json_bytes(record | {"persisting": False}))
    changed = changed_coinglass_world()
    database = Database() if persisting else None
    report_ = run.run_unit(advancing_context(changed, store, database, start=LATER, **KEYED), "coinglass-etf", "all")
    assert report_.status == "REFUSED" and "PREPARED" in report_.detail and changed.calls == []
    assert (database is None or database.connections == []) and store.done("coinglass-etf", "all") is None


def test_review_br1_a_no_persist_run_refuses_a_prepared_etf_unit_and_a_persisting_run_resumes_it(store: run.EvidenceStore) -> None:
    database = Database()
    run_interrupted(store, advancing_context(coinglass_run_world(), store, database, **KEYED), "coinglass-etf", "all")
    committed = insert_params(database)
    changed = changed_coinglass_world()
    report_ = run.run_unit(advancing_context(changed, store, None, start=LATER, **KEYED), "coinglass-etf", "all")
    assert report_.status == "REFUSED" and changed.calls == [] and store.done("coinglass-etf", "all") is None
    database_again = Database()
    report_ = run.run_unit(advancing_context(changed, store, database_again, start=LATER, **KEYED), "coinglass-etf", "all")
    assert report_.status == "DONE" and changed.calls == [] and insert_params(database_again) == committed


def test_review_br1_a_completed_etf_unit_edited_to_look_unpersisted_is_resumed_not_read_afresh(store: run.EvidenceStore) -> None:
    database = Database()
    assert run.run_unit(advancing_context(coinglass_run_world(), store, database, **KEYED), "coinglass-etf", "all").status == "DONE"
    committed = insert_params(database)
    before = {name: data for name, data in unit_files(store, "coinglass-etf", "all").items() if name != "DONE.json"}
    rewrite_marker(store, "coinglass-etf", "all", done_marker(store, "coinglass-etf", "all") | {"persisted": run.NOT_PERSISTED})
    changed, database_again = changed_coinglass_world(), Database()
    report_ = run.run_unit(advancing_context(changed, store, database_again, start=LATER, **KEYED), "coinglass-etf", "all")
    assert report_.status == "DONE", report_.detail
    assert changed.calls == [] and insert_params(database_again) == committed  # the same rows and keys: nothing new
    after = unit_files(store, "coinglass-etf", "all")
    assert {name: data for name, data in after.items() if name != "DONE.json"} == before
    assert json.loads(after["DONE.json"])["persisted"]["etf_flows"] == 3


def test_review_br1_a_derivative_unit_completed_without_persistence_is_resumed_with_its_instants(store: run.EvidenceStore) -> None:
    assert run.run_unit(advancing_context(funding_world(), store, None), "binance-funding", "2020-02").status == "DONE"
    before = {name: data for name, data in unit_files(store, "binance-funding", "2020-02").items() if name != "DONE.json"}
    changed = FakeTransport()
    rows = [fx.funding_row(utc(2020, 2, day, hour), rate="0.000777000007") for day in (1, 2) for hour in (0, 8, 16)]
    fx.add_archive(changed, binance.funding_archive_url(date(2020, 2, 1)), rows)
    database = Database()
    report_ = run.run_unit(advancing_context(changed, store, database, start=LATER), "binance-funding", "2020-02")
    assert report_.status == "REFUSED" and "reconcile" in report_.detail and database.connections == []
    assert store.done("binance-funding", "2020-02")["persisted"] == run.NOT_PERSISTED  # left as it was
    report_ = run.run_unit(advancing_context(funding_world(), store, database, start=LATER), "binance-funding", "2020-02")
    assert report_.status == "DONE" and available_at(database) and all(value < LATER for _, value in available_at(database))
    after = unit_files(store, "binance-funding", "2020-02")
    assert {name: data for name, data in after.items() if name != "DONE.json"} == before and "PREPARED.json" not in after


def test_review_br1_a_reopened_unit_keeps_a_marker_through_any_interruption(store: run.EvidenceStore, monkeypatch: pytest.MonkeyPatch) -> None:
    assert run.run_unit(advancing_context(funding_world(), store, None), "binance-funding", "2020-02").status == "DONE"
    directory = store.unit_dir("binance-funding", "2020-02")
    done_bytes = (directory / "DONE.json").read_bytes()
    write = run._atomic_write

    def interrupted_marker(path: Path, data: bytes) -> None:
        if path.name == "PREPARED.json":
            raise OSError("interrupted before the marker")
        write(path, data)

    with monkeypatch.context() as patch:
        patch.setattr(run, "_atomic_write", interrupted_marker)
        with pytest.raises(OSError):
            store.reopen("binance-funding", "2020-02")
    assert (directory / "DONE.json").read_bytes() == done_bytes  # DONE.json is dropped only once PREPARED.json is written
    store.reopen("binance-funding", "2020-02")
    assert store.prepared("binance-funding", "2020-02")[0]["files"] == json.loads(done_bytes)["files"] and not (directory / "DONE.json").exists()
    (directory / "DONE.json").write_bytes(done_bytes)  # as if interrupted between its two steps
    transport = funding_world()
    report_ = run.run_unit(advancing_context(transport, store, None, start=LATER), "binance-funding", "2020-02")
    assert report_.status == "REFUSED" and "only a persisting run" in report_.detail and transport.calls == []  # review BR5
    database = Database()
    run_interrupted(store, advancing_context(funding_world(), store, database, start=LATER), "binance-funding", "2020-02")
    committed = available_at(database)
    assert committed and all(value < LATER for _, value in committed) and store.prepared("binance-funding", "2020-02") is not None
    assert (directory / "DONE.json").read_bytes() == done_bytes  # still beside PREPARED.json, its claim now stale
    report_ = run.run_unit(advancing_context(funding_world(), store, None, start=LATER), "binance-funding", "2020-02")
    assert report_.status == "REFUSED" and "only a persisting run" in report_.detail
    database_again = Database()
    report_ = run.run_unit(advancing_context(funding_world(), store, database_again, start=LATER + timedelta(hours=1)), "binance-funding", "2020-02")
    assert report_.status == "DONE" and available_at(database_again) == committed
    assert store.done("binance-funding", "2020-02")["persisted"] == {"funding_rates": 6} and store.prepared("binance-funding", "2020-02") is None
    refused("PROVIDER_REQUEST_MISMATCH", store.reopen, "binance-funding", "2020-02")  # persisted: never reopened
    refused("PROVIDER_REQUEST_MISMATCH", store.reopen, "binance-funding", "2020-03")  # nothing completed


# --- review BR5: a not_persisted completion is trusted only without a PREPARED.json beside it -------


@pytest.mark.parametrize("prepared", ["verifying", "not-verifying"])
def test_review_br5_a_restored_no_persist_done_cannot_override_a_committed_preparation(store: run.EvidenceStore, prepared: str) -> None:
    # the re-review's reproducer: a --no-persist completion, reopened and committed by a persisting run
    # interrupted before its completion, then the old DONE.json restored beside PREPARED.json
    assert run.run_unit(advancing_context(coinglass_run_world(), store, None, **KEYED), "coinglass-etf", "all").status == "DONE"
    directory = store.unit_dir("coinglass-etf", "all")
    done_bytes = (directory / "DONE.json").read_bytes()
    database = Database()
    run_interrupted(store, advancing_context(changed_coinglass_world(), store, database, start=LATER, **KEYED), "coinglass-etf", "all")
    committed = insert_params(database)
    assert committed and store.prepared("coinglass-etf", "all") is not None and not (directory / "DONE.json").exists()
    (directory / "DONE.json").write_bytes(done_bytes)
    if prepared == "not-verifying":
        (directory / "PREPARED.json").write_bytes(b"{")
    changed = changed_coinglass_world()
    report_ = run.run_unit(advancing_context(changed, store, None, start=LATER + timedelta(hours=1), **KEYED), "coinglass-etf", "all")
    assert report_.status == "REFUSED" and changed.calls == []
    assert (directory / "DONE.json").read_bytes() == done_bytes  # left as it was
    database_again = Database()
    report_ = run.run_unit(advancing_context(changed, store, database_again, start=LATER + timedelta(hours=1), **KEYED), "coinglass-etf", "all")
    if prepared == "not-verifying":
        assert report_.status == "REFUSED" and "reconcile" in report_.detail and database_again.connections == []
    else:
        assert report_.status == "DONE" and changed.calls == [] and insert_params(database_again) == committed  # the prepared read
        assert store.done("coinglass-etf", "all")["persisted"]["etf_flows"] == 3 and store.prepared("coinglass-etf", "all") is None


def test_review_br5_a_no_persist_completion_alone_is_still_skipped_by_a_no_persist_run(store: run.EvidenceStore) -> None:
    assert run.run_unit(advancing_context(coinglass_run_world(), store, None, **KEYED), "coinglass-etf", "all").status == "DONE"
    transport = FakeTransport()
    assert run.run_unit(advancing_context(transport, store, None, start=LATER, **KEYED), "coinglass-etf", "all").status == "SKIPPED"
    assert transport.calls == []


@pytest.mark.parametrize("marker", ["PREPARED.json", "DONE.json"])
def test_review_br1_an_etf_unit_whose_marker_was_removed_is_refused_not_read_afresh(store: run.EvidenceStore, marker: str) -> None:
    ctx = advancing_context(coinglass_run_world(), store, Database(), **KEYED)
    if marker == "PREPARED.json":
        run_interrupted(store, ctx, "coinglass-etf", "all")
    else:
        assert run.run_unit(ctx, "coinglass-etf", "all").status == "DONE"
    (store.unit_dir("coinglass-etf", "all") / marker).unlink()
    for database in (Database(), None):
        changed = changed_coinglass_world()
        report_ = run.run_unit(advancing_context(changed, store, database, start=LATER, **KEYED), "coinglass-etf", "all")
        assert report_.status == "REFUSED" and "reconcile" in report_.detail and changed.calls == []
        assert database is None or database.connections == []


def test_review_br3_only_a_unit_of_a_persisting_source_without_a_directory_is_read_afresh(store: run.EvidenceStore) -> None:
    directory = store.unit_dir("binance-funding", "2020-02")
    directory.mkdir(parents=True)
    (directory / "summary.json.partial").write_bytes(b"{")  # an interrupted first write
    for emptied in (False, True):
        if emptied:
            (directory / "summary.json.partial").unlink()  # an empty directory is not a new unit (review BR3)
        for database in (Database(), None):
            transport = funding_world()
            report_ = run.run_unit(advancing_context(transport, store, database), "binance-funding", "2020-02")
            assert report_.status == "REFUSED" and "reconcile" in report_.detail and transport.calls == []
            assert database is None or database.connections == []
    directory.rmdir()  # the operator's reconciliation
    assert run.run_unit(advancing_context(funding_world(), store, Database()), "binance-funding", "2020-02").status == "DONE"


# --- review BR3: emptying a unit's directory never makes it new ------------------------------


@pytest.mark.parametrize("state", ["prepared", "done"])
def test_review_br3_an_etf_unit_emptied_but_its_directory_kept_is_refused_not_read_afresh(store: run.EvidenceStore, state: str) -> None:
    ctx = advancing_context(coinglass_run_world(), store, Database(), **KEYED)
    if state == "prepared":
        run_interrupted(store, ctx, "coinglass-etf", "all")  # committed, then interrupted
    else:
        assert run.run_unit(ctx, "coinglass-etf", "all").status == "DONE"
    directory = store.unit_dir("coinglass-etf", "all")
    for path in directory.iterdir():
        path.unlink()
    for database in (Database(), None):
        changed = changed_coinglass_world()
        report_ = run.run_unit(advancing_context(changed, store, database, start=LATER, **KEYED), "coinglass-etf", "all")
        assert report_.status == "REFUSED" and "reconcile" in report_.detail and changed.calls == []
        assert database is None or database.connections == []
    assert directory.is_dir() and list(directory.iterdir()) == []  # left as it was


def test_review_br3_an_interruption_before_a_units_first_file_refuses_until_its_directory_is_removed(
    store: run.EvidenceStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    def interrupted(path: Path, data: bytes) -> None:
        raise OSError("interrupted before the unit's first file")

    database = Database()
    with monkeypatch.context() as patch:
        patch.setattr(run, "_atomic_write", interrupted)
        with pytest.raises(OSError):
            run.run_unit(advancing_context(funding_world(), store, database), "binance-funding", "2020-02")
    directory = store.unit_dir("binance-funding", "2020-02")
    assert directory.is_dir() and list(directory.iterdir()) == [] and database.connections == []  # nothing persisted
    for again in (Database(), None):
        transport = funding_world()
        report_ = run.run_unit(advancing_context(transport, store, again, start=LATER), "binance-funding", "2020-02")
        assert report_.status == "REFUSED" and "reconcile" in report_.detail and transport.calls == []
    directory.rmdir()  # the operator's reconciliation
    again = Database()
    assert run.run_unit(advancing_context(funding_world(), store, again, start=LATER), "binance-funding", "2020-02").status == "DONE"
    assert store.done("binance-funding", "2020-02")["persisted"] == {"funding_rates": 6}


def test_review_br3_a_source_that_persists_nothing_reads_an_empty_unit_afresh(store: run.EvidenceStore) -> None:
    store.unit_dir("kraken-incidents", "all").mkdir(parents=True)
    transport = FakeTransport()
    transport.add(run.TARDIS_EXCHANGE_URL, tardis_body())
    assert run.run_unit(advancing_context(transport, store, None), "kraken-incidents", "all").status == "DONE"
    assert len(transport.calls) == 1 and store.done("kraken-incidents", "all")["persisted"] == {}


def test_review_br1_a_source_that_persists_nothing_is_read_afresh_whatever_it_holds(store: run.EvidenceStore) -> None:
    transport = FakeTransport()
    transport.add(run.TARDIS_EXCHANGE_URL, tardis_body())
    run_interrupted(store, advancing_context(transport, store, Database()), "kraken-incidents", "all")
    assert store.prepared("kraken-incidents", "all") is not None and len(transport.calls) == 1
    assert run.run_unit(advancing_context(transport, store, None, start=LATER), "kraken-incidents", "all").status == "DONE"
    (store.unit_dir("kraken-incidents", "all") / "DONE.json").unlink()
    assert run.run_unit(advancing_context(transport, store, Database(), start=LATER), "kraken-incidents", "all").status == "DONE"
    assert len(transport.calls) == 3 and store.done("kraken-incidents", "all")["persisted"] == {}


# --- review BR2: a completed CoinGlass unit binds every projection its summary records ----------------


ETF_PROJECTIONS = {"flow_history.projected.json", "history_GBTC.projected.json", "history_IBIT.projected.json"}


def completed_etf_unit(store: run.EvidenceStore) -> dict[str, Any]:
    assert run.run_unit(advancing_context(coinglass_run_world(), store, Database(), **KEYED), "coinglass-etf", "all").status == "DONE"
    marker = done_marker(store, "coinglass-etf", "all")
    assert {name for name, _, _ in run.coinglass_evidence(store.completed("coinglass-etf", "all")[1])} == ETF_PROJECTIONS <= set(marker["files"])
    return marker


@pytest.mark.parametrize("dropped", sorted(ETF_PROJECTIONS))
def test_review_br2_a_completed_etf_unit_missing_a_recorded_projection_is_refused(store: run.EvidenceStore, dropped: str) -> None:
    # the re-review's reproducer: a projection file deleted with only its entry in DONE.json
    marker = completed_etf_unit(store)
    (store.unit_dir("coinglass-etf", "all") / dropped).unlink()
    rewrite_marker(store, "coinglass-etf", "all", marker | {"files": {k: v for k, v in marker["files"].items() if k != dropped}})
    assert store.completed("coinglass-etf", "all") is not None  # the marker itself verifies
    for database in (Database(), None):
        changed = changed_coinglass_world()
        report_ = run.run_unit(advancing_context(changed, store, database, start=LATER, **KEYED), "coinglass-etf", "all")
        assert report_.status == "REFUSED" and "evidence" in report_.detail and changed.calls == []
        assert database is None or database.connections == []


def test_review_br2_a_completed_etf_units_summary_must_record_its_projections(store: run.EvidenceStore) -> None:
    marker = completed_etf_unit(store)
    directory = store.unit_dir("coinglass-etf", "all")
    summary = json.loads((directory / "summary.json").read_bytes())
    for edited in ({k: v for k, v in summary.items() if k != "projections"}, summary | {"projections": []}, summary | {"projections": [1]}):
        data = sources.canonical_json_bytes(edited)
        (directory / "summary.json").write_bytes(data)
        rewrite_marker(store, "coinglass-etf", "all", marker | {"files": marker["files"] | {"summary.json": sources.sha256_hex(data)}})
        changed = changed_coinglass_world()
        report_ = run.run_unit(advancing_context(changed, store, Database(), start=LATER, **KEYED), "coinglass-etf", "all")
        assert report_.status == "REFUSED" and "projection records" in report_.detail and changed.calls == [], edited
    refused("PROVIDER_REQUEST_MISMATCH", run.coinglass_evidence, {"summary.json": b"{not json"})


# --- review BR4: each projection a completed CoinGlass unit records must match its exposure record -----


def no_decoding(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail on any value parser or rebuild; a projection's metadata (``_projection_from_exposure``) may be read (review BR6)."""

    def decoded(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("a completion check decoded a projection")

    monkeypatch.setattr(coinglass, "parse_flow_history", decoded)
    monkeypatch.setattr(coinglass, "parse_fund_history", decoded)
    monkeypatch.setattr(coinglass, "etf_flows_from_projections", decoded)


def substitute(store: run.EvidenceStore, marker: dict[str, Any], replaced: dict[str, bytes]) -> None:
    directory = store.unit_dir("coinglass-etf", "all")
    for name, data in replaced.items():
        (directory / name).write_bytes(data)
    rewrite_marker(store, "coinglass-etf", "all", marker | {"files": marker["files"] | {name: sources.sha256_hex(data) for name, data in replaced.items()}})
    assert store.completed("coinglass-etf", "all") is not None  # the marker itself verifies


@pytest.mark.parametrize("case", ["copied-fund", "swapped-funds", "replaced-flow"])
def test_review_br4_a_completed_etf_unit_with_a_substituted_projection_is_refused(
    store: run.EvidenceStore, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    # the re-review's reproducer: a projection replaced, only its digest in DONE.json updated, the summary unchanged
    marker = completed_etf_unit(store)
    saved = unit_files(store, "coinglass-etf", "all")
    ibit, gbtc = (saved[f"history_{fund}.projected.json"] for fund in ("IBIT", "GBTC"))
    replaced = {
        "copied-fund": {"history_IBIT.projected.json": gbtc},
        "swapped-funds": {"history_IBIT.projected.json": gbtc, "history_GBTC.projected.json": ibit},
        "replaced-flow": {"flow_history.projected.json": ibit},
    }[case]
    assert all(saved[name] != data for name, data in replaced.items())
    substitute(store, marker, replaced)
    no_decoding(monkeypatch)
    for database in (Database(), None):
        changed = changed_coinglass_world()
        report_ = run.run_unit(advancing_context(changed, store, database, start=LATER, **KEYED), "coinglass-etf", "all")
        assert report_.status == "REFUSED" and "does not match the record" in report_.detail and changed.calls == []
        assert database is None or database.connections == []


RECORD_EDITS = {
    "other-digest": ("projected_sha256", lambda record: "0" * 64),
    "other-size": ("projected_size", lambda record: record["projected_size"] + 1),
    "float-size": ("projected_size", lambda record: float(record["projected_size"])),  # equal in value, not an integer
    "string-size": ("projected_size", lambda record: str(record["projected_size"])),
    "boolean-size": ("projected_size", lambda record: True),
}


@pytest.mark.parametrize("edit", sorted(RECORD_EDITS))
def test_review_br4_a_completed_etf_units_summary_must_record_each_projections_digest_and_size(
    store: run.EvidenceStore, monkeypatch: pytest.MonkeyPatch, edit: str
) -> None:
    marker = completed_etf_unit(store)
    directory = store.unit_dir("coinglass-etf", "all")
    summary = json.loads((directory / "summary.json").read_bytes())
    field, value = RECORD_EDITS[edit]
    summary["projections"][1] = summary["projections"][1] | {field: value(summary["projections"][1])}
    substitute(store, marker, {"summary.json": sources.canonical_json_bytes(summary)})
    no_decoding(monkeypatch)
    changed = changed_coinglass_world()
    report_ = run.run_unit(advancing_context(changed, store, Database(), start=LATER, **KEYED), "coinglass-etf", "all")
    assert report_.status == "REFUSED" and "does not match the record" in report_.detail and changed.calls == []


def test_review_br4_an_intact_completed_etf_unit_is_skipped_without_decoding_a_projection(
    store: run.EvidenceStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    completed_etf_unit(store)
    no_decoding(monkeypatch)
    for database in (Database(), None):
        transport = FakeTransport()
        report_ = run.run_unit(advancing_context(transport, store, database, start=LATER, **KEYED), "coinglass-etf", "all")
        assert report_.status == "SKIPPED" and transport.calls == [] and (database is None or database.connections == [])


# --- review BR6: a CoinGlass unit's projection records are proven value-blind, complete and consistent ---


def _edit_records(summary: dict[str, Any], edit: str) -> list[str]:
    """Edit a CoinGlass summary as the re-review's probes did; return the files removed with it."""

    records = summary["projections"]
    if edit == "omit-fund":  # IBIT's record, file and binding removed; tickers_seen unchanged
        summary["projections"] = [item for item in records if item["url"] != coinglass.fund_history_url("IBIT")]
        return ["history_IBIT.projected.json"]
    if edit == "fund-url-first":
        records[0]["url"] = coinglass.fund_history_url("IBIT")
    elif edit == "foreign-url-first":
        records[0]["url"] = "https://outside.invalid/projection"
    elif edit == "duplicate-fund":
        records.append(dict(records[1]))
    elif edit == "funds-out-of-order":
        records[1:] = records[:0:-1]
    elif edit == "kept-mismatch":
        records[2]["kept"] = 0
    elif edit == "date-proof-mismatch":
        records[2]["date_keys"] = ["assets_date"]
    elif edit == "day-span-narrowed":
        records[2]["last_day"] = "2024-01-11"
    elif edit == "day-span-widened":  # inside the window and the bytes still re-project: only the unit's days refuse it
        records[2]["first_day"] = "2024-01-02"
    elif edit == "day-span-into-holdout":
        records[2]["last_day"] = "2026-06-30"
    elif edit == "flow-kept-mismatch":
        records[0]["kept"] = 0
    elif edit == "flow-date-proof-mismatch":
        records[0]["date_keys"] = list(coinglass.FUND_DATE_KEYS)
    elif edit == "rule-mismatch":
        records[0]["rule"] = "OTHER"
    elif edit == "float-kept":
        records[1]["kept"] = float(records[1]["kept"])
    elif edit == "boolean-dropped":
        records[1]["dropped_holdout"] = True
    elif edit == "census-extra-fund":
        summary["tickers_seen"] = sorted([*summary["tickers_seen"], "ARKB"])
    elif edit == "census-unsorted":
        summary["tickers_seen"] = summary["tickers_seen"][::-1]
    elif edit == "census-duplicated":
        summary["tickers_seen"] = [*summary["tickers_seen"], summary["tickers_seen"][-1]]
    elif edit == "census-missing":
        del summary["tickers_seen"]
    elif edit == "funds-and-census-reversed":  # consistent with each other, but not the read's sorted order
        records[1:] = records[:0:-1]
        summary["tickers_seen"] = summary["tickers_seen"][::-1]
    elif edit == "fund-and-census-duplicated":  # consistent with each other, but a fund twice
        records.append(dict(records[-1]))
        summary["tickers_seen"] = [*summary["tickers_seen"], summary["tickers_seen"][-1]]
    elif edit == "non-text-digest":
        records[1]["response_sha256"] = 12345
    else:
        raise AssertionError(edit)
    return []


BR6_EDITS = [
    "omit-fund", "fund-url-first", "foreign-url-first", "duplicate-fund", "funds-out-of-order", "kept-mismatch",
    "date-proof-mismatch", "day-span-narrowed", "day-span-widened", "rule-mismatch", "float-kept", "boolean-dropped",
    "census-extra-fund", "census-unsorted", "census-duplicated", "census-missing", "funds-and-census-reversed",
    "fund-and-census-duplicated", "non-text-digest", "day-span-into-holdout", "flow-kept-mismatch", "flow-date-proof-mismatch",
]


def edited_unit(store: run.EvidenceStore, marker_name: str, edit: str) -> None:
    directory = store.unit_dir("coinglass-etf", "all")
    marker = json.loads((directory / marker_name).read_bytes())
    summary = json.loads((directory / "summary.json").read_bytes())
    assert summary["tickers_seen"] == ["GBTC", "IBIT"] and len(summary["projections"]) == 3
    for name in _edit_records(summary, edit):
        (directory / name).unlink()
        del marker["files"][name]
    data = sources.canonical_json_bytes(summary)
    (directory / "summary.json").write_bytes(data)
    marker["files"]["summary.json"] = sources.sha256_hex(data)
    (directory / marker_name).write_bytes(sources.canonical_json_bytes(marker))


@pytest.mark.parametrize("edit", BR6_EDITS)
def test_review_br6_a_completed_etf_unit_must_declare_its_projections_completely_and_consistently(
    store: run.EvidenceStore, monkeypatch: pytest.MonkeyPatch, edit: str
) -> None:
    # the re-review's reproducers and their kin: the summary edited, its digest in DONE.json updated
    completed_etf_unit(store)
    edited_unit(store, "DONE.json", edit)
    assert store.completed("coinglass-etf", "all") is not None  # the marker itself verifies
    no_decoding(monkeypatch)
    for database in (Database(), None):
        transport = FakeTransport()
        report_ = run.run_unit(advancing_context(transport, store, database, start=LATER, **KEYED), "coinglass-etf", "all")
        assert report_.status == "REFUSED" and transport.calls == [], (edit, report_)
        assert database is None or database.connections == []


@pytest.mark.parametrize("edit", ["omit-fund", "day-span-widened", "float-kept", "census-extra-fund"])
def test_review_br6_a_prepared_etf_unit_is_proven_before_its_rebuild_decodes_anything(
    store: run.EvidenceStore, monkeypatch: pytest.MonkeyPatch, edit: str
) -> None:
    database = Database()
    run_interrupted(store, advancing_context(coinglass_run_world(), store, database, **KEYED), "coinglass-etf", "all")
    edited_unit(store, "PREPARED.json", edit)
    assert store.prepared("coinglass-etf", "all") is not None
    no_decoding(monkeypatch)
    again, transport = Database(), FakeTransport()
    report_ = run.run_unit(advancing_context(transport, store, again, start=LATER, **KEYED), "coinglass-etf", "all")
    assert report_.status == "REFUSED" and transport.calls == [] and again.connections == [], (edit, report_)


def test_review_br6_the_proof_accepts_every_unit_the_code_completes_and_decodes_nothing(
    store: run.EvidenceStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    completed_etf_unit(store)
    files = store.completed("coinglass-etf", "all")[1]
    no_decoding(monkeypatch)
    projections = run.coinglass_proven(files)
    assert [item.url for item in projections] == [coinglass.FLOW_HISTORY_URL, *(coinglass.fund_history_url(t) for t in ("GBTC", "IBIT"))]
    assert all((item.first_day, item.last_day) == (run.ETF_FIRST_DAY, run.LAST_DATA_DAY) for item in projections)


# --- review BR7: a CoinGlass unit's projection records must be the reads its retrieval log records ----------


BR7_REFUSAL = "one successful read per projection record"


def _moved(instant: str) -> str:
    return sources.iso(datetime.fromisoformat(instant) + timedelta(hours=1))


def _edit_log(summary: dict[str, Any], log: list[dict[str, Any]], edit: str) -> list[str]:
    """Edit a CoinGlass summary's records or its retrieval log as the re-review's probes did; return the files removed with it."""

    records = summary["projections"]
    if edit == "fund-instant-moved":  # the re-review's reproducer: IBIT's record an hour later, its retrieval unchanged
        records[2]["retrieved_at"] = _moved(records[2]["retrieved_at"])
    elif edit == "flow-instant-moved":
        records[0]["retrieved_at"] = _moved(records[0]["retrieved_at"])
    elif edit == "response-digest":
        records[1]["response_sha256"] = "0" * 64
    elif edit == "response-size":
        records[1]["response_size"] += 1
    elif edit == "fund-and-census-removed":  # IBIT's record, census entry, file and binding removed; its retrieval still logged
        assert records[2]["url"] == coinglass.fund_history_url("IBIT")
        summary["projections"], summary["tickers_seen"] = records[:2], ["GBTC"]
        return ["history_IBIT.projected.json"]
    elif edit == "log-instant-moved":
        log[2]["retrieved_at"] = _moved(log[2]["retrieved_at"])
    elif edit == "log-url":
        log[2]["url"] = coinglass.fund_history_url("ARKB")
    elif edit == "log-status":
        log[1]["status"] = 404
    elif edit == "log-missing":
        del log[-1]
    elif edit == "log-extra-attempt":  # a refused attempt before the read it records
        log.insert(1, log[1] | {"status": 429})
    elif edit == "log-reordered":
        log[1:] = log[:0:-1]
    elif edit == "log-float-size":
        log[1]["size"] = float(log[1]["size"])
    elif edit == "log-extra-field":
        log[1]["note"] = "retried"
    else:
        raise AssertionError(edit)
    return []


BR7_EDITS = [
    "fund-instant-moved", "flow-instant-moved", "response-digest", "response-size", "fund-and-census-removed",
    "log-instant-moved", "log-url", "log-status", "log-missing", "log-extra-attempt", "log-reordered", "log-float-size",
    "log-extra-field",
]


def br7_unit(store: run.EvidenceStore, marker_name: str, edit: str) -> None:
    directory = store.unit_dir("coinglass-etf", "all")
    marker = json.loads((directory / marker_name).read_bytes())
    summary = json.loads((directory / "summary.json").read_bytes())
    log = json.loads((directory / "retrievals.json").read_bytes())
    assert summary["tickers_seen"] == ["GBTC", "IBIT"] and len(summary["projections"]) == len(log) == 3
    for name in _edit_log(summary, log, edit):
        (directory / name).unlink()
        del marker["files"][name]
    for name, value in (("summary.json", summary), ("retrievals.json", log)):
        data = sources.canonical_json_bytes(value)
        (directory / name).write_bytes(data)
        marker["files"][name] = sources.sha256_hex(data)
    (directory / marker_name).write_bytes(sources.canonical_json_bytes(marker))


@pytest.mark.parametrize("edit", BR7_EDITS)
def test_review_br7_a_completed_etf_units_records_must_be_the_reads_its_retrieval_log_records(
    store: run.EvidenceStore, monkeypatch: pytest.MonkeyPatch, edit: str
) -> None:
    # the re-review's cases: the records or the log edited, their digests in DONE.json updated, every projection unchanged
    completed_etf_unit(store)
    br7_unit(store, "DONE.json", edit)
    assert store.completed("coinglass-etf", "all") is not None  # the marker itself verifies
    no_decoding(monkeypatch)
    for database in (Database(), None):
        transport = FakeTransport()
        report_ = run.run_unit(advancing_context(transport, store, database, start=LATER, **KEYED), "coinglass-etf", "all")
        assert report_.status == "REFUSED" and BR7_REFUSAL in report_.detail and transport.calls == [], (edit, report_)
        assert database is None or database.connections == []


@pytest.mark.parametrize("edit", ["fund-instant-moved", "flow-instant-moved", "log-instant-moved", "fund-and-census-removed", "log-missing"])
def test_review_br7_a_prepared_etf_unit_is_resumed_only_with_the_instants_its_log_records(
    store: run.EvidenceStore, monkeypatch: pytest.MonkeyPatch, edit: str
) -> None:
    # the re-review's reproducer: interrupted after its commit, IBIT's record an hour later, PREPARED.json's digest updated;
    # resumed, its rows would take another available_at, so another key
    database = Database()
    run_interrupted(store, advancing_context(coinglass_run_world(), store, database, **KEYED), "coinglass-etf", "all")
    assert available_at(database)
    br7_unit(store, "PREPARED.json", edit)
    assert store.prepared("coinglass-etf", "all") is not None
    no_decoding(monkeypatch)
    again, transport = Database(), FakeTransport()
    report_ = run.run_unit(advancing_context(transport, store, again, start=LATER, **KEYED), "coinglass-etf", "all")
    assert report_.status == "REFUSED" and BR7_REFUSAL in report_.detail, (edit, report_)
    assert transport.calls == [] and again.connections == [] and store.done("coinglass-etf", "all") is None


def test_review_br7_a_not_persisted_etf_unit_whose_records_disagree_with_its_log_is_neither_reopened_nor_skipped(
    store: run.EvidenceStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert run.run_unit(advancing_context(coinglass_run_world(), store, None, **KEYED), "coinglass-etf", "all").status == "DONE"
    br7_unit(store, "DONE.json", "fund-instant-moved")
    assert store.completed("coinglass-etf", "all") is not None
    no_decoding(monkeypatch)
    for database in (Database(), None):
        transport = FakeTransport()
        report_ = run.run_unit(advancing_context(transport, store, database, start=LATER, **KEYED), "coinglass-etf", "all")
        assert report_.status == "REFUSED" and BR7_REFUSAL in report_.detail and transport.calls == [], report_
        assert database is None or database.connections == []
    assert store.done("coinglass-etf", "all")["persisted"] == run.NOT_PERSISTED and store.prepared("coinglass-etf", "all") is None


@pytest.mark.parametrize("edit", BR6_EDITS)
def test_review_br7_each_br6_edit_is_refused_on_its_own_with_a_log_forged_to_match(
    store: run.EvidenceStore, monkeypatch: pytest.MonkeyPatch, edit: str
) -> None:
    # BR6's proof stands without the log check: the log is rewritten to the edited records, and the refusal is not the log's
    completed_etf_unit(store)
    edited_unit(store, "DONE.json", edit)
    directory = store.unit_dir("coinglass-etf", "all")
    marker = json.loads((directory / "DONE.json").read_bytes())
    records = json.loads((directory / "summary.json").read_bytes())["projections"]
    log = [
        {"url": item["url"], "retrieved_at": item["retrieved_at"], "status": 200, "size": item["response_size"], "sha256": item["response_sha256"]}
        for item in records
    ]
    data = sources.canonical_json_bytes(log)
    (directory / "retrievals.json").write_bytes(data)
    rewrite_marker(store, "coinglass-etf", "all", marker | {"files": marker["files"] | {"retrievals.json": sources.sha256_hex(data)}})
    assert store.completed("coinglass-etf", "all") is not None
    no_decoding(monkeypatch)
    for database in (Database(), None):
        transport = FakeTransport()
        report_ = run.run_unit(advancing_context(transport, store, database, start=LATER, **KEYED), "coinglass-etf", "all")
        assert report_.status == "REFUSED" and BR7_REFUSAL not in report_.detail and transport.calls == [], (edit, report_)
        assert database is None or database.connections == []


def coinglass_world_of(funds: tuple[str, ...]) -> FakeTransport:
    """A CoinGlass world of other funds and days than ``coinglass_run_world``'s: each fund flows on its own Thursday."""

    transport = FakeTransport()
    days = {date(2024, 1, 11) + timedelta(weeks=index): {fund: index + 1} for index, fund in enumerate(funds)}
    transport.add(coinglass.FLOW_HISTORY_URL, fx.coinglass_flow_page(days | {date(2026, 1, 5): {funds[0]: 777000001}}))
    for index, (day, fund) in enumerate(zip(days, funds, strict=True)):
        assets = {day: 100 + index, date(2025, 12, 31): 200 + index}
        transport.add(coinglass.fund_history_url(fund), fx.coinglass_fund_page(assets, ticker=fund))
    return transport


@pytest.mark.parametrize("funds", [("FBTC",), ("ARKB", "BITB", "FBTC", "IBIT")])
def test_review_br7_the_log_check_accepts_units_of_other_funds_and_days_resumed_or_completed(
    store: run.EvidenceStore, monkeypatch: pytest.MonkeyPatch, funds: tuple[str, ...]
) -> None:
    database = Database()
    run_interrupted(store, advancing_context(coinglass_world_of(funds), store, database, **KEYED), "coinglass-etf", "all")
    committed = available_at(database)
    assert committed and len(json.loads(prepared_files(store, "coinglass-etf", "all")["retrievals.json"])) == len(funds) + 1
    later, again = FakeTransport(), Database()
    report_ = run.run_unit(advancing_context(later, store, again, start=LATER, **KEYED), "coinglass-etf", "all")
    assert report_.status == "DONE" and later.calls == [] and available_at(again) == committed, report_.detail
    no_decoding(monkeypatch)
    for database_ in (Database(), None):
        transport = FakeTransport()
        report_ = run.run_unit(advancing_context(transport, store, database_, start=LATER, **KEYED), "coinglass-etf", "all")
        assert report_.status == "SKIPPED" and transport.calls == [], report_
    assert len(run.coinglass_proven(store.completed("coinglass-etf", "all")[1])) == len(funds) + 1


def test_rows_persist_in_monthly_slices_and_every_row_must_land(store: run.EvidenceStore) -> None:
    rows = binance.read_funding(fx.make_fetcher(funding_world()), date(2020, 2, 1), date(2020, 2, 1)).rows
    recorded = persistence.RecordedDerivativesProvider("binance", "BTCUSDT", binance.BINANCE_PROVIDER, funding=rows)
    connection = RecordingConnection()
    counts = run.persist_derivative_rows(connection, RETRIEVED_AT, recorded, [date(2020, 1, 1), date(2020, 2, 1)], source="s")
    assert counts == {"funding_rates": 6} and len(connection.statements) == 1  # the empty January slice inserts nothing
    refused("PROVIDER_REQUEST_MISMATCH", run.persist_derivative_rows, RecordingConnection(), RETRIEVED_AT, recorded, [date(2020, 3, 1)], source="s")


def test_deterministic_gzip_reproduces_and_round_trips() -> None:
    data = b'{"hours":[]}' * 100
    assert run.deterministic_gzip(data) == run.deterministic_gzip(data) and gzip.decompress(run.deterministic_gzip(data)) == data
    assert run.deterministic_gzip(data)[4:8] == b"\x00\x00\x00\x00"  # mtime zero


# --- incidents and liquidations ----------------------------------------------------------------


def tardis_body(*reports: dict[str, Any]) -> bytes:
    return json.dumps({"id": "cryptofacilities", "incidentReports": list(reports), "availableSymbols": []}).encode()


def report(start: str, end: str) -> dict[str, Any]:
    return {"from": start, "to": end, "status": "resolved", "details": "free text 777000001"}


def test_the_incident_list_keeps_in_window_instants_only() -> None:
    body = tardis_body(
        report("2026-06-23T19:32:00.000Z", "2026-06-23T19:37:00.000Z"),
        report("2021-11-10T05:09:00.000Z", "2021-11-10T05:19:00.000Z"),
        report("2019-08-01T10:45:00.000Z", "2019-08-01T14:09:00.000Z"),
        report("2019-12-31T23:50:00.000Z", "2020-01-01T00:10:00.000Z"),
    )
    assert run.parse_tardis_incidents(body) == ((utc(2020, 1, 1), utc(2020, 1, 1, 0, 10)), (utc(2021, 11, 10, 5, 9), utc(2021, 11, 10, 5, 19)))
    for bad in (b"[]", b"{}", tardis_body({"from": "x", "to": "y", "status": "s", "details": "d"}), tardis_body({"from": "2021-01-01T00:00:00Z"}),
                tardis_body(report("2021-01-02T00:00:00Z", "2021-01-01T00:00:00Z"))):
        refused("RESPONSE_SHAPE_REFUSED", run.parse_tardis_incidents, bad)


def test_the_incidents_unit_records_instants_never_details_and_feeds_the_liquidation_days(store: run.EvidenceStore) -> None:
    transport = FakeTransport()
    transport.add(run.TARDIS_EXCHANGE_URL, tardis_body(report("2021-11-10T05:09:00.000Z", "2021-11-10T05:19:00.000Z")))
    ctx = context(transport, store)
    refused("PROVIDER_REQUEST_MISMATCH", run.liquidation_unit, ctx, "2021-11-10")
    assert run.run_unit(ctx, "kraken-incidents", "all").status == "DONE"
    summary = json.loads((store.unit_dir("kraken-incidents", "all") / "summary.json").read_bytes())
    assert summary == {"incidents": [{"start": "2021-11-10T05:09:00+00:00", "end": "2021-11-10T05:19:00+00:00"}], "matches_rbt002": True}
    assert all(b"777000001" not in data for data in unit_files(store, "kraken-incidents", "all").values())
    assert run._incidents(ctx) == kraken.RBT002_RECORDED_INCIDENTS


def test_a_liquidation_day_keeps_its_gzipped_evidence_and_persists_its_rows(store: run.EvidenceStore) -> None:
    transport = FakeTransport()
    transport.add(run.TARDIS_EXCHANGE_URL, tardis_body())
    day = date(2021, 6, 1)
    start = utc(2021, 6, 1)
    executions = [fx.execution(f"e{hour}", start + timedelta(hours=hour, minutes=5)) for hour in range(24)]
    executions.append(fx.execution("liq", start + timedelta(hours=3, minutes=7), quantity="777000005", order_type="Liquidation", direction="Sell"))
    executions.sort(key=lambda item: item["timestamp"])
    transport.add(kraken.executions_url(start, start + timedelta(days=1)), fx.execution_page(executions))
    series = {start + timedelta(hours=hour): ("777000005" if hour == 3 else "0") for hour in range(24)}
    transport.add(kraken.liquidation_volume_url(start, start + timedelta(hours=23)), fx.series_body(series))
    database = Database()
    ctx = context(transport, store, database)
    assert run.run_unit(ctx, "kraken-incidents", "all").status == "DONE"
    report_ = run.run_unit(ctx, "kraken-liquidations", day.isoformat())
    assert report_.status == "DONE", report_.detail
    files = unit_files(store, "kraken-liquidations", "2021-06-01")
    summary = json.loads(files["summary.json"])
    evidence = gzip.decompress(files["liquidation_hour_evidence.json.gz"])
    assert sources.sha256_hex(evidence) == summary["evidence_sha256"] and len(evidence) == summary["evidence_size"]
    hours = kraken.parse_liquidation_hour_evidence(evidence, expected_sha256=summary["evidence_sha256"])
    assert len(hours) == 24 and summary["corroboration"] == {"AGREES": 24} and summary["disagreeing_hours"] == []
    assert summary["feed_status"] == {"OBSERVED_WITH_EVENTS": 1, "OBSERVED_ZERO_EVENTS": 23} and summary["rows"] == 1
    assert json.loads(files["DONE.json"])["persisted"] == {"liquidations": 1}
    assert b"777000005" not in files["summary.json"] and b"777000005" not in files["retrievals.json"]


def liquidation_world(*, in_order: bool) -> FakeTransport:
    transport = FakeTransport()
    transport.add(run.TARDIS_EXCHANGE_URL, tardis_body())
    start = utc(2021, 6, 1)
    executions = [fx.execution(f"e{hour}", start + timedelta(hours=hour, minutes=5)) for hour in range(24)]
    executions.append(fx.execution("liq", start + timedelta(hours=3, minutes=7), quantity="777000005", order_type="Liquidation", direction="Sell"))
    if in_order:
        executions.sort(key=lambda item: item["timestamp"])
    transport.add(kraken.executions_url(start, start + timedelta(days=1)), fx.execution_page(executions))  # else "liq" is listed last
    series = {start + timedelta(hours=hour): ("777000005" if hour == 3 else "0") for hour in range(24)}
    transport.add(kraken.liquidation_volume_url(start, start + timedelta(hours=23)), fx.series_body(series))
    return transport


@pytest.mark.parametrize(("in_order", "steps"), [(True, 0), (False, 1)], ids=["in-order", "out-of-order"])
def test_ruling_12_a_liquidation_day_listed_out_of_order_is_collected_and_its_summary_counts_the_steps_back(
    store: run.EvidenceStore, in_order: bool, steps: int
) -> None:
    ctx = context(liquidation_world(in_order=in_order), store, Database())
    assert run.run_unit(ctx, "kraken-incidents", "all").status == "DONE"
    report_ = run.run_unit(ctx, "kraken-liquidations", "2021-06-01")
    assert report_.status == "DONE", report_.detail
    files = unit_files(store, "kraken-liquidations", "2021-06-01")
    summary = json.loads(files["summary.json"])
    assert summary["out_of_order_steps"] == steps and summary["rows"] == 1 and summary["corroboration"] == {"AGREES": 24}
    assert json.loads(files["DONE.json"])["persisted"] == {"liquidations": 1}
    assert run.run_unit(ctx, "kraken-liquidations", "2021-06-01").status == "SKIPPED"


def test_ruling_12_a_liquidation_day_out_of_order_interrupted_after_its_commit_is_read_again_with_its_instants(
    store: run.EvidenceStore,
) -> None:
    database = Database()
    assert run.run_unit(advancing_context(liquidation_world(in_order=False), store), "kraken-incidents", "all").status == "DONE"
    run_interrupted(store, advancing_context(liquidation_world(in_order=False), store, database), "kraken-liquidations", "2021-06-01")
    committed = available_at(database)
    before = prepared_files(store, "kraken-liquidations", "2021-06-01")
    assert committed and json.loads(before["summary.json"])["out_of_order_steps"] == 1
    transport, database_again = liquidation_world(in_order=False), Database()
    report_ = run.run_unit(advancing_context(transport, store, database_again, start=LATER), "kraken-liquidations", "2021-06-01")
    assert report_.status == "DONE", report_.detail
    assert available_at(database_again) == committed
    after = unit_files(store, "kraken-liquidations", "2021-06-01")
    assert {name: data for name, data in after.items() if name != "DONE.json"} == before


def copied_liquidation_world(*, repeat_changed: bool = False) -> FakeTransport:
    """A day whose log lists one block, the liquidation among it, twice in a row (owner Part B ruling 13)."""

    transport = FakeTransport()
    transport.add(run.TARDIS_EXCHANGE_URL, tardis_body())
    start = utc(2021, 6, 1)
    executions = [fx.execution(f"e{hour}", start + timedelta(hours=hour, minutes=5)) for hour in range(24)]
    executions.insert(4, fx.execution("liq", start + timedelta(hours=3, minutes=7), quantity="777000005", order_type="Liquidation", direction="Sell"))
    block = json.loads(json.dumps(executions[2:6]))  # e2, e3, liq, e4
    if repeat_changed:
        block[2]["event"]["Execution"]["execution"]["quantity"] = "777000006"
    transport.add(kraken.executions_url(start, start + timedelta(days=1)), fx.execution_page(executions[:6] + block + executions[6:]))
    series = {start + timedelta(hours=hour): ("777000005" if hour == 3 else "0") for hour in range(24)}
    transport.add(kraken.liquidation_volume_url(start, start + timedelta(hours=23)), fx.series_body(series))
    return transport


def test_ruling_13_a_liquidation_day_listing_a_block_twice_is_collected_and_its_summary_counts_the_copies(
    store: run.EvidenceStore,
) -> None:
    ctx = context(copied_liquidation_world(), store, Database())
    assert run.run_unit(ctx, "kraken-incidents", "all").status == "DONE"
    report_ = run.run_unit(ctx, "kraken-liquidations", "2021-06-01")
    assert report_.status == "DONE", report_.detail
    files = unit_files(store, "kraken-liquidations", "2021-06-01")
    summary = json.loads(files["summary.json"])
    assert summary["duplicate_copies"] == 4 and summary["out_of_order_steps"] == 0
    assert summary["rows"] == 1 and summary["corroboration"] == {"AGREES": 24}
    assert json.loads(files["DONE.json"])["persisted"] == {"liquidations": 1}
    assert run.run_unit(ctx, "kraken-liquidations", "2021-06-01").status == "SKIPPED"


@pytest.mark.parametrize("in_order", [True, False], ids=["in-order", "out-of-order"])
def test_ruling_13_a_liquidation_day_without_copies_counts_none(store: run.EvidenceStore, in_order: bool) -> None:
    ctx = context(liquidation_world(in_order=in_order), store, Database())
    assert run.run_unit(ctx, "kraken-incidents", "all").status == "DONE"
    assert run.run_unit(ctx, "kraken-liquidations", "2021-06-01").status == "DONE"
    assert json.loads(unit_files(store, "kraken-liquidations", "2021-06-01")["summary.json"])["duplicate_copies"] == 0


def test_ruling_13_a_liquidation_day_whose_repeat_differs_is_refused_and_writes_nothing(store: run.EvidenceStore) -> None:
    database = Database()
    ctx = context(copied_liquidation_world(repeat_changed=True), store, database)
    assert run.run_unit(ctx, "kraken-incidents", "all").status == "DONE"
    connections = len(database.connections)
    report_ = run.run_unit(ctx, "kraken-liquidations", "2021-06-01")
    assert report_.status == "REFUSED" and report_.detail.startswith("DUPLICATE_PROVIDER_RECORD"), report_.detail
    assert "777000006" not in report_.detail and "777000005" not in report_.detail
    assert not store.unit_dir("kraken-liquidations", "2021-06-01").exists() and len(database.connections) == connections


# --- the single reads --------------------------------------------------------------------------


def test_the_basis_unit_keeps_its_listing_evidence_and_persists_by_month(store: run.EvidenceStore) -> None:
    transport = FakeTransport()
    transport.add(binance.archive_listing_url(binance.COINM_KLINES_PREFIX), fx.s3_listing(["BTCUSD_200925", "BTCUSD_PERP"]))
    fx.add_contract(transport, "BTCUSD_200925", utc(2020, 8, 10, 8), utc(2020, 9, 25, 7))
    fx.add_index(transport, utc(2020, 8, 1), utc(2020, 9, 30, 23))
    database = Database()
    report_ = run.run_unit(context(transport, store, database), "binance-basis", "all")
    assert report_.status == "DONE", report_.detail
    files = unit_files(store, "binance-basis", "all")
    summary = json.loads(files["summary.json"])
    assert summary["contracts"] == [
        {"instrument": "BTCUSD_200925", "first_kline_open_at": "2020-08-10T08:00:00+00:00", "delivery_at": "2020-09-25T08:00:00+00:00"}
    ]
    assert summary["listing_evidence_sha256"] == sources.sha256_hex(files["futures_basis_listing_evidence.json"])
    persisted = json.loads(files["DONE.json"])["persisted"]["futures_basis"]
    assert persisted == summary["rows"] and len(database.connections[0].statements) == 2  # August and September


def test_the_market_cap_unit_keeps_the_v2_evidence_file(store: run.EvidenceStore, monkeypatch: pytest.MonkeyPatch) -> None:
    first, last = date(2020, 1, 1), date(2020, 1, 3)
    monkeypatch.setattr(run, "LAST_DATA_DAY", last)
    transport = FakeTransport()
    transport.add(coinmetrics.timeseries_url(first, last), fx.coinmetrics_page([(first, "1.5"), (last, "2.5")], token=None))
    assert run.run_unit(context(transport, store), "coinmetrics-market-cap", "all").status == "DONE"
    files = unit_files(store, "coinmetrics-market-cap", "all")
    summary = json.loads(files["summary.json"])
    assert summary["missing_days"] == ["2020-01-02"] and summary["evidence_sha256"] == sources.sha256_hex(files["market_cap_evidence.json"])


def test_ruling_10_coinglass_runs_only_when_allowed_and_keyed(store: run.EvidenceStore) -> None:
    transport = FakeTransport()
    report_ = run.run_unit(context(transport, store), "coinglass-etf", "all")
    assert report_.status == "REFUSED" and "allow-coinglass" in report_.detail and transport.calls == []
    report_ = run.run_unit(context(transport, store, allow_coinglass=True), "coinglass-etf", "all")
    assert report_.status == "REFUSED" and "COINGLASS_API_KEY" in report_.detail and transport.calls == []


def test_ruling_10_the_coinglass_unit_keeps_projections_and_their_exposure(store: run.EvidenceStore) -> None:
    first, second = date(2024, 1, 11), date(2024, 2, 1)
    transport = FakeTransport()
    days = {first: {"IBIT": 5, "GBTC": -7}, second: {"IBIT": 6}, date(2026, 1, 5): {"IBIT": 777000001}}
    transport.add(coinglass.FLOW_HISTORY_URL, fx.coinglass_flow_page(days))
    transport.add(coinglass.fund_history_url("IBIT"), fx.coinglass_fund_page({first: 9, second: 10, date(2026, 1, 5): 777000002}))
    transport.add(coinglass.fund_history_url("GBTC"), fx.coinglass_fund_page({date(2019, 6, 3): 777000003, first: 11}, ticker="GBTC"))
    database = Database()
    report_ = run.run_unit(context(transport, store, database, allow_coinglass=True, coinglass_key="key-123"), "coinglass-etf", "all")
    assert report_.status == "DONE", report_.detail
    files = unit_files(store, "coinglass-etf", "all")
    assert sorted(files) == ["DONE.json", "flow_history.projected.json", "history_GBTC.projected.json", "history_IBIT.projected.json", "retrievals.json", "summary.json"]
    assert all(b"77700000" not in data for data in files.values())
    assert all(b"key-123" not in data for data in files.values())
    summary = json.loads(files["summary.json"])
    assert [(item["kept"], item["dropped_prohibited"], item["dropped_holdout"]) for item in summary["projections"]] == [(2, 0, 1), (1, 1, 0), (2, 0, 1)]
    assert summary["rows"] == 3 and summary["tickers_seen"] == ["GBTC", "IBIT"]
    assert json.loads(files["DONE.json"])["persisted"]["etf_flows"] == 3
    assert sum(len(connection.statements) for connection in database.connections) == 2  # January and February 2024
