from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.portfolio import (
    ENTER,
    EXIT,
    PENDING_ENTRY,
    apply_position_event,
    start_position_lifecycle,
)
from btc_predictor.reporting import (
    POSITION_MANAGEMENT_REPORT_FEATURE_ID,
    POSITION_MANAGEMENT_REPORT_MEDIA_TYPE,
    POSITION_MANAGEMENT_REPORT_VERSION,
    PositionManagementReportResult,
    position_management_report_from_record,
    render_position_management_report,
    render_recommendation,
)
from btc_predictor.risk import (
    HIGHER_LOW,
    LOWER_HIGH,
    calculate_risk_at_stop,
    calculate_trailing_stop,
    risk_at_stop_from_record,
)


CONFIG = load_strategy_config()
METADATA = CONFIG.run_metadata()
EVALUATED_AT = datetime(2026, 8, 31, tzinfo=timezone.utc)
OPENED_AT = EVALUATED_AT - timedelta(days=1)


def _recommendation(*, direction: str = "long", action: str = "HOLD"):
    recommendation = {
        "recommendation_id": 171,
        "run_id": 51,
        "evaluation_time": EVALUATED_AT,
        "symbol": "BTC-USD",
        "timeframe": "1d",
        "regime": "BULL",
        "setup": "BULLISH_RESET",
        "direction": direction,
        "trend_score": Decimal("82"),
        "regime_score": Decimal("72"),
        "flow_score": Decimal("78"),
        "positioning_score": Decimal("74"),
        "volatility_score": Decimal("68"),
        "structure_score": Decimal("86"),
        "entry_conviction": Decimal("84"),
        "hold_score": Decimal("76"),
        "add_score": Decimal("87"),
        "entry_zone_lower": None,
        "entry_zone_upper": None,
        "invalidation_level": None,
        "initial_stop": None,
        "rr_ratio": None,
        "risk_fraction_nav": None,
        "risk_amount": None,
        "suggested_notional": None,
        "action": action,
    }
    if action == "ADD":
        recommendation.update(
            entry_zone_lower=Decimal("104000"),
            entry_zone_upper=Decimal("106000"),
            invalidation_level=Decimal("96000"),
            initial_stop=Decimal("95000"),
            rr_ratio=Decimal("2.5"),
            risk_fraction_nav=Decimal("0.005"),
            risk_amount=Decimal("10000"),
            suggested_notional=Decimal("200000"),
        )
    return recommendation


def _advisory(*, direction: str = "long", action: str = "HOLD"):
    return render_recommendation(
        _recommendation(direction=direction, action=action),
        (
            {
                "recommendation_id": 171,
                "reason_rank": 0,
                "code": "CROWDING_WARNING",
                "source_component": "positioning",
                "severity": "warning",
                "detail": "Positioning is crowded and reduces add quality.",
            },
            {
                "recommendation_id": 171,
                "reason_rank": 1,
                "code": "TREND_12W_POSITIVE",
                "source_component": "trend",
                "severity": "info",
                "detail": "Twelve-week momentum remains positive.",
            },
        ),
        predictor_run={
            "run_id": 51,
            "evaluation_time": EVALUATED_AT,
            **METADATA,
        },
        strategy_config=CONFIG,
    )


def _lifecycle(*, direction: str = "long", metadata=None):
    lifecycle = start_position_lifecycle(
        symbol="BTC-USD",
        direction=direction,
        state=PENDING_ENTRY,
        config_metadata=metadata or METADATA,
    )
    return apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=OPENED_AT,
        quantity="1",
        price="100000",
        stop_price="90000" if direction == "long" else "110000",
    )


def _trailing(lifecycle, *, mark: str, advance: bool = True):
    if lifecycle.direction == "long":
        structure = "98000" if advance else "85000"
        structure_type = HIGHER_LOW
    else:
        structure = "102000" if advance else "115000"
        structure_type = LOWER_HIGH
    return calculate_trailing_stop(
        direction=lifecycle.direction,
        previous_stop=lifecycle.stop_price,
        structure_price=structure,
        buffer="1500",
        current_price=mark,
        evaluated_at=EVALUATED_AT,
        config_metadata=METADATA,
        structure_id="structure-171",
        structure_source_feature_id="ENTRY_TRIGGER_HIGHER_LOW",
        structure_type=structure_type,
        structure_level_timestamp=EVALUATED_AT - timedelta(days=2),
        structure_detected_at=EVALUATED_AT - timedelta(hours=1),
        structure_reason_codes=("STRUCTURE_CONFIRMED",),
    )


