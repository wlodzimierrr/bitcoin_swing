"""RBT-006 ``FREEZE_RESEARCH_CHAMPION_AND_PREREGISTER_V1``: the freeze and the preregistration.

Everything here is fixed before any research-backtest result exists (policy
``RESEARCH_BACKTEST_POLICY_V7`` sections 3, 6 and 8; the RBT-006 owner rulings
of 2026-11-11). It computes no trade, fill or outcome. It reads only owner
code, the strategy configuration, the RBT-003 dataset's public index and,
for the completeness-only pass, the frozen replay inputs, from which it keeps
dates, completeness flags and reason codes: never a value.

- **ETF fund launch dates (ruling 1).** Each fund's first US trading date is
  the date of its first row in RBT-003's frozen ``etf_flows`` input, named by
  that file's digest, cross-checked against the documented first trading
  dates below; any mismatch, an undocumented fund or a documented fund absent
  from the evidence refuses.
- **The decision schedule.** Every UTC midnight strictly inside the data
  window: from ``2020-01-02 00:00`` (the close of the window's first full UTC
  day) to ``2025-12-31 00:00``. The midnight at the window's end is excluded:
  a decision there would execute on the next bar, in the holdout.
- **Walk-forward folds (ruling 2).** BTC-182's configured expanding scheme
  with 182-period test windows, a 182-period step and no embargo, counted in
  decision instants. Each venue trains on every instant before its
  evaluation-window start, so its first out-of-sample window begins there; a
  shorter tail is reported as untested.
- **Threshold sweeps (ruling 3, clarifications 3a-3c).** Every BTC-185
  parameter, on the long setups' configuration paths, at its configured
  value and at +-10% and +-20% of it. Each distinct configured value is its
  own one-scalar sweep; a candidate the configuration or the BTC-185 owner
  refuses is dropped with its reason; fewer than two candidates leaves the
  value unswept. The stop buffer, which the configuration accepts only from
  its own ``sweep_atr_multipliers``, is swept over that grid (3c).
  ``mean_return_fraction``, plateau tolerance 0.005, the ``base`` cost rung,
  ``SENSITIVITY_ONLY_NOT_SELECTION``.
- **The Momentum Persistence ablation (policy V7 sections 6A.10 and 8).**
  Hold Score without ``momentum_persistence``: its weight 0 and the other four
  divided by their sum, at the configuration's seven decimals.
- **The metric definitions and the report version (ruling 4, clarification
  4a).** A canonical, hash-bound definition of every Rulebook section 28
  primary metric: the existing BTC-180..185 owner convention where one
  exists, otherwise a formula labelled ``NEW_DEFINITION``, consistent with
  those conventions; and the policy section 8 cross-venue source-sensitivity
  measures (4a).
- **The completeness-only pass (V6 section 5A.6; the ticket).** At every
  decision instant it composes the five Entry Conviction components and the
  core regime score through the reviewed RBT-004 composer's own steps, and
  records only whether each is complete, its accounted missing-input causes
  and any unaccounted cause. It never composes Entry Conviction, the
  Rulebook 24 flags, a setup, a gate or an intent. A venue's evaluation-window
  start is its first instant at which all six are complete; an unaccounted
  cause, or an ETF calendar date outside the closure table's coverage, blocks
  the freeze.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import tomllib
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path
from typing import Any

from btc_predictor.backtest.threshold_sweeps import (
    ADD_THRESHOLD,
    ENTRY_CONVICTION,
    FLOW_MINIMUM,
    HOLD_THRESHOLD,
    MEAN_RETURN_OBJECTIVE,
    POSITIONING_MINIMUM,
    REWARD_RISK_MINIMUM,
    RISK_BUDGET,
    STOP_BUFFER,
    STRUCTURE_MINIMUM,
    THRESHOLD_PARAMETERS,
    TREND_MINIMUM,
    threshold_parameter_value,
    threshold_sweep_spec,
)
from btc_predictor.backtest.walk_forward import (
    EXPANDING_SCHEME,
    WALK_FORWARD_CAPITAL_POLICY_VERSION,
    walk_forward_plan,
    walk_forward_windows,
)
from btc_predictor.config.strategy import (
    DEFAULT_STRATEGY_CONFIG_PATH,
    StrategyConfig,
    StrategyConfigError,
    load_strategy_config,
)
from btc_predictor.data import EtfFlow
from btc_predictor.features.hold import HOLD_SCORE_COMPONENT_IDS, HOLD_SCORE_WEIGHT_SUM_TOLERANCE
from btc_predictor.research.us_equity_market_closures import DEFINITION_SHA256 as CLOSURE_TABLE_SHA256
from btc_predictor.research_backtest import entry_composer as ec
from btc_predictor.research_backtest.completion_spec import CHAMPION_BASE_IDENTITY, RESEARCH_STRATEGY_ID, SPEC_VERSION
from btc_predictor.research_backtest.entry_composer import (
    CAUSE_DECISION_PRICE_BAR_MISSING,
    CLOSURE_TABLE_COVERAGE_END,
    CLOSURE_TABLE_COVERAGE_START,
    CLOSURE_TABLE_VERSION,
    COMPLETION_SPEC_SHA256,
    COMPONENT_NAMES,
    ENTRY_COMPOSER_VERSION,
    LEDGER_VERSION,
    EntryComposer,
    EntryComposerInputs,
    EtfFundLaunch,
    UnevaluableComponent,
    is_daily_decision_instant,
)
from btc_predictor.research_backtest.management_composer import MANAGEMENT_COMPOSER_VERSION, MANAGEMENT_LEDGER_VERSION
from btc_predictor.research_backtest.replay_inputs import (
    CANONICAL_REFERENCE_UNRESOLVED,
    DATA_WINDOW,
    RESEARCH_EVIDENCE_CLASS,
    ReplayInputRefused,
    ReplayWindow,
    canonical_json_bytes,
    replay_market_bars_at,
    sha256_hex,
)
from btc_predictor.research_backtest.replay_inputs_v2 import REPLAY_AVAILABILITY_POLICY_V2, RESEARCH_BACKTEST_POLICY_V7

PREREGISTRATION_VERSION = "RBT006_PREREGISTRATION_V1"
PREREGISTRATION_TICKET = "FREEZE_RESEARCH_CHAMPION_AND_PREREGISTER_V1"
REPORT_VERSION = "RESEARCH_BACKTEST_REPORT_V1"
METRIC_SPEC_VERSION = "RESEARCH_BACKTEST_METRIC_DEFINITIONS_V1"
COMPLETENESS_PASS_VERSION = "RBT006_COMPLETENESS_ONLY_PASS_V1"
SENSITIVITY_ONLY = "SENSITIVITY_ONLY_NOT_SELECTION"
HEADLINE_COST_RUNG = "base"
COST_RUNGS = ("optimistic", "base", "stress")

_DAY = timedelta(days=1)
_HEX64 = re.compile(r"[0-9a-f]{64}")
_HEX40 = re.compile(r"[0-9a-f]{40}")


class PreregistrationRefused(ValueError):
    """A freeze input that does not meet the RBT-006 rulings; nothing is frozen."""

    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(f"{reason_code}: {message}")
        self.reason_code = reason_code


def _refuse(code: str, message: str) -> PreregistrationRefused:
    return PreregistrationRefused(code, message)


# --- ruling 1: ETF fund launch dates ------------------------------------------------------------

_EDGAR = "https://www.sec.gov/Archives/edgar/data/"
_JANUARY_ORDER = (
    "SEC Release No. 34-99306 (Jan. 10, 2024), 89 FR 3008 (Jan. 17, 2024), approving the NYSE Arca, Nasdaq and Cboe BZX "
    "listings of eleven spot bitcoin products"
)
_MINI_ORDER = "SEC Release No. 34-100610 (July 26, 2024), 89 FR 62821 (Aug. 1, 2024), SR-NYSEARCA-2024-45, approving its NYSE Arca listing"


def _filing(order: str, document: str, statement: str, url: str) -> str:
    return f"{order}; {document}: {statement} ({_EDGAR}{url})"


# The documented first US trading date of every fund in RBT-003's CoinGlass
# history (review F4: each with the approval order and the fund's own filing).
# GBTC traded over the counter as a trust before; under ruling 1 its launch is
# its first day as a listed ETF, its 2024-01-11 uplisting. HODL's two annual
# reports give 2024-01-10, the approval order's date; its launch announcement,
# filed with the SEC, and every other fund give 2024-01-11, and the citation
# records the conflict.
DOCUMENTED_FIRST_TRADING_DATES: Mapping[str, tuple[date, str]] = {
    "ARKB": (date(2024, 1, 11), _filing(
        _JANUARY_ORDER, "ARK 21Shares Bitcoin ETF Form 10-K FY2024 (0001013762-25-002798), Item 1",
        '"commenced on January 11, 2024 (the day the Trust\'s Shares were initially listed on the Exchange)", Cboe BZX',
        "1869699/000101376225002798/ea0234790-10k_ark21shares.htm",
    )),
    "BITB": (date(2024, 1, 11), _filing(
        _JANUARY_ORDER, "Bitwise Bitcoin ETF Form 10-K FY2024 (0000950170-25-040572)",
        '"The Trust commenced operations on January 10, 2024 and commenced trading on the Exchange on January 11, 2024.", NYSE Arca',
        "1763415/000095017025040572/bitb-20241231.htm",
    )),
    "BRRR": (date(2024, 1, 11), _filing(
        _JANUARY_ORDER, "CoinShares Valkyrie Bitcoin Fund Form 10-K FY2024 (0001999371-25-003309), Item 5",
        "the date the Shares began trading, January 11, 2024, Nasdaq",
        "1841175/000199937125003309/brrr_10k-123124.htm",
    )),
    "BTC": (date(2024, 7, 31), _filing(
        _MINI_ORDER, "Grayscale Bitcoin Mini Trust ETF Form 10-K FY2024 (0000950170-25-029405), Item 1",
        '"which began trading on NYSE Arca on July 31, 2024"',
        "2015034/000095017025029405/btc-20241231.htm",
    )),
    "BTCO": (date(2024, 1, 11), _filing(
        _JANUARY_ORDER, "Invesco Galaxy Bitcoin ETF Form 10-K FY2024 (0000950170-25-029444), Item 1",
        '"The Trust commenced trading on the Cboe BZX Exchange Inc. (the \u201cExchange\u201d) on January 11, 2024."',
        "1855781/000095017025029444/btco-20241231.htm",
    )),
    "BTCW": (date(2024, 1, 11), _filing(
        _JANUARY_ORDER, "WisdomTree Bitcoin Fund Form 10-K FY2024 (0001214659-25-004851), Item 1",
        '"began trading under the ticker symbol \u201cBTCW\u201d on January 11, 2024", Cboe BZX',
        "1850391/000121465925004851/wtb3242510k.htm",
    )),
    "EZBC": (date(2024, 1, 11), _filing(
        _JANUARY_ORDER, "Franklin Templeton Digital Holdings Trust (Franklin Bitcoin ETF) Form 10-K for the fiscal year ended March 31, 2024 (0001193125-24-173040)",
        '"The registrant\'s shares began trading on the Cboe BZX Exchange, Inc. on January 11, 2024."',
        "1992870/000119312524173040/d772184d10k.htm",
    )),
    "FBTC": (date(2024, 1, 11), _filing(
        _JANUARY_ORDER, "Fidelity Wise Origin Bitcoin Fund Form 10-K FY2024 (0000950170-25-039452), Note 1",
        '"On January 11, 2024, the Trust commenced operations and Shares commenced trading on Cboe BZX Exchange, Inc."',
        "1852317/000095017025039452/ck0001852317-20241231.htm",
    )),
    "GBTC": (date(2024, 1, 11), _filing(
        _JANUARY_ORDER, "Grayscale Bitcoin Trust ETF Form 10-K FY2024 (0000950170-25-029408), Item 1",
        '"began trading on NYSE Arca on January 11, 2024 (the \u201cUplisting Date\u201d)"; before it the Shares were quoted on the OTCQX Best Market',
        "1588489/000095017025029408/gbtc-20241231.htm",
    )),
    "HODL": (date(2024, 1, 11), _filing(
        _JANUARY_ORDER, "VanEck Bitcoin Trust launch announcement filed as Form FWP (0001628280-24-001064)",
        '"NEW YORK, NY (January 11, 2024) ... VanEck is today launching the VanEck Bitcoin Trust", Cboe BZX. CONFLICT: its Forms 10-K '
        "FY2023 (0000930413-24-001178) and FY2024 (0000930413-25-000995), Item 5, say \"On January 10, 2024, the Shares commenced "
        "trading on Cboe BZX\", the approval order's own date; 2024-01-11 is kept with the announcement and the other ten funds",
        "1838028/000162828024001064/hodlfundlaunchpressrelea.htm",
    )),
    "IBIT": (date(2024, 1, 11), _filing(
        _JANUARY_ORDER, "iShares Bitcoin Trust ETF Form 10-K FY2024 (0001437749-25-006260), Item 5",
        '"On January 11, 2024, the Shares commenced trading on NASDAQ under the ticker symbol IBIT."',
        "1980994/000143774925006260/bit20241231_10k.htm",
    )),
}


def etf_fund_launches(etf_rows: Sequence[EtfFlow], *, evidence_sha256: str) -> tuple[EtfFundLaunch, ...]:
    """Each fund's launch: its first row in the frozen evidence, cross-checked (ruling 1).

    Only each row's fund and observation date are read.
    """

    if type(evidence_sha256) is not str or not _HEX64.fullmatch(evidence_sha256):
        raise _refuse("ETF_LAUNCH_REFUSED", "the evidence must be named by its SHA-256")
    first: dict[str, date] = {}
    for row in etf_rows:
        if type(row) is not EtfFlow:
            raise _refuse("ETF_LAUNCH_REFUSED", "launch dates come only from EtfFlow rows")
        if row.fund not in first or row.observation_date < first[row.fund]:
            first[row.fund] = row.observation_date
    if not first:
        raise _refuse("ETF_LAUNCH_REFUSED", "the evidence holds no ETF row")
    undocumented = sorted(set(first) - set(DOCUMENTED_FIRST_TRADING_DATES))
    if undocumented:
        raise _refuse("ETF_LAUNCH_REFUSED", f"funds without a documented first trading date: {undocumented}")
    absent = sorted(set(DOCUMENTED_FIRST_TRADING_DATES) - set(first))
    if absent:
        raise _refuse("ETF_LAUNCH_REFUSED", f"documented funds absent from the evidence: {absent}")
    mismatched = sorted(fund for fund, day in first.items() if day != DOCUMENTED_FIRST_TRADING_DATES[fund][0])
    if mismatched:
        raise _refuse("ETF_LAUNCH_MISMATCH", f"first evidence row differs from the documented first trading date: {mismatched}")
    return tuple(
        EtfFundLaunch(
            fund=fund,
            first_trading_date=first[fund],
            source=(
                f"first row in RBT-003's frozen etf_flows input (sha256 {evidence_sha256}); "
                f"documented: {DOCUMENTED_FIRST_TRADING_DATES[fund][1]}"
            ),
        )
        for fund in sorted(first)
    )


def launch_records(launches: Sequence[EtfFundLaunch]) -> list[dict[str, str]]:
    return [
        {"fund": launch.fund, "first_trading_date": launch.first_trading_date.isoformat(), "source": launch.source}
        for launch in launches
    ]


# --- the decision schedule and ruling 2: walk-forward folds -------------------------------------

FOLD_TEST_PERIODS = 182
FOLD_STEP_PERIODS = 182
FOLD_EMBARGO_PERIODS = 0


def decision_schedule(window: ReplayWindow = DATA_WINDOW) -> tuple[datetime, ...]:
    """Every UTC midnight strictly inside ``window``.

    A decision at the window's end would execute on the next bar, outside the
    window, so the last instant is the midnight before it.
    """

    if window.start is None or window.end is None:
        raise _refuse("SCHEDULE_REFUSED", "the schedule needs a bounded window")
    instants = []
    instant = datetime.combine(window.start.date(), datetime.min.time(), tzinfo=UTC) + _DAY
    while instant < window.end:
        instants.append(instant)
        instant += _DAY
    return tuple(instants)


def fold_plan(evaluation_start: datetime, schedule: Sequence[datetime], *, strategy_config: StrategyConfig) -> dict[str, Any]:
    """The venue's pre-registered BTC-182 split (ruling 2), as a record."""

    timestamps = tuple(schedule)
    if evaluation_start not in timestamps:
        raise _refuse("FOLD_PLAN_REFUSED", "the evaluation start is not a scheduled decision instant")
    declared = strategy_config.backtest.walk_forward
    if declared.scheme != EXPANDING_SCHEME:
        raise _refuse("FOLD_PLAN_REFUSED", f"ruling 2 keeps the configured expanding scheme, not {declared.scheme}")
    train = timestamps.index(evaluation_start)
    if train < 1:
        raise _refuse("FOLD_PLAN_REFUSED", "BTC-182 needs at least one training period before the evaluation start")
    plan = walk_forward_plan(
        strategy_config,
        scheme=EXPANDING_SCHEME,
        train_periods=train,
        test_periods=FOLD_TEST_PERIODS,
        step_periods=FOLD_STEP_PERIODS,
        embargo_periods=FOLD_EMBARGO_PERIODS,
    )
    folds = plan.fold_count(len(timestamps))
    windows = walk_forward_windows(timestamps, plan=plan) if folds else ()
    tested = folds * FOLD_STEP_PERIODS
    return {
        "plan": plan.as_record(),
        "capital_policy_version": WALK_FORWARD_CAPITAL_POLICY_VERSION,
        "schedule_periods": len(timestamps),
        "training_periods": train,
        "fold_count": folds,
        "untested_periods": len(timestamps) - train - tested,
        "folds": [
            {
                "fold_number": window.fold_number,
                "test_start": window.test_start.isoformat(),
                "test_end": window.test_end.isoformat(),
            }
            for window in windows
        ],
    }


