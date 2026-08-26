from datetime import UTC, datetime

import pytest

from btc_predictor.data import (
    DerivativesQualityIssue,
    DerivativesQualityReport,
    OhlcvQualityIssue,
    OhlcvQualityReport,
)
from btc_predictor.signals import (
    DATA_QUALITY_BLOCKED_ACTIONS,
    DATA_QUALITY_FAIL_REASON_CODE,
    DataQualityFailure,
    RecommendationReasonCode,
    apply_data_quality_gate,
    build_recommendation_reason_code_records,
    failures_from_quality_reports,
)


def ohlcv_report() -> OhlcvQualityReport:
    return OhlcvQualityReport(
        issues=(
            OhlcvQualityIssue(
                reason_code="MISSING_PERIOD",
                severity="error",
                message="Expected OHLCV period is missing.",
                timestamp=datetime(2026, 8, 26, tzinfo=UTC),
            ),
        )
    )


def derivatives_report() -> DerivativesQualityReport:
    return DerivativesQualityReport(
        issues=(
            DerivativesQualityIssue(
                reason_code="STALE_FUNDING",
                severity="error",
                message="Latest funding observation is stale.",
                timestamp=datetime(2026, 8, 26, tzinfo=UTC),
            ),
        )
    )


def test_data_quality_fail_reason_code_and_blocked_actions_are_stable() -> None:
    assert DATA_QUALITY_FAIL_REASON_CODE == "DATA_QUALITY_FAIL"
    assert DATA_QUALITY_BLOCKED_ACTIONS == ("ENTER", "ADD")


def test_failed_quality_reports_are_converted_to_deterministic_failures() -> None:
    failures = failures_from_quality_reports(
        {
            "ohlcv": ohlcv_report(),
            "derivatives": derivatives_report(),
            "empty": OhlcvQualityReport(issues=()),
        }
    )

    assert failures == (
        DataQualityFailure(source_component="derivatives", reason_codes=("STALE_FUNDING",)),
        DataQualityFailure(source_component="ohlcv", reason_codes=("MISSING_PERIOD",)),
    )


def test_data_quality_fail_blocks_new_trade_entries() -> None:
    recommendation = apply_data_quality_gate(
        "ENTER",
        (DataQualityFailure("ohlcv", ("MISSING_PERIOD",)),),
    )

    assert recommendation.data_quality_fail is True
    assert recommendation.blocked_by_data_quality is True
    assert recommendation.requested_action == "ENTER"
    assert recommendation.action == "NO_TRADE"
    assert [reason.code for reason in recommendation.reason_codes] == [
        "DATA_QUALITY_FAIL",
        "MISSING_PERIOD",
    ]
    assert all(reason.severity == "veto" for reason in recommendation.reason_codes)


def test_data_quality_fail_blocks_add_but_preserves_existing_position_state() -> None:
    position_state = {
        "position_id": 42,
        "state": "OPEN",
        "current_notional": "25000",
        "stop": "108000",
    }

    recommendation = apply_data_quality_gate(
        "ADD",
        (DataQualityFailure("derivatives", ("STALE_FUNDING", "UNIT_CHANGE")),),
        existing_position_state=position_state,
    )

    assert recommendation.action == "HOLD"
    assert recommendation.blocked_by_data_quality is True
    assert recommendation.existing_position_state == position_state
    assert [reason.code for reason in recommendation.reason_codes] == [
        "DATA_QUALITY_FAIL",
        "STALE_FUNDING",
        "UNIT_CHANGE",
    ]
    assert all(reason.severity == "veto" for reason in recommendation.reason_codes)


def test_data_quality_fail_does_not_block_existing_position_exit_actions() -> None:
    recommendation = apply_data_quality_gate(
        "EXIT",
        (DataQualityFailure("ohlcv", ("STALE_DATA",)),),
        existing_position_state={"position_id": 42, "state": "OPEN"},
    )

    assert recommendation.action == "EXIT"
    assert recommendation.blocked_by_data_quality is False
    assert recommendation.data_quality_fail is True
    assert [reason.severity for reason in recommendation.reason_codes] == [
        "warning",
        "warning",
    ]


def test_data_quality_gate_leaves_clean_recommendations_unchanged() -> None:
    recommendation = apply_data_quality_gate(
        "WATCH",
        (),
        existing_position_state={"position_id": None, "state": "FLAT"},
    )

    assert recommendation.action == "WATCH"
    assert recommendation.data_quality_fail is False
    assert recommendation.reason_codes == ()
    assert recommendation.existing_position_state == {"position_id": None, "state": "FLAT"}


def test_data_quality_failure_rejects_empty_reason_codes() -> None:
    with pytest.raises(ValueError, match="reason_codes"):
        DataQualityFailure("ohlcv", ())


def test_recommendation_reason_code_rejects_invalid_severity() -> None:
    with pytest.raises(ValueError, match="Unsupported recommendation reason severity"):
        RecommendationReasonCode(
            code="DATA_QUALITY_FAIL",
            source_component="data_quality",
            severity="error",
            detail="bad severity",
        )


def test_data_quality_gate_rejects_unknown_actions() -> None:
    with pytest.raises(ValueError, match="Unsupported recommendation action"):
        apply_data_quality_gate(
            "SCALE_IN",
            (DataQualityFailure("ohlcv", ("MISSING_PERIOD",)),),
        )


def test_data_quality_failure_reasons_build_persistable_reason_code_rows() -> None:
    recommendation = apply_data_quality_gate(
        "ENTER",
        (
            DataQualityFailure("ohlcv", ("MISSING_PERIOD",)),
            DataQualityFailure("derivatives", ("STALE_FUNDING",)),
        ),
    )

    records = build_recommendation_reason_code_records(
        recommendation_id=123,
        reason_codes=recommendation.reason_codes,
    )

    assert [record["reason_rank"] for record in records] == [0, 1, 2]
    assert [record["code"] for record in records] == [
        "DATA_QUALITY_FAIL",
        "STALE_FUNDING",
        "MISSING_PERIOD",
    ]
    assert records[0] == {
        "recommendation_id": 123,
        "reason_rank": 0,
        "code": "DATA_QUALITY_FAIL",
        "source_component": "data_quality",
        "severity": "veto",
        "detail": "Critical data quality failure blocks new trade and add actions.",
    }


def test_reason_code_records_reject_invalid_recommendation_id() -> None:
    with pytest.raises(ValueError, match="recommendation_id"):
        build_recommendation_reason_code_records(
            recommendation_id=0,
            reason_codes=(
                RecommendationReasonCode(
                    code="DATA_QUALITY_FAIL",
                    source_component="data_quality",
                    severity="veto",
                    detail="blocked",
                ),
            ),
        )
