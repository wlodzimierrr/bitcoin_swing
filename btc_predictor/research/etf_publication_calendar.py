"""Frozen pre-data authority for U.S. spot-Bitcoin-ETF publication dates.

The low-level ETF feature owners intentionally retain their historical
``market_holidays`` argument.  Scientific callers use this module to derive
that argument from append-only, content-addressed official-exchange evidence.
No live source is consulted during replay.
"""

from __future__ import annotations

import base64
import ast
import hashlib
import inspect
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from btc_predictor.data import EtfFlow, require_utc_datetime
from btc_predictor.features import flow as _flow
from btc_predictor.research import etf_calendar_semantics as _semantics


AUTHORITY_VERSION = "ETF_PUBLICATION_CALENDAR_AUTHORITY_V1"
PROGRAM_TICKET = "POSTP1-001V2A-R1"
WORKSTREAM = "EPIC X"
WORKSTREAM_NAME = "PROSPECTIVE INTEGRATION EVIDENCE"
AUTHORITY_STATUS = "CORRECTED_FROZEN_PRE_DATA_ETF_CALENDAR_AUTHORITY_AWAITING_REPEAT_XHIGH_REVIEW"
FINAL_CLASSIFICATION = "ETF_PUBLICATION_CALENDAR_AUTHORITY_V1_READY_FOR_REPEAT_XHIGH_REVIEW"
CERTIFICATION_STATE = "NOT_CERTIFIED_AWAITING_REPEAT_INDEPENDENT_EXACT_HASH_XHIGH_REVIEW"
OUTPUT_NAMESPACE = "prospective_evidence/etf_publication_calendar_authority_v1_r1"
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

FAILED_AUTHORITY_SHA256 = "a1ceb66bc0f6b90066d3da123447ae6e7dd983047adf363790336bfb557db0b9"

SOURCE_AUTHORITY_REGISTRY: dict[str, dict[str, Any]] = {
    "NYSE_ARCA": {
        "source_authority_id": "NYSE_ARCA_OFFICIAL_TRADING_CALENDAR",
        "source_class": "NYSE / NYSE Arca official Holidays & Trading Hours / annual trading calendar",
        "allowed_https_hostnames": ["www.nyse.com"],
        "allowed_paths": ["/trade/hours-calendars", "/markets/hours-calendars"],
        "allowed_query": {},
        "allowed_redirect_targets": ["https://www.nyse.com/trade/hours-calendars"],
        "document_types": ["text/html"],
        "product_scope": "NYSE Arca Equities annual trading calendar",
        "parser_id": "NYSE_HOLIDAYS_TRADING_HOURS_HTML",
        "parser_version": "1",
        "required_content_markers": ["Holidays & Trading Hours", "NYSE Arca Equities"],
        "coverage_semantics": "each explicit year column covers exactly that civil year",
    },
    "NASDAQ": {
        "source_authority_id": "NASDAQ_TRADER_US_EQUITIES_CALENDAR",
        "source_class": "Nasdaq Trader official U.S. Equity and Options Markets Trading Calendar",
        "allowed_https_hostnames": ["www.nasdaqtrader.com"],
        "allowed_paths": ["/Trader.aspx"],
        "allowed_query": {"id": ["calendar"]},
        "allowed_redirect_targets": [],
        "document_types": ["text/html"],
        "product_scope": "Nasdaq U.S. Equity and Options Markets annual calendar",
        "parser_id": "NASDAQ_TRADER_US_EQUITIES_HTML",
        "parser_version": "1",
        "required_content_markers": ["U.S. Equity and Options Markets Holiday Schedule", "NasdaqTrader.com"],
        "coverage_semantics": "the single explicit heading year covers exactly that civil year",
    },
    "CBOE_BZX": {
        "source_authority_id": "CBOE_US_EQUITIES_HOURS_HOLIDAYS",
        "source_class": "Cboe official U.S. Equities Hours & Holidays / schedule-update notices",
        "allowed_https_hostnames": ["www.cboe.com"],
        "allowed_paths": ["/about/hours", "/about/hours/", "/en/about/hours/"],
        "allowed_query": {},
        "allowed_redirect_targets": ["https://www.cboe.com/en/about/hours/"],
        "document_types": ["text/html"],
        "product_scope": "Cboe BZX U.S. Equities annual calendar",
        "parser_id": "CBOE_BZX_US_EQUITIES_NEXTJS_HTML",
        "parser_version": "1",
        "required_content_markers": ["Cboe BZX and EDGX Equities Trading Hours", "Equities Holiday Schedule"],
        "coverage_semantics": "the single explicit equities schedule year covers exactly that civil year",
    },
}

