"""BTC-129: v1.2 de-nested scoring contract lock and factor-overlap audit."""

from decimal import Decimal

import pytest

from btc_predictor.config.strategy import (
    ADD_SCORE_CONTRACT_VERSION,
    DEFAULT_STRATEGY_CONFIG_PATH,
    ENTRY_CONVICTION_CONTRACT_VERSION,
    HOLD_SCORE_CONTRACT_VERSION,
    PROHIBITED_NESTED_WEIGHT_COMPONENTS,
    SCORING_COMPONENT_SETS,
    STRUCTURE_SCORE_CONTRACT_VERSION,
    StrategyConfigError,
    load_strategy_config,
)
from btc_predictor.features.scoring_contracts import (
    ADD_SCORE_WEIGHTS_V1_2,
    ENTRY_CONVICTION_WEIGHTS_V1_2,
    HOLD_SCORE_WEIGHTS_V1_2,
    MECHANICAL_VS_EMPIRICAL_NOTE,
    PROHIBITED_NESTING_V1_2,
    SCORING_CONTRACTS_VERSION,
    SCORING_GRAPH_V1_1,
    SCORING_GRAPH_V1_2,
    SCORING_PARAMETER_STATUS,
    STRUCTURE_WEIGHTS_V1_2,
    audit_factor_overlap,
    effective_weight_report,
    effective_weights,
    expand_factor_paths,
)


# --- declared v1.2 contracts --------------------------------------------


def test_v1_2_declared_contracts_are_exact_and_sum_to_one() -> None:
    assert SCORING_CONTRACTS_VERSION == "SCORING_CONTRACTS_V1_2"
    assert ENTRY_CONVICTION_WEIGHTS_V1_2 == {
        "trend": Decimal("0.25"),
        "flow": Decimal("0.25"),
        "positioning": Decimal("0.1875"),
        "volatility": Decimal("0.125"),
        "structure": Decimal("0.1875"),
    }
    assert HOLD_SCORE_WEIGHTS_V1_2 == {
        "trend": Decimal("0.2666667"),
        "flow": Decimal("0.2666667"),
        "positioning": Decimal("0.20"),
        "structure": Decimal("0.1333333"),
        "momentum_persistence": Decimal("0.1333333"),
    }
    assert ADD_SCORE_WEIGHTS_V1_2 == {
        "new_structure": Decimal("0.3125"),
        "flow": Decimal("0.25"),
        "positioning": Decimal("0.1875"),
        "momentum": Decimal("0.125"),
        "risk_improvement": Decimal("0.125"),
    }
    for weights in (
        ENTRY_CONVICTION_WEIGHTS_V1_2,
        HOLD_SCORE_WEIGHTS_V1_2,
        ADD_SCORE_WEIGHTS_V1_2,
        STRUCTURE_WEIGHTS_V1_2,
    ):
        assert sum(weights.values(), Decimal("0")) == Decimal("1")


def test_thresholds_and_weights_are_marked_provisional() -> None:
    assert SCORING_PARAMETER_STATUS == "PROVISIONAL_PENDING_BTC_185"


# --- mechanical overlap absence -----------------------------------------


@pytest.mark.parametrize(
    "composite", ["entry_conviction", "hold_score", "add_score", "structure"]
)
def test_v1_2_composites_have_no_mechanical_factor_overlap(composite: str) -> None:
    audit = audit_factor_overlap(composite, SCORING_GRAPH_V1_2)

    assert audit.findings == ()
    assert audit.prohibited_nesting == ()
    assert audit.mechanically_clean is True


def test_regime_is_not_reachable_from_entry_or_hold() -> None:
    for composite in ("entry_conviction", "hold_score"):
        nodes = {
            node
            for item in expand_factor_paths(composite, SCORING_GRAPH_V1_2)
            for node in (*item.path, item.leaf)
        }
        assert "regime" not in nodes


def test_hold_score_is_not_nested_into_add_score() -> None:
    nodes = {
        node
        for item in expand_factor_paths("add_score", SCORING_GRAPH_V1_2)
        for node in (*item.path, item.leaf)
    }

    assert "hold_score" not in nodes
    assert "momentum_persistence" not in nodes


def test_rr_and_confluence_are_not_structure_contributions() -> None:
    leaves = set(effective_weights("structure", SCORING_GRAPH_V1_2))

    assert leaves == {"level_strength", "entry_location"}
    assert "rr_quality" not in leaves
    assert "confluence" not in leaves


