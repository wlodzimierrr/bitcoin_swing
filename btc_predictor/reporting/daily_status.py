"""Deterministic daily system status reporting (BTC-210).

The report is a presentation boundary over existing owners.  Regime, setup,
and action come from the validated BTC-170 advisory; its BTC-172 canonical JSON
is embedded unchanged.  Data quality comes from the existing OHLCV and
derivatives quality reports, and paper status comes from the BTC-160 account
and BTC-150 lifecycle snapshots.  No signal, quality, or portfolio decision is
made here.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, TypeAlias

from btc_predictor.data import (
    DerivativesQualityReport,
    OhlcvQualityReport,
    require_utc_datetime,
)
from btc_predictor.portfolio import (
    ACCOUNT_ACTIVE,
    ACCOUNT_ARCHIVED,
    EXECUTION_COST_POLICY_VERSION,
    PAPER_ACCOUNT_FEATURE_ID,
    PAPER_ACCOUNT_POLICY_VERSION,
    PRE_POSITION_STATES,
    ExecutionCosts,
    PaperAccount,
    PositionLifecycle,
    restore_position_lifecycle,
)
from btc_predictor.reporting.json_output import (
    AdvisoryJsonResult,
    advisory_json_from_record,
    render_json_output,
)
from btc_predictor.reporting.recommendation import (
    RecommendationRendererResult,
    recommendation_renderer_from_record,
)
from btc_predictor.signals.data_quality import (
    DATA_QUALITY_BLOCKED_ACTIONS,
    DATA_QUALITY_FAIL_REASON_CODE,
    QualityReport,
)


DAILY_SYSTEM_STATUS_FEATURE_ID = "DAILY_SYSTEM_STATUS_REPORT"
DAILY_SYSTEM_STATUS_VERSION = "DAILY_SYSTEM_STATUS_REPORT_V1"
DAILY_SYSTEM_STATUS_MEDIA_TYPE = "text/plain"

DATA_QUALITY_PASS = "PASS"
DATA_QUALITY_FAIL = "FAIL"
DATA_QUALITY_STATUSES = (DATA_QUALITY_PASS, DATA_QUALITY_FAIL)

PAPER_PORTFOLIO_ACTIVE_FLAT = "ACTIVE_FLAT"
PAPER_PORTFOLIO_ACTIVE_MONITORING = "ACTIVE_MONITORING"
PAPER_PORTFOLIO_ACTIVE_OPEN = "ACTIVE_OPEN"
PAPER_PORTFOLIO_ARCHIVED = "ARCHIVED"
PAPER_PORTFOLIO_STATUSES = (
    PAPER_PORTFOLIO_ACTIVE_FLAT,
    PAPER_PORTFOLIO_ACTIVE_MONITORING,
    PAPER_PORTFOLIO_ACTIVE_OPEN,
    PAPER_PORTFOLIO_ARCHIVED,
)

DAILY_SYSTEM_STATUS_REASON_CODES = (
    "DAILY_SYSTEM_STATUS_RENDERED",
    "DAILY_SYSTEM_STATUS_DATA_QUALITY_PASS",
    "DAILY_SYSTEM_STATUS_DATA_QUALITY_FAIL",
    "DAILY_SYSTEM_STATUS_PORTFOLIO_ACTIVE_FLAT",
    "DAILY_SYSTEM_STATUS_PORTFOLIO_ACTIVE_MONITORING",
    "DAILY_SYSTEM_STATUS_PORTFOLIO_ACTIVE_OPEN",
    "DAILY_SYSTEM_STATUS_PORTFOLIO_ARCHIVED",
)

_CONFIG_KEYS = ("config_version", "strategy_version", "parameter_set_id")
_QUALITY_REPORT_TYPES = {
    OhlcvQualityReport: "OHLCV",
    DerivativesQualityReport: "DERIVATIVES",
}
_PORTFOLIO_REASON_BY_STATUS = {
    PAPER_PORTFOLIO_ACTIVE_FLAT: "DAILY_SYSTEM_STATUS_PORTFOLIO_ACTIVE_FLAT",
    PAPER_PORTFOLIO_ACTIVE_MONITORING: (
        "DAILY_SYSTEM_STATUS_PORTFOLIO_ACTIVE_MONITORING"
    ),
    PAPER_PORTFOLIO_ACTIVE_OPEN: "DAILY_SYSTEM_STATUS_PORTFOLIO_ACTIVE_OPEN",
    PAPER_PORTFOLIO_ARCHIVED: "DAILY_SYSTEM_STATUS_PORTFOLIO_ARCHIVED",
}

QualityReportInput: TypeAlias = OhlcvQualityReport | DerivativesQualityReport


@dataclass(frozen=True)
class DataQualityComponentStatus:
    """Persistable status of one validated data component."""

    source_component: str
    report_type: str
    status: str
    reason_codes: tuple[str, ...]

    @classmethod
    def from_report(
        cls,
        source_component: str,
        report: QualityReportInput,
    ) -> DataQualityComponentStatus:
        if type(report) not in _QUALITY_REPORT_TYPES:
            raise TypeError(
                "quality reports must be OhlcvQualityReport or "
                "DerivativesQualityReport",
            )
        reasons = _reason_codes(report.reason_codes, "quality reason_codes")
        status = DATA_QUALITY_PASS if report.is_valid else DATA_QUALITY_FAIL
        if status == DATA_QUALITY_FAIL and not reasons:
            raise ValueError("a failed quality report must carry reason codes")
        if status == DATA_QUALITY_PASS and reasons:
            raise ValueError("a passing quality report must not carry reason codes")
        return cls(
            source_component=_single_line(
                source_component,
                "source_component",
            ),
            report_type=_QUALITY_REPORT_TYPES[type(report)],
            status=status,
            reason_codes=reasons,
        )

    @classmethod
    def from_mapping(
        cls,
        source: Mapping[str, Any] | Any,
    ) -> DataQualityComponentStatus:
        row = _mapping(source, "data quality component")
        result = cls(
            source_component=_single_line(
                row.get("source_component"),
                "source_component",
            ),
            report_type=_member(
                row.get("report_type"),
                tuple(_QUALITY_REPORT_TYPES.values()),
                "report_type",
            ),
            status=_member(row.get("status"), DATA_QUALITY_STATUSES, "status"),
            reason_codes=_reason_codes(
                row.get("reason_codes"),
                "reason_codes",
            ),
        )
        result.as_record()
        return result

    def as_record(self) -> dict[str, Any]:
        status = _member(self.status, DATA_QUALITY_STATUSES, "status")
        reasons = _reason_codes(self.reason_codes, "reason_codes")
        if (status == DATA_QUALITY_PASS) != (not reasons):
            raise ValueError("quality status does not match reason codes")
        return {
            "source_component": _single_line(
                self.source_component,
                "source_component",
            ),
            "report_type": _member(
                self.report_type,
                tuple(_QUALITY_REPORT_TYPES.values()),
                "report_type",
            ),
            "status": status,
            "reason_codes": list(reasons),
        }


@dataclass(frozen=True)
class DataQualityStatus:
    """Decision-time data provenance and ordered quality summary."""

    latest_data_timestamp: datetime
    latest_data_source_id: str
    status: str
    components: tuple[DataQualityComponentStatus, ...]
    reason_codes: tuple[str, ...]

    @classmethod
    def from_mapping(
        cls,
        source: Mapping[str, Any] | Any,
    ) -> DataQualityStatus:
        row = _mapping(source, "data quality status")
        components_value = row.get("components")
        if isinstance(components_value, (str, bytes)) or not isinstance(
            components_value,
            Sequence,
        ):
            raise TypeError("components must be a sequence")
        result = cls(
            latest_data_timestamp=_utc_datetime(
                row.get("latest_data_timestamp"),
                "latest_data_timestamp",
            ),
            latest_data_source_id=_single_line(
                row.get("latest_data_source_id"),
                "latest_data_source_id",
            ),
            status=_member(row.get("status"), DATA_QUALITY_STATUSES, "status"),
            components=tuple(
                DataQualityComponentStatus.from_mapping(item)
                for item in components_value
            ),
            reason_codes=_reason_codes(
                row.get("reason_codes"),
                "reason_codes",
            ),
        )
        result.as_record()
        return result

    def as_record(self) -> dict[str, Any]:
        components = _ordered_components(self.components)
        expected_status, expected_reasons = _quality_summary(components)
        if self.status != expected_status:
            raise ValueError("data quality status does not match components")
        if self.reason_codes != expected_reasons:
            raise ValueError("data quality reason_codes do not match components")
        return {
            "latest_data_timestamp": require_utc_datetime(
                self.latest_data_timestamp,
                "latest_data_timestamp",
            ).isoformat(),
            "latest_data_source_id": _single_line(
                self.latest_data_source_id,
                "latest_data_source_id",
            ),
            "status": self.status,
            "components": [component.as_record() for component in components],
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class PaperPortfolioStatus:
    """Current paper-account state and replayable lifecycle snapshots."""

    account: PaperAccount
    lifecycles: tuple[PositionLifecycle, ...]
    status: str
    open_position_count: int
    monitored_position_count: int
    reason_codes: tuple[str, ...]

    @classmethod
    def from_mapping(
        cls,
        source: Mapping[str, Any] | Any,
    ) -> PaperPortfolioStatus:
        row = _mapping(source, "paper portfolio status")
        lifecycle_values = row.get("lifecycles")
        if isinstance(lifecycle_values, (str, bytes)) or not isinstance(
            lifecycle_values,
            Sequence,
        ):
            raise TypeError("lifecycles must be a sequence")
        result = cls(
            account=_paper_account_from_record(
                _mapping(row.get("account"), "account"),
            ),
            lifecycles=tuple(
                restore_position_lifecycle(_mapping(item, "lifecycle"))
                for item in lifecycle_values
            ),
            status=_member(
                row.get("status"),
                PAPER_PORTFOLIO_STATUSES,
                "portfolio status",
            ),
            open_position_count=_non_negative_int(
                row.get("open_position_count"),
                "open_position_count",
            ),
            monitored_position_count=_non_negative_int(
                row.get("monitored_position_count"),
                "monitored_position_count",
            ),
            reason_codes=_reason_codes(
                row.get("reason_codes"),
                "portfolio reason_codes",
            ),
        )
        result.as_record()
        return result

    def as_record(self) -> dict[str, Any]:
        self.account.as_record()
        lifecycles = _ordered_lifecycles(self.lifecycles)
        status, open_count, monitored_count, reasons = _portfolio_summary(
            self.account,
            lifecycles,
        )
        if self.status != status:
            raise ValueError("portfolio status does not match account/lifecycles")
        if self.open_position_count != open_count:
            raise ValueError("open_position_count does not match lifecycles")
        if self.monitored_position_count != monitored_count:
            raise ValueError("monitored_position_count does not match lifecycles")
        if self.reason_codes != reasons:
            raise ValueError("portfolio reason_codes do not match status")
        return {
            "account": self.account.as_record(),
            "lifecycles": [lifecycle.as_record() for lifecycle in lifecycles],
            "status": self.status,
            "open_position_count": self.open_position_count,
            "monitored_position_count": self.monitored_position_count,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class DailySystemStatusResult:
    """Replayable plain-text daily status with machine-readable sources."""

    feature_id: str
    report_version: str
    media_type: str
    as_of: datetime
    data_quality: DataQualityStatus
    advisory: RecommendationRendererResult
    advisory_json: AdvisoryJsonResult
    paper_portfolio: PaperPortfolioStatus
    config_metadata: dict[str, str]
    body: str
    complete: bool
    reason_codes: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        _validate_report(self)
        expected_body = _render_body(
            as_of=self.as_of,
            data_quality=self.data_quality,
            advisory=self.advisory,
            paper_portfolio=self.paper_portfolio,
            config_metadata=self.config_metadata,
        )
        if self.body != expected_body:
            raise ValueError("body does not match daily system status inputs")
        return {
            "feature_id": self.feature_id,
            "report_version": self.report_version,
            "media_type": self.media_type,
            "as_of": self.as_of.isoformat(),
            "data_quality": self.data_quality.as_record(),
            "advisory": self.advisory.as_record(),
            "advisory_json": self.advisory_json.as_record(),
            "paper_portfolio": self.paper_portfolio.as_record(),
            "config_metadata": _config_metadata(self.config_metadata),
            "body": self.body,
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def render_daily_system_status(
    *,
    advisory: RecommendationRendererResult,
    quality_reports: Mapping[str, QualityReport],
    latest_data_timestamp: datetime,
    latest_data_source_id: str,
    paper_account: PaperAccount,
    position_lifecycles: Sequence[PositionLifecycle] = (),
) -> DailySystemStatusResult:
    """Render one daily status as of the advisory's evaluation timestamp."""

    if not isinstance(advisory, RecommendationRendererResult):
        raise TypeError("advisory must be a RecommendationRendererResult")
    if not isinstance(paper_account, PaperAccount):
        raise TypeError("paper_account must be a PaperAccount")
    if not isinstance(quality_reports, Mapping) or not quality_reports:
        raise ValueError("quality_reports must contain at least one report")
    if isinstance(position_lifecycles, (str, bytes)) or not isinstance(
        position_lifecycles,
        Sequence,
    ):
        raise TypeError("position_lifecycles must be a sequence")

    components = _ordered_components(
        tuple(
            DataQualityComponentStatus.from_report(name, report)
            for name, report in quality_reports.items()
        ),
    )
    quality_status, quality_reasons = _quality_summary(components)
    data_quality = DataQualityStatus(
        latest_data_timestamp=_utc_datetime(
            latest_data_timestamp,
            "latest_data_timestamp",
        ),
        latest_data_source_id=_single_line(
            latest_data_source_id,
            "latest_data_source_id",
        ),
        status=quality_status,
        components=components,
        reason_codes=quality_reasons,
    )
    lifecycles = _ordered_lifecycles(tuple(position_lifecycles))
    portfolio_status, open_count, monitored_count, portfolio_reasons = (
        _portfolio_summary(paper_account, lifecycles)
    )
    paper_portfolio = PaperPortfolioStatus(
        account=paper_account,
        lifecycles=lifecycles,
        status=portfolio_status,
        open_position_count=open_count,
        monitored_position_count=monitored_count,
        reason_codes=portfolio_reasons,
    )
    metadata = _config_metadata(advisory.config_metadata)
    as_of = advisory.recommendation.evaluation_time
    result = DailySystemStatusResult(
        feature_id=DAILY_SYSTEM_STATUS_FEATURE_ID,
        report_version=DAILY_SYSTEM_STATUS_VERSION,
        media_type=DAILY_SYSTEM_STATUS_MEDIA_TYPE,
        as_of=as_of,
        data_quality=data_quality,
        advisory=advisory,
        advisory_json=render_json_output(advisory),
        paper_portfolio=paper_portfolio,
        config_metadata=metadata,
        body="",
        complete=True,
        reason_codes=_report_reason_codes(data_quality, paper_portfolio),
    )
    _validate_report(result)
    result = replace(
        result,
        body=_render_body(
            as_of=as_of,
            data_quality=data_quality,
            advisory=advisory,
            paper_portfolio=paper_portfolio,
            config_metadata=metadata,
        ),
    )
    result.as_record()
    return result


