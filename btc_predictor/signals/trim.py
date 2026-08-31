"""Deterministic partial-reduction policy (BTC-157).

The policy emits a signal, not an execution quantity. BTC-164 owns simulated
fill sizing; BTC-150 already owns the invariant that a recorded TRIM must be
strictly smaller than the open position. Keeping those concerns separate means
this module can never turn a trim into an accidental full exit.

Phase 1 flow deterioration is deliberately simple and reproducible: the latest
persisted Flow Score is below the prior decision's Flow Score under the shared
decision-comparison tolerance. No unconfigured lookback or decline threshold is
invented here. BTC-185 may replace that provisional definition after research.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

import numpy as np

from btc_predictor.config import StrategyConfig
from btc_predictor.features.flow import FLOW_SCORE_FEATURE_ID, FlowScoreResult
from btc_predictor.features.hold import HOLD_SCORE_FEATURE_ID, HoldScoreResult
from btc_predictor.features.positioning import (
    CROWDING_FLAG_FEATURE_ID,
    CrowdingFlagResult,
)
from btc_predictor.features.volatility import (
    EUPHORIA_FLAG_FEATURE_ID,
    EuphoriaFlagResult,
)
from btc_predictor.portfolio.state_machine import PositionLifecycle
from btc_predictor.quant.comparisons import (
    decision_greater_equal,
    decision_less,
)


TRIM_SIGNAL_FEATURE_ID = "TRIM_SIGNAL"
TRIM_RULES_POLICY_VERSION = "TRIM_RULES_V1"
TRIM_RULES_PARAMETER_STATUS = "PROVISIONAL_PENDING_BTC_185"
TRIM_ACTION = "TRIM"
TRIM_EFFECTS = ("PARTIAL_REDUCTION",)
TRIM_RULE_INPUT_IDS = (
    "position_open",
    "hold_score",
    "euphoria_active",
    "crowding_active",
    "current_flow_score",
    "prior_flow_score",
)
TRIM_REASON_CODES = (
    "TRIM_INPUT_MISSING",
    "TRIM_NO_OPEN_POSITION",
    "TRIM_SUPPRESSED_EXIT_BAND",
    "TRIM_HOLD_SCORE_BAND",
    "TRIM_EUPHORIA_ACTIVE",
    "TRIM_CROWDING_ACTIVE",
    "TRIM_FLOW_DETERIORATION",
    "TRIM_NOT_TRIGGERED",
)
_BOOLEAN_INPUT_IDS = (
    "position_open",
    "euphoria_active",
    "crowding_active",
)
_SCORE_INPUT_IDS = (
    "hold_score",
    "current_flow_score",
    "prior_flow_score",
)
_REQUIRED_CONFIG_METADATA_KEYS = (
    "config_version",
    "strategy_version",
    "parameter_set_id",
)


@dataclass(frozen=True)
class TrimRuleInput:
    """Point-in-time states used to decide whether to reduce partially."""

    position_open: bool | None
    hold_score: Decimal | None
    euphoria_active: bool | None
    crowding_active: bool | None
    current_flow_score: Decimal | None
    prior_flow_score: Decimal | None
    source_reason_codes: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    def as_record(self) -> dict[str, Any]:
        values = _validate_inputs(self)
        return {
            **{
                input_id: (
                    str(values[input_id])
                    if isinstance(values[input_id], Decimal)
                    else values[input_id]
                )
                for input_id in TRIM_RULE_INPUT_IDS
            },
            "source_reason_codes": {
                source: list(codes)
                for source, codes in _normalize_source_reason_codes(
                    self.source_reason_codes,
                ).items()
            },
        }


@dataclass(frozen=True)
class TrimSignalResult:
    feature_id: str
    policy_version: str
    parameter_status: str
    inputs: TrimRuleInput
    trim_minimum: Decimal
    defensive_minimum: Decimal
    exit_below: Decimal
    signal: bool
    action: str | None
    effects: tuple[str, ...]
    exit_precedence: bool
    missing_inputs: tuple[str, ...]
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...]

    @property
    def partial_reduction(self) -> bool:
        return self.signal

    def as_record(self) -> dict[str, Any]:
        """Return a self-validating, replayable policy record."""

        if self.feature_id != TRIM_SIGNAL_FEATURE_ID:
            raise ValueError("feature_id must be TRIM_SIGNAL")
        if self.policy_version != TRIM_RULES_POLICY_VERSION:
            raise ValueError(
                f"policy_version must be {TRIM_RULES_POLICY_VERSION}",
            )
        if self.parameter_status != TRIM_RULES_PARAMETER_STATUS:
            raise ValueError(
                f"parameter_status must be {TRIM_RULES_PARAMETER_STATUS}",
            )
        trim_minimum, defensive_minimum, exit_below = _validate_thresholds(
            trim_minimum=self.trim_minimum,
            defensive_minimum=self.defensive_minimum,
            exit_below=self.exit_below,
        )
        metadata = _validate_config_metadata(self.config_metadata)
        expected = _evaluate(
            self.inputs,
            trim_minimum=trim_minimum,
            defensive_minimum=defensive_minimum,
            exit_below=exit_below,
        )
        if self.signal != expected.signal:
            raise ValueError("signal does not match trim-rule inputs")
        if self.action != expected.action:
            raise ValueError("action does not match trim-rule inputs")
        if self.effects != expected.effects:
            raise ValueError("effects do not match trim-rule inputs")
        if self.exit_precedence != expected.exit_precedence:
            raise ValueError("exit_precedence does not match Hold Score")
        if self.missing_inputs != expected.missing_inputs:
            raise ValueError("missing_inputs do not match trim-rule inputs")
        if self.complete != expected.complete:
            raise ValueError("complete does not match trim-rule inputs")
        if self.reason_codes != expected.reason_codes:
            raise ValueError("reason_codes do not match trim-rule inputs")

        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "parameter_status": self.parameter_status,
            "inputs": self.inputs.as_record(),
            "trim_minimum": str(trim_minimum),
            "defensive_minimum": str(defensive_minimum),
            "exit_below": str(exit_below),
            "signal": self.signal,
            "action": self.action,
            "partial_reduction": self.partial_reduction,
            "effects": list(self.effects),
            "exit_precedence": self.exit_precedence,
            "missing_inputs": list(self.missing_inputs),
            "config_metadata": metadata,
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class _TrimDecision:
    signal: bool
    action: str | None
    effects: tuple[str, ...]
    exit_precedence: bool
    missing_inputs: tuple[str, ...]
    complete: bool
    reason_codes: tuple[str, ...]


def evaluate_trim_rules(
    inputs: TrimRuleInput,
    *,
    strategy_config: StrategyConfig,
) -> TrimSignalResult:
    """Evaluate the Phase 1 trim policy in deterministic reason-code order."""

    if not isinstance(inputs, TrimRuleInput):
        raise TypeError("inputs must be a TrimRuleInput")
    if not isinstance(strategy_config, StrategyConfig):
        raise TypeError("strategy_config must be a StrategyConfig")
    thresholds = strategy_config.hold_thresholds
    trim_minimum, defensive_minimum, exit_below = _validate_thresholds(
        trim_minimum=thresholds.trim_min,
        defensive_minimum=thresholds.defensive_min,
        exit_below=thresholds.exit_below,
    )
    decision = _evaluate(
        inputs,
        trim_minimum=trim_minimum,
        defensive_minimum=defensive_minimum,
        exit_below=exit_below,
    )
    result = TrimSignalResult(
        feature_id=TRIM_SIGNAL_FEATURE_ID,
        policy_version=TRIM_RULES_POLICY_VERSION,
        parameter_status=TRIM_RULES_PARAMETER_STATUS,
        inputs=inputs,
        trim_minimum=trim_minimum,
        defensive_minimum=defensive_minimum,
        exit_below=exit_below,
        signal=decision.signal,
        action=decision.action,
        effects=decision.effects,
        exit_precedence=decision.exit_precedence,
        missing_inputs=decision.missing_inputs,
        config_metadata=_validate_config_metadata(strategy_config.run_metadata()),
        complete=decision.complete,
        reason_codes=decision.reason_codes,
    )
    result.as_record()
    return result


def trim_rules_from_results(
    *,
    lifecycle: PositionLifecycle,
    hold_score: HoldScoreResult,
    euphoria: EuphoriaFlagResult,
    crowding: CrowdingFlagResult,
    current_flow: FlowScoreResult,
    prior_flow: FlowScoreResult,
    strategy_config: StrategyConfig,
) -> TrimSignalResult:
    """Compose a trim decision from its authoritative upstream results."""

    if not isinstance(lifecycle, PositionLifecycle):
        raise TypeError("lifecycle must be a PositionLifecycle")
    if not isinstance(hold_score, HoldScoreResult):
        raise TypeError("hold_score must be a HoldScoreResult")
    if not isinstance(euphoria, EuphoriaFlagResult):
        raise TypeError("euphoria must be EuphoriaFlagResult")
    if not isinstance(crowding, CrowdingFlagResult):
        raise TypeError("crowding must be a CrowdingFlagResult")
    if not isinstance(current_flow, FlowScoreResult):
        raise TypeError("current_flow must be a FlowScoreResult")
    if not isinstance(prior_flow, FlowScoreResult):
        raise TypeError("prior_flow must be a FlowScoreResult")
    if not isinstance(strategy_config, StrategyConfig):
        raise TypeError("strategy_config must be a StrategyConfig")

    hold_score.as_record()
    euphoria.as_record()
    crowding.as_record()
    current_flow.as_record()
    prior_flow.as_record()
    if hold_score.feature_id != HOLD_SCORE_FEATURE_ID:
        raise ValueError("hold_score feature_id must be HOLD_SCORE")
    if euphoria.feature_id != EUPHORIA_FLAG_FEATURE_ID:
        raise ValueError("euphoria feature_id must be EUPHORIA")
    if crowding.feature_id != CROWDING_FLAG_FEATURE_ID:
        raise ValueError("crowding feature_id must be CROWDING")
    if current_flow.feature_id != FLOW_SCORE_FEATURE_ID:
        raise ValueError("current_flow feature_id must be FLOW_SCORE")
    if prior_flow.feature_id != FLOW_SCORE_FEATURE_ID:
        raise ValueError("prior_flow feature_id must be FLOW_SCORE")

    metadata = _validate_config_metadata(strategy_config.run_metadata())
    for source, source_metadata in (
        ("lifecycle", lifecycle.config_metadata),
        ("hold_score", hold_score.config_metadata),
        ("euphoria", euphoria.config_metadata),
        ("crowding", crowding.config_metadata),
        ("current_flow", current_flow.config_metadata),
        ("prior_flow", prior_flow.config_metadata),
    ):
        if dict(source_metadata) != metadata:
            raise ValueError(f"{source} config_metadata does not match strategy_config")

    evidence = {
        "lifecycle": tuple(lifecycle.reason_codes),
        "hold_score": tuple(hold_score.reason_codes),
        "euphoria": tuple(euphoria.reason_codes),
        "crowding": tuple(crowding.reason_codes),
        "current_flow": tuple(current_flow.reason_codes),
        "prior_flow": tuple(prior_flow.reason_codes),
    }
    return evaluate_trim_rules(
        TrimRuleInput(
            position_open=lifecycle.is_open,
            hold_score=hold_score.score if hold_score.complete else None,
            euphoria_active=euphoria.flagged if euphoria.complete else None,
            crowding_active=crowding.flagged if crowding.complete else None,
            current_flow_score=current_flow.score if current_flow.complete else None,
            prior_flow_score=prior_flow.score if prior_flow.complete else None,
            source_reason_codes=evidence,
        ),
        strategy_config=strategy_config,
    )


def flow_score_is_deteriorating(
    *,
    current_flow_score: Any,
    prior_flow_score: Any,
) -> bool:
    """Return whether current flow is below the prior decision's score."""

    current = _score(current_flow_score, "current_flow_score")
    prior = _score(prior_flow_score, "prior_flow_score")
    return decision_less(current, prior)


