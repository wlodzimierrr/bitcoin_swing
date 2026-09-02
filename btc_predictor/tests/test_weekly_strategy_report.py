from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.data import DerivativesQualityReport, OhlcvQualityReport
from btc_predictor.portfolio import (
    ENTER,
    PENDING_ENTRY,
    apply_position_event,
    open_paper_account,
    start_position_lifecycle,
)
from btc_predictor.reporting import (
    WEEKLY_STRATEGY_REPORT_FEATURE_ID,
    WEEKLY_STRATEGY_REPORT_MEDIA_TYPE,
    WEEKLY_STRATEGY_REPORT_VERSION,
    WeeklyStrategyReportResult,
    render_daily_system_status,
    render_position_management_report,
    render_recommendation,
    render_weekly_strategy_report,
    weekly_strategy_report_from_record,
)
from btc_predictor.risk import (
    HIGHER_LOW,
    calculate_risk_at_stop,
    calculate_trailing_stop,
)

CONFIG = load_strategy_config()
METADATA = CONFIG.run_metadata()
AS_OF = datetime(2026, 9, 2, tzinfo=UTC)
FIRST_AT = AS_OF - timedelta(days=6)
MIDDLE_AT = AS_OF - timedelta(days=3)


def _account(*, created_at: datetime | None = None):
    return open_paper_account(
        account_name="phase-1-paper",
        created_at=created_at or AS_OF - timedelta(days=90),
        starting_nav="1000000",
        reserved_cash="25000",
        config=CONFIG,
    )


def _open_lifecycle():
    pending = start_position_lifecycle(
        symbol="BTC-USD",
        state=PENDING_ENTRY,
        config_metadata=METADATA,
    )
    return apply_position_event(
        pending,
        event=ENTER,
        event_time=AS_OF - timedelta(days=2),
        quantity="0.5",
        price="100000",
        stop_price="92000",
    )


def _advisory(
    *,
    at: datetime,
    recommendation_id: int,
    regime: str,
    setup: str | None,
    trend: str,
    flow: str,
    action: str = "WATCH",
):
    current_position = action in {"HOLD", "ADD", "TRIM", "EXIT"}
    recommendation = {
        "recommendation_id": recommendation_id,
        "run_id": recommendation_id + 1000,
        "evaluation_time": at,
        "symbol": "BTC-USD",
        "timeframe": "1d",
        "regime": regime,
        "setup": setup,
        "direction": "long",
        "trend_score": Decimal(trend),
        "regime_score": Decimal("66") if regime == "BULL" else Decimal("50"),
        "flow_score": Decimal(flow),
        "positioning_score": Decimal("70"),
        "volatility_score": Decimal("64"),
        "structure_score": Decimal("82"),
        "entry_conviction": Decimal("86") if action == "ADD" else Decimal("72"),
        "hold_score": Decimal("78") if current_position else None,
        "add_score": Decimal("87") if current_position else None,
        "entry_zone_lower": Decimal("98500") if action == "ADD" else None,
        "entry_zone_upper": Decimal("101000") if action == "ADD" else None,
        "invalidation_level": Decimal("93000") if action == "ADD" else None,
        "initial_stop": Decimal("91500") if action == "ADD" else None,
        "rr_ratio": Decimal("2.8") if action == "ADD" else None,
        "risk_fraction_nav": Decimal("0.005") if action == "ADD" else None,
        "risk_amount": Decimal("5000") if action == "ADD" else None,
        "suggested_notional": Decimal("100000") if action == "ADD" else None,
        "action": action,
    }
    return render_recommendation(
        recommendation,
        (
            {
                "recommendation_id": recommendation_id,
                "reason_rank": 0,
                "code": "STRATEGY_STATE_RECORDED",
                "source_component": "strategy",
                "severity": "info",
                "detail": "The persisted strategy state supports this action.",
            },
        ),
        predictor_run={
            "run_id": recommendation_id + 1000,
            "evaluation_time": at,
            **METADATA,
        },
        strategy_config=CONFIG,
    )


def _daily(
    *,
    at: datetime,
    recommendation_id: int,
    regime: str,
    setup: str | None,
    trend: str,
    flow: str,
    action: str = "WATCH",
    lifecycles=(),
    account=None,
):
    return render_daily_system_status(
        advisory=_advisory(
            at=at,
            recommendation_id=recommendation_id,
            regime=regime,
            setup=setup,
            trend=trend,
            flow=flow,
            action=action,
        ),
        quality_reports={
            "ohlcv": OhlcvQualityReport(issues=()),
            "derivatives": DerivativesQualityReport(issues=()),
        },
        latest_data_timestamp=at - timedelta(hours=1),
        latest_data_source_id="bitstamp:BTC/USD:1h:raw-noncanonical",
        paper_account=account or _account(),
        position_lifecycles=lifecycles,
    )


