from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.reporting import (
    RECOMMENDATION_RENDERER_FEATURE_ID,
    RECOMMENDATION_RENDERER_MEDIA_TYPE,
    RECOMMENDATION_RENDERER_VERSION,
    RecommendationRendererResult,
    recommendation_renderer_from_record,
    render_recommendation,
)
from btc_predictor.signals import RecommendationReasonCode


def _recommendation(**changes: object) -> dict[str, object]:
    row: dict[str, object] = {
        "recommendation_id": 170,
        "run_id": 42,
        "evaluation_time": datetime(2026, 8, 31, 0, 0, tzinfo=timezone.utc),
        "symbol": "BTC/USD",
        "timeframe": "1d",
        "regime": "BULL",
        "setup": "BULLISH_RESET",
        "direction": "long",
        "trend_score": Decimal("82"),
        "regime_score": Decimal("72"),
        "flow_score": Decimal("87"),
        "positioning_score": Decimal("84"),
        "volatility_score": Decimal("71"),
        "structure_score": Decimal("94"),
        "entry_conviction": Decimal("88"),
        "hold_score": None,
        "add_score": Decimal("86.25"),
        "entry_zone_lower": Decimal("98500"),
        "entry_zone_upper": Decimal("101000"),
        "invalidation_level": Decimal("91300"),
        "initial_stop": Decimal("89800"),
        "rr_ratio": Decimal("3.2"),
        "risk_fraction_nav": Decimal("0.005"),
        "risk_amount": Decimal("500"),
        "suggested_notional": Decimal("5100"),
        "action": "ENTER",
    }
    row.update(changes)
    return row


def _reason_rows() -> tuple[dict[str, object], ...]:
    # Deliberately returned out of query order; reason_rank owns presentation.
    return (
        {
            "recommendation_id": 170,
            "reason_rank": 2,
            "code": "TREND_12W_POSITIVE",
            "source_component": "trend",
            "severity": "info",
            "detail": "Twelve-week momentum is positive.",
        },
        {
            "recommendation_id": 170,
            "reason_rank": 0,
            "code": "MACRO_WEAK",
            "source_component": "macro",
            "severity": "warning",
            "detail": "The macro backdrop is weak.",
        },
        {
            "recommendation_id": 170,
            "reason_rank": 1,
            "code": "RISK_REWARD_VALID",
            "source_component": "reward_risk",
            "severity": "info",
            "detail": "Initial reward-to-risk passes the configured minimum.",
        },
    )


def _predictor_run(**changes: object) -> dict[str, object]:
    config = load_strategy_config()
    row: dict[str, object] = {
        "run_id": 42,
        "evaluation_time": datetime(2026, 8, 31, 0, 0, tzinfo=timezone.utc),
        **config.run_metadata(),
    }
    row.update(changes)
    return row


def test_renderer_contract_and_advisory_output_are_stable() -> None:
    result = render_recommendation(
        _recommendation(),
        _reason_rows(),
        predictor_run=_predictor_run(),
        strategy_config=load_strategy_config(),
    )

    assert isinstance(result, RecommendationRendererResult)
    assert result.feature_id == RECOMMENDATION_RENDERER_FEATURE_ID
    assert result.renderer_version == RECOMMENDATION_RENDERER_VERSION
    assert result.media_type == RECOMMENDATION_RENDERER_MEDIA_TYPE
    assert result.complete is True
    assert [reason.reason_rank for reason in result.reasons] == [0, 1, 2]
    assert result.recommendation.suggested_exposure_fraction_nav == Decimal("0.051")
    assert result.body.isascii()
    assert result.body.startswith("BTC SWING SIGNAL\n\n")
    assert "Regime: BULL (72)" in result.body
    assert "Setup: BULLISH RESET" in result.body
    assert "ACTION:\nENTER INITIAL TRANCHE" in result.body
    assert "Entry Zone:\n98,500 - 101,000" in result.body
    assert "Risk:\n0.5% NAV" in result.body
    assert "Suggested Exposure:\n5.1% NAV" in result.body
    assert "R/R:\n3.2R" in result.body
    assert "Add:         86.3" in result.body
    assert (
        "[+] Initial reward-to-risk passes the configured minimum. "
        "[RISK_REWARD_VALID]"
    ) in result.body
    assert "[!] The macro backdrop is weak. [MACRO_WEAK]" in result.body
    assert "ACTION:\nENTER INITIAL TRANCHE\n\nBLOCKERS:\nNone recorded." in result.body
    assert "[ ] Add Score >= 85" in result.body
    assert "[ ] No average down" in result.body
    assert "[ ] Aggregate risk-at-stop <= 1% NAV" in result.body


