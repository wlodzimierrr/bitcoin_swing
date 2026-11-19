"""RBT-007 report: the policy V7 section 8 report, assembled from the run records.

The report is a deterministic function of the run records, the audit, the
frozen preregistration and the frozen inputs, so it reproduces byte for byte
in a fresh process. Its first section states the evidence class, the
prohibited uses and every named limitation with its exposure counts
(ruling 5). Every value-bearing file is private (ruling 1); the public index
holds digests, sizes, counts and statuses only.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from btc_predictor.backtest.engine import TRAIL_ACTION, restore_backtest_result
from btc_predictor.backtest.threshold_sweeps import run_threshold_sweep
from btc_predictor.backtest.walk_forward import restore_walk_forward_validation
from btc_predictor.config.strategy import StrategyConfig
from btc_predictor.features.hold import HoldScoreInput, calculate_hold_score
from btc_predictor.features.momentum import FOUR_WEEK_MOMENTUM_LOOKBACK_DAYS, TWELVE_WEEK_MOMENTUM_LOOKBACK_DAYS
from btc_predictor.features.volatility import DEFAULT_VOLATILITY_PERCENTILE_WINDOW_DAYS
from btc_predictor.features.trend import FIFTY_TWO_WEEK_HIGH_DISTANCE_LOOKBACK_WEEKS, TWENTY_WEEK_MA_DISTANCE_LOOKBACK_WEEKS
from btc_predictor.research_backtest import preregistration as prereg
from btc_predictor.research_backtest import runner as rn
from btc_predictor.research_backtest import runner_metrics as rm
from btc_predictor.research_backtest.completion_spec import RETURN_HORIZON_DAILY_BARS, UNIFORM_ZSCORE_WINDOW_OBSERVATIONS
from btc_predictor.research_backtest.entry_composer import CAUSE_DECISION_PRICE_BAR_MISSING, EntryComposerInputs
from btc_predictor.research_backtest.replay_inputs import REVISION_HISTORY_UNAVAILABLE, canonical_json_bytes, replay_market_bars_at

REPORT_FILE = "rbt007_report_v1.json"
REPORT_MARKDOWN_FILE = "rbt007_report_v1.md"
INDEX_FILE = "rbt007_report_index_v1.json"
REPORT_ARTIFACT_VERSION = "RBT007_RESEARCH_BACKTEST_REPORT_V1"


def ledger_file(venue: str) -> str:
    return f"rbt007_decision_ledger_{venue.lower()}_v1.json"


EVIDENCE_CLASS = "RESEARCH_BACKTEST_NON_CERTIFYING"
CANONICAL_REFERENCE = "UNRESOLVED"
POLICY = "RESEARCH_BACKTEST_POLICY_V7"
PROHIBITED_USES = (
    "certify Phase 1.5 or any champion",
    "approve, rank or promote a price reference, composite or venue",
    "calibrate, select or tune a production parameter or threshold",
    "serve as BTC-019, V3/V4/V5 or EPIC X evidence of any kind",
    "authorize prospective collection, live shadow or capital deployment",
)


# --- the Momentum Persistence ablation's band count (policy V7 section 8) ------------------------

HOLD_BANDS = ("HOLD_POSSIBLE_ADD", "HOLD", "HOLD_NO_ADD", "DEFENSIVE", "TRIM", "EXIT")


def hold_band(score: Decimal, config: StrategyConfig) -> str:
    """Rulebook section 20's action band for a Hold Score, at the configured thresholds."""

    thresholds = config.hold_thresholds
    if score >= Decimal(str(thresholds.possible_add_min)):
        return "HOLD_POSSIBLE_ADD"
    if score >= Decimal(str(thresholds.hold_min)):
        return "HOLD"
    if score >= Decimal(str(thresholds.no_add_min)):
        return "HOLD_NO_ADD"
    if score >= Decimal(str(thresholds.defensive_min)):
        return "DEFENSIVE"
    if score >= Decimal(str(thresholds.exit_below)):
        return "TRIM"
    return "EXIT"


