"""RBT-007 ``RUN_FIRST_RESEARCH_BACKTEST_V1``: the frozen pipeline, run, and the policy section 8 report.

It runs the champion frozen by RBT-006, unchanged, on RBT-003's frozen replay
dataset, under ``RESEARCH_BACKTEST_POLICY_V7`` and the RBT-007 owner rulings
of 2026-11-18. Its output is ``RESEARCH_BACKTEST_NON_CERTIFYING`` research
evidence only. Nothing here touches the holdout (NOT COLLECTED) or BTC-019.

**The runs.** Every run replays one venue's frozen 1h stream through the
BTC-180 engine, with the RBT-004/RBT-005 composers as its strategy:

- the champion's headline run over each venue's evaluation window, under
  each BTC-181 cost rung (``base`` is the headline);
- the champion's BTC-182 walk-forward under ``INDEPENDENT_FOLD_CAPITAL_V1``,
  under each rung: expanding folds of 4,368 hourly bars from the venue's
  evaluation start, a 4,368-bar step and no embargo (ruling 4);
- every preregistered BTC-185 sweep candidate, as a walk-forward under
  ``base``, labelled ``SENSITIVITY_ONLY_NOT_SELECTION``;
- the frozen Momentum Persistence ablation over each evaluation window
  under ``base``, labelled the same;
- the six BTC-224 golden periods on each venue, at each scenario's own
  cost rung and starting NAV.

A run covers the decision instants ``[first, last]`` and the bars whose
engine availability lies in ``[first, last + 1 day)``, so no decision is
ever composed after the last one, and no bar is available in the holdout.

**Frozen code (ruling 2).** The composers and every repository module they
import stay byte-identical to the preregistration's code commit; the runner
checks this before any run. It runs only in the process its launcher,
``runner_launch.sh``, starts: Python isolated and without ``site``, writing
no bytecode and reading an empty private cache, so nothing but the
interpreter runs before the checks (review N2). A sweep candidate or the
ablation variant reaches the unchanged composers through
:class:`RegisteredEntryComposer`, which accepts only the configurations the
preregistration lists.

**Shared positioning results** (the runtime ruling and ruling 6) come from
:mod:`runner_shared`; the look-ahead audit (ruling 3) recomputes sampled
decisions on truncated inputs without them.

**Outputs (ruling 1).** Every value-bearing output (ledgers, trades, equity
curves, metrics, the report) lives only in the private repository; this
repository keeps a value-free index.
"""

from __future__ import annotations

import copy
import gzip
import hashlib
import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from btc_predictor.backtest.costs import cost_profile
from btc_predictor.backtest.engine import BacktestResult, _bar_available_at, run_backtest
from btc_predictor.backtest.regime_performance import regime_performance_context, run_regime_performance_breakdown
from btc_predictor.backtest.setup_performance import setup_performance_report_from_breakdown
from btc_predictor.backtest.threshold_sweeps import ThresholdSweepSpec, threshold_parameter_sets, threshold_sweep_spec
from btc_predictor.backtest.walk_forward import (
    EXPANDING_SCHEME,
    FoldStrategy,
    TrainingWindow,
    WalkForwardValidation,
    run_walk_forward,
    walk_forward_plan,
    walk_forward_windows,
)
from btc_predictor.config.strategy import StrategyConfig
from btc_predictor.data import OhlcvBar
from btc_predictor.research_backtest import preregistration as prereg
from btc_predictor.research_backtest import runner_metrics as rm
from btc_predictor.research_backtest.entry_composer import (
    EntryComposer,
    EntryComposerInputs,
    CAUSE_DECISION_PRICE_BAR_MISSING,
    EntryDecision,
    is_daily_decision_instant,
    next_decision_instant,
)
from btc_predictor.research_backtest.management_composer import (
    FOLLOWUP_ADD_DROPPED,
    FOLLOWUP_ADD_EMITTED,
    REASON_ADD_PENDING_TRAIL,
    ManagementComposer,
)
from btc_predictor.research_backtest.replay_inputs import canonical_json_bytes
from btc_predictor.research_backtest.runner_shared import ShareStatistics, dump_store_pickle, load_store_pickle

RUNNER_VERSION = "RBT007_RESEARCH_BACKTEST_RUNNER_V1"
RUNNER_TICKET = "RUN_FIRST_RESEARCH_BACKTEST_V1"
CHAMPION = "champion"
HEADLINE = "HEADLINE"
WALK_FORWARD = "WALK_FORWARD"
SWEEP = "SWEEP"
ABLATION = "ABLATION"
GOLDEN = "GOLDEN"
RUN_KINDS = (HEADLINE, WALK_FORWARD, SWEEP, ABLATION, GOLDEN)
HOURS_PER_DAY = 24
FOLD_BARS = prereg.FOLD_TEST_PERIODS * HOURS_PER_DAY  # ruling 4: 182 days of 24 hourly bars
_DAY = timedelta(days=1)
_HOUR = timedelta(hours=1)


class RunnerRefused(ValueError):
    """The runner refuses: a frozen input, check or configuration does not hold."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


# --- the variants: the champion, the sweep candidates and the ablation ---------------------------


@dataclass(frozen=True)
class Variant:
    """One registered configuration and what the preregistration says it is."""

    variant_id: str
    config: StrategyConfig
    role: str  # CHAMPION, SWEEP or ABLATION
    parameter: str | None = None
    value: str | None = None
    sweep_index: int | None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "role": self.role,
            "parameter": self.parameter,
            "value": self.value,
            "sweep_index": self.sweep_index,
            "config_metadata": dict(self.config.run_metadata()),
        }


def _with_paths(base: Mapping[str, Any], updates: Mapping[str, Any], parameter_set_id: str) -> StrategyConfig:
    data = copy.deepcopy(dict(base))
    for path, value in updates.items():
        prereg._set_path(data, path, value)
    data["identity"]["parameter_set_id"] = parameter_set_id
    return StrategyConfig.from_mapping(data)


def _configured_number(base: Mapping[str, Any], path: str, value: Decimal) -> int | float:
    # the same typing RBT-006 used to check each candidate (clarification 3a)
    configured = prereg._get_path(base, path)
    if type(configured) is int and value == value.to_integral_value():
        return int(value)
    return float(value)


def sweep_specs(frozen_sweeps: Sequence[Mapping[str, Any]], champion: StrategyConfig) -> list[tuple[Mapping[str, Any], ThresholdSweepSpec | None]]:
    """Each frozen sweep with its BTC-185 spec, rebuilt and checked against the frozen record."""

    out: list[tuple[Mapping[str, Any], ThresholdSweepSpec | None]] = []
    for record in frozen_sweeps:
        if record["status"] != "SWEPT":
            out.append((record, None))
            continue
        frozen = record["spec"]
        spec = threshold_sweep_spec(
            parameter=frozen["parameter"],
            candidate_values=[Decimal(value) for value in record["candidate_values"]],
            baseline_value=Decimal(record["configured_value"]),
            parameter_paths=record["parameter_paths"],
            base_config_metadata=champion.run_metadata(),
            objective_metric=frozen["objective_metric"],
            plateau_tolerance=Decimal(frozen["plateau_tolerance"]),
        )
        if json.loads(canonical_json_bytes(spec.as_record())) != json.loads(canonical_json_bytes(frozen)):
            raise RunnerRefused("SWEEP_REFUSED", f"the rebuilt {record['parameter']} spec differs from the frozen one")
        out.append((record, spec))
    return out


def sweep_variants(frozen_sweeps: Sequence[Mapping[str, Any]], champion: StrategyConfig) -> list[Variant]:
    """Every kept candidate of every swept value, in sweep and candidate order."""

    base = prereg._configuration_mapping()
    variants: list[Variant] = []
    for index, (record, spec) in enumerate(sweep_specs(frozen_sweeps, champion)):
        if spec is None:
            continue
        for parameter_set in threshold_parameter_sets(spec):
            updates = {path: _configured_number(base, path, parameter_set.value) for path in parameter_set.parameter_paths}
            config = _with_paths(base, updates, parameter_set.parameter_set_id)
            if dict(config.run_metadata()) != dict(parameter_set.config_metadata):
                raise RunnerRefused("SWEEP_REFUSED", "a candidate's configuration identity differs from its parameter set")
            variants.append(
                Variant(parameter_set.parameter_set_id, config, SWEEP, parameter_set.parameter, str(parameter_set.value), index)
            )
    return variants


def ablation_variant(frozen: Mapping[str, Any], champion: StrategyConfig) -> Variant:
    """The frozen Hold-without-Momentum-Persistence variant (policy V7 sections 6A.10 and 8)."""

    if prereg.ablation_variant(champion) != dict(frozen):
        raise RunnerRefused("ABLATION_REFUSED", "the rebuilt ablation variant differs from the frozen one")
    base = prereg._configuration_mapping()
    updates = {f"scoring_weights.hold_score.{key}": float(Decimal(value)) for key, value in frozen["variant_weights"].items()}
    config = _with_paths(base, updates, frozen["variant_id"])
    weights = {key: Decimal(str(value)) for key, value in config.scoring_weights.hold_score.items()}
    if weights != {key: Decimal(value) for key, value in frozen["variant_weights"].items()}:
        raise RunnerRefused("ABLATION_REFUSED", "the variant configuration does not hold the frozen weights")
    return Variant(frozen["variant_id"], config, ABLATION)


@dataclass
class Registry:
    """The configurations the preregistration lists, by identity: nothing else reaches a composer."""

    champion: StrategyConfig
    variants: dict[str, Variant] = field(default_factory=dict)

    def add(self, variant: Variant) -> None:
        if variant.variant_id in self.variants:
            raise RunnerRefused("REGISTRY_REFUSED", f"{variant.variant_id} is registered twice")
        self.variants[variant.variant_id] = variant

    def require(self, variant: Variant) -> None:
        registered = self.variants.get(variant.variant_id)
        if registered is not variant:
            raise RunnerRefused("REGISTRY_REFUSED", f"{variant.variant_id} is not a registered configuration")


class RegisteredEntryComposer(EntryComposer):
    """The unchanged RBT-004 composer, given a registered configuration (ruling 2).

    The composer accepts only the champion's identity, so it is built with the
    champion's configuration and then given the registered one, which differs
    only in the swept values or the ablated weights and in its identity. It
    also keeps each ARM_ENTRY decision, by its intent's source id, for the
    regime and setup breakdowns and the cross-venue matching, and starts
    holding the venue's continuous history before its window (ruling 7).
    """

    def __init__(
        self, inputs: EntryComposerInputs, *, variant: Variant, registry: Registry, history: Sequence[Any] = ()
    ) -> None:
        registry.require(variant)
        super().__init__(inputs, strategy_config=registry.champion)
        if variant.config is not registry.champion:
            self._config = variant.config
            self._metadata = dict(variant.config.run_metadata())
        self.variant = variant
        self.armed: dict[str, EntryDecision] = {}
        # Ruling 7: the market memory (smoothed regime, capitulation flags) the
        # composer reads from its own earlier rows starts as the continuous history.
        self._ledger = list(history)
        self.seeded = len(self._ledger)

    def run_rows(self) -> tuple[Any, ...]:
        """The rows this run composed, without the seeded history."""

        return tuple(self._ledger[self.seeded :])

    def run_records(self) -> list[dict[str, Any]]:
        return [row.as_record() for row in self.run_rows()]

    def decide(self, as_of: datetime, *, position_open: bool = False) -> EntryDecision:
        decision = super().decide(as_of, position_open=position_open)
        if decision.intent is not None:
            self.armed[decision.intent.source_id] = decision
        return decision


class RecordingEntryComposer(RegisteredEntryComposer):
    """The registered composer, keeping every decision it composes for the audit's replay (ruling 3a)."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.decisions: dict[datetime, EntryDecision] = {}

    def decide(self, as_of: datetime, *, position_open: bool = False) -> EntryDecision:
        decision = super().decide(as_of, position_open=position_open)
        self.decisions[decision.row.decision_at] = decision
        return decision


MANAGEMENT_INPUTS = ("lifecycle", "nav", "armed", "prior_flow")


class RecordingManagementComposer(ManagementComposer):
    """The unchanged RBT-005 composer, keeping each management call's inputs and decision for the audit."""

    def __init__(self, entry: EntryComposer) -> None:
        super().__init__(entry)
        self.calls: dict[datetime, dict[str, Any]] = {}
        self.managed: dict[datetime, Any] = {}

    def decide(self, decision: EntryDecision, *, lifecycle: Any, nav: Decimal, armed: Any, prior_flow: Any | None) -> Any:
        instant = decision.row.decision_at
        self.calls[instant] = {"lifecycle": lifecycle, "nav": nav, "armed": armed, "prior_flow": prior_flow}
        managed = super().decide(decision, lifecycle=lifecycle, nav=nav, armed=armed, prior_flow=prior_flow)
        self.managed[instant] = managed
        return managed


# --- windows and plans ------------------------------------------------------------------------


def venue_bars(inputs: EntryComposerInputs) -> tuple[OhlcvBar, ...]:
    return tuple(sorted(inputs.dataset.price_bars, key=lambda bar: bar.timestamp))


def bars_before(bars: Sequence[OhlcvBar], end_exclusive: datetime) -> tuple[OhlcvBar, ...]:
    """The bars the engine makes available strictly before ``end_exclusive``."""

    return tuple(bar for bar in bars if _bar_available_at(bar) < end_exclusive)


def count_before(bars: Sequence[OhlcvBar], instant: datetime) -> int:
    return sum(1 for bar in bars if _bar_available_at(bar) < instant)


