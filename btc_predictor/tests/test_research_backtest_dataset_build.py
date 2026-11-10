"""RBT-003 Part B: the dataset build, its window-bounded reader, the frozen files and the public index.

A synthetic world only: every collection unit is produced by the real
collection run against fake transports, and the rows its collectors insert
are captured from a recording connection; no network (every socket is
refused), no database. Owner Part B rulings 15 and 16.
"""

from __future__ import annotations

import contextlib
import dataclasses
import gzip
import json
import os
import random
import shutil
import socket
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.dialects import postgresql

from btc_predictor.data import OhlcvBar
from btc_predictor.db import raw as raw_tables
from btc_predictor.research_backtest import backfill_binance as binance
from btc_predictor.research_backtest import backfill_coinglass as coinglass
from btc_predictor.research_backtest import backfill_coinmetrics as coinmetrics
from btc_predictor.research_backtest import backfill_kraken as kraken
from btc_predictor.research_backtest import backfill_run as run
from btc_predictor.research_backtest import dataset_build as build
from btc_predictor.research_backtest import dataset_reader as reader
from btc_predictor.research_backtest import replay_inputs as v1
from btc_predictor.research_backtest import replay_inputs_v2 as v2
from btc_predictor.research_backtest.backfill_sources import BackfillRefused, TransportResponse
from btc_predictor.tests import rbt003_backfill_fixtures as fx
from btc_predictor.tests.rbt003_backfill_fixtures import RETRIEVED_AT, FakeTransport, utc

REPOSITORY = Path(__file__).resolve().parents[2]
BULK = datetime(2026, 8, 29, 14, 55, tzinfo=UTC)
LIQUIDATION_DAY, DISAGREEING_DAY = date(2021, 6, 1), date(2021, 6, 2)
DISAGREEING_HOUR = utc(2021, 6, 2, 3)
UNITS = {
    "binance-funding": ("2020-02",),
    "binance-open-interest": ("2020-09",),
    "binance-perp-volume": ("2020-01",),
    "binance-basis": ("all",),
    "kraken-liquidations": (LIQUIDATION_DAY.isoformat(), DISAGREEING_DAY.isoformat()),
    "coinglass-etf": ("all",),
    "coinmetrics-market-cap": ("all",),
    "ohlcv-missing-hours": ("bitfinex", "coinbase"),
}
MARKERS = ("777000005", "777000006", "130000000777", "100.77", "0.000777")  # distinctive values: none may reach a public file


@pytest.fixture(autouse=True)
def no_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("a test opened a socket")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def refused(error: type[Exception], reason: str, call: Any, *args: Any, **kwargs: Any) -> Exception:
    with pytest.raises(error) as caught:
        call(*args, **kwargs)
    assert caught.value.reason_code == reason, str(caught.value)  # type: ignore[attr-defined]
    return caught.value


# --- the synthetic collection ----------------------------------------------------------------------


def tardis_body() -> bytes:
    return json.dumps({"id": "cryptofacilities", "incidentReports": [], "availableSymbols": []}).encode()


def add_liquidation_day(transport: FakeTransport, day: date, *, series_liquidation: str) -> None:
    start = datetime(day.year, day.month, day.day, tzinfo=UTC)
    executions = [fx.execution(f"{day}-e{hour}", start + timedelta(hours=hour, minutes=5)) for hour in range(24)]
    executions.append(fx.execution(f"{day}-liq", start + timedelta(hours=3, minutes=7), quantity="777000005", order_type="Liquidation", direction="Sell"))
    executions.sort(key=lambda item: item["timestamp"])
    transport.add(kraken.executions_url(start, start + timedelta(days=1)), fx.execution_page(executions))
    series = {start + timedelta(hours=hour): (series_liquidation if hour == 3 else "0") for hour in range(24)}
    transport.add(kraken.liquidation_volume_url(start, start + timedelta(hours=23)), fx.series_body(series))


class World:
    """One transport answering every source's URLs; the candle hosts answer with no candle."""

    def __init__(self) -> None:
        self.fake = FakeTransport()
        t = self.fake
        fx.add_archive(t, binance.funding_archive_url(date(2020, 2, 1)), [fx.funding_row(utc(2020, 2, d, h), rate="0.000777") for d in (1, 2) for h in (0, 8, 16)])
        fx.add_archive(t, binance.metrics_archive_url(date(2020, 9, 1)), [fx.metrics_row(utc(2020, 9, 1, h)) for h in range(24)])
        fx.add_archive(t, binance.usdm_klines_archive_url(date(2020, 1, 1)), [fx.kline_row(utc(2020, 1, 1, h), "7200") for h in range(6)])
        t.add(binance.archive_listing_url(binance.COINM_KLINES_PREFIX), fx.s3_listing(["BTCUSD_200925", "BTCUSD_PERP"]))
        fx.add_contract(t, "BTCUSD_200925", utc(2020, 8, 10, 8), utc(2020, 9, 25, 7), lambda at: Decimal("10010") + at.hour)
        fx.add_index(t, utc(2020, 8, 1), utc(2020, 9, 30, 23), lambda at: Decimal("10000"))
        t.add(run.TARDIS_EXCHANGE_URL, tardis_body())
        add_liquidation_day(t, LIQUIDATION_DAY, series_liquidation="777000005")
        add_liquidation_day(t, DISAGREEING_DAY, series_liquidation="777000006")  # owner Part B ruling 16: disagrees
        first, second = date(2024, 1, 11), date(2024, 2, 1)
        t.add(coinglass.FLOW_HISTORY_URL, fx.coinglass_flow_page({first: {"IBIT": 5, "GBTC": -7}, second: {"IBIT": 6}}))
        t.add(coinglass.fund_history_url("IBIT"), fx.coinglass_fund_page({first: 9, second: 10}))
        t.add(coinglass.fund_history_url("GBTC"), fx.coinglass_fund_page({first: 11}, ticker="GBTC"))
        caps = [(date(2020, 1, 1) + timedelta(days=k), f"130000000777.{k}") for k in range(4)]
        t.add(coinmetrics.timeseries_url(date(2020, 1, 1), date(2025, 12, 31)), fx.coinmetrics_page(caps))

    def __call__(self, url: str, headers: Any) -> TransportResponse:
        if url.startswith(("https://api.exchange.coinbase.com/", "https://api-pub.bitfinex.com/")):
            return TransportResponse(200, b"[]")
        return self.fake(url, headers)