SOURCE_SNAPSHOT_KIND = "ETF_OFFICIAL_CALENDAR_HTTP_ACQUISITION_V1"
NORMALIZED_SCHEDULE_KIND = "ETF_NORMALIZED_VENUE_SCHEDULE_V1"
VENUE_SESSION_RECORD_KIND = "ETF_VENUE_SESSION_CALENDAR_RECORD_V1"
NORMALIZATION_METHOD = "FROZEN_SOURCE_PROFILE_PARSER_REPLAY_V1"
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
    """Append-only store admitting only fully validated scientific records."""

    def __init__(self, records: Iterable[Mapping[str, Any]] = ()) -> None:
        self._records: dict[str, dict[str, Any]] = {}
        for record in records:
            self.put(record)

    def put(self, record: Mapping[str, Any]) -> str:
        payload = dict(record)
        if RECORD_DIGEST_FIELD not in payload:
            raise EtfCalendarAuthorityError("scientific records require a declared digest")
        _verify_record(payload)
        kind = payload.get("record_kind")
        if kind == SOURCE_SNAPSHOT_KIND:
            _verify_source_snapshot(payload)
        elif kind == NORMALIZED_SCHEDULE_KIND:
            _verify_schedule_record(self, payload)
        elif kind == VENUE_SESSION_RECORD_KIND:
            _verify_venue_row(self, payload)
        else:
            raise EtfCalendarAuthorityError("unknown scientific record kind")
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


def _profile_for_url(url: str) -> tuple[str, dict[str, Any]]:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.fragment:
        raise EtfCalendarAuthorityError("official acquisition URLs must be uncredentialed HTTPS")
    hostname = (parsed.hostname or "").lower()
    query = {key.lower(): [item.lower() for item in values] for key, values in parse_qs(parsed.query).items()}
    matches: list[tuple[str, dict[str, Any]]] = []
    for venue, profile in SOURCE_AUTHORITY_REGISTRY.items():
        if hostname not in profile["allowed_https_hostnames"]:
            continue
        if parsed.path not in profile["allowed_paths"]:
            continue
        expected_query = profile["allowed_query"]
        if query != expected_query:
            continue
        matches.append((venue, profile))
    if len(matches) != 1:
        raise EtfCalendarAuthorityError("URL must resolve to exactly one frozen source profile")
    return matches[0]


def _validate_profile_urls(
    request_url: str, final_url: str, redirect_chain: Sequence[str]
) -> tuple[str, dict[str, Any]]:
    venue, profile = _profile_for_url(final_url)
    request_venue, request_profile = _profile_for_url(request_url)
    if request_venue != venue:
        raise EtfCalendarAuthorityError("redirect crosses frozen source-profile scope")
    if not isinstance(redirect_chain, (list, tuple)) or any(
        not isinstance(url, str) or urlsplit(url).scheme != "https"
        for url in redirect_chain
    ):
        raise EtfCalendarAuthorityError("redirect chain must contain only HTTPS URLs")
    if request_url == final_url:
        if redirect_chain:
            raise EtfCalendarAuthorityError("redirect chain supplied without a redirect")
    elif (
        not redirect_chain
        or redirect_chain[-1] != final_url
        or final_url not in request_profile["allowed_redirect_targets"]
    ):
        raise EtfCalendarAuthorityError("redirect target is not frozen for the source profile")
    return venue, profile


