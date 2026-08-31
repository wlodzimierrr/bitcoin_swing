"""Versioned v1.2 Add Score aggregation.

Rulebook 21 removes ``HoldScore`` from the Add Score arithmetic because Hold
already carries Flow, Positioning, Structure and momentum information. Adding
Hold back as a weighted component would double-count all of it, so this module
has no field, weight key, or input route for it. Hold quality and a supportive
Regime remain separate add *requirements* and lifecycle context (BTC-154).

``RiskImprovement`` is the one component whose natural unit is not a 0-100
score: BTC-047 reports it in absolute currency. The aggregator therefore takes
an explicit normalized component, exactly as BTC-152 does for Momentum
Persistence, and ``risk_improvement_component_score`` is offered separately as
a versioned bridge for callers that want one rather than inventing their own.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from btc_predictor.config import StrategyConfig
from btc_predictor.config.strategy import ADD_SCORE_CONTRACT_VERSION
from btc_predictor.features._scoring import decimal_weighted_score
from btc_predictor.features.scoring_contracts import SCORING_PARAMETER_STATUS
from btc_predictor.quant import (
    CompleteOutput,
    FloatArray,
    NumericInputError,
    ScoreOutput,
    as_float64_array,
    decision_equal,
    weighted_score,
)
from btc_predictor.quant.risk import risk_improvement


ADD_SCORE_FEATURE_ID = "ADD_SCORE"
ADD_SCORE_VERSION = ADD_SCORE_CONTRACT_VERSION
ADD_SCORE_COMPONENT_IDS = (
    "new_structure",
    "flow",
    "positioning",
    "momentum",
    "risk_improvement",
)
ADD_SCORE_REASON_CODES = (
    "ADD_SCORE_INPUT_MISSING",
    "ADD_SCORE_COMPLETE",
)
ADD_SCORE_WEIGHT_SUM_TOLERANCE = Decimal("0.000001")
REQUIRED_CONFIG_METADATA_KEYS = (
    "config_version",
    "strategy_version",
    "parameter_set_id",
)

# Proportional normalization of the BTC-047 currency-denominated improvement:
# the share of current risk that the proposed stop removes, scaled to 0-100. It
# has no free parameter, so it is a mechanical unit conversion rather than a
# calibration. A NAV-relative alternative is equally defensible, which is why
# the choice is versioned and why the aggregator never applies one implicitly.
RISK_IMPROVEMENT_NORMALIZATION_VERSION = "RISK_IMPROVEMENT_PROPORTIONAL_V1"


@dataclass(frozen=True)
class AddScoreInput:
    """Direct v1.2 component scores; Hold Score deliberately has no field."""

    new_structure_score: Decimal | None
    flow_score: Decimal | None
    positioning_score: Decimal | None
    momentum_score: Decimal | None
    risk_improvement_score: Decimal | None

    def as_record(self) -> dict[str, str | None]:
        return {
            "new_structure": _optional_score_record(
                self.new_structure_score,
                "new_structure",
            ),
            "flow": _optional_score_record(self.flow_score, "flow"),
            "positioning": _optional_score_record(
                self.positioning_score,
                "positioning",
            ),
            "momentum": _optional_score_record(self.momentum_score, "momentum"),
            "risk_improvement": _optional_score_record(
                self.risk_improvement_score,
                "risk_improvement",
            ),
        }


@dataclass(frozen=True)
class AddScoreResult:
    feature_id: str
    score_version: str
    parameter_status: str
    score: Decimal | None
    inputs: AddScoreInput
    weights: dict[str, Decimal]
    contributions: dict[str, Decimal | None]
    missing_components: tuple[str, ...]
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        """Return a validated record sufficient to reconstruct the score."""

        if self.feature_id != ADD_SCORE_FEATURE_ID:
            raise ValueError("feature_id must be ADD_SCORE")
        if self.score_version != ADD_SCORE_VERSION:
            raise ValueError(f"score_version must be {ADD_SCORE_VERSION}")
        if self.parameter_status != SCORING_PARAMETER_STATUS:
            raise ValueError(
                f"parameter_status must be {SCORING_PARAMETER_STATUS}",
            )

        inputs = _input_values(self.inputs)
        weights = _normalize_weights(self.weights)
        metadata = _validate_config_metadata(self.config_metadata)
        if set(self.contributions) != set(ADD_SCORE_COMPONENT_IDS):
            raise ValueError("contributions must exactly match Add Score components")
        contributions = {
            component_id: (
                _non_negative_decimal(self.contributions[component_id], component_id)
                if self.contributions[component_id] is not None
                else None
            )
            for component_id in ADD_SCORE_COMPONENT_IDS
        }
        expected_missing = tuple(
            component_id
            for component_id in ADD_SCORE_COMPONENT_IDS
            if inputs[component_id] is None
        )
        contribution_missing = tuple(
            component_id
            for component_id in ADD_SCORE_COMPONENT_IDS
            if contributions[component_id] is None
        )
        if self.missing_components != expected_missing:
            raise ValueError("missing_components do not match Add Score inputs")
        if contribution_missing != expected_missing:
            raise ValueError("contributions do not match Add Score inputs")
        if self.complete != (self.score is not None and not expected_missing):
            raise ValueError("complete state does not match Add Score inputs")
        expected_reason_codes = (
            ("ADD_SCORE_COMPLETE",)
            if self.complete
            else ("ADD_SCORE_INPUT_MISSING",)
        )
        if self.reason_codes != expected_reason_codes:
            raise ValueError("reason_codes do not match Add Score state")

        score = _score(self.score, "score") if self.score is not None else None
        if score is not None:
            contribution_total = sum(
                (value for value in contributions.values() if value is not None),
                Decimal("0"),
            )
            if not decision_equal(contribution_total, score):
                raise ValueError("component contributions must sum to score")

        return {
            "feature_id": self.feature_id,
            "score_version": self.score_version,
            "parameter_status": self.parameter_status,
            "score": str(score) if score is not None else None,
            "inputs": {
                key: str(value) if value is not None else None
                for key, value in inputs.items()
            },
            "weights": {key: str(value) for key, value in weights.items()},
            "contributions": {
                key: str(value) if value is not None else None
                for key, value in contributions.items()
            },
            "missing_components": list(self.missing_components),
            "config_metadata": metadata,
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class AddScoreBatchResult:
    """Float64 batch output aligned to ``ADD_SCORE_COMPONENT_IDS``."""

    score_version: str
    parameter_status: str
    component_ids: tuple[str, ...]
    weights: dict[str, Decimal]
    scores: ScoreOutput
    contributions: FloatArray
    missing_mask: NDArray[np.bool_]
    complete_mask: CompleteOutput
    single_row: bool
    config_metadata: dict[str, str]


@dataclass(frozen=True)
class RiskImprovementComponent:
    """Currency-denominated risk improvement expressed as a 0-100 component."""

    normalization_version: str
    current_risk: Decimal
    proposed_risk: Decimal
    signed_improvement: Decimal
    improvement_fraction: Decimal | None
    score: Decimal | None
    worsened: bool

    def as_record(self) -> dict[str, Any]:
        return {
            "normalization_version": self.normalization_version,
            "current_risk": str(self.current_risk),
            "proposed_risk": str(self.proposed_risk),
            "signed_improvement": str(self.signed_improvement),
            "improvement_fraction": (
                str(self.improvement_fraction)
                if self.improvement_fraction is not None
                else None
            ),
            "score": str(self.score) if self.score is not None else None,
            "worsened": self.worsened,
        }


def calculate_add_score(
    inputs: AddScoreInput,
    *,
    strategy_config: StrategyConfig,
) -> AddScoreResult:
    """Calculate one v1.2 Add Score from direct component scores."""

    if not isinstance(inputs, AddScoreInput):
        raise TypeError("inputs must be an AddScoreInput")
    weights, metadata = _config_contract(strategy_config)
    input_values = _input_values(inputs)
    weighted = decimal_weighted_score(
        input_values,
        weights,
        component_ids=ADD_SCORE_COMPONENT_IDS,
    )
    complete = weighted.score is not None
    reason_codes = (
        ("ADD_SCORE_COMPLETE",)
        if complete
        else ("ADD_SCORE_INPUT_MISSING",)
    )
    return AddScoreResult(
        feature_id=ADD_SCORE_FEATURE_ID,
        score_version=ADD_SCORE_VERSION,
        parameter_status=SCORING_PARAMETER_STATUS,
        score=weighted.score,
        inputs=inputs,
        weights=weights,
        contributions=weighted.contributions,
        missing_components=weighted.missing_components,
        config_metadata=metadata,
        complete=complete,
        reason_codes=reason_codes,
    )


def calculate_add_score_batch(
    values: ArrayLike,
    *,
    strategy_config: StrategyConfig,
) -> AddScoreBatchResult:
    """Score one float64 row or a historical matrix in canonical column order."""

    weights, metadata = _config_contract(strategy_config)
    observations = as_float64_array(
        values,
        allow_empty=True,
        nan_policy="propagate",
    )
    available = observations[~np.isnan(observations)]
    if np.any((available < 0) | (available > 100)):
        raise NumericInputError("Add Score components must be between 0 and 100")
    weighted = weighted_score(
        observations,
        {key: float(value) for key, value in weights.items()},
        component_names=ADD_SCORE_COMPONENT_IDS,
    )
    return AddScoreBatchResult(
        score_version=ADD_SCORE_VERSION,
        parameter_status=SCORING_PARAMETER_STATUS,
        component_ids=ADD_SCORE_COMPONENT_IDS,
        weights=weights,
        scores=weighted.scores,
        contributions=weighted.contributions,
        missing_mask=weighted.missing_mask,
        complete_mask=weighted.complete_mask,
        single_row=weighted.single_row,
        config_metadata=metadata,
    )


def risk_improvement_component_score(
    *,
    current_risk: Any,
    proposed_risk: Any,
) -> RiskImprovementComponent:
    """Convert BTC-047 risk improvement into a 0-100 Add Score component.

    The improvement is the share of the current risk that the proposed stop
    removes, so a stop that does not improve scores 0 and one that fully
    protects the position scores 100. A worsened stop is reported as a signed
    negative improvement and scores 0; rulebook 18 requires an *improved* stop
    to add at all, and that requirement is BTC-154's, not this score's.

    Both figures are absolute currency at the shared stop, which is what
    ``btc_predictor.risk.exposure`` produces.
    """

    current = _non_negative_decimal(current_risk, "current_risk")
    proposed = _non_negative_decimal(proposed_risk, "proposed_risk")
    # BTC-047 owns the arithmetic; the signed form is what distinguishes an
    # unchanged portfolio from one whose risk grew.
    signed = Decimal(
        str(
            risk_improvement(
                float(current),
                float(proposed),
                floor_at_zero=False,
            )
        )
    )
    worsened = signed < 0
    if current == 0:
        # No risk to remove: the proportion is undefined rather than perfect.
        return RiskImprovementComponent(
            normalization_version=RISK_IMPROVEMENT_NORMALIZATION_VERSION,
            current_risk=current,
            proposed_risk=proposed,
            signed_improvement=signed,
            improvement_fraction=None,
            score=None,
            worsened=worsened,
        )
    fraction = (current - proposed) / current
    bounded = min(max(fraction, Decimal("0")), Decimal("1"))
    return RiskImprovementComponent(
        normalization_version=RISK_IMPROVEMENT_NORMALIZATION_VERSION,
        current_risk=current,
        proposed_risk=proposed,
        signed_improvement=signed,
        improvement_fraction=fraction,
        score=bounded * Decimal("100"),
        worsened=worsened,
    )


def _config_contract(
    strategy_config: StrategyConfig,
) -> tuple[dict[str, Decimal], dict[str, str]]:
    if not isinstance(strategy_config, StrategyConfig):
        raise TypeError("strategy_config must be a StrategyConfig")
    weights = _normalize_weights(strategy_config.scoring_weights.add_score)
    metadata = _validate_config_metadata(strategy_config.run_metadata())
    return weights, metadata


def _normalize_weights(weights: Mapping[str, Any]) -> dict[str, Decimal]:
    missing = set(ADD_SCORE_COMPONENT_IDS) - set(weights)
    extra = set(weights) - set(ADD_SCORE_COMPONENT_IDS)
    if missing or extra:
        raise ValueError(
            "Add Score weights must exactly match "
            f"{ADD_SCORE_COMPONENT_IDS}; "
            f"missing={sorted(missing)}, extra={sorted(extra)}",
        )
    normalized = {
        component_id: _non_negative_decimal(weights[component_id], component_id)
        for component_id in ADD_SCORE_COMPONENT_IDS
    }
    total = sum(normalized.values(), Decimal("0"))
    if abs(total - Decimal("1")) > ADD_SCORE_WEIGHT_SUM_TOLERANCE:
        raise ValueError("Add Score weights must sum to 1")
    return normalized


def _input_values(inputs: AddScoreInput) -> dict[str, Decimal | None]:
    values = {
        "new_structure": inputs.new_structure_score,
        "flow": inputs.flow_score,
        "positioning": inputs.positioning_score,
        "momentum": inputs.momentum_score,
        "risk_improvement": inputs.risk_improvement_score,
    }
    return {
        component_id: (
            _score(value, component_id) if value is not None else None
        )
        for component_id, value in values.items()
    }


def _validate_config_metadata(metadata: Mapping[str, Any]) -> dict[str, str]:
    missing = [key for key in REQUIRED_CONFIG_METADATA_KEYS if key not in metadata]
    if missing:
        raise ValueError(f"config_metadata missing {missing}")
    normalized = dict(metadata)
    for key in REQUIRED_CONFIG_METADATA_KEYS:
        value = normalized[key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"config_metadata.{key} must be a non-empty string")
    return normalized


def _optional_score_record(value: Any | None, name: str) -> str | None:
    return str(_score(value, name)) if value is not None else None


def _score(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if result < 0 or result > 100:
        raise ValueError(f"{name} must be between 0 and 100")
    return result


def _non_negative_decimal(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
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


__all__ = [
    "ADD_SCORE_COMPONENT_IDS",
    "ADD_SCORE_FEATURE_ID",
    "ADD_SCORE_REASON_CODES",
    "ADD_SCORE_VERSION",
    "ADD_SCORE_WEIGHT_SUM_TOLERANCE",
    "RISK_IMPROVEMENT_NORMALIZATION_VERSION",
    "AddScoreBatchResult",
    "AddScoreInput",
    "AddScoreResult",
    "RiskImprovementComponent",
    "calculate_add_score",
    "calculate_add_score_batch",
    "risk_improvement_component_score",
]
