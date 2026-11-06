"""RBT-003 Part B: the resumable collection run (owner Part B rulings 9-11).

Each source is split into units (a month, a day, or one whole read). A unit is
read through the reviewed adapters with the network transport; its rows are
persisted through the existing collectors (BTC-021's ``collect_btc_derivatives``,
BTC-022's ``collect_etf_flows``) in monthly slices inside one transaction, since
one collector call is one ``INSERT``; and its files are written to the private
evidence repository (owner Part B ruling 9) under
``research_backtest_v1/rbt003/<source>/<unit>/``:

- ``retrievals.json``: every response's URL, retrieval instant, status, size and
  SHA-256, never a header or a value;
- ``summary.json``: value-free facts (counts, gaps, exclusions, exposure);
- the unit's evidence files, value-bearing ones included;
- ``PREPARED.json``, written before any row is persisted, binding the files;
- ``DONE.json``, written last over the same files, replacing it.

A unit whose ``DONE.json`` verifies is skipped, so an interrupted run resumes.
A marker verifies only when it names this run version, its own source and
unit, binds ``summary.json``, ``retrievals.json`` and its source's evidence
files (for CoinGlass, every projection its summary records, each matching
the digest and size its exposure record gives it) by SHA-256, and
records its rows persisted (or ``not_persisted``); a
marker that exists but does not verify refuses the unit for reconciliation by
hand, never a silent re-read (review B4). Before a unit is persisted its
files and ``PREPARED.json`` (binding them) are written. For a source that
persists, no marker can prove that a saved read was not committed, so a saved
read is never replaced by a fresh one: a persisting run resumes a prepared
unit, or one completed with ``not_persisted``, from that read, so its rows
keep their retrieval instants and the collectors' insert-or-ignore
re-persists nothing already committed; a ``--no-persist`` run refuses a
prepared unit; and a unit whose directory exists, empty or not, under no
marker the run resumes refuses for reconciliation by hand, so only a unit
without a directory is read afresh (reviews B3, BR1 and BR3). Progress lines are value-free, and a refusal prints
its code and its message with every digit masked (RBT-002's metadata-only
discipline). Spans follow RBT-002's acquisition plan: from the source's depth
or the window start to 2025-12-31.

CoinGlass (owner Part B ruling 10) runs only with ``--allow-coinglass``, which
the operator passes once the projection has passed its independent review.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import sys
import zlib
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from btc_predictor.research.us_equity_market_closures import load_closures
from btc_predictor.research_backtest import backfill_binance as binance
from btc_predictor.research_backtest import backfill_coinglass as coinglass
from btc_predictor.research_backtest import backfill_coinmetrics as coinmetrics
from btc_predictor.research_backtest import backfill_kraken as kraken
from btc_predictor.research_backtest import replay_inputs_v2 as v2
from btc_predictor.research_backtest.backfill_persistence import (
    RecordedDerivativesProvider,
    RecordedEtfFlowProvider,
    persist_derivatives,
    persist_etf_flows,
)
from btc_predictor.research_backtest.backfill_projection import ProjectedResponse
from btc_predictor.research_backtest.backfill_sources import (
    DATA_WINDOW_END,
    DATA_WINDOW_START,
    LAST_DATA_DAY,
    BackfillRefused,
    Clock,
    Fetcher,
    RetrievalLog,
    Transport,
    canonical_json_bytes,
    data_window_days,
    data_window_months,
    iso,
    midnight,
    sha256_hex,
    utc_now,
)


STORE_LAYOUT = Path("research_backtest_v1") / "rbt003"
DONE_FILE = "DONE.json"
RUN_VERSION = "RBT003_PART_B_COLLECTION_RUN_V1"
OPEN_INTEREST_FIRST_DAY = date(2020, 9, 1)  # Binance's daily metrics archive starts here (RBT-002 depth)
KRAKEN_FIRST_DAY = date(2021, 5, 27)  # the REST execution log's first execution (RBT-002 depth)
TARDIS_EXCHANGE_URL = "https://api.tardis.dev/v1/exchanges/cryptofacilities"
TARDIS_INCIDENT_KEYS = frozenset({"from", "to", "status", "details"})
ETF_FIRST_DAY = coinglass.FIRST_ETF_FLOW_DAY

_DIGIT = re.compile(r"\d")
_STORE_NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,39}")  # a source or a unit
_FILE_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,119}")  # a unit file: no separator, never "." or ".."
_SHA256 = re.compile(r"[0-9a-f]{64}")
_COUNT_NAME = re.compile(r"[a-z][a-z_]{0,63}")
PREPARED_FILE = "PREPARED.json"
MARKERS = frozenset({DONE_FILE, PREPARED_FILE})
DONE_KEYS = frozenset({"run_version", "source", "unit", "completed_at", "persisted", "files"})
PREPARED_KEYS = frozenset({"run_version", "source", "unit", "files"})  # no persistence claim (review BR1)
REQUIRED_FILES = frozenset({"retrievals.json", "summary.json"})
NOT_PERSISTED = {"not_persisted": 1}


def masked(text: str, limit: int = 400) -> str:
    """A message with every digit masked: refusals may quote a value, progress lines never do."""

    return _DIGIT.sub("#", text)[:limit]


def deterministic_gzip(data: bytes) -> bytes:
    """Gzip with no file name and a zero mtime, so equal bytes compress to equal bytes."""

    return gzip.compress(data, compresslevel=9, mtime=0)


def _month_after(month: date) -> date:
    return date(month.year + month.month // 12, month.month % 12 + 1, 1)


def _month_span(month: date) -> tuple[datetime, datetime]:
    return midnight(month), min(midnight(_month_after(month)), DATA_WINDOW_END)


# --- the evidence store ----------------------------------------------------------------------


class EvidenceStore:
    """The private evidence repository's RBT-003 directory (owner Part B ruling 9).

    The root must be a git work tree outside this public repository, so a
    value-bearing file can never land in a tracked public path. Below the
    root every directory and file the store reads or writes must be real,
    never a symbolic link, so no destination can leave the store (review B5).
    """

    def __init__(self, root: Path, *, public_repository: Path) -> None:
        root, public = Path(root).expanduser().resolve(), Path(public_repository).resolve()
        if root == public or public in root.parents or root in public.parents:
            raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", "the evidence store must lie outside the public repository")
        if not (root / ".git").exists():
            raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", "the evidence store must be a git work tree (the private repository)")
        self.root = root
        self.base = root / STORE_LAYOUT

    def unit_dir(self, source: str, unit: str) -> Path:
        for name in (source, unit):
            if not isinstance(name, str) or not _STORE_NAME.fullmatch(name):
                raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", "a source or a unit is not a plain store name")
        return self.base / source / unit

    def _real_directory(self, directory: Path, *, create: bool) -> bool:
        """Whether every directory from the root down is real (review B5); ``create`` makes the missing ones."""

        current = self.root
        for part in directory.relative_to(self.root).parts:
            current = current / part
            if current.is_symlink() or (current.exists() and not current.is_dir()):
                raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"{current.relative_to(self.root)} is not a real directory of the evidence store")
            if not current.exists():
                if not create:
                    return False
                current.mkdir()
        return True

    def done(self, source: str, unit: str) -> dict[str, Any] | None:
        """The unit's ``DONE.json`` when it and every file it binds verify; ``None`` otherwise."""

        found = self.completed(source, unit)
        return None if found is None else found[0]

    def has_done_marker(self, source: str, unit: str) -> bool:
        return self._has_marker(source, unit, DONE_FILE)

    def has_prepared_marker(self, source: str, unit: str) -> bool:
        return self._has_marker(source, unit, PREPARED_FILE)

    def _has_marker(self, source: str, unit: str, marker: str) -> bool:
        directory = self.unit_dir(source, unit)
        return self._real_directory(directory, create=False) and ((directory / marker).is_symlink() or (directory / marker).exists())

    def has_directory(self, source: str, unit: str) -> bool:
        """Whether the unit's directory exists, empty or not (reviews BR1 and BR3).

        Emptying a unit's directory never makes it new: for a source that
        persists, only a unit without a directory is read afresh.
        """

        return self._real_directory(self.unit_dir(source, unit), create=False)

    def completed(self, source: str, unit: str) -> tuple[dict[str, Any], dict[str, bytes]] | None:
        """The verified ``DONE.json`` and the files it binds (review B4); ``None`` when absent or not verifying.

        It must hold exactly the marker's keys, name this run version and its
        own source and unit, record a UTC completion instant and non-negative
        integer counts, and bind ``summary.json`` and ``retrievals.json``
        among plain file names whose SHA-256 each match.
        """

        found = self._verified(source, unit, DONE_FILE, DONE_KEYS)
        if found is None or not _utc_instant(found[0]["completed_at"]) or not _counts(found[0]["persisted"]):
            return None
        return found

    def prepared(self, source: str, unit: str) -> tuple[dict[str, Any], dict[str, bytes]] | None:
        """The verified ``PREPARED.json`` and the files it binds (review B3); ``None`` when absent or not verifying.

        It claims nothing about persistence: a prepared unit may have been
        persisted whichever run prepared it (review BR1).
        """

        return self._verified(source, unit, PREPARED_FILE, PREPARED_KEYS)

    def _verified(self, source: str, unit: str, marker_name: str, keys: frozenset[str]) -> tuple[dict[str, Any], dict[str, bytes]] | None:
        directory = self.unit_dir(source, unit)
        if not self._real_directory(directory, create=False):
            return None
        marker = directory / marker_name
        _require_not_link(marker)
        if not marker.is_file():
            return None
        try:
            record = json.loads(marker.read_bytes())
        except (UnicodeDecodeError, ValueError):
            return None
        if not isinstance(record, dict) or set(record) != keys:
            return None
        if (record["run_version"], record["source"], record["unit"]) != (RUN_VERSION, source, unit):
            return None
        bound = record["files"]
        if not isinstance(bound, dict) or not REQUIRED_FILES <= set(bound):
            return None
        files: dict[str, bytes] = {}
        for name, digest in bound.items():
            if not _FILE_NAME.fullmatch(name) or name in MARKERS or not isinstance(digest, str) or not _SHA256.fullmatch(digest):
                return None
            path = directory / name
            _require_not_link(path)
            if not path.is_file():
                return None
            data = path.read_bytes()
            if sha256_hex(data) != digest:
                return None
            files[name] = data
        return record, files

    def prepare(self, source: str, unit: str, files: Mapping[str, bytes]) -> None:
        """Write the unit's files, then ``PREPARED.json`` binding them, before anything is persisted (review B3)."""

        directory = self.unit_dir(source, unit)
        self._real_directory(directory, create=True)
        for marker in MARKERS:
            stale = directory / marker
            _require_not_link(stale)
            if stale.exists():
                stale.unlink()
        for name, data in files.items():
            if not _FILE_NAME.fullmatch(name) or name in MARKERS:
                raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"{name!r} is not a unit file name")
            _atomic_write(directory / name, data)
        record = {
            "run_version": RUN_VERSION,
            "source": source,
            "unit": unit,
            "files": {name: sha256_hex(data) for name, data in sorted(files.items())},
        }
        _atomic_write(directory / PREPARED_FILE, canonical_json_bytes(record))

    def reopen(self, source: str, unit: str) -> None:
        """Prepare a unit completed without persistence again over the same files, before it is persisted (review BR1).

        ``PREPARED.json`` is written before ``DONE.json`` is dropped, so an
        interruption leaves a marker the next run resumes.
        """

        found = self.completed(source, unit)
        if found is None or found[0]["persisted"] != NOT_PERSISTED:
            raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"{source} {unit}: only a unit completed without persistence is reopened")
        directory = self.unit_dir(source, unit)
        record = {"run_version": RUN_VERSION, "source": source, "unit": unit, "files": found[0]["files"]}
        _atomic_write(directory / PREPARED_FILE, canonical_json_bytes(record))
        (directory / DONE_FILE).unlink()

    def complete(self, source: str, unit: str, *, completed_at: datetime, persisted: Mapping[str, int]) -> dict[str, Any]:
        """Write ``DONE.json`` over the prepared files, then drop ``PREPARED.json``."""

        found = self.prepared(source, unit)
        if found is None:
            raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"{source} {unit}: only a prepared unit is completed")
        directory = self.unit_dir(source, unit)
        record = {
            "run_version": RUN_VERSION,
            "source": source,
            "unit": unit,
            "completed_at": iso(completed_at),
            "persisted": dict(sorted(persisted.items())),
            "files": found[0]["files"],
        }
        _atomic_write(directory / DONE_FILE, canonical_json_bytes(record))
        (directory / PREPARED_FILE).unlink()
        return record

    def write(self, source: str, unit: str, files: Mapping[str, bytes], *, completed_at: datetime, persisted: Mapping[str, int]) -> dict[str, Any]:
        """Prepare and complete at once: a unit with nothing to persist."""

        self.prepare(source, unit, files)
        return self.complete(source, unit, completed_at=completed_at, persisted=persisted)