def _semantic_ast_sha256() -> str:
    sources = {"etf_calendar_semantics_module": inspect.getsource(_semantics)}
    for name in (
        "_canonical_json",
        "_digest",
        "_parse_date",
        "_parse_utc",
        "_record",
        "_verify_record",
        "CalendarEvidenceStore",
        "_profile_for_url",
        "_validate_profile_urls",
        "_response_bytes",
        "official_calendar_http_acquisition_record",
        "_verify_source_snapshot",
        "_derive_source_semantic",
        "_verify_schedule_record",
        "venue_session_calendar_record",
        "_verify_venue_row",
        "venue_session_status",
        "common_etf_session_status",
        "derive_etf_window_calendar",
        "scientific_etf_flow_window",
    ):
        owner = globals().get(name)
        if not callable(owner):
            raise EtfCalendarAuthorityError(f"executable semantic owner {name} is missing")
        sources[name] = inspect.getsource(owner)
    return _normalized_python_ast_sha256(sources)


def _normalized_python_ast_sha256(sources: Mapping[str, str]) -> str:
    normalized = [
        {
            "owner": name,
            "ast": ast.dump(ast.parse(source), annotate_fields=True, include_attributes=False),
        }
        for name, source in sorted(sources.items())
    ]
    return _digest(normalized)


def _response_bytes(row: Mapping[str, Any]) -> bytes:
    try:
        raw = base64.b64decode(row["response_body_base64"], validate=True)
    except Exception as error:
        raise EtfCalendarAuthorityError("acquisition response bytes are invalid") from error
    if not raw or hashlib.sha256(raw).hexdigest() != row.get("response_sha256"):
        raise EtfCalendarAuthorityError("response SHA-256 does not recompute")
    return raw


def official_calendar_http_acquisition_record(
    *,
    request_url: str,
    final_url: str,
    response_bytes: bytes,
    response_received_at: datetime,
    acquired_at: datetime,
    redirect_chain: Sequence[str] = (),
    http_method: str = "GET",
    http_status: int = 200,
    response_content_type: str = "text/html; charset=utf-8",
    response_headers: Mapping[str, str] | None = None,
    published_at: datetime | None = None,
) -> dict[str, Any]:
    """Create validated HTTP evidence; venue identity is never caller supplied."""

    if http_method != "GET" or type(http_status) is not int or http_status != 200:
        raise EtfCalendarAuthorityError("only successful official HTTPS GET responses are supported")
    chain = list(redirect_chain)
    venue_id, profile = _validate_profile_urls(request_url, final_url, chain)
    media_type = response_content_type.split(";", 1)[0].strip().lower()
    if media_type not in profile["document_types"]:
        raise EtfCalendarAuthorityError("unsupported official response content type")
    if not isinstance(response_bytes, bytes) or not response_bytes:
        raise EtfCalendarAuthorityError("exact nonempty response bytes are required")
    received = _parse_utc(response_received_at, "response_received_at")
    acquired = _parse_utc(acquired_at, "acquired_at")
    if acquired != received:
        raise EtfCalendarAuthorityError("acquired_at must equal response_received_at")
    published = _parse_utc(published_at, "published_at") if published_at is not None else None
    if published is not None and published > acquired:
        raise EtfCalendarAuthorityError("published_at may not exceed acquired_at")
    normalized_headers: dict[str, str] = {}
    for key, value in (response_headers or {}).items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise EtfCalendarAuthorityError("response headers must be strings")
        if key.lower() in {"content-length", "etag"}:
            normalized_headers[key.lower()] = value
    executable_sha = _semantic_ast_sha256()
    payload: dict[str, Any] = {
        "record_kind": SOURCE_SNAPSHOT_KIND,
        "schema_version": 1,
        "request_url": request_url,
        "final_url": final_url,
        "redirect_chain": chain,
        "http_method": http_method,
        "http_status": http_status,
        "response_content_type": response_content_type,
        "response_headers": dict(sorted(normalized_headers.items())),
        "response_body_base64": base64.b64encode(response_bytes).decode("ascii"),
        "response_sha256": hashlib.sha256(response_bytes).hexdigest(),
        "source_profile_id": f"{venue_id}_OFFICIAL_SOURCE_PROFILE_V1",
        "venue_id": venue_id,
        "source_authority_id": profile["source_authority_id"],
        "parser_id": profile["parser_id"],
        "parser_version": profile["parser_version"],
        "published_at": published.isoformat() if published is not None else None,
        "response_received_at": received.isoformat(),
        "acquired_at": acquired.isoformat(),
        "available_at": acquired.isoformat(),
        "executable_semantic_sha256": executable_sha,
    }
    provisional = _record(payload)
    try:
        semantic = _semantics.derive_schedule(
            profile["parser_id"], response_bytes, provisional[RECORD_DIGEST_FIELD]
        )
    except _semantics.CalendarSourceFormatError as error:
        raise EtfCalendarAuthorityError(str(error)) from error
    if semantic["venue_id"] != venue_id:
        raise EtfCalendarAuthorityError("source content product scope conflicts with URL profile")
    return provisional


