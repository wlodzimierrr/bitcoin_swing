"""RBT-003 Part B: the replay dataset build (``python -m btc_predictor.research_backtest.dataset_build``).

RBT-003's acceptance criteria require two things. The build produces the
frozen per-venue and shared-input replay datasets through the RBT-001 builder
(extended by RBT-001A), with their manifests under
``backtest_evidence/research_backtest_v1/``. And re-running the build from the
database reproduces identical manifests. Owner Part B ruling 9 puts every
value-bearing file in the private evidence repository; this public repository
keeps a value-free index.

``build``:

1. Reads the raw rows through the window-bounded reader
   (:mod:`dataset_reader`) in one read-only, repeatable-read transaction.
2. Loads the evidence the V2 builder needs from the private repository's
   completed collection units, each checked as the collection run checks it:
   the basis listing, the market-cap file, and every Kraken day's hour
   evidence.
3. Checks that each collected series holds exactly the rows its units record
   persisted, and that each venue's rows hold every hour its re-request
   returned and none it left missing (review D2).
4. Withholds from the V2 builder each Kraken hour whose total disagrees with
   Kraken's hourly series, with its rows (owner Part B ruling 16, amending
   RBT-001A ruling 2 for this build). Its day is then incomplete, as an
   unavailable hour already makes it. The frozen inputs keep every row as
   read.
5. Builds the V1 shared snapshot (with ``US_EQUITY_MARKET_CLOSURE_TABLE_V1``),
   the three venue datasets and the V2 extended snapshot.
6. Writes ``research_backtest_v1/datasets/rbt003_v1/`` in the private
   repository:
   - ``inputs/<series>.json.gz``: each series' rows as read, the frozen
     inputs;
   - ``manifests/<name>.json.gz``: each builder's canonical manifest bytes;
   - ``BUILD.json``, written last, binding every file by the SHA-256 of its
     uncompressed and its gzip bytes, with the code commit, the reader's
     series and the evidence units.

The re-requested missing hours (owner Part B ruling 15) must be collected
first.

``verify`` rebuilds in a fresh process twice: from the database (identical
input files and manifests) and from the frozen input files alone (identical
manifests).

``index`` writes the value-free index into this repository once the private
repository has committed the dataset: every file ``BUILD.json`` binds, and
``BUILD.json``, in the commit with exactly the stored bytes (review D3). The
index holds:

- digests and sizes;
- versions, the code commit and the private commit;
- per family, the first and last observation and the gap census.

It holds no record value, no record count and no liquidation or ETF activity.

Output is value-free: series names, file names, digests and yes/no answers.
Nothing outside the data window is read, and the holdout stays NOT COLLECTED.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import re
import subprocess
import sys
import typing
import zlib
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Context, Decimal, InvalidOperation, localcontext
from pathlib import Path
from typing import Any

from btc_predictor.research import us_equity_market_closures as closures
from btc_predictor.research_backtest import backfill_kraken as kraken
from btc_predictor.research_backtest import backfill_ohlcv as ohlcv
from btc_predictor.research_backtest import backfill_run as run
from btc_predictor.research_backtest import replay_inputs as v1
from btc_predictor.research_backtest import replay_inputs_v2 as v2
from btc_predictor.research_backtest.backfill_sources import BACKFILL_TICKET, BackfillRefused, hours_of, iso, sha256_hex
from btc_predictor.research_backtest.dataset_reader import (
    READER_VERSION,
    SERIES,
    SERIES_BY_NAME,
    DatasetBuildRefused,
    DatasetRows,
    DatasetSeries,
    read_dataset_rows,
)

BUILD_VERSION = "RBT003_REPLAY_DATASET_BUILD_V1"
INPUT_FILE_VERSION = "RBT003_REPLAY_DATASET_INPUT_FILE_V1"
INDEX_VERSION = "RBT003_REPLAY_DATASET_INDEX_V1"
DATASET_LAYOUT = Path("research_backtest_v1") / "datasets" / "rbt003_v1"
BUILD_FILE = "BUILD.json"
INDEX_PATH = Path("backtest_evidence") / "research_backtest_v1" / "rbt003_replay_dataset_index_v1.json"
PRIVATE_REPOSITORY = "wlodzimierrr/backtest_evidence"
PUBLIC_REPOSITORY = Path(__file__).resolve().parents[2]
BUILD_KEYS = frozenset(
    {"build_version", "ticket", "evidence_class", "code_commit", "window", "reader", "gzip", "evidence", "inputs", "manifests"}
)
FILE_ENTRY_KEYS = frozenset({"file", "sha256", "size", "gzip_sha256", "gzip_size"})

# the collection sources whose completed units the build reads, and the series each persisted
SERIES_SOURCES = {
    "funding_rates": "binance-funding",
    "open_interest": "binance-open-interest",
    "perp_volume": "binance-perp-volume",
    "futures_basis": "binance-basis",
    "liquidations": "kraken-liquidations",
    "etf_flows": "coinglass-etf",
}
MARKET_CAP_SOURCE = "coinmetrics-market-cap"
MISSING_HOURS_SOURCE = "ohlcv-missing-hours"  # owner Part B ruling 15: collected before the build
EVIDENCE_SOURCES = (*SERIES_SOURCES.values(), MARKET_CAP_SOURCE, MISSING_HOURS_SOURCE)
HOUR_EVIDENCE_FILE = "liquidation_hour_evidence.json.gz"
LISTING_FILE = "futures_basis_listing_evidence.json"
MARKET_CAP_FILE = "market_cap_evidence.json"

_DECODING_CONTEXT = Context(traps=[InvalidOperation])  # a numeral decodes exactly or refuses, whatever the caller's context
# review D4: no file is expanded past the size its record declares, and no declared size past this bound; no frozen or
# evidence file approaches it (the dry build's largest, a manifest, was 76 MB)
MAX_FILE_SIZE = 1 << 30
# the canonical decimal's shape (positional, no exponent), checked before any Decimal is built, so a numeral
# such as 1e999999999999999999 is refused instead of being spelled out digit by digit
_CANONICAL_NUMERAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?")


# --- the frozen input files ----------------------------------------------------------------------

_INSTANT, _DATE, _NUMBER, _OPTIONAL_NUMBER, _TEXT = "instant", "date", "number", "optional number", "text"


def _field_kinds(record: type) -> dict[str, str]:
    kinds = {}
    for name, hint in typing.get_type_hints(record).items():
        if hint is datetime:
            kinds[name] = _INSTANT
        elif hint is date:
            kinds[name] = _DATE
        elif hint is Decimal:
            kinds[name] = _NUMBER
        elif hint == (Decimal | None):
            kinds[name] = _OPTIONAL_NUMBER
        elif hint is str:
            kinds[name] = _TEXT
        else:  # unreachable: the owner records hold only these
            raise TypeError(f"{record.__name__}.{name} has no frozen form")
    return kinds


FIELD_KINDS = {series.name: _field_kinds(series.record) for series in SERIES}


def _encode(value: Any, kind: str, what: str) -> Any:
    if kind == _INSTANT and isinstance(value, datetime):
        return v1._iso(value)
    if kind == _DATE and type(value) is date:
        return value.isoformat()
    if kind in (_NUMBER, _OPTIONAL_NUMBER) and isinstance(value, Decimal):
        return v1.canonical_decimal(value)
    if (kind == _OPTIONAL_NUMBER and value is None) or (kind == _TEXT and type(value) is str):
        return value
    raise DatasetBuildRefused("DATASET_RECORD_REFUSED", f"{what} is not a {kind}")


def input_file_bytes(series: DatasetSeries, records: Sequence[Any]) -> bytes:
    """The canonical bytes of one series' frozen inputs: numbers by value, instants in UTC, primary-key order."""

    kinds = FIELD_KINDS[series.name]
    encoded = [
        {name: _encode(getattr(record, name), kind, f"{series.name}.{name}") for name, kind in kinds.items()}
        for record in records
    ]
    return v1.canonical_json_bytes(
        {
            "file_version": INPUT_FILE_VERSION,
            "reader_version": READER_VERSION,
            "window": v1.DATA_WINDOW.as_record(),
            "series": series.as_record(),
            "records": encoded,
        }
    )


