"""Frozen pre-data authority for U.S. spot-Bitcoin-ETF publication dates.

The low-level ETF feature owners intentionally retain their historical
``market_holidays`` argument.  Scientific callers use this module to derive
that argument from append-only, content-addressed official-exchange evidence.
No live source is consulted during replay.
"""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from btc_predictor.data import EtfFlow, require_utc_datetime
from btc_predictor.features import flow as _flow


AUTHORITY_VERSION = "ETF_PUBLICATION_CALENDAR_AUTHORITY_V1"
PROGRAM_TICKET = "POSTP1-001V2A"
WORKSTREAM = "EPIC X"
WORKSTREAM_NAME = "PROSPECTIVE INTEGRATION EVIDENCE"
AUTHORITY_STATUS = "FROZEN_PRE_DATA_ETF_CALENDAR_AUTHORITY_AWAITING_XHIGH_REVIEW"
FINAL_CLASSIFICATION = "ETF_PUBLICATION_CALENDAR_AUTHORITY_V1_READY_FOR_XHIGH_REVIEW"
CERTIFICATION_STATE = "NOT_CERTIFIED_AWAITING_INDEPENDENT_EXACT_HASH_XHIGH_REVIEW"
OUTPUT_NAMESPACE = "prospective_evidence/etf_publication_calendar_authority_v1"
PROTOCOL_FILENAME = "authority_definition.json"
REPORT_FILENAME = "ETF_PUBLICATION_CALENDAR_AUTHORITY_V1_REPORT.md"

NEW_YORK_TIMEZONE = "America/New_York"
CANONICAL_VENUES = ("NYSE_ARCA", "NASDAQ", "CBOE_BZX")
SESSION_STATUSES = ("OPEN_REGULAR", "OPEN_EARLY_CLOSE", "CLOSED")
OPEN_SESSION_STATUSES = frozenset(("OPEN_REGULAR", "OPEN_EARLY_CLOSE"))
EXPECTED = "EXPECTED"
NOT_EXPECTED = "NOT_EXPECTED"
UNRESOLVED = "UNRESOLVED"
RESOLVED = "RESOLVED"

SOURCE_AUTHORITY_REGISTRY: dict[str, dict[str, str]] = {
    "NYSE_ARCA": {
        "source_authority_id": "NYSE_ARCA_OFFICIAL_TRADING_CALENDAR",
        "source_class": "NYSE / NYSE Arca official Holidays & Trading Hours / annual trading calendar",
    },
    "NASDAQ": {
        "source_authority_id": "NASDAQ_TRADER_US_EQUITIES_CALENDAR",
        "source_class": "Nasdaq Trader official U.S. Equity and Options Markets Trading Calendar",
    },
    "CBOE_BZX": {
        "source_authority_id": "CBOE_US_EQUITIES_HOURS_HOLIDAYS",
        "source_class": "Cboe official U.S. Equities Hours & Holidays / schedule-update notices",
    },
}

SOURCE_SNAPSHOT_KIND = "ETF_OFFICIAL_CALENDAR_SOURCE_SNAPSHOT_V1"
NORMALIZED_SCHEDULE_KIND = "ETF_NORMALIZED_VENUE_SCHEDULE_V1"
VENUE_SESSION_RECORD_KIND = "ETF_VENUE_SESSION_CALENDAR_RECORD_V1"
NORMALIZATION_METHOD = "SOURCE_BOUND_NORMALIZED_SCHEDULE_REPLAY_V1"
RECORD_DIGEST_FIELD = "record_sha256"

COLLECTION_AUTHORIZED = False
V2_CORRECTED_HASH_ISSUED = False
V2_CERTIFIED = False
POSTP1_003R3_AUTHORIZED = False
POSTP1_004_AUTHORIZED = False
BTC019_REOPENED = False
BTC019_SEALED_DATA_ACCESSED = False
EPIC_T_MODIFIED = False


