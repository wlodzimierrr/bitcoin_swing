"""RBT-007A ``DIAGNOSE_STRUCTURAL_INCOMPLETENESS_V1``: why RBT-007's decisions were unevaluable or found no setup.

The owner's choice of 2026-11-26 (EPIC Y): a read-only diagnosis before the
holdout decision. It reads the frozen RBT-003 dataset (private commit
``f36ad14``), RBT-007's private decision ledgers and the frozen code. It
changes no owner, composer, configuration, completion spec or preregistration;
it runs no strategy, sweep or counterfactual with filled-in data; and it reads
no database or network. Its findings are evidence for a later versioned policy
only: under policy V7 section 6 a successor version never claims evidence from
the evaluation window.

For every RBT-007 evaluation-window decision on every venue it:

1. **Replays the frozen composer's own steps** at the decision instant, as
   RBT-006's completeness pass does: the trend, flow, volatility, geometry and
   structure steps, and the positioning step only where the ledger marks
   positioning incomplete (its owner results cost almost all of an instant).
   The composer's own cause attribution (``_component_causes``) of the
   replayed components must equal the ledger's, decision by decision;
   otherwise nothing is published.
2. **Traces each incomplete component's causes** to the upstream observations
   the owners lacked, read from the owners' own results and the frozen
   evidence:
   - flow: the (fund, publication day) rows missing from the flow owner's own
     5- and 20-day windows, each classified from CoinGlass's frozen flow
     history (the day absent, the fund not listed, or listed without a value)
     or as a row not yet available;
   - the liquidation percentile: the previous UTC day's census, its
     unobserved Kraken hours (withheld by ruling 16, a reported incident, or no
     execution) or its too-short history;
   - the volatility buffer and the range percentile: the daily sessions absent
     from the canonical series the owner reads, and their missing hours (left
     missing by ruling 15's re-request);
   - the open-interest growth prior: the prior observation the owner reads, and
     why it is unusable;
   - the structural stop: the market geometry the stop rules refuse.
3. **Attributes each evaluable decision without a setup**, per setup, to the
   setup owner's reason codes, its first code first, from the ledger.

Each traced observation carries its origin and class: ``SOURCE_ABSENT`` (the
source supplied nothing), ``BUILD_RULE`` (collected, but left out by a build
rule or a recorded ruling), ``WARM_UP``, or ``OTHER`` (named). Each root cause
also names the definition that turns the missing observation into an
incomplete component (``DEFINITION``).
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from btc_predictor.features import positioning as positioning_owner
from btc_predictor.research_backtest import entry_composer as ec
from btc_predictor.research_backtest import preregistration as prereg
from btc_predictor.research_backtest.replay_inputs import canonical_json_bytes

DIAGNOSIS_VERSION = "RBT007A_DIAGNOSIS_V1"
TICKET = "RBT-007A"
REPORT_FILE = "rbt007a_diagnosis_v1.json"
REPORT_MARKDOWN_FILE = "rbt007a_diagnosis_v1.md"
INDEX_FILE = "rbt007a_diagnosis_index_v1.json"
INDEX_VERSION = "RBT007A_DIAGNOSIS_INDEX_V1"
EVIDENCE_CLASS = "RESEARCH_BACKTEST_NON_CERTIFYING"
PROHIBITED_USES = (
    "certify Phase 1.5 or any champion",
    "select, tune or recommend a parameter, threshold, weight or rule for this strategy version",
    "claim evidence from the evaluation window for any successor version (policy V7 section 6)",
    "serve as BTC-019, V3/V4/V5 or EPIC X evidence of any kind",
    "authorize collection of the holdout, prospective collection, live shadow or capital deployment",
)
HOLDOUT_STATUS = "NOT COLLECTED"
DATA_WINDOW_FIRST = datetime(2020, 1, 1, tzinfo=UTC)
HOLDOUT_FIRST = datetime(2026, 1, 1, tzinfo=UTC)

# --- the classes and origins of a traced observation ----------------------------------------------

SOURCE_ABSENT = "SOURCE_ABSENT"
BUILD_RULE = "BUILD_RULE"
DEFINITION = "DEFINITION"
WARM_UP = "WARM_UP"
OTHER = "OTHER"
CLASSES = (SOURCE_ABSENT, BUILD_RULE, DEFINITION, WARM_UP, OTHER)

ORIGIN_CLASS = {
    # ETF flows: CoinGlass's frozen flow history (RBT-003, owner Part B ruling 10's projection)
    "FLOW_HISTORY_DAY_ABSENT": SOURCE_ABSENT,
    "FUND_NOT_LISTED": SOURCE_ABSENT,
    "FUND_LISTED_WITHOUT_VALUE": SOURCE_ABSENT,
    "LISTED_WITH_VALUE_NOT_IN_DATASET": BUILD_RULE,
    "ROW_NOT_YET_AVAILABLE": BUILD_RULE,
    # Kraken liquidation hours (HISTORICAL_LIQUIDATION_HOUR_COMPLETENESS_V1)
    "WITHHELD_RULING_16": BUILD_RULE,
    "KRAKEN_REPORTED_INCIDENT": SOURCE_ABSENT,
    "NO_EXECUTION_IN_HOUR": SOURCE_ABSENT,
    "HOUR_NOT_IN_EVIDENCE": SOURCE_ABSENT,
    "DAY_NOT_IN_EVIDENCE": SOURCE_ABSENT,
    "INSUFFICIENT_COMPLETE_DAYS_WARM_UP": WARM_UP,
    "INSUFFICIENT_COMPLETE_DAYS": OTHER,
    # venue price hours (owner Part B ruling 15)
    "STILL_MISSING_AFTER_REREQUEST": SOURCE_ABSENT,
    "HOUR_MISSING_NOT_REREQUESTED": SOURCE_ABSENT,
    "SESSION_ABSENT_NO_MISSING_HOUR": OTHER,
    # open interest
    "SOURCE_ZERO_TOTAL": OTHER,
    "NO_PRIOR_OBSERVATION": WARM_UP,
    # the structural stop
    "MARKET_GEOMETRY": OTHER,
}

# The definitions that turn a missing observation into an incomplete component.
RULES = {
    "ETF_WINDOW_NEEDS_EVERY_FUND_EVERY_DAY": (
        "flow owner etf_flow_window: a 5- or 20-publication-day window is complete only with every launched fund's row "
        "on every day in it; a missing row is never filled, so one missing fund-day leaves every window holding it incomplete"
    ),
    "LIQUIDATION_DAY_NEEDS_24_OBSERVED_HOURS": (
        "HISTORICAL_LIQUIDATION_HOUR_COMPLETENESS_V1: a UTC day's census is complete only when all 24 hours are observed; "
        "the composer reads the previous day's percentile and never substitutes an older day"
    ),
    "LIQUIDATION_PERCENTILE_NEEDS_MIN_COMPLETE_DAYS": (
        "PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_V1: a complete day needs the minimum number of complete days in its "
        "trailing window"
    ),
    "DAILY_SESSION_NEEDS_EVERY_HOUR": (
        "BTC-040 canonical bars: a daily bar exists only when every hour of it is available; a true range needs the "
        "preceding session, so an absent session leaves the ATR (and the stop's volatility buffer) undefined for the "
        "ATR window after it, and the range percentile undefined on the session after it"
    ),
    "OI_GROWTH_NEEDS_NONZERO_PRIOR": (
        "positioning owner open_interest_growth_health: growth needs a nonzero aggregate open interest at the latest "
        "observation at least the growth window before"
    ),
    "STRUCTURAL_STOP_GEOMETRY": (
        "BTC-140/141/142 stop owners: no structural invalidation candidate within the rules (side, confluence, maximum "
        "distance), so no archetype has a stop; market geometry, not missing data"
    ),
}

# Root cause codes, by component: each is traced to upstream observations or a named rule.
ROOT_RULE = {
    ("flow", "ETF_FLOW_INPUT_MISSING"): "ETF_WINDOW_NEEDS_EVERY_FUND_EVERY_DAY",
    ("volatility", ec.CAUSE_LIQUIDATION_PERCENTILE_MISSING): "LIQUIDATION_DAY_NEEDS_24_OBSERVED_HOURS",
    ("volatility", "RANGE_PERCENTILE_INPUT_MISSING"): "DAILY_SESSION_NEEDS_EVERY_HOUR",
    ("structure", "VOLATILITY_BUFFER_INPUT_MISSING"): "DAILY_SESSION_NEEDS_EVERY_HOUR",
    ("positioning", "OI_GROWTH_PRIOR_INPUT_MISSING"): "OI_GROWTH_NEEDS_NONZERO_PRIOR",
    ("decision_instant", ec.CAUSE_DECISION_PRICE_BAR_MISSING): "DAILY_SESSION_NEEDS_EVERY_HOUR",
}
GEOMETRY_CODES = frozenset(
    {
        "STRUCTURAL_INVALIDATION_NO_CANDIDATE",
        "STRUCTURAL_INVALIDATION_BEYOND_MAX_DISTANCE",
        "STRUCTURAL_INVALIDATION_BELOW_MIN_CONFLUENCE",
        "STRUCTURAL_INVALIDATION_WRONG_SIDE",
    }
)
# Codes an owner derives from a root in the same component (each explained by that root's trace).
DERIVED = {
    "flow": {
        "ETF_FLOW_ACCEL_INPUT_MISSING": "the acceleration needs both current windows",
        "FLOW_Z_ETF_NORM_5D_INPUT_MISSING": "the current 5-day value is missing",
        "FLOW_Z_ETF_NORM_20D_INPUT_MISSING": "the current 20-day value is missing",
        "FLOW_Z_FLOW_ACCEL_INPUT_MISSING": "the current acceleration is missing",
        "FLOW_SCORE_CORE_INPUT_MISSING": "a core flow z-score is missing",
        "FLOW_SCORE_P1_INPUT_MISSING": (
            "CVD and spot dominance are never sourced (policy V7 section 5, the ETF_CORE fallback); listed beside a core "
            "gap, never a cause on its own"
        ),
    },
    "volatility": {
        "ORDERLINESS_INPUT_MISSING": "an orderliness input is missing",
        "VOLATILITY_SCORE_INPUT_MISSING": "the orderliness score is missing",
    },
    "structure": {
        "VOLATILITY_BUFFER_INVALIDATION_INCOMPLETE": "the buffer has no invalidation",
        "INITIAL_STOP_INVALIDATION_INCOMPLETE": "the stop has no invalidation",
        "INITIAL_STOP_BUFFER_INCOMPLETE": "the stop has no buffer",
        "INITIAL_STOP_INPUT_MISSING": "the stop's buffer input is missing",
    },
    "positioning": {
        "POSITIONING_SCORE_INPUT_MISSING": "a positioning owner result is missing",
    },
}

LEDGER_OUTCOME_UNEVALUABLE = ec.OUTCOME_STRUCTURALLY_UNEVALUABLE
REASON_NO_STOP = ec.REASON_NO_VALID_STRUCTURAL_STOP
REASON_NO_SETUP = "NO_SETUP_DETECTED"
REPLAYED_COMPONENTS = ("trend", "flow", "volatility", "structure")


class DiagnosisRefused(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


# --- the frozen evidence the traces read ------------------------------------------------------------


@dataclass(frozen=True)
class SourceEvidence:
    """What the source supplied, read from RBT-003's frozen evidence.

    - ``etf_days``: each day of CoinGlass's frozen flow history, mapping each
      listed fund to whether it carries a value;
    - ``liquidation_hours``: the origin of every unobserved Kraken hour the
      evidence records (observed hours are absent);
    - ``liquidation_evidence_days``: the first and last day of the hour
      evidence, and ``liquidation_history`` each day's count of complete days
      in its trailing window (``None`` for an incomplete day);
    - ``still_missing_hours``: per venue, the hours ruling 15's re-request left
      missing.
    """

    etf_days: Mapping[date, Mapping[str, bool]]
    liquidation_hours: Mapping[datetime, str]
    liquidation_evidence_days: tuple[date, date] | None
    liquidation_history: Mapping[date, int | None]
    liquidation_window_days: int
    liquidation_minimum: int
    still_missing_hours: Mapping[str, frozenset[datetime]] = field(default_factory=dict)

    def etf_origin(self, fund: str, day: date) -> str:
        listed = self.etf_days.get(day)
        if listed is None:
            return "FLOW_HISTORY_DAY_ABSENT"
        if fund not in listed:
            return "FUND_NOT_LISTED"
        return "LISTED_WITH_VALUE_NOT_IN_DATASET" if listed[fund] else "FUND_LISTED_WITHOUT_VALUE"


def _observation(origin: str, **fields: Any) -> dict[str, Any]:
    return {**fields, "origin": origin, "class": ORIGIN_CLASS[origin]}


# --- the replay ------------------------------------------------------------------------------------


class _DiagnosisRun(ec._DecisionRun):
    """The RBT-004 decision run's component steps, as RBT-006's completeness pass runs them, without positioning."""

    def replay(self) -> tuple[dict[str, tuple[str, ...]], dict[str, Any] | None]:
        hourly = self.c._visible_hourly(self.t)
        if not hourly or hourly[-1].ingested_at != self.t:
            return {"decision_instant": (ec.CAUSE_DECISION_PRICE_BAR_MISSING,)}, None
        self.price = hourly[-1].close
        canonical = ec.replay_market_bars_at(hourly, decision_at=self.t, window=self.c._window)
        self.daily = tuple(bar for bar in canonical if bar.timeframe == "1d")
        self.weekly = tuple(bar for bar in canonical if bar.timeframe == "1w")
        self.monthly = tuple(bar for bar in canonical if bar.timeframe == "1mo")
        self.hourly = hourly
        trend = self._trend()
        flow = self._flow()
        volatility = self._volatility()
        geometry = self._geometry()
        structure = self._structure(geometry)
        components = dict(zip(REPLAYED_COMPONENTS, (trend, flow, volatility, structure)))
        return {item.component: tuple(item.causes) for item in self._component_causes(components)}, geometry

    def replay_positioning(self) -> tuple[str, ...] | None:
        positioning = self._positioning()
        found = {item.component: tuple(item.causes) for item in self._component_causes({"positioning": positioning})}
        return found.get("positioning")


# --- the traces ------------------------------------------------------------------------------------


def _trace_flow(run: _DiagnosisRun, evidence: SourceEvidence) -> list[dict[str, Any]]:
    """The rows missing from the flow owner's own current windows, each with its origin."""

    shared = run.c._inputs.dataset.shared_snapshot
    visible = {(flow.fund, flow.observation_date) for flow in shared.etf_flows if flow.available_at <= run.t}
    stored = {(flow.fund, flow.observation_date) for flow in shared.etf_flows}
    observations = []
    for label, window in (("etf_flow_5d", "5D"), ("etf_flow_20d", "20D")):
        result = run.results.get(label)
        if result is None or result.complete:
            continue
        for fund in result.funds:
            for day in result.included_observation_dates:
                if (fund, day) in visible:
                    continue
                origin = "ROW_NOT_YET_AVAILABLE" if (fund, day) in stored else evidence.etf_origin(fund, day)
                observations.append(_observation(origin, window=window, fund=fund, date=day.isoformat()))
    return observations


