"""A value-blind projection of an unbounded response to the requested days (RBT-003 Part B).

Owner Part B ruling 10 (2026-11-05): neither CoinGlass ETF endpoint takes a
date bound (``flow-history`` documents no parameter, ``history`` only
``ticker``), so every response holds the provider's whole history: the
prohibited window before 2020 (a fund such as GBTC predates it), the holdout
and the reserve. Such a response is read only through this projection, which
the RBT-002 disclosure ruling allows ("a reviewed transport projection that
rejects/truncates out-of-window records before value
parsing/logging/persistence").

The projection walks the JSON bytes with a tokenizer that checks the grammar
but converts no number and decodes no string value. For each record of the
envelope's ``data`` array it reads only the record's member names and its date
members (13-digit epoch milliseconds), then keeps the record's exact bytes when
every date lies inside the requested days and drops them otherwise. A dropped
record's other members are skipped as byte spans, never decoded, so no
out-of-window value is parsed, logged or kept. The projected response is the
envelope's ``code`` and, when present, its ``msg`` (the live responses omit
it, owner Part B ruling 14) with the kept records' bytes in their order;
only it reaches the strict parsers and the evidence file, and a parser first
proves, with :func:`verified_body`, that the bytes it is given are exactly a
projection on the endpoint's own date members (review B2). The full response
leaves a digest and a size (the retrieval log's), and each projection records
how many records it dropped from the prohibited window, from in-window days
not requested, and from the holdout and reserve: the metadata exposure the
ruling records. Any malformed byte refuses the whole response, a string's
bytes included: each must be a well-formed UTF-8 sequence, checked byte by byte
and never decoded (review B7).
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from btc_predictor.research_backtest.backfill_sources import (
    DATA_WINDOW_START,
    LAST_DATA_DAY,
    BackfillRefused,
    Fetched,
    iso,
    sha256_hex,
)


PROJECTION_RULE = "IN_WINDOW_RECORD_PROJECTION_V1"
ENVELOPE_KEYS = ("code", "msg", "data")
REQUIRED_ENVELOPE_KEYS = ("code", "data")  # msg may be absent: the live responses omit it (owner Part B ruling 14)
MAX_DEPTH = 32

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_WHITESPACE = frozenset(b" \t\n\r")
_NUMBER = re.compile(rb"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")
_MEMBER_NAME = re.compile(rb'"[A-Za-z_][A-Za-z0-9_]*"')
_EPOCH_MILLISECONDS = re.compile(rb"[0-9]{13}")
_ESCAPED = frozenset(b'"\\/bfnrt')
_HEX = frozenset(b"0123456789abcdefABCDEF")
_LITERALS = (b"true", b"false", b"null")


@dataclass(frozen=True)
class ProjectedResponse:
    """The in-window records of one unbounded response, and what was dropped.

    ``body`` is the projected response; ``response_sha256`` and
    ``response_size`` describe the full response, which is not kept.
    """

    url: str
    retrieved_at: datetime
    first_day: date
    last_day: date
    date_keys: tuple[str, ...]
    response_sha256: str
    response_size: int
    body: bytes
    kept: int
    dropped_prohibited: int
    dropped_unrequested: int
    dropped_holdout: int

    @property
    def sha256(self) -> str:
        return sha256_hex(self.body)

    @property
    def dropped(self) -> int:
        return self.dropped_prohibited + self.dropped_unrequested + self.dropped_holdout

    def exposure_record(self) -> dict[str, Any]:
        """The metadata exposure ruling 10 records: digests, sizes, days and counts, never a value."""

        return {
            "rule": PROJECTION_RULE,
            "url": self.url,
            "retrieved_at": iso(self.retrieved_at),
            "first_day": self.first_day.isoformat(),
            "last_day": self.last_day.isoformat(),
            "date_keys": list(self.date_keys),
            "response_sha256": self.response_sha256,
            "response_size": self.response_size,
            "projected_sha256": self.sha256,
            "projected_size": len(self.body),
            "kept": self.kept,
            "dropped_prohibited": self.dropped_prohibited,
            "dropped_unrequested": self.dropped_unrequested,
            "dropped_holdout": self.dropped_holdout,
        }


class _Reader:
    """A JSON grammar check over bytes that keeps spans and converts no value."""

    def __init__(self, data: bytes, what: str) -> None:
        self.data = data
        self.size = len(data)
        self.what = what

    def refuse(self, message: str) -> Any:
        # a message names a position or a member, never response content
        raise BackfillRefused("RESPONSE_SHAPE_REFUSED", f"{self.what}: {message}")

    def space(self, i: int) -> int:
        while i < self.size and self.data[i] in _WHITESPACE:
            i += 1
        return i

    def string_end(self, i: int) -> int:
        """The index after the string opening at ``i``; escapes, control bytes and UTF-8 are checked."""

        data, size = self.data, self.size
        i += 1
        while i < size:
            byte = data[i]
            if byte == 0x22:  # "
                return i + 1
            if byte == 0x5C:  # backslash
                if i + 1 >= size:
                    break
                escaped = data[i + 1]
                if escaped == 0x75:  # u
                    if i + 6 > size or not all(item in _HEX for item in data[i + 2 : i + 6]):
                        self.refuse(f"a string at byte {i} has an invalid unicode escape")
                    i += 6
                    continue
                if escaped not in _ESCAPED:
                    self.refuse(f"a string at byte {i} has an invalid escape")
                i += 2
                continue
            if byte < 0x20:
                self.refuse(f"a string at byte {i} holds a control byte")
            i = self.utf8_end(i) if byte >= 0x80 else i + 1
        return self.refuse("a string is not terminated")

    def utf8_end(self, i: int) -> int:
        """The index after the multi-byte UTF-8 sequence at ``i``: its bytes are checked, never decoded (review B7).

        RFC 3629's table: no overlong form, no surrogate, nothing above U+10FFFF.
        """

        data, lead = self.data, self.data[i]
        if 0xC2 <= lead <= 0xDF:
            length, low, high = 2, 0x80, 0xBF
        elif lead == 0xE0:
            length, low, high = 3, 0xA0, 0xBF
        elif 0xE1 <= lead <= 0xEC or 0xEE <= lead <= 0xEF:
            length, low, high = 3, 0x80, 0xBF
        elif lead == 0xED:
            length, low, high = 3, 0x80, 0x9F
        elif lead == 0xF0:
            length, low, high = 4, 0x90, 0xBF
        elif 0xF1 <= lead <= 0xF3:
            length, low, high = 4, 0x80, 0xBF
        elif lead == 0xF4:
            length, low, high = 4, 0x80, 0x8F
        else:
            return self.refuse(f"a string at byte {i} holds a byte that cannot start a UTF-8 sequence")
        if i + length > self.size or not low <= data[i + 1] <= high or not all(0x80 <= item <= 0xBF for item in data[i + 2 : i + length]):
            self.refuse(f"a string at byte {i} holds a malformed UTF-8 sequence")
        return i + length

    def value_end(self, i: int, depth: int) -> int:
        if depth > MAX_DEPTH:
            self.refuse(f"nesting deeper than {MAX_DEPTH} at byte {i}")
        if i >= self.size:
            self.refuse("the response ends where a value should start")
        byte = self.data[i]
        if byte == 0x22:
            return self.string_end(i)
        if byte == 0x7B:  # {
            return self.members(i, depth)[1]
        if byte == 0x5B:  # [
            return self.elements(i, depth)[1]
        for literal in _LITERALS:
            if self.data.startswith(literal, i):
                return i + len(literal)
        match = _NUMBER.match(self.data, i)
        if match is None:
            self.refuse(f"an unexpected byte at {i}")
        return match.end()

    def members(self, i: int, depth: int) -> tuple[list[tuple[str, int, int]], int]:
        """The object opening at ``i``: each member's name and value span, and the index after it."""

        members: list[tuple[str, int, int]] = []
        i = self.space(i + 1)
        if i < self.size and self.data[i] == 0x7D:  # }
            return members, i + 1
        while True:
            match = _MEMBER_NAME.match(self.data, i)
            if match is None:
                self.refuse(f"a member name at byte {i} is not a plain identifier string")
            name = match.group()[1:-1].decode("ascii")
            i = self.space(match.end())
            if i >= self.size or self.data[i] != 0x3A:  # :
                self.refuse(f"member {name!r} has no colon")
            start = self.space(i + 1)
            end = self.value_end(start, depth + 1)
            members.append((name, start, end))
            i = self.space(end)
            if i < self.size and self.data[i] == 0x2C:  # ,
                i = self.space(i + 1)
                continue
            if i < self.size and self.data[i] == 0x7D:
                return members, i + 1
            self.refuse(f"an object is not closed after member {name!r}")

    def elements(self, i: int, depth: int) -> tuple[list[tuple[int, int]], int]:
        """The array opening at ``i``: each element's span, and the index after it."""

        spans: list[tuple[int, int]] = []
        i = self.space(i + 1)
        if i < self.size and self.data[i] == 0x5D:  # ]
            return spans, i + 1
        while True:
            end = self.value_end(i, depth + 1)
            spans.append((i, end))
            i = self.space(end)
            if i < self.size and self.data[i] == 0x2C:
                i = self.space(i + 1)
                continue
            if i < self.size and self.data[i] == 0x5D:
                return spans, i + 1
            self.refuse(f"an array is not closed at byte {i}")

    def status_string(self, span: tuple[int, int], name: str) -> str:
        start, end = span
        if self.data[start] != 0x22:
            self.refuse(f"the envelope's {name} is not a string")
        try:
            text = json.loads(self.data[start:end])
        except (UnicodeDecodeError, ValueError):
            text = None
        if not isinstance(text, str):
            self.refuse(f"the envelope's {name} is not a JSON string")
        return text


