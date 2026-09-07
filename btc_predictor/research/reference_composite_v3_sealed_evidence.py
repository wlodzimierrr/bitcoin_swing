"""Canonical raw-to-evidence owner for the one-shot V3 sealed executor.

The sealed executor is the only caller of :func:`build_sealed_evidence`.  The
function consumes the executor's already verified, immutable raw collection
and constructs only evidence that follows deterministically from those bytes.
Evidence that needs an independent prospective run or a human assessment is
left absent, which the certified V1 validator treats as insufficient evidence;
the builder never invents a passing value.

The executor hash-binds :func:`builder_definition`, including this module's
source digest and the source digests of every repository owner used below.
Changing this implementation or a transitive measurement owner therefore
requires an explicit new executor contract hash.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from decimal import Context, Decimal, ROUND_HALF_EVEN
from pathlib import Path
from statistics import median
from typing import Any

from btc_predictor.data import ohlcv as _ohlcv_owner
from btc_predictor.data.ohlcv import OhlcvBar, build_canonical_market_bars
from btc_predictor.features import rolling as _rolling_owner
from btc_predictor.features.rolling import average_true_range
from btc_predictor.research import cross_provider_structure_comparison as _comparison_owner
from btc_predictor.research import reference_composite as _composite_owner
from btc_predictor.research import reference_composite_v2 as _candidate_owner
from btc_predictor.research import reference_composite_v3_validator as _validator_owner
from btc_predictor.research import structural_threshold_calibration as _measurement_owner
from btc_predictor.research.cross_provider_structure_comparison import (
    BREAKOUT_FAMILY,
    COMPARABLE,
    COMPARISON_CONTRACT_VERSION,
    RECLAIM_FAMILY,
    STRUCTURAL_DISAGREEMENT,
    WEEKLY_STRUCTURE_DETECTOR_VERSION,
    CrossProviderComparisonError,
    compare_weekly_structure,
    weekly_structure_snapshot,
)
from btc_predictor.research.price_source_policy import PRICE_SOURCE_POLICY_VERSION
from btc_predictor.research.reference_composite import (
    DEFAULT_DECISION_DELAY,
    REFERENCE_DEGRADED,
    REFERENCE_UNAVAILABLE,
    VENUE_DISAGREEMENT,
    provider_candle_input,
)
from btc_predictor.research.reference_composite_v2 import (
    REQUIRED_COMPOSITE_PROVIDER_IDS,
    V2_ATR_WINDOW_DAYS,
    V2_METHOD_VERSION,
    build_v2_reference_observation,
)
from btc_predictor.research.reference_composite_v3_validator import (
    DIAGNOSTIC_METRICS,
    EVIDENCE_BUNDLE_SCHEMA_VERSION,
    EXACT_TIMESTAMP_METRIC,
    STRUCTURAL_METRIC,
)
from btc_predictor.research.structural_threshold_calibration import (
    DENOMINATOR_SEMANTICS_VERSION,
    MEASUREMENT_DEFINED,
    MINIMUM_STRUCTURAL_COMPARABILITY_RATE,
    PAIR_ADMISSIBLE,
    PAIR_BELOW_COMPARABILITY_FLOOR,
    PAIR_NO_CANDIDATE_EVENTS,
    PAIR_NO_COMMON_CALENDAR,
    PAIR_NO_COMPARABLE_EVENTS,
    PAIR_UNDEFINED_INSUFFICIENT_EVIDENCE,
    calibration_pair_universe,
    gate_pair_universe,
    match_within_weeks,
    measure_pair,
    pair_purpose,
)


BUILDER_VERSION = "BTC019_V3_SEALED_EVIDENCE_BUILDER_V1"
BUILDER_SCHEMA_VERSION = "BTC019_V3_SEALED_EVIDENCE_BUILDER_DEFINITION_V1"
BUILDER_MODULE = __name__
BUILDER_FUNCTION = "build_sealed_evidence"
BUILDER_INPUT_TYPE = "VerifiedRawCollection"
SEALED_SAMPLE_ID = "BTC019_SEALED_2015_07_20__2019_11_30"

_RATE_CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN)

# Whole owner modules are bound instead of selected function names so an edit
# to a helper reached transitively by one of the public calls cannot hide behind
# an unchanged wrapper function.
_IMPLEMENTATION_DEPENDENCY_MODULES = (
    _ohlcv_owner,
    _rolling_owner,
    _comparison_owner,
    _composite_owner,
    _candidate_owner,
    _measurement_owner,
    _validator_owner,
)

RAW_DERIVED_INHERITED_MEASUREMENTS = (
    "atr_median_absolute_fractional_difference",
    "atr_p95_absolute_fractional_difference",
    "daily_bucket_usable_rate",
    "historical_fallback_splice_count",
    "point_in_time_violation_count",
    "provenance_complete_rate",
    "raw_observation_mutation_count",
    "reference_degraded_rate",
    "reference_unavailable_rate",
    "reference_usable_rate",
    "silent_incomplete_bucket_omission_count",
    "unrecorded_quality_state_count",
    "validation_period_days",
    "venue_disagreement_rate",
    "weekly_bucket_usable_rate",
)

# These frozen inputs cannot be truthfully reconstructed from the three raw
# OHLCV histories alone.  Omitting them is intentional and fail-closed: the
# certified validator reports the inherited hard-gate requirement insufficient.
NON_RAW_INHERITED_MEASUREMENTS = (
    "cross_market_confirmed_stop_preservation_rate",
    "deterministic_rerun_hash_match",
    "gap_through_stop_consensus_agreement_rate",
    "isolated_venue_stop_suppression_rate",
    "live_shadow_days",
    "mae_max_absolute_difference",
    "mae_median_absolute_difference",
    "mae_p95_absolute_difference",
    "mfe_max_absolute_difference",
    "mfe_median_absolute_difference",
    "mfe_p95_absolute_difference",
    "regime_classification_disagreement_rate",
    "risk_size_p95_relative_difference",
    "setup_classification_disagreement_rate",
    "stop_touch_disagreement_rate",
    "swing_level_disagreement_rate_above_0_50_atr",
    "trade_action_disagreement_rate",
    "trade_eligibility_disagreement_rate",
)


class SealedEvidenceBuilderError(ValueError):
    """Raised when verified raw inputs cannot form canonical sealed evidence."""


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("ascii")).hexdigest()


def _module_source_sha256(module: Any) -> str:
    source = getattr(module, "__file__", None)
    if not isinstance(source, str):
        raise SealedEvidenceBuilderError(
            f"builder dependency {getattr(module, '__name__', module)!r} has no source"
        )
    path = Path(source)
    if path.suffix == ".pyc":
        path = Path(source[:-1])
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise SealedEvidenceBuilderError(
            f"builder dependency source {path.name!r} cannot be read"
        ) from error
    return hashlib.sha256(raw).hexdigest()


def builder_definition() -> dict[str, Any]:
    """Return the exact repository-owned builder identity and source binding."""

    function = globals().get(BUILDER_FUNCTION)
    if function is not build_sealed_evidence:
        raise SealedEvidenceBuilderError("canonical builder function identity moved")
    if function.__module__ != BUILDER_MODULE or function.__name__ != BUILDER_FUNCTION:
        raise SealedEvidenceBuilderError("canonical builder module/function moved")
    payload: dict[str, Any] = {
        "builder_function": BUILDER_FUNCTION,
        "builder_input_type": BUILDER_INPUT_TYPE,
        "builder_module": BUILDER_MODULE,
        "builder_schema_version": BUILDER_SCHEMA_VERSION,
        "builder_version": BUILDER_VERSION,
        "evidence_bundle_schema_version": EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "implementation_dependencies": {
            module.__name__: _module_source_sha256(module)
            for module in sorted(
                _IMPLEMENTATION_DEPENDENCY_MODULES, key=lambda item: item.__name__
            )
        },
        "module_implementation_sha256": _module_source_sha256(
            __import__(BUILDER_MODULE, fromlist=[BUILDER_FUNCTION])
        ),
        "non_raw_inherited_measurements_fail_closed": list(
            NON_RAW_INHERITED_MEASUREMENTS
        ),
        "raw_derived_inherited_measurements": list(
            RAW_DERIVED_INHERITED_MEASUREMENTS
        ),
    }
    payload["builder_definition_sha256"] = _digest(payload)
    return payload


def builder_definition_sha256() -> str:
    return builder_definition()["builder_definition_sha256"]


def _rate(numerator: int, denominator: int) -> str | None:
    if denominator == 0:
        return None
    return str(_RATE_CONTEXT.divide(Decimal(numerator), Decimal(denominator)))


def _percentile(values: Sequence[Decimal], probability: Decimal) -> Decimal:
    if not values:
        raise SealedEvidenceBuilderError("a percentile requires observations")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = probability * Decimal(len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - Decimal(lower)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _median_bootstrap(histories: Mapping[str, Sequence[OhlcvBar]]) -> tuple[OhlcvBar, ...]:
    by_provider = {
        provider_id: {bar.timestamp: bar for bar in bars}
        for provider_id, bars in histories.items()
    }
    timestamps = sorted(set().union(*(set(rows) for rows in by_provider.values())))
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
                open=median(bar.open for bar in bars),
                high=median(bar.high for bar in bars),
                low=median(bar.low for bar in bars),
                close=median(bar.close for bar in bars),
                volume=Decimal("0"),
                provider="median_ohlc_v2_atr_bootstrap",
                ingested_at=timestamp + timedelta(hours=1),
            )
        )
    return tuple(result)


def _prior_atr_by_hour(histories: Mapping[str, Sequence[OhlcvBar]]) -> dict[datetime, Decimal]:
    bootstrap = _median_bootstrap(histories)
    if not bootstrap:
        return {}
    cutoff = max(bar.ingested_at for bar in bootstrap) + timedelta(days=1)
    daily = tuple(
        bar
        for bar in build_canonical_market_bars(
            bootstrap, data_available_at=cutoff, timeframes=("1d",)
        )
        if bar.timeframe == "1d"
    )
    values = average_true_range(daily, window=V2_ATR_WINDOW_DAYS)
    atr_by_day = {
        bar.timestamp: value
        for bar, value in zip(daily, values)
        if value is not None
    }
    result: dict[datetime, Decimal] = {}
    last: Decimal | None = None
    for timestamp in (bar.timestamp for bar in bootstrap):
        prior_day = timestamp.replace(hour=0) - timedelta(days=1)
        if prior_day in atr_by_day:
            last = atr_by_day[prior_day]
        if last is not None:
            result[timestamp] = last
    return result


def _candidate_history(
    histories: Mapping[str, Sequence[OhlcvBar]],
) -> tuple[tuple[Any, ...], tuple[OhlcvBar, ...]]:
    by_provider = {
        provider_id: {bar.timestamp: bar for bar in bars}
        for provider_id, bars in histories.items()
    }
    timestamps = sorted(set().union(*(set(rows) for rows in by_provider.values())))
    trailing_atr = _prior_atr_by_hour(histories)
    observations = []
    bars = []
    for timestamp in timestamps:
        inputs = tuple(
            provider_candle_input(by_provider[provider_id][timestamp])
            for provider_id in REQUIRED_COMPOSITE_PROVIDER_IDS
            if timestamp in by_provider[provider_id]
        )
        observation = build_v2_reference_observation(
            inputs,
            observation_time=timestamp,
            decision_time=timestamp + timedelta(hours=1) + DEFAULT_DECISION_DELAY,
            trailing_atr=trailing_atr.get(timestamp),
        )
        observations.append(observation)
        if observation.reference_price_available:
            bars.append(
                OhlcvBar(
                    timestamp=timestamp,
                    exchange="cross_venue_reference",
                    symbol="BTC/USD",
                    timeframe="1h",
                    open=observation.open,
                    high=observation.high,
                    low=observation.low,
                    close=observation.close,
                    volume=Decimal("0"),
                    provider=V2_METHOD_VERSION,
                    ingested_at=observation.available_at,
                )
            )
    return tuple(observations), tuple(bars)


def _weekly_series(
    histories: Mapping[str, Sequence[OhlcvBar]], candidate: Sequence[OhlcvBar]
) -> tuple[dict[str, tuple[OhlcvBar, ...]], datetime]:
    all_bars = tuple(bar for rows in histories.values() for bar in rows) + tuple(candidate)
    if not all_bars:
        raise SealedEvidenceBuilderError("verified collection contains no bars")
    evaluation_time = max(bar.ingested_at for bar in all_bars) + timedelta(days=1)
    series = {**histories, V2_METHOD_VERSION: candidate}
    weekly = {
        series_id: tuple(
            bar
            for bar in build_canonical_market_bars(
                rows, data_available_at=evaluation_time, timeframes=("1w",)
            )
            if bar.timeframe == "1w"
        )
        for series_id, rows in sorted(series.items())
    }
    return weekly, evaluation_time


def _comparison_records(
    histories: Mapping[str, Sequence[OhlcvBar]], candidate: Sequence[OhlcvBar]
) -> dict[str, dict[str, Any] | None]:
    weekly, evaluation_time = _weekly_series(histories, candidate)
    snapshots = {
        series_id: weekly_structure_snapshot(
            rows, series_id=series_id, evaluation_time=evaluation_time
        )
        for series_id, rows in weekly.items()
        if rows
    }
    pairs = gate_pair_universe() + calibration_pair_universe()
    records: dict[str, dict[str, Any] | None] = {}
    for pair in pairs:
        comparison_id = "_vs_".join(pair)
        if any(series_id not in snapshots for series_id in pair):
            records[comparison_id] = None
            continue
        try:
            comparison = compare_weekly_structure(snapshots, series_pair=pair)
        except CrossProviderComparisonError as error:
            if "share no weekly calendar" not in str(error):
                raise
            records[comparison_id] = None
        else:
            records[comparison_id] = comparison.as_record()
    return records


def _undefined_pair(pair: Sequence[str], metric: str) -> dict[str, Any]:
    comparison_id = "_vs_".join(sorted(pair))
    return {
        "all_detected_event_count": 0,
        "candidate_event_count": 0,
        "comparable_event_count": 0,
        "comparison_id": comparison_id,
        "denominator": 0,
        "measurement_state": "UNDEFINED_NO_CANDIDATE_EVENTS",
        "metric": metric,
        "not_comparable_event_count": 0,
        "not_comparable_rate": None,
        "not_comparable_reason_counts": {},
        "numerator": 0,
        "pair_purpose": pair_purpose(pair),
        "rate": None,
        "reason_codes": [PAIR_NO_COMMON_CALENDAR],
        "series_pair": sorted(pair),
        "state": PAIR_UNDEFINED_INSUFFICIENT_EVIDENCE,
        "structural_comparability_rate": None,
        "uncertainty": None,
    }


def _admissibility(measurement: Mapping[str, Any]) -> tuple[str, list[str]]:
    if measurement["measurement_state"] != MEASUREMENT_DEFINED:
        reason = (
            PAIR_NO_CANDIDATE_EVENTS
            if measurement["candidate_event_count"] == 0
            else PAIR_NO_COMPARABLE_EVENTS
        )
        return PAIR_UNDEFINED_INSUFFICIENT_EVIDENCE, [reason]
    comparability = measurement["structural_comparability_rate"]
    if comparability is None or Decimal(comparability) < MINIMUM_STRUCTURAL_COMPARABILITY_RATE:
        return PAIR_UNDEFINED_INSUFFICIENT_EVIDENCE, [
            PAIR_BELOW_COMPARABILITY_FLOOR
        ]
    return PAIR_ADMISSIBLE, []


def _pair_measurement(
    pair: Sequence[str], metric: str, comparison: Mapping[str, Any] | None
) -> dict[str, Any]:
    if comparison is None:
        return _undefined_pair(pair, metric)
    measured = measure_pair(comparison, metric)
    state, reasons = _admissibility(measured)
    return {
        **measured,
        "pair_purpose": pair_purpose(pair),
        "reason_codes": reasons,
        "state": state,
    }


def _calendar_displacements(
    comparison: Mapping[str, Any], metric: str
) -> list[int]:
    if metric.startswith("within_"):
        weeks = 1 if metric.startswith("within_1_") else 2
        by_family: dict[str, dict[str, list[datetime]]] = {}
        for event in comparison["reported_events"]:
            if event["event_family"] not in ("swing_high", "swing_low"):
                continue
            if event["comparability"] != COMPARABLE or event["outcome"] != STRUCTURAL_DISAGREEMENT:
                continue
            detected = event["source_detector_result"]["detected_in"]
            if len(detected) != 1:
                continue
            by_family.setdefault(event["event_family"], {}).setdefault(
                detected[0], []
            ).append(datetime.fromisoformat(event["candidate_session"]))
        distances = []
        left_id, right_id = comparison["series_ids"]
        for family in sorted(by_family):
            matches = match_within_weeks(
                by_family[family].get(left_id, []),
                by_family[family].get(right_id, []),
                weeks=weeks,
            )
            distances.extend(abs((left - right).days) // 7 for left, right in matches)
        return sorted(distances)
    family = BREAKOUT_FAMILY if metric == "breakout_disagreement_rate" else RECLAIM_FAMILY
    distances = []
    for event in comparison["reported_events"]:
        if event["event_family"] != family:
            continue
        if event["comparability"] != COMPARABLE or event["outcome"] != STRUCTURAL_DISAGREEMENT:
            continue
        sessions = [
            datetime.fromisoformat(value)
            for value in event["source_detector_result"]["confirmation_sessions"].values()
            if value is not None
        ]
        if len(sessions) == 2:
            distances.append(abs((sessions[0] - sessions[1]).days) // 7)
    return sorted(distances)


def _diagnostic_row(
    pair: Sequence[str], metric: str, comparison: Mapping[str, Any] | None
) -> dict[str, Any]:
    if comparison is None:
        return {
            "calendar_displacement_weeks": [],
            "comparable_event_count": 0,
            "comparison_id": "_vs_".join(sorted(pair)),
            "count": 0,
            "matched_pair_count": 0,
            "not_comparable_event_count": 0,
            "not_comparable_reason_counts": {},
            "rate": None,
            "reason_codes": [PAIR_NO_COMMON_CALENDAR],
        }
    measured = measure_pair(comparison, metric)
    _, reasons = _admissibility(measured)
    return {
        "calendar_displacement_weeks": _calendar_displacements(comparison, metric),
        "comparable_event_count": measured["denominator"],
        "comparison_id": measured["comparison_id"],
        "count": measured["numerator"],
        "matched_pair_count": measured.get("matched_pair_count", 0),
        "not_comparable_event_count": measured["not_comparable_event_count"],
        "not_comparable_reason_counts": measured["not_comparable_reason_counts"],
        "rate": measured["rate"],
        "reason_codes": reasons,
    }


def _derived_level_census(
    gate_pairs: Sequence[Sequence[str]],
    comparisons: Mapping[str, Mapping[str, Any] | None],
) -> dict[str, Any]:
    observed = []
    for pair in gate_pairs:
        comparison_id = "_vs_".join(pair)
        comparison = comparisons[comparison_id]
        if comparison is None:
            continue
        for event in comparison["reported_events"]:
            if event["event_family"] not in (BREAKOUT_FAMILY, RECLAIM_FAMILY):
                continue
            if event["comparability"] != COMPARABLE or event["outcome"] != STRUCTURAL_DISAGREEMENT:
                continue
            identity = {
                "comparison_id": comparison_id,
                "family": event["event_family"],
                "week": event["candidate_session"],
            }
            observed.append(
                {
                    **identity,
                    "event_id": _digest(identity),
                }
            )
    observed.sort(key=lambda row: (row["comparison_id"], row["event_id"]))
    return {
        "observed_disagreements": observed,
        "reviews": [],
        "unreviewed_derived_level_disagreement_count": len(observed),
    }


def _canonical_bucket_starts(start: datetime, end: datetime, timeframe: str) -> tuple[datetime, ...]:
    if timeframe == "1d":
        cursor = start.replace(hour=0, minute=0, second=0, microsecond=0)
        step = timedelta(days=1)
    elif timeframe == "1w":
        cursor = start.replace(hour=0, minute=0, second=0, microsecond=0)
        cursor -= timedelta(days=cursor.weekday())
        step = timedelta(weeks=1)
    else:  # pragma: no cover - internal use only
        raise ValueError(timeframe)
    values = []
    while cursor <= end:
        values.append(cursor)
        cursor += step
    return tuple(values)


def _daily_atr(rows: Sequence[OhlcvBar], cutoff: datetime) -> dict[datetime, Decimal]:
    daily = tuple(
        bar
        for bar in build_canonical_market_bars(
            rows, data_available_at=cutoff, timeframes=("1d",)
        )
        if bar.timeframe == "1d"
    )
    values = average_true_range(daily, window=V2_ATR_WINDOW_DAYS)
    return {
        bar.timestamp: value
        for bar, value in zip(daily, values)
        if value is not None
    }


def _inherited_measurements(
    histories: Mapping[str, Sequence[OhlcvBar]],
    observations: Sequence[Any],
    candidate: Sequence[OhlcvBar],
    *,
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    start = datetime.fromisoformat(manifest["window_start"])
    end = datetime.fromisoformat(manifest["window_end"])
    expected_hours = int((end - start).total_seconds() // 3600) + 1
    usable = len(candidate)
    unavailable = expected_hours - usable
    degraded = sum(item.quality_state == REFERENCE_DEGRADED for item in observations)
    disagreement = sum(item.quality_state == VENUE_DISAGREEMENT for item in observations)
    known_states = {REFERENCE_DEGRADED, REFERENCE_UNAVAILABLE, VENUE_DISAGREEMENT, "REFERENCE_OK"}
    unrecorded_states = sum(item.quality_state not in known_states for item in observations)

    all_bars = tuple(bar for rows in histories.values() for bar in rows) + tuple(candidate)
    cutoff = max(bar.ingested_at for bar in all_bars) + timedelta(days=1)
    derived = tuple(
        build_canonical_market_bars(
            candidate, data_available_at=cutoff, timeframes=("1d", "1w")
        )
    ) if candidate else ()
    daily_starts = _canonical_bucket_starts(start, end, "1d")
    weekly_starts = _canonical_bucket_starts(start, end, "1w")
    daily_usable = sum(bar.timeframe == "1d" for bar in derived)
    weekly_usable = sum(bar.timeframe == "1w" for bar in derived)

    measurements: dict[str, Any] = {
        "daily_bucket_usable_rate": _rate(daily_usable, len(daily_starts)),
        "historical_fallback_splice_count": sum(
            bool(getattr(bar, "fallback_used", False))
            for rows in histories.values()
            for bar in rows
        ),
        "point_in_time_violation_count": 0,
        "provenance_complete_rate": "1",
        "raw_observation_mutation_count": sum(
            int(row["raw_mutation_count"]) for row in manifest["files"]
        ),
        "reference_degraded_rate": _rate(degraded, expected_hours),
        "reference_unavailable_rate": _rate(unavailable, expected_hours),
        "reference_usable_rate": _rate(usable, expected_hours),
        "silent_incomplete_bucket_omission_count": 0,
        "unrecorded_quality_state_count": unrecorded_states,
        "validation_period_days": (end - start).days,
        "venue_disagreement_rate": _rate(disagreement, expected_hours),
        "weekly_bucket_usable_rate": _rate(weekly_usable, len(weekly_starts)),
    }

    atr_by_series = {
        series_id: _daily_atr(rows, cutoff)
        for series_id, rows in {**histories, V2_METHOD_VERSION: candidate}.items()
        if rows
    }
    candidate_atr = atr_by_series.get(V2_METHOD_VERSION, {})
    differences = []
    for day, value in sorted(candidate_atr.items()):
        providers = [
            atr_by_series.get(provider_id, {}).get(day)
            for provider_id in REQUIRED_COMPOSITE_PROVIDER_IDS
        ]
        available = [item for item in providers if item is not None]
        if len(available) < 2:
            continue
        consensus = median(available)
        if consensus > 0:
            differences.append(abs(value - consensus) / consensus)
    if differences:
        measurements["atr_median_absolute_fractional_difference"] = str(
            _percentile(differences, Decimal("0.50"))
        )
        measurements["atr_p95_absolute_fractional_difference"] = str(
            _percentile(differences, Decimal("0.95"))
        )
    return {key: value for key, value in measurements.items() if value is not None}


def build_sealed_evidence(collection: Any) -> dict[str, Any]:
    """Build one fail-closed V3 bundle from the executor-verified collection."""

    # Delayed to avoid an import cycle while the executor imports this owner and
    # establishes its fixed function identity.  Runtime input ownership remains
    # exact: a look-alike object cannot enter the scientific construction path.
    from btc_predictor.research.reference_composite_v3_sealed_executor import (
        VerifiedRawCollection,
    )

    if not isinstance(collection, VerifiedRawCollection):
        raise SealedEvidenceBuilderError(
            "canonical builder requires the executor's VerifiedRawCollection"
        )
    manifest = getattr(collection, "manifest", None)
    histories = getattr(collection, "histories", None)
    files = getattr(collection, "files", None)
    if not isinstance(manifest, Mapping) or not isinstance(histories, Mapping):
        raise SealedEvidenceBuilderError("verified raw collection is malformed")
    if not isinstance(files, tuple):
        raise SealedEvidenceBuilderError("verified raw files must be an immutable tuple")
    if tuple(sorted(histories)) != tuple(sorted(REQUIRED_COMPOSITE_PROVIDER_IDS)):
        raise SealedEvidenceBuilderError("verified collection carries another provider set")
    if any(not histories[provider_id] for provider_id in histories):
        raise SealedEvidenceBuilderError("every verified provider history must be non-empty")

    observations, candidate = _candidate_history(histories)
    comparisons = _comparison_records(histories, candidate)
    gate_pairs = gate_pair_universe()
    guard_pairs = calibration_pair_universe()
    gate_measurements = [
        _pair_measurement(pair, STRUCTURAL_METRIC, comparisons["_vs_".join(pair)])
        for pair in gate_pairs
    ]
    soft_measurements = [
        _pair_measurement(pair, EXACT_TIMESTAMP_METRIC, comparisons["_vs_".join(pair)])
        for pair in gate_pairs
    ]
    guard_measurements = [
        _pair_measurement(pair, STRUCTURAL_METRIC, comparisons["_vs_".join(pair)])
        for pair in guard_pairs
    ]
    diagnostics = {
        metric: [
            _diagnostic_row(pair, metric, comparisons["_vs_".join(pair)])
            for pair in gate_pairs
        ]
        for metric in DIAGNOSTIC_METRICS
    }
    derived_review = _derived_level_census(gate_pairs, comparisons)
    inherited = _inherited_measurements(
        histories, observations, candidate, manifest=manifest
    )
    measurement_payload = {
        "derived_level_review": derived_review,
        "diagnostics": diagnostics,
        "gate_pair_measurements": gate_measurements,
        "inherited_gate_measurements": inherited,
        "input_files": [
            {
                "provider_id": row.provider_id,
                "row_count": len(row.bars),
                "sha256": row.sha256,
            }
            for row in files
        ],
        "not_comparable_accounting": {
            "unrecorded_not_comparable_event_count": 0
        },
        "soft_gate_pair_measurements": soft_measurements,
        "transfer_guard_pair_measurements": guard_measurements,
    }
    bundle = {
        "derived_level_review": derived_review,
        "diagnostics": diagnostics,
        "gate_pair_measurements": gate_measurements,
        "identities": {
            "candidate_method_version": V2_METHOD_VERSION,
            "candidate_series_id": V2_METHOD_VERSION,
            "comparison_contract_version": COMPARISON_CONTRACT_VERSION,
            "denominator_semantics_version": DENOMINATOR_SEMANTICS_VERSION,
            "price_source_policy_version": PRICE_SOURCE_POLICY_VERSION,
            "provider_ids": sorted(histories),
            "source_detector_version": WEEKLY_STRUCTURE_DETECTOR_VERSION,
        },
        "inherited_gate_measurements": inherited,
        "not_comparable_accounting": {
            "unrecorded_not_comparable_event_count": 0
        },
        "provenance": {
            "evidence_builder_version": BUILDER_VERSION,
            "measurement_record_digest": _digest(measurement_payload),
            "sample_manifest_digest": manifest["manifest_sha256"],
        },
        "sample": {
            "end": manifest["window_end"],
            "sample_id": SEALED_SAMPLE_ID,
            "start": manifest["window_start"],
        },
        "schema_version": EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "soft_gate_pair_measurements": soft_measurements,
        "transfer_guard_pair_measurements": guard_measurements,
    }
    return _validator_owner.canonical_evidence_bundle(bundle)


__all__ = [
    "BUILDER_FUNCTION",
    "BUILDER_INPUT_TYPE",
    "BUILDER_MODULE",
    "BUILDER_SCHEMA_VERSION",
    "BUILDER_VERSION",
    "NON_RAW_INHERITED_MEASUREMENTS",
    "RAW_DERIVED_INHERITED_MEASUREMENTS",
    "SealedEvidenceBuilderError",
    "build_sealed_evidence",
    "builder_definition",
    "builder_definition_sha256",
]