def _risk(lifecycle, *, stop=None, tranches=None):
    return calculate_risk_at_stop(
        lifecycle.tranches if tranches is None else tranches,
        stop_price=lifecycle.stop_price if stop is None else stop,
        nav="2000000",
        direction=lifecycle.direction,
        config=CONFIG,
    )


def _report(*, direction: str = "long", action: str = "HOLD", advance=True):
    lifecycle = _lifecycle(direction=direction)
    mark = "105000" if direction == "long" else "95000"
    return render_position_management_report(
        advisory=_advisory(direction=direction, action=action),
        lifecycle=lifecycle,
        trailing_stop=_trailing(lifecycle, mark=mark, advance=advance),
        risk_at_stop=_risk(lifecycle),
        mark_price=mark,
        marked_at=EVALUATED_AT,
        mark_source_id="coinmetrics:BTC-USD:1d",
    )


def test_management_report_contract_and_required_output_are_stable() -> None:
    result = _report()

    assert isinstance(result, PositionManagementReportResult)
    assert result.feature_id == POSITION_MANAGEMENT_REPORT_FEATURE_ID
    assert result.report_version == POSITION_MANAGEMENT_REPORT_VERSION
    assert result.media_type == POSITION_MANAGEMENT_REPORT_MEDIA_TYPE
    assert result.complete is True
    assert result.metrics.market_notional == Decimal("105000.0")
    assert result.metrics.unrealized_pnl == Decimal("5000.0")
    assert result.metrics.unrealized_return_fraction == Decimal("0.05")
    assert result.metrics.exposure_fraction_nav == Decimal("0.0525")
    assert result.body.isascii()
    assert result.body.startswith("BTC POSITION MANAGEMENT\n\n")
    assert "State: OPEN INITIAL" in result.body
    assert "Average Entry: 100,000" in result.body
    assert "Current Stop: 90,000" in result.body
    assert "Candidate Stop: 96,500" in result.body
    assert "Stop Instruction: MOVE STOP TO 96,500" in result.body
    assert "Unrealized P&L: +5,000 (+5%)" in result.body
    assert "Hold Score: 76" in result.body
    assert "Add Score: 87" in result.body
    assert "Risk At Stop: 10,000 (0.5% NAV)" in result.body
    assert "Risk Limit: WITHIN LIMIT (max 1% NAV)" in result.body
    assert "SUGGESTED ACTION:\nHOLD POSITION" in result.body
    assert "[!] Positioning is crowded" in result.body
    assert "[+] Twelve-week momentum remains positive." in result.body


def test_report_persists_all_sources_and_replays_exactly() -> None:
    result = _report()
    record = result.as_record()
    restored = position_management_report_from_record(record)

    assert restored == result
    assert restored.as_record() == record
    assert record["config_metadata"] == METADATA
    assert record["mark"] == {
        "price": "105000",
        "marked_at": EVALUATED_AT.isoformat(),
        "source_id": "coinmetrics:BTC-USD:1d",
    }
    assert record["advisory"]["recommendation"]["action"] == "HOLD"
    assert record["lifecycle"]["state"] == "OPEN_INITIAL"
    assert record["trailing_stop"]["candidate_stop"] == "96500"
    assert record["risk_at_stop"]["risk_at_stop"] == "10000.0"


def test_short_position_uses_mirrored_pnl_and_stop_semantics() -> None:
    result = _report(direction="short")

    assert result.metrics.unrealized_pnl == Decimal("5000.0")
    assert "Direction: SHORT" in result.body
    assert "Current Stop: 110,000" in result.body
    assert "Candidate Stop: 103,500" in result.body
    assert "Stop Instruction: MOVE STOP TO 103,500" in result.body
    assert "Unrealized P&L: +5,000 (+5%)" in result.body


def test_held_candidate_is_distinct_from_the_active_stop() -> None:
    result = _report(advance=False)

    assert result.trailing_stop.advanced is False
    assert result.trailing_stop.candidate_stop == Decimal("83500")
    assert "Current Stop: 90,000" in result.body
    assert "Candidate Stop: 83,500" in result.body
    assert "Stop Instruction: KEEP CURRENT STOP" in result.body


@pytest.mark.parametrize(
    ("action", "label"),
    (
        ("HOLD", "HOLD POSITION"),
        ("ADD", "ADD TRANCHE"),
        ("TRIM", "TRIM POSITION"),
        ("EXIT", "EXIT POSITION"),
    ),
)
def test_every_existing_position_action_has_one_label(action: str, label: str) -> None:
    result = _report(action=action)

    assert f"SUGGESTED ACTION:\n{label}\n" in result.body


