"""RBT-003 Part A: the historical provider adapters and evidence writers, offline.

Owner rulings of 2026-11-04 (RBT-003 block): Part A runs on synthetic fixtures
only, with no network, database or purchase. A COIN-M contract's delivery
instant is its symbol date at 08:00 UTC, checked against the archive for
in-window deliveries (ruling 2). The liquidation-volume corroboration agrees at
the series' precision (ruling 3). A differing duplicate open-interest row leaves
a gap (ruling 4). The CoinGlass and Kraken-chart shapes are strict and UNVERIFIED
(ruling 5).

The integration tests feed each adapter's output to the replay builders it is
written for (RBT-001A's V2 builder, BTC-021's and BTC-022's collectors).
"""

from __future__ import annotations

import dataclasses
import hashlib
import itertools
import json
import socket
from datetime import UTC, date, datetime, timedelta
from decimal import (
    MAX_EMAX,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    Context,
    Decimal,
    DivisionByZero,
    Inexact,
    InvalidOperation,
    Overflow,
    localcontext,
)
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import parse_qsl, urlencode

import pytest

from btc_predictor.data import collect_btc_derivatives, collect_etf_flows
from btc_predictor.research import prospective_integration_corpus as epic_x
from btc_predictor.research_backtest import backfill_binance as binance
from btc_predictor.research_backtest import backfill_coinglass as coinglass
from btc_predictor.research_backtest import backfill_coinmetrics as coinmetrics
from btc_predictor.research_backtest import backfill_kraken as kraken
from btc_predictor.research_backtest import backfill_persistence as persistence
from btc_predictor.research_backtest import backfill_projection as projection
from btc_predictor.research_backtest import backfill_sources as sources
from btc_predictor.research_backtest import replay_inputs as v1
from btc_predictor.research_backtest import replay_inputs_v2 as v2
from btc_predictor.research_backtest.backfill_sources import BackfillRefused, RetrievalLog
from btc_predictor.tests import rbt001a_replay_fixtures as rbt001a
from btc_predictor.tests import rbt003_backfill_fixtures as fx
from btc_predictor.tests.rbt003_backfill_fixtures import HOUR, RETRIEVED_AT, FakeTransport, make_fetcher, utc


ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "backtest_evidence" / "research_backtest_v1" / "rbt002_input_coverage_inventory_v1.json"
NEW_MODULES = (sources, binance, kraken, coinmetrics, coinglass, projection, persistence)


@pytest.fixture(autouse=True)
def no_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    """Part A is offline: any socket an adapter or test opened would fail the test."""

    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("RBT-003 Part A opened a socket")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def refused(reason: str, call: Any, *args: Any, **kwargs: Any) -> BackfillRefused:
    with pytest.raises(BackfillRefused) as caught:
        call(*args, **kwargs)
    assert caught.value.reason_code == reason, str(caught.value)
    return caught.value


def probe(probe_id: str) -> dict[str, Any]:
    probes = json.loads(INVENTORY.read_text())["sources"]["probes"]
    return next(item for item in probes if item["probe_id"] == probe_id)


# --- the shared boundary ---------------------------------------------------------------------


def test_no_module_defines_a_network_transport_or_imports_a_client() -> None:
    for module in NEW_MODULES:
        text = Path(module.__file__).read_text()
        for banned in ("urlopen", "import socket", "http.client", "import requests", "import httpx", "urllib.request"):
            assert banned not in text, (module.__name__, banned)


def test_the_window_guard_admits_exactly_the_data_window() -> None:
    sources.require_request_span(utc(2020, 1, 1), utc(2026, 1, 1), "edge")
    refused("REQUEST_OUTSIDE_DATA_WINDOW", sources.require_request_span, utc(2019, 12, 31, 23), utc(2020, 1, 2), "pre")
    refused("REQUEST_OUTSIDE_DATA_WINDOW", sources.require_request_span, utc(2025, 12, 31), utc(2026, 1, 1, 1), "holdout")
    refused("REQUEST_OUTSIDE_DATA_WINDOW", sources.require_request_span, utc(2021, 1, 2), utc(2021, 1, 1), "reversed")
    assert sources.require_observation_in_window(utc(2025, 12, 31, 23), "last") == utc(2025, 12, 31, 23)
    for outside in (utc(2026, 1, 1), utc(2019, 12, 31, 23)):
        refused("OBSERVATION_OUTSIDE_DATA_WINDOW", sources.require_observation_in_window, outside, "row")
    assert sources.data_window_months()[0] == date(2020, 1, 1) and sources.data_window_months()[-1] == date(2025, 12, 1)
    assert sources.data_window_months(date(2019, 5, 1), date(2027, 1, 1)) == sources.data_window_months()
    refused("REQUEST_OUTSIDE_DATA_WINDOW", sources.data_window_days, date(2025, 12, 31), date(2026, 1, 1))


def test_the_fetcher_logs_digests_never_headers_and_refuses_errors() -> None:
    transport = FakeTransport()
    transport.add("https://x/ok", b"body")
    transport.add("https://x/err", b"oops", status=500)
    fetcher = make_fetcher(transport, headers={"CG-API-KEY": "secret"})
    fetched = fetcher.fetch("https://x/ok")
    assert (fetched.body, fetched.retrieved_at, fetched.sha256) == (b"body", RETRIEVED_AT, hashlib.sha256(b"body").hexdigest())
    assert fetcher.fetch_optional("https://x/missing") is None
    refused("PROVIDER_RESPONSE_REFUSED", fetcher.fetch, "https://x/missing")
    refused("PROVIDER_RESPONSE_REFUSED", fetcher.fetch_optional, "https://x/err")
    assert [call[1] for call in transport.calls] == [{"CG-API-KEY": "secret"}] * 4
    records = fetcher.log.as_records()
    assert [record["status"] for record in records] == [200, 404, 404, 500]
    assert "secret" not in json.dumps(records) and set(records[0]) == {"url", "retrieved_at", "status", "size", "sha256"}
    assert fetcher.log.digests() == (hashlib.sha256(b"body").hexdigest(),)


def test_an_unknown_refusal_code_is_itself_an_error() -> None:
    with pytest.raises(ValueError):
        BackfillRefused("SOMETHING_ELSE", "x")


def test_an_archive_must_hold_exactly_its_one_named_csv() -> None:
    good = fx.zip_bytes("a.csv", [["1", "2"]])
    assert sources.single_csv_member(good, "a.csv", "t") == [["1", "2"]]
    refused("RESPONSE_SHAPE_REFUSED", sources.single_csv_member, good, "b.csv", "t")
    refused("RESPONSE_SHAPE_REFUSED", sources.single_csv_member, fx.zip_bytes("a.csv", [["1"]], extra={"b.csv": ""}), "a.csv", "t")
    refused("RESPONSE_SHAPE_REFUSED", sources.single_csv_member, b"not a zip", "a.csv", "t")


@pytest.mark.parametrize(
    ("build", "period"),
    [
        (binance.funding_archive_url, None),
        (binance.usdm_klines_archive_url, None),
        (lambda month: binance.coinm_klines_archive_url("BTCUSD_260327", month), None),
        (binance.coinm_index_archive_url, None),
        (binance.metrics_archive_url, "day"),
    ],
    ids=["funding", "perp-klines", "contract-klines", "index-klines", "metrics"],
)
def test_every_archive_url_builder_refuses_a_period_outside_the_window(build: Any, period: str | None) -> None:
    inside, outside = ((date(2020, 1, 1), date(2025, 12, 31)), (date(2019, 12, 31), date(2026, 1, 1))) if period else (
        (date(2020, 1, 1), date(2025, 12, 1)),
        (date(2019, 12, 1), date(2026, 1, 1)),
    )
    for day in inside:
        binance.require_archive_url_in_window(build(day))
    for day in outside:
        refused("REQUEST_OUTSIDE_DATA_WINDOW", build, day)
    if period is None:
        refused("REQUEST_OUTSIDE_DATA_WINDOW", build, date(2020, 1, 2))  # a month is its first day
    refused("REQUEST_OUTSIDE_DATA_WINDOW", build, datetime(2020, 1, 1, tzinfo=UTC))


@pytest.mark.parametrize(
    "url",
    [
        f"{binance.BINANCE_ARCHIVE_BASE}/um/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-2026-01.zip",
        f"{binance.BINANCE_ARCHIVE_BASE}/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-2019-12-31.zip",
        f"{binance.BINANCE_ARCHIVE_BASE}/cm/monthly/klines/BTCUSD_260327/1h/BTCUSD_260327-1h-2026-02.zip",
        f"{binance.BINANCE_ARCHIVE_BASE}/cm/monthly/indexPriceKlines/BTCUSD/1h/BTCUSD-1h-2026-03.zip",
        f"{binance.BINANCE_ARCHIVE_BASE}/um/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2020-13.zip",
        f"{binance.BINANCE_ARCHIVE_BASE}/um/monthly/klines/BTCUSDT/1h/BTCUSDT-1h.zip",
        f"{binance.BINANCE_ARCHIVE_BASE}/um/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2020-01.zip?x=2026-01",
        "https://elsewhere.example/BTCUSDT-1h-2020-01.zip",
    ],
    ids=["2026-month", "2019-day", "2026-contract", "2026-index", "no-calendar-month", "no-period", "query", "foreign"],
)
def test_the_archive_fetch_refuses_a_hand_built_url_outside_the_window_before_the_transport(url: str) -> None:
    transport = FakeTransport()
    transport.add(url, b"never read")
    refused("REQUEST_OUTSIDE_DATA_WINDOW", binance.verified_archive, make_fetcher(transport), url)
    assert transport.calls == []


def test_the_kraken_url_builders_refuse_a_span_outside_the_window() -> None:
    kraken.executions_url(utc(2025, 12, 31), utc(2026, 1, 1))
    kraken.liquidation_volume_url(utc(2025, 12, 31), utc(2025, 12, 31, 23))
    for since, before in ((utc(2019, 12, 31), utc(2020, 1, 1)), (utc(2025, 12, 31), utc(2026, 1, 1, 1)), (utc(2021, 1, 2), utc(2021, 1, 1))):
        refused("REQUEST_OUTSIDE_DATA_WINDOW", kraken.executions_url, since, before)
        refused("REQUEST_OUTSIDE_DATA_WINDOW", kraken.executions_url, since, before, "token")
    for since, to in ((utc(2019, 12, 31, 23), utc(2020, 1, 1, 1)), (utc(2025, 12, 31), utc(2026, 1, 1)), (utc(2021, 1, 2), utc(2021, 1, 1))):
        refused("REQUEST_OUTSIDE_DATA_WINDOW", kraken.liquidation_volume_url, since, to)


# --- Binance funding -------------------------------------------------------------------------


def funding_month(transport: FakeTransport, month: date, rows: list[list[str]], **kwargs: Any) -> None:
    fx.add_archive(transport, binance.funding_archive_url(month), rows, **kwargs)


def test_funding_settlements_become_owner_rows_and_the_one_pricing_2019_is_excluded() -> None:
    transport = FakeTransport()
    january = [fx.funding_row(utc(2020, 1, 1, hour)) for hour in (0, 8, 16)]
    funding_month(transport, date(2020, 1, 1), [list(binance.FUNDING_HEADER), *january])
    funding_month(transport, date(2020, 2, 1), [fx.funding_row(utc(2020, 2, 1), rate="-0.00025")])
    read = binance.read_funding(make_fetcher(transport), date(2020, 1, 1), date(2020, 2, 1))
    assert [row.observation_time for row in read.rows] == [utc(2020, 1, 1, 8), utc(2020, 1, 1, 16), utc(2020, 2, 1)]
    assert read.excluded == ((utc(2020, 1, 1), binance.EXCLUDED_FUNDING_PRICES_PRE_2020),)
    row = read.rows[-1]
    assert (row.exchange, row.symbol, row.instrument, row.provider) == ("binance", "BTCUSDT", "BTCUSDT", binance.BINANCE_PROVIDER)
    assert (row.funding_rate, row.funding_interval_hours) == (Decimal("-0.00025"), Decimal("8"))
    assert row.available_at == row.ingested_at == RETRIEVED_AT and row.source == binance.funding_archive_url(date(2020, 2, 1))
    # V1's funding rule admits every row the adapter keeps
    snapshot = rbt001a.shared_snapshot(funding_rates=read.rows)
    assert len(snapshot.funding_rates) == 3


def test_only_data_window_funding_months_are_requested() -> None:
    transport = FakeTransport()
    for month in sources.data_window_months(date(2025, 11, 1), date(2025, 12, 1)):
        funding_month(transport, month, [fx.funding_row(datetime(month.year, month.month, 2, tzinfo=UTC))])
    binance.read_funding(make_fetcher(transport), date(2025, 11, 1), date(2027, 3, 1))
    assert all("2026" not in url and "2027" not in url for url in transport.urls)
    assert len(transport.urls) == 4  # two archives and their checksums


@pytest.mark.parametrize(
    ("rows", "reason"),
    [
        ([fx.funding_row(utc(2020, 2, 1)), fx.funding_row(utc(2020, 2, 1))], "DUPLICATE_PROVIDER_RECORD"),
        ([fx.funding_row(utc(2020, 3, 1))], "RESPONSE_SHAPE_REFUSED"),
        ([fx.funding_row(utc(2020, 2, 1), hours="0")], "RESPONSE_SHAPE_REFUSED"),
        ([fx.funding_row(utc(2020, 2, 1), hours="0.0001")], "RESPONSE_SHAPE_REFUSED"),
        ([fx.funding_row(utc(2020, 2, 1), rate="NaN")], "RESPONSE_SHAPE_REFUSED"),
        ([[str(int(fx.ms(utc(2020, 2, 1))) * 1000), "8", "0.0001"]], "RESPONSE_SHAPE_REFUSED"),
        ([["2020-02-01", "8", "0.0001"]], "RESPONSE_SHAPE_REFUSED"),
        ([fx.funding_row(utc(2020, 2, 1))[:2]], "RESPONSE_SHAPE_REFUSED"),
    ],
    ids=["duplicate", "other-month", "zero-interval", "fractional-second", "nan", "microseconds", "date-text", "narrow"],
)
def test_a_malformed_funding_archive_is_refused(rows: list[list[str]], reason: str) -> None:
    transport = FakeTransport()
    funding_month(transport, date(2020, 2, 1), rows)
    refused(reason, binance.read_funding, make_fetcher(transport), date(2020, 2, 1), date(2020, 2, 1))


def test_a_holdout_row_inside_an_archive_is_an_exposure_not_a_filtered_row() -> None:
    transport = FakeTransport()
    funding_month(transport, date(2025, 12, 1), [fx.funding_row(utc(2025, 12, 31, 16)), fx.funding_row(utc(2026, 1, 1))])
    refused("OBSERVATION_OUTSIDE_DATA_WINDOW", binance.read_funding, make_fetcher(transport), date(2025, 12, 1), date(2025, 12, 1))


def test_an_archive_must_match_its_published_checksum() -> None:
    transport = FakeTransport()
    url = binance.funding_archive_url(date(2020, 2, 1))
    funding_month(transport, date(2020, 2, 1), [fx.funding_row(utc(2020, 2, 1))])
    transport.add(f"{url}.CHECKSUM", f"{'0' * 64}  {url.rsplit('/', 1)[1]}\n".encode())
    refused("ARCHIVE_CHECKSUM_MISMATCH", binance.read_funding, make_fetcher(transport), date(2020, 2, 1), date(2020, 2, 1))
    data = transport.responses[url].body
    transport.add(f"{url}.CHECKSUM", f"{hashlib.sha256(data).hexdigest()}  other.zip\n".encode())
    refused("ARCHIVE_CHECKSUM_MISMATCH", binance.read_funding, make_fetcher(transport), date(2020, 2, 1), date(2020, 2, 1))
    transport.add(f"{url}.CHECKSUM", b"garbage")
    refused("ARCHIVE_CHECKSUM_MISMATCH", binance.read_funding, make_fetcher(transport), date(2020, 2, 1), date(2020, 2, 1))
    del transport.responses[f"{url}.CHECKSUM"]
    refused("PROVIDER_RESPONSE_REFUSED", binance.read_funding, make_fetcher(transport), date(2020, 2, 1), date(2020, 2, 1))


# --- Binance open interest -------------------------------------------------------------------


def metrics_day(transport: FakeTransport, day: date, rows: list[list[str]]) -> None:
    fx.add_archive(transport, binance.metrics_archive_url(day), [list(binance.METRICS_HEADER), *rows])


def five_minute_rows(day: date, value_at: Any = lambda t: "1000000") -> list[list[str]]:
    start = datetime(day.year, day.month, day.day, tzinfo=UTC)
    return [fx.metrics_row(start + timedelta(minutes=5 * k), value_at(start + timedelta(minutes=5 * k))) for k in range(288)]


def test_open_interest_keeps_the_hourly_usd_snapshot() -> None:
    transport = FakeTransport()
    day = date(2020, 9, 1)
    metrics_day(transport, day, five_minute_rows(day, lambda t: f"{1000 + t.hour}.5"))
    read = binance.read_open_interest(make_fetcher(transport), day, day)
    assert [row.observation_time for row in read.rows] == fx.hourly(utc(2020, 9, 1), utc(2020, 9, 2)) and read.gaps == ()
    assert [row.open_interest for row in read.rows[:2]] == [Decimal("1000.5"), Decimal("1001.5")]
    assert {row.open_interest_unit for row in read.rows} == {"USD"}
    assert len(rbt001a.shared_snapshot(open_interest=read.rows).open_interest) == 24


def test_ruling_4_identical_duplicates_collapse_and_differing_ones_leave_a_gap() -> None:
    transport = FakeTransport()
    day = date(2020, 9, 2)
    rows = five_minute_rows(day)
    rows.append(fx.metrics_row(utc(2020, 9, 2, 3)))  # byte-identical copy of 03:00
    rows.append(fx.metrics_row(utc(2020, 9, 2, 5), "999"))  # a differing copy of 05:00
    rows.append(fx.metrics_row(utc(2020, 9, 2, 6, 5), "1"))  # duplicates off the hour are never read
    metrics_day(transport, day, rows)
    read = binance.read_open_interest(make_fetcher(transport), day, day)
    assert utc(2020, 9, 2, 3) in {row.observation_time for row in read.rows}
    assert [gap.as_record() for gap in read.gaps] == [
        {"observation_time": utc(2020, 9, 2, 5).isoformat(), "reason": binance.GAP_DIFFERING_DUPLICATE}
    ]
    assert len(read.rows) == 23


def test_ruling_4_compares_the_records_bytes_not_their_decoded_fields() -> None:
    transport = FakeTransport()
    day = date(2020, 9, 2)
    rows = five_minute_rows(day)
    quoted = fx.metrics_row(utc(2020, 9, 2, 3))
    quoted[3] = '"1000000"'  # decodes to the same value; its bytes differ
    rows.append(quoted)
    metrics_day(transport, day, rows)
    read = binance.read_open_interest(make_fetcher(transport), day, day)
    assert [gap.as_record() for gap in read.gaps] == [
        {"observation_time": utc(2020, 9, 2, 3).isoformat(), "reason": binance.GAP_DIFFERING_DUPLICATE}
    ]
    assert len(read.rows) == 23


def test_a_metrics_record_must_be_one_line() -> None:
    url = binance.metrics_archive_url(date(2020, 9, 2))
    name = url.rsplit("/", 1)[1].replace(".zip", ".csv")
    multiline = fx.zip_bytes(name, [fx.metrics_row(utc(2020, 9, 2))[:3] + ['"1\n2"'] + fx.metrics_row(utc(2020, 9, 2))[4:]])
    refused("RESPONSE_SHAPE_REFUSED", sources.single_csv_member_records, multiline, name, "t")
    assert sources.single_csv_member_records(fx.zip_bytes("a.csv", [["1", '"2"']]), "a.csv", "t") == [('1,"2"', ["1", "2"])]


def test_a_missing_snapshot_or_day_is_a_recorded_gap() -> None:
    transport = FakeTransport()
    day = date(2020, 9, 3)
    metrics_day(transport, day, [row for row in five_minute_rows(day) if not row[0].endswith("07:00:00")])
    read = binance.read_open_interest(make_fetcher(transport), day, date(2020, 9, 4))
    reasons = {(gap.observation_time, gap.reason) for gap in read.gaps}
    assert (utc(2020, 9, 3, 7), binance.GAP_SNAPSHOT_MISSING) in reasons
    assert {gap.observation_time for gap in read.gaps if gap.reason == binance.GAP_ARCHIVE_DAY_MISSING} == set(
        fx.hourly(utc(2020, 9, 4), utc(2020, 9, 5))
    )
    assert len(read.rows) == 23


@pytest.mark.parametrize(
    ("row", "reason"),
    [
        (fx.metrics_row(utc(2020, 9, 6, 1), symbol="ETHUSDT"), "RESPONSE_SHAPE_REFUSED"),
        (fx.metrics_row(utc(2020, 9, 7, 1)), "RESPONSE_SHAPE_REFUSED"),
        (fx.metrics_row(utc(2020, 9, 6, 1), value="-1"), "RESPONSE_SHAPE_REFUSED"),
        (["2020-09-06T01:00:00", "BTCUSDT", "1", "1", "1", "1", "1", "1"], "RESPONSE_SHAPE_REFUSED"),
    ],
    ids=["symbol", "other-day", "negative", "iso-text"],
)
def test_a_malformed_metrics_row_is_refused(row: list[str], reason: str) -> None:
    transport = FakeTransport()
    metrics_day(transport, date(2020, 9, 6), [*five_minute_rows(date(2020, 9, 6))[:6], row])
    refused(reason, binance.read_open_interest, make_fetcher(transport), date(2020, 9, 6), date(2020, 9, 6))


# --- Binance perpetual volume ----------------------------------------------------------------


def test_perpetual_volume_is_stamped_at_the_interval_start() -> None:
    transport = FakeTransport()
    month = date(2020, 1, 1)
    rows = [fx.kline_row(t, "7200", volume="3.5", quote="25200") for t in fx.hourly(utc(2020, 1, 1), utc(2020, 1, 1, 3))]
    fx.add_archive(transport, binance.usdm_klines_archive_url(month), rows)
    read = binance.read_perp_volume(make_fetcher(transport), month, month)
    volumes = read.rows
    assert [volume.observation_time for volume in volumes] == [utc(2020, 1, 1), utc(2020, 1, 1, 1), utc(2020, 1, 1, 2)]
    # every other hour of the month is a recorded gap, never a silent absence (review F8)
    assert [gap.observation_time for gap in read.gaps] == fx.hourly(utc(2020, 1, 1, 3), utc(2020, 2, 1))
    assert {gap.reason for gap in read.gaps} == {binance.GAP_PERP_KLINE_MISSING}
    assert {(volume.timeframe, volume.volume, volume.volume_unit, volume.notional_usd) for volume in volumes} == {
        ("1h", Decimal("3.5"), "BTC", Decimal("25200"))
    }
    snapshot = rbt001a.shared_snapshot(perp_volumes=volumes)
    assert [volume.available_at for volume in snapshot.perp_volumes] == [utc(2020, 1, 1, 1), utc(2020, 1, 1, 2), utc(2020, 1, 1, 3)]


def test_an_empty_or_partial_perpetual_month_records_every_missing_hour() -> None:
    transport = FakeTransport()
    fx.add_archive(transport, binance.usdm_klines_archive_url(date(2020, 2, 1)), [])
    full = fx.hourly(utc(2020, 3, 1), utc(2020, 4, 1))
    fx.add_archive(transport, binance.usdm_klines_archive_url(date(2020, 3, 1)), [fx.kline_row(t, "1") for t in full if t != utc(2020, 3, 15, 9)])
    read = binance.read_perp_volume(make_fetcher(transport), date(2020, 2, 1), date(2020, 3, 1))
    assert [gap.observation_time for gap in read.gaps] == [*fx.hourly(utc(2020, 2, 1), utc(2020, 3, 1)), utc(2020, 3, 15, 9)]
    assert len(read.rows) == len(full) - 1
    assert binance.read_perp_volume(make_fetcher(transport), date(2020, 3, 1), date(2020, 3, 1)).gaps[0].as_record() == {
        "observation_time": utc(2020, 3, 15, 9).isoformat(),
        "reason": "PERP_VOLUME_KLINE_MISSING",
    }


