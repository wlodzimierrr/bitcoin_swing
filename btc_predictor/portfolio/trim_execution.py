"""Deterministic simulated trim execution (BTC-164).

A trim is the mirror of a BTC-163 add and shares its shape: BTC-157 decides
*whether* to reduce, this module decides what that costs and what it locks in.
Like an add, a trim is triggered by conditions rather than by price reaching a
level, so it fills at the next full bar's open moved adversely by the BTC-160
cost policy. It reduces, so a long trim sells and a short trim buys -- the
opposite side to an add in the same direction.

Two things a trim needs that an add does not.

A trim **realizes** part of the position. That is the whole point of trimming
into euphoria or a deteriorating Hold Score, so the realized amount is computed
here and reported signed: a defensive trim in the 40-50 Hold band locks in a
loss, and calling that a "profit taken" would misreport it. The figure is what
BTC-160's ``settle_realized_pnl`` consumes.

A trim must stay **strictly partial**. Removing the whole position is an exit,
which is BTC-158's decision with its own rules, so a full reduction is refused
here rather than quietly becoming one. That matches the BTC-150 ledger, which
rejects a trim that would empty the position.

The trim *size* has no rulebook definition. Rulebook 20 and 23 give Hold-Score
bands that say "trim" without saying how much, so ``DEFAULT_TRIM_FRACTION`` is
an explicit provisional placeholder carrying
``PROVISIONAL_RESEARCH_CALIBRATABLE``, overridable per call and persisted on
every result. It is not a calibrated number and does not pretend to be one.
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
from btc_predictor.quant.comparisons import decision_greater_equal
from btc_predictor.quant.risk import POSITION_SIDES


TRIM_EXECUTION_FEATURE_ID = "SIMULATED_TRIM_EXECUTION"
TRIM_EXECUTION_POLICY_VERSION = "SIMULATED_TRIM_EXECUTION_V1"

TRIM_FILLED = "filled"
TRIM_CANCELLED = "cancelled"
TRIM_EXECUTION_STATUSES = (TRIM_FILLED, TRIM_CANCELLED)

TRIM_ACTION = "TRIM"
MARKET_ORDER = "market"

LONG_DIRECTION = "long"

# Rulebook 20 and 23 say "trim" without saying how much. This is a declared
# placeholder, not a calibrated parameter; BTC-185 must set it.
DEFAULT_TRIM_FRACTION = Decimal("0.33")
TRIM_SIZING_PARAMETER_STATUS = "PROVISIONAL_RESEARCH_CALIBRATABLE"

TRIM_EXECUTION_REASON_CODES = (
    "TRIM_EXECUTION_NOT_SIGNALLED",
    "TRIM_EXECUTION_NOT_PARTIAL",
    "TRIM_EXECUTION_REFERENCE_BAR_OPEN",
    "TRIM_EXECUTION_COSTS_APPLIED",
    "TRIM_EXECUTION_REALIZED_PROFIT",
    "TRIM_EXECUTION_REALIZED_LOSS",
    "TRIM_EXECUTION_FILLED",
    "TRIM_EXECUTION_CANCELLED",
)

_REQUIRED_CONFIG_METADATA_KEYS = (
    "config_version",
    "strategy_version",
    "parameter_set_id",
)


@dataclass(frozen=True)
class TrimExecutionIntent:
    """A proposed partial reduction of an open position."""

    execution_id: str
    position_id: int | None
    recommendation_id: int | None
    symbol: str
    direction: str
    timeframe: str
    decision_at: datetime
    average_entry_price: Decimal
    open_quantity: Decimal
    config_metadata: dict[str, str]
    trim_fraction: Decimal = DEFAULT_TRIM_FRACTION

    @property
    def side(self) -> str:
        """Reducing a long sells; reducing a short buys."""

        return SELL_SIDE if self.direction == LONG_DIRECTION else BUY_SIDE

    @property
    def eligible_bar_at(self) -> datetime:
        return next_eligible_bar_timestamp(self.decision_at, self.timeframe)

    @property
    def trim_quantity(self) -> Decimal:
        return self.open_quantity * self.trim_fraction

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
            "open_quantity": str(values.open_quantity),
            "trim_fraction": str(values.trim_fraction),
            "trim_sizing_parameter_status": TRIM_SIZING_PARAMETER_STATUS,
            "trim_quantity": str(values.trim_quantity),
            "config_metadata": dict(values.config_metadata),
        }


@dataclass(frozen=True)
class SimulatedTrimExecution:
    """A partial reduction or a refusal, with the evidence for both."""

    feature_id: str
    policy_version: str
    intent: TrimExecutionIntent
    execution_bar: OhlcvBar
    costs: ExecutionCosts
    signal: Any
    status: str
    action: str
    reference_price: Decimal | None
    average_fill_price: Decimal | None
    requested_quantity: Decimal
    filled_quantity: Decimal
    remaining_quantity: Decimal
    notional: Decimal
    fee: Decimal
    slippage_cost: Decimal
    realized_pnl: Decimal | None
    resolved_at: datetime
    complete: bool
    reason_codes: tuple[str, ...]

    @property
    def filled(self) -> bool:
        return self.status == TRIM_FILLED

    @property
    def cancelled(self) -> bool:
        return self.status == TRIM_CANCELLED

    def as_record(self) -> dict[str, Any]:
        """Return a self-validating record of the decision and the fill."""

        if self.feature_id != TRIM_EXECUTION_FEATURE_ID:
            raise ValueError(f"feature_id must be {TRIM_EXECUTION_FEATURE_ID}")
        if self.policy_version != TRIM_EXECUTION_POLICY_VERSION:
            raise ValueError(f"policy_version must be {TRIM_EXECUTION_POLICY_VERSION}")
        expected = _simulate(
            self.intent,
            self.execution_bar,
            self.costs,
            self.signal,
        )
        actual = (
            self.status,
            self.action,
            self.reference_price,
            self.average_fill_price,
            self.requested_quantity,
            self.filled_quantity,
            self.remaining_quantity,
            self.notional,
            self.fee,
            self.slippage_cost,
            self.realized_pnl,
            require_utc_datetime(self.resolved_at, "resolved_at"),
            self.complete,
            self.reason_codes,
        )
        if actual != expected:
            raise ValueError("trim execution fields do not match replayed evidence")
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "intent": self.intent.as_record(),
            "execution_bar": _bar_record(self.execution_bar),
            "costs": self.costs.as_record(),
            # The BTC-157 decision travels with the fill, so a refusal can be
            # explained without re-running the engine that produced it.
            "signal": self.signal.as_record(),
            "status": self.status,
            "action": self.action,
            "order_type": MARKET_ORDER,
            "reference_price": _optional_decimal_string(self.reference_price),
            "average_fill_price": _optional_decimal_string(self.average_fill_price),
            "requested_quantity": str(self.requested_quantity),
            "filled_quantity": str(self.filled_quantity),
            "remaining_quantity": str(self.remaining_quantity),
            "notional": str(self.notional),
            "fee": str(self.fee),
            "slippage_cost": str(self.slippage_cost),
            "realized_pnl": _optional_decimal_string(self.realized_pnl),
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
            # A refused trim was declined by the system, not prevented by the
            # market, so it is cancelled rather than missed.
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


def simulate_trim_execution(
    intent: TrimExecutionIntent,
    execution_bar: OhlcvBar,
    *,
    signal: Any,
    costs: ExecutionCosts,
) -> SimulatedTrimExecution:
    """Execute a signalled partial reduction on its next eligible bar."""

    decision = _simulate(intent, execution_bar, costs, signal)
    return SimulatedTrimExecution(
        feature_id=TRIM_EXECUTION_FEATURE_ID,
        policy_version=TRIM_EXECUTION_POLICY_VERSION,
        intent=intent,
        execution_bar=execution_bar,
        costs=costs,
        signal=signal,
        status=decision[0],
        action=decision[1],
        reference_price=decision[2],
        average_fill_price=decision[3],
        requested_quantity=decision[4],
        filled_quantity=decision[5],
        remaining_quantity=decision[6],
        notional=decision[7],
        fee=decision[8],
        slippage_cost=decision[9],
        realized_pnl=decision[10],
        resolved_at=decision[11],
        complete=decision[12],
        reason_codes=decision[13],
    )


def _simulate(
    intent: TrimExecutionIntent,
    execution_bar: OhlcvBar,
    costs: ExecutionCosts,
    signal: Any,
) -> tuple[Any, ...]:
    values = _validate_intent(intent)
    bar = _validate_bar(execution_bar, values)
    _validate_costs(costs)
    _validate_signal(signal)
    resolved_at = max(
        next_bar_timestamp(bar.timestamp, bar.timeframe),
        bar.ingested_at,
    )
    requested_quantity = values.trim_quantity

    def cancelled(reason_codes: tuple[str, ...]) -> tuple[Any, ...]:
        return (
            TRIM_CANCELLED,
            TRIM_ACTION,
            None,
            None,
            requested_quantity,
            Decimal("0"),
            values.open_quantity,
            Decimal("0"),
            Decimal("0"),
            Decimal("0"),
            None,
            resolved_at,
            True,
            reason_codes,
        )

    if not signal.signal:
        return cancelled(
            ("TRIM_EXECUTION_NOT_SIGNALLED",)
            + tuple(signal.reason_codes)
            + ("TRIM_EXECUTION_CANCELLED",)
        )
    if decision_greater_equal(requested_quantity, values.open_quantity):
        # Removing everything is an exit, which is BTC-158's decision with its
        # own rules, and the BTC-150 ledger rejects it as a trim.
        return cancelled(
            ("TRIM_EXECUTION_NOT_PARTIAL", "TRIM_EXECUTION_CANCELLED"),
        )

    reference_price = _positive(bar.open, "execution_bar.open")
    fill_price = costs.fill_price(reference_price, side=values.side)
    reference_notional = requested_quantity * reference_price
    notional = requested_quantity * fill_price
    fee = costs.fee(notional)
    gross = (
        requested_quantity * (fill_price - values.average_entry_price)
        if values.direction == LONG_DIRECTION
        else requested_quantity * (values.average_entry_price - fill_price)
    )
    realized_pnl = gross - fee

    reasons = ["TRIM_EXECUTION_REFERENCE_BAR_OPEN", "TRIM_EXECUTION_COSTS_APPLIED"]
    # A defensive trim in the 40-50 Hold band locks in a loss. Reporting that
    # as profit taken would misstate the trade.
    reasons.append(
        "TRIM_EXECUTION_REALIZED_PROFIT"
        if realized_pnl > 0
        else "TRIM_EXECUTION_REALIZED_LOSS"
    )
    reasons.append("TRIM_EXECUTION_FILLED")

    return (
        TRIM_FILLED,
        TRIM_ACTION,
        reference_price,
        fill_price,
        requested_quantity,
        requested_quantity,
        values.open_quantity - requested_quantity,
        notional,
        fee,
        abs(notional - reference_notional),
        realized_pnl,
        resolved_at,
        True,
        tuple(reasons),
    )


def _validate_intent(intent: TrimExecutionIntent) -> TrimExecutionIntent:
    if not isinstance(intent, TrimExecutionIntent):
        raise TypeError("intent must be a TrimExecutionIntent")
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
    _positive(intent.open_quantity, "open_quantity")
    fraction = _positive(intent.trim_fraction, "trim_fraction")
    if fraction > 1:
        raise ValueError("trim_fraction must be between 0 and 1")
    _config_metadata(intent.config_metadata)
    return intent


def _validate_bar(bar: OhlcvBar, intent: TrimExecutionIntent) -> OhlcvBar:
    if not isinstance(bar, OhlcvBar):
        raise TypeError("execution_bar must be an OhlcvBar")
    timestamp = require_utc_datetime(bar.timestamp, "execution_bar.timestamp")
    if bar.symbol != intent.symbol:
        raise ValueError("execution_bar symbol must match intent symbol")
    if bar.timeframe != intent.timeframe:
        raise ValueError("execution_bar timeframe must match intent timeframe")
    if timestamp != intent.eligible_bar_at:
        raise ValueError("execution_bar must be the intent's first eligible full bar")
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


def _validate_signal(signal: Any) -> None:
    for attribute in ("signal", "reason_codes"):
        if not hasattr(signal, attribute):
            raise TypeError(f"signal must expose {attribute}")
    if not callable(getattr(signal, "as_record", None)):
        raise TypeError("signal must expose as_record()")


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
    "DEFAULT_TRIM_FRACTION",
    "MARKET_ORDER",
    "TRIM_ACTION",
    "TRIM_CANCELLED",
    "TRIM_EXECUTION_FEATURE_ID",
    "TRIM_EXECUTION_POLICY_VERSION",
    "TRIM_EXECUTION_REASON_CODES",
    "TRIM_EXECUTION_STATUSES",
    "TRIM_FILLED",
    "TRIM_SIZING_PARAMETER_STATUS",
    "SimulatedTrimExecution",
    "TrimExecutionIntent",
    "simulate_trim_execution",
]
