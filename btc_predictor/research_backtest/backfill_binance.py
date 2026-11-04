"""Binance public-archive adapters for RBT-003 (Part A, offline).

Sources (RBT-002 source ranking, probed 2026-10-01; licence CC BY-NC-SA 4.0):

- USD-M ``BTCUSDT`` funding, monthly ``fundingRate`` archive
  (``calc_time, funding_interval_hours, last_funding_rate``): a
  :class:`FundingRate` per settlement, ``observation_time = calc_time``
  (RBT-002 pin ``FUNDING_SETTLEMENT``). A settlement whose accrual period
  starts before 2020-01-01 prices the prohibited window: it is excluded and
  only its instant is recorded.
- USD-M ``BTCUSDT`` open interest, daily ``metrics`` archive (5-minute rows):
  the ``hh:00`` row's ``sum_open_interest_value`` in USD (pin
  ``OPEN_INTEREST_HOURLY_SNAPSHOT_USD``). Owner ruling 4 (2026-11-04):
  byte-identical duplicates of an ``hh:00`` row collapse; differing duplicates
  leave that hour without a snapshot, recorded as a gap.
- USD-M ``BTCUSDT`` perpetual volume, monthly ``1h`` klines: ``open_time`` is
  the interval start (pin ``PERP_VOLUME_INTERVAL_START``); volume in BTC and
  the quote volume as USD notional, the columns RBT-002 named.
- COIN-M ``BTCUSD`` quarterly basis under ``FUTURES_BASIS_CONTRACT_V1``: the
  futures ``1h`` close over the COIN-M index ``1h`` close, minus one, at the
  hour close ``t``, rounded to the raw table's 18 places as ``NUMERIC(38,18)``
  rounds, and the annualised rate derived from that stored value through the
  replay builder's own :func:`replay_inputs_v2.contract_annualized_basis_rate`
  (RBT-001A ruling 6).
- The ``FUTURES_BASIS_CONTRACT_LISTING_EVIDENCE_V1`` file (RBT-001A ruling 4):
  the contracts the archive lists, each with the open time of its first ``1h``
  kline and its delivery instant. Owner ruling 2 (2026-11-04): the delivery
  instant is the symbol's ``YYMMDD`` date at 08:00 UTC, checked against the
  archive (last kline open plus one hour) for every contract delivered inside
  the data window, so nothing from 2026 is read.

Every archive is checked against its published ``.CHECKSUM`` before it is read.
Only files whose period lies inside the data window are ever requested: each
URL builder refuses a month or day outside it, and :func:`verified_archive`
refuses any URL that does not name an in-window archive period before the
transport is called (review F7), so the guard does not depend on which reader
built the URL.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ElementTree
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Context, Decimal, DivisionByZero, InvalidOperation, Overflow, localcontext
from typing import Any
from urllib.parse import urlencode

from btc_predictor.data import FundingRate, FuturesBasis, OpenInterest, PerpVolume
from btc_predictor.research_backtest import replay_inputs_v2 as v2
from btc_predictor.research_backtest.backfill_sources import (
    DATA_WINDOW_END,
    DATA_WINDOW_START,
    LAST_DATA_DAY,
    BackfillRefused,
    Fetched,
    Fetcher,
    data_rows,
    data_window_days,
    data_window_months,
    from_epoch_milliseconds,
    hours_of,
    month_end,
    require_observation_in_window,
    sha256_hex,
    single_csv_member,
)


BINANCE_EXCHANGE = "binance"
BINANCE_PROVIDER = "binance_public_data"
BINANCE_LICENCE = "CC BY-NC-SA 4.0 (binance-public-data TERMS_AND_CONDITIONS.md)"
BINANCE_ARCHIVE_BASE = "https://data.binance.vision/data/futures"
BINANCE_ARCHIVE_LISTING_URL = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
USDM_SYMBOL = "BTCUSDT"
COINM_INDEX_SYMBOL = "BTCUSD"
COINM_KLINES_PREFIX = "data/futures/cm/monthly/klines/"
COINM_DELIVERY_SYMBOL = re.compile(r"BTCUSD_(\d{2})(\d{2})(\d{2})")
COINM_DELIVERY_TIME_UTC = time(8, 0)  # owner ruling 2 (2026-11-04)
COINM_LISTING_LOOKBACK_MONTHS = 12
MAX_LISTING_PAGES = 100
OPEN_INTEREST_UNIT = "USD"
PERP_VOLUME_UNIT = "BTC"
TIMEFRAME = "1h"

FUNDING_HEADER = ("calc_time", "funding_interval_hours", "last_funding_rate")
METRICS_HEADER = (
    "create_time",
    "symbol",
    "sum_open_interest",
    "sum_open_interest_value",
    "count_toptrader_long_short_ratio",
    "sum_toptrader_long_short_ratio",
    "count_long_short_ratio",
    "sum_taker_long_short_vol_ratio",
)
# The klines column order is fixed; files written with a header spell the quote
# column one of these two ways (RBT-002 recorded the order, not a header).
KLINES_HEADERS = tuple(
    (
        "open_time", "open", "high", "low", "close", "volume", "close_time", quote,
        "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore",
    )
    for quote in ("quote_volume", "quote_asset_volume")
)

GAP_SNAPSHOT_MISSING = "OPEN_INTEREST_SNAPSHOT_MISSING"
GAP_DIFFERING_DUPLICATE = "OPEN_INTEREST_DIFFERING_DUPLICATE"
GAP_ARCHIVE_DAY_MISSING = "OPEN_INTEREST_ARCHIVE_DAY_MISSING"
GAP_FUTURES_KLINE_MISSING = "FUTURES_KLINE_MISSING"
GAP_INDEX_KLINE_MISSING = "INDEX_KLINE_MISSING"
EXCLUDED_FUNDING_PRICES_PRE_2020 = "FUNDING_SETTLEMENT_PRICES_PRE_2020"

_HOUR = timedelta(hours=1)
_KLINE_CLOSE_OFFSET = timedelta(hours=1) - timedelta(milliseconds=1)
_RATE_QUANTUM = v2.RAW_NUMERIC_QUANTUM
_WIDE_CONTEXT = Context(prec=80, rounding=ROUND_HALF_EVEN, traps=[InvalidOperation, DivisionByZero, Overflow])
_S3_NAMESPACE = "{http://s3.amazonaws.com/doc/2006-03-01/}"
_ARCHIVE_PERIOD = re.compile(r"-(\d{4})-(\d{2})(?:-(\d{2}))?\.zip")


# --- URLs (each one names a period inside the data window) ----------------------------------


def _window_month(month: Any) -> date:
    if type(month) is not date or month not in data_window_months():
        raise BackfillRefused("REQUEST_OUTSIDE_DATA_WINDOW", f"archive month {month!r} is not a month inside the data window")
    return month


def _window_day(day: Any) -> date:
    if type(day) is not date or not DATA_WINDOW_START.date() <= day <= LAST_DATA_DAY:
        raise BackfillRefused("REQUEST_OUTSIDE_DATA_WINDOW", f"archive day {day!r} is not a day inside the data window")
    return day


def funding_archive_url(month: date) -> str:
    month = _window_month(month)
    return f"{BINANCE_ARCHIVE_BASE}/um/monthly/fundingRate/{USDM_SYMBOL}/{USDM_SYMBOL}-fundingRate-{month:%Y-%m}.zip"


def metrics_archive_url(day: date) -> str:
    day = _window_day(day)
    return f"{BINANCE_ARCHIVE_BASE}/um/daily/metrics/{USDM_SYMBOL}/{USDM_SYMBOL}-metrics-{day:%Y-%m-%d}.zip"


def usdm_klines_archive_url(month: date) -> str:
    month = _window_month(month)
    return f"{BINANCE_ARCHIVE_BASE}/um/monthly/klines/{USDM_SYMBOL}/1h/{USDM_SYMBOL}-1h-{month:%Y-%m}.zip"


def coinm_klines_archive_url(contract: str, month: date) -> str:
    month = _window_month(month)
    return f"{BINANCE_ARCHIVE_BASE}/cm/monthly/klines/{contract}/1h/{contract}-1h-{month:%Y-%m}.zip"


def coinm_index_archive_url(month: date) -> str:
    month = _window_month(month)
    return (
        f"{BINANCE_ARCHIVE_BASE}/cm/monthly/indexPriceKlines/{COINM_INDEX_SYMBOL}/1h/"
        f"{COINM_INDEX_SYMBOL}-1h-{month:%Y-%m}.zip"
    )


def require_archive_url_in_window(url: str) -> None:
    """An archive URL must be a Binance archive whose file names an in-window month or day."""

    match = _ARCHIVE_PERIOD.search(url) if isinstance(url, str) and url.startswith(f"{BINANCE_ARCHIVE_BASE}/") else None
    if match is None or match.end() != len(url) or "?" in url or "#" in url:
        raise BackfillRefused("REQUEST_OUTSIDE_DATA_WINDOW", f"{url!r} is not a Binance archive naming a data-window period")
    year, month, day = match.groups()
    try:
        period = date(int(year), int(month), int(day or 1))
    except ValueError:
        raise BackfillRefused("REQUEST_OUTSIDE_DATA_WINDOW", f"{url!r} names no calendar period") from None
    if day is None:
        _window_month(period)
    else:
        _window_day(period)


def archive_listing_url(prefix: str, marker: str | None = None) -> str:
    query = {"delimiter": "/", "prefix": prefix}
    if marker is not None:
        query["marker"] = marker
    return f"{BINANCE_ARCHIVE_LISTING_URL}?{urlencode(query)}"


def _archive_name(url: str) -> str:
    return url.rsplit("/", 1)[1]


def verified_archive(fetcher: Fetcher, url: str, *, allow_not_found: bool = False) -> Fetched | None:
    """An archive checked against its published ``.CHECKSUM`` (``None``: an allowed 404)."""

    require_archive_url_in_window(url)
    archive = fetcher.fetch_optional(url, allow_not_found=allow_not_found)
    if archive is None:
        return None
    checksum = fetcher.fetch(f"{url}.CHECKSUM").body
    try:
        expected, name = checksum.decode("ascii").split()
    except (UnicodeDecodeError, ValueError):
        raise BackfillRefused("ARCHIVE_CHECKSUM_MISMATCH", f"{url}.CHECKSUM is not '<sha256>  <file>'") from None
    if name != _archive_name(url) or expected != archive.sha256:
        raise BackfillRefused("ARCHIVE_CHECKSUM_MISMATCH", f"{url}: the archive does not match its published checksum")
    return archive


def _decimal(text: str, what: str) -> Decimal:
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"{what} {text!r} is not a decimal") from None
    if not value.is_finite():
        raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"{what} {text!r} is not finite")
    return value


def _in_month(instant: datetime, month: date, what: str) -> None:
    if not datetime(month.year, month.month, 1, tzinfo=UTC) <= instant < month_end(month):
        raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"{what} {instant.isoformat()} is not in the archive's month {month:%Y-%m}")


# --- funding ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class FundingArchive:
    rows: tuple[FundingRate, ...]
    excluded: tuple[tuple[datetime, str], ...]  # (settlement, reason): instants only, never values


def parse_funding_archive(data: bytes, month: date, *, source: str, retrieved_at: datetime) -> FundingArchive:
    what = f"funding {month:%Y-%m}"
    name = f"{USDM_SYMBOL}-fundingRate-{month:%Y-%m}.csv"
    rows: dict[datetime, FundingRate] = {}
    excluded: list[tuple[datetime, str]] = []
    for row in data_rows(single_csv_member(data, name, what), FUNDING_HEADER, what):
        settled = require_observation_in_window(from_epoch_milliseconds(row[0], f"{what} calc_time"), f"{what} settlement")
        _in_month(settled, month, f"{what} settlement")
        hours = _decimal(row[1], f"{what} funding_interval_hours")
        rate = _decimal(row[2], f"{what} last_funding_rate")
        seconds = hours * 3600
        if hours <= 0 or seconds != seconds.to_integral_value():
            raise BackfillRefused(
                "RESPONSE_SHAPE_REFUSED", f"{what} {settled.isoformat()}: the interval must be a positive whole number of seconds"
            )
        if settled in rows or any(instant == settled for instant, _ in excluded):
            raise BackfillRefused("DUPLICATE_PROVIDER_RECORD", f"{what}: settlement {settled.isoformat()} appears twice")
        if settled - timedelta(seconds=int(seconds)) < DATA_WINDOW_START:
            excluded.append((settled, EXCLUDED_FUNDING_PRICES_PRE_2020))
            continue
        rows[settled] = FundingRate(
            observation_time=settled,
            exchange=BINANCE_EXCHANGE,
            symbol=USDM_SYMBOL,
            instrument=USDM_SYMBOL,
            funding_rate=rate,
            funding_interval_hours=hours,
            provider=BINANCE_PROVIDER,
            source=source,
            available_at=retrieved_at,
            ingested_at=retrieved_at,
        )
    return FundingArchive(tuple(rows[key] for key in sorted(rows)), tuple(excluded))


def read_funding(fetcher: Fetcher, first_month: date, last_month: date) -> FundingArchive:
    rows: list[FundingRate] = []
    excluded: list[tuple[datetime, str]] = []
    for month in data_window_months(first_month, last_month):
        url = funding_archive_url(month)
        archive = _required(verified_archive(fetcher, url), url)
        parsed = parse_funding_archive(archive.body, month, source=url, retrieved_at=archive.retrieved_at)
        rows.extend(parsed.rows)
        excluded.extend(parsed.excluded)
    return FundingArchive(tuple(rows), tuple(excluded))


# --- open interest ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SnapshotGap:
    observation_time: datetime
    reason: str

    def as_record(self) -> dict[str, str]:
        return {"observation_time": self.observation_time.isoformat(), "reason": self.reason}


@dataclass(frozen=True)
class OpenInterestArchive:
    rows: tuple[OpenInterest, ...]
    gaps: tuple[SnapshotGap, ...]


def parse_metrics_archive(data: bytes, day: date, *, source: str, retrieved_at: datetime) -> OpenInterestArchive:
    """The day's ``hh:00`` USD snapshots (owner ruling 4 for duplicates)."""

    what = f"metrics {day.isoformat()}"
    name = f"{USDM_SYMBOL}-metrics-{day.isoformat()}.csv"
    by_hour: dict[datetime, list[list[str]]] = {}
    for row in data_rows(single_csv_member(data, name, what), METRICS_HEADER, what):
        try:
            instant = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
        except ValueError:
            raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"{what}: create_time {row[0]!r} is not 'YYYY-MM-DD HH:MM:SS'") from None
        require_observation_in_window(instant, f"{what} snapshot")
        if instant.date() != day:
            raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"{what}: create_time {row[0]} is not on the file's day")
        if row[1] != USDM_SYMBOL:
            raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"{what}: symbol {row[1]!r} is not {USDM_SYMBOL}")
        if (instant.minute, instant.second) == (0, 0):
            by_hour.setdefault(instant, []).append(row)
    rows: list[OpenInterest] = []
    gaps: list[SnapshotGap] = []
    for hour in hours_of(day):
        copies = by_hour.get(hour, [])
        if not copies:
            gaps.append(SnapshotGap(hour, GAP_SNAPSHOT_MISSING))
            continue
        if any(copy != copies[0] for copy in copies):
            gaps.append(SnapshotGap(hour, GAP_DIFFERING_DUPLICATE))
            continue
        value = _decimal(copies[0][3], f"{what} {hour.isoformat()} sum_open_interest_value")
        if value < 0:
            raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"{what} {hour.isoformat()}: open interest must be >= 0")
        rows.append(
            OpenInterest(
                observation_time=hour,
                exchange=BINANCE_EXCHANGE,
                symbol=USDM_SYMBOL,
                instrument=USDM_SYMBOL,
                open_interest=value,
                open_interest_unit=OPEN_INTEREST_UNIT,
                provider=BINANCE_PROVIDER,
                source=source,
                available_at=retrieved_at,
                ingested_at=retrieved_at,
            )
        )
    return OpenInterestArchive(tuple(rows), tuple(gaps))


