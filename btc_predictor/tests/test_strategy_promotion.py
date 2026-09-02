"""BTC-193: controlled, manual strategy promotion."""

import json
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from btc_predictor.backtest import (
    ENTRY_CONVICTION,
    FoldStrategy,
    ThresholdParameterSet,
    run_threshold_sweep,
    run_walk_forward,
    threshold_sweep_spec,
    walk_forward_plan,
)
from btc_predictor.config.strategy import ConfigIdentity
from btc_predictor.research import (
    AWAITING_MANUAL_APPROVAL,
    MANUAL_HUMAN_APPROVAL,
    PROMOTED,
    PROMOTION_APPROVE,
    PROMOTION_REJECT,
    PROMOTION_REJECTED,
    STRATEGY_PROMOTION_FEATURE_ID,
    STRATEGY_PROMOTION_POLICY_VERSION,
    ComponentAblationReport,
    FeatureMatrixProvenance,
    StrategyPromotionError,
    compare_backtest_strategies,
    compare_paper_trade_strategies,
    finalize_strategy_promotion,
    prepare_strategy_promotion,
    record_manual_promotion_decision,
    restore_strategy_promotion_packet,
    restore_strategy_promotion_record,
    run_component_ablation,
    run_predictor_diagnostics,
)
from btc_predictor.tests.test_backtest_walk_forward import BARS, NAV
from btc_predictor.tests.test_component_ablation import (
    evaluator as ablation_evaluator,
)
from btc_predictor.tests.test_component_ablation import spec as ablation_spec
from btc_predictor.tests.test_predictor_diagnostics import (
    _dataset as diagnostics_dataset,
)
from btc_predictor.tests.test_predictor_diagnostics import _spec as diagnostics_spec
from btc_predictor.tests.test_strategy_comparison import (
    _paper_dataset,
    _result,
)


CURRENT = ConfigIdentity(
    config_version="config-for-swing_v1.2-current",
    strategy_version="swing_v1.2",
    parameter_set_id="current",
)
CANDIDATE = ConfigIdentity(
    config_version="config-for-swing_v1.2-candidate",
    strategy_version="swing_v1.2",
    parameter_set_id="candidate",
)
DECIDED_AT = datetime(2026, 9, 2, 9, 30, tzinfo=UTC)


def _metadata(identity: ConfigIdentity) -> dict[str, str]:
    return {
        "config_version": identity.config_version,
        "strategy_version": identity.strategy_version,
        "parameter_set_id": identity.parameter_set_id,
    }


def _candidate_config(parameter_set_id: str | None = None):
    from btc_predictor.config import load_strategy_config

    config = load_strategy_config()
    return replace(
        config,
        identity=replace(
            CANDIDATE,
            parameter_set_id=(
                CANDIDATE.parameter_set_id
                if parameter_set_id is None
                else parameter_set_id
            ),
        ),
    )


def _walk_forward(config=None):
    selected = _candidate_config() if config is None else config

    def factory(_window):
        return FoldStrategy(
            strategy=lambda _context: None,
            strategy_id=f"promotion-{selected.identity.parameter_set_id}",
        )

    return run_walk_forward(
        BARS,
        strategy_factory=factory,
        plan=walk_forward_plan(
            selected,
            train_periods=3,
            test_periods=2,
            step_periods=2,
        ),
        starting_nav=NAV,
        strategy_config=selected,
    )


def _robustness_sweep():
    spec = threshold_sweep_spec(
        parameter=ENTRY_CONVICTION,
        candidate_values=(75, 80),
        baseline_value=80,
        parameter_paths=("entry_thresholds.valid_trade_min",),
        base_config_metadata=_metadata(CANDIDATE),
    )

    def evaluate(parameter_set: ThresholdParameterSet):
        return _walk_forward(_candidate_config(parameter_set.parameter_set_id))

    return run_threshold_sweep(spec, evaluator=evaluate)


def _diagnostics():
    features, targets, contexts = diagnostics_dataset()
    definition = replace(
        features.definition,
        provenance=FeatureMatrixProvenance(
            config_version=CANDIDATE.config_version,
            strategy_version=CANDIDATE.strategy_version,
            parameter_set_id=CANDIDATE.parameter_set_id,
        ),
    )
    features = replace(features, definition=definition)
    return run_predictor_diagnostics(
        features, targets, contexts, spec=diagnostics_spec(bootstrap_resamples=20)
    )


def _ablation() -> ComponentAblationReport:
    # Reuse the BTC-189 parity evaluator, but bind its base identity to the
    # candidate so BTC-193 can prove the research belongs to this promotion.
    declared = ablation_spec(base_config_metadata=_metadata(CANDIDATE))
    return run_component_ablation(declared, evaluator=ablation_evaluator())


@pytest.fixture(scope="module")
def evidence():
    historical = compare_backtest_strategies(
        (
            _result("swing_v1.2", "candidate", exit_day=3),
            _result("swing_v1.2", "current", exit_day=2),
        ),
        baseline_strategy_version="swing_v1.2",
        baseline_parameter_set_id="current",
    )
    paper = compare_paper_trade_strategies(
        (
            _paper_dataset("swing_v1.2", "candidate", exit_price="110000"),
            _paper_dataset("swing_v1.2", "current", exit_price="105000"),
        ),
        comparison_scope_id="promotion-shadow-campaign",
        baseline_strategy_version="swing_v1.2",
        baseline_parameter_set_id="current",
    )
    return {
        "current_production": CURRENT,
        "candidate": CANDIDATE,
        "paper_trade_comparison": paper,
        "predictor_diagnostics": _diagnostics(),
        "component_ablation": _ablation(),
        "historical_backtest_comparison": historical,
        "walk_forward_validation": _walk_forward(),
        "robustness_sweeps": (_robustness_sweep(),),
    }


