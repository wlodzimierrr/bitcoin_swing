"""Canonical BTC price-source policy and validation helpers."""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_CEILING, Decimal
from statistics import median
from typing import Any

from btc_predictor.data import (
    OhlcvBar,
    build_canonical_market_bars,
    expected_bar_timestamps,
    next_bar_timestamp,
    require_utc_datetime,
)
from btc_predictor.levels import (
    BREAKOUT_LEVEL_TYPE,
    RECLAIM_LEVEL_TYPE,
    WEEKLY_SWING_HIGH,
    WEEKLY_SWING_LOW,
    detect_breakout_reclaim_levels,
    detect_weekly_swing_levels,
)


PRICE_SOURCE_POLICY_VERSION = "PRICE_SOURCE_POLICY_V1"
REFERENCE_PRICE_ROLE = "reference_price"
PRIMARY_RAW_OHLCV_ROLE = "primary_raw_ohlcv"
VALIDATION_PROVIDER_ROLE = "validation_provider"
INSTITUTIONAL_REFERENCE_BENCHMARK_ROLE = "institutional_reference_benchmark"
NONCANONICAL_SANITY_CHECK_ROLE = "noncanonical_sanity_check"
PRICE_SOURCE_PROVIDER_ROLES = (
    REFERENCE_PRICE_ROLE,
    PRIMARY_RAW_OHLCV_ROLE,
    VALIDATION_PROVIDER_ROLE,
    INSTITUTIONAL_REFERENCE_BENCHMARK_ROLE,
    NONCANONICAL_SANITY_CHECK_ROLE,
)
COIN_METRICS_COMMUNITY_PROVIDER_ID = "coin_metrics_community"
BITSTAMP_PROVIDER_ID = "bitstamp"
COINBASE_PROVIDER_ID = "coinbase"
BITFINEX_PROVIDER_ID = "bitfinex"
YFINANCE_PROVIDER_ID = "yfinance"
REQUIRED_POLICY_PROVIDER_IDS = (
    BITSTAMP_PROVIDER_ID,
    COINBASE_PROVIDER_ID,
    BITFINEX_PROVIDER_ID,
)
PRICE_SOURCE_POLICY_REASON_CODES = (
    "PRICE_SOURCE_POLICY_INPUT_MISSING",
    "PRICE_SOURCE_POLICY_REQUIRED_PROVIDER_MISSING",
    "PRICE_SOURCE_POLICY_OVERLAP_TOO_SHORT",
    "PRICE_SOURCE_POLICY_MANUAL_REVIEW_MISSING",
    "PRICE_SOURCE_POLICY_CANONICAL_DECISION_MISSING",
    "PRICE_SOURCE_POLICY_FALLBACK_SPLICE_FORBIDDEN",
)
MANUAL_REVIEW_DISPOSITIONS = (
    "cross_market_movement",
    "venue_specific_anomaly",
    "provider_data_error",
    "timestamp_alignment_artifact",
    "low_liquidity_venue_event",
    "unresolved",
)
PROVIDER_ACCESS_STATUSES = (
    "available",
    "not_requested",
    "credentials_unavailable",
    "entitlement_unavailable",
    "provider_outage",
    "api_error",
)
CANONICAL_DECISION_STATUSES = ("approved", "rejected")
CANONICAL_CANDIDATE_STATUSES = ("provisional", "approved", "rejected")
DIVERGENCE_TIER_PRICE = 1
DIVERGENCE_TIER_INDICATOR = 2
DIVERGENCE_TIER_DECISION = 3
DIVERGENCE_TIER_PORTFOLIO = 4
WICK_ANOMALY_CANDIDATE = "WICK_ANOMALY_CANDIDATE"
CROSS_VENUE_CONFIRMED = "CROSS_VENUE_CONFIRMED"
CROSS_VENUE_UNCONFIRMED = "CROSS_VENUE_UNCONFIRMED"


@dataclass(frozen=True)
class PriceSourceInstrumentPolicy:
    provider_id: str
    provider_name: str
    roles: tuple[str, ...]
    exchange: str
    symbol: str
    api_instrument: str
    timeframe: str
    reference_price_role: bool
    execution_venue: bool
    required_for_v1_completion: bool
    fallback_splicing_allowed: bool
    historical_fallback_policy_version: str | None
    api_endpoint: str
    api_practicality: str
    access_constraints: str
    data_semantics: str
    notes: str

    def as_record(self) -> dict[str, Any]:
        _validate_non_empty(self.provider_id, "provider_id")
        _validate_non_empty(self.provider_name, "provider_name")
        _validate_non_empty(self.exchange, "exchange")
        _validate_non_empty(self.symbol, "symbol")
        _validate_non_empty(self.api_instrument, "api_instrument")
        _validate_non_empty(self.api_endpoint, "api_endpoint")
        _validate_non_empty(self.api_practicality, "api_practicality")
        _validate_non_empty(self.access_constraints, "access_constraints")
        _validate_non_empty(self.data_semantics, "data_semantics")
        if not self.roles or any(
            role not in PRICE_SOURCE_PROVIDER_ROLES for role in self.roles
        ):
            raise ValueError(f"roles must use values from {PRICE_SOURCE_PROVIDER_ROLES}")
        if len(self.roles) != len(set(self.roles)):
            raise ValueError("instrument policy roles must be unique")
        if self.timeframe != "1h":
            raise ValueError("price-source policy compares synchronized 1h windows")
        if self.fallback_splicing_allowed and not self.historical_fallback_policy_version:
            raise ValueError(
                "historical fallback splicing requires a policy version",
            )
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "roles": list(self.roles),
            "exchange": self.exchange,
            "symbol": self.symbol,
            "api_instrument": self.api_instrument,
            "timeframe": self.timeframe,
            "reference_price_role": self.reference_price_role,
            "execution_venue": self.execution_venue,
            "required_for_v1_completion": self.required_for_v1_completion,
            "fallback_splicing_allowed": self.fallback_splicing_allowed,
            "historical_fallback_policy_version": (
                self.historical_fallback_policy_version
            ),
            "api_endpoint": self.api_endpoint,
            "api_practicality": self.api_practicality,
            "access_constraints": self.access_constraints,
            "data_semantics": self.data_semantics,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class PriceSourcePolicy:
    version: str
    canonical_candidate_provider_id: str
    canonical_candidate_status: str
    canonical_reference_provider_id: str | None
    primary_raw_ohlcv_provider_id: str
    required_validation_provider_ids: tuple[str, ...]
    secondary_validation_provider_id: str
    additional_validation_provider_ids: tuple[str, ...]
    institutional_reference_benchmark_provider_ids: tuple[str, ...]
    noncanonical_sanity_check_provider_ids: tuple[str, ...]
    instruments: tuple[PriceSourceInstrumentPolicy, ...]
    isolated_exchange_wick_rule: str
    provider_outage_fallback_rule: str
    historical_fallback_splicing_rule: str

    def as_record(self) -> dict[str, Any]:
        if self.version != PRICE_SOURCE_POLICY_VERSION:
            raise ValueError(f"version must be {PRICE_SOURCE_POLICY_VERSION}")
        if self.canonical_candidate_status not in CANONICAL_CANDIDATE_STATUSES:
            raise ValueError(
                "canonical candidate status must be one of "
                f"{CANONICAL_CANDIDATE_STATUSES}",
            )
        if (
            self.canonical_candidate_status == "approved"
            and self.canonical_candidate_provider_id
            != self.canonical_reference_provider_id
        ):
            raise ValueError(
                "approved V1 reference must match the canonical candidate",
            )
        if (
            self.canonical_candidate_status != "approved"
            and self.canonical_reference_provider_id is not None
        ):
            raise ValueError(
                "unapproved canonical candidate cannot be the canonical reference",
            )
        provider_ids = [instrument.provider_id for instrument in self.instruments]
        if len(provider_ids) != len(set(provider_ids)):
            raise ValueError("price-source policy provider IDs must be unique")
        instruments_by_provider = {
            instrument.provider_id: instrument for instrument in self.instruments
        }
        for instrument in self.instruments:
            instrument.as_record()
        if len(self.required_validation_provider_ids) < 3:
            raise ValueError("at least three independent validation providers are required")
        if len(self.required_validation_provider_ids) != len(
            set(self.required_validation_provider_ids)
        ):
            raise ValueError("required validation provider IDs must be unique")
        required_exchanges = [
            instruments_by_provider[provider_id].exchange
            for provider_id in self.required_validation_provider_ids
            if provider_id in instruments_by_provider
        ]
        if len(required_exchanges) != len(set(required_exchanges)):
            raise ValueError("required validation providers must use independent venues")
        if self.canonical_candidate_provider_id not in self.required_validation_provider_ids:
            raise ValueError("V1 canonical candidate must be in the empirical provider set")
        if self.secondary_validation_provider_id not in self.required_validation_provider_ids:
            raise ValueError("secondary validation provider must be required for V1")
        if any(
            provider_id not in self.required_validation_provider_ids
            for provider_id in self.additional_validation_provider_ids
        ):
            raise ValueError("additional validation providers must be required for V1")
        selected_provider_ids = (
            self.canonical_candidate_provider_id,
            self.primary_raw_ohlcv_provider_id,
            self.secondary_validation_provider_id,
            *self.additional_validation_provider_ids,
            *self.institutional_reference_benchmark_provider_ids,
            *self.noncanonical_sanity_check_provider_ids,
            *self.required_validation_provider_ids,
        )
        if any(
            provider_id not in instruments_by_provider
            for provider_id in selected_provider_ids
        ):
            raise ValueError("every selected provider must have instrument provenance")
        if (
            REFERENCE_PRICE_ROLE
            not in instruments_by_provider[self.canonical_candidate_provider_id].roles
        ):
            raise ValueError("canonical candidate must have reference-price role")
        if (
            PRIMARY_RAW_OHLCV_ROLE
            not in instruments_by_provider[self.primary_raw_ohlcv_provider_id].roles
        ):
            raise ValueError("primary raw provider must have primary raw OHLCV role")
        for provider_id in self.required_validation_provider_ids:
            instrument = instruments_by_provider[provider_id]
            if VALIDATION_PROVIDER_ROLE not in instrument.roles:
                raise ValueError("required providers must have validation-provider role")
            if not instrument.required_for_v1_completion:
                raise ValueError("required provider must be marked required for V1")
        for provider_id, instrument in instruments_by_provider.items():
            if instrument.required_for_v1_completion != (
                provider_id in self.required_validation_provider_ids
            ):
                raise ValueError("instrument required flag must match policy required set")
            if instrument.reference_price_role != (
                REFERENCE_PRICE_ROLE in instrument.roles
            ):
                raise ValueError("reference_price_role must match instrument roles")
        for provider_id in self.institutional_reference_benchmark_provider_ids:
            instrument = instruments_by_provider[provider_id]
            if INSTITUTIONAL_REFERENCE_BENCHMARK_ROLE not in instrument.roles:
                raise ValueError("institutional benchmark provider has wrong role")
            if instrument.required_for_v1_completion:
                raise ValueError("institutional benchmark must be optional for V1")
        for provider_id in self.noncanonical_sanity_check_provider_ids:
            instrument = instruments_by_provider[provider_id]
            if NONCANONICAL_SANITY_CHECK_ROLE not in instrument.roles:
                raise ValueError("sanity-check provider must have noncanonical role")
            if instrument.required_for_v1_completion:
                raise ValueError("sanity-check provider must be optional for V1")
        if instruments_by_provider[
            self.canonical_candidate_provider_id
        ].execution_venue:
            raise ValueError("reference-price role must be separate from execution")
        if any(instrument.fallback_splicing_allowed for instrument in self.instruments):
            raise ValueError("unversioned historical fallback splicing is prohibited")
        return {
            "version": self.version,
            "canonical_candidate_provider_id": self.canonical_candidate_provider_id,
            "canonical_candidate_status": self.canonical_candidate_status,
            "canonical_reference_provider_id": self.canonical_reference_provider_id,
            "primary_raw_ohlcv_provider_id": self.primary_raw_ohlcv_provider_id,
            "required_validation_provider_ids": list(
                self.required_validation_provider_ids
            ),
            "secondary_validation_provider_id": self.secondary_validation_provider_id,
            "additional_validation_provider_ids": list(
                self.additional_validation_provider_ids
            ),
            "institutional_reference_benchmark_provider_ids": list(
                self.institutional_reference_benchmark_provider_ids
            ),
            "noncanonical_sanity_check_provider_ids": list(
                self.noncanonical_sanity_check_provider_ids
            ),
            "instruments": [
                instrument.as_record() for instrument in self.instruments
            ],
            "isolated_exchange_wick_rule": self.isolated_exchange_wick_rule,
            "provider_outage_fallback_rule": self.provider_outage_fallback_rule,
            "historical_fallback_splicing_rule": (
                self.historical_fallback_splicing_rule
            ),
        }