def read_open_interest(fetcher: Fetcher, first_day: date, last_day: date) -> OpenInterestArchive:
    rows: list[OpenInterest] = []
    gaps: list[SnapshotGap] = []
    for day in data_window_days(first_day, last_day):
        url = metrics_archive_url(day)
        archive = verified_archive(fetcher, url, allow_not_found=True)
        if archive is None:
            gaps.extend(SnapshotGap(hour, GAP_ARCHIVE_DAY_MISSING) for hour in hours_of(day))
            continue
        parsed = parse_metrics_archive(archive.body, day, source=url, retrieved_at=archive.retrieved_at)
        rows.extend(parsed.rows)
        gaps.extend(parsed.gaps)
    return OpenInterestArchive(tuple(rows), tuple(gaps))


# --- 1h klines -------------------------------------------------------------------------------


@dataclass(frozen=True)
class Kline:
    open_time: datetime
    close: Decimal
    volume: Decimal
    quote_volume: Decimal


def parse_klines_archive(data: bytes, month: date, *, symbol: str, what: str) -> dict[datetime, Kline]:
    """One month of ``1h`` klines by open time; each closes one millisecond before the next hour."""

    name = f"{symbol}-1h-{month:%Y-%m}.csv"
    rows = single_csv_member(data, name, what)
    header = next((candidate for candidate in KLINES_HEADERS if rows and rows[0] == list(candidate)), KLINES_HEADERS[0])
    klines: dict[datetime, Kline] = {}
    for row in data_rows(rows, header, what):
        opened = require_observation_in_window(from_epoch_milliseconds(row[0], f"{what} open_time"), f"{what} kline")
        closed = from_epoch_milliseconds(row[6], f"{what} close_time")
        if (opened.minute, opened.second, opened.microsecond) != (0, 0, 0) or closed != opened + _KLINE_CLOSE_OFFSET:
            raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"{what}: {opened.isoformat()} is not a 1h kline")
        _in_month(opened, month, f"{what} kline")
        if opened in klines:
            raise BackfillRefused("DUPLICATE_PROVIDER_RECORD", f"{what}: kline {opened.isoformat()} appears twice")
        close = _decimal(row[4], f"{what} close")
        if close <= 0:
            raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"{what} {opened.isoformat()}: the close must be positive")
        klines[opened] = Kline(opened, close, _decimal(row[5], f"{what} volume"), _decimal(row[7], f"{what} quote volume"))
    return klines