class RecordingConnection:
    def __init__(self) -> None:
        self.statements: list[Any] = []

    def execute(self, statement: Any) -> None:
        self.statements.append(statement)


class Recorder:
    def __init__(self) -> None:
        self.connections: list[RecordingConnection] = []

    @contextlib.contextmanager
    def connect(self) -> Any:
        connection = RecordingConnection()
        self.connections.append(connection)
        yield connection

    def rows(self, table: str) -> list[dict[str, Any]]:
        """Every row the collectors inserted into ``raw.<table>``, as its columns."""

        found = []
        columns = [column.name for column in getattr(raw_tables, table).c]
        for connection in self.connections:
            for statement in connection.statements:
                compiled = statement.compile(dialect=postgresql.dialect())
                if not str(compiled).startswith(f"INSERT INTO raw.{table} "):
                    continue
                params = compiled.params
                if f"{columns[0]}_m0" not in params:
                    found.append({name: params[name] for name in columns})
                    continue
                index = 0
                while f"{columns[0]}_m{index}" in params:
                    found.append({name: params[f"{name}_m{index}"] for name in columns})
                    index += 1
        return found


def units_of(source: str) -> tuple[str, ...]:
    return UNITS[source]


def ohlcv_bars(venue: v1.ReplayVenue, *, skip: tuple[int, ...] = ()) -> tuple[OhlcvBar, ...]:
    start = utc(2020, 2, 1)
    return tuple(
        OhlcvBar(start + timedelta(hours=h), venue.exchange, venue.symbol, "1h", Decimal("100"), Decimal("101"), Decimal("99"), Decimal("100.77"), Decimal("2.5"), venue.provider, BULK)
        for h in range(48)
        if h not in skip
    )


@dataclasses.dataclass
class Collected:
    root: Path
    rows: reader.DatasetRows


def collect(root: Path) -> Collected:
    (root / ".git").mkdir(parents=True)
    store = run.EvidenceStore(root, public_repository=REPOSITORY)
    world, recorder = World(), Recorder()
    ctx = run.RunContext(
        transport=world, store=store, clock=lambda: RETRIEVED_AT, connect=recorder.connect,
        coinglass_key="key-123", allow_coinglass=True, out=lambda line: None,
    )
    assert run.run_unit(ctx, "kraken-incidents", "all").status == "DONE"
    for source, units in UNITS.items():
        for unit in units:
            report = run.run_unit(ctx, source, unit)
            assert report.status == "DONE", (source, unit, report.detail)
    rows: reader.DatasetRows = {}
    for series in reader.SERIES:
        if series.table.name == "btc_ohlcv":
            venue = next(v for v in v1.REPLAY_VENUES if build.venue_series_name(v) == series.name)
            rows[series.name] = ohlcv_bars(venue, skip=(7,) if venue is v1.BITFINEX_REPLAY_VENUE else ())
        else:
            rows[series.name] = reader.sorted_records(series, (reader.owner_record(series, row) for row in recorder.rows(series.table.name)))
    return Collected(root, rows)


@pytest.fixture(scope="module")
def collected(tmp_path_factory: pytest.TempPathFactory) -> Collected:
    return collect(tmp_path_factory.mktemp("world") / "backtest_evidence")


@pytest.fixture
def world(collected: Collected, tmp_path: Path) -> Collected:
    """A private copy of the collected store, free to change."""

    root = tmp_path / "backtest_evidence"
    shutil.copytree(collected.root, root, symlinks=True)
    return Collected(root, dict(collected.rows))


def store_of(world: Collected) -> run.EvidenceStore:
    return run.EvidenceStore(world.root, public_repository=REPOSITORY)


def evidence_of(world: Collected) -> build.BuildEvidence:
    return build.load_build_evidence(store_of(world), units=units_of)


def built(world: Collected) -> tuple[build.BuildEvidence, build.ReplayDatasets, dict[str, Any]]:
    evidence = evidence_of(world)
    datasets = build.build_replay_datasets(world.rows, evidence)
    record = build.write_dataset(store_of(world), world.rows, datasets, evidence, code_commit="c" * 40)
    return evidence, datasets, record


