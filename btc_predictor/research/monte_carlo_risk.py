"""Monte Carlo portfolio risk analysis (BTC-187).

A realized equity curve is one draw from the strategy's outcome distribution.
Judging a risk budget by it answers "what did happen" when the question is
"what could plausibly happen".  This module resamples the *observed* trade
outcomes -- BTC-191 paper-trade rows or the completed trades of a BTC-180
backtest -- into many alternative portfolio paths and reports the distribution
of what those paths did:

``ending_nav`` / ``ending_nav_fraction`` / ``total_return_fraction``
    where the account finished;
``max_drawdown_fraction``
    the worst peak-to-trough decline along the path;
``longest_losing_streak``
    the longest run of consecutive losing trades;
``calmar_ratio``
    path total return over that drawdown; and
``trades_taken``
    how many trades the path survived to take.

Every metric is reported as a percentile distribution rather than an average,
together with the exceedance probabilities the ticket names (drawdown worse
than 10% and 15% by default) and the risk-of-ruin tail: the share of paths that
hit the declared ruin level and stopped.

Outcomes enter in risk units, not currency.  Under the ``r_multiple`` basis a
trade's outcome is the BTC-165 R multiple (``INITIAL_PLANNED_RISK_V1``), so a
risk-per-trade schedule of ``f`` moves NAV by ``f * R`` -- exactly the Rulebook
17 / BTC-144 notion of risking a fraction of NAV at the stop.  Under the
``net_return_fraction`` basis a trade's outcome is its net P&L over entry
notional, and the same declared fraction means capital *deployed* rather than
capital risked: that is constant-notional allocation, a different sizing
question, and the two bases are not interchangeable.

Schedules are compared on identical resampled paths (common random numbers), so
a difference between two risk budgets is the budget rather than sampling noise.

Nothing is zero-filled.  A trade whose basis outcome BTC-165 could not measure
is excluded by name, carrying the reason code that explains it, and the report
counts those exclusions.

The analysis is research evidence used to *challenge* a risk budget.  It has no
strategy or configuration mutation path and records BTC-193 as the required
promotion boundary.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import ROUND_HALF_EVEN, Context, Decimal, InvalidOperation, localcontext
from typing import Any

from btc_predictor.backtest.engine import BacktestResult
from btc_predictor.config.strategy import StrategyConfig
from btc_predictor.data import require_utc_datetime
from btc_predictor.portfolio.accounting import (
    PAPER_TRADE_ACCOUNTING_POLICY_VERSION,
    R_MULTIPLE_CONVENTION,
    PaperTradeAccounting,
)
from btc_predictor.quant.simulation import (
    PERMUTATION_INDEX_POLICY_VERSION,
    UNIFORM_INDEX_POLICY_VERSION,
    permutation_index_samples,
    uniform_index_samples,
)
from btc_predictor.research.paper_trade_outcomes import (
    PAPER_TRADE_OUTCOME_POLICY_VERSION,
    TRADE_OUTCOME_AVAILABLE,
    PaperTradeOutcomeDataset,
)
from btc_predictor.risk.budget import risk_schedule_from_config


MONTE_CARLO_FEATURE_ID = "MONTE_CARLO_PORTFOLIO_RISK"
MONTE_CARLO_POLICY_VERSION = "MONTE_CARLO_PORTFOLIO_RISK_V1"
MONTE_CARLO_SAMPLE_POLICY_VERSION = "CLOSED_TRADE_OUTCOME_SAMPLES_V1"
MONTE_CARLO_PATH_POLICY_VERSION = "FIXED_FRACTIONAL_COMPOUNDING_V1"
MONTE_CARLO_DRAWDOWN_POLICY_VERSION = "PATH_PEAK_TO_TROUGH_NAV_DRAWDOWN_V1"
MONTE_CARLO_CALMAR_POLICY_VERSION = "PATH_TOTAL_RETURN_OVER_MAX_DRAWDOWN_V1"
MONTE_CARLO_PERCENTILE_POLICY_VERSION = "NEAREST_RANK_PERCENTILE_V1"
MONTE_CARLO_RUIN_POLICY_VERSION = "RUIN_STOPS_THE_PATH_V1"
MONTE_CARLO_COMMON_PATHS_POLICY_VERSION = "COMMON_RESAMPLED_PATHS_ACROSS_SCHEDULES_V1"
MONTE_CARLO_MISSING_VALUE_POLICY_VERSION = "EXPLICIT_EXCLUSION_NO_ZERO_FILL_V1"
MONTE_CARLO_PROMOTION_POLICY_VERSION = "BTC_193_REQUIRED_V1"
MONTE_CARLO_PRODUCTION_STATUS = "RESEARCH_ONLY_NOT_PRODUCTION"
MONTE_CARLO_PROMOTION_TICKET = "BTC-193"
MONTE_CARLO_RISK_BUDGET_STATUS = "RESEARCH_CHALLENGE_ONLY_NO_AUTOMATIC_CHANGE"

# Both bases measure one closed trade; the basis decides what a schedule's
# declared fraction of NAV means, so they are never mixed inside one analysis.
R_MULTIPLE_BASIS = "r_multiple"
NET_RETURN_BASIS = "net_return_fraction"
MONTE_CARLO_OUTCOME_BASES = (R_MULTIPLE_BASIS, NET_RETURN_BASIS)
NET_RETURN_CONVENTION = "NET_PNL_OVER_ENTRY_NOTIONAL_V1"
RISK_FRACTION_SCALING = "RISK_FRACTION_OF_NAV_AT_STOP_V1"
NOTIONAL_FRACTION_SCALING = "NOTIONAL_FRACTION_OF_NAV_V1"
SCHEDULE_SCALING_POLICY_VERSIONS = {
    R_MULTIPLE_BASIS: RISK_FRACTION_SCALING,
    NET_RETURN_BASIS: NOTIONAL_FRACTION_SCALING,
}

IID_BOOTSTRAP = "iid_bootstrap"
ORDER_PERMUTATION = "order_permutation"
MONTE_CARLO_RESAMPLING_METHODS = (IID_BOOTSTRAP, ORDER_PERMUTATION)
RESAMPLING_POLICY_VERSIONS = {
    IID_BOOTSTRAP: "IID_BOOTSTRAP_WITH_REPLACEMENT_V1",
    ORDER_PERMUTATION: "PERMUTATION_WITHOUT_REPLACEMENT_V1",
}
RANDOM_STREAM_POLICY_VERSIONS = {
    IID_BOOTSTRAP: UNIFORM_INDEX_POLICY_VERSION,
    ORDER_PERMUTATION: PERMUTATION_INDEX_POLICY_VERSION,
}

SCHEDULE_SOURCE_CALLER = "CALLER_DECLARED"
SCHEDULE_SOURCE_CONFIG_BAND = "STRATEGY_CONFIG_RISK_SCHEDULE_BAND"
SCHEDULE_SOURCE_CONFIG_MAXIMUM = "STRATEGY_CONFIG_MAX_RISK_AT_STOP"
SCHEDULE_SOURCES = (
    SCHEDULE_SOURCE_CALLER,
    SCHEDULE_SOURCE_CONFIG_BAND,
    SCHEDULE_SOURCE_CONFIG_MAXIMUM,
)

REQUIRED_CONFIG_METADATA_KEYS = (
    "config_version",
    "strategy_version",
    "parameter_set_id",
)

SAMPLE_AVAILABLE = "AVAILABLE"
SAMPLE_NOT_MEASURED = "NOT_MEASURED"
SAMPLE_STATUSES = (SAMPLE_AVAILABLE, SAMPLE_NOT_MEASURED)
NET_RETURN_UNDEFINED_REASON = "MONTE_CARLO_NET_RETURN_UNDEFINED_ZERO_ENTRY_NOTIONAL"
R_UNDEFINED_REASON = "TRADE_ACCOUNTING_R_UNDEFINED"
OPEN_TRADE_REASON = "TRADE_ACCOUNTING_POSITION_STILL_OPEN"

ENDING_NAV_METRIC = "ending_nav"
ENDING_NAV_FRACTION_METRIC = "ending_nav_fraction"
TOTAL_RETURN_METRIC = "total_return_fraction"
MAX_DRAWDOWN_METRIC = "max_drawdown_fraction"
LONGEST_LOSING_STREAK_METRIC = "longest_losing_streak"
CALMAR_METRIC = "calmar_ratio"
TRADES_TAKEN_METRIC = "trades_taken"
MONTE_CARLO_METRIC_NAMES = (
    ENDING_NAV_METRIC,
    ENDING_NAV_FRACTION_METRIC,
    TOTAL_RETURN_METRIC,
    MAX_DRAWDOWN_METRIC,
    LONGEST_LOSING_STREAK_METRIC,
    CALMAR_METRIC,
    TRADES_TAKEN_METRIC,
)
CALMAR_UNDEFINED_NO_DRAWDOWN = "UNDEFINED_NO_DRAWDOWN"

DEFAULT_DRAWDOWN_THRESHOLDS = (Decimal("0.10"), Decimal("0.15"))
DEFAULT_PERCENTILES = (
    Decimal("1"),
    Decimal("5"),
    Decimal("10"),
    Decimal("25"),
    Decimal("50"),
    Decimal("75"),
    Decimal("90"),
    Decimal("95"),
    Decimal("99"),
)
DEFAULT_SIMULATION_COUNT = 10_000
DEFAULT_STARTING_NAV = Decimal("1")
DEFAULT_RUIN_NAV_FRACTION = Decimal("0")

MINIMUM_SCHEDULES = 2
MINIMUM_USABLE_SAMPLES = 2
ROBUST_SAMPLE_MINIMUM = 30
MAXIMUM_SIMULATION_COUNT = 100_000
MAXIMUM_PATH_LENGTH = 10_000

MONTE_CARLO_DECIMAL_PRECISION = 60
MONTE_CARLO_METRIC_EXPONENT = Decimal("1E-12")

MONTE_CARLO_REASON_CODES = (
    "MONTE_CARLO_RESAMPLED_OBSERVED_TRADE_OUTCOMES",
    "MONTE_CARLO_DETERMINISTIC_SEEDED_STREAM",
    "MONTE_CARLO_COMMON_PATHS_ACROSS_SCHEDULES",
    "MONTE_CARLO_SCHEDULES_COMPARED",
    "MONTE_CARLO_PERCENTILE_DISTRIBUTIONS_REPORTED",
    "MONTE_CARLO_SERIAL_DEPENDENCE_NOT_PRESERVED",
    "MONTE_CARLO_TRADE_MULTISET_PRESERVED",
    "MONTE_CARLO_EXCLUDED_UNMEASURED_OUTCOMES",
    "MONTE_CARLO_EXCLUDED_OPEN_TRADE",
    "MONTE_CARLO_SMALL_SAMPLE_UNIVERSE",
    "MONTE_CARLO_RUIN_OBSERVED",
    "MONTE_CARLO_UNDEFINED_CALMAR_PATHS",
    "MONTE_CARLO_RISK_BUDGET_CHALLENGE_ONLY",
    "MONTE_CARLO_RESEARCH_ONLY",
    "MONTE_CARLO_BTC_193_PROMOTION_REQUIRED",
    "MONTE_CARLO_COMPLETE",
)


class MonteCarloRiskError(ValueError):
    """Raised when Monte Carlo risk evidence violates its frozen contract."""


@dataclass(frozen=True)
class TradeOutcomeSample:
    """One closed trade's outcome in both supported bases."""

    trade_reference: str
    r_multiple: Decimal | None
    r_multiple_status: str
    r_multiple_reason_code: str | None
    net_return_fraction: Decimal | None
    net_return_status: str
    net_return_reason_code: str | None

    def __post_init__(self) -> None:
        _non_empty(self.trade_reference, "trade_reference")
        _validate_cell(
            self.r_multiple,
            self.r_multiple_status,
            self.r_multiple_reason_code,
            name=R_MULTIPLE_BASIS,
        )
        _validate_cell(
            self.net_return_fraction,
            self.net_return_status,
            self.net_return_reason_code,
            name=NET_RETURN_BASIS,
        )

    def value(self, basis: str) -> Decimal | None:
        if basis == R_MULTIPLE_BASIS:
            return self.r_multiple
        if basis == NET_RETURN_BASIS:
            return self.net_return_fraction
        raise KeyError(basis)

    def status(self, basis: str) -> str:
        if basis == R_MULTIPLE_BASIS:
            return self.r_multiple_status
        if basis == NET_RETURN_BASIS:
            return self.net_return_status
        raise KeyError(basis)

    def reason_code(self, basis: str) -> str | None:
        if basis == R_MULTIPLE_BASIS:
            return self.r_multiple_reason_code
        if basis == NET_RETURN_BASIS:
            return self.net_return_reason_code
        raise KeyError(basis)

    def as_record(self) -> dict[str, Any]:
        return {
            "trade_reference": self.trade_reference,
            "r_multiple": _optional_decimal(self.r_multiple),
            "r_multiple_status": self.r_multiple_status,
            "r_multiple_reason_code": self.r_multiple_reason_code,
            "net_return_fraction": _optional_decimal(self.net_return_fraction),
            "net_return_status": self.net_return_status,
            "net_return_reason_code": self.net_return_reason_code,
        }