DEFAULT_PRICE_SOURCE_POLICY = PriceSourcePolicy(
    version=PRICE_SOURCE_POLICY_VERSION,
    canonical_candidate_provider_id=BITSTAMP_PROVIDER_ID,
    canonical_candidate_status="rejected",
    canonical_reference_provider_id=None,
    primary_raw_ohlcv_provider_id=BITSTAMP_PROVIDER_ID,
    required_validation_provider_ids=REQUIRED_POLICY_PROVIDER_IDS,
    secondary_validation_provider_id=COINBASE_PROVIDER_ID,
    additional_validation_provider_ids=(BITFINEX_PROVIDER_ID,),
    institutional_reference_benchmark_provider_ids=(
        COIN_METRICS_COMMUNITY_PROVIDER_ID,
    ),
    noncanonical_sanity_check_provider_ids=(YFINANCE_PROVIDER_ID,),
    instruments=(
        PriceSourceInstrumentPolicy(
            provider_id=BITSTAMP_PROVIDER_ID,
            provider_name="Bitstamp",
            roles=(
                REFERENCE_PRICE_ROLE,
                PRIMARY_RAW_OHLCV_ROLE,
                VALIDATION_PROVIDER_ROLE,
            ),
            exchange="bitstamp",
            symbol="BTC/USD",
            api_instrument="btcusd",
            timeframe="1h",
            reference_price_role=True,
            execution_venue=False,
            required_for_v1_completion=True,
            fallback_splicing_allowed=False,
            historical_fallback_policy_version=None,
            api_endpoint="https://www.bitstamp.net/api/v2/ohlc/btcusd/",
            api_practicality=(
                "1-1000 candles per request; standard public limits are 400 requests "
                "per second and 10000 requests per 10 minutes"
            ),
            access_constraints="Public endpoint; paginate with explicit UTC start/end.",
            data_semantics="Bitstamp BTC/USD spot exchange OHLCV.",
            notes=(
                "Rejected V1 canonical candidate retained as the primary raw OHLCV "
                "provider; it must not be exposed as strategy-canonical."
            ),
        ),
        PriceSourceInstrumentPolicy(
            provider_id=COINBASE_PROVIDER_ID,
            provider_name="Coinbase Exchange",
            roles=(VALIDATION_PROVIDER_ROLE,),
            exchange="coinbase",
            symbol="BTC-USD",
            api_instrument="BTC-USD",
            timeframe="1h",
            reference_price_role=False,
            execution_venue=False,
            required_for_v1_completion=True,
            fallback_splicing_allowed=False,
            historical_fallback_policy_version=None,
            api_endpoint=(
                "https://api.exchange.coinbase.com/products/BTC-USD/candles"
            ),
            api_practicality="Maximum 300 candles per request; page explicit UTC windows.",
            access_constraints=(
                "Public endpoint; historic rates can be incomplete and intervals with "
                "no ticks are omitted."
            ),
            data_semantics="Coinbase Exchange BTC-USD spot OHLCV.",
            notes="Independent Phase 1 validation provider.",
        ),
        PriceSourceInstrumentPolicy(
            provider_id=BITFINEX_PROVIDER_ID,
            provider_name="Bitfinex",
            roles=(VALIDATION_PROVIDER_ROLE,),
            exchange="bitfinex",
            symbol="BTC/USD",
            api_instrument="tBTCUSD",
            timeframe="1h",
            reference_price_role=False,
            execution_venue=False,
            required_for_v1_completion=True,
            fallback_splicing_allowed=False,
            historical_fallback_policy_version=None,
            api_endpoint=(
                "https://api-pub.bitfinex.com/v2/candles/"
                "trade:1h:tBTCUSD/hist"
            ),
            api_practicality=(
                "Maximum 10000 candles per request; public candles rate limit is "
                "30 requests per minute"
            ),
            access_constraints="Public endpoint; paginate millisecond UTC windows.",
            data_semantics="Bitfinex tBTCUSD spot exchange OHLCV.",
            notes="Independent Phase 1 validation provider.",
        ),
        PriceSourceInstrumentPolicy(
            provider_id=COIN_METRICS_COMMUNITY_PROVIDER_ID,
            provider_name="Coin Metrics Community",
            roles=(INSTITUTIONAL_REFERENCE_BENCHMARK_ROLE,),
            exchange="coin_metrics_community",
            symbol="BTC/USD",
            api_instrument="btc-usd",
            timeframe="1h",
            reference_price_role=False,
            execution_venue=False,
            required_for_v1_completion=False,
            fallback_splicing_allowed=False,
            historical_fallback_policy_version=None,
            api_endpoint=(
                "https://community-api.coinmetrics.io/v4/timeseries/pair-candles"
            ),
            api_practicality="next_page_url pagination; historical entitlement check required",
            access_constraints=(
                "Catalog coverage and credential entitlement are separate; unavailable "
                "history is reported as access status and does not block V1."
            ),
            data_semantics=(
                "Pair candles are built from Coin Metrics reference rates and do not "
                "provide exchange volume."
            ),
            notes=(
                "Optional V1 institutional benchmark and future canonical candidate; "
                "promotion requires PRICE_SOURCE_POLICY_V2."
            ),
        ),
        PriceSourceInstrumentPolicy(
            provider_id=YFINANCE_PROVIDER_ID,
            provider_name="yfinance",
            roles=(NONCANONICAL_SANITY_CHECK_ROLE,),
            exchange="yfinance",
            symbol="BTC-USD",
            api_instrument="BTC-USD",
            timeframe="1h",
            reference_price_role=False,
            execution_venue=False,
            required_for_v1_completion=False,
            fallback_splicing_allowed=False,
            historical_fallback_policy_version=None,
            api_endpoint="https://query1.finance.yahoo.com/",
            api_practicality="intraday_history_limited_sanity_check_only",
            access_constraints=(
                "yfinance documents a 60-day maximum for intraday history and limits "
                "the data to research/personal-use workflows."
            ),
            data_semantics="Yahoo Finance BTC-USD convenience series; noncanonical.",
            notes="Research convenience source only; not canonical for intraday history.",
        ),
    ),
    isolated_exchange_wick_rule=(
        "An isolated exchange-specific wick must not automatically redefine strategy "
        "structure; raw candles remain immutable and review determines strategy impact."
    ),
    provider_outage_fallback_rule=(
        "Provider outages must be represented as gaps. Fallback data can be used "
        "for validation and live continuity, but historical splicing is prohibited "
        "unless a new versioned policy explicitly permits it."
    ),
    historical_fallback_splicing_rule=(
        "Historical fallback splicing is prohibited in PRICE_SOURCE_POLICY_V1."
    ),
)


@dataclass(frozen=True)
class ProviderAccessDiagnostic:
    provider_id: str
    status: str
    checked_at: datetime
    details: str
    catalog_coverage_advertised: bool = False
    historical_retrieval_entitled: bool | None = None

    def as_record(self) -> dict[str, Any]:
        _validate_non_empty(self.provider_id, "provider_id")
        if self.status not in PROVIDER_ACCESS_STATUSES:
            raise ValueError(
                f"provider access status must be one of {PROVIDER_ACCESS_STATUSES}",
            )
        _validate_non_empty(self.details, "details")
        return {
            "provider_id": self.provider_id,
            "status": self.status,
            "checked_at": require_utc_datetime(
                self.checked_at,
                "checked_at",
            ).isoformat(),
            "details": self.details,
            "catalog_coverage_advertised": self.catalog_coverage_advertised,
            "historical_retrieval_entitled": self.historical_retrieval_entitled,
        }


