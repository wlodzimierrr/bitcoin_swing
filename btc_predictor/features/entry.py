"""Versioned Entry Conviction scoring."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from btc_predictor.config import StrategyConfig
from btc_predictor.config.strategy import ENTRY_CONVICTION_CONTRACT_VERSION
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


ENTRY_CONVICTION_FEATURE_ID = "ENTRY_CONVICTION"
ENTRY_CONVICTION_SCORE_VERSION = ENTRY_CONVICTION_CONTRACT_VERSION
ENTRY_CONVICTION_COMPONENT_IDS = (
    "trend",
    "flow",
    "positioning",
    "volatility",
    "structure",
)
ENTRY_CONVICTION_REASON_CODES = (
    "ENTRY_CONVICTION_INPUT_MISSING",
    "ENTRY_CONVICTION_COMPLETE",
)
ENTRY_CONVICTION_WEIGHT_SUM_TOLERANCE = Decimal("0.000001")
REQUIRED_CONFIG_METADATA_KEYS = (
    "config_version",
    "strategy_version",
    "parameter_set_id",
)


@dataclass(frozen=True)
class EntryConvictionInput:
    """Direct v1.2 component scores; Regime deliberately has no field."""

    trend_score: Decimal | None
    flow_score: Decimal | None
    positioning_score: Decimal | None
    volatility_score: Decimal | None
    structure_score: Decimal | None

    def as_record(self) -> dict[str, str | None]:
        return {
            "trend": _optional_score_record(self.trend_score, "trend"),
            "flow": _optional_score_record(self.flow_score, "flow"),
            "positioning": _optional_score_record(
                self.positioning_score,
                "positioning",
            ),
            "volatility": _optional_score_record(
                self.volatility_score,
                "volatility",
            ),
            "structure": _optional_score_record(self.structure_score, "structure"),
        }


@dataclass(frozen=True)
class EntryConvictionResult:
    feature_id: str
    score_version: str
    parameter_status: str
    score: Decimal | None
    inputs: EntryConvictionInput
    weights: dict[str, Decimal]
    contributions: dict[str, Decimal | None]
    missing_components: tuple[str, ...]
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        """Return a validated record sufficient to reconstruct the score."""

        if self.feature_id != ENTRY_CONVICTION_FEATURE_ID:
            raise ValueError("feature_id must be ENTRY_CONVICTION")
        if self.score_version != ENTRY_CONVICTION_SCORE_VERSION:
            raise ValueError(
                f"score_version must be {ENTRY_CONVICTION_SCORE_VERSION}",
            )
        if self.parameter_status != SCORING_PARAMETER_STATUS:
            raise ValueError(
                f"parameter_status must be {SCORING_PARAMETER_STATUS}",
            )

        inputs = _input_values(self.inputs)
        weights = _normalize_weights(self.weights)
        metadata = _validate_config_metadata(self.config_metadata)
        if set(self.contributions) != set(ENTRY_CONVICTION_COMPONENT_IDS):
            raise ValueError(
                "contributions must exactly match Entry Conviction components",
            )
        contributions = {
            component_id: (
                _non_negative_decimal(self.contributions[component_id], component_id)
                if self.contributions[component_id] is not None
                else None
            )
            for component_id in ENTRY_CONVICTION_COMPONENT_IDS
        }
        expected_missing = tuple(
            component_id
            for component_id in ENTRY_CONVICTION_COMPONENT_IDS
            if inputs[component_id] is None
        )
        if self.missing_components != expected_missing:
            raise ValueError("missing_components do not match Entry Conviction inputs")
        if self.complete != (self.score is not None and not expected_missing):
            raise ValueError("complete state does not match Entry Conviction inputs")

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
class EntryConvictionBatchResult:
    """Float64 batch output aligned to ``ENTRY_CONVICTION_COMPONENT_IDS``."""

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


def calculate_entry_conviction(
    inputs: EntryConvictionInput,
    *,
    strategy_config: StrategyConfig,
) -> EntryConvictionResult:
    """Calculate one v1.2 Entry Conviction score from direct components."""

    if not isinstance(inputs, EntryConvictionInput):
        raise TypeError("inputs must be an EntryConvictionInput")
    weights, metadata = _config_contract(strategy_config)
    input_values = _input_values(inputs)
    weighted = decimal_weighted_score(
        input_values,
        weights,
        component_ids=ENTRY_CONVICTION_COMPONENT_IDS,
    )
    complete = weighted.score is not None
    reason_codes = (
        ("ENTRY_CONVICTION_COMPLETE",)
        if complete
        else ("ENTRY_CONVICTION_INPUT_MISSING",)
    )
    return EntryConvictionResult(
        feature_id=ENTRY_CONVICTION_FEATURE_ID,
        score_version=ENTRY_CONVICTION_SCORE_VERSION,
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


def calculate_entry_conviction_batch(
    values: ArrayLike,
    *,
    strategy_config: StrategyConfig,
) -> EntryConvictionBatchResult:
    """Score one float64 row or a historical matrix in canonical column order."""

    weights, metadata = _config_contract(strategy_config)
    observations = as_float64_array(
        values,
        allow_empty=True,
        nan_policy="propagate",
    )
    available = observations[~np.isnan(observations)]
    if np.any((available < 0) | (available > 100)):
        raise NumericInputError(
            "Entry Conviction component scores must be between 0 and 100",
        )
    weighted = weighted_score(
        observations,
        {key: float(value) for key, value in weights.items()},
        component_names=ENTRY_CONVICTION_COMPONENT_IDS,
    )
    return EntryConvictionBatchResult(
        score_version=ENTRY_CONVICTION_SCORE_VERSION,
        parameter_status=SCORING_PARAMETER_STATUS,
        component_ids=ENTRY_CONVICTION_COMPONENT_IDS,
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
    weights = _normalize_weights(strategy_config.scoring_weights.entry_conviction)
    metadata = _validate_config_metadata(strategy_config.run_metadata())
    return weights, metadata


def _normalize_weights(weights: Mapping[str, Any]) -> dict[str, Decimal]:
    missing = set(ENTRY_CONVICTION_COMPONENT_IDS) - set(weights)
    extra = set(weights) - set(ENTRY_CONVICTION_COMPONENT_IDS)
    if missing or extra:
        raise ValueError(
            "Entry Conviction weights must exactly match "
            f"{ENTRY_CONVICTION_COMPONENT_IDS}; "
            f"missing={sorted(missing)}, extra={sorted(extra)}",
        )
    normalized = {
        component_id: _non_negative_decimal(weights[component_id], component_id)
        for component_id in ENTRY_CONVICTION_COMPONENT_IDS
    }
    total = sum(normalized.values(), Decimal("0"))
    if abs(total - Decimal("1")) > ENTRY_CONVICTION_WEIGHT_SUM_TOLERANCE:
        raise ValueError("Entry Conviction weights must sum to 1")
    return normalized


def _input_values(
    inputs: EntryConvictionInput,
) -> dict[str, Decimal | None]:
    values = {
        "trend": inputs.trend_score,
        "flow": inputs.flow_score,
        "positioning": inputs.positioning_score,
        "volatility": inputs.volatility_score,
        "structure": inputs.structure_score,
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
