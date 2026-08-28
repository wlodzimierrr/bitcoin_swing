"""Setup detector helpers."""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from btc_predictor.data import require_utc_datetime


BULL_TREND_CONTINUATION_SETUP = "BULL_TREND_CONTINUATION"
BULL_TREND_CONTINUATION_FEATURE_ID = "SETUP_BULL_TREND_CONTINUATION"
BULLISH_RESET_SETUP = "BULLISH_RESET"
BULLISH_RESET_FEATURE_ID = "SETUP_BULLISH_RESET"
CAPITULATION_REVERSAL_SETUP = "CAPITULATION_REVERSAL"
CAPITULATION_REVERSAL_FEATURE_ID = "SETUP_CAPITULATION_REVERSAL"
BULL_TREND_CONTINUATION_REQUIREMENT_KEYS = (
    "regime_min",
    "trend_min",
    "flow_min",
    "positioning_min",
    "structure_min",
    "minimum_rr",
    "require_no_stress",
    "require_no_severe_crowding",
)
BULL_TREND_CONTINUATION_REASON_CODES = (
    "BULL_TREND_CONTINUATION_INPUT_MISSING",
    "BULL_TREND_CONTINUATION_REGIME_TOO_LOW",
    "BULL_TREND_CONTINUATION_TREND_TOO_LOW",
    "BULL_TREND_CONTINUATION_FLOW_TOO_LOW",
    "BULL_TREND_CONTINUATION_POSITIONING_TOO_LOW",
    "BULL_TREND_CONTINUATION_STRUCTURE_TOO_LOW",
    "BULL_TREND_CONTINUATION_STRESS_ACTIVE",
    "BULL_TREND_CONTINUATION_SEVERE_CROWDING_ACTIVE",
    "BULL_TREND_CONTINUATION_RR_TOO_LOW",
)
DEFAULT_BULL_TREND_CONTINUATION_REQUIREMENTS = {
    "regime_min": Decimal("65"),
    "trend_min": Decimal("70"),
    "flow_min": Decimal("55"),
    "positioning_min": Decimal("60"),
    "structure_min": Decimal("70"),
    "minimum_rr": Decimal("2"),
    "require_no_stress": True,
    "require_no_severe_crowding": True,
}
BULLISH_RESET_REQUIREMENT_KEYS = (
    "regime_min",
    "trend_min",
    "correction_min_fraction",
    "correction_max_fraction",
    "funding_health_improving_days",
    "oi_health_stable_days",
    "flow_accel_improving_days",
    "structure_min",
    "entry_trigger_required",
    "entry_conviction_min",
    "minimum_rr",
)
BULLISH_RESET_REASON_CODES = (
    "BULLISH_RESET_INPUT_MISSING",
    "BULLISH_RESET_REGIME_TOO_LOW",
    "BULLISH_RESET_TREND_TOO_LOW",
    "BULLISH_RESET_CORRECTION_TOO_SHALLOW",
    "BULLISH_RESET_CORRECTION_TOO_DEEP",
    "BULLISH_RESET_FUNDING_HEALTH_HISTORY_INSUFFICIENT",
    "BULLISH_RESET_FUNDING_HEALTH_NOT_IMPROVING",
    "BULLISH_RESET_OI_HEALTH_HISTORY_INSUFFICIENT",
    "BULLISH_RESET_OI_HEALTH_DETERIORATING",
    "BULLISH_RESET_FLOW_ACCEL_HISTORY_INSUFFICIENT",
    "BULLISH_RESET_FLOW_ACCEL_NOT_IMPROVING",
    "BULLISH_RESET_STRUCTURE_TOO_LOW",
    "BULLISH_RESET_ENTRY_TRIGGER_NOT_CONFIRMED",
    "BULLISH_RESET_ENTRY_CONVICTION_TOO_LOW",
    "BULLISH_RESET_RR_TOO_LOW",
)
DEFAULT_BULLISH_RESET_REQUIREMENTS = {
    "regime_min": Decimal("55"),
    "trend_min": Decimal("55"),
    "correction_min_fraction": Decimal("0.08"),
    "correction_max_fraction": Decimal("0.25"),
    "funding_health_improving_days": 7,
    "oi_health_stable_days": 7,
    "flow_accel_improving_days": 5,
    "structure_min": Decimal("70"),
    "entry_trigger_required": True,
    "entry_conviction_min": Decimal("80"),
    "minimum_rr": Decimal("2"),
}
CAPITULATION_REVERSAL_REQUIREMENT_KEYS = (
    "capitulation_required",
    "confirmation_required",
    "confirmation_must_follow_capitulation",
    "max_confirmation_lag_days",
    "structure_min",
    "entry_conviction_min",
    "minimum_rr",
)
CAPITULATION_REVERSAL_REASON_CODES = (
    "CAPITULATION_REVERSAL_INPUT_MISSING",
    "CAPITULATION_REVERSAL_CAPITULATION_NOT_ACTIVE",
    "CAPITULATION_REVERSAL_CONFIRMATION_MISSING",
    "CAPITULATION_REVERSAL_CONFIRMATION_BEFORE_CAPITULATION",
    "CAPITULATION_REVERSAL_CONFIRMATION_TOO_STALE",
    "CAPITULATION_REVERSAL_STRUCTURE_TOO_LOW",
    "CAPITULATION_REVERSAL_ENTRY_CONVICTION_TOO_LOW",
    "CAPITULATION_REVERSAL_RR_TOO_LOW",
)
DEFAULT_CAPITULATION_REVERSAL_REQUIREMENTS = {
    "capitulation_required": True,
    "confirmation_required": True,
    "confirmation_must_follow_capitulation": True,
    "max_confirmation_lag_days": 14,
    "structure_min": Decimal("60"),
    "entry_conviction_min": Decimal("80"),
    "minimum_rr": Decimal("2"),
}


