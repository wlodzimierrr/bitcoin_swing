"""BTC-220 focused unit tests for the DECISION_COMPARISON_V1 boundary policy.

``quant.comparisons`` is the single owner of every tolerance-aware hard
decision taken by ``risk.budget``, ``risk.sizing``, ``risk.tranches``,
``risk.exposure``, ``risk.invalidation``, and ``levels.clustering``. The
boundary semantics are therefore pinned here rather than re-derived by each
consumer.
"""

from decimal import Decimal

import numpy as np
import pytest

from btc_predictor.quant import (
    PARITY_TOLERANCE,
    NumericInputError,
)
from btc_predictor.quant.comparisons import (
    DECISION_COMPARISON_POLICY_VERSION,
    DEFAULT_DECISION_TOLERANCE,
    DecisionTolerance,
    decision_compare,
    decision_equal,
    decision_greater,
    decision_greater_equal,
    decision_less,
    decision_less_equal,
)


ORDERING_HELPERS = (
    decision_equal,
    decision_greater,
    decision_greater_equal,
    decision_less,
    decision_less_equal,
)


def test_policy_version_and_default_tolerance_are_frozen() -> None:
    assert DECISION_COMPARISON_POLICY_VERSION == "DECISION_COMPARISON_V1"
    assert DEFAULT_DECISION_TOLERANCE.absolute == Decimal(
        str(PARITY_TOLERANCE.absolute),
    )
    assert DEFAULT_DECISION_TOLERANCE.relative == Decimal(
        str(PARITY_TOLERANCE.relative),
    )
    assert DEFAULT_DECISION_TOLERANCE.absolute == Decimal("1e-12")


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        (Decimal("1"), Decimal("2"), -1),
        (Decimal("2"), Decimal("2"), 0),
        (Decimal("3"), Decimal("2"), 1),
    ],
)
def test_decision_compare_returns_the_three_valued_ordering(
    left: Decimal,
    right: Decimal,
    expected: int,
) -> None:
    assert decision_compare(left, right) == expected


def test_absolute_tolerance_band_collapses_small_differences_near_zero() -> None:
    inside = Decimal("1e-13")
    outside = Decimal("1e-11")

    assert decision_compare(inside, Decimal("0")) == 0
    assert decision_compare(-inside, Decimal("0")) == 0
    assert decision_compare(outside, Decimal("0")) == 1
    assert decision_compare(-outside, Decimal("0")) == -1


def test_relative_tolerance_scales_the_band_with_operand_magnitude() -> None:
    # 1e-9 is far outside the 1e-12 absolute band but inside the relative band
    # once the operands are of order 1e6.
    small = Decimal("1e-9")

    assert decision_compare(small, Decimal("0")) == 1
    assert decision_compare(Decimal("1000000") + small, Decimal("1000000")) == 0
    assert decision_compare(Decimal("1000000.001"), Decimal("1000000")) == 1


def test_tolerance_band_uses_the_larger_operand_magnitude() -> None:
    tolerance = DecisionTolerance(absolute=Decimal("0"), relative=Decimal("0.1"))

    # 10% of max(|left|, |right|) = 10, so a difference of 9 stays equivalent
    # even though it is 90% of the smaller operand.
    assert decision_compare(Decimal("100"), Decimal("91"), tolerance=tolerance) == 0
    assert decision_compare(Decimal("100"), Decimal("89"), tolerance=tolerance) == 1


def test_comparison_is_antisymmetric_for_every_operand_pair() -> None:
    values = (Decimal("-5"), Decimal("0"), Decimal("1e-13"), Decimal("7.25"))

    for left in values:
        for right in values:
            assert decision_compare(left, right) == -decision_compare(right, left)


def test_ordering_helpers_agree_with_decision_compare() -> None:
    pairs = (
        (Decimal("1"), Decimal("2")),
        (Decimal("2"), Decimal("2")),
        (Decimal("2"), Decimal("2") + Decimal("1e-13")),
        (Decimal("3"), Decimal("2")),
    )

    for left, right in pairs:
        ordering = decision_compare(left, right)
        assert decision_equal(left, right) is (ordering == 0)
        assert decision_greater(left, right) is (ordering > 0)
        assert decision_greater_equal(left, right) is (ordering >= 0)
        assert decision_less(left, right) is (ordering < 0)
        assert decision_less_equal(left, right) is (ordering <= 0)


def test_boundary_equivalence_makes_inclusive_and_strict_helpers_disagree() -> None:
    threshold = Decimal("55")
    just_below = threshold - Decimal("1e-13")

    assert decision_greater_equal(just_below, threshold) is True
    assert decision_greater(just_below, threshold) is False
    assert decision_less_equal(just_below, threshold) is True
    assert decision_less(just_below, threshold) is False


