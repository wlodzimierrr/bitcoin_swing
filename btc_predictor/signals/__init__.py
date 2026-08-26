"""Signal and recommendation modules."""

from btc_predictor.signals.data_quality import (
    DATA_QUALITY_BLOCKED_ACTIONS,
    DATA_QUALITY_FAIL_REASON_CODE,
    RECOMMENDATION_ACTIONS,
    RECOMMENDATION_REASON_SEVERITIES,
    DataQualityFailure,
    DataQualityGatedRecommendation,
    RecommendationReasonCode,
    apply_data_quality_gate,
    build_recommendation_reason_code_records,
    failures_from_quality_reports,
)

__all__ = [
    "DATA_QUALITY_BLOCKED_ACTIONS",
    "DATA_QUALITY_FAIL_REASON_CODE",
    "RECOMMENDATION_ACTIONS",
    "RECOMMENDATION_REASON_SEVERITIES",
    "DataQualityFailure",
    "DataQualityGatedRecommendation",
    "RecommendationReasonCode",
    "apply_data_quality_gate",
    "build_recommendation_reason_code_records",
    "failures_from_quality_reports",
]
