"""Frozen development and external validation for BTC_REFERENCE_COMPOSITE_V1."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from statistics import median
from typing import Any

from sqlalchemy import create_engine, func, select

from btc_predictor.data import (
    OhlcvBar,
    build_canonical_market_bars,
    expected_bar_timestamps,
    require_utc_datetime,
)
from btc_predictor.db.derived import (
    btc_reference_composite,
    build_reference_composite_insert_ignore,
)
from btc_predictor.features.rolling import average_true_range
from btc_predictor.levels import (
    BREAKOUT_LEVEL_TYPE,
    RECLAIM_LEVEL_TYPE,
    WEEKLY_SWING_HIGH,
    WEEKLY_SWING_LOW,
    detect_breakout_reclaim_levels,
    detect_weekly_swing_levels,
)
from btc_predictor.research.btc019_empirical import (
    _database_url_from_environment,
    build_weekly_trade_path_probes,
    load_raw_history,
)
from btc_predictor.research.price_source_policy import TradePathProbe
from btc_predictor.research.reference_composite import (
    BITFINEX_PROVIDER_ID,
    BITSTAMP_PROVIDER_ID,
    CLIPPED_CENTER_VERSION,
    COINBASE_PROVIDER_ID,
    CONFIRMATION_TOLERANCE_ATR_GRID,
    CONFIRMED_EXTREMES_VERSION,
    DEFAULT_COMPOSITE_METHOD_DEFINITIONS,
    DEFAULT_DECISION_DELAY,
    DEFAULT_REFERENCE_COMPOSITE_POLICY,
    MEDIAN_OHLC_VERSION,
    REFERENCE_COMPOSITE_POLICY_VERSION,
    REFERENCE_DEGRADED,
    REQUIRED_COMPOSITE_PROVIDER_IDS,
    CompositeReferenceObservation,
    build_composite_observation,
    method_definition,
    provider_candle_input,
)


DEFINITION_SCHEMA_VERSION = "BTC_REFERENCE_COMPOSITE_DEFINITION_V1"
EMPIRICAL_REPORT_SCHEMA_VERSION = "BTC_REFERENCE_COMPOSITE_EMPIRICAL_V1"
DECISION_SCHEMA_VERSION = "BTC_REFERENCE_COMPOSITE_DECISION_V1"
PRIMARY_METHOD_VERSION = MEDIAN_OHLC_VERSION
PRIMARY_TOLERANCE_ATR = Decimal("0.15")
DEVELOPMENT_START = datetime(2023, 1, 1, tzinfo=UTC)
DEVELOPMENT_END = datetime(2025, 12, 31, 23, tzinfo=UTC)
EXTERNAL_WARMUP_START = datetime(2019, 12, 1, tzinfo=UTC)
EXTERNAL_START = datetime(2020, 1, 1, tzinfo=UTC)
EXTERNAL_END = datetime(2022, 12, 31, 23, tzinfo=UTC)
ATR_BOOTSTRAP_METHOD_VERSION = "ATR_BOOTSTRAP_MEDIAN_OHLC_V1"
KNOWN_DEVELOPMENT_EVENTS = (
    {
        "timestamp": datetime(2023, 3, 24, 14, tzinfo=UTC),
        "classification": "ISOLATED_VENUE_EXTREME",
        "description": "Bitstamp isolated high",
        "extreme": "high",
    },
    {
        "timestamp": datetime(2023, 8, 17, 21, tzinfo=UTC),
        "classification": "CROSS_MARKET_MOVE",
        "description": "Cross-market selloff with Bitstamp shallower downside",
        "extreme": "low",
    },
    {
        "timestamp": datetime(2024, 12, 5, 22, tzinfo=UTC),
        "classification": "ISOLATED_VENUE_EXTREME",
        "description": "Bitfinex isolated downside wick",
        "extreme": "low",
    },
    {
        "timestamp": datetime(2025, 4, 2, 4, tzinfo=UTC),
        "classification": "ISOLATED_VENUE_EXTREME",
        "description": "Bitstamp isolated downside wick",
        "extreme": "low",
    },
    {
        "timestamp": datetime(2025, 10, 10, 21, tzinfo=UTC),
        "classification": "CROSS_MARKET_MOVE",
        "description": "Cross-market selloff and consensus stop hit",
        "extreme": "low",
        "reviewed_stop": Decimal("107270"),
    },
)
PREDECLARED_APPROVAL_GATES = {
    "external_period_minimum_days": 730,
    "external_usable_reference_rate_minimum": Decimal("0.995"),
    "external_degraded_reference_rate_maximum": Decimal("0.005"),
    "external_atr_median_abs_divergence_maximum": Decimal("0.02"),
    "external_atr_p95_abs_divergence_maximum": Decimal("0.10"),
    "external_combined_swing_disagreement_rate_maximum": Decimal("0.10"),
    "external_stop_disagreement_rate_maximum": Decimal("0.01"),
    "known_isolated_events_rejected_required": 3,
    "known_cross_market_events_represented_required": 2,
    "october_2025_consensus_stop_must_be_touched": True,
    "all_tolerance_grid_variants_must_pass_known_event_gate": True,
}


@dataclass(frozen=True)
class PeriodAnalysis:
    report: dict[str, Any]
    primary_observations: tuple[CompositeReferenceObservation, ...]


def frozen_candidate_definition() -> dict[str, Any]:
    """Return the immutable protocol recorded before external inspection."""

    policy = DEFAULT_REFERENCE_COMPOSITE_POLICY.as_record()
    return {
        "schema_version": DEFINITION_SCHEMA_VERSION,
        "reference_policy_version": REFERENCE_COMPOSITE_POLICY_VERSION,
        "status": "RESEARCH",
        "canonical_reference_role": (
            "structural and backtest reference; independent of execution venue"
        ),
        "raw_source_mutation_allowed": False,
        "historical_provider_splicing_allowed": False,
        "policy": policy,
        "candidate_methods": [
            definition.as_record()
            for definition in DEFAULT_COMPOSITE_METHOD_DEFINITIONS
        ],
        "primary_candidate_method_version": PRIMARY_METHOD_VERSION,
        "extreme_methods_primary_confirmation_tolerance_atr": str(
            PRIMARY_TOLERANCE_ATR,
        ),
        "sensitivity_tolerance_atr_grid": [
            str(value) for value in CONFIRMATION_TOLERANCE_ATR_GRID
        ],
        "atr_definition": {
            "method_version": ATR_BOOTSTRAP_METHOD_VERSION,
            "source": "median OHLC of at least two synchronized venues",
            "session": "00:00 UTC daily",
            "window_days": DEFAULT_REFERENCE_COMPOSITE_POLICY.atr_window_days,
            "point_in_time": "previous completed daily ATR only",
        },
        "availability_assumption_for_historical_public_api_data": (
            "Each final candle is available at bar close; the composite decision "
            "is fixed at close plus five minutes. Historical API archives cannot "
            "reconstruct provider publication latency, which remains a limitation."
        ),
        "development_period": {
            "start": DEVELOPMENT_START.isoformat(),
            "end": DEVELOPMENT_END.isoformat(),
            "status": "previously inspected development sample",
        },
        "external_validation_protocol": {
            "warmup_start": EXTERNAL_WARMUP_START.isoformat(),
            "evaluation_start": EXTERNAL_START.isoformat(),
            "evaluation_end": EXTERNAL_END.isoformat(),
            "retuning_after_inspection_allowed": False,
        },
        "approval_gates": _json_safe(PREDECLARED_APPROVAL_GATES),
        "price_source_policy_change_in_scope": False,
        "recommended_future_policy_version_if_approved": "PRICE_SOURCE_POLICY_V2",
    }


def freeze_candidate_definition(path: Path, *, frozen_at: datetime) -> dict[str, Any]:
    payload = {
        **frozen_candidate_definition(),
        "frozen_at": require_utc_datetime(frozen_at, "frozen_at").isoformat(),
    }
    payload["definition_sha256"] = _payload_sha256(payload)
    _write_json_exclusive(path, payload)
    return payload


def analyze_period(
    raw_dir: Path,
    *,
    evaluation_start: datetime,
    evaluation_end: datetime,
    sample_name: str,
) -> PeriodAnalysis:
    """Evaluate all six references and the frozen tolerance grid."""

    start = require_utc_datetime(evaluation_start, "evaluation_start")
    end = require_utc_datetime(evaluation_end, "evaluation_end")
    if end < start:
        raise ValueError("evaluation_end must be >= evaluation_start")
    provider_bars = _load_provider_histories(raw_dir)
    trailing_atr = _prior_daily_atr_by_hour(provider_bars)
    observations_by_method = {
        version: _build_composite_history(
            provider_bars,
            method_version=version,
            tolerance_atr=PRIMARY_TOLERANCE_ATR,
            trailing_atr=trailing_atr,
        )
        for version in (
            MEDIAN_OHLC_VERSION,
            CONFIRMED_EXTREMES_VERSION,
            CLIPPED_CENTER_VERSION,
        )
    }
    evaluation_timestamps = set(
        expected_bar_timestamps(start=start, end=end, timeframe="1h"),
    )
    filtered_provider_bars = {
        provider_id: tuple(
            bar for bar in bars if bar.timestamp in evaluation_timestamps
        )
        for provider_id, bars in provider_bars.items()
    }
    filtered_observations = {
        version: tuple(
            item
            for item in observations
            if item.observation_time in evaluation_timestamps
        )
        for version, observations in observations_by_method.items()
    }
    series = {
        **filtered_provider_bars,
        **{
            version: tuple(
                item.as_ohlcv_bar() for item in observations if item.usable
            )
            for version, observations in filtered_observations.items()
        },
    }
    consensus_closes = _consensus_values(filtered_provider_bars, "close")
    structural = _structural_comparison(series)
    bootstrap = tuple(
        bar
        for bar in _bootstrap_median_bars(provider_bars)
        if start - timedelta(days=28) <= bar.timestamp <= end
    )
    probe_start = max(
        start - timedelta(days=28),
        min((bar.timestamp for bar in bootstrap), default=start),
    )
    probes = build_weekly_trade_path_probes(
        bootstrap,
        start=probe_start,
        end=end,
    )
    path_analysis = _trade_path_comparison(series, probes)
    atr_analysis = _atr_comparison(series)
    profiles = {
        series_id: _series_profile(
            series_id,
            bars,
            expected_count=len(evaluation_timestamps),
            consensus_closes=consensus_closes,
            observations=filtered_observations.get(series_id),
        )
        for series_id, bars in series.items()
    }
    known_events = _known_event_analysis(
        series,
        filtered_provider_bars,
        structural=structural,
        period_start=start,
        period_end=end,
    )
    tolerance_grid = _tolerance_grid_analysis(
        provider_bars,
        evaluation_timestamps=evaluation_timestamps,
        trailing_atr=trailing_atr,
        provider_series=filtered_provider_bars,
        probes=probes,
    )
    candidate_differences = _candidate_to_candidate_comparison(
        series,
        structural=structural,
        probes=probes,
    )
    report = {
        "schema_version": EMPIRICAL_REPORT_SCHEMA_VERSION,
        "reference_policy_version": REFERENCE_COMPOSITE_POLICY_VERSION,
        "sample_name": sample_name,
        "evaluation_start": start.isoformat(),
        "evaluation_end": end.isoformat(),
        "evaluation_hour_count": len(evaluation_timestamps),
        "raw_artifacts": _raw_artifact_evidence(raw_dir),
        "series_profiles": profiles,
        "atr_comparison": atr_analysis,
        "structural_comparison": structural,
        "trade_path_comparison": path_analysis,
        "known_event_analysis": known_events,
        "tolerance_grid": tolerance_grid,
        "candidate_to_candidate_comparison": candidate_differences,
        "material_disagreement_events": _material_disagreement_events(
            filtered_provider_bars,
            filtered_observations[PRIMARY_METHOD_VERSION],
            limit=20,
        ),
        "point_in_time_statement": (
            "All composite inputs satisfy provider available_at <= bar close + "
            "five minutes. ATR uses only prior completed daily observations."
        ),
    }
    return PeriodAnalysis(
        report=report,
        primary_observations=tuple(
            item
            for observations in filtered_observations.values()
            for item in observations
        ),
    )


def persist_composite_observations(
    database_url: str,
    observations: Sequence[CompositeReferenceObservation],
    *,
    batch_size: int = 1_000,
) -> int:
    """Persist primary candidate observations without changing an existing row."""

    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    if not observations:
        raise ValueError("observations must contain at least one composite record")
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            count_statement = (
                select(func.count())
                .select_from(btc_reference_composite)
                .where(
                    btc_reference_composite.c.reference_policy_version
                    == REFERENCE_COMPOSITE_POLICY_VERSION,
                    btc_reference_composite.c.observation_time
                    >= min(item.observation_time for item in observations),
                    btc_reference_composite.c.observation_time
                    <= max(item.observation_time for item in observations),
                )
            )
            count_before = int(connection.execute(count_statement).scalar_one())
            for offset in range(0, len(observations), batch_size):
                rows = [
                    item.as_database_record()
                    for item in observations[offset : offset + batch_size]
                ]
                if not rows:
                    continue
                connection.execute(build_reference_composite_insert_ignore(rows))
            count_after = int(connection.execute(count_statement).scalar_one())
        return count_after - count_before
    finally:
        engine.dispose()


def build_final_decision(
    development: Mapping[str, Any],
    external: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply the frozen gate without retuning candidate semantics."""

    primary = PRIMARY_METHOD_VERSION
    development_events = development["known_event_analysis"]["summary_by_series"][primary]
    external_profile = external["series_profiles"][primary]
    external_atr = external["atr_comparison"][primary]
    external_structure = external["structural_comparison"][primary]
    external_paths = external["trade_path_comparison"][primary]
    external_days = (
        datetime.fromisoformat(external["evaluation_end"])
        - datetime.fromisoformat(external["evaluation_start"])
    ).days + 1
    checks = {
        "external_period_sufficient": external_days
        >= PREDECLARED_APPROVAL_GATES["external_period_minimum_days"],
        "external_usable_reference_rate": Decimal(
            external_profile["usable_reference_rate"],
        )
        >= PREDECLARED_APPROVAL_GATES["external_usable_reference_rate_minimum"],
        "external_degraded_reference_rate": Decimal(
            external_profile["degraded_reference_rate"],
        )
        <= PREDECLARED_APPROVAL_GATES["external_degraded_reference_rate_maximum"],
        "external_atr_p95_abs_divergence": _optional_decimal_lte(
            external_atr["abs_fractional_divergence_vs_venue_consensus"]["p95_abs"],
            PREDECLARED_APPROVAL_GATES[
                "external_atr_p95_abs_divergence_maximum"
            ],
        ),
        "external_atr_median_abs_divergence": _optional_decimal_lte(
            external_atr["abs_fractional_divergence_vs_venue_consensus"][
                "median_abs"
            ],
            PREDECLARED_APPROVAL_GATES[
                "external_atr_median_abs_divergence_maximum"
            ],
        ),
        "external_combined_swing_disagreement_rate": Decimal(
            external_structure["combined_swing"]["disagreement_rate"],
        )
        <= PREDECLARED_APPROVAL_GATES[
            "external_combined_swing_disagreement_rate_maximum"
        ],
        "external_stop_disagreement_rate": Decimal(
            external_paths["stop_disagreement_rate"],
        )
        <= PREDECLARED_APPROVAL_GATES["external_stop_disagreement_rate_maximum"],
        "known_isolated_events_rejected": development_events[
            "isolated_extremes_rejected"
        ]
        >= PREDECLARED_APPROVAL_GATES["known_isolated_events_rejected_required"],
        "known_cross_market_events_represented": development_events[
            "cross_market_moves_represented"
        ]
        >= PREDECLARED_APPROVAL_GATES[
            "known_cross_market_events_represented_required"
        ],
        "october_2025_consensus_stop_touched": development_events[
            "october_2025_stop_touched"
        ],
        "tolerance_grid_known_event_gate": all(
            item["known_event_gate_passed"]
            for method_items in development["tolerance_grid"].values()
            for item in method_items
        ),
    }
    if all(checks.values()):
        decision = "APPROVED"
        rationale = (
            "The frozen confirmed-extremes candidate passed every predeclared "
            "development and untouched external-validation gate."
        )
    elif not (
        checks["known_isolated_events_rejected"]
        and checks["known_cross_market_events_represented"]
        and checks["october_2025_consensus_stop_touched"]
    ):
        decision = "REJECTED"
        rationale = (
            "The primary candidate failed a critical known-event discrimination "
            "gate and is not suitable as a canonical structural reference."
        )
    else:
        decision = "RESEARCH_INCONCLUSIVE"
        rationale = (
            "The primary candidate handled the critical known events but did not "
            "pass every predeclared external robustness gate without retuning."
        )
    return {
        "schema_version": DECISION_SCHEMA_VERSION,
        "reference_policy_version": REFERENCE_COMPOSITE_POLICY_VERSION,
        "primary_method_version": primary,
        "decision": decision,
        "gate_results": checks,
        "gate_values": {
            "external_usable_reference_rate": external_profile[
                "usable_reference_rate"
            ],
            "external_degraded_reference_rate": external_profile[
                "degraded_reference_rate"
            ],
            "external_atr_p95_abs_divergence": external_atr[
                "abs_fractional_divergence_vs_venue_consensus"
            ]["p95_abs"],
            "external_atr_median_abs_divergence": external_atr[
                "abs_fractional_divergence_vs_venue_consensus"
            ]["median_abs"],
            "external_combined_swing_disagreement_rate": external_structure[
                "combined_swing"
            ]["disagreement_rate"],
            "external_stop_disagreement_rate": external_paths[
                "stop_disagreement_rate"
            ],
        },
        "rationale": rationale,
        "btc019_impact": (
            "BTC-019 remains IN PROGRESS. Bitstamp remains suitable as immutable "
            "primary raw OHLCV but remains rejected as the sole canonical reference."
        ),
        "price_source_policy_action": (
            "Do not mutate PRICE_SOURCE_POLICY_V1 and do not migrate a composite "
            "while this decision is inconclusive. Any future approved promotion "
            "requires a separately reviewed PRICE_SOURCE_POLICY_V2 migration."
        ),
    }


