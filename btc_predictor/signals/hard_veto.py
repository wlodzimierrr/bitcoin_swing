"""Fail-closed new-trade hard-veto orchestration (BTC-132)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from btc_predictor.config import StrategyConfig


HARD_VETO_FEATURE_ID = "HARD_VETO"
HARD_VETO_POLICY_VERSION = "HARD_VETO_V1"
HARD_VETO_EFFECTS = ("NO_TRADE",)
HARD_VETO_INPUT_IDS = (
    "data_quality_fail",
    "valid_structural_stop",
    "reward_risk_passes",
    "stress_flagged",
    "severe_crowding_flagged",
    "no_chase_blocked",
    "setup",
)
HARD_VETO_REASON_CODES = (
    "HARD_VETO_INPUT_MISSING",
    "HARD_VETO_DATA_QUALITY_FAIL",
    "HARD_VETO_NO_VALID_STRUCTURAL_STOP",
    "HARD_VETO_POOR_REWARD_RISK",
    "HARD_VETO_STRESS",
    "HARD_VETO_SEVERE_CROWDING",
    "HARD_VETO_NO_CHASE_VIOLATION",
    "HARD_VETO_UNSUPPORTED_SETUP",
    "HARD_VETO_CLEAR",
)
_REQUIRED_CONFIG_METADATA_KEYS = (
    "config_version",
    "strategy_version",
    "parameter_set_id",
)


@dataclass(frozen=True)
class HardVetoInput:
    """Resolved upstream states needed to authorize a new trade.

    ``None`` means that a required state is unavailable. The engine fails
    closed in that case. ``setup=None`` means no recognized setup was found.
    Source reason codes retain the evidence used to resolve each state.
    """

    data_quality_fail: bool | None
    valid_structural_stop: bool | None
    reward_risk_passes: bool | None
    stress_flagged: bool | None
    severe_crowding_flagged: bool | None
    no_chase_blocked: bool | None
    setup: str | None
    source_reason_codes: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    def as_record(self) -> dict[str, Any]:
        values = _validate_inputs(self)
        return {
            **values,
            "source_reason_codes": {
                source: list(codes)
                for source, codes in _normalize_source_reason_codes(
                    self.source_reason_codes,
                ).items()
            },
        }


@dataclass(frozen=True)
class HardVetoResult:
    feature_id: str
    policy_version: str
    inputs: HardVetoInput
    supported_setups: tuple[str, ...]
    stress_blocks_new_trades: bool
    blocked: bool
    effects: tuple[str, ...]
    missing_inputs: tuple[str, ...]
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        """Return a self-validating record sufficient to reproduce the veto."""

        if self.feature_id != HARD_VETO_FEATURE_ID:
            raise ValueError("feature_id must be HARD_VETO")
        if self.policy_version != HARD_VETO_POLICY_VERSION:
            raise ValueError(f"policy_version must be {HARD_VETO_POLICY_VERSION}")
        supported_setups = _normalize_supported_setups(self.supported_setups)
        metadata = _validate_config_metadata(self.config_metadata)
        expected = _evaluate(
            self.inputs,
            supported_setups=supported_setups,
            stress_blocks_new_trades=self.stress_blocks_new_trades,
        )
        if self.blocked != expected.blocked:
            raise ValueError("blocked does not match hard-veto inputs")
        if self.effects != expected.effects:
            raise ValueError("effects do not match hard-veto state")
        if self.missing_inputs != expected.missing_inputs:
            raise ValueError("missing_inputs do not match hard-veto inputs")
        if self.complete != expected.complete:
            raise ValueError("complete does not match hard-veto inputs")
        if self.reason_codes != expected.reason_codes:
            raise ValueError("reason_codes do not match hard-veto inputs")

        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "inputs": self.inputs.as_record(),
            "supported_setups": list(supported_setups),
            "stress_blocks_new_trades": self.stress_blocks_new_trades,
            "blocked": self.blocked,
            "effects": list(self.effects),
            "missing_inputs": list(self.missing_inputs),
            "config_metadata": metadata,
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class _VetoDecision:
    blocked: bool
    effects: tuple[str, ...]
    missing_inputs: tuple[str, ...]
    complete: bool
    reason_codes: tuple[str, ...]


def evaluate_hard_veto(
    inputs: HardVetoInput,
    *,
    strategy_config: StrategyConfig,
) -> HardVetoResult:
    """Evaluate all Phase 1 new-trade vetoes in a stable order."""

    if not isinstance(inputs, HardVetoInput):
        raise TypeError("inputs must be a HardVetoInput")
    if not isinstance(strategy_config, StrategyConfig):
        raise TypeError("strategy_config must be a StrategyConfig")

    supported_setups = _normalize_supported_setups(
        strategy_config.setup_requirements.supported_setups,
    )
    stress_blocks = strategy_config.volatility_flags.stress.block_new_trades
    decision = _evaluate(
        inputs,
        supported_setups=supported_setups,
        stress_blocks_new_trades=stress_blocks,
    )
    result = HardVetoResult(
        feature_id=HARD_VETO_FEATURE_ID,
        policy_version=HARD_VETO_POLICY_VERSION,
        inputs=inputs,
        supported_setups=supported_setups,
        stress_blocks_new_trades=stress_blocks,
        blocked=decision.blocked,
        effects=decision.effects,
        missing_inputs=decision.missing_inputs,
        config_metadata=_validate_config_metadata(strategy_config.run_metadata()),
        complete=decision.complete,
        reason_codes=decision.reason_codes,
    )
    result.as_record()
    return result


def _evaluate(
    inputs: HardVetoInput,
    *,
    supported_setups: tuple[str, ...],
    stress_blocks_new_trades: bool,
) -> _VetoDecision:
    values = _validate_inputs(inputs)
    if not isinstance(stress_blocks_new_trades, bool):
        raise TypeError("stress_blocks_new_trades must be a bool")

    missing_inputs = tuple(
        input_id
        for input_id in HARD_VETO_INPUT_IDS
        if values[input_id] is None
    )
    reasons = []
    if missing_inputs:
        reasons.append("HARD_VETO_INPUT_MISSING")
    if values["data_quality_fail"] is True:
        reasons.append("HARD_VETO_DATA_QUALITY_FAIL")
    if values["valid_structural_stop"] is not True:
        reasons.append("HARD_VETO_NO_VALID_STRUCTURAL_STOP")
    if values["reward_risk_passes"] is not True:
        reasons.append("HARD_VETO_POOR_REWARD_RISK")
    if values["stress_flagged"] is True and stress_blocks_new_trades:
        reasons.append("HARD_VETO_STRESS")
    if values["severe_crowding_flagged"] is True:
        reasons.append("HARD_VETO_SEVERE_CROWDING")
    if values["no_chase_blocked"] is True:
        reasons.append("HARD_VETO_NO_CHASE_VIOLATION")
    if not _is_supported_setup(values["setup"], supported_setups):
        reasons.append("HARD_VETO_UNSUPPORTED_SETUP")

    blocked = bool(reasons)
    reason_codes = tuple(reasons) if blocked else ("HARD_VETO_CLEAR",)
    return _VetoDecision(
        blocked=blocked,
        effects=HARD_VETO_EFFECTS if blocked else (),
        missing_inputs=missing_inputs,
        complete=not missing_inputs,
        reason_codes=reason_codes,
    )


def _validate_inputs(inputs: HardVetoInput) -> dict[str, bool | str | None]:
    values: dict[str, bool | str | None] = {
        "data_quality_fail": inputs.data_quality_fail,
        "valid_structural_stop": inputs.valid_structural_stop,
        "reward_risk_passes": inputs.reward_risk_passes,
        "stress_flagged": inputs.stress_flagged,
        "severe_crowding_flagged": inputs.severe_crowding_flagged,
        "no_chase_blocked": inputs.no_chase_blocked,
        "setup": inputs.setup,
    }
    for input_id in HARD_VETO_INPUT_IDS[:-1]:
        value = values[input_id]
        if value is not None and not isinstance(value, bool):
            raise TypeError(f"{input_id} must be a bool or None")
    setup = values["setup"]
    if setup is not None:
        if not isinstance(setup, str):
            raise TypeError("setup must be a string or None")
        setup = setup.strip()
        if not setup:
            raise ValueError("setup must be non-empty when supplied")
        values["setup"] = setup
    _normalize_source_reason_codes(inputs.source_reason_codes)
    return values


def _normalize_supported_setups(setups: Any) -> tuple[str, ...]:
    if isinstance(setups, (str, bytes)):
        raise TypeError("supported_setups must be a sequence of strings")
    try:
        supplied = tuple(setups)
    except TypeError as exc:
        raise TypeError("supported_setups must be a sequence of strings") from exc
    if any(not isinstance(setup, str) for setup in supplied):
        raise TypeError("supported_setups must contain only strings")
    normalized = tuple(setup.strip() for setup in supplied)
    if not normalized or any(not setup for setup in normalized):
        raise ValueError("supported_setups must contain non-empty setup names")
    canonical = tuple(setup.casefold() for setup in normalized)
    if len(set(canonical)) != len(canonical):
        raise ValueError("supported_setups must not contain duplicates")
    return normalized


def _is_supported_setup(setup: bool | str | None, supported: tuple[str, ...]) -> bool:
    if not isinstance(setup, str):
        return False
    canonical = setup.casefold()
    return canonical in {candidate.casefold() for candidate in supported}


def _normalize_source_reason_codes(
    reasons: Mapping[str, tuple[str, ...]],
) -> dict[str, tuple[str, ...]]:
    if not isinstance(reasons, Mapping):
        raise TypeError("source_reason_codes must be a mapping")
    normalized = {}
    for source in sorted(reasons):
        if source not in HARD_VETO_INPUT_IDS:
            raise ValueError(f"unsupported source reason-code key: {source}")
        codes = reasons[source]
        if isinstance(codes, (str, bytes)):
            raise TypeError("source reason codes must be sequences of strings")
        if any(not isinstance(code, str) or not code.strip() for code in codes):
            raise ValueError("source reason codes must be non-empty strings")
        normalized[source] = tuple(codes)
    return normalized


def _validate_config_metadata(metadata: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(metadata, Mapping):
        raise TypeError("config_metadata must be a mapping")
    missing = set(_REQUIRED_CONFIG_METADATA_KEYS) - set(metadata)
    extra = set(metadata) - set(_REQUIRED_CONFIG_METADATA_KEYS)
    if missing or extra:
        raise ValueError(
            "config_metadata must exactly match required keys; "
            f"missing={sorted(missing)}, extra={sorted(extra)}",
        )
    normalized = {}
    for key in _REQUIRED_CONFIG_METADATA_KEYS:
        value = metadata[key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"config_metadata.{key} must be a non-empty string")
        normalized[key] = value
    return normalized


__all__ = [
    "HARD_VETO_EFFECTS",
    "HARD_VETO_FEATURE_ID",
    "HARD_VETO_INPUT_IDS",
    "HARD_VETO_POLICY_VERSION",
    "HARD_VETO_REASON_CODES",
    "HardVetoInput",
    "HardVetoResult",
    "evaluate_hard_veto",
]