def _packet(evidence):
    return prepare_strategy_promotion(**evidence)


def test_complete_evidence_chain_stops_at_manual_approval(evidence) -> None:
    packet = _packet(evidence)

    assert packet.feature_id == STRATEGY_PROMOTION_FEATURE_ID
    assert packet.policy_version == STRATEGY_PROMOTION_POLICY_VERSION
    assert packet.status == AWAITING_MANUAL_APPROVAL
    assert packet.current_production == CURRENT
    assert packet.candidate == CANDIDATE
    assert "STRATEGY_PROMOTION_EVIDENCE_CHAIN_COMPLETE" in packet.reason_codes
    assert "STRATEGY_PROMOTION_NO_AUTOMATIC_CONFIG_MUTATION" in packet.reason_codes


def test_evidence_input_order_is_deterministic(evidence) -> None:
    first = _packet(evidence)
    duplicate_parameter = replace(
        evidence["robustness_sweeps"][0],
        report_id="different-id",
    )

    assert first == _packet(evidence)
    with pytest.raises(StrategyPromotionError, match="one robustness sweep"):
        prepare_strategy_promotion(
            **{
                **evidence,
                "robustness_sweeps": (
                    evidence["robustness_sweeps"][0],
                    duplicate_parameter,
                ),
            }
        )


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("robustness_sweeps", (), "at least one"),
        ("candidate", CURRENT, "new versioned"),
    ],
)
def test_incomplete_or_unversioned_requests_fail_closed(
    evidence, field, replacement, message
) -> None:
    with pytest.raises(StrategyPromotionError, match=message):
        prepare_strategy_promotion(**{**evidence, field: replacement})


def test_evidence_must_bind_to_exact_candidate_identity(evidence) -> None:
    wrong_candidate = replace(CANDIDATE, config_version="unvalidated-config")

    with pytest.raises(StrategyPromotionError, match="candidate config"):
        prepare_strategy_promotion(
            **{**evidence, "candidate": wrong_candidate}
        )


def test_historical_and_paper_stages_cannot_be_swapped(evidence) -> None:
    with pytest.raises(StrategyPromotionError, match="must use PAPER_TRADE"):
        prepare_strategy_promotion(
            **{
                **evidence,
                "paper_trade_comparison": evidence[
                    "historical_backtest_comparison"
                ],
            }
        )


def test_approval_is_explicit_manual_and_records_new_production(evidence) -> None:
    packet = _packet(evidence)
    decision = record_manual_promotion_decision(
        packet,
        decision=PROMOTION_APPROVE,
        approver_id="risk-committee-chair",
        decided_at=DECIDED_AT,
        rationale="Reviewed the complete evidence packet and approved release.",
    )
    result = finalize_strategy_promotion(packet, decision)

    assert decision.approval_method == MANUAL_HUMAN_APPROVAL
    assert result.status == PROMOTED
    assert result.previous_production == CURRENT
    assert result.resulting_production == CANDIDATE
    assert result.effective_at == DECIDED_AT
    assert result.config_mutation_performed is False


def test_manual_rejection_retains_current_production(evidence) -> None:
    packet = _packet(evidence)
    decision = record_manual_promotion_decision(
        packet,
        decision=PROMOTION_REJECT,
        approver_id="risk-committee-chair",
        decided_at=DECIDED_AT,
        rationale="Robustness evidence is not yet persuasive.",
    )
    result = finalize_strategy_promotion(packet, decision)

    assert result.status == PROMOTION_REJECTED
    assert result.resulting_production == CURRENT
    assert result.effective_at is None
    assert result.config_mutation_performed is False


def test_decision_cannot_be_reused_for_another_packet(evidence) -> None:
    packet = _packet(evidence)
    changed_packet = replace(packet, packet_id="another-packet")
    decision = record_manual_promotion_decision(
        packet,
        decision=PROMOTION_APPROVE,
        approver_id="risk-committee-chair",
        decided_at=DECIDED_AT,
        rationale="Approved.",
    )

    with pytest.raises(
        StrategyPromotionError, match="evidence does not match packet_id"
    ):
        finalize_strategy_promotion(changed_packet, decision)


def test_manual_decision_requires_utc_approver_and_rationale(evidence) -> None:
    packet = _packet(evidence)

    with pytest.raises(StrategyPromotionError, match="approver_id"):
        record_manual_promotion_decision(
            packet,
            decision=PROMOTION_APPROVE,
            approver_id="",
            decided_at=DECIDED_AT,
            rationale="Approved.",
        )
    with pytest.raises(StrategyPromotionError, match="timezone-aware UTC"):
        record_manual_promotion_decision(
            packet,
            decision=PROMOTION_APPROVE,
            approver_id="reviewer",
            decided_at=DECIDED_AT.replace(tzinfo=None),
            rationale="Approved.",
        )


def test_packet_and_final_record_round_trip_and_reject_tampering(evidence) -> None:
    packet = _packet(evidence)
    restored_packet = restore_strategy_promotion_packet(packet.as_record())
    decision = record_manual_promotion_decision(
        packet,
        decision=PROMOTION_APPROVE,
        approver_id="risk-committee-chair",
        decided_at=DECIDED_AT,
        rationale="Approved after review.",
    )
    result = finalize_strategy_promotion(packet, decision)
    record = result.as_record()

    assert restored_packet == packet
    assert restore_strategy_promotion_record(record) == result
    assert json.dumps(record, sort_keys=True) == json.dumps(
        result.as_record(), sort_keys=True
    )

    tampered = deepcopy(record)
    tampered["resulting_production"]["parameter_set_id"] = "unreviewed"
    with pytest.raises(StrategyPromotionError, match="reconstructed"):
        restore_strategy_promotion_record(tampered)