def _load_provider_histories(raw_dir: Path) -> dict[str, tuple[OhlcvBar, ...]]:
    histories = {
        provider_id: load_raw_history(
            raw_dir / f"{provider_id}_btc_usd_1h.jsonl.gz",
        )
        for provider_id in REQUIRED_COMPOSITE_PROVIDER_IDS
    }
    if not all(histories.values()):
        raise ValueError("all required provider histories must contain observations")
    return histories


def _build_composite_history(
    provider_bars: Mapping[str, Sequence[OhlcvBar]],
    *,
    method_version: str,
    tolerance_atr: Decimal,
    trailing_atr: Mapping[datetime, Decimal],
) -> tuple[CompositeReferenceObservation, ...]:
    by_provider = {
        provider_id: {bar.timestamp: bar for bar in bars}
        for provider_id, bars in provider_bars.items()
    }
    timestamps = sorted(set().union(*(set(items) for items in by_provider.values())))
    method = method_definition(method_version, tolerance_atr=tolerance_atr)
    observations = []
    for timestamp in timestamps:
        inputs = tuple(
            provider_candle_input(by_provider[provider_id][timestamp])
            for provider_id in REQUIRED_COMPOSITE_PROVIDER_IDS
            if timestamp in by_provider[provider_id]
        )
        observations.append(
            build_composite_observation(
                inputs,
                observation_time=timestamp,
                decision_time=(
                    timestamp + timedelta(hours=1) + DEFAULT_DECISION_DELAY
                ),
                method=method,
                trailing_atr=trailing_atr.get(timestamp),
            ),
        )
    return tuple(observations)


