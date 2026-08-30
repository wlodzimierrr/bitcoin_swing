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
from btc_predictor.signals.reclaim import (
    DEFAULT_RECLAIM_CLOSE_BUFFER_FRACTION,
    DEFAULT_RECLAIM_CONFIRMATION_BARS,
    DEFAULT_RECLAIM_HOLD_BUFFER_FRACTION,
    RECLAIM_TRIGGER_FEATURE_ID,
    RECLAIM_TRIGGER_REASON_CODES,
    RECLAIM_TRIGGER_TYPE,
    ReclaimTriggerResult,
    evaluate_reclaim_trigger,
)

__all__ = [
    "DATA_QUALITY_BLOCKED_ACTIONS",
    "DATA_QUALITY_FAIL_REASON_CODE",
    "DEFAULT_RECLAIM_CLOSE_BUFFER_FRACTION",
    "DEFAULT_RECLAIM_CONFIRMATION_BARS",
    "DEFAULT_RECLAIM_HOLD_BUFFER_FRACTION",
    "RECOMMENDATION_ACTIONS",
    "RECOMMENDATION_REASON_SEVERITIES",
    "RECLAIM_TRIGGER_FEATURE_ID",
    "RECLAIM_TRIGGER_REASON_CODES",
    "RECLAIM_TRIGGER_TYPE",
    "DataQualityFailure",
    "DataQualityGatedRecommendation",
    "RecommendationReasonCode",
    "ReclaimTriggerResult",
    "apply_data_quality_gate",
    "build_recommendation_reason_code_records",
    "failures_from_quality_reports",
    "evaluate_reclaim_trigger",
]
