"""Deterministic plain-text recommendation rendering (BTC-170).

The renderer is a presentation boundary, not another decision engine. It
accepts the persisted ``signals.recommendations`` payload and its ranked reason
rows, validates them, and renders only what those records say. The complete
source snapshot, strategy identity, add-policy values, and rendered body are
retained in ``as_record()`` so an advisory can be replayed or audited later.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Self

from btc_predictor.config import StrategyConfig
from btc_predictor.data import require_utc_datetime
from btc_predictor.db.signals import RECONSTRUCTABLE_RECOMMENDATION_COLUMNS
from btc_predictor.signals.data_quality import (
    RECOMMENDATION_ACTIONS,
    RECOMMENDATION_REASON_SEVERITIES,
    RecommendationReasonCode,
)


RECOMMENDATION_RENDERER_FEATURE_ID = "RECOMMENDATION_RENDERER"
RECOMMENDATION_RENDERER_VERSION = "RECOMMENDATION_RENDERER_V1"
RECOMMENDATION_RENDERER_MEDIA_TYPE = "text/plain"
RECOMMENDATION_RENDERER_REASON_CODES = ("RECOMMENDATION_RENDERED",)

_CONFIG_METADATA_KEYS = (
    "config_version",
    "strategy_version",
    "parameter_set_id",
)
_DIRECTIONS = ("long", "short", "flat")
_ACTION_LABELS = {
    "NO_TRADE": "NO TRADE",
    "WATCH": "WATCH",
    "ENTER": "ENTER INITIAL TRANCHE",
    "HOLD": "HOLD",
    "ADD": "ADD TRANCHE",
    "TRIM": "TRIM POSITION",
    "EXIT": "EXIT POSITION",
}


@dataclass(frozen=True)
class RecommendationView:
    """Validated presentation view of one reconstructable recommendation row."""

    recommendation_id: int
    run_id: int
    evaluation_time: datetime
    symbol: str
    timeframe: str
    regime: str
    setup: str | None
    direction: str
    trend_score: Decimal
    regime_score: Decimal
    flow_score: Decimal
    positioning_score: Decimal
    volatility_score: Decimal
    structure_score: Decimal
    entry_conviction: Decimal
    hold_score: Decimal | None
    add_score: Decimal | None
    entry_zone_lower: Decimal | None
    entry_zone_upper: Decimal | None
    invalidation_level: Decimal | None
    initial_stop: Decimal | None
    rr_ratio: Decimal | None
    risk_fraction_nav: Decimal | None
    risk_amount: Decimal | None
    suggested_notional: Decimal | None
    action: str

    @classmethod
    def from_mapping(cls, source: Mapping[str, Any] | Any) -> Self:
        row = _as_mapping(source, "recommendation")
        missing = set(RECONSTRUCTABLE_RECOMMENDATION_COLUMNS) - set(row)
        if missing:
            raise ValueError(
                "recommendation is missing reconstructable columns: "
                f"{sorted(missing)}",
            )

        lower = _optional_positive_decimal(
            row["entry_zone_lower"],
            "entry_zone_lower",
        )
        upper = _optional_positive_decimal(
            row["entry_zone_upper"],
            "entry_zone_upper",
        )
        if (lower is None) != (upper is None):
            raise ValueError("entry zone must provide both lower and upper bounds")
        if lower is not None and upper is not None and lower > upper:
            raise ValueError("entry_zone_lower must be <= entry_zone_upper")

        direction = _identifier(row["direction"], "direction").lower()
        if direction not in _DIRECTIONS:
            raise ValueError(f"direction must be one of {_DIRECTIONS}")
        action = _identifier(row["action"], "action").upper()
        if action not in RECOMMENDATION_ACTIONS:
            raise ValueError(
                f"action must be one of {RECOMMENDATION_ACTIONS}",
            )

        return cls(
            recommendation_id=_positive_integer(
                row["recommendation_id"],
                "recommendation_id",
            ),
            run_id=_positive_integer(row["run_id"], "run_id"),
            evaluation_time=_utc_datetime(
                row["evaluation_time"],
                "evaluation_time",
            ),
            symbol=_identifier(row["symbol"], "symbol"),
            timeframe=_identifier(row["timeframe"], "timeframe"),
            regime=_identifier(row["regime"], "regime"),
            setup=_optional_identifier(row["setup"], "setup"),
            direction=direction,
            trend_score=_score(row["trend_score"], "trend_score"),
            regime_score=_score(row["regime_score"], "regime_score"),
            flow_score=_score(row["flow_score"], "flow_score"),
            positioning_score=_score(
                row["positioning_score"],
                "positioning_score",
            ),
            volatility_score=_score(
                row["volatility_score"],
                "volatility_score",
            ),
            structure_score=_score(row["structure_score"], "structure_score"),
            entry_conviction=_score(
                row["entry_conviction"],
                "entry_conviction",
            ),
            hold_score=_optional_score(row["hold_score"], "hold_score"),
            add_score=_optional_score(row["add_score"], "add_score"),
            entry_zone_lower=lower,
            entry_zone_upper=upper,
            invalidation_level=_optional_positive_decimal(
                row["invalidation_level"],
                "invalidation_level",
            ),
            initial_stop=_optional_positive_decimal(
                row["initial_stop"],
                "initial_stop",
            ),
            rr_ratio=_optional_non_negative_decimal(row["rr_ratio"], "rr_ratio"),
            risk_fraction_nav=_optional_fraction(
                row["risk_fraction_nav"],
                "risk_fraction_nav",
            ),
            risk_amount=_optional_non_negative_decimal(
                row["risk_amount"],
                "risk_amount",
            ),
            suggested_notional=_optional_non_negative_decimal(
                row["suggested_notional"],
                "suggested_notional",
            ),
            action=action,
        )

    @property
    def suggested_exposure_fraction_nav(self) -> Decimal | None:
        """Derive suggested notional/NAV from the persisted risk identity."""

        if (
            self.suggested_notional is None
            or self.risk_fraction_nav is None
            or self.risk_amount is None
            or self.risk_fraction_nav <= 0
            or self.risk_amount <= 0
        ):
            return None
        nav = self.risk_amount / self.risk_fraction_nav
        return self.suggested_notional / nav

    def as_record(self) -> dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "run_id": self.run_id,
            "evaluation_time": self.evaluation_time.isoformat(),
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "regime": self.regime,
            "setup": self.setup,
            "direction": self.direction,
            "trend_score": str(self.trend_score),
            "regime_score": str(self.regime_score),
            "flow_score": str(self.flow_score),
            "positioning_score": str(self.positioning_score),
            "volatility_score": str(self.volatility_score),
            "structure_score": str(self.structure_score),
            "entry_conviction": str(self.entry_conviction),
            "hold_score": _optional_string(self.hold_score),
            "add_score": _optional_string(self.add_score),
            "entry_zone_lower": _optional_string(self.entry_zone_lower),
            "entry_zone_upper": _optional_string(self.entry_zone_upper),
            "invalidation_level": _optional_string(self.invalidation_level),
            "initial_stop": _optional_string(self.initial_stop),
            "rr_ratio": _optional_string(self.rr_ratio),
            "risk_fraction_nav": _optional_string(self.risk_fraction_nav),
            "risk_amount": _optional_string(self.risk_amount),
            "suggested_notional": _optional_string(self.suggested_notional),
            "action": self.action,
        }


@dataclass(frozen=True)
class PredictorRunView:
    """Run identity needed to prove which config produced a recommendation."""

    run_id: int
    evaluation_time: datetime
    config_version: str
    strategy_version: str
    parameter_set_id: str

    @classmethod
    def from_mapping(cls, source: Mapping[str, Any] | Any) -> Self:
        row = _as_mapping(source, "predictor_run")
        return cls(
            run_id=_positive_integer(row.get("run_id"), "predictor_run.run_id"),
            evaluation_time=_utc_datetime(
                row.get("evaluation_time"),
                "predictor_run.evaluation_time",
            ),
            config_version=_identifier(
                row.get("config_version"),
                "predictor_run.config_version",
            ),
            strategy_version=_identifier(
                row.get("strategy_version"),
                "predictor_run.strategy_version",
            ),
            parameter_set_id=_identifier(
                row.get("parameter_set_id"),
                "predictor_run.parameter_set_id",
            ),
        )

    @property
    def config_metadata(self) -> dict[str, str]:
        return {
            "config_version": self.config_version,
            "strategy_version": self.strategy_version,
            "parameter_set_id": self.parameter_set_id,
        }

    def as_record(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "evaluation_time": self.evaluation_time.isoformat(),
            **self.config_metadata,
        }


@dataclass(frozen=True)
class RankedRecommendationReason:
    """One reason with its immutable display rank and recommendation link."""

    recommendation_id: int
    reason_rank: int
    code: str
    source_component: str
    severity: str
    detail: str

    @classmethod
    def from_mapping(
        cls,
        source: Mapping[str, Any] | Any,
        *,
        recommendation_id: int,
    ) -> Self:
        row = _as_mapping(source, "reason")
        linked_id = row.get("recommendation_id", recommendation_id)
        linked_id = _positive_integer(linked_id, "recommendation_id")
        if linked_id != recommendation_id:
            raise ValueError("reason belongs to a different recommendation")
        severity = _identifier(row.get("severity"), "severity").lower()
        if severity not in RECOMMENDATION_REASON_SEVERITIES:
            raise ValueError(
                "reason severity must be one of "
                f"{RECOMMENDATION_REASON_SEVERITIES}",
            )
        return cls(
            recommendation_id=linked_id,
            reason_rank=_non_negative_integer(
                row.get("reason_rank"),
                "reason_rank",
            ),
            code=_identifier(row.get("code"), "code"),
            source_component=_identifier(
                row.get("source_component"),
                "source_component",
            ),
            severity=severity,
            detail=_line_text(row.get("detail"), "detail"),
        )

    def as_record(self) -> dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "reason_rank": self.reason_rank,
            "code": self.code,
            "source_component": self.source_component,
            "severity": self.severity,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class AddConditionPolicy:
    """Configured BTC-154 conditions displayed beneath an advisory."""

    minimum_add_score: Decimal
    require_profitable_position: bool
    require_stop_improvement: bool
    no_average_down: bool
    maximum_risk_fraction_nav: Decimal

    @classmethod
    def from_strategy_config(cls, strategy_config: StrategyConfig) -> Self:
        if not isinstance(strategy_config, StrategyConfig):
            raise TypeError("strategy_config must be a StrategyConfig")
        return cls(
            minimum_add_score=_score(
                strategy_config.add_thresholds.add_min,
                "minimum_add_score",
            ),
            require_profitable_position=(
                strategy_config.add_thresholds.existing_position_must_be_profitable
            ),
            require_stop_improvement=(
                strategy_config.add_thresholds.stop_must_improve
            ),
            no_average_down=strategy_config.add_thresholds.no_average_down,
            maximum_risk_fraction_nav=_fraction(
                strategy_config.risk.max_risk_at_stop_fraction_nav,
                "maximum_risk_fraction_nav",
            ),
        )

    @classmethod
    def from_mapping(cls, source: Mapping[str, Any] | Any) -> Self:
        row = _as_mapping(source, "add_condition_policy")
        return cls(
            minimum_add_score=_score(
                row.get("minimum_add_score"),
                "minimum_add_score",
            ),
            require_profitable_position=_boolean(
                row.get("require_profitable_position"),
                "require_profitable_position",
            ),
            require_stop_improvement=_boolean(
                row.get("require_stop_improvement"),
                "require_stop_improvement",
            ),
            no_average_down=_boolean(
                row.get("no_average_down"),
                "no_average_down",
            ),
            maximum_risk_fraction_nav=_fraction(
                row.get("maximum_risk_fraction_nav"),
                "maximum_risk_fraction_nav",
            ),
        )

    def as_record(self) -> dict[str, Any]:
        return {
            "minimum_add_score": str(self.minimum_add_score),
            "require_profitable_position": self.require_profitable_position,
            "require_stop_improvement": self.require_stop_improvement,
            "no_average_down": self.no_average_down,
            "maximum_risk_fraction_nav": str(self.maximum_risk_fraction_nav),
        }


@dataclass(frozen=True)
class RecommendationRendererResult:
    """Replayable text advisory and every input used to render it."""

    feature_id: str
    renderer_version: str
    media_type: str
    recommendation: RecommendationView
    predictor_run: PredictorRunView
    reasons: tuple[RankedRecommendationReason, ...]
    add_condition_policy: AddConditionPolicy
    config_metadata: dict[str, str]
    body: str
    complete: bool
    reason_codes: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        """Return a self-validating record sufficient for exact replay."""

        _validate_result_contract(self)
        expected = _render_body(
            self.recommendation,
            self.reasons,
            add_policy=self.add_condition_policy,
            config_metadata=self.config_metadata,
        )
        if self.body != expected:
            raise ValueError("body does not match recommendation renderer inputs")
        return {
            "feature_id": self.feature_id,
            "renderer_version": self.renderer_version,
            "media_type": self.media_type,
            "recommendation": self.recommendation.as_record(),
            "predictor_run": self.predictor_run.as_record(),
            "reasons": [reason.as_record() for reason in self.reasons],
            "add_condition_policy": self.add_condition_policy.as_record(),
            "config_metadata": _config_metadata(self.config_metadata),
            "body": self.body,
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def render_recommendation(
    recommendation: Mapping[str, Any] | Any,
    reasons: Sequence[Mapping[str, Any] | RecommendationReasonCode | Any],
    *,
    predictor_run: Mapping[str, Any] | Any,
    strategy_config: StrategyConfig,
) -> RecommendationRendererResult:
    """Validate and render one recommendation with its persisted explanations."""

    if not isinstance(strategy_config, StrategyConfig):
        raise TypeError("strategy_config must be a StrategyConfig")
    view = RecommendationView.from_mapping(recommendation)
    run = PredictorRunView.from_mapping(predictor_run)
    _validate_source_link(view, run)
    ranked = _normalize_reasons(reasons, recommendation_id=view.recommendation_id)
    metadata = _config_metadata(strategy_config.run_metadata())
    if run.config_metadata != metadata:
        raise ValueError("predictor run config identity does not match strategy_config")
    _validate_action_reasons(view, ranked)
    _validate_action_payload(view)
    add_policy = AddConditionPolicy.from_strategy_config(strategy_config)
    result = RecommendationRendererResult(
        feature_id=RECOMMENDATION_RENDERER_FEATURE_ID,
        renderer_version=RECOMMENDATION_RENDERER_VERSION,
        media_type=RECOMMENDATION_RENDERER_MEDIA_TYPE,
        recommendation=view,
        predictor_run=run,
        reasons=ranked,
        add_condition_policy=add_policy,
        config_metadata=metadata,
        body=_render_body(
            view,
            ranked,
            add_policy=add_policy,
            config_metadata=metadata,
        ),
        complete=True,
        reason_codes=RECOMMENDATION_RENDERER_REASON_CODES,
    )
    result.as_record()
    return result


def recommendation_renderer_from_record(
    source: Mapping[str, Any] | Any,
) -> RecommendationRendererResult:
    """Restore a persisted renderer result and reject replay drift."""

    row = _as_mapping(source, "renderer record")
    recommendation = RecommendationView.from_mapping(row.get("recommendation"))
    run = PredictorRunView.from_mapping(row.get("predictor_run"))
    _validate_source_link(recommendation, run)
    reasons = _normalize_reasons(
        row.get("reasons"),
        recommendation_id=recommendation.recommendation_id,
    )
    result = RecommendationRendererResult(
        feature_id=row.get("feature_id"),
        renderer_version=row.get("renderer_version"),
        media_type=row.get("media_type"),
        recommendation=recommendation,
        predictor_run=run,
        reasons=reasons,
        add_condition_policy=AddConditionPolicy.from_mapping(
            row.get("add_condition_policy"),
        ),
        config_metadata=_config_metadata(row.get("config_metadata")),
        body=_line_block(row.get("body"), "body"),
        complete=_boolean(row.get("complete"), "complete"),
        reason_codes=tuple(row.get("reason_codes", ())),
    )
    result.as_record()
    return result


def _render_body(
    recommendation: RecommendationView,
    reasons: tuple[RankedRecommendationReason, ...],
    *,
    add_policy: AddConditionPolicy,
    config_metadata: Mapping[str, str],
) -> str:
    metadata = _config_metadata(config_metadata)
    entry_zone = (
        "N/A"
        if recommendation.entry_zone_lower is None
        else (
            f"{_format_decimal(recommendation.entry_zone_lower, 2)} - "
            f"{_format_decimal(recommendation.entry_zone_upper, 2)}"
        )
    )
    why = tuple(reason for reason in reasons if reason.severity == "info")
    risks = tuple(reason for reason in reasons if reason.severity == "warning")
    blockers = tuple(reason for reason in reasons if reason.severity == "veto")

    lines = [
        "BTC SWING SIGNAL",
        "",
        f"As Of: {recommendation.evaluation_time.isoformat()}",
        f"Market: {recommendation.symbol} ({recommendation.timeframe})",
        (
            "Strategy: "
            f"{metadata['strategy_version']} / {metadata['parameter_set_id']}"
        ),
        "",
        f"Regime: {_display_identifier(recommendation.regime)} "
        f"({_format_score(recommendation.regime_score)})",
        f"Setup: {_display_optional_identifier(recommendation.setup)}",
        f"Direction: {recommendation.direction.upper()}",
        (
            "Entry Conviction: "
            f"{_format_score(recommendation.entry_conviction)}"
        ),
        "",
        "ACTION:",
        _ACTION_LABELS[recommendation.action],
        "",
        "BLOCKERS:",
        *_reason_lines(blockers, marker="[X]"),
        "",
        "Entry Zone:",
        entry_zone,
        "",
        "Invalidation:",
        _format_optional(recommendation.invalidation_level, 2),
        "",
        "Stop:",
        _format_optional(recommendation.initial_stop, 2),
        "",
        "Risk:",
        _format_percentage(recommendation.risk_fraction_nav),
        "",
        "Suggested Exposure:",
        _format_percentage(recommendation.suggested_exposure_fraction_nav),
        "",
        "R/R:",
        (
            "N/A"
            if recommendation.rr_ratio is None
            else f"{_format_decimal(recommendation.rr_ratio, 2)}R"
        ),
        "",
        f"Trend:       {_format_score(recommendation.trend_score)}",
        f"Flow:        {_format_score(recommendation.flow_score)}",
        f"Positioning: {_format_score(recommendation.positioning_score)}",
        f"Volatility:  {_format_score(recommendation.volatility_score)}",
        f"Structure:   {_format_score(recommendation.structure_score)}",
        f"Hold:        {_format_optional_score(recommendation.hold_score)}",
        f"Add:         {_format_optional_score(recommendation.add_score)}",
        "",
        "WHY:",
        *_reason_lines(why, marker="[+]"),
        "",
        "RISKS:",
        *_reason_lines(risks, marker="[!]"),
        "",
        "ADD CONDITIONS:",
        "[ ] New structural confirmation",
        f"[ ] Add Score >= {_format_score(add_policy.minimum_add_score)}",
        "[ ] Regime, flow, and positioning supportive",
        (
            "[ ] Existing position profitable"
            if add_policy.require_profitable_position
            else "[ ] Existing-position profit gate disabled"
        ),
        (
            "[ ] Stop improves"
            if add_policy.require_stop_improvement
            else "[ ] Stop-improvement gate disabled"
        ),
        (
            "[ ] No average down"
            if add_policy.no_average_down
            else "[ ] No-average-down invariant disabled"
        ),
        (
            "[ ] Aggregate risk-at-stop <= "
            f"{_format_percentage(add_policy.maximum_risk_fraction_nav)}"
        ),
    ]
    return "\n".join(lines)


def _normalize_reasons(
    reasons: Sequence[Mapping[str, Any] | RecommendationReasonCode | Any] | Any,
    *,
    recommendation_id: int,
) -> tuple[RankedRecommendationReason, ...]:
    if isinstance(reasons, (str, bytes)) or not isinstance(reasons, Sequence):
        raise TypeError("reasons must be a sequence")
    normalized: list[RankedRecommendationReason] = []
    for input_rank, reason in enumerate(reasons):
        if isinstance(reason, RankedRecommendationReason):
            row: Mapping[str, Any] | Any = reason.as_record()
        elif isinstance(reason, RecommendationReasonCode):
            row = {
                **reason.as_record(
                    recommendation_id=recommendation_id,
                    reason_rank=input_rank,
                ),
            }
        else:
            row = reason
        normalized.append(
            RankedRecommendationReason.from_mapping(
                row,
                recommendation_id=recommendation_id,
            ),
        )
    if not normalized:
        raise ValueError("reasons must contain at least one explanation")
    ranked = tuple(sorted(normalized, key=lambda reason: reason.reason_rank))
    expected_ranks = tuple(range(len(ranked)))
    actual_ranks = tuple(reason.reason_rank for reason in ranked)
    if actual_ranks != expected_ranks:
        raise ValueError("reason ranks must be unique and contiguous from zero")
    return ranked


def _validate_result_contract(result: RecommendationRendererResult) -> None:
    if result.feature_id != RECOMMENDATION_RENDERER_FEATURE_ID:
        raise ValueError(
            f"feature_id must be {RECOMMENDATION_RENDERER_FEATURE_ID}",
        )
    if result.renderer_version != RECOMMENDATION_RENDERER_VERSION:
        raise ValueError(
            f"renderer_version must be {RECOMMENDATION_RENDERER_VERSION}",
        )
    if result.media_type != RECOMMENDATION_RENDERER_MEDIA_TYPE:
        raise ValueError(
            f"media_type must be {RECOMMENDATION_RENDERER_MEDIA_TYPE}",
        )
    if not result.complete:
        raise ValueError("a validated renderer result must be complete")
    if result.reason_codes != RECOMMENDATION_RENDERER_REASON_CODES:
        raise ValueError("reason_codes do not match renderer state")
    metadata = _config_metadata(result.config_metadata)
    _validate_source_link(result.recommendation, result.predictor_run)
    if result.predictor_run.config_metadata != metadata:
        raise ValueError("predictor run config identity does not match renderer config")
    reasons = _normalize_reasons(
        result.reasons,
        recommendation_id=result.recommendation.recommendation_id,
    )
    _validate_action_reasons(result.recommendation, reasons)
    _validate_action_payload(result.recommendation)


def _validate_source_link(
    recommendation: RecommendationView,
    predictor_run: PredictorRunView,
) -> None:
    if recommendation.run_id != predictor_run.run_id:
        raise ValueError("recommendation belongs to a different predictor run")
    if recommendation.evaluation_time != predictor_run.evaluation_time:
        raise ValueError(
            "recommendation evaluation_time does not match predictor run",
        )


def _validate_action_reasons(
    recommendation: RecommendationView,
    reasons: Sequence[RankedRecommendationReason],
) -> None:
    if recommendation.action in ("ENTER", "ADD") and any(
        reason.severity == "veto" for reason in reasons
    ):
        raise ValueError(
            f"{recommendation.action} cannot be rendered with veto reasons",
        )


def _validate_action_payload(recommendation: RecommendationView) -> None:
    if recommendation.action not in ("ENTER", "ADD"):
        return
    required = {
        "setup": recommendation.setup,
        "entry_zone_lower": recommendation.entry_zone_lower,
        "entry_zone_upper": recommendation.entry_zone_upper,
        "invalidation_level": recommendation.invalidation_level,
        "initial_stop": recommendation.initial_stop,
        "rr_ratio": recommendation.rr_ratio,
        "risk_fraction_nav": recommendation.risk_fraction_nav,
        "risk_amount": recommendation.risk_amount,
        "suggested_notional": recommendation.suggested_notional,
    }
    missing = tuple(name for name, value in required.items() if value is None)
    if missing:
        raise ValueError(
            f"{recommendation.action} requires complete trade geometry: {missing}",
        )
    if recommendation.direction == "flat":
        raise ValueError(f"{recommendation.action} requires a long or short direction")


def _reason_lines(
    reasons: Sequence[RankedRecommendationReason],
    *,
    marker: str,
) -> tuple[str, ...]:
    if not reasons:
        return ("None recorded.",)
    return tuple(
        f"{marker} {reason.detail} [{reason.code}]" for reason in reasons
    )


def _format_percentage(value: Decimal | None) -> str:
    if value is None:
        return "N/A"
    return f"{_format_decimal(value * Decimal('100'), 2)}% NAV"


def _format_score(value: Decimal) -> str:
    return _format_decimal(value, 1)


def _format_optional_score(value: Decimal | None) -> str:
    return "N/A" if value is None else _format_score(value)


def _format_optional(value: Decimal | None, places: int) -> str:
    return "N/A" if value is None else _format_decimal(value, places)


def _format_decimal(value: Decimal, places: int) -> str:
    quantum = Decimal(1).scaleb(-places)
    rounded = value.quantize(quantum, rounding=ROUND_HALF_UP)
    rendered = format(rounded, ",f").rstrip("0").rstrip(".")
    return rendered or "0"


def _display_identifier(value: str) -> str:
    return value.replace("_", " ").upper()


def _display_optional_identifier(value: str | None) -> str:
    return "N/A" if value is None else _display_identifier(value)


def _config_metadata(source: Mapping[str, Any] | Any) -> dict[str, str]:
    row = _as_mapping(source, "config_metadata")
    if set(row) != set(_CONFIG_METADATA_KEYS):
        raise ValueError(
            "config_metadata must exactly contain "
            f"{_CONFIG_METADATA_KEYS}",
        )
    return {
        key: _identifier(row[key], f"config_metadata.{key}")
        for key in _CONFIG_METADATA_KEYS
    }


def _as_mapping(source: Mapping[str, Any] | Any, field_name: str) -> Mapping[str, Any]:
    if isinstance(source, Mapping):
        return source
    row_mapping = getattr(source, "_mapping", None)
    if isinstance(row_mapping, Mapping):
        return row_mapping
    raise TypeError(f"{field_name} must be a mapping or database row")


def _utc_datetime(value: Any, field_name: str) -> datetime:
    parsed = value
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an ISO-8601 datetime") from exc
    if not isinstance(parsed, datetime):
        raise TypeError(f"{field_name} must be a datetime or ISO-8601 string")
    return require_utc_datetime(parsed, field_name)


def _decimal(value: Any, field_name: str) -> Decimal:
    if value is None or isinstance(value, bool):
        raise TypeError(f"{field_name} must be numeric")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not number.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return number


def _score(value: Any, field_name: str) -> Decimal:
    number = _decimal(value, field_name)
    if number < 0 or number > 100:
        raise ValueError(f"{field_name} must be between 0 and 100")
    return number


def _optional_score(value: Any, field_name: str) -> Decimal | None:
    return None if value is None else _score(value, field_name)


def _fraction(value: Any, field_name: str) -> Decimal:
    number = _decimal(value, field_name)
    if number < 0 or number > 1:
        raise ValueError(f"{field_name} must be between 0 and 1")
    return number


def _optional_fraction(value: Any, field_name: str) -> Decimal | None:
    return None if value is None else _fraction(value, field_name)


def _optional_positive_decimal(value: Any, field_name: str) -> Decimal | None:
    if value is None:
        return None
    number = _decimal(value, field_name)
    if number <= 0:
        raise ValueError(f"{field_name} must be positive")
    return number


def _optional_non_negative_decimal(value: Any, field_name: str) -> Decimal | None:
    if value is None:
        return None
    number = _decimal(value, field_name)
    if number < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return number


def _positive_integer(value: Any, field_name: str) -> int:
    number = _non_negative_integer(value, field_name)
    if number < 1:
        raise ValueError(f"{field_name} must be positive")
    return number


def _non_negative_integer(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value


def _identifier(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value or value != value.strip() or any(character.isspace() for character in value):
        raise ValueError(f"{field_name} must be a non-empty identifier")
    return value


def _optional_identifier(value: Any, field_name: str) -> str | None:
    return None if value is None else _identifier(value, field_name)


def _line_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value or value != value.strip() or "\n" in value or "\r" in value:
        raise ValueError(f"{field_name} must be non-empty single-line text")
    return value


def _line_block(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be non-empty text")
    return value


def _boolean(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be a bool")
    return value


def _optional_string(value: Decimal | None) -> str | None:
    return None if value is None else str(value)