def _decode(value: Any, kind: str, what: str) -> Any:
    refused = DatasetBuildRefused("DATASET_FILE_REFUSED", f"{what} is not a canonical {kind}")
    if kind == _OPTIONAL_NUMBER and value is None:
        return None
    if type(value) is not str:
        raise refused
    if kind == _TEXT:
        return value
    try:
        if kind == _INSTANT:
            decoded: Any = datetime.fromisoformat(value)
            canonical = decoded.utcoffset() is not None and v1._iso(decoded) == value
        elif kind == _DATE:
            decoded = date.fromisoformat(value)
            canonical = decoded.isoformat() == value
        else:
            if not _CANONICAL_NUMERAL.fullmatch(value):
                raise refused
            with localcontext(_DECODING_CONTEXT):
                decoded = Decimal(value)
            canonical = decoded.is_finite() and v1.canonical_decimal(decoded) == value
    except (ValueError, ArithmeticError, v1.ReplayInputRefused):
        raise refused from None
    if not canonical:
        raise refused
    return decoded


def parse_input_file(series: DatasetSeries, data: bytes) -> tuple[Any, ...]:
    """One series' frozen inputs as owner records; refused unless ``data`` is exactly the canonical file."""

    try:
        payload = json.loads(data)
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise DatasetBuildRefused("DATASET_FILE_REFUSED", f"{series.name}: the input file is not JSON") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
        raise DatasetBuildRefused("DATASET_FILE_REFUSED", f"{series.name}: the input file has no record list")
    kinds = FIELD_KINDS[series.name]
    records = []
    for index, item in enumerate(payload["records"]):
        if not isinstance(item, dict) or set(item) != set(kinds):
            raise DatasetBuildRefused("DATASET_FILE_REFUSED", f"{series.name}: record {index} is not exactly the {series.record.__name__} fields")
        values = {name: _decode(item[name], kind, f"{series.name} record {index}.{name}") for name, kind in kinds.items()}
        records.append(series.record(**values))
    records_tuple = tuple(records)
    keys = [tuple(getattr(record, name) for name in series.primary_key) for record in records_tuple]
    if any(earlier >= later for earlier, later in zip(keys, keys[1:])):
        raise DatasetBuildRefused("DATASET_FILE_REFUSED", f"{series.name}: the records are not in strict primary-key order")
    if input_file_bytes(series, records_tuple) != data:
        raise DatasetBuildRefused("DATASET_FILE_REFUSED", f"{series.name}: the input file is not the canonical file of its records")
    return records_tuple


# --- the evidence from the collection units ------------------------------------------------------


@dataclass(frozen=True)
class BuildEvidence:
    """The V2 builder's evidence, read from verified completed units, and what each collected series persisted."""

    listing: v2.FuturesBasisListingEvidence
    market_cap: v2.MarketCapEvidence
    liquidation_hours: tuple[v2.LiquidationHourEvidence, ...]
    persisted: Mapping[str, int]
    record: Mapping[str, Any]
    # owner Part B ruling 15, review D2: per venue series, the hours its re-request returned and left missing
    missing_hours: Mapping[str, tuple[frozenset[datetime], frozenset[datetime]]]

    @property
    def withheld_hours(self) -> frozenset[datetime]:
        """Owner Part B ruling 16: every hour whose liquidation total disagrees with Kraken's hourly series."""

        return frozenset(hour.hour_start for hour in self.liquidation_hours if hour.corroboration == v2.CORROBORATION_DISAGREES)


