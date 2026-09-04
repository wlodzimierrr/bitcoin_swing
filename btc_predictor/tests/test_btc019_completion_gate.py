"""BTC-019 completion-gate regressions.

BTC-019 is closed only by an approved production canonical reference. These
tests pin the two things that decide that: the frozen evidence stays exactly as
recorded, and the unresolved adjacency defect that keeps the sealed
`BTC_REFERENCE_COMPOSITE_V2` sample shut stays measured rather than assumed.
"""

import ast
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from btc_predictor.data import OhlcvBar, build_canonical_market_bars
from btc_predictor.features.rolling import average_true_range, true_ranges
from btc_predictor.levels import (
    DEFAULT_WEEKLY_SWING_LEFT_BARS,
    DEFAULT_WEEKLY_SWING_RIGHT_BARS,
    detect_weekly_swing_levels,
)
from btc_predictor.research.btc019_completion_gate import (
    COMPLETION_GATE_OUTCOME,
    COMPLETION_GATE_VERSION,
    INSPECTED_SAMPLE_DIRS,
    OMITTED_SESSION_ADJACENT,
    PRODUCTION_CANONICAL_REFERENCE,
    assess_completion_gate,
    helper_adjacency_census,
    load_inspected_sample,
    sample_evaluation_time,
    session_census,
    structural_differences,
)
from btc_predictor.research.btc019_empirical import _baseline_atr_before
from btc_predictor.research.price_source_policy import (
    BITSTAMP_PROVIDER_ID,
    _atr_fraction_series,
    _atr_value_series,
    _daily_returns,
)
from btc_predictor.research.reference_composite_v2 import (
    UNTOUCHED_OOS_END,
    UNTOUCHED_OOS_START,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ASSESSMENT_PATH = (
    REPOSITORY_ROOT / "research_artifacts/btc019_completion_gate/completion_gate_assessment.json"
)
BTC019_ARTIFACTS = REPOSITORY_ROOT / "research_artifacts/btc019/PRICE_SOURCE_POLICY_V1"
COMPOSITE_ARTIFACTS = REPOSITORY_ROOT / "research_artifacts/btc_reference_composite"

WEEK = timedelta(weeks=1)
DAY = timedelta(days=1)


def committed_assessment() -> dict:
    return json.loads(ASSESSMENT_PATH.read_text())


def weekly_bar(index: int, *, high: int, low: int) -> OhlcvBar:
    timestamp = datetime(2020, 1, 6, tzinfo=UTC) + index * WEEK
    return OhlcvBar(
        provider="composite",
        exchange="composite",
        symbol="BTC/USD",
        timeframe="1w",
        timestamp=timestamp,
        open=Decimal(low),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(low),
        volume=None,
        ingested_at=timestamp + WEEK,
    )


def daily_bar(index: int, *, high: int, low: int, close: int) -> OhlcvBar:
    timestamp = datetime(2021, 1, 1, tzinfo=UTC) + index * DAY
    return OhlcvBar(
        provider="bitstamp",
        exchange="bitstamp",
        symbol="BTC/USD",
        timeframe="1d",
        timestamp=timestamp,
        open=Decimal(close),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=None,
        ingested_at=timestamp + DAY,
    )


# --- no candidate is approved -------------------------------------------------


def test_no_candidate_carries_an_approval_and_the_reference_stays_unresolved() -> None:
    """Rejecting Bitstamp promoted nothing, and neither did the composites."""

    decision = json.loads((BTC019_ARTIFACTS / "canonical_source_decision.json").read_text())
    assert decision["candidate_provider"] == BITSTAMP_PROVIDER_ID
    assert decision["decision"] == "REJECTED"
    assert decision["isolated_wick_risk_acceptable"] is False

    report = json.loads((BTC019_ARTIFACTS / "comparison_report.json").read_text())
    assert report["canonical_provider_approved"] is False

    composite_v1 = json.loads(
        (COMPOSITE_ARTIFACTS / "BTC_REFERENCE_COMPOSITE_V1/final_decision.json").read_text()
    )
    assert composite_v1["decision"] == "RESEARCH_INCONCLUSIVE"
    assert composite_v1["gate_results"]["external_combined_swing_disagreement_rate"] is False
    assert composite_v1["gate_results"]["external_degraded_reference_rate"] is False

    composite_v2 = json.loads(
        (COMPOSITE_ARTIFACTS / "BTC_REFERENCE_COMPOSITE_V2/protocol_definition.json").read_text()
    )
    assert composite_v2["status"] == "FROZEN_RESEARCH_PROTOCOL"
    assert composite_v2["research_only"] is True
    assert composite_v2["production_promotion_authorized"] is False
    assert composite_v2["governance"]["production_canonical_reference"] == "UNRESOLVED"
    assert composite_v2["governance"]["btc019_status"] == "IN PROGRESS"


def test_no_production_module_reads_a_research_reference_candidate() -> None:
    """A research composite must not reach strategy, backtest or advisory code."""

    research_only = ("reference_composite", "btc019_empirical", "btc019b_diagnostics",
                     "price_source_policy", "btc019_completion_gate")
    offenders = []
    for path in sorted(REPOSITORY_ROOT.glob("btc_predictor/**/*.py")):
        relative = path.relative_to(REPOSITORY_ROOT).as_posix()
        if relative.startswith(("btc_predictor/research/", "btc_predictor/tests/")):
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                module = node.module
            elif isinstance(node, ast.Import):
                module = node.names[0].name
            else:
                continue
            if module.startswith("btc_predictor.research.") and any(
                module.endswith(name) for name in research_only
            ):
                offenders.append(f"{relative}: {module}")
    assert offenders == []


# --- sealed sample ------------------------------------------------------------


def test_the_sealed_v2_sample_is_not_collected_and_is_not_opened_here() -> None:
    """No inspected sample overlaps the sealed window, and none was added."""

    assessment = committed_assessment()
    assert assessment["sealed_sample_opened"] is False
    assert tuple(assessment["samples"]) == tuple(INSPECTED_SAMPLE_DIRS)

    for relative in INSPECTED_SAMPLE_DIRS:
        histories = load_inspected_sample(REPOSITORY_ROOT / relative)
        earliest = min(bar.timestamp for bars in histories.values() for bar in bars)
        latest = max(bar.timestamp for bars in histories.values() for bar in bars)
        assert not (earliest <= UNTOUCHED_OOS_END and latest >= UNTOUCHED_OOS_START)

    collected = {
        path.parent.relative_to(REPOSITORY_ROOT).as_posix()
        for path in REPOSITORY_ROOT.glob("data/**/collection_manifest.json")
    }
    assert collected == set(INSPECTED_SAMPLE_DIRS)


def test_collected_provider_history_reproduces_its_recorded_digests() -> None:
    """The samples the frozen evidence was drawn from are byte-identical."""

    for relative in INSPECTED_SAMPLE_DIRS:
        histories = load_inspected_sample(REPOSITORY_ROOT / relative)
        assert set(histories) == {"bitstamp", "coinbase", "bitfinex"}
        assert all(histories.values())


# --- the defect that keeps the sample sealed ----------------------------------


def test_weekly_swing_detection_reads_adjacent_rows_as_adjacent_weeks() -> None:
    """Removing one week confirms a swing the complete calendar does not hold.

    Owner: `btc_predictor/levels/swing.py` (EPIC E). Its output feeds structure
    scores, stops and setups, so it is pinned here rather than changed under
    BTC-019.
    """

    highs = (100, 101, 102, 130, 103, 104, 200, 105, 106, 107)
    lows = tuple(90 + index for index in range(len(highs)))
    complete = tuple(
        weekly_bar(index, high=high, low=low)
        for index, (high, low) in enumerate(zip(highs, lows))
    )
    as_of = complete[-1].timestamp + 2 * WEEK
    disqualifying_week = complete[6].timestamp

    detected = detect_weekly_swing_levels(complete, as_of=as_of)
    assert [(level.level_type, level.level_timestamp) for level in detected] == [
        ("swing_high", disqualifying_week),
    ]

    gapped = tuple(bar for bar in complete if bar.timestamp != disqualifying_week)
    detected_on_gap = detect_weekly_swing_levels(gapped, as_of=as_of)
    assert [(level.level_type, level.level_timestamp) for level in detected_on_gap] == [
        ("swing_high", complete[3].timestamp),
    ]
    assert complete[3].high < complete[6].high


def test_research_helpers_bridge_an_absent_daily_session() -> None:
    """The helpers publish across a gap the BTC-041 owner leaves undefined."""

    closes = tuple(range(100, 100 + 20))
    bars = tuple(
        daily_bar(index, high=close + 5, low=close - 5, close=close)
        for index, close in enumerate(closes)
    )
    absent = bars[15].timestamp
    gapped = tuple(bar for bar in bars if bar.timestamp != absent)
    resumed = bars[16].timestamp

    owner = average_true_range(gapped, window=14)
    defined = {bar.timestamp for bar, value in zip(gapped, owner) if value is not None}
    assert resumed not in defined

    assert resumed in _daily_returns(gapped)
    assert resumed in _atr_fraction_series(gapped, window_days=14)
    assert resumed in _atr_value_series(gapped, window_days=14)

    # The published "daily" return spans two sessions, not one, and nothing in
    # the record says so.
    bridged = _daily_returns(gapped)[resumed]
    assert bridged == (bars[16].close / bars[14].close) - Decimal("1")
    assert bridged != (bars[16].close / bars[15].close) - Decimal("1")
    assert resumed - bars[14].timestamp == 2 * DAY


def test_baseline_atr_helper_bridges_an_absent_session_too() -> None:
    """The third restated helper is measured, not assumed.

    `_baseline_atr_before` is only ever called on the Bitstamp baseline, which
    omits no session in either collected sample, so it contaminates nothing
    today. Handed a series that does have an outage, it publishes anyway.
    """

    hours = []
    for day in range(20):
        for hour in range(24):
            timestamp = datetime(2021, 1, 1, tzinfo=UTC) + day * DAY + hour * timedelta(hours=1)
            price = 100 + day
            hours.append(
                OhlcvBar(
                    provider="bitstamp",
                    exchange="bitstamp",
                    symbol="BTC/USD",
                    timeframe="1h",
                    timestamp=timestamp,
                    open=Decimal(price),
                    high=Decimal(price + 5),
                    low=Decimal(price - 5),
                    close=Decimal(price),
                    volume=Decimal("1"),
                    ingested_at=timestamp + timedelta(hours=1),
                )
            )
    absent_day = datetime(2021, 1, 16, tzinfo=UTC)
    gapped = tuple(bar for bar in hours if bar.timestamp.date() != absent_day.date())
    as_of = hours[-1].ingested_at

    daily = build_canonical_market_bars(gapped, data_available_at=as_of, timeframes=("1d",))
    assert absent_day not in {bar.timestamp for bar in daily}
    owner = average_true_range(daily, window=14)
    resumed = absent_day + DAY
    assert next(
        value for bar, value in zip(daily, owner) if bar.timestamp == resumed
    ) is None

    published = _baseline_atr_before(
        gapped,
        timestamp=resumed + DAY,
        as_of=as_of,
    )
    assert published is not None


def test_research_true_range_matches_the_btc041_owner_where_no_session_is_absent() -> None:
    """Parity evidence: the duplication is only wrong across an outage."""

    closes = tuple(range(100, 100 + 20))
    bars = tuple(
        daily_bar(index, high=close + 5, low=close - 5, close=close)
        for index, close in enumerate(closes)
    )
    owner = true_ranges(bars)
    for index in range(1, len(bars)):
        restated = max(
            bars[index].high - bars[index].low,
            abs(bars[index].high - bars[index - 1].close),
            abs(bars[index].low - bars[index - 1].close),
        )
        assert owner[index] == restated

    helper = _atr_value_series(bars, window_days=14)
    rolling = average_true_range(bars, window=14)
    session_aware = {
        bar.timestamp for bar, value in zip(bars, rolling) if value is not None
    }
    assert set(helper) <= session_aware


@pytest.mark.parametrize("relative", INSPECTED_SAMPLE_DIRS)
def test_bitstamp_omits_no_session_so_the_baseline_paths_stay_uncontaminated(
    relative: str,
) -> None:
    """Tier 1 wick ATR and the manual reviews normalize on the baseline series."""

    histories = load_inspected_sample(REPOSITORY_ROOT / relative)
    as_of = sample_evaluation_time(histories)
    census = session_census(histories[BITSTAMP_PROVIDER_ID], as_of=as_of)
    assert census.omitted_daily_sessions == ()
    assert census.omitted_weekly_sessions == ()
    assert all(
        item.bridged_observation_count == 0
        for item in helper_adjacency_census(histories[BITSTAMP_PROVIDER_ID], as_of=as_of)
    )


# --- the persisted assessment -------------------------------------------------


def test_committed_assessment_reproduces_from_the_immutable_histories() -> None:
    """Same provider facts, same record, on any machine."""

    assert assess_completion_gate(REPOSITORY_ROOT) == committed_assessment()


def test_committed_assessment_records_a_non_approval() -> None:
    assessment = committed_assessment()
    assert assessment["schema_version"] == COMPLETION_GATE_VERSION
    assert assessment["outcome"] == COMPLETION_GATE_OUTCOME
    assert assessment["production_canonical_reference"] == PRODUCTION_CANONICAL_REFERENCE
    assert assessment["btc019_status"] == "IN PROGRESS"
    assert assessment["weekly_swing_confirmation_reach_weeks"] == {
        "left": DEFAULT_WEEKLY_SWING_LEFT_BARS,
        "right": DEFAULT_WEEKLY_SWING_RIGHT_BARS,
    }
    assert "BTC019_NO_APPROVED_CANONICAL_REFERENCE" in assessment["reason_codes"]


def test_committed_assessment_pins_the_measured_contamination() -> None:
    totals = committed_assessment()["totals"]
    assert totals["omitted_weekly_session_count"] == 12
    assert totals["omitted_daily_session_count"] == 12
    assert totals["structural_difference_count"] == 40
    assert totals["omitted_session_adjacent_difference_count"] == 24
    assert totals["helper_bridged_observation_count"] == 348


def test_structural_comparison_reproduces_the_frozen_tier_three_counts() -> None:
    """The recomputed differences are the corrected frozen report's own counts."""

    histories = load_inspected_sample(REPOSITORY_ROOT / INSPECTED_SAMPLE_DIRS[0])
    differences = structural_differences(
        histories,
        baseline_provider_id=BITSTAMP_PROVIDER_ID,
        as_of=sample_evaluation_time(histories),
    )
    counts = {
        level_type: sum(item.level_type == level_type for item in differences)
        for level_type in ("swing_high", "swing_low", "breakout", "reclaim")
    }
    assert counts == {"swing_high": 4, "swing_low": 7, "breakout": 4, "reclaim": 9}

    corrected = json.loads(
        (
            REPOSITORY_ROOT
            / "research_artifacts/btc019_correction_audit/PRICE_SOURCE_POLICY_V1"
            / "comparison_report.json"
        ).read_text()
    )
    assert corrected["swing_high_difference_count"] == counts["swing_high"]
    assert corrected["swing_low_difference_count"] == counts["swing_low"]
    assert corrected["breakout_difference_count"] == counts["breakout"]
    assert corrected["reclaim_difference_count"] == counts["reclaim"]

    adjacent = [
        item for item in differences if item.classification == OMITTED_SESSION_ADJACENT
    ]
    assert len(adjacent) == 14


def test_two_frozen_swing_differences_sit_on_weeks_the_validator_never_had() -> None:
    """A venue cannot disagree about a week it holds no bar for."""

    histories = load_inspected_sample(REPOSITORY_ROOT / INSPECTED_SAMPLE_DIRS[0])
    as_of = sample_evaluation_time(histories)
    omitted = set(session_census(histories["bitfinex"], as_of=as_of).omitted_weekly_sessions)
    assert omitted == {
        datetime(2023, 3, 6, tzinfo=UTC),
        datetime(2024, 4, 29, tzinfo=UTC),
    }

    differences = structural_differences(
        histories,
        baseline_provider_id=BITSTAMP_PROVIDER_ID,
        as_of=as_of,
    )
    on_omitted_weeks = {
        item.level_timestamp
        for item in differences
        if item.comparison == "bitstamp_vs_bitfinex"
        and item.confirmation_timestamp is None
        and item.present_in == BITSTAMP_PROVIDER_ID
        and item.level_timestamp in omitted
    }
    assert on_omitted_weeks == omitted


def test_canonical_bars_keep_a_provider_outage_visible_as_an_absent_session() -> None:
    """The outage is never spliced; the whole session is simply absent."""

    histories = load_inspected_sample(REPOSITORY_ROOT / INSPECTED_SAMPLE_DIRS[0])
    as_of = sample_evaluation_time(histories)
    coinbase = build_canonical_market_bars(
        histories["coinbase"],
        data_available_at=as_of,
        timeframes=("1d",),
    )
    timestamps = {bar.timestamp for bar in coinbase}
    assert datetime(2023, 3, 4, tzinfo=UTC) not in timestamps
    assert datetime(2025, 10, 25, tzinfo=UTC) not in timestamps
    assert all(bar.provider == "coinbase" for bar in coinbase)
