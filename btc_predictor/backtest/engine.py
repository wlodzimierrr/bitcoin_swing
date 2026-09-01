"""Point-in-time event-driven backtest orchestration (BTC-180).

``EVENT_DRIVEN_BACKTEST_V1`` owns the clock, conservative event ordering, and
routing. Economic calculations remain in their BTC-142/BTC-144..165 owner
modules. A market bar is decision-available only after both its close boundary
and its ingestion timestamp, and a decision can execute only on its owner's
first eligible later market bar.

Per market bar the deterministic order is:

1. accrue fixed-policy carry for the position held before bar execution;
2. resolve the resting stop against the full bar;
3. resolve one intent queued by an earlier decision; an entry's pre-authorized
   bracket stop is then resolved against the same ambiguous bar;
4. install a queued trailing stop at bar resolution for later bars;
5. mark NAV/risk at the bar close and expose that post-event state to strategy;
6. queue at most one intent for a future eligible bar.

Funding is intentionally settled immediately before bar resolution against the
pre-execution position. Entry fills do not pay carry for time before they
existed; ADD/TRIM/EXIT/STOP bars charge the quantity held entering the bar.
This makes fill/funding collisions explicit and replayable instead of dropping
every funding event on a fill bar.
"""

from __future__ import annotations

import hashlib
import json
import marshal
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from btc_predictor.backtest.costs import (
    COST_PROFILES,
    CostProfile,
    cost_profile as resolve_cost_profile,
    restore_cost_profile,
)
from btc_predictor.config.strategy import StrategyConfig, load_strategy_config
from btc_predictor.data import OhlcvBar, next_bar_timestamp, require_utc_datetime
from btc_predictor.portfolio.account import (
    ExecutionCosts,
    PaperAccount,
    execution_costs_from_config,
    open_paper_account,
)
from btc_predictor.portfolio.accounting import (
    FundingEvent,
    PaperTradeAccounting,
    TradeFill,
    calculate_trade_accounting_for_lifecycle,
    funding_event_from_rate,
    restore_trade_accounting,
    trade_fill_from_execution,
)
from btc_predictor.portfolio.add_execution import (
    AddExecutionIntent,
    simulate_add_execution,
)
from btc_predictor.portfolio.entry_execution import (
    EntryExecutionIntent,
    next_eligible_bar_timestamp,
    simulate_next_bar_entry,
)
from btc_predictor.portfolio.exit_execution import (
    ExitExecutionIntent,
    simulate_exit_execution,
)
from btc_predictor.portfolio.state_machine import (
    ADD,
    ENTER,
    EXIT,
    PENDING_ENTRY,
    TRIM,
    PositionLifecycle,
    apply_position_event,
    restore_position_lifecycle,
    start_position_lifecycle,
)
from btc_predictor.portfolio.stop_execution import stop_execution_for_position
from btc_predictor.portfolio.trim_execution import (
    TrimExecutionIntent,
    simulate_trim_execution,
)
from btc_predictor.quant.arrays import PARITY_ABSOLUTE_TOLERANCE
from btc_predictor.quant.portfolio import unrealized_pnl as quant_unrealized_pnl
from btc_predictor.risk.budget import calculate_risk_budget
from btc_predictor.risk.exposure import calculate_risk_at_stop
from btc_predictor.risk.sizing import (
    InitialPositionSizeResult,
    initial_position_size_for_trade,
)
from btc_predictor.risk.stop import InitialStopResult
from btc_predictor.risk.trailing import (
    TrailingStopResult,
    apply_trailing_stop,
    used_trailing_structure_ids,
)
from btc_predictor.risk.tranches import (
    TrancheSizingResult,
    calculate_tranche_size,
    next_tranche_for_position,
)


BACKTEST_ENGINE_FEATURE_ID = "EVENT_DRIVEN_BACKTEST"
BACKTEST_ENGINE_POLICY_VERSION = "EVENT_DRIVEN_BACKTEST_V1"
BACKTEST_FUNDING_POLICY_VERSION = "BAR_CLOSE_PRE_EXECUTION_CARRY_V1"
BACKTEST_NAV_POLICY_VERSION = "CASH_PLUS_MARKED_UNREALIZED_V1"
BACKTEST_END_POLICY_VERSION = "MARK_OPEN_POSITION_NO_FORCED_EXIT_V1"
BACKTEST_RECONCILIATION_TOLERANCE = Decimal(str(PARITY_ABSOLUTE_TOLERANCE))

SHARED_CALCULATION_SOURCES = (
    "btc_predictor.backtest.costs",
    "btc_predictor.portfolio.account",
    "btc_predictor.portfolio.accounting",
    "btc_predictor.portfolio.add_execution",
    "btc_predictor.portfolio.entry_execution",
    "btc_predictor.portfolio.exit_execution",
    "btc_predictor.portfolio.state_machine",
    "btc_predictor.portfolio.stop_execution",
    "btc_predictor.portfolio.trim_execution",
    "btc_predictor.quant.portfolio",
    "btc_predictor.risk.budget",
    "btc_predictor.risk.exposure",
    "btc_predictor.risk.sizing",
    "btc_predictor.risk.stop",
    "btc_predictor.risk.trailing",
    "btc_predictor.risk.tranches",
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
    "BACKTEST_COST_PROFILE_APPLIED",
    "BACKTEST_ENTRY_FILLED",
    "BACKTEST_ENTRY_MISSED",
    "BACKTEST_ENTRY_UNSIZED",
    "BACKTEST_ENTRY_REFUSED",
    "BACKTEST_SHORTS_NOT_PERMITTED",
    "BACKTEST_STOPPED_OUT",
    "BACKTEST_EXITED",
    "BACKTEST_ADDED",
    "BACKTEST_ADD_REFUSED",
    "BACKTEST_TRIMMED",
    "BACKTEST_TRIM_REFUSED",
    "BACKTEST_STOP_TRAILED",
    "BACKTEST_TRAIL_HELD",
    "BACKTEST_INTENT_REFUSED",
    "BACKTEST_INTENT_STALE",
    "BACKTEST_INTENT_EXPIRED",
    "BACKTEST_INTENT_UNEXECUTED_END",
    "BACKTEST_POSITION_OPEN_AT_END",
)

QUEUED = "QUEUED"
EXECUTED = "EXECUTED"
REFUSED = "REFUSED"
MISSED = "MISSED"
STALE = "STALE"
EXPIRED = "EXPIRED"
UNEXECUTED = "UNEXECUTED"
RESTING = "RESTING"
APPLIED = "APPLIED"


@dataclass(frozen=True)
class BacktestContext:
    """Defensive point-in-time state exposed to one strategy decision."""

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
    """One strategy decision, routed no earlier than its next eligible bar."""

    action: str
    direction: str = "long"
    entry_zone_lower: Decimal | None = None
    entry_zone_upper: Decimal | None = None
    initial_stop: InitialStopResult | None = None
    entry_conviction: Decimal | None = None
    requirements: Any | None = None
    trim_signal: Any | None = None
    trim_fraction: Decimal | None = None
    trailing_stop: TrailingStopResult | None = None
    exit_reason: str | None = None
    source_id: str | None = None

    def __post_init__(self) -> None:
        if self.action not in BACKTEST_ACTIONS:
            raise ValueError(f"action must be one of {BACKTEST_ACTIONS}")
        if self.direction not in ("long", "short"):
            raise ValueError("direction must be long or short")
        if self.source_id is not None and not self.source_id.strip():
            raise ValueError("source_id must not be empty")
        if self.action == ARM_ENTRY_ACTION:
            for name in ("entry_zone_lower", "entry_zone_upper", "initial_stop"):
                if getattr(self, name) is None:
                    raise ValueError(f"an entry intent requires {name}")
            if self.entry_conviction is None:
                raise ValueError("an entry intent requires entry_conviction")
        if self.action == ADD_ACTION and self.requirements is None:
            raise ValueError("an add intent requires a BTC-154 requirements result")
        if self.action == TRIM_ACTION and self.trim_signal is None:
            raise ValueError("a trim intent requires a BTC-157 signal")
        if self.action == TRAIL_ACTION and self.trailing_stop is None:
            raise ValueError("a trail intent requires a BTC-156 result")
        if self.action == EXIT_ACTION and not self.exit_reason:
            raise ValueError("an exit intent requires exit_reason")

    def as_record(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "direction": self.direction,
            "entry_zone_lower": _optional(self.entry_zone_lower),
            "entry_zone_upper": _optional(self.entry_zone_upper),
            "initial_stop": _upstream_record(self.initial_stop),
            "entry_conviction": _optional(self.entry_conviction),
            "requirements": _upstream_record(self.requirements),
            "trim_signal": _upstream_record(self.trim_signal),
            "trim_fraction": _optional(self.trim_fraction),
            "trailing_stop": _upstream_record(self.trailing_stop),
            "exit_reason": self.exit_reason,
            "source_id": self.source_id,
        }