def _bootstrap_median_bars(
    provider_bars: Mapping[str, Sequence[OhlcvBar]],
) -> tuple[OhlcvBar, ...]:
    by_provider = {
        provider_id: {bar.timestamp: bar for bar in bars}
        for provider_id, bars in provider_bars.items()
    }
    timestamps = sorted(set().union(*(set(items) for items in by_provider.values())))
    result = []
    for timestamp in timestamps:
        bars = [
            by_provider[provider_id][timestamp]
            for provider_id in REQUIRED_COMPOSITE_PROVIDER_IDS
            if timestamp in by_provider[provider_id]
        ]
        if len(bars) < 2:
            continue
        result.append(
            OhlcvBar(
                timestamp=timestamp,
                exchange="cross_venue_reference",
                symbol="BTC/USD",
                timeframe="1h",
                open=_median([bar.open for bar in bars]),
                high=_median([bar.high for bar in bars]),
                low=_median([bar.low for bar in bars]),
                close=_median([bar.close for bar in bars]),
                volume=Decimal("0"),
                provider=ATR_BOOTSTRAP_METHOD_VERSION.lower(),
                ingested_at=timestamp + timedelta(hours=1),
            ),
        )
    return tuple(result)


def _prior_daily_atr_by_hour(
    provider_bars: Mapping[str, Sequence[OhlcvBar]],
) -> dict[datetime, Decimal]:
    bootstrap = _bootstrap_median_bars(provider_bars)
    as_of = max(bar.ingested_at for bar in bootstrap) + timedelta(days=1)
    daily = tuple(
        bar
        for bar in build_canonical_market_bars(
            bootstrap,
            data_available_at=as_of,
            timeframes=("1d",),
        )
        if bar.timeframe == "1d"
    )
    values = average_true_range(
        daily,
        window=DEFAULT_REFERENCE_COMPOSITE_POLICY.atr_window_days,
    )
    atr_by_completed_day = {
        bar.timestamp: value
        for bar, value in zip(daily, values)
        if value is not None
    }
    result = {}
    last_atr: Decimal | None = None
    for timestamp in sorted(bar.timestamp for bar in bootstrap):
        prior_day = timestamp.replace(hour=0) - timedelta(days=1)
        if prior_day in atr_by_completed_day:
            last_atr = atr_by_completed_day[prior_day]
        if last_atr is not None:
            result[timestamp] = last_atr
    return result


