"""BTC_REFERENCE_COMPOSITE_V3 structural threshold calibration regressions.

Two things must be impossible here. The first is a threshold chosen because it
made an already-seen result come out well: the objective, the grid, the pair
universes and the sufficiency policy are all fixed and hashed before a single
rate is computed, and the series the thresholds are calibrated on are disjoint
from the series they will be applied to. The second is evidence that isn't
there being read as agreement: an undefined pair, a zero comparable
denominator and an insufficient comparability rate all have to travel as
undefined and fail closed.

These tests also pin the matching rule the formal review left open, including
its adversarial two-week case, and prove the whole record rebuilds from the
already-inspected samples with no path to the sealed 2015-2019 history.
"""

import decimal
import json
import re
import shutil
from datetime import UTC, datetime, timedelta
from decimal import Context, Decimal
from fractions import Fraction
from pathlib import Path

import pytest

from btc_predictor.levels import WEEKLY_SWING_HIGH, WEEKLY_SWING_LOW
from btc_predictor.research.cross_provider_structure_comparison import (
    AFFECTED_V2_GATE_METRICS,
    COMPARISON_CONTRACT_VERSION,
)
from btc_predictor.research.reference_composite_v2 import (
    FROZEN_V2_DEFINITION_SHA256,
    UntouchedValidationSampleGuardError,
)
from btc_predictor.research.structural_gate_denominator_resolution import (
    frozen_structural_gates,
)
from btc_predictor.research.structural_threshold_calibration import (
    AGGREGATION_ID,
    CALIBRATION_INSUFFICIENT,
    CALIBRATION_OBJECTIVE_ID,
    CALIBRATION_OUTPUT_NAMESPACE,
    CALIBRATION_RECORD_FILENAME,
    CALIBRATION_REPORT_FILENAME,
    CALIBRATION_SCHEMA_VERSION,
    CANDIDATE_SERIES_ID,
    DEGENERATE_ALTERNATIVE_HYPOTHESIS,
    FALSE_REJECTION_TOLERANCE,
    GATE_VERDICT_FAIL,
    GATE_VERDICT_PASS,
    GATE_VERDICT_UNDEFINED,
    GOVERNANCE_FILENAME,
    GOVERNANCE_VERSION,
    MATCHING_ALGORITHM_ID,
    MECHANISM_NOT_EXERCISED,
    METRIC_CALIBRATED,
    METRIC_INSUFFICIENT,
    METRIC_UNSTABLE,
    MINIMUM_DISCRIMINATION_POWER,
    MINIMUM_STRUCTURAL_COMPARABILITY_RATE,
    NO_ADMISSIBLE_THRESHOLD,
    PAIR_ADMISSIBLE,
    PAIR_BELOW_COMPARABILITY_FLOOR,
    PAIR_INADMISSIBLE,
    PAIR_NO_CANDIDATE_EVENTS,
    PAIR_NO_COMPARABLE_EVENTS,
    PAIR_NOT_IN_UNIVERSE,
    PAIR_PURPOSE_CALIBRATION,
    PAIR_PURPOSE_EXCLUDED,
    PAIR_PURPOSE_GATE,
    PAIR_ROLE_MISMATCH,
    PAIR_UNDEFINED_INSUFFICIENT_EVIDENCE,
    PAIR_WRONG_COMPARISON_CONTRACT,
    PERMITTED_CALIBRATION_SAMPLE_DIRS,
    REQUIRED_ADMISSIBLE_GATE_PAIR_COUNT,
    THRESHOLD_GRID,
    UNDEFINED_NO_CANDIDATE_EVENTS,
    UNDEFINED_NO_COMPARABLE_EVENTS,
    ThresholdCalibrationError,
    _rendered,
    aggregate_worst_pair,
    binomial_tail_at_least,
    build_calibration_record,
    calibration_governance_definition,
    calibration_markdown,
    calibration_governance_sha256,
    calibration_pair_universe,
    classify_calibration_pair,
    exact_rate,
    family_failure_probability,
    gate_pair_universe,
    match_within_weeks,
    matched_pair_count,
    measurement_state,
    pair_purpose,
    require_frozen_governance,
    restore_calibration_record,
    restore_governance_definition,
    series_role,
    smallest_failing_count,
    threshold_verdict,
    verify_calibration_artifacts,
    wilson_interval,
    write_calibration_artifacts,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CALIBRATION_DIR = REPOSITORY_ROOT / CALIBRATION_OUTPUT_NAMESPACE

W0 = datetime(2024, 1, 1, tzinfo=UTC)


def week(offset: int) -> datetime:
    return W0 + timedelta(weeks=offset)


# The gate universe, retyped rather than read from the module it guards.
EXPECTED_GATE_PAIRS = (
    ("MEDIAN_OHLC_V2", "bitfinex"),
    ("MEDIAN_OHLC_V2", "bitstamp"),
    ("MEDIAN_OHLC_V2", "coinbase"),
)
EXPECTED_CALIBRATION_PAIRS = (
    ("bitfinex", "bitstamp"),
    ("bitfinex", "coinbase"),
    ("bitstamp", "coinbase"),
)

# The outcome this task reached, retyped so a silent change in the module has
# to break a test rather than quietly move a governance conclusion.
EXPECTED_METRIC_OUTCOMES = {
    "exact_timestamp_swing_disagreement_rate": (METRIC_CALIBRATED, "0.25"),
    "within_1_week_swing_disagreement_rate": (METRIC_INSUFFICIENT, "0.25"),
    "within_2_week_swing_disagreement_rate": (METRIC_INSUFFICIENT, "0.25"),
    "structural_state_disagreement_rate": (METRIC_CALIBRATED, "0.20"),
    "breakout_disagreement_rate": (METRIC_INSUFFICIENT, None),
    "reclaim_disagreement_rate": (METRIC_INSUFFICIENT, None),
}

# Everything Phase A reads. No collected history appears, so the governance
# definition cannot depend on a sample.
_GOVERNANCE_INPUTS = (
    "research_artifacts",
    "btc_predictor/research/reference_composite_empirical.py",
    "btc_predictor/research/btc019b_diagnostics.py",
)


def _isolated_root(destination: Path) -> Path:
    for relative in _GOVERNANCE_INPUTS:
        source = REPOSITORY_ROOT / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    return destination


@pytest.fixture(scope="module")
def record() -> dict:
    return build_calibration_record(REPOSITORY_ROOT)


@pytest.fixture(scope="module")
def governance() -> dict:
    return calibration_governance_definition(REPOSITORY_ROOT)


# =============================================================================
# Phase A -- governance
# =============================================================================


def test_the_gate_pair_universe_is_exactly_the_candidate_versus_provider_pairs() -> None:
    assert gate_pair_universe() == EXPECTED_GATE_PAIRS
    assert len(gate_pair_universe()) == REQUIRED_ADMISSIBLE_GATE_PAIR_COUNT
    for pair in gate_pair_universe():
        assert CANDIDATE_SERIES_ID in pair


def test_the_calibration_universe_never_contains_the_candidate() -> None:
    assert calibration_pair_universe() == EXPECTED_CALIBRATION_PAIRS
    for pair in calibration_pair_universe():
        assert CANDIDATE_SERIES_ID not in pair


def test_the_two_universes_are_disjoint_so_calibration_stays_candidate_blind() -> None:
    assert not set(gate_pair_universe()) & set(calibration_pair_universe())


def test_pair_identity_does_not_depend_on_the_order_it_is_written_in() -> None:
    assert gate_pair_universe(provider_ids=("coinbase", "bitfinex", "bitstamp")) == (
        gate_pair_universe(provider_ids=("bitstamp", "coinbase", "bitfinex"))
    )
    assert calibration_pair_universe(("coinbase", "bitstamp", "bitfinex")) == (
        EXPECTED_CALIBRATION_PAIRS
    )


def test_series_roles_are_explicit_and_a_research_composite_is_neither() -> None:
    assert series_role(CANDIDATE_SERIES_ID) == "CANDIDATE_REFERENCE_UNDER_EVALUATION"
    assert series_role("bitstamp") == "INDEPENDENT_RAW_VALIDATION_PROVIDER"
    assert series_role("MEDIAN_OHLC_V1") == "RESEARCH_ONLY_HISTORICAL_COMPOSITE"
    with pytest.raises(ThresholdCalibrationError, match="undeclared comparison series"):
        series_role("kraken")


def test_pair_purposes_separate_gates_from_dispersion_diagnostics() -> None:
    assert pair_purpose(("bitstamp", CANDIDATE_SERIES_ID)) == PAIR_PURPOSE_GATE
    assert pair_purpose((CANDIDATE_SERIES_ID, "bitstamp")) == PAIR_PURPOSE_GATE
    assert pair_purpose(("bitstamp", "coinbase")) == PAIR_PURPOSE_CALIBRATION
    assert pair_purpose(("MEDIAN_OHLC_V1", "bitstamp")) == PAIR_PURPOSE_EXCLUDED
    assert (
        pair_purpose(("MEDIAN_OHLC_V1", CANDIDATE_SERIES_ID)) == PAIR_PURPOSE_EXCLUDED
    )


def test_the_candidate_cannot_also_be_a_validation_provider() -> None:
    with pytest.raises(ThresholdCalibrationError, match="cannot also be"):
        gate_pair_universe(candidate_series_id="bitstamp")


def _measurement(
    comparison_id: str,
    series_pair: tuple[str, str],
    rate: str | None,
    state: str = PAIR_ADMISSIBLE,
) -> dict:
    return {
        "comparison_id": comparison_id,
        "series_pair": list(series_pair),
        "rate": rate,
        "state": state,
    }


def _gate_measurements(rates: tuple[str | None, ...], state: str = PAIR_ADMISSIBLE):
    return [
        _measurement("_vs_".join(pair), pair, rate, state)
        for pair, rate in zip(gate_pair_universe(), rates, strict=True)
    ]


def test_worst_pair_on_a_maximum_gate_is_the_highest_defined_rate() -> None:
    result = aggregate_worst_pair(
        _gate_measurements(("0.01", "0.30", "0.10")),
        threshold=Decimal("0.20"),
        direction="maximum",
        required_pairs=gate_pair_universe(),
    )
    assert result["aggregation"] == AGGREGATION_ID
    assert result["verdict"] == GATE_VERDICT_FAIL
    assert result["worst_pair_rate"] == "0.30"


def test_worst_pair_on_a_minimum_gate_is_the_lowest_defined_rate() -> None:
    result = aggregate_worst_pair(
        _gate_measurements(("0.99", "0.40", "0.80")),
        threshold=Decimal("0.50"),
        direction="minimum",
        required_pairs=gate_pair_universe(),
    )
    assert result["verdict"] == GATE_VERDICT_FAIL
    assert result["worst_pair_rate"] == "0.40"


def test_a_tie_resolves_to_the_lexicographically_smallest_comparison_id() -> None:
    result = aggregate_worst_pair(
        _gate_measurements(("0.30", "0.30", "0.30")),
        threshold=Decimal("0.20"),
        direction="maximum",
        required_pairs=gate_pair_universe(),
    )
    assert result["worst_pair_comparison_id"] == "MEDIAN_OHLC_V2_vs_bitfinex"
    reversed_order = list(reversed(_gate_measurements(("0.30", "0.30", "0.30"))))
    assert (
        aggregate_worst_pair(
            reversed_order,
            threshold=Decimal("0.20"),
            direction="maximum",
            required_pairs=gate_pair_universe(),
        )
        == result
    )


def test_an_unexpected_pair_is_refused_rather_than_aggregated() -> None:
    measurements = _gate_measurements(("0.01", "0.01", "0.01"))
    measurements.append(_measurement("bitstamp_vs_coinbase", ("bitstamp", "coinbase"), "0.9"))
    with pytest.raises(ThresholdCalibrationError, match="outside the declared gate pair"):
        aggregate_worst_pair(
            measurements,
            threshold=Decimal("0.20"),
            direction="maximum",
            required_pairs=gate_pair_universe(),
        )


def test_a_missing_required_pair_makes_the_gate_undefined_not_smaller() -> None:
    result = aggregate_worst_pair(
        _gate_measurements(("0.01", "0.01", "0.01"))[:2],
        threshold=Decimal("0.20"),
        direction="maximum",
        required_pairs=gate_pair_universe(),
    )
    assert result["verdict"] == GATE_VERDICT_UNDEFINED
    assert result["missing_pairs"] == ["MEDIAN_OHLC_V2_vs_coinbase"]


def test_one_undefined_pair_blocks_the_whole_gate() -> None:
    result = aggregate_worst_pair(
        _gate_measurements(("0.01", None, "0.01")),
        threshold=Decimal("0.20"),
        direction="maximum",
        required_pairs=gate_pair_universe(),
    )
    assert result["verdict"] == GATE_VERDICT_UNDEFINED
    assert result["worst_pair_rate"] is None
    assert result["undefined_or_inadmissible_pairs"] == ["MEDIAN_OHLC_V2_vs_bitstamp"]


def test_every_pair_undefined_is_still_undefined_and_never_a_pass() -> None:
    result = aggregate_worst_pair(
        _gate_measurements((None, None, None)),
        threshold=Decimal("0.20"),
        direction="maximum",
        required_pairs=gate_pair_universe(),
    )
    assert result["verdict"] == GATE_VERDICT_UNDEFINED
    assert result["verdict"] != GATE_VERDICT_PASS


def test_an_inadmissible_pair_cannot_be_read_as_a_passing_measurement() -> None:
    result = aggregate_worst_pair(
        _gate_measurements(("0.00", "0.00", "0.00"), state=PAIR_INADMISSIBLE),
        threshold=Decimal("0.20"),
        direction="maximum",
        required_pairs=gate_pair_universe(),
    )
    assert result["verdict"] == GATE_VERDICT_UNDEFINED


def test_an_undefined_rate_is_never_coerced_to_zero() -> None:
    assert exact_rate(0, 0) is None
    assert threshold_verdict(None, threshold=Decimal("0.05"), direction="maximum") == (
        GATE_VERDICT_UNDEFINED
    )


@pytest.mark.parametrize(
    ("rate", "expected"),
    (
        ("0.0499999999", GATE_VERDICT_PASS),
        ("0.05", GATE_VERDICT_PASS),
        ("0.0500000001", GATE_VERDICT_FAIL),
    ),
)
def test_the_maximum_gate_boundary_is_explicit_at_below_at_and_above(
    rate: str, expected: str
) -> None:
    assert (
        threshold_verdict(Decimal(rate), threshold=Decimal("0.05"), direction="maximum")
        == expected
    )


@pytest.mark.parametrize(
    ("rate", "expected"),
    (
        ("0.9949999999", GATE_VERDICT_FAIL),
        ("0.995", GATE_VERDICT_PASS),
        ("0.9950000001", GATE_VERDICT_PASS),
    ),
)
def test_the_minimum_gate_boundary_is_explicit_at_below_at_and_above(
    rate: str, expected: str
) -> None:
    assert (
        threshold_verdict(Decimal(rate), threshold=Decimal("0.995"), direction="minimum")
        == expected
    )


def test_zero_candidate_and_zero_comparable_events_are_different_undefined_states() -> None:
    assert measurement_state(candidate_event_count=0, denominator=0) == (
        UNDEFINED_NO_CANDIDATE_EVENTS
    )
    assert measurement_state(candidate_event_count=7, denominator=0) == (
        UNDEFINED_NO_COMPARABLE_EVENTS
    )
    assert measurement_state(candidate_event_count=7, denominator=3) == "DEFINED"


def test_a_comparable_denominator_cannot_exceed_an_empty_candidate_universe() -> None:
    with pytest.raises(ThresholdCalibrationError, match="cannot exceed"):
        measurement_state(candidate_event_count=0, denominator=1)


# --- within-N-week matching ---------------------------------------------------


def test_within_one_week_matches_the_same_session_exactly() -> None:
    assert match_within_weeks([week(0)], [week(0)], weeks=1) == ((week(0), week(0)),)


def test_within_one_week_matches_a_one_week_shift() -> None:
    assert match_within_weeks([week(0)], [week(1)], weeks=1) == ((week(0), week(1)),)


def test_within_one_week_does_not_reach_two_weeks() -> None:
    assert match_within_weeks([week(0)], [week(2)], weeks=1) == ()


def test_the_adversarial_two_week_case_is_matched_at_maximum_cardinality() -> None:
    # left {W0, W4} against right {W2, W6} under a two-week tolerance. The
    # tolerance graph is W0-W2, W4-W2 and W4-W6. Taking W4-W2 first -- which
    # "nearest admissible pair first" permits, every edge having distance two
    # -- strands W0 and W6 and yields one matched pair. The maximum is two,
    # asserted here independently of the implementation.
    matched = match_within_weeks([week(0), week(4)], [week(2), week(6)], weeks=2)
    assert len(matched) == 2
    assert matched == ((week(0), week(2)), (week(4), week(6)))


def test_the_adversarial_case_moves_a_hard_gate_denominator() -> None:
    # The within-N denominator merges each matched pair, so a sub-maximal
    # matching publishes both a larger numerator and a larger denominator.
    numerator, denominator = 4, 26
    maximal = len(match_within_weeks([week(0), week(4)], [week(2), week(6)], weeks=2))
    assert (numerator - 2 * maximal, denominator - maximal) == (0, 24)
    assert (numerator - 2 * 1, denominator - 1) == (2, 25)


def test_an_equidistant_choice_is_broken_lexicographically() -> None:
    matched = match_within_weeks([week(2)], [week(0), week(4)], weeks=2)
    assert matched == ((week(2), week(0)),)


def test_crossing_choices_take_the_maximum_cardinality_not_the_greedy_one() -> None:
    matched = match_within_weeks([week(0), week(2)], [week(1), week(3)], weeks=2)
    assert len(matched) == 2
    assert matched == ((week(0), week(1)), (week(2), week(3)))


def test_among_maximum_matchings_total_calendar_distance_is_minimised() -> None:
    # Both {W0-W1, W2-W2} and {W0-W2, W2-W1} match two pairs; the first costs
    # one week and the second three.
    matched = match_within_weeks([week(0), week(2)], [week(1), week(2)], weeks=2)
    assert matched == ((week(0), week(1)), (week(2), week(2)))


def test_matching_does_not_depend_on_input_order() -> None:
    forward = match_within_weeks([week(0), week(4)], [week(2), week(6)], weeks=2)
    reverse = match_within_weeks([week(4), week(0)], [week(6), week(2)], weeks=2)
    assert forward == reverse


def test_matching_is_symmetric_when_the_two_sides_are_exchanged() -> None:
    left = match_within_weeks([week(0), week(4)], [week(2), week(6)], weeks=2)
    right = match_within_weeks([week(2), week(6)], [week(0), week(4)], weeks=2)
    assert len(left) == len(right) == 2


def test_a_repeated_session_on_one_side_is_refused() -> None:
    with pytest.raises(ThresholdCalibrationError, match="one session twice"):
        match_within_weeks([week(0), week(0)], [week(0)], weeks=1)


def test_an_off_cadence_session_is_refused() -> None:
    with pytest.raises(ThresholdCalibrationError, match="whole weekly sessions"):
        match_within_weeks([week(0)], [week(0) + timedelta(days=3)], weeks=1)


def test_an_oversized_matching_input_is_refused_rather_than_enumerated() -> None:
    left = [week(index * 4) for index in range(30)]
    with pytest.raises(ThresholdCalibrationError, match="declared bound"):
        match_within_weeks(left, [week(0)], weeks=2)


def test_swing_highs_and_swing_lows_are_never_matched_across_families() -> None:
    disagreements = {
        "bitstamp": {WEEKLY_SWING_HIGH: [week(0)]},
        "coinbase": {WEEKLY_SWING_LOW: [week(1)]},
    }
    assert matched_pair_count(disagreements, weeks=2) == 0
    same_family = {
        "bitstamp": {WEEKLY_SWING_HIGH: [week(0)]},
        "coinbase": {WEEKLY_SWING_HIGH: [week(1)]},
    }
    assert matched_pair_count(same_family, weeks=2) == 1


def test_matching_refuses_a_derived_family() -> None:
    with pytest.raises(ThresholdCalibrationError, match="only merges swing families"):
        matched_pair_count(
            {"bitstamp": {"breakout": [week(0)]}, "coinbase": {"breakout": [week(0)]}},
            weeks=1,
        )


def test_matching_requires_exactly_two_series() -> None:
    with pytest.raises(ThresholdCalibrationError, match="exactly two series"):
        matched_pair_count({"bitstamp": {WEEKLY_SWING_HIGH: [week(0)]}}, weeks=1)


# --- comparability sufficiency -------------------------------------------------


def _calibration_measurement(
    *,
    candidate: int,
    comparable: int,
    not_comparable: int,
    numerator: int = 0,
) -> dict:
    detected = comparable + not_comparable
    rate = exact_rate(numerator, comparable)
    comparability = None if detected == 0 else exact_rate(comparable, detected)
    return {
        "comparison_id": "bitstamp_vs_coinbase",
        "series_pair": ["bitstamp", "coinbase"],
        "measurement_state": measurement_state(
            candidate_event_count=candidate, denominator=comparable
        ),
        "numerator": numerator,
        "denominator": comparable,
        "rate": None if rate is None else str(rate),
        "candidate_event_count": candidate,
        "all_detected_event_count": detected,
        "comparable_event_count": comparable,
        "not_comparable_event_count": not_comparable,
        "structural_comparability_rate": (
            None if comparability is None else str(comparability)
        ),
    }


_SOUND_COMPARISON = {
    "comparison_contract_version": COMPARISON_CONTRACT_VERSION,
    "source_detector_version": "BTC_PREDICTOR_WEEKLY_LEVELS_V1",
}


def _classify(measurement: dict, *, comparison: dict | None = None, policy: str | None = None):
    from btc_predictor.research.price_source_policy import PRICE_SOURCE_POLICY_VERSION

    return classify_calibration_pair(
        measurement,
        comparison=comparison or _SOUND_COMPARISON,
        dataset_policy_version=policy or PRICE_SOURCE_POLICY_VERSION,
    )


def test_a_pair_with_no_candidate_events_is_undefined_not_admissible() -> None:
    verdict = _classify(
        _calibration_measurement(candidate=0, comparable=0, not_comparable=0)
    )
    assert verdict.state == PAIR_UNDEFINED_INSUFFICIENT_EVIDENCE
    assert PAIR_NO_CANDIDATE_EVENTS in verdict.reason_codes


def test_a_pair_where_every_event_is_not_comparable_is_undefined() -> None:
    verdict = _classify(
        _calibration_measurement(candidate=9, comparable=0, not_comparable=9)
    )
    assert verdict.state == PAIR_UNDEFINED_INSUFFICIENT_EVIDENCE
    assert PAIR_NO_COMPARABLE_EVENTS in verdict.reason_codes
    assert verdict.reason_codes  # never silently dropped


@pytest.mark.parametrize(
    ("comparable", "not_comparable", "expected"),
    (
        (4, 6, PAIR_UNDEFINED_INSUFFICIENT_EVIDENCE),  # 0.40, below the floor
        (5, 5, PAIR_ADMISSIBLE),  # exactly 0.50, the boundary passes
        (6, 4, PAIR_ADMISSIBLE),  # 0.60, above the floor
    ),
)
def test_the_comparability_floor_boundary_is_explicit(
    comparable: int, not_comparable: int, expected: str
) -> None:
    verdict = _classify(
        _calibration_measurement(
            candidate=comparable + not_comparable,
            comparable=comparable,
            not_comparable=not_comparable,
            numerator=1,
        )
    )
    assert verdict.state == expected
    if expected != PAIR_ADMISSIBLE:
        assert PAIR_BELOW_COMPARABILITY_FLOOR in verdict.reason_codes


def test_the_comparability_floor_is_a_half_and_is_not_the_disagreement_threshold(
    governance: dict,
) -> None:
    assert MINIMUM_STRUCTURAL_COMPARABILITY_RATE == Decimal("0.50")
    policy = governance["comparability_sufficiency"]
    assert policy["minimum_structural_comparability_rate"] == "0.50"
    assert policy["insufficient_evidence_consequence"] == GATE_VERDICT_UNDEFINED
    assert policy["minimum_comparable_events_per_gate_pair"] == (
        "DERIVED_IN_PHASE_B_PER_METRIC"
    )
    # Coverage and disagreement are separate numbers in separate sections; the
    # objective never reads the comparability floor as a tolerance.
    assert "comparability" not in json.dumps(governance["calibration_objective"])


def test_a_pair_from_another_comparison_contract_is_inadmissible() -> None:
    verdict = _classify(
        _calibration_measurement(candidate=10, comparable=10, not_comparable=0),
        comparison={**_SOUND_COMPARISON, "comparison_contract_version": "V1"},
    )
    assert verdict.state == PAIR_INADMISSIBLE
    assert PAIR_WRONG_COMPARISON_CONTRACT in verdict.reason_codes


def test_a_candidate_bearing_pair_is_inadmissible_as_calibration_evidence() -> None:
    measurement = _calibration_measurement(candidate=10, comparable=10, not_comparable=0)
    measurement["series_pair"] = [CANDIDATE_SERIES_ID, "bitstamp"]
    verdict = _classify(measurement)
    assert verdict.state == PAIR_INADMISSIBLE
    assert PAIR_ROLE_MISMATCH in verdict.reason_codes
    assert PAIR_NOT_IN_UNIVERSE in verdict.reason_codes


def test_an_unknown_series_is_inadmissible_rather_than_a_crash() -> None:
    measurement = _calibration_measurement(candidate=10, comparable=10, not_comparable=0)
    measurement["series_pair"] = ["kraken", "bitstamp"]
    verdict = _classify(measurement)
    assert verdict.state == PAIR_INADMISSIBLE
    assert PAIR_ROLE_MISMATCH in verdict.reason_codes


# --- uncertainty ---------------------------------------------------------------


def test_a_zero_numerator_still_carries_its_denominator_into_the_interval() -> None:
    small = wilson_interval(0, 3)
    large = wilson_interval(0, 300)
    assert small.rate == large.rate == Decimal(0)
    assert small.lower == large.lower == Decimal(0)
    assert small.upper > large.upper
    assert small.upper > Decimal("0.5")
    assert large.upper < Decimal("0.02")


def test_an_interval_needs_a_denominator() -> None:
    with pytest.raises(ThresholdCalibrationError, match="positive denominator"):
        wilson_interval(0, 0)


def test_intervals_do_not_depend_on_the_callers_decimal_context() -> None:
    baseline = wilson_interval(3, 28).as_record()
    with decimal.localcontext(Context(prec=6, rounding=decimal.ROUND_UP)):
        assert wilson_interval(3, 28).as_record() == baseline


# --- exact operating characteristics ------------------------------------------


def test_the_binomial_tail_is_exact_rational_arithmetic() -> None:
    assert binomial_tail_at_least(size=3, count=0, probability=Fraction(1, 2)) == 1
    assert binomial_tail_at_least(size=3, count=4, probability=Fraction(1, 2)) == 0
    assert binomial_tail_at_least(size=2, count=1, probability=Fraction(1, 2)) == (
        Fraction(3, 4)
    )
    assert binomial_tail_at_least(size=2, count=2, probability=Fraction(1, 3)) == (
        Fraction(1, 9)
    )


def test_the_smallest_failing_count_follows_the_maximum_gate_convention() -> None:
    # rate <= threshold passes, so on 20 comparable events a 0.05 gate allows
    # exactly one disagreement and fails on the second.
    assert smallest_failing_count(size=20, threshold=Decimal("0.05")) == 2
    assert smallest_failing_count(size=20, threshold=Decimal("0.00")) == 1
    assert smallest_failing_count(size=5, threshold=Decimal("0.50")) == 3


def test_a_family_of_pairs_fails_more_often_than_one_pair() -> None:
    one = family_failure_probability(
        [25], threshold=Decimal("0.10"), probability=Fraction(1, 20)
    )
    three = family_failure_probability(
        [25, 25, 25], threshold=Decimal("0.10"), probability=Fraction(1, 20)
    )
    assert 0 < one < three < 1


# --- the Phase-A artifact ------------------------------------------------------


def test_the_governance_definition_hashes_every_semantic_it_settles(
    governance: dict,
) -> None:
    assert governance["governance_version"] == GOVERNANCE_VERSION
    assert governance["parent_definition_sha256"] == FROZEN_V2_DEFINITION_SHA256
    for section in (
        "pair_universe",
        "pair_admissibility",
        "pair_aggregation",
        "zero_denominator_semantics",
        "within_week_matching",
        "comparability_sufficiency",
        "uncertainty",
        "calibration_objective",
        "metric_status",
        "sample_governance",
        "prohibited_optimization_criteria",
    ):
        assert governance[section]
    assert governance["within_week_matching"]["algorithm_id"] == MATCHING_ALGORITHM_ID
    assert governance["calibration_objective"]["objective_id"] == CALIBRATION_OBJECTIVE_ID
    assert len(governance["governance_sha256"]) == 64


def test_the_governance_definition_is_deterministic_and_root_independent(
    tmp_path: Path, governance: dict
) -> None:
    assert calibration_governance_definition(REPOSITORY_ROOT) == governance
    isolated = calibration_governance_definition(_isolated_root(tmp_path / "root"))
    assert isolated == governance


def test_the_governance_definition_does_not_depend_on_the_ambient_context(
    governance: dict,
) -> None:
    with decimal.localcontext(Context(prec=5, rounding=decimal.ROUND_UP)):
        assert calibration_governance_definition(REPOSITORY_ROOT) == governance


def test_phase_b_refuses_a_governance_payload_it_did_not_freeze(governance: dict) -> None:
    tampered = dict(governance)
    tampered["governance_sha256"] = "0" * 64
    with pytest.raises(ThresholdCalibrationError, match="does not match"):
        require_frozen_governance(REPOSITORY_ROOT, governance=tampered)


def test_phase_b_refuses_a_governance_payload_edited_under_its_own_hash(
    governance: dict,
) -> None:
    tampered = json.loads(json.dumps(governance))
    tampered["calibration_objective"]["false_rejection_tolerance"] = "1"
    with pytest.raises(ThresholdCalibrationError, match="without changing its hash"):
        require_frozen_governance(REPOSITORY_ROOT, governance=tampered)


def test_the_prohibited_optimization_criteria_are_recorded(governance: dict) -> None:
    prohibited = " ".join(governance["prohibited_optimization_criteria"])
    assert "maximum observed rate" in prohibited
    assert "sealed" in prohibited
    assert "machine-learned" in prohibited


# =============================================================================
# Phase B -- calibration
# =============================================================================


def test_the_record_binds_the_frozen_phase_a_hash(record: dict, governance: dict) -> None:
    assert record["governance_sha256"] == governance["governance_sha256"]
    assert record["governance_sha256"] == calibration_governance_sha256(REPOSITORY_ROOT)
    assert record["phase_a_frozen_before_calibration"] is True


def test_only_the_two_inspected_samples_are_read(record: dict) -> None:
    assert sorted(record["datasets"]) == sorted(PERMITTED_CALIBRATION_SAMPLE_DIRS)
    assert record["sealed_sample_collected"] is False
    assert record["sealed_sample_opened"] is False
    assert record["sealed_sample_used_for_calibration"] is False
    assert record["evidence_labelling"] == "DEVELOPMENT_CALIBRATION_EVIDENCE"
    assert record["evidence_is_not_out_of_sample"] is True


def test_every_dataset_carries_its_verified_artifact_digests(record: dict) -> None:
    for dataset in record["datasets"].values():
        assert dataset["price_source_policy_version"]
        for provider in dataset["providers"]:
            assert len(provider["raw_artifact_sha256"]) == 64


def test_the_candidate_is_never_measured_by_this_task(record: dict) -> None:
    assert record["candidate_measured_in_this_task"] is False
    assert record["candidate_construction_changed"] is False
    for calibration in record["metric_calibrations"]:
        for sample in calibration["samples"].values():
            for row in sample["measurements"]:
                assert CANDIDATE_SERIES_ID not in row["series_pair"]


def test_every_metric_publishes_its_counts_uncertainty_and_comparability(
    record: dict,
) -> None:
    for calibration in record["metric_calibrations"]:
        for sample in calibration["samples"].values():
            for row in sample["measurements"]:
                assert row["comparable_event_count"] + row[
                    "not_comparable_event_count"
                ] == row["all_detected_event_count"]
                assert row["structural_comparability_rate"] is not None
                assert row["not_comparable_reason_counts"] is not None
                if row["denominator"]:
                    assert row["uncertainty"]["denominator"] == row["denominator"]
                    assert row["uncertainty"]["wilson_95_upper"]


def test_the_six_metrics_reach_the_recorded_statuses_and_thresholds(record: dict) -> None:
    calibrations = {item["metric"]: item for item in record["metric_calibrations"]}
    assert set(calibrations) == set(AFFECTED_V2_GATE_METRICS)
    for metric, (status, threshold) in EXPECTED_METRIC_OUTCOMES.items():
        assert calibrations[metric]["status"] == status
        assert calibrations[metric]["selected_threshold"] == threshold


def test_an_insufficient_metric_never_offers_a_usable_threshold(record: dict) -> None:
    for calibration in record["metric_calibrations"]:
        if calibration["status"] != METRIC_CALIBRATED:
            assert calibration["selected_threshold_usable"] is False
            assert calibration["reason_codes"]
        else:
            assert calibration["selected_threshold_usable"] is True
            assert calibration["reason_codes"] == []


def test_the_within_week_metrics_are_insufficient_because_nothing_ever_merged(
    record: dict,
) -> None:
    calibrations = {item["metric"]: item for item in record["metric_calibrations"]}
    for metric in (
        "within_1_week_swing_disagreement_rate",
        "within_2_week_swing_disagreement_rate",
    ):
        calibration = calibrations[metric]
        assert calibration["mechanism_exercised"] is False
        assert MECHANISM_NOT_EXERCISED in calibration["reason_codes"]
        for sample in calibration["samples"].values():
            for row in sample["measurements"]:
                assert row["matched_pair_count"] == 0


def test_breakout_and_reclaim_have_no_achievable_and_discriminating_threshold(
    record: dict,
) -> None:
    calibrations = {item["metric"]: item for item in record["metric_calibrations"]}
    assert NO_ADMISSIBLE_THRESHOLD in calibrations["breakout_disagreement_rate"][
        "reason_codes"
    ]
    reclaim = calibrations["reclaim_disagreement_rate"]
    assert NO_ADMISSIBLE_THRESHOLD in reclaim["reason_codes"]
    assert DEGENERATE_ALTERNATIVE_HYPOTHESIS in reclaim["reason_codes"]
    for calibration in (calibrations["breakout_disagreement_rate"], reclaim):
        assert not any(item["admissible"] for item in calibration["objective_surface"])


def test_a_selected_threshold_is_not_the_maximum_observed_rate_plus_epsilon(
    record: dict,
) -> None:
    for calibration in record["metric_calibrations"]:
        if calibration["status"] != METRIC_CALIBRATED:
            continue
        selected = Decimal(calibration["selected_threshold"])
        observed = [
            Decimal(row["rate"])
            for sample in calibration["samples"].values()
            for row in sample["measurements"]
            if row["state"] == PAIR_ADMISSIBLE and row["rate"] is not None
        ]
        assert selected in THRESHOLD_GRID
        # More than twice the worst observation, because the objective is
        # bounded by the sampling noise of one pair rather than by any rate.
        assert selected > max(observed) * 2


def test_a_selected_threshold_meets_the_predeclared_objective_on_both_samples(
    record: dict,
) -> None:
    for calibration in record["metric_calibrations"]:
        if calibration["status"] != METRIC_CALIBRATED:
            continue
        selected = calibration["selected_threshold"]
        row = next(
            item
            for item in calibration["objective_surface"]
            if item["threshold"] == selected
        )
        assert row["admissible"] is True
        for sample in row["per_sample"]:
            assert Decimal(sample["false_rejection_probability"]) <= Decimal(
                str(FALSE_REJECTION_TOLERANCE.numerator)
            ) / Decimal(str(FALSE_REJECTION_TOLERANCE.denominator))
            assert Decimal(sample["discrimination_power"]) >= Decimal(
                str(MINIMUM_DISCRIMINATION_POWER.numerator)
            ) / Decimal(str(MINIMUM_DISCRIMINATION_POWER.denominator))
        # And no smaller grid value does, so the objective selected the
        # strictest admissible number rather than a comfortable one.
        for item in calibration["objective_surface"]:
            if Decimal(item["threshold"]) < Decimal(selected):
                assert item["admissible"] is False


def test_a_calibrated_threshold_is_not_on_a_knife_edge(record: dict) -> None:
    for calibration in record["metric_calibrations"]:
        if calibration["status"] != METRIC_CALIBRATED:
            continue
        assert calibration["sensitivity"]["neighbours_that_move_historical_verdicts"] == []
        assert len(calibration["sensitivity"]["neighbourhood"]) == 3


def test_every_calibrated_metric_carries_a_derived_minimum_evidence_requirement(
    record: dict,
) -> None:
    for calibration in record["metric_calibrations"]:
        if calibration["status"] != METRIC_CALIBRATED:
            continue
        minimum = calibration["minimum_comparable_events_per_gate_pair"]
        assert isinstance(minimum, int) and minimum > 1
        # The requirement has to be strict enough that one disagreement alone
        # cannot exceed the threshold, or the gate is zero tolerance in
        # disguise.
        assert Decimal(1) / Decimal(minimum) <= Decimal(
            calibration["selected_threshold"]
        )


def test_the_reference_band_is_estimated_without_the_candidate(record: dict) -> None:
    for calibration in record["metric_calibrations"]:
        band = calibration["reference_band"]
        if band is None:
            continue
        assert "candidate" in band["population"]
        assert calibration["calibration_pair_universe"] == [
            "_vs_".join(pair) for pair in calibration_pair_universe()
        ]
        assert calibration["gate_pair_universe"] == [
            "_vs_".join(pair) for pair in gate_pair_universe()
        ]


def test_both_samples_are_reported_separately_before_they_are_pooled(
    record: dict,
) -> None:
    for calibration in record["metric_calibrations"]:
        assert sorted(calibration["samples"]) == sorted(
            PERMITTED_CALIBRATION_SAMPLE_DIRS
        )
        pooled = sum(
            block["sample_denominator"] for block in calibration["samples"].values()
        )
        assert pooled == calibration["pooled_denominator"]


def test_the_frozen_v2_thresholds_directions_and_hard_flags_are_preserved(
    record: dict,
) -> None:
    gates = frozen_structural_gates(REPOSITORY_ROOT)
    for calibration in record["metric_calibrations"]:
        frozen = gates[calibration["metric"]]
        assert calibration["frozen_v2_threshold"] == frozen["threshold"]
        assert calibration["direction"] == frozen["direction"]
        assert calibration["hard"] is frozen["hard"]
        assert calibration["frozen_v2_threshold_portability"] == (
            "CARRIED_FORWARD_UNCALIBRATED"
        )
        assert calibration["hard_soft_status_source"] == (
            "INHERITED_FROM_FROZEN_PARENT_UNCHANGED"
        )
    assert sum(item["hard"] for item in record["metric_calibrations"]) == 5


def test_the_classification_leaves_v3_proposed_and_the_sealed_sample_shut(
    record: dict,
) -> None:
    classification = record["classification"]
    assert classification["outcome"] == CALIBRATION_INSUFFICIENT
    assert classification["v3_frozen"] is False
    assert classification["successor_status_after_this_task"] == (
        "PROPOSED_PENDING_THRESHOLD_CALIBRATION"
    )
    assert classification["validator_construction_authorized"] is False
    assert classification["sealed_sample_collection_authorized"] is False
    assert classification["sealed_sample_opening_authorized"] is False
    assert classification["unresolved_hard_gates"] == [
        "breakout_disagreement_rate",
        "reclaim_disagreement_rate",
        "within_1_week_swing_disagreement_rate",
        "within_2_week_swing_disagreement_rate",
    ]
    assert record["btc019_status"] == "IN_PROGRESS"
    assert record["production_canonical_reference"] == "UNRESOLVED"
    assert record["production_promotion_authorized"] is False
    assert record["production_swing_semantics_changed"] is False
    assert record["frozen_v2_artifacts_changed"] is False


def test_the_record_is_deterministic_across_repeated_runs(record: dict) -> None:
    assert build_calibration_record(REPOSITORY_ROOT) == record


def test_the_record_does_not_depend_on_the_callers_decimal_context(record: dict) -> None:
    with decimal.localcontext(Context(prec=7, rounding=decimal.ROUND_CEILING)):
        assert build_calibration_record(REPOSITORY_ROOT) == record


# =============================================================================
# integrity
# =============================================================================


def test_written_artifacts_are_deterministic_ascii(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    write_calibration_artifacts(REPOSITORY_ROOT, first)
    write_calibration_artifacts(REPOSITORY_ROOT, second)
    for name in (GOVERNANCE_FILENAME, CALIBRATION_RECORD_FILENAME):
        assert (first / name).read_bytes() == (second / name).read_bytes()
        (first / name).read_text(encoding="ascii")


def test_the_persisted_artifacts_recompute_from_the_repository() -> None:
    persisted = verify_calibration_artifacts(REPOSITORY_ROOT, CALIBRATION_DIR)
    assert persisted["schema_version"] == CALIBRATION_SCHEMA_VERSION
    assert persisted["classification"]["outcome"] == CALIBRATION_INSUFFICIENT


def test_a_tampered_governance_artifact_is_refused(tmp_path: Path) -> None:
    write_calibration_artifacts(REPOSITORY_ROOT, tmp_path)
    path = tmp_path / GOVERNANCE_FILENAME
    payload = json.loads(path.read_text())
    payload["comparability_sufficiency"]["minimum_structural_comparability_rate"] = "0"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(ThresholdCalibrationError, match="tampered"):
        restore_governance_definition(tmp_path)


def test_a_tampered_pair_universe_is_refused(tmp_path: Path) -> None:
    write_calibration_artifacts(REPOSITORY_ROOT, tmp_path)
    path = tmp_path / GOVERNANCE_FILENAME
    payload = json.loads(path.read_text())
    payload["pair_universe"]["gate_pairs"] = ["bitstamp_vs_coinbase"]
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(ThresholdCalibrationError, match="tampered"):
        restore_governance_definition(tmp_path)


def test_a_tampered_matching_algorithm_is_refused(tmp_path: Path) -> None:
    write_calibration_artifacts(REPOSITORY_ROOT, tmp_path)
    path = tmp_path / GOVERNANCE_FILENAME
    payload = json.loads(path.read_text())
    payload["within_week_matching"]["algorithm_id"] = "NEAREST_ADMISSIBLE_PAIR_FIRST"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(ThresholdCalibrationError, match="tampered"):
        restore_governance_definition(tmp_path)


def test_a_governance_artifact_from_another_parent_is_refused(tmp_path: Path) -> None:
    write_calibration_artifacts(REPOSITORY_ROOT, tmp_path)
    path = tmp_path / GOVERNANCE_FILENAME
    payload = json.loads(path.read_text())
    payload["parent_definition_sha256"] = "0" * 64
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(ThresholdCalibrationError, match="different parent"):
        restore_governance_definition(tmp_path)


def test_a_governance_artifact_from_another_comparison_contract_is_refused(
    tmp_path: Path,
) -> None:
    write_calibration_artifacts(REPOSITORY_ROOT, tmp_path)
    path = tmp_path / GOVERNANCE_FILENAME
    payload = json.loads(path.read_text())
    payload["comparison_contract_version"] = "CROSS_PROVIDER_STRUCTURE_COMPARISON_V1"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(ThresholdCalibrationError, match="different comparison contract"):
        restore_governance_definition(tmp_path)


def test_a_tampered_threshold_is_refused(tmp_path: Path) -> None:
    write_calibration_artifacts(REPOSITORY_ROOT, tmp_path)
    path = tmp_path / CALIBRATION_RECORD_FILENAME
    payload = json.loads(path.read_text())
    payload["metric_calibrations"][0]["selected_threshold"] = "0.99"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(ThresholdCalibrationError, match="tampered"):
        restore_calibration_record(tmp_path)


def test_a_record_that_promotes_an_insufficient_metric_is_refused(tmp_path: Path) -> None:
    write_calibration_artifacts(REPOSITORY_ROOT, tmp_path)
    path = tmp_path / CALIBRATION_RECORD_FILENAME
    payload = json.loads(path.read_text())
    target = next(
        item
        for item in payload["metric_calibrations"]
        if item["status"] != METRIC_CALIBRATED
    )
    target["selected_threshold_usable"] = True
    body = {key: value for key, value in payload.items() if key != "artifact_digest"}
    payload["artifact_digest"] = __import__("hashlib").sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
            "ascii"
        )
    ).hexdigest()
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(ThresholdCalibrationError, match="did not earn"):
        restore_calibration_record(tmp_path)


