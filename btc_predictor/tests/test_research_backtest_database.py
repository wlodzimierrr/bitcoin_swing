"""EPIC Y database environment and BTC-019 isolation (policy V6 section 9).

These tests pin:

- ``research_backtest.database.database_url_from_environment``: the same five
  ``POSTGRES_*`` names and URL form as before, ``quote_plus`` for user and
  password, and a missing-variable error that names variables, never values;
- the isolation rule: no module under ``btc_predictor/research_backtest/``
  imports a BTC-019 research-only module, at module level or inside a
  function, in any import form, including an ``importlib`` string import.

``test_btc019_completion_gate.py`` is not edited; this module is stricter than
its source scan (it also catches ``from btc_predictor.research import ...``
and every alias of a multi-name ``import``). Nothing here touches a database.
"""

from __future__ import annotations

import ast
from importlib.util import resolve_name
from pathlib import Path
from urllib.parse import quote_plus

import pytest

from btc_predictor.research_backtest import database
from btc_predictor.research_backtest.database import (
    DATABASE_ENVIRONMENT_NAMES,
    DatabaseEnvironmentError,
    database_url_from_environment,
)


ROOT = Path(__file__).resolve().parents[2]
RESEARCH_BACKTEST = ROOT / "btc_predictor" / "research_backtest"
RESEARCH_BACKTEST_PACKAGE = "btc_predictor.research_backtest"

# The research-only modules guarded by
# test_btc019_completion_gate.py::test_no_production_module_reads_a_research_reference_candidate.
BTC019_RESEARCH_ONLY = (
    "reference_composite",
    "btc019_empirical",
    "btc019b_diagnostics",
    "price_source_policy",
    "btc019_completion_gate",
)
_DYNAMIC_IMPORTERS = frozenset({"import_module", "__import__", "find_spec", "spec_from_file_location"})

_VALUES = {
    "POSTGRES_USER": "rbt user@x",
    "POSTGRES_PASSWORD": "p@ss:w/rd%#&= +",
    "POSTGRES_HOST": "db.example.invalid",
    "POSTGRES_PORT": "6543",
    "POSTGRES_DB": "btc-swing",
}


def _set_environment(monkeypatch: pytest.MonkeyPatch, values: dict[str, str]) -> None:
    for name in DATABASE_ENVIRONMENT_NAMES:
        monkeypatch.delenv(name, raising=False)
    for name, value in values.items():
        monkeypatch.setenv(name, value)


# --- the helper --------------------------------------------------------------------------


def test_the_helper_reads_the_same_five_names() -> None:
    assert DATABASE_ENVIRONMENT_NAMES == (
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
    )


def test_user_and_password_are_quote_plus_encoded(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_environment(monkeypatch, _VALUES)
    url = database_url_from_environment()
    assert url == (
        f"postgresql+psycopg://{quote_plus(_VALUES['POSTGRES_USER'])}:{quote_plus(_VALUES['POSTGRES_PASSWORD'])}"
        "@db.example.invalid:6543/btc-swing"
    )
    assert url == "postgresql+psycopg://rbt+user%40x:p%40ss%3Aw%2Frd%25%23%26%3D+%2B@db.example.invalid:6543/btc-swing"


@pytest.mark.parametrize(
    "missing",
    [
        ("POSTGRES_PASSWORD",),
        ("POSTGRES_USER", "POSTGRES_PORT"),
        ("POSTGRES_HOST", "POSTGRES_DB"),
        DATABASE_ENVIRONMENT_NAMES,
    ],
)
def test_missing_names_are_listed_without_any_value(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], missing: tuple[str, ...]
) -> None:
    _set_environment(monkeypatch, {name: value for name, value in _VALUES.items() if name not in missing})
    with pytest.raises(DatabaseEnvironmentError) as raised:
        database_url_from_environment()
    assert raised.value.missing == missing
    assert str(raised.value) == f"missing PostgreSQL environment variables: {list(missing)}"
    for value in _VALUES.values():
        assert value not in str(raised.value)
        assert quote_plus(value) not in str(raised.value)
    assert capsys.readouterr() == ("", "")


def test_an_empty_variable_counts_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_environment(monkeypatch, {**_VALUES, "POSTGRES_PASSWORD": ""})
    with pytest.raises(DatabaseEnvironmentError) as raised:
        database_url_from_environment()
    assert raised.value.missing == ("POSTGRES_PASSWORD",)
    assert isinstance(raised.value, ValueError)