@dataclass(frozen=True)
class BullTrendContinuationInput:
    regime_score: Decimal | None
    trend_score: Decimal | None
    flow_score: Decimal | None
    positioning_score: Decimal | None
    structure_score: Decimal | None
    stress_flagged: bool | None
    severe_crowding_flagged: bool | None
    risk_reward: Decimal | None

    def as_record(self) -> dict[str, str | bool | None]:
        return {
            "regime_score": _optional_score_record(self.regime_score, "regime_score"),
            "trend_score": _optional_score_record(self.trend_score, "trend_score"),
            "flow_score": _optional_score_record(self.flow_score, "flow_score"),
            "positioning_score": _optional_score_record(
                self.positioning_score,
                "positioning_score",
            ),
            "structure_score": _optional_score_record(
                self.structure_score,
                "structure_score",
            ),
            "stress_flagged": _optional_bool_record(
                self.stress_flagged,
                "stress_flagged",
            ),
            "severe_crowding_flagged": _optional_bool_record(
                self.severe_crowding_flagged,
                "severe_crowding_flagged",
            ),
            "risk_reward": (
                str(_non_negative_decimal(self.risk_reward, "risk_reward"))
                if self.risk_reward is not None
                else None
            ),
        }


@dataclass(frozen=True)
class BullishResetInput:
    regime_score: Decimal | None
    trend_score: Decimal | None
    correction_from_local_high_fraction: Decimal | None
    funding_health_history: Sequence[Decimal | None] | None
    oi_health_history: Sequence[Decimal | None] | None
    flow_accel_history: Sequence[Decimal | None] | None
    structure_score: Decimal | None
    entry_trigger_confirmed: bool | None
    entry_conviction_score: Decimal | None
    risk_reward: Decimal | None

    def as_record(self) -> dict[str, str | bool | list[str | None] | None]:
        return {
            "regime_score": _optional_score_record(self.regime_score, "regime_score"),
            "trend_score": _optional_score_record(self.trend_score, "trend_score"),
            "correction_from_local_high_fraction": (
                str(
                    _non_negative_decimal(
                        self.correction_from_local_high_fraction,
                        "correction_from_local_high_fraction",
                    )
                )
                if self.correction_from_local_high_fraction is not None
                else None
            ),
            "funding_health_history": _optional_score_series_record(
                self.funding_health_history,
                "funding_health_history",
            ),
            "oi_health_history": _optional_score_series_record(
                self.oi_health_history,
                "oi_health_history",
            ),
            "flow_accel_history": _optional_decimal_series_record(
                self.flow_accel_history,
                "flow_accel_history",
            ),
            "structure_score": _optional_score_record(
                self.structure_score,
                "structure_score",
            ),
            "entry_trigger_confirmed": _optional_bool_record(
                self.entry_trigger_confirmed,
                "entry_trigger_confirmed",
            ),
            "entry_conviction_score": _optional_score_record(
                self.entry_conviction_score,
                "entry_conviction_score",
            ),
            "risk_reward": (
                str(_non_negative_decimal(self.risk_reward, "risk_reward"))
                if self.risk_reward is not None
                else None
            ),
        }


