"""RBT-007 shared positioning results (the owner's runtime ruling and ruling 6, 2026-11-18).

The positioning owner rescans the whole history at every instant, and its
inputs are the same on all three venues, so RBT-007 computes each of its
results once and shares it across every run. A shared result is the
unchanged owner function's own return value for exactly the same arguments:

- **Which calls.** Every positioning owner function the entry composer calls
  that rescans the history (:data:`SHARED_FUNCTIONS`): the four public owner
  functions and the four private helpers the composer's zero-variance guards
  call (ruling 6). Nothing else is shared.
- **Exact keys.** A call's key is a SHA-256 digest of the function's name and
  an exact, type-tagged encoding of every argument and keyword argument.
  A tuple of replay rows is encoded as its frozen source (that source's own
  content digest) and the positions of its rows in it, after checking that
  each row is that source's object; a mapping keeps its insertion order;
  ``Decimal`` keeps its exponent. A call whose arguments the encoder cannot
  encode exactly is never served: the owner function is called.
- **The store.** Each result is pickled to its own file, named by its key,
  in the private work directory (Part B ruling 9: the results hold
  market-derived values). A served result is a fresh copy read from those
  bytes, so no caller can change another's result.
- **Scope.** :func:`shared_positioning` replaces those names in the entry
  composer module's namespace for its ``with`` block only, in this process
  only. No file changes: the composer and the owner stay byte-identical to
  the frozen commit (ruling 2).

The look-ahead audit recomputes sampled decisions without the share and
requires byte-identical rows (ruling 3), which checks all of this end to end.
"""

from __future__ import annotations

import hashlib
import json
import os
import pickle
import tempfile
from array import array
from collections import Counter, OrderedDict
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from btc_predictor.features import positioning
from btc_predictor.research_backtest import entry_composer as ec

SHARED_POSITIONING_VERSION = "RBT007_SHARED_POSITIONING_V1"

# The runtime ruling's four public owner functions, then ruling 6's guard helpers.
SHARED_PUBLIC_FUNCTIONS = (
    "funding_health",
    "futures_basis_health",
    "open_interest_growth_health",
    "open_interest_intensity",
)
SHARED_HELPER_FUNCTIONS = (
    "_open_interest_growth_by_time",
    "_funding_averages_by_time",
    "_futures_basis_averages_by_time",
    "_aggregate_open_interest_by_time",
)
SHARED_FUNCTIONS = SHARED_PUBLIC_FUNCTIONS + SHARED_HELPER_FUNCTIONS

_PICKLE_PROTOCOL = 5
_FILE_TAG = SHARED_POSITIONING_VERSION + ":RESULT"


class SharedPositioningError(RuntimeError):
    """The share cannot be trusted: a corrupt file or a misbound name."""


class Unencodable(TypeError):
    """An argument the encoder cannot encode exactly; the call is not shared."""


def _owner_function(name: str) -> Callable[..., Any]:
    """The positioning owner's function, checked to be what the composer imported."""

    owner = getattr(positioning, name)
    imported = getattr(ec, name)
    if imported is not owner:
        raise SharedPositioningError(f"the entry composer's {name} is not the positioning owner's")
    return owner


# --- exact argument keys ------------------------------------------------------------------------


def _row_record_bytes(row: Any) -> bytes:
    """Every field of a frozen replay row, type-tagged, so equal bytes mean equal rows."""

    if not is_dataclass(row) or isinstance(row, type):
        raise SharedPositioningError(f"a replay source holds a {type(row).__name__}, not a row")
    payload = [type(row).__module__ + "." + type(row).__qualname__]
    for item in fields(row):
        payload.append([item.name, _plain(getattr(row, item.name))])
    return json.dumps(payload, separators=(",", ":")).encode()


def _plain(value: Any) -> Any:
    if value is None or value is True or value is False or type(value) in (int, str):
        return [type(value).__name__, value]
    if type(value) is Decimal:
        return ["Decimal", str(value)]
    if type(value) is datetime:
        if value.tzinfo is None:
            raise SharedPositioningError("a replay row holds a naive datetime")
        return ["datetime", value.isoformat(), type(value.tzinfo).__name__]
    if type(value) is date:
        return ["date", value.isoformat()]
    if type(value) in (tuple, list):
        return [type(value).__name__, [_plain(item) for item in value]]
    if is_dataclass(value) and not isinstance(value, type):
        return ["row", json.loads(_row_record_bytes(value))]
    raise SharedPositioningError(f"a replay row holds an unencodable {type(value).__name__}")


