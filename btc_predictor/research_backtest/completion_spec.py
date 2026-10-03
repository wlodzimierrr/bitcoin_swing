"""``CHAMPION_COMPLETION_SPEC_V1``: the frozen completion spec (RBT-002A).

Policy ``RESEARCH_BACKTEST_POLICY_V6`` section 6A makes this pre-registered,
versioned spec part of the EPIC Y research champion
``swing_v1.2+completion_v1``. It defines, once each, the 26 inputs the
reviewed RBT-002 inventory marks owner-less: its 25 ``OWNERLESS_UNDEFINED``
inputs and ``LEVEL_VOLUME_PERCENTILE``, whose Rulebook 9.2 fallback row
section 6A.8 supersedes for this champion. The human policy is
``docs/policies/champion_completion_spec_v1.md``.

What this module is, and is not:

- It is a **typed, declarative definition**. Every entry names the frozen
  owner parameter it supplies, the section 6A.2 source class and citation of
  every element of its rule, the owner helpers the RBT-004/RBT-005 composers
  call to apply it, its point-in-time rule, its missing-input behaviour and its
  warm-up. The canonical sorted JSON of that definition is frozen by SHA-256
  under ``backtest_evidence/research_backtest_v1/``.
- It adds **no executable strategy formula** (section 6A.7). It computes no
  score, signal, trade or outcome, reads no market value and touches no
  database. The only computation here is availability: each entry's warm-up
  is simulated over the observation instants the reviewed inventory's own
  coverage snapshot records, with the RBT-002 simulation primitives, so the
  dates are derived from coverage facts only (section 6A.1).
- It applies to EPIC Y research only. It is not ``swing_v1.2`` for advisory,
  paper or EPIC X use.

The inventory is bound by digest. If the reviewed inventory changes, building
the spec fails until the binding is changed explicitly (RBT-002 finding E3):
it is never silently re-read under a new digest.
"""

from __future__ import annotations

import argparse
import sys
import dataclasses
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import cache
from pathlib import Path
from typing import Any

from btc_predictor.features import positioning as positioning_owner
from btc_predictor.features import volatility as volatility_owner
from btc_predictor.levels import swing as swing_owner
from btc_predictor.research_backtest import coverage
from btc_predictor.research_backtest.replay_inputs import (
    CANONICAL_REFERENCE_UNRESOLVED,
    REPLAY_VENUES,
    RESEARCH_EVIDENCE_CLASS,
    SHARED_VOLUME_VENUE,
    canonical_json_bytes,
    sha256_hex,
)


# --- identity ------------------------------------------------------------------------------

SPEC_VERSION = "CHAMPION_COMPLETION_SPEC_V1"
SPEC_TICKET = "RBT-002A"
SPEC_POLICY_VERSION = "RESEARCH_BACKTEST_POLICY_V6"
SPEC_POLICY_DOCUMENT = "docs/policies/champion_completion_spec_v1.md"
RESEARCH_STRATEGY_ID = "swing_v1.2+completion_v1"
CHAMPION_BASE_IDENTITY = {
    "strategy_version": "swing_v1.2",
    "config_version": "strategy_config_v2",
    "parameter_set_id": "default_phase1",
}
SPEC_SCOPE = "EPIC_Y_RESEARCH_BACKTEST_ONLY"
SPEC_EXCLUDED_USES = ("ADVISORY", "PAPER_TRADING", "EPIC_X", "BTC_019")

# The reviewed RBT-002 inventory this spec covers (policy V6 section 6A: "as
# confirmed by its independent review"). Changing it needs an explicit rebind.
BOUND_INVENTORY_SHA256 = "108ab25b2240a76befc0f685cc684175e5207561d978bad099869fb0cc5efe3a"
BOUND_INVENTORY_VERSION = coverage.INVENTORY_VERSION
BOUND_INVENTORY_FILENAME = coverage.INVENTORY_FILENAME

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIRECTORY = REPOSITORY_ROOT / "backtest_evidence" / "research_backtest_v1"
SPEC_FILENAME = "champion_completion_spec_v1.json"
SPEC_DIGEST_FILENAME = "champion_completion_spec_v1.json.sha256"

# Section 6A.2 source classes, in precedence order: an element takes the first
# class that supplies it.
SOURCE_RULEBOOK = "RULEBOOK"
SOURCE_RULEBOOK_FALLBACK = "RULEBOOK_FALLBACK"
SOURCE_OWNER_CONVENTION = "OWNER_CONVENTION"
SOURCE_CONFIG = "CONFIG"
SOURCE_NEW_PARAMETER = "NEW_PARAMETER"
SOURCE_CLASSES = (
    SOURCE_RULEBOOK,
    SOURCE_RULEBOOK_FALLBACK,
    SOURCE_OWNER_CONVENTION,
    SOURCE_CONFIG,
    SOURCE_NEW_PARAMETER,
)
# Rulings that are not values: scope and omission rulings the policy itself
# authorises (section 6A.6 inert short-side inputs; the ticket's optional
# inputs, "explicit omission is a ruling").
SOURCE_POLICY_RULING = "POLICY_RULING"
# Choices the governing policy itself fixes for this spec (for example section
# 6A.8's Bitstamp volume source and unchanged weights, section 6A.9's guard).
# They bind the spec; they are not a section 6A.2 tier.
SOURCE_POLICY_MANDATE = "POLICY_V6_MANDATE"
ELEMENT_SOURCE_CLASSES = (*SOURCE_CLASSES, SOURCE_POLICY_MANDATE, SOURCE_POLICY_RULING)

DISPOSITION_DEFINED = "DEFINED"
DISPOSITION_OMITTED = "OMITTED"
DISPOSITION_INERT = "INERT"
DISPOSITIONS = (DISPOSITION_DEFINED, DISPOSITION_OMITTED, DISPOSITION_INERT)

# How RBT-004/RBT-005 may call a helper (policy section 5A.6, RBT-002 finding E4).
CENSUS_ROOT = "CENSUS_ROOT"
PROMOTE_TO_CENSUS_ROOT = "PROMOTE_TO_CENSUS_ROOT"
CLASSIFIED_INPUT_SOURCE = "CLASSIFIED_INPUT_SOURCE"
HELPER_CENSUS_STATUSES = (CENSUS_ROOT, PROMOTE_TO_CENSUS_ROOT, CLASSIFIED_INPUT_SOURCE)

# Inventory kinds the spec must cover: every owner-less, undefined row, plus the
# Rulebook-fallback row that section 6A.8 supersedes for this champion.
COVERED_INVENTORY_KINDS = ("OWNERLESS_UNDEFINED", "OWNERLESS_RULEBOOK_FALLBACK")
# Owner-less rows that are defined elsewhere and must not be redefined here.
EXCLUDED_OWNERLESS = {
    "LIQUIDATION_PERCENTILE": (
        "OWNERLESS_CERTIFIED_DEFINITION",
        "reused by reference from EPIC X PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_V1 under "
        "HISTORICAL_LIQUIDATION_HOUR_COMPLETENESS_V1 (policy V6 section 4A); RBT-002 records it, the spec does not",
    ),
}
OWNERLESS_KINDS = (*COVERED_INVENTORY_KINDS, "OWNERLESS_CERTIFIED_DEFINITION")


class CompletionSpecError(ValueError):
    """The completion spec cannot be built, bound or verified."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


# --- typed definition -------------------------------------------------------------------------


@dataclass(frozen=True)
class Element:
    """One part of a rule, with its section 6A.2 source class and citation."""

    name: str
    value: str
    source_class: str
    citation: str
    rationale: str = ""

    def as_record(self) -> dict[str, Any]:
        if self.source_class not in ELEMENT_SOURCE_CLASSES:
            raise CompletionSpecError("UNKNOWN_SOURCE_CLASS", f"{self.name}: {self.source_class}")
        if not self.citation.strip():
            raise CompletionSpecError("CITATION_MISSING", self.name)
        if self.source_class in (SOURCE_NEW_PARAMETER, SOURCE_POLICY_RULING) and not self.rationale.strip():
            raise CompletionSpecError("RATIONALE_MISSING", f"{self.name} is {self.source_class} without a rationale")
        if "\n" in self.rationale:
            raise CompletionSpecError("RATIONALE_NOT_ONE_LINE", self.name)
        return {
            "name": self.name,
            "value": self.value,
            "source_class": self.source_class,
            "citation": self.citation,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class Helper:
    """An owner helper the composer calls to apply a rule."""

    symbol: str
    use: str
    census: str

    def as_record(self) -> dict[str, Any]:
        if self.census not in HELPER_CENSUS_STATUSES:
            raise CompletionSpecError("UNKNOWN_CENSUS_STATUS", f"{self.symbol}: {self.census}")
        return {"symbol": self.symbol, "use": self.use, "census": self.census}


@dataclass(frozen=True)
class Consumer:
    """One inventory occurrence the entry supplies: owner path plus file:symbol."""

    occurrence: str
    location: str

    def as_record(self) -> dict[str, Any]:
        return {"occurrence": self.occurrence, "location": self.location}


@dataclass(frozen=True)
class UniformRule:
    """A section 6A.3 rule shared by every entry of its kind."""

    rule_id: str
    kind: str
    statement: str
    elements: tuple[Element, ...]
    helpers: tuple[Helper, ...]
    exceptions: tuple[str, ...] = ()
    rejected_alternatives: tuple[str, ...] = ()
    application_contract: tuple[tuple[str, str], ...] = ()

    def as_record(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "kind": self.kind,
            "statement": self.statement,
            "elements": [item.as_record() for item in self.elements],
            "helpers": [item.as_record() for item in self.helpers],
            "exceptions": list(self.exceptions),
            "rejected_alternatives": list(self.rejected_alternatives),
            "application_contract": dict(self.application_contract),
        }


# --- the bound inventory ----------------------------------------------------------------------


def inventory_path() -> Path:
    return ARTIFACT_DIRECTORY / BOUND_INVENTORY_FILENAME


@cache
def bound_inventory_bytes() -> bytes:
    """The reviewed inventory's bytes, refused unless they hash to the bound digest."""

    data = inventory_path().read_bytes()
    digest = sha256_hex(data)
    if digest != BOUND_INVENTORY_SHA256:
        raise CompletionSpecError(
            "INVENTORY_DIGEST_MISMATCH",
            f"{BOUND_INVENTORY_FILENAME} hashes to {digest}, not the bound {BOUND_INVENTORY_SHA256}; "
            "rebind the spec explicitly to a reviewed inventory, never silently",
        )
    return data


@cache
def bound_inventory() -> dict[str, Any]:
    return json.loads(bound_inventory_bytes())


def ownerless_occurrences(inventory: Mapping[str, Any]) -> dict[str, tuple[str, tuple[str, ...]]]:
    """Every owner-less inventory input: its kind and its row occurrences.

    A row with an owner-less kind but no input id, or one input id carrying two
    kinds, is refused: either would let a row escape coverage.
    """

    kinds: dict[str, set[str]] = {}
    occurrences: dict[str, list[str]] = {}
    for row in inventory["input_surface"]["rows"]:
        if row["kind"] not in OWNERLESS_KINDS and not str(row["kind"]).startswith("OWNERLESS"):
            continue
        if row["kind"] not in OWNERLESS_KINDS:
            raise CompletionSpecError("UNKNOWN_OWNERLESS_KIND", f"{row['owner']}.{row['name']}: {row['kind']}")
        if not row["input_id"]:
            raise CompletionSpecError("OWNERLESS_ROW_WITHOUT_ID", f"{row['owner']}.{row['name']}")
        kinds.setdefault(row["input_id"], set()).add(row["kind"])
        occurrences.setdefault(row["input_id"], []).append(f"{row['owner']}.{row['name']}")
    result = {}
    for input_id, found in sorted(kinds.items()):
        if len(found) != 1:
            raise CompletionSpecError("OWNERLESS_KIND_CONFLICT", f"{input_id}: {sorted(found)}")
        result[input_id] = (next(iter(found)), tuple(sorted(occurrences[input_id])))
    return result


def check_coverage(entries: Sequence[Any], inventory: Mapping[str, Any]) -> None:
    """Section 6A.7: every owner-less input covered exactly once, nothing else.

    Fails if a covered owner-less input (or one of its row occurrences) is not
    covered, if any input is covered twice, if the spec covers an id the
    inventory does not mark owner-less, or if a certified owner-less input is
    redefined.
    """

    ids = [entry.input_id for entry in entries]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        raise CompletionSpecError("INPUT_COVERED_TWICE", ", ".join(duplicates))
    found = ownerless_occurrences(inventory)
    required = {key: value for key, value in found.items() if value[0] in COVERED_INVENTORY_KINDS}
    excluded = {key: value for key, value in found.items() if value[0] not in COVERED_INVENTORY_KINDS}
    if sorted(excluded) != sorted(EXCLUDED_OWNERLESS) or any(
        excluded[key][0] != EXCLUDED_OWNERLESS[key][0] for key in excluded
    ):
        raise CompletionSpecError("CERTIFIED_OWNERLESS_SET_CHANGED", f"{sorted(excluded)} != {sorted(EXCLUDED_OWNERLESS)}")
    covered = {entry.input_id: entry for entry in entries}
    uncovered = sorted(set(required) - set(covered))
    if uncovered:
        raise CompletionSpecError("OWNERLESS_INPUT_UNCOVERED", ", ".join(uncovered))
    unknown = sorted(set(covered) - set(required))
    if unknown:
        raise CompletionSpecError("SPEC_COVERS_UNKNOWN_INPUT", ", ".join(unknown))
    for input_id, (kind, occurrences) in sorted(required.items()):
        entry = covered[input_id]
        if entry.inventory_kind != kind:
            raise CompletionSpecError("INVENTORY_KIND_MISMATCH", f"{input_id}: {entry.inventory_kind} != {kind}")
        supplied = tuple(sorted(item.occurrence for item in entry.consumers))
        if len(set(supplied)) != len(supplied):
            raise CompletionSpecError("OCCURRENCE_COVERED_TWICE", input_id)
        if supplied != occurrences:
            raise CompletionSpecError(
                "OCCURRENCES_DIFFER",
                f"{input_id}: missing {sorted(set(occurrences) - set(supplied))}, unknown {sorted(set(supplied) - set(occurrences))}",
            )


# --- warm-up: availability simulation over the inventory's coverage facts ---------------------
#
# Nothing below reads a market value. The observation instants come from the
# inventory's persisted coverage snapshot through RBT-002's own primitives
# (venue_bar_series, projected_shared_series and the minimum-history rules), so
# every date is a coverage fact (policy V6 section 6A.1).


def _requirements_by_id() -> dict[str, coverage.HistoryRequirement]:
    return {item.input_id: item for item in coverage.minimum_history_requirements()}


def inventory_input_series(
    input_id: str,
    requirements: Mapping[str, coverage.HistoryRequirement],
    series: Mapping[str, coverage.ObservationSeries],
) -> coverage.ObservationSeries | None:
    """Every observation instant at which an inventory input is evaluable.

    This extends RBT-002's first-instant simulation to the whole series, by the
    same rules: ``lookback_rows`` earlier rows, a rolling window including the
    current row, an ETF publication-day window, a count of prior observations in
    a half-open trailing window, and all-of over upstream inputs. ``None`` for
    an input that RBT-002 marks undefined.
    """

    requirement = requirements.get(input_id)
    if requirement is None:
        return series.get(input_id)
    rule = requirement.rule
    if rule in (coverage.RULE_UNDEFINED, coverage.RULE_UNIMPLEMENTED_FALLBACK):
        return None
    if rule == coverage.RULE_ALL_OF:
        members = [inventory_input_series(name, requirements, series) for name in requirement.upstream]
        if any(member is None for member in members):
            return None
        return _all_of_series(input_id, members)  # type: ignore[arg-type]
    base = series.get(requirement.series)
    if base is None:
        return None
    if rule == coverage.RULE_LOOKBACK_ROWS:
        kept = base.observations[requirement.parameter("lookback_rows") :]
    elif rule == coverage.RULE_ROLLING_ROWS:
        kept = base.observations[requirement.parameter("window_rows") - 1 :]
    elif rule == coverage.RULE_ETF_WINDOW:
        kept = base.observations[requirement.parameter("publication_days") - 1 :]
    elif rule == coverage.RULE_TRAILING_WINDOW:
        return trailing_window_series(
            input_id,
            base,
            window=timedelta(days=requirement.parameter("window_days")),
            min_prior=requirement.parameter("min_prior_observations"),
        )
    else:
        raise CompletionSpecError("UNKNOWN_HISTORY_RULE", f"{input_id}: {rule}")
    return coverage.ObservationSeries(input_id, tuple(kept), base.basis, base.source)


