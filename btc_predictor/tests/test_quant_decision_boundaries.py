from datetime import UTC, datetime
from decimal import Decimal

import numpy as np

from btc_predictor.features import (
    CrowdingFlagInput,
    calculate_crowding_flag,
    calculate_regime_classification,
)
from btc_predictor.levels import cluster_price_levels
from btc_predictor.quant import (
    DECISION_COMPARISON_POLICY_VERSION,
    capital_at_risk,
    decision_greater,
    decision_greater_equal,
    decision_less,
    decision_less_equal,
)


def test_decision_comparison_policy_freezes_inclusive_and_strict_boundaries() -> None:
    threshold = Decimal("3.0")

    assert DECISION_COMPARISON_POLICY_VERSION == "DECISION_COMPARISON_V1"
    for equivalent in (
        Decimal("3.0"),
        Decimal("2.999999999999999"),
        Decimal("3.000000000000001"),
    ):
        assert decision_greater_equal(equivalent, threshold)
        assert decision_less_equal(equivalent, threshold)
        assert not decision_greater(equivalent, threshold)
        assert not decision_less(equivalent, threshold)

    assert decision_less(Decimal("2.999999999"), threshold)
    assert decision_greater(Decimal("3.000000001"), threshold)

    fractional_threshold = 0.15
    for equivalent in (
        fractional_threshold,
        np.nextafter(fractional_threshold, -np.inf),
        np.nextafter(fractional_threshold, np.inf),
    ):
        assert decision_greater_equal(equivalent, fractional_threshold)
        assert decision_less_equal(equivalent, fractional_threshold)
        assert not decision_greater(equivalent, fractional_threshold)
        assert not decision_less(equivalent, fractional_threshold)


def test_float_decimal_artifacts_do_not_change_score_band_or_zscore_flags() -> None:
    classification = calculate_regime_classification(
        Decimal("64.999999999999999")
    )
    crowding = calculate_crowding_flag(
        CrowdingFlagInput(
            funding_zscore=Decimal("1.999999999999999"),
            basis_zscore=None,
            oi_intensity_percentile=None,
        ),
        funding_zscore_min=Decimal("2"),
    )

    assert classification.regime == "BULL"
    assert crowding.flagged is True
    assert "CROWDING_FUNDING_EXCESS" in crowding.reason_codes


def test_atr_distance_boundary_uses_the_same_decision_policy() -> None:
    as_of = datetime(2026, 1, 11, tzinfo=UTC)
    levels = (
        _level("100"),
        _level("100.15", feature_id="MONTHLY_SWING_LEVEL"),
    )

    result = cluster_price_levels(
        levels,
        as_of=as_of,
        reference_price="110",
        cluster_atr="1",
        cluster_atr_distance_threshold="0.15",
    )

    assert len(result.clusters) == 1
    assert result.clusters[0].member_count == 2


def test_risk_cap_boundary_uses_exact_expected_decisions() -> None:
    risk = capital_at_risk(10, 0.3)

    assert risk == 3.0
    assert decision_less_equal(risk, Decimal("3"))
    assert decision_less_equal(Decimal("3.000000000000001"), Decimal("3"))
    assert not decision_less_equal(Decimal("3.000000001"), Decimal("3"))


def _level(
    price: str,
    *,
    feature_id: str = "WEEKLY_SWING_LEVEL",
) -> dict[str, str]:
    return {
        "feature_id": feature_id,
        "level_type": "swing_low",
        "price": price,
        "detected_at": "2026-01-10T00:00:00+00:00",
        "level_timestamp": "2026-01-01T00:00:00+00:00",
        "exchange": "coinbase",
        "symbol": "BTC-USD",
        "timeframe": "1w",
        "provider": "coinbase",
    }