# The failed naked-byte constructor remains unavailable to scientific callers.
def official_source_snapshot_record(**kwargs: Any) -> dict[str, Any]:
    del kwargs
    raise EtfCalendarAuthorityError(
        "naked-byte source snapshots are non-authoritative; use validated HTTP acquisition"
    )


def derive_normalized_schedule_from_official_source(
    store: CalendarEvidenceStore,
    *,
    acquisition_record_sha256: str,
) -> dict[str, Any]:
    """Derive every normalized claim by replaying the frozen parser."""

    source = _verify_source_snapshot(store.get(acquisition_record_sha256))
    schedule_core = _derive_source_semantic(source)
    payload = {
        "record_kind": NORMALIZED_SCHEDULE_KIND,
        "schema_version": 1,
        "venue_id": source["venue_id"],
        "source_authority_id": source["source_authority_id"],
        "source_acquisition_sha256": acquisition_record_sha256,
        "response_sha256": source["response_sha256"],
        "normalization_method": NORMALIZATION_METHOD,
        "normalized_schedule": schedule_core,
        "normalized_schedule_sha256": _digest(schedule_core),
        "parser_id": source["parser_id"],
        "parser_version": source["parser_version"],
        "executable_semantic_sha256": source["executable_semantic_sha256"],
        "available_at": source["available_at"],
        "acquired_at": source["acquired_at"],
    }
    return _record(payload)


def normalized_schedule_record(*args: Any, **kwargs: Any) -> dict[str, Any]:
    del args, kwargs
    raise EtfCalendarAuthorityError(
        "caller-authored coverage/exceptions are non-authoritative; replay official source"
    )


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
    try:
        status = _semantics.status_for_date(core, day)
    except _semantics.CalendarSourceFormatError as error:
        raise EtfCalendarAuthorityError(str(error)) from error
    source = _verify_source_snapshot(store.get(schedule["source_acquisition_sha256"]))
    return _record(
        {
            "record_kind": VENUE_SESSION_RECORD_KIND,
            "schema_version": 1,
            "venue_id": schedule["venue_id"],
            "trade_date": day.isoformat(),
            "session_status": status,
            "source_authority_id": schedule["source_authority_id"],
            "source_profile_id": source["source_profile_id"],
            "response_sha256": source["response_sha256"],
            "source_acquisition_sha256": schedule["source_acquisition_sha256"],
            "normalized_schedule_sha256": normalized_schedule_sha256,
            "normalized_schedule_content_sha256": schedule[
                "normalized_schedule_sha256"
            ],
            "published_at": source["published_at"],
            "response_received_at": source["response_received_at"],
            "acquired_at": source["acquired_at"],
            "available_at": schedule["available_at"],
        }
    )