class EtfCalendarAuthorityError(ValueError):
    """Raised when calendar evidence or a frozen artifact is invalid."""


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


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _parse_date(value: Any, field_name: str) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise EtfCalendarAuthorityError(f"{field_name} must be an ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise EtfCalendarAuthorityError(f"{field_name} must be an ISO date") from error


def _parse_utc(value: Any, field_name: str) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError as error:
            raise EtfCalendarAuthorityError(f"{field_name} must be ISO-8601") from error
    try:
        return require_utc_datetime(value, field_name)
    except (TypeError, ValueError) as error:
        raise EtfCalendarAuthorityError(str(error)) from error


def _record(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    if RECORD_DIGEST_FIELD in result:
        raise EtfCalendarAuthorityError("record payload may not supply record_sha256")
    result[RECORD_DIGEST_FIELD] = _digest(result)
    return result


def _verify_record(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(record)
    declared = payload.pop(RECORD_DIGEST_FIELD, None)
    if not _is_sha256(declared) or _digest(payload) != declared:
        raise EtfCalendarAuthorityError("record_sha256 does not recompute")
    return dict(record)


class CalendarEvidenceStore:
    """Small append-only content-addressed store used by the calendar owner."""

    def __init__(self, records: Iterable[Mapping[str, Any]] = ()) -> None:
        self._records: dict[str, dict[str, Any]] = {}
        for record in records:
            self.put(record)

    def put(self, record: Mapping[str, Any]) -> str:
        payload = dict(record)
        if RECORD_DIGEST_FIELD not in payload:
            payload = _record(payload)
        _verify_record(payload)
        identity = payload[RECORD_DIGEST_FIELD]
        prior = self._records.get(identity)
        if prior is not None and prior != payload:  # pragma: no cover - SHA collision guard
            raise EtfCalendarAuthorityError("content identity collision")
        self._records[identity] = payload
        return identity

    def get(self, record_sha256: str) -> dict[str, Any]:
        if not _is_sha256(record_sha256) or record_sha256 not in self._records:
            raise EtfCalendarAuthorityError("calendar evidence reference is missing")
        return dict(self._records[record_sha256])

    def records(self, *, record_kind: str | None = None) -> tuple[dict[str, Any], ...]:
        rows = self._records.values()
        if record_kind is not None:
            rows = (row for row in rows if row.get("record_kind") == record_kind)
        return tuple(dict(row) for row in sorted(rows, key=lambda row: row[RECORD_DIGEST_FIELD]))


def official_source_snapshot_record(
    *,
    venue_id: str,
    source_document_identity: str,
    source_bytes: bytes,
    acquired_at: datetime,
    available_at: datetime,
    published_at: datetime | None = None,
) -> dict[str, Any]:
    """Persist exact official-source bytes; a URL alone is never authority."""

    if venue_id not in CANONICAL_VENUES:
        raise EtfCalendarAuthorityError("venue_id is outside the frozen venue set")
    if not source_document_identity or not source_bytes:
        raise EtfCalendarAuthorityError("source identity and exact bytes are required")
    acquired = _parse_utc(acquired_at, "acquired_at")
    available = _parse_utc(available_at, "available_at")
    if available > acquired:
        raise EtfCalendarAuthorityError("available_at may not exceed acquired_at")
    authority = SOURCE_AUTHORITY_REGISTRY[venue_id]
    payload: dict[str, Any] = {
        "record_kind": SOURCE_SNAPSHOT_KIND,
        "schema_version": 1,
        "venue_id": venue_id,
        "source_authority_id": authority["source_authority_id"],
        "source_class": authority["source_class"],
        "source_document_identity": source_document_identity,
        "source_document_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "source_document_base64": base64.b64encode(source_bytes).decode("ascii"),
        "published_at": (
            _parse_utc(published_at, "published_at").isoformat()
            if published_at is not None
            else None
        ),
        "observed_at": acquired.isoformat(),
        "acquired_at": acquired.isoformat(),
        "available_at": available.isoformat(),
    }
    return _record(payload)


def normalized_schedule_record(
    store: CalendarEvidenceStore,
    *,
    source_snapshot_sha256: str,
    coverage_start: date,
    coverage_end: date,
    exceptions: Mapping[date | str, str],
    default_weekday_status: str = "OPEN_REGULAR",
) -> dict[str, Any]:
    """Bind a replayable normalized schedule to exact official source bytes."""

    source = _verify_source_snapshot(store.get(source_snapshot_sha256))
    start = _parse_date(coverage_start, "coverage_start")
    end = _parse_date(coverage_end, "coverage_end")
    if end < start:
        raise EtfCalendarAuthorityError("coverage_end must be >= coverage_start")
    if default_weekday_status not in OPEN_SESSION_STATUSES:
        raise EtfCalendarAuthorityError("default weekday status must be an open session")
    normalized: dict[str, str] = {}
    for raw_date, status in exceptions.items():
        trade_date = _parse_date(raw_date, "exception trade_date")
        if not start <= trade_date <= end:
            raise EtfCalendarAuthorityError("schedule exception is outside coverage")
        if trade_date.weekday() >= 5:
            raise EtfCalendarAuthorityError("weekends are governed independently")
        if status not in SESSION_STATUSES:
            raise EtfCalendarAuthorityError("invalid session_status")
        normalized[trade_date.isoformat()] = status
    normalized = dict(sorted(normalized.items()))
    schedule_core = {
        "coverage_start": start.isoformat(),
        "coverage_end": end.isoformat(),
        "default_weekday_status": default_weekday_status,
        "exceptions": normalized,
    }
    payload = {
        "record_kind": NORMALIZED_SCHEDULE_KIND,
        "schema_version": 1,
        "venue_id": source["venue_id"],
        "source_authority_id": source["source_authority_id"],
        "source_snapshot_sha256": source_snapshot_sha256,
        "source_document_sha256": source["source_document_sha256"],
        "normalization_method": NORMALIZATION_METHOD,
        "normalized_schedule": schedule_core,
        "normalized_schedule_sha256": _digest(schedule_core),
        "available_at": source["available_at"],
        "acquired_at": source["acquired_at"],
    }
    return _record(payload)


def venue_session_calendar_record(
    store: CalendarEvidenceStore,
    *,
    normalized_schedule_sha256: str,
    trade_date: date,
) -> dict[str, Any]:
    """Regenerate one immutable venue/date row from a bound schedule."""

    schedule = _verify_schedule(store, normalized_schedule_sha256)
    day = _parse_date(trade_date, "trade_date")
    core = schedule["normalized_schedule"]
    if not date.fromisoformat(core["coverage_start"]) <= day <= date.fromisoformat(
        core["coverage_end"]
    ):
        raise EtfCalendarAuthorityError("trade_date is outside schedule coverage")
    if day.weekday() >= 5:
        status = "CLOSED"
    else:
        status = core["exceptions"].get(day.isoformat(), core["default_weekday_status"])
    source = _verify_source_snapshot(store.get(schedule["source_snapshot_sha256"]))
    return _record(
        {
            "record_kind": VENUE_SESSION_RECORD_KIND,
            "schema_version": 1,
            "venue_id": schedule["venue_id"],
            "trade_date": day.isoformat(),
            "session_status": status,
            "source_authority_id": schedule["source_authority_id"],
            "source_document_identity": source["source_document_identity"],
            "source_document_sha256": source["source_document_sha256"],
            "source_snapshot_sha256": schedule["source_snapshot_sha256"],
            "normalized_schedule_sha256": normalized_schedule_sha256,
            "normalized_schedule_content_sha256": schedule[
                "normalized_schedule_sha256"
            ],
            "published_at": source["published_at"],
            "observed_at": source["observed_at"],
            "acquired_at": source["acquired_at"],
            "available_at": schedule["available_at"],
        }
    )


def _verify_source_snapshot(record: Mapping[str, Any]) -> dict[str, Any]:
    row = _verify_record(record)
    venue = row.get("venue_id")
    if row.get("record_kind") != SOURCE_SNAPSHOT_KIND or venue not in CANONICAL_VENUES:
        raise EtfCalendarAuthorityError("invalid official source snapshot")
    expected = SOURCE_AUTHORITY_REGISTRY[venue]
    if row.get("source_authority_id") != expected["source_authority_id"]:
        raise EtfCalendarAuthorityError("wrong source authority for venue")
    try:
        raw = base64.b64decode(row["source_document_base64"], validate=True)
    except Exception as error:
        raise EtfCalendarAuthorityError("source snapshot bytes are invalid") from error
    if hashlib.sha256(raw).hexdigest() != row.get("source_document_sha256"):
        raise EtfCalendarAuthorityError("source document digest does not recompute")
    _parse_utc(row.get("available_at"), "available_at")
    _parse_utc(row.get("acquired_at"), "acquired_at")
    return row


def _verify_schedule(store: CalendarEvidenceStore, sha256: str) -> dict[str, Any]:
    row = _verify_record(store.get(sha256))
    if row.get("record_kind") != NORMALIZED_SCHEDULE_KIND:
        raise EtfCalendarAuthorityError("reference is not a normalized schedule")
    source = _verify_source_snapshot(store.get(row.get("source_snapshot_sha256")))
    if row.get("venue_id") != source["venue_id"]:
        raise EtfCalendarAuthorityError("schedule venue does not match source")
    if row.get("source_authority_id") != source["source_authority_id"]:
        raise EtfCalendarAuthorityError("schedule source authority does not match")
    if row.get("source_document_sha256") != source["source_document_sha256"]:
        raise EtfCalendarAuthorityError("schedule substituted its source document")
    if _digest(row.get("normalized_schedule")) != row.get("normalized_schedule_sha256"):
        raise EtfCalendarAuthorityError("normalized schedule digest does not recompute")
    return row


def _verify_venue_row(store: CalendarEvidenceStore, record: Mapping[str, Any]) -> dict[str, Any]:
    row = _verify_record(record)
    if row.get("record_kind") != VENUE_SESSION_RECORD_KIND:
        raise EtfCalendarAuthorityError("record is not a venue session row")
    venue = row.get("venue_id")
    day = _parse_date(row.get("trade_date"), "trade_date")
    if venue not in CANONICAL_VENUES or row.get("session_status") not in SESSION_STATUSES:
        raise EtfCalendarAuthorityError("venue session row has invalid values")
    if row.get("source_authority_id") != SOURCE_AUTHORITY_REGISTRY[venue][
        "source_authority_id"
    ]:
        raise EtfCalendarAuthorityError("wrong source authority for venue")
    schedule_sha = row.get("normalized_schedule_sha256")
    schedule = _verify_schedule(store, schedule_sha)
    regenerated = venue_session_calendar_record(
        store, normalized_schedule_sha256=schedule_sha, trade_date=day
    )
    if regenerated != row:
        raise EtfCalendarAuthorityError("venue session row does not replay")
    if row.get("normalized_schedule_content_sha256") != schedule[
        "normalized_schedule_sha256"
    ]:
        raise EtfCalendarAuthorityError("venue row substituted normalized content")
    return row


@dataclass(frozen=True)
class VenueSessionResolution:
    venue_id: str
    trade_date: date
    state: str
    selected_record_sha256: str | None = None
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class CommonSessionResolution:
    trade_date: date
    state: str
    venue_states: tuple[tuple[str, str], ...]
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExpectedPublicationDatesResult:
    state: str
    expected_dates: tuple[date, ...]
    unresolved_dates: tuple[date, ...]
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class CalendarWindowResult:
    state: str
    expected_dates: tuple[date, ...]
    market_holidays: frozenset[date]
    unresolved_dates: tuple[date, ...]
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScientificEtfFlowResult:
    evaluability_state: str
    calendar: CalendarWindowResult
    feature: _flow.EtfFlowFeatureResult | None
    reason_codes: tuple[str, ...] = ()


def venue_session_status(
    venue: str,
    trade_date: date,
    decision_time: datetime,
    evidence_store: CalendarEvidenceStore,
) -> VenueSessionResolution:
    """Resolve the latest PIT-valid authoritative revision, never ingestion order."""

    day = _parse_date(trade_date, "trade_date")
    cutoff = _parse_utc(decision_time, "decision_time")
    if venue not in CANONICAL_VENUES:
        raise EtfCalendarAuthorityError("venue is outside the frozen venue set")
    if day.weekday() >= 5:
        return VenueSessionResolution(venue, day, "CLOSED", reason_codes=("WEEKEND",))

    candidates: list[dict[str, Any]] = []
    invalid_matching_evidence = False
    for raw in evidence_store.records(record_kind=VENUE_SESSION_RECORD_KIND):
        if raw.get("venue_id") != venue or raw.get("trade_date") != day.isoformat():
            continue
        try:
            row = _verify_venue_row(evidence_store, raw)
            available_at = _parse_utc(row["available_at"], "available_at")
        except EtfCalendarAuthorityError:
            invalid_matching_evidence = True
            continue
        if available_at <= cutoff:
            candidates.append(row)
    if invalid_matching_evidence:
        return VenueSessionResolution(
            venue, day, UNRESOLVED, reason_codes=("INVALID_AUTHORITATIVE_EVIDENCE",)
        )
    if not candidates:
        return VenueSessionResolution(
            venue, day, UNRESOLVED, reason_codes=("VENUE_CALENDAR_EVIDENCE_MISSING",)
        )
    latest_time = max(_parse_utc(row["available_at"], "available_at") for row in candidates)
    latest = [
        row
        for row in candidates
        if _parse_utc(row["available_at"], "available_at") == latest_time
    ]
    states = {row["session_status"] for row in latest}
    if len(states) != 1:
        return VenueSessionResolution(
            venue, day, UNRESOLVED, reason_codes=("CONFLICTING_LATEST_CALENDAR_REVISION",)
        )
    selected = max(latest, key=lambda row: row[RECORD_DIGEST_FIELD])
    return VenueSessionResolution(
        venue, day, states.pop(), selected[RECORD_DIGEST_FIELD]
    )


def common_etf_session_status(
    trade_date: date,
    decision_time: datetime,
    evidence_store: CalendarEvidenceStore,
) -> CommonSessionResolution:
    """Apply the frozen three-venue intersection, failing closed on unknowns."""

    day = _parse_date(trade_date, "trade_date")
    resolutions = tuple(
        venue_session_status(venue, day, decision_time, evidence_store)
        for venue in CANONICAL_VENUES
    )
    venue_states = tuple((row.venue_id, row.state) for row in resolutions)
    if any(row.state == UNRESOLVED for row in resolutions):
        reasons = tuple(
            sorted({reason for row in resolutions for reason in row.reason_codes})
        )
        return CommonSessionResolution(day, UNRESOLVED, venue_states, reasons)
    if all(row.state in OPEN_SESSION_STATUSES for row in resolutions):
        return CommonSessionResolution(day, EXPECTED, venue_states)
    return CommonSessionResolution(day, NOT_EXPECTED, venue_states)


def expected_etf_publication_dates(
    start: date,
    end: date,
    decision_time: datetime,
    evidence_store: CalendarEvidenceStore,
) -> ExpectedPublicationDatesResult:
    """Return an inclusive expected-date range or a fail-closed unresolved result."""

    first = _parse_date(start, "start")
    last = _parse_date(end, "end")
    if last < first:
        raise EtfCalendarAuthorityError("end must be >= start")
    expected: list[date] = []
    unresolved: list[date] = []
    current = first
    while current <= last:
        resolution = common_etf_session_status(current, decision_time, evidence_store)
        if resolution.state == EXPECTED:
            expected.append(current)
        elif resolution.state == UNRESOLVED:
            unresolved.append(current)
        current += timedelta(days=1)
    state = UNRESOLVED if unresolved else RESOLVED
    reasons = ("ETF_PUBLICATION_CALENDAR_UNRESOLVED",) if unresolved else ()
    return ExpectedPublicationDatesResult(
        state, tuple(expected), tuple(unresolved), reasons
    )


def derive_etf_window_calendar(
    *,
    end_date: date,
    earliest_date: date,
    window_days: int,
    decision_time: datetime,
    evidence_store: CalendarEvidenceStore,
) -> CalendarWindowResult:
    """Derive exactly the holiday adapter needed by a trailing ETF window."""

    if window_days < 1:
        raise EtfCalendarAuthorityError("window_days must be >= 1")
    end = _parse_date(end_date, "end_date")
    earliest = _parse_date(earliest_date, "earliest_date")
    if end < earliest:
        raise EtfCalendarAuthorityError("end_date must be >= earliest_date")
    expected_desc: list[date] = []
    holidays: set[date] = set()
    unresolved: list[date] = []
    current = end
    while current >= earliest and len(expected_desc) < window_days:
        resolution = common_etf_session_status(current, decision_time, evidence_store)
        if resolution.state == EXPECTED:
            expected_desc.append(current)
        elif resolution.state == NOT_EXPECTED and current.weekday() < 5:
            holidays.add(current)
        elif resolution.state == UNRESOLVED:
            unresolved.append(current)
        current -= timedelta(days=1)
    if unresolved:
        return CalendarWindowResult(
            UNRESOLVED,
            tuple(reversed(expected_desc)),
            frozenset(holidays),
            tuple(sorted(unresolved)),
            ("ETF_PUBLICATION_CALENDAR_UNRESOLVED",),
        )
    if len(expected_desc) != window_days:
        return CalendarWindowResult(
            UNRESOLVED,
            tuple(reversed(expected_desc)),
            frozenset(holidays),
            (),
            ("ETF_PUBLICATION_CALENDAR_COVERAGE_INSUFFICIENT",),
        )
    return CalendarWindowResult(
        RESOLVED, tuple(reversed(expected_desc)), frozenset(holidays), ()
    )


def scientific_etf_flow_window(
    flows: Sequence[EtfFlow],
    *,
    as_of: datetime,
    funds: Sequence[str],
    end_date: date,
    earliest_date: date,
    window_days: int,
    evidence_store: CalendarEvidenceStore,
) -> ScientificEtfFlowResult:
    """Invoke the unchanged ETF owner only after calendar authority resolves."""

    cutoff = _parse_utc(as_of, "as_of")
    calendar = derive_etf_window_calendar(
        end_date=end_date,
        earliest_date=earliest_date,
        window_days=window_days,
        decision_time=cutoff,
        evidence_store=evidence_store,
    )
    if calendar.state == UNRESOLVED:
        return ScientificEtfFlowResult(
            "NOT_EVALUABLE", calendar, None, calendar.reason_codes
        )
    if window_days == _flow.FIVE_DAY_ETF_FLOW_WINDOW_DAYS:
        feature_id = _flow.FIVE_DAY_ETF_FLOW_FEATURE_ID
        normalized_id = _flow.FIVE_DAY_ETF_NORM_FEATURE_ID
    elif window_days == _flow.TWENTY_DAY_ETF_FLOW_WINDOW_DAYS:
        feature_id = _flow.TWENTY_DAY_ETF_FLOW_FEATURE_ID
        normalized_id = _flow.TWENTY_DAY_ETF_NORM_FEATURE_ID
    else:
        raise EtfCalendarAuthorityError("scientific adapter supports frozen 5/20-day windows")
    feature = _flow.etf_flow_window(
        flows,
        as_of=cutoff,
        window_days=window_days,
        funds=funds,
        market_holidays=calendar.market_holidays,
        end_date=end_date,
        feature_id=feature_id,
        normalized_feature_id=normalized_id,
    )
    return ScientificEtfFlowResult("EVALUABLE", calendar, feature)


def venue_authority_registry_contract() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_VENUE_AUTHORITY_REGISTRY_V1",
            "canonical_venue_set": list(CANONICAL_VENUES),
            "dynamic_venue_addition": "REFUSE_REQUIRES_NEW_AUTHORITY_VERSION",
            "official_source_authorities": SOURCE_AUTHORITY_REGISTRY,
            "third_party_calendars": "DIAGNOSTICS_ONLY_NOT_SCIENTIFIC_AUTHORITY",
            "timezone": NEW_YORK_TIMEZONE,
            "trade_date_encoding": "YYYY-MM-DD",
        }
    )


def venue_session_record_schema_contract() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": VENUE_SESSION_RECORD_KIND,
            "required_fields": [
                "venue_id", "trade_date", "session_status", "source_authority_id",
                "source_document_identity", "source_document_sha256", "published_at",
                "observed_at", "acquired_at", "available_at", "record_sha256",
            ],
            "session_statuses": list(SESSION_STATUSES),
            "early_close_collapsed_into_closed": False,
            "append_only": True,
        }
    )


