"""Shared retrieval boundary for the RBT-003 historical provider adapters (Part A).

``BACKFILL_HISTORICAL_INPUTS_V1`` collects exactly the spans RBT-002 marked
missing, inside the data window ``2020-01-01 00:00`` .. ``2025-12-31 23:00``
(policy V7 section 3). The owner ruled on 2026-11-04 that the ticket runs in
two parts: Part A builds the adapters and the evidence writers offline, on
synthetic fixtures, and Part B runs the collection. This module therefore
defines no network transport of its own. Every adapter takes a caller-supplied
:class:`Transport`; Part B supplies the real one.

What every adapter shares:

- **The window guard.** A request is checked before the transport is called:
  every instant it asks for lies in ``[2020-01-01 00:00, 2026-01-01 00:00)``.
  An observation a response returns outside that window is refused, never
  dropped: a holdout or prohibited row in a response is an exposure to record,
  not a row to filter silently.
- **The retrieval log.** Every response is recorded by URL, status, size and
  SHA-256, never by value, with its retrieval instant; evidence files cite the
  digests.
- **One refusal class** with a closed set of reason codes.
- **Provenance** (owner review ruling 7, 2026-11-04). A row's ``available_at``
  is the retrieval instant of the responses it was read from (the later of the
  two archives for a basis row; both responses for an ETF row). The in-memory
  row carries the same instant in ``ingested_at``, which the existing
  collectors replace at persistence with their own instant: a persisted row's
  ``ingested_at`` is when it entered the database. No replay owner reads
  ``ingested_at`` on a derivative or ETF row.

Nothing here opens a database or a network connection, and nothing is
certified: the adapters produce raw records with their true provider, source
and ingestion provenance, and the replay builders model availability.
"""

from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any, Protocol

from btc_predictor.research_backtest import replay_inputs as v1


BACKFILL_ADAPTERS_VERSION = "BACKFILL_PROVIDER_ADAPTERS_V1"
BACKFILL_TICKET = "BACKFILL_HISTORICAL_INPUTS_V1"

DATA_WINDOW_START = v1.DATA_WINDOW.start
DATA_WINDOW_END = v1.DATA_WINDOW.end  # exclusive: the holdout's first instant
LAST_DATA_DAY = (DATA_WINDOW_END - timedelta(days=1)).date()

BACKFILL_REFUSAL_REASON_CODES = (
    "REQUEST_OUTSIDE_DATA_WINDOW",
    "OBSERVATION_OUTSIDE_DATA_WINDOW",
    "PROVIDER_RESPONSE_REFUSED",
    "RESPONSE_SHAPE_REFUSED",
    "ARCHIVE_CHECKSUM_MISMATCH",
    "ARCHIVE_MONTH_MISSING",
    "DELIVERY_INSTANT_MISMATCH",
    "LISTING_START_UNPROVEN",
    "CONTINUATION_CHAIN_REFUSED",
    "LIQUIDATION_SIDE_UNKNOWN",
    "DUPLICATE_PROVIDER_RECORD",
    "PROVIDER_REQUEST_MISMATCH",
)


class BackfillRefused(ValueError):
    """A request or response the adapters refuse, with a closed reason code."""

    def __init__(self, reason_code: str, message: str) -> None:
        if reason_code not in BACKFILL_REFUSAL_REASON_CODES:
            raise ValueError(f"unknown backfill refusal code {reason_code!r}")
        super().__init__(f"{reason_code}: {message}")
        self.reason_code = reason_code


@dataclass(frozen=True)
class TransportResponse:
    """One HTTP response as the transport returns it: status and raw bytes."""

    status: int
    body: bytes


class Transport(Protocol):
    """Part B supplies the network implementation; Part A tests supply fakes."""

    def __call__(self, url: str, headers: Mapping[str, str]) -> TransportResponse:
        ...


@dataclass(frozen=True)
class Retrieval:
    """One recorded response: where, when, its status and its digest, never its values."""

    url: str
    retrieved_at: datetime
    status: int
    size: int
    sha256: str

    def as_record(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "retrieved_at": iso(self.retrieved_at),
            "status": self.status,
            "size": self.size,
            "sha256": self.sha256,
        }