def trailing_window_series(
    name: str,
    base: coverage.ObservationSeries,
    *,
    window: timedelta,
    min_prior: int,
) -> coverage.ObservationSeries:
    """The observations of ``base`` with at least ``min_prior`` earlier
    observations in the half-open window ``[t - window, t)``: the predicate of
    RBT-002's ``trailing_window_index``, applied at every observation."""

    times = base.times()
    kept = []
    start = 0
    for index, current in enumerate(times):
        while start < index and times[start] < current - window:
            start += 1
        if index - start >= min_prior:
            kept.append(base.observations[index])
    return coverage.ObservationSeries(name, tuple(kept), base.basis, base.source)


def _all_of_series(name: str, members: Sequence[coverage.ObservationSeries]) -> coverage.ObservationSeries:
    """Observation instants every member shares, available when the last one is."""

    common = set(members[0].times())
    for member in members[1:]:
        common &= set(member.times())
    available: dict[datetime, datetime] = {}
    for member in members:
        for observed, at in member.observations:
            if observed in common:
                available[observed] = max(at, available.get(observed, at))
    basis = coverage._combined_basis(member.basis for member in members)
    source = "; ".join(sorted({member.source for member in members}))
    return coverage.ObservationSeries(name, tuple(sorted(available.items())), basis or coverage.BASIS_MEASURED, source)


def venue_series(snapshot: Mapping[str, Any], venue: Any) -> dict[str, coverage.ObservationSeries]:
    """One venue's measured bar series plus the projected shared series, exactly
    as RBT-002's ``earliest_evaluable_by_venue`` builds them."""

    missing = coverage.rebuild_missing_hours(snapshot, exchange=venue.exchange, symbol=venue.symbol, provider=venue.provider)
    return {**coverage.venue_bar_series(missing), **coverage.projected_shared_series()}


def _first(series: coverage.ObservationSeries | None) -> tuple[datetime, datetime] | None:
    if series is None or not series.observations:
        return None
    return series.observations[0]


# --- entries ----------------------------------------------------------------------------------

WARMUP_NONE = "NO_WARM_UP"
WARMUP_INHERITS = "INHERITS_UPSTREAM"
WARMUP_UNIFORM_RULE = "UNIFORM_RULE_OVER_UPSTREAM"
WARMUP_LEVEL_VOLUME = "LEVEL_SOURCE_BAR_VOLUME_PERCENTILE"
WARMUP_KINDS = (WARMUP_NONE, WARMUP_INHERITS, WARMUP_UNIFORM_RULE, WARMUP_LEVEL_VOLUME)


@dataclass(frozen=True)
class WarmUp:
    """How an entry's availability follows from inventory coverage facts.

    ``upstream`` names inventory minimum-history inputs (or spec entries). The
    per-venue dates are computed, never written by hand.
    """

    kind: str
    upstream: tuple[str, ...]
    statement: str
    rule_id: str | None = None

    def as_record(self) -> dict[str, Any]:
        if self.kind not in WARMUP_KINDS:
            raise CompletionSpecError("UNKNOWN_WARMUP_KIND", self.kind)
        return {
            "kind": self.kind,
            "upstream": list(self.upstream),
            "statement": self.statement,
            "rule_id": self.rule_id,
        }


@dataclass(frozen=True)
class SpecEntry:
    """One covered owner-less input."""

    input_id: str
    inventory_kind: str
    disposition: str
    consumers: tuple[Consumer, ...]
    rule: str
    elements: tuple[Element, ...]
    helpers: tuple[Helper, ...]
    point_in_time: str
    missing_input: str
    warm_up: WarmUp
    uniform_rule: str | None = None
    entry_components: tuple[str, ...] = ()
    accounted_causes: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    @property
    def source_class(self) -> str:
        """The governing section 6A.2 class: the lowest-precedence tier any
        element needed. An omitted or inert entry is governed by its ruling."""

        if self.disposition != DISPOSITION_DEFINED:
            return SOURCE_POLICY_RULING
        tiered = [item.source_class for item in self.elements if item.source_class in SOURCE_CLASSES]
        if not tiered:
            raise CompletionSpecError("TIERED_ELEMENT_MISSING", self.input_id)
        return max(tiered, key=SOURCE_CLASSES.index)

    def as_record(self) -> dict[str, Any]:
        if self.disposition not in DISPOSITIONS:
            raise CompletionSpecError("UNKNOWN_DISPOSITION", f"{self.input_id}: {self.disposition}")
        if not self.elements:
            raise CompletionSpecError("ELEMENTS_MISSING", self.input_id)
        classes = {item.source_class for item in self.elements}
        if self.disposition != DISPOSITION_DEFINED and SOURCE_POLICY_RULING not in classes:
            raise CompletionSpecError("RULING_MISSING", f"{self.input_id} is {self.disposition} without a policy ruling")
        if self.disposition == DISPOSITION_DEFINED and SOURCE_POLICY_RULING in classes:
            raise CompletionSpecError("RULING_ON_DEFINED_ENTRY", self.input_id)
        if self.disposition == DISPOSITION_DEFINED and self.uniform_rule is None and self.warm_up.kind == WARMUP_UNIFORM_RULE:
            raise CompletionSpecError("UNIFORM_RULE_MISSING", self.input_id)
        return {
            "input_id": self.input_id,
            "inventory_kind": self.inventory_kind,
            "disposition": self.disposition,
            "source_class": self.source_class,
            "consumers": [item.as_record() for item in sorted(self.consumers, key=lambda item: item.occurrence)],
            "entry_components": list(self.entry_components),
            "rule": self.rule,
            "uniform_rule": self.uniform_rule,
            "elements": [item.as_record() for item in self.elements],
            "helpers": [item.as_record() for item in self.helpers],
            "point_in_time": self.point_in_time,
            "missing_input": self.missing_input,
            "warm_up": self.warm_up.as_record(),
            "accounted_causes": list(self.accounted_causes),
            "notes": list(self.notes),
        }


# --- shared helpers and citations ---------------------------------------------------------------

_P = SOURCE_POLICY_RULING

H_BARS = Helper(
    "btc_predictor.research_backtest.replay_inputs.replay_market_bars_at",
    "the venue's point-in-time 1d/1w/1mo bars at the decision instant: RBT-001's wrapper, which calls BTC-040 "
    "build_canonical_market_bars(data_available_at=t) and restamps each bar to its last constituent hour's "
    "availability; the composer never calls build_canonical_market_bars directly",
    CLASSIFIED_INPUT_SOURCE,
)
H_SHARED_VOLUME_BARS = Helper(
    "btc_predictor.research_backtest.replay_inputs.build_shared_replay_snapshot",
    "SharedReplaySnapshot.volume_bars: the SHARED_RAW_VOLUME_1H Bitstamp 1h bars (policy V6 section 2), each hour "
    "used only when replay_inputs.modelled_bar_available_at(bar) <= t",
    CLASSIFIED_INPUT_SOURCE,
)
H_NEXT_BAR = Helper(
    "btc_predictor.data.ohlcv.next_bar_timestamp",
    "the close boundary of a level's pivot bar from its record's timestamp and timeframe (a pure computation)",
    PROMOTE_TO_CENSUS_ROOT,
)
H_CLOSURES = Helper(
    "btc_predictor.research.us_equity_market_closures.load_closures",
    "US_EQUITY_MARKET_CLOSURE_TABLE_V1 passed as market_holidays to every ETF window (policy V6 section 5)",
    CLASSIFIED_INPUT_SOURCE,
)
H_ZSCORE = Helper(
    "btc_predictor.features.rolling.rolling_zscore",
    "UNIFORM_ZSCORE_V1: rolling_zscore(list(H) + [x], window=len(H), min_periods=30, sample=False)[-1], called only "
    "when len(H) >= 30 and H is not exactly constant",
    PROMOTE_TO_CENSUS_ROOT,
)
H_PERCENTILE = Helper(
    "btc_predictor.features.rolling.rolling_percentile",
    "UNIFORM_PERCENTILE_V1: rolling_percentile(list(H) + [x], window=len(H), min_periods=365)[-1], called only when "
    "len(H) >= 365",
    PROMOTE_TO_CENSUS_ROOT,
)
H_NORMAL_CDF = Helper(
    "btc_predictor.quant.transforms.normal_cdf_score",
    "100 * Phi(z), the transform calculate_trend_score and calculate_flow_score apply (trend.py:315, flow.py:740)",
    PROMOTE_TO_CENSUS_ROOT,
)
H_GREATER_EQUAL = Helper(
    "btc_predictor.quant.comparisons.decision_greater_equal",
    "DECISION_COMPARISON_V1 inclusive threshold test, as every owner band uses",
    PROMOTE_TO_CENSUS_ROOT,
)
H_REGIME_CLASSIFICATION = Helper(
    "btc_predictor.features.regime.calculate_regime_classification",
    "classification of the smoothed core regime score under strategy_config.regime_thresholds",
    CENSUS_ROOT,
)
H_REGIME_SMOOTHING = Helper(
    "btc_predictor.features.regime.calculate_regime_smoothing",
    "the smoothed core regime score every setup detector reads (Rulebook 10 line 1157)",
    CENSUS_ROOT,
)

_Z_RULE = "UNIFORM_ZSCORE_V1"
_PCT_RULE = "UNIFORM_PERCENTILE_V1"

UNIFORM_ZSCORE = UniformRule(
    rule_id=_Z_RULE,
    kind="ZSCORE",
    statement=(
        "At decision instant t, let x be the owner value of the input's quantity at its latest observation D visible "
        "at t (the owners' latest-available convention). H is the owner values of the same quantity at the prior "
        "observations D' of its native series with D - 730 days <= D' < D, computed from the same point-in-time "
        "inputs; incomplete (None) values are skipped, never filled. z = (x - mean(H)) / sd(H) with the population "
        "standard deviation (ddof 0). z is None when x is None, when len(H) < 30, or when every value of H is "
        "exactly equal (zero variance; the refusal does not depend on float rounding). Otherwise z is computed by "
        "the BTC-041 helper. Nothing is zero-filled; None leaves the consuming owner's incomplete result standing."
    ),
    elements=(
        Element("form", "(x - mean) / sd over trailing history", SOURCE_RULEBOOK,
                "Rulebook v1.2 section 5.1 lines 413-421 (Z_M4 = (M_4 - mu)/sigma, 'Normalize using trailing "
                "historical data'), line 435 (Z_M12 = zscore(M_12)); section 6.2 line 641 (z(ETFNorm_5), "
                "z(ETFNorm_20), z(FlowAccel))"),
        Element("series", "the quantity's native owner series, one value per owner observation", SOURCE_OWNER_CONVENTION,
                "btc_predictor/features/positioning.py:1087 _funding_average_history (one 7-day average per settlement); "
                "btc_predictor/features/volatility.py:1918 _realized_volatility_history (one RV_20 per daily result)"),
        Element("current_value", "the owner value at the latest observation visible at t", SOURCE_OWNER_CONVENTION,
                "btc_predictor/features/positioning.py:486 (observation_time = latest visible observation)"),
        Element("window", "730 days, half-open [D - 730 days, D), anchored at the current observation D",
                SOURCE_NEW_PARAMETER,
                "value from Rulebook v1.2 section 8.1 line 861 (VolPercentile = Percentile(RV_20, 2yr)) and "
                "btc_predictor/features/volatility.py:136 DEFAULT_VOLATILITY_PERCENTILE_WINDOW_DAYS = 730; the 180-day "
                "z window of Rulebook section 7.1 line 697 / positioning.py:83 is not adoptable",
                "180 days holds at most 25 prior weekly observations, so weekly z-scores could never reach 30; 730 days is "
                "the Rulebook's other normalisation window; the flow owner's 20-observation count window was rejected."),
        Element("prior_window_exclusion", "the current observation D is never in H", SOURCE_OWNER_CONVENTION,
                "btc_predictor/features/positioning.py:1087-1098 (window_start <= t < observation_time); "
                "btc_predictor/quant/rolling.py:347 _prior_windows"),
        Element("minimum_prior_observations", "30", SOURCE_OWNER_CONVENTION,
                "btc_predictor/features/positioning.py:84 DEFAULT_FUNDING_MIN_ZSCORE_OBSERVATIONS = 30 (also :88 basis, "
                ":93 OI growth)"),
        Element("degrees_of_freedom", "0 (population standard deviation)", SOURCE_OWNER_CONVENTION,
                "btc_predictor/features/positioning.py:1260-1264 (variance / len(history)); "
                "btc_predictor/quant/rolling.py:436 (sample=False -> ddof 0)"),
        Element("zero_variance", "exactly constant H refuses (None)", SOURCE_OWNER_CONVENTION,
                "btc_predictor/features/positioning.py:1266-1267 (volatility == 0 refuses; FUNDING_HEALTH_ZERO_VARIANCE); "
                "btc_predictor/quant/rolling.py:108 (deviations != 0); exact equality, the test policy V6 section 6A.9 "
                "prescribes for futures basis"),
        Element("missing_history_points", "skipped, never zero-filled", SOURCE_OWNER_CONVENTION,
                "btc_predictor/features/flow.py:1019 (_latest_zscore skips None history values); Rulebook v1.2 "
                "section 4.2 line 391"),
        Element("helper", "btc_predictor.features.rolling.rolling_zscore", SOURCE_OWNER_CONVENTION,
                "btc_predictor/features/rolling.py:62 (BTC-041 prior-window z-score; policy V6 section 6A.2 tier 3)"),
    ),
    helpers=(H_ZSCORE,),
    exceptions=(),
    rejected_alternatives=(
        "The positioning convention unchanged (180 days, 30 observations; positioning.py:83-84): infeasible on native "
        "weekly series, whose [D - 180 days, D) holds at most 25 prior observations.",
        "The flow owner's count window (20 observations, minimum 20; flow.py:477 spot_perp_participation_from_rows, :1011 "
        "_latest_zscore; EPIC X's certified CVD window, prospective_integration_corpus.py:3265): a 20-row window over "
        "overlapping 5/20-day sums or 28/84-day returns measures recent change rather than 'trailing historical data' "
        "(Rulebook 5.1), spans 20 days or 20 weeks depending on cadence, and starts the flow z-scores earlier "
        "(2024-03-10 against 2024-03-24), which trades more (section 6A.5).",
        "Sampling every quantity at each daily decision instant (180 days, 30 samples): weights each weekly value about "
        "seven times and each weekend-straddling ETF day three times, and starts earlier (trades more).",
    ),
    application_contract=(
        ("history_selection", "Select H by observation time in [D - 730 days, D), after PIT visibility filtering; skip None, never extend the time window to replace gaps."),
        ("missing_or_short", "If x is None or len(H) < 30, return None without calling rolling_zscore."),
        ("constant_history_predicate", "all(h == H[0] for h in H)"),
        ("constant_history_refusal", "Evaluate exact equality on the original owner values BEFORE float conversion or rolling_zscore; if true, return None without calling the helper, whether or not x equals H[0]. No tolerance."),
        ("owner_call", "Otherwise call rolling_zscore((*H, x), window=len(H), min_periods=30, sample=False) and use only its last result. The row window is the count of the already time-selected H, never 730 rows."),
        ("required_tests", "Non-terminating constant histories at full window size (0.1, 1/3, 0.015*365/90), equal and different current values, no helper invocation on refusal, both native and 64-bit longdouble; time-boundary and gap exclusion; nonconstant owner parity. RBT-004 implements and tests this contract."),
    ),
)

UNIFORM_PERCENTILE = UniformRule(
    rule_id=_PCT_RULE,
    kind="PERCENTILE",
    statement=(
        "For a quantity observed once per UTC day, the percentile of the current value x at observation D is the "
        "midrank (count(h < x) + 0.5 * count(h == x)) / len(H) * 100 over H, the same quantity's values at the "
        "prior daily observations D' with D - 730 days <= D' < D; undefined values are skipped. It is None when x "
        "is None or len(H) < 365. Computed by the BTC-041 helper. Nothing is zero-filled."
    ),
    elements=(
        Element("form", "midrank percentile on 0-100", SOURCE_OWNER_CONVENTION,
                "btc_predictor/features/volatility.py:1967-1973 _percentile_rank; btc_predictor/quant/rolling.py:142"),
        Element("series", "the quantity observed once per UTC day", SOURCE_OWNER_CONVENTION,
                "btc_predictor/features/volatility.py:1112 volatility_percentile over daily RV_20 results; EPIC X "
                "LIQUIDATION_PERCENTILE one observation per UTC census day (policy V6 section 4A)"),
        Element("window", "730 days, half-open [D - 730 days, D)", SOURCE_OWNER_CONVENTION,
                "btc_predictor/features/volatility.py:136, :1924-1929; Rulebook v1.2 section 8.1 line 861 (2yr)"),
        Element("prior_window_exclusion", "the current observation D is never in H", SOURCE_OWNER_CONVENTION,
                "btc_predictor/features/volatility.py:1929 (observation_time < current)"),
        Element("minimum_prior_observations", "365", SOURCE_OWNER_CONVENTION,
                "btc_predictor/features/volatility.py:137 DEFAULT_VOLATILITY_PERCENTILE_MIN_OBSERVATIONS = 365"),
        Element("missing_history_points", "skipped, never zero-filled", SOURCE_OWNER_CONVENTION,
                "btc_predictor/features/volatility.py:1928 (realized_volatility is not None)"),
        Element("helper", "btc_predictor.features.rolling.rolling_percentile", SOURCE_OWNER_CONVENTION,
                "btc_predictor/features/rolling.py:81 (BTC-041 prior-window percentile; policy V6 section 6A.2 tier 3)"),
    ),
    helpers=(H_PERCENTILE,),
    exceptions=(),
    application_contract=(
        ("history_selection", "Select H by observation time in [D - 730 days, D), after PIT visibility filtering; skip None, never extend the time window to replace gaps."),
        ("missing_or_short", "If x is None or len(H) < 365, return None without calling rolling_percentile."),
        ("owner_call", "Otherwise call rolling_percentile((*H, x), window=len(H), min_periods=365) and use only its last result. No padding, zero-fill or fixed 730-row lookback."),
    ),
)
UNIFORM_RULES = (UNIFORM_ZSCORE, UNIFORM_PERCENTILE)


