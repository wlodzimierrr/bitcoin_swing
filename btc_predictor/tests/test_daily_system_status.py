from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.data import (
    DerivativesQualityIssue,
    DerivativesQualityReport,
    OhlcvQualityIssue,
    OhlcvQualityReport,
)
from btc_predictor.portfolio import (
    ENTER,
    PENDING_ENTRY,
    apply_position_event,
    open_paper_account,
    start_position_lifecycle,
)
from btc_predictor.reporting import (
    DAILY_SYSTEM_STATUS_FEATURE_ID,
    DAILY_SYSTEM_STATUS_MEDIA_TYPE,
    DAILY_SYSTEM_STATUS_VERSION,
    DATA_QUALITY_FAIL,
    PAPER_PORTFOLIO_ACTIVE_MONITORING,
    PAPER_PORTFOLIO_ACTIVE_OPEN,
    DailySystemStatusResult,
    daily_system_status_from_record,
    render_daily_system_status,
    render_recommendation,
)


CONFIG = load_strategy_config()
METADATA = CONFIG.run_metadata()
AS_OF = datetime(2026, 9, 2, tzinfo=UTC)
LATEST_DATA = AS_OF - timedelta(hours=1)


def _advisory(
    *,
    action: str = "WATCH",
    reasons: tuple[dict[str, object], ...] | None = None,
):
    selected_reasons = reasons or (
        {
            "recommendation_id": 210,
            "reason_rank": 0,
            "code": "ENTRY_CONVICTION_WATCH",
            "source_component": "entry",
            "severity": "info",
            "detail": "Entry conviction remains below the configured threshold.",
        },
    )
    return render_recommendation(
        {
            "recommendation_id": 210,
            "run_id": 71,
            "evaluation_time": AS_OF,
            "symbol": "BTC-USD",
            "timeframe": "1d",
            "regime": "BULL",
            "setup": "BULLISH_RESET",
            "direction": "long",
            "trend_score": Decimal("82"),
            "regime_score": Decimal("75"),
            "flow_score": Decimal("71"),
            "positioning_score": Decimal("69"),
            "volatility_score": Decimal("66"),
            "structure_score": Decimal("84"),
            "entry_conviction": Decimal("78"),
            "hold_score": Decimal("74") if action in {"HOLD", "ADD", "TRIM", "EXIT"} else None,
            "add_score": Decimal("72") if action in {"HOLD", "ADD", "TRIM", "EXIT"} else None,
            "entry_zone_lower": None,
            "entry_zone_upper": None,
            "invalidation_level": None,
            "initial_stop": None,
            "rr_ratio": None,
            "risk_fraction_nav": None,
            "risk_amount": None,
            "suggested_notional": None,
            "action": action,
        },
        selected_reasons,
        predictor_run={
            "run_id": 71,
            "evaluation_time": AS_OF,
            **METADATA,
        },
        strategy_config=CONFIG,
    )


def _account(*, created_at: datetime | None = None):
    return open_paper_account(
        account_name="phase-1-paper",
        created_at=created_at or AS_OF - timedelta(days=30),
        starting_nav="1000000",
        reserved_cash="25000",
        config=CONFIG,
    )


def _pending_lifecycle():
    return start_position_lifecycle(
        symbol="BTC-USD",
        state=PENDING_ENTRY,
        config_metadata=METADATA,
    )


def _open_lifecycle():
    return apply_position_event(
        _pending_lifecycle(),
        event=ENTER,
        event_time=AS_OF - timedelta(days=2),
        quantity="0.5",
        price="100000",
        stop_price="92000",
    )


def _clean_reports(*, reverse: bool = False):
    items = (
        ("ohlcv", OhlcvQualityReport(issues=())),
        ("derivatives", DerivativesQualityReport(issues=())),
    )
    if reverse:
        items = tuple(reversed(items))
    return dict(items)


def _render_clean(**changes):
    values = {
        "advisory": _advisory(),
        "quality_reports": _clean_reports(),
        "latest_data_timestamp": LATEST_DATA,
        "latest_data_source_id": "bitstamp:BTC/USD:1h:raw-noncanonical",
        "paper_account": _account(),
        "position_lifecycles": (_pending_lifecycle(),),
    }
    values.update(changes)
    return render_daily_system_status(**values)


