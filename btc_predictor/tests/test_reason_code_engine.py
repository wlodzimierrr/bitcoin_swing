from dataclasses import replace
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.features import (
    EntryConvictionInput,
    calculate_entry_conviction,
    classify_entry_action,
)
from btc_predictor.signals import (
    CANONICAL_SIGNAL_REASON_CODES,
    REASON_CODE_ENGINE_FEATURE_ID,
    REASON_CODE_ENGINE_SOURCE_IDS,
    REASON_CODE_ENGINE_VERSION,
    HardVetoInput,
    ReasonCodeEngineResult,
    RecommendationReasonCode,
    build_reason_code_engine,
    canonical_signal_reason,
    evaluate_hard_veto,
)
from btc_predictor.signals.data_quality import RECOMMENDATION_REASON_SEVERITIES


def _conviction(*, missing: bool = False):
    config = load_strategy_config()
    result = calculate_entry_conviction(
        EntryConvictionInput(
            trend_score=None if missing else Decimal("85"),
            flow_score=Decimal("85"),
            positioning_score=Decimal("85"),
            volatility_score=Decimal("85"),
            structure_score=Decimal("85"),
        ),
        strategy_config=config,
    )
    return result


def _clear_veto(**changes: object):
    values: dict[str, object] = {
        "data_quality_fail": False,
        "valid_structural_stop": True,
        "reward_risk_passes": True,
        "stress_flagged": False,
        "severe_crowding_flagged": False,
        "no_chase_blocked": False,
        "setup": "BULL_TREND_CONTINUATION",
    }
    values.update(changes)
    return evaluate_hard_veto(
        HardVetoInput(**values),  # type: ignore[arg-type]
        strategy_config=load_strategy_config(),
    )


def _complete_sources():
    config = load_strategy_config()
    conviction = _conviction()
    action = classify_entry_action(conviction.score, strategy_config=config)
    return config, conviction, action, _clear_veto()


def test_reason_code_engine_contract_is_stable() -> None:
    assert REASON_CODE_ENGINE_FEATURE_ID == "REASON_CODE_ENGINE"
    assert REASON_CODE_ENGINE_VERSION == "REASON_CODE_ENGINE_V1"
    assert REASON_CODE_ENGINE_SOURCE_IDS == (
        "entry_conviction",
        "entry_action",
        "hard_veto",
    )
    assert CANONICAL_SIGNAL_REASON_CODES == (
        "TREND_12W_POSITIVE",
        "ETF_FLOW_ACCEL_POSITIVE",
        "FUNDING_RESET",
        "OI_DELEVERAGED",
        "WEEKLY_SUPPORT_CLUSTER",
        "RECLAIM_CONFIRMED",
        "RISK_REWARD_VALID",
        "CROWDING_WARNING",
        "MACRO_WEAK",
    )


def test_canonical_signal_reasons_have_persistable_definitions() -> None:
    reasons = tuple(
        canonical_signal_reason(code) for code in CANONICAL_SIGNAL_REASON_CODES
    )

    assert tuple(reason.code for reason in reasons) == CANONICAL_SIGNAL_REASON_CODES
    assert all(reason.source_component for reason in reasons)
    assert all(reason.severity in ("info", "warning", "veto") for reason in reasons)
    assert all(reason.detail.endswith(".") for reason in reasons)
    assert canonical_signal_reason("CROWDING_WARNING").severity == "warning"
    assert canonical_signal_reason("MACRO_WEAK").source_component == "macro"


def test_complete_explanation_is_ranked_and_reconstructable() -> None:
    config, conviction, action, veto = _complete_sources()
    result = build_reason_code_engine(
        entry_conviction=conviction,
        entry_action=action,
        hard_veto=veto,
        strategy_config=config,
        signal_reasons=(
            canonical_signal_reason("TREND_12W_POSITIVE"),
            canonical_signal_reason("CROWDING_WARNING"),
            canonical_signal_reason("RISK_REWARD_VALID"),
        ),
    )
    record = result.as_record()

    assert isinstance(result, ReasonCodeEngineResult)
    assert result.entry_action == "STRONG"
    assert result.hard_veto_blocked is False
    assert result.complete is True
    assert result.reason_codes == (
        "CROWDING_WARNING",
        "HARD_VETO_CLEAR",
        "ENTRY_ACTION_STRONG",
        "ENTRY_CONVICTION_COMPLETE",
        "RISK_REWARD_VALID",
        "TREND_12W_POSITIVE",
    )
    assert record["source_versions"] == {
        "entry_conviction": "ENTRY_CONVICTION_V1_2",
        "entry_action": "ENTRY_ACTION_CLASSIFICATION_V1",
        "hard_veto": "HARD_VETO_V1",
    }
    assert record["source_complete"] == {
        "entry_conviction": True,
        "entry_action": True,
        "hard_veto": True,
    }
    assert record["config_metadata"] == config.run_metadata()
    assert [reason["reason_rank"] for reason in record["reasons"]] == list(
        range(6),
    )
    assert record["reason_codes"] == list(result.reason_codes)


