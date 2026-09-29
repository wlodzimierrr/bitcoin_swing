"""POSTP1-001V2A-T1 frozen US equity market closure table tests.

Every assertion here is deterministic and offline.  The official venue documents
were retrieved once at freeze time and are stored, compressed, inside the frozen
namespace; these tests re-hash and re-parse those stored bytes rather than
reaching the network.
"""

from __future__ import annotations

import ast
import base64
import calendar
import copy
import gzip
import hashlib
import html
import json
import re
import shutil
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from btc_predictor.data import EtfFlow
from btc_predictor.features.flow import etf_flow_window
from btc_predictor.research import us_equity_market_closures as closures
from btc_predictor.research.us_equity_market_closures import (
    ALL_VENUES_CLOSED,
    CLOSED,
    CLOSURE_TABLE_FILE_SHA256,
    COVERAGE_END,
    COVERAGE_START,
    DEFINITION_FILE_SHA256,
    DEFINITION_SHA256,
    LISTING_VENUES,
    OPEN_OR_NOT_LISTED,
    SCHEDULED_HOLIDAY,
    SOURCE_INDEX_FILE_SHA256,
    UNSCHEDULED_CLOSURE,
    VENUE_DISAGREEMENT,
    ClosureTableError,
    load_closures,
    namespace_root,
)


NAMESPACE = namespace_root()
DEFINITION = json.loads(
    (NAMESPACE / closures.DEFINITION_FILENAME).read_text("ascii")
)
TABLE = json.loads((NAMESPACE / closures.CLOSURE_TABLE_FILENAME).read_text("ascii"))
SOURCE_INDEX = json.loads(
    (NAMESPACE / closures.SOURCE_INDEX_FILENAME).read_text("ascii")
)
ROWS = TABLE["rows"]
SOURCES = SOURCE_INDEX["sources"]
COVERAGE_YEARS = tuple(range(COVERAGE_START.year, COVERAGE_END.year + 1))

REQUIRED_CITATION_FIELDS = (
    "archived_copy",
    "document_title",
    "final_url",
    "original_publisher_url",
    "publisher",
    "request_url",
    "retrieved_at",
    "retrieved_sha256",
    "source_id",
    "source_name_in_document",
    "stored_file",
)

MONTHS = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}


# --------------------------------------------------------------------------- #
# Stored official source documents
# --------------------------------------------------------------------------- #


def _stored_bytes(source_id: str) -> bytes:
    source = SOURCES[source_id]
    encoded = (NAMESPACE / source["stored_file"]).read_bytes()
    return gzip.decompress(base64.b64decode(encoded))


def _document_text(source_id: str) -> str:
    """Tag-stripped, whitespace-collapsed text of one stored source document."""

    raw = _stored_bytes(source_id).decode("utf-8", "replace")
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    return " ".join(html.unescape(re.sub(r"(?s)<[^>]+>", " ", raw)).split())


def _cells(row_html: str) -> list[str]:
    return [
        html.unescape(re.sub(r"(?s)<[^>]+>", "", cell)).replace("\xa0", " ").strip()
        for cell in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", row_html)
    ]


def _parse_nyse_html(text: str) -> dict[int, dict[date, str]]:
    """NYSE 'Holidays & Trading Hours': one column per year, 'Weekday, Month D'."""

    table = re.search(
        r'(?is)<table[^>]*class="[^"]*table-data[^"]*"[^>]*>(.*?)</table>', text
    )
    assert table is not None, "NYSE holiday table not found"
    rows = re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", table.group(1))
    header = _cells(rows[0])
    assert header[0].lower() == "holiday", header
    years = [int(year) for year in header[1:]]
    parsed: dict[int, dict[date, str]] = {year: {} for year in years}
    for row in rows[1:]:
        cells = _cells(row)
        assert len(cells) == len(years) + 1, cells
        for year, cell in zip(years, cells[1:], strict=True):
            if not cell or cell.startswith(("—", "-")):
                continue  # published as not observed, e.g. "-*"
            match = re.match(
                r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+"
                r"([A-Z][a-z]+)\s+(\d{1,2})",
                cell,
            )
            assert match is not None, cell
            day = date(year, MONTHS[match.group(1)], int(match.group(2)))
            parsed[year][day] = cells[0]
    return parsed