def _utc_instant(value: Any) -> bool:
    try:
        instant = datetime.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return False
    return instant is not None and instant.utcoffset() == timedelta(0) and iso(instant) == value


def _counts(value: Any) -> bool:
    return isinstance(value, dict) and all(
        isinstance(name, str) and _COUNT_NAME.fullmatch(name) and type(count) is int and count >= 0 for name, count in value.items()
    )


def _require_not_link(path: Path) -> None:
    if path.is_symlink():
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"{path.name} in the evidence store is a symbolic link")


def _atomic_write(path: Path, data: bytes) -> None:
    """Write a fresh partial file, never through a symbolic link, then rename it over ``path`` (review B5)."""

    _require_not_link(path)
    partial = path.with_name(path.name + ".partial")
    if partial.is_symlink() or partial.exists():
        partial.unlink()  # a link is removed, never followed
    descriptor = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
    os.replace(partial, path)


# --- units -------------------------------------------------------------------------------------


@dataclass(frozen=True)
class UnitOutput:
    """What one unit read: evidence files, a value-free summary and its persistence."""

    files: Mapping[str, bytes]
    summary: Mapping[str, Any]
    persist: Callable[[Any, datetime], Mapping[str, int]] | None = None


@dataclass
class RunContext:
    transport: Transport
    store: EvidenceStore
    clock: Clock = utc_now
    connect: Callable[[], Any] | None = None  # a context manager yielding a write connection; None: no persistence
    coinglass_key: str | None = None
    allow_coinglass: bool = False
    out: Callable[[str], None] = print
    log: RetrievalLog = field(default_factory=RetrievalLog)
    fetch_clock: Clock | None = None  # a prepared read's retrieval instants, replayed (review B3)

    def fetcher(self) -> Fetcher:
        self.log = RetrievalLog()
        return Fetcher(self.transport, self.log, self.fetch_clock or self.clock)