def _optional_decimal(value: Any) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def ablation_band_differences(management_rows: Sequence[Mapping[str, Any]], champion: StrategyConfig, variant: StrategyConfig) -> dict[str, Any]:
    """Each champion Hold evaluation, rescored with the variant's weights on the same inputs."""

    evaluations = differing = incomplete = 0
    transitions: Counter[str] = Counter()
    for row in management_rows:
        hold = row.get("hold") or {}
        if not hold or not hold.get("complete"):
            if hold:
                incomplete += 1
            continue
        inputs = hold["inputs"]
        score_input = HoldScoreInput(
            trend_score=_optional_decimal(inputs["trend"]),
            flow_score=_optional_decimal(inputs["flow"]),
            positioning_score=_optional_decimal(inputs["positioning"]),
            structure_score=_optional_decimal(inputs["structure"]),
            momentum_persistence_score=_optional_decimal(inputs["momentum_persistence"]),
        )
        champion_score = calculate_hold_score(score_input, strategy_config=champion)
        if champion_score.score != Decimal(str(hold["score"])):
            raise rn.RunnerRefused("ABLATION_REFUSED", "a recorded Hold Score does not rescore to itself")
        variant_score = calculate_hold_score(score_input, strategy_config=variant)
        if not variant_score.complete:
            incomplete += 1
            continue
        evaluations += 1
        before, after = hold_band(champion_score.score, champion), hold_band(variant_score.score, variant)
        if before != after:
            differing += 1
            transitions[f"{before}->{after}"] += 1
    return {
        "hold_evaluations": evaluations,
        "differing_action_band": differing,
        "incomplete_hold_evaluations": incomplete,
        "transitions": dict(sorted(transitions.items())),
        "rule": "Rulebook section 20's bands at the configured hold thresholds; the variant rescored on each champion evaluation's own inputs",
    }


# --- coverage and the named limitations' exposure (ruling 5) -------------------------------------


def _gapped(rows: Sequence[Any], step_days: int) -> bool:
    return any((later.timestamp - earlier.timestamp).days != step_days for earlier, later in zip(rows, rows[1:]))


# the uniform z-score's history: 20 native observations strictly before the current one
ZSCORE_PRIOR_OBSERVATIONS = UNIFORM_ZSCORE_WINDOW_OBSERVATIONS
ROW_LOOKBACKS = (
    # (owner, timeframe, rows read for its latest value, rows read with its z-score history)
    ("four_week_momentum_from_daily_bars", "1d", FOUR_WEEK_MOMENTUM_LOOKBACK_DAYS + 1, FOUR_WEEK_MOMENTUM_LOOKBACK_DAYS + 1 + ZSCORE_PRIOR_OBSERVATIONS),
    ("twelve_week_momentum_from_daily_bars", "1d", TWELVE_WEEK_MOMENTUM_LOOKBACK_DAYS + 1, TWELVE_WEEK_MOMENTUM_LOOKBACK_DAYS + 1 + ZSCORE_PRIOR_OBSERVATIONS),
    ("twenty_week_ma_distance_from_weekly_bars", "1w", TWENTY_WEEK_MA_DISTANCE_LOOKBACK_WEEKS, TWENTY_WEEK_MA_DISTANCE_LOOKBACK_WEEKS + ZSCORE_PRIOR_OBSERVATIONS),
    ("fifty_two_week_high_distance_from_weekly_bars", "1w", FIFTY_TWO_WEEK_HIGH_DISTANCE_LOOKBACK_WEEKS, FIFTY_TWO_WEEK_HIGH_DISTANCE_LOOKBACK_WEEKS + ZSCORE_PRIOR_OBSERVATIONS),
    ("price_momentum_from_daily_bars R_7", "1d", RETURN_HORIZON_DAILY_BARS + 1, RETURN_HORIZON_DAILY_BARS + 1),
    ("realized_volatility_from_daily_bars RV_7", "1d", 8, 8),
    ("realized_volatility_from_daily_bars RV_20", "1d", 21, 21),
    ("realized_volatility_from_daily_bars RV_60", "1d", 61, 61),
)
RV20_ROWS = 21


def _percentile_rows(daily: Sequence[Any]) -> Sequence[Any]:
    """The daily rows the two-year volatility percentile reads: each past RV_20 window, and the current one.

    The composer computes RV_20 at every daily bar from its last bar's
    timestamp minus 731 days, each over its own 21 rows.
    """

    if not daily:
        return ()
    start = daily[-1].timestamp - timedelta(days=DEFAULT_VOLATILITY_PERCENTILE_WINDOW_DAYS + 1)
    first = next(index for index, bar in enumerate(daily) if bar.timestamp >= start)
    return daily[max(0, first - (RV20_ROWS - 1)) :]