def _series_profile(
    series_id: str,
    bars: Sequence[OhlcvBar],
    *,
    expected_count: int,
    consensus_closes: Mapping[datetime, Decimal],
    observations: Sequence[CompositeReferenceObservation] | None,
) -> dict[str, Any]:
    close_differences = [
        abs(bar.close - consensus_closes[bar.timestamp])
        / consensus_closes[bar.timestamp]
        for bar in bars
        if bar.timestamp in consensus_closes
    ]
    if observations is None:
        observed_count = len(bars)
        degraded = 0
        quality_counts: dict[str, int] = {}
    else:
        observed_count = sum(item.usable for item in observations)
        degraded = sum(
            item.quality_state == REFERENCE_DEGRADED for item in observations
        )
        quality_counts = dict(Counter(item.quality_state for item in observations))
    return {
        "series_id": series_id,
        "expected_hour_count": expected_count,
        "usable_hour_count": observed_count,
        "missing_reference_bar_count": expected_count - observed_count,
        "usable_reference_rate": _ratio(observed_count, expected_count),
        "degraded_reference_bar_count": degraded,
        "degraded_reference_rate": _ratio(degraded, expected_count),
        "quality_state_counts": quality_counts,
        "close_abs_fractional_divergence_vs_venue_consensus": _distribution(
            close_differences,
        ),
    }