# --- ruling 3: the threshold-sweep grid ---------------------------------------------------------

SWEEP_FACTORS = (Decimal("0.8"), Decimal("0.9"), Decimal("1"), Decimal("1.1"), Decimal("1.2"))
UNIFORM_GRID_RULE = "the configured value and +-10% and +-20% of it (ruling 3); refused candidates dropped (3a)"
# Ruling 3c: the configuration only accepts a stop buffer from its own declared
# research grid, so every uniform candidate is refused; the stop buffer is swept
# over that grid instead, the one exception to the uniform rule.
STOP_BUFFER_GRID_RULE = "the configured stop_buffers.sweep_atr_multipliers, the configuration's own stop-buffer grid (ruling 3c)"
SWEEP_OBJECTIVE = MEAN_RETURN_OBJECTIVE
SWEEP_PLATEAU_TOLERANCE = Decimal("0.005")
SWEEP_COST_RUNG = HEADLINE_COST_RUNG

_LONG_SETUPS = ("bull_trend_continuation", "bullish_reset", "capitulation_reversal")

# Each BTC-185 parameter's configuration paths on the long setups (the
# short-only setup stays fixed, policy V7 section 6A.6). Paths holding the same
# configured value move together; each distinct value is its own sweep (3b).
SWEEP_PARAMETER_PATHS: Mapping[str, tuple[str, ...]] = {
    ENTRY_CONVICTION: (
        "entry_thresholds.valid_trade_min",
        *(f"setup_requirements.{setup}.entry_conviction_min" for setup in _LONG_SETUPS),
    ),
    TREND_MINIMUM: (
        "setup_requirements.bull_trend_continuation.trend_min",
        "setup_requirements.bullish_reset.trend_min",
    ),
    FLOW_MINIMUM: ("setup_requirements.bull_trend_continuation.flow_min",),
    POSITIONING_MINIMUM: ("setup_requirements.bull_trend_continuation.positioning_min",),
    STRUCTURE_MINIMUM: tuple(f"setup_requirements.{setup}.structure_min" for setup in _LONG_SETUPS),
    REWARD_RISK_MINIMUM: (
        "price_levels.rr_minimum",
        *(f"setup_requirements.{setup}.minimum_rr" for setup in _LONG_SETUPS),
    ),
    STOP_BUFFER: ("stop_buffers.atr_multiplier",),
    # Ruling 3d (review F1): the Hold Score thresholds a decision owner of the
    # champion reads -- the trim owner reads all three, the exit owner exit_below.
    HOLD_THRESHOLD: ("hold_thresholds.defensive_min", "hold_thresholds.trim_min", "hold_thresholds.exit_below"),
    ADD_THRESHOLD: ("add_thresholds.add_min",),
    RISK_BUDGET: tuple(f"risk.schedule.{row}.risk_fraction_nav" for row in range(3)),
}