def perp_volumes_from_klines(klines: Mapping[datetime, Kline], *, source: str, retrieved_at: datetime) -> tuple[PerpVolume, ...]:
    volumes = []
    for opened in sorted(klines):
        kline = klines[opened]
        if kline.volume < 0 or kline.quote_volume < 0:
            raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"perp volume {opened.isoformat()}: volumes must be >= 0")
        volumes.append(
            PerpVolume(
                observation_time=opened,
                exchange=BINANCE_EXCHANGE,
                symbol=USDM_SYMBOL,
                timeframe=TIMEFRAME,
                volume=kline.volume,
                volume_unit=PERP_VOLUME_UNIT,
                notional_usd=kline.quote_volume,
                provider=BINANCE_PROVIDER,
                source=source,
                available_at=retrieved_at,
                ingested_at=retrieved_at,
            )
        )
    return tuple(volumes)


def read_perp_volume(fetcher: Fetcher, first_month: date, last_month: date) -> tuple[PerpVolume, ...]:
    volumes: list[PerpVolume] = []
    for month in data_window_months(first_month, last_month):
        url = usdm_klines_archive_url(month)
        archive = _required(verified_archive(fetcher, url), url)
        klines = parse_klines_archive(archive.body, month, symbol=USDM_SYMBOL, what=f"perp klines {month:%Y-%m}")
        volumes.extend(perp_volumes_from_klines(klines, source=url, retrieved_at=archive.retrieved_at))
    return tuple(volumes)