def _evaluate(
    inputs: TrimRuleInput,
    *,
    trim_minimum: Decimal,
    defensive_minimum: Decimal,
    exit_below: Decimal,
) -> _TrimDecision:
    values = _validate_inputs(inputs)
    missing_inputs = tuple(
        input_id for input_id in TRIM_RULE_INPUT_IDS if values[input_id] is None
    )
    reasons: list[str] = []
    if missing_inputs:
        reasons.append("TRIM_INPUT_MISSING")

    position_open = values["position_open"]
    hold_score = values["hold_score"]
    exit_precedence = bool(
        hold_score is not None and decision_less(hold_score, exit_below)
    )
    trigger_reasons: list[str] = []
    if (
        hold_score is not None
        and decision_greater_equal(hold_score, trim_minimum)
        and decision_less(hold_score, defensive_minimum)
    ):
        trigger_reasons.append("TRIM_HOLD_SCORE_BAND")
    if values["euphoria_active"] is True:
        trigger_reasons.append("TRIM_EUPHORIA_ACTIVE")
    if values["crowding_active"] is True:
        trigger_reasons.append("TRIM_CROWDING_ACTIVE")
    if (
        values["current_flow_score"] is not None
        and values["prior_flow_score"] is not None
        and flow_score_is_deteriorating(
            current_flow_score=values["current_flow_score"],
            prior_flow_score=values["prior_flow_score"],
        )
    ):
        trigger_reasons.append("TRIM_FLOW_DETERIORATION")

    signal = False
    if position_open is False:
        reasons.append("TRIM_NO_OPEN_POSITION")
    elif position_open is True and exit_precedence:
        reasons.append("TRIM_SUPPRESSED_EXIT_BAND")
    elif position_open is True and trigger_reasons:
        reasons.extend(trigger_reasons)
        signal = True
    elif position_open is True and not missing_inputs:
        reasons.append("TRIM_NOT_TRIGGERED")

    return _TrimDecision(
        signal=signal,
        action=TRIM_ACTION if signal else None,
        effects=TRIM_EFFECTS if signal else (),
        exit_precedence=exit_precedence,
        missing_inputs=missing_inputs,
        complete=not missing_inputs,
        reason_codes=tuple(reasons),
    )


