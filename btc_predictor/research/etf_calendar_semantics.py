"""Deterministic source-specific extraction for official ETF venue calendars.

This module is deliberately isolated: its normalized AST is a material child of
``ETF_PUBLICATION_CALENDAR_AUTHORITY_V1``.  Keep all scientific extraction and
PIT reduction behavior in this file so runtime attestation covers executable
semantics rather than only declarative summaries.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from html.parser import HTMLParser
from typing import Any


class CalendarSourceFormatError(ValueError):
    """The exact response is not a supported frozen official-source format."""


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text: list[str] = []
        self.cells: list[str] = []
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in {"td", "th"}:
            if self._cell is not None:
                raise CalendarSourceFormatError("nested calendar table cell")
            self._cell = []

    def handle_data(self, data: str) -> None:
        normalized = " ".join(data.split())
        if normalized:
            self.text.append(normalized)
            if self._cell is not None:
                self._cell.append(normalized)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None:
            self.cells.append(" ".join(self._cell))
            self._cell = None


def _html(response_bytes: bytes) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    try:
        document = response_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise CalendarSourceFormatError("official HTML must be UTF-8") from error
    if not document.rstrip().endswith("</html>"):
        raise CalendarSourceFormatError("partial or truncated official HTML")
    parser = _VisibleTextParser()
    try:
        parser.feed(document)
        parser.close()
    except Exception as error:
        if isinstance(error, CalendarSourceFormatError):
            raise
        raise CalendarSourceFormatError("malformed official HTML") from error
    return document, tuple(parser.text), tuple(parser.cells)


def _date_without_year(value: str, year: int) -> date:
    cleaned = re.sub(r"^[A-Za-z]+,\s*", "", value)
    cleaned = re.sub(r"\*+", "", cleaned)
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", cleaned).strip()
    try:
        parsed = datetime.strptime(cleaned, "%B %d").date()
    except ValueError as error:
        raise CalendarSourceFormatError(f"malformed holiday date: {value!r}") from error
    return parsed.replace(year=year)


def _full_date(value: str) -> date:
    cleaned = re.sub(r"^[A-Za-z]+,\s*", "", value)
    cleaned = re.sub(r"\*+", "", cleaned)
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", cleaned).strip()
    try:
        return datetime.strptime(cleaned, "%B %d, %Y").date()
    except ValueError as error:
        raise CalendarSourceFormatError(f"malformed holiday date: {value!r}") from error


def _semantic(
    *,
    venue_id: str,
    acquisition_sha256: str,
    parser_id: str,
    parser_version: str,
    years: set[int],
    closures: set[date],
    early_closes: set[date],
) -> dict[str, Any]:
    if not years or closures & early_closes:
        raise CalendarSourceFormatError("ambiguous calendar coverage or session labels")
    if any(day.year not in years or day.weekday() >= 5 for day in closures | early_closes):
        raise CalendarSourceFormatError("calendar exception is outside weekday coverage")
    intervals = [
        {"coverage_start": f"{year:04d}-01-01", "coverage_end": f"{year:04d}-12-31"}
        for year in sorted(years)
    ]
    return {
        "venue_id": venue_id,
        "source_acquisition_sha256": acquisition_sha256,
        "supported_coverage_intervals": intervals,
        "full_closure_dates": [day.isoformat() for day in sorted(closures)],
        "early_close_dates": [day.isoformat() for day in sorted(early_closes)],
        "default_weekday_status": "OPEN_REGULAR",
        "default_semantics": (
            "within each explicitly headed annual equities holiday schedule, "
            "listed Closed dates are CLOSED, listed Early Close dates are "
            "OPEN_EARLY_CLOSE, and remaining weekdays are OPEN_REGULAR"
        ),
        "parser_id": parser_id,
        "parser_version": parser_version,
    }


def parse_nyse_calendar(response_bytes: bytes, acquisition_sha256: str) -> dict[str, Any]:
    document, text, cells = _html(response_bytes)
    joined = " ".join(text)
    required = (
        "<title>Holidays &amp; Trading Hours</title>",
        "All NYSE markets observe U.S. holidays as listed below",
        "NYSE Arca Equities",
        "Core Trading Session: 9:30 a.m. to 4:00 p.m. ET",
    )
    if any(marker not in document and marker not in joined for marker in required):
        raise CalendarSourceFormatError("NYSE product scope or calendar heading missing")
    try:
        start = cells.index("Holiday")
    except ValueError as error:
        raise CalendarSourceFormatError("NYSE calendar table missing") from error
    years: list[int] = []
    cursor = start + 1
    while cursor < len(cells) and re.fullmatch(r"20\d{2}", cells[cursor]):
        years.append(int(cells[cursor]))
        cursor += 1
    if not years or len(set(years)) != len(years):
        raise CalendarSourceFormatError("NYSE calendar years are missing or ambiguous")
    width = len(years) + 1
    remaining = cells[cursor:]
    if not remaining or len(remaining) % width:
        raise CalendarSourceFormatError("NYSE holiday table is partial")
    closures: set[date] = set()
    for offset in range(0, len(remaining), width):
        row = remaining[offset : offset + width]
        if not row[0] or any(not value for value in row[1:]):
            raise CalendarSourceFormatError("NYSE holiday row is malformed")
        for year, value in zip(years, row[1:], strict=True):
            if value.startswith("—"):
                continue
            closures.add(_date_without_year(value, year))
    early: set[date] = set()
    notices = [value for value in text if "Each market will close early at 1:00 p.m." in value]
    if not notices:
        raise CalendarSourceFormatError("NYSE early-close semantics missing")
    for notice in notices:
        for month, day, year in re.findall(
            r"(?:Monday|Tuesday|Wednesday|Thursday|Friday),\s+"
            r"([A-Z][a-z]+)\s+(\d{1,2}),\s+(20\d{2})",
            notice,
        ):
            early.add(datetime.strptime(f"{month} {day} {year}", "%B %d %Y").date())
    return _semantic(
        venue_id="NYSE_ARCA",
        acquisition_sha256=acquisition_sha256,
        parser_id="NYSE_HOLIDAYS_TRADING_HOURS_HTML",
        parser_version="1",
        years=set(years),
        closures=closures,
        early_closes=early,
    )


def parse_nasdaq_calendar(response_bytes: bytes, acquisition_sha256: str) -> dict[str, Any]:
    document, text, cells = _html(response_bytes)
    joined = " ".join(text)
    headings = re.findall(r"U\.S\. Equity and Options Markets Holiday Schedule (20\d{2})", joined)
    if len(headings) != 1 or "NASDAQTrader.com" not in document:
        raise CalendarSourceFormatError("Nasdaq product scope or annual heading ambiguous")
    year = int(headings[0])
    try:
        start = next(
            index
            for index in range(len(cells) - 2)
            if cells[index : index + 3] == (str(year), "Holiday", "Status")
        )
    except StopIteration as error:
        raise CalendarSourceFormatError("Nasdaq calendar table missing") from error
    closures: set[date] = set()
    early: set[date] = set()
    cursor = start + 3
    rows = 0
    while cursor + 2 < len(cells) and re.fullmatch(
        r"[A-Z][a-z]+ \d{1,2}, 20\d{2}", cells[cursor]
    ):
        day = _full_date(cells[cursor])
        label, status = cells[cursor + 1], cells[cursor + 2]
        if day.year != year:
            raise CalendarSourceFormatError("Nasdaq row escapes annual coverage")
        if status == "Closed" and "Early Close" not in label:
            closures.add(day)
        elif label == "Early Close* - U.S." and status == "1:00 p.m.":
            early.add(day)
        else:
            raise CalendarSourceFormatError("unknown Nasdaq session label")
        rows += 1
        cursor += 3
    if rows < 3 or "Nasdaq will continue to send alerts" not in joined:
        raise CalendarSourceFormatError("Nasdaq calendar is partial")
    return _semantic(
        venue_id="NASDAQ",
        acquisition_sha256=acquisition_sha256,
        parser_id="NASDAQ_TRADER_US_EQUITIES_HTML",
        parser_version="1",
        years={year},
        closures=closures,
        early_closes=early,
    )


def parse_cboe_calendar(response_bytes: bytes, acquisition_sha256: str) -> dict[str, Any]:
    document, text, cells = _html(response_bytes)
    if (
        "Cboe BZX and EDGX Equities Trading Hours" not in document
        or "Equities Holiday Schedule" not in " ".join(text)
        or "/us/equities/holidays/csv/" not in document
        or "Regular Trading Session" not in document
    ):
        raise CalendarSourceFormatError("Cboe BZX product scope or calendar heading missing")
    headings = re.findall(r"(20\d{2}) Equities Holiday Schedule", " ".join(text))
    if len(headings) != 1:
        raise CalendarSourceFormatError("Cboe annual coverage is ambiguous")
    year = int(headings[0])
    try:
        start = next(
            index for index in range(len(cells) - 1)
            if cells[index : index + 2] == ("Holiday", "Date")
        )
    except StopIteration as error:
        raise CalendarSourceFormatError("Cboe calendar table missing") from error
    calendar_cells = cells[start + 2 :]
    if len(calendar_cells) < 6 or len(calendar_cells) % 2:
        raise CalendarSourceFormatError("Cboe calendar is partial")
    closures: set[date] = set()
    early: set[date] = set()
    closure_labels = {
        "New Year's Day", "Martin Luther King, Jr. Day", "Presidents' Day",
        "Good Friday", "Memorial Day", "Juneteenth Holiday",
        "Independence Day Observed", "Labor Day", "Thanksgiving Day",
        "Christmas Day",
    }
    early_labels = {"Thanksgiving Early Close", "Christmas Early Close"}
    for offset in range(0, len(calendar_cells), 2):
        label, displayed_date = calendar_cells[offset : offset + 2]
        day = _date_without_year(displayed_date, year)
        if label in early_labels:
            early.add(day)
        elif label in closure_labels:
            closures.add(day)
        else:
            raise CalendarSourceFormatError("unknown Cboe session label")
    return _semantic(
        venue_id="CBOE_BZX",
        acquisition_sha256=acquisition_sha256,
        parser_id="CBOE_BZX_US_EQUITIES_NEXTJS_HTML",
        parser_version="1",
        years={year},
        closures=closures,
        early_closes=early,
    )


PARSERS = {
    "NYSE_HOLIDAYS_TRADING_HOURS_HTML": parse_nyse_calendar,
    "NASDAQ_TRADER_US_EQUITIES_HTML": parse_nasdaq_calendar,
    "CBOE_BZX_US_EQUITIES_NEXTJS_HTML": parse_cboe_calendar,
}


def derive_schedule(
    parser_id: str, response_bytes: bytes, acquisition_sha256: str
) -> dict[str, Any]:
    try:
        parser = PARSERS[parser_id]
    except KeyError as error:
        raise CalendarSourceFormatError("UNSUPPORTED_SOURCE_FORMAT") from error
    return parser(response_bytes, acquisition_sha256)


def status_for_date(schedule: dict[str, Any], trade_date: date) -> str:
    covered = any(
        date.fromisoformat(interval["coverage_start"])
        <= trade_date
        <= date.fromisoformat(interval["coverage_end"])
        for interval in schedule["supported_coverage_intervals"]
    )
    if not covered:
        raise CalendarSourceFormatError("trade_date is outside source-derived coverage")
    if trade_date.weekday() >= 5:
        return "CLOSED"
    iso_day = trade_date.isoformat()
    if iso_day in schedule["full_closure_dates"]:
        return "CLOSED"
    if iso_day in schedule["early_close_dates"]:
        return "OPEN_EARLY_CLOSE"
    return schedule["default_weekday_status"]


def select_latest_pit_rows(rows: list[dict[str, Any]], cutoff: datetime) -> list[dict[str, Any]]:
    eligible = [row for row in rows if datetime.fromisoformat(row["available_at"]) <= cutoff]
    if not eligible:
        return []
    latest = max(datetime.fromisoformat(row["available_at"]) for row in eligible)
    return [row for row in eligible if datetime.fromisoformat(row["available_at"]) == latest]


def reduce_common_session(states: tuple[str, ...]) -> str:
    if "UNRESOLVED" in states:
        return "UNRESOLVED"
    if all(state in {"OPEN_REGULAR", "OPEN_EARLY_CLOSE"} for state in states):
        return "EXPECTED"
    return "NOT_EXPECTED"