def one_fold_plan(config: StrategyConfig, bars: Sequence[OhlcvBar], first: datetime) -> Any:
    """BTC-182 split for one window: everything before ``first`` trains, the rest is one fold."""

    train = count_before(bars, first)
    test = len(bars) - train
    if train < 1 or test < 1:
        raise RunnerRefused("WINDOW_REFUSED", f"no bar before or from {first.isoformat()}")
    return walk_forward_plan(config, scheme=EXPANDING_SCHEME, train_periods=train, test_periods=test, step_periods=test, embargo_periods=0)


def fold_plan_bars(config: StrategyConfig, bars: Sequence[OhlcvBar], evaluation_start: datetime, fold_bars: int = FOLD_BARS) -> Any:
    """Ruling 4: expanding folds of 4,368 hourly bars from the evaluation start, no embargo."""

    train = count_before(bars, evaluation_start)
    if train < 1:
        raise RunnerRefused("WINDOW_REFUSED", "no bar before the evaluation start")
    return walk_forward_plan(
        config, scheme=EXPANDING_SCHEME, train_periods=train, test_periods=fold_bars, step_periods=fold_bars, embargo_periods=0
    )


def first_decision_at(available: datetime) -> datetime:
    """The first decision instant composed from a bar available at ``available``.

    A fold whose first bar becomes available after midnight (after omitted
    hours, ruling 4) composes its first decision at the next midnight, as the
    entry composer's ``step`` does; its history is the rows before that instant.
    """

    return available if is_daily_decision_instant(available) else next_decision_instant(available)


def fold_decisions(bars: Sequence[OhlcvBar], plan: Any, evaluation_start: datetime) -> list[dict[str, Any]]:
    """Each fold's first and last decision instant, from its bars' engine availability.

    Each fold also records the hourly bars omitted between the evaluation
    start and its first bar, and its end: ruling 4's folds count bars, so
    omitted hours shift them from the preregistered daily folds.
    """

    train = plan.train_periods
    folds = []
    for window in walk_forward_windows([bar.timestamp for bar in bars], plan=plan):
        available = [_bar_available_at(bar) for bar in bars[window.test_start_index : window.test_stop_index]]
        instants = [moment for moment in available if moment.hour == 0 and moment.minute == 0]
        before_start = (available[0] - evaluation_start) // _HOUR - (window.test_start_index - train)
        before_end = (available[-1] + _HOUR - evaluation_start) // _HOUR - (window.test_stop_index - train)
        folds.append(
            {
                "fold_number": window.fold_number,
                "first_decision": instants[0].isoformat() if instants else None,
                "last_decision": instants[-1].isoformat() if instants else None,
                "decisions": len(instants),
                "bars": window.test_periods,
                "omitted_hours_before_start": before_start,
                "omitted_hours_before_end": before_end,
            }
        )
    return folds


# --- one run ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class RunSpec:
    kind: str
    venue: str
    variant: str
    cost_rung: str
    scenario: str | None = None

    @property
    def run_id(self) -> str:
        parts = [self.kind, self.venue, self.variant, self.cost_rung]
        if self.scenario is not None:
            parts.append(self.scenario)
        return ":".join(parts)

    def as_record(self) -> dict[str, Any]:
        return {"kind": self.kind, "venue": self.venue, "variant": self.variant, "cost_rung": self.cost_rung, "scenario": self.scenario}


@dataclass
class RunContext:
    """What every run reads: the frozen inputs, the registered variants and the windows."""

    inputs: Mapping[str, EntryComposerInputs]
    registry: Registry
    evaluation: Mapping[str, tuple[datetime, datetime]]  # venue -> (evaluation start, last decision)
    golden: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    statistics: ShareStatistics = field(default_factory=ShareStatistics)
    # ruling 4's fold length; only synthetic tests shorten it, and the report records it
    fold_bars: int = FOLD_BARS
    # ruling 7: per venue, the champion's continuous decision rows from the schedule's start
    history: Mapping[str, Sequence[Any]] = field(default_factory=dict)
    # the decision schedule the history composes; only synthetic tests shorten it
    schedule: Sequence[datetime] = field(default_factory=prereg.decision_schedule)
    # review F3: what every checkpoint binds (the code, the preregistration, the dataset, the windows)
    binding: Mapping[str, Any] = field(default_factory=dict)
    _history_digests: dict[str, tuple[Any, str]] = field(default_factory=dict, repr=False, compare=False)

    def seed(self, venue: str, first: datetime) -> tuple[Any, ...]:
        history = self.history.get(venue)
        if not history:
            raise RunnerRefused("HISTORY_REFUSED", f"{venue} has no continuous history")
        rows = tuple(row for row in history if row.decision_at < first)
        if (rows and rows[-1].decision_at != first - _DAY) or (not rows and history[0].decision_at != first):
            raise RunnerRefused("HISTORY_REFUSED", f"{venue}'s history does not reach {first.isoformat()}")
        return rows

    def history_sha256(self, venue: str) -> str:
        rows = self.history.get(venue, ())
        known = self._history_digests.get(venue)
        if known is None or known[0] is not rows:
            known = (rows, hashlib.sha256(canonical_json_bytes([row.as_record() for row in rows])).hexdigest())
            self._history_digests[venue] = known
        return known[1]


@dataclass
class RunOutcome:
    spec: RunSpec
    record: dict[str, Any]
    validation: WalkForwardValidation | None = None
    result: BacktestResult | None = None
    composers: list[ManagementComposer] = field(default_factory=list)
    snapshot: RunSnapshot | None = None


MEMORY_FIELDS = ("regime", "capitulation_flag_state")


def memory_check(context: RunContext, venue: str, composers: Sequence[ManagementComposer]) -> dict[str, Any]:
    """Ruling 7's check: every composed row's market memory equals the continuous history's.

    The regime (its score, the smoothed score and the classification) and the
    capitulation flag state depend on the market alone, so a run's row at an
    instant must carry the history's values exactly. A variant that reached
    that memory would fail here.
    """

    return memory_of_rows(context, venue, [strategy.entry.run_rows() for strategy in composers])


def memory_of_rows(context: RunContext, venue: str, row_sets: Sequence[Sequence[Any]]) -> dict[str, Any]:
    """:func:`memory_check` over each composer's own rows (a run snapshot's, review RR2)."""

    history = {row.decision_at: row for row in context.history.get(venue, ())}
    compared = 0
    mismatches = []
    for rows in row_sets:
        for row in rows:
            reference = history.get(row.decision_at)
            if reference is None:
                continue
            compared += 1
            ours, theirs = row.as_record(), reference.as_record()
            if any(ours[name] != theirs[name] for name in MEMORY_FIELDS):
                mismatches.append(row.decision_at.isoformat())
    composed = sum(len(rows) for rows in row_sets)
    # review F3: every composed row must have its history row; an empty history never matches
    return {"compared_rows": compared, "mismatches": mismatches, "matches_history": not mismatches and compared > 0 and compared == composed}


def _contexts(validation: WalkForwardValidation, composers: Sequence[ManagementComposer]) -> list[Any]:
    """One BTC-183 entry context per filled trade, from its ARM_ENTRY decision's composition."""

    contexts = []
    for fold, strategy in zip(validation.folds, composers, strict=True):
        entry = strategy.entry
        for trade in fold.result.trades:
            source = trade.fills[0].source_event_id
            decision = entry.armed[source]
            results = decision.composition.run.results
            contexts.append(
                regime_performance_context(
                    fold_number=fold.fold_number,
                    entry_source_id=source,
                    decision_at=decision.row.decision_at,
                    evidence_available_at=decision.row.decision_at,
                    regime=results["regime_classification"],
                    volatility=results["volatility_score"],
                    setup=results[f"setup:{decision.row.setup}"],
                )
            )
    return contexts


def _drop_embedded(record: Mapping[str, Any], key: str) -> dict[str, Any]:
    """A report record without the validation (or breakdown) it embeds, named by its digests instead."""

    embedded = record[key]
    out = {name: value for name, value in record.items() if name != key}
    out[f"{key}_digests"] = {name: embedded[name] for name in ("validation_id", "report_id", "evidence_digest") if name in embedded}
    return out


@dataclass(frozen=True)
class ComposerSnapshot:
    """One run composer's rows, as its run's record reads them (review RR2).

    The entry rows are the run's own; the composer was seeded with the
    context's continuous history before ``first`` (ruling 7).
    """

    first: datetime
    entry_rows: tuple[Any, ...]
    management_rows: tuple[Any, ...]
    followups: tuple[Any, ...]

    @classmethod
    def of(cls, strategy: ManagementComposer, first: datetime) -> ComposerSnapshot:
        return cls(first, tuple(strategy.entry.run_rows()), tuple(strategy.ledger), tuple(strategy.add_followups))

    def armed(self) -> dict[str, datetime]:
        """Each ARM_ENTRY row's decision instant, by its intent's source id."""

        return {row.intent["source_id"]: row.decision_at for row in self.entry_rows if row.intent is not None}


@dataclass(frozen=True)
class RunSnapshot:
    """What a run's record is built from: its engine objects and its composers' rows (review RR2).

    It is written beside the record under the same binding; a resumed record
    is read only if this snapshot is complete and gives that record exactly.
    """

    result: BacktestResult | None
    validation: WalkForwardValidation | None
    composers: tuple[ComposerSnapshot, ...]
    trade_contexts: tuple[Any, ...] = ()  # a walk-forward's BTC-183 entry contexts

    def results(self) -> tuple[BacktestResult, ...]:
        if self.validation is None:
            return (self.result,) if self.result is not None else ()
        return tuple(fold.result for fold in self.validation.folds)


def _armed_instants(result: BacktestResult, composer: ComposerSnapshot) -> dict[str, str]:
    armed = composer.armed()
    return {str(index): armed[trade.fills[0].source_event_id].isoformat() for index, trade in enumerate(result.trades)}


def _trade_entries(validation: WalkForwardValidation, composers: Sequence[ComposerSnapshot]) -> list[dict[str, str]]:
    """Per fold, each trade's index and the decision instant of the ARM_ENTRY row that opened it."""

    return [_armed_instants(fold.result, composer) for fold, composer in zip(validation.folds, composers, strict=True)]


def _single_run(spec: RunSpec, context: RunContext, variant: Variant, inputs: EntryComposerInputs, window: Sequence[OhlcvBar], *, first: datetime, record_management: bool, starting_nav: Decimal | None = None) -> tuple[BacktestResult, ManagementComposer]:
    composer = RecordingEntryComposer if record_management else RegisteredEntryComposer
    entry = composer(inputs, variant=variant, registry=context.registry, history=context.seed(spec.venue, first))
    strategy = RecordingManagementComposer(entry) if record_management else ManagementComposer(entry)
    result = run_backtest(
        window,
        strategy=strategy,
        symbol=window[0].symbol,
        starting_nav=starting_nav,
        strategy_config=variant.config,
        cost_profile=spec.cost_rung,
        strategy_id=f"rbt007:{spec.run_id}",
    )
    return result, strategy


def event_counts(results: Iterable[BacktestResult]) -> dict[str, int]:
    """Value-free: the engine's events by type, action and status, with each refusal's reason codes.

    RBT-006 surfaced that the entry-conviction candidate 72 has no risk band
    below 80; its runs report here how many intents the engine refused.
    """

    counts: dict[str, int] = {}
    for result in results:
        for event in result.events:
            key = f"{event.event_type}:{event.action}:{event.status}"
            if event.status == "REFUSED":
                key += ":" + ",".join(event.reason_codes)
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _unaccounted(context: RunContext, venue: str, composers: Sequence[ComposerSnapshot]) -> list[str]:
    """Every cause a run's composers left unaccounted, their seeded history's too, by the composers' own methods."""

    entry: set[str] = set()
    management: set[str] = set()
    for composer in composers:
        ledger = SimpleNamespace(_ledger=[*context.seed(venue, composer.first), *composer.entry_rows])
        entry |= {f"entry:{instant}:{code}" for instant, code in EntryComposer.unaccounted_causes(ledger)}
        managed = SimpleNamespace(_ledger=list(composer.management_rows), _followups=list(composer.followups))
        management |= {f"management:{instant}:{code}" for instant, code in ManagementComposer.unaccounted_causes(managed)}
    return sorted(entry | management)


def run_bars(spec: RunSpec, context: RunContext) -> tuple[OhlcvBar, ...]:
    """The bars a run's engine reads: its window's, or for walk-forward folds every bar before its end."""

    bars = venue_bars(context.inputs[spec.venue])
    first, last = spec_window(spec, context)
    if spec.kind in (WALK_FORWARD, SWEEP):
        return bars_before(bars, last + _DAY)
    return tuple(bar for bar in bars if first <= _bar_available_at(bar) < last + _DAY)


def _fold_runs(spec: RunSpec, context: RunContext, window: Sequence[OhlcvBar]) -> list[tuple[tuple[OhlcvBar, ...], datetime]]:
    """Each fold's engine bars and first decision instant (ruling 4; review F1)."""

    variant = context.registry.variants[spec.variant]
    plan = fold_plan_bars(variant.config, window, context.evaluation[spec.venue][0], context.fold_bars)
    return [
        (tuple(window[item.test_start_index : item.test_stop_index]), first_decision_at(_bar_available_at(window[item.test_start_index])))
        for item in walk_forward_windows([bar.timestamp for bar in window], plan=plan)
    ]