@dataclass
class ArgumentEncoder:
    """Exact, deterministic digests of owner-call arguments.

    Replay rows are encoded only through a registered source: the source's
    content digest (every row's record, in order) and the row's position in
    it, after an identity check. Equal sources registered from different
    venues share one digest, so their rows key alike.
    """

    _rows: dict[int, tuple[str, int, Any]] = field(default_factory=dict)
    _sources: dict[int, tuple[str, tuple[Any, ...]]] = field(default_factory=dict)

    def register_source(self, rows: Sequence[Any]) -> str:
        source = tuple(rows)
        known = self._sources.get(id(rows))
        if known is not None and known[1] is rows:
            return known[0]
        digest = hashlib.sha256()
        digest.update(b"ROWS")
        for row in source:
            data = _row_record_bytes(row)
            digest.update(len(data).to_bytes(8, "big"))
            digest.update(data)
        name = digest.hexdigest()
        for index, row in enumerate(source):
            current = self._rows.get(id(row))
            if current is not None and current[2] is row and current[0] != name:
                # one object in two different sources: its position is ambiguous
                self._rows[id(row)] = ("", -1, row)
                continue
            self._rows[id(row)] = (name, index, row)
        self._sources[id(rows)] = (name, rows)  # keeps the source alive, so ids stay valid
        return name

    def key(self, name: str, args: Sequence[Any], kwargs: Mapping[str, Any]) -> str:
        digest = hashlib.sha256()
        digest.update(SHARED_POSITIONING_VERSION.encode() + b"\0" + name.encode() + b"\0")
        digest.update(b"A" + len(args).to_bytes(4, "big"))
        for value in args:
            self._encode(value, digest)
        digest.update(b"K" + len(kwargs).to_bytes(4, "big"))
        for keyword in sorted(kwargs):
            self._encode(keyword, digest)
            self._encode(kwargs[keyword], digest)
        return digest.hexdigest()

    def _encode(self, value: Any, out: Any) -> None:
        if value is None:
            out.update(b"N")
        elif value is True or value is False:
            out.update(b"B1" if value else b"B0")
        elif type(value) is int:
            text = str(value).encode()
            out.update(b"I" + len(text).to_bytes(4, "big") + text)
        elif type(value) is str:
            text = value.encode()
            out.update(b"S" + len(text).to_bytes(8, "big") + text)
        elif type(value) is Decimal:
            text = str(value).encode()  # exact: sign, digits and exponent
            out.update(b"D" + len(text).to_bytes(4, "big") + text)
        elif type(value) is datetime:
            if value.tzinfo is None:
                raise Unencodable("a naive datetime")
            text = (value.isoformat() + "|" + type(value.tzinfo).__name__).encode()
            out.update(b"T" + len(text).to_bytes(4, "big") + text)
        elif type(value) is date:
            text = value.isoformat().encode()
            out.update(b"d" + len(text).to_bytes(4, "big") + text)
        elif type(value) in (tuple, list):
            self._encode_sequence(value, out)
        elif type(value) is dict:
            out.update(b"M" + len(value).to_bytes(8, "big"))
            for item_key, item_value in value.items():  # insertion order is part of the value
                self._encode(item_key, out)
                self._encode(item_value, out)
        else:
            entry = self._rows.get(id(value))
            if entry is None or entry[2] is not value or entry[1] < 0:
                raise Unencodable(f"an unregistered {type(value).__name__}")
            out.update(b"r" + entry[0].encode() + entry[1].to_bytes(8, "big"))

    def _encode_sequence(self, value: Sequence[Any], out: Any) -> None:
        tag = b"U" if type(value) is tuple else b"L"
        if value:
            first = self._rows.get(id(value[0]))
            if first is not None and first[2] is value[0] and first[1] >= 0:
                source = first[0]
                positions = array("q")
                for item in value:
                    entry = self._rows.get(id(item))
                    if entry is None or entry[2] is not item or entry[0] != source:
                        break
                    positions.append(entry[1])
                else:
                    data = positions.tobytes()
                    out.update(tag + b"R" + source.encode() + len(data).to_bytes(8, "big") + data)
                    return
        out.update(tag + len(value).to_bytes(8, "big"))
        for item in value:
            self._encode(item, out)