def _verify_source_snapshot(record: Mapping[str, Any]) -> dict[str, Any]:
    row = _verify_record(record)
    required = {
        "record_kind", "schema_version", "request_url", "final_url", "redirect_chain",
        "http_method", "http_status", "response_content_type", "response_headers",
        "response_body_base64", "response_sha256", "source_profile_id", "venue_id",
        "source_authority_id", "parser_id", "parser_version", "published_at",
        "response_received_at", "acquired_at", "available_at",
        "executable_semantic_sha256", RECORD_DIGEST_FIELD,
    }
    if (
        set(row) != required
        or row.get("record_kind") != SOURCE_SNAPSHOT_KIND
        or row.get("schema_version") != 1
    ):
        raise EtfCalendarAuthorityError("invalid official source snapshot")
    venue, expected = _validate_profile_urls(
        row["request_url"], row["final_url"], row["redirect_chain"]
    )
    if row.get("venue_id") != venue:
        raise EtfCalendarAuthorityError("source venue does not derive from its URL profile")
    if row.get("source_profile_id") != f"{venue}_OFFICIAL_SOURCE_PROFILE_V1":
        raise EtfCalendarAuthorityError("wrong source profile identity")
    if row.get("source_authority_id") != expected["source_authority_id"]:
        raise EtfCalendarAuthorityError("wrong source authority for venue")
    if row.get("parser_id") != expected["parser_id"] or row.get("parser_version") != expected["parser_version"]:
        raise EtfCalendarAuthorityError("wrong frozen parser identity")
    if row.get("http_method") != "GET" or row.get("http_status") != 200:
        raise EtfCalendarAuthorityError("unsupported HTTP acquisition")
    headers = row.get("response_headers")
    if not isinstance(headers, dict) or any(
        key not in {"content-length", "etag"}
        or not isinstance(value, str)
        for key, value in headers.items()
    ):
        raise EtfCalendarAuthorityError("invalid persisted response headers")
    if row.get("response_content_type").split(";", 1)[0].strip().lower() not in expected["document_types"]:
        raise EtfCalendarAuthorityError("unsupported response content type")
    raw = _response_bytes(row)
    acquired = _parse_utc(row.get("acquired_at"), "acquired_at")
    received = _parse_utc(row.get("response_received_at"), "response_received_at")
    available = _parse_utc(row.get("available_at"), "available_at")
    if not acquired == received == available:
        raise EtfCalendarAuthorityError("scientific availability must equal actual acquisition receipt")
    published = row.get("published_at")
    if published is not None and _parse_utc(published, "published_at") > acquired:
        raise EtfCalendarAuthorityError("published_at may not exceed acquired_at")
    if row.get("executable_semantic_sha256") != _semantic_ast_sha256():
        raise EtfCalendarAuthorityError("runtime executable semantic attestation mismatch")
    semantic = _derive_source_semantic(row, raw=raw)
    if semantic["venue_id"] != venue:
        raise EtfCalendarAuthorityError("source product scope conflicts with URL profile")
    return row


def _derive_source_semantic(source: Mapping[str, Any], *, raw: bytes | None = None) -> dict[str, Any]:
    try:
        return _semantics.derive_schedule(
            source["parser_id"], raw if raw is not None else _response_bytes(source), source[RECORD_DIGEST_FIELD]
        )
    except _semantics.CalendarSourceFormatError as error:
        raise EtfCalendarAuthorityError(str(error)) from error


def _verify_schedule(store: CalendarEvidenceStore, sha256: str) -> dict[str, Any]:
    return _verify_schedule_record(store, store.get(sha256))