def test_a_record_claiming_sealed_access_is_refused(tmp_path: Path) -> None:
    write_calibration_artifacts(REPOSITORY_ROOT, tmp_path)
    path = tmp_path / CALIBRATION_RECORD_FILENAME
    payload = json.loads(path.read_text())
    payload["sealed_sample_opened"] = True
    body = {key: value for key, value in payload.items() if key != "artifact_digest"}
    payload["artifact_digest"] = __import__("hashlib").sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
            "ascii"
        )
    ).hexdigest()
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(ThresholdCalibrationError, match="sealed-sample access"):
        restore_calibration_record(tmp_path)


def test_a_persisted_record_that_no_longer_recomputes_is_refused(tmp_path: Path) -> None:
    write_calibration_artifacts(REPOSITORY_ROOT, tmp_path)
    path = tmp_path / CALIBRATION_RECORD_FILENAME
    payload = json.loads(path.read_text())
    payload["metric_calibrations"][0]["pooled_denominator"] += 1
    body = {key: value for key, value in payload.items() if key != "artifact_digest"}
    payload["artifact_digest"] = __import__("hashlib").sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
            "ascii"
        )
    ).hexdigest()
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(ThresholdCalibrationError, match="does not recompute"):
        verify_calibration_artifacts(REPOSITORY_ROOT, tmp_path)