def _normalisation(rule: UniformRule) -> Element:
    governing = max((item.source_class for item in rule.elements), key=SOURCE_CLASSES.index)
    inherited = [item.name for item in rule.elements if item.source_class == SOURCE_NEW_PARAMETER]
    rationale = f"inherits the uniform rule's NEW_PARAMETER element(s): {', '.join(inherited)}." if inherited else ""
    return Element(
        "normalisation", rule.rule_id, governing, f"uniform rule {rule.rule_id} (policy V6 section 6A.3)", rationale
    )


def _causes(input_id: str, *suffixes: str) -> tuple[str, ...]:
    return tuple(f"{input_id}_{suffix}" for suffix in suffixes)


# --- trend and flow z-scores (UNIFORM_ZSCORE_V1) ---------------------------------------------------

_TREND_MISSING = (
    "x None, len(H) < 30 or an exactly constant H gives z = None. TrendScoreInput has no None path "
    "(btc_predictor/features/trend.py:57-62; calculate_trend_score raises RuntimeError at :136), so the composer does "
    "not call calculate_trend_score and passes trend_score=None to every consumer: ENTRY_CONVICTION_INPUT_MISSING, "
    "REGIME_SCORE_CORE_INPUT_MISSING, BULL_TREND_CONTINUATION_INPUT_MISSING / BULLISH_RESET_INPUT_MISSING and "
    "HOLD_SCORE_INPUT_MISSING stand, and the decision is STRUCTURALLY_UNEVALUABLE. Never zero-filled."
)
_FLOW_MISSING = (
    "x None, len(H) < 30 or an exactly constant H gives z = None: calculate_flow_score records "
    "FLOW_SCORE_CORE_INPUT_MISSING with score None (btc_predictor/features/flow.py:716-718, :751), so Entry "
    "Conviction and the core regime are incomplete and the decision is STRUCTURALLY_UNEVALUABLE. Never zero-filled."
)
_BAR_PIT = (
    "Only canonical bars whose close boundary and modelled availability are at or before t (BTC-040 "
    "build_canonical_market_bars with data_available_at=t; policy V6 section 4 INTERVAL). The history values come "
    "from the same visible bars, so nothing after t enters."
)
_ETF_PIT = (
    "Only EtfFlow rows with available_at <= t (DAILY_PUBLISHED, T+2 00:00, policy V6 section 4; flow.py:854-856). "
    "Each history value D' is the owner called with as_of=t and end_date=D', the per-window fund universe of "
    "policy V6 section 5 and market_holidays = US_EQUITY_MARKET_CLOSURE_TABLE_V1; every value uses the information "
    "set at t."
)


def _trend_z(input_id: str, field: str, line: int, upstream: str, owner: str, owner_line: str, formula: Element) -> SpecEntry:
    return SpecEntry(
        input_id=input_id,
        inventory_kind="OWNERLESS_UNDEFINED",
        disposition=DISPOSITION_DEFINED,
        consumers=(Consumer(f"btc_predictor.features.trend.TrendScoreInput.{field}", f"btc_predictor/features/trend.py:{line} TrendScoreInput.{field}"),),
        rule=(
            f"z of {upstream} under {_Z_RULE}: x is the last element of {owner} over the canonical bars visible at t; "
            f"H is the same owner series at the observations in [D - 730 days, D)."
        ),
        elements=(formula, _normalisation(UNIFORM_ZSCORE)),
        helpers=(
            Helper(f"btc_predictor.features.{owner}", f"the {upstream} series (Rulebook 5.1)", CENSUS_ROOT),
            H_BARS,
            H_ZSCORE,
        ),
        point_in_time=_BAR_PIT,
        missing_input=_TREND_MISSING,
        warm_up=WarmUp(WARMUP_UNIFORM_RULE, (upstream,), f"{_Z_RULE} over the native {upstream} series", _Z_RULE),
        uniform_rule=_Z_RULE,
        entry_components=("trend",),
        accounted_causes=_causes(input_id, "INPUT_MISSING", "INSUFFICIENT_HISTORY", "ZERO_VARIANCE"),
        notes=(
            f"{owner_line}: the owner's lookback counts rows, so an omitted bar is read as contiguous (the policy V6 "
            "section 7 row-versus-session limitation class); disclosed, not changed.",
        ),
    )


def _flow_z(input_id: str, field: str, upstream: str, owner_call: str, formula: Element, extra: tuple[Helper, ...]) -> SpecEntry:
    return SpecEntry(
        input_id=input_id,
        inventory_kind="OWNERLESS_UNDEFINED",
        disposition=DISPOSITION_DEFINED,
        consumers=(Consumer(f"btc_predictor.features.flow.FlowScoreInput.{field}", f"btc_predictor/features/flow.py:304 FlowScoreInput.{field}"),),
        rule=(
            f"z of {upstream} under {_Z_RULE}: x = {owner_call} at its latest US publication day D visible at t; H is "
            "the same quantity at the US publication days D' in [D - 730 days, D), each with end_date=D'. All three "
            "flow z-scores at one decision are anchored at the same D."
        ),
        elements=(formula, _normalisation(UNIFORM_ZSCORE)),
        helpers=(*extra, H_CLOSURES, H_ZSCORE),
        point_in_time=_ETF_PIT,
        missing_input=_FLOW_MISSING,
        warm_up=WarmUp(WARMUP_UNIFORM_RULE, (upstream,), f"{_Z_RULE} over the native {upstream} publication-day series", _Z_RULE),
        uniform_rule=_Z_RULE,
        entry_components=("flow",),
        accounted_causes=_causes(input_id, "INPUT_MISSING", "INSUFFICIENT_HISTORY", "ZERO_VARIANCE"),
        notes=(
            "ETF_CORE always also records FLOW_SCORE_P1_INPUT_MISSING (CVD absent; Rulebook 6.2 Phase 1 fallback, "
            "policy V6 section 5); that is an accounted cause, not a spec gap.",
        ),
    )


_H_ETF5 = Helper("btc_predictor.features.flow.five_day_etf_flow", "ETFNorm_5 at D and at every history day D'", CENSUS_ROOT)
_H_ETF20 = Helper("btc_predictor.features.flow.twenty_day_etf_flow", "ETFNorm_20 at D and at every history day D'", CENSUS_ROOT)
_H_ACCEL = Helper(
    "btc_predictor.features.flow.etf_flow_acceleration",
    "FlowAccel from the 5- and 20-day results sharing one observation date (it raises on a mismatch, flow.py:431)",
    CENSUS_ROOT,
)


def _trend_and_flow_entries() -> tuple[SpecEntry, ...]:
    return (
        _trend_z(
            "TREND_Z_M4", "z_m4", 58, "MOMENTUM_4W", "momentum.four_week_momentum_from_daily_bars", "btc_predictor/features/momentum.py:59",
            Element("quantity", "M_4 = P_t / P_(t-28) - 1 on canonical daily closes", SOURCE_RULEBOOK,
                    "Rulebook v1.2 section 5.1 line 409; btc_predictor/features/momentum.py:59 four_week_momentum_from_daily_bars"),
        ),
        _trend_z(
            "TREND_Z_M12", "z_m12", 59, "MOMENTUM_12W", "momentum.twelve_week_momentum_from_daily_bars", "btc_predictor/features/momentum.py:67",
            Element("quantity", "M_12 = P_t / P_(t-84) - 1 on canonical daily closes", SOURCE_RULEBOOK,
                    "Rulebook v1.2 section 5.1 lines 429, 435; btc_predictor/features/momentum.py:67 twelve_week_momentum_from_daily_bars"),
        ),
        _trend_z(
            "TREND_Z_20W", "z_20w", 60, "MA_DISTANCE_20W", "trend.twenty_week_ma_distance_from_weekly_bars", "btc_predictor/features/trend.py:160",
            Element("quantity", "D_20W = (P_t - MA_20W) / MA_20W on canonical weekly bars", SOURCE_RULEBOOK,
                    "Rulebook v1.2 section 5.1 lines 439-447, Z_20W at section 5.2 line 485; "
                    "btc_predictor/features/trend.py:160 twenty_week_ma_distance_from_weekly_bars"),
        ),
        _trend_z(
            "TREND_Z_52H", "z_52h", 62, "HIGH_DISTANCE_52W", "trend.fifty_two_week_high_distance_from_weekly_bars", "btc_predictor/features/trend.py:209",
            Element("quantity", "D_52H = (P_t - H_52W) / H_52W on canonical weekly bars", SOURCE_RULEBOOK,
                    "Rulebook v1.2 section 5.1 lines 461-469, Z_52H at section 5.2 line 489; "
                    "btc_predictor/features/trend.py:209 fifty_two_week_high_distance_from_weekly_bars"),
        ),
        _flow_z(
            "FLOW_Z_ETF_NORM_5D", "etf_norm_5_zscore", "ETF_NORM_5D", "five_day_etf_flow(...).normalized_flow",
            Element("quantity", "ETFNorm_5 = sum of 5 publication days' net flow / total ETF assets", SOURCE_RULEBOOK,
                    "Rulebook v1.2 section 6.1 lines 549-565; btc_predictor/features/flow.py:381 five_day_etf_flow"),
            (_H_ETF5,),
        ),
        _flow_z(
            "FLOW_Z_ETF_NORM_20D", "etf_norm_20_zscore", "ETF_NORM_20D", "twenty_day_etf_flow(...).normalized_flow",
            Element("quantity", "ETFNorm_20 = sum of 20 publication days' net flow / total ETF assets", SOURCE_RULEBOOK,
                    "Rulebook v1.2 section 6.1 lines 567-577; btc_predictor/features/flow.py:403 twenty_day_etf_flow"),
            (_H_ETF20,),
        ),
        _flow_z(
            "FLOW_Z_FLOW_ACCEL", "flow_accel_zscore", "FLOW_ACCEL", "etf_flow_acceleration(five_day, twenty_day).acceleration",
            Element("quantity", "FlowAccel = ETFNorm_5 - ETFNorm_20 / 4", SOURCE_RULEBOOK,
                    "Rulebook v1.2 section 6.1 lines 579-587; btc_predictor/features/flow.py:425 etf_flow_acceleration"),
            (_H_ETF5, _H_ETF20, _H_ACCEL),
        ),
    )


# --- volatility: range percentile and returns ------------------------------------------------------

_RETURN_HORIZON = Element(
    "horizon", "7 canonical daily bars: R_7 = P_t / P_(t-7) - 1, signed, unclipped", SOURCE_NEW_PARAMETER,
    "form from Rulebook v1.2 section 5.1 lines 409, 429 (M_k = P_t / P_(t-k) - 1) via "
    "btc_predictor/features/momentum.py:75 price_momentum_from_daily_bars(bars, lookback_periods=7)",
    "No source fixes a horizon; 7 matches the Rulebook's 7-period changes (OI_7, RV_7, Setup B) and 28 would put Trend's "
    "M_4 inside Volatility; section 6A.5 is not monotone: more Orderliness/STRESS/EUPHORIA firing (fewer trades) but also CAPITULATION, enabling Setup C.",
)
_H_RETURN = Helper(
    "btc_predictor.features.momentum.price_momentum_from_daily_bars",
    "R_7: the last element of price_momentum_from_daily_bars(visible daily bars, lookback_periods=7)",
    PROMOTE_TO_CENSUS_ROOT,
)
_RETURN_NOTE = (
    "The owner helper counts rows, so a 7-row lookback across an omitted daily bar spans 8 days (policy V6 section 7 "
    "row-versus-session limitation class); disclosed, not changed."
)


def _volatility_entries() -> tuple[SpecEntry, ...]:
    return (
        SpecEntry(
            input_id="RANGE_PERCENTILE",
            inventory_kind="OWNERLESS_UNDEFINED",
            disposition=DISPOSITION_DEFINED,
            consumers=(
                Consumer("btc_predictor.features.volatility.CapitulationFlagInput.range_percentile", "btc_predictor/features/volatility.py:495 CapitulationFlagInput.range_percentile"),
                Consumer("btc_predictor.features.volatility.EuphoriaFlagInput.range_percentile", "btc_predictor/features/volatility.py:533 EuphoriaFlagInput.range_percentile"),
                Consumer("btc_predictor.features.volatility.OrderlinessScoreInput.range_percentile", "btc_predictor/features/volatility.py:315 OrderlinessScoreInput.range_percentile"),
            ),
            rule=(
                f"{_PCT_RULE} of the daily range fraction TRF(d) = TR(d) / close(d - 1 day), where TR is the BTC-041 true "
                "range of the canonical daily bar d (features.rolling.true_ranges) and close(d - 1 day) is the adjacent "
                "preceding bar's close. x = TRF at the latest daily bar D visible at t; H = TRF at the daily bars in "
                "[D - 730 days, D). The same value goes to all three consumers at t."
            ),
            elements=(
                Element("quantity", "TR(d) / close(d - 1 day) of the canonical daily bar", SOURCE_NEW_PARAMETER,
                        "btc_predictor/features/rolling.py:123 true_ranges (BTC-041; None after an absent session, "
                        ":157-206); Rulebook v1.2 sections 8.2 line 879, 24 lines 1936-1938, 1980, 2008 name extreme "
                        "ranges/moves without a measure",
                        "No source selects a range measure; true range is the only owner range measure and the prior-close "
                        "ratio makes it scale-free, like the RV_20 the volatility percentile ranks, so the ranking compares ranges, not price levels."),
                _normalisation(UNIFORM_PERCENTILE),
            ),
            helpers=(
                Helper("btc_predictor.features.rolling.true_ranges", "TR of each visible daily bar (None after a gap)", PROMOTE_TO_CENSUS_ROOT),
                H_BARS,
                H_PERCENTILE,
            ),
            point_in_time=_BAR_PIT,
            missing_input=(
                "x None (no adjacent preceding bar, a TR None after a gap) or len(H) < 365 gives None: "
                "OrderlinessScoreResult records ORDERLINESS_INPUT_MISSING with score None (volatility.py:1030-1031), so "
                "the volatility score, Entry Conviction and core regime are incomplete (STRUCTURALLY_UNEVALUABLE); "
                "CAPITULATION and EUPHORIA record *_INPUT_MISSING while flagged is still set by the present triggers. "
                "Never zero-filled."
            ),
            warm_up=WarmUp(WARMUP_UNIFORM_RULE, ("DAILY_TRUE_RANGE_FRACTION",), f"{_PCT_RULE} over the daily true-range fraction series", _PCT_RULE),
            uniform_rule=_PCT_RULE,
            entry_components=("volatility",),
            accounted_causes=_causes("RANGE_PERCENTILE", "INPUT_MISSING", "INSUFFICIENT_HISTORY"),
            notes=(
                "Raw price-unit true range was considered and rejected: ranked over 730 days it rises with the price "
                "level, so 'extreme range' would partly measure price. Neither reading is owner-fixed, and section 6A.5 "
                "is not monotone here (Orderliness trades less on a higher percentile, CAPITULATION/Setup C more).",
            ),
        ),
        SpecEntry(
            input_id="DOWNSIDE_RETURN",
            inventory_kind="OWNERLESS_UNDEFINED",
            disposition=DISPOSITION_DEFINED,
            consumers=(
                Consumer("btc_predictor.features.volatility.CapitulationFlagInput.downside_return", "btc_predictor/features/volatility.py:495 CapitulationFlagInput.downside_return"),
                Consumer("btc_predictor.features.volatility.OrderlinessScoreInput.downside_return", "btc_predictor/features/volatility.py:315 OrderlinessScoreInput.downside_return"),
                Consumer("btc_predictor.features.volatility.StressFlagInput.downside_return", "btc_predictor/features/volatility.py:459 StressFlagInput.downside_return"),
            ),
            rule=(
                "R_7 at the latest daily bar visible at t, signed and unclipped; the owners' negative thresholds "
                "(orderliness -0.08, STRESS -0.10, CAPITULATION -0.12) select the downside. The same value goes to "
                "all three consumers and to UPSIDE_RETURN."
            ),
            elements=(_RETURN_HORIZON,),
            helpers=(_H_RETURN, H_BARS),
            point_in_time=_BAR_PIT,
            missing_input=(
                "Fewer than 8 visible daily rows gives None: ORDERLINESS_INPUT_MISSING (incomplete Entry Conviction), "
                "STRESS_INPUT_MISSING and CAPITULATION_INPUT_MISSING. With a non-DISCRETIONARY STRESS input missing, the "
                "V4 STRESS mapping (policy V6 section 7, DISCRETIONARY-only) does not apply, so the composer's "
                "conservative reading is stress_flagged=None (HARD_VETO_INPUT_MISSING, fail closed). Never zero-filled."
            ),
            warm_up=WarmUp(WARMUP_INHERITS, ("DAILY_RETURN_7",), "7 daily rows after the first visible daily bar"),
            entry_components=("volatility",),
            accounted_causes=_causes("DOWNSIDE_RETURN", "INPUT_MISSING"),
            notes=(_RETURN_NOTE,),
        ),
        SpecEntry(
            input_id="UPSIDE_RETURN",
            inventory_kind="OWNERLESS_UNDEFINED",
            disposition=DISPOSITION_DEFINED,
            consumers=(
                Consumer("btc_predictor.features.volatility.EuphoriaFlagInput.upside_return", "btc_predictor/features/volatility.py:533 EuphoriaFlagInput.upside_return"),
            ),
            rule="The same signed R_7 as DOWNSIDE_RETURN at t; the EUPHORIA threshold (+0.12, default.toml:271) selects the upside.",
            elements=(_RETURN_HORIZON,),
            helpers=(_H_RETURN, H_BARS),
            point_in_time=_BAR_PIT,
            missing_input=(
                "None gives EUPHORIA_INPUT_MISSING; the upside leg cannot fire, so EUPHORIA cannot flag (the less "
                "conservative state for adds, disclosed). EUPHORIA is already incomplete on every date because "
                "systemic_euphoria is DISCRETIONARY. Never zero-filled."
            ),
            warm_up=WarmUp(WARMUP_INHERITS, ("DAILY_RETURN_7",), "7 daily rows after the first visible daily bar"),
            accounted_causes=_causes("UPSIDE_RETURN", "INPUT_MISSING"),
            notes=(
                _RETURN_NOTE,
                "MA_DISTANCE_20W >= 0.12 as an 'extension' reading was considered and rejected: the owner field is a "
                "return (BTC-115 'a large upside return'), and one horizon serves both directions (section 6A.3).",
            ),
        ),
    )