def _verify_schedule_record(store: CalendarEvidenceStore, record: Mapping[str, Any]) -> dict[str, Any]:
    row = _verify_record(record)
    required = {
        "record_kind", "schema_version", "venue_id", "source_authority_id",
        "source_acquisition_sha256", "response_sha256", "normalization_method",
        "normalized_schedule", "normalized_schedule_sha256", "parser_id",
        "parser_version", "executable_semantic_sha256", "available_at",
        "acquired_at", RECORD_DIGEST_FIELD,
    }
    if (
        set(row) != required
        or row.get("record_kind") != NORMALIZED_SCHEDULE_KIND
        or row.get("schema_version") != 1
        or row.get("normalization_method") != NORMALIZATION_METHOD
    ):
        raise EtfCalendarAuthorityError("reference is not a normalized schedule")
    source = _verify_source_snapshot(store.get(row.get("source_acquisition_sha256")))
    if row.get("venue_id") != source["venue_id"]:
        raise EtfCalendarAuthorityError("schedule venue does not match source")
    if row.get("source_authority_id") != source["source_authority_id"]:
        raise EtfCalendarAuthorityError("schedule source authority does not match")
    if row.get("response_sha256") != source["response_sha256"]:
        raise EtfCalendarAuthorityError("schedule substituted its source response")
    if _digest(row.get("normalized_schedule")) != row.get("normalized_schedule_sha256"):
        raise EtfCalendarAuthorityError("normalized schedule digest does not recompute")
    regenerated = _derive_source_semantic(source)
    if row.get("normalized_schedule") != regenerated:
        raise EtfCalendarAuthorityError("normalized schedule does not replay from source")
    if row.get("parser_id") != source["parser_id"] or row.get("parser_version") != source["parser_version"]:
        raise EtfCalendarAuthorityError("schedule parser identity mismatch")
    if row.get("available_at") != source["available_at"] or row.get("acquired_at") != source["acquired_at"]:
        raise EtfCalendarAuthorityError("schedule availability does not derive from acquisition")
    if row.get("executable_semantic_sha256") != _semantic_ast_sha256():
        raise EtfCalendarAuthorityError("runtime executable semantic attestation mismatch")
    return row


def validate_normalized_schedule_against_source(
    store: CalendarEvidenceStore, normalized_schedule_sha256: str
) -> dict[str, Any]:
    return _verify_schedule(store, normalized_schedule_sha256)


