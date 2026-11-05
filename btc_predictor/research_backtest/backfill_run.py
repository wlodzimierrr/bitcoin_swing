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
- ``DONE.json``, written last, binding every other file by SHA-256.

A unit whose ``DONE.json`` verifies is skipped, so an interrupted run resumes;
the collectors insert-or-ignore, so a unit interrupted after persisting
re-persists nothing new. Progress lines are value-free, and a refusal prints
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

        directory = self.unit_dir(source, unit)
        if not self._real_directory(directory, create=False):
            return None
        marker = directory / DONE_FILE
        _require_not_link(marker)
        if not marker.is_file():
            return None
        record = json.loads(marker.read_bytes())
        for name, digest in record["files"].items():
            if not _FILE_NAME.fullmatch(name):
                return None
            path = directory / name
            _require_not_link(path)
            if not path.is_file() or sha256_hex(path.read_bytes()) != digest:
                return None
        return record

    def write(self, source: str, unit: str, files: Mapping[str, bytes], *, completed_at: datetime, persisted: Mapping[str, int]) -> dict[str, Any]:
        directory = self.unit_dir(source, unit)
        self._real_directory(directory, create=True)
        stale = directory / DONE_FILE
        _require_not_link(stale)
        if stale.exists():
            stale.unlink()
        for name, data in files.items():
            if not _FILE_NAME.fullmatch(name) or name == DONE_FILE:
                raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"{name!r} is not a unit file name")
            _atomic_write(directory / name, data)
        record = {
            "run_version": RUN_VERSION,
            "source": source,
            "unit": unit,
            "completed_at": iso(completed_at),
            "persisted": dict(sorted(persisted.items())),
            "files": {name: sha256_hex(data) for name, data in sorted(files.items())},
        }
        _atomic_write(directory / DONE_FILE, canonical_json_bytes(record))
        return record


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

    def fetcher(self) -> Fetcher:
        self.log = RetrievalLog()
        return Fetcher(self.transport, self.log, self.clock)


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


def coinglass_unit(ctx: RunContext, unit: str) -> UnitOutput:
    if not ctx.allow_coinglass:
        raise BackfillRefused(
            "PROVIDER_REQUEST_MISMATCH", "CoinGlass runs only with --allow-coinglass, after the projection's review (owner Part B ruling 10)"
        )
    if not ctx.coinglass_key:
        raise BackfillRefused("PROVIDER_RESPONSE_REFUSED", "COINGLASS_API_KEY is not set")
    ctx.log = RetrievalLog()
    fetcher = coinglass.coinglass_fetcher(ctx.transport, ctx.log, api_key=ctx.coinglass_key, clock=ctx.clock)
    read = coinglass.read_etf_flows(fetcher, None, ETF_FIRST_DAY, LAST_DATA_DAY)
    funds = tuple(sorted({row.fund for row in read.flows}))
    files = {
        ("flow_history" if index == 0 else f"history_{funds_of(item)}") + ".projected.json": item.body
        for index, item in enumerate(read.projections)
    }
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


def funds_of(projection: Any) -> str:
    """The ticker a per-fund projection was requested for, from its URL's only query."""

    match = re.fullmatch(re.escape(coinglass.FUND_HISTORY_URL) + r"\?ticker=([A-Z][A-Z0-9]{0,9})", projection.url)
    if match is None:
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", "a per-fund projection without its ticker")
    return match.group(1)


@dataclass(frozen=True)
class Source:
    units: Callable[[], tuple[str, ...]]
    read: Callable[[RunContext, str], UnitOutput]


def _month_units(first: date) -> Callable[[], tuple[str, ...]]:
    return lambda: tuple(f"{month:%Y-%m}" for month in _months(first, LAST_DATA_DAY))


SOURCES: dict[str, Source] = {
    "binance-funding": Source(_month_units(DATA_WINDOW_START.date()), funding_unit),
    "binance-open-interest": Source(_month_units(OPEN_INTEREST_FIRST_DAY), open_interest_unit),
    "binance-perp-volume": Source(_month_units(DATA_WINDOW_START.date()), perp_volume_unit),
    "binance-basis": Source(lambda: ("all",), basis_unit),
    "kraken-incidents": Source(lambda: ("all",), incidents_unit),
    "kraken-liquidations": Source(lambda: tuple(day.isoformat() for day in data_window_days(KRAKEN_FIRST_DAY, LAST_DATA_DAY)), liquidation_unit),
    "coinmetrics-market-cap": Source(lambda: ("all",), market_cap_unit),
    "coinglass-etf": Source(lambda: ("all",), coinglass_unit),
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


def run_unit(ctx: RunContext, source: str, unit: str) -> UnitReport:
    try:
        _scheduled(source, unit)  # before the store or the transport is touched
        record = ctx.store.done(source, unit)
    except BackfillRefused as refused:
        return UnitReport(source, str(unit), "REFUSED", f"{refused.reason_code}: {masked(str(refused))}")
    # a unit collected with --no-persist is read again when a later run persists
    if record is not None and not (ctx.connect is not None and record["persisted"].get("not_persisted")):
        return UnitReport(source, unit, "SKIPPED")
    try:
        output = SOURCES[source].read(ctx, unit)
        retrievals = ctx.log.as_records()
        persisted: Mapping[str, int] = {}
        if output.persist is not None and ctx.connect is not None:
            with ctx.connect() as connection:
                persisted = output.persist(connection, ctx.clock())
        elif output.persist is not None:
            persisted = {"not_persisted": 1}
        files = dict(output.files)
        files["summary.json"] = canonical_json_bytes(dict(output.summary))
        files["retrievals.json"] = canonical_json_bytes(retrievals)
        ctx.store.write(source, unit, files, completed_at=ctx.clock(), persisted=persisted)
    except BackfillRefused as refused:
        return UnitReport(source, unit, "REFUSED", f"{refused.reason_code}: {masked(str(refused))}")
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