def test_daily_status_shows_every_required_section_and_provenance() -> None:
    result = _render_clean()

    assert isinstance(result, DailySystemStatusResult)
    assert result.feature_id == DAILY_SYSTEM_STATUS_FEATURE_ID
    assert result.report_version == DAILY_SYSTEM_STATUS_VERSION
    assert result.media_type == DAILY_SYSTEM_STATUS_MEDIA_TYPE
    assert result.complete is True
    assert result.data_quality.latest_data_timestamp == LATEST_DATA
    assert result.data_quality.status == "PASS"
    assert result.advisory.recommendation.regime == "BULL"
    assert result.advisory.recommendation.setup == "BULLISH_RESET"
    assert result.advisory.recommendation.action == "WATCH"
    assert result.paper_portfolio.status == PAPER_PORTFOLIO_ACTIVE_MONITORING
    assert "Latest Data Timestamp: 2026-09-01T23:00:00+00:00" in result.body
    assert "Latest Data Source: bitstamp:BTC/USD:1h:raw-noncanonical" in result.body
    assert "Data Quality: PASS" in result.body
    assert "Regime: BULL" in result.body
    assert "Setup: BULLISH RESET" in result.body
    assert "Current Recommendation: WATCH" in result.body
    assert "Status: ACTIVE_MONITORING" in result.body
    assert "PENDING_ENTRY" in result.body


def test_daily_status_embeds_machine_readable_advisory_and_configuration() -> None:
    record = _render_clean().as_record()

    assert record["config_metadata"] == METADATA
    assert record["advisory_json"]["document_type"] == "recommendation"
    assert record["advisory_json"]["source_reason_codes"] == [
        "RECOMMENDATION_RENDERED",
    ]
    assert record["advisory"]["recommendation"]["recommendation_id"] == 210
    assert record["paper_portfolio"]["account"]["config_metadata"] == METADATA
    assert record["paper_portfolio"]["lifecycles"][0]["config_metadata"] == METADATA


def test_daily_status_is_deterministic_across_quality_input_order() -> None:
    first = _render_clean(quality_reports=_clean_reports(reverse=False))
    second = _render_clean(quality_reports=_clean_reports(reverse=True))

    assert first == second
    assert first.as_record() == second.as_record()
    assert [item.source_component for item in first.data_quality.components] == [
        "derivatives",
        "ohlcv",
    ]


def test_open_paper_portfolio_status_uses_lifecycle_owner_state() -> None:
    result = _render_clean(
        advisory=_advisory(action="HOLD"),
        position_lifecycles=(_open_lifecycle(),),
    )

    assert result.paper_portfolio.status == PAPER_PORTFOLIO_ACTIVE_OPEN
    assert result.paper_portfolio.open_position_count == 1
    assert result.paper_portfolio.monitored_position_count == 0
    assert "Open Positions: 1" in result.body
    assert "quantity=0.50; average_entry=100,000.00; stop=92,000.00" in result.body


def test_failed_quality_persists_source_codes_and_matches_gated_advisory() -> None:
    reasons = (
        {
            "recommendation_id": 210,
            "reason_rank": 0,
            "code": "DATA_QUALITY_FAIL",
            "source_component": "data_quality",
            "severity": "warning",
            "detail": "Critical data quality failure is present.",
        },
        {
            "recommendation_id": 210,
            "reason_rank": 1,
            "code": "STALE_FUNDING",
            "source_component": "derivatives",
            "severity": "warning",
            "detail": "The latest funding observation is stale.",
        },
    )
    reports = {
        "ohlcv": OhlcvQualityReport(issues=()),
        "derivatives": DerivativesQualityReport(
            issues=(
                DerivativesQualityIssue(
                    reason_code="STALE_FUNDING",
                    severity="error",
                    message="The latest funding observation is stale.",
                    timestamp=LATEST_DATA,
                ),
            ),
        ),
    }

    result = _render_clean(
        advisory=_advisory(action="HOLD", reasons=reasons),
        quality_reports=reports,
        position_lifecycles=(_open_lifecycle(),),
    )

    assert result.data_quality.status == DATA_QUALITY_FAIL
    assert result.data_quality.reason_codes == ("STALE_FUNDING",)
    assert result.reason_codes == (
        "DAILY_SYSTEM_STATUS_RENDERED",
        "DAILY_SYSTEM_STATUS_DATA_QUALITY_FAIL",
        "DAILY_SYSTEM_STATUS_PORTFOLIO_ACTIVE_OPEN",
    )
    assert "derivatives (DERIVATIVES): FAIL [STALE_FUNDING]" in result.body