@pytest.mark.parametrize("header", binance.KLINES_HEADERS)
def test_a_klines_header_in_either_spelling_is_skipped(header: tuple[str, ...]) -> None:
    transport = FakeTransport()
    fx.add_archive(transport, binance.usdm_klines_archive_url(date(2020, 1, 1)), [list(header), fx.kline_row(utc(2020, 1, 1), "1")])
    assert len(binance.read_perp_volume(make_fetcher(transport), date(2020, 1, 1), date(2020, 1, 1)).rows) == 1


@pytest.mark.parametrize(
    "row",
    [
        fx.kline_row(utc(2020, 1, 1), "1")[:6] + [fx.ms(utc(2020, 1, 1, 2))] + fx.kline_row(utc(2020, 1, 1), "1")[7:],
        fx.kline_row(utc(2020, 1, 1, 0, 30), "1"),
        fx.kline_row(utc(2020, 1, 1), "0"),
        fx.kline_row(utc(2020, 1, 1), "1", volume="-1"),
        ["open_time", *fx.kline_row(utc(2020, 1, 1), "1")[1:]],
    ],
    ids=["close-time", "off-hour", "zero-close", "negative-volume", "bad-header"],
)
def test_a_malformed_kline_is_refused(row: list[str]) -> None:
    transport = FakeTransport()
    fx.add_archive(transport, binance.usdm_klines_archive_url(date(2020, 1, 1)), [row])
    refused("RESPONSE_SHAPE_REFUSED", binance.read_perp_volume, make_fetcher(transport), date(2020, 1, 1), date(2020, 1, 1))


# --- COIN-M contracts, delivery and basis ----------------------------------------------------


def test_the_archive_listing_is_read_across_pages_and_only_btcusd_deliveries_are_contracts() -> None:
    transport = FakeTransport()
    prefix = binance.COINM_KLINES_PREFIX
    transport.add(binance.archive_listing_url(prefix), fx.s3_listing(["BTCUSD_201225", "ADAUSD_PERP"], marker=f"{prefix}ADAUSD_PERP/"))
    transport.add(
        binance.archive_listing_url(prefix, f"{prefix}ADAUSD_PERP/"),
        fx.s3_listing(["BTCUSD_200925", "BTCUSD_PERP", "ETHUSD_200925", "BTCUSD_2009250"]),
    )
    contracts, digests = binance.read_coinm_contracts(make_fetcher(transport))
    assert contracts == ("BTCUSD_200925", "BTCUSD_201225") and len(digests) == 2


def test_an_archive_listing_whose_marker_repeats_is_refused() -> None:
    transport = FakeTransport()
    prefix = binance.COINM_KLINES_PREFIX
    looping = fx.s3_listing(["BTCUSD_200925"], marker=f"{prefix}A/")
    transport.add(binance.archive_listing_url(prefix), looping)
    transport.add(binance.archive_listing_url(prefix, f"{prefix}A/"), looping)
    refused("CONTINUATION_CHAIN_REFUSED", binance.read_coinm_contracts, make_fetcher(transport))
    assert len(transport.calls) == 2


@pytest.mark.parametrize(
    "body",
    [
        b"<not xml",
        b'<ListBucketResult xmlns="urn:other"><IsTruncated>false</IsTruncated></ListBucketResult>',
        fx.s3_listing(["BTCUSD_200925"]).replace(b"<IsTruncated>false</IsTruncated>", b""),
        fx.s3_listing(["BTCUSD_200925"]).replace(b"false", b"true"),
        fx.s3_listing(["x/y"]),
    ],
    ids=["xml", "namespace", "no-truncation-flag", "truncated-without-marker", "nested"],
)
def test_a_malformed_archive_listing_is_refused(body: bytes) -> None:
    refused("RESPONSE_SHAPE_REFUSED", binance.parse_archive_listing, body, binance.COINM_KLINES_PREFIX)


def test_ruling_2_the_delivery_instant_is_the_symbol_date_at_0800_utc() -> None:
    assert binance.contract_delivery_at("BTCUSD_251226") == utc(2025, 12, 26, 8)
    assert binance.contract_delivery_at("BTCUSD_260327") == utc(2026, 3, 27, 8)
    for bad in ("BTCUSD_250231", "BTCUSD_PERP", "ETHUSD_251226"):
        refused("RESPONSE_SHAPE_REFUSED", binance.contract_delivery_at, bad)


def test_an_in_window_delivery_is_checked_against_the_last_archived_kline() -> None:
    transport = FakeTransport()
    fx.add_contract(transport, "BTCUSD_200925", utc(2020, 8, 10, 8), utc(2020, 9, 25, 7))
    read = binance.read_contract_klines(make_fetcher(transport), "BTCUSD_200925")
    assert read is not None
    assert (read.listing.first_kline_open_at, read.listing.delivery_at) == (utc(2020, 8, 10, 8), utc(2020, 9, 25, 8))
    # months from twelve before delivery (clipped to 2020-01) through the delivery month
    months = [url.rsplit("-1h-", 1)[1][:7] for url in transport.urls if not url.endswith(".CHECKSUM")]
    assert months == [f"2020-{m:02d}" for m in range(1, 10)]


def test_a_delivery_the_archive_contradicts_is_refused() -> None:
    transport = FakeTransport()
    fx.add_contract(transport, "BTCUSD_200925", utc(2020, 8, 10, 8), utc(2020, 9, 25, 6))
    refused("DELIVERY_INSTANT_MISMATCH", binance.read_contract_klines, make_fetcher(transport), "BTCUSD_200925")
    # ruling 11: volume in the 09:00 kline means the contract traded past the hour after delivery
    transport = FakeTransport()
    fx.add_contract(transport, "BTCUSD_200925", utc(2020, 8, 10, 8), utc(2020, 9, 25, 9))
    refused("DELIVERY_INSTANT_MISMATCH", binance.read_contract_klines, make_fetcher(transport), "BTCUSD_200925")


SETTLED = utc(2020, 9, 25, 8)  # BTCUSD_200925's delivery instant (ruling 2)


@pytest.mark.parametrize(
    ("last_open", "traded_until"),
    [
        (utc(2020, 9, 25, 8), utc(2020, 9, 25, 9)),  # the delivery-hour kline carries volume (9 of 22 live contracts)
        (utc(2020, 9, 25, 8), SETTLED),  # the delivery-hour kline exists with zero volume (most live contracts)
        (utc(2020, 9, 30, 23), SETTLED),  # zero-volume klines run to the month's end (BTCUSD_200925 live)
        (utc(2020, 9, 30, 23), utc(2020, 9, 25, 9)),  # both: volume at 08:00, then flat to the month's end
    ],
    ids=["volume-in-delivery-hour", "flat-delivery-hour", "flat-to-month-end", "volume-then-flat"],
)
def test_ruling_11_the_last_kline_with_volume_closes_at_delivery_or_the_hour_after(
    last_open: datetime, traded_until: datetime
) -> None:
    transport = FakeTransport()
    fx.add_contract(
        transport, "BTCUSD_200925", utc(2020, 8, 10, 8), last_open, volume_at=lambda t: "2" if t < traded_until else "0"
    )
    read = binance.read_contract_klines(make_fetcher(transport), "BTCUSD_200925")
    assert read is not None and read.listing.delivery_at == SETTLED
    # no kline opening at or after delivery is returned: no basis row may read one
    assert max(read.klines) == utc(2020, 9, 25, 7)


@pytest.mark.parametrize(
    ("last_open", "traded", "why"),
    [
        (utc(2020, 9, 30, 23), lambda t: t < utc(2020, 9, 25, 10), "volume until 10:00, past the hour after delivery"),
        (utc(2020, 9, 30, 23), lambda t: t < SETTLED or t == utc(2020, 9, 28, 12), "volume again days after delivery"),
        (utc(2020, 9, 30, 23), lambda t: t < utc(2020, 9, 25, 7), "no volume in the hour before delivery: stopped early"),
        (utc(2020, 9, 30, 23), lambda t: t < utc(2020, 9, 24, 8), "stopped a day early"),
        (utc(2020, 9, 30, 23), lambda t: False, "no kline has volume"),
    ],
    ids=["past-the-hour-after", "traded-again", "stopped-an-hour-early", "stopped-a-day-early", "never-traded"],
)
def test_ruling_11_any_other_last_traded_kline_refuses(last_open: datetime, traded: Any, why: str) -> None:
    transport = FakeTransport()
    fx.add_contract(transport, "BTCUSD_200925", utc(2020, 8, 10, 8), last_open, volume_at=lambda t: "2" if traded(t) else "0")
    refused("DELIVERY_INSTANT_MISMATCH", binance.read_contract_klines, make_fetcher(transport), "BTCUSD_200925")


def test_ruling_11_reads_volume_without_arithmetic_in_the_callers_context() -> None:
    transport = FakeTransport()
    fx.add_contract(
        transport, "BTCUSD_200925", utc(2020, 8, 10, 8), utc(2020, 9, 30, 23),
        volume_at=lambda t: "0.000000000000000001" if t < SETTLED else "0.000",
    )
    with localcontext() as ctx:
        ctx.prec, ctx.Emin, ctx.traps[Inexact] = 1, -2, True
        read = binance.read_contract_klines(make_fetcher(transport), "BTCUSD_200925")
    assert read is not None and max(read.klines) == utc(2020, 9, 25, 7)


def test_a_2026_delivery_reads_nothing_from_2026() -> None:
    transport = FakeTransport()
    fx.add_contract(transport, "BTCUSD_260327", utc(2025, 9, 26, 8), utc(2025, 12, 31, 23))
    read = binance.read_contract_klines(make_fetcher(transport), "BTCUSD_260327")
    assert read is not None and read.listing.delivery_at == utc(2026, 3, 27, 8)
    assert max(read.klines) == utc(2025, 12, 31, 23)
    assert all("2026-" not in url.rsplit("/", 1)[1] for url in transport.urls)
    # a contract first archived in 2026 is not listed inside the window at all
    assert binance.read_contract_klines(make_fetcher(FakeTransport()), "BTCUSD_260925") is None


def test_the_listing_start_must_be_proven_and_the_months_contiguous() -> None:
    # the first requested month is archived (a mid-month start, so only this rule refuses it):
    # at the window's clipped start, and twelve months before a later delivery
    for contract, first_open in (("BTCUSD_201225", utc(2020, 1, 10, 8)), ("BTCUSD_211231", utc(2020, 12, 10, 8))):
        transport = FakeTransport()
        fx.add_contract(transport, contract, first_open, binance.contract_delivery_at(contract) - HOUR)
        error = refused("LISTING_START_UNPROVEN", binance.read_contract_klines, make_fetcher(transport), contract)
        assert "the first requested month" in str(error)
    transport = FakeTransport()
    fx.add_contract(transport, "BTCUSD_201225", utc(2020, 6, 10, 8), utc(2020, 12, 25, 7))
    month = binance.coinm_klines_archive_url("BTCUSD_201225", date(2020, 8, 1))
    del transport.responses[month], transport.responses[f"{month}.CHECKSUM"]
    refused("ARCHIVE_MONTH_MISSING", binance.read_contract_klines, make_fetcher(transport), "BTCUSD_201225")


def test_ruling_6_a_listing_start_at_the_first_hour_of_a_month_is_unproven() -> None:
    # the review's case: the contract's real first month is missing from the archive
    transport = FakeTransport()
    fx.add_contract(transport, "BTCUSD_201225", utc(2020, 6, 10, 8), utc(2020, 12, 25, 7))
    june = binance.coinm_klines_archive_url("BTCUSD_201225", date(2020, 6, 1))
    del transport.responses[june], transport.responses[f"{june}.CHECKSUM"]
    error = refused("LISTING_START_UNPROVEN", binance.read_contract_klines, make_fetcher(transport), "BTCUSD_201225")
    assert "2020-07-01T00:00:00+00:00" in str(error)
    # a contract whose archive starts exactly at a month's first hour is unproven even with the month before absent
    transport = FakeTransport()
    fx.add_contract(transport, "BTCUSD_201225", utc(2020, 7, 1), utc(2020, 12, 25, 7))
    refused("LISTING_START_UNPROVEN", binance.read_contract_klines, make_fetcher(transport), "BTCUSD_201225")
    # one hour later is a provable start
    transport = FakeTransport()
    fx.add_contract(transport, "BTCUSD_201225", utc(2020, 7, 1, 1), utc(2020, 12, 25, 7))
    read = binance.read_contract_klines(make_fetcher(transport), "BTCUSD_201225")
    assert read is not None and read.listing.first_kline_open_at == utc(2020, 7, 1, 1)


@pytest.mark.parametrize("empty_rows", [[], [list(binance.KLINES_HEADERS[0])]], ids=["no-record", "header-only"])
def test_ruling_8_an_archived_month_without_a_kline_before_the_first_kline_is_unproven(empty_rows: list[list[str]]) -> None:
    # the re-review's case: January-April absent, May archived and verified but empty, June listing mid-month;
    # May is not the first requested month, so only ruling 8 refuses it
    may = binance.coinm_klines_archive_url("BTCUSD_201225", date(2020, 5, 1))
    transport = FakeTransport()
    fx.add_contract(transport, "BTCUSD_201225", utc(2020, 6, 10, 8), utc(2020, 12, 25, 7))
    fx.add_archive(transport, may, empty_rows)
    error = refused("LISTING_START_UNPROVEN", binance.read_contract_klines, make_fetcher(transport), "BTCUSD_201225")
    assert "2020-05 is archived without a kline" in str(error)
    # a contract whose only archive is empty is refused, not read as unlisted
    transport = FakeTransport()
    fx.add_archive(transport, may, empty_rows)
    refused("LISTING_START_UNPROVEN", binance.read_contract_klines, make_fetcher(transport), "BTCUSD_201225")
    # the same history with May absent is a proven start
    transport = FakeTransport()
    fx.add_contract(transport, "BTCUSD_201225", utc(2020, 6, 10, 8), utc(2020, 12, 25, 7))
    read = binance.read_contract_klines(make_fetcher(transport), "BTCUSD_201225")
    assert read is not None and read.listing.first_kline_open_at == utc(2020, 6, 10, 8)


def basis_world(futures_at: Any = lambda t: Decimal("10010") + t.hour, index_at: Any = lambda t: Decimal("10000")) -> FakeTransport:
    transport = FakeTransport()
    transport.add(binance.archive_listing_url(binance.COINM_KLINES_PREFIX), fx.s3_listing(["BTCUSD_200925", "BTCUSD_PERP"]))
    fx.add_contract(transport, "BTCUSD_200925", utc(2020, 8, 10, 8), utc(2020, 9, 25, 7), futures_at)
    fx.add_index(transport, utc(2020, 8, 1), utc(2020, 9, 30, 23), index_at)
    return transport


def test_basis_is_the_rounded_stored_rate_and_its_strict_annualisation() -> None:
    collection = binance.read_basis(make_fetcher(basis_world(index_at=lambda t: Decimal("9999.7"))))
    first, last = collection.rows[0], collection.rows[-1]
    # hour closes first_kline_open_at + 1h <= t < delivery_at (RBT-001A ruling 4)
    assert (first.observation_time, last.observation_time) == (utc(2020, 8, 10, 9), utc(2020, 9, 25, 7))
    assert len(collection.rows) == len(fx.hourly(utc(2020, 8, 10, 9), utc(2020, 9, 25, 8))) and collection.gaps == ()
    for row in collection.rows[:30]:
        exact = Fraction(Decimal("10010") + (row.observation_time - HOUR).hour) / Fraction(Decimal("9999.7")) - 1
        expected = Decimal(exact.numerator) / Decimal(exact.denominator)
        # an independent rounding of the exact rational to 18 places, half away from zero
        scaled = exact * 10**18
        whole = scaled.numerator // scaled.denominator
        if scaled - whole >= Fraction(1, 2):
            whole += 1
        assert row.basis_rate == Decimal(whole).scaleb(-18), (row.observation_time, expected)
        assert row.annualized_basis_rate == v2.contract_annualized_basis_rate(row.basis_rate, row.observation_time, row.expiry)
        assert (row.exchange, row.symbol, row.instrument, row.expiry) == ("binance", "BTCUSD", "BTCUSD_200925", utc(2020, 9, 25, 8))


def test_the_basis_rate_rounds_half_away_from_zero_as_numeric_38_18_stores_it() -> None:
    assert binance.basis_rate(Decimal("1.0000000000000000005"), Decimal(1)) == Decimal("1E-18")
    assert binance.basis_rate(Decimal("0.9999999999999999995"), Decimal(1)) == Decimal("-1E-18")
    assert binance.basis_rate(Decimal("1.0000000000000000004999"), Decimal(1)) == Decimal(0)
    assert binance.basis_rate(Decimal(3), Decimal(7)) == (Decimal(3) / Decimal(7) - 1).quantize(Decimal("1E-18"), ROUND_HALF_UP)


def test_basis_at_t_uses_the_klines_closing_at_t_and_a_missing_one_is_a_gap() -> None:
    transport = basis_world(futures_at=lambda t: Decimal("20000") if t == utc(2020, 8, 13, 4) else Decimal("10010"))
    index_month = binance.coinm_index_archive_url(date(2020, 9, 1))
    rows = [fx.kline_row(t, "10000") for t in fx.hourly(utc(2020, 9, 1), utc(2020, 10, 1)) if t != utc(2020, 9, 10, 12)]
    fx.add_archive(transport, index_month, rows)
    collection = binance.read_basis(make_fetcher(transport))
    by_time = {row.observation_time: row for row in collection.rows}
    assert by_time[utc(2020, 8, 13, 5)].basis_rate == Decimal(1)
    assert by_time[utc(2020, 8, 13, 4)].basis_rate == Decimal("0.001")
    assert utc(2020, 9, 10, 13) not in by_time
    assert [gap.as_record() for gap in collection.gaps] == [
        {"instrument": "BTCUSD_200925", "observation_time": utc(2020, 9, 10, 13).isoformat(), "reason": binance.GAP_INDEX_KLINE_MISSING}
    ]


def test_the_listing_evidence_cites_the_listing_and_contract_archives_and_verifies() -> None:
    transport = basis_world()
    fetcher = make_fetcher(transport)
    collection = binance.read_basis(fetcher)
    evidence = collection.listing_evidence()
    assert [contract.as_record() for contract in evidence.contracts] == [
        {"instrument": "BTCUSD_200925", "first_kline_open_at": utc(2020, 8, 10, 8).isoformat(), "delivery_at": utc(2020, 9, 25, 8).isoformat()}
    ]
    by_url = {item.url: item.sha256 for item in fetcher.log.retrievals if item.status == 200}
    cited = {by_url[url] for url in by_url if "klines/BTCUSD_200925/" in url and url.endswith(".zip")}
    cited.add(by_url[binance.archive_listing_url(binance.COINM_KLINES_PREFIX)])
    assert set(evidence.response_sha256) == cited and evidence.licence == binance.BINANCE_LICENCE


def test_the_v2_builder_admits_the_adapters_basis_rows_with_its_listing() -> None:
    collection = binance.read_basis(make_fetcher(basis_world()))
    snapshot = v2.build_extended_replay_snapshot(
        shared_snapshot=rbt001a.shared_snapshot(),
        futures_basis=collection.rows,
        futures_basis_listing=collection.listing_evidence(),
    )
    excluded = {item.row.observation_time for item in snapshot.excluded_futures_basis}
    assert min(excluded) == utc(2020, 9, 18, 8) and max(excluded) == utc(2020, 9, 25, 7)  # expiry - t <= 7 days
    assert len(snapshot.futures_basis) + len(excluded) == len(collection.rows)
    assert all(row.available_at == row.observation_time for row in snapshot.futures_basis)


# --- Kraken executions -----------------------------------------------------------------------


def test_the_recorded_empty_responses_reproduce_rbt002s_digests() -> None:
    empty_log = b'{"elements":[],"len":0}'
    empty_series = b'{"result":{"timestamp":[],"data":[],"more":false},"errors":[]}'
    assert hashlib.sha256(empty_log).hexdigest() == probe("kraken_rest_executions_before_2020")["response_sha256"]
    assert hashlib.sha256(empty_series).hexdigest() == probe("kraken_analytics_liquidation_volume_2020_02_25")["response_sha256"]
    assert kraken.parse_execution_page(empty_log) == ((), None)
    assert kraken.parse_liquidation_volume(empty_series, since=utc(2021, 6, 1), to=utc(2021, 6, 1, 23)) == {}


DAY = date(2021, 6, 1)


def day_world(pages: list[bytes], series: dict[datetime, Any] | None = None, *, day: date = DAY) -> FakeTransport:
    transport = FakeTransport()
    start = datetime(day.year, day.month, day.day, tzinfo=UTC)
    token = None
    for number, body in enumerate(pages):
        transport.add(kraken.executions_url(start, start + timedelta(days=1), token), body)
        token = f"token-{number}"
    transport.add(kraken.liquidation_volume_url(start, start + timedelta(hours=23)), fx.series_body(series or {}))
    return transport


def test_the_day_is_read_through_one_continuation_chain() -> None:
    first = fx.execution_page([fx.execution("a", utc(2021, 6, 1, 0, 5)), fx.execution("b", utc(2021, 6, 1, 3))], token="token-0")
    second = fx.execution_page([fx.execution("c", utc(2021, 6, 1, 23, 59))])
    transport = day_world([first, second])
    read = kraken.read_execution_day(make_fetcher(transport), DAY)
    assert [item.uid for item in read.executions] == ["a", "b", "c"] and len(read.pages_sha256) == 2
    assert transport.urls[0].endswith("since=1622505600000&before=1622592000000&sort=asc")
    assert transport.urls[1].endswith("&continuationToken=token-0")


@pytest.mark.parametrize(
    ("pages", "reason"),
    [
        ([fx.execution_page([fx.execution("a", utc(2021, 6, 2))])], "CONTINUATION_CHAIN_REFUSED"),
        ([fx.execution_page([fx.execution("a", utc(2021, 6, 1, 1))], "token-0"), fx.execution_page([fx.execution("a", utc(2021, 6, 1, 2))])], "DUPLICATE_PROVIDER_RECORD"),
        ([fx.execution_page([], "token-0"), fx.execution_page([], "token-0")], "CONTINUATION_CHAIN_REFUSED"),
        ([b'{"elements":[],"len":1}'], "RESPONSE_SHAPE_REFUSED"),
        ([b'{"elements":[],"len":0,"extra":1}'], "RESPONSE_SHAPE_REFUSED"),
        ([b'{"elements":[{"event":{}}],"len":1}'], "RESPONSE_SHAPE_REFUSED"),
        ([fx.execution_page([fx.execution("a", utc(2021, 6, 1, 1), quantity="0")])], "RESPONSE_SHAPE_REFUSED"),
    ],
    ids=["outside-day", "duplicate-uid", "repeated-token", "len", "extra-key", "no-execution", "zero-quantity"],
)
def test_a_broken_execution_chain_is_refused(pages: list[bytes], reason: str) -> None:
    refused(reason, kraken.read_execution_day, make_fetcher(day_world(pages)), DAY)


# --- owner Part B ruling 12: a day listed out of time order is read, its steps back counted ----------


