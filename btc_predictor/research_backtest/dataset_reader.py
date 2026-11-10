"""RBT-003 Part B dataset build: the window-bounded database reader.

The dataset build reads the raw rows RBT-003's replay datasets are built from:

- the three ``PRICE_SOURCE_POLICY_V1`` venues' ``1h`` OHLCV (Bitstamp's is also
  the shared volume);
- the series RBT-003 collected: Binance funding, open interest, perpetual
  volume and COIN-M basis, Kraken Futures liquidations, and CoinGlass ETF flows.

Every query names one series by its identity and bounds it to the data window
``[2020-01-01 00:00, 2026-01-01 00:00)``. A row is selected only when the whole
interval it observes lies inside the window, which is the interval the replay
builders admit (RBT-001 design decision 1; RBT-001A):

- a bar or a ``1h`` aggregate covers ``[t, t + 1h)``;
- a funding settlement covers ``(S - interval, S]``;
- a snapshot covers its instant;
- an ETF flow covers its UTC day.

No query selects a row dated in the prohibited window, the holdout or the
reserve (policy V7 section 3; RBT-002: "RBT-003 loaders must bound every query
to the data window").

A guard then counts each table's rows whose observation instant lies in the
window, reading no value. If the series left any such row unread (another
series, or an interval reaching outside the window), the read refuses, so a
dataset never silently omits a row.

The caller supplies a read-only connection; the dataset build opens one
read-only, repeatable-read transaction, so every query sees one snapshot. Rows
become the owners' records unchanged: numbers stay the ``NUMERIC`` columns'
Decimals, and instants are normalized to UTC.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import Float, Table, and_, cast, func, literal_column, select, text

from btc_predictor.data import EtfFlow, FundingRate, FuturesBasis, Liquidation, OhlcvBar, OpenInterest, PerpVolume
from btc_predictor.db import raw
from btc_predictor.research_backtest import backfill_binance as binance
from btc_predictor.research_backtest import backfill_coinglass as coinglass
from btc_predictor.research_backtest import backfill_kraken as kraken
from btc_predictor.research_backtest import replay_inputs as v1
from btc_predictor.research_backtest import replay_inputs_v2 as v2

READER_VERSION = "RBT003_WINDOW_BOUNDED_DATASET_READER_V1"

WINDOW_START = v1.DATA_WINDOW.start
WINDOW_END = v1.DATA_WINDOW.end  # exclusive: the holdout's first instant
LAST_HOUR_START = WINDOW_END - timedelta(hours=1)  # [t, t + 1h) lies in the window iff t <= this
FIRST_DAY = WINDOW_START.date()
LAST_DAY = (WINDOW_END - timedelta(days=1)).date()

INTERVAL_HOUR = "HOUR"  # [t, t + 1h)
INTERVAL_FUNDING = "FUNDING_SETTLEMENT"  # (S - funding_interval_hours, S]
INTERVAL_INSTANT = "INSTANT"
INTERVAL_UTC_DAY = "UTC_DAY"

DATASET_REFUSAL_REASON_CODES = (
    "DATABASE_NOT_READ_ONLY",
    "DATASET_ROWS_UNREAD",
    "DATASET_RECORD_REFUSED",
    "EVIDENCE_UNIT_REFUSED",
    "EVIDENCE_MISMATCH",
    "DATASET_FILE_REFUSED",
    "DATASET_EXISTS",
    "DATASET_NOT_REPRODUCED",
    "CODE_COMMIT_REFUSED",
    "PRIVATE_COMMIT_REFUSED",
)


class DatasetBuildRefused(ValueError):
    """The dataset build refuses, with a closed reason code; a message names a series, a file or a unit, never a value."""

    def __init__(self, reason_code: str, message: str) -> None:
        if reason_code not in DATASET_REFUSAL_REASON_CODES:
            raise ValueError(f"unknown dataset refusal code {reason_code!r}")
        super().__init__(f"{reason_code}: {message}")
        self.reason_code = reason_code


@dataclass(frozen=True)
class DatasetSeries:
    """One series the build reads: its raw table, owner record, identity and observed interval."""

    name: str
    table: Table
    record: type
    identity: tuple[tuple[str, str], ...]
    interval: str

    @property
    def instant_column(self) -> Any:
        if self.table is raw.btc_ohlcv:
            return self.table.c.timestamp
        if self.table is raw.etf_flows:
            return self.table.c.observation_date
        return self.table.c.observation_time

    @property
    def primary_key(self) -> tuple[str, ...]:
        return tuple(column.name for column in self.table.primary_key.columns)

    def as_record(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "table": f"{self.table.schema}.{self.table.name}",
            "identity": dict(self.identity),
            "interval": self.interval,
        }


def _venue_series(venue: v1.ReplayVenue) -> DatasetSeries:
    return DatasetSeries(
        f"ohlcv_1h_{venue.venue_id.lower()}",
        raw.btc_ohlcv,
        OhlcvBar,
        (("exchange", venue.exchange), ("symbol", venue.symbol), ("timeframe", v1.REPLAY_SOURCE_TIMEFRAME), ("provider", venue.provider)),
        INTERVAL_HOUR,
    )


_USDM = (("exchange", binance.BINANCE_EXCHANGE), ("symbol", binance.USDM_SYMBOL))
SERIES: tuple[DatasetSeries, ...] = (
    *(_venue_series(venue) for venue in v1.REPLAY_VENUES),
    DatasetSeries(
        "funding_rates", raw.funding_rates, FundingRate,
        (*_USDM, ("instrument", binance.USDM_SYMBOL), ("provider", binance.BINANCE_PROVIDER)), INTERVAL_FUNDING,
    ),
    DatasetSeries(
        "open_interest", raw.open_interest, OpenInterest,
        (*_USDM, ("instrument", binance.USDM_SYMBOL), ("open_interest_unit", binance.OPEN_INTEREST_UNIT), ("provider", binance.BINANCE_PROVIDER)),
        INTERVAL_INSTANT,
    ),
    DatasetSeries(
        "perp_volume", raw.perp_volume, PerpVolume,
        (*_USDM, ("timeframe", binance.TIMEFRAME), ("volume_unit", binance.PERP_VOLUME_UNIT), ("provider", binance.BINANCE_PROVIDER)),
        INTERVAL_HOUR,
    ),
    DatasetSeries(
        "futures_basis", raw.futures_basis, FuturesBasis,
        (("exchange", v2.FUTURES_BASIS_EXCHANGE), ("symbol", v2.FUTURES_BASIS_SYMBOL), ("provider", binance.BINANCE_PROVIDER)),
        INTERVAL_INSTANT,
    ),
    DatasetSeries(
        "liquidations", raw.liquidations, Liquidation,
        (
            ("exchange", kraken.KRAKEN_EXCHANGE), ("symbol", kraken.KRAKEN_SYMBOL), ("timeframe", kraken.KRAKEN_TIMEFRAME),
            ("quantity_unit", kraken.QUANTITY_UNIT), ("provider", kraken.KRAKEN_PROVIDER),
        ),
        INTERVAL_HOUR,
    ),
    DatasetSeries("etf_flows", raw.etf_flows, EtfFlow, (("provider", coinglass.COINGLASS_PROVIDER),), INTERVAL_UTC_DAY),
)
SERIES_BY_NAME = {series.name: series for series in SERIES}
TABLES: tuple[Table, ...] = tuple(dict.fromkeys(series.table for series in SERIES))

DatasetRows = dict[str, tuple[Any, ...]]


def series_bounds(series: DatasetSeries) -> list[Any]:
    """The window bound of one series: the whole observed interval inside ``[WINDOW_START, WINDOW_END)``."""

    instant = series.instant_column
    if series.interval == INTERVAL_HOUR:
        return [instant >= WINDOW_START, instant <= LAST_HOUR_START]
    if series.interval == INTERVAL_FUNDING:
        interval_start = instant - cast(series.table.c.funding_interval_hours, Float) * literal_column("interval '1 hour'")
        return [interval_start >= WINDOW_START, instant < WINDOW_END]
    if series.interval == INTERVAL_INSTANT:
        return [instant >= WINDOW_START, instant < WINDOW_END]
    if series.interval == INTERVAL_UTC_DAY:
        return [instant >= FIRST_DAY, instant <= LAST_DAY]
    raise ValueError(f"unknown interval {series.interval!r}")  # unreachable: SERIES names only the four


def series_statement(series: DatasetSeries) -> Any:
    """The one query that reads a series: its identity and its window bound, every column of its table."""

    identity = [series.table.c[column] == value for column, value in series.identity]
    return select(*series.table.c).where(and_(*identity, *series_bounds(series)))


def table_count_statement(table: Table) -> Any:
    """Every row of ``table`` whose observation instant lies in the window, counted: no value is read."""

    instant = next(series.instant_column for series in SERIES if series.table is table)
    bound = (
        [instant >= FIRST_DAY, instant <= LAST_DAY] if table is raw.etf_flows else [instant >= WINDOW_START, instant < WINDOW_END]
    )
    return select(func.count()).select_from(table).where(and_(*bound))


READ_ONLY_STATEMENT = text("select current_setting('transaction_read_only')")


def _utc(value: Any, what: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise DatasetBuildRefused("DATASET_RECORD_REFUSED", f"{what} is not a timezone-aware instant")
    return value.astimezone(UTC)


def owner_record(series: DatasetSeries, row: Mapping[str, Any]) -> Any:
    """The owner record of one database row, field for field; instants normalized to UTC, numbers unchanged."""

    names = [field.name for field in dataclasses.fields(series.record)]
    if set(row) != set(names):
        raise DatasetBuildRefused("DATASET_RECORD_REFUSED", f"{series.name}: a row's columns are not the {series.record.__name__} fields")
    values = {}
    for name in names:
        value = row[name]
        if isinstance(value, datetime):
            value = _utc(value, f"{series.name}.{name}")
        elif isinstance(value, date) and name != "observation_date":
            raise DatasetBuildRefused("DATASET_RECORD_REFUSED", f"{series.name}.{name} is a date, not an instant")
        values[name] = value
    return series.record(**values)


def sorted_records(series: DatasetSeries, records: Any) -> tuple[Any, ...]:
    """Records in primary-key order, compared in Python (never a database collation)."""

    key = series.primary_key
    return tuple(sorted(records, key=lambda record: tuple(getattr(record, name) for name in key)))


def read_dataset_rows(connection: Any) -> DatasetRows:
    """Read every series, bounded to the data window, from one read-only connection (see the module docstring)."""

    if connection.execute(READ_ONLY_STATEMENT).scalar_one() != "on":
        raise DatasetBuildRefused("DATABASE_NOT_READ_ONLY", "the dataset build reads only through a read-only transaction")
    rows: DatasetRows = {}
    for series in SERIES:
        result = connection.execute(series_statement(series)).mappings().all()
        rows[series.name] = sorted_records(series, (owner_record(series, row) for row in result))
    for table in TABLES:
        in_window = connection.execute(table_count_statement(table)).scalar_one()
        read = sum(len(rows[series.name]) for series in SERIES if series.table is table)
        if in_window != read:
            raise DatasetBuildRefused(
                "DATASET_ROWS_UNREAD",
                f"raw.{table.name} holds in-window rows its series did not read (another series, or an interval outside the window)",
            )
    return rows
