"""Deterministic weekly strategy reporting (BTC-211).

The report is a presentation boundary over BTC-210 daily status snapshots and
BTC-171 current-position reports.  It detects changes only by comparing the
persisted advisory fields, and it displays levels, lifecycle state, scores,
and risk without creating a second strategy or portfolio decision path.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from itertools import pairwise
from typing import Any, Self

from btc_predictor.data import require_utc_datetime
from btc_predictor.reporting.daily_status import (
    DailySystemStatusResult,
    daily_system_status_from_record,
)
from btc_predictor.reporting.position_management import (
    PositionManagementReportResult,
    position_management_report_from_record,
)

WEEKLY_STRATEGY_REPORT_FEATURE_ID = "WEEKLY_STRATEGY_REPORT"
WEEKLY_STRATEGY_REPORT_VERSION = "WEEKLY_STRATEGY_REPORT_V1"
WEEKLY_STRATEGY_REPORT_MEDIA_TYPE = "text/plain"
WEEKLY_STRATEGY_REPORT_LOOKBACK = timedelta(days=7)

WEEKLY_STRATEGY_REPORT_REASON_CODES = (
    "WEEKLY_STRATEGY_REPORT_RENDERED",
    "WEEKLY_STRATEGY_REPORT_REGIME_CHANGED",
    "WEEKLY_STRATEGY_REPORT_REGIME_STABLE",
    "WEEKLY_STRATEGY_REPORT_REGIME_HISTORY_INSUFFICIENT",
    "WEEKLY_STRATEGY_REPORT_SETUP_CHANGED",
    "WEEKLY_STRATEGY_REPORT_SETUP_STABLE",
    "WEEKLY_STRATEGY_REPORT_SETUP_HISTORY_INSUFFICIENT",
    "WEEKLY_STRATEGY_REPORT_PAPER_TRADES_OPEN",
    "WEEKLY_STRATEGY_REPORT_PAPER_TRADES_NONE",
    "WEEKLY_STRATEGY_REPORT_RISK_AVAILABLE",
    "WEEKLY_STRATEGY_REPORT_RISK_UNAVAILABLE",
)

_CONFIG_KEYS = ("config_version", "strategy_version", "parameter_set_id")
_SCORE_FIELDS = (
    ("trend_score", "Trend"),
    ("regime_score", "Regime"),
    ("flow_score", "Flow"),
    ("positioning_score", "Positioning"),
    ("volatility_score", "Volatility"),
    ("structure_score", "Structure"),
    ("entry_conviction", "Entry Conviction"),
    ("hold_score", "Hold"),
    ("add_score", "Add"),
)


@dataclass(frozen=True)
class StrategyStateChange:
    """One observed transition linked to both persisted recommendations."""

    changed_at: datetime
    previous_value: str | None
    current_value: str | None
    previous_recommendation_id: int
    current_recommendation_id: int

    @classmethod
    def from_mapping(cls, source: Mapping[str, Any] | Any) -> Self:
        row = _mapping(source, "strategy state change")
        result = cls(
            changed_at=_utc_datetime(row.get("changed_at"), "changed_at"),
            previous_value=_optional_identifier(
                row.get("previous_value"),
                "previous_value",
            ),
            current_value=_optional_identifier(
                row.get("current_value"),
                "current_value",
            ),
            previous_recommendation_id=_positive_int(
                row.get("previous_recommendation_id"),
                "previous_recommendation_id",
            ),
            current_recommendation_id=_positive_int(
                row.get("current_recommendation_id"),
                "current_recommendation_id",
            ),
        )
        result.as_record()
        return result

    def as_record(self) -> dict[str, Any]:
        previous = _optional_identifier(self.previous_value, "previous_value")
        current = _optional_identifier(self.current_value, "current_value")
        if previous == current:
            raise ValueError("a strategy state change must change value")
        return {
            "changed_at": require_utc_datetime(
                self.changed_at,
                "changed_at",
            ).isoformat(),
            "previous_value": previous,
            "current_value": current,
            "previous_recommendation_id": _positive_int(
                self.previous_recommendation_id,
                "previous_recommendation_id",
            ),
            "current_recommendation_id": _positive_int(
                self.current_recommendation_id,
                "current_recommendation_id",
            ),
        }


@dataclass(frozen=True)
class ScoreMovement:
    """Start-to-current movement for one persisted advisory score."""

    score_name: str
    first_value: Decimal | None
    current_value: Decimal | None
    delta: Decimal | None
    first_recommendation_id: int | None
    current_recommendation_id: int

    @classmethod
    def from_mapping(cls, source: Mapping[str, Any] | Any) -> Self:
        row = _mapping(source, "score movement")
        result = cls(
            score_name=_identifier(row.get("score_name"), "score_name"),
            first_value=_optional_decimal(row.get("first_value"), "first_value"),
            current_value=_optional_decimal(
                row.get("current_value"),
                "current_value",
            ),
            delta=_optional_decimal(row.get("delta"), "delta"),
            first_recommendation_id=_optional_positive_int(
                row.get("first_recommendation_id"),
                "first_recommendation_id",
            ),
            current_recommendation_id=_positive_int(
                row.get("current_recommendation_id"),
                "current_recommendation_id",
            ),
        )
        result.as_record()
        return result

    def as_record(self) -> dict[str, Any]:
        name = _identifier(self.score_name, "score_name")
        allowed = tuple(field for field, _label in _SCORE_FIELDS)
        if name not in allowed:
            raise ValueError(f"score_name must be one of {allowed}")
        first = _optional_decimal(self.first_value, "first_value")
        current = _optional_decimal(self.current_value, "current_value")
        delta = _optional_decimal(self.delta, "delta")
        first_recommendation_id = _optional_positive_int(
            self.first_recommendation_id,
            "first_recommendation_id",
        )
        if (first is None) != (first_recommendation_id is None):
            raise ValueError(
                "first score value and recommendation ID must be available together",
            )
        expected_delta = (
            current - first if first is not None and current is not None else None
        )
        if delta != expected_delta:
            raise ValueError("score delta does not match first and current values")
        return {
            "score_name": name,
            "first_value": _optional_string(first),
            "current_value": _optional_string(current),
            "delta": _optional_string(delta),
            "first_recommendation_id": first_recommendation_id,
            "current_recommendation_id": _positive_int(
                self.current_recommendation_id,
                "current_recommendation_id",
            ),
        }


@dataclass(frozen=True)
class WeeklyStrategyReportResult:
    """Replayable weekly summary with all authoritative source records."""

    feature_id: str
    report_version: str
    media_type: str
    window_start: datetime
    window_end: datetime
    daily_statuses: tuple[DailySystemStatusResult, ...]
    position_reports: tuple[PositionManagementReportResult, ...]
    regime_changes: tuple[StrategyStateChange, ...]
    setup_changes: tuple[StrategyStateChange, ...]
    score_movements: tuple[ScoreMovement, ...]
    config_metadata: dict[str, str]
    body: str
    complete: bool
    reason_codes: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        statuses, positions = _validate_report(self)
        expected_regime = _state_changes(statuses, "regime")
        expected_setup = _state_changes(statuses, "setup")
        expected_scores = _score_movements(statuses)
        if self.regime_changes != expected_regime:
            raise ValueError("regime_changes do not match daily status history")
        if self.setup_changes != expected_setup:
            raise ValueError("setup_changes do not match daily status history")
        if self.score_movements != expected_scores:
            raise ValueError("score_movements do not match daily status history")
        expected_body = _render_body(
            window_start=self.window_start,
            window_end=self.window_end,
            statuses=statuses,
            positions=positions,
            regime_changes=expected_regime,
            setup_changes=expected_setup,
            score_movements=expected_scores,
            config_metadata=self.config_metadata,
        )
        if self.body != expected_body:
            raise ValueError("body does not match weekly strategy report inputs")
        return {
            "feature_id": self.feature_id,
            "report_version": self.report_version,
            "media_type": self.media_type,
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "daily_statuses": [item.as_record() for item in statuses],
            "position_reports": [item.as_record() for item in positions],
            "regime_changes": [item.as_record() for item in expected_regime],
            "setup_changes": [item.as_record() for item in expected_setup],
            "score_movements": [item.as_record() for item in expected_scores],
            "config_metadata": _config_metadata(self.config_metadata),
            "body": self.body,
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def render_weekly_strategy_report(
    *,
    daily_statuses: Sequence[DailySystemStatusResult],
    position_management_reports: Sequence[PositionManagementReportResult] = (),
) -> WeeklyStrategyReportResult:
    """Render the rolling seven-day report ending at the latest daily status."""

    statuses = _ordered_daily_statuses(daily_statuses)
    positions = _ordered_position_reports(position_management_reports)
    window_end = statuses[-1].as_of
    window_start = window_end - WEEKLY_STRATEGY_REPORT_LOOKBACK
    regime_changes = _state_changes(statuses, "regime")
    setup_changes = _state_changes(statuses, "setup")
    score_movements = _score_movements(statuses)
    metadata = _config_metadata(statuses[-1].config_metadata)
    result = WeeklyStrategyReportResult(
        feature_id=WEEKLY_STRATEGY_REPORT_FEATURE_ID,
        report_version=WEEKLY_STRATEGY_REPORT_VERSION,
        media_type=WEEKLY_STRATEGY_REPORT_MEDIA_TYPE,
        window_start=window_start,
        window_end=window_end,
        daily_statuses=statuses,
        position_reports=positions,
        regime_changes=regime_changes,
        setup_changes=setup_changes,
        score_movements=score_movements,
        config_metadata=metadata,
        body="",
        complete=True,
        reason_codes=_report_reason_codes(
            statuses,
            positions,
            regime_changes,
            setup_changes,
        ),
    )
    _validate_report(result)
    result = replace(
        result,
        body=_render_body(
            window_start=window_start,
            window_end=window_end,
            statuses=statuses,
            positions=positions,
            regime_changes=regime_changes,
            setup_changes=setup_changes,
            score_movements=score_movements,
            config_metadata=metadata,
        ),
    )
    result.as_record()
    return result


def weekly_strategy_report_from_record(
    source: Mapping[str, Any] | Any,
) -> WeeklyStrategyReportResult:
    """Restore a persisted report and reject source, summary, or body drift."""

    row = _mapping(source, "weekly strategy report record")
    statuses_value = _sequence(row.get("daily_statuses"), "daily_statuses")
    positions_value = _sequence(row.get("position_reports"), "position_reports")
    regime_value = _sequence(row.get("regime_changes"), "regime_changes")
    setup_value = _sequence(row.get("setup_changes"), "setup_changes")
    scores_value = _sequence(row.get("score_movements"), "score_movements")
    result = WeeklyStrategyReportResult(
        feature_id=row.get("feature_id"),
        report_version=row.get("report_version"),
        media_type=row.get("media_type"),
        window_start=_utc_datetime(row.get("window_start"), "window_start"),
        window_end=_utc_datetime(row.get("window_end"), "window_end"),
        daily_statuses=tuple(
            daily_system_status_from_record(_mapping(item, "daily status"))
            for item in statuses_value
        ),
        position_reports=tuple(
            position_management_report_from_record(
                _mapping(item, "position management report"),
            )
            for item in positions_value
        ),
        regime_changes=tuple(
            StrategyStateChange.from_mapping(item) for item in regime_value
        ),
        setup_changes=tuple(
            StrategyStateChange.from_mapping(item) for item in setup_value
        ),
        score_movements=tuple(
            ScoreMovement.from_mapping(item) for item in scores_value
        ),
        config_metadata=_config_metadata(row.get("config_metadata")),
        body=_text_block(row.get("body"), "body"),
        complete=_bool(row.get("complete"), "complete"),
        reason_codes=_reason_codes(row.get("reason_codes"), "reason_codes"),
    )
    record = result.as_record()
    if record != dict(row):
        raise ValueError("weekly strategy report record is not canonical")
    return result


def _validate_report(
    result: WeeklyStrategyReportResult,
) -> tuple[
    tuple[DailySystemStatusResult, ...],
    tuple[PositionManagementReportResult, ...],
]:
    if result.feature_id != WEEKLY_STRATEGY_REPORT_FEATURE_ID:
        raise ValueError(f"feature_id must be {WEEKLY_STRATEGY_REPORT_FEATURE_ID}")
    if result.report_version != WEEKLY_STRATEGY_REPORT_VERSION:
        raise ValueError(f"report_version must be {WEEKLY_STRATEGY_REPORT_VERSION}")
    if result.media_type != WEEKLY_STRATEGY_REPORT_MEDIA_TYPE:
        raise ValueError(f"media_type must be {WEEKLY_STRATEGY_REPORT_MEDIA_TYPE}")
    if result.complete is not True:
        raise ValueError("a validated weekly strategy report must be complete")

    statuses = _ordered_daily_statuses(result.daily_statuses)
    positions = _ordered_position_reports(result.position_reports)
    window_end = require_utc_datetime(result.window_end, "window_end")
    window_start = require_utc_datetime(result.window_start, "window_start")
    if window_end != statuses[-1].as_of:
        raise ValueError("window_end must match the latest daily status")
    if window_start != window_end - WEEKLY_STRATEGY_REPORT_LOOKBACK:
        raise ValueError("window_start must be exactly seven days before window_end")
    if statuses[0].as_of < window_start:
        raise ValueError("daily statuses must be inside the seven-day window")

    metadata = _config_metadata(result.config_metadata)
    latest = statuses[-1]
    latest_recommendation = latest.advisory.recommendation
    account_identity = _account_identity(statuses[0])
    for status in statuses:
        status.as_record()
        if _config_metadata(status.config_metadata) != metadata:
            raise ValueError("daily status config identity does not match report")
        recommendation = status.advisory.recommendation
        if recommendation.symbol != latest_recommendation.symbol:
            raise ValueError("daily status symbols must match")
        if recommendation.timeframe != latest_recommendation.timeframe:
            raise ValueError("daily status timeframes must match")
        if _account_identity(status) != account_identity:
            raise ValueError("daily status paper-account identity changed")

    _validate_current_positions(latest, positions, metadata)
    expected_reasons = _report_reason_codes(
        statuses,
        positions,
        _state_changes(statuses, "regime"),
        _state_changes(statuses, "setup"),
    )
    if result.reason_codes != expected_reasons:
        raise ValueError("reason_codes do not match weekly strategy report")
    return statuses, positions


def _validate_current_positions(
    latest: DailySystemStatusResult,
    positions: tuple[PositionManagementReportResult, ...],
    metadata: Mapping[str, str],
) -> None:
    open_lifecycles = tuple(
        lifecycle
        for lifecycle in latest.paper_portfolio.lifecycles
        if lifecycle.is_open
    )
    expected = sorted(_canonical_record(item.as_record()) for item in open_lifecycles)
    actual = sorted(_canonical_record(item.lifecycle.as_record()) for item in positions)
    if actual != expected:
        raise ValueError(
            "position reports must exactly cover the latest open lifecycles",
        )

    for report in positions:
        report.as_record()
        if report.advisory != latest.advisory:
            raise ValueError("position report advisory must match latest daily status")
        if report.mark.marked_at != latest.as_of:
            raise ValueError("position report mark must match report window_end")
        if _config_metadata(report.config_metadata) != dict(metadata):
            raise ValueError("position report config identity does not match report")


def _ordered_daily_statuses(
    values: Sequence[DailySystemStatusResult],
) -> tuple[DailySystemStatusResult, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise TypeError("daily_statuses must be a sequence")
    if not values:
        raise ValueError("daily_statuses must contain at least one status")
    if any(not isinstance(item, DailySystemStatusResult) for item in values):
        raise TypeError("daily_statuses must contain DailySystemStatusResult values")
    ordered = tuple(sorted(values, key=lambda item: item.as_of))
    timestamps = [item.as_of for item in ordered]
    if len(timestamps) != len(set(timestamps)):
        raise ValueError("daily status timestamps must be unique")
    recommendation_ids = [
        item.advisory.recommendation.recommendation_id for item in ordered
    ]
    if len(recommendation_ids) != len(set(recommendation_ids)):
        raise ValueError("daily status recommendation IDs must be unique")
    for item in ordered:
        item.as_record()
    return ordered


def _ordered_position_reports(
    values: Sequence[PositionManagementReportResult],
) -> tuple[PositionManagementReportResult, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise TypeError("position_management_reports must be a sequence")
    if any(not isinstance(item, PositionManagementReportResult) for item in values):
        raise TypeError(
            "position_management_reports must contain "
            "PositionManagementReportResult values",
        )
    keyed = []
    for item in values:
        item.as_record()
        keyed.append((_canonical_record(item.lifecycle.as_record()), item))
    keyed.sort(key=lambda pair: pair[0])
    keys = [pair[0] for pair in keyed]
    if len(keys) != len(set(keys)):
        raise ValueError("position_management_reports must not contain duplicates")
    return tuple(pair[1] for pair in keyed)


def _state_changes(
    statuses: Sequence[DailySystemStatusResult],
    field: str,
) -> tuple[StrategyStateChange, ...]:
    changes = []
    for previous, current in pairwise(statuses):
        previous_recommendation = previous.advisory.recommendation
        current_recommendation = current.advisory.recommendation
        previous_value = getattr(previous_recommendation, field)
        current_value = getattr(current_recommendation, field)
        if previous_value != current_value:
            changes.append(
                StrategyStateChange(
                    changed_at=current.as_of,
                    previous_value=previous_value,
                    current_value=current_value,
                    previous_recommendation_id=(
                        previous_recommendation.recommendation_id
                    ),
                    current_recommendation_id=current_recommendation.recommendation_id,
                ),
            )
    return tuple(changes)


def _score_movements(
    statuses: Sequence[DailySystemStatusResult],
) -> tuple[ScoreMovement, ...]:
    first = statuses[0].advisory.recommendation
    current = statuses[-1].advisory.recommendation
    history_available = len(statuses) >= 2
    movements = []
    for field, _label in _SCORE_FIELDS:
        first_value = getattr(first, field) if history_available else None
        current_value = getattr(current, field)
        delta = (
            current_value - first_value
            if first_value is not None and current_value is not None
            else None
        )
        movements.append(
            ScoreMovement(
                score_name=field,
                first_value=first_value,
                current_value=current_value,
                delta=delta,
                first_recommendation_id=(
                    first.recommendation_id
                    if history_available and first_value is not None
                    else None
                ),
                current_recommendation_id=current.recommendation_id,
            ),
        )
    return tuple(movements)


def _report_reason_codes(
    statuses: Sequence[DailySystemStatusResult],
    positions: Sequence[PositionManagementReportResult],
    regime_changes: Sequence[StrategyStateChange],
    setup_changes: Sequence[StrategyStateChange],
) -> tuple[str, ...]:
    history_available = len(statuses) >= 2
    regime_code = (
        "WEEKLY_STRATEGY_REPORT_REGIME_CHANGED"
        if regime_changes
        else (
            "WEEKLY_STRATEGY_REPORT_REGIME_STABLE"
            if history_available
            else "WEEKLY_STRATEGY_REPORT_REGIME_HISTORY_INSUFFICIENT"
        )
    )
    setup_code = (
        "WEEKLY_STRATEGY_REPORT_SETUP_CHANGED"
        if setup_changes
        else (
            "WEEKLY_STRATEGY_REPORT_SETUP_STABLE"
            if history_available
            else "WEEKLY_STRATEGY_REPORT_SETUP_HISTORY_INSUFFICIENT"
        )
    )
    latest = statuses[-1].advisory.recommendation
    risk_available = bool(positions) or any(
        value is not None
        for value in (
            latest.risk_fraction_nav,
            latest.risk_amount,
            latest.suggested_notional,
        )
    )
    return (
        "WEEKLY_STRATEGY_REPORT_RENDERED",
        regime_code,
        setup_code,
        (
            "WEEKLY_STRATEGY_REPORT_PAPER_TRADES_OPEN"
            if positions
            else "WEEKLY_STRATEGY_REPORT_PAPER_TRADES_NONE"
        ),
        (
            "WEEKLY_STRATEGY_REPORT_RISK_AVAILABLE"
            if risk_available
            else "WEEKLY_STRATEGY_REPORT_RISK_UNAVAILABLE"
        ),
    )


def _render_body(
    *,
    window_start: datetime,
    window_end: datetime,
    statuses: Sequence[DailySystemStatusResult],
    positions: Sequence[PositionManagementReportResult],
    regime_changes: Sequence[StrategyStateChange],
    setup_changes: Sequence[StrategyStateChange],
    score_movements: Sequence[ScoreMovement],
    config_metadata: Mapping[str, str],
) -> str:
    metadata = _config_metadata(config_metadata)
    latest_status = statuses[-1]
    latest = latest_status.advisory.recommendation
    regime_lines = _change_lines(regime_changes)
    setup_lines = _change_lines(setup_changes)
    trade_lines = tuple(_trade_line(report) for report in positions) or ("- None",)
    trade_level_lines = tuple(_trade_level_line(report) for report in positions) or (
        "- None",
    )
    risk_lines = tuple(_position_risk_line(report) for report in positions) or (
        "- None",
    )
    score_by_name = {item.score_name: item for item in score_movements}
    score_lines = tuple(
        _score_line(label, score_by_name[field]) for field, label in _SCORE_FIELDS
    )
    lines = [
        "BTC WEEKLY STRATEGY REPORT",
        "",
        f"Window Start: {window_start.isoformat()}",
        f"Window End: {window_end.isoformat()}",
        f"First Observation: {statuses[0].as_of.isoformat()}",
        f"Observations: {len(statuses)}",
        f"Market: {latest.symbol} ({latest.timeframe})",
        (
            "Strategy: "
            f"{metadata['strategy_version']} / {metadata['parameter_set_id']}"
        ),
        "",
        "CURRENT STATE",
        f"Regime: {_display(latest.regime)}",
        f"Setup: {_display_optional(latest.setup)}",
        f"Recommendation: {latest.action}",
        f"Recommendation ID: {latest.recommendation_id}",
        f"Data Quality: {latest_status.data_quality.status}",
        f"Paper Portfolio: {latest_status.paper_portfolio.status}",
        "",
        "REGIME CHANGES",
        *regime_lines,
        "",
        "SETUP CHANGES",
        *setup_lines,
        "",
        "PRICE LEVELS",
        f"Entry Zone: {_entry_zone(latest.entry_zone_lower, latest.entry_zone_upper)}",
        f"Invalidation: {_format_optional_decimal(latest.invalidation_level)}",
        f"Initial Stop: {_format_optional_decimal(latest.initial_stop)}",
        "Current Trade Levels:",
        *trade_level_lines,
        "",
        "CURRENT PAPER TRADES",
        *trade_lines,
        "",
        "RISK",
        (
            "Recommendation Risk: "
            f"{_format_optional_percent(latest.risk_fraction_nav)}; "
            f"amount={_format_optional_decimal(latest.risk_amount)}; "
            f"suggested_notional={_format_optional_decimal(latest.suggested_notional)}"
        ),
        "Current Position Risk At Stop:",
        *risk_lines,
        "",
        "RECENT SCORE MOVEMENT",
        *score_lines,
    ]
    return "\n".join(lines) + "\n"


def _change_lines(changes: Sequence[StrategyStateChange]) -> tuple[str, ...]:
    if not changes:
        return ("- None observed",)
    return tuple(
        (
            f"- {change.changed_at.isoformat()}: "
            f"{_display_optional(change.previous_value)} -> "
            f"{_display_optional(change.current_value)} "
            f"[recommendation_id={change.current_recommendation_id}]"
        )
        for change in changes
    )


def _trade_level_line(report: PositionManagementReportResult) -> str:
    lifecycle = report.lifecycle
    return (
        f"- {lifecycle.symbol} {lifecycle.direction.upper()}: "
        f"mark={_format_decimal(report.mark.price)}; "
        f"active_stop={_format_optional_decimal(lifecycle.stop_price)}; "
        "candidate_stop="
        f"{_format_optional_decimal(report.trailing_stop.candidate_stop)}"
    )


def _trade_line(report: PositionManagementReportResult) -> str:
    lifecycle = report.lifecycle
    return (
        f"- {lifecycle.symbol} {lifecycle.direction.upper()} {lifecycle.state}; "
        f"tranches={lifecycle.tranche_count}; "
        f"quantity={_format_decimal(lifecycle.quantity, places=8)}; "
        f"average_entry={_format_optional_decimal(lifecycle.average_entry_price)}; "
        f"mark={_format_decimal(report.mark.price)}; "
        f"unrealized_pnl={_format_signed_decimal(report.metrics.unrealized_pnl)}"
    )


def _position_risk_line(report: PositionManagementReportResult) -> str:
    lifecycle = report.lifecycle
    risk = report.risk_at_stop
    status = "WITHIN LIMIT" if risk.within_maximum else "OVER LIMIT"
    return (
        f"- {lifecycle.symbol} {lifecycle.direction.upper()}: "
        f"risk_at_stop={_format_optional_decimal(risk.risk_at_stop)} "
        f"({_format_optional_percent(risk.risk_fraction_nav)}); "
        f"maximum={_format_percent(risk.maximum_fraction_nav)}; "
        f"status={status}; convention={risk.convention}; "
        f"reason_codes={_codes(risk.reason_codes)}"
    )


def _score_line(label: str, movement: ScoreMovement) -> str:
    return (
        f"- {label}: {_format_optional_score(movement.first_value)} -> "
        f"{_format_optional_score(movement.current_value)} "
        f"(delta {_format_optional_signed_score(movement.delta)})"
    )


def _account_identity(status: DailySystemStatusResult) -> tuple[Any, ...]:
    account = status.paper_portfolio.account.as_record()
    return (
        account["feature_id"],
        account["policy_version"],
        account["account_name"],
        account["base_currency"],
        account["starting_nav"],
        _canonical_record(account["costs"]),
        account["created_at"],
        _canonical_record(account["config_metadata"]),
    )


def _config_metadata(source: Mapping[str, Any] | Any) -> dict[str, str]:
    row = _mapping(source, "config_metadata")
    if set(row) != set(_CONFIG_KEYS):
        raise ValueError(f"config_metadata must exactly contain {_CONFIG_KEYS}")
    return {
        key: _identifier(row[key], f"config_metadata.{key}") for key in _CONFIG_KEYS
    }


def _canonical_record(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _mapping(source: Mapping[str, Any] | Any, name: str) -> Mapping[str, Any]:
    if isinstance(source, Mapping):
        return source
    row = getattr(source, "_mapping", None)
    if isinstance(row, Mapping):
        return row
    raise TypeError(f"{name} must be a mapping or database row")


def _sequence(value: Any, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{name} must be a sequence")
    return value


def _utc_datetime(value: Any, name: str) -> datetime:
    if isinstance(value, datetime):
        return require_utc_datetime(value, name)
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a datetime or ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a valid ISO-8601 datetime") from exc
    return require_utc_datetime(parsed, name)


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    if value != value.strip() or "\n" in value or "\r" in value:
        raise ValueError(f"{name} must be a single-line identifier")
    return value


def _optional_identifier(value: Any, name: str) -> str | None:
    return None if value is None else _identifier(value, name)


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _optional_positive_int(value: Any, name: str) -> int | None:
    return None if value is None else _positive_int(value, name)


def _optional_decimal(value: Any, name: str) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError(f"{name} must be numeric")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    return result


def _optional_string(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _text_block(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value


def _bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be a bool")
    return value


def _reason_codes(value: Any, name: str) -> tuple[str, ...]:
    values = _sequence(value, name)
    return tuple(_identifier(item, name) for item in values)


def _display(value: str) -> str:
    return value.replace("_", " ")


def _display_optional(value: str | None) -> str:
    return "N/A" if value is None else _display(value)


def _entry_zone(lower: Decimal | None, upper: Decimal | None) -> str:
    if lower is None or upper is None:
        return "N/A"
    return f"{_format_decimal(lower)}-{_format_decimal(upper)}"


def _format_decimal(value: Decimal, *, places: int = 2) -> str:
    quantum = Decimal(1).scaleb(-places)
    rendered = format(value.quantize(quantum, rounding=ROUND_HALF_UP), ",f")
    rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def _format_optional_decimal(value: Decimal | None) -> str:
    return "N/A" if value is None else _format_decimal(value)


def _format_signed_decimal(value: Decimal) -> str:
    prefix = "+" if value > 0 else ""
    return f"{prefix}{_format_decimal(value)}"


def _format_percent(value: Decimal) -> str:
    return f"{_format_decimal(value * 100)}% NAV"


def _format_optional_percent(value: Decimal | None) -> str:
    return "N/A" if value is None else _format_percent(value)


def _format_optional_score(value: Decimal | None) -> str:
    return "N/A" if value is None else _format_decimal(value, places=1)


def _format_optional_signed_score(value: Decimal | None) -> str:
    if value is None:
        return "N/A"
    prefix = "+" if value > 0 else ""
    return f"{prefix}{_format_decimal(value, places=1)}"


def _codes(values: Sequence[str]) -> str:
    return ",".join(values) if values else "NONE"


__all__ = [
    "WEEKLY_STRATEGY_REPORT_FEATURE_ID",
    "WEEKLY_STRATEGY_REPORT_LOOKBACK",
    "WEEKLY_STRATEGY_REPORT_MEDIA_TYPE",
    "WEEKLY_STRATEGY_REPORT_REASON_CODES",
    "WEEKLY_STRATEGY_REPORT_VERSION",
    "ScoreMovement",
    "StrategyStateChange",
    "WeeklyStrategyReportResult",
    "render_weekly_strategy_report",
    "weekly_strategy_report_from_record",
]
