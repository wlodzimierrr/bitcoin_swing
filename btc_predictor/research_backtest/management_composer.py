"""RBT-005 ``COMPOSE_CHAMPION_POSITION_MANAGEMENT_V1``: the in-position half of the champion.

The EPIC Y research champion ``swing_v1.2+completion_v1`` (policy V7 section 6)
is composed by two halves. The RBT-004 entry composer decides while flat; this
composer decides while a position is open. At each daily decision instant with
an open position it emits at most one of ``EXIT``, ``TRIM`` or ``TRAIL``, or
none, through the existing owners; an ``ADD`` follows its ``TRAIL`` (owner
ruling 1 below). It adds no formula. Every number comes from an owner call or
from the spec's ``declared_arithmetic``, and every owner it calls directly is a
census root, a classified input source or a classified constructor
(:mod:`btc_predictor.research_backtest.composer_boundary`).

**One composition per instant.** The entry composer's decision run at ``t``
already composed every shared input: Trend, Flow, Positioning, the uniform
z-scores, the smoothed regime classification, the Rulebook 24 flags, the
data-quality failures, the ATR and the level clusters. Its
:class:`~btc_predictor.research_backtest.entry_composer.EntryComposition`
hands them over; nothing is composed twice. The entry ledger keeps its row for
every instant (``NO_TRADE / POSITION_ALREADY_OPEN`` or
``STRUCTURALLY_UNEVALUABLE`` while open); this composer's ledger adds one row
per decision instant with an open position.

**Composition order at t** (Rulebook 20-24 and 26; spec section 3):

1. *Hold* (``calculate_hold_score``): Trend, Flow and Positioning from the
   composition; Structure is the entry path's Structure Score at ``P_t``
   (:func:`~btc_predictor.research_backtest.entry_composer.structure_score_at`)
   under the standing stop; ``MOMENTUM_PERSISTENCE_SCORE = 100 * Phi(TREND_Z_M12)``.
2. *Exit* (``exit_rules_for_position``): the decision bar's low as the
   direction-appropriate extreme, ``REGIME_INVALIDATION_PREDICATE`` against
   ``K_entry`` from the position's ``ARM_ENTRY`` ledger row,
   ``DATA_RISK_EXIT_PREDICATE = False``, and the manual research override never
   asserted (``None``, the inventory's replay value).
3. *Trim* (``trim_rules_from_results``): the prior decision instant's
   ``FlowScoreResult`` as the prior flow. When that instant had no decision bar
   no flow was composed for it; the trim owner takes a ``FlowScoreResult`` and
   maps an incomplete one to ``prior_flow_score = None`` ->
   ``TRIM_INPUT_MISSING`` with its other triggers still evaluated (the bound
   inventory rows), so the composer passes the flow owner's own result with
   every input missing: no value is improvised.
4. *Trail* (``trail_stop_for_position``): the confirmed higher low ``C_t`` from
   the one BTC-122 producer Setup C also reads
   (:func:`~btc_predictor.research_backtest.entry_composer.latest_higher_low`),
   and the BTC-141 buffer of a structure with no zone (ATR only).
5. *Add*, evaluated on the lifecycle before this instant's stop move (spec
   ``NEW_STRUCTURAL_CONFIRMATION``): ``ADD_MOMENTUM_SCORE``,
   ``NEW_STRUCTURE_SCORE``, the BTC-153 risk improvement, the projected post-add
   risk at the raised stop, the predicates, then ``add_requirements_from_results``,
   the data-quality gate and Rulebook 24 NO ADDING (policy V7 section 7).

**Owner composition rulings applied (2026-11-01, recorded in the RBT-005 block):**
- the add is evaluated before the stop moves; the ``TRAIL`` is emitted at t and
  the ``ADD``, carrying the requirements evaluated at t, at the first engine
  callback after the raised stop is installed. If the trail was not applied,
  the position closed or changed (any accepted transition but the ADD's own
  trail), or that callback is itself a decision instant, the ``ADD`` is dropped
  and the reason recorded;
- one intent per decision, ``EXIT`` > ``TRIM`` > ``TRAIL``/``ADD``; an add that
  would otherwise go ahead is recorded as suppressed, and a deferred trail does
  not consume its higher low;
- the three unmodelled add and reduce rules (spec limitation
  ``UNMODELLED_ADD_AND_REDUCE_RULES``) are recorded, not enforced.

**Owner review rulings applied (2026-11-01, after the independent review):**
- ruling 4: at the callback that emits the ``ADD``, its projected risk at the
  stop is computed again with the same owners at that callback's closed bar,
  installed stop and NAV; over the ceiling, or incomplete, the ``ADD`` is
  dropped with its reason. The frozen engine fills at the next bar's open, so a
  gap at that open stays a recorded limitation;
- ruling 6: an unknown STRESS or EUPHORIA blocks the add, and
  ``ADD_SUPERSEDED_BY_DECISION`` stands (both ratified);
- ruling 7: an exhausted tranche schedule is the spec named limitation
  ``TRANCHE_SCHEDULE_EXHAUSTED``.

**Design decisions (for the review).**
- *Rulebook 24 NO ADDING* reads each flag as the hard veto does: STRESS through
  the V4 mapping, CROWDING as ``SEVERE_CROWDING_STATE`` and EUPHORIA through the
  same V4 mapping (``flagged`` when only its DISCRETIONARY input is missing).
  An active flag records ``RULEBOOK_24_NO_ADDING_ENFORCED``; an unknown flag
  blocks the add too (fail closed, as BTC-154 and the hard veto do) and records
  ``RULEBOOK_24_FLAG_STATE_UNKNOWN``.
- *Hold Structure.* STRUCTURE_SCORE_V1_2 carries no R/R weight, so the score at
  ``P_t`` does not depend on the stop the owner requires; the standing stop is
  passed, and ``NEW_STRUCTURE_SCORE`` passes the raised stop as the spec says.
- *Position size.* The BTC-145 size is recomputed at the ``ARM_ENTRY``
  decision exactly as the engine sizes the entry (``calculate_risk_budget`` on
  the decision bar's NAV, then ``initial_position_size_for_trade``), and the
  projected add tranche is priced at ``P_t``, as the entry stop is.
- *An exhausted tranche schedule* is the frozen schedule's own limit, not a
  missing input: it is accounted to the spec named limitation (ruling 7). A
  missing stop on an open position is accounted nowhere: it fails loud.

Nothing is zero-filled. Every incomplete owner result and every missing-input
code maps to an accounted cause (:data:`MANAGEMENT_CAUSE_ACCOUNTING`, then the
entry composer's table) in the reviewed inventory or the spec; an unaccounted
one is recorded on its row, and the RBT-005 tests fail on it (policy V7
section 5A.6).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from btc_predictor.backtest.engine import (
    ADD_ACTION,
    EXIT_ACTION,
    TRAIL_ACTION,
    TRIM_ACTION,
    BacktestContext,
    BacktestIntent,
)
from btc_predictor.features.add import AddScoreInput, calculate_add_score, risk_improvement_component_score
from btc_predictor.features.flow import FlowScoreInput, calculate_flow_score
from btc_predictor.features.hold import HoldScoreInput, calculate_hold_score
from btc_predictor.portfolio.state_machine import ADD, ENTER, STOP_MOVE
from btc_predictor.quant.comparisons import decision_greater_equal
from btc_predictor.quant.transforms import normal_cdf_score
from btc_predictor.research_backtest.completion_spec import CHAMPION_BASE_IDENTITY, RESEARCH_STRATEGY_ID, SPEC_VERSION
from btc_predictor.research_backtest.entry_composer import (
    AUTHORITY_INVENTORY_ROW,
    AUTHORITY_SPEC_ENTRY,
    AUTHORITY_SPEC_NAMED_LIMITATION,
    CAUSE_DECISION_PRICE_BAR_MISSING,
    COMPLETION_SPEC_SHA256,
    AccountedCause,
    EntryComposer,
    EntryDecision,
    accounted_cause as entry_accounted_cause,
    is_daily_decision_instant,
    latest_higher_low,
    next_decision_instant,
    structure_score_at,
)
from btc_predictor.research_backtest.replay_inputs import canonical_json_bytes, sha256_hex
from btc_predictor.risk.budget import calculate_risk_budget
from btc_predictor.risk.buffer import volatility_buffer_for_invalidation
from btc_predictor.risk.exposure import calculate_risk_at_stop
from btc_predictor.risk.sizing import initial_position_size_for_trade
from btc_predictor.risk.trailing import HIGHER_LOW, ConfirmedTrailingStructure, trail_stop_for_position
from btc_predictor.risk.tranches import next_tranche_for_position
from btc_predictor.signals.add_requirements import add_requirements_from_results
from btc_predictor.signals.data_quality import apply_data_quality_gate
from btc_predictor.signals.exit_rules import exit_rules_for_position
from btc_predictor.signals.trim import trim_rules_from_results

MANAGEMENT_COMPOSER_VERSION = "COMPOSE_CHAMPION_POSITION_MANAGEMENT_V1"
MANAGEMENT_COMPOSER_TICKET = "RBT-005"
MANAGEMENT_LEDGER_VERSION = "CHAMPION_MANAGEMENT_DECISION_LEDGER_V1"

OUTCOME_EXIT = "EXIT"
OUTCOME_TRIM = "TRIM"
OUTCOME_TRAIL = "TRAIL"
OUTCOME_HOLD = "HOLD"
OUTCOME_STRUCTURALLY_UNEVALUABLE = "STRUCTURALLY_UNEVALUABLE"
MANAGEMENT_OUTCOMES = (OUTCOME_EXIT, OUTCOME_TRIM, OUTCOME_TRAIL, OUTCOME_HOLD, OUTCOME_STRUCTURALLY_UNEVALUABLE)

# policy V7 section 7: each suppressed ADD under Rulebook 24 NO ADDING
REASON_RULEBOOK_24_NO_ADDING = "RULEBOOK_24_NO_ADDING_ENFORCED"
REASON_RULEBOOK_24_FLAG_UNKNOWN = "RULEBOOK_24_FLAG_STATE_UNKNOWN"
REASON_ADD_DATA_QUALITY_GATE = "ADD_DATA_QUALITY_GATE"
REASON_ADD_SUPPRESSED_BY_EXIT = "ADD_SUPPRESSED_BY_EXIT"
REASON_ADD_SUPPRESSED_BY_TRIM = "ADD_SUPPRESSED_BY_TRIM"
REASON_ADD_NO_FURTHER_TRANCHE = "ADD_NO_FURTHER_TRANCHE"
REASON_ADD_PENDING_TRAIL = "ADD_PENDING_TRAIL"
REASON_TRAIL_DEFERRED_BY_EXIT = "TRAIL_DEFERRED_BY_EXIT"
REASON_TRAIL_DEFERRED_BY_TRIM = "TRAIL_DEFERRED_BY_TRIM"
REASON_NO_MANAGEMENT_ACTION = "NO_MANAGEMENT_ACTION"
REASON_HOLD_INCOMPLETE = "HOLD_INCOMPLETE"

# the ADD that follows its TRAIL (owner ruling 1)
FOLLOWUP_ADD_EMITTED = "ADD_EMITTED"
FOLLOWUP_ADD_DROPPED = "ADD_DROPPED"
DROP_SUPERSEDED_BY_DECISION = "ADD_SUPERSEDED_BY_DECISION"
DROP_POSITION_CLOSED = "ADD_POSITION_CLOSED"
DROP_POSITION_CHANGED = "ADD_POSITION_CHANGED"
DROP_TRAIL_NOT_APPLIED = "ADD_TRAIL_NOT_APPLIED"
# owner review ruling 4: the ADD's projected risk at the stop, again at the callback that emits it
DROP_RISK_EXCEEDED_AT_CALLBACK = "ADD_RISK_AT_STOP_EXCEEDED_AT_CALLBACK"
DROP_RISK_RECHECK_INCOMPLETE = "ADD_RISK_RECHECK_INCOMPLETE"

# Spec values, each checked against the frozen spec text by the RBT-005 tests.
# FLOW_SUPPORTIVE_PREDICATE: decision_greater_equal(F.score, 60) (Rulebook 6.2 'Supportive').
FLOW_SUPPORTIVE_MIN = Decimal("60")
# REGIME_SUPPORTIVE_PREDICATE: BULL or STRONG_BULL.
REGIME_SUPPORTIVE_LABELS = ("STRONG_BULL", "BULL")
# REGIME_INVALIDATION_PREDICATE: the bear bands, Mild Bear or below.
REGIME_BEAR_LABELS = ("MILD_BEAR", "BEAR", "STRONG_BEAR")
# DATA_RISK_EXIT_PREDICATE: False at every exit evaluation (Rulebook 24).
DATA_RISK_EXIT_REQUIRED = False

_DAY = timedelta(days=1)


class ManagementComposerError(ValueError):
    """A management composition that cannot be made, with a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