# --- structure: level reaction, level volume, capitulation anchor ------------------------------------

_LEVEL_SCOPE = Element(
    "member_scope", "cluster members whose feature_id is WEEKLY_SWING_LEVEL or MONTHLY_SWING_LEVEL", SOURCE_NEW_PARAMETER,
    "btc_predictor/levels/swing.py:29, :82 (WeeklySwingLevel / MonthlySwingLevel carry the pivot bar, timeframe and "
    "right_bars); btc_predictor/levels/clustering.py:39 LevelClusterMember: m.level_timestamp = member.source_timestamp, "
    "m.timeframe = member.source_timeframe, m.right_bars = int(member.source_record['right_bars']), m.price = "
    "member.price, m.level_type = member.level_type",
    "Only swing records carry a printed pivot bar and confirmation window, and a breakout/reclaim member shares its "
    "source swing's exact price, so it co-clusters with that swing.",
)
_LEVEL_AGGREGATION = Element(
    "cluster_aggregation", "minimum over in-scope members; None if no in-scope member or any member value is None",
    SOURCE_NEW_PARAMETER,
    "btc_predictor/levels/strength.py:234 calculate_level_strength_from_cluster takes one value per cluster",
    "The weakest-link reading gives the lowest level strength, so it trades less (section 6A.5), and a missing "
    "member value is never filled or ignored.",
)
_H_LEVEL_STRENGTH = Helper(
    "btc_predictor.levels.strength.calculate_level_strength_from_cluster",
    "level strength of the cluster the structure owner scores, with the two spec inputs",
    CENSUS_ROOT,
)
_H_CLUSTERS = Helper("btc_predictor.levels.clustering.cluster_price_levels", "the clusters and their member records", CENSUS_ROOT)
_H_WEEKLY_SWINGS = Helper("btc_predictor.levels.swing.detect_weekly_swing_levels", "weekly swing members and their bars", CENSUS_ROOT)
_H_MONTHLY_SWINGS = Helper("btc_predictor.levels.swing.detect_monthly_swing_levels", "monthly swing members and their bars", CENSUS_ROOT)
_LEVEL_MISSING = (
    "None gives LEVEL_STRENGTH_INPUT_MISSING with score None (btc_predictor/levels/strength.py:184-210, at any weight), "
    "then STRUCTURE_SCORE_INPUT_MISSING; Entry Conviction is incomplete (STRUCTURALLY_UNEVALUABLE). Never zero-filled."
)


def _structure_entries() -> tuple[SpecEntry, ...]:
    return (
        SpecEntry(
            input_id="LEVEL_REACTION_MAGNITUDE",
            inventory_kind="OWNERLESS_UNDEFINED",
            disposition=DISPOSITION_DEFINED,
            consumers=(
                Consumer("btc_predictor.levels.strength.LevelStrengthInput.reaction_magnitude_fraction", "btc_predictor/levels/strength.py:47 LevelStrengthInput.reaction_magnitude_fraction"),
                Consumer("btc_predictor.levels.strength.calculate_level_strength_from_cluster.reaction_magnitude_fraction", "btc_predictor/levels/strength.py:234 calculate_level_strength_from_cluster parameter reaction_magnitude_fraction"),
            ),
            rule=(
                "For each in-scope member m: B = the canonical bars of m.timeframe visible at t, k = the index of the bar "
                "with timestamp m.level_timestamp, c = close(B[k + m.right_bars]) (the last bar of the swing owner's own "
                "confirmation window); r(m) = (c - m.price) / m.price for a swing_low and (m.price - c) / m.price for a "
                "swing_high (always > 0 by the swing definition). The value is the minimum of r(m) over the cluster's "
                "in-scope members, as a fraction of price."
            ),
            elements=(
                Element("unit", "a fraction of the level price (full score at 0.10)", SOURCE_OWNER_CONVENTION,
                        "btc_predictor/levels/strength.py:47 reaction_magnitude_fraction, :40 and :316-325 (min(100, "
                        "fraction / 0.10 * 100)); default.toml:128 level_strength_reaction_full_fraction = 0.10"),
                Element("window", "the swing owner's right-side confirmation window", SOURCE_OWNER_CONVENTION,
                        "btc_predictor/levels/swing.py:134 detect_weekly_swing_levels (right_bars 3), :191 monthly "
                        "(right_bars 2); default.toml:115-116"),
                Element("price_point", "close of the last confirming bar (net reaction retained at confirmation)",
                        SOURCE_NEW_PARAMETER,
                        "Rulebook v1.2 section 9.2 lines 990-998 (ReactionScore = f(ReactionMagnitude / ATR), "
                        "ReactionMagnitude undefined)",
                        "The net move kept at confirmation is never larger than the peak excursion, so it is the trades-less reading."),
                _LEVEL_SCOPE,
                _LEVEL_AGGREGATION,
            ),
            helpers=(_H_LEVEL_STRENGTH, _H_CLUSTERS, _H_WEEKLY_SWINGS, _H_MONTHLY_SWINGS, H_BARS),
            point_in_time=(
                "Every bar read closes at or before the member's detected_at (btc_predictor/levels/swing.py:342 "
                "_swing_detected_at), which is at or before t; the cluster owner already drops members detected after t."
            ),
            missing_input=_LEVEL_MISSING,
            warm_up=WarmUp(WARMUP_INHERITS, ("WEEKLY_SWING_LEVELS",), "available whenever a weekly swing level is"),
            entry_components=("structure",),
            accounted_causes=_causes("LEVEL_REACTION_MAGNITUDE", "INPUT_MISSING", "NO_SWING_MEMBER"),
            notes=(
                "Rulebook 9.2 asks for reaction 'relative to ATR'; the frozen owner fixes f as a price fraction with "
                "full score at 0.10, and an ATR multiple would saturate that ramp (trades more). Recorded limitation; "
                "the owner is not edited.",
                "The frozen owner's timeframe table and touch count (strength.py:32-39) and linear touch score differ from Rulebook "
                "9.2's tables; they are frozen owner behaviour, unchanged by this spec.",
            ),
        ),
        SpecEntry(
            input_id="LEVEL_VOLUME_PERCENTILE",
            inventory_kind="OWNERLESS_RULEBOOK_FALLBACK",
            disposition=DISPOSITION_DEFINED,
            consumers=(
                Consumer("btc_predictor.levels.strength.LevelStrengthInput.volume_percentile", "btc_predictor/levels/strength.py:48 LevelStrengthInput.volume_percentile"),
                Consumer("btc_predictor.levels.strength.calculate_level_strength_from_cluster.volume_percentile", "btc_predictor/levels/strength.py:234 calculate_level_strength_from_cluster parameter volume_percentile"),
            ),
            rule=(
                "For each in-scope member m: span [s, e) = [m.level_timestamp, next_bar_timestamp(m.level_timestamp, "
                "m.timeframe)) (its pivot bar), L = e - s. Q_L(d) = the sum of Bitstamp 1h volume over the L hours "
                "[d - L, d), defined only when every one of those hours is present, observed at each UTC 00:00 d. "
                f"p(m) = {_PCT_RULE} of Q_L(e) at observation e against Q_L(d) for d in [e - 730 days, e). The value is "
                "the minimum of p(m) over the cluster's in-scope members."
            ),
            elements=(
                Element("source", "Bitstamp raw 1h volume in all three venue runs", SOURCE_POLICY_MANDATE,
                        "policy V6 section 6A.8 'Source' and section 2 (shared volume source)"),
                Element("weights", "price_levels.level_strength_weights unchanged at 0.20 each", SOURCE_POLICY_MANDATE,
                        "policy V6 section 6A.8; btc_predictor/config/strategy/default.toml:141-146"),
                Element("attribution_span", "the member's pivot bar [level_timestamp, next_bar_timestamp(level_timestamp, timeframe))",
                        SOURCE_NEW_PARAMETER, "btc_predictor/levels/swing.py:29 WeeklySwingLevel.level_timestamp / timeframe",
                        "These are the hours in which the level's price printed, read from level-record fields alone; no owner produces touch or reaction records."),
                Element("comparator_series", "the same-length trailing Bitstamp volume sum observed once per UTC day",
                        SOURCE_NEW_PARAMETER, "btc_predictor/features/volatility.py:1112 (a rolling-window statistic observed daily and ranked over 730 days)",
                        "It is the same quantity, and only a daily cadence can reach the 365-observation minimum (104 weekly or 24 monthly bars cannot)."),
                _normalisation(UNIFORM_PERCENTILE),
                _LEVEL_SCOPE,
                _LEVEL_AGGREGATION,
            ),
            helpers=(_H_LEVEL_STRENGTH, _H_CLUSTERS, _H_WEEKLY_SWINGS, _H_MONTHLY_SWINGS, H_SHARED_VOLUME_BARS, H_NEXT_BAR, H_PERCENTILE),
            point_in_time=(
                "Every hour used ends at or before e, the pivot bar's close, which is before the member's detected_at "
                "and so before t; Bitstamp 1h bars are available at their close (policy V6 section 4 INTERVAL). The "
                "percentile is anchored at e, so it is fixed once computed and does not drift with later volume."
            ),
            missing_input=(
                _LEVEL_MISSING + " A member whose pivot bar closes before the computed warm-up date has no percentile; "
                "under the strict minimum any cluster containing one stays incomplete (declared warm-up cause "
                "LEVEL_VOLUME_PERCENTILE_WARM_UP), because policy V6 section 3 forbids pre-2020 history. A later pivot "
                "whose comparators fall below 365 because of Bitstamp hour gaps is LEVEL_VOLUME_PERCENTILE_INSUFFICIENT_HISTORY."
            ),
            warm_up=WarmUp(WARMUP_LEVEL_VOLUME, ("SHARED_RAW_VOLUME_1H", "WEEKLY_SWING_LEVELS", "MONTHLY_SWING_LEVELS"),
                           "first pivot-bar close with 365 defined daily comparators, per source timeframe"),
            uniform_rule=_PCT_RULE,
            entry_components=("structure",),
            accounted_causes=_causes("LEVEL_VOLUME_PERCENTILE", "INPUT_MISSING", "NO_SWING_MEMBER", "WARM_UP", "INSUFFICIENT_HISTORY"),
            notes=(
                "Policy V6 section 6A.8 supersedes the inventory's RULEBOOK_FALLBACK_EXISTS row and its note 'Do not "
                "define a new volume percentile' for this champion: the Rulebook 9.2 no-volume weights cannot run in "
                "the frozen owner without a placeholder.",
                "No price-level detection and no volume-profile binning: only level-record fields and the shared "
                "volume series are read.",
                "AVWAP and volume-profile members carry no printed pivot bar and are out of scope. Whether RBT-004 "
                "clusters them is its composition decision (their bars are as the reviewed inventory classifies them, "
                "Bitstamp raw OHLCV shared by all runs, policy V6 section 2). If it does, a nearest support cluster "
                "holding only such members gives None (NO_SWING_MEMBER), so Structure is incomplete; surfaced.",
            ),
        ),
        SpecEntry(
            input_id="CAPITULATION_EVENT",
            inventory_kind="OWNERLESS_UNDEFINED",
            disposition=DISPOSITION_OMITTED,
            consumers=tuple(
                Consumer(f"btc_predictor.levels.anchored_vwap.CapitulationEvent.{name}", f"btc_predictor/levels/anchored_vwap.py:56 CapitulationEvent.{name}")
                for name in ("detected_at", "event_timestamp", "exchange", "price", "provider", "reason_codes", "symbol")
            ) + (
                Consumer("btc_predictor.levels.anchored_vwap.anchored_vwap_anchor_from_capitulation_event.event", "btc_predictor/levels/anchored_vwap.py:261 anchored_vwap_anchor_from_capitulation_event parameter event"),
            ),
            rule=(
                "Explicitly omitted. The composer never builds a CapitulationEvent, never calls "
                "anchored_vwap_anchor_from_capitulation_event, and no capitulation-event AVWAP member enters clustering."
            ),
            elements=(
                Element("ruling", "OMITTED", _P,
                        "RBT-002A acceptance criteria ('explicit omission is a ruling'); Rulebook v1.2 section 9.2 lines "
                        "962-966 and 9.4 line 1080 (AVWAP optional, omit rather than score zero); BTC-097",
                        "No owner yields an event instant or price (the CAPITULATION flag returns a flag only), and AVWAP confluence is optional in Phase 1 (Rulebook 9.2, 9.4)."),
            ),
            helpers=(),
            point_in_time="Not applicable: nothing is computed.",
            missing_input=(
                "The optional member does not exist (Rulebook 9.2 'omit them'); no owner is called, so no reason code or "
                "incomplete result arises. Setup C still uses the CAPITULATION flag. Never filled: nothing is zero-filled "
                "and no event is invented."
            ),
            warm_up=WarmUp(WARMUP_NONE, (), "none: omitted"),
            entry_components=("structure",),
            notes=("If a later spec version defines the event, it would feed Structure through cluster confluence.",),
        ),
    )


# --- crowding, hold/add, regime and flow predicates ------------------------------------------------

_H_TRAIL = Helper(
    "btc_predictor.risk.trailing.trail_stop_for_position",
    "the BTC-156 trailing result T at t on the lifecycle as it stands before this instant's STOP_MOVE/ADD",
    CENSUS_ROOT,
)
_H_HIGHER_LOW = Helper(
    "btc_predictor.signals.higher_low.evaluate_higher_low_trigger",
    "the BTC-122 higher-low result R when it is RBT-005's trailing-structure producer (one producer for trail and add)",
    CENSUS_ROOT,
)
_H_STRUCTURE = Helper(
    "btc_predictor.features.structure.calculate_structure_score_from_clusters",
    "Structure Score v1.2 over the point-in-time clusters",
    CENSUS_ROOT,
)
_H_FLOW_SCORE = Helper("btc_predictor.features.flow.calculate_flow_score", "the FlowScoreResult used for AddScoreInput.flow_score at t", CENSUS_ROOT)
_H_TREND_REUSE = (
    "The z value is the one this spec supplies to TrendScoreInput at the same instant t (evaluated once, reused); "
    "no separate window, minimum or tuning."
)