def _trace_liquidation(run: _DiagnosisRun, evidence: SourceEvidence) -> list[dict[str, Any]]:
    """The previous UTC day's census: its unobserved hours, or its too-short history."""

    day = (run.t - timedelta(days=1)).date()
    item = run.c._liquidations.get(day)
    bounds = evidence.liquidation_evidence_days
    if item is None or bounds is None or not bounds[0] <= day <= bounds[1]:
        return [_observation("DAY_NOT_IN_EVIDENCE", day=day.isoformat())]
    observations = []
    if "LIQUIDATION_FEED_UNAVAILABLE" in item.reason_codes:
        start = datetime(day.year, day.month, day.day, tzinfo=UTC)
        for offset in range(24):
            hour = start + timedelta(hours=offset)
            origin = evidence.liquidation_hours.get(hour)
            if origin is not None:
                observations.append(_observation(origin, day=day.isoformat(), hour=hour.isoformat()))
    elif "LIQUIDATION_PERCENTILE_INSUFFICIENT_HISTORY" in item.reason_codes:
        window_start = day - timedelta(days=evidence.liquidation_window_days)
        origin = "INSUFFICIENT_COMPLETE_DAYS_WARM_UP" if window_start < bounds[0] else "INSUFFICIENT_COMPLETE_DAYS"
        observations.append(
            _observation(
                origin,
                day=day.isoformat(),
                complete_days=evidence.liquidation_history.get(day),
                minimum=evidence.liquidation_minimum,
            )
        )
    return observations