@dataclass(frozen=True)
class CanonicalSourceDecision:
    policy_version: str
    provider_id: str
    status: str
    decided_at: datetime
    reviewer: str
    rationale: str

    def as_record(self) -> dict[str, str]:
        if self.policy_version != PRICE_SOURCE_POLICY_VERSION:
            raise ValueError(
                f"canonical decision policy_version must be {PRICE_SOURCE_POLICY_VERSION}",
            )
        if self.status not in CANONICAL_DECISION_STATUSES:
            raise ValueError(
                f"canonical decision status must be one of {CANONICAL_DECISION_STATUSES}",
            )
        _validate_non_empty(self.provider_id, "provider_id")
        _validate_non_empty(self.reviewer, "reviewer")
        _validate_non_empty(self.rationale, "rationale")
        return {
            "policy_version": self.policy_version,
            "provider_id": self.provider_id,
            "status": self.status,
            "decided_at": require_utc_datetime(
                self.decided_at,
                "decided_at",
            ).isoformat(),
            "reviewer": self.reviewer,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class TradePathProbe:
    entry_time: datetime
    exit_time: datetime
    entry_price: Decimal
    direction: str = "long"
    stop_level: Decimal | None = None

    def as_record(self) -> dict[str, str | None]:
        entry_time = require_utc_datetime(self.entry_time, "entry_time")
        exit_time = require_utc_datetime(self.exit_time, "exit_time")
        if exit_time < entry_time:
            raise ValueError("exit_time must be >= entry_time")
        if self.direction not in ("long", "short"):
            raise ValueError("direction must be 'long' or 'short'")
        record = {
            "entry_time": entry_time.isoformat(),
            "exit_time": exit_time.isoformat(),
            "entry_price": str(_positive_decimal(self.entry_price, "entry_price")),
            "direction": self.direction,
        }
        record["stop_level"] = (
            str(_positive_decimal(self.stop_level, "stop_level"))
            if self.stop_level is not None
            else None
        )
        return record


@dataclass(frozen=True)
class DivergenceDistribution:
    observation_count: int
    mean_abs: Decimal | None
    median_abs: Decimal | None
    standard_deviation_abs: Decimal | None
    p90_abs: Decimal | None
    p95_abs: Decimal | None
    p99_abs: Decimal | None
    p995_abs: Decimal | None
    max_abs: Decimal | None

    def as_record(self) -> dict[str, str | int | None]:
        return {
            "observation_count": self.observation_count,
            "mean_abs": _optional_decimal_record(self.mean_abs),
            "median_abs": _optional_decimal_record(self.median_abs),
            "standard_deviation_abs": _optional_decimal_record(
                self.standard_deviation_abs,
            ),
            "p90_abs": _optional_decimal_record(self.p90_abs),
            "p95_abs": _optional_decimal_record(self.p95_abs),
            "p99_abs": _optional_decimal_record(self.p99_abs),
            "p995_abs": _optional_decimal_record(self.p995_abs),
            "max_abs": _optional_decimal_record(self.max_abs),
        }


@dataclass(frozen=True)
class DivergenceTierSummary:
    tier: int
    category: str
    event_count: int
    metrics: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        if self.tier not in (
            DIVERGENCE_TIER_PRICE,
            DIVERGENCE_TIER_INDICATOR,
            DIVERGENCE_TIER_DECISION,
            DIVERGENCE_TIER_PORTFOLIO,
        ):
            raise ValueError("divergence tier must be between 1 and 4")
        if self.event_count < 0:
            raise ValueError("divergence tier event_count must be non-negative")
        _validate_non_empty(self.category, "category")
        return {
            "tier": self.tier,
            "category": self.category,
            "event_count": self.event_count,
            "metrics": list(self.metrics),
        }


@dataclass(frozen=True)
class CrossVenueWickDiagnostic:
    timestamp: datetime
    provider_id: str
    reference_provider_ids: tuple[str, ...]
    provider_high: Decimal
    provider_low: Decimal
    provider_close: Decimal
    median_high: Decimal
    median_low: Decimal
    median_close: Decimal
    atr_value: Decimal | None
    high_atr_divergence: Decimal | None
    low_atr_divergence: Decimal | None
    candidate_flags: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        if any(
            flag not in (
                WICK_ANOMALY_CANDIDATE,
                CROSS_VENUE_CONFIRMED,
                CROSS_VENUE_UNCONFIRMED,
            )
            for flag in self.candidate_flags
        ):
            raise ValueError("unknown cross-venue wick candidate flag")
        return {
            "timestamp": require_utc_datetime(
                self.timestamp,
                "timestamp",
            ).isoformat(),
            "provider_id": self.provider_id,
            "reference_provider_ids": list(self.reference_provider_ids),
            "provider_high": str(self.provider_high),
            "provider_low": str(self.provider_low),
            "provider_close": str(self.provider_close),
            "median_high": str(self.median_high),
            "median_low": str(self.median_low),
            "median_close": str(self.median_close),
            "atr_value": _optional_decimal_record(self.atr_value),
            "high_atr_divergence": _optional_decimal_record(
                self.high_atr_divergence,
            ),
            "low_atr_divergence": _optional_decimal_record(
                self.low_atr_divergence,
            ),
            "candidate_flags": list(self.candidate_flags),
        }


@dataclass(frozen=True)
class PriceSourceSeriesProfile:
    provider_id: str
    price_source_policy_version: str
    price_source_roles: tuple[str, ...]
    fallback_used: bool
    exchange: str
    symbol: str
    timeframe: str
    start: datetime
    end: datetime
    bar_count: int
    expected_bar_count: int
    missing_bar_count: int
    duplicate_bar_count: int
    missing_bar_rate: Decimal
    largest_missing_run_hours: int
    historical_coverage_days: Decimal

    def as_record(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "price_source_policy_version": self.price_source_policy_version,
            "price_source_roles": list(self.price_source_roles),
            "fallback_used": self.fallback_used,
            "exchange": self.exchange,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "start": require_utc_datetime(self.start, "start").isoformat(),
            "end": require_utc_datetime(self.end, "end").isoformat(),
            "bar_count": self.bar_count,
            "expected_bar_count": self.expected_bar_count,
            "missing_bar_count": self.missing_bar_count,
            "duplicate_bar_count": self.duplicate_bar_count,
            "missing_bar_rate": str(self.missing_bar_rate),
            "largest_missing_run_hours": self.largest_missing_run_hours,
            "historical_coverage_days": str(self.historical_coverage_days),
        }


@dataclass(frozen=True)
class PriceSourceDivergenceEvent:
    timestamp: datetime
    provider_id: str
    metric: str
    baseline_value: Decimal
    provider_value: Decimal
    absolute_difference: Decimal
    percentage_difference: Decimal

    def as_record(self) -> dict[str, str]:
        return {
            "timestamp": require_utc_datetime(
                self.timestamp,
                "timestamp",
            ).isoformat(),
            "provider_id": self.provider_id,
            "metric": self.metric,
            "baseline_value": str(self.baseline_value),
            "provider_value": str(self.provider_value),
            "absolute_difference": str(self.absolute_difference),
            "percentage_difference": str(self.percentage_difference),
        }


@dataclass(frozen=True)
class PriceSourceOhlcvSnapshot:
    provider_id: str
    exchange: str
    symbol: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    @classmethod
    def from_bar(cls, bar: OhlcvBar) -> PriceSourceOhlcvSnapshot:
        return cls(
            provider_id=bar.provider,
            exchange=bar.exchange,
            symbol=bar.symbol,
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
        )

    def as_record(self) -> dict[str, str]:
        _validate_non_empty(self.provider_id, "provider_id")
        _validate_non_empty(self.exchange, "exchange")
        _validate_non_empty(self.symbol, "symbol")
        if any(value <= 0 for value in (self.open, self.high, self.low, self.close)):
            raise ValueError("manual review OHLC values must be positive")
        return {
            "provider_id": self.provider_id,
            "exchange": self.exchange,
            "symbol": self.symbol,
            "open": str(self.open),
            "high": str(self.high),
            "low": str(self.low),
            "close": str(self.close),
        }


@dataclass(frozen=True)
class PriceSourceDivergenceReview:
    timestamp: datetime
    provider_id: str
    metric: str
    providers_involved: tuple[str, ...]
    canonical_candidate_ohlc: PriceSourceOhlcvSnapshot
    validator_ohlc: PriceSourceOhlcvSnapshot
    cross_provider_median_high: Decimal
    cross_provider_median_low: Decimal
    cross_provider_median_close: Decimal
    atr_normalized_divergence: Decimal | None
    event_classification: str
    swing_impact: bool
    breakout_impact: bool
    reclaim_impact: bool
    stop_touch_impact: bool
    mfe_impact: bool
    mae_impact: bool
    trade_outcome_impact: bool
    review_conclusion: str
    review_notes: str
    reviewed_at: datetime

    @property
    def event_key(self) -> tuple[datetime, str, str]:
        return (
            require_utc_datetime(self.timestamp, "timestamp"),
            self.provider_id,
            self.metric,
        )

    def as_record(self) -> dict[str, Any]:
        if self.metric not in ("close", "high", "low"):
            raise ValueError("manual review metric must be close, high, or low")
        if self.event_classification not in MANUAL_REVIEW_DISPOSITIONS:
            raise ValueError(
                "manual review classification must be one of "
                f"{MANUAL_REVIEW_DISPOSITIONS}",
            )
        _validate_non_empty(self.provider_id, "provider_id")
        if len(set(self.providers_involved)) < 2:
            raise ValueError("manual review must involve at least two providers")
        if self.provider_id != self.validator_ohlc.provider_id:
            raise ValueError("manual review provider_id must match validator OHLC")
        if self.canonical_candidate_ohlc.provider_id not in self.providers_involved:
            raise ValueError("canonical candidate must be listed in providers_involved")
        if self.validator_ohlc.provider_id not in self.providers_involved:
            raise ValueError("validator must be listed in providers_involved")
        self.canonical_candidate_ohlc.as_record()
        self.validator_ohlc.as_record()
        if any(
            value <= 0
            for value in (
                self.cross_provider_median_high,
                self.cross_provider_median_low,
                self.cross_provider_median_close,
            )
        ):
            raise ValueError("manual review cross-provider medians must be positive")
        if (
            self.atr_normalized_divergence is not None
            and self.atr_normalized_divergence < 0
        ):
            raise ValueError("ATR-normalized divergence must be non-negative")
        _validate_non_empty(self.review_conclusion, "review_conclusion")
        _validate_non_empty(self.review_notes, "review_notes")
        return {
            "timestamp": self.event_key[0].isoformat(),
            "provider_id": self.provider_id,
            "metric": self.metric,
            "providers_involved": list(self.providers_involved),
            "canonical_candidate_ohlc": self.canonical_candidate_ohlc.as_record(),
            "validator_ohlc": self.validator_ohlc.as_record(),
            "cross_provider_median_high": str(self.cross_provider_median_high),
            "cross_provider_median_low": str(self.cross_provider_median_low),
            "cross_provider_median_close": str(self.cross_provider_median_close),
            "atr_normalized_divergence": _optional_decimal_record(
                self.atr_normalized_divergence,
            ),
            "event_classification": self.event_classification,
            "swing_impact": self.swing_impact,
            "breakout_impact": self.breakout_impact,
            "reclaim_impact": self.reclaim_impact,
            "stop_touch_impact": self.stop_touch_impact,
            "mfe_impact": self.mfe_impact,
            "mae_impact": self.mae_impact,
            "trade_outcome_impact": self.trade_outcome_impact,
            "review_conclusion": self.review_conclusion,
            "review_notes": self.review_notes,
            "reviewed_at": require_utc_datetime(
                self.reviewed_at,
                "reviewed_at",
            ).isoformat(),
        }


@dataclass(frozen=True)
class PriceSourceComparisonReport:
    policy_version: str
    baseline_provider_id: str
    required_provider_ids: tuple[str, ...]
    candidate_provider_ids: tuple[str, ...]
    start: datetime
    end: datetime
    as_of: datetime
    overlap_bar_count: int
    overlap_years: Decimal
    minimum_overlap_years: Decimal
    series_profiles: tuple[PriceSourceSeriesProfile, ...]
    close_price_divergence: DivergenceDistribution
    high_price_divergence: DivergenceDistribution
    low_price_divergence: DivergenceDistribution
    extreme_wick_divergence: DivergenceDistribution
    daily_return_divergence: DivergenceDistribution
    atr_divergence: DivergenceDistribution
    wick_high_atr_divergence: DivergenceDistribution
    wick_low_atr_divergence: DivergenceDistribution
    cross_venue_wick_diagnostics: tuple[CrossVenueWickDiagnostic, ...]
    swing_high_difference_count: int
    swing_low_difference_count: int
    swing_level_difference_count: int
    breakout_difference_count: int
    reclaim_difference_count: int
    breakout_reclaim_difference_count: int
    stop_touch_difference_count: int
    mfe_divergence: DivergenceDistribution
    mae_divergence: DivergenceDistribution
    mfe_mae_difference: DivergenceDistribution
    divergence_tiers: tuple[DivergenceTierSummary, ...]
    stop_levels: tuple[Decimal, ...]
    trade_path_probes: tuple[TradePathProbe, ...]
    top_event_count: int
    top_divergence_events: tuple[PriceSourceDivergenceEvent, ...]
    manual_reviews: tuple[PriceSourceDivergenceReview, ...]
    provider_access_diagnostics: tuple[ProviderAccessDiagnostic, ...]
    canonical_source_decision: CanonicalSourceDecision | None
    reason_codes: tuple[str, ...]

    @property
    def policy_decision_ready(self) -> bool:
        return not self.reason_codes

    @property
    def canonical_provider_approved(self) -> bool:
        return (
            self.canonical_source_decision is not None
            and self.canonical_source_decision.status == "approved"
        )

    def as_record(self) -> dict[str, Any]:
        return {
            "policy_version": self.policy_version,
            "baseline_provider_id": self.baseline_provider_id,
            "required_provider_ids": list(self.required_provider_ids),
            "candidate_provider_ids": list(self.candidate_provider_ids),
            "start": require_utc_datetime(self.start, "start").isoformat(),
            "end": require_utc_datetime(self.end, "end").isoformat(),
            "as_of": require_utc_datetime(self.as_of, "as_of").isoformat(),
            "overlap_bar_count": self.overlap_bar_count,
            "overlap_years": str(self.overlap_years),
            "minimum_overlap_years": str(self.minimum_overlap_years),
            "series_profiles": [
                profile.as_record() for profile in self.series_profiles
            ],
            "close_price_divergence": self.close_price_divergence.as_record(),
            "high_price_divergence": self.high_price_divergence.as_record(),
            "low_price_divergence": self.low_price_divergence.as_record(),
            "extreme_wick_divergence": self.extreme_wick_divergence.as_record(),
            "daily_return_divergence": self.daily_return_divergence.as_record(),
            "atr_divergence": self.atr_divergence.as_record(),
            "wick_high_atr_divergence": (
                self.wick_high_atr_divergence.as_record()
            ),
            "wick_low_atr_divergence": self.wick_low_atr_divergence.as_record(),
            "cross_venue_wick_diagnostics": [
                diagnostic.as_record()
                for diagnostic in self.cross_venue_wick_diagnostics
            ],
            "swing_high_difference_count": self.swing_high_difference_count,
            "swing_low_difference_count": self.swing_low_difference_count,
            "swing_level_difference_count": self.swing_level_difference_count,
            "breakout_difference_count": self.breakout_difference_count,
            "reclaim_difference_count": self.reclaim_difference_count,
            "breakout_reclaim_difference_count": (
                self.breakout_reclaim_difference_count
            ),
            "stop_touch_difference_count": self.stop_touch_difference_count,
            "mfe_divergence": self.mfe_divergence.as_record(),
            "mae_divergence": self.mae_divergence.as_record(),
            "mfe_mae_difference": self.mfe_mae_difference.as_record(),
            "divergence_tiers": [
                summary.as_record() for summary in self.divergence_tiers
            ],
            "stop_levels": [str(stop_level) for stop_level in self.stop_levels],
            "trade_path_probes": [
                probe.as_record() for probe in self.trade_path_probes
            ],
            "top_event_count": self.top_event_count,
            "top_divergence_events": [
                event.as_record() for event in self.top_divergence_events
            ],
            "manual_reviews": [
                review.as_record() for review in self.manual_reviews
            ],
            "provider_access_diagnostics": [
                diagnostic.as_record()
                for diagnostic in self.provider_access_diagnostics
            ],
            "canonical_source_decision": (
                self.canonical_source_decision.as_record()
                if self.canonical_source_decision is not None
                else None
            ),
            "policy_decision_ready": self.policy_decision_ready,
            "canonical_provider_approved": self.canonical_provider_approved,
            "reason_codes": list(self.reason_codes),
        }


def compare_price_sources(
    provider_bars: Mapping[str, Sequence[OhlcvBar]],
    *,
    start: datetime,
    end: datetime,
    as_of: datetime,
    policy: PriceSourcePolicy = DEFAULT_PRICE_SOURCE_POLICY,
    baseline_provider_id: str | None = None,
    minimum_overlap_years: Decimal | int | str = Decimal("2"),
    stop_levels: Sequence[Decimal] = (),
    trade_path_probes: Sequence[TradePathProbe] = (),
    manual_reviews: Sequence[PriceSourceDivergenceReview] = (),
    provider_access_diagnostics: Sequence[ProviderAccessDiagnostic] = (),
    canonical_source_decision: CanonicalSourceDecision | None = None,
    top_event_count: int = 10,
) -> PriceSourceComparisonReport:
    """Compare synchronized 1h OHLCV windows across policy candidate providers."""

    policy.as_record()
    instruments_by_provider = {
        instrument.provider_id: instrument for instrument in policy.instruments
    }
    supplied_access = tuple(provider_access_diagnostics)
    unknown_provider_ids = sorted(
        (set(provider_bars) | {item.provider_id for item in supplied_access})
        - set(instruments_by_provider)
    )
    if unknown_provider_ids:
        raise ValueError(
            f"providers are not configured by {policy.version}: {unknown_provider_ids}",
        )
    window_start = require_utc_datetime(start, "start")
    window_end = require_utc_datetime(end, "end")
    signal_time = require_utc_datetime(as_of, "as_of")
    _require_hour_boundary(window_start, "start")
    _require_hour_boundary(window_end, "end")
    if window_end < window_start:
        raise ValueError("end must be >= start")
    if signal_time < window_end:
        raise ValueError("as_of must be >= end")
    if top_event_count < 1:
        raise ValueError("top_event_count must be >= 1")
    min_overlap = _non_negative_decimal(minimum_overlap_years, "minimum_overlap_years")
    baseline = baseline_provider_id or policy.canonical_candidate_provider_id
    if baseline not in instruments_by_provider:
        raise ValueError("baseline provider must be configured by the policy")
    required_provider_ids = policy.required_validation_provider_ids
    normalized_stop_levels = tuple(
        _positive_decimal(stop_level, "stop_level") for stop_level in stop_levels
    )
    normalized_trade_path_probes = tuple(trade_path_probes)
    for probe in normalized_trade_path_probes:
        probe.as_record()
    normalized = {
        provider_id: _normalized_hourly_bars(
            bars,
            provider_id=provider_id,
            expected_exchange=instruments_by_provider[provider_id].exchange,
            expected_symbol=instruments_by_provider[provider_id].symbol,
            start=window_start,
            end=window_end,
            as_of=signal_time,
        )
        for provider_id, bars in provider_bars.items()
    }
    access_diagnostics = _resolve_provider_access_diagnostics(
        policy,
        normalized,
        supplied=supplied_access,
        checked_at=signal_time,
    )

    reason_codes = []
    if not normalized or not any(normalized.values()):
        reason_codes.append("PRICE_SOURCE_POLICY_INPUT_MISSING")
    missing_required = [
        provider_id
        for provider_id in required_provider_ids
        if not normalized.get(provider_id)
    ]
    if missing_required or not normalized.get(baseline):
        reason_codes.append("PRICE_SOURCE_POLICY_REQUIRED_PROVIDER_MISSING")

    access_by_provider = {
        diagnostic.provider_id: diagnostic for diagnostic in access_diagnostics
    }
    profiles = tuple(
        _series_profile(
            provider_id,
            bars,
            instrument_policy=instruments_by_provider[provider_id],
            policy_version=policy.version,
            start=window_start,
            end=window_end,
        )
        for provider_id, bars in sorted(normalized.items())
        if bars or access_by_provider[provider_id].status == "available"
    )
    common_timestamps = _common_timestamps(
        normalized,
        provider_ids=required_provider_ids,
    )
    overlap_bar_count = len(common_timestamps)
    overlap_years = Decimal(overlap_bar_count) / Decimal(24 * 365)
    if overlap_years < min_overlap:
        reason_codes.append("PRICE_SOURCE_POLICY_OVERLAP_TOO_SHORT")

    baseline_bars = _bars_by_timestamp(normalized.get(baseline, ()))
    candidate_provider_ids = tuple(
        provider_id
        for provider_id in sorted(normalized)
        if provider_id != baseline
    )
    comparison_timestamps = expected_bar_timestamps(
        start=window_start,
        end=window_end,
        timeframe="1h",
    )
    close_diffs = _field_pct_differences(
        normalized,
        baseline_provider_id=baseline,
        timestamps=comparison_timestamps,
        field_name="close",
    )
    high_diffs = _field_pct_differences(
        normalized,
        baseline_provider_id=baseline,
        timestamps=comparison_timestamps,
        field_name="high",
    )
    low_diffs = _field_pct_differences(
        normalized,
        baseline_provider_id=baseline,
        timestamps=comparison_timestamps,
        field_name="low",
    )
    wick_diffs = _wick_ratio_differences(
        normalized,
        baseline_provider_id=baseline,
        timestamps=comparison_timestamps,
    )
    daily_by_provider = _daily_bars_by_provider(normalized, as_of=signal_time)
    weekly_by_provider = _weekly_bars_by_provider(normalized, as_of=signal_time)
    daily_return_diffs = _daily_return_differences(daily_by_provider, baseline)
    atr_diffs = _atr_differences(daily_by_provider, baseline)
    swing_counts = _swing_level_difference_counts(
        weekly_by_provider,
        baseline,
        signal_time,
    )
    breakout_counts = _breakout_reclaim_difference_counts(
        weekly_by_provider,
        baseline,
        signal_time,
    )
    stop_touch_difference_count = _stop_touch_difference_count(
        normalized,
        baseline_provider_id=baseline,
        baseline_bars=baseline_bars,
        timestamps=comparison_timestamps,
        stop_levels=normalized_stop_levels,
    )
    stop_touch_difference_count += _probe_stop_touch_difference_count(
        normalized,
        baseline_provider_id=baseline,
        probes=normalized_trade_path_probes,
    )
    mfe_diffs, mae_diffs = _mfe_mae_differences(
        normalized,
        baseline_provider_id=baseline,
        probes=normalized_trade_path_probes,
    )
    wick_high_atr, wick_low_atr, wick_diagnostics = (
        _cross_venue_wick_diagnostics(
            normalized,
            reference_provider_ids=required_provider_ids,
            baseline_provider_id=baseline,
            daily_by_provider=daily_by_provider,
            timestamps=common_timestamps,
            top_event_count=top_event_count,
        )
    )
    top_events = _top_divergence_events(
        normalized,
        baseline_provider_id=baseline,
        timestamps=comparison_timestamps,
        top_event_count=top_event_count,
    )
    reviewed = tuple(manual_reviews)
    for review in reviewed:
        review.as_record()
        _validate_manual_review_context(
            review,
            provider_bars=normalized,
            baseline_provider_id=baseline,
            reference_provider_ids=required_provider_ids,
            baseline_daily_bars=daily_by_provider.get(baseline, ()),
        )
    reviewed_event_keys = {review.event_key for review in reviewed}
    if top_events and any(
        (event.timestamp, event.provider_id, event.metric) not in reviewed_event_keys
        for event in top_events
    ):
        reason_codes.append("PRICE_SOURCE_POLICY_MANUAL_REVIEW_MISSING")
    if canonical_source_decision is None:
        reason_codes.append("PRICE_SOURCE_POLICY_CANONICAL_DECISION_MISSING")
    else:
        canonical_source_decision.as_record()
        if canonical_source_decision.provider_id != policy.canonical_candidate_provider_id:
            raise ValueError("canonical decision provider must match policy candidate")
    divergence_tiers = _build_divergence_tiers(
        close_diffs=close_diffs,
        high_diffs=high_diffs,
        low_diffs=low_diffs,
        wick_diffs=wick_diffs,
        daily_return_diffs=daily_return_diffs,
        atr_diffs=atr_diffs,
        swing_counts=swing_counts,
        breakout_counts=breakout_counts,
        stop_touch_difference_count=stop_touch_difference_count,
        mfe_diffs=mfe_diffs,
        mae_diffs=mae_diffs,
    )
    reason_codes = _dedupe_reason_codes(reason_codes)
    return PriceSourceComparisonReport(
        policy_version=policy.version,
        baseline_provider_id=baseline,
        required_provider_ids=required_provider_ids,
        candidate_provider_ids=candidate_provider_ids,
        start=window_start,
        end=window_end,
        as_of=signal_time,
        overlap_bar_count=overlap_bar_count,
        overlap_years=overlap_years,
        minimum_overlap_years=min_overlap,
        series_profiles=profiles,
        close_price_divergence=_distribution(close_diffs),
        high_price_divergence=_distribution(high_diffs),
        low_price_divergence=_distribution(low_diffs),
        extreme_wick_divergence=_distribution(wick_diffs),
        daily_return_divergence=_distribution(daily_return_diffs),
        atr_divergence=_distribution(atr_diffs),
        wick_high_atr_divergence=_distribution(wick_high_atr),
        wick_low_atr_divergence=_distribution(wick_low_atr),
        cross_venue_wick_diagnostics=wick_diagnostics,
        swing_high_difference_count=swing_counts["swing_high"],
        swing_low_difference_count=swing_counts["swing_low"],
        swing_level_difference_count=sum(swing_counts.values()),
        breakout_difference_count=breakout_counts["breakout"],
        reclaim_difference_count=breakout_counts["reclaim"],
        breakout_reclaim_difference_count=sum(breakout_counts.values()),
        stop_touch_difference_count=stop_touch_difference_count,
        mfe_divergence=_distribution(mfe_diffs),
        mae_divergence=_distribution(mae_diffs),
        mfe_mae_difference=_distribution((*mfe_diffs, *mae_diffs)),
        divergence_tiers=divergence_tiers,
        stop_levels=normalized_stop_levels,
        trade_path_probes=normalized_trade_path_probes,
        top_event_count=top_event_count,
        top_divergence_events=top_events,
        manual_reviews=reviewed,
        provider_access_diagnostics=access_diagnostics,
        canonical_source_decision=canonical_source_decision,
        reason_codes=reason_codes,
    )


def _resolve_provider_access_diagnostics(
    policy: PriceSourcePolicy,
    provider_bars: Mapping[str, Sequence[OhlcvBar]],
    *,
    supplied: Sequence[ProviderAccessDiagnostic],
    checked_at: datetime,
) -> tuple[ProviderAccessDiagnostic, ...]:
    supplied_by_provider = {}
    for diagnostic in supplied:
        diagnostic.as_record()
        if diagnostic.provider_id in supplied_by_provider:
            raise ValueError("provider access diagnostics must be unique by provider")
        if provider_bars.get(diagnostic.provider_id) and diagnostic.status != "available":
            raise ValueError(
                "provider with supplied bars cannot have unavailable access status",
            )
        supplied_by_provider[diagnostic.provider_id] = diagnostic

    diagnostics = []
    for instrument in sorted(policy.instruments, key=lambda item: item.provider_id):
        supplied_diagnostic = supplied_by_provider.get(instrument.provider_id)
        if supplied_diagnostic is not None:
            diagnostics.append(supplied_diagnostic)
            continue
        if provider_bars.get(instrument.provider_id):
            diagnostics.append(
                ProviderAccessDiagnostic(
                    provider_id=instrument.provider_id,
                    status="available",
                    checked_at=checked_at,
                    details="Point-in-time OHLCV bars were supplied to the comparison.",
                    historical_retrieval_entitled=True,
                ),
            )
        else:
            diagnostics.append(
                ProviderAccessDiagnostic(
                    provider_id=instrument.provider_id,
                    status="not_requested",
                    checked_at=checked_at,
                    details="No provider history or explicit access result was supplied.",
                ),
            )
    return tuple(diagnostics)


def _cross_venue_wick_diagnostics(
    provider_bars: Mapping[str, Sequence[OhlcvBar]],
    *,
    reference_provider_ids: Sequence[str],
    baseline_provider_id: str,
    daily_by_provider: Mapping[str, Sequence[OhlcvBar]],
    timestamps: Sequence[datetime],
    top_event_count: int,
) -> tuple[
    tuple[Decimal, ...],
    tuple[Decimal, ...],
    tuple[CrossVenueWickDiagnostic, ...],
]:
    bars_by_provider = {
        provider_id: _bars_by_timestamp(provider_bars.get(provider_id, ()))
        for provider_id in reference_provider_ids
    }
    atr_series = _atr_value_series(
        daily_by_provider.get(baseline_provider_id, ()),
        window_days=14,
    )
    atr_timestamps = tuple(sorted(atr_series))
    high_values = []
    low_values = []
    diagnostics = []
    for timestamp in timestamps:
        synchronized = {
            provider_id: bars[timestamp]
            for provider_id, bars in bars_by_provider.items()
            if timestamp in bars
        }
        if len(synchronized) < 3:
            continue
        median_high = Decimal(str(median([bar.high for bar in synchronized.values()])))
        median_low = Decimal(str(median([bar.low for bar in synchronized.values()])))
        median_close = Decimal(str(median([bar.close for bar in synchronized.values()])))
        atr_value = _latest_series_value_before(
            atr_series,
            atr_timestamps,
            timestamp.replace(hour=0, minute=0, second=0, microsecond=0),
        )
        maximum_high = max(bar.high for bar in synchronized.values())
        minimum_low = min(bar.low for bar in synchronized.values())
        maximum_high_count = sum(
            bar.high == maximum_high for bar in synchronized.values()
        )
        minimum_low_count = sum(bar.low == minimum_low for bar in synchronized.values())
        for provider_id, bar in synchronized.items():
            high_atr_divergence = (
                abs(bar.high - median_high) / atr_value
                if atr_value is not None and atr_value > 0
                else None
            )
            low_atr_divergence = (
                abs(bar.low - median_low) / atr_value
                if atr_value is not None and atr_value > 0
                else None
            )
            if high_atr_divergence is not None:
                high_values.append(high_atr_divergence)
            if low_atr_divergence is not None:
                low_values.append(low_atr_divergence)
            isolated_extreme = (
                (bar.high == maximum_high and maximum_high_count == 1)
                or (bar.low == minimum_low and minimum_low_count == 1)
            )
            flags = (
                (WICK_ANOMALY_CANDIDATE, CROSS_VENUE_UNCONFIRMED)
                if isolated_extreme
                else (CROSS_VENUE_CONFIRMED,)
            )
            diagnostics.append(
                CrossVenueWickDiagnostic(
                    timestamp=timestamp,
                    provider_id=provider_id,
                    reference_provider_ids=tuple(sorted(synchronized)),
                    provider_high=bar.high,
                    provider_low=bar.low,
                    provider_close=bar.close,
                    median_high=median_high,
                    median_low=median_low,
                    median_close=median_close,
                    atr_value=atr_value,
                    high_atr_divergence=high_atr_divergence,
                    low_atr_divergence=low_atr_divergence,
                    candidate_flags=flags,
                ),
            )
    top_diagnostics = tuple(
        sorted(
            diagnostics,
            key=lambda item: (
                max(
                    item.high_atr_divergence or Decimal("0"),
                    item.low_atr_divergence or Decimal("0"),
                ),
                item.timestamp,
                item.provider_id,
            ),
            reverse=True,
        )[:top_event_count]
    )
    return tuple(high_values), tuple(low_values), top_diagnostics


def _validate_manual_review_context(
    review: PriceSourceDivergenceReview,
    *,
    provider_bars: Mapping[str, Sequence[OhlcvBar]],
    baseline_provider_id: str,
    reference_provider_ids: Sequence[str],
    baseline_daily_bars: Sequence[OhlcvBar],
) -> None:
    baseline_bar = _bars_by_timestamp(
        provider_bars.get(baseline_provider_id, ()),
    ).get(review.timestamp)
    validator_bar = _bars_by_timestamp(
        provider_bars.get(review.provider_id, ()),
    ).get(review.timestamp)
    if baseline_bar is None or validator_bar is None:
        raise ValueError("manual review must reference supplied synchronized bars")
    if review.canonical_candidate_ohlc != PriceSourceOhlcvSnapshot.from_bar(
        baseline_bar,
    ):
        raise ValueError("manual review canonical OHLC does not match source data")
    if review.validator_ohlc != PriceSourceOhlcvSnapshot.from_bar(validator_bar):
        raise ValueError("manual review validator OHLC does not match source data")
    reference_bars = [
        bar
        for provider_id in reference_provider_ids
        if (
            bar := _bars_by_timestamp(provider_bars.get(provider_id, ())).get(
                review.timestamp,
            )
        )
        is not None
    ]
    if len(reference_bars) < 2:
        raise ValueError("manual review requires cross-provider reference bars")
    expected_medians = (
        Decimal(str(median([bar.high for bar in reference_bars]))),
        Decimal(str(median([bar.low for bar in reference_bars]))),
        Decimal(str(median([bar.close for bar in reference_bars]))),
    )
    if expected_medians != (
        review.cross_provider_median_high,
        review.cross_provider_median_low,
        review.cross_provider_median_close,
    ):
        raise ValueError("manual review cross-provider medians do not match source data")
    atr_series = _atr_value_series(baseline_daily_bars, window_days=14)
    atr_timestamps = tuple(sorted(atr_series))
    atr_value = _latest_series_value_before(
        atr_series,
        atr_timestamps,
        review.timestamp.replace(hour=0, minute=0, second=0, microsecond=0),
    )
    median_by_metric = {
        "high": review.cross_provider_median_high,
        "low": review.cross_provider_median_low,
        "close": review.cross_provider_median_close,
    }
    expected_atr_divergence = (
        abs(getattr(validator_bar, review.metric) - median_by_metric[review.metric])
        / atr_value
        if atr_value is not None and atr_value > 0
        else None
    )
    if review.atr_normalized_divergence != expected_atr_divergence:
        raise ValueError(
            "manual review ATR-normalized divergence does not match source data",
        )


def _build_divergence_tiers(
    *,
    close_diffs: Sequence[Decimal],
    high_diffs: Sequence[Decimal],
    low_diffs: Sequence[Decimal],
    wick_diffs: Sequence[Decimal],
    daily_return_diffs: Sequence[Decimal],
    atr_diffs: Sequence[Decimal],
    swing_counts: Mapping[str, int],
    breakout_counts: Mapping[str, int],
    stop_touch_difference_count: int,
    mfe_diffs: Sequence[Decimal],
    mae_diffs: Sequence[Decimal],
) -> tuple[DivergenceTierSummary, ...]:
    return (
        DivergenceTierSummary(
            tier=DIVERGENCE_TIER_PORTFOLIO,
            category="PORTFOLIO_DIVERGENCE",
            event_count=(
                stop_touch_difference_count
                + _nonzero_count(mfe_diffs)
                + _nonzero_count(mae_diffs)
            ),
            metrics=("stop_touch", "mfe", "mae"),
        ),
        DivergenceTierSummary(
            tier=DIVERGENCE_TIER_DECISION,
            category="DECISION_DIVERGENCE",
            event_count=sum(swing_counts.values()) + sum(breakout_counts.values()),
            metrics=("swing_high", "swing_low", "breakout", "reclaim"),
        ),
        DivergenceTierSummary(
            tier=DIVERGENCE_TIER_INDICATOR,
            category="INDICATOR_DIVERGENCE",
            event_count=_nonzero_count(daily_return_diffs) + _nonzero_count(atr_diffs),
            metrics=("daily_return", "atr"),
        ),
        DivergenceTierSummary(
            tier=DIVERGENCE_TIER_PRICE,
            category="PRICE_DIVERGENCE",
            event_count=(
                _nonzero_count(close_diffs)
                + _nonzero_count(high_diffs)
                + _nonzero_count(low_diffs)
                + _nonzero_count(wick_diffs)
            ),
            metrics=("close", "high", "low", "wick"),
        ),
    )


def _normalized_hourly_bars(
    bars: Sequence[OhlcvBar],
    *,
    provider_id: str,
    expected_exchange: str,
    expected_symbol: str,
    start: datetime,
    end: datetime,
    as_of: datetime,
) -> tuple[OhlcvBar, ...]:
    normalized = []
    for bar in bars:
        record = bar.as_record()
        if record["provider"] != provider_id:
            raise ValueError("provider_bars key must match OhlcvBar.provider")
        if record["exchange"] != expected_exchange:
            raise ValueError("OhlcvBar.exchange must match policy provenance")
        if record["symbol"] != expected_symbol:
            raise ValueError("OhlcvBar.symbol must match policy provenance")
        if record["timeframe"] != "1h":
            raise ValueError("price-source comparison requires 1h bars")
        _require_hour_boundary(record["timestamp"], "OhlcvBar.timestamp")
        _validate_price_bar(bar)
        if (
            start <= record["timestamp"] <= end
            and record["timestamp"] <= as_of
            and record["ingested_at"] <= as_of
        ):
            normalized.append(bar)
    return tuple(sorted(normalized, key=lambda bar: bar.timestamp))


def _series_profile(
    provider_id: str,
    bars: Sequence[OhlcvBar],
    *,
    instrument_policy: PriceSourceInstrumentPolicy,
    policy_version: str,
    start: datetime,
    end: datetime,
) -> PriceSourceSeriesProfile:
    expected_timestamps = expected_bar_timestamps(start=start, end=end, timeframe="1h")
    timestamps = [bar.timestamp for bar in bars]
    unique_timestamps = set(timestamps)
    missing_timestamps = [
        timestamp for timestamp in expected_timestamps if timestamp not in unique_timestamps
    ]
    duplicate_count = len(timestamps) - len(unique_timestamps)
    first_bar = bars[0] if bars else None
    return PriceSourceSeriesProfile(
        provider_id=provider_id,
        price_source_policy_version=policy_version,
        price_source_roles=instrument_policy.roles,
        fallback_used=False,
        exchange=first_bar.exchange if first_bar is not None else "",
        symbol=first_bar.symbol if first_bar is not None else "",
        timeframe=first_bar.timeframe if first_bar is not None else "1h",
        start=start,
        end=end,
        bar_count=len(bars),
        expected_bar_count=len(expected_timestamps),
        missing_bar_count=len(missing_timestamps),
        duplicate_bar_count=duplicate_count,
        missing_bar_rate=(
            Decimal(len(missing_timestamps)) / Decimal(len(expected_timestamps))
            if expected_timestamps
            else Decimal("0")
        ),
        largest_missing_run_hours=_largest_missing_run_hours(missing_timestamps),
        historical_coverage_days=(
            Decimal(
                int((timestamps[-1] - timestamps[0]).total_seconds()),
            )
            / Decimal(86400)
            if timestamps
            else Decimal("0")
        ),
    )


def _common_timestamps(
    provider_bars: Mapping[str, Sequence[OhlcvBar]],
    *,
    provider_ids: Sequence[str] = (),
) -> tuple[datetime, ...]:
    if provider_ids and any(
        provider_id not in provider_bars for provider_id in provider_ids
    ):
        return ()
    selected_provider_ids = tuple(provider_ids) or tuple(provider_bars)
    timestamp_sets = [
        {bar.timestamp for bar in provider_bars[provider_id]}
        for provider_id in selected_provider_ids
        if provider_bars[provider_id]
    ]
    if len(timestamp_sets) != len(selected_provider_ids):
        return ()
    return tuple(sorted(set.intersection(*timestamp_sets)))


def _bars_by_timestamp(bars: Sequence[OhlcvBar]) -> dict[datetime, OhlcvBar]:
    by_timestamp = {}
    for bar in sorted(bars, key=lambda value: (value.timestamp, value.ingested_at)):
        by_timestamp.setdefault(bar.timestamp, bar)
    return by_timestamp


def _deduplicated_bars(bars: Sequence[OhlcvBar]) -> tuple[OhlcvBar, ...]:
    return tuple(_bars_by_timestamp(bars).values())


def _field_pct_differences(
    provider_bars: Mapping[str, Sequence[OhlcvBar]],
    *,
    baseline_provider_id: str,
    timestamps: Sequence[datetime],
    field_name: str,
) -> tuple[Decimal, ...]:
    baseline_bars = _bars_by_timestamp(provider_bars.get(baseline_provider_id, ()))
    differences = []
    for provider_id, bars in provider_bars.items():
        if provider_id == baseline_provider_id:
            continue
        candidate_bars = _bars_by_timestamp(bars)
        pairwise_timestamps = sorted(
            set(timestamps) & set(baseline_bars) & set(candidate_bars)
        )
        for timestamp in pairwise_timestamps:
            base_value = getattr(baseline_bars[timestamp], field_name)
            candidate_value = getattr(candidate_bars[timestamp], field_name)
            differences.append(abs((candidate_value - base_value) / base_value))
    return tuple(differences)


def _wick_ratio_differences(
    provider_bars: Mapping[str, Sequence[OhlcvBar]],
    *,
    baseline_provider_id: str,
    timestamps: Sequence[datetime],
) -> tuple[Decimal, ...]:
    baseline_bars = _bars_by_timestamp(provider_bars.get(baseline_provider_id, ()))
    differences = []
    for provider_id, bars in provider_bars.items():
        if provider_id == baseline_provider_id:
            continue
        candidate_bars = _bars_by_timestamp(bars)
        pairwise_timestamps = sorted(
            set(timestamps) & set(baseline_bars) & set(candidate_bars)
        )
        for timestamp in pairwise_timestamps:
            differences.append(
                abs(
                    _extreme_wick_ratio(candidate_bars[timestamp])
                    - _extreme_wick_ratio(baseline_bars[timestamp])
                )
            )
    return tuple(differences)


def _top_divergence_events(
    provider_bars: Mapping[str, Sequence[OhlcvBar]],
    *,
    baseline_provider_id: str,
    timestamps: Sequence[datetime],
    top_event_count: int,
) -> tuple[PriceSourceDivergenceEvent, ...]:
    baseline_bars = _bars_by_timestamp(provider_bars.get(baseline_provider_id, ()))
    events = []
    for provider_id, bars in provider_bars.items():
        if provider_id == baseline_provider_id:
            continue
        candidate_bars = _bars_by_timestamp(bars)
        pairwise_timestamps = sorted(
            set(timestamps) & set(baseline_bars) & set(candidate_bars)
        )
        for timestamp in pairwise_timestamps:
            for metric in ("close", "high", "low"):
                base_value = getattr(baseline_bars[timestamp], metric)
                candidate_value = getattr(candidate_bars[timestamp], metric)
                absolute_difference = abs(candidate_value - base_value)
                if absolute_difference == 0:
                    continue
                percentage_difference = absolute_difference / base_value
                events.append(
                    PriceSourceDivergenceEvent(
                        timestamp=timestamp,
                        provider_id=provider_id,
                        metric=metric,
                        baseline_value=base_value,
                        provider_value=candidate_value,
                        absolute_difference=absolute_difference,
                        percentage_difference=percentage_difference,
                    )
                )
    return tuple(
        sorted(
            events,
            key=lambda event: (
                event.percentage_difference,
                event.absolute_difference,
                event.timestamp,
                event.provider_id,
                event.metric,
            ),
            reverse=True,
        )[:top_event_count]
    )


def _daily_bars_by_provider(
    provider_bars: Mapping[str, Sequence[OhlcvBar]],
    *,
    as_of: datetime,
) -> dict[str, tuple[OhlcvBar, ...]]:
    return {
        provider_id: tuple(
            bar
            for bar in build_canonical_market_bars(
                _deduplicated_bars(bars),
                data_available_at=as_of,
                timeframes=("1d",),
            )
            if bar.timeframe == "1d"
        )
        for provider_id, bars in provider_bars.items()
        if bars
    }


def _weekly_bars_by_provider(
    provider_bars: Mapping[str, Sequence[OhlcvBar]],
    *,
    as_of: datetime,
) -> dict[str, tuple[OhlcvBar, ...]]:
    return {
        provider_id: tuple(
            bar
            for bar in build_canonical_market_bars(
                _deduplicated_bars(bars),
                data_available_at=as_of,
                timeframes=("1w",),
            )
            if bar.timeframe == "1w"
        )
        for provider_id, bars in provider_bars.items()
        if bars
    }


def _daily_return_differences(
    daily_by_provider: Mapping[str, Sequence[OhlcvBar]],
    baseline_provider_id: str,
) -> tuple[Decimal, ...]:
    returns_by_provider = {
        provider_id: _daily_returns(bars)
        for provider_id, bars in daily_by_provider.items()
    }
    baseline_returns = returns_by_provider.get(baseline_provider_id, {})
    differences = []
    for provider_id, returns in returns_by_provider.items():
        if provider_id == baseline_provider_id:
            continue
        for timestamp in sorted(set(baseline_returns) & set(returns)):
            differences.append(abs(returns[timestamp] - baseline_returns[timestamp]))
    return tuple(differences)


def _atr_differences(
    daily_by_provider: Mapping[str, Sequence[OhlcvBar]],
    baseline_provider_id: str,
    *,
    window_days: int = 14,
) -> tuple[Decimal, ...]:
    atr_by_provider = {
        provider_id: _atr_fraction_series(bars, window_days=window_days)
        for provider_id, bars in daily_by_provider.items()
    }
    baseline_atr = atr_by_provider.get(baseline_provider_id, {})
    differences = []
    for provider_id, atr in atr_by_provider.items():
        if provider_id == baseline_provider_id:
            continue
        for timestamp in sorted(set(baseline_atr) & set(atr)):
            differences.append(abs(atr[timestamp] - baseline_atr[timestamp]))
    return tuple(differences)


def _swing_level_difference_counts(
    weekly_by_provider: Mapping[str, Sequence[OhlcvBar]],
    baseline_provider_id: str,
    as_of: datetime,
) -> dict[str, int]:
    levels_by_provider = {
        provider_id: detect_weekly_swing_levels(bars, as_of=as_of)
        for provider_id, bars in weekly_by_provider.items()
        if len(bars) >= 7
    }
    return {
        "swing_high": _typed_level_difference_count(
            levels_by_provider,
            baseline_provider_id=baseline_provider_id,
            level_type=WEEKLY_SWING_HIGH,
            timestamp_field="level_timestamp",
        ),
        "swing_low": _typed_level_difference_count(
            levels_by_provider,
            baseline_provider_id=baseline_provider_id,
            level_type=WEEKLY_SWING_LOW,
            timestamp_field="level_timestamp",
        ),
    }


def _breakout_reclaim_difference_counts(
    weekly_by_provider: Mapping[str, Sequence[OhlcvBar]],
    baseline_provider_id: str,
    as_of: datetime,
) -> dict[str, int]:
    breakout_by_provider = {}
    for provider_id, bars in weekly_by_provider.items():
        if len(bars) < 7:
            continue
        levels = detect_weekly_swing_levels(bars, as_of=as_of)
        breakout_by_provider[provider_id] = detect_breakout_reclaim_levels(
            levels,
            bars,
            as_of=as_of,
        )
    return {
        "breakout": _typed_level_difference_count(
            breakout_by_provider,
            baseline_provider_id=baseline_provider_id,
            level_type=BREAKOUT_LEVEL_TYPE,
            timestamp_field="confirmation_timestamp",
        ),
        "reclaim": _typed_level_difference_count(
            breakout_by_provider,
            baseline_provider_id=baseline_provider_id,
            level_type=RECLAIM_LEVEL_TYPE,
            timestamp_field="confirmation_timestamp",
        ),
    }


def _stop_touch_difference_count(
    provider_bars: Mapping[str, Sequence[OhlcvBar]],
    *,
    baseline_provider_id: str,
    baseline_bars: Mapping[datetime, OhlcvBar],
    timestamps: Sequence[datetime],
    stop_levels: Sequence[Decimal],
) -> int:
    stop_values = tuple(_positive_decimal(stop, "stop_level") for stop in stop_levels)
    if not stop_values:
        return 0
    difference_count = 0
    for provider_id, bars in provider_bars.items():
        if provider_id == baseline_provider_id:
            continue
        candidate_bars = _bars_by_timestamp(bars)
        pairwise_timestamps = sorted(
            set(timestamps) & set(baseline_bars) & set(candidate_bars)
        )
        for timestamp in pairwise_timestamps:
            for stop_level in stop_values:
                baseline_touched = _bar_touches_stop(
                    baseline_bars[timestamp],
                    stop_level,
                )
                candidate_touched = _bar_touches_stop(
                    candidate_bars[timestamp],
                    stop_level,
                )
                if baseline_touched != candidate_touched:
                    difference_count += 1
    return difference_count


def _mfe_mae_differences(
    provider_bars: Mapping[str, Sequence[OhlcvBar]],
    *,
    baseline_provider_id: str,
    probes: Sequence[TradePathProbe],
) -> tuple[tuple[Decimal, ...], tuple[Decimal, ...]]:
    mfe_differences = []
    mae_differences = []
    baseline_bars = _deduplicated_bars(
        provider_bars.get(baseline_provider_id, ()),
    )
    for probe in probes:
        baseline_path = _trade_path_metrics(baseline_bars, probe)
        if baseline_path is None:
            continue
        for provider_id, bars in provider_bars.items():
            if provider_id == baseline_provider_id:
                continue
            candidate_path = _trade_path_metrics(_deduplicated_bars(bars), probe)
            if candidate_path is None:
                continue
            mfe_differences.append(abs(candidate_path["mfe"] - baseline_path["mfe"]))
            mae_differences.append(abs(candidate_path["mae"] - baseline_path["mae"]))
    return tuple(mfe_differences), tuple(mae_differences)


def _probe_stop_touch_difference_count(
    provider_bars: Mapping[str, Sequence[OhlcvBar]],
    *,
    baseline_provider_id: str,
    probes: Sequence[TradePathProbe],
) -> int:
    baseline_bars = _deduplicated_bars(
        provider_bars.get(baseline_provider_id, ()),
    )
    difference_count = 0
    for probe in probes:
        if probe.stop_level is None:
            continue
        baseline_touched = _path_touches_probe_stop(baseline_bars, probe)
        for provider_id, bars in provider_bars.items():
            if provider_id == baseline_provider_id:
                continue
            candidate_touched = _path_touches_probe_stop(
                _deduplicated_bars(bars),
                probe,
            )
            if candidate_touched != baseline_touched:
                difference_count += 1
    return difference_count


def _path_touches_probe_stop(
    bars: Sequence[OhlcvBar],
    probe: TradePathProbe,
) -> bool:
    if probe.stop_level is None:
        return False
    stop_level = _positive_decimal(probe.stop_level, "stop_level")
    path = (
        bar
        for bar in bars
        if probe.entry_time <= bar.timestamp <= probe.exit_time
    )
    if probe.direction == "long":
        return any(bar.low <= stop_level for bar in path)
    return any(bar.high >= stop_level for bar in path)


def _daily_returns(bars: Sequence[OhlcvBar]) -> dict[datetime, Decimal]:
    ordered = sorted(bars, key=lambda bar: bar.timestamp)
    return {
        current.timestamp: (current.close / previous.close) - Decimal("1")
        for previous, current in zip(ordered, ordered[1:])
        if previous.close > 0
    }


def _atr_fraction_series(
    bars: Sequence[OhlcvBar],
    *,
    window_days: int,
) -> dict[datetime, Decimal]:
    ordered = sorted(bars, key=lambda bar: bar.timestamp)
    true_ranges = []
    for previous, current in zip(ordered, ordered[1:]):
        true_range = max(
            current.high - current.low,
            abs(current.high - previous.close),
            abs(current.low - previous.close),
        )
        true_ranges.append((current.timestamp, true_range / current.close))
    return {
        timestamp: sum((value for _, value in window), Decimal("0")) / Decimal(len(window))
        for index, (timestamp, _) in enumerate(true_ranges)
        if len(window := true_ranges[max(0, index - window_days + 1) : index + 1])
        == window_days
    }


def _atr_value_series(
    bars: Sequence[OhlcvBar],
    *,
    window_days: int,
) -> dict[datetime, Decimal]:
    ordered = sorted(bars, key=lambda bar: bar.timestamp)
    true_ranges = []
    for previous, current in zip(ordered, ordered[1:]):
        true_ranges.append(
            (
                current.timestamp,
                max(
                    current.high - current.low,
                    abs(current.high - previous.close),
                    abs(current.low - previous.close),
                ),
            ),
        )
    return {
        timestamp: sum((value for _, value in window), Decimal("0"))
        / Decimal(len(window))
        for index, (timestamp, _) in enumerate(true_ranges)
        if len(window := true_ranges[max(0, index - window_days + 1) : index + 1])
        == window_days
    }


def _latest_series_value_before(
    series: Mapping[datetime, Decimal],
    ordered_timestamps: Sequence[datetime],
    cutoff: datetime,
) -> Decimal | None:
    index = bisect_left(ordered_timestamps, cutoff)
    if index == 0:
        return None
    return series[ordered_timestamps[index - 1]]


def _trade_path_metrics(
    bars: Sequence[OhlcvBar],
    probe: TradePathProbe,
) -> dict[str, Decimal] | None:
    entry_time = require_utc_datetime(probe.entry_time, "entry_time")
    exit_time = require_utc_datetime(probe.exit_time, "exit_time")
    if exit_time < entry_time:
        raise ValueError("exit_time must be >= entry_time")
    entry_price = _positive_decimal(probe.entry_price, "entry_price")
    if probe.direction not in ("long", "short"):
        raise ValueError("direction must be 'long' or 'short'")
    path = [
        bar
        for bar in bars
        if entry_time <= bar.timestamp <= exit_time
    ]
    if not path:
        return None
    max_high = max(bar.high for bar in path)
    min_low = min(bar.low for bar in path)
    if probe.direction == "long":
        return {
            "mfe": (max_high - entry_price) / entry_price,
            "mae": (min_low - entry_price) / entry_price,
        }
    return {
        "mfe": (entry_price - min_low) / entry_price,
        "mae": (entry_price - max_high) / entry_price,
    }


def _largest_missing_run_hours(timestamps: Sequence[datetime]) -> int:
    if not timestamps:
        return 0
    largest = 1
    current = 1
    ordered = sorted(timestamps)
    for previous, timestamp in zip(ordered, ordered[1:]):
        if timestamp == next_bar_timestamp(previous, "1h"):
            current += 1
            largest = max(largest, current)
        else:
            current = 1
    return largest


def _extreme_wick_ratio(bar: OhlcvBar) -> Decimal:
    upper_wick = bar.high - max(bar.open, bar.close)
    lower_wick = min(bar.open, bar.close) - bar.low
    return max(upper_wick, lower_wick) / bar.close


def _bar_touches_stop(bar: OhlcvBar, stop_level: Decimal) -> bool:
    return bar.low <= stop_level <= bar.high


def _typed_level_difference_count(
    levels_by_provider: Mapping[str, Sequence[Any]],
    *,
    baseline_provider_id: str,
    level_type: str,
    timestamp_field: str,
) -> int:
    sets_by_provider = {
        provider_id: {
            getattr(level, timestamp_field)
            for level in levels
            if level.level_type == level_type
        }
        for provider_id, levels in levels_by_provider.items()
    }
    baseline = sets_by_provider.get(baseline_provider_id, set())
    return sum(
        len(baseline.symmetric_difference(values))
        for provider_id, values in sets_by_provider.items()
        if provider_id != baseline_provider_id
    )


def _distribution(values: Sequence[Decimal]) -> DivergenceDistribution:
    ordered = tuple(sorted(abs(value) for value in values))
    if not ordered:
        return DivergenceDistribution(
            observation_count=0,
            mean_abs=None,
            median_abs=None,
            standard_deviation_abs=None,
            p90_abs=None,
            p95_abs=None,
            p99_abs=None,
            p995_abs=None,
            max_abs=None,
        )
    mean_abs = sum(ordered, Decimal("0")) / Decimal(len(ordered))
    variance = sum(
        ((value - mean_abs) ** 2 for value in ordered),
        Decimal("0"),
    ) / Decimal(len(ordered))
    return DivergenceDistribution(
        observation_count=len(ordered),
        mean_abs=mean_abs,
        median_abs=Decimal(str(median(ordered))),
        standard_deviation_abs=variance.sqrt(),
        p90_abs=_nearest_rank_percentile(ordered, Decimal("0.90")),
        p95_abs=_nearest_rank_percentile(ordered, Decimal("0.95")),
        p99_abs=_nearest_rank_percentile(ordered, Decimal("0.99")),
        p995_abs=_nearest_rank_percentile(ordered, Decimal("0.995")),
        max_abs=ordered[-1],
    )


def _nearest_rank_percentile(
    ordered: Sequence[Decimal],
    probability: Decimal,
) -> Decimal:
    rank = int(
        (probability * Decimal(len(ordered))).to_integral_value(
            rounding=ROUND_CEILING,
        ),
    )
    return ordered[max(0, rank - 1)]


def _nonzero_count(values: Sequence[Decimal]) -> int:
    return sum(value != 0 for value in values)


def _positive_decimal(value: Decimal, name: str) -> Decimal:
    decimal_value = Decimal(str(value))
    if decimal_value <= 0:
        raise ValueError(f"{name} must be positive")
    return decimal_value


def _non_negative_decimal(value: Decimal | int | str, name: str) -> Decimal:
    decimal_value = Decimal(str(value))
    if decimal_value < 0:
        raise ValueError(f"{name} must be non-negative")
    return decimal_value


def _optional_decimal_record(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _dedupe_reason_codes(reason_codes: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(reason_codes))


def _validate_non_empty(value: str, name: str) -> None:
    if not value.strip():
        raise ValueError(f"{name} must be non-empty")


def _require_hour_boundary(value: datetime, name: str) -> None:
    if value.minute or value.second or value.microsecond:
        raise ValueError(f"{name} must be aligned to an hourly UTC boundary")


def _validate_price_bar(bar: OhlcvBar) -> None:
    prices = (bar.open, bar.high, bar.low, bar.close)
    if any(price <= 0 for price in prices):
        raise ValueError("price-source OHLC values must be positive")
    if bar.high < max(bar.open, bar.close) or bar.low > min(bar.open, bar.close):
        raise ValueError("price-source bar has impossible OHLC ordering")
    if bar.high < bar.low:
        raise ValueError("price-source bar high must be >= low")
    if bar.volume < 0:
        raise ValueError("price-source volume must be non-negative")