def gap_exposure(inputs: EntryComposerInputs, instants: Sequence[datetime]) -> dict[str, Any]:
    """Per row-based owner, the decision instants whose rows read span an omitted bar.

    The rows are the composer's own derived series at each instant (BTC-040 at
    the decision instant): a missing hour omits its day's and week's bars, and
    a row-counting owner reads the rows either side as contiguous. The union
    counts are of distinct instants (review F6).
    """

    hourly = tuple(sorted(inputs.dataset.price_bars, key=lambda bar: bar.timestamp))
    latest: dict[str, set[datetime]] = {owner: set() for owner, *_ in ROW_LOOKBACKS}
    history: dict[str, set[datetime]] = {owner: set() for owner, *_ in ROW_LOOKBACKS}
    percentile: set[datetime] = set()
    weekly: set[datetime] = set()
    omitted_days: set[str] = set()
    for instant in instants:
        visible = tuple(bar for bar in hourly if bar.ingested_at <= instant)
        canonical = replay_market_bars_at(visible, decision_at=instant, window=inputs.dataset.window)
        series = {
            "1d": tuple(bar for bar in canonical if bar.timeframe == "1d"),
            "1w": tuple(bar for bar in canonical if bar.timeframe == "1w"),
        }
        for earlier, later in zip(series["1d"], series["1d"][1:]):
            if (later.timestamp - earlier.timestamp).days != 1:
                omitted_days.add(earlier.timestamp.date().isoformat())
        for owner, timeframe, rows, rows_with_history in ROW_LOOKBACKS:
            step = 1 if timeframe == "1d" else 7
            if _gapped(series[timeframe][-rows:], step):
                latest[owner].add(instant)
            if _gapped(series[timeframe][-rows_with_history:], step):
                history[owner].add(instant)
        if _gapped(_percentile_rows(series["1d"]), 1):
            percentile.add(instant)
        if _gapped(series["1w"], 7):
            weekly.add(instant)
    volatility = set(percentile).union(*(latest[owner] for owner in latest if owner.startswith("realized_volatility")))
    rows_anywhere = set(percentile).union(*history.values())
    return {
        "instants": len(instants),
        "days_before_an_omitted_daily_bar": sorted(omitted_days),
        "latest_value": {owner: len(latest[owner]) for owner, *_ in ROW_LOOKBACKS},
        "with_zscore_history": {owner: len(history[owner]) for owner, *_ in ROW_LOOKBACKS},
        "volatility_percentile_history": len(percentile),
        "any_row_owner": len(rows_anywhere),
        "any_realized_volatility": len(volatility),
        "weekly_swing_series": len(weekly),
    }


def _contains(value: Any, code: str) -> bool:
    if isinstance(value, str):
        return value == code
    if isinstance(value, Mapping):
        return any(_contains(item, code) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains(item, code) for item in value)
    return False


def _evaluated(row: Mapping[str, Any]) -> bool:
    return CAUSE_DECISION_PRICE_BAR_MISSING not in row["reasons"]