def _parse_nasdaq_html(text: str) -> dict[int, dict[date, str]]:
    """nasdaqtrader.com trading calendar rows of (date, holiday, status)."""

    heading = re.search(
        r"(?is)<h1>\s*U\.S\.\s*Equity and Options Markets Holiday Schedule\s*"
        r"(\d{4})\s*</h1>",
        text,
    )
    assert heading is not None, "Nasdaq holiday heading not found"
    year = int(heading.group(1))
    table = re.search(r"(?is)<table[^>]*>(.*?)</table>", text[heading.end() :])
    assert table is not None, "Nasdaq holiday table not found"
    parsed: dict[date, str] = {}
    for row in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", table.group(1)):
        cells = _cells(row)
        assert len(cells) == 3, cells
        when, name, status = cells
        match = re.match(r"^([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})$", when)
        if match is None:
            continue  # header row
        assert int(match.group(3)) == year, when
        if status.lower() != "closed":
            continue  # early close: trading occurs, out of scope
        parsed[date(year, MONTHS[match.group(1)], int(match.group(2)))] = name
    assert parsed, "no Nasdaq closures parsed"
    return {year: parsed}


def _parse_cboe_csv(text: str) -> dict[int, dict[date, str]]:
    """cboe.com US equities holiday CSV: 'Holiday Name,Date' after the '##' line."""

    lines = text.replace("\r\n", "\n").split("\n")
    start = lines.index("##") + 1
    assert lines[start].strip() == "Holiday Name,Date", lines[start]
    parsed: dict[int, dict[date, str]] = {}
    for line in lines[start + 1 :]:
        line = line.strip()
        if not line:
            continue
        name, _, when = line.rpartition(",")
        match = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", when)
        assert match is not None, line
        if "early close" in name.lower():
            continue  # trading occurs, out of scope
        day = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        parsed.setdefault(day.year, {})[day] = name
    assert parsed, "no Cboe closures parsed"
    return parsed


PARSERS = {
    "NYSE_HOURS_CALENDAR_HTML_V1": _parse_nyse_html,
    "NASDAQ_TRADING_CALENDAR_HTML_V1": _parse_nasdaq_html,
    "CBOE_EQUITIES_HOLIDAY_CSV_V1": _parse_cboe_csv,
}


# --------------------------------------------------------------------------- #
# Independent rule-based holiday computation (cross-check only)
# --------------------------------------------------------------------------- #


def _nth_weekday(year: int, month: int, weekday: int, nth: int) -> date:
    first = date(year, month, 1)
    first += timedelta(days=(weekday - first.weekday()) % 7)
    return first + timedelta(days=7 * (nth - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    last = date(year, month, calendar.monthrange(year, month)[1])
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _easter_sunday(year: int) -> date:
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f, g = (b + 8) // 25, (b - (b + 8) // 25 + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    lm = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * lm) // 451
    return date(year, (h + lm - 7 * m + 114) // 31, ((h + lm - 7 * m + 114) % 31) + 1)


def _observed(day: date) -> date | None:
    if day.weekday() == 5:
        return day - timedelta(days=1)
    if day.weekday() == 6:
        return day + timedelta(days=1)
    return day


def _rule_based_closures(year: int) -> set[date]:
    """US equity full-day holidays as the published observance rules imply them."""

    days = {
        _nth_weekday(year, 1, 0, 3),  # Martin Luther King, Jr. Day
        _nth_weekday(year, 2, 0, 3),  # Washington's Birthday
        _easter_sunday(year) - timedelta(days=2),  # Good Friday
        _last_weekday(year, 5, 0),  # Memorial Day
        _nth_weekday(year, 9, 0, 1),  # Labor Day
        _nth_weekday(year, 11, 3, 4),  # Thanksgiving Day
    }
    for fixed in (date(year, 1, 1), date(year, 6, 19), date(year, 7, 4), date(year, 12, 25)):
        # A Saturday holiday is observed on the preceding Friday, except New
        # Year's Day, which the venues do not observe in the preceding year.
        if fixed.month == 1 and fixed.weekday() == 5:
            continue
        days.add(_observed(fixed))
    return days


# --------------------------------------------------------------------------- #
# Frozen anchors
# --------------------------------------------------------------------------- #


def _canonical(payload: object) -> str:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    )


def _digest(payload: object) -> str:
    return hashlib.sha256(_canonical(payload).encode("ascii")).hexdigest()


def _seal(payload: dict) -> dict:
    sealed = dict(payload)
    sealed.pop("definition_sha256", None)
    sealed["definition_sha256"] = _digest(sealed)
    return sealed


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        (closures.DEFINITION_FILENAME, DEFINITION_FILE_SHA256),
        (closures.CLOSURE_TABLE_FILENAME, CLOSURE_TABLE_FILE_SHA256),
        (closures.SOURCE_INDEX_FILENAME, SOURCE_INDEX_FILE_SHA256),
    ],
)
def test_frozen_files_hash_to_their_frozen_anchors(filename: str, expected: str) -> None:
    assert hashlib.sha256((NAMESPACE / filename).read_bytes()).hexdigest() == expected


