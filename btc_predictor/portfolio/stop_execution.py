"""Deterministic simulated stop execution (BTC-162).

A stop is a resting order, which makes it different from a BTC-161 entry in one
important way: an entry that does not fill on its one eligible bar is terminally
missed, whereas a stop that is not touched simply stays live. Only the touch is
decided here, one bar at a time.

The gap case is the reason this ticket exists. A long stop is touched when the
bar trades at or below it, but the price you actually get depends on how the bar
opened:

    opened above the stop  -> the stop price is reachable, fill there
    opened at or below it  -> the market gapped through, fill at the open

Filling a gapped stop at the stop price would quietly assume liquidity that was
never there, and every downstream risk number would inherit that fiction. So the
result reports ``planned_loss`` -- the loss BTC-146 sized the position against --
beside the ``realized_loss`` actually taken, and flags the difference. A gap is
precisely the event that breaks the risk-at-stop constraint, and it should be
visible in the record rather than absorbed silently.

Partial position state means a trimmed position: BTC-157 may have reduced the
open quantity, and the stop covers whatever remains, not the size originally
entered. Partial *fills* of the stop order itself are not modelled, because
intrabar liquidity is unknowable from OHLCV; the stop is all-or-nothing on the
remaining quantity.
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
from btc_predictor.quant.portfolio import position_notional
from btc_predictor.quant.risk import POSITION_SIDES


STOP_EXECUTION_FEATURE_ID = "SIMULATED_STOP_EXECUTION"
STOP_EXECUTION_POLICY_VERSION = "SIMULATED_STOP_EXECUTION_V1"

STOP_FILLED = "filled"
STOP_RESTING = "submitted"
STOP_EXECUTION_STATUSES = (STOP_FILLED, STOP_RESTING)

EXIT_ACTION = "EXIT"
STOP_ORDER = "stop"

LONG_DIRECTION = "long"
SHORT_DIRECTION = "short"

STOP_EXECUTION_REASON_CODES = (
    "STOP_NOT_TOUCHED",
    "STOP_TOUCHED",
    "STOP_FILL_AT_STOP_PRICE",
    "STOP_FILL_AT_GAP_OPEN",
    "STOP_EXECUTION_COSTS_APPLIED",
    "STOP_EXECUTION_FILLED",
    "STOP_EXECUTION_RESTING",
    "STOP_LOSS_EXCEEDED_PLANNED_RISK",
)

_REQUIRED_CONFIG_METADATA_KEYS = (
    "config_version",
    "strategy_version",
    "parameter_set_id",
)


@dataclass(frozen=True)
class StopExecutionIntent:
    """A resting stop over whatever quantity a position still holds."""

    execution_id: str
    position_id: int | None
    symbol: str
    direction: str
    timeframe: str
    stop_price: Decimal
    stop_placed_at: datetime
    average_entry_price: Decimal
    open_quantity: Decimal
    config_metadata: dict[str, str]

    @property
    def side(self) -> str:
        """Exiting a long sells; exiting a short buys."""

        return SELL_SIDE if self.direction == LONG_DIRECTION else BUY_SIDE

    @property
    def eligible_bar_at(self) -> datetime:
        return next_eligible_bar_timestamp(self.stop_placed_at, self.timeframe)

    @property
    def planned_loss(self) -> Decimal:
        """The loss BTC-146 sized this position against: Q * |entry - stop|."""

        return self.open_quantity * abs(self.average_entry_price - self.stop_price)

    def as_record(self) -> dict[str, Any]:
        values = _validate_intent(self)
        return {
            "execution_id": values.execution_id,
            "position_id": values.position_id,
            "symbol": values.symbol,
            "direction": values.direction,
            "side": values.side,
            "timeframe": values.timeframe,
            "stop_price": str(values.stop_price),
            "stop_placed_at": values.stop_placed_at.isoformat(),
            "eligible_bar_at": values.eligible_bar_at.isoformat(),
            "average_entry_price": str(values.average_entry_price),
            "open_quantity": str(values.open_quantity),
            "planned_loss": str(values.planned_loss),
            "config_metadata": dict(values.config_metadata),
        }


@dataclass(frozen=True)
class SimulatedStopExecution:
    """A stop-out or an untouched resting stop, with evidence for replay."""

    feature_id: str
    policy_version: str
    intent: StopExecutionIntent
    execution_bar: OhlcvBar
    costs: ExecutionCosts
    status: str
    action: str | None
    triggered: bool
    gapped: bool
    reference_price: Decimal | None
    average_fill_price: Decimal | None
    filled_quantity: Decimal
    notional: Decimal
    fee: Decimal
    slippage_cost: Decimal
    planned_loss: Decimal
    realized_loss: Decimal | None
    excess_loss: Decimal | None
    resolved_at: datetime
    complete: bool
    reason_codes: tuple[str, ...]

    @property
    def filled(self) -> bool:
        return self.status == STOP_FILLED

    @property
    def resting(self) -> bool:
        return self.status == STOP_RESTING

    def as_record(self) -> dict[str, Any]:
        """Return a self-validating replay record."""

        if self.feature_id != STOP_EXECUTION_FEATURE_ID:
            raise ValueError(f"feature_id must be {STOP_EXECUTION_FEATURE_ID}")
        if self.policy_version != STOP_EXECUTION_POLICY_VERSION:
            raise ValueError(f"policy_version must be {STOP_EXECUTION_POLICY_VERSION}")
        expected = _simulate(self.intent, self.execution_bar, self.costs)
        actual = (
            self.status,
            self.action,
            self.triggered,
            self.gapped,
            self.reference_price,
            self.average_fill_price,
            self.filled_quantity,
            self.notional,
            self.fee,
            self.slippage_cost,
            self.planned_loss,
            self.realized_loss,
            self.excess_loss,
            require_utc_datetime(self.resolved_at, "resolved_at"),
            self.complete,
            self.reason_codes,
        )
        if actual != expected:
            raise ValueError("stop execution fields do not match replayed evidence")
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "intent": self.intent.as_record(),
            "execution_bar": _bar_record(self.execution_bar),
            "costs": self.costs.as_record(),
            "status": self.status,
            "action": self.action,
            "order_type": STOP_ORDER,
            "triggered": self.triggered,
            "gapped": self.gapped,
            "reference_price": _optional_decimal_string(self.reference_price),
            "average_fill_price": _optional_decimal_string(self.average_fill_price),
            "filled_quantity": str(self.filled_quantity),
            "notional": str(self.notional),
            "fee": str(self.fee),
            "slippage_cost": str(self.slippage_cost),
            "planned_loss": str(self.planned_loss),
            "realized_loss": _optional_decimal_string(self.realized_loss),
            "excess_loss": _optional_decimal_string(self.excess_loss),
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
            "recommendation_id": None,
            # An untouched stop is still working, so it stays submitted rather
            # than being cancelled or reported as a miss.
            "action": EXIT_ACTION,
            "side": self.intent.side,
            "order_type": STOP_ORDER,
            "status": self.status,
            "created_at": self.intent.stop_placed_at,
            "submitted_at": self.intent.eligible_bar_at,
            # Intrabar ordering is unknowable from OHLCV, so a fill is recorded
            # when the bar resolves, never at an invented tick time.
            "filled_at": self.resolved_at if self.filled else None,
            "requested_quantity": self.intent.open_quantity,
            "filled_quantity": self.filled_quantity,
            "limit_price": None,
            "stop_price": self.intent.stop_price,
            "average_fill_price": self.average_fill_price,
        }


def simulate_stop_execution(
    intent: StopExecutionIntent,
    execution_bar: OhlcvBar,
    *,
    costs: ExecutionCosts,
) -> SimulatedStopExecution:
    """Resolve a resting stop against one bar."""

    decision = _simulate(intent, execution_bar, costs)
    return SimulatedStopExecution(
        feature_id=STOP_EXECUTION_FEATURE_ID,
        policy_version=STOP_EXECUTION_POLICY_VERSION,
        intent=intent,
        execution_bar=execution_bar,
        costs=costs,
        status=decision[0],
        action=decision[1],
        triggered=decision[2],
        gapped=decision[3],
        reference_price=decision[4],
        average_fill_price=decision[5],
        filled_quantity=decision[6],
        notional=decision[7],
        fee=decision[8],
        slippage_cost=decision[9],
        planned_loss=decision[10],
        realized_loss=decision[11],
        excess_loss=decision[12],
        resolved_at=decision[13],
        complete=decision[14],
        reason_codes=decision[15],
    )


def stop_execution_for_position(
    lifecycle: Any,
    execution_bar: OhlcvBar,
    *,
    costs: ExecutionCosts,
    execution_id: str,
    stop_placed_at: datetime,
    position_id: int | None = None,
    config_metadata: Mapping[str, str] | None = None,
) -> SimulatedStopExecution:
    """Canonical path: resolve the stop a BTC-150 position actually carries.

    Direction, the standing stop, the weighted average entry and the remaining
    quantity all come from the ledger, so a trimmed position cannot be stopped
    out for the size it originally entered.
    """

    stop_price = getattr(lifecycle, "stop_price", None)
    if stop_price is None:
        raise ValueError("lifecycle must carry a stop price")
    average_entry_price = getattr(lifecycle, "average_entry_price", None)
    if average_entry_price is None:
        raise ValueError("lifecycle must carry an average entry price")
    intent = StopExecutionIntent(
        execution_id=execution_id,
        position_id=position_id,
        symbol=getattr(lifecycle, "symbol", ""),
        direction=getattr(lifecycle, "direction", ""),
        timeframe=execution_bar.timeframe,
        stop_price=stop_price,
        stop_placed_at=stop_placed_at,
        average_entry_price=average_entry_price,
        open_quantity=getattr(lifecycle, "quantity", Decimal("0")),
        config_metadata=dict(
            config_metadata or getattr(lifecycle, "config_metadata", {})
        ),
    )
    return simulate_stop_execution(intent, execution_bar, costs=costs)


def restore_simulated_stop_execution(
    record: Mapping[str, Any],
) -> SimulatedStopExecution:
    """Restore a persisted result and reject incomplete or altered records."""

    if not isinstance(record, Mapping):
        raise TypeError("record must be a mapping")
    source = dict(record)
    raw_intent = _mapping(source.get("intent"), "intent")
    raw_bar = _mapping(source.get("execution_bar"), "execution_bar")
    raw_costs = _mapping(source.get("costs"), "costs")
    intent = StopExecutionIntent(
        execution_id=_string(raw_intent.get("execution_id"), "execution_id"),
        position_id=_optional_positive_integer(
            raw_intent.get("position_id"),
            "position_id",
        ),
        symbol=_string(raw_intent.get("symbol"), "symbol"),
        direction=_string(raw_intent.get("direction"), "direction"),
        timeframe=_string(raw_intent.get("timeframe"), "timeframe"),
        stop_price=_positive(raw_intent.get("stop_price"), "stop_price"),
        stop_placed_at=_utc(raw_intent.get("stop_placed_at"), "stop_placed_at"),
        average_entry_price=_positive(
            raw_intent.get("average_entry_price"),
            "average_entry_price",
        ),
        open_quantity=_positive(raw_intent.get("open_quantity"), "open_quantity"),
        config_metadata=_config_metadata(raw_intent.get("config_metadata")),
    )
    bar = OhlcvBar(
        timestamp=_utc(raw_bar.get("timestamp"), "execution_bar.timestamp"),
        exchange=_string(raw_bar.get("exchange"), "execution_bar.exchange"),
        symbol=_string(raw_bar.get("symbol"), "execution_bar.symbol"),
        timeframe=_string(raw_bar.get("timeframe"), "execution_bar.timeframe"),
        open=_positive(raw_bar.get("open"), "execution_bar.open"),
        high=_positive(raw_bar.get("high"), "execution_bar.high"),
        low=_positive(raw_bar.get("low"), "execution_bar.low"),
        close=_positive(raw_bar.get("close"), "execution_bar.close"),
        volume=_non_negative(raw_bar.get("volume"), "execution_bar.volume"),
        provider=_string(raw_bar.get("provider"), "execution_bar.provider"),
        ingested_at=_utc(raw_bar.get("ingested_at"), "execution_bar.ingested_at"),
    )
    costs = ExecutionCosts(
        policy_version=_string(raw_costs.get("policy_version"), "costs.policy_version"),
        fee_bps=_non_negative(raw_costs.get("fee_bps"), "costs.fee_bps"),
        slippage_bps=_non_negative(raw_costs.get("slippage_bps"), "costs.slippage_bps"),
        funding_cost_bps_per_day=_non_negative(
            raw_costs.get("funding_cost_bps_per_day"),
            "costs.funding_cost_bps_per_day",
        ),
    )
    result = simulate_stop_execution(intent, bar, costs=costs)
    if result.as_record() != source:
        raise ValueError("record does not match reconstructed stop execution")
    return result


def _simulate(
    intent: StopExecutionIntent,
    execution_bar: OhlcvBar,
    costs: ExecutionCosts,
) -> tuple[Any, ...]:
    values = _validate_intent(intent)
    bar = _validate_bar(execution_bar, values)
    _validate_costs(costs)
    resolved_at = max(
        next_bar_timestamp(bar.timestamp, bar.timeframe),
        bar.ingested_at,
    )
    planned_loss = values.planned_loss
    long_position = values.direction == LONG_DIRECTION
    touched = (
        bar.low <= values.stop_price if long_position else bar.high >= values.stop_price
    )

    if not touched:
        return (
            STOP_RESTING,
            None,
            False,
            False,
            None,
            None,
            Decimal("0"),
            Decimal("0"),
            Decimal("0"),
            Decimal("0"),
            planned_loss,
            None,
            None,
            resolved_at,
            True,
            ("STOP_NOT_TOUCHED", "STOP_EXECUTION_RESTING"),
        )

    # The gap test is on the open, not the low: a bar that opened beyond the
    # stop never offered the stop price at all.
    gapped = (
        bar.open <= values.stop_price if long_position else bar.open >= values.stop_price
    )
    reference_price = bar.open if gapped else values.stop_price
    reference_reason = (
        "STOP_FILL_AT_GAP_OPEN" if gapped else "STOP_FILL_AT_STOP_PRICE"
    )

    fill_price = costs.fill_price(reference_price, side=values.side)
    reference_notional = _quant_notional(values.open_quantity, reference_price)
    notional = _quant_notional(values.open_quantity, fill_price)
    fee = costs.fee(notional)
    slippage_cost = abs(notional - reference_notional)
    realized_loss = (
        values.open_quantity * (values.average_entry_price - fill_price)
        if long_position
        else values.open_quantity * (fill_price - values.average_entry_price)
    ) + fee
    excess_loss = realized_loss - planned_loss

    reasons = ["STOP_TOUCHED", reference_reason, "STOP_EXECUTION_COSTS_APPLIED"]
    if excess_loss > 0:
        # BTC-146 sized this position assuming a fill at the stop. A gap or
        # adverse slippage breaks that assumption, and the record says so.
        reasons.append("STOP_LOSS_EXCEEDED_PLANNED_RISK")
    reasons.append("STOP_EXECUTION_FILLED")

    return (
        STOP_FILLED,
        EXIT_ACTION,
        True,
        gapped,
        reference_price,
        fill_price,
        values.open_quantity,
        notional,
        fee,
        slippage_cost,
        planned_loss,
        realized_loss,
        excess_loss,
        resolved_at,
        True,
        tuple(reasons),
    )


def _validate_intent(intent: StopExecutionIntent) -> StopExecutionIntent:
    if not isinstance(intent, StopExecutionIntent):
        raise TypeError("intent must be a StopExecutionIntent")
    _string(intent.execution_id, "execution_id")
    _optional_positive_integer(intent.position_id, "position_id")
    _string(intent.symbol, "symbol")
    if intent.direction not in POSITION_SIDES:
        raise ValueError(f"direction must be one of {POSITION_SIDES}")
    if intent.timeframe not in SUPPORTED_TIMEFRAMES:
        raise ValueError(f"timeframe must be one of {SUPPORTED_TIMEFRAMES}")
    _positive(intent.stop_price, "stop_price")
    require_utc_datetime(intent.stop_placed_at, "stop_placed_at")
    entry = _positive(intent.average_entry_price, "average_entry_price")
    # A stop on the wrong side of the entry would report a "loss" that is
    # actually locked-in profit; BTC-142 and BTC-156 both forbid it.
    if intent.direction == LONG_DIRECTION:
        if intent.stop_price >= entry:
            raise ValueError("a long stop must sit below the average entry price")
    elif intent.stop_price <= entry:
        raise ValueError("a short stop must sit above the average entry price")
    _positive(intent.open_quantity, "open_quantity")
    _config_metadata(intent.config_metadata)
    return intent


def _validate_bar(bar: OhlcvBar, intent: StopExecutionIntent) -> OhlcvBar:
    if not isinstance(bar, OhlcvBar):
        raise TypeError("execution_bar must be an OhlcvBar")
    timestamp = require_utc_datetime(bar.timestamp, "execution_bar.timestamp")
    if bar.symbol != intent.symbol:
        raise ValueError("execution_bar symbol must match intent symbol")
    if bar.timeframe != intent.timeframe:
        raise ValueError("execution_bar timeframe must match intent timeframe")
    if next_eligible_bar_timestamp(timestamp, bar.timeframe) != timestamp:
        raise ValueError("execution_bar timestamp must be on a canonical bar boundary")
    if timestamp < intent.eligible_bar_at:
        # A stop cannot fill on a bar that closed before it was placed.
        raise ValueError("execution_bar must not precede the stop's first eligible bar")
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


def _quant_notional(quantity: Decimal, price: Decimal) -> Decimal:
    """Decimal notional pinned to the BTC-047 kernel by parity test."""

    return quantity * price


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


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return dict(value)


def _config_metadata(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError("config_metadata must be a mapping")
    metadata = dict(value)
    if set(metadata) != set(_REQUIRED_CONFIG_METADATA_KEYS):
        raise ValueError(
            "config_metadata must exactly contain "
            f"{_REQUIRED_CONFIG_METADATA_KEYS}",
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


def _utc(value: Any, name: str) -> datetime:
    if isinstance(value, str):
        return require_utc_datetime(datetime.fromisoformat(value), name)
    return require_utc_datetime(value, name)


def _optional_decimal_string(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


__all__ = [
    "EXIT_ACTION",
    "STOP_EXECUTION_FEATURE_ID",
    "STOP_EXECUTION_POLICY_VERSION",
    "STOP_EXECUTION_REASON_CODES",
    "STOP_EXECUTION_STATUSES",
    "STOP_FILLED",
    "STOP_ORDER",
    "STOP_RESTING",
    "SimulatedStopExecution",
    "StopExecutionIntent",
    "restore_simulated_stop_execution",
    "simulate_stop_execution",
    "stop_execution_for_position",
]