def _day_of(epoch_milliseconds: bytes) -> date:
    return (_EPOCH + timedelta(milliseconds=int(epoch_milliseconds))).date()


def project_records(
    fetched: Fetched,
    *,
    date_keys: Sequence[str],
    first_day: date,
    last_day: date,
    what: str,
) -> ProjectedResponse:
    """Keep the ``data`` records whose every date member lies in ``[first_day, last_day]``.

    ``first_day`` .. ``last_day`` must lie inside the data window. A record is
    counted as prohibited when a date precedes the window, as holdout when one
    follows it, and as unrequested when its dates are in the window but not all
    in the requested days. The envelope must be exactly ``code``, ``msg`` and
    ``data``, or ``code`` and ``data`` (owner Part B ruling 14), ``code`` must
    be ``"0"``, and every record an object naming each date member once, as a
    13-digit epoch-millisecond integer. Another ``code`` refuses naming it and
    the ``msg``, if any, before ``data`` is required.
    """

    if not isinstance(fetched, Fetched) or not isinstance(fetched.body, bytes):
        raise BackfillRefused("PROVIDER_RESPONSE_REFUSED", f"{what}: no fetched response to project")
    if not DATA_WINDOW_START.date() <= first_day <= last_day <= LAST_DATA_DAY:
        raise BackfillRefused("REQUEST_OUTSIDE_DATA_WINDOW", f"{what}: days {first_day}..{last_day} are not inside the data window")
    keys = tuple(date_keys)
    if not keys or len(set(keys)) != len(keys):
        raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"{what}: name each date member once")

    reader = _Reader(fetched.body, what)
    start = reader.space(0)
    if start >= reader.size or fetched.body[start] != 0x7B:
        reader.refuse("the response is not a JSON object")
    envelope, end = reader.members(start, 0)
    if reader.space(end) != reader.size:
        reader.refuse(f"bytes follow the envelope at byte {end}")
    names = [name for name, _, _ in envelope]
    mismatch = f"the envelope's members are {sorted(names)}, not exactly {sorted(ENVELOPE_KEYS)} or {sorted(REQUIRED_ENVELOPE_KEYS)}"
    if len(set(names)) != len(names) or not {"code"} <= set(names) <= set(ENVELOPE_KEYS):
        reader.refuse(mismatch)
    spans = {name: (value_start, value_end) for name, value_start, value_end in envelope}
    code = reader.status_string(spans["code"], "code")
    msg = reader.status_string(spans["msg"], "msg") if "msg" in spans else None  # optional (owner Part B ruling 14)
    if code != "0":
        # the provider's status message, never a record; named before data is required (an error has none)
        reader.refuse(f"the provider reports code {code[:40]!r}" + ("" if msg is None else f": {msg[:200]!r}"))
    if "data" not in spans:
        reader.refuse(mismatch)
    data_start, _ = spans["data"]
    if fetched.body[data_start] != 0x5B:
        reader.refuse("the envelope's data is not an array")
    records, _ = reader.elements(data_start, 1)

    first_window_day = DATA_WINDOW_START.date()
    kept: list[bytes] = []
    prohibited = unrequested = holdout = 0
    for index, (record_start, record_end) in enumerate(records):
        if fetched.body[record_start] != 0x7B:
            reader.refuse(f"record {index} is not an object")
        members, _ = reader.members(record_start, 2)
        record_names = [name for name, _, _ in members]
        if len(set(record_names)) != len(record_names):
            reader.refuse(f"record {index} repeats a member name")
        found = {name: (value_start, value_end) for name, value_start, value_end in members}
        days = []
        for key in keys:
            if key not in found:
                reader.refuse(f"record {index} has no {key}")
            value_start, value_end = found[key]
            if not _EPOCH_MILLISECONDS.fullmatch(fetched.body, value_start, value_end):
                reader.refuse(f"record {index}: {key} is not a 13-digit epoch-millisecond integer")
            days.append(_day_of(fetched.body[value_start:value_end]))
        if any(day < first_window_day for day in days):
            prohibited += 1
        elif any(day > LAST_DATA_DAY for day in days):
            holdout += 1
        elif all(first_day <= day <= last_day for day in days):
            kept.append(fetched.body[record_start:record_end])
        else:
            unrequested += 1

    code_start, code_end = spans["code"]
    parts = [b'{"code":', fetched.body[code_start:code_end]]
    if "msg" in spans:  # kept as before; the live responses have none (owner Part B ruling 14)
        msg_start, msg_end = spans["msg"]
        parts += [b',"msg":', fetched.body[msg_start:msg_end]]
    body = b"".join((*parts, b',"data":[', b",".join(kept), b"]}"))
    return ProjectedResponse(
        url=fetched.url,
        retrieved_at=fetched.retrieved_at,
        first_day=first_day,
        last_day=last_day,
        date_keys=keys,
        response_sha256=fetched.sha256,
        response_size=len(fetched.body),
        body=body,
        kept=len(kept),
        dropped_prohibited=prohibited,
        dropped_unrequested=unrequested,
        dropped_holdout=holdout,
    )