def _declared_size(value: Any) -> int | None:
    """A size a record declares, if it is an integer the build will expand to (review D4)."""

    return value if type(value) is int and 0 <= value <= MAX_FILE_SIZE else None


def _gunzip(data: bytes, size: int) -> bytes | None:
    """The one gzip member ``data`` holds, if it decompresses to exactly ``size`` bytes (review D4).

    At most ``size + 1`` bytes are ever expanded, so a file that expands
    further is refused before its output is held. Trailing bytes or a second
    member refuse: the build writes one member.
    """

    decompressor = zlib.decompressobj(wbits=31)  # gzip framing, its CRC-32 and size trailer checked
    try:
        output = decompressor.decompress(data, size + 1)
    except zlib.error:
        return None
    if len(output) != size or not decompressor.eof or decompressor.unused_data:
        return None
    return output


def _no_transport(url: str, headers: Mapping[str, str]) -> Any:
    raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", "the dataset build makes no request")


def _no_connection() -> Any:
    raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", "the dataset build writes no row")


def _summary(files: Mapping[str, bytes], what: str) -> dict[str, Any]:
    try:
        summary = json.loads(files["summary.json"])
    except (KeyError, UnicodeDecodeError, ValueError):
        summary = None
    if not isinstance(summary, dict):
        raise DatasetBuildRefused("EVIDENCE_MISMATCH", f"{what}: its summary is not a JSON object")
    return summary


def _missing_hours_evidence(unit: str, files: Mapping[str, bytes]) -> tuple[str, frozenset[datetime], frozenset[datetime]]:
    """One re-request unit's venue series and the hours it returned and left missing (review D2).

    Its summary must list exactly the venue's scheduled hours as requested,
    split into the hours returned (one row each) and the hours still missing.
    """

    what = f"{MISSING_HOURS_SOURCE} {unit}"
    spec = ohlcv.MISSING_HOURS_VENUES.get(unit)
    summary = _summary(files, what)
    if spec is None:
        raise DatasetBuildRefused("EVIDENCE_MISMATCH", f"{what}: no missing hours are scheduled for it")
    scheduled = {iso(hour): hour for hour in spec.hours()}
    returned, missing = summary.get("returned_hours"), summary.get("still_missing_hours")
    if (
        summary.get("venue") != spec.venue.venue_id
        or summary.get("requested_hours") != list(scheduled)
        or not isinstance(returned, list)
        or not isinstance(missing, list)
        or not all(type(hour) is str for hour in (*returned, *missing))
        or sorted(returned + missing) != list(scheduled)
        or summary.get("rows") != len(returned)
    ):
        raise DatasetBuildRefused("EVIDENCE_MISMATCH", f"{what}: its summary does not split the scheduled hours into returned and missing")
    return (
        venue_series_name(spec.venue),
        frozenset(scheduled[hour] for hour in returned),
        frozenset(scheduled[hour] for hour in missing),
    )


def load_build_evidence(store: run.EvidenceStore, *, units: Callable[[str], Sequence[str]] | None = None) -> BuildEvidence:
    """Every unit the build depends on, complete as the collection run judges it (reviews B4, BR2, BR4, BR6, BR7).

    A unit must be completed and persisted: its ``DONE.json`` verifies, binds
    its source's evidence and records its summary's rows persisted.
    ``units`` names each source's units; by default, every unit the
    collection schedules.
    """

    scheduled = units or (lambda source: run.SOURCES[source].units())
    checker = run.RunContext(transport=_no_transport, store=store, connect=_no_connection, out=lambda line: None)
    completed: dict[str, list[tuple[str, dict[str, Any], dict[str, bytes]]]] = {}
    for source in EVIDENCE_SOURCES:
        names = tuple(scheduled(source))
        if not names:
            raise DatasetBuildRefused("EVIDENCE_UNIT_REFUSED", f"{source} schedules no unit")
        for unit in names:
            if not run._complete(checker, source, unit):
                raise DatasetBuildRefused("EVIDENCE_UNIT_REFUSED", f"{source} {unit} is not a completed, persisted unit")
            found = store.completed(source, unit)
            if found is None:  # unreachable: _complete verified it
                raise DatasetBuildRefused("EVIDENCE_UNIT_REFUSED", f"{source} {unit} does not verify")
            completed.setdefault(source, []).append((unit, found[0], found[1]))

    persisted = {
        name: sum(marker["persisted"].get(SERIES_BY_NAME[name].table.name, 0) for _, marker, _ in completed[source])
        for name, source in SERIES_SOURCES.items()
    }
    (_, _, basis_files), = completed["binance-basis"]
    listing = v2.parse_futures_basis_listing_evidence(
        basis_files[LISTING_FILE], expected_sha256=_summary(basis_files, "binance-basis").get("listing_evidence_sha256")
    )
    (_, _, cap_files), = completed[MARKET_CAP_SOURCE]
    market_cap = v2.parse_market_cap_evidence(
        cap_files[MARKET_CAP_FILE], expected_sha256=_summary(cap_files, MARKET_CAP_SOURCE).get("evidence_sha256")
    )
    hours: list[v2.LiquidationHourEvidence] = []
    for day, _, files in completed["kraken-liquidations"]:
        summary = _summary(files, f"kraken-liquidations {day}")
        size = _declared_size(summary.get("evidence_size"))
        data = None if size is None else _gunzip(files[HOUR_EVIDENCE_FILE], size)
        if data is None:
            raise DatasetBuildRefused("EVIDENCE_MISMATCH", f"kraken-liquidations {day}: its hour evidence is not one gzip member of its recorded size")
        day_hours = kraken.parse_liquidation_hour_evidence(data, expected_sha256=summary.get("evidence_sha256"))
        if tuple(hour.hour_start for hour in day_hours) != hours_of(date.fromisoformat(day)):
            raise DatasetBuildRefused("EVIDENCE_MISMATCH", f"kraken-liquidations {day}: its hour evidence is not that day's 24 hours")
        hours.extend(day_hours)

    def bound(items: list[tuple[str, dict[str, Any], dict[str, bytes]]]) -> dict[str, Any]:
        markers = [[unit, sha256_hex(v1.canonical_json_bytes(marker))] for unit, marker, _ in items]
        return {"unit_count": len(items), "first_unit": items[0][0], "last_unit": items[-1][0], "done_sha256": sha256_hex(v1.canonical_json_bytes(markers))}

    missing_hours = {}
    for unit, _, files in completed[MISSING_HOURS_SOURCE]:
        name, returned, missing = _missing_hours_evidence(unit, files)
        if name in missing_hours:
            raise DatasetBuildRefused("EVIDENCE_MISMATCH", f"{MISSING_HOURS_SOURCE} {unit}: a second unit for {name}")
        missing_hours[name] = (returned, missing)

    withheld = sorted(hour.hour_start for hour in hours if hour.corroboration == v2.CORROBORATION_DISAGREES)
    record = {
        "units": {source: bound(completed[source]) for source in EVIDENCE_SOURCES},
        "withheld_liquidation_hours": [v1._iso(hour) for hour in withheld],  # owner Part B ruling 16
        "futures_basis_listing_sha256": sha256_hex(basis_files[LISTING_FILE]),
        "market_cap_evidence_sha256": sha256_hex(cap_files[MARKET_CAP_FILE]),
        "still_missing_hours": {
            unit: _summary(files, f"{MISSING_HOURS_SOURCE} {unit}").get("still_missing_hours") for unit, _, files in completed[MISSING_HOURS_SOURCE]
        },
    }
    return BuildEvidence(listing, market_cap, tuple(hours), persisted, record, missing_hours)