def test_the_helper_never_prints_or_logs(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _set_environment(monkeypatch, _VALUES)
    database_url_from_environment()
    assert capsys.readouterr() == ("", "")
    tree = ast.parse(Path(database.__file__).read_text())
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    imported = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imported |= {
        (node.module or "").split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    }
    assert "print" not in names
    assert not {"logging", "warnings", "sys"} & imported
    assert not {"write", "write_text", "write_bytes", "dump", "dumps", "open"} & (names | attributes)


# --- isolation from BTC-019 research-only modules -------------------------------------


def _resolve_from(node: ast.ImportFrom, package: str) -> str:
    if not node.level:
        return node.module or ""
    base = package.split(".")
    base = base[: len(base) - (node.level - 1)]
    return ".".join([*base, node.module] if node.module else base)


def _module_package(path: Path) -> str:
    """The package a relative import in ``path`` resolves against."""

    return ".".join(path.relative_to(ROOT).parent.parts)


def _is_research_only(dotted: str) -> bool:
    parts = dotted.split(".")
    if parts[:2] != ["btc_predictor", "research"]:
        return False
    return any(part.endswith(name) for part in parts[2:] for name in BTC019_RESEARCH_ONLY)


def research_only_imports(source: str, *, package: str = RESEARCH_BACKTEST_PACKAGE) -> list[str]:
    """Every BTC-019 research-only module ``source`` imports, in any form, at any depth."""

    found = []
    tree = ast.parse(source)
    importer_names = set(_DYNAMIC_IMPORTERS)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in {"importlib", "importlib.util"}:
            importer_names.update(alias.asname or alias.name for alias in node.names if alias.name in _DYNAMIC_IMPORTERS)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            module = _resolve_from(node, package)
            targets = [module, *(f"{module}.{alias.name}" for alias in node.names)]
        elif isinstance(node, ast.Call):
            function = node.func
            name = function.attr if isinstance(function, ast.Attribute) else getattr(function, "id", "")
            if name not in importer_names:
                continue
            targets = [
                argument.value
                for argument in [*node.args, *(keyword.value for keyword in node.keywords)]
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str)
            ]
            # import_module resolves leading dots against its package argument,
            # which may be a literal or the module's own __package__. Resolve
            # that form before applying the guarded-module identity check.
            package_arg = next((kw.value for kw in node.keywords if kw.arg == "package"),
                               node.args[1] if len(node.args) > 1 else None)
            relative_package = package
            if isinstance(package_arg, ast.Constant) and isinstance(package_arg.value, str):
                relative_package = package_arg.value
            resolved = []
            for target in targets:
                if target.startswith("."):
                    try:
                        target = resolve_name(target, relative_package)
                    except (ImportError, ValueError):
                        pass  # An invalid relative import has no module identity.
                resolved.append(target)
            targets = resolved
        else:
            continue
        found += [target for target in targets if _is_research_only(target)]
    return sorted(set(found))


def _research_backtest_sources() -> list[Path]:
    return sorted(RESEARCH_BACKTEST.rglob("*.py"))


def test_the_isolation_scan_covers_every_research_backtest_module() -> None:
    names = {path.relative_to(RESEARCH_BACKTEST).as_posix() for path in _research_backtest_sources()}
    assert {"__init__.py", "coverage.py", "database.py", "input_census.py", "replay_inputs.py"} <= names


def test_no_research_backtest_module_imports_a_btc019_research_module() -> None:
    offenders = {
        path.relative_to(ROOT).as_posix(): imports
        for path in _research_backtest_sources()
        if (imports := research_only_imports(path.read_text(), package=_module_package(path)))
    }
    assert offenders == {}


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("import btc_predictor.research.btc019_empirical\n", "btc_predictor.research.btc019_empirical"),
        ("import os, btc_predictor.research.reference_composite as rc\n", "btc_predictor.research.reference_composite"),
        ("from btc_predictor.research import btc019_empirical\n", "btc_predictor.research.btc019_empirical"),
        ("from btc_predictor.research import us_equity_market_closures, price_source_policy\n",
         "btc_predictor.research.price_source_policy"),
        ("from btc_predictor.research.btc019b_diagnostics import x\n", "btc_predictor.research.btc019b_diagnostics"),
        ("def f():\n    from btc_predictor.research.btc019_empirical import _database_url_from_environment\n",
         "btc_predictor.research.btc019_empirical"),
        ("class C:\n    def m(self):\n        import btc_predictor.research.btc019_completion_gate\n",
         "btc_predictor.research.btc019_completion_gate"),
        ("from ..research import btc019_empirical\n", "btc_predictor.research.btc019_empirical"),
        ("from ..research.reference_composite import y\n", "btc_predictor.research.reference_composite"),
        ("import importlib\nimportlib.import_module('btc_predictor.research.btc019_empirical')\n",
         "btc_predictor.research.btc019_empirical"),
        ("__import__('btc_predictor.research.price_source_policy')\n", "btc_predictor.research.price_source_policy"),
        ("def f():\n    import importlib\n    return importlib.import_module('..research.btc019_empirical', __package__)\n",
         "btc_predictor.research.btc019_empirical"),
        ("import importlib as loader\nloader.import_module('.reference_composite', 'btc_predictor.research')\n",
         "btc_predictor.research.reference_composite"),
        ("from importlib import import_module as load\nload('btc_predictor.research.btc019_empirical')\n",
         "btc_predictor.research.btc019_empirical"),
        ("from importlib import import_module as load\nload(name='..research.price_source_policy', package=__package__)\n",
         "btc_predictor.research.price_source_policy"),
    ],
)
def test_the_isolation_scan_finds_every_import_form(source: str, expected: str) -> None:
    assert expected in research_only_imports(source)


@pytest.mark.parametrize(
    "source",
    [
        "from btc_predictor.research import us_equity_market_closures\n",
        "from btc_predictor.research import prospective_integration_corpus as corpus\n",
        "from btc_predictor.research_backtest import database\n",
        "from . import database\n",
        "import importlib\nimportlib.import_module(name)\n",
    ],
)
def test_the_isolation_scan_allows_other_modules(source: str) -> None:
    assert research_only_imports(source) == []
