"""BTC-019 completion-gate assessment.

BTC-019 closes only when a production canonical reference is explicitly
approved under a versioned policy. This module measures, from immutable
provider facts alone, whether the repository's evidence supports that approval
today, and persists the exact blockers when it does not.

It approves nothing, promotes nothing, opens no sealed sample, and mutates no
frozen artifact. Every number it reports is recomputed from the collected raw
histories and the authoritative owners, so the same immutable inputs produce
the same assessment on any machine.

The measurement it adds to the existing BTC-019 evidence is the EPIC E/E2
invariant applied to the price-source research path: adjacent rows are not
adjacent calendar sessions. A provider outage removes a whole canonical
session, and the weekly structural owner reads its window by row, so an
omitted week is silently read as if the weeks either side of it were
neighbours.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from btc_predictor.data import OhlcvBar, build_canonical_market_bars
from btc_predictor.features.rolling import average_true_range
from btc_predictor.levels import (
    DEFAULT_WEEKLY_SWING_LEFT_BARS,
    DEFAULT_WEEKLY_SWING_RIGHT_BARS,
    detect_breakout_reclaim_levels,
    detect_weekly_swing_levels,
)
from btc_predictor.research.btc019_empirical import load_raw_history
from btc_predictor.research.price_source_policy import (
    BITSTAMP_PROVIDER_ID,
    PRICE_SOURCE_POLICY_VERSION,
    REQUIRED_POLICY_PROVIDER_IDS,
    _atr_fraction_series,
    _atr_value_series,
    _daily_returns,
)


COMPLETION_GATE_VERSION = "BTC019_COMPLETION_GATE_ASSESSMENT_V1"
COMPLETION_GATE_OUTCOME = "BLOCKED_BY_UNRESOLVED_CORRECTNESS_DEFECT"
PRODUCTION_CANONICAL_REFERENCE = "UNRESOLVED"

OMITTED_SESSION_ADJACENT = "OMITTED_SESSION_ADJACENT"
SOURCE_DIFFERENCE_ONLY = "SOURCE_DIFFERENCE_ONLY"

COMPLETION_GATE_REASON_CODES = (
    "BTC019_NO_APPROVED_CANONICAL_REFERENCE",
    "BTC019_STRUCTURAL_EVIDENCE_CONFOUNDED_BY_OMITTED_SESSIONS",
    "BTC019_RESEARCH_HELPER_BRIDGES_ABSENT_SESSION",
    "BTC019_V2_SEALED_SAMPLE_PRECONDITION_UNMET",
    "BTC019_V2_VALIDATOR_ABSENT",
    "BTC019_V2_SEALED_SAMPLE_NOT_COLLECTED",
)

# Collected, already-inspected samples. The sealed BTC_REFERENCE_COMPOSITE_V2
# validation history (2015-07-20 21:00 UTC .. 2019-11-30 23:00 UTC) is not one
# of them and is not touched here.
INSPECTED_SAMPLE_DIRS = (
    "data/btc019/2023-01-01_2025-12-31",
    "data/btc_reference_composite_v1/external_2019-12-01_2022-12-31",
)

_ATR_WINDOW_DAYS = 14


@dataclass(frozen=True)
class SessionCensus:
    """How many canonical sessions a provider's own history cannot produce."""

    provider: str
    hourly_bar_count: int
    daily_bar_count: int
    omitted_daily_sessions: tuple[datetime, ...]
    weekly_bar_count: int
    omitted_weekly_sessions: tuple[datetime, ...]

    def as_record(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "hourly_bar_count": self.hourly_bar_count,
            "daily_bar_count": self.daily_bar_count,
            "omitted_daily_session_count": len(self.omitted_daily_sessions),
            "omitted_daily_sessions": [
                item.isoformat() for item in self.omitted_daily_sessions
            ],
            "weekly_bar_count": self.weekly_bar_count,
            "omitted_weekly_session_count": len(self.omitted_weekly_sessions),
            "omitted_weekly_sessions": [
                item.isoformat() for item in self.omitted_weekly_sessions
            ],
        }