def require_persisted_rows(rows: DatasetRows, evidence: BuildEvidence) -> None:
    """Each collected series holds exactly the rows its completed units record persisted.

    Each venue's rows hold every hour its re-request returned and persisted,
    and none it left missing (owner Part B ruling 15, review D2).
    """

    for name in SERIES_SOURCES:
        if len(rows[name]) != evidence.persisted[name]:
            raise DatasetBuildRefused("EVIDENCE_MISMATCH", f"{name}: the rows read are not the rows its units record persisted")
    for name, (returned, missing) in evidence.missing_hours.items():
        instant = SERIES_BY_NAME[name].instant_column.name
        held = {getattr(bar, instant) for bar in rows[name]}
        if not returned <= held:
            raise DatasetBuildRefused("EVIDENCE_MISMATCH", f"{name}: an hour its re-request returned and persisted is not in the rows read")
        if not held.isdisjoint(missing):
            raise DatasetBuildRefused("EVIDENCE_MISMATCH", f"{name}: an hour its re-request left missing is in the rows read")


# --- the build -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class ReplayDatasets:
    shared: v1.SharedReplaySnapshot
    venues: tuple[v1.VenueReplayDataset, ...]
    extended: v2.ExtendedReplaySnapshot

    def manifests(self) -> dict[str, bytes]:
        """Each builder's canonical manifest bytes, by file name."""

        return {
            "shared_snapshot": self.shared.manifest_bytes,
            **{f"venue_{dataset.venue.venue_id.lower()}": dataset.manifest_bytes for dataset in self.venues},
            "extended_snapshot": self.extended.manifest_bytes,
        }


def venue_series_name(venue: v1.ReplayVenue) -> str:
    return f"ohlcv_1h_{venue.venue_id.lower()}"


def build_replay_datasets(rows: DatasetRows, evidence: BuildEvidence) -> ReplayDatasets:
    """The V1 shared snapshot, the three venue datasets and the V2 extended snapshot, through the reviewed builders.

    Each Kraken hour whose total disagrees with the series is withheld from the
    V2 builder with its rows (owner Part B ruling 16), so its day is incomplete.
    """

    require_persisted_rows(rows, evidence)
    withheld = evidence.withheld_hours
    shared = v1.build_shared_replay_snapshot(
        window=v1.DATA_WINDOW,
        volume_bars=rows[venue_series_name(v1.SHARED_VOLUME_VENUE)],
        etf_flows=rows["etf_flows"],
        etf_source_publication_times=(),  # CoinGlass publishes no publication time: the T+2 00:00 floor applies
        funding_rates=rows["funding_rates"],
        open_interest=rows["open_interest"],
        perp_volumes=rows["perp_volume"],
        etf_market_holidays=closures.load_closures(closures.COVERAGE_START, closures.COVERAGE_END),
    )
    venues = tuple(
        v1.build_venue_replay_dataset(venue=venue, window=v1.DATA_WINDOW, price_bars=rows[venue_series_name(venue)], shared_snapshot=shared)
        for venue in v1.REPLAY_VENUES
    )
    extended = v2.build_extended_replay_snapshot(
        shared_snapshot=shared,
        futures_basis=rows["futures_basis"],
        futures_basis_listing=evidence.listing,
        market_cap_evidence=evidence.market_cap,
        liquidations=tuple(row for row in rows["liquidations"] if row.observation_time not in withheld),
        liquidation_hours=tuple(hour for hour in evidence.liquidation_hours if hour.hour_start not in withheld),
    )
    return ReplayDatasets(shared, venues, extended)


# --- the private dataset directory ---------------------------------------------------------------


def _file_entry(path: str, data: bytes, compressed: bytes) -> dict[str, Any]:
    return {"file": path, "sha256": sha256_hex(data), "size": len(data), "gzip_sha256": sha256_hex(compressed), "gzip_size": len(compressed)}


