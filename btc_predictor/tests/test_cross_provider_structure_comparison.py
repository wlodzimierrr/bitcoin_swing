"""CROSS_PROVIDER_STRUCTURE_COMPARISON_V2 regressions.

The contract exists to make one confusion impossible: a provider that did not
publish a weekly session must never read as a provider that disagrees about the
structure of that session. These tests derive the expected calendar
comparability from the detector's own confirmation reach rather than from the
implementation helper, pin the fail-closed boundaries, and prove that the V1
comparison still reproduces the frozen BTC-019 evidence beside it.
"""

import decimal
import gzip
import json
import shutil
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from btc_predictor.data import OhlcvBar
from btc_predictor.levels import (
    DEFAULT_WEEKLY_SWING_LEFT_BARS,
    DEFAULT_WEEKLY_SWING_RIGHT_BARS,
    detect_weekly_swing_levels,
)
from btc_predictor.research.btc019_completion_gate import (
    INSPECTED_SAMPLE_DIRS,
    load_inspected_sample,
    sample_evaluation_time,
)
from btc_predictor.research.cross_provider_structure_comparison import (
    BOTH_SERIES,
    BREAKOUT_FAMILY,
    COMPARABLE,
    COMPARABLE_EVENT_DENOMINATOR,
    COMPARISON_CONTRACT_VERSION,
    COMPARISON_OUTPUT_NAMESPACE,
    COMPARISON_REPORT_FILENAME,
    LEGACY_COMPARISON_CONTRACT_VERSION,
    NOT_COMPARABLE,
    NOT_COMPARABLE_AVAILABILITY_GAP,
    NOT_COMPARABLE_CONFIRMATION_PENDING,
    NOT_COMPARABLE_SERIES_COVERAGE,
    NOT_COMPARABLE_SOURCE_LEVEL,
    RECLAIM_FAMILY,
    REQUIRED_SESSION_ABSENT_IN_BOTH_SERIES,
    REQUIRED_SESSION_ABSENT_IN_ONE_SERIES,
    SOURCE_LEVEL_NOT_COMPARABLE,
    STRUCTURAL_AGREEMENT,
    STRUCTURAL_DISAGREEMENT,
    SWING_HIGH_FAMILY,
    SWING_LOW_FAMILY,
    WEEKLY_STRUCTURE_DETECTOR_VERSION,
    CrossProviderComparisonError,
    build_comparison_report,
    build_weekly_session_calendar,
    compare_sample,
    compare_weekly_structure,
    frozen_affected_v2_gates,
    restore_comparison_report,
    verify_comparison_report,
    weekly_structure_snapshot,
)
from btc_predictor.research.reference_composite_v2 import (
    UNTOUCHED_OOS_END,
    UNTOUCHED_OOS_START,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = REPOSITORY_ROOT / COMPARISON_OUTPUT_NAMESPACE / COMPARISON_REPORT_FILENAME

WEEK = timedelta(weeks=1)
ORIGIN = datetime(2020, 1, 6, tzinfo=UTC)

# A swing high sits at index 6 and a decoy at index 3. Removing index 6 is what
# lets the row-indexed detector confirm the decoy the complete calendar denies.
SWING_HIGHS = (100, 101, 102, 130, 103, 104, 200, 105, 106, 107, 108, 109, 110)
SWING_LOWS = tuple(90 - index for index in range(len(SWING_HIGHS)))


def weekly_bar(
    series_id: str,
    index: int,
    *,
    high: int,
    low: int,
    close: int | None = None,
    ingested_at: datetime | None = None,
) -> OhlcvBar:
    timestamp = ORIGIN + index * WEEK
    return OhlcvBar(
        provider=series_id,
        exchange=series_id,
        symbol="BTC/USD",
        timeframe="1w",
        timestamp=timestamp,
        open=Decimal(low),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(low if close is None else close),
        volume=None,
        ingested_at=timestamp + WEEK if ingested_at is None else ingested_at,
    )


def weekly_series(
    series_id: str,
    *,
    highs: tuple[int, ...] = SWING_HIGHS,
    lows: tuple[int, ...] | None = None,
    closes: tuple[int, ...] | None = None,
    omit: tuple[int, ...] = (),
) -> tuple[OhlcvBar, ...]:
    low_values = SWING_LOWS if lows is None else lows
    return tuple(
        weekly_bar(
            series_id,
            index,
            high=highs[index],
            low=low_values[index],
            close=None if closes is None else closes[index],
        )
        for index in range(len(highs))
        if index not in omit
    )


def evaluation_time(*series: tuple[OhlcvBar, ...]) -> datetime:
    return max(bar.ingested_at for bars in series for bar in bars)


def compare(
    left: tuple[OhlcvBar, ...],
    right: tuple[OhlcvBar, ...],
    *,
    as_of: datetime | None = None,
    pair: tuple[str, str] | None = None,
):
    signal_time = evaluation_time(left, right) if as_of is None else as_of
    snapshots = {
        bars[0].provider: weekly_structure_snapshot(
            bars,
            series_id=bars[0].provider,
            evaluation_time=signal_time,
        )
        for bars in (left, right)
    }
    identifiers = tuple(snapshots) if pair is None else pair
    return compare_weekly_structure(snapshots, series_pair=identifiers)


def event_for(comparison, family: str, index: int):
    session = ORIGIN + index * WEEK
    return next(
        event
        for event in comparison.events
        if event.event_family == family and event.candidate_session == session
    )


def expected_required_sessions(index: int) -> set[datetime]:
    """The confirmation calendar, derived from the detector's own reach."""

    return {
        ORIGIN + (index + offset) * WEEK
        for offset in range(
            -DEFAULT_WEEKLY_SWING_LEFT_BARS,
            DEFAULT_WEEKLY_SWING_RIGHT_BARS + 1,
        )
    }


# --- the calendar contract ----------------------------------------------------


def test_the_required_calendar_is_the_detectors_own_confirmation_reach() -> None:
    """Seven consecutive calendar weeks, centred on the candidate."""

    comparison = compare(weekly_series("alpha"), weekly_series("beta"))
    event = event_for(comparison, SWING_HIGH_FAMILY, 6)
    assert set(event.required_sessions) == expected_required_sessions(6)
    assert len(event.required_sessions) == (
        DEFAULT_WEEKLY_SWING_LEFT_BARS + DEFAULT_WEEKLY_SWING_RIGHT_BARS + 1
    )


def test_identical_contiguous_series_agree() -> None:
    comparison = compare(weekly_series("alpha"), weekly_series("beta"))
    event = event_for(comparison, SWING_HIGH_FAMILY, 6)
    assert event.comparability == COMPARABLE
    assert event.outcome == STRUCTURAL_AGREEMENT
    assert event.detected_in == ("alpha", "beta")
    assert all(
        item.outcome != STRUCTURAL_DISAGREEMENT for item in comparison.events
    )


def test_contiguous_series_that_genuinely_differ_disagree() -> None:
    """No week is missing anywhere, so the difference is about price only."""

    quieter = tuple(120 if index == 6 else value for index, value in enumerate(SWING_HIGHS))
    comparison = compare(weekly_series("alpha"), weekly_series("beta", highs=quieter))
    event = event_for(comparison, SWING_HIGH_FAMILY, 6)
    assert event.comparability == COMPARABLE
    assert event.outcome == STRUCTURAL_DISAGREEMENT
    assert event.detected_in == ("alpha",)
    assert event.availability_gap_side is None


def test_one_missing_disqualifying_week_is_not_comparable_rather_than_disagreement() -> None:
    """The exact defect the completion gate measured, refused at the contract."""

    complete = weekly_series("alpha")
    gapped = weekly_series("beta", omit=(6,))

    # The row-indexed detector still confirms the decoy the calendar denies.
    as_of = evaluation_time(complete, gapped)
    row_levels = {
        (level.level_type, level.level_timestamp)
        for level in detect_weekly_swing_levels(gapped, as_of=as_of)
    }
    assert (SWING_HIGH_FAMILY, ORIGIN + 3 * WEEK) in row_levels
    assert (SWING_HIGH_FAMILY, ORIGIN + 6 * WEEK) not in row_levels

    comparison = compare(complete, gapped)
    for index in (3, 6):
        event = event_for(comparison, SWING_HIGH_FAMILY, index)
        assert event.comparability == NOT_COMPARABLE_AVAILABILITY_GAP
        assert event.outcome == NOT_COMPARABLE
        assert event.availability_gap_side == "beta"
        assert event.missing_required_sessions["beta"] == (ORIGIN + 6 * WEEK,)
        assert event.missing_required_sessions["alpha"] == ()
    assert all(
        item.outcome != STRUCTURAL_DISAGREEMENT
        for item in comparison.events
        if item.event_family in (SWING_HIGH_FAMILY, SWING_LOW_FAMILY)
    )


def test_a_missing_week_outside_the_reach_leaves_the_event_alone() -> None:
    """Comparability is a statement about this candidate, not the whole series."""

    complete = weekly_series("alpha")
    gapped = weekly_series("beta", omit=(11,))
    assert (ORIGIN + 11 * WEEK) not in expected_required_sessions(6)

    event = event_for(compare(complete, gapped), SWING_HIGH_FAMILY, 6)
    assert event.comparability == COMPARABLE
    assert event.outcome == STRUCTURAL_AGREEMENT


@pytest.mark.parametrize("omitted", (4, 8))
def test_a_missing_week_either_side_of_the_candidate_blocks_it(omitted: int) -> None:
    """Left and right of the confirmation window are treated alike."""

    assert (ORIGIN + omitted * WEEK) in expected_required_sessions(6)
    event = event_for(
        compare(weekly_series("alpha"), weekly_series("beta", omit=(omitted,))),
        SWING_HIGH_FAMILY,
        6,
    )
    assert event.comparability == NOT_COMPARABLE_AVAILABILITY_GAP
    assert event.availability_gap_side == "beta"
    assert REQUIRED_SESSION_ABSENT_IN_ONE_SERIES in event.reason_codes


@pytest.mark.parametrize("missing_series", ("alpha", "beta"))
def test_the_record_names_which_series_lacks_the_session(missing_series: str) -> None:
    left = weekly_series("alpha", omit=(8,) if missing_series == "alpha" else ())
    right = weekly_series("beta", omit=(8,) if missing_series == "beta" else ())
    event = event_for(compare(left, right), SWING_HIGH_FAMILY, 6)
    assert event.availability_gap_side == missing_series
    assert event.missing_required_sessions[missing_series] == (ORIGIN + 8 * WEEK,)
    other = "beta" if missing_series == "alpha" else "alpha"
    assert event.missing_required_sessions[other] == ()


def test_both_series_missing_the_same_required_week_is_recorded_as_both() -> None:
    event = event_for(
        compare(weekly_series("alpha", omit=(8,)), weekly_series("beta", omit=(8,))),
        SWING_HIGH_FAMILY,
        6,
    )
    assert event.comparability == NOT_COMPARABLE_AVAILABILITY_GAP
    assert event.availability_gap_side == BOTH_SERIES
    assert REQUIRED_SESSION_ABSENT_IN_BOTH_SERIES in event.reason_codes


def test_the_series_edges_are_reported_as_coverage_not_as_an_outage() -> None:
    """A week the collection never covered is not a provider outage."""

    comparison = compare(weekly_series("alpha"), weekly_series("beta"))
    event = event_for(comparison, SWING_HIGH_FAMILY, 0)
    assert event.comparability == NOT_COMPARABLE_SERIES_COVERAGE
    assert event.availability_gap_side is None


# --- point in time ------------------------------------------------------------


def test_a_confirmation_week_that_has_not_arrived_is_pending_not_absent() -> None:
    """The detector may not borrow a week the evaluation instant cannot see."""

    left = weekly_series("alpha")
    right = weekly_series("beta")
    # Week 8 closes at ORIGIN + 9 weeks; stop just short of it.
    as_of = ORIGIN + 9 * WEEK - timedelta(hours=1)
    comparison = compare(left, right, as_of=as_of)
    event = event_for(comparison, SWING_HIGH_FAMILY, 5)
    assert (ORIGIN + 8 * WEEK) in expected_required_sessions(5)
    assert event.comparability == NOT_COMPARABLE_CONFIRMATION_PENDING
    assert event.availability_gap_side is None
    assert event.outcome == NOT_COMPARABLE


def test_appending_later_history_cannot_change_a_finished_comparison() -> None:
    as_of = ORIGIN + 9 * WEEK - timedelta(hours=1)
    baseline = compare(weekly_series("alpha"), weekly_series("beta"), as_of=as_of)
    extended = compare(
        weekly_series("alpha") + (weekly_bar("alpha", 13, high=999, low=1),),
        weekly_series("beta") + (weekly_bar("beta", 13, high=999, low=1),),
        as_of=as_of,
    )
    assert [item.as_record() for item in extended.events] == [
        item.as_record() for item in baseline.events
    ]


# --- order invariance ---------------------------------------------------------


def test_the_comparison_does_not_depend_on_provider_order() -> None:
    left = weekly_series("alpha", omit=(8,))
    right = weekly_series("beta")
    forward = compare(left, right, pair=("alpha", "beta"))
    reverse = compare(left, right, pair=("beta", "alpha"))
    assert forward.as_record() == reverse.as_record()
    assert forward.series_ids == ("alpha", "beta")


# --- fail-closed boundaries ---------------------------------------------------


def test_a_repeated_weekly_session_is_refused() -> None:
    bars = weekly_series("alpha")
    with pytest.raises(CrossProviderComparisonError, match="repeats weekly session"):
        build_weekly_session_calendar(
            bars[:6] + (bars[5],) + bars[6:],
            series_id="alpha",
            evaluation_time=evaluation_time(bars),
        )


def test_an_out_of_order_series_is_refused() -> None:
    bars = weekly_series("alpha")
    reordered = (bars[4],) + bars
    with pytest.raises(CrossProviderComparisonError, match="out of order"):
        build_weekly_session_calendar(
            reordered,
            series_id="alpha",
            evaluation_time=evaluation_time(bars),
        )


def test_an_off_cadence_timestamp_is_refused() -> None:
    bars = weekly_series("alpha")
    midweek = OhlcvBar(
        provider="alpha",
        exchange="alpha",
        symbol="BTC/USD",
        timeframe="1w",
        timestamp=ORIGIN + 13 * WEEK + timedelta(days=2),
        open=Decimal(1),
        high=Decimal(2),
        low=Decimal(1),
        close=Decimal(1),
        volume=None,
        ingested_at=ORIGIN + 15 * WEEK,
    )
    with pytest.raises(CrossProviderComparisonError, match="Monday weekly session"):
        build_weekly_session_calendar(
            bars + (midweek,),
            series_id="alpha",
            evaluation_time=ORIGIN + 20 * WEEK,
        )


def test_a_naive_timestamp_is_refused() -> None:
    bars = weekly_series("alpha")
    with pytest.raises(ValueError, match="timezone-aware"):
        build_weekly_session_calendar(
            bars,
            series_id="alpha",
            evaluation_time=datetime(2020, 6, 1),
        )


def test_two_providers_in_one_series_are_refused() -> None:
    bars = weekly_series("alpha")[:6] + weekly_series("beta")[6:]
    with pytest.raises(CrossProviderComparisonError, match="mixes provider"):
        build_weekly_session_calendar(
            bars,
            series_id="alpha",
            evaluation_time=evaluation_time(bars),
        )


def test_a_bar_without_a_provider_identity_is_refused() -> None:
    bars = weekly_series("alpha")
    anonymous = OhlcvBar(
        provider="",
        exchange="alpha",
        symbol="BTC/USD",
        timeframe="1w",
        timestamp=ORIGIN + 13 * WEEK,
        open=Decimal(1),
        high=Decimal(2),
        low=Decimal(1),
        close=Decimal(1),
        volume=None,
        ingested_at=ORIGIN + 14 * WEEK,
    )
    with pytest.raises(CrossProviderComparisonError, match="provider identity"):
        build_weekly_session_calendar(
            bars + (anonymous,),
            series_id="alpha",
            evaluation_time=ORIGIN + 20 * WEEK,
        )


def test_a_daily_series_is_refused_by_the_weekly_contract() -> None:
    daily = OhlcvBar(
        provider="alpha",
        exchange="alpha",
        symbol="BTC/USD",
        timeframe="1d",
        timestamp=ORIGIN,
        open=Decimal(1),
        high=Decimal(2),
        low=Decimal(1),
        close=Decimal(1),
        volume=None,
        ingested_at=ORIGIN + WEEK,
    )
    with pytest.raises(CrossProviderComparisonError, match="canonical 1w bars"):
        build_weekly_session_calendar(
            (daily,),
            series_id="alpha",
            evaluation_time=ORIGIN + WEEK,
        )


def test_an_unknown_detector_version_is_refused() -> None:
    bars = weekly_series("alpha")
    with pytest.raises(CrossProviderComparisonError, match="unknown structural detector"):
        weekly_structure_snapshot(
            bars,
            series_id="alpha",
            evaluation_time=evaluation_time(bars),
            detector_version="SOMETHING_ELSE_V9",
        )


def test_two_evaluation_times_cannot_be_compared() -> None:
    left = weekly_series("alpha")
    right = weekly_series("beta")
    snapshots = {
        "alpha": weekly_structure_snapshot(
            left,
            series_id="alpha",
            evaluation_time=evaluation_time(left),
        ),
        "beta": weekly_structure_snapshot(
            right,
            series_id="beta",
            evaluation_time=evaluation_time(right) + WEEK,
        ),
    }
    with pytest.raises(CrossProviderComparisonError, match="one evaluation time"):
        compare_weekly_structure(snapshots, series_pair=("alpha", "beta"))


def test_a_series_cannot_be_compared_with_itself() -> None:
    bars = weekly_series("alpha")
    snapshots = {
        "alpha": weekly_structure_snapshot(
            bars,
            series_id="alpha",
            evaluation_time=evaluation_time(bars),
        )
    }
    with pytest.raises(CrossProviderComparisonError, match="two distinct series"):
        compare_weekly_structure(snapshots, series_pair=("alpha", "alpha"))


def test_a_tampered_collected_artifact_is_refused(tmp_path: Path) -> None:
    source = REPOSITORY_ROOT / INSPECTED_SAMPLE_DIRS[0]
    copied = tmp_path / "sample"
    shutil.copytree(source, copied)
    target = copied / "coinbase_btc_usd_1h.jsonl.gz"
    rows = gzip.decompress(target.read_bytes()).decode().splitlines()
    record = json.loads(rows[0])
    record["high"] = str(Decimal(record["high"]) + Decimal("1"))
    rows[0] = json.dumps(record)
    target.write_bytes(gzip.compress(("\n".join(rows) + "\n").encode()))
    with pytest.raises(ValueError, match="digest mismatch"):
        compare_sample(copied)


# --- derived breakout and reclaim ---------------------------------------------


BREAKOUT_HIGHS = (100, 101, 102, 130, 103, 104, 200, 105, 106, 107, 108, 250, 260)
BREAKOUT_LOWS = (90, 89, 88, 87, 86, 85, 84, 83, 82, 81, 80, 79, 78)
BREAKOUT_CLOSES = (95, 95, 95, 95, 95, 95, 95, 95, 95, 95, 95, 210, 220)

RECLAIM_LOWS = (90, 91, 92, 70, 93, 94, 50, 95, 96, 97, 98, 45, 99)
RECLAIM_HIGHS = tuple(200 + index for index in range(13))
RECLAIM_CLOSES = (150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150)


def test_a_breakout_from_a_non_comparable_swing_is_not_a_disagreement() -> None:
    complete = weekly_series(
        "alpha",
        highs=BREAKOUT_HIGHS,
        lows=BREAKOUT_LOWS,
        closes=BREAKOUT_CLOSES,
    )
    gapped = weekly_series(
        "beta",
        highs=BREAKOUT_HIGHS,
        lows=BREAKOUT_LOWS,
        closes=BREAKOUT_CLOSES,
        omit=(6,),
    )
    comparison = compare(complete, gapped)
    swing = event_for(comparison, SWING_HIGH_FAMILY, 3)
    assert swing.comparability == NOT_COMPARABLE_AVAILABILITY_GAP
    derived = event_for(comparison, BREAKOUT_FAMILY, 3)
    assert derived.comparability == NOT_COMPARABLE_SOURCE_LEVEL
    assert derived.outcome == NOT_COMPARABLE
    assert derived.reason_codes == (SOURCE_LEVEL_NOT_COMPARABLE,)


def test_a_reclaim_from_a_non_comparable_swing_is_not_a_disagreement() -> None:
    complete = weekly_series(
        "alpha",
        highs=RECLAIM_HIGHS,
        lows=RECLAIM_LOWS,
        closes=RECLAIM_CLOSES,
    )
    gapped = weekly_series(
        "beta",
        highs=RECLAIM_HIGHS,
        lows=RECLAIM_LOWS,
        closes=RECLAIM_CLOSES,
        omit=(6,),
    )
    comparison = compare(complete, gapped)
    swing = event_for(comparison, SWING_LOW_FAMILY, 3)
    assert swing.comparability == NOT_COMPARABLE_AVAILABILITY_GAP
    derived = event_for(comparison, RECLAIM_FAMILY, 3)
    assert derived.comparability == NOT_COMPARABLE_SOURCE_LEVEL
    assert derived.reason_codes == (SOURCE_LEVEL_NOT_COMPARABLE,)


def test_a_derived_candidate_requires_the_whole_confirmation_calendar() -> None:
    """Any week between the level and the confirmation could have confirmed it."""

    complete = weekly_series(
        "alpha",
        highs=BREAKOUT_HIGHS,
        lows=BREAKOUT_LOWS,
        closes=BREAKOUT_CLOSES,
    )
    gapped = weekly_series(
        "beta",
        highs=BREAKOUT_HIGHS,
        lows=BREAKOUT_LOWS,
        closes=BREAKOUT_CLOSES,
        omit=(10,),
    )
    comparison = compare(complete, gapped)
    swing = event_for(comparison, SWING_HIGH_FAMILY, 6)
    assert swing.comparability == COMPARABLE
    assert swing.outcome == STRUCTURAL_AGREEMENT

    derived = event_for(comparison, BREAKOUT_FAMILY, 6)
    assert derived.required_sessions[0] == ORIGIN + 7 * WEEK
    assert derived.required_sessions[-1] == ORIGIN + 11 * WEEK
    assert derived.comparability == NOT_COMPARABLE_AVAILABILITY_GAP
    assert derived.availability_gap_side == "beta"
    assert derived.missing_required_sessions["beta"] == (ORIGIN + 10 * WEEK,)


# --- metrics and denominators -------------------------------------------------


def test_every_rate_names_its_denominator() -> None:
    comparison = compare(weekly_series("alpha"), weekly_series("beta", omit=(8,)))
    metrics = comparison.as_record()["metrics"]
    revised = metrics["combined_swing"]["exact_timestamp_swing_disagreement_rate"]
    assert revised["denominator_semantics"] == COMPARABLE_EVENT_DENOMINATOR
    assert set(revised) == {"numerator", "denominator", "denominator_semantics", "rate"}
    for family in (SWING_HIGH_FAMILY, SWING_LOW_FAMILY, BREAKOUT_FAMILY, RECLAIM_FAMILY):
        counts = metrics[family]
        assert (
            counts["comparable_candidate_count"]
            + counts["not_comparable_candidate_count"]
            == counts["candidate_session_count"]
        )
        assert (
            counts["comparable_event_count"] + counts["not_comparable_event_count"]
            == counts["raw_detected_event_count"]
        )


def test_an_empty_denominator_is_reported_as_undefined_not_as_zero() -> None:
    comparison = compare(weekly_series("alpha", omit=(6,)), weekly_series("beta", omit=(6,)))
    metrics = comparison.as_record()["metrics"]
    revised = metrics["combined_swing"]["exact_timestamp_swing_disagreement_rate"]
    assert revised["denominator"] == 0
    assert revised["rate"] is None


def test_rates_do_not_depend_on_the_callers_decimal_context() -> None:
    left = weekly_series("alpha")
    right = weekly_series("beta", omit=(8,))
    with decimal.localcontext() as context:
        context.prec = 4
        narrow = compare(left, right).as_record()["metrics"]
    with decimal.localcontext() as context:
        context.prec = 60
        wide = compare(left, right).as_record()["metrics"]
    assert narrow == wide


# --- the collected samples ----------------------------------------------------


@pytest.fixture(scope="module")
def report() -> dict:
    return build_comparison_report(REPOSITORY_ROOT)


def test_the_v1_comparison_still_reproduces_the_frozen_btc019_counts(report: dict) -> None:
    """Both comparison versions coexist; the old one is not re-run under new rules."""

    reproduction = report["legacy_reproduction"]
    assert reproduction["legacy_comparison_contract_version"] == (
        LEGACY_COMPARISON_CONTRACT_VERSION
    )
    assert reproduction["frozen_v1_difference_counts_by_family"] == {
        "swing_high": 4,
        "swing_low": 7,
        "breakout": 4,
        "reclaim": 9,
    }
    assert reproduction["frozen_v1_counts_reproduce"] is True
    assert reproduction["all_samples_reproduce"] is True
    assert report["totals"]["legacy_difference_count"] == 40


def test_both_already_inspected_samples_are_re_measured(report: dict) -> None:
    assert tuple(report["samples"]) == tuple(INSPECTED_SAMPLE_DIRS)
    for sample in report["samples"].values():
        assert len(sample["comparisons"]) == 3
        assert {provider["provider"] for provider in sample["dataset"]["providers"]} == {
            "bitstamp",
            "coinbase",
            "bitfinex",
        }
        for provider in sample["dataset"]["providers"]:
            assert len(provider["raw_artifact_sha256"]) == 64


def test_the_sealed_sample_is_neither_collected_nor_opened(report: dict) -> None:
    assert report["sealed_sample_opened"] is False
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


def test_availability_gaps_never_survive_as_structural_disagreements(report: dict) -> None:
    for sample in report["samples"].values():
        for comparison in sample["comparisons"]:
            for event in comparison["reported_events"]:
                if event["availability_gap_side"] is not None:
                    assert event["outcome"] == NOT_COMPARABLE
                if event["outcome"] == STRUCTURAL_DISAGREEMENT:
                    assert event["comparability"] == COMPARABLE
                    assert all(
                        not sessions
                        for sessions in event["non_present_required_sessions"].values()
                    )


def test_the_two_swing_lows_on_weeks_bitfinex_never_had_stop_being_disagreements(
    report: dict,
) -> None:
    """`2023-03-06` and `2024-04-29` are the exact weeks Bitfinex omits."""

    sample = report["samples"][INSPECTED_SAMPLE_DIRS[0]]
    bitfinex = next(item for item in sample["series"] if item["series_id"] == "bitfinex")
    omitted = set(bitfinex["absent_sessions"])
    assert omitted == {
        "2023-03-06T00:00:00+00:00",
        "2024-04-29T00:00:00+00:00",
    }
    reconciled = {
        (item["legacy_comparison"], item["event_family"], item["candidate_session"]): item
        for item in sample["legacy_reconciliation"]["differences"]
    }
    for session in sorted(omitted):
        item = reconciled[("bitstamp_vs_bitfinex", SWING_LOW_FAMILY, session)]
        assert item["outcome"] == NOT_COMPARABLE
        assert item["availability_gap_side"] == "bitfinex"


def test_the_2023_02_13_swing_and_its_breakout_stop_being_disagreements(
    report: dict,
) -> None:
    """The "Bitstamp alone created one swing and its breakout" clause."""

    sample = report["samples"][INSPECTED_SAMPLE_DIRS[0]]
    reconciled = [
        item
        for item in sample["legacy_reconciliation"]["differences"]
        if item["candidate_session"] == "2023-02-13T00:00:00+00:00"
    ]
    assert reconciled
    assert all(item["outcome"] == NOT_COMPARABLE for item in reconciled)
    breakout = next(
        item for item in reconciled if item["event_family"] == BREAKOUT_FAMILY
    )
    assert breakout["confirmation_timestamp"] == "2023-03-13T00:00:00+00:00"
    assert breakout["reason_codes"] == [SOURCE_LEVEL_NOT_COMPARABLE]


def test_the_btc019b_adjacent_week_pairs_stop_being_disagreements(report: dict) -> None:
    """BTC-019B's four exact-timestamp disagreements, under the new contract."""

    probe = report["btc019b_known_case_probe"]
    assert probe["frozen_exact_timestamp_disagreement_count"] == 4
    assert probe["composite_omitted_weekly_sessions"] == [
        "2020-03-09T00:00:00+00:00",
        "2021-04-12T00:00:00+00:00",
    ]
    sessions = {item["event_timestamp"] for item in probe["records"]}
    assert sessions == {
        "2020-03-09T00:00:00+00:00",
        "2020-03-16T00:00:00+00:00",
        "2021-04-05T00:00:00+00:00",
        "2021-04-12T00:00:00+00:00",
    }
    assert probe["not_comparable_count"] == 4
    assert probe["remaining_disagreement_count"] == 0
    for record in probe["records"]:
        assert record["composite_omitted_sessions_in_window"]


def test_some_prior_differences_survive_as_genuine_disagreements(report: dict) -> None:
    """The contract is a filter, not an eraser."""

    totals = report["totals"]
    assert totals["legacy_difference_count"] == (
        totals["legacy_difference_now_not_comparable_count"]
        + totals["legacy_difference_still_disagreement_count"]
        + totals["legacy_difference_now_agreement_count"]
    )
    assert totals["legacy_difference_still_disagreement_count"] > 0
    assert totals["legacy_difference_now_not_comparable_count"] > 0


def test_provider_order_does_not_decide_the_persisted_pair_identity(report: dict) -> None:
    for sample in report["samples"].values():
        identifiers = [comparison["comparison_id"] for comparison in sample["comparisons"]]
        assert identifiers == sorted(identifiers)
        for comparison in sample["comparisons"]:
            assert comparison["series_ids"] == sorted(comparison["series_ids"])


# --- frozen protocol preservation ---------------------------------------------


def test_the_frozen_v2_gates_and_thresholds_are_read_and_never_written(
    report: dict,
) -> None:
    frozen = json.loads(
        (
            REPOSITORY_ROOT
            / "research_artifacts/btc_reference_composite/BTC_REFERENCE_COMPOSITE_V2"
            / "protocol_definition.json"
        ).read_text()
    )
    declared = {gate["metric"]: gate for gate in frozen["approval_gates"]}
    for gate in report["frozen_v2_gate_measurability"]["gates"]:
        assert gate["threshold"] == declared[gate["metric"]]["threshold"]
        assert gate["hard"] == declared[gate["metric"]]["hard"]
        assert gate["direction"] == declared[gate["metric"]]["direction"]
        assert gate["threshold_changed"] is False
    assert frozen["status"] == "FROZEN_RESEARCH_PROTOCOL"
    assert frozen["governance"]["production_canonical_reference"] == "UNRESOLVED"
    assert [item["metric"] for item in frozen_affected_v2_gates(REPOSITORY_ROOT)] == [
        gate["metric"] for gate in report["frozen_v2_gate_measurability"]["gates"]
    ]


def test_the_report_promotes_nothing(report: dict) -> None:
    assert report["research_only"] is True
    assert report["production_canonical_reference"] == "UNRESOLVED"
    assert report["btc019_status"] == "IN PROGRESS"
    assert report["production_swing_semantics_changed"] is False
    assert report["comparison_contract_version"] == COMPARISON_CONTRACT_VERSION
    assert report["source_detector_version"] == WEEKLY_STRUCTURE_DETECTOR_VERSION


# --- persistence --------------------------------------------------------------


def test_the_persisted_report_recomputes_from_the_immutable_histories(
    report: dict,
) -> None:
    assert restore_comparison_report(REPORT_PATH) == report
    assert verify_comparison_report(REPOSITORY_ROOT, REPORT_PATH) == report


def test_a_persisted_report_from_another_contract_is_refused(tmp_path: Path) -> None:
    persisted = json.loads(REPORT_PATH.read_text())
    persisted["comparison_contract_version"] = "CROSS_PROVIDER_STRUCTURE_COMPARISON_V3"
    path = tmp_path / "comparison_report.json"
    path.write_text(json.dumps(persisted))
    with pytest.raises(CrossProviderComparisonError, match="different comparison contract"):
        restore_comparison_report(path)


def test_a_persisted_report_missing_provenance_is_refused(tmp_path: Path) -> None:
    persisted = json.loads(REPORT_PATH.read_text())
    del persisted["legacy_reproduction"]
    path = tmp_path / "comparison_report.json"
    path.write_text(json.dumps(persisted))
    with pytest.raises(CrossProviderComparisonError, match="missing required provenance"):
        restore_comparison_report(path)


def test_a_persisted_report_that_no_longer_recomputes_is_refused(tmp_path: Path) -> None:
    persisted = json.loads(REPORT_PATH.read_text())
    persisted["totals"]["legacy_difference_count"] = 0
    path = tmp_path / "comparison_report.json"
    path.write_text(json.dumps(persisted))
    with pytest.raises(CrossProviderComparisonError, match="does not recompute"):
        verify_comparison_report(REPOSITORY_ROOT, path)


def test_the_classification_is_read_off_the_predeclared_rule(report: dict) -> None:
    classification = report["classification"]
    assert classification["outcome"] in {
        "READY_TO_BUILD_SEALED_VALIDATOR",
        "NOT_READY_STRUCTURAL_GATES_STILL_INVALID",
        "RESEARCH_INCONCLUSIVE",
        "BLOCKED_BY_NEW_CORRECTNESS_DEFECT",
    }
    assert classification["reason_codes"]
    assert "READY_TO_BUILD_SEALED_VALIDATOR" in report["classification_rule"]


def test_the_evaluation_time_is_the_samples_own_latest_ingestion(report: dict) -> None:
    """No wall clock enters the record."""

    for relative, sample in report["samples"].items():
        histories = load_inspected_sample(REPOSITORY_ROOT / relative)
        assert sample["evaluation_time"] == sample_evaluation_time(histories).isoformat()