# --- accounting (policy V7 section 5A.6) --------------------------------------------------


def _spec(input_id: str) -> AccountedCause:
    return AccountedCause(AUTHORITY_SPEC_ENTRY, input_id, f"{input_id}_INPUT_MISSING")


def _row(reference: str, cause: str) -> AccountedCause:
    return AccountedCause(AUTHORITY_INVENTORY_ROW, reference, cause)


# Reason code -> accounted cause for the in-position owners and spec inputs.
# Every other code is looked up in the entry composer's table.
MANAGEMENT_CAUSE_ACCOUNTING: Mapping[str, AccountedCause] = {
    **{
        f"{input_id}_INPUT_MISSING": _spec(input_id)
        for input_id in (
            "MOMENTUM_PERSISTENCE_SCORE", "ADD_MOMENTUM_SCORE", "NEW_STRUCTURE_SCORE", "NEW_STRUCTURAL_CONFIRMATION",
            "REGIME_SUPPORTIVE_PREDICATE", "FLOW_SUPPORTIVE_PREDICATE", "REGIME_INVALIDATION_PREDICATE",
        )
    },
    "HOLD_SCORE_INPUT_MISSING": _row("btc_predictor.features.hold.calculate_hold_score.inputs", "HOLD_SCORE_INPUT_MISSING"),
    "ADD_SCORE_INPUT_MISSING": _row("btc_predictor.features.add.calculate_add_score.inputs", "ADD_SCORE_INPUT_MISSING"),
    "ADD_REQUIREMENTS_INPUT_MISSING": _row(
        "btc_predictor.signals.add_requirements.add_requirements_from_results.new_structural_confirmation", "ADD_REQUIREMENTS_INPUT_MISSING"
    ),
    "TRIM_INPUT_MISSING": _row("btc_predictor.signals.trim.trim_rules_from_results.hold_score", "TRIM_INPUT_MISSING"),
    # the manual research override is never asserted in a replay (inventory: DISCRETIONARY)
    "EXIT_INPUT_MISSING": _row("btc_predictor.signals.exit_rules.exit_rules_for_position.manual_research_override", "EXIT_INPUT_MISSING"),
    "TRAILING_STOP_BUFFER_INCOMPLETE": _row("btc_predictor.risk.trailing.trail_stop_for_position.buffer", "no trail candidate"),
    # the frozen tranche schedule's own limit, not a missing input (spec named limitation, owner review ruling 7)
    "TRANCHE_SIZING_SCHEDULE_EXHAUSTED": AccountedCause(
        AUTHORITY_SPEC_NAMED_LIMITATION, "TRANCHE_SCHEDULE_EXHAUSTED", "TRANCHE_SIZING_SCHEDULE_EXHAUSTED"
    ),
    # RISK_AT_STOP_INPUT_MISSING is deliberately absent: an open position always has a
    # standing stop, and the inventory's "fail closed" covers only a closed lifecycle
}