@dataclass(frozen=True)
class TradeOutcomeSampleSet:
    """The observed universe an analysis resamples, with its source identity."""

    feature_id: str
    policy_version: str
    source_feature_id: str
    source_policy_version: str
    source_id: str
    accounting_policy_version: str
    r_multiple_convention: str
    net_return_convention: str
    extraction_time: datetime | None
    config_metadata: dict[str, str]
    samples: tuple[TradeOutcomeSample, ...]

    def __post_init__(self) -> None:
        if self.feature_id != MONTE_CARLO_FEATURE_ID:
            raise MonteCarloRiskError(f"feature_id must be {MONTE_CARLO_FEATURE_ID}")
        if self.policy_version != MONTE_CARLO_SAMPLE_POLICY_VERSION:
            raise MonteCarloRiskError(
                f"policy_version must be {MONTE_CARLO_SAMPLE_POLICY_VERSION}"
            )
        _non_empty(self.source_feature_id, "source_feature_id")
        _non_empty(self.source_policy_version, "source_policy_version")
        _non_empty(self.source_id, "source_id")
        if self.accounting_policy_version != PAPER_TRADE_ACCOUNTING_POLICY_VERSION:
            raise MonteCarloRiskError(
                "samples must come from "
                f"{PAPER_TRADE_ACCOUNTING_POLICY_VERSION} accounting"
            )
        if self.r_multiple_convention != R_MULTIPLE_CONVENTION:
            raise MonteCarloRiskError(
                f"r_multiple_convention must be {R_MULTIPLE_CONVENTION}"
            )
        if self.net_return_convention != NET_RETURN_CONVENTION:
            raise MonteCarloRiskError(
                f"net_return_convention must be {NET_RETURN_CONVENTION}"
            )
        extraction_time = (
            None
            if self.extraction_time is None
            else require_utc_datetime(self.extraction_time, "extraction_time")
        )
        samples = tuple(self.samples)
        for sample in samples:
            if not isinstance(sample, TradeOutcomeSample):
                raise MonteCarloRiskError(
                    "samples must contain TradeOutcomeSample values"
                )
        references = [sample.trade_reference for sample in samples]
        if len(set(references)) != len(references):
            raise MonteCarloRiskError("trade references must be unique")
        object.__setattr__(self, "extraction_time", extraction_time)
        object.__setattr__(self, "samples", samples)
        object.__setattr__(
            self, "config_metadata", _config_metadata(self.config_metadata)
        )

    @property
    def sample_count(self) -> int:
        return len(self.samples)

    @property
    def input_digest(self) -> str:
        return _digest(self.as_record())

    def available(self, basis: str) -> tuple[TradeOutcomeSample, ...]:
        """Return the samples measurable in ``basis``, in recorded order."""

        basis = _require_member(basis, MONTE_CARLO_OUTCOME_BASES, "basis")
        return tuple(
            sample
            for sample in self.samples
            if sample.status(basis) == SAMPLE_AVAILABLE
        )

    def excluded(self, basis: str) -> tuple[TradeOutcomeSample, ...]:
        """Return the samples that cannot enter ``basis``, in recorded order."""

        basis = _require_member(basis, MONTE_CARLO_OUTCOME_BASES, "basis")
        return tuple(
            sample
            for sample in self.samples
            if sample.status(basis) != SAMPLE_AVAILABLE
        )

    def as_record(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "source_feature_id": self.source_feature_id,
            "source_policy_version": self.source_policy_version,
            "source_id": self.source_id,
            "accounting_policy_version": self.accounting_policy_version,
            "r_multiple_convention": self.r_multiple_convention,
            "net_return_convention": self.net_return_convention,
            "extraction_time": _isoformat(self.extraction_time),
            "config_metadata": dict(self.config_metadata),
            "samples": [sample.as_record() for sample in self.samples],
        }


@dataclass(frozen=True)
class RiskPerTradeSchedule:
    """One candidate risk-per-trade budget expressed as a fraction of NAV."""

    schedule_id: str
    fraction_of_nav: Decimal
    source: str

    def __post_init__(self) -> None:
        _non_empty(self.schedule_id, "schedule_id")
        fraction = _decimal(self.fraction_of_nav, "fraction_of_nav")
        if fraction <= 0 or fraction > 1:
            raise MonteCarloRiskError(
                "fraction_of_nav must be greater than zero and at most one"
            )
        object.__setattr__(self, "fraction_of_nav", fraction)
        object.__setattr__(
            self, "source", _require_member(self.source, SCHEDULE_SOURCES, "source")
        )

    def as_record(self) -> dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "fraction_of_nav": str(self.fraction_of_nav),
            "source": self.source,
        }