def limitation_exposure(entry_rows: Sequence[Mapping[str, Any]], management_rows: Sequence[Mapping[str, Any]], gaps: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Ruling 5: each named limitation's exposure over the champion's base evaluation-window run."""

    evaluated = sum(1 for row in entry_rows if _evaluated(row))
    holds = sum(1 for row in management_rows if row.get("hold"))
    managed = len(management_rows)

    def coded(rows: Sequence[Mapping[str, Any]], *codes: str) -> int:
        return sum(1 for row in rows if any(_contains(row, code) for code in codes))

    def guard(*guard_ids: str) -> int:
        return sum(1 for row in entry_rows if any(item["guard_id"] in guard_ids for item in row.get("guard_refusals", ())))

    rows = [
        ("E1_FUTURES_BASIS_ZERO_VARIANCE", "spec", "RECORDED", guard("FUTURES_BASIS_ZERO_VARIANCE_GUARD_V1"), "entry rows with the guard's refusal"),
        ("E1_CLASS_FUNDING_AND_OI_GROWTH", "spec", "RECORDED", guard("FUNDING_HEALTH_ZERO_VARIANCE_GUARD_V1", "OI_GROWTH_ZERO_VARIANCE_GUARD_V1"), "entry rows with either guard's refusal, each instant once"),
        ("MOMENTUM_PERSISTENCE_OVERLAP", "spec", "EVERY_COMPOSITION", holds, "every Hold evaluation"),
        ("REACTION_UNIT", "spec", "EVERY_COMPOSITION", evaluated, "every evaluated instant"),
        ("LEVEL_STRENGTH_OWNER_TABLES", "spec", "EVERY_COMPOSITION", evaluated, "every evaluated instant"),
        ("FLOW_OWNER_BANDS", "spec", "EVERY_COMPOSITION", evaluated, "every evaluated instant"),
        ("ROW_BASED_LOOKBACKS", "spec", "DETECTED", gaps["any_row_owner"], "distinct instants at which any row-counting owner's rows, with its z-score history or the volatility percentile's RV_20 history, span an omitted bar (per owner in gap_exposure)"),
        ("SEVERE_CROWDING_IS_CROWDING", "spec", "RECORDED", sum(1 for row in entry_rows if (row.get("flags") or {}).get("crowding", {}).get("flagged") is True), "entry rows with CROWDING flagged"),
        ("LEVEL_VOLUME_PRE_WARM_UP_PIVOTS", "spec", "RECORDED", coded(entry_rows, "LEVEL_VOLUME_PERCENTILE_WARM_UP"), "entry rows recording LEVEL_VOLUME_PERCENTILE_WARM_UP"),
        ("STRESS_NON_DISCRETIONARY_MISSING", "spec", "RECORDED", sum(1 for row in entry_rows if _evaluated(row) and (row.get("flags") or {}).get("stress", {}).get("mapped", False) is None), "evaluated entry rows whose STRESS veto input is None (fails closed)"),
        ("UNMODELLED_ADD_AND_REDUCE_RULES", "spec", "EVERY_COMPOSITION", managed, "every management evaluation"),
        ("LEVEL_FAMILIES_NOT_RULED", "spec", "RECORDED", coded(entry_rows, "LEVEL_REACTION_MAGNITUDE_NO_SWING_MEMBER", "LEVEL_VOLUME_PERCENTILE_NO_SWING_MEMBER"), "entry rows recording a NO_SWING_MEMBER level input"),
        ("ONE_ADD_PER_STRUCTURE", "spec", "RECORDED", sum(1 for row in management_rows if (row.get("intent") or {}).get("action") == TRAIL_ACTION and (row.get("add") or {}).get("outcome") not in ("ADD", "PENDING_TRAIL")), "management rows whose TRAIL consumed a higher low while the add did not pass"),
        ("TRANCHE_SCHEDULE_EXHAUSTED", "spec", "RECORDED", coded(management_rows, "TRANCHE_SIZING_SCHEDULE_EXHAUSTED"), "management rows recording TRANCHE_SIZING_SCHEDULE_EXHAUSTED"),
        ("WEEKLY_SWING_ROW_VS_SESSION", "policy V7 section 7", "DETECTED", gaps["weekly_swing_series"], "instants whose weekly series, which the swing detector reads whole, holds an omitted week"),
        ("REALIZED_VOLATILITY_GAPPED_SERIES", "policy V7 section 7", "DETECTED", gaps["any_realized_volatility"], "distinct instants whose RV 7/20/60 rows, or the RV_20 windows the volatility percentile reads, span an omitted day"),
        ("BTC186_FIFTH_CANDIDATE", "policy V7 section 7", "NOT_COMPOSED", 0, "the champion does not compose the BTC-186 fifth candidate"),
        ("RULEBOOK_24_NO_ADDING_ENFORCED", "policy V7 section 7", "RECORDED", coded(management_rows, "RULEBOOK_24_NO_ADDING_ENFORCED"), "management rows recording the enforced NO ADDING"),
        ("STRESS_MAPPING_EUPHORIA_TRIMS_NEVER_FIRE", "policy V7 section 7", "EVERY_COMPOSITION", managed, "every management evaluation (trim_rules_from_results passes None)"),
    ]
    return [
        {"limitation_id": name, "source": source, "kind": kind, "exposed_instants": count, "method": method, "evaluated_instants": evaluated}
        for name, source, kind, count, method in rows
    ]


def revision_history_counts(entry_rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """Per input family, the entry rows whose visible record carries REVISION_HISTORY_UNAVAILABLE."""

    counts: Counter[str] = Counter()
    for row in entry_rows:
        for family, codes in (row.get("input_reason_codes") or {}).items():
            if REVISION_HISTORY_UNAVAILABLE in codes:
                counts[family] += 1
    return dict(sorted(counts.items()))


# --- assembly ------------------------------------------------------------------------------------


def _outcomes(entry_rows: Sequence[Mapping[str, Any]], management_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "entry": dict(sorted(Counter(row["outcome"] for row in entry_rows).items())),
        "entry_reasons": dict(sorted(Counter(reason for row in entry_rows for reason in row["reasons"]).items())),
        "management": dict(sorted(Counter(row["outcome"] for row in management_rows).items())),
    }


def sweep_reports(specs: Sequence[tuple[Mapping[str, Any], Any]], variants: Sequence[rn.Variant], records: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    """One BTC-185 report per swept value, from its candidates' restored walk-forwards."""

    out = []
    for index, (record, spec) in enumerate(specs):
        if spec is None:
            out.append({"parameter": record["parameter"], "status": record["status"], "report": None})
            continue
        validations = {
            variant.variant_id: restore_walk_forward_validation(records[variant.variant_id]["validation"])
            for variant in variants
            if variant.sweep_index == index
        }
        report = run_threshold_sweep(spec, evaluator=lambda parameter_set: validations[parameter_set.parameter_set_id])
        out.append(
            {
                "parameter": record["parameter"],
                "configured_value": record["configured_value"],
                "parameter_paths": record["parameter_paths"],
                "label": prereg.SENSITIVITY_ONLY,
                "status": record["status"],
                "candidates": [
                    {
                        "variant_id": variant.variant_id,
                        "value": variant.value,
                        "metrics": records[variant.variant_id]["metrics"],
                        "engine_events": records[variant.variant_id]["engine_events"],
                    }
                    for variant in variants
                    if variant.sweep_index == index
                ],
                "report": _sweep_summary(report),
            }
        )
    return out


def _sweep_summary(report: Any) -> dict[str, Any]:
    """BTC-185's report without each point's full validation (kept, with its digest, in the run records)."""

    record = report.as_record()
    return {
        "report_id": record["report_id"],
        "evidence_digest": record["evidence_digest"],
        "spec": record["spec"],
        "points": [
            {
                "parameter_set": point["parameter_set"],
                "validation_id": point["validation"]["validation_id"],
                "validation_evidence_digest": point["validation"]["evidence_digest"],
                "metrics": point["metrics"],
            }
            for point in record["points"]
        ],
        "plateaus": record["plateaus"],
        "best_parameter_set_id": record["best_parameter_set_id"],
        "isolated_optimum": record["isolated_optimum"],
        "reason_codes": record["reason_codes"],
        "label": prereg.SENSITIVITY_ONLY,
    }


def ruling4_check(venue: str, folds: Sequence[Mapping[str, Any]], frozen: Mapping[str, Any]) -> dict[str, Any]:
    """Each fold's decision range against the preregistered daily folds (ruling 4).

    ``equal`` compares the dates as they are. ``consistent`` is the required
    comparison: each preregistered boundary, moved by the hourly bars omitted
    before it, gives the run's first and last decision; a venue without
    omitted hours must equal its preregistered folds.
    """

    hour = timedelta(hours=1)
    expected = [
        {"fold_number": item["fold_number"], "first_decision": item["test_start"], "last_decision": item["test_end"]}
        for item in frozen["walk_forward"]["folds"]
    ]
    actual = [{key: fold[key] for key in ("fold_number", "first_decision", "last_decision")} for fold in folds]
    shifted = []
    for item, fold in zip(frozen["walk_forward"]["folds"], folds, strict=False):
        start = datetime.fromisoformat(item["test_start"]) + fold["omitted_hours_before_start"] * hour
        end = datetime.fromisoformat(item["test_end"]) + timedelta(days=1) + fold["omitted_hours_before_end"] * hour
        shifted.append(
            {
                "fold_number": item["fold_number"],
                "first_decision": rn.first_decision_at(start).isoformat(),
                "last_decision": (rn.first_decision_at(end) - timedelta(days=1)).isoformat(),
            }
        )
    return {
        "venue": venue,
        "preregistered": expected,
        "run": actual,
        "equal": expected == actual,
        "omitted_hours": [[fold["omitted_hours_before_start"], fold["omitted_hours_before_end"]] for fold in folds],
        "preregistered_moved_by_omitted_hours": shifted,
        "consistent": len(folds) == len(expected) and shifted == actual,
        "decisions_per_fold": [fold["decisions"] for fold in folds],
    }


def publication_refusals(report: Mapping[str, Any]) -> list[str]:
    """Every required check that failed (review F4); the report is published only when there is none."""

    integrity = report["integrity"]
    refusals = []
    if integrity["runs"] != integrity["planned_runs"]:
        refusals.append("RUNS_INCOMPLETE")
    refusals += [f"MEMORY_MISMATCH:{run_id}" for run_id, matches in integrity["memory_matches_history"].items() if not matches]
    refusals += [f"UNACCOUNTED_CAUSES:{run_id}" for run_id in integrity["unaccounted"]]
    refusals += [f"LOOKAHEAD_AUDIT_FAILED:{venue}" for venue, audit in report["lookahead_audit"].items() if not audit["passed"]]
    refusals += [f"FOLD_DATES_INCONSISTENT:{venue}" for venue, entry in report["walk_forward"].items() if not entry["ruling_4"]["consistent"]]
    refusals += [
        f"GOLDEN_ENGINE_REFUSED:{scenario}:{venue}"
        for scenario, venues in report["golden_replays"].items()
        for venue, item in venues.items()
        if item["engine_refused"]
    ]
    return refusals


def build_report(
    *,
    preregistration: Mapping[str, Any],
    preregistration_sha256: str,
    identity: Mapping[str, Any],
    context: rn.RunContext,
    specs: Sequence[rn.RunSpec],
    records: Mapping[str, Mapping[str, Any]],
    audits: Mapping[str, Mapping[str, Any]],
    gaps: Mapping[str, Mapping[str, Any]],
    sweep_specs: Sequence[tuple[Mapping[str, Any], Any]],
    coverage_index: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, bytes]]:
    """The report and every private file: the decision ledgers and the report itself."""

    venues = [venue for venue in rm.VENUE_ORDER if venue in context.inputs]
    by_id = {spec.run_id: spec for spec in specs}

    def record(kind: str, venue: str, variant: str, rung: str, scenario: str | None = None) -> Mapping[str, Any]:
        return records[rn.RunSpec(kind, venue, variant, rung, scenario).run_id]

    base = prereg.HEADLINE_COST_RUNG
    files: dict[str, bytes] = {}
    headline: dict[str, Any] = {}
    walk_forward: dict[str, Any] = {}
    breakdowns: dict[str, Any] = {}
    limitations: dict[str, Any] = {}
    ledgers: dict[str, Any] = {}
    coverage: dict[str, Any] = {}
    for venue in venues:
        headline[venue] = {
            rung: {"window": record(rn.HEADLINE, venue, rn.CHAMPION, rung)["window"], "metrics": record(rn.HEADLINE, venue, rn.CHAMPION, rung)["metrics"]}
            for rung in prereg.COST_RUNGS
        }
        walk_forward[venue] = {
            rung: {
                "plan": record(rn.WALK_FORWARD, venue, rn.CHAMPION, rung)["plan"],
                "folds": record(rn.WALK_FORWARD, venue, rn.CHAMPION, rung)["folds"],
                "metrics": record(rn.WALK_FORWARD, venue, rn.CHAMPION, rung)["metrics"],
                "fold_metrics": record(rn.WALK_FORWARD, venue, rn.CHAMPION, rung)["fold_metrics"],
            }
            for rung in prereg.COST_RUNGS
        }
        walk_forward[venue]["ruling_4"] = ruling4_check(venue, record(rn.WALK_FORWARD, venue, rn.CHAMPION, base)["folds"], preregistration["venues"][venue])
        breakdowns[venue] = {
            rung: {
                "regime": record(rn.WALK_FORWARD, venue, rn.CHAMPION, rung)["regime_breakdown"],
                "setup": record(rn.WALK_FORWARD, venue, rn.CHAMPION, rung)["setup_report"],
            }
            for rung in prereg.COST_RUNGS
        }
        champion_base = record(rn.HEADLINE, venue, rn.CHAMPION, base)
        limitations[venue] = limitation_exposure(champion_base["entry_ledger"], champion_base["management_ledger"], gaps[venue])
        ledger = {
            "ledger_version": REPORT_ARTIFACT_VERSION + ":DECISION_LEDGER",
            "venue": venue,
            "run": champion_base["run"],
            "evidence_class": EVIDENCE_CLASS,
            "entry_rows": champion_base["entry_ledger"],
            "management_rows": champion_base["management_ledger"],
        }
        data = canonical_json_bytes(ledger)
        files[ledger_file(venue)] = data
        ledgers[venue] = {
            "file": ledger_file(venue),
            "sha256": hashlib.sha256(data).hexdigest(),
            "instants": len(champion_base["entry_ledger"]),
            "outcomes": _outcomes(champion_base["entry_ledger"], champion_base["management_ledger"]),
        }
        coverage[venue] = {
            "revision_history_unavailable_rows": revision_history_counts(champion_base["entry_ledger"]),
            "completeness": preregistration["venues"][venue]["completeness"],
            "gap_exposure": gaps[venue],
        }

    cross_venue = rm.cross_venue(
        entries={venue: [row for row in record(rn.HEADLINE, venue, rn.CHAMPION, base)["entry_ledger"] if row["outcome"] == "ARM_ENTRY"] for venue in venues},
        trades={venue: restore_backtest_result(record(rn.HEADLINE, venue, rn.CHAMPION, base)["result"]).trades for venue in venues},
        trade_entries={venue: {int(index): instant for index, instant in record(rn.HEADLINE, venue, rn.CHAMPION, base)["trade_entries"].items()} for venue in venues},
        metrics={rung: {venue: record(rn.HEADLINE, venue, rn.CHAMPION, rung)["metrics"] for venue in venues} for rung in prereg.COST_RUNGS},
    )

    registry = context.registry
    sweep_variants = [variant for variant in registry.variants.values() if variant.role == rn.SWEEP]
    ablation = next(variant for variant in registry.variants.values() if variant.role == rn.ABLATION)
    sweeps = {}
    ablation_section = {}
    for venue in venues:
        venue_records = {variant.variant_id: record(rn.SWEEP, venue, variant.variant_id, prereg.SWEEP_COST_RUNG) for variant in sweep_variants}
        sweeps[venue] = sweep_reports(sweep_specs, sweep_variants, venue_records)
        champion_base = record(rn.HEADLINE, venue, rn.CHAMPION, base)
        variant_run = record(rn.ABLATION, venue, ablation.variant_id, base)
        ablation_section[venue] = {
            "label": prereg.SENSITIVITY_ONLY,
            "variant_id": ablation.variant_id,
            "band_differences": ablation_band_differences(champion_base["management_ledger"], registry.champion, ablation.config),
            "variant_metrics": variant_run["metrics"],
            "champion_metrics": champion_base["metrics"],
        }

    golden = {}
    for venue in venues:
        for scenario_id in sorted(context.golden):
            item = record(rn.GOLDEN, venue, rn.CHAMPION, context.golden[scenario_id]["cost_profile"], scenario_id)
            golden.setdefault(scenario_id, {})[venue] = {
                "window": item["window"],
                "engine_refused": item["engine_refused"],
                "decisions_beside_scripted": item["decisions_beside_scripted"],
                "before_evaluation_start": datetime.fromisoformat(item["window"]["first_decision"]) < context.evaluation[venue][0],
            }

    integrity = {
        "memory_matches_history": {run_id: records[run_id]["memory"]["matches_history"] for run_id in sorted(records)},
        "unaccounted": {run_id: records[run_id].get("unaccounted", []) for run_id in sorted(records) if records[run_id].get("unaccounted")},
        "runs": len(records),
        "planned_runs": len(by_id),
    }
    report = {
        "evidence": {
            "evidence_class": EVIDENCE_CLASS,
            "canonical_reference": CANONICAL_REFERENCE,
            "policy": POLICY,
            "prohibited_uses": list(PROHIBITED_USES),
            "named_limitations": limitations,
            "sensitivity_label": prereg.SENSITIVITY_ONLY,
            "holdout": "NOT COLLECTED",
        },
        "identity": {**dict(identity), "report_version": REPORT_ARTIFACT_VERSION, "preregistration_sha256": preregistration_sha256},
        "headline": headline,
        "walk_forward": walk_forward,
        "breakdowns": breakdowns,
        "cross_venue": cross_venue,
        "sweeps": sweeps,
        "ablation": ablation_section,
        "golden_replays": golden,
        "decision_ledgers": ledgers,
        "coverage": {"dataset_index": coverage_index, "venues": coverage},
        "lookahead_audit": audits,
        "integrity": integrity,
    }
    files[REPORT_FILE] = canonical_json_bytes(report)
    files[REPORT_MARKDOWN_FILE] = report_markdown(report).encode()
    return report, files