def test_quality_status_must_match_advisory_reason_codes_and_action() -> None:
    failed = {
        "ohlcv": OhlcvQualityReport(
            issues=(
                OhlcvQualityIssue(
                    reason_code="STALE_DATA",
                    severity="error",
                    message="Latest OHLCV data is stale.",
                ),
            ),
        ),
    }

    with pytest.raises(ValueError, match="does not match advisory"):
        _render_clean(quality_reports=failed)


def test_existing_position_recommendation_requires_open_lifecycle() -> None:
    with pytest.raises(ValueError, match="requires an open lifecycle"):
        _render_clean(
            advisory=_advisory(action="HOLD"),
            position_lifecycles=(),
        )


def test_report_replays_exactly_and_rejects_tampering() -> None:
    result = _render_clean()
    record = result.as_record()
    restored = daily_system_status_from_record(record)

    assert restored == result
    assert restored.as_record() == record

    changed_quality = deepcopy(record)
    changed_quality["data_quality"]["status"] = "FAIL"
    with pytest.raises(ValueError, match="does not match components"):
        daily_system_status_from_record(changed_quality)

    changed_body = deepcopy(record)
    changed_body["body"] = str(changed_body["body"]).replace("WATCH", "ENTER")
    with pytest.raises(ValueError, match="body does not match"):
        daily_system_status_from_record(changed_body)


def test_report_rejects_future_data_and_future_portfolio_state() -> None:
    with pytest.raises(ValueError, match="latest_data_timestamp must be <= as_of"):
        _render_clean(latest_data_timestamp=AS_OF + timedelta(seconds=1))

    with pytest.raises(ValueError, match="created after as_of"):
        _render_clean(paper_account=_account(created_at=AS_OF + timedelta(seconds=1)))

    future_lifecycle = apply_position_event(
        _pending_lifecycle(),
        event=ENTER,
        event_time=AS_OF + timedelta(seconds=1),
        quantity="0.5",
        price="100000",
        stop_price="92000",
    )
    with pytest.raises(ValueError, match="event cannot be after as_of"):
        _render_clean(
            advisory=_advisory(action="HOLD"),
            position_lifecycles=(future_lifecycle,),
        )


def test_report_rejects_config_symbol_and_direction_mismatches() -> None:
    bad_metadata = {**METADATA, "parameter_set_id": "other"}
    bad_config_lifecycle = start_position_lifecycle(
        symbol="BTC-USD",
        state=PENDING_ENTRY,
        config_metadata=bad_metadata,
    )
    with pytest.raises(ValueError, match="lifecycle config identity"):
        _render_clean(position_lifecycles=(bad_config_lifecycle,))

    wrong_symbol = start_position_lifecycle(
        symbol="ETH-USD",
        state=PENDING_ENTRY,
        config_metadata=METADATA,
    )
    with pytest.raises(ValueError, match="lifecycle symbol"):
        _render_clean(position_lifecycles=(wrong_symbol,))


def test_report_rejects_missing_quality_evidence_and_duplicate_lifecycles() -> None:
    with pytest.raises(ValueError, match="at least one report"):
        _render_clean(quality_reports={})

    lifecycle = _pending_lifecycle()
    with pytest.raises(ValueError, match="must not contain duplicates"):
        _render_clean(position_lifecycles=(lifecycle, lifecycle))


def test_report_rejects_forged_paper_account_owner_identity() -> None:
    with pytest.raises(ValueError, match="account.feature_id"):
        _render_clean(paper_account=replace(_account(), feature_id="OTHER"))


def test_report_rejects_non_utc_and_injection_prone_provenance() -> None:
    with pytest.raises(ValueError, match="UTC"):
        _render_clean(latest_data_timestamp=datetime(2026, 9, 2))

    with pytest.raises(ValueError, match="single-line"):
        _render_clean(latest_data_source_id="source\nData Quality: PASS")