@dataclass(frozen=True)
class StructuralDifference:
    """One structural outcome present in exactly one of two provider series."""

    comparison: str
    present_in: str
    level_type: str
    level_timestamp: datetime
    confirmation_timestamp: datetime | None
    classification: str

    def as_record(self) -> dict[str, Any]:
        return {
            "comparison": self.comparison,
            "present_in": self.present_in,
            "level_type": self.level_type,
            "level_timestamp": self.level_timestamp.isoformat(),
            "confirmation_timestamp": (
                None
                if self.confirmation_timestamp is None
                else self.confirmation_timestamp.isoformat()
            ),
            "classification": self.classification,
        }


@dataclass(frozen=True)
class HelperAdjacencyCensus:
    """Where a BTC-019 research helper publishes across an absent session."""

    provider: str
    helper: str
    published_observation_count: int
    session_aware_observation_count: int
    bridged_observation_count: int
    bridged_observations: tuple[datetime, ...]

    def as_record(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "helper": self.helper,
            "published_observation_count": self.published_observation_count,
            "session_aware_observation_count": self.session_aware_observation_count,
            "bridged_observation_count": self.bridged_observation_count,
            "bridged_observations": [
                item.isoformat() for item in self.bridged_observations
            ],
        }


def load_inspected_sample(sample_dir: Path) -> dict[str, tuple[OhlcvBar, ...]]:
    """Load one collected sample after checking its recorded artifact digests.

    The manifest records a SHA-256 per provider artifact. A sample whose bytes
    no longer match is not the history the frozen evidence was drawn from, so
    it is refused rather than silently reassessed.
    """

    manifest = json.loads((sample_dir / "collection_manifest.json").read_text())
    if manifest["price_source_policy_version"] != PRICE_SOURCE_POLICY_VERSION:
        raise ValueError("collected sample was not gathered under the V1 policy")
    histories = {}
    for provider in manifest["providers"]:
        path = sample_dir / f"{provider['provider']}_btc_usd_1h.jsonl.gz"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != provider["raw_artifact_sha256"]:
            raise ValueError(f"collected artifact digest mismatch: {path}")
        histories[provider["provider"]] = load_raw_history(path)
    missing = set(REQUIRED_POLICY_PROVIDER_IDS) - set(histories)
    if missing:
        raise ValueError(f"collected sample is missing required providers: {sorted(missing)}")
    return histories


def sample_evaluation_time(histories: Mapping[str, Sequence[OhlcvBar]]) -> datetime:
    """Return the sample's own latest ingestion instant.

    Deriving the cutoff from the data keeps the assessment reproducible: it
    carries no wall-clock input and exposes no observation the collection did
    not already hold.
    """

    return max(bar.ingested_at for bars in histories.values() for bar in bars)


def session_census(
    bars: Sequence[OhlcvBar],
    *,
    as_of: datetime,
) -> SessionCensus:
    """Count the canonical daily/weekly sessions this provider cannot produce."""

    provider = {bar.provider for bar in bars}
    if len(provider) != 1:
        raise ValueError("session census requires one provider series")
    daily = _canonical_series(bars, as_of=as_of, timeframe="1d")
    weekly = _canonical_series(bars, as_of=as_of, timeframe="1w")
    return SessionCensus(
        provider=provider.pop(),
        hourly_bar_count=len(bars),
        daily_bar_count=len(daily),
        omitted_daily_sessions=_omitted_sessions(daily, step=timedelta(days=1)),
        weekly_bar_count=len(weekly),
        omitted_weekly_sessions=_omitted_sessions(weekly, step=timedelta(weeks=1)),
    )