def build_record(
    *,
    code_commit: str,
    evidence: BuildEvidence,
    inputs: Mapping[str, bytes],
    input_records: Mapping[str, int],
    manifests: Mapping[str, bytes],
) -> dict[str, Any]:
    """``BUILD.json``: every file bound by digest, with the code commit, the reader's series and the evidence units."""

    return {
        "build_version": BUILD_VERSION,
        "ticket": BACKFILL_TICKET,
        "evidence_class": v1.RESEARCH_EVIDENCE_CLASS,
        "code_commit": code_commit,
        "window": v1.DATA_WINDOW.as_record(),
        "reader": {"version": READER_VERSION, "series": [series.as_record() for series in SERIES]},
        "gzip": {"zlib_version": zlib.ZLIB_VERSION, "compresslevel": 9, "mtime": 0},
        "evidence": dict(evidence.record),
        "inputs": {
            name: {**_file_entry(f"inputs/{name}.json.gz", data, run.deterministic_gzip(data)), "records": input_records[name]}
            for name, data in inputs.items()
        },
        "manifests": {
            name: _file_entry(f"manifests/{name}.json.gz", data, run.deterministic_gzip(data)) for name, data in manifests.items()
        },
    }


def dataset_directory(store: run.EvidenceStore) -> Path:
    return store.root / DATASET_LAYOUT


def write_dataset(
    store: run.EvidenceStore, rows: DatasetRows, datasets: ReplayDatasets, evidence: BuildEvidence, *, code_commit: str
) -> dict[str, Any]:
    """Write the frozen inputs, the manifests and, last, ``BUILD.json``; an existing dataset is never overwritten."""

    directory = dataset_directory(store)
    if directory.is_symlink() or directory.exists():
        raise DatasetBuildRefused("DATASET_EXISTS", f"{DATASET_LAYOUT} exists; verify it, or remove an incomplete one by hand")
    inputs = {series.name: input_file_bytes(series, rows[series.name]) for series in SERIES}
    manifests = datasets.manifests()
    record = build_record(
        code_commit=code_commit,
        evidence=evidence,
        inputs=inputs,
        input_records={name: len(records) for name, records in rows.items()},
        manifests=manifests,
    )
    for part in ("inputs", "manifests"):
        store._real_directory(directory / part, create=True)  # every directory real, never a link (review B5)
    for part, files in (("inputs", inputs), ("manifests", manifests)):
        for name, data in files.items():
            compressed = run.deterministic_gzip(data)
            if sha256_hex(compressed) != record[part][name]["gzip_sha256"]:  # unreachable: gzip is deterministic
                raise DatasetBuildRefused("DATASET_FILE_REFUSED", f"{part}/{name}: gzip is not deterministic here")
            run._atomic_write(directory / part / f"{name}.json.gz", compressed)
    run._atomic_write(directory / BUILD_FILE, v1.canonical_json_bytes(record))
    return record


@dataclass(frozen=True)
class StoredDataset:
    record: dict[str, Any]
    record_bytes: bytes
    inputs: dict[str, bytes]
    manifests: dict[str, bytes]


def _read_real_file(directory: Path, relative: str) -> bytes:
    path = directory / relative
    for part in (directory, *(directory / parent for parent in Path(relative).parents if str(parent) != ".")):
        if part.is_symlink():
            raise DatasetBuildRefused("DATASET_FILE_REFUSED", f"{relative}: a directory on its path is a symbolic link")
    if path.is_symlink() or not path.is_file():
        raise DatasetBuildRefused("DATASET_FILE_REFUSED", f"{relative} is not a plain file of the dataset")
    return path.read_bytes()


_DIGEST = re.compile(r"[0-9a-f]{64}")
_COMMIT = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
_ZLIB_VERSION = re.compile(r"[0-9]{1,2}(?:\.[0-9]{1,2}){1,3}(?:[.-][a-z][a-z-]{0,15})?")  # 1.3.2, 1.2.13, 1.3.0.1-motley, 1.3.0.zlib-ng
_UNIT_BOUND_KEYS = frozenset({"unit_count", "first_unit", "last_unit", "done_sha256"})
_EVIDENCE_KEYS = frozenset(
    {"units", "withheld_liquidation_hours", "futures_basis_listing_sha256", "market_cap_evidence_sha256", "still_missing_hours"}
)


def _is_digest(value: Any) -> bool:
    return type(value) is str and _DIGEST.fullmatch(value) is not None


def _is_count(value: Any) -> bool:
    return type(value) is int and value >= 0


def _hours(value: Any) -> tuple[datetime, ...] | None:
    """Canonical whole-hour UTC instants inside the data window, ascending and distinct (review DR1); else ``None``."""

    if type(value) is not list or not all(type(text) is str for text in value):
        return None
    hours = []
    for text in value:
        try:
            hour = datetime.fromisoformat(text)
        except ValueError:
            return None
        if hour.utcoffset() != timedelta(0) or iso(hour) != text or (hour.minute, hour.second, hour.microsecond) != (0, 0, 0):
            return None
        if not v1.DATA_WINDOW.contains(hour):
            return None
        hours.append(hour)
    return tuple(hours) if all(earlier < later for earlier, later in zip(hours, hours[1:])) else None


def _scheduled_unit(source: str, value: Any) -> bool:
    """A unit the collection schedules for ``source`` (review DR1): a unit name, never other text."""

    return type(value) is str and value in run.SOURCES[source].units()


def _scheduled_missing_hours(venue: str, value: Any) -> bool:
    """Hours among those the re-request schedules for ``venue`` (review DR1)."""

    hours = _hours(value)
    return hours is not None and set(hours) <= set(ohlcv.MISSING_HOURS_VENUES[venue].hours())


