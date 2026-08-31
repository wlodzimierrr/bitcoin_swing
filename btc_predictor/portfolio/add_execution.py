"""Deterministic simulated add execution (BTC-163).

An add is not an entry with a different label. An entry is triggered by price
reaching a zone; an add is triggered by *conditions* being met, which BTC-154
has already decided. So this module does not re-derive a fill zone the rulebook
never defines for adds. The proposal executes on the next full bar at its open,
moved adversely by the BTC-160 cost policy, which is the honest fill for a
decision made after the previous bar closed.

What this module owns is the composition, in order:

    BTC-154 requirements -> BTC-155 tranche allocation -> fill -> BTC-150 event

A refused add produces no fill at all, and the refusal keeps the requirement
engine's own reason codes so the explanation is not flattened into "cancelled".
An exhausted tranche schedule likewise produces no fill: BTC-154 decides whether
an add is permitted, BTC-155 whether one is allocated, and both must say yes.

The re-check at the fill price is the substantive part. BTC-154 evaluates
profitability at the *decision*, but the fill happens on the next bar. If price
moved against the position in between, filling anyway would average down --
rulebook 32 rule 2, one of the rules that may never be violated. The same
standard the gate applied is therefore re-applied to the market at execution
time, and an add that has gone underwater in the gap is cancelled rather than
filled. The re-check uses the bar's open, not the slipped fill: slippage is a
cost, not a mark, and a buy that fills higher must never read as a healthier
position than the market it filled in.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from btc_predictor.data import (
    OhlcvBar,
    SUPPORTED_TIMEFRAMES,
    next_bar_timestamp,
    require_utc_datetime,
)
from btc_predictor.portfolio.account import (
    BUY_SIDE,
    EXECUTION_COST_POLICY_VERSION,
    SELL_SIDE,
    ExecutionCosts,
)
from btc_predictor.portfolio.entry_execution import next_eligible_bar_timestamp
from btc_predictor.portfolio.state_machine import (
    position_is_losing_at_price,
    position_is_profitable_at_price,
)
from btc_predictor.quant.risk import POSITION_SIDES


ADD_EXECUTION_FEATURE_ID = "SIMULATED_ADD_EXECUTION"
ADD_EXECUTION_POLICY_VERSION = "SIMULATED_ADD_EXECUTION_V1"

ADD_FILLED = "filled"
ADD_CANCELLED = "cancelled"
ADD_EXECUTION_STATUSES = (ADD_FILLED, ADD_CANCELLED)

ADD_ACTION = "ADD"
MARKET_ORDER = "market"

LONG_DIRECTION = "long"

ADD_EXECUTION_REASON_CODES = (
    "ADD_EXECUTION_BLOCKED_BY_REQUIREMENTS",
    "ADD_EXECUTION_NO_TRANCHE_ALLOCATION",
    "ADD_EXECUTION_NO_LONGER_PROFITABLE",
    "ADD_EXECUTION_REFERENCE_BAR_OPEN",
    "ADD_EXECUTION_COSTS_APPLIED",
    "ADD_EXECUTION_FILLED",
    "ADD_EXECUTION_CANCELLED",
)

_REQUIRED_CONFIG_METADATA_KEYS = (
    "config_version",
    "strategy_version",
    "parameter_set_id",
)


@dataclass(frozen=True)
class AddExecutionIntent:
    """A proposed pyramid add, available at one point in time."""

    execution_id: str
    position_id: int | None
    recommendation_id: int | None
    symbol: str
    direction: str
    timeframe: str
    decision_at: datetime
    average_entry_price: Decimal
    config_metadata: dict[str, str]

    @property
    def side(self) -> str:
        return BUY_SIDE if self.direction == LONG_DIRECTION else SELL_SIDE

    @property
    def eligible_bar_at(self) -> datetime:
        return next_eligible_bar_timestamp(self.decision_at, self.timeframe)

    def as_record(self) -> dict[str, Any]:
        values = _validate_intent(self)
        return {
            "execution_id": values.execution_id,
            "position_id": values.position_id,
            "recommendation_id": values.recommendation_id,
            "symbol": values.symbol,
            "direction": values.direction,
            "side": values.side,
            "timeframe": values.timeframe,
            "decision_at": values.decision_at.isoformat(),
            "eligible_bar_at": values.eligible_bar_at.isoformat(),
            "average_entry_price": str(values.average_entry_price),
            "config_metadata": dict(values.config_metadata),
        }


@dataclass(frozen=True)
class SimulatedAddExecution:
    """A filled pyramid add or a refusal, with the evidence for both."""

    feature_id: str
    policy_version: str
    intent: AddExecutionIntent
    execution_bar: OhlcvBar
    costs: ExecutionCosts
    requirements: Any
    tranche: Any
    status: str
    action: str
    tranche_number: int | None
    reference_price: Decimal | None
    average_fill_price: Decimal | None
    requested_quantity: Decimal | None
    filled_quantity: Decimal
    notional: Decimal
    fee: Decimal
    slippage_cost: Decimal
    resolved_at: datetime
    complete: bool
    reason_codes: tuple[str, ...]

    @property
    def filled(self) -> bool:
        return self.status == ADD_FILLED

    @property
    def cancelled(self) -> bool:
        return self.status == ADD_CANCELLED

    def as_record(self) -> dict[str, Any]:
        """Return a self-validating record of the decision and the fill."""

        if self.feature_id != ADD_EXECUTION_FEATURE_ID:
            raise ValueError(f"feature_id must be {ADD_EXECUTION_FEATURE_ID}")
        if self.policy_version != ADD_EXECUTION_POLICY_VERSION:
            raise ValueError(f"policy_version must be {ADD_EXECUTION_POLICY_VERSION}")
        expected = _simulate(
            self.intent,
            self.execution_bar,
            self.costs,
            self.requirements,
            self.tranche,
        )
        actual = (
            self.status,
            self.action,
            self.tranche_number,
            self.reference_price,
            self.average_fill_price,
            self.requested_quantity,
            self.filled_quantity,
            self.notional,
            self.fee,
            self.slippage_cost,
            require_utc_datetime(self.resolved_at, "resolved_at"),
            self.complete,
            self.reason_codes,
        )
        if actual != expected:
            raise ValueError("add execution fields do not match replayed evidence")
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "intent": self.intent.as_record(),
            "execution_bar": _bar_record(self.execution_bar),
            "costs": self.costs.as_record(),
            # The upstream decisions travel with the fill, so a refusal can be
            # explained without re-running the engines that produced it.
            "requirements": self.requirements.as_record(),
            "tranche": self.tranche.as_record(),
            "status": self.status,
            "action": self.action,
            "order_type": MARKET_ORDER,
            "tranche_number": self.tranche_number,
            "reference_price": _optional_decimal_string(self.reference_price),
            "average_fill_price": _optional_decimal_string(self.average_fill_price),
            "requested_quantity": _optional_decimal_string(self.requested_quantity),
            "filled_quantity": str(self.filled_quantity),
            "notional": str(self.notional),
            "fee": str(self.fee),
            "slippage_cost": str(self.slippage_cost),
            "resolved_at": self.resolved_at.isoformat(),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }

    def as_order_record(
        self,
        *,
        account_id: int,
        position_id: int | None = None,
    ) -> dict[str, Any]:
        """Map onto the existing ``portfolio.paper_orders`` columns."""

        self.as_record()
        if (
            isinstance(account_id, bool)
            or not isinstance(account_id, int)
            or account_id < 1
        ):
            raise ValueError("account_id must be a positive integer")
        resolved_position_id = (
            position_id if position_id is not None else self.intent.position_id
        )
        if resolved_position_id is not None and (
            isinstance(resolved_position_id, bool)
            or not isinstance(resolved_position_id, int)
            or resolved_position_id < 1
        ):
            raise ValueError("position_id must be a positive integer or None")
        return {
            "account_id": account_id,
            "position_id": resolved_position_id,
            "recommendation_id": self.intent.recommendation_id,
            "action": self.action,
            "side": self.intent.side,
            "order_type": MARKET_ORDER,
            # A refused add was proposed and never worked, so it is cancelled
            # rather than missed: nothing about the market prevented it.
            "status": self.status,
            "created_at": self.intent.decision_at,
            "submitted_at": self.intent.eligible_bar_at if self.filled else None,
            "filled_at": self.resolved_at if self.filled else None,
            "requested_quantity": self.requested_quantity,
            "filled_quantity": self.filled_quantity,
            "limit_price": None,
            "stop_price": None,
            "average_fill_price": self.average_fill_price,
        }


def simulate_add_execution(
    intent: AddExecutionIntent,
    execution_bar: OhlcvBar,
    *,
    requirements: Any,
    tranche: Any,
    costs: ExecutionCosts,
) -> SimulatedAddExecution:
    """Execute a gated, sized add on its next eligible bar, or refuse it."""

    decision = _simulate(intent, execution_bar, costs, requirements, tranche)
    return SimulatedAddExecution(
        feature_id=ADD_EXECUTION_FEATURE_ID,
        policy_version=ADD_EXECUTION_POLICY_VERSION,
        intent=intent,
        execution_bar=execution_bar,
        costs=costs,
        requirements=requirements,
        tranche=tranche,
        status=decision[0],
        action=decision[1],
        tranche_number=decision[2],
        reference_price=decision[3],
        average_fill_price=decision[4],
        requested_quantity=decision[5],
        filled_quantity=decision[6],
        notional=decision[7],
        fee=decision[8],
        slippage_cost=decision[9],
        resolved_at=decision[10],
        complete=decision[11],
        reason_codes=decision[12],
    )


def _simulate(
    intent: AddExecutionIntent,
    execution_bar: OhlcvBar,
    costs: ExecutionCosts,
    requirements: Any,
    tranche: Any,
) -> tuple[Any, ...]:
    values = _validate_intent(intent)
    bar = _validate_bar(execution_bar, values)
    _validate_costs(costs)
    _validate_upstream(requirements, "requirements", ("blocked", "reason_codes"))
    _validate_upstream(tranche, "tranche", ("complete", "allocation"))
    resolved_at = max(
        next_bar_timestamp(bar.timestamp, bar.timeframe),
        bar.ingested_at,
    )
    allocation = tranche.allocation
    tranche_number = allocation.tranche_number if allocation is not None else None
    requested_quantity = (
        allocation.quantity if allocation is not None else None
    )

    def cancelled(reason_codes: tuple[str, ...]) -> tuple[Any, ...]:
        return (
            ADD_CANCELLED,
            ADD_ACTION,
            tranche_number,
            None,
            None,
            requested_quantity,
            Decimal("0"),
            Decimal("0"),
            Decimal("0"),
            Decimal("0"),
            resolved_at,
            True,
            reason_codes,
        )

    if requirements.blocked:
        # Keep the gate's own explanation rather than flattening every refusal
        # into a single opaque code.
        return cancelled(
            ("ADD_EXECUTION_BLOCKED_BY_REQUIREMENTS",)
            + tuple(requirements.reason_codes)
            + ("ADD_EXECUTION_CANCELLED",)
        )
    if not tranche.complete or requested_quantity is None:
        return cancelled(
            ("ADD_EXECUTION_NO_TRANCHE_ALLOCATION",)
            + tuple(tranche.reason_codes)
            + ("ADD_EXECUTION_CANCELLED",)
        )

    # The proposal was made after the previous bar closed, so the first price
    # actually available is this bar's open.
    reference_price = _positive(bar.open, "execution_bar.open")
    fill_price = costs.fill_price(reference_price, side=values.side)

    if _would_average_down(
        direction=values.direction,
        average_entry_price=values.average_entry_price,
        # The market reference, not the slipped fill. Slippage is a cost we
        # pay, not a mark: a buy that fills higher must never read as a more
        # profitable position than the market it filled in.
        market_price=reference_price,
        require_profitable=bool(
            getattr(requirements, "require_profitable_position", True)
        ),
    ):
        # BTC-154 judged profitability at the decision; the market moved before
        # the fill. Rulebook 32 rule 2 is absolute, so the add is dropped.
        return cancelled(
            (
                "ADD_EXECUTION_NO_LONGER_PROFITABLE",
                "ADD_EXECUTION_CANCELLED",
            )
        )

    reference_notional = requested_quantity * reference_price
    notional = requested_quantity * fill_price
    return (
        ADD_FILLED,
        ADD_ACTION,
        tranche_number,
        reference_price,
        fill_price,
        requested_quantity,
        requested_quantity,
        notional,
        costs.fee(notional),
        abs(notional - reference_notional),
        resolved_at,
        True,
        (
            "ADD_EXECUTION_REFERENCE_BAR_OPEN",
            "ADD_EXECUTION_COSTS_APPLIED",
            "ADD_EXECUTION_FILLED",
        ),
    )


def _would_average_down(
    *,
    direction: str,
    average_entry_price: Decimal,
    market_price: Decimal,
    require_profitable: bool,
) -> bool:
    """Re-apply the gate's own standard to the market at execution time."""

    if require_profitable:
        return not position_is_profitable_at_price(
            direction=direction,
            average_entry_price=average_entry_price,
            current_price=market_price,
        )
    # BTC-151's never-average-down invariant cannot be switched off, so it
    # still applies when BTC-154's stricter profitability gate is disabled.
    return position_is_losing_at_price(
        direction=direction,
        average_entry_price=average_entry_price,
        current_price=market_price,
    )