def structural_differences(
    histories: Mapping[str, Sequence[OhlcvBar]],
    *,
    baseline_provider_id: str,
    as_of: datetime,
) -> tuple[StructuralDifference, ...]:
    """Compare weekly structure against the baseline and mark omitted-week reach.

    A difference is ``OMITTED_SESSION_ADJACENT`` when either compared series
    omits a weekly session inside the detector's own confirmation reach of the
    level. Those are exactly the weeks whose absence the row-indexed window
    cannot see, so the difference measures availability at least as much as it
    measures venue disagreement.
    """

    weekly = {
        provider_id: _canonical_series(bars, as_of=as_of, timeframe="1w")
        for provider_id, bars in histories.items()
    }
    omitted = {
        provider_id: _omitted_sessions(bars, step=timedelta(weeks=1))
        for provider_id, bars in weekly.items()
    }
    swings = {
        provider_id: detect_weekly_swing_levels(bars, as_of=as_of)
        for provider_id, bars in weekly.items()
    }
    breakouts = {
        provider_id: detect_breakout_reclaim_levels(
            swings[provider_id],
            weekly[provider_id],
            as_of=as_of,
        )
        for provider_id in weekly
    }
    differences = []
    for provider_id in sorted(set(weekly) - {baseline_provider_id}):
        comparison = f"{baseline_provider_id}_vs_{provider_id}"
        reach = (omitted[baseline_provider_id], omitted[provider_id])
        baseline_swings = {
            (level.level_type, level.level_timestamp) for level in swings[baseline_provider_id]
        }
        candidate_swings = {
            (level.level_type, level.level_timestamp) for level in swings[provider_id]
        }
        for level_type, timestamp in sorted(
            baseline_swings ^ candidate_swings,
            key=lambda item: (item[1], item[0]),
        ):
            differences.append(
                StructuralDifference(
                    comparison=comparison,
                    present_in=(
                        baseline_provider_id
                        if (level_type, timestamp) in baseline_swings
                        else provider_id
                    ),
                    level_type=level_type,
                    level_timestamp=timestamp,
                    confirmation_timestamp=None,
                    classification=_adjacency_classification((timestamp,), reach),
                )
            )
        baseline_levels = {
            (level.level_type, level.source_level_timestamp, level.confirmation_timestamp)
            for level in breakouts[baseline_provider_id]
        }
        candidate_levels = {
            (level.level_type, level.source_level_timestamp, level.confirmation_timestamp)
            for level in breakouts[provider_id]
        }
        for level_type, timestamp, confirmation in sorted(
            baseline_levels ^ candidate_levels,
            key=lambda item: (item[2], item[1], item[0]),
        ):
            differences.append(
                StructuralDifference(
                    comparison=comparison,
                    present_in=(
                        baseline_provider_id
                        if (level_type, timestamp, confirmation) in baseline_levels
                        else provider_id
                    ),
                    level_type=level_type,
                    level_timestamp=timestamp,
                    confirmation_timestamp=confirmation,
                    classification=_adjacency_classification(
                        (timestamp, confirmation),
                        reach,
                    ),
                )
            )
    return tuple(differences)


def helper_adjacency_census(
    bars: Sequence[OhlcvBar],
    *,
    as_of: datetime,
) -> tuple[HelperAdjacencyCensus, ...]:
    """Measure where the BTC-019 helpers publish across an absent daily session.

    ``btc_predictor.features.rolling`` is the BTC-041 owner and reports a range
    whose preceding session is absent as undefined. The three BTC-019 research
    helpers restate the formula over ``zip(ordered, ordered[1:])`` instead, so
    they read a row gap as a one-period move. The difference between the two is
    the contamination this census reports.
    """

    provider = {bar.provider for bar in bars}
    if len(provider) != 1:
        raise ValueError("helper census requires one provider series")
    provider_id = provider.pop()
    daily = _canonical_series(bars, as_of=as_of, timeframe="1d")
    owner_atr = average_true_range(daily, window=_ATR_WINDOW_DAYS)
    defined_atr = {
        bar.timestamp for bar, value in zip(daily, owner_atr) if value is not None
    }
    contiguous_returns = {
        current.timestamp
        for previous, current in zip(daily, daily[1:])
        if current.timestamp - previous.timestamp == timedelta(days=1)
    }
    census = []
    for helper, published, defined in (
        ("_daily_returns", set(_daily_returns(daily)), contiguous_returns),
        (
            "_atr_fraction_series",
            set(_atr_fraction_series(daily, window_days=_ATR_WINDOW_DAYS)),
            defined_atr,
        ),
        (
            "_atr_value_series",
            set(_atr_value_series(daily, window_days=_ATR_WINDOW_DAYS)),
            defined_atr,
        ),
    ):
        bridged = tuple(sorted(published - defined))
        census.append(
            HelperAdjacencyCensus(
                provider=provider_id,
                helper=helper,
                published_observation_count=len(published),
                session_aware_observation_count=len(published & defined),
                bridged_observation_count=len(bridged),
                bridged_observations=bridged,
            )
        )
    return tuple(census)