# --- the build -----------------------------------------------------------------------------------


def test_the_world_holds_every_series_rbt003_collected(collected: Collected) -> None:
    assert [series.name for series in reader.SERIES] == list(collected.rows)
    assert all(collected.rows[name] for name in collected.rows)
    assert {row.provider for row in collected.rows["etf_flows"]} == {coinglass.COINGLASS_PROVIDER}


def test_the_build_writes_the_frozen_inputs_the_five_manifests_and_build_json_last(world: Collected) -> None:
    evidence, datasets, record = built(world)
    directory = world.root / build.DATASET_LAYOUT
    assert sorted(path.name for path in directory.iterdir()) == ["BUILD.json", "inputs", "manifests"]
    assert sorted(path.name for path in (directory / "inputs").iterdir()) == sorted(f"{s.name}.json.gz" for s in reader.SERIES)
    assert sorted(record["manifests"]) == sorted(["shared_snapshot", "venue_bitstamp", "venue_coinbase", "venue_bitfinex", "extended_snapshot"])
    assert (directory / "BUILD.json").read_bytes() == v1.canonical_json_bytes(record) and set(record) == build.BUILD_KEYS
    assert record["code_commit"] == "c" * 40 and record["window"] == v1.DATA_WINDOW.as_record()
    assert record["reader"] == {"version": reader.READER_VERSION, "series": [series.as_record() for series in reader.SERIES]}
    # each manifest file is the builder's canonical bytes, bound by the builder's own digest
    manifests = datasets.manifests()
    assert record["manifests"]["shared_snapshot"]["sha256"] == datasets.shared.manifest_sha256
    assert record["manifests"]["extended_snapshot"]["sha256"] == datasets.extended.manifest_sha256
    for name, data in manifests.items():
        assert gzip.decompress((directory / "manifests" / f"{name}.json.gz").read_bytes()) == data
        assert (directory / "manifests" / f"{name}.json.gz").read_bytes() == run.deterministic_gzip(data)
    # the venue manifests bind the one shared snapshot, and the extended snapshot binds it too
    assert {dataset.manifest["shared_snapshot"]["manifest_sha256"] for dataset in datasets.venues} == {datasets.shared.manifest_sha256}
    assert datasets.extended.manifest["shared_snapshot"]["manifest_sha256"] == datasets.shared.manifest_sha256
    for series in reader.SERIES:
        assert record["inputs"][series.name]["records"] == len(world.rows[series.name])
    assert evidence.record["units"]["kraken-liquidations"]["unit_count"] == 2


def test_the_frozen_inputs_parse_back_to_the_rows_read(world: Collected) -> None:
    built(world)
    stored = build.load_dataset(store_of(world))
    assert build.frozen_rows(stored) == {name: records for name, records in world.rows.items()}


def test_verify_rebuilds_identically_from_the_database_rows_and_from_the_frozen_inputs(world: Collected) -> None:
    evidence, _, _ = built(world)
    stored = build.load_dataset(store_of(world))
    assert build.verify_dataset(stored, evidence, world.rows) == {
        "evidence_unchanged": True,
        "manifests_from_frozen_inputs": True,
        "inputs_from_database": True,
        "manifests_from_database": True,
    }
    changed = dict(world.rows)
    bar = changed["ohlcv_1h_coinbase"][0]
    changed["ohlcv_1h_coinbase"] = (dataclasses.replace(bar, volume=bar.volume + 1), *changed["ohlcv_1h_coinbase"][1:])
    results = build.verify_dataset(stored, evidence, changed)
    assert results["inputs_from_database"] is False and results["manifests_from_database"] is False
    assert results["manifests_from_frozen_inputs"] is True


def test_the_build_is_independent_of_row_order(world: Collected) -> None:
    evidence = evidence_of(world)
    expected = build.build_replay_datasets(world.rows, evidence).manifests()
    shuffled = {}
    for name, records in world.rows.items():
        items = list(records)
        random.Random(len(items)).shuffle(items)
        shuffled[name] = tuple(items)
    assert build.build_replay_datasets(shuffled, evidence).manifests() == expected
    series = reader.SERIES_BY_NAME["funding_rates"]
    assert build.input_file_bytes(series, reader.sorted_records(series, shuffled["funding_rates"])) == build.input_file_bytes(series, world.rows["funding_rates"])


def test_numbers_enter_by_value_so_a_numeric_read_back_gives_the_same_files(world: Collected) -> None:
    def at_scale_18(record: Any) -> Any:
        changes = {
            field.name: getattr(record, field.name).quantize(Decimal("1e-18"))
            for field in dataclasses.fields(record)
            if isinstance(getattr(record, field.name), Decimal) and field.name != "funding_interval_hours"
        }
        return dataclasses.replace(record, **changes)

    evidence = evidence_of(world)
    read_back = {name: tuple(at_scale_18(record) for record in records) for name, records in world.rows.items()}
    assert read_back["funding_rates"][0].funding_rate.as_tuple() != world.rows["funding_rates"][0].funding_rate.as_tuple()
    for series in reader.SERIES:
        assert build.input_file_bytes(series, read_back[series.name]) == build.input_file_bytes(series, world.rows[series.name])
    assert build.build_replay_datasets(read_back, evidence).manifests() == build.build_replay_datasets(world.rows, evidence).manifests()