@dataclass(frozen=True)
class MonteCarloRiskSpec:
    """Frozen research question for one Monte Carlo portfolio risk analysis."""

    feature_id: str
    policy_version: str
    sample_policy_version: str
    resampling_policy_version: str
    random_stream_policy_version: str
    path_policy_version: str
    schedule_scaling_policy_version: str
    drawdown_policy_version: str
    calmar_policy_version: str
    percentile_policy_version: str
    ruin_policy_version: str
    common_paths_policy_version: str
    analysis_id: str
    outcome_basis: str
    resampling_method: str
    simulation_count: int
    path_length: int
    seed: int
    starting_nav: Decimal
    ruin_nav_fraction: Decimal
    drawdown_thresholds: tuple[Decimal, ...]
    percentiles: tuple[Decimal, ...]
    schedules: tuple[RiskPerTradeSchedule, ...]
    sample_set_digest: str
    sample_count: int
    usable_sample_count: int
    config_metadata: dict[str, str]

    @property
    def ruin_nav(self) -> Decimal:
        """The NAV at or below which a path is ruined and stops trading."""

        return self.starting_nav * self.ruin_nav_fraction

    def schedule(self, schedule_id: str) -> RiskPerTradeSchedule:
        for item in self.schedules:
            if item.schedule_id == schedule_id:
                return item
        raise KeyError(schedule_id)

    def as_record(self) -> dict[str, Any]:
        _validate_spec(self)
        payload = _spec_payload(self)
        if _digest(payload) != self.analysis_id:
            raise MonteCarloRiskError(
                "monte carlo specification does not match analysis_id"
            )
        return {**payload, "analysis_id": self.analysis_id}


@dataclass(frozen=True)
class PercentileValue:
    """One nearest-rank percentile of a simulated metric."""

    percentile: Decimal
    value: Decimal

    def as_record(self) -> dict[str, Any]:
        return {"percentile": str(self.percentile), "value": str(self.value)}


@dataclass(frozen=True)
class MetricDistribution:
    """The simulated distribution of one metric under one schedule."""

    metric_name: str
    defined_count: int
    undefined_count: int
    undefined_status: str | None
    mean: Decimal | None
    minimum: Decimal | None
    maximum: Decimal | None
    percentiles: tuple[PercentileValue, ...]

    def percentile(self, percentile: Any) -> Decimal:
        wanted = _decimal(percentile, "percentile")
        for item in self.percentiles:
            if item.percentile == wanted:
                return item.value
        raise KeyError(str(wanted))

    def as_record(self) -> dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "defined_count": self.defined_count,
            "undefined_count": self.undefined_count,
            "undefined_status": self.undefined_status,
            "mean": _optional_decimal(self.mean),
            "minimum": _optional_decimal(self.minimum),
            "maximum": _optional_decimal(self.maximum),
            "percentiles": [item.as_record() for item in self.percentiles],
        }


@dataclass(frozen=True)
class DrawdownExceedance:
    """How often a schedule's paths breached one declared drawdown threshold."""

    threshold: Decimal
    path_count: int
    probability: Decimal

    def as_record(self) -> dict[str, Any]:
        return {
            "threshold": str(self.threshold),
            "path_count": self.path_count,
            "probability": str(self.probability),
        }


@dataclass(frozen=True)
class ScheduleRiskProfile:
    """Simulated portfolio risk evidence for one risk-per-trade schedule."""

    schedule: RiskPerTradeSchedule
    ordinal: int
    simulation_count: int
    distributions: tuple[MetricDistribution, ...]
    ruin_path_count: int
    probability_of_ruin: Decimal
    loss_path_count: int
    probability_of_loss: Decimal
    drawdown_exceedances: tuple[DrawdownExceedance, ...]

    @property
    def schedule_id(self) -> str:
        return self.schedule.schedule_id

    def distribution(self, metric_name: str) -> MetricDistribution:
        for item in self.distributions:
            if item.metric_name == metric_name:
                return item
        raise KeyError(metric_name)

    def exceedance(self, threshold: Any) -> DrawdownExceedance:
        wanted = _decimal(threshold, "threshold")
        for item in self.drawdown_exceedances:
            if item.threshold == wanted:
                return item
        raise KeyError(str(wanted))

    def as_record(self) -> dict[str, Any]:
        return {
            "schedule": self.schedule.as_record(),
            "ordinal": self.ordinal,
            "simulation_count": self.simulation_count,
            "distributions": [item.as_record() for item in self.distributions],
            "ruin_path_count": self.ruin_path_count,
            "probability_of_ruin": str(self.probability_of_ruin),
            "loss_path_count": self.loss_path_count,
            "probability_of_loss": str(self.probability_of_loss),
            "drawdown_exceedances": [
                item.as_record() for item in self.drawdown_exceedances
            ],
        }


@dataclass(frozen=True)
class ExcludedSample:
    """One observed trade that could not enter the analysed basis."""

    trade_reference: str
    status: str
    reason_code: str

    def as_record(self) -> dict[str, Any]:
        return {
            "trade_reference": self.trade_reference,
            "status": self.status,
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True)
class MonteCarloRiskReport:
    """Replayable BTC-187 evidence for one Monte Carlo portfolio risk study."""

    feature_id: str
    policy_version: str
    missing_value_policy_version: str
    promotion_policy_version: str
    production_status: str
    promotion_ticket: str
    risk_budget_status: str
    report_id: str
    evidence_digest: str
    spec: MonteCarloRiskSpec
    samples: TradeOutcomeSampleSet
    included_trade_references: tuple[str, ...]
    excluded_samples: tuple[ExcludedSample, ...]
    profiles: tuple[ScheduleRiskProfile, ...]
    config_metadata: dict[str, str]
    reason_codes: tuple[str, ...]

    @property
    def outcome_basis(self) -> str:
        return self.spec.outcome_basis

    @property
    def schedule_ids(self) -> tuple[str, ...]:
        return tuple(profile.schedule_id for profile in self.profiles)

    def profile(self, schedule_id: str) -> ScheduleRiskProfile:
        for item in self.profiles:
            if item.schedule_id == schedule_id:
                return item
        raise KeyError(schedule_id)

    def as_record(self) -> dict[str, Any]:
        _validate_report(self)
        payload = _report_payload(self)
        if _digest(payload) != self.evidence_digest:
            raise MonteCarloRiskError(
                "monte carlo risk evidence does not match digest"
            )
        return {**payload, "evidence_digest": self.evidence_digest}


def trade_outcome_samples_from_dataset(
    dataset: PaperTradeOutcomeDataset,
) -> TradeOutcomeSampleSet:
    """Read the resampling universe from a BTC-191 paper-trade outcome dataset."""

    if not isinstance(dataset, PaperTradeOutcomeDataset):
        raise TypeError("dataset must be a PaperTradeOutcomeDataset")
    # Replays the dataset's own evidence before anything is resampled from it.
    dataset.as_record()
    if dataset.policy_version != PAPER_TRADE_OUTCOME_POLICY_VERSION:
        raise MonteCarloRiskError(
            f"dataset policy_version must be {PAPER_TRADE_OUTCOME_POLICY_VERSION}"
        )
    required = (R_MULTIPLE_BASIS, "net_pnl", "entry_notional")
    missing = tuple(
        name for name in required if name not in dataset.definition.outcome_names
    )
    if missing:
        raise MonteCarloRiskError(
            f"dataset must carry the outcomes {required}; missing {missing}"
        )
    samples: list[TradeOutcomeSample] = []
    with localcontext(Context(prec=MONTE_CARLO_DECIMAL_PRECISION)):
        for row in dataset.rows:
            r_cell = row.outcome(R_MULTIPLE_BASIS)
            net_cell = row.outcome("net_pnl")
            notional_cell = row.outcome("entry_notional")
            net_value, net_status, net_reason = _net_return_cell(
                net_pnl=net_cell.value,
                net_pnl_status=net_cell.status,
                net_pnl_reason=net_cell.reason_code,
                entry_notional=notional_cell.value,
                entry_notional_status=notional_cell.status,
                entry_notional_reason=notional_cell.reason_code,
            )
            samples.append(
                TradeOutcomeSample(
                    trade_reference=row.trade_reference,
                    r_multiple=r_cell.value,
                    r_multiple_status=(
                        SAMPLE_AVAILABLE
                        if r_cell.status == TRADE_OUTCOME_AVAILABLE
                        else SAMPLE_NOT_MEASURED
                    ),
                    r_multiple_reason_code=r_cell.reason_code,
                    net_return_fraction=net_value,
                    net_return_status=net_status,
                    net_return_reason_code=net_reason,
                )
            )
    return TradeOutcomeSampleSet(
        feature_id=MONTE_CARLO_FEATURE_ID,
        policy_version=MONTE_CARLO_SAMPLE_POLICY_VERSION,
        source_feature_id=dataset.feature_id,
        source_policy_version=dataset.policy_version,
        source_id=dataset.dataset_id,
        accounting_policy_version=dataset.accounting_policy_version,
        r_multiple_convention=dataset.r_multiple_convention,
        net_return_convention=NET_RETURN_CONVENTION,
        extraction_time=dataset.extraction_time,
        config_metadata=dict(dataset.config_metadata),
        samples=tuple(samples),
    )


