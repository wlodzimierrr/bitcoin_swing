"""Deterministic, replayable alert generation (BTC-212).

Alerts are a notification boundary over existing decision owners.  Actions
come from BTC-170, data quality and current state come from BTC-210, stop moves
come from BTC-171/BTC-156, and hard flags come from their typed feature
results.  This module does not re-score a setup or choose a trading action.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Self

from btc_predictor.data import require_utc_datetime
from btc_predictor.features.volatility import (
    EUPHORIA_FLAG_FEATURE_ID,
    STRESS_FLAG_FEATURE_ID,
    EuphoriaFlagInput,
    EuphoriaFlagResult,
    StressFlagInput,
    StressFlagResult,
    calculate_euphoria_flag,
    calculate_stress_flag,
)
from btc_predictor.reporting.daily_status import (
    DATA_QUALITY_FAIL,
    DailySystemStatusResult,
    daily_system_status_from_record,
)
from btc_predictor.reporting.position_management import (
    PositionManagementReportResult,
    position_management_report_from_record,
)


ALERTS_FEATURE_ID = "ALERTS"
ALERTS_VERSION = "ALERTS_V1"
ALERTS_SCHEMA_VERSION = "ALERTS_JSON_V1"
ALERTS_MEDIA_TYPE = "application/json"

ACTIONABLE_SETUP = "ACTIONABLE_SETUP"
ENTRY_ZONE_REACHED = "ENTRY_ZONE_REACHED"
NEW_ADD_SIGNAL = "NEW_ADD_SIGNAL"
STOP_MOVE = "STOP_MOVE"
TRIM_SIGNAL = "TRIM_SIGNAL"
EXIT_SIGNAL = "EXIT_SIGNAL"
DATA_QUALITY_FAIL_ALERT = "DATA_QUALITY_FAIL"
STRESS = "STRESS"
EUPHORIA = "EUPHORIA"

ALERT_TYPES = (
    ACTIONABLE_SETUP,
    ENTRY_ZONE_REACHED,
    NEW_ADD_SIGNAL,
    STOP_MOVE,
    TRIM_SIGNAL,
    EXIT_SIGNAL,
    DATA_QUALITY_FAIL_ALERT,
    STRESS,
    EUPHORIA,
)

ALERTS_REASON_CODES = (
    "ALERTS_EMITTED",
    "ALERTS_NONE_EMITTED",
    "ALERTS_ENTRY_ZONE_EVALUATED",
    "ALERTS_ENTRY_ZONE_PRICE_MISSING",
    "ALERTS_ENTRY_ZONE_NOT_APPLICABLE",
    "ALERTS_STRESS_SOURCE_INCOMPLETE",
    "ALERTS_EUPHORIA_SOURCE_INCOMPLETE",
)

_CONFIG_KEYS = ("config_version", "strategy_version", "parameter_set_id")


@dataclass(frozen=True)
class AlertPriceObservation:
    """Exact point-in-time price used only for entry-zone membership."""

    price: Decimal
    observed_at: datetime
    source_id: str

    @classmethod
    def create(
        cls,
        *,
        price: Any,
        observed_at: datetime,
        source_id: str,
    ) -> Self:
        result = cls(
            price=_positive_decimal(price, "price_observation.price"),
            observed_at=_utc_datetime(
                observed_at,
                "price_observation.observed_at",
            ),
            source_id=_single_line(source_id, "price_observation.source_id"),
        )
        result.as_record()
        return result

    @classmethod
    def from_mapping(cls, source: Mapping[str, Any] | Any) -> Self:
        row = _mapping(source, "price observation")
        if set(row) != {"price", "observed_at", "source_id"}:
            raise ValueError("price observation fields are not canonical")
        return cls.create(
            price=row.get("price"),
            observed_at=_utc_datetime(row.get("observed_at"), "observed_at"),
            source_id=row.get("source_id"),
        )

    def as_record(self) -> dict[str, Any]:
        return {
            "price": str(_positive_decimal(self.price, "price_observation.price")),
            "observed_at": require_utc_datetime(
                self.observed_at,
                "price_observation.observed_at",
            ).isoformat(),
            "source_id": _single_line(
                self.source_id,
                "price_observation.source_id",
            ),
        }


@dataclass(frozen=True)
class AlertEvent:
    """One canonical alert ready for a notification consumer."""

    alert_type: str
    as_of: datetime
    symbol: str
    recommendation_id: int
    source_feature_id: str
    source_reason_codes: tuple[str, ...]
    message: str
    details: dict[str, Any]

    @classmethod
    def from_mapping(cls, source: Mapping[str, Any] | Any) -> Self:
        row = _mapping(source, "alert event")
        expected = {
            "alert_type",
            "as_of",
            "symbol",
            "recommendation_id",
            "source_feature_id",
            "source_reason_codes",
            "message",
            "details",
        }
        if set(row) != expected:
            raise ValueError("alert event fields are not canonical")
        details = _mapping(row.get("details"), "alert event details")
        return cls(
            alert_type=_member(row.get("alert_type"), ALERT_TYPES, "alert_type"),
            as_of=_utc_datetime(row.get("as_of"), "alert as_of"),
            symbol=_single_line(row.get("symbol"), "alert symbol"),
            recommendation_id=_positive_int(
                row.get("recommendation_id"),
                "recommendation_id",
            ),
            source_feature_id=_single_line(
                row.get("source_feature_id"),
                "source_feature_id",
            ),
            source_reason_codes=_reason_codes(
                row.get("source_reason_codes"),
                "source_reason_codes",
            ),
            message=_single_line(row.get("message"), "alert message"),
            details=_json_mapping(details, "alert event details"),
        )

    def as_record(self) -> dict[str, Any]:
        return {
            "alert_type": _member(self.alert_type, ALERT_TYPES, "alert_type"),
            "as_of": require_utc_datetime(self.as_of, "alert as_of").isoformat(),
            "symbol": _single_line(self.symbol, "alert symbol"),
            "recommendation_id": _positive_int(
                self.recommendation_id,
                "recommendation_id",
            ),
            "source_feature_id": _single_line(
                self.source_feature_id,
                "source_feature_id",
            ),
            "source_reason_codes": list(
                _reason_codes(self.source_reason_codes, "source_reason_codes"),
            ),
            "message": _single_line(self.message, "alert message"),
            "details": _json_mapping(self.details, "alert event details"),
        }


@dataclass(frozen=True)
class AlertsResult:
    """Canonical alert batch with all inputs needed for exact replay."""

    feature_id: str
    alerts_version: str
    schema_version: str
    media_type: str
    as_of: datetime
    daily_status: DailySystemStatusResult
    position_management_reports: tuple[PositionManagementReportResult, ...]
    price_observation: AlertPriceObservation | None
    stress: StressFlagResult
    euphoria: EuphoriaFlagResult
    alerts: tuple[AlertEvent, ...]
    config_metadata: dict[str, str]
    body: str
    complete: bool
    reason_codes: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        _validate_result(self)
        expected_alerts = _derive_alerts(
            daily_status=self.daily_status,
            position_reports=self.position_management_reports,
            price_observation=self.price_observation,
            stress=self.stress,
            euphoria=self.euphoria,
        )
        if self.alerts != expected_alerts:
            raise ValueError("alerts do not match source state")
        expected_body = _render_body(
            as_of=self.as_of,
            daily_status=self.daily_status,
            alerts=self.alerts,
        )
        if self.body != expected_body:
            raise ValueError("body does not match alerts")
        return {
            "feature_id": self.feature_id,
            "alerts_version": self.alerts_version,
            "schema_version": self.schema_version,
            "media_type": self.media_type,
            "as_of": self.as_of.isoformat(),
            "daily_status": self.daily_status.as_record(),
            "position_management_reports": [
                report.as_record() for report in self.position_management_reports
            ],
            "price_observation": (
                self.price_observation.as_record()
                if self.price_observation is not None
                else None
            ),
            "stress": self.stress.as_record(),
            "euphoria": self.euphoria.as_record(),
            "alerts": [alert.as_record() for alert in self.alerts],
            "config_metadata": _config_metadata(self.config_metadata),
            "body": self.body,
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def create_alerts(
    *,
    daily_status: DailySystemStatusResult,
    stress: StressFlagResult,
    euphoria: EuphoriaFlagResult,
    position_management_reports: Sequence[PositionManagementReportResult] = (),
    price_observation: AlertPriceObservation | None = None,
) -> AlertsResult:
    """Create all current alerts without making a second trading decision."""

    if not isinstance(daily_status, DailySystemStatusResult):
        raise TypeError("daily_status must be a DailySystemStatusResult")
    if not isinstance(stress, StressFlagResult):
        raise TypeError("stress must be a StressFlagResult")
    if not isinstance(euphoria, EuphoriaFlagResult):
        raise TypeError("euphoria must be an EuphoriaFlagResult")
    if price_observation is not None and not isinstance(
        price_observation,
        AlertPriceObservation,
    ):
        raise TypeError("price_observation must be AlertPriceObservation or None")

    reports = _ordered_position_reports(position_management_reports)
    metadata = _config_metadata(daily_status.config_metadata)
    as_of = daily_status.as_of
    alerts = _derive_alerts(
        daily_status=daily_status,
        position_reports=reports,
        price_observation=price_observation,
        stress=stress,
        euphoria=euphoria,
    )
    complete, reason_codes = _completion_and_reasons(
        daily_status=daily_status,
        price_observation=price_observation,
        stress=stress,
        euphoria=euphoria,
        alerts=alerts,
    )
    result = AlertsResult(
        feature_id=ALERTS_FEATURE_ID,
        alerts_version=ALERTS_VERSION,
        schema_version=ALERTS_SCHEMA_VERSION,
        media_type=ALERTS_MEDIA_TYPE,
        as_of=as_of,
        daily_status=daily_status,
        position_management_reports=reports,
        price_observation=price_observation,
        stress=stress,
        euphoria=euphoria,
        alerts=alerts,
        config_metadata=metadata,
        body=_render_body(as_of=as_of, daily_status=daily_status, alerts=alerts),
        complete=complete,
        reason_codes=reason_codes,
    )
    result.as_record()
    return result


def alerts_from_record(source: Mapping[str, Any] | Any) -> AlertsResult:
    """Restore a persisted alert batch and reject any source or output drift."""

    row = _mapping(source, "alerts record")
    report_values = row.get("position_management_reports")
    if isinstance(report_values, (str, bytes)) or not isinstance(
        report_values,
        Sequence,
    ):
        raise TypeError("position_management_reports must be a sequence")
    price_value = row.get("price_observation")
    result = AlertsResult(
        feature_id=row.get("feature_id"),
        alerts_version=row.get("alerts_version"),
        schema_version=row.get("schema_version"),
        media_type=row.get("media_type"),
        as_of=_utc_datetime(row.get("as_of"), "as_of"),
        daily_status=daily_system_status_from_record(
            _mapping(row.get("daily_status"), "daily_status"),
        ),
        position_management_reports=_ordered_position_reports(
            tuple(
                position_management_report_from_record(
                    _mapping(item, "position management report"),
                )
                for item in report_values
            ),
        ),
        price_observation=(
            None
            if price_value is None
            else AlertPriceObservation.from_mapping(price_value)
        ),
        stress=_stress_from_record(row.get("stress")),
        euphoria=_euphoria_from_record(row.get("euphoria")),
        alerts=tuple(
            AlertEvent.from_mapping(item)
            for item in _sequence(row.get("alerts"), "alerts")
        ),
        config_metadata=_config_metadata(row.get("config_metadata")),
        body=_text_block(row.get("body"), "body"),
        complete=_bool(row.get("complete"), "complete"),
        reason_codes=_reason_codes(row.get("reason_codes"), "reason_codes"),
    )
    record = result.as_record()
    if record != dict(row):
        raise ValueError("alerts record is not canonical")
    return result


def _validate_result(result: AlertsResult) -> None:
    if result.feature_id != ALERTS_FEATURE_ID:
        raise ValueError(f"feature_id must be {ALERTS_FEATURE_ID}")
    if result.alerts_version != ALERTS_VERSION:
        raise ValueError(f"alerts_version must be {ALERTS_VERSION}")
    if result.schema_version != ALERTS_SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {ALERTS_SCHEMA_VERSION}")
    if result.media_type != ALERTS_MEDIA_TYPE:
        raise ValueError(f"media_type must be {ALERTS_MEDIA_TYPE}")
    if not isinstance(result.daily_status, DailySystemStatusResult):
        raise TypeError("daily_status must be a DailySystemStatusResult")
    if not isinstance(result.stress, StressFlagResult):
        raise TypeError("stress must be a StressFlagResult")
    if not isinstance(result.euphoria, EuphoriaFlagResult):
        raise TypeError("euphoria must be an EuphoriaFlagResult")
    if result.price_observation is not None and not isinstance(
        result.price_observation,
        AlertPriceObservation,
    ):
        raise TypeError("price_observation has the wrong type")

    result.daily_status.as_record()
    metadata = _config_metadata(result.config_metadata)
    as_of = require_utc_datetime(result.as_of, "as_of")
    if as_of != result.daily_status.as_of:
        raise ValueError("as_of must match daily status")
    if result.daily_status.config_metadata != metadata:
        raise ValueError("daily status config identity does not match alerts")

    _validate_stress(result.stress)
    _validate_euphoria(result.euphoria)
    if _config_metadata(result.stress.config_metadata) != metadata:
        raise ValueError("stress config identity does not match alerts")
    if _config_metadata(result.euphoria.config_metadata) != metadata:
        raise ValueError("euphoria config identity does not match alerts")

    ordered_reports = _ordered_position_reports(result.position_management_reports)
    if result.position_management_reports != ordered_reports:
        raise ValueError("position management reports are not canonically ordered")
    _validate_position_coverage(result.daily_status, ordered_reports, metadata)

    if result.price_observation is not None:
        result.price_observation.as_record()
        if result.price_observation.observed_at != as_of:
            raise ValueError("price observation time must match alerts as_of")

    expected_complete, expected_reasons = _completion_and_reasons(
        daily_status=result.daily_status,
        price_observation=result.price_observation,
        stress=result.stress,
        euphoria=result.euphoria,
        alerts=result.alerts,
    )
    if result.complete != expected_complete:
        raise ValueError("complete does not match alert source availability")
    if result.reason_codes != expected_reasons:
        raise ValueError("reason_codes do not match alert state")
    unknown = tuple(
        code for code in result.reason_codes if code not in ALERTS_REASON_CODES
    )
    if unknown:
        raise ValueError(f"reason_codes are not owned by this module: {unknown}")


def _validate_position_coverage(
    daily_status: DailySystemStatusResult,
    reports: tuple[PositionManagementReportResult, ...],
    metadata: Mapping[str, str],
) -> None:
    open_lifecycles = tuple(
        lifecycle
        for lifecycle in daily_status.paper_portfolio.lifecycles
        if lifecycle.is_open
    )
    expected = sorted(_canonical_record(item.as_record()) for item in open_lifecycles)
    actual = sorted(_canonical_record(item.lifecycle.as_record()) for item in reports)
    if actual != expected:
        raise ValueError(
            "position reports must exactly cover current open lifecycles",
        )
    for report in reports:
        report.as_record()
        if report.advisory != daily_status.advisory:
            raise ValueError("position report advisory must match daily status")
        if report.mark.marked_at != daily_status.as_of:
            raise ValueError("position report mark must match alerts as_of")
        if _config_metadata(report.config_metadata) != dict(metadata):
            raise ValueError("position report config identity does not match alerts")


def _derive_alerts(
    *,
    daily_status: DailySystemStatusResult,
    position_reports: tuple[PositionManagementReportResult, ...],
    price_observation: AlertPriceObservation | None,
    stress: StressFlagResult,
    euphoria: EuphoriaFlagResult,
) -> tuple[AlertEvent, ...]:
    recommendation = daily_status.advisory.recommendation
    advisory_reasons = tuple(reason.code for reason in daily_status.advisory.reasons)
    common = {
        "as_of": daily_status.as_of,
        "symbol": recommendation.symbol,
        "recommendation_id": recommendation.recommendation_id,
    }
    alerts: list[AlertEvent] = []

    if recommendation.action == "ENTER":
        setup = recommendation.setup or "N/A"
        alerts.append(
            AlertEvent(
                alert_type=ACTIONABLE_SETUP,
                source_feature_id=daily_status.advisory.feature_id,
                source_reason_codes=advisory_reasons,
                message=f"ACTIONABLE SETUP: {setup} supports ENTER.",
                details={
                    "action": recommendation.action,
                    "entry_conviction": str(recommendation.entry_conviction),
                    "setup": recommendation.setup,
                },
                **common,
            ),
        )

    if _entry_zone_reached(recommendation, price_observation):
        assert price_observation is not None
        alerts.append(
            AlertEvent(
                alert_type=ENTRY_ZONE_REACHED,
                source_feature_id=daily_status.advisory.feature_id,
                source_reason_codes=advisory_reasons,
                message=(
                    "ENTRY ZONE REACHED: price "
                    f"{price_observation.price} is within "
                    f"{recommendation.entry_zone_lower}-"
                    f"{recommendation.entry_zone_upper}."
                ),
                details={
                    "entry_zone_lower": str(recommendation.entry_zone_lower),
                    "entry_zone_upper": str(recommendation.entry_zone_upper),
                    "observed_at": price_observation.observed_at.isoformat(),
                    "price": str(price_observation.price),
                    "price_source_id": price_observation.source_id,
                },
                **common,
            ),
        )

    if recommendation.action == "ADD":
        alerts.append(
            AlertEvent(
                alert_type=NEW_ADD_SIGNAL,
                source_feature_id=daily_status.advisory.feature_id,
                source_reason_codes=advisory_reasons,
                message="NEW ADD SIGNAL: the persisted recommendation is ADD.",
                details={
                    "action": recommendation.action,
                    "add_score": _optional_string(recommendation.add_score),
                },
                **common,
            ),
        )

    for report in position_reports:
        trailing = report.trailing_stop
        if trailing.advanced:
            alerts.append(
                AlertEvent(
                    alert_type=STOP_MOVE,
                    source_feature_id=trailing.feature_id,
                    source_reason_codes=tuple(trailing.reason_codes),
                    message=(
                        f"STOP MOVE: {trailing.previous_stop} -> "
                        f"{trailing.stop_price}."
                    ),
                    details={
                        "candidate_stop": _optional_string(
                            trailing.candidate_stop,
                        ),
                        "direction": trailing.direction,
                        "new_stop": str(trailing.stop_price),
                        "previous_stop": str(trailing.previous_stop),
                        "structure_id": trailing.structure_id,
                    },
                    **common,
                ),
            )

    if recommendation.action == "TRIM":
        alerts.append(
            AlertEvent(
                alert_type=TRIM_SIGNAL,
                source_feature_id=daily_status.advisory.feature_id,
                source_reason_codes=advisory_reasons,
                message="TRIM SIGNAL: the persisted recommendation is TRIM.",
                details={
                    "action": recommendation.action,
                    "hold_score": _optional_string(recommendation.hold_score),
                },
                **common,
            ),
        )

    if recommendation.action == "EXIT":
        alerts.append(
            AlertEvent(
                alert_type=EXIT_SIGNAL,
                source_feature_id=daily_status.advisory.feature_id,
                source_reason_codes=advisory_reasons,
                message="EXIT SIGNAL: the persisted recommendation is EXIT.",
                details={
                    "action": recommendation.action,
                    "hold_score": _optional_string(recommendation.hold_score),
                },
                **common,
            ),
        )

    if daily_status.data_quality.status == DATA_QUALITY_FAIL:
        alerts.append(
            AlertEvent(
                alert_type=DATA_QUALITY_FAIL_ALERT,
                source_feature_id=daily_status.feature_id,
                source_reason_codes=daily_status.data_quality.reason_codes,
                message="DATA QUALITY FAIL: one or more required components failed.",
                details={
                    "failed_components": [
                        component.source_component
                        for component in daily_status.data_quality.components
                        if component.status == DATA_QUALITY_FAIL
                    ],
                    "latest_data_source_id": (
                        daily_status.data_quality.latest_data_source_id
                    ),
                    "latest_data_timestamp": (
                        daily_status.data_quality.latest_data_timestamp.isoformat()
                    ),
                },
                **common,
            ),
        )

    if stress.flagged:
        alerts.append(
            AlertEvent(
                alert_type=STRESS,
                source_feature_id=stress.feature_id,
                source_reason_codes=tuple(stress.reason_codes),
                message="STRESS: the persisted hard stress flag is active.",
                details={
                    "block_new_trades": stress.block_new_trades,
                    "complete": stress.complete,
                    "effects": list(stress.effects),
                    "max_exposure_multiplier": str(
                        stress.max_exposure_multiplier,
                    ),
                },
                **common,
            ),
        )

    if euphoria.flagged:
        alerts.append(
            AlertEvent(
                alert_type=EUPHORIA,
                source_feature_id=euphoria.feature_id,
                source_reason_codes=tuple(euphoria.reason_codes),
                message="EUPHORIA: the persisted euphoria flag is active.",
                details={
                    "complete": euphoria.complete,
                    "effects": list(euphoria.effects),
                },
                **common,
            ),
        )

    return tuple(alerts)


def _entry_zone_reached(recommendation: Any, price: Any) -> bool:
    if price is None:
        return False
    lower = recommendation.entry_zone_lower
    upper = recommendation.entry_zone_upper
    return lower is not None and upper is not None and lower <= price.price <= upper


def _completion_and_reasons(
    *,
    daily_status: DailySystemStatusResult,
    price_observation: AlertPriceObservation | None,
    stress: StressFlagResult,
    euphoria: EuphoriaFlagResult,
    alerts: tuple[AlertEvent, ...],
) -> tuple[bool, tuple[str, ...]]:
    recommendation = daily_status.advisory.recommendation
    zone_applicable = (
        recommendation.entry_zone_lower is not None
        and recommendation.entry_zone_upper is not None
    )
    reasons = ["ALERTS_EMITTED" if alerts else "ALERTS_NONE_EMITTED"]
    if zone_applicable and price_observation is None:
        reasons.append("ALERTS_ENTRY_ZONE_PRICE_MISSING")
    elif zone_applicable:
        reasons.append("ALERTS_ENTRY_ZONE_EVALUATED")
    else:
        reasons.append("ALERTS_ENTRY_ZONE_NOT_APPLICABLE")
    if not stress.complete:
        reasons.append("ALERTS_STRESS_SOURCE_INCOMPLETE")
    if not euphoria.complete:
        reasons.append("ALERTS_EUPHORIA_SOURCE_INCOMPLETE")
    complete = (
        (not zone_applicable or price_observation is not None)
        and stress.complete
        and euphoria.complete
    )
    return complete, tuple(reasons)


def _render_body(
    *,
    as_of: datetime,
    daily_status: DailySystemStatusResult,
    alerts: tuple[AlertEvent, ...],
) -> str:
    recommendation = daily_status.advisory.recommendation
    payload = {
        "alerts": [alert.as_record() for alert in alerts],
        "as_of": as_of.isoformat(),
        "recommendation_id": recommendation.recommendation_id,
        "schema_version": ALERTS_SCHEMA_VERSION,
        "symbol": recommendation.symbol,
    }
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


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


def _validate_stress(source: StressFlagResult) -> None:
    restored = _stress_from_record(source.as_record())
    if restored != source:
        raise ValueError("stress result does not match its owned calculation")


def _validate_euphoria(source: EuphoriaFlagResult) -> None:
    restored = _euphoria_from_record(source.as_record())
    if restored != source:
        raise ValueError("euphoria result does not match its owned calculation")


def _stress_from_record(source: Mapping[str, Any] | Any) -> StressFlagResult:
    row = _mapping(source, "stress")
    inputs = _mapping(row.get("inputs"), "stress inputs")
    thresholds = _mapping(row.get("thresholds"), "stress thresholds")
    result = calculate_stress_flag(
        StressFlagInput(
            volatility_percentile=_optional_decimal(
                inputs.get("volatility_percentile"),
                "stress.volatility_percentile",
            ),
            liquidation_percentile=_optional_decimal(
                inputs.get("liquidation_percentile"),
                "stress.liquidation_percentile",
            ),
            downside_return=_optional_decimal(
                inputs.get("downside_return"),
                "stress.downside_return",
            ),
            funding_zscore=_optional_decimal(
                inputs.get("funding_zscore"),
                "stress.funding_zscore",
            ),
            basis_zscore=_optional_decimal(
                inputs.get("basis_zscore"),
                "stress.basis_zscore",
            ),
            systemic_shock=_optional_bool(
                inputs.get("systemic_shock"),
                "stress.systemic_shock",
            ),
        ),
        volatility_percentile_min=thresholds.get("volatility_percentile_min"),
        liquidation_percentile_min=thresholds.get(
            "liquidation_percentile_min",
        ),
        downside_return_min=thresholds.get("downside_return_min"),
        funding_abs_zscore_min=thresholds.get("funding_abs_zscore_min"),
        basis_abs_zscore_min=thresholds.get("basis_abs_zscore_min"),
        max_exposure_multiplier=row.get("max_exposure_multiplier"),
        block_new_trades=_bool(row.get("block_new_trades"), "block_new_trades"),
        config_metadata=_string_mapping(
            row.get("config_metadata"),
            "stress config_metadata",
        ),
    )
    if result.feature_id != STRESS_FLAG_FEATURE_ID or result.as_record() != dict(row):
        raise ValueError("stress record does not match its owned calculation")
    return result


def _euphoria_from_record(source: Mapping[str, Any] | Any) -> EuphoriaFlagResult:
    row = _mapping(source, "euphoria")
    inputs = _mapping(row.get("inputs"), "euphoria inputs")
    thresholds = _mapping(row.get("thresholds"), "euphoria thresholds")
    result = calculate_euphoria_flag(
        EuphoriaFlagInput(
            range_percentile=_optional_decimal(
                inputs.get("range_percentile"),
                "euphoria.range_percentile",
            ),
            upside_return=_optional_decimal(
                inputs.get("upside_return"),
                "euphoria.upside_return",
            ),
            funding_zscore=_optional_decimal(
                inputs.get("funding_zscore"),
                "euphoria.funding_zscore",
            ),
            basis_zscore=_optional_decimal(
                inputs.get("basis_zscore"),
                "euphoria.basis_zscore",
            ),
            oi_intensity_percentile=_optional_decimal(
                inputs.get("oi_intensity_percentile"),
                "euphoria.oi_intensity_percentile",
            ),
            volatility_percentile=_optional_decimal(
                inputs.get("volatility_percentile"),
                "euphoria.volatility_percentile",
            ),
            systemic_euphoria=_optional_bool(
                inputs.get("systemic_euphoria"),
                "euphoria.systemic_euphoria",
            ),
        ),
        range_percentile_min=thresholds.get("range_percentile_min"),
        upside_return_min=thresholds.get("upside_return_min"),
        funding_zscore_min=thresholds.get("funding_zscore_min"),
        basis_zscore_min=thresholds.get("basis_zscore_min"),
        oi_intensity_percentile_min=thresholds.get(
            "oi_intensity_percentile_min",
        ),
        volatility_percentile_min=thresholds.get("volatility_percentile_min"),
        config_metadata=_string_mapping(
            row.get("config_metadata"),
            "euphoria config_metadata",
        ),
    )
    if result.feature_id != EUPHORIA_FLAG_FEATURE_ID or result.as_record() != dict(row):
        raise ValueError("euphoria record does not match its owned calculation")
    return result


def _config_metadata(source: Mapping[str, Any] | Any) -> dict[str, str]:
    row = _mapping(source, "config_metadata")
    if set(row) != set(_CONFIG_KEYS):
        raise ValueError(f"config_metadata must contain exactly {_CONFIG_KEYS}")
    return {
        key: _single_line(row.get(key), f"config_metadata.{key}")
        for key in _CONFIG_KEYS
    }


def _string_mapping(source: Mapping[str, Any] | Any, name: str) -> dict[str, str]:
    row = _mapping(source, name)
    return {str(key): _single_line(value, f"{name}.{key}") for key, value in row.items()}


def _mapping(source: Mapping[str, Any] | Any, name: str) -> Mapping[str, Any]:
    if isinstance(source, Mapping):
        return source
    if hasattr(source, "_mapping"):
        return source._mapping
    raise TypeError(f"{name} must be a mapping")


def _sequence(source: Any, name: str) -> Sequence[Any]:
    if isinstance(source, (str, bytes)) or not isinstance(source, Sequence):
        raise TypeError(f"{name} must be a sequence")
    return source


def _utc_datetime(value: Any, name: str) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{name} must be an ISO-8601 datetime") from exc
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    return require_utc_datetime(value, name)


def _decimal(value: Any, name: str) -> Decimal:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be numeric")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    return result


def _positive_decimal(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if result <= 0:
        raise ValueError(f"{name} must be > 0")
    return result


def _optional_decimal(value: Any, name: str) -> Decimal | None:
    return None if value is None else _decimal(value, name)


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _single_line(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    if any(character in value for character in ("\n", "\r")):
        raise ValueError(f"{name} must be single-line")
    return value


def _text_block(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _member(value: Any, choices: tuple[str, ...], name: str) -> str:
    normalized = _single_line(value, name)
    if normalized not in choices:
        raise ValueError(f"{name} must be one of {choices}")
    return normalized


def _reason_codes(value: Any, name: str) -> tuple[str, ...]:
    sequence = _sequence(value, name)
    return tuple(_single_line(item, name) for item in sequence)


def _bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be a bool")
    return value


def _optional_bool(value: Any, name: str) -> bool | None:
    return None if value is None else _bool(value, name)


def _optional_string(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _json_mapping(source: Mapping[str, Any], name: str) -> dict[str, Any]:
    normalized = {str(key): _json_value(value, name) for key, value in source.items()}
    json.dumps(normalized, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return normalized


def _json_value(value: Any, name: str) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, list):
        return [_json_value(item, name) for item in value]
    if isinstance(value, Mapping):
        return _json_mapping(value, name)
    raise TypeError(f"{name} must contain only canonical JSON values")


def _canonical_record(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


__all__ = [
    "ACTIONABLE_SETUP",
    "ALERTS_FEATURE_ID",
    "ALERTS_MEDIA_TYPE",
    "ALERTS_REASON_CODES",
    "ALERTS_SCHEMA_VERSION",
    "ALERTS_VERSION",
    "ALERT_TYPES",
    "DATA_QUALITY_FAIL_ALERT",
    "ENTRY_ZONE_REACHED",
    "EUPHORIA",
    "EXIT_SIGNAL",
    "NEW_ADD_SIGNAL",
    "STOP_MOVE",
    "STRESS",
    "TRIM_SIGNAL",
    "AlertEvent",
    "AlertPriceObservation",
    "AlertsResult",
    "alerts_from_record",
    "create_alerts",
]
