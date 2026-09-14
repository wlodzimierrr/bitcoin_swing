"""POSTP1-001V2A-R2 trusted-origin and parser-completeness tests."""

from __future__ import annotations

import base64
import gzip
import hashlib
import inspect
import json
import os
import re
import subprocess
import sys
from unittest.mock import patch
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from btc_predictor.data import EtfFlow
from btc_predictor.features import flow
from btc_predictor.research import etf_calendar_semantics as semantics
from btc_predictor.research import etf_publication_calendar as cal


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / cal.OUTPUT_NAMESPACE
FIXTURE_DIR = Path(__file__).with_name("fixtures") / "etf_calendar"
PROVENANCE = json.loads((FIXTURE_DIR / "official_fixture_provenance.json").read_text())
ACQUIRED = datetime.fromisoformat(PROVENANCE["acquired_at"])
DECISION = datetime(2026, 12, 31, tzinfo=UTC)
HOLIDAYS_2026 = {
    date(2026, 1, 1), date(2026, 1, 19), date(2026, 2, 16), date(2026, 4, 3),
    date(2026, 5, 25), date(2026, 6, 19), date(2026, 7, 3), date(2026, 9, 7),
    date(2026, 11, 26), date(2026, 12, 25),
}
EARLY_2026 = {date(2026, 11, 27), date(2026, 12, 24)}


def fixture_bytes(venue: str) -> bytes:
    encoded = (FIXTURE_DIR / PROVENANCE["fixtures"][venue]["fixture"]).read_bytes()
    return gzip.decompress(base64.b64decode(encoded))


def mutate_calendar_rows(venue: str, keep: tuple[int, ...]) -> bytes:
    document = fixture_bytes(venue).decode("utf-8")
    needle = {
        "NYSE_ARCA": "New Year’s Day",
        "NASDAQ": "New Years Day (Observed)",
        "CBOE_BZX": "New Year&#x27;s Day",
    }[venue]
    position = document.index(needle)
    table_start = document.rfind("<table", 0, position)
    table_end = document.index("</table>", position) + len("</table>")
    table = document[table_start:table_end]
    body_start = table.index("<tbody")
    body_content_start = table.index(">", body_start) + 1
    body_end = table.index("</tbody>", body_content_start)
    rows = re.findall(r"<tr\b.*?</tr>", table[body_content_start:body_end], flags=re.DOTALL)
    assert len(rows) >= 10
    replacement = "".join(rows[index] for index in keep)
    changed_table = table[:body_content_start] + replacement + table[body_end:]
    return (document[:table_start] + changed_table + document[table_end:]).encode("utf-8")


def duplicate_calendar_table(venue: str) -> bytes:
    document = fixture_bytes(venue).decode("utf-8")
    needle = {"NYSE_ARCA": "New Year’s Day", "NASDAQ": "New Years Day (Observed)", "CBOE_BZX": "New Year&#x27;s Day"}[venue]
    position = document.index(needle)
    start = document.rfind("<table", 0, position)
    end = document.index("</table>", position) + len("</table>")
    return (document[:end] + document[start:end] + document[end:]).encode("utf-8")


def acquisition(venue: str, *, acquired_at: datetime = ACQUIRED, body: bytes | None = None) -> dict:
    metadata = PROVENANCE["fixtures"][venue]
    observation = {
        "request_url": metadata["request_url"], "final_url": metadata["final_url"],
        "redirect_chain": (), "http_status": 200,
        "response_headers": {"Content-Type": metadata["response_content_type"]},
        "response_bytes": fixture_bytes(venue) if body is None else body,
    }
    executable_sha = cal._semantic_ast_sha256()
    with (
        patch.object(cal, "_perform_verified_https_get", return_value=observation),
        patch.object(cal, "_semantic_ast_sha256", return_value=executable_sha),
    ):
        return cal.collect_official_calendar(metadata["source_profile_id"], lambda: acquired_at)


def put_schedule(store: cal.CalendarEvidenceStore, venue: str, *, acquired_at: datetime = ACQUIRED, body: bytes | None = None) -> str:
    acquisition_sha = store.put(acquisition(venue, acquired_at=acquired_at, body=body))
    return store.put(cal.derive_normalized_schedule_from_official_source(
        store, acquisition_record_sha256=acquisition_sha
    ))