@pytest.mark.parametrize("seed", ["0", "8675309"])
def test_a_fresh_process_rebuilds_the_manifests_from_the_frozen_inputs(world: Collected, tmp_path: Path, seed: str) -> None:
    built(world)
    script = tmp_path / "rebuild.py"
    script.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "from btc_predictor.research_backtest import backfill_run as run, dataset_build as build\n"
        "units = {k: tuple(v) for k, v in " + repr({k: list(v) for k, v in UNITS.items()}) + ".items()}\n"
        "store = run.EvidenceStore(Path(sys.argv[1]), public_repository=build.PUBLIC_REPOSITORY)\n"
        "stored = build.load_dataset(store)\n"
        "evidence = build.load_build_evidence(store, units=units.__getitem__)\n"
        "print(build.verify_dataset(stored, evidence, None))\n"
    )
    env = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(REPOSITORY)}
    other = tmp_path / "elsewhere"
    other.mkdir()
    result = subprocess.run([sys.executable, str(script), str(world.root)], cwd=other, env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr[-2000:]
    assert result.stdout.strip() == "{'evidence_unchanged': True, 'manifests_from_frozen_inputs': True}"


# --- owner Part B ruling 16: a disagreeing hour is withheld, its day incomplete ----------------------


def test_ruling_16_a_disagreeing_hour_is_withheld_and_its_day_is_incomplete(world: Collected) -> None:
    evidence, datasets, record = built(world)
    assert evidence.withheld_hours == frozenset({DISAGREEING_HOUR})
    assert record["evidence"]["withheld_liquidation_hours"] == [DISAGREEING_HOUR.isoformat()]
    manifest = datasets.extended.manifest
    hours = manifest["families"]["LIQUIDATIONS"]["hour_evidence"]
    assert hours["record_count"] == 47 and hours["gaps"]["spans"] == [
        {"first_missing": DISAGREEING_HOUR.isoformat(), "last_missing": DISAGREEING_HOUR.isoformat(), "missing_slots": 1}
    ]
    observed = {record_["identity"]["observation_time"] for record_ in manifest["families"]["LIQUIDATIONS"]["records"]}
    assert utc(2021, 6, 1, 3).isoformat() in observed and DISAGREEING_HOUR.isoformat() not in observed
    days = {item["observation_date"]: item for item in manifest["liquidation_percentile"]["records"]}
    assert days["2021-06-01"]["complete"] is True
    assert days["2021-06-02"]["complete"] is False and days["2021-06-02"]["reason_codes"] == [v2.LIQUIDATION_FEED_UNAVAILABLE]
    # the frozen inputs keep every row as read
    frozen = build.frozen_rows(build.load_dataset(store_of(world)))
    assert DISAGREEING_HOUR in {row.observation_time for row in frozen["liquidations"]}


def test_ruling_16_the_reviewed_v2_builder_still_refuses_a_disagreement(world: Collected) -> None:
    evidence = evidence_of(world)
    shared = build.build_replay_datasets(world.rows, evidence).shared
    error = refused(
        v2.ExtendedReplayInputRefused, "LIQUIDATION_CORROBORATION_DISAGREES", v2.build_extended_replay_snapshot,
        shared_snapshot=shared, futures_basis=world.rows["futures_basis"], futures_basis_listing=evidence.listing,
        market_cap_evidence=evidence.market_cap, liquidations=world.rows["liquidations"], liquidation_hours=evidence.liquidation_hours,
    )
    assert "2021-06-02T03:00" in str(error)


# --- the evidence ----------------------------------------------------------------------------------


def test_a_scheduled_unit_not_collected_is_refused(world: Collected) -> None:
    units = {**UNITS, "kraken-liquidations": (*UNITS["kraken-liquidations"], "2021-06-03")}
    refused(build.DatasetBuildRefused, "EVIDENCE_UNIT_REFUSED", build.load_build_evidence, store_of(world), units=units.__getitem__)
    refused(build.DatasetBuildRefused, "EVIDENCE_UNIT_REFUSED", build.load_build_evidence, store_of(world), units=lambda source: ())


def test_ruling_15_the_missing_hours_must_be_collected_and_persisted_first(world: Collected) -> None:
    shutil.rmtree(store_of(world).unit_dir("ohlcv-missing-hours", "coinbase"))
    refused(build.DatasetBuildRefused, "EVIDENCE_UNIT_REFUSED", evidence_of, world)
    ctx = run.RunContext(transport=World(), store=store_of(world), clock=lambda: RETRIEVED_AT, connect=None, out=lambda line: None)
    assert run.run_unit(ctx, "ohlcv-missing-hours", "coinbase").status == "DONE"  # read without persistence
    refused(build.DatasetBuildRefused, "EVIDENCE_UNIT_REFUSED", evidence_of, world)
    still = evidence_of_except(world)
    assert still["still_missing_hours"]["bitfinex"] == [hour.isoformat() for hour in run.ohlcv.MISSING_HOURS_VENUES["bitfinex"].hours()]


def evidence_of_except(world: Collected) -> dict[str, Any]:
    store = store_of(world)
    shutil.rmtree(store.unit_dir("ohlcv-missing-hours", "coinbase"))
    return dict(build.load_build_evidence(store, units=lambda source: ("bitfinex",) if source == "ohlcv-missing-hours" else UNITS[source]).record)


def test_a_changed_evidence_file_refuses(world: Collected) -> None:
    path = store_of(world).unit_dir("kraken-liquidations", DISAGREEING_DAY.isoformat()) / build.HOUR_EVIDENCE_FILE
    path.write_bytes(path.read_bytes() + b"\0")
    refused(BackfillRefused, "PROVIDER_REQUEST_MISMATCH", evidence_of, world)


def test_hour_evidence_that_is_not_its_days_24_hours_is_refused(world: Collected) -> None:
    store = store_of(world)
    source = store.unit_dir("kraken-liquidations", LIQUIDATION_DAY.isoformat())
    files = {name: (source / name).read_bytes() for name in ("liquidation_hour_evidence.json.gz", "summary.json", "retrievals.json")}
    marker = json.loads((source / "DONE.json").read_bytes())
    store.write("kraken-liquidations", "2021-06-05", files, completed_at=RETRIEVED_AT, persisted=marker["persisted"])
    units = {**UNITS, "kraken-liquidations": (*UNITS["kraken-liquidations"], "2021-06-05")}
    error = refused(build.DatasetBuildRefused, "EVIDENCE_MISMATCH", build.load_build_evidence, store, units=units.__getitem__)
    assert "2021-06-05" in str(error)


def test_rows_that_are_not_what_the_units_persisted_are_refused(world: Collected) -> None:
    evidence = evidence_of(world)
    for name in build.SERIES_SOURCES:
        fewer = {**world.rows, name: world.rows[name][1:]}
        refused(build.DatasetBuildRefused, "EVIDENCE_MISMATCH", build.build_replay_datasets, fewer, evidence)


# --- the frozen files ------------------------------------------------------------------------------


def test_an_existing_dataset_is_never_overwritten(world: Collected) -> None:
    evidence, datasets, _ = built(world)
    before = (world.root / build.DATASET_LAYOUT / "BUILD.json").read_bytes()
    refused(build.DatasetBuildRefused, "DATASET_EXISTS", build.write_dataset, store_of(world), world.rows, datasets, evidence, code_commit="d" * 40)
    assert (world.root / build.DATASET_LAYOUT / "BUILD.json").read_bytes() == before


def test_a_linked_dataset_directory_is_refused_and_nothing_lands_outside(world: Collected, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (world.root / "research_backtest_v1" / "datasets").symlink_to(outside, target_is_directory=True)
    evidence = evidence_of(world)
    datasets = build.build_replay_datasets(world.rows, evidence)
    with pytest.raises((build.DatasetBuildRefused, BackfillRefused)):
        build.write_dataset(store_of(world), world.rows, datasets, evidence, code_commit="c" * 40)
    assert list(outside.iterdir()) == []


def _rewrite_gzip(path: Path, change: Any) -> None:
    path.write_bytes(run.deterministic_gzip(change(gzip.decompress(path.read_bytes()))))


TAMPERS = {
    "gzip bytes": lambda d: (d / "inputs" / "liquidations.json.gz").write_bytes((d / "inputs" / "liquidations.json.gz").read_bytes() + b"\0"),
    "content": lambda d: _changed_content(d, "manifests", "venue_coinbase"),
    "missing file": lambda d: (d / "inputs" / "etf_flows.json.gz").unlink(),
    "build record key": lambda d: (d / "BUILD.json").write_bytes(v1.canonical_json_bytes({**json.loads((d / "BUILD.json").read_bytes()), "extra": 1})),
    "build record spacing": lambda d: (d / "BUILD.json").write_bytes(json.dumps(json.loads((d / "BUILD.json").read_bytes())).encode()),
    "renamed entry": lambda d: (d / "BUILD.json").write_bytes(
        v1.canonical_json_bytes(_renamed(json.loads((d / "BUILD.json").read_bytes())))
    ),
}


def _changed_content(directory: Path, part: str, name: str) -> None:
    """Change one file's content and its gzip digest, so only the uncompressed digest can catch it."""

    path = directory / part / f"{name}.json.gz"
    _rewrite_gzip(path, lambda data: data.replace(b'"venue"', b'"VENUE"', 1))
    record = json.loads((directory / "BUILD.json").read_bytes())
    record[part][name].update(gzip_sha256=build.sha256_hex(path.read_bytes()), gzip_size=len(path.read_bytes()))
    (directory / "BUILD.json").write_bytes(v1.canonical_json_bytes(record))


def _renamed(record: dict[str, Any]) -> dict[str, Any]:
    record["inputs"]["etf_flows"]["file"] = "inputs/funding_rates.json.gz"
    return record


@pytest.mark.parametrize("tamper", sorted(TAMPERS))
def test_a_stored_dataset_that_does_not_match_its_build_record_is_refused(world: Collected, tamper: str) -> None:
    built(world)
    TAMPERS[tamper](world.root / build.DATASET_LAYOUT)
    refused(build.DatasetBuildRefused, "DATASET_FILE_REFUSED", build.load_dataset, store_of(world))


def test_a_linked_stored_file_is_refused(world: Collected, tmp_path: Path) -> None:
    built(world)
    path = world.root / build.DATASET_LAYOUT / "inputs" / "etf_flows.json.gz"
    copy = tmp_path / "copy.gz"
    shutil.copy(path, copy)
    path.unlink()
    path.symlink_to(copy)
    refused(build.DatasetBuildRefused, "DATASET_FILE_REFUSED", build.load_dataset, store_of(world))


def _file(world: Collected, name: str = "funding_rates") -> tuple[reader.DatasetSeries, bytes]:
    series = reader.SERIES_BY_NAME[name]
    return series, build.input_file_bytes(series, world.rows[name])


def _edit(data: bytes, change: Any) -> bytes:
    payload = json.loads(data)
    change(payload)
    return v1.canonical_json_bytes(payload)


INPUT_EDITS = {
    "not json": lambda data: b"{",
    "a number not a string": lambda data: _edit(data, lambda p: p["records"][0].update(funding_rate=1)),
    "trailing zero": lambda data: _edit(data, lambda p: p["records"][0].update(funding_rate="0.0007770")),
    "exponent": lambda data: _edit(data, lambda p: p["records"][0].update(funding_rate="7.77E-4")),
    "not a number": lambda data: _edit(data, lambda p: p["records"][0].update(funding_rate="NaN")),
    "huge exponent": lambda data: _edit(data, lambda p: p["records"][0].update(funding_rate="1e999999999999999999")),
    "offset instant": lambda data: _edit(data, lambda p: p["records"][0].update(observation_time="2020-02-01T01:00:00+01:00")),
    "naive instant": lambda data: _edit(data, lambda p: p["records"][0].update(observation_time="2020-02-01T00:00:00")),
    "extra field": lambda data: _edit(data, lambda p: p["records"][0].update(extra="x")),
    "missing field": lambda data: _edit(data, lambda p: p["records"][0].pop("source")),
    "reordered": lambda data: _edit(data, lambda p: p["records"].reverse()),
    "duplicated": lambda data: _edit(data, lambda p: p["records"].append(p["records"][-1])),
    "another version": lambda data: _edit(data, lambda p: p.update(file_version="OTHER")),
    "another series": lambda data: _edit(data, lambda p: p["series"].update(name="open_interest")),
    "spacing": lambda data: json.dumps(json.loads(data)).encode(),
    "deep nesting": lambda data: b"[" * 100_000 + b"]" * 100_000,
}


@pytest.mark.parametrize("edit", sorted(INPUT_EDITS))
def test_a_frozen_input_file_must_be_exactly_the_canonical_file_of_its_records(world: Collected, edit: str) -> None:
    series, data = _file(world)
    assert build.parse_input_file(series, data) == world.rows["funding_rates"]
    refused(build.DatasetBuildRefused, "DATASET_FILE_REFUSED", build.parse_input_file, series, INPUT_EDITS[edit](data))


def test_the_aum_may_be_null_and_stays_null(world: Collected) -> None:
    series = reader.SERIES_BY_NAME["etf_flows"]
    flows = tuple(dataclasses.replace(flow, aum_usd=None) for flow in world.rows["etf_flows"])
    assert all(flow.aum_usd is None for flow in build.parse_input_file(series, build.input_file_bytes(series, flows)))


# --- the window-bounded reader ---------------------------------------------------------------------


def sql(statement: Any) -> str:
    return " ".join(str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})).split())


