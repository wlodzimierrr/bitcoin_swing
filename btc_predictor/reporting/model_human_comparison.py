"""Replayable Model Paper versus Human Actual comparison (BTC-203).

The three arms have deliberately narrow meanings:

``MODEL_PAPER``
    Every final BTC-191 paper-trade outcome in the supplied campaign.
``HUMAN_ACTUAL``
    Every BTC-202 manual execution journal entry supplied to the report.
``MODEL_PLUS_HUMAN``
    The recommendation-linked subset of ``HUMAN_ACTUAL``.  ``MANUAL_ONLY``
    trades remain visible in the human arm but are not attributed to the
    model-and-human workflow.

Paper returns use BTC-165 net P&L divided by entry notional.  The manual
journal has no fee or funding fields, so actual returns are explicitly gross
directional price returns.  The report does not invent live costs.  All arms
then use the same normalized return series for win rate, profit factor,
drawdown, Sharpe, and return per trade.  R multiples remain tied to each
source's recorded initial stop and are missing when that evidence is absent.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from typing import Any

from btc_predictor.data import require_utc_datetime
from btc_predictor.journal.actual_trade import (
    FOLLOWED,
    MANUAL_ONLY,
    OVERRIDDEN,
    ActualTradeEntry,
    actual_trade_entry_from_record,
    verify_actual_trade_entry,
)
from btc_predictor.research.paper_trade_outcomes import (
    TRADE_OUTCOME_AVAILABLE,
    PaperTradeOutcomeDataset,
    PaperTradeOutcomeRow,
    restore_paper_trade_outcome_dataset,
)


MODEL_HUMAN_COMPARISON_FEATURE_ID = "MODEL_HUMAN_COMPARISON"
MODEL_HUMAN_COMPARISON_POLICY_VERSION = "MODEL_HUMAN_COMPARISON_V1"
MODEL_HUMAN_ARM_POLICY_VERSION = "PAPER_ALL_ACTUAL_ALL_ACTUAL_LINKED_V1"
MODEL_HUMAN_RETURN_POLICY_VERSION = "NORMALIZED_CLOSED_TRADE_RETURN_V1"
MODEL_HUMAN_PAPER_RETURN_POLICY_VERSION = "BTC_165_NET_PNL_OVER_ENTRY_NOTIONAL_V1"
MODEL_HUMAN_ACTUAL_RETURN_POLICY_VERSION = (
    "ACTUAL_GROSS_DIRECTIONAL_PRICE_RETURN_NO_RECORDED_COSTS_V1"
)
MODEL_HUMAN_R_POLICY_VERSION = "SOURCE_INITIAL_STOP_R_V1"
MODEL_HUMAN_PROFIT_FACTOR_POLICY_VERSION = (
    "GROSS_POSITIVE_RETURN_OVER_ABSOLUTE_NEGATIVE_RETURN_V1"
)
MODEL_HUMAN_DRAWDOWN_POLICY_VERSION = (
    "SEQUENTIAL_FULL_NOTIONAL_COMPOUNDED_CLOSED_RETURN_DRAWDOWN_V1"
)
MODEL_HUMAN_SHARPE_POLICY_VERSION = (
    "CLOSED_TRADE_RETURN_SAMPLE_ZERO_RF_UNANNUALIZED_V1"
)
MODEL_HUMAN_MISSING_VALUE_POLICY_VERSION = "EXPLICIT_UNAVAILABLE_NO_ZERO_FILL_V1"
MODEL_HUMAN_ORDERING_POLICY_VERSION = "CLOSED_AT_THEN_SOURCE_ID_V1"

MODEL_PAPER = "MODEL_PAPER"
HUMAN_ACTUAL = "HUMAN_ACTUAL"
MODEL_PLUS_HUMAN = "MODEL_PLUS_HUMAN"
MODEL_HUMAN_ARMS = (MODEL_PAPER, HUMAN_ACTUAL, MODEL_PLUS_HUMAN)

RETURN_AVAILABLE = "AVAILABLE"
RETURN_OPEN = "OPEN_TRADE"
RETURN_NOT_MEASURED = "NOT_MEASURED"
RETURN_STATUSES = (RETURN_AVAILABLE, RETURN_OPEN, RETURN_NOT_MEASURED)

R_AVAILABLE = "AVAILABLE"
R_OPEN = "OPEN_TRADE"
R_NOT_MEASURED = "NOT_MEASURED"
R_MISSING_INITIAL_STOP = "MISSING_INITIAL_STOP"
R_NON_ADVERSE_INITIAL_STOP = "NON_ADVERSE_INITIAL_STOP"
R_STATUSES = (
    R_AVAILABLE,
    R_OPEN,
    R_NOT_MEASURED,
    R_MISSING_INITIAL_STOP,
    R_NON_ADVERSE_INITIAL_STOP,
)

PROFIT_FACTOR_AVAILABLE = "AVAILABLE"
PROFIT_FACTOR_NO_MEASURED_TRADES = "NO_MEASURED_TRADES"
PROFIT_FACTOR_NO_LOSSES = "UNBOUNDED_NO_LOSSES"
PROFIT_FACTOR_ALL_FLAT = "UNDEFINED_ALL_FLAT"
PROFIT_FACTOR_STATUSES = (
    PROFIT_FACTOR_AVAILABLE,
    PROFIT_FACTOR_NO_MEASURED_TRADES,
    PROFIT_FACTOR_NO_LOSSES,
    PROFIT_FACTOR_ALL_FLAT,
)

DRAWDOWN_AVAILABLE = "AVAILABLE"
DRAWDOWN_NO_CLOSED_TRADES = "UNAVAILABLE_NO_CLOSED_TRADES"
DRAWDOWN_MISSING_RETURNS = "UNAVAILABLE_MISSING_RETURNS"
DRAWDOWN_NON_POSITIVE_EQUITY = "UNDEFINED_NON_POSITIVE_EQUITY"
DRAWDOWN_STATUSES = (
    DRAWDOWN_AVAILABLE,
    DRAWDOWN_NO_CLOSED_TRADES,
    DRAWDOWN_MISSING_RETURNS,
    DRAWDOWN_NON_POSITIVE_EQUITY,
)

SHARPE_AVAILABLE = "AVAILABLE"
SHARPE_INSUFFICIENT_TRADES = "UNAVAILABLE_INSUFFICIENT_TRADES"
SHARPE_MISSING_RETURNS = "UNAVAILABLE_MISSING_RETURNS"
SHARPE_ZERO_DISPERSION = "UNDEFINED_ZERO_DISPERSION"
SHARPE_STATUSES = (
    SHARPE_AVAILABLE,
    SHARPE_INSUFFICIENT_TRADES,
    SHARPE_MISSING_RETURNS,
    SHARPE_ZERO_DISPERSION,
)

MODEL_HUMAN_RATE_EXPONENT = Decimal("1E-12")
MODEL_HUMAN_DECIMAL_PRECISION = 60

MODEL_HUMAN_COMPARISON_REASON_CODES = (
    "MODEL_HUMAN_MODEL_PAPER_FROM_BTC_191",
    "MODEL_HUMAN_HUMAN_ACTUAL_FROM_BTC_202",
    "MODEL_HUMAN_LINKED_ACTUAL_IS_MODEL_PLUS_HUMAN",
    "MODEL_HUMAN_PAPER_RETURNS_INCLUDE_BTC_165_COSTS",
    "MODEL_HUMAN_ACTUAL_RETURNS_EXCLUDE_UNRECORDED_COSTS",
    "MODEL_HUMAN_NORMALIZED_RETURN_METRICS",
    "MODEL_HUMAN_MISSING_VALUES_EXPLICIT",
    "MODEL_HUMAN_POINT_IN_TIME_CUTOFF",
    "MODEL_HUMAN_CONFIG_AND_REASON_PROVENANCE_PERSISTED",
    "MODEL_HUMAN_COMPARISON_COMPLETE",
)

_PAPER_SOURCE = "PAPER_TRADE_OUTCOME"
_ACTUAL_SOURCE = "ACTUAL_TRADE_ENTRY"
_REQUIRED_PAPER_OUTCOMES = ("net_pnl", "entry_notional", "r_multiple")
_CONFIG_IDENTITY_KEYS = ("config_version", "strategy_version", "parameter_set_id")


class ModelHumanComparisonError(ValueError):
    """Raised when BTC-203 evidence is incomplete or incomparable."""


@dataclass(frozen=True)
class ModelHumanTradeOutcome:
    """One source trade normalized for the comparison."""

    source_type: str
    source_id: str
    recommendation_id: int | None
    opened_at: datetime
    closed_at: datetime | None
    return_fraction: Decimal | None
    return_status: str
    r_multiple: Decimal | None
    r_status: str
    manual_decision: str | None
    discretionary_reason_codes: tuple[str, ...] | None

    @property
    def closed(self) -> bool:
        return self.closed_at is not None

    def as_record(self) -> dict[str, Any]:
        _validate_trade_outcome(self)
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "recommendation_id": self.recommendation_id,
            "opened_at": self.opened_at.isoformat(),
            "closed_at": _optional_time(self.closed_at),
            "return_fraction": _optional_decimal(self.return_fraction),
            "return_status": self.return_status,
            "r_multiple": _optional_decimal(self.r_multiple),
            "r_status": self.r_status,
            "manual_decision": self.manual_decision,
            "discretionary_reason_codes": (
                None
                if self.discretionary_reason_codes is None
                else list(self.discretionary_reason_codes)
            ),
        }


@dataclass(frozen=True)
class ModelHumanMetrics:
    """Required BTC-203 metrics plus explicit coverage and availability."""

    trade_count: int
    closed_trade_count: int
    open_trade_count: int
    measured_return_count: int
    unmeasured_return_count: int
    winning_trade_count: int
    losing_trade_count: int
    flat_trade_count: int
    win_rate: Decimal | None
    measured_r_count: int
    unmeasured_r_count: int
    average_r: Decimal | None
    gross_positive_return: Decimal | None
    gross_negative_return: Decimal | None
    profit_factor: Decimal | None
    profit_factor_status: str
    max_drawdown: Decimal | None
    max_drawdown_status: str
    sharpe: Decimal | None
    sharpe_status: str
    return_per_trade: Decimal | None

    def as_record(self) -> dict[str, Any]:
        _validate_metrics(self)
        return {
            "trade_count": self.trade_count,
            "closed_trade_count": self.closed_trade_count,
            "open_trade_count": self.open_trade_count,
            "measured_return_count": self.measured_return_count,
            "unmeasured_return_count": self.unmeasured_return_count,
            "winning_trade_count": self.winning_trade_count,
            "losing_trade_count": self.losing_trade_count,
            "flat_trade_count": self.flat_trade_count,
            "win_rate": _optional_decimal(self.win_rate),
            "measured_r_count": self.measured_r_count,
            "unmeasured_r_count": self.unmeasured_r_count,
            "average_r": _optional_decimal(self.average_r),
            "gross_positive_return": _optional_decimal(
                self.gross_positive_return
            ),
            "gross_negative_return": _optional_decimal(
                self.gross_negative_return
            ),
            "profit_factor": _optional_decimal(self.profit_factor),
            "profit_factor_status": self.profit_factor_status,
            "max_drawdown": _optional_decimal(self.max_drawdown),
            "max_drawdown_status": self.max_drawdown_status,
            "sharpe": _optional_decimal(self.sharpe),
            "sharpe_status": self.sharpe_status,
            "return_per_trade": _optional_decimal(self.return_per_trade),
        }


@dataclass(frozen=True)
class ModelHumanArm:
    """One table column and the exact trade outcomes supporting it."""

    arm_id: str
    trades: tuple[ModelHumanTradeOutcome, ...]
    metrics: ModelHumanMetrics

    def as_record(self) -> dict[str, Any]:
        _validate_arm(self)
        return {
            "arm_id": self.arm_id,
            "trades": [trade.as_record() for trade in self.trades],
            "metrics": self.metrics.as_record(),
        }


@dataclass(frozen=True)
class ModelHumanComparisonReport:
    """Deterministic BTC-203 evidence with full replay inputs."""

    comparison_id: str
    evidence_digest: str
    feature_id: str
    policy_version: str
    arm_policy_version: str
    return_policy_version: str
    paper_return_policy_version: str
    actual_return_policy_version: str
    r_policy_version: str
    profit_factor_policy_version: str
    drawdown_policy_version: str
    sharpe_policy_version: str
    missing_value_policy_version: str
    ordering_policy_version: str
    extraction_time: datetime
    config_metadata: dict[str, str]
    paper_dataset: PaperTradeOutcomeDataset
    actual_trades: tuple[ActualTradeEntry, ...]
    arms: tuple[ModelHumanArm, ...]
    reason_codes: tuple[str, ...]

    def arm(self, arm_id: str) -> ModelHumanArm:
        for arm in self.arms:
            if arm.arm_id == arm_id:
                return arm
        raise KeyError(arm_id)

    @property
    def model_paper(self) -> ModelHumanArm:
        return self.arm(MODEL_PAPER)

    @property
    def human_actual(self) -> ModelHumanArm:
        return self.arm(HUMAN_ACTUAL)

    @property
    def model_plus_human(self) -> ModelHumanArm:
        return self.arm(MODEL_PLUS_HUMAN)

    def as_record(self) -> dict[str, Any]:
        _validate_report(self)
        payload = _report_payload(self)
        if _digest(payload) != self.evidence_digest:
            raise ModelHumanComparisonError(
                "model-human comparison evidence does not match digest"
            )
        return {**payload, "evidence_digest": self.evidence_digest}


def build_model_human_comparison(
    paper_dataset: PaperTradeOutcomeDataset | Mapping[str, Any],
    actual_trades: Sequence[ActualTradeEntry | Mapping[str, Any]],
) -> ModelHumanComparisonReport:
    """Build the three-column BTC-203 comparison at the paper extraction time."""

    dataset = _paper_dataset(paper_dataset)
    _validate_paper_contract(dataset)
    dataset.as_record()
    actual = tuple(_actual_trade(item) for item in actual_trades)
    ordered_actual = tuple(sorted(actual, key=_actual_sort_key))
    _validate_sources(dataset, ordered_actual)

    paper_outcomes = tuple(_paper_outcome(row) for row in dataset.rows)
    actual_outcomes = tuple(_actual_outcome(item) for item in ordered_actual)
    linked_outcomes = tuple(
        outcome
        for trade, outcome in zip(ordered_actual, actual_outcomes, strict=True)
        if trade.manual_decision != MANUAL_ONLY
    )
    arms = (
        _arm(MODEL_PAPER, paper_outcomes),
        _arm(HUMAN_ACTUAL, actual_outcomes),
        _arm(MODEL_PLUS_HUMAN, linked_outcomes),
    )
    report = ModelHumanComparisonReport(
        comparison_id="",
        evidence_digest="",
        feature_id=MODEL_HUMAN_COMPARISON_FEATURE_ID,
        policy_version=MODEL_HUMAN_COMPARISON_POLICY_VERSION,
        arm_policy_version=MODEL_HUMAN_ARM_POLICY_VERSION,
        return_policy_version=MODEL_HUMAN_RETURN_POLICY_VERSION,
        paper_return_policy_version=MODEL_HUMAN_PAPER_RETURN_POLICY_VERSION,
        actual_return_policy_version=MODEL_HUMAN_ACTUAL_RETURN_POLICY_VERSION,
        r_policy_version=MODEL_HUMAN_R_POLICY_VERSION,
        profit_factor_policy_version=MODEL_HUMAN_PROFIT_FACTOR_POLICY_VERSION,
        drawdown_policy_version=MODEL_HUMAN_DRAWDOWN_POLICY_VERSION,
        sharpe_policy_version=MODEL_HUMAN_SHARPE_POLICY_VERSION,
        missing_value_policy_version=MODEL_HUMAN_MISSING_VALUE_POLICY_VERSION,
        ordering_policy_version=MODEL_HUMAN_ORDERING_POLICY_VERSION,
        extraction_time=dataset.extraction_time,
        config_metadata=dict(dataset.config_metadata),
        paper_dataset=dataset,
        actual_trades=ordered_actual,
        arms=arms,
        reason_codes=MODEL_HUMAN_COMPARISON_REASON_CODES,
    )
    report = replace(report, comparison_id=_comparison_id(report))
    _validate_report(report, allow_empty_digest=True)
    return replace(report, evidence_digest=_digest(_report_payload(report)))


def restore_model_human_comparison(
    record: Mapping[str, Any],
) -> ModelHumanComparisonReport:
    """Replay source evidence and reject derived-field or policy tampering."""

    source = _mapping(record, "record")
    unknown = set(source) - set(_REPORT_RECORD_KEYS)
    if unknown:
        raise ModelHumanComparisonError(
            f"model-human comparison record has unknown fields: {sorted(unknown)}"
        )
    rebuilt = build_model_human_comparison(
        _mapping(source.get("paper_dataset"), "paper_dataset"),
        tuple(
            _mapping(item, "actual_trade")
            for item in _sequence(source.get("actual_trades"), "actual_trades")
        ),
    )
    if rebuilt.as_record() != dict(source):
        raise ModelHumanComparisonError(
            "model-human comparison record does not match replayed evidence"
        )
    return rebuilt


def _paper_outcome(row: PaperTradeOutcomeRow) -> ModelHumanTradeOutcome:
    net = row.outcome("net_pnl")
    notional = row.outcome("entry_notional")
    r_cell = row.outcome("r_multiple")
    if (
        net.status == TRADE_OUTCOME_AVAILABLE
        and notional.status == TRADE_OUTCOME_AVAILABLE
    ):
        assert net.value is not None and notional.value is not None
        if notional.value <= 0:
            raise ModelHumanComparisonError(
                "paper entry_notional must be positive when a return is measured"
            )
        return_fraction = _rate(net.value / notional.value)
        return_status = RETURN_AVAILABLE
    else:
        return_fraction = None
        return_status = RETURN_NOT_MEASURED
    if r_cell.status == TRADE_OUTCOME_AVAILABLE:
        assert r_cell.value is not None
        r_multiple = _rate(r_cell.value)
        r_status = R_AVAILABLE
    else:
        r_multiple = None
        r_status = R_NOT_MEASURED
    outcome = ModelHumanTradeOutcome(
        source_type=_PAPER_SOURCE,
        source_id=row.trade_reference,
        recommendation_id=row.recommendation_id,
        opened_at=row.opened_at,
        closed_at=row.closed_at,
        return_fraction=return_fraction,
        return_status=return_status,
        r_multiple=r_multiple,
        r_status=r_status,
        manual_decision=None,
        discretionary_reason_codes=None,
    )
    _validate_trade_outcome(outcome)
    return outcome


def _actual_outcome(trade: ActualTradeEntry) -> ModelHumanTradeOutcome:
    source_id = "actual:" + _digest(trade.as_record())[:24]
    if not trade.is_closed:
        return_fraction = None
        return_status = RETURN_OPEN
        r_multiple = None
        r_status = R_OPEN
    else:
        assert trade.actual_exit_price is not None
        direction = Decimal("1") if trade.direction == "long" else Decimal("-1")
        price_return = (
            direction
            * (trade.actual_exit_price - trade.actual_entry_price)
            / trade.actual_entry_price
        )
        return_fraction = _rate(price_return)
        return_status = RETURN_AVAILABLE
        if trade.actual_stop is None:
            r_multiple = None
            r_status = R_MISSING_INITIAL_STOP
        else:
            risk_distance = (
                trade.actual_entry_price - trade.actual_stop
                if trade.direction == "long"
                else trade.actual_stop - trade.actual_entry_price
            )
            if risk_distance <= 0:
                r_multiple = None
                r_status = R_NON_ADVERSE_INITIAL_STOP
            else:
                r_multiple = _rate(
                    direction
                    * (trade.actual_exit_price - trade.actual_entry_price)
                    / risk_distance
                )
                r_status = R_AVAILABLE
    outcome = ModelHumanTradeOutcome(
        source_type=_ACTUAL_SOURCE,
        source_id=source_id,
        recommendation_id=trade.recommendation_id,
        opened_at=trade.actual_entry_time,
        closed_at=trade.actual_exit_time,
        return_fraction=return_fraction,
        return_status=return_status,
        r_multiple=r_multiple,
        r_status=r_status,
        manual_decision=trade.manual_decision,
        discretionary_reason_codes=trade.discretionary_reason_codes,
    )
    _validate_trade_outcome(outcome)
    return outcome


def _arm(
    arm_id: str,
    outcomes: Sequence[ModelHumanTradeOutcome],
) -> ModelHumanArm:
    ordered = tuple(sorted(outcomes, key=_outcome_sort_key))
    arm = ModelHumanArm(arm_id=arm_id, trades=ordered, metrics=_metrics(ordered))
    _validate_arm(arm)
    return arm


def _metrics(outcomes: Sequence[ModelHumanTradeOutcome]) -> ModelHumanMetrics:
    closed = tuple(item for item in outcomes if item.closed)
    returns = tuple(
        item.return_fraction
        for item in closed
        if item.return_status == RETURN_AVAILABLE
    )
    measured_returns = tuple(item for item in returns if item is not None)
    measured_r = tuple(
        item.r_multiple for item in closed if item.r_status == R_AVAILABLE
    )
    r_values = tuple(item for item in measured_r if item is not None)
    winners = tuple(item for item in measured_returns if item > 0)
    losers = tuple(item for item in measured_returns if item < 0)
    flats = tuple(item for item in measured_returns if item == 0)
    gross_positive = _sum(winners) if measured_returns else None
    gross_negative = _sum(losers) if measured_returns else None
    factor, factor_status = _profit_factor(
        len(measured_returns), gross_positive, gross_negative
    )
    drawdown, drawdown_status = _max_drawdown(closed)
    sharpe, sharpe_status = _sharpe(closed)
    result = ModelHumanMetrics(
        trade_count=len(outcomes),
        closed_trade_count=len(closed),
        open_trade_count=len(outcomes) - len(closed),
        measured_return_count=len(measured_returns),
        unmeasured_return_count=len(closed) - len(measured_returns),
        winning_trade_count=len(winners),
        losing_trade_count=len(losers),
        flat_trade_count=len(flats),
        win_rate=(
            _ratio(Decimal(len(winners)), Decimal(len(measured_returns)))
            if measured_returns
            else None
        ),
        measured_r_count=len(r_values),
        unmeasured_r_count=len(closed) - len(r_values),
        average_r=_mean(r_values),
        gross_positive_return=gross_positive,
        gross_negative_return=gross_negative,
        profit_factor=factor,
        profit_factor_status=factor_status,
        max_drawdown=drawdown,
        max_drawdown_status=drawdown_status,
        sharpe=sharpe,
        sharpe_status=sharpe_status,
        return_per_trade=_mean(measured_returns),
    )
    _validate_metrics(result)
    return result


def _profit_factor(
    measured_count: int,
    gross_positive: Decimal | None,
    gross_negative: Decimal | None,
) -> tuple[Decimal | None, str]:
    if measured_count == 0:
        return None, PROFIT_FACTOR_NO_MEASURED_TRADES
    assert gross_positive is not None and gross_negative is not None
    if gross_negative < 0:
        return _ratio(gross_positive, abs(gross_negative)), PROFIT_FACTOR_AVAILABLE
    if gross_positive > 0:
        return None, PROFIT_FACTOR_NO_LOSSES
    return None, PROFIT_FACTOR_ALL_FLAT


def _max_drawdown(
    closed: Sequence[ModelHumanTradeOutcome],
) -> tuple[Decimal | None, str]:
    if not closed:
        return None, DRAWDOWN_NO_CLOSED_TRADES
    if any(item.return_status != RETURN_AVAILABLE for item in closed):
        return None, DRAWDOWN_MISSING_RETURNS
    equity = Decimal("1")
    peak = equity
    worst = Decimal("0")
    with localcontext(Context(prec=MODEL_HUMAN_DECIMAL_PRECISION)):
        for item in closed:
            assert item.return_fraction is not None
            equity *= Decimal("1") + item.return_fraction
            if equity <= 0:
                return None, DRAWDOWN_NON_POSITIVE_EQUITY
            if equity > peak:
                peak = equity
            decline = (peak - equity) / peak
            if decline > worst:
                worst = decline
    return _rate(worst), DRAWDOWN_AVAILABLE


def _sharpe(
    closed: Sequence[ModelHumanTradeOutcome],
) -> tuple[Decimal | None, str]:
    if any(item.return_status != RETURN_AVAILABLE for item in closed):
        return None, SHARPE_MISSING_RETURNS
    values = tuple(item.return_fraction for item in closed)
    returns = tuple(item for item in values if item is not None)
    if len(returns) < 2:
        return None, SHARPE_INSUFFICIENT_TRADES
    with localcontext(Context(prec=MODEL_HUMAN_DECIMAL_PRECISION)):
        count = Decimal(len(returns))
        mean = sum(returns, Decimal("0")) / count
        variance = sum(
            ((value - mean) ** 2 for value in returns), Decimal("0")
        ) / (count - Decimal("1"))
        if variance <= 0:
            return None, SHARPE_ZERO_DISPERSION
        deviation = variance.sqrt()
        if deviation == 0:
            return None, SHARPE_ZERO_DISPERSION
        return _rate(mean / deviation), SHARPE_AVAILABLE


def _validate_paper_contract(dataset: PaperTradeOutcomeDataset) -> None:
    missing = tuple(
        name
        for name in _REQUIRED_PAPER_OUTCOMES
        if name not in dataset.definition.outcome_names
    )
    if missing:
        raise ModelHumanComparisonError(
            "paper dataset must carry BTC-165 outcomes: " + ", ".join(missing)
        )


def _validate_sources(
    dataset: PaperTradeOutcomeDataset,
    actual: Sequence[ActualTradeEntry],
) -> None:
    records = tuple(_canonical_json(item.as_record()) for item in actual)
    if len(set(records)) != len(records):
        raise ModelHumanComparisonError("actual trade records must be unique")
    paper_ids = tuple(row.recommendation_id for row in dataset.rows)
    if len(set(paper_ids)) != len(paper_ids):
        raise ModelHumanComparisonError(
            "paper recommendation_id values must be unique for attribution"
        )
    paper_by_id = {row.recommendation_id: row for row in dataset.rows}
    paper_symbols = {row.symbol for row in dataset.rows}
    if len(paper_symbols) > 1:
        raise ModelHumanComparisonError(
            "paper dataset must contain one symbol for portfolio comparison"
        )
    paper_symbol = next(iter(paper_symbols), None)
    linked_ids = tuple(
        item.recommendation_id
        for item in actual
        if item.manual_decision != MANUAL_ONLY
    )
    if len(set(linked_ids)) != len(linked_ids):
        raise ModelHumanComparisonError(
            "a recommendation may link to at most one actual trade"
        )
    cutoff = dataset.extraction_time
    for trade in actual:
        if trade.journaled_at > cutoff:
            raise ModelHumanComparisonError(
                "actual trade was journaled after the paper extraction cutoff"
            )
        if paper_symbol is not None and trade.symbol != paper_symbol:
            raise ModelHumanComparisonError(
                "actual trade symbol must match the paper campaign symbol"
            )
        if trade.manual_decision == MANUAL_ONLY:
            continue
        assert trade.recommendation_id is not None
        try:
            paper = paper_by_id[trade.recommendation_id]
        except KeyError as exc:
            raise ModelHumanComparisonError(
                "linked actual recommendation_id is absent from the paper dataset"
            ) from exc
        if trade.symbol != paper.symbol or trade.direction != paper.direction:
            raise ModelHumanComparisonError(
                "linked actual symbol and direction must match its paper trade"
            )
        expected = {
            key: dataset.config_metadata[key] for key in _CONFIG_IDENTITY_KEYS
        }
        if trade.config_metadata != expected:
            raise ModelHumanComparisonError(
                "linked actual configuration must match the paper dataset"
            )


def _validate_trade_outcome(outcome: ModelHumanTradeOutcome) -> None:
    if outcome.source_type not in (_PAPER_SOURCE, _ACTUAL_SOURCE):
        raise ModelHumanComparisonError("unknown trade outcome source_type")
    _non_empty(outcome.source_id, "source_id")
    require_utc_datetime(outcome.opened_at, "opened_at")
    if outcome.closed_at is not None:
        require_utc_datetime(outcome.closed_at, "closed_at")
        if outcome.closed_at < outcome.opened_at:
            raise ModelHumanComparisonError("closed_at must not precede opened_at")
    _choice(outcome.return_status, RETURN_STATUSES, "return_status")
    _choice(outcome.r_status, R_STATUSES, "r_status")
    if outcome.recommendation_id is not None and (
        isinstance(outcome.recommendation_id, bool)
        or not isinstance(outcome.recommendation_id, int)
        or outcome.recommendation_id < 1
    ):
        raise ModelHumanComparisonError(
            "recommendation_id must be a positive integer or None"
        )
    _availability(outcome.return_fraction, outcome.return_status, RETURN_AVAILABLE)
    _availability(outcome.r_multiple, outcome.r_status, R_AVAILABLE)
    if outcome.closed != (outcome.return_status != RETURN_OPEN):
        raise ModelHumanComparisonError("return status must agree with trade finality")
    if outcome.closed != (outcome.r_status != R_OPEN):
        raise ModelHumanComparisonError("R status must agree with trade finality")
    if outcome.source_type == _PAPER_SOURCE:
        if (
            outcome.manual_decision is not None
            or outcome.discretionary_reason_codes is not None
        ):
            raise ModelHumanComparisonError(
                "paper outcomes cannot carry human decisions"
            )
    else:
        _choice(
            outcome.manual_decision,
            (FOLLOWED, OVERRIDDEN, MANUAL_ONLY),
            "manual_decision",
        )
        if outcome.manual_decision == MANUAL_ONLY:
            if outcome.recommendation_id is not None:
                raise ModelHumanComparisonError(
                    "MANUAL_ONLY outcome cannot carry recommendation attribution"
                )
            if outcome.discretionary_reason_codes is not None:
                raise ModelHumanComparisonError(
                    "MANUAL_ONLY outcome cannot carry discretionary reason codes"
                )
        elif outcome.discretionary_reason_codes is None:
            raise ModelHumanComparisonError(
                "linked actual outcome requires discretionary reason codes"
            )
        else:
            for reason in outcome.discretionary_reason_codes:
                _non_empty(reason, "discretionary_reason_code")


def _validate_metrics(metrics: ModelHumanMetrics) -> None:
    counts = (
        metrics.trade_count,
        metrics.closed_trade_count,
        metrics.open_trade_count,
        metrics.measured_return_count,
        metrics.unmeasured_return_count,
        metrics.winning_trade_count,
        metrics.losing_trade_count,
        metrics.flat_trade_count,
        metrics.measured_r_count,
        metrics.unmeasured_r_count,
    )
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in counts
    ):
        raise ModelHumanComparisonError("metric counts must be non-negative integers")
    if metrics.trade_count != metrics.closed_trade_count + metrics.open_trade_count:
        raise ModelHumanComparisonError("trade counts do not reconcile")
    if metrics.closed_trade_count != (
        metrics.measured_return_count + metrics.unmeasured_return_count
    ):
        raise ModelHumanComparisonError("return coverage counts do not reconcile")
    if metrics.measured_return_count != (
        metrics.winning_trade_count
        + metrics.losing_trade_count
        + metrics.flat_trade_count
    ):
        raise ModelHumanComparisonError("return outcome counts do not reconcile")
    if metrics.closed_trade_count != (
        metrics.measured_r_count + metrics.unmeasured_r_count
    ):
        raise ModelHumanComparisonError("R coverage counts do not reconcile")
    _optional_finite(metrics.win_rate, "win_rate")
    if metrics.win_rate is not None and not (
        Decimal("0") <= metrics.win_rate <= Decimal("1")
    ):
        raise ModelHumanComparisonError("win_rate must be in [0, 1]")
    for name in (
        "average_r",
        "gross_positive_return",
        "gross_negative_return",
        "profit_factor",
        "max_drawdown",
        "sharpe",
        "return_per_trade",
    ):
        _optional_finite(getattr(metrics, name), name)
    if (metrics.win_rate is None) != (metrics.measured_return_count == 0):
        raise ModelHumanComparisonError("win_rate availability is inconsistent")
    if (metrics.return_per_trade is None) != (metrics.measured_return_count == 0):
        raise ModelHumanComparisonError("return_per_trade availability is inconsistent")
    if (metrics.average_r is None) != (metrics.measured_r_count == 0):
        raise ModelHumanComparisonError("average_r availability is inconsistent")
    _choice(
        metrics.profit_factor_status,
        PROFIT_FACTOR_STATUSES,
        "profit_factor_status",
    )
    if (metrics.profit_factor is not None) != (
        metrics.profit_factor_status == PROFIT_FACTOR_AVAILABLE
    ):
        raise ModelHumanComparisonError("profit factor availability is inconsistent")
    _choice(metrics.max_drawdown_status, DRAWDOWN_STATUSES, "max_drawdown_status")
    if (metrics.max_drawdown is not None) != (
        metrics.max_drawdown_status == DRAWDOWN_AVAILABLE
    ):
        raise ModelHumanComparisonError("drawdown availability is inconsistent")
    if metrics.max_drawdown is not None and not (
        Decimal("0") <= metrics.max_drawdown < Decimal("1")
    ):
        raise ModelHumanComparisonError("max_drawdown must be in [0, 1)")
    _choice(metrics.sharpe_status, SHARPE_STATUSES, "sharpe_status")
    if (metrics.sharpe is not None) != (metrics.sharpe_status == SHARPE_AVAILABLE):
        raise ModelHumanComparisonError("Sharpe availability is inconsistent")


def _validate_arm(arm: ModelHumanArm) -> None:
    _choice(arm.arm_id, MODEL_HUMAN_ARMS, "arm_id")
    if tuple(sorted(arm.trades, key=_outcome_sort_key)) != arm.trades:
        raise ModelHumanComparisonError("arm trades must follow canonical order")
    for trade in arm.trades:
        _validate_trade_outcome(trade)
    if arm.metrics != _metrics(arm.trades):
        raise ModelHumanComparisonError("arm metrics do not match its trades")


def _validate_report(
    report: ModelHumanComparisonReport,
    *,
    allow_empty_digest: bool = False,
) -> None:
    expected = {
        "feature_id": MODEL_HUMAN_COMPARISON_FEATURE_ID,
        "policy_version": MODEL_HUMAN_COMPARISON_POLICY_VERSION,
        "arm_policy_version": MODEL_HUMAN_ARM_POLICY_VERSION,
        "return_policy_version": MODEL_HUMAN_RETURN_POLICY_VERSION,
        "paper_return_policy_version": MODEL_HUMAN_PAPER_RETURN_POLICY_VERSION,
        "actual_return_policy_version": MODEL_HUMAN_ACTUAL_RETURN_POLICY_VERSION,
        "r_policy_version": MODEL_HUMAN_R_POLICY_VERSION,
        "profit_factor_policy_version": MODEL_HUMAN_PROFIT_FACTOR_POLICY_VERSION,
        "drawdown_policy_version": MODEL_HUMAN_DRAWDOWN_POLICY_VERSION,
        "sharpe_policy_version": MODEL_HUMAN_SHARPE_POLICY_VERSION,
        "missing_value_policy_version": MODEL_HUMAN_MISSING_VALUE_POLICY_VERSION,
        "ordering_policy_version": MODEL_HUMAN_ORDERING_POLICY_VERSION,
    }
    for name, value in expected.items():
        if getattr(report, name) != value:
            raise ModelHumanComparisonError(f"{name} must be {value!r}")
    require_utc_datetime(report.extraction_time, "extraction_time")
    if report.extraction_time != report.paper_dataset.extraction_time:
        raise ModelHumanComparisonError("extraction time must come from BTC-191")
    if report.config_metadata != report.paper_dataset.config_metadata:
        raise ModelHumanComparisonError("config metadata must come from BTC-191")
    if report.reason_codes != MODEL_HUMAN_COMPARISON_REASON_CODES:
        raise ModelHumanComparisonError("unexpected comparison reason codes")
    if tuple(arm.arm_id for arm in report.arms) != MODEL_HUMAN_ARMS:
        raise ModelHumanComparisonError("comparison arms must use canonical order")
    _validate_sources(report.paper_dataset, report.actual_trades)
    canonical_actual = tuple(sorted(report.actual_trades, key=_actual_sort_key))
    if canonical_actual != report.actual_trades:
        raise ModelHumanComparisonError(
            "actual trade sources must follow canonical order"
        )
    for arm in report.arms:
        _validate_arm(arm)
    paper_outcomes = tuple(_paper_outcome(row) for row in report.paper_dataset.rows)
    actual_outcomes = tuple(_actual_outcome(item) for item in report.actual_trades)
    linked_outcomes = tuple(
        outcome
        for trade, outcome in zip(
            report.actual_trades, actual_outcomes, strict=True
        )
        if trade.manual_decision != MANUAL_ONLY
    )
    expected_arms = (
        _arm(MODEL_PAPER, paper_outcomes),
        _arm(HUMAN_ACTUAL, actual_outcomes),
        _arm(MODEL_PLUS_HUMAN, linked_outcomes),
    )
    if report.arms != expected_arms:
        raise ModelHumanComparisonError("comparison arms do not match source evidence")
    expected_id = _comparison_id(report)
    if report.comparison_id != expected_id:
        raise ModelHumanComparisonError("comparison_id does not match source evidence")
    if not allow_empty_digest:
        _non_empty(report.evidence_digest, "evidence_digest")


def _report_payload(report: ModelHumanComparisonReport) -> dict[str, Any]:
    return {
        "comparison_id": report.comparison_id,
        "feature_id": report.feature_id,
        "policy_version": report.policy_version,
        "arm_policy_version": report.arm_policy_version,
        "return_policy_version": report.return_policy_version,
        "paper_return_policy_version": report.paper_return_policy_version,
        "actual_return_policy_version": report.actual_return_policy_version,
        "r_policy_version": report.r_policy_version,
        "profit_factor_policy_version": report.profit_factor_policy_version,
        "drawdown_policy_version": report.drawdown_policy_version,
        "sharpe_policy_version": report.sharpe_policy_version,
        "missing_value_policy_version": report.missing_value_policy_version,
        "ordering_policy_version": report.ordering_policy_version,
        "extraction_time": report.extraction_time.isoformat(),
        "config_metadata": dict(report.config_metadata),
        "paper_dataset": report.paper_dataset.as_record(),
        "actual_trades": [item.as_record() for item in report.actual_trades],
        "arms": [arm.as_record() for arm in report.arms],
        "reason_codes": list(report.reason_codes),
    }


def _comparison_id(report: ModelHumanComparisonReport) -> str:
    return "model-human:" + _digest(
        {
            "policy_version": report.policy_version,
            "paper_dataset_id": report.paper_dataset.dataset_id,
            "paper_evidence_digest": report.paper_dataset.evidence_digest,
            "actual_trades": [item.as_record() for item in report.actual_trades],
        }
    )[:24]


def _paper_dataset(
    value: PaperTradeOutcomeDataset | Mapping[str, Any],
) -> PaperTradeOutcomeDataset:
    if isinstance(value, PaperTradeOutcomeDataset):
        return value
    if isinstance(value, Mapping):
        return restore_paper_trade_outcome_dataset(value)
    raise TypeError("paper_dataset must be a PaperTradeOutcomeDataset or record")


def _actual_trade(
    value: ActualTradeEntry | Mapping[str, Any],
) -> ActualTradeEntry:
    if isinstance(value, ActualTradeEntry):
        verify_actual_trade_entry(value)
        return value
    if isinstance(value, Mapping):
        return actual_trade_entry_from_record(value)
    raise TypeError("actual_trades must contain ActualTradeEntry values or records")


def _actual_sort_key(trade: ActualTradeEntry) -> tuple[Any, ...]:
    return (
        trade.actual_entry_time,
        trade.actual_exit_time or trade.actual_entry_time,
        trade.recommendation_id or 0,
        _canonical_json(trade.as_record()),
    )


def _outcome_sort_key(outcome: ModelHumanTradeOutcome) -> tuple[Any, ...]:
    return (
        outcome.closed_at is None,
        outcome.closed_at or outcome.opened_at,
        outcome.source_id,
    )


def _availability(value: Decimal | None, status: str, available: str) -> None:
    if (value is not None) != (status == available):
        raise ModelHumanComparisonError(
            "metric value availability disagrees with status"
        )
    _optional_finite(value, "metric value")


def _optional_finite(value: Decimal | None, name: str) -> None:
    if value is not None and (
        not isinstance(value, Decimal) or not value.is_finite()
    ):
        raise ModelHumanComparisonError(f"{name} must be a finite Decimal or None")


def _mean(values: Sequence[Decimal]) -> Decimal | None:
    if not values:
        return None
    with localcontext(Context(prec=MODEL_HUMAN_DECIMAL_PRECISION)):
        return _rate(sum(values, Decimal("0")) / Decimal(len(values)))


def _sum(values: Sequence[Decimal]) -> Decimal:
    with localcontext(Context(prec=MODEL_HUMAN_DECIMAL_PRECISION)):
        return _rate(sum(values, Decimal("0")))


def _ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator <= 0:
        raise ModelHumanComparisonError("metric denominator must be positive")
    with localcontext(Context(prec=MODEL_HUMAN_DECIMAL_PRECISION)):
        return _rate(numerator / denominator)


def _rate(value: Decimal) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ModelHumanComparisonError("derived metric must be a finite Decimal")
    with localcontext(Context(prec=MODEL_HUMAN_DECIMAL_PRECISION)):
        return value.quantize(MODEL_HUMAN_RATE_EXPONENT, rounding=ROUND_HALF_EVEN)


def _choice(value: Any, choices: tuple[str, ...], name: str) -> None:
    if value not in choices:
        raise ModelHumanComparisonError(f"{name} must be one of {choices}")


def _non_empty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ModelHumanComparisonError(f"{name} must be non-empty trimmed text")
    return value


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    return value


def _sequence(value: Any, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{name} must be a sequence")
    return value


def _optional_decimal(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _optional_time(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


_REPORT_RECORD_KEYS = frozenset(
    {
        "comparison_id",
        "evidence_digest",
        "feature_id",
        "policy_version",
        "arm_policy_version",
        "return_policy_version",
        "paper_return_policy_version",
        "actual_return_policy_version",
        "r_policy_version",
        "profit_factor_policy_version",
        "drawdown_policy_version",
        "sharpe_policy_version",
        "missing_value_policy_version",
        "ordering_policy_version",
        "extraction_time",
        "config_metadata",
        "paper_dataset",
        "actual_trades",
        "arms",
        "reason_codes",
    }
)


__all__ = [
    "DRAWDOWN_AVAILABLE",
    "DRAWDOWN_MISSING_RETURNS",
    "DRAWDOWN_NO_CLOSED_TRADES",
    "DRAWDOWN_NON_POSITIVE_EQUITY",
    "HUMAN_ACTUAL",
    "MODEL_HUMAN_ACTUAL_RETURN_POLICY_VERSION",
    "MODEL_HUMAN_ARMS",
    "MODEL_HUMAN_COMPARISON_FEATURE_ID",
    "MODEL_HUMAN_COMPARISON_POLICY_VERSION",
    "MODEL_HUMAN_COMPARISON_REASON_CODES",
    "MODEL_HUMAN_DRAWDOWN_POLICY_VERSION",
    "MODEL_HUMAN_PAPER_RETURN_POLICY_VERSION",
    "MODEL_HUMAN_SHARPE_POLICY_VERSION",
    "MODEL_PAPER",
    "MODEL_PLUS_HUMAN",
    "PROFIT_FACTOR_AVAILABLE",
    "PROFIT_FACTOR_ALL_FLAT",
    "PROFIT_FACTOR_NO_LOSSES",
    "PROFIT_FACTOR_NO_MEASURED_TRADES",
    "RETURN_AVAILABLE",
    "RETURN_NOT_MEASURED",
    "RETURN_OPEN",
    "R_AVAILABLE",
    "R_MISSING_INITIAL_STOP",
    "R_NON_ADVERSE_INITIAL_STOP",
    "R_NOT_MEASURED",
    "R_OPEN",
    "SHARPE_AVAILABLE",
    "SHARPE_INSUFFICIENT_TRADES",
    "SHARPE_MISSING_RETURNS",
    "SHARPE_ZERO_DISPERSION",
    "ModelHumanArm",
    "ModelHumanComparisonError",
    "ModelHumanComparisonReport",
    "ModelHumanMetrics",
    "ModelHumanTradeOutcome",
    "build_model_human_comparison",
    "restore_model_human_comparison",
]