# --- the human-readable summary and the public index -------------------------------------------------


def _cell(metric: Mapping[str, Any]) -> str:
    if metric["value"] is None:
        return metric["status"]
    return metric["value"]


def report_markdown(report: Mapping[str, Any]) -> str:
    """A readable summary of the report's main tables; the JSON report is authoritative."""

    lines = [
        "# RBT-007 first research backtest (private)",
        "",
        f"Evidence class `{report['evidence']['evidence_class']}`, canonical reference "
        f"`{report['evidence']['canonical_reference']}`, policy `{report['evidence']['policy']}`.",
        "",
        "Prohibited uses: " + "; ".join(report["evidence"]["prohibited_uses"]) + ".",
        "",
        "## Headline (evaluation window), primary metrics with trade counts",
        "",
    ]
    for venue, rungs in report["headline"].items():
        lines += [f"### {venue}", "", "| Metric | " + " | ".join(rungs) + " |", "| --- |" + " --- |" * len(rungs)]
        for name in rm.PRIMARY_METRICS:
            cells = []
            for rung in rungs:
                metric = rungs[rung]["metrics"][name]
                trades = metric.get("closed_trades", metric.get("trades"))
                cells.append(f"{_cell(metric)} (n={trades})")
            lines.append(f"| {name} | " + " | ".join(cells) + " |")
        lines.append("")
    lines += ["## Walk-forward (base), fold returns", ""]
    for venue, rungs in report["walk_forward"].items():
        folds = rungs["base"]["fold_metrics"]
        check = rungs["ruling_4"]
        lines.append(
            f"- {venue}: folds {[fold['fold_number'] for fold in folds]}, calmar per fold "
            f"{[_cell(fold['metrics']['calmar']) for fold in folds]}; preregistered fold dates equal: {check['equal']}, "
            f"consistent with the omitted hours: {check['consistent']}"
        )
    lines += ["", "## Look-ahead audit", ""]
    for venue, audit in report["lookahead_audit"].items():
        lines.append(
            f"- {venue}: {audit['history_links']} history and {audit['run_links']} run links; ruling 3's sample "
            f"{audit['audited']} of {audit['sample_size']} unshared; failures {len(audit['failures'])}, passed {audit['passed']}"
        )
    lines += ["", "## Named limitations (exposed instants, base run)", ""]
    for venue, rows in report["evidence"]["named_limitations"].items():
        lines.append(f"- {venue}: " + ", ".join(f"{row['limitation_id']} {row['exposed_instants']}" for row in rows))
    lines.append("")
    return "\n".join(lines)