def test_veto_and_upstream_evidence_rank_before_nonblocking_reasons() -> None:
    config = load_strategy_config()
    conviction = _conviction()
    action = classify_entry_action(conviction.score, strategy_config=config)
    veto = _clear_veto(
        data_quality_fail=True,
        valid_structural_stop=False,
        source_reason_codes={
            "data_quality_fail": ("DATA_QUALITY_FAIL", "MISSING_PERIOD"),
            "valid_structural_stop": ("INITIAL_STOP_INPUT_MISSING",),
        },
    )

    result = build_reason_code_engine(
        entry_conviction=conviction,
        entry_action=action,
        hard_veto=veto,
        strategy_config=config,
        signal_reasons=(canonical_signal_reason("TREND_12W_POSITIVE"),),
    )

    assert result.reason_codes[:2] == (
        "HARD_VETO_DATA_QUALITY_FAIL",
        "HARD_VETO_NO_VALID_STRUCTURAL_STOP",
    )
    assert result.reason_codes[2:5] == (
        "DATA_QUALITY_FAIL",
        "MISSING_PERIOD",
        "INITIAL_STOP_INPUT_MISSING",
    )
    assert all(reason.severity == "veto" for reason in result.reasons[:5])
    assert result.entry_action == "STRONG"
    assert result.hard_veto_blocked is True


def test_incomplete_sources_are_explained_and_propagated() -> None:
    config = load_strategy_config()
    conviction = _conviction(missing=True)
    action = classify_entry_action(conviction.score, strategy_config=config)
    result = build_reason_code_engine(
        entry_conviction=conviction,
        entry_action=action,
        hard_veto=_clear_veto(),
        strategy_config=config,
    )

    assert result.complete is False
    assert result.entry_action is None
    assert result.source_complete == {
        "entry_conviction": False,
        "entry_action": False,
        "hard_veto": True,
    }
    assert result.reason_codes == (
        "ENTRY_ACTION_SCORE_MISSING",
        "ENTRY_CONVICTION_INPUT_MISSING",
        "HARD_VETO_CLEAR",
    )


def test_signal_reason_order_and_exact_duplicates_are_input_order_independent() -> None:
    config, conviction, action, veto = _complete_sources()
    trend = canonical_signal_reason("TREND_12W_POSITIVE")
    flow = canonical_signal_reason("ETF_FLOW_ACCEL_POSITIVE")

    first = build_reason_code_engine(
        entry_conviction=conviction,
        entry_action=action,
        hard_veto=veto,
        strategy_config=config,
        signal_reasons=(trend, flow, trend),
    )
    second = build_reason_code_engine(
        entry_conviction=conviction,
        entry_action=action,
        hard_veto=veto,
        strategy_config=config,
        signal_reasons=(flow, trend),
    )

    assert first.as_record() == second.as_record()
    assert first.reason_codes.count("TREND_12W_POSITIVE") == 1


def test_conflicting_duplicate_reason_is_rejected() -> None:
    config, conviction, action, veto = _complete_sources()
    original = canonical_signal_reason("TREND_12W_POSITIVE")
    conflicting = RecommendationReasonCode(
        code=original.code,
        source_component=original.source_component,
        severity=original.severity,
        detail="Conflicting interpretation.",
    )

    with pytest.raises(ValueError, match="conflicting severity or detail"):
        build_reason_code_engine(
            entry_conviction=conviction,
            entry_action=action,
            hard_veto=veto,
            strategy_config=config,
            signal_reasons=(original, conflicting),
        )