def _well_formed_evidence(evidence: Any) -> bool:
    """The evidence section as ``load_build_evidence`` writes it: scheduled unit names, counts, digests and hours.

    Every text in it is what it names (review DR1): a unit the collection
    schedules, or a canonical whole hour of the data window; the
    still-missing hours are among their venue's scheduled ones. The index
    publishes this section, so no other text may reach it.
    """

    if type(evidence) is not dict or set(evidence) != _EVIDENCE_KEYS:
        return False
    units, missing = evidence["units"], evidence["still_missing_hours"]
    return (
        type(units) is dict
        and sorted(units) == sorted(EVIDENCE_SOURCES)
        and all(
            type(bound) is dict
            and set(bound) == _UNIT_BOUND_KEYS
            and _is_count(bound["unit_count"])
            and _scheduled_unit(source, bound["first_unit"])
            and _scheduled_unit(source, bound["last_unit"])
            and _is_digest(bound["done_sha256"])
            for source, bound in units.items()
        )
        and _hours(evidence["withheld_liquidation_hours"]) is not None
        and _is_digest(evidence["futures_basis_listing_sha256"])
        and _is_digest(evidence["market_cap_evidence_sha256"])
        and type(missing) is dict
        and sorted(missing) == sorted(ohlcv.MISSING_HOURS_VENUES)
        and all(_scheduled_missing_hours(venue, hours) for venue, hours in missing.items())
    )


def _well_formed_build_record(record: dict[str, Any]) -> bool:
    """``BUILD.json``'s metadata as this build writes it (review D5); the file entries are checked with their files."""

    gzip_record = record["gzip"]
    return (
        record["build_version"] == BUILD_VERSION
        and record["ticket"] == BACKFILL_TICKET
        and record["evidence_class"] == v1.RESEARCH_EVIDENCE_CLASS
        and type(record["code_commit"]) is str
        and _COMMIT.fullmatch(record["code_commit"]) is not None
        and record["window"] == v1.DATA_WINDOW.as_record()
        and record["reader"] == {"version": READER_VERSION, "series": [series.as_record() for series in SERIES]}
        and type(gzip_record) is dict
        and set(gzip_record) == {"zlib_version", "compresslevel", "mtime"}
        and type(gzip_record["zlib_version"]) is str
        and _ZLIB_VERSION.fullmatch(gzip_record["zlib_version"]) is not None  # review DR1: a version, never other text
        and type(gzip_record["compresslevel"]) is int
        and type(gzip_record["mtime"]) is int
        and (gzip_record["compresslevel"], gzip_record["mtime"]) == (9, 0)
        and _well_formed_evidence(record["evidence"])
    )


def _well_formed_entry(entry: Any, part: str, name: str) -> bool:
    """A file entry's keys, name, gzip size and record count; its digests and sizes are checked against its file.

    The gzip size must be an integer (review DR2): a fraction such as ``N.0``
    equals the file's length, so the comparison alone would accept it.
    """

    keys = FILE_ENTRY_KEYS | ({"records"} if part == "inputs" else set())
    return (
        type(entry) is dict
        and set(entry) == keys
        and entry["file"] == f"{part}/{name}.json.gz"
        and _is_count(entry["gzip_size"])
        and (part != "inputs" or _is_count(entry["records"]))
    )


def load_dataset(store: run.EvidenceStore) -> StoredDataset:
    """The stored dataset, every file checked against ``BUILD.json`` (gzip and uncompressed digests and sizes).

    ``BUILD.json`` must be its canonical bytes, with every value of the type
    and shape the build writes; anything else, a non-finite number among it,
    refuses, never raises (review D5). Every text in its metadata must be what
    it names, a scheduled unit, a canonical hour or a version, since the index
    publishes it (review DR1).
    """

    directory = dataset_directory(store)
    store._real_directory(directory, create=False)
    record_bytes = _read_real_file(directory, BUILD_FILE)
    try:
        record = json.loads(record_bytes)
        canonical = v1.canonical_json_bytes(record)  # review D5: NaN, Infinity or 1e999 refuse here, never raise
    except (UnicodeDecodeError, ValueError, RecursionError):
        record = canonical = None
    if not isinstance(record, dict) or set(record) != BUILD_KEYS or canonical != record_bytes:
        raise DatasetBuildRefused("DATASET_FILE_REFUSED", f"{BUILD_FILE} is not the canonical build record")
    if not _well_formed_build_record(record):
        raise DatasetBuildRefused("DATASET_FILE_REFUSED", f"{BUILD_FILE} does not hold this build's metadata")
    expected = {"inputs": [series.name for series in SERIES], "manifests": ["shared_snapshot", *(f"venue_{venue.venue_id.lower()}" for venue in v1.REPLAY_VENUES), "extended_snapshot"]}
    stored: dict[str, dict[str, bytes]] = {}
    for part, names in expected.items():
        entries = record[part]
        if not isinstance(entries, dict) or sorted(entries) != sorted(names):
            raise DatasetBuildRefused("DATASET_FILE_REFUSED", f"{BUILD_FILE} does not bind exactly the {part}")
        stored[part] = {}
        for name in names:
            entry = entries[name]
            if not _well_formed_entry(entry, part, name):
                raise DatasetBuildRefused("DATASET_FILE_REFUSED", f"{BUILD_FILE}: the {part} entry {name} is malformed")
            compressed = _read_real_file(directory, entry["file"])
            if (sha256_hex(compressed), len(compressed)) != (entry["gzip_sha256"], entry["gzip_size"]):
                raise DatasetBuildRefused("DATASET_FILE_REFUSED", f"{entry['file']} does not match its gzip digest")
            size = _declared_size(entry["size"])
            data = None if size is None else _gunzip(compressed, size)  # never expanded past its declared size (review D4)
            if data is None:
                raise DatasetBuildRefused("DATASET_FILE_REFUSED", f"{entry['file']} is not one gzip member of its declared size")
            if (sha256_hex(data), len(data)) != (entry["sha256"], entry["size"]):
                raise DatasetBuildRefused("DATASET_FILE_REFUSED", f"{entry['file']} does not match its digest")
            stored[part][name] = data
    return StoredDataset(record, record_bytes, stored["inputs"], stored["manifests"])