# Ruling 3d: configuration paths of a BTC-185 parameter that no decision owner
# of the champion reads (only the configuration's ordering check does). They
# are recorded and never swept: a sweep of them would report the stability of
# an inert value.
SWEEP_UNREAD_PATHS: Mapping[str, tuple[str, ...]] = {
    HOLD_THRESHOLD: ("hold_thresholds.possible_add_min", "hold_thresholds.hold_min", "hold_thresholds.no_add_min"),
}
UNREAD_PATH_REASON = "NO_DECISION_READER: read only by the configuration's ordering check (ruling 3d)"


def unread_sweep_paths() -> list[dict[str, Any]]:
    """The recorded, unswept paths of ruling 3d, with their configured values."""

    base = _configuration_mapping()
    return [
        {
            "parameter": parameter,
            "paths": {path: str(_decimal_of(_get_path(base, path), path)) for path in paths},
            "reason": UNREAD_PATH_REASON,
        }
        for parameter, paths in SWEEP_UNREAD_PATHS.items()
    ]


def _configuration_mapping() -> dict[str, Any]:
    with DEFAULT_STRATEGY_CONFIG_PATH.open("rb") as handle:
        return tomllib.load(handle)


def _segments(path: str) -> list[str | int]:
    return [int(part) if part.isdigit() else part for part in path.split(".")]


def _step(node: Any, segment: str | int, path: str) -> Any:
    if isinstance(node, dict) and type(segment) is str and segment in node:
        return node[segment]
    if isinstance(node, list) and type(segment) is int and 0 <= segment < len(node):
        return node[segment]
    raise _refuse("SWEEP_REFUSED", f"{path} is not a configuration path")


def _get_path(data: Any, path: str) -> Any:
    node = data
    for segment in _segments(path):
        node = _step(node, segment, path)
    return node


def _set_path(data: Any, path: str, value: Any) -> None:
    *parents, last = _segments(path)
    node = data
    for segment in parents:
        node = _step(node, segment, path)
    _step(node, last, path)
    node[last] = value