def _lifecycle_entries() -> tuple[SpecEntry, ...]:
    return (
        SpecEntry(
            input_id="SEVERE_CROWDING_STATE",
            inventory_kind="OWNERLESS_UNDEFINED",
            disposition=DISPOSITION_DEFINED,
            consumers=(
                Consumer("btc_predictor.features.setup.BullTrendContinuationInput.severe_crowding_flagged", "btc_predictor/features/setup.py:172 BullTrendContinuationInput.severe_crowding_flagged"),
                Consumer("btc_predictor.signals.hard_veto.HardVetoInput.severe_crowding_flagged", "btc_predictor/signals/hard_veto.py:55 HardVetoInput.severe_crowding_flagged"),
            ),
            rule=(
                "C = calculate_crowding_flag(CrowdingFlagInput(funding z from funding_health, basis z from the "
                "E1-guarded futures_basis_health, OI-intensity percentile from open_interest_intensity), thresholds from "
                "strategy_config.positioning_flags.crowding). SEVERE_CROWDING_STATE = C.flagged if C.complete else None. "
                "The same value goes to the hard veto and to Setup A; C.reason_codes are passed as source evidence."
            ),
            elements=(
                Element("mapping", "severe crowding = the existing CROWDING flag", SOURCE_POLICY_MANDATE,
                        "policy V6 section 6A.5 ('severe crowding = the existing CROWDING flag'); Rulebook v1.2 section 11 "
                        "line 1230, section 14 line 1488, section 24 line 1958"),
                Element("owner_output", "CrowdingFlagResult.flagged", SOURCE_OWNER_CONVENTION,
                        "btc_predictor/features/positioning.py:860 calculate_crowding_flag"),
                Element("completeness_gate", "flagged if complete else None", SOURCE_OWNER_CONVENTION,
                        "btc_predictor/signals/trim.py:318 ('crowding.flagged if crowding.complete else None')"),
                Element("thresholds", "funding z >= 2.0, basis z >= 2.0, OI-intensity percentile >= 90", SOURCE_CONFIG,
                        "btc_predictor/config/strategy/default.toml:247-251 [positioning_flags.crowding]"),
            ),
            helpers=(
                Helper("btc_predictor.features.positioning.calculate_crowding_flag", "the CROWDING result C", CENSUS_ROOT),
                Helper("btc_predictor.features.positioning.funding_health", "funding z-score input", CENSUS_ROOT),
                Helper("btc_predictor.features.positioning.futures_basis_health", "basis z-score input, after the E1 guard", CENSUS_ROOT),
                Helper("btc_predictor.features.positioning.open_interest_intensity", "OI-intensity percentile input", CENSUS_ROOT),
            ),
            point_in_time=(
                "Each component owner filters its rows by available_at <= t and observation_time <= t (for example "
                "positioning.py:568-573) and anchors at its latest visible observation."
            ),
            missing_input=(
                "An incomplete C (CROWDING_INPUT_MISSING) gives None: the hard veto blocks the new trade with "
                "HARD_VETO_INPUT_MISSING and Setup A records BULL_TREND_CONTINUATION_INPUT_MISSING (both fail closed). "
                "Never filled with False."
            ),
            warm_up=WarmUp(WARMUP_INHERITS, ("FUNDING_HEALTH", "FUTURES_BASIS_HEALTH", "OI_INTENSITY_PERCENTILE"),
                           "available when all three CROWDING inputs are"),
            accounted_causes=_causes("SEVERE_CROWDING_STATE", "INPUT_MISSING"),
            notes=(
                "Every CROWDING instant now vetoes a new trade, so CROWDING's 'reduce entry quality' penalty can never "
                "act on a new trade; no owner consumes entry_quality_penalty. A named choice of swing_v1.2+completion_v1 "
                "under section 6A.5, not a swing_v1.2 change.",
            ),
        ),
        SpecEntry(
            input_id="MOMENTUM_PERSISTENCE_SCORE",
            inventory_kind="OWNERLESS_UNDEFINED",
            disposition=DISPOSITION_DEFINED,
            consumers=(Consumer("btc_predictor.features.hold.HoldScoreInput.momentum_persistence_score", "btc_predictor/features/hold.py:57 HoldScoreInput.momentum_persistence_score"),),
            rule="100 * Phi(z), z = the TREND_Z_M12 value at t. " + _H_TREND_REUSE,
            elements=(
                Element("source_module", "the momentum owner (btc_predictor.features.momentum)", SOURCE_OWNER_CONVENTION,
                        "btc_predictor/research/prospective_integration_corpus.py:3282 DERIVED_STATE_INPUTS "
                        "('momentum_persistence' -> btc_predictor.features.momentum at :3284; EPIC X certified corpus V1)"),
                Element("transform", "100 * Phi(z) onto 0-100", SOURCE_OWNER_CONVENTION,
                        "btc_predictor/features/trend.py:315 _standard_normal_score (normal_cdf_score); "
                        "btc_predictor/features/flow.py:740; Rulebook v1.2 section 5.2 line 497 (TrendScore precedent)"),
                Element("horizon", "12-week momentum (Z_M12)", SOURCE_NEW_PARAMETER,
                        "Rulebook v1.2 section 20 line 1775 (MomentumPersistence, no formula); section 5.1 line 435",
                        "Persistence reads the Rulebook's longer momentum horizon; M_4 is reserved for Add momentum so the two components never share a leaf."),
                _normalisation(UNIFORM_ZSCORE),
            ),
            helpers=(H_NORMAL_CDF, Helper("btc_predictor.features.momentum.twelve_week_momentum_from_daily_bars", "via TREND_Z_M12", CENSUS_ROOT)),
            point_in_time="As TREND_Z_M12 at t.",
            missing_input="TREND_Z_M12 None gives None: HOLD_SCORE_INPUT_MISSING (hold.py:200-205), so HOLD_SCORE_COLLAPSE and Hold-band trims cannot fire at t. Never zero-filled.",
            warm_up=WarmUp(WARMUP_INHERITS, ("TREND_Z_M12",), "as TREND_Z_M12"),
            accounted_causes=_causes("MOMENTUM_PERSISTENCE_SCORE", "INPUT_MISSING"),
            notes=(
                "DISCLOSED OVERLAP (Rulebook 4.1 lines 346-354, 32.17 line 2539): Z_M12 reaches Hold twice, inside Trend "
                "(Hold weight 0.2666667 on 100 * Phi(... + 0.30 * Z_M12 + ...)) and directly (Hold weight 0.1333333 on "
                "100 * Phi(Z_M12)). This spec makes the overlap explicit, quantified and versioned; validation by "
                "ablation cannot precede pre-registration. No overlap-free owner output exists, and a distinct "
                "persistence measure would be a new indicator. Surfaced for the owner and the independent review.",
            ),
        ),
        SpecEntry(
            input_id="ADD_MOMENTUM_SCORE",
            inventory_kind="OWNERLESS_UNDEFINED",
            disposition=DISPOSITION_DEFINED,
            consumers=(Consumer("btc_predictor.features.add.AddScoreInput.momentum_score", "btc_predictor/features/add.py:77 AddScoreInput.momentum_score"),),
            rule="100 * Phi(z), z = the TREND_Z_M4 value at t. " + _H_TREND_REUSE,
            elements=(
                Element("transform", "100 * Phi(z) onto 0-100", SOURCE_OWNER_CONVENTION,
                        "btc_predictor/features/trend.py:315 _standard_normal_score (normal_cdf_score); "
                        "btc_predictor/features/flow.py:740; Rulebook v1.2 section 5.2 line 497 (TrendScore precedent)"),
                Element("horizon", "4-week momentum (Z_M4)", SOURCE_NEW_PARAMETER,
                        "Rulebook v1.2 section 21 line 1817 (Momentum, no formula); section 5.1 lines 409-421",
                        "Add reads current thrust on the shorter Rulebook horizon; Add holds no Trend (Rulebook 4.1 rule 3, BTC-153), so M_4 reaches Add once."),
                _normalisation(UNIFORM_ZSCORE),
            ),
            helpers=(H_NORMAL_CDF, Helper("btc_predictor.features.momentum.four_week_momentum_from_daily_bars", "via TREND_Z_M4", CENSUS_ROOT)),
            point_in_time="As TREND_Z_M4 at t.",
            missing_input="TREND_Z_M4 None gives None: ADD_SCORE_INPUT_MISSING (add.py:252-257), so the add is blocked. Never zero-filled.",
            warm_up=WarmUp(WARMUP_INHERITS, ("TREND_Z_M4",), "as TREND_Z_M4"),
            accounted_causes=_causes("ADD_MOMENTUM_SCORE", "INPUT_MISSING"),
        ),
        SpecEntry(
            input_id="NEW_STRUCTURE_SCORE",
            inventory_kind="OWNERLESS_UNDEFINED",
            disposition=DISPOSITION_DEFINED,
            consumers=(Consumer("btc_predictor.features.add.AddScoreInput.new_structure_score", "btc_predictor/features/add.py:74 AddScoreInput.new_structure_score"),),
            rule=(
                "StructureScoreResult.score from calculate_structure_score_from_clusters at the add decision instant t, "
                "composed exactly as the entry-path Structure Score (same point-in-time clusters, level inputs and v1.2 "
                "weights) except entry_price = the add's reference price P_t (the current_price given to "
                "add_requirements_from_results) and stop_price = T.stop_price from trail_stop_for_position at t."
            ),
            elements=(
                Element("component", "NewStructure", SOURCE_RULEBOOK, "Rulebook v1.2 section 21 line 1811; section 26 line 2153 ('Structure Improves ... Raise Stop -> ADD')"),
                Element("owner_output", "StructureScoreResult.score", SOURCE_OWNER_CONVENTION, "btc_predictor/features/structure.py:303 calculate_structure_score_from_clusters"),
                Element("evaluation_point", "the add's reference price and the raised trailing stop", SOURCE_NEW_PARAMETER,
                        "btc_predictor/risk/trailing.py:359 trail_stop_for_position; btc_predictor/signals/add_requirements.py:259",
                        "Scoring the existing structure owner where the new tranche enters, under the raised stop, measures the structure the add relies on without a new indicator."),
            ),
            helpers=(_H_STRUCTURE, _H_TRAIL, _H_LEVEL_STRENGTH),
            point_in_time="The clusters, levels and trail result are the point-in-time ones at t.",
            missing_input=(
                "The value is StructureScoreResult.score when result.complete, else None. Under STRUCTURE_SCORE_V1_2 an "
                "incomplete result means no support cluster at or below P_t (STRUCTURE_SCORE_SUPPORT_MISSING) or an "
                "incomplete level strength (STRUCTURE_SCORE_INPUT_MISSING, for example NO_SWING_MEMBER or a pre-warm-up "
                "pivot). STRUCTURE_SCORE_TARGET_MISSING and STRUCTURE_SCORE_INVALID_RISK leave a complete v1.2 score "
                "(structure.py:455-470), passed unchanged; their codes are R/R-filter evidence only. None gives "
                "ADD_SCORE_INPUT_MISSING, so the add is blocked. Never zero-filled."
            ),
            warm_up=WarmUp(WARMUP_INHERITS, ("STRUCTURE_SCORE",), "as the Structure Score"),
            accounted_causes=_causes("NEW_STRUCTURE_SCORE", "INPUT_MISSING"),
            notes=("'Newness' is gated by NEW_STRUCTURAL_CONFIRMATION, not by this score.",),
        ),
        SpecEntry(
            input_id="NEW_STRUCTURAL_CONFIRMATION",
            inventory_kind="OWNERLESS_UNDEFINED",
            disposition=DISPOSITION_DEFINED,
            consumers=(
                Consumer("btc_predictor.signals.add_requirements.AddRequirementsInput.new_structural_confirmation", "btc_predictor/signals/add_requirements.py:109 AddRequirementsInput.new_structural_confirmation"),
                Consumer("btc_predictor.signals.add_requirements.add_requirements_from_results.new_structural_confirmation", "btc_predictor/signals/add_requirements.py:259 add_requirements_from_results parameter new_structural_confirmation"),
            ),
            rule=(
                "For an open long lifecycle L at t, evaluated on L before this instant's STOP_MOVE/ADD: T = "
                "trail_stop_for_position(L, structure=C_t, buffer=B_t, current_price=P_t, as_of=t), where C_t is the "
                "confirmed higher-low structure the composer supplies to the trail (one producer for trail and add) and "
                "the same T is then applied by apply_trailing_stop. E_last = the latest event_time of L's accepted ENTER "
                "or ADD transitions. True iff T.advanced and T.structure_type == 'HIGHER_LOW' and "
                "T.structure_level_timestamp > E_last (strict, the trades-less reading); None if T is incomplete "
                "(TRAILING_STOP_* incomplete codes) or the producer reports a data cause (for the BTC-122 higher-low "
                "producer, HIGHER_LOW_SOURCE_BAR_MISSING); otherwise False (pending or not-found structure is False). "
                "C_t's producer is RBT-005's (the reviewed inventory maps ConfirmedTrailingStructure there) and trail and "
                "add use the same one, but C_t.level_timestamp is always the timestamp of the structure's own bar, never "
                "a source swing's. With the BTC-122 producer: S = the latest WeeklySwingLevel swing_low with detected_at "
                "<= t, R = evaluate_higher_low_trigger(S, the daily bars visible at t, as_of=t), C_t exists iff "
                "R.triggered, with price = R.higher_low_price, level_timestamp = R.higher_low_timestamp and detected_at = "
                "R.detected_at."
            ),
            elements=(
                Element("requirement", "new bullish structure has formed and the stop can be raised", SOURCE_RULEBOOK,
                        "Rulebook v1.2 section 18.1 lines 1680-1681; section 22 lines 1854-1862, 1888; section 26 lines 2153, 2163"),
                Element("owner_acceptance", "the trailing owner accepts the higher low (not already used, below price, strictly tighter)",
                        SOURCE_OWNER_CONVENTION, "btc_predictor/risk/trailing.py:359 trail_stop_for_position, :124 TrailingStopResult, :881 _improves"),
                Element("newness_reference", "structure formed after the last accepted ENTER or ADD", SOURCE_NEW_PARAMETER,
                        "btc_predictor/portfolio/state_machine.py:341 PositionLifecycle.transitions (:356); :264 "
                        "PositionTransition event / event_time / accepted (:268, :271, :272); ENTER :99, ADD :101",
                        "Each add needs its own new structure (Rulebook 26 'Further Confirmation'); the transition time cannot be moved earlier by a trim."),
            ),
            helpers=(_H_TRAIL, _H_HIGHER_LOW, _H_WEEKLY_SWINGS),
            point_in_time="T and C_t use only bars, levels and buffers visible at t; E_last is engine state at t.",
            missing_input=(
                "None gives ADD_REQUIREMENTS_INPUT_MISSING plus ADD_REQUIREMENTS_NO_NEW_STRUCTURE (add blocked); False "
                "gives ADD_REQUIREMENTS_NO_NEW_STRUCTURE. Never filled with True."
            ),
            warm_up=WarmUp(WARMUP_INHERITS, ("WEEKLY_SWING_LEVELS",),
                           "an open position and a confirmed structure from RBT-005's producer; a weekly-swing-based "
                           "producer inherits WEEKLY_SWING_LEVELS"),
            accounted_causes=_causes("NEW_STRUCTURAL_CONFIRMATION", "INPUT_MISSING"),
            notes=(
                "Sequencing contract for RBT-005: applying the STOP_MOVE before evaluating the add makes the same structure "
                "TRAILING_STOP_STRUCTURE_ALREADY_USED (trailing.py:312), which would silently disable every add.",
                "One add instant per structure: a higher low the trail accepts at an instant where another add "
                "requirement fails is consumed by that STOP_MOVE and cannot confirm a later add (conservative).",
            ),
        ),
        SpecEntry(
            input_id="REGIME_SUPPORTIVE_PREDICATE",
            inventory_kind="OWNERLESS_UNDEFINED",
            disposition=DISPOSITION_DEFINED,
            consumers=(
                Consumer("btc_predictor.signals.add_requirements.AddRequirementsInput.regime_supportive", "btc_predictor/signals/add_requirements.py:111 AddRequirementsInput.regime_supportive"),
                Consumer("btc_predictor.signals.add_requirements.add_requirements_from_results.regime_supportive", "btc_predictor/signals/add_requirements.py:259 add_requirements_from_results parameter regime_supportive"),
            ),
            rule=(
                "K = calculate_regime_classification(R_t, thresholds=strategy_config.regime_thresholds), R_t the smoothed "
                "core regime score the setup detectors read at t. True iff K.regime is BULL or STRONG_BULL (smoothed score "
                ">= bull_min 65); None if K is incomplete."
            ),
            elements=(
                Element("band", "Bull or Strong Bull (score >= 65)", SOURCE_RULEBOOK,
                        "Rulebook v1.2 section 10 lines 1177-1178; section 11 Setup A lines 1197-1201; section 18.1 line 1682",
                        ""),
                Element("threshold", "regime_thresholds.bull_min = 65", SOURCE_CONFIG, "btc_predictor/config/strategy/default.toml:108"),
            ),
            helpers=(H_REGIME_CLASSIFICATION, H_REGIME_SMOOTHING),
            point_in_time="The smoothed regime score at t from point-in-time component scores.",
            missing_input="None gives ADD_REQUIREMENTS_INPUT_MISSING plus ADD_REQUIREMENTS_REGIME_UNSUPPORTIVE (add blocked). Never filled.",
            warm_up=WarmUp(WARMUP_INHERITS, ("CORE_REGIME_SCORE",), "as the core regime score"),
            accounted_causes=_causes("REGIME_SUPPORTIVE_PREDICATE", "INPUT_MISSING"),
            notes=(
                "Section 6A.5: 65 is the strictest regime floor of any long setup; Mild Bull (>= 55, Setup B) would trade more.",
            ),
        ),
        SpecEntry(
            input_id="FLOW_SUPPORTIVE_PREDICATE",
            inventory_kind="OWNERLESS_UNDEFINED",
            disposition=DISPOSITION_DEFINED,
            consumers=(
                Consumer("btc_predictor.signals.add_requirements.AddRequirementsInput.flow_supportive", "btc_predictor/signals/add_requirements.py:112 AddRequirementsInput.flow_supportive"),
                Consumer("btc_predictor.signals.add_requirements.add_requirements_from_results.flow_supportive", "btc_predictor/signals/add_requirements.py:259 add_requirements_from_results parameter flow_supportive"),
            ),
            rule=(
                "F = the FlowScoreResult used for AddScoreInput.flow_score at t. True iff decision_greater_equal(F.score, 60); "
                "None if F is incomplete. FlowScoreResult.interpretation is not the source (its owner bands differ from the Rulebook)."
            ),
            elements=(
                Element("band", "Supportive or better: FlowScore >= 60", SOURCE_RULEBOOK,
                        "Rulebook v1.2 section 6.2 interpretation lines 661-669 (60-75 'Supportive'); section 18.1 line 1683"),
            ),
            helpers=(_H_FLOW_SCORE, H_GREATER_EQUAL),
            point_in_time="As the flow score at t.",
            missing_input="None gives ADD_REQUIREMENTS_INPUT_MISSING plus ADD_REQUIREMENTS_FLOW_UNSUPPORTIVE (add blocked). Never filled.",
            warm_up=WarmUp(WARMUP_INHERITS, ("FLOW_SCORE",), "as the flow score"),
            accounted_causes=_causes("FLOW_SUPPORTIVE_PREDICATE", "INPUT_MISSING"),
            notes=(
                "Section 6A.5: the Rulebook offers 55 (initial long rule, line 675) and 60 (the band named 'Supportive'); 60 "
                "trades less. The tier-1 Rulebook 60 precedes the owner's SUPPORTIVE_FLOW label at 65 (section 6A.2).",
                "The flow owner's labels use 80/65/45/30 (flow.py:1074-1085) where Rulebook 6.2 uses 75/60/45/30; recorded, not resolved.",
            ),
        ),
    )