def test_binary_float_artifacts_do_not_change_a_hard_decision() -> None:
    # 0.1 + 0.2 != 0.3 in binary float64; the decision policy treats the two
    # as the same boundary value so a threshold cannot flip on representation.
    assert 0.1 + 0.2 != 0.3
    assert decision_equal(0.1 + 0.2, 0.3) is True
    assert decision_greater(0.1 + 0.2, 0.3) is False


@pytest.mark.parametrize(
    "value",
    [
        Decimal("2.5"),
        2.5,
        "2.5",
        np.float64(2.5),
    ],
)
def test_supported_numeric_representations_compare_identically(value) -> None:
    assert decision_compare(value, Decimal("2.5")) == 0
    assert decision_compare(Decimal("2.5"), value) == 0


def test_integer_representations_are_accepted_on_both_sides() -> None:
    assert decision_compare(3, Decimal("3")) == 0
    assert decision_compare(np.int64(3), 3) == 0


@pytest.mark.parametrize("value", [True, False, np.bool_(True)])
def test_booleans_are_rejected_rather_than_silently_treated_as_0_or_1(
    value,
) -> None:
    with pytest.raises(NumericInputError, match="must not be boolean"):
        decision_compare(value, Decimal("1"))
    with pytest.raises(NumericInputError, match="must not be boolean"):
        decision_compare(Decimal("1"), value)


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
        Decimal("NaN"),
        Decimal("Infinity"),
        np.float64("nan"),
    ],
)
def test_non_finite_values_are_rejected_on_both_sides(value) -> None:
    with pytest.raises(NumericInputError, match="must be a finite numeric value"):
        decision_compare(value, Decimal("1"))
    with pytest.raises(NumericInputError, match="must be a finite numeric value"):
        decision_compare(Decimal("1"), value)


@pytest.mark.parametrize("value", [None, "abc", object(), [1.0]])
def test_non_numeric_values_are_rejected(value) -> None:
    with pytest.raises(NumericInputError, match="must be a finite numeric value"):
        decision_compare(value, Decimal("1"))


def test_error_message_names_the_offending_operand() -> None:
    with pytest.raises(NumericInputError, match="^left must be"):
        decision_compare("abc", Decimal("1"))
    with pytest.raises(NumericInputError, match="^right must be"):
        decision_compare(Decimal("1"), "abc")


def test_tolerance_normalizes_supported_representations_to_decimal() -> None:
    tolerance = DecisionTolerance(absolute=1e-9, relative="1e-8")

    assert tolerance.absolute == Decimal("1e-9")
    assert tolerance.relative == Decimal("1e-8")
    assert isinstance(tolerance.absolute, Decimal)
    assert isinstance(tolerance.relative, Decimal)


def test_zero_tolerance_restores_exact_decimal_comparison() -> None:
    exact = DecisionTolerance(absolute=Decimal("0"), relative=Decimal("0"))

    assert decision_compare(Decimal("1e-30"), Decimal("0"), tolerance=exact) == 1
    assert decision_compare(Decimal("1"), Decimal("1"), tolerance=exact) == 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"absolute": Decimal("-1e-12")},
        {"relative": Decimal("-1e-12")},
    ],
)
def test_negative_tolerances_are_rejected(kwargs) -> None:
    with pytest.raises(NumericInputError, match="must be non-negative"):
        DecisionTolerance(**kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"absolute": float("nan")},
        {"relative": float("inf")},
        {"absolute": True},
        {"relative": "abc"},
    ],
)
def test_invalid_tolerance_values_are_rejected(kwargs) -> None:
    with pytest.raises(NumericInputError):
        DecisionTolerance(**kwargs)


@pytest.mark.parametrize("tolerance", [1e-12, "1e-12", None, (1e-12, 1e-12)])
def test_tolerance_argument_must_be_a_decision_tolerance(tolerance) -> None:
    with pytest.raises(NumericInputError, match="must be a DecisionTolerance"):
        decision_compare(Decimal("1"), Decimal("2"), tolerance=tolerance)


def test_repeated_comparisons_are_deterministic() -> None:
    pairs = (
        (Decimal("55.0000000000001"), Decimal("55")),
        (Decimal("1000000.0000000001"), Decimal("1000000")),
        (0.1 + 0.2, 0.3),
    )

    def snapshot() -> list[tuple[object, ...]]:
        return [
            (
                decision_compare(left, right),
                *(helper(left, right) for helper in ORDERING_HELPERS),
            )
            for left, right in pairs
        ]

    first = snapshot()
    for _ in range(3):
        assert snapshot() == first