def test_a_changed_sample_digest_refuses_the_whole_calibration(tmp_path: Path) -> None:
    from btc_predictor.research.structural_threshold_calibration import (
        calibration_evidence,
    )

    root = tmp_path / "root"
    for relative in _GOVERNANCE_INPUTS + PERMITTED_CALIBRATION_SAMPLE_DIRS:
        source = REPOSITORY_ROOT / relative
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    corrupted = root / PERMITTED_CALIBRATION_SAMPLE_DIRS[0] / "bitstamp_btc_usd_1h.jsonl.gz"
    corrupted.write_bytes(corrupted.read_bytes() + b"\x00")
    with pytest.raises(ValueError, match="digest mismatch"):
        calibration_evidence(root)


def test_the_sealed_window_is_refused_by_the_inherited_guard() -> None:
    from btc_predictor.research.structural_threshold_calibration import (
        guard_sealed_sample,
    )

    with pytest.raises(UntouchedValidationSampleGuardError):
        guard_sealed_sample(
            start=datetime(2016, 1, 4, tzinfo=UTC),
            end=datetime(2016, 3, 7, tzinfo=UTC),
            purpose="test",
        )


def test_no_calibration_input_lies_inside_the_sealed_window(record: dict) -> None:
    sealed_end = datetime(2019, 11, 30, 23, tzinfo=UTC)
    for dataset in record["datasets"].values():
        start = datetime.fromisoformat(dataset["historical_period_start"])
        assert start > sealed_end