# --- exits, setups and the reward reference ----------------------------------------------------------

_BEAR_BANDS = ("MILD_BEAR", "BEAR", "STRONG_BEAR")


def _exit_setup_entries() -> tuple[SpecEntry, ...]:
    return (
        SpecEntry(
            input_id="REGIME_INVALIDATION_PREDICATE",
            inventory_kind="OWNERLESS_UNDEFINED",
            disposition=DISPOSITION_DEFINED,
            consumers=(
                Consumer("btc_predictor.signals.exit_rules.ExitRuleInput.regime_invalidated", "btc_predictor/signals/exit_rules.py:97 ExitRuleInput.regime_invalidated"),
                Consumer("btc_predictor.signals.exit_rules.exit_rules_for_position.regime_invalidated", "btc_predictor/signals/exit_rules.py:239 exit_rules_for_position parameter regime_invalidated"),
            ),
            rule=(
                "For an open long position at t: K_t = calculate_regime_classification of the smoothed core regime score "
                "at t; K_entry = the same classification at the position's ARM_ENTRY decision instant, persisted in the "
                f"decision ledger. True iff K_t.regime is in {list(_BEAR_BANDS)} (smoothed score < neutral_min 45) and "
                "K_entry.regime is not; None if K_t is incomplete or K_entry is unavailable; otherwise False."
            ),
            elements=(
                Element("band", "Mild Bear or below (smoothed score < 45)", SOURCE_RULEBOOK,
                        "Rulebook v1.2 section 10 lines 1173-1183 (35-45 Mild Bear); section 20 lines 1757, 1779-1780 "
                        "(REGIME_INVALIDATION, regime a persisted invalidation input)",
                        ""),
                Element("threshold", "regime_thresholds.neutral_min = 45", SOURCE_CONFIG, "btc_predictor/config/strategy/default.toml:110"),
                Element("entry_context", "invalidation requires a non-bear classification at entry", SOURCE_NEW_PARAMETER,
                        "Rulebook v1.2 section 20 line 1757 ('a separately persisted lifecycle context / invalidation input')",
                        "Setup C has no regime gate, so without it a long opened in a bear band would be force-exited at its next evaluation, adding round trips."),
            ),
            helpers=(H_REGIME_CLASSIFICATION, H_REGIME_SMOOTHING),
            point_in_time="The smoothed regime score at t and the persisted ledger classification at entry.",
            missing_input=(
                "None gives EXIT_INPUT_MISSING with complete False; STRUCTURAL_STOP, HOLD_SCORE_COLLAPSE and the other "
                "exit reasons still evaluate (exit_rules.py:401-451), and the engine still enforces the standing stop. "
                "Never filled: an incomplete K_t or a missing K_entry is never replaced by False or True."
            ),
            warm_up=WarmUp(WARMUP_INHERITS, ("CORE_REGIME_SCORE",), "as the core regime score"),
            accounted_causes=_causes("REGIME_INVALIDATION_PREDICATE", "INPUT_MISSING"),
            notes=(
                "Section 6A.5 is not monotone for an exit: fewer forced exits means fewer round trips, earlier exits "
                "mean less exposure. Mild Bear is the first bearish band, strictly below every long regime gate (55, 65), "
                "so it cannot cause exit/re-entry churn at a gate, and it matches the mirrored short premise "
                "setup_requirements.bearish_distribution.regime_max = 45 (default.toml:95). Surfaced for review.",
                "It is disjoint from REGIME_SUPPORTIVE_PREDICATE (>= 65): no instant is both supportive and invalidated.",
                "A position entered in a bear band (most plausibly Setup C) is exempt from REGIME_INVALIDATION for its life, "
                "even if the regime deteriorates further; structural stop and Hold exits still apply. Alternative surfaced: "
                "True iff K_t is bear and strictly below K_entry in the owner's label order.",
            ),
        ),
        SpecEntry(
            input_id="DATA_RISK_EXIT_PREDICATE",
            inventory_kind="OWNERLESS_UNDEFINED",
            disposition=DISPOSITION_DEFINED,
            consumers=(
                Consumer("btc_predictor.signals.exit_rules.ExitRuleInput.data_risk_exit_required", "btc_predictor/signals/exit_rules.py:98 ExitRuleInput.data_risk_exit_required"),
                Consumer("btc_predictor.signals.exit_rules.exit_rules_for_position.data_risk_exit_required", "btc_predictor/signals/exit_rules.py:239 exit_rules_for_position parameter data_risk_exit_required"),
            ),
            rule=(
                "False at every exit evaluation. The Rulebook's only data-quality rule, DATA_QUALITY_FAIL, has exactly two "
                "effects, NO NEW TRADES and NO NEW ADDS, which apply_data_quality_gate already enforces; the gate's "
                "reason codes are passed to exit_rules_for_position as source evidence only."
            ),
            elements=(
                Element("value", "False", SOURCE_RULEBOOK,
                        "Rulebook v1.2 section 24 lines 2023-2031 (DATA_QUALITY_FAIL: NO NEW TRADES / NO NEW ADDS, no exit "
                        "effect); no 'data risk' exit anywhere in the Rulebook"),
                Element("owner_convention", "ordinary DATA_QUALITY_FAIL is not a forced liquidation", SOURCE_OWNER_CONVENTION,
                        "btc_predictor/signals/exit_rules.py:8-11; btc_predictor/signals/data_quality.py:98 apply_data_quality_gate"),
            ),
            helpers=(Helper("btc_predictor.signals.data_quality.apply_data_quality_gate", "evidence only; blocks ENTER and ADD", CENSUS_ROOT),),
            point_in_time="Not applicable: a constant Rulebook ruling, not a measurement.",
            missing_input="Never None, so EXIT_INPUT_MISSING never arises from this field; it is a defined ruling, not a fill of a missing measurement.",
            warm_up=WarmUp(WARMUP_NONE, (), "none: a constant"),
            notes=(
                "A data-driven exit would contradict the explicit Rulebook effect list and BTC-158; section 6A.5 is not "
                "reached because the Rulebook is explicit.",
            ),
        ),
        SpecEntry(
            input_id="CORRECTION_FROM_LOCAL_HIGH",
            inventory_kind="OWNERLESS_UNDEFINED",
            disposition=DISPOSITION_DEFINED,
            consumers=(Consumer("btc_predictor.features.setup.BullishResetInput.correction_from_local_high_fraction", "btc_predictor/features/setup.py:208 BullishResetInput.correction_from_local_high_fraction"),),
            rule=(
                "-D, where D is the last element of fifty_two_week_high_distance_from_weekly_bars over the canonical weekly "
                "bars visible at t, i.e. (H_52W - P) / H_52W >= 0 with P the close of the last completed weekly bar "
                "visible at t. The detector applies the config band [0.08, 0.25] unchanged."
            ),
            elements=(
                Element("owner_output", "HIGH_DISTANCE_52W with its sign flipped", SOURCE_OWNER_CONVENTION,
                        "btc_predictor/features/trend.py:209 fifty_two_week_high_distance_from_weekly_bars; Rulebook v1.2 "
                        "section 5.1 lines 461-469"),
                Element("local_high", "the trailing 52-week high", SOURCE_NEW_PARAMETER,
                        "Rulebook v1.2 section 11 lines 1264, 1271-1279, 1289 ('local high', no lookback)",
                        "The only owner high with a defined lookback; it needs no further choice and is never below that weekly close, and a swing-high reading would need three more new parameters."),
                Element("band", "0.08 <= correction <= 0.25", SOURCE_CONFIG,
                        "btc_predictor/config/strategy/default.toml:75-76; Rulebook v1.2 section 11 line 1289"),
            ),
            helpers=(Helper("btc_predictor.features.trend.fifty_two_week_high_distance_from_weekly_bars", "D at the latest visible weekly bar", CENSUS_ROOT), H_BARS),
            point_in_time=_BAR_PIT,
            missing_input="D None (fewer than 52 visible weekly rows) gives None: BULLISH_RESET_INPUT_MISSING, Setup B not matched (fail closed). Never zero-filled.",
            warm_up=WarmUp(WARMUP_INHERITS, ("HIGH_DISTANCE_52W",), "as HIGH_DISTANCE_52W"),
            accounted_causes=_causes("CORRECTION_FROM_LOCAL_HIGH", "INPUT_MISSING"),
            notes=(
                "The Rulebook says 'local high' (section 11), '52-week high' (5.1) and 'prior local swing high' (15) in "
                "different places; reading 'local' as the trailing 52 weeks is an interpretation, surfaced for review. "
                "No volatility normalisation (Rulebook 1279 defers it).",
                "Weekly resolution: the correction can lag the daily price by up to one week, and a price above H_52W "
                "inside the current week is not seen.",
            ),
        ),
        SpecEntry(
            input_id="DISTRIBUTION_STATE",
            inventory_kind="OWNERLESS_UNDEFINED",
            disposition=DISPOSITION_INERT,
            consumers=(Consumer("btc_predictor.features.setup.BearishDistributionInput.distribution_flagged", "btc_predictor/features/setup.py:316 BearishDistributionInput.distribution_flagged"),),
            rule="Inert short-side input: distribution_flagged=None at every decision instant; detect_bearish_distribution is still called.",
            elements=(
                Element("ruling", "INERT", _P,
                        "policy V6 section 6A.6 (long-only; short-only inputs stay inert and are listed); "
                        "btc_predictor/config/strategy/default.toml:283 allow_short_trades = false",
                        "Setup D is short-only and the engine refuses short intents, so no value is defined; None keeps the owner's incomplete result standing."),
            ),
            helpers=(Helper("btc_predictor.features.setup.detect_bearish_distribution", "called for archetype coverage; never matches", CENSUS_ROOT),),
            point_in_time="Not applicable.",
            missing_input="BEARISH_DISTRIBUTION_INPUT_MISSING with detected False (fail closed); the guard attributes it per field to INERT_SHORT_SIDE. Never filled with True or False.",
            warm_up=WarmUp(WARMUP_NONE, (), "none: inert"),
            accounted_causes=("INERT_SHORT_SIDE",),
            notes=(
                "Rulebook 23 lists 'Euphoria / distribution' as a long-side reduce reason; no long-side owner consumes a "
                "distribution state, so that reason is unmodelled beyond Flow and Hold (limitation).",
            ),
        ),
        SpecEntry(
            input_id="SHORT_TRIGGER",
            inventory_kind="OWNERLESS_UNDEFINED",
            disposition=DISPOSITION_INERT,
            consumers=(Consumer("btc_predictor.features.setup.BearishDistributionInput.short_trigger_confirmed", "btc_predictor/features/setup.py:317 BearishDistributionInput.short_trigger_confirmed"),),
            rule="Inert short-side input: short_trigger_confirmed=None at every decision instant.",
            elements=(
                Element("ruling", "INERT", _P,
                        "policy V6 section 6A.6; btc_predictor/config/strategy/default.toml:283 allow_short_trades = false; "
                        "Rulebook v1.2 section 12 (long-only triggers)",
                        "Defining a mirrored trigger would be a new indicator (section 6A.4) for a direction the engine refuses."),
            ),
            helpers=(),
            point_in_time="Not applicable.",
            missing_input="BEARISH_DISTRIBUTION_INPUT_MISSING with detected False (fail closed); attributed to INERT_SHORT_SIDE. Never filled with True or False.",
            warm_up=WarmUp(WARMUP_NONE, (), "none: inert"),
            accounted_causes=("INERT_SHORT_SIDE",),
        ),
        SpecEntry(
            input_id="MEASURED_MOVE_REFERENCE",
            inventory_kind="OWNERLESS_UNDEFINED",
            disposition=DISPOSITION_OMITTED,
            consumers=(Consumer("btc_predictor.risk.reward.reward_risk_for_stop.measured_move", "btc_predictor/risk/reward.py:395 reward_risk_for_stop parameter measured_move"),),
            rule="Explicitly omitted: reward_risk_for_stop is called with measured_move=None (its default); reward tiers 1-3 evaluate unchanged.",
            elements=(
                Element("ruling", "OMITTED", _P,
                        "RBT-002A acceptance criteria ('explicit omission is a ruling'); Rulebook v1.2 section 15 lines "
                        "1520-1529 (tier 4 named without geometry); btc_predictor/risk/reward.py:78-83, :252-267",
                        "Tier 4 is consulted only when tiers 1-3 have no credible reference, so omitting it can only turn a pass into REWARD_RISK_NO_REWARD_REFERENCE: it provably trades less."),
            ),
            helpers=(Helper("btc_predictor.risk.reward.reward_risk_for_stop", "R/R filter with tiers 1-3", CENSUS_ROOT),),
            point_in_time="Not applicable.",
            missing_input=(
                "With no credible tier 1-3 reference the filter fails with REWARD_RISK_NO_REWARD_REFERENCE (complete, "
                "passes False), as Rulebook 15 line 1529 prescribes; a setup given that result's None reward_risk as "
                "its risk_reward records *_INPUT_MISSING, which the guard maps to the complete R/R verdict. Never filled: no "
                "measured move is invented."
            ),
            warm_up=WarmUp(WARMUP_NONE, (), "none: omitted"),
            accounted_causes=("REWARD_RISK_NO_REWARD_REFERENCE",),
            notes=("default.toml:138 still lists 'conservative_setup_measured_move'; the owner never reads that key, and config is not edited.",),
        ),
    )


def spec_entries() -> tuple[SpecEntry, ...]:
    """The 26 covered inputs, sorted by input id."""

    entries = (
        *_trend_and_flow_entries(),
        *_volatility_entries(),
        *_structure_entries(),
        *_lifecycle_entries(),
        *_exit_setup_entries(),
    )
    return tuple(sorted(entries, key=lambda entry: entry.input_id))


# --- E1: the futures-basis zero-variance guard RBT-004 must implement -------------------------------


@dataclass(frozen=True)
class GuardContract:
    """A contract the spec binds on a later composer ticket; this spec implements nothing."""

    guard_id: str
    implemented_by: str
    limitation: str
    history_helpers: tuple[Helper, ...]
    clauses: tuple[tuple[str, str], ...]
    required_tests: tuple[str, ...]
    prohibited: tuple[str, ...]
    citations: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        return {
            "guard_id": self.guard_id,
            "implemented_by": self.implemented_by,
            "limitation": self.limitation,
            "history_helpers": [item.as_record() for item in self.history_helpers],
            "clauses": {name: text for name, text in self.clauses},
            "required_tests": list(self.required_tests),
            "prohibited": list(self.prohibited),
            "citations": list(self.citations),
        }