def daily_system_status_from_record(
    source: Mapping[str, Any] | Any,
) -> DailySystemStatusResult:
    """Restore a persisted daily report and reject source or body drift."""

    row = _mapping(source, "daily system status record")
    result = DailySystemStatusResult(
        feature_id=row.get("feature_id"),
        report_version=row.get("report_version"),
        media_type=row.get("media_type"),
        as_of=_utc_datetime(row.get("as_of"), "as_of"),
        data_quality=DataQualityStatus.from_mapping(row.get("data_quality")),
        advisory=recommendation_renderer_from_record(
            _mapping(row.get("advisory"), "advisory"),
        ),
        advisory_json=advisory_json_from_record(
            _mapping(row.get("advisory_json"), "advisory_json"),
        ),
        paper_portfolio=PaperPortfolioStatus.from_mapping(
            row.get("paper_portfolio"),
        ),
        config_metadata=_config_metadata(row.get("config_metadata")),
        body=_text_block(row.get("body"), "body"),
        complete=_bool(row.get("complete"), "complete"),
        reason_codes=_reason_codes(row.get("reason_codes"), "reason_codes"),
    )
    record = result.as_record()
    if record != dict(row):
        raise ValueError("daily system status record is not canonical")
    return result


def _validate_report(result: DailySystemStatusResult) -> None:
    if result.feature_id != DAILY_SYSTEM_STATUS_FEATURE_ID:
        raise ValueError(f"feature_id must be {DAILY_SYSTEM_STATUS_FEATURE_ID}")
    if result.report_version != DAILY_SYSTEM_STATUS_VERSION:
        raise ValueError(f"report_version must be {DAILY_SYSTEM_STATUS_VERSION}")
    if result.media_type != DAILY_SYSTEM_STATUS_MEDIA_TYPE:
        raise ValueError(f"media_type must be {DAILY_SYSTEM_STATUS_MEDIA_TYPE}")
    if result.complete is not True:
        raise ValueError("a validated daily system status must be complete")
    if not isinstance(result.data_quality, DataQualityStatus):
        raise TypeError("data_quality must be a DataQualityStatus")
    if not isinstance(result.advisory, RecommendationRendererResult):
        raise TypeError("advisory must be a RecommendationRendererResult")
    if not isinstance(result.advisory_json, AdvisoryJsonResult):
        raise TypeError("advisory_json must be an AdvisoryJsonResult")
    if not isinstance(result.paper_portfolio, PaperPortfolioStatus):
        raise TypeError("paper_portfolio must be a PaperPortfolioStatus")

    as_of = require_utc_datetime(result.as_of, "as_of")
    result.data_quality.as_record()
    result.advisory.as_record()
    result.advisory_json.as_record()
    result.paper_portfolio.as_record()
    metadata = _config_metadata(result.config_metadata)
    if as_of != result.advisory.recommendation.evaluation_time:
        raise ValueError("as_of must match recommendation evaluation_time")
    if result.data_quality.latest_data_timestamp > as_of:
        raise ValueError("latest_data_timestamp must be <= as_of")
    if result.advisory.config_metadata != metadata:
        raise ValueError("advisory config identity does not match report")
    if result.advisory_json.document_type != "recommendation":
        raise ValueError("advisory_json must contain a recommendation document")
    if result.advisory_json.source != result.advisory:
        raise ValueError("advisory_json source does not match advisory")

    account = result.paper_portfolio.account
    if _config_metadata(account.config_metadata) != metadata:
        raise ValueError("paper account config identity does not match report")
    if account.created_at > as_of:
        raise ValueError("paper account cannot be created after as_of")

    recommendation = result.advisory.recommendation
    for lifecycle in result.paper_portfolio.lifecycles:
        if _config_metadata(lifecycle.config_metadata) != metadata:
            raise ValueError("lifecycle config identity does not match report")
        if lifecycle.last_event_at is not None and lifecycle.last_event_at > as_of:
            raise ValueError("lifecycle event cannot be after as_of")
        if lifecycle.symbol != recommendation.symbol:
            raise ValueError("lifecycle symbol does not match recommendation")
        if lifecycle.is_open and lifecycle.direction != recommendation.direction:
            raise ValueError("open lifecycle direction does not match recommendation")

    advisory_codes = {reason.code for reason in result.advisory.reasons}
    quality_failed = result.data_quality.status == DATA_QUALITY_FAIL
    advisory_failed = DATA_QUALITY_FAIL_REASON_CODE in advisory_codes
    if quality_failed != advisory_failed:
        raise ValueError("data quality status does not match advisory reason codes")
    if quality_failed:
        missing_codes = set(result.data_quality.reason_codes) - advisory_codes
        if missing_codes:
            raise ValueError(
                "advisory is missing data quality reason codes: "
                f"{sorted(missing_codes)}",
            )
        if recommendation.action in DATA_QUALITY_BLOCKED_ACTIONS:
            raise ValueError("failed data quality cannot retain ENTER or ADD action")

    if recommendation.action in ("HOLD", "ADD", "TRIM", "EXIT"):
        if result.paper_portfolio.open_position_count < 1:
            raise ValueError("existing-position action requires an open lifecycle")

    expected_reasons = _report_reason_codes(
        result.data_quality,
        result.paper_portfolio,
    )
    if result.reason_codes != expected_reasons:
        raise ValueError("reason_codes do not match daily system status")


