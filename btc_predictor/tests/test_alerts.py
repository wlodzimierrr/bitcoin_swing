import json
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.data import (
    DerivativesQualityIssue,
    DerivativesQualityReport,
    OhlcvQualityReport,
)
from btc_predictor.features.volatility import (
    EuphoriaFlagInput,
    StressFlagInput,
    calculate_euphoria_flag,
    calculate_stress_flag,
)
from btc_predictor.portfolio import (
    ENTER,
    PENDING_ENTRY,
    apply_position_event,
    open_paper_account,
    start_position_lifecycle,
)
from btc_predictor.reporting import (
    ACTIONABLE_SETUP,
    ALERT_TYPES,
    ALERTS_FEATURE_ID,
    ALERTS_MEDIA_TYPE,
    ALERTS_REASON_CODES,
    ALERTS_SCHEMA_VERSION,
    ALERTS_VERSION,
    DATA_QUALITY_FAIL_ALERT,
    ENTRY_ZONE_REACHED,
    EUPHORIA,
    EXIT_SIGNAL,
    NEW_ADD_SIGNAL,
    STOP_MOVE,
    STRESS,
    TRIM_SIGNAL,
    AlertPriceObservation,
    AlertsResult,
    alerts_from_record,
    create_alerts,
    render_daily_system_status,
    render_position_management_report,
    render_recommendation,
)
from btc_predictor.risk import (
    HIGHER_LOW,
    calculate_risk_at_stop,
    calculate_trailing_stop,
)


CONFIG = load_strategy_config()
METADATA = CONFIG.run_metadata()
AS_OF = datetime(2026, 9, 2, tzinfo=UTC)
LATEST_DATA = AS_OF - timedelta(hours=1)
OPENED_AT = AS_OF - timedelta(days=2)
MARK_PRICE = "105000"
SOURCE_ID = "bitstamp:BTC/USD:1h:raw-noncanonical"

_POSITION_ACTIONS = ("HOLD", "ADD", "TRIM", "EXIT")
_GEOMETRY_ACTIONS = ("ENTER", "ADD")
_DEFAULT_REASON = {
    "recommendation_id": 212,
    "reason_rank": 0,
    "code": "TREND_12W_POSITIVE",
    "source_component": "trend",
    "severity": "info",
    "detail": "Twelve-week momentum remains positive.",
}
_QUALITY_REASONS = (
    {
        "recommendation_id": 212,
        "reason_rank": 0,
        "code": "DATA_QUALITY_FAIL",
        "source_component": "data_quality",
        "severity": "warning",
        "detail": "Critical data quality failure is present.",
    },
    {
        "recommendation_id": 212,
        "reason_rank": 1,
        "code": "STALE_FUNDING",
        "source_component": "derivatives",
        "severity": "warning",
        "detail": "The latest funding observation is stale.",
    },
)


