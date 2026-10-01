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

Everything here is structural: no input is classified, no value is read and no
owner is modified.
"""

from __future__ import annotations

import ast
import dataclasses
import dis
import functools
import importlib
import inspect
import sys
import textwrap
import types
from collections import deque
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

import btc_predictor


CENSUS_VERSION = "DECISION_PATH_STATIC_CENSUS_V1"
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
REFERENCE_KINDS = (REF_ROOT, REF_CODE, REF_LOCAL_IMPORT, REF_ANNOTATION, REF_DEFAULT, REF_MEMBER, REF_BASE, REF_FIELD)

ROLE_FUNCTION = "FUNCTION"
ROLE_METHOD = "METHOD"
ROLE_STATICMETHOD = "STATICMETHOD"
ROLE_CLASSMETHOD = "CLASSMETHOD"
ROLE_PROPERTY = "PROPERTY"
_RECEIVER_ROLES = (ROLE_METHOD, ROLE_CLASSMETHOD, ROLE_PROPERTY)

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
class DecisionPathCensus:
    """The static closure from the roots. Paths are ``module.qualname``."""

    roots: tuple[DecisionPathRoot, ...]
    callables: Mapping[str, CensusCallable]
    types: Mapping[str, CensusType]
    references: Mapping[str, tuple[tuple[str, str], ...]]
    call_sites: tuple[CallSite, ...]
    sourceless: tuple[str, ...]

    @property
    def root_paths(self) -> tuple[str, ...]:
        return tuple(root.path for root in self.roots)

    @functools.cached_property
    def callers(self) -> Mapping[str, tuple[str, ...]]:
        """For each node, the reached callables whose bodies name it."""

        callers: dict[str, set[str]] = {}
        for source, targets in self.references.items():
            if source not in self.callables:
                continue
            for kind, target in targets:
                if kind in (REF_CODE, REF_LOCAL_IMPORT):
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
        return {
            "census_version": CENSUS_VERSION,
            "roots": len(self.roots),
            "callables": len(self.callables),
            "types": len(self.types),
            "dataclass_types": len(dataclass_types),
            "protocol_types": len(protocol_types),
            "other_classes": len(self.types) - len(dataclass_types) - len(protocol_types),
            "fields": sum(len(item.fields) for item in self.types.values()),
            "parameters": sum(len(item.parameters) for item in self.callables.values()),
            "resolved_call_sites": len(self.call_sites),
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


class _Walker:
    def __init__(self) -> None:
        self.functions: dict[str, types.FunctionType] = {}
        self.classes: dict[str, type] = {}
        self.parents: dict[str, tuple[str, str]] = {}
        self.references: dict[str, list[tuple[str, str]]] = {}
        self.call_sites: list[CallSite] = []
        self.sourceless: list[str] = []
        self.queue: deque[Any] = deque()

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
class TracedCalls:
    functions: frozenset[str]
    dataclasses: frozenset[str]


def trace_owner_calls(thunk: Callable[[], Any]) -> tuple[Any, TracedCalls]:
    """Run ``thunk`` and record every ``btc_predictor`` function entered and
    every ``btc_predictor`` dataclass constructed, via ``sys.setprofile``.

    A function is recorded as ``module.co_qualname``; nested functions,
    lambdas and generator expressions keep their ``<locals>`` qualname.
    """

    functions: set[str] = set()
    constructed: set[str] = set()

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

    previous = sys.getprofile()
    sys.setprofile(profile)
    try:
        result = thunk()
    finally:
        sys.setprofile(previous)
    return result, TracedCalls(frozenset(functions), frozenset(constructed))


def uncovered_traced(census: DecisionPathCensus, traced: TracedCalls) -> dict[str, list[str]]:
    """Traced items the static census does not contain.

    A traced nested function, lambda or generator expression is covered by the
    census node whose body defines it.
    """

    def covered(path: str) -> bool:
        if path in census.callables:
            return True
        parts = path.split(".<locals>")
        return any(".<locals>".join(parts[: index + 1]) in census.callables for index in range(len(parts) - 1))

    return {
        "functions": sorted(path for path in traced.functions if not covered(path)),
        "dataclasses": sorted(path for path in traced.dataclasses if path not in census.types),
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