def _structural_comparison(
    series: Mapping[str, Sequence[OhlcvBar]],
) -> dict[str, Any]:
    as_of = max(
        bar.ingested_at for bars in series.values() for bar in bars
    ) + timedelta(days=1)
    weekly = {
        series_id: tuple(
            bar
            for bar in build_canonical_market_bars(
                bars,
                data_available_at=as_of,
                timeframes=("1w",),
            )
            if bar.timeframe == "1w"
        )
        for series_id, bars in series.items()
    }
    swings = {
        series_id: detect_weekly_swing_levels(bars, as_of=as_of)
        for series_id, bars in weekly.items()
    }
    breakout_reclaim = {
        series_id: detect_breakout_reclaim_levels(
            swings[series_id],
            weekly[series_id],
            as_of=as_of,
        )
        for series_id in series
    }
    specs = {
        "swing_high": (swings, WEEKLY_SWING_HIGH, "level_timestamp"),
        "swing_low": (swings, WEEKLY_SWING_LOW, "level_timestamp"),
        "breakout": (
            breakout_reclaim,
            BREAKOUT_LEVEL_TYPE,
            "confirmation_timestamp",
        ),
        "reclaim": (
            breakout_reclaim,
            RECLAIM_LEVEL_TYPE,
            "confirmation_timestamp",
        ),
    }
    result: dict[str, Any] = {}
    for series_id in series:
        result[series_id] = {"weekly_bar_count": len(weekly[series_id])}
    consensus_sets = {}
    for category, (collection, level_type, timestamp_field) in specs.items():
        event_sets = {
            series_id: {
                getattr(item, timestamp_field)
                for item in items
                if item.level_type == level_type
            }
            for series_id, items in collection.items()
        }
        provider_counts = Counter(
            timestamp
            for provider_id in REQUIRED_COMPOSITE_PROVIDER_IDS
            for timestamp in event_sets[provider_id]
        )
        consensus = {
            timestamp for timestamp, count in provider_counts.items() if count >= 2
        }
        consensus_sets[category] = consensus
        for series_id, events in event_sets.items():
            difference = events ^ consensus
            union = events | consensus
            result[series_id][category] = {
                "event_count": len(events),
                "consensus_event_count": len(consensus),
                "disagreement_count": len(difference),
                "disagreement_rate": _ratio(len(difference), len(union)),
                "event_timestamps": [item.isoformat() for item in sorted(events)],
            }
    for series_id in series:
        swing_difference = (
            result[series_id]["swing_high"]["disagreement_count"]
            + result[series_id]["swing_low"]["disagreement_count"]
        )
        swing_union = len(
            set(
                result[series_id]["swing_high"]["event_timestamps"]
                + result[series_id]["swing_low"]["event_timestamps"],
            )
            | {
                item.isoformat()
                for item in consensus_sets["swing_high"]
                | consensus_sets["swing_low"]
            },
        )
        result[series_id]["combined_swing"] = {
            "disagreement_count": swing_difference,
            "disagreement_rate": _ratio(swing_difference, swing_union),
        }
    result["consensus_definition"] = (
        "Event timestamp present for at least two independent raw providers."
    )
    return result


def _trade_path_comparison(
    series: Mapping[str, Sequence[OhlcvBar]],
    probes: Sequence[TradePathProbe],
) -> dict[str, Any]:
    metrics_by_series = {
        series_id: [_path_metrics(bars, probe) for probe in probes]
        for series_id, bars in series.items()
    }
    consensus_stop = {}
    consensus_mfe = {}
    consensus_mae = {}
    for index in range(len(probes)):
        provider_metrics = [
            metrics_by_series[provider_id][index]
            for provider_id in REQUIRED_COMPOSITE_PROVIDER_IDS
            if metrics_by_series[provider_id][index] is not None
        ]
        if len(provider_metrics) < 2:
            continue
        consensus_stop[index] = sum(
            bool(item["stop_touched"]) for item in provider_metrics
        ) >= 2
        consensus_mfe[index] = _median([item["mfe"] for item in provider_metrics])
        consensus_mae[index] = _median([item["mae"] for item in provider_metrics])
    result = {}
    for series_id, metrics in metrics_by_series.items():
        compared = [
            (index, item)
            for index, item in enumerate(metrics)
            if item is not None and index in consensus_stop
        ]
        stop_difference = sum(
            bool(item["stop_touched"]) != consensus_stop[index]
            for index, item in compared
        )
        mfe_difference = [
            abs(item["mfe"] - consensus_mfe[index])
            for index, item in compared
        ]
        mae_difference = [
            abs(item["mae"] - consensus_mae[index])
            for index, item in compared
        ]
        result[series_id] = {
            "probe_count": len(probes),
            "comparable_probe_count": len(compared),
            "stop_touch_count": sum(item["stop_touched"] for _, item in compared),
            "stop_disagreement_count": stop_difference,
            "stop_disagreement_rate": _ratio(stop_difference, len(compared)),
            "mfe_abs_difference_vs_venue_consensus": _distribution(mfe_difference),
            "mae_abs_difference_vs_venue_consensus": _distribution(mae_difference),
        }
    result["probe_definition"] = {
        "direction": "long",
        "entry_interval_days": 7,
        "path_days": 28,
        "entry_and_stop_source": ATR_BOOTSTRAP_METHOD_VERSION,
        "stop_rule": "minimum composite-bootstrap low in prior 28 days",
        "point_in_time": True,
    }
    return result


def _atr_comparison(series: Mapping[str, Sequence[OhlcvBar]]) -> dict[str, Any]:
    atr_by_series = {
        series_id: _daily_atr(bars) for series_id, bars in series.items()
    }
    consensus = {}
    all_dates = set().union(
        *(set(atr_by_series[item]) for item in REQUIRED_COMPOSITE_PROVIDER_IDS),
    )
    for timestamp in all_dates:
        values = [
            atr_by_series[provider_id][timestamp]
            for provider_id in REQUIRED_COMPOSITE_PROVIDER_IDS
            if timestamp in atr_by_series[provider_id]
        ]
        if len(values) >= 2:
            consensus[timestamp] = _median(values)
    result = {}
    for series_id, values in atr_by_series.items():
        common = sorted(set(values) & set(consensus))
        differences = [
            abs(values[timestamp] - consensus[timestamp]) / consensus[timestamp]
            for timestamp in common
            if consensus[timestamp] > 0
        ]
        result[series_id] = {
            "daily_atr_count": len(values),
            "daily_atr_distribution": _distribution(list(values.values())),
            "abs_fractional_divergence_vs_venue_consensus": _distribution(
                differences,
            ),
        }
    result["definition"] = "14-day ATR on complete 00:00 UTC daily bars"
    return result