def _decimal_of(value: Any, path: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise _refuse("SWEEP_REFUSED", f"{path} is not a number")
    return _plain(Decimal(str(value)))


def _plain(value: Decimal) -> Decimal:
    """The value without trailing zeros, in plain notation (72.0 -> 72, 1.60 -> 1.6)."""

    return Decimal(f"{value.normalize():f}")


def sweep_grid(strategy_config: StrategyConfig | None = None) -> list[dict[str, Any]]:
    """Every pre-registered sweep (ruling 3, 3a, 3b), in parameter and path order."""

    config = strategy_config if strategy_config is not None else load_strategy_config()
    if dict(config.run_metadata()) != dict(CHAMPION_BASE_IDENTITY):
        raise _refuse("SWEEP_REFUSED", "the sweeps are registered against the champion's configuration")
    if set(SWEEP_PARAMETER_PATHS) != set(THRESHOLD_PARAMETERS):
        raise _refuse("SWEEP_REFUSED", "every BTC-185 parameter needs its configuration paths")
    if {path for paths in SWEEP_UNREAD_PATHS.values() for path in paths} & {path for paths in SWEEP_PARAMETER_PATHS.values() for path in paths}:
        raise _refuse("SWEEP_REFUSED", "a path without a decision reader is never swept (ruling 3d)")
    base = _configuration_mapping()
    if StrategyConfig.from_mapping(copy.deepcopy(base)) != config:
        raise _refuse("SWEEP_REFUSED", "the configuration file is not the champion's configuration")
    sweeps: list[dict[str, Any]] = []
    for parameter in THRESHOLD_PARAMETERS:
        groups: dict[Decimal, list[str]] = {}
        for path in SWEEP_PARAMETER_PATHS[parameter]:
            groups.setdefault(_decimal_of(_get_path(base, path), path), []).append(path)
        for configured, paths in sorted(groups.items(), key=lambda item: SWEEP_PARAMETER_PATHS[parameter].index(item[1][0])):
            candidates: list[Decimal] = []
            dropped: list[dict[str, str]] = []
            if parameter == STOP_BUFFER:
                rule = STOP_BUFFER_GRID_RULE
                proposed = [("configured", _decimal_of(value, "stop_buffers.sweep_atr_multipliers")) for value in base["stop_buffers"]["sweep_atr_multipliers"]]
            else:
                rule = UNIFORM_GRID_RULE
                proposed = [(str(factor), _plain(configured * factor)) for factor in SWEEP_FACTORS]
            for factor, value in proposed:
                reason = _candidate_refusal(base, parameter, paths, value)
                if reason is None:
                    candidates.append(value)
                else:
                    dropped.append({"factor": factor, "value": str(value), "reason": reason})
            record: dict[str, Any] = {
                "parameter": parameter,
                "configured_value": str(configured),
                "parameter_paths": sorted(paths),
                "grid_rule": rule,
                "candidate_values": [str(value) for value in sorted(candidates)],
                "dropped_candidates": dropped,
                "label": SENSITIVITY_ONLY,
                "cost_rung": SWEEP_COST_RUNG,
            }
            if len(candidates) < 2:
                record["status"] = "NOT_SWEPT_FEWER_THAN_TWO_CANDIDATES"
                record["spec"] = None
            else:
                spec = threshold_sweep_spec(
                    parameter=parameter,
                    candidate_values=candidates,
                    baseline_value=configured,
                    parameter_paths=paths,
                    base_config_metadata=config.run_metadata(),
                    objective_metric=SWEEP_OBJECTIVE,
                    plateau_tolerance=SWEEP_PLATEAU_TOLERANCE,
                )
                record["status"] = "SWEPT"
                record["spec"] = spec.as_record()
            sweeps.append(record)
    return sweeps


def _candidate_refusal(base: Mapping[str, Any], parameter: str, paths: Sequence[str], value: Decimal) -> str | None:
    """Why ``value`` cannot be configured on ``paths`` (3a), or None."""

    try:
        threshold_parameter_value(value, parameter, name="candidate_value")
    except (TypeError, ValueError) as error:
        return f"BTC185_OWNER: {error}"
    data = copy.deepcopy(dict(base))
    configured_type = type(_get_path(data, paths[0]))
    number: int | float = int(value) if configured_type is int and value == value.to_integral_value() else float(value)
    for path in paths:
        _set_path(data, path, number)
    try:
        StrategyConfig.from_mapping(data)
    except StrategyConfigError as error:
        return f"STRATEGY_CONFIG: {error}"
    return None


# --- the Momentum Persistence ablation variant (policy V7 sections 6A.10 and 8) -----------------

ABLATION_VARIANT_ID = "swing_v1.2+completion_v1+hold_without_momentum_persistence_v1"
ABLATED_HOLD_COMPONENT = "momentum_persistence"
_WEIGHT_PLACES = Decimal("0.0000001")


def ablation_variant(strategy_config: StrategyConfig | None = None) -> dict[str, Any]:
    """The frozen variant: Hold Score without Momentum Persistence, re-normalized proportionally."""

    config = strategy_config if strategy_config is not None else load_strategy_config()
    configured = {key: Decimal(str(value)) for key, value in config.scoring_weights.hold_score.items()}
    if set(configured) != set(HOLD_SCORE_COMPONENT_IDS):
        raise _refuse("ABLATION_REFUSED", "the Hold Score weights do not match its components")
    remaining = sum((weight for key, weight in configured.items() if key != ABLATED_HOLD_COMPONENT), Decimal("0"))
    variant = {
        key: (Decimal("0") if key == ABLATED_HOLD_COMPONENT else (weight / remaining).quantize(_WEIGHT_PLACES, rounding=ROUND_HALF_EVEN))
        for key, weight in configured.items()
    }
    total = sum(variant.values(), Decimal("0"))
    if abs(total - Decimal("1")) > HOLD_SCORE_WEIGHT_SUM_TOLERANCE:
        raise _refuse("ABLATION_REFUSED", f"the re-normalized weights sum to {total}")
    return {
        "variant_id": ABLATION_VARIANT_ID,
        "champion": RESEARCH_STRATEGY_ID,
        "label": SENSITIVITY_ONLY,
        "rule": (
            "Hold Score without the MomentumPersistence term: its weight 0, the other four divided by their "
            "configured sum, rounded half-even to the configuration's seven decimals (Rulebook 20's re-normalization)"
        ),
        "configured_weights": {key: str(value) for key, value in sorted(configured.items())},
        "variant_weights": {key: str(value) for key, value in sorted(variant.items())},
        "variant_weight_sum": str(total),
        "evaluation": {
            "window": "evaluation window only, never the holdout",
            "cost_rung": HEADLINE_COST_RUNG,
            "reported": [
                "the count of Hold evaluations whose Rulebook 20 action band differs between champion and variant",
                "a full variant replay beside the champion's section 28 primary metrics, with trade counts",
            ],
            "selection": "never selects or replaces the champion",
        },
    }


# --- ruling 4: the metric definitions -----------------------------------------------------------

_OWNER = "OWNER_CONVENTION"
_NEW = "NEW_DEFINITION"

_CONVENTIONS = {
    "closed_trade": "a BTC-180 PaperTradeAccounting whose closed is true; open trades are reported separately and enter no closed-trade metric",
    "period_return": "(nav_i - nav_{i-1}) / nav_{i-1} over consecutive BTC-180 EquityPoints, the first against the run's starting NAV (parameter_surfaces._period_returns)",
    "risk_free_rate": "zero",
    "annualization": "none: every ratio is per equity point, as the BTC-188 parameter-surface owner reports Sharpe",
    "status": "a metric that cannot be computed carries its undefined status, never zero",
    "runs": "each metric is computed for the headline evaluation-window run per venue and cost rung, and per BTC-182 fold",
}

_PRIMARY_METRICS: tuple[dict[str, Any], ...] = (
    {
        "metric": "expectancy",
        "rulebook": "Expectancy",
        "authority": _OWNER,
        "owner": "btc_predictor.backtest.threshold_sweeps._metrics closed_trade_expectancy",
        "definition": "mean net_pnl over closed trades",
        "undefined": "NO_CLOSED_TRADES (this specification's name for the owner's None)",
    },
    {
        "metric": "average_r_per_trade",
        "rulebook": "Average R per trade",
        "authority": _OWNER,
        "owner": "btc_predictor.backtest.threshold_sweeps._metrics mean_r_multiple",
        "definition": "mean r_multiple over closed trades whose r_multiple is not None; the count used is reported",
        "undefined": "NO_R_MULTIPLE (this specification's name for the owner's None)",
    },
    {
        "metric": "sharpe",
        "rulebook": "Sharpe",
        "authority": _OWNER,
        "owner": "btc_predictor.backtest.parameter_surfaces._sharpe (POOLED_WITHIN_FOLD_PERIOD_RETURN_ZERO_RF_SHARPE_V1)",
        "definition": "mean period return over its sample standard deviation (n-1), unannualized, zero risk-free rate",
        "undefined": "UNAVAILABLE_INSUFFICIENT_PERIODS | UNDEFINED_ZERO_DISPERSION | UNDEFINED_NON_POSITIVE_NAV",
    },
    {
        "metric": "sortino",
        "rulebook": "Sortino",
        "authority": _NEW,
        "owner": "",
        "definition": (
            "mean period return over the downside deviation sqrt(sum(min(r, 0)^2) / n) over all n period returns, "
            "unannualized, zero target and risk-free rate (the Sharpe convention's periods)"
        ),
        "undefined": "UNAVAILABLE_INSUFFICIENT_PERIODS (n < 2) | UNDEFINED_NO_DOWNSIDE (deviation 0) | UNDEFINED_NON_POSITIVE_NAV",
    },
    {
        "metric": "calmar",
        "rulebook": "Calmar",
        "authority": _OWNER,
        "owner": "btc_predictor.backtest.parameter_surfaces._calmar (MEAN_FOLD_RETURN_OVER_MAX_DRAWDOWN_V1)",
        "definition": "return fraction over max_drawdown, unannualized; per fold the fold's return, for the walk-forward the mean fold return",
        "undefined": "UNDEFINED_NO_DRAWDOWN | UNAVAILABLE_DRAWDOWN",
    },
    {
        "metric": "max_drawdown",
        "rulebook": "Max drawdown",
        "authority": _OWNER,
        "owner": "btc_predictor.backtest.parameter_surfaces._max_drawdown (WORST_FOLD_PEAK_TO_TROUGH_NAV_DRAWDOWN_V1)",
        "definition": "largest (peak - nav) / peak over the equity curve, the peak starting at the starting NAV; the walk-forward reports the worst fold",
        "undefined": "UNAVAILABLE_NO_EQUITY_CURVE | UNDEFINED_NON_POSITIVE_NAV",
    },
    {
        "metric": "return_per_trade",
        "rulebook": "Return per trade",
        "authority": _NEW,
        "owner": "",
        "definition": "mean of net_pnl / entry_notional over closed trades",
        "undefined": "NO_CLOSED_TRADES",
    },
    {
        "metric": "win_rate",
        "rulebook": "Win rate",
        "authority": _NEW,
        "owner": "",
        "definition": "closed trades with net_pnl > 0 over closed trades; a flat trade is not a win",
        "undefined": "NO_CLOSED_TRADES",
    },
    {
        "metric": "profit_factor",
        "rulebook": "Profit factor",
        "authority": _OWNER,
        "owner": "btc_predictor.backtest.setup_performance._profit_factor",
        "definition": "sum of positive closed net_pnl over the absolute sum of negative closed net_pnl",
        "undefined": "NO_CLOSED_TRADES | UNBOUNDED_NO_CLOSED_LOSSES | UNDEFINED_ALL_CLOSED_TRADES_FLAT",
    },
    {
        "metric": "average_winner",
        "rulebook": "Average winner",
        "authority": _NEW,
        "owner": "",
        "definition": "mean net_pnl over closed trades with net_pnl > 0",
        "undefined": "NO_WINNING_TRADES",
    },
    {
        "metric": "average_loser",
        "rulebook": "Average loser",
        "authority": _NEW,
        "owner": "",
        "definition": "mean net_pnl over closed trades with net_pnl < 0 (negative)",
        "undefined": "NO_LOSING_TRADES",
    },
    {
        "metric": "time_in_market",
        "rulebook": "Time in market",
        "authority": _NEW,
        "owner": "",
        "definition": "equity points with open_quantity > 0 over all equity points of the run",
        "undefined": "UNAVAILABLE_NO_EQUITY_CURVE",
    },
    {
        "metric": "turnover",
        "rulebook": "Turnover",
        "authority": _NEW,
        "owner": "",
        "definition": "sum over trades of entry_notional + exit_notional, over the mean equity-point NAV, unannualized; the run's length in days is reported beside it",
        "undefined": "UNAVAILABLE_NO_EQUITY_CURVE | UNDEFINED_NON_POSITIVE_NAV",
    },
    {
        "metric": "number_of_trades",
        "rulebook": "Number of trades",
        "authority": _OWNER,
        "owner": "btc_predictor.backtest.walk_forward.WalkForwardFold trade_count and closed_trade_count",
        "definition": "the run's trades, with the closed count and the count open at the run's end beside it",
        "undefined": "never undefined; zero is a count",
    },
    {
        "metric": "longest_drawdown",
        "rulebook": "Longest drawdown",
        "authority": _NEW,
        "owner": "",
        "definition": (
            "the longest time underwater, in hours (seconds / 3600). The running peak starts at the run's starting NAV at the run's "
            "started_at (its first bar's timestamp) and rises to each equity point's nav above it; an equity point whose nav is at or "
            "above the running peak is at the peak. A drawdown begins at the latest at-peak instant (started_at for the starting NAV, "
            "else that point's as_of) before an equity point whose nav is strictly below the running peak, and ends at the as_of of "
            "the first later point at or above that peak (recovered) or, if none, at the run's last equity point's as_of "
            "(unrecovered). A run with no point strictly below its running peak has longest drawdown 0 hours; of equal lengths the "
            "first is reported, with its recovered or unrecovered mark. Per fold, the fold's run; the walk-forward reports the "
            "longest fold value, as max_drawdown reports the worst fold"
        ),
        "examples": [
            {"case": "steady rise", "starting_nav": "100", "points": [["1", "101"], ["2", "102"]], "hours": "0", "recovered": None},
            {"case": "plateau at the peak", "starting_nav": "100", "points": [["1", "100"], ["2", "100"]], "hours": "0", "recovered": None},
            {"case": "first point below the starting NAV", "starting_nav": "100", "points": [["1", "99"], ["2", "100"]], "hours": "2", "recovered": True},
            {
                "case": "recovered at an equal NAV",
                "starting_nav": "100",
                "points": [["1", "101"], ["2", "100.5"], ["3", "100.8"], ["4", "101"], ["5", "102"]],
                "hours": "3",
                "recovered": True,
            },
            {"case": "unrecovered at the run's end", "starting_nav": "100", "points": [["1", "102"], ["2", "101"], ["3", "100"]], "hours": "2", "recovered": False},
            {
                "case": "the longer of two drawdowns",
                "starting_nav": "100",
                "points": [["1", "99"], ["2", "100"], ["3", "101"], ["4", "100"], ["5", "100.5"], ["6", "101.5"]],
                "hours": "3",
                "recovered": True,
            },
        ],
        "examples_note": "each point is [hours after started_at of its as_of, its nav]",
        "undefined": "UNAVAILABLE_NO_EQUITY_CURVE",
    },
    {
        "metric": "longest_losing_streak",
        "rulebook": "Longest losing streak",
        "authority": _NEW,
        "owner": "",
        "definition": "the most consecutive closed trades, ordered by closed_at, with net_pnl < 0; a trade with net_pnl >= 0 ends a streak",
        "undefined": "never undefined; zero with no closed trade",
    },
)


_CROSS_VENUE_MEASURES: tuple[dict[str, str], ...] = (
    {
        "measure": "trade_set_overlap",
        "authority": _NEW,
        "definition": (
            "two trades on different venues match when their ARM_ENTRY ledger rows share the daily decision instant and the setup; "
            "per venue pair: matched, only-first and only-second counts and matched / (matched + only-first + only-second); "
            "and the count matched on all three venues"
        ),
        "undefined": "NO_TRADES on both venues of a pair",
    },
    {
        "measure": "matched_trade_divergence",
        "authority": _NEW,
        "definition": (
            "per matched pair (second venue against first, venues in the order bitstamp, coinbase, bitfinex): the relative difference "
            "(second - first) / first of the average entry price, the initial stop price and the average exit price "
            "(exit notional over exited quantity, closed trades only); and the difference of MFE and of MAE, each over its own "
            "trade's initial risk (R units, under PaperTradeAccounting's SIGNED_GROSS_PNL_FULL_BARS_AND_FILL_ENDPOINTS_V1 excursions); per pair: the matched count, the mean, the median and "
            "the largest absolute difference of each"
        ),
        "undefined": "NO_MATCHED_TRADES",
    },
    {
        "measure": "stop_touch_divergence",
        "authority": _NEW,
        "definition": (
            "per venue pair: among matched pairs whose trades are both closed, the count where exactly one trade exited through the "
            "BTC-180 STRUCTURAL_STOP exit, beside the matched closed count"
        ),
        "undefined": "NO_MATCHED_CLOSED_TRADES",
    },
    {
        "measure": "metric_dispersion",
        "authority": _NEW,
        "definition": (
            "for each primary metric and cost rung: the three venues' values and their maximum minus minimum, when the metric is "
            "defined on all three venues; otherwise the venues' statuses"
        ),
        "undefined": "UNDEFINED_ON_SOME_VENUE",
    },
)


def metric_definitions() -> dict[str, Any]:
    """The frozen, hash-bound metric definitions (ruling 4, clarification 4a)."""

    return {
        "metric_spec_version": METRIC_SPEC_VERSION,
        "report_version": REPORT_VERSION,
        "rulebook_section": "28 primary metrics",
        "conventions": dict(_CONVENTIONS),
        "trade_count_rule": "every rate is reported beside the trade count it is computed over (policy V7 section 8)",
        "metrics": copy.deepcopy([dict(metric) for metric in _PRIMARY_METRICS]),
        "cross_venue_section": "policy V7 section 8 cross-venue source sensitivity (clarification 4a)",
        "cross_venue": [dict(measure) for measure in _CROSS_VENUE_MEASURES],
    }


def metric_definitions_bytes() -> bytes:
    return canonical_json_bytes(metric_definitions())


def metric_definitions_sha256() -> str:
    return sha256_hex(metric_definitions_bytes())


# --- the completeness-only pass (V6 section 5A.6) -----------------------------------------------


@dataclass(frozen=True)
class InstantCompleteness:
    """One decision instant's completeness: flags and codes, no value."""

    decision_at: datetime
    price_bar: bool
    components: tuple[tuple[str, bool], ...]
    core_regime: bool
    incomplete: tuple[UnevaluableComponent, ...]
    structure_without_valid_stop: bool
    unaccounted: tuple[str, ...]
    guard_refusals: tuple[str, ...]
    flow_calendar: tuple[date, date] | None

    @property
    def complete(self) -> bool:
        return self.core_regime and all(flag for _, flag in self.components)

    def as_record(self) -> dict[str, Any]:
        return {
            "decision_at": self.decision_at.isoformat(),
            "price_bar": self.price_bar,
            "components": {name: flag for name, flag in self.components},
            "core_regime": self.core_regime,
            "complete": self.complete,
            "incomplete": [item.as_record() for item in self.incomplete],
            "structure_without_valid_stop": self.structure_without_valid_stop,
            "unaccounted": list(self.unaccounted),
            "guard_refusals": list(self.guard_refusals),
            "flow_calendar": (
                {"earliest": self.flow_calendar[0].isoformat(), "latest": self.flow_calendar[1].isoformat()}
                if self.flow_calendar is not None
                else None
            ),
        }


class _CompletenessRun(ec._DecisionRun):
    """The RBT-004 decision run, stopped after the components and the core regime score."""

    def completeness(self) -> InstantCompleteness:
        hourly = self.c._visible_hourly(self.t)
        if not hourly or hourly[-1].ingested_at != self.t:
            # the composer's own attribution (review F5): one cause, on the decision instant
            self._cause("decision_instant", CAUSE_DECISION_PRICE_BAR_MISSING)
            return InstantCompleteness(
                decision_at=self.t,
                price_bar=False,
                components=tuple((name, False) for name in COMPONENT_NAMES),
                core_regime=False,
                incomplete=(UnevaluableComponent("decision_instant", (CAUSE_DECISION_PRICE_BAR_MISSING,)),),
                structure_without_valid_stop=False,
                unaccounted=self._unaccounted(),
                guard_refusals=(),
                flow_calendar=None,
            )
        self.price = hourly[-1].close
        canonical = replay_market_bars_at(hourly, decision_at=self.t, window=self.c._window)
        self.daily = tuple(bar for bar in canonical if bar.timeframe == "1d")
        self.weekly = tuple(bar for bar in canonical if bar.timeframe == "1w")
        self.monthly = tuple(bar for bar in canonical if bar.timeframe == "1mo")
        self.hourly = hourly

        trend = self._trend()
        flow = self._flow()
        positioning = self._positioning()
        volatility = self._volatility()
        regime = self._keep(
            "regime_score",
            ec.calculate_regime_score(
                ec.RegimeScoreInput(trend_score=trend, flow_score=flow, volatility_score=volatility, positioning_score=positioning),
                core_weights=dict(self.config.scoring_weights.core_regime),
                full_weights=dict(self.config.scoring_weights.full_regime),
                config_metadata=self.metadata,
            ),
        )
        geometry = self._geometry()
        structure = self._structure(geometry)
        components = dict(zip(COMPONENT_NAMES, (trend, flow, positioning, volatility, structure)))
        return InstantCompleteness(
            decision_at=self.t,
            price_bar=True,
            components=tuple((name, value is not None) for name, value in components.items()),
            core_regime=bool(regime.complete),
            incomplete=self._component_causes(components),
            structure_without_valid_stop=structure is None and geometry["no_stop_cause"] == "GEOMETRY",
            unaccounted=self._unaccounted(),
            guard_refusals=tuple(refusal.guard_id for refusal in self.guard_refusals),
            flow_calendar=(min(self.calendar), max(self.calendar)) if self.calendar else None,
        )


@dataclass(frozen=True)
class CompletenessReport:
    """One venue's completeness-only pass."""

    venue: str
    rows: tuple[InstantCompleteness, ...]

    @property
    def evaluation_start(self) -> datetime | None:
        return next((row.decision_at for row in self.rows if row.complete), None)

    @property
    def unaccounted(self) -> tuple[tuple[str, str], ...]:
        return tuple((row.decision_at.isoformat(), code) for row in self.rows for code in row.unaccounted)

    @property
    def closure_coverage_violations(self) -> tuple[str, ...]:
        return tuple(
            row.decision_at.isoformat()
            for row in self.rows
            if row.flow_calendar is not None
            and (row.flow_calendar[0] < CLOSURE_TABLE_COVERAGE_START or row.flow_calendar[1] > CLOSURE_TABLE_COVERAGE_END)
        )

    def ledger_bytes(self) -> bytes:
        return canonical_json_bytes(
            {
                "completeness_pass_version": COMPLETENESS_PASS_VERSION,
                "venue": self.venue,
                "rows": [row.as_record() for row in self.rows],
            }
        )

    def summary(self) -> dict[str, Any]:
        """Dates, counts of instants and codes: no value."""

        first_complete = {
            name: next((row.decision_at.isoformat() for row in self.rows if dict(row.components)[name]), None)
            for name in COMPONENT_NAMES
        }
        causes = Counter(
            f"{item.component}:{code}" for row in self.rows for item in row.incomplete for code in item.causes
        )
        start = self.evaluation_start
        return {
            "venue": self.venue,
            "instants": len(self.rows),
            "first_instant": self.rows[0].decision_at.isoformat() if self.rows else None,
            "last_instant": self.rows[-1].decision_at.isoformat() if self.rows else None,
            "evaluation_start": start.isoformat() if start is not None else None,
            "first_complete": {**first_complete, "core_regime": next((row.decision_at.isoformat() for row in self.rows if row.core_regime), None)},
            "incomplete_instants_after_start": (
                sum(1 for row in self.rows if start is not None and row.decision_at > start and not row.complete)
            ),
            "cause_instant_counts": dict(sorted(causes.items())),
            "unaccounted": [f"{at} {code}" for at, code in self.unaccounted],
            "closure_coverage_violations": list(self.closure_coverage_violations),
            "ledger_sha256": sha256_hex(self.ledger_bytes()),
        }


def completeness_pass(
    inputs: EntryComposerInputs,
    instants: Sequence[datetime],
    *,
    strategy_config: StrategyConfig | None = None,
) -> CompletenessReport:
    """Compose completeness only at each instant (ruling 2's schedule in Part B)."""

    config = strategy_config if strategy_config is not None else load_strategy_config()
    composer = EntryComposer(inputs, strategy_config=config)
    rows: list[InstantCompleteness] = []
    previous: datetime | None = None
    for instant in instants:
        if type(instant) is not datetime or instant.tzinfo is None or instant.utcoffset() != timedelta(0) or not is_daily_decision_instant(instant):
            raise _refuse("COMPLETENESS_REFUSED", f"{instant!r} is not a UTC daily decision instant")
        if previous is not None and instant <= previous:
            raise _refuse("COMPLETENESS_REFUSED", "decision instants must strictly increase")
        previous = instant
        rows.append(_CompletenessRun(composer, instant, position_open=False).completeness())
    return CompletenessReport(venue=composer.venue, rows=tuple(rows))


# --- the preregistration artifact ---------------------------------------------------------------


def _cost_ladder(config: StrategyConfig) -> dict[str, dict[str, str]]:
    backtest = config.backtest
    rungs = {
        "optimistic": backtest.cost_profiles.optimistic,
        "base": None,
        "stress": backtest.cost_profiles.stress,
    }
    ladder: dict[str, dict[str, str]] = {}
    for name, rung in rungs.items():
        source = backtest if rung is None else rung
        ladder[name] = {
            "fee_bps": str(source.fee_bps),
            "slippage_bps": str(source.slippage_bps),
            "funding_cost_bps_per_day": str(source.funding_cost_bps_per_day),
        }
    return ladder


def preregistration_record(
    *,
    code_commit: str,
    dataset_index: Mapping[str, Any],
    dataset_index_sha256: str,
    etf_launches: Sequence[EtfFundLaunch],
    completeness: Mapping[str, CompletenessReport],
    schedule: Sequence[datetime],
    strategy_config: StrategyConfig | None = None,
) -> dict[str, Any]:
    """The preregistration artifact; refused unless every freeze condition holds."""

    config = strategy_config if strategy_config is not None else load_strategy_config()
    if dict(config.run_metadata()) != dict(CHAMPION_BASE_IDENTITY):
        raise _refuse("FREEZE_REFUSED", "the freeze binds the champion's configuration")
    if type(code_commit) is not str or not _HEX40.fullmatch(code_commit):
        raise _refuse("FREEZE_REFUSED", "the code commit must be a full lowercase SHA-1 commit id")
    if type(dataset_index_sha256) is not str or not _HEX64.fullmatch(dataset_index_sha256):
        raise _refuse("FREEZE_REFUSED", "the dataset index must be named by its SHA-256")
    if dataset_index.get("evidence_class") != RESEARCH_EVIDENCE_CLASS:
        raise _refuse("FREEZE_REFUSED", "the dataset index is not research-backtest evidence")
    if not etf_launches:
        raise _refuse("FREEZE_REFUSED", "the freeze needs the ETF fund launch records")
    if not completeness:
        raise _refuse("FREEZE_REFUSED", "the freeze needs every venue's completeness pass")
    instants = tuple(schedule)
    venues: dict[str, Any] = {}
    for venue, report in sorted(completeness.items()):
        if report.venue != venue:
            raise _refuse("FREEZE_REFUSED", f"the {venue} pass is another venue's")
        if tuple(row.decision_at for row in report.rows) != instants:
            raise _refuse("FREEZE_REFUSED", f"the {venue} pass did not cover exactly the decision schedule")
        if report.unaccounted:
            raise _refuse("FREEZE_BLOCKED_UNACCOUNTED", f"{venue}: {len(report.unaccounted)} unaccounted incomplete results block the freeze")
        if report.closure_coverage_violations:
            raise _refuse("FREEZE_BLOCKED_CLOSURE_COVERAGE", f"{venue}: an ETF flow window falls outside the closure table's coverage")
        start = report.evaluation_start
        if start is None:
            raise _refuse("FREEZE_REFUSED", f"{venue}: no decision instant is complete")
        venues[venue] = {
            "completeness": report.summary(),
            "evaluation_window": {"start": start.isoformat(), "last_decision": instants[-1].isoformat()},
            "walk_forward": fold_plan(start, instants, strategy_config=config),
        }
    manifests = {name: {"manifest_version": entry["manifest_version"], "sha256": entry["sha256"]} for name, entry in dataset_index["manifests"].items()}
    return {
        "preregistration_version": PREREGISTRATION_VERSION,
        "ticket": PREREGISTRATION_TICKET,
        "evidence_class": RESEARCH_EVIDENCE_CLASS,
        "canonical_reference": CANONICAL_REFERENCE_UNRESOLVED,
        "policy": RESEARCH_BACKTEST_POLICY_V7,
        "code_commit": code_commit,
        "champion": {
            "research_strategy_id": RESEARCH_STRATEGY_ID,
            "base_identity": dict(CHAMPION_BASE_IDENTITY),
            "completion_spec": {"version": SPEC_VERSION, "sha256": COMPLETION_SPEC_SHA256},
        },
        "composers": {
            "entry": {"version": ENTRY_COMPOSER_VERSION, "ledger_version": LEDGER_VERSION},
            "management": {"version": MANAGEMENT_COMPOSER_VERSION, "ledger_version": MANAGEMENT_LEDGER_VERSION},
        },
        "closure_table": {
            "version": CLOSURE_TABLE_VERSION,
            "definition_sha256": CLOSURE_TABLE_SHA256,
            "coverage_start": CLOSURE_TABLE_COVERAGE_START.isoformat(),
            "coverage_end": CLOSURE_TABLE_COVERAGE_END.isoformat(),
        },
        "availability_policy": REPLAY_AVAILABILITY_POLICY_V2,
        "datasets": {
            "index_sha256": dataset_index_sha256,
            "build_record_sha256": dataset_index["build_record_sha256"],
            "private_commit": dataset_index["private_commit"],
            "manifests": dict(sorted(manifests.items())),
        },
        "cost_ladder": {"headline": HEADLINE_COST_RUNG, "rungs": _cost_ladder(config)},
        "decision_schedule": {
            "rule": "every UTC midnight strictly inside the data window",
            "first": instants[0].isoformat(),
            "last": instants[-1].isoformat(),
            "instants": len(instants),
        },
        "etf_fund_launches": launch_records(etf_launches),
        "venues": venues,
        "threshold_sweeps": {
            "factors": [str(factor) for factor in SWEEP_FACTORS],
            "objective": SWEEP_OBJECTIVE,
            "plateau_tolerance": str(SWEEP_PLATEAU_TOLERANCE),
            "cost_rung": SWEEP_COST_RUNG,
            "label": SENSITIVITY_ONLY,
            "sweeps": sweep_grid(config),
            "unread_paths": unread_sweep_paths(),
        },
        "ablation": ablation_variant(config),
        "report": {
            "report_version": REPORT_VERSION,
            "metric_spec_version": METRIC_SPEC_VERSION,
            "metric_spec_sha256": metric_definitions_sha256(),
            "metric_spec": metric_definitions(),
        },
    }


def preregistration_bytes(record: Mapping[str, Any]) -> bytes:
    return canonical_json_bytes(dict(record))


# --- the command line (Part B runs it) -----------------------------------------------------------

ARTIFACT_DIRECTORY = Path("backtest_evidence") / "research_backtest_v1"
PREREGISTRATION_FILE = "rbt006_preregistration_v1.json"
PREREGISTRATION_DIGEST_FILE = PREREGISTRATION_FILE + ".sha256"


def completeness_file(venue: str) -> str:
    return f"rbt006_completeness_{venue.lower()}_v1.json"


def _require_fresh_destinations(public_repository: Path, names: Sequence[str]) -> Path:
    """Every destination checked before anything is written (review F2): a real directory, no file there yet.

    A freeze is never overwritten, as the dataset build never overwrites a dataset.
    """

    directory = public_repository / ARTIFACT_DIRECTORY
    for part in (public_repository / Path(*ARTIFACT_DIRECTORY.parts[: index + 1]) for index in range(len(ARTIFACT_DIRECTORY.parts))):
        if part.is_symlink() or not part.is_dir():
            raise _refuse("FREEZE_DESTINATION_REFUSED", f"{part.relative_to(public_repository)} is not a real directory")
    for name in names:
        for path in (directory / name, directory / f"{name}.partial"):
            if path.is_symlink():
                raise _refuse("FREEZE_DESTINATION_REFUSED", f"{path.name} is a symbolic link")
        if (directory / name).exists():
            raise _refuse("FREEZE_EXISTS", f"{name} exists; a freeze is never overwritten")
    return directory


def freeze_from_store(
    store: Any,
    *,
    code_commit: str,
    evidence: Callable[[Any], Any] | None = None,
    run_pass: Callable[..., CompletenessReport] = completeness_pass,
    progress: Callable[[str], None] = lambda line: None,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    """The freeze from the private store's verified dataset: the record and every file to write.

    The dataset must be committed exactly as stored, rebuild to its stored
    manifests from its frozen inputs, and match the public index byte for byte.
    """

    from btc_predictor.research_backtest import dataset_build as build

    stored = build.load_dataset(store)
    private = build.private_commit(store, stored)
    index_bytes = (build.PUBLIC_REPOSITORY / build.INDEX_PATH).read_bytes()
    if index_bytes != build.dataset_index_bytes(stored, private_commit=private):
        raise _refuse("FREEZE_REFUSED", "the public index is not the stored dataset's index")
    loaded = (evidence or build.load_build_evidence)(store)
    rows = build.frozen_rows(stored)
    datasets = build.build_replay_datasets(rows, loaded)
    if datasets.manifests() != stored.manifests:
        raise _refuse("FREEZE_REFUSED", "the frozen inputs do not rebuild the stored manifests")
    launches = etf_fund_launches(rows["etf_flows"], evidence_sha256=stored.record["inputs"]["etf_flows"]["sha256"])
    schedule = decision_schedule()
    config = load_strategy_config()
    reports: dict[str, CompletenessReport] = {}
    files: dict[str, bytes] = {}
    for dataset in datasets.venues:
        venue = dataset.venue.venue_id
        progress(f"{venue}: completeness pass over {len(schedule)} instants")
        report = run_pass(datasets.extended.entry_composer_inputs(dataset, etf_fund_launches=launches), schedule, strategy_config=config)
        reports[report.venue] = report
        files[completeness_file(report.venue)] = report.ledger_bytes()
        summary = report.summary()
        progress(
            f"{venue}: evaluation start {summary['evaluation_start']}, unaccounted {len(summary['unaccounted'])}, "
            f"closure coverage violations {len(summary['closure_coverage_violations'])}"
        )
    record = preregistration_record(
        code_commit=code_commit,
        dataset_index=json.loads(index_bytes),
        dataset_index_sha256=sha256_hex(index_bytes),
        etf_launches=launches,
        completeness=reports,
        schedule=schedule,
        strategy_config=config,
    )
    artifact = preregistration_bytes(record)
    files[PREREGISTRATION_FILE] = artifact
    files[PREREGISTRATION_DIGEST_FILE] = f"{sha256_hex(artifact)}  {PREREGISTRATION_FILE}\n".encode()
    return record, files


def main(
    argv: Sequence[str] | None = None,
    *,
    commit: Callable[[], str] | None = None,
    evidence: Callable[[Any], Any] | None = None,
    run_pass: Callable[..., CompletenessReport] = completeness_pass,
    out: Callable[[str], None] = print,
) -> int:
    from btc_predictor.research_backtest import backfill_run as run
    from btc_predictor.research_backtest import dataset_build as build

    parser = argparse.ArgumentParser(prog="preregistration", description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("freeze",))
    parser.add_argument("--store", default="~/backtest_evidence", help="the private evidence repository (owner Part B ruling 9)")
    args = parser.parse_args(argv)
    try:
        code = (commit or build.code_commit)()
        artifacts = (PREREGISTRATION_DIGEST_FILE, PREREGISTRATION_FILE)
        _require_fresh_destinations(build.PUBLIC_REPOSITORY, artifacts)  # before the pass: an existing freeze refuses at once
        store = run.EvidenceStore(Path(args.store).expanduser(), public_repository=build.PUBLIC_REPOSITORY)
        record, files = freeze_from_store(store, code_commit=code, evidence=evidence, run_pass=run_pass, progress=out)
        ledgers = sorted(name for name in files if name not in artifacts)
        order = (*ledgers, *artifacts)  # the preregistration last
        if sorted(order) != sorted(files):  # unreachable: freeze_from_store writes both artifacts
            raise _refuse("FREEZE_REFUSED", "the freeze's files are not its ledgers and two artifacts")
        directory = _require_fresh_destinations(build.PUBLIC_REPOSITORY, order)
        for name in order:
            run._atomic_write(directory / name, files[name])
        for venue, item in sorted(record["venues"].items()):
            out(f"{venue}: evaluation start {item['evaluation_window']['start']}, folds {item['walk_forward']['fold_count']}")
        out(f"preregistration written: {ARTIFACT_DIRECTORY / PREREGISTRATION_FILE} sha256 {sha256_hex(files[PREREGISTRATION_FILE])} at code {code}")
        return 0
    except (PreregistrationRefused, build.DatasetBuildRefused, run.BackfillRefused, ReplayInputRefused, ec.EntryComposerError) as refused:
        code = getattr(refused, "reason_code", None) or getattr(refused, "code", type(refused).__name__)
        out(f"REFUSED {code}: {run.masked(str(refused))}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
