"""Static decision-path census for the RBT-002 input inventory (policy V4 section 5A).

The RBT-002 review (finding R1) found that a hand-selected owner registry cannot
prove that the section 5A enumeration is complete: it omitted consumed input
types (``AnchoredVwapAnchor``, ``OhlcvQualityConfig``,
``DerivativesQualityConfig``) and internal helper defaults
(``select_reward_reference.major_timeframes``). This module replaces that
registry with discovery.

- **Roots.** :data:`DECISION_PATH_ROOTS` is the only hand-written list: the
  owner entry points the RBT-004/RBT-005 composers call on the champion's
  decision path, each with the Rulebook area that puts it there.
- **Static closure.** :func:`discover_decision_path` walks ``btc_predictor``
  from the roots with ``inspect`` and the CPython bytecode and AST of each
  reached function. A node reaches every function, method and class it names
  (globals, closure cells, function-local imports, module/class attribute
  chains, dispatch tables and partials held in globals), every type in its
  parameter, return and local annotations, its default values, and, for a
  class, its bases, field types, field defaults and every method or property
  defined in its body. Names are resolved in the live module namespaces at
  call time, so an owner type or helper replaced in memory is the one
  discovered. Nothing below the roots is listed by hand.
- **Surface.** Every field of every reached dataclass or ``Protocol`` and every
  parameter (positional, keyword-only, defaulted) of every reached callable,
  except a method's receiver, is an input-bearing census item.
- **Call-site analysis.** For each defaulted parameter the AST call sites of
  every reached caller are read to decide whether any caller can override the
  default, so a default that no caller passes is reported as a fixed constant
  of the decision path.
- **Runtime cross-check.** :func:`trace_owner_calls` records, with
  ``sys.setprofile`` restricted to ``btc_predictor``, every function entered and
  every dataclass constructed while a thunk runs. The census tests require the
  static census to contain every traced item.

Correction R2 (policy V5 section 5A.1, 5A.5 and 5A.7):

- **Nested, local and private callables.** Every function, lambda, generator
  expression and class defined inside a reached callable's body is discovered
  from the live code object's nested code constants, paired with its node in
  the module source, and recorded with its qualified name, parameters,
  defaults and every call site inside the owner. Each one is classified
  ``OWNER_INTERNAL`` or ``EXTERNAL`` from that call-site AST, with the basis
  recorded (:func:`_classify_nested`).
- **No tracer exemption.** A traced frame is covered only by a static census
  callable with the same code identity and the same parameter names; a nested
  frame is no longer covered by its enclosing callable.
- **Stated limits.** :data:`CENSUS_LIMITS` records what the census cannot see
  and the measured line and branch coverage of the reached owner bodies.

Everything here is structural: no input is classified, no value is read and no
owner is modified.
"""

from __future__ import annotations

import ast
import builtins
import dataclasses
import dis
import functools
import importlib
import inspect
import linecache
import sys
import textwrap
import types
from collections import deque
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

import btc_predictor


CENSUS_VERSION = "DECISION_PATH_STATIC_CENSUS_V2"
PACKAGE = "btc_predictor"
# The census never walks its own tests or EPIC Y research code: neither is
# an owner on the champion's decision path.
OUT_OF_SCOPE_PREFIXES = ("btc_predictor.tests", "btc_predictor.research_backtest")
_PACKAGE_DIRECTORY = Path(btc_predictor.__file__).resolve().parent

# Decision-path owner modules: every function and class they define is either
# reached from a root or listed in LEFT_OUT_OWNER_DEFINITIONS with a reason.
DECISION_PATH_OWNER_PACKAGES = (
    "btc_predictor.features",
    "btc_predictor.levels",
    "btc_predictor.risk",
    "btc_predictor.signals",
)
DECISION_PATH_OWNER_MODULES = (
    "btc_predictor.data.quality",
    "btc_predictor.portfolio.state_machine",
)