def trade_outcome_samples_from_backtest(
    result: BacktestResult,
) -> TradeOutcomeSampleSet:
    """Read the resampling universe from a BTC-180 backtest run.

    A run may end holding a position; that trade is carried as an excluded
    sample citing ``TRADE_ACCOUNTING_POSITION_STILL_OPEN`` rather than resampled.
    """

    if not isinstance(result, BacktestResult):
        raise TypeError("result must be a BacktestResult")
    # Replays the run's own evidence before anything is resampled from it.
    result.as_record()
    samples: list[TradeOutcomeSample] = []
    with localcontext(Context(prec=MONTE_CARLO_DECIMAL_PRECISION)):
        for ordinal, trade in enumerate(result.trades):
            samples.append(
                _accounting_sample(trade, f"{result.run_id}-{ordinal:06d}")
            )
    return TradeOutcomeSampleSet(
        feature_id=MONTE_CARLO_FEATURE_ID,
        policy_version=MONTE_CARLO_SAMPLE_POLICY_VERSION,
        source_feature_id=result.feature_id,
        source_policy_version=result.policy_version,
        source_id=result.run_id,
        accounting_policy_version=PAPER_TRADE_ACCOUNTING_POLICY_VERSION,
        r_multiple_convention=R_MULTIPLE_CONVENTION,
        net_return_convention=NET_RETURN_CONVENTION,
        extraction_time=result.ended_at,
        config_metadata=dict(result.config_metadata),
        samples=tuple(samples),
    )


def restore_trade_outcome_samples(
    record: Mapping[str, Any],
) -> TradeOutcomeSampleSet:
    """Restore a persisted resampling universe exactly as it was recorded."""

    source = _mapping(record, "record")
    samples = tuple(
        TradeOutcomeSample(
            trade_reference=_string(item.get("trade_reference"), "trade_reference"),
            r_multiple=_optional_decimal_from_record(
                item.get("r_multiple"), "r_multiple"
            ),
            r_multiple_status=_string(
                item.get("r_multiple_status"), "r_multiple_status"
            ),
            r_multiple_reason_code=_optional_string(
                item.get("r_multiple_reason_code"), "r_multiple_reason_code"
            ),
            net_return_fraction=_optional_decimal_from_record(
                item.get("net_return_fraction"), "net_return_fraction"
            ),
            net_return_status=_string(
                item.get("net_return_status"), "net_return_status"
            ),
            net_return_reason_code=_optional_string(
                item.get("net_return_reason_code"), "net_return_reason_code"
            ),
        )
        for item in (
            _mapping(entry, "sample")
            for entry in _sequence(source.get("samples"), "samples")
        )
    )
    restored = TradeOutcomeSampleSet(
        feature_id=_string(source.get("feature_id"), "feature_id"),
        policy_version=_string(source.get("policy_version"), "policy_version"),
        source_feature_id=_string(
            source.get("source_feature_id"), "source_feature_id"
        ),
        source_policy_version=_string(
            source.get("source_policy_version"), "source_policy_version"
        ),
        source_id=_string(source.get("source_id"), "source_id"),
        accounting_policy_version=_string(
            source.get("accounting_policy_version"), "accounting_policy_version"
        ),
        r_multiple_convention=_string(
            source.get("r_multiple_convention"), "r_multiple_convention"
        ),
        net_return_convention=_string(
            source.get("net_return_convention"), "net_return_convention"
        ),
        extraction_time=_optional_utc_from_record(
            source.get("extraction_time"), "extraction_time"
        ),
        config_metadata=_string_mapping(
            source.get("config_metadata"), "config_metadata"
        ),
        samples=samples,
    )
    if restored.as_record() != dict(source):
        raise MonteCarloRiskError("record does not match reconstructed sample set")
    return restored


def risk_per_trade_schedule(
    *,
    schedule_id: str,
    fraction_of_nav: Any,
    source: str = SCHEDULE_SOURCE_CALLER,
) -> RiskPerTradeSchedule:
    """Declare one candidate risk-per-trade schedule."""

    schedule = RiskPerTradeSchedule(
        schedule_id=_string(schedule_id, "schedule_id"),
        fraction_of_nav=_decimal(fraction_of_nav, "fraction_of_nav"),
        source=source,
    )
    schedule.as_record()
    return schedule


def config_risk_per_trade_schedules(
    config: StrategyConfig | None = None,
) -> tuple[RiskPerTradeSchedule, ...]:
    """Return the schedules the versioned strategy config already declares.

    The candidates are BTC-144's own conviction-band risk fractions plus the
    configured maximum risk at stop, so a comparison challenges the budgets the
    strategy actually uses rather than invented numbers.
    """

    bands, maximum = risk_schedule_from_config(config)
    fractions: list[tuple[Decimal, str]] = []
    seen: set[Decimal] = set()
    for band in bands:
        if band.risk_fraction_nav in seen:
            continue
        seen.add(band.risk_fraction_nav)
        fractions.append((band.risk_fraction_nav, SCHEDULE_SOURCE_CONFIG_BAND))
    if maximum not in seen:
        fractions.append((maximum, SCHEDULE_SOURCE_CONFIG_MAXIMUM))
    return tuple(
        risk_per_trade_schedule(
            schedule_id=(
                f"config_band_{fraction}"
                if source == SCHEDULE_SOURCE_CONFIG_BAND
                else "config_max_risk_at_stop"
            ),
            fraction_of_nav=fraction,
            source=source,
        )
        for fraction, source in sorted(fractions, key=lambda item: item[0])
    )


def monte_carlo_risk_spec(
    *,
    samples: TradeOutcomeSampleSet,
    schedules: Sequence[RiskPerTradeSchedule],
    seed: int,
    outcome_basis: str = R_MULTIPLE_BASIS,
    resampling_method: str = IID_BOOTSTRAP,
    simulation_count: int = DEFAULT_SIMULATION_COUNT,
    path_length: int | None = None,
    starting_nav: Any = DEFAULT_STARTING_NAV,
    ruin_nav_fraction: Any = DEFAULT_RUIN_NAV_FRACTION,
    drawdown_thresholds: Sequence[Any] = DEFAULT_DRAWDOWN_THRESHOLDS,
    percentiles: Sequence[Any] = DEFAULT_PERCENTILES,
) -> MonteCarloRiskSpec:
    """Declare one Monte Carlo question and bind it to its observed universe."""

    if not isinstance(samples, TradeOutcomeSampleSet):
        raise TypeError("samples must be a TradeOutcomeSampleSet")
    basis = _require_member(outcome_basis, MONTE_CARLO_OUTCOME_BASES, "outcome_basis")
    method = _require_member(
        resampling_method, MONTE_CARLO_RESAMPLING_METHODS, "resampling_method"
    )
    usable = len(samples.available(basis))
    if usable < MINIMUM_USABLE_SAMPLES:
        raise MonteCarloRiskError(
            f"at least {MINIMUM_USABLE_SAMPLES} measurable {basis} outcomes are "
            "required to resample a portfolio"
        )
    resolved_length = usable if path_length is None else _positive_integer(
        path_length, "path_length"
    )
    if method == ORDER_PERMUTATION and resolved_length != usable:
        # Reordering the observed trades keeps every trade exactly once, so a
        # path cannot be longer or shorter than the universe it permutes.
        raise MonteCarloRiskError(
            "order_permutation requires path_length to equal the usable sample count"
        )
    provisional = MonteCarloRiskSpec(
        feature_id=MONTE_CARLO_FEATURE_ID,
        policy_version=MONTE_CARLO_POLICY_VERSION,
        sample_policy_version=MONTE_CARLO_SAMPLE_POLICY_VERSION,
        resampling_policy_version=RESAMPLING_POLICY_VERSIONS[method],
        random_stream_policy_version=RANDOM_STREAM_POLICY_VERSIONS[method],
        path_policy_version=MONTE_CARLO_PATH_POLICY_VERSION,
        schedule_scaling_policy_version=SCHEDULE_SCALING_POLICY_VERSIONS[basis],
        drawdown_policy_version=MONTE_CARLO_DRAWDOWN_POLICY_VERSION,
        calmar_policy_version=MONTE_CARLO_CALMAR_POLICY_VERSION,
        percentile_policy_version=MONTE_CARLO_PERCENTILE_POLICY_VERSION,
        ruin_policy_version=MONTE_CARLO_RUIN_POLICY_VERSION,
        common_paths_policy_version=MONTE_CARLO_COMMON_PATHS_POLICY_VERSION,
        analysis_id="",
        outcome_basis=basis,
        resampling_method=method,
        simulation_count=_positive_integer(simulation_count, "simulation_count"),
        path_length=resolved_length,
        seed=_non_negative_integer(seed, "seed"),
        starting_nav=_decimal(starting_nav, "starting_nav"),
        ruin_nav_fraction=_decimal(ruin_nav_fraction, "ruin_nav_fraction"),
        drawdown_thresholds=_thresholds(drawdown_thresholds),
        percentiles=_percentiles(percentiles),
        schedules=_schedules(schedules),
        sample_set_digest=samples.input_digest,
        sample_count=samples.sample_count,
        usable_sample_count=usable,
        config_metadata=dict(samples.config_metadata),
    )
    spec = replace(provisional, analysis_id=_digest(_spec_payload(provisional)))
    spec.as_record()
    return spec


def run_monte_carlo_risk_analysis(
    spec: MonteCarloRiskSpec,
    samples: TradeOutcomeSampleSet,
) -> MonteCarloRiskReport:
    """Resample the observed outcomes and compare every declared schedule."""

    if not isinstance(spec, MonteCarloRiskSpec):
        raise TypeError("spec must be a MonteCarloRiskSpec")
    if not isinstance(samples, TradeOutcomeSampleSet):
        raise TypeError("samples must be a TradeOutcomeSampleSet")
    spec.as_record()
    return _build_report(spec, samples)


