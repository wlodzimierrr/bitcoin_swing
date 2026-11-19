"""RBT-007 metrics: the frozen ``RESEARCH_BACKTEST_METRIC_DEFINITIONS_V1`` (RBT-006 ruling 4).

Every metric follows its frozen definition in the preregistration. An
``OWNER_CONVENTION`` metric calls the owner function the definition names;
a ``NEW_DEFINITION`` metric is computed here, in the BTC-188 owner's decimal
context (``SURFACE_DECIMAL_PRECISION``) and quantized like the owner's
metrics (``1E-12``, half-even), so every rate is reported to one precision.
A metric that cannot be computed carries its undefined status, never zero,
and every rate is reported beside the trade count it is computed over.

A metric is computed on a :class:`RunView`: the headline evaluation-window
run (one engine run, as one fold), a BTC-182 walk-forward (its folds) or
one fold alone. The owner functions read only a validation's folds and
their results, so they apply to the view unchanged; the view's fold return
and mean fold return are BTC-182's own. Trades and equity points pool
across folds; drawdowns and Calmar follow the owner's worst-fold and
mean-fold-return conventions.

The cross-venue measures (policy V7 section 8, clarification 4a) compare the
three venues' headline runs.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from statistics import median
from typing import Any

from btc_predictor.backtest import parameter_surfaces as surfaces
from btc_predictor.backtest import setup_performance as setups
from btc_predictor.backtest import threshold_sweeps as sweeps
from btc_predictor.backtest import walk_forward as wf
from btc_predictor.backtest.engine import BacktestResult
from btc_predictor.backtest.walk_forward import WalkForwardValidation
from btc_predictor.portfolio.accounting import CLOSING_ACTIONS

METRICS_VERSION = "RBT007_METRICS_V1"
AVAILABLE = "AVAILABLE"
NO_CLOSED_TRADES = "NO_CLOSED_TRADES"
NO_R_MULTIPLE = "NO_R_MULTIPLE"
NO_WINNING_TRADES = "NO_WINNING_TRADES"
NO_LOSING_TRADES = "NO_LOSING_TRADES"
NO_EQUITY_CURVE = "UNAVAILABLE_NO_EQUITY_CURVE"
NON_POSITIVE_NAV = "UNDEFINED_NON_POSITIVE_NAV"
INSUFFICIENT_PERIODS = "UNAVAILABLE_INSUFFICIENT_PERIODS"
NO_DOWNSIDE = "UNDEFINED_NO_DOWNSIDE"
STRUCTURAL_STOP_EXIT = "STRUCTURAL_STOP"
VENUE_ORDER = ("BITSTAMP", "COINBASE", "BITFINEX")

PRIMARY_METRICS = (
    "expectancy",
    "average_r_per_trade",
    "sharpe",
    "sortino",
    "calmar",
    "max_drawdown",
    "return_per_trade",
    "win_rate",
    "profit_factor",
    "average_winner",
    "average_loser",
    "time_in_market",
    "turnover",
    "number_of_trades",
    "longest_drawdown",
    "longest_losing_streak",
)


@dataclass(frozen=True)
class FoldView:
    """One engine run as a fold: what the owner metric functions read of a BTC-182 fold."""

    fold_number: int
    result: BacktestResult

    @property
    def starting_nav(self) -> Decimal:
        return self.result.starting_nav

    @property
    def total_pnl(self) -> Decimal:
        return self.result.total_pnl

    @property
    def net_pnl(self) -> Decimal:
        return self.result.net_pnl

    @property
    def return_fraction(self) -> Decimal:
        return wf._return_fraction(self.total_pnl, self.starting_nav)

    @property
    def position_open_at_end(self) -> bool:
        return self.result.final_lifecycle.quantity > 0


@dataclass(frozen=True)
class RunView:
    """Folds, with BTC-182's aggregate conventions (``WalkForwardValidation``'s properties)."""

    folds: tuple[FoldView, ...]

    @property
    def fold_count(self) -> int:
        return len(self.folds)

    @property
    def summed_net_pnl(self) -> Decimal:
        return sum((fold.net_pnl for fold in self.folds), Decimal("0"))

    @property
    def mean_return_fraction(self) -> Decimal:
        total = sum((fold.return_fraction for fold in self.folds), Decimal("0"))
        return (total / self.fold_count).quantize(wf.WALK_FORWARD_RETURN_EXPONENT, rounding=ROUND_HALF_EVEN)

    @property
    def worst_fold(self) -> FoldView:
        return min(self.folds, key=lambda fold: (fold.return_fraction, fold.fold_number))

    @property
    def best_fold(self) -> FoldView:
        return max(self.folds, key=lambda fold: (fold.return_fraction, -fold.fold_number))


def single_view(result: BacktestResult) -> RunView:
    return RunView((FoldView(1, result),))


def validation_view(validation: WalkForwardValidation) -> RunView:
    validation.as_record()
    return RunView(tuple(FoldView(fold.fold_number, fold.result) for fold in validation.folds))


def _q(value: Decimal) -> Decimal:
    return surfaces._quantize(value)


def _text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _metric(value: Decimal | None, status: str, **counts: Any) -> dict[str, Any]:
    return {"value": _text(value), "status": status, **counts}


def _trades(validation: RunView) -> tuple[Any, ...]:
    return tuple(trade for fold in validation.folds for trade in fold.result.trades)


def _closed(validation: RunView) -> tuple[Any, ...]:
    return tuple(trade for trade in _trades(validation) if trade.closed)


def _equity(validation: RunView) -> tuple[Any, ...]:
    return tuple(point for fold in validation.folds for point in fold.result.equity_curve)


# --- the sixteen primary metrics -------------------------------------------------------------------


def run_metrics(validation: RunView) -> dict[str, Any]:
    """Every primary metric of one run view, each with its status and trade count."""

    if not isinstance(validation, RunView):
        raise TypeError("metrics are computed on a RunView")
    with localcontext(Context(prec=surfaces.SURFACE_DECIMAL_PRECISION)):
        owner = sweeps._metrics(validation)
        trades = _trades(validation)
        closed = _closed(validation)
        closed_count = len(closed)
        metrics: dict[str, Any] = {}

        metrics["expectancy"] = _metric(
            owner.closed_trade_expectancy,
            AVAILABLE if owner.closed_trade_expectancy is not None else NO_CLOSED_TRADES,
            closed_trades=closed_count,
        )
        metrics["average_r_per_trade"] = _metric(
            owner.mean_r_multiple,
            AVAILABLE if owner.mean_r_multiple is not None else NO_R_MULTIPLE,
            closed_trades=closed_count,
            r_multiple_trades=owner.r_multiple_count,
        )

        returns, return_status = surfaces._period_returns(validation)
        sharpe, sharpe_status = surfaces._sharpe(returns, return_status)
        metrics["sharpe"] = _metric(sharpe, sharpe_status, periods=len(returns), closed_trades=closed_count)
        sortino, sortino_status = _sortino(returns, return_status)
        metrics["sortino"] = _metric(sortino, sortino_status, periods=len(returns), closed_trades=closed_count)

        drawdown, drawdown_status = surfaces._max_drawdown(validation)
        calmar, calmar_status = surfaces._calmar(validation.mean_return_fraction, drawdown, drawdown_status)
        metrics["calmar"] = _metric(
            calmar, calmar_status, return_fraction=str(validation.mean_return_fraction), closed_trades=closed_count
        )
        metrics["max_drawdown"] = _metric(drawdown, drawdown_status, closed_trades=closed_count)

        if closed:
            per_trade = _q(sum((trade.net_pnl / trade.entry_notional for trade in closed), Decimal("0")) / Decimal(closed_count))
            metrics["return_per_trade"] = _metric(per_trade, AVAILABLE, closed_trades=closed_count)
            wins = sum(1 for trade in closed if trade.net_pnl > 0)
            metrics["win_rate"] = _metric(_q(Decimal(wins) / Decimal(closed_count)), AVAILABLE, closed_trades=closed_count, winning_trades=wins)
        else:
            metrics["return_per_trade"] = _metric(None, NO_CLOSED_TRADES, closed_trades=0)
            metrics["win_rate"] = _metric(None, NO_CLOSED_TRADES, closed_trades=0, winning_trades=0)

        profit = sum((trade.net_pnl for trade in closed if trade.net_pnl > 0), Decimal("0"))
        loss = sum((trade.net_pnl for trade in closed if trade.net_pnl < 0), Decimal("0"))
        factor, factor_status = setups._profit_factor(closed_count=closed_count, closed_profit=profit, closed_loss=loss)
        metrics["profit_factor"] = _metric(factor, factor_status, closed_trades=closed_count)

        winners = tuple(trade.net_pnl for trade in closed if trade.net_pnl > 0)
        losers = tuple(trade.net_pnl for trade in closed if trade.net_pnl < 0)
        metrics["average_winner"] = _metric(
            _q(sum(winners, Decimal("0")) / Decimal(len(winners))) if winners else None,
            AVAILABLE if winners else NO_WINNING_TRADES,
            winning_trades=len(winners),
            closed_trades=closed_count,
        )
        metrics["average_loser"] = _metric(
            _q(sum(losers, Decimal("0")) / Decimal(len(losers))) if losers else None,
            AVAILABLE if losers else NO_LOSING_TRADES,
            losing_trades=len(losers),
            closed_trades=closed_count,
        )

        equity = _equity(validation)
        if equity:
            in_market = sum(1 for point in equity if point.open_quantity > 0)
            metrics["time_in_market"] = _metric(
                _q(Decimal(in_market) / Decimal(len(equity))), AVAILABLE, equity_points=len(equity), closed_trades=closed_count
            )
        else:
            metrics["time_in_market"] = _metric(None, NO_EQUITY_CURVE, equity_points=0, closed_trades=closed_count)
        metrics["turnover"] = _turnover(validation, trades, equity, closed_count)

        open_at_end = sum(1 for fold in validation.folds if fold.position_open_at_end)
        metrics["number_of_trades"] = {
            "value": str(len(trades)),
            "status": AVAILABLE,
            "trades": len(trades),
            "closed_trades": closed_count,
            "open_at_end": open_at_end,
        }
        metrics["longest_drawdown"] = {**_longest_drawdown(validation), "closed_trades": closed_count}
        metrics["longest_losing_streak"] = _losing_streak(closed)
    return metrics


def _sortino(returns: tuple[Decimal, ...], status: str) -> tuple[Decimal | None, str]:
    """Mean period return over the downside deviation sqrt(sum(min(r, 0)^2) / n)."""

    if status != surfaces.SHARPE_AVAILABLE:
        return None, status
    if len(returns) < 2:
        return None, INSUFFICIENT_PERIODS
    count = Decimal(len(returns))
    mean = sum(returns, Decimal("0")) / count
    downside = sum((min(value, Decimal("0")) ** 2 for value in returns), Decimal("0")) / count
    if downside <= 0:
        return None, NO_DOWNSIDE
    deviation = downside.sqrt()
    if deviation == 0:
        return None, NO_DOWNSIDE
    return _q(mean / deviation), AVAILABLE


def _turnover(validation: RunView, trades: Sequence[Any], equity: Sequence[Any], closed_count: int) -> dict[str, Any]:
    days = sum(
        ((fold.result.ended_at - fold.result.started_at).total_seconds() for fold in validation.folds if fold.result.started_at is not None),
        0.0,
    )
    length_days = str(_q(Decimal(str(days)) / Decimal(86400)))
    if not equity:
        return _metric(None, NO_EQUITY_CURVE, run_days=length_days, closed_trades=closed_count)
    mean_nav = sum((point.nav for point in equity), Decimal("0")) / Decimal(len(equity))
    if mean_nav <= 0:
        return _metric(None, NON_POSITIVE_NAV, run_days=length_days, closed_trades=closed_count)
    traded = sum((trade.entry_notional + trade.exit_notional for trade in trades), Decimal("0"))
    return _metric(_q(traded / mean_nav), AVAILABLE, run_days=length_days, trades=len(trades), closed_trades=closed_count)


def _fold_longest_drawdown(fold: Any) -> tuple[Decimal, bool] | None:
    """One fold's longest time underwater in hours, and whether it recovered."""

    result = fold.result
    if not result.equity_curve or result.started_at is None:
        return None
    peak = fold.starting_nav
    at_peak = result.started_at
    start: datetime | None = None
    longest = timedelta(0)
    recovered = True
    for point in result.equity_curve:
        if point.nav >= peak:
            if start is not None:
                length = point.as_of - start
                if length > longest:
                    longest, recovered = length, True
                start = None
            peak = point.nav
            at_peak = point.as_of
        elif start is None:
            start = at_peak
    if start is not None:
        length = result.equity_curve[-1].as_of - start
        if length > longest:
            longest, recovered = length, False
    return Decimal(str(longest.total_seconds())) / Decimal(3600), recovered