@dataclass(frozen=True)
class BacktestEvent:
    sequence: int
    occurred_at: datetime
    event_type: str
    action: str | None
    status: str
    source_id: str
    reason_codes: tuple[str, ...]
    evidence: dict[str, Any]

    def as_record(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "occurred_at": self.occurred_at.isoformat(),
            "event_type": self.event_type,
            "action": self.action,
            "status": self.status,
            "source_id": self.source_id,
            "reason_codes": list(self.reason_codes),
            "evidence": _json_copy(self.evidence),
        }


@dataclass(frozen=True)
class EquityPoint:
    as_of: datetime
    bar_timestamp: datetime
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
            "bar_timestamp": self.bar_timestamp.isoformat(),
            "close": str(self.close),
            "cash": str(self.cash),
            "unrealized_pnl": str(self.unrealized_pnl),
            "nav": str(self.nav),
            "open_quantity": str(self.open_quantity),
            "risk_at_stop": _optional(self.risk_at_stop),
            "risk_fraction_nav": _optional(self.risk_fraction_nav),
            "nav_policy_version": BACKTEST_NAV_POLICY_VERSION,
        }


@dataclass(frozen=True)
class BacktestResult:
    feature_id: str
    policy_version: str
    funding_policy_version: str
    end_policy_version: str
    run_id: str
    evidence_digest: str
    input_digest: str
    strategy_id: str
    symbol: str
    started_at: datetime | None
    ended_at: datetime | None
    bar_count: int
    input_bars: tuple[OhlcvBar, ...]
    effective_costs: ExecutionCosts
    cost_profile: CostProfile | None
    account: PaperAccount
    final_lifecycle: PositionLifecycle
    starting_nav: Decimal
    ending_nav: Decimal
    trades: tuple[PaperTradeAccounting, ...]
    equity_curve: tuple[EquityPoint, ...]
    events: tuple[BacktestEvent, ...]
    missed_entries: int
    stopped_out: int
    config_metadata: dict[str, str]
    reason_codes: tuple[str, ...]

    @property
    def net_pnl(self) -> Decimal:
        return sum((trade.net_pnl for trade in self.trades), Decimal("0"))

    @property
    def total_pnl(self) -> Decimal:
        return self.ending_nav - self.starting_nav

    def as_record(self) -> dict[str, Any]:
        if self.feature_id != BACKTEST_ENGINE_FEATURE_ID:
            raise ValueError(f"feature_id must be {BACKTEST_ENGINE_FEATURE_ID}")
        if self.policy_version != BACKTEST_ENGINE_POLICY_VERSION:
            raise ValueError(f"policy_version must be {BACKTEST_ENGINE_POLICY_VERSION}")
        _validate_result(self)
        payload = _result_payload(self)
        if _digest(payload) != self.evidence_digest:
            raise ValueError("backtest evidence does not match evidence_digest")
        return {**payload, "evidence_digest": self.evidence_digest}


@dataclass(frozen=True)
class _QueuedIntent:
    intent: BacktestIntent
    source_id: str
    decision_bar_at: datetime
    decision_at: datetime
    eligible_bar_at: datetime
    expected_state: str
    expected_last_event_at: datetime | None
    expected_quantity: Decimal
    position_size: InitialPositionSizeResult | None = None
    initial_tranche: TrancheSizingResult | None = None


def run_backtest(
    bars: Sequence[OhlcvBar],
    *,
    strategy: Callable[[BacktestContext], BacktestIntent | None],
    symbol: str = "BTC-USD",
    starting_nav: Any | None = None,
    strategy_config: StrategyConfig | None = None,
    costs: ExecutionCosts | None = None,
    cost_profile: str | None = None,
    account: PaperAccount | None = None,
    strategy_id: str | None = None,
) -> BacktestResult:
    """Replay canonical bars through shared execution, risk, and accounting.

    ``cost_profile`` names one BTC-181 rung to execute under. Leaving it
    unset keeps the BTC-180 resolution order (explicit costs, else the
    account's, else configuration) and records no profile, because a run
    that did not select a ladder rung must not claim it did.
    """

    config = strategy_config if strategy_config is not None else load_strategy_config()
    if not isinstance(config, StrategyConfig):
        raise TypeError("strategy_config must be a StrategyConfig")
    if not callable(strategy):
        raise TypeError("strategy must be callable")
    ordered = _validate_bars(bars, symbol=symbol)
    metadata = config.run_metadata()
    profile = _resolve_cost_profile(cost_profile, config)
    effective_costs, resolved_account = _resolve_account_and_costs(
        ordered=ordered,
        symbol=symbol,
        config=config,
        metadata=metadata,
        costs=costs,
        profile=profile,
        account=account,
        starting_nav=starting_nav,
    )
    resolved_strategy_id = _strategy_identifier(strategy, strategy_id)
    state = _EngineState(
        config=config,
        costs=effective_costs,
        cost_profile=profile,
        symbol=symbol,
        metadata=metadata,
        account=resolved_account,
        strategy_id=resolved_strategy_id,
    )

    if not ordered:
        return _empty_result(state)

    for index, bar in enumerate(ordered):
        state.on_bar(bar)
        # Availability is validated as nondecreasing, so this immutable prefix
        # is exactly the PIT-visible set without rescanning prior bars.
        visible = ordered[: index + 1]
        intent = strategy(state.context(bar, visible))
        state.queue(intent, bar)

    state.finalize(ordered[-1])
    return _result(state, ordered)


def restore_backtest_result(record: Mapping[str, Any]) -> BacktestResult:
    """Restore persisted BTC-180 evidence and reject drift or tampering."""

    source = _mapping(record, "record")
    costs = _costs_from_record(_mapping(source.get("effective_costs"), "effective_costs"))
    profile_record = source.get("cost_profile")
    profile = (
        restore_cost_profile(_mapping(profile_record, "cost_profile"))
        if profile_record is not None
        else None
    )
    bars = tuple(
        _bar_from_record(_mapping(item, "input_bar"))
        for item in _record_sequence(source.get("input_bars"), "input_bars")
    )
    account_record = _mapping(source.get("account"), "account")
    account_costs = _costs_from_record(
        _mapping(account_record.get("costs"), "account.costs")
    )
    account = PaperAccount(
        feature_id=_string(account_record.get("feature_id"), "account.feature_id"),
        policy_version=_string(
            account_record.get("policy_version"), "account.policy_version"
        ),
        account_name=_string(account_record.get("account_name"), "account.account_name"),
        base_currency=_string(
            account_record.get("base_currency"), "account.base_currency"
        ),
        starting_nav=_decimal(account_record.get("starting_nav"), "account.starting_nav"),
        cash=_decimal(account_record.get("cash"), "account.cash"),
        reserved_cash=_decimal(
            account_record.get("reserved_cash"), "account.reserved_cash"
        ),
        realized_pnl=_decimal(
            account_record.get("realized_pnl"), "account.realized_pnl"
        ),
        fees_paid=_decimal(account_record.get("fees_paid"), "account.fees_paid"),
        funding_paid=_decimal(
            account_record.get("funding_paid"), "account.funding_paid"
        ),
        costs=account_costs,
        status=_string(account_record.get("status"), "account.status"),
        created_at=_utc(account_record.get("created_at"), "account.created_at"),
        config_metadata=_string_mapping(
            account_record.get("config_metadata"), "account.config_metadata"
        ),
        reason_codes=_string_tuple(
            account_record.get("reason_codes"), "account.reason_codes"
        ),
    )
    account.as_record()
    lifecycle = restore_position_lifecycle(
        _mapping(source.get("final_lifecycle"), "final_lifecycle")
    )
    trades = tuple(
        restore_trade_accounting(_mapping(item, "trade"))
        for item in _record_sequence(source.get("trades"), "trades")
    )
    equity_curve = tuple(
        _equity_from_record(_mapping(item, "equity_point"))
        for item in _record_sequence(source.get("equity_curve"), "equity_curve")
    )
    events = tuple(
        _event_from_record(_mapping(item, "event"))
        for item in _record_sequence(source.get("events"), "events")
    )
    result = BacktestResult(
        feature_id=_string(source.get("feature_id"), "feature_id"),
        policy_version=_string(source.get("policy_version"), "policy_version"),
        funding_policy_version=_string(
            source.get("funding_policy_version"), "funding_policy_version"
        ),
        end_policy_version=_string(
            source.get("end_policy_version"), "end_policy_version"
        ),
        run_id=_string(source.get("run_id"), "run_id"),
        evidence_digest=_string(source.get("evidence_digest"), "evidence_digest"),
        input_digest=_string(source.get("input_digest"), "input_digest"),
        strategy_id=_string(source.get("strategy_id"), "strategy_id"),
        symbol=_string(source.get("symbol"), "symbol"),
        started_at=_optional_utc(source.get("started_at"), "started_at"),
        ended_at=_optional_utc(source.get("ended_at"), "ended_at"),
        bar_count=_non_negative_integer(source.get("bar_count"), "bar_count"),
        input_bars=bars,
        effective_costs=costs,
        cost_profile=profile,
        account=account,
        final_lifecycle=lifecycle,
        starting_nav=_decimal(source.get("starting_nav"), "starting_nav"),
        ending_nav=_decimal(source.get("ending_nav"), "ending_nav"),
        trades=trades,
        equity_curve=equity_curve,
        events=events,
        missed_entries=_non_negative_integer(
            source.get("missed_entries"), "missed_entries"
        ),
        stopped_out=_non_negative_integer(source.get("stopped_out"), "stopped_out"),
        config_metadata=_string_mapping(
            source.get("config_metadata"), "config_metadata"
        ),
        reason_codes=_string_tuple(source.get("reason_codes"), "reason_codes"),
    )
    if result.as_record() != source:
        raise ValueError("record does not match reconstructed backtest evidence")
    return result


