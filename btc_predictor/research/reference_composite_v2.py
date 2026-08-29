"""Frozen research protocol for BTC_REFERENCE_COMPOSITE_V2.

This module defines protocol and synthetic-evaluation behavior only. It does not
collect or validate the sealed 2015-2019 out-of-sample period.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

from btc_predictor.data import require_utc_datetime
from btc_predictor.research.reference_composite import (
    BITFINEX_PROVIDER_ID,
    BITSTAMP_PROVIDER_ID,
    COINBASE_PROVIDER_ID,
    DEFAULT_CLOSE_DISAGREEMENT_BPS,
    DEFAULT_DECISION_DELAY,
    DEFAULT_TWO_PROVIDER_RANGE_DISAGREEMENT_ATR,
    REFERENCE_DEGRADED,
    REFERENCE_OK,
    REFERENCE_UNAVAILABLE,
    REQUIRED_COMPOSITE_PROVIDER_IDS,
    SINGLE_PROVIDER_OBSERVATION,
    THREE_PROVIDER_CONSENSUS,
    TWO_PROVIDER_CONSENSUS,
    UNRESOLVED_PROVIDER_DISAGREEMENT,
    VENUE_DISAGREEMENT,
    CompositeDiagnostics,
    ProviderCandleInput,
)


V2_PROTOCOL_VERSION = "BTC_REFERENCE_COMPOSITE_V2"
V2_PROTOCOL_STATUS = "FROZEN_RESEARCH_PROTOCOL"
V2_METHOD = "median_ohlc"
V2_METHOD_VERSION = "MEDIAN_OHLC_V2"
V2_FORMULA = (
    "For every OHLC field independently, publish the median of all provider "
    "values available at the fixed decision time."
)
V2_MINIMUM_PROVIDER_COUNT = 2
V2_ATR_WINDOW_DAYS = 14
V2_PROVIDER_EXCHANGES = {
    BITSTAMP_PROVIDER_ID: "bitstamp",
    COINBASE_PROVIDER_ID: "coinbase",
    BITFINEX_PROVIDER_ID: "bitfinex",
}
V2_PROVIDER_NORMALIZED_SYMBOLS = {
    BITSTAMP_PROVIDER_ID: "BTC/USD",
    COINBASE_PROVIDER_ID: "BTC-USD",
    BITFINEX_PROVIDER_ID: "BTC/USD",
}
V2_PROVIDER_API_SYMBOLS = {
    BITSTAMP_PROVIDER_ID: "btcusd",
    COINBASE_PROVIDER_ID: "BTC-USD",
    BITFINEX_PROVIDER_ID: "tBTCUSD",
}
V2_ATR_MATERIALITY_GRID = (
    Decimal("0.10"),
    Decimal("0.20"),
    Decimal("0.30"),
    Decimal("0.50"),
    Decimal("1.00"),
)
V2_PRIMARY_ATR_MATERIALITY_THRESHOLD = Decimal("0.50")

UNTOUCHED_OOS_START = datetime(2015, 7, 20, 21, tzinfo=UTC)
UNTOUCHED_OOS_END = datetime(2019, 11, 30, 23, tzinfo=UTC)
UNTOUCHED_OOS_STATUS = (
    "BOUNDARY_VERIFIED",
    "BULK_COMPLETENESS_UNMEASURED",
    "OUTCOMES_UNINSPECTED",
    "DO_NOT_OPEN_UNTIL_V2_VALIDATION",
)

BUCKET_COMPLETE_OK = "BUCKET_COMPLETE_OK"
BUCKET_COMPLETE_DEGRADED = "BUCKET_COMPLETE_DEGRADED"
BUCKET_COMPLETE_VENUE_DISAGREEMENT = "BUCKET_COMPLETE_VENUE_DISAGREEMENT"
BUCKET_INCOMPLETE_UNUSABLE = "BUCKET_INCOMPLETE_UNUSABLE"
V2_BUCKET_STATUSES = (
    BUCKET_COMPLETE_OK,
    BUCKET_COMPLETE_DEGRADED,
    BUCKET_COMPLETE_VENUE_DISAGREEMENT,
    BUCKET_INCOMPLETE_UNUSABLE,
)

V2_REASON_CODES = (
    "V2_INPUT_COUNT_INSUFFICIENT",
    "V2_PROVIDER_LATE",
    "V2_CLOSE_PARTIAL_CONSENSUS",
    "V2_CLOSE_DISAGREEMENT_PUBLISHED",
    "V2_THREE_PROVIDER_RANGE_DISAGREEMENT",
    "V2_TWO_PROVIDER_CLOSE_DISAGREEMENT",
    "V2_TWO_PROVIDER_RANGE_DISAGREEMENT",
    "V2_TRAILING_ATR_UNAVAILABLE",
    "V2_CANDLE_INVARIANT_FAILED",
    "V2_INCOMPLETE_BUCKET",
    "V2_BUCKET_CONTAINS_DEGRADED_HOURS",
    "V2_BUCKET_CONTAINS_VENUE_DISAGREEMENT",
)

# Frozen dependency evidence. A mismatch means an earlier research result changed.
EXPECTED_V1_ARTIFACT_SHA256 = {
    "candidate_definition.json": "c2ca6c24363e3964bb1332a35242c2b7dfc93421034f8e5bf8e702a406d8561e",
    "database_persistence_evidence.json": "b750e9f1d66fdd8fea1fd5e25fc990ddbfb212b59626746cffd8a7fc1b69afa0",
    "development_validation_report.json": "8d0555b345bbc430e2f21fba1caef36de5849f22927b3e6fb8f876762a40ea0f",
    "external_manual_review_assessments.json": "90e88d7e5ed276df70193837b901c060a4d83f75ca8e99cc2ac7ae5cb7a95256",
    "external_validation_report.json": "f10de48bd501957f1c59ad58b168e0c8c9a6e6532d71c1145b77be43cc562055",
    "final_decision.json": "cb0a32e14b45cf496c75029a17a83df68450367eba4c6e49708f3388819fc1e3",
    "final_research_report.md": "3aca594b9a08333baeab01bdf97f80f559d776b54a6d830a0af14cd4611da4cb",
    "point_in_time_metadata_correction.json": "2022e45d572a3e435c0973404329469d3b421c5cafcff5bef87b59559703baf4",
}
EXPECTED_BTC019B_ARTIFACT_SHA256 = {
    "degraded_bar_diagnostics.json": "7fef4315bb752bbd35bc18d7b00c3191a3e904a3cdb16129909f00bbbe638fdb",
    "degraded_episode_diagnostics.json": "c1ba2dd65c5ef2da0e23058c3afe7ec3c2825238304f67e0d3546b3d9bea328c",
    "diagnostic_protocol.json": "a3c566a5865591d617172dbc278fcdaa3092892d1c356da13004d8614a2d12bc",
    "final_diagnostic_decision.json": "d911b7dba49ae3f4d05307efb655b0b18b3cc8fcb2ee8c9791ae42033c97a73d",
    "final_diagnostic_report.md": "94e5a844a3eeabf4c28234292ab1b8ffcb59afab6a7226a0eab4525c6bd146bc",
    "swing_disagreement_diagnostics.json": "d916bf9906cd50c8c86dab0510478283d2714d523a76adad65ab4676984002a5",
}
EXPECTED_BTC019_ARTIFACT_SHA256 = {
    "canonical_source_decision.json": "5ca7f5de0492cf2f2b31bd854a282f23a4054a75fd7d0a9c5ad044e24168fa0d",
    "collection_manifest.json": "a2fd940ceb04c3fa8d864a4755f0d7789ff6f4f872907adf3c2e81701940504e",
    "comparison_report.json": "82479ba02ab59e8e412f988a0208bbbaa02c8096eb756335e10211cfab730fac",
    "empirical_validation_report.md": "41aed55372af99bb6bad8cdeff98f435950583d01fa240b6aa52d7f509843d79",
    "manual_reviews.json": "b50aa107358d460a3b4cecdf0f4e61c365241972d73c4d72f2a43a97c3f73c95",
    "review_assessments.json": "f6b8dbf775ffa81c1bb229b10a2034cdd91b1f2d364a419aa34c7766150c0980",
    "supplemental_analysis.json": "94ed504ed111090fe7313445c785b817b48fdb7cce7067e274aaffb024bf29f8",
}

FROZEN_V2_DEFINITION_SHA256 = (
    "bc312f3e6a6035e00a3cd80103aacdee7b5a02ae69732b7bbca5785a3dd6106a"
)
EXPECTED_V2_PROTOCOL_ARTIFACT_SHA256 = {
    "protocol_definition.json": (
        "adfbd36395220fb5f7ae9f5e97e24a5ca809a0e6a09fd8f3b20f75d928862d5e"
    ),
    "protocol_report.md": (
        "5ba71aa54a5fb63fe91e7029db85aee1c2ab9c3a91372fc048a801bce42b2c5e"
    ),
}


class UntouchedValidationSampleGuardError(RuntimeError):
    """Raised when exploratory work overlaps the sealed V2 validation sample."""


@dataclass(frozen=True)
class ApprovalGate:
    metric: str
    threshold: str | int | bool
    direction: str
    hard: bool
    rationale: str
    source_of_rationale: str
    validation_stage: str = "historical_oos"

    def as_record(self) -> dict[str, Any]:
        if self.direction not in ("minimum", "maximum", "equal"):
            raise ValueError("approval-gate direction must be minimum, maximum, or equal")
        if not self.metric or not self.rationale or not self.source_of_rationale:
            raise ValueError("approval-gate text fields must be non-empty")
        if self.validation_stage not in ("historical_oos", "promotion"):
            raise ValueError("unknown validation stage")
        return {
            "metric": self.metric,
            "threshold": self.threshold,
            "direction": self.direction,
            "hard": self.hard,
            "rationale": self.rationale,
            "source_of_rationale": self.source_of_rationale,
            "validation_stage": self.validation_stage,
        }


V2_APPROVAL_GATES = (
    ApprovalGate(
        "validation_period_days",
        1460,
        "minimum",
        True,
        "Require at least four years spanning multiple market regimes.",
        "Economic coverage requirement; candidate sealed period exceeds four years.",
    ),
    ApprovalGate(
        "reference_usable_rate",
        "0.995",
        "minimum",
        True,
        "Canonical structure needs near-continuous hourly prices.",
        (
            "Frozen V1 availability gate retained because availability remains "
            "economically meaningful."
        ),
    ),
    ApprovalGate(
        "reference_unavailable_rate",
        "0.005",
        "maximum",
        True,
        "Unavailable reference hours must remain rare and explicit.",
        "Complement of the frozen 99.5% V1 usable-rate gate.",
    ),
    ApprovalGate(
        "reference_degraded_rate",
        "0.020",
        "maximum",
        False,
        "Track warning frequency without rejecting economically harmless warnings alone.",
        "BTC-019B observed 1.0873% degraded hours with zero material episodes.",
    ),
    ApprovalGate(
        "venue_disagreement_rate",
        "0.005",
        "maximum",
        False,
        "Frequent severe disagreement may indicate an unstable provider set.",
        "BTC-019B observed 0.0114%; threshold is diagnostic, not a sole rejection gate.",
    ),
    ApprovalGate(
        "unrecorded_quality_state_count",
        0,
        "equal",
        True,
        "Every warning and unavailable observation must be reconstructable.",
        "Protocol provenance requirement.",
    ),
    ApprovalGate(
        "daily_bucket_usable_rate",
        "0.995",
        "minimum",
        True,
        "Daily features require nearly continuous explicit period state.",
        "Aligned with the hourly usable-rate floor.",
    ),
    ApprovalGate(
        "weekly_bucket_usable_rate",
        "0.990",
        "minimum",
        True,
        "Structural models must not lose meaningful weekly history.",
        "Economic requirement following the two omitted V1 weeks found by BTC-019B.",
    ),
    ApprovalGate(
        "silent_incomplete_bucket_omission_count",
        0,
        "equal",
        True,
        "Incomplete periods must remain visible as metadata records.",
        "Direct BTC-019B failure mechanism.",
    ),
    ApprovalGate(
        "atr_median_absolute_fractional_difference",
        "0.02",
        "maximum",
        True,
        "Typical volatility estimates should remain close to cross-venue consensus.",
        "Frozen V1 ATR median gate.",
    ),
    ApprovalGate(
        "atr_p95_absolute_fractional_difference",
        "0.10",
        "maximum",
        True,
        "Tail ATR distortion must remain bounded.",
        "Frozen V1 ATR p95 gate.",
    ),
    ApprovalGate(
        "exact_timestamp_swing_disagreement_rate",
        "0.15",
        "maximum",
        False,
        "Retain exact-label sensitivity without making it the sole structural gate.",
        "BTC-019B observed 12.1212% caused by two adjacent-week shifts.",
    ),
    ApprovalGate(
        "within_1_week_swing_disagreement_rate",
        "0.05",
        "maximum",
        True,
        "Weekly structures should match after allowing one label week of tolerance.",
        "BTC-019B diagnostic rate was zero; 5% allows sparse unexplained events.",
    ),
    ApprovalGate(
        "within_2_week_swing_disagreement_rate",
        "0.02",
        "maximum",
        True,
        "Two-week unmatched structures indicate more than label timing noise.",
        "BTC-019B diagnostic rate was zero; stricter 2% tail allowance.",
    ),
    ApprovalGate(
        "swing_level_disagreement_rate_above_0_50_atr",
        "0.05",
        "maximum",
        True,
        "Half an ATR is the primary economically meaningful structural level tolerance.",
        "Predeclared from BTC-019B grid and existing ATR-normalized structural logic.",
    ),
    ApprovalGate(
        "structural_state_disagreement_rate",
        "0.05",
        "maximum",
        True,
        "Reference choice should rarely change support/resistance state.",
        "BTC-019B separated structural effects from exact timestamp labels.",
    ),
    ApprovalGate(
        "breakout_disagreement_rate",
        "0.05",
        "maximum",
        True,
        "Breakout eligibility must be stable across robust references.",
        "Economic reasoning using existing deterministic breakout logic.",
    ),
    ApprovalGate(
        "reclaim_disagreement_rate",
        "0.05",
        "maximum",
        True,
        "Reclaim eligibility must be stable across robust references.",
        "Economic reasoning using existing deterministic reclaim logic.",
    ),
    ApprovalGate(
        "stop_touch_disagreement_rate",
        "0.01",
        "maximum",
        True,
        "Canonical source choice should almost never change stop outcomes.",
        "Frozen V1 stop gate.",
    ),
    ApprovalGate(
        "cross_market_confirmed_stop_preservation_rate",
        "1.0",
        "minimum",
        True,
        "A robust estimator must preserve genuine shared tail moves.",
        "Known-event requirement and BTC-019B stop analysis.",
    ),
    ApprovalGate(
        "isolated_venue_stop_suppression_rate",
        "0.95",
        "minimum",
        True,
        "Most isolated exchange wicks should not create canonical stop events.",
        "Three known isolated V1 events were suppressed; 95% avoids event-specific perfection.",
    ),
    ApprovalGate(
        "gap_through_stop_consensus_agreement_rate",
        "0.99",
        "minimum",
        True,
        "Gap-through behavior must agree with deterministic venue consensus.",
        "Stop-risk economic requirement.",
    ),
    ApprovalGate(
        "mfe_median_absolute_difference",
        "0.0025",
        "maximum",
        True,
        "Typical favorable excursion distortion should remain below 25 bps.",
        "BTC-019B and V1 observed zero median difference.",
    ),
    ApprovalGate(
        "mfe_p95_absolute_difference",
        "0.01",
        "maximum",
        True,
        "95% of path probes should remain within one percentage point.",
        "Existing BTC-019 material-path threshold.",
    ),
    ApprovalGate(
        "mfe_max_absolute_difference",
        "0.05",
        "maximum",
        False,
        "Expose extreme path sensitivity without letting one event decide alone.",
        "Robustness diagnostic chosen before sealed validation.",
    ),
    ApprovalGate(
        "mae_median_absolute_difference",
        "0.0025",
        "maximum",
        True,
        "Typical adverse excursion distortion should remain below 25 bps.",
        "BTC-019B and V1 observed zero median difference.",
    ),
    ApprovalGate(
        "mae_p95_absolute_difference",
        "0.01",
        "maximum",
        True,
        "95% of adverse paths should remain within one percentage point.",
        "Existing BTC-019 material-path threshold.",
    ),
    ApprovalGate(
        "mae_max_absolute_difference",
        "0.05",
        "maximum",
        False,
        "Expose extreme adverse-path sensitivity without post-hoc tuning.",
        "Robustness diagnostic chosen before sealed validation.",
    ),
    ApprovalGate(
        "trade_eligibility_disagreement_rate",
        "0.01",
        "maximum",
        True,
        "Reference policy should rarely change whether a trade is permitted.",
        "Reserved Phase-1 strategy consequence gate.",
    ),
    ApprovalGate(
        "trade_action_disagreement_rate",
        "0.01",
        "maximum",
        True,
        "ENTER/HOLD/ADD/TRIM/EXIT decisions should be stable.",
        "Reserved Phase-1 strategy consequence gate.",
    ),
    ApprovalGate(
        "risk_size_p95_relative_difference",
        "0.10",
        "maximum",
        True,
        "Reference changes should not materially resize most positions.",
        "Reserved Phase-1 risk consequence gate.",
    ),
    ApprovalGate(
        "regime_classification_disagreement_rate",
        "0.02",
        "maximum",
        True,
        "Regime labels should be robust to reference construction.",
        "Reserved Phase-1 strategy consequence gate.",
    ),
    ApprovalGate(
        "setup_classification_disagreement_rate",
        "0.01",
        "maximum",
        True,
        "Setup selection should rarely depend on venue noise.",
        "Reserved Phase-1 strategy consequence gate.",
    ),
    ApprovalGate(
        "point_in_time_violation_count",
        0,
        "equal",
        True,
        "Future or late observations invalidate the study.",
        "Non-negotiable point-in-time correctness requirement.",
    ),
    ApprovalGate(
        "provenance_complete_rate",
        "1.0",
        "minimum",
        True,
        "Every output must be reconstructable from immutable inputs.",
        "Non-negotiable auditability requirement.",
    ),
    ApprovalGate(
        "deterministic_rerun_hash_match",
        True,
        "equal",
        True,
        "Identical inputs and protocol must produce identical artifacts.",
        "Non-negotiable reproducibility requirement.",
    ),
    ApprovalGate(
        "raw_observation_mutation_count",
        0,
        "equal",
        True,
        "Research may not rewrite source evidence.",
        "Existing BTC-019 and V1 governance.",
    ),
    ApprovalGate(
        "historical_fallback_splice_count",
        0,
        "equal",
        True,
        "Unversioned fallback splicing would invalidate provenance.",
        "Existing PRICE_SOURCE_POLICY_V1 governance.",
    ),
    ApprovalGate(
        "live_shadow_days",
        90,
        "minimum",
        True,
        "Historical APIs cannot reconstruct original publication latency.",
        "Prospective promotion requirement.",
        validation_stage="promotion",
    ),
)


@dataclass(frozen=True)
class V2ProviderProvenance:
    observation_id: str
    provider: str
    exchange: str
    symbol: str
    timeframe: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    available_at: datetime

    @classmethod
    def from_input(cls, value: ProviderCandleInput) -> "V2ProviderProvenance":
        value.as_record()
        return cls(
            observation_id=value.observation_id,
            provider=value.bar.provider,
            exchange=value.bar.exchange,
            symbol=value.bar.symbol,
            timeframe=value.bar.timeframe,
            open=value.bar.open,
            high=value.bar.high,
            low=value.bar.low,
            close=value.bar.close,
            available_at=value.available_at,
        )

    def as_record(self) -> dict[str, Any]:
        if self.provider not in REQUIRED_COMPOSITE_PROVIDER_IDS:
            raise ValueError("provider is not part of the frozen V2 set")
        if self.exchange != V2_PROVIDER_EXCHANGES[self.provider]:
            raise ValueError("provider exchange does not match the frozen V2 instrument")
        if self.symbol != V2_PROVIDER_NORMALIZED_SYMBOLS[self.provider]:
            raise ValueError("provider symbol does not match the frozen V2 instrument")
        if self.timeframe != "1h":
            raise ValueError("V2 provenance requires 1h provider candles")
        _validate_candle(self.open, self.high, self.low, self.close)
        return {
            "observation_id": self.observation_id,
            "provider": self.provider,
            "exchange": self.exchange,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "open": str(self.open),
            "high": str(self.high),
            "low": str(self.low),
            "close": str(self.close),
            "available_at": require_utc_datetime(
                self.available_at, "provider available_at"
            ).isoformat(),
        }


@dataclass(frozen=True)
class V2ReferenceObservation:
    reference_policy_version: str
    method_version: str
    observation_time: datetime
    decision_time: datetime
    available_at: datetime
    providers_expected: tuple[str, ...]
    providers_available: tuple[str, ...]
    provider_inputs: tuple[V2ProviderProvenance, ...]
    input_count: int
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal | None
    reference_price_available: bool
    quality_state: str
    confirmation_state: str
    diagnostics: CompositeDiagnostics
    fallback_used: bool
    reason_codes: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        timestamp = require_utc_datetime(self.observation_time, "observation_time")
        decision = require_utc_datetime(self.decision_time, "decision_time")
        available = require_utc_datetime(self.available_at, "available_at")
        if self.reference_policy_version != V2_PROTOCOL_VERSION:
            raise ValueError("unexpected V2 reference policy version")
        if self.method_version != V2_METHOD_VERSION:
            raise ValueError("unexpected V2 method version")
        if decision != timestamp + timedelta(hours=1) + DEFAULT_DECISION_DELAY:
            raise ValueError("V2 decision time must be bar close plus five minutes")
        if available != decision:
            raise ValueError("V2 available_at must equal the fixed decision time")
        if self.providers_expected != REQUIRED_COMPOSITE_PROVIDER_IDS:
            raise ValueError("V2 provider set is frozen")
        if self.input_count != len(self.providers_available):
            raise ValueError("input_count must match providers_available")
        if tuple(item.provider for item in self.provider_inputs) != self.providers_available:
            raise ValueError("provider provenance must match providers_available order")
        for item in self.provider_inputs:
            item.as_record()
            if item.available_at > decision:
                raise ValueError("late provider leaked into V2 provenance")
        values = (self.open, self.high, self.low, self.close)
        if self.reference_price_available:
            if self.quality_state not in (
                REFERENCE_OK,
                REFERENCE_DEGRADED,
                VENUE_DISAGREEMENT,
            ):
                raise ValueError("available V2 price has an invalid quality state")
            _validate_candle(*values)
        else:
            if self.quality_state != REFERENCE_UNAVAILABLE:
                raise ValueError("unavailable V2 price must use REFERENCE_UNAVAILABLE")
            if any(value is not None for value in values):
                raise ValueError("unavailable V2 reference must not publish OHLC")
        if self.fallback_used:
            raise ValueError("historical fallback splicing is prohibited")
        return {
            "reference_policy_version": self.reference_policy_version,
            "method_version": self.method_version,
            "observation_time": timestamp.isoformat(),
            "decision_time": decision.isoformat(),
            "available_at": available.isoformat(),
            "providers_expected": list(self.providers_expected),
            "providers_available": list(self.providers_available),
            "provider_observation_ids": {
                item.provider: item.observation_id for item in self.provider_inputs
            },
            "provider_ohlc": {
                item.provider: {
                    "open": str(item.open),
                    "high": str(item.high),
                    "low": str(item.low),
                    "close": str(item.close),
                }
                for item in self.provider_inputs
            },
            "provider_available_at": {
                item.provider: item.available_at.isoformat()
                for item in self.provider_inputs
            },
            "provider_inputs": [item.as_record() for item in self.provider_inputs],
            "input_count": self.input_count,
            "composite_ohlc": (
                {
                    "open": str(self.open),
                    "high": str(self.high),
                    "low": str(self.low),
                    "close": str(self.close),
                }
                if self.reference_price_available
                else None
            ),
            "reference_price_available": self.reference_price_available,
            "quality_state": self.quality_state,
            "confirmation_state": self.confirmation_state,
            "close_dispersion_bps": _optional_decimal(
                self.diagnostics.close_dispersion_bps
            ),
            "high_dispersion_atr": _optional_decimal(
                self.diagnostics.high_dispersion_atr
            ),
            "low_dispersion_atr": _optional_decimal(
                self.diagnostics.low_dispersion_atr
            ),
            "range_dispersion_atr": _optional_decimal(
                self.diagnostics.range_dispersion_atr
            ),
            "fallback_used": self.fallback_used,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class V2HigherTimeframeReference:
    reference_policy_version: str
    method_version: str
    timeframe: str
    bucket_start: datetime
    bucket_end: datetime
    decision_time: datetime
    available_at: datetime
    expected_bar_count: int
    source_observation_count: int
    observed_bar_count: int
    missing_bar_count: int
    degraded_bar_count: int
    venue_disagreement_bar_count: int
    unavailable_bar_count: int
    quality_state: str
    bucket_status: str
    bucket_complete: bool
    bucket_usable: bool
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal | None
    source_observation_times: tuple[datetime, ...]
    missing_observation_times: tuple[datetime, ...]
    reason_codes: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        start = require_utc_datetime(self.bucket_start, "bucket_start")
        end = require_utc_datetime(self.bucket_end, "bucket_end")
        decision = require_utc_datetime(self.decision_time, "decision_time")
        available = require_utc_datetime(self.available_at, "available_at")
        if self.reference_policy_version != V2_PROTOCOL_VERSION:
            raise ValueError("higher-timeframe V2 policy mismatch")
        if self.method_version != V2_METHOD_VERSION:
            raise ValueError("higher-timeframe V2 method mismatch")
        if self.timeframe not in ("1d", "1w"):
            raise ValueError("V2 quality aggregation supports daily and weekly buckets")
        if decision != end + DEFAULT_DECISION_DELAY or available != decision:
            raise ValueError("bucket availability must be period end plus five minutes")
        if self.expected_bar_count not in (24, 168):
            raise ValueError("unexpected V2 higher-timeframe source count")
        if self.source_observation_count != len(self.source_observation_times):
            raise ValueError("source count must match source observation timestamps")
        if len(set(self.source_observation_times)) != self.source_observation_count:
            raise ValueError("source observation timestamps must be unique")
        if self.missing_bar_count != len(self.missing_observation_times):
            raise ValueError("missing count must match missing observation timestamps")
        if self.observed_bar_count + self.missing_bar_count != self.expected_bar_count:
            raise ValueError("observed and missing counts must cover the bucket")
        if self.bucket_complete != (self.missing_bar_count == 0):
            raise ValueError("bucket_complete does not match missing count")
        if self.bucket_usable != self.bucket_complete:
            raise ValueError("frozen V2 does not approve partial-bucket OHLC")
        if self.bucket_status not in V2_BUCKET_STATUSES:
            raise ValueError("unknown V2 bucket status")
        if self.bucket_usable:
            expected_status = {
                REFERENCE_OK: BUCKET_COMPLETE_OK,
                REFERENCE_DEGRADED: BUCKET_COMPLETE_DEGRADED,
                VENUE_DISAGREEMENT: BUCKET_COMPLETE_VENUE_DISAGREEMENT,
            }.get(self.quality_state)
            if self.bucket_status != expected_status:
                raise ValueError("usable bucket status does not match quality state")
        elif (
            self.quality_state != REFERENCE_UNAVAILABLE
            or self.bucket_status != BUCKET_INCOMPLETE_UNUSABLE
        ):
            raise ValueError("unusable bucket must retain explicit unavailable state")
        values = (self.open, self.high, self.low, self.close)
        if self.bucket_usable:
            _validate_candle(*values)
        elif any(value is not None for value in values):
            raise ValueError("unusable incomplete buckets must not publish partial OHLC")
        return {
            "reference_policy_version": self.reference_policy_version,
            "method_version": self.method_version,
            "timeframe": self.timeframe,
            "bucket_start": start.isoformat(),
            "bucket_end": end.isoformat(),
            "decision_time": decision.isoformat(),
            "available_at": available.isoformat(),
            "expected_bar_count": self.expected_bar_count,
            "source_observation_count": self.source_observation_count,
            "observed_bar_count": self.observed_bar_count,
            "missing_bar_count": self.missing_bar_count,
            "degraded_bar_count": self.degraded_bar_count,
            "venue_disagreement_bar_count": self.venue_disagreement_bar_count,
            "unavailable_bar_count": self.unavailable_bar_count,
            "quality_state": self.quality_state,
            "bucket_status": self.bucket_status,
            "bucket_complete": self.bucket_complete,
            "bucket_usable": self.bucket_usable,
            "composite_ohlc": (
                {
                    "open": str(self.open),
                    "high": str(self.high),
                    "low": str(self.low),
                    "close": str(self.close),
                }
                if self.bucket_usable
                else None
            ),
            "source_observation_times": [
                item.isoformat() for item in self.source_observation_times
            ],
            "missing_observation_times": [
                item.isoformat() for item in self.missing_observation_times
            ],
            "reason_codes": list(self.reason_codes),
        }


def build_v2_reference_observation(
    inputs: Sequence[ProviderCandleInput],
    *,
    observation_time: datetime,
    decision_time: datetime,
    trailing_atr: Decimal | None,
) -> V2ReferenceObservation:
    """Build one research-only V2 reference without waiting past the cutoff."""

    timestamp = require_utc_datetime(observation_time, "observation_time")
    decision = require_utc_datetime(decision_time, "decision_time")
    expected_decision = timestamp + timedelta(hours=1) + DEFAULT_DECISION_DELAY
    if decision != expected_decision:
        raise ValueError("decision_time must equal bar close plus five minutes")
    supplied: dict[str, ProviderCandleInput] = {}
    late = []
    for item in inputs:
        item.as_record()
        if item.bar.timestamp != timestamp:
            raise ValueError("all provider inputs must match observation_time")
        if item.bar.provider in supplied:
            raise ValueError("provider inputs must be unique")
        if item.available_at <= decision:
            supplied[item.bar.provider] = item
        else:
            late.append(item.bar.provider)
    providers = tuple(
        provider_id
        for provider_id in REQUIRED_COMPOSITE_PROVIDER_IDS
        if provider_id in supplied
    )
    available = tuple(supplied[provider_id] for provider_id in providers)
    bars = tuple(item.bar for item in available)
    diagnostics = _diagnostics(bars, trailing_atr=trailing_atr)
    reasons = ["V2_PROVIDER_LATE" for _ in late]
    quality_state, confirmation_state = _v2_quality_state(
        bars,
        diagnostics=diagnostics,
        trailing_atr=trailing_atr,
        reason_codes=reasons,
    )
    reference_price_available = quality_state != REFERENCE_UNAVAILABLE
    ohlc: tuple[Decimal | None, Decimal | None, Decimal | None, Decimal | None]
    if reference_price_available:
        ohlc = tuple(
            _median(tuple(getattr(bar, field) for bar in bars))
            for field in ("open", "high", "low", "close")
        )
        try:
            _validate_candle(*ohlc)
        except ValueError:
            quality_state = REFERENCE_UNAVAILABLE
            confirmation_state = UNRESOLVED_PROVIDER_DISAGREEMENT
            reference_price_available = False
            reasons.append("V2_CANDLE_INVARIANT_FAILED")
            ohlc = (None, None, None, None)
    else:
        ohlc = (None, None, None, None)
    result = V2ReferenceObservation(
        reference_policy_version=V2_PROTOCOL_VERSION,
        method_version=V2_METHOD_VERSION,
        observation_time=timestamp,
        decision_time=decision,
        available_at=decision,
        providers_expected=REQUIRED_COMPOSITE_PROVIDER_IDS,
        providers_available=providers,
        provider_inputs=tuple(V2ProviderProvenance.from_input(item) for item in available),
        input_count=len(available),
        open=ohlc[0],
        high=ohlc[1],
        low=ohlc[2],
        close=ohlc[3],
        reference_price_available=reference_price_available,
        quality_state=quality_state,
        confirmation_state=confirmation_state,
        diagnostics=diagnostics,
        fallback_used=False,
        reason_codes=tuple(dict.fromkeys(reasons)),
    )
    result.as_record()
    return result


def aggregate_v2_reference_bucket(
    observations: Sequence[V2ReferenceObservation],
    *,
    bucket_start: datetime,
    timeframe: str,
) -> V2HigherTimeframeReference:
    """Aggregate a daily/weekly V2 bucket while preserving incomplete state."""

    start = require_utc_datetime(bucket_start, "bucket_start")
    if timeframe == "1d":
        if start.hour or start.minute or start.second or start.microsecond:
            raise ValueError("daily V2 bucket must start at 00:00 UTC")
        end = start + timedelta(days=1)
        expected_count = 24
    elif timeframe == "1w":
        if start.weekday() != 0 or start.hour or start.minute or start.second or start.microsecond:
            raise ValueError("weekly V2 bucket must start Monday 00:00 UTC")
        end = start + timedelta(weeks=1)
        expected_count = 168
    else:
        raise ValueError("V2 quality aggregation supports timeframe 1d or 1w")
    expected_timestamps = tuple(
        start + timedelta(hours=offset) for offset in range(expected_count)
    )
    expected_timestamp_set = set(expected_timestamps)
    by_timestamp = {}
    for observation in observations:
        observation.as_record()
        timestamp = observation.observation_time
        if not start <= timestamp < end:
            raise ValueError("source observation is outside the requested bucket")
        if timestamp not in expected_timestamp_set:
            raise ValueError("source observation must align to an hourly bucket boundary")
        if timestamp in by_timestamp:
            raise ValueError("source observations must have unique timestamps")
        by_timestamp[timestamp] = observation
    available = tuple(
        by_timestamp[timestamp]
        for timestamp in expected_timestamps
        if timestamp in by_timestamp and by_timestamp[timestamp].reference_price_available
    )
    missing = tuple(
        timestamp
        for timestamp in expected_timestamps
        if timestamp not in by_timestamp
        or not by_timestamp[timestamp].reference_price_available
    )
    degraded_count = sum(
        item.quality_state == REFERENCE_DEGRADED for item in by_timestamp.values()
    )
    disagreement_count = sum(
        item.quality_state == VENUE_DISAGREEMENT for item in by_timestamp.values()
    )
    unavailable_count = sum(
        item.quality_state == REFERENCE_UNAVAILABLE for item in by_timestamp.values()
    ) + (expected_count - len(by_timestamp))
    complete = not missing
    reasons = []
    if not complete:
        quality_state = REFERENCE_UNAVAILABLE
        bucket_status = BUCKET_INCOMPLETE_UNUSABLE
        reasons.append("V2_INCOMPLETE_BUCKET")
        ohlc = (None, None, None, None)
    else:
        ohlc = (
            available[0].open,
            max(item.high for item in available),
            min(item.low for item in available),
            available[-1].close,
        )
        if disagreement_count:
            quality_state = VENUE_DISAGREEMENT
            bucket_status = BUCKET_COMPLETE_VENUE_DISAGREEMENT
            reasons.append("V2_BUCKET_CONTAINS_VENUE_DISAGREEMENT")
        elif degraded_count:
            quality_state = REFERENCE_DEGRADED
            bucket_status = BUCKET_COMPLETE_DEGRADED
            reasons.append("V2_BUCKET_CONTAINS_DEGRADED_HOURS")
        else:
            quality_state = REFERENCE_OK
            bucket_status = BUCKET_COMPLETE_OK
    result = V2HigherTimeframeReference(
        reference_policy_version=V2_PROTOCOL_VERSION,
        method_version=V2_METHOD_VERSION,
        timeframe=timeframe,
        bucket_start=start,
        bucket_end=end,
        decision_time=end + DEFAULT_DECISION_DELAY,
        available_at=end + DEFAULT_DECISION_DELAY,
        expected_bar_count=expected_count,
        source_observation_count=len(by_timestamp),
        observed_bar_count=len(available),
        missing_bar_count=len(missing),
        degraded_bar_count=degraded_count,
        venue_disagreement_bar_count=disagreement_count,
        unavailable_bar_count=unavailable_count,
        quality_state=quality_state,
        bucket_status=bucket_status,
        bucket_complete=complete,
        bucket_usable=complete,
        open=ohlc[0],
        high=ohlc[1],
        low=ohlc[2],
        close=ohlc[3],
        source_observation_times=tuple(sorted(by_timestamp)),
        missing_observation_times=missing,
        reason_codes=tuple(reasons),
    )
    result.as_record()
    return result


def guard_untouched_validation_sample(
    *,
    start: datetime,
    end: datetime,
    purpose: str,
) -> None:
    """Reject every current research request overlapping the sealed OOS sample."""

    window_start = require_utc_datetime(start, "start")
    window_end = require_utc_datetime(end, "end")
    if window_end < window_start:
        raise ValueError("end must be >= start")
    if window_start <= UNTOUCHED_OOS_END and window_end >= UNTOUCHED_OOS_START:
        raise UntouchedValidationSampleGuardError(
            f"{purpose!r} overlaps sealed BTC_REFERENCE_COMPOSITE_V2 validation "
            "history; a future dedicated validator bound to the frozen definition "
            "hash is required to open it"
        )


def v2_protocol_definition_payload() -> dict[str, Any]:
    """Return the deterministic hash input for the frozen V2 protocol."""

    gates = [item.as_record() for item in V2_APPROVAL_GATES]
    return {
        "schema_version": "BTC_REFERENCE_COMPOSITE_V2_PROTOCOL_DEFINITION_V1",
        "reference_policy_version": V2_PROTOCOL_VERSION,
        "status": V2_PROTOCOL_STATUS,
        "research_only": True,
        "production_promotion_authorized": False,
        "hypothesis": (
            "Keep robust median OHLC as the reference-price estimator while "
            "separating price availability from reference-quality state."
        ),
        "method": {
            "name": V2_METHOD,
            "version": V2_METHOD_VERSION,
            "formula": V2_FORMULA,
            "open": "median(available provider opens)",
            "high": "median(available provider highs)",
            "low": "median(available provider lows)",
            "close": "median(available provider closes)",
            "volume": "not_composited_provider_specific_only",
            "candle_invariants": [
                "high >= max(open, close)",
                "low <= min(open, close)",
                "high >= low",
                "all prices > 0",
            ],
        },
        "providers": {
            "required": list(REQUIRED_COMPOSITE_PROVIDER_IDS),
            "instruments": {
                provider_id: {
                    "exchange": V2_PROVIDER_EXCHANGES[provider_id],
                    "normalized_symbol": V2_PROVIDER_NORMALIZED_SYMBOLS[provider_id],
                    "api_symbol": V2_PROVIDER_API_SYMBOLS[provider_id],
                }
                for provider_id in REQUIRED_COMPOSITE_PROVIDER_IDS
            },
            "minimum_provider_count": V2_MINIMUM_PROVIDER_COUNT,
            "historical_splicing_allowed": False,
            "single_venue_fallback_allowed": False,
        },
        "quality_thresholds": {
            "close_agreement_bps": str(DEFAULT_CLOSE_DISAGREEMENT_BPS),
            "high_low_or_range_disagreement_atr": str(
                DEFAULT_TWO_PROVIDER_RANGE_DISAGREEMENT_ATR
            ),
            "atr_window_days": V2_ATR_WINDOW_DAYS,
            "threshold_source": (
                "frozen V1 close and two-provider ATR thresholds; V2 applies the "
                "ATR threshold to explicit three-provider range disagreement too"
            ),
        },
        "quality_state_semantics": {
            "three_providers": {
                "full_close_agreement": {
                    "publish": True,
                    "quality_state": REFERENCE_OK,
                },
                "full_close_agreement_with_range_disagreement": {
                    "publish": True,
                    "quality_state": VENUE_DISAGREEMENT,
                    "meaning": (
                        "close consensus exists but a high, low, or total-range "
                        "dispersion exceeds the frozen ATR threshold"
                    ),
                },
                "two_of_three_close_consensus": {
                    "publish": True,
                    "quality_state": REFERENCE_DEGRADED,
                },
                "no_close_consensus": {
                    "publish": True,
                    "quality_state": VENUE_DISAGREEMENT,
                    "meaning": "price exists but confidence and venue agreement are poor",
                },
            },
            "two_providers": {
                "agreement_checks_pass": {
                    "publish": True,
                    "quality_state": REFERENCE_DEGRADED,
                },
                "agreement_checks_fail": {
                    "publish": False,
                    "quality_state": REFERENCE_UNAVAILABLE,
                },
                "prior_atr_unavailable": {
                    "publish": False,
                    "quality_state": REFERENCE_UNAVAILABLE,
                },
            },
            "one_provider": {"publish": False, "quality_state": REFERENCE_UNAVAILABLE},
            "zero_providers": {"publish": False, "quality_state": REFERENCE_UNAVAILABLE},
            "entry_permission_separate": True,
            "strategy_policy_reserved": {
                REFERENCE_OK: "normal operation candidate",
                REFERENCE_DEGRADED: "reference usable; entry/add policy evaluated later",
                VENUE_DISAGREEMENT: "reference usable; hard entry/add veto candidate",
                REFERENCE_UNAVAILABLE: "DATA_QUALITY_FAIL candidate",
            },
        },
        "higher_timeframe_aggregation": {
            "timeframes": ["1d", "1w"],
            "required_metadata": [
                "expected_bar_count",
                "observed_bar_count",
                "missing_bar_count",
                "degraded_bar_count",
                "venue_disagreement_bar_count",
                "unavailable_bar_count",
                "quality_state",
                "bucket_complete",
                "bucket_usable",
            ],
            "complete_ok": "publish OHLC and BUCKET_COMPLETE_OK",
            "complete_degraded": "publish OHLC and preserve degraded count",
            "complete_venue_disagreement": (
                "publish OHLC and preserve venue-disagreement count"
            ),
            "incomplete": (
                "persist bucket metadata with null OHLC, bucket_complete=false, "
                "bucket_usable=false, and REFERENCE_UNAVAILABLE"
            ),
            "partial_bucket_ohlc_approved": False,
            "silent_bucket_omission_allowed": False,
        },
        "point_in_time": {
            "hourly_decision_time": "observation_time + 1 hour + 5 minutes",
            "provider_inclusion": "provider.available_at <= composite decision_time",
            "composite_available_at": "fixed composite decision_time",
            "quality_atr": "prior completed daily ATR only",
            "wait_for_late_provider": False,
        },
        "provenance_schema": [
            "reference_policy_version",
            "method_version",
            "observation_time",
            "decision_time",
            "available_at",
            "providers_expected",
            "providers_available",
            "provider observation IDs",
            "provider OHLC values",
            "provider available_at values",
            "input_count",
            "composite OHLC",
            "reference_price_available",
            "quality_state",
            "confirmation_state",
            "close_dispersion_bps",
            "high_dispersion_atr",
            "low_dispersion_atr",
            "range_dispersion_atr",
            "fallback_used",
            "reason_codes",
        ],
        "validation_metric_families": {
            "availability_quality": [
                "reference_usable_rate",
                "REFERENCE_OK rate",
                "REFERENCE_DEGRADED rate",
                "VENUE_DISAGREEMENT rate",
                "REFERENCE_UNAVAILABLE rate",
                "degraded episode count",
                "unavailable episode count",
                "venue-disagreement episode count",
                "higher-timeframe incomplete-bucket count",
            ],
            "quality_economic_materiality": [
                "structural-state difference",
                "breakout difference",
                "reclaim difference",
                "stop difference",
                "MFE difference",
                "MAE difference",
                "trade eligibility difference",
                "risk difference",
            ],
            "swings": [
                "exact timestamp disagreement",
                "+/-1 week matched disagreement",
                "+/-2 week matched disagreement",
                "ATR-normalized level disagreement",
                "structural-state disagreement",
                "breakout disagreement",
                "reclaim disagreement",
                "stop-impact disagreement",
                "trade/risk-material disagreement",
            ],
            "stops": [
                "stop-touch disagreement rate",
                "cross-market confirmed stop preservation",
                "isolated-venue stop suppression",
                "gap-through-stop behavior",
                "structural invalidation differences",
            ],
            "path": [
                "median absolute MFE difference",
                "p95 MFE difference",
                "max MFE difference",
                "median absolute MAE difference",
                "p95 MAE difference",
                "max MAE difference",
            ],
        },
        "atr_materiality": {
            "grid": [str(value) for value in V2_ATR_MATERIALITY_GRID],
            "primary_threshold": str(V2_PRIMARY_ATR_MATERIALITY_THRESHOLD),
            "selection_rationale": (
                "Half an ATR distinguishes economically meaningful level movement "
                "while the complete grid prevents post-hoc threshold selection."
            ),
        },
        "approval_gates": gates,
        "future_strategy_consequence_metrics": [
            "Trend Score",
            "flow-independent price features",
            "Volatility Score",
            "Structure Score",
            "Regime",
            "setup classification",
            "Entry Conviction",
            "hard vetoes",
            "entry zone",
            "structural stop",
            "R/R",
            "initial position sizing",
            "Hold Score",
            "Add Score",
            "trailing stop",
            "paper-trade outcome",
        ],
        "comparison_series": [
            "Bitstamp-only",
            "Coinbase-only",
            "Bitfinex-only",
            "MEDIAN_OHLC_V1 historical formula",
            V2_PROTOCOL_VERSION,
        ],
        "untouched_validation_sample": {
            "start": UNTOUCHED_OOS_START.isoformat(),
            "end": UNTOUCHED_OOS_END.isoformat(),
            "status": list(UNTOUCHED_OOS_STATUS),
            "known_metadata_only": "provider availability boundaries",
            "guard": (
                "all overlapping exploratory access raises until a future "
                "dedicated validator exists"
            ),
        },
        "live_shadow": {
            "required_for_promotion": True,
            "minimum_days": 90,
            "reason": "historical APIs do not reconstruct publication latency perfectly",
        },
        "governance": {
            "btc019_status": "IN PROGRESS",
            "btc_reference_composite_v1": "RESEARCH_INCONCLUSIVE",
            "price_source_policy_v1": "UNCHANGED",
            "production_canonical_reference": "UNRESOLVED",
            "material_change_requires": "BTC_REFERENCE_COMPOSITE_V3 or later",
            "validation_not_performed": True,
            "normal_phase_1_development_may_resume_after_freeze": True,
        },
        "prohibited_actions": [
            "bulk collect the sealed 2015-2019 sample",
            "inspect sealed-sample composite outcomes",
            "tune thresholds using sealed-sample data",
            "mutate raw provider observations",
            "historically splice a fallback provider",
            "silently omit incomplete higher-timeframe buckets",
            "promote a production canonical source in BTC-019C",
            "modify PRICE_SOURCE_POLICY_V1",
        ],
        "frozen_dependency_artifacts": {
            "BTC-019": EXPECTED_BTC019_ARTIFACT_SHA256,
            "BTC_REFERENCE_COMPOSITE_V1": EXPECTED_V1_ARTIFACT_SHA256,
            "BTC-019B": EXPECTED_BTC019B_ARTIFACT_SHA256,
        },
    }


def v2_definition_sha256(payload: Mapping[str, Any] | None = None) -> str:
    value = dict(payload or v2_protocol_definition_payload())
    value.pop("definition_sha256", None)
    return hashlib.sha256(_canonical_json(value).encode("ascii")).hexdigest()


def frozen_v2_protocol_definition() -> dict[str, Any]:
    payload = v2_protocol_definition_payload()
    digest = v2_definition_sha256(payload)
    if FROZEN_V2_DEFINITION_SHA256 and digest != FROZEN_V2_DEFINITION_SHA256:
        raise ValueError("BTC_REFERENCE_COMPOSITE_V2 definition hash mismatch")
    return {**payload, "definition_sha256": digest}


def verify_frozen_dependency_artifacts(repository_root: Path) -> None:
    groups = (
        (
            repository_root / "research_artifacts/btc019/PRICE_SOURCE_POLICY_V1",
            EXPECTED_BTC019_ARTIFACT_SHA256,
        ),
        (
            repository_root
            / "research_artifacts/btc_reference_composite/BTC_REFERENCE_COMPOSITE_V1",
            EXPECTED_V1_ARTIFACT_SHA256,
        ),
        (
            repository_root / "research_artifacts/btc019b",
            EXPECTED_BTC019B_ARTIFACT_SHA256,
        ),
    )
    for directory, expected in groups:
        actual = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.iterdir())
            if path.is_file()
        }
        if actual != expected:
            raise ValueError(f"frozen dependency artifact mismatch: {directory}")


def verify_frozen_v2_protocol_artifacts(output_dir: Path) -> None:
    actual = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(output_dir.iterdir())
        if path.is_file()
    }
    if actual != EXPECTED_V2_PROTOCOL_ARTIFACT_SHA256:
        raise ValueError(f"frozen V2 protocol artifact mismatch: {output_dir}")


def write_frozen_v2_protocol_artifacts(output_dir: Path) -> None:
    """Persist only the immutable V2 definition and governance report."""

    output_dir.mkdir(parents=True, exist_ok=False)
    definition = frozen_v2_protocol_definition()
    (output_dir / "protocol_definition.json").write_text(
        json.dumps(definition, indent=2, sort_keys=True) + "\n",
        encoding="ascii",
    )
    (output_dir / "protocol_report.md").write_text(
        _protocol_markdown(definition),
        encoding="ascii",
    )
    verify_frozen_v2_protocol_artifacts(output_dir)


def _v2_quality_state(
    bars: Sequence[Any],
    *,
    diagnostics: CompositeDiagnostics,
    trailing_atr: Decimal | None,
    reason_codes: list[str],
) -> tuple[str, str]:
    count = len(bars)
    if count < V2_MINIMUM_PROVIDER_COUNT:
        reason_codes.append("V2_INPUT_COUNT_INSUFFICIENT")
        return (
            REFERENCE_UNAVAILABLE,
            SINGLE_PROVIDER_OBSERVATION
            if count == 1
            else UNRESOLVED_PROVIDER_DISAGREEMENT,
        )
    close_disagreement = bool(
        diagnostics.close_dispersion_bps is not None
        and diagnostics.close_dispersion_bps > DEFAULT_CLOSE_DISAGREEMENT_BPS
    )
    if count == 3:
        if close_disagreement:
            if _has_two_provider_close_consensus(bars):
                reason_codes.append("V2_CLOSE_PARTIAL_CONSENSUS")
                return REFERENCE_DEGRADED, TWO_PROVIDER_CONSENSUS
            reason_codes.append("V2_CLOSE_DISAGREEMENT_PUBLISHED")
            return VENUE_DISAGREEMENT, UNRESOLVED_PROVIDER_DISAGREEMENT
        if _has_range_disagreement(diagnostics):
            reason_codes.append("V2_THREE_PROVIDER_RANGE_DISAGREEMENT")
            return VENUE_DISAGREEMENT, UNRESOLVED_PROVIDER_DISAGREEMENT
        return REFERENCE_OK, THREE_PROVIDER_CONSENSUS
    if close_disagreement:
        reason_codes.append("V2_TWO_PROVIDER_CLOSE_DISAGREEMENT")
        return REFERENCE_UNAVAILABLE, UNRESOLVED_PROVIDER_DISAGREEMENT
    if trailing_atr is None or trailing_atr <= 0:
        reason_codes.append("V2_TRAILING_ATR_UNAVAILABLE")
        return REFERENCE_UNAVAILABLE, UNRESOLVED_PROVIDER_DISAGREEMENT
    if _has_range_disagreement(diagnostics):
        reason_codes.append("V2_TWO_PROVIDER_RANGE_DISAGREEMENT")
        return REFERENCE_UNAVAILABLE, UNRESOLVED_PROVIDER_DISAGREEMENT
    return REFERENCE_DEGRADED, TWO_PROVIDER_CONSENSUS


def _has_range_disagreement(diagnostics: CompositeDiagnostics) -> bool:
    return any(
        value is not None
        and value > DEFAULT_TWO_PROVIDER_RANGE_DISAGREEMENT_ATR
        for value in (
            diagnostics.high_dispersion_atr,
            diagnostics.low_dispersion_atr,
            diagnostics.range_dispersion_atr,
        )
    )


def _has_two_provider_close_consensus(bars: Sequence[Any]) -> bool:
    closes = sorted(bar.close for bar in bars)
    return any(
        (right - left) / _median((left, right)) * Decimal("10000")
        <= DEFAULT_CLOSE_DISAGREEMENT_BPS
        for left, right in zip(closes, closes[1:])
    )


def _diagnostics(
    bars: Sequence[Any], *, trailing_atr: Decimal | None
) -> CompositeDiagnostics:
    if len(bars) < 2:
        return CompositeDiagnostics(None, None, None, None)
    closes = tuple(bar.close for bar in bars)
    highs = tuple(bar.high for bar in bars)
    lows = tuple(bar.low for bar in bars)
    ranges = tuple(bar.high - bar.low for bar in bars)
    atr = trailing_atr if trailing_atr is not None and trailing_atr > 0 else None
    return CompositeDiagnostics(
        close_dispersion_bps=(max(closes) - min(closes)) / _median(closes) * 10000,
        high_dispersion_atr=(max(highs) - min(highs)) / atr if atr else None,
        low_dispersion_atr=(max(lows) - min(lows)) / atr if atr else None,
        range_dispersion_atr=(max(ranges) - min(ranges)) / atr if atr else None,
    )


def _validate_candle(
    open_price: Decimal | None,
    high: Decimal | None,
    low: Decimal | None,
    close: Decimal | None,
) -> None:
    if any(value is None for value in (open_price, high, low, close)):
        raise ValueError("V2 OHLC values must be present")
    if any(value <= 0 for value in (open_price, high, low, close)):
        raise ValueError("V2 OHLC values must be positive")
    if high < max(open_price, close) or low > min(open_price, close) or high < low:
        raise ValueError("V2 OHLC values violate candle invariants")


def _median(values: Sequence[Decimal]) -> Decimal:
    return Decimal(str(median(values)))


def _optional_decimal(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _protocol_markdown(definition: Mapping[str, Any]) -> str:
    hard_count = sum(item["hard"] for item in definition["approval_gates"])
    diagnostic_count = len(definition["approval_gates"]) - hard_count
    return f"""# BTC_REFERENCE_COMPOSITE_V2 Frozen Validation Protocol