def verified_body(projection: Any, *, date_keys: Sequence[str], what: str) -> bytes:
    """The projected bytes, once proven to be a projection on the endpoint's date members (review B2).

    A parser calls this before it decodes anything. The projection must name
    exactly ``date_keys``; its bytes are then projected again, value-blind, on
    those members and its own days, and every record must be kept and the
    result byte-identical. A response projected on fewer date members (a fund
    record whose ``market_date`` is in the holdout, say) or bytes that were
    never projected refuse here, before any value is decoded.
    """

    if not isinstance(projection, ProjectedResponse):
        raise BackfillRefused("PROVIDER_RESPONSE_REFUSED", f"{what} is read only through the in-window projection (owner Part B ruling 10)")
    if tuple(projection.date_keys) != tuple(date_keys):
        raise BackfillRefused(
            "PROVIDER_RESPONSE_REFUSED", f"{what} was projected on {list(projection.date_keys)}, not on the endpoint's {list(date_keys)}"
        )
    if not (
        isinstance(projection.body, bytes)
        and isinstance(projection.retrieved_at, datetime)
        and all(type(day) is date for day in (projection.first_day, projection.last_day))
    ):
        raise BackfillRefused("PROVIDER_RESPONSE_REFUSED", f"{what}: the projection does not name its bytes and days")
    again = project_records(
        Fetched(projection.url, projection.body, projection.retrieved_at),
        date_keys=date_keys, first_day=projection.first_day, last_day=projection.last_day, what=what,
    )
    if again.dropped or again.kept != projection.kept or again.body != projection.body:
        raise BackfillRefused("PROVIDER_RESPONSE_REFUSED", f"{what}: the bytes are not exactly a projection to the requested days")
    return projection.body