def _history(*, current_open: bool = True):
    lifecycle = _open_lifecycle()
    latest = _daily(
        at=AS_OF,
        recommendation_id=2113,
        regime="BULL",
        setup="BULLISH_RESET",
        trend="78",
        flow="74",
        action="ADD" if current_open else "WATCH",
        lifecycles=(lifecycle,) if current_open else (),
    )
    return (
        _daily(
            at=FIRST_AT,
            recommendation_id=2111,
            regime="NEUTRAL",
            setup=None,
            trend="60",
            flow="55",
        ),
        _daily(
            at=MIDDLE_AT,
            recommendation_id=2112,
            regime="BULL",
            setup="BULLISH_RESET",
            trend="71",
            flow="63",
        ),
        latest,
    )


def _position_report(latest):
    lifecycle = latest.paper_portfolio.lifecycles[0]
    trailing = calculate_trailing_stop(
        direction="long",
        previous_stop=lifecycle.stop_price,
        structure_price="98000",
        buffer="1500",
        current_price="104000",
        evaluated_at=AS_OF,
        config_metadata=METADATA,
        structure_id="btc211-higher-low",
        structure_source_feature_id="ENTRY_TRIGGER_HIGHER_LOW",
        structure_type=HIGHER_LOW,
        structure_level_timestamp=AS_OF - timedelta(days=2),
        structure_detected_at=AS_OF - timedelta(hours=2),
        structure_reason_codes=("STRUCTURE_CONFIRMED",),
    )
    risk = calculate_risk_at_stop(
        lifecycle.tranches,
        stop_price=lifecycle.stop_price,
        nav="1000000",
        direction="long",
        config=CONFIG,
    )
    return render_position_management_report(
        advisory=latest.advisory,
        lifecycle=lifecycle,
        trailing_stop=trailing,
        risk_at_stop=risk,
        mark_price="104000",
        marked_at=AS_OF,
        mark_source_id="bitstamp:BTC/USD:1h:raw-noncanonical",
    )


def _report():
    history = _history()
    return render_weekly_strategy_report(
        daily_statuses=history,
        position_management_reports=(_position_report(history[-1]),),
    )


def test_weekly_report_shows_every_required_section_from_owned_sources() -> None:
    result = _report()

    assert isinstance(result, WeeklyStrategyReportResult)
    assert result.feature_id == WEEKLY_STRATEGY_REPORT_FEATURE_ID
    assert result.report_version == WEEKLY_STRATEGY_REPORT_VERSION
    assert result.media_type == WEEKLY_STRATEGY_REPORT_MEDIA_TYPE
    assert result.window_start == AS_OF - timedelta(days=7)
    assert result.window_end == AS_OF
    assert result.complete is True
    assert "NEUTRAL -> BULL" in result.body
    assert "N/A -> BULLISH RESET" in result.body
    assert "Entry Zone: 98,500-101,000" in result.body
    assert "Invalidation: 93,000" in result.body
    assert "active_stop=92,000; candidate_stop=96,500" in result.body
    assert "BTC-USD LONG OPEN_INITIAL" in result.body
    assert "risk_at_stop=4,000 (0.4% NAV)" in result.body
    assert "Trend: 60 -> 78 (delta +18)" in result.body
    assert "Flow: 55 -> 74 (delta +19)" in result.body


def test_report_persists_complete_provenance_configuration_and_reason_codes() -> None:
    record = _report().as_record()

    assert record["config_metadata"] == METADATA
    assert len(record["daily_statuses"]) == 3
    assert record["daily_statuses"][-1]["advisory_json"]["document_type"] == (
        "recommendation"
    )
    assert record["daily_statuses"][-1]["advisory"]["recommendation"][
        "recommendation_id"
    ] == 2113
    assert record["position_reports"][0]["risk_at_stop"]["policy_version"] == (
        "RISK_AT_STOP_V1"
    )
    assert record["position_reports"][0]["mark"]["source_id"].endswith(
        "raw-noncanonical",
    )
    assert record["reason_codes"] == [
        "WEEKLY_STRATEGY_REPORT_RENDERED",
        "WEEKLY_STRATEGY_REPORT_REGIME_CHANGED",
        "WEEKLY_STRATEGY_REPORT_SETUP_CHANGED",
        "WEEKLY_STRATEGY_REPORT_PAPER_TRADES_OPEN",
        "WEEKLY_STRATEGY_REPORT_RISK_AVAILABLE",
    ]


def test_input_order_is_canonical_and_output_is_deterministic() -> None:
    history = _history()
    position = _position_report(history[-1])

    first = render_weekly_strategy_report(
        daily_statuses=history,
        position_management_reports=(position,),
    )
    second = render_weekly_strategy_report(
        daily_statuses=tuple(reversed(history)),
        position_management_reports=(position,),
    )

    assert first == second
    assert first.as_record() == second.as_record()
    assert [item.as_of for item in second.daily_statuses] == [
        FIRST_AT,
        MIDDLE_AT,
        AS_OF,
    ]


