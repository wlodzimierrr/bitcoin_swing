"""Historical input coverage inventory for the EPIC Y research backtest (RBT-002).

``INVENTORY_HISTORICAL_INPUT_COVERAGE_V1`` measures what exists and what must be
collected before any backfill, under ``RESEARCH_BACKTEST_POLICY_V3`` sections 3,
4, 5, 5A and 9. It decides nothing on its own and computes no trading outcome:
no composer, score or backtest runs here.

- **Input surface (section 5A).** The surface is discovered, not listed: the
  static census of :mod:`btc_predictor.research_backtest.input_census` walks the
  owner code from the composer's entry points (the only hand-written list) and
  reaches every helper, method, input/result/config dataclass and default on
  the champion's decision path. Every field of every reached dataclass or
  ``Protocol`` and every parameter of every reached callable must carry exactly
  one :class:`InputClassification`: its section 4 shape, section 5 family,
  producing owner (or ``OWNERLESS``), historical source, the owner's
  missing-input behaviour and the Entry Conviction components it feeds.
  Composer-facing inputs are classified field by field here; the rest follow
  audited rules over the reviewed snapshot in ``input_census_registry``. An
  unclassified owner, field or parameter raises :class:`InputSurfaceError`, so
  an owner that gains an input, or a newly reached owner, fails the
  enumeration.
- **Database coverage.** Read-only ``SELECT`` statements report, per raw table
  and series, counts per policy window, first and last observation, gap
  positions, provenance and timestamp semantics. Rows dated before 2020-01-01 or
  inside the holdout are only counted: ``COUNT``, ``MIN`` and ``MAX`` of their
  time columns. No value column is selected in those ranges, or anywhere else.
- **Minimum history.** Each input's warm-up rule is read from its owner's
  constants and keyword defaults, never restated, and simulated over observation
  instants to find the earliest instant it could be complete. An input with no
  owner window is ``UNDEFINED``, never guessed.
- **Sources, blockers and the RBT-003 plan.** Ranked source candidates with
  measured depth and exact cost from metadata probes, the section 5A blocker
  list, and an acquisition plan with a total cost.

Everything here is ``RESEARCH_BACKTEST_NON_CERTIFYING`` evidence with the
canonical reference ``UNRESOLVED``. No third-party value is stored: each probe is
recorded as provenance (URL, date, HTTP status, response digest) plus metadata.
"""

from __future__ import annotations

import argparse
import dataclasses
import inspect
import re
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from btc_predictor.data import (
    DerivativesQualityConfig,
    EtfFlow,
    FundingRate,
    FuturesBasis,
    Liquidation,
    OhlcvBar,
    OpenInterest,
    PerpVolume,
    derive_ohlcv_bars,
    expected_etf_publication_dates,
    missing_bar_timestamps,
)
from btc_predictor.data import quality as quality_owner
from btc_predictor.features import add as add_owner
from btc_predictor.features import entry as entry_owner
from btc_predictor.features import flow as flow_owner
from btc_predictor.features import hold as hold_owner
from btc_predictor.features import momentum as momentum_owner
from btc_predictor.features import positioning as positioning_owner
from btc_predictor.features import regime as regime_owner
from btc_predictor.features import setup as setup_owner
from btc_predictor.features import structure as structure_owner
from btc_predictor.features import trend as trend_owner
from btc_predictor.features import volatility as volatility_owner
from btc_predictor.levels import anchored_vwap as anchored_vwap_owner
from btc_predictor.levels import breakout as breakout_owner
from btc_predictor.levels import clustering as clustering_owner
from btc_predictor.levels import strength as strength_owner
from btc_predictor.levels import swing as swing_owner
from btc_predictor.levels import volume_profile as volume_profile_owner
from btc_predictor.research import prospective_integration_corpus as epic_x_corpus
from btc_predictor.portfolio import state_machine as state_machine_owner
from btc_predictor.research.us_equity_market_closures import (
    COVERAGE_END as CLOSURE_TABLE_COVERAGE_END,
    COVERAGE_START as CLOSURE_TABLE_COVERAGE_START,
    TABLE_VERSION as CLOSURE_TABLE_VERSION,
    load_closures,
)
from btc_predictor.research_backtest import input_census as census_owner
from btc_predictor.research_backtest import input_census_registry as census_registry
from btc_predictor.research_backtest.replay_inputs import (
    CANONICAL_REFERENCE_UNRESOLVED,
    DATA_WINDOW,
    ETF_FLOW_FAMILY,
    FUNDING_RATE_FAMILY,
    HOLDOUT_WINDOW,
    OPEN_INTEREST_FAMILY,
    PERP_VOLUME_FAMILY,
    PROHIBITED_WINDOW,
    REFERENCE_PRICE_FAMILY,
    REPLAY_VENUES,
    RESEARCH_EVIDENCE_CLASS,
    RESERVE_WINDOW,
    SHARED_VOLUME_FAMILY,
    SHARED_VOLUME_VENUE,
    ReplayWindow,
    canonical_decimal,
    canonical_json_bytes,
    etf_flow_scheduled_available_at,
    sha256_hex,
)
from btc_predictor.risk import budget as budget_owner
from btc_predictor.risk import buffer as buffer_owner
from btc_predictor.risk import exposure as exposure_owner
from btc_predictor.risk import invalidation as invalidation_owner
from btc_predictor.risk import reward as reward_owner
from btc_predictor.risk import sizing as sizing_owner
from btc_predictor.risk import stop as stop_owner
from btc_predictor.risk import trailing as trailing_owner
from btc_predictor.risk import tranches as tranches_owner
from btc_predictor.signals import add_requirements as add_requirements_owner
from btc_predictor.signals import breakout_retest as breakout_retest_owner
from btc_predictor.signals import data_quality as data_quality_gate_owner
from btc_predictor.signals import exit_rules as exit_rules_owner
from btc_predictor.signals import hard_veto as hard_veto_owner
from btc_predictor.signals import higher_low as higher_low_owner
from btc_predictor.signals import no_chase as no_chase_owner
from btc_predictor.signals import reclaim as reclaim_owner
from btc_predictor.signals import trim as trim_owner


# --- identity ------------------------------------------------------------------

INVENTORY_VERSION = "INVENTORY_HISTORICAL_INPUT_COVERAGE_V1"
INVENTORY_TICKET = "RBT-002"
INVENTORY_POLICY_VERSION = "RESEARCH_BACKTEST_POLICY_V4"
INVENTORY_AVAILABILITY_POLICY_VERSION = "HISTORICAL_REPLAY_AVAILABILITY_V2"
DATABASE_COVERAGE_SNAPSHOT_VERSION = "RESEARCH_DATABASE_COVERAGE_SNAPSHOT_V1"
SOURCE_PROBE_DATE = "2026-10-01"
ARTIFACT_DIRECTORY = Path("backtest_evidence") / "research_backtest_v1"
INVENTORY_FILENAME = "rbt002_input_coverage_inventory_v1.json"
INVENTORY_DIGEST_FILENAME = "rbt002_input_coverage_inventory_v1.json.sha256"
INVENTORY_REPORT_FILENAME = "rbt002_input_coverage_inventory_v1.md"

_DATA_START: datetime = DATA_WINDOW.start  # type: ignore[assignment]
_HOLDOUT_START: datetime = HOLDOUT_WINDOW.start  # type: ignore[assignment]
_RESERVE_START: datetime = RESERVE_WINDOW.start  # type: ignore[assignment]
_LAST_DATA_HOUR = _HOLDOUT_START - timedelta(hours=1)
COVERAGE_WINDOWS: tuple[ReplayWindow, ...] = (
    PROHIBITED_WINDOW,
    DATA_WINDOW,
    HOLDOUT_WINDOW,
    RESERVE_WINDOW,
)

# Policy V3 section 3: US spot bitcoin ETFs began trading on 2024-01-11, so the
# flow score cannot be complete before then. The liquidation percentile needs
# its certified minimum of prior daily observations before the first ETF-era
# decision, which fixes the latest acceptable liquidation history start.
ETF_ERA_FIRST_TRADING_DATE = date(2024, 1, 11)
LIQUIDATION_REQUIRED_DEPTH_DATE = ETF_ERA_FIRST_TRADING_DATE - timedelta(
    days=epic_x_corpus.LIQUIDATION_PERCENTILE_MIN_OBSERVATIONS
)
LIQUIDATION_PREFERRED_DEPTH_DATE = date(2022, 1, 1)


class InputSurfaceError(ValueError):
    """The section 5A enumeration found an unclassified or stale input."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


class CoverageError(ValueError):
    """The coverage collection or inventory build refused its inputs."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


# --- vocabularies ----------------------------------------------------------------

# Policy V3 section 4 record shapes.
SHAPE_INTERVAL = "INTERVAL"
SHAPE_SNAPSHOT = "SNAPSHOT"
SHAPE_SETTLEMENT = "SETTLEMENT"
SHAPE_EVENT = "EVENT"
SHAPE_DAILY_PUBLISHED = "DAILY_PUBLISHED"
SHAPE_DISCRETIONARY = "DISCRETIONARY"
POLICY_SHAPES = (
    SHAPE_INTERVAL,
    SHAPE_SNAPSHOT,
    SHAPE_SETTLEMENT,
    SHAPE_EVENT,
    SHAPE_DAILY_PUBLISHED,
    SHAPE_DISCRETIONARY,
)
# A value computed by an owner inherits its upstream records' shapes.
SHAPE_DERIVED = "DERIVED_FROM_UPSTREAM"
SHAPE_NOT_APPLICABLE = "NOT_APPLICABLE"
SHAPES = (*POLICY_SHAPES, SHAPE_DERIVED, SHAPE_NOT_APPLICABLE)

# Policy V3 section 5 families. The first six are RBT-001's identifiers.
FUTURES_BASIS_FAMILY = "FUTURES_BASIS"
LIQUIDATION_FAMILY = "LIQUIDATIONS"
MARKET_CAP_FAMILY = "BTC_MARKET_CAP"
DISCRETIONARY_FAMILY = "DISCRETIONARY_ASSERTION"
MARKET_CLOSURE_FAMILY = "US_EQUITY_MARKET_CLOSURES"
CVD_FAMILY = "CVD"
MACRO_ONCHAIN_LIQUIDITY_FAMILY = "MACRO_ONCHAIN_LIQUIDITY"
POLICY_FAMILIES = (
    REFERENCE_PRICE_FAMILY,
    SHARED_VOLUME_FAMILY,
    ETF_FLOW_FAMILY,
    FUNDING_RATE_FAMILY,
    OPEN_INTEREST_FAMILY,
    FUTURES_BASIS_FAMILY,
    MARKET_CAP_FAMILY,
    LIQUIDATION_FAMILY,
    PERP_VOLUME_FAMILY,
    DISCRETIONARY_FAMILY,
    MARKET_CLOSURE_FAMILY,
    CVD_FAMILY,
    MACRO_ONCHAIN_LIQUIDITY_FAMILY,
)
# Not section 5 data families: the replay's own state and the champion config.
ENGINE_STATE_FAMILY = "ENGINE_STATE"
STRATEGY_CONFIG_FAMILY = "STRATEGY_CONFIG"
FAMILIES = (*POLICY_FAMILIES, ENGINE_STATE_FAMILY, STRATEGY_CONFIG_FAMILY)

KIND_RAW = "RAW_HISTORICAL"
KIND_DERIVED = "DERIVED_BY_OWNER"
KIND_OWNERLESS_CERTIFIED = "OWNERLESS_CERTIFIED_DEFINITION"
KIND_OWNERLESS_UNDEFINED = "OWNERLESS_UNDEFINED"
KIND_OWNERLESS_FALLBACK = "OWNERLESS_RULEBOOK_FALLBACK"
KIND_ENGINE_STATE = "ENGINE_STATE"
KIND_CONFIG = "STRATEGY_CONFIG"
KIND_DISCRETIONARY = "DISCRETIONARY"
KIND_ABSENT = "ABSENT_RULEBOOK_FALLBACK"
KIND_OWNER_INTERNAL = "OWNER_INTERNAL_DATAFLOW"
INPUT_KINDS = (
    KIND_RAW,
    KIND_DERIVED,
    KIND_OWNERLESS_CERTIFIED,
    KIND_OWNERLESS_UNDEFINED,
    KIND_OWNERLESS_FALLBACK,
    KIND_ENGINE_STATE,
    KIND_CONFIG,
    KIND_DISCRETIONARY,
    KIND_ABSENT,
    KIND_OWNER_INTERNAL,
)
OWNERLESS = "OWNERLESS"

ROLE_VALUE = "VALUE"
ROLE_OBSERVATION_TIME = "OBSERVATION_TIME"
ROLE_AVAILABILITY = "AVAILABILITY"
ROLE_INGESTION = "INGESTION_PROVENANCE"
ROLE_IDENTITY = "IDENTITY"
ROLE_PROVENANCE = "PROVENANCE"
ROLE_UNIT = "UNIT"
ROLE_REVISION = "REVISION"
ROLES = (
    ROLE_VALUE,
    ROLE_OBSERVATION_TIME,
    ROLE_AVAILABILITY,
    ROLE_INGESTION,
    ROLE_IDENTITY,
    ROLE_PROVENANCE,
    ROLE_UNIT,
    ROLE_REVISION,
)

ENTRY_CONVICTION_COMPONENTS: tuple[str, ...] = tuple(entry_owner.ENTRY_CONVICTION_COMPONENT_IDS)
CORE_REGIME_COMPONENTS: tuple[str, ...] = tuple(regime_owner.CORE_REGIME_SCORE_COMPONENT_IDS)
_TREND, _FLOW, _POSITIONING, _VOLATILITY, _STRUCTURE = (
    "trend",
    "flow",
    "positioning",
    "volatility",
    "structure",
)
if set(ENTRY_CONVICTION_COMPONENTS) != {_TREND, _FLOW, _POSITIONING, _VOLATILITY, _STRUCTURE}:
    raise ImportError("the Entry Conviction owner changed its component ids")
if not set(CORE_REGIME_COMPONENTS) <= set(ENTRY_CONVICTION_COMPONENTS):
    raise ImportError("the core regime owner changed its component ids")

DECISION_OWNER = "NEEDS_OWNER_DECISION"
DECISION_POLICY_V4 = "NEEDS_POLICY_V4_DECISION"
DECISIONS = (DECISION_OWNER, DECISION_POLICY_V4)


def _owner_path(obj: Any) -> str:
    return f"{obj.__module__}.{obj.__qualname__}"


# --- section 5A classification ---------------------------------------------------


@dataclass(frozen=True)
class InputClassification:
    """One input's section 5A mapping.

    ``producing_owner`` is the dotted owner that produces the value, or
    ``OWNERLESS``. ``input_id`` names the logical input when several fields
    carry it (for example one liquidation percentile feeding three owners).
    ``entry_components`` lists the Entry Conviction components the input feeds;
    an empty tuple means it feeds none (a flag, veto, risk or lifecycle input).
    """

    kind: str
    shape: str
    families: tuple[str, ...]
    producing_owner: str
    historical_source: str
    missing_behaviour: str
    entry_components: tuple[str, ...] = ()
    input_id: str | None = None
    role: str = ROLE_VALUE
    note: str = ""

    def __post_init__(self) -> None:
        if self.kind not in INPUT_KINDS:
            raise ValueError(f"unknown input kind {self.kind!r}")
        if self.shape not in SHAPES:
            raise ValueError(f"unknown shape {self.shape!r}")
        if not self.families or any(family not in FAMILIES for family in self.families):
            raise ValueError(f"families must be non-empty members of FAMILIES: {self.families}")
        if any(component not in ENTRY_CONVICTION_COMPONENTS for component in self.entry_components):
            raise ValueError(f"unknown Entry Conviction component in {self.entry_components}")
        if self.role not in ROLES:
            raise ValueError(f"unknown role {self.role!r}")
        if self.kind == KIND_RAW and self.shape not in POLICY_SHAPES:
            raise ValueError("a raw historical input needs a policy section 4 shape")
        ownerless = self.kind in (KIND_OWNERLESS_CERTIFIED, KIND_OWNERLESS_UNDEFINED, KIND_OWNERLESS_FALLBACK)
        if ownerless != (self.producing_owner == OWNERLESS):
            raise ValueError("producing_owner is OWNERLESS exactly for owner-less inputs")
        if ownerless and not self.input_id:
            raise ValueError("an owner-less input needs an input_id")
        if self.kind == KIND_DISCRETIONARY and self.shape != SHAPE_DISCRETIONARY:
            raise ValueError("a discretionary input has the DISCRETIONARY shape")
        if not self.missing_behaviour.strip() or not self.historical_source.strip():
            raise ValueError("missing_behaviour and historical_source are required")

    @property
    def core_regime_components(self) -> tuple[str, ...]:
        return tuple(c for c in self.entry_components if c in CORE_REGIME_COMPONENTS)

    def as_record(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "shape": self.shape,
            "families": list(self.families),
            "producing_owner": self.producing_owner,
            "historical_source": self.historical_source,
            "missing_behaviour": self.missing_behaviour,
            "entry_components": list(self.entry_components),
            "core_regime_components": list(self.core_regime_components),
            "input_id": self.input_id,
            "role": self.role,
            "note": self.note,
        }


_SRC_OHLCV = "raw.btc_ohlcv via BTC-020 collect_btc_ohlcv (Bitstamp, Coinbase and Bitfinex adapters)"
_SRC_DERIVED_BARS = (
    "derived from the venue's raw.btc_ohlcv 1h replay bars by BTC-040 "
    "build_canonical_market_bars at the decision instant (RBT-001 replay_market_bars_at)"
)
_SRC_ETF = "raw.etf_flows via collect_etf_flows (EtfFlowProvider)"
_SRC_FUNDING = "raw.funding_rates via BTC-021 collect_btc_derivatives (DerivativesProvider.fetch_funding_rates)"
_SRC_OI = "raw.open_interest via BTC-021 collect_btc_derivatives (DerivativesProvider.fetch_open_interest)"
_SRC_BASIS = "raw.futures_basis via BTC-021 collect_btc_derivatives (DerivativesProvider.fetch_futures_basis)"
_SRC_LIQUIDATIONS = "raw.liquidations via BTC-021 collect_btc_derivatives (DerivativesProvider.fetch_liquidations)"
_SRC_PERP = "raw.perp_volume via BTC-021 collect_btc_derivatives (DerivativesProvider.fetch_perp_volume)"
_SRC_MARKET_CAP = (
    "hash-bound evidence files under backtest_evidence/ (policy V3 section 5: no raw "
    "table, no collector, no schema migration)"
)
_SRC_CLOSURES = f"{CLOSURE_TABLE_VERSION} via btc_predictor.research.us_equity_market_closures.load_closures"
_SRC_NONE_DISCRETIONARY = "none: never back-filled (policy V3 section 4 DISCRETIONARY)"
_SRC_ENGINE = "the replay's own BTC-180 engine and BTC-150 lifecycle state"
_SRC_CONFIG = "btc_predictor/config/strategy/default.toml or the owner's keyword default"
_SRC_UPSTREAM = "computed by the producing owner from upstream classified inputs"
_SRC_NONE_ABSENT = "none: declared absent by policy V3 section 5"
_SRC_NONE_OWNERLESS = "none: no owner produces this value"
_SRC_LEDGER = "the composer's own decision ledger of earlier owner results"

_PRICE = (REFERENCE_PRICE_FAMILY,)
_PRICE_VOLUME = (REFERENCE_PRICE_FAMILY, SHARED_VOLUME_FAMILY)
_POSITIONING_FAMILIES = (FUNDING_RATE_FAMILY, OPEN_INTEREST_FAMILY, FUTURES_BASIS_FAMILY, MARKET_CAP_FAMILY)
_VOLATILITY_FAMILIES = (REFERENCE_PRICE_FAMILY, LIQUIDATION_FAMILY)
_ALL_COMPONENT_FAMILIES = (
    REFERENCE_PRICE_FAMILY,
    SHARED_VOLUME_FAMILY,
    ETF_FLOW_FAMILY,
    FUNDING_RATE_FAMILY,
    OPEN_INTEREST_FAMILY,
    FUTURES_BASIS_FAMILY,
    MARKET_CAP_FAMILY,
    LIQUIDATION_FAMILY,
    MARKET_CLOSURE_FAMILY,
)
_REGIME_FAMILIES = tuple(f for f in _ALL_COMPONENT_FAMILIES if f != SHARED_VOLUME_FAMILY)


def _raw(
    families: tuple[str, ...],
    shape: str,
    role: str,
    source: str,
    missing: str,
    entry_components: tuple[str, ...] = (),
    *,
    note: str = "",
) -> InputClassification:
    return InputClassification(
        kind=KIND_RAW,
        shape=shape,
        families=families,
        producing_owner=source.split(" via ")[-1] if " via " in source else source,
        historical_source=source,
        missing_behaviour=missing,
        entry_components=entry_components,
        role=role,
        note=note,
    )


def _derived(
    owner: Any,
    missing: str,
    families: tuple[str, ...],
    entry_components: tuple[str, ...] = (),
    *,
    input_id: str | None = None,
    role: str = ROLE_VALUE,
    note: str = "",
    source: str = _SRC_UPSTREAM,
) -> InputClassification:
    return InputClassification(
        kind=KIND_DERIVED,
        shape=SHAPE_DERIVED,
        families=families,
        producing_owner=owner if isinstance(owner, str) else _owner_path(owner),
        historical_source=source,
        missing_behaviour=missing,
        entry_components=entry_components,
        input_id=input_id,
        role=role,
        note=note,
    )


def _ownerless(
    input_id: str,
    missing: str,
    families: tuple[str, ...],
    entry_components: tuple[str, ...] = (),
    *,
    certified: str | None = None,
    note: str = "",
) -> InputClassification:
    return InputClassification(
        kind=KIND_OWNERLESS_CERTIFIED if certified else KIND_OWNERLESS_UNDEFINED,
        shape=SHAPE_DERIVED,
        families=families,
        producing_owner=OWNERLESS,
        historical_source=certified or _SRC_NONE_OWNERLESS,
        missing_behaviour=missing,
        entry_components=entry_components,
        input_id=input_id,
        note=note,
    )


def _level_volume_fallback() -> InputClassification:
    """Record existing authority without inventing a volume percentile.

    The frozen strength owner still requires volume even at zero weight. This
    is an implementation/authority compatibility gap, not a new percentile to
    choose in CHAMPION_COMPLETION_SPEC_V1.
    """

    return dataclasses.replace(
        _ownerless("LEVEL_VOLUME_PERCENTILE", _M_LEVEL_STRENGTH, _PRICE_VOLUME, (_STRUCTURE,)),
        kind=KIND_OWNERLESS_FALLBACK,
        historical_source="Rulebook v1.2 section 9.2 core weights: timeframe 0.30, touches 0.25, reaction 0.25, confluence 0.20; omit volume",
        note="RULEBOOK_FALLBACK_EXISTS; calculate_level_strength still requires every component including volume, even at zero weight. The fallback has no executable production path; resolve that compatibility gap before composition. Do not define a new volume percentile.",
    )


def _state(
    what: str,
    missing: str,
    *,
    role: str = ROLE_VALUE,
    source: str = _SRC_ENGINE,
    note: str = "",
) -> InputClassification:
    return InputClassification(
        kind=KIND_ENGINE_STATE,
        shape=SHAPE_NOT_APPLICABLE,
        families=(ENGINE_STATE_FAMILY,),
        producing_owner=what,
        historical_source=source,
        missing_behaviour=missing,
        role=role,
        note=note,
    )


def _config(note: str = "owner keyword default or the strategy configuration value") -> InputClassification:
    return InputClassification(
        kind=KIND_CONFIG,
        shape=SHAPE_NOT_APPLICABLE,
        families=(STRATEGY_CONFIG_FAMILY,),
        producing_owner="btc_predictor.config.StrategyConfig",
        historical_source=_SRC_CONFIG,
        missing_behaviour="never missing: a declared constant of the frozen champion configuration",
        note=note,
    )


def _discretionary(input_id: str, missing: str, *, note: str = "") -> InputClassification:
    return InputClassification(
        kind=KIND_DISCRETIONARY,
        shape=SHAPE_DISCRETIONARY,
        families=(DISCRETIONARY_FAMILY,),
        producing_owner="manual assertion (no owner)",
        historical_source=_SRC_NONE_DISCRETIONARY,
        missing_behaviour=missing,
        input_id=input_id,
        note=note,
    )


def _absent(
    input_id: str,
    families: tuple[str, ...],
    missing: str,
    *,
    note: str = "",
) -> InputClassification:
    return InputClassification(
        kind=KIND_ABSENT,
        shape=SHAPE_NOT_APPLICABLE,
        families=families,
        producing_owner="declared absent (policy V3 section 5)",
        historical_source=_SRC_NONE_ABSENT,
        missing_behaviour=missing,
        input_id=input_id,
        note=note,
    )


# Shared missing-input behaviours, quoted from the owners.
_M_EC = "None -> ENTRY_CONVICTION_INPUT_MISSING; Entry Conviction score None, never zero-filled"
_M_REGIME = "None -> REGIME_SCORE_CORE_INPUT_MISSING; regime score None"
_M_HOLD = "None -> HOLD_SCORE_INPUT_MISSING; Hold Score None"
_M_ADD_SCORE = "None -> ADD_SCORE_INPUT_MISSING; Add Score None"
_M_POSITIONING = "None -> POSITIONING_SCORE_INPUT_MISSING; positioning score None (Rulebook 7.5 has no fallback)"
_M_TREND_REQUIRED = (
    "no None handling: TrendScoreInput fields are required Decimals and "
    "calculate_trend_score raises RuntimeError on a None component, so a missing "
    "component cannot be represented and EntryConvictionInput.trend_score must stay None"
)
_M_FLOW_CORE = "None -> FLOW_SCORE_CORE_INPUT_MISSING; FlowScoreResult.complete False, score None"
_M_ORDERLINESS = "any None -> ORDERLINESS_INPUT_MISSING; orderliness score None"
_M_VOLATILITY = "None -> VOLATILITY_SCORE_INPUT_MISSING; volatility score None"
_M_STRUCTURE = "None -> STRUCTURE_SCORE_INPUT_MISSING; structure score None"
_M_STRESS = "None -> STRESS_INPUT_MISSING; complete False, flagged still set by the present triggers"
_M_CAPITULATION = "None -> CAPITULATION_INPUT_MISSING; complete False, flagged still set by the present triggers"
_M_EUPHORIA = "None -> EUPHORIA_INPUT_MISSING; complete False, flagged still set by the present triggers"
_M_CROWDING = "None -> CROWDING_INPUT_MISSING; complete False, flagged still set by the present inputs"
_M_VETO = "None -> HARD_VETO_INPUT_MISSING; the new trade is blocked (fail closed)"
_M_ADD_REQ = "None -> ADD_REQUIREMENTS_INPUT_MISSING; the add is blocked (fail closed)"
_M_TRIM = "None -> TRIM_INPUT_MISSING; complete False, the other triggers still evaluate"
_M_EXIT = "None -> EXIT_INPUT_MISSING; complete False, the other exit reasons still evaluate"
_M_SETUP = "None -> the setup's *_INPUT_MISSING reason; the setup is not matched (fail closed)"
_M_LEVEL_STRENGTH = "None -> LEVEL_STRENGTH_INPUT_MISSING; level strength score None"
_M_SETUP_REJECT = "None -> setup not detected"
_M_REQUIRED_ROW = "required field of a persisted owner record; a record without it is refused by the owner"


def _record_fields(
    families: tuple[str, ...],
    shape: str,
    source: str,
    entry_components: tuple[str, ...],
    missing: str,
    *,
    time_field: str = "observation_time",
    values: Mapping[str, str] = {},
    identity: Iterable[str] = ("exchange", "symbol"),
    units: Iterable[str] = (),
    revision: Iterable[str] = (),
    provenance: Iterable[str] = ("provider", "source"),
    availability: Iterable[str] = ("available_at",),
    ingestion: Iterable[str] = ("ingested_at",),
    note: str = "",
) -> dict[str, InputClassification]:
    """Classify every field of one persisted raw owner record."""

    fields: dict[str, InputClassification] = {
        time_field: _raw(families, shape, ROLE_OBSERVATION_TIME, source, missing, entry_components, note=note)
    }
    for name, value_note in values.items():
        fields[name] = _raw(families, shape, ROLE_VALUE, source, missing, entry_components, note=value_note)
    for name in identity:
        fields[name] = _raw(families, shape, ROLE_IDENTITY, source, _M_REQUIRED_ROW, entry_components)
    for name in units:
        fields[name] = _raw(families, shape, ROLE_UNIT, source, _M_REQUIRED_ROW, entry_components)
    for name in revision:
        fields[name] = _raw(families, shape, ROLE_REVISION, source, _M_REQUIRED_ROW, entry_components)
    for name in provenance:
        fields[name] = _raw(families, shape, ROLE_PROVENANCE, source, _M_REQUIRED_ROW, entry_components)
    for name in availability:
        fields[name] = _raw(
            families,
            shape,
            ROLE_AVAILABILITY,
            source,
            _M_REQUIRED_ROW,
            entry_components,
            note="the replay copy carries the policy V3 section 4 modelled availability here",
        )
    for name in ingestion:
        fields[name] = _raw(
            families,
            shape,
            ROLE_INGESTION,
            source,
            _M_REQUIRED_ROW,
            entry_components,
            note="raw bulk ingestion time; kept in the manifest, never a visibility predicate",
        )
    return fields