class _EngineState:
    def __init__(
        self,
        *,
        config: StrategyConfig,
        costs: ExecutionCosts,
        cost_profile: CostProfile | None,
        symbol: str,
        metadata: dict[str, str],
        account: PaperAccount,
        strategy_id: str,
    ) -> None:
        self.config = config
        self.costs = costs
        self.cost_profile = cost_profile
        self.symbol = symbol
        self.metadata = dict(metadata)
        self.account = account
        self.strategy_id = strategy_id
        self.starting_nav = account.starting_nav
        self.lifecycle = start_position_lifecycle(
            symbol=symbol,
            config_metadata=metadata,
        )
        self.pending: _QueuedIntent | None = None
        self.intent_source_ids: set[str] = set()
        self.fills: list[TradeFill] = []
        self.trade_bars: list[OhlcvBar] = []
        self.funding_events: list[FundingEvent] = []
        self.position_size: InitialPositionSizeResult | None = None
        self.initial_stop_source_id: str | None = None
        self.exit_reason: str | None = None
        self.exit_reason_source_id: str | None = None
        self.settled_trade_gross = Decimal("0")
        self.trades: list[PaperTradeAccounting] = []
        self.equity_curve: list[EquityPoint] = []
        self.events: list[BacktestEvent] = []
        self.reason_codes: list[str] = []
        if cost_profile is not None:
            self._note("BACKTEST_COST_PROFILE_APPLIED")
        self.missed_entries = 0
        self.stopped_out = 0
        self.ledger_sequence = 0
        self.audit_sequence = 0

    def on_bar(self, bar: OhlcvBar) -> None:
        self._charge_funding(bar)
        self._resolve_stop(bar)
        self._resolve_pending(bar)
        self._record_equity(bar)
        if self.lifecycle.quantity > 0:
            self.trade_bars.append(bar)

    def queue(self, intent: BacktestIntent | None, bar: OhlcvBar) -> None:
        if intent is not None and not isinstance(intent, BacktestIntent):
            raise TypeError("strategy must return a BacktestIntent or None")
        if intent is None:
            return
        decision_at = _bar_available_at(bar)
        source_id = intent.source_id or (
            f"{intent.action.lower()}-{decision_at.isoformat()}"
        )
        if source_id in self.intent_source_ids:
            raise ValueError("intent source_id must be unique within a backtest run")
        self.intent_source_ids.add(source_id)
        if self.pending is not None:
            raise ValueError("strategy cannot queue a second intent while one is pending")
        if intent.action == ARM_ENTRY_ACTION and self.lifecycle.quantity > 0:
            self._refuse_intent(intent, source_id, decision_at, "POSITION_ALREADY_OPEN")
            return
        if intent.action != ARM_ENTRY_ACTION and self.lifecycle.quantity <= 0:
            self._refuse_intent(intent, source_id, decision_at, "POSITION_NOT_OPEN")
            return

        position_size = None
        tranche = None
        if intent.action == ARM_ENTRY_ACTION:
            position_size, tranche = self._prepare_entry(intent, bar)
            if position_size is None or tranche is None:
                self._note("BACKTEST_ENTRY_UNSIZED")
                self._event(
                    occurred_at=decision_at,
                    event_type="INTENT",
                    action=intent.action,
                    status=REFUSED,
                    source_id=source_id,
                    reason_codes=("ENTRY_UNSIZED",),
                    evidence={"intent": intent.as_record()},
                )
                return

        queued = _QueuedIntent(
            intent=intent,
            source_id=source_id,
            decision_bar_at=bar.timestamp,
            decision_at=decision_at,
            eligible_bar_at=next_eligible_bar_timestamp(decision_at, bar.timeframe),
            expected_state=self.lifecycle.state,
            expected_last_event_at=self.lifecycle.last_event_at,
            expected_quantity=self.lifecycle.quantity,
            position_size=position_size,
            initial_tranche=tranche,
        )
        self.pending = queued
        self._event(
            occurred_at=decision_at,
            event_type="INTENT",
            action=intent.action,
            status=QUEUED,
            source_id=source_id,
            reason_codes=("INTENT_QUEUED",),
            evidence={
                "decision_bar_at": bar.timestamp.isoformat(),
                "eligible_bar_at": queued.eligible_bar_at.isoformat(),
                "expected_state": queued.expected_state,
                "expected_last_event_at": _optional_time(queued.expected_last_event_at),
                "expected_quantity": str(queued.expected_quantity),
                "intent": intent.as_record(),
            },
        )

    def finalize(self, last_bar: OhlcvBar) -> None:
        if self.pending is not None:
            queued, self.pending = self.pending, None
            self._note("BACKTEST_INTENT_UNEXECUTED_END")
            self._event(
                occurred_at=_bar_available_at(last_bar),
                event_type="INTENT",
                action=queued.intent.action,
                status=UNEXECUTED,
                source_id=queued.source_id,
                reason_codes=("DATASET_ENDED_BEFORE_ELIGIBLE_BAR",),
                evidence={"intent": queued.intent.as_record()},
            )
        if self.lifecycle.quantity > 0:
            self._note("BACKTEST_POSITION_OPEN_AT_END")
        self._note("BACKTEST_COMPLETE")

    def context(self, bar: OhlcvBar, visible: tuple[OhlcvBar, ...]) -> BacktestContext:
        unrealized = self._unrealized(bar.close)
        account_view = replace(
            self.account,
            config_metadata=dict(self.account.config_metadata),
        )
        lifecycle_view = replace(
            self.lifecycle,
            config_metadata=dict(self.lifecycle.config_metadata),
        )
        return BacktestContext(
            as_of=_bar_available_at(bar),
            bar=bar,
            bars=visible,
            account=account_view,
            lifecycle=lifecycle_view,
            nav=self.account.nav(unrealized_pnl=unrealized),
            open_quantity=self.lifecycle.quantity,
            average_entry_price=self.lifecycle.average_entry_price,
            standing_stop=self.lifecycle.stop_price,
        )

    def _resolve_pending(self, bar: OhlcvBar) -> None:
        queued = self.pending
        if queued is None or bar.timestamp < queued.eligible_bar_at:
            return
        self.pending = None
        if bar.timestamp > queued.eligible_bar_at:
            self._note("BACKTEST_INTENT_EXPIRED")
            self._event(
                occurred_at=_bar_available_at(bar),
                event_type="INTENT",
                action=queued.intent.action,
                status=EXPIRED,
                source_id=queued.source_id,
                reason_codes=("FIRST_ELIGIBLE_BAR_MISSING",),
                evidence={"intent": queued.intent.as_record()},
            )
            return
        if self._intent_is_stale(queued):
            self._note("BACKTEST_INTENT_STALE")
            self._event(
                occurred_at=_bar_available_at(bar),
                event_type="INTENT",
                action=queued.intent.action,
                status=STALE,
                source_id=queued.source_id,
                reason_codes=("POSITION_STATE_CHANGED_BEFORE_EXECUTION",),
                evidence={"intent": queued.intent.as_record()},
            )
            return
        action = queued.intent.action
        if action == ARM_ENTRY_ACTION:
            self._execute_entry(queued, bar)
        elif action == ADD_ACTION:
            self._execute_add(queued, bar)
        elif action == TRIM_ACTION:
            self._execute_trim(queued, bar)
        elif action == TRAIL_ACTION:
            self._execute_trail(queued, bar)
        elif action == EXIT_ACTION:
            self._execute_exit(queued, bar)

    def _intent_is_stale(self, queued: _QueuedIntent) -> bool:
        return (
            self.lifecycle.state != queued.expected_state
            or self.lifecycle.last_event_at != queued.expected_last_event_at
            or self.lifecycle.quantity != queued.expected_quantity
        )

    def _resolve_stop(
        self,
        bar: OhlcvBar,
        *,
        entry_bracket_placed_at: datetime | None = None,
    ) -> None:
        if self.lifecycle.quantity <= 0 or self.lifecycle.stop_price is None:
            return
        execution = stop_execution_for_position(
            self.lifecycle,
            bar,
            costs=self.costs,
            execution_id=f"stop-{bar.timestamp.isoformat()}-{self.audit_sequence + 1}",
            entry_bracket_placed_at=entry_bracket_placed_at,
            config_metadata=self.metadata,
        )
        self._event(
            occurred_at=execution.resolved_at,
            event_type="STOP_EXECUTION",
            action=EXIT_ACTION if execution.filled else None,
            status=EXECUTED if execution.filled else RESTING,
            source_id=execution.intent.execution_id,
            reason_codes=execution.reason_codes,
            evidence=execution.as_record(),
        )
        if not execution.filled:
            return
        fill = self._trade_fill(execution)
        closed = apply_position_event(
            self.lifecycle,
            event=EXIT,
            event_time=execution.resolved_at,
            quantity=execution.filled_quantity,
            price=execution.average_fill_price,
            reason_codes=("STRUCTURAL_STOP",) + execution.reason_codes,
            source_feature_id=execution.feature_id,
            source_record_id=execution.intent.execution_id,
        )
        if not closed.accepted:
            raise RuntimeError("BTC-150 refused a filled authoritative stop execution")
        self.lifecycle = closed
        self.fills.append(fill)
        self.account = self.account.charge_fee(execution.notional)
        self.stopped_out += 1
        self.exit_reason = "STRUCTURAL_STOP"
        self.exit_reason_source_id = execution.intent.execution_id
        self._note("BACKTEST_STOPPED_OUT")
        self._close_trade(execution.resolved_at)

    def _prepare_entry(
        self,
        intent: BacktestIntent,
        bar: OhlcvBar,
    ) -> tuple[InitialPositionSizeResult | None, TrancheSizingResult | None]:
        stop = intent.initial_stop
        if not isinstance(stop, InitialStopResult):
            raise TypeError("initial_stop must be an InitialStopResult")
        stop.as_record()
        if not stop.complete or stop.stop_price is None or stop.entry_price is None:
            return None, None
        if stop.direction != intent.direction:
            raise ValueError("initial_stop direction must match entry direction")
        if stop.config_metadata != self.metadata:
            raise ValueError("initial_stop config_metadata must match the run")
        if not intent.entry_zone_lower <= stop.entry_price <= intent.entry_zone_upper:
            raise ValueError("initial_stop entry_price must lie inside the entry zone")
        budget = calculate_risk_budget(
            entry_conviction=intent.entry_conviction,
            nav=self.account.nav(unrealized_pnl=self._unrealized(bar.close)),
            config=self.config,
        )
        size = initial_position_size_for_trade(
            budget,
            stop,
            config_metadata=self.metadata,
        )
        if not size.complete or size.position_notional is None:
            return None, None
        tranche = calculate_tranche_size(
            tranche_number=1,
            final_position_notional=size.position_notional,
            entry_price=stop.entry_price,
            config=self.config,
            config_metadata=self.metadata,
        )
        if not tranche.complete or tranche.allocation.quantity is None:
            return None, None
        return size, tranche

    def _execute_entry(self, queued: _QueuedIntent, bar: OhlcvBar) -> None:
        intent = queued.intent
        if intent.direction == "short" and not self.config.backtest.allow_short_trades:
            self._note("BACKTEST_SHORTS_NOT_PERMITTED")
            return
        if queued.initial_tranche is None or intent.initial_stop is None:
            raise RuntimeError("queued entry lost its authoritative sizing evidence")
        quantity = queued.initial_tranche.allocation.quantity
        if quantity is None:
            raise RuntimeError("queued entry has no requested quantity")
        execution = simulate_next_bar_entry(
            EntryExecutionIntent(
                execution_id=queued.source_id,
                recommendation_id=None,
                symbol=self.symbol,
                direction=intent.direction,
                decision_at=queued.decision_at,
                timeframe=bar.timeframe,
                entry_zone_lower=intent.entry_zone_lower,
                entry_zone_upper=intent.entry_zone_upper,
                entry_zone_available_at=queued.decision_at,
                requested_quantity=quantity,
                config_metadata=self.metadata,
            ),
            bar,
            costs=self.costs,
        )
        self._event(
            occurred_at=execution.resolved_at,
            event_type="ENTRY_EXECUTION",
            action=ARM_ENTRY_ACTION,
            status=MISSED if execution.missed else EXECUTED,
            source_id=queued.source_id,
            reason_codes=execution.reason_codes,
            evidence=execution.as_record(),
        )
        if execution.missed:
            self.missed_entries += 1
            self._note("BACKTEST_ENTRY_MISSED")
            return
        lifecycle = start_position_lifecycle(
            symbol=self.symbol,
            direction=intent.direction,
            state=PENDING_ENTRY,
            config_metadata=self.metadata,
        )
        entered = apply_position_event(
            lifecycle,
            event=ENTER,
            event_time=execution.resolved_at,
            quantity=execution.filled_quantity,
            price=execution.average_fill_price,
            stop_price=intent.initial_stop.stop_price,
            reason_codes=execution.reason_codes + intent.initial_stop.reason_codes,
            source_feature_id=execution.feature_id,
            source_record_id=execution.intent.execution_id,
        )
        if not entered.accepted:
            self._note("BACKTEST_ENTRY_REFUSED")
            self._event(
                occurred_at=execution.resolved_at,
                event_type="LEDGER_TRANSITION",
                action=ENTER,
                status=REFUSED,
                source_id=queued.source_id,
                reason_codes=entered.reason_codes,
                evidence=entered.as_record(),
            )
            return
        self.lifecycle = entered
        self.position_size = queued.position_size
        self.initial_stop_source_id = _source_record_id(intent.initial_stop.as_record())
        self.exit_reason = None
        self.exit_reason_source_id = None
        self.settled_trade_gross = Decimal("0")
        self.fills = [self._trade_fill(execution)]
        self.trade_bars = []
        self.funding_events = []
        self.account = self.account.charge_fee(execution.notional)
        self._note("BACKTEST_ENTRY_FILLED")
        self._resolve_stop(bar, entry_bracket_placed_at=queued.decision_at)

    def _execute_add(self, queued: _QueuedIntent, bar: OhlcvBar) -> None:
        if self.position_size is None:
            raise RuntimeError("open lifecycle has no BTC-145 position size")
        tranche = next_tranche_for_position(
            self.lifecycle,
            self.position_size,
            entry_price=bar.open,
            config=self.config,
            config_metadata=self.metadata,
        )
        execution = simulate_add_execution(
            AddExecutionIntent(
                execution_id=queued.source_id,
                position_id=None,
                recommendation_id=None,
                symbol=self.symbol,
                direction=self.lifecycle.direction,
                timeframe=bar.timeframe,
                decision_at=queued.decision_at,
                average_entry_price=self.lifecycle.average_entry_price,
                config_metadata=self.metadata,
            ),
            bar,
            requirements=queued.intent.requirements,
            tranche=tranche,
            costs=self.costs,
        )
        self._event(
            occurred_at=execution.resolved_at,
            event_type="ADD_EXECUTION",
            action=ADD_ACTION,
            status=EXECUTED if execution.filled else REFUSED,
            source_id=queued.source_id,
            reason_codes=execution.reason_codes,
            evidence=execution.as_record(),
        )
        if not execution.filled:
            self._note("BACKTEST_ADD_REFUSED")
            return
        added = apply_position_event(
            self.lifecycle,
            event=ADD,
            event_time=execution.resolved_at,
            quantity=execution.filled_quantity,
            price=execution.average_fill_price,
            reason_codes=execution.reason_codes,
            source_feature_id=execution.feature_id,
            source_record_id=execution.intent.execution_id,
        )
        if not added.accepted:
            self._note("BACKTEST_ADD_REFUSED")
            self._event(
                occurred_at=execution.resolved_at,
                event_type="LEDGER_TRANSITION",
                action=ADD,
                status=REFUSED,
                source_id=queued.source_id,
                reason_codes=added.reason_codes,
                evidence=added.as_record(),
            )
            return
        self.lifecycle = added
        self.fills.append(self._trade_fill(execution))
        self.account = self.account.charge_fee(execution.notional)
        self._note("BACKTEST_ADDED")

    def _execute_trim(self, queued: _QueuedIntent, bar: OhlcvBar) -> None:
        intent = TrimExecutionIntent(
            execution_id=queued.source_id,
            position_id=None,
            recommendation_id=None,
            symbol=self.symbol,
            direction=self.lifecycle.direction,
            timeframe=bar.timeframe,
            decision_at=queued.decision_at,
            average_entry_price=self.lifecycle.average_entry_price,
            open_quantity=self.lifecycle.quantity,
            config_metadata=self.metadata,
        )
        if queued.intent.trim_fraction is not None:
            intent = replace(intent, trim_fraction=queued.intent.trim_fraction)
        execution = simulate_trim_execution(
            intent,
            bar,
            signal=queued.intent.trim_signal,
            costs=self.costs,
        )
        self._event(
            occurred_at=execution.resolved_at,
            event_type="TRIM_EXECUTION",
            action=TRIM_ACTION,
            status=EXECUTED if execution.filled else REFUSED,
            source_id=queued.source_id,
            reason_codes=execution.reason_codes,
            evidence=execution.as_record(),
        )
        if not execution.filled:
            self._note("BACKTEST_TRIM_REFUSED")
            return
        trimmed = apply_position_event(
            self.lifecycle,
            event=TRIM,
            event_time=execution.resolved_at,
            quantity=execution.filled_quantity,
            price=execution.average_fill_price,
            reason_codes=execution.reason_codes,
            source_feature_id=execution.feature_id,
            source_record_id=execution.intent.execution_id,
        )
        if not trimmed.accepted:
            self._note("BACKTEST_TRIM_REFUSED")
            self._event(
                occurred_at=execution.resolved_at,
                event_type="LEDGER_TRANSITION",
                action=TRIM,
                status=REFUSED,
                source_id=queued.source_id,
                reason_codes=trimmed.reason_codes,
                evidence=trimmed.as_record(),
            )
            return
        self.lifecycle = trimmed
        self.fills.append(self._trade_fill(execution))
        self.account = self.account.charge_fee(execution.notional)
        self._settle_incremental_gross(execution.resolved_at)
        self._note("BACKTEST_TRIMMED")

    def _execute_trail(self, queued: _QueuedIntent, bar: OhlcvBar) -> None:
        result = queued.intent.trailing_stop
        if not isinstance(result, TrailingStopResult):
            raise TypeError("trailing_stop must be a TrailingStopResult")
        result.as_record()
        if result.evaluated_at != queued.decision_at:
            raise ValueError("trailing_stop must be evaluated at the queued decision time")
        if result.config_metadata != self.metadata:
            raise ValueError("trailing_stop config_metadata must match the run")
        if (
            result.advanced
            and result.structure_id in used_trailing_structure_ids(self.lifecycle)
        ):
            self._note("BACKTEST_TRAIL_HELD")
            self._event(
                occurred_at=_bar_available_at(bar),
                event_type="TRAILING_STOP",
                action=TRAIL_ACTION,
                status=REFUSED,
                source_id=queued.source_id,
                reason_codes=("TRAILING_STOP_STRUCTURE_ALREADY_USED",),
                evidence=result.as_record(),
            )
            return
        moved = apply_trailing_stop(
            self.lifecycle,
            result,
            event_time=_bar_available_at(bar),
        )
        self._event(
            occurred_at=_bar_available_at(bar),
            event_type="TRAILING_STOP",
            action=TRAIL_ACTION,
            status=APPLIED if moved is not self.lifecycle else REFUSED,
            source_id=queued.source_id,
            reason_codes=result.reason_codes,
            evidence=result.as_record(),
        )
        if moved is self.lifecycle:
            self._note("BACKTEST_TRAIL_HELD")
            return
        if not moved.accepted:
            raise RuntimeError("BTC-150 refused an advanced BTC-156 stop")
        self.lifecycle = moved
        self._note("BACKTEST_STOP_TRAILED")

    def _execute_exit(self, queued: _QueuedIntent, bar: OhlcvBar) -> None:
        intent = queued.intent
        execution = simulate_exit_execution(
            ExitExecutionIntent(
                execution_id=queued.source_id,
                position_id=None,
                recommendation_id=None,
                symbol=self.symbol,
                direction=self.lifecycle.direction,
                timeframe=bar.timeframe,
                decision_at=queued.decision_at,
                open_quantity=self.lifecycle.quantity,
                exit_reason=intent.exit_reason,
                exit_reason_source_id=intent.source_id or queued.source_id,
                config_metadata=self.metadata,
            ),
            bar,
            costs=self.costs,
        )
        fill = self._trade_fill(execution)
        closed = apply_position_event(
            self.lifecycle,
            event=EXIT,
            event_time=execution.resolved_at,
            quantity=execution.filled_quantity,
            price=execution.average_fill_price,
            reason_codes=(intent.exit_reason,) + execution.reason_codes,
            source_feature_id=execution.feature_id,
            source_record_id=execution.intent.execution_id,
        )
        if not closed.accepted:
            raise RuntimeError("BTC-150 refused a filled authoritative exit")
        self.lifecycle = closed
        self.fills.append(fill)
        self.account = self.account.charge_fee(execution.notional)
        self.exit_reason = intent.exit_reason
        self.exit_reason_source_id = execution.intent.exit_reason_source_id
        self._event(
            occurred_at=execution.resolved_at,
            event_type="EXIT_EXECUTION",
            action=EXIT_ACTION,
            status=EXECUTED,
            source_id=queued.source_id,
            reason_codes=execution.reason_codes,
            evidence=execution.as_record(),
        )
        self._note("BACKTEST_EXITED")
        self._close_trade(execution.resolved_at)

    def _charge_funding(self, bar: OhlcvBar) -> None:
        quantity = self.lifecycle.quantity
        if quantity <= 0 or self.costs.funding_cost_bps_per_day == 0:
            return
        days = _bar_days(bar)
        rate = self.costs.funding_rate(days=days)
        self.ledger_sequence += 1
        effective_at = min(
            next_bar_timestamp(bar.timestamp, bar.timeframe),
            _bar_available_at(bar),
        ) - timedelta(microseconds=1)
        event = funding_event_from_rate(
            sequence=self.ledger_sequence,
            event_id=f"funding-{bar.timestamp.isoformat()}",
            effective_at=effective_at,
            rate=rate,
            mark_price=bar.close,
            position_quantity=quantity,
            direction=self.lifecycle.direction,
        )
        self.funding_events.append(event)
        self.account = self.account.apply_funding_cost(event.funding_cost)
        self._event(
            occurred_at=_bar_available_at(bar),
            event_type="FUNDING",
            action=None,
            status=APPLIED,
            source_id=event.event_id,
            reason_codes=("FUNDING_APPLIED_BEFORE_BAR_RESOLUTION",),
            evidence={
                **event.as_record(),
                "funding_policy_version": BACKTEST_FUNDING_POLICY_VERSION,
                "observed_at": _bar_available_at(bar).isoformat(),
            },
        )

    def _trade_fill(self, execution: Any) -> TradeFill:
        self.ledger_sequence += 1
        return trade_fill_from_execution(execution, sequence=self.ledger_sequence)

    def _accounting(self, as_of: datetime) -> PaperTradeAccounting:
        if self.initial_stop_source_id is None:
            raise RuntimeError("open trade has no initial-stop provenance")
        return calculate_trade_accounting_for_lifecycle(
            self.lifecycle,
            tuple(self.fills),
            funding_events=tuple(self.funding_events),
            excursion_bars=tuple(self.trade_bars) or None,
            as_of=as_of,
            initial_stop_source_id=self.initial_stop_source_id,
            exit_reason=self.exit_reason,
            exit_reason_source_id=self.exit_reason_source_id,
        )

    def _settle_incremental_gross(self, as_of: datetime) -> PaperTradeAccounting:
        accounting = self._accounting(as_of)
        increment = accounting.gross_pnl - self.settled_trade_gross
        if increment != 0:
            self.account = self.account.settle_realized_pnl(increment)
        self.settled_trade_gross = accounting.gross_pnl
        return accounting

    def _close_trade(self, as_of: datetime) -> None:
        accounting = self._settle_incremental_gross(as_of)
        if not accounting.closed:
            raise RuntimeError("terminal lifecycle produced open BTC-165 accounting")
        self.trades.append(accounting)
        self.fills = []
        self.trade_bars = []
        self.funding_events = []
        self.position_size = None
        self.initial_stop_source_id = None
        self.exit_reason = None
        self.exit_reason_source_id = None
        self.settled_trade_gross = Decimal("0")

    def open_trade_snapshot(self, as_of: datetime) -> PaperTradeAccounting | None:
        if self.lifecycle.quantity <= 0 or not self.fills:
            return None
        return self._accounting(as_of)

    def _record_equity(self, bar: OhlcvBar) -> None:
        unrealized = self._unrealized(bar.close)
        nav = self.account.nav(unrealized_pnl=unrealized)
        risk_amount = None
        risk_fraction = None
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
                as_of=_bar_available_at(bar),
                bar_timestamp=bar.timestamp,
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
        value = quant_unrealized_pnl(
            float(average),
            float(price),
            float(quantity),
            side=self.lifecycle.direction,
        )
        return Decimal(str(value))

    def _refuse_intent(
        self,
        intent: BacktestIntent,
        source_id: str,
        as_of: datetime,
        reason: str,
    ) -> None:
        self._note("BACKTEST_INTENT_REFUSED")
        self._event(
            occurred_at=as_of,
            event_type="INTENT",
            action=intent.action,
            status=REFUSED,
            source_id=source_id,
            reason_codes=(reason,),
            evidence={"intent": intent.as_record()},
        )

    def _event(
        self,
        *,
        occurred_at: datetime,
        event_type: str,
        action: str | None,
        status: str,
        source_id: str,
        reason_codes: tuple[str, ...],
        evidence: Mapping[str, Any],
    ) -> None:
        self.audit_sequence += 1
        self.events.append(
            BacktestEvent(
                sequence=self.audit_sequence,
                occurred_at=require_utc_datetime(occurred_at, "occurred_at"),
                event_type=event_type,
                action=action,
                status=status,
                source_id=source_id,
                reason_codes=tuple(dict.fromkeys(reason_codes)),
                evidence=_json_copy(dict(evidence)),
            )
        )

    def _note(self, code: str) -> None:
        if code not in BACKTEST_REASON_CODES:
            raise ValueError(f"undeclared backtest reason code: {code}")
        if code not in self.reason_codes:
            self.reason_codes.append(code)