# On a complete owner result only these codes signal a missing input; on an
# incomplete result every code is checked and at least one must be accounted.
_MISSING_MARKERS = ("INPUT_MISSING", "INSUFFICIENT_HISTORY", "HISTORY_INSUFFICIENT", "ZERO_VARIANCE", "PREVIOUS_SCORE_MISSING", "_UNKNOWN")


def accounted_cause(code: str, feature_id: str | None = None) -> AccountedCause | None:
    if code in MANAGEMENT_CAUSE_ACCOUNTING:
        return MANAGEMENT_CAUSE_ACCOUNTING[code]
    return entry_accounted_cause(code, feature_id)


# --- the position a management decision is about -------------------------------------------


@dataclass(frozen=True)
class ArmedEntry:
    """The ``ARM_ENTRY`` decision a position came from.

    ``entry_regime`` is ``K_entry`` for ``REGIME_INVALIDATION_PREDICATE``: the
    classification persisted on the entry ledger row (None if incomplete).
    ``position_size`` is the BTC-145 size, recomputed at the decision exactly as
    the BTC-180 engine sizes the entry.
    """

    source_id: str
    decision_at: datetime
    entry_regime: str | None
    risk_budget: Any
    position_size: Any


@dataclass(frozen=True)
class UnevaluableInput:
    component: str
    causes: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        return {"component": self.component, "causes": [{"code": code, **_accounting_record(code)} for code in self.causes]}


@dataclass(frozen=True)
class ManagementDecisionRow:
    """One management-ledger row: the decision at one instant with an open position."""

    decision_at: datetime
    venue: str
    outcome: str
    reasons: tuple[str, ...]
    position: Mapping[str, Any]
    regime: Mapping[str, Any]
    hold: Mapping[str, Any]
    exit_rules: Mapping[str, Any] | None
    trim: Mapping[str, Any] | None
    trail: Mapping[str, Any] | None
    add: Mapping[str, Any] | None
    unevaluable: tuple[UnevaluableInput, ...]
    owner_reason_codes: Mapping[str, Any]
    unaccounted: tuple[str, ...]
    intent: Mapping[str, Any] | None

    def as_record(self) -> dict[str, Any]:
        return _jsonable(
            {
                "decision_at": self.decision_at,
                "venue": self.venue,
                "outcome": self.outcome,
                "reasons": list(self.reasons),
                "position": self.position,
                "regime": self.regime,
                "hold": self.hold,
                "exit": self.exit_rules,
                "trim": self.trim,
                "trail": self.trail,
                "add": self.add,
                "unevaluable": [item.as_record() for item in self.unevaluable],
                "owner_reason_codes": self.owner_reason_codes,
                "unaccounted": list(self.unaccounted),
                "intent": self.intent,
            }
        )


@dataclass(frozen=True)
class AddFollowUp:
    """What became of the ADD a TRAIL decision left pending (owner ruling 1)."""

    decision_at: datetime
    resolved_at: datetime
    outcome: str
    reasons: tuple[str, ...]
    intent: Mapping[str, Any] | None
    # owner review ruling 4: the risk re-check at this callback (None if the ADD was dropped before it)
    risk_recheck: Mapping[str, Any] | None = None
    unaccounted: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        return _jsonable(
            {
                "decision_at": self.decision_at,
                "resolved_at": self.resolved_at,
                "outcome": self.outcome,
                "reasons": list(self.reasons),
                "intent": self.intent,
                "risk_recheck": self.risk_recheck,
                "unaccounted": list(self.unaccounted),
            }
        )


@dataclass(frozen=True)
class ManagementDecision:
    """The decision at one instant: its row, the intent, and an ADD left pending on the TRAIL."""

    row: ManagementDecisionRow
    intent: BacktestIntent | None
    pending_add: BacktestIntent | None = None


@dataclass(frozen=True)
class _PendingAdd:
    decision_at: datetime
    intent: BacktestIntent
    stop_price: Decimal
    opened_at: datetime | None
    quantity: Decimal


# --- composer -------------------------------------------------------------------------------