# Composer-facing owner input types the census reaches, with every field
# classified. Membership is decided by the census: the enumeration requires
# these to be exactly the reached types that the registry does not categorise.
_INPUT_TYPE_FIELDS: dict[type, dict[str, InputClassification]] = {
    # -- persisted raw records (the leaves) ---------------------------------------
    OhlcvBar: {
        **_record_fields(
            _PRICE_VOLUME,
            SHAPE_INTERVAL,
            _SRC_OHLCV,
            (_TREND, _VOLATILITY, _STRUCTURE),
            "a missing hour leaves its daily/weekly/monthly bucket underived (BTC-040 complete-hour census); never filled",
            time_field="timestamp",
            values={
                "open": "venue price (one venue per run, no splicing)",
                "high": "venue price",
                "low": "venue price",
                "close": "venue price",
                "volume": "Bitstamp raw volume feeds spot participation and volume profile (policy section 2)",
            },
            identity=("exchange", "symbol", "timeframe"),
            provenance=("provider",),
            availability=(),
            ingestion=(),
        ),
        "ingested_at": _raw(
            _PRICE_VOLUME,
            SHAPE_INTERVAL,
            ROLE_AVAILABILITY,
            _SRC_OHLCV,
            _M_REQUIRED_ROW,
            (_TREND, _VOLATILITY, _STRUCTURE),
            note="the only bar availability field the engine reads; the replay copy carries timestamp + 1h",
        ),
    },
    EtfFlow: _record_fields(
        (ETF_FLOW_FAMILY,),
        SHAPE_DAILY_PUBLISHED,
        _SRC_ETF,
        (_FLOW,),
        "a missing (fund, publication date) row -> ETF_FLOW_INPUT_MISSING; missing AUM -> ETF_FLOW_AUM_MISSING",
        time_field="observation_date",
        values={"flow_usd": "net creation/redemption flow per fund and US trading date", "aum_usd": "fund AUM (TotalETFAssets)"},
        identity=("fund",),
        revision=("revision",),
    ),
    FundingRate: _record_fields(
        (FUNDING_RATE_FAMILY,),
        SHAPE_SETTLEMENT,
        _SRC_FUNDING,
        (_POSITIONING,),
        "no visible rows -> FUNDING_RATE_INPUT_MISSING; fewer prior averages than the owner minimum -> FUNDING_HEALTH_INSUFFICIENT_HISTORY",
        values={"funding_rate": "rate for the settled funding interval", "funding_interval_hours": "settled accrual period length"},
        identity=("exchange", "symbol", "instrument"),
    ),
    OpenInterest: _record_fields(
        (OPEN_INTEREST_FAMILY,),
        SHAPE_SNAPSHOT,
        _SRC_OI,
        (_POSITIONING,),
        "no visible rows -> OI_GROWTH_INPUT_MISSING / OI_INTENSITY_OI_INPUT_MISSING",
        values={"open_interest": "snapshot open interest"},
        identity=("exchange", "symbol", "instrument"),
        units=("open_interest_unit",),
    ),
    FuturesBasis: _record_fields(
        (FUTURES_BASIS_FAMILY,),
        SHAPE_SNAPSHOT,
        _SRC_BASIS,
        (_POSITIONING,),
        "no visible rows -> FUTURES_BASIS_INPUT_MISSING; short history -> FUTURES_BASIS_INSUFFICIENT_HISTORY",
        values={
            "basis_rate": "futures versus spot basis",
            "annualized_basis_rate": "annualized basis; the owner z-scores this field",
            "expiry": "contract expiry",
        },
        identity=("exchange", "symbol", "instrument"),
        note="schema: 'UTC market timestamp for the basis observation' and no timeframe column, so SNAPSHOT",
    ),
    Liquidation: _record_fields(
        (LIQUIDATION_FAMILY,),
        SHAPE_INTERVAL,
        _SRC_LIQUIDATIONS,
        (_VOLATILITY,),
        "an hour or day without an observed feed state yields no liquidation percentile (certified adapter); never 0",
        values={"quantity": "liquidated quantity", "notional_usd": "liquidated notional (USD)", "side": "liquidated side"},
        identity=("exchange", "symbol", "timeframe"),
        units=("quantity_unit",),
        note=(
            "persisted as per-side interval aggregates: the primary key (observation_time, exchange, "
            "symbol, timeframe, side, provider) cannot hold two same-side events at one instant"
        ),
    ),
    PerpVolume: _record_fields(
        (PERP_VOLUME_FAMILY,),
        SHAPE_INTERVAL,
        _SRC_PERP,
        (),
        "no visible rows -> PERP_VOLUME_INPUT_MISSING (spot participation only; not used under ETF_CORE)",
        values={"volume": "perpetual volume", "notional_usd": "perpetual notional (USD)"},
        identity=("exchange", "symbol", "timeframe"),
        units=("volume_unit",),
        note="RBT-001: persisted stamped at the interval start (the participation join needs it)",
    ),
    positioning_owner.MarketCapObservation: _record_fields(
        (MARKET_CAP_FAMILY,),
        SHAPE_DAILY_PUBLISHED,
        _SRC_MARKET_CAP,
        (_POSITIONING,),
        "no market cap at an OI snapshot instant -> OI_INTENSITY_MARKET_CAP_INPUT_MISSING; leverage_health None",
        values={"market_cap_usd": "BTC market capitalisation (USD)"},
        identity=(),
        provenance=("provider",),
        ingestion=(),
        note="the owner joins market cap to OI by exact observation_time equality",
    ),
    flow_owner.VolumeParticipationObservation: {
        name: _derived(
            flow_owner.spot_perp_participation_from_rows,
            "no spot or no perp rows -> SPOT_VOLUME_INPUT_MISSING / PERP_VOLUME_INPUT_MISSING",
            (SHARED_VOLUME_FAMILY, PERP_VOLUME_FAMILY),
            role=role,
            note="built by the owner from Bitstamp OhlcvBar and PerpVolume rows; not used under ETF_CORE",
        )
        for name, role in (
            ("observation_time", ROLE_OBSERVATION_TIME),
            ("market_type", ROLE_IDENTITY),
            ("notional_usd", ROLE_VALUE),
            ("provider", ROLE_PROVENANCE),
            ("available_at", ROLE_AVAILABILITY),
        )
    },
    flow_owner.CvdObservation: {
        name: _absent(
            "CVD",
            (CVD_FAMILY,),
            "no persisted CVD -> SPOT_CVD_INPUT_MISSING / PERP_CVD_INPUT_MISSING; flow model ETF_CORE",
            note="policy V3 section 5: CVD absent, Rulebook 6.2 ETF_CORE fallback applies",
        )
        for name in ("observation_time", "market_type", "cvd_usd", "provider", "available_at")
    },
    # -- Entry Conviction and its components ----------------------------------------
    entry_owner.EntryConvictionInput: {
        "trend_score": _derived(trend_owner.calculate_trend_score, _M_EC, _PRICE, (_TREND,)),
        "flow_score": _derived(flow_owner.calculate_flow_score, _M_EC, (ETF_FLOW_FAMILY, MARKET_CLOSURE_FAMILY), (_FLOW,)),
        "positioning_score": _derived(
            positioning_owner.calculate_positioning_score, _M_EC, _POSITIONING_FAMILIES, (_POSITIONING,)
        ),
        "volatility_score": _derived(
            volatility_owner.calculate_volatility_score, _M_EC, _VOLATILITY_FAMILIES, (_VOLATILITY,)
        ),
        "structure_score": _derived(
            structure_owner.calculate_structure_score_from_clusters, _M_EC, _PRICE_VOLUME, (_STRUCTURE,)
        ),
    },
    trend_owner.TrendScoreInput: {
        "z_m4": _ownerless(
            "TREND_Z_M4",
            _M_TREND_REQUIRED,
            _PRICE,
            (_TREND,),
            note="MOMENTUM_4W has an owner; its z-score normalisation window does not (Rulebook 5.1: 'trailing historical data')",
        ),
        "z_m12": _ownerless(
            "TREND_Z_M12",
            _M_TREND_REQUIRED,
            _PRICE,
            (_TREND,),
            note="MOMENTUM_12W has an owner; its z-score normalisation window does not",
        ),
        "z_20w": _ownerless(
            "TREND_Z_20W",
            _M_TREND_REQUIRED,
            _PRICE,
            (_TREND,),
            note="MA_DISTANCE_20W has an owner; its z-score normalisation window does not",
        ),
        "structure_score": _derived(
            trend_owner.classify_weekly_structure_from_weekly_bars,
            _M_TREND_REQUIRED,
            _PRICE,
            (_TREND,),
            input_id="WEEKLY_STRUCTURE",
            note="the weekly structure raw score (-1..+1), not z-scored by the Rulebook",
        ),
        "z_52h": _ownerless(
            "TREND_Z_52H",
            _M_TREND_REQUIRED,
            _PRICE,
            (_TREND,),
            note="HIGH_DISTANCE_52W has an owner; its z-score normalisation window does not",
        ),
    },
    flow_owner.FlowScoreInput: {
        "etf_norm_5_zscore": _ownerless(
            "FLOW_Z_ETF_NORM_5D",
            _M_FLOW_CORE,
            (ETF_FLOW_FAMILY, MARKET_CLOSURE_FAMILY),
            (_FLOW,),
            note="ETF_NORM_5D has an owner; z(ETFNorm_5)'s normalisation window does not (Rulebook 6.2)",
        ),
        "etf_norm_20_zscore": _ownerless(
            "FLOW_Z_ETF_NORM_20D",
            _M_FLOW_CORE,
            (ETF_FLOW_FAMILY, MARKET_CLOSURE_FAMILY),
            (_FLOW,),
            note="ETF_NORM_20D has an owner; z(ETFNorm_20)'s normalisation window does not",
        ),
        "flow_accel_zscore": _ownerless(
            "FLOW_Z_FLOW_ACCEL",
            _M_FLOW_CORE,
            (ETF_FLOW_FAMILY, MARKET_CLOSURE_FAMILY),
            (_FLOW,),
            note="FLOW_ACCEL has an owner; z(FlowAccel)'s normalisation window does not",
        ),
        "cvd_spread_zscore": _absent(
            "CVD",
            (CVD_FAMILY,),
            "None -> FLOW_SCORE_P1_INPUT_MISSING and flow_model ETF_CORE (Rulebook 6.2 fallback)",
        ),
        "spot_dominance_zscore": _absent(
            "SPOT_DOMINANCE_ZSCORE",
            (SHARED_VOLUME_FAMILY, PERP_VOLUME_FAMILY),
            "None -> FLOW_SCORE_P1_INPUT_MISSING; with CVD absent ETF_CORE is selected either way",
            note="does not enter ETF_CORE; z(SpotDominance)'s normalisation window is also owner-less",
        ),
    },
    positioning_owner.PositioningScoreInput: {
        "funding_health": _derived(positioning_owner.funding_health, _M_POSITIONING, (FUNDING_RATE_FAMILY,), (_POSITIONING,)),
        "oi_health": _derived(
            positioning_owner.open_interest_growth_health, _M_POSITIONING, (OPEN_INTEREST_FAMILY,), (_POSITIONING,)
        ),
        "basis_health": _derived(
            positioning_owner.futures_basis_health, _M_POSITIONING, (FUTURES_BASIS_FAMILY,), (_POSITIONING,)
        ),
        "leverage_health": _derived(
            positioning_owner.open_interest_intensity,
            _M_POSITIONING,
            (OPEN_INTEREST_FAMILY, MARKET_CAP_FAMILY),
            (_POSITIONING,),
            note="the OI-intensity percentile health (Rulebook 7.3)",
        ),
    },
    positioning_owner.CrowdingFlagInput: {
        "funding_zscore": _derived(positioning_owner.funding_health, _M_CROWDING, (FUNDING_RATE_FAMILY,)),
        "basis_zscore": _derived(positioning_owner.futures_basis_health, _M_CROWDING, (FUTURES_BASIS_FAMILY,)),
        "oi_intensity_percentile": _derived(
            positioning_owner.open_interest_intensity, _M_CROWDING, (OPEN_INTEREST_FAMILY, MARKET_CAP_FAMILY)
        ),
    },
    volatility_owner.VolatilityCompressionRatioInput: {
        "rv_7": _derived(
            volatility_owner.realized_volatility_from_daily_bars,
            "None -> VOL_COMPRESSION_INPUT_MISSING; compression ratio None",
            _PRICE,
            (_VOLATILITY,),
        ),
        "rv_60": _derived(
            volatility_owner.realized_volatility_from_daily_bars,
            "None -> VOL_COMPRESSION_INPUT_MISSING; compression ratio None",
            _PRICE,
            (_VOLATILITY,),
        ),
    },
    volatility_owner.OrderlinessScoreInput: {
        "range_percentile": _ownerless(
            "RANGE_PERCENTILE",
            _M_ORDERLINESS,
            _PRICE,
            (_VOLATILITY,),
            note="no owner computes it and no certified definition exists (quantity, window and minimum all undefined)",
        ),
        "downside_return": _ownerless(
            "DOWNSIDE_RETURN",
            _M_ORDERLINESS,
            _PRICE,
            (_VOLATILITY,),
            note="no owner computes it and no certified definition exists (return horizon undefined)",
        ),
        "liquidation_percentile": _ownerless(
            "LIQUIDATION_PERCENTILE",
            _M_ORDERLINESS,
            (LIQUIDATION_FAMILY,),
            (_VOLATILITY,),
            certified=(
                f"{epic_x_corpus.PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_VERSION} (EPIC X corpus V1, by reference) "
                f"over {epic_x_corpus.LIQUIDATION_UTC_DAY_CENSUS_VERSION} days of "
                f"{epic_x_corpus.PROSPECTIVE_LIQUIDATION_CAPTURE_VERSION} {epic_x_corpus.LIQUIDATION_INSTRUMENT} liquidations"
            ),
        ),
        "volatility_percentile": _derived(volatility_owner.volatility_percentile, _M_ORDERLINESS, _PRICE, (_VOLATILITY,)),
    },
    volatility_owner.VolatilityScoreInput: {
        "compression_ratio": _derived(
            volatility_owner.volatility_compression_ratio_from_results, _M_VOLATILITY, _PRICE, (_VOLATILITY,)
        ),
        "orderliness_score": _derived(
            volatility_owner.calculate_orderliness_score, _M_VOLATILITY, _VOLATILITY_FAMILIES, (_VOLATILITY,)
        ),
        "volatility_percentile": _derived(
            volatility_owner.volatility_percentile,
            "None -> VOLATILITY_REGIME_UNKNOWN; the score itself is unaffected (diagnostic only)",
            _PRICE,
            (_VOLATILITY,),
        ),
    },
    volatility_owner.StressFlagInput: {
        "volatility_percentile": _derived(volatility_owner.volatility_percentile, _M_STRESS, _PRICE),
        "liquidation_percentile": _ownerless(
            "LIQUIDATION_PERCENTILE",
            _M_STRESS,
            (LIQUIDATION_FAMILY,),
            certified=epic_x_corpus.PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_VERSION,
        ),
        "downside_return": _ownerless("DOWNSIDE_RETURN", _M_STRESS, _PRICE),
        "funding_zscore": _derived(positioning_owner.funding_health, _M_STRESS, (FUNDING_RATE_FAMILY,)),
        "basis_zscore": _derived(positioning_owner.futures_basis_health, _M_STRESS, (FUTURES_BASIS_FAMILY,)),
        "systemic_shock": _discretionary(
            "SYSTEMIC_SHOCK",
            _M_STRESS + "; never asserted, so STRESS is never complete",
        ),
    },
    volatility_owner.CapitulationFlagInput: {
        "range_percentile": _ownerless("RANGE_PERCENTILE", _M_CAPITULATION, _PRICE),
        "downside_return": _ownerless("DOWNSIDE_RETURN", _M_CAPITULATION, _PRICE),
        "liquidation_percentile": _ownerless(
            "LIQUIDATION_PERCENTILE",
            _M_CAPITULATION,
            (LIQUIDATION_FAMILY,),
            certified=epic_x_corpus.PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_VERSION,
        ),
        "volatility_percentile": _derived(volatility_owner.volatility_percentile, _M_CAPITULATION, _PRICE),
        "funding_zscore": _derived(positioning_owner.funding_health, _M_CAPITULATION, (FUNDING_RATE_FAMILY,)),
        "systemic_shock": _discretionary(
            "SYSTEMIC_SHOCK",
            _M_CAPITULATION + "; never asserted, so CAPITULATION is never complete",
        ),
    },
    volatility_owner.EuphoriaFlagInput: {
        "range_percentile": _ownerless("RANGE_PERCENTILE", _M_EUPHORIA, _PRICE),
        "upside_return": _ownerless(
            "UPSIDE_RETURN",
            _M_EUPHORIA,
            _PRICE,
            note="no owner computes it and no certified definition exists (return horizon undefined)",
        ),
        "funding_zscore": _derived(positioning_owner.funding_health, _M_EUPHORIA, (FUNDING_RATE_FAMILY,)),
        "basis_zscore": _derived(positioning_owner.futures_basis_health, _M_EUPHORIA, (FUTURES_BASIS_FAMILY,)),
        "oi_intensity_percentile": _derived(
            positioning_owner.open_interest_intensity, _M_EUPHORIA, (OPEN_INTEREST_FAMILY, MARKET_CAP_FAMILY)
        ),
        "volatility_percentile": _derived(volatility_owner.volatility_percentile, _M_EUPHORIA, _PRICE),
        "systemic_euphoria": _discretionary(
            "SYSTEMIC_EUPHORIA",
            _M_EUPHORIA + "; never asserted, so EUPHORIA is never complete",
        ),
    },
    structure_owner.StructureScoreInput: {
        "level_strength": _derived(
            strength_owner.calculate_level_strength_from_cluster,
            _M_STRUCTURE,
            _PRICE_VOLUME,
            (_STRUCTURE,),
            note="incomplete while LevelStrengthInput.reaction_magnitude_fraction or volume_percentile is None",
        ),
        "entry_location": _derived(
            structure_owner.calculate_structure_score_from_clusters, _M_STRUCTURE, _PRICE_VOLUME, (_STRUCTURE,)
        ),
        "rr_quality": _derived(
            structure_owner.calculate_structure_score_from_clusters,
            "diagnostic under STRUCTURE_SCORE_V1_2: None never makes the score incomplete",
            _PRICE_VOLUME,
        ),
        "confluence": _derived(
            clustering_owner.cluster_price_levels,
            "diagnostic under STRUCTURE_SCORE_V1_2: None never makes the score incomplete",
            _PRICE_VOLUME,
        ),
    },
    strength_owner.LevelStrengthInput: {
        "timeframes": _derived(clustering_owner.cluster_price_levels, _M_LEVEL_STRENGTH, _PRICE, (_STRUCTURE,)),
        "touch_count": _derived(
            strength_owner.calculate_level_strength_from_cluster,
            _M_LEVEL_STRENGTH,
            _PRICE,
            (_STRUCTURE,),
            note="defaults to the cluster member_count when the caller passes None",
        ),
        "reaction_magnitude_fraction": _ownerless(
            "LEVEL_REACTION_MAGNITUDE",
            _M_LEVEL_STRENGTH,
            _PRICE,
            (_STRUCTURE,),
            note="no owner measures it (Rulebook 9.2: f(ReactionMagnitude/ATR), undefined)",
        ),
        "volume_percentile": _level_volume_fallback(),
        "confluence_score": _derived(clustering_owner.cluster_price_levels, _M_LEVEL_STRENGTH, _PRICE, (_STRUCTURE,)),
    },
    # -- core regime --------------------------------------------------------------------
    regime_owner.RegimeScoreInput: {
        "trend_score": _derived(trend_owner.calculate_trend_score, _M_REGIME, _PRICE, (_TREND,)),
        "flow_score": _derived(flow_owner.calculate_flow_score, _M_REGIME, (ETF_FLOW_FAMILY, MARKET_CLOSURE_FAMILY), (_FLOW,)),
        "volatility_score": _derived(
            volatility_owner.calculate_volatility_score, _M_REGIME, _VOLATILITY_FAMILIES, (_VOLATILITY,)
        ),
        "positioning_score": _derived(
            positioning_owner.calculate_positioning_score, _M_REGIME, _POSITIONING_FAMILIES, (_POSITIONING,)
        ),
        "macro_score": _absent(
            "MACRO",
            (MACRO_ONCHAIN_LIQUIDITY_FAMILY,),
            "None -> REGIME_SCORE_P1_INPUT_MISSING; core regime fallback CORE_MARKET_ONLY",
        ),
        "onchain_score": _absent(
            "ONCHAIN",
            (MACRO_ONCHAIN_LIQUIDITY_FAMILY,),
            "None -> REGIME_SCORE_P1_INPUT_MISSING; core regime fallback CORE_MARKET_ONLY",
        ),
        "liquidity_score": _absent(
            "LIQUIDITY",
            (MACRO_ONCHAIN_LIQUIDITY_FAMILY,),
            "None -> REGIME_SCORE_P1_INPUT_MISSING; core regime fallback CORE_MARKET_ONLY",
        ),
    },
    regime_owner.RegimeSmoothingInput: {
        "previous_smoothed_score": _state(
            "the previous decision's REGIME_SMOOTHED_SCORE",
            "None -> REGIME_SMOOTHING_PREVIOUS_SCORE_MISSING; initialised from the current score",
            source=_SRC_LEDGER,
        ),
        "new_regime_score": _derived(
            regime_owner.calculate_regime_score,
            "None -> REGIME_SMOOTHING_NEW_SCORE_MISSING; smoothed score None",
            _REGIME_FAMILIES,
        ),
    },
    # -- setups -----------------------------------------------------------------------------
    setup_owner.BullTrendContinuationInput: {
        "regime_score": _derived(regime_owner.calculate_regime_smoothing, _M_SETUP, _REGIME_FAMILIES),
        "trend_score": _derived(trend_owner.calculate_trend_score, _M_SETUP, _PRICE),
        "flow_score": _derived(flow_owner.calculate_flow_score, _M_SETUP, (ETF_FLOW_FAMILY, MARKET_CLOSURE_FAMILY)),
        "positioning_score": _derived(positioning_owner.calculate_positioning_score, _M_SETUP, _POSITIONING_FAMILIES),
        "structure_score": _derived(structure_owner.calculate_structure_score_from_clusters, _M_SETUP, _PRICE_VOLUME),
        "stress_flagged": _derived(volatility_owner.calculate_stress_flag, _M_SETUP, _VOLATILITY_FAMILIES),
        "severe_crowding_flagged": _ownerless(
            "SEVERE_CROWDING_STATE",
            _M_SETUP,
            _POSITIONING_FAMILIES,
            note="the CROWDING owner has no severity grade; 'severe' is undefined",
        ),
        "risk_reward": _derived(reward_owner.reward_risk_for_stop, _M_SETUP, _PRICE),
    },
    setup_owner.BullishResetInput: {
        "regime_score": _derived(regime_owner.calculate_regime_smoothing, _M_SETUP, _REGIME_FAMILIES),
        "trend_score": _derived(trend_owner.calculate_trend_score, _M_SETUP, _PRICE),
        "correction_from_local_high_fraction": _ownerless(
            "CORRECTION_FROM_LOCAL_HIGH",
            _M_SETUP,
            _PRICE,
            note="no owner defines the local high or its lookback",
        ),
        "funding_health_history": _derived(
            positioning_owner.funding_health, _M_SETUP, (FUNDING_RATE_FAMILY,), source=_SRC_LEDGER
        ),
        "oi_health_history": _derived(
            positioning_owner.open_interest_growth_health, _M_SETUP, (OPEN_INTEREST_FAMILY,), source=_SRC_LEDGER
        ),
        "flow_accel_history": _derived(
            flow_owner.etf_flow_acceleration, _M_SETUP, (ETF_FLOW_FAMILY, MARKET_CLOSURE_FAMILY), source=_SRC_LEDGER
        ),
        "structure_score": _derived(structure_owner.calculate_structure_score_from_clusters, _M_SETUP, _PRICE_VOLUME),
        "entry_trigger_confirmed": _derived(reclaim_owner.evaluate_reclaim_trigger, _M_SETUP, _PRICE),
        "entry_conviction_score": _derived(entry_owner.calculate_entry_conviction, _M_SETUP, _ALL_COMPONENT_FAMILIES),
        "risk_reward": _derived(reward_owner.reward_risk_for_stop, _M_SETUP, _PRICE),
    },
    setup_owner.CapitulationReversalInput: {
        "capitulation_flagged": _derived(volatility_owner.calculate_capitulation_flag, _M_SETUP, _VOLATILITY_FAMILIES),
        "capitulation_detected_at": _state(
            "the decision instant the CAPITULATION flag was first raised",
            _M_SETUP,
            source=_SRC_LEDGER,
            role=ROLE_OBSERVATION_TIME,
        ),
        "confirmation_triggered": _derived(higher_low_owner.evaluate_higher_low_trigger, _M_SETUP, _PRICE),
        "confirmation_at": _state(
            "the decision instant the confirmation trigger fired",
            _M_SETUP,
            source=_SRC_LEDGER,
            role=ROLE_OBSERVATION_TIME,
        ),
        "structure_score": _derived(structure_owner.calculate_structure_score_from_clusters, _M_SETUP, _PRICE_VOLUME),
        "entry_conviction_score": _derived(entry_owner.calculate_entry_conviction, _M_SETUP, _ALL_COMPONENT_FAMILIES),
        "risk_reward": _derived(reward_owner.reward_risk_for_stop, _M_SETUP, _PRICE),
    },
    setup_owner.BearishDistributionInput: {
        "regime_score": _derived(regime_owner.calculate_regime_smoothing, _M_SETUP, _REGIME_FAMILIES),
        "trend_score": _derived(trend_owner.calculate_trend_score, _M_SETUP, _PRICE),
        "flow_score": _derived(flow_owner.calculate_flow_score, _M_SETUP, (ETF_FLOW_FAMILY, MARKET_CLOSURE_FAMILY)),
        "positioning_score": _derived(positioning_owner.calculate_positioning_score, _M_SETUP, _POSITIONING_FAMILIES),
        "structure_score": _derived(structure_owner.calculate_structure_score_from_clusters, _M_SETUP, _PRICE_VOLUME),
        "entry_conviction_score": _derived(entry_owner.calculate_entry_conviction, _M_SETUP, _ALL_COMPONENT_FAMILIES),
        "risk_reward": _derived(reward_owner.reward_risk_for_stop, _M_SETUP, _PRICE),
        "distribution_flagged": _ownerless(
            "DISTRIBUTION_STATE",
            _M_SETUP,
            _PRICE,
            note="inert for the champion: the engine refuses short intents (backtest.allow_short_trades = false)",
        ),
        "short_trigger_confirmed": _ownerless(
            "SHORT_TRIGGER",
            _M_SETUP,
            _PRICE,
            note="inert for the champion: the engine refuses short intents (backtest.allow_short_trades = false)",
        ),
        "stress_flagged": _derived(volatility_owner.calculate_stress_flag, _M_SETUP, _VOLATILITY_FAMILIES),
    },
    # -- hard vetoes ---------------------------------------------------------------------
    hard_veto_owner.HardVetoInput: {
        "data_quality_fail": _derived(
            data_quality_gate_owner.failures_from_quality_reports,
            _M_VETO,
            (REFERENCE_PRICE_FAMILY, FUNDING_RATE_FAMILY, OPEN_INTEREST_FAMILY, PERP_VOLUME_FAMILY),
            note="from the BTC-031 OHLCV and derivatives quality reports over the visible prefix",
        ),
        "valid_structural_stop": _derived(stop_owner.initial_stop_for_setup, _M_VETO, _PRICE),
        "reward_risk_passes": _derived(reward_owner.reward_risk_for_stop, _M_VETO, _PRICE),
        "stress_flagged": _derived(
            volatility_owner.calculate_stress_flag,
            _M_VETO,
            _VOLATILITY_FAMILIES,
            note=(
                "STRESS is never complete (systemic_shock is DISCRETIONARY); no owner maps an "
                "incomplete StressFlagResult to this bool"
            ),
        ),
        "severe_crowding_flagged": _ownerless(
            "SEVERE_CROWDING_STATE",
            _M_VETO,
            _POSITIONING_FAMILIES,
            note="the CROWDING owner has no severity grade; 'severe' is undefined",
        ),
        "no_chase_blocked": _derived(no_chase_owner.apply_no_chase_filter, _M_VETO, _PRICE),
        "setup": _derived(
            setup_owner.detect_bull_trend_continuation,
            "None -> HARD_VETO_UNSUPPORTED_SETUP (no recognised setup)",
            _ALL_COMPONENT_FAMILIES,
            note="the setup detectors of features.setup",
        ),
        "source_reason_codes": _state(
            "upstream owner reason codes",
            "empty mapping allowed; evidence only",
            role=ROLE_PROVENANCE,
            source=_SRC_UPSTREAM,
        ),
    },
    # -- lifecycle, add, trim and exit --------------------------------------------------
    hold_owner.HoldScoreInput: {
        "trend_score": _derived(trend_owner.calculate_trend_score, _M_HOLD, _PRICE),
        "flow_score": _derived(flow_owner.calculate_flow_score, _M_HOLD, (ETF_FLOW_FAMILY, MARKET_CLOSURE_FAMILY)),
        "positioning_score": _derived(positioning_owner.calculate_positioning_score, _M_HOLD, _POSITIONING_FAMILIES),
        "structure_score": _derived(structure_owner.calculate_structure_score_from_clusters, _M_HOLD, _PRICE_VOLUME),
        "momentum_persistence_score": _ownerless(
            "MOMENTUM_PERSISTENCE_SCORE",
            _M_HOLD,
            _PRICE,
            note="the Hold owner takes an explicitly normalised component and no owner produces it",
        ),
    },
    add_owner.AddScoreInput: {
        "new_structure_score": _ownerless("NEW_STRUCTURE_SCORE", _M_ADD_SCORE, _PRICE),
        "flow_score": _derived(flow_owner.calculate_flow_score, _M_ADD_SCORE, (ETF_FLOW_FAMILY, MARKET_CLOSURE_FAMILY)),
        "positioning_score": _derived(positioning_owner.calculate_positioning_score, _M_ADD_SCORE, _POSITIONING_FAMILIES),
        "momentum_score": _ownerless("ADD_MOMENTUM_SCORE", _M_ADD_SCORE, _PRICE),
        "risk_improvement_score": _derived(add_owner.risk_improvement_component_score, _M_ADD_SCORE, _PRICE),
    },
    add_requirements_owner.AddRequirementsInput: {
        "position_profitable": _state(
            "btc_predictor.portfolio.state_machine.position_is_profitable_at_price (BTC-150 ledger)",
            _M_ADD_REQ,
        ),
        "new_structural_confirmation": _ownerless(
            "NEW_STRUCTURAL_CONFIRMATION",
            _M_ADD_REQ,
            _PRICE,
            note="Rulebook 18.1(2) 'new bullish structure has formed' is not defined by any owner",
        ),
        "signed_risk_improvement": _derived(add_owner.risk_improvement_component_score, _M_ADD_REQ, _PRICE),
        "regime_supportive": _ownerless(
            "REGIME_SUPPORTIVE_PREDICATE",
            _M_ADD_REQ,
            _REGIME_FAMILIES,
            note="Rulebook 18.1(4) 'regime remains supportive' has no owner threshold",
        ),
        "flow_supportive": _ownerless(
            "FLOW_SUPPORTIVE_PREDICATE",
            _M_ADD_REQ,
            (ETF_FLOW_FAMILY, MARKET_CLOSURE_FAMILY),
            note="Rulebook 18.1(5) 'flow remains supportive' has no owner threshold",
        ),
        "positioning_healthy": _derived(
            positioning_owner.calculate_crowding_flag,
            _M_ADD_REQ,
            _POSITIONING_FAMILIES,
            note="Rulebook 18.1(6) 'positioning is not crowded': not CROWDING.flagged (BTC-222 notes)",
        ),
        "add_score": _derived(add_owner.calculate_add_score, _M_ADD_REQ, _ALL_COMPONENT_FAMILIES),
        "projected_risk_at_stop_within_maximum": _derived(exposure_owner.calculate_risk_at_stop, _M_ADD_REQ, _PRICE),
        "source_reason_codes": _state("upstream owner reason codes", "evidence only", role=ROLE_PROVENANCE, source=_SRC_UPSTREAM),
    },
    trim_owner.TrimRuleInput: {
        "position_open": _state("BTC-150 PositionLifecycle.is_open", _M_TRIM),
        "hold_score": _derived(hold_owner.calculate_hold_score, _M_TRIM, _ALL_COMPONENT_FAMILIES),
        "euphoria_active": _derived(
            volatility_owner.calculate_euphoria_flag,
            _M_TRIM,
            _VOLATILITY_FAMILIES + _POSITIONING_FAMILIES,
            note="trim_rules_from_results passes EUPHORIA.flagged only when complete: always None while systemic_euphoria is DISCRETIONARY",
        ),
        "crowding_active": _derived(positioning_owner.calculate_crowding_flag, _M_TRIM, _POSITIONING_FAMILIES),
        "current_flow_score": _derived(flow_owner.calculate_flow_score, _M_TRIM, (ETF_FLOW_FAMILY, MARKET_CLOSURE_FAMILY)),
        "prior_flow_score": _derived(
            flow_owner.calculate_flow_score, _M_TRIM, (ETF_FLOW_FAMILY, MARKET_CLOSURE_FAMILY), source=_SRC_LEDGER
        ),
        "source_reason_codes": _state("upstream owner reason codes", "evidence only", role=ROLE_PROVENANCE, source=_SRC_UPSTREAM),
    },
    exit_rules_owner.ExitRuleInput: {
        "position_open": _state("BTC-150 PositionLifecycle.is_open", _M_EXIT),
        "direction": _state("BTC-150 PositionLifecycle.direction", _M_EXIT),
        "standing_stop": _state("BTC-150 PositionLifecycle.stop_price", _M_EXIT),
        "current_price": _raw(
            _PRICE,
            SHAPE_INTERVAL,
            ROLE_VALUE,
            _SRC_OHLCV,
            _M_EXIT,
            note="the replay bar's direction-appropriate extreme (structural_stop_triggered)",
        ),
        "hold_score": _derived(hold_owner.calculate_hold_score, _M_EXIT, _ALL_COMPONENT_FAMILIES),
        "regime_invalidated": _ownerless(
            "REGIME_INVALIDATION_PREDICATE",
            _M_EXIT,
            _REGIME_FAMILIES,
            note="Rulebook 20/26 REGIME_INVALIDATION has no owner threshold",
        ),
        "data_risk_exit_required": _ownerless(
            "DATA_RISK_EXIT_PREDICATE",
            _M_EXIT,
            (REFERENCE_PRICE_FAMILY,),
            note="no owner defines when data risk forces an exit (DATA_QUALITY_FAIL is not a forced liquidation)",
        ),
        "manual_research_override": _discretionary(
            "MANUAL_RESEARCH_OVERRIDE",
            _M_EXIT + "; never asserted in a replay",
        ),
        "manual_override_reason": _discretionary(
            "MANUAL_RESEARCH_OVERRIDE",
            "None allowed; required only with an asserted override",
        ),
        "source_reason_codes": _state("upstream owner reason codes", "evidence only", role=ROLE_PROVENANCE, source=_SRC_UPSTREAM),
    },
    trailing_owner.ConfirmedTrailingStructure: {
        name: _derived(
            "btc_predictor.levels.swing / btc_predictor.signals.higher_low (mapped by the RBT-005 composer, no formula)",
            "no confirmed structure -> trail_stop_for_position keeps the standing stop (structure=None)",
            _PRICE,
            role=role,
        )
        for name, role in (
            ("structure_id", ROLE_IDENTITY),
            ("source_feature_id", ROLE_PROVENANCE),
            ("direction", ROLE_IDENTITY),
            ("structure_type", ROLE_IDENTITY),
            ("price", ROLE_VALUE),
            ("level_timestamp", ROLE_OBSERVATION_TIME),
            ("detected_at", ROLE_AVAILABILITY),
            ("config_metadata", ROLE_PROVENANCE),
            ("reason_codes", ROLE_PROVENANCE),
        )
    },
}
_SWING_LEVEL_PRODUCERS = (
    "btc_predictor.levels.swing.detect_weekly_swing_levels / detect_monthly_swing_levels "
    "(WeeklySwingLevel and MonthlySwingLevel satisfy the protocol)"
)
_M_CAPITULATION_EVENT = (
    "no CapitulationEvent -> the composer builds no capitulation-event AVWAP anchor; the swing and breakout anchors "
    "and every other level still evaluate (nothing is zero-filled)"
)
_CAPITULATION_EVENT_NOTE = (
    "no owner produces a CapitulationEvent: BTC-093 implements 'capitulation anchors use explicit event metadata' "
    "supplied by the caller, the CAPITULATION flag owner returns a flag, not an event instant, price or detection "
    "time, and Rulebook 9.1 names 'Anchored VWAPs from important market events' without defining the event. AVWAP "
    "confluence is an optional Phase 1 enhancement (Rulebook 9.2; BTC-097 'must not be required for the Phase 1 "
    "score'), so the spec may define or explicitly omit this anchor; it must not be inferred. When included, its "
    "AVWAP enters cluster confluence, LevelStrength and the Structure Score. Optionality does not remove that dataflow."
)


def _capitulation_event_field(role: str) -> InputClassification:
    return dataclasses.replace(
        _ownerless("CAPITULATION_EVENT", _M_CAPITULATION_EVENT, _PRICE, (_STRUCTURE,), note=_CAPITULATION_EVENT_NOTE),
        role=role,
    )