def _absent_sessions(daily: Sequence[Any], bars: int) -> list[date]:
    """UTC days absent between consecutive bars among the last ``bars`` daily bars the owner reads."""

    tail = list(daily)[-bars:]
    absent = []
    for previous, current in zip(tail, tail[1:]):
        day = previous.timestamp.date() + timedelta(days=1)
        while day < current.timestamp.date():
            absent.append(day)
            day += timedelta(days=1)
    return absent


def _trace_sessions(run: _DiagnosisRun, evidence: SourceEvidence, bars: int) -> list[dict[str, Any]]:
    """The absent daily sessions in the bars the owner reads, and each one's missing hours."""

    venue = run.c.venue
    present = {bar.timestamp for bar in run.c._hourly}
    still_missing = evidence.still_missing_hours.get(venue, frozenset())
    observations = []
    for session in _absent_sessions(run.daily, bars):
        start = datetime(session.year, session.month, session.day, tzinfo=UTC)
        hours = [start + timedelta(hours=offset) for offset in range(24)]
        missing = [hour for hour in hours if hour not in present]
        if not missing:
            observations.append(_observation("SESSION_ABSENT_NO_MISSING_HOUR", session=session.isoformat()))
        for hour in missing:
            origin = "STILL_MISSING_AFTER_REREQUEST" if hour in still_missing else "HOUR_MISSING_NOT_REREQUESTED"
            observations.append(_observation(origin, session=session.isoformat(), hour=hour.isoformat()))
    return observations