# =============================================================================
# the objective's own boundaries, on synthetic evidence
# =============================================================================


def _synthetic_rows(counts: tuple[tuple[int, int], ...], *, state: str = PAIR_ADMISSIBLE):
    rows = []
    for index, (numerator, denominator) in enumerate(counts):
        rate = exact_rate(numerator, denominator)
        rows.append(
            {
                "comparison_id": f"pair_{index}",
                "series_pair": ["bitfinex", "bitstamp"],
                "metric": "synthetic",
                "measurement_state": measurement_state(
                    candidate_event_count=max(denominator, 1),
                    denominator=denominator,
                ),
                "numerator": numerator,
                "denominator": denominator,
                "rate": None if rate is None else str(rate),
                "candidate_event_count": max(denominator, 1),
                "all_detected_event_count": max(denominator, 1),
                "comparable_event_count": denominator,
                "not_comparable_event_count": max(denominator, 1) - denominator,
                "structural_comparability_rate": "1",
                "not_comparable_rate": "0",
                "not_comparable_reason_counts": {},
                "uncertainty": (
                    None
                    if denominator == 0
                    else wilson_interval(numerator, denominator).as_record()
                ),
                "state": state,
                "pair_purpose": PAIR_PURPOSE_CALIBRATION,
                "reason_codes": [] if state == PAIR_ADMISSIBLE else [PAIR_NOT_IN_UNIVERSE],
            }
        )
    return rows