@dataclass
class ReplayClock:
    """A prepared read's retrieval instants, in their order (review B3)."""

    instants: tuple[datetime, ...]
    used: int = 0

    def __call__(self) -> datetime:
        if self.used >= len(self.instants):
            raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", "the re-read makes more requests than the prepared read")
        self.used += 1
        return self.instants[self.used - 1]


def _derivative_counts(result: Any) -> Counter[str]:
    return Counter(
        {
            "funding_rates": len(result.funding_rates),
            "open_interest": len(result.open_interest),
            "futures_basis": len(result.futures_basis),
            "liquidations": len(result.liquidations),
            "perp_volume": len(result.perp_volume),
        }
    )


def persist_derivative_rows(
    connection: Any,
    ingested_at: datetime,
    recorded: RecordedDerivativesProvider,
    months: Iterable[date],
    *,
    source: str,
) -> dict[str, int]:
    """Persist in monthly slices (one collector call is one ``INSERT``); every row must land in a slice."""

    totals: Counter[str] = Counter()
    for month in months:
        start, end = _month_span(month)
        result = persist_derivatives(recorded, connection, recorded.collection_request(start, end, source=source), ingested_at=ingested_at)
        totals += _derivative_counts(result)
    expected = Counter(
        {
            "funding_rates": len(recorded.funding),
            "open_interest": len(recorded.open_interest_rows),
            "futures_basis": len(recorded.basis),
            "liquidations": len(recorded.liquidation_rows),
            "perp_volume": len(recorded.perp_volume_rows),
        }
    )
    if +totals != +expected:
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"persisted {dict(+totals)}, not every row {dict(+expected)}")
    return dict(+totals)