# --- the store ------------------------------------------------------------------------------------


MISSING = object()


@dataclass
class SharedResultStore:
    """Pickled owner results, one file per key, plus a small in-memory cache of their bytes."""

    directory: Path
    memory_entries: int = 64
    _memory: OrderedDict[str, bytes] = field(default_factory=OrderedDict)

    def __post_init__(self) -> None:
        self.directory = Path(self.directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.directory / key[:2] / f"{key}.pickle"

    def get(self, key: str, name: str) -> Any:
        data = self._memory.get(key)
        if data is None:
            try:
                data = self._path(key).read_bytes()
            except FileNotFoundError:
                return MISSING
            self._remember(key, data)
        else:
            self._memory.move_to_end(key)
        tag, stored_key, stored_name, result = pickle.loads(data)
        if tag != _FILE_TAG or stored_key != key or stored_name != name:
            raise SharedPositioningError(f"the shared result {key} is not {name}'s")
        return result

    def put(self, key: str, name: str, result: Any) -> None:
        data = pickle.dumps((_FILE_TAG, key, name, result), protocol=_PICKLE_PROTOCOL)
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            # Written whole, then renamed: a reader sees the full file or none.
            # Concurrent writers of one key write equal bytes.
            handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=".partial-")
            try:
                with os.fdopen(handle, "wb") as stream:
                    stream.write(data)
                os.replace(temporary, path)
            except BaseException:
                if os.path.exists(temporary):
                    os.unlink(temporary)
                raise
        self._remember(key, data)

    def _remember(self, key: str, data: bytes) -> None:
        self._memory[key] = data
        self._memory.move_to_end(key)
        while len(self._memory) > self.memory_entries:
            self._memory.popitem(last=False)


# --- the scoped share -----------------------------------------------------------------------------


@dataclass
class ShareStatistics:
    """Value-free counts: served, computed and never-shared calls per function."""

    served: Counter[str] = field(default_factory=Counter)
    computed: Counter[str] = field(default_factory=Counter)
    not_shared: Counter[str] = field(default_factory=Counter)

    def as_record(self) -> dict[str, dict[str, int]]:
        return {
            name: {
                "served": self.served[name],
                "computed": self.computed[name],
                "not_shared": self.not_shared[name],
            }
            for name in SHARED_FUNCTIONS
        }

    def merge(self, other: ShareStatistics) -> None:
        self.served.update(other.served)
        self.computed.update(other.computed)
        self.not_shared.update(other.not_shared)


def register_positioning_sources(encoder: ArgumentEncoder, inputs: ec.EntryComposerInputs) -> None:
    """Register every replay source a shared call's rows come from."""

    shared = inputs.dataset.shared_snapshot
    for rows in (shared.funding_rates, shared.open_interest, inputs.futures_basis, inputs.market_caps):
        encoder.register_source(rows)


@contextmanager
def shared_positioning(
    store: SharedResultStore,
    encoder: ArgumentEncoder,
    statistics: ShareStatistics | None = None,
) -> Iterator[ShareStatistics]:
    """Serve :data:`SHARED_FUNCTIONS` from ``store`` inside the block, computing and storing misses."""

    stats = statistics if statistics is not None else ShareStatistics()
    originals = {name: _owner_function(name) for name in SHARED_FUNCTIONS}

    def wrap(name: str, owner: Callable[..., Any]) -> Callable[..., Any]:
        def shared(*args: Any, **kwargs: Any) -> Any:
            try:
                key = encoder.key(name, args, kwargs)
            except Unencodable:
                stats.not_shared[name] += 1
                return owner(*args, **kwargs)
            found = store.get(key, name)
            if found is not MISSING:
                stats.served[name] += 1
                return found
            result = owner(*args, **kwargs)
            store.put(key, name, result)
            stats.computed[name] += 1
            # the caller gets the stored bytes' copy, as every later caller will
            return store.get(key, name)

        shared.__wrapped__ = owner  # type: ignore[attr-defined]
        return shared

    for name, owner in originals.items():
        setattr(ec, name, wrap(name, owner))
    try:
        yield stats
    finally:
        for name, owner in originals.items():
            setattr(ec, name, owner)