_SYNTHETIC_GATE = {
    "threshold": "0.05",
    "direction": "maximum",
    "hard": True,
    "validation_stage": "historical_oos",
}


def test_a_knife_edge_surface_cannot_produce_a_calibrated_metric() -> None:
    from btc_predictor.research.structural_threshold_calibration import calibrate_metric

    # 6/28 = 0.2142 sits between the 0.20 and 0.25 grid values, so the
    # neighbour below the selected threshold changes that pair's historical
    # verdict and the metric must not be published as calibrated.
    result = calibrate_metric(
        "structural_state_disagreement_rate",
        {
            "sample_a": _synthetic_rows(((6, 28), (1, 26), (1, 28))),
            "sample_b": _synthetic_rows(((0, 23), (0, 22), (2, 29))),
        },
        frozen_gate=_SYNTHETIC_GATE,
    )
    assert result["selected_threshold"] == "0.25"
    assert result["status"] == METRIC_UNSTABLE
    assert result["sensitivity"]["neighbours_that_move_historical_verdicts"] == ["0.20"]
    assert result["selected_threshold_usable"] is False


def test_no_admissible_calibration_evidence_cannot_produce_a_calibrated_metric() -> None:
    from btc_predictor.research.structural_threshold_calibration import calibrate_metric

    result = calibrate_metric(
        "structural_state_disagreement_rate",
        {
            "sample_a": _synthetic_rows(((1, 20),), state=PAIR_INADMISSIBLE),
            "sample_b": _synthetic_rows(((0, 20),), state=PAIR_INADMISSIBLE),
        },
        frozen_gate=_SYNTHETIC_GATE,
    )
    assert result["status"] == METRIC_INSUFFICIENT
    assert result["reference_band"] is None
    assert result["selected_threshold"] is None