# --- COIN-M contracts, listing and basis -----------------------------------------------------


def parse_archive_listing(data: bytes, prefix: str) -> tuple[tuple[str, ...], str | None]:
    """The directory names under ``prefix`` in one S3 listing page, and the next marker."""

    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError:
        raise BackfillRefused("RESPONSE_SHAPE_REFUSED", "the archive listing is not XML") from None
    if root.tag != f"{_S3_NAMESPACE}ListBucketResult":
        raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"the archive listing root is {root.tag!r}")
    names = []
    for element in root.findall(f"{_S3_NAMESPACE}CommonPrefixes/{_S3_NAMESPACE}Prefix"):
        text = element.text or ""
        if not text.startswith(prefix) or not text.endswith("/") or "/" in text[len(prefix):-1]:
            raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"listing entry {text!r} is not a directory under {prefix}")
        names.append(text[len(prefix):-1])
    truncated = root.findtext(f"{_S3_NAMESPACE}IsTruncated")
    if truncated not in ("true", "false"):
        raise BackfillRefused("RESPONSE_SHAPE_REFUSED", "the archive listing does not say whether it is truncated")
    marker = root.findtext(f"{_S3_NAMESPACE}NextMarker") if truncated == "true" else None
    if truncated == "true" and not marker:
        raise BackfillRefused("RESPONSE_SHAPE_REFUSED", "a truncated archive listing carries no next marker")
    return tuple(names), marker