def test_sources_must_share_config_and_score_identity() -> None:
    config, conviction, action, veto = _complete_sources()
    mismatched_config = replace(
        conviction,
        config_metadata={
            **conviction.config_metadata,
            "parameter_set_id": "different_parameters",
        },
    )
    mismatched_score = classify_entry_action(
        Decimal("86"),
        strategy_config=config,
    )

    with pytest.raises(ValueError, match="config metadata does not match"):
        build_reason_code_engine(
            entry_conviction=mismatched_config,
            entry_action=action,
            hard_veto=veto,
            strategy_config=config,
        )
    with pytest.raises(ValueError, match="score must match"):
        build_reason_code_engine(
            entry_conviction=conviction,
            entry_action=mismatched_score,
            hard_veto=veto,
            strategy_config=config,
        )


def test_result_builds_existing_recommendation_reason_rows() -> None:
    config, conviction, action, veto = _complete_sources()
    result = build_reason_code_engine(
        entry_conviction=conviction,
        entry_action=action,
        hard_veto=veto,
        strategy_config=config,
        signal_reasons=(canonical_signal_reason("RECLAIM_CONFIRMED"),),
    )

    rows = result.recommendation_records(321)

    assert [row["reason_rank"] for row in rows] == list(range(len(rows)))
    assert all(row["recommendation_id"] == 321 for row in rows)
    assert [row["code"] for row in rows] == list(result.reason_codes)
    assert set(rows[0]) == {
        "recommendation_id",
        "reason_rank",
        "code",
        "source_component",
        "severity",
        "detail",
    }


def test_result_record_rejects_rank_or_completion_drift() -> None:
    config, conviction, action, veto = _complete_sources()
    result = build_reason_code_engine(
        entry_conviction=conviction,
        entry_action=action,
        hard_veto=veto,
        strategy_config=config,
        signal_reasons=(canonical_signal_reason("TREND_12W_POSITIVE"),),
    )

    with pytest.raises(ValueError, match="deterministic engine ranking"):
        replace(result, reasons=tuple(reversed(result.reasons))).as_record()
    with pytest.raises(ValueError, match="completion state"):
        replace(result, complete=False).as_record()
    with pytest.raises(ValueError, match="hard_veto_blocked does not match"):
        replace(result, hard_veto_blocked=True).as_record()
    with pytest.raises(ValueError, match="entry_action does not match"):
        replace(result, entry_action="VALID").as_record()


def test_unknown_or_malformed_reason_codes_fail_fast() -> None:
    with pytest.raises(ValueError, match="unsupported canonical"):
        canonical_signal_reason("UNKNOWN_REASON")

    config, conviction, action, veto = _complete_sources()
    malformed = RecommendationReasonCode(
        code="not-valid",
        source_component="trend",
        severity="info",
        detail="Malformed code.",
    )
    with pytest.raises(ValueError, match="UPPER_SNAKE_CASE"):
        build_reason_code_engine(
            entry_conviction=conviction,
            entry_action=action,
            hard_veto=veto,
            strategy_config=config,
            signal_reasons=(malformed,),
        )


# --- BTC-220: engine input, identity, and persisted-record validation ------


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("feature_id", "REASON_CODES", "feature_id must be REASON_CODE_ENGINE"),
        ("engine_version", "REASON_CODE_ENGINE_V0", "engine_version must be"),
    ],
)
def test_record_rejects_engine_identity_drift(field, value, match) -> None:
    config, conviction, action, veto = _complete_sources()
    result = build_reason_code_engine(
        entry_conviction=conviction,
        entry_action=action,
        hard_veto=veto,
        strategy_config=config,
    )

    with pytest.raises(ValueError, match=match):
        replace(result, **{field: value}).as_record()


def test_record_rejects_source_version_drift() -> None:
    config, conviction, action, veto = _complete_sources()
    result = build_reason_code_engine(
        entry_conviction=conviction,
        entry_action=action,
        hard_veto=veto,
        strategy_config=config,
    )
    versions = dict(result.source_versions) | {"hard_veto": "HARD_VETO_V0"}

    with pytest.raises(ValueError, match="source_versions do not match"):
        replace(result, source_versions=versions).as_record()