def populated_store(start: date = date(2026, 11, 1), end: date = date(2026, 12, 31)) -> cal.CalendarEvidenceStore:
    store = cal.CalendarEvidenceStore()
    for venue in cal.CANONICAL_VENUES:
        schedule_sha = put_schedule(store, venue)
        day = start
        while day <= end:
            if day.weekday() < 5:
                store.put(cal.venue_session_calendar_record(
                    store, normalized_schedule_sha256=schedule_sha, trade_date=day
                ))
            day += timedelta(days=1)
    return store


@pytest.fixture(scope="module")
def official_store() -> cal.CalendarEvidenceStore:
    return populated_store()


def flow_row(fund: str, day: date) -> EtfFlow:
    return EtfFlow(
        fund=fund, observation_date=day, flow_usd=Decimal("10"),
        aum_usd=Decimal("1000"), provider="synthetic", source="synthetic",
        revision="1",
        available_at=datetime.combine(day + timedelta(days=1), datetime.min.time(), UTC),
        ingested_at=datetime.combine(day + timedelta(days=1), datetime.min.time(), UTC),
    )


def rehash(row: dict) -> dict:
    row = dict(row)
    row.pop(cal.RECORD_DIGEST_FIELD, None)
    return cal._record(row)


def test_authority_scope_failed_lineage_and_safety_are_frozen() -> None:
    authority = cal.authority_definition()
    assert authority["authority_version"] == "ETF_PUBLICATION_CALENDAR_AUTHORITY_V1"
    assert authority["program_ticket"] == "POSTP1-001V2A-R2"
    assert authority["final_classification"] == "ETF_PUBLICATION_CALENDAR_AUTHORITY_V1_READY_FOR_FINAL_XHIGH_REVIEW"
    assert authority["certification"]["certified"] is False
    assert [row["definition_sha256"] for row in authority["failed_authority_lineage"]] == [
        cal.FAILED_AUTHORITY_SHA256, cal.FAILED_CORRECTED_AUTHORITY_SHA256,
    ]
    assert all(
        row["authoritative"] is False and row["certified"] is False
        and row["prospective_observations"] == 0 and row["superseded_before_use"] is True
        for row in authority["failed_authority_lineage"]
    )
    assert authority["safety"] == {
        "prospective_observations_collected": 0,
        "persistent_strategy_collection_started": False,
        "real_stage_b_evaluation": False, "v2_corrected_hash_issued": False,
        "v2_certified": False, "postp1_003r3_authorized": False,
        "postp1_004_authorized": False, "collection_authorized": False,
        "btc019_reopened": False, "btc019_sealed_data_accessed": False,
        "epic_t_modified": False,
    }


def test_material_children_are_mechanical_bound_and_digest_valid() -> None:
    authority, children = cal.authority_definition(), cal._children()
    assert authority["material_child_count"] == len(cal._CHILD_ARTIFACTS) == 12
    assert authority["child_definition_sha256"] == {
        name: payload["definition_sha256"] for name, payload in children.items()
    }
    for payload in children.values():
        cal._verify_definition_digest(payload)
    cal.verify_authority_definition(authority)


def test_every_material_child_mutation_moves_top_hash(monkeypatch) -> None:
    baseline = cal.authority_definition()["definition_sha256"]
    for _, builder_name in cal._CHILD_ARTIFACTS:
        original = getattr(cal, builder_name)
        def mutated(original=original, builder_name=builder_name):
            payload = original(); payload.pop("definition_sha256")
            payload["mutation"] = builder_name
            return cal._definition(payload)
        with monkeypatch.context() as context:
            context.setattr(cal, builder_name, mutated)
            assert cal.authority_definition()["definition_sha256"] != baseline


def test_official_fixture_provenance_and_exact_bytes() -> None:
    for venue, metadata in PROVENANCE["fixtures"].items():
        raw = fixture_bytes(venue)
        assert hashlib.sha256(raw).hexdigest() == metadata["response_sha256"]
        record = acquisition(venue)
        assert record["venue_id"] == venue
        assert record["source_profile_id"] == metadata["source_profile_id"]
        assert record["response_sha256"] == metadata["response_sha256"]
        assert base64.b64decode(record["response_body_base64"]) == raw
        assert record["acquisition_provenance"] == cal.TRUSTED_ACQUISITION_PROVENANCE