def test_renderer_persists_every_source_and_replays_exactly() -> None:
    result = render_recommendation(
        _recommendation(),
        _reason_rows(),
        predictor_run=_predictor_run(),
        strategy_config=load_strategy_config(),
    )
    record = result.as_record()
    restored = recommendation_renderer_from_record(record)

    assert restored == result
    assert restored.as_record() == record
    assert record["config_metadata"] == load_strategy_config().run_metadata()
    assert record["predictor_run"] == {
        "run_id": 42,
        "evaluation_time": "2026-08-31T00:00:00+00:00",
        **load_strategy_config().run_metadata(),
    }
    assert record["recommendation"]["evaluation_time"] == "2026-08-31T00:00:00+00:00"
    assert record["recommendation"]["risk_fraction_nav"] == "0.005"
    assert [reason["code"] for reason in record["reasons"]] == [
        "MACRO_WEAK",
        "RISK_REWARD_VALID",
        "TREND_12W_POSITIVE",
    ]
    assert record["add_condition_policy"] == {
        "minimum_add_score": "85.0",
        "require_profitable_position": True,
        "require_stop_improvement": True,
        "no_average_down": True,
        "maximum_risk_fraction_nav": "0.01",
    }


def test_renderer_accepts_live_reason_objects_in_their_existing_order() -> None:
    reasons = (
        RecommendationReasonCode(
            code="RISK_REWARD_VALID",
            source_component="reward_risk",
            severity="info",
            detail="Initial reward-to-risk passes the configured minimum.",
        ),
        RecommendationReasonCode(
            code="NO_CHASE_VIOLATION",
            source_component="no_chase",
            severity="veto",
            detail="Price moved beyond the intended entry zone.",
        ),
    )

    result = render_recommendation(
        _recommendation(action="NO_TRADE"),
        reasons,
        predictor_run=_predictor_run(),
        strategy_config=load_strategy_config(),
    )

    assert "ACTION:\nNO TRADE" in result.body
    assert "BLOCKERS:\n[X] Price moved beyond the intended entry zone." in result.body
    assert [reason.code for reason in result.reasons] == [
        "RISK_REWARD_VALID",
        "NO_CHASE_VIOLATION",
    ]


@pytest.mark.parametrize(
    ("action", "label"),
    (
        ("NO_TRADE", "NO TRADE"),
        ("WATCH", "WATCH"),
        ("ENTER", "ENTER INITIAL TRANCHE"),
        ("HOLD", "HOLD"),
        ("ADD", "ADD TRANCHE"),
        ("TRIM", "TRIM POSITION"),
        ("EXIT", "EXIT POSITION"),
    ),
)
def test_every_persisted_action_has_an_unambiguous_label(
    action: str,
    label: str,
) -> None:
    result = render_recommendation(
        _recommendation(action=action),
        _reason_rows(),
        predictor_run=_predictor_run(),
        strategy_config=load_strategy_config(),
    )

    assert f"ACTION:\n{label}\n" in result.body


def test_optional_trade_geometry_is_reported_as_unavailable_not_invented() -> None:
    result = render_recommendation(
        _recommendation(
            setup=None,
            hold_score=None,
            add_score=None,
            entry_zone_lower=None,
            entry_zone_upper=None,
            invalidation_level=None,
            initial_stop=None,
            rr_ratio=None,
            risk_fraction_nav=None,
            risk_amount=None,
            suggested_notional=None,
            action="WATCH",
        ),
        _reason_rows(),
        predictor_run=_predictor_run(),
        strategy_config=load_strategy_config(),
    )

    assert "Setup: N/A" in result.body
    assert "Entry Zone:\nN/A" in result.body
    assert "Risk:\nN/A" in result.body
    assert "Suggested Exposure:\nN/A" in result.body
    assert "Hold:        N/A" in result.body
    assert "Add:         N/A" in result.body


def test_tradable_action_requires_complete_geometry_and_direction() -> None:
    with pytest.raises(ValueError, match="complete trade geometry"):
        render_recommendation(
            _recommendation(initial_stop=None),
            _reason_rows(),
            predictor_run=_predictor_run(),
            strategy_config=load_strategy_config(),
        )

    with pytest.raises(ValueError, match="long or short direction"):
        render_recommendation(
            _recommendation(direction="flat"),
            _reason_rows(),
            predictor_run=_predictor_run(),
            strategy_config=load_strategy_config(),
        )