def _render_body(
    *,
    as_of: datetime,
    data_quality: DataQualityStatus,
    advisory: RecommendationRendererResult,
    paper_portfolio: PaperPortfolioStatus,
    config_metadata: Mapping[str, str],
) -> str:
    recommendation = advisory.recommendation
    metadata = _config_metadata(config_metadata)
    component_lines = [
        (
            f"- {component.source_component} ({component.report_type}): "
            f"{component.status} [{_codes_label(component.reason_codes)}]"
        )
        for component in data_quality.components
    ]
    lifecycle_lines = [
        _lifecycle_line(lifecycle)
        for lifecycle in paper_portfolio.lifecycles
    ] or ["- None"]
    account = paper_portfolio.account
    lines = [
        "BTC DAILY SYSTEM STATUS",
        "",
        f"As Of: {as_of.isoformat()}",
        (
            "Strategy: "
            f"{metadata['strategy_version']} / {metadata['parameter_set_id']}"
        ),
        "",
        "DATA",
        f"Latest Data Timestamp: {data_quality.latest_data_timestamp.isoformat()}",
        f"Latest Data Source: {data_quality.latest_data_source_id}",
        f"Data Quality: {data_quality.status}",
        *component_lines,
        "",
        "MARKET STATE",
        f"Regime: {_display_identifier(recommendation.regime)}",
        f"Setup: {_display_optional_identifier(recommendation.setup)}",
        f"Current Recommendation: {recommendation.action}",
        f"Recommendation ID: {recommendation.recommendation_id}",
        "",
        "PAPER PORTFOLIO",
        f"Status: {paper_portfolio.status}",
        f"Account: {account.account_name} ({account.status.upper()})",
        f"Cash: {_format_decimal(account.cash)} {account.base_currency}",
        (
            "Available Cash: "
            f"{_format_decimal(account.available_cash)} {account.base_currency}"
        ),
        f"Open Positions: {paper_portfolio.open_position_count}",
        f"Monitored Entries: {paper_portfolio.monitored_position_count}",
        "Lifecycle Snapshots:",
        *lifecycle_lines,
    ]
    return "\n".join(lines) + "\n"


