"""Kraken Futures liquidation adapter for RBT-003 (Part A, offline).

``HISTORICAL_LIQUIDATION_HOUR_COMPLETENESS_V1`` (policy V7 section 4A) reads
the paginated REST execution log of ``PI_XBTUSD``:

- an hour ``[h, h+1)`` is observed when the log was read contiguously across it
  (an unbroken continuation chain, no error) and at least one execution of any
  order type is stamped in it; it is ``OBSERVED_WITH_EVENTS`` with a
  liquidation (``takerOrder.orderType == "Liquidation"``, RBT-002's probe) and
  ``OBSERVED_ZERO_EVENTS`` without one;
- an hour with no execution, or one overlapping a reported incident, is
  ``SOURCE_UNAVAILABLE``.

The quantity is EPIC X's by reference: USD notional is the execution quantity
times the ``PI_XBTUSD`` contract size of 1 USD, the side is the taker side
mapped by ``LIQUIDATION_SIDE_TO_POSITION`` (``sell`` liquidates a long), and an
unknown side refuses the day, as EPIC X's census invalidates the interval.

Corroboration (owner ruling 3, 2026-11-04): an observed hour ``AGREES`` when its
long-plus-short USD total, rounded half-even to the decimal places of Kraken's
published hourly liquidation-volume value, equals that value; otherwise it
``DISAGREES``, and the replay builder refuses the build (RBT-001A ruling 2). An
observed hour the series does not cover is ``SERIES_UNAVAILABLE``.

The execution page and chart response shapes are those RBT-002 recorded; both
empty forms reproduce its recorded SHA-256 values. Part B's first step checked
them live (2026-11-05): the chart's values are JSON strings holding a decimal
numeral, not JSON numbers, so a number is refused (owner ruling 5), and its
unit is USD contracts (two hours agreed exactly, owner ruling 3). Any other
unexpected field or shape refuses the response.

Each hour's evidence record (status, corroboration, execution count, the sorted
liquidation uids, the per-side quantities, the series value and the response
digests) is hashed into the ``evidence_sha256`` of RBT-001A's
:class:`LiquidationHourEvidence`, and the records are written to one
hash-bound ``HISTORICAL_LIQUIDATION_HOUR_EVIDENCE_V1`` file.

The series value is stored as its published spelling (the exact decimal,
exponent kept: ``1500.0`` is not ``1500``), because ruling 3 compares at the
published precision (review F6). The file's parser accepts nothing it cannot
re-derive: the declared rule, universe, order type, contract size, source and
licence; every hour inside the data window; the incident flag from the
declared incidents; the status from the incident flag, execution count and
liquidation uids; and the corroboration recomputed from the per-side
quantities and the stored series value. The collection's own typed hours are
read back through that parser.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import (
    MAX_EMAX,
    MIN_EMIN,
    ROUND_HALF_EVEN,
    Context,
    Decimal,
    DivisionByZero,
    Inexact,
    InvalidOperation,
    Overflow,
    localcontext,
)
from typing import Any
from urllib.parse import urlencode

from btc_predictor.data import Liquidation
from btc_predictor.research import prospective_integration_corpus as epic_x
from btc_predictor.research_backtest import replay_inputs as v1
from btc_predictor.research_backtest import replay_inputs_v2 as v2
from btc_predictor.research_backtest.backfill_sources import (
    BackfillRefused,
    Fetcher,
    canonical_json_bytes,
    data_window_days,
    epoch_milliseconds,
    from_epoch_milliseconds,
    hours_of,
    iso,
    midnight,
    require_observation_in_window,
    require_request_span,
    require_utc,
    sha256_hex,
)


KRAKEN_EXCHANGE = v2.LIQUIDATION_EXCHANGE
KRAKEN_SYMBOL = v2.LIQUIDATION_SYMBOL
KRAKEN_TIMEFRAME = v2.LIQUIDATION_TIMEFRAME
KRAKEN_PROVIDER = "kraken_futures_rest_history"
KRAKEN_LICENCE = "UNVERIFIED (RBT-002: no licence found; hashes only)"
EXECUTIONS_URL = f"https://futures.kraken.com/api/history/v2/market/{KRAKEN_SYMBOL}/executions"
LIQUIDATION_VOLUME_URL = f"https://futures.kraken.com/api/charts/v1/analytics/{KRAKEN_SYMBOL}/liquidation-volume"
LIQUIDATION_ORDER_TYPE = "Liquidation"
QUANTITY_UNIT = "contracts"
CONTRACT_SIZE_USD = epic_x.LIQUIDATION_CONTRACT_SIZE_USD
TAKER_DIRECTIONS = {"Buy": "buy", "Sell": "sell"}

HOUR_EVIDENCE_VERSION = "HISTORICAL_LIQUIDATION_HOUR_EVIDENCE_V1"
CORROBORATION_RULE = "LIQUIDATION_VOLUME_EQUAL_AT_SERIES_PRECISION_V1"
MAX_PAGES_PER_DAY = 10_000

# RBT-002's source ranking records one Tardis-reported incident inside the data
# window; Part B re-reads the incident list before collecting.
RBT002_RECORDED_INCIDENTS = (
    (datetime(2021, 11, 10, 5, 9, tzinfo=UTC), datetime(2021, 11, 10, 5, 19, tzinfo=UTC)),
)

_HOUR = timedelta(hours=1)
_DAY = timedelta(days=1)
_EXECUTION_FIELDS = frozenset(
    {"uid", "timestamp", "price", "quantity", "usdValue", "markPrice", "limitFilled", "takerOrder", "makerOrder"}
)
_PAGE_KEYS = frozenset({"elements", "len", "continuationToken"})
# a chart value is a JSON string holding a non-negative decimal numeral (Part B's live check, ruling 5)
_SERIES_NUMERAL = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")
# sums and the notional are exact or refused, whatever the caller's context (review F4)
_EXACT_CONTEXT = Context(prec=80, rounding=ROUND_HALF_EVEN, traps=[Inexact, InvalidOperation, DivisionByZero, Overflow])
# the widest exact sum one side of an hour may need before the 80-digit check (re-review R12-1)
EXACT_SUM_MAX_DIGITS = 10_000
# each side's quantity and notional fit the liquidation table's NUMERIC(38,18), as V2 requires of
# these rows: below 10^20, nothing past the 18th place (re-review R12-3)
RAW_NUMERIC_LIMIT = Decimal("1E+20")
RAW_NUMERIC_PLACES = 18
# the longest canonical spelling of a value that fits: 20 integer digits, the point and 18 places (re-review R12-6)
RAW_NUMERIC_SPELLING_MAX = 39
# a published value is spelled with a capital E, whatever the caller's ``capitals`` (re-review N3)
_SPELLING_CONTEXT = Context(capitals=1)
_HOUR_EVIDENCE_KEYS = frozenset(
    {
        "evidence_version", "rule", "corroboration_rule", "exchange", "symbol", "liquidation_order_type",
        "contract_size_usd", "source", "licence", "retrieved_at", "incidents", "hours",
    }
)
_SHA256 = re.compile(r"[0-9a-f]{64}")
_HOUR_RECORD_KEYS = frozenset(
    {
        "hour_start", "feed_status", "corroboration", "execution_count", "liquidation_uids", "long_quantity",
        "short_quantity", "series_value", "incident", "pages_sha256", "series_sha256",
    }
)


def _refuse_shape(message: str) -> Any:
    raise BackfillRefused("RESPONSE_SHAPE_REFUSED", message)


def _json(data: bytes, what: str) -> Any:
    try:
        # every JSON number is read exactly; one whose exponent decimal cannot hold refuses whatever the
        # caller's traps (re-review R12-5)
        with localcontext(_EXACT_CONTEXT):
            return json.loads(data, parse_float=Decimal)
    except (UnicodeDecodeError, ValueError):
        return _refuse_shape(f"{what} is not JSON")
    except InvalidOperation:
        return _refuse_shape(f"{what} holds a number no decimal can hold")
    except RecursionError:
        # a body nested past the decoder's depth refuses instead of raising (re-review R12-8)
        return _refuse_shape(f"{what} is nested too deeply to read")


def _quantity(value: Any, what: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        return _refuse_shape(f"{what} {value!r} is not a decimal")
    # read in the exact context, so the same text refuses the same way whatever the caller's traps (re-review R12-9)
    number = _numeral_value(str(value))
    if number is None:
        return _refuse_shape(f"{what} {value!r} is not a decimal")
    if not number.is_finite() or number <= 0:
        return _refuse_shape(f"{what} {value!r} must be positive")
    return number


# --- the execution log -----------------------------------------------------------------------


@dataclass(frozen=True)
class Execution:
    uid: str
    timestamp: datetime
    quantity: Decimal
    order_type: str
    direction: str


def executions_url(since: datetime, before: datetime, token: str | None = None) -> str:
    require_request_span(since, before, "an executions request")  # review F7: the window at the builder
    query: dict[str, Any] = {"since": epoch_milliseconds(since), "before": epoch_milliseconds(before), "sort": "asc"}
    if token is not None:
        query["continuationToken"] = token
    return f"{EXECUTIONS_URL}?{urlencode(query)}"


def parse_execution_page(data: bytes) -> tuple[tuple[Execution, ...], str | None]:
    """One page: ``{"elements": [...], "len": n}`` plus a ``continuationToken`` when more follow."""

    executions, _, token = _execution_page(data)
    return executions, token


def _element_identities(data: bytes) -> tuple[str, ...]:
    """Each element's identity: equal exactly when two elements are the same JSON value with every number
    spelled the same way (owner Part B ruling 13); whitespace and key order do not count.

    Two readings of the page, already read once by ``_json``: one with every number as its spelling (a
    string), one with every number as ``null``. A leaf that is a string in the first and ``null`` in the
    second is a number spelled that way; a string in both is that string; ``null`` in both is ``null``. So
    equal pairs mean equal values, number spellings and types alike.
    """

    try:
        spelled = json.loads(data, parse_int=str, parse_float=str, parse_constant=str)["elements"]
        typed = json.loads(data, parse_int=_no_value, parse_float=_no_value, parse_constant=_no_value)["elements"]
        return tuple(
            json.dumps([a, b], sort_keys=True, separators=(",", ":")) for a, b in zip(spelled, typed, strict=True)
        )
    except RecursionError:
        return _refuse_shape("an execution page is nested too deeply to compare its elements")


def _no_value(_: str) -> None:
    return None


def _execution_page(data: bytes) -> tuple[tuple[Execution, ...], tuple[str, ...], str | None]:
    payload = _json(data, "an execution page")
    if not isinstance(payload, dict) or not {"elements", "len"} <= set(payload) <= _PAGE_KEYS:
        return _refuse_shape(f"an execution page has keys {sorted(payload) if isinstance(payload, dict) else payload!r}")
    elements, count = payload["elements"], payload["len"]
    if not isinstance(elements, list) or type(count) is not int or count != len(elements):
        return _refuse_shape("an execution page's len does not count its elements")
    token = payload.get("continuationToken")
    if token is not None and (not isinstance(token, str) or not token):
        return _refuse_shape("a continuation token must be a non-empty string")
    executions = []
    for element in elements:
        try:
            execution = element["event"]["Execution"]["execution"]
            taker = execution["takerOrder"]
        except (KeyError, TypeError):
            return _refuse_shape("an element is not event.Execution.execution with a takerOrder")
        if not isinstance(execution, dict) or not _EXECUTION_FIELDS <= set(execution) or not isinstance(taker, dict):
            return _refuse_shape(f"an execution lacks the recorded fields {sorted(_EXECUTION_FIELDS)}")
        uid, order_type, direction = execution["uid"], taker.get("orderType"), taker.get("direction")
        if not all(isinstance(item, str) and item for item in (uid, order_type, direction)):
            return _refuse_shape("an execution needs a uid and the taker order's orderType and direction")
        executions.append(
            Execution(
                uid=uid,
                timestamp=from_epoch_milliseconds(execution["timestamp"], "an execution timestamp"),
                quantity=_quantity(execution["quantity"], f"execution {uid} quantity"),
                order_type=order_type,
                direction=direction,
            )
        )
    return tuple(executions), _element_identities(data), token


@dataclass(frozen=True)
class ExecutionDay:
    day: date
    executions: tuple[Execution, ...]
    pages_sha256: tuple[str, ...]
    retrieved_at: datetime
    out_of_order_steps: int  # executions listed before an earlier one (owner Part B ruling 12)
    duplicate_copies: int  # identical copies of an execution listed earlier, dropped (owner Part B ruling 13)


def read_execution_day(fetcher: Fetcher, day: date) -> ExecutionDay:
    """The whole day ``[D 00:00, D+1 00:00)`` through one unbroken continuation chain.

    The log is kept in the provider's order. An execution listed with an
    earlier timestamp than the one before it is counted, not refused (owner
    Part B ruling 12): the live log lists some days slightly out of time order,
    and the hour records do not depend on the order. An execution listed again
    as an identical copy of its first listing is dropped and counted (owner
    Part B ruling 13): it is not part of the log, so it is no step back. The
    chain itself must still end, never repeat a token, never list a uid again
    with any difference, and stay inside the day.
    """

    since, before = midnight(day), midnight(day) + _DAY
    require_request_span(since, before, f"executions {day.isoformat()}")
    executions: list[Execution] = []
    digests: list[str] = []
    seen: dict[str, str] = {}  # uid -> its first listing's identity
    tokens: set[str] = set()
    token: str | None = None
    retrieved_at = since
    out_of_order = copies = 0
    for _ in range(MAX_PAGES_PER_DAY):
        page = fetcher.fetch(executions_url(since, before, token))
        digests.append(page.sha256)
        retrieved_at = page.retrieved_at
        elements, identities, token = _execution_page(page.body)
        for execution, identity in zip(elements, identities, strict=True):
            require_observation_in_window(execution.timestamp, f"execution {execution.uid}")
            if not since <= execution.timestamp < before:
                raise BackfillRefused(
                    "CONTINUATION_CHAIN_REFUSED",
                    f"execution {execution.uid} at {iso(execution.timestamp)} is outside the requested day {day.isoformat()}",
                )
            first = seen.get(execution.uid)
            if first is not None:
                if identity != first:
                    raise BackfillRefused("DUPLICATE_PROVIDER_RECORD", f"execution {execution.uid} appears twice")
                copies += 1
                continue
            if executions and execution.timestamp < executions[-1].timestamp:
                out_of_order += 1
            seen[execution.uid] = identity
            executions.append(execution)
        if token is None:
            return ExecutionDay(day, tuple(executions), tuple(digests), retrieved_at, out_of_order, copies)
        if token in tokens:
            raise BackfillRefused("CONTINUATION_CHAIN_REFUSED", f"{day.isoformat()}: a continuation token repeats")
        tokens.add(token)
    raise BackfillRefused("CONTINUATION_CHAIN_REFUSED", f"{day.isoformat()}: more than {MAX_PAGES_PER_DAY} pages")


# --- the hourly liquidation-volume series (UNVERIFIED shape, owner ruling 5) -----------------


def liquidation_volume_url(since: datetime, to: datetime) -> str:
    # ``to`` is the last hour start asked for, so the request covers [since, to + 1h) (review F7)
    require_request_span(since, to + _HOUR, "a liquidation-volume request")
    query = {"interval": 3600, "since": int(since.timestamp()), "to": int(to.timestamp())}
    return f"{LIQUIDATION_VOLUME_URL}?{urlencode(query)}"


def parse_liquidation_volume(data: bytes, *, since: datetime, to: datetime) -> dict[datetime, Decimal]:
    """``{"result": {"timestamp": [...], "data": [...], "more": false}, "errors": []}``.

    Timestamps are whole hours in epoch seconds inside ``[since, to]``; values
    are JSON strings holding a non-negative decimal numeral, kept with their
    published digits. A JSON number is refused: the live series spells every
    value as a string (Part B's first step, owner ruling 5).
    """

    payload = _json(data, "the liquidation-volume series")
    if not isinstance(payload, dict) or set(payload) != {"result", "errors"} or payload["errors"] != []:
        return _refuse_shape("the liquidation-volume series is not {result, errors: []}")
    result = payload["result"]
    if not isinstance(result, dict) or set(result) != {"timestamp", "data", "more"} or result["more"] is not False:
        return _refuse_shape("the series result is not {timestamp, data, more: false}")
    stamps, values = result["timestamp"], result["data"]
    if not isinstance(stamps, list) or not isinstance(values, list) or len(stamps) != len(values):
        return _refuse_shape("the series timestamps and values do not pair up")
    series: dict[datetime, Decimal] = {}
    for stamp, value in zip(stamps, values):
        if type(stamp) is not int or len(str(stamp)) != 10:
            return _refuse_shape(f"series timestamp {stamp!r} is not an epoch second")
        if not isinstance(value, str) or not _SERIES_NUMERAL.fullmatch(value):
            return _refuse_shape(f"series value {value!r} is not a string holding a decimal numeral")
        hour = require_observation_in_window(datetime.fromtimestamp(stamp, tz=UTC), "a series point")
        number = _numeral_value(value)
        if (hour.minute, hour.second) != (0, 0) or not since <= hour <= to:
            return _refuse_shape(f"series point {iso(hour)} is not an hour inside [{iso(since)}, {iso(to)}]")
        if number is None:
            return _refuse_shape(f"series value {value!r} at {iso(hour)} has an exponent no decimal can hold")
        if not number.is_finite() or number < 0:
            return _refuse_shape(f"series value {value!r} at {iso(hour)} must be non-negative")
        if hour in series:
            return _refuse_shape(f"series point {iso(hour)} appears twice")
        series[hour] = number
    return series


@dataclass(frozen=True)
class SeriesDay:
    values: Mapping[datetime, Decimal]
    sha256: str
    retrieved_at: datetime


def read_series_day(fetcher: Fetcher, day: date) -> SeriesDay:
    """The day's hourly points; ``to`` is the last hour start, so nothing past the day is asked for."""

    since = midnight(day)
    to = since + timedelta(hours=23)
    require_request_span(since, to + _HOUR, f"liquidation volume {day.isoformat()}")
    page = fetcher.fetch(liquidation_volume_url(since, to))
    return SeriesDay(parse_liquidation_volume(page.body, since=since, to=to), page.sha256, page.retrieved_at)


def corroborates(total: Decimal, published: Decimal) -> bool:
    """Owner ruling 3: equal once ``total`` is rounded half-even to ``published``'s decimal places.

    The rounding never runs out of digits, however many places the published
    value has (re-review R12-2). When its last place is at or below the
    total's lowest non-zero digit nothing rounds, and the exact values are
    compared. Otherwise the rounded total has at most one digit more than the
    total has above that place: the precision is computed from the two
    values, with ``decimal``'s widest exponent limits, never a fixed context.
    """

    exponent = published.as_tuple().exponent
    if not isinstance(exponent, int):
        return False
    if total.is_zero() or exponent <= _lowest_digit(total):
        return total == published
    context = Context(
        prec=max(total.adjusted() - exponent + 2, 1),
        rounding=ROUND_HALF_EVEN,
        Emax=MAX_EMAX,
        Emin=MIN_EMIN,
        traps=[InvalidOperation, Overflow],
    )
    return total.quantize(Decimal((0, (1,), exponent)), context=context) == published


# --- hours, rows and evidence -----------------------------------------------------------------


def _side(execution: Execution) -> str:
    taker = TAKER_DIRECTIONS.get(execution.direction)
    side = epic_x.LIQUIDATION_SIDE_TO_POSITION.get(taker) if taker else None
    if side is None:
        raise BackfillRefused(
            "LIQUIDATION_SIDE_UNKNOWN",
            f"liquidation {execution.uid} has taker direction {execution.direction!r}; an unknown side refuses its day",
        )
    return side


def _numeral_value(value: str) -> Decimal | None:
    """A numeral's exact value, or ``None`` when ``decimal`` cannot read it (re-review R12-4, R12-9).

    ``None`` for an exponent past what ``decimal`` holds, or for text that is
    no numeral at all. The conversion is exact at any precision; the context
    only makes such text signal the same way whatever the caller's traps.
    """

    try:
        with localcontext(_EXACT_CONTEXT):
            return Decimal(value)
    except InvalidOperation:
        return None


def _overlaps(hour: datetime, incidents: Sequence[tuple[datetime, datetime]]) -> bool:
    return any(start < hour + _HOUR and hour < end for start, end in incidents)


def _lowest_digit(value: Decimal) -> int:
    """The place of a positive decimal's lowest non-zero digit (``Decimal("1.50")`` gives -1)."""

    _, digits, exponent = value.as_tuple()
    return exponent + len(digits) - len("".join(map(str, digits)).rstrip("0"))


def fits_raw_numeric(value: Decimal) -> bool:
    """A non-negative decimal the liquidation table's ``NUMERIC(38,18)`` holds as it is (re-review R12-3).

    Exact comparisons only, no arithmetic, so no caller context and no
    spelling length matters; a value that fits is spelled in at most 39
    characters.
    """

    return value.is_zero() or (value < RAW_NUMERIC_LIMIT and _lowest_digit(value) >= -RAW_NUMERIC_PLACES)


def exact_sum(values: Sequence[Decimal]) -> Decimal | None:
    """The exact sum of positive decimals, the same in any order (re-review R12-1).

    Adding one value at a time in the 80-digit exact context let a partial
    sum need more digits than the total, so the same values were accepted
    in one order and refused in another. Here nothing rounds: every partial
    sum is a multiple of the lowest non-zero digit among the values and, the
    values being positive, at most their total, which is below ten to the
    power of the largest value's leading place plus the digits of their
    count. That span, taken from the values and never from their order, is
    the precision, with no exponent limit. A span above
    ``EXACT_SUM_MAX_DIGITS`` gives ``None`` instead of using that much
    memory. The caller applies the 80-digit exact context to the sum once.
    """

    if not values:
        return Decimal(0)
    lowest = min(_lowest_digit(value) for value in values)
    highest = max(value.adjusted() for value in values) + len(str(len(values)))
    digits = highest - lowest + 1
    if digits > EXACT_SUM_MAX_DIGITS:
        return None
    context = Context(prec=digits, rounding=ROUND_HALF_EVEN, Emax=MAX_EMAX, Emin=MIN_EMIN, traps=[Inexact, InvalidOperation, Overflow])
    total = Decimal(0)
    with localcontext(context):
        for value in values:
            total += value
    return total


def hour_record(
    hour: datetime,
    executions: Sequence[Execution],
    *,
    incident: bool,
    series_value: Decimal | None,
    pages_sha256: Sequence[str],
    series_sha256: str | None,
) -> dict[str, Any]:
    """The evidence record of one hour; its canonical digest is the hour's ``evidence_sha256``."""

    in_hour = [execution for execution in executions if hour <= execution.timestamp < hour + _HOUR]
    liquidations = [execution for execution in in_hour if execution.order_type == LIQUIDATION_ORDER_TYPE]
    # every side is known before any sum, each side summed exactly, then held to 80 digits once (re-review R12-1)
    by_side: dict[str, list[Decimal]] = {"long": [], "short": []}
    for execution in sorted(liquidations, key=lambda item: item.uid):
        by_side[_side(execution)].append(execution.quantity)
    quantities: dict[str, Decimal] = {}
    try:
        for side, values in by_side.items():
            value = exact_sum(values)
            if value is None:
                return _refuse_shape(
                    f"hour {iso(hour)}: the {side} liquidation quantities need more than {EXACT_SUM_MAX_DIGITS} digits to sum exactly"
                )
            quantities[side] = _EXACT_CONTEXT.plus(value)
        with localcontext(_EXACT_CONTEXT):
            notionals = {side: quantity * CONTRACT_SIZE_USD for side, quantity in quantities.items()}
            total = (quantities["long"] + quantities["short"]) * CONTRACT_SIZE_USD
    except Inexact:
        return _refuse_shape(f"hour {iso(hour)}: the liquidation quantities do not sum exactly")
    # what the hour stores and persists fits the table, so its spelling always reads back (re-review R12-3)
    for side, quantity in quantities.items():
        if not (fits_raw_numeric(quantity) and fits_raw_numeric(notionals[side])):
            return _refuse_shape(
                f"hour {iso(hour)}: the {side} liquidation quantity or its notional does not fit the liquidation table's"
                f" NUMERIC(38,18) (below 10^20, at most {RAW_NUMERIC_PLACES} places)"
            )
    if incident or not in_hour:
        status, corroboration = epic_x.FEED_STATUS_SOURCE_UNAVAILABLE, v2.CORROBORATION_NOT_APPLICABLE
    else:
        status = epic_x.FEED_STATUS_OBSERVED_WITH_EVENTS if liquidations else epic_x.FEED_STATUS_OBSERVED_ZERO_EVENTS
        if series_value is None:
            corroboration = v2.CORROBORATION_SERIES_UNAVAILABLE
        else:
            corroboration = v2.CORROBORATION_AGREES if corroborates(total, series_value) else v2.CORROBORATION_DISAGREES
    return {
        "hour_start": iso(hour),
        "feed_status": status,
        "corroboration": corroboration,
        "execution_count": len(in_hour),
        "liquidation_uids": sorted(execution.uid for execution in liquidations),
        "long_quantity": v1.canonical_decimal(quantities["long"]),
        "short_quantity": v1.canonical_decimal(quantities["short"]),
        "series_value": None if series_value is None else published_spelling(series_value),
        "incident": incident,
        "pages_sha256": list(pages_sha256),
        "series_sha256": series_sha256,
    }


def published_spelling(value: Decimal) -> str:
    """The published value exactly, exponent kept, so ruling 3's precision survives the file.

    The spelling never depends on the caller's decimal context, so the same
    responses always give the same evidence bytes and the parser reads them
    back under any context.
    """

    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        return _refuse_shape(f"series value {value!r} is not a finite non-negative decimal")
    return _SPELLING_CONTEXT.to_sci_string(value)


def hour_evidence(record: Mapping[str, Any]) -> v2.LiquidationHourEvidence:
    return v2.LiquidationHourEvidence(
        hour_start=datetime.fromisoformat(record["hour_start"]),
        feed_status=record["feed_status"],
        corroboration=record["corroboration"],
        evidence_sha256=sha256_hex(canonical_json_bytes(dict(record))),
    )


def liquidation_rows(record: Mapping[str, Any], *, retrieved_at: datetime) -> tuple[Liquidation, ...]:
    """One per-side ``1h`` aggregate for each side with liquidations in an observed hour."""

    if record["feed_status"] != epic_x.FEED_STATUS_OBSERVED_WITH_EVENTS:
        return ()
    hour = datetime.fromisoformat(record["hour_start"])
    rows = []
    for side in v2.LIQUIDATION_SIDES:
        quantity = Decimal(record[f"{side}_quantity"])
        if quantity > 0:
            try:
                with localcontext(_EXACT_CONTEXT):
                    notional = quantity * CONTRACT_SIZE_USD
            except Inexact:
                return _refuse_shape(f"hour {record['hour_start']}: the {side} notional is not exact")
            rows.append(
                Liquidation(
                    observation_time=hour,
                    exchange=KRAKEN_EXCHANGE,
                    symbol=KRAKEN_SYMBOL,
                    timeframe=KRAKEN_TIMEFRAME,
                    side=side,
                    quantity=quantity,
                    quantity_unit=QUANTITY_UNIT,
                    notional_usd=notional,
                    provider=KRAKEN_PROVIDER,
                    source=EXECUTIONS_URL,
                    available_at=retrieved_at,
                    ingested_at=retrieved_at,
                )
            )
    return tuple(rows)


def liquidation_hour_evidence_bytes(
    *,
    retrieved_at: datetime,
    incidents: Sequence[tuple[datetime, datetime]],
    hours: Sequence[Mapping[str, Any]],
) -> bytes:
    """The canonical bytes of a ``HISTORICAL_LIQUIDATION_HOUR_EVIDENCE_V1`` file."""

    return canonical_json_bytes(
        {
            "evidence_version": HOUR_EVIDENCE_VERSION,
            "rule": v2.LIQUIDATION_COMPLETENESS_VERSION,
            "corroboration_rule": CORROBORATION_RULE,
            "exchange": KRAKEN_EXCHANGE,
            "symbol": KRAKEN_SYMBOL,
            "liquidation_order_type": LIQUIDATION_ORDER_TYPE,
            "contract_size_usd": v1.canonical_decimal(CONTRACT_SIZE_USD),
            "source": f"{EXECUTIONS_URL} ; {LIQUIDATION_VOLUME_URL}",
            "licence": KRAKEN_LICENCE,
            "retrieved_at": iso(retrieved_at),
            "incidents": [{"start": iso(start), "end": iso(end)} for start, end in incidents],
            "hours": [dict(record) for record in hours],
        }
    )


def parse_liquidation_hour_evidence(data: bytes, *, expected_sha256: str) -> tuple[v2.LiquidationHourEvidence, ...]:
    """Verify an hour evidence file and give the builder's typed records.

    The file must be the canonical bytes its digest names, declare this rule
    and universe, and list strictly increasing whole hours, each exactly the
    recorded keys; every hour's ``evidence_sha256`` is recomputed from its record.
    """

    if not isinstance(data, bytes) or sha256_hex(data) != expected_sha256:
        return _refuse_shape("the hour evidence does not match its bound SHA-256")
    payload = _json(data, "the hour evidence")
    if not isinstance(payload, dict) or not _is_canonical(payload, data) or set(payload) != _HOUR_EVIDENCE_KEYS:
        return _refuse_shape("the hour evidence is not the canonical file with exactly its keys")
    declared = {key: payload[key] for key in _HOUR_EVIDENCE_KEYS - {"retrieved_at", "incidents", "hours"}}
    if declared != _declared_constants():
        return _refuse_shape(f"the hour evidence declares {declared}")
    _instant(payload["retrieved_at"], "retrieved_at")
    incidents = _incidents(payload["incidents"])
    if not isinstance(payload["hours"], list):
        return _refuse_shape("hours must be a list")
    typed: list[v2.LiquidationHourEvidence] = []
    for record in payload["hours"]:
        if not isinstance(record, dict) or set(record) != _HOUR_RECORD_KEYS:
            return _refuse_shape(f"each hour is exactly {sorted(_HOUR_RECORD_KEYS)}")
        hour = _instant(record["hour_start"], "hour_start")
        if (hour.minute, hour.second, hour.microsecond) != (0, 0, 0):
            return _refuse_shape(f"hour {record['hour_start']!r} is not a canonical UTC hour start")
        require_observation_in_window(hour, "an evidence hour")
        if typed and hour <= typed[-1].hour_start:
            return _refuse_shape(f"hour {record['hour_start']}: hours must be strictly increasing")
        _check_hour(record, hour, incidents)
        typed.append(hour_evidence(record))
    return tuple(typed)


def _is_canonical(payload: Any, data: bytes) -> bool:
    """Whether ``data`` is the canonical encoding of what it decodes to (re-review R12-7).

    A JSON fraction decodes as a ``Decimal``, and ``NaN`` or an infinity as a
    float, none of which the canonical writer writes; such a body, or one
    nested too deeply for the writer, is not the canonical file.
    """

    try:
        return canonical_json_bytes(payload) == data
    except (TypeError, ValueError, RecursionError):
        return False


def _declared_constants() -> dict[str, Any]:
    return {
        "evidence_version": HOUR_EVIDENCE_VERSION,
        "rule": v2.LIQUIDATION_COMPLETENESS_VERSION,
        "corroboration_rule": CORROBORATION_RULE,
        "exchange": KRAKEN_EXCHANGE,
        "symbol": KRAKEN_SYMBOL,
        "liquidation_order_type": LIQUIDATION_ORDER_TYPE,
        "contract_size_usd": v1.canonical_decimal(CONTRACT_SIZE_USD),
        "source": f"{EXECUTIONS_URL} ; {LIQUIDATION_VOLUME_URL}",
        "licence": KRAKEN_LICENCE,
    }


def _instant(text: Any, what: str) -> datetime:
    try:
        instant = datetime.fromisoformat(text) if isinstance(text, str) else None
    except ValueError:
        instant = None
    if instant is None or instant.tzinfo is None or instant.utcoffset() != timedelta(0) or iso(instant) != text:
        return _refuse_shape(f"{what} {text!r} is not a canonical UTC instant")
    return instant.astimezone(UTC)


def _incidents(items: Any) -> tuple[tuple[datetime, datetime], ...]:
    if not isinstance(items, list):
        return _refuse_shape("incidents must be a list")
    incidents = []
    for item in items:
        if not isinstance(item, dict) or set(item) != {"start", "end"}:
            return _refuse_shape("each incident is exactly {start, end}")
        start, end = _instant(item["start"], "an incident start"), _instant(item["end"], "an incident end")
        if end <= start:
            return _refuse_shape("an incident must end after it starts")
        incidents.append((start, end))
    return tuple(incidents)


def _stored_quantity(text: Any, what: str) -> Decimal:
    try:
        value = Decimal(text) if isinstance(text, str) else None
    except InvalidOperation:
        value = None
    if value is None or not value.is_finite() or value < 0:
        return _refuse_shape(f"{what} {text!r} is not a canonical non-negative decimal")
    # before the spelling check: a numeral too long for ``int`` would raise there (re-review R12-3)
    if not fits_raw_numeric(value):
        return _refuse_shape(f"{what} does not fit the liquidation table's NUMERIC(38,18)")
    # a longer spelling of a value that fits is not canonical, refused before ``canonical_decimal`` converts its
    # digits with ``int``, which raises past 4,300 of them (re-review R12-6)
    if len(text) > RAW_NUMERIC_SPELLING_MAX or v1.canonical_decimal(value) != text:
        return _refuse_shape(f"{what} {text!r} is not a canonical non-negative decimal")
    return value


def _check_hour(record: Mapping[str, Any], hour: datetime, incidents: Sequence[tuple[datetime, datetime]]) -> None:
    """Re-derive the hour's status and corroboration from what the record stores (review F6)."""

    what = f"hour {record['hour_start']}"
    count, uids, incident = record["execution_count"], record["liquidation_uids"], record["incident"]
    if type(count) is not int or count < 0:
        return _refuse_shape(f"{what}: execution_count must be a non-negative integer")
    if not isinstance(uids, list) or not all(isinstance(uid, str) and uid for uid in uids) or uids != sorted(set(uids)):
        return _refuse_shape(f"{what}: liquidation_uids must be sorted unique identifiers")
    if len(uids) > count:
        return _refuse_shape(f"{what}: more liquidations than executions")
    if type(incident) is not bool or incident != _overlaps(hour, incidents):
        return _refuse_shape(f"{what}: the incident flag does not match the declared incidents")
    pages, series_digest = record["pages_sha256"], record["series_sha256"]
    if not isinstance(pages, list) or not pages or not all(isinstance(item, str) and _SHA256.fullmatch(item) for item in pages):
        return _refuse_shape(f"{what}: pages_sha256 must list the execution pages' digests")
    if series_digest is not None and not (isinstance(series_digest, str) and _SHA256.fullmatch(series_digest)):
        return _refuse_shape(f"{what}: series_sha256 is not a digest")
    long, short = _stored_quantity(record["long_quantity"], f"{what} long_quantity"), _stored_quantity(
        record["short_quantity"], f"{what} short_quantity"
    )
    # no arithmetic here: a sum in the caller's decimal context could round or trap (re-review N1)
    no_quantity = long.is_zero() and short.is_zero()
    if not uids and not no_quantity:
        return _refuse_shape(f"{what}: quantities without liquidations")
    if uids and no_quantity:
        return _refuse_shape(f"{what}: liquidations without a quantity")
    published = record["series_value"]
    if published is not None:
        # read in the exact context, so the same text refuses the same way whatever the caller's traps (re-review R12-9)
        series_value = _numeral_value(published) if isinstance(published, str) else None
        if series_value is None or published_spelling(series_value) != published or series_digest is None:
            return _refuse_shape(f"{what}: series_value {published!r} is not a published decimal with its response digest")
    if incident or count == 0:
        expected = (epic_x.FEED_STATUS_SOURCE_UNAVAILABLE, v2.CORROBORATION_NOT_APPLICABLE)
    else:
        status = epic_x.FEED_STATUS_OBSERVED_WITH_EVENTS if uids else epic_x.FEED_STATUS_OBSERVED_ZERO_EVENTS
        if published is None:
            expected = (status, v2.CORROBORATION_SERIES_UNAVAILABLE)
        else:
            try:
                with localcontext(_EXACT_CONTEXT):
                    total = (long + short) * CONTRACT_SIZE_USD
            except Inexact:
                return _refuse_shape(f"{what}: the stored quantities do not sum exactly")
            agrees = corroborates(total, series_value)
            expected = (status, v2.CORROBORATION_AGREES if agrees else v2.CORROBORATION_DISAGREES)
    if (record["feed_status"], record["corroboration"]) != expected:
        return _refuse_shape(f"{what}: {record['feed_status']}/{record['corroboration']} is not the derived {expected[0]}/{expected[1]}")
    return None


@dataclass(frozen=True)
class KrakenLiquidationCollection:
    rows: tuple[Liquidation, ...]
    hours: tuple[v2.LiquidationHourEvidence, ...]
    evidence_bytes: bytes
    out_of_order_steps: int  # over every day read (owner Part B ruling 12)
    duplicate_copies: int  # over every day read (owner Part B ruling 13)

    @property
    def evidence_sha256(self) -> str:
        return sha256_hex(self.evidence_bytes)


def read_liquidations(
    fetcher: Fetcher,
    first_day: date,
    last_day: date,
    *,
    incidents: Sequence[tuple[datetime, datetime]],
) -> KrakenLiquidationCollection:
    """Every hour of ``first_day`` .. ``last_day``: rows, typed hour records and the evidence file."""

    incidents = tuple((require_utc(start, "incident start"), require_utc(end, "incident end")) for start, end in incidents)
    if any(end <= start for start, end in incidents):
        raise BackfillRefused("RESPONSE_SHAPE_REFUSED", "an incident must end after it starts")
    records: list[dict[str, Any]] = []
    rows: list[Liquidation] = []
    retrieved: list[datetime] = []
    out_of_order = copies = 0
    for day in data_window_days(first_day, last_day):
        log = read_execution_day(fetcher, day)
        series = read_series_day(fetcher, day)
        retrieved += [log.retrieved_at, series.retrieved_at]
        out_of_order += log.out_of_order_steps
        copies += log.duplicate_copies
        for hour in hours_of(day):
            record = hour_record(
                hour,
                log.executions,
                incident=_overlaps(hour, incidents),
                series_value=series.values.get(hour),
                pages_sha256=log.pages_sha256,
                series_sha256=series.sha256,
            )
            records.append(record)
            rows.extend(liquidation_rows(record, retrieved_at=log.retrieved_at))
    evidence = liquidation_hour_evidence_bytes(retrieved_at=max(retrieved), incidents=incidents, hours=records)
    # the typed hours are read back through the file's own parser, so writer and parser cannot drift
    hours = parse_liquidation_hour_evidence(evidence, expected_sha256=sha256_hex(evidence))
    return KrakenLiquidationCollection(tuple(rows), hours, evidence, out_of_order, copies)