def _trace_price_bar(run: _DiagnosisRun, evidence: SourceEvidence) -> list[dict[str, Any]]:
    hour = run.t - timedelta(hours=1)
    still_missing = evidence.still_missing_hours.get(run.c.venue, frozenset())
    origin = "STILL_MISSING_AFTER_REREQUEST" if hour in still_missing else "HOUR_MISSING_NOT_REREQUESTED"
    return [_observation(origin, session=hour.date().isoformat(), hour=hour.isoformat())]


def _trace_open_interest_prior(run: _DiagnosisRun) -> list[dict[str, Any]]:
    """The prior observation the growth owner reads, and why it is unusable."""

    result = run.results.get("open_interest_growth_health")
    if result is None or result.complete or "OI_GROWTH_PRIOR_INPUT_MISSING" not in result.reason_codes:
        return []
    rows = run._owner_visible(run.c._inputs.dataset.shared_snapshot.open_interest, result.open_interest_unit)
    aggregate = positioning_owner._aggregate_open_interest_by_time(rows)
    cutoff = result.observation_time - timedelta(days=result.growth_window_days)
    prior_times = [time for time in aggregate if time <= cutoff]
    if not prior_times:
        return [_observation("NO_PRIOR_OBSERVATION", observation_time=result.observation_time.isoformat())]
    prior = max(prior_times)
    if aggregate[prior] != 0:
        return []
    count = sum(1 for row in rows if row.as_record()["observation_time"] == prior)
    return [
        _observation(
            "SOURCE_ZERO_TOTAL",
            observation_time=result.observation_time.isoformat(),
            prior_time=prior.isoformat(),
            rows_at_prior=count,
        )
    ]


def _trace_root(component: str, code: str, run: _DiagnosisRun, evidence: SourceEvidence, atr_bars: int) -> list[dict[str, Any]]:
    if component == "flow":
        return _trace_flow(run, evidence)
    if component == "volatility" and code == ec.CAUSE_LIQUIDATION_PERCENTILE_MISSING:
        return _trace_liquidation(run, evidence)
    if component == "volatility":
        return _trace_sessions(run, evidence, 2)  # the range percentile: the last bar's true range
    if component == "structure":
        return _trace_sessions(run, evidence, atr_bars)  # the buffer's ATR window
    if component == "positioning":
        return _trace_open_interest_prior(run)
    return _trace_price_bar(run, evidence)


def _trace_component(
    component: str, codes: Sequence[str], run: _DiagnosisRun, evidence: SourceEvidence, atr_bars: int
) -> dict[str, Any]:
    roots, derived, untraced = [], [], []
    geometry = sorted(code for code in codes if component == "structure" and code in GEOMETRY_CODES)
    for code in codes:
        rule = ROOT_RULE.get((component, code))
        if rule is not None:
            observations = _trace_root(component, code, run, evidence, atr_bars)
            if observations:
                roots.append({"code": code, "rule": rule, "observations": observations})
            else:
                untraced.append({"code": code, "reason": "its root trace found no missing or unusable observation"})
        elif code in geometry:
            continue
        elif code in DERIVED.get(component, {}):
            derived.append(code)
        else:
            untraced.append({"code": code, "reason": "no tracer for this cause"})
    if geometry:
        roots.append(
            {
                "code": "+".join(geometry),
                "rule": "STRUCTURAL_STOP_GEOMETRY",
                "observations": [_observation("MARKET_GEOMETRY", codes=geometry)],
            }
        )
    if not roots and not untraced:
        untraced.append({"code": None, "reason": "only derived causes, no root"})
    return {"codes": list(codes), "roots": roots, "derived": sorted(derived), "untraced": untraced}


# --- one venue ------------------------------------------------------------------------------------


def _ledger_incomplete(row: Mapping[str, Any]) -> dict[str, tuple[str, ...]]:
    return {item["component"]: tuple(cause["code"] for cause in item["causes"]) for item in row["unevaluable"]}


def _expected_replay(row: Mapping[str, Any]) -> dict[str, tuple[str, ...]] | None:
    """The replayed components' causes the ledger implies, or ``None`` for a no-valid-stop NO_TRADE (checked apart)."""

    if row["outcome"] == LEDGER_OUTCOME_UNEVALUABLE:
        return {name: codes for name, codes in _ledger_incomplete(row).items() if name != "positioning"}
    if list(row["reasons"]) == [REASON_NO_STOP]:
        return None
    return {}


def _setups(row: Mapping[str, Any]) -> dict[str, Any]:
    found = {}
    for label, result in sorted(row["owner_reason_codes"].items()):
        if label.startswith("setup:"):
            codes = list(result.get("reason_codes") or [])
            found[label.split(":", 1)[1]] = {"complete": result.get("complete"), "codes": codes, "first": codes[0] if codes else None}
    return found


