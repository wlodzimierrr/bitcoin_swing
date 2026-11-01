"""RBT-005 core contract: the management ledger, the adapter, determinism and accounting.

One management row per daily decision instant with an open position, beside the
entry ledger's own row; the position's armed entry (K_entry and the BTC-145
size); the composition read from the entry half; the spec values against the
frozen spec; and the policy V7 section 5A.6 completeness guard with its
accounting against the bound inventory and spec. Synthetic deterministic
fixtures only.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from btc_predictor.features.regime import REGIME_CLASSIFICATION_LABELS
from btc_predictor.portfolio.state_machine import ADD, apply_position_event
from btc_predictor.quant.transforms import normal_cdf_score
from btc_predictor.research_backtest import completion_spec, entry_composer, management_composer
from btc_predictor.research_backtest.entry_composer import (
    AUTHORITY_INVENTORY_ROW,
    AUTHORITY_SPEC_ENTRY,
    AUTHORITY_SPEC_NAMED_LIMITATION,
    CAUSE_DECISION_PRICE_BAR_MISSING,
    COMPLETION_SPEC_SHA256,
    OUTCOME_ARM_ENTRY,
    REASON_POSITION_ALREADY_OPEN,
)
from btc_predictor.research_backtest.management_composer import (
    DATA_RISK_EXIT_REQUIRED,
    FLOW_SUPPORTIVE_MIN,
    MANAGEMENT_CAUSE_ACCOUNTING,
    MANAGEMENT_LEDGER_VERSION,
    MANAGEMENT_OUTCOMES,
    OUTCOME_EXIT,
    OUTCOME_HOLD,
    OUTCOME_STRUCTURALLY_UNEVALUABLE,
    OUTCOME_TRIM,
    REGIME_BEAR_LABELS,
    REGIME_SUPPORTIVE_LABELS,
    ManagementComposer,
    ManagementComposerError,
    accounted_cause,
)
from btc_predictor.research_backtest.replay_inputs import canonical_json_bytes
from btc_predictor.risk.tranches import calculate_tranche_size
from btc_predictor.tests.rbt004_composer_fixtures import OwnerCall
from btc_predictor.tests.rbt005_management_fixtures import (
    ARMED_AT,
    CONFIG,
    DAY,
    FILLED_AT,
    HOUR,
    TRAIL_AT,
    managed_run,
    management_market,
    natural_run,
    trail_add_interventions,
    trail_add_run,
    utc,
)

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = completion_spec.ARTIFACT_DIRECTORY
SPEC = json.loads((ARTIFACTS / completion_spec.SPEC_FILENAME).read_text(encoding="utf-8"))
INVENTORY = json.loads((ARTIFACTS / "rbt002_input_coverage_inventory_v1.json").read_text(encoding="utf-8"))
ENTRIES = {entry["input_id"]: entry for entry in SPEC["entries"]}
MISSING_HOUR = utc(2024, 4, 2, 23)


@pytest.fixture(scope="module")
def natural():
    return natural_run()


@pytest.fixture(scope="module")
def gapped():
    """The decision bar closing at 2024-04-03 00:00 is missing while the position is open."""

    return managed_run(management_market(end=utc(2024, 4, 8), missing_hours=(MISSING_HOUR,)), engine_end=utc(2024, 4, 5, 6))


# --- the ledger ------------------------------------------------------------------------------


def test_one_management_row_per_decision_instant_with_an_open_position(natural):
    entry_rows = natural.champion.entry.ledger
    armed = [row for row in entry_rows if row.outcome == OUTCOME_ARM_ENTRY]
    assert [row.decision_at for row in armed] == [ARMED_AT]
    open_instants = [row.decision_at for row in entry_rows if row.position_open]
    rows = natural.champion.ledger
    assert [row.decision_at for row in rows] == open_instants == [ARMED_AT + DAY * day for day in range(1, 14)]
    for row in rows:
        assert row.outcome in MANAGEMENT_OUTCOMES and row.reasons
        assert row.venue == "BITSTAMP"
        assert row.unaccounted == ()
    # the entry half keeps its own row at every instant: never an entry while open
    for row in entry_rows:
        if row.position_open:
            assert row.intent is None
            assert row.reasons == (REASON_POSITION_ALREADY_OPEN,) or row.outcome == "STRUCTURALLY_UNEVALUABLE"


def test_the_natural_position_is_held_and_trimmed_and_every_trim_executes(natural):
    rows = natural.rows()
    outcomes = {row.outcome for row in rows.values()}
    assert outcomes <= {OUTCOME_HOLD, OUTCOME_TRIM} and outcomes == {OUTCOME_HOLD, OUTCOME_TRIM}
    trims = [when for when, row in rows.items() if row.outcome == OUTCOME_TRIM]
    queued = [event.occurred_at for event in natural.events(event_type="INTENT", action="TRIM")]
    executed = [event for event in natural.events(event_type="TRIM_EXECUTION") if event.status == "EXECUTED"]
    assert queued == trims and len(executed) == len(trims)
    for row in rows.values():
        assert row.trail["reason_codes"] == ["TRAILING_STOP_HELD"] and row.trail["advanced"] is False
        assert row.add["outcome"] == "BLOCKED" and row.add["reasons"]
        if row.outcome == OUTCOME_HOLD:
            assert row.intent is None and row.reasons == ("NO_MANAGEMENT_ACTION",)
        else:
            assert row.intent["action"] == "TRIM" and row.intent["trim_signal"]["signal"] is True


def test_each_row_records_its_position_and_armed_entry(natural):
    armed_row = next(row for row in natural.champion.entry.ledger if row.outcome == OUTCOME_ARM_ENTRY)
    for row in natural.champion.ledger:
        assert row.position["entry_source_id"] == armed_row.intent["source_id"]
        assert row.position["entry_decision_at"] == ARMED_AT
        assert row.position["opened_at"] == FILLED_AT
        assert row.position["quantity"] > 0 and row.position["standing_stop"] is not None
        # K_entry for REGIME_INVALIDATION_PREDICATE is the armed row's persisted classification
        assert row.regime["entry_classification"] == armed_row.regime["classification"]


def test_the_armed_size_is_the_size_the_engine_filled(natural):
    (armed,) = natural.champion._armed.values()
    (fill,) = [event for event in natural.events(event_type="ENTRY_EXECUTION") if event.status == "EXECUTED"]
    entry_row = next(row for row in natural.champion.entry.ledger if row.outcome == OUTCOME_ARM_ENTRY)
    first = calculate_tranche_size(
        tranche_number=1,
        final_position_notional=armed.position_size.position_notional,
        entry_price=Decimal(entry_row.intent["initial_stop"]["entry_price"]),
        config=CONFIG,
        config_metadata=dict(CONFIG.run_metadata()),
    )
    # the engine's first tranche of the composer's BTC-145 size is the quantity it filled
    assert Decimal(fill.evidence["intent"]["requested_quantity"]) == first.allocation.quantity


def test_the_hold_score_reads_the_entry_composition(natural):
    instant = ARMED_AT + 2 * DAY
    item = natural.captured[instant]
    composition = item.decision.composition
    with recording_management("calculate_hold_score", "normal_cdf_score") as calls:
        natural.redecide(instant)
    (hold,) = calls["calculate_hold_score"]
    inputs = hold.args[0]
    assert inputs.trend_score == composition.trend_score
    assert inputs.flow_score == composition.flow.score and composition.flow.complete
    assert inputs.positioning_score == composition.positioning_score
    # STRUCTURE_SCORE_V1_2 carries no R/R weight: the standing stop gives the entry path's Structure
    assert inputs.structure_score == item.decision.row.components["structure"]
    z = composition.trend_z["TREND_Z_M12"]
    assert inputs.momentum_persistence_score == Decimal(str(normal_cdf_score(float(z))))
    assert [call.args[0] for call in calls["normal_cdf_score"]] == [float(z), float(composition.trend_z["TREND_Z_M4"])]


def test_the_trim_reads_the_prior_decision_instants_flow(natural):
    for instant, item in natural.captured.items():
        assert item.prior_flow is not None and item.prior_flow.feature_id == "FLOW_SCORE"
        previous = natural.captured.get(instant - DAY)
        if previous is not None:
            assert item.prior_flow is previous.decision.composition.flow
    with recording_management("trim_rules_from_results") as calls:
        natural.redecide(ARMED_AT + 3 * DAY)
    (trim,) = calls["trim_rules_from_results"]
    assert trim.kwargs["prior_flow"] is natural.captured[ARMED_AT + 3 * DAY].prior_flow
    assert trim.kwargs["current_flow"] is natural.captured[ARMED_AT + 3 * DAY].decision.composition.flow


def test_a_missing_decision_bar_while_open_gets_its_row_and_the_next_trim_still_evaluates(gapped):
    rows = gapped.rows()
    skipped = rows[MISSING_HOUR + HOUR]
    assert skipped.outcome == OUTCOME_STRUCTURALLY_UNEVALUABLE and skipped.reasons == (CAUSE_DECISION_PRICE_BAR_MISSING,)
    assert skipped.position["quantity"] > 0 and skipped.intent is None and skipped.unaccounted == ()
    assert skipped.unevaluable[0].component == "decision_instant"
    after = rows[skipped.decision_at + DAY]
    # the prior decision had no decision bar, so no prior flow; the trim owner still runs with None
    # (bound inventory: "None -> TRIM_INPUT_MISSING; complete False, the other triggers still evaluate")
    assert after.trim["evaluated"] is True and after.trim["complete"] is False
    assert "TRIM_INPUT_MISSING" in after.trim["reason_codes"]
    assert after.trim["prior_flow_causes"] == [CAUSE_DECISION_PRICE_BAR_MISSING]
    assert after.unaccounted == ()
    assert all(row.unaccounted == () for row in rows.values())


def test_a_missing_prior_flow_leaves_the_other_trim_triggers_to_the_owner(natural):
    """Review F2: with no prior flow, a Hold of 45 still trims on the Hold band."""

    instant = ARMED_AT + 1 * DAY
    item = natural.captured[instant]
    with intervening_management("calculate_hold_score", trend_score=Decimal("45"), flow_score=Decimal("45"), positioning_score=Decimal("45"),
                                structure_score=Decimal("45"), momentum_persistence_score=Decimal("45")):
        decision = ManagementComposer(natural.champion.entry).decide(
            item.decision, lifecycle=item.lifecycle, nav=item.nav, armed=item.armed, prior_flow=None
        )
    assert decision.row.hold["score"] > CONFIG.hold_thresholds.exit_below
    assert decision.row.outcome == OUTCOME_TRIM
    assert {"TRIM_INPUT_MISSING", "TRIM_HOLD_SCORE_BAND"} <= set(decision.row.trim["reason_codes"])
    assert decision.row.trim["prior_flow_causes"] == [CAUSE_DECISION_PRICE_BAR_MISSING]
    # the prior flow is the flow owner's own result with every input missing: no value improvised
    unavailable = decision.row.owner_reason_codes["trim_prior_flow_unavailable"]
    assert unavailable["feature_id"] == "FLOW_SCORE" and unavailable["complete"] is False
    assert decision.row.unaccounted == ()


# --- determinism and serialisation -----------------------------------------------------------


def test_the_ledger_is_canonical_and_names_both_halves(natural):
    data = natural.champion.ledger_bytes()
    parsed = json.loads(data)
    assert data == canonical_json_bytes(parsed)
    assert parsed["ledger_version"] == MANAGEMENT_LEDGER_VERSION
    assert parsed["completion_spec"] == {"version": "CHAMPION_COMPLETION_SPEC_V1", "sha256": COMPLETION_SPEC_SHA256}
    assert parsed["entry_ledger_sha256"] == natural.champion.entry.ledger_sha256()
    assert natural.champion.ledger_sha256() == hashlib.sha256(data).hexdigest()
    assert [row["decision_at"] for row in parsed["rows"]] == [row.decision_at.isoformat() for row in natural.champion.ledger]


RUNNER = """
from btc_predictor.tests.rbt005_management_fixtures import managed_run, management_market, utc
run = managed_run(management_market(end=utc(2024, 4, 6)), engine_end=utc(2024, 4, 3, 6))
print(run.champion.ledger_sha256())
"""


def test_the_ledger_digest_is_stable_across_hash_seeds_and_working_directories(tmp_path):
    script = tmp_path / "runner.py"
    script.write_text(RUNNER, encoding="utf-8")
    digests = set()
    for seed in ("0", "8675309"):
        environment = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(ROOT)}
        result = subprocess.run([sys.executable, str(script)], cwd=tmp_path, env=environment, capture_output=True, text=True, check=True, timeout=900)
        digests.add(result.stdout.strip())
    local = managed_run(management_market(end=utc(2024, 4, 6)), engine_end=utc(2024, 4, 3, 6))
    assert digests == {local.champion.ledger_sha256()}


# --- the decision API ------------------------------------------------------------------------


def test_decide_refuses_a_flat_book_a_missing_composition_and_reordering(natural):
    instant = ARMED_AT + 2 * DAY
    item = natural.captured[instant]
    fresh = ManagementComposer(natural.champion.entry)
    with pytest.raises(ManagementComposerError) as refused:
        fresh.decide(replace(item.decision, composition=None), lifecycle=item.lifecycle, nav=item.nav, armed=item.armed, prior_flow=item.prior_flow)
    assert refused.value.code == "INPUT_REFUSED"
    with pytest.raises(ManagementComposerError) as refused:
        fresh.decide(item.decision, lifecycle=replace(item.lifecycle, quantity=Decimal("0")), nav=item.nav, armed=item.armed, prior_flow=item.prior_flow)
    assert refused.value.code == "INPUT_REFUSED"
    decision = fresh.decide(item.decision, lifecycle=item.lifecycle, nav=item.nav, armed=item.armed, prior_flow=item.prior_flow)
    assert fresh.ledger == ()  # decide never writes
    fresh.record(decision)
    with pytest.raises(ManagementComposerError) as refused:
        fresh.decide(item.decision, lifecycle=item.lifecycle, nav=item.nav, armed=item.armed, prior_flow=item.prior_flow)
    assert refused.value.code == "DECISION_ORDER"
    # the same inputs compose the same row
    assert decision.row == natural.rows()[instant]


def test_the_composer_accepts_only_the_rbt004_entry_composer():
    with pytest.raises(ManagementComposerError):
        ManagementComposer(object())  # type: ignore[arg-type]


# --- exits: regime invalidation, data risk and the manual override -----------------------------


def test_regime_invalidation_needs_a_bear_band_now_and_none_at_entry(natural):
    instant = ARMED_AT + 1 * DAY
    item = natural.captured[instant]
    current = item.decision.composition.regime_classification
    assert current.complete and current.regime not in REGIME_BEAR_LABELS
    bear = replace(current, regime="MILD_BEAR")
    invalidated = natural.redecide(instant, regime_classification=bear)
    assert invalidated.row.outcome == OUTCOME_EXIT and invalidated.row.reasons == ("REGIME_INVALIDATION",)
    assert invalidated.intent.action == "EXIT" and invalidated.intent.exit_reason == "REGIME_INVALIDATION"
    assert invalidated.row.regime["invalidated"] is True
    # a position armed in a bear band is exempt (spec REGIME_INVALIDATION_PREDICATE)
    exempt = natural.redecide(instant, regime_classification=bear, armed=replace(item.armed, entry_regime="BEAR"))
    assert exempt.row.regime["invalidated"] is False and exempt.row.outcome != OUTCOME_EXIT
    # an unknown K_entry is never read as False
    unknown = natural.redecide(instant, regime_classification=bear, armed=replace(item.armed, entry_regime=None))
    assert unknown.row.regime["invalidated"] is None and unknown.row.outcome != OUTCOME_EXIT
    assert "EXIT_INPUT_MISSING" in unknown.row.exit_rules["reason_codes"] and unknown.row.unaccounted == ()


def test_a_hold_score_collapse_exits_at_the_owner_threshold(natural):
    instant = ARMED_AT + 1 * DAY
    with intervening_management("calculate_hold_score", trend_score=Decimal("20"), flow_score=Decimal("20"), positioning_score=Decimal("20"),
                                structure_score=Decimal("20"), momentum_persistence_score=Decimal("20")):
        collapsed = natural.redecide(instant)
    assert collapsed.row.hold["score"] < CONFIG.hold_thresholds.exit_below
    assert collapsed.row.outcome == OUTCOME_EXIT and collapsed.intent.exit_reason == "HOLD_SCORE_COLLAPSE"


def test_the_exit_reads_the_bar_extreme_no_data_risk_and_no_override(natural):
    instant = ARMED_AT + 1 * DAY
    item = natural.captured[instant]
    with recording_management("exit_rules_for_position") as calls:
        natural.redecide(instant)
    (call,) = calls["exit_rules_for_position"]
    assert call.kwargs["current_price"] == item.decision.composition.decision_bar.low
    assert call.kwargs["data_risk_exit_required"] is DATA_RISK_EXIT_REQUIRED is False
    assert call.kwargs["manual_research_override"] is None and call.kwargs["manual_override_reason"] is None
    assert call.kwargs["evaluated_at"] == instant and call.kwargs["hold_score"].feature_id == "HOLD_SCORE"
    assert call.kwargs["source_reason_codes"] == {"data_quality_gate": ()}


# --- spec values against the frozen spec -------------------------------------------------------


def test_the_spec_values_are_the_frozen_specs():
    assert "decision_greater_equal(F.score, 60)" in ENTRIES["FLOW_SUPPORTIVE_PREDICATE"]["rule"]
    assert FLOW_SUPPORTIVE_MIN == Decimal("60")
    assert "BULL or STRONG_BULL" in ENTRIES["REGIME_SUPPORTIVE_PREDICATE"]["rule"]
    assert set(REGIME_SUPPORTIVE_LABELS) == {"BULL", "STRONG_BULL"}
    assert str(list(REGIME_BEAR_LABELS)) in ENTRIES["REGIME_INVALIDATION_PREDICATE"]["rule"]
    assert set(REGIME_SUPPORTIVE_LABELS) | set(REGIME_BEAR_LABELS) <= set(REGIME_CLASSIFICATION_LABELS)
    assert ENTRIES["DATA_RISK_EXIT_PREDICATE"]["rule"].startswith("False at every exit evaluation") and DATA_RISK_EXIT_REQUIRED is False
    assert "100 * Phi(z), z = the TREND_Z_M12 value" in ENTRIES["MOMENTUM_PERSISTENCE_SCORE"]["rule"]
    assert "100 * Phi(z), z = the TREND_Z_M4 value" in ENTRIES["ADD_MOMENTUM_SCORE"]["rule"]


# --- the completeness guard and its accounting (policy V7 section 5A.6) ---------------------------


def _inventory_rows():
    rows: dict[str, list[dict]] = {}
    for row in INVENTORY["input_surface"]["rows"]:
        rows.setdefault(f"{row['owner']}.{row['name']}", []).append(row)
    return rows


# The one inventory citation by phrase rather than by the code itself: the row
# states the owner's behaviour for a missing buffer, and a test below shows the
# owner's code for it through the real owners.
PHRASE_CITATIONS = {"TRAILING_STOP_BUFFER_INCOMPLETE": "None -> no trail candidate"}


def test_every_management_accounted_cause_is_backed_by_a_bound_artifact():
    rows = _inventory_rows()
    limitations = {item["limitation_id"]: item["statement"] for item in SPEC["named_limitations"]}
    assert len(MANAGEMENT_CAUSE_ACCOUNTING) == 14
    for code, cause in MANAGEMENT_CAUSE_ACCOUNTING.items():
        if cause.authority == AUTHORITY_SPEC_ENTRY:
            assert cause.cause in ENTRIES[cause.reference]["accounted_causes"], code
        elif cause.authority == AUTHORITY_SPEC_NAMED_LIMITATION:
            # the limitation names the very code it accounts for
            assert cause.cause == code and code in limitations[cause.reference], code
        else:
            assert cause.authority == AUTHORITY_INVENTORY_ROW
            texts = [row.get("missing_behaviour") or "" for row in rows[cause.reference]]
            if code in PHRASE_CITATIONS:
                assert cause.cause in PHRASE_CITATIONS[code] and PHRASE_CITATIONS[code] in texts, code
            else:
                # the row names the very code it accounts for
                assert cause.cause == code and any(code in text for text in texts), code
    # review F5: a missing stop on an open position is accounted nowhere (it fails loud)
    assert accounted_cause("RISK_AT_STOP_INPUT_MISSING") is None
    # management first, then the entry composer's table
    assert accounted_cause("HOLD_SCORE_INPUT_MISSING") == MANAGEMENT_CAUSE_ACCOUNTING["HOLD_SCORE_INPUT_MISSING"]
    assert accounted_cause(CAUSE_DECISION_PRICE_BAR_MISSING) == entry_composer.accounted_cause(CAUSE_DECISION_PRICE_BAR_MISSING)


def test_every_management_spec_input_is_accounted():
    management_inputs = {
        "MOMENTUM_PERSISTENCE_SCORE", "ADD_MOMENTUM_SCORE", "NEW_STRUCTURE_SCORE", "NEW_STRUCTURAL_CONFIRMATION",
        "REGIME_SUPPORTIVE_PREDICATE", "FLOW_SUPPORTIVE_PREDICATE", "REGIME_INVALIDATION_PREDICATE",
    }
    for input_id in management_inputs:
        for cause in ENTRIES[input_id]["accounted_causes"]:
            assert accounted_cause(cause) is not None, cause
    # DATA_RISK_EXIT_PREDICATE is a constant: it has no missing-input cause
    assert ENTRIES["DATA_RISK_EXIT_PREDICATE"].get("accounted_causes", []) == []


def test_an_unaccounted_owner_code_is_reported(natural):
    instant = ARMED_AT + 1 * DAY
    real = management_composer.next_tranche_for_position

    def unknown(*args, **kwargs):
        result = real(*args, **kwargs)
        return replace(result, complete=False, allocation=None, reason_codes=("TRANCHE_SIZING_NOVEL_INPUT_MISSING",))

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(management_composer, "next_tranche_for_position", unknown)
        decision = natural.redecide(instant)
    assert decision.row.unaccounted == ("add_tranche:TRANCHE_SIZING_NOVEL_INPUT_MISSING",)
    assert decision.row.add["outcome"] == "NOT_EVALUATED"


def test_an_incomplete_result_with_no_accounted_code_is_reported(natural):
    instant = ARMED_AT + 1 * DAY
    real = management_composer.trail_stop_for_position

    def silent(*args, **kwargs):
        return replace(real(*args, **kwargs), complete=False, reason_codes=("TRAILING_STOP_SOMETHING_NEW",))

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(management_composer, "trail_stop_for_position", silent)
        decision = natural.redecide(instant)
    assert "trailing_stop:TRAILING_STOP_SOMETHING_NEW" in decision.row.unaccounted


def test_a_missing_stop_on_an_open_position_is_unaccounted(natural):
    """Review F5: the closed-lifecycle "fail closed" text does not account for an open position's missing stop."""

    real = management_composer.calculate_risk_at_stop

    def missing_stop(tranches, **kwargs):
        return real(tranches, **{**kwargs, "stop_price": None})

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(management_composer, "calculate_risk_at_stop", missing_stop)
        decision = natural.redecide(ARMED_AT + 1 * DAY)
    assert decision.row.owner_reason_codes["risk_at_stop_current"]["reason_codes"] == ["RISK_AT_STOP_INPUT_MISSING"]
    assert "risk_at_stop_current:RISK_AT_STOP_INPUT_MISSING" in decision.row.unaccounted