def _daily_atr(bars: Sequence[OhlcvBar]) -> dict[datetime, Decimal]:
    if not bars:
        return {}
    as_of = max(bar.ingested_at for bar in bars) + timedelta(days=1)
    daily = tuple(
        bar
        for bar in build_canonical_market_bars(
            bars,
            data_available_at=as_of,
            timeframes=("1d",),
        )
        if bar.timeframe == "1d"
    )
    values = average_true_range(daily, window=14)
    return {
        bar.timestamp: value
        for bar, value in zip(daily, values)
        if value is not None
    }


def _known_event_analysis(
    series: Mapping[str, Sequence[OhlcvBar]],
    provider_series: Mapping[str, Sequence[OhlcvBar]],
    *,
    structural: Mapping[str, Any],
    period_start: datetime,
    period_end: datetime,
) -> dict[str, Any]:
    by_series = {
        series_id: {bar.timestamp: bar for bar in bars}
        for series_id, bars in series.items()
    }
    events = []
    for definition in KNOWN_DEVELOPMENT_EVENTS:
        timestamp = definition["timestamp"]
        if not period_start <= timestamp <= period_end:
            continue
        raw = {
            provider_id: by_series[provider_id][timestamp]
            for provider_id in REQUIRED_COMPOSITE_PROVIDER_IDS
            if timestamp in by_series[provider_id]
        }
        if len(raw) != 3:
            continue
        field = definition["extreme"]
        raw_values = [getattr(raw[item], field) for item in REQUIRED_COMPOSITE_PROVIDER_IDS]
        consensus_value = _median(raw_values)
        path_entry_time = timestamp - timedelta(days=7)
        path_exit_time = timestamp + timedelta(days=21)
        entry_closes = [
            by_series[provider_id][path_entry_time].close
            for provider_id in REQUIRED_COMPOSITE_PROVIDER_IDS
            if path_entry_time in by_series[provider_id]
        ]
        path_probe = (
            TradePathProbe(
                entry_time=path_entry_time,
                exit_time=path_exit_time,
                entry_price=_median(entry_closes),
                direction="long",
                stop_level=definition.get("reviewed_stop"),
            )
            if len(entry_closes) >= 2
            else None
        )
        provider_path_metrics = [
            _path_metrics(provider_series[provider_id], path_probe)
            for provider_id in REQUIRED_COMPOSITE_PROVIDER_IDS
        ] if path_probe is not None else []
        comparable_provider_paths = [
            item for item in provider_path_metrics if item is not None
        ]
        path_consensus = (
            {
                "mfe": _median([item["mfe"] for item in comparable_provider_paths]),
                "mae": _median([item["mae"] for item in comparable_provider_paths]),
            }
            if len(comparable_provider_paths) >= 2
            else None
        )
        event_record = {
            **{
                key: value.isoformat() if isinstance(value, datetime) else str(value)
                if isinstance(value, Decimal)
                else value
                for key, value in definition.items()
            },
            "raw_ohlc": {
                provider_id: _ohlc_record(bar) for provider_id, bar in raw.items()
            },
            "venue_consensus_extreme": str(consensus_value),
            "event_centered_path_definition": (
                path_probe.as_record() if path_probe is not None else None
            ),
            "venue_consensus_path": _json_safe(path_consensus),
            "series_behavior": {},
        }
        week = timestamp.replace(hour=0) - timedelta(
            days=timestamp.weekday(),
        )
        for series_id in series:
            bar = by_series[series_id].get(timestamp)
            if bar is None:
                event_record["series_behavior"][series_id] = {"available": False}
                continue
            value = getattr(bar, field)
            isolated_rejected = None
            cross_market_represented = None
            if definition["classification"] == "ISOLATED_VENUE_EXTREME":
                isolated = max(
                    raw_values,
                    key=lambda item: abs(item - consensus_value),
                )
                isolated_rejected = abs(value - consensus_value) < abs(
                    value - isolated,
                )
            else:
                if field == "low":
                    cross_market_represented = value <= sorted(raw_values)[1]
                else:
                    cross_market_represented = value >= sorted(raw_values)[1]
            stop = definition.get("reviewed_stop")
            path_metrics = (
                _path_metrics(series[series_id], path_probe)
                if path_probe is not None
                else None
            )
            event_record["series_behavior"][series_id] = {
                "available": True,
                "ohlc": _ohlc_record(bar),
                "isolated_extreme_rejected": isolated_rejected,
                "cross_market_move_represented": cross_market_represented,
                "reviewed_stop_touched": (
                    bar.low <= stop if stop is not None else None
                ),
                "event_centered_mfe": (
                    str(path_metrics["mfe"]) if path_metrics is not None else None
                ),
                "event_centered_mae": (
                    str(path_metrics["mae"]) if path_metrics is not None else None
                ),
                "mfe_difference_vs_venue_consensus": (
                    str(path_metrics["mfe"] - path_consensus["mfe"])
                    if path_metrics is not None and path_consensus is not None
                    else None
                ),
                "mae_difference_vs_venue_consensus": (
                    str(path_metrics["mae"] - path_consensus["mae"])
                    if path_metrics is not None and path_consensus is not None
                    else None
                ),
                "swing_state_in_event_week": any(
                    item in structural[series_id][category]["event_timestamps"]
                    for category in ("swing_high", "swing_low")
                    for item in (week.isoformat(),)
                ),
                "breakout_state_in_event_week": week.isoformat()
                in structural[series_id]["breakout"]["event_timestamps"],
                "reclaim_state_in_event_week": week.isoformat()
                in structural[series_id]["reclaim"]["event_timestamps"],
            }
        events.append(event_record)
    summary = {}
    for series_id in series:
        behaviors = [
            event["series_behavior"][series_id]
            for event in events
            if event["series_behavior"][series_id].get("available")
        ]
        october = next(
            (
                event["series_behavior"][series_id]
                for event in events
                if event["timestamp"].startswith("2025-10-10")
            ),
            {},
        )
        summary[series_id] = {
            "isolated_extremes_rejected": sum(
                item["isolated_extreme_rejected"] is True for item in behaviors
            ),
            "cross_market_moves_represented": sum(
                item["cross_market_move_represented"] is True for item in behaviors
            ),
            "october_2025_stop_touched": october.get("reviewed_stop_touched"),
        }
    return {"events": events, "summary_by_series": summary}