def public_index(report: Mapping[str, Any], files: Mapping[str, bytes], *, private_commit: str | None) -> dict[str, Any]:
    """The value-free public record (ruling 1): digests, sizes, counts and statuses only."""

    audits = report["lookahead_audit"]
    integrity = report["integrity"]
    return {
        "index_version": REPORT_ARTIFACT_VERSION + ":PUBLIC_INDEX",
        "evidence_class": EVIDENCE_CLASS,
        "canonical_reference": CANONICAL_REFERENCE,
        "policy": POLICY,
        "prohibited_uses": list(PROHIBITED_USES),
        "named_limitations": sorted({row["limitation_id"] for rows in report["evidence"]["named_limitations"].values() for row in rows}),
        "identity": report["identity"],
        "private_repository_commit": private_commit,
        "files": {name: {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)} for name, data in sorted(files.items())},
        "runs": integrity["runs"],
        "planned_runs": integrity["planned_runs"],
        "memory_check_failures": sum(1 for value in integrity["memory_matches_history"].values() if not value),
        "runs_with_unaccounted_causes": len(integrity["unaccounted"]),
        "lookahead_audit": {
            venue: {
                "history_links": audit["history_links"],
                "run_links": audit["run_links"],
                "sample_size": audit["sample_size"],
                "audited": audit["audited"],
                "failures": len(audit["failures"]),
                "passed": audit["passed"],
            }
            for venue, audit in audits.items()
        },
        "ruling_4_fold_dates_equal": {venue: entry["ruling_4"]["equal"] for venue, entry in report["walk_forward"].items()},
        "holdout": "NOT COLLECTED",
    }