def _lifecycle_line(lifecycle: PositionLifecycle) -> str:
    return (
        f"- {lifecycle.symbol} {lifecycle.direction.upper()} {lifecycle.state}; "
        f"quantity={_format_decimal(lifecycle.quantity)}; "
        f"average_entry={_format_optional_decimal(lifecycle.average_entry_price)}; "
        f"stop={_format_optional_decimal(lifecycle.stop_price)}"
    )


def _ordered_components(
    components: Sequence[DataQualityComponentStatus],
) -> tuple[DataQualityComponentStatus, ...]:
    if not components:
        raise ValueError("data quality components must not be empty")
    if any(not isinstance(item, DataQualityComponentStatus) for item in components):
        raise TypeError("components must contain DataQualityComponentStatus values")
    ordered = tuple(sorted(components, key=lambda item: item.source_component))
    names = [item.source_component for item in ordered]
    if len(names) != len(set(names)):
        raise ValueError("data quality source_component values must be unique")
    for item in ordered:
        item.as_record()
    return ordered


def _quality_summary(
    components: Sequence[DataQualityComponentStatus],
) -> tuple[str, tuple[str, ...]]:
    ordered = _ordered_components(components)
    failed = tuple(item for item in ordered if item.status == DATA_QUALITY_FAIL)
    reasons = _stable_unique(
        code for component in failed for code in component.reason_codes
    )
    return (DATA_QUALITY_FAIL if failed else DATA_QUALITY_PASS), reasons


