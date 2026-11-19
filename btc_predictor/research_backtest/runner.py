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
checks this before any run. A sweep candidate or the ablation variant
reaches the unchanged composers through :class:`RegisteredEntryComposer`,
which accepts only the configurations the preregistration lists.

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
    EntryDecision,
    is_daily_decision_instant,
    next_decision_instant,
)
from btc_predictor.research_backtest.management_composer import ManagementComposer
from btc_predictor.research_backtest.replay_inputs import canonical_json_bytes
from btc_predictor.research_backtest.runner_shared import ShareStatistics

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


class RecordingManagementComposer(ManagementComposer):
    """The unchanged RBT-005 composer, keeping each management call's inputs for the audit."""

    def __init__(self, entry: EntryComposer) -> None:
        super().__init__(entry)
        self.calls: dict[datetime, dict[str, Any]] = {}

    def decide(self, decision: EntryDecision, *, lifecycle: Any, nav: Decimal, armed: Any, prior_flow: Any | None) -> Any:
        self.calls[decision.row.decision_at] = {
            "decision": decision,
            "lifecycle": lifecycle,
            "nav": nav,
            "armed": armed,
            "prior_flow": prior_flow,
        }
        return super().decide(decision, lifecycle=lifecycle, nav=nav, armed=armed, prior_flow=prior_flow)


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