def test_ruling_12_a_day_listed_out_of_time_order_is_read_whole_in_the_providers_order() -> None:
    # the live log listed 2021-07-15 with one execution 1 ms before the one above it
    noon = utc(2021, 6, 1, 13)
    first = fx.execution_page(
        [
            fx.execution("b", utc(2021, 6, 1, 5)),
            fx.execution("a", utc(2021, 6, 1, 4)),  # back an hour
            fx.execution("c", utc(2021, 6, 1, 4)),  # the same instant is not a step back
            fx.execution("m2", noon + timedelta(milliseconds=2)),
            fx.execution("m1", noon + timedelta(milliseconds=1)),  # back 1 ms
        ],
        token="token-0",
    )
    second = fx.execution_page([fx.execution("d", noon), fx.execution("e", utc(2021, 6, 1, 23, 59))])  # back across the pages
    read = kraken.read_execution_day(make_fetcher(day_world([first, second])), DAY)
    assert [item.uid for item in read.executions] == ["b", "a", "c", "m2", "m1", "d", "e"]
    assert read.out_of_order_steps == 3 and len(read.pages_sha256) == 2


def test_ruling_12_a_day_in_time_order_counts_no_step_back() -> None:
    page = fx.execution_page([fx.execution("a", utc(2021, 6, 1, 4)), fx.execution("b", utc(2021, 6, 1, 4)), fx.execution("c", utc(2021, 6, 1, 5))])
    assert kraken.read_execution_day(make_fetcher(day_world([page])), DAY).out_of_order_steps == 0


@pytest.mark.parametrize(
    ("pages", "reason", "detail", "reads"),
    [
        ([fx.execution_page([fx.execution("b", utc(2021, 6, 1, 5)), fx.execution("a", datetime(2021, 5, 31, 23, 59, 59, tzinfo=UTC))])],
         "CONTINUATION_CHAIN_REFUSED", "is outside the requested day", 1),
        ([fx.execution_page([fx.execution("b", utc(2021, 6, 1, 5)), fx.execution("a", utc(2021, 6, 2, 0))])],
         "CONTINUATION_CHAIN_REFUSED", "is outside the requested day", 1),
        ([fx.execution_page([fx.execution("b", utc(2021, 6, 1, 5)), fx.execution("a", utc(2021, 6, 1, 4))], "token-0"), fx.execution_page([fx.execution("b", utc(2021, 6, 1, 3))])],
         "DUPLICATE_PROVIDER_RECORD", "appears twice", 2),
        ([fx.execution_page([fx.execution("b", utc(2021, 6, 1, 5)), fx.execution("a", utc(2021, 6, 1, 4))], "token-0"), fx.execution_page([], "token-0")],
         "CONTINUATION_CHAIN_REFUSED", "a continuation token repeats", 2),
    ],
    ids=["back-before-the-day", "past-the-day", "duplicate-uid", "repeated-token"],
)
def test_ruling_12_a_day_out_of_order_still_refuses_a_broken_chain(pages: list[bytes], reason: str, detail: str, reads: int) -> None:
    transport = day_world(pages)
    refusal = refused(reason, kraken.read_execution_day, make_fetcher(transport), DAY)
    assert detail in str(refusal) and len(transport.urls) == reads  # refused by its own check, at the page that breaks the chain


def test_ruling_12_an_execution_out_of_order_in_the_holdout_is_still_an_exposure() -> None:
    page = fx.execution_page([fx.execution("b", utc(2025, 12, 31, 5)), fx.execution("a", utc(2026, 1, 1)), fx.execution("c", utc(2025, 12, 31, 4))])
    transport = day_world([page], day=date(2025, 12, 31))
    refused("OBSERVATION_OUTSIDE_DATA_WINDOW", kraken.read_execution_day, make_fetcher(transport), date(2025, 12, 31))


def without_page_digests(collection: kraken.KrakenLiquidationCollection) -> dict[str, Any]:
    evidence = json.loads(collection.evidence_bytes)
    for hour in evidence["hours"]:
        assert hour.pop("pages_sha256")
    return evidence


def test_ruling_12_the_hours_and_rows_do_not_depend_on_the_listing_order() -> None:
    _, executions = liquidation_day()
    series = {hour: 0 for hour in fx.hourly(utc(2021, 6, 1), utc(2021, 6, 2))}
    series[utc(2021, 6, 1, 1)] = "1500"
    series[utc(2021, 6, 1, 3)] = "50"
    listings = {
        "in order": [fx.execution_page(executions)],
        "reversed": [fx.execution_page(executions[::-1])],
        "reversed across pages": [fx.execution_page(executions[:0:-1], token="token-0"), fx.execution_page(executions[:1])],
    }
    collections = {
        name: kraken.read_liquidations(make_fetcher(day_world(pages, series)), DAY, DAY, incidents=()) for name, pages in listings.items()
    }
    steps = len(executions) - 1  # every execution of the day is listed at a distinct instant
    assert {name: collection.out_of_order_steps for name, collection in collections.items()} == {
        "in order": 0, "reversed": steps, "reversed across pages": steps,
    }
    in_order = collections["in order"]
    assert len(in_order.rows) == 3
    def classified(collection: kraken.KrakenLiquidationCollection) -> list[tuple[datetime, str, str]]:
        return [(hour.hour_start, hour.feed_status, hour.corroboration) for hour in collection.hours]

    for collection in collections.values():
        assert collection.rows == in_order.rows and classified(collection) == classified(in_order)
        # the hour records differ only in the digests of the pages they were read from
        assert without_page_digests(collection) == without_page_digests(in_order)


# --- owner Part B ruling 13: an identical copy of an execution collapses to one, counted ---------------


def element_text(element: dict[str, Any]) -> bytes:
    return json.dumps(element, separators=(",", ":")).encode()


def page_of(*elements: bytes) -> bytes:
    """A page from each element's own JSON text, so a copy may differ from its first listing in spelling alone."""

    return b'{"elements":[' + b",".join(elements) + b'],"len":' + str(len(elements)).encode() + b"}"


def test_ruling_13_a_block_listed_twice_back_to_back_collapses_to_one_listing() -> None:
    # the live log listed 2022-12-15, 2023-02-14, 2023-02-20 and 2023-03-17 with one block of executions twice in a row
    block = [fx.execution(uid, utc(2021, 6, 1, hour)) for uid, hour in (("a", 1), ("b", 2), ("c", 3))]
    page = fx.execution_page([*block, *block, fx.execution("d", utc(2021, 6, 1, 4))])
    read = kraken.read_execution_day(make_fetcher(day_world([page])), DAY)
    assert [item.uid for item in read.executions] == ["a", "b", "c", "d"]
    assert read.duplicate_copies == 3 and read.out_of_order_steps == 0  # a copy is not in the log, so no step back


def test_ruling_13_copies_across_pages_and_repeated_copies_are_each_counted() -> None:
    a, b, c = (fx.execution(uid, utc(2021, 6, 1, hour)) for uid, hour in (("a", 5), ("b", 4), ("c", 6)))
    first = fx.execution_page([a, b, a], token="token-0")
    second = fx.execution_page([b, a, c, c])
    read = kraken.read_execution_day(make_fetcher(day_world([first, second])), DAY)
    assert [item.uid for item in read.executions] == ["a", "b", "c"] and len(read.pages_sha256) == 2
    assert read.duplicate_copies == 4 and read.out_of_order_steps == 1  # only b, listed after a, steps back


def test_ruling_13_a_day_without_copies_counts_none() -> None:
    page = fx.execution_page([fx.execution("a", utc(2021, 6, 1, 4)), fx.execution("b", utc(2021, 6, 1, 5))])
    assert kraken.read_execution_day(make_fetcher(day_world([page])), DAY).duplicate_copies == 0
    assert kraken.parse_execution_page(page)[1] is None  # the public page parser keeps its shape


def reordered(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: reordered(value[key]) for key in reversed(list(value))}
    return value


def test_ruling_13_whitespace_key_order_and_string_escapes_do_not_make_a_copy_differ() -> None:
    a = fx.execution("a", utc(2021, 6, 1, 4))
    spaced = json.dumps(reordered(a), indent=2).encode()
    escaped = json.dumps(a).encode().replace(b'"Limit"', b'"\\u004cimit"')
    assert escaped != json.dumps(a).encode() and json.loads(escaped) == a
    read = kraken.read_execution_day(make_fetcher(day_world([page_of(element_text(a), spaced, escaped)])), DAY)
    assert [item.uid for item in read.executions] == ["a"] and read.duplicate_copies == 2


def with_extra(value: bytes) -> bytes:
    """Execution ``a``'s element with one more element-level field holding ``value``'s JSON text."""

    text = element_text(fx.execution("a", utc(2021, 6, 1, 4)))
    return text[:-1] + b',"extra":' + value + b"}"


# the first listing's and the repeat's values of one field: each pair differs, in value, type or spelling
DIFFERING_VALUES = [
    (b"1", b"2"),
    (b"1", b"1.0"),
    (b"1", b"1e0"),
    (b"1e0", b"1E0"),
    (b"1.0", b"1.00"),
    (b"0", b"-0"),
    (b"100", b"1E+2"),
    (b"1", b'"1"'),
    (b"null", b'"null"'),
    (b"NaN", b'"NaN"'),
    (b"Infinity", b'"Infinity"'),
    (b"-Infinity", b"Infinity"),
    (b"Infinity", b"1e999"),
    (b"true", b"1"),
    (b"false", b"0"),
    (b"true", b'"true"'),
    (b"null", b"0"),
    (b'""', b"null"),
    (b'"x"', b'"x "'),
    (b"[1,2]", b"[2,1]"),
    (b"[]", b"{}"),
    (b"[null]", b"[]"),
    (b'{"k":1}', b'{"k":1,"j":1}'),
    (b'{"k":1}', b'{"k":"1"}'),
    (b'["1",1]', b'[1,"1"]'),
    (b'{"k":[1]}', b'{"k":1}'),
]


@pytest.mark.parametrize("swapped", [False, True], ids=["first-then-repeat", "repeat-then-first"])
@pytest.mark.parametrize(("first", "repeat"), DIFFERING_VALUES, ids=[f"{a.decode()}~{b.decode()}" for a, b in DIFFERING_VALUES])
def test_ruling_13_a_repeat_differing_in_any_value_type_or_number_spelling_still_refuses(first: bytes, repeat: bytes, swapped: bool) -> None:
    if swapped:
        first, repeat = repeat, first
    transport = day_world([page_of(with_extra(first), with_extra(repeat))])
    refusal = refused("DUPLICATE_PROVIDER_RECORD", kraken.read_execution_day, make_fetcher(transport), DAY)
    assert str(refusal).endswith("execution a appears twice") and len(transport.urls) == 1


def changed(change: Any) -> dict[str, Any]:
    element = fx.execution("a", utc(2021, 6, 1, 4))
    change(element, element["event"]["Execution"]["execution"])
    return element


@pytest.mark.parametrize(
    "repeat",
    [
        changed(lambda element, execution: execution.update(quantity="200")),
        changed(lambda element, execution: execution.update(quantity=100)),  # the number, not the string
        changed(lambda element, execution: execution.update(price="30000.0")),
        changed(lambda element, execution: execution.update(limitFilled=True)),
        changed(lambda element, execution: execution.update(timestamp=execution["timestamp"] + 1)),
        changed(lambda element, execution: execution["takerOrder"].update(uid="taker-b")),
        changed(lambda element, execution: execution["makerOrder"].pop("uid")),
        changed(lambda element, execution: execution.update(extra=None)),
        changed(lambda element, execution: element.update(uid="element-b")),
        changed(lambda element, execution: element.update(timestamp=element["timestamp"] + 1)),
        changed(lambda element, execution: element.pop("timestamp")),
        changed(lambda element, execution: element.update(extra=1)),
    ],
    ids=[
        "quantity", "quantity-number", "price-spelling", "limit-filled", "execution-timestamp", "taker-uid",
        "maker-key-missing", "execution-key-extra", "element-uid", "element-timestamp", "element-key-missing",
        "element-key-extra",
    ],
)
def test_ruling_13_a_repeat_differing_anywhere_in_its_element_still_refuses(repeat: dict[str, Any]) -> None:
    a = fx.execution("a", utc(2021, 6, 1, 4))
    for pages in (
        [fx.execution_page([a, repeat])],
        [fx.execution_page([a, a], "token-0"), fx.execution_page([repeat])],  # after an identical copy, on a later page
    ):
        transport = day_world(pages)
        refusal = refused("DUPLICATE_PROVIDER_RECORD", kraken.read_execution_day, make_fetcher(transport), DAY)
        assert str(refusal).endswith("execution a appears twice") and len(transport.urls) == len(pages)


@pytest.mark.parametrize(
    ("day", "repeat_at", "reason", "detail"),
    [
        (DAY, utc(2021, 6, 2), "CONTINUATION_CHAIN_REFUSED", "is outside the requested day"),
        (DAY, datetime(2021, 5, 31, 23, 59, 59, tzinfo=UTC), "CONTINUATION_CHAIN_REFUSED", "is outside the requested day"),
        (date(2025, 12, 31), utc(2026, 1, 1), "OBSERVATION_OUTSIDE_DATA_WINDOW", ""),
    ],
    ids=["past-the-day", "before-the-day", "holdout"],
)
def test_ruling_13_a_repeat_stamped_outside_the_day_or_the_window_refuses_by_that_guard_first(
    day: date, repeat_at: datetime, reason: str, detail: str
) -> None:
    first = fx.execution("a", datetime(day.year, day.month, day.day, 5, tzinfo=UTC))
    repeat = fx.execution("a", repeat_at)
    refusal = refused(reason, kraken.read_execution_day, make_fetcher(day_world([fx.execution_page([first, repeat])], day=day)), day)
    assert detail in str(refusal)


def test_ruling_13_copies_change_no_hour_record_row_or_step_back() -> None:
    _, executions = liquidation_day()
    series = {hour: 0 for hour in fx.hourly(utc(2021, 6, 1), utc(2021, 6, 2))}
    series[utc(2021, 6, 1, 1)] = "1500"
    series[utc(2021, 6, 1, 3)] = "50"
    listings = {
        "plain": [fx.execution_page(executions)],
        # the two first liquidations and a trade listed twice in a row; the third liquidation again at the end
        "copies": [fx.execution_page(executions[:3] + executions[:3] + executions[3:] + executions[4:5])],
        "copies across pages": [fx.execution_page(executions[:3], token="token-0"), fx.execution_page(executions + executions[::-1])],
    }
    collections = {
        name: kraken.read_liquidations(make_fetcher(day_world(pages, series)), DAY, DAY, incidents=()) for name, pages in listings.items()
    }
    assert {name: (item.duplicate_copies, item.out_of_order_steps) for name, item in collections.items()} == {
        "plain": (0, 0), "copies": (4, 0), "copies across pages": (3 + len(executions), 0),
    }
    plain = collections["plain"]
    assert len(plain.rows) == 3

    def classified(collection: kraken.KrakenLiquidationCollection) -> list[tuple[datetime, str, str]]:
        return [(hour.hour_start, hour.feed_status, hour.corroboration) for hour in collection.hours]

    for collection in collections.values():
        assert collection.rows == plain.rows and classified(collection) == classified(plain)
        assert without_page_digests(collection) == without_page_digests(plain)


def test_ruling_13_an_element_nested_to_any_depth_is_compared_or_refused_never_raised() -> None:
    limit = deepest_decodable_nesting()
    outcomes = set()
    for depth in range(limit - 12, limit + 2):
        same = nested(depth)
        other = b"[" * depth + b"1" + b"]" * depth
        for repeat, expected in ((same, "DUPLICATE_COPY"), (other, "DUPLICATE_PROVIDER_RECORD")):
            try:
                read = kraken.read_execution_day(make_fetcher(day_world([page_of(with_extra(same), with_extra(repeat))])), DAY)
            except BackfillRefused as refusal:
                assert refusal.reason_code in {expected, "RESPONSE_SHAPE_REFUSED"}, (depth, str(refusal))
                outcomes.add(refusal.reason_code)
            else:
                assert expected == "DUPLICATE_COPY" and read.duplicate_copies == 1, depth
                outcomes.add(expected)
    assert outcomes == {"DUPLICATE_COPY", "DUPLICATE_PROVIDER_RECORD", "RESPONSE_SHAPE_REFUSED"}


@pytest.mark.parametrize("step", ["loads", "dumps"])
def test_ruling_13_a_page_too_deep_to_compare_its_elements_refuses(monkeypatch: pytest.MonkeyPatch, step: str) -> None:
    def loads(data: Any, **hooks: Any) -> Any:
        if hooks.get("parse_int") is not None:  # the comparison's readings, not the page's own
            raise RecursionError
        return json.loads(data, **hooks)

    def dumps(*args: Any, **kwargs: Any) -> str:
        raise RecursionError

    stand_in = SimpleNamespace(loads=loads if step == "loads" else json.loads, dumps=dumps if step == "dumps" else json.dumps)
    monkeypatch.setattr(kraken, "json", stand_in)
    a = fx.execution("a", utc(2021, 6, 1, 4))
    refusal = refused("RESPONSE_SHAPE_REFUSED", kraken.read_execution_day, make_fetcher(day_world([fx.execution_page([a])])), DAY)
    assert str(refusal).endswith("an execution page is nested too deeply to compare its elements")


def test_an_execution_in_the_holdout_is_an_exposure() -> None:
    transport = day_world([fx.execution_page([fx.execution("a", utc(2026, 1, 1))])], day=date(2025, 12, 31))
    refused("OBSERVATION_OUTSIDE_DATA_WINDOW", kraken.read_execution_day, make_fetcher(transport), date(2025, 12, 31))


def test_the_series_request_ends_at_the_days_last_hour() -> None:
    transport = day_world([fx.execution_page([])], day=date(2025, 12, 31))
    kraken.read_series_day(make_fetcher(transport), date(2025, 12, 31))
    assert transport.urls[-1].endswith("interval=3600&since=1767139200&to=1767222000")  # 2025-12-31 00:00 .. 23:00


@pytest.mark.parametrize(
    "body",
    [
        fx.series_body({utc(2021, 6, 1, 1): 5}, more=True),
        fx.series_body({utc(2021, 6, 1, 1): 5}, errors=["boom"]),
        fx.series_body({utc(2021, 6, 1, 1): 5}, quoted=False),
        fx.series_body({utc(2021, 6, 1, 1): -1}),
        fx.series_body({utc(2021, 6, 1, 1): "+5"}),
        fx.series_body({utc(2021, 6, 1, 1): "05"}),
        fx.series_body({utc(2021, 6, 1, 1): " 5"}),
        fx.series_body({utc(2021, 6, 1, 1): "NaN"}),
        fx.series_body({utc(2021, 6, 1, 1): "Infinity"}),
        fx.series_body({utc(2021, 6, 1, 1): "5."}),
        fx.series_body({utc(2021, 6, 1, 1): ""}),
        fx.series_body({utc(2021, 6, 2): 5}),
        b'{"result":{"timestamp":[1622509200000],"data":["5"],"more":false},"errors":[]}',
        b'{"result":{"timestamp":[1622509200],"data":["5","6"],"more":false},"errors":[]}',
        b'{"result":{"timestamp":[],"data":[],"more":false,"x":1},"errors":[]}',
    ],
    ids=[
        "more", "errors", "number-value", "negative", "plus-sign", "leading-zero", "space", "nan", "infinity",
        "bare-point", "empty", "outside-day", "milliseconds", "unpaired", "extra-key",
    ],
)
def test_ruling_5_an_unexpected_series_shape_is_refused(body: bytes) -> None:
    refused("RESPONSE_SHAPE_REFUSED", kraken.parse_liquidation_volume, body, since=utc(2021, 6, 1), to=utc(2021, 6, 1, 23))


@pytest.mark.parametrize(
    ("spelled", "value"),
    [("0", "0"), ("1234567", "1234567"), ("1500.20", "1500.20"), ("0.00000000", "0E-8"), ("1.5e+3", "1.5E+3")],
)
def test_the_live_series_spells_each_value_as_a_decimal_string(spelled: str, value: str) -> None:
    # Part B's first step (2026-11-05): the live chart's values are JSON strings of digits; the parser keeps their digits
    hour = utc(2021, 6, 1, 1)
    series = kraken.parse_liquidation_volume(
        fx.series_body({hour: spelled}), since=utc(2021, 6, 1), to=utc(2021, 6, 1, 23)
    )
    assert list(series) == [hour] and str(series[hour]) == str(Decimal(value)) and series[hour].as_tuple() == Decimal(value).as_tuple()


@pytest.mark.parametrize(
    ("total", "published", "agrees"),
    [
        ("1500", "1500", True),
        ("1500.4", "1500", True),
        ("1500.5", "1500", True),  # half-even
        ("1501.5", "1501", False),  # half-even rounds to 1502
        ("1500.6", "1500", False),
        ("1500.25", "1500.2", True),
        ("1500.26", "1500.2", False),
        ("1549", "1.5E+3", True),
        ("0", "0", True),
        ("0.4", "0", True),
        ("1", "0", False),
    ],
)
def test_ruling_3_agreement_is_equality_at_the_series_precision(total: str, published: str, agrees: bool) -> None:
    assert kraken.corroborates(Decimal(total), Decimal(published)) is agrees


def liquidation_day() -> tuple[FakeTransport, list[dict[str, Any]]]:
    executions = [
        fx.execution("l1", utc(2021, 6, 1, 1, 10), "1200", order_type="Liquidation", direction="Sell"),
        fx.execution("l2", utc(2021, 6, 1, 1, 20), "300.5", order_type="Liquidation", direction="Buy"),
        fx.execution("t1", utc(2021, 6, 1, 1, 30)),
        fx.execution("t2", utc(2021, 6, 1, 2, 0)),
        fx.execution("l3", utc(2021, 6, 1, 3, 59), "50", order_type="Liquidation", direction="Sell"),
    ]
    executions += [fx.execution(f"x{hour}", utc(2021, 6, 1, hour, 30)) for hour in range(4, 24)]
    series = {hour: 0 for hour in fx.hourly(utc(2021, 6, 1), utc(2021, 6, 2))}
    series[utc(2021, 6, 1, 1)] = "1500"
    series[utc(2021, 6, 1, 3)] = "50"
    return day_world([fx.execution_page(executions)], series), executions


def test_hours_are_classified_by_the_completeness_rule_and_corroborated() -> None:
    transport, _ = liquidation_day()
    collection = kraken.read_liquidations(make_fetcher(transport), DAY, DAY, incidents=())
    status = {hour.hour_start.hour: (hour.feed_status, hour.corroboration) for hour in collection.hours}
    assert status[0] == (epic_x.FEED_STATUS_SOURCE_UNAVAILABLE, v2.CORROBORATION_NOT_APPLICABLE)  # no execution
    assert status[1] == (epic_x.FEED_STATUS_OBSERVED_WITH_EVENTS, v2.CORROBORATION_AGREES)  # 1500.5 at precision 0
    assert status[2] == (epic_x.FEED_STATUS_OBSERVED_ZERO_EVENTS, v2.CORROBORATION_AGREES)
    assert status[3] == (epic_x.FEED_STATUS_OBSERVED_WITH_EVENTS, v2.CORROBORATION_AGREES)
    assert [(row.observation_time.hour, row.side, row.notional_usd) for row in collection.rows] == [
        (1, "long", Decimal("1200")),
        (1, "short", Decimal("300.5")),
        (3, "long", Decimal("50")),
    ]
    row = collection.rows[0]
    assert (row.exchange, row.symbol, row.timeframe, row.quantity_unit, row.quantity) == (
        "kraken_futures", "PI_XBTUSD", "1h", "contracts", Decimal("1200")
    )
    assert row.available_at == row.ingested_at == RETRIEVED_AT


