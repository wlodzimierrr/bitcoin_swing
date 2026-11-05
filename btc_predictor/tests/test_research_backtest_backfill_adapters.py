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
import json
import socket
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, Inexact, localcontext
from fractions import Fraction
from pathlib import Path
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
        ([fx.execution_page([fx.execution("b", utc(2021, 6, 1, 5)), fx.execution("a", utc(2021, 6, 1, 4))])], "CONTINUATION_CHAIN_REFUSED"),
        ([fx.execution_page([fx.execution("a", utc(2021, 6, 1, 1))], "token-0"), fx.execution_page([fx.execution("a", utc(2021, 6, 1, 2))])], "DUPLICATE_PROVIDER_RECORD"),
        ([fx.execution_page([], "token-0"), fx.execution_page([], "token-0")], "CONTINUATION_CHAIN_REFUSED"),
        ([b'{"elements":[],"len":1}'], "RESPONSE_SHAPE_REFUSED"),
        ([b'{"elements":[],"len":0,"extra":1}'], "RESPONSE_SHAPE_REFUSED"),
        ([b'{"elements":[{"event":{}}],"len":1}'], "RESPONSE_SHAPE_REFUSED"),
        ([fx.execution_page([fx.execution("a", utc(2021, 6, 1, 1), quantity="0")])], "RESPONSE_SHAPE_REFUSED"),
    ],
    ids=["outside-day", "descending", "duplicate-uid", "repeated-token", "len", "extra-key", "no-execution", "zero-quantity"],
)
def test_a_broken_execution_chain_is_refused(pages: list[bytes], reason: str) -> None:
    refused(reason, kraken.read_execution_day, make_fetcher(day_world(pages)), DAY)


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