def execute_run(spec: RunSpec, context: RunContext, *, record_management: bool = False) -> RunOutcome:
    """Run one spec and return its record (and, in process, its objects and snapshot)."""

    if spec.kind not in RUN_KINDS:
        raise RunnerRefused("RUN_REFUSED", f"unknown run kind {spec.kind}")
    variant = context.registry.variants[spec.variant]
    inputs = context.inputs[spec.venue]
    window = run_bars(spec, context)
    if spec.kind in (HEADLINE, ABLATION, GOLDEN):
        # one continuous engine run over the window, from flat
        first = spec_window(spec, context)[0]
        golden = spec.kind == GOLDEN
        result, strategy = _single_run(
            spec,
            context,
            variant,
            inputs,
            window,
            first=first,
            record_management=record_management and not golden,
            starting_nav=Decimal(context.golden[spec.scenario]["starting_nav"]) if golden else None,
        )
        snapshot = RunSnapshot(result, None, (ComposerSnapshot.of(strategy, first),))
        return RunOutcome(spec, run_record(spec, context, snapshot), result=result, composers=[strategy], snapshot=snapshot)

    start = context.evaluation[spec.venue][0]
    plan = fold_plan_bars(variant.config, window, start, context.fold_bars)
    composers: list[ManagementComposer] = []
    firsts: list[datetime] = []

    def factory(training: TrainingWindow) -> FoldStrategy:
        first = first_decision_at(_bar_available_at(window[training.window.test_start_index]))
        entry = RegisteredEntryComposer(inputs, variant=variant, registry=context.registry, history=context.seed(spec.venue, first))
        strategy = ManagementComposer(entry)
        composers.append(strategy)
        firsts.append(first)
        return FoldStrategy(strategy=strategy, strategy_id=f"rbt007:{spec.run_id}:fold-{training.window.fold_number}")

    # BTC-185 compares candidates only without a selected BTC-181 profile, whose
    # record carries each candidate's identity; the configuration's own costs are
    # the base rung's, which the runner checks.
    selected = None if spec.kind == SWEEP else spec.cost_rung
    validation = run_walk_forward(
        window, strategy_factory=factory, plan=plan, symbol=window[0].symbol, strategy_config=variant.config, cost_profile=selected
    )
    if selected is None:
        rung = cost_profile(spec.cost_rung, config=variant.config)
        if validation.effective_costs.as_record() != rung.costs.as_record():
            raise RunnerRefused("SWEEP_REFUSED", f"a sweep's costs are not the {spec.cost_rung} rung's")
    snapshot = RunSnapshot(
        None,
        validation,
        tuple(ComposerSnapshot.of(strategy, first) for strategy, first in zip(composers, firsts, strict=True)),
        # BTC-183 and BTC-184 attribute each filled out-of-sample trade (a BTC-182 validation)
        tuple(_contexts(validation, composers)) if spec.kind == WALK_FORWARD else (),
    )
    return RunOutcome(spec, run_record(spec, context, snapshot), validation=validation, composers=composers, snapshot=snapshot)


def run_record(spec: RunSpec, context: RunContext, snapshot: RunSnapshot) -> dict[str, Any]:
    """A run's record, built from its snapshot and the context it binds alone (review RR2).

    The run writes it; a resumed run rebuilds it from the stored snapshot and
    reads the stored record only if the two are equal.
    """

    variant = context.registry.variants[spec.variant]
    first, last = spec_window(spec, context)
    composers = snapshot.composers
    if spec.kind in (HEADLINE, ABLATION, GOLDEN):
        result, (composer,) = snapshot.result, composers
        window = {"first_decision": first.isoformat(), "last_decision": last.isoformat(), "bars": len(result.input_bars)}
        if spec.kind == GOLDEN:
            return _golden_record(spec, context, result, composer, window)
        return {
            "run": spec.as_record(),
            "run_id": spec.run_id,
            "variant": variant.as_record(),
            "window": window,
            "metrics": rm.run_metrics(rm.single_view(result)),
            "result": result.as_record(),
            "entry_ledger": [row.as_record() for row in composer.entry_rows],
            "management_ledger": [row.as_record() for row in composer.management_rows],
            "trade_entries": _armed_instants(result, composer),
            "unaccounted": _unaccounted(context, spec.venue, composers),
            "memory": memory_of_rows(context, spec.venue, [composer.entry_rows]),
            "engine_events": event_counts([result]),
            "binding": run_binding(spec, context),
        }

    validation = snapshot.validation
    window_bars = run_bars(spec, context)
    plan = fold_plan_bars(variant.config, window_bars, first, context.fold_bars)
    view = rm.validation_view(validation)
    record = {
        "run": spec.as_record(),
        "run_id": spec.run_id,
        "variant": variant.as_record(),
        "plan": plan.as_record(),
        "folds": fold_decisions(window_bars, plan, first),
        "metrics": rm.run_metrics(view),
        "fold_metrics": rm.fold_metrics(view),
        "validation": validation.as_record(),
        "entry_ledgers": [[row.as_record() for row in composer.entry_rows] for composer in composers],
        "management_ledgers": [[row.as_record() for row in composer.management_rows] for composer in composers],
        "trade_entries": _trade_entries(validation, composers),
        "unaccounted": _unaccounted(context, spec.venue, composers),
        "memory": memory_of_rows(context, spec.venue, [composer.entry_rows for composer in composers]),
        "engine_events": event_counts(snapshot.results()),
        "binding": run_binding(spec, context),
    }
    if spec.kind == WALK_FORWARD:
        breakdown = run_regime_performance_breakdown(validation, list(snapshot.trade_contexts))
        record["regime_breakdown"] = _drop_embedded(breakdown.as_record(), "validation")
        record["setup_report"] = _drop_embedded(setup_performance_report_from_breakdown(breakdown).as_record(), "source_breakdown")
    return record


def snapshot_refusals(spec: RunSpec, context: RunContext, snapshot: Any) -> list[str]:
    """Why a run's snapshot is not a complete run of its bound window (review RR2); empty if it is.

    Each engine run must have read exactly the bars its window gives, and its
    composer been seeded at its first decision. The entry ledger must hold a
    row at every daily decision instant from the engine's first callback to
    its last (RBT-004 records each crossed instant), the management ledger a
    row exactly where the entry row has the position open (RBT-005 decides,
    or records the missing-bar row, while a position is open), and the
    intents the ledgers and follow-ups returned must be exactly the ones the
    engine received. Review N3: every TRAIL that left an ADD pending has
    exactly one follow-up, at the engine's next callback, unless the run ended
    first (RBT-005 resolves it there, owner ruling 1); an emitted ADD is that
    pending ADD's intent, and a dropped one has its reasons and no intent.
    """

    if not isinstance(snapshot, RunSnapshot) or not all(isinstance(item, ComposerSnapshot) for item in snapshot.composers):
        return ["not a run snapshot"]
    window = run_bars(spec, context)
    if spec.kind in (HEADLINE, ABLATION, GOLDEN):
        if snapshot.validation is not None or snapshot.result is None or len(snapshot.composers) != 1:
            return ["not a single engine run"]
        expected = [(window, spec_window(spec, context)[0])]
    else:
        if snapshot.result is not None or snapshot.validation is None:
            return ["not a walk-forward validation"]
        expected = _fold_runs(spec, context, window)
        if len(expected) != len(snapshot.validation.folds) or len(snapshot.composers) != len(expected):
            return ["not one composer per fold"]
    if spec.kind != WALK_FORWARD and snapshot.trade_contexts:
        return ["entry contexts outside a walk-forward"]
    problems = []
    for number, (result, composer, (bars, first)) in enumerate(zip(snapshot.results(), snapshot.composers, expected, strict=True), start=1):
        if tuple(result.input_bars) != tuple(bars):
            problems.append(f"engine run {number} read other bars than its window's")
        if composer.first != first:
            problems.append(f"engine run {number}'s composer was not seeded at its first decision")
        crossed: list[datetime] = []
        if bars:
            instant, end = first_decision_at(_bar_available_at(bars[0])), _bar_available_at(bars[-1])
            while instant <= end:
                crossed.append(instant)
                instant += _DAY
        if [row.decision_at for row in composer.entry_rows] != crossed:
            problems.append(f"engine run {number}'s entry ledger is not one row per decision instant crossed")
        if [row.decision_at for row in composer.management_rows] != [row.decision_at for row in composer.entry_rows if row.position_open]:
            problems.append(f"engine run {number}'s management ledger is not one row per instant with the position open")
        callbacks = [_bar_available_at(bar) for bar in bars]
        pending = []
        for row in composer.management_rows:
            if REASON_ADD_PENDING_TRAIL in row.reasons:
                resolved = next((at for at in callbacks if at > row.decision_at), None)
                if resolved is not None:  # else the run ended before the ADD's callback
                    pending.append((row, resolved))
        if [(item.decision_at, item.resolved_at) for item in composer.followups] != [(row.decision_at, resolved) for row, resolved in pending]:
            problems.append(f"engine run {number}'s follow-ups are not one per pending ADD whose next callback came")
        else:
            for item, (row, _resolved) in zip(composer.followups, pending, strict=True):
                emitted = item.outcome == FOLLOWUP_ADD_EMITTED and not item.reasons and item.intent == row.add["intent"]
                dropped = item.outcome == FOLLOWUP_ADD_DROPPED and bool(item.reasons) and item.intent is None
                if not (emitted or dropped):
                    problems.append(f"engine run {number}'s follow-up at {item.resolved_at.isoformat()} is not its pending ADD's resolution")
        returned = [item.intent["source_id"] for item in (*composer.entry_rows, *composer.management_rows, *composer.followups) if item.intent is not None]
        received = {event.source_id for event in result.events if event.event_type == "INTENT"}
        if len(returned) != len(set(returned)) or set(returned) != received:
            problems.append(f"engine run {number}'s intents are not the ones its ledgers returned")
    return problems


def golden_window(scenario: Mapping[str, Any]) -> tuple[datetime, datetime]:
    """The decision instants at the close of each golden session day: (first, last)."""

    first_day = date.fromisoformat(scenario["period"]["start"])
    last_day = date.fromisoformat(scenario["period"]["end"])
    first = datetime(first_day.year, first_day.month, first_day.day, tzinfo=UTC) + _DAY
    last = datetime(last_day.year, last_day.month, last_day.day, tzinfo=UTC) + _DAY
    return first, last


def _golden_record(
    spec: RunSpec, context: RunContext, result: BacktestResult, composer: ComposerSnapshot, window: Mapping[str, Any]
) -> dict[str, Any]:
    scenario = context.golden[spec.scenario]
    rows = {row.decision_at: row for row in composer.entry_rows}
    beside = []
    for scripted in scenario["plan"]["decisions"]:
        day = date.fromisoformat(scripted["on"])
        instant = datetime(day.year, day.month, day.day, tzinfo=UTC) + _DAY
        row = rows.get(instant)
        managed = next((item for item in composer.management_rows if item.decision_at == instant), None)
        beside.append(
            {
                "on": scripted["on"],
                "scripted_action": scripted["action"],
                "decision_at": instant.isoformat(),
                "entry_outcome": row.outcome if row is not None else None,
                "entry_reasons": list(row.reasons) if row is not None else None,
                "management_outcome": managed.outcome if managed is not None else None,
            }
        )
    return {
        "run": spec.as_record(),
        "run_id": spec.run_id,
        "window": dict(window),
        "engine_reason_codes": list(result.reason_codes),
        "engine_refused": "BACKTEST_INTENT_REFUSED" in result.reason_codes,
        "engine_events": event_counts([result]),
        # review RR4: a golden run's unaccounted causes are gated like every other run's
        "unaccounted": _unaccounted(context, spec.venue, [composer]),
        "decisions_beside_scripted": beside,
        "result": result.as_record(),
        "entry_ledger": [row.as_record() for row in composer.entry_rows],
        "management_ledger": [row.as_record() for row in composer.management_rows],
        "memory": memory_of_rows(context, spec.venue, [composer.entry_rows]),
        "binding": run_binding(spec, context),
    }


# --- checkpoint files ---------------------------------------------------------------------------


def run_file(directory: Path, spec: RunSpec) -> Path:
    name = hashlib.sha256(spec.run_id.encode()).hexdigest()[:24]
    return Path(directory) / "runs" / f"{name}.json.gz"


def run_snapshot_file(directory: Path, spec: RunSpec) -> Path:
    return run_file(directory, spec).with_name(run_file(directory, spec).name.replace(".json.gz", ".snapshot.pickle.gz"))


def _replace_whole(path: Path, data: bytes) -> None:
    partial = path.with_name(path.name + ".partial")
    partial.write_bytes(data)
    partial.replace(path)


def write_run(directory: Path, outcome: RunOutcome) -> Path:
    """Write a run's snapshot, then its record, each whole, then renamed: a resumed run reads complete records only.

    The snapshot goes first, under the record's binding, so a record on disk
    always has the snapshot it is rebuilt from (review RR2). The record names
    the snapshot file's SHA-256 (review N1).
    """

    if outcome.snapshot is None:
        raise RunnerRefused("CHECKPOINT_REFUSED", f"{outcome.spec.run_id} has no snapshot to write")
    path = run_file(directory, outcome.spec)
    path.parent.mkdir(parents=True, exist_ok=True)
    stored = {"run_id": outcome.spec.run_id, "binding": json.loads(canonical_json_bytes(outcome.record["binding"])), "snapshot": outcome.snapshot}
    snapshot = gzip.compress(dump_store_pickle(stored), mtime=0)
    _replace_whole(run_snapshot_file(directory, outcome.spec), snapshot)
    record = {**outcome.record, SNAPSHOT_DIGEST: hashlib.sha256(snapshot).hexdigest()}
    _replace_whole(path, gzip.compress(canonical_json_bytes(record), mtime=0))
    return path


