"""Paper trading account and its execution cost model (BTC-160).

The five configurables the ticket asks for already exist as versioned strategy
configuration under ``[backtest]``: ``initial_cash``, ``fee_bps``,
``slippage_bps`` and ``funding_cost_bps_per_day``, with available cash derived
from the account's own balance. This module reads those rather than minting a
parallel paper-only set, because rulebook 32 rule 15 requires advisory, paper
trading and backtesting to share the same quantitative assumptions. A separate
``[paper]`` fee block would let the two silently diverge, which is exactly the
failure that rule exists to prevent.

NAV and cash are deliberately distinct. BTC-144, BTC-145 and BTC-146 all size
against **NAV**, and NAV is cash plus the unrealized value of open positions.
Sizing against cash instead would shrink every position as soon as a trade went
into profit, so the account exposes ``nav()`` explicitly and never lets the two
words blur into one number.

Costs are expressed in basis points, where 10 bps is 0.10%. Slippage is always
adverse: a buy fills higher and a sell fills lower. There is no configuration
that makes paper fills better than the reference price.

The account is immutable. Charging a fee returns a new account, so a rejected
or replayed step can never leave a half-applied balance behind.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from typing import Any

from btc_predictor.config.strategy import StrategyConfig, load_strategy_config
from btc_predictor.data import require_utc_datetime
from btc_predictor.quant.comparisons import decision_greater, decision_less_equal


PAPER_ACCOUNT_FEATURE_ID = "PAPER_ACCOUNT"
PAPER_ACCOUNT_POLICY_VERSION = "PAPER_ACCOUNT_V1"
EXECUTION_COST_POLICY_VERSION = "EXECUTION_COST_V1"

# 1 bp = 0.01%. Every rate on ExecutionCosts is in basis points, so the unit is
# stated once here instead of being re-derived at each call site.
BASIS_POINT = Decimal("0.0001")

ACCOUNT_ACTIVE = "active"
ACCOUNT_ARCHIVED = "archived"
PAPER_ACCOUNT_STATUSES = (ACCOUNT_ACTIVE, ACCOUNT_ARCHIVED)

BUY_SIDE = "buy"
SELL_SIDE = "sell"
ORDER_SIDES = (BUY_SIDE, SELL_SIDE)

PAPER_ACCOUNT_REASON_CODES = (
    "PAPER_ACCOUNT_OPENED",
    "PAPER_ACCOUNT_FEE_CHARGED",
    "PAPER_ACCOUNT_FUNDING_CHARGED",
    "PAPER_ACCOUNT_PNL_SETTLED",
    "PAPER_ACCOUNT_ARCHIVED",
    "PAPER_ACCOUNT_CASH_EXHAUSTED",
)


@dataclass(frozen=True)
class ExecutionCosts:
    """Versioned fee, slippage and funding assumptions, all in basis points."""

    policy_version: str
    fee_bps: Decimal
    slippage_bps: Decimal
    funding_cost_bps_per_day: Decimal

    def fee(self, notional: Any) -> Decimal:
        """Return the commission charged on one fill of ``notional``."""

        return _non_negative(notional, "notional") * self.fee_bps * BASIS_POINT

    def slippage(self, notional: Any) -> Decimal:
        """Return the adverse execution cost on one fill of ``notional``."""

        return _non_negative(notional, "notional") * self.slippage_bps * BASIS_POINT

    def fill_price(self, price: Any, *, side: str) -> Decimal:
        """Return the reference price moved adversely by the slippage rate."""

        if side not in ORDER_SIDES:
            raise ValueError(f"side must be one of {ORDER_SIDES}")
        reference = _positive(price, "price")
        drift = reference * self.slippage_bps * BASIS_POINT
        return reference + drift if side == BUY_SIDE else reference - drift

    def funding(self, notional: Any, *, days: Any) -> Decimal:
        """Return the carry charged on ``notional`` held for ``days``."""

        value = _non_negative(notional, "notional")
        return value * self.funding_rate(days=days)

    def funding_rate(self, *, days: Any) -> Decimal:
        """Return the signed-account carry rate for a holding interval."""

        held = _non_negative(days, "days")
        return self.funding_cost_bps_per_day * BASIS_POINT * held

    def round_trip_cost(self, notional: Any) -> Decimal:
        """Return fee plus slippage on both the entry and the exit fill.

        A 2R target is not 2R after costs, so the round trip is available as
        one number rather than being reassembled by each caller.
        """

        value = _non_negative(notional, "notional")
        return (self.fee(value) + self.slippage(value)) * Decimal("2")

    def as_record(self) -> dict[str, Any]:
        return {
            "policy_version": self.policy_version,
            "fee_bps": str(self.fee_bps),
            "slippage_bps": str(self.slippage_bps),
            "funding_cost_bps_per_day": str(self.funding_cost_bps_per_day),
        }


@dataclass(frozen=True)
class PaperAccount:
    """Immutable paper account state; every charge returns a new account."""

    feature_id: str
    policy_version: str
    account_name: str
    base_currency: str
    starting_nav: Decimal
    cash: Decimal
    reserved_cash: Decimal
    realized_pnl: Decimal
    fees_paid: Decimal
    funding_paid: Decimal
    costs: ExecutionCosts
    status: str
    created_at: datetime
    config_metadata: dict[str, str]
    reason_codes: tuple[str, ...] = ()

    @property
    def available_cash(self) -> Decimal:
        """Deployable cash: the balance less any reserve, floored at zero."""

        remaining = self.cash - self.reserved_cash
        return remaining if remaining > 0 else Decimal("0")

    @property
    def total_costs_paid(self) -> Decimal:
        return self.fees_paid + self.funding_paid

    @property
    def is_active(self) -> bool:
        return self.status == ACCOUNT_ACTIVE

    def nav(self, *, unrealized_pnl: Any = Decimal("0")) -> Decimal:
        """Return cash plus the unrealized value of open positions.

        This, not ``cash``, is what BTC-144, BTC-145 and BTC-146 size against.
        """

        return self.cash + _decimal(unrealized_pnl, "unrealized_pnl")

    def charge_fee(self, notional: Any) -> PaperAccount:
        return self._debit(
            self.costs.fee(notional),
            field="fees_paid",
            reason="PAPER_ACCOUNT_FEE_CHARGED",
        )

    def charge_funding(self, notional: Any, *, days: Any) -> PaperAccount:
        return self._debit(
            self.costs.funding(notional, days=days),
            field="funding_paid",
            reason="PAPER_ACCOUNT_FUNDING_CHARGED",
        )

    def apply_funding_cost(self, amount: Any) -> PaperAccount:
        """Apply a signed BTC-165 funding cost without recomputing it.

        Positive values are paid by the account and negative values are
        receipts. This is the account-side companion to
        ``funding_event_from_rate`` and keeps long/short funding symmetry in
        one authoritative path.
        """

        return self._debit(
            _decimal(amount, "amount"),
            field="funding_paid",
            reason="PAPER_ACCOUNT_FUNDING_CHARGED",
        )

    def settle_realized_pnl(self, amount: Any) -> PaperAccount:
        """Apply a signed realized profit or loss to cash."""

        value = _decimal(amount, "amount")
        cash = self.cash + value
        return replace(
            self,
            cash=cash if cash > 0 else Decimal("0"),
            realized_pnl=self.realized_pnl + value,
            reason_codes=(
                ("PAPER_ACCOUNT_PNL_SETTLED", "PAPER_ACCOUNT_CASH_EXHAUSTED")
                if cash <= 0
                else ("PAPER_ACCOUNT_PNL_SETTLED",)
            ),
        )

    def archive(self) -> PaperAccount:
        return replace(
            self,
            status=ACCOUNT_ARCHIVED,
            reason_codes=("PAPER_ACCOUNT_ARCHIVED",),
        )

    def _debit(self, amount: Decimal, *, field: str, reason: str) -> PaperAccount:
        cash = self.cash - amount
        exhausted = cash <= 0
        return replace(
            self,
            cash=cash if not exhausted else Decimal("0"),
            reason_codes=(
                (reason, "PAPER_ACCOUNT_CASH_EXHAUSTED") if exhausted else (reason,)
            ),
            **{field: getattr(self, field) + amount},
        )

    def as_record(self) -> dict[str, Any]:
        if self.status not in PAPER_ACCOUNT_STATUSES:
            raise ValueError(f"status must be one of {PAPER_ACCOUNT_STATUSES}")
        if self.cash < 0 or self.starting_nav < 0:
            raise ValueError("paper account balances must not be negative")
        if decision_greater(self.reserved_cash, self.starting_nav):
            raise ValueError("reserved_cash must not exceed starting_nav")
        created_at = require_utc_datetime(self.created_at, "created_at")
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "account_name": self.account_name,
            "base_currency": self.base_currency,
            "starting_nav": str(self.starting_nav),
            "cash": str(self.cash),
            "reserved_cash": str(self.reserved_cash),
            "available_cash": str(self.available_cash),
            "realized_pnl": str(self.realized_pnl),
            "fees_paid": str(self.fees_paid),
            "funding_paid": str(self.funding_paid),
            "costs": self.costs.as_record(),
            "status": self.status,
            "created_at": created_at.isoformat(),
            "config_metadata": dict(self.config_metadata),
            "reason_codes": list(self.reason_codes),
        }

    def as_db_record(self) -> dict[str, Any]:
        """Return the ``portfolio.paper_accounts`` columns for this account.

        The table stores cash, not NAV, and its status CHECK accepts only
        ``active`` and ``archived``; keeping that mapping here means no caller
        invents one that the constraint would reject.
        """

        record = self.as_record()
        return {
            "account_name": record["account_name"],
            "base_currency": record["base_currency"],
            "starting_cash": Decimal(record["starting_nav"]),
            "current_cash": Decimal(record["cash"]),
            "created_at": require_utc_datetime(self.created_at, "created_at"),
            "status": record["status"],
        }


def execution_costs_from_config(
    config: StrategyConfig | None = None,
) -> ExecutionCosts:
    """Return the shared execution assumptions from versioned configuration."""

    resolved = config if config is not None else load_strategy_config()
    if not isinstance(resolved, StrategyConfig):
        raise TypeError("config must be a StrategyConfig")
    backtest = resolved.backtest
    return ExecutionCosts(
        policy_version=EXECUTION_COST_POLICY_VERSION,
        fee_bps=_non_negative(backtest.fee_bps, "fee_bps"),
        slippage_bps=_non_negative(backtest.slippage_bps, "slippage_bps"),
        funding_cost_bps_per_day=_non_negative(
            backtest.funding_cost_bps_per_day,
            "funding_cost_bps_per_day",
        ),
    )


def open_paper_account(
    *,
    account_name: str,
    created_at: datetime,
    starting_nav: Any | None = None,
    reserved_cash: Any = Decimal("0"),
    base_currency: str = "USD",
    costs: ExecutionCosts | None = None,
    config: StrategyConfig | None = None,
    config_metadata: Mapping[str, str] | None = None,
) -> PaperAccount:
    """Open an account from versioned configuration.

    ``starting_nav`` defaults to ``backtest.initial_cash`` and ``costs`` to the
    configured fee, slippage and funding rates, so a paper run and a backtest
    of the same period begin from identical assumptions unless a caller
    deliberately overrides them.
    """

    if not account_name or not account_name.strip():
        raise ValueError("account_name must not be empty")
    if not base_currency or not base_currency.strip():
        raise ValueError("base_currency must not be empty")
    resolved = config if config is not None else load_strategy_config()
    if not isinstance(resolved, StrategyConfig):
        raise TypeError("config must be a StrategyConfig")

    nav = (
        _positive(starting_nav, "starting_nav")
        if starting_nav is not None
        else _positive(resolved.backtest.initial_cash, "starting_nav")
    )
    reserve = _non_negative(reserved_cash, "reserved_cash")
    if decision_greater(reserve, nav):
        # Reserving more than the account holds is a configuration error, not a
        # zero-cash account that would silently refuse every trade.
        raise ValueError("reserved_cash must not exceed starting_nav")

    return PaperAccount(
        feature_id=PAPER_ACCOUNT_FEATURE_ID,
        policy_version=PAPER_ACCOUNT_POLICY_VERSION,
        account_name=account_name.strip(),
        base_currency=base_currency.strip(),
        starting_nav=nav,
        cash=nav,
        reserved_cash=reserve,
        realized_pnl=Decimal("0"),
        fees_paid=Decimal("0"),
        funding_paid=Decimal("0"),
        costs=costs if costs is not None else execution_costs_from_config(resolved),
        status=ACCOUNT_ACTIVE,
        created_at=require_utc_datetime(created_at, "created_at"),
        config_metadata=dict(config_metadata or resolved.run_metadata()),
        reason_codes=("PAPER_ACCOUNT_OPENED",),
    )


def _decimal(value: Any, name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    try:
        result = Decimal(str(value))
    except Exception as error:  # noqa: BLE001 - surfaced as a domain error
        raise ValueError(f"{name} must be numeric") from error
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    return result


def _positive(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if decision_less_equal(result, 0):
        raise ValueError(f"{name} must be positive")
    return result


def _non_negative(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


__all__ = [
    "ACCOUNT_ACTIVE",
    "ACCOUNT_ARCHIVED",
    "BASIS_POINT",
    "BUY_SIDE",
    "EXECUTION_COST_POLICY_VERSION",
    "ORDER_SIDES",
    "PAPER_ACCOUNT_FEATURE_ID",
    "PAPER_ACCOUNT_POLICY_VERSION",
    "PAPER_ACCOUNT_REASON_CODES",
    "PAPER_ACCOUNT_STATUSES",
    "SELL_SIDE",
    "ExecutionCosts",
    "PaperAccount",
    "execution_costs_from_config",
    "open_paper_account",
]