def test_an_incident_hour_is_unavailable_even_with_executions() -> None:
    transport, _ = liquidation_day()
    incident = ((utc(2021, 6, 1, 1, 50), utc(2021, 6, 1, 2, 5)),)
    collection = kraken.read_liquidations(make_fetcher(transport), DAY, DAY, incidents=incident)
    status = {hour.hour_start.hour: hour.feed_status for hour in collection.hours}
    assert status[1] == status[2] == epic_x.FEED_STATUS_SOURCE_UNAVAILABLE
    assert {row.observation_time.hour for row in collection.rows} == {3}
    assert kraken.RBT002_RECORDED_INCIDENTS == ((utc(2021, 11, 10, 5, 9), utc(2021, 11, 10, 5, 19)),)


def test_a_missing_or_disagreeing_series_value_is_recorded_and_the_builder_refuses_it() -> None:
    transport, executions = liquidation_day()
    series = {hour: 0 for hour in fx.hourly(utc(2021, 6, 1), utc(2021, 6, 2))}
    series[utc(2021, 6, 1, 1)] = "1502"
    del series[utc(2021, 6, 1, 3)]
    start = utc(2021, 6, 1)
    transport.add(kraken.liquidation_volume_url(start, start + timedelta(hours=23)), fx.series_body(series))
    collection = kraken.read_liquidations(make_fetcher(transport), DAY, DAY, incidents=())
    status = {hour.hour_start.hour: hour.corroboration for hour in collection.hours}
    assert (status[1], status[3]) == (v2.CORROBORATION_DISAGREES, v2.CORROBORATION_SERIES_UNAVAILABLE)
    with pytest.raises(v1.ReplayInputRefused) as caught:
        v2.build_extended_replay_snapshot(
            shared_snapshot=rbt001a.shared_snapshot(), liquidations=collection.rows, liquidation_hours=collection.hours
        )
    assert caught.value.reason_code == "LIQUIDATION_CORROBORATION_DISAGREES"


def test_an_unknown_liquidation_side_refuses_the_day() -> None:
    page = fx.execution_page([fx.execution("l1", utc(2021, 6, 1, 1), order_type="Liquidation", direction="sell")])
    refused("LIQUIDATION_SIDE_UNKNOWN", kraken.read_liquidations, make_fetcher(day_world([page])), DAY, DAY, incidents=())


def test_the_hour_evidence_file_binds_every_hour_and_the_v2_builder_admits_the_rows() -> None:
    transport, executions = liquidation_day()
    collection = kraken.read_liquidations(make_fetcher(transport), DAY, DAY, incidents=())
    typed = kraken.parse_liquidation_hour_evidence(collection.evidence_bytes, expected_sha256=collection.evidence_sha256)
    assert typed == collection.hours and len(typed) == 24
    payload = json.loads(collection.evidence_bytes)
    assert payload["hours"][1]["liquidation_uids"] == ["l1", "l2"] and payload["hours"][1]["series_value"] == "1500"
    assert payload["corroboration_rule"] == kraken.CORROBORATION_RULE and payload["rule"] == v2.LIQUIDATION_COMPLETENESS_VERSION
    record_digest = hashlib.sha256(v1.canonical_json_bytes(payload["hours"][1])).hexdigest()
    assert typed[1].evidence_sha256 == record_digest
    snapshot = v2.build_extended_replay_snapshot(
        shared_snapshot=rbt001a.shared_snapshot(), liquidations=collection.rows, liquidation_hours=collection.hours
    )
    assert [row.available_at for row in snapshot.liquidations] == [utc(2021, 6, 1, 2), utc(2021, 6, 1, 2), utc(2021, 6, 1, 4)]


def evidence_variant(change: Any) -> tuple[bytes, str]:
    transport, _ = liquidation_day()
    collection = kraken.read_liquidations(make_fetcher(transport), DAY, DAY, incidents=())
    payload = json.loads(collection.evidence_bytes)
    change(payload)
    data = v1.canonical_json_bytes(payload)
    return data, hashlib.sha256(data).hexdigest()


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p.update(rule="OTHER"),
        lambda p: p.update(extra=1),
        lambda p: p["hours"].reverse(),
        lambda p: p["hours"][0].update(hour_start="2021-06-01T00:00:00Z"),
        lambda p: p["hours"][0].update(hour_start="2021-06-01T00:30:00+00:00"),
        lambda p: p["hours"][0].pop("incident"),
        lambda p: p["hours"].__setitem__(1, p["hours"][0]),
    ],
    ids=["rule", "extra-key", "order", "spelling", "off-hour", "missing-key", "repeated-hour"],
)
def test_a_malformed_hour_evidence_file_is_refused(change: Any) -> None:
    data, digest = evidence_variant(change)
    refused("RESPONSE_SHAPE_REFUSED", kraken.parse_liquidation_hour_evidence, data, expected_sha256=digest)


UNAVAILABLE, ZERO, WITH = (
    epic_x.FEED_STATUS_SOURCE_UNAVAILABLE,
    epic_x.FEED_STATUS_OBSERVED_ZERO_EVENTS,
    epic_x.FEED_STATUS_OBSERVED_WITH_EVENTS,
)


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        (lambda p: p.update(contract_size_usd="100"), "RESPONSE_SHAPE_REFUSED"),
        (lambda p: p.update(liquidation_order_type="Limit"), "RESPONSE_SHAPE_REFUSED"),
        (lambda p: p.update(source="elsewhere"), "RESPONSE_SHAPE_REFUSED"),
        (lambda p: p.update(licence="other"), "RESPONSE_SHAPE_REFUSED"),
        (lambda p: p.update(retrieved_at="2026-11-05T10:00:00Z"), "RESPONSE_SHAPE_REFUSED"),
        (lambda p: p.update(incidents=[{"start": "2021-06-01T02:00:00+00:00", "end": "2021-06-01T01:00:00+00:00"}]), "RESPONSE_SHAPE_REFUSED"),
        (lambda p: p.update(incidents=[{"start": "2021-06-01T01:00:00+00:00", "end": "2021-06-01T01:30:00+00:00"}]), "RESPONSE_SHAPE_REFUSED"),
        (lambda p: p["hours"][1].update(incident=True), "RESPONSE_SHAPE_REFUSED"),
        (lambda p: p["hours"][0].update(incident=True), "RESPONSE_SHAPE_REFUSED"),
        (lambda p: p["hours"][0].update(feed_status=ZERO, corroboration="AGREES", series_value="999"), "RESPONSE_SHAPE_REFUSED"),
        (lambda p: p["hours"][1].update(corroboration="DISAGREES"), "RESPONSE_SHAPE_REFUSED"),
        (lambda p: p["hours"][1].update(series_value="1499"), "RESPONSE_SHAPE_REFUSED"),
        (lambda p: p["hours"][1].update(series_value="+1500"), "RESPONSE_SHAPE_REFUSED"),
        (lambda p: p["hours"][1].update(series_sha256=None), "RESPONSE_SHAPE_REFUSED"),
        (lambda p: p["hours"][1].update(long_quantity="1200.0"), "RESPONSE_SHAPE_REFUSED"),
        (lambda p: p["hours"][1].update(liquidation_uids=["l2", "l1"]), "RESPONSE_SHAPE_REFUSED"),
        (lambda p: p["hours"][1].update(execution_count=1), "RESPONSE_SHAPE_REFUSED"),
        (lambda p: p["hours"][1].update(feed_status=ZERO), "RESPONSE_SHAPE_REFUSED"),
        (lambda p: p["hours"][2].update(long_quantity="5"), "RESPONSE_SHAPE_REFUSED"),
        (lambda p: p["hours"][2].update(feed_status=WITH), "RESPONSE_SHAPE_REFUSED"),
        (lambda p: p["hours"][1].update(pages_sha256=["x"]), "RESPONSE_SHAPE_REFUSED"),
        (lambda p: p["hours"][1].update(long_quantity="9" * 81), "RESPONSE_SHAPE_REFUSED"),
        (lambda p: p["hours"][-1].update(hour_start="2026-01-01T00:00:00+00:00"), "OBSERVATION_OUTSIDE_DATA_WINDOW"),
        (lambda p: p["hours"][0].update(hour_start="2019-12-31T23:00:00+00:00"), "OBSERVATION_OUTSIDE_DATA_WINDOW"),
    ],
    ids=[
        "contract-size", "order-type", "source", "licence", "retrieved-at", "reversed-incident", "incident-without-flag",
        "flag-without-incident", "flag-on-empty-hour", "observed-empty-hour-agrees-999", "corroboration-flipped",
        "series-changed", "series-spelling", "series-without-digest", "quantity-spelling", "uids-unsorted",
        "count-below-uids", "liquidations-as-zero-events", "quantity-without-liquidation", "zero-events-as-with",
        "page-digest", "quantity-too-wide", "holdout-hour", "pre-2020-hour",
    ],
)
def test_the_hour_evidence_parser_accepts_only_what_it_can_re_derive(change: Any, reason: str) -> None:
    data, digest = evidence_variant(change)
    refused(reason, kraken.parse_liquidation_hour_evidence, data, expected_sha256=digest)


def test_the_published_precision_survives_the_evidence_file() -> None:
    # 1500.4 rounds to 1500 at the precision of "1500" and to 1500.4 at the precision of "1500.0"
    outcomes = {}
    for published in ("1500", "1500.0"):
        executions = [fx.execution("l1", utc(2021, 6, 1, 1, 10), "1500.4", order_type="Liquidation", direction="Sell")]
        executions += [fx.execution(f"x{hour}", utc(2021, 6, 1, hour, 30)) for hour in range(24)]
        executions.sort(key=lambda element: element["timestamp"])
        series = {hour: 0 for hour in fx.hourly(utc(2021, 6, 1), utc(2021, 6, 2))}
        series[utc(2021, 6, 1, 1)] = published
        collection = kraken.read_liquidations(make_fetcher(day_world([fx.execution_page(executions)], series)), DAY, DAY, incidents=())
        stored = json.loads(collection.evidence_bytes)["hours"][1]
        typed = kraken.parse_liquidation_hour_evidence(collection.evidence_bytes, expected_sha256=collection.evidence_sha256)
        outcomes[published] = (stored["series_value"], typed[1].corroboration)
    assert outcomes == {"1500": ("1500", v2.CORROBORATION_AGREES), "1500.0": ("1500.0", v2.CORROBORATION_DISAGREES)}


@pytest.mark.parametrize(("published", "stored"), [("0.00000000", "0E-8"), ("1.5e+3", "1.5E+3"), ("1500.0", "1500.0")])
def test_the_evidence_bytes_do_not_depend_on_the_callers_decimal_capitals(published: str, stored: str) -> None:
    # re-review N3: the same responses give the same bytes, and each file reads back under either setting
    executions = [fx.execution(f"x{hour}", utc(2021, 6, 1, hour, 30)) for hour in range(24)]
    series = {hour: 0 for hour in fx.hourly(utc(2021, 6, 1), utc(2021, 6, 2))}
    series[utc(2021, 6, 1, 1)] = published
    collections = {}
    for capitals in (0, 1):
        with localcontext() as caller:
            caller.capitals = capitals
            transport = day_world([fx.execution_page(executions)], series)
            collections[capitals] = kraken.read_liquidations(make_fetcher(transport), DAY, DAY, incidents=())
    assert collections[0].evidence_bytes == collections[1].evidence_bytes
    assert json.loads(collections[0].evidence_bytes)["hours"][1]["series_value"] == stored
    for capitals in (0, 1):
        written = collections[1 - capitals]
        with localcontext() as caller:
            caller.capitals = capitals
            hours = kraken.parse_liquidation_hour_evidence(written.evidence_bytes, expected_sha256=written.evidence_sha256)
        assert hours == collections[0].hours


def test_hour_evidence_must_be_the_bound_canonical_bytes() -> None:
    transport, _ = liquidation_day()
    collection = kraken.read_liquidations(make_fetcher(transport), DAY, DAY, incidents=())
    refused("RESPONSE_SHAPE_REFUSED", kraken.parse_liquidation_hour_evidence, collection.evidence_bytes, expected_sha256="0" * 64)
    spaced = json.dumps(json.loads(collection.evidence_bytes), sort_keys=True).encode()
    refused("RESPONSE_SHAPE_REFUSED", kraken.parse_liquidation_hour_evidence, spaced, expected_sha256=hashlib.sha256(spaced).hexdigest())


# --- Coin Metrics ----------------------------------------------------------------------------


def coinmetrics_world(rows: list[tuple[date, str]], first: date, last: date, **kwargs: Any) -> FakeTransport:
    transport = FakeTransport()
    transport.add(coinmetrics.timeseries_url(first, last), fx.coinmetrics_page(rows, **kwargs))
    return transport


def test_market_caps_become_the_v2_evidence_file_the_builder_admits() -> None:
    first, last = date(2020, 1, 1), date(2020, 1, 5)
    rows = [(first + timedelta(days=k), f"{130000000000 + k}.5") for k in range(5) if k != 2]
    collection = coinmetrics.read_market_caps(make_fetcher(coinmetrics_world(rows, first, last)), first, last)
    assert collection.missing_days == (date(2020, 1, 3),)
    evidence = collection.evidence()
    assert evidence.rows == tuple((day, Decimal(value)) for day, value in rows)
    assert (evidence.source, evidence.licence) == (coinmetrics.COINMETRICS_SOURCE, coinmetrics.COINMETRICS_LICENCE)
    snapshot = v2.build_extended_replay_snapshot(shared_snapshot=rbt001a.shared_snapshot(), market_cap_evidence=evidence)
    assert snapshot.market_caps[0].available_at == utc(2020, 1, 3)


def test_the_market_cap_request_is_exactly_the_bounded_inclusive_query() -> None:
    first, last = date(2020, 1, 1), date(2020, 1, 5)
    transport = coinmetrics_world([(first, "1")], first, last)
    coinmetrics.read_market_caps(make_fetcher(transport), first, last)
    (url,) = transport.urls
    assert url.split("?", 1)[0] == "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
    assert dict(parse_qsl(url.split("?", 1)[1], strict_parsing=True)) == {
        "assets": "btc",
        "metrics": "CapMrktCurUSD",
        "frequency": "1d",
        "start_time": "2020-01-01",
        "end_time": "2020-01-05",
        "end_inclusive": "true",
        "page_size": "10000",
    }


def continuation_url(first: date, last: date, token: str = "token", **changes: Any) -> str:
    query = {**coinmetrics.bounded_query(first, last), "next_page_token": token, **changes}
    return f"{coinmetrics.COINMETRICS_TIMESERIES_URL}?{urlencode({key: value for key, value in query.items() if value is not None})}"


def test_a_market_cap_continuation_is_rebuilt_from_the_bounded_query() -> None:
    first, last = date(2020, 1, 1), date(2020, 1, 2)
    # the provider's own spelling, in another parameter order, names the same bounded query
    provider_url = continuation_url(first, last)
    reordered = provider_url.split("?")[0] + "?" + "&".join(reversed(provider_url.split("?")[1].split("&")))
    transport = coinmetrics_world([(first, "1")], first, last, next_url=reordered)
    transport.add(coinmetrics.timeseries_url(first, last, "token"), fx.coinmetrics_page([(last, "2")]))
    assert len(coinmetrics.read_market_caps(make_fetcher(transport), first, last).rows) == 2
    assert transport.urls == [coinmetrics.timeseries_url(first, last), coinmetrics.timeseries_url(first, last, "token")]


@pytest.mark.parametrize(
    ("next_url", "token", "reason"),
    [
        ("https://elsewhere.example/page", "token", "RESPONSE_SHAPE_REFUSED"),
        ("pre-2020", "token", "CONTINUATION_CHAIN_REFUSED"),
        ("holdout", "token", "CONTINUATION_CHAIN_REFUSED"),
        ("unbounded", "token", "CONTINUATION_CHAIN_REFUSED"),
        ("exclusive", "token", "CONTINUATION_CHAIN_REFUSED"),
        ("extra", "token", "CONTINUATION_CHAIN_REFUSED"),
        ("other-token", "token", "CONTINUATION_CHAIN_REFUSED"),
        ("bounded", None, "CONTINUATION_CHAIN_REFUSED"),
    ],
    ids=["foreign", "pre-2020", "holdout", "unbounded", "exclusive", "extra-parameter", "token-mismatch", "no-token"],
)
def test_a_market_cap_continuation_outside_the_bounded_query_is_never_requested(
    next_url: str, token: str | None, reason: str
) -> None:
    first, last = date(2020, 1, 1), date(2020, 1, 31)
    urls = {
        "pre-2020": continuation_url(first, last, start_time="2019-12-01"),
        "holdout": continuation_url(first, last, end_time="2026-06-30"),
        "unbounded": continuation_url(first, last, start_time=None, end_time=None),
        "exclusive": continuation_url(first, last, end_inclusive="false"),
        "extra": continuation_url(first, last, paging_from="start"),
        "other-token": continuation_url(first, last, token="other"),
        "bounded": continuation_url(first, last),
    }
    transport = coinmetrics_world([(first, "1")], first, last, next_url=urls.get(next_url, next_url), token=token)
    refused(reason, coinmetrics.read_market_caps, make_fetcher(transport), first, last)
    assert transport.urls == [coinmetrics.timeseries_url(first, last)]


def test_a_repeated_market_cap_token_refuses_the_chain() -> None:
    first, last = date(2020, 1, 1), date(2020, 1, 3)
    transport = coinmetrics_world([(first, "1")], first, last, next_url=continuation_url(first, last))
    transport.add(
        coinmetrics.timeseries_url(first, last, "token"),
        fx.coinmetrics_page([(date(2020, 1, 2), "2")], next_url=continuation_url(first, last)),
    )
    refused("CONTINUATION_CHAIN_REFUSED", coinmetrics.read_market_caps, make_fetcher(transport), first, last)
    assert len(transport.urls) == 2


@pytest.mark.parametrize(
    ("rows", "kwargs", "reason"),
    [
        ([(date(2026, 1, 1), "1")], {}, "OBSERVATION_OUTSIDE_DATA_WINDOW"),
        ([(date(2019, 12, 31), "1")], {}, "OBSERVATION_OUTSIDE_DATA_WINDOW"),
        ([(date(2020, 2, 1), "1")], {}, "RESPONSE_SHAPE_REFUSED"),
        ([(date(2020, 1, 1), "0")], {}, "RESPONSE_SHAPE_REFUSED"),
        ([(date(2020, 1, 1), "1")], {"extra": {"CapMrktCurUSD.status": "x"}}, "RESPONSE_SHAPE_REFUSED"),
        ([(date(2020, 1, 1), "1"), (date(2020, 1, 1), "2")], {}, "DUPLICATE_PROVIDER_RECORD"),
        ([], {}, "RESPONSE_SHAPE_REFUSED"),
    ],
    ids=["holdout", "pre-2020", "unrequested-day", "zero", "extra-key", "duplicate", "empty"],
)
def test_a_malformed_market_cap_response_is_refused(rows: list[tuple[date, str]], kwargs: dict[str, Any], reason: str) -> None:
    first, last = date(2020, 1, 1), date(2020, 1, 31)
    refused(reason, coinmetrics.read_market_caps, make_fetcher(coinmetrics_world(rows, first, last, **kwargs)), first, last)


def test_a_market_cap_value_must_be_a_decimal_string_and_the_stamp_a_day() -> None:
    first, last = date(2020, 1, 1), date(2020, 1, 1)
    for item in (
        {"asset": "btc", "time": "2020-01-01T00:00:00.000000000Z", "CapMrktCurUSD": 5},
        {"asset": "btc", "time": "2020-01-01T01:00:00.000000000Z", "CapMrktCurUSD": "5"},
        {"asset": "eth", "time": "2020-01-01T00:00:00.000000000Z", "CapMrktCurUSD": "5"},
    ):
        transport = FakeTransport()
        transport.add(coinmetrics.timeseries_url(first, last), json.dumps({"data": [item]}).encode())
        refused("RESPONSE_SHAPE_REFUSED", coinmetrics.read_market_caps, make_fetcher(transport), first, last)
    refused("REQUEST_OUTSIDE_DATA_WINDOW", coinmetrics.timeseries_url, date(2025, 12, 1), date(2026, 1, 1))


# --- CoinGlass (UNVERIFIED shapes) -----------------------------------------------------------


def coinglass_world(flows: dict[date, dict[str, Any]], assets: dict[str, dict[date, Any]], first: date, last: date) -> FakeTransport:
    transport = FakeTransport()
    transport.add(coinglass.FLOW_HISTORY_URL, fx.coinglass_flow_page(flows))
    for ticker, history in assets.items():
        transport.add(coinglass.fund_history_url(ticker), fx.coinglass_fund_page(history, ticker=ticker))
    return transport


def coinglass_read(transport: FakeTransport, funds: tuple[str, ...], first: date, last: date) -> coinglass.EtfFlowCollectionRead:
    fetcher = coinglass.coinglass_fetcher(transport, RetrievalLog(), api_key="key-123", clock=lambda: RETRIEVED_AT)
    return coinglass.read_etf_flows(fetcher, funds, first, last)


def test_ruling_10_coinglass_urls_carry_no_date_and_bad_requests_fetch_nothing() -> None:
    assert coinglass.FLOW_HISTORY_URL == "https://open-api-v4.coinglass.com/api/etf/bitcoin/flow-history"
    assert coinglass.fund_history_url("IBIT") == "https://open-api-v4.coinglass.com/api/etf/bitcoin/history?ticker=IBIT"
    for bad in ("", "ibit", "IBIT&start_time=1", " IBIT", "IBIT ", "ABCDEFGHIJK", "1BIT"):
        refused("PROVIDER_REQUEST_MISMATCH", coinglass.fund_history_url, bad)
    transport = FakeTransport()
    fetcher = coinglass.coinglass_fetcher(transport, RetrievalLog(), api_key="key")
    # requested days outside the window, a bad ticker or a repeated fund refuse before any request
    refused("REQUEST_OUTSIDE_DATA_WINDOW", coinglass.read_etf_flows, fetcher, ("IBIT",), date(2025, 12, 1), date(2026, 1, 1))
    refused("REQUEST_OUTSIDE_DATA_WINDOW", coinglass.read_etf_flows, fetcher, ("IBIT",), date(2024, 1, 11), date(2024, 1, 10))
    refused("REQUEST_OUTSIDE_DATA_WINDOW", coinglass.read_etf_flows, fetcher, ("IBIT",), date(2023, 1, 1), date(2023, 12, 31))
    refused("PROVIDER_REQUEST_MISMATCH", coinglass.read_etf_flows, fetcher, ("IBIT", "ibit"), date(2024, 1, 11), date(2024, 1, 31))
    refused("PROVIDER_REQUEST_MISMATCH", coinglass.read_etf_flows, fetcher, ("IBIT", "IBIT"), date(2024, 1, 11), date(2024, 1, 31))
    assert transport.calls == []
    refused("PROVIDER_RESPONSE_REFUSED", coinglass.coinglass_fetcher, transport, RetrievalLog(), api_key="")


@pytest.mark.parametrize(
    "key",
    [
        "synthetic-secret\ncontinued", "synthetic-secret\r\n", "synthetic secret", " synthetic-secret",
        "synthetic-secret ", "synthetic-secret\x00", "synthetic-s\u00e9cret", "synthetic-secret" * 20, None, b"synthetic-secret",
    ],
)
def test_review_b6_a_key_http_does_not_allow_refuses_without_being_quoted(key: Any) -> None:
    caught = refused("PROVIDER_RESPONSE_REFUSED", coinglass.coinglass_fetcher, FakeTransport(), RetrievalLog(), api_key=key)
    assert "synthetic" not in str(caught)