def configuration_sha256(config: StrategyConfig) -> str:
    """The whole configuration's digest: its frozen dataclass representation."""

    return hashlib.sha256(repr(config).encode()).hexdigest()


def run_binding(spec: RunSpec, context: RunContext) -> dict[str, Any]:
    """What a run record holds, so a resumed run never reads another one's (review F3)."""

    variant = context.registry.variants[spec.variant]
    first, last = spec_window(spec, context)
    return {
        "context": dict(context.binding),
        "run": spec.as_record(),
        "variant": variant.as_record(),
        "configuration_sha256": configuration_sha256(variant.config),
        "window": [first.isoformat(), last.isoformat()],
        "fold_bars": context.fold_bars,
        "starting_nav": context.golden[spec.scenario]["starting_nav"] if spec.kind == GOLDEN else None,
        "history_sha256": context.history_sha256(spec.venue),
    }


SNAPSHOT_DIGEST = "snapshot_sha256"  # review N1: the stored record's name for its snapshot file's digest
_SINGLE_KEYS = ("run", "run_id", "variant", "window", "metrics", "result", "entry_ledger", "management_ledger", "trade_entries", "unaccounted", "memory", "engine_events", "binding")
_FOLDED_KEYS = ("run", "run_id", "variant", "plan", "folds", "metrics", "fold_metrics", "validation", "entry_ledgers", "management_ledgers", "trade_entries", "unaccounted", "memory", "engine_events", "binding")
RECORD_KEYS = {
    HEADLINE: _SINGLE_KEYS,
    ABLATION: _SINGLE_KEYS,
    WALK_FORWARD: (*_FOLDED_KEYS, "regime_breakdown", "setup_report"),
    SWEEP: _FOLDED_KEYS,
    GOLDEN: ("run", "run_id", "window", "engine_reason_codes", "engine_refused", "engine_events", "unaccounted", "decisions_beside_scripted", "result", "entry_ledger", "management_ledger", "memory", "binding"),
}