def _validate_intent(intent: AddExecutionIntent) -> AddExecutionIntent:
    if not isinstance(intent, AddExecutionIntent):
        raise TypeError("intent must be an AddExecutionIntent")
    _string(intent.execution_id, "execution_id")
    _optional_positive_integer(intent.position_id, "position_id")
    _optional_positive_integer(intent.recommendation_id, "recommendation_id")
    _string(intent.symbol, "symbol")
    if intent.direction not in POSITION_SIDES:
        raise ValueError(f"direction must be one of {POSITION_SIDES}")
    if intent.timeframe not in SUPPORTED_TIMEFRAMES:
        raise ValueError(f"timeframe must be one of {SUPPORTED_TIMEFRAMES}")
    require_utc_datetime(intent.decision_at, "decision_at")
    _positive(intent.average_entry_price, "average_entry_price")
    _config_metadata(intent.config_metadata)
    return intent


def _validate_bar(bar: OhlcvBar, intent: AddExecutionIntent) -> OhlcvBar:
    if not isinstance(bar, OhlcvBar):
        raise TypeError("execution_bar must be an OhlcvBar")
    timestamp = require_utc_datetime(bar.timestamp, "execution_bar.timestamp")
    if timestamp != intent.eligible_bar_at:
        raise ValueError("execution_bar must be the intent's first eligible full bar")
    if bar.symbol != intent.symbol:
        raise ValueError("execution_bar symbol must match intent symbol")
    if bar.timeframe != intent.timeframe:
        raise ValueError("execution_bar timeframe must match intent timeframe")
    open_price = _positive(bar.open, "execution_bar.open")
    high = _positive(bar.high, "execution_bar.high")
    low = _positive(bar.low, "execution_bar.low")
    close = _positive(bar.close, "execution_bar.close")
    _non_negative(bar.volume, "execution_bar.volume")
    _string(bar.exchange, "execution_bar.exchange")
    _string(bar.provider, "execution_bar.provider")
    require_utc_datetime(bar.ingested_at, "execution_bar.ingested_at")
    if high < max(open_price, close) or low > min(open_price, close) or high < low:
        raise ValueError("execution_bar has impossible OHLC geometry")
    return bar