@dataclass(frozen=True)
class CapitulationReversalInput:
    capitulation_flagged: bool | None
    capitulation_detected_at: datetime | None
    confirmation_triggered: bool | None
    confirmation_at: datetime | None
    structure_score: Decimal | None
    entry_conviction_score: Decimal | None
    risk_reward: Decimal | None

    def as_record(self) -> dict[str, str | bool | None]:
        return {
            "capitulation_flagged": _optional_bool_record(
                self.capitulation_flagged,
                "capitulation_flagged",
            ),
            "capitulation_detected_at": _optional_utc_datetime_record(
                self.capitulation_detected_at,
                "capitulation_detected_at",
            ),
            "confirmation_triggered": _optional_bool_record(
                self.confirmation_triggered,
                "confirmation_triggered",
            ),
            "confirmation_at": _optional_utc_datetime_record(
                self.confirmation_at,
                "confirmation_at",
            ),
            "structure_score": _optional_score_record(
                self.structure_score,
                "structure_score",
            ),
            "entry_conviction_score": _optional_score_record(
                self.entry_conviction_score,
                "entry_conviction_score",
            ),
            "risk_reward": (
                str(_non_negative_decimal(self.risk_reward, "risk_reward"))
                if self.risk_reward is not None
                else None
            ),
        }