INPUT_TYPE_FIELD_CLASSIFICATIONS: dict[str, dict[str, InputClassification]] = {
    **{_owner_path(owner): fields for owner, fields in _INPUT_TYPE_FIELDS.items()},
    # The anchored-VWAP owner's market-event anchor input (root
    # anchored_vwap_anchor_from_capitulation_event); the composer would build it.
    "btc_predictor.levels.anchored_vwap.CapitulationEvent": {
        "event_timestamp": _capitulation_event_field(ROLE_OBSERVATION_TIME),
        "detected_at": _capitulation_event_field(ROLE_AVAILABILITY),
        "price": _capitulation_event_field(ROLE_VALUE),
        "exchange": _capitulation_event_field(ROLE_IDENTITY),
        "symbol": _capitulation_event_field(ROLE_IDENTITY),
        "provider": _capitulation_event_field(ROLE_IDENTITY),
        "reason_codes": _capitulation_event_field(ROLE_PROVENANCE),
    },
    # The breakout owner's structural view of its source levels.
    "btc_predictor.levels.breakout.SourceLevel": {
        name: _derived(
            _SWING_LEVEL_PRODUCERS,
            "no source levels -> no breakout/reclaim level is detected",
            _PRICE,
            (_STRUCTURE,),
            role=role,
        )
        for name, role in (
            ("feature_id", ROLE_PROVENANCE),
            ("level_type", ROLE_IDENTITY),
            ("level_timestamp", ROLE_OBSERVATION_TIME),
            ("detected_at", ROLE_AVAILABILITY),
            ("price", ROLE_VALUE),
            ("exchange", ROLE_IDENTITY),
            ("symbol", ROLE_IDENTITY),
            ("provider", ROLE_IDENTITY),
        )
    },
}
OWNER_INPUT_TYPES: tuple[str, ...] = tuple(INPUT_TYPE_FIELD_CLASSIFICATIONS)


# --- call-site parameters --------------------------------------------------------

_P_INSTANT = _state(
    "the composer's decision instant",
    "required argument; every owner filters its records to available_at <= instant",
    role=ROLE_OBSERVATION_TIME,
)
_P_CONFIG = _config()
_P_META = _config("strategy config identity metadata (config_version, strategy_version, parameter_set_id)")
_P_STRATEGY_CONFIG = _config("the frozen champion StrategyConfig")
_P_DAILY = _derived(
    "btc_predictor.data.build_canonical_market_bars",
    "an underived bucket is absent; owners read the remaining bars (policy V3 section 7 limitation)",
    _PRICE,
    (_TREND, _VOLATILITY, _STRUCTURE),
    source=_SRC_DERIVED_BARS,
    note="1d canonical bars",
)
_P_WEEKLY = dataclasses.replace(_P_DAILY, note="1w canonical bars (Monday 00:00 UTC)")
_P_MONTHLY = dataclasses.replace(_P_DAILY, note="1mo canonical bars")
_P_HOURLY_VENUE = _raw(
    _PRICE,
    SHAPE_INTERVAL,
    ROLE_VALUE,
    _SRC_OHLCV,
    "a missing hour is a gap, never filled",
    (_STRUCTURE,),
    note="the venue's 1h replay bars",
)
_P_HOURLY_VOLUME = _raw(
    (SHARED_VOLUME_FAMILY,),
    SHAPE_INTERVAL,
    ROLE_VALUE,
    _SRC_OHLCV,
    "no visible spot bars -> SPOT_VOLUME_INPUT_MISSING",
    note="Bitstamp raw OHLCV shared by all three runs (policy section 2)",
)
_P_LIFECYCLE = _state("BTC-150 PositionLifecycle", "required; a closed lifecycle resolves its inputs to None (fail closed)")
_P_NAV = _state("the replay account NAV", "required argument")
_P_CURRENT_PRICE = dataclasses.replace(_P_HOURLY_VENUE, entry_components=(), note="the replay bar price at the decision")


def _up(owner: Any, missing: str, families: tuple[str, ...], components: tuple[str, ...] = (), **kwargs: Any) -> InputClassification:
    return _derived(owner, missing, families, components, **kwargs)


# Every parameter of every root (input_census.DECISION_PATH_ROOTS): the values
# the RBT-004/RBT-005 composer supplies. The enumeration requires these keys to
# be exactly the census roots and each signature to match.
_ROOT_CALL_SITES: tuple[tuple[Callable[..., Any], dict[str, InputClassification]], ...] = (
    # trend
    (momentum_owner.four_week_momentum_from_daily_bars, {"bars": _P_DAILY}),
    (momentum_owner.twelve_week_momentum_from_daily_bars, {"bars": _P_DAILY}),
    (trend_owner.twenty_week_ma_distance_from_weekly_bars, {"bars": _P_WEEKLY}),
    (trend_owner.fifty_two_week_high_distance_from_weekly_bars, {"bars": _P_WEEKLY}),
    (trend_owner.classify_weekly_structure_from_weekly_bars, {"bars": _P_WEEKLY}),
    (trend_owner.calculate_trend_score, {"inputs": _up(trend_owner.TrendScoreInput, _M_TREND_REQUIRED, _PRICE, (_TREND,)), "weights": _P_CONFIG}),
    # flow
    *(
        (
            function,
            {
                "flows": _raw(
                    (ETF_FLOW_FAMILY,),
                    SHAPE_DAILY_PUBLISHED,
                    ROLE_VALUE,
                    _SRC_ETF,
                    "a missing (fund, date) row -> ETF_FLOW_INPUT_MISSING; missing AUM -> ETF_FLOW_AUM_MISSING",
                    (_FLOW,),
                ),
                "as_of": _P_INSTANT,
                "funds": _state(
                    "the ETF fund universe the composer passes (empty = every fund visible)",
                    "empty tuple: the owner uses every fund present in the visible rows",
                    source="RBT-003 source plan and the composer",
                    note="fund launches inside a window interact with this universe (see the ETF fund-universe blocker)",
                ),
                "market_holidays": _raw(
                    (MARKET_CLOSURE_FAMILY,),
                    SHAPE_DAILY_PUBLISHED,
                    ROLE_VALUE,
                    _SRC_CLOSURES,
                    "the empty default treats a closure as a publication date -> ETF_FLOW_INPUT_MISSING",
                    (_FLOW,),
                ),
                "end_date": _state("optional explicit window end", "None -> the latest visible observation date"),
            },
        )
        for function in (flow_owner.five_day_etf_flow, flow_owner.twenty_day_etf_flow)
    ),
    (
        flow_owner.etf_flow_acceleration,
        {
            "five_day_flow": _up(flow_owner.five_day_etf_flow, "incomplete -> ETF_FLOW_ACCEL_INPUT_MISSING", (ETF_FLOW_FAMILY,), (_FLOW,)),
            "twenty_day_flow": _up(flow_owner.twenty_day_etf_flow, "incomplete -> ETF_FLOW_ACCEL_INPUT_MISSING", (ETF_FLOW_FAMILY,), (_FLOW,)),
        },
    ),
    (
        flow_owner.spot_perp_participation_from_rows,
        {
            "spot_bars": _P_HOURLY_VOLUME,
            "perp_volumes": _raw(
                (PERP_VOLUME_FAMILY,),
                SHAPE_INTERVAL,
                ROLE_VALUE,
                _SRC_PERP,
                "no visible perp rows -> PERP_VOLUME_INPUT_MISSING",
            ),
            "as_of": _P_INSTANT,
            "growth_window_periods": _P_CONFIG,
            "zscore_window_periods": _P_CONFIG,
            "min_zscore_periods": _P_CONFIG,
        },
    ),
    (
        flow_owner.spot_perp_cvd_spread,
        {
            "observations": _absent("CVD", (CVD_FAMILY,), "no observations -> SPOT_PERP_CVD_SPREAD_INSUFFICIENT_HISTORY"),
            "as_of": _P_INSTANT,
            "zscore_window_periods": _P_CONFIG,
            "min_zscore_periods": _P_CONFIG,
        },
    ),
    (
        flow_owner.calculate_flow_score,
        {
            "inputs": _up(flow_owner.FlowScoreInput, _M_FLOW_CORE, (ETF_FLOW_FAMILY,), (_FLOW,)),
            "core_weights": _P_CONFIG,
            "full_weights": _P_CONFIG,
            "config_metadata": _P_META,
        },
    ),
    # positioning
    (
        positioning_owner.funding_health,
        {
            "funding_rates": _raw(
                (FUNDING_RATE_FAMILY,),
                SHAPE_SETTLEMENT,
                ROLE_VALUE,
                _SRC_FUNDING,
                "no visible rows -> FUNDING_RATE_INPUT_MISSING",
                (_POSITIONING,),
            ),
            "as_of": _P_INSTANT,
            "average_window_days": _P_CONFIG,
            "zscore_window_days": _P_CONFIG,
            "min_zscore_observations": _P_CONFIG,
            "preferred_zscore": _P_CONFIG,
            "zscore_width": _P_CONFIG,
        },
    ),
    (
        positioning_owner.futures_basis_health,
        {
            "futures_basis_rows": _raw(
                (FUTURES_BASIS_FAMILY,),
                SHAPE_SNAPSHOT,
                ROLE_VALUE,
                _SRC_BASIS,
                "no visible rows -> FUTURES_BASIS_INPUT_MISSING",
                (_POSITIONING,),
            ),
            "as_of": _P_INSTANT,
            "zscore_window_days": _P_CONFIG,
            "min_zscore_observations": _P_CONFIG,
            "preferred_basis_zscore": _P_CONFIG,
            "basis_zscore_width": _P_CONFIG,
        },
    ),
    (
        positioning_owner.open_interest_growth_health,
        {
            "open_interest_rows": _raw(
                (OPEN_INTEREST_FAMILY,),
                SHAPE_SNAPSHOT,
                ROLE_VALUE,
                _SRC_OI,
                "no visible rows -> OI_GROWTH_INPUT_MISSING",
                (_POSITIONING,),
            ),
            "as_of": _P_INSTANT,
            "open_interest_unit": _config("the pinned OI unit (RBT-002 pins USD)"),
            "growth_window_days": _P_CONFIG,
            "zscore_window_days": _P_CONFIG,
            "min_zscore_observations": _P_CONFIG,
            "preferred_growth_zscore": _P_CONFIG,
            "growth_zscore_width": _P_CONFIG,
        },
    ),
    (
        positioning_owner.open_interest_intensity,
        {
            "open_interest_rows": _raw(
                (OPEN_INTEREST_FAMILY,),
                SHAPE_SNAPSHOT,
                ROLE_VALUE,
                _SRC_OI,
                "no visible rows -> OI_INTENSITY_OI_INPUT_MISSING",
                (_POSITIONING,),
            ),
            "market_caps": _raw(
                (MARKET_CAP_FAMILY,),
                SHAPE_DAILY_PUBLISHED,
                ROLE_VALUE,
                _SRC_MARKET_CAP,
                "no market cap at an OI instant -> OI_INTENSITY_MARKET_CAP_INPUT_MISSING",
                (_POSITIONING,),
            ),
            "as_of": _P_INSTANT,
            "open_interest_unit": _config("the pinned OI unit (RBT-002 pins USD)"),
            "percentile_window_days": _P_CONFIG,
            "min_percentile_observations": _P_CONFIG,
        },
    ),
    (
        positioning_owner.calculate_positioning_score,
        {
            "inputs": _up(positioning_owner.PositioningScoreInput, _M_POSITIONING, _POSITIONING_FAMILIES, (_POSITIONING,)),
            "weights": _P_CONFIG,
            "config_metadata": _P_META,
        },
    ),
    (
        positioning_owner.calculate_crowding_flag,
        {
            "inputs": _up(positioning_owner.CrowdingFlagInput, _M_CROWDING, _POSITIONING_FAMILIES),
            "funding_zscore_min": _P_CONFIG,
            "basis_zscore_min": _P_CONFIG,
            "oi_intensity_percentile_min": _P_CONFIG,
            "entry_quality_penalty": _P_CONFIG,
            "config_metadata": _P_META,
        },
    ),
    # volatility and flags
    (
        volatility_owner.realized_volatility_from_daily_bars,
        {"bars": _P_DAILY, "as_of": _P_INSTANT, "window_days": _P_CONFIG, "annualization_periods": _P_CONFIG},
    ),
    (
        volatility_owner.volatility_percentile,
        {
            "results": _up(volatility_owner.realized_volatility_from_daily_bars, "no RV results -> VOL_PERCENTILE_INPUT_MISSING", _PRICE, (_VOLATILITY,)),
            "as_of": _P_INSTANT,
            "source_feature_id": _P_CONFIG,
            "percentile_window_days": _P_CONFIG,
            "min_percentile_observations": _P_CONFIG,
        },
    ),
    (
        volatility_owner.volatility_compression_ratio_from_results,
        {"results": _up(volatility_owner.realized_volatility_from_daily_bars, "missing RV -> VOL_COMPRESSION_INPUT_MISSING", _PRICE, (_VOLATILITY,))},
    ),
    (
        volatility_owner.calculate_orderliness_score,
        {
            "inputs": _up(volatility_owner.OrderlinessScoreInput, _M_ORDERLINESS, _VOLATILITY_FAMILIES, (_VOLATILITY,)),
            "weights": _P_CONFIG,
            "range_percentile_max": _P_CONFIG,
            "downside_return_min": _P_CONFIG,
            "liquidation_percentile_max": _P_CONFIG,
            "volatility_percentile_max": _P_CONFIG,
            "config_metadata": _P_META,
        },
    ),
    (
        volatility_owner.calculate_volatility_score,
        {
            "inputs": _up(volatility_owner.VolatilityScoreInput, _M_VOLATILITY, _VOLATILITY_FAMILIES, (_VOLATILITY,)),
            "weights": _P_CONFIG,
            "full_score_ratio": _P_CONFIG,
            "zero_score_ratio": _P_CONFIG,
            "compressed_percentile_max": _P_CONFIG,
            "normal_percentile_max": _P_CONFIG,
            "elevated_percentile_max": _P_CONFIG,
            "disorderly_score_max": _P_CONFIG,
            "config_metadata": _P_META,
        },
    ),
    (
        volatility_owner.calculate_stress_flag,
        {
            "inputs": _up(volatility_owner.StressFlagInput, _M_STRESS, _VOLATILITY_FAMILIES),
            "volatility_percentile_min": _P_CONFIG,
            "liquidation_percentile_min": _P_CONFIG,
            "downside_return_min": _P_CONFIG,
            "funding_abs_zscore_min": _P_CONFIG,
            "basis_abs_zscore_min": _P_CONFIG,
            "max_exposure_multiplier": _P_CONFIG,
            "block_new_trades": _P_CONFIG,
            "config_metadata": _P_META,
        },
    ),
    (
        volatility_owner.calculate_capitulation_flag,
        {
            "inputs": _up(volatility_owner.CapitulationFlagInput, _M_CAPITULATION, _VOLATILITY_FAMILIES),
            "range_percentile_min": _P_CONFIG,
            "downside_return_min": _P_CONFIG,
            "liquidation_percentile_min": _P_CONFIG,
            "volatility_percentile_min": _P_CONFIG,
            "funding_zscore_max": _P_CONFIG,
            "config_metadata": _P_META,
        },
    ),
    (
        volatility_owner.calculate_euphoria_flag,
        {
            "inputs": _up(volatility_owner.EuphoriaFlagInput, _M_EUPHORIA, _VOLATILITY_FAMILIES + _POSITIONING_FAMILIES),
            "range_percentile_min": _P_CONFIG,
            "upside_return_min": _P_CONFIG,
            "funding_zscore_min": _P_CONFIG,
            "basis_zscore_min": _P_CONFIG,
            "oi_intensity_percentile_min": _P_CONFIG,
            "volatility_percentile_min": _P_CONFIG,
            "config_metadata": _P_META,
        },
    ),
    # structure and levels
    (swing_owner.detect_weekly_swing_levels, {"bars": _P_WEEKLY, "as_of": _P_INSTANT, "left_bars": _P_CONFIG, "right_bars": _P_CONFIG}),
    (swing_owner.detect_monthly_swing_levels, {"bars": _P_MONTHLY, "as_of": _P_INSTANT, "left_bars": _P_CONFIG, "right_bars": _P_CONFIG}),
    (
        breakout_owner.detect_breakout_reclaim_levels,
        {
            "source_levels": _up(_SWING_LEVEL_PRODUCERS, "no levels -> no breakout/reclaim level", _PRICE, (_STRUCTURE,)),
            "bars": _P_DAILY,
            "as_of": _P_INSTANT,
            "breakout_close_buffer_fraction": _P_CONFIG,
            "reclaim_close_buffer_fraction": _P_CONFIG,
        },
    ),
    (
        anchored_vwap_owner.calculate_anchored_vwaps,
        {
            "anchors": _up(
                "btc_predictor.levels.anchored_vwap.anchored_vwap_anchor_from_swing_level / "
                "anchored_vwap_anchor_from_breakout_level / anchored_vwap_anchor_from_capitulation_event",
                "no anchors -> no AVWAP level",
                _PRICE,
            ),
            "bars": dataclasses.replace(_P_HOURLY_VOLUME, families=_PRICE_VOLUME),
            "as_of": _P_INSTANT,
            "price_source": _P_CONFIG,
        },
    ),
    (
        volume_profile_owner.calculate_volume_profile_levels,
        {
            "bars": dataclasses.replace(_P_HOURLY_VOLUME, families=_PRICE_VOLUME),
            "as_of": _P_INSTANT,
            "price_source": _P_CONFIG,
            "bin_size_fraction": _P_CONFIG,
            "value_area_fraction": _P_CONFIG,
            "hvn_volume_fraction": _P_CONFIG,
            "min_bar_count": _P_CONFIG,
        },
    ),
    (
        clustering_owner.cluster_price_levels,
        {
            "levels": _up(
                "btc_predictor.levels: weekly and monthly swing levels, breakout/reclaim levels, volume-profile levels "
                "and anchored-VWAP results (clustering._prepare_members accepts each by feature_id)",
                "no levels -> LEVEL_CLUSTER_INPUT_MISSING; no clusters",
                _PRICE_VOLUME,
                (_STRUCTURE,),
            ),
            "as_of": _P_INSTANT,
            "reference_price": _P_CURRENT_PRICE,
            "cluster_distance_fraction": _P_CONFIG,
            "cluster_atr": _up(buffer_owner.atr_from_daily_bars, "None -> fractional clustering only", _PRICE),
            "cluster_atr_distance_threshold": _P_CONFIG,
            "minimum_level_strength": _P_CONFIG,
        },
    ),
    (
        strength_owner.calculate_level_strength_from_cluster,
        {
            "cluster": _up(clustering_owner.cluster_price_levels, _M_LEVEL_STRENGTH, _PRICE, (_STRUCTURE,)),
            "touch_count": _up(clustering_owner.cluster_price_levels, "None -> the cluster member_count", _PRICE, (_STRUCTURE,)),
            "reaction_magnitude_fraction": _ownerless("LEVEL_REACTION_MAGNITUDE", _M_LEVEL_STRENGTH, _PRICE, (_STRUCTURE,)),
            "volume_percentile": _level_volume_fallback(),
            "weights": _P_CONFIG,
            "timeframe_scores": _P_CONFIG,
            "touch_count_full": _P_CONFIG,
            "reaction_full_fraction": _P_CONFIG,
            "config_metadata": _P_META,
        },
    ),
    (
        structure_owner.calculate_structure_score_from_clusters,
        {
            "clusters": _up(clustering_owner.cluster_price_levels, _M_STRUCTURE, _PRICE, (_STRUCTURE,)),
            "entry_price": dataclasses.replace(_P_CURRENT_PRICE, entry_components=(_STRUCTURE,)),
            "stop_price": _up(stop_owner.initial_stop_for_setup, _M_STRUCTURE, _PRICE, (_STRUCTURE,)),
            "version": _P_CONFIG,
            "level_strength_score": _up(strength_owner.calculate_level_strength_from_cluster, _M_STRUCTURE, _PRICE_VOLUME, (_STRUCTURE,)),
            "level_strength_result": _up(strength_owner.calculate_level_strength_from_cluster, _M_STRUCTURE, _PRICE_VOLUME, (_STRUCTURE,)),
            "weights": _P_CONFIG,
            "entry_location_full_score_distance_fraction": _P_CONFIG,
            "entry_location_zero_score_distance_fraction": _P_CONFIG,
            "rr_minimum": _P_CONFIG,
            "rr_preferred_min": _P_CONFIG,
            "rr_preferred_max": _P_CONFIG,
            "config_metadata": _P_META,
        },
    ),
    # regime and Entry Conviction
    (
        regime_owner.calculate_regime_score,
        {
            "inputs": _up(regime_owner.RegimeScoreInput, _M_REGIME, _REGIME_FAMILIES),
            "core_weights": _P_CONFIG,
            "full_weights": _P_CONFIG,
            "config_metadata": _P_META,
        },
    ),
    (
        regime_owner.calculate_regime_smoothing,
        {
            "inputs": _up(regime_owner.RegimeSmoothingInput, "None -> REGIME_SMOOTHING_NEW_SCORE_MISSING", _REGIME_FAMILIES),
            "previous_weight": _P_CONFIG,
            "new_weight": _P_CONFIG,
            "config_metadata": _P_META,
        },
    ),
    (
        regime_owner.calculate_regime_classification,
        {
            "score": _up(regime_owner.calculate_regime_smoothing, "None -> REGIME_CLASSIFICATION_SCORE_MISSING", _REGIME_FAMILIES),
            "thresholds": _P_CONFIG,
            "config_metadata": _P_META,
        },
    ),
    (
        entry_owner.calculate_entry_conviction,
        {
            "inputs": _up(entry_owner.EntryConvictionInput, _M_EC, _ALL_COMPONENT_FAMILIES, ENTRY_CONVICTION_COMPONENTS),
            "strategy_config": _P_STRATEGY_CONFIG,
        },
    ),
    (
        entry_owner.classify_entry_action,
        {
            "score": _up(entry_owner.calculate_entry_conviction, "None -> ENTRY_ACTION_SCORE_MISSING", _ALL_COMPONENT_FAMILIES),
            "strategy_config": _P_STRATEGY_CONFIG,
        },
    ),
    # setups and entry triggers
    *(
        (
            detector,
            {
                "inputs": _up(input_type, _M_SETUP, _ALL_COMPONENT_FAMILIES),
                "requirements": _P_CONFIG,
                "config_metadata": _P_META,
            },
        )
        for detector, input_type in (
            (setup_owner.detect_bull_trend_continuation, setup_owner.BullTrendContinuationInput),
            (setup_owner.detect_bullish_reset, setup_owner.BullishResetInput),
            (setup_owner.detect_capitulation_reversal, setup_owner.CapitulationReversalInput),
            (setup_owner.detect_bearish_distribution, setup_owner.BearishDistributionInput),
        )
    ),
    (
        reclaim_owner.evaluate_reclaim_trigger,
        {
            "reclaim_level": _up(breakout_owner.detect_breakout_reclaim_levels, "no level -> no trigger", _PRICE),
            "bars": _P_HOURLY_VENUE,
            "as_of": _P_INSTANT,
            "confirmation_bars": _P_CONFIG,
            "hold_buffer_fraction": _P_CONFIG,
            "close_buffer_fraction": _P_CONFIG,
            "config_metadata": _P_META,
        },
    ),
    (
        breakout_retest_owner.evaluate_breakout_retest_trigger,
        {
            "breakout_level": _up(breakout_owner.detect_breakout_reclaim_levels, "no level -> no trigger", _PRICE),
            "bars": _P_HOURLY_VENUE,
            "as_of": _P_INSTANT,
            "atr": _up(buffer_owner.atr_from_daily_bars, "None -> ATR-scaled checks unavailable", _PRICE),
            "atr_available_at": _P_INSTANT,
            "max_retest_bars": _P_CONFIG,
            "max_continuation_bars": _P_CONFIG,
            "retest_distance_atr_max": _P_CONFIG,
            "support_breach_atr_max": _P_CONFIG,
            "continuation_buffer_atr": _P_CONFIG,
            "config_metadata": _P_META,
        },
    ),
    (
        higher_low_owner.evaluate_higher_low_trigger,
        {
            "source_swing_low": _up(swing_owner.detect_weekly_swing_levels, "no swing low -> no trigger", _PRICE),
            "daily_bars": _P_DAILY,
            "as_of": _P_INSTANT,
            "pivot_left_bars": _P_CONFIG,
            "pivot_right_bars": _P_CONFIG,
            "higher_low_left_bars": _P_CONFIG,
            "higher_low_right_bars": _P_CONFIG,
            "max_pattern_bars": _P_CONFIG,
            "max_breakout_bars": _P_CONFIG,
            "higher_low_buffer_fraction": _P_CONFIG,
            "pivot_break_buffer_fraction": _P_CONFIG,
            "config_metadata": _P_META,
        },
    ),
    (
        no_chase_owner.apply_no_chase_filter,
        {
            "entry_zone": _up(invalidation_owner.select_structural_invalidation, "None -> no-chase unavailable", _PRICE),
            "current_price": _P_CURRENT_PRICE,
            "current_price_available_at": _P_INSTANT,
            "as_of": _P_INSTANT,
            "direction": _P_CONFIG,
            "distance_mode": _P_CONFIG,
            "max_distance_atr": _P_CONFIG,
            "max_distance_fraction": _P_CONFIG,
            "atr": _up(buffer_owner.atr_from_daily_bars, "None -> ATR mode unavailable", _PRICE),
            "atr_available_at": _P_INSTANT,
            "config_metadata": _P_META,
        },
    ),
    # hard vetoes and data quality
    (
        hard_veto_owner.evaluate_hard_veto,
        {"inputs": _up(hard_veto_owner.HardVetoInput, _M_VETO, _ALL_COMPONENT_FAMILIES), "strategy_config": _P_STRATEGY_CONFIG},
    ),
    (
        quality_owner.validate_ohlcv_quality,
        {
            "bars": _P_HOURLY_VENUE,
            "start": _P_INSTANT,
            "end": _P_INSTANT,
            "timeframe": _P_CONFIG,
            "as_of": _P_INSTANT,
            "config": _P_CONFIG,
        },
    ),
    (
        quality_owner.validate_derivatives_quality,
        {
            "rows": _raw(
                (FUNDING_RATE_FAMILY, OPEN_INTEREST_FAMILY, PERP_VOLUME_FAMILY, LIQUIDATION_FAMILY),
                SHAPE_SNAPSHOT,
                ROLE_VALUE,
                _SRC_FUNDING,
                "stale or missing feeds -> STALE_FUNDING_RATE / MISSING_EXCHANGE_SNAPSHOT (DATA_QUALITY_FAIL)",
                note="the visible prefix of every derivatives feed the quality owner checks",
            ),
            "as_of": _P_INSTANT,
            "config": _P_CONFIG,
        },
    ),
    (
        data_quality_gate_owner.failures_from_quality_reports,
        {"reports": _up(quality_owner.validate_ohlcv_quality, "a failed report -> DATA_QUALITY_FAIL", (REFERENCE_PRICE_FAMILY, FUNDING_RATE_FAMILY))},
    ),
    (
        data_quality_gate_owner.apply_data_quality_gate,
        {
            "requested_action": _state("the composer's requested action", "required argument"),
            "failures": _up(data_quality_gate_owner.failures_from_quality_reports, "failures -> ENTER/ADD blocked", (REFERENCE_PRICE_FAMILY,)),
            "existing_position_state": _P_LIFECYCLE,
        },
    ),
    # risk, sizing and stops
    (
        reward_owner.reward_risk_for_stop,
        {
            "stop": _up(stop_owner.initial_stop_for_setup, "None -> no R/R", _PRICE),
            "resistance_clusters": _up(clustering_owner.cluster_price_levels, "None -> reference unavailable", _PRICE),
            "swing_highs": _up(swing_owner.detect_weekly_swing_levels, "None -> reference unavailable", _PRICE),
            "range_highs": _up(breakout_owner.detect_breakout_reclaim_levels, "None -> reference unavailable", _PRICE),
            "measured_move": _ownerless(
                "MEASURED_MOVE_REFERENCE", "None -> tier-four reference absent; other reward references still evaluate", _PRICE,
                note="Rulebook 15 names a conservative measured move from the active setup, but no owner defines its target price and PIT detected_at. The setup detector produces filter results, not a measured-move target. Optional does not mean defined; the completion spec must explicitly resolve or omit this tier.",
            ),
            "as_of": _P_INSTANT,
            "setup": _up(setup_owner.detect_bull_trend_continuation, "required", _ALL_COMPONENT_FAMILIES),
            "minimum_reward_risk": _P_CONFIG,
            "config": _P_STRATEGY_CONFIG,
            "config_metadata": _P_META,
        },
    ),
    (
        invalidation_owner.select_structural_invalidation,
        {
            "clusters": _up(clustering_owner.cluster_price_levels, "no eligible cluster -> no structural invalidation", _PRICE),
            "setup": _up(setup_owner.detect_bull_trend_continuation, "required", _ALL_COMPONENT_FAMILIES),
            "entry_price": _P_CURRENT_PRICE,
            "as_of": _P_INSTANT,
            "atr": _up(buffer_owner.atr_from_daily_bars, "None -> ATR distance unavailable", _PRICE),
            "max_distance_fraction": _P_CONFIG,
            "min_confluence": _P_CONFIG,
            "min_member_count": _P_CONFIG,
            "config_metadata": _P_META,
        },
    ),
    (buffer_owner.atr_from_daily_bars, {"bars": _P_DAILY, "window": _P_CONFIG}),
    (
        buffer_owner.volatility_buffer_for_invalidation,
        {
            "invalidation": _up(invalidation_owner.select_structural_invalidation, "required", _PRICE),
            "atr": _up(buffer_owner.atr_from_daily_bars, "required", _PRICE),
            "atr_multiplier": _P_CONFIG,
            "atr_window": _P_CONFIG,
            "config_metadata": _P_META,
        },
    ),
    (
        stop_owner.initial_stop_for_setup,
        {
            "invalidation": _up(invalidation_owner.select_structural_invalidation, "None -> no valid structural stop", _PRICE),
            "buffer": _up(buffer_owner.volatility_buffer_for_invalidation, "required", _PRICE),
            "config_metadata": _P_META,
        },
    ),
    (
        budget_owner.calculate_risk_budget,
        {
            "entry_conviction": _up(entry_owner.calculate_entry_conviction, "below the schedule -> zero budget band", _ALL_COMPONENT_FAMILIES),
            "nav": _P_NAV,
            "config": _P_STRATEGY_CONFIG,
            "schedule": _P_CONFIG,
            "maximum_risk_fraction_nav": _P_CONFIG,
            "config_metadata": _P_META,
        },
    ),
    (
        sizing_owner.initial_position_size_for_trade,
        {
            "risk_budget": _up(budget_owner.calculate_risk_budget, "required", _ALL_COMPONENT_FAMILIES),
            "stop": _up(stop_owner.initial_stop_for_setup, "required", _PRICE),
            "maximum_notional_fraction_nav": _P_CONFIG,
            "config_metadata": _P_META,
        },
    ),
    (
        tranches_owner.next_tranche_for_position,
        {
            "lifecycle": _P_LIFECYCLE,
            "position_size": _up(sizing_owner.initial_position_size_for_trade, "required", _PRICE),
            "entry_price": _P_CURRENT_PRICE,
            "schedule": _P_CONFIG,
            "config": _P_STRATEGY_CONFIG,
            "config_metadata": _P_META,
        },
    ),
    (
        exposure_owner.calculate_risk_at_stop,
        {
            "tranches": _P_LIFECYCLE,
            "stop_price": _P_LIFECYCLE,
            "nav": _P_NAV,
            "direction": _P_LIFECYCLE,
            "convention": _P_CONFIG,
            "target_fraction_nav": _P_CONFIG,
            "maximum_fraction_nav": _P_CONFIG,
            "config": _P_STRATEGY_CONFIG,
            "config_metadata": _P_META,
        },
    ),
    (
        trailing_owner.trail_stop_for_position,
        {
            "lifecycle": _P_LIFECYCLE,
            "structure": _up(trailing_owner.ConfirmedTrailingStructure, "None -> the standing stop is kept", _PRICE),
            "buffer": _up(buffer_owner.volatility_buffer_for_invalidation, "None -> no trail candidate", _PRICE),
            "current_price": _P_CURRENT_PRICE,
            "as_of": _P_INSTANT,
        },
    ),
    # lifecycle: hold, add, trim and exit
    (
        hold_owner.calculate_hold_score,
        {"inputs": _up(hold_owner.HoldScoreInput, _M_HOLD, _ALL_COMPONENT_FAMILIES), "strategy_config": _P_STRATEGY_CONFIG},
    ),
    (
        add_owner.calculate_add_score,
        {"inputs": _up(add_owner.AddScoreInput, _M_ADD_SCORE, _ALL_COMPONENT_FAMILIES), "strategy_config": _P_STRATEGY_CONFIG},
    ),
    (
        add_owner.risk_improvement_component_score,
        {"current_risk": _P_LIFECYCLE, "proposed_risk": _up(trailing_owner.trail_stop_for_position, "required", _PRICE)},
    ),
    (
        add_requirements_owner.add_requirements_from_results,
        {
            "lifecycle": _P_LIFECYCLE,
            "current_price": _P_CURRENT_PRICE,
            "add_score": _up(add_owner.calculate_add_score, _M_ADD_REQ, _ALL_COMPONENT_FAMILIES),
            "risk_improvement": _up(add_owner.risk_improvement_component_score, _M_ADD_REQ, _PRICE),
            "projected_risk_at_stop": _up(exposure_owner.calculate_risk_at_stop, _M_ADD_REQ, _PRICE),
            "new_structural_confirmation": _ownerless("NEW_STRUCTURAL_CONFIRMATION", _M_ADD_REQ, _PRICE),
            "regime_supportive": _ownerless("REGIME_SUPPORTIVE_PREDICATE", _M_ADD_REQ, _REGIME_FAMILIES),
            "flow_supportive": _ownerless("FLOW_SUPPORTIVE_PREDICATE", _M_ADD_REQ, (ETF_FLOW_FAMILY, MARKET_CLOSURE_FAMILY)),
            "positioning_healthy": _up(positioning_owner.calculate_crowding_flag, _M_ADD_REQ, _POSITIONING_FAMILIES),
            "strategy_config": _P_STRATEGY_CONFIG,
            "source_reason_codes": _state("upstream owner reason codes", "evidence only", role=ROLE_PROVENANCE, source=_SRC_UPSTREAM),
        },
    ),
    (
        trim_owner.trim_rules_from_results,
        {
            "lifecycle": _P_LIFECYCLE,
            "hold_score": _up(hold_owner.calculate_hold_score, _M_TRIM, _ALL_COMPONENT_FAMILIES),
            "euphoria": _up(volatility_owner.calculate_euphoria_flag, _M_TRIM + "; an incomplete EUPHORIA passes None", _VOLATILITY_FAMILIES),
            "crowding": _up(positioning_owner.calculate_crowding_flag, _M_TRIM, _POSITIONING_FAMILIES),
            "current_flow": _up(flow_owner.calculate_flow_score, _M_TRIM, (ETF_FLOW_FAMILY,)),
            "prior_flow": _up(flow_owner.calculate_flow_score, _M_TRIM, (ETF_FLOW_FAMILY,), source=_SRC_LEDGER),
            "strategy_config": _P_STRATEGY_CONFIG,
        },
    ),
    (
        exit_rules_owner.exit_rules_for_position,
        {
            "lifecycle": _P_LIFECYCLE,
            "current_price": _P_CURRENT_PRICE,
            "hold_score": _up(hold_owner.calculate_hold_score, _M_EXIT, _ALL_COMPONENT_FAMILIES),
            "regime_invalidated": _ownerless("REGIME_INVALIDATION_PREDICATE", _M_EXIT, _REGIME_FAMILIES),
            "data_risk_exit_required": _ownerless("DATA_RISK_EXIT_PREDICATE", _M_EXIT, (REFERENCE_PRICE_FAMILY,)),
            "manual_research_override": _discretionary("MANUAL_RESEARCH_OVERRIDE", _M_EXIT + "; never asserted in a replay"),
            "manual_override_reason": _discretionary("MANUAL_RESEARCH_OVERRIDE", "None allowed without an override"),
            "strategy_config": _P_STRATEGY_CONFIG,
            "evaluated_at": _P_INSTANT,
            "source_reason_codes": _state("upstream owner reason codes", "evidence only", role=ROLE_PROVENANCE, source=_SRC_UPSTREAM),
        },
    ),
    # lifecycle state machine and the trailing owner's lifecycle write
    (
        state_machine_owner.start_position_lifecycle,
        {
            "symbol": _state("the replay venue's instrument symbol", "required argument", role=ROLE_IDENTITY),
            "direction": _config("long-only champion: backtest.allow_short_trades = false; the composer opens LONG lifecycles"),
            "state": _state("the initial BTC-150 lifecycle state", "keyword default WATCH"),
            "config_metadata": _P_META,
        },
    ),
    (
        state_machine_owner.apply_position_event,
        {
            "lifecycle": _P_LIFECYCLE,
            "event": _state(
                "the BTC-150 lifecycle event the BTC-180 engine applies for a composer intent, a fill, a stop or an exit",
                "required argument; an event invalid in the current state is refused by the state machine",
            ),
            "event_time": _P_INSTANT,
            "quantity": _state("the BTC-180 simulated fill quantity of a sized intent", "None for events that carry no quantity"),
            "price": _state("the BTC-180 simulated fill price (next-bar execution)", "None for events that carry no fill"),
            "stop_price": _up(
                stop_owner.initial_stop_for_setup,
                "None for events that leave the stop unchanged",
                _PRICE,
                note="the initial structural stop, or an advanced trailing stop through apply_trailing_stop",
            ),
            "reason_codes": _state("the event's reason codes", "empty tuple allowed; evidence only", role=ROLE_PROVENANCE, source=_SRC_UPSTREAM),
            "source_feature_id": _state("the owner result that caused the event", "None allowed; evidence only", role=ROLE_PROVENANCE, source=_SRC_UPSTREAM),
            "source_record_id": _state("the owner record that caused the event", "None allowed; evidence only", role=ROLE_PROVENANCE, source=_SRC_UPSTREAM),
        },
    ),
    (
        trailing_owner.apply_trailing_stop,
        {
            "lifecycle": _P_LIFECYCLE,
            "result": _up(trailing_owner.trail_stop_for_position, "required; a held result records no event", _PRICE),
            "event_time": _P_INSTANT,
        },
    ),
    # anchored-VWAP anchors
    (
        anchored_vwap_owner.anchored_vwap_anchor_from_swing_level,
        {"level": _up(_SWING_LEVEL_PRODUCERS, "no swing level -> no swing anchor", _PRICE, (_STRUCTURE,))},
    ),
    (
        anchored_vwap_owner.anchored_vwap_anchor_from_breakout_level,
        {"level": _up(breakout_owner.detect_breakout_reclaim_levels, "no breakout level -> no breakout anchor", _PRICE, (_STRUCTURE,))},
    ),
    (
        anchored_vwap_owner.anchored_vwap_anchor_from_capitulation_event,
        {"event": _ownerless("CAPITULATION_EVENT", _M_CAPITULATION_EVENT, _PRICE, (_STRUCTURE,), note=_CAPITULATION_EVENT_NOTE)},
    ),
)