def test_each_v1_2_leaf_is_reached_by_exactly_one_path() -> None:
    for composite in ("entry_conviction", "hold_score", "add_score"):
        paths = expand_factor_paths(composite, SCORING_GRAPH_V1_2)
        leaves = [item.leaf for item in paths]
        assert len(leaves) == len(set(leaves)), composite


# --- retired v1.1 benchmark ---------------------------------------------


def test_v1_1_entry_effective_weights_are_reported_for_benchmark() -> None:
    audit = audit_factor_overlap("entry_conviction", SCORING_GRAPH_V1_1)

    # Trend reaches Entry both directly (0.20) and through Regime
    # (0.20 * 0.45 = 0.09), for an effective 0.29 against a declared 0.20.
    assert audit.effective_weights["trend"] == Decimal("0.2900")
    assert audit.effective_weights["flow"] == Decimal("0.2500")
    assert audit.effective_weights["positioning"] == Decimal("0.1800")
    assert audit.effective_weights["volatility"] == Decimal("0.1300")
    assert audit.effective_weight_total == Decimal("1.0000")
    assert audit.mechanically_clean is False
    assert {item.leaf for item in audit.findings} == {
        "trend",
        "flow",
        "positioning",
        "volatility",
    }


def test_v1_1_hold_and_add_overlap_is_reported() -> None:
    hold = audit_factor_overlap("hold_score", SCORING_GRAPH_V1_1)
    add = audit_factor_overlap("add_score", SCORING_GRAPH_V1_1)

    # Hold: 0.20 direct + 0.25 * 0.45 through Regime.
    assert hold.effective_weights["trend"] == Decimal("0.3125")
    assert hold.mechanically_clean is False
    # Add: trend leaks in only through the nested Hold Score.
    assert add.effective_weights["trend"] == Decimal("0.062500")
    assert add.mechanically_clean is False
    assert "hold_score" in {node for item in
                            expand_factor_paths("add_score", SCORING_GRAPH_V1_1)
                            for node in item.path}


def test_effective_weight_report_covers_both_architectures() -> None:
    report = effective_weight_report()

    assert set(report["composites"]) == {
        "entry_conviction",
        "hold_score",
        "add_score",
    }
    for block in report["composites"].values():
        assert block["v1_1_mechanically_clean"] is False
        assert block["v1_2_mechanically_clean"] is True
        assert block["v1_2_declared_weight_total"].startswith("1.0")
    assert report["parameter_status"] == "PROVISIONAL_PENDING_BTC_185"
    assert "empirical" in report["mechanical_vs_empirical"]


def test_audit_distinguishes_mechanical_nesting_from_empirical_correlation() -> None:
    """Two separately declared components are clean however correlated."""

    graph = {
        "demo": {"trend": Decimal("0.5"), "flow": Decimal("0.5")},
    }
    audit = audit_factor_overlap("demo", graph)

    # Trend and Flow are empirically correlated in real markets; that is not
    # a mechanical double-count and must not be reported as one.
    assert audit.mechanically_clean is True
    assert "empirical" in MECHANICAL_VS_EMPIRICAL_NOTE


def test_audit_detects_a_reintroduced_nesting() -> None:
    graph = dict(SCORING_GRAPH_V1_2)
    graph["entry_conviction"] = {
        **ENTRY_CONVICTION_WEIGHTS_V1_2,
        "regime": Decimal("0.0"),
    }
    audit = audit_factor_overlap("entry_conviction", graph)

    assert audit.mechanically_clean is False
    assert ("entry_conviction", "regime") in audit.prohibited_nesting


def test_cycles_in_the_graph_are_rejected() -> None:
    graph = {
        "a": {"b": Decimal("1")},
        "b": {"a": Decimal("1")},
    }
    with pytest.raises(ValueError, match="cycle"):
        expand_factor_paths("a", graph)


def test_an_unknown_composite_is_rejected_rather_than_returning_no_paths() -> None:
    with pytest.raises(ValueError, match="unknown composite: sentiment"):
        expand_factor_paths("sentiment", SCORING_GRAPH_V1_2)
    with pytest.raises(ValueError, match="unknown composite: sentiment"):
        effective_weights("sentiment", SCORING_GRAPH_V1_2)
    with pytest.raises(ValueError, match="unknown composite: sentiment"):
        audit_factor_overlap("sentiment")


# --- config enforcement --------------------------------------------------


def test_default_config_declares_the_v1_2_contracts() -> None:
    config = load_strategy_config()

    assert config.identity.config_version == "strategy_config_v2"
    assert config.identity.strategy_version == "swing_v1.2"
    assert "regime" not in config.scoring_weights.entry_conviction
    assert "regime" not in config.scoring_weights.hold_score
    assert "hold_score" not in config.scoring_weights.add_score
    assert set(config.scoring_weights.structure_score) == {
        "level_strength",
        "entry_location",
    }