def test_review_b3_the_etf_rows_rebuild_from_their_projections_alone() -> None:
    first, second = date(2024, 1, 11), date(2024, 1, 12)
    transport = coinglass_world({first: {"IBIT": 5, "GBTC": -7}, second: {"IBIT": 6}}, {"IBIT": {first: 9}, "GBTC": {second: 11}}, first, second)
    fetcher = coinglass.coinglass_fetcher(transport, RetrievalLog(), api_key="key-123", clock=AdvancingClock())
    read = coinglass.read_etf_flows(fetcher, None, first, second)
    flow, gbtc, ibit = read.projections
    assert [item.url for item in (gbtc, ibit)] == [coinglass.fund_history_url("GBTC"), coinglass.fund_history_url("IBIT")]
    assert coinglass.etf_flows_from_projections(flow, (gbtc, ibit)) == read  # rows, instants, missing AUM and projections
    for histories in ((ibit, gbtc), (ibit,), (gbtc, ibit, ibit), ()):
        refused("PROVIDER_REQUEST_MISMATCH", coinglass.etf_flows_from_projections, flow, histories)
    refused("PROVIDER_REQUEST_MISMATCH", coinglass.etf_flows_from_projections, gbtc, (gbtc, ibit))
    refused("PROVIDER_REQUEST_MISMATCH", coinglass.etf_flows_from_projections, dataclasses.replace(flow, url=flow.url + "?x=1"), (gbtc, ibit))
    assert coinglass.fund_of_history_url(coinglass.fund_history_url("IBIT")) == "IBIT"
    for bad in (coinglass.FLOW_HISTORY_URL, coinglass.fund_history_url("IBIT") + "&start_time=1", None):
        refused("PROVIDER_REQUEST_MISMATCH", coinglass.fund_of_history_url, bad)


def test_ruling_10_a_parser_refuses_bytes_that_were_not_projected() -> None:
    refused("PROVIDER_RESPONSE_REFUSED", coinglass.parse_flow_history, fx.coinglass_flow_page({}))
    refused("PROVIDER_RESPONSE_REFUSED", coinglass.parse_fund_history, fx.coinglass_fund_page({}), ticker="IBIT")


def test_etf_flows_join_the_same_days_net_assets_and_never_log_the_key() -> None:
    first, last = date(2024, 1, 11), date(2024, 1, 12)
    flows = {first: {"IBIT": 111700000, "GBTC": -95100000, "OTHER": 1}, last: {"IBIT": 386000000, "GBTC": None}}
    assets = {"IBIT": {first: 1000, last: 2000.5}, "GBTC": {first: 28000000000}}
    transport = coinglass_world(flows, assets, first, last)
    read = coinglass_read(transport, ("IBIT", "GBTC"), first, last)
    assert [(row.fund, row.observation_date, row.flow_usd, row.aum_usd) for row in read.flows] == [
        ("GBTC", first, Decimal("-95100000"), Decimal("28000000000")),
        ("IBIT", first, Decimal("111700000"), Decimal("1000")),
        ("IBIT", last, Decimal("386000000"), Decimal("2000.5")),
    ]
    assert read.tickers_seen == ("GBTC", "IBIT", "OTHER") and read.missing_aum == ()
    assert {(row.provider, row.revision, row.source) for row in read.flows} == {
        ("coinglass", "FINAL_AS_RETRIEVED", coinglass.FLOW_HISTORY_URL)
    }
    assert all(headers == {"CG-API-KEY": "key-123"} for _, headers in transport.calls)
    assert all("key-123" not in url for url in transport.urls)


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        (fx.coinglass_flow_page({date(2024, 1, 11): {"IBIT": 1}}, code="40001"), "RESPONSE_SHAPE_REFUSED"),
        (fx.coinglass_flow_page({date(2024, 1, 11): {"IBIT": "1"}}), "RESPONSE_SHAPE_REFUSED"),
        (b'{"code":"0","msg":"success","data":[],"extra":1}', "RESPONSE_SHAPE_REFUSED"),
        (b'{"code":"0","msg":"success","data":[{"timestamp":1704931200000,"flow_usd":0,"etf_flows":[]}]}', "RESPONSE_SHAPE_REFUSED"),
        (b'{"code":"0","msg":"success","data":[{"timestamp":1704931200001,"flow_usd":0,"price_usd":1,"etf_flows":[]}]}', "RESPONSE_SHAPE_REFUSED"),
    ],
    ids=["error-code", "string-flow", "extra-key", "missing-key", "not-midnight"],
)
def test_ruling_5_an_unexpected_flow_history_is_refused(body: bytes, reason: str) -> None:
    first, last = date(2024, 1, 11), date(2024, 1, 31)
    transport = coinglass_world({}, {"IBIT": {}}, first, last)
    transport.add(coinglass.FLOW_HISTORY_URL, body)
    refused(reason, coinglass_read, transport, ("IBIT",), first, last)


def test_a_missing_net_asset_value_is_recorded_not_invented() -> None:
    first = date(2024, 1, 11)
    read = coinglass_read(coinglass_world({first: {"IBIT": 5}}, {"IBIT": {}}, first, first), ("IBIT",), first, first)
    assert read.flows[0].aum_usd is None and read.missing_aum == (("IBIT", first),)


def test_a_malformed_fund_history_is_refused() -> None:
    first = date(2024, 1, 11)
    transport = coinglass_world({first: {"IBIT": 5}}, {"IBIT": {first: -1}}, first, first)
    refused("RESPONSE_SHAPE_REFUSED", coinglass_read, transport, ("IBIT",), first, first)
    transport.add(
        coinglass.fund_history_url("IBIT"),
        b'{"code":"0","msg":"success","data":[{"assets_date":1704931200000,"net_assets_usd":1}]}',
    )
    refused("RESPONSE_SHAPE_REFUSED", coinglass_read, transport, ("IBIT",), first, first)


# --- the in-window projection (owner Part B ruling 10) ----------------------------------------


def fetched(body: bytes, url: str = "https://open-api-v4.coinglass.com/api/etf/bitcoin/flow-history") -> sources.Fetched:
    return sources.Fetched(url, body, RETRIEVED_AT)


def day_ms(day: date) -> int:
    return coinglass.utc_day_stamp(day)


# each dropped record carries a sentinel no kept record holds; none may reach a decoder
SENTINELS = {date(2019, 6, 3): 777000001, date(2023, 5, 1): 777000002, date(2026, 1, 2): 777000003, date(2026, 8, 3): 777000004}


def sentinel_flow_page() -> bytes:
    days = {day: {"IBIT": value} for day, value in SENTINELS.items()}
    days |= {date(2024, 1, 11): {"IBIT": 5}, date(2024, 1, 12): {"IBIT": 6}}
    return fx.coinglass_flow_page(days)


def test_ruling_10_the_projection_keeps_the_requested_days_and_counts_the_rest() -> None:
    body = sentinel_flow_page()
    projected = projection.project_records(
        fetched(body), date_keys=("timestamp",), first_day=date(2024, 1, 11), last_day=date(2024, 1, 12), what="flows"
    )
    assert (projected.kept, projected.dropped_prohibited, projected.dropped_unrequested, projected.dropped_holdout) == (2, 1, 1, 2)
    assert (projected.response_sha256, projected.response_size) == (hashlib.sha256(body).hexdigest(), len(body))
    kept = json.loads(projected.body)
    assert kept == {"code": "0", "msg": "success", "data": json.loads(body)["data"][2:4]}
    assert all(str(value).encode() not in projected.body for value in SENTINELS.values())
    assert coinglass.parse_flow_history(projected) == {("IBIT", date(2024, 1, 11)): Decimal(5), ("IBIT", date(2024, 1, 12)): Decimal(6)}
    record = projected.exposure_record()
    assert record["projected_sha256"] == hashlib.sha256(projected.body).hexdigest() and record["dropped_holdout"] == 2
    assert all(str(value) not in json.dumps(record) for value in SENTINELS.values())


def test_ruling_10_no_dropped_value_is_ever_decoded(monkeypatch: pytest.MonkeyPatch) -> None:
    decoded: list[bytes] = []
    real_loads = json.loads

    def spy(data: Any, *args: Any, **kwargs: Any) -> Any:
        decoded.append(data if isinstance(data, bytes) else str(data).encode())
        return real_loads(data, *args, **kwargs)

    monkeypatch.setattr(json, "loads", spy)
    first = date(2024, 1, 11)
    transport = FakeTransport()
    transport.add(coinglass.FLOW_HISTORY_URL, sentinel_flow_page())
    funds = {day: value for day, value in SENTINELS.items()} | {first: 9}
    transport.add(coinglass.fund_history_url("IBIT"), fx.coinglass_fund_page(funds))
    read = coinglass_read(transport, ("IBIT",), first, date(2024, 1, 12))
    assert [(row.observation_date, row.flow_usd, row.aum_usd) for row in read.flows] == [
        (first, Decimal(5), Decimal(9)), (date(2024, 1, 12), Decimal(6), None)
    ]
    assert decoded and not any(str(value).encode() in item for value in SENTINELS.values() for item in decoded)
    assert [item.dropped for item in read.projections] == [4, 4]
    assert [item.url for item in read.projections] == [coinglass.FLOW_HISTORY_URL, coinglass.fund_history_url("IBIT")]


def spy_on_json(monkeypatch: pytest.MonkeyPatch) -> list[bytes]:
    decoded: list[bytes] = []
    real_loads = json.loads

    def spy(data: Any, *args: Any, **kwargs: Any) -> Any:
        decoded.append(data if isinstance(data, bytes) else str(data).encode())
        return real_loads(data, *args, **kwargs)

    monkeypatch.setattr(json, "loads", spy)
    return decoded


def fund_record(assets_day: date, market_day: date, market_price: str) -> str:
    return (
        '{"assets_date":%d,"btc_holdings":1000,"market_date":%d,"market_price":%s,"name":"iShares Bitcoin Trust",'
        '"nav":38.57,"net_assets":9,"premium_discount":-0.16,"shares_outstanding":555700100,"ticker":"IBIT"}'
        % (day_ms(assets_day), day_ms(market_day), market_price)
    )


def test_review_b2_a_projection_on_fewer_date_members_is_refused_before_decoding(monkeypatch: pytest.MonkeyPatch) -> None:
    first = date(2024, 1, 11)
    body = ('{"code":"0","msg":"success","data":[%s]}' % fund_record(first, date(2026, 1, 5), "777000011")).encode()
    decoded = spy_on_json(monkeypatch)
    partial = projection.project_records(
        fetched(body, coinglass.fund_history_url("IBIT")), date_keys=("assets_date",), first_day=first, last_day=first, what="IBIT"
    )
    assert partial.kept == 1  # projected on assets_date alone, the holdout market date stays
    refused("PROVIDER_RESPONSE_REFUSED", coinglass.parse_fund_history, partial, ticker="IBIT")
    assert decoded and not any(b"777000011" in item for item in decoded)
    # projected on both members, the record is dropped and nothing is left to decode
    whole = projection.project_records(
        fetched(body, coinglass.fund_history_url("IBIT")), date_keys=coinglass.FUND_DATE_KEYS, first_day=first, last_day=first, what="IBIT"
    )
    assert (whole.kept, whole.dropped_holdout) == (0, 1) and coinglass.parse_fund_history(whole, ticker="IBIT") == {}
    assert not any(b"777000011" in item for item in decoded)


def test_review_b2_bytes_or_claims_that_are_not_an_exact_projection_are_refused_before_decoding(monkeypatch: pytest.MonkeyPatch) -> None:
    first, second = date(2024, 1, 11), date(2024, 1, 12)
    body = sentinel_flow_page()
    decoded = spy_on_json(monkeypatch)
    forged = projection.ProjectedResponse(
        url=coinglass.FLOW_HISTORY_URL, retrieved_at=RETRIEVED_AT, first_day=first, last_day=second, date_keys=coinglass.FLOW_DATE_KEYS,
        response_sha256=hashlib.sha256(body).hexdigest(), response_size=len(body), body=body, kept=6,
        dropped_prohibited=0, dropped_unrequested=0, dropped_holdout=0,
    )
    refused("PROVIDER_RESPONSE_REFUSED", coinglass.parse_flow_history, forged)  # never projected
    # never projected, though it claims the count a projection would keep
    refused("PROVIDER_RESPONSE_REFUSED", coinglass.parse_flow_history, dataclasses.replace(forged, kept=2))
    genuine = projection.project_records(fetched(body), date_keys=coinglass.FLOW_DATE_KEYS, first_day=first, last_day=second, what="flows")
    for changed in (
        {"last_day": first},  # the bytes hold a day the claim does not request
        {"kept": 1},
        {"date_keys": coinglass.FUND_DATE_KEYS},
        {"date_keys": ("timestamp", "timestamp")},
        {"first_day": datetime(2024, 1, 11, tzinfo=UTC)},
        {"body": body.decode()},
        {"body": genuine.body.replace(b'{"code":', b'{ "code":')},  # the same records, not the projection's bytes
        {"retrieved_at": None},
    ):
        refused("PROVIDER_RESPONSE_REFUSED", coinglass.parse_flow_history, dataclasses.replace(genuine, **changed))
    refused("PROVIDER_RESPONSE_REFUSED", coinglass.parse_fund_history, genuine, ticker="IBIT")  # a flow projection
    assert not any(str(value).encode() in item for value in SENTINELS.values() for item in decoded)
    assert coinglass.parse_flow_history(genuine) == {("IBIT", first): Decimal(5), ("IBIT", second): Decimal(6)}


def test_ruling_10_a_dropped_record_is_never_shape_checked() -> None:
    # a holdout record the strict parser would refuse (unknown field, string value) is dropped, not read
    first = date(2024, 1, 11)
    body = '{"code":"0","msg":"success","data":[%s,{"timestamp":%d,"unexpected":"x","etf_flows":"y"}]}' % (
        FLOW_DAY % ("0", "45000", "5"), day_ms(date(2026, 3, 2))
    )
    transport = FakeTransport()
    transport.add(coinglass.FLOW_HISTORY_URL, body.encode())
    transport.add(coinglass.fund_history_url("IBIT"), fx.coinglass_fund_page({first: 9}))
    read = coinglass_read(transport, ("IBIT",), first, first)
    assert [row.flow_usd for row in read.flows] == [Decimal(5)] and read.projections[0].dropped_holdout == 1


@pytest.mark.parametrize(
    ("assets_day", "market_day", "counted"),
    [
        (date(2024, 1, 11), date(2024, 1, 11), "kept"),
        (date(2024, 1, 11), date(2026, 1, 2), "dropped_holdout"),
        (date(2019, 12, 31), date(2024, 1, 11), "dropped_prohibited"),
        (date(2015, 7, 20), date(2015, 7, 20), "dropped_prohibited"),  # GBTC predates the window: the sealed sample's years
        (date(2024, 1, 11), date(2024, 1, 13), "dropped_unrequested"),
    ],
)
def test_ruling_10_a_fund_record_is_kept_only_when_both_of_its_dates_are_requested(
    assets_day: date, market_day: date, counted: str
) -> None:
    record = json.loads(FUND_DAY % ("1000", "9"))
    record |= {"assets_date": day_ms(assets_day), "market_date": day_ms(market_day)}
    body = json.dumps({"code": "0", "msg": "success", "data": [record]}).encode()
    projected = projection.project_records(
        fetched(body, coinglass.fund_history_url("IBIT")), date_keys=coinglass.FUND_DATE_KEYS,
        first_day=date(2024, 1, 11), last_day=date(2024, 1, 12), what="IBIT history",
    )
    assert getattr(projected, counted) == 1 and projected.kept + projected.dropped == 1


VALID_RECORD = '{"timestamp":1704931200000,"flow_usd":0,"price_usd":1,"etf_flows":[]}'
HOLDOUT_STAMP = day_ms(date(2026, 1, 5))


@pytest.mark.parametrize(
    "body",
    [
        b"",
        b"[]",
        b'{"code":"0","msg":"success","data":[' + VALID_RECORD.encode(),
        b'{"code":"0","msg":"success","data":[]} x',
        b'{"code":"0","msg":"success","data":[]}{}',
        b'{"code":"0","msg":"success","data":[{"timestamp":%d,"name":"unterminated}]}' % HOLDOUT_STAMP,
        b'{"code":"0","msg":"success","data":[{"timestamp":%d,"name":"bad \\q escape"}]}' % HOLDOUT_STAMP,
        b'{"code":"0","msg":"success","data":[{"timestamp":%d,"name":"bad \\u12 escape"}]}' % HOLDOUT_STAMP,
        b'{"code":"0","msg":"success","data":[{"timestamp":%d,"name":"tab\tinside"}]}' % HOLDOUT_STAMP,
        b'{"code":"0","msg":"success","data":[{"timestamp":%d,"flow_usd":01}]}' % HOLDOUT_STAMP,
        b'{"code":"0","msg":"success","data":[{"timestamp":%d,"flow_usd":1.}]}' % HOLDOUT_STAMP,
        b'{"code":"0","msg":"success","data":[{"timestamp":%d,"flow_usd":NaN}]}' % HOLDOUT_STAMP,
        b'{"code":"0","msg":"success","data":[{"timestamp":%d,"flow_usd":nulls}]}' % HOLDOUT_STAMP,
        b'{"code":"0","msg":"success","data":[{"timestamp":%d,"flow_usd":[1,]}]}' % HOLDOUT_STAMP,
        b'{"code":"0","msg":"success","data":[{"timestamp":%d,}]}' % HOLDOUT_STAMP,
        b'{"code":"0","msg":"success","data":[{"timestamp":%d,"x":%s}]}' % (HOLDOUT_STAMP, b"[" * 40 + b"]" * 40),
        b'{"code":"0","msg":"success","data":[{"timestamp":%d,"x":1,"x":2}]}' % HOLDOUT_STAMP,
        b'{"code":"0","msg":"success","data":[{"timestamp":%d,"bad name":1}]}' % HOLDOUT_STAMP,
        b'{"code":"0","msg":"success","data":[{"timestamp":%d,"esc\\u0061ped":1}]}' % HOLDOUT_STAMP,
        b'{"code":"0","msg":"success","data":[{"flow_usd":1}]}',
        b'{"code":"0","msg":"success","data":[{"timestamp":"1704931200000"}]}',
        b'{"code":"0","msg":"success","data":[{"timestamp":1704931200}]}',
        b'{"code":"0","msg":"success","data":[{"timestamp":-1704931200000}]}',
        b'{"code":"0","msg":"success","data":[{"timestamp":1704931200000.0}]}',
        b'{"code":"0","msg":"success","data":[{"timestamp":1704931200000,"timestamp":1704931200000}]}',
        b'{"code":"0","msg":"success","data":[[]]}',
        b'{"code":"0","msg":"success","data":{}}',
        b'{"code":"0","msg":"success","data":null}',
        b'{"code":"0","msg":"success"}',
        b'{"code":"0","msg":"success","data":[],"extra":1}',
        b'{"code":"0","msg":"success","data":[],"data":[]}',
        b'{"code":0,"msg":"success","data":[]}',
        b'{"code":"0","msg":null,"data":[]}',
        b'{"code":"40001","msg":"API key invalid","data":null}',
    ],
)
def test_ruling_10_the_projection_checks_the_grammar_of_every_byte(body: bytes) -> None:
    refused("RESPONSE_SHAPE_REFUSED", projection.project_records, fetched(body), date_keys=("timestamp",),
            first_day=date(2024, 1, 11), last_day=date(2024, 1, 12), what="flows")


# review B7: a lone continuation, a byte no sequence starts with, overlong forms, surrogates,
# code points above U+10FFFF and truncated sequences
MALFORMED_UTF8 = [
    b"\xff", b"\xfe", b"\x80", b"\xbf", b"\xc0\xaf", b"\xc1\xbf", b"\xc2", b"\xc2\x41", b"\xe2\x82",
    b"\xe2\x82\x41", b"\xe0\x80\x80", b"\xe0\x9f\xbf", b"\xed\xa0\x80", b"\xed\xbf\xbf", b"\xf0\x80\x80\x80",
    b"\xf0\x8f\xbf\xbf", b"\xf4\x90\x80\x80", b"\xf5\x80\x80\x80", b"\xf8\x88\x80\x80\x80",
]


@pytest.mark.parametrize("sequence", MALFORMED_UTF8)
@pytest.mark.parametrize("where", ["dropped", "kept-msg"])
def test_review_b7_every_string_byte_must_be_well_formed_utf8(sequence: bytes, where: str) -> None:
    if where == "dropped":
        body = b'{"code":"0","msg":"success","data":[{"timestamp":%d,"name":"a%sb"}]}' % (HOLDOUT_STAMP, sequence)
    else:
        body = b'{"code":"0","msg":"a%sb","data":[%s]}' % (sequence, VALID_RECORD.encode())
    error = refused("RESPONSE_SHAPE_REFUSED", projection.project_records, fetched(body), date_keys=("timestamp",),
                    first_day=date(2024, 1, 11), last_day=date(2024, 1, 11), what="flows")
    assert "UTF-8" in str(error)


def test_review_b7_well_formed_utf8_passes_and_is_kept_byte_for_byte() -> None:
    text = "\u0080\u00e9\u07ff\u0800\u20ac\ud7ff\ue000\uffff\U0001d11e\U0010ffff".encode()
    assert len(text) == 2 + 2 + 2 + 3 + 3 + 3 + 3 + 3 + 4 + 4  # every sequence length, each boundary
    body = b'{"code":"0","msg":"s%s","data":[{"timestamp":%d,"name":"%s"},%s]}' % (text, HOLDOUT_STAMP, text, VALID_RECORD.encode())
    projected = projection.project_records(
        fetched(body), date_keys=("timestamp",), first_day=date(2024, 1, 11), last_day=date(2024, 1, 11), what="flows"
    )
    assert projected.body == b'{"code":"0","msg":"s' + text + b'","data":[' + VALID_RECORD.encode() + b"]}"
    assert (projected.kept, projected.dropped_holdout) == (1, 1)


def test_ruling_10_member_order_whitespace_and_escaped_text_do_not_change_the_projection() -> None:
    kept = '{ "etf_flows" : [ { "etf_ticker" : "IBIT", "flow_usd" : 5 } ],\n "price_usd":1, "flow_usd":-2.5e1,\t"timestamp" : 1704931200000 }'
    dropped = '{"name":"q\\"]},{\\u005d [","nested":{"a":[true,false,null,{"b":"}"}]},"timestamp":%d}' % HOLDOUT_STAMP
    body = ('\n{ "data" : [ %s , %s ] , "msg" : "success" , "code" : "0" }\n' % (dropped, kept)).encode()
    projected = projection.project_records(
        fetched(body), date_keys=("timestamp",), first_day=date(2024, 1, 11), last_day=date(2024, 1, 11), what="flows"
    )
    assert projected.body == b'{"code":"0","msg":"success","data":[' + kept.encode() + b"]}"
    assert (projected.kept, projected.dropped_holdout) == (1, 1)
    assert coinglass.parse_flow_history(projected) == {("IBIT", date(2024, 1, 11)): Decimal(5)}


def test_ruling_10_the_projection_asks_only_for_days_inside_the_window() -> None:
    body = fetched(fx.coinglass_flow_page({}))
    for first, last in ((date(2025, 12, 31), date(2026, 1, 1)), (date(2019, 12, 31), date(2020, 1, 1)), (date(2024, 2, 1), date(2024, 1, 31))):
        refused("REQUEST_OUTSIDE_DATA_WINDOW", projection.project_records, body, date_keys=("timestamp",), first_day=first, last_day=last, what="flows")
    refused("PROVIDER_REQUEST_MISMATCH", projection.project_records, body, date_keys=(), first_day=date(2024, 1, 11), last_day=date(2024, 1, 11), what="flows")
    refused("PROVIDER_RESPONSE_REFUSED", projection.project_records, fx.coinglass_flow_page({}), date_keys=("timestamp",),
            first_day=date(2024, 1, 11), last_day=date(2024, 1, 11), what="flows")
    edge = projection.project_records(
        fetched(fx.coinglass_flow_page({date(2025, 12, 31): {"IBIT": 1}, date(2026, 1, 1): {"IBIT": 2}})),
        date_keys=("timestamp",), first_day=date(2024, 1, 11), last_day=date(2025, 12, 31), what="flows",
    )
    assert (edge.kept, edge.dropped_holdout) == (1, 1)