def read_coinm_contracts(fetcher: Fetcher) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Every ``BTCUSD_YYMMDD`` delivery contract the archive lists, by delivery, and the pages' digests."""

    names: list[str] = []
    digests: list[str] = []
    markers: set[str] = set()
    marker: str | None = None
    for _ in range(MAX_LISTING_PAGES):
        page = fetcher.fetch(archive_listing_url(COINM_KLINES_PREFIX, marker))
        digests.append(page.sha256)
        entries, marker = parse_archive_listing(page.body, COINM_KLINES_PREFIX)
        names.extend(entries)
        if marker is None:
            break
        if marker in markers:
            raise BackfillRefused("CONTINUATION_CHAIN_REFUSED", f"the archive listing repeats marker {marker!r}")
        markers.add(marker)
    else:
        raise BackfillRefused("CONTINUATION_CHAIN_REFUSED", f"the archive listing runs past {MAX_LISTING_PAGES} pages")
    contracts = sorted({name for name in names if COINM_DELIVERY_SYMBOL.fullmatch(name)}, key=contract_delivery_at)
    return tuple(contracts), tuple(digests)


def contract_delivery_at(contract: str) -> datetime:
    """Owner ruling 2 (2026-11-04): the symbol's ``YYMMDD`` date at 08:00 UTC."""

    match = COINM_DELIVERY_SYMBOL.fullmatch(contract)
    if match is None:
        raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"{contract!r} is not a BTCUSD_YYMMDD delivery contract")
    year, month, day = (int(part) for part in match.groups())
    try:
        return datetime.combine(date(2000 + year, month, day), COINM_DELIVERY_TIME_UTC, tzinfo=UTC)
    except ValueError:
        raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"{contract!r} names no calendar date") from None