def _validate_inputs(inputs: TrimRuleInput) -> dict[str, Any]:
    if not isinstance(inputs, TrimRuleInput):
        raise TypeError("inputs must be a TrimRuleInput")
    values = {
        "position_open": inputs.position_open,
        "hold_score": inputs.hold_score,
        "euphoria_active": inputs.euphoria_active,
        "crowding_active": inputs.crowding_active,
        "current_flow_score": inputs.current_flow_score,
        "prior_flow_score": inputs.prior_flow_score,
    }
    for input_id in _BOOLEAN_INPUT_IDS:
        value = values[input_id]
        if value is not None and not isinstance(value, (bool, np.bool_)):
            raise TypeError(f"{input_id} must be a bool or None")
        if isinstance(value, np.bool_):
            values[input_id] = bool(value)
    for input_id in _SCORE_INPUT_IDS:
        value = values[input_id]
        if value is not None:
            values[input_id] = _score(value, input_id)
    _normalize_source_reason_codes(inputs.source_reason_codes)
    return values


def _validate_thresholds(
    *,
    trim_minimum: Any,
    defensive_minimum: Any,
    exit_below: Any,
) -> tuple[Decimal, Decimal, Decimal]:
    trim = _score(trim_minimum, "trim_minimum")
    defensive = _score(defensive_minimum, "defensive_minimum")
    exit_threshold = _score(exit_below, "exit_below")
    if not decision_less(trim, defensive):
        raise ValueError("trim_minimum must be below defensive_minimum")
    if decision_less(trim, exit_threshold):
        raise ValueError("exit_below must be <= trim_minimum")
    return trim, defensive, exit_threshold


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
            raise TypeError("source reason codes must be tuples of strings")
        normalized_codes = tuple(codes)
        if any(not isinstance(code, str) or not code for code in normalized_codes):
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


def _score(value: Any, name: str) -> Decimal:
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be numeric")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError(f"{name} must be numeric") from error
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    if result < 0 or result > 100:
        raise ValueError(f"{name} must be between 0 and 100")
    return result


__all__ = [
    "TRIM_ACTION",
    "TRIM_EFFECTS",
    "TRIM_REASON_CODES",
    "TRIM_RULE_INPUT_IDS",
    "TRIM_RULES_PARAMETER_STATUS",
    "TRIM_RULES_POLICY_VERSION",
    "TRIM_SIGNAL_FEATURE_ID",
    "TrimRuleInput",
    "TrimSignalResult",
    "evaluate_trim_rules",
    "flow_score_is_deteriorating",
    "trim_rules_from_results",
]