def _months(first: date, last: date) -> tuple[date, ...]:
    return data_window_months(first.replace(day=1), last.replace(day=1))


def _usdm_recorded(**rows: Any) -> RecordedDerivativesProvider:
    return RecordedDerivativesProvider(binance.BINANCE_EXCHANGE, binance.USDM_SYMBOL, binance.BINANCE_PROVIDER, **rows)


def funding_unit(ctx: RunContext, unit: str) -> UnitOutput:
    month = date.fromisoformat(unit + "-01")
    archive = binance.read_funding(ctx.fetcher(), month, month)
    recorded = _usdm_recorded(funding=archive.rows)
    summary = {
        "rows": len(archive.rows),
        "excluded": [{"settlement": iso(instant), "reason": reason} for instant, reason in archive.excluded],
    }
    return UnitOutput({}, summary, lambda c, at: persist_derivative_rows(c, at, recorded, [month], source=recorded.provider))


def open_interest_unit(ctx: RunContext, unit: str) -> UnitOutput:
    month = date.fromisoformat(unit + "-01")
    first = max(month, OPEN_INTEREST_FIRST_DAY)
    last = min(_month_after(month) - timedelta(days=1), LAST_DATA_DAY)
    archive = binance.read_open_interest(ctx.fetcher(), first, last)
    recorded = _usdm_recorded(open_interest_rows=archive.rows)
    summary = {"rows": len(archive.rows), "gaps": binance.gap_records(archive.gaps)}
    return UnitOutput({}, summary, lambda c, at: persist_derivative_rows(c, at, recorded, [month], source=recorded.provider))


def perp_volume_unit(ctx: RunContext, unit: str) -> UnitOutput:
    month = date.fromisoformat(unit + "-01")
    collection = binance.read_perp_volume(ctx.fetcher(), month, month)
    recorded = _usdm_recorded(perp_volume_rows=collection.rows)
    summary = {"rows": len(collection.rows), "gaps": binance.gap_records(collection.gaps)}
    return UnitOutput({}, summary, lambda c, at: persist_derivative_rows(c, at, recorded, [month], source=recorded.provider))


def basis_unit(ctx: RunContext, unit: str) -> UnitOutput:
    collection = binance.read_basis(ctx.fetcher())
    listing = collection.listing_evidence()
    recorded = RecordedDerivativesProvider(v2.FUTURES_BASIS_EXCHANGE, v2.FUTURES_BASIS_SYMBOL, binance.BINANCE_PROVIDER, basis=collection.rows)
    months = data_window_months()
    summary = {
        "rows": len(collection.rows),
        "gaps": binance.gap_records(collection.gaps),
        "unlisted_in_window": list(collection.unlisted_in_window),
        "contracts": [
            {"instrument": item.instrument, "first_kline_open_at": iso(item.first_kline_open_at), "delivery_at": iso(item.delivery_at)}
            for item in listing.contracts
        ],
        "listing_evidence_sha256": collection.listing_sha256,
    }
    files = {"futures_basis_listing_evidence.json": collection.listing_bytes}
    return UnitOutput(files, summary, lambda c, at: persist_derivative_rows(c, at, recorded, months, source=binance.BASIS_SOURCE))


def parse_tardis_incidents(data: bytes) -> tuple[tuple[datetime, datetime], ...]:
    """Every reported incident overlapping the data window: instants only, never the free-text details."""

    try:
        payload = json.loads(data)
    except (UnicodeDecodeError, ValueError):
        raise BackfillRefused("RESPONSE_SHAPE_REFUSED", "the Tardis exchange metadata is not JSON") from None
    reports = payload.get("incidentReports") if isinstance(payload, dict) else None
    if not isinstance(reports, list):
        raise BackfillRefused("RESPONSE_SHAPE_REFUSED", "the Tardis exchange metadata has no incidentReports list")
    incidents = []
    for index, report in enumerate(reports):
        if not isinstance(report, dict) or set(report) != TARDIS_INCIDENT_KEYS:
            raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"incident {index} is not exactly {sorted(TARDIS_INCIDENT_KEYS)}")
        try:
            start = datetime.fromisoformat(report["from"].replace("Z", "+00:00")).astimezone(UTC)
            end = datetime.fromisoformat(report["to"].replace("Z", "+00:00")).astimezone(UTC)
        except (AttributeError, TypeError, ValueError):
            raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"incident {index} has no ISO instants") from None
        if end <= start:
            raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"incident {index} ends before it starts")
        if start < DATA_WINDOW_END and end > DATA_WINDOW_START:
            incidents.append((max(start, DATA_WINDOW_START), min(end, DATA_WINDOW_END)))
    return tuple(sorted(incidents))