@pytest.mark.parametrize(
    ("name", "bound"),
    [
        ("ohlcv_1h_bitstamp", "raw.btc_ohlcv.timestamp >= '2020-01-01 00:00:00+00:00' AND raw.btc_ohlcv.timestamp <= '2025-12-31 23:00:00+00:00'"),
        (
            "funding_rates",
            "raw.funding_rates.observation_time - CAST(raw.funding_rates.funding_interval_hours AS FLOAT) * interval '1 hour' >= '2020-01-01 00:00:00+00:00' "
            "AND raw.funding_rates.observation_time < '2026-01-01 00:00:00+00:00'",
        ),
        ("open_interest", "raw.open_interest.observation_time >= '2020-01-01 00:00:00+00:00' AND raw.open_interest.observation_time < '2026-01-01 00:00:00+00:00'"),
        ("perp_volume", "raw.perp_volume.observation_time >= '2020-01-01 00:00:00+00:00' AND raw.perp_volume.observation_time <= '2025-12-31 23:00:00+00:00'"),
        ("futures_basis", "raw.futures_basis.observation_time >= '2020-01-01 00:00:00+00:00' AND raw.futures_basis.observation_time < '2026-01-01 00:00:00+00:00'"),
        ("liquidations", "raw.liquidations.observation_time >= '2020-01-01 00:00:00+00:00' AND raw.liquidations.observation_time <= '2025-12-31 23:00:00+00:00'"),
        ("etf_flows", "raw.etf_flows.observation_date >= '2020-01-01' AND raw.etf_flows.observation_date <= '2025-12-31'"),
    ],
)
def test_every_query_names_its_series_and_bounds_it_to_the_data_window(name: str, bound: str) -> None:
    series = reader.SERIES_BY_NAME[name]
    text = sql(reader.series_statement(series))
    assert text.endswith(bound), text
    for column, value in series.identity:
        assert f"raw.{series.table.name}.{column} = '{value}'" in text
    assert "2019" not in text and "2026-01-01 00:00:00+00:00' AND" not in text.split("WHERE")[1].replace(bound, "")
    assert text.count(" OR ") == 0