def frozen_rows(stored: StoredDataset) -> DatasetRows:
    """The frozen inputs as owner records, each file the canonical file of its records."""

    return {series.name: parse_input_file(series, stored.inputs[series.name]) for series in SERIES}


def verify_dataset(stored: StoredDataset, evidence: BuildEvidence, database_rows: DatasetRows | None) -> dict[str, bool]:
    """Rebuild from the frozen inputs, and from the database when given, against the stored files."""

    results = {
        "evidence_unchanged": v1.canonical_json_bytes(dict(evidence.record)) == v1.canonical_json_bytes(stored.record["evidence"]),
    }
    results["manifests_from_frozen_inputs"] = build_replay_datasets(frozen_rows(stored), evidence).manifests() == stored.manifests
    if database_rows is not None:
        rebuilt = {series.name: input_file_bytes(series, database_rows[series.name]) for series in SERIES}
        results["inputs_from_database"] = rebuilt == stored.inputs
        results["manifests_from_database"] = build_replay_datasets(database_rows, evidence).manifests() == stored.manifests
    return results


# --- the value-free public index -----------------------------------------------------------------

_GAP_KEYS = ("method", "gap_count", "missing_slot_count", "not_evaluated_reason", "spans")


def _gaps(gaps: Mapping[str, Any]) -> dict[str, Any]:
    return {key: gaps.get(key) for key in _GAP_KEYS}


def _family_coverage(section: Mapping[str, Any], *, series: bool = True) -> dict[str, Any]:
    coverage = {key: section[key] for key in ("gap_count", "missing_slot_count", "gap_not_evaluated_reasons")}
    if series:
        coverage["series"] = [
            {
                "identity": item["identity"],
                "first_observation": item["first_observation"],
                "last_observation": item["last_observation"],
                "gaps": _gaps(item["gaps"]),
            }
            for item in section["series"]
        ]
    return coverage


def dataset_index_bytes(stored: StoredDataset, *, private_commit: str) -> bytes:
    """The value-free index: digests, sizes, versions, commits and the gap census; no value, no record count."""

    manifests = {name: json.loads(data) for name, data in stored.manifests.items()}
    shared, extended = manifests["shared_snapshot"], manifests["extended_snapshot"]
    hour_evidence = extended["families"][v2.LIQUIDATIONS_FAMILY]["hour_evidence"]
    record = stored.record
    index = {
        "index_version": INDEX_VERSION,
        "build_version": record["build_version"],
        "ticket": record["ticket"],
        "evidence_class": record["evidence_class"],
        "code_commit": record["code_commit"],
        "private_repository": PRIVATE_REPOSITORY,
        "private_commit": private_commit,
        "path": DATASET_LAYOUT.as_posix(),
        "build_record_sha256": sha256_hex(stored.record_bytes),
        "window": record["window"],
        "reader": record["reader"],
        "gzip": record["gzip"],
        "evidence": record["evidence"],
        "files": {
            f"{part}/{name}": {key: entry[key] for key in sorted(FILE_ENTRY_KEYS - {"file"})}
            for part in ("inputs", "manifests")
            for name, entry in record[part].items()
        },
        "manifests": {name: {"manifest_version": manifest["manifest_version"], "sha256": sha256_hex(stored.manifests[name])} for name, manifest in manifests.items()},
        "coverage": {
            "shared_snapshot": {family: _family_coverage(section) for family, section in shared["families"].items()},
            "venues": {
                name: _family_coverage(manifest["price_series"]) for name, manifest in manifests.items() if name.startswith("venue_")
            },
            "extended_snapshot": {
                v2.FUTURES_BASIS_FAMILY: _family_coverage(extended["families"][v2.FUTURES_BASIS_FAMILY]),
                v2.BTC_MARKET_CAP_FAMILY: _family_coverage(extended["families"][v2.BTC_MARKET_CAP_FAMILY]),
                v2.LIQUIDATIONS_FAMILY: _family_coverage(extended["families"][v2.LIQUIDATIONS_FAMILY], series=False),
                v2.LIQUIDATION_HOUR_EVIDENCE_FAMILY: {
                    "first_hour": hour_evidence["first_hour"],
                    "last_hour": hour_evidence["last_hour"],
                    "gaps": _gaps(hour_evidence["gaps"]),
                },
            },
        },
    }
    return v1.canonical_json_bytes(index)


# --- commits -------------------------------------------------------------------------------------