_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _bar_available_at(bar: OhlcvBar) -> datetime:
    return max(next_bar_timestamp(bar.timestamp, bar.timeframe), bar.ingested_at)


def _bar_days(bar: OhlcvBar) -> Decimal:
    seconds = Decimal(
        str((next_bar_timestamp(bar.timestamp, bar.timeframe) - bar.timestamp).total_seconds())
    )
    return seconds / Decimal("86400")


def _validate_bars(
    bars: Sequence[OhlcvBar],
    *,
    symbol: str,
) -> tuple[OhlcvBar, ...]:
    ordered = tuple(bars)
    timeframe = None
    source_identity = None
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
        identity = (bar.exchange, bar.provider)
        if source_identity is None:
            source_identity = identity
        elif identity != source_identity:
            raise ValueError("historical provider splicing requires a separately versioned dataset")
        if next_eligible_bar_timestamp(bar.timestamp, bar.timeframe) != bar.timestamp:
            raise ValueError("bar timestamp must lie on a canonical timeframe boundary")
        open_price = _positive_decimal(bar.open, "bar.open")
        high = _positive_decimal(bar.high, "bar.high")
        low = _positive_decimal(bar.low, "bar.low")
        close = _positive_decimal(bar.close, "bar.close")
        _non_negative_decimal(bar.volume, "bar.volume")
        if high < max(open_price, close) or low > min(open_price, close) or high < low:
            raise ValueError("bar has impossible OHLC geometry")
    for previous, current in zip(ordered, ordered[1:]):
        if current.timestamp <= previous.timestamp:
            raise ValueError("bars must be in strictly increasing time order")
        if _bar_available_at(current) < _bar_available_at(previous):
            raise ValueError("bar availability must be in non-decreasing time order")
    return ordered


