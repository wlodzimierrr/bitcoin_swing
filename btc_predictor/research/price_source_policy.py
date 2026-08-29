"""Canonical BTC price-source policy and validation helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
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
    detect_breakout_reclaim_levels,
    detect_weekly_swing_levels,
)


PRICE_SOURCE_POLICY_VERSION = "PRICE_SOURCE_POLICY_V1"
REFERENCE_PRICE_ROLE = "reference_price"
PRIMARY_RAW_OHLCV_ROLE = "primary_raw_ohlcv"
SECONDARY_VALIDATION_FALLBACK_ROLE = "secondary_validation_fallback"
NONCANONICAL_SANITY_CHECK_ROLE = "noncanonical_sanity_check"
PRICE_SOURCE_PROVIDER_ROLES = (
    REFERENCE_PRICE_ROLE,
    PRIMARY_RAW_OHLCV_ROLE,
    SECONDARY_VALIDATION_FALLBACK_ROLE,
    NONCANONICAL_SANITY_CHECK_ROLE,
)
COIN_METRICS_COMMUNITY_PROVIDER_ID = "coin_metrics_community"
BITSTAMP_PROVIDER_ID = "bitstamp"
COINBASE_PROVIDER_ID = "coinbase"
YFINANCE_PROVIDER_ID = "yfinance"
REQUIRED_POLICY_PROVIDER_IDS = (
    COIN_METRICS_COMMUNITY_PROVIDER_ID,
    BITSTAMP_PROVIDER_ID,
    COINBASE_PROVIDER_ID,
)
PRICE_SOURCE_POLICY_REASON_CODES = (
    "PRICE_SOURCE_POLICY_INPUT_MISSING",
    "PRICE_SOURCE_POLICY_REQUIRED_PROVIDER_MISSING",
    "PRICE_SOURCE_POLICY_OVERLAP_TOO_SHORT",
    "PRICE_SOURCE_POLICY_MANUAL_REVIEW_MISSING",
    "PRICE_SOURCE_POLICY_FALLBACK_SPLICE_FORBIDDEN",
)
MANUAL_REVIEW_DISPOSITIONS = (
    "confirmed_source_divergence",
    "isolated_exchange_wick",
    "provider_gap_or_outage",
    "needs_follow_up",
)


@dataclass(frozen=True)
class PriceSourceInstrumentPolicy:
    provider_id: str
    provider_name: str
    role: str
    exchange: str
    symbol: str
    api_instrument: str
    timeframe: str
    reference_price_role: bool
    execution_venue: bool
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
        if self.role not in PRICE_SOURCE_PROVIDER_ROLES:
            raise ValueError(f"role must be one of {PRICE_SOURCE_PROVIDER_ROLES}")
        if self.timeframe != "1h":
            raise ValueError("price-source policy compares synchronized 1h windows")
        if self.fallback_splicing_allowed and not self.historical_fallback_policy_version:
            raise ValueError(
                "historical fallback splicing requires a policy version",
            )
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "role": self.role,
            "exchange": self.exchange,
            "symbol": self.symbol,
            "api_instrument": self.api_instrument,
            "timeframe": self.timeframe,
            "reference_price_role": self.reference_price_role,
            "execution_venue": self.execution_venue,
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
    canonical_reference_provider_id: str
    primary_raw_ohlcv_provider_id: str
    secondary_validation_fallback_provider_id: str
    noncanonical_sanity_check_provider_id: str
    instruments: tuple[PriceSourceInstrumentPolicy, ...]
    isolated_exchange_wick_rule: str
    provider_outage_fallback_rule: str
    historical_fallback_splicing_rule: str

    def as_record(self) -> dict[str, Any]:
        if self.version != PRICE_SOURCE_POLICY_VERSION:
            raise ValueError(f"version must be {PRICE_SOURCE_POLICY_VERSION}")
        provider_ids = [instrument.provider_id for instrument in self.instruments]
        if len(provider_ids) != len(set(provider_ids)):
            raise ValueError("price-source policy provider IDs must be unique")
        instruments_by_provider = {
            instrument.provider_id: instrument for instrument in self.instruments
        }
        for provider_id in REQUIRED_POLICY_PROVIDER_IDS:
            if provider_id not in instruments_by_provider:
                raise ValueError(f"required provider missing: {provider_id}")
        if self.noncanonical_sanity_check_provider_id not in instruments_by_provider:
            raise ValueError("noncanonical sanity-check provider must be configured")
        selected_provider_ids = (
            self.canonical_reference_provider_id,
            self.primary_raw_ohlcv_provider_id,
            self.secondary_validation_fallback_provider_id,
            self.noncanonical_sanity_check_provider_id,
        )
        if any(
            provider_id not in instruments_by_provider
            for provider_id in selected_provider_ids
        ):
            raise ValueError("every selected provider must have instrument provenance")
        if (
            instruments_by_provider[self.canonical_reference_provider_id].role
            != REFERENCE_PRICE_ROLE
        ):
            raise ValueError("canonical provider must have reference-price role")
        if (
            instruments_by_provider[self.primary_raw_ohlcv_provider_id].role
            != PRIMARY_RAW_OHLCV_ROLE
        ):
            raise ValueError("primary raw provider must have primary raw OHLCV role")
        if (
            instruments_by_provider[self.secondary_validation_fallback_provider_id].role
            != SECONDARY_VALIDATION_FALLBACK_ROLE
        ):
            raise ValueError(
                "secondary provider must have validation/fallback role",
            )
        if (
            instruments_by_provider[self.noncanonical_sanity_check_provider_id].role
            != NONCANONICAL_SANITY_CHECK_ROLE
        ):
            raise ValueError("sanity-check provider must have noncanonical role")
        if instruments_by_provider[
            self.canonical_reference_provider_id
        ].execution_venue:
            raise ValueError("reference-price role must be separate from execution")
        if any(instrument.fallback_splicing_allowed for instrument in self.instruments):
            raise ValueError("unversioned historical fallback splicing is prohibited")
        return {
            "version": self.version,
            "canonical_reference_provider_id": self.canonical_reference_provider_id,
            "primary_raw_ohlcv_provider_id": self.primary_raw_ohlcv_provider_id,
            "secondary_validation_fallback_provider_id": (
                self.secondary_validation_fallback_provider_id
            ),
            "noncanonical_sanity_check_provider_id": (
                self.noncanonical_sanity_check_provider_id
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
    canonical_reference_provider_id=COIN_METRICS_COMMUNITY_PROVIDER_ID,
    primary_raw_ohlcv_provider_id=BITSTAMP_PROVIDER_ID,
    secondary_validation_fallback_provider_id=COINBASE_PROVIDER_ID,
    noncanonical_sanity_check_provider_id=YFINANCE_PROVIDER_ID,
    instruments=(
        PriceSourceInstrumentPolicy(
            provider_id=COIN_METRICS_COMMUNITY_PROVIDER_ID,
            provider_name="Coin Metrics Community",
            role=REFERENCE_PRICE_ROLE,
            exchange="coin_metrics_community",
            symbol="BTC/USD",
            api_instrument="btc-usd",
            timeframe="1h",
            reference_price_role=True,
            execution_venue=False,
            fallback_splicing_allowed=False,
            historical_fallback_policy_version=None,
            api_endpoint=(
                "https://community-api.coinmetrics.io/v4/timeseries/pair-candles"
            ),
            api_practicality="next_page_url pagination; historical entitlement check required",
            access_constraints=(
                "Community catalog coverage does not guarantee unauthenticated "
                "historical timeseries access; credential-backed access or an export "
                "must be verified before final validation."
            ),
            data_semantics=(
                "Pair candles are built from Coin Metrics reference rates and do not "
                "provide exchange volume."
            ),
            notes="Canonical Phase 1 reference-price source.",
        ),
        PriceSourceInstrumentPolicy(
            provider_id=BITSTAMP_PROVIDER_ID,
            provider_name="Bitstamp",
            role=PRIMARY_RAW_OHLCV_ROLE,
            exchange="bitstamp",
            symbol="BTC/USD",
            api_instrument="btcusd",
            timeframe="1h",
            reference_price_role=False,
            execution_venue=False,
            fallback_splicing_allowed=False,
            historical_fallback_policy_version=None,
            api_endpoint="https://www.bitstamp.net/api/v2/ohlc/btcusd/",
            api_practicality=(
                "1-1000 candles per request; standard public limits are 400 requests "
                "per second and 10000 requests per 10 minutes"
            ),
            access_constraints="Public endpoint; paginate with explicit UTC start/end.",
            data_semantics="Bitstamp BTC/USD spot exchange OHLCV.",
            notes="Primary raw OHLCV provider for collector ingestion.",
        ),
        PriceSourceInstrumentPolicy(
            provider_id=COINBASE_PROVIDER_ID,
            provider_name="Coinbase",
            role=SECONDARY_VALIDATION_FALLBACK_ROLE,
            exchange="coinbase",
            symbol="BTC-USD",
            api_instrument="BTC-USD",
            timeframe="1h",
            reference_price_role=False,
            execution_venue=False,
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
            notes="Secondary validation and outage fallback source.",
        ),
        PriceSourceInstrumentPolicy(
            provider_id=YFINANCE_PROVIDER_ID,
            provider_name="yfinance",
            role=NONCANONICAL_SANITY_CHECK_ROLE,
            exchange="yfinance",
            symbol="BTC-USD",
            api_instrument="BTC-USD",
            timeframe="1h",
            reference_price_role=False,
            execution_venue=False,
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
        "Isolated provider wicks are not allowed to move structural levels, stops, "
        "or MFE/MAE unless confirmed by the reference and validation providers."
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
class TradePathProbe:
    entry_time: datetime
    exit_time: datetime
    entry_price: Decimal
    direction: str = "long"

    def as_record(self) -> dict[str, str]:
        entry_time = require_utc_datetime(self.entry_time, "entry_time")
        exit_time = require_utc_datetime(self.exit_time, "exit_time")
        if exit_time < entry_time:
            raise ValueError("exit_time must be >= entry_time")
        if self.direction not in ("long", "short"):
            raise ValueError("direction must be 'long' or 'short'")
        return {
            "entry_time": entry_time.isoformat(),
            "exit_time": exit_time.isoformat(),
            "entry_price": str(_positive_decimal(self.entry_price, "entry_price")),
            "direction": self.direction,
        }


@dataclass(frozen=True)
class DivergenceDistribution:
    observation_count: int
    mean_abs: Decimal | None
    median_abs: Decimal | None
    p95_abs: Decimal | None
    max_abs: Decimal | None

    def as_record(self) -> dict[str, str | int | None]:
        return {
            "observation_count": self.observation_count,
            "mean_abs": _optional_decimal_record(self.mean_abs),
            "median_abs": _optional_decimal_record(self.median_abs),
            "p95_abs": _optional_decimal_record(self.p95_abs),
            "max_abs": _optional_decimal_record(self.max_abs),
        }


@dataclass(frozen=True)
class PriceSourceSeriesProfile:
    provider_id: str
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
class PriceSourceDivergenceReview:
    timestamp: datetime
    provider_id: str
    metric: str
    disposition: str
    notes: str

    @property
    def event_key(self) -> tuple[datetime, str, str]:
        return (
            require_utc_datetime(self.timestamp, "timestamp"),
            self.provider_id,
            self.metric,
        )

    def as_record(self) -> dict[str, str]:
        if self.metric not in ("close", "high", "low"):
            raise ValueError("manual review metric must be close, high, or low")
        if self.disposition not in MANUAL_REVIEW_DISPOSITIONS:
            raise ValueError(
                f"manual review disposition must be one of {MANUAL_REVIEW_DISPOSITIONS}",
            )
        _validate_non_empty(self.provider_id, "provider_id")
        _validate_non_empty(self.notes, "notes")
        return {
            "timestamp": self.event_key[0].isoformat(),
            "provider_id": self.provider_id,
            "metric": self.metric,
            "disposition": self.disposition,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class PriceSourceComparisonReport:
    policy_version: str
    baseline_provider_id: str
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
    swing_level_difference_count: int
    breakout_reclaim_difference_count: int
    stop_touch_difference_count: int
    mfe_mae_difference: DivergenceDistribution
    stop_levels: tuple[Decimal, ...]
    trade_path_probes: tuple[TradePathProbe, ...]
    top_event_count: int
    top_divergence_events: tuple[PriceSourceDivergenceEvent, ...]
    manual_reviews: tuple[PriceSourceDivergenceReview, ...]
    reason_codes: tuple[str, ...]

    @property
    def policy_decision_ready(self) -> bool:
        return not self.reason_codes

    def as_record(self) -> dict[str, Any]:
        return {
            "policy_version": self.policy_version,
            "baseline_provider_id": self.baseline_provider_id,
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
            "swing_level_difference_count": self.swing_level_difference_count,
            "breakout_reclaim_difference_count": (
                self.breakout_reclaim_difference_count
            ),
            "stop_touch_difference_count": self.stop_touch_difference_count,
            "mfe_mae_difference": self.mfe_mae_difference.as_record(),
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
            "policy_decision_ready": self.policy_decision_ready,
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
    top_event_count: int = 10,
) -> PriceSourceComparisonReport:
    """Compare synchronized 1h OHLCV windows across policy candidate providers."""

    policy.as_record()
    instruments_by_provider = {
        instrument.provider_id: instrument for instrument in policy.instruments
    }
    unknown_provider_ids = sorted(set(provider_bars) - set(instruments_by_provider))
    if unknown_provider_ids:
        raise ValueError(
            f"providers are not configured by {policy.version}: {unknown_provider_ids}",
        )
    window_start = require_utc_datetime(start, "start")
    window_end = require_utc_datetime(end, "end")
    signal_time = require_utc_datetime(as_of, "as_of")
    if window_end < window_start:
        raise ValueError("end must be >= start")
    if signal_time < window_end:
        raise ValueError("as_of must be >= end")
    if top_event_count < 1:
        raise ValueError("top_event_count must be >= 1")
    min_overlap = _non_negative_decimal(minimum_overlap_years, "minimum_overlap_years")
    baseline = baseline_provider_id or policy.canonical_reference_provider_id
    if baseline not in instruments_by_provider:
        raise ValueError("baseline provider must be configured by the policy")
    required_provider_ids = (
        policy.canonical_reference_provider_id,
        policy.primary_raw_ohlcv_provider_id,
        policy.secondary_validation_fallback_provider_id,
    )
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

    profiles = tuple(
        _series_profile(
            provider_id,
            bars,
            start=window_start,
            end=window_end,
        )
        for provider_id, bars in sorted(normalized.items())
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
    top_events = _top_divergence_events(
        normalized,
        baseline_provider_id=baseline,
        timestamps=comparison_timestamps,
        top_event_count=top_event_count,
    )
    reviewed = tuple(manual_reviews)
    for review in reviewed:
        review.as_record()
    reviewed_event_keys = {review.event_key for review in reviewed}
    if top_events and any(
        (event.timestamp, event.provider_id, event.metric) not in reviewed_event_keys
        for event in top_events
    ):
        reason_codes.append("PRICE_SOURCE_POLICY_MANUAL_REVIEW_MISSING")
    daily_by_provider = _daily_bars_by_provider(normalized, as_of=signal_time)
    weekly_by_provider = _weekly_bars_by_provider(normalized, as_of=signal_time)
    reason_codes = _dedupe_reason_codes(reason_codes)
    return PriceSourceComparisonReport(
        policy_version=policy.version,
        baseline_provider_id=baseline,
        candidate_provider_ids=candidate_provider_ids,
        start=window_start,
        end=window_end,
        as_of=signal_time,
        overlap_bar_count=overlap_bar_count,
        overlap_years=overlap_years,
        minimum_overlap_years=min_overlap,
        series_profiles=profiles,
        close_price_divergence=_distribution(close_diffs),
        high_price_divergence=_distribution(
            _field_pct_differences(
                normalized,
                baseline_provider_id=baseline,
                timestamps=comparison_timestamps,
                field_name="high",
            )
        ),
        low_price_divergence=_distribution(
            _field_pct_differences(
                normalized,
                baseline_provider_id=baseline,
                timestamps=comparison_timestamps,
                field_name="low",
            )
        ),
        extreme_wick_divergence=_distribution(
            _wick_ratio_differences(
                normalized,
                baseline_provider_id=baseline,
                timestamps=comparison_timestamps,
            )
        ),
        daily_return_divergence=_distribution(
            _daily_return_differences(daily_by_provider, baseline),
        ),
        atr_divergence=_distribution(_atr_differences(daily_by_provider, baseline)),
        swing_level_difference_count=_swing_level_difference_count(
            weekly_by_provider,
            baseline,
            signal_time,
        ),
        breakout_reclaim_difference_count=_breakout_reclaim_difference_count(
            weekly_by_provider,
            baseline,
            signal_time,
        ),
        stop_touch_difference_count=_stop_touch_difference_count(
            normalized,
            baseline_provider_id=baseline,
            baseline_bars=baseline_bars,
            timestamps=comparison_timestamps,
            stop_levels=normalized_stop_levels,
        ),
        mfe_mae_difference=_distribution(
            _mfe_mae_differences(
                normalized,
                baseline_provider_id=baseline,
                probes=normalized_trade_path_probes,
            )
        ),
        stop_levels=normalized_stop_levels,
        trade_path_probes=normalized_trade_path_probes,
        top_event_count=top_event_count,
        top_divergence_events=top_events,
        manual_reviews=reviewed,
        reason_codes=reason_codes,
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


def _swing_level_difference_count(
    weekly_by_provider: Mapping[str, Sequence[OhlcvBar]],
    baseline_provider_id: str,
    as_of: datetime,
) -> int:
    levels_by_provider = {
        provider_id: {
            (level.level_type, level.level_timestamp)
            for level in detect_weekly_swing_levels(bars, as_of=as_of)
        }
        for provider_id, bars in weekly_by_provider.items()
        if len(bars) >= 7
    }
    return _set_difference_count(levels_by_provider, baseline_provider_id)


def _breakout_reclaim_difference_count(
    weekly_by_provider: Mapping[str, Sequence[OhlcvBar]],
    baseline_provider_id: str,
    as_of: datetime,
) -> int:
    breakout_by_provider = {}
    for provider_id, bars in weekly_by_provider.items():
        if len(bars) < 7:
            continue
        levels = detect_weekly_swing_levels(bars, as_of=as_of)
        breakout_by_provider[provider_id] = {
            (level.level_type, level.confirmation_timestamp)
            for level in detect_breakout_reclaim_levels(levels, bars, as_of=as_of)
        }
    return _set_difference_count(breakout_by_provider, baseline_provider_id)


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
) -> tuple[Decimal, ...]:
    differences = []
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
            differences.append(abs(candidate_path["mfe"] - baseline_path["mfe"]))
            differences.append(abs(candidate_path["mae"] - baseline_path["mae"]))
    return tuple(differences)


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


def _set_difference_count(
    sets_by_provider: Mapping[str, set[tuple[Any, ...]]],
    baseline_provider_id: str,
) -> int:
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
            p95_abs=None,
            max_abs=None,
        )
    return DivergenceDistribution(
        observation_count=len(ordered),
        mean_abs=sum(ordered, Decimal("0")) / Decimal(len(ordered)),
        median_abs=Decimal(str(median(ordered))),
        p95_abs=ordered[min(len(ordered) - 1, int(len(ordered) * Decimal("0.95")))],
        max_abs=ordered[-1],
    )


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
