"""Independent RBT-002 review regressions; synthetic inputs only."""

import dataclasses
from decimal import Decimal

from btc_predictor.research_backtest import coverage
from btc_predictor.features.setup import BullTrendContinuationResult
from btc_predictor.levels.strength import LevelStrengthInput, calculate_level_strength
from btc_predictor.risk.reward import reward_risk_for_stop


def test_measured_move_has_no_target_in_the_claimed_producer() -> None:
    # A setup filter result cannot supply the target-price record required by
    # the reward selector. Its absence is optional, but still needs an explicit
    # completion-spec ruling instead of a fictitious producing owner.
    names = {field.name for field in dataclasses.fields(BullTrendContinuationResult)}
    assert not ({"price", "level_price", "measured_move"} & names)
    row = next(row for row in coverage.enumerate_input_surface()
               if row.owner == coverage._owner_path(reward_risk_for_stop) and row.name == "measured_move")
    assert row.classification.kind == coverage.KIND_OWNERLESS_UNDEFINED
    assert row.classification.input_id == "MEASURED_MOVE_REFERENCE"
    assert "MEASURED_MOVE_REFERENCE" in coverage.input_surface_summary(coverage.enumerate_input_surface())["ownerless_inputs"]


def test_volume_has_existing_rulebook_fallback_and_no_new_percentile_is_requested() -> None:
    rows = [row for row in coverage.enumerate_input_surface()
            if row.classification.input_id == "LEVEL_VOLUME_PERCENTILE"]
    assert len(rows) == 2
    assert all(row.classification.kind == coverage.KIND_OWNERLESS_FALLBACK for row in rows)
    assert all("section 9.2" in row.classification.historical_source for row in rows)
    assert all("LEVEL_VOLUME_PERCENTILE" not in item["inputs"]
               for item in coverage.derive_blockers(coverage.enumerate_input_surface()))

    # This is the actual remaining compatibility gap: zero weight does not
    # bypass the production owner's unconditional missing-component check.
    result = calculate_level_strength(
        LevelStrengthInput(("1w",), 2, Decimal("0.02"), None, Decimal("80")),
        level_id="synthetic-review-level",
        weights={"timeframe": Decimal("0.30"), "touch_count": Decimal("0.25"),
                 "reaction_magnitude": Decimal("0.25"), "volume": Decimal("0"),
                 "confluence": Decimal("0.20")},
    )
    assert not result.complete
    assert result.score is None
    assert "LEVEL_STRENGTH_INPUT_MISSING" in result.reason_codes
    requirement = next(item for item in coverage.minimum_history_requirements()
                       if item.input_id == "LEVEL_VOLUME_PERCENTILE")
    assert requirement.rule == coverage.RULE_UNIMPLEMENTED_FALLBACK
    status = coverage.earliest_evaluable_inputs((requirement,), {})[requirement.input_id]
    assert status.status == coverage.STATUS_UNIMPLEMENTED_FALLBACK