def _resolve_account_and_costs(
    *,
    ordered: tuple[OhlcvBar, ...],
    symbol: str,
    config: StrategyConfig,
    metadata: dict[str, str],
    costs: ExecutionCosts | None,
    profile: CostProfile | None,
    account: PaperAccount | None,
    starting_nav: Any | None,
) -> tuple[ExecutionCosts, PaperAccount]:
    configured = execution_costs_from_config(config)
    if costs is not None and not isinstance(costs, ExecutionCosts):
        raise TypeError("costs must be an ExecutionCosts")
    if profile is not None:
        if costs is not None:
            # Both would be a silent claim that the run priced the named rung.
            raise ValueError("costs and cost_profile are mutually exclusive")
        costs = profile.costs
    if account is not None and not isinstance(account, PaperAccount):
        raise TypeError("account must be a PaperAccount")
    if account is not None:
        if starting_nav is not None:
            raise ValueError("starting_nav cannot be supplied with account")
        account.as_record()
        if not account.is_active:
            raise ValueError("account must be active")
        if account.config_metadata != metadata:
            raise ValueError("account config_metadata must match the backtest config")
        if (
            account.cash != account.starting_nav
            or account.reserved_cash != 0
            or account.realized_pnl != 0
            or account.fees_paid != 0
            or account.funding_paid != 0
        ):
            raise ValueError("account must be pristine because each run starts a fresh lifecycle")
        if ordered and account.created_at > ordered[0].timestamp:
            raise ValueError("account cannot be created after the backtest starts")
        effective = costs if costs is not None else account.costs
        if account.costs != effective:
            raise ValueError("account and execution costs must be identical")
        effective.as_record()
        return effective, account
    effective = costs if costs is not None else configured
    effective.as_record()
    created_at = ordered[0].timestamp if ordered else _EPOCH
    return effective, open_paper_account(
        account_name=f"backtest-{symbol}",
        created_at=created_at,
        starting_nav=starting_nav,
        costs=effective,
        config=config,
    )