def restore_monte_carlo_risk_report(
    record: Mapping[str, Any],
) -> MonteCarloRiskReport:
    """Restore persisted evidence by replaying the seeded analysis it records."""

    source = _mapping(record, "record")
    spec = _restore_spec(_mapping(source.get("spec"), "spec"))
    samples = restore_trade_outcome_samples(_mapping(source.get("samples"), "samples"))
    report = _build_report(spec, samples)
    if report.as_record() != dict(source):
        raise MonteCarloRiskError(
            "record does not match the replayed monte carlo analysis"
        )
    return report


def _build_report(
    spec: MonteCarloRiskSpec,
    samples: TradeOutcomeSampleSet,
) -> MonteCarloRiskReport:
    if samples.input_digest != spec.sample_set_digest:
        raise MonteCarloRiskError("samples do not match the specification digest")
    if samples.sample_count != spec.sample_count:
        raise MonteCarloRiskError("sample count does not match the specification")
    basis = spec.outcome_basis
    available = samples.available(basis)
    if len(available) != spec.usable_sample_count:
        raise MonteCarloRiskError(
            "usable sample count does not match the specification"
        )
    excluded = tuple(
        ExcludedSample(
            trade_reference=sample.trade_reference,
            status=sample.status(basis),
            reason_code=_required_reason_code(sample, basis),
        )
        for sample in samples.excluded(basis)
    )
    values = tuple(_sample_value(sample, basis) for sample in available)
    paths = _index_paths(spec)
    profiles: list[ScheduleRiskProfile] = []
    with localcontext(Context(prec=MONTE_CARLO_DECIMAL_PRECISION)):
        for ordinal, schedule in enumerate(spec.schedules):
            profiles.append(_profile(spec, schedule, ordinal, values, paths))
    report = MonteCarloRiskReport(
        feature_id=MONTE_CARLO_FEATURE_ID,
        policy_version=MONTE_CARLO_POLICY_VERSION,
        missing_value_policy_version=MONTE_CARLO_MISSING_VALUE_POLICY_VERSION,
        promotion_policy_version=MONTE_CARLO_PROMOTION_POLICY_VERSION,
        production_status=MONTE_CARLO_PRODUCTION_STATUS,
        promotion_ticket=MONTE_CARLO_PROMOTION_TICKET,
        risk_budget_status=MONTE_CARLO_RISK_BUDGET_STATUS,
        report_id="",
        evidence_digest="",
        spec=spec,
        samples=samples,
        included_trade_references=tuple(
            sample.trade_reference for sample in available
        ),
        excluded_samples=excluded,
        profiles=tuple(profiles),
        config_metadata=dict(spec.config_metadata),
        reason_codes=_reason_codes(spec, tuple(profiles), excluded),
    )
    report = replace(report, report_id=_report_id(report))
    _validate_report(report)
    return replace(report, evidence_digest=_digest(_report_payload(report)))


def _index_paths(spec: MonteCarloRiskSpec) -> list[list[int]]:
    """Draw the resampled trade orders shared by every compared schedule."""

    if spec.resampling_method == IID_BOOTSTRAP:
        drawn = uniform_index_samples(
            (spec.simulation_count, spec.path_length),
            seed=spec.seed,
            high=spec.usable_sample_count,
        )
    else:
        drawn = permutation_index_samples(
            spec.simulation_count,
            seed=spec.seed,
            size=spec.usable_sample_count,
        )
    return [[int(index) for index in row] for row in drawn.tolist()]


def _profile(
    spec: MonteCarloRiskSpec,
    schedule: RiskPerTradeSchedule,
    ordinal: int,
    values: tuple[Decimal, ...],
    paths: list[list[int]],
) -> ScheduleRiskProfile:
    one = Decimal(1)
    fraction = schedule.fraction_of_nav
    # One growth factor per observed trade: the NAV multiplier that trade
    # produces under this schedule, reused by every path that draws it.
    growth = tuple(one + fraction * value for value in values)
    losing = tuple(value < 0 for value in values)
    ruin_nav = spec.ruin_nav
    starting_nav = spec.starting_nav

    ending: list[Decimal] = []
    ending_fraction: list[Decimal] = []
    total_return: list[Decimal] = []
    drawdowns: list[Decimal] = []
    streaks: list[Decimal] = []
    taken: list[Decimal] = []
    calmar: list[Decimal] = []
    calmar_undefined = 0
    ruin_paths = 0
    loss_paths = 0

    for row in paths:
        nav = starting_nav
        peak = starting_nav
        trough = starting_nav
        worst = Decimal(0)
        streak = 0
        longest = 0
        trades = 0
        ruined = False
        for index in row:
            nav = nav * growth[index]
            trades += 1
            if losing[index]:
                streak += 1
                if streak > longest:
                    longest = streak
            else:
                streak = 0
            if nav > peak:
                decline = (peak - trough) / peak
                if decline > worst:
                    worst = decline
                peak = nav
                trough = nav
            elif nav < trough:
                trough = nav
            if nav <= ruin_nav:
                ruined = True
                break
        decline = (peak - trough) / peak
        if decline > worst:
            worst = decline
        fraction_of_start = nav / starting_nav
        ending.append(nav)
        ending_fraction.append(fraction_of_start)
        total_return.append(fraction_of_start - one)
        drawdowns.append(worst)
        streaks.append(Decimal(longest))
        taken.append(Decimal(trades))
        if worst > 0:
            calmar.append((fraction_of_start - one) / worst)
        else:
            calmar_undefined += 1
        if ruined:
            ruin_paths += 1
        if nav < starting_nav:
            loss_paths += 1

    simulations = len(paths)
    distributions = (
        _distribution(ENDING_NAV_METRIC, ending, 0, None, spec),
        _distribution(ENDING_NAV_FRACTION_METRIC, ending_fraction, 0, None, spec),
        _distribution(TOTAL_RETURN_METRIC, total_return, 0, None, spec),
        _distribution(MAX_DRAWDOWN_METRIC, drawdowns, 0, None, spec),
        _distribution(LONGEST_LOSING_STREAK_METRIC, streaks, 0, None, spec),
        _distribution(
            CALMAR_METRIC,
            calmar,
            calmar_undefined,
            CALMAR_UNDEFINED_NO_DRAWDOWN if calmar_undefined else None,
            spec,
        ),
        _distribution(TRADES_TAKEN_METRIC, taken, 0, None, spec),
    )
    exceedances = tuple(
        DrawdownExceedance(
            threshold=threshold,
            path_count=sum(1 for value in drawdowns if value > threshold),
            probability=_probability(
                sum(1 for value in drawdowns if value > threshold), simulations
            ),
        )
        for threshold in spec.drawdown_thresholds
    )
    return ScheduleRiskProfile(
        schedule=schedule,
        ordinal=ordinal,
        simulation_count=simulations,
        distributions=distributions,
        ruin_path_count=ruin_paths,
        probability_of_ruin=_probability(ruin_paths, simulations),
        loss_path_count=loss_paths,
        probability_of_loss=_probability(loss_paths, simulations),
        drawdown_exceedances=exceedances,
    )


def _distribution(
    metric_name: str,
    values: list[Decimal],
    undefined_count: int,
    undefined_status: str | None,
    spec: MonteCarloRiskSpec,
) -> MetricDistribution:
    """Summarize one metric as nearest-rank percentiles over defined paths."""

    if not values:
        return MetricDistribution(
            metric_name=metric_name,
            defined_count=0,
            undefined_count=undefined_count,
            undefined_status=undefined_status,
            mean=None,
            minimum=None,
            maximum=None,
            percentiles=(),
        )
    ordered = sorted(values)
    count = len(ordered)
    total = sum(ordered, Decimal(0))
    percentiles = tuple(
        PercentileValue(
            percentile=percentile,
            value=_quantize(ordered[_nearest_rank(percentile, count) - 1]),
        )
        for percentile in spec.percentiles
    )
    return MetricDistribution(
        metric_name=metric_name,
        defined_count=count,
        undefined_count=undefined_count,
        undefined_status=undefined_status,
        mean=_quantize(total / Decimal(count)),
        minimum=_quantize(ordered[0]),
        maximum=_quantize(ordered[-1]),
        percentiles=percentiles,
    )


def _nearest_rank(percentile: Decimal, count: int) -> int:
    """Return the 1-based nearest rank, so a percentile is an observed value."""

    scaled = percentile * Decimal(count) / Decimal(100)
    rank = int(scaled)
    if Decimal(rank) < scaled:
        rank += 1
    if rank < 1:
        rank = 1
    if rank > count:
        rank = count
    return rank


def _probability(count: int, simulations: int) -> Decimal:
    return _quantize(Decimal(count) / Decimal(simulations))


def _sample_value(sample: TradeOutcomeSample, basis: str) -> Decimal:
    value = sample.value(basis)
    if value is None:
        raise MonteCarloRiskError(
            f"{sample.trade_reference} has no measurable {basis} outcome"
        )
    return value


def _required_reason_code(sample: TradeOutcomeSample, basis: str) -> str:
    reason = sample.reason_code(basis)
    if reason is None:
        raise MonteCarloRiskError(
            f"{sample.trade_reference} must explain its unmeasured {basis} outcome"
        )
    return reason


