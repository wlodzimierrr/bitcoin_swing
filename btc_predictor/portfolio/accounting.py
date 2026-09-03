"""Replayable, point-in-time paper trade accounting (BTC-165).

``PAPER_TRADE_ACCOUNTING_V1`` uses actual fill prices and fees. For a closed
long, gross P&L is total sell proceeds less total buy cost; for a closed short,
it is total short-sale proceeds less total cover cost. Net P&L subtracts fees
and signed account funding cost. Positive funding is paid by the account and
negative funding is received.

One R is the initial filled quantity multiplied by the distance from the actual
initial fill to the authoritative entry stop. It is frozen at entry under
``INITIAL_PLANNED_RISK_V1``; later adds, trims, and stop moves do not rewrite
the denominator.

MFE and MAE are signed extrema of total gross trade P&L. Full OHLC bars that
contain an entry, add, trim, or exit are excluded because OHLC cannot establish
whether their extremes occurred before or after the fill. Exact non-entry fill
prices are retained as point observations, including a gap-stop exit.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from fractions import Fraction
from typing import Any

from btc_predictor.data import OhlcvBar, next_bar_timestamp, require_utc_datetime
from btc_predictor.quant.comparisons import decision_greater, decision_less


PAPER_TRADE_ACCOUNTING_FEATURE_ID = "PAPER_TRADE_ACCOUNTING"
PAPER_TRADE_ACCOUNTING_POLICY_VERSION = "PAPER_TRADE_ACCOUNTING_V1"
R_MULTIPLE_CONVENTION = "INITIAL_PLANNED_RISK_V1"
FUNDING_CONVENTION = "SIGNED_ACCOUNT_FUNDING_COST_V1"
EXCURSION_CONVENTION = "SIGNED_GROSS_PNL_FULL_BARS_AND_FILL_ENDPOINTS_V1"
MAXIMUM_SIZE_CONVENTION = "MAX_OPEN_ENTRY_COST_BASIS_V1"

LONG_DIRECTION = "long"
SHORT_DIRECTION = "short"
TRADE_DIRECTIONS = (LONG_DIRECTION, SHORT_DIRECTION)

ENTER_ACTION = "ENTER"
ADD_ACTION = "ADD"
TRIM_ACTION = "TRIM"
EXIT_ACTION = "EXIT"
OPENING_ACTIONS = (ENTER_ACTION, ADD_ACTION)
CLOSING_ACTIONS = (TRIM_ACTION, EXIT_ACTION)
TRADE_FILL_ACTIONS = OPENING_ACTIONS + CLOSING_ACTIONS

TRADE_ACCOUNTING_REASON_CODES = (
    "TRADE_ACCOUNTING_COMPLETE",
    "TRADE_ACCOUNTING_POSITION_STILL_OPEN",
    "TRADE_ACCOUNTING_NET_PROFIT",
    "TRADE_ACCOUNTING_NET_LOSS",
    "TRADE_ACCOUNTING_NET_FLAT",
    "TRADE_ACCOUNTING_R_UNDEFINED",
    "TRADE_ACCOUNTING_R_PENDING",
    "TRADE_ACCOUNTING_NO_EXCURSION_BARS",
    "TRADE_ACCOUNTING_COSTS_REVERSED_A_GROSS_PROFIT",
)

_REQUIRED_CONFIG_METADATA_KEYS = (
    "config_version",
    "strategy_version",
    "parameter_set_id",
)
_SECONDS_PER_DAY = Decimal("86400")


@dataclass(frozen=True)
class TradeFill:
    """One authoritative execution, in trade-ledger order.

    ``source_event_id`` identifies the originating execution record. The bar
    fields identify the OHLC interval containing the fill and are mandatory
    whenever excursion bars are supplied.
    """

    sequence: int
    filled_at: datetime
    action: str
    quantity: Decimal
    price: Decimal
    fee: Decimal = Decimal("0")
    source_event_id: str | None = None
    execution_bar_at: datetime | None = None
    execution_bar_timeframe: str | None = None

    @property
    def opening(self) -> bool:
        return self.action in OPENING_ACTIONS

    @property
    def notional(self) -> Decimal:
        return self.quantity * self.price

    def as_record(self) -> dict[str, Any]:
        _validate_trade_fill(self)
        return {
            "sequence": self.sequence,
            "source_event_id": self.source_event_id,
            "filled_at": require_utc_datetime(self.filled_at, "filled_at").isoformat(),
            "action": self.action,
            "quantity": str(self.quantity),
            "price": str(self.price),
            "fee": str(self.fee),
            "execution_bar_at": _optional_time(self.execution_bar_at),
            "execution_bar_timeframe": self.execution_bar_timeframe,
        }


@dataclass(frozen=True)
class FundingEvent:
    """A funding settlement with cost signed from the account perspective.

    Positive ``funding_cost`` is paid and reduces net P&L. Negative cost is
    received and increases it. ``position_quantity`` is checked against the
    fill ledger at the event's ordered timestamp.
    """

    sequence: int
    event_id: str
    effective_at: datetime
    rate: Decimal
    mark_price: Decimal
    position_quantity: Decimal
    funding_cost: Decimal

    def as_record(self) -> dict[str, Any]:
        _validate_funding_event(self)
        return {
            "sequence": self.sequence,
            "event_id": self.event_id,
            "effective_at": require_utc_datetime(
                self.effective_at, "funding.effective_at"
            ).isoformat(),
            "rate": str(self.rate),
            "mark_price": str(self.mark_price),
            "position_quantity": str(self.position_quantity),
            "funding_cost": str(self.funding_cost),
        }


@dataclass(frozen=True)
class _PositionState:
    """One point on the position walk.

    ``cost_basis`` and ``realized_gross`` are exact rationals, not Decimals.
    A pro-rata basis removal is ``cost_basis * closed / open``, which repeats
    for any open quantity that is not a terminating decimal -- and BTC-155
    produces those routinely, because it divides a notional by a price.
    Rounding that removal to the Decimal context leaves the amount taken out
    of the basis and the amount added to realized P&L disagreeing in the last
    place, so the telescoping identities this module is built on stop holding
    exactly. Keeping the walk rational makes the removal cancel exactly and
    only the final reported figure is converted.
    """

    filled_at: datetime
    sequence: int
    action: str
    fill_price: Decimal
    quantity: Decimal
    cost_basis: Fraction
    realized_gross: Fraction


@dataclass(frozen=True)
class PaperTradeAccounting:
    feature_id: str
    policy_version: str
    r_multiple_convention: str
    funding_convention: str
    excursion_convention: str
    maximum_size_convention: str
    evidence_digest: str
    symbol: str
    direction: str
    fills: tuple[TradeFill, ...]
    funding_events: tuple[FundingEvent, ...]
    excursion_bars: tuple[OhlcvBar, ...]
    opened_at: datetime
    closed_at: datetime | None
    as_of: datetime
    holding_days: Decimal
    initial_quantity: Decimal
    initial_entry_price: Decimal
    initial_stop_price: Decimal
    initial_stop_source_id: str
    initial_risk: Decimal
    average_entry_price: Decimal
    entry_notional: Decimal
    exit_notional: Decimal
    gross_pnl: Decimal
    fees: Decimal
    funding: Decimal
    net_pnl: Decimal
    r_multiple: Decimal | None
    maximum_favourable_excursion: Decimal | None
    maximum_adverse_excursion: Decimal | None
    mfe_r: Decimal | None
    mae_r: Decimal | None
    maximum_quantity: Decimal
    maximum_entry_notional: Decimal
    add_count: int
    trim_count: int
    exit_reason: str | None
    exit_reason_source_id: str | None
    closed: bool
    config_metadata: dict[str, str]
    reason_codes: tuple[str, ...]

    @property
    def maximum_notional(self) -> Decimal:
        """Compatibility alias for the explicitly named entry-cost measure."""

        return self.maximum_entry_notional

    def as_record(self) -> dict[str, Any]:
        expected = calculate_trade_accounting(
            self.fills,
            symbol=self.symbol,
            direction=self.direction,
            initial_stop_price=self.initial_stop_price,
            initial_stop_source_id=self.initial_stop_source_id,
            exit_reason=self.exit_reason,
            exit_reason_source_id=self.exit_reason_source_id,
            funding_events=self.funding_events,
            excursion_bars=self.excursion_bars,
            as_of=self.as_of,
            config_metadata=self.config_metadata,
        )
        if self != expected:
            raise ValueError("trade accounting fields do not match replayed evidence")
        return self._record()

    def _record(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "r_multiple_convention": self.r_multiple_convention,
            "funding_convention": self.funding_convention,
            "excursion_convention": self.excursion_convention,
            "maximum_size_convention": self.maximum_size_convention,
            "evidence_digest": self.evidence_digest,
            "symbol": self.symbol,
            "direction": self.direction,
            "fills": [fill.as_record() for fill in self.fills],
            "funding_events": [event.as_record() for event in self.funding_events],
            "excursion_bars": [_bar_record(bar) for bar in self.excursion_bars],
            "opened_at": self.opened_at.isoformat(),
            "closed_at": _optional_time(self.closed_at),
            "as_of": self.as_of.isoformat(),
            "holding_days": str(self.holding_days),
            "initial_quantity": str(self.initial_quantity),
            "initial_entry_price": str(self.initial_entry_price),
            "initial_stop_price": str(self.initial_stop_price),
            "initial_stop_source_id": self.initial_stop_source_id,
            "initial_risk": str(self.initial_risk),
            "average_entry_price": str(self.average_entry_price),
            "entry_notional": str(self.entry_notional),
            "exit_notional": str(self.exit_notional),
            "gross_pnl": str(self.gross_pnl),
            "fees": str(self.fees),
            "funding": str(self.funding),
            "net_pnl": str(self.net_pnl),
            "r_multiple": _optional_decimal(self.r_multiple),
            "maximum_favourable_excursion": _optional_decimal(
                self.maximum_favourable_excursion
            ),
            "maximum_adverse_excursion": _optional_decimal(
                self.maximum_adverse_excursion
            ),
            "mfe_r": _optional_decimal(self.mfe_r),
            "mae_r": _optional_decimal(self.mae_r),
            "maximum_quantity": str(self.maximum_quantity),
            "maximum_entry_notional": str(self.maximum_entry_notional),
            "add_count": self.add_count,
            "trim_count": self.trim_count,
            "exit_reason": self.exit_reason,
            "exit_reason_source_id": self.exit_reason_source_id,
            "closed": self.closed,
            "config_metadata": dict(self.config_metadata),
            "reason_codes": list(self.reason_codes),
        }

    def as_completed_trade_record(
        self, *, account_id: int, position_id: int
    ) -> dict[str, Any]:
        """Map every accounting output onto ``portfolio.completed_trades``."""

        accounting_record = self.as_record()
        if not self.closed or self.closed_at is None or self.exit_reason is None:
            raise ValueError("an open position is not a completed trade")
        for name, value in (("account_id", account_id), ("position_id", position_id)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        return {
            "position_id": position_id,
            "account_id": account_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "opened_at": self.opened_at,
            "closed_at": self.closed_at,
            "entry_notional": self.entry_notional,
            "exit_notional": self.exit_notional,
            "gross_pnl": self.gross_pnl,
            "fees": self.fees,
            "funding": self.funding,
            "realized_pnl": self.net_pnl,
            "initial_risk": self.initial_risk,
            "realized_r": self.r_multiple,
            "mfe": self.maximum_favourable_excursion,
            "mae": self.maximum_adverse_excursion,
            "mfe_r": self.mfe_r,
            "mae_r": self.mae_r,
            "holding_days": self.holding_days,
            "maximum_quantity": self.maximum_quantity,
            "maximum_entry_notional": self.maximum_entry_notional,
            "add_count": self.add_count,
            "trim_count": self.trim_count,
            "exit_reason": self.exit_reason,
            "initial_stop_source_id": self.initial_stop_source_id,
            "exit_reason_source_id": self.exit_reason_source_id,
            "accounting_evidence_digest": self.evidence_digest,
            "accounting_policy_version": self.policy_version,
            "r_multiple_convention": self.r_multiple_convention,
            "funding_convention": self.funding_convention,
            "excursion_convention": self.excursion_convention,
            "maximum_size_convention": self.maximum_size_convention,
            "config_version": self.config_metadata["config_version"],
            "accounting_record": accounting_record,
        }


def funding_event_from_rate(
    *,
    sequence: int,
    event_id: str,
    effective_at: datetime,
    rate: Any,
    mark_price: Any,
    position_quantity: Any,
    direction: str,
) -> FundingEvent:
    """Build signed account funding cost from one market funding rate."""

    if direction not in TRADE_DIRECTIONS:
        raise ValueError(f"direction must be one of {TRADE_DIRECTIONS}")
    normalized_rate = _decimal(rate, "rate")
    price = _positive(mark_price, "mark_price")
    quantity = _positive(position_quantity, "position_quantity")
    unsigned = quantity * price * normalized_rate
    event = FundingEvent(
        sequence=_sequence(sequence, "funding.sequence"),
        event_id=_identifier(event_id, "funding.event_id"),
        effective_at=require_utc_datetime(effective_at, "funding.effective_at"),
        rate=normalized_rate,
        mark_price=price,
        position_quantity=quantity,
        funding_cost=unsigned if direction == LONG_DIRECTION else -unsigned,
    )
    _validate_funding_event(event)
    return event


def calculate_trade_accounting(
    fills: Iterable[TradeFill],
    *,
    symbol: str,
    direction: str,
    initial_stop_price: Any,
    exit_reason: str | None,
    initial_stop_source_id: str | None = None,
    exit_reason_source_id: str | None = None,
    funding_events: Iterable[FundingEvent] = (),
    funding: Any | None = None,
    excursion_bars: Sequence[OhlcvBar] | None = None,
    as_of: datetime | None = None,
    config_metadata: Mapping[str, str] | None = None,
) -> PaperTradeAccounting:
    """Account for one paper trade from replayable execution evidence."""

    if direction not in TRADE_DIRECTIONS:
        raise ValueError(f"direction must be one of {TRADE_DIRECTIONS}")
    normalized_symbol = _identifier(symbol, "symbol")
    stop_source = _identifier(initial_stop_source_id, "initial_stop_source_id")
    metadata = _config_metadata(config_metadata)
    ordered = _validate_fills(fills)
    stop_price = _positive(initial_stop_price, "initial_stop_price")
    if funding is not None and _decimal(funding, "funding") != 0:
        raise ValueError("aggregate funding is not replayable; use funding_events")

    opening = ordered[0]
    if direction == LONG_DIRECTION and stop_price > opening.price:
        raise ValueError("a long initial stop must not exceed the entry fill")
    if direction == SHORT_DIRECTION and stop_price < opening.price:
        raise ValueError("a short initial stop must not be below the entry fill")

    long_position = direction == LONG_DIRECTION
    quantity = Decimal("0")
    cost_basis = Fraction(0)
    opened_quantity = Decimal("0")
    realized = Fraction(0)
    fees = Decimal("0")
    entry_notional = Fraction(0)
    exit_notional = Fraction(0)
    maximum_quantity = Decimal("0")
    maximum_entry_notional = Fraction(0)
    add_count = 0
    trim_count = 0
    timeline: list[_PositionState] = []

    for index, fill in enumerate(ordered):
        fees += fill.fee
        fill_notional = Fraction(fill.notional)
        if fill.opening:
            if quantity == 0 and fill.action != ENTER_ACTION:
                raise ValueError("ADD requires an open position")
            quantity += fill.quantity
            opened_quantity += fill.quantity
            cost_basis += fill_notional
            entry_notional += fill_notional
            if fill.action == ADD_ACTION:
                add_count += 1
            maximum_quantity = max(maximum_quantity, quantity)
            maximum_entry_notional = max(maximum_entry_notional, cost_basis)
        else:
            if quantity == 0:
                raise ValueError("a close requires an open position")
            if fill.quantity > quantity:
                raise ValueError("a close cannot exceed the open quantity")
            if fill.action == TRIM_ACTION and fill.quantity == quantity:
                raise ValueError("TRIM must leave a positive open quantity")
            if fill.action == EXIT_ACTION:
                if fill.quantity != quantity:
                    raise ValueError("EXIT must close the full open quantity")
                if index != len(ordered) - 1:
                    raise ValueError("EXIT must be the final fill")
            removed = (
                cost_basis
                if fill.quantity == quantity
                else cost_basis * Fraction(fill.quantity) / Fraction(quantity)
            )
            realized += (
                fill_notional - removed if long_position else removed - fill_notional
            )
            exit_notional += fill_notional
            cost_basis -= removed
            quantity -= fill.quantity
            if fill.action == TRIM_ACTION:
                trim_count += 1
        timeline.append(
            _PositionState(
                filled_at=fill.filled_at,
                sequence=fill.sequence,
                action=fill.action,
                fill_price=fill.price,
                quantity=quantity,
                cost_basis=cost_basis,
                realized_gross=realized,
            )
        )

    closed = quantity == 0
    if closed != (ordered[-1].action == EXIT_ACTION):
        raise ValueError("a closed trade requires one final EXIT fill")
    opened_at = ordered[0].filled_at
    if closed:
        normalized_exit_reason = _identifier(exit_reason, "exit_reason")
        exit_source = _identifier(exit_reason_source_id, "exit_reason_source_id")
        closed_at: datetime | None = ordered[-1].filled_at
        accounting_as_of = (
            closed_at if as_of is None else require_utc_datetime(as_of, "as_of")
        )
        if accounting_as_of < closed_at:
            raise ValueError("as_of must not precede the closing fill")
        holding_end = closed_at
    else:
        if exit_reason is not None or exit_reason_source_id is not None:
            raise ValueError("an open trade cannot have an exit reason")
        if as_of is None:
            raise ValueError("as_of is required for an open trade")
        accounting_as_of = require_utc_datetime(as_of, "as_of")
        if accounting_as_of < ordered[-1].filled_at:
            raise ValueError("as_of must not precede the latest fill")
        normalized_exit_reason = None
        exit_source = None
        closed_at = None
        holding_end = accounting_as_of

    events = _validate_funding_events(
        funding_events,
        fills=ordered,
        timeline=timeline,
        direction=direction,
        opened_at=opened_at,
        terminal_at=holding_end,
        closed=closed,
    )
    funding_total = sum((event.funding_cost for event in events), Decimal("0"))
    initial_risk = opening.quantity * abs(opening.price - stop_price)

    if closed:
        # The walk is rational, so this holds exactly for every trade shape,
        # including a pyramided position that was trimmed before it closed.
        expected_gross = (
            exit_notional - entry_notional
            if long_position
            else entry_notional - exit_notional
        )
        if realized != expected_gross:
            raise ValueError("closed trade does not satisfy the exact cash-flow identity")

    entry_notional_value = _from_fraction(entry_notional)
    exit_notional_value = _from_fraction(exit_notional)
    maximum_entry_notional_value = _from_fraction(maximum_entry_notional)
    gross_pnl = _from_fraction(realized)
    net_pnl = gross_pnl - fees - funding_total
    r_multiple = None if not closed or initial_risk == 0 else net_pnl / initial_risk
    bars = tuple(excursion_bars or ())
    favourable, adverse = _excursions(
        bars,
        fills=ordered,
        timeline=timeline,
        long_position=long_position,
        symbol=normalized_symbol,
        opened_at=opened_at,
        terminal_at=holding_end,
        accounting_as_of=accounting_as_of,
    )
    evidence_digest = _evidence_digest(
        fills=ordered,
        funding_events=events,
        excursion_bars=bars,
        symbol=normalized_symbol,
        direction=direction,
        initial_stop_price=stop_price,
        initial_stop_source_id=stop_source,
        exit_reason=normalized_exit_reason,
        exit_reason_source_id=exit_source,
        as_of=accounting_as_of,
        config_metadata=metadata,
    )

    reasons = [
        "TRADE_ACCOUNTING_COMPLETE"
        if closed
        else "TRADE_ACCOUNTING_POSITION_STILL_OPEN"
    ]
    comparison = 0
    if decision_greater(net_pnl, 0):
        comparison = 1
        reasons.append("TRADE_ACCOUNTING_NET_PROFIT")
    elif decision_less(net_pnl, 0):
        comparison = -1
        reasons.append("TRADE_ACCOUNTING_NET_LOSS")
    else:
        reasons.append("TRADE_ACCOUNTING_NET_FLAT")
    if decision_greater(gross_pnl, 0) and comparison < 0:
        reasons.append("TRADE_ACCOUNTING_COSTS_REVERSED_A_GROSS_PROFIT")
    if not closed:
        reasons.append("TRADE_ACCOUNTING_R_PENDING")
    elif r_multiple is None:
        reasons.append("TRADE_ACCOUNTING_R_UNDEFINED")
    if favourable is None:
        reasons.append("TRADE_ACCOUNTING_NO_EXCURSION_BARS")

    return PaperTradeAccounting(
        feature_id=PAPER_TRADE_ACCOUNTING_FEATURE_ID,
        policy_version=PAPER_TRADE_ACCOUNTING_POLICY_VERSION,
        r_multiple_convention=R_MULTIPLE_CONVENTION,
        funding_convention=FUNDING_CONVENTION,
        excursion_convention=EXCURSION_CONVENTION,
        maximum_size_convention=MAXIMUM_SIZE_CONVENTION,
        evidence_digest=evidence_digest,
        symbol=normalized_symbol,
        direction=direction,
        fills=ordered,
        funding_events=events,
        excursion_bars=bars,
        opened_at=opened_at,
        closed_at=closed_at,
        as_of=accounting_as_of,
        holding_days=_days_between(opened_at, holding_end),
        initial_quantity=opening.quantity,
        initial_entry_price=opening.price,
        initial_stop_price=stop_price,
        initial_stop_source_id=stop_source,
        initial_risk=initial_risk,
        average_entry_price=entry_notional_value / opened_quantity,
        entry_notional=entry_notional_value,
        exit_notional=exit_notional_value,
        gross_pnl=gross_pnl,
        fees=fees,
        funding=funding_total,
        net_pnl=net_pnl,
        r_multiple=r_multiple,
        maximum_favourable_excursion=favourable,
        maximum_adverse_excursion=adverse,
        mfe_r=(
            None
            if favourable is None or initial_risk == 0
            else favourable / initial_risk
        ),
        mae_r=(
            None if adverse is None or initial_risk == 0 else adverse / initial_risk
        ),
        maximum_quantity=maximum_quantity,
        maximum_entry_notional=maximum_entry_notional_value,
        add_count=add_count,
        trim_count=trim_count,
        exit_reason=normalized_exit_reason,
        exit_reason_source_id=exit_source,
        closed=closed,
        config_metadata=metadata,
        reason_codes=tuple(reasons),
    )


def trade_fill_from_execution(execution: Any, *, sequence: int) -> TradeFill:
    """Create a fill from a replay-validated BTC-161 through BTC-164 result."""

    validator = getattr(execution, "as_record", None)
    if not callable(validator):
        raise TypeError("execution must expose as_record()")
    validator()
    if getattr(execution, "filled", False) is not True:
        raise ValueError("execution must be filled")
    intent = getattr(execution, "intent", None)
    bar = getattr(execution, "execution_bar", None)
    if not isinstance(bar, OhlcvBar):
        raise TypeError("execution.execution_bar must be an OhlcvBar")
    return TradeFill(
        sequence=_sequence(sequence, "sequence"),
        filled_at=require_utc_datetime(execution.resolved_at, "execution.resolved_at"),
        action=_identifier(execution.action, "execution.action"),
        quantity=_positive(execution.filled_quantity, "execution.filled_quantity"),
        price=_positive(execution.average_fill_price, "execution.average_fill_price"),
        fee=_non_negative(execution.fee, "execution.fee"),
        source_event_id=_identifier(
            getattr(intent, "execution_id", None), "execution.intent.execution_id"
        ),
        execution_bar_at=require_utc_datetime(
            bar.timestamp, "execution.execution_bar.timestamp"
        ),
        execution_bar_timeframe=_identifier(
            bar.timeframe, "execution.execution_bar.timeframe"
        ),
    )


def calculate_trade_accounting_for_lifecycle(
    lifecycle: Any,
    fills: Iterable[TradeFill],
    *,
    funding_events: Iterable[FundingEvent] = (),
    excursion_bars: Sequence[OhlcvBar] | None = None,
    as_of: datetime | None = None,
    initial_stop_source_id: str | None = None,
    exit_reason: str | None = None,
    exit_reason_source_id: str | None = None,
) -> PaperTradeAccounting:
    """Account from BTC-150, deriving and reconciling stop/exit provenance."""

    from btc_predictor.portfolio.state_machine import (  # local: avoid cycle
        ADD,
        ENTER,
        EXIT,
        TRIM,
        PositionLifecycle,
    )

    if not isinstance(lifecycle, PositionLifecycle):
        raise TypeError("lifecycle must be a PositionLifecycle")
    lifecycle.as_record()
    relevant = tuple(
        transition
        for transition in lifecycle.transitions
        if transition.accepted and transition.event in (ENTER, ADD, TRIM, EXIT)
    )
    ordered = _validate_fills(fills)
    if len(relevant) != len(ordered):
        raise ValueError("fills must reconcile one-for-one with lifecycle transitions")
    for transition, fill in zip(relevant, ordered):
        quantity = (
            abs(transition.quantity_delta)
            if transition.event == EXIT and transition.quantity_delta is not None
            else transition.requested_quantity
        )
        if (
            transition.event != fill.action
            or transition.event_time != fill.filled_at
            or transition.source_record_id != fill.source_event_id
            or quantity != fill.quantity
            or transition.price != fill.price
        ):
            raise ValueError("fill does not match its authoritative lifecycle transition")
    if not relevant or relevant[0].event != ENTER:
        raise ValueError("lifecycle has no authoritative ENTER transition")
    enter = relevant[0]
    if enter.stop_price is None or enter.source_record_id is None:
        raise ValueError("ENTER transition must identify its authoritative execution source")
    stop_source = (
        _identifier(initial_stop_source_id, "initial_stop_source_id")
        if initial_stop_source_id is not None
        else enter.source_record_id
    )

    closed = relevant[-1].event == EXIT
    if closed:
        terminal = relevant[-1]
        external_reasons = tuple(
            code
            for code in terminal.reason_codes
            if not code.startswith("POSITION_STATE_")
        )
        if terminal.source_record_id is None or not external_reasons:
            raise ValueError("EXIT transition must identify an authoritative exit signal")
        derived_exit_reason: str | None = "|".join(external_reasons)
        derived_exit_source: str | None = terminal.source_record_id
        accounting_exit_reason = (
            _identifier(exit_reason, "exit_reason")
            if exit_reason is not None
            else derived_exit_reason
        )
        accounting_exit_source = (
            _identifier(exit_reason_source_id, "exit_reason_source_id")
            if exit_reason_source_id is not None
            else derived_exit_source
        )
    else:
        if exit_reason is not None or exit_reason_source_id is not None:
            raise ValueError("an open lifecycle cannot have exit provenance")
        accounting_exit_reason = None
        accounting_exit_source = None

    return calculate_trade_accounting(
        ordered,
        symbol=lifecycle.symbol,
        direction=lifecycle.direction,
        initial_stop_price=enter.stop_price,
        initial_stop_source_id=stop_source,
        exit_reason=accounting_exit_reason,
        exit_reason_source_id=accounting_exit_source,
        funding_events=funding_events,
        excursion_bars=excursion_bars,
        as_of=as_of,
        config_metadata=lifecycle.config_metadata,
    )


def restore_trade_accounting(record: Mapping[str, Any]) -> PaperTradeAccounting:
    """Restore a record by replaying all persisted evidence field-for-field."""

    source = _mapping(record, "record")
    if source.get("feature_id") != PAPER_TRADE_ACCOUNTING_FEATURE_ID:
        raise ValueError(f"feature_id must be {PAPER_TRADE_ACCOUNTING_FEATURE_ID}")
    if source.get("policy_version") != PAPER_TRADE_ACCOUNTING_POLICY_VERSION:
        raise ValueError(f"policy_version must be {PAPER_TRADE_ACCOUNTING_POLICY_VERSION}")
    fills = tuple(
        _fill_from_record(_mapping(value, "fill"))
        for value in _sequence_values(source.get("fills"), "fills")
    )
    events = tuple(
        _funding_from_record(_mapping(value, "funding_event"))
        for value in _sequence_values(source.get("funding_events"), "funding_events")
    )
    bars = tuple(
        _bar_from_record(_mapping(value, "excursion_bar"))
        for value in _sequence_values(source.get("excursion_bars"), "excursion_bars")
    )
    result = calculate_trade_accounting(
        fills,
        symbol=source.get("symbol"),
        direction=source.get("direction"),
        initial_stop_price=source.get("initial_stop_price"),
        initial_stop_source_id=source.get("initial_stop_source_id"),
        exit_reason=source.get("exit_reason"),
        exit_reason_source_id=source.get("exit_reason_source_id"),
        funding_events=events,
        excursion_bars=bars,
        as_of=_utc(source.get("as_of"), "as_of"),
        config_metadata=_mapping(source.get("config_metadata"), "config_metadata"),
    )
    if result._record() != source:
        raise ValueError("trade accounting record does not match replayed evidence")
    return result


def _excursions(
    bars: tuple[OhlcvBar, ...],
    *,
    fills: tuple[TradeFill, ...],
    timeline: list[_PositionState],
    long_position: bool,
    symbol: str,
    opened_at: datetime,
    terminal_at: datetime,
    accounting_as_of: datetime,
) -> tuple[Decimal | None, Decimal | None]:
    """Return signed MFE and MAE, converted from the exact rational walk."""

    if not bars:
        return None, None
    execution_bars: set[tuple[datetime, str]] = set()
    for fill in fills:
        if fill.execution_bar_at is None or fill.execution_bar_timeframe is None:
            raise ValueError(
                "every fill needs execution-bar provenance when excursions are calculated"
            )
        execution_bars.add((fill.execution_bar_at, fill.execution_bar_timeframe))

    observations: list[tuple[Fraction, Fraction]] = []
    previous_timestamp: datetime | None = None
    seen: set[tuple[Any, ...]] = set()
    for bar in bars:
        identity, timestamp, end_at = _validate_excursion_bar(bar, symbol=symbol)
        if identity in seen:
            raise ValueError("excursion bars must not contain duplicates")
        seen.add(identity)
        if previous_timestamp is not None and timestamp <= previous_timestamp:
            raise ValueError("excursion bars must be in strictly increasing time order")
        previous_timestamp = timestamp
        if (
            timestamp < opened_at
            or end_at > terminal_at
            or end_at > accounting_as_of
            or bar.ingested_at > accounting_as_of
            or (timestamp, bar.timeframe) in execution_bars
        ):
            continue
        state = _position_at(timeline, timestamp)
        if state.quantity == 0:
            continue
        best_price = bar.high if long_position else bar.low
        worst_price = bar.low if long_position else bar.high
        observations.append(
            (
                state.realized_gross
                + _unrealized(
                    state.quantity, best_price, state.cost_basis, long_position
                ),
                state.realized_gross
                + _unrealized(
                    state.quantity, worst_price, state.cost_basis, long_position
                ),
            )
        )

    # Entry's zero-P&L instant is excluded, allowing positive signed MAE. Every
    # later fill contributes its exact point value, including a gap-stop exit.
    for state in timeline[1:]:
        if state.filled_at > terminal_at or state.filled_at > accounting_as_of:
            continue
        value = state.realized_gross + _unrealized(
            state.quantity, state.fill_price, state.cost_basis, long_position
        )
        observations.append((value, value))
    if not observations:
        return None, None
    return (
        _from_fraction(max(best for best, _ in observations)),
        _from_fraction(min(worst for _, worst in observations)),
    )


def _validate_excursion_bar(
    bar: OhlcvBar, *, symbol: str
) -> tuple[tuple[Any, ...], datetime, datetime]:
    if not isinstance(bar, OhlcvBar):
        raise TypeError("excursion_bars must contain OhlcvBar instances")
    timestamp = require_utc_datetime(bar.timestamp, "excursion_bar.timestamp")
    ingested = require_utc_datetime(bar.ingested_at, "excursion_bar.ingested_at")
    if bar.symbol != symbol:
        raise ValueError("excursion bar symbol must match the trade symbol")
    for name in ("exchange", "provider", "timeframe"):
        _identifier(getattr(bar, name), f"excursion_bar.{name}")
    open_price = _positive(bar.open, "excursion_bar.open")
    high = _positive(bar.high, "excursion_bar.high")
    low = _positive(bar.low, "excursion_bar.low")
    close = _positive(bar.close, "excursion_bar.close")
    _non_negative(bar.volume, "excursion_bar.volume")
    if low > min(open_price, close) or high < max(open_price, close) or low > high:
        raise ValueError("excursion bar has impossible OHLC geometry")
    end_at = next_bar_timestamp(timestamp, bar.timeframe)
    if ingested < timestamp:
        raise ValueError("excursion bar cannot be ingested before its timestamp")
    identity = (bar.exchange, bar.symbol, bar.timeframe, timestamp, bar.provider)
    return identity, timestamp, end_at


def _unrealized(
    quantity: Decimal, price: Decimal, basis: Fraction, long_position: bool
) -> Fraction:
    marked = Fraction(quantity) * Fraction(price)
    return marked - basis if long_position else basis - marked


def _empty_state(at: datetime) -> _PositionState:
    return _PositionState(
        filled_at=at,
        sequence=0,
        action=ENTER_ACTION,
        fill_price=Decimal("0"),
        quantity=Decimal("0"),
        cost_basis=Fraction(0),
        realized_gross=Fraction(0),
    )


def _position_at(timeline: list[_PositionState], timestamp: datetime) -> _PositionState:
    state = _empty_state(timestamp)
    for candidate in timeline:
        if candidate.filled_at > timestamp:
            break
        state = candidate
    return state


def _validate_fills(fills: Iterable[TradeFill]) -> tuple[TradeFill, ...]:
    ordered = tuple(fills)
    if not ordered:
        raise ValueError("a trade requires at least one fill")
    for fill in ordered:
        if not isinstance(fill, TradeFill):
            raise TypeError("fills must be TradeFill instances")
        _validate_trade_fill(fill)
    if ordered[0].action != ENTER_ACTION:
        raise ValueError("the first fill must be an ENTER")
    if any(fill.action == ENTER_ACTION for fill in ordered[1:]):
        raise ValueError("a trade has exactly one ENTER")
    event_ids = [fill.source_event_id for fill in ordered]
    if len(set(event_ids)) != len(event_ids):
        raise ValueError("fill source_event_id values must be unique")
    for previous, current in zip(ordered, ordered[1:]):
        if current.filled_at < previous.filled_at:
            raise ValueError("fills must be in non-decreasing time order")
        if current.sequence <= previous.sequence:
            raise ValueError("fill sequences must strictly increase")
    return ordered


def _validate_trade_fill(fill: TradeFill) -> None:
    _sequence(fill.sequence, "fill.sequence")
    if fill.action not in TRADE_FILL_ACTIONS:
        raise ValueError(f"action must be one of {TRADE_FILL_ACTIONS}")
    _positive(fill.quantity, "fill.quantity")
    _positive(fill.price, "fill.price")
    _non_negative(fill.fee, "fill.fee")
    _identifier(fill.source_event_id, "fill.source_event_id")
    require_utc_datetime(fill.filled_at, "fill.filled_at")
    if (fill.execution_bar_at is None) != (fill.execution_bar_timeframe is None):
        raise ValueError("execution bar timestamp and timeframe must be supplied together")
    if fill.execution_bar_at is not None:
        execution_at = require_utc_datetime(
            fill.execution_bar_at, "fill.execution_bar_at"
        )
        timeframe = _identifier(
            fill.execution_bar_timeframe, "fill.execution_bar_timeframe"
        )
        if execution_at > fill.filled_at:
            raise ValueError("execution bar cannot start after the fill is resolved")
        next_bar_timestamp(execution_at, timeframe)


def _validate_funding_events(
    events: Iterable[FundingEvent],
    *,
    fills: tuple[TradeFill, ...],
    timeline: list[_PositionState],
    direction: str,
    opened_at: datetime,
    terminal_at: datetime,
    closed: bool,
) -> tuple[FundingEvent, ...]:
    ordered = tuple(events)
    fill_event_ids = {fill.source_event_id for fill in fills}
    fill_order_keys = {(fill.filled_at, fill.sequence) for fill in fills}
    seen_ids: set[str] = set()
    seen_order_keys: set[tuple[datetime, int]] = set()
    for event in ordered:
        if not isinstance(event, FundingEvent):
            raise TypeError("funding_events must contain FundingEvent instances")
        _validate_funding_event(event)
        if event.event_id in seen_ids:
            raise ValueError("funding event IDs must be unique")
        if event.event_id in fill_event_ids:
            raise ValueError("funding and fill event IDs must be unique")
        seen_ids.add(event.event_id)
        order_key = (event.effective_at, event.sequence)
        if order_key in seen_order_keys or order_key in fill_order_keys:
            raise ValueError("same-time ledger event sequences must be unique")
        seen_order_keys.add(order_key)
    sorted_events = tuple(
        sorted(ordered, key=lambda item: (item.effective_at, item.sequence))
    )
    if sorted_events != ordered:
        raise ValueError("funding events must be in deterministic time/sequence order")
    for event in ordered:
        if event.effective_at <= opened_at or (
            event.effective_at >= terminal_at
            if closed
            else event.effective_at > terminal_at
        ):
            raise ValueError("funding event must fall inside the open holding interval")
        state = _position_before_event(timeline, event)
        if event.position_quantity != state.quantity:
            raise ValueError("funding event position quantity does not match the ledger")
        expected = event.position_quantity * event.mark_price * event.rate
        if direction == SHORT_DIRECTION:
            expected = -expected
        if event.funding_cost != expected:
            raise ValueError(
                "funding cost does not match rate, mark, quantity, and direction"
            )
    return ordered


def _position_before_event(
    timeline: list[_PositionState], event: FundingEvent
) -> _PositionState:
    state = _empty_state(event.effective_at)
    key = (event.effective_at, event.sequence)
    for candidate in timeline:
        if (candidate.filled_at, candidate.sequence) >= key:
            break
        state = candidate
    return state


def _validate_funding_event(event: FundingEvent) -> None:
    _sequence(event.sequence, "funding.sequence")
    _identifier(event.event_id, "funding.event_id")
    require_utc_datetime(event.effective_at, "funding.effective_at")
    _decimal(event.rate, "funding.rate")
    _positive(event.mark_price, "funding.mark_price")
    _positive(event.position_quantity, "funding.position_quantity")
    _decimal(event.funding_cost, "funding.funding_cost")


def _fill_from_record(source: Mapping[str, Any]) -> TradeFill:
    return TradeFill(
        sequence=_sequence(source.get("sequence"), "fill.sequence"),
        filled_at=_utc(source.get("filled_at"), "fill.filled_at"),
        action=_identifier(source.get("action"), "fill.action"),
        quantity=_positive(source.get("quantity"), "fill.quantity"),
        price=_positive(source.get("price"), "fill.price"),
        fee=_non_negative(source.get("fee"), "fill.fee"),
        source_event_id=_identifier(
            source.get("source_event_id"), "fill.source_event_id"
        ),
        execution_bar_at=_optional_utc(
            source.get("execution_bar_at"), "fill.execution_bar_at"
        ),
        execution_bar_timeframe=_optional_identifier(
            source.get("execution_bar_timeframe"), "fill.execution_bar_timeframe"
        ),
    )


def _funding_from_record(source: Mapping[str, Any]) -> FundingEvent:
    return FundingEvent(
        sequence=_sequence(source.get("sequence"), "funding.sequence"),
        event_id=_identifier(source.get("event_id"), "funding.event_id"),
        effective_at=_utc(source.get("effective_at"), "funding.effective_at"),
        rate=_decimal(source.get("rate"), "funding.rate"),
        mark_price=_positive(source.get("mark_price"), "funding.mark_price"),
        position_quantity=_positive(
            source.get("position_quantity"), "funding.position_quantity"
        ),
        funding_cost=_decimal(source.get("funding_cost"), "funding.funding_cost"),
    )


def _bar_record(bar: OhlcvBar) -> dict[str, Any]:
    _validate_excursion_bar(bar, symbol=bar.symbol)
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


def _bar_from_record(source: Mapping[str, Any]) -> OhlcvBar:
    return OhlcvBar(
        timestamp=_utc(source.get("timestamp"), "excursion_bar.timestamp"),
        exchange=_identifier(source.get("exchange"), "excursion_bar.exchange"),
        symbol=_identifier(source.get("symbol"), "excursion_bar.symbol"),
        timeframe=_identifier(source.get("timeframe"), "excursion_bar.timeframe"),
        open=_positive(source.get("open"), "excursion_bar.open"),
        high=_positive(source.get("high"), "excursion_bar.high"),
        low=_positive(source.get("low"), "excursion_bar.low"),
        close=_positive(source.get("close"), "excursion_bar.close"),
        volume=_non_negative(source.get("volume"), "excursion_bar.volume"),
        provider=_identifier(source.get("provider"), "excursion_bar.provider"),
        ingested_at=_utc(source.get("ingested_at"), "excursion_bar.ingested_at"),
    )


def _days_between(opened_at: datetime, ended_at: datetime) -> Decimal:
    delta: timedelta = ended_at - opened_at
    return Decimal(str(delta.total_seconds())) / _SECONDS_PER_DAY


def _evidence_digest(
    *,
    fills: tuple[TradeFill, ...],
    funding_events: tuple[FundingEvent, ...],
    excursion_bars: tuple[OhlcvBar, ...],
    symbol: str,
    direction: str,
    initial_stop_price: Decimal,
    initial_stop_source_id: str,
    exit_reason: str | None,
    exit_reason_source_id: str | None,
    as_of: datetime,
    config_metadata: Mapping[str, str],
) -> str:
    evidence = {
        "fills": [fill.as_record() for fill in fills],
        "funding_events": [event.as_record() for event in funding_events],
        "excursion_bars": [_bar_record(bar) for bar in excursion_bars],
        "symbol": symbol,
        "direction": direction,
        "initial_stop_price": str(initial_stop_price),
        "initial_stop_source_id": initial_stop_source_id,
        "exit_reason": exit_reason,
        "exit_reason_source_id": exit_reason_source_id,
        "as_of": as_of.isoformat(),
        "config_metadata": dict(config_metadata),
    }
    payload = json.dumps(evidence, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _config_metadata(value: Mapping[str, str] | None) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError("config_metadata must be a mapping with full strategy identity")
    metadata = dict(value)
    for key in _REQUIRED_CONFIG_METADATA_KEYS:
        if key not in metadata:
            raise ValueError(f"config_metadata must include {key}")
    for key, item in metadata.items():
        _identifier(key, "config_metadata key")
        _identifier(item, f"config_metadata[{key!r}]")
    return metadata


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    return dict(value)


def _sequence_values(value: Any, name: str) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{name} must be a sequence")
    return tuple(value)


def _sequence(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    if value != value.strip():
        raise ValueError(f"{name} must not contain surrounding whitespace")
    return value


def _optional_identifier(value: Any, name: str) -> str | None:
    return None if value is None else _identifier(value, name)


def _from_fraction(value: Fraction) -> Decimal:
    """Return the exact Decimal of a terminating rational, else round it.

    Every figure this module reports from the position walk is a sum or
    difference of fill notionals, so the exact branch is the one the cash-flow
    and excursion identities depend on. Only a pro-rata basis removal on a
    still-open trade can repeat, and that is rounded by the same context
    division the walk used before this became rational.
    """

    remaining = value.denominator
    twos = 0
    while remaining % 2 == 0:
        remaining //= 2
        twos += 1
    fives = 0
    while remaining % 5 == 0:
        remaining //= 5
        fives += 1
    if remaining != 1:
        return Decimal(value.numerator) / Decimal(value.denominator)
    exponent = max(twos, fives)
    scaled = value.numerator * (10**exponent // value.denominator)
    return Decimal(f"{scaled}E-{exponent}")


def _decimal(value: Any, name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except Exception as error:  # noqa: BLE001 - normalize as a domain error
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
        raise ValueError(f"{name} must be an ISO-8601 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an ISO-8601 UTC timestamp") from error
    return require_utc_datetime(parsed, name)


def _optional_utc(value: Any, name: str) -> datetime | None:
    return None if value is None else _utc(value, name)


def _optional_decimal(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _optional_time(value: datetime | None) -> str | None:
    return (
        None
        if value is None
        else require_utc_datetime(value, "timestamp").isoformat()
    )


__all__ = [
    "ADD_ACTION",
    "CLOSING_ACTIONS",
    "ENTER_ACTION",
    "EXCURSION_CONVENTION",
    "EXIT_ACTION",
    "FUNDING_CONVENTION",
    "FundingEvent",
    "LONG_DIRECTION",
    "MAXIMUM_SIZE_CONVENTION",
    "OPENING_ACTIONS",
    "PAPER_TRADE_ACCOUNTING_FEATURE_ID",
    "PAPER_TRADE_ACCOUNTING_POLICY_VERSION",
    "PaperTradeAccounting",
    "R_MULTIPLE_CONVENTION",
    "SHORT_DIRECTION",
    "TRADE_ACCOUNTING_REASON_CODES",
    "TRADE_DIRECTIONS",
    "TRADE_FILL_ACTIONS",
    "TRIM_ACTION",
    "TradeFill",
    "calculate_trade_accounting",
    "calculate_trade_accounting_for_lifecycle",
    "funding_event_from_rate",
    "restore_trade_accounting",
    "trade_fill_from_execution",
]