def _resolve_cost_profile(
    profile: str | None,
    config: StrategyConfig,
) -> CostProfile | None:
    if profile is None:
        return None
    if profile not in COST_PROFILES:
        raise ValueError(f"cost_profile must be one of {COST_PROFILES}")
    return resolve_cost_profile(profile, config=config)


def _strategy_identifier(
    strategy: Callable[[BacktestContext], BacktestIntent | None],
    explicit: str | None,
) -> str:
    if explicit is not None:
        if not isinstance(explicit, str) or not explicit.strip():
            raise ValueError("strategy_id must not be empty")
        return explicit
    module = getattr(strategy, "__module__", type(strategy).__module__)
    qualname = getattr(strategy, "__qualname__", type(strategy).__qualname__)
    code = getattr(strategy, "__code__", None)
    fingerprint = hashlib.sha256(
        marshal.dumps(code) if code is not None else f"{module}:{qualname}".encode()
    ).hexdigest()[:16]
    return f"{module}:{qualname}:{fingerprint}"


def _empty_result(state: _EngineState) -> BacktestResult:
    reasons = tuple(state.reason_codes) + ("BACKTEST_NO_BARS",)
    input_digest = _digest([])
    run_id = _run_id(
        strategy_id=state.strategy_id,
        config_metadata=state.metadata,
        costs=state.costs,
        cost_profile=state.cost_profile,
        starting_nav=state.starting_nav,
        input_digest=input_digest,
    )
    result = BacktestResult(
        feature_id=BACKTEST_ENGINE_FEATURE_ID,
        policy_version=BACKTEST_ENGINE_POLICY_VERSION,
        funding_policy_version=BACKTEST_FUNDING_POLICY_VERSION,
        end_policy_version=BACKTEST_END_POLICY_VERSION,
        run_id=run_id,
        evidence_digest="",
        input_digest=input_digest,
        strategy_id=state.strategy_id,
        symbol=state.symbol,
        started_at=None,
        ended_at=None,
        bar_count=0,
        input_bars=(),
        effective_costs=state.costs,
        cost_profile=state.cost_profile,
        account=state.account,
        final_lifecycle=state.lifecycle,
        starting_nav=state.starting_nav,
        ending_nav=state.account.nav(),
        trades=(),
        equity_curve=(),
        events=(),
        missed_entries=0,
        stopped_out=0,
        config_metadata=dict(state.metadata),
        reason_codes=reasons,
    )
    _validate_result(result)
    return replace(result, evidence_digest=_digest(_result_payload(result)))