def read_run(directory: Path, spec: RunSpec, context: RunContext, *, binding: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    """A run's complete record, only if it is this run's under this binding and its snapshot gives it; None if not written.

    ``binding`` is the run's binding under ``context`` unless a test gives
    another. Review RR2: the run's snapshot, stored under the same binding,
    must be a complete run of the bound window (:func:`snapshot_refusals`),
    and the record rebuilt from it must equal the stored record byte for byte.
    Review N1: the snapshot file must have the digest the record names before
    it is read, and it is read with only the classes the store files hold.
    The record is returned as the run gave it, without that digest.
    """

    import pickle

    binding = run_binding(spec, context) if binding is None else binding
    path = run_file(directory, spec)
    if not path.exists():
        return None
    try:
        record = json.loads(gzip.decompress(path.read_bytes()))
    except (OSError, EOFError, ValueError) as error:
        raise RunnerRefused("CHECKPOINT_REFUSED", f"{path.name} is not a readable record: {error}") from error
    if not isinstance(record, dict) or record.get("run_id") != spec.run_id:
        raise RunnerRefused("CHECKPOINT_REFUSED", f"{path.name} does not hold {spec.run_id}")
    if record.get("binding") != json.loads(canonical_json_bytes(binding)):
        raise RunnerRefused("CHECKPOINT_REFUSED", f"{path.name} was written under another binding")
    missing = [key for key in (*RECORD_KEYS[spec.kind], SNAPSHOT_DIGEST) if key not in record]
    if missing:
        raise RunnerRefused("CHECKPOINT_REFUSED", f"{path.name} lacks {missing}")
    snapshot_path = run_snapshot_file(directory, spec)
    try:
        snapshot = snapshot_path.read_bytes()
    except OSError as error:
        raise RunnerRefused("CHECKPOINT_REFUSED", f"{path.name} has no readable snapshot: {error}") from error
    if hashlib.sha256(snapshot).hexdigest() != record.pop(SNAPSHOT_DIGEST):
        raise RunnerRefused("CHECKPOINT_REFUSED", f"{snapshot_path.name} is not the snapshot {path.name} names")
    try:
        stored = load_store_pickle(gzip.decompress(snapshot))
    except (OSError, EOFError, pickle.UnpicklingError, AttributeError, ValueError, TypeError) as error:
        raise RunnerRefused("CHECKPOINT_REFUSED", f"{path.name} has no readable snapshot: {error}") from error
    if not isinstance(stored, dict) or stored.get("run_id") != spec.run_id or stored.get("binding") != record["binding"]:
        raise RunnerRefused("CHECKPOINT_REFUSED", f"{snapshot_path.name} is not {spec.run_id}'s under this binding")
    problems = snapshot_refusals(spec, context, stored.get("snapshot"))
    if problems:
        raise RunnerRefused("CHECKPOINT_REFUSED", f"{snapshot_path.name} is not a complete run: {'; '.join(problems)}")
    try:
        rebuilt = canonical_json_bytes(run_record(spec, context, stored["snapshot"]))
    except RunnerRefused:
        raise
    except Exception as error:  # anything an incomplete snapshot makes an owner raise
        raise RunnerRefused("CHECKPOINT_REFUSED", f"{path.name}'s snapshot does not give a record: {error}") from error
    if rebuilt != canonical_json_bytes(record):
        raise RunnerRefused("CHECKPOINT_REFUSED", f"{path.name} is not the record its snapshot gives")
    return record


# --- the frozen inputs and their checks -----------------------------------------------------------

PREREGISTRATION_PATH = prereg.ARTIFACT_DIRECTORY / prereg.PREREGISTRATION_FILE
PREREGISTRATION_DIGEST_PATH = prereg.ARTIFACT_DIRECTORY / prereg.PREREGISTRATION_DIGEST_FILE
GOLDEN_FIXTURE_PATH = Path("btc_predictor") / "tests" / "golden" / "btc_golden_scenarios_v1.json"
STRATEGY_CONFIG_PATH = Path("btc_predictor") / "config" / "strategy" / "default.toml"
RUNNER_MODULES = ("runner.py", "runner_metrics.py", "runner_report.py", "runner_shared.py")


@dataclass(frozen=True)
class FrozenInputs:
    inputs: Mapping[str, EntryComposerInputs]
    private_commit: str
    index_sha256: str


def load_frozen_inputs(store: Any) -> FrozenInputs:
    """RBT-003's frozen dataset, under the same checks as the RBT-006 freeze.

    The private commit must hold the dataset as stored, its index must equal
    the public index byte for byte, and its frozen inputs must rebuild the
    stored manifests.
    """

    from btc_predictor.research_backtest import dataset_build as build

    stored = build.load_dataset(store)
    private = build.private_commit(store, stored)
    index_bytes = (build.PUBLIC_REPOSITORY / build.INDEX_PATH).read_bytes()
    if index_bytes != build.dataset_index_bytes(stored, private_commit=private):
        raise RunnerRefused("DATASET_REFUSED", "the public index is not the stored dataset's index")
    loaded = build.load_build_evidence(store)
    rows = build.frozen_rows(stored)
    datasets = build.build_replay_datasets(rows, loaded)
    if datasets.manifests() != stored.manifests:
        raise RunnerRefused("DATASET_REFUSED", "the frozen inputs do not rebuild the stored manifests")
    launches = prereg.etf_fund_launches(rows["etf_flows"], evidence_sha256=stored.record["inputs"]["etf_flows"]["sha256"])
    inputs = {dataset.venue.venue_id: datasets.extended.entry_composer_inputs(dataset, etf_fund_launches=launches) for dataset in datasets.venues}
    return FrozenInputs(inputs, private, hashlib.sha256(index_bytes).hexdigest())


def read_preregistration(repository: Path) -> dict[str, Any]:
    """The committed preregistration, checked against its digest file."""

    data = (repository / PREREGISTRATION_PATH).read_bytes()
    digest = (repository / PREREGISTRATION_DIGEST_PATH).read_text().split()[0]
    if hashlib.sha256(data).hexdigest() != digest:
        raise RunnerRefused("PREREGISTRATION_REFUSED", "the preregistration does not match its digest file")
    record = json.loads(data)
    if record.get("ticket") != prereg.PREREGISTRATION_TICKET or record.get("preregistration_version") != prereg.PREREGISTRATION_VERSION:
        raise RunnerRefused("PREREGISTRATION_REFUSED", "not the RBT-006 preregistration")
    return record


def verify_preregistration(record: Mapping[str, Any], champion: StrategyConfig, frozen: FrozenInputs | None = None) -> None:
    """Every frozen choice, re-derived from the code the runner checked is frozen, equals the record."""

    if dict(record["champion"]["base_identity"]) != dict(champion.run_metadata()):
        raise RunnerRefused("PREREGISTRATION_REFUSED", "the configuration is not the frozen champion")
    checks = {
        "threshold_sweeps.sweeps": (record["threshold_sweeps"]["sweeps"], prereg.sweep_grid(champion)),
        "ablation": (record["ablation"], prereg.ablation_variant(champion)),
        "report.metric_spec": (record["report"]["metric_spec"], prereg.metric_definitions()),
        "report.metric_spec_sha256": (record["report"]["metric_spec_sha256"], prereg.metric_definitions_sha256()),
        "cost_ladder.rungs": (record["cost_ladder"]["rungs"], prereg._cost_ladder(champion)),
    }
    for name, (frozen_value, derived) in checks.items():
        if json.loads(canonical_json_bytes(frozen_value)) != json.loads(canonical_json_bytes(derived)):
            raise RunnerRefused("PREREGISTRATION_REFUSED", f"{name} differs from the frozen record")
    schedule = prereg.decision_schedule()
    expected = {"first": schedule[0].isoformat(), "last": schedule[-1].isoformat(), "instants": len(schedule)}
    if {key: record["decision_schedule"][key] for key in expected} != expected:
        raise RunnerRefused("PREREGISTRATION_REFUSED", "the decision schedule differs from the frozen record")
    if record["cost_ladder"]["headline"] != prereg.HEADLINE_COST_RUNG:
        raise RunnerRefused("PREREGISTRATION_REFUSED", "the headline cost rung differs")
    if frozen is not None:
        datasets = record["datasets"]
        if datasets["index_sha256"] != frozen.index_sha256 or datasets["private_commit"] != frozen.private_commit:
            raise RunnerRefused("PREREGISTRATION_REFUSED", "the loaded dataset is not the one the preregistration binds")
        if set(record["venues"]) != set(frozen.inputs):
            raise RunnerRefused("PREREGISTRATION_REFUSED", "the venues differ from the frozen record")


def evaluation_windows(record: Mapping[str, Any]) -> dict[str, tuple[datetime, datetime]]:
    """Each venue's frozen evaluation window: (evaluation start, last decision)."""

    return {
        venue: (
            datetime.fromisoformat(entry["evaluation_window"]["start"]),
            datetime.fromisoformat(entry["evaluation_window"]["last_decision"]),
        )
        for venue, entry in record["venues"].items()
    }


def _repository_module(name: str) -> bool:
    return name == "btc_predictor" or name.startswith("btc_predictor.")


def frozen_code_paths(repository: Path, modules: Iterable[tuple[str, Any]], *, pycache_prefix: str | None = None) -> list[str]:
    """Every loaded repository module outside the runner and the tests, and the frozen data files.

    Every repository module but the tests must have been loaded by the source
    loader from its ``.py`` file in this repository, and, in the command's
    fresh process, compiled into its empty private cache: no bytecode from
    elsewhere ran (review F5). Anything else refuses.
    """

    import importlib.machinery

    root = (repository / "btc_predictor").resolve()
    prefix = Path(pycache_prefix).resolve() if pycache_prefix is not None else None
    paths = set()
    for name, module in modules:
        if not _repository_module(name) or name == "btc_predictor.tests" or name.startswith("btc_predictor.tests."):
            continue
        spec = getattr(module, "__spec__", None)
        origin = getattr(spec, "origin", None) or getattr(module, "__file__", None)
        # review RR3: the source loader itself, not a subclass that may change the code it loads
        if not origin or type(getattr(spec, "loader", None)) is not importlib.machinery.SourceFileLoader:
            raise RunnerRefused("FROZEN_CODE_REFUSED", f"{name} was not loaded from its source file")
        resolved = Path(origin).resolve()
        if root not in resolved.parents or resolved.suffix != ".py":
            raise RunnerRefused("FROZEN_CODE_REFUSED", f"{name} was loaded from outside {root}")
        cached = getattr(spec, "cached", None)
        if prefix is not None and cached is not None and prefix not in Path(cached).resolve().parents:
            raise RunnerRefused("FROZEN_CODE_REFUSED", f"{name}'s bytecode is not in the fresh cache")
        relative = resolved.relative_to(repository.resolve())
        if relative.parts[1] == "tests" or (relative.parts[1] == "research_backtest" and relative.name in RUNNER_MODULES):
            continue
        paths.add(relative.as_posix())
    paths.update({STRATEGY_CONFIG_PATH.as_posix(), GOLDEN_FIXTURE_PATH.as_posix()})
    return sorted(paths)


def frozen_code_mismatches(repository: Path, commit: str, paths: Sequence[str]) -> list[str]:
    """Each path whose bytes differ from ``commit``'s (ruling 2); empty when all are frozen."""

    import subprocess

    request = "".join(f"{commit}:{path}\n" for path in paths).encode()
    completed = subprocess.run(
        ["git", "-C", str(repository), "cat-file", "--batch"], input=request, capture_output=True, check=True
    )
    output = completed.stdout
    mismatches = []
    position = 0
    for path in paths:
        end = output.index(b"\n", position)
        header = output[position:end].decode()
        position = end + 1
        if header.endswith(" missing"):
            mismatches.append(path)
            continue
        size = int(header.split()[2])
        frozen = output[position : position + size]
        position += size + 1
        if (repository / path).read_bytes() != frozen:
            mismatches.append(path)
    return mismatches


FRESH_BYTECODE_ENV = "RBT007_FRESH_PYCACHE"
# review N2: the only supported launch; it starts Python isolated, without site, with an empty bytecode cache
LAUNCHER = Path("btc_predictor") / "research_backtest" / "runner_launch.sh"


def fresh_bytecode_process() -> bool:
    """True in the process the launcher starts: isolated, without ``site``, no bytecode written, an empty private cache read (review N2)."""

    import os
    import sys

    prefix = os.environ.get(FRESH_BYTECODE_ENV)
    return (
        bool(prefix)
        and bool(sys.flags.dont_write_bytecode)
        and sys.pycache_prefix == prefix
        and bool(sys.flags.isolated)
        and bool(sys.flags.no_site)
    )


_FROZEN_BOOTSTRAP = ("<frozen importlib._bootstrap_external>", "<frozen importlib._bootstrap>")
_SOURCE_LOADER_METHODS = ("create_module", "exec_module", "get_code", "get_data", "get_filename", "path_stats", "source_to_code")


def startup_refusals(
    *,
    flags: Any = None,
    modules: Mapping[str, Any] | None = None,
    meta_path: Sequence[Any] | None = None,
    path_hooks: Sequence[Any] | None = None,
    loader: Any = None,
    builtins_module: Any = None,
) -> list[str]:
    """What in this process could run code other than the source files' (review RR3); empty if nothing.

    The process must be isolated and without ``site``, no startup
    customization module loaded, and its import system the interpreter's own:
    the three built-in meta-path finders, the two built-in path hooks, the
    source loader's methods from the frozen bootstrap, and the built-in
    ``compile`` and ``exec``. The arguments default to this process's.
    """

    import builtins
    import importlib.machinery as machinery
    import sys
    import types
    import zipimport

    flags = sys.flags if flags is None else flags
    modules = sys.modules if modules is None else modules
    meta_path = sys.meta_path if meta_path is None else meta_path
    path_hooks = sys.path_hooks if path_hooks is None else path_hooks
    loader = machinery.SourceFileLoader if loader is None else loader
    builtins_module = builtins if builtins_module is None else builtins_module
    problems = []
    if not (flags.isolated and flags.no_site and flags.ignore_environment and flags.safe_path):
        problems.append("the process is not isolated and without site")
    problems += [f"{name} was loaded" for name in ("sitecustomize", "usercustomize") if name in modules]
    if list(meta_path) != [machinery.BuiltinImporter, machinery.FrozenImporter, machinery.PathFinder]:
        problems.append("the meta path is not the interpreter's own")
    hook = path_hooks[1] if len(path_hooks) == 2 else None
    if (
        len(path_hooks) != 2
        or path_hooks[0] is not zipimport.zipimporter
        or getattr(hook, "__qualname__", None) != "FileFinder.path_hook.<locals>.path_hook_for_FileFinder"
        or getattr(getattr(hook, "__code__", None), "co_filename", None) not in _FROZEN_BOOTSTRAP
    ):
        problems.append("the path hooks are not the interpreter's own")
    for name in _SOURCE_LOADER_METHODS:
        code = getattr(getattr(loader, name, None), "__code__", None)
        if getattr(code, "co_filename", None) not in _FROZEN_BOOTSTRAP:
            problems.append(f"the source loader's {name} is not the interpreter's own")
    for name in ("compile", "exec"):
        function = getattr(builtins_module, name, None)
        if not isinstance(function, types.BuiltinFunctionType) or function.__module__ != "builtins":
            problems.append(f"{name} is not the built-in")
    return problems


def require_fresh_bytecode() -> str:
    import sys

    if not fresh_bytecode_process():
        raise RunnerRefused("FROZEN_CODE_REFUSED", "the command must run in its fresh-bytecode process")
    prefix = Path(sys.pycache_prefix)
    if not prefix.is_dir() or any(prefix.iterdir()):
        raise RunnerRefused("FROZEN_CODE_REFUSED", "the fresh bytecode cache is not an empty directory")
    problems = startup_refusals()
    if problems:
        raise RunnerRefused("FROZEN_CODE_REFUSED", f"the import system is not the interpreter's own: {problems}")
    return str(sys.pycache_prefix)


def require_frozen_code(repository: Path, commit: str) -> tuple[list[str], set[str]]:
    """Refuse unless every loaded repository module and frozen file equals ``commit``'s.

    Returns the paths compared and the modules checked; modules loaded later
    are checked by :func:`verify_loaded_code`.
    """

    import sys

    prefix = require_fresh_bytecode()
    modules = list(sys.modules.items())
    paths = frozen_code_paths(repository, modules, pycache_prefix=prefix)
    mismatches = frozen_code_mismatches(repository, commit, paths)
    if mismatches:
        raise RunnerRefused("FROZEN_CODE_REFUSED", f"{len(mismatches)} file(s) differ from {commit[:7]}: {mismatches[:5]}")
    return paths, {name for name, _module in modules if _repository_module(name)}


def preflight(repository: Path, out: Callable[[str], None] = print) -> int:
    """The run's first checks, reading neither the store nor the commit (review N2): 0 in the launcher's process.

    The process flags, the empty bytecode cache, the interpreter's own import
    system, and every repository module loaded so far from its source file;
    it also names the environment variables the process received, and its
    bytecode cache with that directory's permissions.
    """

    import os
    import sys

    try:
        prefix = require_fresh_bytecode()
        paths = frozen_code_paths(repository, list(sys.modules.items()), pycache_prefix=prefix)
    except RunnerRefused as error:
        out(f"refused: {error}")
        return 2
    cache = {"path": prefix, "mode": oct(Path(prefix).stat().st_mode & 0o777)}
    out(json.dumps({"launched": True, "modules_from_source": len(paths), "path": sys.path, "environment": sorted(os.environ), "cache": cache}))
    return 0


def verify_loaded_code() -> None:
    """Check every repository module loaded since the last check, in this process (review F5)."""

    import sys

    frozen = _STATE.get("frozen")
    if frozen is None:
        return
    repository, commit = frozen
    problems = startup_refusals()
    if problems:
        raise RunnerRefused("FROZEN_CODE_REFUSED", f"the import system changed during the run: {problems}")
    checked: set[str] = _STATE["checked_modules"]
    new = [(name, module) for name, module in list(sys.modules.items()) if _repository_module(name) and name not in checked]
    if not new:
        return
    prefix = sys.pycache_prefix if fresh_bytecode_process() else None
    paths = frozen_code_paths(repository, new, pycache_prefix=prefix)
    mismatches = frozen_code_mismatches(repository, commit, paths)
    if mismatches:
        raise RunnerRefused("FROZEN_CODE_REFUSED", f"a module loaded during the run differs from {commit[:7]}: {mismatches[:5]}")
    checked.update(name for name, _module in new)


def _verified(task: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """A pool task that checks the modules it loaded before it returns."""

    import functools

    @functools.wraps(task)
    def run(argument: Any) -> Any:
        result = task(argument)
        verify_loaded_code()
        return result

    return run


def golden_scenarios(repository: Path) -> dict[str, dict[str, Any]]:
    """The BTC-224 golden fixture's scenarios (periods, scripted decisions, rungs, starting NAV)."""

    document = json.loads((repository / GOLDEN_FIXTURE_PATH).read_text())
    return {scenario["scenario_id"]: scenario for scenario in document["scenarios"]}


# --- the run plan ----------------------------------------------------------------------------------


def run_plan(venues: Sequence[str], registry: Registry, golden: Mapping[str, Mapping[str, Any]]) -> list[RunSpec]:
    """Every run, in a fixed order: the report never depends on the order runs finish in."""

    specs: list[RunSpec] = []
    for venue in venues:
        for rung in prereg.COST_RUNGS:
            specs.append(RunSpec(HEADLINE, venue, CHAMPION, rung))
            specs.append(RunSpec(WALK_FORWARD, venue, CHAMPION, rung))
        specs.append(RunSpec(ABLATION, venue, _ablation_id(registry), prereg.HEADLINE_COST_RUNG))
        for variant in registry.variants.values():
            if variant.role == SWEEP:
                specs.append(RunSpec(SWEEP, venue, variant.variant_id, prereg.SWEEP_COST_RUNG))
        for scenario_id, scenario in golden.items():
            specs.append(RunSpec(GOLDEN, venue, CHAMPION, scenario["cost_profile"], scenario_id))
    return specs


def _ablation_id(registry: Registry) -> str:
    found = [variant.variant_id for variant in registry.variants.values() if variant.role == ABLATION]
    if len(found) != 1:
        raise RunnerRefused("REGISTRY_REFUSED", "exactly one ablation variant must be registered")
    return found[0]


def spec_window(spec: RunSpec, context: RunContext) -> tuple[datetime, datetime]:
    """The first and last decision instant a run composes."""

    if spec.kind == GOLDEN:
        return golden_window(context.golden[spec.scenario])
    return context.evaluation[spec.venue]


def precompute_instants(specs: Sequence[RunSpec], context: RunContext) -> list[datetime]:
    """Every scheduled instant up to the last any run composes: the continuous history composes them all."""

    last = max(spec_window(spec, context)[1] for spec in specs)
    return [instant for instant in context.schedule if instant <= last]


def continuous_history(
    inputs: EntryComposerInputs, champion: StrategyConfig, last: datetime, schedule: Sequence[datetime] | None = None
) -> tuple[Any, ...]:
    """Ruling 7: the champion's decisions, flat, at every scheduled instant up to ``last``, consecutively."""

    composer = EntryComposer(inputs, strategy_config=champion)
    for instant in schedule if schedule is not None else prereg.decision_schedule():
        if instant > last:
            break
        composer.record(composer.decide(instant))
    return tuple(composer.ledger)


def precompute_blocks(instants: Sequence[datetime], parts: int) -> list[tuple[datetime, ...]]:
    """Contiguous runs of consecutive instants, cut into blocks of about equal cost.

    An instant's cost grows with the square of its distance from the data
    window's start, so later blocks hold fewer instants.
    """

    runs: list[list[datetime]] = []
    for instant in instants:
        if runs and instant - runs[-1][-1] == _DAY:
            runs[-1].append(instant)
        else:
            runs.append([instant])
    origin = instants[0] if instants else datetime(2020, 1, 2, tzinfo=UTC)

    def cost(instant: datetime) -> float:
        return float(((instant - origin) / _DAY) + 1) ** 2

    total = sum(cost(instant) for instant in instants)
    target = total / max(parts, 1)
    blocks: list[tuple[datetime, ...]] = []
    for run in runs:
        current: list[datetime] = []
        spent = 0.0
        for instant in run:
            current.append(instant)
            spent += cost(instant)
            if spent >= target:
                blocks.append(tuple(current))
                current, spent = [], 0.0
        if current:
            blocks.append(tuple(current))
    return blocks


# --- the look-ahead audit (ruling 3, amended by review ruling 3a) ----------------------------------------

AUDIT_VERSION = "RBT007_LOOKAHEAD_AUDIT_V2"
AUDIT_SEEDED_INSTANTS = 20
AUDIT_RULE = (
    "review ruling 3a: every continuous-history row and every decision instant of the champion's base "
    "evaluation-window run, each recomputed on inputs truncated at its own instant and seeded only with the "
    "recorded rows before it; the engine state each decision received replayed from only the bars available "
    "at its instant and the run's earlier decisions; ruling 3's sample (every intent instant plus 20 seeded "
    "instants) recomputed unshared, every other link sharing positioning results only among the audit's own "
    "truncated recomputations"
)
HISTORY_LINK = "HISTORY"
RUN_LINK = "RUN"


def truncated_inputs(inputs: EntryComposerInputs, instant: datetime) -> EntryComposerInputs:
    """The replay inputs keeping only the rows available at ``instant``.

    Price and volume bars by their ``ingested_at``, every other family by its
    ``available_at``: the fields the composer's own visibility checks read.
    The ETF fund launches (RBT-006 ruling 1) are a frozen static table, kept.
    """

    dataset = inputs.dataset
    shared = dataset.shared_snapshot
    shared_t = replace(
        shared,
        volume_bars=tuple(bar for bar in shared.volume_bars if bar.ingested_at <= instant),
        etf_flows=tuple(row for row in shared.etf_flows if row.available_at <= instant),
        funding_rates=tuple(row for row in shared.funding_rates if row.available_at <= instant),
        open_interest=tuple(row for row in shared.open_interest if row.available_at <= instant),
        perp_volumes=tuple(row for row in shared.perp_volumes if row.available_at <= instant),
    )
    dataset_t = replace(dataset, price_bars=tuple(bar for bar in dataset.price_bars if bar.ingested_at <= instant), shared_snapshot=shared_t)
    return replace(
        inputs,
        dataset=dataset_t,
        futures_basis=tuple(row for row in inputs.futures_basis if row.available_at <= instant),
        market_caps=tuple(row for row in inputs.market_caps if row.available_at <= instant),
        liquidation_percentiles=tuple(row for row in inputs.liquidation_percentiles if row.available_at <= instant),
    )


def audit_sample(venue: str, instants: Sequence[datetime], intent_instants: Iterable[datetime]) -> list[tuple[datetime, str]]:
    """Every intent instant, plus 20 instants drawn by a fixed seed from the rest of the window (ruling 3)."""

    intents = set(intent_instants)
    rest = [instant for instant in instants if instant not in intents]
    ranked = sorted(rest, key=lambda instant: hashlib.sha256(f"{AUDIT_VERSION}:{venue}:{instant.isoformat()}".encode()).hexdigest())
    chosen = [(instant, "INTENT") for instant in intents] + [(instant, "SEEDED") for instant in ranked[:AUDIT_SEEDED_INSTANTS]]
    return sorted(chosen)


def _same(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    return canonical_json_bytes(a) == canonical_json_bytes(b)


@dataclass(frozen=True)
class _ReplayComposition:
    """What the management composer's engine adapter reads from a composition."""

    flow: Any
    decision_bar: Any


def _slim(decision: EntryDecision) -> EntryDecision:
    if decision.composition is None:
        return decision
    return replace(decision, composition=_ReplayComposition(decision.composition.flow, decision.composition.decision_bar))


def _composed(decision: EntryDecision) -> tuple[Any, Any] | None:
    composition = decision.composition
    return None if composition is None else (composition.flow, composition.decision_bar)


class _ReplayEntryComposer(EntryComposer):
    """Gives back the run's recorded decisions; records the position each was offered."""

    def __init__(self, inputs: EntryComposerInputs, champion: StrategyConfig, decisions: Mapping[datetime, EntryDecision]) -> None:
        super().__init__(inputs, strategy_config=champion)
        self._decisions = decisions
        self.offered: dict[datetime, bool] = {}

    def decide(self, as_of: datetime, *, position_open: bool = False) -> EntryDecision:
        self.offered[as_of] = position_open
        return self._decisions[as_of]


class _ReplayManagementComposer(ManagementComposer):
    """The unchanged engine adapter over recorded decisions; records what management received."""

    def __init__(self, entry: EntryComposer, managed: Mapping[datetime, Any]) -> None:
        super().__init__(entry)
        self._managed = managed
        self.received: dict[datetime, dict[str, Any]] = {}
        self.positions: dict[datetime, bool] = {}

    def __call__(self, context: Any) -> Any:
        self.positions[context.as_of] = context.position_open
        return super().__call__(context)

    def decide(self, decision: EntryDecision, *, lifecycle: Any, nav: Decimal, armed: Any, prior_flow: Any | None) -> Any:
        instant = decision.row.decision_at
        self.received[instant] = {"lifecycle": lifecycle, "nav": nav, "armed": armed, "prior_flow": prior_flow}
        return self._managed[instant]


@dataclass(frozen=True)
class AuditState:
    """The reproduced champion base run, as the chain's run links read it (ruling 3a)."""

    venue: str
    reproduced: bool
    first: datetime
    last: datetime
    strategy_id: str
    ledger: tuple[Any, ...]  # the run composer's rows: its seeded history, then the run's own
    decisions: Mapping[datetime, EntryDecision]  # every decision the run composed, slim
    calls: Mapping[datetime, Mapping[str, Any]]  # the management inputs the composer received
    managed: Mapping[datetime, Any]
    management_rows: tuple[Any, ...]
    followups: tuple[Any, ...]
    sample: tuple[tuple[datetime, str], ...]
    replay_reproduces_run: bool = False

    @property
    def run_instants(self) -> list[datetime]:
        return sorted(instant for instant in self.decisions if self.first <= instant <= self.last)

    def meta(self) -> dict[str, Any]:
        intents = [instant.isoformat() for instant, reason in self.sample if reason == "INTENT"]
        return {
            "venue": self.venue,
            "reproduced": self.reproduced,
            "replay_reproduces_run": self.replay_reproduces_run,
            "run_instants": [instant.isoformat() for instant in self.run_instants],
            "sample": [[instant.isoformat(), reason] for instant, reason in self.sample],
            "intent_instants": intents,
        }


def _replay(
    state: AuditState, context: RunContext, until: datetime, *, inclusive: bool = True, truncated: EntryComposerInputs | None = None
) -> tuple[_ReplayEntryComposer, _ReplayManagementComposer]:
    """The engine over the run's bars available by ``until``, replaying the run's recorded decisions.

    Nothing after ``until`` is given to the engine or the composers, so the
    state it hands the composer at ``until`` comes from those bars and the
    earlier decisions alone.
    """

    inputs = context.inputs[state.venue]
    bars = tuple(
        bar
        for bar in venue_bars(inputs)
        if state.first <= _bar_available_at(bar) and (_bar_available_at(bar) <= until if inclusive else _bar_available_at(bar) < until)
    )
    entry = _ReplayEntryComposer(truncated if truncated is not None else truncated_inputs(inputs, until), context.registry.champion, state.decisions)
    strategy = _ReplayManagementComposer(entry, state.managed)
    if not bars:  # the instant's own bar omitted at the window's start: no callback yet, flat
        return entry, strategy
    run_backtest(
        bars,
        strategy=strategy,
        symbol=bars[0].symbol,
        strategy_config=context.registry.champion,
        cost_profile=prereg.HEADLINE_COST_RUNG,
        strategy_id=state.strategy_id,
    )
    return entry, strategy


def _inputs_equal(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    return all(a[name] == b[name] for name in MANAGEMENT_INPUTS)


def audit_state(venue: str, context: RunContext, checkpoint: Mapping[str, Any], share: Callable[[], Any] | None = None) -> AuditState:
    """Reproduce the champion's base headline run, which must equal its record, and keep its state.

    ``share`` serves the run's shared positioning results to the
    reproduction only; no audited recomputation uses them.
    """

    from contextlib import nullcontext

    spec = RunSpec(HEADLINE, venue, CHAMPION, prereg.HEADLINE_COST_RUNG)
    with (share() if share is not None else nullcontext()):
        outcome = execute_run(spec, context, record_management=True)
    strategy = outcome.composers[0]
    entry = strategy.entry
    start, last = context.evaluation[venue]
    run_rows = entry.run_rows()
    intents = {row.decision_at for row in run_rows if row.intent is not None}
    intents |= {row.decision_at for row in strategy.ledger if row.intent is not None}
    instants = sorted(row.decision_at for row in run_rows if start <= row.decision_at <= last)
    state = AuditState(
        venue=venue,
        reproduced=_same(outcome.record, checkpoint),
        first=start,
        last=last,
        strategy_id=f"rbt007:{spec.run_id}",
        ledger=tuple(entry.ledger),
        decisions={instant: _slim(decision) for instant, decision in entry.decisions.items()},
        calls={instant: dict(call) for instant, call in strategy.calls.items()},
        managed=dict(strategy.managed),
        management_rows=tuple(strategy.ledger),
        followups=tuple(strategy.add_followups),
        sample=tuple(audit_sample(venue, instants, intents)),
    )
    # the replay machinery, over the whole window, must give back the run itself
    _entry, replay = _replay(state, context, last + _DAY, inclusive=False)
    whole = (
        [row.as_record() for row in replay.ledger] == [row.as_record() for row in state.management_rows]
        and [followup.as_record() for followup in replay.add_followups] == [followup.as_record() for followup in state.followups]
        and set(replay.received) == set(state.calls)
        and all(_inputs_equal(replay.received[instant], call) for instant, call in state.calls.items())
    )
    return replace(state, replay_reproduces_run=whole)


def history_link(venue: str, context: RunContext, instant: datetime, *, truncated: EntryComposerInputs | None = None) -> dict[str, Any]:
    """One continuous-history row, recomputed on inputs truncated at its instant, seeded with the rows before it."""

    rows = context.history[venue]
    reference = next(row for row in rows if row.decision_at == instant)
    fresh = RegisteredEntryComposer(
        truncated if truncated is not None else truncated_inputs(context.inputs[venue], instant),
        variant=context.registry.variants[CHAMPION],
        registry=context.registry,
        history=tuple(row for row in rows if row.decision_at < instant),
    )
    decision = fresh.decide(instant)
    return {"venue": venue, "kind": HISTORY_LINK, "decision_at": instant.isoformat(), "entry_row_equal": _same(decision.row.as_record(), reference.as_record())}


def run_link(state: AuditState, context: RunContext, instant: datetime, *, truncated: EntryComposerInputs | None = None) -> dict[str, Any]:
    """One decision instant of the champion's base run, proven from what was available at it.

    The engine replay to ``instant`` gives the position, and at a management
    instant the lifecycle, NAV, armed entry and prior flow, from the bars
    available at it and the run's earlier decisions (each its own link). The
    decision is then recomputed on inputs truncated at ``instant``, seeded
    with the run's rows before it, and must equal the run's: its row, intent,
    flow and decision bar, and its management row, intent and pending add.
    """

    truncated = truncated if truncated is not None else truncated_inputs(context.inputs[state.venue], instant)
    replay_entry, replay = _replay(state, context, instant, truncated=truncated)
    callbacks = [moment for moment in replay.positions if moment <= instant]
    position_open = replay_entry.offered.get(instant, replay.positions[max(callbacks)] if callbacks else False)
    original = state.decisions[instant]
    fresh = RegisteredEntryComposer(
        truncated,
        variant=context.registry.variants[CHAMPION],
        registry=context.registry,
        history=tuple(row for row in state.ledger if row.decision_at < instant),
    )
    decision = fresh.decide(instant, position_open=position_open)
    item: dict[str, Any] = {
        "venue": state.venue,
        "kind": RUN_LINK,
        "decision_at": instant.isoformat(),
        "sample": dict(state.sample).get(instant),
        "entry_row_equal": _same(decision.row.as_record(), original.row.as_record()),
        "intent_equal": decision.intent == original.intent,
        "composition_equal": _composed(decision) == _composed(original),
        "replay_prefix_equal": (
            [row.as_record() for row in replay.ledger if row.decision_at < instant]
            == [row.as_record() for row in state.management_rows if row.decision_at < instant]
            and [followup.as_record() for followup in replay.add_followups if followup.resolved_at <= instant]
            == [followup.as_record() for followup in state.followups if followup.resolved_at <= instant]
        ),
        "engine_state_equal": None,
        "management_row_equal": None,
    }
    call, received = state.calls.get(instant), replay.received.get(instant)
    if call is None:
        item["engine_state_equal"] = received is None
    else:
        item["engine_state_equal"] = received is not None and _inputs_equal(received, call)
        if received is not None:
            managed = ManagementComposer(fresh).decide(decision, **received)
            saved = state.managed[instant]
            item["management_row_equal"] = (
                _same(managed.row.as_record(), saved.row.as_record()) and managed.intent == saved.intent and managed.pending_add == saved.pending_add
            )
    return item


_HISTORY_CHECKS = ("entry_row_equal",)
_RUN_CHECKS = ("entry_row_equal", "intent_equal", "composition_equal", "replay_prefix_equal", "engine_state_equal")


def _link_failed(item: Mapping[str, Any], managed: bool | None = None) -> bool:
    """A link proves its instant only if every check of its kind is present and true (review RR1).

    A run link's management check is true at an instant the composer managed
    and absent (None) at any other; ``managed`` says which, else either passes.
    """

    checks = _HISTORY_CHECKS if item.get("kind") == HISTORY_LINK else _RUN_CHECKS
    if item.get("kind") not in (HISTORY_LINK, RUN_LINK) or any(item.get(name) is not True for name in checks):
        return True
    if item["kind"] == HISTORY_LINK:
        return False
    if "management_row_equal" not in item:
        return True
    management = item["management_row_equal"]
    if managed is None:
        return not (management is True or management is None)
    return management is not (True if managed else None)


def audit_expectation(venue: str, context: RunContext, record: Mapping[str, Any]) -> dict[str, Any]:
    """What ruling 3a must prove for a venue, from its bound base run alone (review RR1).

    Every decision instant of the champion's base evaluation-window run gets a
    run link; ruling 3's sample is its intent instants plus the seeded draw;
    management is checked wherever the composer managed: an open position at
    an instant with its decision bar.
    """

    start, last = context.evaluation[venue]
    rows = record["entry_ledger"]
    instants = sorted(datetime.fromisoformat(row["decision_at"]) for row in rows if start <= datetime.fromisoformat(row["decision_at"]) <= last)
    intents = {datetime.fromisoformat(row["decision_at"]) for row in (*rows, *record["management_ledger"]) if row["intent"] is not None}
    managed = [row["decision_at"] for row in rows if row["position_open"] and list(row["reasons"]) != [CAUSE_DECISION_PRICE_BAR_MISSING]]
    return {
        "run_instants": [instant.isoformat() for instant in instants],
        "sample": [[instant.isoformat(), reason] for instant, reason in audit_sample(venue, instants, intents)],
        "managed": managed,
    }


def audit_summary(
    venue: str, meta: Mapping[str, Any], history_instants: Sequence[datetime], links: Sequence[Mapping[str, Any]], expected: Mapping[str, Any]
) -> dict[str, Any]:
    """Ruling 3a's verdict for one venue: every link the base run requires present once, and every one equal.

    Review RR1: what is required comes from the bound base run
    (:func:`audit_expectation`), never from the audit's own stored list.
    """

    history = sorted((item for item in links if item.get("kind") == HISTORY_LINK), key=lambda item: item["decision_at"])
    run = sorted((item for item in links if item.get("kind") == RUN_LINK), key=lambda item: item["decision_at"])
    sample = {instant: reason for instant, reason in expected["sample"]}
    managed = set(expected["managed"])
    sampled = [item for item in run if item["decision_at"] in sample]
    complete = (
        bool(expected["run_instants"])
        and [item["decision_at"] for item in history] == [instant.isoformat() for instant in history_instants]
        and [item["decision_at"] for item in run] == list(expected["run_instants"])
        and list(meta.get("run_instants", ())) == list(expected["run_instants"])
        and [list(pair) for pair in meta.get("sample", ())] == [list(pair) for pair in expected["sample"]]
        and all(item.get("sample") == sample.get(item["decision_at"]) for item in run)
        and len(sampled) == len(sample)
        and all(item.get("shared") is False for item in sampled)
    )
    failures = [f"{item['kind']}:{item['decision_at']}" for item in history if _link_failed(item)]
    failures += [f"{item['kind']}:{item['decision_at']}" for item in run if _link_failed(item, item["decision_at"] in managed)]
    return {
        "venue": venue,
        "audit_version": AUDIT_VERSION,
        "rule": AUDIT_RULE,
        "history_links": len(history),
        "run_links": len(run),
        "sample_size": len(sample),
        "audited": len(sampled),
        "intent_instants": sum(1 for reason in sample.values() if reason == "INTENT"),
        "seeded_instants": sum(1 for reason in sample.values() if reason == "SEEDED"),
        "management_checked": sum(1 for item in run if item["decision_at"] in managed and item.get("management_row_equal") is True),
        "reproduced": meta.get("reproduced") is True,
        "replay_reproduces_run": meta.get("replay_reproduces_run") is True,
        "complete": complete,
        "failures": failures,
        "passed": complete and not failures and meta.get("reproduced") is True and meta.get("replay_reproduces_run") is True,
        "sampled_instants": sampled,
    }


# --- orchestration: the precompute, the runs and the audit, resumable ----------------------------

_STATE: dict[str, Any] = {}  # set in the parent before the pool forks; the workers inherit it


@dataclass(frozen=True)
class Workspace:
    """The private work directory: shared results, run records and markers (Part B ruling 9)."""

    directory: Path

    @property
    def shared(self) -> Path:
        return self.directory / "shared"

    @property
    def markers(self) -> Path:
        return self.directory / "markers"

    @property
    def log(self) -> Path:
        return self.directory / "run_log.jsonl"


def _share_factory() -> Callable[[], Any]:
    from btc_predictor.research_backtest import runner_shared as rs

    encoder = rs.ArgumentEncoder()
    for inputs in _STATE["context"].inputs.values():
        rs.register_positioning_sources(encoder, inputs)
    store = rs.SharedResultStore(_STATE["workspace"].shared)
    statistics = _STATE.setdefault("statistics", ShareStatistics())
    return lambda: rs.shared_positioning(store, encoder, statistics)


def _marker(name: str) -> Path:
    return _STATE["workspace"].markers / f"{hashlib.sha256(name.encode()).hexdigest()[:24]}.json"


def _write_marker(name: str, record: Mapping[str, Any]) -> None:
    path = _marker(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    partial.write_bytes(canonical_json_bytes({"name": name, **record}))
    partial.replace(path)


def _log(entry: Mapping[str, Any]) -> None:
    # the operational log: durations and share counts, outside every reproducible record
    with _STATE["workspace"].log.open("a") as stream:
        stream.write(json.dumps(entry, sort_keys=True) + "\n")


@_verified
def _precompute_block(block: tuple[datetime, ...]) -> str:
    import time

    name = f"precompute:{block[0].isoformat()}:{block[-1].isoformat()}"
    if _marker(name).exists():
        return name
    _STATE["statistics"] = ShareStatistics()
    share = _share_factory()
    composer = EntryComposer(_STATE["precompute_inputs"], strategy_config=_STATE["context"].registry.champion)
    started = time.monotonic()
    with share():
        for instant in block:
            composer.decide(instant)
    _write_marker(name, {"instants": len(block)})
    _log({"event": "precompute", "block": [block[0].isoformat(), block[-1].isoformat()], "seconds": round(time.monotonic() - started, 1), "share": _STATE["statistics"].as_record()})
    return name


def history_file(workspace: Workspace, venue: str) -> Path:
    return workspace.directory / "history" / f"{venue.lower()}.pickle"


def history_binding(context: RunContext, venue: str, last: datetime) -> dict[str, Any]:
    instants = [instant for instant in context.schedule if instant <= last]
    champion = context.registry.champion
    return {
        "context": dict(context.binding),
        "venue": venue,
        "champion": champion.run_metadata(),
        "configuration_sha256": configuration_sha256(champion),
        "schedule": [instants[0].isoformat(), instants[-1].isoformat(), len(instants)],
    }


def read_history(workspace: Workspace, venue: str, context: RunContext, last: datetime) -> tuple[Any, ...]:
    """A venue's continuous history, only if it is this binding's and holds every scheduled instant (review F3)."""

    import pickle

    path = history_file(workspace, venue)
    try:
        data = load_store_pickle(path.read_bytes())
    except (OSError, EOFError, pickle.UnpicklingError, AttributeError, ValueError, TypeError) as error:
        raise RunnerRefused("HISTORY_REFUSED", f"{venue}'s history file is not readable: {error}") from error
    if not isinstance(data, dict) or data.get("binding") != history_binding(context, venue, last):
        raise RunnerRefused("HISTORY_REFUSED", f"{venue}'s history file was written under another binding")
    rows = tuple(data.get("rows") or ())
    expected = [instant for instant in context.schedule if instant <= last]
    if not rows or [row.decision_at for row in rows] != expected or any(row.venue != venue for row in rows):
        raise RunnerRefused("HISTORY_REFUSED", f"{venue}'s history does not hold every scheduled instant")
    return rows


@_verified
def _history_task(venue: str) -> str:
    import time

    workspace: Workspace = _STATE["workspace"]
    context: RunContext = _STATE["context"]
    last = _STATE["history_last"]
    if history_file(workspace, venue).exists():
        read_history(workspace, venue, context, last)
        return venue
    _STATE["statistics"] = ShareStatistics()
    share = _share_factory()
    started = time.monotonic()
    with share():
        rows = continuous_history(context.inputs[venue], context.registry.champion, last, context.schedule)
    _write_whole(history_file(workspace, venue), dump_store_pickle({"binding": history_binding(context, venue, last), "rows": rows}))
    _log({"event": "history", "venue": venue, "rows": len(rows), "seconds": round(time.monotonic() - started, 1), "share": _STATE["statistics"].as_record()})
    return venue


def load_history(workspace: Workspace, venues: Iterable[str], context: RunContext, last: datetime) -> dict[str, tuple[Any, ...]]:
    return {venue: read_history(workspace, venue, context, last) for venue in venues}


@_verified
def _run_spec(spec: RunSpec) -> str:
    import time

    workspace: Workspace = _STATE["workspace"]
    if read_run(workspace.directory, spec, _STATE["context"]) is not None:
        return spec.run_id
    _STATE["statistics"] = ShareStatistics()
    share = _share_factory()
    started = time.monotonic()
    with share():
        outcome = execute_run(spec, _STATE["context"])
    write_run(workspace.directory, outcome)
    _log({"event": "run", "run_id": spec.run_id, "seconds": round(time.monotonic() - started, 1), "share": _STATE["statistics"].as_record()})
    return spec.run_id


def audit_state_file(workspace: Workspace, venue: str) -> Path:
    return workspace.directory / "audit" / f"state_{venue.lower()}.pickle"


def audit_meta_file(workspace: Workspace, venue: str) -> Path:
    return workspace.directory / "audit" / f"state_{venue.lower()}.json"


def audit_links_file(workspace: Workspace, kind: str, instant: datetime) -> Path:
    return workspace.directory / "audit" / kind.lower() / f"{instant.strftime('%Y%m%dT%H%M')}.json"


def _write_whole(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    partial.write_bytes(data)
    partial.replace(path)


def audit_binding(context: RunContext, venue: str, checkpoint: Mapping[str, Any]) -> dict[str, Any]:
    """What a venue's audit files hold: the history and the base run they audit (review F3)."""

    return {
        "context": dict(context.binding),
        "audit_version": AUDIT_VERSION,
        "venue": venue,
        "history_sha256": context.history_sha256(venue),
        "base_run_record_sha256": hashlib.sha256(canonical_json_bytes(checkpoint)).hexdigest(),
    }


def link_binding(context: RunContext, kind: str, instant: datetime, venues: Mapping[str, Any]) -> dict[str, Any]:
    return {"context": dict(context.binding), "audit_version": AUDIT_VERSION, "kind": kind, "instant": instant.isoformat(), "venues": dict(venues)}


def _read_links(path: Path, expected: Mapping[str, Any]) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_bytes())
    except (OSError, ValueError) as error:
        raise RunnerRefused("AUDIT_REFUSED", f"{path.name} is not readable: {error}") from error
    if not isinstance(data, dict) or data.get("binding") != json.loads(canonical_json_bytes(expected)):
        raise RunnerRefused("AUDIT_REFUSED", f"{path.name} was written under another binding")
    links = data.get("links")
    # review RR1: each link is its file's instant's; a missing or malformed one proves nothing
    if not isinstance(links, list) or not all(isinstance(item, dict) and item.get("decision_at") == expected["instant"] for item in links):
        raise RunnerRefused("AUDIT_REFUSED", f"{path.name} does not hold its instant's links")
    return list(links)


def _audit_share(truncated: Iterable[EntryComposerInputs]) -> Callable[[], Any]:
    """Ruling 3a: positioning results shared among the audit's own truncated recomputations only."""

    from btc_predictor.research_backtest import runner_shared as rs

    encoder = rs.ArgumentEncoder()
    for inputs in truncated:
        rs.register_positioning_sources(encoder, inputs)
    store = rs.SharedResultStore(_STATE["workspace"].directory / "audit_shared")
    statistics = _STATE.setdefault("statistics", ShareStatistics())
    return lambda: rs.shared_positioning(store, encoder, statistics)


def _audit_state_task(venue: str) -> None:
    workspace: Workspace = _STATE["workspace"]
    binding = _STATE["audit_bindings"][venue]
    if audit_state_file(workspace, venue).exists():
        load_audit_state(workspace, venue, binding)
        return
    context: RunContext = _STATE["context"]
    spec = RunSpec(HEADLINE, venue, CHAMPION, prereg.HEADLINE_COST_RUNG)
    checkpoint = read_run(workspace.directory, spec, context)
    if checkpoint is None:
        raise RunnerRefused("AUDIT_REFUSED", f"{venue}'s base headline run has no record yet")
    state = audit_state(venue, context, checkpoint, share=_share_factory())
    _write_whole(audit_meta_file(workspace, venue), canonical_json_bytes({**state.meta(), "binding": binding}))
    _write_whole(audit_state_file(workspace, venue), dump_store_pickle({"binding": binding, "state": state}))


def _history_links_task(instant: datetime) -> None:
    workspace: Workspace = _STATE["workspace"]
    context: RunContext = _STATE["context"]
    venues = [venue for venue in context.inputs if any(row.decision_at == instant for row in context.history[venue])]
    binding = link_binding(context, HISTORY_LINK, instant, {venue: context.history_sha256(venue) for venue in venues})
    path = audit_links_file(workspace, HISTORY_LINK, instant)
    if path.exists():
        _read_links(path, binding)
        return
    truncated = {venue: truncated_inputs(context.inputs[venue], instant) for venue in venues}
    _STATE["statistics"] = ShareStatistics()
    share = _audit_share(truncated.values())
    with share():
        links = [{**history_link(venue, context, instant, truncated=truncated[venue]), "shared": True} for venue in venues]
    _write_whole(path, canonical_json_bytes({"binding": binding, "links": links}))


def _run_links_task(instant: datetime) -> None:
    from contextlib import nullcontext

    workspace: Workspace = _STATE["workspace"]
    context: RunContext = _STATE["context"]
    states: Mapping[str, AuditState] = _STATE["audit_states"]
    venues = [venue for venue, state in states.items() if instant in state.run_instants]
    binding = link_binding(context, RUN_LINK, instant, {venue: _STATE["audit_bindings"][venue] for venue in venues})
    path = audit_links_file(workspace, RUN_LINK, instant)
    if path.exists():
        _read_links(path, binding)
        return
    truncated = {venue: truncated_inputs(context.inputs[venue], instant) for venue in venues}
    _STATE["statistics"] = ShareStatistics()
    share = _audit_share(truncated.values())
    links = []
    for venue in venues:
        # ruling 3's sample is recomputed with no shared result at all
        shared = instant not in dict(states[venue].sample)
        with (share() if shared else nullcontext()):
            links.append({**run_link(states[venue], context, instant, truncated=truncated[venue]), "shared": shared})
    _write_whole(path, canonical_json_bytes({"binding": binding, "links": links}))


@_verified
def _audit_phase_one(task: tuple[str, Any]) -> str:
    import time

    kind, value = task
    started = time.monotonic()
    if kind == "state":
        _audit_state_task(value)
    else:
        _history_links_task(value)
    _log({"event": f"audit:{kind}", "task": str(value), "seconds": round(time.monotonic() - started, 1)})
    return f"{kind}:{value}"


@_verified
def _audit_phase_two(instant: datetime) -> str:
    import time

    started = time.monotonic()
    _run_links_task(instant)
    _log({"event": "audit:run", "task": instant.isoformat(), "seconds": round(time.monotonic() - started, 1)})
    return instant.isoformat()


def load_audit_state(workspace: Workspace, venue: str, binding: Mapping[str, Any]) -> AuditState:
    import pickle

    path = audit_state_file(workspace, venue)
    if not path.exists():
        raise RunnerRefused("AUDIT_REFUSED", f"{venue}'s audit state has not been written")
    try:
        data = load_store_pickle(path.read_bytes())
    except (OSError, EOFError, pickle.UnpicklingError, AttributeError, ValueError, TypeError) as error:
        raise RunnerRefused("AUDIT_REFUSED", f"{venue}'s audit state is not readable: {error}") from error
    if not isinstance(data, dict) or data.get("binding") != binding or not isinstance(data.get("state"), AuditState):
        raise RunnerRefused("AUDIT_REFUSED", f"{venue}'s audit state was written under another binding")
    return data["state"]


def read_audit(workspace: Workspace, venue: str, context: RunContext, binding: Mapping[str, Any]) -> dict[str, Any]:
    """Ruling 3a's summary for one venue, from its state and every link file, each under its binding."""

    meta_path = audit_meta_file(workspace, venue)
    if not meta_path.exists():
        raise RunnerRefused("AUDIT_REFUSED", f"{venue}'s audit state has not been written")
    meta = json.loads(meta_path.read_bytes())
    if meta.get("binding") != json.loads(canonical_json_bytes(binding)):
        raise RunnerRefused("AUDIT_REFUSED", f"{venue}'s audit state was written under another binding")
    # review RR1: the links required are the bound base run's, not the stored metadata's
    base = _base_record(workspace, context, venue)
    if json.loads(canonical_json_bytes(binding)) != json.loads(canonical_json_bytes(audit_binding(context, venue, base))):
        raise RunnerRefused("AUDIT_REFUSED", f"{venue}'s audit is not bound to its base run's record")
    required = audit_expectation(venue, context, base)
    history_instants = [row.decision_at for row in context.history[venue]]
    links: list[dict[str, Any]] = []
    for kind, instants, own in (
        (HISTORY_LINK, history_instants, context.history_sha256(venue)),
        (RUN_LINK, [datetime.fromisoformat(item) for item in required["run_instants"]], binding),
    ):
        for instant in instants:
            path = audit_links_file(workspace, kind, instant)
            if not path.exists():
                raise RunnerRefused("AUDIT_REFUSED", f"the {kind.lower()} link at {instant.isoformat()} has not been written")
            data = json.loads(path.read_bytes())
            stored = data.get("binding") if isinstance(data, dict) else None
            expected = link_binding(context, kind, instant, {**(stored or {}).get("venues", {}), venue: own})
            links.extend(item for item in _read_links(path, expected) if item.get("venue") == venue)
    return audit_summary(venue, meta, history_instants, links, required)


def _base_record(workspace: Workspace, context: RunContext, venue: str) -> dict[str, Any]:
    spec = RunSpec(HEADLINE, venue, CHAMPION, prereg.HEADLINE_COST_RUNG)
    record = read_run(workspace.directory, spec, context)
    if record is None:
        raise RunnerRefused("AUDIT_REFUSED", f"{venue}'s base headline run has no record yet")
    return record


def _expected_cost(spec: RunSpec) -> int:
    # longest first, so the pool's tail is short
    return {HEADLINE: 4, ABLATION: 4, WALK_FORWARD: 3, SWEEP: 3, GOLDEN: 1}[spec.kind]


def execute_all(
    context: RunContext,
    specs: Sequence[RunSpec],
    workspace: Workspace,
    *,
    workers: int,
    precompute_venue: str,
    progress: Callable[[str], None] = lambda line: None,
    frozen_code: tuple[Path, str, set[str]] | None = None,
) -> None:
    """The precompute, the history, every run and the audit, each skipped when its complete file exists."""

    import multiprocessing

    workspace.directory.mkdir(parents=True, exist_ok=True)
    _STATE.clear()
    _STATE.update({"context": context, "workspace": workspace, "precompute_inputs": context.inputs[precompute_venue]})
    if frozen_code is not None:
        # review F5: modules loaded after the command's check are checked where they load
        repository, commit, checked = frozen_code
        _STATE.update({"frozen": (repository, commit), "checked_modules": set(checked)})
        verify_loaded_code()
    pool_context = multiprocessing.get_context("fork")
    blocks = precompute_blocks(precompute_instants(specs, context), workers * 4)
    progress(f"precompute: {len(blocks)} blocks over {sum(len(block) for block in blocks)} instants")
    with pool_context.Pool(workers) as pool:
        for done, _name in enumerate(pool.imap_unordered(_precompute_block, sorted(blocks, key=lambda block: block[-1], reverse=True)), 1):
            progress(f"precompute: {done}/{len(blocks)} blocks")
    _STATE["history_last"] = max(spec_window(spec, context)[1] for spec in specs)
    venues = list(context.inputs)
    progress(f"history: {len(venues)} venues")
    with pool_context.Pool(min(workers, len(venues))) as pool:
        for venue in pool.imap_unordered(_history_task, venues):
            progress(f"history: {venue} done")
    context.history = load_history(workspace, venues, context, _STATE["history_last"])
    ordered = sorted(specs, key=lambda spec: -_expected_cost(spec))
    progress(f"runs: {len(ordered)}")
    with pool_context.Pool(workers) as pool:
        for done, run_id in enumerate(pool.imap_unordered(_run_spec, ordered), 1):
            progress(f"runs: {done}/{len(ordered)} ({run_id})")
    # ruling 3a: the run states and every history link, then every run link
    _STATE["audit_bindings"] = {venue: audit_binding(context, venue, _base_record(workspace, context, venue)) for venue in venues}
    history_instants = sorted({row.decision_at for venue in venues for row in context.history[venue]}, reverse=True)
    tasks: list[tuple[str, Any]] = [("state", venue) for venue in venues] + [("history", instant) for instant in history_instants]
    progress(f"audit: {len(venues)} run states and {len(history_instants)} history instants")
    with pool_context.Pool(workers) as pool:
        for done, name in enumerate(pool.imap_unordered(_audit_phase_one, tasks), 1):
            progress(f"audit: {done}/{len(tasks)} ({name})")
    _STATE["audit_states"] = {venue: load_audit_state(workspace, venue, _STATE["audit_bindings"][venue]) for venue in venues}
    run_instants = sorted({instant for state in _STATE["audit_states"].values() for instant in state.run_instants}, reverse=True)
    progress(f"audit: {len(run_instants)} run instants")
    with pool_context.Pool(workers) as pool:
        for done, name in enumerate(pool.imap_unordered(_audit_phase_two, run_instants), 1):
            progress(f"audit: run {done}/{len(run_instants)} ({name})")


# --- the command line -------------------------------------------------------------------------------

def build_registry(preregistration: Mapping[str, Any], champion: StrategyConfig) -> Registry:
    registry = Registry(champion=champion)
    registry.add(Variant(CHAMPION, champion, "CHAMPION"))
    for variant in sweep_variants(preregistration["threshold_sweeps"]["sweeps"], champion):
        registry.add(variant)
    registry.add(ablation_variant(preregistration["ablation"], champion))
    return registry


def _write_fresh(directory: Path, files: Mapping[str, bytes]) -> None:
    """Write each file whole; refuse to replace an existing one (a report is produced once)."""

    directory.mkdir(parents=True, exist_ok=True)
    for name in files:
        if (directory / name).exists():
            raise RunnerRefused("OUTPUT_REFUSED", f"{name} already exists in {directory}")
    for name, data in files.items():
        partial = directory / (name + ".partial")
        partial.write_bytes(data)
        partial.replace(directory / name)


REFUSED_REPORT_FILE = "refused_report.json"


def publish(report: Mapping[str, Any], files: Mapping[str, bytes], *, private: Path, public: Path, workspace: Workspace) -> None:
    """Write the private files and the public index, only if every required check passed (review F4).

    Otherwise nothing is published: the report and its refusals go to the
    private work directory alone, and the command fails.
    """

    from btc_predictor.research_backtest import runner_report as report_module

    refusals = report_module.publication_refusals(report)
    if refusals:
        _write_whole(workspace.directory / REFUSED_REPORT_FILE, canonical_json_bytes({"refusals": refusals, "report": report}))
        raise RunnerRefused(
            "PUBLICATION_REFUSED", f"{len(refusals)} required check(s) failed, nothing published: {refusals[:5]} (see {REFUSED_REPORT_FILE})"
        )
    _write_fresh(private, files)
    index_file = report_module.public_index(report, files, private_commit=None)
    _write_fresh(public, {report_module.INDEX_FILE: canonical_json_bytes(index_file)})


def main(argv: Sequence[str] | None = None, *, out: Callable[[str], None] = print) -> int:
    import argparse
    import os

    if not fresh_bytecode_process():
        # review N2: never run again from an ordinary process, whose startup has already run
        out(f"refused: FROZEN_CODE_REFUSED: start the runner with {LAUNCHER}, which starts Python isolated, without site and with an empty bytecode cache")
        return 2

    from btc_predictor.config.strategy import load_strategy_config
    from btc_predictor.research_backtest import backfill_run as run
    from btc_predictor.research_backtest import dataset_build as build
    from btc_predictor.research_backtest import runner_report as report_module

    parser = argparse.ArgumentParser(prog="runner", description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("run", "preflight"), help="run: the backtest; preflight: the launch checks alone")
    parser.add_argument("--store", default="~/backtest_evidence", help="the private evidence repository (Part B ruling 9)")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    args = parser.parse_args(argv)
    if args.command == "preflight":
        return preflight(build.PUBLIC_REPOSITORY, out)
    try:
        repository = build.PUBLIC_REPOSITORY
        code = build.code_commit(repository)  # refuses uncommitted tracked changes
        preregistration = read_preregistration(repository)
        frozen_paths, checked = require_frozen_code(repository, preregistration["code_commit"])
        champion = load_strategy_config()
        verify_preregistration(preregistration, champion)
        store = run.EvidenceStore(Path(args.store).expanduser(), public_repository=repository)
        frozen = load_frozen_inputs(store)
        verify_preregistration(preregistration, champion, frozen)
        registry = build_registry(preregistration, champion)
        venues = [venue for venue in rm.VENUE_ORDER if venue in frozen.inputs]
        digest = (repository / PREREGISTRATION_DIGEST_PATH).read_text().split()[0]
        binding = {
            "runner_version": RUNNER_VERSION,
            "run_code_commit": code,
            "frozen_code_commit": preregistration["code_commit"],
            "preregistration_sha256": digest,
            "private_dataset_commit": frozen.private_commit,
            "dataset_index_sha256": frozen.index_sha256,
            "venues": venues,
        }
        context = RunContext(
            inputs=frozen.inputs,
            registry=registry,
            evaluation=evaluation_windows(preregistration),
            golden=golden_scenarios(repository),
            binding=binding,
        )
        specs = run_plan(venues, registry, context.golden)
        private = store.root / prereg.ARTIFACT_DIRECTORY.name  # research_backtest_v1/, the public layout (ruling 9)
        workspace = Workspace(private / "rbt007_work")
        out(f"RBT-007 run at {code[:7]}: {len(specs)} runs on {len(venues)} venues, {args.workers} workers")
        execute_all(
            context,
            specs,
            workspace,
            workers=args.workers,
            precompute_venue=venues[0],
            progress=out,
            frozen_code=(repository, preregistration["code_commit"], checked),
        )
        records = {}
        for spec in specs:
            record = read_run(workspace.directory, spec, context)
            if record is None:
                raise RunnerRefused("RUN_REFUSED", f"{spec.run_id} has no record")
            records[spec.run_id] = record
        audits = {
            venue: read_audit(workspace, venue, context, audit_binding(context, venue, records[RunSpec(HEADLINE, venue, CHAMPION, prereg.HEADLINE_COST_RUNG).run_id]))
            for venue in venues
        }
        gaps = {}
        for venue in venues:
            start, last = context.evaluation[venue]
            instants = [instant for instant in prereg.decision_schedule() if start <= instant <= last]
            gaps[venue] = report_module.gap_exposure(context.inputs[venue], instants)
        index = json.loads((repository / build.INDEX_PATH).read_bytes())
        identity = {
            "runner_version": RUNNER_VERSION,
            "ticket": RUNNER_TICKET,
            "run_code_commit": code,
            "frozen_code_commit": preregistration["code_commit"],
            "frozen_code_files_checked": len(frozen_paths),
            "private_dataset_commit": frozen.private_commit,
            "dataset_index_sha256": frozen.index_sha256,
            "fold_bars": context.fold_bars,
            "venues": venues,
            "rulings": "RBT-007 owner rulings 1-7, the runtime ruling and review ruling 3a (2026-11-18)",
        }
        report, files = report_module.build_report(
            preregistration=preregistration,
            preregistration_sha256=digest,
            identity=identity,
            context=context,
            specs=specs,
            records=records,
            audits=audits,
            gaps=gaps,
            sweep_specs=sweep_specs(preregistration["threshold_sweeps"]["sweeps"], champion),
            coverage_index=index["coverage"],
        )
        verify_loaded_code()
        publish(report, files, private=private, public=repository / prereg.ARTIFACT_DIRECTORY, workspace=workspace)
        out(f"report written: {sorted(files)} (private), {report_module.INDEX_FILE} (public)")
        return 0
    except RunnerRefused as error:
        out(f"refused: {error}")
        return 2


if __name__ == "__main__":
    # run the imported module, not this __main__ copy: one set of classes and one state
    from btc_predictor.research_backtest import runner as _runner

    raise SystemExit(_runner.main())