def _root_parameter_table() -> dict[str, dict[str, InputClassification]]:
    table: dict[str, dict[str, InputClassification]] = {}
    for function, classified in _ROOT_CALL_SITES:
        path = _owner_path(function)
        if path in table:
            raise ImportError(f"root {path} is classified twice")
        table[path] = dict(classified)
    return table


ROOT_PARAMETER_CLASSIFICATIONS: dict[str, dict[str, InputClassification]] = _root_parameter_table()


@dataclass(frozen=True)
class SurfaceRow:
    """One enumerated input: a reached type's field or a reached callable's parameter."""

    surface: str
    owner: str
    name: str
    classification: InputClassification
    category: str = ""
    default: str | None = None
    default_override: str | None = None
    reached_from: str = ""

    @property
    def key(self) -> str:
        return f"{self.owner}.{self.name}"

    def as_record(self) -> dict[str, Any]:
        return {
            "surface": self.surface,
            "owner": self.owner,
            "name": self.name,
            "census_category": self.category,
            "default": self.default,
            "default_override": self.default_override,
            "reached_from": self.reached_from,
            **self.classification.as_record(),
        }


SURFACE_FIELD = "OWNER_INPUT_TYPE_FIELD"
SURFACE_PARAMETER = "OWNER_CALL_SITE_PARAMETER"
SURFACE_INTERNAL_PARAMETER = "OWNER_INTERNAL_PARAMETER"
SURFACES = (SURFACE_FIELD, SURFACE_PARAMETER, SURFACE_INTERNAL_PARAMETER)

CATEGORY_INPUT_TYPE = "COMPOSER_INPUT_TYPE"
CATEGORY_ROOT_PARAMETER = "ROOT_PARAMETER"
CATEGORY_INTERNAL_PARAMETER = "INTERNAL_PARAMETER"
CATEGORY_OWNER_DEFAULT = "OWNER_DEFAULT_CONSTANT"
CATEGORY_CONFIG_LOADER = "CONFIG_LOADER_PARAMETER"

_CONFIG_LOADER_MODULE = "btc_predictor.config.strategy"
_PSEUDO_FAMILIES = (ENGINE_STATE_FAMILY, STRATEGY_CONFIG_FAMILY)
_M_OWNER_OUTPUT = (
    "owner output: present whenever the producing owner returns; incompleteness is reported by that owner's "
    "complete flag, None values and reason codes, never zero-filled"
)
_M_INTERNAL = (
    "supplied by the reached calling owner, never by the composer: it cannot be missing at the composer "
    "boundary, and the caller's own missing-input handling applies"
)
_SRC_INTERNAL = "passed by the reached calling owner, computed from its own classified inputs"
_SRC_STRATEGY_CONFIG = "btc_predictor/config/strategy/default.toml (strategy_config_v2) through load_strategy_config"


def classify_owner_type(owner_type: type, classified: Mapping[str, InputClassification]) -> tuple[SurfaceRow, ...]:
    """Rows for one composer-facing type, refusing unclassified or stale fields.

    Used for fixture owners; :func:`enumerate_input_surface` applies the same
    check to every type the census reaches.
    """

    if not isinstance(owner_type, type) or not (
        dataclasses.is_dataclass(owner_type) or census_owner._is_protocol(owner_type)
    ):
        raise InputSurfaceError("NOT_A_DATACLASS", f"{owner_type!r} is not an owner dataclass or protocol")
    path = _owner_path(owner_type)
    names = census_owner._type_fields(owner_type)[1]
    _require_exact_classification(path, names, classified, unclassified="UNCLASSIFIED_FIELD")
    return tuple(SurfaceRow(SURFACE_FIELD, path, name, classified[name], category=CATEGORY_INPUT_TYPE) for name in names)


def classify_owner_callable(
    function: Callable[..., Any], classified: Mapping[str, InputClassification]
) -> tuple[SurfaceRow, ...]:
    """Rows for one root-like callable, refusing unclassified or stale parameters."""

    path = _owner_path(function)
    names = tuple(inspect.signature(function).parameters)
    _require_exact_classification(path, names, classified, unclassified="UNCLASSIFIED_PARAMETER")
    return tuple(
        SurfaceRow(SURFACE_PARAMETER, path, name, classified[name], category=CATEGORY_ROOT_PARAMETER) for name in names
    )


def enumerate_input_surface(census: census_owner.DecisionPathCensus | None = None) -> tuple[SurfaceRow, ...]:
    """Enumerate the section 5A input surface the census discovers.

    The census is built from the live owner code unless one is passed. Every
    field of every reached type and every parameter of every reached callable
    must be classified: composer-facing types and roots field by field here,
    everything else by the reviewed snapshot in ``input_census_registry``.
    Unclassified owners, fields and parameters are refused before stale
    classifications, so an owner that gains an input reports exactly that.
    """

    census = census_owner.discover_decision_path() if census is None else census
    _require_classified_census(census)
    profiles = _root_profiles(census)
    rows: list[SurfaceRow] = []
    for path, record in census.types.items():
        if path in INPUT_TYPE_FIELD_CLASSIFICATIONS:
            classified = INPUT_TYPE_FIELD_CLASSIFICATIONS[path]
            rows.extend(
                SurfaceRow(SURFACE_FIELD, path, name, classified[name], CATEGORY_INPUT_TYPE, reached_from=record.reached_from)
                for name in record.fields
            )
            continue
        category, _, note = census_registry.DISCOVERED_TYPES[path]
        for name in record.fields:
            rows.append(
                SurfaceRow(
                    SURFACE_FIELD,
                    path,
                    name,
                    _discovered_field(path, name, category, note, census, profiles),
                    category,
                    reached_from=record.reached_from,
                )
            )
    roots = set(census.root_paths)
    for path, record in census.callables.items():
        if path in roots:
            classified = ROOT_PARAMETER_CLASSIFICATIONS[path]
            rows.extend(
                SurfaceRow(
                    SURFACE_PARAMETER,
                    path,
                    item.name,
                    classified[item.name],
                    CATEGORY_ROOT_PARAMETER,
                    default=item.default,
                    default_override=census_owner.DEFAULT_COMPOSER_SUPPLIED if item.has_default else None,
                    reached_from=census_owner.ROOT_PARENT,
                )
                for item in record.parameters
            )
            continue
        for item in record.parameters:
            verdict = census.default_override(path, item.name)[0] if item.has_default else None
            classification, category = _internal_parameter(path, item, verdict, census, profiles)
            rows.append(
                SurfaceRow(
                    SURFACE_INTERNAL_PARAMETER,
                    path,
                    item.name,
                    classification,
                    category,
                    default=item.default,
                    default_override=verdict,
                    reached_from=record.reached_from,
                )
            )
    return tuple(sorted(rows, key=lambda row: (row.surface, row.owner, row.name)))


def _require_classified_census(census: census_owner.DecisionPathCensus) -> None:
    semantic = INPUT_TYPE_FIELD_CLASSIFICATIONS
    registry_types = census_registry.DISCOVERED_TYPES
    registry_callables = census_registry.DISCOVERED_CALLABLES
    roots = set(census.root_paths)
    doubled = sorted(set(semantic) & set(registry_types))
    if doubled:
        raise InputSurfaceError("DUPLICATE_OWNER_TYPE", f"classified twice: {doubled}")
    doubled = sorted(set(ROOT_PARAMETER_CLASSIFICATIONS) & set(registry_callables))
    if doubled:
        raise InputSurfaceError("DUPLICATE_CALL_SITE", f"classified as root and as internal: {doubled}")
    # Unclassified owners, fields and parameters first.
    for path, record in census.types.items():
        if path in semantic:
            _require_exact_classification(path, record.fields, semantic[path], unclassified="UNCLASSIFIED_FIELD")
        elif path in registry_types:
            category, names, _ = registry_types[path]
            if category not in census_registry.TYPE_CATEGORIES:
                raise InputSurfaceError("UNKNOWN_TYPE_CATEGORY", f"{path}: {category!r}")
            _require_exact_names(path, record.fields, names, unclassified="UNCLASSIFIED_FIELD")
        else:
            raise InputSurfaceError("UNCLASSIFIED_OWNER_TYPE", f"{path} is reached from {record.reached_from} but has no classification")
    missing_roots = sorted(roots - set(ROOT_PARAMETER_CLASSIFICATIONS))
    if missing_roots:
        raise InputSurfaceError("UNCLASSIFIED_PARAMETER", f"roots without parameter classifications: {missing_roots}")
    for path, record in census.callables.items():
        if path in roots:
            _require_exact_classification(
                path, record.parameter_names, ROOT_PARAMETER_CLASSIFICATIONS[path], unclassified="UNCLASSIFIED_PARAMETER"
            )
        elif path in registry_callables:
            _require_exact_names(path, record.parameter_names, registry_callables[path], unclassified="UNCLASSIFIED_PARAMETER")
        else:
            raise InputSurfaceError("UNCLASSIFIED_CALLABLE", f"{path} is reached from {record.reached_from} but has no classification")
    # Then classifications that outlived their owner.
    stale = sorted((set(semantic) | set(registry_types)) - set(census.types))
    stale += sorted((set(ROOT_PARAMETER_CLASSIFICATIONS) - roots) | (set(registry_callables) - set(census.callables)))
    if stale:
        raise InputSurfaceError("STALE_CLASSIFICATION", f"classified owners the census no longer reaches: {stale}")


def _require_exact_classification(
    owner: str,
    names: Sequence[str],
    classified: Mapping[str, InputClassification],
    *,
    unclassified: str,
) -> None:
    missing = [name for name in names if name not in classified]
    if missing:
        raise InputSurfaceError(unclassified, f"{owner} has unclassified inputs {missing}")
    stale = sorted(set(classified) - set(names))
    if stale:
        raise InputSurfaceError("STALE_CLASSIFICATION", f"{owner} no longer has {stale}")
    for name in names:
        if not isinstance(classified[name], InputClassification):
            raise InputSurfaceError(unclassified, f"{owner}.{name} has no InputClassification")


def _require_exact_names(owner: str, names: Sequence[str], pinned: Sequence[str], *, unclassified: str) -> None:
    missing = [name for name in names if name not in pinned]
    if missing:
        raise InputSurfaceError(unclassified, f"{owner} has unclassified inputs {missing}")
    stale = sorted(set(pinned) - set(names))
    if stale:
        raise InputSurfaceError("STALE_CLASSIFICATION", f"{owner} no longer has {stale}")
    if tuple(names) != tuple(pinned):
        raise InputSurfaceError("SIGNATURE_ORDER_CHANGED", f"{owner}: {tuple(names)} != {tuple(pinned)}")


def _root_profiles(census: census_owner.DecisionPathCensus) -> dict[str, tuple[tuple[str, ...], tuple[str, ...]]]:
    """Each root's input families and Entry Conviction components."""

    profiles = {}
    for path in census.root_paths:
        families: set[str] = set()
        components: set[str] = set()
        for classification in ROOT_PARAMETER_CLASSIFICATIONS[path].values():
            families.update(classification.families)
            components.update(classification.entry_components)
        data = families - set(_PSEUDO_FAMILIES)
        profiles[path] = (
            tuple(family for family in FAMILIES if family in (data or families)),
            tuple(component for component in ENTRY_CONVICTION_COMPONENTS if component in components),
        )
    return profiles


