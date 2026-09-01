"""Event-driven backtest engine (BTC-180).

The engine owns exactly two things: the clock and the routing. Every number it
reports is produced by the module that already owns that calculation, because
rulebook 32 rule 15 requires advisory, paper trading and backtesting to share
the same quantitative formulas. A backtester with its own sizing or its own
risk-at-stop is not testing the strategy that will trade.

    risk budget          BTC-144   calculate_risk_budget
    position size        BTC-145   calculate_initial_position_size
    risk at stop         BTC-146   calculate_risk_at_stop
    tranche allocation   BTC-155   calculate_tranche_size
    trailing stop        BTC-156   trail_stop_for_position
    position state       BTC-150   apply_position_event
    execution costs      BTC-160   ExecutionCosts
    entry / stop fills   BTC-161   BTC-162
    add / trim fills     BTC-163   BTC-164
    trade accounting     BTC-165   calculate_trade_accounting

Point-in-time is enforced structurally rather than by discipline. A strategy is
handed only the bars whose ``ingested_at`` is at or before the decision moment,
and every decision it returns is queued for the *next* bar. Nothing can be
executed on the bar that produced it, which is the single mistake that makes a
backtest look profitable.

Within a bar the order is fixed and adverse-first:

    1. a resting stop is checked before anything else
    2. then the intent queued by the previous bar is executed
    3. then the strategy decides, for the next bar

OHLCV cannot say whether the stop or a new order came first inside a bar, so
the engine assumes the stop did. Resolving that tie in the strategy's favour
would manufacture returns that never existed.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from btc_predictor.config.strategy import StrategyConfig, load_strategy_config
from btc_predictor.data import OhlcvBar, require_utc_datetime
from btc_predictor.portfolio.account import (
    ExecutionCosts,
    PaperAccount,
    execution_costs_from_config,
    open_paper_account,
)
from btc_predictor.portfolio.account import BASIS_POINT
from btc_predictor.portfolio.accounting import (
    FundingEvent,
    PaperTradeAccounting,
    TradeFill,
    calculate_trade_accounting,
)
from btc_predictor.portfolio.add_execution import (
    AddExecutionIntent,
    simulate_add_execution,
)
from btc_predictor.portfolio.entry_execution import (
    EntryExecutionIntent,
    simulate_next_bar_entry,
)
from btc_predictor.portfolio.state_machine import (
    ADD,
    ENTER,
    EXIT,
    PENDING_ENTRY,
    STOP_MOVE,
    TRIM,
    PositionLifecycle,
    apply_position_event,
    start_position_lifecycle,
)
from btc_predictor.portfolio.stop_execution import (
    StopExecutionIntent,
    simulate_stop_execution,
)
from btc_predictor.portfolio.trim_execution import (
    TrimExecutionIntent,
    simulate_trim_execution,
)
from btc_predictor.risk.budget import calculate_risk_budget
from btc_predictor.risk.exposure import calculate_risk_at_stop
from btc_predictor.risk.sizing import calculate_initial_position_size
from btc_predictor.risk.tranches import calculate_tranche_size
from btc_predictor.risk.trailing import calculate_trailing_stop


BACKTEST_ENGINE_FEATURE_ID = "EVENT_DRIVEN_BACKTEST"
BACKTEST_ENGINE_POLICY_VERSION = "EVENT_DRIVEN_BACKTEST_V1"

# Declared so the "must not maintain separate formulas" requirement is testable
# rather than aspirational: every entry is a module this engine delegates to.
SHARED_CALCULATION_SOURCES = (
    "btc_predictor.portfolio.account",
    "btc_predictor.portfolio.accounting",
    "btc_predictor.portfolio.add_execution",
    "btc_predictor.portfolio.entry_execution",
    "btc_predictor.portfolio.state_machine",
    "btc_predictor.portfolio.stop_execution",
    "btc_predictor.portfolio.trim_execution",
    "btc_predictor.risk.budget",
    "btc_predictor.risk.exposure",
    "btc_predictor.risk.sizing",
    "btc_predictor.risk.tranches",
    "btc_predictor.risk.trailing",
)

ARM_ENTRY_ACTION = "ARM_ENTRY"
ADD_ACTION = "ADD"
TRIM_ACTION = "TRIM"
TRAIL_ACTION = "TRAIL"
EXIT_ACTION = "EXIT"
BACKTEST_ACTIONS = (
    ARM_ENTRY_ACTION,
    ADD_ACTION,
    TRIM_ACTION,
    TRAIL_ACTION,
    EXIT_ACTION,
)

BACKTEST_REASON_CODES = (
    "BACKTEST_COMPLETE",
    "BACKTEST_NO_BARS",
    "BACKTEST_ENTRY_FILLED",
    "BACKTEST_ENTRY_MISSED",
    "BACKTEST_ENTRY_UNSIZED",
    "BACKTEST_SHORTS_NOT_PERMITTED",
    "BACKTEST_STOPPED_OUT",
    "BACKTEST_EXITED",
    "BACKTEST_ADDED",
    "BACKTEST_ADD_REFUSED",
    "BACKTEST_TRIMMED",
    "BACKTEST_TRIM_REFUSED",
    "BACKTEST_STOP_TRAILED",
    "BACKTEST_POSITION_OPEN_AT_END",
)


@dataclass(frozen=True)
class BacktestContext:
    """What a strategy may see at one decision point, and nothing more."""

    as_of: datetime
    bar: OhlcvBar
    bars: tuple[OhlcvBar, ...]
    account: PaperAccount
    lifecycle: PositionLifecycle
    nav: Decimal
    open_quantity: Decimal
    average_entry_price: Decimal | None
    standing_stop: Decimal | None

    @property
    def position_open(self) -> bool:
        return self.open_quantity > 0


@dataclass(frozen=True)
class BacktestIntent:
    """A decision made on one bar, to be executed on the next."""

    action: str
    direction: str = "long"
    entry_zone_lower: Decimal | None = None
    entry_zone_upper: Decimal | None = None
    stop_price: Decimal | None = None
    entry_conviction: Decimal | None = None
    structure_price: Decimal | None = None
    buffer: Decimal | None = None
    exit_reason: str | None = None
    # BTC-154 and BTC-157 results. The strategy decides; the engine only routes.
    requirements: Any | None = None
    trim_signal: Any | None = None
    trim_fraction: Decimal | None = None

    def __post_init__(self) -> None:
        if self.action not in BACKTEST_ACTIONS:
            raise ValueError(f"action must be one of {BACKTEST_ACTIONS}")
        if self.action == ARM_ENTRY_ACTION:
            for name in ("entry_zone_lower", "entry_zone_upper", "stop_price"):
                if getattr(self, name) is None:
                    raise ValueError(f"an entry intent requires {name}")
            if self.entry_conviction is None:
                raise ValueError("an entry intent requires entry_conviction")
        if self.action == ADD_ACTION and self.requirements is None:
            raise ValueError("an add intent requires a BTC-154 requirements result")
        if self.action == TRIM_ACTION and self.trim_signal is None:
            raise ValueError("a trim intent requires a BTC-157 signal")
        if self.action == TRAIL_ACTION and self.structure_price is None:
            raise ValueError("a trail intent requires structure_price")
        if self.action == EXIT_ACTION and not self.exit_reason:
            raise ValueError("an exit intent requires exit_reason")


@dataclass(frozen=True)
class EquityPoint:
    """NAV and open risk after one bar, both from the shared modules."""

    as_of: datetime
    close: Decimal
    cash: Decimal
    unrealized_pnl: Decimal
    nav: Decimal
    open_quantity: Decimal
    risk_at_stop: Decimal | None
    risk_fraction_nav: Decimal | None

    def as_record(self) -> dict[str, Any]:
        return {
            "as_of": self.as_of.isoformat(),
            "close": str(self.close),
            "cash": str(self.cash),
            "unrealized_pnl": str(self.unrealized_pnl),
            "nav": str(self.nav),
            "open_quantity": str(self.open_quantity),
            "risk_at_stop": _optional(self.risk_at_stop),
            "risk_fraction_nav": _optional(self.risk_fraction_nav),
        }


@dataclass(frozen=True)
class BacktestResult:
    feature_id: str
    policy_version: str
    symbol: str
    started_at: datetime | None
    ended_at: datetime | None
    bar_count: int
    account: PaperAccount
    starting_nav: Decimal
    ending_nav: Decimal
    trades: tuple[PaperTradeAccounting, ...]
    equity_curve: tuple[EquityPoint, ...]
    missed_entries: int
    stopped_out: int
    config_metadata: dict[str, str]
    reason_codes: tuple[str, ...]

    @property
    def net_pnl(self) -> Decimal:
        return sum((trade.net_pnl for trade in self.trades), Decimal("0"))

    def as_record(self) -> dict[str, Any]:
        if self.feature_id != BACKTEST_ENGINE_FEATURE_ID:
            raise ValueError(f"feature_id must be {BACKTEST_ENGINE_FEATURE_ID}")
        if self.policy_version != BACKTEST_ENGINE_POLICY_VERSION:
            raise ValueError(f"policy_version must be {BACKTEST_ENGINE_POLICY_VERSION}")
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "symbol": self.symbol,
            "started_at": _optional_time(self.started_at),
            "ended_at": _optional_time(self.ended_at),
            "bar_count": self.bar_count,
            "starting_nav": str(self.starting_nav),
            "ending_nav": str(self.ending_nav),
            "net_pnl": str(self.net_pnl),
            "trade_count": len(self.trades),
            "trades": [trade.as_record() for trade in self.trades],
            "equity_curve": [point.as_record() for point in self.equity_curve],
            "missed_entries": self.missed_entries,
            "stopped_out": self.stopped_out,
            "account": self.account.as_record(),
            "config_metadata": dict(self.config_metadata),
            "reason_codes": list(self.reason_codes),
        }


def run_backtest(
    bars: Sequence[OhlcvBar],
    *,
    strategy: Callable[[BacktestContext], BacktestIntent | None],
    symbol: str = "BTC-USD",
    starting_nav: Any | None = None,
    strategy_config: StrategyConfig | None = None,
    costs: ExecutionCosts | None = None,
    account: PaperAccount | None = None,
) -> BacktestResult:
    """Replay ``bars`` through the shared execution and risk modules."""

    config = strategy_config if strategy_config is not None else load_strategy_config()
    if not isinstance(config, StrategyConfig):
        raise TypeError("strategy_config must be a StrategyConfig")
    if not callable(strategy):
        raise TypeError("strategy must be callable")
    ordered = _validate_bars(bars, symbol=symbol)
    metadata = config.run_metadata()
    execution_costs = (
        costs if costs is not None else execution_costs_from_config(config)
    )
    state = _EngineState(
        config=config,
        costs=execution_costs,
        symbol=symbol,
        metadata=metadata,
        account=(
            account
            if account is not None
            else open_paper_account(
                account_name=f"backtest-{symbol}",
                created_at=ordered[0].timestamp if ordered else _EPOCH,
                starting_nav=starting_nav,
                costs=execution_costs,
                config=config,
            )
        ),
    )

    if not ordered:
        return _empty_result(state, ("BACKTEST_NO_BARS",))

    for index, bar in enumerate(ordered):
        state.on_bar(bar)
        # A strategy sees only what had been ingested by this bar's close.
        visible = tuple(item for item in ordered[: index + 1] if _visible(item, bar))
        intent = strategy(state.context(bar, visible))
        state.queue(intent, bar)

    state.finalize(ordered[-1])
    reasons = list(state.reason_codes)
    if state.lifecycle.quantity > 0:
        reasons.append("BACKTEST_POSITION_OPEN_AT_END")
    reasons.append("BACKTEST_COMPLETE")
    return _result(state, ordered, tuple(dict.fromkeys(reasons)))


class _EngineState:
    """Mutable run state. Every calculation it performs is delegated."""

    def __init__(
        self,
        *,
        config: StrategyConfig,
        costs: ExecutionCosts,
        symbol: str,
        metadata: dict[str, str],
        account: PaperAccount,
    ) -> None:
        self.config = config
        self.costs = costs
        self.symbol = symbol
        self.metadata = metadata
        self.account = account
        self.starting_nav = account.starting_nav
        self.lifecycle = start_position_lifecycle(
            symbol=symbol,
            config_metadata=metadata,
        )
        self.pending: BacktestIntent | None = None
        self.pending_at: datetime | None = None
        self.fills: list[TradeFill] = []
        self.trade_bars: list[OhlcvBar] = []
        self.initial_stop: Decimal | None = None
        self.initial_stop_source_id: str | None = None
        self.exit_reason: str | None = None
        self.exit_reason_source_id: str | None = None
        self.final_position_notional: Decimal | None = None
        self.pending_notional: Decimal | None = None
        self.funding_events: list[FundingEvent] = []
        self.trades: list[PaperTradeAccounting] = []
        self.equity_curve: list[EquityPoint] = []
        self.reason_codes: list[str] = []
        self.missed_entries = 0
        self.stopped_out = 0
        self.sequence = 0

    # --- per-bar orchestration ------------------------------------------

    def on_bar(self, bar: OhlcvBar) -> None:
        # Adverse first: OHLCV cannot order a stop against a new order inside
        # one bar, so the stop is assumed to have come first.
        self._resolve_stop(bar)
        self._resolve_pending(bar)
        self._charge_funding(bar)
        self._record_equity(bar)
        if self.lifecycle.quantity > 0:
            self.trade_bars.append(bar)

    def queue(self, intent: BacktestIntent | None, bar: OhlcvBar) -> None:
        if intent is not None and not isinstance(intent, BacktestIntent):
            raise TypeError("strategy must return a BacktestIntent or None")
        self.pending = intent
        self.pending_at = bar.timestamp

    def finalize(self, last_bar: OhlcvBar) -> None:
        if self.lifecycle.quantity > 0:
            self._close_trade(last_bar)

    def context(self, bar: OhlcvBar, visible: tuple[OhlcvBar, ...]) -> BacktestContext:
        unrealized = self._unrealized(bar.close)
        return BacktestContext(
            as_of=bar.timestamp,
            bar=bar,
            bars=visible,
            account=self.account,
            lifecycle=self.lifecycle,
            nav=self.account.nav(unrealized_pnl=unrealized),
            open_quantity=self.lifecycle.quantity,
            average_entry_price=self.lifecycle.average_entry_price,
            standing_stop=self.lifecycle.stop_price,
        )

    # --- routed execution -------------------------------------------------

    def _resolve_stop(self, bar: OhlcvBar) -> None:
        if self.lifecycle.quantity <= 0 or self.lifecycle.stop_price is None:
            return
        intent = StopExecutionIntent(
            execution_id=f"stop-{bar.timestamp.isoformat()}",
            position_id=None,
            symbol=self.symbol,
            direction=self.lifecycle.direction,
            timeframe=bar.timeframe,
            stop_price=self.lifecycle.stop_price,
            stop_placed_at=self.lifecycle.opened_at or bar.timestamp,
            average_entry_price=self.lifecycle.average_entry_price,
            open_quantity=self.lifecycle.quantity,
            config_metadata=self.metadata,
        )
        execution = simulate_stop_execution(intent, bar, costs=self.costs)
        if not execution.filled:
            return
        self._record_fill(
            bar,
            action="EXIT",
            quantity=execution.filled_quantity,
            price=execution.average_fill_price,
            fee=execution.fee,
        )
        self.lifecycle = apply_position_event(
            self.lifecycle,
            event=EXIT,
            event_time=bar.timestamp,
        )
        self.stopped_out += 1
        self.exit_reason = "STRUCTURAL_STOP"
        self.exit_reason_source_id = intent.execution_id
        self._note("BACKTEST_STOPPED_OUT")
        self._close_trade(bar)

    def _resolve_pending(self, bar: OhlcvBar) -> None:
        intent, self.pending = self.pending, None
        if intent is None or self.pending_at is None or self.pending_at >= bar.timestamp:
            if intent is not None:
                # Re-queue: the decision has not reached its execution bar yet.
                self.pending = intent
            return
        if intent.action == ARM_ENTRY_ACTION:
            self._execute_entry(intent, bar)
        elif intent.action == ADD_ACTION:
            self._execute_add(intent, bar)
        elif intent.action == TRIM_ACTION:
            self._execute_trim(intent, bar)
        elif intent.action == TRAIL_ACTION:
            self._execute_trail(intent, bar)
        elif intent.action == EXIT_ACTION:
            self._execute_exit(intent, bar)

    def _execute_entry(self, intent: BacktestIntent, bar: OhlcvBar) -> None:
        if self.lifecycle.quantity > 0:
            return
        if intent.direction == "short" and not self.config.backtest.allow_short_trades:
            self._note("BACKTEST_SHORTS_NOT_PERMITTED")
            return

        quantity = self._entry_quantity(intent, bar)
        if quantity is None:
            self._note("BACKTEST_ENTRY_UNSIZED")
            return

        # A decision taken on the previous bar becomes actionable at that
        # bar's close, which is this bar's opening boundary. Dating it to the
        # decision bar's own start would make that bar its own execution bar.
        decision_at = bar.timestamp
        execution = simulate_next_bar_entry(
            EntryExecutionIntent(
                execution_id=f"entry-{decision_at.isoformat()}",
                recommendation_id=None,
                symbol=self.symbol,
                direction=intent.direction,
                decision_at=decision_at,
                timeframe=bar.timeframe,
                entry_zone_lower=intent.entry_zone_lower,
                entry_zone_upper=intent.entry_zone_upper,
                entry_zone_available_at=decision_at,
                requested_quantity=quantity,
                config_metadata=self.metadata,
            ),
            bar,
            costs=self.costs,
        )
        if execution.missed:
            self.missed_entries += 1
            self._note("BACKTEST_ENTRY_MISSED")
            return

        self.lifecycle = start_position_lifecycle(
            symbol=self.symbol,
            direction=intent.direction,
            state=PENDING_ENTRY,
            config_metadata=self.metadata,
        )
        self.lifecycle = apply_position_event(
            self.lifecycle,
            event=ENTER,
            event_time=bar.timestamp,
            quantity=execution.filled_quantity,
            price=execution.average_fill_price,
            stop_price=intent.stop_price,
        )
        self.initial_stop = intent.stop_price
        self.initial_stop_source_id = execution.intent.execution_id
        # The whole-position size the tranche schedule allocates against, so a
        # later add draws from the same BTC-155 schedule rather than resizing.
        self.final_position_notional = self.pending_notional
        self.fills = []
        self.trade_bars = []
        self.exit_reason = None
        self._record_fill(
            bar,
            action="ENTER",
            quantity=execution.filled_quantity,
            price=execution.average_fill_price,
            fee=execution.fee,
        )
        self.account = self.account.charge_fee(execution.notional)
        self._note("BACKTEST_ENTRY_FILLED")

    def _entry_quantity(
        self,
        intent: BacktestIntent,
        bar: OhlcvBar,
    ) -> Decimal | None:
        """Size through BTC-144, BTC-145 and BTC-155 rather than locally."""

        reference = intent.entry_zone_upper
        distance = abs(reference - intent.stop_price) / reference
        budget = calculate_risk_budget(
            entry_conviction=intent.entry_conviction,
            nav=self.account.nav(unrealized_pnl=self._unrealized(bar.close)),
            config=self.config,
        )
        if not budget.complete:
            return None
        size = calculate_initial_position_size(
            nav=budget.nav,
            risk_fraction_nav=budget.risk_fraction_nav,
            stop_distance_fraction=distance,
            entry_price=reference,
        )
        if not size.complete:
            return None
        tranche = calculate_tranche_size(
            tranche_number=1,
            final_position_notional=size.position_notional,
            entry_price=reference,
            config=self.config,
        )
        if not tranche.complete or tranche.allocation.quantity is None:
            return None
        self.pending_notional = size.position_notional
        return tranche.allocation.quantity

    def _execute_add(self, intent: BacktestIntent, bar: OhlcvBar) -> None:
        if self.lifecycle.quantity <= 0 or self.final_position_notional is None:
            return
        # The next stage of the same BTC-155 schedule the entry was cut from.
        tranche = calculate_tranche_size(
            tranche_number=self.lifecycle.tranche_count + 1,
            final_position_notional=self.final_position_notional,
            entry_price=bar.open,
            config=self.config,
        )
        execution = simulate_add_execution(
            AddExecutionIntent(
                execution_id=f"add-{bar.timestamp.isoformat()}",
                position_id=None,
                recommendation_id=None,
                symbol=self.symbol,
                direction=self.lifecycle.direction,
                timeframe=bar.timeframe,
                decision_at=bar.timestamp,
                average_entry_price=self.lifecycle.average_entry_price,
                config_metadata=self.metadata,
            ),
            bar,
            requirements=intent.requirements,
            tranche=tranche,
            costs=self.costs,
        )
        if not execution.filled:
            self._note("BACKTEST_ADD_REFUSED")
            return
        added = apply_position_event(
            self.lifecycle,
            event=ADD,
            event_time=bar.timestamp,
            quantity=execution.filled_quantity,
            price=execution.average_fill_price,
        )
        if not added.accepted:
            # BTC-150 and BTC-151 have the final word on the ledger.
            self._note("BACKTEST_ADD_REFUSED")
            return
        self.lifecycle = added
        self._record_fill(
            bar,
            action="ADD",
            quantity=execution.filled_quantity,
            price=execution.average_fill_price,
            fee=execution.fee,
        )
        self.account = self.account.charge_fee(execution.notional)
        self._note("BACKTEST_ADDED")

    def _execute_trim(self, intent: BacktestIntent, bar: OhlcvBar) -> None:
        if self.lifecycle.quantity <= 0:
            return
        trim_intent = TrimExecutionIntent(
            execution_id=f"trim-{bar.timestamp.isoformat()}",
            position_id=None,
            recommendation_id=None,
            symbol=self.symbol,
            direction=self.lifecycle.direction,
            timeframe=bar.timeframe,
            decision_at=bar.timestamp,
            average_entry_price=self.lifecycle.average_entry_price,
            open_quantity=self.lifecycle.quantity,
            config_metadata=self.metadata,
        )
        if intent.trim_fraction is not None:
            trim_intent = replace(trim_intent, trim_fraction=intent.trim_fraction)
        execution = simulate_trim_execution(
            trim_intent,
            bar,
            signal=intent.trim_signal,
            costs=self.costs,
        )
        if not execution.filled:
            self._note("BACKTEST_TRIM_REFUSED")
            return
        trimmed = apply_position_event(
            self.lifecycle,
            event=TRIM,
            event_time=bar.timestamp,
            quantity=execution.filled_quantity,
        )
        if not trimmed.accepted:
            self._note("BACKTEST_TRIM_REFUSED")
            return
        self.lifecycle = trimmed
        self._record_fill(
            bar,
            action="TRIM",
            quantity=execution.filled_quantity,
            price=execution.average_fill_price,
            fee=execution.fee,
        )
        self.account = self.account.charge_fee(execution.notional)
        self._note("BACKTEST_TRIMMED")

    def _execute_trail(self, intent: BacktestIntent, bar: OhlcvBar) -> None:
        if self.lifecycle.quantity <= 0 or self.lifecycle.stop_price is None:
            return
        trailed = calculate_trailing_stop(
            direction=self.lifecycle.direction,
            previous_stop=self.lifecycle.stop_price,
            structure_price=intent.structure_price,
            buffer=intent.buffer if intent.buffer is not None else Decimal("0"),
            current_price=bar.open,
        )
        if not trailed.advanced:
            return
        moved = apply_position_event(
            self.lifecycle,
            event=STOP_MOVE,
            event_time=bar.timestamp,
            stop_price=trailed.stop_price,
        )
        if moved.accepted:
            self.lifecycle = moved
            self._note("BACKTEST_STOP_TRAILED")

    def _execute_exit(self, intent: BacktestIntent, bar: OhlcvBar) -> None:
        if self.lifecycle.quantity <= 0:
            return
        fill_price = self.costs.fill_price(
            bar.open,
            side="sell" if self.lifecycle.direction == "long" else "buy",
        )
        quantity = self.lifecycle.quantity
        notional = quantity * fill_price
        self._record_fill(
            bar,
            action="EXIT",
            quantity=quantity,
            price=fill_price,
            fee=self.costs.fee(notional),
        )
        self.lifecycle = apply_position_event(
            self.lifecycle,
            event=EXIT,
            event_time=bar.timestamp,
        )
        self.exit_reason = intent.exit_reason
        self.exit_reason_source_id = f"exit-{bar.timestamp.isoformat()}"
        self._note("BACKTEST_EXITED")
        self._close_trade(bar)

    # --- bookkeeping ------------------------------------------------------

    def _record_fill(
        self,
        bar: OhlcvBar,
        *,
        action: str,
        quantity: Decimal,
        price: Decimal,
        fee: Decimal,
    ) -> None:
        self.sequence += 1
        self.fills.append(
            TradeFill(
                sequence=self.sequence,
                filled_at=bar.timestamp,
                action=action,
                quantity=quantity,
                price=price,
                fee=fee,
                source_event_id=f"{action.lower()}-{bar.timestamp.isoformat()}",
                execution_bar_at=bar.timestamp,
                execution_bar_timeframe=bar.timeframe,
            )
        )

    def _close_trade(self, bar: OhlcvBar) -> None:
        if not self.fills or self.initial_stop is None:
            return
        accounting = calculate_trade_accounting(
            tuple(self.fills),
            symbol=self.symbol,
            direction=self.lifecycle.direction,
            initial_stop_price=self.initial_stop,
            initial_stop_source_id=self.initial_stop_source_id,
            exit_reason=self.exit_reason,
            exit_reason_source_id=self.exit_reason_source_id,
            funding_events=tuple(self.funding_events),
            excursion_bars=tuple(self.trade_bars) or None,
            as_of=bar.timestamp,
            config_metadata=self.metadata,
        )
        self.trades.append(accounting)
        self.account = self.account.settle_realized_pnl(accounting.gross_pnl)
        self.fills = []
        self.trade_bars = []
        self.funding_events = []
        self.final_position_notional = None
        self.initial_stop = None
        self.initial_stop_source_id = None
        self.exit_reason = None
        self.exit_reason_source_id = None

    def _charge_funding(self, bar: OhlcvBar) -> None:
        """Accrue carry as a replayable event, never as an opaque total."""

        days = _bar_days(bar.timeframe)
        quantity = self.lifecycle.quantity
        if quantity <= 0 or days <= 0 or self.costs.funding_cost_bps_per_day == 0:
            return
        if any(fill.filled_at == bar.timestamp for fill in self.fills):
            # A bar that also filled would make the event's recorded quantity
            # ambiguous against the ledger at that instant.
            return
        notional = quantity * bar.open
        cost = self.costs.funding(notional, days=days)
        self.sequence += 1
        self.funding_events.append(
            FundingEvent(
                sequence=self.sequence,
                event_id=f"funding-{bar.timestamp.isoformat()}",
                effective_at=bar.timestamp,
                rate=self.costs.funding_cost_bps_per_day * BASIS_POINT * days,
                mark_price=bar.open,
                position_quantity=quantity,
                funding_cost=cost,
            )
        )
        self.account = self.account.charge_funding(notional, days=days)

    def _record_equity(self, bar: OhlcvBar) -> None:
        unrealized = self._unrealized(bar.close)
        nav = self.account.nav(unrealized_pnl=unrealized)
        risk_amount: Decimal | None = None
        risk_fraction: Decimal | None = None
        if self.lifecycle.quantity > 0 and self.lifecycle.stop_price is not None:
            exposure = calculate_risk_at_stop(
                [
                    {
                        "tranche_id": f"t{tranche.tranche_number}",
                        "quantity": tranche.quantity,
                        "entry_price": tranche.entry_price,
                    }
                    for tranche in self.lifecycle.tranches
                ],
                stop_price=self.lifecycle.stop_price,
                nav=nav,
                direction=self.lifecycle.direction,
                config=self.config,
            )
            risk_amount = exposure.risk_at_stop
            risk_fraction = exposure.risk_fraction_nav
        self.equity_curve.append(
            EquityPoint(
                as_of=bar.timestamp,
                close=bar.close,
                cash=self.account.cash,
                unrealized_pnl=unrealized,
                nav=nav,
                open_quantity=self.lifecycle.quantity,
                risk_at_stop=risk_amount,
                risk_fraction_nav=risk_fraction,
            )
        )

    def _unrealized(self, price: Decimal) -> Decimal:
        quantity = self.lifecycle.quantity
        average = self.lifecycle.average_entry_price
        if quantity <= 0 or average is None:
            return Decimal("0")
        marked = quantity * price
        basis = quantity * average
        return marked - basis if self.lifecycle.direction == "long" else basis - marked

    def _note(self, code: str) -> None:
        if code not in self.reason_codes:
            self.reason_codes.append(code)


_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_BAR_DAYS = {
    "1h": Decimal("1") / Decimal("24"),
    "1d": Decimal("1"),
    "1w": Decimal("7"),
    "1mo": Decimal("30"),
}


def _bar_days(timeframe: str) -> Decimal:
    return _BAR_DAYS.get(timeframe, Decimal("0"))


def _visible(candidate: OhlcvBar, decision_bar: OhlcvBar) -> bool:
    """A bar is visible only once it has actually been ingested."""

    return candidate.ingested_at <= decision_bar.ingested_at


def _validate_bars(
    bars: Sequence[OhlcvBar],
    *,
    symbol: str,
) -> tuple[OhlcvBar, ...]:
    ordered = tuple(bars)
    timeframe: str | None = None
    for bar in ordered:
        if not isinstance(bar, OhlcvBar):
            raise TypeError("bars must be OhlcvBar instances")
        require_utc_datetime(bar.timestamp, "bar.timestamp")
        require_utc_datetime(bar.ingested_at, "bar.ingested_at")
        if bar.symbol != symbol:
            raise ValueError("every bar must belong to the backtest symbol")
        if timeframe is None:
            timeframe = bar.timeframe
        elif bar.timeframe != timeframe:
            raise ValueError("every bar must share one timeframe")
    for previous, current in zip(ordered, ordered[1:]):
        if current.timestamp <= previous.timestamp:
            raise ValueError("bars must be in strictly increasing time order")
    return ordered


def _empty_result(
    state: _EngineState,
    reasons: tuple[str, ...],
) -> BacktestResult:
    return BacktestResult(
        feature_id=BACKTEST_ENGINE_FEATURE_ID,
        policy_version=BACKTEST_ENGINE_POLICY_VERSION,
        symbol=state.symbol,
        started_at=None,
        ended_at=None,
        bar_count=0,
        account=state.account,
        starting_nav=state.starting_nav,
        ending_nav=state.account.nav(),
        trades=(),
        equity_curve=(),
        missed_entries=0,
        stopped_out=0,
        config_metadata=dict(state.metadata),
        reason_codes=reasons,
    )


def _result(
    state: _EngineState,
    bars: tuple[OhlcvBar, ...],
    reasons: tuple[str, ...],
) -> BacktestResult:
    return BacktestResult(
        feature_id=BACKTEST_ENGINE_FEATURE_ID,
        policy_version=BACKTEST_ENGINE_POLICY_VERSION,
        symbol=state.symbol,
        started_at=bars[0].timestamp,
        ended_at=bars[-1].timestamp,
        bar_count=len(bars),
        account=state.account,
        starting_nav=state.starting_nav,
        ending_nav=state.equity_curve[-1].nav if state.equity_curve else state.account.nav(),
        trades=tuple(state.trades),
        equity_curve=tuple(state.equity_curve),
        missed_entries=state.missed_entries,
        stopped_out=state.stopped_out,
        config_metadata=dict(state.metadata),
        reason_codes=reasons,
    )


def _optional(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _optional_time(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


__all__ = [
    "ADD_ACTION",
    "ARM_ENTRY_ACTION",
    "BACKTEST_ACTIONS",
    "BACKTEST_ENGINE_FEATURE_ID",
    "BACKTEST_ENGINE_POLICY_VERSION",
    "BACKTEST_REASON_CODES",
    "EXIT_ACTION",
    "SHARED_CALCULATION_SOURCES",
    "TRAIL_ACTION",
    "TRIM_ACTION",
    "BacktestContext",
    "BacktestIntent",
    "BacktestResult",
    "EquityPoint",
    "run_backtest",
]
