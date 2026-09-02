"""Actual manual trade entries (BTC-202).

The recommendation decision journal records what the operator decided about an
advisory. This module records the different fact that an entry fill really
happened. A linked fill must come from a validated APPROVED or MODIFIED BTC-200
decision; REJECTED and MISSED decisions do not describe executions.

The BTC-017 table also supports MANUAL_ONLY trades. Those deliberately carry
no strategy/config identity or discretionary decision codes because no model
recommendation produced them. Missing stops and exits remain ``None`` rather
than being converted to zero.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from btc_predictor.data import require_utc_datetime
from btc_predictor.db.portfolio import manual_trade_journal
from btc_predictor.journal.decision_journal import (
    APPROVED,
    DECISION_JOURNAL_POLICY_VERSION,
    DISCRETIONARY_REASON_CODES,
    DISCRETIONARY_REASON_POLICY_VERSION,
    MODIFIED,
    RecommendationDecisionEntry,
    recommendation_decision_from_record,
    verify_decision_entry,
)


ACTUAL_TRADE_FEATURE_ID = "ACTUAL_TRADE_ENTRY"
ACTUAL_TRADE_POLICY_VERSION = "MANUAL_EXECUTION_JOURNAL_V1"
ACTUAL_TRADE_TABLE = "manual_trade_journal"

FOLLOWED = "FOLLOWED"
OVERRIDDEN = "OVERRIDDEN"
MANUAL_ONLY = "MANUAL_ONLY"

_EXECUTED_DECISIONS = (APPROVED, MODIFIED)
_ACTUAL_DIRECTIONS = ("long", "short")
_RECORD_KEYS = (
    "feature_id",
    "policy_version",
    "recommendation_id",
    "strategy_version",
    "parameter_set_id",
    "config_version",
    "decision_journal_policy_version",
    "decision_decided_at",
    "decision_reason_codes",
    "discretionary_reason_policy_version",
    "discretionary_reason_codes",
    "symbol",
    "direction",
    "journaled_at",
    "manual_decision",
    "override_reason",
    "actual_entry_time",
    "actual_entry_price",
    "actual_size",
    "actual_size_unit",
    "actual_stop",
    "actual_exit_time",
    "actual_exit_price",
    "notes",
)
_WRITABLE_COLUMNS = frozenset(
    column.name for column in manual_trade_journal.columns
) - {"manual_trade_id"}


@dataclass(frozen=True)
class ActualTradeEntry:
    """One observed manual trade, ready for deterministic persistence."""

    feature_id: str
    policy_version: str
    recommendation_id: int | None
    strategy_version: str | None
    parameter_set_id: str | None
    config_version: str | None
    decision_journal_policy_version: str | None
    decision_decided_at: datetime | None
    decision_reason_codes: tuple[str, ...] | None
    discretionary_reason_policy_version: str | None
    discretionary_reason_codes: tuple[str, ...] | None
    symbol: str
    direction: str
    journaled_at: datetime
    manual_decision: str
    override_reason: str | None
    actual_entry_time: datetime
    actual_entry_price: Decimal
    actual_size: Decimal
    actual_size_unit: str
    actual_stop: Decimal | None
    actual_exit_time: datetime | None
    actual_exit_price: Decimal | None
    notes: str | None

    @property
    def is_closed(self) -> bool:
        return self.actual_exit_time is not None

    @property
    def config_metadata(self) -> dict[str, str] | None:
        if self.config_version is None:
            return None
        return {
            "config_version": self.config_version,
            "strategy_version": self.strategy_version,
            "parameter_set_id": self.parameter_set_id,
        }

    def as_record(self) -> dict[str, Any]:
        """Return a deterministic, self-validating execution record."""

        verify_actual_trade_entry(self)
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "recommendation_id": self.recommendation_id,
            "strategy_version": self.strategy_version,
            "parameter_set_id": self.parameter_set_id,
            "config_version": self.config_version,
            "decision_journal_policy_version": self.decision_journal_policy_version,
            "decision_decided_at": _datetime_record(self.decision_decided_at),
            "decision_reason_codes": _sequence_record(self.decision_reason_codes),
            "discretionary_reason_policy_version": (
                self.discretionary_reason_policy_version
            ),
            "discretionary_reason_codes": _sequence_record(
                self.discretionary_reason_codes,
            ),
            "symbol": self.symbol,
            "direction": self.direction,
            "journaled_at": self.journaled_at.isoformat(),
            "manual_decision": self.manual_decision,
            "override_reason": self.override_reason,
            "actual_entry_time": self.actual_entry_time.isoformat(),
            "actual_entry_price": str(self.actual_entry_price),
            "actual_size": str(self.actual_size),
            "actual_size_unit": self.actual_size_unit,
            "actual_stop": _decimal_record(self.actual_stop),
            "actual_exit_time": _datetime_record(self.actual_exit_time),
            "actual_exit_price": _decimal_record(self.actual_exit_price),
            "notes": self.notes,
        }

    def as_row(self) -> dict[str, Any]:
        """Map exactly onto ``portfolio.manual_trade_journal``."""

        self.as_record()
        row = {
            "recommendation_id": self.recommendation_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "journaled_at": self.journaled_at,
            "manual_decision": self.manual_decision,
            "override_reason": self.override_reason,
            "actual_entry_time": self.actual_entry_time,
            "actual_entry_price": self.actual_entry_price,
            "actual_size": self.actual_size,
            "actual_size_unit": self.actual_size_unit,
            "actual_stop": self.actual_stop,
            "actual_exit_time": self.actual_exit_time,
            "actual_exit_price": self.actual_exit_price,
            "notes": self.notes,
            "strategy_version": self.strategy_version,
            "parameter_set_id": self.parameter_set_id,
            "config_version": self.config_version,
            "decision_journal_policy_version": self.decision_journal_policy_version,
            "decision_decided_at": self.decision_decided_at,
            "decision_reason_codes": _sequence_record(self.decision_reason_codes),
            "discretionary_reason_policy_version": (
                self.discretionary_reason_policy_version
            ),
            "discretionary_reason_codes": _sequence_record(
                self.discretionary_reason_codes,
            ),
            "execution_journal_policy_version": self.policy_version,
        }
        if set(row) != _WRITABLE_COLUMNS:
            raise ValueError(
                f"{ACTUAL_TRADE_TABLE} row does not match the table columns: "
                f"{sorted(set(row) ^ _WRITABLE_COLUMNS)}",
            )
        return row


def record_actual_trade_entry(
    *,
    symbol: str,
    direction: str,
    journaled_at: datetime,
    actual_entry_time: datetime,
    actual_entry_price: Decimal | str | int | float,
    actual_size: Decimal | str | int | float,
    actual_size_unit: str,
    recommendation_decision: RecommendationDecisionEntry | Mapping[str, Any] | None = None,
    actual_stop: Decimal | str | int | float | None = None,
    actual_exit_time: datetime | None = None,
    actual_exit_price: Decimal | str | int | float | None = None,
    override_reason: str | None = None,
    notes: str | None = None,
) -> ActualTradeEntry:
    """Record one actual entry fill, optionally linked to a model decision."""

    source = _decision_source(recommendation_decision)
    recorded_symbol = _bounded_identity(symbol, "symbol", maximum=32)
    recorded_direction = _direction(direction)
    entry_time = _utc_datetime(actual_entry_time, "actual_entry_time")
    journal_time = _utc_datetime(journaled_at, "journaled_at")

    if source is None:
        attribution: dict[str, Any] = {
            "recommendation_id": None,
            "strategy_version": None,
            "parameter_set_id": None,
            "config_version": None,
            "decision_journal_policy_version": None,
            "decision_decided_at": None,
            "decision_reason_codes": None,
            "discretionary_reason_policy_version": None,
            "discretionary_reason_codes": None,
            "manual_decision": MANUAL_ONLY,
        }
    else:
        verify_decision_entry(source)
        if source.decision not in _EXECUTED_DECISIONS:
            raise ValueError(
                f"actual execution requires a decision in {_EXECUTED_DECISIONS}",
            )
        advisory = source.advisory().recommendation
        if advisory.action != "ENTER":
            raise ValueError("actual trade entry requires an ENTER advisory")
        if recorded_symbol != advisory.symbol:
            raise ValueError("execution symbol does not match the advised symbol")
        if recorded_direction != advisory.direction:
            raise ValueError("execution direction does not match the advised direction")
        if entry_time < source.decided_at:
            raise ValueError("actual_entry_time must not precede the recorded decision")
        attribution = {
            "recommendation_id": source.recommendation_id,
            "strategy_version": source.provenance.strategy_version,
            "parameter_set_id": source.provenance.parameter_set_id,
            "config_version": source.config_version,
            "decision_journal_policy_version": source.policy_version,
            "decision_decided_at": source.decided_at,
            "decision_reason_codes": source.reason_codes,
            "discretionary_reason_policy_version": (
                source.discretionary_reason_policy_version
            ),
            "discretionary_reason_codes": source.discretionary_reason_codes,
            "manual_decision": FOLLOWED if source.decision == APPROVED else OVERRIDDEN,
        }

    entry = ActualTradeEntry(
        feature_id=ACTUAL_TRADE_FEATURE_ID,
        policy_version=ACTUAL_TRADE_POLICY_VERSION,
        **attribution,
        symbol=recorded_symbol,
        direction=recorded_direction,
        journaled_at=journal_time,
        override_reason=_optional_text(override_reason, "override_reason"),
        actual_entry_time=entry_time,
        actual_entry_price=_positive_decimal(actual_entry_price, "actual_entry_price"),
        actual_size=_positive_decimal(actual_size, "actual_size"),
        actual_size_unit=_bounded_identity(
            actual_size_unit,
            "actual_size_unit",
            maximum=16,
        ),
        actual_stop=_optional_positive_decimal(actual_stop, "actual_stop"),
        actual_exit_time=_optional_utc_datetime(actual_exit_time, "actual_exit_time"),
        actual_exit_price=_optional_positive_decimal(
            actual_exit_price,
            "actual_exit_price",
        ),
        notes=_optional_text(notes, "notes"),
    )
    entry.as_record()
    return entry


def actual_trade_entry_from_record(source: Mapping[str, Any] | Any) -> ActualTradeEntry:
    """Restore a serialized entry and reject policy or record drift."""

    row = _as_mapping(source, "actual trade entry record")
    unknown = set(row) - set(_RECORD_KEYS)
    if unknown:
        raise ValueError(f"actual trade entry record has unknown fields: {sorted(unknown)}")
    entry = ActualTradeEntry(
        feature_id=row.get("feature_id"),
        policy_version=row.get("policy_version"),
        recommendation_id=_optional_positive_integer(
            row.get("recommendation_id"),
            "recommendation_id",
        ),
        strategy_version=_optional_identity(row.get("strategy_version"), "strategy_version"),
        parameter_set_id=_optional_identity(
            row.get("parameter_set_id"),
            "parameter_set_id",
        ),
        config_version=_optional_identity(row.get("config_version"), "config_version"),
        decision_journal_policy_version=_optional_identity(
            row.get("decision_journal_policy_version"),
            "decision_journal_policy_version",
        ),
        decision_decided_at=_optional_utc_datetime(
            row.get("decision_decided_at"),
            "decision_decided_at",
        ),
        decision_reason_codes=_optional_string_sequence(
            row.get("decision_reason_codes"),
            "decision_reason_codes",
        ),
        discretionary_reason_policy_version=_optional_identity(
            row.get("discretionary_reason_policy_version"),
            "discretionary_reason_policy_version",
        ),
        discretionary_reason_codes=_optional_string_sequence(
            row.get("discretionary_reason_codes"),
            "discretionary_reason_codes",
        ),
        symbol=_bounded_identity(row.get("symbol"), "symbol", maximum=32),
        direction=_direction(row.get("direction")),
        journaled_at=_utc_datetime(row.get("journaled_at"), "journaled_at"),
        manual_decision=row.get("manual_decision"),
        override_reason=_optional_text(row.get("override_reason"), "override_reason"),
        actual_entry_time=_utc_datetime(
            row.get("actual_entry_time"),
            "actual_entry_time",
        ),
        actual_entry_price=_positive_decimal(
            row.get("actual_entry_price"),
            "actual_entry_price",
        ),
        actual_size=_positive_decimal(row.get("actual_size"), "actual_size"),
        actual_size_unit=_bounded_identity(
            row.get("actual_size_unit"),
            "actual_size_unit",
            maximum=16,
        ),
        actual_stop=_optional_positive_decimal(row.get("actual_stop"), "actual_stop"),
        actual_exit_time=_optional_utc_datetime(
            row.get("actual_exit_time"),
            "actual_exit_time",
        ),
        actual_exit_price=_optional_positive_decimal(
            row.get("actual_exit_price"),
            "actual_exit_price",
        ),
        notes=_optional_text(row.get("notes"), "notes"),
    )
    if entry.as_record() != dict(row):
        raise ValueError("actual trade entry record does not match its validated entry")
    return entry


def verify_actual_trade_entry(entry: ActualTradeEntry) -> None:
    """Raise unless an entry is internally coherent and persistable."""

    if not isinstance(entry, ActualTradeEntry):
        raise TypeError("entry must be an ActualTradeEntry")
    if entry.feature_id != ACTUAL_TRADE_FEATURE_ID:
        raise ValueError(f"feature_id must be {ACTUAL_TRADE_FEATURE_ID}")
    if entry.policy_version != ACTUAL_TRADE_POLICY_VERSION:
        raise ValueError(f"policy_version must be {ACTUAL_TRADE_POLICY_VERSION}")

    _bounded_identity(entry.symbol, "symbol", maximum=32)
    _direction(entry.direction)
    journaled_at = _utc_datetime(entry.journaled_at, "journaled_at")
    entry_time = _utc_datetime(entry.actual_entry_time, "actual_entry_time")
    _positive_decimal(entry.actual_entry_price, "actual_entry_price")
    _positive_decimal(entry.actual_size, "actual_size")
    _bounded_identity(entry.actual_size_unit, "actual_size_unit", maximum=16)
    _optional_positive_decimal(entry.actual_stop, "actual_stop")
    exit_time = _optional_utc_datetime(entry.actual_exit_time, "actual_exit_time")
    exit_price = _optional_positive_decimal(entry.actual_exit_price, "actual_exit_price")
    _optional_text(entry.notes, "notes")

    if journaled_at < entry_time:
        raise ValueError("journaled_at must not precede actual_entry_time")
    if (exit_time is None) != (exit_price is None):
        raise ValueError("actual exit time and price must be recorded together")
    if exit_time is not None:
        if exit_time < entry_time:
            raise ValueError("actual_exit_time must not precede actual_entry_time")
        if journaled_at < exit_time:
            raise ValueError("journaled_at must not precede actual_exit_time")

    if entry.manual_decision == MANUAL_ONLY:
        _verify_manual_only_attribution(entry)
    elif entry.manual_decision in (FOLLOWED, OVERRIDDEN):
        _verify_linked_attribution(entry)
    else:
        raise ValueError(
            f"an actual trade entry must be {FOLLOWED}, {OVERRIDDEN}, or {MANUAL_ONLY}",
        )

    reason = _optional_text(entry.override_reason, "override_reason")
    if entry.manual_decision == OVERRIDDEN and reason is None:
        raise ValueError("OVERRIDDEN requires an override_reason")
    if entry.manual_decision != OVERRIDDEN and reason is not None:
        raise ValueError("override_reason is only valid for OVERRIDDEN")


def _verify_manual_only_attribution(entry: ActualTradeEntry) -> None:
    attributed = (
        entry.recommendation_id,
        entry.strategy_version,
        entry.parameter_set_id,
        entry.config_version,
        entry.decision_journal_policy_version,
        entry.decision_decided_at,
        entry.decision_reason_codes,
        entry.discretionary_reason_policy_version,
        entry.discretionary_reason_codes,
    )
    if any(value is not None for value in attributed):
        raise ValueError("MANUAL_ONLY must not carry recommendation decision attribution")


def _verify_linked_attribution(entry: ActualTradeEntry) -> None:
    _optional_positive_integer(entry.recommendation_id, "recommendation_id")
    if entry.recommendation_id is None:
        raise ValueError("linked execution requires a recommendation_id")
    _identity(entry.strategy_version, "strategy_version")
    _identity(entry.parameter_set_id, "parameter_set_id")
    _identity(entry.config_version, "config_version")
    if entry.decision_journal_policy_version != DECISION_JOURNAL_POLICY_VERSION:
        raise ValueError(
            f"decision_journal_policy_version must be {DECISION_JOURNAL_POLICY_VERSION}",
        )
    decided_at = _optional_utc_datetime(entry.decision_decided_at, "decision_decided_at")
    if decided_at is None:
        raise ValueError("linked execution requires decision_decided_at")
    if entry.actual_entry_time < decided_at:
        raise ValueError("actual_entry_time must not precede the recorded decision")

    decision = APPROVED if entry.manual_decision == FOLLOWED else MODIFIED
    expected_reasons = (
        "DECISION_JOURNAL_RECORDED",
        f"DECISION_JOURNAL_{decision}",
    )
    if entry.decision_reason_codes != expected_reasons:
        raise ValueError("decision_reason_codes do not match manual_decision")
    if (
        entry.discretionary_reason_policy_version
        != DISCRETIONARY_REASON_POLICY_VERSION
    ):
        raise ValueError(
            "discretionary_reason_policy_version must be "
            f"{DISCRETIONARY_REASON_POLICY_VERSION}",
        )
    reasons = _optional_string_sequence(
        entry.discretionary_reason_codes,
        "discretionary_reason_codes",
    )
    if reasons is None:
        raise ValueError("linked execution requires discretionary_reason_codes")
    if len(set(reasons)) != len(reasons):
        raise ValueError("discretionary_reason_codes must not repeat a code")
    unknown = set(reasons) - set(DISCRETIONARY_REASON_CODES)
    if unknown:
        raise ValueError(
            "discretionary_reason_codes must be drawn from "
            f"{DISCRETIONARY_REASON_CODES}",
        )
    canonical = tuple(code for code in DISCRETIONARY_REASON_CODES if code in set(reasons))
    if reasons != canonical:
        raise ValueError("discretionary_reason_codes are not in canonical order")


def _decision_source(
    source: RecommendationDecisionEntry | Mapping[str, Any] | None,
) -> RecommendationDecisionEntry | None:
    if source is None:
        return None
    if isinstance(source, RecommendationDecisionEntry):
        return source
    if isinstance(source, Mapping) or isinstance(getattr(source, "_mapping", None), Mapping):
        return recommendation_decision_from_record(source)
    raise TypeError(
        "recommendation_decision must be a RecommendationDecisionEntry, "
        "serialized decision record, or None",
    )


def _as_mapping(source: Mapping[str, Any] | Any, name: str) -> Mapping[str, Any]:
    if isinstance(source, Mapping):
        return source
    row = getattr(source, "_mapping", None)
    if isinstance(row, Mapping):
        return row
    raise TypeError(f"{name} must be a mapping or database row")


def _utc_datetime(value: Any, name: str) -> datetime:
    parsed = value
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{name} must be an ISO-8601 datetime") from exc
    if not isinstance(parsed, datetime):
        raise TypeError(f"{name} must be a datetime or ISO-8601 string")
    return require_utc_datetime(parsed, name)


def _optional_utc_datetime(value: Any, name: str) -> datetime | None:
    return None if value is None else _utc_datetime(value, name)


def _positive_decimal(value: Any, name: str) -> Decimal:
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not result.is_finite() or result <= 0:
        raise ValueError(f"{name} must be finite and greater than zero")
    return result


def _optional_positive_decimal(value: Any, name: str) -> Decimal | None:
    return None if value is None else _positive_decimal(value, name)


def _direction(value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError("direction must be a string")
    if value not in _ACTUAL_DIRECTIONS:
        raise ValueError(f"direction must be one of {_ACTUAL_DIRECTIONS}")
    return value


def _bounded_identity(value: Any, name: str, *, maximum: int) -> str:
    result = _identity(value, name)
    if len(result) > maximum:
        raise ValueError(f"{name} must contain at most {maximum} characters")
    return result


def _identity(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be non-empty trimmed text")
    return value


def _optional_identity(value: Any, name: str) -> str | None:
    return None if value is None else _identity(value, name)


def _optional_text(value: Any, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value or value != value.strip():
        raise ValueError(f"{name} must be non-empty trimmed text")
    return value


def _optional_positive_integer(value: Any, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _optional_string_sequence(value: Any, name: str) -> tuple[str, ...] | None:
    if value is None:
        return None
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{name} must be a sequence of strings or None")
    values = tuple(value)
    if any(not isinstance(item, str) or not item.strip() for item in values):
        raise ValueError(f"{name} must contain non-empty strings")
    return values


def _datetime_record(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _decimal_record(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _sequence_record(value: tuple[str, ...] | None) -> list[str] | None:
    return None if value is None else list(value)


__all__ = [
    "ACTUAL_TRADE_FEATURE_ID",
    "ACTUAL_TRADE_POLICY_VERSION",
    "ACTUAL_TRADE_TABLE",
    "ActualTradeEntry",
    "FOLLOWED",
    "MANUAL_ONLY",
    "OVERRIDDEN",
    "actual_trade_entry_from_record",
    "record_actual_trade_entry",
    "verify_actual_trade_entry",
]