def _reach_profile(
    paths: Iterable[str],
    census: census_owner.DecisionPathCensus,
    profiles: Mapping[str, tuple[tuple[str, ...], tuple[str, ...]]],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Families and components of every root whose closure reaches ``paths``."""

    families: set[str] = set()
    components: set[str] = set()
    for path in paths:
        for root in census.reaching_roots.get(path, ()):
            families.update(profiles[root][0])
            components.update(profiles[root][1])
    data = families - set(_PSEUDO_FAMILIES)
    return (
        tuple(family for family in FAMILIES if family in (data or families or {STRATEGY_CONFIG_FAMILY})),
        tuple(component for component in ENTRY_CONVICTION_COMPONENTS if component in components),
    )


def _producer_text(paths: Sequence[str]) -> str:
    paths = sorted(paths)
    if len(paths) <= 3:
        return "; ".join(paths)
    return "; ".join(paths[:3]) + f"; and {len(paths) - 3} more reached owners"


def _field_role(name: str) -> str:
    if name in ("reason_codes", "config_metadata", "feature_id", "policy_version", "source_record_id") or name.endswith(
        ("_reason_codes", "_feature_id")
    ):
        return ROLE_PROVENANCE
    if name in ("exchange", "symbol", "provider", "timeframe", "instrument", "fund", "market_type") or name.endswith("_id"):
        return ROLE_IDENTITY
    if name in ("detected_at", "available_at") or name.endswith(("_detected_at", "_available_at")):
        return ROLE_AVAILABILITY
    if name in ("as_of", "timestamp", "evaluated_at") or name.endswith(("_timestamp", "_time", "_at")):
        return ROLE_OBSERVATION_TIME
    return ROLE_VALUE


def _type_producers(path: str, census: census_owner.DecisionPathCensus) -> tuple[str, ...]:
    constructors = sorted({site.caller for site in census.call_sites if site.callee == path})
    return tuple(constructors or census.callers.get(path, ()))


def _discovered_field(
    type_path: str,
    name: str,
    category: str,
    note: str,
    census: census_owner.DecisionPathCensus,
    profiles: Mapping[str, tuple[tuple[str, ...], tuple[str, ...]]],
) -> InputClassification:
    role = _field_role(name)
    if category == census_registry.TYPE_STRATEGY_CONFIG:
        return dataclasses.replace(
            _config(note or f"StrategyConfig section {type_path.rsplit('.', 1)[-1]}"),
            producing_owner="btc_predictor.config.strategy.load_strategy_config (the frozen champion StrategyConfig)",
            historical_source=_SRC_STRATEGY_CONFIG,
            missing_behaviour="never missing: a declared field of the frozen champion StrategyConfig",
            role=role,
        )
    if category == census_registry.TYPE_OWNER_CONFIG:
        return dataclasses.replace(
            _config(note),
            producing_owner=type_path,
            historical_source="the owner configuration record's own defaults (or values built from the frozen StrategyConfig)",
            missing_behaviour="never missing: an owner configuration record built by owner code",
            role=role,
        )
    if category == census_registry.TYPE_ENGINE_STATE:
        return _state(
            "btc_predictor.portfolio.state_machine (BTC-150 lifecycle maintained for the replay by the BTC-180 engine)",
            "engine state: maintained by the state machine for the replay's own position; never back-filled",
            role=role,
            note=note,
        )
    if category == census_registry.TYPE_OWNER_OUTPUT:
        producers = _type_producers(type_path, census)
        if not producers:
            raise InputSurfaceError("OWNER_OUTPUT_WITHOUT_PRODUCER", f"{type_path} is categorised as an owner output but nothing reached constructs it")
        families, components = _reach_profile(producers, census, profiles)
        return InputClassification(
            kind=KIND_DERIVED,
            shape=SHAPE_DERIVED,
            families=families,
            producing_owner=_producer_text(producers),
            historical_source=_SRC_UPSTREAM,
            missing_behaviour=_M_OWNER_OUTPUT,
            entry_components=components,
            role=role,
            note=note,
        )
    raise InputSurfaceError("UNKNOWN_TYPE_CATEGORY", f"{type_path}: {category!r} has fields")


def _internal_parameter(
    path: str,
    item: census_owner.CensusParameter,
    verdict: str | None,
    census: census_owner.DecisionPathCensus,
    profiles: Mapping[str, tuple[tuple[str, ...], tuple[str, ...]]],
) -> tuple[InputClassification, str]:
    if path.startswith(_CONFIG_LOADER_MODULE + "."):
        return (
            dataclasses.replace(
                _config("configuration loader internals: parse default.toml into the frozen StrategyConfig, reached only through an owner's config=None default"),
                producing_owner=path,
                historical_source=_SRC_STRATEGY_CONFIG,
            ),
            CATEGORY_CONFIG_LOADER,
        )
    if verdict == census_owner.DEFAULT_FIXED:
        return (
            dataclasses.replace(
                _config(f"owner keyword default {item.default}"),
                producing_owner=path,
                historical_source="the owner's keyword default",
                missing_behaviour=(
                    f"never missing: the keyword default {item.default} is a fixed constant of the decision path "
                    "because no reached caller passes this argument"
                ),
            ),
            CATEGORY_OWNER_DEFAULT,
        )
    callers = census.callers.get(path, ())
    record = census.callables[path]
    if callers:
        producer = _producer_text(callers)
    elif record.role in (census_owner.ROLE_METHOD, census_owner.ROLE_PROPERTY, census_owner.ROLE_CLASSMETHOD):
        producer = f"reached owner code calling {path} on an owner record"
    else:
        producer = f"the reached owner that holds {path} (reached by {record.reached_by} from {record.reached_from})"
    families, components = _reach_profile((path,), census, profiles)
    note = f"default {item.default} unless the caller passes it ({verdict})" if item.has_default else ""
    return (
        InputClassification(
            kind=KIND_OWNER_INTERNAL,
            shape=SHAPE_DERIVED,
            families=families,
            producing_owner=producer,
            historical_source=_SRC_INTERNAL,
            missing_behaviour=_M_INTERNAL,
            entry_components=components,
            note=note,
        ),
        CATEGORY_INTERNAL_PARAMETER,
    )


def input_surface_summary(rows: Sequence[SurfaceRow]) -> dict[str, Any]:
    """Counts by surface, category, family and kind, plus the owner-less,
    discretionary and fixed-default inputs."""

    by_family: dict[str, int] = {}
    raw_by_family: dict[str, int] = {}
    composer_by_family: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    by_shape: dict[str, int] = {}
    by_surface: dict[str, int] = {}
    by_category: dict[str, int] = {}
    ownerless: dict[str, dict[str, Any]] = {}
    discretionary: dict[str, list[str]] = {}
    defaults: list[dict[str, Any]] = []
    for row in rows:
        classification = row.classification
        composer_facing = row.category in (CATEGORY_INPUT_TYPE, CATEGORY_ROOT_PARAMETER)
        for family in classification.families:
            by_family[family] = by_family.get(family, 0) + 1
            if composer_facing:
                composer_by_family[family] = composer_by_family.get(family, 0) + 1
            if classification.kind == KIND_RAW:
                raw_by_family[family] = raw_by_family.get(family, 0) + 1
        by_kind[classification.kind] = by_kind.get(classification.kind, 0) + 1
        by_shape[classification.shape] = by_shape.get(classification.shape, 0) + 1
        by_surface[row.surface] = by_surface.get(row.surface, 0) + 1
        if row.category:
            by_category[row.category] = by_category.get(row.category, 0) + 1
        if classification.kind in (KIND_OWNERLESS_CERTIFIED, KIND_OWNERLESS_UNDEFINED, KIND_OWNERLESS_FALLBACK):
            entry = ownerless.setdefault(
                classification.input_id or "",
                {"kind": classification.kind, "certified_definition": None, "occurrences": [], "entry_components": set()},
            )
            entry["occurrences"].append(row.key)
            entry["entry_components"].update(classification.entry_components)
            if classification.kind == KIND_OWNERLESS_CERTIFIED:
                entry["certified_definition"] = classification.historical_source
        if classification.kind == KIND_DISCRETIONARY:
            discretionary.setdefault(classification.input_id or row.name, []).append(row.key)
        if row.category == CATEGORY_OWNER_DEFAULT:
            defaults.append({"owner": row.owner, "parameter": row.name, "default": row.default})
    return {
        "rows": len(rows),
        "owner_input_types": len({row.owner for row in rows if row.surface == SURFACE_FIELD}),
        "owner_call_sites": len({row.owner for row in rows if row.surface == SURFACE_PARAMETER}),
        "owner_internal_callables": len({row.owner for row in rows if row.surface == SURFACE_INTERNAL_PARAMETER}),
        "count_by_surface": dict(sorted(by_surface.items())),
        "count_by_census_category": dict(sorted(by_category.items())),
        "count_by_family": dict(sorted(by_family.items())),
        "count_by_family_composer_facing": dict(sorted(composer_by_family.items())),
        "count_by_family_raw_leaves": dict(sorted(raw_by_family.items())),
        "count_by_kind": dict(sorted(by_kind.items())),
        "count_by_shape": dict(sorted(by_shape.items())),
        "ownerless_inputs": {
            input_id: {
                "kind": entry["kind"],
                "certified_definition": entry["certified_definition"],
                "entry_components": sorted(entry["entry_components"]),
                "occurrences": sorted(entry["occurrences"]),
            }
            for input_id, entry in sorted(ownerless.items())
        },
        "discretionary_inputs": {key: sorted(value) for key, value in sorted(discretionary.items())},
        "owner_default_constants": sorted(defaults, key=lambda item: (item["owner"], item["parameter"])),
    }


def census_record(census: census_owner.DecisionPathCensus) -> dict[str, Any]:
    """The census evidence persisted with the inventory: roots, left-out owner
    definitions, and every reached type and callable with how it was reached."""

    categories = {path: entry[0] for path, entry in census_registry.DISCOVERED_TYPES.items()}
    return {
        "summary": census.summary(),
        "roots": [root.as_record() for root in census.roots],
        "left_out_owner_definitions": [
            {"definition": path, "justification": reason}
            for path, reason in sorted(census_owner.LEFT_OUT_OWNER_DEFINITIONS.items())
        ],
        "outside_owner_scope": [
            {"package": name, "justification": reason} for name, reason in sorted(census_owner.OUTSIDE_OWNER_SCOPE.items())
        ],
        "types": [
            {**record.as_record(), "census_category": categories.get(path, CATEGORY_INPUT_TYPE)}
            for path, record in census.types.items()
        ],
        "callables": [
            {key: value for key, value in record.as_record().items() if key != "parameters"}
            for record in census.callables.values()
        ],
    }


# --- minimum history (read from the owners) ------------------------------------------

RULE_LOOKBACK_ROWS = "LOOKBACK_ROWS"
RULE_ROLLING_ROWS = "ROLLING_ROWS_INCLUDING_CURRENT"
RULE_TRAILING_WINDOW = "COUNT_IN_HALF_OPEN_TRAILING_WINDOW"
RULE_ETF_WINDOW = "ETF_PUBLICATION_DAY_WINDOW"
RULE_ALL_OF = "ALL_OF"
RULE_UNDEFINED = "UNDEFINED_OWNERLESS"
RULE_UNIMPLEMENTED_FALLBACK = "UNIMPLEMENTED_RULEBOOK_FALLBACK"

SERIES_DAILY = "VENUE_1D_CANONICAL_BARS"
SERIES_WEEKLY = "VENUE_1W_CANONICAL_BARS"
SERIES_MONTHLY = "VENUE_1MO_CANONICAL_BARS"
SERIES_RV_20 = "VENUE_RV_20_RESULTS"
SERIES_ETF_DAYS = "ETF_PUBLICATION_DAYS"
SERIES_FUNDING = "FUNDING_SETTLEMENTS"
SERIES_OI_GROWTH = "OI_GROWTH_OBSERVATIONS"
SERIES_BASIS = "FUTURES_BASIS_SNAPSHOTS"
SERIES_OI_INTENSITY = "OI_INTENSITY_OBSERVATIONS"
SERIES_LIQUIDATION_DAYS = "LIQUIDATION_CENSUS_DAYS"
SERIES_NONE = "NONE"


@dataclass(frozen=True)
class HistoryParameter:
    name: str
    value: int
    owner_reference: str

    def as_record(self) -> dict[str, Any]:
        return {"name": self.name, "value": self.value, "owner_reference": self.owner_reference}


@dataclass(frozen=True)
class HistoryRequirement:
    """One input's warm-up rule, with every number taken from its owner."""

    input_id: str
    owner: str
    rule: str
    series: str
    parameters: tuple[HistoryParameter, ...] = ()
    upstream: tuple[str, ...] = ()
    entry_components: tuple[str, ...] = ()
    note: str = ""

    def parameter(self, name: str) -> int:
        for item in self.parameters:
            if item.name == name:
                return item.value
        raise KeyError(f"{self.input_id} has no parameter {name}")

    def as_record(self) -> dict[str, Any]:
        return {
            "input_id": self.input_id,
            "owner": self.owner,
            "rule": self.rule,
            "series": self.series,
            "parameters": [item.as_record() for item in self.parameters],
            "upstream": list(self.upstream),
            "entry_components": list(self.entry_components),
            "note": self.note,
        }


def _p(name: str, value: int, reference: str) -> HistoryParameter:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise CoverageError("OWNER_WINDOW_INVALID", f"{reference} is not a non-negative int")
    return HistoryParameter(name, value, reference)


def minimum_history_requirements() -> tuple[HistoryRequirement, ...]:
    """Every warm-up rule on the Entry Conviction and core regime path.

    Numbers are read from owner constants and keyword defaults at call time, so
    an owner change moves the derived earliest dates. Inputs with no owner
    window are ``UNDEFINED_OWNERLESS``.
    """

    vol_defaults = volatility_owner.volatility_percentile.__kwdefaults__
    rv_windows = volatility_owner.REALIZED_VOLATILITY_WINDOWS
    rv_ids = volatility_owner.REALIZED_VOLATILITY_FEATURE_IDS
    weekly_swing = swing_owner.detect_weekly_swing_levels.__kwdefaults__
    monthly_swing = swing_owner.detect_monthly_swing_levels.__kwdefaults__
    trend_path = "btc_predictor.features.trend"
    momentum_path = "btc_predictor.features.momentum"
    flow_path = "btc_predictor.features.flow"
    positioning_path = "btc_predictor.features.positioning"
    volatility_path = "btc_predictor.features.volatility"
    corpus_path = "btc_predictor.research.prospective_integration_corpus"
    swing_path = "btc_predictor.levels.swing"

    requirements: list[HistoryRequirement] = [
        HistoryRequirement(
            "MOMENTUM_4W",
            _owner_path(momentum_owner.four_week_momentum_from_daily_bars),
            RULE_LOOKBACK_ROWS,
            SERIES_DAILY,
            (_p("lookback_rows", momentum_owner.FOUR_WEEK_MOMENTUM_LOOKBACK_DAYS, f"{momentum_path}.FOUR_WEEK_MOMENTUM_LOOKBACK_DAYS"),),
            entry_components=(_TREND,),
        ),
        HistoryRequirement(
            "MOMENTUM_12W",
            _owner_path(momentum_owner.twelve_week_momentum_from_daily_bars),
            RULE_LOOKBACK_ROWS,
            SERIES_DAILY,
            (_p("lookback_rows", momentum_owner.TWELVE_WEEK_MOMENTUM_LOOKBACK_DAYS, f"{momentum_path}.TWELVE_WEEK_MOMENTUM_LOOKBACK_DAYS"),),
            entry_components=(_TREND,),
        ),
        HistoryRequirement(
            "MA_DISTANCE_20W",
            _owner_path(trend_owner.twenty_week_ma_distance_from_weekly_bars),
            RULE_ROLLING_ROWS,
            SERIES_WEEKLY,
            (_p("window_rows", trend_owner.TWENTY_WEEK_MA_DISTANCE_LOOKBACK_WEEKS, f"{trend_path}.TWENTY_WEEK_MA_DISTANCE_LOOKBACK_WEEKS"),),
            entry_components=(_TREND,),
        ),
        HistoryRequirement(
            "HIGH_DISTANCE_52W",
            _owner_path(trend_owner.fifty_two_week_high_distance_from_weekly_bars),
            RULE_ROLLING_ROWS,
            SERIES_WEEKLY,
            (_p("window_rows", trend_owner.FIFTY_TWO_WEEK_HIGH_DISTANCE_LOOKBACK_WEEKS, f"{trend_path}.FIFTY_TWO_WEEK_HIGH_DISTANCE_LOOKBACK_WEEKS"),),
            entry_components=(_TREND,),
        ),
        HistoryRequirement(
            "WEEKLY_STRUCTURE",
            _owner_path(trend_owner.classify_weekly_structure_from_weekly_bars),
            RULE_LOOKBACK_ROWS,
            SERIES_WEEKLY,
            (_p("lookback_rows", 1, f"{trend_path}.classify_weekly_structure (index 0 has no previous week; tested)"),),
            entry_components=(_TREND,),
        ),
        *(
            HistoryRequirement(input_id, OWNERLESS, RULE_UNDEFINED, SERIES_NONE, entry_components=(_TREND,), note=note)
            for input_id, note in (
                ("TREND_Z_M4", "z-score normalisation of MOMENTUM_4W: no owner window or minimum"),
                ("TREND_Z_M12", "z-score normalisation of MOMENTUM_12W: no owner window or minimum"),
                ("TREND_Z_20W", "z-score normalisation of MA_DISTANCE_20W: no owner window or minimum"),
                ("TREND_Z_52H", "z-score normalisation of HIGH_DISTANCE_52W: no owner window or minimum"),
            )
        ),
        HistoryRequirement(
            "TREND_SCORE",
            _owner_path(trend_owner.calculate_trend_score),
            RULE_ALL_OF,
            SERIES_NONE,
            upstream=("MOMENTUM_4W", "MOMENTUM_12W", "MA_DISTANCE_20W", "HIGH_DISTANCE_52W", "WEEKLY_STRUCTURE", "TREND_Z_M4", "TREND_Z_M12", "TREND_Z_20W", "TREND_Z_52H"),
            entry_components=(_TREND,),
        ),
        HistoryRequirement(
            "ETF_NORM_5D",
            _owner_path(flow_owner.five_day_etf_flow),
            RULE_ETF_WINDOW,
            SERIES_ETF_DAYS,
            (_p("publication_days", flow_owner.FIVE_DAY_ETF_FLOW_WINDOW_DAYS, f"{flow_path}.FIVE_DAY_ETF_FLOW_WINDOW_DAYS"),),
            entry_components=(_FLOW,),
            note=f"publication days exclude {CLOSURE_TABLE_VERSION} closures; T+2 00:00 availability",
        ),
        HistoryRequirement(
            "ETF_NORM_20D",
            _owner_path(flow_owner.twenty_day_etf_flow),
            RULE_ETF_WINDOW,
            SERIES_ETF_DAYS,
            (_p("publication_days", flow_owner.TWENTY_DAY_ETF_FLOW_WINDOW_DAYS, f"{flow_path}.TWENTY_DAY_ETF_FLOW_WINDOW_DAYS"),),
            entry_components=(_FLOW,),
            note=f"publication days exclude {CLOSURE_TABLE_VERSION} closures; T+2 00:00 availability",
        ),
        HistoryRequirement(
            "FLOW_ACCEL",
            _owner_path(flow_owner.etf_flow_acceleration),
            RULE_ALL_OF,
            SERIES_NONE,
            upstream=("ETF_NORM_5D", "ETF_NORM_20D"),
            entry_components=(_FLOW,),
        ),
        *(
            HistoryRequirement(input_id, OWNERLESS, RULE_UNDEFINED, SERIES_NONE, entry_components=(_FLOW,), note=note)
            for input_id, note in (
                ("FLOW_Z_ETF_NORM_5D", "z(ETFNorm_5): no owner window or minimum"),
                ("FLOW_Z_ETF_NORM_20D", "z(ETFNorm_20): no owner window or minimum"),
                ("FLOW_Z_FLOW_ACCEL", "z(FlowAccel): no owner window or minimum"),
            )
        ),
        HistoryRequirement(
            "FLOW_SCORE",
            _owner_path(flow_owner.calculate_flow_score),
            RULE_ALL_OF,
            SERIES_NONE,
            upstream=("ETF_NORM_5D", "ETF_NORM_20D", "FLOW_ACCEL", "FLOW_Z_ETF_NORM_5D", "FLOW_Z_ETF_NORM_20D", "FLOW_Z_FLOW_ACCEL"),
            entry_components=(_FLOW,),
            note="ETF_CORE (CVD absent)",
        ),
        HistoryRequirement(
            "FUNDING_HEALTH",
            _owner_path(positioning_owner.funding_health),
            RULE_TRAILING_WINDOW,
            SERIES_FUNDING,
            (
                _p("window_days", positioning_owner.DEFAULT_FUNDING_ZSCORE_WINDOW_DAYS, f"{positioning_path}.DEFAULT_FUNDING_ZSCORE_WINDOW_DAYS"),
                _p("min_prior_observations", positioning_owner.DEFAULT_FUNDING_MIN_ZSCORE_OBSERVATIONS, f"{positioning_path}.DEFAULT_FUNDING_MIN_ZSCORE_OBSERVATIONS"),
                _p("average_window_days", positioning_owner.DEFAULT_FUNDING_AVERAGE_WINDOW_DAYS, f"{positioning_path}.DEFAULT_FUNDING_AVERAGE_WINDOW_DAYS"),
            ),
            entry_components=(_POSITIONING,),
            note="one 7-day average per settlement; the owner sets no minimum count inside the average window",
        ),
        HistoryRequirement(
            "OI_GROWTH_HEALTH",
            _owner_path(positioning_owner.open_interest_growth_health),
            RULE_TRAILING_WINDOW,
            SERIES_OI_GROWTH,
            (
                _p("window_days", positioning_owner.DEFAULT_OI_GROWTH_ZSCORE_WINDOW_DAYS, f"{positioning_path}.DEFAULT_OI_GROWTH_ZSCORE_WINDOW_DAYS"),
                _p("min_prior_observations", positioning_owner.DEFAULT_OI_GROWTH_MIN_ZSCORE_OBSERVATIONS, f"{positioning_path}.DEFAULT_OI_GROWTH_MIN_ZSCORE_OBSERVATIONS"),
                _p("growth_window_days", positioning_owner.DEFAULT_OI_GROWTH_WINDOW_DAYS, f"{positioning_path}.DEFAULT_OI_GROWTH_WINDOW_DAYS"),
            ),
            entry_components=(_POSITIONING,),
            note="a growth observation needs an OI snapshot growth_window_days earlier",
        ),
        HistoryRequirement(
            "FUTURES_BASIS_HEALTH",
            _owner_path(positioning_owner.futures_basis_health),
            RULE_TRAILING_WINDOW,
            SERIES_BASIS,
            (
                _p("window_days", positioning_owner.DEFAULT_FUTURES_BASIS_ZSCORE_WINDOW_DAYS, f"{positioning_path}.DEFAULT_FUTURES_BASIS_ZSCORE_WINDOW_DAYS"),
                _p("min_prior_observations", positioning_owner.DEFAULT_FUTURES_BASIS_MIN_ZSCORE_OBSERVATIONS, f"{positioning_path}.DEFAULT_FUTURES_BASIS_MIN_ZSCORE_OBSERVATIONS"),
            ),
            entry_components=(_POSITIONING,),
        ),
        HistoryRequirement(
            "OI_INTENSITY_PERCENTILE",
            _owner_path(positioning_owner.open_interest_intensity),
            RULE_TRAILING_WINDOW,
            SERIES_OI_INTENSITY,
            (
                _p("window_days", positioning_owner.DEFAULT_OI_INTENSITY_PERCENTILE_WINDOW_DAYS, f"{positioning_path}.DEFAULT_OI_INTENSITY_PERCENTILE_WINDOW_DAYS"),
                _p("min_prior_observations", positioning_owner.DEFAULT_OI_INTENSITY_MIN_PERCENTILE_OBSERVATIONS, f"{positioning_path}.DEFAULT_OI_INTENSITY_MIN_PERCENTILE_OBSERVATIONS"),
            ),
            entry_components=(_POSITIONING,),
            note="observations exist only where an OI snapshot and a market cap share an observation_time",
        ),
        HistoryRequirement(
            "POSITIONING_SCORE",
            _owner_path(positioning_owner.calculate_positioning_score),
            RULE_ALL_OF,
            SERIES_NONE,
            upstream=("FUNDING_HEALTH", "OI_GROWTH_HEALTH", "FUTURES_BASIS_HEALTH", "OI_INTENSITY_PERCENTILE"),
            entry_components=(_POSITIONING,),
        ),
        *(
            HistoryRequirement(
                rv_ids[window],
                _owner_path(volatility_owner.realized_volatility_from_daily_bars),
                RULE_LOOKBACK_ROWS,
                SERIES_DAILY,
                (_p("lookback_rows", window, f"{volatility_path}.REALIZED_VOLATILITY_WINDOWS[{index}]"),),
                entry_components=(_VOLATILITY,),
                note="window_days returns need window_days + 1 closes (row-based: gaps read as contiguous)",
            )
            for index, window in enumerate(rv_windows)
        ),
        HistoryRequirement(
            "VOL_COMPRESSION_RATIO",
            _owner_path(volatility_owner.volatility_compression_ratio_from_results),
            RULE_ALL_OF,
            SERIES_NONE,
            upstream=(rv_ids[rv_windows[0]], rv_ids[rv_windows[-1]]),
            entry_components=(_VOLATILITY,),
        ),
        HistoryRequirement(
            "VOL_PERCENTILE_2Y",
            _owner_path(volatility_owner.volatility_percentile),
            RULE_TRAILING_WINDOW,
            SERIES_RV_20,
            (
                _p("window_days", vol_defaults["percentile_window_days"], f"{volatility_path}.volatility_percentile.percentile_window_days"),
                _p("min_prior_observations", vol_defaults["min_percentile_observations"], f"{volatility_path}.volatility_percentile.min_percentile_observations"),
            ),
            upstream=(vol_defaults["source_feature_id"],),
            entry_components=(_VOLATILITY,),
        ),
        HistoryRequirement(
            "LIQUIDATION_PERCENTILE",
            epic_x_corpus.PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_VERSION,
            RULE_TRAILING_WINDOW,
            SERIES_LIQUIDATION_DAYS,
            (
                _p("window_days", epic_x_corpus.LIQUIDATION_PERCENTILE_WINDOW_DAYS, f"{corpus_path}.LIQUIDATION_PERCENTILE_WINDOW_DAYS"),
                _p("min_prior_observations", epic_x_corpus.LIQUIDATION_PERCENTILE_MIN_OBSERVATIONS, f"{corpus_path}.LIQUIDATION_PERCENTILE_MIN_OBSERVATIONS"),
            ),
            entry_components=(_VOLATILITY,),
            note="certified EPIC X corpus V1 definition, used by reference: one observation per complete UTC census day",
        ),
        *(
            HistoryRequirement(input_id, OWNERLESS, RULE_UNDEFINED, SERIES_NONE, entry_components=(_VOLATILITY,), note=note)
            for input_id, note in (
                ("RANGE_PERCENTILE", "no owner quantity, window or minimum"),
                ("DOWNSIDE_RETURN", "no owner return horizon"),
            )
        ),
        HistoryRequirement(
            "ORDERLINESS_SCORE",
            _owner_path(volatility_owner.calculate_orderliness_score),
            RULE_ALL_OF,
            SERIES_NONE,
            upstream=("RANGE_PERCENTILE", "DOWNSIDE_RETURN", "LIQUIDATION_PERCENTILE", "VOL_PERCENTILE_2Y"),
            entry_components=(_VOLATILITY,),
        ),
        HistoryRequirement(
            "VOLATILITY_SCORE",
            _owner_path(volatility_owner.calculate_volatility_score),
            RULE_ALL_OF,
            SERIES_NONE,
            upstream=("VOL_COMPRESSION_RATIO", "ORDERLINESS_SCORE"),
            entry_components=(_VOLATILITY,),
        ),
        HistoryRequirement(
            "WEEKLY_SWING_LEVELS",
            _owner_path(swing_owner.detect_weekly_swing_levels),
            RULE_ROLLING_ROWS,
            SERIES_WEEKLY,
            (
                _p(
                    "window_rows",
                    weekly_swing["left_bars"] + weekly_swing["right_bars"] + 1,
                    f"{swing_path}.detect_weekly_swing_levels left_bars + right_bars + 1",
                ),
            ),
            entry_components=(_STRUCTURE,),
            note="the first confirmable weekly pivot; a support and a target cluster must also exist (data-dependent)",
        ),
        HistoryRequirement(
            "MONTHLY_SWING_LEVELS",
            _owner_path(swing_owner.detect_monthly_swing_levels),
            RULE_ROLLING_ROWS,
            SERIES_MONTHLY,
            (
                _p(
                    "window_rows",
                    monthly_swing["left_bars"] + monthly_swing["right_bars"] + 1,
                    f"{swing_path}.detect_monthly_swing_levels left_bars + right_bars + 1",
                ),
            ),
            entry_components=(_STRUCTURE,),
            note="optional for completeness: weekly levels alone can supply clusters",
        ),
        *(
            HistoryRequirement(input_id, OWNERLESS, RULE_UNDEFINED, SERIES_NONE, entry_components=(_STRUCTURE,), note=note)
            for input_id, note in (
                ("LEVEL_REACTION_MAGNITUDE", "no owner measures the level reaction"),
            )
        ),
        HistoryRequirement(
            "LEVEL_VOLUME_PERCENTILE", OWNERLESS, RULE_UNIMPLEMENTED_FALLBACK, SERIES_NONE,
            entry_components=(_STRUCTURE,),
            note="Rulebook 9.2 defines the core weights without volume; the frozen owner still requires volume even with zero weight. Implementation compatibility is unresolved, not a new percentile definition.",
        ),
        HistoryRequirement(
            "STRUCTURE_SCORE",
            _owner_path(structure_owner.calculate_structure_score_from_clusters),
            RULE_ALL_OF,
            SERIES_NONE,
            upstream=("WEEKLY_SWING_LEVELS", "LEVEL_REACTION_MAGNITUDE", "LEVEL_VOLUME_PERCENTILE"),
            entry_components=(_STRUCTURE,),
            note="STRUCTURE_SCORE_V1_2 weights level strength and entry location",
        ),
        HistoryRequirement(
            "CORE_REGIME_SCORE",
            _owner_path(regime_owner.calculate_regime_score),
            RULE_ALL_OF,
            SERIES_NONE,
            upstream=("TREND_SCORE", "FLOW_SCORE", "VOLATILITY_SCORE", "POSITIONING_SCORE"),
            note="CORE_MARKET_ONLY fallback (macro, on-chain and liquidity declared unavailable)",
        ),
        HistoryRequirement(
            "ENTRY_CONVICTION",
            _owner_path(entry_owner.calculate_entry_conviction),
            RULE_ALL_OF,
            SERIES_NONE,
            upstream=("TREND_SCORE", "FLOW_SCORE", "POSITIONING_SCORE", "VOLATILITY_SCORE", "STRUCTURE_SCORE"),
            entry_components=ENTRY_CONVICTION_COMPONENTS,
        ),
    ]
    ids = [item.input_id for item in requirements]
    if len(ids) != len(set(ids)):
        raise CoverageError("DUPLICATE_REQUIREMENT", "minimum-history input ids must be unique")
    known = set(ids)
    for item in requirements:
        missing = [name for name in item.upstream if name not in known and item.rule == RULE_ALL_OF]
        if missing:
            raise CoverageError("UNKNOWN_UPSTREAM", f"{item.input_id} names unknown upstream {missing}")
    return tuple(requirements)


@dataclass(frozen=True)
class ObservationSeries:
    """Observation instants of one series and when each became available."""

    name: str
    observations: tuple[tuple[datetime, datetime], ...]
    basis: str
    source: str

    def times(self) -> tuple[datetime, ...]:
        return tuple(observed for observed, _ in self.observations)


BASIS_MEASURED = "MEASURED_FROM_RESEARCH_DATABASE"
BASIS_PROJECTED = "PROJECTED_FROM_SOURCE_DEPTH"

STATUS_EVALUABLE = "EVALUABLE"
STATUS_UNDEFINED = "UNDEFINED_OWNERLESS"
STATUS_UNIMPLEMENTED_FALLBACK = "UNIMPLEMENTED_RULEBOOK_FALLBACK"
STATUS_NO_OBSERVATIONS = "NO_OBSERVATIONS"
STATUS_INSUFFICIENT = "INSUFFICIENT_HISTORY_IN_DATA_WINDOW"


@dataclass(frozen=True)
class EarliestEvaluable:
    input_id: str
    status: str
    observation_time: datetime | None = None
    available_at: datetime | None = None
    basis: str | None = None
    blocking_inputs: tuple[str, ...] = ()
    lower_bound_available_at: datetime | None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "input_id": self.input_id,
            "status": self.status,
            "observation_time": _iso(self.observation_time),
            "available_at": _iso(self.available_at),
            "available_date": self.available_at.date().isoformat() if self.available_at else None,
            "basis": self.basis,
            "blocking_inputs": list(self.blocking_inputs),
            "lower_bound_available_at": _iso(self.lower_bound_available_at),
        }


def lookback_rows_index(times: Sequence[datetime], lookback_rows: int) -> int | None:
    """Index of the first row with ``lookback_rows`` earlier rows."""

    return lookback_rows if len(times) > lookback_rows else None


def trailing_window_index(times: Sequence[datetime], window: timedelta, min_prior: int) -> int | None:
    """Index of the first observation with ``min_prior`` earlier observations in
    the half-open window ``[t - window, t)`` -- the positioning, volatility and
    certified liquidation owners' history predicate."""

    start = 0
    for index, current in enumerate(times):
        while start < index and times[start] < current - window:
            start += 1
        if index - start >= min_prior:
            return index
    return None


def earliest_evaluable_inputs(
    requirements: Sequence[HistoryRequirement],
    series: Mapping[str, ObservationSeries],
) -> dict[str, EarliestEvaluable]:
    """Simulate each requirement's rule over its observation instants."""

    by_id = {item.input_id: item for item in requirements}
    results: dict[str, EarliestEvaluable] = {}

    def resolve(input_id: str) -> EarliestEvaluable:
        if input_id in results:
            return results[input_id]
        requirement = by_id.get(input_id)
        if requirement is None:
            result = _series_result(input_id, series.get(input_id), lambda times: 0)
        elif requirement.rule == RULE_UNDEFINED:
            result = EarliestEvaluable(input_id, STATUS_UNDEFINED, blocking_inputs=(input_id,))
        elif requirement.rule == RULE_UNIMPLEMENTED_FALLBACK:
            result = EarliestEvaluable(input_id, STATUS_UNIMPLEMENTED_FALLBACK, blocking_inputs=(input_id,))
        elif requirement.rule == RULE_ALL_OF:
            result = _all_of(input_id, [resolve(name) for name in requirement.upstream])
        elif requirement.rule == RULE_LOOKBACK_ROWS:
            rows = requirement.parameter("lookback_rows")
            result = _series_result(input_id, series.get(requirement.series), lambda times: lookback_rows_index(times, rows))
        elif requirement.rule == RULE_ROLLING_ROWS:
            rows = requirement.parameter("window_rows")
            result = _series_result(input_id, series.get(requirement.series), lambda times: lookback_rows_index(times, rows - 1))
        elif requirement.rule == RULE_TRAILING_WINDOW:
            window = timedelta(days=requirement.parameter("window_days"))
            minimum = requirement.parameter("min_prior_observations")
            result = _series_result(
                input_id,
                series.get(requirement.series),
                lambda times: trailing_window_index(times, window, minimum),
            )
        elif requirement.rule == RULE_ETF_WINDOW:
            days = requirement.parameter("publication_days")
            result = _series_result(input_id, series.get(requirement.series), lambda times: lookback_rows_index(times, days - 1))
        else:
            raise CoverageError("UNKNOWN_RULE", requirement.rule)
        results[input_id] = result
        return result

    for requirement in requirements:
        resolve(requirement.input_id)
    return {item.input_id: results[item.input_id] for item in requirements}


def _series_result(
    input_id: str,
    observations: ObservationSeries | None,
    first_index: Callable[[tuple[datetime, ...]], int | None],
) -> EarliestEvaluable:
    if observations is None or not observations.observations:
        return EarliestEvaluable(input_id, STATUS_NO_OBSERVATIONS, basis=observations.basis if observations else None)
    index = first_index(observations.times())
    if index is None:
        return EarliestEvaluable(input_id, STATUS_INSUFFICIENT, basis=observations.basis)
    observed, available = observations.observations[index]
    return EarliestEvaluable(input_id, STATUS_EVALUABLE, observed, available, observations.basis)


def _all_of(input_id: str, members: Sequence[EarliestEvaluable]) -> EarliestEvaluable:
    blocking = tuple(sorted({name for member in members for name in member.blocking_inputs}))
    defined = [member for member in members if member.status == STATUS_EVALUABLE]
    basis = _combined_basis(member.basis for member in members)
    lacking = {m.input_id for m in members if m.status in (STATUS_NO_OBSERVATIONS, STATUS_INSUFFICIENT)}
    if lacking:
        status = STATUS_UNDEFINED if blocking else STATUS_NO_OBSERVATIONS
        return EarliestEvaluable(input_id, status, basis=basis, blocking_inputs=tuple(sorted(set(blocking) | lacking)))
    bounds = [m.available_at for m in defined if m.available_at]
    bounds += [m.lower_bound_available_at for m in members if m.lower_bound_available_at]
    lower_bound = max(bounds, default=None)
    if blocking:
        return EarliestEvaluable(input_id, STATUS_UNDEFINED, basis=basis, blocking_inputs=blocking, lower_bound_available_at=lower_bound)
    latest = max(defined, key=lambda member: member.available_at or datetime.min.replace(tzinfo=UTC))
    return EarliestEvaluable(input_id, STATUS_EVALUABLE, latest.observation_time, latest.available_at, basis)


def _combined_basis(values: Iterable[str | None]) -> str | None:
    present = {value for value in values if value}
    if not present:
        return None
    return BASIS_PROJECTED if BASIS_PROJECTED in present else BASIS_MEASURED


def venue_bar_series(missing_hours: Iterable[datetime]) -> dict[str, ObservationSeries]:
    """Complete daily, weekly and monthly buckets of one venue's data window.

    BTC-040 ``derive_ohlcv_bars`` decides completeness itself: it is called on
    timestamp-only stand-in bars (every price 1, volume 0), so its exact-hour
    census is reused, not restated, and no market value is read.
    """

    missing = {_utc(value) for value in missing_hours}
    hours: list[OhlcvBar] = []
    current = _DATA_START
    one_hour = timedelta(hours=1)
    unit = Decimal("1")
    while current < _HOLDOUT_START:
        if current not in missing:
            hours.append(
                OhlcvBar(current, "coverage", "coverage", "1h", unit, unit, unit, unit, Decimal("0"), "coverage", current + one_hour)
            )
        current += one_hour
    derived = derive_ohlcv_bars(hours, ("1d", "1w", "1mo"), ingested_at=_HOLDOUT_START)
    buckets: dict[str, list[tuple[datetime, datetime]]] = {"1d": [], "1w": [], "1mo": []}
    for bar in derived:
        buckets[bar.timeframe].append((bar.timestamp, _bucket_end(bar.timestamp, bar.timeframe)))
    daily = tuple(sorted(buckets["1d"]))
    rv_source = volatility_owner.volatility_percentile.__kwdefaults__["source_feature_id"]
    rv_window = next(window for window, name in volatility_owner.REALIZED_VOLATILITY_FEATURE_IDS.items() if name == rv_source)
    source = "raw.btc_ohlcv data-window hours (missing hours from the coverage snapshot)"
    return {
        SERIES_DAILY: ObservationSeries(SERIES_DAILY, daily, BASIS_MEASURED, source),
        SERIES_WEEKLY: ObservationSeries(SERIES_WEEKLY, tuple(sorted(buckets["1w"])), BASIS_MEASURED, source),
        SERIES_MONTHLY: ObservationSeries(SERIES_MONTHLY, tuple(sorted(buckets["1mo"])), BASIS_MEASURED, source),
        SERIES_RV_20: ObservationSeries(SERIES_RV_20, daily[rv_window:], BASIS_MEASURED, f"{rv_source} results on the daily bars"),
    }


def _bucket_end(start: datetime, timeframe: str) -> datetime:
    if timeframe == "1d":
        return start + timedelta(days=1)
    if timeframe == "1w":
        return start + timedelta(days=7)
    year, month = (start.year + 1, 1) if start.month == 12 else (start.year, start.month + 1)
    return start.replace(year=year, month=month)


def _regular_series(name: str, first: datetime, step: timedelta, *, lag: timedelta, source: str) -> ObservationSeries:
    values = []
    current = first
    while current < _HOLDOUT_START:
        values.append((current, current + lag))
        current += step
    return ObservationSeries(name, tuple(values), BASIS_PROJECTED, source)


def projected_shared_series() -> dict[str, ObservationSeries]:
    """Shared non-price series as the selected sources would supply them.

    The research database holds no row of these families, so their instants
    are projected from each selected source's measured first instant and
    cadence (see :data:`SOURCE_CANDIDATES`), restricted to the data window.
    """

    hour = timedelta(hours=1)
    day = timedelta(days=1)
    funding_step = timedelta(hours=8)
    # Binance USD-M BTCUSDT settles every 8 h from 2020-01-01 00:00; that first
    # settlement prices a 2019 period, which RBT-001 admission refuses.
    funding = _regular_series(
        SERIES_FUNDING, _DATA_START + funding_step, funding_step, lag=timedelta(0), source="binance_usdm_btcusdt_funding_archive"
    )
    oi = _regular_series(
        "OPEN_INTEREST_SNAPSHOTS", datetime(2020, 9, 1, tzinfo=UTC), hour, lag=timedelta(0), source="binance_usdm_btcusdt_metrics_archive (hourly sampling)"
    )
    growth_window = timedelta(days=positioning_owner.DEFAULT_OI_GROWTH_WINDOW_DAYS)
    oi_first = oi.observations[0][0]
    oi_growth = ObservationSeries(
        SERIES_OI_GROWTH,
        tuple(item for item in oi.observations if item[0] - growth_window >= oi_first),
        BASIS_PROJECTED,
        oi.source,
    )
    basis = _regular_series(
        SERIES_BASIS, datetime(2020, 8, 1, 1, tzinfo=UTC), hour, lag=timedelta(0), source="binance_coinm_quarterly_basis (hourly close snapshots)"
    )
    # Market cap for UTC day D is pinned at observation_time D+1 00:00 and is
    # available at D+2 00:00; the first admitted day is 2020-01-01.
    market_cap = {
        observed: available
        for observed, available in (
            (_DATA_START + (index + 1) * day, _DATA_START + (index + 2) * day)
            for index in range((_HOLDOUT_START - _DATA_START).days)
        )
        if observed < _HOLDOUT_START
    }
    intensity = ObservationSeries(
        SERIES_OI_INTENSITY,
        tuple((observed, max(available, market_cap[observed])) for observed, available in oi.observations if observed in market_cap),
        BASIS_PROJECTED,
        "OI snapshots joined to coinmetrics_community_capmrktcurusd by exact observation_time",
    )
    liquidation_first_day = datetime(2021, 5, 28, tzinfo=UTC)
    liquidations = _regular_series(
        SERIES_LIQUIDATION_DAYS, liquidation_first_day, day, lag=day, source="kraken_futures_rest_executions (first complete UTC day)"
    )
    holidays = load_closures(CLOSURE_TABLE_COVERAGE_START, CLOSURE_TABLE_COVERAGE_END)
    publication_days = expected_etf_publication_dates(
        start=ETF_ERA_FIRST_TRADING_DATE,
        end=(_HOLDOUT_START - day).date(),
        market_holidays=holidays,
    )
    etf = ObservationSeries(
        SERIES_ETF_DAYS,
        tuple((datetime.combine(item, datetime.min.time(), tzinfo=UTC), etf_flow_scheduled_available_at(item)) for item in publication_days),
        BASIS_PROJECTED,
        f"US spot bitcoin ETF publication days from {ETF_ERA_FIRST_TRADING_DATE.isoformat()} ({CLOSURE_TABLE_VERSION})",
    )
    return {
        SERIES_FUNDING: funding,
        SERIES_OI_GROWTH: oi_growth,
        SERIES_BASIS: basis,
        SERIES_OI_INTENSITY: intensity,
        SERIES_LIQUIDATION_DAYS: liquidations,
        SERIES_ETF_DAYS: etf,
    }


# --- read-only database coverage --------------------------------------------------

_FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|UPSERT|CREATE|ALTER|DROP|TRUNCATE|GRANT|REVOKE|COPY|CALL|DO|SET|RESET|"
    r"LOCK|VACUUM|ANALYZE|REINDEX|CLUSTER|COMMENT|REFRESH|NOTIFY|LISTEN|UNLISTEN|PREPARE|EXECUTE|"
    r"DEALLOCATE|DISCARD|BEGIN|COMMIT|ROLLBACK|SAVEPOINT|RETURNING|INTO|FOR)\b",
    re.IGNORECASE,
)
_LEADING_TAG = re.compile(r"^\s*/\*[^*]*\*/\s*")
_SKIPPED_TABLE_PATTERN = re.compile(r"trusted|acquisition|attestation|calendar", re.IGNORECASE)


def require_select_only(sql: str) -> str:
    """Refuse anything but a single read-only ``SELECT`` statement."""

    body = _LEADING_TAG.sub("", sql, count=1).strip()
    if ";" in body:
        raise CoverageError("NON_SELECT_SQL_REFUSED", "statement separators are not allowed")
    if not re.match(r"(?is)^(SELECT|WITH)\b", body):
        raise CoverageError("NON_SELECT_SQL_REFUSED", "only SELECT statements may run")
    match = _FORBIDDEN_SQL.search(body)
    if match:
        raise CoverageError("NON_SELECT_SQL_REFUSED", f"forbidden keyword {match.group(1)!r}")
    return sql


def _select(connection: Any, sql: str, params: Mapping[str, Any] | None = None) -> list[tuple[Any, ...]]:
    from sqlalchemy import text

    require_select_only(sql)
    result = connection.execute(text(sql), dict(params or {}))
    return [tuple(row) for row in result.all()]


@dataclass(frozen=True)
class RawTableSpec:
    table: str
    families: tuple[str, ...]
    time_column: str
    series_columns: tuple[str, ...]
    extra_time_columns: tuple[str, ...]
    grid_timeframe_column: str | None = None
    is_date: bool = False
    gap_threshold: timedelta | None = None
    schema_semantics: str = ""

    @property
    def qualified(self) -> str:
        return f"raw.{self.table}"


_QUALITY_DEFAULTS = DerivativesQualityConfig()
RAW_TABLE_SPECS: tuple[RawTableSpec, ...] = (
    RawTableSpec(
        "btc_ohlcv",
        (REFERENCE_PRICE_FAMILY, SHARED_VOLUME_FAMILY),
        "timestamp",
        ("exchange", "symbol", "timeframe", "provider"),
        ("ingested_at",),
        grid_timeframe_column="timeframe",
        schema_semantics="bar start timestamp (BTC-020; next_bar_timestamp closes the interval)",
    ),
    RawTableSpec(
        "etf_flows",
        (ETF_FLOW_FAMILY,),
        "observation_date",
        ("fund", "provider"),
        ("available_at", "ingested_at"),
        is_date=True,
        schema_semantics="US trading date; a revision column exists, no source publication-time column",
    ),
    RawTableSpec(
        "funding_rates",
        (FUNDING_RATE_FAMILY,),
        "observation_time",
        ("exchange", "symbol", "instrument", "provider"),
        ("available_at", "ingested_at"),
        gap_threshold=_QUALITY_DEFAULTS.max_funding_staleness,
        schema_semantics="'UTC funding timestamp or period end reported by the exchange' (SETTLEMENT)",
    ),
    RawTableSpec(
        "open_interest",
        (OPEN_INTEREST_FAMILY,),
        "observation_time",
        ("exchange", "symbol", "instrument", "provider"),
        ("available_at", "ingested_at"),
        gap_threshold=_QUALITY_DEFAULTS.max_provider_gap,
        schema_semantics="'UTC market timestamp for the open-interest snapshot' (SNAPSHOT)",
    ),
    RawTableSpec(
        "futures_basis",
        (FUTURES_BASIS_FAMILY,),
        "observation_time",
        ("exchange", "symbol", "instrument", "expiry", "provider"),
        ("available_at", "ingested_at"),
        gap_threshold=_QUALITY_DEFAULTS.max_provider_gap,
        schema_semantics="'UTC market timestamp for the basis observation'; no timeframe column (SNAPSHOT)",
    ),
    RawTableSpec(
        "liquidations",
        (LIQUIDATION_FAMILY,),
        "observation_time",
        ("exchange", "symbol", "timeframe", "side", "provider"),
        ("available_at", "ingested_at"),
        grid_timeframe_column="timeframe",
        schema_semantics=(
            "'UTC bar timestamp or period end for liquidation aggregation'; the primary key holds one row per "
            "(instant, timeframe, side, provider), so rows are per-side interval aggregates, not events"
        ),
    ),
    RawTableSpec(
        "perp_volume",
        (PERP_VOLUME_FAMILY,),
        "observation_time",
        ("exchange", "symbol", "timeframe", "provider"),
        ("available_at", "ingested_at"),
        grid_timeframe_column="timeframe",
        schema_semantics="'UTC bar timestamp or period end' (start or end is not fixed by the schema)",
    ),
    RawTableSpec(
        "generic_series",
        (MARKET_CAP_FAMILY, MACRO_ONCHAIN_LIQUIDITY_FAMILY),
        "observation_time",
        ("series_id", "provider"),
        ("available_at", "ingested_at"),
        schema_semantics="generic macro/on-chain series; not an EPIC Y market-cap target (policy V3 section 5)",
    ),
)
_OTHER_SCHEMAS = ("derived", "signals", "portfolio", "system", "research", "public")