def test_ruling_10_a_provider_error_names_its_status_but_never_a_record() -> None:
    error = refused("RESPONSE_SHAPE_REFUSED", projection.project_records, fetched(b'{"code":"40001","msg":"API key invalid","data":null}'),
                    date_keys=("timestamp",), first_day=date(2024, 1, 11), last_day=date(2024, 1, 11), what="flows")
    assert "40001" in str(error) and "API key invalid" in str(error)
    body = b'{"code":"0","msg":"success","data":[{"timestamp":%d,"flow_usd":777000009,}]}' % HOLDOUT_STAMP
    error = refused("RESPONSE_SHAPE_REFUSED", projection.project_records, fetched(body),
                    date_keys=("timestamp",), first_day=date(2024, 1, 11), last_day=date(2024, 1, 11), what="flows")
    assert "777000009" not in str(error)


# --- persistence through the existing collectors ---------------------------------------------


class RecordingConnection:
    def __init__(self) -> None:
        self.statements: list[Any] = []

    def execute(self, statement: Any) -> None:
        self.statements.append(statement)


def test_basis_rows_persist_through_the_btc021_collector_under_their_own_names() -> None:
    collection = binance.read_basis(make_fetcher(basis_world()))
    provider = persistence.RecordedDerivativesProvider("binance", "BTCUSD", binance.BINANCE_PROVIDER, basis=collection.rows)
    connection = RecordingConnection()
    request = provider.collection_request(utc(2020, 8, 1), utc(2020, 10, 1))
    result = collect_btc_derivatives(provider, connection, request, ingested_at=RETRIEVED_AT)
    assert result.futures_basis == tuple(collection.rows) and len(connection.statements) == 1
    assert result.funding_rates == result.liquidations == ()
    other = persistence.RecordedDerivativesProvider("binance", "BTCUSD", binance.BINANCE_PROVIDER, basis=collection.rows)
    renamed = type(request)(exchange="binance", symbol="BTCUSDT", provider=binance.BINANCE_PROVIDER, start=request.start, end=request.end)
    with pytest.raises(Exception) as caught:
        collect_btc_derivatives(other, RecordingConnection(), renamed, ingested_at=RETRIEVED_AT)
    assert isinstance(caught.value.__cause__, BackfillRefused) and caught.value.__cause__.reason_code == "PROVIDER_REQUEST_MISMATCH"


def test_a_wrapper_refuses_rows_of_another_identity() -> None:
    transport, _ = liquidation_day()
    rows = kraken.read_liquidations(make_fetcher(transport), DAY, DAY, incidents=()).rows
    refused("PROVIDER_REQUEST_MISMATCH", persistence.RecordedDerivativesProvider, "binance", "PI_XBTUSD", kraken.KRAKEN_PROVIDER, liquidation_rows=rows)
    provider = persistence.RecordedDerivativesProvider("kraken_futures", "PI_XBTUSD", kraken.KRAKEN_PROVIDER, liquidation_rows=rows)
    served = provider.fetch_liquidations(exchange="kraken_futures", symbol="PI_XBTUSD", start=utc(2021, 6, 1, 1), end=utc(2021, 6, 1, 3))
    assert len(served) == 2  # [start, end)


def test_etf_rows_persist_through_the_btc022_collector() -> None:
    first = date(2024, 1, 11)
    read = coinglass_read(coinglass_world({first: {"IBIT": 5}}, {"IBIT": {first: 9}}, first, first), ("IBIT",), first, first)
    provider = persistence.RecordedEtfFlowProvider(coinglass.COINGLASS_PROVIDER, read.flows)
    request = provider.collection_request(("IBIT",), first, first, source=coinglass.FLOW_HISTORY_URL, market_holidays=frozenset())
    connection = RecordingConnection()
    result = collect_etf_flows(provider, connection, request, ingested_at=RETRIEVED_AT)
    assert [(flow.fund, flow.flow_usd, flow.aum_usd, flow.revision) for flow in result.flows] == [("IBIT", Decimal(5), Decimal(9), "FINAL_AS_RETRIEVED")]
    assert len(connection.statements) == 1
    refused("PROVIDER_REQUEST_MISMATCH", persistence.RecordedEtfFlowProvider, "other", read.flows)


def test_persistence_refuses_a_request_that_renames_the_rows_before_the_collector_runs() -> None:
    collection = binance.read_basis(make_fetcher(basis_world()))
    provider = persistence.RecordedDerivativesProvider("binance", "BTCUSD", binance.BINANCE_PROVIDER, basis=collection.rows)
    request = provider.collection_request(utc(2020, 8, 1), utc(2020, 10, 1))
    connection = RecordingConnection()
    result = persistence.persist_derivatives(provider, connection, request, ingested_at=RETRIEVED_AT)
    assert result.futures_basis == tuple(collection.rows) and len(connection.statements) == 1
    for changes in ({"provider": "renamed"}, {"exchange": "other"}, {"symbol": "BTCUSDT"}):
        renamed = dataclasses.replace(request, **changes)
        untouched = RecordingConnection()
        refused("PROVIDER_REQUEST_MISMATCH", persistence.persist_derivatives, provider, untouched, renamed)
        assert untouched.statements == []
    for start, end in ((utc(2019, 12, 1), utc(2020, 10, 1)), (utc(2020, 8, 1), utc(2026, 2, 1))):
        refused("REQUEST_OUTSIDE_DATA_WINDOW", persistence.persist_derivatives, provider, RecordingConnection(), dataclasses.replace(request, start=start, end=end))


def test_etf_persistence_refuses_a_renamed_provider_or_days_outside_the_window() -> None:
    first = date(2024, 1, 11)
    read = coinglass_read(coinglass_world({first: {"IBIT": 5}}, {"IBIT": {first: 9}}, first, first), ("IBIT",), first, first)
    provider = persistence.RecordedEtfFlowProvider(coinglass.COINGLASS_PROVIDER, read.flows)
    request = provider.collection_request(("IBIT",), first, first, source=coinglass.FLOW_HISTORY_URL, market_holidays=frozenset())
    connection = RecordingConnection()
    result = persistence.persist_etf_flows(provider, connection, request, ingested_at=RETRIEVED_AT)
    assert [(flow.fund, flow.provider) for flow in result.flows] == [("IBIT", "coinglass")] and len(connection.statements) == 1
    untouched = RecordingConnection()
    refused("PROVIDER_REQUEST_MISMATCH", persistence.persist_etf_flows, provider, untouched, dataclasses.replace(request, provider="renamed"))
    assert untouched.statements == []
    refused(
        "REQUEST_OUTSIDE_DATA_WINDOW",
        persistence.persist_etf_flows,
        provider,
        RecordingConnection(),
        dataclasses.replace(request, end=date(2026, 1, 2)),
    )


class AdvancingClock:
    """One second later on every read, so each response has its own retrieval instant."""

    def __init__(self) -> None:
        self.ticks = 0

    def __call__(self) -> datetime:
        self.ticks += 1
        return RETRIEVED_AT + timedelta(seconds=self.ticks)


def test_a_basis_row_is_stamped_from_its_own_two_archives_and_persisted_under_ruling_7() -> None:
    fetcher = sources.Fetcher(basis_world(), RetrievalLog(), AdvancingClock())
    collection = binance.read_basis(fetcher)
    retrieved = {item.url: item.retrieved_at for item in fetcher.log.retrievals if item.status == 200}
    for row in collection.rows:
        month = (row.observation_time - HOUR).date().replace(day=1)
        expected = max(
            retrieved[binance.coinm_klines_archive_url("BTCUSD_200925", month)],
            retrieved[binance.coinm_index_archive_url(month)],
        )
        assert row.available_at == row.ingested_at == expected, row.observation_time
    assert len({row.available_at for row in collection.rows}) == 2  # August and September, not the latest of all
    # ruling 7: the collector stamps the persistence instant; every row keeps its own retrieval instant
    provider = persistence.RecordedDerivativesProvider("binance", "BTCUSD", binance.BINANCE_PROVIDER, basis=collection.rows)
    persisted_at = RETRIEVED_AT + timedelta(hours=1)
    result = persistence.persist_derivatives(
        provider, RecordingConnection(), provider.collection_request(utc(2020, 8, 1), utc(2020, 10, 1)), ingested_at=persisted_at
    )
    assert [row.available_at for row in result.futures_basis] == [row.available_at for row in collection.rows]
    assert {row.ingested_at for row in result.futures_basis} == {persisted_at}


def test_an_etf_row_keeps_its_retrieval_instant_and_takes_the_persistence_instant() -> None:
    first = date(2024, 1, 11)
    transport = coinglass_world({first: {"IBIT": 5}}, {"IBIT": {first: 9}}, first, first)
    fetcher = coinglass.coinglass_fetcher(transport, RetrievalLog(), api_key="key-123", clock=AdvancingClock())
    read = coinglass.read_etf_flows(fetcher, ("IBIT",), first, first)
    assert read.flows[0].available_at == RETRIEVED_AT + timedelta(seconds=2)  # the later of its two responses
    provider = persistence.RecordedEtfFlowProvider(coinglass.COINGLASS_PROVIDER, read.flows)
    request = provider.collection_request(("IBIT",), first, first, source=coinglass.FLOW_HISTORY_URL, market_holidays=frozenset())
    persisted_at = RETRIEVED_AT + timedelta(hours=1)
    result = persistence.persist_etf_flows(provider, RecordingConnection(), request, ingested_at=persisted_at)
    assert (result.flows[0].available_at, result.flows[0].ingested_at) == (RETRIEVED_AT + timedelta(seconds=2), persisted_at)


FULL_WIDTH = "12345678901234567890.123456789012345678"  # a valid NUMERIC(38,18) quantity


def test_liquidation_quantities_and_notional_are_exact_under_a_narrow_caller_context() -> None:
    executions = [
        fx.execution("l1", utc(2021, 6, 1, 1, 10), FULL_WIDTH, order_type="Liquidation", direction="Sell"),
        fx.execution("l2", utc(2021, 6, 1, 1, 20), "0.000000000000000001", order_type="Liquidation", direction="Sell"),
    ]
    executions += [fx.execution(f"x{hour}", utc(2021, 6, 1, hour, 30)) for hour in range(24)]
    executions.sort(key=lambda element: element["timestamp"])
    exact_total = Decimal("12345678901234567890.123456789012345679")
    series = {hour: 0 for hour in fx.hourly(utc(2021, 6, 1), utc(2021, 6, 2))}
    series[utc(2021, 6, 1, 1)] = str(exact_total)
    transport = day_world([fx.execution_page(executions)], series)
    with localcontext() as narrow:
        narrow.prec = 6
        collection = kraken.read_liquidations(make_fetcher(transport), DAY, DAY, incidents=())
    (row,) = collection.rows
    assert (row.side, row.quantity, row.notional_usd) == ("long", exact_total, exact_total)
    assert {hour.hour_start.hour: hour.corroboration for hour in collection.hours}[1] == v2.CORROBORATION_AGREES
    snapshot = v2.build_extended_replay_snapshot(
        shared_snapshot=rbt001a.shared_snapshot(), liquidations=collection.rows, liquidation_hours=collection.hours
    )
    assert [item.notional_usd for item in snapshot.liquidations] == [exact_total]


def test_a_liquidation_sum_that_cannot_be_exact_is_refused() -> None:
    huge = "9" * 81
    executions = [fx.execution(f"l{k}", utc(2021, 6, 1, 1, k), huge if k else "0." + "0" * 80 + "1", order_type="Liquidation", direction="Sell") for k in range(2)]
    refused("RESPONSE_SHAPE_REFUSED", kraken.read_liquidations, make_fetcher(day_world([fx.execution_page(executions)])), DAY, DAY, incidents=())


def same_side(quantities: list[str], *, direction: str = "Sell") -> list[dict[str, Any]]:
    return [
        fx.execution(f"l{k}", utc(2021, 6, 1, 1, k + 1), quantity, order_type="Liquidation", direction=direction)
        for k, quantity in enumerate(quantities)
    ]


def precision_day(liquidations: list[dict[str, Any]], published: str | None) -> FakeTransport:
    """A fully observed day whose hour 1 lists ``liquidations`` in the order given (ruling 12 admits any order)."""

    executions = [fx.execution(f"x{hour}", utc(2021, 6, 1, hour, 30)) for hour in range(24)]
    executions[1:1] = liquidations
    series: dict[datetime, Any] = {hour: 0 for hour in fx.hourly(utc(2021, 6, 1), utc(2021, 6, 2))}
    if published is not None:
        series[utc(2021, 6, 1, 1)] = published
    return day_world([fx.execution_page(executions)], series)


def listing_orders(count: int) -> list[tuple[int, ...]]:
    return list(itertools.permutations(range(count))) if count <= 4 else [tuple(range(count)), tuple(reversed(range(count)))]


NINES_80 = "0." + "9" * 80


@pytest.mark.parametrize(
    ("quantities", "total"),
    [
        (["1", "1E-80", NINES_80], "2"),
        (["1E-80", "1", "1." + "9" * 80], "3"),
        (["9"] * 12, "108"),
        (["1." + "0" * 20_000, "2"], "3"),
    ],
    ids=["a-carry-cancels-the-last-digit", "a-value-wider-than-80-digits", "carries-into-new-leading-digits", "trailing-zeros"],
)
def test_r12_1_an_hours_quantities_sum_exactly_in_every_listing_order(quantities: list[str], total: str) -> None:
    # re-review R12-1: one value at a time in 80 digits accepted [1E-80, 1-1E-80, 1] and refused [1, 1E-80, 1-1E-80]
    liquidations = same_side(quantities)
    outcomes = []
    for order in listing_orders(len(liquidations)):
        transport = precision_day([liquidations[k] for k in order], total)
        collection = kraken.read_liquidations(make_fetcher(transport), DAY, DAY, incidents=())
        (row,) = collection.rows
        assert (row.side, row.quantity, row.notional_usd) == ("long", Decimal(total), Decimal(total))
        assert (collection.hours[1].feed_status, collection.hours[1].corroboration) == (WITH, v2.CORROBORATION_AGREES)
        classified = [(hour.hour_start, hour.feed_status, hour.corroboration) for hour in collection.hours]
        outcomes.append((collection.rows, classified, without_page_digests(collection)))
    assert all(outcome == outcomes[0] for outcome in outcomes)


@pytest.mark.parametrize(
    "quantities",
    [["1", "1E-80"], ["0." + "0" * 80 + "1", "9" * 81], ["1E-80", "1", "1." + "9" * 79], [f"9E+{MAX_EMAX}"] * 2],
    ids=["81-digits", "162-digits", "81-digits-of-three", "past-the-largest-exponent"],
)
def test_r12_1_a_sum_wider_than_80_digits_refuses_in_every_listing_order(quantities: list[str]) -> None:
    liquidations = same_side(quantities)
    for order in listing_orders(len(liquidations)):
        transport = precision_day([liquidations[k] for k in order], None)
        refusal = refused("RESPONSE_SHAPE_REFUSED", kraken.read_liquidations, make_fetcher(transport), DAY, DAY, incidents=())
        assert "do not sum exactly" in str(refusal)


def test_r12_1_each_side_is_held_to_80_digits_even_when_the_hours_total_fits() -> None:
    # the long side sums to 1 + 1E-80 (81 digits); with the short side's 1 - 1E-80 the hour's total would be 2
    liquidations = same_side(["1", "1E-80"]) + [
        fx.execution("s0", utc(2021, 6, 1, 1, 30), NINES_80, order_type="Liquidation", direction="Buy")
    ]
    for order in listing_orders(3):
        transport = precision_day([liquidations[k] for k in order], "2")
        refusal = refused("RESPONSE_SHAPE_REFUSED", kraken.read_liquidations, make_fetcher(transport), DAY, DAY, incidents=())
        assert "do not sum exactly" in str(refusal)


@pytest.mark.parametrize("places", [kraken.EXACT_SUM_MAX_DIGITS - 1, kraken.EXACT_SUM_MAX_DIGITS], ids=["at-the-cap", "past-the-cap"])
def test_r12_1_the_exact_sum_is_bounded_by_the_quantities_span_in_every_listing_order(places: int) -> None:
    # 0.9...9 (places nines) and 1E-places sum to 1 over places + 1 digits: the cap admits a span of exactly its size
    liquidations = same_side(["0." + "9" * places, f"1E-{places}"])
    for order in listing_orders(2):
        transport = precision_day([liquidations[k] for k in order], "1")
        if places + 1 <= kraken.EXACT_SUM_MAX_DIGITS:
            collection = kraken.read_liquidations(make_fetcher(transport), DAY, DAY, incidents=())
            assert [(row.side, row.quantity) for row in collection.rows] == [("long", Decimal(1))]
        else:
            refusal = refused("RESPONSE_SHAPE_REFUSED", kraken.read_liquidations, make_fetcher(transport), DAY, DAY, incidents=())
            assert f"need more than {kraken.EXACT_SUM_MAX_DIGITS} digits" in str(refusal)


@pytest.mark.parametrize(
    "values",
    [
        ["1", "1E-80", NINES_80],
        ["1E+30", "1E-30", "123.456", "0.5"],
        ["9"] * 4,
        ["1." + "0" * 300, "7E-200"],
        ["1E-1000050", "2E-1000050"],
        ["1E+1000050", "1E+1000050", "3E+1000049"],
    ],
    ids=["carry-cancels", "mixed-places", "carries", "trailing-zeros", "below-the-80-digit-exponent-range", "above-it"],
)
def test_r12_1_exact_sum_is_the_exact_total_in_every_order_under_any_caller_context(values: list[str]) -> None:
    numbers = [Decimal(value) for value in values]
    expected = sum((Fraction(number) for number in numbers), Fraction(0))
    for order in itertools.permutations(numbers):
        with localcontext() as caller:
            caller.prec, caller.traps[Inexact] = 3, True
            total = kraken.exact_sum(list(order))
        assert total is not None and Fraction(total) == expected
    assert kraken.exact_sum([]) == 0
    assert kraken.exact_sum([Decimal("1E+5000"), Decimal("1E-5001")]) is None  # a span of 10,002 digits


def test_r12_1_an_unknown_side_refuses_before_any_sum_and_names_the_same_liquidation_in_every_order() -> None:
    liquidations = same_side(["1", "1E-80"])  # their sum alone would not be exact
    liquidations += [
        fx.execution(uid, utc(2021, 6, 1, 1, 20 + k), order_type="Liquidation", direction="sell") for k, uid in enumerate(["u2", "u1"])
    ]
    for order in listing_orders(4):
        transport = precision_day([liquidations[k] for k in order], None)
        refusal = refused("LIQUIDATION_SIDE_UNKNOWN", kraken.read_liquidations, make_fetcher(transport), DAY, DAY, incidents=())
        assert "liquidation u1 has" in str(refusal)


# --- re-review R12-2 to R12-4: a numeric input refuses its day, never raises ----------------------


def ruling_3(total: Decimal, published: Decimal) -> bool:
    """Owner ruling 3 in exact fractions: the total rounded half-even to the published places is the published value."""

    unit = Fraction(10) ** published.as_tuple().exponent
    return round(Fraction(total) / unit) * unit == Fraction(published)


def corroborates_before_r12_2(total: Decimal, published: Decimal) -> bool:
    """The comparison before R12-2, in its fixed 80-digit context; it raises where that runs out of digits."""

    exponent = published.as_tuple().exponent
    with localcontext(Context(prec=80, rounding=ROUND_HALF_EVEN, traps=[InvalidOperation, DivisionByZero, Overflow])):
        return total.quantize(Decimal((0, (1,), exponent)), rounding=ROUND_HALF_EVEN) == published


R12_2_TOTALS = ["0", "1", "5", "15", "25", "0.5", "2.5", "99.95", "12345.6789", "1E-80", NINES_80, "9" * 80, "1E+30"]
R12_2_EXPONENTS = [-200, -100, -81, -80, -79, -18, -4, -2, -1, 0, 1, 2, 3, 31, 81, 200]


def test_r12_2_corroboration_is_ruling_3_at_any_published_precision_under_any_caller_context() -> None:
    compared = 0
    for text in R12_2_TOTALS:
        total = Decimal(text)
        for exponent in R12_2_EXPONENTS:
            rounded = round(Fraction(total) / Fraction(10) ** exponent)
            for coefficient in {rounded, rounded + 1, max(rounded - 1, 0)}:
                published = Decimal((0, tuple(int(digit) for digit in str(coefficient)), exponent))
                with localcontext() as caller:
                    caller.prec, caller.Emax, caller.Emin, caller.traps[Inexact] = 3, 10, -10, True
                    agrees = kraken.corroborates(total, published)
                assert agrees is (coefficient == rounded) is ruling_3(total, published), (text, exponent, coefficient)
                try:
                    before = corroborates_before_r12_2(total, published)
                except InvalidOperation:
                    continue
                assert before is agrees  # wherever the earlier comparison answered, the answer is the same
                compared += 1
    assert compared >= 380  # the cases the earlier comparison answered


@pytest.mark.parametrize(
    ("total", "published", "agrees"),
    [
        ("1", "1." + "0" * 20_000, True),
        ("1", "1." + "0" * 19_999 + "1", False),
        ("5", f"0E+{MAX_EMAX}", True),  # 5 rounded to the largest place decimal holds is 0
        ("5", f"1E+{MAX_EMAX}", False),
        ("0", f"0E+{MAX_EMAX}", True),
        ("1", "1E-1000000000000000000", False),  # an exponent below the smallest a context may set
        ("0", "0E-1000000000000000000", True),
        ("9" * 80, "1E+80", True),
        ("9" * 80, "1E+81", False),
    ],
    ids=["20000-places", "20000-places-differs", "largest-place-zero", "largest-place-one", "zero-at-the-largest-place",
         "below-the-smallest-exponent", "zero-below-it", "carry-into-a-new-digit", "past-the-carry"],
)
def test_r12_2_corroboration_answers_at_the_exponent_extremes(total: str, published: str, agrees: bool) -> None:
    with localcontext() as caller:
        caller.prec, caller.traps[Inexact] = 3, True
        assert kraken.corroborates(Decimal(total), Decimal(published)) is agrees


@pytest.mark.parametrize("places", [79, 80, 200, 20_000])
def test_r12_2_a_published_value_with_any_number_of_places_corroborates_and_reads_back(places: int) -> None:
    # re-review R12-2: a total of 1 against 1 with 80 zero places raised InvalidOperation instead of agreeing
    for published, corroboration in [("1." + "0" * places, v2.CORROBORATION_AGREES), ("1." + "0" * (places - 1) + "1", v2.CORROBORATION_DISAGREES)]:
        with localcontext() as caller:
            caller.prec, caller.traps[Inexact] = 3, True
            collection = kraken.read_liquidations(make_fetcher(precision_day(same_side(["1"]), published)), DAY, DAY, incidents=())
        assert [(row.side, row.quantity) for row in collection.rows] == [("long", Decimal(1))]
        assert (collection.hours[1].feed_status, collection.hours[1].corroboration) == (WITH, corroboration)
        stored = json.loads(collection.evidence_bytes)["hours"][1]
        assert (stored["series_value"], stored["corroboration"]) == (published, corroboration)
        typed = kraken.parse_liquidation_hour_evidence(collection.evidence_bytes, expected_sha256=collection.evidence_sha256)
        assert typed == collection.hours


