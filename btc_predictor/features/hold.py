"""Versioned v1.2 Hold Score aggregation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from btc_predictor.config import StrategyConfig
from btc_predictor.config.strategy import HOLD_SCORE_CONTRACT_VERSION
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


HOLD_SCORE_FEATURE_ID = "HOLD_SCORE"
HOLD_SCORE_VERSION = HOLD_SCORE_CONTRACT_VERSION
HOLD_SCORE_COMPONENT_IDS = (
    "trend",
    "flow",
    "positioning",
    "structure",
    "momentum_persistence",
)
HOLD_SCORE_REASON_CODES = (
    "HOLD_SCORE_INPUT_MISSING",
    "HOLD_SCORE_COMPLETE",
)
HOLD_SCORE_WEIGHT_SUM_TOLERANCE = Decimal("0.000001")
REQUIRED_CONFIG_METADATA_KEYS = (
    "config_version",
    "strategy_version",
    "parameter_set_id",
)


@dataclass(frozen=True)
class HoldScoreInput:
    """Direct v1.2 component scores; Regime deliberately has no field."""

    trend_score: Decimal | None
    flow_score: Decimal | None
    positioning_score: Decimal | None
    structure_score: Decimal | None
    momentum_persistence_score: Decimal | None

    def as_record(self) -> dict[str, str | None]:
        return {
            "trend": _optional_score_record(self.trend_score, "trend"),
            "flow": _optional_score_record(self.flow_score, "flow"),
            "positioning": _optional_score_record(
                self.positioning_score,
                "positioning",
            ),
            "structure": _optional_score_record(self.structure_score, "structure"),
            "momentum_persistence": _optional_score_record(
                self.momentum_persistence_score,
                "momentum_persistence",
            ),
        }


@dataclass(frozen=True)
class HoldScoreResult:
    feature_id: str
    score_version: str
    parameter_status: str
    score: Decimal | None
    inputs: HoldScoreInput
    weights: dict[str, Decimal]
    contributions: dict[str, Decimal | None]
    missing_components: tuple[str, ...]
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        """Return a validated record sufficient to reconstruct the score."""

        if self.feature_id != HOLD_SCORE_FEATURE_ID:
            raise ValueError("feature_id must be HOLD_SCORE")
        if self.score_version != HOLD_SCORE_VERSION:
            raise ValueError(f"score_version must be {HOLD_SCORE_VERSION}")
        if self.parameter_status != SCORING_PARAMETER_STATUS:
            raise ValueError(
                f"parameter_status must be {SCORING_PARAMETER_STATUS}",
            )

        inputs = _input_values(self.inputs)
        weights = _normalize_weights(self.weights)
        metadata = _validate_config_metadata(self.config_metadata)
        if set(self.contributions) != set(HOLD_SCORE_COMPONENT_IDS):
            raise ValueError("contributions must exactly match Hold Score components")
        contributions = {
            component_id: (
                _non_negative_decimal(self.contributions[component_id], component_id)
                if self.contributions[component_id] is not None
                else None
            )
            for component_id in HOLD_SCORE_COMPONENT_IDS
        }
        expected_missing = tuple(
            component_id
            for component_id in HOLD_SCORE_COMPONENT_IDS
            if inputs[component_id] is None
        )
        contribution_missing = tuple(
            component_id
            for component_id in HOLD_SCORE_COMPONENT_IDS
            if contributions[component_id] is None
        )
        if self.missing_components != expected_missing:
            raise ValueError("missing_components do not match Hold Score inputs")
        if contribution_missing != expected_missing:
            raise ValueError("contributions do not match Hold Score inputs")
        if self.complete != (self.score is not None and not expected_missing):
            raise ValueError("complete state does not match Hold Score inputs")
        expected_reason_codes = (
            ("HOLD_SCORE_COMPLETE",)
            if self.complete
            else ("HOLD_SCORE_INPUT_MISSING",)
        )
        if self.reason_codes != expected_reason_codes:
            raise ValueError("reason_codes do not match Hold Score state")

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
class HoldScoreBatchResult:
    """Float64 batch output aligned to ``HOLD_SCORE_COMPONENT_IDS``."""

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


def calculate_hold_score(
    inputs: HoldScoreInput,
    *,
    strategy_config: StrategyConfig,
) -> HoldScoreResult:
    """Calculate one v1.2 Hold Score from direct component scores."""

    if not isinstance(inputs, HoldScoreInput):
        raise TypeError("inputs must be a HoldScoreInput")
    weights, metadata = _config_contract(strategy_config)
    input_values = _input_values(inputs)
    weighted = decimal_weighted_score(
        input_values,
        weights,
        component_ids=HOLD_SCORE_COMPONENT_IDS,
    )
    complete = weighted.score is not None
    reason_codes = (
        ("HOLD_SCORE_COMPLETE",)
        if complete
        else ("HOLD_SCORE_INPUT_MISSING",)
    )
    return HoldScoreResult(
        feature_id=HOLD_SCORE_FEATURE_ID,
        score_version=HOLD_SCORE_VERSION,
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


def calculate_hold_score_batch(
    values: ArrayLike,
    *,
    strategy_config: StrategyConfig,
) -> HoldScoreBatchResult:
    """Score one float64 row or a historical matrix in canonical column order."""

    weights, metadata = _config_contract(strategy_config)
    observations = as_float64_array(
        values,
        allow_empty=True,
        nan_policy="propagate",
    )
    available = observations[~np.isnan(observations)]
    if np.any((available < 0) | (available > 100)):
        raise NumericInputError("Hold Score components must be between 0 and 100")
    weighted = weighted_score(
        observations,
        {key: float(value) for key, value in weights.items()},
        component_names=HOLD_SCORE_COMPONENT_IDS,
    )
    return HoldScoreBatchResult(
        score_version=HOLD_SCORE_VERSION,
        parameter_status=SCORING_PARAMETER_STATUS,
        component_ids=HOLD_SCORE_COMPONENT_IDS,
        weights=weights,
        scores=weighted.scores,
        contributions=weighted.contributions,
        missing_mask=weighted.missing_mask,
        complete_mask=weighted.complete_mask,
        single_row=weighted.single_row,
        config_metadata=metadata,
    )


def _config_contract(
    strategy_config: StrategyConfig,
) -> tuple[dict[str, Decimal], dict[str, str]]:
    if not isinstance(strategy_config, StrategyConfig):
        raise TypeError("strategy_config must be a StrategyConfig")
    weights = _normalize_weights(strategy_config.scoring_weights.hold_score)
    metadata = _validate_config_metadata(strategy_config.run_metadata())
    return weights, metadata


def _normalize_weights(weights: Mapping[str, Any]) -> dict[str, Decimal]:
    missing = set(HOLD_SCORE_COMPONENT_IDS) - set(weights)
    extra = set(weights) - set(HOLD_SCORE_COMPONENT_IDS)
    if missing or extra:
        raise ValueError(
            "Hold Score weights must exactly match "
            f"{HOLD_SCORE_COMPONENT_IDS}; "
            f"missing={sorted(missing)}, extra={sorted(extra)}",
        )
    normalized = {
        component_id: _non_negative_decimal(weights[component_id], component_id)
        for component_id in HOLD_SCORE_COMPONENT_IDS
    }
    total = sum(normalized.values(), Decimal("0"))
    if abs(total - Decimal("1")) > HOLD_SCORE_WEIGHT_SUM_TOLERANCE:
        raise ValueError("Hold Score weights must sum to 1")
    return normalized


def _input_values(inputs: HoldScoreInput) -> dict[str, Decimal | None]:
    values = {
        "trend": inputs.trend_score,
        "flow": inputs.flow_score,
        "positioning": inputs.positioning_score,
        "structure": inputs.structure_score,
        "momentum_persistence": inputs.momentum_persistence_score,
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
    "HOLD_SCORE_COMPONENT_IDS",
    "HOLD_SCORE_FEATURE_ID",
    "HOLD_SCORE_REASON_CODES",
    "HOLD_SCORE_VERSION",
    "HOLD_SCORE_WEIGHT_SUM_TOLERANCE",
    "HoldScoreBatchResult",
    "HoldScoreInput",
    "HoldScoreResult",
    "calculate_hold_score",
    "calculate_hold_score_batch",
]