def _result(state: _EngineState, bars: tuple[OhlcvBar, ...]) -> BacktestResult:
    open_trade = state.open_trade_snapshot(_bar_available_at(bars[-1]))
    trades = tuple(state.trades) + ((open_trade,) if open_trade is not None else ())
    bar_records = [_bar_record(item) for item in bars]
    input_digest = _digest(bar_records)
    run_id = _run_id(
        strategy_id=state.strategy_id,
        config_metadata=state.metadata,
        costs=state.costs,
        cost_profile=state.cost_profile,
        starting_nav=state.starting_nav,
        input_digest=input_digest,
    )
    result = BacktestResult(
        feature_id=BACKTEST_ENGINE_FEATURE_ID,
        policy_version=BACKTEST_ENGINE_POLICY_VERSION,
        funding_policy_version=BACKTEST_FUNDING_POLICY_VERSION,
        end_policy_version=BACKTEST_END_POLICY_VERSION,
        run_id=run_id,
        evidence_digest="",
        input_digest=input_digest,
        strategy_id=state.strategy_id,
        symbol=state.symbol,
        started_at=bars[0].timestamp,
        ended_at=bars[-1].timestamp,
        bar_count=len(bars),
        input_bars=bars,
        effective_costs=state.costs,
        cost_profile=state.cost_profile,
        account=state.account,
        final_lifecycle=state.lifecycle,
        starting_nav=state.starting_nav,
        ending_nav=state.equity_curve[-1].nav,
        trades=trades,
        equity_curve=tuple(state.equity_curve),
        events=tuple(state.events),
        missed_entries=state.missed_entries,
        stopped_out=state.stopped_out,
        config_metadata=dict(state.metadata),
        reason_codes=tuple(state.reason_codes),
    )
    _validate_result(result)
    return replace(result, evidence_digest=_digest(_result_payload(result)))


def _run_id(
    *,
    strategy_id: str,
    config_metadata: Mapping[str, str],
    costs: ExecutionCosts,
    cost_profile: CostProfile | None,
    starting_nav: Decimal,
    input_digest: str,
) -> str:
    return _digest(
        {
            "policy": BACKTEST_ENGINE_POLICY_VERSION,
            "funding_policy": BACKTEST_FUNDING_POLICY_VERSION,
            "end_policy": BACKTEST_END_POLICY_VERSION,
            "cost_profile": cost_profile.profile if cost_profile is not None else None,
            "strategy_id": strategy_id,
            "config": dict(config_metadata),
            "costs": costs.as_record(),
            "starting_nav": str(starting_nav),
            "input_digest": input_digest,
        }
    )


def _validate_result(result: BacktestResult) -> None:
    if result.funding_policy_version != BACKTEST_FUNDING_POLICY_VERSION:
        raise ValueError(f"funding_policy_version must be {BACKTEST_FUNDING_POLICY_VERSION}")
    if result.end_policy_version != BACKTEST_END_POLICY_VERSION:
        raise ValueError(f"end_policy_version must be {BACKTEST_END_POLICY_VERSION}")
    if result.bar_count != len(result.input_bars):
        raise ValueError("bar_count must equal input_bars length")
    if _validate_bars(result.input_bars, symbol=result.symbol) != result.input_bars:
        raise ValueError("input_bars must retain canonical order")
    if result.input_digest != _digest([_bar_record(item) for item in result.input_bars]):
        raise ValueError("input bars do not match input_digest")
    expected_run_id = _run_id(
        strategy_id=result.strategy_id,
        config_metadata=result.config_metadata,
        costs=result.effective_costs,
        cost_profile=result.cost_profile,
        starting_nav=result.starting_nav,
        input_digest=result.input_digest,
    )
    if result.run_id != expected_run_id:
        raise ValueError("run inputs do not match run_id")
    if result.cost_profile is not None:
        result.cost_profile.as_record()
        if result.cost_profile.costs != result.effective_costs:
            raise ValueError("cost_profile costs must equal effective_costs")
        if result.cost_profile.config_metadata != result.config_metadata:
            raise ValueError("cost_profile config_metadata must match result")
    if result.account.costs != result.effective_costs:
        raise ValueError("account costs must equal effective_costs")
    if result.account.config_metadata != result.config_metadata:
        raise ValueError("account config_metadata must match result")
    if result.final_lifecycle.config_metadata != result.config_metadata:
        raise ValueError("lifecycle config_metadata must match result")
    if any(trade.config_metadata != result.config_metadata for trade in result.trades):
        raise ValueError("trade config_metadata must match result")
    if tuple(event.sequence for event in result.events) != tuple(
        range(1, len(result.events) + 1)
    ):
        raise ValueError("event sequences must be contiguous")
    if any(
        current.occurred_at < previous.occurred_at
        for previous, current in zip(result.events, result.events[1:])
    ):
        raise ValueError("events must be in deterministic chronological order")
    if any(code not in BACKTEST_REASON_CODES for code in result.reason_codes):
        raise ValueError("result contains an undeclared reason code")
    if result.bar_count == 0:
        if result.equity_curve or result.trades or result.events:
            raise ValueError("an empty run cannot contain economic evidence")
        if result.started_at is not None or result.ended_at is not None:
            raise ValueError("an empty run cannot have market timestamps")
        expected_ending = result.account.nav()
    else:
        if len(result.equity_curve) != result.bar_count:
            raise ValueError("equity_curve must contain one point per bar")
        if result.started_at != result.input_bars[0].timestamp:
            raise ValueError("started_at must identify the first input bar")
        if result.ended_at != result.input_bars[-1].timestamp:
            raise ValueError("ended_at must identify the last input bar")
        for bar, point in zip(result.input_bars, result.equity_curve):
            if (
                point.bar_timestamp != bar.timestamp
                or point.as_of != _bar_available_at(bar)
                or point.close != bar.close
                or point.nav != point.cash + point.unrealized_pnl
            ):
                raise ValueError("equity points must reconcile with their source bars")
        expected_ending = result.equity_curve[-1].nav
    if result.ending_nav != expected_ending:
        raise ValueError("ending_nav does not match final marked equity")
    if result.starting_nav != result.account.starting_nav:
        raise ValueError("starting_nav does not match account")
    fees = sum((trade.fees for trade in result.trades), Decimal("0"))
    funding = sum((trade.funding for trade in result.trades), Decimal("0"))
    realized = sum((trade.gross_pnl for trade in result.trades), Decimal("0"))
    if fees != result.account.fees_paid:
        raise ValueError("account fees do not reconcile with trade evidence")
    if funding != result.account.funding_paid:
        raise ValueError("account funding does not reconcile with trade evidence")
    if abs(realized - result.account.realized_pnl) > BACKTEST_RECONCILIATION_TOLERANCE:
        raise ValueError("account realized P&L does not reconcile with trade evidence")
    expected_cash = result.starting_nav + realized - fees - funding
    if abs(result.account.cash - expected_cash) > BACKTEST_RECONCILIATION_TOLERANCE:
        raise ValueError("account cash does not reconcile with replayed economics")
    open_trades = tuple(trade for trade in result.trades if not trade.closed)
    if len(open_trades) > 1:
        raise ValueError("Phase 1 supports at most one open BTC trade")
    if (result.final_lifecycle.quantity > 0) != bool(open_trades):
        raise ValueError("open-trade evidence must match the final lifecycle")
    if open_trades:
        accounted_quantity = sum(
            (
                fill.quantity if fill.opening else -fill.quantity
                for fill in open_trades[0].fills
            ),
            Decimal("0"),
        )
        if accounted_quantity != result.final_lifecycle.quantity:
            raise ValueError("open-trade quantity must match the final lifecycle")
    missed = sum(
        event.event_type == "ENTRY_EXECUTION" and event.status == MISSED
        for event in result.events
    )
    stopped = sum(
        event.event_type == "STOP_EXECUTION" and event.status == EXECUTED
        for event in result.events
    )
    if result.missed_entries != missed or result.stopped_out != stopped:
        raise ValueError("summary counters must reconcile with event evidence")
    unrealized = result.equity_curve[-1].unrealized_pnl if result.equity_curve else Decimal("0")
    expected_total = result.net_pnl + (unrealized if open_trades else Decimal("0"))
    if abs(result.total_pnl - expected_total) > BACKTEST_RECONCILIATION_TOLERANCE:
        raise ValueError("NAV does not reconcile with realized and unrealized trade economics")