E1_GUARD = GuardContract(
    guard_id="FUTURES_BASIS_ZERO_VARIANCE_GUARD_V1",
    implemented_by="RBT-004 (COMPOSE_CHAMPION_ENTRY_DECISION_V1)",
    limitation=(
        "Named limitation E1: the frozen futures_basis_health owner averages with Decimal sum and division at the "
        "default 28-digit context (positioning.py:1340 _average), so an exactly constant history of a non-terminating "
        "annualized basis leaves a nonzero computed variance and _zscore's 'volatility == 0' refusal (positioning.py:"
        "1266) never fires: the owner returns a complete result (z = 1, health 83.527... in the RBT-002 re-review "
        "fixture) where it promises FUTURES_BASIS_ZERO_VARIANCE. The strict XFAIL "
        "test_research_backtest_coverage_rereview.py::test_nonterminating_constant_basis_refuses_zero_variance pins it. "
        "Disclosure alone does not authorise accepting the false score."
    ),
    history_helpers=(
        Helper("btc_predictor.features.positioning.futures_basis_health", "R = the owner result at t (owner defaults)", CENSUS_ROOT),
        Helper(
            "btc_predictor.features.positioning._futures_basis_averages_by_time",
            "A = the owner's per-observation_time averages of the visible rows",
            PROMOTE_TO_CENSUS_ROOT,
        ),
        Helper(
            "btc_predictor.features.positioning._futures_basis_history",
            "H = the owner's prior annualized-basis history over [R.observation_time - 180 days, R.observation_time)",
            PROMOTE_TO_CENSUS_ROOT,
        ),
    ),
    clauses=(
        ("1_owner_result", "At each decision instant t, R = futures_basis_health(rows, as_of=t) with the owner's defaults."),
        ("2_owner_refusal_stands", "If R.annualized_basis_zscore is None, R stands unchanged (INPUT_MISSING, INSUFFICIENT_HISTORY or the owner's own ZERO_VARIANCE) and the guard does nothing; the guard never relabels an owner refusal."),
        ("3_visible_rows", "rows_t = the replay basis rows with available_at <= t and observation_time <= t: the owner's own inline predicate (positioning.py:568-573), applied identically by the composer."),
        ("4_history", "A = _futures_basis_averages_by_time(rows_t); H = _futures_basis_history(A, observation_time=R.observation_time, zscore_window_days=R.zscore_window_days). The composer asserts len(H) == R.history_observation_count and max(A) == R.observation_time; a mismatch is a composer defect and fails its test."),
        ("5_equality", "If every element of H is exactly equal under Decimal == (all(h == H[0] for h in H)), the guard refuses. This holds whether or not the current value R.annualized_basis_rate_avg equals H[0]."),
        ("6_refusal", "On refusal: record FUTURES_BASIS_ZERO_VARIANCE with R as evidence, and pass no health score and no z-score anywhere: PositioningScoreInput.basis_health, CrowdingFlagInput.basis_zscore, StressFlagInput.basis_zscore and EuphoriaFlagInput.basis_zscore all receive None."),
        ("7_structural_unevaluability", "Positioning is recorded as STRUCTURALLY_UNEVALUABLE at t with cause FUTURES_BASIS_ZERO_VARIANCE, an accounted cause under policy V6 section 5A.6; the incomplete Entry Conviction, regime, CROWDING (SEVERE_CROWDING_STATE None, so the hard veto fails closed) and, while a position is open, Hold and Add map to it. StressFlagInput.basis_zscore and EuphoriaFlagInput.basis_zscore None are attributed per field to the same cause: STRESS then reads stress_flagged=None (STRESS_NON_DISCRETIONARY_MISSING), and EUPHORIA's basis leg cannot fire (fewer NO ADD suppressions, disclosed)."),
        ("8_pass_through", "Otherwise R.health_score and R.annualized_basis_zscore pass unchanged; the guard's only numeric operation is the equality test."),
        ("9_census", "_futures_basis_averages_by_time and _futures_basis_history are promoted to classified census roots before RBT-004 calls them (policy V6 sections 5A.6, 6A.9)."),
    ),
    required_tests=(
        "a constant history refuses FUTURES_BASIS_ZERO_VARIANCE and passes no health or z to any of the four consumers",
        "a current value equal to the constant history refuses",
        "a current value different from the constant history refuses",
        "point-in-time exclusion: a row with available_at > t or observation_time > t never joins H",
        "non-constant histories give results identical to the owner's",
    ),
    prohibited=(
        "reimplementing the mean, variance or z-score",
        "substituting zero or any placeholder value",
        "a near-equality tolerance (it would change non-constant results)",
        "editing btc_predictor/features/positioning.py without a separate cross-workstream decision",
    ),
    citations=(
        "policy V6 section 6A.9",
        "btc_predictor/features/positioning.py:551 futures_basis_health, :1111 _futures_basis_averages_by_time, :1130 _futures_basis_history, :1260 _zscore, :1340 _average",
        "docs/execution/research_backtest_track_v1.md RBT-002 re-review finding E1",
    ),
)


# --- declared arithmetic, limitations and the pre-registration record -------------------------------

# Policy V6 section 6A.7: the composers implement the spec by calling owner
# helpers. This is the complete list of arithmetic the spec declares on top of
# owner calls; RBT-004/RBT-005's "no new formulas" admits exactly these.
DECLARED_ARITHMETIC = (
    "select a quantity's history by observation-time window [D - 730 days, D) and skip None values (uniform rules)",
    "exact equality of every history value (uniform z-score refusal; E1 guard)",
    "TR(d) / close(d - 1 day) (RANGE_PERCENTILE)",
    "negation of the HIGH_DISTANCE_52W value (CORRECTION_FROM_LOCAL_HIGH)",
    "(c - p) / p for a swing low and (p - c) / p for a swing high (LEVEL_REACTION_MAGNITUDE)",
    "sum of Bitstamp 1h volume over the L hours [d - L, d) (LEVEL_VOLUME_PERCENTILE)",
    "minimum over a cluster's in-scope members (LEVEL_REACTION_MAGNITUDE, LEVEL_VOLUME_PERCENTILE)",
    "membership of an owner classification label in a listed band (regime predicates)",
    "decision_greater_equal(FlowScore, 60), the Rulebook 6.2 Supportive band floor (FLOW_SUPPORTIVE_PREDICATE)",
    "timestamp comparison against the last accepted ENTER/ADD transition (NEW_STRUCTURAL_CONFIRMATION)",
)

NAMED_LIMITATIONS = (
    ("E1_FUTURES_BASIS_ZERO_VARIANCE", "Frozen owner defect; refused by the RBT-004 guard FUTURES_BASIS_ZERO_VARIANCE_GUARD_V1."),
    ("E1_CLASS_FUNDING_AND_OI_GROWTH", "funding_health (positioning.py:516) and open_interest_growth_health (positioning.py:694) call the same Decimal _zscore/_average; an exactly constant non-terminating 180-day history would give the same false-complete z. Policy V6 section 6A.9 authorises a guard for futures basis only; this spec neither extends nor ignores it. Open owner question."),
    ("MOMENTUM_PERSISTENCE_OVERLAP", "Z_M12 reaches Hold through Trend and directly (see MOMENTUM_PERSISTENCE_SCORE); explicit, quantified and versioned here, not validated by ablation. Open owner question."),
    ("REACTION_UNIT", "Rulebook 9.2 measures reaction relative to ATR; the frozen strength owner takes a price fraction (full score 0.10). The spec feeds the owner's unit."),
    ("LEVEL_STRENGTH_OWNER_TABLES", "The frozen strength owner's timeframe table and linear touch score differ from Rulebook 9.2; unchanged."),
    ("FLOW_OWNER_BANDS", "The flow owner's interpretation labels (80/65/45/30) differ from Rulebook 6.2 (75/60/45/30); FLOW_SUPPORTIVE_PREDICATE reads the score, not the label."),
    ("ROW_BASED_LOOKBACKS", "Momentum, MA-distance, 52-week-high and R_7 owners count rows, so an omitted bar is read as contiguous (analogous to the policy V6 section 7 limitations). Obligation: RBT-006/RBT-007 report, per venue, the count of decision instants at which such a lookback spans an omitted bar."),
    ("SEVERE_CROWDING_IS_CROWDING", "Every CROWDING instant vetoes a new trade (policy V6 section 6A.5), so the CROWDING entry-quality penalty never acts on a new trade."),
    ("LEVEL_VOLUME_PRE_WARM_UP_PIVOTS", "A swing member whose pivot bar closes before the computed volume warm-up date never gets a percentile; under the strict minimum a cluster containing one stays incomplete."),
    ("STRESS_NON_DISCRETIONARY_MISSING", "The V4 STRESS mapping covers only a DISCRETIONARY-only missing input; when a spec input (DOWNSIDE_RETURN) or an E1 refusal leaves STRESS incomplete, the conservative composer reading is stress_flagged=None (hard veto fails closed). RBT-004 must state it."),
    ("UNMODELLED_ADD_AND_REDUCE_RULES", "Rulebook 21 line 1823 'hold quality', 7.5 'PositioningScore >= 70 to add' and 23 'distribution' as a reduce reason have no owner consumer and no inventory input; outside this spec, flagged for RBT-005."),
    ("LEVEL_FAMILIES_NOT_RULED", "If RBT-004 clusters volume-profile or AVWAP members, a nearest support cluster holding only such members has no swing member, so both level inputs are None and Structure is incomplete (NO_SWING_MEMBER). The family choice is RBT-004's; surfaced."),
    ("ONE_ADD_PER_STRUCTURE", "A confirmed higher low the trail accepts at an instant where another add requirement fails is consumed by that STOP_MOVE and cannot confirm a later add."),
)

SURFACED_FOR_REVIEW = (
    "MOMENTUM_PERSISTENCE_SCORE overlap with Trend (Rulebook 4.1/32.17): accept as explicit/quantified/versioned with validation deferred to SENSITIVITY_ONLY_NOT_SELECTION reporting, or choose a new persistence indicator, or leave Hold incomplete (owner decision; a closure precondition for RBT-002A).",
    "E1-class risk in funding_health and open_interest_growth_health: extend the section 6A.9 guard or record as a named limitation only (owner decision).",
    "UNIFORM_ZSCORE_V1 window: 730 days with 30 observations; the positioning 180 days cannot hold 30 weekly observations and the flow owner's 20-observation count window was rejected (recent change, cadence-dependent horizon, earlier start).",
    "DOWNSIDE_RETURN/UPSIDE_RETURN horizon of 7 daily bars versus 1: section 6A.5 is not monotone across consumers (CAPITULATION enables Setup C).",
    "RANGE_PERCENTILE quantity: true range over the prior close (scale-free) rather than raw price-unit true range; neither is owner-fixed and section 6A.5 is not monotone.",
    "REGIME_INVALIDATION_PREDICATE band: Mild Bear or below with a non-bear entry context; bear-entered positions are exempt for life; alternative: bear and strictly below the entry label.",
    "CORRECTION_FROM_LOCAL_HIGH: 'local high' read as the trailing 52-week high, at weekly resolution.",
    "Level families clustered by RBT-004: volume-profile or AVWAP-only support clusters make both level inputs None (NO_SWING_MEMBER).",
    "NEW_STRUCTURAL_CONFIRMATION depends on RBT-005's trailing-structure producer, shared with the trail; one add instant per structure.",
)

PRE_REGISTRATION = {
    "data_consulted": [
        f"the reviewed RBT-002 inventory {BOUND_INVENTORY_FILENAME} ({BOUND_INVENTORY_SHA256}): its coverage snapshot "
        "(per-venue missing-hour runs, first and last instants), the selected sources' measured depth and cadence, "
        "the earliest-evaluable facts, the input-surface rows and the census roots",
        "owner source code, strategy configuration (btc_predictor/config/strategy/default.toml), Rulebook v1.2, "
        "policy V6 and the EPIC Y track document",
        "synthetic fixtures in the tests only",
    ],
    "database_connected": False,
    "market_values_read": False,
    "scores_signals_trades_or_performance_computed": False,
    "holdout": "NOT COLLECTED",
    "btc019_sealed_sample": "UNOPENED",
}


# --- computed warm-up ------------------------------------------------------------------------------

# Numbers the warm-up simulation applies, each read from its owner (the uniform
# z-score window takes the volatility owner's 730 days as its NEW_PARAMETER).
UNIFORM_ZSCORE_WINDOW_DAYS = volatility_owner.DEFAULT_VOLATILITY_PERCENTILE_WINDOW_DAYS
UNIFORM_ZSCORE_MIN_OBSERVATIONS = positioning_owner.DEFAULT_FUNDING_MIN_ZSCORE_OBSERVATIONS
UNIFORM_PERCENTILE_WINDOW_DAYS = volatility_owner.DEFAULT_VOLATILITY_PERCENTILE_WINDOW_DAYS
UNIFORM_PERCENTILE_MIN_OBSERVATIONS = volatility_owner.DEFAULT_VOLATILITY_PERCENTILE_MIN_OBSERVATIONS
RETURN_HORIZON_DAILY_BARS = 7
SWING_RIGHT_BARS = {
    "1w": swing_owner.DEFAULT_WEEKLY_SWING_RIGHT_BARS,
    "1mo": swing_owner.DEFAULT_MONTHLY_SWING_RIGHT_BARS,
}
_RULE_PARAMETERS = {
    _Z_RULE: (UNIFORM_ZSCORE_WINDOW_DAYS, UNIFORM_ZSCORE_MIN_OBSERVATIONS),
    _PCT_RULE: (UNIFORM_PERCENTILE_WINDOW_DAYS, UNIFORM_PERCENTILE_MIN_OBSERVATIONS),
}
DAILY_TRUE_RANGE_FRACTION = "DAILY_TRUE_RANGE_FRACTION"
DAILY_RETURN_7 = "DAILY_RETURN_7"
COMPONENT_INPUTS = (
    ("trend", "TREND_SCORE"),
    ("flow", "FLOW_SCORE"),
    ("positioning", "POSITIONING_SCORE"),
    ("volatility", "VOLATILITY_SCORE"),
    ("structure", "STRUCTURE_SCORE"),
)
STATUS_NO_WARM_UP = "NO_WARM_UP"
STATUS_DATA_DEPENDENT_LOWER_BOUND = "DATA_DEPENDENT_LOWER_BOUND"


def _custom_series(name: str, series: Mapping[str, coverage.ObservationSeries]) -> coverage.ObservationSeries:
    daily = series[coverage.SERIES_DAILY]
    observations = daily.observations
    if name == DAILY_TRUE_RANGE_FRACTION:
        # TR / previous close needs the adjacent preceding daily bar (true_ranges is None after a gap).
        kept = tuple(
            observations[index]
            for index in range(1, len(observations))
            if observations[index][0] - observations[index - 1][0] == timedelta(days=1)
        )
    elif name == DAILY_RETURN_7:
        kept = observations[RETURN_HORIZON_DAILY_BARS:]
    else:
        raise CompletionSpecError("UNKNOWN_CUSTOM_SERIES", name)
    return coverage.ObservationSeries(name, kept, daily.basis, daily.source)


def _upstream_series(
    name: str,
    requirements: Mapping[str, coverage.HistoryRequirement],
    series: Mapping[str, coverage.ObservationSeries],
    computed: Mapping[str, coverage.ObservationSeries | None],
) -> coverage.ObservationSeries | None:
    if name in (DAILY_TRUE_RANGE_FRACTION, DAILY_RETURN_7):
        return _custom_series(name, series)
    if name in computed:
        return computed[name]
    return inventory_input_series(name, requirements, series)


def _midnights(start: datetime, end: datetime) -> Iterable[datetime]:
    current = datetime(start.year, start.month, start.day, tzinfo=UTC)
    if current < start:
        current += timedelta(days=1)
    while current < end:
        yield current
        current += timedelta(days=1)