def common_session_rule_contract() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_COMMON_SESSION_RULE_V1",
            "publication_date_meaning": (
                "the U.S. equity trade date on which the common listing-venue "
                "calendar contains an equity trading session"
            ),
            "weekend_rule": {"SATURDAY": "CLOSED", "SUNDAY": "CLOSED"},
            "open_states": sorted(OPEN_SESSION_STATUSES),
            "common_open": "NYSE_ARCA_OPEN AND NASDAQ_OPEN AND CBOE_BZX_OPEN",
            "expected_etf_publication_date": "COMMON_OPEN",
            "venue_disagreement": "ANY_CLOSED_MEANS_NOT_EXPECTED_WHEN_ALL_RESOLVED",
            "unknown_rule": "ANY_UNRESOLVED_MEANS_UNRESOLVED",
        }
    )


def pit_revision_rule_contract() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_PIT_REVISION_RULE_V1",
            "eligibility": "available_at <= decision_time",
            "selection": "latest available_at first",
            "same_timestamp_same_state_tie_break": "greatest record_sha256",
            "same_timestamp_incompatible_states": UNRESOLVED,
            "future_revision_leaks_backward": False,
            "extraordinary_closure_rule": "effective only when official notice is available",
            "overwrite": "FORBIDDEN_APPEND_ONLY",
        }
    )