@pytest.mark.parametrize("payload", [DEFINITION, TABLE, SOURCE_INDEX])
def test_definition_sha256_recomputes_mechanically(payload: dict) -> None:
    body = {key: value for key, value in payload.items() if key != "definition_sha256"}
    assert _digest(body) == payload["definition_sha256"]


def test_definition_binds_the_table_and_the_source_index() -> None:
    assert DEFINITION["closure_table_file_sha256"] == CLOSURE_TABLE_FILE_SHA256
    assert DEFINITION["source_index_file_sha256"] == SOURCE_INDEX_FILE_SHA256
    assert DEFINITION["definition_sha256"] == DEFINITION_SHA256
    assert DEFINITION["contract_version"] == closures.TABLE_VERSION
    assert DEFINITION["program_ticket"] == closures.PROGRAM_TICKET
    assert DEFINITION["required_review"] == closures.REQUIRED_REVIEW
    assert tuple(DEFINITION["venues"]) == LISTING_VENUES
    assert DEFINITION["coverage_start"] == COVERAGE_START.isoformat()
    assert DEFINITION["coverage_end"] == COVERAGE_END.isoformat()


def test_definition_freezes_the_authority_and_amendment_rules() -> None:
    assert DEFINITION["authority_mechanism"] == "EXACT_HASH_REVIEW_OF_THE_TABLE"
    assert DEFINITION["runtime_acquisition"] is False
    assert DEFINITION["in_place_edits_permitted"] is False
    assert DEFINITION["early_closes_out_of_scope"] is True
    assert DEFINITION["observations"] == 0
    assert DEFINITION["authorizes_collection"] is False
    assert DEFINITION["authorizes"] == ["POSTP1-002V2A-T1"]
    # citations are audit aids, not an authority mechanism
    assert "audit aids" in DEFINITION["citation_authority_statement"]
    assert "not an authority mechanism" in DEFINITION["citation_authority_statement"]
    # the amendment rule must state fail-closed-through-the-owner and no in-place edits
    amendment = DEFINITION["amendment_rule"]
    assert "ETF_FLOW_INPUT_MISSING" in amendment
    assert "never a zero" in amendment
    assert "US_EQUITY_MARKET_CLOSURE_TABLE_V2" in amendment
    assert "never edited in place" in amendment
    # the early-close exclusion records why trading days stay in the window
    assert "Trading occurs" in DEFINITION["early_close_rationale"]


# --------------------------------------------------------------------------- #
# Every row
# --------------------------------------------------------------------------- #


def test_table_row_count_and_per_year_counts_match_the_rows() -> None:
    assert TABLE["row_count"] == len(ROWS) == DEFINITION["row_count"]
    dates = [row["date"] for row in ROWS]
    assert dates == sorted(dates), "rows are not in ascending date order"
    assert len(set(dates)) == len(dates), "a date is repeated"
    for year in COVERAGE_YEARS:
        yearly = [row for row in ROWS if row["date"].startswith(f"{year}-")]
        declared = TABLE["rows_per_year"][str(year)]
        assert declared["total"] == len(yearly)
        assert declared["scheduled_holiday"] == sum(
            row["closure_type"] == SCHEDULED_HOLIDAY for row in yearly
        )
        assert declared["unscheduled_closure"] == sum(
            row["closure_type"] == UNSCHEDULED_CLOSURE for row in yearly
        )
    assert DEFINITION["rows_per_year"] == TABLE["rows_per_year"]