def incidents_unit(ctx: RunContext, unit: str) -> UnitOutput:
    page = ctx.fetcher().fetch(TARDIS_EXCHANGE_URL)
    incidents = parse_tardis_incidents(page.body)
    summary = {
        "incidents": [{"start": iso(start), "end": iso(end)} for start, end in incidents],
        "matches_rbt002": incidents == tuple(kraken.RBT002_RECORDED_INCIDENTS),
    }
    return UnitOutput({}, summary)


def _incidents(ctx: RunContext) -> tuple[tuple[datetime, datetime], ...]:
    record = ctx.store.done("kraken-incidents", "all")
    if record is None:
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", "collect kraken-incidents first: the liquidation days need the incident list")
    summary = json.loads((ctx.store.unit_dir("kraken-incidents", "all") / "summary.json").read_bytes())
    return tuple(
        (datetime.fromisoformat(item["start"]), datetime.fromisoformat(item["end"])) for item in summary["incidents"]
    )


def liquidation_unit(ctx: RunContext, unit: str) -> UnitOutput:
    day = date.fromisoformat(unit)
    collection = kraken.read_liquidations(ctx.fetcher(), day, day, incidents=_incidents(ctx))
    recorded = RecordedDerivativesProvider(kraken.KRAKEN_EXCHANGE, kraken.KRAKEN_SYMBOL, kraken.KRAKEN_PROVIDER, liquidation_rows=collection.rows)
    summary = {
        "rows": len(collection.rows),
        "feed_status": dict(sorted(Counter(hour.feed_status for hour in collection.hours).items())),
        "corroboration": dict(sorted(Counter(hour.corroboration for hour in collection.hours).items())),
        "disagreeing_hours": [iso(hour.hour_start) for hour in collection.hours if hour.corroboration == "DISAGREES"],
        "evidence_sha256": collection.evidence_sha256,
        "evidence_size": len(collection.evidence_bytes),
        "gzip": {"zlib_version": zlib.ZLIB_VERSION, "compresslevel": 9, "mtime": 0},
    }
    files = {"liquidation_hour_evidence.json.gz": deterministic_gzip(collection.evidence_bytes)}
    return UnitOutput(files, summary, lambda c, at: persist_derivative_rows(c, at, recorded, [day.replace(day=1)], source=recorded.provider))


def market_cap_unit(ctx: RunContext, unit: str) -> UnitOutput:
    collection = coinmetrics.read_market_caps(ctx.fetcher(), DATA_WINDOW_START.date(), LAST_DATA_DAY)
    summary = {
        "days": len(collection.rows),
        "missing_days": [day.isoformat() for day in collection.missing_days],
        "evidence_sha256": collection.evidence_sha256,
    }
    return UnitOutput({"market_cap_evidence.json": collection.evidence_bytes}, summary)


def _coinglass_allowed(ctx: RunContext) -> None:
    if not ctx.allow_coinglass:
        raise BackfillRefused(
            "PROVIDER_REQUEST_MISMATCH", "CoinGlass runs only with --allow-coinglass, after the projection's review (owner Part B ruling 10)"
        )


def _projection_file(index: int, url: Any) -> str:
    return "flow_history.projected.json" if index == 0 else f"history_{coinglass.fund_of_history_url(url)}.projected.json"


def coinglass_unit(ctx: RunContext, unit: str) -> UnitOutput:
    _coinglass_allowed(ctx)
    if not ctx.coinglass_key:
        raise BackfillRefused("PROVIDER_RESPONSE_REFUSED", "COINGLASS_API_KEY is not set")
    ctx.log = RetrievalLog()
    fetcher = coinglass.coinglass_fetcher(ctx.transport, ctx.log, api_key=ctx.coinglass_key, clock=ctx.fetch_clock or ctx.clock)
    return _coinglass_output(coinglass.read_etf_flows(fetcher, None, ETF_FIRST_DAY, LAST_DATA_DAY))


def coinglass_resume(ctx: RunContext, unit: str, files: Mapping[str, bytes]) -> UnitOutput:
    """The prepared CoinGlass unit rebuilt from its projections and their exposure records; nothing is requested (review B3).

    Each projection is rebuilt from its file and its summary's exposure record,
    which must reproduce that record exactly (digests, sizes and counts
    included), so the rows keep the prepared read's retrieval instants.
    """

    _coinglass_allowed(ctx)
    projections = []
    for name, exposure in _coinglass_projections(files):
        if name not in files:
            raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"the prepared CoinGlass unit has no {name}")
        projections.append(_projection_from_exposure(exposure, files[name]))
    return _coinglass_output(coinglass.etf_flows_from_projections(projections[0], projections[1:]))