@pytest.mark.parametrize(
    ("section", "nested", "line"),
    [
        ("entry_conviction", "regime", "trend = 0.25"),
        ("hold_score", "regime", "trend = 0.2666667"),
        ("add_score", "hold_score", "new_structure = 0.3125"),
    ],
)
def test_config_rejects_prohibited_nested_components(
    tmp_path,
    section: str,
    nested: str,
    line: str,
) -> None:
    text = DEFAULT_STRATEGY_CONFIG_PATH.read_text(encoding="utf-8")
    marker = f"[scoring_weights.{section}]\n{line}"
    assert marker in text
    broken = text.replace(marker, f"{marker}\n{nested} = 0.0", 1)
    config_path = tmp_path / f"nested_{section}.toml"
    config_path.write_text(broken, encoding="utf-8")

    with pytest.raises(StrategyConfigError, match=f"must not nest '{nested}'"):
        load_strategy_config(config_path)


def test_config_rejects_reintroduced_structure_rr_and_confluence(tmp_path) -> None:
    text = DEFAULT_STRATEGY_CONFIG_PATH.read_text(encoding="utf-8")
    broken = text.replace(
        "[scoring_weights.structure_score]\nlevel_strength = 0.642857",
        "[scoring_weights.structure_score]\nrr_quality = 0.0\nlevel_strength = 0.642857",
        1,
    )
    config_path = tmp_path / "nested_structure.toml"
    config_path.write_text(broken, encoding="utf-8")

    with pytest.raises(StrategyConfigError, match="must not nest 'rr_quality'"):
        load_strategy_config(config_path)


def test_prohibited_nesting_tables_agree_between_config_and_contracts() -> None:
    """The config guard and the analytical contract must not drift apart."""

    contract_edges = {(parent, child) for parent, child, _ in PROHIBITED_NESTING_V1_2}
    config_edges = {
        ("structure" if section == "structure_score" else section, nested)
        for section, nested_map in PROHIBITED_NESTED_WEIGHT_COMPONENTS.items()
        for nested in nested_map
    }

    assert contract_edges == config_edges


# --- version-keyed exact component-set validation ------------------------

V1_2_SECTIONS = {
    "entry_conviction": (
        ENTRY_CONVICTION_CONTRACT_VERSION,
        """[scoring_weights.entry_conviction]
trend = 0.25
flow = 0.25
positioning = 0.1875
volatility = 0.125
structure = 0.1875""",
    ),
    "hold_score": (
        HOLD_SCORE_CONTRACT_VERSION,
        """[scoring_weights.hold_score]
trend = 0.2666667
flow = 0.2666667
positioning = 0.20
structure = 0.1333333
momentum_persistence = 0.1333333""",
    ),
    "add_score": (
        ADD_SCORE_CONTRACT_VERSION,
        """[scoring_weights.add_score]
new_structure = 0.3125
flow = 0.25
positioning = 0.1875
momentum = 0.125
risk_improvement = 0.125""",
    ),
    "structure_score": (
        STRUCTURE_SCORE_CONTRACT_VERSION,
        """[scoring_weights.structure_score]
level_strength = 0.642857
entry_location = 0.357143""",
    ),
}


def _config_with(tmp_path, section: str, replacement: str, name: str):
    """Rewrite one scoring_weights section of the default config."""

    text = DEFAULT_STRATEGY_CONFIG_PATH.read_text(encoding="utf-8")
    original = V1_2_SECTIONS[section][1]
    assert original in text, section
    path = tmp_path / f"{name}_{section}.toml"
    path.write_text(text.replace(original, replacement, 1), encoding="utf-8")
    return path


def test_component_sets_are_bound_to_a_named_contract_version() -> None:
    assert ENTRY_CONVICTION_CONTRACT_VERSION == "ENTRY_CONVICTION_V1_2"
    assert HOLD_SCORE_CONTRACT_VERSION == "HOLD_SCORE_V1_2"
    assert ADD_SCORE_CONTRACT_VERSION == "ADD_SCORE_V1_2"
    assert STRUCTURE_SCORE_CONTRACT_VERSION == "STRUCTURE_SCORE_V1_2"
    assert set(SCORING_COMPONENT_SETS) == {
        "entry_conviction",
        "hold_score",
        "add_score",
        "structure_score",
    }