def test_renderer_fails_on_incomplete_or_misattributed_explanations() -> None:
    with pytest.raises(ValueError, match="at least one explanation"):
        render_recommendation(
            _recommendation(),
            (),
            predictor_run=_predictor_run(),
            strategy_config=load_strategy_config(),
        )

    wrong_id = [dict(reason) for reason in _reason_rows()]
    wrong_id[0]["recommendation_id"] = 999
    with pytest.raises(ValueError, match="different recommendation"):
        render_recommendation(
            _recommendation(),
            wrong_id,
            predictor_run=_predictor_run(),
            strategy_config=load_strategy_config(),
        )

    duplicate_rank = [dict(reason) for reason in _reason_rows()]
    duplicate_rank[0]["reason_rank"] = 1
    with pytest.raises(ValueError, match="unique and contiguous"):
        render_recommendation(
            _recommendation(),
            duplicate_rank,
            predictor_run=_predictor_run(),
            strategy_config=load_strategy_config(),
        )


def test_renderer_rejects_invalid_recommendation_geometry_and_time() -> None:
    with pytest.raises(ValueError, match="both lower and upper"):
        render_recommendation(
            _recommendation(entry_zone_upper=None),
            _reason_rows(),
            predictor_run=_predictor_run(),
            strategy_config=load_strategy_config(),
        )

    with pytest.raises(ValueError, match="UTC"):
        render_recommendation(
            _recommendation(evaluation_time=datetime(2026, 8, 31)),
            _reason_rows(),
            predictor_run=_predictor_run(),
            strategy_config=load_strategy_config(),
        )

    with pytest.raises(ValueError, match="between 0 and 100"):
        render_recommendation(
            _recommendation(entry_conviction=Decimal("101")),
            _reason_rows(),
            predictor_run=_predictor_run(),
            strategy_config=load_strategy_config(),
        )


def test_restore_rejects_body_and_config_drift() -> None:
    record = render_recommendation(
        _recommendation(),
        _reason_rows(),
        predictor_run=_predictor_run(),
        strategy_config=load_strategy_config(),
    ).as_record()
    changed_body = deepcopy(record)
    changed_body["body"] = str(changed_body["body"]).replace(
        "ENTER INITIAL TRANCHE",
        "WATCH",
    )
    with pytest.raises(ValueError, match="body does not match"):
        recommendation_renderer_from_record(changed_body)

    changed_config = deepcopy(record)
    changed_config["config_metadata"]["parameter_set_id"] = "other"
    with pytest.raises(ValueError, match="config identity"):
        recommendation_renderer_from_record(changed_config)


def test_reason_detail_cannot_inject_new_advisory_lines() -> None:
    reasons = [dict(reason) for reason in _reason_rows()]
    reasons[0]["detail"] = "Warning.\nACTION:\nENTER"

    with pytest.raises(ValueError, match="single-line"):
        render_recommendation(
            _recommendation(),
            reasons,
            predictor_run=_predictor_run(),
            strategy_config=load_strategy_config(),
        )


def test_renderer_rejects_run_and_config_provenance_mismatches() -> None:
    with pytest.raises(ValueError, match="different predictor run"):
        render_recommendation(
            _recommendation(),
            _reason_rows(),
            predictor_run=_predictor_run(run_id=43),
            strategy_config=load_strategy_config(),
        )

    with pytest.raises(ValueError, match="evaluation_time"):
        render_recommendation(
            _recommendation(),
            _reason_rows(),
            predictor_run=_predictor_run(
                evaluation_time=datetime(2026, 8, 30, tzinfo=timezone.utc),
            ),
            strategy_config=load_strategy_config(),
        )

    with pytest.raises(ValueError, match="config identity"):
        render_recommendation(
            _recommendation(),
            _reason_rows(),
            predictor_run=_predictor_run(parameter_set_id="other"),
            strategy_config=load_strategy_config(),
        )


def test_entry_or_add_cannot_be_rendered_with_a_veto() -> None:
    veto = RecommendationReasonCode(
        code="DATA_QUALITY_FAIL",
        source_component="data_quality",
        severity="veto",
        detail="Critical source data failed quality checks.",
    )

    with pytest.raises(ValueError, match="ENTER cannot be rendered with veto"):
        render_recommendation(
            _recommendation(),
            (veto,),
            predictor_run=_predictor_run(),
            strategy_config=load_strategy_config(),
        )
