"""BTC-019B diagnostics for the frozen BTC reference-composite V1 result."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

from btc_predictor.data import OhlcvBar, build_canonical_market_bars
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
    MATERIAL_PATH_DIFFERENCE,
    build_weekly_trade_path_probes,
)
from btc_predictor.research.reference_composite import (
    DEFAULT_CLOSE_DISAGREEMENT_BPS,
    DEFAULT_DECISION_DELAY,
    DEFAULT_TWO_PROVIDER_RANGE_DISAGREEMENT_ATR,
    MEDIAN_OHLC_VERSION,
    REFERENCE_COMPOSITE_POLICY_VERSION,
    REFERENCE_DEGRADED,
    REFERENCE_OK,
    REFERENCE_UNAVAILABLE,
    REQUIRED_COMPOSITE_PROVIDER_IDS,
    VENUE_DISAGREEMENT,
    CompositeReferenceObservation,
    raw_observation_id,
)
from btc_predictor.research.reference_composite_empirical import (
    EXTERNAL_END,
    EXTERNAL_START,
    PRIMARY_METHOD_VERSION,
    PRIMARY_TOLERANCE_ATR,
    _bootstrap_median_bars,
    _build_composite_history,
    _load_provider_histories,
    _path_metrics,
    _prior_daily_atr_by_hour,
)


DIAGNOSTIC_SCHEMA_VERSION = "BTC019B_GATE_DIAGNOSTICS_V1"
DIAGNOSTIC_PROTOCOL_VERSION = "BTC019B_DIAGNOSTIC_PROTOCOL_V1"
DIAGNOSTIC_OUTPUT_NAMESPACE = "btc019b"
DIAGNOSTIC_ATR_GRID = (
    Decimal("0.10"),
    Decimal("0.20"),
    Decimal("0.30"),
    Decimal("0.50"),
    Decimal("1.00"),
)
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

MISSING_PROVIDER = "MISSING_PROVIDER"
TWO_OF_THREE_CLOSE_CONSENSUS = "TWO_OF_THREE_CLOSE_CONSENSUS"
PROVIDER_CLOSE_DISCONTINUITY = "PROVIDER_CLOSE_DISCONTINUITY"
RANGE_DISAGREEMENT = "RANGE_DISAGREEMENT"
ISOLATED_PROVIDER_OUTLIER = "ISOLATED_PROVIDER_OUTLIER"
GENUINE_CROSS_MARKET_VOLATILITY = "GENUINE_CROSS_MARKET_VOLATILITY"
PERSISTENT_PROVIDER_DISLOCATION = "PERSISTENT_PROVIDER_DISLOCATION"
OTHER_EXPLAINED = "OTHER_EXPLAINED"
UNRESOLVED = "UNRESOLVED"

DEGRADED_CLASSIFICATIONS = (
    MISSING_PROVIDER,
    TWO_OF_THREE_CLOSE_CONSENSUS,
    PROVIDER_CLOSE_DISCONTINUITY,
    RANGE_DISAGREEMENT,
    ISOLATED_PROVIDER_OUTLIER,
    GENUINE_CROSS_MARKET_VOLATILITY,
    PERSISTENT_PROVIDER_DISLOCATION,
    OTHER_EXPLAINED,
    UNRESOLVED,
)

ECONOMICALLY_EQUIVALENT = "REFERENCE_DEGRADED_BUT_ECONOMICALLY_EQUIVALENT"
MINOR_NUMERIC_DIFFERENCE = "REFERENCE_DEGRADED_WITH_MINOR_NUMERIC_DIFFERENCE"
STRUCTURAL_EFFECT = "REFERENCE_DEGRADED_WITH_STRUCTURAL_EFFECT"
TRADE_OR_RISK_EFFECT = "REFERENCE_DEGRADED_WITH_TRADE_OR_RISK_EFFECT"

TIMESTAMP_ONLY_EQUIVALENT_STRUCTURE = "TIMESTAMP_ONLY_EQUIVALENT_STRUCTURE"
MINOR_LEVEL_DIFFERENCE = "MINOR_LEVEL_DIFFERENCE"
MATERIAL_LEVEL_DIFFERENCE = "MATERIAL_LEVEL_DIFFERENCE"
STRUCTURAL_STATE_DIFFERENCE = "STRUCTURAL_STATE_DIFFERENCE"
TRADE_DECISION_DIFFERENCE = "TRADE_DECISION_DIFFERENCE"
STOP_OR_RISK_DIFFERENCE = "STOP_OR_RISK_DIFFERENCE"


def diagnostic_protocol() -> dict[str, Any]:
    """Return the predeclared research-only BTC-019B diagnostic protocol."""

    return {
        "schema_version": DIAGNOSTIC_PROTOCOL_VERSION,
        "scope": "diagnostic_only",
        "frozen_v1_invariants": {
            "reference_policy_version": REFERENCE_COMPOSITE_POLICY_VERSION,
            "primary_method_version": MEDIAN_OHLC_VERSION,
            "formula_changed": False,
            "approval_thresholds_changed": False,
            "v1_decision": "RESEARCH_INCONCLUSIVE",
            "price_source_policy_changed": False,
        },
        "bar_classification_precedence": [
            MISSING_PROVIDER,
            GENUINE_CROSS_MARKET_VOLATILITY,
            PROVIDER_CLOSE_DISCONTINUITY,
            PERSISTENT_PROVIDER_DISLOCATION,
            ISOLATED_PROVIDER_OUTLIER,
            TWO_OF_THREE_CLOSE_CONSENSUS,
            RANGE_DISAGREEMENT,
            OTHER_EXPLAINED,
            UNRESOLVED,
        ],
        "diagnostic_rules": {
            "missing_provider": "Fewer than all three frozen V1 providers are present.",
            "two_of_three_close_consensus": (
                "The closest provider-close pair is within the frozen 50 bps V1 "
                "close threshold while all three closes are not."
            ),
            "range_disagreement": (
                "High, low, or candle-range dispersion exceeds the frozen 0.30 "
                "prior-daily-ATR V1 two-provider range threshold."
            ),
            "genuine_cross_market_volatility": (
                "Every available venue has an hourly high-low range of at least "
                "0.30 prior daily ATR. This uses the frozen V1 range threshold."
            ),
            "provider_close_discontinuity": (
                "The isolated close has an opposite one-hour return sign to both "
                "members of the agreeing pair, or its open gap from its own prior "
                "close exceeds 50 bps and every agreeing-pair gap."
            ),
            "persistent_provider_dislocation": (
                "The same isolated provider was already the outlier in the "
                "immediately preceding degraded hour; no future hour is used."
            ),
            "isolated_provider_outlier": (
                "One provider lies outside the closest close pair and no stronger "
                "point-in-time diagnostic above applies."
            ),
        },
        "episode_definition": (
            "Maximal sequence of REFERENCE_DEGRADED observations separated by "
            "exactly one hour."
        ),
        "economic_counterfactual": (
            "Research-only, one episode at a time: for three-provider degraded "
            "hours, replace each independent median-OHLC candle with the fieldwise "
            "midpoint of the closest close-consensus pair. Two-provider candles "
            "are unchanged. This is diagnostic attribution, not a composite candidate."
        ),
        "material_path_difference_fraction": str(MATERIAL_PATH_DIFFERENCE),
        "atr_material_grid": [str(value) for value in DIAGNOSTIC_ATR_GRID],
        "point_in_time": {
            "decision_time": "observation_time + 1 hour + 5 minutes",
            "input_rule": "input.available_at <= composite_decision_time",
            "atr_rule": "prior completed daily ATR only",
            "persistent_flag_rule": "prior observations only",
        },
    }


def analyze_btc019b(
    raw_dir: Path,
    v1_artifact_dir: Path,
) -> dict[str, Any]:
    """Build the complete BTC-019B diagnostic result from immutable V1 inputs."""

    _validate_v1_state(v1_artifact_dir)
    _validate_raw_evidence(raw_dir, v1_artifact_dir)
    provider_bars = _load_provider_histories(raw_dir)
    provider_by_time = {
        provider_id: {bar.timestamp: bar for bar in bars}
        for provider_id, bars in provider_bars.items()
    }
    trailing_atr = _prior_daily_atr_by_hour(provider_bars)
    observations = _build_composite_history(
        provider_bars,
        method_version=PRIMARY_METHOD_VERSION,
        tolerance_atr=PRIMARY_TOLERANCE_ATR,
        trailing_atr=trailing_atr,
    )
    external = tuple(
        item
        for item in observations
        if EXTERNAL_START <= item.observation_time <= EXTERNAL_END
    )
    degraded = tuple(
        item for item in external if item.quality_state == REFERENCE_DEGRADED
    )
    if len(degraded) != 286:
        raise ValueError(f"expected 286 frozen external degraded bars, found {len(degraded)}")

    degraded_records = _classify_degraded_bars(
        degraded,
        provider_by_time=provider_by_time,
        trailing_atr=trailing_atr,
    )
    episodes = _group_degraded_episodes(degraded_records)
    actual_bars = tuple(item.as_ohlcv_bar() for item in external if item.usable)
    probes = _external_trade_probes(provider_bars)
    episode_records = _diagnose_episode_consequences(
        episodes,
        actual_bars=actual_bars,
        provider_by_time=provider_by_time,
        trailing_atr=trailing_atr,
        probes=probes,
    )
    consequence_by_episode = {
        item["episode_id"]: item["economic_consequence"] for item in episode_records
    }
    for record in degraded_records:
        record["economic_consequence"] = consequence_by_episode[record["episode_id"]]

    swing_analysis = _diagnose_swing_disagreements(
        provider_bars=provider_bars,
        external_observations=external,
        actual_bars=actual_bars,
        trailing_atr=trailing_atr,
        probes=probes,
    )
    quality_analysis = _quality_state_analysis(
        external,
        provider_by_time=provider_by_time,
        trailing_atr=trailing_atr,
        swing_analysis=swing_analysis,
    )
    attribution = _provider_attribution(degraded_records)
    summary = _build_summary(
        external,
        degraded_records=degraded_records,
        episodes=episode_records,
        quality_analysis=quality_analysis,
        swing_analysis=swing_analysis,
    )
    v2_proposal = _v2_research_proposal()
    return {
        "schema_version": DIAGNOSTIC_SCHEMA_VERSION,
        "ticket": "BTC-019B",
        "diagnostic_protocol_version": DIAGNOSTIC_PROTOCOL_VERSION,
        "reference_policy_version": REFERENCE_COMPOSITE_POLICY_VERSION,
        "primary_method_version": PRIMARY_METHOD_VERSION,
        "evaluation_start": EXTERNAL_START.isoformat(),
        "evaluation_end": EXTERNAL_END.isoformat(),
        "v1_artifact_sha256": _artifact_hashes(v1_artifact_dir),
        "protocol": diagnostic_protocol(),
        "summary": summary,
        "provider_attribution": attribution,
        "quality_state_analysis": quality_analysis,
        "degraded_bars": degraded_records,
        "degraded_episodes": episode_records,
        "swing_analysis": swing_analysis,
        "v2_research_proposal": v2_proposal,
        "database": {
            "migration_required": False,
            "schema_changed": False,
            "expected_existing_head": "0019_reference_composite",
            "reason": "BTC-019B persists immutable research artifacts only.",
        },
        "governance": {
            "diagnostic_conclusion": _governance_conclusion(summary),
            "btc_reference_composite_v1": "RESEARCH_INCONCLUSIVE",
            "price_source_policy_v1": "UNCHANGED",
            "production_canonical_reference": "UNRESOLVED",
            "btc019_status_recommendation": "IN PROGRESS",
            "automatic_provider_promotion": False,
            "degraded_rate_gate_assessment": (
                "The frozen total-frequency gate is not economically well specified "
                "as a standalone gate: it treats usable warnings with zero measured "
                "structural/trade effects like unusable reference failures. Preserve "
                "it for V1 and supplement, rather than retroactively replace, it."
            ),
            "exact_swing_gate_assessment": (
                "Exact timestamps are too brittle as a standalone weekly-structure "
                "gate, but the failure exposed real omitted-week level and breakout "
                "state changes. Preserve the V1 result and require temporal, ATR, "
                "structural-state, and trade-risk diagnostics in a future version."
            ),
        },
    }


def write_btc019b_artifacts(result: Mapping[str, Any], output_dir: Path) -> None:
    """Write a new immutable BTC-019B artifact namespace."""

    output_dir.mkdir(parents=True, exist_ok=False)
    files = {
        "diagnostic_protocol.json": result["protocol"],
        "degraded_bar_diagnostics.json": {
            "schema_version": DIAGNOSTIC_SCHEMA_VERSION,
            "records": result["degraded_bars"],
        },
        "degraded_episode_diagnostics.json": {
            "schema_version": DIAGNOSTIC_SCHEMA_VERSION,
            "records": result["degraded_episodes"],
        },
        "swing_disagreement_diagnostics.json": result["swing_analysis"],
        "final_diagnostic_decision.json": {
            "schema_version": DIAGNOSTIC_SCHEMA_VERSION,
            "summary": result["summary"],
            "governance": result["governance"],
            "provider_attribution": result["provider_attribution"],
            "quality_state_analysis": result["quality_state_analysis"],
            "v1_artifact_sha256": result["v1_artifact_sha256"],
            "v2_research_proposal": result["v2_research_proposal"],
            "database": result["database"],
        },
    }
    for name, payload in files.items():
        _write_json(output_dir / name, payload)
    (output_dir / "final_diagnostic_report.md").write_text(
        _markdown_report(result),
        encoding="utf-8",
    )


def _classify_degraded_bars(
    observations: Sequence[CompositeReferenceObservation],
    *,
    provider_by_time: Mapping[str, Mapping[datetime, OhlcvBar]],
    trailing_atr: Mapping[datetime, Decimal],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    prior_outlier: str | None = None
    prior_timestamp: datetime | None = None
    for observation in sorted(observations, key=lambda item: item.observation_time):
        timestamp = observation.observation_time
        bars = {
            provider_id: provider_by_time[provider_id][timestamp]
            for provider_id in observation.input_providers_available
        }
        missing = tuple(
            provider_id
            for provider_id in REQUIRED_COMPOSITE_PROVIDER_IDS
            if provider_id not in bars
        )
        pair, outlier, pair_dispersion, outlier_dispersion = _closest_close_pair(bars)
        atr = trailing_atr.get(timestamp)
        returns = {
            provider_id: _one_hour_return(
                bar,
                provider_by_time[provider_id].get(timestamp - timedelta(hours=1)),
            )
            for provider_id, bar in bars.items()
        }
        open_gaps = {
            provider_id: _open_gap_bps(
                bar,
                provider_by_time[provider_id].get(timestamp - timedelta(hours=1)),
            )
            for provider_id, bar in bars.items()
        }
        range_disagreement = bool(
            atr
            and any(
                value is not None
                and value > DEFAULT_TWO_PROVIDER_RANGE_DISAGREEMENT_ATR
                for value in (
                    observation.diagnostics.high_dispersion_atr,
                    observation.diagnostics.low_dispersion_atr,
                    observation.diagnostics.range_dispersion_atr,
                )
            )
        )
        genuine_volatility = bool(
            atr
            and len(bars) == 3
            and all(
                (bar.high - bar.low) / atr
                >= DEFAULT_TWO_PROVIDER_RANGE_DISAGREEMENT_ATR
                for bar in bars.values()
            )
        )
        discontinuity = _is_close_discontinuity(
            pair,
            outlier,
            returns=returns,
            open_gaps=open_gaps,
        )
        persistent = bool(
            outlier
            and outlier == prior_outlier
            and prior_timestamp is not None
            and timestamp == prior_timestamp + timedelta(hours=1)
        )
        flags = []
        if missing:
            flags.append(MISSING_PROVIDER)
        if pair and outlier:
            flags.extend((TWO_OF_THREE_CLOSE_CONSENSUS, ISOLATED_PROVIDER_OUTLIER))
        if range_disagreement:
            flags.append(RANGE_DISAGREEMENT)
        if genuine_volatility:
            flags.append(GENUINE_CROSS_MARKET_VOLATILITY)
        if discontinuity:
            flags.append(PROVIDER_CLOSE_DISCONTINUITY)
        if persistent:
            flags.append(PERSISTENT_PROVIDER_DISLOCATION)
        classification = _primary_degraded_classification(
            missing=bool(missing),
            pair=pair,
            outlier=outlier,
            genuine_volatility=genuine_volatility,
            discontinuity=discontinuity,
            persistent=persistent,
            range_disagreement=range_disagreement,
        )
        field_outliers = {
            field: _field_outlier(bars, field) for field in ("close", "high", "low")
        }
        records.append(
            {
                "timestamp": timestamp,
                "composite_decision_time": observation.available_at,
                "input_providers_available": list(observation.input_providers_available),
                "missing_providers": list(missing),
                "provider_available_at": {
                    provider_id: timestamp + timedelta(hours=1)
                    for provider_id in bars
                },
                "provider_observation_ids": {
                    provider_id: raw_observation_id(bar)
                    for provider_id, bar in bars.items()
                },
                "provider_ohlc": {
                    provider_id: _ohlc_record(bar)
                    for provider_id, bar in bars.items()
                },
                "quality_state": observation.quality_state,
                "confirmation_state": observation.confirmation_state,
                "reason_codes": list(observation.reason_codes),
                "composite_ohlc": _ohlc_record(observation.as_ohlcv_bar()),
                "diagnostics": observation.diagnostics.as_record(),
                "prior_daily_atr": atr,
                "closest_close_pair": list(pair) if pair else [],
                "dominant_divergent_provider": outlier,
                "closest_pair_dispersion_bps": pair_dispersion,
                "outlier_to_pair_center_bps": outlier_dispersion,
                "one_hour_returns": returns,
                "open_gap_bps": open_gaps,
                "field_outliers": field_outliers,
                "primary_classification": classification,
                "diagnostic_flags": list(dict.fromkeys(flags)),
            }
        )
        prior_outlier = outlier
        prior_timestamp = timestamp
    return records


def _primary_degraded_classification(
    *,
    missing: bool,
    pair: tuple[str, str] | None,
    outlier: str | None,
    genuine_volatility: bool,
    discontinuity: bool,
    persistent: bool,
    range_disagreement: bool,
) -> str:
    if missing:
        return MISSING_PROVIDER
    if genuine_volatility:
        return GENUINE_CROSS_MARKET_VOLATILITY
    if discontinuity:
        return PROVIDER_CLOSE_DISCONTINUITY
    if persistent:
        return PERSISTENT_PROVIDER_DISLOCATION
    if pair and outlier:
        return ISOLATED_PROVIDER_OUTLIER
    if pair:
        return TWO_OF_THREE_CLOSE_CONSENSUS
    if range_disagreement:
        return RANGE_DISAGREEMENT
    return UNRESOLVED


def _closest_close_pair(
    bars: Mapping[str, OhlcvBar],
) -> tuple[tuple[str, str] | None, str | None, Decimal | None, Decimal | None]:
    if len(bars) != 3:
        return None, None, None, None
    candidates = []
    providers = sorted(bars)
    for index, left in enumerate(providers):
        for right in providers[index + 1 :]:
            center = _median((bars[left].close, bars[right].close))
            dispersion = abs(bars[left].close - bars[right].close) / center * 10000
            candidates.append((dispersion, left, right))
    dispersion, left, right = min(candidates)
    pair = (left, right)
    outlier = next(provider_id for provider_id in providers if provider_id not in pair)
    center = _median((bars[left].close, bars[right].close))
    outlier_dispersion = abs(bars[outlier].close - center) / center * 10000
    return pair, outlier, dispersion, outlier_dispersion


def _is_close_discontinuity(
    pair: tuple[str, str] | None,
    outlier: str | None,
    *,
    returns: Mapping[str, Decimal | None],
    open_gaps: Mapping[str, Decimal | None],
) -> bool:
    if not pair or not outlier:
        return False
    outlier_return = returns[outlier]
    pair_returns = [returns[item] for item in pair]
    opposite_return = bool(
        outlier_return not in (None, Decimal("0"))
        and all(value not in (None, Decimal("0")) for value in pair_returns)
        and all((outlier_return > 0) != (value > 0) for value in pair_returns if value is not None)
    )
    outlier_gap = open_gaps[outlier]
    pair_gaps = [open_gaps[item] for item in pair]
    isolated_gap = bool(
        outlier_gap is not None
        and outlier_gap > DEFAULT_CLOSE_DISAGREEMENT_BPS
        and all(value is not None and outlier_gap > value for value in pair_gaps)
    )
    return opposite_return or isolated_gap


def _group_degraded_episodes(records: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    episodes: list[list[dict[str, Any]]] = []
    for record in records:
        timestamp = record["timestamp"]
        if not episodes or timestamp != episodes[-1][-1]["timestamp"] + timedelta(hours=1):
            episodes.append([])
        episodes[-1].append(record)
    for index, episode in enumerate(episodes, start=1):
        episode_id = f"BTC019B-DEG-{index:03d}"
        for record in episode:
            record["episode_id"] = episode_id
    return episodes


def _diagnose_episode_consequences(
    episodes: Sequence[Sequence[dict[str, Any]]],
    *,
    actual_bars: Sequence[OhlcvBar],
    provider_by_time: Mapping[str, Mapping[datetime, OhlcvBar]],
    trailing_atr: Mapping[datetime, Decimal],
    probes: Sequence[Any],
) -> list[dict[str, Any]]:
    actual_map = {bar.timestamp: bar for bar in actual_bars}
    actual_state = _derived_state(tuple(actual_map.values()))
    actual_paths = tuple(_path_metrics(actual_bars, probe) for probe in probes)
    results = []
    for episode in episodes:
        counterfactual_map = dict(actual_map)
        changed_timestamps = []
        for record in episode:
            timestamp = record["timestamp"]
            replacement = _agreement_pair_counterfactual(
                record,
                provider_by_time=provider_by_time,
            )
            if replacement is not None and replacement != actual_map[timestamp]:
                counterfactual_map[timestamp] = replacement
                changed_timestamps.append(timestamp)
        counterfactual_bars = tuple(
            counterfactual_map[item] for item in sorted(counterfactual_map)
        )
        counterfactual_state = (
            _derived_state(counterfactual_bars) if changed_timestamps else actual_state
        )
        relevant_probe_indexes = [
            index
            for index, probe in enumerate(probes)
            if any(probe.entry_time <= item["timestamp"] <= probe.exit_time for item in episode)
        ]
        counter_paths = {
            index: _path_metrics(counterfactual_bars, probes[index])
            for index in relevant_probe_indexes
        }
        consequence = _state_consequence(
            actual_state,
            counterfactual_state,
            actual_paths=actual_paths,
            counter_paths=counter_paths,
            relevant_probe_indexes=relevant_probe_indexes,
            trailing_atr=trailing_atr,
        )
        classifications = Counter(item["primary_classification"] for item in episode)
        divergent = Counter(
            item["dominant_divergent_provider"]
            for item in episode
            if item["dominant_divergent_provider"]
        )
        results.append(
            {
                "episode_id": episode[0]["episode_id"],
                "start": episode[0]["timestamp"],
                "end": episode[-1]["timestamp"],
                "duration_hours": len(episode),
                "degraded_bar_count": len(episode),
                "providers_missing": sorted(
                    {
                        provider_id
                        for item in episode
                        for provider_id in item["missing_providers"]
                    }
                ),
                "dominant_divergent_provider": (
                    divergent.most_common(1)[0][0] if divergent else None
                ),
                "max_close_dispersion_bps": max(
                    Decimal(item["diagnostics"]["close_dispersion_bps"])
                    for item in episode
                ),
                "max_high_dispersion_atr": _max_optional_decimal(
                    item["diagnostics"]["high_dispersion_atr"] for item in episode
                ),
                "max_low_dispersion_atr": _max_optional_decimal(
                    item["diagnostics"]["low_dispersion_atr"] for item in episode
                ),
                "classification_counts": dict(classifications),
                "episode_classification": classifications.most_common(1)[0][0],
                "reference_usable": True,
                "counterfactual_changed_bar_count": len(changed_timestamps),
                "economic_consequence": consequence,
            }
        )
    return results


def _agreement_pair_counterfactual(
    record: Mapping[str, Any],
    *,
    provider_by_time: Mapping[str, Mapping[datetime, OhlcvBar]],
) -> OhlcvBar | None:
    pair = tuple(record["closest_close_pair"])
    if len(pair) != 2:
        return None
    timestamp = record["timestamp"]
    bars = [provider_by_time[provider_id][timestamp] for provider_id in pair]
    return OhlcvBar(
        timestamp=timestamp,
        exchange="cross_venue_reference",
        symbol="BTC/USD",
        timeframe="1h",
        open=_median(tuple(bar.open for bar in bars)),
        high=_median(tuple(bar.high for bar in bars)),
        low=_median(tuple(bar.low for bar in bars)),
        close=_median(tuple(bar.close for bar in bars)),
        volume=Decimal("0"),
        provider=MEDIAN_OHLC_VERSION.lower(),
        ingested_at=timestamp + timedelta(hours=1) + DEFAULT_DECISION_DELAY,
    )


def _derived_state(bars: Sequence[OhlcvBar]) -> dict[str, Any]:
    if not bars:
        return {"weekly": {}, "swings": {}, "breakout_reclaim": {}, "daily_atr": {}}
    as_of = max(bar.ingested_at for bar in bars) + timedelta(days=8)
    derived = build_canonical_market_bars(
        tuple(sorted(bars, key=lambda item: item.timestamp)),
        data_available_at=as_of,
        timeframes=("1d", "1w"),
    )
    weekly = tuple(item for item in derived if item.timeframe == "1w")
    daily = tuple(item for item in derived if item.timeframe == "1d")
    swings = detect_weekly_swing_levels(weekly, as_of=as_of)
    breakout_reclaim = detect_breakout_reclaim_levels(swings, weekly, as_of=as_of)
    atr_values = average_true_range(daily, window=14)
    return {
        "weekly": {item.timestamp: item for item in weekly},
        "swings": {
            (item.level_type, item.level_timestamp): item for item in swings
        },
        "breakout_reclaim": {
            (item.level_type, item.confirmation_timestamp, item.source_level_timestamp): item
            for item in breakout_reclaim
        },
        "daily_atr": {
            item.timestamp: value
            for item, value in zip(daily, atr_values)
            if value is not None
        },
    }


def _state_consequence(
    actual: Mapping[str, Any],
    counterfactual: Mapping[str, Any],
    *,
    actual_paths: Sequence[Mapping[str, Any] | None],
    counter_paths: Mapping[int, Mapping[str, Any] | None],
    relevant_probe_indexes: Sequence[int],
    trailing_atr: Mapping[datetime, Decimal],
) -> dict[str, Any]:
    swing_keys = set(actual["swings"]) ^ set(counterfactual["swings"])
    breakout_keys = set(actual["breakout_reclaim"]) ^ set(
        counterfactual["breakout_reclaim"]
    )
    common_swings = set(actual["swings"]) & set(counterfactual["swings"])
    level_distances_atr = []
    for key in common_swings:
        timestamp = key[1]
        atr = trailing_atr.get(timestamp)
        if atr:
            level_distances_atr.append(
                abs(actual["swings"][key].price - counterfactual["swings"][key].price)
                / atr
            )
    weekly_difference = _maximum_bar_fractional_difference(
        actual["weekly"], counterfactual["weekly"]
    )
    atr_difference = _maximum_mapping_fractional_difference(
        actual["daily_atr"], counterfactual["daily_atr"]
    )
    stop_differences = 0
    mfe_differences = []
    mae_differences = []
    for index in relevant_probe_indexes:
        left = actual_paths[index]
        right = counter_paths[index]
        if left is None or right is None:
            continue
        stop_differences += left["stop_touched"] != right["stop_touched"]
        mfe_differences.append(abs(left["mfe"] - right["mfe"]))
        mae_differences.append(abs(left["mae"] - right["mae"]))
    max_mfe = max(mfe_differences, default=Decimal("0"))
    max_mae = max(mae_differences, default=Decimal("0"))
    trade_material = bool(
        stop_differences
        or max_mfe >= MATERIAL_PATH_DIFFERENCE
        or max_mae >= MATERIAL_PATH_DIFFERENCE
    )
    structural = bool(
        swing_keys
        or breakout_keys
        or any(value >= DIAGNOSTIC_ATR_GRID[0] for value in level_distances_atr)
    )
    numeric = bool(
        weekly_difference
        or atr_difference
        or any(value != 0 for value in level_distances_atr)
        or max_mfe
        or max_mae
    )
    if trade_material:
        classification = TRADE_OR_RISK_EFFECT
    elif structural:
        classification = STRUCTURAL_EFFECT
    elif numeric:
        classification = MINOR_NUMERIC_DIFFERENCE
    else:
        classification = ECONOMICALLY_EQUIVALENT
    return {
        "classification": classification,
        "weekly_swing_event_difference_count": len(swing_keys),
        "breakout_reclaim_event_difference_count": len(breakout_keys),
        "max_structural_level_distance_atr": max(level_distances_atr, default=Decimal("0")),
        "max_weekly_ohlc_fractional_difference": weekly_difference,
        "max_daily_atr_fractional_difference": atr_difference,
        "relevant_trade_probe_count": len(relevant_probe_indexes),
        "stop_touch_difference_count": stop_differences,
        "max_mfe_fractional_difference": max_mfe,
        "max_mae_fractional_difference": max_mae,
        "entry_location": "not_evaluable_in_current_btc019_research_pipeline",
        "structural_invalidation": "proxied_by_swing_level_distance_only",
        "stop_location": "probe_stops_are_frozen_from_prior_bootstrap_history",
        "setup_eligibility": "not_integrated_for_btc019b",
        "entry_eligibility": "not_integrated_for_btc019b",
        "risk_sizing": "not_integrated_for_btc019b",
        "trade_action": "not_integrated_for_btc019b",
    }


def _diagnose_swing_disagreements(
    *,
    provider_bars: Mapping[str, Sequence[OhlcvBar]],
    external_observations: Sequence[CompositeReferenceObservation],
    actual_bars: Sequence[OhlcvBar],
    trailing_atr: Mapping[datetime, Decimal],
    probes: Sequence[Any],
) -> dict[str, Any]:
    filtered_provider = {
        provider_id: tuple(
            bar for bar in bars if EXTERNAL_START <= bar.timestamp <= EXTERNAL_END
        )
        for provider_id, bars in provider_bars.items()
    }
    states = {
        provider_id: _derived_state(bars)
        for provider_id, bars in filtered_provider.items()
    }
    states[PRIMARY_METHOD_VERSION] = _derived_state(actual_bars)
    consensus = _exact_provider_swing_consensus(states)
    composite_levels = states[PRIMARY_METHOD_VERSION]["swings"]
    paired = _pair_swing_disagreements(consensus, composite_levels)

    disagreement_observations = tuple(
        item for item in external_observations if item.quality_state == VENUE_DISAGREEMENT
    )
    restored_bars = _restore_disagreement_hours_for_diagnosis(
        actual_bars,
        disagreement_observations=disagreement_observations,
        provider_bars=filtered_provider,
    )
    restored_state = _derived_state(restored_bars)
    actual_state = states[PRIMARY_METHOD_VERSION]
    actual_paths = tuple(_path_metrics(actual_bars, probe) for probe in probes)
    restored_paths = tuple(_path_metrics(restored_bars, probe) for probe in probes)
    global_stop_difference = sum(
        left is not None
        and right is not None
        and left["stop_touched"] != right["stop_touched"]
        for left, right in zip(actual_paths, restored_paths)
    )
    global_mfe_difference = max(
        (
            abs(left["mfe"] - right["mfe"])
            for left, right in zip(actual_paths, restored_paths)
            if left is not None and right is not None
        ),
        default=Decimal("0"),
    )
    global_mae_difference = max(
        (
            abs(left["mae"] - right["mae"])
            for left, right in zip(actual_paths, restored_paths)
            if left is not None and right is not None
        ),
        default=Decimal("0"),
    )
    restored_swing_difference = set(restored_state["swings"]) ^ set(consensus)
    restored_breakout_difference = set(restored_state["breakout_reclaim"]) ^ set(
        actual_state["breakout_reclaim"]
    )
    records = []
    for pair_index, pair in enumerate(paired, start=1):
        consensus_key = pair["consensus_key"]
        composite_key = pair["composite_key"]
        consensus_level = consensus[consensus_key]
        composite_level = composite_levels[composite_key]
        atr = trailing_atr.get(max(consensus_key[1], composite_key[1]))
        distance = abs(consensus_level["price"] - composite_level.price)
        distance_atr = distance / atr if atr else None
        source_effects = _source_level_effects(
            consensus_key,
            composite_key,
            states=states,
        )
        classification = (
            STOP_OR_RISK_DIFFERENCE
            if global_stop_difference
            else TRADE_DECISION_DIFFERENCE
            if max(global_mfe_difference, global_mae_difference)
            >= MATERIAL_PATH_DIFFERENCE
            else STRUCTURAL_STATE_DIFFERENCE
            if source_effects["breakout_or_reclaim_state_changed"]
            else MATERIAL_LEVEL_DIFFERENCE
            if distance_atr is None or distance_atr > DIAGNOSTIC_ATR_GRID[0]
            else MINOR_LEVEL_DIFFERENCE
            if distance
            else TIMESTAMP_ONLY_EQUIVALENT_STRUCTURE
        )
        common_record = {
            "pair_id": f"BTC019B-SWING-PAIR-{pair_index:02d}",
            "event_type": consensus_key[0],
            "consensus_timestamp": consensus_key[1],
            "composite_timestamp": composite_key[1],
            "timestamp_difference_weeks": pair["week_distance"],
            "within_one_week": pair["week_distance"] <= 1,
            "within_two_weeks": pair["week_distance"] <= 2,
            "consensus_price": consensus_level["price"],
            "composite_price": composite_level.price,
            "absolute_price_difference": distance,
            "percentage_price_difference": distance / consensus_level["price"],
            "prior_daily_atr": atr,
            "atr_normalized_difference": distance_atr,
            "atr_grid_materiality": {
                str(threshold): distance_atr is None or distance_atr > threshold
                for threshold in DIAGNOSTIC_ATR_GRID
            },
            "provider_swing_timestamps": consensus_level["provider_timestamps"],
            "provider_weekly_ohlc": {
                provider_id: {
                    timestamp.isoformat(): _optional_ohlc(
                        states[provider_id]["weekly"].get(timestamp)
                    )
                    for timestamp in (consensus_key[1], composite_key[1])
                }
                for provider_id in REQUIRED_COMPOSITE_PROVIDER_IDS
            },
            "composite_weekly_ohlc": {
                timestamp.isoformat(): _optional_ohlc(
                    actual_state["weekly"].get(timestamp)
                )
                for timestamp in (consensus_key[1], composite_key[1])
            },
            "restored_diagnostic_weekly_ohlc": {
                timestamp.isoformat(): _optional_ohlc(
                    restored_state["weekly"].get(timestamp)
                )
                for timestamp in (consensus_key[1], composite_key[1])
            },
            "classification": classification,
            "downstream_consequences": {
                **source_effects,
                "support_resistance_level_changed": distance != 0,
                "entry_location": "not_evaluable_in_current_btc019_research_pipeline",
                "structural_invalidation": (
                    "level_changed" if distance else "unchanged"
                ),
                "stop_location": "not_linked_to_swing_source_in_current_probe_model",
                "stop_touch_difference": bool(global_stop_difference),
                "mfe_material_difference": global_mfe_difference
                >= MATERIAL_PATH_DIFFERENCE,
                "mae_material_difference": global_mae_difference
                >= MATERIAL_PATH_DIFFERENCE,
                "setup_eligibility": "not_integrated_for_btc019b",
                "entry_eligibility": "not_integrated_for_btc019b",
                "risk_sizing": "not_integrated_for_btc019b",
                "trade_action": "not_integrated_for_btc019b",
            },
        }
        for side, key in (("consensus_only", consensus_key), ("composite_only", composite_key)):
            records.append(
                {
                    **common_record,
                    "disagreement_side": side,
                    "event_timestamp": key[1],
                }
            )

    metrics = _swing_metric_summary(
        consensus,
        composite_levels,
        records=records,
        stop_difference_count=global_stop_difference,
        mfe_difference=global_mfe_difference,
        mae_difference=global_mae_difference,
    )
    alternatives = _consensus_alternatives(states, composite_levels)
    return {
        "schema_version": DIAGNOSTIC_SCHEMA_VERSION,
        "frozen_exact_metric_unchanged": True,
        "disagreement_record_count": len(records),
        "paired_economic_structure_count": len(paired),
        "records": records,
        "metrics": metrics,
        "consensus_definition_analysis": alternatives,
        "disagreement_hour_restoration_diagnostic": {
            "method": (
                "Research-only fieldwise median of all three raw venues for the "
                "three V1 VENUE_DISAGREEMENT hours; not a proposed formula."
            ),
            "restored_hour_count": len(disagreement_observations),
            "swing_symmetric_difference_after_restoration": len(
                restored_swing_difference
            ),
            "breakout_reclaim_state_changes_vs_frozen_composite": len(
                restored_breakout_difference
            ),
            "stop_touch_difference_count": global_stop_difference,
            "max_mfe_fractional_difference": global_mfe_difference,
            "max_mae_fractional_difference": global_mae_difference,
        },
    }


def _exact_provider_swing_consensus(states: Mapping[str, Mapping[str, Any]]) -> dict:
    result = {}
    for level_type in (WEEKLY_SWING_HIGH, WEEKLY_SWING_LOW):
        counts: Counter[datetime] = Counter()
        by_provider = {}
        for provider_id in REQUIRED_COMPOSITE_PROVIDER_IDS:
            levels = {
                timestamp: level
                for (kind, timestamp), level in states[provider_id]["swings"].items()
                if kind == level_type
            }
            by_provider[provider_id] = levels
            counts.update(levels.keys())
        for timestamp, count in counts.items():
            if count < 2:
                continue
            members = {
                provider_id: levels[timestamp]
                for provider_id, levels in by_provider.items()
                if timestamp in levels
            }
            result[(level_type, timestamp)] = {
                "price": _median(tuple(item.price for item in members.values())),
                "provider_timestamps": {
                    provider_id: timestamp for provider_id in members
                },
                "provider_prices": {
                    provider_id: item.price for provider_id, item in members.items()
                },
            }
    return result


def _pair_swing_disagreements(
    consensus: Mapping[tuple[str, datetime], Any],
    composite: Mapping[tuple[str, datetime], Any],
) -> list[dict[str, Any]]:
    consensus_only = set(consensus) - set(composite)
    composite_only = set(composite) - set(consensus)
    candidates = sorted(
        (
            abs((left[1] - right[1]).days) // 7,
            left,
            right,
        )
        for left in consensus_only
        for right in composite_only
        if left[0] == right[0]
    )
    used_left = set()
    used_right = set()
    result = []
    for distance, left, right in candidates:
        if left in used_left or right in used_right:
            continue
        used_left.add(left)
        used_right.add(right)
        result.append(
            {
                "consensus_key": left,
                "composite_key": right,
                "week_distance": distance,
            }
        )
    if used_left != consensus_only or used_right != composite_only:
        raise ValueError("all frozen external swing disagreements must pair by type")
    return result


def _restore_disagreement_hours_for_diagnosis(
    actual_bars: Sequence[OhlcvBar],
    *,
    disagreement_observations: Sequence[CompositeReferenceObservation],
    provider_bars: Mapping[str, Sequence[OhlcvBar]],
) -> tuple[OhlcvBar, ...]:
    result = {bar.timestamp: bar for bar in actual_bars}
    by_provider = {
        provider_id: {bar.timestamp: bar for bar in bars}
        for provider_id, bars in provider_bars.items()
    }
    for observation in disagreement_observations:
        timestamp = observation.observation_time
        bars = [by_provider[provider_id][timestamp] for provider_id in REQUIRED_COMPOSITE_PROVIDER_IDS]
        result[timestamp] = OhlcvBar(
            timestamp=timestamp,
            exchange="cross_venue_reference",
            symbol="BTC/USD",
            timeframe="1h",
            open=_median(tuple(item.open for item in bars)),
            high=_median(tuple(item.high for item in bars)),
            low=_median(tuple(item.low for item in bars)),
            close=_median(tuple(item.close for item in bars)),
            volume=Decimal("0"),
            provider=MEDIAN_OHLC_VERSION.lower(),
            ingested_at=timestamp + timedelta(hours=1) + DEFAULT_DECISION_DELAY,
        )
    return tuple(result[item] for item in sorted(result))


def _source_level_effects(
    consensus_key: tuple[str, datetime],
    composite_key: tuple[str, datetime],
    *,
    states: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    provider_events = set()
    for provider_id in REQUIRED_COMPOSITE_PROVIDER_IDS:
        for key, item in states[provider_id]["breakout_reclaim"].items():
            if item.source_level_timestamp == consensus_key[1]:
                provider_events.add((item.level_type, item.confirmation_timestamp))
    composite_events = {
        (item.level_type, item.confirmation_timestamp)
        for item in states[PRIMARY_METHOD_VERSION]["breakout_reclaim"].values()
        if item.source_level_timestamp == composite_key[1]
    }
    provider_counts = Counter(
        (item.level_type, item.confirmation_timestamp)
        for provider_id in REQUIRED_COMPOSITE_PROVIDER_IDS
        for item in states[provider_id]["breakout_reclaim"].values()
        if item.source_level_timestamp == consensus_key[1]
    )
    provider_consensus = {item for item, count in provider_counts.items() if count >= 2}
    return {
        "provider_consensus_breakout_reclaim_events": sorted(provider_consensus),
        "provider_any_breakout_reclaim_events": sorted(provider_events),
        "composite_breakout_reclaim_events": sorted(composite_events),
        "breakout_or_reclaim_state_changed": composite_events != provider_consensus,
    }


def _swing_metric_summary(
    consensus: Mapping[tuple[str, datetime], Any],
    composite: Mapping[tuple[str, datetime], Any],
    *,
    records: Sequence[Mapping[str, Any]],
    stop_difference_count: int,
    mfe_difference: Decimal,
    mae_difference: Decimal,
) -> dict[str, Any]:
    exact_difference = set(consensus) ^ set(composite)
    exact_union = set(consensus) | set(composite)
    pair_records = {
        item["pair_id"]: item for item in records if item["disagreement_side"] == "consensus_only"
    }
    result = {
        "exact_timestamp": _metric(len(exact_difference), len(exact_union)),
    }
    for weeks in (1, 2):
        matched_pair_count = sum(
            item["timestamp_difference_weeks"] <= weeks
            for item in pair_records.values()
        )
        unresolved = 2 * (len(pair_records) - matched_pair_count)
        fuzzy_union = len(exact_union) - matched_pair_count
        result[f"within_{weeks}_week"] = _metric(unresolved, fuzzy_union)
    result["atr_material_grid"] = {
        str(threshold): _metric(
            sum(
                2
                for item in pair_records.values()
                if item["atr_normalized_difference"] is None
                or item["atr_normalized_difference"] > threshold
            ),
            len(exact_union),
        )
        for threshold in DIAGNOSTIC_ATR_GRID
    }
    structural_count = sum(
        2
        for item in pair_records.values()
        if item["downstream_consequences"]["breakout_or_reclaim_state_changed"]
    )
    trade_material = (
        stop_difference_count > 0
        or mfe_difference >= MATERIAL_PATH_DIFFERENCE
        or mae_difference >= MATERIAL_PATH_DIFFERENCE
    )
    result["structural_state"] = _metric(structural_count, len(exact_union))
    result["stop_impact"] = _metric(
        len(exact_difference) if stop_difference_count else 0,
        len(exact_union),
    )
    result["trade_or_risk_material"] = _metric(
        len(exact_difference) if trade_material else 0,
        len(exact_union),
    )
    return result


def _consensus_alternatives(
    states: Mapping[str, Mapping[str, Any]],
    composite: Mapping[tuple[str, datetime], Any],
) -> list[dict[str, Any]]:
    exact = _exact_provider_swing_consensus(states)
    result = []
    for weeks in (0, 1, 2):
        clusters = _temporal_provider_consensus(states, tolerance_weeks=weeks)
        unmatched = _unmatched_fuzzy_count(set(clusters), set(composite), weeks=weeks)
        union_count = len(clusters) + len(composite) - (
            (len(clusters) + len(composite) - unmatched) // 2
        )
        result.append(
            {
                "definition": "exact_timestamp" if weeks == 0 else f"within_{weeks}_week",
                "provider_consensus_event_count": len(clusters),
                "disagreement_count": unmatched,
                "disagreement_rate": _ratio(unmatched, union_count),
            }
        )
    result.append(
        {
            "definition": "price_zone_atr_grid_within_2_weeks",
            "provider_consensus_event_count": len(exact),
            "diagnostic_grid": [str(value) for value in DIAGNOSTIC_ATR_GRID],
            "note": (
                "ATR materiality is reported against the frozen exact consensus "
                "in metrics. No single price-zone threshold is selected."
            ),
        }
    )
    return result


def _temporal_provider_consensus(
    states: Mapping[str, Mapping[str, Any]],
    *,
    tolerance_weeks: int,
) -> dict[tuple[str, datetime], dict[str, Any]]:
    if tolerance_weeks == 0:
        return _exact_provider_swing_consensus(states)
    events = sorted(
        (
            level_type,
            timestamp,
            provider_id,
            level,
        )
        for provider_id in REQUIRED_COMPOSITE_PROVIDER_IDS
        for (level_type, timestamp), level in states[provider_id]["swings"].items()
    )
    clusters: list[list[tuple[str, datetime, str, Any]]] = []
    for event in events:
        matching = next(
            (
                cluster
                for cluster in reversed(clusters)
                if cluster[0][0] == event[0]
                and abs((event[1] - cluster[-1][1]).days) <= tolerance_weeks * 7
                and event[2] not in {item[2] for item in cluster}
            ),
            None,
        )
        if matching is None:
            clusters.append([event])
        else:
            matching.append(event)
    result = {}
    for cluster in clusters:
        providers = {item[2] for item in cluster}
        if len(providers) < 2:
            continue
        representative = sorted(item[1] for item in cluster)[(len(cluster) - 1) // 2]
        result[(cluster[0][0], representative)] = {
            "price": _median(tuple(item[3].price for item in cluster)),
            "provider_timestamps": {item[2]: item[1] for item in cluster},
        }
    return result


def _unmatched_fuzzy_count(
    left: set[tuple[str, datetime]],
    right: set[tuple[str, datetime]],
    *,
    weeks: int,
) -> int:
    candidates = sorted(
        (
            abs((left_item[1] - right_item[1]).days),
            left_item,
            right_item,
        )
        for left_item in left
        for right_item in right
        if left_item[0] == right_item[0]
        and abs((left_item[1] - right_item[1]).days) <= weeks * 7
    )
    used_left = set()
    used_right = set()
    for _, left_item, right_item in candidates:
        if left_item in used_left or right_item in used_right:
            continue
        used_left.add(left_item)
        used_right.add(right_item)
    return len(left - used_left) + len(right - used_right)


def _quality_state_analysis(
    observations: Sequence[CompositeReferenceObservation],
    *,
    provider_by_time: Mapping[str, Mapping[datetime, OhlcvBar]],
    trailing_atr: Mapping[datetime, Decimal],
    swing_analysis: Mapping[str, Any],
) -> dict[str, Any]:
    counts = Counter(item.quality_state for item in observations)
    unresolved = []
    for item in observations:
        if item.quality_state != VENUE_DISAGREEMENT:
            continue
        bars = {
            provider_id: provider_by_time[provider_id][item.observation_time]
            for provider_id in item.input_providers_available
        }
        atr = trailing_atr.get(item.observation_time)
        week = _week_start(item.observation_time)
        linked_pairs = sorted(
            {
                record["pair_id"]
                for record in swing_analysis["records"]
                if week
                in (record["consensus_timestamp"], record["composite_timestamp"])
            }
        )
        unresolved.append(
            {
                "timestamp": item.observation_time,
                "classification": GENUINE_CROSS_MARKET_VOLATILITY
                if atr
                and all(
                    (bar.high - bar.low) / atr
                    >= DEFAULT_TWO_PROVIDER_RANGE_DISAGREEMENT_ATR
                    for bar in bars.values()
                )
                else UNRESOLVED,
                "provider_ohlc": {
                    provider_id: _ohlc_record(bar)
                    for provider_id, bar in bars.items()
                },
                "diagnostics": item.diagnostics.as_record(),
                "reason_codes": list(item.reason_codes),
                "reference_usable": False,
                "weekly_bucket": week,
                "complete_week_omitted_from_frozen_composite": True,
                "linked_swing_pair_ids": linked_pairs,
                "structural_effect": bool(linked_pairs),
                "stop_touch_effect": bool(
                    swing_analysis["metrics"]["stop_impact"]["disagreement_count"]
                ),
                "trade_or_risk_material_effect": bool(
                    swing_analysis["metrics"]["trade_or_risk_material"][
                        "disagreement_count"
                    ]
                ),
            }
        )
    expected = len(observations)
    usable = sum(item.usable for item in observations)
    return {
        "quality_state_counts": dict(counts),
        "reference_degraded": {
            "bar_count": counts[REFERENCE_DEGRADED],
            "rate": _ratio(counts[REFERENCE_DEGRADED], expected),
            "reference_usable": True,
        },
        "reference_unavailable": {
            "bar_count": counts[REFERENCE_UNAVAILABLE],
            "rate": _ratio(counts[REFERENCE_UNAVAILABLE], expected),
        },
        "unresolved_venue_disagreement": {
            "bar_count": counts[VENUE_DISAGREEMENT],
            "rate": _ratio(counts[VENUE_DISAGREEMENT], expected),
            "records": unresolved,
            "causal_swing_link": (
                "The three unusable hours make the 2020-03-09 and 2021-04-12 "
                "weekly buckets incomplete. The research-only restoration diagnostic "
                "tests whether those omissions explain the paired swing differences."
            ),
            "restoration_result": swing_analysis[
                "disagreement_hour_restoration_diagnostic"
            ],
        },
        "usable_reference": {
            "bar_count": usable,
            "rate": _ratio(usable, expected),
        },
        "material_degraded": {},
    }


def _provider_attribution(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    total = len(records)
    result = {}
    for provider_id in REQUIRED_COMPOSITE_PROVIDER_IDS:
        close_outlier = sum(
            item["field_outliers"]["close"] == provider_id for item in records
        )
        high_outlier = sum(
            item["field_outliers"]["high"] == provider_id for item in records
        )
        low_outlier = sum(
            item["field_outliers"]["low"] == provider_id for item in records
        )
        stale_dislocated = sum(
            item["dominant_divergent_provider"] == provider_id
            and item["primary_classification"]
            in (PROVIDER_CLOSE_DISCONTINUITY, PERSISTENT_PROVIDER_DISLOCATION)
            for item in records
        )
        missing = sum(provider_id in item["missing_providers"] for item in records)
        agreeing = sum(provider_id in item["closest_close_pair"] for item in records)
        result[provider_id] = {
            "close_outlier": _count_rate(close_outlier, total),
            "high_outlier": _count_rate(high_outlier, total),
            "low_outlier": _count_rate(low_outlier, total),
            "stale_or_dislocated": _count_rate(stale_dislocated, total),
            "missing": _count_rate(missing, total),
            "agreeing_close_cluster_member": _count_rate(agreeing, total),
        }
    return result


def _build_summary(
    observations: Sequence[CompositeReferenceObservation],
    *,
    degraded_records: Sequence[Mapping[str, Any]],
    episodes: Sequence[Mapping[str, Any]],
    quality_analysis: Mapping[str, Any],
    swing_analysis: Mapping[str, Any],
) -> dict[str, Any]:
    expected = len(observations)
    classification_counts = Counter(
        item["primary_classification"] for item in degraded_records
    )
    episode_classification_counts = Counter(
        item["episode_classification"] for item in episodes
    )
    consequence_counts = Counter(
        item["economic_consequence"]["classification"] for item in episodes
    )
    consequence_bar_counts: Counter[str] = Counter()
    for item in episodes:
        consequence_bar_counts[
            item["economic_consequence"]["classification"]
        ] += item["degraded_bar_count"]
    material_classes = (STRUCTURAL_EFFECT, TRADE_OR_RISK_EFFECT)
    material_episodes = [
        item
        for item in episodes
        if item["economic_consequence"]["classification"] in material_classes
    ]
    material_bars = sum(item["degraded_bar_count"] for item in material_episodes)
    durations = sorted(item["duration_hours"] for item in episodes)
    classification_breakdown = {}
    for classification in DEGRADED_CLASSIFICATIONS:
        bar_count = classification_counts[classification]
        category_episodes = [
            item for item in episodes if item["episode_classification"] == classification
        ]
        if not bar_count and not category_episodes:
            continue
        classification_breakdown[classification] = {
            "bars": bar_count,
            "episodes": len(category_episodes),
            "percent_of_all_hours": _ratio(bar_count, expected),
            "material_structure_episodes": sum(
                item["economic_consequence"]["classification"] == STRUCTURAL_EFFECT
                for item in category_episodes
            ),
            "stop_impact_count": sum(
                item["economic_consequence"]["stop_touch_difference_count"]
                for item in category_episodes
            ),
            "trade_or_risk_material_episodes": sum(
                item["economic_consequence"]["classification"] == TRADE_OR_RISK_EFFECT
                for item in category_episodes
            ),
        }
    quality_analysis["material_degraded"] = {
        "bar_count": material_bars,
        "episode_count": len(material_episodes),
        "rate_of_all_hours": _ratio(material_bars, expected),
        "rate_of_degraded_hours": _ratio(material_bars, len(degraded_records)),
    }
    return {
        "evaluation_hour_count": expected,
        "total_degraded_bars": len(degraded_records),
        "total_degraded_episodes": len(episodes),
        "degraded_classification_counts": dict(classification_counts),
        "degraded_episode_classification_counts": dict(episode_classification_counts),
        "degraded_classification_breakdown": classification_breakdown,
        "degraded_episode_rate_per_evaluation_hour": _ratio(len(episodes), expected),
        "episode_duration_hours": {
            "median": _percentile(durations, Decimal("0.50")),
            "p95": _percentile(durations, Decimal("0.95")),
            "maximum": max(durations, default=0),
        },
        "economic_consequence_counts": dict(consequence_counts),
        "economic_consequence_bar_counts": dict(consequence_bar_counts),
        "economically_material_degraded_bars": material_bars,
        "economically_material_degraded_episodes": len(material_episodes),
        "economically_material_degraded_rate_all_hours": _ratio(
            material_bars, expected
        ),
        "economically_material_degraded_rate_degraded_hours": _ratio(
            material_bars, len(degraded_records)
        ),
        "unavailable_bar_count": quality_analysis["reference_unavailable"]["bar_count"],
        "unresolved_disagreement_bar_count": quality_analysis[
            "unresolved_venue_disagreement"
        ]["bar_count"],
        "unavailable_or_disagreement_rate": _ratio(
            quality_analysis["reference_unavailable"]["bar_count"]
            + quality_analysis["unresolved_venue_disagreement"]["bar_count"],
            expected,
        ),
        "usable_reference_rate": quality_analysis["usable_reference"]["rate"],
        "frozen_degraded_rate": _ratio(len(degraded_records), expected),
        "frozen_exact_swing_disagreement": swing_analysis["metrics"][
            "exact_timestamp"
        ],
        "diagnostic_within_one_week_swing_disagreement": swing_analysis["metrics"][
            "within_1_week"
        ],
        "diagnostic_within_two_weeks_swing_disagreement": swing_analysis["metrics"][
            "within_2_week"
        ],
        "diagnostic_structural_state_disagreement": swing_analysis["metrics"][
            "structural_state"
        ],
        "diagnostic_stop_impact_disagreement": swing_analysis["metrics"][
            "stop_impact"
        ],
        "diagnostic_trade_or_risk_material_disagreement": swing_analysis["metrics"][
            "trade_or_risk_material"
        ],
    }


def _governance_conclusion(summary: Mapping[str, Any]) -> str:
    degraded_material = int(summary["economically_material_degraded_episodes"])
    structural = int(
        summary["diagnostic_structural_state_disagreement"]["disagreement_count"]
    )
    trade_risk = int(
        summary["diagnostic_trade_or_risk_material_disagreement"][
            "disagreement_count"
        ]
    )
    nearby = int(
        summary["diagnostic_within_one_week_swing_disagreement"][
            "disagreement_count"
        ]
    )
    if degraded_material == 0 and structural == 0 and trade_risk == 0 and nearby == 0:
        return "V1_FAILURES_ARE_PRIMARILY_METRIC_DEFINITION_ISSUES"
    if (degraded_material or structural or trade_risk) and nearby == 0:
        return "MIXED"
    if degraded_material or structural or trade_risk:
        return "V1_FAILURES_ARE_ECONOMICALLY_MATERIAL"
    return "INSUFFICIENT_EVIDENCE"


def _external_trade_probes(
    provider_bars: Mapping[str, Sequence[OhlcvBar]],
) -> tuple[Any, ...]:
    bootstrap = tuple(
        bar
        for bar in _bootstrap_median_bars(provider_bars)
        if EXTERNAL_START - timedelta(days=28) <= bar.timestamp <= EXTERNAL_END
    )
    probe_start = max(
        EXTERNAL_START - timedelta(days=28),
        min((bar.timestamp for bar in bootstrap), default=EXTERNAL_START),
    )
    return build_weekly_trade_path_probes(
        bootstrap,
        start=probe_start,
        end=EXTERNAL_END,
    )


def _validate_v1_state(v1_artifact_dir: Path) -> None:
    hashes = _artifact_hashes(v1_artifact_dir)
    if hashes != EXPECTED_V1_ARTIFACT_SHA256:
        raise ValueError("immutable BTC_REFERENCE_COMPOSITE_V1 artifact checksum mismatch")
    decision = json.loads((v1_artifact_dir / "final_decision.json").read_text())
    if decision["decision"] != "RESEARCH_INCONCLUSIVE":
        raise ValueError("BTC_REFERENCE_COMPOSITE_V1 must remain RESEARCH_INCONCLUSIVE")
    if decision["reference_policy_version"] != REFERENCE_COMPOSITE_POLICY_VERSION:
        raise ValueError("unexpected V1 reference policy version")


def _validate_raw_evidence(raw_dir: Path, v1_artifact_dir: Path) -> None:
    external = json.loads(
        (v1_artifact_dir / "external_validation_report.json").read_text()
    )
    evidence = external["raw_artifacts"]
    manifest_path = raw_dir / "collection_manifest.json"
    if _file_sha256(manifest_path) != evidence["collection_manifest_sha256"]:
        raise ValueError("external collection manifest checksum mismatch")
    for provider_id in REQUIRED_COMPOSITE_PROVIDER_IDS:
        path = raw_dir / f"{provider_id}_btc_usd_1h.jsonl.gz"
        if _file_sha256(path) != evidence["providers"][provider_id]["sha256"]:
            raise ValueError(f"external raw artifact checksum mismatch for {provider_id}")


def _v2_research_proposal() -> dict[str, Any]:
    return {
        "status": "PROPOSED_NOT_IMPLEMENTED",
        "version": "BTC_REFERENCE_COMPOSITE_V2",
        "candidate_methodology": (
            "Retain MEDIAN_OHLC_V1 as the leading formula candidate; study quality-state "
            "and incomplete-period semantics before introducing any new formula."
        ),
        "quality_state_semantics": {
            "degraded": (
                "Usable two-provider or partial-consensus reference with separately "
                "persisted cause, episode, and materiality diagnostics."
            ),
            "unavailable": (
                "No publishable hourly reference. Weekly aggregation must explicitly "
                "persist incomplete-bucket state rather than silently remove the week."
            ),
            "unresolved_disagreement": (
                "Separate from missing input and from usable degraded consensus."
            ),
        },
        "swing_consensus_semantics": (
            "Keep exact timestamps, add predeclared +/-1w, +/-2w, ATR-grid, "
            "structural-state, stop, and trade/risk material metrics."
        ),
        "approval_metrics": [
            "usable_reference_rate",
            "unavailable_and_unresolved_rate",
            "degraded_episode_rate",
            "economically_material_degraded_rate",
            "exact_and_temporal_swing_disagreement",
            "atr_material_swing_disagreement_grid",
            "structural_state_disagreement",
            "stop_impact_disagreement",
            "trade_or_risk_material_disagreement",
        ],
        "threshold_policy": (
            "Freeze thresholds and the complete 0.10/0.20/0.30/0.50/1.00 ATR grid "
            "before opening any V2 validation sample."
        ),
        "point_in_time_rules": (
            "Retain close + 5 minute decision time, require input available_at <= "
            "decision time, use prior completed ATR only, and prohibit implicit splicing."
        ),
        "untouched_validation": {
            "inspected_and_ineligible_as_pristine_oos": "2020-01-01 through 2025-12-31",
            "candidate_longest_historical_period": (
                "2015-07-20T21:00:00Z through 2019-11-30T23:00:00Z"
            ),
            "candidate_status": (
                "Public API boundary availability verified on 2026-08-29; bulk "
                "completeness remains unmeasured and must be frozen before collection."
            ),
            "coverage_boundary_evidence": {
                "coinbase": {
                    "instrument": "BTC-USD",
                    "first_public_1h_candle": "2015-07-20T21:00:00Z",
                    "documentation": (
                        "https://docs.cdp.coinbase.com/api-reference/exchange-api/"
                        "rest-api/products/get-product-candles"
                    ),
                },
                "bitstamp": {
                    "instrument": "BTC/USD",
                    "candle_present_at_common_start": True,
                    "documentation": "https://www.bitstamp.net/api/#ohlc_data",
                },
                "bitfinex": {
                    "instrument": "tBTCUSD",
                    "candle_present_at_common_start": True,
                    "documentation": "https://docs.bitfinex.com/reference/rest-public-candles",
                },
                "inspection_scope": (
                    "Coverage-boundary metadata only; no cross-provider outcomes, "
                    "gate tuning, or V2 metric design used this historical sample."
                ),
            },
            "required_supplement": "future live-shadow validation",
        },
        "migration_and_governance": (
            "Create new versioned policy, method, persistence metadata, migration, and "
            "reviewed approval decision; never rewrite V1 rows or artifacts."
        ),
    }


def _artifact_hashes(path: Path) -> dict[str, str]:
    return {
        item.name: hashlib.sha256(item.read_bytes()).hexdigest()
        for item in sorted(path.iterdir())
        if item.is_file()
    }


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _one_hour_return(current: OhlcvBar, previous: OhlcvBar | None) -> Decimal | None:
    if previous is None or previous.close <= 0:
        return None
    return current.close / previous.close - 1


def _open_gap_bps(current: OhlcvBar, previous: OhlcvBar | None) -> Decimal | None:
    if previous is None or previous.close <= 0:
        return None
    return abs(current.open - previous.close) / previous.close * 10000


def _field_outlier(bars: Mapping[str, OhlcvBar], field: str) -> str | None:
    if len(bars) != 3:
        return None
    center = _median(tuple(getattr(item, field) for item in bars.values()))
    ranked = sorted(
        (
            abs(getattr(bar, field) - center),
            provider_id,
        )
        for provider_id, bar in bars.items()
    )
    return ranked[-1][1] if ranked[-1][0] > 0 else None


def _maximum_bar_fractional_difference(
    left: Mapping[datetime, OhlcvBar],
    right: Mapping[datetime, OhlcvBar],
) -> Decimal:
    values = []
    for timestamp in set(left) & set(right):
        for field in ("open", "high", "low", "close"):
            baseline = getattr(left[timestamp], field)
            if baseline > 0:
                values.append(abs(baseline - getattr(right[timestamp], field)) / baseline)
    return max(values, default=Decimal("0"))


def _maximum_mapping_fractional_difference(
    left: Mapping[datetime, Decimal],
    right: Mapping[datetime, Decimal],
) -> Decimal:
    return max(
        (
            abs(left[item] - right[item]) / left[item]
            for item in set(left) & set(right)
            if left[item] > 0
        ),
        default=Decimal("0"),
    )


def _ohlc_record(bar: OhlcvBar) -> dict[str, Decimal]:
    return {
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
    }


def _optional_ohlc(bar: OhlcvBar | None) -> dict[str, Decimal] | None:
    return _ohlc_record(bar) if bar else None


def _week_start(timestamp: datetime) -> datetime:
    return timestamp.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
        days=timestamp.weekday()
    )


def _max_optional_decimal(values: Sequence[str | None] | Any) -> Decimal | None:
    parsed = [Decimal(value) for value in values if value is not None]
    return max(parsed) if parsed else None


def _count_rate(count: int, denominator: int) -> dict[str, Any]:
    return {"count": count, "rate": _ratio(count, denominator)}


def _metric(disagreement_count: int, denominator: int) -> dict[str, Any]:
    return {
        "disagreement_count": disagreement_count,
        "denominator": denominator,
        "disagreement_rate": _ratio(disagreement_count, denominator),
    }


def _ratio(numerator: int, denominator: int) -> Decimal:
    return Decimal(numerator) / Decimal(denominator) if denominator else Decimal("0")


def _percentile(values: Sequence[int], percentile: Decimal) -> Decimal | None:
    if not values:
        return None
    index = int((Decimal(len(values) - 1) * percentile).to_integral_value())
    return Decimal(values[index])


def _median(values: Sequence[Decimal]) -> Decimal:
    return Decimal(str(median(values)))


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, Decimal):
        return "0" if value == 0 else str(value)
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(f"cannot serialize {type(value).__name__}")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, default=_json_default, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _markdown_report(result: Mapping[str, Any]) -> str:
    summary = result["summary"]
    swing = result["swing_analysis"]
    governance = result["governance"]
    lines = [
        "# BTC-019B External Gate Diagnostics",
        "",
        "## Governance",
        "",
        f"- Diagnostic conclusion: `{governance['diagnostic_conclusion']}`",
        "- `BTC_REFERENCE_COMPOSITE_V1`: `RESEARCH_INCONCLUSIVE` (unchanged)",
        "- `PRICE_SOURCE_POLICY_V1`: unchanged",
        "- BTC-019 recommendation: `IN PROGRESS`",
        "",
        "## Degraded Reference",
        "",
        f"- Degraded bars: {summary['total_degraded_bars']}",
        f"- Contiguous episodes: {summary['total_degraded_episodes']}",
        f"- Frozen degraded rate: {summary['frozen_degraded_rate']}",
        f"- Economically material degraded bars: {summary['economically_material_degraded_bars']}",
        f"- Economically material degraded episodes: {summary['economically_material_degraded_episodes']}",
        f"- Economically equivalent: {summary['economic_consequence_bar_counts'][ECONOMICALLY_EQUIVALENT]} bars / {summary['economic_consequence_counts'][ECONOMICALLY_EQUIVALENT]} episodes",
        f"- Minor numeric difference only: {summary['economic_consequence_bar_counts'][MINOR_NUMERIC_DIFFERENCE]} bars / {summary['economic_consequence_counts'][MINOR_NUMERIC_DIFFERENCE]} episodes",
        "",
        "| Primary classification | Bars | Episodes | % hours | Structure | Stop | Trade/risk |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, item in sorted(summary["degraded_classification_breakdown"].items()):
        lines.append(
            f"| {name} | {item['bars']} | {item['episodes']} | "
            f"{item['percent_of_all_hours']} | {item['material_structure_episodes']} | "
            f"{item['stop_impact_count']} | {item['trade_or_risk_material_episodes']} |"
        )
    lines.extend(
        [
            "",
            "The frozen degraded gate counts every usable quality warning equally. "
            "BTC-019B additionally measures episode-level structural and trade consequences; "
            "it does not replace or relax the failed V1 gate.",
            "",
            "| Provider | Close outlier | High outlier | Low outlier | Missing | Agreeing cluster |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for provider_id, item in result["provider_attribution"].items():
        lines.append(
            f"| {provider_id} | {item['close_outlier']['count']} | "
            f"{item['high_outlier']['count']} | {item['low_outlier']['count']} | "
            f"{item['missing']['count']} | {item['agreeing_close_cluster_member']['count']} |"
        )
    lines.extend(
        [
            "",
            "## Unusable Reference",
            "",
            f"- `REFERENCE_UNAVAILABLE`: {summary['unavailable_bar_count']}",
            f"- unresolved `VENUE_DISAGREEMENT`: {summary['unresolved_disagreement_bar_count']}",
            f"- unavailable/disagreement rate: {summary['unavailable_or_disagreement_rate']}",
            f"- usable-reference rate: {summary['usable_reference_rate']}",
            "",
            "The three disagreement hours fall in the March 2020 capitulation week "
            "and April 2021 high week. Complete-period aggregation omits those weeks, "
            "which is analyzed separately from the 286 degraded-but-usable bars.",
            "",
            "## Swing Diagnostics",
            "",
            "| Metric | Disagreements | Denominator | Rate |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for key in (
        "exact_timestamp",
        "within_1_week",
        "within_2_week",
        "structural_state",
        "stop_impact",
        "trade_or_risk_material",
    ):
        item = swing["metrics"][key]
        lines.append(
            f"| {key} | {item['disagreement_count']} | {item['denominator']} | "
            f"{item['disagreement_rate']} |"
        )
    lines.extend(
        [
            "",
            "| Event | Side | Type | +/-1w | +/-2w | ATR distance | Classification | Stop | Trade/risk |",
            "| --- | --- | --- | --- | --- | ---: | --- | --- | --- |",
        ]
    )
    for item in swing["records"]:
        lines.append(
            f"| {item['event_timestamp'].isoformat()} | {item['disagreement_side']} | "
            f"{item['event_type']} | {item['within_one_week']} | "
            f"{item['within_two_weeks']} | {item['atr_normalized_difference']} | "
            f"{item['classification']} | "
            f"{item['downstream_consequences']['stop_touch_difference']} | "
            f"{item['downstream_consequences']['mfe_material_difference'] or item['downstream_consequences']['mae_material_difference']} |"
        )
    lines.extend(
        [
            "",
            "| ATR threshold | Material disagreements | Denominator | Rate |",
            "| ---: | ---: | ---: | ---: |",
        ]
    )
    for threshold, item in swing["metrics"]["atr_material_grid"].items():
        lines.append(
            f"| {threshold} | {item['disagreement_count']} | {item['denominator']} | "
            f"{item['disagreement_rate']} |"
        )
    lines.extend(
        [
            "",
            "All four frozen exact disagreements remain recorded. The nearby-week and "
            "ATR grids are research-only diagnostics; they do not retroactively pass V1.",
            "",
            "## Gate Assessment",
            "",
            governance["degraded_rate_gate_assessment"],
            "",
            governance["exact_swing_gate_assessment"],
            "",
            "## V2 Research Recommendation",
            "",
            "Propose a separately governed `BTC_REFERENCE_COMPOSITE_V2` study focused "
            "on quality-state semantics and complete-period behavior, while retaining "
            "median OHLC as the leading candidate. Predeclare degraded, unavailable, "
            "temporal swing-consensus, ATR-grid, structural-state, and trade-risk gates. "
            "Use only point-in-time inputs and prohibit unversioned fallback splicing.",
            "",
            "The 2020-2025 history is inspected and cannot be pristine V2 out-of-sample "
            "evidence. The longest boundary-verified untouched common period is "
            "2015-07-20 21:00 UTC through 2019-11-30 23:00 UTC. Freeze and measure its "
            "bulk completeness before opening it, then supplement it with future "
            "live-shadow validation.",
            "",
            "## Limitations",
            "",
            "Setup eligibility, entry eligibility, integrated stop placement, position "
            "sizing, and action generation are not wired into the BTC-019 research pipeline. "
            "BTC-019B reports those fields as unavailable instead of inventing results.",
        ]
    )
    return "\n".join(lines) + "\n"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--v1-artifact-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = analyze_btc019b(args.raw_dir, args.v1_artifact_dir)
    write_btc019b_artifacts(result, args.output_dir)


if __name__ == "__main__":
    main()