def test_the_series_are_the_three_venues_and_what_rbt003_collected() -> None:
    assert [series.name for series in reader.SERIES] == [
        "ohlcv_1h_bitstamp", "ohlcv_1h_coinbase", "ohlcv_1h_bitfinex",
        "funding_rates", "open_interest", "perp_volume", "futures_basis", "liquidations", "etf_flows",
    ]
    assert dict(reader.SERIES_BY_NAME["liquidations"].identity) == {
        "exchange": "kraken_futures", "symbol": "PI_XBTUSD", "timeframe": "1h", "quantity_unit": "contracts", "provider": "kraken_futures_rest_history",
    }
    assert dict(reader.SERIES_BY_NAME["etf_flows"].identity) == {"provider": "coinglass"}
    for table in reader.TABLES:
        text = sql(reader.table_count_statement(table))
        assert text.startswith(f"SELECT count(*) AS count_1 FROM raw.{table.name} WHERE")
        assert ("2025-12-31'" in text) if table.name == "etf_flows" else ("< '2026-01-01 00:00:00+00:00'" in text)


class Result:
    def __init__(self, *, scalar: Any = None, rows: list[dict[str, Any]] | None = None) -> None:
        self.scalar, self.rows = scalar, rows

    def scalar_one(self) -> Any:
        return self.scalar

    def mappings(self) -> Result:
        return self

    def all(self) -> list[dict[str, Any]]:
        return list(self.rows or [])