def _shift_months(month: date, offset: int) -> date:
    index = month.year * 12 + month.month - 1 + offset
    return date(index // 12, index % 12 + 1, 1)


@dataclass(frozen=True)
class ContractKlines:
    """A contract's klines inside the data window and its listing as the archive shows it."""

    listing: v2.FuturesBasisContractListing
    klines: Mapping[datetime, Kline]
    retrieved_by_month: Mapping[date, datetime]
    sources: tuple[str, ...]
    archive_sha256: tuple[str, ...]

    @property
    def retrieved_at(self) -> datetime:
        """The latest retrieval of any of the contract's archives (the listing file's instant)."""

        return max(self.retrieved_by_month.values())


def read_contract_klines(fetcher: Fetcher, contract: str) -> ContractKlines | None:
    """The contract's in-window months, or ``None`` when it is not listed inside the window.

    Months are requested from twelve before delivery (clipped to the window)
    through the delivery month or December 2025, whichever is earlier. A month
    before the first archived one may be absent; the first requested month must
    be absent, or the listing start is unproven; every later month must exist.
    """

    delivery = contract_delivery_at(contract)
    if delivery <= DATA_WINDOW_START:
        return None
    delivery_month = date(delivery.year, delivery.month, 1)
    first_month = max(_shift_months(delivery_month, -COINM_LISTING_LOOKBACK_MONTHS), DATA_WINDOW_START.date())
    months = data_window_months(first_month, min(delivery.date(), LAST_DATA_DAY))
    klines: dict[datetime, Kline] = {}
    sources: list[str] = []
    digests: list[str] = []
    retrieved: dict[date, datetime] = {}
    for index, month in enumerate(months):
        url = coinm_klines_archive_url(contract, month)
        archive = verified_archive(fetcher, url, allow_not_found=True)
        if archive is None:
            if klines:
                raise BackfillRefused("ARCHIVE_MONTH_MISSING", f"{contract}: {month:%Y-%m} is missing after its first archived month")
            continue
        if not klines and index == 0:
            raise BackfillRefused(
                "LISTING_START_UNPROVEN",
                f"{contract}: the first requested month {month:%Y-%m} is already archived, so the listing may start earlier",
            )
        klines.update(parse_klines_archive(archive.body, month, symbol=contract, what=f"{contract} {month:%Y-%m}"))
        sources.append(url)
        digests.append(archive.sha256)
        retrieved[month] = archive.retrieved_at
    if not klines:
        return None
    first = min(klines)
    later = [opened for opened in klines if opened + _HOUR > delivery]
    if later:
        raise BackfillRefused("DELIVERY_INSTANT_MISMATCH", f"{contract}: a kline at {later[0].isoformat()} runs past the delivery")
    if delivery < DATA_WINDOW_END and max(klines) + _HOUR != delivery:
        raise BackfillRefused(
            "DELIVERY_INSTANT_MISMATCH",
            f"{contract}: the last archived kline closes at {(max(klines) + _HOUR).isoformat()}, not the delivery {delivery.isoformat()}",
        )
    return ContractKlines(
        v2.FuturesBasisContractListing(contract, first, delivery), klines, retrieved, tuple(sources), tuple(digests)
    )


def basis_rate(futures_close: Decimal, index_close: Decimal) -> Decimal:
    """``futures / index - 1`` rounded half away from zero to 18 places, as ``NUMERIC(38,18)`` stores it."""

    with localcontext(_WIDE_CONTEXT):
        return (futures_close / index_close - 1).quantize(_RATE_QUANTUM, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class BasisGap:
    instrument: str
    observation_time: datetime
    reason: str

    def as_record(self) -> dict[str, str]:
        return {"instrument": self.instrument, "observation_time": self.observation_time.isoformat(), "reason": self.reason}


def _month_of(instant: datetime) -> date:
    return date(instant.year, instant.month, 1)


def basis_rows(
    contract: ContractKlines,
    index: Mapping[datetime, Kline],
    *,
    index_retrieved: Mapping[date, datetime],
    source: str,
) -> tuple[tuple[FuturesBasis, ...], tuple[BasisGap, ...]]:
    """One row per hour close ``t`` in ``[first + 1h, delivery)`` inside the window, with both klines.

    A row's ``available_at`` is the later retrieval of the two archives its
    klines came from (the contract's and the index's month of ``t - 1h``), not
    of any other month (review F3).
    """

    listing = contract.listing
    rows: list[FuturesBasis] = []
    gaps: list[BasisGap] = []
    t = listing.first_kline_open_at + _HOUR
    while t < listing.delivery_at and t < DATA_WINDOW_END:
        future = contract.klines.get(t - _HOUR)
        spot = index.get(t - _HOUR)
        if future is None or spot is None:
            gaps.append(BasisGap(listing.instrument, t, GAP_FUTURES_KLINE_MISSING if future is None else GAP_INDEX_KLINE_MISSING))
        else:
            rate = basis_rate(future.close, spot.close)
            month = _month_of(t - _HOUR)
            retrieved_at = max(contract.retrieved_by_month[month], index_retrieved[month])
            rows.append(
                FuturesBasis(
                    observation_time=t,
                    exchange=v2.FUTURES_BASIS_EXCHANGE,
                    symbol=v2.FUTURES_BASIS_SYMBOL,
                    instrument=listing.instrument,
                    expiry=listing.delivery_at,
                    basis_rate=rate,
                    annualized_basis_rate=v2.contract_annualized_basis_rate(rate, t, listing.delivery_at),
                    provider=BINANCE_PROVIDER,
                    source=source,
                    available_at=retrieved_at,
                    ingested_at=retrieved_at,
                )
            )
        t += _HOUR
    return tuple(rows), tuple(gaps)


@dataclass(frozen=True)
class BasisCollection:
    rows: tuple[FuturesBasis, ...]
    gaps: tuple[BasisGap, ...]
    unlisted_in_window: tuple[str, ...]
    listing_bytes: bytes

    @property
    def listing_sha256(self) -> str:
        return sha256_hex(self.listing_bytes)

    def listing_evidence(self) -> v2.FuturesBasisListingEvidence:
        return v2.parse_futures_basis_listing_evidence(self.listing_bytes, expected_sha256=self.listing_sha256)


BASIS_SOURCE = "data.binance.vision cm monthly klines 1h / indexPriceKlines BTCUSD 1h"
LISTING_SOURCE = "data.binance.vision cm monthly klines 1h archive listing and contract klines"


def read_basis(fetcher: Fetcher) -> BasisCollection:
    """Every listed contract's basis rows inside the window, and the listing evidence file."""

    contracts, listing_digests = read_coinm_contracts(fetcher)
    listed: list[ContractKlines] = []
    unlisted: list[str] = []
    for contract in contracts:
        read = read_contract_klines(fetcher, contract)
        if read is None:
            unlisted.append(contract)
        else:
            listed.append(read)
    if not listed:
        raise BackfillRefused("RESPONSE_SHAPE_REFUSED", "no BTCUSD delivery contract is archived inside the data window")
    first_month = min(item.listing.first_kline_open_at for item in listed).date()
    last_needed = min(max(item.listing.delivery_at for item in listed).date(), LAST_DATA_DAY)
    index: dict[datetime, Kline] = {}
    index_retrieved: dict[date, datetime] = {}
    for month in data_window_months(first_month, last_needed):
        url = coinm_index_archive_url(month)
        archive = _required(verified_archive(fetcher, url), url)
        index.update(parse_klines_archive(archive.body, month, symbol=COINM_INDEX_SYMBOL, what=f"index {month:%Y-%m}"))
        index_retrieved[month] = archive.retrieved_at
    rows: list[FuturesBasis] = []
    gaps: list[BasisGap] = []
    for item in listed:
        contract_rows, contract_gaps = basis_rows(item, index, index_retrieved=index_retrieved, source=BASIS_SOURCE)
        rows.extend(contract_rows)
        gaps.extend(contract_gaps)
    # the listing pages and every contract archive the listing rests on (RBT-001A ruling 4)
    listing_bytes = v2.futures_basis_listing_evidence_bytes(
        source=LISTING_SOURCE,
        licence=BINANCE_LICENCE,
        retrieved_at=max(item.retrieved_at for item in listed),
        response_sha256=[*listing_digests, *(digest for item in listed for digest in item.archive_sha256)],
        contracts=[item.listing for item in listed],
    )
    rows.sort(key=lambda row: (row.observation_time, row.instrument))
    return BasisCollection(tuple(rows), tuple(gaps), tuple(unlisted), listing_bytes)


def gap_records(gaps: Sequence[Any]) -> list[dict[str, str]]:
    return [gap.as_record() for gap in gaps]


def _required(archive: Fetched | None, url: str) -> Fetched:
    if archive is None:  # unreachable: a 404 refuses unless it is allowed
        raise BackfillRefused("ARCHIVE_MONTH_MISSING", f"{url} is missing")
    return archive