@dataclass
class RetrievalLog:
    """Every response one collection read, in order."""

    retrievals: list[Retrieval] = field(default_factory=list)

    def record(self, retrieval: Retrieval) -> None:
        self.retrievals.append(retrieval)

    def digests(self, *, ok_only: bool = True) -> tuple[str, ...]:
        return tuple(item.sha256 for item in self.retrievals if not ok_only or item.status == 200)

    def as_records(self) -> list[dict[str, Any]]:
        return [item.as_record() for item in self.retrievals]


Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class Fetched:
    """A ``200`` response body with its URL, retrieval instant and digest."""

    url: str
    body: bytes
    retrieved_at: datetime

    @property
    def sha256(self) -> str:
        return sha256_hex(self.body)


@dataclass(frozen=True)
class Fetcher:
    """A transport bound to a log and a clock; the only way an adapter reads a URL.

    ``headers`` go to the transport only: the log records the URL, never a
    header, so a credential passed this way is never persisted.
    """

    transport: Transport
    log: RetrievalLog
    clock: Clock = utc_now
    headers: Mapping[str, str] = field(default_factory=dict)

    def fetch(self, url: str) -> Fetched:
        """The ``200`` response; any other status refuses the collection."""

        fetched = self.fetch_optional(url, allow_not_found=False)
        if fetched is None:  # unreachable: only an allowed 404 returns None
            raise BackfillRefused("PROVIDER_RESPONSE_REFUSED", f"{url}: no response")
        return fetched

    def fetch_optional(self, url: str, *, allow_not_found: bool = True) -> Fetched | None:
        """The ``200`` response, or ``None`` for a ``404`` when that is allowed.

        Any other status refuses: an error is never read as an empty result.
        """

        retrieved_at = require_utc(self.clock(), "retrieved_at")
        response = self.transport(url, dict(self.headers))
        if not isinstance(response, TransportResponse) or not isinstance(response.body, bytes):
            raise BackfillRefused("PROVIDER_RESPONSE_REFUSED", f"{url}: the transport returned no response bytes")
        if type(response.status) is not int:
            raise BackfillRefused("PROVIDER_RESPONSE_REFUSED", f"{url}: the transport returned no integer status")
        self.log.record(Retrieval(url, retrieved_at, response.status, len(response.body), sha256_hex(response.body)))
        if response.status == 200:
            return Fetched(url, response.body, retrieved_at)
        if response.status == 404 and allow_not_found:
            return None
        raise BackfillRefused("PROVIDER_RESPONSE_REFUSED", f"{url}: HTTP {response.status}")


# --- the data window ------------------------------------------------------------------------


def require_utc(value: Any, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"{name} must be a UTC datetime")
    return value.astimezone(UTC)


def require_request_span(start: datetime, end: datetime, what: str) -> None:
    """A request for ``[start, end)`` must lie inside the data window."""

    start = require_utc(start, f"{what} start")
    end = require_utc(end, f"{what} end")
    if not DATA_WINDOW_START <= start < end <= DATA_WINDOW_END:
        raise BackfillRefused(
            "REQUEST_OUTSIDE_DATA_WINDOW",
            f"{what}: [{iso(start)}, {iso(end)}) is not inside the data window "
            f"[{iso(DATA_WINDOW_START)}, {iso(DATA_WINDOW_END)})",
        )


def require_observation_in_window(instant: datetime, what: str) -> datetime:
    """A returned observation outside the data window is an exposure, refused."""

    instant = require_utc(instant, what)
    if not DATA_WINDOW_START <= instant < DATA_WINDOW_END:
        raise BackfillRefused(
            "OBSERVATION_OUTSIDE_DATA_WINDOW",
            f"{what} {iso(instant)} lies outside the data window; the response is refused, not filtered",
        )
    return instant