def test_a_missing_buffer_holds_the_trail_with_its_accounted_code():
    """The phrase citation: the inventory's "None -> no trail candidate", through the real owners."""

    run = trail_add_run()
    real = management_composer.volatility_buffer_for_invalidation

    def no_atr(levels, **kwargs):
        return real(levels, **{**kwargs, "atr": None})

    with trail_add_interventions(run.inputs), pytest.MonkeyPatch.context() as patch:
        patch.setattr(management_composer, "volatility_buffer_for_invalidation", no_atr)
        decision = run.redecide(TRAIL_AT)
    assert decision.row.owner_reason_codes["trailing_buffer"]["complete"] is False
    assert decision.row.trail["structure"] is not None and decision.row.trail["advanced"] is False
    assert decision.row.trail["reason_codes"] == ["TRAILING_STOP_BUFFER_INCOMPLETE"]
    assert decision.row.outcome != "TRAIL" and decision.row.unaccounted == ()


def test_composer_unaccounted_causes_are_collected(natural):
    assert natural.champion.unaccounted_causes() == ()


def test_an_exhausted_tranche_schedule_is_the_schedules_limit_not_a_missing_input(natural):
    instant = ARMED_AT + 1 * DAY
    item = natural.captured[instant]
    price = item.decision.composition.price
    lifecycle = item.lifecycle
    for offset in (2, 1):  # the two scheduled adds (40% / 35% / 25%), filled before t
        lifecycle = apply_position_event(
            lifecycle, event=ADD, event_time=instant - offset * HOUR, quantity=Decimal("0.01"), price=price,
            source_feature_id="RBT005_TEST_ADD", source_record_id=f"rbt005-test-add-{offset}",
        )
        assert lifecycle.accepted
    assert len(lifecycle.tranches) == len(CONFIG.risk.tranche_schedule) == 3
    decision = ManagementComposer(natural.champion.entry).decide(
        item.decision, lifecycle=lifecycle, nav=item.nav, armed=item.armed, prior_flow=item.prior_flow
    )
    assert decision.row.add["outcome"] == "NOT_EVALUATED"
    assert decision.row.add["reasons"] == ["ADD_NO_FURTHER_TRANCHE", "TRANCHE_SIZING_SCHEDULE_EXHAUSTED"]
    # owner review ruling 7: the spec named limitation, not the schedule's "never missing" inventory row
    cause = accounted_cause("TRANCHE_SIZING_SCHEDULE_EXHAUSTED")
    assert (cause.authority, cause.reference) == (AUTHORITY_SPEC_NAMED_LIMITATION, "TRANCHE_SCHEDULE_EXHAUSTED")
    assert decision.row.unaccounted == ()


# --- helpers -------------------------------------------------------------------------------


def recording_management(*names):
    """Record each named owner call the management composer makes (the real owner runs)."""

    @contextmanager
    def context():
        calls = {name: [] for name in names}
        with pytest.MonkeyPatch.context() as patch:
            for name in names:
                real = getattr(management_composer, name)

                def wrapper(*args, _real=real, _name=name, **kwargs):
                    result = _real(*args, **kwargs)
                    calls[_name].append(OwnerCall(args, kwargs, result))
                    return result

                patch.setattr(management_composer, name, wrapper)
            yield calls

    return context()


def intervening_management(name, **changes):
    """Replace fields of the named owner's first positional input (the real owner runs)."""

    @contextmanager
    def context():
        real = getattr(management_composer, name)

        def wrapper(inputs, *args, **kwargs):
            return real(replace(inputs, **changes), *args, **kwargs)

        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(management_composer, name, wrapper)
            yield

    return context()