@pytest.mark.parametrize("row", ROWS, ids=[row["date"] for row in ROWS])
def test_every_row_is_a_covered_weekday_with_all_three_venues(row: dict) -> None:
    day = date.fromisoformat(row["date"])
    assert COVERAGE_START <= day <= COVERAGE_END
    assert day.weekday() < 5, "a closure row must be a Monday-to-Friday date"
    assert row["weekday"] == day.strftime("%A").upper()
    assert row["closure_type"] in (SCHEDULED_HOLIDAY, UNSCHEDULED_CLOSURE)
    assert row["official_name"].strip() == row["official_name"] != ""

    assert tuple(sorted(row["venue_status"])) == LISTING_VENUES
    assert set(row["venue_status"].values()) <= {CLOSED, OPEN_OR_NOT_LISTED}
    closed_everywhere = all(
        row["venue_status"][venue] == CLOSED for venue in LISTING_VENUES
    )
    assert row["agreement"] == (
        ALL_VENUES_CLOSED if closed_everywhere else VENUE_DISAGREEMENT
    )


@pytest.mark.parametrize("row", ROWS, ids=[row["date"] for row in ROWS])
def test_every_row_carries_a_complete_per_venue_citation(row: dict) -> None:
    for venue in LISTING_VENUES:
        if row["venue_status"][venue] != CLOSED:
            assert venue not in row["venue_citations"]
            continue
        citation = row["venue_citations"][venue]
        assert tuple(sorted(citation)) == REQUIRED_CITATION_FIELDS
        for field in REQUIRED_CITATION_FIELDS:
            if field == "archived_copy":
                assert isinstance(citation[field], bool)
                continue
            assert isinstance(citation[field], str) and citation[field].strip()
        assert len(citation["retrieved_sha256"]) == 64
        datetime.strptime(citation["retrieved_at"], "%Y-%m-%dT%H:%M:%SZ")

        source = SOURCES[citation["source_id"]]
        assert source["venue"] == venue
        assert date.fromisoformat(row["date"]).year in source["covered_years"]
        for field in (
            "publisher",
            "document_title",
            "request_url",
            "final_url",
            "original_publisher_url",
            "retrieved_at",
            "retrieved_sha256",
            "stored_file",
            "archived_copy",
        ):
            assert citation[field] == source[field], (row["date"], venue, field)


def test_every_covered_venue_year_has_an_official_source() -> None:
    schedules = {
        (source["venue"], year)
        for source in SOURCES.values()
        if source["role"] == "ANNUAL_SCHEDULE"
        for year in source["covered_years"]
    }
    assert schedules == {
        (venue, year) for venue in LISTING_VENUES for year in COVERAGE_YEARS
    }
    assert SOURCE_INDEX["source_count"] == len(SOURCES) == DEFINITION["source_count"]
    assert SOURCE_INDEX["third_party_aggregators_used"] is False


@pytest.mark.parametrize("source_id", sorted(SOURCES), ids=sorted(SOURCES))
def test_stored_source_bytes_rehash_to_the_recorded_sha256(source_id: str) -> None:
    source = SOURCES[source_id]
    stored_path = NAMESPACE / source["stored_file"]
    assert (
        hashlib.sha256(stored_path.read_bytes()).hexdigest()
        == source["stored_file_sha256"]
    )
    raw = _stored_bytes(source_id)
    assert hashlib.sha256(raw).hexdigest() == source["retrieved_sha256"]
    assert len(raw) == source["retrieved_bytes"]
    assert source["retrieval_http_status"] == 200
    assert source["archived_copy"] is (
        "archive_capture_timestamp" in source
    ), "an archived copy must be marked as such"
    if source["archived_copy"]:
        assert source["archive_service"] == "INTERNET_ARCHIVE_WAYBACK_MACHINE"
        assert re.fullmatch(r"\d{14}", source["archive_capture_timestamp"])
        assert source["archive_capture_timestamp"] in source["request_url"]
    assert "://" in source["original_publisher_url"]


# --------------------------------------------------------------------------- #
# Coverage completeness against the stored official sources
# --------------------------------------------------------------------------- #