def _ordered_lifecycles(
    lifecycles: Sequence[PositionLifecycle],
) -> tuple[PositionLifecycle, ...]:
    if any(not isinstance(item, PositionLifecycle) for item in lifecycles):
        raise TypeError("position_lifecycles must contain PositionLifecycle values")
    records = []
    for lifecycle in lifecycles:
        record = lifecycle.as_record()
        encoded = json.dumps(record, sort_keys=True, separators=(",", ":"))
        records.append((encoded, lifecycle))
    records.sort(key=lambda item: item[0])
    encodings = [item[0] for item in records]
    if len(encodings) != len(set(encodings)):
        raise ValueError("position_lifecycles must not contain duplicates")
    return tuple(item[1] for item in records)


def _portfolio_summary(
    account: PaperAccount,
    lifecycles: Sequence[PositionLifecycle],
) -> tuple[str, int, int, tuple[str, ...]]:
    if not isinstance(account, PaperAccount):
        raise TypeError("account must be a PaperAccount")
    _validate_account_identity(account)
    ordered = _ordered_lifecycles(lifecycles)
    open_count = sum(item.is_open for item in ordered)
    monitored_count = sum(item.state in PRE_POSITION_STATES for item in ordered)
    if account.status == ACCOUNT_ARCHIVED:
        status = PAPER_PORTFOLIO_ARCHIVED
    elif open_count:
        status = PAPER_PORTFOLIO_ACTIVE_OPEN
    elif monitored_count:
        status = PAPER_PORTFOLIO_ACTIVE_MONITORING
    else:
        status = PAPER_PORTFOLIO_ACTIVE_FLAT
    return status, open_count, monitored_count, (_PORTFOLIO_REASON_BY_STATUS[status],)