def _window_predicates(column: str, *, is_date: bool) -> dict[str, str]:
    suffix = "_date" if is_date else ""
    quoted = f'"{column}"'
    return {
        PROHIBITED_WINDOW.window_id: f"{quoted} < :data_start{suffix}",
        DATA_WINDOW.window_id: f"{quoted} >= :data_start{suffix} AND {quoted} < :holdout_start{suffix}",
        HOLDOUT_WINDOW.window_id: f"{quoted} >= :holdout_start{suffix} AND {quoted} < :reserve_start{suffix}",
        RESERVE_WINDOW.window_id: f"{quoted} >= :reserve_start{suffix}",
    }


def _window_params() -> dict[str, Any]:
    return {
        "data_start": _DATA_START,
        "holdout_start": _HOLDOUT_START,
        "reserve_start": _RESERVE_START,
        "data_start_date": _DATA_START.date(),
        "holdout_start_date": _HOLDOUT_START.date(),
        "reserve_start_date": _RESERVE_START.date(),
    }


def window_count_sql(spec: RawTableSpec) -> str:
    """Per series and window: row counts plus MIN/MAX of time columns only."""

    predicates = _window_predicates(spec.time_column, is_date=spec.is_date)
    series = ", ".join(f'"{column}"' for column in spec.series_columns)
    time_columns = (spec.time_column, *spec.extra_time_columns)
    aggregates = []
    for window in COVERAGE_WINDOWS:
        predicate = predicates[window.window_id]
        aggregates.append(f"COUNT(*) FILTER (WHERE {predicate})")
        for column in time_columns:
            aggregates.append(f'MIN("{column}") FILTER (WHERE {predicate})')
            aggregates.append(f'MAX("{column}") FILTER (WHERE {predicate})')
    return (
        f"/* rbt002:window_counts:{spec.qualified} */ SELECT {series}, {', '.join(aggregates)} "
        f"FROM {spec.qualified} GROUP BY {series} ORDER BY {series}"
    )


def data_window_times_sql(spec: RawTableSpec) -> str:
    """Series keys and observation instants inside the data window only."""

    series = ", ".join(f'"{column}"' for column in spec.series_columns)
    predicate = _window_predicates(spec.time_column, is_date=spec.is_date)[DATA_WINDOW.window_id]
    return (
        f'/* rbt002:data_window_times:{spec.qualified} */ SELECT {series}, "{spec.time_column}" '
        f'FROM {spec.qualified} WHERE {predicate} ORDER BY {series}, "{spec.time_column}"'
    )


def availability_lag_sql(spec: RawTableSpec) -> str:
    """Data-window range of ``available_at - observation_time``, in seconds."""

    series = ", ".join(f'"{column}"' for column in spec.series_columns)
    predicate = _window_predicates(spec.time_column, is_date=spec.is_date)[DATA_WINDOW.window_id]
    lag = f'EXTRACT(EPOCH FROM ("available_at" - "{spec.time_column}"))'
    return (
        f"/* rbt002:availability_lag:{spec.qualified} */ SELECT {series}, MIN({lag}), MAX({lag}) "
        f"FROM {spec.qualified} WHERE {predicate} GROUP BY {series} ORDER BY {series}"
    )


def etf_revision_sql() -> str:
    predicate = _window_predicates("observation_date", is_date=True)[DATA_WINDOW.window_id]
    return (
        '/* rbt002:etf_revisions:raw.etf_flows */ SELECT "fund", "provider", COUNT(DISTINCT "revision"), '
        f'COUNT(*) FROM raw.etf_flows WHERE {predicate} GROUP BY "fund", "provider" ORDER BY "fund", "provider"'
    )


SERVER_FACTS_SQL = (
    "/* rbt002:server_facts */ SELECT current_setting('server_version'), current_database(), "
    "current_setting('default_transaction_read_only'), current_setting('transaction_read_only')"
)
SCHEMAS_SQL = "/* rbt002:schemas */ SELECT schema_name FROM information_schema.schemata ORDER BY schema_name"
OTHER_TIME_COLUMNS_SQL = (
    "/* rbt002:other_time_columns */ SELECT table_schema, table_name, column_name, data_type "
    "FROM information_schema.columns WHERE table_schema IN :schemas AND data_type IN "
    "('timestamp with time zone', 'timestamp without time zone', 'date') "
    "ORDER BY table_schema, table_name, ordinal_position"
)


def _total_rows_sql(qualified: str) -> str:
    return f"/* rbt002:total_rows:{qualified} */ SELECT COUNT(*) FROM {qualified}"


def _other_column_sql(schema: str, table: str, column: str, *, is_date: bool) -> str:
    predicates = _window_predicates(column, is_date=is_date)
    windows = ", ".join(f"COUNT(*) FILTER (WHERE {predicates[window.window_id]})" for window in COVERAGE_WINDOWS)
    return (
        f'/* rbt002:other_column:{schema}.{table}.{column} */ SELECT COUNT(*), {windows}, MIN("{column}"), MAX("{column}") '
        f'FROM "{schema}"."{table}"'
    )


def open_research_engine() -> Any:
    """A read-only engine over the environment's research database.

    The URL comes from ``btc019_empirical._database_url_from_environment`` and
    is never printed or persisted.
    """

    from sqlalchemy import create_engine

    from btc_predictor.research.btc019_empirical import _database_url_from_environment

    return create_engine(_database_url_from_environment()).execution_options(postgresql_readonly=True)


def collect_database_coverage(connection: Any, *, collected_at: datetime) -> dict[str, Any]:
    """Collect the coverage snapshot with read-only ``SELECT`` statements.

    Rows before 2020-01-01 or inside the holdout and reserve windows appear only
    in ``COUNT``/``MIN``/``MAX`` aggregates over time columns. Data-window rows
    are read as series keys and observation instants. No value column is read.
    """

    server_version, database, default_read_only, transaction_read_only = _select(connection, SERVER_FACTS_SQL)[0]
    if default_read_only != "on":
        raise CoverageError("DATABASE_NOT_READ_ONLY", "default_transaction_read_only must be 'on'")
    schemas = [row[0] for row in _select(connection, SCHEMAS_SQL)]
    params = _window_params()
    tables: dict[str, Any] = {}
    for spec in RAW_TABLE_SPECS:
        total = int(_select(connection, _total_rows_sql(spec.qualified))[0][0])
        window_rows = _select(connection, window_count_sql(spec), params) if total else []
        times = _select(connection, data_window_times_sql(spec), params) if total else []
        lags = (
            _select(connection, availability_lag_sql(spec), params)
            if total and "available_at" in spec.extra_time_columns and not spec.is_date
            else []
        )
        revisions = _select(connection, etf_revision_sql(), params) if total and spec.table == "etf_flows" else []
        tables[spec.qualified] = summarize_raw_table(
            spec,
            total_rows=total,
            window_rows=window_rows,
            data_window_times=times,
            availability_lags=lags,
            etf_revisions=revisions,
        )
    other_columns = []
    columns = _select(connection, OTHER_TIME_COLUMNS_SQL.replace(":schemas", _in_list(_OTHER_SCHEMAS)))
    for schema, table, column, data_type in columns:
        if _SKIPPED_TABLE_PATTERN.search(table):
            other_columns.append({"table": f"{schema}.{table}", "column": column, "skipped": "trusted-acquisition or calendar persistence: not read"})
            continue
        row = _select(connection, _other_column_sql(schema, table, column, is_date=data_type == "date"), params)[0]
        total, prohibited, data, holdout, reserve, first, last = row
        other_columns.append(
            {
                "table": f"{schema}.{table}",
                "column": column,
                "rows": int(total),
                "window_rows": {
                    PROHIBITED_WINDOW.window_id: int(prohibited),
                    DATA_WINDOW.window_id: int(data),
                    HOLDOUT_WINDOW.window_id: int(holdout),
                    RESERVE_WINDOW.window_id: int(reserve),
                },
                "min": _iso_any(first),
                "max": _iso_any(last),
            }
        )
    return {
        "snapshot_version": DATABASE_COVERAGE_SNAPSHOT_VERSION,
        "collected_at": _iso(_utc(collected_at)),
        "server": {
            "server_version": str(server_version),
            "database": str(database),
            "default_transaction_read_only": str(default_read_only),
            "transaction_read_only": str(transaction_read_only),
            "engine_execution_options": {"postgresql_readonly": True},
        },
        "schemas": sorted(schemas),
        "raw_tables": tables,
        "other_time_columns": other_columns,
    }


def _in_list(values: Sequence[str]) -> str:
    for value in values:
        if not re.fullmatch(r"[a-z_]+", value):
            raise CoverageError("UNSAFE_IDENTIFIER", value)
    return "(" + ", ".join(f"'{value}'" for value in values) + ")"


def summarize_raw_table(
    spec: RawTableSpec,
    *,
    total_rows: int,
    window_rows: Sequence[Sequence[Any]],
    data_window_times: Sequence[Sequence[Any]],
    availability_lags: Sequence[Sequence[Any]] = (),
    etf_revisions: Sequence[Sequence[Any]] = (),
) -> dict[str, Any]:
    """Summarise one raw table from timestamp-only query results."""

    key_width = len(spec.series_columns)
    time_columns = (spec.time_column, *spec.extra_time_columns)
    series: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in window_rows:
        key = tuple(row[:key_width])
        values = list(row[key_width:])
        windows: dict[str, Any] = {}
        for window in COVERAGE_WINDOWS:
            count = int(values.pop(0))
            ranges = {}
            for column in time_columns:
                first, last = values.pop(0), values.pop(0)
                ranges[column] = {"min": _iso_any(first), "max": _iso_any(last)}
            windows[window.window_id] = {"rows": count, **ranges}
        series[key] = {"key": dict(zip(spec.series_columns, (_iso_any(item) for item in key))), "windows": windows}
    observed: dict[tuple[Any, ...], list[Any]] = {}
    for row in data_window_times:
        observed.setdefault(tuple(row[:key_width]), []).append(row[key_width])
    lags = {tuple(row[:key_width]): (row[key_width], row[key_width + 1]) for row in availability_lags}
    revisions = {tuple(row[:key_width]): (int(row[key_width]), int(row[key_width + 1])) for row in etf_revisions}
    for key, entry in series.items():
        times = observed.get(key, [])
        entry["data_window"] = _data_window_summary(spec, key, times)
        if key in lags:
            low, high = lags[key]
            entry["data_window"]["availability_lag_seconds"] = {"min": _number(low), "max": _number(high)}
        if key in revisions:
            entry["data_window"]["distinct_revision_labels"] = revisions[key][0]
    exposure = {
        window.window_id: sum(entry["windows"][window.window_id]["rows"] for entry in series.values())
        for window in COVERAGE_WINDOWS
    }
    return {
        "families": list(spec.families),
        "time_column": spec.time_column,
        "series_columns": list(spec.series_columns),
        "total_rows": int(total_rows),
        "window_rows": exposure,
        "timestamp_semantics": _table_semantics(spec, series),
        "publication_time_column": False,
        "revision_history_column": spec.table == "etf_flows",
        "series": [series[key] for key in sorted(series, key=lambda item: tuple(str(part) for part in item))],
    }


def _data_window_summary(spec: RawTableSpec, key: tuple[Any, ...], times: Sequence[Any]) -> dict[str, Any]:
    if spec.is_date:
        dates = sorted({value if isinstance(value, date) and not isinstance(value, datetime) else _utc(value).date() for value in times})
        return {"observations": len(times), "first": _iso_any(dates[0]) if dates else None, "last": _iso_any(dates[-1]) if dates else None, "grid": "US_TRADING_DATES"}
    instants = sorted(_utc(value) for value in times)
    summary: dict[str, Any] = {
        "observations": len(instants),
        "distinct_instants": len(set(instants)),
        "first": _iso(instants[0]) if instants else None,
        "last": _iso(instants[-1]) if instants else None,
    }
    if spec.grid_timeframe_column is not None:
        timeframe = str(key[spec.series_columns.index(spec.grid_timeframe_column)])
        summary["grid"] = timeframe
        expected_end = _last_grid_start(timeframe)
        missing = missing_bar_timestamps(instants, start=_DATA_START, end=expected_end, timeframe=timeframe) if expected_end else ()
        grid = set(_expected_grid(timeframe))
        summary["misaligned"] = sum(1 for value in instants if value not in grid)
        summary["missing"] = len(missing)
        summary["missing_runs"] = _runs(missing, timeframe)
        summary["starts_at_window_start"] = bool(instants) and instants[0] == _DATA_START
        summary["ends_at_last_window_grid_start"] = bool(instants) and instants[-1] == expected_end
    elif spec.gap_threshold is not None and len(instants) > 1:
        spacings = [later - earlier for earlier, later in zip(instants, instants[1:]) if later != earlier]
        large = [(earlier, later) for earlier, later in zip(instants, instants[1:]) if later - earlier > spec.gap_threshold]
        summary["max_spacing_seconds"] = int(max(spacings).total_seconds()) if spacings else 0
        summary["discontinuity_threshold_seconds"] = int(spec.gap_threshold.total_seconds())
        summary["discontinuities"] = [[_iso(a), _iso(b)] for a, b in large]
    return summary


def _last_grid_start(timeframe: str) -> datetime | None:
    starts = _expected_grid(timeframe)
    return starts[-1] if starts else None


def _expected_grid(timeframe: str) -> tuple[datetime, ...]:
    from btc_predictor.data import next_bar_timestamp

    values = []
    current = _DATA_START
    while current < _HOLDOUT_START and next_bar_timestamp(current, timeframe) <= _HOLDOUT_START:
        values.append(current)
        current = next_bar_timestamp(current, timeframe)
    return tuple(values)


def _runs(missing: Sequence[datetime], timeframe: str) -> list[list[Any]]:
    from btc_predictor.data import next_bar_timestamp

    runs: list[list[Any]] = []
    for value in missing:
        if runs and next_bar_timestamp(runs[-1][1], timeframe) == value:
            runs[-1][1] = value
            runs[-1][2] += 1
        else:
            runs.append([value, value, 1])
    return [[_iso(first), _iso(last), count] for first, last, count in runs]


def _table_semantics(spec: RawTableSpec, series: Mapping[tuple[Any, ...], Mapping[str, Any]]) -> dict[str, Any]:
    if not series:
        return {"from_schema": spec.schema_semantics, "from_data": "NO_PERSISTED_ROWS: not confirmable from data"}
    if spec.grid_timeframe_column is None:
        return {"from_schema": spec.schema_semantics, "from_data": "NO_GRID_TEST_DEFINED: schema reading retained"}
    verdicts = [_series_stamp_verdict(entry) for entry in series.values() if entry["data_window"]["observations"]]
    if verdicts and all(verdict == STAMPS_CONSISTENT_WITH_START for verdict in verdicts):
        verdict = (
            f"{STAMPS_CONSISTENT_WITH_START}: every series is grid-aligned, its data-window stamps run from the "
            "window start through the last start-grid point, and it has no holdout row. Stamps alone cannot "
            "exclude end stamping (a collection truncated at the same stamps would look identical); the "
            "collector's provider mapping must pin it"
        )
    elif STAMPS_INCONSISTENT in verdicts:
        verdict = f"{STAMPS_INCONSISTENT}: at least one series has stamps off the {spec.grid_timeframe_column} grid"
    else:
        verdict = f"{STAMPS_NOT_CONFIRMABLE}: a series does not span the whole data window, so its stamps cannot show start versus end"
    return {"from_schema": spec.schema_semantics, "from_data": verdict}


STAMPS_CONSISTENT_WITH_START = "CONSISTENT_WITH_INTERVAL_START"
STAMPS_INCONSISTENT = "INCONSISTENT_WITH_THE_GRID"
STAMPS_NOT_CONFIRMABLE = "NOT_CONFIRMABLE_FROM_STAMPS"


def _series_stamp_verdict(entry: Mapping[str, Any]) -> str:
    window = entry["data_window"]
    if window.get("misaligned"):
        return STAMPS_INCONSISTENT
    holdout_rows = entry["windows"][HOLDOUT_WINDOW.window_id]["rows"]
    if window.get("starts_at_window_start") and window.get("ends_at_last_window_grid_start") and holdout_rows == 0:
        return STAMPS_CONSISTENT_WITH_START
    return STAMPS_NOT_CONFIRMABLE


def rebuild_missing_hours(snapshot: Mapping[str, Any], *, exchange: str, symbol: str, provider: str) -> tuple[datetime, ...]:
    """Expand one venue's recorded missing-hour runs from a coverage snapshot."""

    table = snapshot["raw_tables"]["raw.btc_ohlcv"]
    for entry in table["series"]:
        key = entry["key"]
        if (key["exchange"], key["symbol"], key["provider"], key["timeframe"]) == (exchange, symbol, provider, "1h"):
            values = []
            for first, last, count in entry["data_window"]["missing_runs"]:
                current = _utc(datetime.fromisoformat(first))
                for _ in range(count):
                    values.append(current)
                    current += timedelta(hours=1)
                if values[-1] != _utc(datetime.fromisoformat(last)):
                    raise CoverageError("SNAPSHOT_INCONSISTENT", "a missing-hour run does not end where recorded")
            return tuple(values)
    return ()


def _venue_present(snapshot: Mapping[str, Any], *, exchange: str, symbol: str, provider: str) -> bool:
    table = snapshot["raw_tables"]["raw.btc_ohlcv"]
    return any(
        (entry["key"]["exchange"], entry["key"]["symbol"], entry["key"]["provider"], entry["key"]["timeframe"]) == (exchange, symbol, provider, "1h")
        and entry["data_window"]["observations"] > 0
        for entry in table["series"]
    )


# --- metadata probes (provenance only; no third-party value is stored) ------------------


@dataclass(frozen=True)
class ProbeEvidence:
    """One metadata probe: where, when, what came back, and what it showed.

    ``observed`` holds metadata only: schemas, first instants, counts, plan
    terms and HTTP outcomes. ``response_sha256`` binds the exact bytes retrieved
    on :data:`SOURCE_PROBE_DATE`; the bytes themselves are not stored.
    """

    probe_id: str
    url: str
    http_status: int | None
    response_bytes: int | None
    response_sha256: str | None
    observed: tuple[tuple[str, str], ...]

    def as_record(self) -> dict[str, Any]:
        return {
            "probe_id": self.probe_id,
            "retrieved_on": SOURCE_PROBE_DATE,
            "url": self.url,
            "http_status": self.http_status,
            "response_bytes": self.response_bytes,
            "response_sha256": self.response_sha256,
            "observed": dict(self.observed),
        }


def _probe(probe_id: str, url: str, status: int | None, size: int | None, digest: str | None, **observed: str) -> ProbeEvidence:
    return ProbeEvidence(probe_id, url, status, size, digest, tuple(sorted(observed.items())))


_KRAKEN_EXECUTIONS = "https://futures.kraken.com/api/history/v2/market/PI_XBTUSD/executions"
_KRAKEN_ANALYTICS = "https://futures.kraken.com/api/charts/v1/analytics/PI_XBTUSD"
_BINANCE = "https://data.binance.vision/data"

PROBE_EVIDENCE: tuple[ProbeEvidence, ...] = (
    _probe("kraken_rest_executions_since_2018", f"{_KRAKEN_EXECUTIONS}?since=1514764800000&sort=asc", 200, 812598,
           "7f76a6212f31bc226bb93a0151e785e8462ef9a755b75cbe53394bfcef932f42",
           earliest_execution="2021-05-27T11:55:25.097+00:00",
           schema="elements[].event.Execution.execution{uid,timestamp,price,quantity,usdValue,markPrice,limitFilled,takerOrder,makerOrder}"),
    _probe("kraken_rest_executions_before_2020", f"{_KRAKEN_EXECUTIONS}?before=1577836800000&sort=desc", 200, 23,
           "c94188f9c9003d1e1b499232bb157f55a5705cf1f84fdca1f354d41e8739c1cc", elements="0"),
    _probe("kraken_rest_executions_2022_11_09", f"{_KRAKEN_EXECUTIONS}?since=1668002400000&sort=asc", 200, 809466,
           "c79c0d032d4907ba1e9bfd17f95d50bddcb7901a2d78447d8d894b777894a492",
           liquidation_identification="takerOrder.orderType == 'Liquidation' (6 of the first 1000 fills; 87 of 8000 over 8 pages)",
           order_types_seen="taker: IoC, Limit, Liquidation; maker: Limit, Post"),
    _probe("kraken_v3_history_recent_typing", "https://futures.kraken.com/derivatives/api/v3/history?symbol=PI_XBTUSD", 200, None, None,
           uid_overlap_with_v2="95 of 100 recent v3 trades share a uid with v2 executions",
           liquidations_in_window="0 (type 'liquidation' vs orderType 'Liquidation' equivalence UNVERIFIED)",
           lastTime_2022="returns 0 trades: recent history only",
           window_note="reserve-window trades; only type labels and uids were compared"),
    _probe("kraken_v4_historical_funding_rates", "https://futures.kraken.com/derivatives/api/v4/historicalfundingrates?symbol=PI_XBTUSD", 200, None, None,
           depth="rolling trailing year (first 2025-10-01T08:00Z), hourly settlements",
           range_filter="none: the response includes holdout and reserve rows; timestamps only were inspected, never values",
           not_re_requested="deliberately not re-fetched for hashing"),
    _probe("kraken_analytics_liquidation_volume_2020_02_25", f"{_KRAKEN_ANALYTICS}/liquidation-volume?interval=3600&since=1582588800&to=1582675200", 200, 62,
           "a55d741d4189baa59c2150cade2876c0bcbe25296454d8b4ec8974bd39d6101f", timestamps="0"),
    _probe("kraken_analytics_liquidation_volume_2020_02_26", f"{_KRAKEN_ANALYTICS}/liquidation-volume?interval=3600&since=1582675200&to=1582761600", 200, 292,
           "d803c7c8b6ae74b1feaf7d96b1d4844c0684a020a35dfb8218b4401f5b673c6c",
           first_day="2020-02-26", hourly_grid="every hour present with explicit zeros (169/169 slots over 2023-03-05..12)",
           shape="one total per hour (no side split, no event ids)"),
    _probe("kraken_analytics_open_interest_2023_03_06", f"{_KRAKEN_ANALYTICS}/open-interest?interval=3600&since=1678060800&to=1678147200", 200, 62,
           "a55d741d4189baa59c2150cade2876c0bcbe25296454d8b4ec8974bd39d6101f", timestamps="0"),
    _probe("kraken_analytics_open_interest_2023_03_07", f"{_KRAKEN_ANALYTICS}/open-interest?interval=3600&since=1678147200&to=1678233600", 200, 858,
           "49398c54d4418a42b15c9b0272c3c8a286075e802f2925638ea510591197b781", first_day="2023-03-07"),
    _probe("tardis_exchange_cryptofacilities", "https://api.tardis.dev/v1/exchanges/cryptofacilities", 200, 503867,
           "f54d6bdc5ec55ab81eed2ab6630e3d5a51228d6c7c7fe927b10f1cccd6fcfbeb",
           pi_xbtusd_available_since="2019-03-30T00:00:00.000Z",
           pi_xbtusd_data_types="trades, incremental_book_L2, quotes, book_snapshot_5, book_snapshot_25, derivative_ticker, liquidations, book_ticker",
           recorded_feed="wss://futures.kraken.com/ws/v1 (the EPIC X capture endpoint)",
           incidents_in_data_window="2021-11-10T05:09Z..05:19Z (~10 minute gap)"),
    _probe("tardis_billing_faq", "https://docs.tardis.dev/faq/billing-and-subscriptions", 200, 1292412,
           "f90165cfe47a0a210a70f90d89ffaf0769c5af6ac728953463de30ec99a110bb",
           history_yearly="Academic/Solo/Pro: 4 years back from the start date; Business: all since 2019-03-30",
           history_quarterly="12 months", history_monthly="4 months (Solo, Pro, Business)",
           academic="quarterly or yearly billing only; eligibility confirmation required",
           one_off_purchases="none: subscriptions only", perpetuals_plan_includes="Kraken Futures: all perpetual swaps"),
    _probe("tardis_home_pricing", "https://tardis.dev/", 200, 378354,
           "a62253ee0a1ed7222d02ac4442380b4f15f0dc8c124f10f1f947e526bacab0b0",
           perpetuals_plan_monthly_price_usd="Academic 350, Solo 700, Professional 1000, Business 3000",
           all_exchanges_plan_monthly_price_usd="Academic 650, Solo 1200, Professional 2200, Business 6000"),
    _probe("tardis_free_liquidations_2022_01_01", "https://datasets.tardis.dev/v1/cryptofacilities/liquidations/2022/01/01/PI_XBTUSD.csv.gz", 200, 1063,
           "8e17bc9aa6e3bcdaadce2ee5e0843f5ef1b7648e4c84c6dbd9b631312c70d707",
           header="exchange,symbol,timestamp,local_timestamp,id,side,price,amount",
           free_sample="first day of each month downloadable without an API key"),
    _probe("coinalyze_api_doc", "https://api.coinalyze.net/v1/doc/", 200, 1216661,
           "ac89beae88790819d13e5b91f28ad47e78987a2582c2b5c20bf62ec567655415",
           retention="intraday keeps 1500-2000 points (old data deleted daily); daily granularity is never deleted",
           liquidation_history_shape="[{symbol, history:[{t,l,s}]}] (long and short per interval)",
           terms="free; cite Coinalyze when used in public places", auth="api_key required"),
    _probe("coinalyze_future_markets_no_key", "https://api.coinalyze.net/v1/future-markets", 401, 37,
           "c8f7734cc6e1841a66ac66a84f056c4dcfd08c55f6d11d8bfc0e4fc1fe6a16fc",
           result="Invalid/Missing API key (COINALYZE_API_KEY not set): depth UNVERIFIED"),
    _probe("coinglass_pricing", "https://www.coinglass.com/pricing", 200, 332721,
           "9fb6093979498b75107cf96593fed8dd96cfead754f13d8f6f109ec53d00ad1e",
           hobbyist="USD 29/month billed monthly; USD 348/year billed annually; personal use; 30 requests/min",
           startup="USD 79/month; personal use", standard="USD 299/month; commercial use",
           hobbyist_history="1d interval: all-time; 4h-12h: 180-360 days; below 4h: not available"),
    _probe("coinglass_doc_etf_flows_history", "https://docs.coinglass.com/reference/etf-flows-history", 200, 623499,
           "5f594838585fc01f2b120638cf7b8368c20012d8a137be54907e6ebe85d40012",
           plans="Hobbyist, Startup, Standard, Professional, Enterprise", sample_first_timestamp="1704931200000 (2024-01-11)",
           shape="daily total flow_usd plus per-ticker flows"),
    _probe("coinglass_doc_etf_history", "https://docs.coinglass.com/reference/etf-history", 200, 626521,
           "2881e542783d0caabaa5e0ca18bf47efd12d68fd8fa9ac5ebffcd041ec9c9c1e",
           plans="Hobbyist and above", shape="per ticker: assets_date, btc_holdings, net assets history"),
    _probe("coinglass_doc_pair_liquidation_history", "https://docs.coinglass.com/reference/liquidation-history", 200, 636582,
           "0c2d984f0e433e3b494f373d566bfbf6bb2a1ab0ecdce7ccf1decdec6199df9d",
           plans="Hobbyist (interval >= 4h), Startup (>= 30m), higher unlimited",
           params="exchange, symbol, interval, limit<=1000, start_time, end_time",
           kraken_pi_xbtusd="pair support UNVERIFIED without an API key"),
    _probe("coinmetrics_catalog_capmrktcurusd", "https://community-api.coinmetrics.io/v4/catalog-all-v2/asset-metrics?assets=btc&metrics=CapMrktCurUSD", 200, 205,
           "8d6a0c3977295c06d26d8c4ff9a07e17f9e86d644e356330339b98827097bff6",
           frequency="1d", min_time="2010-07-18T00:00:00Z", max_time="2026-09-30T00:00:00Z", community="true",
           reviewable="not flagged (no flash/reviewed/revised status, no vintages)"),
    _probe("coinmetrics_data_readme", "https://raw.githubusercontent.com/coinmetrics/data/master/README.md", 200, 1496,
           "9c9d798a88a688f4d25791a953d1f01acda99b9ef5cb5d2481ec577b28af84ae", licence="CC BY-NC 4.0"),
    _probe("coinmetrics_doc_market_cap", "https://docs.coinmetrics.io/network-data/network-data-overview/market/market-capitalization", 200, 3362901,
           "90f2427ed561fa1372235c39e726a66db59875894725b07e59f3166112c378cc",
           definition="CapMrktCurUSD = SplyCur * PriceUSD, daily close price"),
    _probe("coinmetrics_doc_price", "https://docs.coinmetrics.io/network-data/network-data-overview/market/price", 200, 1220524,
           "891bf71bb28719866856c016f30dc098e6f8719e4f8ac59b13639aeb607c0cab",
           timestamp_semantics="daily PriceUSD is the price as of the end of the UTC day, stamped at the day's 00:00"),
    _probe("coingecko_history_2022_public", "https://api.coingecko.com/api/v3/coins/bitcoin/history?date=01-01-2022&localization=false", 401, 335,
           "0d4de32f49bf1bf7cedf088f1b055d223a94f923b62cee16a6ecb32ea5fcb23e",
           result="public API limited to the past 365 days; full history needs a paid plan (price not probed)"),
    _probe("binance_vision_terms", "https://raw.githubusercontent.com/binance/binance-public-data/master/TERMS_AND_CONDITIONS.md", 200, 9798,
           "dcf358e9d18f598a7a635fac80f6e643fa24a0e111a4d39bda47f1e246b31eb1",
           licence="CC BY-NC-SA 4.0; algorithmic historical backtesting for personal non-production research permitted; derivative redistribution under the same licence with attribution"),
    _probe("binance_um_metrics_btcusdt_2020_08_31", f"{_BINANCE}/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-2020-08-31.zip", 404, 339,
           "022db7046b345d8e2ae63eee674184f7a24573004be8a6bd39c9c4e78cdc29d1", result="no file before 2020-09-01"),
    _probe("binance_um_metrics_btcusdt_2020_09_01", f"{_BINANCE}/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-2020-09-01.zip", 200, 12191,
           "9a9c0518bfb939032afe97a6b1708668ec833457743b1ba6ef448fb157722ae3",
           header="create_time,symbol,sum_open_interest,sum_open_interest_value,count_toptrader_long_short_ratio,sum_toptrader_long_short_ratio,count_long_short_ratio,sum_taker_long_short_vol_ratio",
           first_create_time="2020-09-01 00:00:00", rows="576 (2 per 5-minute slot; 288 per day in 2022 files)",
           archive_listing="2221 daily files 2020-09-01..2026-09-30"),
    _probe("binance_um_funding_btcusdt_2020_01", f"{_BINANCE}/futures/um/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-2020-01.zip", 200, 825,
           "7f81b2f3694d13779e7e896b69d60cd61e9444d7b9f9e90df761935e1c1b76e2",
           header="calc_time,funding_interval_hours,last_funding_rate", first_calc_time="2020-01-01T00:00:00Z",
           cadence="8 h (93 rows in January 2020)", archive_listing="81 monthly files 2020-01..2026-09"),
    _probe("binance_um_klines_btcusdt_1h_2020_01", f"{_BINANCE}/futures/um/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2020-01.zip", 200, 37271,
           "512a1d725c8df97a1bbbee4f118e730e9628500a8f271c9e59d2a7fc5fbfcfcc",
           columns="open_time,open,high,low,close,volume,close_time,quote_asset_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore",
           first_open_time="2020-01-01T00:00:00Z", stamping="open_time = interval start"),
    _probe("binance_cm_klines_btcusd_200925_1h_2020_08", f"{_BINANCE}/futures/cm/monthly/klines/BTCUSD_200925/1h/BTCUSD_200925-1h-2020-08.zip", 200, 31999,
           "99e68f96f29f5f1a6e3db15284352905226f3e8a2169cadcc619a766955ad31d",
           first_open_time="2020-08-01T00:00:00Z", quarterly_contracts="26 BTCUSD delivery contracts BTCUSD_200925..BTCUSD_261225"),
    _probe("binance_cm_index_btcusd_1h_2020_06", f"{_BINANCE}/futures/cm/monthly/indexPriceKlines/BTCUSD/1h/BTCUSD-1h-2020-06.zip", 200, 13612,
           "bd1667dad466a09528925625cf4ca671b752bbc46b7602030b78b0a89928fcd1",
           first_open_time="2020-06-09T09:00:00Z", archive_listing="75 monthly files 2020-06..2026-08"),
    _probe("farside_btc_flows", "https://farside.co.uk/btc/", 200, 271212,
           "aae291a8ba473836d6986363612a9a5a1f8bfcf5821465dfd8e2a694626e65ce",
           result="403 on direct fetches; one 200 interstitial without a flow table: UNVERIFIED"),
    _probe("issuer_ishares_ibit_download",
           "https://www.ishares.com/us/products/333011/ishares-bitcoin-trust-etf/1467271812596.ajax?fileType=xls&fileName=iShares-Bitcoin-Trust-ETF_fund&dataType=fund",
           200, 1331819, "9ec3ea2ed5f5c69a7bff4b2814f171ef7c9ddda2671adfd7f2e96fdf7396d4f0",
           result="the download URL returns the HTML product page to a non-browser client: UNVERIFIED"),
    _probe("issuer_fidelity_fbtc", "https://www.fidelity.com/etfs/fbtc", 403, 381,
           "85dc190117565141be0c72b3edc60a9fdb6eeaec1761c95cfdd8527688aca029", result="403: UNVERIFIED"),
    _probe("issuer_grayscale_gbtc", "https://etfs.grayscale.com/gbtc", 429, 33946,
           "46658f41a866767dc6ec83b8067697ceb731f212751c9ea132e5f7710fc4034c", result="429: UNVERIFIED"),
    _probe("issuer_ark_arkb", "https://www.ark-funds.com/funds/arkb", 200, 154512,
           "16a2ad2ff9291779528e5ee69d219a174581be88a44fa32a9f42e518bb06a938", result="intermittent 200/403; no daily history download located"),
    _probe("issuer_bitwise_bitb", "https://bitbetf.com/", 200, 241426,
           "3f14727c95e814fa959c3090f0db927e52fd54f4775e026adfa24096c1d68e57", result="current shares outstanding only; no daily history download located"),
    _probe("issuer_invesco_btco", "https://www.invesco.com/us/financial-products/etfs/product-detail?audienceType=Investor&ticker=BTCO", 200, 613398,
           "413b3a2168005124a83d42b4fcd9dc8efae77ea731ce71cb334f1dcf501905b1", result="intermittent 200/406; no daily history download located"),
    _probe("issuer_franklin_ezbc",
           "https://www.franklintempleton.com/investments/options/exchange-traded-funds/products/39639/SINGLCLASS/franklin-bitcoin-etf/EZBC",
           200, 63944, "24624ee7ffad1c60881bae62c36bc639cfe415cf2828398501b761aa39244dfc", result="no daily history download located"),
    _probe("issuer_coinshares_brrr", "https://coinshares.com/us/etf/brrr", 200, 1490337,
           "7b5c290e763672a9ef1b57c8ed7bf935ec2667243484cb74c8d93b516e08fe50", result="no daily history download located"),
    _probe("issuer_wisdomtree_btcw", "https://www.wisdomtree.com/investments/etfs/crypto/btcw", 403, 5557,
           "a6f26ec803321f0b10d63b94e9ad8bfed8f42cef98bce7414dda317cd7719a9e", result="403: UNVERIFIED"),
    _probe("issuer_hashdex_defi", "https://hashdex-etfs.com/defi", 200, 497625,
           "97a1a85b867b7740dd16c7da89b8d2a222873474cf8de8cff2432c9caa68704e", result="current holdings workbook only; no daily history download located"),
)