def _coinglass_projections(files: Mapping[str, bytes]) -> list[tuple[str, dict[str, Any]]]:
    """Each projection file a CoinGlass unit's summary records, with its exposure record (reviews B3 and BR2)."""

    try:
        exposures = json.loads(files["summary.json"])["projections"]
    except (KeyError, TypeError, UnicodeDecodeError, ValueError):
        exposures = None
    if not isinstance(exposures, list) or not exposures or not all(isinstance(item, dict) for item in exposures):
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", "the CoinGlass unit's summary has no projection records")
    return [(_projection_file(index, exposure.get("url")), exposure) for index, exposure in enumerate(exposures)]


def coinglass_evidence(files: Mapping[str, bytes]) -> tuple[tuple[str, Any, Any], ...]:
    """Each projection file a CoinGlass unit's summary records, with the digest and size its exposure record gives it.

    A completed unit binds every one, and each file must match its record
    (reviews BR2 and BR4); only digests and sizes are compared, so no value is
    decoded.
    """

    return tuple((name, exposure.get("projected_sha256"), exposure.get("projected_size")) for name, exposure in _coinglass_projections(files))


def _projection_from_exposure(exposure: Mapping[str, Any], body: bytes) -> ProjectedResponse:
    try:
        rebuilt = ProjectedResponse(
            url=exposure["url"],
            retrieved_at=datetime.fromisoformat(exposure["retrieved_at"]),
            first_day=date.fromisoformat(exposure["first_day"]),
            last_day=date.fromisoformat(exposure["last_day"]),
            date_keys=tuple(exposure["date_keys"]),
            response_sha256=exposure["response_sha256"],
            response_size=exposure["response_size"],
            body=body,
            kept=exposure["kept"],
            dropped_prohibited=exposure["dropped_prohibited"],
            dropped_unrequested=exposure["dropped_unrequested"],
            dropped_holdout=exposure["dropped_holdout"],
        )
    except (KeyError, TypeError, ValueError):
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", "a prepared projection record is malformed") from None
    if rebuilt.exposure_record() != dict(exposure):
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", "a prepared projection does not reproduce its exposure record")
    return rebuilt


def _coinglass_output(read: coinglass.EtfFlowCollectionRead) -> UnitOutput:
    funds = tuple(sorted({row.fund for row in read.flows}))
    files = {_projection_file(index, item.url): item.body for index, item in enumerate(read.projections)}
    summary = {
        "rows": len(read.flows),
        "tickers_seen": list(read.tickers_seen),
        "missing_aum": [{"fund": fund, "day": day.isoformat()} for fund, day in read.missing_aum],
        "projections": [item.exposure_record() for item in read.projections],
    }
    recorded = RecordedEtfFlowProvider(coinglass.COINGLASS_PROVIDER, read.flows)

    def persist(connection: Any, ingested_at: datetime) -> dict[str, int]:
        total, missing = 0, 0
        for month in _months(ETF_FIRST_DAY, LAST_DATA_DAY):
            start = max(month, ETF_FIRST_DAY)
            end = min(_month_after(month) - timedelta(days=1), LAST_DATA_DAY)
            request = recorded.collection_request(
                funds, start, end, source=coinglass.FLOW_HISTORY_URL, market_holidays=load_closures(start, end)
            )
            result = persist_etf_flows(recorded, connection, request, ingested_at=ingested_at)
            total += len(result.flows)
            missing += sum(len(days) for days in result.missing_publication_dates.values())
        if total != len(read.flows):
            raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"persisted {total} ETF rows, not every row ({len(read.flows)})")
        return {"etf_flows": total, "missing_publication_dates": missing}

    return UnitOutput(files, summary, persist)


@dataclass(frozen=True)
class Source:
    """A source's schedule and reader, and what its completion marker must record (review B4).

    ``table`` is the raw table its rows go to (``None``: nothing is persisted);
    ``evidence`` the files every completed unit binds besides the summary and
    the retrieval log; ``described`` the further files a unit's own summary
    says it holds, each with the SHA-256 and size it records, which a
    completed unit must bind and match (reviews BR2 and BR4);
    ``extra_persisted`` further counts a persisting run records.
    """

    units: Callable[[], tuple[str, ...]]
    read: Callable[[RunContext, str], UnitOutput]
    table: str | None = None
    evidence: tuple[str, ...] = ()
    extra_persisted: frozenset[str] = frozenset()
    resume: Callable[[RunContext, str, Mapping[str, bytes]], UnitOutput] | None = None  # rebuild from prepared files
    described: Callable[[Mapping[str, bytes]], tuple[tuple[str, Any, Any], ...]] | None = None


def _month_units(first: date) -> Callable[[], tuple[str, ...]]:
    return lambda: tuple(f"{month:%Y-%m}" for month in _months(first, LAST_DATA_DAY))


SOURCES: dict[str, Source] = {
    "binance-funding": Source(_month_units(DATA_WINDOW_START.date()), funding_unit, "funding_rates"),
    "binance-open-interest": Source(_month_units(OPEN_INTEREST_FIRST_DAY), open_interest_unit, "open_interest"),
    "binance-perp-volume": Source(_month_units(DATA_WINDOW_START.date()), perp_volume_unit, "perp_volume"),
    "binance-basis": Source(lambda: ("all",), basis_unit, "futures_basis", ("futures_basis_listing_evidence.json",)),
    "kraken-incidents": Source(lambda: ("all",), incidents_unit),
    "kraken-liquidations": Source(
        lambda: tuple(day.isoformat() for day in data_window_days(KRAKEN_FIRST_DAY, LAST_DATA_DAY)),
        liquidation_unit, "liquidations", ("liquidation_hour_evidence.json.gz",),
    ),
    "coinmetrics-market-cap": Source(lambda: ("all",), market_cap_unit, None, ("market_cap_evidence.json",)),
    "coinglass-etf": Source(
        lambda: ("all",), coinglass_unit, "etf_flows", ("flow_history.projected.json",), frozenset({"missing_publication_dates"}),
        coinglass_resume, coinglass_evidence,
    ),
}