@pytest.mark.parametrize("venue", cal.CANONICAL_VENUES)
def test_fixture_bytes_are_explicitly_non_authoritative_and_store_refuses(venue: str) -> None:
    metadata = PROVENANCE["fixtures"][venue]
    fixture = cal.load_calendar_parser_fixture(metadata["source_profile_id"], fixture_bytes(venue))
    record = fixture["fixture_record"]
    assert record["acquisition_provenance"] == cal.FIXTURE_ACQUISITION_PROVENANCE
    with pytest.raises(cal.EtfCalendarAuthorityError, match="unknown scientific record kind"):
        cal.CalendarEvidenceStore().put(record)


def test_trusted_collector_builds_request_and_observes_response(monkeypatch) -> None:
    metadata = PROVENANCE["fixtures"]["NASDAQ"]
    calls: list[tuple[str, int]] = []

    class Response:
        status = 200
        headers = {"Content-Type": metadata["response_content_type"], "ETag": "fixture"}
        def __enter__(self): return self
        def __exit__(self, *args): return None
        def read(self): return fixture_bytes("NASDAQ")
        def geturl(self): return metadata["final_url"]

    class Opener:
        def open(self, request, timeout):
            calls.append((request.full_url, timeout))
            return Response()

    monkeypatch.setattr(cal, "build_opener", lambda *handlers: Opener())
    record = cal.collect_official_calendar(metadata["source_profile_id"], lambda: ACQUIRED)
    assert calls == [(metadata["request_url"], cal.HTTP_TIMEOUT_SECONDS)]
    assert record["request_url"] == metadata["request_url"]
    assert record["final_url"] == metadata["final_url"]
    assert record["response_sha256"] == metadata["response_sha256"]
    assert record["available_at"] == record["acquired_at"] == record["response_received_at"]


def test_venue_is_derived_and_naked_byte_constructor_refuses() -> None:
    assert tuple(inspect.signature(cal.collect_official_calendar).parameters) == ("profile_id", "receipt_clock")
    for forbidden in ("response_bytes", "http_status", "final_url", "redirect_chain", "response_headers", "transport", "session"):
        assert forbidden not in inspect.signature(cal.collect_official_calendar).parameters
    with pytest.raises(cal.EtfCalendarAuthorityError, match="caller HTTP evidence"):
        cal.official_calendar_http_acquisition_record(
            request_url="https://www.nyse.com/trade/hours-calendars",
            response_bytes=fixture_bytes("NYSE_ARCA"),
        )
    with pytest.raises(cal.EtfCalendarAuthorityError, match="naked-byte"):
        cal.official_source_snapshot_record(venue_id="NASDAQ", source_bytes=b"anything")
    with pytest.raises(cal.EtfCalendarAuthorityError, match="caller-authored"):
        cal.normalized_schedule_record(
            cal.CalendarEvidenceStore(), coverage_start=date(2026, 1, 1),
            coverage_end=date(2028, 12, 31), exceptions={},
        )


@pytest.mark.parametrize(("body_venue", "url_venue"), [
    ("NYSE_ARCA", "NASDAQ"), ("NASDAQ", "CBOE_BZX"), ("CBOE_BZX", "NYSE_ARCA")
])
def test_cross_venue_source_relabel_refuses(body_venue: str, url_venue: str) -> None:
    metadata = PROVENANCE["fixtures"][url_venue]
    with pytest.raises(cal.EtfCalendarAuthorityError):
        cal.load_calendar_parser_fixture(metadata["source_profile_id"], fixture_bytes(body_venue))


@pytest.mark.parametrize("venue", cal.CANONICAL_VENUES)
def test_source_derivation_exact_2026_schedule(venue: str) -> None:
    store = cal.CalendarEvidenceStore(); schedule_sha = put_schedule(store, venue)
    semantic = cal.validate_normalized_schedule_against_source(store, schedule_sha)["normalized_schedule"]
    assert {date.fromisoformat(x) for x in semantic["full_closure_dates"] if x.startswith("2026-")} == HOLIDAYS_2026
    assert {date.fromisoformat(x) for x in semantic["early_close_dates"] if x.startswith("2026-")} == EARLY_2026
    coverage = semantic["supported_coverage_intervals"]
    if venue == "NYSE_ARCA":
        assert [x["coverage_start"][:4] for x in coverage] == ["2026", "2027", "2028"]
    else:
        assert coverage == [{"coverage_start": "2026-01-01", "coverage_end": "2026-12-31"}]