def _verify_venue_row(store: CalendarEvidenceStore, record: Mapping[str, Any]) -> dict[str, Any]:
    row = _verify_record(record)
    required = {
        "record_kind", "schema_version", "venue_id", "trade_date", "session_status",
        "source_authority_id", "source_profile_id", "response_sha256",
        "source_acquisition_sha256", "normalized_schedule_sha256",
        "normalized_schedule_content_sha256", "published_at", "response_received_at",
        "acquired_at", "available_at", RECORD_DIGEST_FIELD,
    }
    if set(row) != required or row.get("record_kind") != VENUE_SESSION_RECORD_KIND:
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
    for raw in evidence_store.records(record_kind=VENUE_SESSION_RECORD_KIND):
        if raw.get("venue_id") != venue or raw.get("trade_date") != day.isoformat():
            continue
        # Store admission has already established strict schema.  Apply PIT
        # eligibility before replay so future evidence cannot affect the past,
        # including after a later runtime semantic drift.
        if _parse_utc(raw.get("available_at"), "available_at") > cutoff:
            continue
        candidates.append(_verify_venue_row(evidence_store, raw))
    candidates = _semantics.select_latest_pit_rows(candidates, cutoff)
    if not candidates:
        return VenueSessionResolution(
            venue, day, UNRESOLVED, reason_codes=("VENUE_CALENDAR_EVIDENCE_MISSING",)
        )
    states = {row["session_status"] for row in candidates}
    if len(states) != 1:
        return VenueSessionResolution(
            venue, day, UNRESOLVED, reason_codes=("CONFLICTING_LATEST_CALENDAR_REVISION",)
        )
    selected = max(candidates, key=lambda row: row[RECORD_DIGEST_FIELD])
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
    reduced = _semantics.reduce_common_session(tuple(row.state for row in resolutions))
    if reduced == UNRESOLVED:
        reasons = tuple(
            sorted({reason for row in resolutions for reason in row.reason_codes})
        )
        return CommonSessionResolution(day, UNRESOLVED, venue_states, reasons)
    return CommonSessionResolution(day, reduced, venue_states)


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
            "contract_version": "ETF_CALENDAR_OFFICIAL_SOURCE_PROFILE_REGISTRY_V1",
            "canonical_venue_set": list(CANONICAL_VENUES),
            "dynamic_venue_addition": "REFUSE_REQUIRES_NEW_AUTHORITY_VERSION",
            "source_profiles": SOURCE_AUTHORITY_REGISTRY,
            "profile_resolution": "request/final HTTPS URL resolves exactly one profile; venue and authority derive from it",
            "venue_supplied_by_caller": False,
            "dynamic_source_discovery": False,
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
                "source_profile_id", "response_sha256", "source_acquisition_sha256",
                "normalized_schedule_sha256", "published_at", "response_received_at",
                "acquired_at", "available_at", "record_sha256",
            ],
            "session_statuses": list(SESSION_STATUSES),
            "early_close_collapsed_into_closed": False,
            "append_only": True,
            "validation": "replay exact acquisition, parser-derived schedule, and venue/date status",
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
            "query_order": [
                "strict scientific records only", "exact venue/date", "available_at <= decision_time",
                "latest-time conflict resolution", "source/schedule replay", "derive status",
            ],
            "available_at": "response_received_at == acquired_at; caller cannot supply it",
            "extraordinary_closure_rule": "effective only when official notice is available",
            "overwrite": "FORBIDDEN_APPEND_ONLY",
        }
    )


def official_source_snapshot_contract() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": SOURCE_SNAPSHOT_KIND,
            "authority": "validated HTTPS acquisition envelope + exact response bytes + frozen profile/parser",
            "method": "GET",
            "successful_statuses": [200],
            "https_only": True,
            "url_alone_sufficient": False,
            "naked_bytes_constructor_authoritative": False,
            "scientific_available_at": "response_received_at == acquired_at == available_at",
            "published_at": "informational only; null unless reliable; when present <= acquired_at",
            "clock_integrity": (
                "future POSTP1-004 collector must bind response receipt to existing "
                "PROSPECTIVE_CLOCK_INTEGRITY_V1; this standalone pre-data authority "
                "enforces that availability cannot precede local receipt/acquisition"
            ),
            "manual_date_without_source_evidence_authoritative": False,
            "minimum_bindings": [
                "request/final URL", "redirect chain", "HTTP method/status/content type",
                "exact response bytes and SHA-256", "source profile/venue/authority",
                "response_received_at/acquired_at", "executable semantic identity",
            ],
            "external_source_change_mutates_persisted_evidence": False,
        }
    )


def source_parser_registry_contract() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_SOURCE_FORMAT_PARSER_REGISTRY_V1",
            "parsers": {
                venue: {
                    "parser_id": profile["parser_id"],
                    "parser_version": profile["parser_version"],
                    "recognition": profile["required_content_markers"],
                    "product_scope": profile["product_scope"],
                    "coverage_derivation": profile["coverage_semantics"],
                    "closure_extraction": "explicit Closed/holiday table rows",
                    "early_close_extraction": "explicit early-close rows/notices only",
                    "regular_default": "remaining weekdays only inside explicit annual coverage",
                    "unknown_or_ambiguous": "UNSUPPORTED_SOURCE_FORMAT_REFUSE",
                }
                for venue, profile in SOURCE_AUTHORITY_REGISTRY.items()
            },
        }
    )


