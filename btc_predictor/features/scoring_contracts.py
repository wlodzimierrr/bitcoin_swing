"""Declarative v1.2 scoring dependency graph and factor-overlap audit.

BTC-129 locks the Phase 1 score dependency graph *before* Entry Conviction and
the lifecycle scores are implemented, so that a later implementation cannot
reintroduce the mechanical factor nesting that v1.1 carried.

The audit here is purely **structural**: it inspects the declared dependency
graph and reports when one leaf factor reaches a composite through more than
one path. That is mechanical double-counting and is prohibited.

It says nothing whatsoever about **empirical correlation**. Trend and Flow are
naturally correlated in real markets, and that is expected and permitted; two
components may move together without either being arithmetically embedded in
the other. Only the graph relationship is governed here. See
``MECHANICAL_VS_EMPIRICAL_NOTE``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Context, Decimal, localcontext
from typing import Any


SCORING_CONTRACTS_VERSION = "SCORING_CONTRACTS_V1_2"
RETIRED_SCORING_CONTRACTS_VERSION = "SCORING_CONTRACTS_V1_1"

MECHANICAL_VS_EMPIRICAL_NOTE = (
    "This audit detects mechanical (structural) double-counting only: one leaf "
    "factor reaching a composite through more than one declared path. Natural "
    "empirical correlation between distinct components is expected, is not a "
    "defect, and is deliberately out of scope here."
)

# Node roles.
ROLE_COMPOSITE = "COMPOSITE"
ROLE_FACTOR = "FACTOR"
ROLE_CONTEXT_GATE = "CONTEXT_GATE"
ROLE_INDEPENDENT_FILTER = "INDEPENDENT_FILTER"
ROLE_DIAGNOSTIC = "DIAGNOSTIC"
SCORING_NODE_ROLES = (
    ROLE_COMPOSITE,
    ROLE_FACTOR,
    ROLE_CONTEXT_GATE,
    ROLE_INDEPENDENT_FILTER,
    ROLE_DIAGNOSTIC,
)

# --- v1.2 canonical weighted contracts -----------------------------------
# Entry/Hold/Add thresholds and weights remain PROVISIONAL pending BTC-185
# parameter-robustness research. They are starting values, not validated
# constants.
SCORING_PARAMETER_STATUS = "PROVISIONAL_PENDING_BTC_185"

ENTRY_CONVICTION_WEIGHTS_V1_2 = {
    "trend": Decimal("0.25"),
    "flow": Decimal("0.25"),
    "positioning": Decimal("0.1875"),
    "volatility": Decimal("0.125"),
    "structure": Decimal("0.1875"),
}
HOLD_SCORE_WEIGHTS_V1_2 = {
    "trend": Decimal("0.2666667"),
    "flow": Decimal("0.2666667"),
    "positioning": Decimal("0.20"),
    "structure": Decimal("0.1333333"),
    "momentum_persistence": Decimal("0.1333333"),
}
ADD_SCORE_WEIGHTS_V1_2 = {
    "new_structure": Decimal("0.3125"),
    "flow": Decimal("0.25"),
    "positioning": Decimal("0.1875"),
    "momentum": Decimal("0.125"),
    "risk_improvement": Decimal("0.125"),
}
STRUCTURE_WEIGHTS_V1_2 = {
    "level_strength": Decimal("0.642857"),
    "entry_location": Decimal("0.357143"),
}

# --- retired v1.1 contracts, kept only as an analytical benchmark ---------
ENTRY_CONVICTION_WEIGHTS_V1_1 = {
    "trend": Decimal("0.20"),
    "regime": Decimal("0.20"),
    "flow": Decimal("0.20"),
    "positioning": Decimal("0.15"),
    "volatility": Decimal("0.10"),
    "structure": Decimal("0.15"),
}
HOLD_SCORE_WEIGHTS_V1_1 = {
    "regime": Decimal("0.25"),
    "trend": Decimal("0.20"),
    "flow": Decimal("0.20"),
    "positioning": Decimal("0.15"),
    "structure": Decimal("0.10"),
    "momentum_persistence": Decimal("0.10"),
}
ADD_SCORE_WEIGHTS_V1_1 = {
    "hold_score": Decimal("0.20"),
    "new_structure": Decimal("0.25"),
    "flow": Decimal("0.20"),
    "positioning": Decimal("0.15"),
    "momentum": Decimal("0.10"),
    "risk_improvement": Decimal("0.10"),
}
STRUCTURE_WEIGHTS_V1_1 = {
    "level_strength": Decimal("0.45"),
    "entry_location": Decimal("0.25"),
    "rr_quality": Decimal("0.20"),
    "confluence": Decimal("0.10"),
}
# Regime is a weighted composite over the very factors Entry and Hold already
# score directly. Nesting it is precisely the v1.1 double-count v1.2 removes.
CORE_REGIME_WEIGHTS = {
    "trend": Decimal("0.45"),
    "flow": Decimal("0.25"),
    "volatility": Decimal("0.15"),
    "positioning": Decimal("0.15"),
}

SCORING_GRAPH_V1_2: dict[str, dict[str, Decimal]] = {
    "entry_conviction": ENTRY_CONVICTION_WEIGHTS_V1_2,
    "hold_score": HOLD_SCORE_WEIGHTS_V1_2,
    "add_score": ADD_SCORE_WEIGHTS_V1_2,
    "structure": STRUCTURE_WEIGHTS_V1_2,
    "regime": CORE_REGIME_WEIGHTS,
}
SCORING_GRAPH_V1_1: dict[str, dict[str, Decimal]] = {
    "entry_conviction": ENTRY_CONVICTION_WEIGHTS_V1_1,
    "hold_score": HOLD_SCORE_WEIGHTS_V1_1,
    "add_score": ADD_SCORE_WEIGHTS_V1_1,
    "structure": STRUCTURE_WEIGHTS_V1_1,
    "regime": CORE_REGIME_WEIGHTS,
}

# Nodes that must never appear as a weighted component of another score.
SCORING_NODE_ROLES_V1_2 = {
    "regime": ROLE_CONTEXT_GATE,
    "rr_quality": ROLE_INDEPENDENT_FILTER,
    "confluence": ROLE_DIAGNOSTIC,
    "hold_score": ROLE_COMPOSITE,
}
PROHIBITED_NESTING_V1_2 = (
    ("entry_conviction", "regime", "Regime is a setup/context gate, and its own components are already scored directly by Entry Conviction."),
    ("hold_score", "regime", "Regime is separate context and invalidation logic, not a Hold Score component."),
    ("add_score", "hold_score", "Add Score must be an independent judgement, not a re-weighting of Hold Score."),
    ("structure", "rr_quality", "R/R is an independent hard asymmetry filter, not a Structure contribution."),
    ("structure", "confluence", "Confluence is already represented inside LevelStrength."),
)


@dataclass(frozen=True)
class FactorPath:
    """One route from a composite down to a leaf factor."""

    leaf: str
    path: tuple[str, ...]
    weight: Decimal

    def as_record(self) -> dict[str, Any]:
        return {
            "leaf": self.leaf,
            "path": list(self.path),
            "weight": str(self.weight),
        }


@dataclass(frozen=True)
class FactorOverlapFinding:
    composite: str
    leaf: str
    paths: tuple[FactorPath, ...]

    def as_record(self) -> dict[str, Any]:
        return {
            "composite": self.composite,
            "leaf": self.leaf,
            "path_count": len(self.paths),
            "paths": [item.as_record() for item in self.paths],
        }


@dataclass(frozen=True)
class FactorOverlapAudit:
    contracts_version: str
    composite: str
    effective_weights: dict[str, Decimal]
    effective_weight_total: Decimal
    findings: tuple[FactorOverlapFinding, ...]
    prohibited_nesting: tuple[tuple[str, str], ...]

    @property
    def mechanically_clean(self) -> bool:
        return not self.findings and not self.prohibited_nesting

    def as_record(self) -> dict[str, Any]:
        return {
            "contracts_version": self.contracts_version,
            "composite": self.composite,
            "effective_weights": {
                key: str(value) for key, value in self.effective_weights.items()
            },
            "effective_weight_total": str(self.effective_weight_total),
            "mechanically_clean": self.mechanically_clean,
            "findings": [item.as_record() for item in self.findings],
            "prohibited_nesting": [list(item) for item in self.prohibited_nesting],
            "mechanical_vs_empirical": MECHANICAL_VS_EMPIRICAL_NOTE,
        }


# Path weights are products of the declared graph weights.  They are
# computed in an explicit context so the analytical decomposition BTC-189
# persists and BTC-193 replays does not depend on the caller's ambient
# decimal context.  Every value is already exact at this precision.
SCORING_DECIMAL_PRECISION = 60


def _declared_total(weights: Mapping[str, Decimal]) -> Decimal:
    with localcontext(Context(prec=SCORING_DECIMAL_PRECISION)):
        return sum(weights.values(), Decimal("0"))


def expand_factor_paths(
    composite: str,
    graph: Mapping[str, Mapping[str, Decimal]],
) -> tuple[FactorPath, ...]:
    """Expand a composite into every weighted route down to a leaf factor."""

    if composite not in graph:
        raise ValueError(f"unknown composite: {composite}")

    paths: list[FactorPath] = []

    def walk(node: str, prefix: tuple[str, ...], weight: Decimal) -> None:
        if node in prefix:
            raise ValueError(
                f"scoring graph contains a cycle through {node!r}: {prefix}",
            )
        components = graph.get(node)
        if not components:
            paths.append(FactorPath(leaf=node, path=prefix, weight=weight))
            return
        for name, component_weight in components.items():
            walk(name, (*prefix, node), weight * component_weight)

    with localcontext(Context(prec=SCORING_DECIMAL_PRECISION)):
        for name, component_weight in graph[composite].items():
            walk(name, (composite,), component_weight)
    return tuple(paths)


def effective_weights(
    composite: str,
    graph: Mapping[str, Mapping[str, Decimal]],
) -> dict[str, Decimal]:
    """Sum every path weight per leaf factor, fully expanding nested scores."""

    totals: dict[str, Decimal] = {}
    paths = expand_factor_paths(composite, graph)
    with localcontext(Context(prec=SCORING_DECIMAL_PRECISION)):
        for item in paths:
            totals[item.leaf] = totals.get(item.leaf, Decimal("0")) + item.weight
    return totals


def audit_factor_overlap(
    composite: str,
    graph: Mapping[str, Mapping[str, Decimal]] = SCORING_GRAPH_V1_2,
    *,
    contracts_version: str = SCORING_CONTRACTS_VERSION,
    prohibited: Sequence[tuple[str, str, str]] = PROHIBITED_NESTING_V1_2,
) -> FactorOverlapAudit:
    """Report mechanical factor double-counting for one composite score."""

    paths = expand_factor_paths(composite, graph)
    by_leaf: dict[str, list[FactorPath]] = {}
    for item in paths:
        by_leaf.setdefault(item.leaf, []).append(item)
    findings = tuple(
        FactorOverlapFinding(
            composite=composite,
            leaf=leaf,
            paths=tuple(items),
        )
        for leaf, items in sorted(by_leaf.items())
        if len(items) > 1
    )
    reachable = {node for item in paths for node in item.path} | {
        item.leaf for item in paths
    }
    violations = tuple(
        (parent, child)
        for parent, child, _ in prohibited
        if parent in reachable and child in graph.get(parent, {})
    )
    totals = effective_weights(composite, graph)
    with localcontext(Context(prec=SCORING_DECIMAL_PRECISION)):
        total = sum(totals.values(), Decimal("0"))
    return FactorOverlapAudit(
        contracts_version=contracts_version,
        composite=composite,
        effective_weights=totals,
        effective_weight_total=total,
        findings=findings,
        prohibited_nesting=violations,
    )


def effective_weight_report() -> dict[str, Any]:
    """Analytical v1.1 vs v1.2 effective-weight comparison for the record."""

    report: dict[str, Any] = {
        "contracts_version": SCORING_CONTRACTS_VERSION,
        "retired_contracts_version": RETIRED_SCORING_CONTRACTS_VERSION,
        "parameter_status": SCORING_PARAMETER_STATUS,
        "mechanical_vs_empirical": MECHANICAL_VS_EMPIRICAL_NOTE,
        "composites": {},
    }
    for composite in ("entry_conviction", "hold_score", "add_score"):
        retired = audit_factor_overlap(
            composite,
            SCORING_GRAPH_V1_1,
            contracts_version=RETIRED_SCORING_CONTRACTS_VERSION,
        )
        current = audit_factor_overlap(composite, SCORING_GRAPH_V1_2)
        report["composites"][composite] = {
            "v1_1_declared_weights": {
                key: str(value)
                for key, value in SCORING_GRAPH_V1_1[composite].items()
            },
            "v1_1_effective_weights": {
                key: str(value) for key, value in retired.effective_weights.items()
            },
            "v1_1_mechanically_clean": retired.mechanically_clean,
            "v1_1_overlapping_leaves": [item.leaf for item in retired.findings],
            "v1_2_declared_weights": {
                key: str(value)
                for key, value in SCORING_GRAPH_V1_2[composite].items()
            },
            "v1_2_declared_weight_total": str(
                _declared_total(SCORING_GRAPH_V1_2[composite]),
            ),
            "v1_2_effective_weights": {
                key: str(value) for key, value in current.effective_weights.items()
            },
            "v1_2_mechanically_clean": current.mechanically_clean,
        }
    return report
