"""Deterministic strategy-version and parameter-set comparison (BTC-192).

The comparison layer consumes evidence already produced by the authoritative
execution and accounting owners.  It can compare either like-for-like BTC-180
historical backtests or homogeneous BTC-191 paper-trade outcome datasets.  The
two evidence modes are deliberately never blended: historical and paper
results answer different questions and must remain separately inspectable.

Every arm is identified by the persisted ``strategy_version`` and
``parameter_set_id``.  Closed-trade net P&L and R multiples are read from the
source records; they are not reconstructed from prices.  Missing R values stay
missing, and every unavailable comparison delta carries an explicit status.

The report is research evidence only.  It cannot alter strategy configuration
and records BTC-193 as the required promotion boundary.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from typing import Any

from btc_predictor.backtest.engine import BacktestResult, restore_backtest_result
from btc_predictor.research.paper_trade_outcomes import (
    TRADE_OUTCOME_AVAILABLE,
    PaperTradeOutcomeDataset,
    restore_paper_trade_outcome_dataset,
)


STRATEGY_COMPARISON_FEATURE_ID = "STRATEGY_COMPARISON"
STRATEGY_COMPARISON_POLICY_VERSION = "STRATEGY_COMPARISON_FRAMEWORK_V1"
STRATEGY_COMPARISON_METRIC_POLICY_VERSION = "CLOSED_NET_TRADE_OUTCOMES_V1"
STRATEGY_COMPARISON_COMPARABILITY_POLICY_VERSION = (
    "ONE_EVIDENCE_MODE_LIKE_FOR_LIKE_SCOPE_V1"
)
STRATEGY_COMPARISON_DELTA_POLICY_VERSION = "ABSOLUTE_CANDIDATE_MINUS_BASELINE_V1"
STRATEGY_COMPARISON_MISSING_VALUE_POLICY_VERSION = (
    "EXPLICIT_UNAVAILABLE_NO_ZERO_FILL_V1"
)
STRATEGY_COMPARISON_PROMOTION_POLICY_VERSION = "BTC_193_REQUIRED_V1"
STRATEGY_COMPARISON_PRODUCTION_STATUS = "RESEARCH_ONLY_NOT_PRODUCTION"
STRATEGY_COMPARISON_PROMOTION_TICKET = "BTC-193"

HISTORICAL_BACKTEST = "HISTORICAL_BACKTEST"
PAPER_TRADE = "PAPER_TRADE"
STRATEGY_COMPARISON_EVIDENCE_MODES = (HISTORICAL_BACKTEST, PAPER_TRADE)

DELTA_AVAILABLE = "AVAILABLE"
DELTA_BASELINE_UNAVAILABLE = "BASELINE_UNAVAILABLE"
DELTA_CANDIDATE_UNAVAILABLE = "CANDIDATE_UNAVAILABLE"
DELTA_BOTH_UNAVAILABLE = "BOTH_UNAVAILABLE"
STRATEGY_COMPARISON_DELTA_STATUSES = (
    DELTA_AVAILABLE,
    DELTA_BASELINE_UNAVAILABLE,
    DELTA_CANDIDATE_UNAVAILABLE,
    DELTA_BOTH_UNAVAILABLE,
)

PROFIT_FACTOR_AVAILABLE = "AVAILABLE"
PROFIT_FACTOR_NO_MEASURED_TRADES = "NO_MEASURED_TRADES"
PROFIT_FACTOR_NO_LOSSES = "UNBOUNDED_NO_LOSSES"
PROFIT_FACTOR_ALL_FLAT = "UNDEFINED_ALL_FLAT"
STRATEGY_COMPARISON_PROFIT_FACTOR_STATUSES = (
    PROFIT_FACTOR_AVAILABLE,
    PROFIT_FACTOR_NO_MEASURED_TRADES,
    PROFIT_FACTOR_NO_LOSSES,
    PROFIT_FACTOR_ALL_FLAT,
)

CLOSED_TRADE_COUNT_METRIC = "closed_trade_count"
SUMMED_NET_PNL_METRIC = "summed_net_pnl"
CLOSED_TRADE_EXPECTANCY_METRIC = "closed_trade_expectancy"
CLOSED_TRADE_WIN_RATE_METRIC = "closed_trade_win_rate"
PROFIT_FACTOR_METRIC = "profit_factor"
MEAN_R_MULTIPLE_METRIC = "mean_r_multiple"
STRATEGY_COMPARISON_METRICS = (
    CLOSED_TRADE_COUNT_METRIC,
    SUMMED_NET_PNL_METRIC,
    CLOSED_TRADE_EXPECTANCY_METRIC,
    CLOSED_TRADE_WIN_RATE_METRIC,
    PROFIT_FACTOR_METRIC,
    MEAN_R_MULTIPLE_METRIC,
)

STRATEGY_COMPARISON_RATE_EXPONENT = Decimal("1E-12")
STRATEGY_COMPARISON_DECIMAL_PRECISION = 60

STRATEGY_COMPARISON_REASON_CODES = (
    "STRATEGY_COMPARISON_BASELINE_EXPLICIT",
    "STRATEGY_COMPARISON_STRATEGY_VERSIONS",
    "STRATEGY_COMPARISON_PARAMETER_SETS",
    "STRATEGY_COMPARISON_BACKTEST_SCOPE_VERIFIED",
    "STRATEGY_COMPARISON_PAPER_SCOPE_DECLARED",
    "STRATEGY_COMPARISON_CLOSED_OUTCOMES_ONLY",
    "STRATEGY_COMPARISON_MISSING_VALUES_EXPLICIT",
    "STRATEGY_COMPARISON_NO_TRADES",
    "STRATEGY_COMPARISON_UNMEASURED_OUTCOMES",
    "STRATEGY_COMPARISON_RESEARCH_ONLY",
    "STRATEGY_COMPARISON_BTC_193_PROMOTION_REQUIRED",
    "STRATEGY_COMPARISON_COMPLETE",
)


class StrategyComparisonError(ValueError):
    """Raised when evidence violates the BTC-192 comparison contract."""


@dataclass(frozen=True, order=True)
class StrategyVariant:
    """One strategy/configuration identity compared by the framework."""

    strategy_version: str
    parameter_set_id: str

    def __post_init__(self) -> None:
        _non_empty(self.strategy_version, "strategy_version")
        _non_empty(self.parameter_set_id, "parameter_set_id")

    @property
    def variant_id(self) -> str:
        return f"{self.strategy_version}:{self.parameter_set_id}"

    def as_record(self) -> dict[str, str]:
        return {
            "strategy_version": self.strategy_version,
            "parameter_set_id": self.parameter_set_id,
            "variant_id": self.variant_id,
        }


@dataclass(frozen=True)
class StrategyComparisonMetrics:
    """Closed-trade economics for one evidence arm.

    ``trade_count`` still reports open BTC-180 trades, but every quality metric
    is based only on final closed outcomes.  Paper-trade datasets contain final
    outcomes by BTC-191 policy, so their open count is always zero.
    """

    trade_count: int
    closed_trade_count: int
    open_trade_count: int
    measured_net_pnl_count: int
    unmeasured_net_pnl_count: int
    summed_net_pnl: Decimal | None
    closed_trade_expectancy: Decimal | None
    winning_closed_trades: int
    losing_closed_trades: int
    flat_closed_trades: int
    closed_trade_win_rate: Decimal | None
    gross_profit: Decimal | None
    gross_loss: Decimal | None
    profit_factor: Decimal | None
    profit_factor_status: str
    r_multiple_count: int
    unmeasured_r_multiple_count: int
    mean_r_multiple: Decimal | None

    def metric(self, name: str) -> Decimal | None:
        if name == CLOSED_TRADE_COUNT_METRIC:
            return Decimal(self.closed_trade_count)
        if name not in STRATEGY_COMPARISON_METRICS:
            raise KeyError(name)
        value = getattr(self, name)
        if value is not None and not isinstance(value, Decimal):
            raise StrategyComparisonError(f"{name} is not a Decimal metric")
        return value

    def as_record(self) -> dict[str, Any]:
        _validate_metrics(self)
        return {
            "trade_count": self.trade_count,
            "closed_trade_count": self.closed_trade_count,
            "open_trade_count": self.open_trade_count,
            "measured_net_pnl_count": self.measured_net_pnl_count,
            "unmeasured_net_pnl_count": self.unmeasured_net_pnl_count,
            "summed_net_pnl": _optional_decimal(self.summed_net_pnl),
            "closed_trade_expectancy": _optional_decimal(
                self.closed_trade_expectancy
            ),
            "winning_closed_trades": self.winning_closed_trades,
            "losing_closed_trades": self.losing_closed_trades,
            "flat_closed_trades": self.flat_closed_trades,
            "closed_trade_win_rate": _optional_decimal(
                self.closed_trade_win_rate
            ),
            "gross_profit": _optional_decimal(self.gross_profit),
            "gross_loss": _optional_decimal(self.gross_loss),
            "profit_factor": _optional_decimal(self.profit_factor),
            "profit_factor_status": self.profit_factor_status,
            "r_multiple_count": self.r_multiple_count,
            "unmeasured_r_multiple_count": self.unmeasured_r_multiple_count,
            "mean_r_multiple": _optional_decimal(self.mean_r_multiple),
        }


@dataclass(frozen=True)
class StrategyComparisonArm:
    """One immutable source and its strategy-level summary."""

    variant: StrategyVariant
    evidence_mode: str
    evidence_id: str
    source_evidence_digest: str
    config_metadata: dict[str, str]
    source: BacktestResult | PaperTradeOutcomeDataset
    metrics: StrategyComparisonMetrics

    def as_record(self) -> dict[str, Any]:
        _validate_arm(self)
        return {
            "variant": self.variant.as_record(),
            "evidence_mode": self.evidence_mode,
            "evidence_id": self.evidence_id,
            "source_evidence_digest": self.source_evidence_digest,
            "config_metadata": dict(self.config_metadata),
            "source": self.source.as_record(),
            "metrics": self.metrics.as_record(),
        }


@dataclass(frozen=True)
class StrategyMetricDelta:
    """One candidate-minus-baseline absolute metric difference."""

    metric_name: str
    baseline_value: Decimal | None
    candidate_value: Decimal | None
    absolute_delta: Decimal | None
    status: str

    def as_record(self) -> dict[str, Any]:
        _validate_delta(self)
        return {
            "metric_name": self.metric_name,
            "baseline_value": _optional_decimal(self.baseline_value),
            "candidate_value": _optional_decimal(self.candidate_value),
            "absolute_delta": _optional_decimal(self.absolute_delta),
            "status": self.status,
        }


@dataclass(frozen=True)
class StrategyCandidateComparison:
    """All declared deltas for one candidate relative to the baseline."""

    candidate: StrategyVariant
    evidence_id: str
    deltas: tuple[StrategyMetricDelta, ...]

    def delta(self, metric_name: str) -> StrategyMetricDelta:
        for item in self.deltas:
            if item.metric_name == metric_name:
                return item
        raise KeyError(metric_name)

    def as_record(self) -> dict[str, Any]:
        _validate_candidate_comparison(self)
        return {
            "candidate": self.candidate.as_record(),
            "evidence_id": self.evidence_id,
            "deltas": [item.as_record() for item in self.deltas],
        }


@dataclass(frozen=True)
class StrategyComparisonReport:
    """Replayable BTC-192 baseline-versus-candidates research evidence."""

    feature_id: str
    policy_version: str
    metric_policy_version: str
    comparability_policy_version: str
    delta_policy_version: str
    missing_value_policy_version: str
    comparison_id: str
    evidence_digest: str
    evidence_mode: str
    comparison_scope_id: str
    baseline: StrategyVariant
    arms: tuple[StrategyComparisonArm, ...]
    comparisons: tuple[StrategyCandidateComparison, ...]
    production_status: str
    promotion_policy_version: str
    promotion_ticket: str
    reason_codes: tuple[str, ...]

    def arm(
        self, strategy_version: str, parameter_set_id: str
    ) -> StrategyComparisonArm:
        wanted = StrategyVariant(strategy_version, parameter_set_id)
        for item in self.arms:
            if item.variant == wanted:
                return item
        raise KeyError(wanted.variant_id)

    @property
    def baseline_arm(self) -> StrategyComparisonArm:
        return self.arm(
            self.baseline.strategy_version, self.baseline.parameter_set_id
        )

    def comparison(
        self, strategy_version: str, parameter_set_id: str
    ) -> StrategyCandidateComparison:
        wanted = StrategyVariant(strategy_version, parameter_set_id)
        for item in self.comparisons:
            if item.candidate == wanted:
                return item
        raise KeyError(wanted.variant_id)

    def as_record(self) -> dict[str, Any]:
        _validate_report(self)
        payload = _report_payload(self)
        if _digest(payload) != self.evidence_digest:
            raise StrategyComparisonError(
                "strategy comparison evidence does not match digest"
            )
        return {**payload, "evidence_digest": self.evidence_digest}


def compare_backtest_strategies(
    results: Sequence[BacktestResult],
    *,
    baseline_strategy_version: str,
    baseline_parameter_set_id: str,
) -> StrategyComparisonReport:
    """Compare BTC-180 runs over the exact same bars, capital, and costs."""

    sources = tuple(results)
    if any(not isinstance(item, BacktestResult) for item in sources):
        raise TypeError("results must contain BacktestResult values")
    if len(sources) < 2:
        raise StrategyComparisonError("at least two backtest results are required")
    for item in sources:
        item.as_record()
    signatures = tuple(_backtest_scope_signature(item) for item in sources)
    if any(item != signatures[0] for item in signatures[1:]):
        raise StrategyComparisonError(
            "backtest arms must share bars, symbol, period, capital, and costs"
        )
    scope_id = f"backtest-scope-{_digest(signatures[0])[:24]}"
    arms = tuple(_backtest_arm(item) for item in sources)
    return _build_report(
        arms,
        evidence_mode=HISTORICAL_BACKTEST,
        comparison_scope_id=scope_id,
        baseline=StrategyVariant(
            baseline_strategy_version, baseline_parameter_set_id
        ),
    )


def compare_paper_trade_strategies(
    datasets: Sequence[PaperTradeOutcomeDataset],
    *,
    comparison_scope_id: str,
    baseline_strategy_version: str,
    baseline_parameter_set_id: str,
) -> StrategyComparisonReport:
    """Compare BTC-191 datasets from one caller-declared paper-trade scope.

    BTC-191 records completed entries but not the full set of opportunities a
    strategy observed.  The caller must therefore identify the common paper
    evaluation window/campaign explicitly.  Extraction time and accounting
    conventions are additionally checked here.
    """

    sources = tuple(datasets)
    if any(not isinstance(item, PaperTradeOutcomeDataset) for item in sources):
        raise TypeError("datasets must contain PaperTradeOutcomeDataset values")
    if len(sources) < 2:
        raise StrategyComparisonError(
            "at least two paper-trade outcome datasets are required"
        )
    scope = _non_empty(comparison_scope_id, "comparison_scope_id")
    for item in sources:
        item.as_record()
    signatures = tuple(_paper_scope_signature(item) for item in sources)
    if any(item != signatures[0] for item in signatures[1:]):
        raise StrategyComparisonError(
            "paper-trade arms must share extraction time and accounting conventions"
        )
    arms = tuple(_paper_arm(item) for item in sources)
    return _build_report(
        arms,
        evidence_mode=PAPER_TRADE,
        comparison_scope_id=scope,
        baseline=StrategyVariant(
            baseline_strategy_version, baseline_parameter_set_id
        ),
    )


def compare_strategies(
    evidence: Sequence[BacktestResult | PaperTradeOutcomeDataset],
    *,
    baseline_strategy_version: str,
    baseline_parameter_set_id: str,
    comparison_scope_id: str | None = None,
) -> StrategyComparisonReport:
    """Dispatch a homogeneous evidence sequence to the appropriate owner."""

    sources = tuple(evidence)
    if not sources:
        raise StrategyComparisonError("at least two evidence sources are required")
    if all(isinstance(item, BacktestResult) for item in sources):
        if comparison_scope_id is not None:
            raise StrategyComparisonError(
                "backtest comparison scope is derived; do not declare one"
            )
        return compare_backtest_strategies(
            sources,  # type: ignore[arg-type]
            baseline_strategy_version=baseline_strategy_version,
            baseline_parameter_set_id=baseline_parameter_set_id,
        )
    if all(isinstance(item, PaperTradeOutcomeDataset) for item in sources):
        if comparison_scope_id is None:
            raise StrategyComparisonError(
                "paper-trade comparisons require comparison_scope_id"
            )
        return compare_paper_trade_strategies(
            sources,  # type: ignore[arg-type]
            comparison_scope_id=comparison_scope_id,
            baseline_strategy_version=baseline_strategy_version,
            baseline_parameter_set_id=baseline_parameter_set_id,
        )
    raise StrategyComparisonError(
        "comparison evidence must use exactly one evidence mode"
    )


def restore_strategy_comparison_report(
    record: Mapping[str, Any],
) -> StrategyComparisonReport:
    """Restore a persisted comparison and reject source or metric tampering."""

    source = _mapping(record, "record")
    mode = _string(source.get("evidence_mode"), "evidence_mode")
    arm_records = _sequence(source.get("arms"), "arms")
    if mode == HISTORICAL_BACKTEST:
        evidence: tuple[BacktestResult | PaperTradeOutcomeDataset, ...] = tuple(
            restore_backtest_result(
                _mapping(_mapping(item, "arm").get("source"), "arm.source")
            )
            for item in arm_records
        )
        scope: str | None = None
    elif mode == PAPER_TRADE:
        evidence = tuple(
            restore_paper_trade_outcome_dataset(
                _mapping(_mapping(item, "arm").get("source"), "arm.source")
            )
            for item in arm_records
        )
        scope = _string(source.get("comparison_scope_id"), "comparison_scope_id")
    else:
        raise StrategyComparisonError(
            f"evidence_mode must be one of {STRATEGY_COMPARISON_EVIDENCE_MODES}"
        )
    baseline_record = _mapping(source.get("baseline"), "baseline")
    rebuilt = compare_strategies(
        evidence,
        baseline_strategy_version=_string(
            baseline_record.get("strategy_version"), "baseline.strategy_version"
        ),
        baseline_parameter_set_id=_string(
            baseline_record.get("parameter_set_id"), "baseline.parameter_set_id"
        ),
        comparison_scope_id=scope,
    )
    if rebuilt.as_record() != dict(source):
        raise StrategyComparisonError(
            "record does not match reconstructed strategy comparison"
        )
    return rebuilt


def _build_report(
    arms: tuple[StrategyComparisonArm, ...],
    *,
    evidence_mode: str,
    comparison_scope_id: str,
    baseline: StrategyVariant,
) -> StrategyComparisonReport:
    _member(evidence_mode, STRATEGY_COMPARISON_EVIDENCE_MODES, "evidence_mode")
    identities = tuple(item.variant for item in arms)
    if len(set(identities)) != len(identities):
        raise StrategyComparisonError(
            "each strategy_version/parameter_set_id arm must be unique"
        )
    evidence_ids = tuple(item.evidence_id for item in arms)
    if len(set(evidence_ids)) != len(evidence_ids):
        raise StrategyComparisonError("comparison evidence IDs must be unique")
    if baseline not in identities:
        raise StrategyComparisonError(
            f"baseline variant {baseline.variant_id!r} is not present"
        )
    by_variant = {item.variant: item for item in arms}
    ordered_variants = (baseline,) + tuple(
        sorted(item for item in identities if item != baseline)
    )
    ordered_arms = tuple(by_variant[item] for item in ordered_variants)
    baseline_arm = ordered_arms[0]
    comparisons = tuple(
        StrategyCandidateComparison(
            candidate=item.variant,
            evidence_id=item.evidence_id,
            deltas=tuple(
                _metric_delta(
                    name,
                    baseline_arm.metrics.metric(name),
                    item.metrics.metric(name),
                )
                for name in STRATEGY_COMPARISON_METRICS
            ),
        )
        for item in ordered_arms[1:]
    )
    report = StrategyComparisonReport(
        feature_id=STRATEGY_COMPARISON_FEATURE_ID,
        policy_version=STRATEGY_COMPARISON_POLICY_VERSION,
        metric_policy_version=STRATEGY_COMPARISON_METRIC_POLICY_VERSION,
        comparability_policy_version=(
            STRATEGY_COMPARISON_COMPARABILITY_POLICY_VERSION
        ),
        delta_policy_version=STRATEGY_COMPARISON_DELTA_POLICY_VERSION,
        missing_value_policy_version=(
            STRATEGY_COMPARISON_MISSING_VALUE_POLICY_VERSION
        ),
        comparison_id="",
        evidence_digest="",
        evidence_mode=evidence_mode,
        comparison_scope_id=comparison_scope_id,
        baseline=baseline,
        arms=ordered_arms,
        comparisons=comparisons,
        production_status=STRATEGY_COMPARISON_PRODUCTION_STATUS,
        promotion_policy_version=STRATEGY_COMPARISON_PROMOTION_POLICY_VERSION,
        promotion_ticket=STRATEGY_COMPARISON_PROMOTION_TICKET,
        reason_codes=_reason_codes(ordered_arms, evidence_mode=evidence_mode),
    )
    report = replace(report, comparison_id=_comparison_id(report))
    _validate_report(report, allow_empty_digest=True)
    return replace(report, evidence_digest=_digest(_report_payload(report)))


def _backtest_arm(result: BacktestResult) -> StrategyComparisonArm:
    metadata = _string_mapping(result.config_metadata, "config_metadata")
    variant = _variant_from_metadata(metadata)
    closed = tuple(item for item in result.trades if item.closed)
    return StrategyComparisonArm(
        variant=variant,
        evidence_mode=HISTORICAL_BACKTEST,
        evidence_id=result.run_id,
        source_evidence_digest=result.evidence_digest,
        config_metadata=metadata,
        source=result,
        metrics=_metrics(
            trade_count=len(result.trades),
            closed_trade_count=len(closed),
            net_values=tuple(item.net_pnl for item in closed),
            r_values=tuple(item.r_multiple for item in closed),
        ),
    )


def _paper_arm(dataset: PaperTradeOutcomeDataset) -> StrategyComparisonArm:
    metadata = _string_mapping(dataset.config_metadata, "config_metadata")
    variant = _variant_from_metadata(metadata)
    net_values = tuple(_paper_outcome(row, "net_pnl") for row in dataset.rows)
    r_values = tuple(_paper_outcome(row, "r_multiple") for row in dataset.rows)
    return StrategyComparisonArm(
        variant=variant,
        evidence_mode=PAPER_TRADE,
        evidence_id=dataset.dataset_id,
        source_evidence_digest=dataset.evidence_digest,
        config_metadata=metadata,
        source=dataset,
        metrics=_metrics(
            trade_count=len(dataset.rows),
            closed_trade_count=len(dataset.rows),
            net_values=net_values,
            r_values=r_values,
        ),
    )


def _paper_outcome(row: Any, name: str) -> Decimal | None:
    try:
        outcome = row.outcome(name)
    except KeyError:
        return None
    return outcome.value if outcome.status == TRADE_OUTCOME_AVAILABLE else None


def _metrics(
    *,
    trade_count: int,
    closed_trade_count: int,
    net_values: Sequence[Decimal | None],
    r_values: Sequence[Decimal | None],
) -> StrategyComparisonMetrics:
    measured_net = tuple(item for item in net_values if item is not None)
    measured_r = tuple(item for item in r_values if item is not None)
    winners = tuple(item for item in measured_net if item > 0)
    losers = tuple(item for item in measured_net if item < 0)
    flats = tuple(item for item in measured_net if item == 0)
    gross_profit = _sum(winners) if measured_net else None
    gross_loss = _sum(losers) if measured_net else None
    profit_factor, profit_factor_status = _profit_factor(
        measured_count=len(measured_net),
        gross_profit=gross_profit,
        gross_loss=gross_loss,
    )
    metrics = StrategyComparisonMetrics(
        trade_count=trade_count,
        closed_trade_count=closed_trade_count,
        open_trade_count=trade_count - closed_trade_count,
        measured_net_pnl_count=len(measured_net),
        unmeasured_net_pnl_count=closed_trade_count - len(measured_net),
        summed_net_pnl=_sum(measured_net) if measured_net else None,
        closed_trade_expectancy=_mean(measured_net),
        winning_closed_trades=len(winners),
        losing_closed_trades=len(losers),
        flat_closed_trades=len(flats),
        closed_trade_win_rate=(
            _ratio(Decimal(len(winners)), Decimal(len(measured_net)))
            if measured_net
            else None
        ),
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=profit_factor,
        profit_factor_status=profit_factor_status,
        r_multiple_count=len(measured_r),
        unmeasured_r_multiple_count=closed_trade_count - len(measured_r),
        mean_r_multiple=_mean(measured_r),
    )
    _validate_metrics(metrics)
    return metrics


def _profit_factor(
    *,
    measured_count: int,
    gross_profit: Decimal | None,
    gross_loss: Decimal | None,
) -> tuple[Decimal | None, str]:
    if measured_count == 0:
        return None, PROFIT_FACTOR_NO_MEASURED_TRADES
    assert gross_profit is not None and gross_loss is not None
    if gross_loss < 0:
        return _ratio(gross_profit, abs(gross_loss)), PROFIT_FACTOR_AVAILABLE
    if gross_profit > 0:
        return None, PROFIT_FACTOR_NO_LOSSES
    return None, PROFIT_FACTOR_ALL_FLAT


def _metric_delta(
    name: str,
    baseline_value: Decimal | None,
    candidate_value: Decimal | None,
) -> StrategyMetricDelta:
    if baseline_value is None and candidate_value is None:
        status = DELTA_BOTH_UNAVAILABLE
    elif baseline_value is None:
        status = DELTA_BASELINE_UNAVAILABLE
    elif candidate_value is None:
        status = DELTA_CANDIDATE_UNAVAILABLE
    else:
        status = DELTA_AVAILABLE
    return StrategyMetricDelta(
        metric_name=name,
        baseline_value=baseline_value,
        candidate_value=candidate_value,
        absolute_delta=_difference(candidate_value, baseline_value),
        status=status,
    )


def _backtest_scope_signature(result: BacktestResult) -> dict[str, Any]:
    return {
        "input_digest": result.input_digest,
        "symbol": result.symbol,
        "started_at": _optional_time(result.started_at),
        "ended_at": _optional_time(result.ended_at),
        "bar_count": result.bar_count,
        "starting_nav": str(result.starting_nav),
        "effective_costs": result.effective_costs.as_record(),
        "cost_profile_name": (
            result.cost_profile.name if result.cost_profile is not None else None
        ),
    }


def _paper_scope_signature(dataset: PaperTradeOutcomeDataset) -> dict[str, Any]:
    return {
        "extraction_time": dataset.extraction_time.isoformat(),
        "accounting_policy_version": dataset.accounting_policy_version,
        "r_multiple_convention": dataset.r_multiple_convention,
        "funding_convention": dataset.funding_convention,
        "excursion_convention": dataset.excursion_convention,
        "maximum_size_convention": dataset.maximum_size_convention,
    }


def _variant_from_metadata(metadata: Mapping[str, str]) -> StrategyVariant:
    return StrategyVariant(
        _string(metadata.get("strategy_version"), "config strategy_version"),
        _string(metadata.get("parameter_set_id"), "config parameter_set_id"),
    )


def _reason_codes(
    arms: tuple[StrategyComparisonArm, ...], *, evidence_mode: str
) -> tuple[str, ...]:
    codes = ["STRATEGY_COMPARISON_BASELINE_EXPLICIT"]
    if len({item.variant.strategy_version for item in arms}) > 1:
        codes.append("STRATEGY_COMPARISON_STRATEGY_VERSIONS")
    if len({item.variant.parameter_set_id for item in arms}) > 1:
        codes.append("STRATEGY_COMPARISON_PARAMETER_SETS")
    codes.append(
        "STRATEGY_COMPARISON_BACKTEST_SCOPE_VERIFIED"
        if evidence_mode == HISTORICAL_BACKTEST
        else "STRATEGY_COMPARISON_PAPER_SCOPE_DECLARED"
    )
    codes.extend(
        (
            "STRATEGY_COMPARISON_CLOSED_OUTCOMES_ONLY",
            "STRATEGY_COMPARISON_MISSING_VALUES_EXPLICIT",
        )
    )
    if any(item.metrics.closed_trade_count == 0 for item in arms):
        codes.append("STRATEGY_COMPARISON_NO_TRADES")
    if any(
        item.metrics.unmeasured_net_pnl_count
        or item.metrics.unmeasured_r_multiple_count
        for item in arms
    ):
        codes.append("STRATEGY_COMPARISON_UNMEASURED_OUTCOMES")
    codes.extend(
        (
            "STRATEGY_COMPARISON_RESEARCH_ONLY",
            "STRATEGY_COMPARISON_BTC_193_PROMOTION_REQUIRED",
            "STRATEGY_COMPARISON_COMPLETE",
        )
    )
    return tuple(codes)


def _validate_report(
    report: StrategyComparisonReport, *, allow_empty_digest: bool = False
) -> None:
    expected = {
        "feature_id": STRATEGY_COMPARISON_FEATURE_ID,
        "policy_version": STRATEGY_COMPARISON_POLICY_VERSION,
        "metric_policy_version": STRATEGY_COMPARISON_METRIC_POLICY_VERSION,
        "comparability_policy_version": (
            STRATEGY_COMPARISON_COMPARABILITY_POLICY_VERSION
        ),
        "delta_policy_version": STRATEGY_COMPARISON_DELTA_POLICY_VERSION,
        "missing_value_policy_version": (
            STRATEGY_COMPARISON_MISSING_VALUE_POLICY_VERSION
        ),
        "production_status": STRATEGY_COMPARISON_PRODUCTION_STATUS,
        "promotion_policy_version": STRATEGY_COMPARISON_PROMOTION_POLICY_VERSION,
        "promotion_ticket": STRATEGY_COMPARISON_PROMOTION_TICKET,
    }
    for name, value in expected.items():
        if getattr(report, name) != value:
            raise StrategyComparisonError(f"{name} must be {value!r}")
    _member(
        report.evidence_mode,
        STRATEGY_COMPARISON_EVIDENCE_MODES,
        "evidence_mode",
    )
    _non_empty(report.comparison_scope_id, "comparison_scope_id")
    _non_empty(report.comparison_id, "comparison_id")
    if report.comparison_id != _comparison_id(report):
        raise StrategyComparisonError("comparison does not match comparison_id")
    if not allow_empty_digest:
        _non_empty(report.evidence_digest, "evidence_digest")
    if len(report.arms) < 2:
        raise StrategyComparisonError("a comparison requires at least two arms")
    if report.arms[0].variant != report.baseline:
        raise StrategyComparisonError("the baseline must be the first arm")
    if any(item.evidence_mode != report.evidence_mode for item in report.arms):
        raise StrategyComparisonError("all arms must use the report evidence mode")
    for item in report.arms:
        _validate_arm(item)
    variants = tuple(item.variant for item in report.arms)
    if len(set(variants)) != len(variants):
        raise StrategyComparisonError("comparison variants must be unique")
    expected_candidates = variants[1:]
    if tuple(item.candidate for item in report.comparisons) != expected_candidates:
        raise StrategyComparisonError("candidate comparisons do not match arms")
    baseline_metrics = report.arms[0].metrics
    for item, arm in zip(report.comparisons, report.arms[1:], strict=True):
        _validate_candidate_comparison(item)
        if item.evidence_id != arm.evidence_id:
            raise StrategyComparisonError(
                "candidate comparison evidence_id does not match its arm"
            )
        expected_deltas = tuple(
            _metric_delta(
                name, baseline_metrics.metric(name), arm.metrics.metric(name)
            )
            for name in STRATEGY_COMPARISON_METRICS
        )
        if item.deltas != expected_deltas:
            raise StrategyComparisonError(
                "candidate deltas do not match baseline and arm metrics"
            )
    expected_reasons = _reason_codes(report.arms, evidence_mode=report.evidence_mode)
    if report.reason_codes != expected_reasons:
        raise StrategyComparisonError("reason_codes do not match comparison evidence")


def _validate_arm(arm: StrategyComparisonArm) -> None:
    _member(arm.evidence_mode, STRATEGY_COMPARISON_EVIDENCE_MODES, "evidence_mode")
    _non_empty(arm.evidence_id, "evidence_id")
    _non_empty(arm.source_evidence_digest, "source_evidence_digest")
    metadata = _string_mapping(arm.config_metadata, "config_metadata")
    if _variant_from_metadata(metadata) != arm.variant:
        raise StrategyComparisonError("arm variant does not match config metadata")
    if isinstance(arm.source, BacktestResult):
        expected_mode = HISTORICAL_BACKTEST
        expected_id = arm.source.run_id
    elif isinstance(arm.source, PaperTradeOutcomeDataset):
        expected_mode = PAPER_TRADE
        expected_id = arm.source.dataset_id
    else:
        raise TypeError("arm source must be BTC-180 or BTC-191 evidence")
    arm.source.as_record()
    if arm.evidence_mode != expected_mode:
        raise StrategyComparisonError("arm evidence mode does not match source")
    if arm.evidence_id != expected_id:
        raise StrategyComparisonError("arm evidence_id does not match source")
    if arm.source_evidence_digest != arm.source.evidence_digest:
        raise StrategyComparisonError("arm source digest does not match source")
    if arm.config_metadata != arm.source.config_metadata:
        raise StrategyComparisonError("arm config metadata does not match source")
    expected = (
        _backtest_arm(arm.source).metrics
        if isinstance(arm.source, BacktestResult)
        else _paper_arm(arm.source).metrics
    )
    if arm.metrics != expected:
        raise StrategyComparisonError("arm metrics do not match source evidence")


def _validate_metrics(metrics: StrategyComparisonMetrics) -> None:
    count_fields = (
        "trade_count",
        "closed_trade_count",
        "open_trade_count",
        "measured_net_pnl_count",
        "unmeasured_net_pnl_count",
        "winning_closed_trades",
        "losing_closed_trades",
        "flat_closed_trades",
        "r_multiple_count",
        "unmeasured_r_multiple_count",
    )
    for name in count_fields:
        _non_negative_integer(getattr(metrics, name), name)
    if metrics.trade_count != metrics.closed_trade_count + metrics.open_trade_count:
        raise StrategyComparisonError("trade counts do not reconcile")
    if metrics.closed_trade_count != (
        metrics.measured_net_pnl_count + metrics.unmeasured_net_pnl_count
    ):
        raise StrategyComparisonError("net P&L coverage does not reconcile")
    if metrics.closed_trade_count != (
        metrics.r_multiple_count + metrics.unmeasured_r_multiple_count
    ):
        raise StrategyComparisonError("R-multiple coverage does not reconcile")
    if metrics.measured_net_pnl_count != (
        metrics.winning_closed_trades
        + metrics.losing_closed_trades
        + metrics.flat_closed_trades
    ):
        raise StrategyComparisonError("measured closed outcomes do not reconcile")
    for name in (
        "summed_net_pnl",
        "closed_trade_expectancy",
        "closed_trade_win_rate",
        "gross_profit",
        "gross_loss",
        "profit_factor",
        "mean_r_multiple",
    ):
        _optional_finite_decimal(getattr(metrics, name), name)
    measured = metrics.measured_net_pnl_count > 0
    for name in (
        "summed_net_pnl",
        "closed_trade_expectancy",
        "closed_trade_win_rate",
        "gross_profit",
        "gross_loss",
    ):
        if (getattr(metrics, name) is not None) != measured:
            raise StrategyComparisonError(
                f"{name} must be available exactly when net P&L is measured"
            )
    if metrics.closed_trade_win_rate is not None and not (
        Decimal("0") <= metrics.closed_trade_win_rate <= Decimal("1")
    ):
        raise StrategyComparisonError("closed_trade_win_rate must be in [0, 1]")
    _member(
        metrics.profit_factor_status,
        STRATEGY_COMPARISON_PROFIT_FACTOR_STATUSES,
        "profit_factor_status",
    )
    if (metrics.profit_factor is not None) != (
        metrics.profit_factor_status == PROFIT_FACTOR_AVAILABLE
    ):
        raise StrategyComparisonError(
            "profit_factor availability does not match its status"
        )
    if (metrics.mean_r_multiple is not None) != (metrics.r_multiple_count > 0):
        raise StrategyComparisonError(
            "mean_r_multiple must be available exactly when R is measured"
        )


def _validate_delta(delta: StrategyMetricDelta) -> None:
    _member(delta.metric_name, STRATEGY_COMPARISON_METRICS, "metric_name")
    _member(delta.status, STRATEGY_COMPARISON_DELTA_STATUSES, "status")
    for name in ("baseline_value", "candidate_value", "absolute_delta"):
        _optional_finite_decimal(getattr(delta, name), name)
    expected = _metric_delta(
        delta.metric_name, delta.baseline_value, delta.candidate_value
    )
    if delta != expected:
        raise StrategyComparisonError("metric delta does not match its values")


def _validate_candidate_comparison(item: StrategyCandidateComparison) -> None:
    _non_empty(item.evidence_id, "evidence_id")
    if tuple(delta.metric_name for delta in item.deltas) != STRATEGY_COMPARISON_METRICS:
        raise StrategyComparisonError("candidate deltas must use the metric contract")
    for delta in item.deltas:
        _validate_delta(delta)


def _comparison_id(report: StrategyComparisonReport) -> str:
    return "strategy-comparison-" + _digest(
        {
            "policy_version": report.policy_version,
            "evidence_mode": report.evidence_mode,
            "comparison_scope_id": report.comparison_scope_id,
            "baseline": report.baseline.as_record(),
            "evidence_ids": [item.evidence_id for item in report.arms],
        }
    )[:24]


def _report_payload(report: StrategyComparisonReport) -> dict[str, Any]:
    return {
        "feature_id": report.feature_id,
        "policy_version": report.policy_version,
        "metric_policy_version": report.metric_policy_version,
        "comparability_policy_version": report.comparability_policy_version,
        "delta_policy_version": report.delta_policy_version,
        "missing_value_policy_version": report.missing_value_policy_version,
        "comparison_id": report.comparison_id,
        "evidence_mode": report.evidence_mode,
        "comparison_scope_id": report.comparison_scope_id,
        "baseline": report.baseline.as_record(),
        "arms": [item.as_record() for item in report.arms],
        "comparisons": [item.as_record() for item in report.comparisons],
        "production_status": report.production_status,
        "promotion_policy_version": report.promotion_policy_version,
        "promotion_ticket": report.promotion_ticket,
        "reason_codes": list(report.reason_codes),
    }


def _mean(values: Sequence[Decimal]) -> Decimal | None:
    if not values:
        return None
    with localcontext(Context(prec=STRATEGY_COMPARISON_DECIMAL_PRECISION)):
        return (_sum(values) / Decimal(len(values))).quantize(
            STRATEGY_COMPARISON_RATE_EXPONENT, rounding=ROUND_HALF_EVEN
        )


def _sum(values: Sequence[Decimal]) -> Decimal:
    with localcontext(Context(prec=STRATEGY_COMPARISON_DECIMAL_PRECISION)):
        return sum(values, Decimal("0"))


def _difference(
    candidate_value: Decimal | None, baseline_value: Decimal | None
) -> Decimal | None:
    if candidate_value is None or baseline_value is None:
        return None
    with localcontext(Context(prec=STRATEGY_COMPARISON_DECIMAL_PRECISION)):
        return candidate_value - baseline_value


def _ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    with localcontext(Context(prec=STRATEGY_COMPARISON_DECIMAL_PRECISION)):
        return (numerator / denominator).quantize(
            STRATEGY_COMPARISON_RATE_EXPONENT, rounding=ROUND_HALF_EVEN
        )


def _digest(payload: Any) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _optional_decimal(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _optional_time(value: Any | None) -> str | None:
    return None if value is None else value.isoformat()


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    return dict(value)


def _sequence(value: Any, name: str) -> tuple[Any, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError(f"{name} must be a sequence")
    return tuple(value)


def _string_mapping(value: Any, name: str) -> dict[str, str]:
    source = _mapping(value, name)
    if any(
        not isinstance(key, str) or not isinstance(item, str)
        for key, item in source.items()
    ):
        raise TypeError(f"{name} keys and values must be strings")
    return source


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StrategyComparisonError(f"{name} must not be empty")
    return value


def _non_empty(value: Any, name: str) -> str:
    return _string(value, name)


def _member(value: str, choices: Sequence[str], name: str) -> str:
    if value not in choices:
        raise StrategyComparisonError(f"{name} must be one of {tuple(choices)}")
    return value


def _non_negative_integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise StrategyComparisonError(f"{name} must be a non-negative integer")
    return value


def _optional_finite_decimal(value: Any, name: str) -> None:
    if value is None:
        return
    if not isinstance(value, Decimal) or not value.is_finite():
        raise StrategyComparisonError(f"{name} must be a finite Decimal or None")

