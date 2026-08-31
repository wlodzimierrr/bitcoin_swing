"""Versioned recommendation explanation aggregation (BTC-133)."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from btc_predictor.config import StrategyConfig
from btc_predictor.features.entry import (
    ENTRY_ACTION_CLASSIFICATION_VERSION,
    ENTRY_ACTION_LABELS,
    ENTRY_CONVICTION_SCORE_VERSION,
    EntryActionResult,
    EntryConvictionResult,
)
from btc_predictor.signals.data_quality import (
    RecommendationReasonCode,
    build_recommendation_reason_code_records,
)
from btc_predictor.signals.hard_veto import (
    HARD_VETO_POLICY_VERSION,
    HARD_VETO_REASON_CODES,
    HardVetoResult,
)


REASON_CODE_ENGINE_FEATURE_ID = "REASON_CODE_ENGINE"
REASON_CODE_ENGINE_VERSION = "REASON_CODE_ENGINE_V1"
REASON_CODE_ENGINE_SOURCE_IDS = (
    "entry_conviction",
    "entry_action",
    "hard_veto",
)
CANONICAL_SIGNAL_REASON_CODES = (
    "TREND_12W_POSITIVE",
    "ETF_FLOW_ACCEL_POSITIVE",
    "FUNDING_RESET",
    "OI_DELEVERAGED",
    "WEEKLY_SUPPORT_CLUSTER",
    "RECLAIM_CONFIRMED",
    "RISK_REWARD_VALID",
    "CROWDING_WARNING",
    "MACRO_WEAK",
)
_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
_SEVERITY_RANK = {"veto": 0, "warning": 1, "info": 2}
_SOURCE_RANK = {
    "hard_veto": 0,
    "entry_action": 1,
    "entry_conviction": 2,
}
_HARD_VETO_CODE_RANK = {
    code: rank for rank, code in enumerate(HARD_VETO_REASON_CODES)
}
_REQUIRED_CONFIG_METADATA_KEYS = (
    "config_version",
    "strategy_version",
    "parameter_set_id",
)


@dataclass(frozen=True)
class ReasonCodeDefinition:
    code: str
    source_component: str
    severity: str
    detail: str

    def to_reason(self) -> RecommendationReasonCode:
        return RecommendationReasonCode(
            code=self.code,
            source_component=self.source_component,
            severity=self.severity,
            detail=self.detail,
        )


_CANONICAL_DEFINITIONS = {
    "TREND_12W_POSITIVE": ReasonCodeDefinition(
        "TREND_12W_POSITIVE",
        "trend",
        "info",
        "Twelve-week momentum is positive.",
    ),
    "ETF_FLOW_ACCEL_POSITIVE": ReasonCodeDefinition(
        "ETF_FLOW_ACCEL_POSITIVE",
        "flow",
        "info",
        "ETF flow acceleration is positive.",
    ),
    "FUNDING_RESET": ReasonCodeDefinition(
        "FUNDING_RESET",
        "positioning",
        "info",
        "Funding conditions have reset from an overheated state.",
    ),
    "OI_DELEVERAGED": ReasonCodeDefinition(
        "OI_DELEVERAGED",
        "positioning",
        "info",
        "Open interest indicates deleveraging.",
    ),
    "WEEKLY_SUPPORT_CLUSTER": ReasonCodeDefinition(
        "WEEKLY_SUPPORT_CLUSTER",
        "structure",
        "info",
        "A credible weekly support cluster is available.",
    ),
    "RECLAIM_CONFIRMED": ReasonCodeDefinition(
        "RECLAIM_CONFIRMED",
        "entry_trigger",
        "info",
        "The reclaim entry trigger is confirmed.",
    ),
    "RISK_REWARD_VALID": ReasonCodeDefinition(
        "RISK_REWARD_VALID",
        "reward_risk",
        "info",
        "Initial reward-to-risk passes the configured minimum.",
    ),
    "CROWDING_WARNING": ReasonCodeDefinition(
        "CROWDING_WARNING",
        "positioning",
        "warning",
        "Positioning is crowded and reduces entry quality.",
    ),
    "MACRO_WEAK": ReasonCodeDefinition(
        "MACRO_WEAK",
        "macro",
        "warning",
        "The macro backdrop is weak.",
    ),
}


@dataclass(frozen=True)
class ReasonCodeEngineResult:
    feature_id: str
    engine_version: str
    entry_action: str | None
    hard_veto_blocked: bool
    source_versions: dict[str, str]
    source_complete: dict[str, bool]
    reasons: tuple[RecommendationReasonCode, ...]
    config_metadata: dict[str, str]
    complete: bool

    @property
    def reason_codes(self) -> tuple[str, ...]:
        return tuple(reason.code for reason in self.reasons)

    def as_record(self) -> dict[str, Any]:
        """Return a validated record with stable display ranks."""

        if self.feature_id != REASON_CODE_ENGINE_FEATURE_ID:
            raise ValueError("feature_id must be REASON_CODE_ENGINE")
        if self.engine_version != REASON_CODE_ENGINE_VERSION:
            raise ValueError(f"engine_version must be {REASON_CODE_ENGINE_VERSION}")
        versions = _validate_source_versions(self.source_versions)
        completion = _validate_source_completion(self.source_complete)
        metadata = _validate_config_metadata(self.config_metadata)
        reasons = _rank_reasons(self.reasons)
        if reasons != self.reasons:
            raise ValueError("reasons must use deterministic engine ranking")
        if self.complete != all(completion.values()):
            raise ValueError("complete must match source completion state")
        if not isinstance(self.hard_veto_blocked, bool):
            raise TypeError("hard_veto_blocked must be a bool")
        _validate_derived_state(
            entry_action=self.entry_action,
            hard_veto_blocked=self.hard_veto_blocked,
            source_complete=completion,
            reasons=reasons,
        )

        return {
            "feature_id": self.feature_id,
            "engine_version": self.engine_version,
            "entry_action": self.entry_action,
            "hard_veto_blocked": self.hard_veto_blocked,
            "source_versions": versions,
            "source_complete": completion,
            "reasons": [
                {
                    "reason_rank": rank,
                    "code": reason.code,
                    "source_component": reason.source_component,
                    "severity": reason.severity,
                    "detail": reason.detail,
                }
                for rank, reason in enumerate(reasons)
            ],
            "config_metadata": metadata,
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }

    def recommendation_records(
        self,
        recommendation_id: int,
    ) -> tuple[dict[str, Any], ...]:
        """Build rows for ``signals.recommendation_reason_codes``."""

        self.as_record()
        return build_recommendation_reason_code_records(
            recommendation_id,
            self.reasons,
        )


def canonical_signal_reason(code: str) -> RecommendationReasonCode:
    """Return the stable definition for a rulebook-level signal reason."""

    if not isinstance(code, str):
        raise TypeError("code must be a string")
    try:
        definition = _CANONICAL_DEFINITIONS[code]
    except KeyError as exc:
        raise ValueError(f"unsupported canonical signal reason code: {code}") from exc
    return definition.to_reason()


def build_reason_code_engine(
    *,
    entry_conviction: EntryConvictionResult,
    entry_action: EntryActionResult,
    hard_veto: HardVetoResult,
    strategy_config: StrategyConfig,
    signal_reasons: Sequence[RecommendationReasonCode] = (),
) -> ReasonCodeEngineResult:
    """Aggregate score, action, veto, and domain-owned signal explanations."""

    if not isinstance(entry_conviction, EntryConvictionResult):
        raise TypeError("entry_conviction must be an EntryConvictionResult")
    if not isinstance(entry_action, EntryActionResult):
        raise TypeError("entry_action must be an EntryActionResult")
    if not isinstance(hard_veto, HardVetoResult):
        raise TypeError("hard_veto must be a HardVetoResult")
    if not isinstance(strategy_config, StrategyConfig):
        raise TypeError("strategy_config must be a StrategyConfig")
    if isinstance(signal_reasons, (str, bytes)):
        raise TypeError("signal_reasons must be a sequence of reason codes")

    entry_conviction.as_record()
    entry_action.as_record()
    hard_veto.as_record()
    expected_metadata = _validate_config_metadata(strategy_config.run_metadata())
    _require_matching_config(
        "entry_conviction",
        entry_conviction.config_metadata,
        expected_metadata,
    )
    _require_matching_config(
        "entry_action",
        entry_action.config_metadata,
        expected_metadata,
    )
    _require_matching_config("hard_veto", hard_veto.config_metadata, expected_metadata)
    if entry_action.score != entry_conviction.score:
        raise ValueError("entry_action score must match entry_conviction score")

    reasons = [
        *_hard_veto_reasons(hard_veto),
        *_entry_action_reasons(entry_action),
        *_entry_conviction_reasons(entry_conviction),
        *_hard_veto_source_reasons(hard_veto),
    ]
    for reason in signal_reasons:
        if not isinstance(reason, RecommendationReasonCode):
            raise TypeError(
                "signal_reasons must contain RecommendationReasonCode values",
            )
        reasons.append(reason)
    ranked = _rank_reasons(reasons)
    source_complete = {
        "entry_conviction": entry_conviction.complete,
        "entry_action": entry_action.complete,
        "hard_veto": hard_veto.complete,
    }
    result = ReasonCodeEngineResult(
        feature_id=REASON_CODE_ENGINE_FEATURE_ID,
        engine_version=REASON_CODE_ENGINE_VERSION,
        entry_action=entry_action.action,
        hard_veto_blocked=hard_veto.blocked,
        source_versions={
            "entry_conviction": entry_conviction.score_version,
            "entry_action": entry_action.classification_version,
            "hard_veto": hard_veto.policy_version,
        },
        source_complete=source_complete,
        reasons=ranked,
        config_metadata=expected_metadata,
        complete=all(source_complete.values()),
    )
    result.as_record()
    return result


def _hard_veto_reasons(result: HardVetoResult) -> tuple[RecommendationReasonCode, ...]:
    return tuple(
        RecommendationReasonCode(
            code=code,
            source_component="hard_veto",
            severity="info" if code == "HARD_VETO_CLEAR" else "veto",
            detail=_reason_detail(code),
        )
        for code in result.reason_codes
    )


def _entry_action_reasons(
    result: EntryActionResult,
) -> tuple[RecommendationReasonCode, ...]:
    codes = (
        (result.reason_code,)
        if result.reason_code is not None
        else result.reason_codes
    )
    severity = "warning" if result.action in (None, "IGNORE", "WATCH") else "info"
    return tuple(
        RecommendationReasonCode(
            code=code,
            source_component="entry_action",
            severity=severity,
            detail=_reason_detail(code),
        )
        for code in codes
    )


def _entry_conviction_reasons(
    result: EntryConvictionResult,
) -> tuple[RecommendationReasonCode, ...]:
    return tuple(
        RecommendationReasonCode(
            code=code,
            source_component="entry_conviction",
            severity="info" if result.complete else "warning",
            detail=_reason_detail(code),
        )
        for code in result.reason_codes
    )


def _hard_veto_source_reasons(
    result: HardVetoResult,
) -> tuple[RecommendationReasonCode, ...]:
    reasons = []
    source_records = result.inputs.as_record()["source_reason_codes"]
    for source_component, codes in source_records.items():
        for code in codes:
            reasons.append(
                RecommendationReasonCode(
                    code=code,
                    source_component=source_component,
                    severity=_hard_veto_source_severity(source_component, result),
                    detail=(
                        f"Upstream {source_component.replace('_', ' ')} evidence: "
                        f"{code}."
                    ),
                ),
            )
    return tuple(reasons)


def _hard_veto_source_severity(source: str, result: HardVetoResult) -> str:
    inputs = result.inputs
    vetoed = {
        "data_quality_fail": inputs.data_quality_fail is True,
        "valid_structural_stop": inputs.valid_structural_stop is not True,
        "reward_risk_passes": inputs.reward_risk_passes is not True,
        "stress_flagged": (
            inputs.stress_flagged is True and result.stress_blocks_new_trades
        ),
        "severe_crowding_flagged": inputs.severe_crowding_flagged is True,
        "no_chase_blocked": inputs.no_chase_blocked is True,
        "setup": not _setup_is_supported(inputs.setup, result.supported_setups),
    }
    return "veto" if vetoed[source] else "info"


def _setup_is_supported(setup: str | None, supported: Sequence[str]) -> bool:
    if setup is None:
        return False
    return setup.strip().casefold() in {item.strip().casefold() for item in supported}


def _rank_reasons(
    reasons: Sequence[RecommendationReasonCode],
) -> tuple[RecommendationReasonCode, ...]:
    unique: dict[tuple[str, str], RecommendationReasonCode] = {}
    for reason in reasons:
        _validate_reason(reason)
        key = (reason.source_component, reason.code)
        previous = unique.get(key)
        if previous is not None and previous != reason:
            raise ValueError(
                "duplicate source/code reason has conflicting severity or detail: "
                f"{reason.source_component}/{reason.code}",
            )
        unique[key] = reason
    return tuple(sorted(unique.values(), key=_reason_sort_key))


def _reason_sort_key(reason: RecommendationReasonCode) -> tuple[Any, ...]:
    return (
        _SEVERITY_RANK[reason.severity],
        _SOURCE_RANK.get(reason.source_component, 100),
        _HARD_VETO_CODE_RANK.get(reason.code, 100),
        reason.source_component,
        reason.code,
        reason.detail,
    )


def _validate_reason(reason: RecommendationReasonCode) -> None:
    if not isinstance(reason, RecommendationReasonCode):
        raise TypeError("reasons must contain RecommendationReasonCode values")
    if len(reason.code) > 64 or _CODE_PATTERN.fullmatch(reason.code) is None:
        raise ValueError("reason code must be <= 64 characters in UPPER_SNAKE_CASE")
    if len(reason.source_component) > 64:
        raise ValueError("reason source_component must be <= 64 characters")
    if reason.severity not in _SEVERITY_RANK:
        raise ValueError("unsupported reason severity")


def _validate_derived_state(
    *,
    entry_action: str | None,
    hard_veto_blocked: bool,
    source_complete: Mapping[str, bool],
    reasons: Sequence[RecommendationReasonCode],
) -> None:
    action_reasons = tuple(
        reason.code
        for reason in reasons
        if reason.source_component == "entry_action"
    )
    if source_complete["entry_action"]:
        if entry_action not in ENTRY_ACTION_LABELS:
            raise ValueError("complete entry action must use a supported label")
        expected_action_reasons = (f"ENTRY_ACTION_{entry_action}",)
    else:
        if entry_action is not None:
            raise ValueError("incomplete entry action cannot contain an action")
        expected_action_reasons = ("ENTRY_ACTION_SCORE_MISSING",)
    if action_reasons != expected_action_reasons:
        raise ValueError("entry_action does not match entry-action reasons")

    veto_reason_present = any(
        reason.source_component == "hard_veto" and reason.severity == "veto"
        for reason in reasons
    )
    if hard_veto_blocked != veto_reason_present:
        raise ValueError("hard_veto_blocked does not match hard-veto reasons")


def _reason_detail(code: str) -> str:
    details = {
        "ENTRY_CONVICTION_COMPLETE": "All Entry Conviction components are available.",
        "ENTRY_CONVICTION_INPUT_MISSING": "Entry Conviction inputs are incomplete.",
        "ENTRY_ACTION_SCORE_MISSING": (
            "Entry action cannot be classified without a score."
        ),
        "HARD_VETO_INPUT_MISSING": "Required hard-veto evidence is unavailable.",
        "HARD_VETO_DATA_QUALITY_FAIL": "Critical data quality blocks a new trade.",
        "HARD_VETO_NO_VALID_STRUCTURAL_STOP": "No valid structural stop is available.",
        "HARD_VETO_POOR_REWARD_RISK": (
            "Reward-to-risk does not pass its independent filter."
        ),
        "HARD_VETO_STRESS": "Configured market stress blocks a new trade.",
        "HARD_VETO_SEVERE_CROWDING": "Severe positioning crowding blocks a new trade.",
        "HARD_VETO_NO_CHASE_VIOLATION": "Price violates the no-chase entry constraint.",
        "HARD_VETO_UNSUPPORTED_SETUP": "No supported setup authorizes a new trade.",
        "HARD_VETO_CLEAR": "No configured hard veto is active.",
    }
    if code.startswith("ENTRY_ACTION_"):
        action = code.removeprefix("ENTRY_ACTION_").replace("_", " ").lower()
        return f"Entry Conviction is classified as {action}."
    try:
        return details[code]
    except KeyError as exc:
        raise ValueError(f"no internal reason detail is defined for {code}") from exc


def _validate_source_versions(versions: Mapping[str, Any]) -> dict[str, str]:
    expected = {
        "entry_conviction": ENTRY_CONVICTION_SCORE_VERSION,
        "entry_action": ENTRY_ACTION_CLASSIFICATION_VERSION,
        "hard_veto": HARD_VETO_POLICY_VERSION,
    }
    if dict(versions) != expected:
        raise ValueError("source_versions do not match BTC-130/131/132 contracts")
    return expected


def _validate_source_completion(values: Mapping[str, Any]) -> dict[str, bool]:
    if set(values) != set(REASON_CODE_ENGINE_SOURCE_IDS):
        raise ValueError("source_complete must exactly match engine sources")
    normalized = {}
    for source_id in REASON_CODE_ENGINE_SOURCE_IDS:
        value = values[source_id]
        if not isinstance(value, bool):
            raise TypeError(f"source_complete.{source_id} must be a bool")
        normalized[source_id] = value
    return normalized


def _require_matching_config(
    source: str,
    actual: Mapping[str, Any],
    expected: Mapping[str, str],
) -> None:
    if _validate_config_metadata(actual) != dict(expected):
        raise ValueError(f"{source} config metadata does not match strategy_config")


def _validate_config_metadata(metadata: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(metadata, Mapping):
        raise TypeError("config_metadata must be a mapping")
    if set(metadata) != set(_REQUIRED_CONFIG_METADATA_KEYS):
        raise ValueError("config_metadata must exactly match required keys")
    normalized = {}
    for key in _REQUIRED_CONFIG_METADATA_KEYS:
        value = metadata[key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"config_metadata.{key} must be a non-empty string")
        normalized[key] = value
    return normalized


__all__ = [
    "CANONICAL_SIGNAL_REASON_CODES",
    "REASON_CODE_ENGINE_FEATURE_ID",
    "REASON_CODE_ENGINE_SOURCE_IDS",
    "REASON_CODE_ENGINE_VERSION",
    "ReasonCodeDefinition",
    "ReasonCodeEngineResult",
    "build_reason_code_engine",
    "canonical_signal_reason",
]