def level_volume_warm_up(snapshot: Mapping[str, Any], series: Mapping[str, coverage.ObservationSeries]) -> dict[str, Any]:
    """The first pivot bar, per source timeframe, whose Bitstamp volume sum has
    365 defined same-length daily comparators in its prior 730 days, and the
    earliest instant a swing member on that bar can be detected (its last
    confirming bar's close). Computed from the inventory's Bitstamp coverage."""

    import bisect

    venue = SHARED_VOLUME_VENUE
    missing = sorted(coverage.rebuild_missing_hours(snapshot, exchange=venue.exchange, symbol=venue.symbol, provider=venue.provider))
    data_start = coverage._DATA_START
    data_end = coverage._HOLDOUT_START

    def defined(close: datetime, length: timedelta) -> bool:
        start = close - length
        if start < data_start or close > data_end:
            return False
        position = bisect.bisect_left(missing, start)
        return position == len(missing) or missing[position] >= close

    window = timedelta(days=UNIFORM_PERCENTILE_WINDOW_DAYS)
    result: dict[str, Any] = {}
    for timeframe, series_name in (("1w", coverage.SERIES_WEEKLY), ("1mo", coverage.SERIES_MONTHLY)):
        bars = series[series_name].observations
        found = None
        for index, (start, close) in enumerate(bars):
            length = close - start
            if not defined(close, length):
                continue
            count = sum(1 for day in _midnights(close - window, close) if defined(day, length))
            if count >= UNIFORM_PERCENTILE_MIN_OBSERVATIONS:
                found = (index, start, close, count)
                break
        if found is None:
            result[timeframe] = {"status": coverage.STATUS_INSUFFICIENT}
            continue
        index, start, close, count = found
        confirm = index + SWING_RIGHT_BARS[timeframe]
        detection = bars[confirm][1] if confirm < len(bars) else None
        result[timeframe] = {
            "status": coverage.STATUS_EVALUABLE,
            "first_pivot_bar_start": coverage._iso(start),
            "first_pivot_bar_close": coverage._iso(close),
            "comparators_at_first_pivot": count,
            "earliest_member_detection": coverage._iso(detection),
            "right_bars": SWING_RIGHT_BARS[timeframe],
        }
    return result


def _record(result: coverage.EarliestEvaluable | None, status: str | None = None) -> dict[str, Any]:
    if result is None:
        return {"status": status or STATUS_NO_WARM_UP}
    return result.as_record()


def _series_first(name: str, observations: coverage.ObservationSeries | None) -> coverage.EarliestEvaluable:
    first = _first(observations)
    if first is None:
        return coverage.EarliestEvaluable(name, coverage.STATUS_NO_OBSERVATIONS)
    return coverage.EarliestEvaluable(name, coverage.STATUS_EVALUABLE, first[0], first[1], observations.basis)  # type: ignore[union-attr]


def _require_primitives_reproduce_inventory(
    inventory: Mapping[str, Any],
    venue_id: str,
    requirements: Mapping[str, coverage.HistoryRequirement],
    series: Mapping[str, coverage.ObservationSeries],
) -> None:
    """Every date the bound inventory records as evaluable must be reproduced by
    the simulation primitives, or the warm-up is refused (the coverage constants
    the inventory digest does not bind cannot drift silently)."""

    for input_id, expected in inventory["earliest_evaluable"]["venues"][venue_id]["inputs"].items():
        if expected["status"] != coverage.STATUS_EVALUABLE:
            continue
        first = _first(inventory_input_series(input_id, requirements, series))
        if first is None or coverage._iso(first[1]) != expected["available_at"]:
            raise CompletionSpecError("WARMUP_PRIMITIVES_DRIFT", f"{venue_id} {input_id}: {first} != {expected['available_at']}")


def compute_warm_up(entries: Sequence[SpecEntry], inventory: Mapping[str, Any]) -> dict[str, Any]:
    """Per venue: each entry's earliest availability and the effect on the
    earliest instant every Entry Conviction component and the core regime are
    complete, from the inventory's coverage facts only (no outcome)."""

    snapshot = inventory["database_coverage"]
    requirements_list = coverage.minimum_history_requirements()
    requirements = {item.input_id: item for item in requirements_list}
    covered = {entry.input_id for entry in entries}
    graph = [item for item in requirements_list if item.input_id not in covered]
    by_venue: dict[str, Any] = {}
    for venue in REPLAY_VENUES:
        series = venue_series(snapshot, venue)
        _require_primitives_reproduce_inventory(inventory, venue.venue_id, requirements, series)
        computed: dict[str, coverage.ObservationSeries | None] = {}
        volume = level_volume_warm_up(snapshot, series)
        pending = list(entries)
        while pending:
            progressed = False
            for entry in list(pending):
                kind = entry.warm_up.kind
                upstream = entry.warm_up.upstream
                if kind == WARMUP_NONE:
                    computed[entry.input_id] = None
                elif kind == WARMUP_LEVEL_VOLUME:
                    detection = volume["1w"].get("earliest_member_detection")
                    start = volume["1w"].get("first_pivot_bar_start")
                    computed[entry.input_id] = (
                        coverage.ObservationSeries(
                            entry.input_id,
                            ((datetime.fromisoformat(start), datetime.fromisoformat(detection)),),
                            coverage.BASIS_MEASURED,
                            "Bitstamp shared 1h volume coverage and the venue's weekly bars",
                        )
                        if detection
                        else None
                    )
                elif any(name in covered and name not in computed for name in upstream):
                    continue
                elif any(name in ("CORE_REGIME_SCORE", "FLOW_SCORE", "STRUCTURE_SCORE") for name in upstream):
                    continue  # resolved from the completed graph below
                elif kind == WARMUP_UNIFORM_RULE:
                    window_days, minimum = _RULE_PARAMETERS[entry.warm_up.rule_id or ""]
                    base = _upstream_series(upstream[0], requirements, series, computed)
                    computed[entry.input_id] = (
                        trailing_window_series(entry.input_id, base, window=timedelta(days=window_days), min_prior=minimum)
                        if base is not None
                        else None
                    )
                elif kind == WARMUP_INHERITS:
                    members = [_upstream_series(name, requirements, series, computed) for name in upstream]
                    computed[entry.input_id] = (
                        None if any(member is None for member in members) else _all_of_series(entry.input_id, members)  # type: ignore[arg-type]
                    )
                pending.remove(entry)
                progressed = True
            if not progressed:
                break
        merged = {**series, **{key: value for key, value in computed.items() if value is not None}}
        results = coverage.earliest_evaluable_inputs(graph, merged)
        components = {component: results[name].as_record() for component, name in COMPONENT_INPUTS}
        combined = coverage._all_of("ENTRY_CONVICTION_AND_CORE_REGIME", [results["ENTRY_CONVICTION"], results["CORE_REGIME_SCORE"]])
        inventory_bound = inventory["earliest_evaluable"]["venues"][venue.venue_id]["every_component_and_core_regime"]
        def lower_bound(record: dict[str, Any]) -> dict[str, Any]:
            # Only an evaluable date becomes a data-dependent lower bound; a
            # failure status is never relabelled.
            if record["status"] == coverage.STATUS_EVALUABLE:
                return {**record, "status": STATUS_DATA_DEPENDENT_LOWER_BOUND}
            return record

        graph_inputs = {item.input_id for item in requirements_list if item.rule in (coverage.RULE_UNDEFINED, coverage.RULE_UNIMPLEMENTED_FALLBACK)}
        combined_at = combined.available_at.isoformat() if combined.available_at else None
        entry_records = {}
        binding_entries = []
        for entry in entries:
            if entry.warm_up.kind == WARMUP_NONE:
                record = {"input_id": entry.input_id, "status": STATUS_NO_WARM_UP}
            elif entry.input_id in computed:
                record = _series_first(entry.input_id, computed[entry.input_id]).as_record()
                if entry.warm_up.kind == WARMUP_LEVEL_VOLUME:
                    record = {**lower_bound(record), "by_source_timeframe": volume}
            else:
                upstream = entry.warm_up.upstream[0]
                record = {**results[upstream].as_record(), "input_id": entry.input_id, "via": upstream}
                if upstream == "STRUCTURE_SCORE":
                    record = lower_bound(record)
            binds = entry.input_id in graph_inputs and record.get("available_at") is not None and record["available_at"] == combined_at
            if binds:
                binding_entries.append(entry.input_id)
            entry_records[entry.input_id] = {**record, "binds_earliest_evaluable": binds}
        components["structure"] = lower_bound(components["structure"])
        lower_bound_due_to = ["structure"] if components["structure"]["status"] == STATUS_DATA_DEPENDENT_LOWER_BOUND else []
        entry_conviction = results["ENTRY_CONVICTION"].as_record()
        combined_record = combined.as_record()
        if lower_bound_due_to:
            entry_conviction = {**lower_bound(entry_conviction), "lower_bound_due_to": lower_bound_due_to}
            combined_record = {**lower_bound(combined_record), "lower_bound_due_to": lower_bound_due_to}
        by_venue[venue.venue_id] = {
            "entries": dict(sorted(entry_records.items())),
            "binding_entries": sorted(binding_entries),
            "entry_conviction_components": components,
            "core_regime": results["CORE_REGIME_SCORE"].as_record(),
            "entry_conviction": entry_conviction,
            "every_component_and_core_regime": combined_record,
            "inventory_lower_bound_available_at": inventory_bound["lower_bound_available_at"],
            "inventory_status": inventory_bound["status"],
        }
    return {
        "data_dependent": (
            "LEVEL_VOLUME_PERCENTILE, and through it STRUCTURE_SCORE and NEW_STRUCTURE_SCORE, report a lower bound: "
            "whether the cluster selected at an instant holds a member whose pivot bar precedes the volume warm-up "
            "depends on prices, which this pre-registration does not read"
        ),
        "rule": "input availability only, from the bound inventory's coverage facts; no score, signal, trade or outcome",
        "basis": "venue bars measured from the inventory snapshot; shared series projected from the selected sources' depth (RBT-002)",
        "by_venue": by_venue,
    }


# --- the frozen definition ---------------------------------------------------------------------


def _all_helpers(entries: Sequence[SpecEntry]) -> list[Helper]:
    helpers = [helper for rule in UNIFORM_RULES for helper in rule.helpers]
    helpers += [helper for entry in entries for helper in entry.helpers]
    helpers += list(E1_GUARD.history_helpers)
    return helpers


def helper_census(entries: Sequence[SpecEntry]) -> dict[str, list[str]]:
    """Every helper symbol by census status. A symbol must not carry two statuses."""

    statuses: dict[str, set[str]] = {}
    for helper in _all_helpers(entries):
        statuses.setdefault(helper.symbol, set()).add(helper.census)
    conflicts = sorted(symbol for symbol, found in statuses.items() if len(found) > 1)
    if conflicts:
        raise CompletionSpecError("HELPER_STATUS_CONFLICT", ", ".join(conflicts))
    grouped: dict[str, list[str]] = {status: [] for status in HELPER_CENSUS_STATUSES}
    for symbol, found in sorted(statuses.items()):
        grouped[next(iter(found))].append(symbol)
    return grouped


def _earliest_effect(warm_up: Mapping[str, Any]) -> dict[str, Any]:
    effect = {}
    for venue_id, facts in warm_up["by_venue"].items():
        combined = facts["every_component_and_core_regime"]
        bound = facts["inventory_lower_bound_available_at"]
        binding = sorted(
            component
            for component, record in facts["entry_conviction_components"].items()
            if record["available_at"] == combined["available_at"]
        )
        if facts["core_regime"]["available_at"] == combined["available_at"]:
            binding.append("core_regime")
        moved = None
        if combined["available_at"] and bound:
            moved = (datetime.fromisoformat(combined["available_at"]) - datetime.fromisoformat(bound)).days
        effect[venue_id] = {
            "inventory_lower_bound_available_at": bound,
            "spec_completed_status": combined["status"],
            "spec_completed_available_at": combined["available_at"],
            "lower_bound_due_to": combined.get("lower_bound_due_to", []),
            "days_later_than_inventory_lower_bound": moved,
            "binding_components": binding,
            "binding_entries": facts["binding_entries"],
        }
    return effect


def spec_definition() -> dict[str, Any]:
    """The complete typed definition as one canonical record.

    Refuses unless the bound inventory has the bound digest and every owner-less
    inventory input is covered exactly once.
    """

    inventory = bound_inventory()
    entries = spec_entries()
    check_coverage(entries, inventory)
    if inventory["inventory_version"] != BOUND_INVENTORY_VERSION:
        raise CompletionSpecError("INVENTORY_VERSION_MISMATCH", inventory["inventory_version"])
    warm_up = compute_warm_up(entries, inventory)
    census = helper_census(entries)
    entry_records = [entry.as_record() for entry in entries]
    new_parameters = [
        {"input_id": record["input_id"], "name": element["name"], "value": element["value"], "rationale": element["rationale"], "citation": element["citation"]}
        for record in entry_records
        for element in record["elements"]
        if element["source_class"] == SOURCE_NEW_PARAMETER and element["name"] != "normalisation"
    ] + [
        {"input_id": rule.rule_id, "name": element.name, "value": element.value, "rationale": element.rationale, "citation": element.citation}
        for rule in UNIFORM_RULES
        for element in rule.elements
        if element.source_class == SOURCE_NEW_PARAMETER
    ]
    return {
        "spec_version": SPEC_VERSION,
        "ticket": SPEC_TICKET,
        "policy": SPEC_POLICY_VERSION,
        "policy_document": SPEC_POLICY_DOCUMENT,
        "research_strategy_id": RESEARCH_STRATEGY_ID,
        "champion_base_identity": dict(CHAMPION_BASE_IDENTITY),
        "scope": SPEC_SCOPE,
        "excluded_uses": list(SPEC_EXCLUDED_USES),
        "evidence_class": RESEARCH_EVIDENCE_CLASS,
        "canonical_reference": CANONICAL_REFERENCE_UNRESOLVED,
        "bound_inventory": {
            "inventory_version": BOUND_INVENTORY_VERSION,
            "filename": BOUND_INVENTORY_FILENAME,
            "sha256": BOUND_INVENTORY_SHA256,
            "reviewed_under_policy": inventory["policy"],
        },
        "coverage": {
            "covered_inventory_kinds": list(COVERED_INVENTORY_KINDS),
            "excluded_ownerless": {key: {"kind": kind, "reason": reason} for key, (kind, reason) in sorted(EXCLUDED_OWNERLESS.items())},
            "covered_input_count": len(entries),
            "by_disposition": {item: sorted(e.input_id for e in entries if e.disposition == item) for item in DISPOSITIONS},
            "by_source_class": {
                item: sorted(e.input_id for e in entries if e.source_class == item)
                for item in (*SOURCE_CLASSES, SOURCE_POLICY_RULING)
            },
        },
        "source_class_precedence": list(SOURCE_CLASSES),
        "uniform_rules": [rule.as_record() for rule in UNIFORM_RULES],
        "entries": entry_records,
        "new_parameters": new_parameters,
        "e1_guard": E1_GUARD.as_record(),
        "declared_arithmetic": list(DECLARED_ARITHMETIC),
        "helpers_by_census_status": census,
        "composer_roots_to_promote": census[PROMOTE_TO_CENSUS_ROOT],
        "named_limitations": [{"limitation_id": key, "statement": text} for key, text in NAMED_LIMITATIONS],
        "surfaced_for_review": list(SURFACED_FOR_REVIEW),
        "pre_registration": dict(PRE_REGISTRATION),
        "warm_up": warm_up,
        "earliest_evaluable_effect": _earliest_effect(warm_up),
    }


def spec_bytes() -> bytes:
    """The canonical sorted JSON of the definition: the hashed form."""

    return canonical_json_bytes(spec_definition())


def spec_sha256() -> str:
    return sha256_hex(spec_bytes())


def write_spec(output_dir: Path = ARTIFACT_DIRECTORY) -> dict[str, Path]:
    data = spec_bytes()
    digest = sha256_hex(data)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {"spec": output_dir / SPEC_FILENAME, "digest": output_dir / SPEC_DIGEST_FILENAME}
    paths["spec"].write_bytes(data)
    paths["digest"].write_text(f"{digest}  {SPEC_FILENAME}\n", encoding="ascii")
    return paths


def verify_persisted(directory: Path = ARTIFACT_DIRECTORY) -> str:
    """Rebuild the definition and require the persisted bytes and digest to match."""

    data = spec_bytes()
    digest = sha256_hex(data)
    persisted = (directory / SPEC_FILENAME).read_bytes()
    if persisted != data:
        raise CompletionSpecError("PERSISTED_SPEC_DIFFERS", f"{SPEC_FILENAME} does not rebuild byte for byte")
    recorded = (directory / SPEC_DIGEST_FILENAME).read_text(encoding="ascii")
    if recorded != f"{digest}  {SPEC_FILENAME}\n":
        raise CompletionSpecError("PERSISTED_DIGEST_DIFFERS", f"{SPEC_DIGEST_FILENAME} does not match {digest}")
    return digest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=SPEC_VERSION)
    commands = parser.add_subparsers(dest="command", required=True)
    write = commands.add_parser("write", help="build the definition and persist it with its digest")
    write.add_argument("--output-dir", type=Path, default=ARTIFACT_DIRECTORY)
    verify = commands.add_parser("verify", help="rebuild and compare with the persisted definition")
    verify.add_argument("--directory", type=Path, default=ARTIFACT_DIRECTORY)
    commands.add_parser("digest", help="print the definition's SHA-256")
    args = parser.parse_args(argv)
    if args.command == "write":
        for name, path in sorted(write_spec(args.output_dir).items()):
            print(f"{name}: {path}")
    elif args.command == "verify":
        print(verify_persisted(args.directory))
    else:
        print(spec_sha256())
    return 0


if __name__ == "__main__":  # pragma: no cover - command line entry point
    sys.exit(main())