# --- ranked sources --------------------------------------------------------------------

DEPTH_MEASURED = "MEASURED"
DEPTH_DOCUMENTED = "DOCUMENTED"
DEPTH_UNVERIFIED = "UNVERIFIED"
REDISTRIBUTION_NC_ATTRIBUTION = "NON_COMMERCIAL_WITH_ATTRIBUTION"
REDISTRIBUTION_PERSONAL = "PERSONAL_USE_ONLY"
REDISTRIBUTION_UNVERIFIED = "UNVERIFIED_TREATED_AS_RESTRICTED"
ROLE_PRIMARY = "CANDIDATE"
ROLE_CORROBORATION = "CORROBORATION_ONLY"


@dataclass(frozen=True)
class SourceCandidate:
    candidate_id: str
    family: str
    rank: int
    provider: str
    dataset: str
    universe: str
    persisted_shape: str
    depth_start: str | None
    depth_status: str
    cost_usd: Decimal | None
    cost_basis: str
    licence: str
    redistribution: str
    publication_time_available: bool
    revision_history_available: bool
    adequate: bool
    probes: tuple[str, ...]
    universe_equal_to_certified: bool | None = None
    certified_census_applies_unchanged: bool | None = None
    meets_required_depth: bool | None = None
    deviations: tuple[str, ...] = ()
    role: str = ROLE_PRIMARY
    notes: str = ""

    def as_record(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "family": self.family,
            "rank": self.rank,
            "role": self.role,
            "provider": self.provider,
            "dataset": self.dataset,
            "universe": self.universe,
            "persisted_shape": self.persisted_shape,
            "depth_start": self.depth_start,
            "depth_status": self.depth_status,
            "cost_usd": canonical_decimal(self.cost_usd) if self.cost_usd is not None else None,
            "cost_basis": self.cost_basis,
            "licence": self.licence,
            "redistribution": self.redistribution,
            "publication_time_available": self.publication_time_available,
            "revision_history_available": self.revision_history_available,
            "universe_equal_to_certified": self.universe_equal_to_certified,
            "certified_census_applies_unchanged": self.certified_census_applies_unchanged,
            "meets_required_depth": self.meets_required_depth,
            "adequate": self.adequate,
            "deviations": list(self.deviations),
            "probes": list(self.probes),
            "notes": self.notes,
        }


_LIQ_UNIVERSE = f"Kraken Futures {epic_x_corpus.LIQUIDATION_INSTRUMENT}"
_CENSUS_DEVIATION = "DEV_LIQUIDATION_HISTORICAL_CENSUS"
_DAILY_AGGREGATE_DEVIATION = "DEV_LIQUIDATION_DAILY_AGGREGATE"
_BASIS_DEVIATION = "DEV_FUTURES_BASIS_CONTRACT"
_ETF_UNIVERSE_DEVIATION = "DEV_ETF_FUND_UNIVERSE"

SOURCE_CANDIDATES: tuple[SourceCandidate, ...] = (
    # liquidations: consistency with the EPIC X universe first, cost second (RBT-002 order)
    SourceCandidate(
        "kraken_futures_rest_executions", LIQUIDATION_FAMILY, 1, "Kraken Futures (public REST)",
        f"{_KRAKEN_EXECUTIONS} (paginated by continuationToken)", _LIQ_UNIVERSE, SHAPE_EVENT,
        "2021-05-27T11:55:25.097Z", DEPTH_MEASURED, Decimal("0"), "free public endpoint",
        "Kraken terms of service; no explicit market-data redistribution licence located", REDISTRIBUTION_UNVERIFIED,
        False, False, True,
        ("kraken_rest_executions_since_2018", "kraken_rest_executions_before_2020", "kraken_rest_executions_2022_11_09", "kraken_v3_history_recent_typing"),
        universe_equal_to_certified=True, certified_census_applies_unchanged=False, meets_required_depth=True,
        deviations=(_CENSUS_DEVIATION,),
        notes=(
            "Raw fills; liquidations identified by takerOrder.orderType == 'Liquidation'; side from takerOrder.direction "
            "(Buy closes a short, Sell a long, as LIQUIDATION_SIDE_TO_POSITION). Covers all of 2022 and every day from "
            "2021-05-28. RBT-003 must verify the orderType label equals the websocket type 'liquidation' on a window "
            "containing liquidations (uids join v2 and v3)."
        ),
    ),
    SourceCandidate(
        "kraken_futures_analytics_liquidation_volume", LIQUIDATION_FAMILY, 1, "Kraken Futures (public charts API)",
        f"{_KRAKEN_ANALYTICS}/liquidation-volume?interval=3600", _LIQ_UNIVERSE, SHAPE_INTERVAL,
        "2020-02-26", DEPTH_MEASURED, Decimal("0"), "free public endpoint",
        "Kraken terms of service", REDISTRIBUTION_UNVERIFIED, False, False, False,
        ("kraken_analytics_liquidation_volume_2020_02_25", "kraken_analytics_liquidation_volume_2020_02_26"),
        universe_equal_to_certified=True, certified_census_applies_unchanged=False, meets_required_depth=True,
        role=ROLE_CORROBORATION,
        notes="Kraken's own hourly totals with explicit zero hours; no events or sides. Corroborates hour completeness for the rank-1 events.",
    ),
    SourceCandidate(
        "tardis_kraken_futures_liquidations", LIQUIDATION_FAMILY, 2, "Tardis.dev",
        "cryptofacilities liquidations CSV (recording of wss://futures.kraken.com/ws/v1)", _LIQ_UNIVERSE, SHAPE_EVENT,
        "2019-03-30", DEPTH_MEASURED, Decimal("4200"),
        "Perpetuals plan, Academic, yearly billing (USD 350 x 12; eligibility required; reaches 2022-10-01 if started 2026-10-01). "
        "Solo yearly USD 8400 reaches the same depth; Business yearly USD 36000 reaches 2019-03-30. Quarterly (12 months) is too shallow.",
        "Tardis.dev subscription terms; redistribution terms not located", REDISTRIBUTION_UNVERIFIED, False, False, True,
        ("tardis_exchange_cryptofacilities", "tardis_billing_faq", "tardis_home_pricing", "tardis_free_liquidations_2022_01_01"),
        universe_equal_to_certified=True, certified_census_applies_unchanged=False, meets_required_depth=True,
        deviations=(_CENSUS_DEVIATION,),
        notes="The same websocket feed EPIC X captures, with exact prices; one incident in the data window (2021-11-10 05:09-05:19Z).",
    ),
    SourceCandidate(
        "coinalyze_liquidation_history_daily", LIQUIDATION_FAMILY, 3, "Coinalyze (free API)",
        "/v1/liquidation-history interval=daily (preferably the Kraken PI_XBTUSD symbol)", "UNVERIFIED (Kraken PI_XBTUSD availability unknown)",
        SHAPE_INTERVAL, None, DEPTH_UNVERIFIED, Decimal("0"), "free with an API key (COINALYZE_API_KEY not set)",
        "free; attribution when used publicly", REDISTRIBUTION_UNVERIFIED, False, False, False,
        ("coinalyze_api_doc", "coinalyze_future_markets_no_key"),
        universe_equal_to_certified=None, certified_census_applies_unchanged=False, meets_required_depth=None,
        deviations=(_DAILY_AGGREGATE_DEVIATION,),
        notes="Daily aggregates retained forever; intraday only 1500-2000 points. Depth and symbol UNVERIFIED without a key.",
    ),
    SourceCandidate(
        "coinglass_pair_liquidation_history_daily", LIQUIDATION_FAMILY, 4, "CoinGlass API (Hobbyist)",
        "/api/futures/liquidation/history exchange=Kraken interval=1d", "UNVERIFIED (Kraken PI_XBTUSD pair support unknown)",
        SHAPE_INTERVAL, "all-time at 1d (plan table)", DEPTH_DOCUMENTED, Decimal("29"), "Hobbyist, one month billed monthly",
        "CoinGlass API terms: personal use", REDISTRIBUTION_PERSONAL, False, False, False,
        ("coinglass_pricing", "coinglass_doc_pair_liquidation_history"),
        universe_equal_to_certified=None, certified_census_applies_unchanged=False, meets_required_depth=None,
        deviations=(_DAILY_AGGREGATE_DEVIATION,),
        notes="Hobbyist intervals are >= 4h with 180-day history; only 1d reaches all-time, so the hourly census cannot apply.",
    ),
    # market cap
    SourceCandidate(
        "coinmetrics_community_capmrktcurusd", MARKET_CAP_FAMILY, 1, "Coin Metrics Community API",
        "/v4/timeseries/asset-metrics assets=btc metrics=CapMrktCurUSD frequency=1d", "BTC network market cap (SplyCur x PriceUSD daily close)",
        SHAPE_DAILY_PUBLISHED, "2010-07-18", DEPTH_MEASURED, Decimal("0"), "free community endpoint, no key",
        "CC BY-NC 4.0", REDISTRIBUTION_NC_ATTRIBUTION, False, False, True,
        ("coinmetrics_catalog_capmrktcurusd", "coinmetrics_data_readme", "coinmetrics_doc_market_cap", "coinmetrics_doc_price"),
        meets_required_depth=True,
        notes="Final values only (not reviewable, no vintages): REVISION_HISTORY_UNAVAILABLE; no publication time, so D+2 00:00.",
    ),
    SourceCandidate(
        "coingecko_market_cap_history", MARKET_CAP_FAMILY, 2, "CoinGecko API",
        "/coins/bitcoin/history (EPIC X prospective market-cap source)", "CoinGecko BTC market cap",
        SHAPE_DAILY_PUBLISHED, None, DEPTH_UNVERIFIED, None, "public API limited to 365 days; paid plan price not probed",
        "CoinGecko API terms", REDISTRIBUTION_UNVERIFIED, False, False, False, ("coingecko_history_2022_public",),
        notes="Consistent with the EPIC X prospective source, but 2020-2025 history needs a paid plan of unverified cost.",
    ),
    # futures basis
    SourceCandidate(
        "binance_coinm_quarterly_basis", FUTURES_BASIS_FAMILY, 1, "Binance Vision public archive",
        "cm klines BTCUSD_YYMMDD 1h + cm indexPriceKlines BTCUSD 1h", "Binance COIN-M BTCUSD quarterly delivery contracts vs the COIN-M BTCUSD index",
        SHAPE_SNAPSHOT, "2020-08-01T00:00:00Z", DEPTH_MEASURED, Decimal("0"), "free public archive",
        "CC BY-NC-SA 4.0", REDISTRIBUTION_NC_ATTRIBUTION, False, False, True,
        ("binance_cm_klines_btcusd_200925_1h_2020_08", "binance_cm_index_btcusd_1h_2020_06", "binance_vision_terms"),
        meets_required_depth=True, deviations=(_BASIS_DEVIATION,),
        notes="The BTC-021 collector defines no instrument, spot reference or annualisation, so these semantics need a decision.",
    ),
    SourceCandidate(
        "tardis_kraken_futures_fixed_maturity", FUTURES_BASIS_FAMILY, 2, "Tardis.dev",
        "cryptofacilities derivative_ticker for FI_XBTUSD_* (mark/index)", "Kraken Futures fixed-maturity contracts",
        SHAPE_SNAPSHOT, None, DEPTH_UNVERIFIED, None, "within a Tardis Perpetuals/Derivatives subscription; fixed-maturity coverage not probed",
        "Tardis.dev subscription terms", REDISTRIBUTION_UNVERIFIED, False, False, False, ("tardis_exchange_cryptofacilities",),
        deviations=(_BASIS_DEVIATION,),
    ),
    # funding, open interest, perpetual volume
    SourceCandidate(
        "binance_usdm_btcusdt_funding_archive", FUNDING_RATE_FAMILY, 1, "Binance Vision public archive",
        "um monthly fundingRate BTCUSDT (calc_time, funding_interval_hours, last_funding_rate)", "Binance USD-M BTCUSDT perpetual",
        SHAPE_SETTLEMENT, "2020-01-01T00:00:00Z", DEPTH_MEASURED, Decimal("0"), "free public archive",
        "CC BY-NC-SA 4.0", REDISTRIBUTION_NC_ATTRIBUTION, False, False, True,
        ("binance_um_funding_btcusdt_2020_01", "binance_vision_terms"), meets_required_depth=True,
        notes="Maps onto FundingRate exactly (settlement instant and interval). The 2020-01-01 00:00 settlement prices 2019 and is refused.",
    ),
    SourceCandidate(
        "tardis_kraken_derivative_ticker", FUNDING_RATE_FAMILY, 2, "Tardis.dev",
        "cryptofacilities derivative_ticker PI_XBTUSD (funding_timestamp, funding_rate, open_interest)", _LIQ_UNIVERSE,
        SHAPE_SETTLEMENT, "2019-03-30", DEPTH_MEASURED, Decimal("4200"), "the same Tardis subscription as liquidation rank 2",
        "Tardis.dev subscription terms", REDISTRIBUTION_UNVERIFIED, False, False, True, ("tardis_exchange_cryptofacilities",),
        notes="A single-venue alternative (Kraken universe) for funding and OI.",
    ),
    SourceCandidate(
        "kraken_v4_historical_funding_rates", FUNDING_RATE_FAMILY, 3, "Kraken Futures (public REST)",
        "/derivatives/api/v4/historicalfundingrates", _LIQ_UNIVERSE, SHAPE_SETTLEMENT,
        "2025-10-01T08:00:00Z", DEPTH_MEASURED, Decimal("0"), "free", "Kraken terms of service", REDISTRIBUTION_UNVERIFIED,
        False, False, False, ("kraken_v4_historical_funding_rates",), meets_required_depth=False,
        notes="Rolling trailing year with no date filter: too shallow, and every response carries holdout rows.",
    ),
    SourceCandidate(
        "binance_usdm_btcusdt_metrics_archive", OPEN_INTEREST_FAMILY, 1, "Binance Vision public archive",
        "um daily metrics BTCUSDT (create_time, sum_open_interest_value)", "Binance USD-M BTCUSDT perpetual",
        SHAPE_SNAPSHOT, "2020-09-01T00:00:00Z", DEPTH_MEASURED, Decimal("0"), "free public archive",
        "CC BY-NC-SA 4.0", REDISTRIBUTION_NC_ATTRIBUTION, False, False, True,
        ("binance_um_metrics_btcusdt_2020_08_31", "binance_um_metrics_btcusdt_2020_09_01", "binance_vision_terms"), meets_required_depth=True,
        notes="5-minute snapshots; early files carry two rows per slot, which RBT-003 must de-duplicate and record.",
    ),
    SourceCandidate(
        "kraken_futures_analytics_open_interest", OPEN_INTEREST_FAMILY, 3, "Kraken Futures (public charts API)",
        f"{_KRAKEN_ANALYTICS}/open-interest", _LIQ_UNIVERSE, SHAPE_SNAPSHOT, "2023-03-07", DEPTH_MEASURED, Decimal("0"), "free",
        "Kraken terms of service", REDISTRIBUTION_UNVERIFIED, False, False, False,
        ("kraken_analytics_open_interest_2023_03_06", "kraken_analytics_open_interest_2023_03_07"), meets_required_depth=False,
        notes="Starts 2023-03-07: too shallow for 2022.",
    ),
    SourceCandidate(
        "binance_usdm_btcusdt_klines_1h", PERP_VOLUME_FAMILY, 1, "Binance Vision public archive",
        "um monthly klines BTCUSDT 1h (open_time, volume, quote_asset_volume)", "Binance USD-M BTCUSDT perpetual",
        SHAPE_INTERVAL, "2020-01-01T00:00:00Z", DEPTH_MEASURED, Decimal("0"), "free public archive",
        "CC BY-NC-SA 4.0", REDISTRIBUTION_NC_ATTRIBUTION, False, False, True,
        ("binance_um_klines_btcusdt_1h_2020_01", "binance_vision_terms"), meets_required_depth=True,
        notes="open_time is the interval start (RBT-001 requirement). Not used under ETF_CORE, but data quality requires a perp_volume feed.",
    ),
    # ETF flows and AUM
    SourceCandidate(
        "coinglass_etf_flows_and_history", ETF_FLOW_FAMILY, 1, "CoinGlass API (Hobbyist)",
        "/api/etf/bitcoin/flow-history (per-ticker daily flows) + /api/etf/bitcoin/history (per-fund net assets)", "US spot bitcoin ETFs",
        SHAPE_DAILY_PUBLISHED, "2024-01-11", DEPTH_DOCUMENTED, Decimal("29"), "Hobbyist, one month billed monthly",
        "CoinGlass API terms: personal use", REDISTRIBUTION_PERSONAL, False, False, True,
        ("coinglass_pricing", "coinglass_doc_etf_flows_history", "coinglass_doc_etf_history"), meets_required_depth=True,
        deviations=(_ETF_UNIVERSE_DEVIATION,),
        notes="Aggregator flows: final values only (REVISION_HISTORY_UNAVAILABLE), no publication time (T+2 00:00). RBT-003 must check the date convention against an issuer where one is reachable.",
    ),
    SourceCandidate(
        "issuer_websites", ETF_FLOW_FAMILY, 2, "ETF issuers (iShares, Fidelity, Grayscale, ARK, Bitwise, Invesco, Franklin, CoinShares, WisdomTree, Hashdex)",
        "issuer product pages and downloads", "US spot bitcoin ETFs", SHAPE_DAILY_PUBLISHED, None, DEPTH_UNVERIFIED, Decimal("0"),
        "free where reachable", "issuer site terms", REDISTRIBUTION_UNVERIFIED, False, False, False,
        ("issuer_ishares_ibit_download", "issuer_fidelity_fbtc", "issuer_grayscale_gbtc", "issuer_ark_arkb", "issuer_bitwise_bitb",
         "issuer_invesco_btco", "issuer_franklin_ezbc", "issuer_coinshares_brrr", "issuer_wisdomtree_btcw", "issuer_hashdex_defi"),
        notes="Bot protection (403/406/429) or no daily-history download on every probed issuer: UNVERIFIED.",
    ),
    SourceCandidate(
        "farside_btc_etf_flows", ETF_FLOW_FAMILY, 3, "Farside Investors", "https://farside.co.uk/btc/", "US spot bitcoin ETFs",
        SHAPE_DAILY_PUBLISHED, None, DEPTH_UNVERIFIED, Decimal("0"), "free website", "site terms not reachable", REDISTRIBUTION_UNVERIFIED,
        False, False, False, ("farside_btc_flows",), notes="403: UNVERIFIED.",
    ),
)


def selected_sources(candidates: Sequence[SourceCandidate] = SOURCE_CANDIDATES) -> dict[str, SourceCandidate]:
    """Per family, the best-ranked adequate candidate (consistency, then cost)."""

    chosen: dict[str, SourceCandidate] = {}
    for candidate in sorted(candidates, key=lambda item: (item.family, item.rank, item.cost_usd or Decimal("0"))):
        if candidate.adequate and candidate.role == ROLE_PRIMARY and candidate.family not in chosen:
            chosen[candidate.family] = candidate
    return chosen


# Semantics RBT-002 pins for RBT-001A/RBT-003. Each is consistent with an owner,
# the schema, policy V3 section 4 or a provider definition, and changes nothing.
SEMANTIC_PINS: tuple[tuple[str, str], ...] = (
    ("PERP_VOLUME_INTERVAL_START", "PerpVolume.observation_time is the interval start (Binance open_time); timeframe 1h; available at the interval end (RBT-001 requirement)."),
    ("OPEN_INTEREST_HOURLY_SNAPSHOT_USD", "OpenInterest rows are the hourly :00 snapshots of the 5-minute archive (BTC-021 DerivativesCollectionRequest.timeframe default '1h'), unit USD (sum_open_interest_value) so OI/market cap is dimensionless; available at the snapshot instant."),
    ("FUNDING_SETTLEMENT", "FundingRate.observation_time = calc_time (settlement S), funding_interval_hours as supplied; available at S; a settlement whose accrual period starts before 2020-01-01 is refused (RBT-001)."),
    ("MARKET_CAP_END_OF_DAY", "MarketCapObservation for UTC day D: observation_time D+1 00:00 (the provider's value is the end-of-day close), available D+2 00:00 (policy V3 DAILY_PUBLISHED), REVISION_HISTORY_UNAVAILABLE; the first admitted day is 2020-01-01."),
    ("LIQUIDATION_HOURLY_AGGREGATES", "raw.liquidations rows are per-side 1h INTERVAL aggregates (the primary key cannot hold events), available at the hour end; every contributing event id is digested in hash-bound evidence."),
    ("FUTURES_BASIS_SNAPSHOT", "raw.futures_basis rows are SNAPSHOTs (schema: market timestamp, no timeframe column); the contract definition itself is a blocker."),
    ("ETF_FLOW_DAILY_PUBLISHED", "EtfFlow rows: DAILY_PUBLISHED at T+2 00:00 UTC; REVISION_HISTORY_UNAVAILABLE unless a source supplies vintages; the closure table supplies market_holidays."),
)


# --- section 5A blockers -----------------------------------------------------------------


@dataclass(frozen=True)
class ResolutionOption:
    option: str
    data_cost_usd: Decimal
    note: str

    def as_record(self) -> dict[str, Any]:
        return {"option": self.option, "data_cost_usd": canonical_decimal(self.data_cost_usd), "note": self.note}


@dataclass(frozen=True)
class BlockerDefinition:
    blocker_id: str
    title: str
    decision: str
    finding: str
    proposed_rule: str
    options: tuple[ResolutionOption, ...]
    blocks: tuple[str, ...]
    members: tuple[str, ...] = ()
    every_new_trade_blocked: bool = False
    required_for_entry_component: bool = True


_NO_DATA = Decimal("0")
_OWNER_OPTIONS = (
    ResolutionOption("Owner/Rulebook decision defining the missing quantity, window and minimum (a new versioned owner contract)", _NO_DATA, "price/ETF history already in scope; a longer window delays the first evaluable date"),
    ResolutionOption("Explicitly versioned research strategy variant (AGENTS.md strategy-semantics change)", _NO_DATA, "never silent; a new strategy version"),
    ResolutionOption("No change: the affected score stays structurally incomplete", _NO_DATA, "every decision is STRUCTURALLY_UNEVALUABLE / NO TRADE"),
)

OWNERLESS_BLOCKERS: tuple[BlockerDefinition, ...] = (
    BlockerDefinition(
        "BLK-TREND-ZSCORE-NORMALISATION", "Trend z-score normalisation is undefined", DECISION_OWNER,
        "TrendScoreInput takes Z_M4, Z_M12, Z_20W and Z_52H as required Decimals. The momentum, MA-distance and 52-week-high owners exist, "
        "but no owner, configuration value, certified definition or Rulebook text fixes the z-score window or minimum (Rulebook 5.1: "
        "'normalize using trailing historical data'). No production code constructs TrendScoreInput.",
        "Decide one versioned normalisation (window, minimum, population vs sample) for all four trend z-scores before RBT-004.",
        _OWNER_OPTIONS, ("RBT-004", "RBT-006"),
        members=("TREND_Z_M4", "TREND_Z_M12", "TREND_Z_20W", "TREND_Z_52H"),
    ),
    BlockerDefinition(
        "BLK-FLOW-ZSCORE-NORMALISATION", "Flow z-score normalisation is undefined", DECISION_OWNER,
        "FlowScoreInput takes z(ETFNorm_5), z(ETFNorm_20) and z(FlowAccel). The ETF window owners exist, but nothing defines the "
        "z-score window or minimum. With ETF flows starting 2024-01-11, every day of z-score window delays the first evaluable decision.",
        "Decide one versioned flow normalisation before RBT-004; its warm-up adds to the 20-publication-day ETF window.",
        _OWNER_OPTIONS, ("RBT-004", "RBT-006"),
        members=("FLOW_Z_ETF_NORM_5D", "FLOW_Z_ETF_NORM_20D", "FLOW_Z_FLOW_ACCEL"),
    ),
    BlockerDefinition(
        "BLK-VOLATILITY-RANGE-AND-RETURN", "Range percentile and downside/upside return are undefined", DECISION_OWNER,
        "OrderlinessScoreInput requires range_percentile and downside_return; any None makes orderliness, and so the volatility score, "
        "incomplete. STRESS, CAPITULATION and EUPHORIA consume them too. No owner computes them and no certified definition exists "
        "(EPIC X certified only liquidation_percentile).",
        "Decide the quantities (range measure, return horizon), windows and minima as a versioned owner contract before RBT-004.",
        _OWNER_OPTIONS, ("RBT-004", "RBT-006"),
        members=("RANGE_PERCENTILE", "DOWNSIDE_RETURN", "UPSIDE_RETURN"),
    ),
    BlockerDefinition(
        "BLK-LEVEL-STRENGTH-INPUTS", "Level reaction is undefined; the volume fallback lacks an executable path", DECISION_OWNER,
        "STRUCTURE_SCORE_V1_2 weights LevelStrength. calculate_level_strength returns None while reaction_magnitude_fraction or "
        "volume_percentile is None, and no owner produces either. Rulebook 9.2 says omit volume and use the core weights, but the "
        "owner and config weight volume at 0.20 and require it.",
        "Define the reaction-magnitude measure. Reuse Rulebook 9.2 core weights without inventing a volume percentile; resolve the frozen owner's inability to omit missing volume through an explicit authorized compatibility correction.",
        _OWNER_OPTIONS, ("RBT-004", "RBT-006"),
        members=("LEVEL_REACTION_MAGNITUDE",),
    ),
    BlockerDefinition(
        "BLK-SEVERE-CROWDING-STATE", "'Severe crowding' has no owner definition", DECISION_OWNER,
        "HardVetoInput and BullTrendContinuationInput take severe_crowding_flagged; the CROWDING owner has no severity grade. "
        "The hard veto fails closed on None (HARD_VETO_INPUT_MISSING), so every new trade would be vetoed on every date.",
        "Decide the severe-crowding predicate (for example CROWDING.flagged, or a stricter threshold) as a versioned rule.",
        _OWNER_OPTIONS, ("RBT-004",),
        members=("SEVERE_CROWDING_STATE",), every_new_trade_blocked=True,
    ),
    BlockerDefinition(
        "BLK-LIFECYCLE-PREDICATES", "Hold, add and exit inputs have no owner", DECISION_OWNER,
        "Momentum persistence (Hold), new structure and momentum (Add), and the Rulebook 18.1/20/26 predicates (new structural "
        "confirmation, regime supportive, flow supportive, regime invalidation, data-risk exit) are qualitative only. Hold Score is "
        "therefore never complete (no HOLD_SCORE_COLLAPSE exit or hold-band trim), and every add fails closed.",
        "Decide versioned definitions before RBT-005; structural-stop exits still work without them.",
        _OWNER_OPTIONS, ("RBT-005",),
        members=(
            "MOMENTUM_PERSISTENCE_SCORE", "NEW_STRUCTURE_SCORE", "ADD_MOMENTUM_SCORE", "NEW_STRUCTURAL_CONFIRMATION",
            "REGIME_SUPPORTIVE_PREDICATE", "FLOW_SUPPORTIVE_PREDICATE", "REGIME_INVALIDATION_PREDICATE", "DATA_RISK_EXIT_PREDICATE",
        ),
    ),
    BlockerDefinition(
        "BLK-SETUP-INPUTS", "Setup inputs without an owner", DECISION_OWNER,
        "Bullish Reset needs correction_from_local_high_fraction (local-high selection undefined), so it can never match. The optional tier-four measured_move reward reference has no target-price/PIT owner. Bearish Distribution's "
        "distribution and short-trigger states have no owner, but are inert for the long-only champion (backtest.allow_short_trades = false).",
        "Decide the local-high measure before RBT-004 if Bullish Reset is to be reachable; the short-side inputs need nothing while shorts stay disabled.",
        _OWNER_OPTIONS, ("RBT-004",),
        members=("CORRECTION_FROM_LOCAL_HIGH", "DISTRIBUTION_STATE", "SHORT_TRIGGER", "MEASURED_MOVE_REFERENCE"),
    ),
    BlockerDefinition(
        "BLK-AVWAP-EVENT-ANCHOR", "The anchored-VWAP market-event anchor has no owner", DECISION_OWNER,
        "anchored_vwap_anchor_from_capitulation_event takes a CapitulationEvent (event instant, price and detection time). "
        "No owner produces one (BTC-093 takes 'explicit event metadata' from the caller): the CAPITULATION flag owner "
        "returns a flag result, not an event, and Rulebook 9.1 names "
        "'Anchored VWAPs from important market events' without defining the event. Found by the RBT-002 R1 census. AVWAP "
        "confluence is an optional Phase 1 enhancement (Rulebook 9.2), so no Entry Conviction component is structurally "
        "incomplete without it: the swing and breakout anchors and every other level still evaluate.",
        "CHAMPION_COMPLETION_SPEC_V1 defines the event from existing owner outputs or explicitly omits the event anchor; "
        "it is never inferred.",
        (
            ResolutionOption("Owner/Rulebook decision defining the event from existing owner outputs (a versioned owner contract)", _NO_DATA, "price history already in scope"),
            ResolutionOption("Explicitly versioned research strategy variant (AGENTS.md strategy-semantics change)", _NO_DATA, "never silent; a new strategy version"),
            ResolutionOption("Explicitly omit the optional event anchor", _NO_DATA, "Rulebook 9.2 optional enhancement; swing and breakout anchors still evaluate"),
        ),
        ("RBT-004",),
        members=("CAPITULATION_EVENT",),
        required_for_entry_component=False,
    ),
)