def test_report_replays_exactly_and_rejects_summary_body_and_source_tampering() -> None:
    result = _report()
    record = result.as_record()

    restored = weekly_strategy_report_from_record(record)
    assert restored == result
    assert restored.as_record() == record

    changed_summary = deepcopy(record)
    changed_summary["score_movements"][0]["delta"] = "999"
    with pytest.raises(ValueError, match="score delta"):
        weekly_strategy_report_from_record(changed_summary)

    changed_body = deepcopy(record)
    changed_body["body"] = str(changed_body["body"]).replace("ADD", "EXIT")
    with pytest.raises(ValueError, match="body does not match"):
        weekly_strategy_report_from_record(changed_body)

    changed_source = deepcopy(record)
    changed_source["daily_statuses"][-1]["advisory"]["body"] = "forged"
    with pytest.raises(ValueError, match="body does not match"):
        weekly_strategy_report_from_record(changed_source)


def test_all_state_transitions_are_retained_in_chronological_order() -> None:
    history = (
        _daily(
            at=FIRST_AT,
            recommendation_id=2121,
            regime="NEUTRAL",
            setup=None,
            trend="60",
            flow="55",
        ),
        _daily(
            at=MIDDLE_AT,
            recommendation_id=2122,
            regime="BULL",
            setup="BULLISH_RESET",
            trend="70",
            flow="65",
        ),
        _daily(
            at=AS_OF,
            recommendation_id=2123,
            regime="NEUTRAL",
            setup=None,
            trend="62",
            flow="57",
        ),
    )

    result = render_weekly_strategy_report(daily_statuses=history)

    assert [item.current_value for item in result.regime_changes] == [
        "BULL",
        "NEUTRAL",
    ]
    assert [item.current_recommendation_id for item in result.setup_changes] == [
        2122,
        2123,
    ]


def test_one_observation_does_not_claim_stability_or_zero_fill_scores() -> None:
    only = _history(current_open=False)[-1]
    result = render_weekly_strategy_report(daily_statuses=(only,))

    assert result.reason_codes == (
        "WEEKLY_STRATEGY_REPORT_RENDERED",
        "WEEKLY_STRATEGY_REPORT_REGIME_HISTORY_INSUFFICIENT",
        "WEEKLY_STRATEGY_REPORT_SETUP_HISTORY_INSUFFICIENT",
        "WEEKLY_STRATEGY_REPORT_PAPER_TRADES_NONE",
        "WEEKLY_STRATEGY_REPORT_RISK_UNAVAILABLE",
    )
    hold = next(
        item for item in result.score_movements if item.score_name == "hold_score"
    )
    trend = next(
        item for item in result.score_movements if item.score_name == "trend_score"
    )
    assert hold.first_value is None
    assert hold.current_value is None
    assert hold.delta is None
    assert trend.first_value is None
    assert trend.first_recommendation_id is None
    assert trend.current_value == Decimal("78")
    assert trend.delta is None
    assert "Trend: N/A -> 78 (delta N/A)" in result.body
    assert "Hold: N/A -> N/A (delta N/A)" in result.body
    assert "Recommendation Risk: N/A; amount=N/A; suggested_notional=N/A" in (
        result.body
    )


def test_current_open_lifecycles_require_exact_current_management_reports() -> None:
    history = _history()
    with pytest.raises(ValueError, match="exactly cover"):
        render_weekly_strategy_report(daily_statuses=history)

    flat_history = _history(current_open=False)
    with pytest.raises(ValueError, match="exactly cover"):
        render_weekly_strategy_report(
            daily_statuses=flat_history,
            position_management_reports=(_position_report(history[-1]),),
        )


def test_position_report_must_use_latest_advisory_and_point_in_time_mark() -> None:
    history = _history()
    current = _position_report(history[-1])
    other_current_advisory = _advisory(
        at=AS_OF,
        recommendation_id=9999,
        regime="BULL",
        setup="BULLISH_RESET",
        trend="78",
        flow="74",
        action="ADD",
    )
    forged = replace(current, advisory=other_current_advisory)

    with pytest.raises(ValueError, match="advisory must match latest"):
        render_weekly_strategy_report(
            daily_statuses=history,
            position_management_reports=(forged,),
        )


def test_history_must_fit_window_and_keep_market_and_account_identity() -> None:
    history = _history(current_open=False)
    too_old = _daily(
        at=AS_OF - timedelta(days=8),
        recommendation_id=2130,
        regime="NEUTRAL",
        setup=None,
        trend="50",
        flow="50",
    )
    with pytest.raises(ValueError, match="seven-day window"):
        render_weekly_strategy_report(daily_statuses=(too_old, *history))

    changed_account = _daily(
        at=MIDDLE_AT,
        recommendation_id=2131,
        regime="BULL",
        setup="BULLISH_RESET",
        trend="70",
        flow="65",
        account=_account(created_at=AS_OF - timedelta(days=100)),
    )
    with pytest.raises(ValueError, match="paper-account identity changed"):
        render_weekly_strategy_report(
            daily_statuses=(history[0], changed_account, history[-1]),
        )


def test_duplicate_observations_and_noncanonical_records_fail_closed() -> None:
    history = _history(current_open=False)
    with pytest.raises(ValueError, match="timestamps must be unique"):
        render_weekly_strategy_report(daily_statuses=(history[0], history[0]))

    record = render_weekly_strategy_report(daily_statuses=history).as_record()
    record["unexpected"] = True
    with pytest.raises(ValueError, match="not canonical"):
        weekly_strategy_report_from_record(record)
