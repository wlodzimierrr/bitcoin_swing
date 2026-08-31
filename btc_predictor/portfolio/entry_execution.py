"""Deterministic next-bar paper entry execution (BTC-161).

An entry is a zone-triggered market order.  The first complete bar beginning
at or after the decision time is the only eligible bar: if it does not touch
the zone, the entry is terminally missed and later bars are never searched.
When a bar opens outside the zone, the nearest boundary is the first price the
bar could have crossed; when it opens inside, its open is the reference.  The
shared BTC-160 cost policy then moves that reference adversely.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from btc_predictor.data import OhlcvBar, SUPPORTED_TIMEFRAMES, next_bar_timestamp
from btc_predictor.data import require_utc_datetime
from btc_predictor.portfolio.account import (
    BUY_SIDE,
    EXECUTION_COST_POLICY_VERSION,
    SELL_SIDE,
    ExecutionCosts,
)
from btc_predictor.quant.portfolio import position_notional
from btc_predictor.quant.risk import POSITION_SIDES


ENTRY_EXECUTION_FEATURE_ID = "SIMULATED_ENTRY_EXECUTION"
ENTRY_EXECUTION_POLICY_VERSION = "SIMULATED_ENTRY_EXECUTION_V1"

ENTRY_FILLED = "filled"
ENTRY_MISSED = "missed"
ENTRY_EXECUTION_STATUSES = (ENTRY_FILLED, ENTRY_MISSED)

ENTER_ACTION = "ENTER"
MISSED_ACTION = "MISSED"
MARKET_ORDER = "market"

ENTRY_EXECUTION_REASON_CODES = (
    "ENTRY_ZONE_TOUCHED",
    "ENTRY_ZONE_NOT_TOUCHED",
    "ENTRY_REFERENCE_BAR_OPEN",
    "ENTRY_REFERENCE_ZONE_LOWER",
    "ENTRY_REFERENCE_ZONE_UPPER",
    "ENTRY_EXECUTION_COSTS_APPLIED",
    "ENTRY_EXECUTION_FILLED",
    "ENTRY_EXECUTION_MISSED",
    "ENTRY_DO_NOT_CHASE",
)

_REQUIRED_CONFIG_METADATA_KEYS = (
    "config_version",
    "strategy_version",
    "parameter_set_id",
)


@dataclass(frozen=True)
class EntryExecutionIntent:
    """Immutable entry instruction available at one point in time."""

    execution_id: str
    recommendation_id: int | None
    symbol: str
    direction: str
    decision_at: datetime
    timeframe: str
    entry_zone_lower: Decimal
    entry_zone_upper: Decimal
    entry_zone_available_at: datetime
    requested_quantity: Decimal
    config_metadata: dict[str, str]
    entry_zone_id: str | None = None

    @property
    def side(self) -> str:
        return BUY_SIDE if self.direction == "long" else SELL_SIDE

    @property
    def eligible_bar_at(self) -> datetime:
        return next_eligible_bar_timestamp(self.decision_at, self.timeframe)

    def as_record(self) -> dict[str, Any]:
        values = _validate_intent(self)
        return {
            "execution_id": values.execution_id,
            "recommendation_id": values.recommendation_id,
            "symbol": values.symbol,
            "direction": values.direction,
            "side": values.side,
            "decision_at": values.decision_at.isoformat(),
            "timeframe": values.timeframe,
            "eligible_bar_at": values.eligible_bar_at.isoformat(),
            "entry_zone_lower": str(values.entry_zone_lower),
            "entry_zone_upper": str(values.entry_zone_upper),
            "entry_zone_available_at": values.entry_zone_available_at.isoformat(),
            "entry_zone_id": values.entry_zone_id,
            "requested_quantity": str(values.requested_quantity),
            "config_metadata": dict(values.config_metadata),
        }


@dataclass(frozen=True)
class SimulatedEntryExecution:
    """A complete fill or terminal miss with enough evidence for replay."""

    feature_id: str
    policy_version: str
    intent: EntryExecutionIntent
    execution_bar: OhlcvBar
    costs: ExecutionCosts
    status: str
    action: str
    reference_price: Decimal | None
    average_fill_price: Decimal | None
    filled_quantity: Decimal
    notional: Decimal
    fee: Decimal
    slippage_cost: Decimal
    resolved_at: datetime
    complete: bool
    reason_codes: tuple[str, ...]

    @property
    def filled(self) -> bool:
        return self.status == ENTRY_FILLED

    @property
    def missed(self) -> bool:
        return self.status == ENTRY_MISSED

    def as_record(self) -> dict[str, Any]:
        """Return a self-validating replay record."""

        if self.feature_id != ENTRY_EXECUTION_FEATURE_ID:
            raise ValueError(f"feature_id must be {ENTRY_EXECUTION_FEATURE_ID}")
        if self.policy_version != ENTRY_EXECUTION_POLICY_VERSION:
            raise ValueError(f"policy_version must be {ENTRY_EXECUTION_POLICY_VERSION}")
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
            raise ValueError("entry execution fields do not match replayed evidence")
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "intent": self.intent.as_record(),
            "execution_bar": _bar_record(self.execution_bar),
            "costs": self.costs.as_record(),
            "status": self.status,
            "action": self.action,
            "order_type": MARKET_ORDER,
            "reference_price": _optional_decimal_string(self.reference_price),
            "average_fill_price": _optional_decimal_string(self.average_fill_price),
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
        if isinstance(account_id, bool) or not isinstance(account_id, int) or account_id < 1:
            raise ValueError("account_id must be a positive integer")
        if position_id is not None and (
            isinstance(position_id, bool)
            or not isinstance(position_id, int)
            or position_id < 1
        ):
            raise ValueError("position_id must be a positive integer or None")
        return {
            "account_id": account_id,
            "position_id": position_id,
            "recommendation_id": self.intent.recommendation_id,
            "action": self.action,
            "side": self.intent.side,
            "order_type": MARKET_ORDER,
            "status": self.status,
            "created_at": self.intent.decision_at,
            "submitted_at": self.intent.eligible_bar_at,
            # Intrabar ordering is unknowable from OHLCV.  A fill is therefore
            # recorded when the bar resolves, never at an invented tick time.
            "filled_at": self.resolved_at if self.filled else None,
            "requested_quantity": self.intent.requested_quantity,
            "filled_quantity": self.filled_quantity,
            "limit_price": None,
            "stop_price": None,
            "average_fill_price": self.average_fill_price,
        }


def simulate_next_bar_entry(
    intent: EntryExecutionIntent,
    execution_bar: OhlcvBar,
    *,
    costs: ExecutionCosts,
) -> SimulatedEntryExecution:
    """Execute an intent on its one eligible bar or mark it missed."""

    decision = _simulate(intent, execution_bar, costs)
    return SimulatedEntryExecution(
        feature_id=ENTRY_EXECUTION_FEATURE_ID,
        policy_version=ENTRY_EXECUTION_POLICY_VERSION,
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


def restore_simulated_entry_execution(
    record: Mapping[str, Any],
) -> SimulatedEntryExecution:
    """Restore a persisted result and reject incomplete or altered records."""

    if not isinstance(record, Mapping):
        raise TypeError("record must be a mapping")
    source = dict(record)
    raw_intent = _mapping(source.get("intent"), "intent")
    raw_bar = _mapping(source.get("execution_bar"), "execution_bar")
    raw_costs = _mapping(source.get("costs"), "costs")
    intent = EntryExecutionIntent(
        execution_id=_string(raw_intent.get("execution_id"), "execution_id"),
        recommendation_id=_optional_positive_integer(
            raw_intent.get("recommendation_id"), "recommendation_id"
        ),
        symbol=_string(raw_intent.get("symbol"), "symbol"),
        direction=_string(raw_intent.get("direction"), "direction"),
        decision_at=_utc(raw_intent.get("decision_at"), "decision_at"),
        timeframe=_string(raw_intent.get("timeframe"), "timeframe"),
        entry_zone_lower=_positive(raw_intent.get("entry_zone_lower"), "entry_zone_lower"),
        entry_zone_upper=_positive(raw_intent.get("entry_zone_upper"), "entry_zone_upper"),
        entry_zone_available_at=_utc(
            raw_intent.get("entry_zone_available_at"), "entry_zone_available_at"
        ),
        entry_zone_id=_optional_string(raw_intent.get("entry_zone_id"), "entry_zone_id"),
        requested_quantity=_positive(
            raw_intent.get("requested_quantity"), "requested_quantity"
        ),
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
    result = simulate_next_bar_entry(intent, bar, costs=costs)
    if result.as_record() != source:
        raise ValueError("record does not match reconstructed entry execution")
    return result


def next_eligible_bar_timestamp(decision_at: datetime, timeframe: str) -> datetime:
    """Return the first canonical full-bar boundary at or after a decision."""

    decision = require_utc_datetime(decision_at, "decision_at")
    if timeframe not in SUPPORTED_TIMEFRAMES:
        raise ValueError(
            f"Unsupported timeframe {timeframe!r}; expected one of: {SUPPORTED_TIMEFRAMES}"
        )
    day = decision.replace(hour=0, minute=0, second=0, microsecond=0)
    if timeframe == "1h":
        boundary = decision.replace(minute=0, second=0, microsecond=0)
    elif timeframe == "1d":
        boundary = day
    elif timeframe == "1w":
        boundary = day - timedelta(days=day.weekday())
    else:
        boundary = day.replace(day=1)
    return boundary if decision == boundary else next_bar_timestamp(boundary, timeframe)


def _simulate(
    intent: EntryExecutionIntent,
    execution_bar: OhlcvBar,
    costs: ExecutionCosts,
) -> tuple[Any, ...]:
    values = _validate_intent(intent)
    bar = _validate_bar(execution_bar, values)
    _validate_costs(costs)
    resolved_at = max(next_bar_timestamp(bar.timestamp, bar.timeframe), bar.ingested_at)
    if bar.high < values.entry_zone_lower or bar.low > values.entry_zone_upper:
        return (
            ENTRY_MISSED,
            MISSED_ACTION,
            None,
            None,
            Decimal("0"),
            Decimal("0"),
            Decimal("0"),
            Decimal("0"),
            resolved_at,
            True,
            (
                "ENTRY_ZONE_NOT_TOUCHED",
                "ENTRY_EXECUTION_MISSED",
                "ENTRY_DO_NOT_CHASE",
            ),
        )

    if bar.open < values.entry_zone_lower:
        reference_price = values.entry_zone_lower
        reference_reason = "ENTRY_REFERENCE_ZONE_LOWER"
    elif bar.open > values.entry_zone_upper:
        reference_price = values.entry_zone_upper
        reference_reason = "ENTRY_REFERENCE_ZONE_UPPER"
    else:
        reference_price = bar.open
        reference_reason = "ENTRY_REFERENCE_BAR_OPEN"

    fill_price = costs.fill_price(reference_price, side=values.side)
    reference_notional = _quant_notional(values.requested_quantity, reference_price)
    notional = _quant_notional(values.requested_quantity, fill_price)
    return (
        ENTRY_FILLED,
        ENTER_ACTION,
        reference_price,
        fill_price,
        values.requested_quantity,
        notional,
        costs.fee(notional),
        abs(notional - reference_notional),
        resolved_at,
        True,
        (
            "ENTRY_ZONE_TOUCHED",
            reference_reason,
            "ENTRY_EXECUTION_COSTS_APPLIED",
            "ENTRY_EXECUTION_FILLED",
        ),
    )


def _validate_intent(intent: EntryExecutionIntent) -> EntryExecutionIntent:
    if not isinstance(intent, EntryExecutionIntent):
        raise TypeError("intent must be an EntryExecutionIntent")
    _string(intent.execution_id, "execution_id")
    _optional_positive_integer(intent.recommendation_id, "recommendation_id")
    _string(intent.symbol, "symbol")
    if intent.direction not in POSITION_SIDES:
        raise ValueError(f"direction must be one of {POSITION_SIDES}")
    decision_at = require_utc_datetime(intent.decision_at, "decision_at")
    if intent.timeframe not in SUPPORTED_TIMEFRAMES:
        raise ValueError(f"timeframe must be one of {SUPPORTED_TIMEFRAMES}")
    lower = _positive(intent.entry_zone_lower, "entry_zone_lower")
    upper = _positive(intent.entry_zone_upper, "entry_zone_upper")
    if lower > upper:
        raise ValueError("entry_zone_lower must be <= entry_zone_upper")
    available_at = require_utc_datetime(
        intent.entry_zone_available_at, "entry_zone_available_at"
    )
    if available_at > decision_at:
        raise ValueError("entry zone must be available by decision_at")
    _positive(intent.requested_quantity, "requested_quantity")
    _optional_string(intent.entry_zone_id, "entry_zone_id")
    _config_metadata(intent.config_metadata)
    return intent


def _validate_bar(bar: OhlcvBar, intent: EntryExecutionIntent) -> OhlcvBar:
    if not isinstance(bar, OhlcvBar):
        raise TypeError("execution_bar must be an OhlcvBar")
    timestamp = require_utc_datetime(bar.timestamp, "execution_bar.timestamp")
    if timestamp != intent.eligible_bar_at:
        raise ValueError("execution_bar must be the intent's first eligible full bar")
    if bar.symbol != intent.symbol:
        raise ValueError("execution_bar symbol must match intent symbol")
    if bar.timeframe != intent.timeframe:
        raise ValueError("execution_bar timeframe must match intent timeframe")
    if next_eligible_bar_timestamp(timestamp, bar.timeframe) != timestamp:
        raise ValueError("execution_bar timestamp must be on a canonical bar boundary")
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
        raise TypeError("costs must be ExecutionCosts")
    if costs.policy_version != EXECUTION_COST_POLICY_VERSION:
        raise ValueError(f"costs.policy_version must be {EXECUTION_COST_POLICY_VERSION}")
    _non_negative(costs.fee_bps, "costs.fee_bps")
    _non_negative(costs.slippage_bps, "costs.slippage_bps")
    _non_negative(costs.funding_cost_bps_per_day, "costs.funding_cost_bps_per_day")


def _quant_notional(quantity: Decimal, price: Decimal) -> Decimal:
    """Use the BTC-047 float64 kernel and retain a persistence-safe decimal."""

    return Decimal(str(position_notional(float(quantity), float(price))))


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
        raise TypeError(f"{name} must be a mapping")
    return dict(value)


def _config_metadata(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise TypeError("config_metadata must be a mapping")
    result = dict(value)
    if set(result) != set(_REQUIRED_CONFIG_METADATA_KEYS):
        raise ValueError(
            "config_metadata must exactly contain "
            f"{_REQUIRED_CONFIG_METADATA_KEYS}"
        )
    for key, item in result.items():
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"config_metadata.{key} must be a non-empty string")
    return result


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _optional_string(value: Any, name: str) -> str | None:
    return None if value is None else _string(value, name)


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
        result = Decimal(str(value))
    except Exception as error:  # noqa: BLE001 - normalized as a domain error
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
    if not isinstance(value, str):
        raise ValueError(f"{name} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an ISO-8601 datetime") from error
    return require_utc_datetime(parsed, name)


def _optional_decimal_string(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


__all__ = [
    "ENTER_ACTION",
    "ENTRY_EXECUTION_FEATURE_ID",
    "ENTRY_EXECUTION_POLICY_VERSION",
    "ENTRY_EXECUTION_REASON_CODES",
    "ENTRY_EXECUTION_STATUSES",
    "ENTRY_FILLED",
    "ENTRY_MISSED",
    "MARKET_ORDER",
    "MISSED_ACTION",
    "EntryExecutionIntent",
    "SimulatedEntryExecution",
    "next_eligible_bar_timestamp",
    "restore_simulated_entry_execution",
    "simulate_next_bar_entry",
]