def _accounting_sample(
    trade: PaperTradeAccounting,
    trade_reference: str,
) -> TradeOutcomeSample:
    if not isinstance(trade, PaperTradeAccounting):
        raise TypeError("trades must be PaperTradeAccounting values")
    if trade.policy_version != PAPER_TRADE_ACCOUNTING_POLICY_VERSION:
        raise MonteCarloRiskError(
            f"trade accounting must be {PAPER_TRADE_ACCOUNTING_POLICY_VERSION}"
        )
    if trade.r_multiple_convention != R_MULTIPLE_CONVENTION:
        raise MonteCarloRiskError(
            f"r_multiple_convention must be {R_MULTIPLE_CONVENTION}"
        )
    if not trade.closed:
        # BTC-180 lets a run end holding a position.  Accounting to date is not
        # a final outcome, so that trade is excluded by name in both bases
        # rather than resampled as though it had finished -- and rather than
        # discarding the closed trades the run did produce.
        if OPEN_TRADE_REASON not in trade.reason_codes:
            raise MonteCarloRiskError(
                f"an open trade must cite {OPEN_TRADE_REASON} from the accounting"
            )
        return TradeOutcomeSample(
            trade_reference=trade_reference,
            r_multiple=None,
            r_multiple_status=SAMPLE_NOT_MEASURED,
            r_multiple_reason_code=OPEN_TRADE_REASON,
            net_return_fraction=None,
            net_return_status=SAMPLE_NOT_MEASURED,
            net_return_reason_code=OPEN_TRADE_REASON,
        )
    if trade.r_multiple is None:
        if R_UNDEFINED_REASON not in trade.reason_codes:
            raise MonteCarloRiskError(
                "an unmeasured R multiple must cite "
                f"{R_UNDEFINED_REASON} from the accounting"
            )
        r_status = SAMPLE_NOT_MEASURED
        r_reason: str | None = R_UNDEFINED_REASON
    else:
        r_status = SAMPLE_AVAILABLE
        r_reason = None
    net_value, net_status, net_reason = _net_return_cell(
        net_pnl=trade.net_pnl,
        net_pnl_status=TRADE_OUTCOME_AVAILABLE,
        net_pnl_reason=None,
        entry_notional=trade.entry_notional,
        entry_notional_status=TRADE_OUTCOME_AVAILABLE,
        entry_notional_reason=None,
    )
    return TradeOutcomeSample(
        trade_reference=trade_reference,
        r_multiple=trade.r_multiple,
        r_multiple_status=r_status,
        r_multiple_reason_code=r_reason,
        net_return_fraction=net_value,
        net_return_status=net_status,
        net_return_reason_code=net_reason,
    )


def _net_return_cell(
    *,
    net_pnl: Decimal | None,
    net_pnl_status: str,
    net_pnl_reason: str | None,
    entry_notional: Decimal | None,
    entry_notional_status: str,
    entry_notional_reason: str | None,
) -> tuple[Decimal | None, str, str | None]:
    """Normalize net P&L by entry notional, or explain why it is unmeasured."""

    if net_pnl_status != TRADE_OUTCOME_AVAILABLE or net_pnl is None:
        return None, SAMPLE_NOT_MEASURED, net_pnl_reason
    if entry_notional_status != TRADE_OUTCOME_AVAILABLE or entry_notional is None:
        return None, SAMPLE_NOT_MEASURED, entry_notional_reason
    if entry_notional == 0:
        return None, SAMPLE_NOT_MEASURED, NET_RETURN_UNDEFINED_REASON
    return net_pnl / entry_notional, SAMPLE_AVAILABLE, None


def _reason_codes(
    spec: MonteCarloRiskSpec,
    profiles: tuple[ScheduleRiskProfile, ...],
    excluded: tuple[ExcludedSample, ...],
) -> tuple[str, ...]:
    codes = [
        "MONTE_CARLO_RESAMPLED_OBSERVED_TRADE_OUTCOMES",
        "MONTE_CARLO_DETERMINISTIC_SEEDED_STREAM",
        "MONTE_CARLO_COMMON_PATHS_ACROSS_SCHEDULES",
        "MONTE_CARLO_SCHEDULES_COMPARED",
        "MONTE_CARLO_PERCENTILE_DISTRIBUTIONS_REPORTED",
    ]
    if spec.resampling_method == IID_BOOTSTRAP:
        # Independent draws destroy the order of the realized run, so streak
        # and drawdown evidence assumes trade outcomes are exchangeable.
        codes.append("MONTE_CARLO_SERIAL_DEPENDENCE_NOT_PRESERVED")
    else:
        codes.append("MONTE_CARLO_TRADE_MULTISET_PRESERVED")
    if excluded:
        codes.append("MONTE_CARLO_EXCLUDED_UNMEASURED_OUTCOMES")
    if any(item.reason_code == OPEN_TRADE_REASON for item in excluded):
        codes.append("MONTE_CARLO_EXCLUDED_OPEN_TRADE")
    if spec.usable_sample_count < ROBUST_SAMPLE_MINIMUM:
        # Resampling cannot manufacture evidence the observed record lacks.
        codes.append("MONTE_CARLO_SMALL_SAMPLE_UNIVERSE")
    if any(profile.ruin_path_count for profile in profiles):
        codes.append("MONTE_CARLO_RUIN_OBSERVED")
    if any(
        profile.distribution(CALMAR_METRIC).undefined_count for profile in profiles
    ):
        codes.append("MONTE_CARLO_UNDEFINED_CALMAR_PATHS")
    codes.extend(
        (
            "MONTE_CARLO_RISK_BUDGET_CHALLENGE_ONLY",
            "MONTE_CARLO_RESEARCH_ONLY",
            "MONTE_CARLO_BTC_193_PROMOTION_REQUIRED",
            "MONTE_CARLO_COMPLETE",
        )
    )
    return tuple(codes)


def _validate_spec(spec: MonteCarloRiskSpec) -> None:
    if spec.feature_id != MONTE_CARLO_FEATURE_ID:
        raise MonteCarloRiskError(f"feature_id must be {MONTE_CARLO_FEATURE_ID}")
    if spec.policy_version != MONTE_CARLO_POLICY_VERSION:
        raise MonteCarloRiskError(
            f"policy_version must be {MONTE_CARLO_POLICY_VERSION}"
        )
    if spec.sample_policy_version != MONTE_CARLO_SAMPLE_POLICY_VERSION:
        raise MonteCarloRiskError(
            f"sample_policy_version must be {MONTE_CARLO_SAMPLE_POLICY_VERSION}"
        )
    basis = _require_member(
        spec.outcome_basis, MONTE_CARLO_OUTCOME_BASES, "outcome_basis"
    )
    method = _require_member(
        spec.resampling_method, MONTE_CARLO_RESAMPLING_METHODS, "resampling_method"
    )
    if spec.resampling_policy_version != RESAMPLING_POLICY_VERSIONS[method]:
        raise MonteCarloRiskError(
            "resampling_policy_version must match the resampling method"
        )
    if spec.random_stream_policy_version != RANDOM_STREAM_POLICY_VERSIONS[method]:
        raise MonteCarloRiskError(
            "random_stream_policy_version must match the resampling method"
        )
    if spec.schedule_scaling_policy_version != SCHEDULE_SCALING_POLICY_VERSIONS[basis]:
        raise MonteCarloRiskError(
            "schedule_scaling_policy_version must match the outcome basis"
        )
    for field_name, expected in (
        ("path_policy_version", MONTE_CARLO_PATH_POLICY_VERSION),
        ("drawdown_policy_version", MONTE_CARLO_DRAWDOWN_POLICY_VERSION),
        ("calmar_policy_version", MONTE_CARLO_CALMAR_POLICY_VERSION),
        ("percentile_policy_version", MONTE_CARLO_PERCENTILE_POLICY_VERSION),
        ("ruin_policy_version", MONTE_CARLO_RUIN_POLICY_VERSION),
        ("common_paths_policy_version", MONTE_CARLO_COMMON_PATHS_POLICY_VERSION),
    ):
        if getattr(spec, field_name) != expected:
            raise MonteCarloRiskError(f"{field_name} must be {expected}")
    _positive_integer(spec.simulation_count, "simulation_count")
    if spec.simulation_count > MAXIMUM_SIMULATION_COUNT:
        raise MonteCarloRiskError(
            f"simulation_count must not exceed {MAXIMUM_SIMULATION_COUNT}"
        )
    _positive_integer(spec.path_length, "path_length")
    if spec.path_length > MAXIMUM_PATH_LENGTH:
        raise MonteCarloRiskError(
            f"path_length must not exceed {MAXIMUM_PATH_LENGTH}"
        )
    _non_negative_integer(spec.seed, "seed")
    if not isinstance(spec.starting_nav, Decimal) or spec.starting_nav <= 0:
        raise MonteCarloRiskError("starting_nav must be a positive decimal")
    if not isinstance(spec.ruin_nav_fraction, Decimal):
        raise MonteCarloRiskError("ruin_nav_fraction must be a decimal")
    if spec.ruin_nav_fraction < 0 or spec.ruin_nav_fraction >= 1:
        raise MonteCarloRiskError(
            "ruin_nav_fraction must be at least zero and below one"
        )
    _thresholds(spec.drawdown_thresholds)
    _percentiles(spec.percentiles)
    _schedules(spec.schedules)
    _non_empty(spec.sample_set_digest, "sample_set_digest")
    _positive_integer(spec.sample_count, "sample_count")
    _positive_integer(spec.usable_sample_count, "usable_sample_count")
    if spec.usable_sample_count > spec.sample_count:
        raise MonteCarloRiskError(
            "usable_sample_count cannot exceed sample_count"
        )
    if spec.usable_sample_count < MINIMUM_USABLE_SAMPLES:
        raise MonteCarloRiskError(
            f"at least {MINIMUM_USABLE_SAMPLES} usable samples are required"
        )
    if method == ORDER_PERMUTATION and spec.path_length != spec.usable_sample_count:
        raise MonteCarloRiskError(
            "order_permutation requires path_length to equal the usable sample count"
        )
    _config_metadata(spec.config_metadata)


