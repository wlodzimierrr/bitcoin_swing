"""Loader for the frozen `US_EQUITY_MARKET_CLOSURE_TABLE_V1` closure table.

`POSTP1-001V2A-T1` freezes a static, hash-bound table of every full-day closure
of the US equity venues that list the US spot bitcoin ETF universe.  The table's
authority is the exact-hash review of the table itself, exactly as for any other
frozen constant in this repository.  There is no runtime acquisition, worker,
verifier or origin authority here, and this module imports nothing from the
closed ETF-calendar proof-architecture lineage.

Consumers pass the loaded set to the existing ``market_holidays`` parameter of
``btc_predictor.features.flow.etf_flow_window``.  Wiring a consumer belongs to
that consumer's ticket; this module only loads.

A closure that is missing from the table is never treated as an open day.  The
flow owner counts the unlisted date as a publication date, finds no flow record
for it and fails closed with ``ETF_FLOW_INPUT_MISSING``.  Corrections are new
frozen versions, reviewed before use; the table is never edited in place.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any


TABLE_VERSION = "US_EQUITY_MARKET_CLOSURE_TABLE_V1"
PROGRAM_TICKET = "POSTP1-001V2A-T1"
REQUIRED_REVIEW = "POSTP1-002V2A-T1"

NAMESPACE = "prospective_evidence/us_equity_market_closure_table_v1"
DEFINITION_FILENAME = "us_equity_market_closure_table_v1_definition.json"
CLOSURE_TABLE_FILENAME = "closure_table.json"
SOURCE_INDEX_FILENAME = "source_index.json"

# Frozen anchors.  A single altered byte in any of these files refuses.
# *_FILE_SHA256 is SHA-256 over the checked-in file bytes; DEFINITION_SHA256 is
# the artifact's canonical-JSON definition digest, with the field excluded.
DEFINITION_SHA256 = "2292388e4a91c1617275ac20ed9d6b45e4b9678525c020e1ccc6fc36a01d1710"
DEFINITION_FILE_SHA256 = (
    "0692e778a8a20e87cfa9b7c40b0d1af37b201e870d448d683ee467b7124456fe"
)
CLOSURE_TABLE_FILE_SHA256 = (
    "4a7a5a25d19ead02619e83af6dd99574372450a08d1daac17973947911ee241d"
)
SOURCE_INDEX_FILE_SHA256 = (
    "f939b1d70da2f0543e19c73dcba96471c39735a369c159d4ead1041d7b38ebd3"
)

LISTING_VENUES = ("CBOE_BZX", "NASDAQ", "NYSE_ARCA")
COVERAGE_START = date(2023, 1, 1)
COVERAGE_END = date(2026, 12, 31)

CLOSED = "CLOSED"
OPEN_OR_NOT_LISTED = "OPEN_OR_NOT_LISTED"
VENUE_STATUSES = (CLOSED, OPEN_OR_NOT_LISTED)

ALL_VENUES_CLOSED = "ALL_VENUES_CLOSED"
VENUE_DISAGREEMENT = "VENUE_DISAGREEMENT"
AGREEMENTS = (ALL_VENUES_CLOSED, VENUE_DISAGREEMENT)

SCHEDULED_HOLIDAY = "SCHEDULED_HOLIDAY"
UNSCHEDULED_CLOSURE = "UNSCHEDULED_CLOSURE"
CLOSURE_TYPES = (SCHEDULED_HOLIDAY, UNSCHEDULED_CLOSURE)

_WEEKDAYS = (
    "MONDAY",
    "TUESDAY",
    "WEDNESDAY",
    "THURSDAY",
    "FRIDAY",
    "SATURDAY",
    "SUNDAY",
)


class ClosureTableError(ValueError):
    """Raised when the frozen closure table cannot be used exactly as frozen."""


def namespace_root() -> Path:
    """Return the checked-in frozen namespace directory."""

    return Path(__file__).resolve().parents[2] / NAMESPACE


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("ascii")).hexdigest()


def _read_hash_bound(filename: str, expected_sha256: str) -> dict[str, Any]:
    """Read one frozen namespace file, refusing unless its bytes hash exactly."""

    path = namespace_root() / filename
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ClosureTableError(f"{filename} is not readable: {exc}") from exc
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_sha256:
        raise ClosureTableError(
            f"{filename} does not match its frozen hash: "
            f"expected {expected_sha256}, found {actual}"
        )
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ClosureTableError(f"{filename} is not canonical ASCII JSON") from exc
    if not isinstance(payload, dict):
        raise ClosureTableError(f"{filename} is not a JSON object")
    declared = dict(payload)
    if declared.pop("definition_sha256", None) != _digest(declared):
        raise ClosureTableError(f"{filename} definition_sha256 does not recompute")
    return payload


def _parse_date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise ClosureTableError(f"{field} is not a string")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ClosureTableError(f"{field} is not an ISO date: {value!r}") from exc


def _verified_table() -> dict[str, Any]:
    """Return the frozen table after verifying every frozen anchor it declares."""

    definition = _read_hash_bound(DEFINITION_FILENAME, DEFINITION_FILE_SHA256)
    table = _read_hash_bound(CLOSURE_TABLE_FILENAME, CLOSURE_TABLE_FILE_SHA256)
    # The provenance index does not feed the returned set, but it is part of the
    # hash-bound namespace, so a swap of it refuses here too rather than later.
    _read_hash_bound(SOURCE_INDEX_FILENAME, SOURCE_INDEX_FILE_SHA256)

    if definition.get("contract_version") != TABLE_VERSION:
        raise ClosureTableError("definition contract_version is not the frozen version")
    if definition.get("definition_sha256") != DEFINITION_SHA256:
        raise ClosureTableError("definition digest is not the frozen definition hash")
    if definition.get("closure_table_file_sha256") != CLOSURE_TABLE_FILE_SHA256:
        raise ClosureTableError("definition does not bind the frozen closure table hash")
    if definition.get("source_index_file_sha256") != SOURCE_INDEX_FILE_SHA256:
        raise ClosureTableError("definition does not bind the frozen source index hash")
    if tuple(definition.get("venues", ())) != LISTING_VENUES:
        raise ClosureTableError("definition venues are not the frozen listing venues")

    if tuple(table.get("venues", ())) != LISTING_VENUES:
        raise ClosureTableError("table venues are not the frozen listing venues")
    if _parse_date(table.get("coverage_start"), "coverage_start") != COVERAGE_START:
        raise ClosureTableError("table coverage_start is not the frozen coverage start")
    if _parse_date(table.get("coverage_end"), "coverage_end") != COVERAGE_END:
        raise ClosureTableError("table coverage_end is not the frozen coverage end")
    for key in ("coverage_start", "coverage_end"):
        if definition.get(key) != table.get(key):
            raise ClosureTableError(f"definition and table disagree on {key}")

    rows = table.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ClosureTableError("table rows are missing")
    if table.get("row_count") != len(rows):
        raise ClosureTableError("table row_count does not match the rows")
    return table


def _row_dates(table: Mapping[str, Any]) -> tuple[dict[date, str], list[date]]:
    """Return ``{closure date: agreement}`` and the declared disagreement dates."""

    by_date: dict[date, str] = {}
    for index, row in enumerate(table["rows"]):
        if not isinstance(row, dict):
            raise ClosureTableError(f"row {index} is not a JSON object")
        day = _parse_date(row.get("date"), f"row {index} date")
        if day in by_date:
            raise ClosureTableError(f"row {index} repeats the date {day.isoformat()}")
        if not COVERAGE_START <= day <= COVERAGE_END:
            raise ClosureTableError(f"row {day.isoformat()} is outside coverage")
        if day.weekday() >= 5:
            raise ClosureTableError(f"row {day.isoformat()} is not a weekday")
        if row.get("weekday") != _WEEKDAYS[day.weekday()]:
            raise ClosureTableError(f"row {day.isoformat()} weekday does not match")
        if row.get("closure_type") not in CLOSURE_TYPES:
            raise ClosureTableError(f"row {day.isoformat()} closure_type is unknown")

        status = row.get("venue_status")
        if not isinstance(status, dict) or tuple(sorted(status)) != LISTING_VENUES:
            raise ClosureTableError(
                f"row {day.isoformat()} does not carry all listing venue statuses"
            )
        if any(value not in VENUE_STATUSES for value in status.values()):
            raise ClosureTableError(f"row {day.isoformat()} venue status is unknown")

        agreement = row.get("agreement")
        if agreement not in AGREEMENTS:
            raise ClosureTableError(f"row {day.isoformat()} agreement is unknown")
        closed_everywhere = all(status[venue] == CLOSED for venue in LISTING_VENUES)
        if agreement != (ALL_VENUES_CLOSED if closed_everywhere else VENUE_DISAGREEMENT):
            raise ClosureTableError(
                f"row {day.isoformat()} agreement does not match its venue statuses"
            )
        by_date[day] = agreement

    declared = table.get("venue_disagreement_dates")
    if not isinstance(declared, list):
        raise ClosureTableError("venue_disagreement_dates is missing")
    disagreements = [
        _parse_date(value, "venue_disagreement_dates") for value in declared
    ]
    derived = sorted(day for day, agree in by_date.items() if agree == VENUE_DISAGREEMENT)
    if sorted(disagreements) != derived:
        raise ClosureTableError(
            "venue_disagreement_dates does not match the rows it summarises"
        )
    return by_date, derived


def load_closures(start: date, end: date) -> frozenset[date]:
    """Return every full-day closure in ``[start, end]``, both dates inclusive.

    The table bytes are verified against their frozen hash on every call.  The
    range must lie wholly inside the frozen coverage and must not contain a date
    on which the listing venues disagree; either refuses with
    :class:`ClosureTableError` rather than implying that a date was open.
    """

    # datetime is a date subclass and carries a time component this table has not
    # frozen, so a subclass is refused rather than silently truncated.
    for name, value in (("start", start), ("end", end)):
        if type(value) is not date:
            raise ClosureTableError(
                f"{name} must be a datetime.date, not {type(value).__name__}"
            )
    if start > end:
        raise ClosureTableError(
            f"start {start.isoformat()} is after end {end.isoformat()}"
        )
    if start < COVERAGE_START or end > COVERAGE_END:
        raise ClosureTableError(
            f"requested range {start.isoformat()}..{end.isoformat()} is not wholly "
            f"inside the frozen coverage "
            f"{COVERAGE_START.isoformat()}..{COVERAGE_END.isoformat()}; an uncovered "
            f"date is never implied open"
        )

    table = _verified_table()
    by_date, disagreements = _row_dates(table)

    blocking = [day for day in disagreements if start <= day <= end]
    if blocking:
        listed = ", ".join(day.isoformat() for day in blocking)
        raise ClosureTableError(
            f"requested range {start.isoformat()}..{end.isoformat()} contains a "
            f"venue disagreement: {listed}"
        )

    return frozenset(
        day
        for day, agreement in by_date.items()
        if agreement == ALL_VENUES_CLOSED and start <= day <= end
    )