def _validate_account_identity(account: PaperAccount) -> None:
    record = account.as_record()
    if record["feature_id"] != PAPER_ACCOUNT_FEATURE_ID:
        raise ValueError(f"account.feature_id must be {PAPER_ACCOUNT_FEATURE_ID}")
    if record["policy_version"] != PAPER_ACCOUNT_POLICY_VERSION:
        raise ValueError(
            f"account.policy_version must be {PAPER_ACCOUNT_POLICY_VERSION}",
        )
    if record["costs"]["policy_version"] != EXECUTION_COST_POLICY_VERSION:
        raise ValueError(
            "account execution cost policy must be "
            f"{EXECUTION_COST_POLICY_VERSION}",
        )


def _report_reason_codes(
    data_quality: DataQualityStatus,
    portfolio: PaperPortfolioStatus,
) -> tuple[str, ...]:
    quality_reason = (
        "DAILY_SYSTEM_STATUS_DATA_QUALITY_PASS"
        if data_quality.status == DATA_QUALITY_PASS
        else "DAILY_SYSTEM_STATUS_DATA_QUALITY_FAIL"
    )
    return (
        "DAILY_SYSTEM_STATUS_RENDERED",
        quality_reason,
        _PORTFOLIO_REASON_BY_STATUS[portfolio.status],
    )