def official_source_snapshot_contract() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_OFFICIAL_SOURCE_SNAPSHOT_CONTRACT_V1",
            "authority": "exact persisted official-source snapshot + content digest + extraction result",
            "url_alone_sufficient": False,
            "manual_date_without_source_evidence_authoritative": False,
            "minimum_bindings": [
                "source authority", "document identity", "document content digest",
                "extracted date/status", "acquisition timestamp",
            ],
            "external_source_change_mutates_persisted_evidence": False,
        }
    )


def calendar_extraction_contract() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_EXTRACTION_CONTRACT_V1",
            "method": NORMALIZATION_METHOD,
            "binds": ["raw source digest", "normalized schedule digest"],
            "replay": "regenerate trade_date and session_status from bound normalized representation",
            "annual_rollover": "required venue/date range must have official evidence before evaluation",
            "missing_next_year": UNRESOLVED,
        }
    )


def etf_feature_adapter_contract() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_FEATURE_ADAPTER_V1",
            "market_holidays": "weekday dates whose common-session status is CLOSED",
            "caller_calendar_is_scientific_authority": False,
            "unresolved_action": "DO_NOT_INVOKE_FEATURE_NOT_EVALUABLE",
            "closed_date": "NOT_AN_EXPECTED_ETF_INPUT",
            "expected_date_missing_flow": "ETF_FLOW_INPUT_MISSING",
            "low_level_compatibility_parameter_retained": True,
            "window_days": {
                "ETF_FLOW_5D": _flow.FIVE_DAY_ETF_FLOW_WINDOW_DAYS,
                "ETF_FLOW_20D": _flow.TWENTY_DAY_ETF_FLOW_WINDOW_DAYS,
            },
            "flow_accel_formula": "ETFNorm_5 - ETFNorm_20 / 4",
            "formula_changed": False,
            "normalization_changed": False,
            "fund_completeness_changed": False,
            "aum_semantics_changed": False,
        }
    )


