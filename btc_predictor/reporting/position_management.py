"""Existing-position management report (BTC-171).

This module composes already-decided advisory, lifecycle, trailing-stop, and
risk-at-stop records. It does not choose a portfolio action. Mark-to-market
values delegate to the shared BTC-047 quantitative kernels.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from btc_predictor.data import require_utc_datetime
from btc_predictor.portfolio import (
    PositionLifecycle,
    restore_position_lifecycle,
)
from btc_predictor.quant import position_notional, unrealized_pnl
from btc_predictor.reporting.recommendation import (
    RecommendationRendererResult,
    RankedRecommendationReason,
    recommendation_renderer_from_record,
)
from btc_predictor.risk import (
    RiskAtStopResult,
    TrailingStopResult,
    risk_at_stop_from_record,
    trailing_stop_from_record,
)


POSITION_MANAGEMENT_REPORT_FEATURE_ID = "POSITION_MANAGEMENT_REPORT"
POSITION_MANAGEMENT_REPORT_VERSION = "POSITION_MANAGEMENT_REPORT_V1"
POSITION_MANAGEMENT_REPORT_MEDIA_TYPE = "text/plain"
POSITION_MANAGEMENT_REPORT_REASON_CODES = ("POSITION_MANAGEMENT_REPORT_RENDERED",)
POSITION_MANAGEMENT_ACTIONS = ("HOLD", "ADD", "TRIM", "EXIT")

_ACTION_LABELS = {
    "HOLD": "HOLD POSITION",
    "ADD": "ADD TRANCHE",
    "TRIM": "TRIM POSITION",
    "EXIT": "EXIT POSITION",
}
_CONFIG_KEYS = ("config_version", "strategy_version", "parameter_set_id")


@dataclass(frozen=True)
class PositionMark:
    """Point-in-time price used for position valuation."""

    price: Decimal
    marked_at: datetime
    source_id: str

    @classmethod
    def create(cls, *, price: Any, marked_at: datetime, source_id: str) -> PositionMark:
        mark = cls(
            price=_positive_decimal(price, "mark.price"),
            marked_at=_utc_datetime(marked_at, "mark.marked_at"),
            source_id=_single_line(source_id, "mark.source_id"),
        )
        mark.as_record()
        return mark

    @classmethod
    def from_mapping(cls, source: Mapping[str, Any] | Any) -> PositionMark:
        row = _mapping(source, "mark")
        return cls.create(
            price=row.get("price"),
            marked_at=_utc_datetime(row.get("marked_at"), "mark.marked_at"),
            source_id=row.get("source_id"),
        )

    def as_record(self) -> dict[str, Any]:
        return {
            "price": str(_positive_decimal(self.price, "mark.price")),
            "marked_at": require_utc_datetime(
                self.marked_at,
                "mark.marked_at",
            ).isoformat(),
            "source_id": _single_line(self.source_id, "mark.source_id"),
        }


@dataclass(frozen=True)
class PositionManagementMetrics:
    """Shared-kernel mark-to-market values used by the report."""

    market_notional: Decimal
    unrealized_pnl: Decimal
    unrealized_return_fraction: Decimal
    exposure_fraction_nav: Decimal

    @classmethod
    def from_mapping(
        cls,
        source: Mapping[str, Any] | Any,
    ) -> PositionManagementMetrics:
        row = _mapping(source, "metrics")
        return cls(
            market_notional=_non_negative_decimal(
                row.get("market_notional"),
                "market_notional",
            ),
            unrealized_pnl=_decimal(row.get("unrealized_pnl"), "unrealized_pnl"),
            unrealized_return_fraction=_decimal(
                row.get("unrealized_return_fraction"),
                "unrealized_return_fraction",
            ),
            exposure_fraction_nav=_non_negative_decimal(
                row.get("exposure_fraction_nav"),
                "exposure_fraction_nav",
            ),
        )

    def as_record(self) -> dict[str, str]:
        return {
            "market_notional": str(self.market_notional),
            "unrealized_pnl": str(self.unrealized_pnl),
            "unrealized_return_fraction": str(self.unrealized_return_fraction),
            "exposure_fraction_nav": str(self.exposure_fraction_nav),
        }


@dataclass(frozen=True)
class PositionManagementReportResult:
    """Replayable existing-position management report."""

    feature_id: str
    report_version: str
    media_type: str
    advisory: RecommendationRendererResult
    lifecycle: PositionLifecycle
    trailing_stop: TrailingStopResult
    risk_at_stop: RiskAtStopResult
    mark: PositionMark
    metrics: PositionManagementMetrics
    config_metadata: dict[str, str]
    body: str
    complete: bool
    reason_codes: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        _validate_report(self)
        expected_metrics = _calculate_metrics(
            self.lifecycle,
            self.mark,
            self.risk_at_stop,
        )
        if self.metrics != expected_metrics:
            raise ValueError("metrics do not match lifecycle, mark, and NAV")
        expected_body = _render_body(
            advisory=self.advisory,
            lifecycle=self.lifecycle,
            trailing_stop=self.trailing_stop,
            risk_at_stop=self.risk_at_stop,
            mark=self.mark,
            metrics=self.metrics,
            config_metadata=self.config_metadata,
        )
        if self.body != expected_body:
            raise ValueError("body does not match position management inputs")
        return {
            "feature_id": self.feature_id,
            "report_version": self.report_version,
            "media_type": self.media_type,
            "advisory": self.advisory.as_record(),
            "lifecycle": self.lifecycle.as_record(),
            "trailing_stop": self.trailing_stop.as_record(),
            "risk_at_stop": self.risk_at_stop.as_record(),
            "mark": self.mark.as_record(),
            "metrics": self.metrics.as_record(),
            "config_metadata": _config_metadata(self.config_metadata),
            "body": self.body,
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def render_position_management_report(
    *,
    advisory: RecommendationRendererResult,
    lifecycle: PositionLifecycle,
    trailing_stop: TrailingStopResult,
    risk_at_stop: RiskAtStopResult,
    mark_price: Any,
    marked_at: datetime,
    mark_source_id: str,
) -> PositionManagementReportResult:
    """Render one open-position report from validated upstream decisions."""

    if not isinstance(advisory, RecommendationRendererResult):
        raise TypeError("advisory must be a RecommendationRendererResult")
    if not isinstance(lifecycle, PositionLifecycle):
        raise TypeError("lifecycle must be a PositionLifecycle")
    if not isinstance(trailing_stop, TrailingStopResult):
        raise TypeError("trailing_stop must be a TrailingStopResult")
    if not isinstance(risk_at_stop, RiskAtStopResult):
        raise TypeError("risk_at_stop must be a RiskAtStopResult")
    if not lifecycle.is_open:
        raise ValueError("position management report requires an open lifecycle")
    if not risk_at_stop.complete or risk_at_stop.nav is None:
        raise ValueError("position management report requires complete risk-at-stop")
    mark = PositionMark.create(
        price=mark_price,
        marked_at=marked_at,
        source_id=mark_source_id,
    )
    metadata = _config_metadata(advisory.config_metadata)
    metrics = _calculate_metrics(lifecycle, mark, risk_at_stop)
    result = PositionManagementReportResult(
        feature_id=POSITION_MANAGEMENT_REPORT_FEATURE_ID,
        report_version=POSITION_MANAGEMENT_REPORT_VERSION,
        media_type=POSITION_MANAGEMENT_REPORT_MEDIA_TYPE,
        advisory=advisory,
        lifecycle=lifecycle,
        trailing_stop=trailing_stop,
        risk_at_stop=risk_at_stop,
        mark=mark,
        metrics=metrics,
        config_metadata=metadata,
        body="",
        complete=True,
        reason_codes=POSITION_MANAGEMENT_REPORT_REASON_CODES,
    )
    _validate_report(result)
    result = replace(
        result,
        body=_render_body(
            advisory=advisory,
            lifecycle=lifecycle,
            trailing_stop=trailing_stop,
            risk_at_stop=risk_at_stop,
            mark=mark,
            metrics=metrics,
            config_metadata=metadata,
        ),
    )
    result.as_record()
    return result


def position_management_report_from_record(
    source: Mapping[str, Any] | Any,
) -> PositionManagementReportResult:
    """Restore a persisted report and reject source or rendering drift."""

    row = _mapping(source, "position management report")
    result = PositionManagementReportResult(
        feature_id=row.get("feature_id"),
        report_version=row.get("report_version"),
        media_type=row.get("media_type"),
        advisory=recommendation_renderer_from_record(
            _mapping(row.get("advisory"), "advisory"),
        ),
        lifecycle=restore_position_lifecycle(
            _mapping(row.get("lifecycle"), "lifecycle"),
        ),
        trailing_stop=trailing_stop_from_record(
            _mapping(row.get("trailing_stop"), "trailing_stop"),
        ),
        risk_at_stop=risk_at_stop_from_record(
            _mapping(row.get("risk_at_stop"), "risk_at_stop"),
        ),
        mark=PositionMark.from_mapping(row.get("mark")),
        metrics=PositionManagementMetrics.from_mapping(row.get("metrics")),
        config_metadata=_config_metadata(row.get("config_metadata")),
        body=_text_block(row.get("body"), "body"),
        complete=_bool(row.get("complete"), "complete"),
        reason_codes=_reason_codes(row.get("reason_codes"), "reason_codes"),
    )
    result.as_record()
    return result


def _validate_report(result: PositionManagementReportResult) -> None:
    if result.feature_id != POSITION_MANAGEMENT_REPORT_FEATURE_ID:
        raise ValueError(f"feature_id must be {POSITION_MANAGEMENT_REPORT_FEATURE_ID}")
    if result.report_version != POSITION_MANAGEMENT_REPORT_VERSION:
        raise ValueError(f"report_version must be {POSITION_MANAGEMENT_REPORT_VERSION}")
    if result.media_type != POSITION_MANAGEMENT_REPORT_MEDIA_TYPE:
        raise ValueError(f"media_type must be {POSITION_MANAGEMENT_REPORT_MEDIA_TYPE}")
    if result.complete is not True:
        raise ValueError("a validated position management report must be complete")
    if result.reason_codes != POSITION_MANAGEMENT_REPORT_REASON_CODES:
        raise ValueError("reason_codes do not match report state")
    if not isinstance(result.advisory, RecommendationRendererResult):
        raise TypeError("advisory must be a RecommendationRendererResult")
    if not isinstance(result.lifecycle, PositionLifecycle):
        raise TypeError("lifecycle must be a PositionLifecycle")
    if not isinstance(result.trailing_stop, TrailingStopResult):
        raise TypeError("trailing_stop must be a TrailingStopResult")
    if not isinstance(result.risk_at_stop, RiskAtStopResult):
        raise TypeError("risk_at_stop must be a RiskAtStopResult")

    result.advisory.as_record()
    result.lifecycle.as_record()
    result.trailing_stop.as_record()
    result.risk_at_stop.as_record()
    result.mark.as_record()
    metadata = _config_metadata(result.config_metadata)
    sources = (
        ("advisory", result.advisory.config_metadata),
        ("lifecycle", result.lifecycle.config_metadata),
        ("trailing_stop", result.trailing_stop.config_metadata),
        ("risk_at_stop", result.risk_at_stop.config_metadata),
    )
    for name, source_metadata in sources:
        if _config_metadata(source_metadata) != metadata:
            raise ValueError(f"{name} config identity does not match report")

    recommendation = result.advisory.recommendation
    if recommendation.action not in POSITION_MANAGEMENT_ACTIONS:
        raise ValueError(
            "existing-position action must be one of "
            f"{POSITION_MANAGEMENT_ACTIONS}",
        )
    if not result.lifecycle.is_open:
        raise ValueError("position management report requires an open lifecycle")
    if recommendation.symbol != result.lifecycle.symbol:
        raise ValueError("advisory symbol does not match lifecycle")
    if recommendation.direction != result.lifecycle.direction:
        raise ValueError("advisory direction does not match lifecycle")
    if result.mark.marked_at != recommendation.evaluation_time:
        raise ValueError("mark time must match recommendation evaluation_time")
    if (
        result.lifecycle.last_event_at is not None
        and result.lifecycle.last_event_at > result.mark.marked_at
    ):
        raise ValueError("lifecycle contains events after the report mark")

    trailing = result.trailing_stop
    if trailing.direction != result.lifecycle.direction:
        raise ValueError("trailing-stop direction does not match lifecycle")
    if trailing.previous_stop != result.lifecycle.stop_price:
        raise ValueError("trailing previous_stop must match the active lifecycle stop")
    if trailing.evaluated_at != result.mark.marked_at:
        raise ValueError("trailing-stop evaluation time must match report mark")
    if trailing.current_price != result.mark.price:
        raise ValueError("trailing-stop current price must match report mark")

    risk = result.risk_at_stop
    if not risk.complete:
        raise ValueError("position management report requires complete risk-at-stop")
    if risk.direction != result.lifecycle.direction:
        raise ValueError("risk-at-stop direction does not match lifecycle")
    if risk.stop_price != result.lifecycle.stop_price:
        raise ValueError("risk-at-stop must be measured at the active lifecycle stop")
    if risk.nav is None or risk.risk_at_stop is None or risk.risk_fraction_nav is None:
        raise ValueError("complete risk-at-stop values are required")
    _validate_risk_tranches(result.lifecycle, risk)


def _validate_risk_tranches(
    lifecycle: PositionLifecycle,
    risk: RiskAtStopResult,
) -> None:
    expected = {
        str(tranche.tranche_number): (
            tranche.entry_price,
            tranche.entry_price * tranche.quantity,
        )
        for tranche in lifecycle.tranches
    }
    actual = {
        tranche.tranche_id: (tranche.entry_price, tranche.notional)
        for tranche in risk.tranches
    }
    if actual != expected:
        raise ValueError("risk-at-stop tranches do not match the lifecycle ledger")


def _calculate_metrics(
    lifecycle: PositionLifecycle,
    mark: PositionMark,
    risk: RiskAtStopResult,
) -> PositionManagementMetrics:
    if lifecycle.average_entry_price is None or risk.nav is None:
        raise ValueError("position economics and NAV are required")
    notional = _quant_decimal(
        position_notional(float(lifecycle.quantity), float(mark.price)),
        "market_notional",
    )
    pnl = _quant_decimal(
        unrealized_pnl(
            float(lifecycle.average_entry_price),
            float(mark.price),
            float(lifecycle.quantity),
            side=lifecycle.direction,
        ),
        "unrealized_pnl",
    )
    entry_notional = lifecycle.average_entry_price * lifecycle.quantity
    return PositionManagementMetrics(
        market_notional=notional,
        unrealized_pnl=pnl,
        unrealized_return_fraction=pnl / entry_notional,
        exposure_fraction_nav=notional / risk.nav,
    )


def _render_body(
    *,
    advisory: RecommendationRendererResult,
    lifecycle: PositionLifecycle,
    trailing_stop: TrailingStopResult,
    risk_at_stop: RiskAtStopResult,
    mark: PositionMark,
    metrics: PositionManagementMetrics,
    config_metadata: Mapping[str, str],
) -> str:
    metadata = _config_metadata(config_metadata)
    recommendation = advisory.recommendation
    why = tuple(reason for reason in advisory.reasons if reason.severity == "info")
    warnings = tuple(
        reason for reason in advisory.reasons if reason.severity == "warning"
    )
    blockers = tuple(reason for reason in advisory.reasons if reason.severity == "veto")
    stop_instruction = (
        f"MOVE STOP TO {_format_decimal(trailing_stop.stop_price, 2)}"
        if trailing_stop.advanced
        else ("KEEP CURRENT STOP" if trailing_stop.complete else "UNAVAILABLE")
    )
    risk_status = "WITHIN LIMIT" if risk_at_stop.within_maximum else "OVER LIMIT"
    lines = [
        "BTC POSITION MANAGEMENT",
        "",
        f"As Of: {mark.marked_at.isoformat()}",
        f"Market: {lifecycle.symbol}",
        f"Mark Source: {mark.source_id}",
        f"Strategy: {metadata['strategy_version']} / {metadata['parameter_set_id']}",
        "",
        "CURRENT POSITION:",
        f"State: {lifecycle.state.replace('_', ' ')}",
        f"Direction: {lifecycle.direction.upper()}",
        f"Tranches: {lifecycle.tranche_count}",
        f"Quantity: {_format_decimal(lifecycle.quantity, 8)}",
        f"Mark Price: {_format_decimal(mark.price, 2)}",
        f"Market Notional: {_format_decimal(metrics.market_notional, 2)}",
        f"Exposure: {_format_percent(metrics.exposure_fraction_nav)}",
        "",
        f"Average Entry: {_format_decimal(lifecycle.average_entry_price, 2)}",
        f"Current Stop: {_format_decimal(lifecycle.stop_price, 2)}",
        f"Candidate Stop: {_format_optional(trailing_stop.candidate_stop, 2)}",
        f"Stop Instruction: {stop_instruction}",
        "",
        (
            "Unrealized P&L: "
            f"{_format_signed(metrics.unrealized_pnl, 2)} "
            f"({_format_signed_percent(metrics.unrealized_return_fraction)})"
        ),
        f"Hold Score: {_format_optional(recommendation.hold_score, 1)}",
        f"Add Score: {_format_optional(recommendation.add_score, 1)}",
        (
            "Risk At Stop: "
            f"{_format_decimal(risk_at_stop.risk_at_stop, 2)} "
            f"({_format_percent(risk_at_stop.risk_fraction_nav)})"
        ),
        (
            f"Risk Limit: {risk_status} "
            f"(max {_format_percent(risk_at_stop.maximum_fraction_nav)})"
        ),
        "",
        "SUGGESTED ACTION:",
        _ACTION_LABELS[recommendation.action],
        "",
        "BLOCKERS:",
        *_reason_lines(blockers, "[X]"),
        "",
        "WHY:",
        *_reason_lines(why, "[+]"),
        "",
        "RISKS:",
        *_reason_lines(warnings, "[!]"),
        "",
        "SOURCE STATUS:",
        f"Position: {', '.join(lifecycle.reason_codes)}",
        f"Trailing Stop: {', '.join(trailing_stop.reason_codes)}",
        f"Risk At Stop: {', '.join(risk_at_stop.reason_codes)}",
    ]
    return "\n".join(lines)


def _reason_lines(
    reasons: Sequence[RankedRecommendationReason],
    marker: str,
) -> tuple[str, ...]:
    if not reasons:
        return ("None recorded.",)
    return tuple(f"{marker} {reason.detail} [{reason.code}]" for reason in reasons)


def _format_optional(value: Decimal | None, places: int) -> str:
    return "N/A" if value is None else _format_decimal(value, places)


def _format_decimal(value: Decimal | None, places: int) -> str:
    if value is None:
        return "N/A"
    quantum = Decimal(1).scaleb(-places)
    rendered = format(value.quantize(quantum, rounding=ROUND_HALF_UP), ",f")
    rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def _format_signed(value: Decimal, places: int) -> str:
    prefix = "+" if value > 0 else ""
    return f"{prefix}{_format_decimal(value, places)}"


def _format_percent(value: Decimal | None) -> str:
    return "N/A" if value is None else f"{_format_decimal(value * 100, 2)}% NAV"


def _format_signed_percent(value: Decimal) -> str:
    prefix = "+" if value > 0 else ""
    return f"{prefix}{_format_decimal(value * 100, 2)}%"


def _config_metadata(source: Mapping[str, Any] | Any) -> dict[str, str]:
    row = _mapping(source, "config_metadata")
    if set(row) != set(_CONFIG_KEYS):
        raise ValueError(f"config_metadata must exactly contain {_CONFIG_KEYS}")
    return {key: _identifier(row[key], f"config_metadata.{key}") for key in _CONFIG_KEYS}


def _mapping(source: Mapping[str, Any] | Any, name: str) -> Mapping[str, Any]:
    if isinstance(source, Mapping):
        return source
    row = getattr(source, "_mapping", None)
    if isinstance(row, Mapping):
        return row
    raise TypeError(f"{name} must be a mapping or database row")


def _decimal(value: Any, name: str) -> Decimal:
    if value is None or isinstance(value, bool):
        raise TypeError(f"{name} must be numeric")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    return result


def _quant_decimal(value: Any, name: str) -> Decimal:
    return _decimal(value, name)


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


def _utc_datetime(value: Any, name: str) -> datetime:
    parsed = value
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{name} must be an ISO datetime") from exc
    if not isinstance(parsed, datetime):
        raise TypeError(f"{name} must be a datetime")
    return require_utc_datetime(parsed, name)


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty identifier")
    if any(character.isspace() for character in value):
        raise ValueError(f"{name} must not contain whitespace")
    return value


def _single_line(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be non-empty text")
    if "\n" in value or "\r" in value:
        raise ValueError(f"{name} must be single-line text")
    return value


def _text_block(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be non-empty text")
    return value


def _bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be a bool")
    return value


def _reason_codes(value: Any, name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{name} must be a sequence")
    result = tuple(value)
    if any(not isinstance(code, str) or not code.strip() for code in result):
        raise ValueError(f"{name} must contain non-empty strings")
    return result