def _tolerance_grid_analysis(
    provider_bars: Mapping[str, Sequence[OhlcvBar]],
    *,
    evaluation_timestamps: set[datetime],
    trailing_atr: Mapping[datetime, Decimal],
    provider_series: Mapping[str, Sequence[OhlcvBar]],
    probes: Sequence[TradePathProbe],
) -> dict[str, Any]:
    result = {}
    for method_version in (CONFIRMED_EXTREMES_VERSION, CLIPPED_CENTER_VERSION):
        variants = []
        for tolerance in CONFIRMATION_TOLERANCE_ATR_GRID:
            observations = _build_composite_history(
                provider_bars,
                method_version=method_version,
                tolerance_atr=tolerance,
                trailing_atr=trailing_atr,
            )
            bars = tuple(
                item.as_ohlcv_bar()
                for item in observations
                if item.observation_time in evaluation_timestamps and item.usable
            )
            variant_series = {**provider_series, method_version: bars}
            structural = _structural_comparison(variant_series)[method_version]
            paths = _trade_path_comparison(variant_series, probes)[method_version]
            known = _known_event_analysis(
                variant_series,
                provider_series,
                structural=_structural_comparison(variant_series),
                period_start=min(evaluation_timestamps),
                period_end=max(evaluation_timestamps),
            )["summary_by_series"][method_version]
            expected_count = len(evaluation_timestamps)
            variants.append(
                {
                    "research_parameter_override": True,
                    "tolerance_atr": str(tolerance),
                    "usable_reference_rate": _ratio(len(bars), expected_count),
                    "combined_swing_disagreement_rate": structural[
                        "combined_swing"
                    ]["disagreement_rate"],
                    "stop_disagreement_rate": paths["stop_disagreement_rate"],
                    "known_event_summary": known,
                    "known_event_gate_passed": (
                        not known["october_2025_stop_touched"] is False
                        and known["isolated_extremes_rejected"]
                        >= sum(
                            item["classification"] == "ISOLATED_VENUE_EXTREME"
                            and item["timestamp"] in evaluation_timestamps
                            for item in KNOWN_DEVELOPMENT_EVENTS
                        )
                        and known["cross_market_moves_represented"]
                        >= sum(
                            item["classification"] == "CROSS_MARKET_MOVE"
                            and item["timestamp"] in evaluation_timestamps
                            for item in KNOWN_DEVELOPMENT_EVENTS
                        )
                    ),
                },
            )
        result[method_version] = variants
    return result


def _candidate_to_candidate_comparison(
    series: Mapping[str, Sequence[OhlcvBar]],
    *,
    structural: Mapping[str, Any],
    probes: Sequence[TradePathProbe],
) -> list[dict[str, Any]]:
    versions = (MEDIAN_OHLC_VERSION, CONFIRMED_EXTREMES_VERSION, CLIPPED_CENTER_VERSION)
    by_series = {
        series_id: {bar.timestamp: bar for bar in series[series_id]}
        for series_id in versions
    }
    comparisons = []
    for index, left in enumerate(versions):
        for right in versions[index + 1 :]:
            common = sorted(set(by_series[left]) & set(by_series[right]))
            close = [
                abs(by_series[left][item].close - by_series[right][item].close)
                / by_series[left][item].close
                for item in common
            ]
            high = [
                abs(by_series[left][item].high - by_series[right][item].high)
                / by_series[left][item].high
                for item in common
            ]
            low = [
                abs(by_series[left][item].low - by_series[right][item].low)
                / by_series[left][item].low
                for item in common
            ]
            left_paths = [_path_metrics(series[left], probe) for probe in probes]
            right_paths = [_path_metrics(series[right], probe) for probe in probes]
            stop_disagreement = sum(
                left_item is not None
                and right_item is not None
                and left_item["stop_touched"] != right_item["stop_touched"]
                for left_item, right_item in zip(left_paths, right_paths)
            )
            comparisons.append(
                {
                    "left": left,
                    "right": right,
                    "common_hour_count": len(common),
                    "close_abs_fractional_difference": _distribution(close),
                    "high_abs_fractional_difference": _distribution(high),
                    "low_abs_fractional_difference": _distribution(low),
                    "combined_swing_disagreement_rate_difference": str(
                        abs(
                            Decimal(
                                structural[left]["combined_swing"][
                                    "disagreement_rate"
                                ],
                            )
                            - Decimal(
                                structural[right]["combined_swing"][
                                    "disagreement_rate"
                                ],
                            )
                        ),
                    ),
                    "stop_touch_disagreement_count": stop_disagreement,
                },
            )
    return comparisons