@pytest.mark.parametrize("venue", cal.CANONICAL_VENUES)
@pytest.mark.parametrize("attack", ["invent_closure", "invent_early", "omit_closure", "omit_early", "empty", "coverage"])
def test_caller_schedule_forgery_refuses_even_when_rehashed(venue: str, attack: str) -> None:
    store = cal.CalendarEvidenceStore(); schedule_sha = put_schedule(store, venue)
    forged = store.get(schedule_sha); semantic = dict(forged["normalized_schedule"])
    semantic["full_closure_dates"] = list(semantic["full_closure_dates"])
    semantic["early_close_dates"] = list(semantic["early_close_dates"])
    semantic["supported_coverage_intervals"] = [dict(x) for x in semantic["supported_coverage_intervals"]]
    if attack == "invent_closure": semantic["full_closure_dates"].append("2026-08-25")
    elif attack == "invent_early": semantic["early_close_dates"].append("2026-08-25")
    elif attack == "omit_closure": semantic["full_closure_dates"].remove("2026-11-26")
    elif attack == "omit_early": semantic["early_close_dates"].remove("2026-11-27")
    elif attack == "empty": semantic["full_closure_dates"], semantic["early_close_dates"] = [], []
    else: semantic["supported_coverage_intervals"][-1]["coverage_end"] = "2029-12-31"
    forged["normalized_schedule"] = semantic
    forged["normalized_schedule_sha256"] = cal._digest(semantic)
    with pytest.raises(cal.EtfCalendarAuthorityError, match="does not replay"):
        store.put(rehash(forged))