class ManagementComposer:
    """The champion's BTC-180 strategy: the entry composer while flat, management while open.

    :meth:`decide` is engine-agnostic: an entry decision with its composition,
    the lifecycle, NAV, the armed entry and the prior instant's flow in, a
    decision record out (Rulebook invariant 15). Calling the instance is the
    BTC-180 ``run_backtest`` strategy adapter.
    """

    def __init__(self, entry: EntryComposer) -> None:
        if not isinstance(entry, EntryComposer):
            raise ManagementComposerError("INPUT_REFUSED", "entry must be the RBT-004 EntryComposer")
        self._entry = entry
        self._config = entry.strategy_config
        self._metadata = dict(self._config.run_metadata())
        self._venue = entry.venue
        self._ledger: list[ManagementDecisionRow] = []
        self._followups: list[AddFollowUp] = []
        self._armed: dict[str, ArmedEntry] = {}
        # the FlowScoreResult of each evaluated decision instant: the trim owner's prior flow
        self._flows: dict[datetime, Any] = {}
        self._pending: _PendingAdd | None = None
        self._last_callback_at: datetime | None = None
        self._last_lifecycle: Any = None

    # -- public ---------------------------------------------------------------------

    @property
    def entry(self) -> EntryComposer:
        return self._entry

    @property
    def ledger(self) -> tuple[ManagementDecisionRow, ...]:
        return tuple(self._ledger)

    @property
    def add_followups(self) -> tuple[AddFollowUp, ...]:
        return tuple(self._followups)

    def ledger_records(self) -> list[dict[str, Any]]:
        return [row.as_record() for row in self._ledger]

    def ledger_bytes(self) -> bytes:
        header = {
            "ledger_version": MANAGEMENT_LEDGER_VERSION,
            "composer_version": MANAGEMENT_COMPOSER_VERSION,
            "research_strategy_id": RESEARCH_STRATEGY_ID,
            "completion_spec": {"version": SPEC_VERSION, "sha256": COMPLETION_SPEC_SHA256},
            "champion_base_identity": dict(CHAMPION_BASE_IDENTITY),
            "venue": self._venue,
            # the entry half's ledger at the same point, so the pair is one record
            "entry_ledger_sha256": EntryComposer.ledger_sha256(self._entry),
            "rows": self.ledger_records(),
            "add_followups": [item.as_record() for item in self._followups],
        }
        return canonical_json_bytes(header)

    def ledger_sha256(self) -> str:
        return sha256_hex(self.ledger_bytes())

    def unaccounted_causes(self) -> tuple[tuple[str, str], ...]:
        rows = [(row.decision_at.isoformat(), code) for row in self._ledger for code in row.unaccounted]
        followups = [(item.resolved_at.isoformat(), code) for item in self._followups for code in item.unaccounted]
        return tuple(rows + followups)

    def __call__(self, context: BacktestContext) -> BacktestIntent | None:
        """The BTC-180 strategy callback.

        The entry composer records its row at every decision instant. While a
        position is open, this composer decides at each decision instant; a
        decision instant the engine never offered (no bar closes at it) is
        recorded at the first callback after it as the missing-bar row, with the
        position the previous callback reported (as RBT-004 records it). At the
        first callback after a TRAIL that left an ADD pending, the ADD follows
        or is dropped (owner ruling 1).
        """

        as_of = _utc(context.as_of, "as_of")
        previous_at, previous_lifecycle = self._last_callback_at, self._last_lifecycle
        followup = self._resolve_pending(context, as_of)
        decision = EntryComposer.step(self._entry, context)
        self._last_callback_at, self._last_lifecycle = as_of, context.lifecycle
        if previous_at is not None and previous_lifecycle is not None and previous_lifecycle.quantity > 0:
            missed = next_decision_instant(previous_at)
            while missed < as_of:
                self._append(self._missing_bar_row(missed, previous_lifecycle))
                missed += _DAY
        if decision is None:
            return followup
        if decision.composition is not None:
            self._flows[decision.row.decision_at] = decision.composition.flow
        if decision.intent is not None:
            self._arm(decision, context)
            return decision.intent
        if context.open_quantity <= 0:
            return None
        if decision.composition is None:
            self._append(self._missing_bar_row(decision.row.decision_at, context.lifecycle))
            return None
        bar = decision.composition.decision_bar
        if context.bar.timestamp != bar.timestamp or context.bar.close != bar.close:
            raise ManagementComposerError("COMPOSER_DEFECT", "the engine's decision bar differs from the composition's")
        managed = self.decide(
            decision,
            lifecycle=context.lifecycle,
            nav=context.nav,
            armed=self._armed_for(context.lifecycle),
            prior_flow=self._flows.get(decision.row.decision_at - _DAY),
        )
        self.record(managed)
        if managed.pending_add is not None:
            trail = managed.intent.trailing_stop
            self._pending = _PendingAdd(
                decision.row.decision_at, managed.pending_add, trail.stop_price, context.lifecycle.opened_at, context.lifecycle.quantity
            )
        return managed.intent

    def decide(self, decision: EntryDecision, *, lifecycle: Any, nav: Decimal, armed: ArmedEntry, prior_flow: Any | None) -> ManagementDecision:
        """Compose the management decision at one daily decision instant (no ledger write)."""

        if decision.composition is None:
            raise ManagementComposerError("INPUT_REFUSED", "a missing-bar instant has no composition to manage")
        if self._ledger and decision.row.decision_at <= self._ledger[-1].decision_at:
            raise ManagementComposerError("DECISION_ORDER", "decision instants must strictly increase")
        if lifecycle.quantity <= 0:
            raise ManagementComposerError("INPUT_REFUSED", "management needs an open position")
        return _ManagementRun(self, decision, lifecycle=lifecycle, nav=nav, armed=armed, prior_flow=prior_flow).run()

    def record(self, decision: ManagementDecision) -> None:
        """Append a :meth:`decide` result to the ledger (the engine adapter does this)."""

        self._append(decision.row)

    # -- internals ------------------------------------------------------------------

    def _append(self, row: ManagementDecisionRow) -> None:
        if self._ledger and row.decision_at <= self._ledger[-1].decision_at:
            raise ManagementComposerError("DECISION_ORDER", "ledger rows must strictly increase")
        self._ledger.append(row)

    def _arm(self, decision: EntryDecision, context: BacktestContext) -> None:
        """Size the armed entry exactly as the engine will (BTC-145), and keep K_entry."""

        intent = decision.intent
        budget = calculate_risk_budget(entry_conviction=intent.entry_conviction, nav=context.nav, config=self._config)
        size = initial_position_size_for_trade(budget, intent.initial_stop, config_metadata=self._metadata)
        regime = decision.row.regime
        self._armed[intent.source_id] = ArmedEntry(
            source_id=intent.source_id,
            decision_at=decision.row.decision_at,
            entry_regime=regime["classification"] if regime["complete"] else None,
            risk_budget=budget,
            position_size=size,
        )

    def _armed_for(self, lifecycle: Any) -> ArmedEntry:
        entered = [item for item in lifecycle.transitions if item.event == ENTER and item.accepted]
        if len(entered) != 1 or entered[0].source_record_id not in self._armed:
            raise ManagementComposerError("COMPOSER_DEFECT", "the open position did not come from an ARM_ENTRY this composer recorded")
        return self._armed[entered[0].source_record_id]

    def _resolve_pending(self, context: BacktestContext, as_of: datetime) -> BacktestIntent | None:
        pending, self._pending = self._pending, None
        if pending is None:
            return None
        lifecycle = context.lifecycle
        later = [item for item in lifecycle.transitions if item.accepted and item.event_time > pending.decision_at]
        moved = [item for item in later if item.event == STOP_MOVE and item.stop_price == pending.stop_price]
        if is_daily_decision_instant(as_of):
            reason = DROP_SUPERSEDED_BY_DECISION
        elif lifecycle.quantity <= 0 or lifecycle.opened_at != pending.opened_at:
            reason = DROP_POSITION_CLOSED
        elif lifecycle.quantity != pending.quantity or len(later) != len(moved):
            # any accepted transition but the ADD's own trail changes the position (ruling 1)
            reason = DROP_POSITION_CHANGED
        elif not moved or lifecycle.stop_price != pending.stop_price:
            reason = DROP_TRAIL_NOT_APPLIED
        else:
            reason = None
        if reason is not None:
            self._followups.append(AddFollowUp(pending.decision_at, as_of, FOLLOWUP_ADD_DROPPED, (reason,), None))
            return None
        recheck, drop, unaccounted = self._recheck_risk(context, lifecycle)
        if drop:
            self._followups.append(AddFollowUp(pending.decision_at, as_of, FOLLOWUP_ADD_DROPPED, drop, None, recheck, unaccounted))
            return None
        self._followups.append(
            AddFollowUp(pending.decision_at, as_of, FOLLOWUP_ADD_EMITTED, (), _intent_record(pending.intent), recheck, unaccounted)
        )
        return pending.intent

    def _recheck_risk(self, context: BacktestContext, lifecycle: Any) -> tuple[dict[str, Any], tuple[str, ...], tuple[str, ...]]:
        """Owner review ruling 4: the ADD's projected risk at the stop, at this callback.

        The same owners as at t (``next_tranche_for_position``, then
        ``calculate_risk_at_stop``), at the close of the bar this callback
        serves, with the installed stop and this callback's NAV. The engine then
        fills at the next bar's open; a gap at that open is the recorded
        limitation.
        """

        armed = self._armed_for(lifecycle)
        price = context.bar.close
        tranche = next_tranche_for_position(
            lifecycle, armed.position_size, entry_price=price, config=self._config, config_metadata=self._metadata
        )
        results: dict[str, Any] = {"recheck_tranche": tranche}
        risk = None
        if tranche.allocation is not None:
            risk = calculate_risk_at_stop(
                (*lifecycle.tranches, {"tranche_id": "projected_add", "quantity": tranche.allocation.quantity, "entry_price": price}),
                stop_price=lifecycle.stop_price,
                nav=context.nav,
                direction=lifecycle.direction,
                config=self._config,
                config_metadata=self._metadata,
            )
            results["recheck_risk_at_stop"] = risk
        record = {
            "bar_timestamp": context.bar.timestamp,
            "price": price,
            "stop_price": lifecycle.stop_price,
            "nav": context.nav,
            "projected_risk_fraction_nav": risk.risk_fraction_nav if risk is not None else None,
            "within_maximum": risk.within_maximum if risk is not None else None,
            "owner_reason_codes": {
                label: {"feature_id": result.feature_id, "complete": result.complete, "reason_codes": list(result.reason_codes)}
                for label, result in sorted(results.items())
            },
        }
        if risk is None or not tranche.complete or not risk.complete:
            drop = (DROP_RISK_RECHECK_INCOMPLETE, *_unique(code for result in results.values() for code in result.reason_codes))
        elif not risk.within_maximum:
            drop = (DROP_RISK_EXCEEDED_AT_CALLBACK,)
        else:
            drop = ()
        return record, drop, _unaccounted_results(results)

    def _missing_bar_row(self, instant: datetime, lifecycle: Any) -> ManagementDecisionRow:
        return ManagementDecisionRow(
            decision_at=instant,
            venue=self._venue,
            outcome=OUTCOME_STRUCTURALLY_UNEVALUABLE,
            reasons=(CAUSE_DECISION_PRICE_BAR_MISSING,),
            position=_position_record(lifecycle, None),
            regime={},
            hold={},
            exit_rules=None,
            trim=None,
            trail=None,
            add=None,
            unevaluable=(UnevaluableInput("decision_instant", (CAUSE_DECISION_PRICE_BAR_MISSING,)),),
            owner_reason_codes={},
            unaccounted=tuple(code for code in (CAUSE_DECISION_PRICE_BAR_MISSING,) if accounted_cause(code) is None),
            intent=None,
        )