def _material_disagreement_events(
    provider_bars: Mapping[str, Sequence[OhlcvBar]],
    observations: Sequence[CompositeReferenceObservation],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    by_provider = {
        provider_id: {bar.timestamp: bar for bar in bars}
        for provider_id, bars in provider_bars.items()
    }
    ranked = sorted(
        (
            item
            for item in observations
            if item.diagnostics.high_dispersion_atr is not None
            and item.diagnostics.low_dispersion_atr is not None
        ),
        key=lambda item: max(
            item.diagnostics.high_dispersion_atr or Decimal("0"),
            item.diagnostics.low_dispersion_atr or Decimal("0"),
        ),
        reverse=True,
    )[:limit]
    result = []
    for item in ranked:
        values = {
            provider_id: by_provider[provider_id].get(item.observation_time)
            for provider_id in REQUIRED_COMPOSITE_PROVIDER_IDS
        }
        result.append(
            {
                "timestamp": item.observation_time.isoformat(),
                "diagnostics": item.diagnostics.as_record(),
                "quality_state": item.quality_state,
                "raw_ohlc": {
                    provider_id: _ohlc_record(bar)
                    for provider_id, bar in values.items()
                    if bar is not None
                },
                "primary_composite_ohlc": (
                    _ohlc_record(item.as_ohlcv_bar()) if item.usable else None
                ),
            },
        )
    return result


def _consensus_values(
    provider_bars: Mapping[str, Sequence[OhlcvBar]],
    field: str,
) -> dict[datetime, Decimal]:
    by_provider = {
        provider_id: {bar.timestamp: bar for bar in bars}
        for provider_id, bars in provider_bars.items()
    }
    timestamps = set().union(*(set(items) for items in by_provider.values()))
    result = {}
    for timestamp in timestamps:
        values = [
            getattr(by_provider[provider_id][timestamp], field)
            for provider_id in REQUIRED_COMPOSITE_PROVIDER_IDS
            if timestamp in by_provider[provider_id]
        ]
        if len(values) >= 2:
            result[timestamp] = _median(values)
    return result


def _path_metrics(
    bars: Sequence[OhlcvBar],
    probe: TradePathProbe | None,
) -> dict[str, Any] | None:
    if probe is None:
        return None
    path = [
        bar for bar in bars if probe.entry_time <= bar.timestamp <= probe.exit_time
    ]
    if not path:
        return None
    max_high = max(bar.high for bar in path)
    min_low = min(bar.low for bar in path)
    if probe.direction == "long":
        return {
            "mfe": (max_high - probe.entry_price) / probe.entry_price,
            "mae": (min_low - probe.entry_price) / probe.entry_price,
            "stop_touched": (
                min_low <= probe.stop_level
                if probe.stop_level is not None
                else None
            ),
        }
    return {
        "mfe": (probe.entry_price - min_low) / probe.entry_price,
        "mae": (probe.entry_price - max_high) / probe.entry_price,
        "stop_touched": (
            max_high >= probe.stop_level if probe.stop_level is not None else None
        ),
    }


def _raw_artifact_evidence(raw_dir: Path) -> dict[str, Any]:
    manifest_path = raw_dir / "collection_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    providers = {}
    for provider_id in REQUIRED_COMPOSITE_PROVIDER_IDS:
        path = raw_dir / f"{provider_id}_btc_usd_1h.jsonl.gz"
        providers[provider_id] = {
            "path": str(path),
            "sha256": _file_sha256(path),
            "size_bytes": path.stat().st_size,
        }
    return {
        "collection_manifest_sha256": _file_sha256(manifest_path),
        "historical_period_start": manifest["historical_period_start"],
        "historical_period_end": manifest["historical_period_end"],
        "providers": providers,
    }


def _ohlc_record(bar: OhlcvBar) -> dict[str, str]:
    return {
        "open": str(bar.open),
        "high": str(bar.high),
        "low": str(bar.low),
        "close": str(bar.close),
    }


def _distribution(values: Sequence[Decimal]) -> dict[str, Any]:
    ordered = sorted(abs(value) for value in values)
    if not ordered:
        return {
            "observation_count": 0,
            "median_abs": None,
            "p95_abs": None,
            "p99_abs": None,
            "max_abs": None,
        }
    return {
        "observation_count": len(ordered),
        "median_abs": str(Decimal(str(median(ordered)))),
        "p95_abs": str(_percentile(ordered, Decimal("0.95"))),
        "p99_abs": str(_percentile(ordered, Decimal("0.99"))),
        "max_abs": str(ordered[-1]),
    }


def _percentile(values: Sequence[Decimal], probability: Decimal) -> Decimal:
    rank = int(
        (probability * Decimal(len(values))).to_integral_value(
            rounding=ROUND_CEILING,
        ),
    )
    return values[max(rank - 1, 0)]


def _median(values: Sequence[Decimal]) -> Decimal:
    return Decimal(str(median(values)))


def _ratio(numerator: int, denominator: int) -> str:
    return str(
        Decimal(numerator) / Decimal(denominator)
        if denominator
        else Decimal("0"),
    )


def _optional_decimal_lte(value: str | None, limit: Decimal) -> bool:
    return value is not None and Decimal(value) <= limit


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    return value


def _payload_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        _json_safe(payload),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_exclusive(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as artifact:
        json.dump(_json_safe(payload), artifact, indent=2, sort_keys=True)
        artifact.write("\n")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as artifact:
        json.dump(_json_safe(payload), artifact, indent=2, sort_keys=True)
        artifact.write("\n")


def _parse_utc(value: str) -> datetime:
    return require_utc_datetime(datetime.fromisoformat(value), "timestamp")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "analyze"))
    parser.add_argument("--raw-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sample-name")
    parser.add_argument("--start", type=_parse_utc)
    parser.add_argument("--end", type=_parse_utc)
    parser.add_argument("--database-url")
    parser.add_argument("--persist-database", action="store_true")
    args = parser.parse_args()
    if args.command == "freeze":
        payload = freeze_candidate_definition(args.output, frozen_at=datetime.now(UTC))
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    if not args.raw_dir or not args.sample_name or not args.start or not args.end:
        parser.error("analyze requires --raw-dir, --sample-name, --start, and --end")
    analysis = analyze_period(
        args.raw_dir,
        evaluation_start=args.start,
        evaluation_end=args.end,
        sample_name=args.sample_name,
    )
    database_url = (
        args.database_url
        or (_database_url_from_environment() if args.persist_database else None)
    )
    if database_url:
        analysis.report["database_records_inserted"] = persist_composite_observations(
            database_url,
            analysis.primary_observations,
        )
    _write_json(args.output, analysis.report)
    print(json.dumps({"output": str(args.output), "sample": args.sample_name}, indent=2))


if __name__ == "__main__":
    main()