@pytest.mark.parametrize("venue", cal.CANONICAL_VENUES)
def test_each_parser_fails_closed_on_partial_format(venue: str) -> None:
    raw = fixture_bytes(venue)
    with pytest.raises(cal.EtfCalendarAuthorityError):
        acquisition(venue, body=raw[: len(raw) // 2])


@pytest.mark.parametrize("venue", cal.CANONICAL_VENUES)
@pytest.mark.parametrize("attack", ["one", "three", "missing_last", "missing_first"])
def test_structurally_closed_but_incomplete_annual_tables_refuse(
    venue: str, attack: str,
) -> None:
    row_count = 10 if venue == "NYSE_ARCA" else 12
    selected = {
        "one": (0,), "three": (0, 1, 2),
        "missing_last": tuple(range(row_count - 1)),
        "missing_first": tuple(range(1, row_count)),
    }[attack]
    with pytest.raises(cal.EtfCalendarAuthorityError):
        acquisition(venue, body=mutate_calendar_rows(venue, selected))


@pytest.mark.parametrize(("venue", "missing_index"), [
    ("NYSE_ARCA", 5), ("NASDAQ", 5), ("NASDAQ", 9), ("NASDAQ", 10),
    ("CBOE_BZX", 5), ("CBOE_BZX", 9), ("CBOE_BZX", 10),
])
def test_middle_closure_and_each_table_early_close_omission_refuse(
    venue: str, missing_index: int,
) -> None:
    row_count = 10 if venue == "NYSE_ARCA" else 12
    keep = tuple(index for index in range(row_count) if index != missing_index)
    with pytest.raises(cal.EtfCalendarAuthorityError):
        acquisition(venue, body=mutate_calendar_rows(venue, keep))


@pytest.mark.parametrize("venue", cal.CANONICAL_VENUES)
def test_duplicate_supported_calendar_table_refuses(venue: str) -> None:
    with pytest.raises(cal.EtfCalendarAuthorityError, match="ambiguous"):
        acquisition(venue, body=duplicate_calendar_table(venue))


@pytest.mark.parametrize("venue", cal.CANONICAL_VENUES)
def test_trailing_unrelated_table_is_not_interpreted_as_calendar(venue: str) -> None:
    raw = fixture_bytes(venue)
    changed = raw.replace(b"</body>", b"<table><tbody><tr><td>unrelated</td></tr></tbody></table></body>", 1)
    assert acquisition(venue, body=changed)["venue_id"] == venue


@pytest.mark.parametrize("venue", cal.CANONICAL_VENUES)
def test_duplicate_and_unknown_calendar_rows_refuse(venue: str) -> None:
    row_count = 10 if venue == "NYSE_ARCA" else 12
    duplicate = mutate_calendar_rows(venue, tuple(range(row_count)) + (0,))
    with pytest.raises(cal.EtfCalendarAuthorityError):
        acquisition(venue, body=duplicate)
    unknown = fixture_bytes(venue).replace(
        {"NYSE_ARCA": "Good Friday", "NASDAQ": "Good Friday", "CBOE_BZX": "Good Friday"}[venue].encode(),
        b"Made Up Holiday",
        1,
    )
    with pytest.raises(cal.EtfCalendarAuthorityError):
        acquisition(venue, body=unknown)


def test_modified_nyse_early_close_prose_refuses_entire_source() -> None:
    raw = fixture_bytes("NYSE_ARCA")
    changed = raw.replace(b"Friday, November 26, 2027", b"Friday, Novembuary 99, 2027", 1)
    with pytest.raises(cal.EtfCalendarAuthorityError, match="parse completely"):
        acquisition("NYSE_ARCA", body=changed)


@pytest.mark.parametrize(("venue", "marker"), [
    ("NYSE_ARCA", b"NYSE Arca Equities"),
    ("NASDAQ", b"U.S. Equity and Options Markets Holiday Schedule 2026"),
    ("CBOE_BZX", b"Cboe BZX and EDGX Equities Trading Hours"),
])
def test_each_parser_fails_closed_on_wrong_product_scope(venue: str, marker: bytes) -> None:
    raw = fixture_bytes(venue)
    assert marker in raw
    with pytest.raises(cal.EtfCalendarAuthorityError):
        acquisition(venue, body=raw.replace(marker, b"WRONG PRODUCT SCOPE"))


@pytest.mark.parametrize("venue", cal.CANONICAL_VENUES)
def test_each_parser_fails_closed_on_malformed_date(venue: str) -> None:
    raw = fixture_bytes(venue)
    assert b"November 26" in raw
    with pytest.raises(cal.EtfCalendarAuthorityError):
        acquisition(venue, body=raw.replace(b"November 26", b"Novembuary 99"))


@pytest.mark.parametrize(("venue", "label"), [
    ("NYSE_ARCA", b"Each market will close early at 1:00 p.m."),
    ("NASDAQ", b"Early Close* - U.S."),
    ("CBOE_BZX", b"Thanksgiving Early Close"),
])
def test_each_parser_fails_closed_on_unknown_session_semantics(venue: str, label: bytes) -> None:
    raw = fixture_bytes(venue)
    assert label in raw
    with pytest.raises(cal.EtfCalendarAuthorityError):
        acquisition(venue, body=raw.replace(label, b"UNKNOWN SESSION LABEL"))


@pytest.mark.parametrize("url", [
    "http://www.nasdaqtrader.com/Trader.aspx?id=calendar",
    "https://www.nasdaqtrader.com:443/Trader.aspx?id=calendar",
    "https://www.nasdaqtrader.com:444/Trader.aspx?id=calendar",
    "https://www.nasdaqtrader.com:99999/Trader.aspx?id=calendar",
    "https://www.nasdaqtrader.com:evil/Trader.aspx?id=calendar",
    "https://www.nasdaqtrader.com/Trader.aspx?id=calendar&extra=1",
    "https://www.nasdaqtrader.com/Trader.aspx?id=calendar&=x",
    "https://www.nasdaqtrader.com/Trader.aspx?id=calendar&extra=",
    "https://www.nasdaqtrader.com/Trader.aspx?id=calendar&id=calendar",
    "https://www.nasdaqtrader.com/Trader.aspx?id=Calendar",
    "https://www.nasdaqtrader.com/Trader.aspx?id=%63alendar",
    "https://www.nasdaqtrader.com//Trader.aspx?id=calendar",
    "https://www.nasdaqtrader.com/a/../Trader.aspx?id=calendar",
    "https://www.nasdaqtrader.com/Trader.aspx/?id=calendar",
    "https://user@www.nasdaqtrader.com/Trader.aspx?id=calendar",
    "https://www.nasdaqtrader.com/Trader.aspx?id=calendar#fragment",
])
def test_noncanonical_url_variants_fail_closed(url: str) -> None:
    with pytest.raises(cal.EtfCalendarAuthorityError):
        cal._profile_for_url(url)


def test_bad_status_and_off_profile_redirects_fail_closed() -> None:
    record = acquisition("NASDAQ")
    record["http_status"] = 404
    with pytest.raises(cal.EtfCalendarAuthorityError):
        cal.CalendarEvidenceStore().put(rehash(record))
    request = PROVENANCE["fixtures"]["NASDAQ"]["request_url"]
    for chain, final in (
        (["https://evil.example/anything", request], request),
        (["http://www.nasdaqtrader.com/Trader.aspx?id=calendar"], request),
        (["https://www.nasdaqtrader.com/Trader.aspx?id=calendar&extra=1"], request),
    ):
        with pytest.raises(cal.EtfCalendarAuthorityError):
            cal._validate_profile_urls(request, final, chain)


def test_availability_is_acquisition_time_and_backdating_refuses() -> None:
    record = acquisition("NASDAQ")
    assert record["available_at"] == record["acquired_at"] == record["response_received_at"]
    assert "available_at" not in inspect.signature(cal.collect_official_calendar).parameters
    forged = dict(record); forged["available_at"] = "2020-01-01T00:00:00+00:00"
    with pytest.raises(cal.EtfCalendarAuthorityError, match="availability"):
        cal.CalendarEvidenceStore().put(rehash(forged))


def test_published_at_is_informational_and_future_refuses() -> None:
    record = acquisition("NASDAQ")
    assert record["published_at"] is None
    assert record["available_at"] == ACQUIRED.isoformat()
    forged = dict(record)
    forged["published_at"] = (ACQUIRED + timedelta(seconds=1)).isoformat()
    with pytest.raises(cal.EtfCalendarAuthorityError, match="published_at"):
        cal.CalendarEvidenceStore().put(rehash(forged))


def test_unknown_or_schema_invalid_future_records_refuse_at_insertion() -> None:
    store = cal.CalendarEvidenceStore()
    unknown = cal._record({"record_kind": "OPAQUE", "available_at": "2099-01-01T00:00:00+00:00"})
    with pytest.raises(cal.EtfCalendarAuthorityError, match="unknown"):
        store.put(unknown)
    malformed = acquisition("NASDAQ"); malformed["invented"] = True
    with pytest.raises(cal.EtfCalendarAuthorityError, match="invalid official"):
        store.put(rehash(malformed))


def test_malformed_future_source_schedule_and_venue_rows_cannot_change_past() -> None:
    day = date(2026, 11, 27); store = cal.CalendarEvidenceStore()
    schedule_sha = put_schedule(store, "NASDAQ")
    row = cal.venue_session_calendar_record(
        store, normalized_schedule_sha256=schedule_sha, trade_date=day
    )
    store.put(row)
    before = cal.venue_session_status("NASDAQ", day, DECISION, store)
    assert before.state == "OPEN_EARLY_CLOSE"

    malformed_source = acquisition("NASDAQ", acquired_at=datetime(2027, 1, 2, tzinfo=UTC))
    malformed_source["available_at"] = "2020-01-01T00:00:00+00:00"
    malformed_schedule = store.get(schedule_sha)
    malformed_schedule["available_at"] = "2099-01-01T00:00:00+00:00"
    malformed_row = dict(row)
    malformed_row["available_at"] = "2099-01-01T00:00:00+00:00"
    for malformed in (malformed_source, malformed_schedule, malformed_row):
        with pytest.raises(cal.EtfCalendarAuthorityError):
            store.put(rehash(malformed))
    assert cal.venue_session_status("NASDAQ", day, DECISION, store) == before


def test_future_valid_revision_does_not_leak_backward() -> None:
    day = date(2026, 11, 27); store = cal.CalendarEvidenceStore()
    schedule = put_schedule(store, "CBOE_BZX")
    store.put(cal.venue_session_calendar_record(store, normalized_schedule_sha256=schedule, trade_date=day))
    assert cal.venue_session_status("CBOE_BZX", day, DECISION, store).state == "OPEN_EARLY_CLOSE"
    future_time = datetime(2027, 1, 2, tzinfo=UTC)
    future_schedule = put_schedule(store, "CBOE_BZX", acquired_at=future_time)
    store.put(cal.venue_session_calendar_record(store, normalized_schedule_sha256=future_schedule, trade_date=day))
    assert cal.venue_session_status("CBOE_BZX", day, DECISION, store).state == "OPEN_EARLY_CLOSE"
    assert cal.venue_session_status("CBOE_BZX", day, future_time, store).state == "OPEN_EARLY_CLOSE"


def test_same_available_at_incompatible_valid_revisions_are_unresolved(monkeypatch) -> None:
    day = date(2026, 11, 27); store = cal.CalendarEvidenceStore()
    open_schedule = put_schedule(store, "CBOE_BZX")
    store.put(cal.venue_session_calendar_record(store, normalized_schedule_sha256=open_schedule, trade_date=day))
    original = next(iter(store.records(record_kind=cal.VENUE_SESSION_RECORD_KIND)))
    conflicting = dict(original)
    conflicting["session_status"] = "CLOSED"
    conflicting = rehash(conflicting)
    store._records[conflicting[cal.RECORD_DIGEST_FIELD]] = conflicting
    monkeypatch.setattr(cal, "_verify_venue_row", lambda evidence_store, row: dict(row))
    result = cal.venue_session_status("CBOE_BZX", day, DECISION, store)
    assert result.state == cal.UNRESOLVED
    assert result.reason_codes == ("CONFLICTING_LATEST_CALENDAR_REVISION",)


def test_forged_venue_row_refuses_even_when_rehashed() -> None:
    store = cal.CalendarEvidenceStore(); schedule = put_schedule(store, "NASDAQ")
    row = cal.venue_session_calendar_record(store, normalized_schedule_sha256=schedule, trade_date=date(2026, 8, 25))
    row["session_status"] = "CLOSED"
    with pytest.raises(cal.EtfCalendarAuthorityError, match="does not replay"):
        store.put(rehash(row))


@pytest.mark.parametrize(("day", "expected"), [
    (date(2026, 11, 25), cal.EXPECTED), (date(2026, 11, 28), cal.NOT_EXPECTED),
    (date(2026, 11, 26), cal.NOT_EXPECTED), (date(2026, 11, 27), cal.EXPECTED),
    (date(2026, 12, 24), cal.EXPECTED),
])
def test_preserved_common_calendar_semantics(
    day: date, expected: str, official_store: cal.CalendarEvidenceStore
) -> None:
    assert cal.common_etf_session_status(day, DECISION, official_store).state == expected


def test_unresolved_required_venue_preserves_existing_intersection_rule() -> None:
    store = cal.CalendarEvidenceStore()
    for venue in ("NYSE_ARCA", "NASDAQ"):
        schedule = put_schedule(store, venue)
        store.put(cal.venue_session_calendar_record(store, normalized_schedule_sha256=schedule, trade_date=date(2026, 11, 26)))
    assert cal.common_etf_session_status(date(2026, 11, 26), DECISION, store).state == cal.UNRESOLVED


def test_missing_unsupported_year_is_unresolved_not_default_open(
    official_store: cal.CalendarEvidenceStore,
) -> None:
    assert cal.common_etf_session_status(date(2029, 1, 2), DECISION, official_store).state == cal.UNRESOLVED


def test_five_and_twenty_day_adapter_reproduce_owner_dates(
    official_store: cal.CalendarEvidenceStore,
) -> None:
    store = official_store; end = date(2026, 12, 24)
    calendar = cal.derive_etf_window_calendar(
        end_date=end, earliest_date=date(2026, 11, 1), window_days=20,
        decision_time=DECISION, evidence_store=store,
    )
    rows = tuple(flow_row(fund, day) for day in calendar.expected_dates for fund in ("IBIT", "FBTC"))
    for window_days in (5, 20):
        result = cal.scientific_etf_flow_window(
            rows, as_of=DECISION, funds=("IBIT", "FBTC"), end_date=end,
            earliest_date=date(2026, 11, 1), window_days=window_days,
            evidence_store=store,
        )
        assert result.evaluability_state == "EVALUABLE"
        assert result.feature is not None
        assert result.feature.included_observation_dates == result.calendar.expected_dates


def test_unresolved_calendar_never_invokes_feature(monkeypatch) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("ETF owner invoked on unresolved calendar")
    monkeypatch.setattr(flow, "etf_flow_window", forbidden)
    result = cal.scientific_etf_flow_window(
        (), as_of=DECISION, funds=("IBIT",), end_date=date(2026, 8, 25),
        earliest_date=date(2026, 8, 1), window_days=5,
        evidence_store=cal.CalendarEvidenceStore(),
    )
    assert result.evaluability_state == "NOT_EVALUABLE" and result.feature is None


def test_formula_and_revision_science_remain_unchanged() -> None:
    adapter = cal.etf_feature_adapter_contract()
    assert adapter["window_days"] == {"ETF_FLOW_5D": 5, "ETF_FLOW_20D": 20}
    assert adapter["flow_accel_formula"] == "ETFNorm_5 - ETFNorm_20 / 4"
    for key in ("formula_changed", "normalization_changed", "fund_completeness_changed",
                "aum_semantics_changed", "etf_flow_revision_semantics_changed"):
        assert adapter[key] is False


def test_executable_mutations_move_manifest_and_top_hash(monkeypatch) -> None:
    source = inspect.getsource(semantics)
    mutations = (
        source.replace('if iso_day in schedule["full_closure_dates"]:', "if False:"),
        source.replace('return "OPEN_EARLY_CLOSE"', 'return "CLOSED"'),
        source.replace('datetime.fromisoformat(row["available_at"]) <= cutoff', "True"),
    )
    baseline_digest = cal._semantic_ast_sha256(); baseline_top = cal.authority_definition()["definition_sha256"]
    for changed in mutations:
        assert changed != source
        changed_digest = cal._normalized_python_ast_sha256({"etf_calendar_semantics_module": changed})
        assert changed_digest != baseline_digest
        with monkeypatch.context() as context:
            context.setattr(cal, "_semantic_ast_sha256", lambda digest=changed_digest: digest)
            assert cal.authority_definition()["definition_sha256"] != baseline_top


def test_runtime_semantic_mismatch_refuses(monkeypatch) -> None:
    record = acquisition("NASDAQ")
    with monkeypatch.context() as context:
        context.setattr(cal, "_semantic_ast_sha256", lambda: "f" * 64)
        with pytest.raises(cal.EtfCalendarAuthorityError, match="attestation mismatch"):
            cal.CalendarEvidenceStore().put(record)


def test_hash_determinism_artifacts_and_failed_v2_unchanged(tmp_path) -> None:
    restored = cal.restore_artifacts(ARTIFACT_DIR)
    expected = cal.authority_definition()["definition_sha256"]
    assert restored["definition_sha256"] == expected
    assert expected not in {cal.FAILED_AUTHORITY_SHA256, cal.FAILED_CORRECTED_AUTHORITY_SHA256}
    command = [sys.executable, "-c", "from btc_predictor.research.etf_publication_calendar import authority_definition; print(authority_definition()['definition_sha256'])"]
    outputs = set()
    for seed, cwd in (("1", ROOT), ("999", tmp_path)):
        env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONPATH=str(ROOT))
        outputs.add(subprocess.run(command, cwd=cwd, env=env, check=True, capture_output=True, text=True).stdout.strip())
    assert outputs == {expected}
    failed_v2 = json.loads((ROOT / "prospective_evidence/prospective_integration_corpus_v2/protocol_definition.json").read_text())
    assert failed_v2["definition_sha256"] == "488251df7bc1b49f801caa0dc28eb5224836574b154db9e4a70d4be670ec0b6d"
    failed_calendar = json.loads((ROOT / "prospective_evidence/etf_publication_calendar_authority_v1/authority_definition.json").read_text())
    failed_corrected = json.loads((ROOT / "prospective_evidence/etf_publication_calendar_authority_v1_r1/authority_definition.json").read_text())
    assert failed_calendar["definition_sha256"] == cal.FAILED_AUTHORITY_SHA256
    assert failed_corrected["definition_sha256"] == cal.FAILED_CORRECTED_AUTHORITY_SHA256