def diagnose_venue(
    inputs: ec.EntryComposerInputs,
    ledger_rows: Sequence[Mapping[str, Any]],
    instants: Sequence[datetime],
    evidence: SourceEvidence,
    *,
    strategy_config: Any,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """One venue's diagnosis: each decision replayed, checked against its ledger row and traced."""

    for instant in instants:
        if not DATA_WINDOW_FIRST <= instant < HOLDOUT_FIRST:
            raise DiagnosisRefused("WINDOW_REFUSED", f"{instant.isoformat()} is outside the data window (holdout NOT COLLECTED)")
    rows = {row["decision_at"]: row for row in ledger_rows}
    if sorted(rows) != [instant.isoformat() for instant in instants] or len(rows) != len(ledger_rows):
        raise DiagnosisRefused("LEDGER_REFUSED", "the ledger's decisions are not exactly the evaluation window's instants")
    composer = ec.EntryComposer(inputs, strategy_config=strategy_config)
    atr_bars = int(strategy_config.stop_buffers.atr_period) + 1
    decisions = []
    for count, instant in enumerate(instants, 1):
        row = rows[instant.isoformat()]
        run = _DiagnosisRun(composer, instant, position_open=False)
        replayed, geometry = run.replay()
        disagreements = []
        expected = _expected_replay(row)
        if expected is None:
            if set(replayed) != {"structure"} or geometry is None or geometry["no_stop_cause"] != "GEOMETRY":
                disagreements.append("the ledger's no-valid-stop NO_TRADE is not a geometry-only structure gap in the replay")
        elif replayed != expected:
            disagreements.append(f"replayed {sorted(replayed.items())} != ledger {sorted(expected.items())}")
        incomplete = dict(replayed)
        ledger = _ledger_incomplete(row)
        if "positioning" in ledger:
            positioning_run = _DiagnosisRun(composer, instant, position_open=False)
            causes = positioning_run.replay_positioning()
            if causes != ledger["positioning"]:
                disagreements.append(f"replayed positioning {causes} != ledger {ledger['positioning']}")
            incomplete["positioning"] = ledger["positioning"]
        else:
            positioning_run = None
        traced = {}
        for component, codes in sorted(incomplete.items()):
            source_run = positioning_run if component == "positioning" and positioning_run is not None else run
            traced[component] = _trace_component(component, codes, source_run, evidence, atr_bars)
        decision = {
            "decision_at": instant.isoformat(),
            "outcome": row["outcome"],
            "reasons": list(row["reasons"]),
            "incomplete": traced,
            "disagreements": disagreements,
        }
        if row["outcome"] == ec.OUTCOME_NO_TRADE and list(row["reasons"]) == [REASON_NO_SETUP]:
            decision["setups"] = _setups(row)
        decisions.append(decision)
        if progress is not None and count % 50 == 0:
            progress(f"{composer.venue}: {count}/{len(instants)}")
    return {"venue": composer.venue, "decisions": decisions, "summary": venue_summary(decisions)}


# --- summaries ------------------------------------------------------------------------------------


def _counter(counter: Counter) -> dict[str, int]:
    return {str(key): count for key, count in sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))}


