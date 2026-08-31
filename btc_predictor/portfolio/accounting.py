"""Closed paper trade accounting (BTC-165).

One walk over a trade's fills produces every figure the ticket asks for, so no
two of them can disagree. The fills are the same ones BTC-161 through BTC-164
emit, and the excursion bars are the same OHLCV those executions resolved
against.

Three conventions are stated rather than assumed, because each has a plausible
alternative that would silently change every reported number.

**1R is the risk planned at entry.** ``initial_quantity * |entry - initial
stop|``, fixed once. Measuring against the trailed stop would inflate R as the
stop ratchets, so a trade could report 3R having never risked more than it made.
Adds increase P&L without retroactively changing the denominator, which is why
the convention is versioned as ``INITIAL_PLANNED_RISK_V1``.

**MFE and MAE are signed peaks of total trade P&L**, not unsigned distances from
entry. They include P&L already realized by trims and exclude fees, matching
gross P&L. Reporting them as magnitudes hides the case where a trade gapped
favourably and never came back, whose "adverse excursion" is a profit.

**Average entry is invariant under a partial close.** Trimming reduces quantity
pro rata and leaves the weighted average alone, matching the BTC-150 ledger, so
a trim cannot re-base the price the remaining position is measured against.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from btc_predictor.data import OhlcvBar, require_utc_datetime


PAPER_TRADE_ACCOUNTING_FEATURE_ID = "PAPER_TRADE_ACCOUNTING"
PAPER_TRADE_ACCOUNTING_POLICY_VERSION = "PAPER_TRADE_ACCOUNTING_V1"
R_MULTIPLE_CONVENTION = "INITIAL_PLANNED_RISK_V1"

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
    "TRADE_ACCOUNTING_NO_EXCURSION_BARS",
    "TRADE_ACCOUNTING_COSTS_REVERSED_A_GROSS_PROFIT",
)

_SECONDS_PER_DAY = Decimal("86400")


@dataclass(frozen=True)
class TradeFill:
    """One execution against a trade, in ledger order."""

    sequence: int
    filled_at: datetime
    action: str
    quantity: Decimal
    price: Decimal
    fee: Decimal = Decimal("0")

    @property
    def opening(self) -> bool:
        return self.action in OPENING_ACTIONS

    @property
    def notional(self) -> Decimal:
        return self.quantity * self.price

    def as_record(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "filled_at": require_utc_datetime(self.filled_at, "filled_at").isoformat(),
            "action": self.action,
            "quantity": str(self.quantity),
            "price": str(self.price),
            "fee": str(self.fee),
        }


@dataclass(frozen=True)
class PaperTradeAccounting:
    feature_id: str
    policy_version: str
    r_multiple_convention: str
    symbol: str
    direction: str
    fills: tuple[TradeFill, ...]
    opened_at: datetime
    closed_at: datetime
    holding_days: Decimal
    initial_quantity: Decimal
    initial_entry_price: Decimal
    initial_stop_price: Decimal
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
    maximum_notional: Decimal
    add_count: int
    trim_count: int
    exit_reason: str
    closed: bool
    config_metadata: dict[str, str]
    reason_codes: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        if self.feature_id != PAPER_TRADE_ACCOUNTING_FEATURE_ID:
            raise ValueError(
                f"feature_id must be {PAPER_TRADE_ACCOUNTING_FEATURE_ID}",
            )
        if self.policy_version != PAPER_TRADE_ACCOUNTING_POLICY_VERSION:
            raise ValueError(
                f"policy_version must be {PAPER_TRADE_ACCOUNTING_POLICY_VERSION}",
            )
        if self.net_pnl != self.gross_pnl - self.fees - self.funding:
            raise ValueError("net P&L must equal gross P&L less fees and funding")
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "r_multiple_convention": self.r_multiple_convention,
            "symbol": self.symbol,
            "direction": self.direction,
            "fills": [fill.as_record() for fill in self.fills],
            "opened_at": self.opened_at.isoformat(),
            "closed_at": self.closed_at.isoformat(),
            "holding_days": str(self.holding_days),
            "initial_quantity": str(self.initial_quantity),
            "initial_entry_price": str(self.initial_entry_price),
            "initial_stop_price": str(self.initial_stop_price),
            "initial_risk": str(self.initial_risk),
            "average_entry_price": str(self.average_entry_price),
            "entry_notional": str(self.entry_notional),
            "exit_notional": str(self.exit_notional),
            "gross_pnl": str(self.gross_pnl),
            "fees": str(self.fees),
            "funding": str(self.funding),
            "net_pnl": str(self.net_pnl),
            "r_multiple": _optional(self.r_multiple),
            "maximum_favourable_excursion": _optional(
                self.maximum_favourable_excursion,
            ),
            "maximum_adverse_excursion": _optional(self.maximum_adverse_excursion),
            "mfe_r": _optional(self.mfe_r),
            "mae_r": _optional(self.mae_r),
            "maximum_quantity": str(self.maximum_quantity),
            "maximum_notional": str(self.maximum_notional),
            "add_count": self.add_count,
            "trim_count": self.trim_count,
            "exit_reason": self.exit_reason,
            "closed": self.closed,
            "config_metadata": dict(self.config_metadata),
            "reason_codes": list(self.reason_codes),
        }

    def as_completed_trade_record(
        self,
        *,
        account_id: int,
        position_id: int,
    ) -> dict[str, Any]:
        """Map onto the ``portfolio.completed_trades`` columns."""

        self.as_record()
        if not self.closed:
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
            "realized_pnl": self.net_pnl,
            "realized_r": self.r_multiple,
        }


def calculate_trade_accounting(
    fills: Iterable[TradeFill],
    *,
    symbol: str,
    direction: str,
    initial_stop_price: Any,
    exit_reason: str,
    funding: Any = Decimal("0"),
    excursion_bars: Sequence[OhlcvBar] | None = None,
    config_metadata: Mapping[str, str] | None = None,
) -> PaperTradeAccounting:
    """Account for one paper trade from its fills."""

    if direction not in TRADE_DIRECTIONS:
        raise ValueError(f"direction must be one of {TRADE_DIRECTIONS}")
    if not symbol or not symbol.strip():
        raise ValueError("symbol must not be empty")
    if not exit_reason or not exit_reason.strip():
        raise ValueError("exit_reason must not be empty")
    ordered = _validate_fills(fills)
    stop_price = _positive(initial_stop_price, "initial_stop_price")
    funding_total = _non_negative(funding, "funding")
    long_position = direction == LONG_DIRECTION

    opening = ordered[0]
    initial_quantity = opening.quantity
    initial_entry_price = opening.price
    initial_risk = initial_quantity * abs(initial_entry_price - stop_price)

    quantity = Decimal("0")
    numerator = Decimal("0")
    opened_quantity = Decimal("0")
    realized = Decimal("0")
    fees = Decimal("0")
    entry_notional = Decimal("0")
    exit_notional = Decimal("0")
    maximum_quantity = Decimal("0")
    maximum_notional = Decimal("0")
    add_count = 0
    trim_count = 0
    # (as_of, quantity, cost_basis, realized_so_far) after each fill, for the
    # excursion walk. The position during a bar is the state left by the last
    # fill at or before that bar. Carrying the basis rather than the average
    # keeps the excursion exact: quantity * price - basis never divides.
    timeline: list[tuple[datetime, Decimal, Decimal, Decimal]] = []

    for fill in ordered:
        fees += fill.fee
        if fill.opening:
            quantity += fill.quantity
            opened_quantity += fill.quantity
            numerator += fill.notional
            entry_notional += fill.notional
            if fill.action == ADD_ACTION:
                add_count += 1
            if quantity > maximum_quantity:
                maximum_quantity = quantity
            # The open position's cost basis, carried without dividing, so the
            # peak is exact rather than a rounded quantity * average.
            if numerator > maximum_notional:
                maximum_notional = numerator
        else:
            if fill.quantity > quantity:
                raise ValueError("a close cannot exceed the open quantity")
            # Pro rata: the weighted average survives a partial close. The
            # final close takes the exact remaining basis instead of a second
            # rounded division, so a fully closed trade's gross P&L is exactly
            # exit notional less entry notional.
            removed = (
                numerator
                if fill.quantity == quantity
                else numerator * fill.quantity / quantity
            )
            realized += (
                fill.notional - removed if long_position else removed - fill.notional
            )
            exit_notional += fill.notional
            numerator -= removed
            quantity -= fill.quantity
            if fill.action == TRIM_ACTION:
                trim_count += 1
        timeline.append((fill.filled_at, quantity, numerator, realized))

    closed = quantity == 0
    average_entry_price = entry_notional / opened_quantity
    opened_at = ordered[0].filled_at
    closed_at = ordered[-1].filled_at
    holding_days = _days_between(opened_at, closed_at)

    gross_pnl = realized
    net_pnl = gross_pnl - fees - funding_total

    r_multiple = None if initial_risk == 0 else net_pnl / initial_risk
    favourable, adverse = _excursions(
        excursion_bars,
        timeline=timeline,
        long_position=long_position,
        opened_at=opened_at,
        closed_at=closed_at,
    )

    reasons: list[str] = []
    reasons.append(
        "TRADE_ACCOUNTING_COMPLETE" if closed else "TRADE_ACCOUNTING_POSITION_STILL_OPEN"
    )
    if net_pnl > 0:
        reasons.append("TRADE_ACCOUNTING_NET_PROFIT")
    elif net_pnl < 0:
        reasons.append("TRADE_ACCOUNTING_NET_LOSS")
    else:
        reasons.append("TRADE_ACCOUNTING_NET_FLAT")
    if gross_pnl > 0 and net_pnl < 0:
        # A trade that was profitable on price and lost after costs is a
        # distinct outcome worth naming rather than a plain loss.
        reasons.append("TRADE_ACCOUNTING_COSTS_REVERSED_A_GROSS_PROFIT")
    if r_multiple is None:
        reasons.append("TRADE_ACCOUNTING_R_UNDEFINED")
    if favourable is None:
        reasons.append("TRADE_ACCOUNTING_NO_EXCURSION_BARS")

    return PaperTradeAccounting(
        feature_id=PAPER_TRADE_ACCOUNTING_FEATURE_ID,
        policy_version=PAPER_TRADE_ACCOUNTING_POLICY_VERSION,
        r_multiple_convention=R_MULTIPLE_CONVENTION,
        symbol=symbol.strip(),
        direction=direction,
        fills=ordered,
        opened_at=opened_at,
        closed_at=closed_at,
        holding_days=holding_days,
        initial_quantity=initial_quantity,
        initial_entry_price=initial_entry_price,
        initial_stop_price=stop_price,
        initial_risk=initial_risk,
        average_entry_price=average_entry_price,
        entry_notional=entry_notional,
        exit_notional=exit_notional,
        gross_pnl=gross_pnl,
        fees=fees,
        funding=funding_total,
        net_pnl=net_pnl,
        r_multiple=r_multiple,
        maximum_favourable_excursion=favourable,
        maximum_adverse_excursion=adverse,
        mfe_r=(
            None if favourable is None or initial_risk == 0 else favourable / initial_risk
        ),
        mae_r=(
            None if adverse is None or initial_risk == 0 else adverse / initial_risk
        ),
        maximum_quantity=maximum_quantity,
        maximum_notional=maximum_notional,
        add_count=add_count,
        trim_count=trim_count,
        exit_reason=exit_reason.strip(),
        closed=closed,
        config_metadata=dict(config_metadata or {}),
        reason_codes=tuple(reasons),
    )


def _excursions(
    bars: Sequence[OhlcvBar] | None,
    *,
    timeline: list[tuple[datetime, Decimal, Decimal, Decimal]],
    long_position: bool,
    opened_at: datetime,
    closed_at: datetime,
) -> tuple[Decimal | None, Decimal | None]:
    """Return the signed peak and trough of total trade P&L across the bars."""

    if not bars:
        return None, None
    favourable: Decimal | None = None
    adverse: Decimal | None = None
    for bar in bars:
        timestamp = require_utc_datetime(bar.timestamp, "excursion_bar.timestamp")
        if timestamp < opened_at or timestamp > closed_at:
            continue
        quantity, basis, realized = _position_at(timeline, timestamp)
        best_price = bar.high if long_position else bar.low
        worst_price = bar.low if long_position else bar.high
        best = realized + _unrealized(quantity, best_price, basis, long_position)
        worst = realized + _unrealized(quantity, worst_price, basis, long_position)
        favourable = best if favourable is None or best > favourable else favourable
        adverse = worst if adverse is None or worst < adverse else adverse
    return favourable, adverse


def _unrealized(
    quantity: Decimal,
    price: Decimal,
    basis: Decimal,
    long_position: bool,
) -> Decimal:
    marked = quantity * price
    return marked - basis if long_position else basis - marked


def _position_at(
    timeline: list[tuple[datetime, Decimal, Decimal, Decimal]],
    timestamp: datetime,
) -> tuple[Decimal, Decimal, Decimal]:
    quantity = Decimal("0")
    basis = Decimal("0")
    realized = Decimal("0")
    for as_of, held, cost, booked in timeline:
        if as_of > timestamp:
            break
        quantity, basis, realized = held, cost, booked
    return quantity, basis, realized


def _validate_fills(fills: Iterable[TradeFill]) -> tuple[TradeFill, ...]:
    ordered = tuple(fills)
    if not ordered:
        raise ValueError("a trade requires at least one fill")
    for fill in ordered:
        if not isinstance(fill, TradeFill):
            raise TypeError("fills must be TradeFill instances")
        if fill.action not in TRADE_FILL_ACTIONS:
            raise ValueError(f"action must be one of {TRADE_FILL_ACTIONS}")
        _positive(fill.quantity, "fill.quantity")
        _positive(fill.price, "fill.price")
        _non_negative(fill.fee, "fill.fee")
        require_utc_datetime(fill.filled_at, "fill.filled_at")
    if ordered[0].action != ENTER_ACTION:
        raise ValueError("the first fill must be an ENTER")
    if any(fill.action == ENTER_ACTION for fill in ordered[1:]):
        raise ValueError("a trade has exactly one ENTER")
    for previous, current in zip(ordered, ordered[1:]):
        if current.filled_at < previous.filled_at:
            raise ValueError("fills must be in non-decreasing time order")
        if current.sequence <= previous.sequence:
            raise ValueError("fill sequences must strictly increase")
    return ordered


def _days_between(opened_at: datetime, closed_at: datetime) -> Decimal:
    delta: timedelta = closed_at - opened_at
    return Decimal(str(delta.total_seconds())) / _SECONDS_PER_DAY


def _optional(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


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


__all__ = [
    "ADD_ACTION",
    "CLOSING_ACTIONS",
    "ENTER_ACTION",
    "EXIT_ACTION",
    "OPENING_ACTIONS",
    "PAPER_TRADE_ACCOUNTING_FEATURE_ID",
    "PAPER_TRADE_ACCOUNTING_POLICY_VERSION",
    "R_MULTIPLE_CONVENTION",
    "TRADE_ACCOUNTING_REASON_CODES",
    "TRADE_DIRECTIONS",
    "TRADE_FILL_ACTIONS",
    "TRIM_ACTION",
    "PaperTradeAccounting",
    "TradeFill",
    "calculate_trade_accounting",
]