def normalized_schedule_contract() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": NORMALIZED_SCHEDULE_KIND,
            "method": NORMALIZATION_METHOD,
            "inputs": ["validated acquisition record SHA-256"],
            "caller_coverage": "PROHIBITED",
            "caller_exceptions": "PROHIBITED",
            "outputs": [
                "venue", "acquisition SHA", "supported coverage intervals",
                "full closures", "early closes", "source-supported weekday default",
                "parser ID/version",
            ],
            "validator": "rerun acquisition validation and parser; exact semantic object/digest equality",
            "missing_or_unsupported_coverage": UNRESOLVED,
        }
    )


def executable_semantic_manifest_contract() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_EXECUTABLE_SEMANTIC_MANIFEST_V1",
            "identity_method": "SHA-256 of normalized Python AST; locations excluded",
            "semantic_module": "btc_predictor.research.etf_calendar_semantics",
            "normalized_ast_sha256": _semantic_ast_sha256(),
            "owners": [
                "source profile resolver", "NYSE parser", "Nasdaq parser", "Cboe parser",
                "normalized schedule validator", "venue-row derivation", "PIT revision selector",
                "common-session reducer", "ETF adapter",
            ],
            "runtime_mismatch": "REFUSE_SCIENTIFIC_REPLAY",
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
            "etf_flow_revision_semantics_changed": False,
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
            "venue_scope_changed": 0,
            "intersection_semantics_changed": 0,
            "early_close_treatment_changed": 0,
            "stage_b_metrics_changed": 0,
            "risk_stops_thresholds_changed": 0,
        }
    )


def _definition(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result["definition_sha256"] = _digest(result)
    return result


_CHILD_ARTIFACTS: tuple[tuple[str, str], ...] = (
    ("official_source_profile_registry.json", "venue_authority_registry_contract"),
    ("http_acquisition_schema.json", "official_source_snapshot_contract"),
    ("source_parser_registry.json", "source_parser_registry_contract"),
    ("normalized_schedule_contract.json", "normalized_schedule_contract"),
    ("venue_session_record_schema.json", "venue_session_record_schema_contract"),
    ("pit_revision_rule.json", "pit_revision_rule_contract"),
    ("common_session_rule.json", "common_session_rule_contract"),
    ("etf_feature_adapter_contract.json", "etf_feature_adapter_contract"),
    ("authority_completion_semantic_diff.json", "authority_completion_semantic_diff_contract"),
    ("executable_semantic_manifest.json", "executable_semantic_manifest_contract"),
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
        "failed_authority_lineage": {
            "definition_sha256": FAILED_AUTHORITY_SHA256,
            "authoritative": False,
            "certified": False,
            "prospective_observations": 0,
            "superseded_before_use": True,
            "review_result": "FAIL — ETF CALENDAR SOURCE DERIVATION INVALID",
        },
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
        "Calendar evidence is append-only. A validated HTTPS acquisition binds request/final",
        "URLs, exact response bytes, receipt/acquisition time and a uniquely resolved frozen",
        "source profile. Venue, product scope, coverage, closures and early closes are then",
        "derived by the frozen source-specific parser; caller-authored schedules are refused.", "",
        "Scientific `available_at` equals response receipt and acquisition time. PIT filtering",
        "precedes revision replay, so future evidence cannot affect an earlier decision.",
        "The normalized AST of every parser/reducer/adapter owner is hash-bound and runtime",
        "replay refuses when the executable semantic identity differs.", "",
        "## Retained official fixtures (2026-09-13)", "",
        "Exact compressed response bytes and acquisition provenance for the NYSE, Nasdaq",
        "Trader and Cboe official formats used for certification are retained under",
        "`btc_predictor/tests/fixtures/etf_calendar/`. Their response SHA-256 values are",
        "validated before parser extraction. No fixture is a prospective strategy observation.", "",
        "## Failed lineage", "",
        f"The failed authority `{FAILED_AUTHORITY_SHA256}` remains non-authoritative,",
        "non-certified, unused, and preserved in its original artifact directory.", "",
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