# --- the run -----------------------------------------------------------------------------------


@dataclass
class UnitReport:
    source: str
    unit: str
    status: str  # DONE, SKIPPED or REFUSED
    detail: str = ""


def _scheduled(source: str, unit: str) -> None:
    """A unit is read only when its source schedules it (review B8): the source's depth and the window bound it."""

    if source not in SOURCES:
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"unknown source {source!r}")
    if not isinstance(unit, str) or unit not in SOURCES[source].units():
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"{source} schedules no unit {unit!r}")


def _complete(ctx: RunContext, source: str, unit: str) -> bool:
    """Whether the unit is complete for this run, so it is skipped (review B4).

    A marker that exists but does not verify, lacks its source's evidence, or
    does not record its summary's rows persisted refuses: the unit may already
    be persisted, so only the operator reconciles it. A unit collected with
    ``--no-persist`` is resumed from its saved read by a persisting run
    (review BR1).
    """

    found = ctx.store.completed(source, unit)
    if found is None:
        if ctx.store.has_done_marker(source, unit):
            raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"{source} {unit}: its DONE.json does not verify; reconcile the unit by hand")
        return False
    record, files = found
    spec, persisted = SOURCES[source], record["persisted"]
    described = () if spec.described is None else spec.described(files)
    if not set(spec.evidence) <= set(files) or not {name for name, _, _ in described} <= set(files):
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"{source} {unit}: its DONE.json does not bind the source's evidence")
    if any(type(size) is not int or (sha256_hex(files[name]), len(files[name])) != (digest, size) for name, digest, size in described):
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"{source} {unit}: a file does not match the record its summary keeps of it")
    if spec.table is None:
        if persisted != {}:
            raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"{source} {unit}: its DONE.json records rows the source never persists")
        return True
    if persisted == NOT_PERSISTED:
        return ctx.connect is None
    try:
        summary = json.loads(files["summary.json"])
    except (UnicodeDecodeError, ValueError):
        summary = None
    rows = summary.get("rows") if isinstance(summary, dict) else None
    if type(rows) is not int or not set(persisted) <= {spec.table, *spec.extra_persisted} or persisted.get(spec.table, 0) != rows:
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"{source} {unit}: its DONE.json does not record the summary's rows persisted")
    return True


def _unit_files(output: UnitOutput, retrievals: bytes) -> dict[str, bytes]:
    files = dict(output.files)
    files["summary.json"] = canonical_json_bytes(dict(output.summary))
    files["retrievals.json"] = retrievals
    return files


def _retrieval_instants(data: bytes) -> tuple[datetime, ...]:
    try:
        records = json.loads(data)
        instants = tuple(item["retrieved_at"] for item in records)
    except (KeyError, TypeError, UnicodeDecodeError, ValueError):
        instants = None
    if instants is None or not all(_utc_instant(item) for item in instants):
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", "the prepared retrieval log is malformed")
    return tuple(datetime.fromisoformat(item) for item in instants)


def _resume(ctx: RunContext, source: str, unit: str, saved: Mapping[str, bytes]) -> UnitOutput:
    """The unit's saved read reproduced (review B3): any difference refuses for reconciliation by hand.

    CoinGlass rebuilds its rows from the saved projections; every other source
    reads again with the saved retrieval instants replayed and must reproduce
    the saved files byte for byte. Either way the rows are the saved read's.
    """

    spec = SOURCES[source]
    if spec.resume is not None:
        output = spec.resume(ctx, unit, saved)
        files = _unit_files(output, saved["retrievals.json"])
    else:
        clock = ReplayClock(_retrieval_instants(saved["retrievals.json"]))
        ctx.fetch_clock = clock
        try:
            output = spec.read(ctx, unit)
        finally:
            ctx.fetch_clock = None
        files = _unit_files(output, canonical_json_bytes(ctx.log.as_records()))
        if clock.used != len(clock.instants):
            files = {}
    if files != dict(saved):
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"{source} {unit}: the re-read differs from the saved read; reconcile the unit by hand")
    return output