def venue_summary(decisions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    unevaluable = [d for d in decisions if d["outcome"] == LEDGER_OUTCOME_UNEVALUABLE]
    classes: Counter = Counter()
    rules: Counter = Counter()
    etf: dict[tuple[str, str], dict[str, Any]] = {}
    liquidation_days: dict[str, dict[str, Any]] = {}
    liquidation_hours: dict[str, str] = {}
    sessions: dict[str, dict[str, Any]] = {}
    open_interest: dict[str, dict[str, Any]] = {}
    for decision in decisions:
        seen_classes, seen_rules, seen_pairs, seen_days, seen_sessions = set(), set(), set(), set(), set()
        for component in decision["incomplete"].values():
            for root in component["roots"]:
                seen_rules.add(root["rule"])
                for item in root["observations"]:
                    seen_classes.add(item["class"])
                    if "fund" in item:
                        key = (item["fund"], item["date"])
                        etf.setdefault(key, {"origin": item["origin"], "decisions": 0})
                        seen_pairs.add(key)
                    elif "session" in item:
                        entry = sessions.setdefault(item["session"], {"hours": {}, "decisions": 0})
                        if "hour" in item:
                            entry["hours"][item["hour"]] = item["origin"]
                        seen_sessions.add(item["session"])
                    elif "day" in item:
                        entry = liquidation_days.setdefault(item["day"], {"origin": item["origin"], "decisions": 0})
                        if "hour" in item:
                            liquidation_hours[item["hour"]] = item["origin"]
                            entry["origin"] = "UNOBSERVED_HOURS"
                        seen_days.add(item["day"])
                    elif "prior_time" in item or item["origin"] == "NO_PRIOR_OBSERVATION":
                        open_interest[decision["decision_at"]] = {k: v for k, v in item.items() if k != "class"}
        classes.update(seen_classes)
        rules.update(seen_rules)
        for key in seen_pairs:
            etf[key]["decisions"] += 1
        for day in seen_days:
            liquidation_days[day]["decisions"] += 1
        for session in seen_sessions:
            sessions[session]["decisions"] += 1
    setups: dict[str, dict[str, Counter]] = {}
    for decision in decisions:
        for setup, found in decision.get("setups", {}).items():
            entry = setups.setdefault(setup, {"first": Counter(), "codes": Counter()})
            entry["first"][found["first"]] += 1
            entry["codes"].update(found["codes"])
    etf_by_fund: Counter = Counter(fund for fund, _ in etf)
    etf_by_month: Counter = Counter(day[:7] for _, day in etf)
    worst = sorted(etf.items(), key=lambda item: (-item[1]["decisions"], item[0]))[:10]
    return {
        "decisions": len(decisions),
        "outcomes": _counter(Counter(d["outcome"] for d in decisions)),
        "no_trade_reasons": _counter(Counter("+".join(d["reasons"]) for d in decisions if d["outcome"] == ec.OUTCOME_NO_TRADE)),
        "incomplete_components": _counter(Counter(c for d in unevaluable for c in d["incomplete"])),
        "component_combinations": _counter(Counter("+".join(sorted(d["incomplete"])) for d in unevaluable)),
        "decisions_by_class": _counter(classes),
        "decisions_by_rule": _counter(rules),
        "etf": {
            "missing_fund_days": len(etf),
            "missing_fund_days_by_origin": _counter(Counter(entry["origin"] for entry in etf.values())),
            "missing_fund_days_by_fund": _counter(etf_by_fund),
            "missing_fund_days_by_month": dict(sorted(etf_by_month.items())),
            "first_missing_day": min((day for _, day in etf), default=None),
            "last_missing_day": max((day for _, day in etf), default=None),
            "most_decisions": [{"fund": fund, "date": day, **entry} for (fund, day), entry in worst],
        },
        "liquidation": {
            "days": len(liquidation_days),
            "days_by_origin": _counter(Counter(entry["origin"] for entry in liquidation_days.values())),
            "unobserved_hours": len(liquidation_hours),
            "unobserved_hours_by_origin": _counter(Counter(liquidation_hours.values())),
            "day_list": [{"day": day, **entry} for day, entry in sorted(liquidation_days.items())],
        },
        "price_sessions": [
            {"session": session, "decisions": entry["decisions"], "hours": dict(sorted(entry["hours"].items()))}
            for session, entry in sorted(sessions.items())
        ],
        "open_interest_prior": [{"decision_at": key, **value} for key, value in sorted(open_interest.items())],
        "setups": {
            setup: {"first_code": _counter(entry["first"]), "codes": _counter(entry["codes"])} for setup, entry in sorted(setups.items())
        },
        "untraced": [
            {"decision_at": d["decision_at"], "component": name, **item}
            for d in decisions
            for name, component in sorted(d["incomplete"].items())
            for item in component["untraced"]
        ],
        "disagreements": [{"decision_at": d["decision_at"], "disagreements": d["disagreements"]} for d in decisions if d["disagreements"]],
    }


# --- the report, its markdown and the public index ---------------------------------------------------


def build_report(identity: Mapping[str, Any], venues: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "diagnosis_version": DIAGNOSIS_VERSION,
        "ticket": TICKET,
        "evidence_class": EVIDENCE_CLASS,
        "prohibited_uses": list(PROHIBITED_USES),
        "holdout": HOLDOUT_STATUS,
        "identity": dict(identity),
        "classes": list(CLASSES),
        "origins": dict(sorted(ORIGIN_CLASS.items())),
        "rules": dict(sorted(RULES.items())),
        "derived": {component: dict(sorted(codes.items())) for component, codes in sorted(DERIVED.items())},
        "positioning_replayed": "only on the decisions the ledger marks positioning incomplete",
        "venues": {venue: dict(venues[venue]) for venue in sorted(venues)},
    }


def publication_refusals(report: Mapping[str, Any]) -> list[str]:
    """Every replay must agree with its ledger row; untraced causes are listed, not refused (the ticket)."""

    return [
        f"{venue}: {len(entry['summary']['disagreements'])} decision(s) disagree with the ledger"
        for venue, entry in report["venues"].items()
        if entry["summary"]["disagreements"]
    ]


def _table(header: Sequence[str], rows: Sequence[Sequence[Any]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return lines


def report_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        f"# RBT-007A diagnosis ({report['diagnosis_version']})",
        "",
        f"**Evidence class:** {report['evidence_class']}. **Holdout:** {report['holdout']}.",
        "",
        "**Prohibited uses:**",
        *[f"- {use}" for use in report["prohibited_uses"]],
        "",
        "Every decision was replayed through the frozen composer and agreed with its RBT-007 ledger row; "
        "positioning was replayed only where the ledger marks it incomplete.",
        "",
        "## Definitions",
        *[f"- **{rule}**: {text}" for rule, text in report["rules"].items()],
    ]
    for venue, entry in report["venues"].items():
        summary = entry["summary"]
        lines += ["", f"## {venue}", "", f"{summary['decisions']} decisions."]
        lines += ["", *_table(("Outcome", "Decisions"), list(summary["outcomes"].items()))]
        lines += ["", *_table(("No-trade reason", "Decisions"), list(summary["no_trade_reasons"].items()))]
        lines += ["", *_table(("Incomplete component", "Unevaluable decisions"), list(summary["incomplete_components"].items()))]
        lines += ["", *_table(("Incomplete components together", "Decisions"), list(summary["component_combinations"].items()))]
        lines += ["", *_table(("Class of a traced observation", "Decisions"), list(summary["decisions_by_class"].items()))]
        lines += ["", *_table(("Definition", "Decisions"), list(summary["decisions_by_rule"].items()))]
        etf = summary["etf"]
        lines += [
            "",
            f"**ETF flows.** {etf['missing_fund_days']} distinct missing fund-days, {etf['first_missing_day']} to "
            f"{etf['last_missing_day']}.",
            "",
            *_table(("Origin", "Fund-days"), list(etf["missing_fund_days_by_origin"].items())),
            "",
            *_table(("Fund", "Fund-days"), list(etf["missing_fund_days_by_fund"].items())),
            "",
            *_table(("Month", "Fund-days"), list(etf["missing_fund_days_by_month"].items())),
            "",
            *_table(("Fund", "Day", "Origin", "Decisions it leaves incomplete"), [
                (item["fund"], item["date"], item["origin"], item["decisions"]) for item in etf["most_decisions"]
            ]),
        ]
        liquidation = summary["liquidation"]
        lines += [
            "",
            f"**Liquidation percentile.** {liquidation['days']} distinct previous days; {liquidation['unobserved_hours']} "
            "unobserved hours.",
            "",
            *_table(("Day origin", "Days"), list(liquidation["days_by_origin"].items())),
            "",
            *_table(("Hour origin", "Hours"), list(liquidation["unobserved_hours_by_origin"].items())),
        ]
        if summary["price_sessions"]:
            lines += ["", "**Absent price sessions.**", "", *_table(("Session", "Missing hours", "Decisions"), [
                (item["session"], len(item["hours"]), item["decisions"]) for item in summary["price_sessions"]
            ])]
        if summary["open_interest_prior"]:
            lines += ["", "**Open-interest prior.**", "", *_table(("Decision", "Prior", "Origin"), [
                (item["decision_at"], item.get("prior_time"), item["origin"]) for item in summary["open_interest_prior"]
            ])]
        for setup, found in summary["setups"].items():
            lines += ["", f"**Setup {setup}** on decisions without a setup (first code).", "",
                      *_table(("First code", "Decisions"), list(found["first_code"].items()))]
        lines += ["", f"Untraced causes: {len(summary['untraced'])}. Disagreements with the ledger: {len(summary['disagreements'])}."]
    return "\n".join(lines) + "\n"


def public_index(report: Mapping[str, Any], files: Mapping[str, bytes]) -> dict[str, Any]:
    """The value-free index: digests, sizes, process counts, statuses and commits only (ruling 1)."""

    venues = {}
    for venue, entry in report["venues"].items():
        summary = entry["summary"]
        venues[venue] = {
            "decisions_examined": summary["decisions"],
            "untraced": len(summary["untraced"]),
            "ledger_disagreements": len(summary["disagreements"]),
        }
    return {
        "index_version": INDEX_VERSION,
        "ticket": TICKET,
        "evidence_class": EVIDENCE_CLASS,
        "prohibited_uses": list(PROHIBITED_USES),
        "holdout": HOLDOUT_STATUS,
        "identity": dict(report["identity"]),
        "files": {name: {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)} for name, data in sorted(files.items())},
        "venues": venues,
        "private_repository_commit": None,
    }


def report_files(report: Mapping[str, Any]) -> dict[str, bytes]:
    return {REPORT_FILE: canonical_json_bytes(report), REPORT_MARKDOWN_FILE: report_markdown(report).encode("utf-8")}


# --- loading the frozen evidence and RBT-007's ledgers ---------------------------------------------------


def rbt007_ledgers(store_root: Path, repository: Path, venues: Sequence[str]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """RBT-007's private ledgers, each byte-identical to the file its committed public index binds."""

    from btc_predictor.research_backtest import runner_report as rr

    index_bytes = (repository / prereg.ARTIFACT_DIRECTORY / rr.INDEX_FILE).read_bytes()
    index = json.loads(index_bytes)
    ledgers = {}
    for venue in venues:
        name = rr.ledger_file(venue)
        bound = index["files"].get(name)
        path = store_root / prereg.ARTIFACT_DIRECTORY.name / name
        data = path.read_bytes() if path.is_file() and not path.is_symlink() else None
        if bound is None or data is None or hashlib.sha256(data).hexdigest() != bound["sha256"] or len(data) != bound["size"]:
            raise DiagnosisRefused("LEDGER_REFUSED", f"{name} is not the file RBT-007's public index binds")
        record = json.loads(data)
        if record.get("venue") != venue:
            raise DiagnosisRefused("LEDGER_REFUSED", f"{name} is not {venue}'s ledger")
        ledgers[venue] = record["entry_rows"]
    return ledgers, {"index_sha256": hashlib.sha256(index_bytes).hexdigest(), "identity": index["identity"]}


def unobserved_hour_origins(records: Sequence[Mapping[str, Any]]) -> dict[datetime, str]:
    """Each unobserved hour of a verified Kraken hour-evidence file, by why: a reported incident, or no execution.

    ``SOURCE_UNAVAILABLE`` marks an hour overlapping a reported incident or one
    with no execution of any type (``backfill_kraken``); an observed hour is
    left out.
    """

    from btc_predictor.research.prospective_integration_corpus import LIQUIDATION_OBSERVED_FEED_STATUSES

    origins = {}
    for record in records:
        if record["feed_status"] in LIQUIDATION_OBSERVED_FEED_STATUSES:
            continue
        start = datetime.fromisoformat(record["hour_start"])
        if record["incident"]:
            origins[start] = "KRAKEN_REPORTED_INCIDENT"
        elif record["execution_count"] == 0:
            origins[start] = "NO_EXECUTION_IN_HOUR"
        else:
            raise DiagnosisRefused("EVIDENCE_REFUSED", f"hour {record['hour_start']} is unobserved with executions and no incident")
    return origins


def load_source_evidence(store: Any, venues: Sequence[str], *, units: Callable[[str], Sequence[str]] | None = None) -> SourceEvidence:
    """The frozen evidence the traces classify against, each file proven as the build proves it."""

    from btc_predictor.research.prospective_integration_corpus import (
        LIQUIDATION_OBSERVED_FEED_STATUSES,
        LIQUIDATION_PERCENTILE_MIN_OBSERVATIONS,
        LIQUIDATION_PERCENTILE_WINDOW_DAYS,
    )
    from btc_predictor.research_backtest import backfill_coinglass as coinglass
    from btc_predictor.research_backtest import backfill_kraken as kraken
    from btc_predictor.research_backtest import backfill_run as run
    from btc_predictor.research_backtest import dataset_build as build

    found = store.completed("coinglass-etf", "all")
    if found is None:
        raise DiagnosisRefused("EVIDENCE_REFUSED", "the CoinGlass unit does not verify")
    flow = run.coinglass_proven(found[1])[0]
    etf_days: dict[date, dict[str, bool]] = {}
    for entry in coinglass._envelope(flow, "the flow history", coinglass.FLOW_DATE_KEYS):
        day = coinglass._trading_day(entry["timestamp"], "a flow day", flow.first_day, flow.last_day)
        etf_days[day] = {item["etf_ticker"]: item.get("flow_usd") is not None for item in entry["etf_flows"]}

    evidence = build.load_build_evidence(store, units=units)
    withheld = evidence.withheld_hours
    hours: dict[datetime, str] = {}
    for hour in evidence.liquidation_hours:
        if hour.hour_start in withheld:
            hours[hour.hour_start] = "WITHHELD_RULING_16"
    unavailable_days = sorted(
        {hour.hour_start.date() for hour in evidence.liquidation_hours if hour.feed_status not in LIQUIDATION_OBSERVED_FEED_STATUSES}
    )
    for day in unavailable_days:
        unit = store.completed("kraken-liquidations", day.isoformat())
        if unit is None:
            raise DiagnosisRefused("EVIDENCE_REFUSED", f"kraken-liquidations {day} does not verify")
        files = unit[1]
        summary = build._summary(files, f"kraken-liquidations {day}")
        size = build._declared_size(summary.get("evidence_size"))
        data = None if size is None else build._gunzip(files[build.HOUR_EVIDENCE_FILE], size)
        if data is None:
            raise DiagnosisRefused("EVIDENCE_REFUSED", f"kraken-liquidations {day}: its hour evidence does not verify")
        kraken.parse_liquidation_hour_evidence(data, expected_sha256=summary.get("evidence_sha256"))  # proves the bytes
        for start, origin in unobserved_hour_origins(json.loads(data)["hours"]).items():
            hours.setdefault(start, origin)  # a withheld hour keeps its ruling
    all_days = sorted({hour.hour_start.date() for hour in evidence.liquidation_hours})
    stored = build.load_dataset(store)
    datasets = build.build_replay_datasets(build.frozen_rows(stored), evidence)
    if datasets.manifests() != stored.manifests:
        raise DiagnosisRefused("EVIDENCE_REFUSED", "the frozen inputs do not rebuild the stored manifests")
    history = {day.observation_date: day.history_observation_count for day in datasets.extended.liquidation_days}
    still_missing = {}
    for venue in venues:
        listed = evidence.record["still_missing_hours"].get(venue.lower()) or []
        still_missing[venue] = frozenset(datetime.fromisoformat(hour.replace("Z", "+00:00")) for hour in listed)
    return SourceEvidence(
        etf_days=etf_days,
        liquidation_hours=hours,
        liquidation_evidence_days=(all_days[0], all_days[-1]) if all_days else None,
        liquidation_history=history,
        liquidation_window_days=int(LIQUIDATION_PERCENTILE_WINDOW_DAYS),
        liquidation_minimum=int(LIQUIDATION_PERCENTILE_MIN_OBSERVATIONS),
        still_missing_hours=still_missing,
    )


# --- the command ---------------------------------------------------------------------------------------


def require_code(repository: Path, frozen_commit: str, run_commit: str) -> dict[str, Any]:
    """The loaded owners and composers are the frozen commit's, and the runner's helpers RBT-007's run commit's."""

    import sys

    from btc_predictor.research_backtest import runner

    paths = runner.frozen_code_paths(repository, list(sys.modules.items()))
    mine = (Path("btc_predictor") / "research_backtest" / "diagnosis.py").as_posix()
    frozen_paths = [path for path in paths if path != mine]
    mismatches = runner.frozen_code_mismatches(repository, frozen_commit, frozen_paths)
    if mismatches:
        raise DiagnosisRefused("FROZEN_CODE_REFUSED", f"{len(mismatches)} file(s) differ from {frozen_commit[:7]}: {mismatches[:5]}")
    runner_paths = [(Path("btc_predictor") / "research_backtest" / name).as_posix() for name in runner.RUNNER_MODULES]
    mismatches = runner.frozen_code_mismatches(repository, run_commit, runner_paths)
    if mismatches:
        raise DiagnosisRefused("FROZEN_CODE_REFUSED", f"the runner differs from RBT-007's run commit {run_commit[:7]}: {mismatches}")
    return {"frozen_code_files_checked": len(frozen_paths), "runner_files_checked": len(runner_paths)}


def _refusals() -> tuple[type[Exception], ...]:
    from btc_predictor.research_backtest.backfill_sources import BackfillRefused
    from btc_predictor.research_backtest.dataset_reader import DatasetBuildRefused
    from btc_predictor.research_backtest.replay_inputs import ReplayInputRefused
    from btc_predictor.research_backtest.runner import RunnerRefused

    return (DiagnosisRefused, RunnerRefused, DatasetBuildRefused, BackfillRefused, ReplayInputRefused, prereg.PreregistrationRefused, ec.EntryComposerError)


def main(argv: Sequence[str] | None = None, *, out: Callable[[str], None] = print) -> int:
    import argparse

    from btc_predictor.config.strategy import load_strategy_config
    from btc_predictor.research_backtest import backfill_run as run
    from btc_predictor.research_backtest import dataset_build as build
    from btc_predictor.research_backtest import runner

    parser = argparse.ArgumentParser(prog="diagnosis", description=__doc__.splitlines()[0])
    parser.add_argument("--store", required=True, help="a clone of the private repository at the dataset's commit, with RBT-007's files")
    parser.add_argument("--out", required=True, help="the private directory the diagnosis's files are written to")
    args = parser.parse_args(argv)
    REFUSALS = _refusals()
    try:
        repository = build.PUBLIC_REPOSITORY
        code = build.code_commit(repository)  # refuses uncommitted tracked changes
        preregistration = runner.read_preregistration(repository)
        champion = load_strategy_config()
        runner.verify_preregistration(preregistration, champion)
        store = run.EvidenceStore(Path(args.store).expanduser(), public_repository=repository)
        frozen = runner.load_frozen_inputs(store)
        runner.verify_preregistration(preregistration, champion, frozen)
        venues = [venue for venue in ("BITSTAMP", "COINBASE", "BITFINEX") if venue in frozen.inputs]
        ledgers, rbt007 = rbt007_ledgers(store.root, repository, venues)
        bound = rbt007["identity"]
        if bound.get("private_dataset_commit") != frozen.private_commit or bound.get("dataset_index_sha256") != frozen.index_sha256:
            raise DiagnosisRefused("LEDGER_REFUSED", "RBT-007's ledgers were not run on the loaded dataset")
        evidence = load_source_evidence(store, venues)
        checked = require_code(repository, preregistration["code_commit"], bound["run_code_commit"])  # every module loaded
        windows = runner.evaluation_windows(preregistration)
        results = {}
        for venue in venues:
            start, last = windows[venue]
            instants = [instant for instant in prereg.decision_schedule() if start <= instant <= last]
            out(f"{venue}: {len(instants)} decisions")
            results[venue] = diagnose_venue(frozen.inputs[venue], ledgers[venue], instants, evidence, strategy_config=champion, progress=out)
        identity = {
            "code_commit": code,
            "frozen_code_commit": preregistration["code_commit"],
            "rbt007_run_code_commit": bound["run_code_commit"],
            "private_dataset_commit": frozen.private_commit,
            "dataset_index_sha256": frozen.index_sha256,
            "rbt007_index_sha256": rbt007["index_sha256"],
            **checked,
        }
        report = build_report(identity, results)
        refusals = publication_refusals(report)
        if refusals:
            raise DiagnosisRefused("PUBLICATION_REFUSED", f"nothing published: {refusals}")
        files = report_files(report)
        runner._write_fresh(Path(args.out).expanduser(), files)
        runner._write_fresh(repository / prereg.ARTIFACT_DIRECTORY, {INDEX_FILE: canonical_json_bytes(public_index(report, files))})
    except REFUSALS as refused:
        out(f"refused: {refused}")
        return 2
    out(f"diagnosis written: {sorted(files)} (private), {INDEX_FILE} (public)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