class FakeDatabase:
    """Answers the reader's own statements from rows held in memory; any other statement fails the test."""

    def __init__(self, rows: reader.DatasetRows, *, read_only: str = "on", surplus: dict[str, int] | None = None, convert: Any = None) -> None:
        self.rows, self.read_only, self.surplus = rows, read_only, surplus or {}
        self.convert = convert or (lambda value: value)
        self.statements: list[str] = []

    def execute(self, statement: Any) -> Result:
        text = sql(statement)
        self.statements.append(text)
        if text == sql(reader.READ_ONLY_STATEMENT):
            return Result(scalar=self.read_only)
        for series in reader.SERIES:
            if text == sql(reader.series_statement(series)):
                return Result(rows=[{k: self.convert(v) for k, v in dataclasses.asdict(r).items()} for r in self.rows[series.name]])
        for table in reader.TABLES:
            if text == sql(reader.table_count_statement(table)):
                held = sum(len(self.rows[s.name]) for s in reader.SERIES if s.table is table)
                return Result(scalar=held + self.surplus.get(table.name, 0))
        raise AssertionError(f"unexpected statement {text}")

    @contextlib.contextmanager
    def connect(self) -> Any:
        yield self


def test_the_reader_reads_every_series_through_one_read_only_connection(collected: Collected) -> None:
    database = FakeDatabase(collected.rows)
    assert reader.read_dataset_rows(database) == collected.rows
    assert database.statements[0] == sql(reader.READ_ONLY_STATEMENT) and len(database.statements) == 1 + len(reader.SERIES) + len(reader.TABLES)
    refused(reader.DatasetBuildRefused, "DATABASE_NOT_READ_ONLY", reader.read_dataset_rows, FakeDatabase(collected.rows, read_only="off"))


@pytest.mark.parametrize("table", ["btc_ohlcv", "funding_rates", "liquidations", "etf_flows"])
def test_an_in_window_row_no_series_read_refuses_the_read(collected: Collected, table: str) -> None:
    error = refused(reader.DatasetBuildRefused, "DATASET_ROWS_UNREAD", reader.read_dataset_rows, FakeDatabase(collected.rows, surplus={table: 1}))
    assert f"raw.{table}" in str(error) and not any(marker in str(error) for marker in MARKERS)


def test_instants_are_normalized_to_utc_and_a_naive_one_is_refused(collected: Collected) -> None:
    plus_two = timezone(timedelta(hours=2))
    shifted = FakeDatabase(collected.rows, convert=lambda v: v.astimezone(plus_two) if isinstance(v, datetime) else v)
    rows = reader.read_dataset_rows(shifted)
    assert rows == collected.rows and rows["liquidations"][0].observation_time.tzinfo is UTC
    naive = FakeDatabase(collected.rows, convert=lambda v: v.replace(tzinfo=None) if isinstance(v, datetime) else v)
    refused(reader.DatasetBuildRefused, "DATASET_RECORD_REFUSED", reader.read_dataset_rows, naive)
    series = reader.SERIES_BY_NAME["funding_rates"]
    row = dataclasses.asdict(collected.rows["funding_rates"][0])
    refused(reader.DatasetBuildRefused, "DATASET_RECORD_REFUSED", reader.owner_record, series, {**row, "extra": 1})


# --- the public index and the commits --------------------------------------------------------------


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True).stdout.strip()