class _ManagementRun:
    """One decision instant's management composition; it records every owner result."""

    def __init__(self, composer: ManagementComposer, decision: EntryDecision, *, lifecycle: Any, nav: Decimal, armed: ArmedEntry, prior_flow: Any | None) -> None:
        self.c = composer
        self.t = decision.row.decision_at
        self.decision = decision
        self.composition = decision.composition
        self.lifecycle = lifecycle
        self.nav = nav
        self.armed = armed
        self.prior_flow = prior_flow
        self.config = composer._config
        self.metadata = composer._metadata
        self.price = self.composition.price
        self.results: dict[str, Any] = {}
        self.composer_causes: dict[str, list[str]] = {}

    # -- recording ----------------------------------------------------------------

    def _keep(self, label: str, result: Any) -> Any:
        self.results[label] = result
        return result

    def _cause(self, component: str, code: str) -> None:
        self.composer_causes.setdefault(component, [])
        if code not in self.composer_causes[component]:
            self.composer_causes[component].append(code)

    # -- run ------------------------------------------------------------------------

    def run(self) -> ManagementDecision:
        # DATA_QUALITY_FAIL blocks adds only (Rulebook 24); its codes are exit evidence
        self.gate = apply_data_quality_gate(ADD, self.composition.quality_failures)
        self.gate_codes = tuple(reason.code for reason in self.gate.reason_codes)
        hold = self._hold()
        exit_signal = self._exit(hold)
        trim = self._trim(hold)
        trail = self._trail()
        add = self._add(trail)

        intent = None
        pending_add = None
        add_record = add["record"]
        if exit_signal.signal:
            outcome, reasons = OUTCOME_EXIT, tuple(exit_signal.exit_reasons)
            intent = self._intent(EXIT_ACTION, exit_reason=exit_signal.exit_reasons[0])
            if add["go"]:
                add_record = {**add_record, "outcome": "SUPPRESSED", "reasons": [*add_record["reasons"], REASON_ADD_SUPPRESSED_BY_EXIT]}
        elif trim.signal:
            outcome, reasons = OUTCOME_TRIM, tuple(trim.reason_codes)
            intent = self._intent(TRIM_ACTION, trim_signal=trim)
            if add["go"]:
                add_record = {**add_record, "outcome": "SUPPRESSED", "reasons": [*add_record["reasons"], REASON_ADD_SUPPRESSED_BY_TRIM]}
        elif trail.advanced:
            outcome, reasons = OUTCOME_TRAIL, tuple(trail.reason_codes)
            intent = self._intent(TRAIL_ACTION, trailing_stop=trail)
            if add["go"]:
                pending_add = self._intent(ADD_ACTION, requirements=self.results["add_requirements"])
                reasons = (*reasons, REASON_ADD_PENDING_TRAIL)
                add_record = {**add_record, "outcome": "PENDING_TRAIL", "intent": _intent_record(pending_add)}
        elif hold.complete:
            outcome, reasons = OUTCOME_HOLD, (REASON_NO_MANAGEMENT_ACTION,)
        else:
            outcome, reasons = OUTCOME_STRUCTURALLY_UNEVALUABLE, (REASON_HOLD_INCOMPLETE,)
        trail_record = self._trail_record(trail)
        if trail.advanced and outcome in (OUTCOME_EXIT, OUTCOME_TRIM):
            deferred = REASON_TRAIL_DEFERRED_BY_EXIT if outcome == OUTCOME_EXIT else REASON_TRAIL_DEFERRED_BY_TRIM
            trail_record = {**trail_record, "deferred": deferred}

        row = ManagementDecisionRow(
            decision_at=self.t,
            venue=self.c._venue,
            outcome=outcome,
            reasons=reasons,
            position=_position_record(self.lifecycle, self.armed),
            regime=self.regime_record,
            hold=self.hold_record,
            exit_rules=_signal_record(exit_signal, exit_reasons=list(exit_signal.exit_reasons)),
            trim=_signal_record(trim, prior_flow_causes=list(self.composer_causes.get("trim", ()))),
            trail=trail_record,
            add=add_record,
            unevaluable=self._unevaluable(hold),
            owner_reason_codes={
                label: {"feature_id": result.feature_id, "complete": result.complete, "reason_codes": list(result.reason_codes)}
                for label, result in sorted(self.results.items())
            },
            unaccounted=self._unaccounted(),
            intent=_intent_record(intent),
        )
        return ManagementDecision(row, intent, pending_add)

    def _intent(self, action: str, **fields: Any) -> BacktestIntent:
        return BacktestIntent(
            action=action,
            direction=self.lifecycle.direction,
            source_id=f"rbt005:{self.c._venue}:{action.lower()}:{self.t.isoformat()}",
            **fields,
        )

    # -- 1: Hold (Rulebook 20) ----------------------------------------------------------

    def _hold(self) -> Any:
        composition = self.composition
        structure = self._structure_at("hold_structure", self.lifecycle.stop_price, "hold")
        persistence = self._normal_score("TREND_Z_M12", "MOMENTUM_PERSISTENCE_SCORE", "hold")
        flow = composition.flow.score if composition.flow.complete else None
        inputs = HoldScoreInput(
            trend_score=composition.trend_score,
            flow_score=flow,
            positioning_score=composition.positioning_score,
            structure_score=structure,
            momentum_persistence_score=persistence,
        )
        hold = self._keep("hold_score", calculate_hold_score(inputs, strategy_config=self.config))
        self.hold_record = {
            "score": hold.score,
            "complete": hold.complete,
            "inputs": {
                "trend": composition.trend_score,
                "flow": flow,
                "positioning": composition.positioning_score,
                "structure": structure,
                "momentum_persistence": persistence,
            },
            "reason_codes": list(hold.reason_codes),
        }
        return hold

    def _structure_at(self, label: str, stop_price: Decimal, component: str) -> Decimal | None:
        at = structure_score_at(self.composition, stop_price)
        self._keep(f"{label}_selection", at.selection)
        if at.level_strength is not None:
            self._keep(f"{label}_level_strength", at.level_strength)
        result = self._keep(label, at.result)
        for cause in at.causes:
            self._cause(component, cause)
        return result.score if result.complete else None

    def _normal_score(self, z_input: str, input_id: str, component: str) -> Decimal | None:
        """``100 * Phi(z)``, as the trend and flow owners map a z-score to 0-100."""

        z = self.composition.trend_z[z_input]
        if z is None:
            self._cause(component, f"{input_id}_INPUT_MISSING")
            return None
        return Decimal(str(normal_cdf_score(float(z))))

    # -- 2: Exit (Rulebook 23, 26; BTC-158) ----------------------------------------------

    def _exit(self, hold: Any) -> Any:
        current = self.composition.regime_classification
        entry_regime = self.armed.entry_regime
        if not current.complete or entry_regime is None:
            invalidated = None
            self._cause("exit", "REGIME_INVALIDATION_PREDICATE_INPUT_MISSING")
        else:
            invalidated = current.regime in REGIME_BEAR_LABELS and entry_regime not in REGIME_BEAR_LABELS
        self.regime_record = {
            "classification": current.regime if current.complete else None,
            "complete": current.complete,
            "entry_classification": entry_regime,
            "invalidated": invalidated,
        }
        return self._keep(
            "exit",
            exit_rules_for_position(
                lifecycle=self.lifecycle,
                # the decision bar's direction-appropriate extreme (inventory: structural_stop_triggered)
                current_price=self.composition.decision_bar.low,
                hold_score=hold,
                regime_invalidated=invalidated,
                data_risk_exit_required=DATA_RISK_EXIT_REQUIRED,
                manual_research_override=None,
                manual_override_reason=None,
                strategy_config=self.config,
                evaluated_at=self.t,
                source_reason_codes={"data_quality_gate": self.gate_codes},
            ),
        )

    # -- 3: Trim (Rulebook 23; BTC-157) --------------------------------------------------

    def _trim(self, hold: Any) -> Any:
        prior_flow = self.prior_flow
        if prior_flow is None:
            # The prior decision instant had no decision bar, so no flow was composed for it.
            # The trim owner takes a FlowScoreResult and maps an incomplete one to
            # prior_flow_score None: "None -> TRIM_INPUT_MISSING; complete False, the other
            # triggers still evaluate" (bound inventory rows trim_rules_from_results.prior_flow
            # and TrimRuleInput.prior_flow_score). The flow owner's own result with every input
            # missing says exactly that; no value is improvised.
            self._cause("trim", CAUSE_DECISION_PRICE_BAR_MISSING)
            prior_flow = self._keep(
                "trim_prior_flow_unavailable",
                calculate_flow_score(
                    FlowScoreInput(
                        etf_norm_5_zscore=None,
                        etf_norm_20_zscore=None,
                        flow_accel_zscore=None,
                        cvd_spread_zscore=None,
                        spot_dominance_zscore=None,
                    ),
                    core_weights=dict(self.config.scoring_weights.core_flow),
                    full_weights=dict(self.config.scoring_weights.full_flow),
                    config_metadata=self.metadata,
                ),
            )
        return self._keep(
            "trim",
            trim_rules_from_results(
                lifecycle=self.lifecycle,
                hold_score=hold,
                euphoria=self.composition.euphoria,
                crowding=self.composition.crowding,
                current_flow=self.composition.flow,
                prior_flow=prior_flow,
                strategy_config=self.config,
            ),
        )

    # -- 4: Trail (Rulebook 22; BTC-156) --------------------------------------------------

    def _trail(self) -> Any:
        higher_low = latest_higher_low(self.composition)
        self.structure_data_cause = False
        structure = None
        if higher_low is not None:
            self._keep("trailing_higher_low", higher_low)
            if "HIGHER_LOW_SOURCE_BAR_MISSING" in higher_low.reason_codes:
                self.structure_data_cause = True
            elif higher_low.triggered:
                structure = ConfirmedTrailingStructure(
                    # a higher low is identified by its own bar, never a source swing's
                    structure_id=f"{higher_low.feature_id}:{higher_low.higher_low_timestamp.isoformat()}",
                    source_feature_id=higher_low.feature_id,
                    direction=self.lifecycle.direction,
                    structure_type=HIGHER_LOW,
                    price=higher_low.higher_low_price,
                    level_timestamp=higher_low.higher_low_timestamp,
                    detected_at=higher_low.detected_at,
                    config_metadata=self.metadata,
                    reason_codes=tuple(higher_low.reason_codes),
                )
        self.structure = structure
        stop_buffers = self.config.stop_buffers
        buffer = self._keep(
            "trailing_buffer",
            # a higher low is a point: no zone, so the owner's ATR-only buffer
            volatility_buffer_for_invalidation(
                {},
                atr=self.composition.atr,
                atr_multiplier=stop_buffers.atr_multiplier,
                atr_window=stop_buffers.atr_period,
                config_metadata=self.metadata,
            ),
        )
        return self._keep(
            "trailing_stop",
            trail_stop_for_position(self.lifecycle, structure=structure, buffer=buffer, current_price=self.price, as_of=self.t),
        )

    def _trail_record(self, trail: Any) -> dict[str, Any]:
        return {
            "structure": self.structure.as_record() if self.structure is not None else None,
            "advanced": trail.advanced,
            "previous_stop": trail.previous_stop,
            "stop_price": trail.stop_price,
            "candidate_stop": trail.candidate_stop,
            "stage": trail.stage,
            "complete": trail.complete,
            "reason_codes": list(trail.reason_codes),
        }

    # -- 5: Add (Rulebook 18, 19, 21, 24; BTC-153, BTC-154) --------------------------------

    def _add(self, trail: Any) -> dict[str, Any]:
        composition = self.composition
        reasons: list[str] = []
        confirmation = self._new_structural_confirmation(trail)
        momentum = self._normal_score("TREND_Z_M4", "ADD_MOMENTUM_SCORE", "add")
        new_structure = self._structure_at("add_structure", trail.stop_price, "add")
        if new_structure is None:
            self._cause("add", "NEW_STRUCTURE_SCORE_INPUT_MISSING")
        current = self._keep("risk_at_stop_current", self._risk_at_stop(self.lifecycle.tranches, self.lifecycle.stop_price))
        proposed = self._keep("risk_at_stop_proposed", self._risk_at_stop(self.lifecycle.tranches, trail.stop_price))
        tranche = self._keep(
            "add_tranche",
            next_tranche_for_position(
                self.lifecycle, self.armed.position_size, entry_price=self.price, config=self.config, config_metadata=self.metadata
            ),
        )
        flags = self._no_adding_flags()
        record: dict[str, Any] = {
            "evaluated": False,
            "new_structural_confirmation": confirmation,
            "rulebook_24": flags,
            "data_quality_gate": {"action": self.gate.action, "data_quality_fail": self.gate.data_quality_fail},
        }
        if not current.complete or not proposed.complete or tranche.allocation is None:
            if tranche.allocation is None:
                reasons.extend((REASON_ADD_NO_FURTHER_TRANCHE, *tranche.reason_codes))
            for result in (current, proposed):
                if not result.complete:
                    reasons.extend(code for code in result.reason_codes if code not in reasons)
            return {"go": False, "record": {**record, "outcome": "NOT_EVALUATED", "reasons": reasons}}

        improvement = risk_improvement_component_score(current_risk=current.risk_at_stop, proposed_risk=proposed.risk_at_stop)
        flow = composition.flow.score if composition.flow.complete else None
        add_score = self._keep(
            "add_score",
            calculate_add_score(
                AddScoreInput(
                    new_structure_score=new_structure,
                    flow_score=flow,
                    positioning_score=composition.positioning_score,
                    momentum_score=momentum,
                    risk_improvement_score=improvement.score,
                ),
                strategy_config=self.config,
            ),
        )
        projected = self._keep(
            "risk_at_stop_projected",
            self._risk_at_stop(
                (
                    *self.lifecycle.tranches,
                    {"tranche_id": "projected_add", "quantity": tranche.allocation.quantity, "entry_price": self.price},
                ),
                trail.stop_price,
            ),
        )
        requirements = self._keep(
            "add_requirements",
            add_requirements_from_results(
                lifecycle=self.lifecycle,
                current_price=self.price,
                add_score=add_score,
                risk_improvement=improvement,
                projected_risk_at_stop=projected,
                new_structural_confirmation=confirmation,
                regime_supportive=self._regime_supportive(),
                flow_supportive=self._flow_supportive(),
                positioning_healthy=self._positioning_healthy(),
                strategy_config=self.config,
                source_reason_codes={"data_quality_gate": self.gate_codes},
            ),
        )
        if requirements.blocked:
            reasons.extend(requirements.reason_codes)
        if self.gate.action != ADD:
            reasons.append(REASON_ADD_DATA_QUALITY_GATE)
        if any(state is True for state in flags.values()):
            reasons.append(REASON_RULEBOOK_24_NO_ADDING)
        if any(state is None for state in flags.values()):
            reasons.append(REASON_RULEBOOK_24_FLAG_UNKNOWN)
        go = not reasons
        record = {
            **record,
            "evaluated": True,
            "outcome": "PERMITTED" if go else "BLOCKED",
            "reasons": reasons,
            "add_score": add_score.score,
            "momentum_score": momentum,
            "new_structure_score": new_structure,
            "risk_improvement": {
                "current_risk": improvement.current_risk,
                "proposed_risk": improvement.proposed_risk,
                "signed_improvement": improvement.signed_improvement,
                "score": improvement.score,
            },
            "projected_risk_fraction_nav": projected.risk_fraction_nav,
            "tranche_number": tranche.tranche_number,
            "requirements_blocked": requirements.blocked,
        }
        return {"go": go, "record": record}

    def _new_structural_confirmation(self, trail: Any) -> bool | None:
        """Spec ``NEW_STRUCTURAL_CONFIRMATION``, on the lifecycle before this instant's STOP_MOVE."""

        if not trail.complete or self.structure_data_cause:
            self._cause("add", "NEW_STRUCTURAL_CONFIRMATION_INPUT_MISSING")
            return None
        entered = [item.event_time for item in self.lifecycle.transitions if item.accepted and item.event in (ENTER, ADD)]
        latest = max(entered)
        return bool(trail.advanced and trail.structure_type == HIGHER_LOW and trail.structure_level_timestamp > latest)

    def _risk_at_stop(self, tranches: Any, stop_price: Decimal) -> Any:
        return calculate_risk_at_stop(
            tranches,
            stop_price=stop_price,
            nav=self.nav,
            direction=self.lifecycle.direction,
            config=self.config,
            config_metadata=self.metadata,
        )

    def _regime_supportive(self) -> bool | None:
        current = self.composition.regime_classification
        if not current.complete:
            self._cause("add", "REGIME_SUPPORTIVE_PREDICATE_INPUT_MISSING")
            return None
        return current.regime in REGIME_SUPPORTIVE_LABELS

    def _flow_supportive(self) -> bool | None:
        flow = self.composition.flow
        if not flow.complete:
            self._cause("add", "FLOW_SUPPORTIVE_PREDICATE_INPUT_MISSING")
            return None
        return bool(decision_greater_equal(flow.score, FLOW_SUPPORTIVE_MIN))

    def _positioning_healthy(self) -> bool | None:
        # Rulebook 18.1(6) 'positioning is not crowded': not CROWDING.flagged (inventory)
        crowding = self.composition.crowding
        return (not crowding.flagged) if crowding.complete else None

    def _no_adding_flags(self) -> dict[str, bool | None]:
        """Rulebook 24 NO ADDING: each flag as the hard veto reads it (see the module notes)."""

        crowding = self.composition.crowding
        euphoria = self.composition.euphoria
        inputs = euphoria.inputs
        # every EUPHORIA input but the DISCRETIONARY systemic_euphoria
        measured = all(
            value is not None
            for value in (
                inputs.range_percentile, inputs.upside_return, inputs.funding_zscore, inputs.basis_zscore,
                inputs.oi_intensity_percentile, inputs.volatility_percentile,
            )
        )
        return {
            "stress": self.composition.stress_mapped,
            "crowding": crowding.flagged if crowding.complete else None,
            "euphoria": euphoria.flagged if measured else None,
        }

    # -- accounting -----------------------------------------------------------------------

    def _unevaluable(self, hold: Any) -> tuple[UnevaluableInput, ...]:
        if hold.complete:
            return ()
        entry_causes = {item.component: item.causes for item in self.decision.row.unevaluable}
        items = []
        for name, value in self.hold_record["inputs"].items():
            if value is not None:
                continue
            if name in ("trend", "flow", "positioning"):
                causes = entry_causes.get(name, ())
            elif name == "structure":
                result = self.results["hold_structure"]
                causes = (
                    *self.composer_causes.get("hold", ()),
                    *(code for code in result.reason_codes if accounted_cause(code, result.feature_id) is not None),
                )
            else:
                causes = ("MOMENTUM_PERSISTENCE_SCORE_INPUT_MISSING",)
            items.append(UnevaluableInput(name, _unique(causes)))
        return tuple(items)

    def _unaccounted(self) -> tuple[str, ...]:
        missing = list(_unaccounted_results(self.results))
        for component, codes in self.composer_causes.items():
            for code in codes:
                if accounted_cause(code) is None:
                    missing.append(f"{component}:{code}")
        return _unique(missing)


