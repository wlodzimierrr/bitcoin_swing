"""Out-of-sample setup-level performance comparison (BTC-184).

The report consumes the same point-in-time entry contexts as BTC-183 and
delegates trade attribution to that module.  This layer compares the four
Phase-1 setup archetypes; it does not detect setups, rescore historical data,
or introduce another trade-accounting formula.

Closed-trade quality metrics use BTC-165 net outcomes.  Open trades contribute
realized net P&L, costs, and the BTC-183 fold-end mark to totals, but they are
excluded from closed-outcome metrics such as expectancy, win rate, profit
factor, and average holding period.  An unavailable metric remains ``None``
and carries an explicit status where the reason is otherwise ambiguous.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import Any

from btc_predictor.backtest.regime_performance import (
    OPEN_TRADE_MARK_POLICY_VERSION,
    PERFORMANCE_RATE_EXPONENT,
    SETUP_BUCKETS,
    SETUP_DIMENSION,
    RegimePerformanceBreakdown,
    RegimePerformanceContext,
    restore_regime_performance_breakdown,
    run_regime_performance_breakdown,
)
from btc_predictor.backtest.walk_forward import WalkForwardValidation


SETUP_PERFORMANCE_FEATURE_ID = "SETUP_LEVEL_PERFORMANCE_REPORT"
SETUP_PERFORMANCE_POLICY_VERSION = "SETUP_LEVEL_PERFORMANCE_REPORT_V1"
SETUP_METRIC_POLICY_VERSION = "CLOSED_NET_OUTCOME_METRICS_V1"
SETUP_PROFIT_FACTOR_POLICY_VERSION = (
    "CLOSED_NET_PROFIT_OVER_ABSOLUTE_CLOSED_NET_LOSS_V1"
)

PROFIT_FACTOR_AVAILABLE = "AVAILABLE"
PROFIT_FACTOR_NO_CLOSED_TRADES = "NO_CLOSED_TRADES"
PROFIT_FACTOR_NO_CLOSED_LOSSES = "UNBOUNDED_NO_CLOSED_LOSSES"
PROFIT_FACTOR_ALL_CLOSED_TRADES_FLAT = "UNDEFINED_ALL_CLOSED_TRADES_FLAT"
PROFIT_FACTOR_STATUSES = (
    PROFIT_FACTOR_AVAILABLE,
    PROFIT_FACTOR_NO_CLOSED_TRADES,
    PROFIT_FACTOR_NO_CLOSED_LOSSES,
    PROFIT_FACTOR_ALL_CLOSED_TRADES_FLAT,
)

SETUP_PERFORMANCE_REASON_CODES = (
    "SETUP_PERFORMANCE_POINT_IN_TIME_ATTRIBUTION_REUSED",
    "SETUP_PERFORMANCE_ALL_SETUP_ROWS_EMITTED",
    "SETUP_PERFORMANCE_OPEN_TRADES_MARKED",
    "SETUP_PERFORMANCE_PROFIT_FACTOR_UNBOUNDED",
    "SETUP_PERFORMANCE_NO_TRADES",
    "SETUP_PERFORMANCE_COMPLETE",
)


@dataclass(frozen=True)
class SetupPerformance:
    """Comparable economics for one declared Phase-1 setup archetype."""

    setup: str
    trade_count: int
    closed_trade_count: int
    open_trade_count: int
    winning_closed_trades: int
    losing_closed_trades: int
    flat_closed_trades: int
    realized_net_pnl: Decimal
    marked_unrealized_pnl: Decimal
    total_pnl: Decimal
    fees: Decimal
    funding: Decimal
    total_costs: Decimal
    closed_net_profit: Decimal
    closed_net_loss: Decimal
    closed_trade_expectancy: Decimal | None
    closed_trade_win_rate: Decimal | None
    profit_factor: Decimal | None
    profit_factor_status: str
    average_winner: Decimal | None
    average_loser: Decimal | None
    average_closed_holding_days: Decimal | None
    r_multiple_count: int
    summed_r_multiple: Decimal
    mean_r_multiple: Decimal | None

    def as_record(self) -> dict[str, Any]:
        _validate_setup_performance(self)
        return {
            "setup": self.setup,
            "trade_count": self.trade_count,
            "closed_trade_count": self.closed_trade_count,
            "open_trade_count": self.open_trade_count,
            "winning_closed_trades": self.winning_closed_trades,
            "losing_closed_trades": self.losing_closed_trades,
            "flat_closed_trades": self.flat_closed_trades,
            "realized_net_pnl": str(self.realized_net_pnl),
            "marked_unrealized_pnl": str(self.marked_unrealized_pnl),
            "total_pnl": str(self.total_pnl),
            "fees": str(self.fees),
            "funding": str(self.funding),
            "total_costs": str(self.total_costs),
            "closed_net_profit": str(self.closed_net_profit),
            "closed_net_loss": str(self.closed_net_loss),
            "closed_trade_expectancy": _optional_decimal(
                self.closed_trade_expectancy
            ),
            "closed_trade_win_rate": _optional_decimal(
                self.closed_trade_win_rate
            ),
            "profit_factor": _optional_decimal(self.profit_factor),
            "profit_factor_status": self.profit_factor_status,
            "average_winner": _optional_decimal(self.average_winner),
            "average_loser": _optional_decimal(self.average_loser),
            "average_closed_holding_days": _optional_decimal(
                self.average_closed_holding_days
            ),
            "r_multiple_count": self.r_multiple_count,
            "summed_r_multiple": str(self.summed_r_multiple),
            "mean_r_multiple": _optional_decimal(self.mean_r_multiple),
        }


@dataclass(frozen=True)
class SetupPerformanceReport:
    """Replayable BTC-184 comparison over one BTC-182 validation."""

    feature_id: str
    policy_version: str
    metric_policy_version: str
    profit_factor_policy_version: str
    open_trade_mark_policy_version: str
    report_id: str
    evidence_digest: str
    source_breakdown: RegimePerformanceBreakdown
    setups: tuple[SetupPerformance, ...]
    config_metadata: dict[str, str]
    reason_codes: tuple[str, ...]

    @property
    def validation_id(self) -> str:
        return self.source_breakdown.validation.validation_id

    @property
    def trade_count(self) -> int:
        return sum(item.trade_count for item in self.setups)

    def performance(self, setup: str) -> SetupPerformance:
        for item in self.setups:
            if item.setup == setup:
                return item
        raise KeyError(setup)

    def as_record(self) -> dict[str, Any]:
        _validate_report(self)
        payload = _report_payload(self)
        if _digest(payload) != self.evidence_digest:
            raise ValueError("setup performance evidence does not match digest")
        return {**payload, "evidence_digest": self.evidence_digest}


def run_setup_performance_report(
    validation: WalkForwardValidation,
    contexts: Sequence[RegimePerformanceContext],
) -> SetupPerformanceReport:
    """Compare all four setups from filled out-of-sample entry contexts."""

    source = run_regime_performance_breakdown(validation, contexts)
    return setup_performance_report_from_breakdown(source)


def setup_performance_report_from_breakdown(
    source: RegimePerformanceBreakdown,
) -> SetupPerformanceReport:
    """Build BTC-184 evidence from an already validated BTC-183 breakdown."""

    if not isinstance(source, RegimePerformanceBreakdown):
        raise TypeError("source must be a RegimePerformanceBreakdown")
    source.as_record()
    report = SetupPerformanceReport(
        feature_id=SETUP_PERFORMANCE_FEATURE_ID,
        policy_version=SETUP_PERFORMANCE_POLICY_VERSION,
        metric_policy_version=SETUP_METRIC_POLICY_VERSION,
        profit_factor_policy_version=SETUP_PROFIT_FACTOR_POLICY_VERSION,
        open_trade_mark_policy_version=OPEN_TRADE_MARK_POLICY_VERSION,
        report_id="",
        evidence_digest="",
        source_breakdown=source,
        setups=_derive_setup_performance(source),
        config_metadata=dict(source.config_metadata),
        reason_codes=_reason_codes(source),
    )
    report = replace(report, report_id=_report_id(report))
    _validate_report(report)
    return replace(report, evidence_digest=_digest(_report_payload(report)))


def restore_setup_performance_report(
    record: Mapping[str, Any],
) -> SetupPerformanceReport:
    """Restore persisted BTC-184 evidence and reject drift or tampering."""

    source = _mapping(record, "record")
    breakdown = restore_regime_performance_breakdown(
        _mapping(source.get("source_breakdown"), "source_breakdown")
    )
    result = setup_performance_report_from_breakdown(breakdown)
    restored = replace(
        result,
        feature_id=_string(source.get("feature_id"), "feature_id"),
        policy_version=_string(source.get("policy_version"), "policy_version"),
        metric_policy_version=_string(
            source.get("metric_policy_version"), "metric_policy_version"
        ),
        profit_factor_policy_version=_string(
            source.get("profit_factor_policy_version"),
            "profit_factor_policy_version",
        ),
        open_trade_mark_policy_version=_string(
            source.get("open_trade_mark_policy_version"),
            "open_trade_mark_policy_version",
        ),
        report_id=_string(source.get("report_id"), "report_id"),
        evidence_digest=_string(source.get("evidence_digest"), "evidence_digest"),
        config_metadata=_string_mapping(
            source.get("config_metadata"), "config_metadata"
        ),
        reason_codes=_string_tuple(source.get("reason_codes"), "reason_codes"),
    )
    if restored.as_record() != dict(source):
        raise ValueError("record does not match reconstructed setup performance")
    return restored


def _derive_setup_performance(
    source: RegimePerformanceBreakdown,
) -> tuple[SetupPerformance, ...]:
    setup_buckets = source.breakdown(SETUP_DIMENSION)
    buckets = {item.bucket: item for item in setup_buckets.buckets}
    trades_by_setup: dict[str, list[Any]] = {setup: [] for setup in SETUP_BUCKETS}
    fold_by_number = {
        fold.fold_number: fold for fold in source.validation.folds
    }
    for attribution in source.attributions:
        fold = fold_by_number.get(attribution.fold_number)
        if fold is None or not 1 <= attribution.trade_number <= len(fold.result.trades):
            raise ValueError("setup attribution does not identify a validation trade")
        trade = fold.result.trades[attribution.trade_number - 1]
        if trade.evidence_digest != attribution.trade_evidence_digest:
            raise ValueError("setup attribution does not match trade evidence")
        trades_by_setup[attribution.setup].append(trade)

    rows: list[SetupPerformance] = []
    for setup in SETUP_BUCKETS:
        bucket = buckets[setup]
        trades = tuple(trades_by_setup[setup])
        closed = tuple(trade for trade in trades if trade.closed)
        winners = tuple(trade for trade in closed if trade.net_pnl > 0)
        losers = tuple(trade for trade in closed if trade.net_pnl < 0)
        flats = tuple(trade for trade in closed if trade.net_pnl == 0)
        closed_profit = sum((trade.net_pnl for trade in winners), Decimal("0"))
        closed_loss = sum((trade.net_pnl for trade in losers), Decimal("0"))
        profit_factor, profit_factor_status = _profit_factor(
            closed_count=len(closed),
            closed_profit=closed_profit,
            closed_loss=closed_loss,
        )
        row = SetupPerformance(
            setup=setup,
            trade_count=bucket.trade_count,
            closed_trade_count=bucket.closed_trade_count,
            open_trade_count=bucket.open_trade_count,
            winning_closed_trades=bucket.winning_closed_trades,
            losing_closed_trades=bucket.losing_closed_trades,
            flat_closed_trades=bucket.flat_closed_trades,
            realized_net_pnl=bucket.realized_net_pnl,
            marked_unrealized_pnl=bucket.marked_unrealized_pnl,
            total_pnl=bucket.total_pnl,
            fees=sum((trade.fees for trade in trades), Decimal("0")),
            funding=sum((trade.funding for trade in trades), Decimal("0")),
            total_costs=sum(
                (trade.fees + trade.funding for trade in trades), Decimal("0")
            ),
            closed_net_profit=closed_profit,
            closed_net_loss=closed_loss,
            closed_trade_expectancy=(
                _mean((trade.net_pnl for trade in closed)) if closed else None
            ),
            closed_trade_win_rate=bucket.closed_trade_win_rate,
            profit_factor=profit_factor,
            profit_factor_status=profit_factor_status,
            average_winner=(
                _mean((trade.net_pnl for trade in winners)) if winners else None
            ),
            average_loser=(
                _mean((trade.net_pnl for trade in losers)) if losers else None
            ),
            average_closed_holding_days=(
                _mean((trade.holding_days for trade in closed)) if closed else None
            ),
            r_multiple_count=bucket.r_multiple_count,
            summed_r_multiple=bucket.summed_r_multiple,
            mean_r_multiple=bucket.mean_r_multiple,
        )
        _validate_setup_performance(row)
        if len(closed) != len(winners) + len(losers) + len(flats):
            raise ValueError("closed trade outcomes do not reconcile")
        rows.append(row)
    return tuple(rows)


def _profit_factor(
    *,
    closed_count: int,
    closed_profit: Decimal,
    closed_loss: Decimal,
) -> tuple[Decimal | None, str]:
    if closed_count == 0:
        return None, PROFIT_FACTOR_NO_CLOSED_TRADES
    if closed_loss < 0:
        return _ratio(closed_profit, abs(closed_loss)), PROFIT_FACTOR_AVAILABLE
    if closed_profit > 0:
        return None, PROFIT_FACTOR_NO_CLOSED_LOSSES
    return None, PROFIT_FACTOR_ALL_CLOSED_TRADES_FLAT


def _reason_codes(source: RegimePerformanceBreakdown) -> tuple[str, ...]:
    reasons = [
        "SETUP_PERFORMANCE_POINT_IN_TIME_ATTRIBUTION_REUSED",
        "SETUP_PERFORMANCE_ALL_SETUP_ROWS_EMITTED",
    ]
    if any(not attribution.closed for attribution in source.attributions):
        reasons.append("SETUP_PERFORMANCE_OPEN_TRADES_MARKED")
    rows = _derive_setup_performance(source)
    if any(
        row.profit_factor_status == PROFIT_FACTOR_NO_CLOSED_LOSSES
        for row in rows
    ):
        reasons.append("SETUP_PERFORMANCE_PROFIT_FACTOR_UNBOUNDED")
    if not source.attributions:
        reasons.append("SETUP_PERFORMANCE_NO_TRADES")
    reasons.append("SETUP_PERFORMANCE_COMPLETE")
    return tuple(reasons)


def _validate_report(report: SetupPerformanceReport) -> None:
    expected = {
        "feature_id": SETUP_PERFORMANCE_FEATURE_ID,
        "policy_version": SETUP_PERFORMANCE_POLICY_VERSION,
        "metric_policy_version": SETUP_METRIC_POLICY_VERSION,
        "profit_factor_policy_version": SETUP_PROFIT_FACTOR_POLICY_VERSION,
        "open_trade_mark_policy_version": OPEN_TRADE_MARK_POLICY_VERSION,
    }
    for field_name, value in expected.items():
        if getattr(report, field_name) != value:
            raise ValueError(f"{field_name} must be {value}")
    report.source_breakdown.as_record()
    if report.config_metadata != report.source_breakdown.config_metadata:
        raise ValueError("report config identity must match source breakdown")
    if report.setups != _derive_setup_performance(report.source_breakdown):
        raise ValueError("setup metrics do not match source trade evidence")
    if tuple(item.setup for item in report.setups) != SETUP_BUCKETS:
        raise ValueError("report must emit all setup rows in canonical order")
    if report.trade_count != report.source_breakdown.trade_count:
        raise ValueError("setup rows must attribute every trade exactly once")
    if sum((item.total_pnl for item in report.setups), Decimal("0")) != (
        report.source_breakdown.overall.total_pnl
    ):
        raise ValueError("setup P&L must reconcile to source performance")
    if report.reason_codes != _reason_codes(report.source_breakdown):
        raise ValueError("reason codes do not describe setup performance")
    if any(code not in SETUP_PERFORMANCE_REASON_CODES for code in report.reason_codes):
        raise ValueError("setup performance contains an unsupported reason code")
    if report.report_id != _report_id(report):
        raise ValueError("report inputs do not match report_id")


def _validate_setup_performance(item: SetupPerformance) -> None:
    if item.setup not in SETUP_BUCKETS:
        raise ValueError("setup is not a supported Phase-1 setup")
    counts = (
        item.trade_count,
        item.closed_trade_count,
        item.open_trade_count,
        item.winning_closed_trades,
        item.losing_closed_trades,
        item.flat_closed_trades,
        item.r_multiple_count,
    )
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in counts
    ):
        raise ValueError("setup performance counts must be non-negative integers")
    if item.trade_count != item.closed_trade_count + item.open_trade_count:
        raise ValueError("setup trade counts do not reconcile")
    if item.closed_trade_count != (
        item.winning_closed_trades
        + item.losing_closed_trades
        + item.flat_closed_trades
    ):
        raise ValueError("setup closed-trade outcomes do not reconcile")
    if item.total_pnl != item.realized_net_pnl + item.marked_unrealized_pnl:
        raise ValueError("setup P&L does not reconcile")
    if item.total_costs != item.fees + item.funding:
        raise ValueError("setup costs do not reconcile")
    if item.fees < 0 or item.closed_net_profit < 0 or item.closed_net_loss > 0:
        raise ValueError("setup outcome signs are invalid")
    optional_metrics = (
        item.closed_trade_expectancy,
        item.closed_trade_win_rate,
        item.profit_factor,
        item.average_winner,
        item.average_loser,
        item.average_closed_holding_days,
        item.mean_r_multiple,
    )
    decimals = (
        item.realized_net_pnl,
        item.marked_unrealized_pnl,
        item.total_pnl,
        item.fees,
        item.funding,
        item.total_costs,
        item.closed_net_profit,
        item.closed_net_loss,
        item.summed_r_multiple,
        *(value for value in optional_metrics if value is not None),
    )
    if any(not isinstance(value, Decimal) or not value.is_finite() for value in decimals):
        raise ValueError("setup performance values must be finite Decimals")
    if (item.closed_trade_count == 0) != (
        item.closed_trade_expectancy is None
        and item.closed_trade_win_rate is None
        and item.average_closed_holding_days is None
    ):
        raise ValueError("closed metric availability must match closed trade count")
    if (item.winning_closed_trades == 0) != (item.average_winner is None):
        raise ValueError("average winner availability must match winner count")
    if (item.losing_closed_trades == 0) != (item.average_loser is None):
        raise ValueError("average loser availability must match loser count")
    if item.average_winner is not None and item.average_winner <= 0:
        raise ValueError("average winner must be positive")
    if item.average_loser is not None and item.average_loser >= 0:
        raise ValueError("average loser must be negative")
    if (item.r_multiple_count == 0) != (item.mean_r_multiple is None):
        raise ValueError("mean R availability must match R count")
    if item.profit_factor_status not in PROFIT_FACTOR_STATUSES:
        raise ValueError("profit factor status is unsupported")
    expected_factor, expected_status = _profit_factor(
        closed_count=item.closed_trade_count,
        closed_profit=item.closed_net_profit,
        closed_loss=item.closed_net_loss,
    )
    if (
        item.profit_factor != expected_factor
        or item.profit_factor_status != expected_status
    ):
        raise ValueError("profit factor does not match closed net outcomes")


def _report_id(report: SetupPerformanceReport) -> str:
    return _digest(
        {
            "policy_version": report.policy_version,
            "metric_policy_version": report.metric_policy_version,
            "profit_factor_policy_version": report.profit_factor_policy_version,
            "open_trade_mark_policy_version": report.open_trade_mark_policy_version,
            "source_report_id": report.source_breakdown.report_id,
            "source_evidence_digest": report.source_breakdown.evidence_digest,
        }
    )


def _report_payload(report: SetupPerformanceReport) -> dict[str, Any]:
    return {
        "feature_id": report.feature_id,
        "policy_version": report.policy_version,
        "metric_policy_version": report.metric_policy_version,
        "profit_factor_policy_version": report.profit_factor_policy_version,
        "open_trade_mark_policy_version": report.open_trade_mark_policy_version,
        "report_id": report.report_id,
        "validation_id": report.validation_id,
        "source_breakdown": report.source_breakdown.as_record(),
        "trade_count": report.trade_count,
        "setups": [item.as_record() for item in report.setups],
        "config_metadata": dict(report.config_metadata),
        "reason_codes": list(report.reason_codes),
    }


def _mean(values: Any) -> Decimal:
    resolved = tuple(values)
    if not resolved:
        raise ValueError("mean requires at least one value")
    return _ratio(sum(resolved, Decimal("0")), Decimal(len(resolved)))


def _ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator <= 0:
        raise ValueError("ratio denominator must be positive")
    return (numerator / denominator).quantize(
        PERFORMANCE_RATE_EXPONENT,
        rounding=ROUND_HALF_EVEN,
    )


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    return _json_copy(dict(value))


def _string_mapping(value: Any, name: str) -> dict[str, str]:
    source = _mapping(value, name)
    result: dict[str, str] = {}
    for key, item in source.items():
        result[_string(key, f"{name} key")] = _string(item, f"{name}.{key}")
    return result


def _string_tuple(value: Any, name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{name} must be a sequence")
    return tuple(_string(item, name) for item in value)


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value


def _optional_decimal(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _json_copy(value: Any) -> Any:
    try:
        return json.loads(
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
        )
    except (TypeError, ValueError, InvalidOperation) as exc:
        raise ValueError("evidence must be JSON serializable") from exc
