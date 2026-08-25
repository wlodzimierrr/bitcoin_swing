from btc_predictor.db import (
    PREDICTOR_RUNS_PRIMARY_KEY,
    RECOMMENDATIONS_PRIMARY_KEY,
    RECOMMENDATION_REASON_CODES_PRIMARY_KEY,
    RECONSTRUCTABLE_RECOMMENDATION_COLUMNS,
    predictor_runs,
    recommendation_reason_codes,
    recommendations,
)


def test_predictor_runs_capture_strategy_identity_for_reconstruction() -> None:
    assert PREDICTOR_RUNS_PRIMARY_KEY == ("run_id",)
    for column_name in (
        "run_started_at",
        "evaluation_time",
        "data_available_at",
        "config_version",
        "strategy_version",
        "feature_version",
        "parameter_set_id",
        "code_commit",
        "data_snapshot_id",
    ):
        assert column_name in predictor_runs.c


def test_recommendations_capture_full_decision_payload() -> None:
    assert RECOMMENDATIONS_PRIMARY_KEY == ("recommendation_id",)
    for column_name in RECONSTRUCTABLE_RECOMMENDATION_COLUMNS:
        assert column_name in recommendations.c


def test_recommendation_reason_codes_are_ordered_and_attached_to_recommendations() -> None:
    assert RECOMMENDATION_REASON_CODES_PRIMARY_KEY == (
        "recommendation_id",
        "reason_rank",
    )
    for column_name in (
        "recommendation_id",
        "reason_rank",
        "code",
        "source_component",
        "severity",
        "detail",
    ):
        assert column_name in recommendation_reason_codes.c


def test_reconstructable_recommendation_columns_include_ticket_required_fields() -> None:
    required_fields = {
        "regime",
        "setup",
        "direction",
        "trend_score",
        "regime_score",
        "flow_score",
        "positioning_score",
        "volatility_score",
        "structure_score",
        "entry_conviction",
        "hold_score",
        "add_score",
        "entry_zone_lower",
        "entry_zone_upper",
        "invalidation_level",
        "initial_stop",
        "rr_ratio",
        "risk_fraction_nav",
        "risk_amount",
        "suggested_notional",
        "action",
    }

    assert required_fields.issubset(RECONSTRUCTABLE_RECOMMENDATION_COLUMNS)
