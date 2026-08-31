from dataclasses import replace
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.features.entry import (
    ENTRY_ACTION_CLASSIFICATION_VERSION,
    ENTRY_ACTION_FEATURE_ID,
    ENTRY_ACTION_LABELS,
    ENTRY_ACTION_REASON_CODES,
    ENTRY_ACTION_THRESHOLD_IDS,
    EntryActionResult,
    classify_entry_action,
)


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        ("0", "IGNORE"),
        ("69.99", "IGNORE"),
        ("70", "WATCH"),
        ("79.999", "WATCH"),
        ("80", "VALID"),
        ("84.999", "VALID"),
        ("85", "STRONG"),
        ("89.999", "STRONG"),
        ("90", "EXCEPTIONAL"),
        ("100", "EXCEPTIONAL"),
    ],
)
def test_entry_action_boundaries(score: str, expected: str) -> None:
    result = classify_entry_action(
        Decimal(score),
        strategy_config=load_strategy_config(),
    )

    assert result.action == expected
    assert result.reason_code == f"ENTRY_ACTION_{expected}"
    assert result.complete is True
    assert result.reason_codes == ()


def test_entry_action_contract_and_labels_are_stable() -> None:
    assert ENTRY_ACTION_FEATURE_ID == "ENTRY_ACTION"
    assert ENTRY_ACTION_CLASSIFICATION_VERSION == "ENTRY_ACTION_CLASSIFICATION_V1"
    assert ENTRY_ACTION_LABELS == (
        "IGNORE",
        "WATCH",
        "VALID",
        "STRONG",
        "EXCEPTIONAL",
    )
    assert ENTRY_ACTION_THRESHOLD_IDS == (
        "ignore_below",
        "watch_min",
        "valid_trade_min",
        "strong_setup_min",
        "exceptional_min",
    )
    assert ENTRY_ACTION_REASON_CODES == ("ENTRY_ACTION_SCORE_MISSING",)


def test_entry_action_record_persists_thresholds_and_versions() -> None:
    config = load_strategy_config()
    result = classify_entry_action(Decimal("85"), strategy_config=config)

    assert isinstance(result, EntryActionResult)
    assert result.as_record() == {
        "feature_id": "ENTRY_ACTION",
        "classification_version": "ENTRY_ACTION_CLASSIFICATION_V1",
        "source_feature_id": "ENTRY_CONVICTION",
        "source_score_version": "ENTRY_CONVICTION_V1_2",
        "score": "85",
        "action": "STRONG",
        "reason_code": "ENTRY_ACTION_STRONG",
        "thresholds": {
            "ignore_below": "70.0",
            "watch_min": "70.0",
            "valid_trade_min": "80.0",
            "strong_setup_min": "85.0",
            "exceptional_min": "90.0",
        },
        "config_metadata": {
            "config_version": "strategy_config_v2",
            "strategy_version": "swing_v1.2",
            "parameter_set_id": "default_phase1",
        },
        "complete": True,
        "reason_codes": [],
    }


def test_missing_score_is_explicit_and_persistable() -> None:
    result = classify_entry_action(None, strategy_config=load_strategy_config())
    record = result.as_record()

    assert result.score is None
    assert result.action is None
    assert result.reason_code is None
    assert result.complete is False
    assert result.reason_codes == ("ENTRY_ACTION_SCORE_MISSING",)
    assert record["score"] is None
    assert record["action"] is None


def test_classification_uses_thresholds_from_supplied_strategy_config() -> None:
    default = load_strategy_config()
    custom = replace(
        default,
        entry_thresholds=replace(
            default.entry_thresholds,
            ignore_below=60,
            watch_min=60,
            valid_trade_min=75,
            strong_setup_min=85,
            exceptional_min=95,
        ),
    )

    default_result = classify_entry_action(Decimal("65"), strategy_config=default)
    custom_result = classify_entry_action(Decimal("65"), strategy_config=custom)

    assert default_result.action == "IGNORE"
    assert custom_result.action == "WATCH"
    assert custom_result.thresholds["watch_min"] == Decimal("60")
    assert custom_result.config_metadata == custom.run_metadata()


@pytest.mark.parametrize("score", [Decimal("-0.01"), Decimal("100.01")])
def test_invalid_entry_action_score_fails_fast(score: Decimal) -> None:
    with pytest.raises(ValueError, match="between 0 and 100"):
        classify_entry_action(score, strategy_config=load_strategy_config())


def test_entry_action_record_rejects_action_or_reason_drift() -> None:
    result = classify_entry_action(Decimal("85"), strategy_config=load_strategy_config())

    with pytest.raises(ValueError, match="action does not match"):
        replace(result, action="VALID").as_record()
    with pytest.raises(ValueError, match="reason_codes do not match"):
        replace(result, reason_codes=("ENTRY_ACTION_SCORE_MISSING",)).as_record()


def test_entry_action_is_deterministic() -> None:
    config = load_strategy_config()

    first = classify_entry_action(Decimal("87.125"), strategy_config=config)
    second = classify_entry_action(Decimal("87.125"), strategy_config=config)

    assert first.as_record() == second.as_record()
