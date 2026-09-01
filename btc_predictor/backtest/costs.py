"""Realistic backtest cost profiles (BTC-181).

A single cost assumption makes a backtest look like a fact. Three make it look
like what it is: a range. ``REALISTIC_COST_MODEL_V1`` publishes one ordered
ladder of ``ExecutionCosts``:

```text
optimistic   patient limit fills in liquid conditions
base         the shared configured assumption
stress       taker fees, gapped fills and crowded perpetual carry
```

The ``base`` rung is not a fourth set of numbers. It is exactly
``execution_costs_from_config()``, the same assumption advisory and paper
trading already price against, so selecting ``base`` can never quietly disagree
with the rest of the system. Only ``optimistic`` and ``stress`` are declared in
``[backtest.cost_profiles]``.

The ladder must be monotone: no component of a more pessimistic rung may be
cheaper than the same component of a more optimistic one. A ladder that crosses
would report "stress" results that are cheaper than "base", which is worse than
having no profiles at all, so resolving any rung validates the whole ladder and
fails closed.

Profiles change the priced assumptions of a run, never its strategy semantics.
Costs stay in ``ExecutionCosts`` and continue to be applied by the BTC-160/165
owners; this module only decides which assumption a run is executed under and
records that choice as replayable evidence.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from btc_predictor.config.strategy import (
    CostProfileAssumptions,
    StrategyConfig,
    load_strategy_config,
)
from btc_predictor.portfolio.account import (
    EXECUTION_COST_POLICY_VERSION,
    ExecutionCosts,
    execution_costs_from_config,
)


COST_PROFILE_FEATURE_ID = "BACKTEST_COST_PROFILE"
COST_PROFILE_POLICY_VERSION = "REALISTIC_COST_MODEL_V1"
COST_PROFILE_PARAMETER_STATUS = "PROVISIONAL_RESEARCH_CALIBRATABLE"

OPTIMISTIC_PROFILE = "optimistic"
BASE_PROFILE = "base"
STRESS_PROFILE = "stress"
# Ladder order, cheapest first. Persisted evidence and comparisons rely on it.
COST_PROFILES = (OPTIMISTIC_PROFILE, BASE_PROFILE, STRESS_PROFILE)

COST_PROFILE_REASON_CODES = (
    "COST_PROFILE_SELECTED",
    "COST_PROFILE_SHARED_CONFIG_COSTS",
    "COST_PROFILE_FUNDING_UNPRICED",
)

# The cost fraction of one unit of notional; the owner does the arithmetic.
_UNIT_NOTIONAL = Decimal("1")


@dataclass(frozen=True)
class CostProfile:
    """One resolved rung of the cost ladder, with its selection evidence."""

    feature_id: str
    policy_version: str
    parameter_status: str
    profile: str
    costs: ExecutionCosts
    config_metadata: dict[str, str]
    reason_codes: tuple[str, ...] = ()

    def round_trip_cost(self, notional: Any) -> Decimal:
        """Return the BTC-160 entry-plus-exit fee and slippage on ``notional``."""

        return self.costs.round_trip_cost(notional)

    def as_record(self) -> dict[str, Any]:
        if self.feature_id != COST_PROFILE_FEATURE_ID:
            raise ValueError(f"feature_id must be {COST_PROFILE_FEATURE_ID}")
        if self.policy_version != COST_PROFILE_POLICY_VERSION:
            raise ValueError(f"policy_version must be {COST_PROFILE_POLICY_VERSION}")
        if self.parameter_status != COST_PROFILE_PARAMETER_STATUS:
            raise ValueError(
                f"parameter_status must be {COST_PROFILE_PARAMETER_STATUS}"
            )
        if self.profile not in COST_PROFILES:
            raise ValueError(f"profile must be one of {COST_PROFILES}")
        if self.costs.policy_version != EXECUTION_COST_POLICY_VERSION:
            raise ValueError(
                f"costs.policy_version must be {EXECUTION_COST_POLICY_VERSION}"
            )
        for code in self.reason_codes:
            if code not in COST_PROFILE_REASON_CODES:
                raise ValueError(f"undeclared cost profile reason code: {code}")
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "parameter_status": self.parameter_status,
            "profile": self.profile,
            "costs": self.costs.as_record(),
            "round_trip_cost_fraction": str(self.round_trip_cost(_UNIT_NOTIONAL)),
            "config_metadata": dict(self.config_metadata),
            "reason_codes": list(self.reason_codes),
        }


def cost_profiles(config: StrategyConfig | None = None) -> tuple[CostProfile, ...]:
    """Return every rung of the validated ladder, cheapest first."""

    resolved = config if config is not None else load_strategy_config()
    if not isinstance(resolved, StrategyConfig):
        raise TypeError("config must be a StrategyConfig")
    metadata = resolved.run_metadata()
    declared = resolved.backtest.cost_profiles
    ladder = (
        _profile(
            OPTIMISTIC_PROFILE,
            _costs_from_assumptions(declared.optimistic, OPTIMISTIC_PROFILE),
            metadata,
        ),
        _profile(BASE_PROFILE, execution_costs_from_config(resolved), metadata),
        _profile(
            STRESS_PROFILE,
            _costs_from_assumptions(declared.stress, STRESS_PROFILE),
            metadata,
        ),
    )
    _validate_ladder(ladder)
    return ladder


def cost_profile(
    profile: str,
    *,
    config: StrategyConfig | None = None,
) -> CostProfile:
    """Return one named rung, having validated the ladder it belongs to."""

    if profile not in COST_PROFILES:
        raise ValueError(f"profile must be one of {COST_PROFILES}")
    ladder = cost_profiles(config)
    return next(rung for rung in ladder if rung.profile == profile)


def restore_cost_profile(record: Mapping[str, Any]) -> CostProfile:
    """Restore a persisted profile and reject drift or tampering."""

    if not isinstance(record, Mapping):
        raise ValueError("cost_profile record must be a mapping")
    costs_record = record.get("costs")
    if not isinstance(costs_record, Mapping):
        raise ValueError("cost_profile.costs must be a mapping")
    restored = CostProfile(
        feature_id=_string(record.get("feature_id"), "cost_profile.feature_id"),
        policy_version=_string(
            record.get("policy_version"), "cost_profile.policy_version"
        ),
        parameter_status=_string(
            record.get("parameter_status"), "cost_profile.parameter_status"
        ),
        profile=_string(record.get("profile"), "cost_profile.profile"),
        costs=ExecutionCosts(
            policy_version=_string(
                costs_record.get("policy_version"), "cost_profile.costs.policy_version"
            ),
            fee_bps=_non_negative(
                costs_record.get("fee_bps"), "cost_profile.costs.fee_bps"
            ),
            slippage_bps=_non_negative(
                costs_record.get("slippage_bps"), "cost_profile.costs.slippage_bps"
            ),
            funding_cost_bps_per_day=_non_negative(
                costs_record.get("funding_cost_bps_per_day"),
                "cost_profile.costs.funding_cost_bps_per_day",
            ),
        ),
        config_metadata=_string_mapping(
            record.get("config_metadata"), "cost_profile.config_metadata"
        ),
        reason_codes=_string_tuple(
            record.get("reason_codes"), "cost_profile.reason_codes"
        ),
    )
    if restored.as_record() != dict(record):
        raise ValueError("record does not match reconstructed cost profile evidence")
    return restored


def _profile(
    profile: str,
    costs: ExecutionCosts,
    metadata: dict[str, str],
) -> CostProfile:
    reasons = ["COST_PROFILE_SELECTED"]
    if profile == BASE_PROFILE:
        # The base rung is the shared assumption itself, not a copy of it.
        reasons.append("COST_PROFILE_SHARED_CONFIG_COSTS")
    if costs.funding_cost_bps_per_day == 0:
        # A run that prices no carry says so rather than implying carry is free.
        reasons.append("COST_PROFILE_FUNDING_UNPRICED")
    resolved = CostProfile(
        feature_id=COST_PROFILE_FEATURE_ID,
        policy_version=COST_PROFILE_POLICY_VERSION,
        parameter_status=COST_PROFILE_PARAMETER_STATUS,
        profile=profile,
        costs=costs,
        config_metadata=dict(metadata),
        reason_codes=tuple(reasons),
    )
    resolved.as_record()
    return resolved


def _costs_from_assumptions(
    assumptions: CostProfileAssumptions,
    profile: str,
) -> ExecutionCosts:
    if not isinstance(assumptions, CostProfileAssumptions):
        raise TypeError(f"{profile} profile must be a CostProfileAssumptions")
    return ExecutionCosts(
        policy_version=EXECUTION_COST_POLICY_VERSION,
        fee_bps=_non_negative(assumptions.fee_bps, f"{profile}.fee_bps"),
        slippage_bps=_non_negative(
            assumptions.slippage_bps, f"{profile}.slippage_bps"
        ),
        funding_cost_bps_per_day=_non_negative(
            assumptions.funding_cost_bps_per_day,
            f"{profile}.funding_cost_bps_per_day",
        ),
    )


def _validate_ladder(ladder: tuple[CostProfile, ...]) -> None:
    """Fail closed on a ladder whose rungs are not ordered cheapest first."""

    if tuple(rung.profile for rung in ladder) != COST_PROFILES:
        raise ValueError(f"cost ladder must declare {COST_PROFILES} in order")
    for cheaper, dearer in zip(ladder, ladder[1:]):
        for component in ("fee_bps", "slippage_bps", "funding_cost_bps_per_day"):
            if getattr(dearer.costs, component) < getattr(cheaper.costs, component):
                raise ValueError(
                    f"cost profile {dearer.profile} must not price {component} "
                    f"below {cheaper.profile}"
                )


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _string_mapping(value: Any, name: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    items = {}
    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, str):
            raise ValueError(f"{name} must map strings to strings")
        items[key] = item
    return items


def _string_tuple(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{name} must be a sequence")
    return tuple(_string(item, name) for item in value)


def _non_negative(value: Any, name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    try:
        result = Decimal(str(value))
    except Exception as error:  # noqa: BLE001 - surfaced as a domain error
        raise ValueError(f"{name} must be numeric") from error
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


__all__ = [
    "BASE_PROFILE",
    "COST_PROFILES",
    "COST_PROFILE_FEATURE_ID",
    "COST_PROFILE_PARAMETER_STATUS",
    "COST_PROFILE_POLICY_VERSION",
    "COST_PROFILE_REASON_CODES",
    "OPTIMISTIC_PROFILE",
    "STRESS_PROFILE",
    "CostProfile",
    "cost_profile",
    "cost_profiles",
    "restore_cost_profile",
]