def test_report_rejects_non_management_action_and_closed_position() -> None:
    lifecycle = _lifecycle()
    with pytest.raises(ValueError, match="existing-position action"):
        render_position_management_report(
            advisory=_advisory(action="WATCH"),
            lifecycle=lifecycle,
            trailing_stop=_trailing(lifecycle, mark="105000"),
            risk_at_stop=_risk(lifecycle),
            mark_price="105000",
            marked_at=EVALUATED_AT,
            mark_source_id="mark",
        )

    closed = apply_position_event(
        lifecycle,
        event=EXIT,
        event_time=EVALUATED_AT - timedelta(hours=1),
        quantity="1",
        price="105000",
    )
    with pytest.raises(ValueError, match="open lifecycle"):
        render_position_management_report(
            advisory=_advisory(),
            lifecycle=closed,
            trailing_stop=_trailing(lifecycle, mark="105000"),
            risk_at_stop=_risk(lifecycle),
            mark_price="105000",
            marked_at=EVALUATED_AT,
            mark_source_id="mark",
        )


def test_report_rejects_mixed_times_stops_and_config_identity() -> None:
    lifecycle = _lifecycle()
    sources = {
        "advisory": _advisory(),
        "lifecycle": lifecycle,
        "trailing_stop": _trailing(lifecycle, mark="105000"),
        "risk_at_stop": _risk(lifecycle),
        "mark_price": "105000",
        "marked_at": EVALUATED_AT,
        "mark_source_id": "mark",
    }
    with pytest.raises(ValueError, match="mark time"):
        render_position_management_report(
            **{**sources, "marked_at": EVALUATED_AT - timedelta(hours=1)},
        )

    wrong_trailing = calculate_trailing_stop(
        direction="long",
        previous_stop="91000",
        current_price="105000",
        evaluated_at=EVALUATED_AT,
        config_metadata=METADATA,
    )
    with pytest.raises(ValueError, match="active lifecycle stop"):
        render_position_management_report(
            **{**sources, "trailing_stop": wrong_trailing},
        )

    with pytest.raises(ValueError, match="risk-at-stop must be measured"):
        render_position_management_report(
            **{**sources, "risk_at_stop": _risk(lifecycle, stop="91000")},
        )

    other = _lifecycle(metadata={**METADATA, "parameter_set_id": "other"})
    with pytest.raises(ValueError, match="lifecycle config identity"):
        render_position_management_report(
            **{**sources, "lifecycle": other},
        )


def test_report_rejects_risk_from_a_different_tranche_ledger() -> None:
    lifecycle = _lifecycle()
    mismatched = _risk(
        lifecycle,
        tranches=[
            {
                "tranche_id": "1",
                "entry_price": "100000",
                "quantity": "2",
            },
        ],
    )

    with pytest.raises(ValueError, match="tranches do not match"):
        render_position_management_report(
            advisory=_advisory(),
            lifecycle=lifecycle,
            trailing_stop=_trailing(lifecycle, mark="105000"),
            risk_at_stop=mismatched,
            mark_price="105000",
            marked_at=EVALUATED_AT,
            mark_source_id="mark",
        )


def test_restore_rejects_rendering_and_risk_record_drift() -> None:
    record = _report().as_record()
    changed_body = deepcopy(record)
    changed_body["body"] = str(changed_body["body"]).replace(
        "HOLD POSITION",
        "EXIT POSITION",
    )
    with pytest.raises(ValueError, match="body does not match"):
        position_management_report_from_record(changed_body)

    changed_risk = deepcopy(record["risk_at_stop"])
    changed_risk["risk_at_stop"] = "1"
    with pytest.raises(ValueError, match="sum of tranche contributions"):
        risk_at_stop_from_record(changed_risk)


def test_report_rejects_mark_source_line_injection() -> None:
    lifecycle = _lifecycle()
    with pytest.raises(ValueError, match="single-line"):
        render_position_management_report(
            advisory=_advisory(),
            lifecycle=lifecycle,
            trailing_stop=_trailing(lifecycle, mark="105000"),
            risk_at_stop=_risk(lifecycle),
            mark_price="105000",
            marked_at=EVALUATED_AT,
            mark_source_id="source\nSUGGESTED ACTION: EXIT",
        )
