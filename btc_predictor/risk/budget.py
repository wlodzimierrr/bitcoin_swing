"""Conviction-based risk budget (BTC-144).

Rulebook 17 sizes initial risk from Entry Conviction:

    80-84   0.35% NAV
    85-89   0.50% NAV
    90+     0.60% NAV

The schedule is not hardcoded here. It is read from the versioned strategy
config (``risk.schedule``), which already declares these bands, so advisory,
paper trading and backtesting cannot drift onto different numbers.

Below the lowest band there is no budget. Rulebook 14 makes anything under 80
WATCH or IGNORE rather than a valid trade, so the correct answer is "no risk
budget", never a silently reduced one.

This module produces the risk budget only. Turning it into a position size is
BTC-145's ``PositionNotional = NAV * RiskBudget / StopDistance%``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from btc_predictor.config.strategy import StrategyConfig, load_strategy_config
from btc_predictor.quant.comparisons import (
    decision_greater_equal,
    decision_less,
    decision_less_equal,
)


RISK_BUDGET_FEATURE_ID = "RISK_BUDGET"
RISK_BUDGET_POLICY_VERSION = "RISK_BUDGET_V1"
RISK_BUDGET_PARAMETER_STATUS = "PROVISIONAL_PENDING_BTC_185"

RISK_BUDGET_REASON_CODES = (
    "RISK_BUDGET_ASSIGNED",
    "RISK_BUDGET_INPUT_MISSING",
    "RISK_BUDGET_BELOW_MINIMUM_CONVICTION",
    "RISK_BUDGET_CAPPED_AT_MAXIMUM",
)


@dataclass(frozen=True)
class RiskBudgetBand:
    """One resolved conviction band from the strategy config."""

    min_entry_conviction: Decimal
    max_entry_conviction: Decimal | None
    risk_fraction_nav: Decimal

    def contains(self, conviction: Decimal) -> bool:
        # Bands are half-open [min, max) so adjacent bands cannot both match.
        if decision_less(conviction, self.min_entry_conviction):
            return False
        if self.max_entry_conviction is None:
            return True
        return decision_less(conviction, self.max_entry_conviction)

    def as_record(self) -> dict[str, Any]:
        return {
            "min_entry_conviction": str(self.min_entry_conviction),
            "max_entry_conviction": (
                str(self.max_entry_conviction)
                if self.max_entry_conviction is not None
                else None
            ),
            "risk_fraction_nav": str(self.risk_fraction_nav),
        }


@dataclass(frozen=True)
class RiskBudgetResult:
    feature_id: str
    policy_version: str
    entry_conviction: Decimal | None
    risk_fraction_nav: Decimal | None
    nav: Decimal | None
    risk_budget_amount: Decimal | None
    selected_band: RiskBudgetBand | None
    maximum_risk_fraction_nav: Decimal
    schedule: tuple[RiskBudgetBand, ...]
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        if self.complete and self.risk_fraction_nav is None:
            raise ValueError("a complete risk budget requires a risk fraction")
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "entry_conviction": _optional(self.entry_conviction),
            "risk_fraction_nav": _optional(self.risk_fraction_nav),
            "nav": _optional(self.nav),
            "risk_budget_amount": _optional(self.risk_budget_amount),
            "selected_band": (
                self.selected_band.as_record()
                if self.selected_band is not None
                else None
            ),
            "maximum_risk_fraction_nav": str(self.maximum_risk_fraction_nav),
            "schedule": [band.as_record() for band in self.schedule],
            "config_metadata": dict(self.config_metadata),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def risk_schedule_from_config(
    config: StrategyConfig | None = None,
) -> tuple[tuple[RiskBudgetBand, ...], Decimal]:
    """Resolve the conviction schedule and the global cap from strategy config."""

    resolved = config if config is not None else load_strategy_config()
    bands = tuple(
        RiskBudgetBand(
            min_entry_conviction=Decimal(str(band.min_entry_conviction)),
            max_entry_conviction=(
                Decimal(str(band.max_entry_conviction))
                if band.max_entry_conviction is not None
                else None
            ),
            risk_fraction_nav=Decimal(str(band.risk_fraction_nav)),
        )
        for band in resolved.risk.schedule
    )
    return bands, Decimal(str(resolved.risk.max_risk_at_stop_fraction_nav))


def calculate_risk_budget(
    *,
    entry_conviction: Any | None,
    nav: Any | None = None,
    config: StrategyConfig | None = None,
    schedule: Sequence[RiskBudgetBand] | None = None,
    maximum_risk_fraction_nav: Any | None = None,
    config_metadata: Mapping[str, str] | None = None,
) -> RiskBudgetResult:
    """Assign a NAV risk fraction from Entry Conviction.

    ``nav`` is optional. When supplied the budget is also expressed in
    currency, which BTC-145 divides by the stop distance to size a position.
    """

    if schedule is None or maximum_risk_fraction_nav is None:
        config_bands, config_maximum = risk_schedule_from_config(config)
        bands = tuple(schedule) if schedule is not None else config_bands
        maximum = (
            _non_negative_decimal(maximum_risk_fraction_nav, "maximum_risk_fraction_nav")
            if maximum_risk_fraction_nav is not None
            else config_maximum
        )
    else:
        bands = tuple(schedule)
        maximum = _non_negative_decimal(
            maximum_risk_fraction_nav,
            "maximum_risk_fraction_nav",
        )
    if not bands:
        raise ValueError("risk schedule must not be empty")
    metadata = dict(config_metadata or {})
    nav_value = _positive_decimal(nav, "nav") if nav is not None else None

    if entry_conviction is None:
        return _no_budget(
            conviction=None,
            nav=nav_value,
            bands=bands,
            maximum=maximum,
            metadata=metadata,
            reason_codes=("RISK_BUDGET_INPUT_MISSING",),
        )

    conviction = _score_decimal(entry_conviction, "entry_conviction")
    band = next((item for item in bands if item.contains(conviction)), None)
    if band is None:
        # Below the lowest band the setup is WATCH or IGNORE, not a smaller
        # trade. Returning no budget keeps that decision explicit.
        return _no_budget(
            conviction=conviction,
            nav=nav_value,
            bands=bands,
            maximum=maximum,
            metadata=metadata,
            reason_codes=("RISK_BUDGET_BELOW_MINIMUM_CONVICTION",),
        )

    reason_codes = ["RISK_BUDGET_ASSIGNED"]
    fraction = band.risk_fraction_nav
    if decision_greater_equal(fraction, maximum) and fraction != maximum:
        fraction = maximum
        reason_codes.append("RISK_BUDGET_CAPPED_AT_MAXIMUM")

    return RiskBudgetResult(
        feature_id=RISK_BUDGET_FEATURE_ID,
        policy_version=RISK_BUDGET_POLICY_VERSION,
        entry_conviction=conviction,
        risk_fraction_nav=fraction,
        nav=nav_value,
        risk_budget_amount=(
            None if nav_value is None else nav_value * fraction
        ),
        selected_band=band,
        maximum_risk_fraction_nav=maximum,
        schedule=bands,
        config_metadata=metadata,
        complete=True,
        reason_codes=tuple(reason_codes),
    )


def _no_budget(
    *,
    conviction: Decimal | None,
    nav: Decimal | None,
    bands: tuple[RiskBudgetBand, ...],
    maximum: Decimal,
    metadata: dict[str, str],
    reason_codes: tuple[str, ...],
) -> RiskBudgetResult:
    return RiskBudgetResult(
        feature_id=RISK_BUDGET_FEATURE_ID,
        policy_version=RISK_BUDGET_POLICY_VERSION,
        entry_conviction=conviction,
        risk_fraction_nav=None,
        nav=nav,
        risk_budget_amount=None,
        selected_band=None,
        maximum_risk_fraction_nav=maximum,
        schedule=bands,
        config_metadata=metadata,
        complete=False,
        reason_codes=reason_codes,
    )


def _optional(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _decimal(value: Any, name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as error:  # noqa: BLE001 - surfaced as a domain error
        raise ValueError(f"{name} must be numeric") from error
    # NaN and infinity are rejected here as named domain errors. Left to the
    # bare comparisons they surface as decimal.InvalidOperation, an
    # ArithmeticError carrying no field name, and NaN silently poisons every
    # downstream max/sum instead of refusing the input.
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    return result


def _score_decimal(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if decision_less(result, 0) or decision_greater_equal(result, Decimal("100.000001")):
        raise ValueError(f"{name} must be between 0 and 100")
    return result


def _positive_decimal(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if decision_less_equal(result, 0):
        raise ValueError(f"{name} must be positive")
    return result


def _non_negative_decimal(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


__all__ = [
    "RISK_BUDGET_FEATURE_ID",
    "RISK_BUDGET_PARAMETER_STATUS",
    "RISK_BUDGET_POLICY_VERSION",
    "RISK_BUDGET_REASON_CODES",
    "RiskBudgetBand",
    "RiskBudgetResult",
    "calculate_risk_budget",
    "risk_schedule_from_config",
]