def assess_completion_gate(
    repository_root: Path,
    *,
    sample_dirs: Sequence[str] = INSPECTED_SAMPLE_DIRS,
    baseline_provider_id: str = BITSTAMP_PROVIDER_ID,
) -> dict[str, Any]:
    """Return the reproducible BTC-019 completion-gate record."""

    samples = {}
    for relative in sample_dirs:
        histories = load_inspected_sample(repository_root / relative)
        as_of = sample_evaluation_time(histories)
        samples[relative] = {
            "evaluation_time": as_of.isoformat(),
            "session_census": [
                session_census(histories[provider_id], as_of=as_of).as_record()
                for provider_id in sorted(histories)
            ],
            "helper_adjacency_census": [
                item.as_record()
                for provider_id in sorted(histories)
                for item in helper_adjacency_census(histories[provider_id], as_of=as_of)
            ],
            "structural_differences": [
                item.as_record()
                for item in structural_differences(
                    histories,
                    baseline_provider_id=baseline_provider_id,
                    as_of=as_of,
                )
            ],
        }
    return {
        "schema_version": COMPLETION_GATE_VERSION,
        "btc019_status": "IN PROGRESS",
        "outcome": COMPLETION_GATE_OUTCOME,
        "production_canonical_reference": PRODUCTION_CANONICAL_REFERENCE,
        "price_source_policy_version": PRICE_SOURCE_POLICY_VERSION,
        "baseline_provider_id": baseline_provider_id,
        "weekly_swing_confirmation_reach_weeks": {
            "left": DEFAULT_WEEKLY_SWING_LEFT_BARS,
            "right": DEFAULT_WEEKLY_SWING_RIGHT_BARS,
        },
        "reason_codes": list(COMPLETION_GATE_REASON_CODES),
        "sealed_sample_opened": False,
        "samples": samples,
        "totals": _totals(samples),
    }


def write_completion_gate_assessment(
    repository_root: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Persist the assessment as deterministic ASCII JSON."""

    assessment = assess_completion_gate(repository_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(assessment, indent=2, sort_keys=True) + "\n",
        encoding="ascii",
    )
    return assessment


def _canonical_series(
    bars: Sequence[OhlcvBar],
    *,
    as_of: datetime,
    timeframe: str,
) -> tuple[OhlcvBar, ...]:
    return tuple(
        bar
        for bar in build_canonical_market_bars(
            bars,
            data_available_at=as_of,
            timeframes=(timeframe,),
        )
        if bar.timeframe == timeframe
    )


def _omitted_sessions(
    bars: Sequence[OhlcvBar],
    *,
    step: timedelta,
) -> tuple[datetime, ...]:
    omitted = []
    for previous, current in zip(bars, bars[1:]):
        expected = previous.timestamp + step
        while expected < current.timestamp:
            omitted.append(expected)
            expected += step
    return tuple(omitted)


def _adjacency_classification(
    timestamps: Sequence[datetime],
    reach: Sequence[Sequence[datetime]],
) -> str:
    before = timedelta(weeks=DEFAULT_WEEKLY_SWING_LEFT_BARS)
    after = timedelta(weeks=DEFAULT_WEEKLY_SWING_RIGHT_BARS)
    for omitted in reach:
        for session in omitted:
            if any(
                timestamp - before <= session <= timestamp + after
                for timestamp in timestamps
            ):
                return OMITTED_SESSION_ADJACENT
    return SOURCE_DIFFERENCE_ONLY


def _totals(samples: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    differences = [
        item for sample in samples.values() for item in sample["structural_differences"]
    ]
    census = [
        item for sample in samples.values() for item in sample["helper_adjacency_census"]
    ]
    return {
        "omitted_weekly_session_count": sum(
            item["omitted_weekly_session_count"]
            for sample in samples.values()
            for item in sample["session_census"]
        ),
        "omitted_daily_session_count": sum(
            item["omitted_daily_session_count"]
            for sample in samples.values()
            for item in sample["session_census"]
        ),
        "structural_difference_count": len(differences),
        "omitted_session_adjacent_difference_count": sum(
            item["classification"] == OMITTED_SESSION_ADJACENT for item in differences
        ),
        "helper_bridged_observation_count": sum(
            item["bridged_observation_count"] for item in census
        ),
    }