def _validate_costs(costs: ExecutionCosts) -> None:
    if not isinstance(costs, ExecutionCosts):
        raise TypeError("costs must be an ExecutionCosts")
    if costs.policy_version != EXECUTION_COST_POLICY_VERSION:
        raise ValueError(
            f"costs.policy_version must be {EXECUTION_COST_POLICY_VERSION}",
        )


def _validate_upstream(value: Any, name: str, attributes: tuple[str, ...]) -> None:
    for attribute in attributes:
        if not hasattr(value, attribute):
            raise TypeError(f"{name} must expose {attribute}")
    if not callable(getattr(value, "as_record", None)):
        raise TypeError(f"{name} must expose as_record()")


def _bar_record(bar: OhlcvBar) -> dict[str, Any]:
    return {
        "timestamp": bar.timestamp.isoformat(),
        "exchange": bar.exchange,
        "symbol": bar.symbol,
        "timeframe": bar.timeframe,
        "open": str(bar.open),
        "high": str(bar.high),
        "low": str(bar.low),
        "close": str(bar.close),
        "volume": str(bar.volume),
        "provider": bar.provider,
        "ingested_at": bar.ingested_at.isoformat(),
    }


def _config_metadata(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError("config_metadata must be a mapping")
    metadata = dict(value)
    if set(metadata) != set(_REQUIRED_CONFIG_METADATA_KEYS):
        raise ValueError(
            f"config_metadata must exactly contain {_REQUIRED_CONFIG_METADATA_KEYS}",
        )
    for key in _REQUIRED_CONFIG_METADATA_KEYS:
        if not isinstance(metadata[key], str) or not metadata[key].strip():
            raise ValueError(f"config_metadata.{key} must be a non-empty string")
    return metadata


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _optional_positive_integer(value: Any, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer or None")
    return value


def _decimal(value: Any, name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except Exception as error:  # noqa: BLE001 - surfaced as a domain error
        raise ValueError(f"{name} must be numeric") from error
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    return result


def _positive(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


def _non_negative(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


def _optional_decimal_string(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


__all__ = [
    "ADD_ACTION",
    "ADD_CANCELLED",
    "ADD_EXECUTION_FEATURE_ID",
    "ADD_EXECUTION_POLICY_VERSION",
    "ADD_EXECUTION_REASON_CODES",
    "ADD_EXECUTION_STATUSES",
    "ADD_FILLED",
    "AddExecutionIntent",
    "SimulatedAddExecution",
    "simulate_add_execution",
]