@pytest.mark.parametrize(
    ("quantities", "total"),
    [
        (["99999999999999999999.999999999999999999"], "99999999999999999999.999999999999999999"),  # the column's largest
        (["0.000000000000000001"], "0.000000000000000001"),
        (["0.0000000000000000005", "0.0000000000000000005"], "0.000000000000000001"),  # each past 18 places, not their sum
        (["1E+20"], None),
        (["99999999999999999999.999999999999999999", "0.000000000000000001"], None),  # the sum reaches 10^20
        (["0.0000000000000000001"], None),
        (["1E+4300"], None),  # the review's case: 4,301 digits that would not read back
        (["1E+999999"], None),
    ],
    ids=["largest", "smallest", "places-cancel-in-the-sum", "10^20", "sum-reaches-10^20", "19-places", "1E+4300", "1E+999999"],
)
def test_r12_3_a_side_the_liquidation_table_cannot_hold_refuses_its_day(quantities: list[str], total: str | None) -> None:
    for direction, side in [("Sell", "long"), ("Buy", "short")]:
        transport = precision_day(same_side(quantities, direction=direction), total or "1")
        if total is not None:
            collection = kraken.read_liquidations(make_fetcher(transport), DAY, DAY, incidents=())
            assert [(row.side, row.quantity, row.notional_usd) for row in collection.rows] == [(side, Decimal(total), Decimal(total))]
            assert collection.hours[1].corroboration == v2.CORROBORATION_AGREES
            assert kraken.parse_liquidation_hour_evidence(collection.evidence_bytes, expected_sha256=collection.evidence_sha256) == collection.hours
        else:
            refusal = refused("RESPONSE_SHAPE_REFUSED", kraken.read_liquidations, make_fetcher(transport), DAY, DAY, incidents=())
            assert f"the {side} liquidation quantity or its notional does not fit the liquidation table's NUMERIC(38,18)" in str(refusal)


def test_r12_3_each_sides_notional_is_held_to_the_column_too(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(kraken, "CONTRACT_SIZE_USD", Decimal(1000))
    hour = utc(2021, 6, 1, 1)

    def record(quantity: str) -> dict[str, Any]:
        liquidation = kraken.Execution("l0", hour, Decimal(quantity), "Liquidation", "Sell")
        return kraken.hour_record(hour, [liquidation], incident=False, series_value=None, pages_sha256=["0" * 64], series_sha256=None)

    assert record("99999999999999999")["long_quantity"] == "99999999999999999"  # its notional 99999999999999999000 fits
    refusal = refused("RESPONSE_SHAPE_REFUSED", record, "100000000000000000")  # the quantity fits, its notional 10^20 does not
    assert "the long liquidation quantity or its notional does not fit" in str(refusal)


@pytest.mark.parametrize(
    "stored",
    ["1" + "0" * 4300, "1" + "0" * 100_000, "100000000000000000000", "0." + "0" * 18 + "1", "0." + "0" * 5000 + "1"],
    ids=["4301-digits", "100001-digits", "10^20", "19-places", "5001-places"],
)
def test_r12_3_a_stored_quantity_the_column_cannot_hold_refuses_before_its_spelling_is_read(stored: str) -> None:
    # re-review R12-3: a 4,301-digit stored quantity raised ValueError inside the replay owner's canonical spelling
    def change(payload: dict[str, Any]) -> None:
        payload["hours"][1]["long_quantity"] = stored

    data, digest = evidence_variant(change)
    with localcontext() as caller:
        caller.prec, caller.traps[Inexact] = 3, True
        refusal = refused("RESPONSE_SHAPE_REFUSED", kraken.parse_liquidation_hour_evidence, data, expected_sha256=digest)
    assert "long_quantity does not fit the liquidation table's NUMERIC(38,18)" in str(refusal)


def test_r12_3_the_column_rule_is_the_v2_builders() -> None:
    assert kraken.RAW_NUMERIC_LIMIT == v2._RAW_NUMERIC_LIMIT
    assert Decimal((0, (1,), -kraken.RAW_NUMERIC_PLACES)) == v2.RAW_NUMERIC_QUANTUM
    values = [
        "0", "1", "1E-18", "1E-19", "1.5E-18", "0.0000000000000000015", "5E+19", "99999999999999999999.999999999999999999",
        "1E+20", "100000000000000000000.000000000000000001", "123456789012345678901", "1E+4300", "1E-1000050", "1." + "0" * 300,
    ]
    for text in values:
        value = Decimal(text)
        try:
            v2._require_raw_numeric(SimpleNamespace(quantity=value), ("quantity",), "a probe")
            v2_holds = True
        except v2.ExtendedReplayInputRefused:
            v2_holds = False
        assert kraken.fits_raw_numeric(value) is v2_holds, text


@pytest.mark.parametrize("published", ["1e+1000000000000000000", "1E+99999999999999999999", "0e+1000000000000000000"])
@pytest.mark.parametrize("trap", [True, False], ids=["caller-traps", "caller-does-not-trap"])
def test_r12_4_a_published_exponent_no_decimal_can_hold_refuses_its_day_under_any_caller_context(published: str, trap: bool) -> None:
    transport = precision_day(same_side(["1"]), published)
    with localcontext() as caller:
        caller.traps[InvalidOperation] = trap
        refusal = refused("RESPONSE_SHAPE_REFUSED", kraken.read_liquidations, make_fetcher(transport), DAY, DAY, incidents=())
    assert f"series value {published!r} at 2021-06-01T01:00:00+00:00 has an exponent no decimal can hold" in str(refusal)


@pytest.mark.parametrize(
    ("published", "corroboration"),
    [(f"1E+{MAX_EMAX}", v2.CORROBORATION_DISAGREES), (f"0E+{MAX_EMAX}", v2.CORROBORATION_AGREES)],
    ids=["one-at-the-largest-exponent", "zero-at-it"],
)
def test_r12_4_the_largest_published_exponent_reads_compares_and_reads_back(published: str, corroboration: str) -> None:
    collection = kraken.read_liquidations(make_fetcher(precision_day(same_side(["1"]), published)), DAY, DAY, incidents=())
    assert collection.hours[1].corroboration == corroboration
    assert json.loads(collection.evidence_bytes)["hours"][1]["series_value"] == published
    assert kraken.parse_liquidation_hour_evidence(collection.evidence_bytes, expected_sha256=collection.evidence_sha256) == collection.hours


HUGE_JSON_NUMBER = b"1e+1000000000000000000"  # valid JSON; its exponent is past what decimal holds


def read_with_a_huge_json_number(where: str) -> Any:
    """Read a complete day, or its evidence, with one JSON number whose exponent no decimal can hold."""

    executions = [fx.execution(f"x{hour}", utc(2021, 6, 1, hour, 30)) for hour in range(24)]
    executions[1:1] = same_side(["7"])
    page = fx.execution_page(executions)
    series: dict[datetime, Any] = {hour: "0" for hour in fx.hourly(utc(2021, 6, 1), utc(2021, 6, 2))}
    series[utc(2021, 6, 1, 1)] = "7"
    if where == "execution-page":
        assert page.count(b'"quantity":"7"') == 1
        page = page.replace(b'"quantity":"7"', b'"quantity":' + HUGE_JSON_NUMBER)
    transport = day_world([page], series)
    if where == "series":
        series[utc(2021, 6, 1, 1)] = HUGE_JSON_NUMBER.decode()
        transport.add(kraken.liquidation_volume_url(utc(2021, 6, 1), utc(2021, 6, 1, 23)), fx.series_body(series, quoted=False))
    if where != "hour-evidence":
        return lambda: kraken.read_liquidations(make_fetcher(transport), DAY, DAY, incidents=())
    evidence = kraken.read_liquidations(make_fetcher(transport), DAY, DAY, incidents=()).evidence_bytes
    assert evidence.count(b'"incident":false') == 24
    tampered = evidence.replace(b'"incident":false', b'"incident":' + HUGE_JSON_NUMBER, 1)
    return lambda: kraken.parse_liquidation_hour_evidence(tampered, expected_sha256=hashlib.sha256(tampered).hexdigest())


@pytest.mark.parametrize(
    ("where", "what"),
    [("execution-page", "an execution page"), ("series", "the liquidation-volume series"), ("hour-evidence", "the hour evidence")],
)
@pytest.mark.parametrize("trap", [True, False], ids=["caller-traps", "caller-does-not-trap"])
def test_r12_5_a_json_number_no_decimal_can_hold_refuses_under_any_caller_context(where: str, what: str, trap: bool) -> None:
    # implementer-found R12-5: json.loads(parse_float=Decimal) raised InvalidOperation, which is not a ValueError
    read = read_with_a_huge_json_number(where)
    with localcontext() as caller:
        caller.traps[InvalidOperation] = trap
        refusal = refused("RESPONSE_SHAPE_REFUSED", read)
    assert str(refusal).endswith(f"{what} holds a number no decimal can hold")


LARGEST_FITTING = "99999999999999999999.999999999999999999"  # the column's largest value, canonically spelled


def test_r12_6_the_spelling_limit_is_the_longest_canonical_spelling_of_a_value_that_fits() -> None:
    assert len(LARGEST_FITTING) == kraken.RAW_NUMERIC_SPELLING_MAX
    for text in [LARGEST_FITTING, "12345678901234567890.123456789012345678", "99999999999999999999", "0.000000000000000001", "0"]:
        value = Decimal(text)
        assert kraken.fits_raw_numeric(value) and v1.canonical_decimal(value) == text
        assert len(text) <= kraken.RAW_NUMERIC_SPELLING_MAX


@pytest.mark.parametrize(
    "stored",
    [
        "1." + "0" * 4300,  # the review's case: exactly 1, a coefficient of 4,301 digits
        "1." + "0" * 100_000,
        "0.000000000000000001" + "0" * 4300,
        LARGEST_FITTING + "0" * 4300,
        "0" * 5000 + "1." + "0" * 5000,
    ],
    ids=["one-4300-zeros", "one-100000-zeros", "smallest-4300-zeros", "largest-4300-zeros", "leading-and-trailing-zeros"],
)
@pytest.mark.parametrize("side", ["long_quantity", "short_quantity"])
@pytest.mark.parametrize("hostile", [False, True], ids=["default-context", "hostile-context"])
def test_r12_6_a_long_spelling_of_a_stored_quantity_that_fits_refuses_as_not_canonical(stored: str, side: str, hostile: bool) -> None:
    # re-review R12-6: the value fits, so the column check passed, and canonical_decimal's int raised ValueError
    assert kraken.fits_raw_numeric(Decimal(stored))

    def change(payload: dict[str, Any]) -> None:
        payload["hours"][1][side] = stored

    data, digest = evidence_variant(change)
    with localcontext() as caller:
        if hostile:
            caller.prec, caller.traps[Inexact], caller.traps[InvalidOperation] = 3, True, False
        refusal = refused("RESPONSE_SHAPE_REFUSED", kraken.parse_liquidation_hour_evidence, data, expected_sha256=digest)
    assert f"{side} {stored!r} is not a canonical non-negative decimal" in str(refusal)


@pytest.mark.parametrize("spelling", ["1." + "0" * 4300, "1." + "0" * 100_000], ids=["4300-zeros", "100000-zeros"])
def test_r12_6_a_long_spelled_execution_quantity_is_stored_canonically_and_reads_back(spelling: str) -> None:
    collection = kraken.read_liquidations(make_fetcher(precision_day(same_side([spelling]), "1")), DAY, DAY, incidents=())
    assert json.loads(collection.evidence_bytes)["hours"][1]["long_quantity"] == "1"
    assert [(row.side, row.quantity) for row in collection.rows] == [("long", Decimal(1))]
    assert collection.hours[1].corroboration == v2.CORROBORATION_AGREES
    assert kraken.parse_liquidation_hour_evidence(collection.evidence_bytes, expected_sha256=collection.evidence_sha256) == collection.hours


@pytest.mark.parametrize("number", [b"1.0", b"1e1", b"0.5", b"NaN", b"Infinity", b"-Infinity"])
@pytest.mark.parametrize("field", ["contract_size_usd", "execution_count", "long_quantity", "series_value", "incident"])
def test_r12_7_a_json_number_the_canonical_writer_cannot_write_refuses_the_evidence(field: str, number: bytes) -> None:
    # re-review R12-7: a JSON fraction decoded as a Decimal (TypeError) or a non-finite float (ValueError) in the canonical check
    def change(payload: dict[str, Any]) -> None:
        (payload if field == "contract_size_usd" else payload["hours"][1])[field] = "R12-7 SENTINEL"

    data, _ = evidence_variant(change)
    assert data.count(b'"R12-7 SENTINEL"') == 1
    tampered = data.replace(b'"R12-7 SENTINEL"', number)
    refusal = refused(
        "RESPONSE_SHAPE_REFUSED", kraken.parse_liquidation_hour_evidence, tampered, expected_sha256=hashlib.sha256(tampered).hexdigest()
    )
    assert str(refusal).endswith("the hour evidence is not the canonical file with exactly its keys")


def test_r12_7_the_canonical_check_refuses_when_the_writer_runs_out_of_depth(monkeypatch: pytest.MonkeyPatch) -> None:
    # the decoder and the writer reach the same depth today; a writer that ran out of it first refuses too
    transport, _ = liquidation_day()
    collection = kraken.read_liquidations(make_fetcher(transport), DAY, DAY, incidents=())

    def out_of_depth(value: Any) -> bytes:
        raise RecursionError("maximum recursion depth exceeded while encoding a JSON object")

    monkeypatch.setattr(kraken, "canonical_json_bytes", out_of_depth)
    refusal = refused(
        "RESPONSE_SHAPE_REFUSED", kraken.parse_liquidation_hour_evidence, collection.evidence_bytes, expected_sha256=collection.evidence_sha256
    )
    assert str(refusal).endswith("the hour evidence is not the canonical file with exactly its keys")


def nested(depth: int) -> bytes:
    return b"[" * depth + b"]" * depth


def deepest_decodable_nesting() -> int:
    """The deepest array nesting this interpreter's JSON decoder reads (about 10,000 on CPython 3.12)."""

    low, high = 1, 1_000_000
    while low < high:
        middle = (low + high + 1) // 2
        try:
            json.loads(nested(middle))
            low = middle
        except RecursionError:
            high = middle - 1
    return low


def read_with_a_json_value(where: str, value: bytes) -> Any:
    """Read a complete day, or its evidence, with ``value``'s JSON text in place of one of its values."""

    executions = [fx.execution(f"x{hour}", utc(2021, 6, 1, hour, 30)) for hour in range(24)]
    executions[1:1] = same_side(["7"])
    page = fx.execution_page(executions)
    series: dict[datetime, Any] = {hour: "0" for hour in fx.hourly(utc(2021, 6, 1), utc(2021, 6, 2))}
    series[utc(2021, 6, 1, 1)] = "7"
    if where == "execution-page":
        assert page.count(b'"quantity":"7"') == 1
        page = page.replace(b'"quantity":"7"', b'"quantity":' + value)
    transport = day_world([page], series)
    if where == "series":
        series[utc(2021, 6, 1, 1)] = value.decode()
        transport.add(kraken.liquidation_volume_url(utc(2021, 6, 1), utc(2021, 6, 1, 23)), fx.series_body(series, quoted=False))
    if where != "hour-evidence":
        return lambda: kraken.read_liquidations(make_fetcher(transport), DAY, DAY, incidents=())
    evidence = kraken.read_liquidations(make_fetcher(transport), DAY, DAY, incidents=()).evidence_bytes
    assert evidence.count(b'"incident":false') == 24
    tampered = evidence.replace(b'"incident":false', b'"incident":' + value, 1)
    return lambda: kraken.parse_liquidation_hour_evidence(tampered, expected_sha256=hashlib.sha256(tampered).hexdigest())


@pytest.mark.parametrize(
    ("where", "what"),
    [("execution-page", "an execution page"), ("series", "the liquidation-volume series"), ("hour-evidence", "the hour evidence")],
)
def test_r12_8_a_body_nested_too_deeply_to_decode_refuses_in_every_reader(where: str, what: str) -> None:
    # implementer-found R12-8: the decoder's RecursionError is not a ValueError
    limit = deepest_decodable_nesting()
    for depth in [limit + 1, 100_000, 1_000_000]:
        refusal = refused("RESPONSE_SHAPE_REFUSED", read_with_a_json_value(where, nested(depth)))
        assert str(refusal).endswith(f"{what} is nested too deeply to read"), depth
    for depth in range(limit - 10, limit + 11):  # around the decoder's depth: refused by depth or by shape, never raised
        refused("RESPONSE_SHAPE_REFUSED", read_with_a_json_value(where, nested(depth)))


@pytest.mark.parametrize("quantity", ["1e+1000000000000000000", "seven"], ids=["exponent-no-decimal-holds", "no-numeral"])
@pytest.mark.parametrize("trap", [True, False], ids=["caller-traps", "caller-does-not-trap"])
def test_r12_9_an_execution_quantity_decimal_cannot_read_refuses_the_same_way_under_any_caller_context(quantity: str, trap: bool) -> None:
    # implementer-found R12-9: read in the caller's context, the message turned on its InvalidOperation trap
    transport = precision_day(same_side([quantity]), "1")
    with localcontext() as caller:
        caller.traps[InvalidOperation] = trap
        refusal = refused("RESPONSE_SHAPE_REFUSED", kraken.read_liquidations, make_fetcher(transport), DAY, DAY, incidents=())
    assert str(refusal).endswith(f"execution l0 quantity {quantity!r} is not a decimal")


@pytest.mark.parametrize("published", ["1e+1000000000000000000", "1E+99999999999999999999", "seven"])
@pytest.mark.parametrize("trap", [True, False], ids=["caller-traps", "caller-does-not-trap"])
def test_r12_9_a_stored_published_value_decimal_cannot_read_refuses_the_same_way_under_any_caller_context(published: str, trap: bool) -> None:
    def change(payload: dict[str, Any]) -> None:
        payload["hours"][1]["series_value"] = published

    data, digest = evidence_variant(change)
    with localcontext() as caller:
        caller.traps[InvalidOperation] = trap
        refusal = refused("RESPONSE_SHAPE_REFUSED", kraken.parse_liquidation_hour_evidence, data, expected_sha256=digest)
    assert str(refusal).endswith(f"series_value {published!r} is not a published decimal with its response digest")


@pytest.mark.parametrize(
    ("quantity", "prec", "emin", "trap_inexact"),
    [(FULL_WIDTH, 28, None, True), ("0.000000000000000001", 3, -5, False), ("1234.5", 3, None, True)],
    ids=["full-width-inexact-trapped", "underflow-at-precision-3", "ordinary-inexact-trapped"],
)
def test_the_evidence_read_back_admits_a_valid_hour_under_any_caller_context(
    quantity: str, prec: int, emin: int | None, trap_inexact: bool
) -> None:
    # re-review N1: the parser re-derives each hour without arithmetic in the caller's context
    executions = [fx.execution("l1", utc(2021, 6, 1, 1, 10), quantity, order_type="Liquidation", direction="Sell")]
    executions += [fx.execution(f"x{hour}", utc(2021, 6, 1, hour, 30)) for hour in range(24)]
    executions.sort(key=lambda element: element["timestamp"])
    series = {hour: 0 for hour in fx.hourly(utc(2021, 6, 1), utc(2021, 6, 2))}
    series[utc(2021, 6, 1, 1)] = quantity
    transport = day_world([fx.execution_page(executions)], series)
    with localcontext() as caller:
        caller.prec = prec
        if emin is not None:
            caller.Emin = emin
        caller.traps[Inexact] = trap_inexact
        collection = kraken.read_liquidations(make_fetcher(transport), DAY, DAY, incidents=())
    (row,) = collection.rows
    assert row.quantity == row.notional_usd == Decimal(quantity)
    assert (collection.hours[1].feed_status, collection.hours[1].corroboration) == (WITH, v2.CORROBORATION_AGREES)


def test_a_funding_interval_is_whole_seconds_exactly_at_any_width() -> None:
    transport = FakeTransport()
    funding_month(transport, date(2020, 2, 1), [fx.funding_row(utc(2020, 2, 1), hours="8.00000000000000000000000000001")])
    with localcontext() as context:
        context.prec = 28
        refused("RESPONSE_SHAPE_REFUSED", binance.read_funding, make_fetcher(transport), date(2020, 2, 1), date(2020, 2, 1))
    transport = FakeTransport()
    funding_month(transport, date(2020, 2, 1), [fx.funding_row(utc(2020, 2, 1), hours="1" + "0" * 40)])
    refused("RESPONSE_SHAPE_REFUSED", binance.read_funding, make_fetcher(transport), date(2020, 2, 1), date(2020, 2, 1))
    transport = FakeTransport()
    funding_month(transport, date(2020, 2, 1), [fx.funding_row(utc(2020, 2, 1), hours="8.000000000000000000000000000000")])
    assert binance.read_funding(make_fetcher(transport), date(2020, 2, 1), date(2020, 2, 1)).rows[0].funding_interval_hours == 8


FLOW_DAY = '{"timestamp":1704931200000,"flow_usd":%s,"price_usd":%s,"etf_flows":[{"etf_ticker":"IBIT","flow_usd":%s}]}'
FUND_DAY = (
    '{"assets_date":1704931200000,"btc_holdings":%s,"market_date":1704931200000,"market_price":38.51,'
    '"name":"iShares Bitcoin Trust","nav":38.57,"net_assets":%s,"premium_discount":-0.16,'
    '"shares_outstanding":555700100,"ticker":"IBIT"}'
)


@pytest.mark.parametrize(
    ("flow", "fund"),
    [
        (FLOW_DAY % ('{"unexpected":[]}', "45000", "5"), FUND_DAY % ("1000", "9")),
        (FLOW_DAY % ("0", '{"unexpected":[]}', "5"), FUND_DAY % ("1000", "9")),
        (FLOW_DAY % ("0", "null", "5"), FUND_DAY % ("1000", "9")),
        (FLOW_DAY % ('"0"', "45000", "5"), FUND_DAY % ("1000", "9")),
        (FLOW_DAY % ("0", "45000", '{"unexpected":[]}'), FUND_DAY % ("1000", "9")),
        (FLOW_DAY % ("0", "45000", "5"), FUND_DAY % ('{"unexpected":[]}', "9")),
        (FLOW_DAY % ("0", "45000", "5"), FUND_DAY % ("true", "9")),
        (FLOW_DAY % ("0", "45000", "5"), FUND_DAY % ("1000", "null")),
    ],
    ids=["day-flow-object", "price-object", "price-null", "day-flow-string", "ticker-flow-object", "holdings-object", "holdings-bool", "assets-null"],
)
def test_ruling_5_every_declared_coinglass_field_is_type_checked(flow: str, fund: str) -> None:
    first = date(2024, 1, 11)
    transport = FakeTransport()
    transport.add(coinglass.FLOW_HISTORY_URL, ('{"code":"0","msg":"success","data":[%s]}' % flow).encode())
    transport.add(coinglass.fund_history_url("IBIT"), ('{"code":"0","msg":"success","data":[%s]}' % fund).encode())
    refused("RESPONSE_SHAPE_REFUSED", coinglass_read, transport, ("IBIT",), first, first)


@pytest.mark.parametrize(
    "change",
    [
        {"ticker": "GBTC"},  # another fund's history served for the requested ticker
        {"name": ""},
        {"name": 5},
        {"market_date": 1704931200001},  # not a UTC day stamp
        {"market_date": None},
    ],
    ids=["other-ticker", "empty-name", "number-name", "market-date-not-midnight", "market-date-null"],
)
def test_a_fund_history_day_must_name_its_fund_and_a_day(change: dict[str, Any]) -> None:
    first = date(2024, 1, 11)
    record = json.loads(FUND_DAY % ("1000", "9")) | change
    transport = FakeTransport()
    transport.add(coinglass.FLOW_HISTORY_URL, ('{"code":"0","msg":"success","data":[%s]}' % (FLOW_DAY % ("0", "45000", "5"))).encode())
    transport.add(coinglass.fund_history_url("IBIT"), json.dumps({"code": "0", "msg": "success", "data": [record]}).encode())
    reason = "RESPONSE_SHAPE_REFUSED"
    refused(reason, coinglass_read, transport, ("IBIT",), first, first)


@pytest.mark.parametrize("value", ["1", True, None, [], {}], ids=["string", "bool", "null", "array", "object"])
@pytest.mark.parametrize("field", ["btc_holdings", "market_price", "nav", "premium_discount", "shares_outstanding", "net_assets"])
def test_review_each_fund_number_is_type_checked_on_its_own(field: str, value: Any) -> None:
    # the Part B review's mutants found no test of the nav check alone: each number, each wrong type
    first = date(2024, 1, 11)
    record = json.loads(FUND_DAY % ("1000", "9")) | {field: value}
    transport = FakeTransport()
    transport.add(coinglass.FLOW_HISTORY_URL, ('{"code":"0","msg":"success","data":[%s]}' % (FLOW_DAY % ("0", "45000", "5"))).encode())
    transport.add(coinglass.fund_history_url("IBIT"), json.dumps({"code": "0", "msg": "success", "data": [record]}).encode())
    refused("RESPONSE_SHAPE_REFUSED", coinglass_read, transport, ("IBIT",), first, first)


def test_the_valid_coinglass_forms_are_still_read() -> None:
    first = date(2024, 1, 11)
    transport = FakeTransport()
    body = '{"code":"0","msg":"success","data":[%s]}'
    flow = '{"timestamp":1704931200000,"flow_usd":-1.5,"price_usd":45000.25,"etf_flows":[{"etf_ticker":"IBIT","flow_usd":5},{"etf_ticker":"GBTC","flow_usd":null},{"etf_ticker":"FBTC"}]}'
    transport.add(coinglass.FLOW_HISTORY_URL, (body % flow).encode())
    transport.add(coinglass.fund_history_url("IBIT"), (body % (FUND_DAY % ("0.5", "9"))).encode())
    read = coinglass_read(transport, ("IBIT",), first, first)
    assert [(row.fund, row.flow_usd, row.aum_usd) for row in read.flows] == [("IBIT", Decimal(5), Decimal(9))]
    assert read.tickers_seen == ("IBIT",)


def test_a_coinglass_msg_must_be_a_string() -> None:
    first = date(2024, 1, 11)
    transport = coinglass_world({first: {"IBIT": 5}}, {"IBIT": {first: 9}}, first, first)
    transport.add(coinglass.FLOW_HISTORY_URL, b'{"code":"0","msg":null,"data":[]}')
    refused("RESPONSE_SHAPE_REFUSED", coinglass_read, transport, ("IBIT",), first, first)


def test_a_duplicate_coinglass_flow_or_assets_day_is_refused() -> None:
    first = date(2024, 1, 11)
    body = '{"code":"0","msg":"success","data":[%s]}'
    day = FLOW_DAY % ("0", "45000", "5")
    transport = FakeTransport()
    transport.add(coinglass.FLOW_HISTORY_URL, (body % f"{day},{day}").encode())
    transport.add(coinglass.fund_history_url("IBIT"), (body % (FUND_DAY % ("1", "9"))).encode())
    refused("DUPLICATE_PROVIDER_RECORD", coinglass_read, transport, ("IBIT",), first, first)
    # a repeated ticker within one day, even without a value, and a repeated day with distinct tickers
    null_twice = '{"timestamp":1704931200000,"flow_usd":0,"price_usd":1,"etf_flows":[{"etf_ticker":"GBTC","flow_usd":null},{"etf_ticker":"GBTC"}]}'
    transport.add(coinglass.FLOW_HISTORY_URL, (body % null_twice).encode())
    refused("DUPLICATE_PROVIDER_RECORD", coinglass_read, transport, ("IBIT",), first, first)
    other = '{"timestamp":1704931200000,"flow_usd":0,"price_usd":1,"etf_flows":[{"etf_ticker":"FBTC","flow_usd":1}]}'
    transport.add(coinglass.FLOW_HISTORY_URL, (body % f"{day},{other}").encode())
    refused("DUPLICATE_PROVIDER_RECORD", coinglass_read, transport, ("IBIT",), first, first)
    transport.add(coinglass.FLOW_HISTORY_URL, (body % day).encode())
    assets = FUND_DAY % ("1", "9")
    transport.add(coinglass.fund_history_url("IBIT"), (body % f"{assets},{assets}").encode())
    refused("DUPLICATE_PROVIDER_RECORD", coinglass_read, transport, ("IBIT",), first, first)


# --- owner Part B ruling 14: the envelope's msg and a fund day's btc_holdings may be absent ------------


def live_shape(page: bytes, *, holdings: bool = True) -> bytes:
    """A fixture page as CoinGlass's live responses are: no msg, and with ``holdings=False`` no btc_holdings."""

    payload = json.loads(page)
    del payload["msg"]
    if not holdings:
        for record in payload["data"]:
            del record["btc_holdings"]
    return json.dumps(payload).encode()


def live_world(flows: dict[date, dict[str, Any]], assets: dict[str, dict[date, Any]], *, holdings: bool = True) -> FakeTransport:
    transport = FakeTransport()
    transport.add(coinglass.FLOW_HISTORY_URL, live_shape(fx.coinglass_flow_page(flows)))
    for ticker, history in assets.items():
        transport.add(coinglass.fund_history_url(ticker), live_shape(fx.coinglass_fund_page(history, ticker=ticker), holdings=holdings))
    return transport


def project_flows(body: bytes) -> projection.ProjectedResponse:
    return projection.project_records(
        fetched(body), date_keys=("timestamp",), first_day=date(2024, 1, 11), last_day=date(2024, 1, 12), what="flows"
    )


def test_ruling_14_an_envelope_without_msg_is_projected_without_one() -> None:
    documented, live = project_flows(sentinel_flow_page()), project_flows(live_shape(sentinel_flow_page()))
    counts = (live.kept, live.dropped_prohibited, live.dropped_unrequested, live.dropped_holdout)
    assert counts == (documented.kept, documented.dropped_prohibited, documented.dropped_unrequested, documented.dropped_holdout)
    assert counts == (2, 1, 1, 2)
    assert live.body == documented.body.replace(b',"msg":"success"', b"", 1) and b"msg" not in live.body
    assert json.loads(live.body) == {"code": "0", "data": json.loads(sentinel_flow_page())["data"][2:4]}
    assert all(str(value).encode() not in live.body for value in SENTINELS.values())
    assert projection.verified_body(live, date_keys=("timestamp",), what="flows") == live.body
    # member order and whitespace do not matter; the projection is written in its own order
    kept = '{"timestamp":%d,"flow_usd":0,"price_usd":1,"etf_flows":[]}' % day_ms(date(2024, 1, 11))
    dropped = '{"timestamp":%d,"flow_usd":777000009,"price_usd":1,"etf_flows":[]}' % HOLDOUT_STAMP
    spaced = project_flows(('\n{ "data" : [ %s , %s ] , "code" : "0" }\n' % (dropped, kept)).encode())
    assert spaced.body == b'{"code":"0","data":[' + kept.encode() + b"]}" and spaced.dropped_holdout == 1


@pytest.mark.parametrize("msg", [b'"success"', b'""', b'"a\\u00e9b"'], ids=["success", "empty", "escaped"])
def test_ruling_14_a_present_msg_is_kept_byte_for_byte_as_before(msg: bytes) -> None:
    kept = VALID_RECORD.encode()
    projected = project_flows(b'{"msg":' + msg + b',"code":"0","data":[' + kept + b"]}")
    assert projected.body == b'{"code":"0","msg":' + msg + b',"data":[' + kept + b"]}"


@pytest.mark.parametrize(
    "body",
    [
        b"{}",
        b'{"code":"0"}',
        b'{"data":[]}',
        b'{"msg":"success","data":[]}',
        b'{"code":"0","msg":"success"}',
        b'{"code":"0","data":[],"extra":1}',
        b'{"code":"0","data":[],"data":[]}',
        b'{"code":"0","code":"0","data":[]}',
        b'{"code":"0","msg":"a","msg":"b","data":[]}',
        b'{"code":"0","Msg":"success","data":[]}',
        b'{"code":"0","message":"success","data":[]}',
        b'{"code":0,"data":[]}',
        b'{"code":null,"data":[]}',
        b'{"code":"0","msg":null,"data":[]}',
        b'{"code":"0","msg":1,"data":[]}',
        b'{"code":"0","msg":[],"data":[]}',
        b'{"code":"0","msg":{},"data":[]}',
        b'{"code":"0","msg":true,"data":[]}',
        b'{"code":"0","data":{}}',
        b'{"code":"0","data":null}',
        b'{"code":"0","data":"[]"}',
        b'{"code":"0","data":[]} x',
        b'{"code":"0","data":[{"timestamp":%d,"flow_usd":01}]}' % HOLDOUT_STAMP,
    ],
)
def test_ruling_14_the_envelope_is_still_exactly_code_and_data_with_an_optional_msg(body: bytes) -> None:
    refused("RESPONSE_SHAPE_REFUSED", project_flows, body)


def test_ruling_14_both_envelopes_are_read() -> None:
    for body in (b'{"code":"0","data":[]}', b'{"code":"0","msg":"success","data":[]}', b'{"data":[],"code":"0"}'):
        assert project_flows(body).kept == 0


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (b'{"code":"401","msg":"Upgrade plan"}', "the provider reports code '401': 'Upgrade plan'"),
        (b'{"msg":"Upgrade plan","code":"401"}', "the provider reports code '401': 'Upgrade plan'"),
        (b'{"code":"401"}', "the provider reports code '401'"),
        (b'{"code":"401","data":null}', "the provider reports code '401'"),
        (b'{"code":"40001","msg":"API key invalid","data":null}', "the provider reports code '40001': 'API key invalid'"),
        (b'{"code":"500","data":[{"timestamp":%d,"flow_usd":777000009}]}' % HOLDOUT_STAMP, "the provider reports code '500'"),
    ],
    ids=["no-data", "no-data-reordered", "code-only", "null-data", "documented", "records-unread"],
)
def test_ruling_14_a_provider_error_names_its_code_and_any_message_before_data_is_required(body: bytes, expected: str) -> None:
    error = refused("RESPONSE_SHAPE_REFUSED", project_flows, body)
    assert str(error) == f"RESPONSE_SHAPE_REFUSED: flows: {expected}"