def git_store(world: Collected) -> run.EvidenceStore:
    shutil.rmtree(world.root / ".git")
    git(world.root, "init", "-q")
    git(world.root, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "add", "-A")
    git(world.root, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "evidence")
    return store_of(world)


def test_the_index_is_value_free_and_binds_the_private_commit(world: Collected) -> None:
    built(world)
    store = git_store(world)
    stored = build.load_dataset(store)
    commit = build.private_commit(store)
    data = build.dataset_index_bytes(stored, private_commit=commit)
    index = json.loads(data)
    assert index["private_commit"] == commit == git(world.root, "rev-parse", "HEAD")
    assert index["build_record_sha256"] == build.sha256_hex(stored.record_bytes)
    assert index["evidence"]["withheld_liquidation_hours"] == [DISAGREEING_HOUR.isoformat()]
    assert {name: entry["sha256"] for name, entry in index["manifests"].items()} == {
        name: build.sha256_hex(manifest) for name, manifest in stored.manifests.items()
    }
    text = data.decode()
    assert not any(marker in text for marker in MARKERS)
    for forbidden in ('"record_count"', '"records"', '"status_counts"', '"valued_day_count"', '"complete_day_count"', '"rows"'):
        assert forbidden not in text, forbidden
    coverage = index["coverage"]["venues"]["venue_bitfinex"]
    assert coverage["missing_slot_count"] == 1 and coverage["series"][0]["gaps"]["spans"][0]["first_missing"] == utc(2020, 2, 1, 7).isoformat()


def test_the_private_commit_must_hold_the_dataset_as_stored(world: Collected) -> None:
    store = git_store(world)
    built(world)
    refused(build.DatasetBuildRefused, "PRIVATE_COMMIT_REFUSED", build.private_commit, store)
    git(world.root, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "add", "-A")
    git(world.root, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "dataset")
    assert build.private_commit(store) == git(world.root, "rev-parse", "HEAD")
    (world.root / build.DATASET_LAYOUT / "stray").write_bytes(b"x")
    refused(build.DatasetBuildRefused, "PRIVATE_COMMIT_REFUSED", build.private_commit, store)


def test_the_build_names_a_clean_code_commit(tmp_path: Path) -> None:
    repository = tmp_path / "public"
    repository.mkdir()
    git(repository, "init", "-q")
    (repository / "a.py").write_text("x = 1\n")
    git(repository, "add", "a.py")
    git(repository, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "code")
    assert build.code_commit(repository) == git(repository, "rev-parse", "HEAD")
    (repository / "untracked.txt").write_text("scratch")  # an untracked file names no code
    assert build.code_commit(repository) == git(repository, "rev-parse", "HEAD")
    (repository / "a.py").write_text("x = 2\n")
    refused(build.DatasetBuildRefused, "CODE_COMMIT_REFUSED", build.code_commit, repository)


# --- the command line ------------------------------------------------------------------------------


def test_the_command_line_builds_verifies_and_refuses_value_free(world: Collected, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(build, "load_build_evidence", lambda store, units=None: _ORIGINAL_LOAD(store, units=units_of))
    lines: list[str] = []
    database = FakeDatabase(world.rows)
    args = ["--store", str(world.root)]
    assert build.main(["build", *args], connect=database.connect, commit=lambda: "e" * 40, out=lines.append) == 0
    assert any(line.startswith("dataset written:") for line in lines)
    lines.clear()
    assert build.main(["verify", *args], connect=database.connect, out=lines.append) == 0
    assert lines[-4:] == [
        "evidence_unchanged: True", "manifests_from_frozen_inputs: True", "inputs_from_database: True", "manifests_from_database: True"
    ]
    lines.clear()
    assert build.main(["build", *args], connect=database.connect, commit=lambda: "e" * 40, out=lines.append) == 1
    assert lines[-1].startswith("REFUSED DATASET_EXISTS") and not any(character.isdigit() for character in lines[-1].split(":", 1)[1])
    lines.clear()
    assert build.main(["verify", "--no-database", *args], connect=_no_connect, out=lines.append) == 0
    changed = FakeDatabase({**world.rows, "liquidations": world.rows["liquidations"][1:]})
    lines.clear()
    assert build.main(["verify", *args], connect=changed.connect, out=lines.append) == 1
    assert lines[-1].startswith("REFUSED EVIDENCE_MISMATCH")
    for line in lines:
        assert not any(marker in line for marker in MARKERS)


_ORIGINAL_LOAD = build.load_build_evidence


def _no_connect() -> Any:
    raise AssertionError("verify --no-database connected")


def test_the_dataset_modules_open_no_network_connection() -> None:
    for module in (reader, build):
        text = Path(module.__file__).read_text()
        for word in ("urlopen", "import socket", "http.client", "import requests", "import httpx", "urllib.request", "backfill_transport"):
            assert word not in text, (module.__name__, word)


def test_the_holdout_stays_closed() -> None:
    assert v1.HOLDOUT_OPENING_AUTHORIZED is False
    assert (reader.WINDOW_START, reader.WINDOW_END) == (v1.DATA_WINDOW.start, v1.DATA_WINDOW.end)
    assert reader.LAST_HOUR_START == datetime(2025, 12, 31, 23, tzinfo=UTC) and reader.LAST_DAY == date(2025, 12, 31)