def _table_closures_by_venue_year() -> dict[tuple[str, int], set[date]]:
    found: dict[tuple[str, int], set[date]] = {
        (venue, year): set() for venue in LISTING_VENUES for year in COVERAGE_YEARS
    }
    for row in ROWS:
        day = date.fromisoformat(row["date"])
        for venue in LISTING_VENUES:
            if row["venue_status"][venue] == CLOSED:
                found[(venue, day.year)].add(day)
    return found


@pytest.mark.parametrize(
    ("venue", "year"),
    [(venue, year) for venue in LISTING_VENUES for year in COVERAGE_YEARS],
    ids=[f"{venue}-{year}" for venue in LISTING_VENUES for year in COVERAGE_YEARS],
)
def test_table_lists_every_closure_the_official_sources_publish(
    venue: str, year: int
) -> None:
    """Re-parse the stored official documents and cross-check the table."""

    published: dict[date, str] = {}
    for source_id, source in SOURCES.items():
        if source["venue"] != venue or year not in source["covered_years"]:
            continue
        if source["role"] == "ANNUAL_SCHEDULE":
            parser = PARSERS[source["source_format"]]
            parsed = parser(_stored_bytes(source_id).decode("utf-8", "replace"))
            published.update(parsed[year])
        else:
            # A single-date closure notice: the stored bytes must state the
            # closure, and the table row it supports must cite this notice.
            supported = [
                row
                for row in ROWS
                for cited in [row["venue_citations"].get(venue)]
                if cited is not None and cited["source_id"] == source_id
            ]
            assert supported, source_id
            text = _document_text(source_id)
            for row in supported:
                day = date.fromisoformat(row["date"])
                spoken = f"{day.strftime('%B')} {day.day}, {day.year}"
                assert spoken in text, (source_id, spoken)
                assert re.search(r"will be closed|will close", text, re.I), source_id
                quoted = row["venue_citations"][venue]["source_name_in_document"]
                assert quoted in text, (source_id, quoted)
                published[day] = quoted

    assert published, (venue, year)
    assert set(published) == _table_closures_by_venue_year()[(venue, year)], (
        venue,
        year,
    )
    for row in ROWS:
        day = date.fromisoformat(row["date"])
        if day.year != year or row["venue_status"][venue] != CLOSED:
            continue
        assert (
            row["venue_citations"][venue]["source_name_in_document"] == published[day]
        )


@pytest.mark.parametrize("year", COVERAGE_YEARS)
def test_rule_based_computation_cross_checks_the_scheduled_holidays(year: int) -> None:
    """A second, independent derivation. It never replaces the official sources."""

    scheduled = {
        date.fromisoformat(row["date"])
        for row in ROWS
        if row["closure_type"] == SCHEDULED_HOLIDAY and row["date"].startswith(f"{year}-")
    }
    assert scheduled == _rule_based_closures(year)


def test_every_covered_year_lists_good_friday_and_juneteenth() -> None:
    for year in COVERAGE_YEARS:
        names = {
            row["official_name"]
            for row in ROWS
            if row["date"].startswith(f"{year}-")
        }
        assert "Good Friday" in names, year
        assert "Juneteenth National Independence Day" in names, year


def test_the_known_unscheduled_closure_is_present_and_sourced() -> None:
    unscheduled = [row for row in ROWS if row["closure_type"] == UNSCHEDULED_CLOSURE]
    assert [row["date"] for row in unscheduled] == ["2025-01-09"]
    row = unscheduled[0]
    assert row["weekday"] == "THURSDAY"
    assert row["agreement"] == ALL_VENUES_CLOSED
    assert "National Day of Mourning" in row["official_name"]
    assert {
        row["venue_citations"][venue]["source_id"] for venue in LISTING_VENUES
    } == {
        "cboe_bzx_2025_holiday_schedule_csv",
        "nasdaq_2025_national_day_of_mourning_alert",
        "nyse_arca_2025_national_day_of_mourning_notice",
    }


def test_no_early_close_leaked_into_the_table() -> None:
    """Early closes are trading days; the table must not contain one."""

    early_close_dates: set[date] = set()
    for source_id, source in SOURCES.items():
        if source["source_format"] != "CBOE_EQUITIES_HOLIDAY_CSV_V1":
            continue
        text = _stored_bytes(source_id).decode("utf-8", "replace")
        for line in text.replace("\r\n", "\n").split("\n"):
            name, _, when = line.strip().rpartition(",")
            if "early close" in name.lower() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", when):
                early_close_dates.add(date.fromisoformat(when))
    assert early_close_dates, "no early closes were parsed from the stored sources"
    assert early_close_dates.isdisjoint(
        date.fromisoformat(row["date"]) for row in ROWS
    )