def data_window_months(first: date | None = None, last: date | None = None) -> tuple[date, ...]:
    """The first day of every month from ``first``'s month to ``last``'s, clipped to the window."""

    first = max(first or DATA_WINDOW_START.date(), DATA_WINDOW_START.date())
    last = min(last or LAST_DATA_DAY, LAST_DATA_DAY)
    months = []
    cursor = first.replace(day=1)
    while cursor <= last:
        months.append(cursor)
        cursor = date(cursor.year + cursor.month // 12, cursor.month % 12 + 1, 1)
    return tuple(months)


def data_window_days(first: date, last: date) -> tuple[date, ...]:
    """Every UTC day from ``first`` to ``last`` inclusive; both must be in the window."""

    if not DATA_WINDOW_START.date() <= first <= last <= LAST_DATA_DAY:
        raise BackfillRefused("REQUEST_OUTSIDE_DATA_WINDOW", f"days {first}..{last} are not inside the data window")
    return tuple(first + timedelta(days=offset) for offset in range((last - first).days + 1))


def month_end(month: date) -> datetime:
    """The exclusive end instant of the month starting at ``month``."""

    return datetime(month.year + month.month // 12, month.month % 12 + 1, 1, tzinfo=UTC)


def midnight(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def hours_of(day: date) -> tuple[datetime, ...]:
    start = midnight(day)
    return tuple(start + timedelta(hours=offset) for offset in range(24))


# --- archives -------------------------------------------------------------------------------


def _single_member_text(data: bytes, expected_name: str, what: str) -> str:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        names = archive.namelist()
        if names != [expected_name]:
            raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"{what}: the archive holds {names}, not [{expected_name!r}]")
        return archive.read(expected_name).decode("ascii")
    except (zipfile.BadZipFile, UnicodeDecodeError, KeyError) as error:
        raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"{what}: not a readable single-CSV archive ({error})") from None


def _csv_rows(text: str, what: str) -> list[list[str]]:
    rows = [row for row in csv.reader(io.StringIO(text))]
    if any(not row for row in rows):
        raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"{what}: the CSV has a blank line")
    return rows


def single_csv_member(data: bytes, expected_name: str, what: str) -> list[list[str]]:
    """The rows of the one CSV file a provider archive holds, under its expected name."""

    return _csv_rows(_single_member_text(data, expected_name, what), what)


def single_csv_member_records(data: bytes, expected_name: str, what: str) -> list[tuple[str, list[str]]]:
    """Each record of the archive's one CSV with its exact text: its line, without the terminator.

    The archive is ASCII, so a record's text is its bytes; owner ruling 4
    compares records by these (review F10). Every record must be one line, and
    the records must be exactly the rows the whole file parses to.
    """

    text = _single_member_text(data, expected_name, what)
    records = []
    for line in text.splitlines():
        parsed = list(csv.reader([line]))
        if len(parsed) != 1 or not parsed[0]:
            raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"{what}: line {line!r} is not one CSV record")
        records.append((line, parsed[0]))
    if [row for _, row in records] != _csv_rows(text, what):
        raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"{what}: the CSV's records do not split by line")
    return records


def data_rows(rows: list[list[str]], header: Sequence[str], what: str) -> Iterator[list[str]]:
    """Rows after an optional exact header, each exactly as wide as the header.

    The archives write the header in some files and not others; anything else
    in the first row must be a data row of the same width.
    """

    start = 1 if rows and rows[0] == list(header) else 0
    for number, row in enumerate(rows[start:], start=start + 1):
        if len(row) != len(header):
            raise BackfillRefused(
                "RESPONSE_SHAPE_REFUSED",
                f"{what} line {number}: {len(row)} fields, not the {len(header)} of {list(header)}",
            )
        yield row


# --- canonical form --------------------------------------------------------------------------


def iso(instant: datetime) -> str:
    """The evidence files' one spelling of an instant (as RBT-001A's ``_iso``)."""

    return instant.astimezone(UTC).isoformat()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return v1.canonical_json_bytes(value)


def epoch_milliseconds(instant: datetime) -> int:
    instant = require_utc(instant, "instant")
    return (instant - datetime(1970, 1, 1, tzinfo=UTC)) // timedelta(milliseconds=1)


def from_epoch_milliseconds(value: Any, what: str) -> datetime:
    """A millisecond epoch written as an integer string or JSON integer (13 digits in range)."""

    text = str(value)
    if isinstance(value, bool) or not text.isdigit() or len(text) != 13:
        raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"{what} {value!r} is not a millisecond epoch")
    return datetime(1970, 1, 1, tzinfo=UTC) + timedelta(milliseconds=int(text))