class CensusError(ValueError):
    """The decision-path census cannot be built from the owner code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


# --- roots ------------------------------------------------------------------------

AREA_ENTRY_CONVICTION = "ENTRY_CONVICTION_AND_COMPONENTS"
AREA_CORE_REGIME = "CORE_REGIME_AND_SMOOTHING"
AREA_HARD_FLAGS = "RULEBOOK_24_HARD_FLAGS"
AREA_VETO_AND_QUALITY = "HARD_VETO_AND_DATA_QUALITY"
AREA_SETUP_AND_TRIGGER = "SETUP_DETECTION_AND_ENTRY_TRIGGER"
AREA_RISK_GEOMETRY = "INVALIDATION_BUFFER_STOP_AND_REWARD_RISK"
AREA_BUDGET_AND_SIZING = "RISK_BUDGET_SIZING_AND_RISK_AT_STOP"
AREA_LIFECYCLE = "LIFECYCLE_HOLD_ADD_TRANCHES_TRAIL_TRIM_EXIT"
AREA_LEVEL_PRODUCERS = "LEVEL_STRUCTURE_AND_ANCHORED_VWAP_PRODUCERS"
ROOT_AREAS = (
    AREA_ENTRY_CONVICTION,
    AREA_CORE_REGIME,
    AREA_HARD_FLAGS,
    AREA_VETO_AND_QUALITY,
    AREA_SETUP_AND_TRIGGER,
    AREA_RISK_GEOMETRY,
    AREA_BUDGET_AND_SIZING,
    AREA_LIFECYCLE,
    AREA_LEVEL_PRODUCERS,
)


@dataclass(frozen=True)
class DecisionPathRoot:
    """One owner entry point the champion's composer calls.

    The callable is named by module and qualified name and resolved at
    discovery time, so a root that is renamed or removed fails the census.
    """

    module: str
    qualname: str
    area: str
    justification: str

    def __post_init__(self) -> None:
        if self.area not in ROOT_AREAS:
            raise ValueError(f"unknown root area {self.area!r}")
        if not self.justification.strip():
            raise ValueError("every root needs a justification")

    @property
    def path(self) -> str:
        return f"{self.module}.{self.qualname}"

    def resolve(self) -> Any:
        try:
            owner: Any = importlib.import_module(self.module)
            for part in self.qualname.split("."):
                owner = getattr(owner, part)
        except (ImportError, AttributeError) as error:
            raise CensusError("ROOT_NOT_FOUND", f"{self.path}: {error}") from None
        if not isinstance(owner, types.FunctionType):
            raise CensusError("ROOT_NOT_A_FUNCTION", self.path)
        return owner

    def as_record(self) -> dict[str, str]:
        return {"root": self.path, "area": self.area, "justification": self.justification}


def _root(module: str, qualname: str, area: str, justification: str) -> DecisionPathRoot:
    return DecisionPathRoot(f"btc_predictor.{module}", qualname, area, justification)


# The only hand-written list. Each entry is an owner entry point the RBT-004
# (entry) or RBT-005 (position management) composer calls directly. Everything
# those entry points reach is discovered, not listed.
DECISION_PATH_ROOTS: tuple[DecisionPathRoot, ...] = (
    # Entry Conviction (Rulebook 13) and its five component scores (5-9). The
    # component owners and the producers that fill their input types are roots,
    # because the composer, not the score owner, calls those producers.
    _root("features.entry", "calculate_entry_conviction", AREA_ENTRY_CONVICTION,
          "Rulebook 13: the champion's Entry Conviction over the five component scores"),
    _root("features.entry", "classify_entry_action", AREA_ENTRY_CONVICTION,
          "Rulebook 13 interpretation bands: maps Entry Conviction to the entry action the composer acts on"),
    _root("features.trend", "calculate_trend_score", AREA_ENTRY_CONVICTION,
          "Rulebook 5.2 Trend composite (Entry Conviction trend component)"),
    _root("features.momentum", "four_week_momentum_from_daily_bars", AREA_ENTRY_CONVICTION,
          "Rulebook 5.1 4-week momentum: the raw quantity under TrendScoreInput.z_m4"),
    _root("features.momentum", "twelve_week_momentum_from_daily_bars", AREA_ENTRY_CONVICTION,
          "Rulebook 5.1 12-week momentum: the raw quantity under TrendScoreInput.z_m12"),
    _root("features.trend", "twenty_week_ma_distance_from_weekly_bars", AREA_ENTRY_CONVICTION,
          "Rulebook 5.1 distance from the 20-week MA: the raw quantity under TrendScoreInput.z_20w"),
    _root("features.trend", "fifty_two_week_high_distance_from_weekly_bars", AREA_ENTRY_CONVICTION,
          "Rulebook 5.1 distance from the 52-week high: the raw quantity under TrendScoreInput.z_52h"),
    _root("features.trend", "classify_weekly_structure_from_weekly_bars", AREA_ENTRY_CONVICTION,
          "Rulebook 5.1 weekly market structure: produces TrendScoreInput.structure_score"),
    _root("features.flow", "calculate_flow_score", AREA_ENTRY_CONVICTION,
          "Rulebook 6.2 Flow composite (Entry Conviction flow component, ETF_CORE fallback)"),
    _root("features.flow", "five_day_etf_flow", AREA_ENTRY_CONVICTION,
          "Rulebook 6.1 5-day ETF flow: the normalised flow under FlowScoreInput.etf_norm_5_zscore"),
    _root("features.flow", "twenty_day_etf_flow", AREA_ENTRY_CONVICTION,
          "Rulebook 6.1 20-day ETF flow: the normalised flow under FlowScoreInput.etf_norm_20_zscore"),
    _root("features.flow", "etf_flow_acceleration", AREA_ENTRY_CONVICTION,
          "Rulebook 6.1 flow acceleration: the quantity under FlowScoreInput.flow_accel_zscore"),
    _root("features.flow", "spot_perp_participation_from_rows", AREA_ENTRY_CONVICTION,
          "Rulebook 6.1 spot-vs-derivatives participation: the full-model flow input the composer evaluates before ETF_CORE applies"),
    _root("features.flow", "spot_perp_cvd_spread", AREA_ENTRY_CONVICTION,
          "Rulebook 6.1 spot-vs-perp CVD: the full-model flow input whose absence selects ETF_CORE"),
    _root("features.positioning", "calculate_positioning_score", AREA_ENTRY_CONVICTION,
          "Rulebook 7.5 Positioning composite (Entry Conviction positioning component)"),
    _root("features.positioning", "funding_health", AREA_ENTRY_CONVICTION,
          "Rulebook 7.1 funding health: produces PositioningScoreInput.funding_health and the funding z-score"),
    _root("features.positioning", "open_interest_growth_health", AREA_ENTRY_CONVICTION,
          "Rulebook 7.2 OI growth: produces PositioningScoreInput.oi_health"),
    _root("features.positioning", "open_interest_intensity", AREA_ENTRY_CONVICTION,
          "Rulebook 7.3 OI intensity: produces PositioningScoreInput.leverage_health and the OI-intensity percentile"),
    _root("features.positioning", "futures_basis_health", AREA_ENTRY_CONVICTION,
          "Rulebook 7.4 futures basis: produces PositioningScoreInput.basis_health and the basis z-score"),
    _root("features.volatility", "calculate_volatility_score", AREA_ENTRY_CONVICTION,
          "Rulebook 8 Volatility score (Entry Conviction volatility component)"),
    _root("features.volatility", "realized_volatility_from_daily_bars", AREA_ENTRY_CONVICTION,
          "Rulebook 8.1 realized volatility: RV7/RV60 and the volatility percentile history"),
    _root("features.volatility", "volatility_percentile", AREA_ENTRY_CONVICTION,
          "Rulebook 8.1 volatility percentile: feeds the score, orderliness and the hard flags"),
    _root("features.volatility", "volatility_compression_ratio_from_results", AREA_ENTRY_CONVICTION,
          "Rulebook 8.1 compression ratio: produces VolatilityScoreInput.compression_ratio"),
    _root("features.volatility", "calculate_orderliness_score", AREA_ENTRY_CONVICTION,
          "Rulebook 8.1 orderliness: produces VolatilityScoreInput.orderliness_score"),
    _root("features.structure", "calculate_structure_score_from_clusters", AREA_ENTRY_CONVICTION,
          "Rulebook 9.4 Structure composite over level clusters (Entry Conviction structure component)"),
    # Core regime score, smoothing and classification (Rulebook 10).
    _root("features.regime", "calculate_regime_score", AREA_CORE_REGIME,
          "Rulebook 10 core regime score (CORE_MARKET_ONLY fallback)"),
    _root("features.regime", "calculate_regime_smoothing", AREA_CORE_REGIME,
          "Rulebook 10 regime smoothing: the smoothed score every setup reads"),
    _root("features.regime", "calculate_regime_classification", AREA_CORE_REGIME,
          "Rulebook 10 regime classification of the smoothed score"),
    # Rulebook 24 hard flags.
    _root("features.volatility", "calculate_stress_flag", AREA_HARD_FLAGS, "Rulebook 24 STRESS"),
    _root("features.volatility", "calculate_capitulation_flag", AREA_HARD_FLAGS, "Rulebook 24 CAPITULATION"),
    _root("features.volatility", "calculate_euphoria_flag", AREA_HARD_FLAGS, "Rulebook 24 EUPHORIA"),
    _root("features.positioning", "calculate_crowding_flag", AREA_HARD_FLAGS, "Rulebook 24 CROWDING"),
    # Hard vetoes (Rulebook 14) and DATA_QUALITY_FAIL (Rulebook 24).
    _root("signals.hard_veto", "evaluate_hard_veto", AREA_VETO_AND_QUALITY, "Rulebook 14 hard vetoes for a new trade"),
    _root("data.quality", "validate_ohlcv_quality", AREA_VETO_AND_QUALITY,
          "Rulebook 24 DATA_QUALITY_FAIL: the BTC-031 OHLCV quality report over the visible prefix"),
    _root("data.quality", "validate_derivatives_quality", AREA_VETO_AND_QUALITY,
          "Rulebook 24 DATA_QUALITY_FAIL: the BTC-031 derivatives quality report over the visible prefix"),
    _root("signals.data_quality", "failures_from_quality_reports", AREA_VETO_AND_QUALITY,
          "Rulebook 24 DATA_QUALITY_FAIL: maps quality reports to the veto's data_quality_fail"),
    _root("signals.data_quality", "apply_data_quality_gate", AREA_VETO_AND_QUALITY,
          "Rulebook 24 DATA_QUALITY_FAIL gate: blocks ENTER and ADD"),
    # Setup detection (Rulebook 11), entry triggers (12) and no-chase (25).
    _root("features.setup", "detect_bull_trend_continuation", AREA_SETUP_AND_TRIGGER, "Rulebook 11 Setup A"),
    _root("features.setup", "detect_bullish_reset", AREA_SETUP_AND_TRIGGER, "Rulebook 11 Setup B"),
    _root("features.setup", "detect_capitulation_reversal", AREA_SETUP_AND_TRIGGER, "Rulebook 11 Setup C"),
    _root("features.setup", "detect_bearish_distribution", AREA_SETUP_AND_TRIGGER,
          "Rulebook 11 Setup D (inert while backtest.allow_short_trades = false, but on the detector path)"),
    _root("signals.reclaim", "evaluate_reclaim_trigger", AREA_SETUP_AND_TRIGGER, "Rulebook 12.1 reclaim trigger"),
    _root("signals.breakout_retest", "evaluate_breakout_retest_trigger", AREA_SETUP_AND_TRIGGER,
          "Rulebook 12.2 breakout-and-retest trigger"),
    _root("signals.higher_low", "evaluate_higher_low_trigger", AREA_SETUP_AND_TRIGGER,
          "Rulebook 12.3 higher-low confirmation trigger"),
    _root("signals.no_chase", "apply_no_chase_filter", AREA_SETUP_AND_TRIGGER, "Rulebook 25 no-chase rule"),
    # Invalidation, buffer and initial stop (Rulebook 16) and the R/R filter
    # (15). Reward-reference selection is reached inside reward_risk_for_stop.
    _root("risk.invalidation", "select_structural_invalidation", AREA_RISK_GEOMETRY, "Rulebook 16.1 structural invalidation"),
    _root("risk.buffer", "atr_from_daily_bars", AREA_RISK_GEOMETRY,
          "Rulebook 16.1 ATR for the volatility buffer, clustering and trigger distances"),
    _root("risk.buffer", "volatility_buffer_for_invalidation", AREA_RISK_GEOMETRY, "Rulebook 16.1 volatility buffer"),
    _root("risk.stop", "initial_stop_for_setup", AREA_RISK_GEOMETRY, "Rulebook 16.1 initial structural stop"),
    _root("risk.reward", "reward_risk_for_stop", AREA_RISK_GEOMETRY,
          "Rulebook 15 R/R filter, including the reward-reference selection it performs"),
    # Risk budget and sizing (Rulebook 17) and risk at stop (19).
    _root("risk.budget", "calculate_risk_budget", AREA_BUDGET_AND_SIZING, "Rulebook 17 conviction risk budget"),
    _root("risk.sizing", "initial_position_size_for_trade", AREA_BUDGET_AND_SIZING, "Rulebook 17 initial position size"),
    _root("risk.exposure", "calculate_risk_at_stop", AREA_BUDGET_AND_SIZING, "Rulebook 19 risk-at-stop constraint"),
    # Lifecycle state machine (Rulebook 26), hold (20), add (18, 21),
    # tranches (18), trailing (22), trim (23) and exit (26, 31).
    _root("portfolio.state_machine", "start_position_lifecycle", AREA_LIFECYCLE,
          "Rulebook 26 trade lifecycle: the composer opens the BTC-150 lifecycle every lifecycle owner reads"),
    _root("portfolio.state_machine", "apply_position_event", AREA_LIFECYCLE,
          "Rulebook 26 trade lifecycle: every entry, add, trim, stop and exit transition"),
    _root("features.hold", "calculate_hold_score", AREA_LIFECYCLE, "Rulebook 20 Hold Score"),
    _root("features.add", "calculate_add_score", AREA_LIFECYCLE, "Rulebook 21 Add Score"),
    _root("features.add", "risk_improvement_component_score", AREA_LIFECYCLE, "Rulebook 21 risk-improvement component"),
    _root("signals.add_requirements", "add_requirements_from_results", AREA_LIFECYCLE, "Rulebook 18.1 add requirements"),
    _root("risk.tranches", "next_tranche_for_position", AREA_LIFECYCLE, "Rulebook 18 add tranches"),
    _root("risk.trailing", "trail_stop_for_position", AREA_LIFECYCLE, "Rulebook 22 trailing stop"),
    _root("risk.trailing", "apply_trailing_stop", AREA_LIFECYCLE,
          "Rulebook 22/26: the trailing owner's only lifecycle write; the BTC-180 engine records an advanced trail through it"),
    _root("signals.trim", "trim_rules_from_results", AREA_LIFECYCLE, "Rulebook 23 trim rules"),
    _root("signals.exit_rules", "exit_rules_for_position", AREA_LIFECYCLE, "Rulebook 26/31 exit rules"),
    # Level, structure and anchored-VWAP producers (Rulebook 9.1-9.2) the
    # structure score, invalidation, triggers and R/R consume.
    _root("levels.swing", "detect_weekly_swing_levels", AREA_LEVEL_PRODUCERS, "Rulebook 9.1 weekly swing highs/lows"),
    _root("levels.swing", "detect_monthly_swing_levels", AREA_LEVEL_PRODUCERS, "Rulebook 9.1 monthly swing highs/lows"),
    _root("levels.breakout", "detect_breakout_reclaim_levels", AREA_LEVEL_PRODUCERS, "Rulebook 9.1 major breakout/reclaim levels"),
    _root("levels.volume_profile", "calculate_volume_profile_levels", AREA_LEVEL_PRODUCERS,
          "Rulebook 9.1 volume-profile HVN, value area and point of control"),
    _root("levels.anchored_vwap", "anchored_vwap_anchor_from_swing_level", AREA_LEVEL_PRODUCERS,
          "Rulebook 9.1 AVWAP anchored at a major swing level"),
    _root("levels.anchored_vwap", "anchored_vwap_anchor_from_breakout_level", AREA_LEVEL_PRODUCERS,
          "Rulebook 9.1 AVWAP anchored at a breakout level"),
    _root("levels.anchored_vwap", "anchored_vwap_anchor_from_capitulation_event", AREA_LEVEL_PRODUCERS,
          "Rulebook 9.1 'Anchored VWAPs from important market events': the owner's only event anchor"),
    _root("levels.anchored_vwap", "calculate_anchored_vwaps", AREA_LEVEL_PRODUCERS, "Rulebook 9.1 anchored VWAP levels"),
    _root("levels.clustering", "cluster_price_levels", AREA_LEVEL_PRODUCERS, "Rulebook 9.2 support/resistance clusters"),
    _root("levels.strength", "calculate_level_strength_from_cluster", AREA_LEVEL_PRODUCERS, "Rulebook 9.2 level strength"),
)


# --- census records ----------------------------------------------------------------

ROOT_PARENT = "ROOT"
REF_ROOT = "ROOT"
REF_CODE = "CODE"
REF_LOCAL_IMPORT = "LOCAL_IMPORT"
REF_ANNOTATION = "ANNOTATION"
REF_DEFAULT = "DEFAULT"
REF_MEMBER = "CLASS_MEMBER"
REF_BASE = "BASE_CLASS"
REF_FIELD = "FIELD_TYPE_OR_DEFAULT"
REF_NESTED = "NESTED_DEFINITION"
REFERENCE_KINDS = (
    REF_ROOT, REF_CODE, REF_LOCAL_IMPORT, REF_ANNOTATION, REF_DEFAULT, REF_MEMBER, REF_BASE, REF_FIELD, REF_NESTED,
)

ROLE_FUNCTION = "FUNCTION"
ROLE_METHOD = "METHOD"
ROLE_STATICMETHOD = "STATICMETHOD"
ROLE_CLASSMETHOD = "CLASSMETHOD"
ROLE_PROPERTY = "PROPERTY"
_RECEIVER_ROLES = (ROLE_METHOD, ROLE_CLASSMETHOD, ROLE_PROPERTY)
# Callables defined inside a reached callable's body (correction R2).
ROLE_NESTED_FUNCTION = "NESTED_FUNCTION"
ROLE_LAMBDA = "LAMBDA"
ROLE_GENERATOR_EXPRESSION = "GENERATOR_EXPRESSION"
ROLE_LOCAL_CLASS = "LOCAL_CLASS"
NESTED_ROLES = (ROLE_NESTED_FUNCTION, ROLE_LAMBDA, ROLE_GENERATOR_EXPRESSION, ROLE_LOCAL_CLASS)

# Policy V5 section 5A.1: a nested callable is owner-internal when every call
# site inside the owner supplies only owner-computed values or literals;
# otherwise it is part of the external input surface.
NESTED_OWNER_INTERNAL = "OWNER_INTERNAL"
NESTED_EXTERNAL = "EXTERNAL"
NESTED_CLASSIFICATIONS = (NESTED_OWNER_INTERNAL, NESTED_EXTERNAL)
BASIS_DIRECT_CALLS = "EVERY_CALL_SITE_IS_A_DIRECT_CALL_PASSING_LITERALS_OR_ENCLOSING_SCOPE_NAMES"
BASIS_BUILTIN_KEY = "KEY_FUNCTION_OF_BUILTIN_SORTED_MIN_OR_MAX_OVER_ENCLOSING_SCOPE_VALUES"
BASIS_GENERATOR = "GENERATOR_EXPRESSION_ITERATOR_BOUND_IN_THE_ENCLOSING_SCOPE"
BASIS_NEVER_CALLED = "NEVER_REFERENCED_IN_THE_ENCLOSING_SCOPE"
BASIS_ESCAPES = "ESCAPES_THE_ENCLOSING_SCOPE_AS_A_VALUE"
BASIS_COMPUTED_ARGUMENT = "A_CALL_SITE_PASSES_A_COMPUTED_EXPRESSION"
BASIS_UNPACKED_ARGUMENT = "A_CALL_SITE_UNPACKS_ARGUMENTS"
BASIS_DECORATED = "DECORATED_LOCAL_FUNCTION"
BASIS_REBOUND = "LOCAL_NAME_REBOUND_IN_THE_ENCLOSING_SCOPE"
BASIS_LOCAL_CLASS = "LOCAL_CLASS_OR_ITS_MEMBER"
BASIS_LIVE_CODE_DIFFERS = "LIVE_CODE_DIFFERS_FROM_ITS_SOURCE"
OWNER_INTERNAL_BASES = (BASIS_DIRECT_CALLS, BASIS_BUILTIN_KEY, BASIS_GENERATOR, BASIS_NEVER_CALLED)

FORM_DIRECT_CALL = "DIRECT_CALL"
FORM_BUILTIN_KEY = "BUILTIN_KEY_CALLBACK"
FORM_GENERATOR = "GENERATOR_EXPRESSION"
ARGUMENT_LITERAL = "LITERAL"
ARGUMENT_SCOPE_NAME = "ENCLOSING_SCOPE_NAME"
ARGUMENT_SCOPE_EXPRESSION = "EVALUATED_IN_THE_ENCLOSING_SCOPE"
ARGUMENT_COMPUTED = "COMPUTED_EXPRESSION"
ARGUMENT_UNPACKED = "UNPACKED"
_KEY_BUILTINS = frozenset({"sorted", "min", "max"})

TYPE_DATACLASS = "DATACLASS"
TYPE_PROTOCOL = "PROTOCOL"
TYPE_CLASS = "CLASS"

DEFAULT_COMPOSER_SUPPLIED = "ROOT_PARAMETER_SUPPLIED_BY_THE_COMPOSER"
DEFAULT_FIXED = "NO_REACHED_CALLER_OVERRIDES_THE_DEFAULT"
DEFAULT_OVERRIDDEN = "A_REACHED_CALLER_PASSES_THIS_ARGUMENT"
DEFAULT_UNRESOLVED = "A_CALLER_IS_NOT_A_RESOLVED_DIRECT_CALL"


@dataclass(frozen=True)
class CensusParameter:
    name: str
    kind: str
    position: int | None
    has_default: bool
    default: str | None

    def as_record(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "position": self.position,
            "has_default": self.has_default,
            "default": self.default,
        }


@dataclass(frozen=True)
class CensusCallable:
    path: str
    role: str
    reached_from: str
    reached_by: str
    source: str
    parameters: tuple[CensusParameter, ...]

    @property
    def parameter_names(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.parameters)

    def as_record(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "role": self.role,
            "reached_from": self.reached_from,
            "reached_by": self.reached_by,
            "source": self.source,
            "parameters": [item.as_record() for item in self.parameters],
        }


@dataclass(frozen=True)
class CensusType:
    path: str
    kind: str
    reached_from: str
    reached_by: str
    source: str
    fields: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "kind": self.kind,
            "reached_from": self.reached_from,
            "reached_by": self.reached_by,
            "source": self.source,
            "fields": list(self.fields),
        }


@dataclass(frozen=True)
class CallSite:
    """One resolved direct call, in a reached function, to a census node."""

    caller: str
    callee: str
    positional: int
    keywords: tuple[str, ...]
    star_args: bool
    star_kwargs: bool


@dataclass(frozen=True)
class NestedArgument:
    """One value a call site inside the owner supplies to a nested callable."""

    slot: str
    expression: str
    basis: str

    def as_record(self) -> dict[str, str]:
        return {"slot": self.slot, "expression": self.expression, "basis": self.basis}


@dataclass(frozen=True)
class NestedCallSite:
    """Where the owner supplies a nested callable's parameters.

    A direct call names the callable; a builtin ``sorted``/``min``/``max``
    applies a ``key=`` lambda to the values the owner passes it; a generator
    expression receives the iterator of its first ``for`` clause.
    """

    form: str
    line: int
    callee: str
    arguments: tuple[NestedArgument, ...]

    def as_record(self) -> dict[str, Any]:
        return {
            "form": self.form,
            "line": self.line,
            "callee": self.callee,
            "arguments": [item.as_record() for item in self.arguments],
        }


@dataclass(frozen=True)
class NestedCallable:
    """A callable defined inside a reached callable's body, and its classification.

    ``module``, ``qualname`` (the code object's ``co_qualname``), ``source``
    and ``column`` identify the code object, so the tracer can match an
    executed nested frame exactly. Its parameters are the census callable
    record under the same path.
    """

    path: str
    module: str
    qualname: str
    role: str
    enclosing: str
    source: str
    column: int
    classification: str
    basis: str
    call_sites: tuple[NestedCallSite, ...]

    @property
    def code_key(self) -> tuple[str, str, str, int]:
        return (self.module, self.qualname, self.source, self.column)

    def as_record(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "qualname": self.qualname,
            "role": self.role,
            "enclosing": self.enclosing,
            "source": self.source,
            "column": self.column,
            "classification": self.classification,
            "basis": self.basis,
            "call_sites": [site.as_record() for site in self.call_sites],
        }


@dataclass(frozen=True)
class DecisionPathCensus:
    """The static closure from the roots. Paths are ``module.qualname``.

    ``callables`` holds every reached callable, including the nested ones;
    ``nested`` adds, for those, their enclosing owner, call sites and
    ``OWNER_INTERNAL``/``EXTERNAL`` classification.
    """

    roots: tuple[DecisionPathRoot, ...]
    callables: Mapping[str, CensusCallable]
    types: Mapping[str, CensusType]
    references: Mapping[str, tuple[tuple[str, str], ...]]
    call_sites: tuple[CallSite, ...]
    sourceless: tuple[str, ...]
    nested: Mapping[str, NestedCallable] = field(default_factory=dict)

    @property
    def root_paths(self) -> tuple[str, ...]:
        return tuple(root.path for root in self.roots)

    @functools.cached_property
    def nested_by_code(self) -> Mapping[tuple[str, str, str, int], tuple[str, ...]]:
        """Nested census paths by code identity (module, co_qualname, source, column)."""

        grouped: dict[tuple[str, str, str, int], list[str]] = {}
        for path, record in self.nested.items():
            grouped.setdefault(record.code_key, []).append(path)
        return {key: tuple(sorted(value)) for key, value in grouped.items()}

    @functools.cached_property
    def callers(self) -> Mapping[str, tuple[str, ...]]:
        """For each node, the reached callables whose bodies name or define it."""

        callers: dict[str, set[str]] = {}
        for source, targets in self.references.items():
            if source not in self.callables:
                continue
            for kind, target in targets:
                if kind in (REF_CODE, REF_LOCAL_IMPORT, REF_NESTED):
                    callers.setdefault(target, set()).add(source)
        return {key: tuple(sorted(value)) for key, value in sorted(callers.items())}

    @functools.cached_property
    def reaching_roots(self) -> Mapping[str, tuple[str, ...]]:
        """For each node, the roots whose own closure reaches it."""

        reached: dict[str, set[str]] = {}
        for root in self.root_paths:
            seen = {root}
            queue = deque([root])
            while queue:
                current = queue.popleft()
                reached.setdefault(current, set()).add(root)
                for _, target in self.references.get(current, ()):
                    if target not in seen:
                        seen.add(target)
                        queue.append(target)
        return {key: tuple(sorted(value)) for key, value in sorted(reached.items())}

    @functools.cached_property
    def _sites_by_callee(self) -> Mapping[str, tuple[CallSite, ...]]:
        grouped: dict[str, list[CallSite]] = {}
        for site in self.call_sites:
            grouped.setdefault(site.callee, []).append(site)
        return {key: tuple(value) for key, value in grouped.items()}

    def default_override(self, path: str, parameter: str) -> tuple[str, tuple[str, ...]]:
        """Whether any reached caller can override ``parameter``'s default.

        Returns the verdict and the callers that pass or may pass it.
        """

        if path in self.root_paths:
            return DEFAULT_COMPOSER_SUPPLIED, ()
        record = self.callables[path]
        item = next(entry for entry in record.parameters if entry.name == parameter)
        if not item.has_default:
            raise CensusError("NO_DEFAULT", f"{path}.{parameter} has no default")
        sites = self._sites_by_callee.get(path, ())
        sited = {site.caller for site in sites}
        unresolved = sorted(
            source
            for source, targets in self.references.items()
            if any(target == path and kind not in (REF_ANNOTATION,) for kind, target in targets)
            and source not in sited
        )
        nested = self.nested.get(path)
        if nested is not None and nested.basis not in (BASIS_DIRECT_CALLS, BASIS_NEVER_CALLED):
            # Called back by a builtin, escaping or unverifiable: a direct call
            # site does not show every argument this callable receives.
            unresolved = sorted({*unresolved, nested.enclosing})
        overriding = sorted(
            {
                site.caller
                for site in sites
                if parameter in site.keywords
                or (item.position is not None and item.position < site.positional)
            }
        )
        starred = sorted({site.caller for site in sites if site.star_args or site.star_kwargs})
        if overriding:
            return DEFAULT_OVERRIDDEN, tuple(overriding)
        if unresolved or starred:
            return DEFAULT_UNRESOLVED, tuple(sorted({*unresolved, *starred}))
        return DEFAULT_FIXED, ()

    def summary(self) -> dict[str, Any]:
        dataclass_types = [item for item in self.types.values() if item.kind == TYPE_DATACLASS]
        protocol_types = [item for item in self.types.values() if item.kind == TYPE_PROTOCOL]
        named = [item for path, item in self.callables.items() if path not in self.nested]
        nested = list(self.nested.values())

        def count(values: Iterator[str]) -> dict[str, int]:
            counts: dict[str, int] = {}
            for value in values:
                counts[value] = counts.get(value, 0) + 1
            return dict(sorted(counts.items()))

        return {
            "census_version": CENSUS_VERSION,
            "roots": len(self.roots),
            "callables": len(named),
            "nested_callables": len(nested),
            "nested_callables_by_role": count(item.role for item in nested),
            "nested_callables_by_classification": count(item.classification for item in nested),
            "nested_callables_by_basis": count(item.basis for item in nested),
            "types": len(self.types),
            "dataclass_types": len(dataclass_types),
            "protocol_types": len(protocol_types),
            "other_classes": len(self.types) - len(dataclass_types) - len(protocol_types),
            "fields": sum(len(item.fields) for item in self.types.values()),
            "parameters": sum(len(item.parameters) for item in named),
            "nested_parameters": sum(len(self.callables[item.path].parameters) for item in nested),
            "resolved_call_sites": len(self.call_sites),
            "nested_call_sites": sum(len(item.call_sites) for item in nested),
            "callables_without_source": list(self.sourceless),
        }


# --- static discovery ------------------------------------------------------------------


def in_scope_module(name: Any) -> bool:
    return (
        isinstance(name, str)
        and (name == PACKAGE or name.startswith(PACKAGE + "."))
        and not any(name == prefix or name.startswith(prefix + ".") for prefix in OUT_OF_SCOPE_PREFIXES)
    )


@functools.lru_cache(maxsize=None)
def _is_package_source(filename: str) -> bool:
    if not filename.endswith(".py"):
        return False
    try:
        Path(filename).resolve().relative_to(_PACKAGE_DIRECTORY)
    except ValueError:
        return False
    return True


def owner_path(obj: Any) -> str:
    return f"{obj.__module__}.{obj.__qualname__}"


def _source_location(obj: Any) -> str:
    code = getattr(obj, "__code__", None)
    if code is not None:
        filename, line = code.co_filename, code.co_firstlineno
    else:
        try:
            filename = inspect.getsourcefile(obj) or ""
            line = inspect.getsourcelines(obj)[1]
        except (OSError, TypeError):
            return "unavailable"
    try:
        relative = Path(filename).resolve().relative_to(_PACKAGE_DIRECTORY.parent)
    except ValueError:
        relative = Path(filename).name
    return f"{relative.as_posix()}:{line}"


def _unwrap(obj: Any) -> Any:
    if isinstance(obj, (staticmethod, classmethod)):
        obj = obj.__func__
    if not isinstance(obj, types.FunctionType) and callable(obj) and hasattr(obj, "__wrapped__"):
        try:
            unwrapped = inspect.unwrap(obj)
        except ValueError:
            return obj
        if isinstance(unwrapped, types.FunctionType):
            return unwrapped
    if isinstance(obj, types.MethodType):
        return obj.__func__
    return obj


_DATACLASS_GENERATED_METHODS = frozenset(
    {
        "__init__", "__repr__", "__eq__", "__hash__", "__setattr__", "__delattr__", "__getstate__",
        "__setstate__", "__lt__", "__le__", "__gt__", "__ge__", "__replace__",
    }
)


def _is_generated_method(function: types.FunctionType) -> bool:
    """A dataclass-generated method (``exec``-compiled, possibly reprlib-wrapped)."""

    inner = inspect.unwrap(function) if hasattr(function, "__wrapped__") else function
    return inner.__code__.co_filename.startswith("<") and inner.__name__ in _DATACLASS_GENERATED_METHODS


def _is_source_function(obj: Any) -> bool:
    return (
        isinstance(obj, types.FunctionType)
        and in_scope_module(obj.__module__)
        and _is_package_source(obj.__code__.co_filename)
    )


def _is_scope_class(obj: Any) -> bool:
    return isinstance(obj, type) and in_scope_module(obj.__module__)


def _is_protocol(cls: type) -> bool:
    return bool(getattr(cls, "_is_protocol", False))


def _node_candidates(value: Any, *, depth: int = 0, seen: set[int] | None = None) -> list[Any]:
    """Census nodes (source functions, scope classes) named by one value."""

    seen = set() if seen is None else seen
    if id(value) in seen or depth > 6:
        return []
    seen.add(id(value))
    out: list[Any] = []
    if isinstance(value, property):
        for accessor in (value.fget, value.fset, value.fdel):
            if accessor is not None:
                out.extend(_node_candidates(accessor, depth=depth + 1, seen=seen))
        return out
    value = _unwrap(value)
    if isinstance(value, functools.partial):
        out.extend(_node_candidates(value.func, depth=depth + 1, seen=seen))
        for item in (*value.args, *value.keywords.values()):
            out.extend(_node_candidates(item, depth=depth + 1, seen=seen))
        return out
    if isinstance(value, types.FunctionType):
        if not in_scope_module(value.__module__):
            return []
        if _is_package_source(value.__code__.co_filename):
            return [value]
        if _is_generated_method(value):
            return []
        raise CensusError(
            "FOREIGN_OWNER_CODE",
            f"{owner_path(value)} is bound to code defined outside btc_predictor ({value.__code__.co_filename})",
        )
    if isinstance(value, type):
        return [value] if _is_scope_class(value) else []
    if isinstance(value, (types.ModuleType, str, bytes, int, float, bool, Decimal, datetime, date, time, timedelta)) or value is None:
        return []
    if isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            out.extend(_node_candidates(item, depth=depth + 1, seen=seen))
        return out
    if isinstance(value, (dict, types.MappingProxyType)):
        for key, item in value.items():
            out.extend(_node_candidates(key, depth=depth + 1, seen=seen))
            out.extend(_node_candidates(item, depth=depth + 1, seen=seen))
        return out
    if isinstance(value, Enum) or (dataclasses.is_dataclass(value) and not isinstance(value, type)):
        return _node_candidates(type(value), depth=depth + 1, seen=seen)
    if _is_scope_class(type(value)):
        return [type(value)]
    return []


def _code_objects(code: types.CodeType) -> Iterator[types.CodeType]:
    yield code
    for constant in code.co_consts:
        if isinstance(constant, types.CodeType):
            yield from _code_objects(constant)


_MISSING = object()


def _getattr(owner: Any, name: str) -> Any:
    if isinstance(owner, types.ModuleType):
        found = getattr(owner, name, _MISSING)
        if found is _MISSING:
            try:
                return importlib.import_module(f"{owner.__name__}.{name}")
            except ImportError:
                return _MISSING
        return found
    try:
        return inspect.getattr_static(owner, name)
    except AttributeError:
        return _MISSING


def _closure_values(function: types.FunctionType) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for name, cell in zip(function.__code__.co_freevars, function.__closure__ or ()):
        try:
            values[name] = cell.cell_contents
        except ValueError:
            continue
    return values


def _absolute_module(name: str, level: int, package: str) -> str:
    if not level:
        return name
    base = package.rsplit(".", level - 1)[0] if level > 1 else package
    return f"{base}.{name}" if name else base


_LOAD_FAST = ("LOAD_FAST", "LOAD_FAST_CHECK", "LOAD_FAST_AND_CLEAR")
_STORE_LOCAL = ("STORE_FAST", "STORE_NAME", "STORE_DEREF", "STORE_GLOBAL")


def _bytecode_references(function: types.FunctionType) -> list[tuple[str, Any]]:
    """Objects a function body names, resolved from its live namespaces."""

    namespace = function.__globals__
    closure = _closure_values(function)
    package = function.__module__.rsplit(".", 1)[0]
    references: list[tuple[str, Any]] = []
    for code in _code_objects(function.__code__):
        chain: Any = _MISSING
        imported: Any = _MISSING
        pending: Any = _MISSING
        local: dict[str, Any] = {}
        previous_consts: list[Any] = []
        for instruction in dis.get_instructions(code):
            op = instruction.opname
            if op == "LOAD_CONST":
                previous_consts = [*previous_consts[-1:], instruction.argval]
                continue
            if op == "LOAD_GLOBAL":
                chain = namespace.get(instruction.argval, _MISSING)
                if chain is not _MISSING:
                    references.append((REF_CODE, chain))
            elif op == "LOAD_DEREF" and instruction.argval in closure:
                chain = closure[instruction.argval]
                references.append((REF_CODE, chain))
            elif op in _LOAD_FAST and instruction.argval in local:
                chain = local[instruction.argval]
                references.append((REF_LOCAL_IMPORT, chain))
            elif op in ("LOAD_ATTR", "LOAD_METHOD") and chain is not _MISSING:
                chain = _getattr(chain, instruction.argval)
                if chain is not _MISSING:
                    references.append((REF_CODE, chain))
            elif op == "IMPORT_NAME":
                level = previous_consts[0] if len(previous_consts) == 2 and isinstance(previous_consts[0], int) else 0
                fromlist = previous_consts[-1] if previous_consts else None
                name = _absolute_module(instruction.argval, level, package)
                try:
                    module = importlib.import_module(name)
                except ImportError:
                    imported = pending = _MISSING
                else:
                    imported = module
                    pending = module if fromlist else sys.modules.get(name.split(".")[0], module)
                chain = _MISSING
            elif op == "IMPORT_FROM" and imported is not _MISSING:
                pending = _getattr(imported, instruction.argval)
                if pending is not _MISSING:
                    references.append((REF_LOCAL_IMPORT, pending))
                chain = _MISSING
            elif op in _STORE_LOCAL and pending is not _MISSING:
                local[instruction.argval] = pending
                pending = _MISSING
                chain = _MISSING
            elif op == "POP_TOP":
                imported = pending = chain = _MISSING
            else:
                chain = _MISSING
            previous_consts = []
    return references


def _annotation_objects(annotation: Any, namespace: Mapping[str, Any]) -> list[Any]:
    if annotation is None or annotation is inspect.Parameter.empty:
        return []
    if isinstance(annotation, str):
        try:
            tree = ast.parse(annotation, mode="eval")
        except SyntaxError:
            return []
        return _expression_objects(tree.body, namespace)
    found: list[Any] = []
    stack = [annotation]
    while stack:
        current = stack.pop()
        if isinstance(current, type):
            found.append(current)
        elif isinstance(current, str):
            found.extend(_annotation_objects(current, namespace))
        stack.extend(getattr(current, "__args__", ()) or ())
    return found


def _resolve_expression(node: ast.AST, namespace: Mapping[str, Any]) -> Any:
    if isinstance(node, ast.Name):
        return namespace.get(node.id, _MISSING)
    if isinstance(node, ast.Attribute):
        owner = _resolve_expression(node.value, namespace)
        return _MISSING if owner is _MISSING else _getattr(owner, node.attr)
    return _MISSING


def _expression_objects(node: ast.AST, namespace: Mapping[str, Any]) -> list[Any]:
    import typing

    found: list[Any] = []
    stack = [node]
    while stack:
        current = stack.pop()
        if isinstance(current, (ast.Name, ast.Attribute)):
            value = _resolve_expression(current, namespace)
            if value is not _MISSING:
                found.append(value)
            if isinstance(current, ast.Attribute):
                stack.append(current.value)
            continue
        if isinstance(current, ast.Subscript) and _resolve_expression(current.value, namespace) is typing.Literal:
            continue
        if isinstance(current, ast.Constant) and isinstance(current.value, str):
            found.extend(_annotation_objects(current.value, namespace))
            continue
        stack.extend(ast.iter_child_nodes(current))
    return found


@functools.lru_cache(maxsize=4096)
def _parsed_source(function: types.FunctionType) -> ast.AST | None:
    try:
        return ast.parse(textwrap.dedent(inspect.getsource(function)))
    except (OSError, TypeError, SyntaxError, IndentationError):
        return None


def _local_import_namespace(tree: ast.AST, function: types.FunctionType) -> dict[str, Any]:
    package = function.__module__.rsplit(".", 1)[0]
    names: dict[str, Any] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            base = _absolute_module(node.module or "", node.level, package)
            try:
                module = importlib.import_module(base)
            except ImportError:
                continue
            for alias in node.names:
                value = _getattr(module, alias.name)
                if value is not _MISSING:
                    names[alias.asname or alias.name] = value
        elif isinstance(node, ast.Import):
            for alias in node.names:
                try:
                    module = importlib.import_module(alias.name)
                except ImportError:
                    continue
                names[alias.asname or alias.name.split(".")[0]] = (
                    module if alias.asname else sys.modules[alias.name.split(".")[0]]
                )
    return names


def _function_namespace(function: types.FunctionType, tree: ast.AST | None) -> dict[str, Any]:
    namespace = dict(function.__globals__)
    namespace.update(_closure_values(function))
    if tree is not None:
        namespace.update(_local_import_namespace(tree, function))
    return namespace


def _callable_role(function: types.FunctionType) -> str:
    qualname = function.__qualname__
    if "<locals>" in qualname or "." not in qualname:
        return ROLE_FUNCTION
    owner: Any = sys.modules.get(function.__module__)
    parts = qualname.split(".")
    for part in parts[:-1]:
        owner = getattr(owner, part, None)
        if owner is None:
            return ROLE_FUNCTION
    if not isinstance(owner, type):
        return ROLE_FUNCTION
    member = owner.__dict__.get(parts[-1])
    if isinstance(member, staticmethod):
        return ROLE_STATICMETHOD
    if isinstance(member, classmethod):
        return ROLE_CLASSMETHOD
    if isinstance(member, property):
        return ROLE_PROPERTY
    return ROLE_METHOD


def canonical_default(value: Any) -> str:
    """A deterministic text form of a default value (no ids, sorted sets)."""

    if isinstance(value, Enum):
        return f"{owner_path(type(value))}.{value.name}"
    if value is None or isinstance(value, (bool, int, str, float)):
        return repr(value)
    if isinstance(value, Decimal):
        return f"Decimal('{value}')"
    if isinstance(value, (datetime, date, time, timedelta)):
        return repr(value)
    if isinstance(value, tuple):
        items = [canonical_default(item) for item in value]
        return "(" + ", ".join(items) + ("," if len(items) == 1 else "") + ")"
    if isinstance(value, list):
        return "[" + ", ".join(canonical_default(item) for item in value) + "]"
    if isinstance(value, (set, frozenset)):
        items = sorted(canonical_default(item) for item in value)
        return f"{type(value).__name__}({{{', '.join(items)}}})"
    if isinstance(value, (dict, types.MappingProxyType)):
        return "{" + ", ".join(f"{canonical_default(k)}: {canonical_default(v)}" for k, v in value.items()) + "}"
    if isinstance(value, (types.FunctionType, type)):
        return owner_path(value)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        inner = ", ".join(
            f"{item.name}={canonical_default(getattr(value, item.name))}" for item in dataclasses.fields(value)
        )
        return f"{owner_path(type(value))}({inner})"
    return f"<{type(value).__module__}.{type(value).__qualname__}>"


def _parameters(function: types.FunctionType, role: str) -> tuple[CensusParameter, ...]:
    parameters = list(inspect.signature(function, follow_wrapped=False).parameters.values())
    if role in _RECEIVER_ROLES and parameters:
        parameters = parameters[1:]
    out = []
    position = 0
    for parameter in parameters:
        positional = parameter.kind in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD)
        has_default = parameter.default is not parameter.empty
        out.append(
            CensusParameter(
                name=parameter.name,
                kind=parameter.kind.name,
                position=position if positional else None,
                has_default=has_default,
                default=canonical_default(parameter.default) if has_default else None,
            )
        )
        if positional:
            position += 1
    return tuple(out)


def _type_fields(cls: type) -> tuple[str, tuple[str, ...]]:
    if dataclasses.is_dataclass(cls):
        return TYPE_DATACLASS, tuple(item.name for item in dataclasses.fields(cls))
    if _is_protocol(cls):
        names: list[str] = []
        for base in reversed(cls.__mro__):
            if base is cls or (_is_scope_class(base) and _is_protocol(base)):
                for name in base.__dict__.get("__annotations__", {}):
                    if name not in names:
                        names.append(name)
        return TYPE_PROTOCOL, tuple(names)
    return TYPE_CLASS, ()


# --- nested, local and private callables (correction R2) -----------------------------------


def code_parameters(code: types.CodeType) -> tuple[tuple[str, str], ...]:
    """A code object's parameters as ``(name, kind)`` in signature order.

    The kinds are ``inspect.Parameter`` kind names. A generator expression's
    only parameter is CPython's implicit iterator ``.0``.
    """

    names = code.co_varnames
    positional = code.co_argcount
    keyword_only = code.co_kwonlyargcount
    out = [(name, "POSITIONAL_ONLY") for name in names[: code.co_posonlyargcount]]
    out += [(name, "POSITIONAL_OR_KEYWORD") for name in names[code.co_posonlyargcount : positional]]
    index = positional + keyword_only
    if code.co_flags & inspect.CO_VARARGS:
        out.append((names[index], "VAR_POSITIONAL"))
        index += 1
    out += [(name, "KEYWORD_ONLY") for name in names[positional : positional + keyword_only]]
    if code.co_flags & inspect.CO_VARKEYWORDS:
        out.append((names[index], "VAR_KEYWORD"))
    return tuple(out)


def code_source(code: types.CodeType) -> str:
    """``path:line`` of a code object, relative to the repository like every census source."""

    try:
        relative = Path(code.co_filename).resolve().relative_to(_PACKAGE_DIRECTORY.parent)
    except ValueError:
        relative = Path(Path(code.co_filename).name)
    return f"{relative.as_posix()}:{code.co_firstlineno}"


def _source_positions(code: types.CodeType) -> list[tuple[int, int, int, int]]:
    """Instruction positions that cover source text (the zero-width ``RESUME`` marker excluded)."""

    return [
        (line, end_line, column, end_column)
        for line, end_line, column, end_column in code.co_positions()
        if None not in (line, end_line, column, end_column) and (line, column) != (end_line, end_column)
    ]


def code_column(code: types.CodeType) -> int:
    """The first column an instruction of ``code`` covers on its first line (-1 if none).

    Two anonymous scopes on one source line differ here.
    """

    columns = [column for line, _, column, _ in _source_positions(code) if line == code.co_firstlineno]
    return min(columns) if columns else -1


_SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.GeneratorExp, ast.ClassDef)
# CPython 3.12 compiles list, set and dict comprehensions inline (PEP 709): they
# have no code object of their own, but they still scope their targets.
_INLINED_COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp)
_COMPREHENSION_SCOPES = (ast.GeneratorExp, *_INLINED_COMPREHENSIONS)


def _scope_name(node: ast.AST) -> str:
    if isinstance(node, ast.Lambda):
        return "<lambda>"
    if isinstance(node, ast.GeneratorExp):
        return "<genexpr>"
    return node.name  # type: ignore[attr-defined]


def _scope_first_line(node: ast.AST) -> int:
    lines = [node.lineno]  # type: ignore[attr-defined]
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        lines += [decorator.lineno for decorator in node.decorator_list]
    return min(lines)


def _scope_own_parts(node: ast.AST) -> list[ast.AST]:
    """The parts of a scope node compiled into that scope's own code."""

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return list(node.body)
    if isinstance(node, ast.Lambda):
        return [node.body]
    if isinstance(node, _COMPREHENSION_SCOPES):
        first, *rest = node.generators
        elements = [node.key, node.value] if isinstance(node, ast.DictComp) else [node.elt]
        return [*elements, first.target, *first.ifs, *(part for item in rest for part in (item.target, item.iter, *item.ifs))]
    return []


def _scope_outer_parts(node: ast.AST) -> list[ast.AST]:
    """The parts of a scope node evaluated in the scope that encloses it."""

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        arguments = node.args
        parts: list[ast.AST] = [*arguments.defaults, *(item for item in arguments.kw_defaults if item is not None)]
        if isinstance(node, ast.Lambda):
            return parts
        every = (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs, arguments.vararg, arguments.kwarg)
        parts += [item.annotation for item in every if item is not None and item.annotation is not None]
        return [*node.decorator_list, *parts, *([node.returns] if node.returns is not None else [])]
    if isinstance(node, _COMPREHENSION_SCOPES):
        return [node.generators[0].iter]
    if isinstance(node, ast.ClassDef):
        return [*node.decorator_list, *node.bases, *(keyword.value for keyword in node.keywords)]
    return []


def _child_scopes(node: ast.AST) -> list[ast.AST]:
    """Scope nodes whose code objects are constants of ``node``'s own code."""

    found: list[ast.AST] = []

    def visit(item: ast.AST) -> None:
        if isinstance(item, _SCOPE_NODES):
            found.append(item)
            for part in _scope_outer_parts(item):
                visit(part)
            return
        for child in ast.iter_child_nodes(item):
            visit(child)

    for part in _scope_own_parts(node):
        visit(part)
    return found


def _walk_scoped(scope: ast.AST) -> Iterator[tuple[ast.AST, tuple[ast.AST, ...]]]:
    """Every node inside ``scope``'s own code with the scopes between it and ``scope``."""

    def visit(item: ast.AST, stack: tuple[ast.AST, ...]) -> Iterator[tuple[ast.AST, tuple[ast.AST, ...]]]:
        yield item, stack
        if isinstance(item, (*_SCOPE_NODES, *_INLINED_COMPREHENSIONS)):
            for part in _scope_outer_parts(item):
                yield from visit(part, stack)
            for part in _scope_own_parts(item):
                yield from visit(part, (*stack, item))
            return
        for child in ast.iter_child_nodes(item):
            yield from visit(child, stack)

    for part in _scope_own_parts(scope):
        yield from visit(part, ())


def _scope_bindings(scope: ast.AST) -> frozenset[str]:
    """Names a scope binds: its parameters, assignment, loop, import, ``with``,
    ``except`` and ``match`` targets and the local functions and classes it
    defines. Names it declares ``global`` are not bound."""

    bound: set[str] = set()
    declared_global: set[str] = set()
    if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        arguments = scope.args
        every = (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs, arguments.vararg, arguments.kwarg)
        bound.update(item.arg for item in every if item is not None)

    def visit(item: ast.AST) -> None:
        if isinstance(item, ast.Name) and isinstance(item.ctx, (ast.Store, ast.Del)):
            bound.add(item.id)
        elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(item.name)
        elif isinstance(item, (ast.Import, ast.ImportFrom)):
            bound.update(alias.asname or alias.name.split(".")[0] for alias in item.names)
        elif isinstance(item, ast.Global):
            declared_global.update(item.names)
        elif isinstance(item, ast.ExceptHandler) and item.name:
            bound.add(item.name)
        elif isinstance(item, (ast.MatchAs, ast.MatchStar)) and item.name:
            bound.add(item.name)
        elif isinstance(item, ast.MatchMapping) and item.rest:
            bound.add(item.rest)
        if isinstance(item, (*_SCOPE_NODES, *_INLINED_COMPREHENSIONS)):
            for part in _scope_outer_parts(item):
                visit(part)
            if isinstance(item, _COMPREHENSION_SCOPES):
                # an assignment expression in a comprehension binds in this scope
                bound.update(
                    target.target.id
                    for target in ast.walk(item)
                    if isinstance(target, ast.NamedExpr) and isinstance(target.target, ast.Name)
                )
            return
        for child in ast.iter_child_nodes(item):
            visit(child)

    for part in _scope_own_parts(scope):
        visit(part)
    return frozenset(bound - declared_global)


@functools.lru_cache(maxsize=None)
def _module_scope_index(filename: str) -> Mapping[tuple[str, int], tuple[ast.AST, ...]]:
    """Every scope node of a source file by (name, first line)."""

    text = "".join(linecache.getlines(filename))
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return {}
    index: dict[tuple[str, int], list[ast.AST]] = {}
    for node in ast.walk(tree):
        if isinstance(node, _SCOPE_NODES):
            index.setdefault((_scope_name(node), _scope_first_line(node)), []).append(node)
    return {key: tuple(value) for key, value in index.items()}


def _span_contains(node: ast.AST, code: types.CodeType) -> bool:
    start = (_scope_first_line(node), 0) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else (
        node.lineno, node.col_offset  # type: ignore[attr-defined]
    )
    end = (node.end_lineno, node.end_col_offset)  # type: ignore[attr-defined]
    positions = _source_positions(code)
    return bool(positions) and all(start <= (line, column) and (end_line, end_column) <= end for line, end_line, column, end_column in positions)


def _pick_node(code: types.CodeType, candidates: Sequence[ast.AST]) -> ast.AST | None:
    if len(candidates) == 1:
        return candidates[0]
    containing = [node for node in candidates if _span_contains(node, code)]
    return containing[0] if len(containing) == 1 else None


def _source_node(code: types.CodeType) -> ast.AST | None:
    """The scope node of a reached function's code in its module source, if the live code still matches it."""

    candidates = _module_scope_index(code.co_filename).get((code.co_name, code.co_firstlineno), ())
    return _pick_node(code, candidates)


def _match_child_scopes(
    parent_code: types.CodeType, parent_node: ast.AST | None
) -> list[tuple[types.CodeType, ast.AST | None]]:
    """Pair each nested code constant with its source node (``None`` when the
    live code no longer matches its source)."""

    children = [constant for constant in parent_code.co_consts if isinstance(constant, types.CodeType)]
    if parent_node is None:
        return [(child, None) for child in children]
    candidates: dict[tuple[str, int], list[ast.AST]] = {}
    for node in _child_scopes(parent_node):
        candidates.setdefault((_scope_name(node), _scope_first_line(node)), []).append(node)
    matched: list[tuple[types.CodeType, ast.AST | None]] = []
    used: set[int] = set()
    for child in children:
        options = [node for node in candidates.get((child.co_name, child.co_firstlineno), ()) if id(node) not in used]
        node = _pick_node(child, options)
        if node is not None:
            used.add(id(node))
        matched.append((child, node))
    return matched


def _source_parameters(node: ast.AST | None) -> tuple[tuple[str, ...] | None, dict[str, str]]:
    """Parameter names and default expressions as the source declares them."""

    if isinstance(node, ast.GeneratorExp):
        return (".0",), {}
    if isinstance(node, ast.ClassDef):
        return (), {}
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        return None, {}
    arguments = node.args
    positional = [*arguments.posonlyargs, *arguments.args]
    defaults = {
        item.arg: ast.unparse(default)
        for item, default in zip(positional[len(positional) - len(arguments.defaults) :], arguments.defaults)
    }
    defaults.update(
        {item.arg: ast.unparse(default) for item, default in zip(arguments.kwonlyargs, arguments.kw_defaults) if default is not None}
    )
    names = tuple(
        item.arg
        for item in (*positional, arguments.vararg, *arguments.kwonlyargs, arguments.kwarg)
        if item is not None
    )
    return names, defaults


class _ScopeContext:
    """Parents, enclosing scopes and name occurrences inside one scope's own code."""

    def __init__(self, scope: ast.AST, chain: tuple[frozenset[str], ...], namespace: Mapping[str, Any]) -> None:
        self.scope = scope
        self.chain = chain
        self.namespace = namespace
        self.parents: dict[ast.AST, ast.AST] = {}
        self.stacks: dict[ast.AST, tuple[ast.AST, ...]] = {}
        self.names: dict[str, list[ast.Name]] = {}
        self._bindings: dict[ast.AST, frozenset[str]] = {}
        for node, stack in _walk_scoped(scope):
            self.stacks[node] = stack
            for child in ast.iter_child_nodes(node):
                self.parents.setdefault(child, node)
            if isinstance(node, ast.Name):
                self.names.setdefault(node.id, []).append(node)

    def bindings(self, scope: ast.AST) -> frozenset[str]:
        if scope not in self._bindings:
            self._bindings[scope] = _scope_bindings(scope)
        return self._bindings[scope]

    def shadowed(self, name: str, node: ast.AST) -> bool:
        """Whether ``name`` at ``node`` refers to a binding of a scope inside this one."""

        return any(name in self.bindings(scope) for scope in self.stacks[node])

    def argument(self, slot: str, expression: ast.AST, at: ast.AST, *, unpacked: bool = False) -> NestedArgument:
        text = ast.unparse(expression)
        if unpacked or isinstance(expression, ast.Starred):
            return NestedArgument(slot, text, ARGUMENT_UNPACKED)
        try:
            ast.literal_eval(expression)
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            pass
        else:
            return NestedArgument(slot, text, ARGUMENT_LITERAL)
        if isinstance(expression, ast.Name):
            for scope in reversed(self.stacks[at]):
                if expression.id in self.bindings(scope):
                    # a comprehension target iterates values computed in this
                    # owner; an inner function's own name is not the owner's
                    basis = ARGUMENT_SCOPE_NAME if isinstance(scope, _COMPREHENSION_SCOPES) else ARGUMENT_COMPUTED
                    return NestedArgument(slot, text, basis)
            if any(expression.id in bound for bound in self.chain):
                return NestedArgument(slot, text, ARGUMENT_SCOPE_NAME)
        return NestedArgument(slot, text, ARGUMENT_COMPUTED)

    def is_builtin(self, function: ast.AST, names: frozenset[str]) -> bool:
        return (
            isinstance(function, ast.Name)
            and function.id in names
            and not self.shadowed(function.id, function)
            and not any(function.id in bound for bound in self.chain)
            and function.id not in self.namespace
            and hasattr(builtins, function.id)
        )


def _classify_named(name: str, context: _ScopeContext) -> tuple[str, str, tuple[NestedCallSite, ...]]:
    """A local function (or lambda bound to a local name) by its uses in the enclosing scope."""

    sites: list[NestedCallSite] = []
    external: str | None = None
    definitions = sum(
        1
        for node, stack in context.stacks.items()
        if not stack
        and (
            (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name)
            or (isinstance(node, ast.Name) and node.id == name and isinstance(node.ctx, (ast.Store, ast.Del)))
        )
    )
    if definitions > 1:
        external = BASIS_REBOUND
    for occurrence in context.names.get(name, ()):
        if context.shadowed(name, occurrence) or isinstance(occurrence.ctx, (ast.Store, ast.Del)):
            continue
        call = context.parents.get(occurrence)
        if not (isinstance(call, ast.Call) and call.func is occurrence):
            external = external or BASIS_ESCAPES
            continue
        arguments = [context.argument(str(index), item, call) for index, item in enumerate(call.args)]
        arguments += [
            context.argument(keyword.arg or "**", keyword.value, call, unpacked=keyword.arg is None)
            for keyword in call.keywords
        ]
        sites.append(NestedCallSite(FORM_DIRECT_CALL, call.lineno, name, tuple(arguments)))
    bases = {argument.basis for site in sites for argument in site.arguments}
    if external is not None:
        return NESTED_EXTERNAL, external, tuple(sites)
    if ARGUMENT_UNPACKED in bases:
        return NESTED_EXTERNAL, BASIS_UNPACKED_ARGUMENT, tuple(sites)
    if ARGUMENT_COMPUTED in bases:
        return NESTED_EXTERNAL, BASIS_COMPUTED_ARGUMENT, tuple(sites)
    if not sites:
        return NESTED_OWNER_INTERNAL, BASIS_NEVER_CALLED, ()
    return NESTED_OWNER_INTERNAL, BASIS_DIRECT_CALLS, tuple(sites)


def _classify_nested(node: ast.AST, context: _ScopeContext) -> tuple[str, str, tuple[NestedCallSite, ...]]:
    """``OWNER_INTERNAL`` or ``EXTERNAL`` for a callable defined in ``context.scope``, decided from the AST.

    Owner-internal means every value its parameters receive is supplied inside
    the enclosing owner:

    - a local function called only directly, every argument a literal or a
      name bound in the enclosing owner's scopes;
    - a lambda passed only as ``key=`` to builtin ``sorted``, ``min`` or
      ``max``, which applies it to the values the owner passes the builtin;
    - a generator expression, whose only parameter is the iterator of its
      first ``for`` clause, evaluated in the enclosing scope.

    Anything else (escaping as a value, a computed or unpacked argument, a
    decorator, a rebound name, a local class) is external.
    """

    if isinstance(node, ast.GeneratorExp):
        iterable = node.generators[0].iter
        argument = NestedArgument(".0", f"iter({ast.unparse(iterable)})", ARGUMENT_SCOPE_EXPRESSION)
        return NESTED_OWNER_INTERNAL, BASIS_GENERATOR, (NestedCallSite(FORM_GENERATOR, iterable.lineno, "<genexpr>", (argument,)),)
    if isinstance(node, ast.ClassDef):
        return NESTED_EXTERNAL, BASIS_LOCAL_CLASS, ()
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if node.decorator_list:
            return NESTED_EXTERNAL, BASIS_DECORATED, ()
        return _classify_named(node.name, context)
    parent = context.parents.get(node)
    if isinstance(parent, ast.keyword) and parent.arg == "key":
        call = context.parents.get(parent)
        if isinstance(call, ast.Call) and context.is_builtin(call.func, _KEY_BUILTINS):
            arguments = tuple(context.argument(str(index), item, call) for index, item in enumerate(call.args))
            unpacked = any(item.basis == ARGUMENT_UNPACKED for item in arguments) or any(k.arg is None for k in call.keywords)
            site = NestedCallSite(
                FORM_BUILTIN_KEY,
                call.lineno,
                call.func.id,  # type: ignore[attr-defined]
                tuple(
                    item if item.basis == ARGUMENT_UNPACKED else dataclasses.replace(item, basis=ARGUMENT_SCOPE_EXPRESSION)
                    for item in arguments
                ),
            )
            if unpacked:
                return NESTED_EXTERNAL, BASIS_UNPACKED_ARGUMENT, (site,)
            return NESTED_OWNER_INTERNAL, BASIS_BUILTIN_KEY, (site,)
    if (
        isinstance(parent, ast.Assign)
        and len(parent.targets) == 1
        and isinstance(parent.targets[0], ast.Name)
        and parent.value is node
        and not context.stacks.get(parent, ())
    ):
        return _classify_named(parent.targets[0].id, context)
    return NESTED_EXTERNAL, BASIS_ESCAPES, ()


def _nested_role(code: types.CodeType, node: ast.AST | None) -> str:
    if isinstance(node, ast.ClassDef):
        return ROLE_LOCAL_CLASS
    if isinstance(node, ast.Lambda) or code.co_name == "<lambda>":
        return ROLE_LAMBDA
    if isinstance(node, ast.GeneratorExp) or code.co_name == "<genexpr>":
        return ROLE_GENERATOR_EXPRESSION
    if node is None and not code.co_flags & inspect.CO_NEWLOCALS:
        return ROLE_LOCAL_CLASS
    return ROLE_NESTED_FUNCTION


def _nested_call_site(caller: str, callee: str, site: NestedCallSite) -> CallSite:
    positional = [item for item in site.arguments if item.slot.isdigit()]
    return CallSite(
        caller=caller,
        callee=callee,
        positional=sum(1 for item in positional if item.basis != ARGUMENT_UNPACKED),
        keywords=tuple(sorted(item.slot for item in site.arguments if not item.slot.isdigit() and item.slot != "**")),
        star_args=any(item.basis == ARGUMENT_UNPACKED for item in positional),
        star_kwargs=any(item.slot == "**" for item in site.arguments),
    )


class _Walker:
    def __init__(self) -> None:
        self.functions: dict[str, types.FunctionType] = {}
        self.classes: dict[str, type] = {}
        self.parents: dict[str, tuple[str, str]] = {}
        self.references: dict[str, list[tuple[str, str]]] = {}
        self.call_sites: list[CallSite] = []
        self.sourceless: list[str] = []
        self.queue: deque[Any] = deque()
        self.nested: dict[str, NestedCallable] = {}
        self.nested_callables: dict[str, CensusCallable] = {}

    def offer(self, value: Any, parent: str, kind: str) -> None:
        candidates = {}
        for candidate in _node_candidates(value):
            candidates[owner_path(candidate)] = candidate
        for path, candidate in sorted(candidates.items()):
            self._add(path, candidate, parent, kind)

    def _add(self, path: str, node: Any, parent: str, kind: str) -> None:
        if parent != ROOT_PARENT and path != parent:
            self.references.setdefault(parent, [])
            if (kind, path) not in self.references[parent]:
                self.references[parent].append((kind, path))
        known: Any = self.functions.get(path, self.classes.get(path))
        if known is not None:
            same = known.__code__ is node.__code__ if isinstance(node, types.FunctionType) else known is node
            if not same:
                raise CensusError(
                    "CONFLICTING_OWNER_OBJECTS",
                    f"two different objects are reached under {path}; replace an owner everywhere it is bound",
                )
            return
        if isinstance(node, types.FunctionType):
            self.functions[path] = node
        else:
            self.classes[path] = node
        self.parents[path] = (parent, kind)
        self.queue.append(node)

    def drain(self) -> None:
        while self.queue:
            node = self.queue.popleft()
            if isinstance(node, types.FunctionType):
                self._visit_function(node)
            else:
                self._visit_class(node)

    def _visit_function(self, function: types.FunctionType) -> None:
        path = owner_path(function)
        for kind, value in _bytecode_references(function):
            self.offer(value, path, kind)
        tree = _parsed_source(function)
        if tree is None:
            self.sourceless.append(path)
        namespace = _function_namespace(function, tree)
        for annotation in getattr(function, "__annotations__", {}).values():
            for value in _annotation_objects(annotation, namespace):
                self.offer(value, path, REF_ANNOTATION)
        if tree is not None:
            for node in ast.walk(tree):
                annotations: list[ast.AST] = []
                if isinstance(node, ast.AnnAssign):
                    annotations.append(node.annotation)
                elif isinstance(node, ast.arg) and node.annotation is not None:
                    annotations.append(node.annotation)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.returns is not None:
                    annotations.append(node.returns)
                for annotation_node in annotations:
                    for value in _expression_objects(annotation_node, namespace):
                        self.offer(value, path, REF_ANNOTATION)
            self._record_call_sites(path, tree, namespace)
        for default in (*(function.__defaults__ or ()), *(function.__kwdefaults__ or {}).values()):
            self.offer(default, path, REF_DEFAULT)
        if any(isinstance(constant, types.CodeType) for constant in function.__code__.co_consts):
            module = function.__globals__.get("__name__", function.__module__)
            self._visit_nested(function.__code__, _source_node(function.__code__), path, (), module, function.__globals__, False)

    def _visit_nested(
        self,
        parent_code: types.CodeType,
        parent_node: ast.AST | None,
        parent_path: str,
        chain: tuple[frozenset[str], ...],
        module: str,
        namespace: Mapping[str, Any],
        in_local_class: bool,
    ) -> None:
        """Discover and classify every callable defined in ``parent_code``.

        Its body's references and call sites are already the enclosing reached
        callable's; this records the nested callable itself, so its parameters
        are enumerated and the tracer can match its frames.
        """

        pairs = _match_child_scopes(parent_code, parent_node)
        if not pairs:
            return
        context = None
        if parent_node is not None:
            chain = (_scope_bindings(parent_node), *chain)
            context = _ScopeContext(parent_node, chain, namespace)
        groups: dict[str, list[tuple[types.CodeType, ast.AST | None]]] = {}
        for child, node in pairs:
            groups.setdefault(child.co_name, []).append((child, node))
        for name, members in sorted(groups.items()):
            members.sort(key=lambda item: (item[0].co_firstlineno, code_column(item[0])))
            for index, (child, node) in enumerate(members, start=1):
                prefix = parent_code.co_qualname + "."
                relative = (
                    child.co_qualname[len(parent_code.co_qualname) :]
                    if child.co_qualname.startswith(prefix)
                    else f".<locals>.{child.co_name}"
                )
                # anonymous scopes, and repeated names, carry their source-order ordinal
                suffix = f"#{index}" if name.startswith("<") or len(members) > 1 else ""
                path = f"{parent_path}{relative}{suffix}"
                role = _nested_role(child, node)
                parameters = code_parameters(child)
                source_names, defaults = _source_parameters(node)
                matches = node is not None and source_names == tuple(item for item, _ in parameters)
                if in_local_class or role == ROLE_LOCAL_CLASS:
                    classification, basis, sites = NESTED_EXTERNAL, BASIS_LOCAL_CLASS, ()
                elif not matches or context is None:
                    classification, basis, sites = NESTED_EXTERNAL, BASIS_LIVE_CODE_DIFFERS, ()
                else:
                    classification, basis, sites = _classify_nested(node, context)  # type: ignore[arg-type]
                records = []
                position = 0
                for item, kind in parameters:
                    positional = kind in ("POSITIONAL_ONLY", "POSITIONAL_OR_KEYWORD")
                    default = defaults.get(item) if matches else None
                    records.append(CensusParameter(item, kind, position if positional else None, default is not None, default))
                    position += 1 if positional else 0
                source = code_source(child)
                self.nested_callables[path] = CensusCallable(path, role, parent_path, REF_NESTED, source, tuple(records))
                self.nested[path] = NestedCallable(
                    path=path,
                    module=module,
                    qualname=child.co_qualname,
                    role=role,
                    enclosing=parent_path,
                    source=source,
                    column=code_column(child),
                    classification=classification,
                    basis=basis,
                    call_sites=sites,
                )
                self.references.setdefault(parent_path, [])
                if (REF_NESTED, path) not in self.references[parent_path]:
                    self.references[parent_path].append((REF_NESTED, path))
                self.call_sites.extend(_nested_call_site(parent_path, path, site) for site in sites if site.form == FORM_DIRECT_CALL)
                self._visit_nested(
                    child, node if matches else None, path, chain, module, namespace, in_local_class or role == ROLE_LOCAL_CLASS
                )

    def _record_call_sites(self, caller: str, tree: ast.AST, namespace: Mapping[str, Any]) -> None:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            target = _resolve_expression(node.func, namespace)
            if isinstance(target, (staticmethod, classmethod)):
                target = target.__func__
            # Only a direct call of a function or class counts: a partial, a
            # bound method or a dispatch container may supply arguments the
            # call site does not show, so such a callee stays unresolved.
            if not (_is_source_function(target) or _is_scope_class(target)):
                continue
            callee = target
            self.call_sites.append(
                CallSite(
                    caller=caller,
                    callee=owner_path(callee),
                    positional=sum(1 for argument in node.args if not isinstance(argument, ast.Starred)),
                    keywords=tuple(sorted(keyword.arg for keyword in node.keywords if keyword.arg is not None)),
                    star_args=any(isinstance(argument, ast.Starred) for argument in node.args),
                    star_kwargs=any(keyword.arg is None for keyword in node.keywords),
                )
            )

    def _visit_class(self, cls: type) -> None:
        path = owner_path(cls)
        namespace = vars(sys.modules[cls.__module__])
        for base in cls.__mro__[1:]:
            if _is_scope_class(base):
                self.offer(base, path, REF_BASE)
        if dataclasses.is_dataclass(cls):
            for item in dataclasses.fields(cls):
                for value in _annotation_objects(item.type, namespace):
                    self.offer(value, path, REF_FIELD)
                if item.default is not dataclasses.MISSING:
                    self.offer(item.default, path, REF_FIELD)
                if item.default_factory is not dataclasses.MISSING:
                    self.offer(item.default_factory, path, REF_FIELD)
        if _is_protocol(cls):
            for annotation in cls.__dict__.get("__annotations__", {}).values():
                for value in _annotation_objects(annotation, namespace):
                    self.offer(value, path, REF_FIELD)
        for name, member in sorted(cls.__dict__.items()):
            if isinstance(member, (types.FunctionType, staticmethod, classmethod, property)):
                self.offer(member, path, REF_MEMBER)
            elif not (name.startswith("__") and name.endswith("__")):
                self.offer(member, path, REF_FIELD)


def discover_decision_path(roots: Sequence[DecisionPathRoot] = DECISION_PATH_ROOTS) -> DecisionPathCensus:
    """Build the static closure from the roots, reading the live owner code."""

    paths = [root.path for root in roots]
    if len(paths) != len(set(paths)):
        raise CensusError("DUPLICATE_ROOT", "a root is listed twice")
    walker = _Walker()
    for root in roots:
        walker.offer(root.resolve(), ROOT_PARENT, REF_ROOT)
    walker.drain()
    callables = {}
    for path, function in sorted(walker.functions.items()):
        role = _callable_role(function)
        parent, kind = walker.parents[path]
        callables[path] = CensusCallable(
            path=path,
            role=role,
            reached_from=parent,
            reached_by=kind,
            source=_source_location(function),
            parameters=_parameters(function, role),
        )
    clashing = sorted(set(callables) & set(walker.nested_callables))
    if clashing:
        raise CensusError("CONFLICTING_OWNER_OBJECTS", f"a nested callable shares a path with a reached owner: {clashing}")
    callables = dict(sorted({**callables, **walker.nested_callables}.items()))
    census_types = {}
    for path, cls in sorted(walker.classes.items()):
        kind_name, fields = _type_fields(cls)
        parent, kind = walker.parents[path]
        census_types[path] = CensusType(
            path=path,
            kind=kind_name,
            reached_from=parent,
            reached_by=kind,
            source=_source_location(cls),
            fields=fields,
        )
    references = {key: tuple(sorted(set(value))) for key, value in sorted(walker.references.items())}
    sites = tuple(
        sorted(
            set(walker.call_sites),
            key=lambda site: (site.caller, site.callee, site.positional, site.keywords, site.star_args, site.star_kwargs),
        )
    )
    return DecisionPathCensus(
        roots=tuple(roots),
        callables=callables,
        types=census_types,
        references=references,
        call_sites=sites,
        sourceless=tuple(sorted(walker.sourceless)),
        nested=dict(sorted(walker.nested.items())),
    )


# --- decision-path owner modules: what the roots leave out ---------------------------------


def _owner_modules() -> list[types.ModuleType]:
    import pkgutil

    names = set(DECISION_PATH_OWNER_MODULES)
    for package_name in DECISION_PATH_OWNER_PACKAGES:
        package = importlib.import_module(package_name)
        names.add(package_name)
        for info in pkgutil.walk_packages(package.__path__, prefix=package_name + "."):
            names.add(info.name)
    return [importlib.import_module(name) for name in sorted(names)]


def owner_module_definitions() -> dict[str, str]:
    """Every function, class and class member the owner modules define.

    Maps each path to ``FUNCTION``, ``CLASS`` or the member role. Generated
    dataclass methods are not definitions.
    """

    definitions: dict[str, str] = {}
    for module in _owner_modules():
        for value in vars(module).values():
            if _is_source_function(value) and value.__module__ == module.__name__:
                definitions[owner_path(value)] = ROLE_FUNCTION
            elif _is_scope_class(value) and value.__module__ == module.__name__:
                definitions[owner_path(value)] = "CLASS"
                for member in value.__dict__.values():
                    for candidate in _node_candidates(member):
                        if isinstance(candidate, types.FunctionType) and candidate.__module__ == module.__name__:
                            definitions[owner_path(candidate)] = _callable_role(candidate)
    return dict(sorted(definitions.items()))


def unreached_owner_definitions(census: DecisionPathCensus) -> dict[str, str]:
    reached = set(census.callables) | set(census.types)
    return {path: role for path, role in owner_module_definitions().items() if path not in reached}


# --- runtime cross-check -----------------------------------------------------------------


@dataclass(frozen=True)
class TracedCode:
    """One executed code object: its identity and its parameter names."""

    module: str
    qualname: str
    source: str
    column: int
    parameters: tuple[str, ...]

    @classmethod
    def from_code(cls, module: str, code: types.CodeType) -> TracedCode:
        return cls(module, code.co_qualname, code_source(code), code_column(code), tuple(name for name, _ in code_parameters(code)))

    @property
    def key(self) -> tuple[str, str, str, int]:
        return (self.module, self.qualname, self.source, self.column)


@dataclass(frozen=True)
class TracedCalls:
    functions: frozenset[str]
    dataclasses: frozenset[str]
    code: frozenset[TracedCode] = frozenset()


def trace_owner_calls(thunk: Callable[[], Any]) -> tuple[Any, TracedCalls]:
    """Run ``thunk`` and record every ``btc_predictor`` function entered and
    every ``btc_predictor`` dataclass constructed, via ``sys.setprofile``.

    A function is recorded as ``module.co_qualname``; nested functions,
    lambdas and generator expressions keep their ``<locals>`` qualname. Each
    executed code object is also recorded with its identity and parameter
    names, so :func:`uncovered_traced` can check it against its own static
    record.
    """

    functions: set[str] = set()
    constructed: set[str] = set()
    executed: set[tuple[str, types.CodeType]] = set()

    def profile(frame: types.FrameType, event: str, arg: Any) -> None:
        if event != "call":
            return
        code = frame.f_code
        if code.co_name == "__init__":
            instance = frame.f_locals.get("self")
            if instance is not None and dataclasses.is_dataclass(instance) and _is_scope_class(type(instance)):
                constructed.add(owner_path(type(instance)))
        if not _is_package_source(code.co_filename):
            return
        module = frame.f_globals.get("__name__")
        if in_scope_module(module):
            functions.add(f"{module}.{code.co_qualname}")
            executed.add((module, code))

    previous = sys.getprofile()
    sys.setprofile(profile)
    try:
        result = thunk()
    finally:
        sys.setprofile(previous)
    code = frozenset(TracedCode.from_code(module, item) for module, item in executed)
    return result, TracedCalls(frozenset(functions), frozenset(constructed), code)


def uncovered_traced(census: DecisionPathCensus, traced: TracedCalls) -> dict[str, list[str]]:
    """Traced items the static census does not contain.

    There is no exemption (policy V5 section 5A.5). A traced nested function,
    lambda or generator expression is covered only by its own static nested
    record, never by the callable that encloses it. Each executed code object
    must match a census callable by identity and by parameter names (less a
    method's receiver), so a callable whose live signature differs from the
    static census is reported too.
    """

    nested_paths = {f"{record.module}.{record.qualname}" for record in census.nested.values()}
    named = {path for path in census.callables if path not in census.nested}
    missing = {path for path in traced.functions if path not in named and path not in nested_paths}
    for code in traced.code:
        plain = f"{code.module}.{code.qualname}"
        candidates = census.nested_by_code.get(code.key) or ((plain,) if plain in named else ())
        if not candidates:
            missing.add(f"{plain} at {code.source}: not in the static census")
            continue
        expected = []
        for path in candidates:
            record = census.callables[path]
            expected.append(record.parameter_names)
            receiver = record.role in _RECEIVER_ROLES and path not in census.nested
            if (code.parameters[1:] if receiver else code.parameters) == record.parameter_names:
                break
        else:
            missing.add(f"{candidates[0]}: executed parameters {code.parameters} differ from the static census {expected[0]}")
    return {
        "functions": sorted(missing),
        "dataclasses": sorted(path for path in traced.dataclasses if path not in census.types),
    }


# --- stated limits (policy V5 section 5A.5) -------------------------------------------------

CENSUS_LIMITS_VERSION = "DECISION_PATH_CENSUS_LIMITS_V1"
CENSUS_COMPLETENESS_CLAIM = (
    "The census claims completeness only for static discovery plus the runtime trace over the paths the fixture runs "
    "and the owner tests actually exercise; it is not a universal proof (policy V5 section 5A.5). Static discovery "
    "walks every reached callable's bytecode, annotations, defaults, members and nested code, and classifies every "
    "nested, local and private callable it defines. The tracer has no exemption: every executed frame, nested or "
    "not, must match a statically discovered callable by code identity and parameter names."
)
KNOWN_LIMITS: tuple[tuple[str, str], ...] = (
    (
        "ENCLOSING_LOCAL_CALLBACKS",
        "A callable an owner receives as a value (a parameter or local variable holding a callback) is invisible to "
        "static discovery, which resolves names only in module globals, closure cells and function-local imports. "
        "Every function, lambda, generator expression and class defined inside a reached body is discovered and "
        "classified; a received callback is caught only if a traced run executes it.",
    ),
    (
        "UNNAMED_PROTOCOL_IMPLEMENTATIONS",
        "A method on a concrete class that no reached code names, such as a caller-supplied implementation of a "
        "Protocol, is not discovered. The one reached Protocol, btc_predictor.levels.breakout.SourceLevel, is "
        "field-only, and its supported implementations (the weekly and monthly swing levels) are reached.",
    ),
    (
        "DYNAMIC_GETATTR_DISPATCH",
        "A getattr with a computed name is not resolved. Every reached owner getattr reads a field, property or "
        "as_record of a reached class or a field of an enumerated configuration dataclass (R1 audit, confirmed by the "
        "re-review pattern audit).",
    ),
    (
        "UNEXECUTED_BRANCHES",
        "Code that never runs gives no runtime evidence. The measured line and branch coverage of the reached owner "
        "bodies is recorded below; an unexecuted arc is covered by static discovery alone.",
    ),
)
MEASURED_COVERAGE: Mapping[str, Any] = {
    "tool": "coverage.py 7.16.0 (branch measurement) on CPython 3.12.14",
    "measured_on": "2026-10-02",
    "scope": (
        "Reached-body figures count the statements and branch arcs inside the source bodies of the reached named "
        "callables, which contain every nested callable; whole-module figures also count unreached definitions and "
        "module initialisation of the 50 reached source modules."
    ),
    "runs": (
        {
            "run": "fixture runs",
            "description": "the 202 deterministic fixture runs of the nine census trace modules, covering all 74 roots",
            "reached_lines": {"covered": 4993, "total": 7565, "percent": "66.00"},
            "reached_branches": {"covered": 2235, "total": 3728, "percent": "59.95"},
            "module_lines": {"covered": 4993, "total": 11539, "percent": "43.27"},
            "module_branches": {"covered": 2235, "total": 4140, "percent": "53.99"},
            "nested_callables_executed": {"covered": 224, "total": 230},
        },
        {
            "run": "owner tests",
            "description": (
                "the 1,699 existing owner tests in the 55 modules listed under owner_test_files in "
                "rbt002_rereview_evidence_v1.json"
            ),
            "reached_lines": {"covered": 5855, "total": 7565, "percent": "77.40"},
            "reached_branches": {"covered": 2934, "total": 3728, "percent": "78.70"},
            "module_lines": {"covered": 6480, "total": 11539, "percent": "56.16"},
            "module_branches": {"covered": 3149, "total": 4140, "percent": "76.06"},
            "nested_callables_executed": {"covered": 224, "total": 230},
        },
    ),
    "strict_trace": (
        "Under both runs a root-scoped tracer checked every executed frame against the static census by code identity "
        "and parameter names, with no exemption: 0 uncovered functions and 0 uncovered dataclasses."
    ),
    "nested_never_executed": (
        "btc_predictor.data.quality.DerivativesQualityConfig.__post_init__.<locals>.<genexpr>#1",
        "btc_predictor.features.entry.EntryConvictionResult.as_record.<locals>.<genexpr>#1",
        "btc_predictor.features.entry.EntryConvictionResult.as_record.<locals>.<genexpr>#2",
        "btc_predictor.features.entry.EntryConvictionResult.as_record.<locals>.<genexpr>#3",
        "btc_predictor.risk.trailing._validate_result.<locals>.<genexpr>#1",
    ),
    "unexecuted_arcs": (
        "1,493 reached-body branch arcs never run under the fixtures and 794 never run under the owner tests. Their "
        "complete source-line to target-line lists are in backtest_evidence/research_backtest_v1/"
        "rbt002_rereview_evidence_v1.json under coverage.runs.{fixtures,owners}.files.*.unexecuted_branches; the R2 "
        "re-measurement reproduced those lists exactly."
    ),
}
RUNTIME_GUARD_BACKSTOP = (
    "Backstop: the runtime completeness guard of policy V5 section 5A.6, binding on RBT-004, RBT-005 and RBT-006. Every "
    "owner function a composer calls directly must be a census root, and any incomplete owner result or missing-input "
    "reason code in a composed replay must map to a cause in the reviewed inventory or CHAMPION_COMPLETION_SPEC_V1; an "
    "unaccounted one fails the test (RBT-004/RBT-005) or blocks the freeze (RBT-006)."
)


def census_limits() -> dict[str, Any]:
    """The census's stated limits and measured coverage, persisted with the inventory."""

    return {
        "version": CENSUS_LIMITS_VERSION,
        "claim": CENSUS_COMPLETENESS_CLAIM,
        "known_limits": [{"limit": name, "statement": statement} for name, statement in KNOWN_LIMITS],
        "measured_coverage": {
            **{key: value for key, value in MEASURED_COVERAGE.items() if key not in ("runs", "nested_never_executed")},
            "runs": [dict(run) for run in MEASURED_COVERAGE["runs"]],
            "nested_never_executed": list(MEASURED_COVERAGE["nested_never_executed"]),
        },
        "backstop": RUNTIME_GUARD_BACKSTOP,
    }


# --- what the roots leave out ---------------------------------------------------------------

_BATCH = (
    "batch/report wrapper that scores a series of persisted inputs; the composer scores one decision instant at a "
    "time through the single-decision root"
)
_RAW_SERIES_VARIANT = (
    "value-series variant over a bare price sequence; the root {root} computes the same Rulebook quantity from "
    "point-in-time daily bars"
)
_ROLLING_HELPER = (
    "BTC-041 generic prior-window helper that no decision-path owner calls. It is a candidate convention for "
    "CHAMPION_COMPLETION_SPEC_V1 (policy V4 section 6A.2), not a current input"
)
_FACTOR_AUDIT = "Rulebook 4.1 factor-separation audit tooling, run by tests and reports; it feeds no decision"
_PERSISTENCE = (
    "persistence round-trip of a stored record or lifecycle (reports, persistence and the engine restore state they "
    "already hold); it adds no decision input"
)
_EXPLANATION = (
    "Rulebook 27 explanation output: aggregates already-computed results into reason-code records after a decision; "
    "it feeds no decision"
)


def _helper_of(owner: str) -> str:
    return f"private helper reached only from the left-out {owner}"


# Every function, class and member defined in the decision-path owner modules
# that no root reaches, with the reason it is not on the decision path. The
# census tests require this to equal the unreached definitions exactly.
LEFT_OUT_OWNER_DEFINITIONS: dict[str, str] = {
    "btc_predictor.features.add.AddScoreBatchResult": _BATCH,
    "btc_predictor.features.add.calculate_add_score_batch": _BATCH,
    "btc_predictor.features.entry.EntryConvictionBatchResult": _BATCH,
    "btc_predictor.features.entry.calculate_entry_conviction_batch": _BATCH,
    "btc_predictor.features.hold.HoldScoreBatchResult": _BATCH,
    "btc_predictor.features.hold.calculate_hold_score_batch": _BATCH,
    "btc_predictor.features.momentum.four_week_momentum": _RAW_SERIES_VARIANT.format(root="four_week_momentum_from_daily_bars"),
    "btc_predictor.features.momentum.twelve_week_momentum": _RAW_SERIES_VARIANT.format(root="twelve_week_momentum_from_daily_bars"),
    "btc_predictor.features.rolling.historical_normalize": _ROLLING_HELPER,
    "btc_predictor.features.rolling.rolling_percentile": _ROLLING_HELPER,
    "btc_predictor.features.rolling.rolling_volatility": _ROLLING_HELPER,
    "btc_predictor.features.rolling.rolling_zscore": _ROLLING_HELPER,
    "btc_predictor.features.rolling.true_ranges": _ROLLING_HELPER,
    "btc_predictor.features.scoring_contracts.FactorOverlapAudit": _FACTOR_AUDIT,
    "btc_predictor.features.scoring_contracts.FactorOverlapAudit.as_record": _FACTOR_AUDIT,
    "btc_predictor.features.scoring_contracts.FactorOverlapAudit.mechanically_clean": _FACTOR_AUDIT,
    "btc_predictor.features.scoring_contracts.FactorOverlapFinding": _FACTOR_AUDIT,
    "btc_predictor.features.scoring_contracts.FactorOverlapFinding.as_record": _FACTOR_AUDIT,
    "btc_predictor.features.scoring_contracts.FactorPath": _FACTOR_AUDIT,
    "btc_predictor.features.scoring_contracts.FactorPath.as_record": _FACTOR_AUDIT,
    "btc_predictor.features.scoring_contracts._declared_total": _FACTOR_AUDIT,
    "btc_predictor.features.scoring_contracts.audit_factor_overlap": _FACTOR_AUDIT,
    "btc_predictor.features.scoring_contracts.effective_weight_report": _FACTOR_AUDIT,
    "btc_predictor.features.scoring_contracts.effective_weights": _FACTOR_AUDIT,
    "btc_predictor.features.scoring_contracts.expand_factor_paths": _FACTOR_AUDIT,
    "btc_predictor.features.volatility.calculate_volatility_score_from_results": (
        "convenience wrapper that rebuilds VolatilityScoreInput from persisted results and calls the root "
        "calculate_volatility_score; the composer calls the root"
    ),
    "btc_predictor.features.volatility.rv_7_20_60_from_daily_bars": (
        "RV7/RV20/RV60 convenience triple; the root realized_volatility_from_daily_bars computes each window the "
        "volatility owners consume (RV20 is not a Rulebook 8 input)"
    ),
    "btc_predictor.portfolio.state_machine._as_mapping": _helper_of("persistence round-trip functions"),
    "btc_predictor.portfolio.state_machine._persisted_transition_record": _helper_of("position_event_records"),
    "btc_predictor.portfolio.state_machine._replay_transition_record": _helper_of("replay_position_lifecycle"),
    "btc_predictor.portfolio.state_machine._transition_from_record": _helper_of("restore_position_lifecycle"),
    "btc_predictor.portfolio.state_machine.persisted_action_for_event": _PERSISTENCE,
    "btc_predictor.portfolio.state_machine.persisted_status_for_state": _PERSISTENCE,
    "btc_predictor.portfolio.state_machine.position_event_records": _PERSISTENCE,
    "btc_predictor.portfolio.state_machine.replay_position_event_records": _PERSISTENCE,
    "btc_predictor.portfolio.state_machine.replay_position_lifecycle": _PERSISTENCE,
    "btc_predictor.portfolio.state_machine.restore_position_lifecycle": _PERSISTENCE,
    "btc_predictor.risk.buffer.volatility_buffer_grid": (
        "BTC-185 research grid over ATR multipliers; the decision uses volatility_buffer_for_invalidation (root) "
        "at the configured multiplier"
    ),
    "btc_predictor.risk.exposure._record_bool": _helper_of("risk_at_stop_from_record"),
    "btc_predictor.risk.exposure._record_optional_decimal": _helper_of("risk_at_stop_from_record"),
    "btc_predictor.risk.exposure._record_reason_codes": _helper_of("risk_at_stop_from_record"),
    "btc_predictor.risk.exposure._record_string": _helper_of("risk_at_stop_from_record"),
    "btc_predictor.risk.exposure._tranche_risk_from_record": _helper_of("risk_at_stop_from_record"),
    "btc_predictor.risk.exposure.risk_at_stop_from_record": _PERSISTENCE,
    "btc_predictor.risk.trailing._optional_string": _helper_of("trailing_stop_from_record"),
    "btc_predictor.risk.trailing._optional_utc": _helper_of("trailing_stop_from_record"),
    "btc_predictor.risk.trailing._record_bool": _helper_of("trailing_stop_from_record"),
    "btc_predictor.risk.trailing._record_int": _helper_of("trailing_stop_from_record"),
    "btc_predictor.risk.trailing.trailing_stop_from_record": _PERSISTENCE,
    "btc_predictor.signals.data_quality.build_recommendation_reason_code_records": _EXPLANATION,
    "btc_predictor.signals.exit_rules._optional_bool": _helper_of("exit_signal_from_record"),
    "btc_predictor.signals.exit_rules._optional_positive_decimal": _helper_of("exit_signal_from_record"),
    "btc_predictor.signals.exit_rules._optional_score": _helper_of("exit_signal_from_record"),
    "btc_predictor.signals.exit_rules._optional_string": _helper_of("exit_signal_from_record"),
    "btc_predictor.signals.exit_rules._parse_utc": _helper_of("exit_signal_from_record"),
    "btc_predictor.signals.exit_rules._required_bool": _helper_of("exit_signal_from_record"),
    "btc_predictor.signals.exit_rules._required_string": _helper_of("exit_signal_from_record"),
    "btc_predictor.signals.exit_rules._string_tuple": _helper_of("exit_signal_from_record"),
    "btc_predictor.signals.exit_rules.exit_signal_from_record": _PERSISTENCE,
    "btc_predictor.signals.reason_codes.ReasonCodeDefinition": _EXPLANATION,
    "btc_predictor.signals.reason_codes.ReasonCodeDefinition.to_reason": _EXPLANATION,
    "btc_predictor.signals.reason_codes.ReasonCodeEngineResult": _EXPLANATION,
    "btc_predictor.signals.reason_codes.ReasonCodeEngineResult.as_record": _EXPLANATION,
    "btc_predictor.signals.reason_codes.ReasonCodeEngineResult.reason_codes": _EXPLANATION,
    "btc_predictor.signals.reason_codes.ReasonCodeEngineResult.recommendation_records": _EXPLANATION,
    "btc_predictor.signals.reason_codes._entry_action_reasons": _helper_of("build_reason_code_engine"),
    "btc_predictor.signals.reason_codes._entry_conviction_reasons": _helper_of("build_reason_code_engine"),
    "btc_predictor.signals.reason_codes._hard_veto_reasons": _helper_of("build_reason_code_engine"),
    "btc_predictor.signals.reason_codes._hard_veto_source_reasons": _helper_of("build_reason_code_engine"),
    "btc_predictor.signals.reason_codes._hard_veto_source_severity": _helper_of("build_reason_code_engine"),
    "btc_predictor.signals.reason_codes._rank_reasons": _helper_of("build_reason_code_engine"),
    "btc_predictor.signals.reason_codes._reason_detail": _helper_of("build_reason_code_engine"),
    "btc_predictor.signals.reason_codes._reason_sort_key": _helper_of("build_reason_code_engine"),
    "btc_predictor.signals.reason_codes._require_matching_config": _helper_of("build_reason_code_engine"),
    "btc_predictor.signals.reason_codes._setup_is_supported": _helper_of("build_reason_code_engine"),
    "btc_predictor.signals.reason_codes._validate_config_metadata": _helper_of("build_reason_code_engine"),
    "btc_predictor.signals.reason_codes._validate_derived_state": _helper_of("build_reason_code_engine"),
    "btc_predictor.signals.reason_codes._validate_reason": _helper_of("build_reason_code_engine"),
    "btc_predictor.signals.reason_codes._validate_source_completion": _helper_of("build_reason_code_engine"),
    "btc_predictor.signals.reason_codes._validate_source_versions": _helper_of("build_reason_code_engine"),
    "btc_predictor.signals.reason_codes.build_reason_code_engine": _EXPLANATION,
    "btc_predictor.signals.reason_codes.canonical_signal_reason": _EXPLANATION,
}

# Every other top-level part of btc_predictor, and why its code is not an
# owner of the champion's decision inputs. Reached code there (helpers, the
# config loader, data records) is still enumerated by the census.
OUTSIDE_OWNER_SCOPE: dict[str, str] = {
    "btc_predictor.backtest": (
        "BTC-180..185 engine, costs and research tooling: executes and evaluates the composer's intents (fills, "
        "costs, walk-forward); its lifecycle writes go through the state-machine roots"
    ),
    "btc_predictor.config": (
        "configuration owner: the frozen StrategyConfig is enumerated field by field and the loader is reached through "
        "owner defaults; application/runtime settings are not strategy inputs"
    ),
    "btc_predictor.data": (
        "persisted record types (enumerated as raw historical inputs), collectors and provider adapters that fill the "
        "raw tables; the BTC-031 quality owner data.quality is in scope"
    ),
    "btc_predictor.db": "database schema and migrations: storage, not a decision input",
    "btc_predictor.journal": "trade journal persistence of decisions already made",
    "btc_predictor.logging": "logging configuration",
    "btc_predictor.portfolio": (
        "paper-execution simulation, accounting and persistence of fills; the BTC-150 lifecycle state machine "
        "portfolio.state_machine is in scope"
    ),
    "btc_predictor.quant": "numerical helpers; every quant function an owner calls is reached and enumerated",
    "btc_predictor.reporting": "reports and explanation output built from stored results",
    "btc_predictor.research": "BTC-019 and EPIC X research and evidence code: not part of the champion's decision path",
    "btc_predictor.research_backtest": "EPIC Y research code, including this census: never an owner",
    "btc_predictor.tests": "tests",
}