def _git(repository: Path, *args: str) -> str:
    completed = subprocess.run(["git", "-C", str(repository), *args], capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise DatasetBuildRefused("CODE_COMMIT_REFUSED", f"git {args[0]} failed in {repository.name}")
    return completed.stdout.strip()


def code_commit(repository: Path = PUBLIC_REPOSITORY) -> str:
    """The public repository's commit; refused when a tracked file differs from it, so the build names its code."""

    if _git(repository, "status", "--porcelain", "--untracked-files=no"):
        raise DatasetBuildRefused("CODE_COMMIT_REFUSED", "the public repository has uncommitted changes; the build runs on a commit")
    return _git(repository, "rev-parse", "HEAD")


_BLOB_HASHES = {"sha1": hashlib.sha1, "sha256": hashlib.sha256}
_FILE_MODES = frozenset({"100644", "100755"})  # a regular file: never a link (120000) or a submodule (160000)


def _blob_id(data: bytes, object_format: str) -> str:
    """The id git gives a blob of exactly these bytes."""

    return _BLOB_HASHES[object_format](b"blob %d\0" % len(data) + data).hexdigest()


def private_commit(store: run.EvidenceStore, stored: StoredDataset) -> str:
    """The private repository's commit holding the dataset exactly as stored (review D3).

    ``BUILD.json`` and every file it binds must be in the commit, as regular
    files with exactly the stored bytes, and the commit's dataset directory
    must hold nothing else; nothing in the working tree may differ from it,
    ignored files included. Checking only ``BUILD.json`` let a commit leave
    ignored payloads out.
    """

    path = DATASET_LAYOUT.as_posix()
    directory = dataset_directory(store)
    expected = {BUILD_FILE: stored.record_bytes}
    for part in ("inputs", "manifests"):
        for entry in stored.record[part].values():
            data = _read_real_file(directory, entry["file"])
            if sha256_hex(data) != entry["gzip_sha256"]:
                raise DatasetBuildRefused("PRIVATE_COMMIT_REFUSED", f"{entry['file']} is not the file the dataset was loaded with")
            expected[entry["file"]] = data
    try:
        status = _git(store.root, "status", "--porcelain", "--untracked-files=all", "--ignored=matching", "--", path)
        object_format = _git(store.root, "rev-parse", "--show-object-format")
        commit = _git(store.root, "rev-parse", "--verify", "HEAD^{commit}")
        listing = _git(store.root, "ls-tree", "-r", "-z", "--full-tree", commit, "--", path)
    except DatasetBuildRefused:
        raise DatasetBuildRefused("PRIVATE_COMMIT_REFUSED", "the private repository does not hold the dataset in a commit") from None
    if status:
        raise DatasetBuildRefused("PRIVATE_COMMIT_REFUSED", "the dataset is not committed as stored in the private repository")
    if object_format not in _BLOB_HASHES:
        raise DatasetBuildRefused("PRIVATE_COMMIT_REFUSED", "the private repository's object format is not one the build checks")
    tree: dict[str, tuple[str, str, str]] = {}
    for item in filter(None, listing.split("\0")):
        meta, _, name = item.partition("\t")
        mode, kind, blob = meta.split(" ")
        tree[name] = (mode, kind, blob)
    wanted = {f"{path}/{name}": data for name, data in expected.items()}
    if set(tree) != set(wanted) or any(
        tree[name][0] not in _FILE_MODES or tree[name][1:] != ("blob", _blob_id(data, object_format)) for name, data in wanted.items()
    ):
        raise DatasetBuildRefused("PRIVATE_COMMIT_REFUSED", "the commit does not hold exactly the dataset's files as stored")
    return commit


# --- the command line ----------------------------------------------------------------------------


@contextlib.contextmanager
def read_only_connection() -> Iterator[Any]:
    """One read-only, repeatable-read transaction on the research database; its URL is never printed."""

    from sqlalchemy import create_engine

    from btc_predictor.research_backtest.database import database_url_from_environment

    engine = create_engine(database_url_from_environment(), hide_parameters=True)
    try:
        with engine.connect() as connection:
            connection = connection.execution_options(isolation_level="REPEATABLE READ", postgresql_readonly=True)
            with connection.begin():
                yield connection
    finally:
        engine.dispose()


def _database_rows(connect: Callable[[], Any]) -> DatasetRows:
    from sqlalchemy.exc import SQLAlchemyError

    try:
        with connect() as connection:
            return read_dataset_rows(connection)
    except SQLAlchemyError as error:  # its text may carry the host or the user: the type only
        raise DatasetBuildRefused("DATABASE_NOT_READ_ONLY", f"the database read failed ({type(error).__name__})") from None


def main(
    argv: Sequence[str] | None = None,
    *,
    connect: Callable[[], Any] = read_only_connection,
    commit: Callable[[], str] = code_commit,
    out: Callable[[str], None] = print,
) -> int:
    parser = argparse.ArgumentParser(prog="dataset_build", description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("build", "verify", "index"))
    parser.add_argument("--store", default="~/backtest_evidence", help="the private evidence repository (owner Part B ruling 9)")
    parser.add_argument("--no-database", action="store_true", help="verify: rebuild from the frozen inputs only")
    args = parser.parse_args(argv)
    try:
        store = run.EvidenceStore(Path(args.store), public_repository=PUBLIC_REPOSITORY)
        if args.command == "index":
            stored = load_dataset(store)
            commit = private_commit(store, stored)
            path = PUBLIC_REPOSITORY / INDEX_PATH
            run._atomic_write(path, dataset_index_bytes(stored, private_commit=commit))
            out(f"index written: {INDEX_PATH} (private commit {commit})")
            return 0
        commit_of_code = commit() if args.command == "build" else None
        evidence = load_build_evidence(store)
        out(f"evidence: {sum(item['unit_count'] for item in evidence.record['units'].values())} completed units verified")
        if commit_of_code is not None:
            rows = _database_rows(connect)
            out(f"read {len(rows)} series, bounded to the data window")
            datasets = build_replay_datasets(rows, evidence)
            record = write_dataset(store, rows, datasets, evidence, code_commit=commit_of_code)
            for name, entry in record["manifests"].items():
                out(f"manifest {name}: sha256 {entry['sha256']}")
            out(f"dataset written: {DATASET_LAYOUT} at code {commit_of_code}")
            return 0
        stored = load_dataset(store)
        results = verify_dataset(stored, evidence, None if args.no_database else _database_rows(connect))
        for name, passed in results.items():
            out(f"{name}: {passed}")
        return 0 if all(results.values()) else 1
    except (DatasetBuildRefused, BackfillRefused, v1.ReplayInputRefused) as refused:
        out(f"REFUSED {getattr(refused, 'reason_code', type(refused).__name__)}: {run.masked(str(refused))}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