def test_no_venue_disagreement_is_recorded() -> None:
    assert TABLE["venue_disagreement_dates"] == []
    assert DEFINITION["venue_disagreement_dates"] == []
    assert DEFINITION["venue_disagreement_count"] == 0
    assert all(row["agreement"] == ALL_VENUES_CLOSED for row in ROWS)


# --------------------------------------------------------------------------- #
# Loader
# --------------------------------------------------------------------------- #


def test_in_coverage_range_returns_the_exact_frozen_set() -> None:
    loaded = load_closures(COVERAGE_START, COVERAGE_END)
    assert loaded == frozenset(date.fromisoformat(row["date"]) for row in ROWS)
    assert isinstance(loaded, frozenset)
    assert len(loaded) == TABLE["row_count"]


def test_narrow_in_coverage_range_is_inclusive_on_both_ends() -> None:
    assert load_closures(date(2024, 7, 4), date(2024, 7, 4)) == {date(2024, 7, 4)}
    # 2024-07-05 .. 2024-09-01 holds no closure: Labor Day is 2024-09-02
    assert load_closures(date(2024, 7, 5), date(2024, 9, 1)) == frozenset()
    assert load_closures(date(2024, 1, 1), date(2024, 3, 29)) == {
        date(2024, 1, 1),
        date(2024, 1, 15),
        date(2024, 2, 19),
        date(2024, 3, 29),
    }


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (date(2022, 12, 31), date(2023, 1, 5)),  # starts before coverage
        (date(2026, 12, 1), date(2027, 1, 4)),  # ends after coverage
        (date(2027, 1, 1), date(2027, 12, 31)),  # wholly after coverage
        (date(2019, 1, 1), date(2019, 12, 31)),  # wholly before coverage
    ],
)
def test_out_of_coverage_range_refuses(start: date, end: date) -> None:
    with pytest.raises(ClosureTableError, match="not wholly inside the frozen coverage"):
        load_closures(start, end)


def test_inverted_and_non_date_ranges_refuse() -> None:
    with pytest.raises(ClosureTableError, match="is after end"):
        load_closures(date(2024, 5, 1), date(2024, 4, 1))
    with pytest.raises(ClosureTableError, match="must be a datetime.date"):
        load_closures(datetime(2024, 5, 1, tzinfo=UTC), date(2024, 6, 1))
    with pytest.raises(ClosureTableError, match="must be a datetime.date"):
        load_closures("2024-05-01", date(2024, 6, 1))  # type: ignore[arg-type]


def _install_namespace(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    monkeypatch.setattr(closures, "namespace_root", lambda: root)


def _rewrite_namespace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, table: dict
) -> Path:
    """Write a re-sealed namespace and re-anchor the loader's frozen hashes."""

    root = tmp_path / "namespace"
    shutil.copytree(NAMESPACE, root)
    sealed_table = _seal(table)
    (root / closures.CLOSURE_TABLE_FILENAME).write_text(
        json.dumps(sealed_table, indent=2, sort_keys=True) + "\n", "ascii"
    )
    table_sha = hashlib.sha256(
        (root / closures.CLOSURE_TABLE_FILENAME).read_bytes()
    ).hexdigest()
    definition = _seal({**DEFINITION, "closure_table_file_sha256": table_sha})
    (root / closures.DEFINITION_FILENAME).write_text(
        json.dumps(definition, indent=2, sort_keys=True) + "\n", "ascii"
    )
    definition_sha = hashlib.sha256(
        (root / closures.DEFINITION_FILENAME).read_bytes()
    ).hexdigest()
    _install_namespace(monkeypatch, root)
    monkeypatch.setattr(closures, "CLOSURE_TABLE_FILE_SHA256", table_sha)
    monkeypatch.setattr(closures, "DEFINITION_FILE_SHA256", definition_sha)
    monkeypatch.setattr(closures, "DEFINITION_SHA256", definition["definition_sha256"])
    return root