def _paper_account_from_record(source: Mapping[str, Any]) -> PaperAccount:
    costs_row = _mapping(source.get("costs"), "account.costs")
    costs = ExecutionCosts(
        policy_version=_single_line(
            costs_row.get("policy_version"),
            "costs.policy_version",
        ),
        fee_bps=_non_negative_decimal(costs_row.get("fee_bps"), "fee_bps"),
        slippage_bps=_non_negative_decimal(
            costs_row.get("slippage_bps"),
            "slippage_bps",
        ),
        funding_cost_bps_per_day=_non_negative_decimal(
            costs_row.get("funding_cost_bps_per_day"),
            "funding_cost_bps_per_day",
        ),
    )
    if costs.policy_version != EXECUTION_COST_POLICY_VERSION:
        raise ValueError(
            f"costs.policy_version must be {EXECUTION_COST_POLICY_VERSION}",
        )
    account = PaperAccount(
        feature_id=source.get("feature_id"),
        policy_version=source.get("policy_version"),
        account_name=_single_line(source.get("account_name"), "account_name"),
        base_currency=_single_line(source.get("base_currency"), "base_currency"),
        starting_nav=_non_negative_decimal(
            source.get("starting_nav"),
            "starting_nav",
        ),
        cash=_non_negative_decimal(source.get("cash"), "cash"),
        reserved_cash=_non_negative_decimal(
            source.get("reserved_cash"),
            "reserved_cash",
        ),
        realized_pnl=_decimal(source.get("realized_pnl"), "realized_pnl"),
        fees_paid=_non_negative_decimal(source.get("fees_paid"), "fees_paid"),
        funding_paid=_decimal(source.get("funding_paid"), "funding_paid"),
        costs=costs,
        status=_member(
            source.get("status"),
            (ACCOUNT_ACTIVE, ACCOUNT_ARCHIVED),
            "account.status",
        ),
        created_at=_utc_datetime(source.get("created_at"), "created_at"),
        config_metadata=_config_metadata(source.get("config_metadata")),
        reason_codes=_reason_codes(
            source.get("reason_codes"),
            "account.reason_codes",
        ),
    )
    if account.feature_id != PAPER_ACCOUNT_FEATURE_ID:
        raise ValueError(f"account.feature_id must be {PAPER_ACCOUNT_FEATURE_ID}")
    if account.policy_version != PAPER_ACCOUNT_POLICY_VERSION:
        raise ValueError(
            f"account.policy_version must be {PAPER_ACCOUNT_POLICY_VERSION}",
        )
    record = account.as_record()
    if record != dict(source):
        raise ValueError("paper account record does not match restored account")
    return account