def _unaccounted_results(results: Mapping[str, Any]) -> tuple[str, ...]:
    """Owner results whose incompleteness or missing-input codes have no accounted cause (V7 section 5A.6)."""

    missing = []
    for label, result in results.items():
        codes = tuple(result.reason_codes)
        if not result.complete:
            if not any(accounted_cause(code, result.feature_id) is not None for code in codes):
                missing.append(f"{label}:{'|'.join(codes) or 'INCOMPLETE_WITHOUT_REASON'}")
        for code in codes:
            if any(marker in code for marker in _MISSING_MARKERS) and accounted_cause(code, result.feature_id) is None:
                missing.append(f"{label}:{code}")
    return _unique(missing)


# --- records ------------------------------------------------------------------------------


def _position_record(lifecycle: Any, armed: ArmedEntry | None) -> dict[str, Any]:
    return {
        "quantity": lifecycle.quantity,
        "average_entry_price": lifecycle.average_entry_price,
        "standing_stop": lifecycle.stop_price,
        "tranche_count": len(lifecycle.tranches),
        "opened_at": lifecycle.opened_at,
        "entry_source_id": armed.source_id if armed is not None else None,
        "entry_decision_at": armed.decision_at if armed is not None else None,
    }


def _signal_record(result: Any, **extra: Any) -> dict[str, Any]:
    return {"evaluated": True, "signal": result.signal, "complete": result.complete, "reason_codes": list(result.reason_codes), **extra}


def _intent_record(intent: BacktestIntent | None) -> dict[str, Any] | None:
    if intent is None:
        return None
    return {
        "action": intent.action,
        "direction": intent.direction,
        "source_id": intent.source_id,
        "exit_reason": intent.exit_reason,
        "trailing_stop": intent.trailing_stop.as_record() if intent.trailing_stop is not None else None,
        "trim_signal": intent.trim_signal.as_record() if intent.trim_signal is not None else None,
        "requirements": intent.requirements.as_record() if intent.requirements is not None else None,
    }


def _accounting_record(code: str) -> dict[str, Any]:
    cause = accounted_cause(code)
    return {"accounted": cause.as_record() if cause is not None else None}


def _unique(values: Any) -> tuple[str, ...]:
    seen: list[str] = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return tuple(seen)


def _utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ManagementComposerError("INPUT_REFUSED", f"{name} must be a timezone-aware datetime")
    return value.astimezone(UTC)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return repr(value)
    raise ManagementComposerError("NOT_SERIALISABLE", f"{type(value).__name__} has no ledger form")