def _longest_drawdown(validation: RunView) -> dict[str, Any]:
    best: tuple[Decimal, bool, int] | None = None
    for fold in validation.folds:
        found = _fold_longest_drawdown(fold)
        if found is None:
            continue
        hours, recovered = found
        if best is None or hours > best[0]:
            best = (hours, recovered, fold.fold_number)
    if best is None:
        return _metric(None, NO_EQUITY_CURVE)
    return _metric(_q(best[0]), AVAILABLE, recovered=best[1], fold_number=best[2])


def _losing_streak(closed: Sequence[Any]) -> dict[str, Any]:
    longest = current = 0
    for trade in sorted(closed, key=lambda item: item.closed_at):
        current = current + 1 if trade.net_pnl < 0 else 0
        longest = max(longest, current)
    return {"value": str(longest), "status": AVAILABLE, "closed_trades": len(closed)}


def fold_metrics(view: RunView) -> list[dict[str, Any]]:
    """Each fold's primary metrics, computed on that fold alone."""

    return [{"fold_number": fold.fold_number, "metrics": run_metrics(RunView((fold,)))} for fold in view.folds]


# --- the cross-venue measures (clarification 4a) ------------------------------------------------


def cross_venue(
    entries: Mapping[str, Sequence[Mapping[str, Any]]],
    trades: Mapping[str, Sequence[Any]],
    trade_entries: Mapping[str, Mapping[int, str]],
    metrics: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> dict[str, Any]:
    """The four policy V7 section 8 measures over the three venues' headline runs.

    ``entries`` maps each venue to its ARM_ENTRY ledger records,
    ``trade_entries`` maps each venue's trade index to the decision instant of
    the ARM_ENTRY row that opened it (the trade sets are these trades), and ``metrics`` maps each cost rung to
    each venue's primary metrics.
    """

    venues = [venue for venue in VENUE_ORDER if venue in entries]
    keyed: dict[str, dict[tuple[str, str], dict[str, Any]]] = {}
    for venue in venues:
        # review F7: the sets hold filled trades, each by the ARM_ENTRY row that opened it; an unfilled intent is no trade
        rows = {row["decision_at"]: row for row in entries[venue]}
        keyed[venue] = {(instant, rows[instant]["setup"]): rows[instant] for instant in trade_entries[venue].values()}
    trade_by_entry: dict[str, dict[str, Any]] = {
        venue: {instant: trades[venue][index] for index, instant in trade_entries[venue].items()} for venue in venues
    }
    pairs = [(first, second) for position, first in enumerate(venues) for second in venues[position + 1 :]]
    overlap: list[dict[str, Any]] = []
    divergence: list[dict[str, Any]] = []
    touches: list[dict[str, Any]] = []
    for first, second in pairs:
        a, b = set(keyed[first]), set(keyed[second])
        matched = sorted(a & b)
        only_first, only_second = len(a - b), len(b - a)
        total = len(matched) + only_first + only_second
        overlap.append(
            {
                "pair": [first, second],
                "matched": len(matched),
                "only_first": only_first,
                "only_second": only_second,
                "overlap": str(_q(Decimal(len(matched)) / Decimal(total))) if total else None,
                "status": AVAILABLE if total else "NO_TRADES",
            }
        )
        divergence.append(_pair_divergence(first, second, matched, trade_by_entry))
        touches.append(_stop_touch(first, second, matched, trade_by_entry))
    everywhere = set.intersection(*(set(keyed[venue]) for venue in venues)) if venues else set()
    return {
        "trade_set_overlap": {"pairs": overlap, "matched_on_all_venues": len(everywhere)},
        "matched_trade_divergence": divergence,
        "stop_touch_divergence": touches,
        "metric_dispersion": _dispersion(metrics, venues),
    }


def _matched_trades(first: str, second: str, matched: Sequence[tuple[str, str]], trade_by_entry: Mapping[str, Mapping[str, Any]]) -> list[tuple[Any, Any]]:
    out = []
    for instant, _setup in matched:
        a = trade_by_entry[first].get(instant)
        b = trade_by_entry[second].get(instant)
        if a is not None and b is not None:
            out.append((a, b))
    return out


def _exit_price(trade: Any) -> Decimal | None:
    if not trade.closed:
        return None
    exited = sum((fill.quantity for fill in trade.fills if fill.action in CLOSING_ACTIONS), Decimal("0"))
    if exited <= 0:
        return None
    return trade.exit_notional / exited


def _summary(values: Sequence[Decimal]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "mean": None, "median": None, "largest_absolute": None}
    return {
        "count": len(values),
        "mean": str(_q(sum(values, Decimal("0")) / Decimal(len(values)))),
        "median": str(_q(Decimal(median(values)))),
        "largest_absolute": str(_q(max(abs(value) for value in values))),
    }


def _pair_divergence(first: str, second: str, matched: Sequence[tuple[str, str]], trade_by_entry: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    pairs = _matched_trades(first, second, matched, trade_by_entry)
    with localcontext(Context(prec=surfaces.SURFACE_DECIMAL_PRECISION)):
        entry = [(b.average_entry_price - a.average_entry_price) / a.average_entry_price for a, b in pairs]
        stop = [(b.initial_stop_price - a.initial_stop_price) / a.initial_stop_price for a, b in pairs]
        exits = []
        for a, b in pairs:
            ea, eb = _exit_price(a), _exit_price(b)
            if ea is not None and eb is not None:
                exits.append((eb - ea) / ea)
        mfe = [b.mfe_r - a.mfe_r for a, b in pairs if a.mfe_r is not None and b.mfe_r is not None]
        mae = [b.mae_r - a.mae_r for a, b in pairs if a.mae_r is not None and b.mae_r is not None]
        return {
            "pair": [first, second],
            "matched": len(pairs),
            "status": AVAILABLE if pairs else "NO_MATCHED_TRADES",
            "average_entry_price": _summary(entry),
            "initial_stop_price": _summary(stop),
            "average_exit_price": _summary(exits),
            "mfe_r": _summary(mfe),
            "mae_r": _summary(mae),
        }


def _stop_touch(first: str, second: str, matched: Sequence[tuple[str, str]], trade_by_entry: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    pairs = [(a, b) for a, b in _matched_trades(first, second, matched, trade_by_entry) if a.closed and b.closed]
    exactly_one = sum(1 for a, b in pairs if (a.exit_reason == STRUCTURAL_STOP_EXIT) != (b.exit_reason == STRUCTURAL_STOP_EXIT))
    return {
        "pair": [first, second],
        "matched_closed": len(pairs),
        "exactly_one_structural_stop": exactly_one,
        "status": AVAILABLE if pairs else "NO_MATCHED_CLOSED_TRADES",
    }


def _dispersion(metrics: Mapping[str, Mapping[str, Mapping[str, Any]]], venues: Sequence[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for rung, by_venue in sorted(metrics.items()):
        rows = {}
        for name in PRIMARY_METRICS:
            values = {venue: by_venue[venue][name] for venue in venues}
            defined = all(item["status"] == AVAILABLE and item["value"] is not None for item in values.values())
            if defined:
                numbers = [Decimal(item["value"]) for item in values.values()]
                rows[name] = {
                    "values": {venue: item["value"] for venue, item in values.items()},
                    "max_minus_min": str(_q(max(numbers) - min(numbers))),
                    "status": AVAILABLE,
                }
            else:
                rows[name] = {
                    "statuses": {venue: item["status"] for venue, item in values.items()},
                    "status": "UNDEFINED_ON_SOME_VENUE",
                }
        out[rung] = rows
    return out
