"""Deterministic full-exit policy for open positions (BTC-158).

Five independent conditions can request a full exit: a touched structural
stop, Hold Score collapse, regime invalidation, an explicit data-risk exit,
or a manual research override. The module emits a decision and never simulates
fills. BTC-150 owns lifecycle mutation and the paper-trading epic owns execution.

The rulebook defines one numerical threshold here: Hold Score strictly below
``hold_thresholds.exit_below``. Regime invalidation and data-risk exit remain
explicit booleans supplied by their owning policies; this module does not
invent thresholds or treat ordinary DATA_QUALITY_FAIL as forced liquidation.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import numpy as np

from btc_predictor.config import StrategyConfig
from btc_predictor.data import require_utc_datetime
from btc_predictor.features.hold import HOLD_SCORE_FEATURE_ID, HoldScoreResult
from btc_predictor.portfolio.state_machine import PositionLifecycle
from btc_predictor.quant.comparisons import (
    decision_greater_equal,
    decision_less,
    decision_less_equal,
)
from btc_predictor.risk.invalidation import (
    INVALIDATION_DIRECTIONS,
    LONG_DIRECTION,
)


EXIT_SIGNAL_FEATURE_ID = "EXIT_SIGNAL"
EXIT_RULES_POLICY_VERSION = "EXIT_RULES_V1"
EXIT_RULES_PARAMETER_STATUS = "PROVISIONAL_PENDING_BTC_185"
EXIT_ACTION = "EXIT"
EXIT_EFFECTS = ("FULL_EXIT",)

STRUCTURAL_STOP = "STRUCTURAL_STOP"
HOLD_SCORE_COLLAPSE = "HOLD_SCORE_COLLAPSE"
REGIME_INVALIDATION = "REGIME_INVALIDATION"
DATA_RISK = "DATA_RISK"
MANUAL_RESEARCH_OVERRIDE = "MANUAL_RESEARCH_OVERRIDE"
EXIT_REASON_IDS = (
    STRUCTURAL_STOP,
    HOLD_SCORE_COLLAPSE,
    REGIME_INVALIDATION,
    DATA_RISK,
    MANUAL_RESEARCH_OVERRIDE,
)

EXIT_RULE_INPUT_IDS = (
    "position_open",
    "direction",
    "standing_stop",
    "current_price",
    "hold_score",
    "regime_invalidated",
    "data_risk_exit_required",
    "manual_research_override",
)
EXIT_RULE_REASON_CODES = (
    "EXIT_INPUT_MISSING",
    "EXIT_NO_OPEN_POSITION",
    *EXIT_REASON_IDS,
    "EXIT_NOT_TRIGGERED",
)
_BOOLEAN_INPUT_IDS = (
    "position_open",
    "regime_invalidated",
    "data_risk_exit_required",
    "manual_research_override",
)
_REQUIRED_CONFIG_METADATA_KEYS = (
    "config_version",
    "strategy_version",
    "parameter_set_id",
)
_CANONICAL_EVIDENCE_SOURCES = ("lifecycle", "hold_score")


@dataclass(frozen=True)
class ExitRuleInput:
    """Point-in-time evidence used by the full-exit policy."""

    position_open: bool | None
    direction: str | None
    standing_stop: Decimal | None
    current_price: Decimal | None
    hold_score: Decimal | None
    regime_invalidated: bool | None
    data_risk_exit_required: bool | None
    manual_research_override: bool | None
    manual_override_reason: str | None = None
    source_reason_codes: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    def as_record(self) -> dict[str, Any]:
        values = _validate_inputs(self)
        return {
            "position_open": values["position_open"],
            "direction": values["direction"],
            "standing_stop": _optional_decimal_record(values["standing_stop"]),
            "current_price": _optional_decimal_record(values["current_price"]),
            "hold_score": _optional_decimal_record(values["hold_score"]),
            "regime_invalidated": values["regime_invalidated"],
            "data_risk_exit_required": values["data_risk_exit_required"],
            "manual_research_override": values["manual_research_override"],
            "manual_override_reason": values["manual_override_reason"],
            "source_reason_codes": {
                source: list(codes)
                for source, codes in _normalize_source_reason_codes(
                    self.source_reason_codes,
                ).items()
            },
        }


@dataclass(frozen=True)
class ExitSignalResult:
    feature_id: str
    policy_version: str
    parameter_status: str
    inputs: ExitRuleInput
    exit_below: Decimal
    evaluated_at: datetime
    signal: bool
    action: str | None
    effects: tuple[str, ...]
    exit_reasons: tuple[str, ...]
    missing_inputs: tuple[str, ...]
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...]

    @property
    def full_exit(self) -> bool:
        return self.signal

    def as_record(self) -> dict[str, Any]:
        """Return a self-validating record sufficient for exact replay."""

        if self.feature_id != EXIT_SIGNAL_FEATURE_ID:
            raise ValueError("feature_id must be EXIT_SIGNAL")
        if self.policy_version != EXIT_RULES_POLICY_VERSION:
            raise ValueError(f"policy_version must be {EXIT_RULES_POLICY_VERSION}")
        if self.parameter_status != EXIT_RULES_PARAMETER_STATUS:
            raise ValueError(
                f"parameter_status must be {EXIT_RULES_PARAMETER_STATUS}",
            )
        threshold = _score(self.exit_below, "exit_below")
        evaluated_at = require_utc_datetime(self.evaluated_at, "evaluated_at")
        metadata = _validate_config_metadata(self.config_metadata)
        expected = _evaluate(self.inputs, exit_below=threshold)
        if self.signal != expected.signal:
            raise ValueError("signal does not match exit-rule inputs")
        if self.action != expected.action:
            raise ValueError("action does not match exit-rule inputs")
        if self.effects != expected.effects:
            raise ValueError("effects do not match exit-rule inputs")
        if self.exit_reasons != expected.exit_reasons:
            raise ValueError("exit_reasons do not match exit-rule inputs")
        if self.missing_inputs != expected.missing_inputs:
            raise ValueError("missing_inputs do not match exit-rule inputs")
        if self.complete != expected.complete:
            raise ValueError("complete does not match exit-rule inputs")
        if self.reason_codes != expected.reason_codes:
            raise ValueError("reason_codes do not match exit-rule inputs")
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "parameter_status": self.parameter_status,
            "inputs": self.inputs.as_record(),
            "exit_below": str(threshold),
            "evaluated_at": evaluated_at.isoformat(),
            "signal": self.signal,
            "action": self.action,
            "full_exit": self.full_exit,
            "effects": list(self.effects),
            "exit_reasons": list(self.exit_reasons),
            "missing_inputs": list(self.missing_inputs),
            "config_metadata": metadata,
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class _ExitDecision:
    signal: bool
    action: str | None
    effects: tuple[str, ...]
    exit_reasons: tuple[str, ...]
    missing_inputs: tuple[str, ...]
    complete: bool
    reason_codes: tuple[str, ...]


def evaluate_exit_rules(
    inputs: ExitRuleInput,
    *,
    strategy_config: StrategyConfig,
    evaluated_at: datetime,
) -> ExitSignalResult:
    """Evaluate all independent exit conditions in canonical reason order."""

    if not isinstance(inputs, ExitRuleInput):
        raise TypeError("inputs must be an ExitRuleInput")
    if not isinstance(strategy_config, StrategyConfig):
        raise TypeError("strategy_config must be a StrategyConfig")
    signal_time = require_utc_datetime(evaluated_at, "evaluated_at")
    threshold = _score(strategy_config.hold_thresholds.exit_below, "exit_below")
    decision = _evaluate(inputs, exit_below=threshold)
    result = ExitSignalResult(
        feature_id=EXIT_SIGNAL_FEATURE_ID,
        policy_version=EXIT_RULES_POLICY_VERSION,
        parameter_status=EXIT_RULES_PARAMETER_STATUS,
        inputs=inputs,
        exit_below=threshold,
        evaluated_at=signal_time,
        signal=decision.signal,
        action=decision.action,
        effects=decision.effects,
        exit_reasons=decision.exit_reasons,
        missing_inputs=decision.missing_inputs,
        config_metadata=_validate_config_metadata(strategy_config.run_metadata()),
        complete=decision.complete,
        reason_codes=decision.reason_codes,
    )
    result.as_record()
    return result


def exit_rules_for_position(
    *,
    lifecycle: PositionLifecycle,
    current_price: Any | None,
    hold_score: HoldScoreResult,
    regime_invalidated: bool | None,
    data_risk_exit_required: bool | None,
    manual_research_override: bool | None,
    manual_override_reason: str | None,
    strategy_config: StrategyConfig,
    evaluated_at: datetime,
    source_reason_codes: Mapping[str, tuple[str, ...]] | None = None,
) -> ExitSignalResult:
    """Compose an exit decision from authoritative lifecycle and score state."""

    if not isinstance(lifecycle, PositionLifecycle):
        raise TypeError("lifecycle must be a PositionLifecycle")
    if not isinstance(hold_score, HoldScoreResult):
        raise TypeError("hold_score must be a HoldScoreResult")
    if not isinstance(strategy_config, StrategyConfig):
        raise TypeError("strategy_config must be a StrategyConfig")
    hold_score.as_record()
    if hold_score.feature_id != HOLD_SCORE_FEATURE_ID:
        raise ValueError("hold_score feature_id must be HOLD_SCORE")

    signal_time = require_utc_datetime(evaluated_at, "evaluated_at")
    if lifecycle.last_event_at is not None and signal_time < lifecycle.last_event_at:
        raise ValueError("evaluated_at must not precede the lifecycle watermark")
    metadata = _validate_config_metadata(strategy_config.run_metadata())
    for source, source_metadata in (
        ("lifecycle", lifecycle.config_metadata),
        ("hold_score", hold_score.config_metadata),
    ):
        if dict(source_metadata) != metadata:
            raise ValueError(f"{source} config_metadata does not match strategy_config")

    extra_evidence = _normalize_source_reason_codes(source_reason_codes or {})
    conflicts = set(extra_evidence).intersection(_CANONICAL_EVIDENCE_SOURCES)
    if conflicts:
        raise ValueError(
            f"source_reason_codes cannot replace canonical sources {sorted(conflicts)}",
        )
    evidence = {
        "lifecycle": tuple(lifecycle.reason_codes),
        "hold_score": tuple(hold_score.reason_codes),
        **extra_evidence,
    }
    return evaluate_exit_rules(
        ExitRuleInput(
            position_open=lifecycle.is_open,
            direction=lifecycle.direction,
            standing_stop=lifecycle.stop_price,
            current_price=current_price,
            hold_score=hold_score.score if hold_score.complete else None,
            regime_invalidated=regime_invalidated,
            data_risk_exit_required=data_risk_exit_required,
            manual_research_override=manual_research_override,
            manual_override_reason=manual_override_reason,
            source_reason_codes=evidence,
        ),
        strategy_config=strategy_config,
        evaluated_at=signal_time,
    )


def structural_stop_triggered(
    *,
    direction: str,
    standing_stop: Any,
    current_price: Any,
) -> bool:
    """Return whether the observed price touched or crossed the standing stop.

    The caller owns observation semantics. A live engine may supply a traded
    price; a bar backtester should supply the direction-appropriate intrabar
    extreme. Fill price, gaps, slippage, and ordering remain execution concerns.
    """

    if direction not in INVALIDATION_DIRECTIONS:
        raise ValueError(f"direction must be one of {INVALIDATION_DIRECTIONS}")
    stop = _positive_decimal(standing_stop, "standing_stop")
    price = _positive_decimal(current_price, "current_price")
    if direction == LONG_DIRECTION:
        return decision_less_equal(price, stop)
    return decision_greater_equal(price, stop)


def exit_signal_from_record(record: Mapping[str, Any]) -> ExitSignalResult:
    """Reconstruct and verify a persisted exit signal exactly."""

    if not isinstance(record, Mapping):
        raise TypeError("record must be a mapping")
    source = dict(record)
    raw_inputs = source.get("inputs")
    if not isinstance(raw_inputs, Mapping):
        raise ValueError("inputs must be a mapping")
    raw_reasons = raw_inputs.get("source_reason_codes", {})
    if not isinstance(raw_reasons, Mapping):
        raise ValueError("source_reason_codes must be a mapping")
    inputs = ExitRuleInput(
        position_open=_optional_bool(raw_inputs.get("position_open"), "position_open"),
        direction=_optional_string(raw_inputs.get("direction"), "direction"),
        standing_stop=_optional_positive_decimal(
            raw_inputs.get("standing_stop"),
            "standing_stop",
        ),
        current_price=_optional_positive_decimal(
            raw_inputs.get("current_price"),
            "current_price",
        ),
        hold_score=_optional_score(raw_inputs.get("hold_score"), "hold_score"),
        regime_invalidated=_optional_bool(
            raw_inputs.get("regime_invalidated"),
            "regime_invalidated",
        ),
        data_risk_exit_required=_optional_bool(
            raw_inputs.get("data_risk_exit_required"),
            "data_risk_exit_required",
        ),
        manual_research_override=_optional_bool(
            raw_inputs.get("manual_research_override"),
            "manual_research_override",
        ),
        manual_override_reason=_optional_string(
            raw_inputs.get("manual_override_reason"),
            "manual_override_reason",
        ),
        source_reason_codes={
            source_id: tuple(codes) for source_id, codes in raw_reasons.items()
        },
    )
    result = ExitSignalResult(
        feature_id=_required_string(source.get("feature_id"), "feature_id"),
        policy_version=_required_string(
            source.get("policy_version"),
            "policy_version",
        ),
        parameter_status=_required_string(
            source.get("parameter_status"),
            "parameter_status",
        ),
        inputs=inputs,
        exit_below=_score(source.get("exit_below"), "exit_below"),
        evaluated_at=_parse_utc(source.get("evaluated_at"), "evaluated_at"),
        signal=_required_bool(source.get("signal"), "signal"),
        action=_optional_string(source.get("action"), "action"),
        effects=_string_tuple(source.get("effects"), "effects"),
        exit_reasons=_string_tuple(source.get("exit_reasons"), "exit_reasons"),
        missing_inputs=_string_tuple(source.get("missing_inputs"), "missing_inputs"),
        config_metadata=_validate_config_metadata(
            source.get("config_metadata", {}),
        ),
        complete=_required_bool(source.get("complete"), "complete"),
        reason_codes=_string_tuple(source.get("reason_codes"), "reason_codes"),
    )
    if source.get("full_exit") != result.full_exit:
        raise ValueError("full_exit does not match signal")
    if result.as_record() != source:
        raise ValueError("record does not match reconstructed exit signal")
    return result


def _evaluate(inputs: ExitRuleInput, *, exit_below: Decimal) -> _ExitDecision:
    values = _validate_inputs(inputs)
    missing_inputs = tuple(
        input_id for input_id in EXIT_RULE_INPUT_IDS if values[input_id] is None
    )
    exit_reasons: list[str] = []
    if (
        values["direction"] is not None
        and values["standing_stop"] is not None
        and values["current_price"] is not None
        and structural_stop_triggered(
            direction=values["direction"],
            standing_stop=values["standing_stop"],
            current_price=values["current_price"],
        )
    ):
        exit_reasons.append(STRUCTURAL_STOP)
    if values["hold_score"] is not None and decision_less(
        values["hold_score"],
        exit_below,
    ):
        exit_reasons.append(HOLD_SCORE_COLLAPSE)
    if values["regime_invalidated"] is True:
        exit_reasons.append(REGIME_INVALIDATION)
    if values["data_risk_exit_required"] is True:
        exit_reasons.append(DATA_RISK)
    if values["manual_research_override"] is True:
        exit_reasons.append(MANUAL_RESEARCH_OVERRIDE)

    position_open = values["position_open"]
    signal = position_open is True and bool(exit_reasons)
    reasons: list[str] = []
    if missing_inputs:
        reasons.append("EXIT_INPUT_MISSING")
    if position_open is False:
        reasons.append("EXIT_NO_OPEN_POSITION")
        exit_reasons = []
    elif signal:
        reasons.extend(exit_reasons)
    elif position_open is True and not missing_inputs:
        reasons.append("EXIT_NOT_TRIGGERED")

    return _ExitDecision(
        signal=signal,
        action=EXIT_ACTION if signal else None,
        effects=EXIT_EFFECTS if signal else (),
        exit_reasons=tuple(exit_reasons) if signal else (),
        missing_inputs=missing_inputs,
        complete=not missing_inputs,
        reason_codes=tuple(reasons),
    )


def _validate_inputs(inputs: ExitRuleInput) -> dict[str, Any]:
    if not isinstance(inputs, ExitRuleInput):
        raise TypeError("inputs must be an ExitRuleInput")
    values: dict[str, Any] = {
        "position_open": inputs.position_open,
        "direction": inputs.direction,
        "standing_stop": inputs.standing_stop,
        "current_price": inputs.current_price,
        "hold_score": inputs.hold_score,
        "regime_invalidated": inputs.regime_invalidated,
        "data_risk_exit_required": inputs.data_risk_exit_required,
        "manual_research_override": inputs.manual_research_override,
    }
    for input_id in _BOOLEAN_INPUT_IDS:
        value = values[input_id]
        if value is not None and not isinstance(value, (bool, np.bool_)):
            raise TypeError(f"{input_id} must be a bool or None")
        if isinstance(value, np.bool_):
            values[input_id] = bool(value)
    direction = values["direction"]
    if direction is not None and direction not in INVALIDATION_DIRECTIONS:
        raise ValueError(f"direction must be one of {INVALIDATION_DIRECTIONS} or None")
    for input_id in ("standing_stop", "current_price"):
        value = values[input_id]
        if value is not None:
            values[input_id] = _positive_decimal(value, input_id)
    if values["hold_score"] is not None:
        values["hold_score"] = _score(values["hold_score"], "hold_score")

    manual_reason = _manual_reason(inputs.manual_override_reason)
    if values["manual_research_override"] is True and manual_reason is None:
        raise ValueError("manual override requires manual_override_reason")
    if values["manual_research_override"] is not True and manual_reason is not None:
        raise ValueError(
            "manual_override_reason requires manual_research_override=true",
        )
    values["manual_override_reason"] = manual_reason
    _normalize_source_reason_codes(inputs.source_reason_codes)
    return values


def _normalize_source_reason_codes(
    values: Mapping[str, tuple[str, ...]],
) -> dict[str, tuple[str, ...]]:
    if not isinstance(values, Mapping):
        raise TypeError("source_reason_codes must be a mapping")
    normalized: dict[str, tuple[str, ...]] = {}
    for source, codes in values.items():
        if not isinstance(source, str) or not source.strip():
            raise ValueError("source reason-code names must be non-empty strings")
        if isinstance(codes, (str, bytes)):
            raise TypeError("source reason codes must be iterables of strings")
        normalized_codes = tuple(codes)
        if any(not isinstance(code, str) or not code.strip() for code in normalized_codes):
            raise ValueError("source reason codes must be non-empty strings")
        normalized[source] = tuple(dict.fromkeys(normalized_codes))
    return normalized


def _validate_config_metadata(metadata: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(metadata, Mapping):
        raise TypeError("config_metadata must be a mapping")
    normalized = dict(metadata)
    missing = [key for key in _REQUIRED_CONFIG_METADATA_KEYS if key not in normalized]
    if missing:
        raise ValueError(f"config_metadata missing {missing}")
    for key in _REQUIRED_CONFIG_METADATA_KEYS:
        value = normalized[key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"config_metadata.{key} must be a non-empty string")
    return normalized


def _manual_reason(value: Any | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("manual_override_reason must be a non-empty string or None")
    return value.strip()


def _score(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if result < 0 or result > 100:
        raise ValueError(f"{name} must be between 0 and 100")
    return result


def _positive_decimal(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if decision_less_equal(result, 0):
        raise ValueError(f"{name} must be positive")
    return result


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


def _optional_positive_decimal(value: Any | None, name: str) -> Decimal | None:
    return None if value is None else _positive_decimal(value, name)


def _optional_score(value: Any | None, name: str) -> Decimal | None:
    return None if value is None else _score(value, name)


def _optional_decimal_record(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _required_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _optional_string(value: Any | None, name: str) -> str | None:
    return None if value is None else _required_string(value, name)


def _required_bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a bool")
    return value


def _optional_bool(value: Any | None, name: str) -> bool | None:
    if value is None:
        return None
    return _required_bool(value, name)


def _string_tuple(value: Any, name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        raise TypeError(f"{name} must be an iterable of strings")
    try:
        result = tuple(value)
    except TypeError as error:
        raise TypeError(f"{name} must be an iterable of strings") from error
    if any(not isinstance(item, str) or not item.strip() for item in result):
        raise ValueError(f"{name} must contain non-empty strings")
    if len(result) != len(set(result)):
        raise ValueError(f"{name} must not contain duplicates")
    return result


def _parse_utc(value: Any, name: str) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError(f"{name} must be an ISO datetime") from error
    return require_utc_datetime(value, name)


__all__ = [
    "DATA_RISK",
    "EXIT_ACTION",
    "EXIT_EFFECTS",
    "EXIT_REASON_IDS",
    "EXIT_RULE_INPUT_IDS",
    "EXIT_RULE_REASON_CODES",
    "EXIT_RULES_PARAMETER_STATUS",
    "EXIT_RULES_POLICY_VERSION",
    "EXIT_SIGNAL_FEATURE_ID",
    "HOLD_SCORE_COLLAPSE",
    "MANUAL_RESEARCH_OVERRIDE",
    "REGIME_INVALIDATION",
    "STRUCTURAL_STOP",
    "ExitRuleInput",
    "ExitSignalResult",
    "evaluate_exit_rules",
    "exit_rules_for_position",
    "exit_signal_from_record",
    "structural_stop_triggered",
]