def _validate_report(report: MonteCarloRiskReport) -> None:
    if report.feature_id != MONTE_CARLO_FEATURE_ID:
        raise MonteCarloRiskError(f"feature_id must be {MONTE_CARLO_FEATURE_ID}")
    if report.policy_version != MONTE_CARLO_POLICY_VERSION:
        raise MonteCarloRiskError(
            f"policy_version must be {MONTE_CARLO_POLICY_VERSION}"
        )
    if report.missing_value_policy_version != MONTE_CARLO_MISSING_VALUE_POLICY_VERSION:
        raise MonteCarloRiskError(
            "missing_value_policy_version must be "
            f"{MONTE_CARLO_MISSING_VALUE_POLICY_VERSION}"
        )
    if report.promotion_policy_version != MONTE_CARLO_PROMOTION_POLICY_VERSION:
        raise MonteCarloRiskError(
            f"promotion_policy_version must be {MONTE_CARLO_PROMOTION_POLICY_VERSION}"
        )
    if report.production_status != MONTE_CARLO_PRODUCTION_STATUS:
        raise MonteCarloRiskError(
            f"production_status must be {MONTE_CARLO_PRODUCTION_STATUS}"
        )
    if report.promotion_ticket != MONTE_CARLO_PROMOTION_TICKET:
        raise MonteCarloRiskError(
            f"promotion_ticket must be {MONTE_CARLO_PROMOTION_TICKET}"
        )
    if report.risk_budget_status != MONTE_CARLO_RISK_BUDGET_STATUS:
        raise MonteCarloRiskError(
            f"risk_budget_status must be {MONTE_CARLO_RISK_BUDGET_STATUS}"
        )
    _validate_spec(report.spec)
    if report.samples.input_digest != report.spec.sample_set_digest:
        raise MonteCarloRiskError("samples do not match the specification digest")
    if report.config_metadata != report.spec.config_metadata:
        raise MonteCarloRiskError(
            "report config_metadata must match the specification"
        )
    if len(report.profiles) != len(report.spec.schedules):
        raise MonteCarloRiskError("one profile is required for every schedule")
    for ordinal, (profile, schedule) in enumerate(
        zip(report.profiles, report.spec.schedules, strict=True)
    ):
        if profile.schedule != schedule or profile.ordinal != ordinal:
            raise MonteCarloRiskError(
                "profiles must follow the specification's schedule order"
            )
        if profile.simulation_count != report.spec.simulation_count:
            raise MonteCarloRiskError(
                "every profile must report the declared simulation count"
            )
        _validate_profile(report.spec, profile)
    included = report.included_trade_references
    excluded = tuple(item.trade_reference for item in report.excluded_samples)
    if len(included) != report.spec.usable_sample_count:
        raise MonteCarloRiskError(
            "included trade references must match the usable sample count"
        )
    recorded = tuple(sample.trade_reference for sample in report.samples.samples)
    if tuple(sorted((*included, *excluded))) != tuple(sorted(recorded)):
        raise MonteCarloRiskError(
            "included and excluded trades must account for every sample"
        )
    for item in report.excluded_samples:
        if item.status == SAMPLE_AVAILABLE:
            raise MonteCarloRiskError("an excluded trade must not be available")
        _require_member(item.status, SAMPLE_STATUSES, "excluded status")
        _non_empty(item.reason_code, "reason_code")
    for code in report.reason_codes:
        if code not in MONTE_CARLO_REASON_CODES:
            raise MonteCarloRiskError(f"unknown monte carlo reason code {code}")
    if report.reason_codes[-1:] != ("MONTE_CARLO_COMPLETE",):
        raise MonteCarloRiskError("reason codes must end with MONTE_CARLO_COMPLETE")


def _validate_profile(
    spec: MonteCarloRiskSpec,
    profile: ScheduleRiskProfile,
) -> None:
    names = tuple(item.metric_name for item in profile.distributions)
    if names != MONTE_CARLO_METRIC_NAMES:
        raise MonteCarloRiskError(
            f"a profile must report exactly {MONTE_CARLO_METRIC_NAMES}"
        )
    for distribution in profile.distributions:
        total = distribution.defined_count + distribution.undefined_count
        if total != profile.simulation_count:
            raise MonteCarloRiskError(
                "every simulated path must be defined or explicitly undefined"
            )
        if distribution.undefined_count and distribution.undefined_status is None:
            raise MonteCarloRiskError(
                "undefined metric paths must carry an explicit status"
            )
        if not distribution.undefined_count and distribution.undefined_status:
            raise MonteCarloRiskError(
                "a fully defined metric must not carry an undefined status"
            )
        expected = () if not distribution.defined_count else spec.percentiles
        if tuple(item.percentile for item in distribution.percentiles) != expected:
            raise MonteCarloRiskError(
                "percentiles must follow the declared percentile grid"
            )
    thresholds = tuple(item.threshold for item in profile.drawdown_exceedances)
    if thresholds != spec.drawdown_thresholds:
        raise MonteCarloRiskError(
            "drawdown exceedances must follow the declared thresholds"
        )
    for exceedance in profile.drawdown_exceedances:
        if not 0 <= exceedance.path_count <= profile.simulation_count:
            raise MonteCarloRiskError("exceedance counts must be within the paths")
    if not 0 <= profile.ruin_path_count <= profile.simulation_count:
        raise MonteCarloRiskError("ruin counts must be within the simulated paths")
    if not 0 <= profile.loss_path_count <= profile.simulation_count:
        raise MonteCarloRiskError("loss counts must be within the simulated paths")


def _report_id(report: MonteCarloRiskReport) -> str:
    return _digest(
        {
            "feature_id": report.feature_id,
            "policy_version": report.policy_version,
            "analysis_id": report.spec.analysis_id,
            "sample_set_digest": report.spec.sample_set_digest,
        }
    )


def _report_payload(report: MonteCarloRiskReport) -> dict[str, Any]:
    return {
        "feature_id": report.feature_id,
        "policy_version": report.policy_version,
        "missing_value_policy_version": report.missing_value_policy_version,
        "promotion_policy_version": report.promotion_policy_version,
        "production_status": report.production_status,
        "promotion_ticket": report.promotion_ticket,
        "risk_budget_status": report.risk_budget_status,
        "report_id": report.report_id,
        "spec": report.spec.as_record(),
        "samples": report.samples.as_record(),
        "included_trade_references": list(report.included_trade_references),
        "excluded_samples": [item.as_record() for item in report.excluded_samples],
        "profiles": [item.as_record() for item in report.profiles],
        "config_metadata": dict(report.config_metadata),
        "reason_codes": list(report.reason_codes),
    }


def _spec_payload(spec: MonteCarloRiskSpec) -> dict[str, Any]:
    return {
        "feature_id": spec.feature_id,
        "policy_version": spec.policy_version,
        "sample_policy_version": spec.sample_policy_version,
        "resampling_policy_version": spec.resampling_policy_version,
        "random_stream_policy_version": spec.random_stream_policy_version,
        "path_policy_version": spec.path_policy_version,
        "schedule_scaling_policy_version": spec.schedule_scaling_policy_version,
        "drawdown_policy_version": spec.drawdown_policy_version,
        "calmar_policy_version": spec.calmar_policy_version,
        "percentile_policy_version": spec.percentile_policy_version,
        "ruin_policy_version": spec.ruin_policy_version,
        "common_paths_policy_version": spec.common_paths_policy_version,
        "outcome_basis": spec.outcome_basis,
        "resampling_method": spec.resampling_method,
        "simulation_count": spec.simulation_count,
        "path_length": spec.path_length,
        "seed": spec.seed,
        "starting_nav": str(spec.starting_nav),
        "ruin_nav_fraction": str(spec.ruin_nav_fraction),
        "drawdown_thresholds": [str(value) for value in spec.drawdown_thresholds],
        "percentiles": [str(value) for value in spec.percentiles],
        "schedules": [item.as_record() for item in spec.schedules],
        "sample_set_digest": spec.sample_set_digest,
        "sample_count": spec.sample_count,
        "usable_sample_count": spec.usable_sample_count,
        "config_metadata": dict(spec.config_metadata),
    }


