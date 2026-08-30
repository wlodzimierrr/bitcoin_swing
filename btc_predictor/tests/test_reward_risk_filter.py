"""BTC-143: reward reference selection and the R/R filter."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.risk import (
    BEARISH_DISTRIBUTION_SETUP,
    BULL_TREND_CONTINUATION_SETUP,
    CONSERVATIVE_MEASURED_MOVE,
    DEFAULT_MINIMUM_REWARD_RISK,
    MAJOR_RESISTANCE_CLUSTER,
    MAJOR_REWARD_TIMEFRAMES,
    PREFERRED_REWARD_RISK_MAX,
    PREFERRED_REWARD_RISK_MIN,
    PRIOR_LOCAL_SWING_HIGH,
    PRIOR_RANGE_HIGH,
    REWARD_REFERENCE_PRIORITY,
    REWARD_RISK_FEATURE_ID,
    REWARD_RISK_POLICY_VERSION,
    REWARD_RISK_REASON_CODES,
    RewardReference,
    RewardRiskResult,
    evaluate_reward_risk,
    initial_stop_for_setup,
    reward_risk_for_stop,
    select_reward_reference,
    select_structural_invalidation,
    volatility_buffer_for_invalidation,
)

AS_OF = datetime(2026, 6, 1, tzinfo=UTC)
DETECTED = datetime(2026, 1, 1, tzinfo=UTC)


def resistance(
    cluster_id: str,
    lower: str,
    upper: str,
    *,
    timeframe: str = "1w",
    detected_at: datetime = DETECTED,
    zone_type: str = "resistance",
) -> dict[str, object]:
    return {
        "cluster_id": cluster_id,
        "zone_type": zone_type,
        "lower_bound": lower,
        "upper_bound": upper,
        "members": [{"source_timeframe": timeframe}],
        "detected_at": detected_at,
    }


def test_metadata_is_stable() -> None:
    assert REWARD_RISK_FEATURE_ID == "REWARD_RISK_FILTER"
    assert REWARD_RISK_POLICY_VERSION == "REWARD_RISK_FILTER_V1"
    assert DEFAULT_MINIMUM_REWARD_RISK == Decimal("2")
    assert (PREFERRED_REWARD_RISK_MIN, PREFERRED_REWARD_RISK_MAX) == (
        Decimal("2.5"),
        Decimal("3.0"),
    )
    assert MAJOR_REWARD_TIMEFRAMES == ("1w", "1mo")
    assert REWARD_REFERENCE_PRIORITY == (
        MAJOR_RESISTANCE_CLUSTER,
        PRIOR_LOCAL_SWING_HIGH,
        PRIOR_RANGE_HIGH,
        CONSERVATIVE_MEASURED_MOVE,
    )


# --- strict priority order ----------------------------------------------


def test_priority_1_beats_a_nearer_lower_tier_reference() -> None:
    reference, _ = select_reward_reference(
        entry_price="10000",
        resistance_clusters=[resistance("weekly", "11000", "11200")],
        swing_highs=["10100"],
        range_highs=["10050"],
        measured_move="10020",
    )

    # The rulebook order is strict: a nearer swing high does not override a
    # major resistance cluster.
    assert reference.reference_type == MAJOR_RESISTANCE_CLUSTER
    assert reference.price == Decimal("11000")
    assert reference.priority == 1


@pytest.mark.parametrize(
    ("kwargs", "expected_type", "expected_price"),
    [
        ({"swing_highs": ["10500"], "range_highs": ["10800"]},
         PRIOR_LOCAL_SWING_HIGH, Decimal("10500")),
        ({"range_highs": ["10800"], "measured_move": "10400"},
         PRIOR_RANGE_HIGH, Decimal("10800")),
        ({"measured_move": "10400"},
         CONSERVATIVE_MEASURED_MOVE, Decimal("10400")),
    ],
)
def test_each_tier_is_used_when_higher_tiers_are_empty(
    kwargs,
    expected_type: str,
    expected_price: Decimal,
) -> None:
    reference, _ = select_reward_reference(entry_price="10000", **kwargs)

    assert reference.reference_type == expected_type
    assert reference.price == expected_price


def test_nearest_reference_wins_within_a_tier() -> None:
    reference, _ = select_reward_reference(
        entry_price="10000",
        resistance_clusters=[
            resistance("far", "12000", "12200"),
            resistance("near", "10500", "10700"),
        ],
    )

    assert reference.source_id == "near"
    # Reward is measured to the near edge of the zone.
    assert reference.price == Decimal("10500")


def test_only_major_timeframe_clusters_qualify_for_priority_1() -> None:
    reference, considered = select_reward_reference(
        entry_price="10000",
        resistance_clusters=[resistance("daily", "10200", "10300", timeframe="1d")],
        swing_highs=["10600"],
    )

    # A daily cluster is not a "major weekly/monthly" reference, so the swing
    # high takes over even though the daily level is nearer.
    assert reference.reference_type == PRIOR_LOCAL_SWING_HIGH
    assert reference.price == Decimal("10600")
    assert all(
        item.reference_type != MAJOR_RESISTANCE_CLUSTER for item in considered
    )


def test_monthly_clusters_also_qualify() -> None:
    reference, _ = select_reward_reference(
        entry_price="10000",
        resistance_clusters=[resistance("monthly", "11000", "11500", timeframe="1mo")],
    )

    assert reference.reference_type == MAJOR_RESISTANCE_CLUSTER


def test_references_at_or_below_entry_are_not_credible() -> None:
    reference, considered = select_reward_reference(
        entry_price="10000",
        resistance_clusters=[resistance("below", "9000", "9500")],
        swing_highs=["10000", "9800"],
    )

    # Nothing above entry means no reward is available at all.
    assert reference is None
    assert considered  # they were still evaluated and are reportable


def test_references_detected_after_as_of_are_excluded() -> None:
    reference, _ = select_reward_reference(
        entry_price="10000",
        resistance_clusters=[
            resistance("future", "10500", "10700", detected_at=AS_OF + timedelta(hours=1)),
            resistance("known", "11000", "11200"),
        ],
        as_of=AS_OF,
    )

    assert reference.source_id == "known"


def test_short_side_measures_reward_downward() -> None:
    reference, _ = select_reward_reference(
        entry_price="10000",
        direction="short",
        resistance_clusters=[resistance("support", "9000", "9400", zone_type="support")],
    )

    assert reference.reference_type == MAJOR_RESISTANCE_CLUSTER
    # For a short the far edge downward is the zone's upper bound.
    assert reference.price == Decimal("9400")


# --- the filter ----------------------------------------------------------


def reference_at(price: str) -> RewardReference:
    return RewardReference(
        reference_type=MAJOR_RESISTANCE_CLUSTER, priority=1, price=Decimal(price)
    )


def test_ratio_is_reward_over_risk() -> None:
    result = evaluate_reward_risk(
        entry_price="10000",
        stop_price="9500",
        reward_reference=reference_at("11500"),
    )

    assert result.risk == Decimal("500")
    assert result.reward == Decimal("1500")
    assert result.reward_risk == Decimal("3")
    assert result.passes is True


def test_the_minimum_is_inclusive() -> None:
    at_minimum = evaluate_reward_risk(
        entry_price="10000", stop_price="9500", reward_reference=reference_at("11000")
    )
    below = evaluate_reward_risk(
        entry_price="10000", stop_price="9500", reward_reference=reference_at("10999")
    )

    assert at_minimum.reward_risk == Decimal("2")
    assert at_minimum.passes is True
    assert below.passes is False
    assert below.reason_codes == ("REWARD_RISK_BELOW_MINIMUM",)


def test_the_preferred_band_is_reported_without_changing_the_verdict() -> None:
    preferred = evaluate_reward_risk(
        entry_price="10000", stop_price="9500", reward_reference=reference_at("11400")
    )
    beyond = evaluate_reward_risk(
        entry_price="10000", stop_price="9500", reward_reference=reference_at("13000")
    )

    assert preferred.reward_risk == Decimal("2.8")
    assert "REWARD_RISK_PREFERRED_BAND" in preferred.reason_codes
    assert beyond.passes is True
    assert "REWARD_RISK_PREFERRED_BAND" not in beyond.reason_codes


def test_no_credible_reference_fails_the_filter() -> None:
    result = evaluate_reward_risk(
        entry_price="10000", stop_price="9500", reward_reference=None
    )

    # Acceptance criterion: absence of structure is a failure, never a pass
    # and never a neutral outcome.
    assert result.passes is False
    assert result.reward_risk is None
    assert result.reason_codes == ("REWARD_RISK_NO_REWARD_REFERENCE",)


def test_a_reference_behind_entry_fails_rather_than_inverting() -> None:
    result = evaluate_reward_risk(
        entry_price="10000", stop_price="9500", reward_reference=reference_at("9000")
    )

    assert result.passes is False
    assert result.reason_codes == ("REWARD_RISK_INVALID_RISK",)


def test_a_stop_on_the_wrong_side_fails_rather_than_inverting() -> None:
    result = evaluate_reward_risk(
        entry_price="10000", stop_price="10500", reward_reference=reference_at("11500")
    )

    assert result.passes is False
    assert result.reason_codes == ("REWARD_RISK_INVALID_RISK",)


def test_missing_entry_or_stop_is_incomplete_and_fails() -> None:
    for kwargs in ({"entry_price": None}, {"stop_price": None}):
        base = {
            "entry_price": "10000",
            "stop_price": "9500",
            "reward_reference": reference_at("11500"),
        }
        result = evaluate_reward_risk(**{**base, **kwargs})
        assert result.complete is False
        assert result.passes is False
        assert result.reason_codes == ("REWARD_RISK_INPUT_MISSING",)


def test_a_custom_minimum_is_honoured() -> None:
    result = evaluate_reward_risk(
        entry_price="10000",
        stop_price="9500",
        reward_reference=reference_at("11500"),
        minimum_reward_risk="4",
    )

    assert result.reward_risk == Decimal("3")
    assert result.passes is False
    assert result.minimum_reward_risk == Decimal("4")


def test_short_side_ratio_is_mirrored() -> None:
    result = evaluate_reward_risk(
        entry_price="10000",
        stop_price="10500",
        direction="short",
        reward_reference=reference_at("8500"),
    )

    assert result.risk == Decimal("500")
    assert result.reward == Decimal("1500")
    assert result.reward_risk == Decimal("3")
    assert result.passes is True


def test_ratio_matches_the_btc047_quant_kernel() -> None:
    """The Decimal filter must agree with the shared float64 primitive."""

    from btc_predictor.quant.risk import reward_risk_ratio

    for entry, stop, target in (
        ("10000", "9500", "11500"),
        ("10000", "9000", "12000"),
        ("8000", "7600", "9200"),
    ):
        result = evaluate_reward_risk(
            entry_price=entry, stop_price=stop, reward_reference=reference_at(target)
        )
        expected = reward_risk_ratio(
            float(entry), float(stop), float(target), side="long"
        )
        assert abs(float(result.reward_risk) - float(expected)) < 1e-9


# --- canonical path ------------------------------------------------------


def support_zone(cluster_id: str, lower: str, upper: str) -> dict[str, object]:
    return {
        "feature_id": "LEVEL_CLUSTER",
        "cluster_id": cluster_id,
        "zone_type": "support",
        "lower_bound": lower,
        "upper_bound": upper,
        "center_price": str((Decimal(lower) + Decimal(upper)) / 2),
        "confluence_score": "75",
        "member_count": 3,
        "detected_at": DETECTED,
    }


def long_stop(entry: str = "10000"):
    invalidation = select_structural_invalidation(
        [support_zone("z", "9400", "9600")],
        setup=BULL_TREND_CONTINUATION_SETUP,
        entry_price=entry,
        as_of=AS_OF,
    )
    buffer = volatility_buffer_for_invalidation(invalidation, atr="500")
    return initial_stop_for_setup(invalidation, buffer)


def test_canonical_path_filters_a_btc142_stop() -> None:
    stop = long_stop()

    result = reward_risk_for_stop(
        stop, resistance_clusters=[resistance("weekly", "11500", "11800")]
    )

    # stop 9400 - 150 buffer = 9250, so risk is 750 against 1500 reward.
    assert stop.stop_price == Decimal("9250.00")
    assert result.risk == Decimal("750.00")
    assert result.reward == Decimal("1500")
    assert result.passes is True
    assert result.direction == "long"


def test_canonical_path_takes_geometry_from_the_stop() -> None:
    stop = long_stop()

    result = reward_risk_for_stop(
        stop, resistance_clusters=[resistance("weekly", "11500", "11800")]
    )

    assert result.entry_price == stop.entry_price
    assert result.stop_price == stop.stop_price
    assert result.direction == stop.direction


def test_canonical_path_accepts_a_persisted_stop_record() -> None:
    stop = long_stop()
    clusters = [resistance("weekly", "11500", "11800")]

    assert (
        reward_risk_for_stop(stop, resistance_clusters=clusters).as_record()
        == reward_risk_for_stop(
            stop.as_record(), resistance_clusters=clusters
        ).as_record()
    )


def test_canonical_path_fails_when_no_structure_exists_above_entry() -> None:
    result = reward_risk_for_stop(long_stop(), resistance_clusters=[])

    assert result.passes is False
    assert result.reason_codes == ("REWARD_RISK_NO_REWARD_REFERENCE",)


def test_an_incomplete_stop_propagates_as_a_failure() -> None:
    empty = select_structural_invalidation(
        [], setup=BULL_TREND_CONTINUATION_SETUP, entry_price="10000", as_of=AS_OF
    )
    buffer = volatility_buffer_for_invalidation(empty, atr="500")
    stop = initial_stop_for_setup(empty, buffer)

    result = reward_risk_for_stop(
        stop, resistance_clusters=[resistance("weekly", "11500", "11800")]
    )

    assert stop.complete is False
    assert result.complete is False
    assert result.passes is False


# --- persistence and determinism ----------------------------------------


def test_recomputation_is_deterministic() -> None:
    stop = long_stop()
    clusters = [resistance("weekly", "11500", "11800")]

    first = reward_risk_for_stop(stop, resistance_clusters=clusters)
    second = reward_risk_for_stop(stop, resistance_clusters=clusters)

    assert first.as_record() == second.as_record()


def test_record_persists_the_selected_reference_and_is_reproducible() -> None:
    result = reward_risk_for_stop(
        long_stop(),
        resistance_clusters=[resistance("weekly", "11500", "11800")],
        swing_highs=["10800"],
        config_metadata={"config_version": "strategy_config_v2"},
    )
    record = result.as_record()

    assert isinstance(result, RewardRiskResult)
    assert record["feature_id"] == "REWARD_RISK_FILTER"
    # Acceptance criterion: the selected reward reference is persisted.
    assert record["reward_reference"]["reference_type"] == MAJOR_RESISTANCE_CLUSTER
    assert record["reward_reference"]["price"] == "11500"
    assert record["reward_reference"]["source_id"] == "weekly"
    assert record["reward_reference"]["priority"] == 1
    # Acceptance criterion: R/R is reproducible from the stored values.
    entry = Decimal(record["entry_price"])
    stop_price = Decimal(record["stop_price"])
    target = Decimal(record["reward_reference"]["price"])
    assert (target - entry) / (entry - stop_price) == Decimal(record["reward_risk"])
    # Rejected alternatives stay auditable.
    assert any(
        item["reference_type"] == PRIOR_LOCAL_SWING_HIGH
        for item in record["considered_references"]
    )
    assert record["config_metadata"] == {"config_version": "strategy_config_v2"}


def test_reason_codes_are_drawn_from_the_declared_set() -> None:
    results = [
        evaluate_reward_risk(
            entry_price="10000", stop_price="9500", reward_reference=reference_at("11500")
        ),
        evaluate_reward_risk(
            entry_price="10000", stop_price="9500", reward_reference=None
        ),
        evaluate_reward_risk(
            entry_price="10000", stop_price="9500", reward_reference=reference_at("10100")
        ),
        evaluate_reward_risk(
            entry_price=None, stop_price="9500", reward_reference=None
        ),
    ]

    for result in results:
        for code in result.reason_codes:
            assert code in REWARD_RISK_REASON_CODES