def test_a_zero_comparable_denominator_never_becomes_a_zero_rate() -> None:
    rows = _synthetic_rows(((0, 0),))
    assert rows[0]["rate"] is None
    assert rows[0]["measurement_state"] == UNDEFINED_NO_COMPARABLE_EVENTS
    assert rows[0]["uncertainty"] is None


# =============================================================================
# the published report


def test_the_report_never_renders_a_probability_greater_than_one(
    governance: dict, record: dict
) -> None:
    """A sub-1e-6 operating characteristic must not lose its exponent.

    ``str(Decimal)`` goes scientific below 1e-6, so truncating the persisted
    string published ``1.2125`` for ``1.2125E-8``: a false-rejection column
    that read as an impossible probability and as though it rose with the
    threshold.
    """

    report = calibration_markdown(governance, record)
    rendered = re.findall(r"([0-9]+\.[0-9]+) / ([0-9]+\.[0-9]+)", report)
    assert rendered
    for false_rejection, power in rendered:
        assert Decimal(false_rejection) <= Decimal(1)
        assert Decimal(power) <= Decimal(1)
    assert "E-" not in report


@pytest.mark.parametrize(
    ("value", "digits", "expected"),
    (
        ("1.212591878623292637242216099E-8", 6, "0.0000"),
        ("2.211694676594633952760323174E-7", 6, "0.0000"),
        ("0.00001067893125966141030889479526", 6, "0.0000"),
        ("0.9995507463577667966831864074", 6, "0.9995"),
        ("0.107142857142857142857142857", 8, "0.107142"),
        ("0", 6, "0"),
        ("1", 6, "1"),
    ),
)
def test_a_rendered_value_keeps_its_scale(value: str, digits: int, expected: str) -> None:
    assert _rendered(value, digits) == expected


def test_the_written_report_carries_no_impossible_probability(tmp_path: Path) -> None:
    write_calibration_artifacts(REPOSITORY_ROOT, tmp_path)
    report = (tmp_path / CALIBRATION_REPORT_FILENAME).read_text()
    for false_rejection, power in re.findall(
        r"([0-9]+\.[0-9]+) / ([0-9]+\.[0-9]+)", report
    ):
        assert Decimal(false_rejection) <= Decimal(1)
        assert Decimal(power) <= Decimal(1)