def test_ruling_14_a_coinglass_read_refused_by_the_provider_names_its_status() -> None:
    first = date(2024, 1, 11)
    transport = FakeTransport()
    transport.add(coinglass.FLOW_HISTORY_URL, b'{"code":"401","msg":"Upgrade plan"}')
    error = refused("RESPONSE_SHAPE_REFUSED", coinglass_read, transport, None, first, first)
    assert "'401'" in str(error) and "'Upgrade plan'" in str(error) and len(transport.calls) == 1


@pytest.mark.parametrize("holdings", [True, False], ids=["with-holdings", "without-holdings"])
def test_ruling_14_a_live_shaped_read_gives_the_documented_reads_rows(holdings: bool) -> None:
    first, last = date(2024, 1, 11), date(2024, 1, 12)
    flows = {first: {"IBIT": 5, "GBTC": -7}, last: {"IBIT": 6}, date(2026, 1, 5): {"IBIT": 777000001}}
    assets = {"IBIT": {first: 9, last: 10, date(2026, 1, 5): 777000002}, "GBTC": {date(2019, 6, 3): 777000003, first: 11}}
    documented = coinglass_read(coinglass_world(flows, assets, first, last), None, first, last)
    live = coinglass_read(live_world(flows, assets, holdings=holdings), None, first, last)
    assert live.flows == documented.flows and len(live.flows) == 3
    assert (live.tickers_seen, live.missing_aum) == (documented.tickers_seen, documented.missing_aum)
    for mine, theirs in zip(live.projections, documented.projections, strict=True):
        assert (mine.url, mine.kept, mine.dropped) == (theirs.url, theirs.kept, theirs.dropped)
        assert b"msg" not in mine.body and b"77700000" not in mine.body
        assert (b"btc_holdings" in mine.body) == (holdings and mine.url != coinglass.FLOW_HISTORY_URL)
        if holdings:
            assert mine.body == theirs.body.replace(b',"msg":"success"', b"", 1)


def test_ruling_14_a_fund_history_may_mix_days_with_and_without_btc_holdings() -> None:
    first, second = date(2024, 1, 11), date(2024, 1, 12)
    without = json.loads(fund_record(second, second, "38.51"))
    del without["btc_holdings"]
    transport = live_world({first: {"IBIT": 5}, second: {"IBIT": 6}}, {})
    transport.add(coinglass.fund_history_url("IBIT"), ('{"code":"0","data":[%s,%s]}' % (fund_record(first, first, "38.51"), json.dumps(without))).encode())
    read = coinglass_read(transport, ("IBIT",), first, second)
    assert [(row.observation_date, row.flow_usd, row.aum_usd) for row in read.flows] == [(first, 5, 9), (second, 6, 9)]
    assert read.missing_aum == ()


FUND_MEMBERS = ("assets_date", "market_date", "market_price", "name", "nav", "net_assets", "premium_discount", "shares_outstanding", "ticker")


@pytest.mark.parametrize("holdings", [True, False], ids=["with-holdings", "without-holdings"])
@pytest.mark.parametrize("member", FUND_MEMBERS)
def test_ruling_14_every_other_fund_member_is_still_required(member: str, holdings: bool) -> None:
    first = date(2024, 1, 11)
    record = json.loads(FUND_DAY % ("1000", "9"))
    del record[member]
    if not holdings:
        del record["btc_holdings"]
    transport = live_world({first: {"IBIT": 5}}, {})
    transport.add(coinglass.fund_history_url("IBIT"), json.dumps({"code": "0", "data": [record]}).encode())
    refused("RESPONSE_SHAPE_REFUSED", coinglass_read, transport, ("IBIT",), first, first)


@pytest.mark.parametrize(
    ("remove", "add"),
    [
        (("btc_holdings",), {"btc_holding": 1000}),  # a misspelt holdings member
        ((), {"aum": 1}),  # an unknown member beside the holdings
        (("btc_holdings",), {"aum": 1}),  # an unknown member without them
    ],
    ids=["misspelt", "extra-with", "extra-without"],
)
def test_ruling_14_an_unknown_fund_member_still_refuses(remove: tuple[str, ...], add: dict[str, Any]) -> None:
    first = date(2024, 1, 11)
    record = {name: value for name, value in json.loads(FUND_DAY % ("1000", "9")).items() if name not in remove} | add
    transport = live_world({first: {"IBIT": 5}}, {})
    transport.add(coinglass.fund_history_url("IBIT"), json.dumps({"code": "0", "data": [record]}).encode())
    refused("RESPONSE_SHAPE_REFUSED", coinglass_read, transport, ("IBIT",), first, first)


@pytest.mark.parametrize("value", ["1", True, None, [], {}], ids=["string", "bool", "null", "array", "object"])
def test_ruling_14_a_present_btc_holdings_is_still_a_finite_number(value: Any) -> None:
    first = date(2024, 1, 11)
    record = json.loads(FUND_DAY % ("1000", "9")) | {"btc_holdings": value}
    transport = live_world({first: {"IBIT": 5}}, {})
    transport.add(coinglass.fund_history_url("IBIT"), json.dumps({"code": "0", "data": [record]}).encode())
    refused("RESPONSE_SHAPE_REFUSED", coinglass_read, transport, ("IBIT",), first, first)


@pytest.mark.parametrize("endpoint", ["flow", "fund"])
@pytest.mark.parametrize("msg", [None, 1, [], {}, True], ids=["null", "number", "array", "object", "bool"])
def test_ruling_14_a_present_msg_is_still_a_string(endpoint: str, msg: Any) -> None:
    first = date(2024, 1, 11)
    transport = live_world({first: {"IBIT": 5}}, {"IBIT": {first: 9}})
    if endpoint == "flow":
        url, page = coinglass.FLOW_HISTORY_URL, fx.coinglass_flow_page({first: {"IBIT": 5}})
    else:
        url, page = coinglass.fund_history_url("IBIT"), fx.coinglass_fund_page({first: 9})
    transport.add(url, json.dumps(json.loads(live_shape(page)) | {"msg": msg}).encode())
    refused("RESPONSE_SHAPE_REFUSED", coinglass_read, transport, ("IBIT",), first, first)


@pytest.mark.parametrize("member", ["timestamp", "flow_usd", "price_usd", "etf_flows"])
def test_ruling_14_every_flow_day_member_is_still_required(member: str) -> None:
    first = date(2024, 1, 11)
    payload = json.loads(live_shape(fx.coinglass_flow_page({first: {"IBIT": 5}})))
    del payload["data"][0][member]
    transport = live_world({}, {"IBIT": {first: 9}})
    transport.add(coinglass.FLOW_HISTORY_URL, json.dumps(payload).encode())
    refused("RESPONSE_SHAPE_REFUSED", coinglass_read, transport, ("IBIT",), first, first)


# --- re-review R14-1: a CoinGlass number no decimal can hold refuses instead of raising --------------

R14_HUGE = "1e+1000000000000000000"  # valid JSON; its exponent is past what decimal holds
R14_PLACEHOLDER = "@@r14-number@@"
R14_FIELDS = [
    ("flow", "flow_usd"),
    ("flow", "price_usd"),
    ("flow", "ticker flow_usd"),
    ("fund", "net_assets"),
    ("fund", "btc_holdings"),
    ("fund", "market_price"),
    ("fund", "nav"),
    ("fund", "premium_discount"),
    ("fund", "shares_outstanding"),
]


def r14_world(endpoint: str, field: str, numeral: str, *, msg: bool) -> FakeTransport:
    """A one-day IBIT read whose in-window ``endpoint`` record holds the raw JSON ``numeral`` at ``field``."""

    first = date(2024, 1, 11)
    flow = json.loads(fx.coinglass_flow_page({first: {"IBIT": 5}}))
    fund = json.loads(fx.coinglass_fund_page({first: 9}))
    if endpoint == "flow" and field == "ticker flow_usd":
        flow["data"][0]["etf_flows"][0]["flow_usd"] = R14_PLACEHOLDER
    else:
        (flow if endpoint == "flow" else fund)["data"][0][field] = R14_PLACEHOLDER
    transport = FakeTransport()
    for url, payload in ((coinglass.FLOW_HISTORY_URL, flow), (coinglass.fund_history_url("IBIT"), fund)):
        if not msg:
            del payload["msg"]
        body = json.dumps(payload)
        transport.add(url, body.replace(f'"{R14_PLACEHOLDER}"', numeral).encode())
    return transport


@pytest.mark.parametrize("trap", [True, False], ids=["caller-traps", "caller-does-not-trap"])
@pytest.mark.parametrize("msg", [True, False], ids=["with-msg", "without-msg"])
@pytest.mark.parametrize(("endpoint", "field"), R14_FIELDS, ids=[f"{endpoint}-{field.replace(' ', '-')}" for endpoint, field in R14_FIELDS])
def test_r14_1_a_json_number_no_decimal_can_hold_refuses_under_any_caller_context(endpoint: str, field: str, msg: bool, trap: bool) -> None:
    # re-review R14-1: json.loads(parse_float=Decimal) raised InvalidOperation, which is not a ValueError
    first = date(2024, 1, 11)
    transport = r14_world(endpoint, field, R14_HUGE, msg=msg)
    with localcontext() as caller:
        caller.traps[InvalidOperation] = trap
        error = refused("RESPONSE_SHAPE_REFUSED", coinglass_read, transport, ("IBIT",), first, first)
    what = "the flow history" if endpoint == "flow" else "the IBIT history"
    assert str(error) == f"RESPONSE_SHAPE_REFUSED: {what} holds a number no decimal can hold"
    assert len(transport.calls) == (1 if endpoint == "flow" else 2)


@pytest.mark.parametrize(
    "numeral",
    ["1e+1000000000000000000", "1E+99999999999999999999", "0e+1000000000000000000", "-1e+1000000000000000000", "1.5E+1000000000000000000"],
)
@pytest.mark.parametrize(("endpoint", "field"), [("flow", "flow_usd"), ("fund", "net_assets")])
def test_r14_1_each_exponent_no_decimal_can_hold_refuses(endpoint: str, field: str, numeral: str) -> None:
    first = date(2024, 1, 11)
    error = refused("RESPONSE_SHAPE_REFUSED", coinglass_read, r14_world(endpoint, field, numeral, msg=False), ("IBIT",), first, first)
    assert str(error).endswith("holds a number no decimal can hold")


@pytest.mark.parametrize("numeral", ["1e+999999999999999999", "1E-1000000000000000000", "1" + "0" * 4000, "-0.0"])
@pytest.mark.parametrize(("endpoint", "field"), [("flow", "price_usd"), ("fund", "btc_holdings")])
def test_r14_1_a_number_decimal_can_hold_still_decodes(endpoint: str, field: str, numeral: str) -> None:
    # the largest exponent decimal holds, a smaller one, a long integer and a negative zero, in a member no row uses
    first = date(2024, 1, 11)
    plain = coinglass_read(r14_world(endpoint, field, "1", msg=False), ("IBIT",), first, first)
    read = coinglass_read(r14_world(endpoint, field, numeral, msg=False), ("IBIT",), first, first)
    assert read.flows == plain.flows and len(read.flows) == 1


def test_r14_1_an_integer_too_long_for_python_still_refuses() -> None:
    first = date(2024, 1, 11)
    for endpoint, field in (("flow", "price_usd"), ("fund", "btc_holdings")):
        refused("RESPONSE_SHAPE_REFUSED", coinglass_read, r14_world(endpoint, field, "1" + "0" * 5000, msg=False), ("IBIT",), first, first)


def test_r14_1_the_decoding_does_not_depend_on_the_callers_context() -> None:
    first = date(2024, 1, 11)
    plain = coinglass_read(r14_world("fund", "btc_holdings", "1000", msg=True), ("IBIT",), first, first)
    hostile = Context(prec=1, Emax=1, Emin=-1, rounding=ROUND_HALF_UP, capitals=0, traps=list(Context().traps))
    with localcontext(hostile):
        again = coinglass_read(r14_world("fund", "btc_holdings", "1000", msg=True), ("IBIT",), first, first)
        transport = r14_world("fund", "net_assets", R14_HUGE, msg=False)
        error = refused("RESPONSE_SHAPE_REFUSED", coinglass_read, transport, ("IBIT",), first, first)
    assert again.flows == plain.flows and [row.aum_usd for row in again.flows] == [9]
    assert str(error) == "RESPONSE_SHAPE_REFUSED: the IBIT history holds a number no decimal can hold"


@pytest.mark.parametrize("msg", [True, False], ids=["with-msg", "without-msg"])
def test_r14_1_such_a_number_in_a_dropped_record_is_never_decoded(msg: bool, monkeypatch: pytest.MonkeyPatch) -> None:
    first, holdout = date(2024, 1, 11), date(2026, 1, 5)
    flows = {first: {"IBIT": 5}, holdout: {"IBIT": 777000001}}
    assets = {"IBIT": {date(2019, 6, 3): 777000003, first: 9, holdout: 777000002}}
    plain = coinglass_read(coinglass_world(flows, assets, first, first), None, first, first)
    transport = coinglass_world(flows, assets, first, first)
    for url, response in list(transport.responses.items()):
        payload = json.loads(response.body)
        if not msg:
            del payload["msg"]
        body = json.dumps(payload).encode()
        for sentinel in (b"777000001", b"777000002", b"777000003"):
            body = body.replace(sentinel, R14_HUGE.encode())
        transport.add(url, body)
    decoded: list[bytes] = []
    real_loads = coinglass.json.loads
    monkeypatch.setattr(coinglass.json, "loads", lambda body, **kw: decoded.append(body) or real_loads(body, **kw))
    read = coinglass_read(transport, None, first, first)
    assert read.flows == plain.flows and read.missing_aum == plain.missing_aum
    # json.loads is the module's own: the projection's status reads and both parsers' bodies, none with the number
    assert all(R14_HUGE.encode() not in body for body in decoded)
    assert sum(body.startswith(b'{"code":"0",') for body in decoded) == 2
