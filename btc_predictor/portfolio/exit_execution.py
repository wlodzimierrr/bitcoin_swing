"""Deterministic next-bar discretionary exit execution.

BTC-180 routes discretionary exits through this shared portfolio boundary so
the backtest, paper ledger, and later live adapters cannot acquire separate
fill-price or fee formulas. Structural stop exits remain owned by BTC-162.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from btc_predictor.data import OhlcvBar, next_bar_timestamp, require_utc_datetime
from btc_predictor.portfolio.account import (
    BUY_SIDE,
    EXECUTION_COST_POLICY_VERSION,
    SELL_SIDE,
    ExecutionCosts,
)
from btc_predictor.portfolio.entry_execution import next_eligible_bar_timestamp


EXIT_EXECUTION_FEATURE_ID = "SIMULATED_EXIT_EXECUTION"
EXIT_EXECUTION_POLICY_VERSION = "SIMULATED_EXIT_EXECUTION_V1"
EXIT_ACTION = "EXIT"
EXIT_FILLED = "filled"
EXIT_EXECUTION_REASON_CODES = (
    "EXIT_EXECUTION_REFERENCE_BAR_OPEN",
    "EXIT_EXECUTION_COSTS_APPLIED",
    "EXIT_EXECUTION_FILLED",
)
POSITION_SIDES = ("long", "short")
SUPPORTED_TIMEFRAMES = ("1h", "1d", "1w", "1mo")


@dataclass(frozen=True)
class ExitExecutionIntent:
    execution_id: str
    position_id: int | None
    recommendation_id: int | None
    symbol: str
    direction: str
    timeframe: str
    decision_at: datetime
    open_quantity: Decimal
    exit_reason: str
    exit_reason_source_id: str
    config_metadata: dict[str, str]

    @property
    def side(self) -> str:
        return SELL_SIDE if self.direction == "long" else BUY_SIDE

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
            "open_quantity": str(values.open_quantity),
            "exit_reason": values.exit_reason,
            "exit_reason_source_id": values.exit_reason_source_id,
            "config_metadata": dict(values.config_metadata),
        }


@dataclass(frozen=True)
class SimulatedExitExecution:
    feature_id: str
    policy_version: str
    intent: ExitExecutionIntent
    execution_bar: OhlcvBar
    costs: ExecutionCosts
    status: str
    action: str
    reference_price: Decimal
    average_fill_price: Decimal
    filled_quantity: Decimal
    notional: Decimal
    fee: Decimal
    slippage_cost: Decimal
    resolved_at: datetime
    complete: bool
    reason_codes: tuple[str, ...]

    @property
    def filled(self) -> bool:
        return self.status == EXIT_FILLED

    def as_record(self) -> dict[str, Any]:
        if self.feature_id != EXIT_EXECUTION_FEATURE_ID:
            raise ValueError(f"feature_id must be {EXIT_EXECUTION_FEATURE_ID}")
        if self.policy_version != EXIT_EXECUTION_POLICY_VERSION:
            raise ValueError(f"policy_version must be {EXIT_EXECUTION_POLICY_VERSION}")
        expected = _simulate(self.intent, self.execution_bar, self.costs)
        actual = (
            self.status,
            self.action,
            self.reference_price,
            self.average_fill_price,
            self.filled_quantity,
            self.notional,
            self.fee,
            self.slippage_cost,
            require_utc_datetime(self.resolved_at, "resolved_at"),
            self.complete,
            self.reason_codes,
        )
        if actual != expected:
            raise ValueError("exit execution fields do not match replayed evidence")
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "intent": self.intent.as_record(),
            "execution_bar": _bar_record(self.execution_bar),
            "costs": self.costs.as_record(),
            "status": self.status,
            "action": self.action,
            "reference_price": str(self.reference_price),
            "average_fill_price": str(self.average_fill_price),
            "filled_quantity": str(self.filled_quantity),
            "notional": str(self.notional),
            "fee": str(self.fee),
            "slippage_cost": str(self.slippage_cost),
            "resolved_at": self.resolved_at.isoformat(),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def simulate_exit_execution(
    intent: ExitExecutionIntent,
    execution_bar: OhlcvBar,
    *,
    costs: ExecutionCosts,
) -> SimulatedExitExecution:
    decision = _simulate(intent, execution_bar, costs)
    return SimulatedExitExecution(
        feature_id=EXIT_EXECUTION_FEATURE_ID,
        policy_version=EXIT_EXECUTION_POLICY_VERSION,
        intent=intent,
        execution_bar=execution_bar,
        costs=costs,
        status=decision[0],
        action=decision[1],
        reference_price=decision[2],
        average_fill_price=decision[3],
        filled_quantity=decision[4],
        notional=decision[5],
        fee=decision[6],
        slippage_cost=decision[7],
        resolved_at=decision[8],
        complete=decision[9],
        reason_codes=decision[10],
    )


def restore_simulated_exit_execution(
    record: Mapping[str, Any],
) -> SimulatedExitExecution:
    """Restore an exit by replaying its intent, bar, and cost evidence."""

    if not isinstance(record, Mapping):
        raise TypeError("record must be a mapping")
    source = dict(record)
    raw_intent = _mapping(source.get("intent"), "intent")
    raw_bar = _mapping(source.get("execution_bar"), "execution_bar")
    raw_costs = _mapping(source.get("costs"), "costs")
    intent = ExitExecutionIntent(
        execution_id=_identifier(raw_intent.get("execution_id"), "execution_id"),
        position_id=_optional_positive_integer(raw_intent.get("position_id"), "position_id"),
        recommendation_id=_optional_positive_integer(
            raw_intent.get("recommendation_id"), "recommendation_id"
        ),
        symbol=_identifier(raw_intent.get("symbol"), "symbol"),
        direction=_identifier(raw_intent.get("direction"), "direction"),
        timeframe=_identifier(raw_intent.get("timeframe"), "timeframe"),
        decision_at=_utc(raw_intent.get("decision_at"), "decision_at"),
        open_quantity=_positive(raw_intent.get("open_quantity"), "open_quantity"),
        exit_reason=_identifier(raw_intent.get("exit_reason"), "exit_reason"),
        exit_reason_source_id=_identifier(
            raw_intent.get("exit_reason_source_id"), "exit_reason_source_id"
        ),
        config_metadata=_config_metadata(raw_intent.get("config_metadata")),
    )
    bar = OhlcvBar(
        timestamp=_utc(raw_bar.get("timestamp"), "execution_bar.timestamp"),
        exchange=_identifier(raw_bar.get("exchange"), "execution_bar.exchange"),
        symbol=_identifier(raw_bar.get("symbol"), "execution_bar.symbol"),
        timeframe=_identifier(raw_bar.get("timeframe"), "execution_bar.timeframe"),
        open=_positive(raw_bar.get("open"), "execution_bar.open"),
        high=_positive(raw_bar.get("high"), "execution_bar.high"),
        low=_positive(raw_bar.get("low"), "execution_bar.low"),
        close=_positive(raw_bar.get("close"), "execution_bar.close"),
        volume=_non_negative(raw_bar.get("volume"), "execution_bar.volume"),
        provider=_identifier(raw_bar.get("provider"), "execution_bar.provider"),
        ingested_at=_utc(raw_bar.get("ingested_at"), "execution_bar.ingested_at"),
    )
    costs = ExecutionCosts(
        policy_version=_identifier(raw_costs.get("policy_version"), "costs.policy_version"),
        fee_bps=_non_negative(raw_costs.get("fee_bps"), "costs.fee_bps"),
        slippage_bps=_non_negative(raw_costs.get("slippage_bps"), "costs.slippage_bps"),
        funding_cost_bps_per_day=_non_negative(
            raw_costs.get("funding_cost_bps_per_day"),
            "costs.funding_cost_bps_per_day",
        ),
    )
    result = simulate_exit_execution(intent, bar, costs=costs)
    if result.as_record() != source:
        raise ValueError("record does not match reconstructed exit execution")
    return result


def _simulate(
    intent: ExitExecutionIntent,
    bar: OhlcvBar,
    costs: ExecutionCosts,
) -> tuple[Any, ...]:
    values = _validate_intent(intent)
    _validate_bar(bar, values)
    _validate_costs(costs)
    reference_price = bar.open
    fill_price = costs.fill_price(reference_price, side=values.side)
    reference_notional = values.open_quantity * reference_price
    notional = values.open_quantity * fill_price
    return (
        EXIT_FILLED,
        EXIT_ACTION,
        reference_price,
        fill_price,
        values.open_quantity,
        notional,
        costs.fee(notional),
        abs(notional - reference_notional),
        max(next_bar_timestamp(bar.timestamp, bar.timeframe), bar.ingested_at),
        True,
        EXIT_EXECUTION_REASON_CODES,
    )


def _validate_intent(intent: ExitExecutionIntent) -> ExitExecutionIntent:
    if not isinstance(intent, ExitExecutionIntent):
        raise TypeError("intent must be an ExitExecutionIntent")
    _identifier(intent.execution_id, "execution_id")
    _optional_positive_integer(intent.position_id, "position_id")
    _optional_positive_integer(intent.recommendation_id, "recommendation_id")
    _identifier(intent.symbol, "symbol")
    if intent.direction not in POSITION_SIDES:
        raise ValueError(f"direction must be one of {POSITION_SIDES}")
    if intent.timeframe not in SUPPORTED_TIMEFRAMES:
        raise ValueError(f"timeframe must be one of {SUPPORTED_TIMEFRAMES}")
    require_utc_datetime(intent.decision_at, "decision_at")
    _positive(intent.open_quantity, "open_quantity")
    _identifier(intent.exit_reason, "exit_reason")
    _identifier(intent.exit_reason_source_id, "exit_reason_source_id")
    _config_metadata(intent.config_metadata)
    return intent


def _validate_bar(bar: OhlcvBar, intent: ExitExecutionIntent) -> None:
    if not isinstance(bar, OhlcvBar):
        raise TypeError("execution_bar must be an OhlcvBar")
    timestamp = require_utc_datetime(bar.timestamp, "execution_bar.timestamp")
    if timestamp != intent.eligible_bar_at:
        raise ValueError("execution_bar must be the intent's first eligible full bar")
    if bar.symbol != intent.symbol or bar.timeframe != intent.timeframe:
        raise ValueError("execution_bar identity must match intent")
    open_price = _positive(bar.open, "execution_bar.open")
    high = _positive(bar.high, "execution_bar.high")
    low = _positive(bar.low, "execution_bar.low")
    close = _positive(bar.close, "execution_bar.close")
    _non_negative(bar.volume, "execution_bar.volume")
    _identifier(bar.exchange, "execution_bar.exchange")
    _identifier(bar.provider, "execution_bar.provider")
    require_utc_datetime(bar.ingested_at, "execution_bar.ingested_at")
    if high < max(open_price, close) or low > min(open_price, close) or high < low:
        raise ValueError("execution_bar has impossible OHLC geometry")


def _validate_costs(costs: ExecutionCosts) -> None:
    if not isinstance(costs, ExecutionCosts):
        raise TypeError("costs must be an ExecutionCosts")
    if costs.policy_version != EXECUTION_COST_POLICY_VERSION:
        raise ValueError(f"costs.policy_version must be {EXECUTION_COST_POLICY_VERSION}")
    _non_negative(costs.fee_bps, "costs.fee_bps")
    _non_negative(costs.slippage_bps, "costs.slippage_bps")
    _non_negative(costs.funding_cost_bps_per_day, "costs.funding_cost_bps_per_day")


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
        raise TypeError("config_metadata must be a mapping")
    metadata = dict(value)
    for key in ("config_version", "strategy_version", "parameter_set_id"):
        _identifier(metadata.get(key), f"config_metadata.{key}")
    if any(not isinstance(key, str) or not isinstance(item, str) for key, item in metadata.items()):
        raise TypeError("config_metadata keys and values must be strings")
    return metadata


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    return dict(value)


def _utc(value: Any, name: str) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError as error:
            raise ValueError(f"{name} must be an ISO-8601 datetime") from error
    return require_utc_datetime(value, name)


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must not be empty")
    return value


def _optional_positive_integer(value: Any, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer or None")
    return value


def _decimal(value: Any, name: str) -> Decimal:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be numeric")
    try:
        result = Decimal(str(value))
    except (TypeError, ValueError, ArithmeticError) as error:
        raise TypeError(f"{name} must be numeric") from error
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


__all__ = [
    "EXIT_ACTION",
    "EXIT_EXECUTION_FEATURE_ID",
    "EXIT_EXECUTION_POLICY_VERSION",
    "EXIT_EXECUTION_REASON_CODES",
    "EXIT_FILLED",
    "ExitExecutionIntent",
    "SimulatedExitExecution",
    "restore_simulated_exit_execution",
    "simulate_exit_execution",
]