def _restore_spec(record: Mapping[str, Any]) -> MonteCarloRiskSpec:
    source = _mapping(record, "spec")
    schedules = tuple(
        RiskPerTradeSchedule(
            schedule_id=_string(item.get("schedule_id"), "schedule_id"),
            fraction_of_nav=_decimal_from_record(
                item.get("fraction_of_nav"), "fraction_of_nav"
            ),
            source=_string(item.get("source"), "source"),
        )
        for item in (
            _mapping(entry, "schedule")
            for entry in _sequence(source.get("schedules"), "schedules")
        )
    )
    spec = MonteCarloRiskSpec(
        feature_id=_string(source.get("feature_id"), "feature_id"),
        policy_version=_string(source.get("policy_version"), "policy_version"),
        sample_policy_version=_string(
            source.get("sample_policy_version"), "sample_policy_version"
        ),
        resampling_policy_version=_string(
            source.get("resampling_policy_version"), "resampling_policy_version"
        ),
        random_stream_policy_version=_string(
            source.get("random_stream_policy_version"), "random_stream_policy_version"
        ),
        path_policy_version=_string(
            source.get("path_policy_version"), "path_policy_version"
        ),
        schedule_scaling_policy_version=_string(
            source.get("schedule_scaling_policy_version"),
            "schedule_scaling_policy_version",
        ),
        drawdown_policy_version=_string(
            source.get("drawdown_policy_version"), "drawdown_policy_version"
        ),
        calmar_policy_version=_string(
            source.get("calmar_policy_version"), "calmar_policy_version"
        ),
        percentile_policy_version=_string(
            source.get("percentile_policy_version"), "percentile_policy_version"
        ),
        ruin_policy_version=_string(
            source.get("ruin_policy_version"), "ruin_policy_version"
        ),
        common_paths_policy_version=_string(
            source.get("common_paths_policy_version"), "common_paths_policy_version"
        ),
        analysis_id=_string(source.get("analysis_id"), "analysis_id"),
        outcome_basis=_string(source.get("outcome_basis"), "outcome_basis"),
        resampling_method=_string(
            source.get("resampling_method"), "resampling_method"
        ),
        simulation_count=_positive_integer(
            source.get("simulation_count"), "simulation_count"
        ),
        path_length=_positive_integer(source.get("path_length"), "path_length"),
        seed=_non_negative_integer(source.get("seed"), "seed"),
        starting_nav=_decimal_from_record(source.get("starting_nav"), "starting_nav"),
        ruin_nav_fraction=_decimal_from_record(
            source.get("ruin_nav_fraction"), "ruin_nav_fraction"
        ),
        drawdown_thresholds=tuple(
            _decimal_from_record(value, "drawdown_threshold")
            for value in _sequence(
                source.get("drawdown_thresholds"), "drawdown_thresholds"
            )
        ),
        percentiles=tuple(
            _decimal_from_record(value, "percentile")
            for value in _sequence(source.get("percentiles"), "percentiles")
        ),
        schedules=schedules,
        sample_set_digest=_string(
            source.get("sample_set_digest"), "sample_set_digest"
        ),
        sample_count=_positive_integer(source.get("sample_count"), "sample_count"),
        usable_sample_count=_positive_integer(
            source.get("usable_sample_count"), "usable_sample_count"
        ),
        config_metadata=_string_mapping(
            source.get("config_metadata"), "config_metadata"
        ),
    )
    if spec.as_record() != dict(source):
        raise MonteCarloRiskError("record does not match reconstructed specification")
    return spec


def _schedules(
    values: Sequence[RiskPerTradeSchedule],
) -> tuple[RiskPerTradeSchedule, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise TypeError("schedules must be a sequence")
    for schedule in values:
        if not isinstance(schedule, RiskPerTradeSchedule):
            raise TypeError("schedules must contain RiskPerTradeSchedule values")
    if len(values) < MINIMUM_SCHEDULES:
        raise MonteCarloRiskError(
            f"at least {MINIMUM_SCHEDULES} risk-per-trade schedules are required"
        )
    identifiers = [schedule.schedule_id for schedule in values]
    if len(set(identifiers)) != len(identifiers):
        raise MonteCarloRiskError("schedule identifiers must be unique")
    fractions = [schedule.fraction_of_nav for schedule in values]
    if len(set(fractions)) != len(fractions):
        raise MonteCarloRiskError("schedules must declare distinct NAV fractions")
    # Canonical order keeps one research question to one analysis_id however
    # the caller happened to list its candidate budgets.
    return tuple(sorted(values, key=lambda item: item.fraction_of_nav))


def _thresholds(values: Sequence[Any]) -> tuple[Decimal, ...]:
    resolved = tuple(
        _decimal(value, "drawdown_threshold") for value in _sequence(values, "thresholds")
    )
    if not resolved:
        raise MonteCarloRiskError("at least one drawdown threshold is required")
    if any(value <= 0 for value in resolved):
        raise MonteCarloRiskError("drawdown thresholds must be positive")
    if len(set(resolved)) != len(resolved):
        raise MonteCarloRiskError("drawdown thresholds must be unique")
    if tuple(sorted(resolved)) != resolved:
        raise MonteCarloRiskError("drawdown thresholds must be ascending")
    return resolved


def _percentiles(values: Sequence[Any]) -> tuple[Decimal, ...]:
    resolved = tuple(
        _decimal(value, "percentile") for value in _sequence(values, "percentiles")
    )
    if not resolved:
        raise MonteCarloRiskError("at least one percentile is required")
    if any(value <= 0 or value > 100 for value in resolved):
        raise MonteCarloRiskError("percentiles must fall in (0, 100]")
    if len(set(resolved)) != len(resolved):
        raise MonteCarloRiskError("percentiles must be unique")
    if tuple(sorted(resolved)) != resolved:
        raise MonteCarloRiskError("percentiles must be ascending")
    return resolved


def _validate_cell(
    value: Decimal | None,
    status: str,
    reason_code: str | None,
    *,
    name: str,
) -> None:
    _require_member(status, SAMPLE_STATUSES, f"{name} status")
    if status == SAMPLE_AVAILABLE:
        if not isinstance(value, Decimal):
            raise MonteCarloRiskError(f"an available {name} must be a Decimal")
        if not value.is_finite():
            raise MonteCarloRiskError(f"an available {name} must be finite")
        if reason_code is not None:
            raise MonteCarloRiskError(
                f"an available {name} must not carry a reason code"
            )
        return
    if value is not None:
        raise MonteCarloRiskError(f"an unmeasured {name} must not carry a value")
    _non_empty(reason_code, f"{name} reason_code")


def _config_metadata(value: Mapping[str, str]) -> dict[str, str]:
    """Carry the source's whole strategy identity, requiring the core keys.

    A source may version more than the strategy itself -- a BTC-191 dataset
    records the BTC-048 feature, price-source, and point-in-time versions too --
    and dropping those would make the persisted evidence less replayable than
    the dataset it was drawn from, so every recorded key is preserved.
    """

    source = _mapping(value, "config_metadata")
    missing = tuple(key for key in REQUIRED_CONFIG_METADATA_KEYS if key not in source)
    if missing:
        raise MonteCarloRiskError(f"config_metadata must include {missing}")
    return {
        _non_empty(key, "config_metadata key"): _non_empty(
            item, f"config_metadata.{key}"
        )
        for key, item in sorted(source.items())
    }


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(MONTE_CARLO_METRIC_EXPONENT, rounding=ROUND_HALF_EVEN)


def _decimal(value: Any, name: str) -> Decimal:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a finite decimal")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as error:
        raise TypeError(f"{name} must be a finite decimal") from error
    if not result.is_finite():
        raise MonteCarloRiskError(f"{name} must be finite")
    return result


def _decimal_from_record(value: Any, name: str) -> Decimal:
    if not isinstance(value, str):
        raise MonteCarloRiskError(f"{name} must be recorded as a string")
    return _decimal(value, name)


def _optional_decimal_from_record(value: Any, name: str) -> Decimal | None:
    if value is None:
        return None
    return _decimal_from_record(value, name)


def _optional_decimal(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _require_member(value: Any, allowed: Sequence[str], name: str) -> str:
    result = _string(value, name)
    if result not in allowed:
        raise MonteCarloRiskError(f"{name} must be one of {tuple(allowed)}")
    return result


def _non_empty(value: Any, name: str) -> str:
    result = _string(value, name)
    if not result.strip():
        raise MonteCarloRiskError(f"{name} must not be empty")
    return result


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise MonteCarloRiskError(f"{name} must be a string")
    return value


def _optional_string(value: Any, name: str) -> str | None:
    return None if value is None else _string(value, name)


def _string_mapping(value: Any, name: str) -> dict[str, str]:
    source = _mapping(value, name)
    return {
        _string(key, f"{name} key"): _string(item, f"{name} value")
        for key, item in source.items()
    }


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise MonteCarloRiskError(f"{name} must be a mapping")
    return value


def _sequence(value: Any, name: str) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise MonteCarloRiskError(f"{name} must be a sequence")
    return tuple(value)


def _positive_integer(value: Any, name: str) -> int:
    result = _non_negative_integer(value, name)
    if result < 1:
        raise MonteCarloRiskError(f"{name} must be a positive integer")
    return result


def _non_negative_integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MonteCarloRiskError(f"{name} must be a non-negative integer")
    return value


def _isoformat(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _optional_utc_from_record(value: Any, name: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise MonteCarloRiskError(f"{name} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise MonteCarloRiskError(f"{name} must be an ISO-8601 timestamp") from error
    return require_utc_datetime(parsed, name)


def _digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