def _config_metadata(source: Mapping[str, Any] | Any) -> dict[str, str]:
    row = _mapping(source, "config_metadata")
    if set(row) != set(_CONFIG_KEYS):
        raise ValueError(f"config_metadata must exactly contain {_CONFIG_KEYS}")
    return {
        key: _single_line(row.get(key), f"config_metadata.{key}")
        for key in _CONFIG_KEYS
    }


def _mapping(source: Mapping[str, Any] | Any, name: str) -> Mapping[str, Any]:
    if isinstance(source, Mapping):
        return source
    row = getattr(source, "_mapping", None)
    if isinstance(row, Mapping):
        return row
    raise TypeError(f"{name} must be a mapping or database row")


def _utc_datetime(value: Any, name: str) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{name} must be an ISO-8601 datetime") from exc
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    return require_utc_datetime(value, name)


def _single_line(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    if "\n" in value or "\r" in value:
        raise ValueError(f"{name} must be single-line text")
    return value.strip()


def _text_block(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be non-empty text")
    return value


def _member(value: Any, choices: tuple[str, ...], name: str) -> str:
    if value not in choices:
        raise ValueError(f"{name} must be one of {choices}")
    return value


def _reason_codes(value: Any, name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{name} must be a sequence")
    reasons = tuple(_single_line(item, name) for item in value)
    if len(reasons) != len(set(reasons)):
        raise ValueError(f"{name} must not contain duplicates")
    return reasons


def _stable_unique(values: Any) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)


def _non_negative_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _decimal(value: Any, name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    return result


def _non_negative_decimal(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


def _format_decimal(value: Decimal) -> str:
    rounded = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{rounded:,.2f}"


def _format_optional_decimal(value: Decimal | None) -> str:
    return "N/A" if value is None else _format_decimal(value)


def _codes_label(reason_codes: tuple[str, ...]) -> str:
    return ", ".join(reason_codes) if reason_codes else "NONE"


def _display_identifier(value: str) -> str:
    return value.replace("_", " ")


def _display_optional_identifier(value: str | None) -> str:
    return "N/A" if value is None else _display_identifier(value)


def _bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be a bool")
    return value


__all__ = [
    "DAILY_SYSTEM_STATUS_FEATURE_ID",
    "DAILY_SYSTEM_STATUS_MEDIA_TYPE",
    "DAILY_SYSTEM_STATUS_REASON_CODES",
    "DAILY_SYSTEM_STATUS_VERSION",
    "DATA_QUALITY_FAIL",
    "DATA_QUALITY_PASS",
    "DATA_QUALITY_STATUSES",
    "PAPER_PORTFOLIO_ACTIVE_FLAT",
    "PAPER_PORTFOLIO_ACTIVE_MONITORING",
    "PAPER_PORTFOLIO_ACTIVE_OPEN",
    "PAPER_PORTFOLIO_ARCHIVED",
    "PAPER_PORTFOLIO_STATUSES",
    "DailySystemStatusResult",
    "DataQualityComponentStatus",
    "DataQualityStatus",
    "PaperPortfolioStatus",
    "daily_system_status_from_record",
    "render_daily_system_status",
]