def _advisory(*, action: str = "WATCH", reasons=None):
    row = {
        "recommendation_id": 212,
        "run_id": 88,
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
        "entry_conviction": Decimal("88"),
        "hold_score": Decimal("74") if action in _POSITION_ACTIONS else None,
        "add_score": Decimal("86") if action in _POSITION_ACTIONS else None,
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
    if action in _GEOMETRY_ACTIONS:
        row.update(
            entry_zone_lower=Decimal("98500"),
            entry_zone_upper=Decimal("101000"),
            invalidation_level=Decimal("91300"),
            initial_stop=Decimal("89800"),
            rr_ratio=Decimal("3.2"),
            risk_fraction_nav=Decimal("0.005"),
            risk_amount=Decimal("10000"),
            suggested_notional=Decimal("200000"),
        )
    return render_recommendation(
        row,
        reasons or (_DEFAULT_REASON,),
        predictor_run={"run_id": 88, "evaluation_time": AS_OF, **METADATA},
        strategy_config=CONFIG,
    )


def _account():
    return open_paper_account(
        account_name="phase-1-paper",
        created_at=AS_OF - timedelta(days=30),
        starting_nav="1000000",
        reserved_cash="25000",
        config=CONFIG,
    )


def _pending_lifecycle():
    return start_position_lifecycle(
        symbol="BTC-USD",
        direction="long",
        state=PENDING_ENTRY,
        config_metadata=METADATA,
    )


def _open_lifecycle():
    return apply_position_event(
        _pending_lifecycle(),
        event=ENTER,
        event_time=OPENED_AT,
        quantity="1",
        price="100000",
        stop_price="90000",
    )


def _clean_reports(*, reverse: bool = False):
    items = (
        ("ohlcv", OhlcvQualityReport(issues=())),
        ("derivatives", DerivativesQualityReport(issues=())),
    )
    if reverse:
        items = tuple(reversed(items))
    return dict(items)


def _failed_reports():
    return {
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


def _daily_status(*, advisory=None, quality_reports=None, lifecycles=()):
    return render_daily_system_status(
        advisory=advisory if advisory is not None else _advisory(),
        quality_reports=quality_reports or _clean_reports(),
        latest_data_timestamp=LATEST_DATA,
        latest_data_source_id=SOURCE_ID,
        paper_account=_account(),
        position_lifecycles=lifecycles,
    )


def _position_report(advisory, lifecycle, *, advance: bool = True):
    trailing = calculate_trailing_stop(
        direction=lifecycle.direction,
        previous_stop=lifecycle.stop_price,
        structure_price="98000" if advance else "85000",
        buffer="1500",
        current_price=MARK_PRICE,
        evaluated_at=AS_OF,
        config_metadata=METADATA,
        structure_id="structure-212",
        structure_source_feature_id="ENTRY_TRIGGER_HIGHER_LOW",
        structure_type=HIGHER_LOW,
        structure_level_timestamp=AS_OF - timedelta(days=3),
        structure_detected_at=AS_OF - timedelta(hours=2),
        structure_reason_codes=("STRUCTURE_CONFIRMED",),
    )
    risk = calculate_risk_at_stop(
        lifecycle.tranches,
        stop_price=lifecycle.stop_price,
        nav="2000000",
        direction=lifecycle.direction,
        config=CONFIG,
    )
    return render_position_management_report(
        advisory=advisory,
        lifecycle=lifecycle,
        trailing_stop=trailing,
        risk_at_stop=risk,
        mark_price=MARK_PRICE,
        marked_at=AS_OF,
        mark_source_id=SOURCE_ID,
    )


def _stress(*, flagged: bool = False, complete: bool = True):
    return calculate_stress_flag(
        StressFlagInput(
            volatility_percentile=Decimal("40") if complete else None,
            liquidation_percentile=Decimal("35"),
            downside_return=Decimal("-0.01"),
            funding_zscore=Decimal("0.4"),
            basis_zscore=Decimal("0.3"),
            systemic_shock=flagged,
        ),
        config_metadata=METADATA,
    )


def _euphoria(*, flagged: bool = False, complete: bool = True):
    return calculate_euphoria_flag(
        EuphoriaFlagInput(
            range_percentile=Decimal("40") if complete else None,
            upside_return=Decimal("0.02"),
            funding_zscore=Decimal("0.3"),
            basis_zscore=Decimal("0.2"),
            oi_intensity_percentile=Decimal("38"),
            volatility_percentile=Decimal("41"),
            systemic_euphoria=flagged,
        ),
        config_metadata=METADATA,
    )


def _price(price: str = "99500", *, observed_at: datetime = AS_OF):
    return AlertPriceObservation.create(
        price=price,
        observed_at=observed_at,
        source_id=SOURCE_ID,
    )


def _alerts(**changes):
    values = {
        "daily_status": _daily_status(lifecycles=(_pending_lifecycle(),)),
        "stress": _stress(),
        "euphoria": _euphoria(),
    }
    values.update(changes)
    return create_alerts(**values)


def _entry_batch(**changes):
    advisory = _advisory(action="ENTER")
    values = {
        "daily_status": _daily_status(
            advisory=advisory,
            lifecycles=(_pending_lifecycle(),),
        ),
        "price_observation": _price(),
    }
    values.update(changes)
    return _alerts(**values)


def _position_batch(action: str, *, advance: bool = True, **changes):
    advisory = _advisory(action=action)
    lifecycle = _open_lifecycle()
    values = {
        "daily_status": _daily_status(advisory=advisory, lifecycles=(lifecycle,)),
        "position_management_reports": (
            _position_report(advisory, lifecycle, advance=advance),
        ),
    }
    if action in _GEOMETRY_ACTIONS:
        values["price_observation"] = _price()
    values.update(changes)
    return _alerts(**values)


def _types(result: AlertsResult) -> tuple[str, ...]:
    return tuple(alert.alert_type for alert in result.alerts)


def test_entry_setup_emits_actionable_and_entry_zone_alerts_with_provenance() -> None:
    result = _entry_batch()

    assert isinstance(result, AlertsResult)
    assert result.feature_id == ALERTS_FEATURE_ID
    assert result.alerts_version == ALERTS_VERSION
    assert result.schema_version == ALERTS_SCHEMA_VERSION
    assert result.media_type == ALERTS_MEDIA_TYPE
    assert result.as_of == AS_OF
    assert result.config_metadata == METADATA
    assert result.complete is True
    assert _types(result) == (ACTIONABLE_SETUP, ENTRY_ZONE_REACHED)
    assert result.reason_codes == (
        "ALERTS_EMITTED",
        "ALERTS_ENTRY_ZONE_EVALUATED",
    )

    setup_alert, zone_alert = result.alerts
    assert setup_alert.symbol == "BTC-USD"
    assert setup_alert.recommendation_id == 212
    assert setup_alert.source_feature_id == result.daily_status.advisory.feature_id
    assert setup_alert.source_reason_codes == ("TREND_12W_POSITIVE",)
    assert setup_alert.details["action"] == "ENTER"
    assert setup_alert.details["entry_conviction"] == "88"
    assert zone_alert.details["price"] == "99500"
    assert zone_alert.details["price_source_id"] == SOURCE_ID
    assert zone_alert.details["entry_zone_lower"] == "98500"
    assert zone_alert.details["entry_zone_upper"] == "101000"


def test_add_batch_emits_add_zone_and_owner_reported_stop_move() -> None:
    result = _position_batch("ADD")

    assert _types(result) == (ENTRY_ZONE_REACHED, NEW_ADD_SIGNAL, STOP_MOVE)
    stop_alert = result.alerts[-1]
    trailing = result.position_management_reports[0].trailing_stop
    assert trailing.advanced is True
    assert stop_alert.source_feature_id == trailing.feature_id
    assert stop_alert.source_reason_codes == tuple(trailing.reason_codes)
    assert stop_alert.details["previous_stop"] == "90000"
    assert stop_alert.details["new_stop"] == str(trailing.stop_price)
    assert stop_alert.details["structure_id"] == "structure-212"
    assert result.alerts[1].details["add_score"] == "86"


def test_held_stop_emits_no_stop_move_and_trim_exit_use_persisted_action() -> None:
    trim = _position_batch("TRIM", advance=False)
    assert _types(trim) == (TRIM_SIGNAL,)
    assert trim.alerts[0].details["hold_score"] == "74"
    assert trim.position_management_reports[0].trailing_stop.advanced is False

    exit_batch = _position_batch("EXIT", advance=False)
    assert _types(exit_batch) == (EXIT_SIGNAL,)
    assert exit_batch.alerts[0].details["action"] == "EXIT"


def test_failed_data_quality_emits_alert_with_component_reason_codes() -> None:
    status = _daily_status(
        advisory=_advisory(action="WATCH", reasons=_QUALITY_REASONS),
        quality_reports=_failed_reports(),
        lifecycles=(_pending_lifecycle(),),
    )
    result = _alerts(daily_status=status)

    assert _types(result) == (DATA_QUALITY_FAIL_ALERT,)
    alert = result.alerts[0]
    assert alert.source_feature_id == status.feature_id
    assert alert.source_reason_codes == ("STALE_FUNDING",)
    assert alert.details["failed_components"] == ["derivatives"]
    assert alert.details["latest_data_source_id"] == SOURCE_ID
    assert alert.details["latest_data_timestamp"] == LATEST_DATA.isoformat()


def test_hard_flags_emit_alerts_and_surface_incomplete_flag_inputs() -> None:
    result = _alerts(
        stress=_stress(flagged=True, complete=False),
        euphoria=_euphoria(flagged=True),
    )

    assert _types(result) == (STRESS, EUPHORIA)
    stress_alert, euphoria_alert = result.alerts
    assert stress_alert.source_feature_id == "STRESS"
    assert "STRESS_SYSTEMIC_MARKET_SHOCK" in stress_alert.source_reason_codes
    assert stress_alert.details["max_exposure_multiplier"] == "0.50"
    assert stress_alert.details["block_new_trades"] is False
    assert euphoria_alert.source_feature_id == "EUPHORIA"
    assert result.complete is False
    assert result.reason_codes == (
        "ALERTS_EMITTED",
        "ALERTS_ENTRY_ZONE_NOT_APPLICABLE",
        "ALERTS_STRESS_SOURCE_INCOMPLETE",
    )


def test_every_documented_alert_type_is_reachable() -> None:
    emitted = set()
    for result in (
        _entry_batch(),
        _position_batch("ADD"),
        _position_batch("TRIM"),
        _position_batch("EXIT"),
        _alerts(stress=_stress(flagged=True), euphoria=_euphoria(flagged=True)),
        _alerts(
            daily_status=_daily_status(
                advisory=_advisory(action="WATCH", reasons=_QUALITY_REASONS),
                quality_reports=_failed_reports(),
                lifecycles=(_pending_lifecycle(),),
            ),
        ),
    ):
        emitted.update(_types(result))

    assert emitted == set(ALERT_TYPES)


def test_quiet_state_emits_no_alerts_and_records_that_fact() -> None:
    result = _alerts()

    assert result.alerts == ()
    assert result.complete is True
    assert result.reason_codes == (
        "ALERTS_NONE_EMITTED",
        "ALERTS_ENTRY_ZONE_NOT_APPLICABLE",
    )
    assert set(result.reason_codes) <= set(ALERTS_REASON_CODES)
    assert json.loads(result.body)["alerts"] == []


def test_entry_zone_membership_is_exact_and_never_assumed() -> None:
    inside = _entry_batch(price_observation=_price("98500"))
    assert ENTRY_ZONE_REACHED in _types(inside)

    upper_edge = _entry_batch(price_observation=_price("101000"))
    assert ENTRY_ZONE_REACHED in _types(upper_edge)

    outside = _entry_batch(price_observation=_price("101000.01"))
    assert _types(outside) == (ACTIONABLE_SETUP,)
    assert outside.complete is True


def test_missing_entry_zone_price_is_surfaced_rather_than_assumed() -> None:
    advisory = _advisory(action="ENTER")
    result = _alerts(
        daily_status=_daily_status(
            advisory=advisory,
            lifecycles=(_pending_lifecycle(),),
        ),
    )

    assert _types(result) == (ACTIONABLE_SETUP,)
    assert result.price_observation is None
    assert result.complete is False
    assert result.reason_codes == (
        "ALERTS_EMITTED",
        "ALERTS_ENTRY_ZONE_PRICE_MISSING",
    )


def test_alerts_are_deterministic_across_position_report_input_order() -> None:
    first = _entry_batch()
    second = _entry_batch()

    assert first == second
    assert first.as_record() == second.as_record()
    assert first.body == second.body

    advisory = _advisory(action="TRIM")
    long_lifecycle = _open_lifecycle()
    other = apply_position_event(
        start_position_lifecycle(
            symbol="BTC-USD",
            direction="long",
            state=PENDING_ENTRY,
            config_metadata=METADATA,
        ),
        event=ENTER,
        event_time=OPENED_AT,
        quantity="2",
        price="99000",
        stop_price="90000",
    )
    status = _daily_status(advisory=advisory, lifecycles=(long_lifecycle, other))
    reports = (
        _position_report(advisory, long_lifecycle),
        _position_report(advisory, other),
    )
    forward = _alerts(daily_status=status, position_management_reports=reports)
    reverse = _alerts(
        daily_status=status,
        position_management_reports=tuple(reversed(reports)),
    )

    assert forward == reverse
    assert forward.as_record() == reverse.as_record()
    assert _types(forward) == (STOP_MOVE, STOP_MOVE, TRIM_SIGNAL)
    assert list(_types(forward)) == sorted(
        _types(forward),
        key=ALERT_TYPES.index,
    )


def test_record_replays_exactly_and_retains_complete_provenance() -> None:
    result = _position_batch("ADD")
    record = result.as_record()

    assert record["config_metadata"] == METADATA
    assert record["daily_status"]["advisory"]["recommendation"][
        "recommendation_id"
    ] == 212
    assert record["stress"]["config_metadata"] == METADATA
    assert record["euphoria"]["config_metadata"] == METADATA
    assert record["price_observation"]["source_id"] == SOURCE_ID
    assert [alert["alert_type"] for alert in record["alerts"]] == list(_types(result))
    assert record["reason_codes"] == list(result.reason_codes)

    restored = alerts_from_record(record)
    assert restored == result
    assert restored.as_record() == record
    assert json.dumps(record, sort_keys=True) == json.dumps(
        restored.as_record(),
        sort_keys=True,
    )


def test_record_rejects_alert_body_reason_and_source_tampering() -> None:
    record = _position_batch("ADD").as_record()

    dropped = deepcopy(record)
    dropped["alerts"] = dropped["alerts"][:1]
    with pytest.raises(ValueError, match="alerts do not match source state"):
        alerts_from_record(dropped)

    retyped = deepcopy(record)
    retyped["alerts"][0]["alert_type"] = EXIT_SIGNAL
    with pytest.raises(ValueError, match="alerts do not match source state"):
        alerts_from_record(retyped)

    changed_body = deepcopy(record)
    changed_body["body"] = str(changed_body["body"]).replace(
        NEW_ADD_SIGNAL,
        EXIT_SIGNAL,
    )
    with pytest.raises(ValueError, match="body does not match alerts"):
        alerts_from_record(changed_body)

    changed_reasons = deepcopy(record)
    changed_reasons["reason_codes"] = ["ALERTS_NONE_EMITTED"]
    with pytest.raises(ValueError, match="reason_codes do not match"):
        alerts_from_record(changed_reasons)

    changed_complete = deepcopy(record)
    changed_complete["complete"] = False
    with pytest.raises(ValueError, match="complete does not match"):
        alerts_from_record(changed_complete)

    changed_advisory = deepcopy(record)
    changed_advisory["daily_status"]["advisory"]["recommendation"]["action"] = "EXIT"
    with pytest.raises(ValueError):
        alerts_from_record(changed_advisory)

    changed_stress = deepcopy(record)
    changed_stress["stress"]["flagged"] = True
    with pytest.raises(ValueError, match="stress record does not match"):
        alerts_from_record(changed_stress)

    changed_price = deepcopy(record)
    changed_price["price_observation"]["price"] = "1"
    with pytest.raises(ValueError, match="alerts do not match source state"):
        alerts_from_record(changed_price)


def test_open_positions_must_be_exactly_covered_by_current_reports() -> None:
    advisory = _advisory(action="TRIM")
    lifecycle = _open_lifecycle()
    status = _daily_status(advisory=advisory, lifecycles=(lifecycle,))

    with pytest.raises(ValueError, match="exactly cover current open lifecycles"):
        _alerts(daily_status=status)

    report = _position_report(advisory, lifecycle)
    with pytest.raises(ValueError, match="must not contain duplicates"):
        _alerts(
            daily_status=status,
            position_management_reports=(report, report),
        )

    other_advisory = _advisory(action="HOLD")
    other_lifecycle = _open_lifecycle()
    with pytest.raises(ValueError, match="advisory must match daily status"):
        _alerts(
            daily_status=status,
            position_management_reports=(
                _position_report(other_advisory, other_lifecycle),
            ),
        )


def test_alerts_reject_config_identity_and_point_in_time_drift() -> None:
    stale_metadata = {**METADATA, "parameter_set_id": "other"}
    with pytest.raises(ValueError, match="stress config identity"):
        _alerts(
            stress=calculate_stress_flag(
                StressFlagInput(
                    volatility_percentile=Decimal("40"),
                    liquidation_percentile=Decimal("35"),
                    downside_return=Decimal("-0.01"),
                    funding_zscore=Decimal("0.4"),
                    basis_zscore=Decimal("0.3"),
                    systemic_shock=False,
                ),
                config_metadata=stale_metadata,
            ),
        )

    with pytest.raises(ValueError, match="price observation time must match"):
        _entry_batch(
            price_observation=_price(observed_at=AS_OF - timedelta(hours=1)),
        )

    with pytest.raises(ValueError, match="UTC"):
        _price(observed_at=datetime(2026, 9, 2))


def test_alerts_reject_forged_owner_identity_and_injection_prone_sources() -> None:
    result = _entry_batch()

    with pytest.raises(ValueError, match="feature_id must be"):
        replace(result, feature_id="OTHER").as_record()

    with pytest.raises(ValueError, match="as_of must match daily status"):
        replace(result, as_of=AS_OF + timedelta(seconds=1)).as_record()

    with pytest.raises(TypeError, match="daily_status must be"):
        create_alerts(
            daily_status=object(),
            stress=_stress(),
            euphoria=_euphoria(),
        )

    with pytest.raises(TypeError, match="must be a sequence"):
        _alerts(position_management_reports="report")

    with pytest.raises(ValueError, match="single-line"):
        _price(observed_at=AS_OF).__class__.create(
            price="99500",
            observed_at=AS_OF,
            source_id="source\nALERT",
        )