@dataclass(frozen=True)
class BullTrendContinuationResult:
    feature_id: str
    setup: str
    detected: bool
    inputs: BullTrendContinuationInput
    requirements: dict[str, Decimal | bool]
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...] = ()

    @property
    def reason_code(self) -> str | None:
        if self.detected:
            return f"{self.feature_id}_VALID"
        if self.reason_codes:
            return self.reason_codes[0]
        return None

    def as_record(self) -> dict[str, Any]:
        if self.feature_id != BULL_TREND_CONTINUATION_FEATURE_ID:
            raise ValueError("feature_id must be SETUP_BULL_TREND_CONTINUATION")
        if self.setup != BULL_TREND_CONTINUATION_SETUP:
            raise ValueError("setup must be BULL_TREND_CONTINUATION")
        normalized_requirements = _normalize_bull_trend_requirements(self.requirements)
        self.inputs.as_record()
        return {
            "feature_id": self.feature_id,
            "setup": self.setup,
            "detected": self.detected,
            "reason_code": self.reason_code,
            "inputs": self.inputs.as_record(),
            "requirements": {
                key: str(value) if isinstance(value, Decimal) else value
                for key, value in normalized_requirements.items()
            },
            "config_metadata": dict(self.config_metadata),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class BullishResetResult:
    feature_id: str
    setup: str
    detected: bool
    inputs: BullishResetInput
    requirements: dict[str, Decimal | int | bool]
    comparisons: dict[str, str | None]
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...] = ()

    @property
    def reason_code(self) -> str | None:
        if self.detected:
            return f"{self.feature_id}_VALID"
        if self.reason_codes:
            return self.reason_codes[0]
        return None

    def as_record(self) -> dict[str, Any]:
        if self.feature_id != BULLISH_RESET_FEATURE_ID:
            raise ValueError("feature_id must be SETUP_BULLISH_RESET")
        if self.setup != BULLISH_RESET_SETUP:
            raise ValueError("setup must be BULLISH_RESET")
        normalized_requirements = _normalize_bullish_reset_requirements(
            self.requirements,
        )
        self.inputs.as_record()
        return {
            "feature_id": self.feature_id,
            "setup": self.setup,
            "detected": self.detected,
            "reason_code": self.reason_code,
            "inputs": self.inputs.as_record(),
            "requirements": {
                key: str(value) if isinstance(value, Decimal) else value
                for key, value in normalized_requirements.items()
            },
            "comparisons": dict(self.comparisons),
            "config_metadata": dict(self.config_metadata),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class CapitulationReversalResult:
    feature_id: str
    setup: str
    detected: bool
    inputs: CapitulationReversalInput
    requirements: dict[str, Decimal | int | bool]
    confirmation_lag_days: Decimal | None
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...] = ()

    @property
    def reason_code(self) -> str | None:
        if self.detected:
            return f"{self.feature_id}_VALID"
        if self.reason_codes:
            return self.reason_codes[0]
        return None

    def as_record(self) -> dict[str, Any]:
        if self.feature_id != CAPITULATION_REVERSAL_FEATURE_ID:
            raise ValueError("feature_id must be SETUP_CAPITULATION_REVERSAL")
        if self.setup != CAPITULATION_REVERSAL_SETUP:
            raise ValueError("setup must be CAPITULATION_REVERSAL")
        normalized_requirements = _normalize_capitulation_reversal_requirements(
            self.requirements,
        )
        self.inputs.as_record()
        return {
            "feature_id": self.feature_id,
            "setup": self.setup,
            "detected": self.detected,
            "reason_code": self.reason_code,
            "inputs": self.inputs.as_record(),
            "requirements": {
                key: str(value) if isinstance(value, Decimal) else value
                for key, value in normalized_requirements.items()
            },
            "confirmation_lag_days": (
                str(self.confirmation_lag_days)
                if self.confirmation_lag_days is not None
                else None
            ),
            "config_metadata": dict(self.config_metadata),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def detect_bull_trend_continuation(
    inputs: BullTrendContinuationInput,
    *,
    requirements: Mapping[str, Any] | None = None,
    config_metadata: Mapping[str, str] | None = None,
) -> BullTrendContinuationResult:
    """Evaluate the Bull Trend Continuation hard filters."""

    normalized_requirements = _normalize_bull_trend_requirements(
        requirements
        if requirements is not None
        else DEFAULT_BULL_TREND_CONTINUATION_REQUIREMENTS,
    )
    input_values = _bull_trend_input_values(inputs)
    reason_codes = []

    if any(value is None for value in input_values.values()):
        reason_codes.append("BULL_TREND_CONTINUATION_INPUT_MISSING")
    _append_score_failure(
        reason_codes,
        value=inputs.regime_score,
        minimum=normalized_requirements["regime_min"],
        reason_code="BULL_TREND_CONTINUATION_REGIME_TOO_LOW",
    )
    _append_score_failure(
        reason_codes,
        value=inputs.trend_score,
        minimum=normalized_requirements["trend_min"],
        reason_code="BULL_TREND_CONTINUATION_TREND_TOO_LOW",
    )
    _append_score_failure(
        reason_codes,
        value=inputs.flow_score,
        minimum=normalized_requirements["flow_min"],
        reason_code="BULL_TREND_CONTINUATION_FLOW_TOO_LOW",
    )
    _append_score_failure(
        reason_codes,
        value=inputs.positioning_score,
        minimum=normalized_requirements["positioning_min"],
        reason_code="BULL_TREND_CONTINUATION_POSITIONING_TOO_LOW",
    )
    _append_score_failure(
        reason_codes,
        value=inputs.structure_score,
        minimum=normalized_requirements["structure_min"],
        reason_code="BULL_TREND_CONTINUATION_STRUCTURE_TOO_LOW",
    )
    if normalized_requirements["require_no_stress"] and inputs.stress_flagged is True:
        reason_codes.append("BULL_TREND_CONTINUATION_STRESS_ACTIVE")
    if (
        normalized_requirements["require_no_severe_crowding"]
        and inputs.severe_crowding_flagged is True
    ):
        reason_codes.append("BULL_TREND_CONTINUATION_SEVERE_CROWDING_ACTIVE")
    if (
        inputs.risk_reward is not None
        and inputs.risk_reward < normalized_requirements["minimum_rr"]
    ):
        reason_codes.append("BULL_TREND_CONTINUATION_RR_TOO_LOW")

    reason_codes = _dedupe_reason_codes(reason_codes)
    return BullTrendContinuationResult(
        feature_id=BULL_TREND_CONTINUATION_FEATURE_ID,
        setup=BULL_TREND_CONTINUATION_SETUP,
        detected=not reason_codes,
        inputs=inputs,
        requirements=normalized_requirements,
        config_metadata=dict(config_metadata or {}),
        complete="BULL_TREND_CONTINUATION_INPUT_MISSING" not in reason_codes,
        reason_codes=reason_codes,
    )


def detect_bullish_reset(
    inputs: BullishResetInput,
    *,
    requirements: Mapping[str, Any] | None = None,
    config_metadata: Mapping[str, str] | None = None,
) -> BullishResetResult:
    """Evaluate the Bullish Reset hard filters."""

    normalized_requirements = _normalize_bullish_reset_requirements(
        requirements
        if requirements is not None
        else DEFAULT_BULLISH_RESET_REQUIREMENTS,
    )
    input_values = _bullish_reset_input_values(inputs)
    reason_codes = []

    if any(value is None for value in input_values.values()):
        reason_codes.append("BULLISH_RESET_INPUT_MISSING")
    _append_score_failure(
        reason_codes,
        value=inputs.regime_score,
        minimum=normalized_requirements["regime_min"],
        reason_code="BULLISH_RESET_REGIME_TOO_LOW",
    )
    _append_score_failure(
        reason_codes,
        value=inputs.trend_score,
        minimum=normalized_requirements["trend_min"],
        reason_code="BULLISH_RESET_TREND_TOO_LOW",
    )
    if inputs.correction_from_local_high_fraction is not None:
        correction = _non_negative_decimal(
            inputs.correction_from_local_high_fraction,
            "correction_from_local_high_fraction",
        )
        if correction < normalized_requirements["correction_min_fraction"]:
            reason_codes.append("BULLISH_RESET_CORRECTION_TOO_SHALLOW")
        if correction > normalized_requirements["correction_max_fraction"]:
            reason_codes.append("BULLISH_RESET_CORRECTION_TOO_DEEP")

    comparisons = {
        "funding_health": _series_delta_record(
            inputs.funding_health_history,
            normalized_requirements["funding_health_improving_days"],
        ),
        "oi_health": _series_delta_record(
            inputs.oi_health_history,
            normalized_requirements["oi_health_stable_days"],
        ),
        "flow_accel": _series_delta_record(
            inputs.flow_accel_history,
            normalized_requirements["flow_accel_improving_days"],
        ),
    }
    _append_history_failure(
        reason_codes,
        values=inputs.funding_health_history,
        lookback=normalized_requirements["funding_health_improving_days"],
        insufficient_reason_code="BULLISH_RESET_FUNDING_HEALTH_HISTORY_INSUFFICIENT",
        failed_reason_code="BULLISH_RESET_FUNDING_HEALTH_NOT_IMPROVING",
        allow_equal=False,
    )
    _append_history_failure(
        reason_codes,
        values=inputs.oi_health_history,
        lookback=normalized_requirements["oi_health_stable_days"],
        insufficient_reason_code="BULLISH_RESET_OI_HEALTH_HISTORY_INSUFFICIENT",
        failed_reason_code="BULLISH_RESET_OI_HEALTH_DETERIORATING",
        allow_equal=True,
    )
    _append_history_failure(
        reason_codes,
        values=inputs.flow_accel_history,
        lookback=normalized_requirements["flow_accel_improving_days"],
        insufficient_reason_code="BULLISH_RESET_FLOW_ACCEL_HISTORY_INSUFFICIENT",
        failed_reason_code="BULLISH_RESET_FLOW_ACCEL_NOT_IMPROVING",
        allow_equal=False,
    )
    _append_score_failure(
        reason_codes,
        value=inputs.structure_score,
        minimum=normalized_requirements["structure_min"],
        reason_code="BULLISH_RESET_STRUCTURE_TOO_LOW",
    )
    if (
        normalized_requirements["entry_trigger_required"]
        and inputs.entry_trigger_confirmed is not True
        and inputs.entry_trigger_confirmed is not None
    ):
        reason_codes.append("BULLISH_RESET_ENTRY_TRIGGER_NOT_CONFIRMED")
    _append_score_failure(
        reason_codes,
        value=inputs.entry_conviction_score,
        minimum=normalized_requirements["entry_conviction_min"],
        reason_code="BULLISH_RESET_ENTRY_CONVICTION_TOO_LOW",
    )
    if (
        inputs.risk_reward is not None
        and inputs.risk_reward < normalized_requirements["minimum_rr"]
    ):
        reason_codes.append("BULLISH_RESET_RR_TOO_LOW")

    reason_codes = _dedupe_reason_codes(reason_codes)
    return BullishResetResult(
        feature_id=BULLISH_RESET_FEATURE_ID,
        setup=BULLISH_RESET_SETUP,
        detected=not reason_codes,
        inputs=inputs,
        requirements=normalized_requirements,
        comparisons=comparisons,
        config_metadata=dict(config_metadata or {}),
        complete=not any(
            reason_code.endswith("_INPUT_MISSING")
            or reason_code.endswith("_HISTORY_INSUFFICIENT")
            for reason_code in reason_codes
        ),
        reason_codes=reason_codes,
    )


def detect_capitulation_reversal(
    inputs: CapitulationReversalInput,
    *,
    requirements: Mapping[str, Any] | None = None,
    config_metadata: Mapping[str, str] | None = None,
) -> CapitulationReversalResult:
    """Evaluate confirmation after a capitulation event."""

    normalized_requirements = _normalize_capitulation_reversal_requirements(
        requirements
        if requirements is not None
        else DEFAULT_CAPITULATION_REVERSAL_REQUIREMENTS,
    )
    input_values = _capitulation_reversal_input_values(inputs)
    reason_codes = []

    if any(value is None for value in input_values.values()):
        reason_codes.append("CAPITULATION_REVERSAL_INPUT_MISSING")
    if (
        normalized_requirements["capitulation_required"]
        and inputs.capitulation_flagged is False
    ):
        reason_codes.append("CAPITULATION_REVERSAL_CAPITULATION_NOT_ACTIVE")
    if (
        normalized_requirements["confirmation_required"]
        and inputs.confirmation_triggered is False
    ):
        reason_codes.append("CAPITULATION_REVERSAL_CONFIRMATION_MISSING")

    confirmation_lag_days = _confirmation_lag_days(
        inputs.capitulation_detected_at,
        inputs.confirmation_at,
    )
    if confirmation_lag_days is not None:
        if (
            normalized_requirements["confirmation_must_follow_capitulation"]
            and confirmation_lag_days < 0
        ):
            reason_codes.append(
                "CAPITULATION_REVERSAL_CONFIRMATION_BEFORE_CAPITULATION",
            )
        if confirmation_lag_days > normalized_requirements["max_confirmation_lag_days"]:
            reason_codes.append("CAPITULATION_REVERSAL_CONFIRMATION_TOO_STALE")

    _append_score_failure(
        reason_codes,
        value=inputs.structure_score,
        minimum=normalized_requirements["structure_min"],
        reason_code="CAPITULATION_REVERSAL_STRUCTURE_TOO_LOW",
    )
    _append_score_failure(
        reason_codes,
        value=inputs.entry_conviction_score,
        minimum=normalized_requirements["entry_conviction_min"],
        reason_code="CAPITULATION_REVERSAL_ENTRY_CONVICTION_TOO_LOW",
    )
    if (
        inputs.risk_reward is not None
        and inputs.risk_reward < normalized_requirements["minimum_rr"]
    ):
        reason_codes.append("CAPITULATION_REVERSAL_RR_TOO_LOW")

    reason_codes = _dedupe_reason_codes(reason_codes)
    return CapitulationReversalResult(
        feature_id=CAPITULATION_REVERSAL_FEATURE_ID,
        setup=CAPITULATION_REVERSAL_SETUP,
        detected=not reason_codes,
        inputs=inputs,
        requirements=normalized_requirements,
        confirmation_lag_days=confirmation_lag_days,
        config_metadata=dict(config_metadata or {}),
        complete="CAPITULATION_REVERSAL_INPUT_MISSING" not in reason_codes,
        reason_codes=reason_codes,
    )


def _normalize_bull_trend_requirements(
    requirements: Mapping[str, Any],
) -> dict[str, Decimal | bool]:
    missing = set(BULL_TREND_CONTINUATION_REQUIREMENT_KEYS) - set(requirements)
    if missing:
        raise ValueError(
            "bull trend continuation requirements missing "
            f"{sorted(missing)}",
        )
    normalized: dict[str, Decimal | bool] = {
        "regime_min": _score(requirements["regime_min"], "regime_min"),
        "trend_min": _score(requirements["trend_min"], "trend_min"),
        "flow_min": _score(requirements["flow_min"], "flow_min"),
        "positioning_min": _score(
            requirements["positioning_min"],
            "positioning_min",
        ),
        "structure_min": _score(requirements["structure_min"], "structure_min"),
        "minimum_rr": _positive_decimal(requirements["minimum_rr"], "minimum_rr"),
        "require_no_stress": _bool(
            requirements["require_no_stress"],
            "require_no_stress",
        ),
        "require_no_severe_crowding": _bool(
            requirements["require_no_severe_crowding"],
            "require_no_severe_crowding",
        ),
    }
    return normalized


def _normalize_bullish_reset_requirements(
    requirements: Mapping[str, Any],
) -> dict[str, Decimal | int | bool]:
    missing = set(BULLISH_RESET_REQUIREMENT_KEYS) - set(requirements)
    if missing:
        raise ValueError(f"bullish reset requirements missing {sorted(missing)}")
    correction_min = _fraction(
        requirements["correction_min_fraction"],
        "correction_min_fraction",
    )
    correction_max = _fraction(
        requirements["correction_max_fraction"],
        "correction_max_fraction",
    )
    if correction_max <= correction_min:
        raise ValueError("correction_max_fraction must be > correction_min_fraction")
    return {
        "regime_min": _score(requirements["regime_min"], "regime_min"),
        "trend_min": _score(requirements["trend_min"], "trend_min"),
        "correction_min_fraction": correction_min,
        "correction_max_fraction": correction_max,
        "funding_health_improving_days": _positive_int(
            requirements["funding_health_improving_days"],
            "funding_health_improving_days",
        ),
        "oi_health_stable_days": _positive_int(
            requirements["oi_health_stable_days"],
            "oi_health_stable_days",
        ),
        "flow_accel_improving_days": _positive_int(
            requirements["flow_accel_improving_days"],
            "flow_accel_improving_days",
        ),
        "structure_min": _score(requirements["structure_min"], "structure_min"),
        "entry_trigger_required": _bool(
            requirements["entry_trigger_required"],
            "entry_trigger_required",
        ),
        "entry_conviction_min": _score(
            requirements["entry_conviction_min"],
            "entry_conviction_min",
        ),
        "minimum_rr": _positive_decimal(requirements["minimum_rr"], "minimum_rr"),
    }


def _normalize_capitulation_reversal_requirements(
    requirements: Mapping[str, Any],
) -> dict[str, Decimal | int | bool]:
    missing = set(CAPITULATION_REVERSAL_REQUIREMENT_KEYS) - set(requirements)
    if missing:
        raise ValueError(
            f"capitulation reversal requirements missing {sorted(missing)}",
        )
    return {
        "capitulation_required": _bool(
            requirements["capitulation_required"],
            "capitulation_required",
        ),
        "confirmation_required": _bool(
            requirements["confirmation_required"],
            "confirmation_required",
        ),
        "confirmation_must_follow_capitulation": _bool(
            requirements["confirmation_must_follow_capitulation"],
            "confirmation_must_follow_capitulation",
        ),
        "max_confirmation_lag_days": _positive_int(
            requirements["max_confirmation_lag_days"],
            "max_confirmation_lag_days",
        ),
        "structure_min": _score(requirements["structure_min"], "structure_min"),
        "entry_conviction_min": _score(
            requirements["entry_conviction_min"],
            "entry_conviction_min",
        ),
        "minimum_rr": _positive_decimal(requirements["minimum_rr"], "minimum_rr"),
    }


def _bull_trend_input_values(
    inputs: BullTrendContinuationInput,
) -> dict[str, Decimal | bool | None]:
    inputs.as_record()
    return {
        "regime_score": inputs.regime_score,
        "trend_score": inputs.trend_score,
        "flow_score": inputs.flow_score,
        "positioning_score": inputs.positioning_score,
        "structure_score": inputs.structure_score,
        "stress_flagged": inputs.stress_flagged,
        "severe_crowding_flagged": inputs.severe_crowding_flagged,
        "risk_reward": inputs.risk_reward,
    }


def _bullish_reset_input_values(
    inputs: BullishResetInput,
) -> dict[str, Decimal | bool | Sequence[Decimal | None] | None]:
    inputs.as_record()
    return {
        "regime_score": inputs.regime_score,
        "trend_score": inputs.trend_score,
        "correction_from_local_high_fraction": (
            inputs.correction_from_local_high_fraction
        ),
        "funding_health_history": inputs.funding_health_history,
        "oi_health_history": inputs.oi_health_history,
        "flow_accel_history": inputs.flow_accel_history,
        "structure_score": inputs.structure_score,
        "entry_trigger_confirmed": inputs.entry_trigger_confirmed,
        "entry_conviction_score": inputs.entry_conviction_score,
        "risk_reward": inputs.risk_reward,
    }


def _capitulation_reversal_input_values(
    inputs: CapitulationReversalInput,
) -> dict[str, Decimal | bool | datetime | None]:
    inputs.as_record()
    return {
        "capitulation_flagged": inputs.capitulation_flagged,
        "capitulation_detected_at": inputs.capitulation_detected_at,
        "confirmation_triggered": inputs.confirmation_triggered,
        "confirmation_at": inputs.confirmation_at,
        "structure_score": inputs.structure_score,
        "entry_conviction_score": inputs.entry_conviction_score,
        "risk_reward": inputs.risk_reward,
    }


def _append_score_failure(
    reason_codes: list[str],
    *,
    value: Decimal | None,
    minimum: Decimal | bool,
    reason_code: str,
) -> None:
    if not isinstance(minimum, Decimal):
        raise ValueError("minimum must be decimal")
    if value is not None and value < minimum:
        reason_codes.append(reason_code)


def _append_history_failure(
    reason_codes: list[str],
    *,
    values: Sequence[Decimal | None] | None,
    lookback: Decimal | int | bool,
    insufficient_reason_code: str,
    failed_reason_code: str,
    allow_equal: bool,
) -> None:
    if not isinstance(lookback, int) or isinstance(lookback, bool):
        raise ValueError("lookback must be int")
    comparison = _series_comparison_values(values, lookback)
    if comparison is None:
        reason_codes.append(insufficient_reason_code)
        return
    previous, latest = comparison
    if latest < previous or (latest == previous and not allow_equal):
        reason_codes.append(failed_reason_code)


def _series_delta_record(
    values: Sequence[Decimal | None] | None,
    lookback: Decimal | int | bool,
) -> str | None:
    if not isinstance(lookback, int) or isinstance(lookback, bool):
        raise ValueError("lookback must be int")
    comparison = _series_comparison_values(values, lookback)
    if comparison is None:
        return None
    previous, latest = comparison
    return str(latest - previous)


def _series_comparison_values(
    values: Sequence[Decimal | None] | None,
    lookback: int,
) -> tuple[Decimal, Decimal] | None:
    if values is None or len(values) < lookback + 1:
        return None
    previous = values[-lookback - 1]
    latest = values[-1]
    if previous is None or latest is None:
        return None
    return _decimal(previous, "previous_series_value"), _decimal(
        latest,
        "latest_series_value",
    )


def _optional_score_record(value: Decimal | None, name: str) -> str | None:
    if value is None:
        return None
    return str(_score(value, name))


def _optional_bool_record(value: bool | None, name: str) -> bool | None:
    if value is not None and not isinstance(value, bool):
        raise ValueError(f"{name} must be bool when provided")
    return value


def _optional_utc_datetime_record(value: datetime | None, name: str) -> str | None:
    if value is None:
        return None
    return require_utc_datetime(value, name).isoformat()


def _confirmation_lag_days(
    capitulation_detected_at: datetime | None,
    confirmation_at: datetime | None,
) -> Decimal | None:
    if capitulation_detected_at is None or confirmation_at is None:
        return None
    capitulation_time = require_utc_datetime(
        capitulation_detected_at,
        "capitulation_detected_at",
    )
    confirmation_time = require_utc_datetime(confirmation_at, "confirmation_at")
    seconds = int((confirmation_time - capitulation_time).total_seconds())
    return Decimal(seconds) / Decimal(86400)


def _optional_score_series_record(
    value: Sequence[Decimal | None] | None,
    name: str,
) -> list[str | None] | None:
    if value is None:
        return None
    return [
        str(_score(item, name)) if item is not None else None
        for item in value
    ]


def _optional_decimal_series_record(
    value: Sequence[Decimal | None] | None,
    name: str,
) -> list[str | None] | None:
    if value is None:
        return None
    return [
        str(_decimal(item, name)) if item is not None else None
        for item in value
    ]


def _score(value: Any, name: str) -> Decimal:
    score = _decimal(value, name)
    if score < 0 or score > 100:
        raise ValueError(f"{name} must be between 0 and 100")
    return score


def _positive_decimal(value: Any, name: str) -> Decimal:
    number = _decimal(value, name)
    if number <= 0:
        raise ValueError(f"{name} must be positive")
    return number


def _non_negative_decimal(value: Any, name: str) -> Decimal:
    number = _decimal(value, name)
    if number < 0:
        raise ValueError(f"{name} must be non-negative")
    return number


def _fraction(value: Any, name: str) -> Decimal:
    number = _decimal(value, name)
    if number < 0 or number > 1:
        raise ValueError(f"{name} must be between 0 and 1")
    return number


def _positive_int(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be bool")
    return value


def _decimal(value: Any, name: str) -> Decimal:
    if value is None or isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc


def _dedupe_reason_codes(reason_codes: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(reason_codes))