def fold_decisions(bars: Sequence[OhlcvBar], plan: Any) -> list[dict[str, Any]]:
    """Each fold's first and last decision instant, from its bars' engine availability."""

    folds = []
    for window in walk_forward_windows([bar.timestamp for bar in bars], plan=plan):
        available = [_bar_available_at(bar) for bar in bars[window.test_start_index : window.test_stop_index]]
        instants = [moment for moment in available if moment.hour == 0 and moment.minute == 0]
        folds.append(
            {
                "fold_number": window.fold_number,
                "first_decision": instants[0].isoformat() if instants else None,
                "last_decision": instants[-1].isoformat() if instants else None,
                "decisions": len(instants),
                "bars": window.test_periods,
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

    def seed(self, venue: str, first: datetime) -> tuple[Any, ...]:
        rows = tuple(row for row in self.history.get(venue, ()) if row.decision_at < first)
        if rows and rows[-1].decision_at != first - _DAY:
            raise RunnerRefused("HISTORY_REFUSED", f"{venue}'s history does not reach {first.isoformat()}")
        return rows


@dataclass
class RunOutcome:
    spec: RunSpec
    record: dict[str, Any]
    validation: WalkForwardValidation | None = None
    result: BacktestResult | None = None
    composers: list[ManagementComposer] = field(default_factory=list)


MEMORY_FIELDS = ("regime", "capitulation_flag_state")


def memory_check(context: RunContext, venue: str, composers: Sequence[ManagementComposer]) -> dict[str, Any]:
    """Ruling 7's check: every composed row's market memory equals the continuous history's.

    The regime (its score, the smoothed score and the classification) and the
    capitulation flag state depend on the market alone, so a run's row at an
    instant must carry the history's values exactly. A variant that reached
    that memory would fail here.
    """

    history = {row.decision_at: row for row in context.history.get(venue, ())}
    compared = 0
    mismatches = []
    for strategy in composers:
        for row in strategy.entry.run_rows():
            reference = history.get(row.decision_at)
            if reference is None:
                continue
            compared += 1
            ours, theirs = row.as_record(), reference.as_record()
            if any(ours[name] != theirs[name] for name in MEMORY_FIELDS):
                mismatches.append(row.decision_at.isoformat())
    return {"compared_rows": compared, "mismatches": mismatches, "matches_history": not mismatches and compared > 0 or not history}


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


def _trade_entries(validation: WalkForwardValidation, composers: Sequence[ManagementComposer]) -> list[dict[str, str]]:
    """Per fold, each trade's index and the decision instant of the ARM_ENTRY row that opened it."""

    out = []
    for fold, strategy in zip(validation.folds, composers, strict=True):
        armed = strategy.entry.armed
        out.append({str(index): armed[trade.fills[0].source_event_id].row.decision_at.isoformat() for index, trade in enumerate(fold.result.trades)})
    return out


def _single_run(spec: RunSpec, context: RunContext, variant: Variant, inputs: EntryComposerInputs, window: Sequence[OhlcvBar], *, first: datetime, record_management: bool, starting_nav: Decimal | None = None) -> tuple[BacktestResult, ManagementComposer]:
    entry = RegisteredEntryComposer(inputs, variant=variant, registry=context.registry, history=context.seed(spec.venue, first))
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


def _unaccounted(composers: Sequence[ManagementComposer]) -> list[str]:
    return sorted(
        {f"entry:{venue}:{code}" for strategy in composers for venue, code in strategy.entry.unaccounted_causes()}
        | {f"management:{venue}:{code}" for strategy in composers for venue, code in strategy.unaccounted_causes()}
    )


def _armed_instants(result: BacktestResult, strategy: ManagementComposer) -> dict[str, str]:
    armed = strategy.entry.armed
    return {str(index): armed[trade.fills[0].source_event_id].row.decision_at.isoformat() for index, trade in enumerate(result.trades)}


def execute_run(spec: RunSpec, context: RunContext, *, record_management: bool = False) -> RunOutcome:
    """Run one spec and return its record (and, in process, its objects)."""

    if spec.kind not in RUN_KINDS:
        raise RunnerRefused("RUN_REFUSED", f"unknown run kind {spec.kind}")
    variant = context.registry.variants[spec.variant]
    inputs = context.inputs[spec.venue]
    bars = venue_bars(inputs)
    if spec.kind == GOLDEN:
        return _golden_run(spec, context, variant, inputs, bars)
    start, last = context.evaluation[spec.venue]
    end = last + _DAY
    if spec.kind in (HEADLINE, ABLATION):
        # one continuous engine run over the evaluation window, from flat
        window = tuple(bar for bar in bars if start <= _bar_available_at(bar) < end)
        result, strategy = _single_run(spec, context, variant, inputs, window, first=start, record_management=record_management)
        view = rm.single_view(result)
        record = {
            "run": spec.as_record(),
            "run_id": spec.run_id,
            "variant": variant.as_record(),
            "window": {"first_decision": start.isoformat(), "last_decision": last.isoformat(), "bars": len(window)},
            "metrics": rm.run_metrics(view),
            "result": result.as_record(),
            "entry_ledger": strategy.entry.run_records(),
            "management_ledger": strategy.ledger_records(),
            "trade_entries": _armed_instants(result, strategy),
            "unaccounted": _unaccounted([strategy]),
            "memory": memory_check(context, spec.venue, [strategy]),
            "engine_events": event_counts([result]),
        }
        return RunOutcome(spec, record, result=result, composers=[strategy])

    window = bars_before(bars, end)
    plan = fold_plan_bars(variant.config, window, start, context.fold_bars)
    composers: list[ManagementComposer] = []

    def factory(training: TrainingWindow) -> FoldStrategy:
        first = first_decision_at(_bar_available_at(window[training.window.test_start_index]))
        entry = RegisteredEntryComposer(inputs, variant=variant, registry=context.registry, history=context.seed(spec.venue, first))
        strategy = ManagementComposer(entry)
        composers.append(strategy)
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
    view = rm.validation_view(validation)
    record = {
        "run": spec.as_record(),
        "run_id": spec.run_id,
        "variant": variant.as_record(),
        "plan": plan.as_record(),
        "folds": fold_decisions(window, plan),
        "metrics": rm.run_metrics(view),
        "fold_metrics": rm.fold_metrics(view),
        "validation": validation.as_record(),
        "entry_ledgers": [strategy.entry.run_records() for strategy in composers],
        "management_ledgers": [strategy.ledger_records() for strategy in composers],
        "trade_entries": _trade_entries(validation, composers),
        "unaccounted": _unaccounted(composers),
        "memory": memory_check(context, spec.venue, composers),
        "engine_events": event_counts(fold.result for fold in validation.folds),
    }
    if spec.kind == WALK_FORWARD:
        # BTC-183 and BTC-184 attribute each filled out-of-sample trade (a BTC-182 validation)
        breakdown = run_regime_performance_breakdown(validation, _contexts(validation, composers))
        record["regime_breakdown"] = _drop_embedded(breakdown.as_record(), "validation")
        record["setup_report"] = _drop_embedded(setup_performance_report_from_breakdown(breakdown).as_record(), "source_breakdown")
    return RunOutcome(spec, record, validation=validation, composers=composers)


def golden_window(scenario: Mapping[str, Any]) -> tuple[datetime, datetime]:
    """The decision instants at the close of each golden session day: (first, last)."""

    first_day = date.fromisoformat(scenario["period"]["start"])
    last_day = date.fromisoformat(scenario["period"]["end"])
    first = datetime(first_day.year, first_day.month, first_day.day, tzinfo=UTC) + _DAY
    last = datetime(last_day.year, last_day.month, last_day.day, tzinfo=UTC) + _DAY
    return first, last


def _golden_run(spec: RunSpec, context: RunContext, variant: Variant, inputs: EntryComposerInputs, bars: Sequence[OhlcvBar]) -> RunOutcome:
    scenario = context.golden[spec.scenario]
    first, last = golden_window(scenario)
    window = tuple(bar for bar in bars if first <= _bar_available_at(bar) < last + _DAY)
    result, strategy = _single_run(
        spec, context, variant, inputs, window, first=first, record_management=False, starting_nav=Decimal(scenario["starting_nav"])
    )
    entry = strategy.entry
    rows = {row.decision_at: row for row in entry.run_rows()}
    beside = []
    for scripted in scenario["plan"]["decisions"]:
        day = date.fromisoformat(scripted["on"])
        instant = datetime(day.year, day.month, day.day, tzinfo=UTC) + _DAY
        row = rows.get(instant)
        managed = next((item for item in strategy.ledger if item.decision_at == instant), None)
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
    record = {
        "run": spec.as_record(),
        "run_id": spec.run_id,
        "window": {"first_decision": first.isoformat(), "last_decision": last.isoformat(), "bars": len(window)},
        "engine_reason_codes": list(result.reason_codes),
        "engine_refused": "BACKTEST_INTENT_REFUSED" in result.reason_codes,
        "decisions_beside_scripted": beside,
        "result": result.as_record(),
        "entry_ledger": entry.run_records(),
        "management_ledger": strategy.ledger_records(),
        "memory": memory_check(context, spec.venue, [strategy]),
    }
    return RunOutcome(spec, record, result=result, composers=[strategy])


# --- checkpoint files ---------------------------------------------------------------------------


def run_file(directory: Path, spec: RunSpec) -> Path:
    name = hashlib.sha256(spec.run_id.encode()).hexdigest()[:24]
    return Path(directory) / "runs" / f"{name}.json.gz"


def write_run(directory: Path, outcome: RunOutcome) -> Path:
    """Write a run's record whole, then rename: a resumed run reads complete records only."""

    path = run_file(directory, outcome.spec)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = gzip.compress(canonical_json_bytes(outcome.record), mtime=0)
    partial = path.with_name(path.name + ".partial")
    partial.write_bytes(data)
    partial.replace(path)
    return path


def read_run(directory: Path, spec: RunSpec) -> dict[str, Any] | None:
    path = run_file(directory, spec)
    if not path.exists():
        return None
    record = json.loads(gzip.decompress(path.read_bytes()))
    if record.get("run_id") != spec.run_id:
        raise RunnerRefused("CHECKPOINT_REFUSED", f"{path.name} does not hold {spec.run_id}")
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


def frozen_code_paths(repository: Path, modules: Iterable[Any]) -> list[str]:
    """Every loaded repository module outside the runner and the tests, and the frozen data files."""

    root = (repository / "btc_predictor").resolve()
    paths = set()
    for module in modules:
        location = getattr(module, "__file__", None)
        if not location:
            continue
        resolved = Path(location).resolve()
        if root not in resolved.parents or resolved.suffix != ".py":
            continue
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


def require_frozen_code(repository: Path, commit: str) -> list[str]:
    """Refuse unless every loaded repository module and frozen file equals ``commit``'s; return the paths."""

    import sys

    paths = frozen_code_paths(repository, list(sys.modules.values()))
    mismatches = frozen_code_mismatches(repository, commit, paths)
    if mismatches:
        raise RunnerRefused("FROZEN_CODE_REFUSED", f"{len(mismatches)} file(s) differ from {commit[:7]}: {mismatches[:5]}")
    return paths


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


# --- the look-ahead audit (ruling 3) -----------------------------------------------------------------

AUDIT_VERSION = "RBT007_LOOKAHEAD_AUDIT_V1"
AUDIT_SEEDED_INSTANTS = 20


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
    """Every intent instant, plus 20 instants drawn by a fixed seed from the rest of the window."""

    intents = set(intent_instants)
    rest = [instant for instant in instants if instant not in intents]
    ranked = sorted(rest, key=lambda instant: hashlib.sha256(f"{AUDIT_VERSION}:{venue}:{instant.isoformat()}".encode()).hexdigest())
    chosen = [(instant, "INTENT") for instant in intents] + [(instant, "SEEDED") for instant in ranked[:AUDIT_SEEDED_INSTANTS]]
    return sorted(chosen)


def _same(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    return canonical_json_bytes(a) == canonical_json_bytes(b)


def audit_shard(
    venue: str,
    context: RunContext,
    checkpoint: Mapping[str, Any],
    shard: int,
    shards: int,
    share: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    """Reproduce the champion's base headline run, then audit one shard of its sample unshared.

    ``share`` returns a context manager serving the shared positioning
    results; it wraps only the reproduction and the prior-flow recomputation,
    never an audited decision.
    """

    from contextlib import nullcontext

    spec = RunSpec(HEADLINE, venue, CHAMPION, prereg.HEADLINE_COST_RUNG)
    with (share() if share is not None else nullcontext()):
        outcome = execute_run(spec, context, record_management=True)
    reproduced = _same(outcome.record, checkpoint)
    strategy = outcome.composers[0]
    entry_rows = {row.decision_at: row for row in strategy.entry.run_rows()}
    all_rows = tuple(strategy.entry.ledger)
    all_rows_by_instant = {row.decision_at: row for row in all_rows}
    management_rows = {row.decision_at: row for row in strategy.ledger}
    intents = {row.decision_at for row in entry_rows.values() if row.intent is not None}
    intents |= {row.decision_at for row in management_rows.values() if row.intent is not None}
    start, last = context.evaluation[venue]
    instants = sorted(instant for instant in entry_rows if start <= instant <= last)
    sample = audit_sample(venue, instants, intents)
    champion = context.registry.variants[CHAMPION]
    results = []
    for position, (instant, reason) in enumerate(sample):
        if position % shards != shard:
            continue
        truncated = truncated_inputs(context.inputs[venue], instant)
        row = entry_rows[instant]
        # the composer's own earlier rows are its state at the instant (ruling 7)
        before = tuple(item for item in all_rows if item.decision_at < instant)
        fresh = RegisteredEntryComposer(truncated, variant=champion, registry=context.registry, history=before)
        decision = fresh.decide(instant, position_open=row.position_open)
        entry_equal = _same(decision.row.as_record(), row.as_record())
        item: dict[str, Any] = {"decision_at": instant.isoformat(), "reason": reason, "entry_row_equal": entry_equal}
        call = getattr(strategy, "calls", {}).get(instant)
        if call is not None:
            prior = call["prior_flow"]
            prior_equal = None
            if prior is not None:
                previous = instant - _DAY
                with (share() if share is not None else nullcontext()):
                    earlier = RegisteredEntryComposer(
                        truncated,
                        variant=champion,
                        registry=context.registry,
                        history=tuple(item for item in all_rows if item.decision_at < previous),
                    ).decide(previous, position_open=all_rows_by_instant[previous].position_open)
                prior_equal = earlier.composition is not None and earlier.composition.flow == prior
            managed = ManagementComposer(fresh).decide(
                decision, lifecycle=call["lifecycle"], nav=call["nav"], armed=call["armed"], prior_flow=prior
            )
            item["management_row_equal"] = _same(managed.row.as_record(), management_rows[instant].as_record())
            item["prior_flow_equal"] = prior_equal
        results.append(item)
    return {
        "venue": venue,
        "shard": shard,
        "shards": shards,
        "reproduced": reproduced,
        "sample_size": len(sample),
        "intent_instants": len(intents),
        "audited": results,
    }


def audit_summary(venue: str, shards: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    audited = sorted((item for shard in shards for item in shard["audited"]), key=lambda item: item["decision_at"])
    failures = [
        item["decision_at"]
        for item in audited
        if not item["entry_row_equal"] or item.get("management_row_equal") is False or item.get("prior_flow_equal") is False
    ]
    sizes = {shard["sample_size"] for shard in shards}
    sample_size = next(iter(sizes)) if len(sizes) == 1 else None
    reproduced = all(shard["reproduced"] for shard in shards)
    return {
        "venue": venue,
        "audit_version": AUDIT_VERSION,
        "rule": "every intent instant of the champion's base evaluation-window run, plus 20 instants drawn by a fixed seed; each recomputed unshared on inputs truncated at its instant",
        "sample_size": sample_size,
        "audited": len(audited),
        "intent_instants": sum(1 for item in audited if item["reason"] == "INTENT"),
        "seeded_instants": sum(1 for item in audited if item["reason"] == "SEEDED"),
        "management_checked": sum(1 for item in audited if "management_row_equal" in item),
        "reproduced_by_every_shard": reproduced,
        "failures": failures,
        "passed": not failures and reproduced and sample_size is not None and len(audited) == sample_size,
        "instants": audited,
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


def _history_task(venue: str) -> str:
    import pickle
    import time

    workspace: Workspace = _STATE["workspace"]
    path = history_file(workspace, venue)
    if path.exists():
        return venue
    _STATE["statistics"] = ShareStatistics()
    share = _share_factory()
    started = time.monotonic()
    with share():
        context = _STATE["context"]
        rows = continuous_history(context.inputs[venue], context.registry.champion, _STATE["history_last"], context.schedule)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    partial.write_bytes(pickle.dumps(rows, protocol=5))
    partial.replace(path)
    _log({"event": "history", "venue": venue, "rows": len(rows), "seconds": round(time.monotonic() - started, 1), "share": _STATE["statistics"].as_record()})
    return venue


def load_history(workspace: Workspace, venues: Iterable[str]) -> dict[str, tuple[Any, ...]]:
    import pickle

    return {venue: pickle.loads(history_file(workspace, venue).read_bytes()) for venue in venues}


def _run_spec(spec: RunSpec) -> str:
    import time

    workspace: Workspace = _STATE["workspace"]
    if run_file(workspace.directory, spec).exists():
        return spec.run_id
    _STATE["statistics"] = ShareStatistics()
    share = _share_factory()
    started = time.monotonic()
    with share():
        outcome = execute_run(spec, _STATE["context"])
    write_run(workspace.directory, outcome)
    _log({"event": "run", "run_id": spec.run_id, "seconds": round(time.monotonic() - started, 1), "share": _STATE["statistics"].as_record()})
    return spec.run_id


def _audit_task(task: tuple[str, int, int]) -> str:
    import time

    venue, shard, shards = task
    name = f"audit:{venue}:{shard}:{shards}"
    path = _marker(name)
    if path.exists():
        return name
    workspace: Workspace = _STATE["workspace"]
    checkpoint = read_run(workspace.directory, RunSpec(HEADLINE, venue, CHAMPION, prereg.HEADLINE_COST_RUNG))
    if checkpoint is None:
        raise RunnerRefused("AUDIT_REFUSED", f"{venue}'s base headline run has no record yet")
    started = time.monotonic()
    result = audit_shard(venue, _STATE["context"], checkpoint, shard, shards, share=_share_factory())
    _write_marker(name, {"result": result})
    _log({"event": "audit", "task": name, "seconds": round(time.monotonic() - started, 1)})
    return name


def read_audit(workspace: Workspace, venue: str, shards: int) -> list[dict[str, Any]]:
    out = []
    for shard in range(shards):
        _STATE.setdefault("workspace", workspace)
        path = workspace.markers / f"{hashlib.sha256(f'audit:{venue}:{shard}:{shards}'.encode()).hexdigest()[:24]}.json"
        out.append(json.loads(path.read_bytes())["result"])
    return out


def _expected_cost(spec: RunSpec) -> int:
    # longest first, so the pool's tail is short
    return {HEADLINE: 4, ABLATION: 4, WALK_FORWARD: 3, SWEEP: 3, GOLDEN: 1}[spec.kind]


def execute_all(
    context: RunContext,
    specs: Sequence[RunSpec],
    workspace: Workspace,
    *,
    workers: int,
    audit_shards: int,
    precompute_venue: str,
    progress: Callable[[str], None] = lambda line: None,
) -> None:
    """The precompute, every run and the audit, each skipped when its complete file exists."""

    import multiprocessing

    workspace.directory.mkdir(parents=True, exist_ok=True)
    _STATE.clear()
    _STATE.update({"context": context, "workspace": workspace, "precompute_inputs": context.inputs[precompute_venue]})
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
    context.history = load_history(workspace, venues)
    ordered = sorted(specs, key=lambda spec: -_expected_cost(spec))
    progress(f"runs: {len(ordered)}")
    with pool_context.Pool(workers) as pool:
        for done, run_id in enumerate(pool.imap_unordered(_run_spec, ordered), 1):
            progress(f"runs: {done}/{len(ordered)} ({run_id})")
    tasks = [(venue, shard, audit_shards) for venue in context.inputs for shard in range(audit_shards)]
    progress(f"audit: {len(tasks)} shards")
    with pool_context.Pool(workers) as pool:
        for done, name in enumerate(pool.imap_unordered(_audit_task, tasks), 1):
            progress(f"audit: {done}/{len(tasks)} ({name})")


# --- the command line -------------------------------------------------------------------------------

DEFAULT_AUDIT_SHARDS = 3


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


def main(argv: Sequence[str] | None = None, *, out: Callable[[str], None] = print) -> int:
    import argparse
    import os

    from btc_predictor.config.strategy import load_strategy_config
    from btc_predictor.research_backtest import backfill_run as run
    from btc_predictor.research_backtest import dataset_build as build
    from btc_predictor.research_backtest import runner_report as report_module

    parser = argparse.ArgumentParser(prog="runner", description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("run",))
    parser.add_argument("--store", default="~/backtest_evidence", help="the private evidence repository (Part B ruling 9)")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    parser.add_argument("--audit-shards", type=int, default=DEFAULT_AUDIT_SHARDS)
    args = parser.parse_args(argv)
    try:
        repository = build.PUBLIC_REPOSITORY
        code = build.code_commit(repository)  # refuses uncommitted tracked changes
        preregistration = read_preregistration(repository)
        frozen_paths = require_frozen_code(repository, preregistration["code_commit"])
        champion = load_strategy_config()
        verify_preregistration(preregistration, champion)
        store = run.EvidenceStore(Path(args.store).expanduser(), public_repository=repository)
        frozen = load_frozen_inputs(store)
        verify_preregistration(preregistration, champion, frozen)
        registry = build_registry(preregistration, champion)
        venues = [venue for venue in rm.VENUE_ORDER if venue in frozen.inputs]
        context = RunContext(
            inputs=frozen.inputs, registry=registry, evaluation=evaluation_windows(preregistration), golden=golden_scenarios(repository)
        )
        specs = run_plan(venues, registry, context.golden)
        private = store.root / prereg.ARTIFACT_DIRECTORY.name  # research_backtest_v1/, the public layout (ruling 9)
        workspace = Workspace(private / "rbt007_work")
        out(f"RBT-007 run at {code[:7]}: {len(specs)} runs on {len(venues)} venues, {args.workers} workers")
        execute_all(context, specs, workspace, workers=args.workers, audit_shards=args.audit_shards, precompute_venue=venues[0], progress=out)
        records = {}
        for spec in specs:
            record = read_run(workspace.directory, spec)
            if record is None:
                raise RunnerRefused("RUN_REFUSED", f"{spec.run_id} has no record")
            records[spec.run_id] = record
        audits = {venue: audit_summary(venue, read_audit(workspace, venue, args.audit_shards)) for venue in venues}
        gaps = {}
        for venue in venues:
            start, last = context.evaluation[venue]
            instants = [instant for instant in prereg.decision_schedule() if start <= instant <= last]
            gaps[venue] = report_module.gap_exposure(context.inputs[venue], instants)
        index = json.loads((repository / build.INDEX_PATH).read_bytes())
        digest = (repository / PREREGISTRATION_DIGEST_PATH).read_text().split()[0]
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
            "rulings": "RBT-007 owner rulings 1-7 and the runtime ruling (2026-11-18)",
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
        _write_fresh(private, files)
        index_file = report_module.public_index(report, files, private_commit=None)
        _write_fresh(repository / prereg.ARTIFACT_DIRECTORY, {report_module.INDEX_FILE: canonical_json_bytes(index_file)})
        out(f"report written: {sorted(files)} (private), {report_module.INDEX_FILE} (public)")
        return 0
    except RunnerRefused as error:
        out(f"refused: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
