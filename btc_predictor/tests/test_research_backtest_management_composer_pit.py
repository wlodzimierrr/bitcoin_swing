"""RBT-005 point-in-time property (policy V7 section 4; the RBT-004 criterion, applied again).

A management decision reads only the BacktestContext and replay inputs whose
modelled availability is at or before its instant. Every input family is
perturbed or extended after a cutoff with RBT-004's ``perturb_after`` (later
bars, ETF revisions, late derivative rows, later liquidation days, ...), and the
composed champion is replayed through BTC-180: every management row, entry row
and engine event up to the cutoff is byte-identical. The converse control shows
the property is not vacuous: rows after the cutoff do change.
"""

from __future__ import annotations

import pytest

from btc_predictor.tests.rbt005_management_fixtures import (
    HOUR,
    TRAIL_AT,
    Interventions,
    add_score_lifted,
    higher_low_at,
    managed_run,
    management_market,
    natural_run,
    trail_add_run,
    utc,
)
from btc_predictor.tests.test_research_backtest_entry_composer_pit import perturb_after

CUTOFF = utc(2024, 4, 6)
SEEDS = (0, 1)


def _upto(run, instant):
    management = [row.as_record() for row in run.champion.ledger if row.decision_at <= instant]
    entry = [row.as_record() for row in run.champion.entry.ledger if row.decision_at <= instant]
    events = [event.as_record() for event in run.result.events if event.occurred_at <= instant]
    return management, entry, events


@pytest.fixture(scope="module", params=SEEDS)
def perturbed(request):
    seed = request.param
    run = managed_run(
        management_market(end=utc(2024, 4, 14)), engine_end=utc(2024, 4, 9, 6),
        modify=lambda built: perturb_after(built, CUTOFF, seed),
    )
    return seed, run


def test_management_up_to_t_ignores_everything_after_t(perturbed):
    _, run = perturbed
    baseline = natural_run()
    management, entry, events = _upto(baseline, CUTOFF)
    assert management and entry and events
    assert _upto(run, CUTOFF) == (management, entry, events)
    # not vacuous: the perturbed future does change what happens after the cutoff
    def after(replay):
        return (
            [row.as_record() for row in replay.champion.ledger if CUTOFF < row.decision_at <= utc(2024, 4, 9)],
            [event.as_record() for event in replay.result.events if CUTOFF < event.occurred_at <= utc(2024, 4, 9)],
        )

    assert after(run) != after(baseline)


def test_a_pending_add_is_composed_from_its_instant_alone():
    """The trail-and-add decision and its ADD requirements do not read past TRAIL_AT."""

    baseline = trail_add_run()
    market = management_market(end=utc(2024, 4, 8))
    inputs = market.build()

    def setup(interventions: Interventions) -> None:
        higher_low_at(interventions, inputs, {TRAIL_AT})
        add_score_lifted(interventions, {TRAIL_AT})

    run = managed_run(market, engine_end=utc(2024, 4, 3, 6), setup=setup, modify=lambda built: perturb_after(built, TRAIL_AT, 0))
    management, entry, events = _upto(baseline, TRAIL_AT)
    assert _upto(run, TRAIL_AT) == (management, entry, events)
    assert run.rows()[TRAIL_AT].add["intent"] == baseline.rows()[TRAIL_AT].add["intent"] is not None


def test_the_adds_risk_recheck_reads_nothing_after_its_callback():
    """Owner review ruling 4: the re-check at TRAIL_AT + 1h reads only what is available then."""

    baseline = trail_add_run()
    market = management_market(end=utc(2024, 4, 8))
    inputs = market.build()
    callback = TRAIL_AT + HOUR

    def setup(interventions: Interventions) -> None:
        higher_low_at(interventions, inputs, {TRAIL_AT})
        add_score_lifted(interventions, {TRAIL_AT})

    run = managed_run(market, engine_end=callback + 2 * HOUR, setup=setup, modify=lambda built: perturb_after(built, callback, 0))
    (followup,) = run.champion.add_followups
    assert followup.resolved_at == callback and followup.risk_recheck is not None
    assert followup.as_record() == baseline.champion.add_followups[0].as_record()
