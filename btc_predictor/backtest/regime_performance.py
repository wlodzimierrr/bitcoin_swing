"""Out-of-sample regime performance attribution (BTC-183).

The report consumes a completed BTC-182 walk-forward validation and the exact
point-in-time feature evidence used by each *filled* entry decision.  It does
not infer regime or setup from future price action and it does not recompute a
strategy score inside the reporting layer.

Each trade is attributed once on four independent axes:

* the Rulebook's seven directional regime labels collapse to bull, bear, or
  neutral without changing the underlying classification;
* ``VOLATILITY_REGIME_V1`` labels collapse to high or low volatility at the
  existing NORMAL/ELEVATED boundary;
* the entry decision is before or on/after the first U.S. spot-Bitcoin ETF
  trading day (2024-01-11 UTC);
* the detected Phase-1 setup type is retained verbatim.

Closed-trade outcomes use BTC-165 net P&L and R.  A position still open at a
fold boundary retains its realized net P&L and receives that fold's BTC-180
marked unrealized P&L.  Consequently every axis reconciles to the arithmetic
sum of independent fold NAV changes without pretending the folds compound.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import Any

from btc_predictor.backtest.engine import (
    ARM_ENTRY_ACTION,
    BACKTEST_RECONCILIATION_TOLERANCE,
)
from btc_predictor.backtest.walk_forward import (
    WalkForwardValidation,
    restore_walk_forward_validation,
)
from btc_predictor.data import require_utc_datetime
from btc_predictor.features.regime import (
    REGIME_CLASSIFICATION_FEATURE_ID,
    REGIME_CLASSIFICATION_LABELS,
    RegimeClassificationResult,
)
from btc_predictor.features.setup import (
    BEARISH_DISTRIBUTION_FEATURE_ID,
    BEARISH_DISTRIBUTION_SETUP,
    BULLISH_RESET_FEATURE_ID,
    BULLISH_RESET_SETUP,
    BULL_TREND_CONTINUATION_FEATURE_ID,
    BULL_TREND_CONTINUATION_SETUP,
    CAPITULATION_REVERSAL_FEATURE_ID,
    CAPITULATION_REVERSAL_SETUP,
    BearishDistributionResult,
    BullishResetResult,
    BullTrendContinuationResult,
    CapitulationReversalResult,
)
from btc_predictor.features.volatility import (
    VOLATILITY_REGIMES,
    VOLATILITY_REGIME_VERSION,
    VOLATILITY_SCORE_FEATURE_ID,
    VolatilityScoreResult,
)


REGIME_PERFORMANCE_FEATURE_ID = "REGIME_PERFORMANCE_BREAKDOWN"
REGIME_PERFORMANCE_POLICY_VERSION = "REGIME_PERFORMANCE_BREAKDOWN_V1"
ENTRY_CONTEXT_POLICY_VERSION = "FILLED_ENTRY_DECISION_CONTEXT_V1"
MARKET_REGIME_BUCKET_POLICY_VERSION = "RULEBOOK_DIRECTIONAL_REGIME_BUCKETS_V1"
VOLATILITY_BUCKET_POLICY_VERSION = "VOLATILITY_REGIME_BINARY_BUCKETS_V1"
ETF_ERA_POLICY_VERSION = "US_SPOT_BITCOIN_ETF_FIRST_TRADING_DAY_V1"
OPEN_TRADE_MARK_POLICY_VERSION = "FOLD_END_MARK_TO_MARKET_V1"

US_SPOT_BITCOIN_ETF_ERA_START = datetime(2024, 1, 11, tzinfo=UTC)
PERFORMANCE_RATE_EXPONENT = Decimal("1E-12")

BULL_BUCKET = "BULL"
BEAR_BUCKET = "BEAR"
NEUTRAL_BUCKET = "NEUTRAL"
MARKET_REGIME_BUCKETS = (BULL_BUCKET, BEAR_BUCKET, NEUTRAL_BUCKET)

HIGH_VOL_BUCKET = "HIGH_VOL"
LOW_VOL_BUCKET = "LOW_VOL"
VOLATILITY_BUCKETS = (HIGH_VOL_BUCKET, LOW_VOL_BUCKET)

PRE_ETF_BUCKET = "PRE_ETF"
ETF_ERA_BUCKET = "ETF_ERA"
ETF_ERA_BUCKETS = (PRE_ETF_BUCKET, ETF_ERA_BUCKET)

SETUP_BUCKETS = (
    BULL_TREND_CONTINUATION_SETUP,
    BULLISH_RESET_SETUP,
    CAPITULATION_REVERSAL_SETUP,
    BEARISH_DISTRIBUTION_SETUP,
)

MARKET_REGIME_DIMENSION = "market_regime"
VOLATILITY_DIMENSION = "volatility"
ETF_ERA_DIMENSION = "etf_era"
SETUP_DIMENSION = "setup"
REGIME_PERFORMANCE_DIMENSIONS = (
    MARKET_REGIME_DIMENSION,
    VOLATILITY_DIMENSION,
    ETF_ERA_DIMENSION,
    SETUP_DIMENSION,
)

REGIME_PERFORMANCE_REASON_CODES = (
    "REGIME_PERFORMANCE_ENTRY_DECISION_CONTEXT",
    "REGIME_PERFORMANCE_MARKET_REGIME_GROUPS_APPLIED",
    "REGIME_PERFORMANCE_VOLATILITY_GROUPS_APPLIED",
    "REGIME_PERFORMANCE_ETF_ERA_GROUPS_APPLIED",
    "REGIME_PERFORMANCE_SETUP_GROUPS_APPLIED",
    "REGIME_PERFORMANCE_OPEN_TRADES_MARKED",
    "REGIME_PERFORMANCE_NO_TRADES",
    "REGIME_PERFORMANCE_COMPLETE",
)

_BULL_REGIMES = frozenset(("STRONG_BULL", "BULL", "MILD_BULL"))
_BEAR_REGIMES = frozenset(("MILD_BEAR", "BEAR", "STRONG_BEAR"))
_LOW_VOLATILITY_REGIMES = frozenset(("COMPRESSED", "NORMAL"))
_HIGH_VOLATILITY_REGIMES = frozenset(("ELEVATED", "STRESSED"))
_SETUP_FEATURE_IDS = {
    BULL_TREND_CONTINUATION_SETUP: BULL_TREND_CONTINUATION_FEATURE_ID,
    BULLISH_RESET_SETUP: BULLISH_RESET_FEATURE_ID,
    CAPITULATION_REVERSAL_SETUP: CAPITULATION_REVERSAL_FEATURE_ID,
    BEARISH_DISTRIBUTION_SETUP: BEARISH_DISTRIBUTION_FEATURE_ID,
}

type SetupResult = (
    BullTrendContinuationResult
    | BullishResetResult
    | CapitulationReversalResult
    | BearishDistributionResult
)


@dataclass(frozen=True)
class RegimePerformanceContext:
    """Point-in-time classifications belonging to one filled entry intent."""

    context_id: str
    fold_number: int
    entry_source_id: str
    decision_at: datetime
    evidence_available_at: datetime
    regime: str
    volatility_regime: str
    setup: str
    regime_record: dict[str, Any]
    volatility_record: dict[str, Any]
    setup_record: dict[str, Any]
    config_metadata: dict[str, str]

    @property
    def market_regime_bucket(self) -> str:
        return _market_regime_bucket(self.regime)

    @property
    def volatility_bucket(self) -> str:
        return _volatility_bucket(self.volatility_regime)

    @property
    def etf_era_bucket(self) -> str:
        return (
            ETF_ERA_BUCKET
            if self.decision_at >= US_SPOT_BITCOIN_ETF_ERA_START
            else PRE_ETF_BUCKET
        )

    def as_record(self) -> dict[str, Any]:
        _validate_context(self)
        payload = _context_payload(self)
        if _digest(payload) != self.context_id:
            raise ValueError("regime performance context does not match context_id")
        return {**payload, "context_id": self.context_id}


@dataclass(frozen=True)
class TradeRegimeAttribution:
    """One BTC-180 trade with its entry-time BTC-183 classifications."""

    fold_number: int
    trade_number: int
    run_id: str
    trade_evidence_digest: str
    context_id: str
    entry_source_id: str
    decision_at: datetime
    opened_at: datetime
    closed_at: datetime | None
    closed: bool
    regime: str
    market_regime_bucket: str
    volatility_regime: str
    volatility_bucket: str
    etf_era_bucket: str
    setup: str
    realized_net_pnl: Decimal
    marked_unrealized_pnl: Decimal
    total_pnl: Decimal
    r_multiple: Decimal | None

    def as_record(self) -> dict[str, Any]:
        _validate_attribution(self)
        return {
            "fold_number": self.fold_number,
            "trade_number": self.trade_number,
            "run_id": self.run_id,
            "trade_evidence_digest": self.trade_evidence_digest,
            "context_id": self.context_id,
            "entry_source_id": self.entry_source_id,
            "decision_at": self.decision_at.isoformat(),
            "opened_at": self.opened_at.isoformat(),
            "closed_at": _optional_time(self.closed_at),
            "closed": self.closed,
            "regime": self.regime,
            "market_regime_bucket": self.market_regime_bucket,
            "volatility_regime": self.volatility_regime,
            "volatility_bucket": self.volatility_bucket,
            "etf_era_bucket": self.etf_era_bucket,
            "setup": self.setup,
            "realized_net_pnl": str(self.realized_net_pnl),
            "marked_unrealized_pnl": str(self.marked_unrealized_pnl),
            "total_pnl": str(self.total_pnl),
            "r_multiple": _optional_decimal(self.r_multiple),
        }


@dataclass(frozen=True)
class BucketPerformance:
    """Economic totals for one mutually exclusive performance bucket."""

    dimension: str
    bucket: str
    trade_count: int
    closed_trade_count: int
    open_trade_count: int
    winning_closed_trades: int
    losing_closed_trades: int
    flat_closed_trades: int
    realized_net_pnl: Decimal
    marked_unrealized_pnl: Decimal
    total_pnl: Decimal
    r_multiple_count: int
    summed_r_multiple: Decimal
    mean_r_multiple: Decimal | None
    closed_trade_win_rate: Decimal | None

    def as_record(self) -> dict[str, Any]:
        _validate_bucket_performance(self)
        return {
            "dimension": self.dimension,
            "bucket": self.bucket,
            "trade_count": self.trade_count,
            "closed_trade_count": self.closed_trade_count,
            "open_trade_count": self.open_trade_count,
            "winning_closed_trades": self.winning_closed_trades,
            "losing_closed_trades": self.losing_closed_trades,
            "flat_closed_trades": self.flat_closed_trades,
            "realized_net_pnl": str(self.realized_net_pnl),
            "marked_unrealized_pnl": str(self.marked_unrealized_pnl),
            "total_pnl": str(self.total_pnl),
            "r_multiple_count": self.r_multiple_count,
            "summed_r_multiple": str(self.summed_r_multiple),
            "mean_r_multiple": _optional_decimal(self.mean_r_multiple),
            "closed_trade_win_rate": _optional_decimal(self.closed_trade_win_rate),
        }


@dataclass(frozen=True)
class PerformanceBreakdown:
    """All declared buckets for one independent classification axis."""

    dimension: str
    buckets: tuple[BucketPerformance, ...]

    def as_record(self) -> dict[str, Any]:
        _validate_breakdown(self)
        return {
            "dimension": self.dimension,
            "buckets": [bucket.as_record() for bucket in self.buckets],
        }


@dataclass(frozen=True)
class RegimePerformanceBreakdown:
    """Replayable BTC-183 report over one BTC-182 validation."""

    feature_id: str
    policy_version: str
    entry_context_policy_version: str
    market_regime_bucket_policy_version: str
    volatility_bucket_policy_version: str
    volatility_regime_version: str
    etf_era_policy_version: str
    etf_era_start: datetime
    open_trade_mark_policy_version: str
    report_id: str
    evidence_digest: str
    validation: WalkForwardValidation
    contexts: tuple[RegimePerformanceContext, ...]
    attributions: tuple[TradeRegimeAttribution, ...]
    overall: BucketPerformance
    breakdowns: tuple[PerformanceBreakdown, ...]
    config_metadata: dict[str, str]
    reason_codes: tuple[str, ...]

    @property
    def trade_count(self) -> int:
        return len(self.attributions)

    def breakdown(self, dimension: str) -> PerformanceBreakdown:
        for item in self.breakdowns:
            if item.dimension == dimension:
                return item
        raise KeyError(dimension)

    def as_record(self) -> dict[str, Any]:
        _validate_result(self)
        payload = _result_payload(self)
        if _digest(payload) != self.evidence_digest:
            raise ValueError("regime performance evidence does not match digest")
        return {**payload, "evidence_digest": self.evidence_digest}


def regime_performance_context(
    *,
    fold_number: int,
    entry_source_id: str,
    decision_at: datetime,
    evidence_available_at: datetime,
    regime: RegimeClassificationResult,
    volatility: VolatilityScoreResult,
    setup: SetupResult,
) -> RegimePerformanceContext:
    """Bind authoritative entry-time feature results to one queued intent."""

    if not isinstance(regime, RegimeClassificationResult):
        raise TypeError("regime must be a RegimeClassificationResult")
    if not isinstance(volatility, VolatilityScoreResult):
        raise TypeError("volatility must be a VolatilityScoreResult")
    if not isinstance(
        setup,
        (
            BullTrendContinuationResult,
            BullishResetResult,
            CapitulationReversalResult,
            BearishDistributionResult,
        ),
    ):
        raise TypeError("setup must be a supported Phase-1 setup result")
    regime_record = regime.as_record()
    volatility_record = volatility.as_record()
    setup_record = setup.as_record()
    if not regime.complete or regime.regime is None:
        raise ValueError("entry context requires a complete regime classification")
    if not volatility.complete or volatility.volatility_regime is None:
        raise ValueError("entry context requires a known volatility regime")
    if not setup.complete or not setup.detected:
        raise ValueError("entry context requires a complete detected setup")
    if not (
        regime.config_metadata
        == volatility.config_metadata
        == setup.config_metadata
    ):
        raise ValueError("entry context feature evidence must share config identity")

    context = RegimePerformanceContext(
        context_id="",
        fold_number=_positive_integer(fold_number, "fold_number"),
        entry_source_id=_string(entry_source_id, "entry_source_id"),
        decision_at=_utc(decision_at, "decision_at"),
        evidence_available_at=_utc(evidence_available_at, "evidence_available_at"),
        regime=regime.regime,
        volatility_regime=volatility.volatility_regime,
        setup=setup.setup,
        regime_record=_json_copy(regime_record),
        volatility_record=_json_copy(volatility_record),
        setup_record=_json_copy(setup_record),
        config_metadata=dict(regime.config_metadata),
    )
    context = replace(context, context_id=_digest(_context_payload(context)))
    context.as_record()
    return context


def run_regime_performance_breakdown(
    validation: WalkForwardValidation,
    contexts: Sequence[RegimePerformanceContext],
) -> RegimePerformanceBreakdown:
    """Attribute every filled out-of-sample trade to its entry-time context."""

    if not isinstance(validation, WalkForwardValidation):
        raise TypeError("validation must be a WalkForwardValidation")
    validation.as_record()
    if isinstance(contexts, (str, bytes)) or not isinstance(contexts, Sequence):
        raise TypeError("contexts must be a sequence")
    resolved_contexts = tuple(
        sorted(
            contexts,
            key=lambda item: (
                getattr(item, "fold_number", 0),
                getattr(item, "entry_source_id", ""),
            ),
        )
    )
    for context in resolved_contexts:
        if not isinstance(context, RegimePerformanceContext):
            raise TypeError("contexts must contain RegimePerformanceContext values")
        context.as_record()
        if context.config_metadata != validation.config_metadata:
            raise ValueError("entry context config identity must match validation")

    attributions = _derive_attributions(validation, resolved_contexts)
    overall = _bucket_performance("overall", "ALL", attributions)
    breakdowns = _derive_breakdowns(attributions)
    result = RegimePerformanceBreakdown(
        feature_id=REGIME_PERFORMANCE_FEATURE_ID,
        policy_version=REGIME_PERFORMANCE_POLICY_VERSION,
        entry_context_policy_version=ENTRY_CONTEXT_POLICY_VERSION,
        market_regime_bucket_policy_version=MARKET_REGIME_BUCKET_POLICY_VERSION,
        volatility_bucket_policy_version=VOLATILITY_BUCKET_POLICY_VERSION,
        volatility_regime_version=VOLATILITY_REGIME_VERSION,
        etf_era_policy_version=ETF_ERA_POLICY_VERSION,
        etf_era_start=US_SPOT_BITCOIN_ETF_ERA_START,
        open_trade_mark_policy_version=OPEN_TRADE_MARK_POLICY_VERSION,
        report_id="",
        evidence_digest="",
        validation=validation,
        contexts=resolved_contexts,
        attributions=attributions,
        overall=overall,
        breakdowns=breakdowns,
        config_metadata=dict(validation.config_metadata),
        reason_codes=_result_reason_codes(attributions),
    )
    result = replace(result, report_id=_report_id(result))
    _validate_result(result)
    return replace(result, evidence_digest=_digest(_result_payload(result)))


def restore_regime_performance_breakdown(
    record: Mapping[str, Any],
) -> RegimePerformanceBreakdown:
    """Restore persisted BTC-183 evidence and reject drift or tampering."""

    source = _mapping(record, "record")
    validation = restore_walk_forward_validation(
        _mapping(source.get("validation"), "validation")
    )
    contexts = tuple(
        _context_from_record(_mapping(item, "context"))
        for item in _record_sequence(source.get("contexts"), "contexts")
    )
    result = run_regime_performance_breakdown(validation, contexts)
    restored = replace(
        result,
        feature_id=_string(source.get("feature_id"), "feature_id"),
        policy_version=_string(source.get("policy_version"), "policy_version"),
        entry_context_policy_version=_string(
            source.get("entry_context_policy_version"),
            "entry_context_policy_version",
        ),
        market_regime_bucket_policy_version=_string(
            source.get("market_regime_bucket_policy_version"),
            "market_regime_bucket_policy_version",
        ),
        volatility_bucket_policy_version=_string(
            source.get("volatility_bucket_policy_version"),
            "volatility_bucket_policy_version",
        ),
        volatility_regime_version=_string(
            source.get("volatility_regime_version"),
            "volatility_regime_version",
        ),
        etf_era_policy_version=_string(
            source.get("etf_era_policy_version"),
            "etf_era_policy_version",
        ),
        etf_era_start=_utc(source.get("etf_era_start"), "etf_era_start"),
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
        raise ValueError("record does not match reconstructed regime performance")
    return restored


def _derive_attributions(
    validation: WalkForwardValidation,
    contexts: tuple[RegimePerformanceContext, ...],
) -> tuple[TradeRegimeAttribution, ...]:
    context_by_target: dict[tuple[int, str], RegimePerformanceContext] = {}
    for context in contexts:
        target = (context.fold_number, context.entry_source_id)
        if target in context_by_target:
            raise ValueError("entry contexts must not repeat a fold/source target")
        context_by_target[target] = context

    used_targets: set[tuple[int, str]] = set()
    attributions: list[TradeRegimeAttribution] = []
    for fold in validation.folds:
        open_unrealized = (
            fold.result.equity_curve[-1].unrealized_pnl
            if fold.result.equity_curve
            else Decimal("0")
        )
        for trade_number, trade in enumerate(fold.result.trades, start=1):
            if not trade.fills:
                raise ValueError("a backtest trade must contain at least one fill")
            entry_source_id = trade.fills[0].source_event_id
            if entry_source_id is None:
                raise ValueError("a backtest trade entry must retain its source id")
            target = (fold.fold_number, entry_source_id)
            context = context_by_target.get(target)
            if context is None:
                raise ValueError(
                    "every filled trade requires one entry decision context "
                    f"(missing fold {fold.fold_number}, source {entry_source_id!r})"
                )
            decision = _entry_decision_event(fold.result.events, entry_source_id)
            if context.decision_at != decision.occurred_at:
                raise ValueError("entry context decision_at must match queued intent")
            if context.evidence_available_at > context.decision_at:
                raise ValueError("entry context evidence must be point-in-time available")
            if context.decision_at >= trade.opened_at:
                raise ValueError("entry decision must occur before its filled trade")
            used_targets.add(target)
            marked = open_unrealized if not trade.closed else Decimal("0")
            attributions.append(
                TradeRegimeAttribution(
                    fold_number=fold.fold_number,
                    trade_number=trade_number,
                    run_id=fold.result.run_id,
                    trade_evidence_digest=trade.evidence_digest,
                    context_id=context.context_id,
                    entry_source_id=entry_source_id,
                    decision_at=context.decision_at,
                    opened_at=trade.opened_at,
                    closed_at=trade.closed_at,
                    closed=trade.closed,
                    regime=context.regime,
                    market_regime_bucket=context.market_regime_bucket,
                    volatility_regime=context.volatility_regime,
                    volatility_bucket=context.volatility_bucket,
                    etf_era_bucket=context.etf_era_bucket,
                    setup=context.setup,
                    realized_net_pnl=trade.net_pnl,
                    marked_unrealized_pnl=marked,
                    total_pnl=trade.net_pnl + marked,
                    r_multiple=trade.r_multiple,
                )
            )

    extras = set(context_by_target) - used_targets
    if extras:
        target = min(extras)
        raise ValueError(
            "entry contexts must describe filled trades only "
            f"(unused fold {target[0]}, source {target[1]!r})"
        )
    return tuple(attributions)


def _entry_decision_event(events: Sequence[Any], entry_source_id: str) -> Any:
    matches = [
        event
        for event in events
        if event.event_type == "INTENT"
        and event.action == ARM_ENTRY_ACTION
        and event.status == "QUEUED"
        and event.source_id == entry_source_id
    ]
    if len(matches) != 1:
        raise ValueError("a filled entry must map to exactly one queued intent")
    return matches[0]


def _derive_breakdowns(
    attributions: tuple[TradeRegimeAttribution, ...],
) -> tuple[PerformanceBreakdown, ...]:
    definitions = (
        (
            MARKET_REGIME_DIMENSION,
            MARKET_REGIME_BUCKETS,
            lambda item: item.market_regime_bucket,
        ),
        (
            VOLATILITY_DIMENSION,
            VOLATILITY_BUCKETS,
            lambda item: item.volatility_bucket,
        ),
        (ETF_ERA_DIMENSION, ETF_ERA_BUCKETS, lambda item: item.etf_era_bucket),
        (SETUP_DIMENSION, SETUP_BUCKETS, lambda item: item.setup),
    )
    return tuple(
        PerformanceBreakdown(
            dimension=dimension,
            buckets=tuple(
                _bucket_performance(
                    dimension,
                    bucket,
                    tuple(item for item in attributions if classify(item) == bucket),
                )
                for bucket in buckets
            ),
        )
        for dimension, buckets, classify in definitions
    )


def _bucket_performance(
    dimension: str,
    bucket: str,
    attributions: Sequence[TradeRegimeAttribution],
) -> BucketPerformance:
    values = tuple(attributions)
    closed = tuple(item for item in values if item.closed)
    wins = sum(item.realized_net_pnl > 0 for item in closed)
    losses = sum(item.realized_net_pnl < 0 for item in closed)
    flats = len(closed) - wins - losses
    r_values = tuple(
        item.r_multiple for item in values if item.r_multiple is not None
    )
    summed_r = sum(r_values, Decimal("0"))
    return BucketPerformance(
        dimension=dimension,
        bucket=bucket,
        trade_count=len(values),
        closed_trade_count=len(closed),
        open_trade_count=len(values) - len(closed),
        winning_closed_trades=wins,
        losing_closed_trades=losses,
        flat_closed_trades=flats,
        realized_net_pnl=sum(
            (item.realized_net_pnl for item in values), Decimal("0")
        ),
        marked_unrealized_pnl=sum(
            (item.marked_unrealized_pnl for item in values), Decimal("0")
        ),
        total_pnl=sum((item.total_pnl for item in values), Decimal("0")),
        r_multiple_count=len(r_values),
        summed_r_multiple=summed_r,
        mean_r_multiple=(
            _rate(summed_r, len(r_values)) if r_values else None
        ),
        closed_trade_win_rate=(
            _rate(Decimal(wins), len(closed)) if closed else None
        ),
    )


def _validate_result(result: RegimePerformanceBreakdown) -> None:
    expected_versions = {
        "feature_id": REGIME_PERFORMANCE_FEATURE_ID,
        "policy_version": REGIME_PERFORMANCE_POLICY_VERSION,
        "entry_context_policy_version": ENTRY_CONTEXT_POLICY_VERSION,
        "market_regime_bucket_policy_version": MARKET_REGIME_BUCKET_POLICY_VERSION,
        "volatility_bucket_policy_version": VOLATILITY_BUCKET_POLICY_VERSION,
        "volatility_regime_version": VOLATILITY_REGIME_VERSION,
        "etf_era_policy_version": ETF_ERA_POLICY_VERSION,
        "open_trade_mark_policy_version": OPEN_TRADE_MARK_POLICY_VERSION,
    }
    for field_name, expected in expected_versions.items():
        if getattr(result, field_name) != expected:
            raise ValueError(f"{field_name} must be {expected}")
    if result.etf_era_start != US_SPOT_BITCOIN_ETF_ERA_START:
        raise ValueError("etf_era_start does not match the declared era policy")
    result.validation.as_record()
    if result.config_metadata != result.validation.config_metadata:
        raise ValueError("report config identity must match validation")
    for context in result.contexts:
        context.as_record()
        if context.config_metadata != result.config_metadata:
            raise ValueError("entry context config identity must match report")
    expected_attributions = _derive_attributions(result.validation, result.contexts)
    if result.attributions != expected_attributions:
        raise ValueError("trade attributions do not match validation and contexts")
    expected_overall = _bucket_performance("overall", "ALL", result.attributions)
    if result.overall != expected_overall:
        raise ValueError("overall performance does not match trade attributions")
    expected_breakdowns = _derive_breakdowns(result.attributions)
    if result.breakdowns != expected_breakdowns:
        raise ValueError("breakdowns do not match trade attributions")
    expected_fold_total = sum(
        (fold.total_pnl for fold in result.validation.folds), Decimal("0")
    )
    if (
        abs(result.overall.total_pnl - expected_fold_total)
        > BACKTEST_RECONCILIATION_TOLERANCE
    ):
        raise ValueError("attributed P&L must reconcile to independent fold NAV changes")
    for breakdown in result.breakdowns:
        breakdown.as_record()
        if sum(bucket.trade_count for bucket in breakdown.buckets) != result.trade_count:
            raise ValueError("each axis must attribute every trade exactly once")
        if sum(
            (bucket.total_pnl for bucket in breakdown.buckets), Decimal("0")
        ) != result.overall.total_pnl:
            raise ValueError("each axis P&L must reconcile to overall performance")
    if result.reason_codes != _result_reason_codes(result.attributions):
        raise ValueError("reason codes do not describe regime performance")
    _validate_reason_codes(result.reason_codes)
    if result.report_id != _report_id(result):
        raise ValueError("report inputs do not match report_id")


def _validate_context(context: RegimePerformanceContext) -> None:
    _positive_integer(context.fold_number, "fold_number")
    _string(context.entry_source_id, "entry_source_id")
    decision_at = _utc(context.decision_at, "decision_at")
    available_at = _utc(context.evidence_available_at, "evidence_available_at")
    if available_at > decision_at:
        raise ValueError("evidence_available_at must not follow decision_at")
    _market_regime_bucket(context.regime)
    _volatility_bucket(context.volatility_regime)
    if context.setup not in SETUP_BUCKETS:
        raise ValueError("setup is not a supported Phase-1 setup")
    _string_mapping(context.config_metadata, "config_metadata")
    _validate_regime_record(
        context.regime_record,
        regime=context.regime,
        config_metadata=context.config_metadata,
    )
    _validate_volatility_record(
        context.volatility_record,
        volatility_regime=context.volatility_regime,
        config_metadata=context.config_metadata,
    )
    _validate_setup_record(
        context.setup_record,
        setup=context.setup,
        config_metadata=context.config_metadata,
    )


def _validate_regime_record(
    value: Mapping[str, Any],
    *,
    regime: str,
    config_metadata: dict[str, str],
) -> None:
    record = _mapping(value, "regime_record")
    if record.get("feature_id") != REGIME_CLASSIFICATION_FEATURE_ID:
        raise ValueError("regime_record must be REGIME_CLASSIFICATION")
    if record.get("regime") != regime or regime not in REGIME_CLASSIFICATION_LABELS:
        raise ValueError("regime_record does not match regime")
    if record.get("complete") is not True or record.get("score") is None:
        raise ValueError("regime_record must be complete")
    if record.get("config_metadata") != config_metadata:
        raise ValueError("regime_record config identity must match context")
    if record.get("reason_code") != f"{REGIME_CLASSIFICATION_FEATURE_ID}_{regime}":
        raise ValueError("regime_record reason code does not match regime")


def _validate_volatility_record(
    value: Mapping[str, Any],
    *,
    volatility_regime: str,
    config_metadata: dict[str, str],
) -> None:
    record = _mapping(value, "volatility_record")
    if record.get("feature_id") != VOLATILITY_SCORE_FEATURE_ID:
        raise ValueError("volatility_record must be VOLATILITY_SCORE")
    if (
        record.get("volatility_regime") != volatility_regime
        or volatility_regime not in VOLATILITY_REGIMES
    ):
        raise ValueError("volatility_record does not match volatility_regime")
    if record.get("volatility_regime_version") != VOLATILITY_REGIME_VERSION:
        raise ValueError("volatility_record uses an unsupported regime version")
    if record.get("complete") is not True:
        raise ValueError("volatility_record must be complete")
    if record.get("config_metadata") != config_metadata:
        raise ValueError("volatility_record config identity must match context")


def _validate_setup_record(
    value: Mapping[str, Any],
    *,
    setup: str,
    config_metadata: dict[str, str],
) -> None:
    record = _mapping(value, "setup_record")
    expected_feature = _SETUP_FEATURE_IDS[setup]
    if record.get("feature_id") != expected_feature or record.get("setup") != setup:
        raise ValueError("setup_record does not match setup")
    if record.get("complete") is not True or record.get("detected") is not True:
        raise ValueError("setup_record must be complete and detected")
    if record.get("reason_code") != f"{expected_feature}_VALID":
        raise ValueError("setup_record reason code does not match setup")
    if record.get("config_metadata") != config_metadata:
        raise ValueError("setup_record config identity must match context")


def _validate_attribution(attribution: TradeRegimeAttribution) -> None:
    _positive_integer(attribution.fold_number, "fold_number")
    _positive_integer(attribution.trade_number, "trade_number")
    _string(attribution.run_id, "run_id")
    _string(attribution.trade_evidence_digest, "trade_evidence_digest")
    _string(attribution.context_id, "context_id")
    _string(attribution.entry_source_id, "entry_source_id")
    decision_at = _utc(attribution.decision_at, "decision_at")
    opened_at = _utc(attribution.opened_at, "opened_at")
    if decision_at >= opened_at:
        raise ValueError("trade decision must precede opening fill")
    if attribution.closed:
        if attribution.closed_at is None:
            raise ValueError("closed attribution requires closed_at")
        if _utc(attribution.closed_at, "closed_at") < opened_at:
            raise ValueError("closed_at must not precede opened_at")
        if attribution.marked_unrealized_pnl != 0:
            raise ValueError("closed trade cannot retain marked unrealized P&L")
    elif attribution.closed_at is not None:
        raise ValueError("open attribution cannot have closed_at")
    if attribution.market_regime_bucket != _market_regime_bucket(attribution.regime):
        raise ValueError("market regime bucket does not match regime")
    if attribution.volatility_bucket != _volatility_bucket(
        attribution.volatility_regime
    ):
        raise ValueError("volatility bucket does not match volatility regime")
    expected_era = (
        ETF_ERA_BUCKET
        if attribution.decision_at >= US_SPOT_BITCOIN_ETF_ERA_START
        else PRE_ETF_BUCKET
    )
    if attribution.etf_era_bucket != expected_era:
        raise ValueError("ETF era bucket does not match decision timestamp")
    if attribution.setup not in SETUP_BUCKETS:
        raise ValueError("attribution setup is unsupported")
    if attribution.total_pnl != (
        attribution.realized_net_pnl + attribution.marked_unrealized_pnl
    ):
        raise ValueError("trade total P&L must reconcile")


def _validate_bucket_performance(bucket: BucketPerformance) -> None:
    _string(bucket.dimension, "dimension")
    _string(bucket.bucket, "bucket")
    counts = (
        bucket.trade_count,
        bucket.closed_trade_count,
        bucket.open_trade_count,
        bucket.winning_closed_trades,
        bucket.losing_closed_trades,
        bucket.flat_closed_trades,
        bucket.r_multiple_count,
    )
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in counts):
        raise ValueError("bucket counts must be non-negative integers")
    if bucket.trade_count != bucket.closed_trade_count + bucket.open_trade_count:
        raise ValueError("bucket trade counts do not reconcile")
    if bucket.closed_trade_count != (
        bucket.winning_closed_trades
        + bucket.losing_closed_trades
        + bucket.flat_closed_trades
    ):
        raise ValueError("bucket closed-trade outcomes do not reconcile")
    if bucket.total_pnl != bucket.realized_net_pnl + bucket.marked_unrealized_pnl:
        raise ValueError("bucket P&L does not reconcile")
    if (bucket.r_multiple_count == 0) != (bucket.mean_r_multiple is None):
        raise ValueError("mean R availability must match R count")
    if (bucket.closed_trade_count == 0) != (bucket.closed_trade_win_rate is None):
        raise ValueError("win-rate availability must match closed-trade count")
    if bucket.mean_r_multiple is not None and bucket.mean_r_multiple != _rate(
        bucket.summed_r_multiple, bucket.r_multiple_count
    ):
        raise ValueError("mean R does not match summed R")
    if bucket.closed_trade_win_rate is not None:
        expected = _rate(
            Decimal(bucket.winning_closed_trades), bucket.closed_trade_count
        )
        if bucket.closed_trade_win_rate != expected:
            raise ValueError("win rate does not match closed-trade outcomes")


def _validate_breakdown(breakdown: PerformanceBreakdown) -> None:
    expected = {
        MARKET_REGIME_DIMENSION: MARKET_REGIME_BUCKETS,
        VOLATILITY_DIMENSION: VOLATILITY_BUCKETS,
        ETF_ERA_DIMENSION: ETF_ERA_BUCKETS,
        SETUP_DIMENSION: SETUP_BUCKETS,
    }
    if breakdown.dimension not in expected:
        raise ValueError("unsupported regime performance dimension")
    if tuple(bucket.bucket for bucket in breakdown.buckets) != expected[breakdown.dimension]:
        raise ValueError("breakdown buckets do not match dimension vocabulary")
    for bucket in breakdown.buckets:
        bucket.as_record()
        if bucket.dimension != breakdown.dimension:
            raise ValueError("bucket dimension must match its breakdown")


def _result_reason_codes(
    attributions: tuple[TradeRegimeAttribution, ...],
) -> tuple[str, ...]:
    codes = [
        "REGIME_PERFORMANCE_ENTRY_DECISION_CONTEXT",
        "REGIME_PERFORMANCE_MARKET_REGIME_GROUPS_APPLIED",
        "REGIME_PERFORMANCE_VOLATILITY_GROUPS_APPLIED",
        "REGIME_PERFORMANCE_ETF_ERA_GROUPS_APPLIED",
        "REGIME_PERFORMANCE_SETUP_GROUPS_APPLIED",
    ]
    if any(not item.closed for item in attributions):
        codes.append("REGIME_PERFORMANCE_OPEN_TRADES_MARKED")
    if not attributions:
        codes.append("REGIME_PERFORMANCE_NO_TRADES")
    codes.append("REGIME_PERFORMANCE_COMPLETE")
    return tuple(codes)


def _validate_reason_codes(codes: tuple[str, ...]) -> None:
    if len(set(codes)) != len(codes):
        raise ValueError("reason codes must not repeat")
    if any(code not in REGIME_PERFORMANCE_REASON_CODES for code in codes):
        raise ValueError("report contains an undeclared reason code")


def _report_id(result: RegimePerformanceBreakdown) -> str:
    return _digest(
        {
            "policy_version": result.policy_version,
            "entry_context_policy_version": result.entry_context_policy_version,
            "market_regime_bucket_policy_version": (
                result.market_regime_bucket_policy_version
            ),
            "volatility_bucket_policy_version": (
                result.volatility_bucket_policy_version
            ),
            "volatility_regime_version": result.volatility_regime_version,
            "etf_era_policy_version": result.etf_era_policy_version,
            "etf_era_start": result.etf_era_start.isoformat(),
            "open_trade_mark_policy_version": result.open_trade_mark_policy_version,
            "validation_id": result.validation.validation_id,
            "validation_evidence_digest": result.validation.evidence_digest,
            "context_ids": [context.context_id for context in result.contexts],
        }
    )


def _result_payload(result: RegimePerformanceBreakdown) -> dict[str, Any]:
    return {
        "feature_id": result.feature_id,
        "policy_version": result.policy_version,
        "entry_context_policy_version": result.entry_context_policy_version,
        "market_regime_bucket_policy_version": (
            result.market_regime_bucket_policy_version
        ),
        "volatility_bucket_policy_version": result.volatility_bucket_policy_version,
        "volatility_regime_version": result.volatility_regime_version,
        "etf_era_policy_version": result.etf_era_policy_version,
        "etf_era_start": result.etf_era_start.isoformat(),
        "open_trade_mark_policy_version": result.open_trade_mark_policy_version,
        "report_id": result.report_id,
        "validation_id": result.validation.validation_id,
        "validation": result.validation.as_record(),
        "trade_count": result.trade_count,
        "contexts": [context.as_record() for context in result.contexts],
        "attributions": [item.as_record() for item in result.attributions],
        "overall": result.overall.as_record(),
        "breakdowns": [item.as_record() for item in result.breakdowns],
        "config_metadata": dict(result.config_metadata),
        "reason_codes": list(result.reason_codes),
    }


def _context_payload(context: RegimePerformanceContext) -> dict[str, Any]:
    return {
        "fold_number": context.fold_number,
        "entry_source_id": context.entry_source_id,
        "decision_at": context.decision_at.isoformat(),
        "evidence_available_at": context.evidence_available_at.isoformat(),
        "regime": context.regime,
        "market_regime_bucket": context.market_regime_bucket,
        "volatility_regime": context.volatility_regime,
        "volatility_bucket": context.volatility_bucket,
        "setup": context.setup,
        "regime_record": _json_copy(context.regime_record),
        "volatility_record": _json_copy(context.volatility_record),
        "setup_record": _json_copy(context.setup_record),
        "config_metadata": dict(context.config_metadata),
    }


def _context_from_record(source: Mapping[str, Any]) -> RegimePerformanceContext:
    context = RegimePerformanceContext(
        context_id=_string(source.get("context_id"), "context_id"),
        fold_number=_positive_integer(source.get("fold_number"), "fold_number"),
        entry_source_id=_string(source.get("entry_source_id"), "entry_source_id"),
        decision_at=_utc(source.get("decision_at"), "decision_at"),
        evidence_available_at=_utc(
            source.get("evidence_available_at"), "evidence_available_at"
        ),
        regime=_string(source.get("regime"), "regime"),
        volatility_regime=_string(
            source.get("volatility_regime"), "volatility_regime"
        ),
        setup=_string(source.get("setup"), "setup"),
        regime_record=_mapping(source.get("regime_record"), "regime_record"),
        volatility_record=_mapping(
            source.get("volatility_record"), "volatility_record"
        ),
        setup_record=_mapping(source.get("setup_record"), "setup_record"),
        config_metadata=_string_mapping(
            source.get("config_metadata"), "config_metadata"
        ),
    )
    if context.as_record() != dict(source):
        raise ValueError("persisted entry context does not match its evidence")
    return context


def _market_regime_bucket(regime: str) -> str:
    if regime in _BULL_REGIMES:
        return BULL_BUCKET
    if regime in _BEAR_REGIMES:
        return BEAR_BUCKET
    if regime == "NEUTRAL":
        return NEUTRAL_BUCKET
    raise ValueError("regime is not a supported Rulebook classification")


def _volatility_bucket(volatility_regime: str) -> str:
    if volatility_regime in _HIGH_VOLATILITY_REGIMES:
        return HIGH_VOL_BUCKET
    if volatility_regime in _LOW_VOLATILITY_REGIMES:
        return LOW_VOL_BUCKET
    raise ValueError("volatility_regime is not supported")


def _rate(numerator: Decimal, denominator: int) -> Decimal:
    if denominator <= 0:
        raise ValueError("rate denominator must be positive")
    return (numerator / Decimal(denominator)).quantize(
        PERFORMANCE_RATE_EXPONENT,
        rounding=ROUND_HALF_EVEN,
    )


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    return _json_copy(dict(value))


def _record_sequence(value: Any, name: str) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{name} must be a sequence")
    return tuple(value)


def _string_mapping(value: Any, name: str) -> dict[str, str]:
    source = _mapping(value, name)
    result: dict[str, str] = {}
    for key, item in source.items():
        result[_string(key, f"{name} key")] = _string(item, f"{name}.{key}")
    return result


def _string_tuple(value: Any, name: str) -> tuple[str, ...]:
    return tuple(_string(item, name) for item in _record_sequence(value, name))


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value


def _positive_integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _utc(value: Any, name: str) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{name} must be an ISO-8601 timestamp") from exc
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    return require_utc_datetime(value, name)


def _optional_time(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


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
