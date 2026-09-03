"""Point-in-time-safe trailing-stop progression (BTC-156).

For a long, ``candidate = new higher low - BTC-141 buffer`` and the standing
stop takes the maximum. For a short, ``candidate = new lower high + buffer``
and the standing stop takes the minimum. The numerical calculator is pure; the
canonical path additionally requires confirmed structure identity, availability
time, an authoritative BTC-141 result, and a BTC-150 lifecycle.

Calculation and application are separate. Re-evaluating a pure calculation is
deterministic and mutates nothing. ``apply_trailing_stop`` records an accepted
advance with its structure identity in the BTC-150 transition payload. After
that transition is persisted or replayed, the same structure cannot advance the
stop again, even if its buffer changes.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import numpy as np

from btc_predictor.data import require_utc_datetime
from btc_predictor.quant.comparisons import (
    DECISION_COMPARISON_POLICY_VERSION,
    decision_equal,
    decision_greater,
    decision_greater_equal,
    decision_less,
    decision_less_equal,
)
from btc_predictor.risk.buffer import (
    VOLATILITY_BUFFER_FEATURE_ID,
    VOLATILITY_BUFFER_POLICY_VERSION,
    VolatilityBufferResult,
)
from btc_predictor.risk.invalidation import (
    INVALIDATION_DIRECTIONS,
    LONG_DIRECTION,
    SHORT_DIRECTION,
)


TRAILING_STOP_FEATURE_ID = "TRAILING_STOP"
TRAILING_STOP_POLICY_VERSION = "TRAILING_STOP_V1"
DIRECT_BUFFER_FEATURE_ID = "DIRECT_NUMERIC_BUFFER"
DIRECT_BUFFER_POLICY_VERSION = "DIRECT_NUMERIC_BUFFER_V1"

THESIS_STOP = "THESIS_STOP"
CONFIRMATION_STOP = "CONFIRMATION_STOP"
PROFIT_PROTECTION_TRAIL = "PROFIT_PROTECTION_TRAIL"
TRAILING_STOP_STAGES = (THESIS_STOP, CONFIRMATION_STOP, PROFIT_PROTECTION_TRAIL)

HIGHER_LOW = "HIGHER_LOW"
LOWER_HIGH = "LOWER_HIGH"
TRAILING_STRUCTURE_TYPES = (HIGHER_LOW, LOWER_HIGH)

TRAILING_STOP_REASON_CODES = (
    "TRAILING_STOP_ADVANCED",
    "TRAILING_STOP_HELD",
    "TRAILING_STOP_NO_NEW_STRUCTURE",
    "TRAILING_STOP_INPUT_MISSING",
    "TRAILING_STOP_BUFFER_INCOMPLETE",
    "TRAILING_STOP_CANDIDATE_NON_POSITIVE",
    "TRAILING_STOP_CANDIDATE_BEYOND_PRICE",
    "TRAILING_STOP_STRUCTURE_ALREADY_USED",
)
_REQUIRED_CONFIG_METADATA_KEYS = (
    "config_version",
    "strategy_version",
    "parameter_set_id",
)


@dataclass(frozen=True)
class ConfirmedTrailingStructure:
    """A newly confirmed structural point available by a decision timestamp."""

    structure_id: str
    source_feature_id: str
    direction: str
    structure_type: str
    price: Decimal
    level_timestamp: datetime
    detected_at: datetime
    config_metadata: dict[str, str]
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        structure_id = _required_string(self.structure_id, "structure_id")
        source_feature_id = _required_string(
            self.source_feature_id,
            "source_feature_id",
        )
        direction = _direction(self.direction)
        structure_type = _structure_type(self.structure_type, direction=direction)
        price = _positive_decimal(self.price, "price")
        level_timestamp = require_utc_datetime(
            self.level_timestamp,
            "level_timestamp",
        )
        detected_at = require_utc_datetime(self.detected_at, "detected_at")
        if detected_at < level_timestamp:
            raise ValueError("detected_at must be >= level_timestamp")
        metadata = _validate_config_metadata(self.config_metadata)
        reasons = _reason_codes(self.reason_codes)
        return {
            "structure_id": structure_id,
            "source_feature_id": source_feature_id,
            "direction": direction,
            "structure_type": structure_type,
            "price": str(price),
            "level_timestamp": level_timestamp.isoformat(),
            "detected_at": detected_at.isoformat(),
            "config_metadata": metadata,
            "reason_codes": list(reasons),
        }


@dataclass(frozen=True)
class TrailingStopResult:
    feature_id: str
    policy_version: str
    direction: str
    stage: str
    prior_advance_count: int
    advance_count: int
    previous_stop: Decimal
    structure_id: str | None
    structure_source_feature_id: str | None
    structure_type: str | None
    structure_price: Decimal | None
    structure_level_timestamp: datetime | None
    structure_detected_at: datetime | None
    structure_reason_codes: tuple[str, ...]
    structure_already_used: bool
    buffer_feature_id: str | None
    buffer_policy_version: str | None
    buffer: Decimal | None
    buffer_reason_codes: tuple[str, ...]
    candidate_stop: Decimal | None
    stop_price: Decimal
    current_price: Decimal | None
    evaluated_at: datetime | None
    advanced: bool
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        """Return a fully validated record that can be reconstructed exactly."""

        normalized = _validate_result(self, require_persistence_context=True)
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "comparison_policy": DECISION_COMPARISON_POLICY_VERSION,
            "direction": normalized.direction,
            "stage": self.stage,
            "prior_advance_count": self.prior_advance_count,
            "advance_count": self.advance_count,
            "previous_stop": str(normalized.previous_stop),
            "structure_id": self.structure_id,
            "structure_source_feature_id": self.structure_source_feature_id,
            "structure_type": self.structure_type,
            "structure_price": _optional(normalized.structure_price),
            "structure_level_timestamp": _optional_time(
                self.structure_level_timestamp,
            ),
            "structure_detected_at": _optional_time(self.structure_detected_at),
            "structure_reason_codes": list(normalized.structure_reason_codes),
            "structure_already_used": self.structure_already_used,
            "buffer_feature_id": self.buffer_feature_id,
            "buffer_policy_version": self.buffer_policy_version,
            "buffer": _optional(normalized.buffer),
            "buffer_reason_codes": list(normalized.buffer_reason_codes),
            "candidate_stop": _optional(normalized.candidate_stop),
            "stop_price": str(normalized.stop_price),
            "current_price": _optional(normalized.current_price),
            "evaluated_at": _optional_time(self.evaluated_at),
            "advanced": self.advanced,
            "config_metadata": normalized.config_metadata,
            "complete": self.complete,
            "reason_codes": list(normalized.reason_codes),
        }


@dataclass(frozen=True)
class _NormalizedResult:
    direction: str
    previous_stop: Decimal
    structure_price: Decimal | None
    structure_reason_codes: tuple[str, ...]
    buffer: Decimal | None
    buffer_reason_codes: tuple[str, ...]
    candidate_stop: Decimal | None
    stop_price: Decimal
    current_price: Decimal | None
    config_metadata: dict[str, str]
    reason_codes: tuple[str, ...]


def calculate_trailing_stop(
    *,
    direction: str,
    previous_stop: Any,
    structure_price: Any | None = None,
    buffer: Any | None = None,
    advance_count: int = 0,
    current_price: Any | None = None,
    config_metadata: Mapping[str, str] | None = None,
    evaluated_at: datetime | None = None,
    structure_id: str | None = None,
    structure_source_feature_id: str | None = None,
    structure_type: str | None = None,
    structure_level_timestamp: datetime | None = None,
    structure_detected_at: datetime | None = None,
    structure_reason_codes: tuple[str, ...] = (),
    structure_already_used: bool = False,
    buffer_feature_id: str | None = None,
    buffer_policy_version: str | None = None,
    buffer_reason_codes: tuple[str, ...] = (),
) -> TrailingStopResult:
    """Apply the directionally mirrored ratchet to validated numeric inputs.

    This low-level function proves the arithmetic and accepts a direct numeric
    buffer. ``trail_stop_for_position`` is the strategy path: it owns PIT
    validation, source identity, BTC-141 provenance, and ledger-derived state.
    A BTC-156 calculation requires an existing stop; BTC-142 alone establishes
    the initial thesis stop.
    """

    direction_value = _direction(direction)
    prior_count = _advance_count(advance_count, "advance_count")
    standing = _positive_decimal(previous_stop, "previous_stop")
    structure = (
        _positive_decimal(structure_price, "structure_price")
        if structure_price is not None
        else None
    )
    buffer_value = (
        _non_negative_decimal(buffer, "buffer") if buffer is not None else None
    )
    price = (
        _positive_decimal(current_price, "current_price")
        if current_price is not None
        else None
    )
    metadata = _metadata(config_metadata or {})
    signal_time = (
        require_utc_datetime(evaluated_at, "evaluated_at")
        if evaluated_at is not None
        else None
    )
    structure_reasons = _reason_codes(structure_reason_codes)
    buffer_reasons = _reason_codes(buffer_reason_codes)
    if not isinstance(structure_already_used, bool):
        raise TypeError("structure_already_used must be a bool")

    if buffer_value is not None and buffer_feature_id is None:
        buffer_feature_id = DIRECT_BUFFER_FEATURE_ID
        buffer_policy_version = DIRECT_BUFFER_POLICY_VERSION
    _optional_source_identity(
        buffer_feature_id,
        buffer_policy_version,
        "buffer",
    )

    def held(
        reason: str,
        *,
        candidate: Decimal | None = None,
        complete: bool = True,
    ) -> TrailingStopResult:
        return _result(
            direction=direction_value,
            prior_advance_count=prior_count,
            previous_stop=standing,
            structure_id=structure_id,
            structure_source_feature_id=structure_source_feature_id,
            structure_type=structure_type,
            structure_price=structure,
            structure_level_timestamp=structure_level_timestamp,
            structure_detected_at=structure_detected_at,
            structure_reason_codes=structure_reasons,
            structure_already_used=structure_already_used,
            buffer_feature_id=buffer_feature_id,
            buffer_policy_version=buffer_policy_version,
            buffer=buffer_value,
            buffer_reason_codes=buffer_reasons,
            candidate_stop=candidate,
            stop_price=standing,
            current_price=price,
            evaluated_at=signal_time,
            advanced=False,
            config_metadata=metadata,
            complete=complete,
            reason_codes=(reason,),
        )

    if structure is None:
        return held("TRAILING_STOP_NO_NEW_STRUCTURE")
    if structure_already_used:
        candidate = (
            None
            if buffer_value is None
            else _candidate(direction_value, structure, buffer_value)
        )
        return held("TRAILING_STOP_STRUCTURE_ALREADY_USED", candidate=candidate)
    if buffer_value is None:
        return held("TRAILING_STOP_BUFFER_INCOMPLETE", complete=False)

    candidate = _candidate(direction_value, structure, buffer_value)
    if decision_less_equal(candidate, 0):
        return held("TRAILING_STOP_CANDIDATE_NON_POSITIVE", candidate=candidate)
    if price is not None and _beyond_price(
        direction=direction_value,
        candidate=candidate,
        current_price=price,
    ):
        return held("TRAILING_STOP_CANDIDATE_BEYOND_PRICE", candidate=candidate)
    if not _improves(
        direction=direction_value,
        candidate=candidate,
        previous_stop=standing,
    ):
        return held("TRAILING_STOP_HELD", candidate=candidate)

    return _result(
        direction=direction_value,
        prior_advance_count=prior_count,
        previous_stop=standing,
        structure_id=structure_id,
        structure_source_feature_id=structure_source_feature_id,
        structure_type=structure_type,
        structure_price=structure,
        structure_level_timestamp=structure_level_timestamp,
        structure_detected_at=structure_detected_at,
        structure_reason_codes=structure_reasons,
        structure_already_used=False,
        buffer_feature_id=buffer_feature_id,
        buffer_policy_version=buffer_policy_version,
        buffer=buffer_value,
        buffer_reason_codes=buffer_reasons,
        candidate_stop=candidate,
        stop_price=candidate,
        current_price=price,
        evaluated_at=signal_time,
        advanced=True,
        config_metadata=metadata,
        complete=True,
        reason_codes=("TRAILING_STOP_ADVANCED",),
    )


def trail_stop_for_position(
    lifecycle: Any,
    *,
    structure: ConfirmedTrailingStructure | None = None,
    buffer: VolatilityBufferResult | None = None,
    current_price: Any | None = None,
    as_of: datetime,
) -> TrailingStopResult:
    """Canonical PIT-safe path from BTC-150, confirmed structure, and BTC-141."""

    from btc_predictor.portfolio.state_machine import PositionLifecycle

    if not isinstance(lifecycle, PositionLifecycle):
        raise TypeError("lifecycle must be a PositionLifecycle")
    if not lifecycle.is_open:
        raise ValueError("lifecycle must contain an open position")
    if lifecycle.stop_price is None:
        raise ValueError("open lifecycle must contain a standing stop")
    signal_time = require_utc_datetime(as_of, "as_of")
    if lifecycle.last_event_at is not None and signal_time < lifecycle.last_event_at:
        # The standing stop and the advance count are read off the ledger as it
        # stands now, so a result stamped before the ledger's own watermark
        # would claim to have been evaluated on state that did not exist yet.
        # BTC-158 refuses the same composition for the same reason.
        raise ValueError("as_of must not precede the lifecycle watermark")
    metadata = _validate_config_metadata(lifecycle.config_metadata)

    structure_values: dict[str, Any] = {
        "structure_id": None,
        "structure_source_feature_id": None,
        "structure_type": None,
        "structure_price": None,
        "structure_level_timestamp": None,
        "structure_detected_at": None,
        "structure_reason_codes": (),
    }
    already_used = False
    if structure is not None:
        if not isinstance(structure, ConfirmedTrailingStructure):
            raise TypeError("structure must be a ConfirmedTrailingStructure or None")
        structure_record = structure.as_record()
        if structure.direction != lifecycle.direction:
            raise ValueError("structure direction does not match lifecycle direction")
        if structure.detected_at > signal_time:
            raise ValueError("structure must be available by as_of")
        if structure.config_metadata != metadata:
            raise ValueError("structure config_metadata does not match lifecycle")
        already_used = structure.structure_id in used_trailing_structure_ids(lifecycle)
        structure_values = {
            "structure_id": structure_record["structure_id"],
            "structure_source_feature_id": structure_record["source_feature_id"],
            "structure_type": structure_record["structure_type"],
            "structure_price": structure.price,
            "structure_level_timestamp": structure.level_timestamp,
            "structure_detected_at": structure.detected_at,
            "structure_reason_codes": structure.reason_codes,
        }

    buffer_value = None
    buffer_feature_id = None
    buffer_policy_version = None
    buffer_reasons: tuple[str, ...] = ()
    if buffer is not None:
        if not isinstance(buffer, VolatilityBufferResult):
            raise TypeError("buffer must be a VolatilityBufferResult or None")
        buffer_record = buffer.as_record()
        if buffer.feature_id != VOLATILITY_BUFFER_FEATURE_ID:
            raise ValueError("buffer feature_id must be VOLATILITY_BUFFER")
        if buffer.policy_version != VOLATILITY_BUFFER_POLICY_VERSION:
            raise ValueError(
                f"buffer policy_version must be {VOLATILITY_BUFFER_POLICY_VERSION}",
            )
        if buffer.config_metadata != metadata:
            raise ValueError("buffer config_metadata does not match lifecycle")
        buffer_value = buffer.buffer if buffer.complete else None
        buffer_feature_id = buffer_record["feature_id"]
        buffer_policy_version = buffer_record["policy_version"]
        buffer_reasons = buffer.reason_codes

    return calculate_trailing_stop(
        direction=lifecycle.direction,
        previous_stop=lifecycle.stop_price,
        buffer=buffer_value,
        advance_count=stop_advance_count(lifecycle),
        current_price=current_price,
        config_metadata=metadata,
        evaluated_at=signal_time,
        structure_already_used=already_used,
        buffer_feature_id=buffer_feature_id,
        buffer_policy_version=buffer_policy_version,
        buffer_reason_codes=buffer_reasons,
        **structure_values,
    )


def apply_trailing_stop(
    lifecycle: Any,
    result: TrailingStopResult,
    *,
    event_time: datetime,
):
    """Atomically record an advanced result; held calculations leave no event."""

    from btc_predictor.portfolio.state_machine import (
        STOP_MOVE,
        PositionLifecycle,
        apply_position_event,
    )

    if not isinstance(lifecycle, PositionLifecycle):
        raise TypeError("lifecycle must be a PositionLifecycle")
    if not isinstance(result, TrailingStopResult):
        raise TypeError("result must be a TrailingStopResult")
    result.as_record()
    moment = require_utc_datetime(event_time, "event_time")
    if result.evaluated_at is None or result.evaluated_at > moment:
        raise ValueError("event_time must be >= trailing-stop evaluated_at")
    if result.direction != lifecycle.direction:
        raise ValueError("result direction does not match lifecycle")
    if result.config_metadata != lifecycle.config_metadata:
        raise ValueError("result config_metadata does not match lifecycle")
    if lifecycle.stop_price is None or not decision_equal(
        result.previous_stop,
        lifecycle.stop_price,
    ):
        raise ValueError("result previous_stop does not match lifecycle")
    current_count = stop_advance_count(lifecycle)
    if result.prior_advance_count != current_count:
        raise ValueError("result prior_advance_count does not match lifecycle")
    if not result.advanced:
        return lifecycle
    if result.structure_id is None:
        raise ValueError("an advanced result requires structure identity")
    return apply_position_event(
        lifecycle,
        event=STOP_MOVE,
        event_time=moment,
        stop_price=result.stop_price,
        reason_codes=result.reason_codes,
        source_feature_id=TRAILING_STOP_FEATURE_ID,
        source_record_id=result.structure_id,
    )


def stop_advance_count(lifecycle: Any) -> int:
    """Count accepted post-entry events that actually tightened the stop."""

    transitions = getattr(lifecycle, "transitions", None)
    direction = getattr(lifecycle, "direction", None)
    if transitions is None:
        raise ValueError("lifecycle must expose transitions")
    direction_value = _direction(direction)
    count = 0
    entered = False
    standing: Decimal | None = None
    for transition in transitions:
        if not getattr(transition, "accepted", False):
            continue
        event = getattr(transition, "event", None)
        transition_stop = getattr(transition, "stop_price", None)
        if not entered:
            if event == "ENTER":
                entered = True
                standing = _positive_decimal(transition_stop, "entry stop_price")
            continue
        if transition_stop is None:
            continue
        candidate = _positive_decimal(transition_stop, "transition stop_price")
        if standing is None:
            raise ValueError("post-entry stop history lacks a standing stop")
        if _moves_backwards(
            direction=direction_value,
            previous_stop=standing,
            stop_price=candidate,
        ):
            raise ValueError("accepted lifecycle history contains a widened stop")
        if _improves(
            direction=direction_value,
            candidate=candidate,
            previous_stop=standing,
        ):
            count += 1
            standing = candidate
    return count


def used_trailing_structure_ids(lifecycle: Any) -> tuple[str, ...]:
    """Return accepted BTC-156 structure identities in ledger order."""

    transitions = getattr(lifecycle, "transitions", None)
    if transitions is None:
        raise ValueError("lifecycle must expose transitions")
    result = []
    for transition in transitions:
        if (
            getattr(transition, "accepted", False)
            and getattr(transition, "source_feature_id", None)
            == TRAILING_STOP_FEATURE_ID
        ):
            record_id = getattr(transition, "source_record_id", None)
            if record_id is None:
                raise ValueError("trailing transition lacks source_record_id")
            if record_id not in result:
                result.append(record_id)
    return tuple(result)


def trailing_stop_from_record(record: Mapping[str, Any]) -> TrailingStopResult:
    """Reconstruct and verify a persisted trailing-stop result."""

    if not isinstance(record, Mapping):
        raise TypeError("record must be a mapping")
    source = dict(record)
    if source.get("comparison_policy") != DECISION_COMPARISON_POLICY_VERSION:
        raise ValueError(
            f"comparison_policy must be {DECISION_COMPARISON_POLICY_VERSION}",
        )
    result = TrailingStopResult(
        feature_id=_required_string(source.get("feature_id"), "feature_id"),
        policy_version=_required_string(source.get("policy_version"), "policy_version"),
        direction=_required_string(source.get("direction"), "direction"),
        stage=_required_string(source.get("stage"), "stage"),
        prior_advance_count=_record_int(source, "prior_advance_count"),
        advance_count=_record_int(source, "advance_count"),
        previous_stop=_positive_decimal(source.get("previous_stop"), "previous_stop"),
        structure_id=_optional_string(source.get("structure_id"), "structure_id"),
        structure_source_feature_id=_optional_string(
            source.get("structure_source_feature_id"),
            "structure_source_feature_id",
        ),
        structure_type=_optional_string(
            source.get("structure_type"),
            "structure_type",
        ),
        structure_price=_optional_decimal(source.get("structure_price"), "structure_price"),
        structure_level_timestamp=_optional_utc(
            source.get("structure_level_timestamp"),
            "structure_level_timestamp",
        ),
        structure_detected_at=_optional_utc(
            source.get("structure_detected_at"),
            "structure_detected_at",
        ),
        structure_reason_codes=_reason_codes(source.get("structure_reason_codes", ())),
        structure_already_used=_record_bool(source, "structure_already_used"),
        buffer_feature_id=_optional_string(
            source.get("buffer_feature_id"),
            "buffer_feature_id",
        ),
        buffer_policy_version=_optional_string(
            source.get("buffer_policy_version"),
            "buffer_policy_version",
        ),
        buffer=_optional_decimal(source.get("buffer"), "buffer"),
        buffer_reason_codes=_reason_codes(source.get("buffer_reason_codes", ())),
        candidate_stop=_optional_decimal(source.get("candidate_stop"), "candidate_stop"),
        stop_price=_positive_decimal(source.get("stop_price"), "stop_price"),
        current_price=_optional_decimal(source.get("current_price"), "current_price"),
        evaluated_at=_optional_utc(source.get("evaluated_at"), "evaluated_at"),
        advanced=_record_bool(source, "advanced"),
        config_metadata=_validate_config_metadata(source.get("config_metadata", {})),
        complete=_record_bool(source, "complete"),
        reason_codes=_reason_codes(source.get("reason_codes", ())),
    )
    if result.as_record() != source:
        raise ValueError("record does not match reconstructed trailing-stop result")
    return result


def _result(
    *,
    direction: str,
    prior_advance_count: int,
    previous_stop: Decimal,
    structure_id: str | None,
    structure_source_feature_id: str | None,
    structure_type: str | None,
    structure_price: Decimal | None,
    structure_level_timestamp: datetime | None,
    structure_detected_at: datetime | None,
    structure_reason_codes: tuple[str, ...],
    structure_already_used: bool,
    buffer_feature_id: str | None,
    buffer_policy_version: str | None,
    buffer: Decimal | None,
    buffer_reason_codes: tuple[str, ...],
    candidate_stop: Decimal | None,
    stop_price: Decimal,
    current_price: Decimal | None,
    evaluated_at: datetime | None,
    advanced: bool,
    config_metadata: dict[str, str],
    complete: bool,
    reason_codes: tuple[str, ...],
) -> TrailingStopResult:
    output_count = prior_advance_count + (1 if advanced else 0)
    return TrailingStopResult(
        feature_id=TRAILING_STOP_FEATURE_ID,
        policy_version=TRAILING_STOP_POLICY_VERSION,
        direction=direction,
        stage=_stage_for(output_count),
        prior_advance_count=prior_advance_count,
        advance_count=output_count,
        previous_stop=previous_stop,
        structure_id=structure_id,
        structure_source_feature_id=structure_source_feature_id,
        structure_type=structure_type,
        structure_price=structure_price,
        structure_level_timestamp=structure_level_timestamp,
        structure_detected_at=structure_detected_at,
        structure_reason_codes=structure_reason_codes,
        structure_already_used=structure_already_used,
        buffer_feature_id=buffer_feature_id,
        buffer_policy_version=buffer_policy_version,
        buffer=buffer,
        buffer_reason_codes=buffer_reason_codes,
        candidate_stop=candidate_stop,
        stop_price=stop_price,
        current_price=current_price,
        evaluated_at=evaluated_at,
        advanced=advanced,
        config_metadata=config_metadata,
        complete=complete,
        reason_codes=reason_codes,
    )


def _validate_result(
    result: TrailingStopResult,
    *,
    require_persistence_context: bool,
) -> _NormalizedResult:
    if result.feature_id != TRAILING_STOP_FEATURE_ID:
        raise ValueError("feature_id must be TRAILING_STOP")
    if result.policy_version != TRAILING_STOP_POLICY_VERSION:
        raise ValueError(
            f"policy_version must be {TRAILING_STOP_POLICY_VERSION}",
        )
    direction = _direction(result.direction)
    prior_count = _advance_count(result.prior_advance_count, "prior_advance_count")
    output_count = _advance_count(result.advance_count, "advance_count")
    if result.stage not in TRAILING_STOP_STAGES:
        raise ValueError(f"stage must be one of {TRAILING_STOP_STAGES}")
    if result.stage != _stage_for(output_count):
        raise ValueError("stage does not match advance_count")
    if not isinstance(result.advanced, bool):
        raise TypeError("advanced must be a bool")
    if output_count != prior_count + (1 if result.advanced else 0):
        raise ValueError("advance_count does not match advanced state")
    if not isinstance(result.complete, bool):
        raise TypeError("complete must be a bool")
    if not isinstance(result.structure_already_used, bool):
        raise TypeError("structure_already_used must be a bool")

    previous_stop = _positive_decimal(result.previous_stop, "previous_stop")
    stop_price = _positive_decimal(result.stop_price, "stop_price")
    structure_price = _optional_positive_decimal(
        result.structure_price,
        "structure_price",
    )
    buffer = _optional_non_negative_decimal(result.buffer, "buffer")
    candidate = _optional_decimal(result.candidate_stop, "candidate_stop")
    current = _optional_positive_decimal(result.current_price, "current_price")
    structure_reasons = _reason_codes(result.structure_reason_codes)
    buffer_reasons = _reason_codes(result.buffer_reason_codes)
    reasons = _reason_codes(result.reason_codes)
    if len(reasons) != 1 or reasons[0] not in TRAILING_STOP_REASON_CODES:
        raise ValueError("reason_codes must contain one declared trailing reason")
    metadata = (
        _validate_config_metadata(result.config_metadata)
        if require_persistence_context
        else _metadata(result.config_metadata)
    )
    evaluated_at = (
        require_utc_datetime(result.evaluated_at, "evaluated_at")
        if result.evaluated_at is not None
        else None
    )
    if require_persistence_context and evaluated_at is None:
        raise ValueError("persisted trailing stop requires evaluated_at")

    structure_fields = (
        result.structure_id,
        result.structure_source_feature_id,
        result.structure_type,
        structure_price,
        result.structure_level_timestamp,
        result.structure_detected_at,
    )
    if structure_price is None:
        if any(value is not None for value in structure_fields):
            raise ValueError("absent structure must not contain structure provenance")
        if result.structure_already_used:
            raise ValueError("absent structure cannot already be used")
    else:
        if require_persistence_context and any(value is None for value in structure_fields):
            raise ValueError("persisted structure requires complete provenance")
        if result.structure_id is not None:
            _required_string(result.structure_id, "structure_id")
        if result.structure_source_feature_id is not None:
            _required_string(
                result.structure_source_feature_id,
                "structure_source_feature_id",
            )
        if result.structure_type is not None:
            _structure_type(result.structure_type, direction=direction)
        level_timestamp = (
            require_utc_datetime(
                result.structure_level_timestamp,
                "structure_level_timestamp",
            )
            if result.structure_level_timestamp is not None
            else None
        )
        detected_at = (
            require_utc_datetime(result.structure_detected_at, "structure_detected_at")
            if result.structure_detected_at is not None
            else None
        )
        if level_timestamp is not None and detected_at is not None:
            if detected_at < level_timestamp:
                raise ValueError("structure_detected_at must be >= level timestamp")
            if evaluated_at is not None and detected_at > evaluated_at:
                raise ValueError("structure must be available by evaluated_at")

    _optional_source_identity(
        result.buffer_feature_id,
        result.buffer_policy_version,
        "buffer",
    )
    buffer_identity = (result.buffer_feature_id, result.buffer_policy_version)
    supported_buffer_identities = (
        (None, None),
        (DIRECT_BUFFER_FEATURE_ID, DIRECT_BUFFER_POLICY_VERSION),
        (VOLATILITY_BUFFER_FEATURE_ID, VOLATILITY_BUFFER_POLICY_VERSION),
    )
    if buffer_identity not in supported_buffer_identities:
        raise ValueError("buffer source identity is not supported")
    if buffer is not None and result.buffer_feature_id is None:
        raise ValueError("a numeric buffer requires source provenance")

    expected_reason: str
    expected_candidate: Decimal | None = None
    expected_stop = previous_stop
    expected_advanced = False
    expected_complete = True
    if structure_price is None:
        expected_reason = "TRAILING_STOP_NO_NEW_STRUCTURE"
    elif result.structure_already_used:
        expected_candidate = (
            None if buffer is None else _candidate(direction, structure_price, buffer)
        )
        expected_reason = "TRAILING_STOP_STRUCTURE_ALREADY_USED"
    elif buffer is None:
        expected_reason = "TRAILING_STOP_BUFFER_INCOMPLETE"
        expected_complete = False
    else:
        expected_candidate = _candidate(direction, structure_price, buffer)
        if decision_less_equal(expected_candidate, 0):
            expected_reason = "TRAILING_STOP_CANDIDATE_NON_POSITIVE"
        elif current is not None and _beyond_price(
            direction=direction,
            candidate=expected_candidate,
            current_price=current,
        ):
            expected_reason = "TRAILING_STOP_CANDIDATE_BEYOND_PRICE"
        elif _improves(
            direction=direction,
            candidate=expected_candidate,
            previous_stop=previous_stop,
        ):
            expected_reason = "TRAILING_STOP_ADVANCED"
            expected_stop = expected_candidate
            expected_advanced = True
        else:
            expected_reason = "TRAILING_STOP_HELD"

    if _moves_backwards(
        direction=direction,
        previous_stop=previous_stop,
        stop_price=stop_price,
    ):
        raise ValueError(
            "a long stop may never move lower and a short stop may never move higher",
        )
    if candidate != expected_candidate:
        raise ValueError("candidate_stop does not match structure and buffer")
    if not decision_equal(stop_price, expected_stop):
        raise ValueError("stop_price does not match trailing ratchet")
    if result.advanced != expected_advanced:
        raise ValueError("advanced does not match trailing ratchet")
    if result.complete != expected_complete:
        raise ValueError("complete does not match trailing inputs")
    if reasons != (expected_reason,):
        raise ValueError("reason_codes do not match trailing result")
    return _NormalizedResult(
        direction=direction,
        previous_stop=previous_stop,
        structure_price=structure_price,
        structure_reason_codes=structure_reasons,
        buffer=buffer,
        buffer_reason_codes=buffer_reasons,
        candidate_stop=candidate,
        stop_price=stop_price,
        current_price=current,
        config_metadata=metadata,
        reason_codes=reasons,
    )


def _stage_for(advance_count: int) -> str:
    if advance_count <= 0:
        return THESIS_STOP
    if advance_count == 1:
        return CONFIRMATION_STOP
    return PROFIT_PROTECTION_TRAIL


def _candidate(direction: str, structure: Decimal, buffer: Decimal) -> Decimal:
    return structure - buffer if direction == LONG_DIRECTION else structure + buffer


def _improves(*, direction: str, candidate: Decimal, previous_stop: Decimal) -> bool:
    if direction == LONG_DIRECTION:
        return decision_greater(candidate, previous_stop)
    return decision_less(candidate, previous_stop)


def _moves_backwards(
    *,
    direction: str,
    previous_stop: Decimal,
    stop_price: Decimal,
) -> bool:
    if direction == LONG_DIRECTION:
        return decision_less(stop_price, previous_stop)
    return decision_greater(stop_price, previous_stop)


def _beyond_price(
    *,
    direction: str,
    candidate: Decimal,
    current_price: Decimal,
) -> bool:
    if direction == LONG_DIRECTION:
        return decision_greater_equal(candidate, current_price)
    return decision_less_equal(candidate, current_price)


def _direction(value: Any) -> str:
    if value not in INVALIDATION_DIRECTIONS:
        raise ValueError(f"direction must be one of {INVALIDATION_DIRECTIONS}")
    return value


def _structure_type(value: Any, *, direction: str) -> str:
    if value not in TRAILING_STRUCTURE_TYPES:
        raise ValueError(f"structure_type must be one of {TRAILING_STRUCTURE_TYPES}")
    expected = HIGHER_LOW if direction == LONG_DIRECTION else LOWER_HIGH
    if value != expected:
        raise ValueError(f"{direction} trailing structure must be {expected}")
    return value


def _advance_count(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must not be negative")
    return value


def _record_int(source: Mapping[str, Any], name: str) -> int:
    value = source.get(name)
    return _advance_count(value, name)


def _record_bool(source: Mapping[str, Any], name: str) -> bool:
    value = source.get(name)
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a bool")
    return value


def _decimal(value: Any, name: str) -> Decimal:
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be numeric")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError(f"{name} must be numeric") from error
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    return result


def _positive_decimal(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if decision_less_equal(result, 0):
        raise ValueError(f"{name} must be positive")
    return result


def _non_negative_decimal(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


def _optional_decimal(value: Any | None, name: str) -> Decimal | None:
    return None if value is None else _decimal(value, name)


def _optional_positive_decimal(value: Any | None, name: str) -> Decimal | None:
    return None if value is None else _positive_decimal(value, name)


def _optional_non_negative_decimal(value: Any | None, name: str) -> Decimal | None:
    return None if value is None else _non_negative_decimal(value, name)


def _required_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _optional_string(value: Any | None, name: str) -> str | None:
    return None if value is None else _required_string(value, name)


def _optional_source_identity(
    feature_id: Any | None,
    policy_version: Any | None,
    name: str,
) -> None:
    if (feature_id is None) != (policy_version is None):
        raise ValueError(f"{name} feature and policy identity must be paired")
    if feature_id is not None:
        _required_string(feature_id, f"{name}_feature_id")
        _required_string(policy_version, f"{name}_policy_version")


def _reason_codes(values: Any) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError("reason_codes must be an iterable of strings")
    result = tuple(values)
    if any(not isinstance(code, str) or not code.strip() for code in result):
        raise ValueError("reason codes must be non-empty strings")
    if len(result) != len(set(result)):
        raise ValueError("reason codes must not contain duplicates")
    return result


def _metadata(value: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise TypeError("config_metadata must be a mapping")
    result: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("config_metadata keys must be non-empty strings")
        if not isinstance(item, str) or not item.strip():
            raise ValueError("config_metadata values must be non-empty strings")
        result[key] = item
    return result


def _validate_config_metadata(value: Mapping[str, Any]) -> dict[str, str]:
    result = _metadata(value)
    missing = [key for key in _REQUIRED_CONFIG_METADATA_KEYS if key not in result]
    if missing:
        raise ValueError(f"config_metadata missing {missing}")
    return result


def _optional_utc(value: Any | None, name: str) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError(f"{name} must be an ISO datetime") from error
    return require_utc_datetime(value, name)


def _optional(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _optional_time(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


__all__ = [
    "CONFIRMATION_STOP",
    "DIRECT_BUFFER_FEATURE_ID",
    "DIRECT_BUFFER_POLICY_VERSION",
    "HIGHER_LOW",
    "LOWER_HIGH",
    "PROFIT_PROTECTION_TRAIL",
    "THESIS_STOP",
    "TRAILING_STOP_FEATURE_ID",
    "TRAILING_STOP_POLICY_VERSION",
    "TRAILING_STOP_REASON_CODES",
    "TRAILING_STOP_STAGES",
    "TRAILING_STRUCTURE_TYPES",
    "ConfirmedTrailingStructure",
    "TrailingStopResult",
    "apply_trailing_stop",
    "calculate_trailing_stop",
    "stop_advance_count",
    "trail_stop_for_position",
    "trailing_stop_from_record",
    "used_trailing_structure_ids",
]
