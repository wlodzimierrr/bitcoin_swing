"""Deterministic simulated stop execution (BTC-162).

A stop is a resting order, which makes it different from a BTC-161 entry in one
important way: an entry that does not fill on its one eligible bar is terminally
missed, whereas a stop that is not touched simply stays live. Only the touch is
decided here, one bar at a time.

The gap case is the reason this ticket exists. A long stop is touched when the
bar trades at or below it, but the price you actually get depends on how the bar
opened:

    opened at/above stop (long) -> stop price is reachable, fill there
    opened below stop (long)    -> market gapped through, fill at the open

Filling a gapped stop at the stop price would quietly assume liquidity that was
never there, and every downstream risk number would inherit that fiction. The
result therefore reports BTC-146's tranche-level, floored downside risk
separately from signed gross and net P&L. A profitable trailing stop has zero
remaining downside risk and positive P&L; those are different facts and must
not be collapsed into an absolute-distance "loss".

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
from btc_predictor.quant.comparisons import (
    decision_equal,
    decision_greater,
    decision_greater_equal,
    decision_less,
    decision_less_equal,
)
from btc_predictor.quant.portfolio import position_notional
from btc_predictor.quant.risk import POSITION_SIDES


STOP_EXECUTION_FEATURE_ID = "SIMULATED_STOP_EXECUTION"
STOP_EXECUTION_POLICY_VERSION = "SIMULATED_STOP_EXECUTION_V1"

STOP_FILLED = "filled"
STOP_RESTING = "submitted"
STOP_EXECUTION_STATUSES = (STOP_FILLED, STOP_RESTING)

EXIT_ACTION = "EXIT"
STOP_ORDER = "stop"
STOP_RISK_CONVENTION = "FLOORED_AT_ZERO"

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
class StopExecutionTranche:
    """One remaining BTC-150 tranche at stop-evaluation time."""

    tranche_id: str
    entry_price: Decimal
    quantity: Decimal

    def as_record(self) -> dict[str, str]:
        return {
            "tranche_id": _string(self.tranche_id, "tranche_id"),
            "entry_price": str(_positive(self.entry_price, "tranche.entry_price")),
            "quantity": str(_positive(self.quantity, "tranche.quantity")),
        }


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
    tranches: tuple[StopExecutionTranche, ...] = ()

    @property
    def side(self) -> str:
        """Exiting a long sells; exiting a short buys."""

        return SELL_SIDE if self.direction == LONG_DIRECTION else BUY_SIDE

    @property
    def eligible_bar_at(self) -> datetime:
        return next_eligible_bar_timestamp(self.stop_placed_at, self.timeframe)

    @property
    def planned_downside_risk(self) -> Decimal:
        """BTC-146 FLOORED_AT_ZERO downside risk at the standing stop."""

        return sum(
            (
                tranche.quantity
                * max(
                    (
                        tranche.entry_price - self.stop_price
                        if self.direction == LONG_DIRECTION
                        else self.stop_price - tranche.entry_price
                    ),
                    Decimal("0"),
                )
                for tranche in _effective_tranches(self)
            ),
            Decimal("0"),
        )

    @property
    def planned_gross_pnl(self) -> Decimal:
        """Signed gross P&L if the stop fills exactly at its price."""

        return sum(
            (
                tranche.quantity
                * (
                    self.stop_price - tranche.entry_price
                    if self.direction == LONG_DIRECTION
                    else tranche.entry_price - self.stop_price
                )
                for tranche in _effective_tranches(self)
            ),
            Decimal("0"),
        )

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
            "risk_at_stop_convention": STOP_RISK_CONVENTION,
            "planned_downside_risk": str(values.planned_downside_risk),
            "planned_gross_pnl": str(values.planned_gross_pnl),
            "tranches": [tranche.as_record() for tranche in values.tranches],
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
    planned_downside_risk: Decimal
    planned_gross_pnl: Decimal
    gross_pnl: Decimal | None
    net_pnl: Decimal | None
    realized_loss: Decimal | None
    execution_shortfall: Decimal | None
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
            self.planned_downside_risk,
            self.planned_gross_pnl,
            self.gross_pnl,
            self.net_pnl,
            self.realized_loss,
            self.execution_shortfall,
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
            "risk_at_stop_convention": STOP_RISK_CONVENTION,
            "planned_downside_risk": str(self.planned_downside_risk),
            "planned_gross_pnl": str(self.planned_gross_pnl),
            "gross_pnl": _optional_decimal_string(self.gross_pnl),
            "net_pnl": _optional_decimal_string(self.net_pnl),
            "realized_loss": _optional_decimal_string(self.realized_loss),
            "execution_shortfall": _optional_decimal_string(
                self.execution_shortfall
            ),
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
        if (
            position_id is not None
            and self.intent.position_id is not None
            and position_id != self.intent.position_id
        ):
            raise ValueError("position_id must match the execution intent")
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
        planned_downside_risk=decision[10],
        planned_gross_pnl=decision[11],
        gross_pnl=decision[12],
        net_pnl=decision[13],
        realized_loss=decision[14],
        execution_shortfall=decision[15],
        excess_loss=decision[16],
        resolved_at=decision[17],
        complete=decision[18],
        reason_codes=decision[19],
    )


def stop_execution_for_position(
    lifecycle: Any,
    execution_bar: OhlcvBar,
    *,
    costs: ExecutionCosts,
    execution_id: str,
    stop_placed_at: datetime | None = None,
    position_id: int | None = None,
    config_metadata: Mapping[str, str] | None = None,
) -> SimulatedStopExecution:
    """Canonical path: resolve the stop a BTC-150 position actually carries.

    Direction, the standing stop, the weighted average entry and the remaining
    quantity all come from the ledger, so a trimmed position cannot be stopped
    out for the size it originally entered.
    """

    from btc_predictor.portfolio.state_machine import PositionLifecycle

    if not isinstance(lifecycle, PositionLifecycle):
        raise TypeError("lifecycle must be a PositionLifecycle")
    stop_price = getattr(lifecycle, "stop_price", None)
    if stop_price is None:
        raise ValueError("lifecycle must carry a stop price")
    average_entry_price = getattr(lifecycle, "average_entry_price", None)
    if average_entry_price is None:
        raise ValueError("lifecycle must carry an average entry price")
    if not getattr(lifecycle, "is_open", False):
        raise ValueError("lifecycle must be an open BTC-150 position")
    ledger_metadata = _config_metadata(getattr(lifecycle, "config_metadata", {}))
    if config_metadata is not None and _config_metadata(config_metadata) != ledger_metadata:
        raise ValueError("config_metadata must match the BTC-150 lifecycle")
    ledger_stop_placed_at = _stop_placement_time(lifecycle, stop_price)
    if stop_placed_at is not None and require_utc_datetime(
        stop_placed_at,
        "stop_placed_at",
    ) != ledger_stop_placed_at:
        raise ValueError("stop_placed_at must match the BTC-150 stop transition")
    lifecycle_tranches = tuple(
        StopExecutionTranche(
            tranche_id=str(getattr(tranche, "tranche_number", "")),
            entry_price=getattr(tranche, "entry_price", Decimal("0")),
            quantity=getattr(tranche, "quantity", Decimal("0")),
        )
        for tranche in getattr(lifecycle, "tranches", ())
    )
    intent = StopExecutionIntent(
        execution_id=execution_id,
        position_id=position_id,
        symbol=getattr(lifecycle, "symbol", ""),
        direction=getattr(lifecycle, "direction", ""),
        timeframe=execution_bar.timeframe,
        stop_price=stop_price,
        stop_placed_at=ledger_stop_placed_at,
        average_entry_price=average_entry_price,
        open_quantity=getattr(lifecycle, "quantity", Decimal("0")),
        config_metadata=ledger_metadata,
        tranches=lifecycle_tranches,
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
    raw_tranches = raw_intent.get("tranches")
    if not isinstance(raw_tranches, list):
        raise ValueError("intent.tranches must be a list")
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
        tranches=tuple(
            StopExecutionTranche(
                tranche_id=_string(
                    _mapping(item, "intent.tranche").get("tranche_id"),
                    "tranche_id",
                ),
                entry_price=_positive(
                    _mapping(item, "intent.tranche").get("entry_price"),
                    "tranche.entry_price",
                ),
                quantity=_positive(
                    _mapping(item, "intent.tranche").get("quantity"),
                    "tranche.quantity",
                ),
            )
            for item in raw_tranches
        ),
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
    planned_downside_risk = values.planned_downside_risk
    planned_gross_pnl = values.planned_gross_pnl
    long_position = values.direction == LONG_DIRECTION
    touched = (
        decision_less_equal(bar.low, values.stop_price)
        if long_position
        else decision_greater_equal(bar.high, values.stop_price)
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
            planned_downside_risk,
            planned_gross_pnl,
            None,
            None,
            None,
            None,
            None,
            resolved_at,
            True,
            ("STOP_NOT_TOUCHED", "STOP_EXECUTION_RESTING"),
        )

    # The gap test is on the open, not the low: a bar that opened beyond the
    # stop never offered the stop price at all.
    gapped = (
        decision_less(bar.open, values.stop_price)
        if long_position
        else decision_greater(bar.open, values.stop_price)
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
    gross_pnl = (
        values.open_quantity * (fill_price - values.average_entry_price)
        if long_position
        else values.open_quantity * (values.average_entry_price - fill_price)
    )
    net_pnl = gross_pnl - fee
    realized_loss = max(-net_pnl, Decimal("0"))
    execution_shortfall = max(planned_gross_pnl - net_pnl, Decimal("0"))
    excess_loss = max(realized_loss - planned_downside_risk, Decimal("0"))

    reasons = ["STOP_TOUCHED", reference_reason, "STOP_EXECUTION_COSTS_APPLIED"]
    if decision_greater(excess_loss, 0):
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
        planned_downside_risk,
        planned_gross_pnl,
        gross_pnl,
        net_pnl,
        realized_loss,
        execution_shortfall,
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
    quantity = _positive(intent.open_quantity, "open_quantity")
    if not isinstance(intent.tranches, tuple):
        raise TypeError("tranches must be a tuple")
    identifiers: list[str] = []
    tranche_quantity = Decimal("0")
    weighted_entry = Decimal("0")
    for tranche in intent.tranches:
        if not isinstance(tranche, StopExecutionTranche):
            raise TypeError("tranches must contain StopExecutionTranche values")
        tranche.as_record()
        identifiers.append(tranche.tranche_id)
        tranche_quantity += tranche.quantity
        weighted_entry += tranche.quantity * tranche.entry_price
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("tranche identifiers must be unique")
    if intent.tranches:
        if not decision_equal(tranche_quantity, quantity):
            raise ValueError("tranche quantity must equal open_quantity")
        if not decision_equal(weighted_entry / tranche_quantity, entry):
            raise ValueError("tranches must reproduce average_entry_price")
    _config_metadata(intent.config_metadata)
    return intent


def _effective_tranches(
    intent: StopExecutionIntent,
) -> tuple[StopExecutionTranche, ...]:
    if intent.tranches:
        return intent.tranches
    return (
        StopExecutionTranche(
            tranche_id="aggregate",
            entry_price=intent.average_entry_price,
            quantity=intent.open_quantity,
        ),
    )


def _stop_placement_time(lifecycle: Any, stop_price: Decimal) -> datetime:
    """Return the authoritative transition that installed the standing stop."""

    for transition in reversed(getattr(lifecycle, "transitions", ())):
        transition_stop = getattr(transition, "stop_price", None)
        if (
            getattr(transition, "accepted", False)
            and transition_stop is not None
            and decision_equal(transition_stop, stop_price)
        ):
            return require_utc_datetime(transition.event_time, "stop transition time")
    raise ValueError("lifecycle does not contain the standing stop transition")


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
    _non_negative(costs.fee_bps, "costs.fee_bps")
    _non_negative(costs.slippage_bps, "costs.slippage_bps")
    _non_negative(
        costs.funding_cost_bps_per_day,
        "costs.funding_cost_bps_per_day",
    )


def _quant_notional(quantity: Decimal, price: Decimal) -> Decimal:
    """Decimal notional pinned to the BTC-047 kernel by parity test."""

    exact = quantity * price
    kernel = Decimal(str(position_notional(float(quantity), float(price))))
    if not decision_equal(exact, kernel):
        raise ArithmeticError("Decimal notional diverged from the BTC-047 kernel")
    return exact


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
    "STOP_RISK_CONVENTION",
    "SimulatedStopExecution",
    "StopExecutionIntent",
    "StopExecutionTranche",
    "restore_simulated_stop_execution",
    "simulate_stop_execution",
    "stop_execution_for_position",
]