def authority_completion_semantic_diff_contract() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_AUTHORITY_COMPLETION_DIFF_V1",
            "classification": "one previously unowned ETF calendar input is now explicitly governed prospectively before collection",
            "v1": "UNOWNED INPUT",
            "v2": AUTHORITY_VERSION,
            "provider_source_semantics_changed": 0,
            "etf_feature_formula_changed": 0,
            "etf_lookbacks_changed": 0,
            "calendar_authority_row_forced_to_zero": False,
            "etf_flow_revision_selection_changed_here": False,
            "etf_source_quality_defined_here": False,
        }
    )


def _definition(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result["definition_sha256"] = _digest(result)
    return result


_CHILD_ARTIFACTS: tuple[tuple[str, str], ...] = (
    ("venue_authority_registry.json", "venue_authority_registry_contract"),
    ("venue_session_record_schema.json", "venue_session_record_schema_contract"),
    ("common_session_rule.json", "common_session_rule_contract"),
    ("pit_revision_rule.json", "pit_revision_rule_contract"),
    ("official_source_snapshot_contract.json", "official_source_snapshot_contract"),
    ("calendar_extraction_contract.json", "calendar_extraction_contract"),
    ("etf_feature_adapter_contract.json", "etf_feature_adapter_contract"),
    ("authority_completion_semantic_diff.json", "authority_completion_semantic_diff_contract"),
)


def _children() -> dict[str, dict[str, Any]]:
    return {
        filename.removesuffix(".json"): globals()[builder]()
        for filename, builder in _CHILD_ARTIFACTS
    }


def authority_definition() -> dict[str, Any]:
    children = _children()
    payload = {
        "authority_version": AUTHORITY_VERSION,
        "program_ticket": PROGRAM_TICKET,
        "workstream": {"epic": WORKSTREAM, "name": WORKSTREAM_NAME},
        "status": AUTHORITY_STATUS,
        "final_classification": FINAL_CLASSIFICATION,
        "certification": {
            "certified": False,
            "state": CERTIFICATION_STATE,
            "required_review": "independent exact-hash xHigh calendar-authority review",
        },
        "material_child_count": len(children),
        "material_child_enumeration": "mechanically enumerated from one artifact/builder registry",
        "child_definition_sha256": {
            name: child["definition_sha256"] for name, child in children.items()
        },
        "scientific_scope": "expected ETF publication-date eligibility only",
        "safety": {
            "prospective_observations_collected": 0,
            "persistent_strategy_collection_started": COLLECTION_AUTHORIZED,
            "real_stage_b_evaluation": False,
            "v2_corrected_hash_issued": V2_CORRECTED_HASH_ISSUED,
            "v2_certified": V2_CERTIFIED,
            "postp1_003r3_authorized": POSTP1_003R3_AUTHORIZED,
            "postp1_004_authorized": POSTP1_004_AUTHORIZED,
            "collection_authorized": COLLECTION_AUTHORIZED,
            "btc019_reopened": BTC019_REOPENED,
            "btc019_sealed_data_accessed": BTC019_SEALED_DATA_ACCESSED,
            "epic_t_modified": EPIC_T_MODIFIED,
        },
        "failed_v2_candidate_retained": "488251df7bc1b49f801caa0dc28eb5224836574b154db9e4a70d4be670ec0b6d",
        "certified_v1_predecessor_retained": "8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7",
    }
    return _definition(payload)


def verify_authority_definition(persisted: Mapping[str, Any]) -> None:
    if dict(persisted) != authority_definition():
        raise EtfCalendarAuthorityError("persisted authority does not reproduce")
    _verify_definition_digest(persisted)


def _verify_definition_digest(payload: Mapping[str, Any]) -> None:
    row = dict(payload)
    declared = row.pop("definition_sha256", None)
    if not _is_sha256(declared) or _digest(row) != declared:
        raise EtfCalendarAuthorityError("definition_sha256 does not recompute")


def _report_markdown(protocol: Mapping[str, Any]) -> str:
    lines = [
        f"# {AUTHORITY_VERSION}", "",
        f"- Ticket: `{PROGRAM_TICKET}`", f"- Definition hash: `{protocol['definition_sha256']}`",
        f"- Status: `{AUTHORITY_STATUS}`", f"- Classification: `{FINAL_CLASSIFICATION}`",
        f"- Material children: {protocol['material_child_count']}", "",
        "## Frozen decision", "",
        "ETF publication-date eligibility is the intersection of the NYSE Arca, Nasdaq,",
        "and Cboe BZX U.S. equity session calendars. Regular and early-close sessions",
        "are expected; full closures are not. Weekends are closed independently. Any",
        "missing, invalid, or unresolved conflicting official evidence fails closed.", "",
        "Calendar evidence is append-only, PIT-selected by `available_at`, and binds exact",
        "official-source bytes, their digest, a normalized schedule digest, and each",
        "replayed venue/date row. Mutable URLs and third-party calendars are not authority.", "",
        "## Non-persistent official-source verification (2026-09-13)", "",
        "- NYSE / NYSE Arca: the official Holidays & Trading Hours page identifies",
        "  regular NYSE Arca equity hours, 2026 full-day closures, and the November 27",
        "  and December 24 early closes:",
        "  https://www.nyse.com/trade/hours-calendars",
        "- Nasdaq Trader: the official 2026 U.S. Equity and Options Markets calendar",
        "  identifies closed dates and the two 1:00 p.m. early closes:",
        "  https://www.nasdaqtrader.com/Trader.aspx?id=calendar",
        "- Cboe: the official U.S. Equities Hours & Holidays page identifies BZX regular",
        "  trading hours, full closures, and the two 2026 equities early closes; official",
        "  schedule-update notices provide the frozen extraordinary-change source class:",
        "  https://www.cboe.com/about/hours",
        "- This verification did not persist live pages as calendar evidence. Operational",
        "  rows become authority only through the source-snapshot and extraction contracts.", "",
        "## Material child hashes", "", "| child | definition hash |", "| --- | --- |",
    ]
    for child, sha256 in sorted(protocol["child_definition_sha256"].items()):
        lines.append(f"| `{child}` | `{sha256}` |")
    lines += ["", "## Safety", "", "No prospective observation was collected. The failed V2 corpus was not changed", "or certified. POSTP1-003R3, POSTP1-004, collection, and BTC-019 remain blocked.", ""]
    return "\n".join(lines)


def write_artifacts(output_dir: Path) -> dict[str, Any]:
    protocol = authority_definition()
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {PROTOCOL_FILENAME: protocol}
    payloads.update(
        {filename: globals()[builder]() for filename, builder in _CHILD_ARTIFACTS}
    )
    for filename, payload in payloads.items():
        (output_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii"
        )
    (output_dir / REPORT_FILENAME).write_text(
        _report_markdown(protocol), encoding="utf-8"
    )
    return protocol


def restore_artifacts(output_dir: Path) -> dict[str, Any]:
    protocol = json.loads((output_dir / PROTOCOL_FILENAME).read_text(encoding="ascii"))
    verify_authority_definition(protocol)
    for filename, builder in _CHILD_ARTIFACTS:
        persisted = json.loads((output_dir / filename).read_text(encoding="ascii"))
        expected = globals()[builder]()
        if persisted != expected:
            raise EtfCalendarAuthorityError(f"persisted {filename} does not reproduce")
        _verify_definition_digest(persisted)
        key = filename.removesuffix(".json")
        if protocol["child_definition_sha256"].get(key) != expected["definition_sha256"]:
            raise EtfCalendarAuthorityError(f"authority does not bind {filename}")
    if (output_dir / REPORT_FILENAME).read_text(encoding="utf-8") != _report_markdown(protocol):
        raise EtfCalendarAuthorityError("persisted report does not reproduce")
    return protocol


def main() -> None:  # pragma: no cover - artifact writer
    root = Path(__file__).resolve().parents[2]
    print(write_artifacts(root / OUTPUT_NAMESPACE)["definition_sha256"])


if __name__ == "__main__":  # pragma: no cover
    main()