## State

- Status: `{definition['status']}`
- Definition SHA-256: `{definition['definition_sha256']}`
- Research only: `true`
- External validation performed: `false`
- Production promotion authorized: `false`
- BTC-019: `IN PROGRESS`

## Formula

`MEDIAN_OHLC_V2` independently takes the median available provider open, high,
low, and close. Composite volume is not defined.

## Quality Semantics

- Three providers with full close agreement: publish `REFERENCE_OK`.
- Three providers with full close agreement but material high, low, or range
  dispersion: publish `VENUE_DISAGREEMENT`.
- Three providers with two-provider close consensus: publish `REFERENCE_DEGRADED`.
- Three providers without close consensus: publish `VENUE_DISAGREEMENT` with
  `reference_price_available=true`.
- Two agreeing providers with prior ATR and range checks passing: publish
  `REFERENCE_DEGRADED`.
- Two providers failing agreement checks: `REFERENCE_UNAVAILABLE`.
- One or zero providers: `REFERENCE_UNAVAILABLE`.

Reference availability and strategy entry permission are separate contracts.
This protocol does not choose final entry/add behavior.

## Higher Timeframes

Daily and weekly records always persist expected, observed, missing, degraded,
venue-disagreement, and unavailable counts. Complete warned buckets publish
OHLC with warning state. Incomplete buckets persist null OHLC with
`bucket_complete=false`, `bucket_usable=false`, and `REFERENCE_UNAVAILABLE`.
Partial-bucket OHLC is not approved, and silent omission is prohibited.

## Validation

- Hard gates: {hard_count}
- Diagnostic gates: {diagnostic_count}
- Primary ATR materiality threshold: `0.50 ATR`
- Full ATR grid: `0.10, 0.20, 0.30, 0.50, 1.00 ATR`
- Required comparison series: Bitstamp, Coinbase, Bitfinex, historical
  `MEDIAN_OHLC_V1`, and `BTC_REFERENCE_COMPOSITE_V2`.
- Production promotion additionally requires at least 90 days of live shadow.

## Sealed Sample

- Start: `{definition['untouched_validation_sample']['start']}`
- End: `{definition['untouched_validation_sample']['end']}`
- `BOUNDARY_VERIFIED`
- `BULK_COMPLETENESS_UNMEASURED`
- `OUTCOMES_UNINSPECTED`
- `DO_NOT_OPEN_UNTIL_V2_VALIDATION`

BTC-019C does not bulk collect, inspect, or validate this period. A future
dedicated validator bound to this definition hash is required to open it.

## Governance

V1, BTC-019B, and `PRICE_SOURCE_POLICY_V1` remain unchanged. Material V2
methodology changes require `BTC_REFERENCE_COMPOSITE_V3` or a later explicit
version. Normal Phase-1 development may resume after this freeze.
"""