def test_record_rejects_a_source_completion_map_that_is_not_the_contract() -> None:
    config, conviction, action, veto = _complete_sources()
    result = build_reason_code_engine(
        entry_conviction=conviction,
        entry_action=action,
        hard_veto=veto,
        strategy_config=config,
    )

    extra = dict(result.source_complete) | {"macro": True}
    with pytest.raises(ValueError, match="source_complete must exactly match"):
        replace(result, source_complete=extra).as_record()

    non_bool = dict(result.source_complete) | {"hard_veto": 1}
    with pytest.raises(TypeError, match="source_complete.hard_veto must be a bool"):
        replace(result, source_complete=non_bool).as_record()


def test_record_rejects_config_metadata_that_is_not_the_required_key_set() -> None:
    config, conviction, action, veto = _complete_sources()
    result = build_reason_code_engine(
        entry_conviction=conviction,
        entry_action=action,
        hard_veto=veto,
        strategy_config=config,
    )

    partial = dict(result.config_metadata)
    del partial["parameter_set_id"]
    with pytest.raises(ValueError, match="config_metadata must exactly match"):
        replace(result, config_metadata=partial).as_record()

    blank = dict(result.config_metadata) | {"config_version": "  "}
    with pytest.raises(
        ValueError,
        match="config_metadata.config_version must be a non-empty string",
    ):
        replace(result, config_metadata=blank).as_record()

    with pytest.raises(TypeError, match="config_metadata must be a mapping"):
        replace(result, config_metadata=("config_version", "x")).as_record()


def test_record_rejects_a_non_boolean_hard_veto_flag() -> None:
    config, conviction, action, veto = _complete_sources()
    result = build_reason_code_engine(
        entry_conviction=conviction,
        entry_action=action,
        hard_veto=veto,
        strategy_config=config,
    )

    with pytest.raises(TypeError, match="hard_veto_blocked must be a bool"):
        replace(result, hard_veto_blocked=1).as_record()


def test_record_rejects_an_incomplete_action_that_still_carries_a_label() -> None:
    config = load_strategy_config()
    conviction = _conviction(missing=True)
    action = classify_entry_action(conviction.score, strategy_config=config)
    result = build_reason_code_engine(
        entry_conviction=conviction,
        entry_action=action,
        hard_veto=_clear_veto(),
        strategy_config=config,
    )

    assert result.entry_action is None
    with pytest.raises(
        ValueError,
        match="incomplete entry action cannot contain an action",
    ):
        replace(result, entry_action="VALID").as_record()


def test_record_rejects_an_unsupported_action_label() -> None:
    config, conviction, action, veto = _complete_sources()
    result = build_reason_code_engine(
        entry_conviction=conviction,
        entry_action=action,
        hard_veto=veto,
        strategy_config=config,
    )

    with pytest.raises(
        ValueError,
        match="complete entry action must use a supported label",
    ):
        replace(result, entry_action="SUPER_STRONG").as_record()


@pytest.mark.parametrize(
    ("source", "match"),
    [
        ("entry_conviction", "entry_conviction must be an EntryConvictionResult"),
        ("entry_action", "entry_action must be an EntryActionResult"),
        ("hard_veto", "hard_veto must be a HardVetoResult"),
        ("strategy_config", "strategy_config must be a StrategyConfig"),
    ],
)
def test_engine_requires_the_declared_source_types(source: str, match: str) -> None:
    config, conviction, action, veto = _complete_sources()
    sources = {
        "entry_conviction": conviction,
        "entry_action": action,
        "hard_veto": veto,
        "strategy_config": config,
    }
    sources[source] = object()

    with pytest.raises(TypeError, match=match):
        build_reason_code_engine(**sources)


def test_signal_reasons_must_be_a_sequence_of_reason_codes() -> None:
    config, conviction, action, veto = _complete_sources()

    with pytest.raises(
        TypeError,
        match="signal_reasons must be a sequence of reason codes",
    ):
        build_reason_code_engine(
            entry_conviction=conviction,
            entry_action=action,
            hard_veto=veto,
            strategy_config=config,
            signal_reasons="TREND_12W_POSITIVE",
        )

    with pytest.raises(
        TypeError,
        match="signal_reasons must contain RecommendationReasonCode values",
    ):
        build_reason_code_engine(
            entry_conviction=conviction,
            entry_action=action,
            hard_veto=veto,
            strategy_config=config,
            signal_reasons=("TREND_12W_POSITIVE",),
        )