def test_range_containing_a_venue_disagreement_refuses(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    table = copy.deepcopy(TABLE)
    target = next(row for row in table["rows"] if row["date"] == "2024-07-04")
    target["venue_status"]["NASDAQ"] = OPEN_OR_NOT_LISTED
    target["venue_citations"].pop("NASDAQ")
    target["agreement"] = VENUE_DISAGREEMENT
    table["venue_disagreement_dates"] = ["2024-07-04"]
    _rewrite_namespace(monkeypatch, tmp_path, table)

    with pytest.raises(ClosureTableError, match="venue disagreement: 2024-07-04"):
        load_closures(date(2024, 7, 1), date(2024, 7, 31))
    with pytest.raises(ClosureTableError, match="venue disagreement: 2024-07-04"):
        load_closures(COVERAGE_START, COVERAGE_END)

    # a range that excludes the disagreement still loads, and the disagreeing
    # date is never reported as a closure
    loaded = load_closures(date(2024, 8, 1), date(2024, 12, 31))
    assert date(2024, 7, 4) not in loaded
    assert loaded == {date(2024, 9, 2), date(2024, 11, 28), date(2024, 12, 25)}


def test_undeclared_venue_disagreement_refuses(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A row whose venues disagree cannot hide behind a stale summary list."""

    table = copy.deepcopy(TABLE)
    target = next(row for row in table["rows"] if row["date"] == "2024-07-04")
    target["venue_status"]["NASDAQ"] = OPEN_OR_NOT_LISTED
    target["venue_citations"].pop("NASDAQ")
    target["agreement"] = VENUE_DISAGREEMENT
    _rewrite_namespace(monkeypatch, tmp_path, table)  # summary left empty

    with pytest.raises(ClosureTableError, match="venue_disagreement_dates does not match"):
        load_closures(date(2024, 1, 1), date(2024, 12, 31))


def test_altering_one_table_byte_refuses(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "namespace"
    shutil.copytree(NAMESPACE, root)
    target = root / closures.CLOSURE_TABLE_FILENAME
    raw = bytearray(target.read_bytes())
    index = raw.index(b"2023-01-02")
    raw[index + 9] = ord("3")  # 2023-01-02 -> 2023-01-03
    target.write_bytes(bytes(raw))
    assert hashlib.sha256(bytes(raw)).hexdigest() != CLOSURE_TABLE_FILE_SHA256
    _install_namespace(monkeypatch, root)

    with pytest.raises(ClosureTableError, match="does not match its frozen hash"):
        load_closures(COVERAGE_START, COVERAGE_END)


def test_altering_one_definition_byte_refuses(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "namespace"
    shutil.copytree(NAMESPACE, root)
    target = root / closures.DEFINITION_FILENAME
    raw = target.read_bytes().replace(b'"observations": 0', b'"observations": 1')
    assert raw != target.read_bytes()
    target.write_bytes(raw)
    _install_namespace(monkeypatch, root)

    with pytest.raises(ClosureTableError, match="does not match its frozen hash"):
        load_closures(COVERAGE_START, COVERAGE_END)


def test_altering_one_source_index_byte_refuses(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "namespace"
    shutil.copytree(NAMESPACE, root)
    target = root / closures.SOURCE_INDEX_FILENAME
    raw = target.read_bytes().replace(
        b'"third_party_aggregators_used": false',
        b'"third_party_aggregators_used": true',
    )
    assert raw != target.read_bytes()
    target.write_bytes(raw)
    _install_namespace(monkeypatch, root)

    with pytest.raises(ClosureTableError, match="does not match its frozen hash"):
        load_closures(COVERAGE_START, COVERAGE_END)


def test_a_missing_namespace_refuses(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install_namespace(monkeypatch, tmp_path / "absent")
    with pytest.raises(ClosureTableError, match="is not readable"):
        load_closures(COVERAGE_START, COVERAGE_END)


def test_loader_imports_nothing_from_the_closed_calendar_lineage() -> None:
    module = Path(closures.__file__)
    tree = ast.parse(module.read_text("utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert imported == {
        "__future__",
        "collections.abc",
        "datetime",
        "hashlib",
        "json",
        "pathlib",
        "typing",
    }
    forbidden = ("etf_calendar", "etf_publication_calendar", "trusted_acquisition")
    source = module.read_text("utf-8")
    assert not any(token in source for token in forbidden)


# --------------------------------------------------------------------------- #
# Owner-effect demonstration against the unchanged flow owner
# --------------------------------------------------------------------------- #


FUND = "IBIT"
# Every fixture flow is published at observation_date + 2 days, so an as_of well
# past the last fixture publication keeps point-in-time availability out of the
# way: what this demonstration isolates is the market_holidays parameter.
AS_OF = datetime(2024, 7, 15, 12, 0, tzinfo=UTC)
OBSERVATION_DATE = date(2024, 7, 9)
FIXTURE_START = date(2024, 4, 1)


def _flow_fixture(skip: frozenset[date] = frozenset()) -> list[EtfFlow]:
    """One flow record per real trading day, so only a closure can be missing."""

    holidays = load_closures(FIXTURE_START, OBSERVATION_DATE)
    flows: list[EtfFlow] = []
    day = FIXTURE_START
    while day <= OBSERVATION_DATE:
        if day.weekday() < 5 and day not in holidays and day not in skip:
            flows.append(
                EtfFlow(
                    fund=FUND,
                    observation_date=day,
                    flow_usd=Decimal("1000000"),
                    aum_usd=Decimal("50000000000"),
                    provider="FIXTURE",
                    source="FIXTURE",
                    revision="1",
                    available_at=datetime(day.year, day.month, day.day, tzinfo=UTC)
                    + timedelta(days=2),
                    ingested_at=datetime(day.year, day.month, day.day, tzinfo=UTC)
                    + timedelta(days=2),
                )
            )
        day += timedelta(days=1)
    return flows


def _window(flows: list[EtfFlow], window_days: int, market_holidays):
    return etf_flow_window(
        flows,
        as_of=AS_OF,
        window_days=window_days,
        funds=(FUND,),
        market_holidays=market_holidays,
        end_date=OBSERVATION_DATE,
        feature_id=f"ETF_FLOW_{window_days}D",
        normalized_feature_id=f"ETF_NORM_{window_days}D",
    )


@pytest.mark.parametrize("window_days", [5, 20])
def test_empty_default_fails_closed_over_a_listed_holiday(window_days: int) -> None:
    """This is the POSTP1-002V2 finding the table exists to own."""

    result = _window(_flow_fixture(), window_days, ())
    assert date(2024, 7, 4) in result.included_observation_dates
    assert "ETF_FLOW_INPUT_MISSING" in result.reason_codes
    assert result.complete is False
    assert result.flow_sum_usd is None  # never silently zero


@pytest.mark.parametrize("window_days", [5, 20])
def test_loaded_closures_complete_the_same_window(window_days: int) -> None:
    holidays = load_closures(FIXTURE_START, OBSERVATION_DATE)
    result = _window(_flow_fixture(), window_days, holidays)
    assert date(2024, 7, 4) not in result.included_observation_dates
    assert holidays.isdisjoint(result.included_observation_dates)
    assert all(day.weekday() < 5 for day in result.included_observation_dates)
    assert len(result.included_observation_dates) == window_days
    assert result.reason_codes == ()
    assert result.complete is True
    assert result.flow_sum_usd == Decimal("1000000") * window_days


def test_the_twenty_day_window_spans_more_than_one_listed_holiday() -> None:
    """The 20-day demonstration must actually exercise two closures."""

    empty = _window(_flow_fixture(), 20, ())
    spanned = load_closures(FIXTURE_START, OBSERVATION_DATE) & set(
        empty.included_observation_dates
    )
    assert spanned == {date(2024, 6, 19), date(2024, 7, 4)}


@pytest.mark.parametrize("window_days", [5, 20])
def test_an_unlisted_closure_still_fails_closed(window_days: int) -> None:
    """The frozen amendment rule, demonstrated against the unchanged owner."""

    unlisted = date(2024, 7, 8)  # a Monday the table does not list
    assert unlisted not in load_closures(FIXTURE_START, OBSERVATION_DATE)
    holidays = load_closures(FIXTURE_START, OBSERVATION_DATE)
    result = _window(_flow_fixture(skip=frozenset({unlisted})), window_days, holidays)
    assert unlisted in result.included_observation_dates
    assert "ETF_FLOW_INPUT_MISSING" in result.reason_codes
    assert result.complete is False
    assert result.flow_sum_usd is None