POLICY_V4_BLOCKERS: tuple[BlockerDefinition, ...] = (
    BlockerDefinition(
        "BLK-LIQUIDATION-HISTORICAL-CENSUS", "The certified hourly census cannot be applied unchanged to history", DECISION_POLICY_V4,
        f"{epic_x_corpus.LIQUIDATION_UTC_DAY_CENSUS_VERSION} admits an hour only with prospective SOURCE_STREAM_EPOCH, liveness, clock and "
        "collector-health evidence for the websocket feed. No historical source (Kraken REST, Tardis, Coinalyze, CoinGlass) can produce it. "
        "The universe (Kraken Futures PI_XBTUSD), daily long+short USD quantity, 730-day window, 365 minimum and midrank convention can all be kept.",
        "HISTORICAL_LIQUIDATION_HOUR_COMPLETENESS_V1 (proposed): an hour [h, h+1) of PI_XBTUSD is OBSERVED when the paginated REST "
        "execution log was read contiguously across it (unbroken continuation chain, no error) and at least one execution of any order "
        "type is stamped in it; zero Liquidation-typed fills then make OBSERVED_ZERO_EVENTS. An hour with no execution at all, or a "
        "Tardis-reported incident hour, is SOURCE_UNAVAILABLE. Kraken's hourly liquidation-volume series must agree within rounding. "
        "Days still need all 24 OBSERVED hours; the percentile adapter is otherwise unchanged.",
        (
            ResolutionOption("Adopt the proposed rule in RESEARCH_BACKTEST_POLICY_V4 with Kraken REST (rank 1)", Decimal("0"), "same universe, raw events, depth 2021-05-27"),
            ResolutionOption("Same rule over Tardis Kraken Futures liquidations (rank 2)", Decimal("4200"), "Academic yearly (eligibility); Solo yearly USD 8400"),
            ResolutionOption("Daily-aggregate rule over Coinalyze or CoinGlass (ranks 3-4)", Decimal("29"), "universe unverified; hourly census replaced by daily completeness"),
        ),
        ("RBT-001A", "RBT-003"),
    ),
    BlockerDefinition(
        "BLK-FUTURES-BASIS-CONTRACT", "The futures-basis contract is not defined anywhere", DECISION_POLICY_V4,
        "Policy V3 section 5 asks for a historical adapter that reproduces the BTC-021 semantics exactly, but BTC-021 has no concrete "
        "provider: it fixes no futures instrument, spot reference or annualisation, raw.futures_basis is empty, and EPIC X defines no "
        "basis contract. futures_basis_health averages every row sharing an observation_time.",
        "FUTURES_BASIS_CONTRACT_V1 (proposed): Binance COIN-M BTCUSD quarterly delivery contracts listed at t, basis_rate = "
        "futures 1h close / COIN-M BTCUSD index 1h close - 1 at the hour close t (SNAPSHOT), annualized_basis_rate = basis_rate * "
        "365 days / (expiry - t), contracts within 7 days of expiry excluded; expiry = the contract's delivery instant.",
        (
            ResolutionOption("Adopt the proposed Binance COIN-M contract in policy V4", Decimal("0"), "depth 2020-08-01"),
            ResolutionOption("Kraken Futures fixed-maturity contracts via Tardis", Decimal("4200"), "same venue as the liquidation universe; FI coverage unverified"),
        ),
        ("RBT-001A", "RBT-003"),
    ),
    BlockerDefinition(
        "BLK-STRESS-HARD-VETO-MAPPING", "How an incomplete STRESS result reaches the hard veto", DECISION_POLICY_V4,
        "systemic_shock is DISCRETIONARY (never asserted), so StressFlagResult.complete is False on every date while flagged is still "
        "computed from the other triggers. HardVetoInput.stress_flagged and BullTrendContinuationInput.stress_flagged take a bool; no "
        "owner maps an incomplete result. Passing None vetoes every trade; passing flagged follows the owner's documented handling. "
        "(The trim path is owner-defined: trim_rules_from_results passes None, so EUPHORIA trims never fire: a named limitation.)",
        "Pass StressFlagResult.flagged and record STRESS_INPUT_MISSING in source_reason_codes when the only missing input is DISCRETIONARY.",
        (ResolutionOption("Adopt the proposed mapping in policy V4", Decimal("0"), "no data needed"),),
        ("RBT-004",), every_new_trade_blocked=True,
    ),
    BlockerDefinition(
        "BLK-ETF-FUND-UNIVERSE", "The ETF fund universe across fund launches", DECISION_POLICY_V4,
        "etf_flow_window uses every fund visible in the window (or the funds passed) and fails closed on any missing (fund, date). "
        "A fund launched after 2024-01-11 makes every window spanning its launch incomplete for up to 20 publication days, unless "
        "pre-launch rows are invented (zero-fill, prohibited) or the universe is chosen per window.",
        "Per decision, pass funds = the funds with a first US trading date on or before the window's first included publication "
        "date; record each fund's launch date with its source evidence.",
        (ResolutionOption("Adopt the proposed per-window universe in policy V4", Decimal("0"), "no data beyond the ETF source"),),
        ("RBT-003", "RBT-004"),
    ),
)


def derive_blockers(
    rows: Sequence[SurfaceRow],
    candidates: Sequence[SourceCandidate] = SOURCE_CANDIDATES,
) -> list[dict[str, Any]]:
    """The section 5A blocker list, derived from the surface and the sources.

    Every ``OWNERLESS_UNDEFINED`` input must belong to exactly one owner-less
    blocker; its Entry Conviction components come from the surface rows. A
    deviation recorded on a selected source raises its policy V4 blocker.
    """

    undefined: dict[str, set[str]] = {}
    occurrences: dict[str, list[str]] = {}
    for row in rows:
        classification = row.classification
        if classification.kind == KIND_OWNERLESS_UNDEFINED:
            input_id = classification.input_id or ""
            undefined.setdefault(input_id, set()).update(classification.entry_components)
            occurrences.setdefault(input_id, []).append(row.key)
    membership: dict[str, str] = {}
    for blocker in OWNERLESS_BLOCKERS:
        for member in blocker.members:
            if member in membership:
                raise CoverageError("BLOCKER_MEMBERSHIP", f"{member} belongs to two blockers")
            membership[member] = blocker.blocker_id
    unassigned = sorted(set(undefined) - set(membership))
    if unassigned:
        raise CoverageError("BLOCKER_MEMBERSHIP", f"owner-less inputs without a blocker: {unassigned}")
    stale = sorted(set(membership) - set(undefined))
    if stale:
        raise CoverageError("BLOCKER_MEMBERSHIP", f"blocker members no longer owner-less: {stale}")
    records = []
    for blocker in OWNERLESS_BLOCKERS:
        components = sorted({c for member in blocker.members for c in undefined[member]})
        records.append(
            _blocker_record(
                blocker,
                category="OWNERLESS_NO_DEFINITION",
                entry_components=components,
                inputs={member: sorted(occurrences[member]) for member in blocker.members},
            )
        )
    raised = {deviation for candidate in selected_sources(candidates).values() for deviation in candidate.deviations}
    deviation_to_blocker = {
        _CENSUS_DEVIATION: "BLK-LIQUIDATION-HISTORICAL-CENSUS",
        _BASIS_DEVIATION: "BLK-FUTURES-BASIS-CONTRACT",
        _ETF_UNIVERSE_DEVIATION: "BLK-ETF-FUND-UNIVERSE",
    }
    triggered = {deviation_to_blocker[item] for item in raised if item in deviation_to_blocker}
    triggered.add("BLK-STRESS-HARD-VETO-MAPPING")
    for blocker in POLICY_V4_BLOCKERS:
        if blocker.blocker_id in triggered:
            components = {
                "BLK-LIQUIDATION-HISTORICAL-CENSUS": [_VOLATILITY],
                "BLK-FUTURES-BASIS-CONTRACT": [_POSITIONING],
                "BLK-ETF-FUND-UNIVERSE": [_FLOW],
            }.get(blocker.blocker_id, [])
            records.append(_blocker_record(blocker, category="SOURCE_OR_COMPOSER_SEMANTICS", entry_components=components, inputs={}))
    return records


def _blocker_record(
    blocker: BlockerDefinition,
    *,
    category: str,
    entry_components: Sequence[str],
    inputs: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    structural = category == "OWNERLESS_NO_DEFINITION" and bool(entry_components) and blocker.required_for_entry_component
    return {
        "blocker_id": blocker.blocker_id,
        "title": blocker.title,
        "category": category,
        "decision_required": blocker.decision,
        "entry_components": sorted(entry_components),
        "entry_conviction_structurally_incomplete_on_every_date": structural,
        "every_new_trade_blocked_on_every_date": blocker.every_new_trade_blocked,
        "blocks_tickets": list(blocker.blocks),
        "finding": blocker.finding,
        "proposed_rule": blocker.proposed_rule,
        "resolution_options": [option.as_record() for option in blocker.options],
        "inputs": {key: list(value) for key, value in sorted(inputs.items())},
    }


# --- coverage per family and the RBT-003 plan -----------------------------------------


def family_coverage(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Per section 5 family (and per venue for prices): data-window coverage."""

    tables = snapshot["raw_tables"]
    records = []
    ohlcv = tables["raw.btc_ohlcv"]
    for venue in REPLAY_VENUES:
        entry = next(
            (
                item
                for item in ohlcv["series"]
                if (item["key"]["exchange"], item["key"]["symbol"], item["key"]["provider"], item["key"]["timeframe"])
                == (venue.exchange, venue.symbol, venue.provider, "1h")
            ),
            None,
        )
        families = [REFERENCE_PRICE_FAMILY] + ([SHARED_VOLUME_FAMILY] if venue == SHARED_VOLUME_VENUE else [])
        for family in families:
            records.append(_series_coverage(family, venue.venue_id, "raw.btc_ohlcv", entry))
    for table, family in (
        ("raw.etf_flows", ETF_FLOW_FAMILY),
        ("raw.funding_rates", FUNDING_RATE_FAMILY),
        ("raw.open_interest", OPEN_INTEREST_FAMILY),
        ("raw.futures_basis", FUTURES_BASIS_FAMILY),
        ("raw.liquidations", LIQUIDATION_FAMILY),
        ("raw.perp_volume", PERP_VOLUME_FAMILY),
    ):
        summary = tables[table]
        data_rows = summary["window_rows"][DATA_WINDOW.window_id]
        records.append(
            {
                "family": family,
                "venue": "SHARED",
                "source": table,
                "status": "EMPTY" if data_rows == 0 else "PRESENT",
                "data_window_rows": data_rows,
                "series": len(summary["series"]),
                "missing_span": DATA_WINDOW.as_record() if data_rows == 0 else "see raw_tables series",
                "publication_time_column": summary["publication_time_column"],
                "revision_history_column": summary["revision_history_column"],
                "timestamp_semantics": summary["timestamp_semantics"],
            }
        )
    records.append(
        {
            "family": MARKET_CAP_FAMILY,
            "venue": "SHARED",
            "source": _SRC_MARKET_CAP,
            "status": "EMPTY",
            "data_window_rows": 0,
            "series": 0,
            "missing_span": DATA_WINDOW.as_record(),
            "publication_time_column": False,
            "revision_history_column": False,
            "timestamp_semantics": {"from_schema": "MarketCapObservation (no raw table)", "from_data": "NO_PERSISTED_ROWS"},
        }
    )
    records.append(
        {
            "family": MARKET_CLOSURE_FAMILY,
            "venue": "SHARED",
            "source": _SRC_CLOSURES,
            "status": "PRESENT",
            "data_window_rows": None,
            "series": 1,
            "missing_span": f"coverage {CLOSURE_TABLE_COVERAGE_START.isoformat()}..{CLOSURE_TABLE_COVERAGE_END.isoformat()} spans every ETF flow window from {ETF_ERA_FIRST_TRADING_DATE.isoformat()}",
            "publication_time_column": False,
            "revision_history_column": False,
            "timestamp_semantics": {"from_schema": "frozen hash-bound table", "from_data": "loaded through load_closures"},
        }
    )
    return records


def _series_coverage(family: str, venue_id: str, table: str, entry: Mapping[str, Any] | None) -> dict[str, Any]:
    if entry is None:
        return {"family": family, "venue": venue_id, "source": table, "status": "EMPTY", "data_window_rows": 0, "missing_span": DATA_WINDOW.as_record()}
    window = entry["data_window"]
    return {
        "family": family,
        "venue": venue_id,
        "source": table,
        "provider": entry["key"]["provider"],
        "status": "COMPLETE" if window["missing"] == 0 else "GAPS_PRESERVED",
        "data_window_rows": window["observations"],
        "first": window["first"],
        "last": window["last"],
        "missing_hours": window["missing"],
        "missing_runs": window["missing_runs"],
        "prohibited_window_rows": entry["windows"][PROHIBITED_WINDOW.window_id]["rows"],
        "holdout_window_rows": entry["windows"][HOLDOUT_WINDOW.window_id]["rows"],
        "revision_history": "REVISION_HISTORY_UNAVAILABLE (schema has no revision field)",
    }


_PLAN: tuple[tuple[str, str, str, str, str], ...] = (
    # family, adapter id, protocol, persisted target, cadence
    (ETF_FLOW_FAMILY, "COINGLASS_ETF_FLOW_ADAPTER_V1", "btc_predictor.data.EtfFlowProvider", "raw.etf_flows + hash-bound publication/revision evidence", "daily per fund"),
    (FUNDING_RATE_FAMILY, "BINANCE_VISION_FUNDING_ADAPTER_V1", "btc_predictor.data.DerivativesProvider.fetch_funding_rates", "raw.funding_rates", "8h settlements"),
    (OPEN_INTEREST_FAMILY, "BINANCE_VISION_OPEN_INTEREST_ADAPTER_V1", "btc_predictor.data.DerivativesProvider.fetch_open_interest", "raw.open_interest", "hourly snapshots (USD)"),
    (PERP_VOLUME_FAMILY, "BINANCE_VISION_PERP_VOLUME_ADAPTER_V1", "btc_predictor.data.DerivativesProvider.fetch_perp_volume", "raw.perp_volume", "1h, interval start"),
    (FUTURES_BASIS_FAMILY, "BINANCE_VISION_QUARTERLY_BASIS_ADAPTER_V1", "btc_predictor.data.DerivativesProvider.fetch_futures_basis", "raw.futures_basis", "hourly snapshots"),
    (LIQUIDATION_FAMILY, "KRAKEN_FUTURES_LIQUIDATION_HISTORY_ADAPTER_V1", "btc_predictor.data.DerivativesProvider.fetch_liquidations", "raw.liquidations (per-side 1h aggregates) + hash-bound event-id and census evidence", "1h per side"),
    (MARKET_CAP_FAMILY, "COINMETRICS_MARKET_CAP_EVIDENCE_V1", "hash-bound evidence files (no raw table)", "backtest_evidence/research_backtest_v1/ market-cap evidence", "daily"),
)


def acquisition_plan(snapshot: Mapping[str, Any], blockers: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """The RBT-003 plan: what to collect, from where, and what it costs."""

    chosen = selected_sources()
    blocked_by_family = {
        LIQUIDATION_FAMILY: [b["blocker_id"] for b in blockers if b["blocker_id"] == "BLK-LIQUIDATION-HISTORICAL-CENSUS"],
        FUTURES_BASIS_FAMILY: [b["blocker_id"] for b in blockers if b["blocker_id"] == "BLK-FUTURES-BASIS-CONTRACT"],
    }
    coverage = {record["family"]: record for record in family_coverage(snapshot) if record["venue"] == "SHARED"}
    items = []
    subscriptions: dict[str, Decimal] = {}
    for family, adapter, protocol, target, cadence in _PLAN:
        candidate = chosen[family]
        start = _span_start(candidate)
        blocked = blocked_by_family.get(family, [])
        items.append(
            {
                "family": family,
                "source_candidate": candidate.candidate_id,
                "provider": candidate.provider,
                "span_start": start,
                "span_end": _iso(_LAST_DATA_HOUR),
                "database_status": coverage[family]["status"],
                "adapter_id": adapter,
                "adapter_protocol": protocol,
                "persisted_target": target,
                "cadence": cadence,
                "shape": candidate.persisted_shape,
                "cost_usd": canonical_decimal(candidate.cost_usd or Decimal("0")),
                "status": "BLOCKED_PENDING_POLICY_V4_DECISION" if blocked else "READY_FOR_RBT_003_AFTER_RBT_001A",
                "blocked_by": blocked,
                "revision_history": "REVISION_HISTORY_UNAVAILABLE",
                "licence": candidate.licence,
                "storage_rule": "hashes and provenance only in the repository" if candidate.redistribution != REDISTRIBUTION_NC_ATTRIBUTION else "values may be stored with attribution (non-commercial); persisted to the research database",
            }
        )
        subscriptions[f"{candidate.provider}|{candidate.cost_basis}"] = candidate.cost_usd or Decimal("0")
    gaps = []
    for record in family_coverage(snapshot):
        if record["family"] == REFERENCE_PRICE_FAMILY and record.get("missing_hours"):
            gaps.append({"venue": record["venue"], "missing_hours": record["missing_hours"], "missing_runs": record["missing_runs"]})
    total = sum(subscriptions.values(), Decimal("0"))
    return {
        "items": items,
        "reference_price_rerequest": {
            "adapter": "the existing BTC-020 venue adapters (no new adapter)",
            "cost_usd": "0",
            "rule": "re-request exactly these hours inside the data window; any hour the venue still does not return stays a preserved gap",
            "gaps": gaps,
        },
        "total_cost_usd": canonical_decimal(total),
        "total_cost_basis": "one CoinGlass Hobbyist month (USD 29) for ETF flows and per-fund AUM; every other selected source is free",
        "cost_if_rank_2_liquidations_chosen_usd": canonical_decimal(total + Decimal("4200")),
        "purchases_made": False,
    }


def _span_start(candidate: SourceCandidate) -> str:
    if candidate.family == ETF_FLOW_FAMILY:
        return ETF_ERA_FIRST_TRADING_DATE.isoformat()
    if candidate.family == MARKET_CAP_FAMILY:
        return _DATA_START.date().isoformat()
    if candidate.depth_start is None:
        return _iso(_DATA_START) or ""
    start = candidate.depth_start.replace("Z", "+00:00")
    moment = datetime.fromisoformat(start) if "T" in start else datetime.combine(date.fromisoformat(start), datetime.min.time())
    moment = moment if moment.tzinfo else moment.replace(tzinfo=UTC)
    return _iso(max(moment.astimezone(UTC), _DATA_START)) or ""


# --- earliest evaluable dates per venue -----------------------------------------------


def earliest_evaluable_by_venue(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    requirements = minimum_history_requirements()
    shared = projected_shared_series()
    venues: dict[str, Any] = {}
    for venue in REPLAY_VENUES:
        if not _venue_present(snapshot, exchange=venue.exchange, symbol=venue.symbol, provider=venue.provider):
            venues[venue.venue_id] = {"status": STATUS_NO_OBSERVATIONS}
            continue
        missing = rebuild_missing_hours(snapshot, exchange=venue.exchange, symbol=venue.symbol, provider=venue.provider)
        series = {**venue_bar_series(missing), **shared}
        results = earliest_evaluable_inputs(requirements, series)
        components = {
            component: results[name].as_record()
            for component, name in (
                (_TREND, "TREND_SCORE"),
                (_FLOW, "FLOW_SCORE"),
                (_POSITIONING, "POSITIONING_SCORE"),
                (_VOLATILITY, "VOLATILITY_SCORE"),
                (_STRUCTURE, "STRUCTURE_SCORE"),
            )
        }
        ec = results["ENTRY_CONVICTION"]
        regime = results["CORE_REGIME_SCORE"]
        combined = _all_of("ENTRY_CONVICTION_AND_CORE_REGIME", [ec, regime])
        venues[venue.venue_id] = {
            "missing_hours": len(missing),
            "inputs": {key: value.as_record() for key, value in sorted(results.items())},
            "entry_conviction_components": components,
            "entry_conviction": ec.as_record(),
            "core_regime": regime.as_record(),
            "every_component_and_core_regime": combined.as_record(),
        }
    return {
        "rule": "input completeness only: no composer, score, trade or outcome is computed",
        "measured_series": "venue daily/weekly/monthly canonical bars and RV_20 results, from the coverage snapshot",
        "projected_series": "ETF publication days and every derivatives/market-cap/liquidation series, from the selected sources' measured depth and cadence (the research database holds none of them)",
        "venues": venues,
    }


# --- the inventory artifact -------------------------------------------------------------


def build_inventory(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Assemble the canonical RBT-002 inventory from one coverage snapshot.

    Everything except the snapshot is computed from code, so rebuilding a
    persisted inventory from its own snapshot must reproduce it byte for byte.
    """

    if snapshot.get("snapshot_version") != DATABASE_COVERAGE_SNAPSHOT_VERSION:
        raise CoverageError("SNAPSHOT_VERSION", "unsupported coverage snapshot")
    census = census_owner.discover_decision_path()
    rows = enumerate_input_surface(census)
    blockers = derive_blockers(rows)
    structural = [b["blocker_id"] for b in blockers if b["entry_conviction_structurally_incomplete_on_every_date"]]
    veto_every_trade = [b["blocker_id"] for b in blockers if b["every_new_trade_blocked_on_every_date"]]
    plan = acquisition_plan(snapshot, blockers)
    return {
        "inventory_version": INVENTORY_VERSION,
        "ticket": INVENTORY_TICKET,
        "policy": INVENTORY_POLICY_VERSION,
        "availability_policy": INVENTORY_AVAILABILITY_POLICY_VERSION,
        "evidence_class": RESEARCH_EVIDENCE_CLASS,
        "canonical_reference": CANONICAL_REFERENCE_UNRESOLVED,
        "windows": [window.as_record() for window in COVERAGE_WINDOWS],
        "input_surface": {
            "summary": input_surface_summary(rows),
            "census": census_record(census),
            "rows": [row.as_record() for row in rows],
        },
        "database_coverage": snapshot,
        "family_coverage": family_coverage(snapshot),
        "exposures": _exposures(snapshot),
        "minimum_history": [item.as_record() for item in minimum_history_requirements()],
        "earliest_evaluable": earliest_evaluable_by_venue(snapshot),
        "sources": {
            "required_liquidation_depth": {
                "latest_acceptable_start": LIQUIDATION_REQUIRED_DEPTH_DATE.isoformat(),
                "preferred_start": LIQUIDATION_PREFERRED_DEPTH_DATE.isoformat(),
                "basis": f"{epic_x_corpus.LIQUIDATION_PERCENTILE_MIN_OBSERVATIONS} prior daily observations before {ETF_ERA_FIRST_TRADING_DATE.isoformat()}",
            },
            "certified_liquidation_definitions": {
                epic_x_corpus.PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_VERSION: epic_x_corpus.prospective_liquidation_percentile_adapter_contract()["definition_sha256"],
                epic_x_corpus.PROSPECTIVE_LIQUIDATION_CAPTURE_VERSION: epic_x_corpus.prospective_liquidation_capture_contract()["definition_sha256"],
                epic_x_corpus.LIQUIDATION_UTC_DAY_CENSUS_VERSION: epic_x_corpus.liquidation_utc_day_census_contract()["definition_sha256"],
            },
            "candidates": [item.as_record() for item in sorted(SOURCE_CANDIDATES, key=lambda c: (c.family, c.rank, c.candidate_id))],
            "selected": {family: candidate.candidate_id for family, candidate in sorted(selected_sources().items())},
            "semantic_pins": [{"pin": name, "rule": rule} for name, rule in SEMANTIC_PINS],
            "probes": [probe.as_record() for probe in PROBE_EVIDENCE],
        },
        "blockers": blockers,
        "acquisition_plan": plan,
        "verdict": {
            "epic_y_stops_for_owner_decision": bool(structural),
            "entry_conviction_structural_blockers": structural,
            "every_new_trade_vetoed_blockers": veto_every_trade,
            "policy_v4_decisions": [b["blocker_id"] for b in blockers if b["decision_required"] == DECISION_POLICY_V4],
            "owner_decisions": [b["blocker_id"] for b in blockers if b["decision_required"] == DECISION_OWNER],
            "rbt_003_scoping": "no scoping for owner-less inputs; source acquisition items are listed with their blocking decisions",
        },
        "safety": {
            "holdout_values_read": False,
            "prohibited_window_values_read": False,
            "value_columns_selected": False,
            "data_collected": "metadata probes only",
            "trading_outcome_computed": False,
            "btc_019_sealed_sample": "untouched and unopened",
        },
    }


def _exposures(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    raw = {
        table: {
            "prohibited_rows": summary["window_rows"][PROHIBITED_WINDOW.window_id],
            "holdout_rows": summary["window_rows"][HOLDOUT_WINDOW.window_id],
            "reserve_rows": summary["window_rows"][RESERVE_WINDOW.window_id],
            "series": [
                {
                    "key": entry["key"],
                    "prohibited": entry["windows"][PROHIBITED_WINDOW.window_id],
                    "holdout": entry["windows"][HOLDOUT_WINDOW.window_id],
                }
                for entry in summary["series"]
                if entry["windows"][PROHIBITED_WINDOW.window_id]["rows"] or entry["windows"][HOLDOUT_WINDOW.window_id]["rows"]
            ],
        }
        for table, summary in sorted(snapshot["raw_tables"].items())
    }
    outside = (PROHIBITED_WINDOW.window_id, HOLDOUT_WINDOW.window_id, RESERVE_WINDOW.window_id)
    columns = [column for column in snapshot["other_time_columns"] if column.get("window_rows")]
    observation_columns = {
        column["table"]: column
        for column in columns
        if column["column"] in ("observation_time", "timestamp")
    }
    other = []
    for column in columns:
        if not any(column["window_rows"][window] for window in outside):
            continue
        observed = observation_columns.get(column["table"])
        note = (
            "availability or bookkeeping instants only: this table's observation instants all lie in the data window"
            if observed is not None and observed is not column and not any(observed["window_rows"][w] for w in outside)
            else "observation instants outside the data window: exposure recorded"
        )
        other.append({**column, "note": note})
    prohibited = sum(item["prohibited_rows"] for item in raw.values())
    holdout = sum(item["holdout_rows"] for item in raw.values())
    return {
        "raw_tables": raw,
        "other_time_columns_outside_data_window": other,
        "raw_prohibited_window_rows": prohibited,
        "raw_holdout_window_rows": holdout,
        "recorded": (
            "pre-2020 rows exist in the research database; they were counted only. RBT-001 refuses any record before "
            "2020-01-01 and RBT-003 loaders must bound every query to the data window"
            if prohibited
            else "no pre-2020 raw rows"
        ),
    }


def inventory_bytes(inventory: Mapping[str, Any]) -> bytes:
    return canonical_json_bytes(_jsonable(inventory))


def inventory_digest(inventory: Mapping[str, Any]) -> str:
    return sha256_hex(inventory_bytes(inventory))


def write_inventory(snapshot: Mapping[str, Any], output_dir: Path) -> dict[str, Path]:
    inventory = build_inventory(snapshot)
    data = inventory_bytes(inventory)
    digest = sha256_hex(data)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "inventory": output_dir / INVENTORY_FILENAME,
        "digest": output_dir / INVENTORY_DIGEST_FILENAME,
        "report": output_dir / INVENTORY_REPORT_FILENAME,
    }
    paths["inventory"].write_bytes(data)
    paths["digest"].write_text(f"{digest}  {INVENTORY_FILENAME}\n", encoding="ascii")
    paths["report"].write_text(render_report(inventory, digest), encoding="utf-8")
    return paths


def render_report(inventory: Mapping[str, Any], digest: str) -> str:
    """A short human report rendered deterministically from the inventory."""

    summary = inventory["input_surface"]["summary"]
    census = inventory["input_surface"]["census"]
    lines = [
        "# RBT-002 historical input coverage inventory",
        "",
        f"`{inventory['inventory_version']}` under `{inventory['policy']}`. Evidence class "
        f"`{inventory['evidence_class']}`, canonical reference `{inventory['canonical_reference']}`.",
        f"Inventory SHA-256 `{digest}` over the canonical bytes of `{INVENTORY_FILENAME}`.",
        "",
        "Nothing here is a trading outcome. Holdout and pre-2020 rows were only counted.",
        "",
        "## Input surface (policy V3/V4 section 5A)",
        "",
        f"Discovered, not listed: `{census['summary']['census_version']}` walks the owner code from "
        f"{census['summary']['roots']} hand-written roots and reaches {census['summary']['callables']} callables and "
        f"{census['summary']['types']} types ({census['summary']['dataclass_types']} dataclasses, "
        f"{census['summary']['protocol_types']} protocol). {len(census['left_out_owner_definitions'])} owner-module "
        "definitions are left out, each with a recorded reason.",
        "",
        f"{summary['rows']} inputs: the fields of {summary['owner_input_types']} reached types, the parameters of "
        f"{summary['owner_call_sites']} roots and the parameters of {summary['owner_internal_callables']} internal callables.",
        "",
        "| census category | inputs |",
        "| --- | ---: |",
        *(f"| {category} | {count} |" for category, count in summary["count_by_census_category"].items()),
        "",
        "| family | raw leaf inputs | inputs drawing on the family (direct or upstream) |",
        "| --- | ---: | ---: |",
        *(
            f"| {family} | {summary['count_by_family_raw_leaves'].get(family, 0)} | {count} |"
            for family, count in summary["count_by_family"].items()
        ),
        "",
        "| kind | inputs |",
        "| --- | ---: |",
        *(f"| {kind} | {count} |" for kind, count in summary["count_by_kind"].items()),
        "",
        "Owner-less inputs:",
        "",
        *(
            f"- `{name}` ({entry['kind']}; Entry Conviction: {', '.join(entry['entry_components']) or 'none'})"
            for name, entry in summary["ownerless_inputs"].items()
        ),
        "",
        "Owner keyword defaults that no reached caller overrides (fixed constants of the decision path):",
        "",
        *(f"- `{item['owner']}.{item['parameter']}` = `{item['default']}`" for item in summary["owner_default_constants"]),
        "",
        "## Database coverage",
        "",
        "| family | venue | status | data-window rows | missing |",
        "| --- | --- | --- | ---: | ---: |",
        *(
            f"| {record['family']} | {record['venue']} | {record['status']} | {record.get('data_window_rows')} | {record.get('missing_hours', '-')} |"
            for record in inventory["family_coverage"]
        ),
        "",
        f"Exposure: {inventory['exposures']['raw_prohibited_window_rows']} pre-2020 raw rows and "
        f"{inventory['exposures']['raw_holdout_window_rows']} holdout raw rows. {inventory['exposures']['recorded']}.",
        "",
        "## Earliest evaluable date (input completeness only)",
        "",
        "| venue | Entry Conviction + core regime | lower bound if owner-less inputs were defined without extra history | blocking inputs |",
        "| --- | --- | --- | --- |",
    ]
    for venue, result in inventory["earliest_evaluable"]["venues"].items():
        combined = result.get("every_component_and_core_regime", {})
        lines.append(
            f"| {venue} | {combined.get('status')} {combined.get('available_date') or ''} | "
            f"{combined.get('lower_bound_available_at') or '-'} | {', '.join(combined.get('blocking_inputs', [])) or '-'} |"
        )
    lines += [
        "",
        "| venue | component | status | available at | lower bound |",
        "| --- | --- | --- | --- | --- |",
    ]
    for venue, result in inventory["earliest_evaluable"]["venues"].items():
        for component, record in result.get("entry_conviction_components", {}).items():
            lines.append(
                f"| {venue} | {component} | {record['status']} | {record['available_at'] or '-'} | {record['lower_bound_available_at'] or '-'} |"
            )
        regime = result.get("core_regime")
        if regime:
            lines.append(
                f"| {venue} | core regime | {regime['status']} | {regime['available_at'] or '-'} | {regime['lower_bound_available_at'] or '-'} |"
            )
    lines += [
        "",
        "## Source ranking",
        "",
        "| family | rank | role | candidate | depth | cost (USD) | adequate |",
        "| --- | ---: | --- | --- | --- | ---: | --- |",
        *(
            f"| {c['family']} | {c['rank']} | {c['role']} | `{c['candidate_id']}` | {c['depth_start'] or 'UNVERIFIED'} ({c['depth_status']}) | {c['cost_usd'] if c['cost_usd'] is not None else 'UNVERIFIED'} | {c['adequate']} |"
            for c in inventory["sources"]["candidates"]
        ),
        "",
        "## Blockers",
        "",
        *(
            f"- **{b['blocker_id']}** ({b['decision_required']}): {b['title']}."
            + (" Entry Conviction structurally incomplete on every date." if b["entry_conviction_structurally_incomplete_on_every_date"] else "")
            + (" Every new trade vetoed on every date." if b["every_new_trade_blocked_on_every_date"] else "")
            for b in inventory["blockers"]
        ),
        "",
        "## RBT-003 acquisition plan",
        "",
        "| family | source | span start | status | cost (USD) |",
        "| --- | --- | --- | --- | ---: |",
        *(
            f"| {item['family']} | `{item['source_candidate']}` | {item['span_start']} | {item['status']} | {item['cost_usd']} |"
            for item in inventory["acquisition_plan"]["items"]
        ),
        "",
        f"Total acquisition cost: USD {inventory['acquisition_plan']['total_cost_usd']} "
        f"({inventory['acquisition_plan']['total_cost_basis']}). Nothing was purchased.",
        "",
        "## Verdict",
        "",
        f"EPIC Y stops for owner decisions: {inventory['verdict']['epic_y_stops_for_owner_decision']} "
        f"({', '.join(inventory['verdict']['entry_conviction_structural_blockers'])}).",
        "",
    ]
    return "\n".join(lines)


# --- canonical encoding --------------------------------------------------------------


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return _iso(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return canonical_decimal(value)
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise CoverageError("NON_FINITE", "non-finite number in the inventory")
        return value
    raise CoverageError("NOT_SERIALISABLE", f"{type(value).__name__} has no canonical form")


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CoverageError("NON_UTC_TIMESTAMP", "timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _iso(value: datetime | None) -> str | None:
    return None if value is None else _utc(value).isoformat()


def _iso_any(value: Any) -> Any:
    if isinstance(value, datetime):
        return _iso(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


def _number(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return canonical_decimal(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


# --- command line ----------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=INVENTORY_VERSION)
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("collect", help="read-only coverage collection, then build the inventory")
    collect.add_argument("--output-dir", type=Path, default=ARTIFACT_DIRECTORY)
    collect.add_argument("--collected-at", default=None, help="ISO-8601 UTC instant recorded in the snapshot")
    rebuild = commands.add_parser("rebuild", help="rebuild the inventory from a persisted inventory's own snapshot")
    rebuild.add_argument("--artifact", type=Path, default=ARTIFACT_DIRECTORY / INVENTORY_FILENAME)
    rebuild.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    if args.command == "collect":
        collected_at = datetime.fromisoformat(args.collected_at) if args.collected_at else datetime.now(UTC)
        engine = open_research_engine()
        try:
            with engine.connect() as connection:
                snapshot = collect_database_coverage(connection, collected_at=collected_at)
        finally:
            engine.dispose()
        paths = write_inventory(snapshot, args.output_dir)
    else:
        import json

        snapshot = json.loads(args.artifact.read_bytes())["database_coverage"]
        paths = write_inventory(snapshot, args.output_dir or args.artifact.parent)
    for name, path in sorted(paths.items()):
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover - command line entry point
    sys.exit(main())
