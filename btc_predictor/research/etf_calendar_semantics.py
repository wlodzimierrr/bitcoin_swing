"""Hash-bound, structurally complete official ETF-calendar parsers."""

from __future__ import annotations

import re
from datetime import date, datetime
from html.parser import HTMLParser
from typing import Any, Callable


class CalendarSourceFormatError(ValueError):
    """The response is not a supported frozen official-source format."""


class _StructuredHtmlParser(HTMLParser):
    """Capture visible text plus table/section/row/cell boundaries."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text: list[str] = []
        self.tables: list[dict[str, Any]] = []
        self._ignored_depth = 0
        self._table: dict[str, Any] | None = None
        self._section: str | None = None
        self._row: dict[str, Any] | None = None
        self._cell: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in {"script", "style"}:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        if tag == "table":
            if self._table is not None:
                raise CalendarSourceFormatError("nested calendar table")
            self._table = {"rows": []}
            self.tables.append(self._table)
        elif tag in {"thead", "tbody"} and self._table is not None:
            if self._section is not None or self._row is not None:
                raise CalendarSourceFormatError("malformed calendar table section")
            self._section = tag
        elif tag == "tr" and self._table is not None:
            if self._row is not None:
                raise CalendarSourceFormatError("nested calendar row")
            self._row = {"section": self._section, "cells": [], "cell_tags": []}
        elif tag in {"th", "td"} and self._row is not None:
            if self._cell is not None:
                raise CalendarSourceFormatError("nested calendar table cell")
            self._cell = {"tag": tag, "text": []}

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        normalized = " ".join(data.split())
        if normalized:
            self.text.append(normalized)
            if self._cell is not None:
                self._cell["text"].append(normalized)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            if self._ignored_depth:
                self._ignored_depth -= 1
            return
        if self._ignored_depth:
            return
        if tag in {"th", "td"} and self._cell is not None:
            if self._cell["tag"] != tag or self._row is None:
                raise CalendarSourceFormatError("malformed calendar table cell")
            self._row["cells"].append(" ".join(self._cell["text"]))
            self._row["cell_tags"].append(tag)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._cell is not None or self._table is None:
                raise CalendarSourceFormatError("unterminated calendar table cell")
            self._row["cells"] = tuple(self._row["cells"])
            self._row["cell_tags"] = tuple(self._row["cell_tags"])
            self._table["rows"].append(self._row)
            self._row = None
        elif tag in {"thead", "tbody"} and self._section == tag:
            if self._row is not None:
                raise CalendarSourceFormatError("unterminated calendar row")
            self._section = None
        elif tag == "table" and self._table is not None:
            if self._cell is not None or self._row is not None or self._section is not None:
                raise CalendarSourceFormatError("unterminated calendar table")
            self._table["rows"] = tuple(self._table["rows"])
            self._table = None

    def assert_complete(self) -> None:
        if any((self._ignored_depth, self._table, self._section, self._row, self._cell)):
            raise CalendarSourceFormatError("partial or malformed official HTML")


def _html(response_bytes: bytes) -> tuple[str, tuple[str, ...], tuple[dict[str, Any], ...]]:
    try:
        document = response_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise CalendarSourceFormatError("official HTML must be UTF-8") from error
    if not document.rstrip().lower().endswith("</html>"):
        raise CalendarSourceFormatError("partial or truncated official HTML")
    parser = _StructuredHtmlParser()
    try:
        parser.feed(document)
        parser.close()
        parser.assert_complete()
    except Exception as error:
        if isinstance(error, CalendarSourceFormatError):
            raise
        raise CalendarSourceFormatError("malformed official HTML") from error
    return document, tuple(parser.text), tuple(parser.tables)


def _calendar_table(
    tables: tuple[dict[str, Any], ...],
    header_match: Callable[[tuple[str, ...]], bool],
) -> tuple[tuple[str, ...], tuple[tuple[str, ...], ...]]:
    matches = [table for table in tables if table["rows"] and header_match(table["rows"][0]["cells"])]
    if len(matches) != 1:
        raise CalendarSourceFormatError("annual calendar table identity is missing or ambiguous")
    rows = matches[0]["rows"]
    header, body = rows[0], rows[1:]
    if (
        header["section"] not in {"thead", None}
        or any(tag != "th" for tag in header["cell_tags"])
        or not body
        or any(row["section"] != "tbody" for row in body)
    ):
        raise CalendarSourceFormatError("annual calendar table structure is unsupported")
    return header["cells"], tuple(row["cells"] for row in body)


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
    *, venue_id: str, acquisition_sha256: str, parser_id: str,
    source_format_version: str, years: set[int], closures: list[date],
    early_closes: list[date],
) -> dict[str, Any]:
    if (
        not years
        or len(closures) != len(set(closures))
        or len(early_closes) != len(set(early_closes))
        or set(closures) & set(early_closes)
    ):
        raise CalendarSourceFormatError("ambiguous coverage or duplicate session labels")
    if any(day.year not in years or day.weekday() >= 5 for day in closures + early_closes):
        raise CalendarSourceFormatError("calendar exception is outside weekday coverage")
    return {
        "venue_id": venue_id,
        "source_acquisition_sha256": acquisition_sha256,
        "supported_coverage_intervals": [
            {"coverage_start": f"{year:04d}-01-01", "coverage_end": f"{year:04d}-12-31"}
            for year in sorted(years)
        ],
        "full_closure_dates": [day.isoformat() for day in sorted(closures)],
        "early_close_dates": [day.isoformat() for day in sorted(early_closes)],
        "default_weekday_status": "OPEN_REGULAR",
        "default_semantics": (
            "the complete frozen annual semantic row census is traversed; listed "
            "closures are CLOSED, listed early closes are OPEN_EARLY_CLOSE, and "
            "remaining covered weekdays are OPEN_REGULAR"
        ),
        "parser_id": parser_id,
        "parser_version": "2",
        "source_format_version": source_format_version,
    }


_NYSE_HEADER = ("Holiday", "2026", "2027", "2028")
_NYSE_LABELS = (
    "New Year’s Day", "Martin Luther King, Jr. Day", "Washington's Birthday",
    "Good Friday", "Memorial Day", "Juneteenth National Independence Day",
    "Independence Day", "Labor Day", "Thanksgiving Day", "Christmas Day",
)
_NYSE_EARLY_NOTICE_DATE_COUNTS = {"**": 1, "***": 3, "****": 1}


def _nyse_early_closes(text: tuple[str, ...], years: set[int]) -> list[date]:
    candidates = tuple(value for value in text if "close early" in value.lower() or "1:00 p.m." in value.lower())
    notices: dict[str, str] = {}
    for value in candidates:
        match = re.match(r"^(\*{2,4}) Each market will close early at 1:00 p\.m\. ", value)
        if match is None:
            raise CalendarSourceFormatError("unsupported NYSE early-close statement")
        marker = match.group(1)
        if marker in notices:
            raise CalendarSourceFormatError("duplicate NYSE early-close statement class")
        if any(fragment not in value for fragment in (
            "NYSE Arca Equities", "late trading sessions will close at 5:00 p.m.",
            "All times are Eastern Time.",
        )):
            raise CalendarSourceFormatError("incomplete NYSE early-close product statement")
        notices[marker] = value
    if set(notices) != set(_NYSE_EARLY_NOTICE_DATE_COUNTS):
        raise CalendarSourceFormatError("NYSE early-close statement census is incomplete")
    early: list[date] = []
    for marker, expected_count in _NYSE_EARLY_NOTICE_DATE_COUNTS.items():
        matches = re.findall(
            r"(?:Monday|Tuesday|Wednesday|Thursday|Friday),\s+([A-Z][a-z]+)\s+(\d{1,2}),\s+(20\d{2})",
            notices[marker],
        )
        if len(matches) != expected_count:
            raise CalendarSourceFormatError("NYSE early-close statement did not parse completely")
        for month, day, year in matches:
            try:
                parsed = datetime.strptime(f"{month} {day} {year}", "%B %d %Y").date()
            except ValueError as error:
                raise CalendarSourceFormatError(
                    "NYSE early-close statement did not parse completely"
                ) from error
            if parsed.year not in years:
                raise CalendarSourceFormatError("NYSE early close escapes supported coverage")
            early.append(parsed)
    return early


def parse_nyse_calendar(response_bytes: bytes, acquisition_sha256: str) -> dict[str, Any]:
    document, text, tables = _html(response_bytes)
    joined = " ".join(text)
    required = (
        "<title>Holidays &amp; Trading Hours</title>",
        "All NYSE markets observe U.S. holidays as listed below for 2026, 2027, and 2028.",
        "NYSE Arca Equities", "Core Trading Session: 9:30 a.m. to 4:00 p.m. ET",
    )
    if any(marker not in document and marker not in joined for marker in required):
        raise CalendarSourceFormatError("NYSE product scope or calendar heading missing")
    header, rows = _calendar_table(tables, lambda cells: cells == _NYSE_HEADER)
    if header != _NYSE_HEADER or tuple(row[0] for row in rows if row) != _NYSE_LABELS:
        raise CalendarSourceFormatError("NYSE annual semantic row census is unsupported")
    years = [int(value) for value in header[1:]]
    closures: list[date] = []
    for row in rows:
        if len(row) != len(header) or not all(row):
            raise CalendarSourceFormatError("NYSE holiday row is malformed")
        for year, value in zip(years, row[1:], strict=True):
            if not value.startswith("—"):
                closures.append(_date_without_year(value, year))
    return _semantic(
        venue_id="NYSE_ARCA", acquisition_sha256=acquisition_sha256,
        parser_id="NYSE_HOLIDAYS_TRADING_HOURS_HTML",
        source_format_version="NYSE_2026_2028_HTML_V1", years=set(years),
        closures=closures, early_closes=_nyse_early_closes(text, set(years)),
    )


_NASDAQ_HEADER = ("2026", "Holiday", "Status")
_NASDAQ_ROW_CENSUS = (
    ("New Years Day (Observed)", "Closed"),
    ("Martin Luther King, Jr. Day", "Closed"),
    ("President's Day - U.S.", "Closed"), ("Good Friday", "Closed"),
    ("Memorial Day - U.S.", "Closed"),
    ("Juneteenth Holiday (Observed)", "Closed"),
    ("Independence Day - U.S. (Observed)", "Closed"),
    ("Labor Day - U.S.", "Closed"), ("Thanksgiving Day - U.S.", "Closed"),
    ("Early Close* - U.S.", "1:00 p.m."),
    ("Early Close* - U.S.", "1:00 p.m."),
    ("Christmas Holiday - U.S.", "Closed"),
)


def parse_nasdaq_calendar(response_bytes: bytes, acquisition_sha256: str) -> dict[str, Any]:
    document, text, tables = _html(response_bytes)
    joined = " ".join(text)
    headings = re.findall(r"U\.S\. Equity and Options Markets Holiday Schedule (20\d{2})", joined)
    if headings != ["2026"] or "NASDAQTrader.com" not in document:
        raise CalendarSourceFormatError("Nasdaq product scope or annual heading ambiguous")
    header, rows = _calendar_table(tables, lambda cells: cells == _NASDAQ_HEADER)
    if header != _NASDAQ_HEADER or any(len(row) != 3 for row in rows):
        raise CalendarSourceFormatError("Nasdaq annual table schema is unsupported")
    if tuple((row[1], row[2]) for row in rows) != _NASDAQ_ROW_CENSUS:
        raise CalendarSourceFormatError("Nasdaq annual semantic row census is unsupported")
    if "Nasdaq will continue to send alerts" not in joined:
        raise CalendarSourceFormatError("Nasdaq early-close source notice is incomplete")
    closures: list[date] = []
    early: list[date] = []
    for displayed_date, label, status in rows:
        day = _full_date(displayed_date)
        if day.year != 2026:
            raise CalendarSourceFormatError("Nasdaq row escapes annual coverage")
        (closures if status == "Closed" else early).append(day)
    return _semantic(
        venue_id="NASDAQ", acquisition_sha256=acquisition_sha256,
        parser_id="NASDAQ_TRADER_US_EQUITIES_HTML",
        source_format_version="NASDAQ_US_EQUITIES_2026_HTML_V1", years={2026},
        closures=closures, early_closes=early,
    )


_CBOE_HEADER = ("Holiday", "Date")
_CBOE_LABELS = (
    "New Year's Day", "Martin Luther King, Jr. Day", "Presidents' Day",
    "Good Friday", "Memorial Day", "Juneteenth Holiday",
    "Independence Day Observed", "Labor Day", "Thanksgiving Day",
    "Thanksgiving Early Close", "Christmas Early Close", "Christmas Day",
)
_CBOE_EARLY_LABELS = {"Thanksgiving Early Close", "Christmas Early Close"}


def parse_cboe_calendar(response_bytes: bytes, acquisition_sha256: str) -> dict[str, Any]:
    document, text, tables = _html(response_bytes)
    joined = " ".join(text)
    if (
        "Cboe BZX and EDGX Equities Trading Hours" not in document
        or "Equities Holiday Schedule" not in joined
        or "/us/equities/holidays/csv/" not in document
        or "Regular Trading Session" not in document
    ):
        raise CalendarSourceFormatError("Cboe BZX product scope or calendar heading missing")
    if re.findall(r"(20\d{2}) Equities Holiday Schedule", joined) != ["2026"]:
        raise CalendarSourceFormatError("Cboe annual coverage is ambiguous")
    header, rows = _calendar_table(tables, lambda cells: cells == _CBOE_HEADER)
    if header != _CBOE_HEADER or any(len(row) != 2 for row in rows):
        raise CalendarSourceFormatError("Cboe annual table schema is unsupported")
    if tuple(row[0] for row in rows) != _CBOE_LABELS:
        raise CalendarSourceFormatError("Cboe annual semantic row census is unsupported")
    closures: list[date] = []
    early: list[date] = []
    for label, displayed_date in rows:
        day = _date_without_year(displayed_date, 2026)
        (early if label in _CBOE_EARLY_LABELS else closures).append(day)
    return _semantic(
        venue_id="CBOE_BZX", acquisition_sha256=acquisition_sha256,
        parser_id="CBOE_BZX_US_EQUITIES_NEXTJS_HTML",
        source_format_version="CBOE_BZX_EQUITIES_2026_HTML_V1", years={2026},
        closures=closures, early_closes=early,
    )


PARSERS = {
    "NYSE_HOLIDAYS_TRADING_HOURS_HTML": parse_nyse_calendar,
    "NASDAQ_TRADER_US_EQUITIES_HTML": parse_nasdaq_calendar,
    "CBOE_BZX_US_EQUITIES_NEXTJS_HTML": parse_cboe_calendar,
}


def derive_schedule(parser_id: str, response_bytes: bytes, acquisition_sha256: str) -> dict[str, Any]:
    try:
        parser = PARSERS[parser_id]
    except KeyError as error:
        raise CalendarSourceFormatError("UNSUPPORTED_SOURCE_FORMAT") from error
    return parser(response_bytes, acquisition_sha256)


def status_for_date(schedule: dict[str, Any], trade_date: date) -> str:
    covered = any(
        date.fromisoformat(interval["coverage_start"]) <= trade_date <= date.fromisoformat(interval["coverage_end"])
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