def _result_payload(result: BacktestResult) -> dict[str, Any]:
    return {
        "feature_id": result.feature_id,
        "policy_version": result.policy_version,
        "funding_policy_version": result.funding_policy_version,
        "nav_policy_version": BACKTEST_NAV_POLICY_VERSION,
        "end_policy_version": result.end_policy_version,
        "run_id": result.run_id,
        "input_digest": result.input_digest,
        "strategy_id": result.strategy_id,
        "symbol": result.symbol,
        "started_at": _optional_time(result.started_at),
        "ended_at": _optional_time(result.ended_at),
        "bar_count": result.bar_count,
        "input_bars": [_bar_record(item) for item in result.input_bars],
        "effective_costs": result.effective_costs.as_record(),
        "cost_profile": (
            result.cost_profile.as_record()
            if result.cost_profile is not None
            else None
        ),
        "starting_nav": str(result.starting_nav),
        "ending_nav": str(result.ending_nav),
        "net_pnl": str(result.net_pnl),
        "total_pnl": str(result.total_pnl),
        "trade_count": len(result.trades),
        "trades": [trade.as_record() for trade in result.trades],
        "equity_curve": [point.as_record() for point in result.equity_curve],
        "events": [event.as_record() for event in result.events],
        "missed_entries": result.missed_entries,
        "stopped_out": result.stopped_out,
        "account": result.account.as_record(),
        "final_lifecycle": result.final_lifecycle.as_record(),
        "config_metadata": dict(result.config_metadata),
        "reason_codes": list(result.reason_codes),
    }


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


def _bar_from_record(source: Mapping[str, Any]) -> OhlcvBar:
    return OhlcvBar(
        timestamp=_utc(source.get("timestamp"), "bar.timestamp"),
        exchange=_string(source.get("exchange"), "bar.exchange"),
        symbol=_string(source.get("symbol"), "bar.symbol"),
        timeframe=_string(source.get("timeframe"), "bar.timeframe"),
        open=_positive_decimal(source.get("open"), "bar.open"),
        high=_positive_decimal(source.get("high"), "bar.high"),
        low=_positive_decimal(source.get("low"), "bar.low"),
        close=_positive_decimal(source.get("close"), "bar.close"),
        volume=_non_negative_decimal(source.get("volume"), "bar.volume"),
        provider=_string(source.get("provider"), "bar.provider"),
        ingested_at=_utc(source.get("ingested_at"), "bar.ingested_at"),
    )


def _costs_from_record(source: Mapping[str, Any]) -> ExecutionCosts:
    costs = ExecutionCosts(
        policy_version=_string(source.get("policy_version"), "costs.policy_version"),
        fee_bps=_non_negative_decimal(source.get("fee_bps"), "costs.fee_bps"),
        slippage_bps=_non_negative_decimal(
            source.get("slippage_bps"), "costs.slippage_bps"
        ),
        funding_cost_bps_per_day=_non_negative_decimal(
            source.get("funding_cost_bps_per_day"),
            "costs.funding_cost_bps_per_day",
        ),
    )
    costs.as_record()
    return costs


def _equity_from_record(source: Mapping[str, Any]) -> EquityPoint:
    if source.get("nav_policy_version") != BACKTEST_NAV_POLICY_VERSION:
        raise ValueError(f"nav_policy_version must be {BACKTEST_NAV_POLICY_VERSION}")
    point = EquityPoint(
        as_of=_utc(source.get("as_of"), "equity.as_of"),
        bar_timestamp=_utc(
            source.get("bar_timestamp"), "equity.bar_timestamp"
        ),
        close=_positive_decimal(source.get("close"), "equity.close"),
        cash=_decimal(source.get("cash"), "equity.cash"),
        unrealized_pnl=_decimal(
            source.get("unrealized_pnl"), "equity.unrealized_pnl"
        ),
        nav=_decimal(source.get("nav"), "equity.nav"),
        open_quantity=_non_negative_decimal(
            source.get("open_quantity"), "equity.open_quantity"
        ),
        risk_at_stop=_optional_decimal(
            source.get("risk_at_stop"), "equity.risk_at_stop"
        ),
        risk_fraction_nav=_optional_decimal(
            source.get("risk_fraction_nav"), "equity.risk_fraction_nav"
        ),
    )
    if point.nav != point.cash + point.unrealized_pnl:
        raise ValueError("equity NAV must equal cash plus unrealized P&L")
    return point


def _event_from_record(source: Mapping[str, Any]) -> BacktestEvent:
    return BacktestEvent(
        sequence=_positive_integer(source.get("sequence"), "event.sequence"),
        occurred_at=_utc(source.get("occurred_at"), "event.occurred_at"),
        event_type=_string(source.get("event_type"), "event.event_type"),
        action=(
            _string(source.get("action"), "event.action")
            if source.get("action") is not None
            else None
        ),
        status=_string(source.get("status"), "event.status"),
        source_id=_string(source.get("source_id"), "event.source_id"),
        reason_codes=_string_tuple(source.get("reason_codes"), "event.reason_codes"),
        evidence=_mapping(source.get("evidence"), "event.evidence"),
    )


def _source_record_id(record: Mapping[str, Any]) -> str:
    return f"source-{_digest(record)[:24]}"


def _upstream_record(value: Any | None) -> dict[str, Any] | None:
    if value is None:
        return None
    serializer = getattr(value, "as_record", None)
    if not callable(serializer):
        raise TypeError("upstream intent evidence must expose as_record()")
    record = serializer()
    if not isinstance(record, Mapping):
        raise TypeError("upstream as_record() must return a mapping")
    return _json_copy(dict(record))


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    return dict(value)


def _record_sequence(value: Any, name: str) -> tuple[Any, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError(f"{name} must be a sequence")
    return tuple(value)


def _string_mapping(value: Any, name: str) -> dict[str, str]:
    source = _mapping(value, name)
    if any(not isinstance(key, str) or not isinstance(item, str) for key, item in source.items()):
        raise TypeError(f"{name} keys and values must be strings")
    return source


def _string_tuple(value: Any, name: str) -> tuple[str, ...]:
    values = _record_sequence(value, name)
    if any(not isinstance(item, str) or not item for item in values):
        raise TypeError(f"{name} must contain non-empty strings")
    return tuple(values)


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must not be empty")
    return value


def _utc(value: Any, name: str) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError as error:
            raise ValueError(f"{name} must be an ISO-8601 datetime") from error
    return require_utc_datetime(value, name)


def _optional_utc(value: Any, name: str) -> datetime | None:
    return None if value is None else _utc(value, name)


def _positive_integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _non_negative_integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _optional_decimal(value: Any, name: str) -> Decimal | None:
    return None if value is None else _decimal(value, name)


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _json_copy(value: Any) -> Any:
    return json.loads(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    )


def _positive_decimal(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


def _non_negative_decimal(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


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


def _optional(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _optional_time(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


__all__ = [
    "ADD_ACTION",
    "ARM_ENTRY_ACTION",
    "BACKTEST_ACTIONS",
    "BACKTEST_END_POLICY_VERSION",
    "BACKTEST_ENGINE_FEATURE_ID",
    "BACKTEST_ENGINE_POLICY_VERSION",
    "BACKTEST_FUNDING_POLICY_VERSION",
    "BACKTEST_NAV_POLICY_VERSION",
    "BACKTEST_RECONCILIATION_TOLERANCE",
    "BACKTEST_REASON_CODES",
    "EXIT_ACTION",
    "SHARED_CALCULATION_SOURCES",
    "TRAIL_ACTION",
    "TRIM_ACTION",
    "BacktestContext",
    "BacktestEvent",
    "BacktestIntent",
    "BacktestResult",
    "EquityPoint",
    "restore_backtest_result",
    "run_backtest",
]