def _read_or_resume(ctx: RunContext, source: str, unit: str) -> tuple[UnitOutput, dict[str, bytes]]:
    """Read the unit and prepare it, or resume its saved read (reviews B3 and BR1).

    A unit's files and ``PREPARED.json`` are written before anything is
    persisted, so a run interrupted after its commit leaves its read behind,
    and the rows it committed carry that read's retrieval instants (an ETF
    row's key includes ``available_at``). For a source that persists, no
    marker can prove that a saved read was not committed, so a saved read is
    never replaced by a fresh one: a persisting run resumes a prepared unit,
    whichever run prepared it, or a unit completed with ``not_persisted``,
    from its saved read, so the collectors' insert-or-ignore adds nothing
    already committed; a ``--no-persist`` run refuses a prepared unit; and a
    unit whose directory exists, empty or not, under no marker it resumes
    refuses for reconciliation by hand (an interruption before the unit's
    first file leaves an empty directory, and nothing persisted). Only a unit
    without a directory is read afresh (review BR3). A source that persists
    nothing is always read afresh.
    """

    spec = SOURCES[source]
    found = ctx.store.prepared(source, unit)
    if found is None and ctx.store.has_prepared_marker(source, unit):
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"{source} {unit}: its PREPARED.json does not verify; reconcile the unit by hand")
    if spec.table is not None:
        if found is not None:
            if ctx.connect is None:
                raise BackfillRefused(
                    "PROVIDER_REQUEST_MISMATCH", f"{source} {unit}: a prepared unit may be persisted, so only a persisting run completes it"
                )
            return _resume(ctx, source, unit, found[1]), found[1]
        done = ctx.store.completed(source, unit)
        if done is not None and done[0]["persisted"] == NOT_PERSISTED and ctx.connect is not None:
            output = _resume(ctx, source, unit, done[1])
            ctx.store.reopen(source, unit)
            return output, done[1]
        if done is not None or ctx.store.has_directory(source, unit):
            raise BackfillRefused(
                "PROVIDER_REQUEST_MISMATCH", f"{source} {unit}: its directory exists under no marker this run resumes; reconcile the unit by hand"
            )
    output = spec.read(ctx, unit)
    files = _unit_files(output, canonical_json_bytes(ctx.log.as_records()))
    ctx.store.prepare(source, unit, files)
    return output, files


def run_unit(ctx: RunContext, source: str, unit: str) -> UnitReport:
    try:
        _scheduled(source, unit)  # before the store or the transport is touched
        complete = _complete(ctx, source, unit)
    except BackfillRefused as refused:
        return UnitReport(source, str(unit), "REFUSED", f"{refused.reason_code}: {masked(str(refused))}")
    if complete:
        return UnitReport(source, unit, "SKIPPED")
    try:
        output, files = _read_or_resume(ctx, source, unit)
        persisted: Mapping[str, int] = {}
        if output.persist is not None and ctx.connect is not None:
            with ctx.connect() as connection:
                persisted = output.persist(connection, ctx.clock())
        elif output.persist is not None:
            persisted = NOT_PERSISTED
        ctx.store.complete(source, unit, completed_at=ctx.clock(), persisted=persisted)
    except BackfillRefused as refused:
        return UnitReport(source, unit, "REFUSED", f"{refused.reason_code}: {masked(str(refused))}")
    retrievals = json.loads(files["retrievals.json"])
    statuses = Counter(item["status"] for item in retrievals)
    detail = f"{len(retrievals)} requests {dict(statuses)}, persisted {dict(persisted)}"
    return UnitReport(source, unit, "DONE", detail)


def run(ctx: RunContext, sources: Sequence[str], *, limit: int | None = None, stop_on_refusal: bool = True) -> list[UnitReport]:
    reports: list[UnitReport] = []
    attempted = 0
    for source in sources:
        if source not in SOURCES:
            raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"unknown source {source!r}")
        for unit in SOURCES[source].units():
            if limit is not None and attempted >= limit:
                return reports
            report = run_unit(ctx, source, unit)
            reports.append(report)
            if report.status != "SKIPPED":
                attempted += 1
                ctx.out(f"{report.status:8} {source} {unit} {report.detail}")
            if report.status == "REFUSED" and stop_on_refusal:
                return reports
    return reports


def _write_engine_connect() -> Callable[[], Any]:
    from sqlalchemy import create_engine

    from btc_predictor.research_backtest.database import database_url_from_environment

    engine = create_engine(database_url_from_environment(), hide_parameters=True)
    return engine.begin


def main(argv: Sequence[str] | None = None) -> int:
    from btc_predictor.research_backtest.backfill_transport import UrllibTransport

    parser = argparse.ArgumentParser(prog="backfill_run", description=__doc__.splitlines()[0])
    parser.add_argument("sources", nargs="+", choices=sorted(SOURCES))
    parser.add_argument("--store", default="~/backtest_evidence", help="the private evidence repository (ruling 9)")
    parser.add_argument("--limit", type=int, default=None, help="stop after this many attempted units")
    parser.add_argument("--no-persist", action="store_true", help="write evidence only, persist nothing")
    parser.add_argument("--allow-coinglass", action="store_true", help="only after the projection's review (ruling 10)")
    parser.add_argument("--keep-going", action="store_true", help="continue past a refused unit")
    args = parser.parse_args(argv)
    public = Path(__file__).resolve().parents[2]
    ctx = RunContext(
        transport=UrllibTransport(),
        store=EvidenceStore(Path(args.store), public_repository=public),
        connect=None if args.no_persist else _write_engine_connect(),
        coinglass_key=os.environ.get("COINGLASS_API_KEY") if "coinglass-etf" in args.sources else None,
        allow_coinglass=args.allow_coinglass,
    )
    reports = run(ctx, args.sources, limit=args.limit, stop_on_refusal=not args.keep_going)
    counts = Counter(report.status for report in reports)
    print(f"units: {dict(counts)}")
    return 1 if counts.get("REFUSED") else 0


if __name__ == "__main__":
    sys.exit(main())