def test_canonical_signal_reason_requires_a_string_code() -> None:
    with pytest.raises(TypeError, match="code must be a string"):
        canonical_signal_reason(None)


@pytest.mark.parametrize(
    ("reason", "match"),
    [
        (
            RecommendationReasonCode(
                code="A" * 65,
                source_component="trend",
                severity="info",
                detail="Too long.",
            ),
            "UPPER_SNAKE_CASE",
        ),
        (
            RecommendationReasonCode(
                code="TREND_OK",
                source_component="c" * 65,
                severity="info",
                detail="Component too long.",
            ),
            "source_component must be <= 64 characters",
        ),
    ],
)
def test_reason_fields_are_bounded_and_use_supported_severities(
    reason,
    match: str,
) -> None:
    config, conviction, action, veto = _complete_sources()

    with pytest.raises(ValueError, match=match):
        build_reason_code_engine(
            entry_conviction=conviction,
            entry_action=action,
            hard_veto=veto,
            strategy_config=config,
            signal_reasons=(reason,),
        )


def test_engine_ranks_exactly_the_shared_reason_severity_vocabulary() -> None:
    config, conviction, action, veto = _complete_sources()
    result = build_reason_code_engine(
        entry_conviction=conviction,
        entry_action=action,
        hard_veto=veto,
        strategy_config=config,
        signal_reasons=(
            canonical_signal_reason("TREND_12W_POSITIVE"),
            canonical_signal_reason("CROWDING_WARNING"),
        ),
    )

    assert set(RECOMMENDATION_REASON_SEVERITIES) == {"info", "warning", "veto"}
    assert {reason.severity for reason in result.reasons} <= set(
        RECOMMENDATION_REASON_SEVERITIES,
    )
    # The engine ranks veto first, then warning, then info; the shared
    # vocabulary is unordered, so the engine ordering is asserted directly.
    severities = [reason.severity for reason in result.reasons]
    assert severities == sorted(
        severities,
        key=lambda value: {"veto": 0, "warning": 1, "info": 2}[value],
    )


@pytest.mark.parametrize("setup", [None, "RANGE_SCALP"])
def test_absent_or_unsupported_setup_vetoes_and_propagates_to_the_engine(
    setup,
) -> None:
    veto = _clear_veto(setup=setup)

    assert veto.blocked is True
    assert "HARD_VETO_UNSUPPORTED_SETUP" in veto.reason_codes

    config = load_strategy_config()
    conviction = _conviction()
    action = classify_entry_action(conviction.score, strategy_config=config)
    result = build_reason_code_engine(
        entry_conviction=conviction,
        entry_action=action,
        hard_veto=veto,
        strategy_config=config,
    )

    assert result.hard_veto_blocked is True
    assert "HARD_VETO_UNSUPPORTED_SETUP" in result.reason_codes
    veto_reasons = [
        reason
        for reason in result.reasons
        if reason.code == "HARD_VETO_UNSUPPORTED_SETUP"
    ]
    assert [reason.severity for reason in veto_reasons] == ["veto"]


def test_supported_setup_matching_ignores_case_and_surrounding_whitespace() -> None:
    veto = _clear_veto(setup="  bull_trend_continuation  ")

    assert veto.blocked is False
    assert veto.reason_codes == ("HARD_VETO_CLEAR",)

    config = load_strategy_config()
    conviction = _conviction()
    action = classify_entry_action(conviction.score, strategy_config=config)
    result = build_reason_code_engine(
        entry_conviction=conviction,
        entry_action=action,
        hard_veto=veto,
        strategy_config=config,
    )

    assert result.hard_veto_blocked is False
    assert "HARD_VETO_CLEAR" in result.reason_codes


def test_record_rejects_reason_entries_that_are_not_reason_codes() -> None:
    config, conviction, action, veto = _complete_sources()
    result = build_reason_code_engine(
        entry_conviction=conviction,
        entry_action=action,
        hard_veto=veto,
        strategy_config=config,
    )

    with pytest.raises(
        TypeError,
        match="reasons must contain RecommendationReasonCode values",
    ):
        replace(result, reasons=(*result.reasons, "TREND_12W_POSITIVE")).as_record()
