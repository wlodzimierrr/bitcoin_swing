"""Fail-closed pyramiding requirements orchestration (BTC-154).

Rulebook 18 and 31 make adding strictly harder than holding. Every requirement
is conjunctive, so this engine mirrors BTC-132: an unresolved input blocks the
add rather than being assumed favourable, and each refusal carries its own
reason code so the explanation survives into persistence.

Two requirements are deliberately not booleans:

``Add Score``
    compared against ``add_thresholds.add_min`` under DECISION_COMPARISON_V1,
    so the 85 boundary is inclusive and tolerance-stable rather than a bare
    float comparison.

``stop can improve``
    taken as the *signed* currency improvement from BTC-047 by way of BTC-153's
    ``risk_improvement_component_score``. A floored improvement cannot tell an
    unchanged stop from a worsened one, and both must block an add, so the sign
    is what this gate needs. Strict improvement is required: an unchanged stop
    does not earn a bigger position.

The engine composes upstream results rather than restating them.
``add_requirements_from_results`` is the canonical path: profitability comes
from the BTC-150 ledger, the score from BTC-153, projected risk from BTC-146.
Nothing here re-derives a sign convention that another module already owns.

Scope. This decides whether an add is *permitted*, not how large it is
(BTC-155) or where the stop then goes (BTC-156). It does not duplicate the
BTC-150 transition table: a position whose state forbids ADD is refused by the
state machine, and a lifecycle that is not open resolves profitability to
``None`` here, which fails closed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from btc_predictor.config import StrategyConfig
from btc_predictor.features.add import (
    ADD_SCORE_FEATURE_ID,
    RISK_IMPROVEMENT_NORMALIZATION_VERSION,
    AddScoreResult,
    RiskImprovementComponent,
)
from btc_predictor.portfolio.state_machine import (
    OPEN_POSITION_STATES,
    PositionLifecycle,
    position_is_profitable_at_price,
)
from btc_predictor.quant.comparisons import decision_greater, decision_greater_equal
from btc_predictor.risk.exposure import RISK_AT_STOP_FEATURE_ID, RiskAtStopResult


ADD_REQUIREMENTS_FEATURE_ID = "ADD_REQUIREMENTS"
ADD_REQUIREMENTS_POLICY_VERSION = "ADD_REQUIREMENTS_V1"
ADD_REQUIREMENTS_EFFECTS = ("NO_ADD",)
ADD_REQUIREMENTS_INPUT_IDS = (
    "position_profitable",
    "new_structural_confirmation",
    "signed_risk_improvement",
    "regime_supportive",
    "flow_supportive",
    "positioning_healthy",
    "add_score",
    "projected_risk_at_stop_within_maximum",
)
_BOOLEAN_INPUT_IDS = (
    "position_profitable",
    "new_structural_confirmation",
    "regime_supportive",
    "flow_supportive",
    "positioning_healthy",
    "projected_risk_at_stop_within_maximum",
)
ADD_REQUIREMENTS_REASON_CODES = (
    "ADD_REQUIREMENTS_INPUT_MISSING",
    "ADD_REQUIREMENTS_POSITION_NOT_PROFITABLE",
    "ADD_REQUIREMENTS_NO_NEW_STRUCTURE",
    "ADD_REQUIREMENTS_STOP_CANNOT_IMPROVE",
    "ADD_REQUIREMENTS_REGIME_UNSUPPORTIVE",
    "ADD_REQUIREMENTS_FLOW_UNSUPPORTIVE",
    "ADD_REQUIREMENTS_POSITIONING_UNHEALTHY",
    "ADD_REQUIREMENTS_ADD_SCORE_BELOW_MINIMUM",
    "ADD_REQUIREMENTS_RISK_AT_STOP_EXCEEDED",
    "ADD_REQUIREMENTS_SATISFIED",
)
ADD_REQUIREMENTS_PARAMETER_STATUS = "PROVISIONAL_PENDING_BTC_185"
_REQUIRED_CONFIG_METADATA_KEYS = (
    "config_version",
    "strategy_version",
    "parameter_set_id",
)


@dataclass(frozen=True)
class AddRequirementsInput:
    """Resolved upstream states needed to authorize a pyramid add.

    ``None`` means a required state is unavailable and the engine fails closed.
    ``signed_risk_improvement`` is currency at the shared stop and may be
    negative; ``add_score`` is a 0-100 BTC-153 score. Source reason codes retain
    the evidence used to resolve each state.
    """

    position_profitable: bool | None
    new_structural_confirmation: bool | None
    signed_risk_improvement: Decimal | None
    regime_supportive: bool | None
    flow_supportive: bool | None
    positioning_healthy: bool | None
    add_score: Decimal | None
    projected_risk_at_stop_within_maximum: bool | None
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
                for input_id in ADD_REQUIREMENTS_INPUT_IDS
            },
            "source_reason_codes": {
                source: list(codes)
                for source, codes in _normalize_source_reason_codes(
                    self.source_reason_codes,
                ).items()
            },
        }


@dataclass(frozen=True)
class AddRequirementsResult:
    feature_id: str
    policy_version: str
    parameter_status: str
    inputs: AddRequirementsInput
    minimum_add_score: Decimal
    require_profitable_position: bool
    require_stop_improvement: bool
    blocked: bool
    effects: tuple[str, ...]
    missing_inputs: tuple[str, ...]
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...]

    @property
    def permitted(self) -> bool:
        return not self.blocked

    def as_record(self) -> dict[str, Any]:
        """Return a self-validating record sufficient to reproduce the gate."""

        if self.feature_id != ADD_REQUIREMENTS_FEATURE_ID:
            raise ValueError("feature_id must be ADD_REQUIREMENTS")
        if self.policy_version != ADD_REQUIREMENTS_POLICY_VERSION:
            raise ValueError(
                f"policy_version must be {ADD_REQUIREMENTS_POLICY_VERSION}",
            )
        if self.parameter_status != ADD_REQUIREMENTS_PARAMETER_STATUS:
            raise ValueError(
                f"parameter_status must be {ADD_REQUIREMENTS_PARAMETER_STATUS}",
            )
        minimum = _score(self.minimum_add_score, "minimum_add_score")
        metadata = _validate_config_metadata(self.config_metadata)
        expected = _evaluate(
            self.inputs,
            minimum_add_score=minimum,
            require_profitable_position=self.require_profitable_position,
            require_stop_improvement=self.require_stop_improvement,
        )
        if self.blocked != expected.blocked:
            raise ValueError("blocked does not match add-requirement inputs")
        if self.effects != expected.effects:
            raise ValueError("effects do not match add-requirement state")
        if self.missing_inputs != expected.missing_inputs:
            raise ValueError("missing_inputs do not match add-requirement inputs")
        if self.complete != expected.complete:
            raise ValueError("complete does not match add-requirement inputs")
        if self.reason_codes != expected.reason_codes:
            raise ValueError("reason_codes do not match add-requirement inputs")

        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "parameter_status": self.parameter_status,
            "inputs": self.inputs.as_record(),
            "minimum_add_score": str(minimum),
            "require_profitable_position": self.require_profitable_position,
            "require_stop_improvement": self.require_stop_improvement,
            "blocked": self.blocked,
            "effects": list(self.effects),
            "missing_inputs": list(self.missing_inputs),
            "config_metadata": metadata,
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class _AddDecision:
    blocked: bool
    effects: tuple[str, ...]
    missing_inputs: tuple[str, ...]
    complete: bool
    reason_codes: tuple[str, ...]


def evaluate_add_requirements(
    inputs: AddRequirementsInput,
    *,
    strategy_config: StrategyConfig,
) -> AddRequirementsResult:
    """Evaluate every Phase 1 add requirement in a stable order."""

    if not isinstance(inputs, AddRequirementsInput):
        raise TypeError("inputs must be an AddRequirementsInput")
    if not isinstance(strategy_config, StrategyConfig):
        raise TypeError("strategy_config must be a StrategyConfig")

    thresholds = strategy_config.add_thresholds
    minimum = _score(thresholds.add_min, "minimum_add_score")
    decision = _evaluate(
        inputs,
        minimum_add_score=minimum,
        require_profitable_position=(
            thresholds.existing_position_must_be_profitable
        ),
        require_stop_improvement=thresholds.stop_must_improve,
    )
    result = AddRequirementsResult(
        feature_id=ADD_REQUIREMENTS_FEATURE_ID,
        policy_version=ADD_REQUIREMENTS_POLICY_VERSION,
        parameter_status=ADD_REQUIREMENTS_PARAMETER_STATUS,
        inputs=inputs,
        minimum_add_score=minimum,
        require_profitable_position=(
            thresholds.existing_position_must_be_profitable
        ),
        require_stop_improvement=thresholds.stop_must_improve,
        blocked=decision.blocked,
        effects=decision.effects,
        missing_inputs=decision.missing_inputs,
        config_metadata=_validate_config_metadata(strategy_config.run_metadata()),
        complete=decision.complete,
        reason_codes=decision.reason_codes,
    )
    result.as_record()
    return result


def add_requirements_from_results(
    *,
    lifecycle: PositionLifecycle,
    current_price: Any,
    add_score: AddScoreResult,
    risk_improvement: RiskImprovementComponent,
    projected_risk_at_stop: RiskAtStopResult,
    new_structural_confirmation: bool | None,
    regime_supportive: bool | None,
    flow_supportive: bool | None,
    positioning_healthy: bool | None,
    strategy_config: StrategyConfig,
    source_reason_codes: Mapping[str, tuple[str, ...]] | None = None,
) -> AddRequirementsResult:
    """Canonical path: gate an add from the upstream results themselves.

    Profitability comes from the BTC-150 ledger's weighted average entry, the
    score from a BTC-153 ``AddScoreResult``, the stop improvement from a BTC-153
    ``RiskImprovementComponent``, and the ceiling test from a BTC-146
    ``RiskAtStopResult`` computed on the *projected* post-add book. An
    incomplete upstream result resolves to ``None`` and blocks the add.

    Each upstream result is identified rather than duck-typed, the way BTC-157
    and BTC-158 identify theirs. A ``HoldScoreResult`` also exposes ``score``
    and ``complete``, so structural typing alone would let the v1.2 de-nesting
    that BTC-153 exists to enforce be undone here by composition -- an add
    authorized by Hold Score, with the persisted evidence saying so and nothing
    refusing it. Config identity is checked for the same reason: a run must not
    mix parameter sets and then record itself under only one of them.
    """

    if not isinstance(lifecycle, PositionLifecycle):
        raise TypeError("lifecycle must be a PositionLifecycle")
    if not isinstance(add_score, AddScoreResult):
        raise TypeError("add_score must be an AddScoreResult")
    if not isinstance(risk_improvement, RiskImprovementComponent):
        raise TypeError("risk_improvement must be a RiskImprovementComponent")
    if not isinstance(projected_risk_at_stop, RiskAtStopResult):
        raise TypeError("projected_risk_at_stop must be a RiskAtStopResult")
    if not isinstance(strategy_config, StrategyConfig):
        raise TypeError("strategy_config must be a StrategyConfig")
    if add_score.feature_id != ADD_SCORE_FEATURE_ID:
        raise ValueError("add_score feature_id must be ADD_SCORE")
    if projected_risk_at_stop.feature_id != RISK_AT_STOP_FEATURE_ID:
        raise ValueError("projected_risk_at_stop feature_id must be RISK_AT_STOP")
    if (
        risk_improvement.normalization_version
        != RISK_IMPROVEMENT_NORMALIZATION_VERSION
    ):
        raise ValueError(
            "risk_improvement normalization_version must be "
            f"{RISK_IMPROVEMENT_NORMALIZATION_VERSION}",
        )
    add_score.as_record()
    projected_risk_at_stop.as_record()
    risk_improvement.as_record()

    metadata = _validate_config_metadata(strategy_config.run_metadata())
    for source, source_metadata in (
        ("lifecycle", lifecycle.config_metadata),
        ("add_score", add_score.config_metadata),
        ("projected_risk_at_stop", projected_risk_at_stop.config_metadata),
    ):
        if dict(source_metadata) != metadata:
            raise ValueError(f"{source} config_metadata does not match strategy_config")

    evidence = {
        key: tuple(codes) for key, codes in dict(source_reason_codes or {}).items()
    }

    profitable: bool | None = None
    if (
        lifecycle.state in OPEN_POSITION_STATES
        and lifecycle.average_entry_price is not None
    ):
        profitable = position_is_profitable_at_price(
            direction=lifecycle.direction,
            average_entry_price=lifecycle.average_entry_price,
            current_price=current_price,
        )
    if lifecycle.reason_codes:
        evidence.setdefault("lifecycle", tuple(lifecycle.reason_codes))

    score = add_score.score if add_score.complete else None
    if add_score.reason_codes:
        evidence.setdefault("add_score", tuple(add_score.reason_codes))

    signed = risk_improvement.signed_improvement

    within_maximum = (
        projected_risk_at_stop.within_maximum
        if projected_risk_at_stop.complete
        else None
    )
    if projected_risk_at_stop.reason_codes:
        evidence.setdefault(
            "projected_risk_at_stop",
            tuple(projected_risk_at_stop.reason_codes),
        )

    return evaluate_add_requirements(
        AddRequirementsInput(
            position_profitable=profitable,
            new_structural_confirmation=new_structural_confirmation,
            signed_risk_improvement=signed,
            regime_supportive=regime_supportive,
            flow_supportive=flow_supportive,
            positioning_healthy=positioning_healthy,
            add_score=score,
            projected_risk_at_stop_within_maximum=within_maximum,
            source_reason_codes=evidence,
        ),
        strategy_config=strategy_config,
    )


def _evaluate(
    inputs: AddRequirementsInput,
    *,
    minimum_add_score: Decimal,
    require_profitable_position: bool,
    require_stop_improvement: bool,
) -> _AddDecision:
    values = _validate_inputs(inputs)
    if not isinstance(require_profitable_position, bool):
        raise TypeError("require_profitable_position must be a bool")
    if not isinstance(require_stop_improvement, bool):
        raise TypeError("require_stop_improvement must be a bool")

    missing_inputs = tuple(
        input_id
        for input_id in ADD_REQUIREMENTS_INPUT_IDS
        if values[input_id] is None
        and _input_is_required(
            input_id,
            require_profitable_position=require_profitable_position,
            require_stop_improvement=require_stop_improvement,
        )
    )
    reasons = []
    if missing_inputs:
        reasons.append("ADD_REQUIREMENTS_INPUT_MISSING")
    if require_profitable_position and values["position_profitable"] is not True:
        reasons.append("ADD_REQUIREMENTS_POSITION_NOT_PROFITABLE")
    if values["new_structural_confirmation"] is not True:
        reasons.append("ADD_REQUIREMENTS_NO_NEW_STRUCTURE")
    if require_stop_improvement and not _stop_improves(
        values["signed_risk_improvement"],
    ):
        # Strict: an unchanged stop does not earn a bigger position, and a
        # floored improvement could not tell that case from a worsened one.
        reasons.append("ADD_REQUIREMENTS_STOP_CANNOT_IMPROVE")
    if values["regime_supportive"] is not True:
        reasons.append("ADD_REQUIREMENTS_REGIME_UNSUPPORTIVE")
    if values["flow_supportive"] is not True:
        reasons.append("ADD_REQUIREMENTS_FLOW_UNSUPPORTIVE")
    if values["positioning_healthy"] is not True:
        reasons.append("ADD_REQUIREMENTS_POSITIONING_UNHEALTHY")
    if not _score_clears(values["add_score"], minimum_add_score):
        reasons.append("ADD_REQUIREMENTS_ADD_SCORE_BELOW_MINIMUM")
    if values["projected_risk_at_stop_within_maximum"] is not True:
        reasons.append("ADD_REQUIREMENTS_RISK_AT_STOP_EXCEEDED")

    blocked = bool(reasons)
    reason_codes = tuple(reasons) if blocked else ("ADD_REQUIREMENTS_SATISFIED",)
    return _AddDecision(
        blocked=blocked,
        effects=ADD_REQUIREMENTS_EFFECTS if blocked else (),
        missing_inputs=missing_inputs,
        complete=not missing_inputs,
        reason_codes=reason_codes,
    )


def _input_is_required(
    input_id: str,
    *,
    require_profitable_position: bool,
    require_stop_improvement: bool,
) -> bool:
    if input_id == "position_profitable":
        return require_profitable_position
    if input_id == "signed_risk_improvement":
        return require_stop_improvement
    return True


def _stop_improves(value: Decimal | None) -> bool:
    return value is not None and decision_greater(value, Decimal("0"))


def _score_clears(value: Decimal | None, minimum: Decimal) -> bool:
    return value is not None and decision_greater_equal(value, minimum)


def _validate_inputs(inputs: AddRequirementsInput) -> dict[str, Any]:
    values: dict[str, Any] = {
        "position_profitable": inputs.position_profitable,
        "new_structural_confirmation": inputs.new_structural_confirmation,
        "signed_risk_improvement": inputs.signed_risk_improvement,
        "regime_supportive": inputs.regime_supportive,
        "flow_supportive": inputs.flow_supportive,
        "positioning_healthy": inputs.positioning_healthy,
        "add_score": inputs.add_score,
        "projected_risk_at_stop_within_maximum": (
            inputs.projected_risk_at_stop_within_maximum
        ),
    }
    for input_id in _BOOLEAN_INPUT_IDS:
        value = values[input_id]
        if value is not None and not isinstance(value, bool):
            raise TypeError(f"{input_id} must be a bool or None")
    if values["signed_risk_improvement"] is not None:
        values["signed_risk_improvement"] = _decimal(
            values["signed_risk_improvement"],
            "signed_risk_improvement",
        )
    if values["add_score"] is not None:
        values["add_score"] = _score(values["add_score"], "add_score")
    _normalize_source_reason_codes(inputs.source_reason_codes)
    return values


def _normalize_source_reason_codes(
    source_reason_codes: Mapping[str, tuple[str, ...]],
) -> dict[str, tuple[str, ...]]:
    if not isinstance(source_reason_codes, Mapping):
        raise TypeError("source_reason_codes must be a mapping")
    normalized: dict[str, tuple[str, ...]] = {}
    for source, codes in source_reason_codes.items():
        if not isinstance(source, str) or not source.strip():
            raise ValueError("source_reason_codes keys must be non-empty strings")
        if isinstance(codes, str) or not isinstance(codes, (tuple, list)):
            raise TypeError(f"source_reason_codes.{source} must be a sequence")
        for code in codes:
            if not isinstance(code, str) or not code.strip():
                raise ValueError(
                    f"source_reason_codes.{source} must contain non-empty strings",
                )
        normalized[source] = tuple(codes)
    return normalized


def _validate_config_metadata(metadata: Mapping[str, Any]) -> dict[str, str]:
    missing = [key for key in _REQUIRED_CONFIG_METADATA_KEYS if key not in metadata]
    if missing:
        raise ValueError(f"config_metadata missing {missing}")
    normalized = dict(metadata)
    for key in _REQUIRED_CONFIG_METADATA_KEYS:
        value = normalized[key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"config_metadata.{key} must be a non-empty string")
    return normalized


def _score(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if result < 0 or result > 100:
        raise ValueError(f"{name} must be between 0 and 100")
    return result


def _decimal(value: Any, name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError(f"{name} must be numeric") from error
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    return result


__all__ = [
    "ADD_REQUIREMENTS_EFFECTS",
    "ADD_REQUIREMENTS_FEATURE_ID",
    "ADD_REQUIREMENTS_INPUT_IDS",
    "ADD_REQUIREMENTS_PARAMETER_STATUS",
    "ADD_REQUIREMENTS_POLICY_VERSION",
    "ADD_REQUIREMENTS_REASON_CODES",
    "AddRequirementsInput",
    "AddRequirementsResult",
    "add_requirements_from_results",
    "evaluate_add_requirements",
]