def test_config_component_sets_match_the_authoritative_contracts() -> None:
    """The config key tuples and the analytical contracts must not drift."""

    assert set(SCORING_COMPONENT_SETS["entry_conviction"][1]) == set(
        ENTRY_CONVICTION_WEIGHTS_V1_2,
    )
    assert set(SCORING_COMPONENT_SETS["hold_score"][1]) == set(
        HOLD_SCORE_WEIGHTS_V1_2,
    )
    assert set(SCORING_COMPONENT_SETS["add_score"][1]) == set(ADD_SCORE_WEIGHTS_V1_2)
    assert set(SCORING_COMPONENT_SETS["structure_score"][1]) == set(
        STRUCTURE_WEIGHTS_V1_2,
    )


def test_default_config_weights_match_the_authoritative_contracts() -> None:
    """Independent config and analytical weight definitions must not drift."""

    config = load_strategy_config()
    expected = {
        "entry_conviction": ENTRY_CONVICTION_WEIGHTS_V1_2,
        "hold_score": HOLD_SCORE_WEIGHTS_V1_2,
        "add_score": ADD_SCORE_WEIGHTS_V1_2,
        "structure_score": STRUCTURE_WEIGHTS_V1_2,
    }

    for section, contract_weights in expected.items():
        configured = getattr(config.scoring_weights, section)
        assert {
            name: Decimal(str(weight)) for name, weight in configured.items()
        } == contract_weights


@pytest.mark.parametrize("section", sorted(V1_2_SECTIONS))
def test_accepts_exactly_the_authoritative_v1_2_component_set(
    tmp_path,
    section: str,
) -> None:
    version, block = V1_2_SECTIONS[section]
    config = load_strategy_config(_config_with(tmp_path, section, block, "exact"))
    weights = getattr(config.scoring_weights, section)

    assert set(weights) == set(SCORING_COMPONENT_SETS[section][1])
    assert abs(sum(weights.values()) - 1.0) <= 1e-6
    assert SCORING_COMPONENT_SETS[section][0] == version


@pytest.mark.parametrize("section", sorted(V1_2_SECTIONS))
def test_rejects_missing_required_component(tmp_path, section: str) -> None:
    version, block = V1_2_SECTIONS[section]
    lines = block.splitlines()
    # Drop the final component and give its weight to the first one so the
    # sum still reaches 1.0 and only the missing key can be the failure.
    dropped_name, dropped_weight = lines[-1].split(" = ")
    first_name, first_weight = lines[1].split(" = ")
    lines[1] = f"{first_name} = {float(first_weight) + float(dropped_weight)}"
    broken = "\n".join(lines[:-1])
    path = _config_with(tmp_path, section, broken, "missing")

    with pytest.raises(StrategyConfigError, match="must exactly match") as excinfo:
        load_strategy_config(path)
    assert version in str(excinfo.value)
    assert dropped_name in str(excinfo.value)


@pytest.mark.parametrize("section", sorted(V1_2_SECTIONS))
def test_rejects_unexpected_additional_component(tmp_path, section: str) -> None:
    version, block = V1_2_SECTIONS[section]
    path = _config_with(
        tmp_path,
        section,
        f"{block}\nsentiment = 0.0",
        "extra",
    )

    with pytest.raises(StrategyConfigError, match="must exactly match") as excinfo:
        load_strategy_config(path)
    assert version in str(excinfo.value)
    assert "sentiment" in str(excinfo.value)


@pytest.mark.parametrize(
    ("section", "retired"),
    [
        ("entry_conviction", "regime"),
        ("hold_score", "regime"),
        ("add_score", "hold_score"),
        ("structure_score", "rr_quality"),
        ("structure_score", "confluence"),
    ],
)
def test_rejects_retired_nested_component(
    tmp_path,
    section: str,
    retired: str,
) -> None:
    _, block = V1_2_SECTIONS[section]
    path = _config_with(
        tmp_path,
        section,
        f"{block}\n{retired} = 0.0",
        "retired",
    )

    # The nesting prohibition must win over the generic key error, so the
    # author is told *why* the component is gone.
    with pytest.raises(
        StrategyConfigError,
        match=f"must not nest '{retired}'",
    ):
        load_strategy_config(path)


@pytest.mark.parametrize("section", sorted(V1_2_SECTIONS))
def test_rejects_correct_names_with_invalid_weight_sum(
    tmp_path,
    section: str,
) -> None:
    version, block = V1_2_SECTIONS[section]
    lines = block.splitlines()
    name, weight = lines[1].split(" = ")
    lines[1] = f"{name} = {float(weight) + 0.05}"
    path = _config_with(tmp_path, section, "\n".join(lines), "sum")

    with pytest.raises(StrategyConfigError, match="must sum to 1.0") as excinfo:
        load_strategy_config(path)
    assert version in str(excinfo.value)
